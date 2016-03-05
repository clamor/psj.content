# -*- coding: utf-8 -*-
#  psj.content is copyright (c) 2014, 2015 Uli Fouquet
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston,
#  MA 02111-1307 USA.
#
"""Sources (in the zope.schema sense) and source context binders.

"""
import os
import redis
from dinsort import normalize
from five import grok
from z3c.formwidget.query.interfaces import IQuerySource
from zope.component import queryUtility
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from psj.content.interfaces import IExternalVocabConfig, IRedisStoreConfig
from psj.content.utils import make_terms, make_keyvalue_terms, tokenize, untokenize, to_string


class ExternalVocabBinder(object):
    """A source retrieving data from an external vocabulary.

    We expect some IExternalVocabConfig registered under name `name`.

    This binder is initialized with a `name` under which we will look
    up IExternalVocabConfigs when binding.

    When an instance of this binder is called for the first time, it
    tries to find the appropriate external vocab config, tries to read
    the file linked to the config and returns a SimpleVocabulary.

    If one of these steps fails (the external vocab was not
    registered, the path given in a config does not exist, etc.), we
    return an empty vocabulary.
    """
    grok.implements(IContextSourceBinder)

    name = None
    vocab = None

    def __init__(self, name):
        self.name = name

    def __call__(self, context):
        if self.vocab is not None:
            return self.vocab
        util = queryUtility(IExternalVocabConfig, name=self.name)
        if util is None:
            return SimpleVocabulary.fromValues([])
        path = util.get('path', None)
        if not path or not os.path.isfile(path):
            return SimpleVocabulary.fromValues([])
        vtype = util.get('vtype', None)
        if vtype == 'keyvalue':
            self.vocab = SimpleVocabulary(
                make_keyvalue_terms([line.strip() for line in open(path, 'r')]))
        else:
            self.vocab = SimpleVocabulary(
                make_terms([line.strip() for line in open(path, 'r')]))
        return self.vocab


class ExternalRedisBinder(ExternalVocabBinder):
    """A source that looks up an external REDIS store to retrieve
    valid entries.
    """
    def __call__(self, context):
        if self.vocab is not None:
            return self.vocab
        util = queryUtility(IRedisStoreConfig, name=self.name)
        if util is None:
            return SimpleVocabulary.fromValues([])
        return RedisSource(
            host=util['host'], port=util['port'], db=util['db'])


class ExternalRedisAutocompleteBinder(ExternalVocabBinder):
    """A source that looks up an external REDIS store to retrieve
    valid entries.

    Different to `ExternalRedisBinder` this one utilizes a
    `RedisAutocompleteSource` for retrieving data and not a regular
    RedisSource.

    Please note, that we provide sources with `allow_iter` set to
    False. This should work even with huge amounts of data.
    """
    def __init__(self, name, zset_name="autcomplete"):
        self.name = name
        self.zset_name = zset_name

    def __call__(self, context):
        if self.vocab is not None:
            return self.vocab
        util = queryUtility(IRedisStoreConfig, name=self.name)
        if util is None:
            return SimpleVocabulary.fromValues([])
        return RedisAutocompleteSource(
            host=util['host'], port=util['port'], db=util['db'],
            zset_name=self.zset_name, allow_iter=False)


class RedisSource(object):
    """A zope.schema ISource containing values from a Redis Store.

    This source contains keys of a Redis Store db.
    """
    grok.implements(IQuerySource)

    _client = None

    def __init__(self, host='localhost', port=6379, db=0):
        self.host = host
        self.port = port
        self.db = db

    def _get_client(self):
        if self._client is None:
            # create a client as late as possible but keep it then
            self._client = redis.StrictRedis(
                host=self.host, port=self.port, db=self.db)
        return self._client

    def __contains__(self, value):
        result = self._get_client().get(value)
        return result is not None

    def getTerm(self, value):
        """Return the ITerm object for term `value`.

        Raises `LookupError` if no such value can be found in Redis
        Store.

        Returns ITerm of `value`, where `value` is expected to be an
        existing *key* in a Redis store.

        The `title` of any resulting term will be set to the
        corresponding `value`.
        """
        db_val = self._get_client().get(value)
        if db_val is None:
            raise LookupError('No such term: %s' % value)
        return SimpleTerm(
            value, token=tokenize(value), title=db_val.decode('utf-8'))

    def __iter__(self):
        """Required by IIterableVocabulary.

        Return an iterator over all elements in source.
        """
        client = self._get_client()
        for key in client.scan_iter():
            value = self._get_client().get(key)
            yield SimpleTerm(
                key, token=tokenize(key), title=value.decode('utf-8'))

    def __len__(self):
        """Required by IIterableVocabulary.
        """
        return self._get_client().dbsize()

    def getTermByToken(self, token):
        key = untokenize(token)
        return self.getTerm(key)

    def search(self, query_string):
        """Return an iterable of ITerms matching `query_string`.

        A term matches, if its title starts with `query_string`.
        """
        for term in self:
            if term.title.startswith(query_string):
                yield term


class RedisKeysSource(RedisSource):
    """A redis source that only looks for keys in Redis stores.
    """
    def getTerm(self, value):
        result = super(RedisKeysSource, self).getTerm(value)
        return SimpleTerm(
            result.value, token=result.token, title=result.value)


class RedisAutocompleteSource(RedisSource):
    """A redis source that supports autocomplete functionality.

    `zset_name` sets the name of the redis ZSET containing the
    autocomplete terms.

    `separator` tells how we separate normalized terms from
    non-normalized when we lookup entries in redis ZSET.

    `allow_iter` marks whether queries over the full range of items are
    allowed. In principle we allow the use of `__iter__` but some dumb
    Plone widgets use it to render unchosen values. For huge datasets
    (say 100k+ items at least) we recommend to disable iteration. You
    should set `allow_iter` to `False` then.
    """
    def __init__(self, host='localhost', port=6379, db=0,
                 zset_name="autocomplete", separator="&&", allow_iter=True):
        self.host = host
        self.port = port
        self.db = db
        self.zset_name = zset_name
        self.separator = to_string(separator)
        self.allow_iter = allow_iter

    def _split_entry(self, entry):
        """Split an entry as found in ZSETs into pieces.
        """
        normalized, title = to_string(entry).split(self.separator, 1)
        return normalized.encode("utf-8"), title.decode("utf-8")

    def __iter__(self):
        """Required by IIterableVocabulary.

        Return an iterator over all elements in source. If instance var
        `allow_iter` is False, we return an empty iterator.
        """
        if self.allow_iter:
            client = self._get_client()
            for entry, score in client.zscan_iter(self.zset_name):
                token, title = self._split_entry(entry)
                yield SimpleTerm(token, token, title)

    def __len__(self):
        """Required by IIterableVocabulary.
        """
        return self._get_client().zcard(self.zset_name)

    def getTerm(self, key):
        """Return the ITerm object for term `key`.

        Raises `LookupError` if no such key can be found in Redis
        Store.

        Given keys are treated as tokens.

        The `title` of any resulting term will is constructed from key
        and value as::

           "<VALUE> (<KEY>)"

        """
        value = self._get_client().get(key)
        if value is None:
            raise LookupError('No such term: %s' % key)
        title = "%s (%s)" % (value.decode("utf-8"), key)
        return SimpleTerm(key, key, title)

    def getTermByToken(self, token):
        """Get ITerm with `token`.

        Raises `LookupError` if token cannot be found.
        """
        return self.getTerm(token)

    def search(self, query_string):
        """Return an iterable of ITerms matching `query_string`.

        A term matches, if its normalized title starts with `query_string`.

        "normalized" means what `dinsort` defines as normalizing.

        We will delver at most 10 entries. Why so few? Because the
        normally used autocomplete widget only displays 10 items and
        does its own sorting. This led to the following unfortunate
        possibility: if a term contains umlauts and is sorted by
        autocomplete widget relatively late, then the term might not
        show up in the first ten items displayed and is therefore
        unpickable at all. Giving 10 entries, we can be sure that the
        (in *our* ordering) first picked term is displayed by the
        autocomplete widget.
        """
        query_string = normalize(query_string)
        search_term = "(%s" % to_string(query_string)
        db_entries = self._get_client().zrangebylex(
            self.zset_name, search_term, "+", 0, 10)
        for entry in db_entries:
            normalized, token = self._split_entry(entry)
            term = self.getTerm(token)
            yield term


language_source = ExternalVocabBinder(u'psj.content.Languages')
institutes_source = ExternalVocabBinder(u'psj.content.Institutes')
licenses_source = ExternalVocabBinder(u'psj.content.Licenses')
publishers_source = ExternalVocabBinder(u'psj.content.Publishers')
subjectgroup_source = ExternalVocabBinder(u'psj.content.Subjectgroup')
ddcgeo_source = ExternalVocabBinder(u'psj.content.DDCGeo')
ddcsach_source = ExternalVocabBinder(u'psj.content.DDCSach')
ddczeit_source = ExternalVocabBinder(u'psj.content.DDCZeit')
gndid_source = ExternalVocabBinder(u'psj.content.GND_ID')
gndterms_source = ExternalRedisAutocompleteBinder(
    u'psj.content.redis_conf', zset_name="gnd-autocomplete")

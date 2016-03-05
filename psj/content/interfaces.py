# -*- coding: utf-8 -*-
#  psj.content is copyright (c) 2014 Uli Fouquet
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
"""Public interfaces for psj.content.

"""
from zope.configuration.fields import Path
from zope.interface import Interface
from zope.schema import TextLine, ASCIILine, Int
from z3c.relationfield.interfaces import IHasRelations


class IDexterityHasRelations(IHasRelations):
    """ """


class IExternalVocabConfig(Interface):
    """A vocabular configuration.

    Contains a path to a file where the vocabulary contents are
    stored in simple lines.

    See `zcml.py` for hints how to use this ZCML directive.

    `path` is the local path to a file containing vocabulary contents.

    `name` is the name under which the vocabulary is registered
    (globally).
    """
    path = Path(
        title=u'Path',
        description=u'Directory where a vocabulary file can be found.',
        required=True,
        )

    name = TextLine(
        title=u'Name',
        description=u'Name this vocab should be registered under.',
        required=True,
        )

    vtype = TextLine(
        title=u'Vocabulary type',
        description=u'What type of vocabulary is used.',
        required=False,
        )
    

class IRedisStoreConfig(Interface):
    """Configuration for connections to a Redis store.

    See `zcml.py` for hints how to use this ZCML directive.
    """
    host = ASCIILine(
        title=u'Host',
        description=u'The machine where the Redis store is running',
        required=True,
        default='localhost',
        )

    port = Int(
        title=u'Port',
        description=u'Port number the Redis store runs at',
        required=True,
        default=6379,
        )

    db = Int(
        title=u'DB',
        description=u'Database number of Redis store to connect to',
        required=True,
        default=0,
        )

    name = TextLine(
        title=u'Name',
        description=u'Name this config should be registered under.',
        required=True,
        )


class IRedisStoreZSetConfig(IRedisStoreConfig):
    """Definition of a ZSet stored in a RedisStore.

    Requires parameters from `IRedisStoreConfig` and one additional
    parameter `zset_name` that gives the name of an existing ZSET
    stored in a redis store.

    See `zcml.py` for hints how to use this ZCML directive.
    """
    zset_name = TextLine(
        title=u"ZSet name",
        description=u"Name of ZSET as stored in redis store.",
        required=True,
    )


class ISearchableTextGetter(Interface):
    """A utility determining the searchable text of objects.
    """
    def __call__(context):
        """Get the searchable text for `context`.

        Returns a string containing the text that should be
        searchable.
        """


class IPSJGNDTermsGetter(Interface):
    """A utility that can map GND ids to GND terms.
    """
    def terms_from_ids(ids):
        """Return an iterable of terms.

        `ids` is expected to be an iterable as well.
        """

class IPSJGNDTermsLayer(Interface):
    """Marker interface for the Browserlayer
    """

class IHasGNDTerms(Interface):
    """Content with GND Terms
    """

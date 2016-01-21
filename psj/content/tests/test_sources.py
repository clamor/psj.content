# -*- coding: utf-8 -*-
# Tests for sources module.
import redis
import unittest
from z3c.formwidget.query.interfaces import IQuerySource
from zope.component import getGlobalSiteManager
from zope.interface import verify
from zope.schema.interfaces import IContextSourceBinder, ITitledTokenizedTerm
from zope.schema.vocabulary import SimpleVocabulary
from psj.content.interfaces import IRedisStoreConfig
from psj.content.sources import (
    ExternalVocabBinder, ExternalRedisBinder, ExternalRedisAutocompleteBinder,
    RedisSource, RedisAutocompleteSource, RedisKeysSource, institutes_source,
    licenses_source, publishers_source, subjectgroup_source, ddcgeo_source,
    ddcsach_source, ddczeit_source, gndid_source, gndterms_source,
    )
from psj.content.testing import ExternalVocabSetup, RedisLayer
from psj.content.utils import tokenize


class RedisSourceTests(unittest.TestCase):
    layer = RedisLayer

    def setUp(self):
        settings = self.layer['redis_server'].settings['redis_conf']
        port = settings['port']
        self.redis = redis.StrictRedis(host='localhost', port=port, db=0)
        self.redis.flushdb()
        self.redis.set(u'foo', u'bar')
        self.redis_host = settings['bind']
        self.redis_port = settings['port']

    def tearDown(self):
        self.redis.flushdb()

    def test_iface(self):
        # make sure we fullfill promised interfaces
        source = RedisSource(host=self.redis_host, port=self.redis_port)
        verify.verifyClass(IQuerySource, RedisSource)
        verify.verifyObject(IQuerySource, source)

    def test_basic(self):
        # make sure, basic redis store test setup works
        r = self.redis
        result = r.get('foo')
        self.assertEqual(result, 'bar')

    def test_get_contained(self):
        # we can tell whether a certain key is stored in redis store
        source = RedisSource(host=self.redis_host, port=self.redis_port)
        result = u'foo' in source
        self.assertEqual(result, True)

    def test_get_uncontained(self):
        # we can tell if a certain key is not in redis store
        source = RedisSource(host=self.redis_host, port=self.redis_port)
        result = u'bar' in source
        self.assertEqual(result, False)

    def test_get_term_contained(self):
        # we can get contained terms as ITerm
        source = RedisSource(host=self.redis_host, port=self.redis_port)
        term = source.getTerm(u'foo')
        assert ITitledTokenizedTerm.providedBy(term)
        self.assertTrue(hasattr(term, 'value'))
        self.assertEqual(term.value, u'foo')
        self.assertTrue(hasattr(term, 'token'))
        self.assertEqual(term.token, 'Zm9v')
        self.assertTrue(hasattr(term, 'title'))
        self.assertEqual(term.title, u'bar')

    def test_len(self):
        # we can get the size of a database
        source = RedisSource(host=self.redis_host, port=self.redis_port)
        self.assertEqual(len(source), 1)
        self.redis.set("bar", "baz")
        self.assertEqual(len(source), 2)

    def test_iter(self):
        # we can iterate over all elements
        source = RedisSource(host=self.redis_host, port=self.redis_port)
        elem_list = [x for x in source]
        self.assertEqual(len(elem_list), 1)
        self.assertTrue(ITitledTokenizedTerm.providedBy(elem_list[0]))

    def test_get_term_by_token(self):
        # we can get a term by its token
        source = RedisSource(host=self.redis_host, port=self.redis_port)
        token = tokenize("foo")
        result = source.getTermByToken(token)
        self.assertTrue(ITitledTokenizedTerm.providedBy(result))

    def test_search(self):
        # we can search a source
        source = RedisSource(host=self.redis_host, port=self.redis_port)
        self.redis.set("far", "boo")
        self.redis.set("gaz", "hor")
        result1 = [x.title for x in source.search("b")]
        result2 = [x.title for x in source.search("h")]
        result3 = [x.title for x in source.search("ba")]
        self.assertEqual(sorted(result1), ["bar", "boo"])
        self.assertEqual(result2, ["hor"])
        self.assertEqual(result3, ["bar"])


class RedisKeysSourceTests(unittest.TestCase):

    layer = RedisLayer

    def setUp(self):
        settings = self.layer['redis_server'].settings['redis_conf']
        port = settings['port']
        self.redis = redis.StrictRedis(host='localhost', port=port, db=0)
        self.redis.flushdb()
        self.redis.set(u'foo', u'bar')
        self.redis_host = settings['bind']
        self.redis_port = settings['port']

    def tearDown(self):
        self.redis.flushdb()

    def test_iface(self):
        # make sure we fullfill promised interfaces
        source = RedisKeysSource(host=self.redis_host, port=self.redis_port)
        verify.verifyClass(IQuerySource, RedisKeysSource)
        verify.verifyObject(IQuerySource, source)

    def test_get_contained(self):
        # we can tell whether a certain key is stored in redis store
        source = RedisKeysSource(host=self.redis_host, port=self.redis_port)
        result = u'foo' in source
        self.assertEqual(result, True)

    def test_get_uncontained(self):
        # we can tell if a certain key is not in redis store
        source = RedisKeysSource(host=self.redis_host, port=self.redis_port)
        result = u'bar' in source
        self.assertEqual(result, False)

    def test_get_term_contained(self):
        # we can get contained terms as ITerm
        source = RedisKeysSource(host=self.redis_host, port=self.redis_port)
        term = source.getTerm(u'foo')
        assert ITitledTokenizedTerm.providedBy(term)
        self.assertTrue(hasattr(term, 'value'))
        self.assertEqual(term.value, u'foo')
        self.assertTrue(hasattr(term, 'token'))
        self.assertEqual(term.token, 'Zm9v')
        self.assertTrue(hasattr(term, 'title'))
        self.assertEqual(term.title, u'foo')


class RedisAutocompleteSourceTests(unittest.TestCase):

    layer = RedisLayer

    def setUp(self):
        settings = self.layer['redis_server'].settings['redis_conf']
        port = settings['port']
        self.redis = redis.StrictRedis(host='localhost', port=port, db=0)
        self.redis.flushdb()
        self.redis.zadd(u"autocomplete-foo", 0, "foo&&1")
        self.redis.zadd(u"autocomplete-foo", 0, "for&&2")
        self.redis.zadd(u"autocomplete-foo", 0, "baz&&3")
        self.redis.zadd(u"autocomplete-foo", 0, "bar&&4")
        self.redis.set("1", "Foo")
        self.redis.set("2", "For")
        self.redis.set("3", "Baz")
        self.redis.set("4", "Bär")
        self.redis_host = settings['bind']
        self.redis_port = settings['port']

    def tearDown(self):
        self.redis.flushdb()

    def test_basic(self):
        # make sure, basic redis store test setup works
        r = self.redis
        assert r.zcard('autocomplete-foo') == 4
        assert r.get("4") == "Bär"

    def test_iface(self):
        # make sure we fullfill promised interfaces
        source = RedisAutocompleteSource(
            host=self.redis_host, port=self.redis_port)
        verify.verifyClass(IQuerySource, RedisAutocompleteSource)
        verify.verifyObject(IQuerySource, source)

    def test_split_entry(self):
        # we can split ZSET entries.
        source = RedisAutocompleteSource(
            host=self.redis_host, port=self.redis_port)
        assert source._split_entry("one&&two") == ("one", u"two")
        assert source._split_entry(u"one&&two") == ("one", u"two")
        part1, part2 = source._split_entry("one&&two")
        assert isinstance(part1, str)
        assert isinstance(part2, unicode)

    def test_get_contained(self):
        # we can tell whether a certain key is stored in redis store
        self.redis.zadd(u'autocomplete-foo', 0, "bär&&5")
        self.redis.set(u"5", u"Bär")
        source = RedisAutocompleteSource(
            host=self.redis_host, port=self.redis_port,
            zset_name="autocomplete-foo")
        assert u'1' in source
        assert '1' in source
        assert u'5' in source
        assert '5' in source

    def test_get_uncontained(self):
        # we can tell if a certain key is not in redis store
        source = RedisAutocompleteSource(
            host=self.redis_host, port=self.redis_port,
            zset_name="autocomplete-foo")
        assert u'5' not in source
        assert '5' not in source

    def test_get_term_contained(self):
        # we can get contained terms as ITerm
        source = RedisAutocompleteSource(
            host=self.redis_host, port=self.redis_port,
            zset_name="autocomplete-foo")
        term = source.getTerm(u'4')
        assert ITitledTokenizedTerm.providedBy(term)
        self.assertTrue(hasattr(term, 'value'))
        self.assertEqual(term.value, u'4')
        self.assertTrue(hasattr(term, 'token'))
        self.assertEqual(term.token, u'4')
        self.assertTrue(hasattr(term, 'title'))
        self.assertEqual(term.title, u'Bär (4)')

    def test_len(self):
        # we can get the size of a ZSET providing our terms
        source = RedisAutocompleteSource(
            host=self.redis_host, port=self.redis_port,
            zset_name="autocomplete-foo")
        self.assertEqual(len(source), 4)
        self.redis.zadd(u'autocomplete-foo', 0, "new (0)&&New Kid (0)")
        self.assertEqual(len(source), 5)

    def test_iter(self):
        # we can iterate over all elements
        source = RedisAutocompleteSource(
            host=self.redis_host, port=self.redis_port,
            zset_name="autocomplete-foo")
        elem_list = [x for x in source]
        self.assertEqual(len(elem_list), 4)
        self.assertTrue(ITitledTokenizedTerm.providedBy(elem_list[0]))

    def test_allow_iter(self):
        # we can forbid to iterate. Useful for huge data sets.
        source = RedisAutocompleteSource(
            host=self.redis_host, port=self.redis_port,
            zset_name="autocomplete-foo", allow_iter=False)
        self.assertEqual(len([x for x in source]), 0)

    def test_allow_iter_on_the_fly(self):
        # we can forbid to iterate even after creation of source
        source = RedisAutocompleteSource(
            host=self.redis_host, port=self.redis_port,
            zset_name="autocomplete-foo", allow_iter=True)
        self.assertEqual(len([x for x in source]), 4)
        source.allow_iter = False
        self.assertEqual(len([x for x in source]), 0)

    def test_get_term_by_token(self):
        # we can get a term by its token
        source = RedisAutocompleteSource(
            host=self.redis_host, port=self.redis_port,
            zset_name="autocomplete-foo")
        result = source.getTermByToken(u'1')
        self.assertTrue(ITitledTokenizedTerm.providedBy(result))

    def test_search(self):
        # we can search autocomplete sources
        source = RedisAutocompleteSource(
            host=self.redis_host, port=self.redis_port,
            zset_name="autocomplete-foo")
        result1 = [x.title for x in source.search("b")]
        result2 = [x.title for x in source.search("fo")]
        result3 = [x.title for x in source.search("for")]
        result4 = [x.title for x in source.search("For (2)")]
        self.assertEqual(
            result1, [u'Bär (4)', u'Baz (3)', u'Foo (1)', u'For (2)'])
        self.assertEqual(result2, [u"Foo (1)", u"For (2)"])
        self.assertEqual(result3, [u"For (2)"])
        self.assertEqual(result4, [u"For (2)"])


class ExternalVocabBinderTests(ExternalVocabSetup, unittest.TestCase):

    def test_external_vocab_binder_iface(self):
        binder = ExternalVocabBinder(None)
        verify.verifyClass(IContextSourceBinder, ExternalVocabBinder)
        verify.verifyObject(IContextSourceBinder, binder)

    def test_external_vocab_binder_no_conf(self):
        # we cope with not registered utils
        binder = ExternalVocabBinder(name='not-a-registered-util-name')
        vocab = binder(context=None)
        assert isinstance(vocab, SimpleVocabulary)
        assert len([x for x in vocab]) == 0

    def test_external_vocab_binder_no_valid_path(self):
        # we cope with external confs where path is invalid
        self.create_external_vocab('psj.content.testvocab', valid_path=False)
        binder = ExternalVocabBinder(name='psj.content.testvocab')
        vocab = binder(context=None)
        assert isinstance(vocab, SimpleVocabulary)
        assert len([x for x in vocab]) == 0

    def test_inst_src_w_vocab(self):
        self.create_external_vocab('psj.content.Institutes')
        institutes_source.vocab = None  # make sure not to get cached entries
        src = institutes_source(context=None)
        assert isinstance(src, SimpleVocabulary)
        assert u'Vocab Entry 1' in src

    def test_licenses_src_w_vocab(self):
        self.create_external_vocab('psj.content.Licenses')
        licenses_source.vocab = None  # make sure not to get cached entries
        src = licenses_source(context=None)
        assert isinstance(src, SimpleVocabulary)
        assert u'Vocab Entry 1' in src

    def test_publishers_src_w_vocab(self):
        self.create_external_vocab('psj.content.Publishers')
        publishers_source.vocab = None  # make sure not to get cached entries
        src = publishers_source(context=None)
        assert isinstance(src, SimpleVocabulary)
        assert u'Vocab Entry 1' in src

    def test_subjectgroup_src_w_vocab(self):
        self.create_external_vocab('psj.content.Subjectgroup')
        subjectgroup_source.vocab = None  # avoid cached entries
        src = subjectgroup_source(context=None)
        assert isinstance(src, SimpleVocabulary)
        assert u'Vocab Entry 1' in src

    def test_ddcgeo_src_w_vocab(self):
        self.create_external_vocab('psj.content.DDCGeo')
        ddcgeo_source.vocab = None  # avoid cached entries
        src = ddcgeo_source(context=None)
        assert isinstance(src, SimpleVocabulary)
        assert u'Vocab Entry 1' in src

    def test_ddcsach_src_w_vocab(self):
        self.create_external_vocab('psj.content.DDCSach')
        ddcsach_source.vocab = None  # avoid cached entries
        src = ddcsach_source(context=None)
        assert isinstance(src, SimpleVocabulary)
        assert u'Vocab Entry 1' in src

    def test_ddczeit_src_w_vocab(self):
        self.create_external_vocab('psj.content.DDCZeit')
        ddczeit_source.vocab = None  # avoid cached entries
        src = ddczeit_source(context=None)
        assert isinstance(src, SimpleVocabulary)
        assert u'Vocab Entry 1' in src

    def test_gndid_src_w_vocab(self):
        self.create_external_vocab('psj.content.GND_ID')
        gndid_source.vocab = None  # avoid cached entries
        src = gndid_source(context=None)
        assert isinstance(src, SimpleVocabulary)
        assert u'Vocab Entry 1' in src


class ExternalRedisBinderTests(unittest.TestCase):

    layer = RedisLayer

    def setUp(self):
        settings = self.layer['redis_server'].settings['redis_conf']
        port = settings['port']
        self.redis = redis.StrictRedis(host='localhost', port=port, db=0)
        self.redis.flushdb()
        self.redis.set(u'foo', u'bar')
        self.redis.set(u'bar', u'baz')
        self.redis_host = settings['bind']
        self.redis_port = settings['port']

    def tearDown(self):
        self.redis.flushdb()

    def register_redis_conf(self, name='my-conf', invalid=0):
        # register a redis config as a named utility
        gsm = getGlobalSiteManager()
        conf = {
            'host': self.redis_host,
            'port': self.redis_port,
            'db': 0 + invalid
            }
        gsm.registerUtility(conf, provided=IRedisStoreConfig, name=name)

    def test_external_redis_binder_iface(self):
        binder = ExternalRedisBinder(None)
        verify.verifyClass(IContextSourceBinder, ExternalRedisBinder)
        verify.verifyObject(IContextSourceBinder, binder)

    def test_external_redis_binder_no_conf(self):
        # we cope with not registered redis confs
        binder = ExternalRedisBinder(name='not-a-registered-util-name')
        vocab = binder(context=None)
        assert isinstance(vocab, SimpleVocabulary)
        assert len([x for x in vocab]) == 0

    def test_external_redis_binder_invalid_conf(self):
        # with an invalid redis conf, we get empty sources
        self.register_redis_conf(name='my-test-redis-conf', invalid=1)
        binder = ExternalRedisBinder(name='my-test-redis-conf')
        source = binder(context=None)
        self.assertRaises(LookupError, source.getTerm, u'foo')
        assert isinstance(source, RedisSource)
        assert u'foo' not in source

    def test_external_redis_binder_valid_conf(self):
        # with a valid redis conf, we get valid vocabs
        self.register_redis_conf(name='my-test-redis-conf')
        binder = ExternalRedisBinder(name='my-test-redis-conf')
        source = binder(context=None)
        term = source.getTerm(u'foo')
        assert isinstance(source, RedisSource)
        assert u'foo' in source
        assert u'bar' in source
        assert u'baz' not in source
        self.assertEqual(term.value, u'foo')
        self.assertEqual(term.title, u'bar')


class ExternalRedisAutocompleteBinderTests(unittest.TestCase):

    layer = RedisLayer

    def setUp(self):
        settings = self.layer['redis_server'].settings['redis_conf']
        port = settings['port']
        self.redis = redis.StrictRedis(host='localhost', port=port, db=0)
        self.redis.flushdb()
        self.redis.zadd(u'autocomplete-foo', 0, u'foo&&1')
        self.redis.zadd(u'autocomplete-foo', 0, u'bar&&2')
        self.redis.set("1", "Foo")
        self.redis.set("2", "Bar")
        self.redis_host = settings['bind']
        self.redis_port = settings['port']

    def tearDown(self):
        self.redis.flushdb()

    def register_redis_conf(self, name='my-conf', invalid=0):
        # register a redis config as a named utility
        gsm = getGlobalSiteManager()
        conf = {
            'host': self.redis_host,
            'port': self.redis_port,
            'db': 0 + invalid
            }
        gsm.registerUtility(conf, provided=IRedisStoreConfig, name=name)

    def test_external_redis_binder_iface(self):
        binder = ExternalRedisAutocompleteBinder(None)
        verify.verifyClass(
            IContextSourceBinder, ExternalRedisAutocompleteBinder)
        verify.verifyObject(IContextSourceBinder, binder)

    def test_external_redis_binder_no_conf(self):
        # we cope with not registered redis confs
        binder = ExternalRedisAutocompleteBinder(
            name='not-a-registered-util-name', zset_name='autocomplete-foo')
        vocab = binder(context=None)
        assert isinstance(vocab, SimpleVocabulary)
        assert len([x for x in vocab]) == 0

    def test_external_redis_binder_invalid_conf(self):
        # with an invalid redis conf, we get empty sources
        self.register_redis_conf(name='my-test-redis-conf', invalid=1)
        binder = ExternalRedisAutocompleteBinder(
            name='my-test-redis-conf', zset_name='autocomplete-foo')
        source = binder(context=None)
        self.assertRaises(LookupError, source.getTerm, u'1')
        assert isinstance(source, RedisSource)
        assert u'1' not in source

    def test_external_redis_binder_valid_conf(self):
        # with a valid redis conf, we get valid vocabs
        self.register_redis_conf(name='my-test-redis-conf')
        binder = ExternalRedisAutocompleteBinder(
            name='my-test-redis-conf', zset_name='autocomplete-foo')
        source = binder(context=None)
        term = source.getTerm(u'1')
        assert isinstance(source, RedisSource)
        assert u'1' in source
        assert u'2' in source
        assert u'4' not in source
        self.assertEqual(term.value, u'1')
        self.assertEqual(term.title, u'Foo (1)')

    def test_external_redis_binder_no_iter(self):
        # for huge datasets, redis autocomplete binders forbids iter()
        self.register_redis_conf(name='my-test-redis-conf')
        binder = ExternalRedisAutocompleteBinder(
            name='my-test-redis-conf', zset_name='autocomplete-foo')
        source = binder(context=None)
        term = source.getTerm(u'1')
        assert term is not None               # we can get single terms...
        assert len([x for x in source]) == 0    # ...but not _all_ terms.
        assert source.allow_iter is False

    def test_gndterms_src_w_vocab(self):
        # we can use the gndterms source
        self.redis.zadd(u'gnd-autocomplete', 0, u'foo&&1')
        self.redis.zadd(u'gnd-autocomplete', 0, u'bar&&2')
        self.redis.set("1", "Foo")
        self.redis.set("2", "Bar")
        self.register_redis_conf(name=u'psj.content.redis_conf')
        gndterms_source.vocab = None  # avoid cached entries
        src = gndterms_source(context=None)
        assert isinstance(src, RedisAutocompleteSource)
        assert u'1' in src
        assert u'3' not in src

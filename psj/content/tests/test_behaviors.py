# -*- coding: utf-8 -*-
# tests for psj.content.behaviors
#
# XXX: FSD-related tests are missing. These are blocked by
#      difficulties installing FSD in tests.
#
import redis
import unittest
from plone.behavior.interfaces import IBehavior, IBehaviorAssignable
from plone.dexterity.interfaces import IDexterityContent
from plone.directives.form import IFormFieldProvider
from zope.component import (
    queryUtility, adapts, provideAdapter, getGlobalSiteManager
    )
from zope.interface import implements
from zope.schema.interfaces import (
    WrongType, ConstraintNotSatisfied, WrongContainedType,
    )
from psj.content.behaviors import (
    IPSJAuthor, IPSJTitle, IPSJSubtitle, IPSJAbstract, IPSJContributors,
    IPSJAddRetro, IPSJPartOf, IPSJEdition, IPSJSubjectIndexing,
    IPSJRelatedContent, IPSJGNDTerms,
    )
from psj.content.interfaces import IRedisStoreConfig
from psj.content.testing import (
    ExternalVocabSetup, REDIS_INTEGRATION_TESTING,
    )


class DummyDocument(object):
    # a dummy document that supports properties
    implements(IDexterityContent)
    portal_type = u'testtype'

    def __init__(self, title):
        self.title = title

    def hasProperty(self, key):
        return key in dir(self)

    def setProperty(self, key, val):
        setattr(self, key, val)

    def getProperty(self, key):
        return getattr(self, key)

    def _updateProperty(self, key, val):
        self.setProperty(key, val)


class TestingAssignable(object):
    # a IBehaviorAssignable adapter that adapts DummyContent objects
    implements(IBehaviorAssignable)
    adapts(DummyDocument)

    enabled = [IPSJAuthor, IPSJTitle, IPSJSubtitle, IPSJAbstract,
               IPSJContributors, IPSJAddRetro, IPSJPartOf, IPSJEdition,
               IPSJSubjectIndexing, IPSJRelatedContent, IPSJGNDTerms
               ]

    def __init__(self, context):
        self.context = context

    def supports(self, behavior_interface):
        return behavior_interface in self.enabled

    def enumerate_behaviors(self):
        for e in self.enabled:
            yield queryUtility(IBehavior, name=e.__identifier__)


class MetadataBehaviorsTests(ExternalVocabSetup, unittest.TestCase):
    # Tests of behaviors concerning basic PSJ metadata.

    layer = REDIS_INTEGRATION_TESTING

    def setup_redis_store(self):
        # setup a redis store config providing GND terms (deprecated?)
        gsm = getGlobalSiteManager()
        settings = self.layer['redis_server'].settings['redis_conf']
        conf = {
            'host': settings['bind'], 'port': settings['port'], 'db': 0
            }
        redis_client = redis.StrictRedis(
            host=conf['host'], port=conf['port'], db=conf['db'])
        redis_client.set(u'foo', u'bar')
        gsm.registerUtility(
            conf, provided=IRedisStoreConfig, name="psj.content.redis-GND")

    def setup_redis_autocomplete(self):
        # setup a redis store config providing GND terms for autocompletion
        gsm = getGlobalSiteManager()
        settings = self.layer['redis_server'].settings['redis_conf']
        conf = {
            'host': settings['bind'], 'port': settings['port'], 'db': 0
            }
        redis_cli = redis.StrictRedis(
            host=conf['host'], port=conf['port'], db=conf['db'])
        redis_cli.zadd(u'gnd-autocomplete', 0, "vocab entry 1&&1")
        redis_cli.zadd(u'gnd-autocomplete', 0, "vocab entry 2&&2")
        redis_cli.zadd(u'gnd-autocomplete', 0, "vocab entry 3&&3")
        redis_cli.set("1", "Vocab Entry Title 1")
        redis_cli.set("2", "Vocab Entry Title 2")
        redis_cli.set("3", "Vocab Entry Title 3")
        gsm.registerUtility(
            conf, provided=IRedisStoreConfig, name="psj.content.redis_conf")
        return redis_cli

    def tearDown(self):
        # unregister IRedisStoreConfig utils, if they are registered.
        for name in ("psj.content.redis-GND", "psj.content.redis_conf"):
            util = queryUtility(IRedisStoreConfig, name=name)
            if util is None:
                continue
            getGlobalSiteManager().unregisterUtility(
                util, provided=IRedisStoreConfig, name=name)
        super(MetadataBehaviorsTests, self).tearDown()

    def create_behavioral_doc(self):
        # Create a dummy document for which bahaviors can be assigned
        doc = DummyDocument(b'doc')
        provideAdapter(TestingAssignable)
        self.assertEqual(IDexterityContent.providedBy(doc), True)
        return doc

    def behavior_installed(self, name, iface):
        # make sure we get the desired behavior after install
        name = u'psj.content.behaviors.%s' % name
        behavior = queryUtility(IBehavior, name=name, default=None)
        self.assertTrue(behavior is not None)
        self.assertEqual(behavior.interface, iface)
        # make sure the behavior provides IFormFieldProvider
        self.assertEqual(
            IFormFieldProvider.providedBy(behavior.interface), True)
        return

    def text_behavior_usable(self, attr_name, iface):
        # we can attach a behavior to a content type and modify some
        # text/textline attribute
        doc = self.create_behavioral_doc()
        behavior = iface(doc, None)
        self.assertTrue(behavior is not None)
        self.assertEqual(True, hasattr(behavior, attr_name))
        # we can assign valid values to doc through the behavior
        setattr(behavior, attr_name, u'John Cleese')
        self.assertEqual(u'John Cleese', getattr(doc, attr_name))
        # numbers are not accepted as Text/TextLines
        self.assertRaises(
            WrongType, setattr, behavior, attr_name, 1)
        # also byte streams (non-unicode) are rejected
        self.assertRaises(
            WrongType, setattr, behavior, attr_name, b'Cheese')
        return

    def textlist_behavior_usable(self, attr_name, iface):
        # we can attach a behavior to a content type and modify some
        # list of text/textline attribute
        doc = self.create_behavioral_doc()
        behavior = iface(doc, None)
        self.assertTrue(behavior is not None)
        self.assertEqual(True, hasattr(behavior, attr_name))
        # we can assign valid values to doc through the behavior
        setattr(behavior, attr_name, [u'John Cleese', ])
        self.assertEqual([u'John Cleese', ], getattr(doc, attr_name))
        # byte streams (non-unicode) are rejected
        self.assertRaises(
            WrongContainedType, setattr, behavior, attr_name, [b'Cheese', ])
        return

    def choice_behavior_usable(self, attr_name, iface):
        doc = self.create_behavioral_doc()
        self.create_external_vocab_from_choice(iface, attr_name)
        behavior = iface(doc, None)
        self.assertTrue(behavior is not None)
        self.assertEqual(True, hasattr(behavior, attr_name))
        # we can assign valid values to doc through the behavior
        setattr(behavior, attr_name, u'Vocab Entry 1')
        self.assertEqual(u'Vocab Entry 1', getattr(doc, attr_name))
        # values not in the vocab are rejected
        self.assertRaises(
            ConstraintNotSatisfied,
            setattr,
            behavior, attr_name, u'Invalid Entry')
        return

    def choicelist_behavior_usable(self, attr_name, iface):
        doc = self.create_behavioral_doc()
        self.create_external_vocab_from_choicelist(iface, attr_name)
        behavior = iface(doc, None)
        self.assertTrue(behavior is not None)
        self.assertEqual(True, hasattr(behavior, attr_name))
        # we can assign valid values to doc through the behavior
        setattr(behavior, attr_name, [u'Vocab Entry 1', ])
        self.assertEqual([u'Vocab Entry 1', ], getattr(doc, attr_name))
        # values not in the vocab are rejected
        self.assertRaises(
            WrongContainedType,
            setattr,
            behavior, attr_name, [u'Invalid Entry', ])
        return

    def enum_choicelist_behavior_usable(self, attr_name, iface):
        # test choicelists that contain "enumerating" choices, i.e.
        # sources with key/value pairs and numbers as keys.
        doc = self.create_behavioral_doc()
        behavior = iface(doc, None)
        self.assertTrue(behavior is not None)
        self.assertEqual(True, hasattr(behavior, attr_name))
        # we can assign valid values to doc through the behavior
        setattr(behavior, attr_name, ['1', ])
        self.assertEqual(['1', ], getattr(doc, attr_name))
        # values not in the vocab are rejected
        self.assertRaises(
            WrongContainedType,
            setattr,
            behavior, attr_name, [u'Invalid Entry', ])
        return

    def test_author_installed(self):
        self.behavior_installed('IPSJAuthor', IPSJAuthor)
        return

    def test_author_behavior_usable(self):
        # we can get a behavior by adapter
        self.text_behavior_usable(b'psj_author', IPSJAuthor)
        return

    def test_title_installed(self):
        self.behavior_installed('IPSJTitle', IPSJTitle)
        return

    def test_title_behavior_usable(self):
        # we can get a behavior by adapter
        self.text_behavior_usable(b'psj_title', IPSJTitle)
        return

    def test_subtitle_installed(self):
        self.behavior_installed('IPSJSubtitle', IPSJSubtitle)
        return

    def test_subtitle_behavior_usable(self):
        # we can get a behavior by adapter
        self.text_behavior_usable(b'psj_subtitle', IPSJSubtitle)
        return

    def test_abstract_installed(self):
        self.behavior_installed('IPSJAbstract', IPSJAbstract)
        return

    def test_abstract_behavior_usable(self):
        # we can get a behavior by adapter
        self.text_behavior_usable(b'psj_abstract', IPSJAbstract)
        return

    def test_contributors_installed(self):
        self.behavior_installed('IPSJContributors', IPSJContributors)

    def test_contributors_bahavior_usable(self):
        # XXX: we cannot test a relation?
        pass

    def test_add_retro_behavior_installed(self):
        self.behavior_installed('IPSJAddRetro', IPSJAddRetro)

    def test_add_retro_behavior_usable(self):
        # we can get a behavior by adapter
        self.text_behavior_usable(b'psj_link_bsb', IPSJAddRetro)
        self.text_behavior_usable(b'psj_ocr_text', IPSJAddRetro)

    def test_partof_behavior_installed(self):
        self.behavior_installed('IPSJPartOf', IPSJPartOf)

    def test_partof_behavior_usable(self):
        self.text_behavior_usable(b'psj_series', IPSJPartOf)
        self.text_behavior_usable(b'psj_volume', IPSJPartOf)

    def test_edition_behavior_installed(self):
        self.behavior_installed('IPSJEdition', IPSJEdition)

    def test_edition_behavior_usable(self):
        self.text_behavior_usable(b'psj_publisher', IPSJEdition)
        self.text_behavior_usable(b'psj_isbn_issn', IPSJEdition)

    def test_subject_indexing_behavior_installed(self):
        self.behavior_installed('IPSJSubjectIndexing', IPSJSubjectIndexing)

    def test_subject_indexing_behavior_usable(self):
        self.choicelist_behavior_usable(
            b'psj_subject_group', IPSJSubjectIndexing)
        self.choicelist_behavior_usable(
            b'psj_ddc_geo', IPSJSubjectIndexing)
        self.choicelist_behavior_usable(
            b'psj_ddc_sach', IPSJSubjectIndexing)
        self.choicelist_behavior_usable(
            b'psj_ddc_zeit', IPSJSubjectIndexing)
        self.textlist_behavior_usable(
            b'psj_gnd_id', IPSJSubjectIndexing)
        self.textlist_behavior_usable(
            b'psj_free_keywords', IPSJSubjectIndexing)

    def test_subject_indexing_behavior_gnd_terms(self):
        # psj_gnd_terms is a special field
        doc = DummyDocument(b'doc')
        provideAdapter(TestingAssignable)
        self.assertEqual(IDexterityContent.providedBy(doc), True)
        behavior = IPSJSubjectIndexing(doc, None)
        self.assertTrue(behavior is not None)
        self.assertEqual(True, hasattr(behavior, 'psj_gnd_terms'))
        behavior.psj_gnd_id = [u'foo', u'baz']
        self.setup_redis_store()
        self.assertEqual(behavior.psj_gnd_terms, [u'bar', u'baz'])

    def test_gndterms_installed(self):
        self.behavior_installed('IPSJGNDTerms', IPSJGNDTerms)
        return

    def test_gndterms_usable(self):
        self.setup_redis_autocomplete()
        self.enum_choicelist_behavior_usable(b'psj_gndterms', IPSJGNDTerms)

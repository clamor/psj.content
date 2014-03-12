# -*- coding: utf-8 -*-
# Tests for utils module.
import unittest
from zope.component import queryUtility
from zope.interface import verify
from psj.content.interfaces import ISearchableTextGetter
from psj.content.testing import INTEGRATION_TESTING
from psj.content.utils import to_string, SearchableTextGetter


class FakeTextProvider(object):

    psj_author = 'My Author'
    psj_title = 'My Title'
    psj_subtitle = u'My Subtitle'
    psj_institute = 'My Institute 1'
    psj_abstract = 'My Abstract'
    psj_publication_year = '1980'
    psj_ocr_text = 'My OCR'
    psj_series = 'My series'
    psj_publisher = 'My publisher'
    psj_subject_group = 'My subject group'
    psj_ddc_geo = 'My DDC Geo'
    psj_ddc_sach = 'My DDC Sach'
    psj_ddc_zeit = 'My DDC Zeit'
    psj_gnd_term = 'My GND term'
    psj_free_keywords = 'My keyword 1'
    psj_contributors = 'Contributor 1'


class HelperTests(unittest.TestCase):

    def test_to_string_from_string(self):
        # we can turn strings into strings
        result = to_string('äöü')
        self.assertEqual(result, 'äöü')

    def test_to_string_from_unicode(self):
        # we can turn unicodes into strings
        result = to_string(u'äöü')
        self.assertEqual(result, 'äöü')

    def test_to_string_from_number(self):
        # we can turn numbers into strings
        result = to_string(999)
        self.assertEqual(result, '999')


class SearchableTextGetterTests(unittest.TestCase):

    def get_context(self, value):
        # get a context object with one attribute set to `value`
        class FakeContext(object):
            psj_author = None
        context = FakeContext()
        context.psj_author = value
        return context

    def test_constructor(self):
        # we can construct searchableTextGetters without paramaters
        getter = SearchableTextGetter()
        assert isinstance(getter, SearchableTextGetter)

    def test_interfaces(self):
        # SearchableTextGetter instances provide the promised interfaces.
        getter = SearchableTextGetter()
        verify.verifyClass(ISearchableTextGetter, SearchableTextGetter)
        verify.verifyObject(ISearchableTextGetter, getter)

    def test_attributes_complete(self):
        # All relevant attribute names are looked up
        context = FakeTextProvider()
        getter = SearchableTextGetter()
        result = getter(context)
        attr_names = [x for x in dir(context) if not x.startswith('_')]
        for name in attr_names:
            val = getattr(context, name)
            assert val in result

    def test_missing_attributes(self):
        # we ignore not existent attributes
        context = object()
        getter = SearchableTextGetter()
        result = getter(context)
        self.assertEqual(result, '')

    def test_none_attributes(self):
        # we ignore attributes with None type
        context = self.get_context(None)
        result = SearchableTextGetter()(context)
        self.assertEqual(result, '')

    def test_str_attributes(self):
        # attributes with string values are respected
        context = self.get_context('String Value')
        result = SearchableTextGetter()(context)
        self.assertEqual(result, 'String Value')

    def test_unicode_attributes(self):
        # attributes with unicode values are respected
        context = self.get_context(u'Unicode Value')
        result = SearchableTextGetter()(context)
        self.assertEqual(result, 'Unicode Value')

    def test_list_attributes(self):
        # attributes with list values are respected
        context = self.get_context(['Value1', 'Value2'])
        result = SearchableTextGetter()(context)
        self.assertEqual(result, 'Value1 Value2')

    def test_tuple_attributes(self):
        # attributes with tuples values are respected
        context = self.get_context(('Value1', 'Value2'))
        result = SearchableTextGetter()(context)
        self.assertEqual(result, 'Value1 Value2')

    def test_number_attributes(self):
        # attributes with number values are respected
        context = self.get_context(999)
        result = SearchableTextGetter()(context)
        self.assertEqual(result, '999')

    def test_newlines_removed(self):
        # newlines are removed from values
        context = self.get_context('Foo\nBar\nBaz\n\n')
        result = SearchableTextGetter()(context)
        self.assertEqual(result, 'Foo Bar Baz')

    def test_umlauts_in_strings(self):
        # umlauts in strings are okay
        context = self.get_context('äöü')
        result = SearchableTextGetter()(context)
        self.assertEqual(result, 'äöü')

    def test_umlauts_in_unicodes(self):
        # umlauts in unicodes are okay
        context = self.get_context(u'äöü')
        result = SearchableTextGetter()(context)
        self.assertEqual(result, 'äöü')

    def test_umlauts_in_lists(self):
        # umlauts in list values are okay
        context = self.get_context(['aä', u'oö'])
        result = SearchableTextGetter()(context)
        self.assertEqual(result, 'aä oö')


class UtilsIntegrationTests(unittest.TestCase):

    layer = INTEGRATION_TESTING

    def test_searchabletextgetter_registered(self):
        # we can get an ISearchableTextGetter at runtime
        obj = queryUtility(ISearchableTextGetter)
        assert obj is not None

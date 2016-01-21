# -*- coding: utf-8 -*-
# Tests for utils module.
import unittest
from plone.app.textfield.value import RichTextValue
from zope.component import queryUtility
from zope.interface import verify
from zope.schema.vocabulary import SimpleTerm
from psj.content.interfaces import ISearchableTextGetter
from psj.content.testing import INTEGRATION_TESTING
from psj.content.utils import (
    to_string, strip_tags, SearchableTextGetter, make_terms, tokenize,
    untokenize,
    )


class FakeHTMLProvider(object):
    # fake a blob
    def __init__(self, data):
        self.data = data


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

    #
    # to_string() tests
    #
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

    #
    # strip_tags() tests
    #
    def test_strip_tags_simple(self):
        # simple one-leveled docs are stripped correctly
        result = strip_tags('<div>foo</div>')
        self.assertEqual('foo', result)

    def test_strip_tags_nested(self):
        # we can strip tags from nested HTML
        result = strip_tags('<div>foo<div>bar</div>baz</div>')
        self.assertEqual('foobarbaz', result)

    def test_strip_tags_non_ascii(self):
        # we handle non-ASCII chars correctly
        result = strip_tags('<div>ä</div>')
        self.assertEqual('ä', result)

    def test_strip_tags_no_content(self):
        # HTML w/o any tags is handled correctly
        result = strip_tags('Hi there!')
        self.assertEqual('Hi there!', result)

    def test_strip_tags_no_linebreak(self):
        # linebreaks are removed from HTML
        result = strip_tags('foo\nbar\nbaz')
        self.assertEqual('foo bar baz', result)

    def test_strip_tags_only_single_spaces(self):
        # concatenated spaces are reduced to a single one.
        result = strip_tags('foo  bar \nbaz')
        self.assertEqual('foo bar baz', result)

    def test_strip_tags_result_stripped(self):
        # leading/trailing whitespaces are stripped from result
        result = strip_tags('  foo bar \n ')
        self.assertEqual('foo bar', result)


class SearchableTextGetterTests(unittest.TestCase):

    def get_context(self, value):
        # get a context object with one attribute set to `value`
        class FakeContext(object):
            psj_author = None
        context = FakeContext()
        context.psj_author = value
        return context

    def get_html_context(self, value):
        # get a context object with psj_html_repr set to `value`
        class FakeHTMLContext(object):
            psj_html_repr = None
        context = FakeHTMLContext()
        context.psj_html_repr = value
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

    def test_richtext_attributes(self):
        # attributes with richtext values are treated correctly
        context = self.get_context(
            RichTextValue(
                u"My Richtext Value\n",
                'text/plain', 'text/x-html-safe', 'utf-8')
            )
        result = SearchableTextGetter()(context)
        self.assertEqual(result, 'My Richtext Value')

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

    def test_html_repr_is_None(self):
        # psj_html_repr can be None
        context = self.get_html_context(None)
        result = SearchableTextGetter()(context)
        self.assertEqual(result, '')

    def test_html_repr_str(self):
        # psj_html_repr can be a string
        context = self.get_html_context(
            FakeHTMLProvider('<body><h1>Title1</h1>\n<p>Some Text</p></body>'))
        result = SearchableTextGetter()(context)
        self.assertEqual(result, 'Title1 Some Text')


class TokenizeTests(unittest.TestCase):
    # tests for tokenize()

    def is_7bit_ascii(self, string):
        if len(string) != len(string.encode('ascii', 'ignore')):
            raise ValueError('Token contains non-ASCII chars: %s' % string)

    def test_empty_string(self):
        result = tokenize('')
        assert len(result) > 0
        self.is_7bit_ascii(result)

    def test_simple_stream(self):
        result = tokenize('abc')
        self.assertEqual(result, 'YWJj')
        self.is_7bit_ascii(result)

    def test_utf8_stream(self):
        result = tokenize('äöü')
        self.assertEqual(result, 'w6TDtsO8')
        self.is_7bit_ascii(result)


class UntokenizeTest(unittest.TestCase):
    # tests for untokenize()

    def test_empty_string(self):
        result = untokenize(tokenize(''))
        self.assertEqual(result, '')

    def test_simple_stream(self):
        result = untokenize(tokenize('abc'))
        self.assertEqual(result, 'abc')

    def test_utf8_stream(self):
        result = untokenize(tokenize('äöü'))
        self.assertEqual(result, 'äöü')


class MakeTermsTests(unittest.TestCase):
    # tests for the make_terms function

    def test_make_terms(self):
        result = make_terms(['foo', 'bar', 'baz'])
        for term in result:
            assert isinstance(term, SimpleTerm)
        assert len(result) == 3
        term_strings = [(x.title, x.token, x.value) for x in result]
        self.assertEqual(
            term_strings,
            [(u'foo', 'Zm9v', u'foo'),
             (u'bar', 'YmFy', u'bar'),
             (u'baz', 'YmF6', u'baz')]
            )

    def test_make_terms_umlauts(self):
        result = make_terms(['ümläut', 'ömläut'])
        term_strings = [(x.title, x.token, x.value) for x in result]
        self.assertEqual(
            term_strings,
            [(u'\xfcml\xe4ut', 'w7xtbMOkdXQ=', u'\xfcml\xe4ut'),
             (u'\xf6ml\xe4ut', 'w7ZtbMOkdXQ=', u'\xf6ml\xe4ut')]
            )

    def test_make_terms_ignore_empty(self):
        # emtpy strings are ignored when creating terms
        result = make_terms(['', 'foo', '', 'bar', ''])
        term_strings = [(x.title, x.token, x.value) for x in result]
        self.assertEqual(
            term_strings,
            [(u'foo', 'Zm9v', u'foo'),
             (u'bar', 'YmFy', u'bar')]
            )


class UtilsIntegrationTests(unittest.TestCase):

    layer = INTEGRATION_TESTING

    def test_searchabletextgetter_registered(self):
        # we can get an ISearchableTextGetter at runtime
        obj = queryUtility(ISearchableTextGetter)
        assert obj is not None

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
"""Utilities and helpers for PSJ.

"""
from base64 import b64encode, b64decode
from five import grok
from plone.app.textfield import RichTextValue
from zope.schema.vocabulary import SimpleTerm
from psj.content import _
from psj.content.interfaces import ISearchableTextGetter

#: The attributes considered to hold fulltext.
FULLTEXT_ATTRIBUTES = (
    'psj_author', 'psj_title', 'psj_subtitle', 'psj_institute',
    'psj_abstract', 'psj_publication_year', 'psj_ocr_text', 'psj_series',
    'psj_publisher', 'psj_subject_group', 'psj_ddc_geo', 'psj_ddc_geo',
    'psj_ddc_sach', 'psj_ddc_zeit', 'psj_gnd_term', 'psj_free_keywords',
    'psj_contributors', 'psj_urn', 'psj_issue_number',
    )


def to_string(text):
    """Turn `text` into a string.

    Unicode texts are converted via `encode()`, other objects are
    simply casted by `str()`.
    """
    if isinstance(text, unicode):
        text = text.encode('utf-8')
    elif not isinstance(text, str):
        text = str(text)
    return text


def strip_tags(html):
    """Strip tags from HTML text.

    Returns the text in `html` with all tags removed. Any consecutive
    whitespaces are reduced to a single space. Thus, ``<div> Foo \n
    </div>`` becomes ``Foo``.
    """
    in_tag = False
    in_quote = False
    result = ''

    for char in html:
        if not in_tag and char == '<':
            in_tag = True
        elif not in_quote and char == '>':
            in_tag = False
        elif char in ['"', "'"]:
            in_quote = not in_quote
        elif not in_tag:
            result += char
    # replace consecutive whitespaces with single spaces
    return ' '.join(result.split()).strip()


class SearchableTextGetter(grok.GlobalUtility):
    """A utility extracting searchable text from objects.

    For PSJ objects we want a bunch of attribute values to be
    searchable by simple full-text search. The `SearchableTextGetter`
    scans object instances for these attributes and tries to turn the
    values into strings. Also `list` and `tuple` values are supported.

    An instance of this class is available as an unnamed global
    utility at runtime.
    """

    grok.implements(ISearchableTextGetter)

    def __call__(self, context):
        """Search all `FULLTEXT_ATTRIBUTES` in `context`.

        Values of `context` attributes are searched and turned into a
        single string.
        """
        result = ''
        for attr_name in FULLTEXT_ATTRIBUTES:
            attr_val = getattr(context, attr_name, None)
            if not attr_val:
                continue
            if isinstance(attr_val, list) or isinstance(attr_val, tuple):
                attr_val = ' '.join([to_string(x.strip()) for x in attr_val])
            elif isinstance(attr_val, RichTextValue):
                attr_val = to_string(attr_val.raw)
            else:
                attr_val = to_string(attr_val)
            attr_val = attr_val.replace('\n', ' ')
            result = '%s %s' % (result, attr_val.strip())
        result = '%s %s' % (result.strip(), self.get_html_repr_text(context))
        return result.strip()

    def get_html_repr_text(self, context):
        """Extract HTML from any `psj_html_repr` attribute of a
        `context`.

        The text is returned with all HTML tags stripped.
        """
        if not hasattr(context, 'psj_html_repr'):
            return ''
        html_content = getattr(context.psj_html_repr, 'data', '')
        return strip_tags(html_content)


def tokenize(byte_string):
    """Create a token from a byte stream.

    The `byte_stream` is expected to be a utf-8-encoded sequence of
    bytes.

    The result is guaranteed to be unique (i.e.: different
    `byte_streams` will give different results, same `byte_streams`
    will give same results).

    The result is guaranteed to be a valid 7-bit ASCII string.

    The result is guaranteed not to be empty.
    """
    return b64encode(byte_string) or '#'


def untokenize(ascii_string):
    """Create a byte stream from an ASCII token.

    Reverse op to `tokenize`.
    """
    if ascii_string == "#":
        return ""
    return b64decode(ascii_string)


def make_terms(strings):
    """Create zope.schema.SimpleTermss from strings.

    `strings` is expected to be a list of bytes in `utf-8` encoding.

    This function returns a list of `SimpleTerm` instances with
    unicode formatted titles and values and base 64 encoded tokens.

    `make_terms` guarantees that tokens are unique for each string put
    in and are representable as ASCII.
    """
    tuples = [(tokenize(s), _(s.decode('utf-8'))) for s in strings if s]
    return [SimpleTerm(value=t[1], token=t[0], title=t[1])
            for t in tuples]

def make_keyvalue_terms(strings):
    """
    """
    tuples = [(tokenize(s.split('&&')[0]), _(s.split('&&')[1].decode('utf-8'))) for s in strings if s]
    return [SimpleTerm(value=t[1], token=t[0], title=t[1])
            for t in tuples]

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
"""Plone Behaviors for `psj.content`.

"""
import md5
from collective import dexteritytextindexer
from five import grok
from plone.app.dexterity.behaviors.metadata import DCFieldProperty
from plone.app.textfield import RichText
from plone.autoform import directives as form
from plone.dexterity.interfaces import IDexterityContent
from plone.directives.form import (
    Schema, fieldset, IFormFieldProvider, mode, primary)
from plone.formwidget.autocomplete import (
    AutocompleteMultiFieldWidget)
from plone.formwidget.contenttree import ObjPathSourceBinder
from plone.namedfile.field import NamedBlobFile as NamedBlobFileField
from plone.namedfile.file import NamedBlobFile
from plone.supermodel import model
from Products.CMFCore.utils import getToolByName
from z3c.form.browser.orderedselect import OrderedSelectFieldWidget
from z3c.form.interfaces import IEditForm
from z3c.relationfield.schema import RelationChoice, RelationList
from zope.component import adapts, queryUtility
from zope.interface import implements, alsoProvides
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.schema import TextLine, Text, Choice, List, ASCIILine
from psj.content import _
from psj.content.interfaces import IRedisStoreConfig
from psj.content.sources import (
    subjectgroup_source, ddcgeo_source, ddcsach_source,
    ddczeit_source, RedisSource, language_source, institutes_source,
    licenses_source, gndterms_source
)


class PSJMetadataBase(object):
    """An adapter storing metadata directly on an object using the
    standard CMF DefaultDublinCoreImpl getters and setters.

    `context` is the object to be adapted.
    """
    adapts(IDexterityContent)

    def __init__(self, context):
        self.context = context


class PSJFieldProperty(DCFieldProperty):
    """A PSJ field property.

    A DC field property for PSJ behaviors.
    """
    pass


class IPSJBehavior(Schema):
    """A behavior supporting PSJ content types.
    """


class IPSJMetisCounter(IPSJBehavior):
    """PSJ Metis Counter.
    """
    fieldset(
        'psj_stats',
        label=_(u'PSJ Stats'),
        fields=('psj_metiscounter',),
        )

    psj_metiscounter = TextLine(
        title=_(u'Metis Counter'),
        description=_(u'URL zum Zählpixel der VG Wort'),
        required=False,
        )

alsoProvides(IPSJMetisCounter, IFormFieldProvider)


class IPSJAuthor(IPSJBehavior):
    """A document author.
    """
    fieldset(
        'psj_metadata',
        label=_(u'PSJ Metadata'),
        fields=('psj_author', ),
        )

    psj_author = TextLine(
        title=_(u'Author'),
        description=_(u'Document Author'),
        required=False,
        )

alsoProvides(IPSJAuthor, IFormFieldProvider)


class IPSJTitle(IPSJBehavior):
    """A document title.
    """
    fieldset(
        'psj_metadata',
        label=_(u'PSJ Metadata'),
        fields=('psj_title',),
        )

    psj_title = TextLine(
        title=_(u'Title'),
        description=_(u'Document Title'),
        required=False,
        )

alsoProvides(IPSJTitle, IFormFieldProvider)


class IPSJSubtitle(IPSJBehavior):
    """A document subtitle.
    """
    fieldset(
        'psj_metadata',
        label=_(u'PSJ Metadata'),
        fields=('psj_subtitle',),
        )

    psj_subtitle = TextLine(
        title=_(u'Subtitle'),
        description=_(u'Document Subtitle'),
        required=False,
        )

alsoProvides(IPSJSubtitle, IFormFieldProvider)


class IPSJAbstract(IPSJBehavior):
    """A document abstract.
    """
    fieldset(
        'psj_metadata',
        label=_(u'PSJ Metadata'),
        fields=('psj_abstract',),
        )

    psj_abstract = Text(
        title=_(u'Abstract'),
        description=_(u'Document Abstract'),
        required=False,
        )

alsoProvides(IPSJAbstract, IFormFieldProvider)


class IPSJContributors(IPSJBehavior):
    """FSDPersons as contributors.
    """
    fieldset(
        'psj_metadata',
        label=_(u'PSJ Metadata'),
        fields=('psj_contributors',),
        )

    psj_contributors = RelationList(
        title=_(u'Beitragende'),
        description=_(u'Contributors'),
        required=False,
        value_type=RelationChoice(
            title=_(
                u'Wählen Sie einen Personensatz aus Relation '
                u'zum Contenttype FSDPerson (Person)'),
            source=ObjPathSourceBinder()),
        )


alsoProvides(IPSJContributors, IFormFieldProvider)


class IPSJGNDTerms(IPSJBehavior):
    """A field providing GND terms with autocompletion.
    """
    form.widget('psj_gndterms', AutocompleteMultiFieldWidget)
    dexteritytextindexer.searchable('psj_gndterms')
    fieldset(
        'psj_metadata',
        label=_(u'PSJ Metadata'),
        fields=('psj_gndterms',),
        )

    psj_gndterms = List(
        title=_(u'GND Terms'),
        description=_(u'Description for GND Terms'),
        value_type=Choice(
            title=_(u'GND Terms'),
            description=_(u'GND Terms'),
            source=gndterms_source,
            ),
        required=False,
        )

alsoProvides(IPSJGNDTerms, IFormFieldProvider)


class IPSJBaseData(IPSJBehavior):
    """Document base metadata, including authorname, title, etc.
    """
    fieldset(
        'psj_metadata',
        label=_(u'PSJ Metadata'),
        fields=('psj_author', 'psj_author_relation', 'psj_author_list',
                'psj_title', 'psj_subtitle', 'psj_doi', 'psj_urn'),
        )

    dexteritytextindexer.searchable('psj_author')
    psj_author = List(
        title=_(u'Autor'),
        description=_(u'Autor(en) oder Herausgeber.'),
        required=True,
        readonly=True,
        value_type=TextLine(),
        )

    form.widget(psj_author_relation=AutocompleteMultiFieldWidget)
    psj_author_relation = List(
        title=_(u'Autor Relation'),
        description=_(u'Autor oder Herausgeber. '),
        required=False,
        value_type=Choice(
            title=_(
                u'Wählen Sie einen Personensatz aus Relation '
                u'zum Contenttype FSDPerson (Person)'),
            vocabulary="plone.principalsource.Users"),
        )

    psj_author_list = List(
        title=_(u'Autor'),
        description=_(u'Autor(en) oder Herausgeber.'),
        required=False,
        value_type=TextLine(),
        )

    dexteritytextindexer.searchable('psj_title')
    psj_title = TextLine(
        title=_(u'Titel'),
        description=_(u'Titel der Publikation'),
        required=False,
        )

    dexteritytextindexer.searchable('psj_subtitle')
    psj_subtitle = TextLine(
        title=_(u'Untertitel'),
        description=_(u'Untertitel der Publikation'),
        required=False,
        )

    dexteritytextindexer.searchable('psj_doi')
    psj_doi = TextLine(
        title=_(u'DOI'),
        description=_(u'Digital Object Identifier'),
        required=False,
        )

    dexteritytextindexer.searchable('psj_urn')
    psj_urn = TextLine(
        title=_(u'URN'),
        description=_(u'Unfiform Resource Name'),
        required=False,
        )

alsoProvides(IPSJBaseData, IFormFieldProvider)


class IPSJBaseDataContext(IPSJBehavior):
    """Document base metadata, including authorname, title, etc.
    """
    fieldset(
        'psj_metadata',
        label=_(u'PSJ Metadata'),
        fields=('psj_institute',),
        )

    dexteritytextindexer.searchable('psj_institute')
    form.widget(psj_institute=OrderedSelectFieldWidget)
    psj_institute = List(
        title=_(u'Institution'),
        description=_(u'Wählen Sie eine Institution aus'),
        value_type=Choice(
            title=_(u'Institution'),
            description=_(u'Institution'),
            source=institutes_source,
            required=False,
            ),
        required=False,
        )

alsoProvides(IPSJBaseDataContext, IFormFieldProvider)


class IPSJBaseDataDocLevel(IPSJBehavior):
    """Document base metadata, including authorname, title, etc.
    """
    fieldset(
        'psj_metadata',
        label=_(u'PSJ Metadata'),
        fields=('psj_abstract', 'psj_language', 'psj_license'),
        )

    dexteritytextindexer.searchable('psj_abstract')
    psj_abstract = RichText(
        title=_(u'Abstract'),
        description=_(u'Inhaltliche Zusammenfassung'),
        default_mime_type="text/html",
        output_mime_type="text/html",
        allowed_mime_types=('text/structured', 'text/plain', 'text/html'),
        default=u'',
        required=False,
        )

    psj_language = List(
        title=_(u'Language'),
        description=_(u'PSJ content language'),
        value_type=Choice(
            title=_(u'PSJ content language'),
            description=_(u''),
            source=language_source,
            required=False,
            ),
        required=False,
        )

    dexteritytextindexer.searchable('psj_license')
    psj_license = Choice(
        title=_(u'Lizenz'),
        description=_(u'Wählen Sie eine Lizenz aus'),
        source=licenses_source,
        required=False,
    )

alsoProvides(IPSJBaseDataDocLevel, IFormFieldProvider)


class IPSJAddRetro(IPSJBehavior):
    """Technical metadata for retro articles and postprints.
    """
    fieldset(
        'psj_metadata',
        label=_(u'PSJ Metadata'),
        fields=('psj_link_bsb', 'psj_pages', 'psj_ocr_text', 'psj_file'),
        )

    psj_link_bsb = TextLine(
        title=_(u'Link BSB'),
        description=_(u'Link zum Bereitstellungssystem der BSB'),
        required=False,
        )

    psj_pages = TextLine(
        title=_(u'Seiten'),
        description=_(u'Seiten in der Publikation'),
        required=False,
        )

    form.omitted('psj_ocr_text')
    form.no_omit(IEditForm, 'psj_ocr_text')
    dexteritytextindexer.searchable('psj_ocr_text')
    psj_ocr_text = Text(
        title=_(u'OCR Text'),
        description=_(u''),
        required=False,
        )

    primary('psj_file')
    psj_file = NamedBlobFileField(
        title=_(u'Digitized document'),
        description=_(u'Digitized document'),
        required=False,
        )

    mode(psj_ocr_text='input')


alsoProvides(IPSJAddRetro, IFormFieldProvider)


class IPSJPartOf(IPSJBehavior):
    """The meta data fields used to describe things being parts of others.
    """
    fieldset(
        'psj_metadata',
        label=_(u'PSJ Metadata'),
        fields=('psj_series', 'psj_volume'),
        )

    dexteritytextindexer.searchable('psj_series')
    psj_series = TextLine(
        title=_(u'Reihe'),
        description=_(u'Reihentitel'),
        required=False,
        )

    dexteritytextindexer.searchable('psj_volume')
    psj_volume = TextLine(
        title=_(u'Band'),
        description=_(u'Band'),
        required=False,
        )


alsoProvides(IPSJPartOf, IFormFieldProvider)


class IPSJPublicationYear(IPSJBehavior):
    """The meta data fields to describe an edition.
    """
    fieldset(
        'psj_metadata',
        label=_(u'PSJ Metadata'),
        fields=('psj_publication_year',),
        )

    dexteritytextindexer.searchable('psj_publication_year')
    psj_publication_year = TextLine(
        title=_(u'Erscheinungsjahr'),
        description=u'Erscheinungsjahr',
        required=False,
        )

alsoProvides(IPSJPublicationYear, IFormFieldProvider)


class IPSJEdition(IPSJBehavior):
    """The meta data fields to describe an edition.
    """
    fieldset(
        'psj_metadata',
        label=_(u'PSJ Metadata'),
        fields=('psj_publisher', 'psj_isbn_issn'),
        )

    dexteritytextindexer.searchable('psj_publisher')
    psj_publisher = TextLine(
        title=_(u'Verlag'),
        description=u'',
        required=False,
        )

    dexteritytextindexer.searchable('psj_isbn_issn')
    psj_isbn_issn = TextLine(
        title=_(u'ISBN/ISSN'),
        description=u'',
        required=False,
        )


alsoProvides(IPSJEdition, IFormFieldProvider)


class IPSJSubjectIndexing(IPSJBehavior):
    """Fields to categorize some document.
    """
    fieldset(
        'psj_metadata',
        label=_(u'PSJ Metadata'),
        fields=('psj_subject_group',
                'psj_ddc_geo',
                'psj_ddc_sach',
                'psj_ddc_zeit',
                'psj_gnd_id',
                'psj_gnd_terms',
                'psj_free_keywords',
                'psj_sw_zeit',
                ),
        )

    dexteritytextindexer.searchable('psj_subject_group')
    psj_subject_group = List(
        title=_(u'Epochenkategorie'),
        description=_(u''),
        value_type=Choice(
            title=_(u'Kategorie'),
            description=_(u''),
            source=subjectgroup_source,
            required=False,
            ),
        required=False,
        )

    dexteritytextindexer.searchable('psj_ddc_geo')
    psj_ddc_geo = List(
        title=_(u'Land/Region'),
        description=_(u''),
        value_type=Choice(
            title=_(u'Geo-Kategorie'),
            description=_(u''),
            source=ddcgeo_source,
            required=False,
            ),
        required=False,
        )

    dexteritytextindexer.searchable('psj_ddc_sach')
    psj_ddc_sach = List(
        title=_(u'Sach-Klassifikation'),
        description=_(u''),
        value_type=Choice(
            title=_(u'Sach-Kategorie'),
            description=_(u''),
            source=ddcsach_source,
            required=False,
            ),
        required=False,
        )

    dexteritytextindexer.searchable('psj_ddc_zeit')
    psj_ddc_zeit = List(
        title=_(u'Epoche'),
        description=_(u''),
        value_type=Choice(
            title=_(u'Zeit-Kategorie nach DDC'),
            description=_(u''),
            source=ddczeit_source,
            required=False,
            ),
        required=False,
        )

    dexteritytextindexer.searchable('psj_gnd_id')
    psj_gnd_id = List(
        title=_(u'Identnummern aus GND'),
        description=_(u''),
        value_type=TextLine(
            title=_(u'Identnummer'),
            description=_(u''),
            required=True,
            ),
        required=False,
        )

    dexteritytextindexer.searchable('psj_gnd_terms')
    psj_gnd_terms = List(
        title=_(u'GND Schlagwörter'),
        description=_(u''),
        value_type=TextLine(
            title=_(u'GND Schlagwort'),
            description=_(u''),
            ),
        required=False,
        readonly=True,
        )

    dexteritytextindexer.searchable('psj_free_keywords')
    psj_free_keywords = List(
        title=_(u'Freie Schlagwörter'),
        description=_(u''),
        value_type=TextLine(
            title=_(u'Freies Schlagwort'),
            description=_(u''),
            ),
        required=False,
        )

    dexteritytextindexer.searchable('psj_sw_zeit')
    psj_sw_zeit = TextLine(
        title=_(u'Zeitschlagwort'),
        description=_(u''),
        required=False,
        )


alsoProvides(IPSJSubjectIndexing, IFormFieldProvider)


class IPSJRelatedContent(model.Schema):
    """Some related document.
    """
    fieldset(
        'psj_related_content',
        label=_(u'Related Content'),
        fields=('psj_media', 'psj_primary_source'),
        )

    psj_media = RelationList(
        title=_(u'Media'),
        description=_(u'Link to folder with images or videos. '
                      u'Presented as tab'),
        default=[],
        value_type=RelationChoice(
            title=_(
                u'Wählen Sie einen Ordner '),
            source=ObjPathSourceBinder()),
        required=False,
        )

    psj_primary_source = TextLine(
        title=_(u'Quellen'),
        description=_(u'Link to related source on other site.'),
        required=False,
        )
alsoProvides(IPSJRelatedContent, IFormFieldProvider)


class IPSJOfficeDocTransformer(IPSJBehavior):
    """A document that provides some office doc.

    The transformer also supports automatic transforms of uploaded
    office docs.
    """
    fieldset(
        'psj_docholder',
        label=_(u'Office Docs'),
        fields=('psj_office_doc', 'psj_pdf_repr', 'psj_html_repr', 'psj_md5'),
        )

    primary('psj_office_doc')
    psj_office_doc = NamedBlobFileField(
        title=_(u'Source Office File (.doc, .docx, .odt)'),
        description=_(u'Document Abstract'),
        required=True,
        )

    dexteritytextindexer.searchable('psj_pdf_repr')
    psj_pdf_repr = NamedBlobFileField(
        title=_(u'PDF version'),
        description=_(u'The PDF representation of the source document.'),
        required=False,
        readonly=True,
        )

    psj_html_repr = NamedBlobFileField(
        title=_(u'HTML representation'),
        description=_(u'The HTML representation of the source document.'),
        required=False,
        readonly=True,
        )

    psj_md5 = ASCIILine(
        title=_(u'MD5 of Source'),
        description=_(u'The MD5 sum of the contained office doc.'),
        required=False,
        readonly=True,
        )

alsoProvides(IPSJOfficeDocTransformer, IFormFieldProvider)


class PSJMetisCounter(PSJMetadataBase):
    """A behaviour allowing to set the Metis pixel URL of a PSJ document.
    """
    implements(IPSJMetisCounter)

    psj_metiscounter = DCFieldProperty(
        IPSJMetisCounter['psj_metiscounter'],
        get_name='psj_metiscounter'
        )


class PSJAuthor(PSJMetadataBase):
    """A behaviour allowing to set the author of a PSJ document.
    """
    implements(IPSJAuthor)

    psj_author = DCFieldProperty(
        IPSJAuthor['psj_author'],
        get_name='psj_author'
        )


class PSJTitle(PSJMetadataBase):
    """A behaviour allowing to set the title of a PSJ document.
    """
    implements(IPSJTitle)

    psj_title = DCFieldProperty(
        IPSJTitle['psj_title'],
        get_name='psj_title'
        )


class PSJSubtitle(PSJMetadataBase):
    """A behaviour allowing to set the subtitle of a PSJ document.
    """
    implements(IPSJSubtitle)

    psj_subtitle = DCFieldProperty(
        IPSJSubtitle['psj_subtitle'],
        get_name='psj_subtitle'
        )


class PSJAbstract(PSJMetadataBase):
    """A behaviour allowing to set the abstract of a PSJ document.
    """
    implements(IPSJAbstract)

    psj_abstract = DCFieldProperty(
        IPSJAbstract['psj_abstract'],
        get_name='psj_abstract'
        )


class PSJContributors(PSJMetadataBase):
    """A behaviour allowing to set FSD persons as contributors.
    """
    implements(IPSJContributors)

    psj_abstract = DCFieldProperty(
        IPSJContributors['psj_contributors'],
        get_name='psj_contributors'
        )


class PSJGNDTerms(PSJMetadataBase):
    """A behavior providing GND terms read from a Redis Store.
    """
    implements(IPSJGNDTerms)

    psj_gndterms = DCFieldProperty(
        IPSJGNDTerms['psj_gndterms'],
        get_name='psj_gndterms'
        )


class PSJBaseDataContext(PSJMetadataBase):
    """A behavior providing base metadata
    'psj_institute'
    """
    implements(IPSJBaseDataContext)

    psj_institute = DCFieldProperty(
        IPSJBaseDataContext['psj_institute'],
        get_name='psj_institute'
        )


class PSJBaseDataDocLevel(PSJMetadataBase):
    """A behavior providing base metadata
    'psj_abstract', 'psj_language', 'psj_license'
    """
    implements(IPSJBaseDataDocLevel)

    psj_abstract = DCFieldProperty(
        IPSJBaseDataDocLevel['psj_abstract'],
        get_name='psj_abstract'
        )

    psj_language = DCFieldProperty(
        IPSJBaseDataDocLevel['psj_language'],
        get_name='psj_language'
        )

    psj_license = DCFieldProperty(
        IPSJBaseDataDocLevel['psj_license'],
        get_name='psj_license'
        )


class PSJBaseData(PSJMetadataBase):
    """A behavior providing base metadata
    'psj_author', 'psj_author_relation', 'psj_author_list',
    'psj_title', 'psj_subtitle','psj_doi', 'psj_urn'.
    """
    implements(IPSJBaseData)

    psj_author = DCFieldProperty(
        IPSJBaseData['psj_author'],
        get_name='psj_author'
        )

    psj_author_relation = DCFieldProperty(
        IPSJBaseData['psj_author_relation'],
        get_name='psj_author_relation'
        )

    psj_author_list = DCFieldProperty(
        IPSJBaseData['psj_author_list'],
        get_name='psj_author_list'
        )

    psj_title = DCFieldProperty(
        IPSJBaseData['psj_title'],
        get_name='psj_title'
        )

    psj_subtitle = DCFieldProperty(
        IPSJBaseData['psj_subtitle'],
        get_name='psj_subtitle'
        )

    psj_doi = DCFieldProperty(
        IPSJBaseData['psj_doi'],
        get_name='psj_doi'
        )

    psj_urn = DCFieldProperty(
        IPSJBaseData['psj_urn'],
        get_name='psj_urn'
        )


class PSJAddRetro(PSJMetadataBase):
    """A behavior providing technical metadata for retro docs.
    """
    implements(IPSJAddRetro)

    psj_link_bsb = DCFieldProperty(
        IPSJAddRetro['psj_link_bsb'],
        get_name='psj_link_bsb'
        )

    psj_pages = DCFieldProperty(
        IPSJAddRetro['psj_pages'],
        get_name='psj_pages'
        )

    psj_ocr_text = DCFieldProperty(
        IPSJAddRetro['psj_ocr_text'],
        get_name='psj_ocr_text'
        )

    primary('psj_file')
    psj_file = DCFieldProperty(
        IPSJAddRetro['psj_file'],
        get_name='psj_file'
        )


class PSJPartOf(PSJMetadataBase):
    """A behavior providing fields for docs being part of others.
    """
    implements(IPSJPartOf)

    psj_series = DCFieldProperty(
        IPSJPartOf['psj_series'],
        get_name='psj_series'
        )

    psj_volume = DCFieldProperty(
        IPSJPartOf['psj_volume'],
        get_name='psj_volume'
        )


class PSJEdition(PSJMetadataBase):
    """A behavior providing fields for edited documents.
    """
    implements(IPSJEdition)

    psj_publisher = DCFieldProperty(
        IPSJEdition['psj_publisher'],
        get_name='psj_publisher'
        )

    psj_isbn_issn = DCFieldProperty(
        IPSJEdition['psj_isbn_issn'],
        get_name='psj_isbn_issn'
        )


class PSJPublicationYear(PSJMetadataBase):
    """A behavior providing fields for edited documents.
    """
    implements(IPSJPublicationYear)

    psj_publication_year = DCFieldProperty(
        IPSJPublicationYear['psj_publication_year'],
        get_name='psj_publication_year'
        )


class PSJOfficeDocTransformer(PSJMetadataBase):
    """A document that provides some office doc.
    """
    implements(IPSJOfficeDocTransformer)

    psj_office_doc = DCFieldProperty(
        IPSJOfficeDocTransformer['psj_office_doc'],
        get_name='psj_office_doc',
        )

    psj_pdf_repr = DCFieldProperty(
        IPSJOfficeDocTransformer['psj_pdf_repr'],
        get_name='psj_pdf_repr',
        )

    psj_html_repr = DCFieldProperty(
        IPSJOfficeDocTransformer['psj_html_repr'],
        get_name='psj_html_repr',
        )


def psj_create_reprs(obj):
    """Create PDF, HTML, etc. representations of source doc.
    """
    transforms = getToolByName(obj, 'portal_transforms')
    in_data = getattr(obj.psj_office_doc, 'data', None)
    if in_data is not None:  # safety belt
        psj_create_pdf(obj, transforms)
        psj_create_html(obj, transforms)
    return


def psj_create_pdf(obj, transforms):
    """Event handler for freshly created IPSJOfficeDocTransforms.

    Creates PDF representation of uploaded office doc on creation.
    """
    out_data = transforms.convertTo(
        'application/pdf', getattr(obj.psj_office_doc, 'data'),
        mimetype='application/vnd.oasis.opendocument.text')
    if out_data is None:
        # transform failed
        return
    new_filename = obj.psj_office_doc.filename + '.pdf'
    obj.psj_pdf_repr = NamedBlobFile(
        data=out_data.getData(), filename=new_filename)


def psj_create_html(obj, transforms):
    """Create an HTML representation of `in_data`.

    `in_data` is supposed to be the binary content of an office
    document.

    `transforms` are the portal transforms.
    """
    out_data = transforms.convertTo(
        'text/html', getattr(obj.psj_office_doc, 'data'),
        mimetype='application/vnd.oasis.opendocument.text')
    obj.psj_md5 = md5.new(getattr(obj.psj_office_doc, 'data')).hexdigest()
    if out_data is None:
        # transform failed
        return
    new_filename = obj.psj_office_doc.filename + '.html'
    html = out_data.getData()
    obj.psj_html_repr = NamedBlobFile(
        data=html, filename=new_filename)
    for name in obj.keys():
        # make sure all old extra-files (images, etc.) are
        # deleted.
        del obj[name]
    for name, subdata in out_data.getSubObjects().items():
        name = name.decode('utf8')
        if name.lower()[-4:] in (u'.png', u'.jpg', u'.gif', u'.tif'):
            new_name = obj.invokeFactory('Image', name)
        else:
            new_name = obj.invokeFactory('File', name)
        new_context = obj[new_name]
        new_context.file = NamedBlobFile(subdata, filename=name)


@grok.subscribe(IPSJOfficeDocTransformer, IObjectModifiedEvent)
def update_representations(obj, event):
    """Update office representations of file connected to context obj.
    """
    md5_sum = md5.new(getattr(obj.psj_office_doc, 'data', '')).hexdigest()
    if md5_sum != getattr(obj, 'psj_md5', ''):
        psj_create_reprs(obj)


class PSJSubjectIndexing(PSJMetadataBase):
    """A behavior providing fields for subject indexing.
    """
    implements(IPSJSubjectIndexing)

    psj_subject_group = DCFieldProperty(
        IPSJSubjectIndexing['psj_subject_group'],
        get_name='psj_subject_group',
        )

    psj_ddc_geo = DCFieldProperty(
        IPSJSubjectIndexing['psj_ddc_geo'],
        get_name='psj_ddc_geo',
        )

    psj_ddc_sach = DCFieldProperty(
        IPSJSubjectIndexing['psj_ddc_sach'],
        get_name='psj_ddc_sach',
        )

    psj_ddc_zeit = DCFieldProperty(
        IPSJSubjectIndexing['psj_ddc_zeit'],
        get_name='psj_ddc_zeit',
        )

    psj_gnd_id = DCFieldProperty(
        IPSJSubjectIndexing['psj_gnd_id'],
        get_name='psj_gnd_id',
        )

    psj_free_keywords = DCFieldProperty(
        IPSJSubjectIndexing['psj_free_keywords'],
        get_name='psj_free_keywords',
        )

    psj_sw_zeit = DCFieldProperty(
        IPSJSubjectIndexing['psj_sw_zeit'],
        get_name='psj_sw_zeit',
        )

    @property
    def psj_gnd_terms(self):
        if not hasattr(self, 'psj_gnd_id'):
            return []
        conf = queryUtility(IRedisStoreConfig, name="psj.content.redis-GND")
        if conf is None:
            return []
        redis_source = RedisSource(
            host=conf['host'], port=conf['port'], db=conf['db'])
        result = []
        for elem in self.psj_gnd_id:
            try:
                val = redis_source.getTerm(elem)
                result.append(val.title)
            except LookupError:
                # id not in store.
                result.append(elem)
        return result

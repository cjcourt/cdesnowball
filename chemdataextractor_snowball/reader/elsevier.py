# -*- coding: utf-8 -*-
"""
chemdataextractor.reader.elsevier
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Readers for documents from Elsevier.
by Callum Court
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from lxml import etree
from lxml.etree import XMLParser
from ..text import get_encoding
from .markup import HtmlReader, XmlReader
from ..scrape.clean import clean, Cleaner
import six
class ElsevierHtmlReader(HtmlReader):
    """Reader for HTML documents from Elsevier."""

    cleaners = [clean]

    root_css = 'html'
    title_css = 'h1.sVTitle'
    heading_css = 'h2, h3, h4, h5, h6, .title1, span.title2, span.title3'
    table_css = 'dd.table, dl.table'
    table_caption_css = '.caption'
    figure_css = 'dl.figure, dd.figure'
    figure_caption_css = '.caption'
    citation_css = 'ul.reference'
    ignore_css = 'a[href="JavaScript:void(0);"], a.ref sup'

    def detect(self, fstring, fname=None):
        """"""
        if fname and not (fname.endswith('.html') or fname.endswith('.htm')):
            return False
        if b'<link rel="canonical" href="http://www.sciencedirect.com/' in fstring:
            return True
        return False


clean_elsevier_xml = Cleaner(strip_xpath='.//ns7:inf | .//ns7:bold | .//ns7:sup | .//ns7:italic', kill_xpath='.//ns7:cross-refs | .//ns7:cross-ref', fix_whitespace=False)

def fix_elsevier_xml_whitespace(document):
    """ Fix tricky xml tags"""
    # space hsp correctly
    for el in document.xpath('//ns7:hsp'):
        parent = el.getparent()
        previous = el.getprevious()
        if el.tag == '{http://www.elsevier.com/xml/common/dtd}italic' and parent.tag == '{http://www.elsevier.com/xml/common/dtd}inf':
            continue
        # We can't strip the root element!
        if parent is None:
            continue
        # Append the text to previous tail (or parent text if no previous), ensuring newline if block level
        if el.text and isinstance(el.tag, six.string_types):
            if previous is None:
                if parent.text:
                    if parent.text.endswith(' '):
                        parent.text = (parent.text or '') + '' + el.text
                    else:
                        parent.text = (parent.text or '') + ' ' + el.text
            else:
                if previous.tail:
                    if previous.tail.endswith(' '):
                        previous.tail = (previous.tail or '') + '' + el.text
                    else:
                        previous.tail = (previous.tail or '') + ' ' + el.text
        # Append the tail to last child tail, or previous tail, or parent text, ensuring newline if block level
        if el.tail:
            if len(el):
                last = el[-1]
                last.tail = (last.tail or '') + el.tail
            elif previous is None:
                if el.tail.startswith(' '):
                    parent.text = (parent.text or '') + '' + el.tail
                else:
                    parent.text = (parent.text or '') + ' ' + el.tail
            else:
                if el.tail.startswith(' '):
                    previous.tail = (previous.tail or '') + '' + el.tail
                else:
                    previous.tail = (previous.tail or '') +  ' ' + el.tail

        index = parent.index(el)
        parent[index:index + 1] = el[:]

    return document


class ElsevierXmlReader(XmlReader):
    """Reader for Elsevier XML documents."""

    # Namespaces
    dc = etree.FunctionNamespace("http://purl.org/dc/elements/1.1/")
    ns0 = etree.FunctionNamespace("http://www.elsevier.com/xml/svapi/article/dtd")
    ns4 = etree.FunctionNamespace("http://www.elsevier.com/xml/xocs/dtd")
    ns6 = etree.FunctionNamespace("http://www.elsevier.com/xml/ja/dtd")
    ns7 = etree.FunctionNamespace("http://www.elsevier.com/xml/common/dtd")
    ns8 = etree.FunctionNamespace("http://www.elsevier.com/xml/common/cals/dtd")
    ns10 = etree.FunctionNamespace("http://www.elsevier.com/xml/common/struct-bib/dtd")
    dc.prefix = 'dc'
    ns0.prefix = 'ns0'
    ns4.prefix = 'ns4'
    ns6.prefix = 'ns6'
    ns7.prefix = 'ns7'
    ns8.prefix = 'ns8'
    ns10.prefix = 'ns10'

    root_css = 'ns0|full-text-retrieval-response'
    title_css = 'ns7|title'
    heading_css = 'ns7|section-title'
    table_css = 'ns7|table'
    table_caption_css = 'ns7|table ns7|caption'
    table_head_row_css = 'ns8|thead ns8|row'
    table_body_row_css = 'ns8|tbody ns8|row'
    table_cell_css = 'ns7|entry'
    figure_css = 'ns7|figure'
    figure_caption_css = 'ns7|caption'
    reference_css = 'ns7|cross-ref[refid^="bib"], ns7|cross-refs'
    citation_css = 'ns7|bib-reference'
    ignore_css = 'ns0|objects, ns0|scopus-id, ns0|scopus-eid, ns4|meta, ns0|coredata, ns6|item-info, ns7|author-group, ns7|abstract[class^="author-highlights"], ns7|keywords, ns7|label'

    cleaners = [clean, fix_elsevier_xml_whitespace, clean_elsevier_xml]

    def detect(self, fstring, fname=None):
        """"""
        if fname and not (fname.endswith('.xml') or fname.endswith('.nxml')):
            return False
        if b'full-text-retrieval-response' in fstring:
            return True
        return False


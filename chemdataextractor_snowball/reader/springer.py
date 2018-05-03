# -*- coding: utf-8 -*-
"""
chemdataextractor.reader.springer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Readers for documents from Springer.
by Callum Court
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from lxml import etree
from lxml.html import HTMLParser
from lxml.etree import XMLParser
from ..text import get_encoding
from .markup import HtmlReader, XmlReader
from ..scrape.clean import clean, Cleaner

clean_springer_html = Cleaner(fix_whitespace=True, strip_xpath='.//sub | .//em')

class SpringerMaterialsHtmlReader(HtmlReader):
    """Reader for HTML documents from SpringerMaterials."""

    cleaners = [clean, clean_springer_html]

    root_css = 'html'
    citation_css = 'span[class="CitationRef"]'
    title_css = 'title'
    heading_css = 'h2, h3, h4, h5, h6, .title1, span.title2, span.title3'
    table_css = 'div[class="Table"]'
    table_caption_css = 'div[class="Table"] p'
    table_head_row_css = 'thead tr'
    table_body_row_css = 'tbody tr'
    table_cell_css = 'th, td'
    ignore_css = 'sub, sup, em[class^="EmphasisTypeItalic "], li[class="article-metrics__item"], div[class="CitationContent"]'

    def detect(self, fstring, fname=None):
        """"""
        if fname and not (fname.endswith('.html') or fname.endswith('.htm')):
            return False
        if b'<a class="footer-copyright_link" href="http://www.springernature.com"' in fstring or b'<meta content="SpringerLink"' in fstring:
            return True
        return False

    def _make_tree(self, fstring):
        root = etree.fromstring(fstring, parser=HTMLParser(encoding=get_encoding(fstring, guesses='utf-8', is_html=True)))
        return root



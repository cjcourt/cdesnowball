# -*- coding: utf-8 -*-
"""
chemdataextractor.scrape.acs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tools for scraping documents from The American Chemical Society.

:copyright: Copyright 2017 by Callum Court.
:license: MIT, see LICENSE file for more details.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import logging
import re

from bs4 import UnicodeDammit
from lxml.etree import fromstring
from lxml.html import HTMLParser, Element
import six

from ...text.processors import Substitutor, Discard, Chain, LStrip, RStrip, LAdd
from ...text.normalize import normalize
from .. import BLOCK_ELEMENTS
from ..clean import Cleaner, clean
from ..entity import Entity, DocumentEntity, EntityList
from ..fields import StringField, EntityField, UrlField
from ..scraper import RssScraper, SearchScraper, UrlScraper
from ..selector import Selector
from selenium import webdriver
from time import sleep

log = logging.getLogger(__name__)

#: Map placeholder text to unicode characters.
CHAR_REPLACEMENTS = [
    ('\[?\[1 with combining macron\]\]?', '1\u0304'),
    ('\[?\[2 with combining macron\]\]?', '2\u0304'),
    ('\[?\[3 with combining macron\]\]?', '3\u0304'),
    ('\[?\[4 with combining macron\]\]?', '4\u0304'),
    ('\[?\[approximate\]\]?', '\u2248'),
    ('\[?\[bottom\]\]?', '\u22a5'),
    ('\[?\[c with combining tilde\]\]?', 'C\u0303'),
    ('\[?\[capital delta\]\]?', '\u0394'),
    ('\[?\[capital lambda\]\]?', '\u039b'),
    ('\[?\[capital omega\]\]?', '\u03a9'),
    ('\[?\[capital phi\]\]?', '\u03a6'),
    ('\[?\[capital pi\]\]?', '\u03a0'),
    ('\[?\[capital psi\]\]?', '\u03a8'),
    ('\[?\[capital sigma\]\]?', '\u03a3'),
    ('\[?\[caret\]\]?', '^'),
    ('\[?\[congruent with\]\]?', '\u2245'),
    ('\[?\[curly or open phi\]\]?', '\u03d5'),
    ('\[?\[dagger\]\]?', '\u2020'),
    ('\[?\[dbl greater-than\]\]?', '\u226b'),
    ('\[?\[dbl vertical bar\]\]?', '\u2016'),
    ('\[?\[degree\]\]?', '\xb0'),
    ('\[?\[double bond, length as m-dash\]\]?', '='),
    ('\[?\[double bond, length half m-dash\]\]?', '='),
    ('\[?\[double dagger\]\]?', '\u2021'),
    ('\[?\[double equals\]\]?', '\u2267'),
    ('\[?\[double less-than\]\]?', '\u226a'),
    ('\[?\[double prime\]\]?', '\u2033'),
    ('\[?\[downward arrow\]\]?', '\u2193'),
    ('\[?\[fraction five-over-two\]\]?', '5/2'),
    ('\[?\[fraction three-over-two\]\]?', '3/2'),
    ('\[?\[gamma\]\]?', '\u03b3'),
    ('\[?\[greater-than-or-equal\]\]?', '\u2265'),
    ('\[?\[greater, similar\]\]?', '\u2273'),
    ('\[?\[gt-or-equal\]\]?', '\u2265'),
    ('\[?\[i without dot\]\]?', '\u0131'),
    ('\[?\[identical with\]\]?', '\u2261'),
    ('\[?\[infinity\]\]?', '\u221e'),
    ('\[?\[intersection\]\]?', '\u2229'),
    ('\[?\[iota\]\]?', '\u03b9'),
    ('\[?\[is proportional to\]\]?', '\u221d'),
    ('\[?\[leftrightarrow\]\]?', '\u2194'),
    ('\[?\[leftrightarrows\]\]?', '\u21c4'),
    ('\[?\[less-than-or-equal\]\]?', '\u2264'),
    ('\[?\[less, similar\]\]?', '\u2272'),
    ('\[?\[logical and\]\]?', '\u2227'),
    ('\[?\[middle dot\]\]?', '\xb7'),
    ('\[?\[not equal\]\]?', '\u2260'),
    ('\[?\[parallel\]\]?', '\u2225'),
    ('\[?\[per thousand\]\]?', '\u2030'),
    ('\[?\[prime or minute\]\]?', '\u2032'),
    ('\[?\[quadruple bond, length as m-dash\]\]?', '\u2263'),
    ('\[?\[radical dot\]\]?', ' \u0307'),
    ('\[?\[ratio\]\]?', '\u2236'),
    ('\[?\[registered sign\]\]?', '\xae'),
    ('\[?\[reverse similar\]\]?', '\u223d'),
    ('\[?\[right left arrows\]\]?', '\u21C4'),
    ('\[?\[right left harpoons\]\]?', '\u21cc'),
    ('\[?\[rightward arrow\]\]?', '\u2192'),
    ('\[?\[round bullet, filled\]\]?', '\u2022'),
    ('\[?\[sigma\]\]?', '\u03c3'),
    ('\[?\[similar\]\]?', '\u223c'),
    ('\[?\[small alpha\]\]?', '\u03b1'),
    ('\[?\[small beta\]\]?', '\u03b2'),
    ('\[?\[small chi\]\]?', '\u03c7'),
    ('\[?\[small delta\]\]?', '\u03b4'),
    ('\[?\[small eta\]\]?', '\u03b7'),
    ('\[?\[small gamma, Greek, dot above\]\]?', '\u03b3\u0307'),
    ('\[?\[small kappa\]\]?', '\u03ba'),
    ('\[?\[small lambda\]\]?', '\u03bb'),
    ('\[?\[small micro\]\]?', '\xb5'),
    ('\[?\[small mu \]\]?', '\u03bc'),
    ('\[?\[small nu\]\]?', '\u03bd'),
    ('\[?\[small omega\]\]?', '\u03c9'),
    ('\[?\[small phi\]\]?', '\u03c6'),
    ('\[?\[small pi\]\]?', '\u03c0'),
    ('\[?\[small psi\]\]?', '\u03c8'),
    ('\[?\[small tau\]\]?', '\u03c4'),
    ('\[?\[small theta\]\]?', '\u03b8'),
    ('\[?\[small upsilon\]\]?', '\u03c5'),
    ('\[?\[small xi\]\]?', '\u03be'),
    ('\[?\[small zeta\]\]?', '\u03b6'),
    ('\[?\[space\]\]?', ' '),
    ('\[?\[square\]\]?', '\u25a1'),
    ('\[?\[subset or is implied by\]\]?', '\u2282'),
    ('\[?\[summation operator\]\]?', '\u2211'),
    ('\[?\[times\]\]?', '\xd7'),
    ('\[?\[trade mark sign\]\]?', '\u2122'),
    ('\[?\[triple bond, length as m-dash\]\]?', '\u2261'),
    ('\[?\[triple bond, length half m-dash\]\]?', '\u2261'),
    ('\[?\[triple prime\]\]?', '\u2034'),
    ('\[?\[upper bond 1 end\]\]?', ''),
    ('\[?\[upper bond 1 start\]\]?', ''),
    ('\[?\[upward arrow\]\]?', '\u2191'),
    ('\[?\[varepsilon\]\]?', '\u03b5'),
    ('\[?\[x with combining tilde\]\]?', 'X\u0303'),
]

#: Substitutor that replaces ACS escape codes with the actual unicode character
acs_substitute = Substitutor(CHAR_REPLACEMENTS)


class AcsSearchDocument(Entity):
    """Document information from ACS search results page."""
    dois = StringField('//div[@class="articleBox "]/@doi', xpath=True, all=True)
    titles = StringField('//div[@class="hlFld-Title"]', xpath=True, all=True)
    authors = StringField('//span[@class="articleEntryAuthorsLinks"]', xpath=True, all=True)
    journals = StringField('//span[@class="notInJournal"]', xpath=True, all=True)
    publication_date = StringField('//div[@class="epubdate"]', xpath=True, all=True)
    page_numbers = StringField('//span[@class="articlePageRange"]', xpath=True)
    html_urls = UrlField('a[title="View the Full Text HTML"]::attr("href")', all=True)
    pdf_urls = UrlField('a[title="Download the PDF Full Text"]::attr("href")', all=True)
    number_of_results = StringField('//div[@class="paginationStatus"]', xpath=True)
    number_of_results_pages = StringField('//a[@class="lastPage"]', xpath=True)
    process_html_urls = LAdd('http://pubs.acs.org')

class AcsSearchScraper(SearchScraper):
    """Scraper for ACS search results."""

    entity = AcsSearchDocument

    def perform_search(self, query, page):
        log.debug('Processing query: %s' % query)
        http_string = 'http://pubs.acs.org/action/doSearch?' + 'AllField=' + query + '&pageSize=100' + '&startPage=' + str(page) + '&sortBy=relevancy'
        driver = webdriver.Firefox()
        driver.get(http_string)
        sleep(10)
        response = driver.page_source
        driver.quit()
        return response

    def run(self, query, page=1):
        """ Override from SearchScraper class """
        query = self.process_query(query)
        if not query:
            return
        response = self.perform_search(query, page)
        selector = Selector.from_html_text(response)
        entities = []
        for root in self.get_roots(selector):
            entity = self.entity(root)
            entity = self.process_entity(entity)
            if entity:
                entities.append(entity)
        return EntityList(*entities)

class AcsLandingDocument(DocumentEntity):
    """ Document information for ACS landing page """
    title = StringField('//meta[@property="og:title"]/@content', xpath=True)
    description = StringField('//meta[@property="og:description"]/@content', xpath=True)
    url = UrlField('//meta[@property="og:url"]/@content', xpath=True)
    process_title = Chain(acs_substitute, normalize)

class AcsLandingScraper(UrlScraper):
    """Scraper for ACS Landing pages."""
    entity = AcsLandingDocument

class AcsImage(Entity):
    """Embedded image. Includes both Schemes and Figures."""
    label = StringField('div[id^="fig"]::attr("id"), img[alt="Abstract Image"]::attr("alt"), div[id^="sch"]::attr("id")')
    caption = StringField('div[class="caption hlFld-FigureCaption"]')
    url = UrlField('img::attr("src")')
    process_caption = Chain(acs_substitute, normalize)

class AcsTableData(Entity):
    rows = StringField('td', all=True)

class AcsTable(Entity):
    """Table within document."""
    title = StringField('div[class="title2"]')
    column_headings = StringField('th', all=True)
    data = EntityField(AcsTableData, 'tbody', all=True)
    caption = StringField('div[class="footnote"]', all = True)

class AcsHtmlDocument(DocumentEntity):
    """Scraper of document information from ACS html papers"""
    abstract = StringField('.articleBody_abstractText')
    language = StringField('//meta[@name="dc.Language"]/@content', xpath=True)
    journal = StringField('//cite', xpath=True)
    copyright = StringField('//div[@id="artCopyright"]',xpath=True)
    paragraphs = StringField('//div[@class="NLM_p"] | //div[@class="NLM_p last"]', xpath=True, all=True)
    headings = StringField('//h2[@id]', xpath=True, all=True)
    sub_headings = StringField('//span[@class="title3"]', xpath=True, all=True)
    tables = EntityField(AcsTable, '.NLM_table-wrap', all=True)
    figures = EntityField(AcsImage,'.figure', all=True)
    supplementary_information_url = UrlField('a[href^="http://pubs.acs.org/doi/suppl/"]::attr("href")')
    citations = StringField('//div[@class="NLM_citation"]', xpath=True, all=True)
    description = StringField('//meta[@name="dc.Description"]/@content', xpath=True)


    def process_figures(self, value):
        """Filter those without 'Fig' in label, they are Schemes."""
        return value if value.label and 'Fig' in value.label else None

    def process_schemes(self, value):
       """Filter those without 'Scheme' in label, they are Figures."""
       return value if value.label and 'Scheme' in value.label else None

class AcsHtmlScraper(UrlScraper):
    """ Scraper for ACS html paper pages """
    entity = AcsHtmlDocument




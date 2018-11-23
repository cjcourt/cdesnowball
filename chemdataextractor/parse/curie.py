# -*- coding: utf-8 -*-
"""
 Curie parse tool for chemdataextractor.parse.Curie
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Curie temperature text parser
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import logging
import re

from .cem import cem, chemical_label, lenient_chemical_label, solvent_name
from .common import lbrct, dt, rbrct
from ..utils import first, last
from ..model import Compound, CurieTemperature
from .actions import merge, join
from .base import BaseParser
from .elements import W, I, R, Optional, Any, OneOrMore, Not, ZeroOrMore
from lxml import etree

log = logging.getLogger(__name__)

delim = R('^[:;\.,]$')

# Values, units and ranges
units = (Optional(W('°')) + Optional(R('^[CFK]\.?$')) | W('K\.?') | W('mK\.?'))('units').add_action(merge)
joined_range = R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?$')('value').add_action(merge)
spaced_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() + (R('^[\-±–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(merge)
to_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() + (I('to') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(join)
temp_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)
temp_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)
temp = (temp_range | temp_value)('value')
temp_and_units = (Optional(lbrct).hide() + temp + units + Optional(rbrct).hide())('ct')


# Generic specifier for a curie temperature as Tc
black_list = (I('Θ/TC') | I('T/TC'))
tc_specifier = (Not(black_list) + (I('TC')| R('^\[?T(c|C|Curie|curie)[1-2]?\]?$')))

# Any specifier for curie temperature
ct_specifier = (tc_specifier | (I('curie') | I('Curie') | I('ferromagnetic'))
                + Optional(I('ordering')).hide() + Optional(I('phase')) + Optional(I('transition')) \
                + (R('^temperature[s]?$') | R('^temp[\.]?$') | I('point') | I('value')) \
                + Optional(delim).hide() \
                + Optional(I('θ')).hide() \
                + Optional(I('of')) \
                + Optional(I('up') + I('to')).hide() \
                + Optional(delim).hide() \
                + Optional(lbrct | I('[')).hide() + Optional(tc_specifier) + Optional(rbrct | I(']')).hide() \
                + Optional(delim).hide())

# Standard curie temperature prefix phrase
prefix = (Optional(I('the') | I('a') | I('an') | I('its') | I('with')).hide()\
         + ct_specifier \
         + Optional(I('varies') + I('from')).hide() \
         + Optional(W('=') | W('~') | W('≈') | W('≃') |  I('of') | I('was') | I('is') | I('at') | I('near') | I('above') | I('below')).hide() \
         + Optional(I('reported') | I('determined')).hide()\
         + Optional(I('as') | (I('to') + I('be'))).hide() \
         + Optional(I('in') + I('the') + I('range')).hide()\
         + Optional(I('of') | I('about') | I('approximately') | I('around') | (I('high') + I('as')) | (I('higher') + I('than'))).hide())

ct_specifier_and_value = (prefix + Optional(delim).hide() + Optional(lbrct | I('[')).hide() + Optional(ct_specifier).hide() + temp + units + Optional(rbrct | I(']')).hide())('ct')

bracket_any = (lbrct | I('[')) + OneOrMore(Not(ct_specifier_and_value) + Not(rbrct) + Any()) + (rbrct | I(']'))

# Phrases in which the CEM is before the curie temperature specifier
cem_before_ct_and_value_phrase = (Optional(cem | lenient_chemical_label) \
                 + Optional(delim).hide() + Optional(I('samples') | I('system')) \
                 + Optional(I('that') | I('which') | I('was') | I('since') | I('the')).hide()
                 + Optional(I('typically')).hide()\
                 + Optional(I('exhibits') | I('exhibiting')| R('^show[s]*$')| I('demonstrates')| I('undergoes') | I('has') | I('having') | I('determined') | I('with') |I('where')| I('orders') | (I('is') + Optional(I('classified') + I('as')))).hide()\
                 + Optional(I('reported') + I('to') + I('have')).hide() + Optional(I('disorder') | I('have')| I('from')).hide() \
                 + Optional(I('characterized') + I('by'))
                 + Optional(I('a') | I('an') | I('are') | I('two') | I('multiple')).hide()\
                 + Optional(I('transition') + I('to') + I('a')).hide() \
                 + Optional(I('naturally') | I('still')).hide() \
                 + Optional(I('first') + Optional(I('-')).hide() + I('order')).hide()
                 + Optional(Optional(I('G')) + Optional(I('-')) + I('type') + Optional((I('2') | I('II') | I('two')))).hide()\
                 + Optional(I('3D')).hide() \
                 + Optional(lbrct) + Optional(I('helical') | R('canted') | I('complex') | (I('well') + R('\-') +I('known'))).hide() + Optional(rbrct)\
                 + Optional(I('ferromagnetic') | I('magnetic') | I('multiferroic') | I('ferroelectric')).hide() + Optional(lbrct).hide() + Optional(I('FM')) + Optional(rbrct).hide()
                 + Optional(I('ferromagnetically') | I('magnetically') | I('metamagnet') | I('metamagnetic') | I('ferromagnet')).hide() \
                 + Optional(I('ferromagnetism')).hide() + Optional(lbrct).hide() + Optional(I('FM-II')) + Optional(rbrct).hide()\
                 + Optional(I('peak') | (Optional(I('ground')) + I('state'))).hide() \
                 + Optional(I('compound') | I('material')).hide() \
                 + Optional(delim).hide()\
                 + Optional(I('at') + I('temperatures')).hide() \
                 + Optional(I('behavior')| I('behaviour') | (I('ordering') | I('ordered') | I('phase') + I('transition')) | R('^transition[s]*$') | (I('order-disorder') + I('transition'))).hide()\
                 + Optional(I('to') + I('paramagnetic')).hide() \
                 + Optional(I('occurs') | (I('is') + I('displayed')))\
                 + Optional(I('much')) \
                 + Optional(I('below') | I('at') | I('above') | I('around') | I('near') | I('lower') | I('higher') | I('to')).hide()\
                 + Optional(I('where') | I('having') | I('with') | I('that') | I('and')).hide()\
                 + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() \
                 + Optional(lbrct).hide() + ct_specifier_and_value + Optional(rbrct).hide() \
                 )('ct_phrase')

# Phrases where the specifier is given before the CEM and values
ct_before_cem_and_value_phrase = (prefix \
                 + Optional(I('of') | I('in') | I('for')).hide() \
                 + Optional(I('bulk') | I('powdered') | I('doped') | I('the')).hide() \
                 + Optional(cem | lenient_chemical_label) \
                 + Optional(I('is') | I('were') | I('occurs') | I('of') | (I('can') + I('be') + I('assigned') + Optional(I('at') | I('to')))).hide() \
                 + Optional(I('in') + I('the') + I('range') + I('of')) \
                 + Optional(I('about')) \
                 + Optional(lbrct) \
                 + (ct_specifier_and_value | temp_and_units)
                 + Optional(rbrct))('ct_phrase')

# Phrases where the CEM is given after both the specifier and the value
cem_after_ct_and_value_phrase = (Optional(I('below') | I('at')) \
                                 + ct_specifier_and_value \
                                 + Optional((I('has') + I('been') + I('found') + I('for')) | (I('was') + I('observed'))) \
                                 + Optional(I('in') | I('for') | I('of'))\
                                 + Optional(I('the')) \
                                 + Optional(R('^[:;,]$')) \
                                 + Optional(I('bulk') | I('powdered') | I('doped') | (I('thin') + I('film')))
                                 + Optional(I('ferromagnetic') | I('multiferroic')) + Optional(lbrct) + Optional(I('FM')) + Optional(rbrct) \
                                 + Optional(cem | lenient_chemical_label) \
                                 )('ct_phrase')

value_specifier_cem_phrase = (Optional(I('of')) \
                              + temp_and_units \
                              + Optional(delim) \
                              + Optional(I('which')) \
                              + Optional(I('likely') | I('close') | (I('can') + I('be'))) \
                              + Optional(I('corresponds') | I('associated')) \
                              + Optional(I('to') | I('with') | I('is')) \
                              + Optional(I('the')) \
                              + I('Curie') + I('temperature') \
                              + Optional(I('of') | I('in')) \
                              + (cem | lenient_chemical_label))('ct_phrase')

# Rules for finding multiple values in a single sentence
temp_with_optional_unit = (Optional(lbrct).hide() + temp + Optional(units) + Optional(rbrct).hide())('ct')
list_of_temperatures = (temp_with_optional_unit + Optional(OneOrMore(delim + temp_with_optional_unit)) + I('and') + temp_and_units)('temp_list')
list_of_cems = (cem + Optional(OneOrMore(delim + cem)) + I('and') + cem + Optional(I('compounds')))('cem_list')


# List of curie temperature values
multiple_ct_phrase = (prefix
                      + Optional(I('are'))
                      + Optional(I('equal'))
                      + Optional(I('found'))
                      + Optional(I('to') + Optional(I('be')))
                      + Optional(I('of'))
                      + list_of_temperatures)('ct_phrase')

ct_phrase = (multiple_ct_phrase | cem_after_ct_and_value_phrase | ct_before_cem_and_value_phrase | cem_before_ct_and_value_phrase | value_specifier_cem_phrase )

class CtParser(BaseParser):
    """"""
    root = ct_phrase

    def interpret(self, result, start, end):
        #print(etree.tostring(result))
        if result.tag == 'temp_list':
            last_unit = first(last(result.xpath('./ct_phrase/ct')).xpath('./units/text()'))
            for ct in result.xpath('./ct_phrase/ct'):
                c = Compound()
                unit = first(ct.xpath('./units/text()'))
                if unit:
                    curie_temp = CurieTemperature(value=first(ct.xpath('./value/text()')),
                                                units=unit)
                else:
                    curie_temp = CurieTemperature(value=first(ct.xpath('./value/text()')),
                                                units=last_unit)
                c.curie_temperatures = [curie_temp]
                yield c

        elif result.tag == 'respectively_phrase':
            # Create curie temperatures
            last_unit = first(last(result.xpath('./ct_phrase/temp_list/ct')).xpath('./units/text()'))
            idx = 0
            for ct in result.xpath('./ct_phrase/temp_list/ct'):
                unit = first(ct.xpath('./units/text()'))
                if unit:
                    curie_temp = CurieTemperature(value=first(ct.xpath('./value/text()')),
                                                units=unit)
                else:
                    curie_temp = CurieTemperature(value=first(ct.xpath('./value/text()')),
                                                units=last_unit)
                compounds = result.xpath('./cem_list/cem')
                cem_el = compounds[idx]
                c = Compound(names=cem_el.xpath('./name/text()'),
                             labels=cem_el.xpath('./label/text()'),
                             curie_temperatures=[curie_temp])
                idx += 1
                yield c

        elif result.tag == 'multi_cem_phrase':
            curie_temp = CurieTemperature(value=first(result.xpath('./ct/value/text()')),
                                        units=first(result.xpath('./ct/units/text()')))
            for cem_el in result.xpath('./cem_list/cem'):
                c = Compound(names=cem_el.xpath('./name/text()'),
                             labels=cem_el.xpath('./label/text()'),
                             curie_temperatures=[curie_temp])
                yield c

        elif result.tag == 'single_cem_multiple_ct_phrase':
            c = Compound(names=result.xpath('./cem/name/text()'),
                         labels=result.xpath('./cem/label/text()'))
            curie_temps = []
            for ct in result.xpath('./temp_list/ct_phrase/ct'):
                curie_temps.append(CurieTemperature(value=first(ct.xpath('./value/text()')),
                                                  units=first(ct.xpath('./units/text()'))))

            c.curie_temperatures = curie_temps
            yield c


        elif result.tag == 'ct_phrase':
            compound = Compound(
                curie_temperatures=[
                    CurieTemperature(
                        value=first(result.xpath('./ct/value/text()')),
                        units=first(result.xpath('./ct/units/text()'))
                    )
                ]
            )
            cem_el = first(result.xpath('./cem'))
            if cem_el is not None:
                compound.names = cem_el.xpath('./name/text()')
                compound.labels = cem_el.xpath('./label/text()')
            yield compound


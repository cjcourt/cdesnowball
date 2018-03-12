# -*- coding: utf-8 -*-
"""
 Neel parse tool for chemdataextractor.parse.Neel
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Neel temperature text parser
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
from ..model import Compound, NeelTemperature
from .actions import merge, join
from .base import BaseParser
from .elements import W, I, R, T, Optional, Any, OneOrMore, Not, ZeroOrMore, Group

from lxml import etree

log = logging.getLogger(__name__)

delim = R('^[:;\.,]$')

# Values, units and ranges
units = (Optional(W('°')) + Optional(R('^[CFK]\.?$')) | W('K\.?') | W('mK\.?'))('units').add_action(merge)
joined_range = R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?[\-––-−~∼˜]\d+(\.\d+)?(\(\d\))?$')('value').add_action(merge)
spaced_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() + (R('^[\-±–−~∼˜]$') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(merge)
to_range = (R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') + Optional(units).hide() + (I('to') + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$') | R('^[\+\-–−]\d+(\.\d+)?(\(\d\))?$')))('value').add_action(join)
temp_range = (Optional(R('^[\-–−]$')) + (joined_range | spaced_range | to_range))('value').add_action(merge)
temp_value = (Optional(R('^[~∼˜\<\>\≤\≥]$')) + Optional(R('^[\-\–\–\−±∓⨤⨦±]$')) + R('^[\+\-–−]?\d+(\.\d+)?(\(\d\))?$'))('value').add_action(merge)
temp = (temp_range | temp_value)('value')
temp_and_units = (Optional(lbrct).hide() + temp + units + Optional(rbrct).hide())('nt')
temp_with_optional_unit = (Optional(lbrct).hide() + temp + Optional(units) + Optional(rbrct).hide())('nt')

# black list some common post codes in U.S
postcode_blacklist = ((I('TN') + (R('^37931$') | R('^37831$') | R('^37996$'))))
tn_specifier = Not(postcode_blacklist) + R('^T(n|N|Neel|Néel|neel|néel)(\(K\))?[1-2]?$')
# This is a hacky way of doing this
nt_ratio = ((I('T') | I('θ')) + I('/') + I('TN') + (W('=') | W('>')) + R('^(\d.?)+$'))('nt_ratio_phrase')

# Any specifier for Neel temperature
nt_specifier = (tn_specifier | (((I('Néel') | I('Neel') | I('Neél') | I('antiferromagnetic')) + Optional(R('[\']'))) + Optional(I('ordering')).hide() + Optional(I('phase')) + Optional(I('transition')) + (R('^temperature[s]?$') | R('^temp[\.]?$') | I('point') | I('value')))) \
                + Optional(delim).hide() \
                + Optional(I('θ')).hide() \
                + Optional(I('of')).hide() \
                + Optional(I('up') + I('to')).hide() \
                + Optional(delim).hide() \
                + Optional(lbrct).hide() + Optional(tn_specifier) + Optional(rbrct).hide() \
                + Optional(delim).hide()

# Standard Néel temperature prefix phrase
prefix = (Optional(I('the') | I('a') | I('an') | I('its') | I('with') | I('at') | I('low') | I('high')).hide()\
         + nt_specifier \
         + Optional(I('varies') + I('from')).hide() \
         + Optional(W('=') | W('~') | W('≈') | W('≃') |  I('of') | I('was') | I('is') | I('at') | I('near') | I('above') | I('below') | I('were')).hide() \
         + Optional(I('reported') | I('determined')).hide()\
         + Optional(I('as') | I('for') | (I('to') + I('be'))).hide() \
         + Optional(I('this') + I('material')) \
         + Optional(I('in') + I('the') + I('range')).hide()\
         + Optional(I('of') | I('about') | I('around') | I('approximately') | (I('high') + I('as'))).hide())

nt_specifier_and_value = (prefix + Optional(delim).hide() + Optional(lbrct) + Optional(nt_specifier).hide() + temp + units + Optional(rbrct))('nt')



bracket_any = lbrct + OneOrMore(Not(nt_specifier_and_value) + Not(rbrct) + Any()) + rbrct

# Phrases in which the CEM is before the neel temperature specifier
cem_before_nt_and_value_phrase = (Optional((cem | lenient_chemical_label )) \
                 + Optional(delim).hide() + Optional(I('samples') | I('system') | I('stoichiometry')) \
                 + Optional(I('that') | I('which') | I('was') | I('since') | I('the')).hide()
                 + Optional(I('studied') + I('experimentally')).hide() \
                 + Optional(I('typically')).hide()\
                 + Optional(I('exhibits') | I('exhibiting')| R('^show[s]*$')| I('demonstrates')| I('undergoes') | I('has') | I('having') | I('determined') | I('with') |I('where')| I('orders') | (I('is') + Optional(I('classified') + I('as')))).hide()\
                 + Optional(I('reported') + I('to') + I('have')).hide() + Optional(I('disorder') | I('have')| I('from')).hide() \
                 + Optional(I('known') + I('to') + I('be')) \
                 + Optional(I('a') | I('an') | I('are') | I('two') | I('multiple')).hide()\
                 + Optional(I('transition') + Optional(I('to') + (I('a') | I('an')))).hide() \
                 + Optional(I('naturally') | I('still')).hide() \
                 + Optional(I('first') + Optional(I('-')).hide() + I('order')).hide()
                 + Optional(Optional(I('G')) + Optional(I('-')) + I('type') + Optional((I('2') | I('II') | I('two')))).hide()\
                 + Optional(I('3D')).hide() \
                 + Optional(lbrct) + Optional(I('helical') | R('canted') | I('complex') | I('metallic')).hide() + Optional(rbrct)\
                 + Optional(I('antiferromagnetic') | I('anti-ferromagnetic') | I('magnetic') | I('multiferroic')).hide() + Optional(lbrct).hide() + Optional(I('AFM')) + Optional(rbrct).hide()
                 + Optional(I('antiferromagnetically') | I('anti-ferromagnetically') | I('magnetically') | I('metamagnet') | I('metamagnetic') | I('anti-ferromagnet') | I('antiferromagnet')).hide() \
                 + Optional(I('antiferromagnetism') | I('anti-ferromagnetism')).hide() + Optional(lbrct).hide() + Optional(I('AFM-II')) + Optional(rbrct).hide()\
                 + Optional(I('peak') | (Optional(I('ground')) + I('state'))).hide() \
                 + Optional(I('compound') | I('material') | I('order') | I('ordering')).hide() \
                 + Optional(delim).hide()\
                 + Optional(I('at') + I('temperatures')).hide() \
                 + Optional(I('behavior')| I('behaviour') | (I('ordering') | I('ordered') | I('phase') + I('transition')) | R('^transition[s]*$') | (I('order-disorder') + I('transition'))).hide()\
                 + Optional(I('to') + I('paramagnetic')).hide() \
                 + Optional(I('occurs') | (I('is') + I('displayed')))\
                 + Optional(I('below') | I('at') | I('above') | I('around') | I('near') | I('lower') | I('higher') | I('to')).hide()\
                 + Optional(I('where') | I('having') | I('with') | I('that')).hide()\
                 + Optional(delim).hide() + Optional(bracket_any).hide() + Optional(delim).hide() \
                 + Optional(lbrct).hide() + nt_specifier_and_value + Optional(rbrct).hide() \
                 )('nt_phrase')

# Phrases where the specifier is given before the CEM and values
nt_before_cem_and_value_phrase = (prefix \
                 + Optional(I('of') | I('in') | I('for')).hide() \
                 + Optional(I('the')) \
                 + Optional(I('bulk') | I('powdered') | I('doped')).hide() \
                 + Optional((cem | lenient_chemical_label)) \
                 + Optional(I('is') | I('were') | I('was') | I('occurs') | I('of') | (I('can') + I('be') + I('assigned') + Optional(I('at') | I('to')))).hide() \
                 + Optional(I('about') | I('at') | I('below')).hide() \
                 + (nt_specifier_and_value | temp_and_units))('nt_phrase')

# Phrases where the CEM is given after both the specifier and the value
cem_after_nt_and_value_phrase = (Optional(I('below') | I('at') | I('to') | I('e.g.') | I('but')).hide() \
                                 + Optional(delim) \
                                 + Optional(I('its')) \
                                 + (nt_specifier_and_value) \
                                 + Optional(delim) \
                                 + Optional((I('has') | I('have')) + I('been') + I('found') + I('for')).hide() \
                                 + Optional(I('in') | I('for') | I('of')).hide()\
                                 + Optional(I('the')).hide() \
                                 + Optional(R('^[:;,]$')).hide() \
                                 + Optional(I('bulk') | I('powdered') | I('doped') | (I('thin') + I('film'))).hide()
                                 + Optional(I('antiferromagnetic') | I('anti-ferromagnetic') | I('multiferroic')).hide() + Optional(lbrct).hide() + Optional(I('AFM')) + Optional(rbrct).hide()
                                 + Optional((cem | lenient_chemical_label)) \
                                 )('nt_phrase')

value_specifier_cem_phrase = (Optional(lbrct) + temp_and_units + Optional(rbrct) \
                              + Optional(I('likely') | I('close')) \
                              + Optional(I('corresponds')) \
                              + Optional(I('to')) \
                              + prefix
                              + Optional(I('of')) \
                              + (cem  | lenient_chemical_label))('nt_phrase')



# Rules for finding multiple values in a single sentence
list_of_temperatures = (temp_with_optional_unit + Optional(OneOrMore(delim + temp_with_optional_unit)) + Optional(delim) + I('and') + temp_and_units)('nt_phrase')
list_of_cems = (cem + Optional(OneOrMore(delim + cem)) + Optional(delim) + I('and') + cem)('cem_list')

# List of neel temperature values
multiple_nt_phrase = (prefix + list_of_temperatures)('temp_list')

## RESPECTIVELY PHRASE
cem_before_nt_respecitvely_phrase = (list_of_cems + Optional(delim) + Optional(I('typically')).hide()\
                        + Optional(I('exhibits') | I('exhibiting')  | I('exhibit')| R('^show[s]*$')| I('demonstrates')| I('undergoes') | I('has') | I('having') | I('determined') | I('with') |I('where')| I('orders') | (I('is') + Optional(I('classified') + I('as')))).hide()\
                        + Optional(I('reported') + I('to') + I('have')).hide() + Optional(I('disorder') | I('have')| I('from')).hide() \
                        + Optional(I('a') | I('an') | (I('are') + Optional(I('all'))) | I('two') | I('multiple')).hide()\
                        + Optional(I('transition') + I('to') + I('a')).hide() \
                        + Optional(I('naturally') | I('still')).hide() \
                        + Optional(I('first') + Optional(I('-')).hide() + I('order')).hide()
                        + Optional(Optional(I('G')) + Optional(I('-')) + I('type') + Optional((I('2') | I('II') | I('two')))).hide()\
                        + Optional(I('3D')).hide() \
                        + Optional(lbrct) + Optional(I('helical') | R('canted') | I('complex')).hide() + Optional(rbrct)\
                        + Optional(I('antiferromagnetic') | I('anti-ferromagnetic') | I('magnetic') | I('multiferroic')).hide() + Optional(lbrct).hide() + Optional(I('AFM')) + Optional(rbrct).hide()
                        + Optional(I('antiferromagnetically') | I('anti-ferromagnetically') | I('magnetically') | I('metamagnet') | I('metamagnetic') | I('anti-ferromagnet') | I('antiferromagnet')).hide() \
                        + Optional(I('antiferromagnetism') | I('anti-ferromagnetism')).hide() + Optional(lbrct).hide() + Optional(I('AFM-II')) + Optional(rbrct).hide()\
                        + Optional(I('peak') | (Optional(I('ground')) + I('state'))).hide() \
                        + Optional(I('compound') | I('material')).hide() \
                        + Optional(delim).hide()\
                        + Optional(I('at') + I('temperatures')).hide() \
                        + Optional(I('behavior')| I('behaviour') | (I('ordering') | I('ordered') | I('phase') + I('transition')) | R('^transition[s]*$') | (I('order-disorder') + I('transition'))).hide()\
                        + Optional(I('to') + I('paramagnetic')).hide() \
                        + Optional(I('occurs') | (I('is') + I('displayed')))\
                        + Optional(I('below') | I('at') | I('above') | I('around') | I('near') | I('lower') | I('higher') | I('to')).hide()\
                        + Optional(I('where') | I('having') | I('with') | I('that')).hide() + multiple_nt_phrase + Optional(delim) + Optional(I('respectively')))('respectively_phrase')

nt_before_cem_respectively_phrase = (multiple_nt_phrase + \
                                    Optional(((I('have') + I('been')) | I('were')) + I('found')) + \
                                    Optional(I('of') | I('in') | I('for')) + \
                                    list_of_cems + Optional(delim) + Optional(I('respectively')))('respectively_phrase')

respectively_phrase = (nt_before_cem_respectively_phrase | cem_before_nt_respecitvely_phrase)



## list of cems with a single neel temperature
cems_first = (list_of_cems + Optional(I('all')) + Optional((I('show') | I('exhibit') | I('have'))) + nt_specifier_and_value )('multi_cem_phrase')
nt_first = (nt_specifier_and_value + Optional(I('have') + I('been') + I('found')) + \
                        Optional(I('in') | I('for')) + \
                        list_of_cems + Optional(I('respectively')))('multi_cem_phrase')

multi_cem_single_nt_phrase = (cems_first | nt_first)

# single cem with multiple neel temps
single_cem_multiple_nt_phrase = ((cem | lenient_chemical_label) + Optional(delim).hide() + Optional(I('samples') | I('system')) \
                 + Optional(I('that') | I('which') | I('was') | I('since') | I('the')).hide()
                 + Optional(I('typically')).hide()\
                 + Optional(I('exhibits') | I('exhibiting')| R('^show[s]*$')| I('demonstrates')| I('undergoes') | I('has') | I('having') | I('determined') | I('with') |I('where')| I('orders') | (I('is') + Optional(I('classified') + I('as')))).hide()\
                 + Optional(I('reported') + I('to') + I('have')).hide() + Optional(I('disorder') | I('have')| I('from')).hide() \
                 + Optional(I('a') | I('an') | I('are') | I('two') | I('multiple')).hide()\
                 + Optional(I('transition') + I('to') + I('a')).hide() \
                 + Optional(I('naturally') | I('still')).hide() \
                 + Optional(I('first') + Optional(I('-')).hide() + I('order')).hide()
                 + Optional(Optional(I('G')) + Optional(I('-')) + I('type') + Optional((I('2') | I('II') | I('two')))).hide()\
                 + Optional(I('3D')).hide() \
                 + Optional(lbrct) + Optional(I('helical') | R('canted') | I('complex')).hide() + Optional(rbrct)\
                 + Optional(I('antiferromagnetic') | I('anti-ferromagnetic') | I('magnetic') | I('multiferroic')).hide() + Optional(lbrct).hide() + Optional(I('AFM')) + Optional(rbrct).hide()
                 + Optional(I('antiferromagnetically') | I('anti-ferromagnetically') | I('magnetically') | I('metamagnet') | I('metamagnetic') | I('anti-ferromagnet') | I('antiferromagnet')).hide() \
                 + Optional(I('antiferromagnetism') | I('anti-ferromagnetism')).hide() + Optional(lbrct).hide() + Optional(I('AFM-II')) + Optional(rbrct).hide()\
                 + Optional(I('peak') | (Optional(I('ground')) + I('state'))).hide() \
                 + Optional(I('compound') | I('material')).hide() \
                 + Optional(delim).hide()\
                 + Optional(I('at') + I('temperatures')).hide() \
                 + Optional(I('behavior')| I('behaviour') | (I('ordering') | I('ordered') | I('phase') + I('transition')) | R('^transition[s]*$') | (I('order-disorder') + I('transition'))).hide()\
                 + Optional(I('to') + I('paramagnetic')).hide() \
                 + Optional(I('occurs') | (I('is') + I('displayed')))\
                 + Optional(I('below') | I('at') | I('above') | I('around') | I('near') | I('lower') | I('higher') | I('to')).hide()\
                 + Optional(I('where') | I('having') | I('with') | I('that')).hide() + multiple_nt_phrase)('single_cem_multiple_nt_phrase')


#nt_phrase = (nt_ratio | respectively_phrase | multi_cem_single_nt_phrase |single_cem_multiple_nt_phrase | multiple_nt_phrase | cem_after_nt_and_value_phrase | nt_before_cem_and_value_phrase | cem_before_nt_and_value_phrase | value_specifier_cem_phrase)
nt_phrase =  (nt_ratio | multiple_nt_phrase | cem_after_nt_and_value_phrase | nt_before_cem_and_value_phrase | cem_before_nt_and_value_phrase | value_specifier_cem_phrase)


class NtParser(BaseParser):
    """"""
    root = nt_phrase

    def interpret(self, result, start, end):
        #print(etree.tostring(result))
        if result.tag == 'respectively_phrase':
            # Create neel temperatures
            last_unit = first(last(result.xpath('./temp_list/nt_phrase/nt')).xpath('./units/text()'))
            idx = 0
            for nt in result.xpath('./temp_list/nt_phrase/nt'):
                unit = first(nt.xpath('./units/text()'))
                if unit:
                    neel_temp = NeelTemperature(value=first(nt.xpath('./value/text()')),
                                                units=unit)
                else:
                    neel_temp = NeelTemperature(value=first(nt.xpath('./value/text()')),
                                                units=last_unit)
                compounds = result.xpath('./cem_list/cem')
                cem_el = compounds[idx]
                c = Compound(names=cem_el.xpath('./name/text()'),
                             labels=cem_el.xpath('./label/text()'),
                             neel_temperatures = [neel_temp])
                idx += 1
                yield c

        elif result.tag == 'temp_list':
            last_unit = first(last(result.xpath('./nt_phrase/nt')).xpath('./units/text()'))
            for nt in result.xpath('./nt_phrase/nt'):
                c = Compound()
                unit = first(nt.xpath('./units/text()'))
                if unit:
                    neel_temp = NeelTemperature(value=first(nt.xpath('./value/text()')),
                                                units=unit)
                else:
                    neel_temp = NeelTemperature(value=first(nt.xpath('./value/text()')),
                                                units=last_unit)
                c.neel_temperatures = [neel_temp]
                yield c

        elif result.tag == 'multi_cem_phrase':
            neel_temp = NeelTemperature(value=first(result.xpath('./nt/value/text()')),
                                        units=first(result.xpath('./nt/units/text()')))
            for cem_el in result.xpath('./cem_list/cem'):
                c = Compound(names=cem_el.xpath('./name/text()'),
                             labels=cem_el.xpath('./label/text()'),
                             neel_temperatures=[neel_temp])
                yield c

        elif result.tag == 'single_cem_multiple_nt_phrase':
            c = Compound(names=result.xpath('./cem/name/text()'),
                         labels=result.xpath('./cem/label/text()'))
            neel_temps = []
            for nt in result.xpath('./temp_list/nt_phrase/nt'):
                neel_temps.append(NeelTemperature(value=first(nt.xpath('./value/text()')),
                                                    units=first(nt.xpath('./units/text()'))))

            c.neel_temperatures = neel_temps
            yield c

        elif result.tag == 'nt_ratio_phrase':
            yield Compound()

        elif result.tag == 'nt_phrase':
            compound = Compound(
                neel_temperatures=[
                    NeelTemperature(
                        value=first(result.xpath('./nt/value/text()')),
                        units=first(result.xpath('./nt/units/text()'))
                    )
                ]
            )
            cem_el = first(result.xpath('./cem'))
            if cem_el is not None:
                compound.names = cem_el.xpath('./name/text()')
                compound.labels = cem_el.xpath('./label/text()')
            yield compound











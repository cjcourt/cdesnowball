# -*- coding: utf-8 -*-
"""
chemdataextractor.relex.pattern.py
Extraction pattern object
"""
import re
from .utils import compound_wildcard_regex


class Pattern:
    """ Pattern object, fundamentally the same as a phrase"""

    def __init__(self, entities=None,
                 elements=None,
                 label=None,
                 relations=None,
                 sentences=None,
                 order=None,
                 specifier_regex=None,
                 value_regex=None,
                 unit_regex=None):
        """

        :param entities: Dict containing the associated entities
        :param elements: Dict containing tokens and vectors for this pattern
        :param label: string associating this pattern to a cluster
        :param relations: known relations
        :param sentences: known sentences
        :param order: order of entities in the pattern
        :param specifier_regex:
        :param value_regex:
        :param unit_regex:
        """
        self.cluster_label = label
        self.elements = {'prefix': elements['prefix'],
                         'middles': elements['middles'],
                         'suffix': elements['suffix']
                         }

        self.entities = entities
        self.number_of_entities = len(self.entities)
        self.order = order
        self.specifier_regex = specifier_regex
        self.value_regex = value_regex
        self.unit_regex = unit_regex
        self.regex = self.as_regex()
        self.confidence = self.determine_confidence(relations, sentences)

    def as_regex(self):
        """ Convert the pattern to a regular expression """
        output_regex = r'\b'
        prefix_tokens = [re.escape(i) for i in self.elements['prefix']['1']['tokens']]
        output_regex += r'\s?'.join(prefix_tokens) + r'\s?'
        if output_regex.startswith((r'\b\.', r'\b\,', r'\b\(', r'\b\=')):
            output_regex = output_regex[2:]

        for i in range(0, len(self.order)):
            if self.order[i] == '0':
                output_regex += compound_wildcard_regex
            elif self.order[i] == '1':
                output_regex += self.value_regex
            elif self.order[i] == '2':
                output_regex += self.specifier_regex
            elif self.order[i] == '3':
                output_regex += self.unit_regex

            if str(i+1) in self.elements['middles'].keys():
                output_regex += r'\s?'
                middle_tokens = [re.escape(i) for i in self.elements['middles'][str(i+1)]['tokens']]
                output_regex += r'\s?'.join(middle_tokens)
                output_regex += r'\s?'

        suffix_tokens = [re.escape(i) for i in self.elements['suffix']['1']['tokens']]
        output_regex += r'\s?' + r'\s?'.join(suffix_tokens)

        return output_regex

    def as_string(self):
        """
        :return: Output Patter as a string
        """
        output_string = ''
        output_string += ' '.join(self.elements['prefix']['1']['tokens']) + ' '
        output_string += self.entities[0][1] + ' '
        for i in range(0, self.number_of_entities - 1):
            if str(i+1) in self.elements['middles'].keys():
                output_string += ' '.join(self.elements['middles'][str(i + 1)]['tokens']) + ' '
            output_string += self.entities[i + 1][1] + ' '
        output_string += ' '.join(self.elements['suffix']['1']['tokens'])

        # first replace troublesome characters
        output_string = output_string.replace('\n', ' ')
        output_string = output_string.replace(u'\u00A0', ' ')
        output_string = output_string.replace(u'\u2212', '-')
        output_string = output_string.replace(u'\u2009 ', ' ')

        output_string.replace('  ', ' ')
        return output_string

    def determine_confidence(self, relations, sentences):
        """ Determine the confidence score of this pattern
            do this by using the pattern regex on all known sentences and
            attempting to extrat known relation confidence is then the ratio
            of correct extractions to incorrect ones

            :param relations: list of relations to evaluate
            :param sentences: list of derived setences
        """
        # TODO: Currently using regular expressions, could we instead use NER?

        total = 0
        correct = 0

        for s in sentences:
            matches = [m for m in re.finditer(self.regex, s, re.IGNORECASE)]
            if matches:
                total += len(matches)
                for m in matches:
                    retrieved_entities_list = []
                    for i in range(0, len(self.order)):
                        if self.order[i] == '0':
                            retrieved_entities_list.append(m.group(i+1))
                        elif self.order[i] == '1':
                            retrieved_entities_list.append(m.group(i+1))
                        elif self.order[i] == '2':
                            retrieved_entities_list.append(m.group(i+1))
                        elif self.order[i] == '3':
                            retrieved_entities_list.append(m.group(i+1))
                    retrieved_relations = []
                    number_of_units = self.order.count('3')
                    for i in self.entities:
                        for j in self.entities:
                            if i[1].startswith('<CEM') and j[1].startswith('<VALUE') and i[1][4] == j[1][6] and number_of_units == 1:
                                retrieved_relations.append([retrieved_entities_list[self.entities.index(i)], retrieved_entities_list[self.entities.index(j)], retrieved_entities_list[self.order.index('3')]])
                            elif i[1].startswith('<CEM') and j[1].startswith('<VALUE') and i[1][4] == j[1][6] and number_of_units != 1:
                                for k in self.entities:
                                    if k[1].startswith('<UNIT') and k[1][5] == j[1][6] and k[1][5] == i[1][4]:
                                        retrieved_relations.append([retrieved_entities_list[self.entities.index(i)], retrieved_entities_list[self.entities.index(j)], retrieved_entities_list[self.entities.index(k)]])
                    for relation in relations:
                        for rr in retrieved_relations:
                            if relation.compound == rr[0].lstrip(' ').rstrip(' ') and relation.value == rr[1].lstrip(' ').rstrip(' ') and relation.units == rr[2].lstrip(' ').rstrip(' '):
                                correct += (1.0/len(retrieved_relations))
        if total > 0:
            confidence = float(correct/total)
        else:
            confidence = 0
        return confidence

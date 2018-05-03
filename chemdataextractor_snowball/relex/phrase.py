# -*- coding: utf-8 -*-
"""
chemdataextractor.relex.phrase
Phrase object

"""
import re


class Phrase:
    def __init__(self, sentence=None, matches=None):
        """
        :param sentence: String of the sentence used to create phrase(s)
        :param matches: Dict containing relations and the associated compound/value/unit/specifier regex matches
        """
        self.cluster_assignments = set()  # Set of cluster labels, describing which clusters this belongs to
        self.full_sentence = None  # string
        self.number_of_entities = None
        self.elements = {'prefix': {},  # {'tokens': [], 'vector': []}
                         'middles': {},
                         'suffix': {}
                         }
        self.entities = []  # list of lists [[<STR>, <CEM>], ...]
        self.order = None  # String telling the entity order
        if sentence and matches:
            self.create(sentence, matches)

    def create(self, sentence, matches):
        """ Create a phrase from known matches"""
        compounds = matches['compounds']
        values = matches['values']
        specifiers = matches['specifiers']
        units = matches['units']
        self.number_of_entities = len(compounds) + len(values) + len(specifiers) + len(units)
        number_of_middles = self.number_of_entities - 1

        # Determine the order of the entities
        compound_tuples = [[m[0], '<CEM' + str(m[1]) + '>', m[1]] for m in compounds]
        value_tuples = [[m[0], '<VALUE' + str(m[1]) + '>', m[1]] for m in values]
        specifier_tuples = [[m[0], '<SPECIFIER' + str(m[1]) + '>', m[1]] for m in specifiers]
        unit_tuples = [[m[0], '<UNIT' + str(m[1]) + '>', m[1]] for m in units]
        entity_list = compound_tuples + value_tuples + specifier_tuples + unit_tuples

        sorted_entity_list = sorted(entity_list, key=lambda t: t[0].start())

        self.entities = [[m[0].group().lstrip(' ').rstrip(' '), m[1], m[2]] for m in sorted_entity_list]

        self.order = ''
        for e in sorted_entity_list:
            if e[1].startswith('<CEM'):
                self.order += '0'
            elif e[1].startswith('<VALUE'):
                self.order += '1'
            elif e[1].startswith('<SPECIFIER'):
                self.order += '2'
            elif e[1].startswith('<UNIT'):
                self.order += '3'

        splitting_regex = r"[\w]+|[^\s\w]"

        # Prefix is everything before the first entity - take the one token before
        t = {'tokens': re.findall(splitting_regex, sentence[:sorted_entity_list[0][0].start()], re.UNICODE)[-1:], 'vector': None}
        self.elements['prefix']['1'] = t
        # first middle is everything between the first and second etc
        for i in range(0, number_of_middles):
            t = {'tokens': re.findall(splitting_regex, sentence[sorted_entity_list[i][0].end():sorted_entity_list[i+1][0].start()], re.UNICODE), 'vector': None}
            self.elements['middles'][str(i + 1)] = t

        # suffix everything after the last entity - take the one word after
        t = {'tokens': re.findall(splitting_regex, sentence[sorted_entity_list[number_of_middles][0].end():], re.UNICODE)[:1], 'vector': None}
        self.elements['suffix']['1'] = t

        output_string = ''
        output_string += ' '.join(self.elements['prefix']['1']['tokens']) + ' '
        output_string += self.entities[0][0] + ' '
        for i in range(0, self.number_of_entities - 1):
            if str(i + 1) in self.elements['middles'].keys():
                if len(self.elements['middles'][str(i+1)]['tokens']) != 0:
                    output_string += ' '.join(self.elements['middles'][str(i + 1)]['tokens']) + ' '
            output_string += self.entities[i + 1][0] + ' '
        output_string += ' '.join(self.elements['suffix']['1']['tokens'])

        #replace troublesome characters
        # TODO: is this needed here??
        output_string = output_string.replace('\n', ' ')
        output_string = output_string.replace(u'\u00A0', ' ')  # Possibly a hidden non breaking space
        output_string = output_string.replace(u'\u2212', '-')
        output_string = output_string.replace(u'\u2009 ', ' ')

        output_string.replace('  ', ' ')
        output_string.replace('  ', ' ')
        self.full_sentence = output_string
        return

    def reset_vectors(self):
        """ Set all element vectors to None"""
        for element in self.elements:
            for element_num in self.elements[element].keys():
                self.elements[element][element_num]['vector'] = None
        return

    def as_tokens(self):
        """
        :return: Phrase object as a list of tokens
        """
        output_list = [self.elements['prefix']['1']['tokens'], self.entities[0][1]]
        for i in range(0, self.number_of_entities - 1):
            output_list.append(self.elements['middles'][str(i+1)]['tokens'])
            output_list.append(self.entities[i+1][1])
        output_list.append(self.elements['suffix']['1']['tokens'])
        return output_list

    def as_string(self):
        """

        :return: phrase object as a string
        """
        output_string = ''
        output_string += ' '.join(self.elements['prefix']['1']['tokens']) + ' '
        output_string += self.entities[0][1] + ' '
        for i in range(0, self.number_of_entities - 1):
            if str(i+1) in self.elements['middles'].keys():
                output_string += ' '.join(self.elements['middles'][str(i + 1)]['tokens']) + ' '
            output_string += self.entities[i + 1][1] + ' '
        output_string += ' '.join(self.elements['suffix']['1']['tokens'])

        # replace troublesome characters
        output_string = output_string.replace('\n', ' ')
        output_string = output_string.replace(u'\u00A0', ' ')  # Possibly a hidden non breaking space
        output_string = output_string.replace(u'\u2212', '-')
        output_string = output_string.replace(u'\u2009 ', ' ')

        output_string.replace('  ', ' ')

        return output_string

    def retrieve_relations(self):
        """ Use the entity tags to recover the related entities from this phrase """
        retrieved_relations = []
        number_of_units = self.order.count('3')
        # print(number_of_units)
        for i in self.entities:
            # print(i)
            for j in self.entities:
                # print(j)
                if i[1].startswith('<CEM') and j[1].startswith('<VALUE') and i[1][4] == j[1][6] and number_of_units == 1:
                    unit_index = self.order.index('3')
                    retrieved_relations.append([i[0], j[0], self.entities[unit_index][0]])
                elif i[1].startswith('<CEM') and j[1].startswith('<VALUE') and i[1][4] == j[1][6] and number_of_units != 1:
                    for k in self.entities:
                        if k[1].startswith('<UNIT') and k[1][5] == j[1][6] and k[1][5] == i[1][4]:
                            retrieved_relations.append([i[0], j[0], k[0]])
        print(retrieved_relations)
        return retrieved_relations

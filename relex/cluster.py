# -*- coding: utf-8 -*-
"""
chemdataextractor.relex.cluster
Cluster of phrase objects and associated cluster dictionaries
"""
from collections import OrderedDict
from .pattern import Pattern
import numpy as np
from scipy import spatial



def mode_rows(a):
    """
    Find the modal row of a 2d array
    :param a: The 2d array to process
    :type a: np.array()
    :return: The most frequent row
    """
    a = np.ascontiguousarray(a)
    void_dt = np.dtype((np.void, a.dtype.itemsize * np.prod(a.shape[1:])))
    _, ids, count = np.unique(a.view(void_dt).ravel(),
                              return_index=True,
                              return_counts=True)
    largest_count_id = ids[count.argmax()]
    most_frequent_row = a[largest_count_id]
    return most_frequent_row


class Cluster:
    """
    Base Snowball Cluster
    """
    def __init__(self, label=None,
                 update_param=None,
                 minimum_match_score=None,
                 specifier_regex=None,
                 value_regex=None,
                 unit_regex=None):
        """
        :param label: String to identify this cluster
        :type label: str
        :param update_param: Learning rate for Pattern confidence
        :type  update_param: float
        :param minimum_match_score: Minimum match required to join this cluster
        :type minimum_match_score: float
        :param specifier_regex: Specifier extraction regex
        :type specifier_regex: str
        :param value_regex: Value extraction regex
        :type value_regex: str
        :param unit_regex: unit extraction regex
        :type unit_regex: str
        """
        self.label = label
        self.phrases = []
        self.pattern = None
        self.entities = []
        self.dictionaries = {'prefix': {},
                             'middles': {},
                             'suffix': {}}

        self.minimum_match_score = minimum_match_score  # Minimum similarity score required to match to this cluster
        self.cluster_update_param = update_param
        self.order = None
        self.specifier_regex = specifier_regex
        self.unit_regex = unit_regex
        self.value_regex = value_regex

    def add(self, phrase):
        """ Add phrase to this cluster,
        update the word dictionary and token weights

        :param phrase: The phrase to add to the cluster
        :type phrase: chemdataextractor.relex.phrase.Phrase
        """
        self.phrases.append(phrase)
        self.order = phrase.order
        self.entities = phrase.entities
        self.update_dictionaries(phrase)
        self.update_weights()
        return

    def update_dictionaries(self, phrase):
        """Update all dictionaries in this cluster

        :param phrase: The phrase to update
        :type phrase: chemdataextractor.relex.phrase.Phrase

        """
        # Go through the prefix, middle and suffix elements
        for element in phrase.elements.keys():  # Prefix, middles, suffix
            for element_key in phrase.elements[element].keys():  # 1, 2, etc
                if element_key not in self.dictionaries[element].keys():
                    self.dictionaries[element][element_key] = {'token dict': OrderedDict(),
                                                               'unique words': [],  # Which words appear once
                                                               'total words': 0,  # counter
                                                               'total recurring words': 0}  # counter
                # add the tokens
                self.add_tokens(self.dictionaries[element][element_key], phrase.elements[element][element_key]['tokens'])
        return

    @staticmethod
    def add_tokens(dictionary, tokens):
        """ Add specified tokens to the specified dictionary

        :param dictionary: The dictionary to add tokens to
        :type dictionary: OrderedDict
        :param tokens: tokens to add
        :type: list of str

        """
        for token in tokens:
            if token not in dictionary['token dict'].keys():
                dictionary['total words'] += 1
                dictionary['token dict'][token] = [1.0, 0]  # [frequeny, weight]
            else:
                dictionary['total words'] += 1
                dictionary['token dict'][token][0] += 1
        return

    def update_weights(self):
        """ Update the weights on each token in the phrases"""
        for element in self.dictionaries.keys():
            for element_key in self.dictionaries[element].keys():
                for token in self.dictionaries[element][element_key]['token dict'].keys():
                    freq = self.dictionaries[element][element_key]['token dict'][token][0]
                    weight = freq / self.dictionaries[element][element_key]['total words']
                    self.dictionaries[element][element_key]['token dict'][token] = [freq, weight]

        return

    def update_pattern(self, relations, sentences):
        """ Use the cluster phrases to generate a new centroid extraction Pattern object

        :param relations: List of known relations to look for
        :type: list of Relation objects
        :param sentences: List of sentences known to contain relations
        :type sentences: List of str"""

        vectors = {'prefix': {'1': []},
                   'middles': {'1': []},
                   'suffix': {'1': []}}

        pattern_elements = {'prefix': {},
                            'middles': {},
                            'suffix': {}}

        # Create a dict of vectors for all phrases in the cluster
        for phrase in self.phrases:
            self.vectorise(phrase)
            for element in phrase.elements.keys():  # Prefix, ,iddles, suffix
                for element_key in phrase.elements[element].keys():  ## 1, 2,3..
                    if element_key not in vectors[element].keys():
                        vectors[element][element_key] = [phrase.elements[element][element_key]['vector']]
                    elif phrase.elements[element][element_key]['vector']:
                        vectors[element][element_key].append(phrase.elements[element][element_key]['vector'])
                    else:
                        vectors[element][element_key] = [[]]

        # Find the centroid vector for prefix, middles, suffix
        for element in vectors.keys():
            for element_key in vectors[element].keys():
                element_array = np.array(vectors[element][element_key])

                # compute mode of vectors
                if element_array.any():
                    element_mode = mode_rows(element_array)
                else:
                    element_mode = np.array([])
                # find points closest to the mode
                medoid_idx = spatial.KDTree(element_array).query(element_mode)[1]
                pattern_elements[element][element_key] = self.phrases[medoid_idx].elements[element][element_key]

        # Create the new pattern
        self.pattern = Pattern(entities=self.entities,
                               elements=pattern_elements,
                               label=self.label,
                               relations=relations,
                               sentences=sentences,
                               order=self.order,
                               specifier_regex=self.specifier_regex,
                               value_regex=self.value_regex,
                               unit_regex=self.unit_regex)

        return

    def vectorise(self, phrase):
        """ Convert phrase prefix, middles and suffix into
        a normalised vector of weights

        :param phrase: The phrase to vectorise
        :type phrase: chemdataextractor.relex.phrase.Phrase

        """

        for element in phrase.elements.keys():
            for element_key in phrase.elements[element].keys():
                #print(element, element_key)
                element_dict = phrase.elements[element][element_key]
                #print("Dict", element_dict)
                vector = np.zeros(len(self.dictionaries[element][element_key]['token dict']))
                for token in element_dict['tokens']:
                    if token in list(self.dictionaries[element][element_key]['token dict'].keys()):
                        #print(token, "in dict")
                        token_index = list(self.dictionaries[element][element_key]['token dict'].keys()).index(token)
                        vector[token_index] = self.dictionaries[element][element_key]['token dict'][token][1]
                norm = np.linalg.norm(vector)
                if norm > 1e-15:
                    element_dict['vector'] = list((vector/np.linalg.norm(vector)))
                    #print(element_dict['vector'], len(element_dict['vector']))
                else:
                    element_dict['vector'] = list(np.zeros(len(self.dictionaries[element][element_key]['token dict'])))
                #print("Vector", element_dict['vector'])
        return

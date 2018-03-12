# -*- coding: utf-8 -*-
"""
chemdataextractor.relex.relation
Relation object, consisting of compound, value, units and confidence

"""
import re


class Relation:
    def __init__(self, compound, value, units, confidence):
        """
        :param compound: String of compound name
        :param value: String of value
        :param units: String of unit
        :param confidence: float representing confidence
        """
        self.compound = compound
        self.value = value
        self.units = units
        self.confidence = confidence
        self.phrases = []  # List of phrase objects
        self.found = False  # Wether or not this relation has any phrase objects

        self.compound_regex = r'(\b)' + re.escape(self.compound) + r'(\b)'
        self.value_regex = r'\s' + re.escape(self.value) + r'\s'

    def print(self):
        return print(self.compound, self.value, self.units)







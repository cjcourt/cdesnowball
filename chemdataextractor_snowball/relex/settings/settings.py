# -*- coding: utf-8 -*-
"""
ChemDataExtractor.relex.settings.settings.py
~~~~~~~~~~~~~~~~~
Hard coded settings for neel/curie snowball systems
"""

import os

file_dir = os.path.dirname(__file__)

# similarity thresholds
neel_tc = 0.8
neel_tsim = 0.8
curie_tc = 0.8
curie_tsim = 0.8

# Phrase similarity weightings
prefix_weight = 0.1
middle_weight = 0.8
suffix_weight = 0.1

# -*- coding: utf-8 -*-
"""
chemdataextractor.relex
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sentence level relationship extraction algorithms
"""

import os
from .load import load_snowball

this_file_dir = os.path.dirname(__file__)

# search directory for '.pkl'
snowball_systems = []

for file_name in os.listdir(this_file_dir + '/settings/'):
    if file_name.endswith('.pkl'):
        print("Loading Snowball system", file_name)
        snowball_systems.append(load_snowball(this_file_dir +
                                              '/settings/' + file_name))

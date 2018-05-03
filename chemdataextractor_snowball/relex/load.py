# -*- coding: utf-8 -*-
"""
ChemDataExtractor.relex.load.py
~~~~~~~~~~~~~~~~~
Load snowball clusters and settings from previous save

"""
import os
import pickle


def load_snowball(file_path):
    """ Load snowball configuration from pickle """
    print(file_path)
    if not os.path.isfile(file_path):
        raise FileNotFoundError('settings file missing')
    else:
        print("loading snowball", file_path)
        with open(file_path, 'rb') as f:
            return pickle.load(f)

# -*- coding: utf-8 -*-
"""
chemdataextractor.relex.train.py
Script for training the Curie and Neel snowball systems
Corpus directories can be set in .relex.settings.settings.py

"""
from .snowball import Snowball
from ..doc.document import Document
import os
import time


file_dir = os.path.dirname(__file__)


class SnowballTrainer(object):
    """
    Class for training and setting up the Snowball algorithm
    """
    def __init__(self,
                 seeds,
                 corpus,
                 tc,
                 tsim,
                 val_regex,
                 unit_regex,
                 spec_regex,
                 relationship_name
                 ):

        """

        :param seeds: List of seed tuples to train from
        :param corpus: Path to training corpus
        :param tc: Minimum confidecne threshold
        :param tsim: minimum phrase similarity threshold
        :param val_regex: value extraction regex
        :param unit_regex: unit extraction regex
        :param spec_regex: specifier regex
        """

        self._seeds = seeds
        self._corpus = corpus
        self._tc = tc
        self._tsim = tsim
        self._val_regex = val_regex
        self._unit_regex = unit_regex
        self._spec_regex = spec_regex
        self._ppty = relationship_name

    def train(self):
        t0 = time.clock()
        print("Reading training corpora")
        corpus = []
        for f in os.listdir(self._corpus):
            if f.endswith('.html') or f.endswith('.xml'):
                with open(self._corpus + f, 'rb') as d:
                    doc = Document.from_file(d)
                    corpus.append(doc)

        # Create a snowball object, pass a corpus
        #  seeds, regexes and save
        # directory
        sb = Snowball(seeds=self._seeds,
                      pperty=self._ppty,
                      specifier_regex=self._spec_regex,
                      value_regex=self._val_regex,
                      unit_regex=self._unit_regex,
                      save_dir=file_dir + '/settings/',
                      save_settings_file=self._ppty + '.pkl',
                      t_c=self._tc,
                      t_sim=self._tsim
                      )

        sb.train(corpus)

        t1 = time.clock()
        print("Trained in", t1-t0, "Seconds")
        return

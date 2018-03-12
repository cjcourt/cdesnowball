# -*- coding: utf-8 -*-
"""
chemdataextractor.relex.snowball.py
Snowball algorithm for relationship extraction

"""
import os
import pickle
import re
from .relation import Relation
from .phrase import Phrase
from .cluster import Cluster
from .utils import neel_temperature_specifier_regex, curie_temperature_specifier_regex, matches_coincide, snowball_to_cde, match

from itertools import combinations


class Snowball:
    """ Snowball algorithm """

    def __init__(self,
                 seeds,
                 pperty,
                 specifier_regex,
                 value_regex,
                 unit_regex,
                 save_dir,
                 save_settings_file,
                 settings_file_dir=None,
                 update_param=1.0,
                 t_sim=0.9,
                 t_c=0.9):
        """
        :param settings_file_dir: Directory from which to load a preset snowball
         configuration, default None
        :param seeds: List of tuples (compound, value, unit)
        :param specifier_regex: Regular expression to extract a measurement
        specifier
        :param value_regex: Regular expression to extract values
        :param unit_regex: Regular expression to extract units
        :param save_dir: Directory to save settings and files to
        :param update_param: Learning rate used to update pattern confidences
         default 1
        :param t_sim: Minimum similarity score needed to match a phrase to a
        cluster default 0.9
        :param t_c: Minimum confidence score needed to accept a relation
        default 0.9
        """
        self.seeds = seeds
        self.pperty = pperty
        self.save_dir = save_dir
        self.settings_file_dir = settings_file_dir
        self.relations = []
        self.new_relations = []
        self.candidate_relations = []
        self.candidate_phrases = []
        self.matched_sentences = []
        self.clusters = None
        self.cluster_label_counter = 0
        self.save_file_name = save_settings_file

        # Params
        self.minimum_relation_confidence = t_c
        self.update_param = update_param
        self.minimum_cluster_similarity_score = t_sim
        self.specifier_regex = specifier_regex
        self.value_regex = value_regex
        self.unit_regex = unit_regex

    def train(self, corpus):
        """ Train the Snowball system from scratch
         :param corpus: list of chemdataExtractor Document objects """
        print("Initialising seed relations...")
        self.initialise_seed_relations()

        # Parse the corpus to generate phrases
        print("Parsing corpus...")
        self.parse_corpus(corpus, training=True)
        del corpus
        # Now we have created a set of relations and found the sentences they came from
        # Generate phrase clusters and extraction patterns
        print("Clustering...")
        self.single_pass_classification()
        self.save(save_dir=self.save_dir)

        return

    def initialise_seed_relations(self):
        """ Convert seed tuples to Relations of confidence 1
            seeds have to be in the form (compound, value, unit)"""
        for seed in self.seeds:
            if len(seed) != 3:
                raise ValueError("Seed is not the correct length", seed)
            else:
                self.relations.append(Relation(seed[0], seed[1], seed[2], 1))
        return

    def parse_corpus(self, corpus, training):
        """ Process each document in the corpus
        :param corpus: List of corpus documents
        :param training: Wether or not the system is in training mode
        :type training: bool"""

        for d in corpus:
            self.parse_document(d, training)
        return

    def parse_document(self, d, training):
        """
        Parse CDE document
        :param d: CDE Document entity
        :param training: If True, we are training, else we are parsing for candidates
        :return:
        """
        # Parse each sentence with all the different relations
        for paragraph in d.paragraphs:
            for sentence in paragraph.sentences:
                self.parse_sentence(sentence, training)
        return

    def parse_sentence(self, sentence, training):
        """ Parse a CDE sentence object to find relations
        :param sentence: CDE Sentence object
        :param training: If training, generate phrases from the sentence, otherwise generate candidates
        """
        # first replace troublesome characters
        output_string = sentence.text.replace('\n', ' ')
        output_string = output_string.replace('\n', ' ')
        output_string = output_string.replace(u'\u00A0', ' ')  # Possibly a hidden non breaking space
        output_string = output_string.replace(u'\u2212', '-')
        output_string = output_string.replace(u'\u2009', ' ')
        s = output_string

        # Instantly reject this sentence if we cant find a specifier
        specifiers = [m for m in re.finditer(self.specifier_regex, s)]
        if not specifiers:
            return

        if training:
            self.generate_phrases(s)
        else:
            self.generate_candidate_phrases(sentence)

        return

    def parse_element(self, element, training):
        for sentence in element.sentences:
            self.parse_sentence(sentence, training)
        return

    def generate_phrases(self, s):
        """ Determine if a sentence contains known relations, if it does, create associated phrases
        :param s: Sentence string
        """
        # TODO: Clean this up?
        #print('Parsing sentence', s)
        matched_sentence = False  # Keep track of whether or not this sentence contains phrases
        entities = []  # list of dicts [{'relation':<Relation>, 'matches: [cem1, cem2,val1]}
        cem_counter = 0
        val_counter = 0
        spec_counter = 0
        unit_counter = 0

        for relation in self.relations:
            compound_regex = relation.compound_regex
            value_regex = relation.value_regex

            # Find the matches in the sentence
            compound_matches = [m for m in re.finditer(compound_regex, s)]
            value_matches = [m for m in re.finditer(value_regex, s)]
            specifier_matches = [m for m in re.finditer(self.specifier_regex, s)]
            unit_matches = [m for m in re.finditer(self.unit_regex, s)]

            # Only accept these units if followed by a comma, period, space, tab, semicolon or lrbrct
            # This prevents any K from being classed as a unit
            # TODO: Improve this method
            sure_unit_matches = []
            for unit_match in unit_matches:
                if unit_match.end() < len(s):
                    if s[unit_match.end()] in [',', '.', ')', ' ', '\t', ';', '']:
                        sure_unit_matches.append(unit_match)

            unit_matches = sure_unit_matches

            if compound_matches and value_matches and specifier_matches and unit_matches:
                matched_sentence = True
                relation.found = True # ??

                # ASSUMPTIONS: CEM is associated to nearest VALUE entity
                # VALUE IS ASSOCIATED TO SPECIFIER AND UNIT

                # Which matches to chose
                chosen_compound_match = None
                chosen_value_match = None
                chosen_specifier_match = None
                chosen_unit_match = None

                # Only use closest cem-value pair
                lowest_dist = 100000000
                for c_match in compound_matches:
                    for v_match in value_matches:
                            if c_match.start() < v_match.start():
                                dist = v_match.start() - c_match.end()
                            else:
                                dist = c_match.start() - v_match.end()
                            if dist < lowest_dist:
                                lowest_dist = dist
                                chosen_compound_match = c_match
                                chosen_value_match = v_match

                # Use the specifier and unit which are closest to the value
                spec_dist = 10000000
                for specifier_match in specifier_matches:
                    if specifier_match.start() < chosen_value_match.start():
                        dist = chosen_value_match.end() - specifier_match.start()
                    elif chosen_value_match.start() < specifier_match.start():
                        dist = specifier_match.end() - chosen_value_match.start()
                    if dist < spec_dist:
                        spec_dist = dist
                        chosen_specifier_match = specifier_match

                unit_dist = 10000000
                for u_match in unit_matches:
                    if u_match.start() < chosen_value_match.start():
                        dist = chosen_value_match.end() - u_match.start()
                    elif chosen_value_match.start() < u_match.start():
                        dist = u_match.end() - chosen_value_match.start()
                    if dist < unit_dist:
                        unit_dist = dist
                        chosen_unit_match = u_match

                # A single sentence may have multiple compounds associated to a single value or visa versa
                # May be a single specifier for many value-unit pairs etc
                # We need to find these cases and separate them out
                matched_compound = False
                matched_value = False
                matched_specifier = False
                matched_unit = False

                # Now we can check for multiple occurrences of compounds, values and units in our sentence
                # Initially we will have found no phrases in this sentence
                if not entities:
                    # Counters to track the number of entities in a sentence
                    cem_counter += 1
                    val_counter += 1
                    spec_counter += 1
                    unit_counter += 1
                    entities.append({'relations': [relation],
                                     'matches': {'compounds': [(chosen_compound_match, str(cem_counter))],
                                                 'values': [(chosen_value_match, str(val_counter))],
                                                 'specifiers': [(chosen_specifier_match, str(spec_counter))],
                                                 'units': [(chosen_unit_match, str(unit_counter))]}})
                else:
                    for entity_dict in entities:
                        match_dict = entity_dict['matches']
                        for compound_tuple in match_dict['compounds']:
                            if matches_coincide(compound_tuple[0], chosen_compound_match):
                                matched_compound = True

                        for value_tuple in match_dict['values']:
                            if matches_coincide(value_tuple[0], chosen_value_match):
                                matched_value = True

                        for specifier_tuple in match_dict['specifiers']:
                            if matches_coincide(specifier_tuple[0], chosen_specifier_match):
                                matched_specifier = True

                        for unit_tuple in match_dict['units']:
                            if matches_coincide(unit_tuple[0], chosen_unit_match):
                                matched_unit = True

                        # Check for all sentence cases
                        # Single compound. multiple values, specifiers and units
                        #  e.g CEM has neel temps TN = 15 K and TN = 145 K
                        if matched_compound and not matched_value and not matched_specifier and not matched_unit:
                            match_dict['values'].append((chosen_value_match, str(val_counter)))
                            match_dict['specifiers'].append((chosen_specifier_match, str(spec_counter)))
                            match_dict['units'].append((chosen_unit_match, str(unit_counter)))
                            entity_dict['relations'].append(relation)

                        # Single compound with multiple values and specifiers but a single unit
                        # e.g CEM has TN = 145 and TN = 15 K

                        elif matched_compound and not matched_value and not matched_specifier and matched_unit:
                            match_dict['values'].append((chosen_value_match, str(val_counter)))
                            match_dict['specifiers'].append((chosen_specifier_match, str(spec_counter)))
                            entity_dict['relations'].append(relation)

                        # Compound and value with multiple specifiers and multiple units? - unlikely
                        elif matched_compound and matched_value and not matched_specifier and not matched_unit:
                            match_dict['specifiers'].append((chosen_specifier_match, str(spec_counter)))
                            match_dict['units'].append((chosen_unit_match, str(unit_counter)))

                        # Compound, value, unit with multiple specifiers -  unlikely
                        elif matched_compound and matched_value and not matched_specifier and matched_unit:
                            match_dict['specifiers'].append((chosen_specifier_match, str(spec_counter)))

                        # Compound with multiple values for a single specifier
                        # e.g  CEM has neel temperatures 15 K and 145 K
                        elif matched_compound and not matched_value and matched_specifier and not matched_unit:
                            match_dict['values'].append((chosen_value_match, str(val_counter)))
                            match_dict['units'].append((chosen_unit_match, str(unit_counter)))
                            entity_dict['relations'].append(relation)

                        # Compound with multiple values for a single specifier and single unit
                        #  e.g  CEM has neel temperatures of 15 and 145 K
                        elif matched_compound and not matched_value and matched_specifier and matched_unit:
                            match_dict['values'].append((chosen_value_match, str(val_counter)))
                            entity_dict['relations'].append(relation)

                        # Single value for multiple specifiers and cems and units - unlikely
                        elif matched_value and not matched_compound and not matched_specifier and not matched_unit:
                            match_dict['compounds'].append((chosen_compound_match, str(cem_counter)))
                            match_dict['specifiers'].append((chosen_specifier_match, str(spec_counter)))
                            match_dict['units'].append((chosen_unit_match, str(unit_counter)))
                            entity_dict['relations'].append(relation)

                        # Single value and unit for multiple cems and specifiers, unlikely
                        elif matched_value and not matched_compound and not matched_specifier and matched_unit:
                            match_dict['compounds'].append((chosen_compound_match, str(cem_counter)))
                            match_dict['specifiers'].append((chosen_specifier_match, str(spec_counter)))
                            entity_dict['relations'].append(relation)

                        # Single value with multiple specifiers unit and cems unlikely
                        elif matched_value and not matched_compound and matched_specifier and not matched_unit:
                            match_dict['compounds'].append((chosen_compound_match, str(cem_counter)))
                            match_dict['units'].append((chosen_unit_match, str(unit_counter)))
                            entity_dict['relations'].append(relation)

                        # Single value, unit and specifier with multiple cems
                        #  e.g TN = 400 K has been found in cem, cem and cem

                        elif matched_value and not matched_compound and matched_specifier and matched_unit:
                            match_dict['compounds'].append((chosen_compound_match, str(cem_counter)))
                            entity_dict['relations'].append(relation)

                        # Single sprcifier for multiple compounds, values and units
                        # e.g neel temperature of 115 K, 145 K 160 K for cem cem and cem respectively
                        elif matched_specifier and not matched_compound and not matched_value and not matched_unit:
                            cem_counter += 1
                            val_counter += 1
                            unit_counter += 1
                            match_dict['compounds'].append((chosen_compound_match, str(cem_counter)))
                            match_dict['values'].append((chosen_value_match, str(val_counter)))
                            match_dict['units'].append((chosen_unit_match, str(unit_counter)))
                            entity_dict['relations'].append(relation)

                        # Single specifier for multiple compounds and values with single unit
                        # e.g cem, cem and cem have tN = 145, 115 and 40 K respectivly
                        elif matched_specifier and not matched_compound and not matched_value and matched_unit:
                            cem_counter += 1
                            val_counter += 1
                            match_dict['compounds'].append((chosen_compound_match, str(cem_counter)))
                            match_dict['values'].append((chosen_value_match, str(val_counter)))
                            entity_dict['relations'].append(relation)

                    # Else this is just a Standalone relation
                    if not matched_compound and not matched_value and not matched_specifier and not matched_unit:
                            entities.append({'relations': [relation],
                                             'matches': {'compounds': [(chosen_compound_match, str(1))],
                                                         'values': [(chosen_value_match, str(1))],
                                                         'specifiers': [(chosen_specifier_match, str(1))],
                                                         'units': [(chosen_unit_match, str(unit_counter))]}})

        # Now we have a dict containing relations and all associated matches for this sentence
        # Create phrases for each
        # Then append to the correct relations
        for e_dict in entities:
            phrase = Phrase(s, matches=e_dict['matches'])
            if matched_sentence:
                self.matched_sentences.append(phrase.full_sentence)
            for rel in e_dict['relations']:
                rel.phrases.append(phrase)
        return

    def single_pass_classification(self):
        """ Cluster the phrases using a single pass clustering algorithm
        based on phrase match scores
        """
        # Assign the first phrase of each order to its own cluster
        # Update dictionaries and patterns in that cluster
        # For each subsequent phrase, get the match score and assign to any
        # clusters in which it has a high enough score
        for relation in self.relations:
            for phrase in relation.phrases:
                if self.clusters is None:
                    #print("adding first phrase", phrase.full_sentence, "to a new cluster")
                    cluster0 = Cluster(str(self.cluster_label_counter),
                                       self.update_param,
                                       self.minimum_cluster_similarity_score,
                                       self.specifier_regex,
                                       self.value_regex,
                                       self.unit_regex)
                    phrase.cluster_assignments.add(cluster0.label)
                    cluster0.add(phrase)
                    cluster0.update_pattern(self.relations, self.matched_sentences)
                    self.clusters = [cluster0]
                else:
                    self.classify(phrase)

        return

    def classify(self, phrase):
        """
        Assign a phrase to clusters based on similarity score
        :param phrase: Phrase object
        :return:
        """
        phrase_added = False
        for cluster in self.clusters:
            if phrase in cluster.phrases:
                continue
            else:
                if phrase.order == cluster.order:
                    # vectorise the phrase using this clusters dictionary
                    cluster.vectorise(cluster.pattern)
                    cluster.vectorise(phrase)

                    similarity = match(phrase, cluster.pattern)
                    #print(similarity)
                    if similarity >= cluster.minimum_match_score:
                        phrase.cluster_assignments.add(cluster.label)
                        cluster.add(phrase)
                        cluster.update_pattern(self.relations,
                                               self.matched_sentences)
                        phrase_added = True
                    else:
                        phrase.reset_vectors()

        if phrase_added is False:
            # Create a new cluster
            self.cluster_label_counter += 1
            # create a new cluster
            new_cluster = Cluster(str(self.cluster_label_counter),
                                  self.update_param,
                                  self.minimum_cluster_similarity_score,
                                  self.specifier_regex,
                                  self.value_regex,
                                  self.unit_regex)
            phrase.cluster_assignments.add(new_cluster.label)
            new_cluster.add(phrase)
            new_cluster.update_pattern(self.relations, self.matched_sentences)
            self.clusters.append(new_cluster)
        return

    def save(self, save_dir):
        """ Write all snowball settings to file for loading later"""
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        with open(save_dir + self.save_file_name, 'wb') as f:
            pickle.dump(self, f)

        with open(save_dir + self.save_file_name[1:] + 'clusters.txt', 'w+') as f:
            s = "Cluster set contains " + str(len(self.clusters)) + " clusters."
            f.write(s + "\n")
            for c in self.clusters:
                s = "Cluster " + str(c.label) + " contains " + str(
                    len(c.phrases)) + " phrases. With order " + c.order
                f.write(s + "\n")
                for phrase in c.phrases:
                    f.write("\t " + phrase.full_sentence + "\n")
                f.write("The cluster centroid pattern is: ")
                p = c.pattern
                f.write(str(p.as_string()) + " with confidence score " + str(p.confidence) + "\n")

        with open(save_dir +self.save_file_name[1:] + 'patterns.txt', 'w+') as f:
            for c in self.clusters:
                p = c.pattern
                f.write(str(p.as_string()) + " with confidence score " + str(p.confidence) + "\n\n")

        with open(save_dir + self.save_file_name[1:] +'relations.txt', 'w+') as f:
            for r in self.relations:
                if r.found:
                    rel_str = "(" + r.compound + ", " + r.value + ", " + r.units + ", " + str(r.confidence) + ")"
                    f.write(rel_str + "\n")
                    for p in r.phrases:
                        for elem in p.as_tokens():
                            if isinstance(elem, list):
                                for el in elem:
                                    f.write(el + ' ')
                            else:
                                f.write(elem + ' ')
                        f.write('\n')
                    f.write('\n')

        with open(save_dir + self.save_file_name[1:] +'sentences.txt', 'w+') as f:
            for s in self.matched_sentences:
                f.write(s + '\n')

        return

    def records(self, element):
        """ Detect new relations from a CDE element
         :param element: CDE element e.g. paragraph"""
        records = []
        self.new_relations = []
        self.candidate_phrases = []
        self.parse_element(element, training=False)

        # Now update the system
        self.update()

        # rewrite the settings files
        self.save(save_dir=self.save_dir)

        if self.new_relations:
            print(self.new_relations)
            for nr in self.new_relations:
                d = {'Type': self.pperty, 'Names': nr.compound, 'Extracted Value': nr.value, 'Extracted Units':nr.units, 'Confidence':nr.confidence}
                records.append(snowball_to_cde(d))

        return records

    def generate_candidate_phrases(self, s):
        """
        Search the Sentence for records that contain the property type, and cems

        :param s: CDE sentence element
        :return:

        """
        # instantly reject this sentence if no cems are found
        if not s.cems:
            return
        else:
            # Generate candidates #TODO Change how this is done
            cems = s.cems
            #print(self.pperty)
            if self.pperty == 'neel_temperatures':
                properties = [rec.neel_temperatures[i] for rec in s.records for i in range(0, len(rec.neel_temperatures)) if rec.neel_temperatures and not rec.names and not rec.labels]
            elif self.pperty == 'curie_temperatures':
                properties = [rec.curie_temperatures[i] for rec in s.records for i in range(0, len(rec.curie_temperatures)) if rec.curie_temperatures and not rec.names and not rec.labels]
            else:
                raise ValueError("Property type not known")
            self.candidate_phrases = self.extract(s, cems, properties)

        return

    def extract(self, sentence, cems, properties):
        """ Extract possible candidate phrases from a sentence with marked cems and properties
        :param cems: List of Span objects representing the CEMS CDE has tagged
        :param properties: List of CDE Entities representing the detected properties in the list
        :param sentence: CDE sentence of the candidate sentence
        """
        # Some documents are retrieved as single long sentences which overloads snowball
        # Limit sentence length to avoid these cases
        if len(sentence.text) > 500:
            return []

        # first replace troublesome characters
        output_string = sentence.text.replace('\n', ' ')
        output_string = output_string.replace('\n', ' ')
        output_string = output_string.replace(u'\u00A0', ' ')  # Possibly a hidden non breaking space
        output_string = output_string.replace(u'\u2212', '-')
        output_string = output_string.replace(u'\u2009', ' ')
        sentence_str = output_string

        print("Candidate sentence", sentence_str)

        candidate_phrases = []
        compounds = []
        values = []
        units = []

        # Create compound regex matches
        for c in cems:
            for m in re.finditer(re.escape(str(c)), sentence_str):
                if m.start() == (c.start - sentence.start) and m.end() == (c.end - sentence.start):
                    compounds.append((m, 'c'))

        # value and unit regex matches
        for nt in properties:
            if nt.value:
                value_string = nt.value
                for ch in value_string:
                    index = 0
                    if ch.isdigit():
                        break
                    else:
                        value_string = value_string[:index + 1] + ' ' + value_string[index + 1:]

                for m in re.finditer(value_string, sentence_str):
                    values.append((m, 'v'))

            if nt.units:
                for m in re.finditer(nt.units, sentence_str):
                    units.append((m, 'u'))

        # Remove duplicate matches
        u_to_remove = []
        v_to_remove = []

        for i in units:
            for j in units:
                if i != j and matches_coincide(i[0], j[0]) and units.index(j) > units.index(i):
                    u_to_remove.append(units.index(j))

        u_to_remove = list(set(u_to_remove))
        for i in values:
            for j in values:
                if i != j and matches_coincide(i[0], j[0]) and values.index(j) > values.index(i):
                    v_to_remove.append(values.index(j))
        v_to_remove = list(set(v_to_remove))

        for index in sorted(u_to_remove, reverse=True):
            del units[index]
        for index in sorted(v_to_remove, reverse=True):
            del values[index]


        # specifier regex matches
        if self.pperty == 'neel_temperatures':
            spec_reg = neel_temperature_specifier_regex
        elif self.pperty == 'curie_temperatures':
            spec_reg = curie_temperature_specifier_regex
        else:
            raise ValueError("Property type not known")

        specifiers = [(m, 's') for m in re.finditer(self.specifier_regex,
                                                    sentence_str)]

        # we need combinations of all possible entities to form candidate phrases
        # Disallow cases where unit is not preceeded by any values
        # TODO: Disallow cases with more specifiers than values (?)
        # sort entities by lexical order
        sorted_entities = sorted(compounds + specifiers + values + units, key=lambda t: t[0].start())
        # Remove units that appear before values
        units_to_remove = []
        for j in sorted_entities:
            if j[1] == 'v':
                break
            elif j[1] == 'u':
                units_to_remove.append(sorted_entities.index(j))

        for index in sorted(units_to_remove, reverse=True):
            del sorted_entities[index]

        # print("Found entities", sorted_entities)
        # find all possible entity combinations that contains at least 4 entities (we cant have a phrase with less than
        # 4
        # TODO: Make faster by requiring at least one of each type?
        combs = [m for r in range(4, len(sorted_entities) + 1) for m in combinations(sorted_entities, r)]
        phrase_sets = []
        for comb in combs:
            phrase_match = {'compounds': [], 'specifiers': [], 'values': [], 'units': []}
            for i in comb:
                if i[1] == 'c':
                    phrase_match['compounds'].append((i[0], 'c'))
                elif i[1] == 's':
                    phrase_match['specifiers'].append((i[0], 's'))
                elif i[1] == 'v':
                    phrase_match['values'].append((i[0], 'v'))
                elif i[1] == 'u':
                    phrase_match['units'].append((i[0], 'u'))

            if phrase_match['compounds'] and phrase_match['specifiers'] and phrase_match['values'] and phrase_match['units']:
                phrase_sets.append(phrase_match)

        # Create phrases
        for p in phrase_sets:
            new_phrase = Phrase(sentence=sentence_str, matches=p)
            candidate_phrases.append(new_phrase)
        return candidate_phrases

    def update(self):
        """ Update patterns and learn new relations from candidate phrases"""
        best_candidate = None
        best_match_pattern = None
        best_match_score = 0
        best_candidate_confidence = 0
        best_matched_clusters = []

        # Find the best candidate phrase
        for candidate in self.candidate_phrases:
            confidence_term = 1.0
            match_pattern = None
            match_score = 0
            matched_clusters = []
            # Compare candidate to all clusters
            for cluster in self.clusters:
                pattern = cluster.pattern
                if candidate.order == pattern.order:
                    cluster.vectorise(candidate)
                    cluster.vectorise(pattern)
                    similarity = match(candidate, pattern)
                    if similarity >= self.minimum_cluster_similarity_score:
                        confidence_term *= (1.0 - similarity*pattern.confidence)
                        matched_clusters.append(cluster.label)
                    if similarity > match_score:
                        match_pattern = pattern
                        match_score = similarity
            confidence = 1 - confidence_term
            if confidence >= self.minimum_relation_confidence:
                if confidence > best_candidate_confidence:
                    best_candidate = candidate
                    best_candidate_confidence = confidence
                    best_match_pattern = match_pattern
                    best_matched_clusters = matched_clusters

        if not best_candidate or not best_match_pattern:
            return
        else:
            # Retrieve relations from best candidate
            candidate_relations = self.get_relations(best_match_pattern, best_candidate)
            for rr in candidate_relations:
                # Check we havent already seen this new relation,
                #  if we have just update the old one
                matched = False
                for relation in self.relations:
                    if relation.compound == rr[0].lstrip().rstrip() and relation.value == rr[1].lstrip().rstrip() and relation.units == rr[2].lstrip().rstrip():
                        print("Found relation that already exists", relation.compound, relation.value, relation.units)
                        relation.phrases.append(best_candidate)
                        self.new_relations.append(relation)
                        self.matched_sentences.append(best_candidate.full_sentence)
                        matched = True

                if not matched:
                    # if we havent, create it new
                    print("Created new relation", rr[0], rr[1], rr[2], "with confidence ", best_candidate_confidence, "and", best_match_pattern.cluster_label)
                    new_relation = Relation(rr[0], rr[1], rr[2], best_candidate_confidence)
                    new_relation.found = True
                    new_relation.phrases.append(best_candidate)
                    self.relations.append(new_relation)
                    self.new_relations.append(new_relation)
                    self.matched_sentences.append(best_candidate.full_sentence)

            # Add candidate phrase to appropriate clusters and update them
            for c_label in best_matched_clusters:
                for cluster in self.clusters:
                    if c_label == cluster.label:
                        cluster.add(best_candidate)
                        cluster.update_pattern(self.relations, self.matched_sentences)
        return

    @staticmethod
    def get_relations(pattern, candidate_phrase):
        """ Given a pattern and a candidate phrase that match with confidence
         given, extract the relation(s)
         """

        # First relex-label the candidate entities
        for i in range(0, len(pattern.entities)):
            candidate_phrase.entities[i][1] = pattern.entities[i][1]
            candidate_phrase.entities[i][2] = pattern.entities[i][2]

        retrieved_relations = candidate_phrase.retrieve_relations()

        return retrieved_relations

    def delete_cluster(self, index):
        del self.clusters[index]
        self.save(self.save_dir)
        return

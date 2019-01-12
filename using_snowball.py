#%% [markdown]
# ## Snowball Relationship Extraction
#%% [markdown]
# The new Relex package is a toolkit for performing probabilistic chemical relationship extraction based on semi-supervised online learning. The aim is to train parse expressions probabilistically, removing the need for creating parsers with trial and error.
# 
# This overview is based on how to use the code, for a detailed explanation of the algorithm please see the associated paper: https://www.nature.com/articles/sdata2018111
# 
#%% [markdown]
# In general, chemical relationships can consist of any number of entities, that is, the elements of a relationship that are linked together to uniquely define it. Here we will focus on a simple Curie Temperature relationship that consists of the following entities:
# - A compound
# - A specifier
# - A value
# - A unit
# 
# Thus this forms a quaternary relationship. Note the algorithm is generalm and so any number of entities can be specified. You can even make some entities more important than others.
# 
# First define a new model, as usual:

#%%
from chemdataextractor.relex import Snowball, ChemicalRelationship
from chemdataextractor.model import BaseModel, StringType, ListType, ModelType, Compound
import re
from chemdataextractor.parse import R, I, W, Optional, merge, join, OneOrMore, Any, ZeroOrMore, Start
from chemdataextractor.parse.cem import chemical_name, chemical_label
from chemdataextractor.parse.base import BaseParser
from chemdataextractor.parse.common import lrb, rrb, delim
from chemdataextractor.utils import first
from chemdataextractor.doc import Paragraph, Heading, Sentence
from lxml import etree

class CurieTemperature(BaseModel):
    specifier = StringType()
    value = StringType()
    units = StringType()

Compound.curie_temperatures = ListType(ModelType(CurieTemperature))

#%% [markdown]
# Now define parse elements that describe how to identify the entities in text. Think of these as tagging processes.

#%%
# Define a very basic entity tagger
specifier = (I('curie') + I('temperature') + Optional(lrb | delim) + Optional(R('^T(C|c)(urie)?')) + Optional(rrb) | R('^T(C|c)(urie)?'))('specifier').add_action(join)
units = (R('^[CFK]\.?$'))('units').add_action(merge)
value = (R('^\d+(\.\,\d+)?$'))('value')

#%% [markdown]
# Note we tag each with a unique identifier that will be used later. Now let the entities in a sentence be any ordering of these (or whatever ordering you feel like). Here we specify that the value and units must coincide, but this does not have to be the case. 
# 
# We also define an extremely general parse phrase, this will be used to identify candidate sentences.

#%%
# Let the entities be any combination of chemical names, specifier values and units
entities = (chemical_name | specifier | value + units)

# Now create a very generic parse phrase that will match any combination of these entities
curie_temperature_phrase = (entities + OneOrMore(entities | Any()))('curie_temperature')

# List all the entities
curie_temp_entities = [chemical_name, specifier, value, units]

#%% [markdown]
# We are now ready to start Snowballing. Lets formalise our ChemicalRelationship passing in the entities, the extraction phrase and a name.

#%%
curie_temp_relationship = ChemicalRelationship(curie_temp_entities, curie_temperature_phrase, name='curie_temperatures')

#%% [markdown]
# Now create a ```Snowball``` object to use on our relationship and point to a path for training.
# 
# Here will we use the default parameters:
# - TC = 0.95, the minimum Confidence required for a new relationship to be accepted
# - Tsim=0.95, The minimum similarity between phrases for them to be clustered together
# - learning_rate = 0.5, How quickly the system updates the confidences based on new information
# - Prefix_length=1, number of tokens in phrase prefix
# - suffix_length = 1, number of tokens in phrase suffix
# - prefix_weight = 0.1, the weight of the prefix in determining similarity
# - middles_weight = 0.8, the weight of the middles in determining similarity
# - suffix_weight  = 0.1, weight of suffix in determining similarity
# 
# Note increasing TC and Tsim yields more extraction patterns but stricter rules on new relations
# Increasing the learning rate influences how much we trust new information compared to our training
# Increasing the prefix/suffix length increases the likelihood of getting overlapping relationships
# 
# 
# The training process in online. This means that the user can train the system on as many papers as they like, and it will continue to update the knowledge base. At each paper, the sentences are scanned for any matches to the parse phrase, and if the sentence matches, candidate relationships are formed. There can be many candidate relationships in a single sentence, so the output provides the user will all available candidates. 
# 
# The user can specify to accept a relationship by typing in the number (or numbers) of the candidates they wish to accept. I.e. If you want candidate 0 only, type '0' then press enter. If you want 0 and 3 type '0,3' and press enter. If you dont want any, then press any other key. e.g. 'n' or 'no'. 
# 

#%%
snowball = Snowball(curie_temp_relationship)


#%%
snowball.train(corpus='tests/data/relex/curie_training_set/')

#%% [markdown]
# This training process automatically clusters the sentences you accept and updates the knowlede base. You can check what has been learned by searching in the relex/data folder. 
# 
# You can always stop training and start again, or come back to the same training process if you wish, simply load in an existing snowball system using: ```Snowball.load()```
#%% [markdown]
# Looking into data/relex/curie_temperatures_patterns.txt, we see what patterns were learned from our training:
# 
#  name_1 is a ferromagnetic transition metal exhibiting a high specifier_1 of value_1  units_1 ( with confidence score 1.0
# 
# the name_1 nanocrystals show a transition temperature specifier_1 at around value_1  units_1 ( with confidence score 1.0
# 
# the specifier_1  value_1  units_1 ) of bulk name_1 suggests with confidence score 1.0
# 
#  name_1 is ferromagnetic with a specifier_1 of value_1  units_1 and with confidence score 1.0
# 
# , name_1 has recently attracted much attention due to its high specifier_1 ∼ value_1  units_1 ) with confidence score 1.0
# 
#  name_1 is probably the most studied half metal because of it high specifier_1 ∼ value_1  units_1 ) with confidence score 1.0
# 
# , name_1 has a high spin polarization ( > 95 % )118 and a specifier_1 of value_1  units_1 . with confidence score 1.0
# 
# , name_1 ( name_2 ) has received the most attention , due to its high ferroelectric specifier_1 ∼ value_1  units_1 ) with confidence score 1.0
# 
# 
# 
#%% [markdown]
# Now let's extract a new relationship from a previously unseen sentence. We will save to a different file so we can see the new clusters afterwards. We hope that the sentence will be similar enough to a previously seen sentence in order for us to extract the new relationship.

#%%
snowball.save_file_name = 'curie_new'
test_sentence = Sentence('BiFeO3 is highly ferromagnetic with a curie temperature of 1103 K and that is extremely interesting')
rels = snowball.extract(test_sentence)
print("Found relationship:", rels)

#%% [markdown]
# As we can see, we found the right entities. Lets see how confident we are in this relation

#%%
print(rels[0].confidence)

#%% [markdown]
# Lets look at the new clusters that have updated to reflect the new sentence: in ```curie_test_output_clusters```
# 
# Cluster 3 contains 2 phrases
# 
# CoS2 is ferromagnetic with a Curie temperature of 116 K and Co9S8 is antiferromagnetic with a Néel temperature above the decomposition temperature.28 The magnetic susceptibility of Ni3S2 was found to be temperature - independent , which is consistent with Pauli paramagnetism.
#      
#      
# BiFeO3 is ferromagnetic with a curie temperature of 1103 K and this is very interesting
# 
# The cluster centroid pattern is:  name_1 is ferromagnetic with a specifier_1 of value_1  units_1 and with confidence score 1.0
# 
# 
#%% [markdown]
# So our sentence was assigned to Cluster 3 and the new extraction pattern confidence is 1.0.
#%% [markdown]
# Of course, this worked because our new sentence was (purposefully) similar to one that already existed in the training set. In order for this to work more gnereally you will need to train on a lot more than 7 examples.


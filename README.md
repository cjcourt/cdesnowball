# CDESnowball
Updated version of the ChemDataExtractor toolkit to include Quaternary semi-supervised relationship extraction for
retrieving Curie and Neel phase transition temperatures. This work adds new text and table parsers for Curie and Néel
temperature extraction, updated CEM parsers and the relationship extraction (relex) package.


# Training the system

The default Snowball clusters are provided as .pkl files within the [relex settings](relex/settings/).
The adaptable parameters of the system can be edited in the [settings.py file](relex/settings/settings.py).

Train the Snowball cluster system using the SnowballTrainer class:
```
# Import the Snowball training system
from CDESnowball.relex.train import SnowballTrainer
from CDESnowball.relex.utils inport neel_seeds, temp_value_regex, temp_unit_regex, neel_temperature_specifier_regex

# designate a path to a training corpus HTML/XML files
training_corpus = '//path/to/training/corpus'

# Provide some seeds e.g. the neel temperature seeds provided
seeds = neel_seeds

# Set the minimum relationship confidence
tc = 0.8

# Set the minimum sentence similarity
tsim = 0.8

# train the snowball algorithm
sbt = SnowballTrainer(seeds=s,
                      corpus=training_corpus,
                      tsim=tsim,
                      tc=tc,
                      val_regex=temp_value_regex,
                      unit_regex=temp_unit_regex,
                      spec_regex=neel_temperature_specifier_regex,
                      relationship_name='neel_temperatures')
sbt.train()

````
This will initiate the training sequence. Creating the extraction patterns as .pkl files once completed. The saved files will be in the relex.settings folder


# USAGE
Clone this github repository and run 
'''
python3 setup.py install
''''
Or simply use the code in your own project.

Recommended toolkit usage is with the [magdb](https://github.com/cjcourt/magdb) database creation package.

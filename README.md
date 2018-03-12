# chemdataextractor-snowball
Updated version of the ChemDataExtractor toolkit to include Quaternary semi-supervised relationship extraction for
retrieving Curie and Neel phase transition temperatures. This work adds new text and table parsers for Curie and Néel
temperature extraction, updated CEM parsers and the relationship extraction (relex) package.


# Training the system

The default Snowball clusters are provided as .pkl files within the [relex settings](relex/settings/). The adaptable parameters of the system can be edited in the [settings.py file](relex/settings/settings.py).

1) Edit the settings file to locate the neel and curie training corpora

2) Train the Snowball cluster system by either running the relex.train.py file or using the import statement:
```
from chemdataextractor_snowball.relex import train
````
This will initiate the training sequence. Creating the extraction patterns as .pkl files once completed.


# USAGE
To use this updated ChemDataExtractor toolkit you must first have the latest ChemDataExtractor build installed
and running. The latest version is available [here](http://chemdataextractor.org/download).

Next, install this updated version as a separate package named chemdataextractor_snowball in your local python3
site-packages directory. Or simply use the code in your own project.

Recommended toolkit usage is with the [magdb](https://github.com/cjcourt/magdb) database creation package.

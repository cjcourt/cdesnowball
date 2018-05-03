# chemdataextractor-snowball
Updated version of the ChemDataExtractor toolkit to include Quaternary semi-supervised relationship extraction for
retrieving Curie and Neel phase transition temperatures. This work adds new text and table parsers for Curie and Néel
temperature extraction, updated CEM parsers and the relationship extraction (relex) package.

This will initiate the training sequence. Creating the extraction patterns as .pkl files once completed. The saved files will be in the relex.settings folder

See [magneticmaterials.org](http://magneticmaterials.org/documentation) for more details and documentation.


# USAGE
Clone this github repository and run 
```
python3 setup.py install
```

Or simply use the code in your own project.

Recommended toolkit usage is with the [magdb](https://github.com/cjcourt/magdb) database creation package.

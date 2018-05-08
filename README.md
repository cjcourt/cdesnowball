# chemdataextractor-snowball
Updated version of the ChemDataExtractor toolkit to include Quaternary semi-supervised relationship extraction for
retrieving Curie and Neel phase transition temperatures. This work adds new text and table parsers for Curie and Néel
temperature extraction, updated CEM parsers and the relationship extraction (relex) package.

This package is released under MIT License, please see the LICENSE file for details.

If using CDE in your work please cite:
```
Swain, M. C., & Cole, J. M. "ChemDataExtractor: A Toolkit for Automated Extraction of Chemical Information from the Scientific Literature", J. Chem. Inf. Model. 2016, 56 (10), pp 1894–1904 10.1021/acs.jcim.6b00207
```

See [magneticmaterials.org](http://magneticmaterials.org/documentation) for more details and documentation.


# USAGE
Clone this github repository and run 
```
python3 setup.py install
```

Or simply use the code in your own project.

Recommended toolkit usage is with the [magdb](https://github.com/cjcourt/magdb) database creation package.

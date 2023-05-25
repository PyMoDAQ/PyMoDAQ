  .. _contributors:

Contributing
============


How to contribute
#################

If you're willing to help, there are several ways to do it:


* Use PyMoDAQ and report bug or issues using github issue tracker
* Talk about PyMoDAQ to your colleagues
* Cite PyMoDAQ in your papers
* Add your instruments in plugins (see :ref:`instrument_plugin_doc`)
* Work on new features, on solving bugs or issues

For the last point, here are some pointers:

you should fork and clone the up-to-date GitHub repo: https://github.com/PyMoDAQ
using git command line or GitHub Desktop. Then create a dedicated branch name from the change you want to work on
(using git).

Finally I advise to create a dedicated conda environment for this and install PyMoDAQ's package as a developer:

* ``conda create -n dev_env``
* ``conda activate dev_env``
* ``cd`` to the location of the folder where you downloaded or cloned the repository.
* install the package as a developer using the command ``pip install -e .``.

Then any change on the code will be *seen* by python interpreter so that you can see and test your modifications. Think about
writing tests that will make sure your code is sound and that modification elsewhere doesn't change the expected behavior.

When ready, you can create a pull request from your code into the main development branch.


Where to contribute
###################

There are easy places where to contribute and some more obscure places... After a few years of code rewriting/enhancing,
several places are available for easily adding functionalities. These places are implementing one form or another of the
`Factory Pattern`__. For other places, you'll have to read the API documentation :-)

__ https://realpython.com/factory-method-python/


Factory Patterns (to be completed)
**********************************

Data Exporting
--------------
New Exporting data format from the H5Browser is made easy see pymodaq/utils/h5modules/exporters

Math functions in ROI
---------------------

Scanning modes
--------------


Contributors
############

Here is a list of the main contributors:

Main modules
************

Functionalities
---------------

* Sébastien Weber, Research Engineer at CEMES/CNRS
* David Bresteau, Research Engineer at Attolab facility, CEA Saclay
* Nicolas Tappy, Engineer at Attolight (https://attolight.com/)

Cleaning
--------

* Sébastien Weber, Research Engineer at CEMES/CNRS
* David Trémouilles, Researcher at LAAS/CNRS


Plugins
*******

* Sébastien Weber, Research Engineer at CEMES/CNRS
* Sophie Meuret, Researcher at CEMES/CNRS
* David Bresteau, Research Engineer at Attolab facility, CEA Saclay
* and many others...

Extensions
**********
* Sébastien Weber, Research Engineer at CEMES/CNRS
* Romain Geneaux, Researcher at CEA Saclay contributed to the PyMoDAQ-Femto extension

Documentation
*************
* Sébastien Weber, Research Engineer at CEMES/CNRS
* Matthieu Cabos helped with this documentation
* David Bresteau wrote the documentation of the PID extension

Testing
*******
* Sébastien Weber, Research Engineer at CEMES/CNRS
* Pierre Jannot wrote tests with a total of 5000 lines of code tested during his internship at CEMES in 2021


.. note::

  If you're not in the list and contributed somehow, sorry for that and let us know at sebastien.weber@cemes.fr
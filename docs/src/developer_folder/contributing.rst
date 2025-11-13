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

You should `fork and clone <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo#forking-a-repository/>`_
the up-to-date GitHub repo: https://github.com/PyMoDAQ/PyMoDAQ using git command line or GitHub Desktop
(the latter is recommended for newcomers, just make sure to uncheck "Copy the ... branch only").
Then create a dedicated branch name from the change you want to work on
(using git).

Finally it is advised to create a dedicated virtual environment for this and install PyMoDAQ's package as a developer. For example, using mamba as an environment manager:

- ``mamba create -n dev_env``
- ``mamba activate dev_env``
- ``cd`` to the location of the folder where you downloaded or cloned the repository.
- install the package as a developer with test tools using the command either by using the provided script ``python install-packages.py -d``.
    - it calls `pip install -e` on each pymodaq package (pymodaq_utils, pymodaq_data, pymodaq_gui and pymodaq) in the package folder.
    - the `-e` option tells pip to install the package in editable mode, meaning that any change done to the source will be reported to the installed package.
    - the `-d` option activates `[dev]` in the package names transmitted to `pip install` (e.g. `pymodaq_utils[dev]`). It indicate to install the package alongside its optional dependancies, declared as `dev` in the `pyproject.toml` file.


Then any change on the code will be *seen* by python interpreter so that you can see and test your modifications. Think about
writing tests that will make sure your code is sound and that modification elsewhere doesn't change the expected behavior.

It also requires the installation of a QT backend and some system packages on Linux, like explained in :ref:`the installation tips page <installation_tips>` of the documentation.

When ready, you can create a pull request from your code into the proper branch, as discussed in the next section.

Branch structure and release cycle
##################################
.. _branches_release_cycle_doc:

There are several branches of the PyMoDAQ repository, directly linked to the *release cycle* of PyMoDAQ, which we
define here. PyMoDAQ versioning follows usual practice, as described `in this link <https://en.wikipedia.org/wiki/Software_versioning>`_:

.. figure:: https://upload.wikimedia.org/wikipedia/commons/8/82/Semver.jpg
    :width: 150
    :align: center

Starting from November 2025, the following structure was agreed upon by the contributors. At any given time,
there is a **stable** version of PyMoDAQ - at the time of writing it is 5.1.0 - which is not to be modified except for
bugfixes, and a **development** version (he next **minor** version), onto which new features may be added.

The release cycle is illustrated in this figure:

.. figure:: /image/tutorial_contribute_to_pymodaq_code/release_cycle_pymodaq3.png

This cycle makes use of several types of branches:

**Code flow branches:**

* **the stable branch, eg: '5.1.x'** This is the branch representing the stable version of PyMoDAQ. No change should be
  made on this branch except bugfixes and hotfixes (see below). This is the branch from which the official releases are
  created, for instance version *5.1.0*, *5.1.1*, *5.1.2*, etc. Only packages with modifications will be part of a bugfix release.
  For example, if the current version is *5.1.0*, all packaged are at version *5.1.0*. Then, pymodaq_data and pymodaq_utils are
  modified and a new bugfix version is released, then pymodaq_utils and pymodaq_data *5.1.1* will be released and pymodaq_gui
  and pymodaq will stay at *5.1.0*.

* **the development branch: 'dev** Note that the branch name will **always** be dev.
  This is the development branch. It is *ahead* of the main branch, in the sense that it contains more
  recent commits than the main branch. It is thus the future state of the code. This is where the last developments
  of the code of PyMoDAQ are pushed. When the developers are happy with the state of this branch, typically when they
  finished to develop a new functionality and they tested it, this will lead to a new *release* of all four packages (5.1.x -> 5.2.0 in our example).
  In practice, the branch will stay *dev* but a *5.2.x* branch  will be created based on the last state of *dev*

**Temporary branches:**

* **Feature, eg: 'feature/new_colors'**: Any additional feature should be done on a feature branch. They are created based
  on the current development branch. When the feature is complete, a Pull Request must be open to integrate the changes into
  the development branch.

* **Bugfix, eg: 'bugfix/remove_annoying_message'**: These branches are meant to correct small issues. It can be created based
  on either the stable or development branch, depending on where the bug is located. Regardless, any bugfix must then be applied to
  all branches, if applicable (see note below).

* **Hotfix, eg: 'hotfix/fix_huge_bug'**: This is similar to a bugfix, but for more important bugs. More precisely, hotfixes
  are important enough that when applied, they will trigger an immediate new release (e.g. *5.1.1* -> *5.1.2*) that incorporate the fix.
  At the contrary bugfixes can wait for a future release.

.. note::
    **Applying fixes across several branches**

    Let's consider the case where a bug is found on the **stable** branch. We create a new branch to fix it, open a pull request
    into the stable branch, and wait for it to be accepted. However, it is likely that the buggy code is also part of the
    **development** version, requiring another pull request on that branch! Thus, but when a bug is found, one should always
    remember to check if it is present on several branches.

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
* David Bresteau wrote the documentation of the PID extension and the tutorial: :ref:`plugin_development`

Testing
*******
* Sébastien Weber, Research Engineer at CEMES/CNRS
* Pierre Jannot wrote tests with a total of 5000 lines of code tested during his internship at CEMES in 2021


.. note::

  If you're not in the list and contributed somehow, sorry for that and let us know at sebastien.weber@cemes.fr

.. _release_3:

=======================
PyMoDAQ 3 (3.0.0-3.0.4)
=======================

PyMoDAQ 3.0.0 was released on 2020-11-25. This page covers the releases documented up to 3.0.4 (2021-01-12).

.. note::

   Later 3.x releases (up to 3.6.13, February 2023) were not described in the former changelog, and are not listed
   here.

3.0.4 (2021-01-12)
==================

* Fixed the documentation build, broken since the new ``src`` layout
* Fixed a wrong call to the version in the Dashboard

3.0.3 (2021-01-08)
==================

* Continuous integration moved from Travis to GitHub Actions (build, linting and ``pytest``; coverage still low)
* ``src`` package layout adopted to separate source code from packaging
* Python 3.8 compatibility: use of ``importlib.metadata``, now in the standard library
* LCD widget displays the correct label

3.0.0-3.0.2 (2020-11-25)
========================

* New main version after a developer mistake in the versioning: the version went from 2.2.6 to 3.0.2 because the
  version number was obtained from a file copied from the ``pymodaq_plugins`` repository. The new main version reflects
  the compatibility with the latest ``pyqtgraph`` (>= 0.11) and with Python >= 3.8
* Compatibility with Python < 3.9 (was < 3.8 before)
* flake8 syntax checking and code clean-up

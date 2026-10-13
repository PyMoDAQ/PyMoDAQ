.. _release_5_2:

==========================
PyMoDAQ 5.2 (5.2.0-5.2.12)
==========================

PyMoDAQ 5.2.0 was released on 2026-06-12, followed by twelve bug-fix releases until 2026-10-06. Pull requests (#NNN)
refer to the `PyMoDAQ repository <https://github.com/PyMoDAQ/PyMoDAQ>`_.

.. contents::
   :local:
   :depth: 2

Highlights
==========

5.2 is a large UI and architecture release: a new **configurator** to select and apply sets of settings (which became
the State Manager), a rework of the **managers** framework, a **widget synchronizer**, **Material icons**, a common
**shared UI** (menus and toolbars) for the Dashboard and the extensions, new **Overshoot** and **Scan** managers,
**scripting** capabilities, and many data-saving improvements.

Major new features
==================

Configurator and managers
-------------------------

* New configurator extension, then **preset configurator** and configurator loaded from a preset file: #748, #773,
  #948. It was renamed *State Manager* in the UI: #1012
* Refactoring of the managers framework (``ManagerBase``): #753. New **modules manager**: #929, with a rationalization
  of the origin/name of the data produced by viewers and actuators: #955
* New **Overshoot manager**: #938
* **Scan manager**: #1028, #1033 (removed again in 5.2.6 because it was "not mature enough": #1089, and brought back
  in 5.3.0)

Common UI framework
-------------------

* **Widget synchronizer** keeping widgets and parameters in sync: #804, #819, #825
* Common window encapsulating the common menus and toolbars (*SharedUI*): #837, #862, #986, #1009, #1017, #1062
* **Qt Material icons**, many new, flipped and colored icons, switch on checked state: #811, #865-#867, #887, #889,
  #919, #953
* Dashboard UX rework and dashboard loader reusable by other applications: #805, #862, #888
* Compact dock manager: #920; search in control module settings: #841; dark/light style switch and style proxy for
  checkboxes in dark themes: #802, #1007
* **Action LED** and updated viewer0D: #926, #916
* Launcher for PyMoDAQ: #1014

Control modules and scans
-------------------------

* DAQ_Move refactorization and actuator UI configuration: #870, #829
* DAQ_Scan update: #881, #1034, #1036, #1038
* Control module factorization and resource manager utilities: #996, #1047
* Save and display the settings of all modules in the h5 file: #1020
* Data names and origins: #955, #1038; ``split_as_dte`` to split a data object into several ones: #900

Configuration
-------------

* ``Config`` is a singleton: #775. New ``GlobalConfig`` to manipulate all configurations: #890, with a
  ``config_changed`` signal: #913
* Configuration to parameter XML conversion: #912; cleaning of config paths: #972

Data saving
-----------

* Single-Write-Multiple-Read (SWMR) data saving: #906; options when calling the ``DataSaver``: #852; access to the
  h5 backend from the ``DataSaver``: #914
* Conversion to ``xarray``: #934; ``H5Saver`` parameters generated according to the save type: #966

Scripting
---------

* Scripting capabilities in PyMoDAQ: #923, with a Python editor: #1018

Install and environment
-----------------------

* Python 3.9 no longer supported, Python 3.13 added: #794; installation on Python 3.14: #1032
* Monorepo documentation and ``install-packages.py`` options: #767, #783, #785; ``tables < 3.10`` security dependency
  removed: #897

Bug fixes (5.2.1-5.2.12)
========================

* **5.2.1-5.2.2**: epsilon units used in value comparisons, h5py with enlargeable data: #1067, #1068, #1069
* **5.2.3-5.2.4**: h5py hotfix, splash screen removal in DAQ_Scan, module saving: #1070, #1072, #1078, #1080
* **5.2.5**: tabular scan save and load: #1085
* **5.2.6**: scan manager removed: #1089
* **5.2.7**: averaging, colors, double logger entry, dashboard startup visibility, PID, shared UI kept alive with the
  H5Browser: #1092, #1097, #1087, #1111, #1123, #1134, #1137, #1142
* **5.2.8**: parameter tree header resize, ``DAQ_type``/``detector_type`` backward compatibility, delta epsilon in
  comparisons: #1145, #1136, #1158
* **5.2.9**: more file filters when opening files, errors in the savers: #1165, #1167
* **5.2.10**: display errors in 0D data scans: #1183
* **5.2.11**: relative UI: #1185
* **5.2.12**: icons, scan timeout option and other backports from the development branch (#1061, #1093, #1105),
  LECO communication refactoring, stale items kept in ``ItemSelect`` (ROI output silently empty): #1182, #1247

.. _whats_new5:

What's new in PyMoDAQ 5
***********************

The main modifications in PyMoDAQ 5 is related to the organization of the packaging.
The second one is the change from python packaging with the introduction of `pyproject.toml` (for more information check :doc:`/developer_folder/plugins`)
and the choice to use `hatch` to manage the building, package versioning and publishing (All those part are treated in the :doc:`/tutorials/new_plugin`).

Three new packages were created to offer features pack independantly :

* `pymodaq_data`_: specific for data management/saving/loading
* `pymodaq_gui`_: specific to create GUI and giving access to the one we know from pymodaq
* `pymodaq_utils`_: the basic things that are used everywhere (ie: logging, configuration management, mathematical tools...)

The main idea behind this change is to increase modularity, reusability and to be able to load just the part of the features we need.

.. figure:: /image/pymomorph4to5.gif

For a full list of matching path of objects between version 4 and 5, check :doc:`/api/api_callable_v4to5`

.. _pymodaq_utils:

PyMoDAQ Utils
-------------
*(for detailed library information check* :doc:`pymodaq_utils</api/API_Utility_Library>` *)*

This package provide a set of utilities (constants, methods and classes) that are used in the
various subpackages of PyMoDAQ (PyMoDAQ itself, but also plugins and data management and user interfaces modules).

Basically, all the common generic class and methods used in every pymodaq packages, like logging.
Figure :numref:`pymodaq_utils_hierarchy` show the layout of this package.

.. _pymodaq_utils_hierarchy:

.. figure:: /image/pymodaq_utils_files.png
  :width: 200

  Layout of the ``utils`` module

It looks a lot like the old utils directory in PyMoDAQ 4 (without the gui and data objects).
They can also be used
in some other programs to use their features. Below is a short description of what they are related to:

* abstract: contains abstract classes (if not stored in another specific module)
* array_manipulation: utility functions to create, manipulate  and extract info from numpy arrays
* config: objects dealing with configuration files (for instance the main config for pymodaq). Can be used elsewhere,
  for instance in instrument plugin
* enums: base class and method to ease the use of enumerated types
* factory: base class to be used when defining a factory pattern
* logger: methods to initialize the logging objects in the various modules
* math_utils: a set of useful mathematical functions
* units: methods for conversion between physical units (especially photon energy in eV, nm, cm, J...)

.. _pymodaq_data:

PyMoDAQ Data
------------

All the changes made in PyMoDAQ 4 about :ref:`data management<data_management>` were moved in this package.

Before the :term:`modules<module>` where stored in different places, mainly ``pymodaq.utils.data``, ``pymodaq.utils.h5modules``
module. You had to install and load the whole PyMoDAQ python :term:`package<package>` if you want to use the Data Objects or acess the hdf5 features.
Now, you can install only ``pymodaq_data`` (which still requires the all the basic function from utils).
Figure :numref:`pymodaq_data_hierarchy` show the layout of this package.
All the datatypes are listed there :doc:`/api/utility_api/data_management`

.. _pymodaq_data_hierarchy:

.. figure:: /image/pymodaq_data_files.png
   :width: 200

   Layout of the ``data`` module

.. _pymodaq_gui:

PyMoDAQ GUI
------------
This package gathered all the GUI components shared (or to be shared) among all the PyMoDAQ affiliates (dashboard, customapp, extensions...).
Set of Qt widgets and graphical components for the PyMoDAQ ecosystem.
The two main categories are : `Managers`_, `Plotting`_

Figure :numref:`pymodaq_gui_hierarchy` show the layout of this package.

.. _pymodaq_gui_hierarchy:

.. figure:: /image/pymodaq_gui_files.png
   :width: 200

   Layout of the ``GUI`` module

.. _Managers:

Managers
++++++++
*(for detailed library information check* :doc:`Managers</api/api_utility_modules/managers>` *)*

* ``ActionManager``, offers to all user interfaces ``QAction`` and connected actions management.
* ``ParameterManager``, used to manage all the ``ParameterTree`` (from pyqtgraph) in pymodaq modules (global settings, viewer settings, hardware settings...).
* ``ModulesManager`` : DAQ_Moves, DAQ_Viewers...


.. _Plotting:
Plotting
++++++++
*(for detailed library information check* :doc:`Plotting</api/api_utility_modules/api_plotting/viewers>` *)*

The plotting tools are mainly used for data display, from scalar data up to 4 dimensions data.
This is also another plotting class (for lcd like display) described there :doc:`/api/api_utility_modules/api_plotting/other_classes`

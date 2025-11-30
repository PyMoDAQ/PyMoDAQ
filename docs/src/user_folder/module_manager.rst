
.. _module_manager:

Module Manager
==============

The module manager is an object used to deal with:

* Selection of actuators and detectors by a user (and internal facilities to manipulate them, see api :ref:`api-managers_module_manager`)
* Synchronize acquisition from selected detectors
* Synchronize moves from selected actuators
* Probe as lists all the datas that will be exported by the selected detectors (see :numref:`module_manager_fig`)
* Test Actuators positioning. Clicking on test_actuator will let you enter positions for all selected actuators that
  will be displayed when reached


  .. _module_manager_fig:

.. figure:: /image/managers/module_manager.PNG
   :alt: module_manager_fig

   The Module Manager user interface with selectable detectors and actuators, with probed data feature and actuators testing.

This module is made so that selecting actuators and detectors for a given action is made easy. On top of it, there are
features to test communication and retrieve infos on exported datas (mandatory fro the adaptive scan mode) or positioning.
Internally, it also features a clean
way to synchronize detectors and actuators that should be set together within a single action (such as a scan step).



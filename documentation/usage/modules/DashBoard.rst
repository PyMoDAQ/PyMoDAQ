.. _Dashboard_module:

DashBoard
=========

This module is the heart of PyMoDAQ, it will:

* Help you declare the list of actuators and detectors to be used for a given experiment (:ref:`preset_manager`)
* Setup automatic data acquisition of detectors as a function of one or more actuators using its DAQ_Scan extension
* Log data into advanced binary file or distant database using using its DAQ_Logger extension

The flow of this module is as follow:

* At startup you have to define/load/modify a preset (see :ref:`preset_manager`) representing an ensemble of actuators and detectors
* Define/load/modify eventual overshoots (see :ref:`overshoot_manager`)
* Define/load/modify eventual ROI (Region of interests) selections (see :ref:`roi_manager`)
* Use the actuators and detectors manually to drive your experiment
* Select an action to perform: automated scan (DAQ_Scan) or log data (DAQ_Logger)


Introduction
------------

This module has one main window,
the dashboard (:numref:`daq_scan_dashboard`) where a log and all declared actuators and detector
will be loaded as instances of DAQ_Move and DAQ_Viewer.
The dashboard gives you full control for manual adjustments
of each actuator, checking their impact on live data from the detectors. Once all is set, one can move on to
different actions.


  .. _daq_scan_dashboard:

.. figure:: /image/dashboard.png
   :alt: dashboard

   DAQ_Scan dashboard containing all declared modules and log.

.. :download:`png <dashboard.png>`


Preset manager
--------------

The *Preset modes* menu is used to create, modify and load preset. A preset is a set of
actuators and detectors represented in a tree like structure, see :ref:`preset_manager`.

Overshoot manager
-----------------

The *Overshoot* menu is used to configure actions (for instance the absolute positionning of one or more
actuators, such as a beam block to stop a laser eam) when a detected value (from a running detector module) gets
out of range with respect to some predefined bounds. For details, see :ref:`overshoot_manager`.


ROI manager
-----------
The *ROI menu*, see :ref:`roi_manager`, is used to configure the layout of region of interest in all 1D and 2D viewers
of all detectors in the dashboard. You can then, in one go, recall a particular complex configuration for data acquisition.

.. _multiple_hardware:

Multiple hardware from one controller
-------------------------------------

Sometimes one hardware controller can drive multiple actuators and sometimes detectors (for instance a XY translation stage). For
this particular case the controller should not be initialized multiple times. One should identify one actuator
referred to as *Master* and the other ones will be referred to as *Slave*. They will share the same controller
address represented in the settings tree by the *Controller ID* entry. These settings will be activated
within the plugin script where one can define a unique identifier for each actuator (U or V for the conex
in :numref:`daq_move_gui_settings`). This feature can be enabled for both DAQ_Move and DAQ_Viewer modules but will be
most often encountered with actuators, so see for more details: :ref:`multiaxes_controller`. This has to be done using the Preset Manager

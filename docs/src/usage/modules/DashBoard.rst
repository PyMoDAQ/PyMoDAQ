.. _Dashboard_module:

DashBoard
=========

This module is the heart of PyMoDAQ, it will:

* Help you declare the list of actuators and detectors to be used for a given experiment (:ref:`preset_manager`)
* Setup automatic data acquisition of detectors as a function of one or more actuators using its DAQ_Scan extension
* Log data into advanced binary file or distant database using its DAQ_Logger extension


The flow of this module is as follow:

* At startup you have to define/load/modify a preset (see :ref:`preset_manager`) representing an ensemble of actuators and detectors
* Define/load/modify eventual overshoots (see :ref:`overshoot_manager`)
* Define/load/modify eventual ROI (Region of interests) selections (see :ref:`roi_manager`)
* Use the actuators and detectors manually to drive your experiment
* Select an action to perform: automated scan (DAQ_Scan) and/or log data (DAQ_Logger)


Introduction
------------

This module has one main window,
the dashboard (:numref:`daq_scan_dashboard`) where a log and all declared actuators and detectors
will be loaded as instances of DAQ_Move and DAQ_Viewer.
The dashboard gives you full control for manual adjustments
of each actuator, checking their impact on live data from the detectors. Once all is set, one can move on to
different actions.


  .. _daq_scan_dashboard:

.. figure:: /image/dashboard.PNG
   :alt: dashboard

   Dashboard user interface containing all declared control modules (actuators/detectors) and some initialization info.

.. :download:`png <dashboard.png>`


Menu Bar Description
--------------------

Figure :numref:`dashboard_menu` displays the menu of the *Dashboard* window with access to all the *Managers* useful
within PyMoDAQ and described below:

  .. _dashboard_menu:

.. figure:: /image/dashboard_menu.png
   :alt: dashboard_menu

   Dashboard menu bar.

The file menu will allow you to quickly display, in a default text editor, the current log file (older logs can be found
in the *pymodaq_local* folder, see :ref:`section_configuration`). The user can also access and edit the general
configuration file *config.toml* selecting the *Show configuration file* entry that will open a popup window (see
Fig. :numref:`edit_config`) allowing the user to modify all its fields. Finally, the user can *Quit* the application
or *Restart* it is changes have to be applied (for instance when modifying a *Preset*)


  .. _edit_config:

.. figure:: /image/configuration/edit_config.png
   :alt: config_file

   Configuration popup window.

The *Settings* entry is allowing the user to save/load layouts of docked windows within the *Dashboard*.

..note

    When a *Preset* has been loaded and if the arrangement of the *Control Modules* (their docked panels) is
    modified, then a *layout* configuration file whose name derive from the loaded preset filename will be created.
    At each later loading of this preset, the *Control Modules* arrangement will then be restored.



Preset manager
++++++++++++++

The *Preset modes* menu is used to create, modify and load preset. A preset is a set of
actuators and detectors represented in a tree like structure, see :ref:`preset_manager`.

Overshoot manager
+++++++++++++++++

The *Overshoot* menu is used to configure actions (for instance the absolute positionning of one or more
actuators, such as a beam block to stop a laser beam) when a detected value (from a running detector module) gets
out of range with respect to some predefined bounds. For details, see :ref:`overshoot_manager`.


ROI manager
+++++++++++
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




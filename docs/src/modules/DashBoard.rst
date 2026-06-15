.. _Dashboard_module:

DashBoard
=========

This module is the heart of PyMoDAQ, it will:

* Help you declare the list of actuators and detectors to be used for a given experiment (:ref:`experiment_manager`)
* Allow you to set particular values for their settings (see :ref:`state_manager`)
* Load and run specific extensions such as:
  * Automatic data acquisition of detectors as a function of one or more actuators using the DAQ_Scan
  * Log data into advanced binary file or distant database using its DAQ_Logger extension
  * Optimize data or sampling using the Bayesian or Adaptive extensions
  * Mix data using the DataMixer
  * ...


The flow of this module is as follow:

* At startup you have to define/load/modify an experiment (see :ref:`experiment_manager`) representing an ensemble
  of actuators and detectors
* Define/load/modify a State (see :ref:`state_manager`) representing a state of the control modules settings and
  some other special state subentries like actuator values
* Define/load/modify eventual overshoots (see :ref:`overshoot_manager`)
* Define/load/modify eventual ROI (Region of interests) selections (see :ref:`roi_manager`)
* Use the actuators and detectors manually to drive your experiment
* Select an extension to run: automated scan (DAQ_Scan), log data (DAQ_Logger)...

.. _dashboard_cli_arguments_note:

.. note::

    This module can be started from a terminal, using the command ``dashboard`` in an activated environment where
    PyMoDAQ is installed.

    A list of accepted command-line arguments are available, you can list them using ``dashboard -h``. For now the
    accepted arguments are the following:

    * ``-exp`` or ``--experiment`` followed by an existing experiment name will start the dashboard with the
      selected experiment loaded. For example ``dashboard -exp default`` should start the dashboard with the default
      experiment.

Introduction
------------

This module has one main window,
the dashboard (:numref:`dashboard`) where a log and all declared actuators and detectors
will be loaded as instances of DAQ_Move and DAQ_Viewer.
The dashboard gives you full control for manual adjustments
of each actuator, checking their impact on live data from the detectors. Once all is set, one can move on to
different actions.

  .. _dashboard:

.. figure:: /image/dashboard/dashboard.png
   :alt: dashboard

   Dashboard user interface containing all declared control modules (actuators/detectors) and some initialization info.

.. :download:`png <dashboard.png>`


Menu Bar Description
--------------------

Figure :numref:`dashboard_menu` displays the menu of the *Dashboard* window with access to all the tools useful
within PyMoDAQ and described below:

  .. _dashboard_menu:

.. figure:: /image/dashboard/dashboard_menu.png
   :alt: dashboard_menu

   Dashboard menu bar.

The **File** menu will allow you to:

* create a new Experiment file
* Restart or Quit the DashBoard

The **View** menu is allowing the user to save/load layouts of docked windows within the *Dashboard* and display or not
the various toolbars

.. note::

    Docked Windows Layout: when an *Experiment* has been loaded and if the arrangement of the *Control Modules*
    (their docked panels) is
    modified, then a *layout* configuration file whose name derive from the loaded experiment filename will be created.
    At each later loading of this experiment, the *Control Modules* arrangement will then be restored.


The **Tools** menu will allow you to:

* Open the Experiment Manager (see :ref:`experiment_manager`)
* Open the State Manager
* the Overshoot Manager
* Load Extensions of the DashBoard
* Look at the current log file in the default editor. The older logs can be found in the *.pymodaq* folder,
  see :ref:`section_configuration`.
* Open and modify the Preferences related to all pymodaq modules and plugins (see Fig. :numref:`edit_config`)
* Run the leco Coordinator (see :ref:`leco_communication`)


  .. _edit_config:

.. figure:: /image/configuration/edit_config.png
   :alt: config_file

   Preferences popup window.


The **Tools/Experiment** menu enables to create or modify (using the :ref:`experiment_manager`) *experiments* that are XML
files defining a set of actuators and detectors used for a given experiment. Each experiment has therefore a corresponding
experiment file. At startup, the program checks for existing experiment files and create a menu entry for each of them.

The **State** menu, new from version 5.2.x, enables to create or modify (using the :ref:`state_manager`)
*States* that are binary files defining a set of status for the settings of all actuators and detectors
declared in the DashBoard (from the loaded experiment). One can therefore easily switch between different states, hence
different settings for the control modules. Special *actions* are also available such as the initialization of control
modules (could be interesting if some settings have to be set before initialization) or defining a value for an actuator.

The **Overshoot** menu is used to configure actions like stoping the acquisition or setting the value of a given
actuator when a detected value (from a running detector module) gets
out of range with respect to some predefined bounds. For details, see :ref:`overshoot_manager`.

The **ROI Modes** menu, see :ref:`roi_manager`, is used to save the state of all regions of interest defined by a user
within the 1D or 2D viewers declared in the *DAQ_Viewers* control modules in the *Dashboard*. You can then, in one go,
recall a particular complex configuration for data acquisition.

The **Remote/Shortcuts Control** menu, see :ref:`Remote_module`, is used to define key sequences on a keyboard or buttons/joysticks on a gamepad to
trigger specific actions from the *Control modules*, for instance jogging of the actuator values using a joystick or grabing
data from a detector using a button.

The **Extensions** menu let the user load a specific installed extensions. Default ones are the *DAQ_Scan* or
*DAQ_Logger* ones. More specific ones can be installed, for instance the package `Pymodaq Femto`__

__ https://pymodaq-femto.readthedocs.io/en/latest/



.. _multiple_hardware:

Multiple hardware from one controller
-------------------------------------

Sometimes one hardware controller can drive multiple actuators and sometimes detectors (for instance a XY translation stage). For
this particular case the controller should not be initialized multiple times. One should identify one actuator
referred to as *Master* and the other ones will be referred to as *Slave*. They will share the same controller
address represented in the settings tree by the *Controller ID* entry. These settings will be activated
within the plugin script where one can define a unique identifier for each actuator (U or V for the conex
in :numref:`daq_move_gui_settings`). This feature can be enabled for both DAQ_Move and DAQ_Viewer modules but will be
most often encountered with actuators, so see for more details: :ref:`multiaxes_controller`. This has to be done using the Experiment Manager




  .. _shared_ui:

Shared UI
=========

Introduction
------------
All user interfaces within PyMoDAQ are sharing some features that would be complex
to maintain if declared everywhere. This is why most of the UI derive from the
:ref:`custom_app` base class. However the latter provides only the framework to quickly build interfaces
that may be very different. It doesn't provide a unified way to add direct `actions` and
access to comonly used features such as the PyMoDAQ preferences, the log file or even a
direct link to the documentation. This is the role of the SharedUi object that will
wraps CustomApps with common features (mostly actions and menus) we will describe below.


Instantiating a SharedUI
------------------------

The code below shows how to create and instantiate a SharedUI. One should first
create a MainWindow either directly or using the `make_window` method. The SharedUI
object take this window as an argument and will build on it the menus and actions,
see :numref:`naked_shared_ui`

.. code-block::

    from pymodaq_gui.qt_utils import mkQApp
    app = mkQApp('CommonWindow')

    win, area = make_window(area=False, title='SharedUI')
    window = SharedUI(win)

    window.show()

    # Run application
    sys.exit(app.exec())


  .. _naked_shared_ui:

.. figure:: /image/shared_ui/shared_ui_naked.png
   :alt: Shared UI

   SharedUI interface.

And Wrapping it around a CustomApp
----------------------------------


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

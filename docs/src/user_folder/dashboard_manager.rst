.. _dashboard_manager:

DashBoard Managers
==================

.. note::

  Since version 5.2.0 all the *DashBoard Managers* below share the same structure (see API and description
  below).

A DashBoard Manager is a GUI allowing to create entries for a given task. These entries are
saved (and loaded) as files in the pymodaq system-wide configuration folder. The Manager GUI
allows a unified framework to deal with entry creation, deletion, copy, reloading and execution
(see :numref:`manager_toolbar`).


   .. _manager_toolbar:

.. figure:: /image/dashboard/manager_toolbar.png
   :alt: toolbar

   A toolbar to browse, duplicate, create, delete, save, reload and execute a given entry managed by the manager.

The entries browsing and execution is incorporated in the DashBoard toolbar (see :numref:`dashboard`
 and :numref:`dashboard_manager_toolbar` below)

   .. _dashboard_manager_toolbar:

.. figure:: /image/dashboard/dashboard_manager_toolbar.png
   :alt: toolbar

   Toolbar from the manager incorporated into the DashBoard. The manager can be opened from there and entries
   can be browsed and directly executed.


Depending on the task, an entry will look different (see below a Preset entry and a Configurator entry). A preset
features a list of actuators and detectors while a configuration is a list of actions one can perform on control
modules settings for a given *preset*.

.. _preset_manager:

Preset manager
--------------

The *Preset manager* is an object that helps to generate, modify and save preset configurations of :ref:`Dashboard_module`.
A preset is a set of actuators and detectors represented in a tree like structure, see :numref:`preset_fig`.


   .. _preset_fig:

.. figure:: /image/dashboard/preset_fig.png
   :alt: preset_fig

   An example of a preset creation named *default* containing 4 actuator modules and 3 detector
   modules.

Only a few options are available for the preset. It is merely there to configure the type and list of
control modules to be added in the DashBoard. The only options are related to the master/slave status
(see :ref:`multiple_hardware`) and if it should be initialized at startup. For configuration of
the initial settings of the control modules, see below the :ref:`configurator`.

.. note::

  Since its modification in version 5.2.0 onwards, *Presets* can be modified at any time and
  a new preset can be loaded also at any time without having to restart the DashBoard!!

.. _configurator:

Configurator
------------

.. note::

  New in version 5.2.0


   .. _configurator_fig:

.. figure:: /image/dashboard/configurator_fig.png
   :alt: configurator_fig

   An example of a *Configuration* creation named *default* and related to the *beam_steering* preset
   This Configuration contains six subentries: four to set some specific settings to the Xpiezo and
   Ypiezo actuators and two to set their absolute value. This *default* configuration is executed
   at startup just after the preset is done loading control modules.

Once the :ref:`preset_manager` is done loading its configured control modules, the Configurator
can be opened. In fact, for each preset file, a configuration called *default* (empty by default)
will be created and loaded after the loading of the control modules. But then any predefined configuration
can be loaded at any time.

A configuration is made by selecting a given settings (left side of figure :numref:`configurator_fig`)
and dragging/dropping it to the table on the right. You can also use double clicking
a setting to move it to a configuration or use the right arrow in the middle of the window.
If you select a group parameter, all its children will be moved in the configuration.
All but only the ones that are valid as configurable settings.

Three special *configuration* subentries are available from the context menu (right click while
the mouse is hovering the configuration table), see :numref:`configurator_context_menu`.

   .. _configurator_context_menu:

.. figure:: /image/dashboard/configurator_context_menu.png
   :alt: configurator_fig

   The Configurator context menu

These allow to configure:

* the Initialization of a given control module
* the value of an Actuator (an absolute move will be done)
* a Waiting time before moving to the next subentry

There are also many ways to move around and delete the subentries: either using the
arrows in the middle of the window (look at their tooltip) or shortcuts: Ctrl+Up to move up,
Del to delete...


.. _overshoot_manager:

Overshoot manager
-----------------

.. note::

  As of version 5.2.0 the overshoot manager will be rewritten to use the general framework described above and also
  to use entries from the Configurator to trigger a *safe* configuration...


The *Overshoot* manager is used to configure **safety actions** (for instance the absolute positioning of one or more
actuators, such as a beam block to stop a laser beam) when a detected value (from a running detector module) gets
out of range with respect to some predefined bounds, see :numref:`overshoot_manager_fig`. It is configurable in the framework of the Dashboard module,
when actuators and detectors have been activated. A file containing its configuration will be saved (with a name derived
from the preset configuration name and will automatically be loaded with its preset if existing on disk)

  .. _overshoot_manager_fig:

.. figure:: /image/DAQ_Scan/overshoot_fig.png
   :alt: overshoot_fig

   An example of an overshoot creation named *overshoot_default* (and corresponding xml file)
   containing one listening detector and 2 actuators to be activated.


.. _roi_manager:

ROI manager
-----------

.. note::

  As of version 5.2.0 the *ROI* manager will be rewritten to use the general framework described above.

The *ROI* manager is used to save and load in one click all ROIs or Lineouts defined in the current detector's viewers,
see :numref:`roi_manager_fig`.
The file name will be derived from the preset configuration file, so that at start up, it will automatically be loaded,
and ROIs and Lineouts will be restored.

  .. _roi_manager_fig:

.. figure:: /image/managers/roi_manager.PNG
   :alt: roi_manager_fig

   An example of ROI manager modification named from the preset *preset_adaptive* (and corresponding xml file)
   containing all ROIs and lineouts defined on the detectors's viewers.


.. _Remote_module:

Remote Manager
--------------

In construction


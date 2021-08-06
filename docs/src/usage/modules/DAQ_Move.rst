.. _DAQ_Move_module:

DAQ Move
========

This module is to be used to control any actuator hardware. An actuator is, in a general sense, any parameter
that one can control and may vary during an experiment.  The default actuator
is a Mock one (a kind of software based
actuator displaying a *position* and accepting absolute or relative *positioning*).

Introduction
------------

This module has a generic interface in the form of a dockable panel containing the interface for initialization,
the manual control of the actuator *position* and a side tree like interface displaying all the settings.
:numref:`daq_move_gui_base` shows the minimal interface of the module (in order to take minimal place in the Dashboard)


   .. _daq_move_gui_base:

.. figure:: /image/DAQ_Move/daq_move_gui_base.PNG
   :alt: daq_move_gui_base

   Minimal DAQ_Move user interface

.. :download:`png <daq_move_gui_base.png>`

.. |green_arrow| image:: /image/DAQ_Move/green_arrow.PNG
    :width: 20pt
    :height: 20pt

.. |plus_button| image:: /image/DAQ_Move/plus_button.PNG
    :width: 20pt
    :height: 20pt

.. |settings| image:: /image/DAQ_move/settings_button.PNG
    :width: 20pt
    :height: 20pt

.. |move_rel| image:: /image/DAQ_move/move_rel.PNG
    :width: 60pt
    :height: 20pt

.. |move_rel_m| image:: /image/DAQ_move/move_rel_m.PNG
    :width: 60pt
    :height: 20pt

.. |home| image:: /image/DAQ_move/home.PNG
    :width: 60pt
    :height: 20pt

.. |stop| image:: /image/DAQ_move/stop.PNG
    :width: 60pt
    :height: 20pt

.. |where| image:: /image/DAQ_move/where.PNG
    :width: 60pt
    :height: 20pt

.. |abs| image:: /image/DAQ_move/abs.PNG
    :width: 60pt
    :height: 20pt

Hardware initialization
-----------------------

* ``Stage``: list of available hardware plugins of the DAQ_Move type.
* ``Ini. Stage``: Initialize the hardware with the given settings (see :ref:`plugin_doc` for details on how to set hardware settings.)
* ``Quit``: De-initialize the hardware and quit the module


Positioning
-----------

Once the hardware is initialized, the actual *position* is displayed on the *Current position* display
(bottom of :numref:`daq_move_gui_base`) while the absolute *position* can be set using the top spinbox
and apply it using the |green_arrow| button.

Advanced positioning
--------------------

More options can be displayed in order to precisely control the actuator by pressing the |plus_button| button.
The user interface will then look like :numref:`daq_move_gui_rel`.


   .. _daq_move_gui_rel:

.. figure:: /image/DAQ_Move/daq_move_gui_rel.PNG
   :alt: daq_move_gui_rel

   DAQ_Move user interface with controls

.. :download:`png <daq_move_gui_rel.png>`


The two new displayed spinbox relate to Absolute positioning (redundant with the one on the top)  and
Relative one.

* |home|: the actuator will try to reach a home position (knwon position or physical switch limit)
* |abs|: the actuator will try to reach the set Absolute position
* |move_rel|: the actuator will try to reach a relative position (+increment)
* |move_rel_m|: the actuator will try to reach a relative position (-increment)
* |where|: will update the current position display
* |stop|: stop the current motion (if possible)


Settings
--------

The hardware and module settings can be displayed in order to initialize correctly the actuator and add other
options by pressing the |settings| button. The user interface will then look like
:numref:`daq_move_gui_settings`.


   .. _daq_move_gui_settings:

.. figure:: /image/DAQ_Move/daq_move_gui_settings.PNG
   :alt: daq_move_gui_settings

   Full DAQ_Move user interface with controls and settings

.. :download:`png <daq_move_gui_settings.png>`

In the settings tree, there is two sections. The first relates to *Main settings* (not much there for
the moment apart for the selected stage type and *Controller ID* that is related to multiaxes controller.
The second relates to the hardware settings (the ones the hardware will need in order
to initialize...). There is also specific settings explained below.

.. _multiaxes_controller:

Multiaxes controller
^^^^^^^^^^^^^^^^^^^^

Sometimes one hardware controller can drive multiple actuators (for instance a XY translation stage). For
this particular case the controller should not be initialized multiple times. One should identify one actuator
refered to as *Master* and the other ones will be referred to as *Slave*. They will share the same controller
address represented in the settings tree by the *Controller ID* entry. These settings will be activated
within the plugin script where one can define a unique identifier for each actuator (U or V for the conex
in :numref:`daq_move_gui_settings`).

* ``Controller ID``: unique identifier of the controller driving the stage
* ``is Multiaxes``: boolean
* ``Status``: Master or Slave
* ``Axis``: identifier defined in the plugin script

See :download:`daq_move_Template.py <daq_move_Template.py>` for a detailed example. These settings are
really valid only when the module is used within the Dashboard framework that deals with multiple modules
at the same time as configured in the :ref:`preset_manager` interface.

Bounds
^^^^^^
if this section is activated (by clicking the *Set Bounds* entry) then the actuator *positions* will
be software limited between *min* and *max*. This can be used to prevent the actuator to reach dangerous
values for the experiment or anything else.

Scaling
^^^^^^^
If this section is activated (by clicking the *Use scaling* entry) then the *set* and *displayed* positions
will be scaled as:

.. code-block:: python

  new_position=scaling*old_position+offset

This can be useful for instance when one deals with translation stage used to delay a laser pulse with
respect to another. In that case it is easier to work with temporal units such as *femtoseconds* compared
to *mm* or other native controller unit.

Other settings
^^^^^^^^^^^^^^

* ``epsilon``: -**very important feature**- the actuator will try to reach the target position with a precision
  *epsilon*. So one could use it if one want to be sure the actuator really reached a given position before moving on.
  However if the set precision is too small, the actuator may never reached it and will issue a timeout
* ``Timeout``: maximum amout of time the module will wait for the actuator to reach the desired position.
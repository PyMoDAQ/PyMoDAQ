.. _DAQ_Move_module:

DAQ Move
========

This module is to be used to control any :term:`Actuator` hardware. An :term:`Actuator` is, in a general sense, any parameter
that one can control and may vary during an experiment.  The default actuator
is a Mock one (a kind of software based
actuator displaying a *position* and accepting absolute or relative *positioning*).

Introduction
------------

This module has a generic interface in the form of a dockable panel containing the interface for initialization,
the manual control of the actuator *position* and a side tree like interface displaying all the settings.
:numref:`daq_move_gui_base` shows the minimal interface of the module (in order to take minimal place in the
Dashboard)


   .. _daq_move_gui_base:

.. figure:: /image/DAQ_Move/daq_move_gui_base.PNG
   :alt: daq_move_gui_base

   Minimal DAQ_Move user interface



.. |green_arrow| image:: /image/DAQ_Move/green_arrow.PNG
    :width: 20pt
    :height: 20pt

.. |red_arrow| image:: /image/DAQ_Move/red_arrow.PNG
    :width: 20pt
    :height: 20pt

.. |plus_button| image:: /image/DAQ_Move/plus_button.PNG
    :width: 20pt
    :height: 20pt

.. |settings| image:: /image/DAQ_Move/settings_button.PNG
    :width: 20pt
    :height: 20pt

.. |refresh| image:: /image/DAQ_Move/loop_get_value.PNG
    :width: 20pt
    :height: 20pt

.. |quit| image:: /image/DAQ_Move/quit.PNG
    :width: 20pt
    :height: 20pt

.. |log| image:: /image/DAQ_Move/log.PNG
    :width: 20pt
    :height: 20pt

.. |move_rel| image:: /image/DAQ_Move/move_rel.PNG
    :width: 60pt
    :height: 20pt

.. |move_rel_m| image:: /image/DAQ_Move/move_rel_m.PNG
    :width: 60pt
    :height: 20pt

.. |home| image:: /image/DAQ_Move/home.PNG
    :width: 60pt
    :height: 20pt

.. |stop| image:: /image/DAQ_Move/stop.PNG
    :width: 60pt
    :height: 20pt

.. |where| image:: /image/DAQ_Move/where.PNG
    :width: 60pt
    :height: 20pt

.. |abs| image:: /image/DAQ_Move/abs.PNG
    :width: 60pt
    :height: 20pt

.. |init| image:: /image/DAQ_Move/init.PNG
    :width: 80pt
    :height: 20pt

Hardware initialization
-----------------------

* ``Actuator``: list of available instrument plugins of the DAQ_Move type, see :numref:`daq_move_gui_base_actuators`.
* |init|: Initialize the hardware with the given settings (see :ref:`instrument_plugin_doc` for details
  on how to set hardware settings.)
* |quit|: De-initialize the hardware and quit the module


   .. _daq_move_gui_base_actuators:

.. figure:: /image/DAQ_Move/daq_move_gui_actuators.PNG
   :alt: daq_move_gui_base

   Menu list displaying the available instrument plugin of type ``DAQ_Move``

Positioning
-----------

Once the hardware is initialized, the actuator's *value* is displayed on the *Current value* display
(bottom of :numref:`daq_move_gui_base`) while the absolute *value* can be set using one of the top spinbox
(respectively green or red) and apply it using respectively the |green_arrow| or |red_arrow| button. This double
positioning allows to quickly define two values and switch between them.

Advanced positioning
--------------------

More options can be displayed in order to precisely control the actuator by pressing the |plus_button| button.
The user interface will then look like :numref:`daq_move_gui_rel`.


   .. _daq_move_gui_rel:

.. figure:: /image/DAQ_Move/daq_move_gui_rel.PNG
   :alt: daq_move_gui_rel

   DAQ_Move user interface with finer controls


The two new displayed spinbox relate to *Absolute* positioning and *Relative* one.

* |home|: the actuator will try to reach a home position (known position or physical switch limit)
* |abs|: the actuator will try to reach the set *absolute* position
* |move_rel|: the actuator will try to reach a *relative* position (+increment)
* |move_rel_m|: the actuator will try to reach a *relative* position (-increment)
* |where|: will update the current actuator's value display
* |stop|: stop the current motion (if possible)


Settings
--------

The hardware and module settings can be displayed by pressing the |settings| button.
The user interface will then look like :numref:`daq_move_gui_settings`.


   .. _daq_move_gui_settings:

.. figure:: /image/DAQ_Move/daq_move_gui_settings.PNG
   :alt: daq_move_gui_settings

   Full DAQ_Move user interface with controls and settings

In the settings tree, there is two sections. The first relates to the *Main settings* of the actuator while
the second relates to the hardware settings (the ones the hardware will need in order
to initialize...). There is also specific settings explained below.


(not much there for
the moment apart for the selected stage type and *Controller ID* that is related to multi-axes controller.


Main Settings
^^^^^^^^^^^^^

* *Actuator type*: is recalling the instrument plugin class being selected
* *Actuator name*: is the name as defined in the preset (otherwise it is defaulted to *test*)
* *Controller ID*: is related to multi-axes controller (see :ref:`multiaxes_controller`)
* *Refresh value*: is the timer duration when grabbing the actuator's current value (see :ref:`daq_move_grabing`).


.. _multiaxes_controller:

Multiaxes controller
^^^^^^^^^^^^^^^^^^^^

Sometimes one hardware controller can drive multiple actuators (for instance a XY translation stage). In the
simplest use case, one should just initialize the instrument plugin and select (in the settings) which *axis* to
use, see :numref:`daq_move_gui_multiaxes`.


   .. _daq_move_gui_multiaxes:

.. figure:: /image/DAQ_Move/daq_move_gui_settings.PNG
   :alt: daq_move_gui_settings

   Selection of one of the axis this controller is able to drive.

Then the selected axis can be driven normally and you can switch at any time to another one.

It is more complex when you want to drive two or more of these multi-axes during a scan. Indeed, each one should be
considered in the Dashboard as one actuator. But if no particular care is taken, the Dashboard will try to initialize
the controller multiple times, but only one communication channel exists, for instance a COM port. The solution
in PyMoDAQ is to identify one actuator (one axis) as *Master* and the other ones will be referred to as *Slave*.
They will share the same controller
address (and actual driver, wrapper, ...) represented in the settings tree by the *Controller ID* entry.
These settings will be activated
within the instrument plugin class where one can define a unique identifier for each actuator
(U or V for the conex
in :numref:`daq_move_gui_settings`).

* ``Controller ID``: unique identifier of the controller driving the stage
* ``is Multiaxes``: boolean
* ``Status``: Master or Slave
* ``Axis``: identifier defined in the plugin script

These settings are
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
* ``Timeout``: maximum amount of time the module will wait for the actuator to reach the desired position.


.. _daq_move_grabing:

Grabbing the actuator's value
----------------------------



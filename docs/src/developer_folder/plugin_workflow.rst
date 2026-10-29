.. _plugin_workflow:

How an instrument plugin works with the Dashboard
=================================================

An instrument plugin (a ``DAQ_Move_*`` or ``DAQ_xDViewer_*`` class) is never called by the user interface directly. Three
objects talk to each other, and knowing which one lives in which thread explains most of the rules of
:ref:`instrument_plugin_doc`. The diagrams below show them; each one is followed by its text version.

* the **control module** (``DAQ_Move`` or ``DAQ_Viewer``, with its user interface) lives in the GUI thread;
* the **worker** (``ActuatorWorker`` in ``control_modules/daq_move.py``, ``DetectorWorker`` in
  ``control_modules/daq_viewer.py``) and the **plugin** it creates live in the *plugin thread*. The worker receives the
  commands of the control module, calls the methods of the plugin and sends back what the plugin emits;
* the **controller** is the object of the driver, created by the plugin in ``ini_stage`` or ``ini_detector``. It is
  used in the plugin thread, and can be shared by several plugins (see :ref:`plugin_workflow_init`).

The control module and the worker only exchange :py:class:`ThreadCommand<pymodaq.utils.daq_utils.ThreadCommand>` objects
through Qt signals: the control module emits ``command_hardware``, received by ``queue_command`` of the worker, and the
worker emits ``status_sig``, received by ``thread_status`` of the control module. The plugin reaches the control module
with ``emit_status``, which emits ``status_sig`` of its worker (see :ref:`instrument_plugin_doc`).

.. graphviz::
   :caption: The three layers and the threads

   digraph layers {
     rankdir=LR; node [shape=box, fontname="Helvetica", fontsize=10];
     subgraph cluster_gui { label="GUI thread"; style=dashed;
       ui [label="DAQ_Move / DAQ_Viewer\nuser interface"];
       cm [label="control module\nprocess_ui_cmds\nthread_status"]; }
     subgraph cluster_pl { label="Plugin thread (one per controller)"; style=dashed;
       w [label="worker\nActuatorWorker / DetectorWorker\nqueue_command"];
       p [label="your plugin\nDAQ_Move_xxx / DAQ_xDViewer_xxx"];
       c [label="controller\nthe driver object", shape=ellipse]; }
     ui -> cm [label="command_sig"]; cm -> ui [label="display"];
     cm -> w [label="command_hardware\n(ThreadCommand)"];
     w -> cm [label="status_sig\n(ThreadCommand)"];
     w -> p [label="calls the methods"];
     p -> w [label="emit_status,\nmove_done_signal,\ndte_signal"];
     p -> c [label="uses"];
   }

Text version: the user interface sends its commands to the control module (``command_sig``). The control module sends a
``ThreadCommand`` to the worker with ``command_hardware``. The worker lives in the plugin thread and calls the methods
of the plugin (``move_abs``, ``grab_data``...), which use the controller. What the plugin emits (``emit_status``,
``move_done_signal``, ``dte_signal``) goes back through the worker and ``status_sig`` to the ``thread_status`` method of
the control module, which updates the user interface and emits its own signals for the extensions. Do not touch a widget
from the plugin: send a ``ThreadCommand``.

.. _plugin_workflow_init:

Initialization and closing
--------------------------

.. graphviz::
   :caption: Initialization of an instrument, with a master and a slave

   digraph init {
     rankdir=TB; node [shape=box, fontname="Helvetica", fontsize=10];
     a [label="the user checks Init (or the Dashboard applies an experiment)\nDAQ_Move / DAQ_Viewer: init_hardware"];
     b [label="the control module creates the worker\nmaster: a new QThreadProxy\nslave: the thread of its master (an error if there is none)"];
     c [label="worker.moveToThread(thread)\nthe thread is started by the master only"];
     d [label="command_hardware -> worker.queue_command\nstatus_sig -> control module thread_status"];
     e [label="ThreadCommand INI_HARDWARE is emitted"];
     f [label="worker.ini_hardware: creates the plugin,\ncalls ini_stage(controller) / ini_detector(controller)\nthe slave receives the controller of its master"];
     g [label="status_sig: INI_HARDWARE\n(initialized, info, controller)"];
     h [label="control module: init_signal,\ninit button colour (green master, magenta slave)"];
     a -> b -> c -> d -> e -> f -> g -> h;
   }

Text version:

#. The control module creates its worker. The first module of a *Controller ID* (the master) creates a thread; a slave
   needs the thread of its master and refuses to initialize without it.
#. The worker is moved to that thread, and the signals ``command_hardware`` and ``status_sig`` are connected.
#. The ``INI_HARDWARE`` command makes the worker create the plugin and call ``ini_stage`` or ``ini_detector``, in the
   plugin thread. A slave gets the controller of its master as argument; the master creates it.
#. The result (``initialized``, ``info``, the controller) comes back as an ``INI_HARDWARE`` status. The control module
   stores the controller, emits ``init_signal`` and colours its init button (green for a master, magenta for a slave). A
   failed initialization marks the module in error.
#. Closing: the ``CLOSE`` command makes the worker call the ``close`` method of the plugin. When the master is closed,
   the workers of its slaves are closed too and the thread is stopped (``quit`` then ``wait``, up to 5 s before it is
   terminated with a warning).

Moving an actuator
------------------

.. graphviz::
   :caption: ``move_abs`` of a ``DAQ_Move`` (with polling, the default)

   digraph move {
     rankdir=LR; node [shape=box, fontname="Helvetica", fontsize=10];
     subgraph cluster_gui { label="GUI thread"; style=dashed;
       u [label="move button or\nextension: move_abs(value)"];
       s [label="thread_status\nGET_ACTUATOR_VALUE: display\nMOVE_DONE: display, move_done_signal"]; }
     subgraph cluster_pl { label="Plugin thread"; style=dashed;
       q [label="worker.queue_command\nMOVE_ABS -> worker.move_abs\n(units converted to axis_unit)"];
       m [label="plugin.move_abs(value)"];
       t [label="poll_moving: poll_timer\ncheck_target_reached\nget_actuator_value every interval"];
       d [label="plugin.move_done()\nmove_done_signal -> worker.move_done"]; }
     u -> q [label="RESET_STOP_MOTION,\nMOVE_ABS"];
     q -> m -> t;
     t -> s [label="GET_ACTUATOR_VALUE\nuntil the target is reached"];
     t -> d [label="target reached"];
     d -> s [label="MOVE_DONE (once)"];
   }

Text version:

#. ``DAQ_Move.move_abs`` does nothing when the value equals the current one (within ``epsilon``): it reports a
   ``MOVE_DONE`` at once. Otherwise it sends ``RESET_STOP_MOTION`` and ``MOVE_ABS`` to the worker.
#. The worker converts the position to the units of the axis (``axis_unit``), resets ``move_is_done``, calls
   ``plugin.move_abs`` and then ``plugin.poll_moving``.
#. With polling (the default), ``poll_moving`` starts the timer of the plugin. At each interval
   (``polling_interval_ms`` of the configuration) ``check_target_reached`` calls ``get_actuator_value``, sends it to the
   control module (``GET_ACTUATOR_VALUE`` status, displayed live), and stops with a ``RAISE_TIMEOUT`` status when the
   ``timeout`` setting is exceeded.
#. When the target is reached, ``move_done`` of the plugin emits ``move_done_signal``. The worker forwards it **once**
   per move as a ``MOVE_DONE`` status, and the control module displays the position and emits its own
   ``move_done_signal``, which is what extensions wait for.
#. Without polling (``ispolling`` False), no timer runs: ``poll_moving`` itself calls ``move_done`` just after
   ``move_abs`` returned, with the target value or, if the plugin has an encoder, the value it reads. A plugin whose move
   only ends later (a homing, a callback of the driver) calls ``move_done`` itself when it ends.
#. An exception raised by a plugin method is caught by the worker and sent as an ``ERROR`` status: the control module
   writes it in its status bar and is marked in error until the next status coming from the hardware.

``move_rel`` follows the same path, and ``move_home`` calls ``plugin.move_home``, which must call ``move_done`` when the
homing is over. ``stop_motion`` sets ``motion_stopped``, calls ``plugin.stop_motion`` and stops the timer.

Grabbing data
-------------

.. graphviz::
   :caption: ``grab_data`` of a ``DAQ_Viewer``

   digraph grab {
     rankdir=LR; node [shape=box, fontname="Helvetica", fontsize=10];
     subgraph cluster_gui { label="GUI thread"; style=dashed;
       u [label="Snap or Grab button:\nDAQ_Viewer.grab_data"];
       sd [label="show_data\nviewers, then grab_done_signal"]; }
     subgraph cluster_pl { label="Plugin thread"; style=dashed;
       q [label="worker.queue_command\nSINGLE / GRAB -> worker.grab_data"];
       g [label="plugin.grab_data(Naverage, live, ...)\nthe controller acquires"];
       r [label="data_ready\nsoftware averaging if\nNaverage > 1 and no hardware_averaging"]; }
     u -> q [label="SINGLE or GRAB\n(Naverage)"];
     q -> g;
     g -> r [label="dte_signal\n(DataToExport)"];
     r -> sd [label="data_detector_sig"];
     u -> q [label="STOP_GRAB", style=dashed];
   }

Text version:

#. The Snap button sends ``SINGLE`` and the Grab button ``GRAB`` to the worker, with the number of data to average.
#. The worker calls ``plugin.grab_data``. If the plugin sets ``live_mode_available``, it is called once and streams its
   data until ``STOP_GRAB``; otherwise the worker calls it again after each data, waiting ``wait_time`` between two
   calls in continuous mode.
#. The plugin emits its data with ``dte_signal`` (a ``DataToExport``, see :ref:`data_emission`). The worker's
   ``data_ready`` averages them if ``Naverage`` is larger than 1 and the plugin does not average itself
   (``hardware_averaging``), then emits ``data_detector_sig``.
#. In the GUI thread, ``show_data`` copies the data, processes them (background, live averaging), sends them to the
   viewers and emits ``grab_done_signal``, which extensions and the saving use.
#. ``STOP_GRAB`` sets ``grab_state`` to False and calls ``plugin.stop``; the worker then sends ``grab_stopped`` to the
   control module, which emits ``grab_status(False)``.

A thread of the driver (a callback or a wait for the camera, see :ref:`data_ready`) never touches the control module: it
only emits ``dte_signal`` of the plugin, or a Qt signal received in the plugin thread.

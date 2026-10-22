.. _modules_manager:

The ModulesManager
==================

``ModulesManager`` (``pymodaq.utils.managers.modules.modules_manager``) is how an extension reaches the actuators
(``DAQ_Move``) and detectors (``DAQ_Viewer``) of the Dashboard: it lists them, remembers which of them are *selected*,
moves the selected actuators, grabs the selected detectors, and tells you when they are done. An extension never creates
control modules (see :ref:`custom_app`), it uses them through its ``ModulesManager``.

.. contents::
   :local:
   :depth: 2

Where you get one
-----------------

* ``self.modules_manager`` in a ``CustomExt`` (and in any object using ``DashboardMixin``). By default it is a
  ``ModulesManager`` created for this object by ``init_dashboard``: its lists hold the same ``DAQ_Move`` and ``DAQ_Viewer``
  objects as the Dashboard, but **its selection is its own**, so two extensions can work with different instruments at
  the same time. Give another class with the ``module_manager_class`` argument of ``CustomExt.__init__`` if you need one.
* ``dashboard.modules_manager``, the manager of the Dashboard. A class with ``own_modules_manager = False`` (the State
  and ROI managers) gets this one as its ``modules_manager``. Its selection is shared by everything using it: the *Move* and
  *Scanner* elements of the Sequencer move through it (the *Grab* and *Choice* elements have a manager of their own).
* ``ModulesManager(detectors=..., actuators=...)`` for tests or scripts: it takes lists of modules, and selects none.

The lists are filled by the Dashboard when an experiment is applied, and an extension refreshes its own copy in
``do_things_after_experiment_set`` (see :ref:`customext_experiment_state`). **Setting the lists empties the selection**
(``actuators_all = ...``, ``detectors_all = ...``, and so ``do_things_after_experiment_set``): choose the modules again
after a new experiment.

What it holds
-------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Attribute
     - Content
   * - ``detectors_all``, ``actuators_all``, ``modules_all``
     - all the ``DAQ_Viewer``, all the ``DAQ_Move``, both
   * - ``detectors``, ``actuators``, ``modules``
     - the selected ones
   * - ``detectors_name``, ``actuators_name``, ``modules_name``
     - the titles of all of them (``modules_name`` is all the modules)
   * - ``selected_detectors_name``, ``selected_actuators_name``
     - the titles of the selected ones. Can be set (see below)
   * - ``Ndetectors``, ``Nactuators``
     - the number of selected modules
   * - ``get_mod_from_name(name, mod)``, ``get_mods_from_names(names, mod)``
     - the module(s) of this title, ``mod`` is a ``ModuleType`` (``Detector`` by default, ``Actuator`` or ``Control`` for
       both). ``get_mod_from_name`` returns ``None`` and logs a warning if the title is unknown
   * - ``settings_tree``, ``settings``
     - the parameter tree to put in your UI: two lists with check boxes, to select the modules, and the *probe* actions
       below. It is a ``ParameterManager``: the selection made by the user is the one of ``selected_*_name``

The module titles are the identifiers: they are unique, they are what you give to select a module, and they are stamped as
the ``origin`` of the data coming back from a module.

Selecting modules
-----------------

Everything below acts on the **selected** modules. Select by title::

    self.modules_manager.selected_detectors_name = ['Det1', 'Det3']
    self.modules_manager.selected_actuators_name = ['X_axis']

The selection can also be made by the user in ``settings_tree``. Two traps:

* A name that is not in the list of the manager is not an error: **the whole assignment is ignored** and the selection
  stays as it was (``['X', 'unknown']`` selects nothing new). Check ``selected_*_name`` if the names come from a
  settings file.
* The selection starts empty, and is emptied each time the lists are set (new experiment).

Signals
-------

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Signal
     - Emits
     - When
   * - ``detectors_changed``, ``actuators_changed``
     - the list of the selected titles
     - the selection changed (by the user, by code, or because the lists were set)
   * - ``det_done_signal``
     - a ``DataToExport`` with the data of all the selected detectors
     - all of them have answered a grab
   * - ``move_done_signal``
     - a ``DataToExport`` of ``DataActuator``, one per selected actuator
     - all of them have reached their target (or ``move_actuators`` has ended, on a timeout too)
   * - ``timeout_signal``
     - the list of the titles that did not answer
     - a grab or a move was not completed in time (see below)
   * - ``modules_added_signal``
     - nothing
     - ``add_modules`` was called

Grabbing data
-------------

The detectors have to be *connected* to the manager for it to count their answers: ``connect_detectors()`` connects the
``grab_done_signal`` of the selected detectors to the manager, ``connect_detectors(False)`` disconnects them. The
``*_with_callback`` methods do it for you.

``grab_data_with_callback(callback=..., Naverage=None, check_do_override=True, do_connect_modules=True)``
    Asks each selected detector for a snap and returns immediately. ``callback(dte)`` is called with the data of all of
    them when the last one has answered. It is connected to ``det_done_signal``, and **stays connected**: call
    ``forget_callback(callback, module_type=ModuleType.Detector)`` in the callback (or when a timeout is reported) to
    disconnect it and the detectors.

``grab_data(...)``
    The same, blocking: it waits for the answers, processing the Qt events in a loop, and returns the ``DataToExport``.
    You have to call ``connect_detectors()`` before and ``connect_detectors(False)`` after: without it nothing counts the
    answers and the call returns an empty ``DataToExport`` after the timeout.

``Naverage`` overrides the number of averages of each detector for this grab (otherwise the one of the module is used).
``check_do_override`` skips the detectors that a ``DataMixer`` detector is computing from.

The data of the detectors are told apart by their ``origin``, the title of the detector (a detector with several channels
sends one ``DataWithAxes`` per channel, all with the same ``origin``).

Moving actuators
----------------

The positions are given in a ``DataToExport`` holding one ``DataActuator`` per actuator, **named like the actuator**
(a ``DataToActuators`` also carries the mode). Their number has to be the number of selected actuators.

``move_actuators_with_callback(dte_act, mode=MoveType.ABS, callback=None, do_connect_modules=True)``
    Selects the actuators named in ``dte_act``, starts the moves and returns immediately. ``callback(dte)`` is called with
    the positions reached when all the actuators have told they are done. Same rule as for the grab: call
    ``forget_callback(callback, module_type=ModuleType.Actuator)``. The default mode is absolute, give
    ``mode=MoveType.REL`` for relative moves (a ``DataToActuators`` brings its own mode, which is then used). Older
    versions of this method defaulted to relative moves: give the mode explicitly in code that has to run on them.

``move_actuators(dte_act, mode=MoveType.ABS, polling=True)``
    Starts the moves and, with ``polling=True``, waits for them in a loop (blocking, as ``grab_data``). The actuators
    have to be connected (``connect_actuators()``) and selected beforehand. Deprecated in favour of the callback version,
    which does not run a nested event loop.

``connect_and_move_actuators(dte_act, mode, polling, slot, signal)``
    Selects the actuators of ``dte_act``, connects them, calls ``move_actuators`` and disconnects them.

An actuator is *done* when its plugin has called ``move_done`` (see :ref:`move_home` for the homing), so that a move is as slow
as the slowest actuator.

``connect_actuators(connect=True, slot=None, signal='move_done')`` and ``connect_detectors(connect, slot)`` can also be
used to follow the modules continuously, with your own slot: ``signal='current_value'`` connects the
``current_value_signal`` of the selected actuators, and ``slot`` receives the data of each detector, as the DAQ_Logger does.

Timeouts
--------

A grab or a move that is not completed in time does not raise: the manager logs an error and emits
``timeout_signal`` with the titles of the modules it did not hear from. The duration is read from the configuration at
each call: ``[viewer] timeout`` for the detectors (in ms, 10000 by default) and ``[actuator] polling_timeout_s`` for the
actuators (in s, 20 by default). A blocking call returns at the timeout (with the data received so far); with a callback,
the callback is never called and the timeout only tells you. Connect ``timeout_signal`` to stop what you were doing and
call ``forget_callback``.

Probing
-------

The two actions of ``settings_tree`` (*Probe detectors* and *Probe actuators*) are a quick check for the user. The first
snaps the selected detectors and lists the channels they send in the tree below (``get_probed_data_full_names(dim)``
returns their names, to offer them in a list); the second asks for target positions in a dialog, moves the selected
actuators and shows the positions reached. ``probe_detectors()`` and ``probe_actuators()`` can be called from code.
``get_det_data_list`` and ``test_move_actuators`` are the deprecated names of these methods.

Use cases
---------

Each snippet is run by ``tests/utils/managers/modules_manager_use_cases_test.py`` on mock modules.

Move, then grab, without blocking the GUI
+++++++++++++++++++++++++++++++++++++++++

The chain of callbacks used by the Sequencer elements (``sequencer/utilities/elements/move.py``, ``grab.py`` and
``scanner.py``) and by the ramping extension (``ramping/ramping.py``, ``go_to_ini_ramp``):

.. code-block:: python

    from pymodaq.control_modules.enums import MoveType
    from pymodaq.utils.data import DataActuator
    from pymodaq.utils.managers.modules import ModuleType
    from pymodaq_data.data import DataToExport

    def start(self, positions: dict[str, float], detectors: list[str]):
        dte_move = DataToExport('targets', data=[DataActuator(name, data=value)
                                                 for name, value in positions.items()])
        self.modules_manager.selected_detectors_name = detectors
        self.modules_manager.move_actuators_with_callback(dte_move, mode=MoveType.ABS,
                                                          callback=self._on_move_done)

    def _on_move_done(self, dte_positions: DataToExport):
        self.modules_manager.forget_callback(self._on_move_done, module_type=ModuleType.Actuator)
        self.modules_manager.grab_data_with_callback(callback=self._on_grab_done)

    def _on_grab_done(self, dte: DataToExport):
        self.modules_manager.forget_callback(self._on_grab_done, module_type=ModuleType.Detector)
        ...  # use the data: dte.get_data_from_name(...), dte.get_origins()

``move_actuators_with_callback`` selects the actuators, ``grab_data_with_callback`` uses the detectors selected before.
Nothing waits: the GUI stays alive during the moves and the grabs.

A loop that blocks until each step is done
++++++++++++++++++++++++++++++++++++++++++

The optimizers (``optimizers_base/optimizer.py``, ``run_opti``), the PID (``pid/pid_controller.py``) and the Data Mixer
(``data_mixer/data_mixer.py``, ``snap``) use the blocking calls, each step needing the result of the previous one:

.. code-block:: python

    self.modules_manager.selected_actuators_name = ['X_axis']
    self.modules_manager.selected_detectors_name = ['Det1']
    self.modules_manager.connect_actuators()
    self.modules_manager.connect_detectors()
    try:
        while self.running:
            positions = self.modules_manager.move_actuators(dte_targets, mode=MoveType.ABS)
            dte = self.modules_manager.grab_data()
            ...
    finally:
        self.modules_manager.connect_actuators(False)
        self.modules_manager.connect_detectors(False)

Connect once before the loop, disconnect after it (in a ``finally``). Disconnect before you change the selection:
``connect_detectors(False)`` and ``connect_actuators(False)`` disconnect the modules **selected at that time**, the ones
unselected since stay connected. Prefer the callbacks when the GUI has to stay responsive.

Choose the modules, and follow the user
+++++++++++++++++++++++++++++++++++++++

Put ``self.modules_manager.settings_tree`` in your UI to let the user select, as ``daq_logger`` does (``daq_scan`` puts
the parameters of the manager in its own trees), and
react to ``actuators_changed`` and ``detectors_changed`` (``daq_scan.py``: ``clear_plot_from``, ``update_actuators``).
Or select from your own settings with ``selected_*_name``, as the optimizers do from their model
(``optimizers_base/models.py``).

React to a new experiment
+++++++++++++++++++++++++

The modules are destroyed and created again with each experiment: the objects you kept (a ``DAQ_Move``, a list, a signal
connection) are gone and the selection is empty. Reimplement ``do_things_after_experiment_set``, call ``super()``
first, and rebuild from ``self.modules_manager``:

.. code-block:: python

    def do_things_after_experiment_set(self, experiment_name: str, show_dashboard: bool = None):
        super().do_things_after_experiment_set(experiment_name, show_dashboard)
        self.settings.child('actuator').setLimits(self.modules_manager.actuators_name)
        self.settings.child('detectors').setValue(dict(all_items=self.modules_manager.detectors_name,
                                                       selected=[]))

(``ramping/ramping.py`` does this for its actuator and detector lists.)

Rules
-----

* Never create control modules in an extension, use the ones of ``self.modules_manager``.
* Select the modules before moving or grabbing; give one position per selected actuator, named like it.
* Connect before a blocking call and disconnect after it; call ``forget_callback`` for each ``*_with_callback`` call, in
  the callback and on a timeout.
* Handle ``timeout_signal``: a missing answer is reported by it only.
* Start again from an empty selection after a new experiment.
* Do not share a ``ModulesManager`` between extensions, unless it is on purpose the one of the Dashboard.

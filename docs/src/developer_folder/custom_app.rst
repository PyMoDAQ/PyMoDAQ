.. _custom_app:

CustomApp and CustomExt
=======================

.. toctree::
   :maxdepth: 3
   :caption: Contents:

.. _custom_app_context:

The big picture
---------------

PyMoDAQ is split in four packages, each building on the previous one: ``pymodaq_utils`` (helpers, no GUI),
``pymodaq_data`` (data objects and h5 saving), ``pymodaq_gui`` (widgets, ``CustomApp``, the managers) and ``pymodaq``
(the instrument layer: control modules, the Dashboard and the extensions). What you build depends on whether your
interface needs instruments, and where it is meant to live:

* The :ref:`control modules <control_modules>` (``DAQ_Move`` for actuators, ``DAQ_Viewer`` for detectors) are the
  objects that talk to the instruments, through the instrument plugins, each plugin running in its own thread.
* The :ref:`Dashboard <Dashboard_module>` creates and owns the control modules of an *experiment*, and lists the
  installed *extensions* in its menu. The extensions that ship with PyMoDAQ (:ref:`DAQ_Scan_module`, DAQ_Logger,
  PID, optimizers, data mixer, sequencer, ramping...) and the ones installed from plugin packages
  (see :ref:`extension_plugins`) are all built the same way.
* An *application* is a program that you start yourself, independent of the Dashboard. It is the right choice only when no instrument is involved.

``CustomApp`` is the common base of the Dashboard, of the extensions and of the applications: it provides the
user-interface skeleton (docks, menus, toolbars, actions, settings tree, status bar, h5 file handling, worker
threads). ``CustomExt`` is the specialisation for what runs inside a Dashboard, because it needs to use the
instruments the Dashboard already controls. So the rule is:

.. list-table::
   :header-rows: 1

   * - You want to build
     - Derive from
     - Instruments come from
     - Started by
   * - An interface that needs no instrument (data viewer, analysis tool, h5 browser)
     - ``CustomApp``
     - none
     - your script
   * - A tool using the instruments of the current experiment (scan, logging, feedback, optimization)
     - ``CustomExt``
     - the Dashboard, through ``self.modules_manager``
     - the Dashboard *Extensions* menu, or your script through ``create_extension``

.. graphviz::
   :caption: Where CustomApp and CustomExt sit among PyMoDAQ's objects

   digraph context {
     rankdir=TB; node [shape=box, fontname="Helvetica", fontsize=10]; compound=true;
     subgraph cluster_gui { label="pymodaq_gui"; style=dashed; CustomApp [label="CustomApp"]; }
     subgraph cluster_pymodaq { label="pymodaq"; style=dashed;
       CustomExt [label="CustomExt"]; DashBoard [label="DashBoard"];
       ext [label="Extensions\n(DAQ_Scan, DAQ_Logger, ...,\nand those of plugin packages)"];
       cm [label="Control modules\nDAQ_Move / DAQ_Viewer"];
     }
     plugins [label="Instrument plugins\n(pymodaq_plugins_*)"]; hw [label="Hardware", shape=ellipse];
     apps [label="Your standalone apps"];
     CustomExt -> CustomApp [label="extends"]; DashBoard -> CustomApp [label="extends"];
     ext -> CustomExt [label="extend"]; apps -> CustomApp [label="extend"];
     DashBoard -> cm [label="creates"]; DashBoard -> ext [label="loads (entry points)"];
     ext -> cm [label="use through the\nModulesManager", style=dashed];
     cm -> plugins [label="load"]; plugins -> hw [label="drive"];
   }

Text version of the diagram:

* ``CustomApp`` (in ``pymodaq_gui``) is extended by ``DashBoard``, by ``CustomExt`` and by your standalone applications.
* ``CustomExt`` (in ``pymodaq``) is extended by every Dashboard extension, those shipped with PyMoDAQ as well as those
  in plugin packages.
* The ``DashBoard`` creates the control modules and loads the extensions declared as entry points.
* An extension uses the control modules of the Dashboard through its ``ModulesManager``; it does not create them (see :ref:`modules_manager`).
* The control modules load the instrument plugins, which drive the hardware.

.. note::

  A generic base class ``CustomApp`` located in ``pymodaq_gui.utils.custom_app`` can be used to
  build very quickly standalone *Applications*. ``CustomExt`` (``pymodaq.utils.custom_ext``) extends ``CustomApp``
  with what deals with instruments and the Dashboard, and is the base class of any *Dashboard extension*
  (the *DAQ_Logger* extension has been built using it, as well as some examples in the example folder).
  See :ref:`custom_app_structure`.

Writing a CustomApp or a CustomExt
----------------------------------

Below you'll find the skeleton of a *CustomApp* (a *CustomExt* is written the same way) subclassing the base class and methods you
have to override with your App/Extension specifics:

.. code-block:: python

    class CustomAppExample(gutils.CustomApp):

        # list of dicts enabling a settings tree on the user interface
        params = [
            {'title': 'Main settings:', 'name': 'main_settings', 'type': 'group', 'children': [
                {'title': 'Save base path:', 'name': 'base_path', 'type': 'browsepath',
                 'value': config['data_saving']['h5file']['save_path']},
                {'title': 'File name:', 'name': 'target_filename', 'type': 'str', 'value': "", 'readonly': True},
                {'title': 'Date:', 'name': 'date', 'type': 'date', 'value': QDate.currentDate()},
                {'title': 'Do something, such as showing data:', 'name': 'do_something', 'type': 'bool', 'value': False},
            ]},
        ]

        def __init__(self, dockarea, dashboard=None):
            super().__init__(dockarea)
            # init the App specific attributes
            self.raw_data = []
            self.setup_ui()  # calls the methods below, in the order given in the lifecycle table

        def setup_docks_and_widgets(self):
            '''
            subclass method from CustomApp
            '''
            logger.debug('setting docks')
            self.dock_settings = gutils.Dock('Settings', size=(350, 350))
            self.dockarea.addDock(self.dock_settings, 'left')
            self.dock_settings.addWidget(self.settings_tree, 10)
            logger.debug('docks are set')

        def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
            '''
            subclass method from CustomApp
            '''
            logger.debug('settings menu')
            file_menu = self.add_menu('file', 'File')
            file_menu.addSeparator()
            logger.debug('menu set')

        def setup_actions(self):
            '''
            subclass method from ActionManager
            '''
            logger.debug('setting actions')
            self.add_action('quit', 'Quit', 'close2', "Quit program",
                toolbar=self.toolbar, menu='file')
            self.add_action('grab', 'Grab', 'camera', "Grab from camera", checkable=True, toolbar=self.toolbar)
            logger.debug('actions set')

        def connect_things(self):
            '''
            subclass method from CustomApp
            '''
            logger.debug('connecting things')
            self.connect_action('quit', self.quit_fun)
            self.connect_action('grab', self.grab)
            logger.debug('connecting done')

        def value_changed(self, param):
            logger.debug(f'calling value_changed with param {param.name()}')
            if param.name() == 'do_something':
                if param.value():
                    self.settings.child('main_settings', 'something_done').setValue(True)
                else:
                    self.settings.child('main_settings', 'something_done').setValue(False)

            logger.debug(f'Value change applied')

        def grab(self, grab: bool):
            ...  # all other methods required by your Application class

In a few lines of codes, you'll get an application running. For the available *Parameter* available
for your `settings_tree`, see :ref:`Settings <parameter_tree>`.

.. _custom_app_structure:

Structure of the classes
------------------------

``CustomApp`` is a thin class that assembles three building blocks. ``CustomExt`` adds what is needed to live
inside a Dashboard. :numref:`custom_app_classes` shows who brings what.

.. _custom_app_classes:

.. graphviz::
   :caption: Class structure of CustomApp and CustomExt

   digraph classes {
     rankdir=BT; node [shape=box, fontname="Helvetica", fontsize=10];
     QObject;
     ActionManager [label="ActionManager\n(pymodaq_gui.managers)\nadd_action, add_menu, add_toolbar,\nconnect_action, set_action_enabled"];
     ParameterManager [label="ParameterManager\n(pymodaq_gui.managers)\nparams, settings, settings_tree,\nvalue_changed, child_added, param_deleted,\nparam_activated"];
     CustomApp [label="CustomApp\n(pymodaq_gui.utils)\ndockarea, mainwindow, docks, menubar,\nstatusbar, thread_manager, h5_manager,\nsetup_ui, quit_fun"];
     DashboardMixin [label="DashboardMixin\n(pymodaq.utils.dashboard_mixin)\ndashboard, is_dashboard_available, modules_manager,\nexperiment_manager, state_manager,\ncreate_dashboard_toolbar, show_dashboard"];
     CustomExt [label="CustomExt\n(pymodaq.utils.custom_ext)"];
     Managers [label="Managers working on the Dashboard\n(ExperimentManager, StateManager, ROIManager...)"];
     CustomApp -> QObject; CustomApp -> ActionManager; CustomApp -> ParameterManager;
     CustomExt -> CustomApp; CustomExt -> DashboardMixin;
     Managers -> CustomApp; Managers -> DashboardMixin;
   }

Text version of the diagram:

* ``CustomApp(QObject, ActionManager, ParameterManager)`` lives in ``pymodaq_gui.utils.custom_app``.
* ``ActionManager`` brings the actions, and their placement in the toolbars and menus: ``add_action``, ``add_menu``,
  ``add_toolbar``, ``connect_action``, ``set_action_enabled``, ``set_action_checked``.
* ``ParameterManager`` brings the settings tree: the class attribute ``params``, the ``settings`` Parameter, the
  ``settings_tree`` widget and the callbacks ``value_changed``, ``child_added``, ``param_deleted`` and ``param_activated`` (the button of an
  ``action`` or ``action_led`` parameter has been clicked).
* ``CustomApp`` itself brings the dock area (``dockarea``, ``docks``), the optional ``mainwindow``, the menu and
  status bars, the ``h5_manager`` and the ``thread_manager``, and the ``setup_ui`` sequence.
* ``DashboardMixin`` lives in ``pymodaq.utils.dashboard_mixin`` and holds everything dealing with the Dashboard, see
  :ref:`dashboard_mixin`.
* ``CustomExt(DashboardMixin, CustomApp)`` lives in ``pymodaq.utils.custom_ext``. It takes the ``dashboard`` as second
  argument and sets it up with the mixin.

The ``parent`` given to the constructor can be a ``DockArea``, a ``QMainWindow`` or a ``QWidget``: this decides
whether ``dockarea`` and ``mainwindow`` are created by the app or reused from the parent.

.. _dashboard_mixin:

DashboardMixin
++++++++++++++

``DashboardMixin`` (``pymodaq.utils.dashboard_mixin``) gathers what an object needs to work with a ``DashBoard``. It is
shared by the extensions (``CustomExt``) and by the managers that act on the Dashboard (``ExperimentManager``,
``StateManager``, ``ROIManager``, ``ExtensionManager``, ``Overshooter``, ``ScanManager``). It lives in ``pymodaq``
because the lower packages (``pymodaq_gui``, with ``CustomApp`` and ``ManagerBase``) cannot import ``pymodaq``: they
know nothing about the Dashboard.

* ``dashboard``: the ``DashBoard``, or ``None`` if the object runs without it. ``is_dashboard_available`` tells which.
* ``modules_manager``: a ``ModulesManager`` created for the object from the detectors and actuators of the Dashboard
  (``None`` without Dashboard). Its class can be changed with the ``module_manager_class`` argument. It has its own
  selection of modules, and is filled when an experiment is applied. An object that only looks modules up, without
  selecting any (the State and ROI managers), sets the class attribute ``own_modules_manager = False`` and gets the
  ``ModulesManager`` of the Dashboard instead, always up to date.
* ``experiment_manager``, ``state_manager``: the managers of the Dashboard (``None`` without Dashboard).
* ``do_things_after_experiment_set(experiment_name, show_dashboard=None)``: called each time an experiment is applied,
  see below. The base implementation refreshes ``modules_manager``.
* ``create_dashboard_toolbar`` and ``show_dashboard``, see below.

The mixin has no ``__init__`` on purpose: the Qt side of the object (``QObject.__init__``...) has to be initialized
first, and the class using the mixin then calls ``init_dashboard(dashboard, module_manager_class)`` and
``connect_experiment_manager()``. ``CustomExt`` does so right after ``CustomApp.__init__`` (the call for an experiment
already applied waiting for the end of its ``setup_ui``, as it may use the user interface), and the managers through two
hooks of ``ManagerBase`` (``init_extra`` before the user interface is set up, so ``dashboard`` is available in
``setup_ui``, and ``finish_init`` once the manager is built). A new object working with the Dashboard is therefore
written ``class MyThing(DashboardMixin, CustomApp)`` (the mixin first) and does not need anything else.

A manager decides itself if its entries can be executed, by reimplementing ``can_execute_entry`` (``False`` in
``ManagerBase``). The managers working on the Dashboard return ``self.is_dashboard_available``.

What is executed depends on how ``execute_entry`` is called. ``execute_entry()`` (and ``execute_current_entry()``, what
the *Execute* action calls) executes the entry as it is currently set in the manager, unsaved changes included: the
manager gives a snapshot of its settings to ``_execute_entry`` and the entry file is left untouched. ``execute_entry(name_or_path)``
first loads that entry in the manager, replacing its current settings, then executes it: this is what external callers
(the Dashboard, the sequencer menus...) use to run a stored entry. A manager implementing ``_execute_entry`` therefore
only has to read the file it is given, and ``save_entries`` has to be able to write what the manager holds.
``execute_current_entry`` (the *Execute* action) can first ask whether to save the entry when the manager content
differs from the file (``has_unsaved_changes``): this is driven by the ``ask_before_executing_unsaved`` property of
``ManagerBase``, read from the ``[manager]`` section of the gui configuration (*gui.toml*), so it applies to every
manager.

.. _custom_app_lifecycle:

Lifecycle
---------

``setup_ui`` calls, in this order, the methods you reimplement:

.. list-table::
   :header-rows: 1

   * - Step
     - Method
     - What to put in it
   * - 1
     - ``__init__``
     - Call ``super().__init__`` (creates the settings tree, ``H5Manager`` and ``WorkerThreadManager``), set your
       own attributes, then call ``self.setup_ui()``.
   * - 2
     - ``setup_docks_and_widgets``
     - Create the docks and widgets (the settings tree is ``self.settings_tree``).
   * - 3
     - ``setup_menus_and_toolbars``
     - Create menus and toolbars with ``add_menu`` and ``add_toolbar``.
   * - 4
     - ``setup_workflow_actions``
     - Automatic if ``show_workflow_actions`` is True: start, stop, pause and log actions
       (``WorkFlowActions``).
   * - 5
     - ``setup_actions``
     - Create the actions with ``add_action``.
   * - 6
     - ``connect_things``
     - Connect actions and widget signals to your methods.
   * - 7
     - ``do_things_after_ui_setup``
     - Optional last touches. The window is then resized to ``_size_hint``.
   * - run
     - ``value_changed``, ``child_added``, ``param_deleted``, ``param_activated``
     - React to the user's changes in the settings tree.
   * - end
     - ``quit_fun`` (``CustomExt``: ``_quit_fun``)
     - Clean up. ``CustomApp.quit_fun`` exits the worker threads, closes the main window and disconnects the tree.
       In a ``CustomExt``, return False from ``_quit_fun`` to refuse quitting.

.. _custom_app_threads:

Supporting objects: threads, files and signals
----------------------------------------------

Three objects are created by ``CustomApp`` or by the worker pattern around it.

* ``H5Manager`` (``pymodaq_gui.managers.h5manager``): owns the ``H5Saver``, the file actions (``FileAction``: new
  file, load, save, show, open, close, settings) and the file status LED. ``FileStatus`` tells what happened when a
  file was opened (new, reopened, closed, another file reopened, no file). Signals: ``file_open_signal(bool)``,
  ``file_loaded_signal(Path)`` and ``command_sig(ThreadCommand)``. Reach it with ``self.h5_manager`` or
  ``self.h5saver``; hide some file actions with the ``h5_actions_not`` constructor argument.
* ``WorkerThreadManager`` (``pymodaq_gui.managers.runner_thread_manager``): ``self.thread_manager``. It creates a
  ``QThread`` for a ``ThreadWorker``, moves the worker into it (``create_thread_for_worker``), starts it
  (``start_thread``) and stops it (``exit_worker_thread``). Always talk to a worker with signals, a direct method
  call would run in the calling thread.
* ``ExtensionWorker`` (``pymodaq_gui.utils.app_worker``): the object that does the work of an extension while the
  user interface stays responsive (used by DAQ_Scan, DAQ_Logger, the Sequencer and Ramping). It has its own
  ``WorkerThreadManager`` and creates a ``SaverWorker`` (and optionally a ``ProcessorWorker``) in separate threads.
  The actions start, pause and stop of the app are connected to its ``start``, ``pause`` and ``stop`` methods, and
  you implement ``_start``, ``_pause`` and ``_stop``.

.. _custom_app_threads_fig:

.. graphviz::
   :caption: Threads and signals of an extension using an ExtensionWorker

   digraph threads {
     rankdir=LR; node [shape=box, fontname="Helvetica", fontsize=10]; fontsize=10;
     subgraph cluster_main { label="GUI thread"; style=dashed;
       app [label="CustomApp / CustomExt"]; h5m [label="H5Manager"]; ew [label="ExtensionWorker"];
     }
     subgraph cluster_saver { label="Saver thread"; style=dashed; sw [label="SaverWorker"]; }
     subgraph cluster_proc { label="Processor thread (optional)"; style=dashed; pw [label="ProcessorWorker"]; }
     app -> h5m [label="owns"]; app -> ew [label="start / pause / stop\n(WorkFlowActions)"];
     ew -> sw [label="data_to_save_signal\n(DataBundle)"];
     sw -> ew [label="n_jobs_done_signal\n(name, n)"];
     ew -> pw [label="data_to_process_signal"];
     pw -> ew [label="data_processed_signal\nn_jobs_done_signal"];
     ew -> app [label="workers_terminated"];
     ew -> h5m [label="close_file at the end"];
   }

Text version of the diagram:

#. The app (GUI thread) owns the ``H5Manager`` and, for the extensions that need it, an ``ExtensionWorker``.
#. The user presses start: the app calls ``ExtensionWorker.start``, which creates the ``SaverWorker`` (and the
   ``ProcessorWorker`` if ``has_data_processor``) with ``create_thread_for_worker`` and starts their threads.
#. For each piece of data, the ``ExtensionWorker`` emits ``data_to_save_signal`` (a ``DataBundle``) to the saver,
   which writes it in the h5 file and answers with ``n_jobs_done_signal(name, n_saved)``. The difference with the
   number of jobs sent is displayed as ``worker_tasks`` in the settings.
#. When the user presses stop, the emission towards the workers is disconnected, then once every queue is empty
   (``_workers_done``) the threads are exited, the file is closed through the ``H5Manager`` and
   ``workers_terminated`` is emitted.

.. _custom_app_patterns:

The patterns
------------

Two patterns cover almost every need: a standalone ``CustomApp`` when no instrument is involved, and a ``CustomExt``
run by the Dashboard as soon as instruments are. A third one, embedding control modules in a ``CustomApp``, exists
but is not advised (see its section).

Standalone app without instruments
++++++++++++++++++++++++++++++++++

Derive from ``CustomApp`` and give it a ``QMainWindow`` (or a ``DockArea`` placed in your own window). Nothing
else is needed: no Dashboard, no ``ModulesManager``. Examples are in ``pymodaq_gui/examples`` (for instance
``function_plotter.py`` and ``saving_loading.py``).

.. graphviz::
   :caption: Standalone app: who creates and owns what

   digraph standalone {
     node [shape=box, fontname="Helvetica", fontsize=10];
     script [label="your script"]; win [label="QMainWindow / DockArea"]; app [label="MyApp(CustomApp)"];
     script -> win [label="creates"]; script -> app [label="creates, passes the window"];
     app -> win [label="uses"]; app -> H5Manager [label="owns"]; app -> WorkerThreadManager [label="owns"];
   }

Text version: the script creates the window and the app; the app owns its ``H5Manager`` and
``WorkerThreadManager`` and fills the window. The app never calls the Dashboard. The lifecycle is the table above.

Extension of the Dashboard
++++++++++++++++++++++++++

Derive from ``CustomExt``. The ``DashBoard`` instantiates it from the extension entry point (see
:ref:`extension_plugins`) with a ``DockArea`` and itself: ``MyExtension(dockarea, dashboard)``. The control modules
already exist and are listed in ``self.modules_manager``.

.. graphviz::
   :caption: Extension: who creates and owns what

   digraph extension {
     node [shape=box, fontname="Helvetica", fontsize=10];
     dash [label="DashBoard"]; ext [label="MyExtension(CustomExt)"]; mm [label="ModulesManager"];
     cm [label="DAQ_Move / DAQ_Viewer"];
     dash -> cm [label="creates and owns"]; dash -> ext [label="creates (dockarea, dashboard)"];
     ext -> mm [label="creates, filled with the Dashboard's modules"];
     mm -> cm [label="references", style=dashed];
     ext -> H5Manager [label="owns"]; ext -> ExtensionWorker [label="owns (if needed)"];
     dash -> ext [label="experiment_manager.applied_entry\n-> do_things_after_experiment_set", style=dashed];
   }

Text version: the Dashboard owns the control modules and creates the extension. The extension creates a
``ModulesManager`` which only references the Dashboard's modules; it is refreshed each time an experiment entry is
applied (``do_things_after_experiment_set``). The extension owns its ``H5Manager`` and, if it acquires and saves data,
an ``ExtensionWorker``. Add ``create_dashboard_toolbar()`` in ``setup_menus_and_toolbars`` to show or hide the
Dashboard from the extension. Implement ``_quit_fun`` rather than ``quit_fun``; the Dashboard is shown again when
the extension quits.

.. _customext_experiment_state:

Experiment, State and the Dashboard toolbar in a CustomExt
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The *experiment* (the set of actuators and detectors of the Dashboard, see :ref:`experiment_manager`) and its *state*
(values of the instruments settings, see :ref:`state_manager`) belong to the Dashboard. A ``CustomExt`` does not create
its own managers: it reaches the Dashboard's ones, and can display their controls in its own window.

* ``self.experiment_manager`` and ``self.state_manager`` are the ``ExperimentManager`` and ``StateManager`` of the
  Dashboard (``None`` if the extension runs without Dashboard). Never create others, nor your own save/load of the
  instrument configurations.
* ``self.modules_manager`` is created for the extension, and filled with the actuators and detectors of the
  Dashboard. It is refreshed each time an experiment is applied, see below.
* Applying an experiment from the extension is the same thing as applying it from the Dashboard: the control
  modules are recreated by the Dashboard, then ``ExperimentManager.applied_entry`` (a ``Signal(str)`` carrying the
  experiment name) is emitted. Applying a state sets values in the existing control modules, with no change of the list
  of modules.

React to a new experiment by reimplementing ``do_things_after_experiment_set(experiment_name, show_dashboard)``.
``CustomExt.__init__`` connects it to ``applied_entry`` and also calls it once at startup if an experiment is already
applied (``experiment_manager.entry_applied``), so the extension is set up the same way whenever it is opened. The base
implementation updates ``self.modules_manager`` and shows or hides the Dashboard window: call it with ``super()`` when you
override it, then rebuild what depends on the instruments (lists of modules in your settings, signal connections to the
control modules...), as these were destroyed with the previous experiment.

``create_dashboard_toolbar`` creates a toolbar named *dashboard* in the main window of the extension (call it in
``setup_menus_and_toolbars`` or ``setup_actions``, once the actions can be added). It is the same toolbar as the one
described in :ref:`dashboard_external_toolbar`, with three optional groups:

.. list-table::
   :header-rows: 1

   * - Argument
     - Adds
     - Provided by
   * - ``add_dashboard=True``
     - the *Show/Hide Dashboard* toggle (action ``DashBoardToolbarActions.SHOW``, handled by ``show_dashboard``)
     - ``CustomExt``
   * - ``add_experiment=True``
     - a button opening the Experiment manager, a list of the experiments and a button applying the selected one
     - ``self.experiment_manager.get_external_toolbar_menu``
   * - ``add_state=True``
     - the same three controls for the states of the current experiment
     - ``self.state_manager.get_external_toolbar_menu``

``add_break=True`` puts the toolbar on a new row. For instance ``self.create_dashboard_toolbar(add_state=False)`` keeps the
experiment list but not the states, which is relevant for an extension that only needs to choose the instruments. The
lists of experiments and states are kept in sync with the ones of the Dashboard, they all show the same current entry. A
manager can also be used without its toolbar: ``get_external_toolbar_menu(toolbar, menu)`` fills any toolbar or menu you
give, so you can place the controls where you want in your interface.

.. graphviz::
   :caption: Experiment and State managers shared between the Dashboard and an extension

   digraph managers {
     rankdir=LR; node [shape=box, fontname="Helvetica", fontsize=10];
     subgraph cluster_dash { label="DashBoard"; style=dashed;
       em [label="ExperimentManager"]; sm [label="StateManager"]; cm [label="control modules"]; dtb [label="its own toolbars"]; }
     subgraph cluster_ext { label="Extension (CustomExt)"; style=dashed;
       etb [label="dashboard toolbar\n(create_dashboard_toolbar)"]; hook [label="do_things_after_experiment_set"]; mm [label="modules_manager"]; }
     em -> dtb [label="get_external_toolbar_menu"]; sm -> dtb;
     em -> etb [label="get_external_toolbar_menu"]; sm -> etb [label="get_external_toolbar_menu"];
     etb -> em [label="apply experiment", style=dashed]; etb -> sm [label="apply state", style=dashed];
     em -> cm [label="creates"];
     em -> hook [label="applied_entry(str)"]; hook -> mm [label="refresh"];
     mm -> cm [label="references", style=dashed];
   }

Text version: the Dashboard owns one ``ExperimentManager`` and one ``StateManager``. Each manager can display its
controls (open the manager, list of entries, apply) in any toolbar through ``get_external_toolbar_menu``: the Dashboard
does it for its own toolbars, and ``create_dashboard_toolbar`` does it for the extension. Applying an experiment, from
either toolbar, makes the Dashboard create the control modules, then ``applied_entry`` is emitted and the extension
refreshes its ``modules_manager`` in ``do_things_after_experiment_set``.

App embedding control modules directly (not advised)
++++++++++++++++++++++++++++++++++++++++++++++++++++

An app *can* create its own ``DAQ_Move`` and ``DAQ_Viewer`` objects without any Dashboard, but you should not do it.
Use a ``CustomExt`` run by the Dashboard instead: it is easier and better. The Dashboard already creates, initializes
and saves the settings of the instruments (experiment and state managers), and the extension just gets them through
``self.modules_manager``, with the toolbar and the file handling done for you. An app that embeds control modules has
to redo all this by itself and loses it (no experiment or state, no shared ``ModulesManager``).

If you still need it, ``create_load_daq_move`` and ``create_load_daq_viewer`` in
``pymodaq.utils.gui_utils.loader_utils`` show how to build a control module with its docks and toolbar. The app then
owns the control modules and must quit them in its ``quit_fun`` before calling ``super().quit_fun()``.

.. graphviz::
   :caption: App embedding control modules (not advised): who creates and owns what

   digraph embedding {
     node [shape=box, fontname="Helvetica", fontsize=10];
     app [label="MyApp(CustomApp)"]; viewer [label="DAQ_Viewer"]; move [label="DAQ_Move"];
     plugin [label="instrument plugins"];
     app -> viewer [label="creates and owns"]; app -> move [label="creates and owns"];
     viewer -> plugin [label="loads, in its own thread"]; move -> plugin [label="loads, in its own thread"];
     app -> H5Manager [label="owns"];
   }

Text version: the app creates and owns the control modules and its ``H5Manager``; each control module loads its
plugin in its own thread, as in the Dashboard.

.. _custom_app:

Custom App
==========

.. toctree::
   :maxdepth: 3
   :caption: Contents:

PyMoDAQ's set of modules is a very efficient way to build a completely custom application (related to data acquisition
or actuators displacement) without having to do it from scratch. :numref:`custom_app_fig` is an example of such an
interface build using only PyMoDAQ's building blocks. The corresponding script template is within the example folder.

  .. _custom_app_fig:

.. figure:: /image/custom_app.PNG
   :alt: dashboard

   A custom application build using PyMoDAQ's modules.

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
* An *application* is a program that you start yourself, independent of the Dashboard.

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
   * - A dedicated application with its own instruments, without Dashboard
     - ``CustomApp``
     - control modules you create yourself
     - your script

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
     apps -> cm [label="may create", style=dashed];
     cm -> plugins [label="load"]; plugins -> hw [label="drive"];
   }

Text version of the diagram:

* ``CustomApp`` (in ``pymodaq_gui``) is extended by ``DashBoard``, by ``CustomExt`` and by your standalone applications.
* ``CustomExt`` (in ``pymodaq``) is extended by every Dashboard extension, those shipped with PyMoDAQ as well as those
  in plugin packages.
* The ``DashBoard`` creates the control modules and loads the extensions declared as entry points.
* An extension uses the control modules of the Dashboard through its ``ModulesManager``; it does not create them.
* A standalone application may create its own control modules.
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
     ParameterManager [label="ParameterManager\n(pymodaq_gui.managers)\nparams, settings, settings_tree,\nvalue_changed, child_added, param_deleted"];
     CustomApp [label="CustomApp\n(pymodaq_gui.utils)\ndockarea, mainwindow, docks, menubar,\nstatusbar, thread_manager, h5_manager,\nsetup_ui, quit_fun"];
     CustomExt [label="CustomExt\n(pymodaq.utils.custom_ext)\ndashboard, modules_manager,\nexperiment_manager, state_manager,\ncreate_dashboard_toolbar, show_dashboard"];
     CustomApp -> QObject; CustomApp -> ActionManager; CustomApp -> ParameterManager;
     CustomExt -> CustomApp;
   }

Text version of the diagram:

* ``CustomApp(QObject, ActionManager, ParameterManager)`` lives in ``pymodaq_gui.utils.custom_app``.
* ``ActionManager`` brings the actions, and their placement in the toolbars and menus: ``add_action``, ``add_menu``,
  ``add_toolbar``, ``connect_action``, ``set_action_enabled``, ``set_action_checked``.
* ``ParameterManager`` brings the settings tree: the class attribute ``params``, the ``settings`` Parameter, the
  ``settings_tree`` widget and the callbacks ``value_changed``, ``child_added`` and ``param_deleted``.
* ``CustomApp`` itself brings the dock area (``dockarea``, ``docks``), the optional ``mainwindow``, the menu and
  status bars, the ``h5_manager`` and the ``thread_manager``, and the ``setup_ui`` sequence.
* ``CustomExt(CustomApp)`` lives in ``pymodaq.utils.custom_ext``. It takes the ``dashboard`` as second argument,
  creates a ``ModulesManager`` from the Dashboard's detectors and actuators (``modules_manager``), exposes the
  ``experiment_manager`` and ``state_manager`` of the Dashboard, and provides ``create_dashboard_toolbar`` and
  ``show_dashboard``.

The ``parent`` given to the constructor can be a ``DockArea``, a ``QMainWindow`` or a ``QWidget``: this decides
whether ``dockarea`` and ``mainwindow`` are created by the app or reused from the parent.

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
     - ``value_changed``, ``child_added``, ``param_deleted``
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

The three patterns
------------------

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

App embedding control modules directly
++++++++++++++++++++++++++++++++++++++

An app can create its own ``DAQ_Move`` and ``DAQ_Viewer`` objects without any Dashboard, deriving from
``CustomApp`` (``dashboard`` is not needed). ``create_load_daq_move`` and ``create_load_daq_viewer`` in
``pymodaq.utils.gui_utils.loader_utils`` show how to build a control module with its docks and toolbar.

.. graphviz::
   :caption: App embedding control modules: who creates and owns what

   digraph embedding {
     node [shape=box, fontname="Helvetica", fontsize=10];
     app [label="MyApp(CustomApp)"]; viewer [label="DAQ_Viewer"]; move [label="DAQ_Move"];
     plugin [label="instrument plugins"];
     app -> viewer [label="creates and owns"]; app -> move [label="creates and owns"];
     viewer -> plugin [label="loads, in its own thread"]; move -> plugin [label="loads, in its own thread"];
     app -> H5Manager [label="owns"];
   }

Text version: the app creates the control modules with the docks it provides, owns them, and must quit them in its
``quit_fun`` (``quit_fun`` of the control modules) before calling ``super().quit_fun()``. Each control module loads its
plugin in its own thread, as in the Dashboard. Without a Dashboard there is no ``ModulesManager`` unless you create
one yourself.


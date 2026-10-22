.. _extension_workflow:

How a Dashboard extension works
===============================

This page follows an extension from the moment it is started to the moment it quits, with the objects involved. It is
what the core extensions (:ref:`DAQ_Scan_module`, DAQ_Logger, PID, data mixer, sequencer, ramping...) do, and an
extension of a plugin package works exactly the same way, the only differences being the ``EXTENSION_NAME`` and
``CLASS_NAME`` that make it discoverable (see :ref:`extension_discovery`). Read :ref:`custom_app` first for the base
classes, ``CustomApp`` and ``CustomExt``.

Each diagram is followed by its text version.

.. _extension_startup:

Starting an extension
---------------------

There are two ways to start the same extension class:

* from the Dashboard: the user picks it in the *Extensions* menu, the Dashboard builds the extension window and the
  extension object;
* on its own, with the ``main()`` function of the extension module: it builds a Dashboard (hidden) and does the
  same thing.

.. graphviz::
   :caption: Startup of an extension with its ``main()`` function

   digraph startup {
     rankdir=TB; node [shape=box, fontname="Helvetica", fontsize=10];
     a [label="mkQApp('My Extension')\nthe Qt application"];
     b [label="load_dashboard_with_arguments(\nshow_dashboard=False, load_extension=False)\nreads -x EXPERIMENT and -s STATE, builds the Dashboard\nand applies the experiment if one is given"];
     c [label="win.mainwindow.setVisible(False)\nthe Dashboard stays hidden"];
     d [label="create_extension(dashboard, MyExtension, show_extension=True)\nbuilds the window and the DockArea,\nthen MyExtension(dockarea, dashboard)"];
     e [label="the extension window is shown"];
     f [label="sys.exit(app.exec())\nthe Qt event loop"];
     a -> b -> c -> d -> e -> f;
   }

Text version:

#. ``mkQApp`` creates the Qt application.
#. ``load_dashboard_with_arguments(show_dashboard=False, load_extension=False)`` reads the command line (``-x`` the
   experiment to load, ``-s`` the state to apply), builds the Dashboard, and applies the experiment if given.
#. The Dashboard window is hidden: the user works in the extension window and can show the Dashboard from the Dashboard
   toolbar of the extension (see :ref:`customext_experiment_state`).
#. ``create_extension(dashboard, MyExtension, show_extension=True)`` creates the window and its ``DockArea``, instantiates
   ``MyExtension(dockarea, dashboard)``, adds the toolbars of the extension to the window and shows it. It already shows
   the window: do not call ``show()`` again.
#. ``app.exec()`` runs the Qt event loop; the program ends when the window is closed.

The ``main()`` function of an extension module is therefore always the same:

.. code-block:: python

    def main():
        import sys
        from pymodaq_gui.qt_utils import mkQApp
        from pymodaq.dashboard import load_dashboard_with_arguments
        from pymodaq.utils.gui_utils.loader_utils import create_extension

        app = mkQApp('My Extension')
        win, dashboard, _ = load_dashboard_with_arguments(show_dashboard=False, load_extension=False)
        win.mainwindow.setVisible(False)
        win_ext, ext = create_extension(dashboard, MyExtension, show_extension=True)
        sys.exit(app.exec())

    if __name__ == '__main__':
        main()

When started from the Dashboard instead, ``DashBoard.load_extension`` calls the same ``create_extension``, keeps the
extension in ``dashboard.extensions``, checks the *Show Dashboard* action of its toolbar and connects the
``status_signal`` of the extension to the status display of the Dashboard.

.. _extension_run_lifecycle:

Life of the extension object
----------------------------

.. graphviz::
   :caption: Life of a CustomExt object

   digraph lifecycle {
     rankdir=LR; node [shape=box, fontname="Helvetica", fontsize=10];
     init [label="__init__\nsuper().__init__(parent, dashboard)\nthen self.setup_ui()"];
     ui [label="setup_ui\nsetup_docks_and_widgets\nsetup_menus_and_toolbars\nsetup_actions\nconnect_things\ndo_things_after_ui_setup"];
     exp [label="do_things_after_experiment_set\nat start if an experiment is applied,\nthen at each new experiment"];
     run [label="running\nvalue_changed (settings tree)\nactions, signals of the modules,\nworkers", shape=ellipse];
     quit [label="quit_fun -> _quit_fun()\nreturn True to accept"];
     init -> ui -> exp -> run; run -> exp [label="new experiment applied", style=dashed]; run -> quit;
   }

Text version:

#. ``__init__`` calls the base ``__init__`` with ``(parent, dashboard)``, which creates the settings tree, the
   ``H5Manager``, the ``WorkerThreadManager`` and the ``ModulesManager`` of the extension, then calls ``self.setup_ui()``.
#. ``setup_ui`` builds the user interface by calling the methods listed in the table of :ref:`custom_app_lifecycle`.
#. ``do_things_after_experiment_set`` is called once at the end of ``CustomExt.__init__`` if an experiment is already
   applied, and each time the user applies another experiment. This is where the extension adapts to the instruments
   that are available (see :ref:`customext_experiment_state`).
#. While running, the extension reacts to the user (``value_changed`` of the settings tree, actions) and to the signals of
   the control modules. Long work (a scan, a sequence, a ramp) is done by an ``ExtensionWorker`` (see
   :ref:`custom_app_threads`).
#. When the window is closed, the Dashboard or the window calls ``quit_fun``, which calls your ``_quit_fun``. Return
   ``False`` (after telling the user) while the extension is running to refuse to quit, and ``True`` otherwise: the base
   implementation returns ``None``, which prevents the extension from closing. The base ``quit_fun`` then exits the worker
   threads, closes the window and shows the Dashboard again.
   The extension is registered in the Dashboard's ``ExtensionManager`` when ``create_extension`` builds it (whether it comes
   from the Dashboard, ``dashboard -e`` or a script) and removed from it when it has quit, so closing the Dashboard
   calls ``quit_fun(external_call=True)`` on every extension left. If the ``extension_close_all`` option of the
   ``[extensions]`` section of the configuration is true (see :ref:`extensions_closing`), ``quit_fun`` of an extension
   asks the Dashboard to quit instead, which quits all the extensions: the ``external_call`` argument prevents them from
   calling the Dashboard back.

.. _extension_threads:

What runs where
---------------

All the code of an extension (the methods above, the slots connected to actions and to the signals of the control
modules) runs in the GUI thread. The hardware is never reached directly: the extension talks to the control modules
(``DAQ_Move`` and ``DAQ_Viewer``) found in ``self.modules_manager``, which run the instrument plugins in their own
threads, and reacts to their signals (data grabbed, move done...). Never poll or sleep in the GUI thread. Work that is
long but is not instrument access, such as saving, is done in a worker thread (``ExtensionWorker`` and ``SaverWorker``,
see :ref:`custom_app_threads`).

.. graphviz::
   :caption: Threads of an extension

   digraph extthreads {
     rankdir=LR; node [shape=box, fontname="Helvetica", fontsize=10];
     subgraph cluster_gui { label="GUI thread"; style=dashed;
       ext [label="MyExtension"]; mm [label="modules_manager"]; cm [label="DAQ_Move / DAQ_Viewer\n(control modules)"]; }
     subgraph cluster_hw { label="One thread per instrument"; style=dashed; pl [label="instrument plugins"]; }
     subgraph cluster_w { label="Worker threads"; style=dashed; sv [label="SaverWorker"]; }
     ext -> mm [label="uses"]; mm -> cm [label="references"];
     cm -> pl [label="commands (signals)"]; pl -> cm [label="data, positions (signals)"];
     cm -> ext [label="grab_done_signal,\nmove_done_signal... (signals)"];
     ext -> sv [label="data_to_save_signal"];
   }

Text version: the extension, the ``ModulesManager`` and the control modules live in the GUI thread. Each control module
exchanges commands and data with its instrument plugin, which runs in its own thread, only through signals. The
extension connects to the signals of the control modules (``grab_done_signal`` of a detector, ``move_done_signal`` of an
actuator) to get the results, and sends the data to save to a ``SaverWorker`` thread with ``data_to_save_signal``.

.. _extension_discovery:

How an extension is found
-------------------------

.. graphviz::
   :caption: Discovery of the extensions

   digraph discovery {
     rankdir=LR; node [shape=box, fontname="Helvetica", fontsize=10];
     ep [label="pyproject.toml\n[project.entry-points.'pymodaq.extensions']"];
     pkg [label="package\npymodaq_plugins_xxxx"];
     mod [label="extensions/my_ext.py\nEXTENSION_NAME, CLASS_NAME,\nclass MyExtension(CustomExt)"];
     get [label="get_extensions()\nExtensionEnum"];
     menu [label="Dashboard\nExtensions menu"];
     ep -> pkg [label="names the package"]; pkg -> mod [label="every module of\nthe extensions folder"];
     mod -> get [label="module with EXTENSION_NAME"]; get -> menu [label="one action per extension"];
   }

Text version:

#. The ``pyproject.toml`` of the plugin package declares the entry point group ``pymodaq.extensions`` (created by the
   ``extensions = true`` feature flag, see :ref:`extension_plugins`).
#. ``pymodaq.extensions.utils.get_extensions`` imports each package declared in this group and every module of its
   ``extensions`` folder. A module that has an ``EXTENSION_NAME`` attribute defines an extension: ``CLASS_NAME`` is the name
   of the class (deriving from ``CustomExt``) found in the module.
#. The extensions found, those of PyMoDAQ included, are listed in the ``ExtensionEnum``; the Dashboard adds one
   action per extension in its *Extensions* menu (enabled once an experiment is applied), which calls
   ``DashBoard.load_extension``.
#. A module that cannot be imported is skipped with a warning in the log (check it if your extension is missing).

``EXTENSION_NAME`` is the label displayed in the menu and ``CLASS_NAME`` the name of the class. With these two attributes
and an entry point, nothing else is needed for the Dashboard to offer the extension.

.. _extension_example:

A complete small example
------------------------

The package `pymodaq_plugins_mockexamples <https://github.com/PyMoDAQ/pymodaq_plugins_mockexamples>`__ contains the
smallest useful extension, *Move and Grab* (``extensions/move_and_grab.py``, about 130 lines), to start from. With the mock
instruments of PyMoDAQ it shows, in order:

* the module variables ``EXTENSION_NAME`` and ``CLASS_NAME``, and the ``main()`` function of this page;
* the lifecycle methods of :ref:`custom_app_lifecycle`, and the Dashboard toolbar of :ref:`customext_experiment_state`;
* ``do_things_after_experiment_set`` refreshing the lists of actuators and detectors;
* the instruments used through ``self.modules_manager`` (``move_actuators_with_callback``, ``grab_data_with_callback`` and
  ``forget_callback``): the next step is done in a callback when the control module signals the end of the previous
  one, never by waiting in the GUI thread;
* a position with units (``DataActuator``), data as ``DataToExport``, shown in a ``ViewerDispatcher`` and saved with
  ``DataToExportSaver`` in the file of the ``H5Manager``;
* a clean shutdown: a timeout handler so that the extension is never stuck busy, and ``_quit_fun`` refusing to quit
  while a move or a grab is going on.

Its tests (``tests/test_move_and_grab.py``) show how to test an extension against a Dashboard holding mock instruments.

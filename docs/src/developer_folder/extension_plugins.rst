.. _extension_plugins:

Extension Plugins
=================

.. toctree::
   :maxdepth: 3
   :caption: Contents:

PyMoDAQ's plugins allows to add functionnalities to PyMoDAQ from external packages. You should be well aware of the
instrument type plugins and somehow of the PID models plugins. Here we are highlighting how to built dashboard
extensions such as the :ref:`DAQ_Scan_module`.

For your package to be considered as a PyMoDAQ's dashboard extension, you should make sure of a few things:

* The entrypoint in the *pyproject.toml* file should be correctly configured, see :numref:`extension_entrypoint_fig`
* The presence of an *extensions* module at the root of the package
* each module within the *extensions* module will define an extension. It should contains three attributes:

  * EXTENSION_NAME: a string used to display the extension name in the dashboard extension menu
  * CLASS_NAME: a string giving the name of the extension class
  * a class deriving from the ``CustomApp`` base class (see :ref:`custom_app`)

The *pymodaq_plugins_template* contains already all this, so make sure to start from there when you wish to build an
extension.

  .. _extension_entrypoint_fig:

.. figure:: /image/extensions/entrypoint.png
   :alt: dashboard

   The correct configuration of your package.

The class itself defining the extension derives from the ``CustomApp`` base class. As such, it's ``__init__`` method
takes two attributes, a ``DockArea`` instance and a ``DashBoard`` instance (the one from which the extension will be
loaded and that contains all the actuators/detectors needed for your extension). The ``DashBoard`` will smoothly
initialize your class when launching it from the menu. Below you'll find a sample of an extension module with an
extension class called ``MyExtension`` (from the *pymodaq_plugins_template* package)


.. code-block::

    EXTENSION_NAME = 'MY_EXTENSION_NAME'
    CLASS_NAME = 'MyExtension'

    class MyExtension(gutils.CustomApp):
        # list of dicts enabling the settings tree on the user interface
        params = [
            {'title': 'Main settings:', 'name': 'main_settings', 'type': 'group', 'children': [
                {'title': 'Save base path:', 'name': 'base_path', 'type': 'browsepath',
                 'value': config['data_saving']['h5file']['save_path']},
                {'title': 'File name:', 'name': 'target_filename', 'type': 'str', 'value': "", 'readonly': True},
                {'title': 'Date:', 'name': 'date', 'type': 'date', 'value': QtCore.QDate.currentDate()},
                {'title': 'Do something, such as showing data:', 'name': 'do_something', 'type': 'bool', 'value': False},
                {'title': 'Something done:', 'name': 'something_done', 'type': 'led', 'value': False, 'readonly': True},
                {'title': 'Infos:', 'name': 'info', 'type': 'text', 'value': ""},
                {'title': 'push:', 'name': 'push', 'type': 'bool_push', 'value': False}
            ]},
            {'title': 'Other settings:', 'name': 'other_settings', 'type': 'group', 'children': [
                {'title': 'List of stuffs:', 'name': 'list_stuff', 'type': 'list', 'value': 'first',
                 'limits': ['first', 'second', 'third'], 'tip': 'choose a stuff from the list'},
                {'title': 'List of integers:', 'name': 'list_int', 'type': 'list', 'value': 0,
                 'limits': [0, 256, 512], 'tip': 'choose a stuff from this int list'},
                {'title': 'one integer:', 'name': 'an_integer', 'type': 'int', 'value': 500, },
                {'title': 'one float:', 'name': 'a_float', 'type': 'float', 'value': 2.7, },
            ]},
        ]

        def __init__(self, dockarea, dashboard):
            super().__init__(dockarea, dashboard)
            self.setup_ui()

With such a file in the extensions folder, the dashboard will be able to see it and will list it into its available
extensions. Then you'll have to code the inners of your extension following the ``CustomApp`` class
(see :ref:`custom_app`). The big difference between extensions and Standalone apps resides in the fact that your
dashboard instance is available here, hence all the control modules it contains. You'll be able to use all their
functionalities only focusing on your extension layout!


Providing Caller Context to plugins
------------------------------------

If your extension drives detectors through its own acquisition loop (like :ref:`DAQ_Scan_module` does), plugins
may want to know, from within ``grab_data``, which file/node your extension is currently writing to - see
:ref:`caller_context` for why a plugin would need that. As the extension author, it is up to *you* to build and
pass that :class:`~pymodaq.utils.caller.CallerInfo` on every grab; nothing does it for you automatically.

If you inherit from ``CustomExt`` rather than the bare ``CustomApp`` (``DAQScan`` does, and it is the recommended
base for any extension that acquires data from several detectors, as covered above), a
:class:`~pymodaq.utils.managers.modules.modules_manager.ModulesManager` wired to the dashboard's selected detectors
and actuators is already available as ``self.modules_manager`` - you don't need to build it yourself.

1. **Define your own caller class**, if you need to carry extension-specific information (e.g. a step index) on
   top of the base ``h5_file_path``/``node_name``/``caller_name`` fields. A plain :class:`~pymodaq.utils.caller.CallerInfo`
   is enough if you have nothing to add. Follow the pattern used by ``DAQScanCaller``
   (``pymodaq.extensions.scan.daq_scan``):

   .. code-block:: python

       from dataclasses import dataclass
       from pymodaq.utils.caller import CallerInfo

       @dataclass
       class MyExtensionCaller(CallerInfo):
           caller_name: str = 'MyExtension'
           ind_step: int = 0  # whatever extra context your acquisition loop can provide

2. **Know your current save target.** Just like ``DAQScan`` does when it starts a run (see
   ``DAQScan.start_scan``), get the node you are about to write to from your own
   :class:`~pymodaq.utils.h5modules.module_saving.ScanSaver` (or another
   :class:`~pymodaq.utils.h5modules.module_saving.ModuleSaver` subclass fitting your case)/
   :class:`~pymodaq_gui.h5modules.saving.H5Saver` set up (see :ref:`module_savers` for the module saver objects
   PyMoDAQ's own extensions use), and keep the file path and node name around for the duration of the acquisition:

   .. code-block:: python

       scan_node = self.module_and_data_saver.get_set_node(new=True)
       self.current_node_name = scan_node.name.split('/')[-1]
       self.current_h5_file_path = str(self.h5saver.settings['current_h5_file'])

3. **Pass a fresh caller instance on every grab**, as the ``caller`` kwarg to
   :meth:`~pymodaq.utils.managers.modules.modules_manager.ModulesManager.grab_data`. It is forwarded, unchanged,
   to every selected detector for that call - so if two detectors need different callers you must grab them
   separately rather than in the same ``grab_data`` call:

   .. code-block:: python

       for ind_step in range(n_steps):
           ...
           caller = MyExtensionCaller(
               h5_file_path=self.current_h5_file_path,
               node_name=self.current_node_name,
               ind_step=ind_step,
           )
           self.modules_manager.grab_data(caller=caller)

   If you are not using ``ModulesManager`` and are driving a single ``DAQ_Viewer`` directly instead, pass ``caller``
   the same way through its public ``grab_data``/command API, e.g.
   ``detector.command_hardware.emit(ThreadCommand(ControlToHardwareViewer.SINGLE, dict(Naverage=1, caller=caller)))``.

A plugin can then tell your extension is driving the current grab (rather than seeing the generic fallback
described in :ref:`caller_context`) by checking ``caller.caller_type == 'MyExtensionCaller'``.
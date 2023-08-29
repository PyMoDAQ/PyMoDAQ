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

* The entrypoint in the setup file should be correctly configured, see :numref:`extension_entrypoint_fig`
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
takes two attributes, a ``DoackArea`` instance and a ``DashBoard`` instance (the one from which the extension will be
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

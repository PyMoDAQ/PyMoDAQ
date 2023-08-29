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

.. note::

  A generic base class `CustomApp` located in `pymodaq.utils.gui_utils` can be used to
  build very quickly standalone *Application* or *Dashboard* extensions. The *DAQ_Logger* extension
  has been built using it as well as some examples in the example folder.

Below you'll find the skeleton of a *CustomApp* subclassing the base class and methods you
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

        def setup_actions(self):
            '''
            subclass method from ActionManager
            '''
            logger.debug('setting actions')
            self.add_action('quit', 'Quit', 'close2', "Quit program", toolbar=self.toolbar)
            self.add_action('grab', 'Grab', 'camera', "Grab from camera", checkable=True, toolbar=self.toolbar)
            logger.debug('actions set')

        def setup_docks(self):
            '''
            subclass method from CustomApp
            '''
            logger.debug('setting docks')
            self.dock_settings = gutils.Dock('Settings', size=(350, 350))
            self.dockarea.addDock(self.dock_settings, 'left')
            self.dock_settings.addWidget(self.settings_tree, 10)
            logger.debug('docks are set')

        def connect_things(self):
            '''
            subclass method from CustomApp
            '''
            logger.debug('connecting things')
            self.actions['quit'].connect(self.quit_function)
            self.actions['grab'].connect(self.detector.grab)
            logger.debug('connecting done')

        def setup_menu(self):
            '''
            subclass method from CustomApp
            '''
            logger.debug('settings menu')
            file_menu = self.mainwindow.menuBar().addMenu('File')
            self.affect_to('quit', file_menu)
            file_menu.addSeparator()
             logger.debug('menu set')

        def value_changed(self, param):
            logger.debug(f'calling value_changed with param {param.name()}')
            if param.name() == 'do_something':
                if param.value():
                    self.settings.child('main_settings', 'something_done').setValue(True)
                else:
                    self.settings.child('main_settings', 'something_done').setValue(False)

            logger.debug(f'Value change applied')

    """
    All other methods required by your Application class
    """

In a few lines of codes, you'll get an application running. For the available *Parameter* available
for your `settings_tree`, see :ref:`Settings <parameter_tree>`.
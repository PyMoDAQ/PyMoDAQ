.. _managers:

Managers and Mixin Objects
==========================


Action Manager
++++++++++++++


Overview
--------

The Action Manager provides a convenient way to manage QActions and widgets in PyQt/PySide applications. It simplifies the creation, organization, and management of toolbar actions and menu items through a unified interface.

Key Features
~~~~~~~~~~~~

* Centralized action management through a dictionary-based system
* Easy creation of actions with icons, tooltips, and shortcuts
* Support for both actions and custom widgets in toolbars
* Built-in methods for controlling action visibility, enabled state, and checked state
* Multiple dispatch support for operating on single or multiple actions at once

Getting Started
---------------

Basic Usage
~~~~~~~~~~~

To use the ActionManager, create a class that inherits from it and implement the ``setup_actions`` method:

.. code-block:: python

    from pymodaq.utils.managers.action_manager import ActionManager
    from qtpy import QtWidgets
    
    class MyWidget(QtWidgets.QWidget, ActionManager):
        def __init__(self):
            QtWidgets.QWidget.__init__(self)
            ActionManager.__init__(self)
            
            # Create toolbar
            self.set_toolbar(QtWidgets.QToolBar())
            
            # Setup actions
            self.setup_actions()
        
        def setup_actions(self):
            """Define all actions here"""
            self.add_action('quit', 'Quit', 'close2', 
                          tip='Quit the application',
                          shortcut='Ctrl+Q')
            
            self.add_action('save', 'Save', 'SaveAs',
                          tip='Save current data',
                          checkable=False)
            
            self.add_action('grab', 'Grab', 'camera',
                          tip='Grab from camera',
                          checkable=True)

Creating Actions
~~~~~~~~~~~~~~~~

Actions can be created with various properties:

.. code-block:: python

    # Simple action with icon and tooltip
    self.add_action('open', 'Open File', 'Open', 
                   tip='Open a file')
    
    # Checkable action (toggle button)
    self.add_action('live_view', 'Live View', 'camera',
                   tip='Toggle live view',
                   checkable=True,
                   checked=False)
    
    # Action with keyboard shortcut
    self.add_action('save', 'Save', 'SaveAs',
                   tip='Save data',
                   shortcut='Ctrl+S')
    
    # Initially disabled action
    self.add_action('export', 'Export', 'export',
                   tip='Export data',
                   enabled=False)

Connecting Actions to Slots
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Connect actions to methods that will be called when triggered:

.. code-block:: python

    def setup_actions(self):
        self.add_action('quit', 'Quit', 'close2')
        self.add_action('save', 'Save', 'SaveAs')
        
        # Connect actions after creation
        self.connect_action('quit', self.on_quit)
        self.connect_action('save', self.on_save)
    
    def on_quit(self):
        """Called when quit action is triggered"""
        self.close()
    
    def on_save(self):
        """Called when save action is triggered"""
        # Save logic here
        print("Saving data...")

Adding Widgets to Toolbars
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beyond actions, you can add custom widgets to toolbars:

.. code-block:: python

    def setup_actions(self):
        # Add a spinbox
        self.add_widget('exposure_time', 'QSpinBox',
                       tip='Set exposure time (ms)',
                       signal_str='valueChanged',
                       slot=self.on_exposure_changed)
        
        # Add a combobox
        self.add_widget('mode_selector', 'QComboBox',
                       tip='Select acquisition mode')
        
        # Configure the combobox
        combo = self.get_action('mode_selector')
        combo.addItems(['Single', 'Continuous', 'Burst'])
    
    def on_exposure_changed(self, value):
        print(f"Exposure time changed to {value} ms")

Working with Icons
~~~~~~~~~~~~~~~~~~

The ActionManager supports multiple ways to specify icons:

.. code-block:: python

    # Built-in PyMoDAQ icon
    self.add_action('save', 'Save', 'SaveAs')
    
    # Custom icon from file path
    self.add_action('custom', 'Custom', '/path/to/icon.png')
    
    # QIcon instance
    from qtpy.QtGui import QIcon
    icon = QIcon('/path/to/icon.png')
    self.add_action('with_qicon', 'Action', icon)
    
    # Qt theme icon (Qt >= 6.7)
    self.add_action('theme_icon', 'Open', 'folder-open')

From PyMoDAQ 5.2, Material Icons from Google (https://fonts.google.com/icons) are available easily. You can browse
on the website for an icon and should add its name in the `pymodaq_gui/resources/icons.toml` file. Then, as a developer
(using the ./install_packages.py shortcut for installing) execute:
``python -m pymodaq_gui.resources.check_icons_dev``.

This will fetch and copy the full list of icons and add them as binary resource files. A specified icon name from this
list will then be used in priority. To display MaterialIcons already included in PyMoDAQ, run:

``python -m pymodaq_gui.examples.material_icon_ex``

Managing Action States
~~~~~~~~~~~~~~~~~~~~~~

Control action visibility, enabled state, and checked state:

.. code-block:: python

    # Single action
    self.set_action_visible('save', False)  # Hide action
    self.set_action_enabled('export', True)  # Enable action
    self.set_action_checked('live_view', True)  # Check action
    
    # Multiple actions at once
    self.set_action_visible(['save', 'export'], False)
    self.set_action_enabled(['open', 'save'], True)
    
    # Query action state
    if self.is_action_checked('live_view'):
        print("Live view is active")
    
    if self.is_action_enabled('save'):
        print("Save is enabled")

Complete Example
----------------

Here's a complete example showing a simple image viewer application:

.. code-block:: python

    from pymodaq.utils.managers.action_manager import ActionManager
    from qtpy import QtWidgets, QtCore
    
    class ImageViewer(QtWidgets.QMainWindow, ActionManager):
        def __init__(self):
            QtWidgets.QMainWindow.__init__(self)
            ActionManager.__init__(self)
            
            self.setWindowTitle("Image Viewer")
            
            # Setup UI
            self.setup_ui()
            self.setup_actions()
            self.connect_actions()
        
        def setup_ui(self):
            """Create the user interface"""
            # Central widget
            self.image_label = QtWidgets.QLabel()
            self.setCentralWidget(self.image_label)
            
            
            self.set_toolbar(QtWidgets.QToolBar())
            
            # Create menu
            menubar = self.menuBar()
            self.file_menu = menubar.addMenu('File')
            self.set_menu(self.file_menu)
        
        def setup_actions(self):
            """Define all actions"""
            self.add_action('open', 'Open', 'Open',
                          tip='Open image file',
                          shortcut='Ctrl+O')
            
            self.add_action('save', 'Save', 'SaveAs',
                          tip='Save current image',
                          shortcut='Ctrl+S',
                          enabled=False)
            
            self.add_action('zoom_in', 'Zoom In', 'zoom_in',
                          tip='Zoom in',
                          shortcut='+')
            
            self.add_action('zoom_out', 'Zoom Out', 'zoom_out',
                          tip='Zoom out',
                          shortcut='-')
            
            self.add_action('fit_window', 'Fit to Window', 'fit',
                          tip='Fit image to window',
                          checkable=True,
                          checked=True)
            
            self.toolbar.addSeparator()
            
            self.add_action('quit', 'Quit', 'close2',
                          tip='Quit application',
                          shortcut='Ctrl+Q')
        
        def connect_actions(self):
            """Connect actions to their slots"""
            self.connect_action('open', self.on_open)
            self.connect_action('save', self.on_save)
            self.connect_action('zoom_in', self.on_zoom_in)
            self.connect_action('zoom_out', self.on_zoom_out)
            self.connect_action('fit_window', self.on_fit_window)
            self.connect_action('quit', self.close)
        
        def on_open(self):
            """Open an image file"""
            filename, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open Image", "",
                "Images (*.png *.jpg *.bmp)")
            
            if filename:
                # Load and display image
                print(f"Opening {filename}")
                self.set_action_enabled('save', True)
        
        def on_save(self):
            """Save the current image"""
            print("Saving image...")
        
        def on_zoom_in(self):
            """Zoom in the image"""
            print("Zooming in...")
        
        def on_zoom_out(self):
            """Zoom out the image"""
            print("Zooming out...")
        
        def on_fit_window(self, checked):
            """Toggle fit to window mode"""
            if checked:
                print("Fit to window enabled")
            else:
                print("Fit to window disabled")
    
    
    if __name__ == '__main__':
        import sys
        app = QtWidgets.QApplication(sys.argv)
        viewer = ImageViewer()
        viewer.show()
        sys.exit(app.exec_())

Advanced Topics
---------------

Working with Custom Widgets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can add custom widget classes to your toolbar:

.. code-block:: python

    from qtpy import QtWidgets
    
    class CustomSlider(QtWidgets.QSlider):
        def __init__(self):
            super().__init__(QtCore.Qt.Horizontal)
            self.setRange(0, 100)
    
    # In setup_actions:
    self.add_widget('custom_slider', CustomSlider,
                   tip='Adjust value',
                   signal_str='valueChanged',
                   slot=self.on_slider_changed)

Dynamic Action Management
~~~~~~~~~~~~~~~~~~~~~~~~~

Actions can be managed dynamically at runtime:

.. code-block:: python

    def update_ui_state(self, has_data):
        """Update UI based on application state"""
        # Enable/disable groups of actions
        data_actions = ['save', 'export', 'analyze']
        self.set_action_enabled(data_actions, has_data)
        
        # Show/hide actions based on mode
        if self.advanced_mode:
            self.set_action_visible(['debug', 'settings'], True)
        else:
            self.set_action_visible(['debug', 'settings'], False)

Accessing Actions
~~~~~~~~~~~~~~~~~

Retrieve action objects when needed:

.. code-block:: python

    # Get single action
    save_action = self.get_action('save')
    save_action.setText('Save All')
    
    # Check if action exists
    if self.has_action('export'):
        print("Export action is available")
    
    # Get all action names
    print(self.actions_names)
    
    # Get all action objects
    all_actions = self.actions

Best Practices
--------------

1. **Organize actions logically**: Group related actions together in your ``setup_actions`` method
2. **Use meaningful short names**: Choose clear, descriptive short names for easy reference. Even better, is to list the action names within a StrEnum. This avoids mistakes when writing strings while giving access to automatic autocompletion when calling the action name (see extensions/optimizers_base/optimizer.py for an example).
3. **Provide tooltips**: Always add helpful tooltips to guide users
4. **Use keyboard shortcuts**: Add shortcuts for frequently used actions
5. **Manage state appropriately**: Keep enabled/disabled state in sync with application logic
6. **Separate concerns**: Keep action creation, connection, and business logic separate
7. **Use icons consistently**: Maintain a consistent icon style throughout your application

See Also
--------


* :ref:`Action Manager API <api-managers_action_manager>`
* Qt Documentation on QAction
* PyMoDAQ Icon Library


Parameter Manager
+++++++++++++++++


Overview
--------

The ``ParameterManager`` serves as a layer on top of the Parameter and ParameterTree helping classes to handle changes in the settings and providing a unique interface for all modules in PyMoDAQ dealing with Parameters.
The Parameter Manager is built on top of `pyqtgraph's Parameter system <https://pyqtgraph.readthedocs.io/en/latest/parametertree/index.html>`_, extending it with additional functionality for application settings management. It provides a complete UI widget that combines pyqtgraph's ParameterTree with a toolbar (inherited from the ``ActionManager``) for common operations like saving, loading, and searching. If you're not familiar with pyqtgraph Parameters, please first read the `pyqtgraph Parameter documentation <https://pyqtgraph.readthedocs.io/en/latest/parametertree/index.html>`_ to understand the underlying system.
To find an example of the different parameter types available in PyMoDAQ, look at the ``parameter_ex.py`` in the examples folder.



Key Additional Features
~~~~~~~~~~~~~~~~~~~~~~~

Beyond pyqtgraph's Parameter system, this module adds:

* **Integrated toolbar** with save, load, and update buttons
* **XML persistence** for saving/loading parameter trees
* **Search functionality** with real-time filtering and keyboard shortcuts (Ctrl+F, Esc)
* **Collapsible toolbar** to maximize screen space
* **Automatic callback routing** to simplified handler methods
* **Structure validation** when updating settings from files

Getting Started
---------------

Basic Usage
~~~~~~~~~~~

Create a subclass of ParameterManager and define your parameter structure using pyqtgraph's parameter dictionary format:

.. code-block:: python

    from pymodaq_gui.managers.parameter_manager import ParameterManager
    
    class MySettings(ParameterManager):
        settings_name = 'my_app_settings'
        params = [
            {'title': 'General:', 'name': 'general', 'type': 'group', 'children': [
                {'title': 'Name:', 'name': 'name', 'type': 'str', 'value': 'Default'},
                {'title': 'Value:', 'name': 'value', 'type': 'int', 'value': 42},
            ]},
        ]
    
    # Create instance
    settings = MySettings()
    
    # Get the widget to display in your UI
    widget = settings.settings_tree  # This is a QWidget with toolbar + tree

**Note:** The ``params`` list uses pyqtgraph's parameter dictionary format. See `pyqtgraph parameter types <https://pyqtgraph.readthedocs.io/en/latest/parametertree/parametertypes.html>`_ for all available parameter types and options.

Toolbar Actions
~~~~~~~~~~~~~~~

Control which toolbar actions are displayed:

.. code-block:: python

    # Include all actions (default)
    settings = MySettings(action_list=('search', 'save', 'update', 'load'))
    
    # Only save and load
    settings = MySettings(action_list=('save', 'load'))
    
    # No toolbar actions
    settings = MySettings(action_list=())

Available actions:

* ``'search'``: Search field with debounced input and keyboard shortcuts
* ``'save'``: Save current settings to XML file
* ``'update'``: Update settings from XML (validates structure matches)
* ``'load'``: Load settings from XML (replaces current structure)

Accessing Parameters
~~~~~~~~~~~~~~~~~~~~

Use pyqtgraph's standard Parameter methods to access and modify values:

.. code-block:: python

    # Access nested parameters using child()
    value = settings.settings.child('settings', 'value').value()
    value = manager.settings['settings', 'value']

    # Set value
    manager.settings.child('settings', 'timeout').setValue(2000)
    manager.settings['settings', 'timeout'] = 2000

    # Access parameter objects
    param = settings.settings.child('general', 'name')
    print(param.name())   # 'name'
    print(param.title())  # 'Name:'
    print(param.type())   # 'str'

For complete details on Parameter methods, see `pyqtgraph Parameter API <https://pyqtgraph.readthedocs.io/en/latest/parametertree/parameter.html>`_.

Novel Features
--------------

Simplified Change Callbacks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Parameter Manager simplifies pyqtgraph's change handling by routing different change types to dedicated methods:

.. code-block:: python

    class MySettings(ParameterManager):
        params = [
            {'title': 'Settings:', 'name': 'settings', 'type': 'group', 'children': [
                {'title': 'Mode:', 'name': 'mode', 'type': 'list',
                 'values': ['A', 'B'], 'value': 'A'},
                {'title': 'Value:', 'name': 'value', 'type': 'int', 'value': 10},
            ]},
        ]
        
        def value_changed(self, param):
            """Called when any parameter value changes"""
            if param.name() == 'mode':
                print(f"Mode changed to: {param.value()}")
        
        def child_added(self, param, data):
            """Called when a child parameter is added"""
            print(f"Child {data.name()} added to {param.name()}")
        
        def param_deleted(self, param):
            """Called when a parameter is removed"""
            print(f"Parameter {param.name()} was deleted")
        
        def options_changed(self, param, data):
            """Called when parameter options change (visible, enabled, etc.)"""
            if 'visible' in data:
                print(f"{param.name()} visibility changed to {data['visible']}")
        
        def limits_changed(self, param, data):
            """Called when parameter limits change"""
            min_val, max_val = data
            print(f"{param.name()} limits changed to [{min_val}, {max_val}]")

**Comparison to pyqtgraph:** Instead of handling all changes in a single ``sigTreeStateChanged`` handler, the Parameter Manager automatically routes changes to specific methods based on type.

XML Persistence
~~~~~~~~~~~~~~~

Built-in methods for saving and loading parameter trees to/from XML:

.. code-block:: python

    from pathlib import Path
    
    settings = MySettings()
    
    # Save settings
    settings.save_settings_slot(Path('my_settings.xml'))
    
    # Load settings (replaces tree structure)
    settings.load_settings_slot(Path('my_settings.xml'))
    
    # Update settings (requires matching structure)
    settings.update_settings_slot(Path('compatible_settings.xml'))

**Key difference between load and update:**

* ``load_settings_slot()``: Completely replaces the parameter tree with the loaded structure
* ``update_settings_slot()``: Only updates values; validates that the loaded tree has the same structure (parameter names and hierarchy) as the current tree

Search Functionality
~~~~~~~~~~~~~~~~~~~~

The search feature filters parameters in real-time:

.. code-block:: python

    # Enable search in toolbar
    settings = MySettings(action_list=('search', 'save', 'load'))
    
    # Keyboard shortcuts automatically available:
    # Ctrl+F: Activate search field
    # Esc: Clear search and collapse toolbar
    
    # Programmatic search
    settings.search_settings_slot('exposure')  # Shows only matching parameters

The search is implemented with:

* **Debounced input** (200ms delay) to avoid excessive filtering during typing
* **Case-insensitive matching** against parameter titles
* **Tree visibility management** using pyqtgraph's parameter options

The search is only active when the widget containing the line edit is expanded (i.e. after pressing Ctrl+F or pressing the push button).
Pressing again Ctrl + F / Esc / push button will collapse the widget and restore the tree. 
The search currently only acts on the setOpts at the parameter level and not on the tree itself. This aspect could be change in the future.

Creating Parameters from Different Sources
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The static ``create_parameter()`` method creates Parameter objects from various inputs:

.. code-block:: python

    from pymodaq_gui.managers.parameter_manager import ParameterManager
    from pathlib import Path
    
    # From dictionary list (standard pyqtgraph format)
    params_list = [
        {'title': 'Value:', 'name': 'val', 'type': 'int', 'value': 5}
    ]
    param = ParameterManager.create_parameter(params_list)
    
    # From XML file
    param = ParameterManager.create_parameter(Path('settings.xml'))
    
    # From existing Parameter (creates copy)
    existing_param = Parameter.create(name='test', type='group')
    param_copy = ParameterManager.create_parameter(existing_param)

This is useful when you need to create parameter objects outside of a ParameterManager instance.

Complete Examples
-----------------

Example 1: Camera Settings with Dynamic UI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from pymodaq_gui.managers.parameter_manager import ParameterManager
    from qtpy import QtWidgets
    import sys
    
    class CameraSettings(ParameterManager):
        settings_name = 'camera'
        params = [
            {'title': 'Acquisition:', 'name': 'acquisition', 'type': 'group', 'children': [
                {'title': 'Mode:', 'name': 'mode', 'type': 'list',
                 'values': ['Auto', 'Manual'], 'value': 'Auto'},
                {'title': 'Exposure (ms):', 'name': 'exposure', 'type': 'int',
                 'value': 100, 'min': 1, 'max': 10000, 'readonly': True},
                {'title': 'Gain:', 'name': 'gain', 'type': 'float',
                 'value': 1.0, 'min': 0.1, 'max': 10.0, 'readonly': True},
            ]},
        ]
        
        def value_changed(self, param):
            """Enable/disable manual controls based on mode"""
            if param.name() == 'mode':
                is_manual = param.value() == 'Manual'
                self.settings.child('acquisition', 'exposure').setOpts(readonly=not is_manual)
                self.settings.child('acquisition', 'gain').setOpts(readonly=not is_manual)
    
    
    if __name__ == '__main__':
        app = QtWidgets.QApplication(sys.argv)
        settings = CameraSettings()
        settings.settings_tree.show()
        sys.exit(app.exec_())

Example 2: Application with Persistent Settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from pymodaq_gui.managers.parameter_manager import ParameterManager
    from qtpy import QtWidgets
    from pathlib import Path
    import sys
    
    class AppSettings(ParameterManager):
        settings_name = 'myapp'
        params = [
            {'title': 'Preferences:', 'name': 'prefs', 'type': 'group', 'children': [
                {'title': 'Theme:', 'name': 'theme', 'type': 'list',
                 'values': ['Light', 'Dark'], 'value': 'Light'},
                {'title': 'Auto-save:', 'name': 'autosave', 'type': 'bool', 'value': True},
                {'title': 'Save Interval (min):', 'name': 'save_interval', 'type': 'int',
                 'value': 5, 'min': 1, 'max': 60},
            ]},
        ]
        
        def __init__(self):
            super().__init__(action_list=('search', 'save', 'load'))
            self.config_file = Path.home() / '.myapp' / 'config.xml'
            self.load_config()
        
        def load_config(self):
            """Load config on startup if it exists"""
            if self.config_file.exists():
                self.load_settings_slot(self.config_file)
        
        def save_config(self):
            """Save config"""
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            self.save_settings_slot(self.config_file)
        
        def value_changed(self, param):
            """Auto-save on any change"""
            if param.name() in ['theme', 'autosave', 'save_interval']:
                self.save_config()
    
    
    if __name__ == '__main__':
        app = QtWidgets.QApplication(sys.argv)
        
        window = QtWidgets.QMainWindow()
        settings = AppSettings()
        window.setCentralWidget(settings.settings_tree)
        window.setWindowTitle('App Settings')
        window.show()
        
        sys.exit(app.exec_())

Example 3: Using ParameterTreeWidget Standalone
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ParameterTreeWidget without subclassing ParameterManager:

.. code-block:: python

    from pymodaq_gui.managers.parameter_manager import ParameterTreeWidget
    from pymodaq_gui.parameter import Parameter
    from qtpy import QtWidgets
    
    app = QtWidgets.QApplication([])
    
    # Create widget with toolbar
    tree_widget = ParameterTreeWidget(action_list=('save', 'load', 'search'))
    
    # Create parameters using pyqtgraph
    params = [
        {'title': 'Settings:', 'name': 'settings', 'type': 'group', 'children': [
            {'title': 'Value:', 'name': 'value', 'type': 'int', 'value': 42},
        ]},
    ]
    root_param = Parameter.create(name='root', type='group', children=params)
    
    # Set parameters in tree
    tree_widget.tree.setParameters(root_param, showTop=False)
    
    # Show widget
    tree_widget.widget.show()
    app.exec_()

Best Practices
--------------

1. **Use pyqtgraph parameter types**: Leverage the full range of pyqtgraph's parameter types (int, float, str, bool, list, color, file, etc.)

2. **Structure validation**: Use ``update_settings_slot()`` instead of ``load_settings_slot()`` when loading user-provided settings files to ensure structure compatibility

3. **Efficient filtering**: The search feature uses ``treeChangeBlocker()`` for efficient batch updates when filtering large trees

4. **Keyboard shortcuts**: Enable the search action to provide users with Ctrl+F and Esc shortcuts for better UX

5. **Separate concerns**: Override only the callback methods you need (``value_changed``, ``child_added``, etc.)

6. **XML file management**: Store settings in a user config directory using ``pymodaq_utils.config.get_set_config_dir()``

Common Patterns
---------------

Conditional Visibility
~~~~~~~~~~~~~~~~~~~~~~

Show/hide parameters based on other parameter values:

.. code-block:: python

    def value_changed(self, param):
        if param.name() == 'enable_advanced':
            self.settings.child('advanced_group').setOpts(
                visible=param.value()
            )

Dynamic Parameter Creation
~~~~~~~~~~~~~~~~~~~~~~~~~~

Add/remove parameters dynamically:

.. code-block:: python

    def value_changed(self, param):
        if param.name() == 'num_channels':
            parent = self.settings.child('channels')
            # Remove existing children
            parent.clearChildren()
            # Add new children
            for i in range(param.value()):
                parent.addChild({
                    'title': f'Channel {i}:', 
                    'name': f'ch_{i}', 
                    'type': 'bool', 
                    'value': True
                })

Cascading Updates
~~~~~~~~~~~~~~~~~

Update related parameters when one changes:

.. code-block:: python

    def value_changed(self, param):
        if param.name() == 'sample_rate':
            max_freq = param.value() / 2  # Nyquist
            self.settings.child('filter', 'cutoff').setLimits((0, max_freq))

See Also
--------

* :ref:`Parameter Manager API <api-managers_parameter_manager>`
* `pyqtgraph Parameter documentation <https://pyqtgraph.readthedocs.io/en/latest/parametertree/index.html>`_
* `pyqtgraph ParameterTree documentation <https://pyqtgraph.readthedocs.io/en/latest/parametertree/parametertree.html>`_

.. _modules_manager:

Modules Manager
+++++++++++++++

``ModulesManager`` (``pymodaq.utils.managers.modules.modules_manager``) is how an extension reaches the actuators
(``DAQ_Move``) and detectors (``DAQ_Viewer``) of the Dashboard: it lists them, remembers which of them are *selected*,
moves the selected actuators, grabs the selected detectors, and tells you when they are done. An extension never creates
control modules (see :ref:`custom_app`), it uses them through its ``ModulesManager``.

.. contents::
   :local:
   :depth: 2

Where you get one
~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~

Everything below acts on the **selected** modules. Select by title::

    self.modules_manager.selected_detectors_name = ['Det1', 'Det3']
    self.modules_manager.selected_actuators_name = ['X_axis']

The selection can also be made by the user in ``settings_tree``. Two traps:

* A name that is not in the list of the manager is not an error: **the whole assignment is ignored** and the selection
  stays as it was (``['X', 'unknown']`` selects nothing new). Check ``selected_*_name`` if the names come from a
  settings file.
* The selection starts empty, and is emptied each time the lists are set (new experiment).

Signals
~~~~~~~

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
~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~

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
~~~~~~~~

A grab or a move that is not completed in time does not raise: the manager logs an error and emits
``timeout_signal`` with the titles of the modules it did not hear from. The duration is read from the configuration at
each call: ``[viewer] timeout`` for the detectors (in ms, 10000 by default) and ``[actuator] polling_timeout_s`` for the
actuators (in s, 20 by default). A blocking call returns at the timeout (with the data received so far); with a callback,
the callback is never called and the timeout only tells you. Connect ``timeout_signal`` to stop what you were doing and
call ``forget_callback``.

Probing
~~~~~~~

The two actions of ``settings_tree`` (*Probe detectors* and *Probe actuators*) are a quick check for the user. The first
snaps the selected detectors and lists the channels they send in the tree below (``get_probed_data_full_names(dim)``
returns their names, to offer them in a list); the second asks for target positions in a dialog, moves the selected
actuators and shows the positions reached. ``probe_detectors()`` and ``probe_actuators()`` can be called from code.
``get_det_data_list`` and ``test_move_actuators`` are the deprecated names of these methods.

Use cases
~~~~~~~~~

Each snippet is run by ``tests/utils/managers/modules_manager_use_cases_test.py`` on mock modules.

Move, then grab, without blocking the GUI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The optimizers (``optimizers_base/optimizer.py``, ``run_opti``), the PID (``pid/pid_controller.py``) and the Data Mixer
(``data_mixer/data_mixer.py``, ``snap``) use the blocking calls, each step needing the result of the previous one
(``grab_datas`` in the PID is the old name of ``grab_data``). They will be progressively moved to the ``*_with_callback``
sequences, which do not run a polling loop in the GUI thread: prefer those in new code.

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Put ``self.modules_manager.settings_tree`` in your UI to let the user select, as ``daq_logger`` does (``daq_scan`` puts
the parameters of the manager in its own trees), and
react to ``actuators_changed`` and ``detectors_changed`` (``daq_scan.py``: ``clear_plot_from``, ``update_actuators``).
Or select from your own settings with ``selected_*_name``, as the optimizers do from their model
(``optimizers_base/models.py``).

React to a new experiment
^^^^^^^^^^^^^^^^^^^^^^^^^

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
~~~~~

* Never create control modules in an extension, use the ones of ``self.modules_manager``.
* Select the modules before moving or grabbing; give one position per selected actuator, named like it.
* Connect before a blocking call and disconnect after it; call ``forget_callback`` for each ``*_with_callback`` call, in
  the callback and on a timeout.
* Handle ``timeout_signal``: a missing answer is reported by it only.
* Start again from an empty selection after a new experiment.
* Do not share a ``ModulesManager`` between extensions, unless it is on purpose the one of the Dashboard.

.. _roi_manager_dev:

ROI Manager
+++++++++++

``ROIManager`` (``pymodaq.utils.managers.roi_manager.roi_manager``) saves and restores the regions of interest (ROIs)
defined in the viewers of the Dashboard detectors. Users see it as described in :ref:`roi_manager`; this section is
for code that needs to use it.

* The Dashboard creates it: ``dashboard.roi_manager``. It is a ``ManagerBase`` (see the sections above) with
  ``entry_type = 'roi'``: an entry is a ``.rois`` file in the ``rois`` folder of the user configuration folder
  (``pymodaq.utils.config.get_set_roi_manager_path``). Do not confuse it with the ROI manager of a single viewer
  (``viewer.roi_manager``), which is where the ROIs actually live.
* Like the State manager it uses the ``ModulesManager`` of the Dashboard (``own_modules_manager = False``) and cannot
  execute an entry without a Dashboard (``can_execute_entry``).
* An entry holds the checked ROIs of the *ROIs* list: for each of them the parameter of the ROI in its viewer,
  with its path ``[detector title, viewer title, ROI name]``, serialized with the ``SerializableFactory``.
* When an experiment is set (``do_things_after_experiment_set``), the manager refreshes its list of viewers, creates
  an entry named after the experiment if there is none, and loads it. It executes it only if ``restore_rois`` is true
  in the ``[viewer]`` section of the preferences.
* Executing an entry clears the ROIs of each viewer it mentions and adds the saved ones; detectors that are no longer
  in the Dashboard are skipped with a warning.

From an extension or a script, use the usual ``ManagerBase`` methods on ``dashboard.roi_manager``:

.. code-block:: python

    roi_manager = dashboard.roi_manager
    roi_manager.update_viewer_list_from_dashboard()   # after adding or removing detectors
    roi_manager.update_roi_list()                      # list the ROIs of the selected viewers
    roi_manager.save_check(bypass_dialog=True)        # save the checked ROIs in the current entry, without asking
    roi_manager.execute_entry('my_experiment')         # re-create the ROIs of an entry in the viewers

Rules:

* The list of viewers is not updated by itself when you add detectors to a running Dashboard: refresh it before
  saving.
* ROIs are saved by viewer title, so renaming a detector or a viewer makes its saved ROIs unusable.


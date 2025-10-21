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

Modules Manager
+++++++++++++++


ROI Manager
+++++++++++




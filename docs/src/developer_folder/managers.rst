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
2. **Use meaningful short names**: Choose clear, descriptive short names for easy reference
3. **Provide tooltips**: Always add helpful tooltips to guide users
4. **Use keyboard shortcuts**: Add shortcuts for frequently used actions
5. **Manage state appropriately**: Keep enabled/disabled state in sync with application logic
6. **Separate concerns**: Keep action creation, connection, and business logic separate
7. **Use icons consistently**: Maintain a consistent icon style throughout your application

See Also
--------

.. * :doc:`action_manager_api` - Complete API reference
* Qt Documentation on QAction
* PyMoDAQ Icon Library

Modules Manager
+++++++++++++++


ROI Manager
+++++++++++




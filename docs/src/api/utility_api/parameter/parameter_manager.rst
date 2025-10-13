Parameter Manager
==================

Overview
--------

The ``ParameterManager`` inherits from the ActionManager.It provides a user interface for managing hierarchical parameter configurations with search, save/load capabilities, and a collapsible toolbar.

Quick Start
-----------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

    from pymodaq_gui.parameter.parameter_manager import ParameterManager
    from pymodaq_gui.parameter import Parameter
    
    # Define parameter structure
    params = [
        {
            'title': 'Settings',
            'name': 'settings',
            'type': 'group',
            'children': [
                {'title': 'Mode', 'name': 'mode', 'type': 'list',
                 'limits': ['Auto', 'Manual'], 'value': 'Auto'},
                {'title': 'Timeout', 'name': 'timeout', 
                 'type': 'int', 'value': 1000, 'suffix': 'ms'},
            ]
        },
    ]
    
    # Create manager
    manager = ParameterManager(
        settings_name='my_settings',
        action_list=('search', 'save', 'load')
    )
    
    # Initialize settings
    manager.settings = Parameter.create(
        name='my_settings',
        type='group',
        children=params,
        showTop=False
    )
    
    # Add to your UI
    layout.addWidget(manager.settings_tree)

Key Features
------------

Search
~~~~~~

**Keyboard Shortcuts:**

- ``Ctrl+F``: Open search and focus search field
- ``Esc``: Close search and clear filter

**Behavior:**

- Case-insensitive filtering
- Auto-expands parent groups containing matches
- Live filtering with debouncing

.. code-block:: python

    # Programmatic search
    manager.search_settings_slot("temperature")
    
    # Clear search
    manager.search_settings_slot("")

File Operations
~~~~~~~~~~~~~~~

Save Settings
"""""""""""""

.. code-block:: python

    # Interactive (opens file dialog)
    manager.save_settings_slot()
    
    # Programmatic
    from pathlib import Path
    manager.save_settings_slot(Path('config.xml'))

Load Settings
"""""""""""""

Replaces entire parameter tree:

.. code-block:: python

    manager.load_settings_slot()  # Interactive
    manager.load_settings_slot(Path('config.xml'))  # Programmatic

Update Settings
"""""""""""""""

Updates values only (structures must match):

.. code-block:: python

    manager.update_settings_slot()  # Interactive
    manager.update_settings_slot(Path('new_values.xml'))  # Programmatic

Responding to Changes
~~~~~~~~~~~~~~~~~~~~~

Override ``value_changed`` to respond to parameter updates:

.. code-block:: python

    class MyManager(ParameterManager):
        def value_changed(self, param):
            if param.name() == 'mode':
                if param.value() == 'Manual':
                    # Show manual controls
                    self.settings.child('manual_value').show()
                else:
                    self.settings.child('manual_value').hide()

Common Patterns
---------------

Conditional Visibility
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def value_changed(self, param):
        if param.name() == 'enable_advanced':
            advanced = self.settings.child('advanced_group')
            if param.value():
                advanced.show()
            else:
                advanced.hide()

Accessing Values
~~~~~~~~~~~~~~~~

.. code-block:: python

    # Get value
    mode = manager.settings.child('settings', 'mode').value()
    
    # Set value
    manager.settings.child('settings', 'timeout').setValue(2000)

Custom Action List
~~~~~~~~~~~~~~~~~~

Control which toolbar actions appear:

.. code-block:: python

    # Only search and save
    manager = ParameterManager(action_list=('search', 'save'))
    
    # Only file operations
    manager = ParameterManager(action_list=('save', 'update', 'load'))

API Reference
-------------

ParameterManager
~~~~~~~~~~~~~~~~

.. py:class:: ParameterManager(settings_name=None, action_list=('search', 'save', 'update', 'load'))

   :param settings_name: Name for root parameter
   :param action_list: Tuple of toolbar actions to enable

   **Main Properties:**
   
   - ``settings``: Root Parameter object
   - ``settings_tree``: QWidget containing tree and toolbar
   - ``tree``: Underlying ParameterTree widget

   **Main Methods:**
   
   - ``save_settings_slot(file_path=None)``: Save to XML
   - ``load_settings_slot(file_path=None)``: Load from XML (replaces tree)
   - ``update_settings_slot(file_path=None)``: Update from XML (preserves structure)
   - ``search_settings_slot(text="")``: Filter by search text

   **Override Methods:**
   
   - ``value_changed(param)``: Called when parameter value changes
   - ``child_added(param, data)``: Called when child added
   - ``param_deleted(param)``: Called when parameter deleted
   - ``options_changed(param, data)``: Called when options change
   - ``limits_changed(param, data)``: Called when limits change
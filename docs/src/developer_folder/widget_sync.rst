.. _widget_sync:

Widget Synchronization
======================

.. contents::
   :local:
   :depth: 2

Overview
--------

The ``widget_sync`` module provides a simple, powerful way to synchronize widget properties across multiple Qt widgets.
It's perfect for keeping toolbar buttons, menu items, and settings panels in sync without manual signal management.

**Key features:**

* Automatic bidirectional synchronization
* Multiple sync modes (bidirectional, to_sync, from_sync)
* Value transformations between widgets
* Automatic cleanup when widgets are deleted
* No memory leaks (uses weak references)
* Easy extension with custom factory methods

Basic Usage
-----------

Simple Synchronization
~~~~~~~~~~~~~~~~~~~~~

Keep multiple checkboxes in sync:

.. code-block:: python

    from pymodaq_gui.utils.widget_sync import WidgetSync

    # Create sync from first checkbox
    sync = WidgetSync.for_checkbox(toolbar_checkbox, initial=True)

    # Add more checkboxes - they stay in sync automatically
    sync.add(menu_checkbox)
    sync.add(settings_checkbox)

    # Change value programmatically - all update
    sync.value = False  # All three checkboxes uncheck

Different Widget Types
~~~~~~~~~~~~~~~~~~~~~

Sync different widget types representing the same value:

.. code-block:: python

    # Slider and spinbox for same value
    sync = WidgetSync.for_slider(slider, initial=50)
    # Use match='property' to allow different widget types with same property/signal
    sync.add(spinbox, match='property')  # Works because both use 'value'/'valueChanged'

    # Add read-only display
    sync.bind(
        progress_bar,
        setter=lambda v: progress_bar.setValue(v),
        mode=SyncMode.FROM_SYNC  # Read-only
    )

Factory Methods
---------------

Built-in Factories
~~~~~~~~~~~~~~~~~

Convenient factories for common widget types:

.. code-block:: python

    # Checkboxes
    sync = WidgetSync.for_checkbox(checkbox, initial=True)

    # SpinBoxes / DoubleSpinBoxes
    sync = WidgetSync.for_spinbox(spinbox, initial=50)

    # Sliders
    sync = WidgetSync.for_slider(slider, initial=75)

    # ComboBoxes
    sync = WidgetSync.for_combobox(combo, initial=0)  # By index
    sync = WidgetSync.for_combobox(combo, initial="Option A", use_text=True)  # By text

    # LineEdits
    sync = WidgetSync.for_lineedit(edit, initial="Hello")

Generic Factory
~~~~~~~~~~~~~~

For any Qt property:

.. code-block:: python

    sync = WidgetSync.for_property(
        widget,
        property_name='value',  # Qt property name
        signal_name='valueChanged',  # Change signal (optional, auto-detected)
        initial=50,
        data_type=int  # Optional: explicit type checking
    )

Adding Widgets: Type vs Property Matching
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When adding widgets with ``add()``, you can control the matching strategy:

.. code-block:: python

    # Type matching (default) - only same widget types
    sync = WidgetSync.for_slider(slider1)
    sync.add(slider2)  # OK - both QSlider
    # sync.add(spinbox)  # Would raise TypeError

    # Property matching - different widget types with compatible property/signal
    sync = WidgetSync.for_slider(slider1)
    sync.add(spinbox, match='property')  # OK - both use 'value'/'valueChanged'
    sync.add(dial, match='property')     # OK - also uses 'value'/'valueChanged'

**When to use:**

- ``match='type'`` (default): Safest, ensures identical widget behavior
- ``match='property'``: Flexible, allows mixing compatible widget types (e.g., QSlider + QSpinBox)

Data Type Safety
~~~~~~~~~~~~~~~~

WidgetSync supports explicit data type checking:

.. code-block:: python

    # Type inferred from initial value
    sync = WidgetSync(initial_value=True)  # data_type = bool
    sync = WidgetSync(initial_value=50)    # data_type = int

    # Explicit type checking
    sync = WidgetSync(initial_value=0, data_type=int)

    # Using factories with data_type
    sync = WidgetSync.for_property(
        widget, 'value', initial=50, data_type=int
    )

    # Type checking validates values and transforms
    sync.value = 100  # OK
    # sync.value = "text"  # Raises TypeError

Sync Modes
----------

Three synchronization modes:

.. code-block:: python

    from pymodaq_gui.utils.widget_sync import SyncMode

    # BIDIRECTIONAL (default): Widget ↔ Sync
    sync.add(widget, mode=SyncMode.BIDIRECTIONAL)

    # TO_SYNC: Widget → Sync only
    sync.add(widget, mode=SyncMode.TO_SYNC)

    # FROM_SYNC: Sync → Widget only (read-only display)
    sync.bind(label, setter=lambda v: label.setText(str(v)),
              mode=SyncMode.FROM_SYNC)

Value Transformations
---------------------

Transform values between widgets:

.. code-block:: python

    # Temperature: Celsius ↔ Fahrenheit
    celsius_sync = WidgetSync.for_spinbox(celsius_spin, initial=0)

    celsius_sync.add(
        fahrenheit_spin,
        to_sync_transform=lambda f: round((f - 32) * 5/9),  # F → C
        from_sync_transform=lambda c: round(c * 9/5 + 32)   # C → F
    )

    # Opposite/Inverted Checkboxes
    # Perfect for "Enable/Disable" vs "Lock/Unlock" scenarios
    enable_sync = WidgetSync.for_checkbox(enable_checkbox, initial=True)

    enable_sync.add(
        disable_checkbox,
        match='property',  # Both are checkboxes with 'checked' property
        to_sync_transform=lambda checked: not checked,  # Invert: checked → not checked
        from_sync_transform=lambda checked: not checked  # Invert: checked → not checked
    )
    # Now: enable_checkbox=True ↔ disable_checkbox=False

    # Boolean ↔ ComboBox index
    bool_sync = WidgetSync.for_checkbox(checkbox, initial=True)

    bool_sync.bind(
        combobox,
        signal=combobox.currentIndexChanged,
        getter=lambda: combobox.currentIndex(),
        setter=lambda i: combobox.setCurrentIndex(i),
        to_sync_transform=lambda i: i == 1,  # Index → Bool
        from_sync_transform=lambda b: 1 if b else 0  # Bool → Index
    )

Advanced Usage
--------------

Manual Connection
~~~~~~~~~~~~~~~~

For complete control:

.. code-block:: python

    sync = WidgetSync(initial_value=50)

    sync.bind(
        widget,
        signal=widget.valueChanged,
        getter=lambda: widget.value(),
        setter=lambda v: widget.setValue(v),
        mode=SyncMode.BIDIRECTIONAL
    )

Temporarily Disable Connections
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Temporarily pause syncing without disconnecting:

.. code-block:: python

    sync = WidgetSync.for_slider(slider1, initial=50)
    sync.add(slider2)
    sync.add(slider3)

    # Disable one slider temporarily
    sync.disable(slider2)
    slider1.setValue(75)  # slider2 doesn't update, slider3 does

    # Re-enable it
    sync.enable(slider2)
    slider2.setValue(60)  # Now it syncs again

    # Check if enabled
    if sync.is_enabled(slider2):
        print("Slider 2 is syncing")

**Use cases:**

* Temporarily pause sync during batch operations
* Conditional syncing based on application state
* Prevent feedback loops during complex updates
* Testing and debugging

**Key differences:**

* ``disable()`` - Temporarily stops syncing, connection remains
* ``unbind()`` - Removes connection entirely, needs reconnection

Conditional Widget Enable/Disable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable/disable widgets based on another widget's state:

.. code-block:: python

    # Create sync for master checkbox
    enable_sync = WidgetSync.for_checkbox(master_checkbox, initial=False)

    # Connect to enable/disable other widgets
    enable_sync.value_changed.connect(
        lambda enabled: advanced_spinbox.setEnabled(enabled)
    )
    enable_sync.value_changed.connect(
        lambda enabled: advanced_slider.setEnabled(enabled)
    )

Introspection
~~~~~~~~~~~~~

Check sync state:

.. code-block:: python

    # Get connected widgets
    widgets = sync.connected_widgets  # List of active widgets

    # Get connection count
    count = sync.connection_count  # Number of connections

    # Get current value
    value = sync.value

Connection Management
~~~~~~~~~~~~~~~~~~~~~

Cleanup is automatic via weak reference callbacks - when a widget is deleted,
its connection is automatically removed. Manual management is available when needed:

.. code-block:: python

    # Temporarily pause syncing (connection remains)
    sync.disable(widget)
    sync.enable(widget)  # Resume syncing

    # Check connection state
    is_syncing = sync.is_enabled(widget)

    # Permanently unbind widget
    sync.unbind(widget)
    # or
    sync.remove(widget)  # Alias for unbind

    # Unbind all (useful when deleting the sync itself)
    sync.unbind_all()

**When to use what:**

* ``disable()`` - Temporary pause, keeps connection setup, fast to re-enable
* ``unbind()`` - Permanent removal, requires full reconnection
* Automatic cleanup - Widget deletion triggers cleanup automatically


Dictionary Synchronization (DictSync)
--------------------------------------

When you need to synchronize multiple related properties or map widgets to different keys,
use dictionary-based synchronization.

When to Use DictSync vs ValueSync
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Use ValueSync (default) when:**

* Synchronizing a single value across multiple widgets
* All widgets represent the same logical property
* Example: Multiple checkboxes for the same "enabled" state

**Use DictSync when:**

* Synchronizing multiple related properties (e.g., RGB color components)
* Mapping different widgets to different dictionary keys
* Syncing multiple properties of a single widget
* Example: Color picker with separate R, G, B sliders

Creating DictSync
~~~~~~~~~~~~~~~~~

WidgetSync automatically detects when to use DictSync:

.. code-block:: python

    from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode

    # Auto-detects DictSync because initial_value is a dict
    color_sync = WidgetSync(initial_value={'r': 128, 'g': 64, 'b': 192})

    # Access/modify the dict value
    print(color_sync.value)  # {'r': 128, 'g': 64, 'b': 192}
    color_sync.value = {'r': 255, 'g': 0, 'b': 0}  # Red

DictSync Binding Methods
~~~~~~~~~~~~~~~~~~~~~~~~~

DictSync provides three binding methods:

1. **bind()** - For widgets that work with entire dict (JSON editors, displays)
2. **bind_properties()** - For multiple properties of ONE widget
3. **bind_dict()** - For DIFFERENT widgets mapped to dict keys

Method 1: bind() - Entire Dict
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For widgets that need the entire dictionary:

.. code-block:: python

    config_sync = WidgetSync(initial_value={'host': 'localhost', 'port': 8080})

    # Custom widget that displays JSON
    config_sync.bind(
        json_display,
        signal=json_display.contentChanged,
        getter=lambda: json_display.get_dict(),
        setter=lambda d: json_display.set_dict(d),
        mode=SyncMode.BIDIRECTIONAL
    )

    # Read-only display
    config_sync.bind(
        status_label,
        setter=lambda d: status_label.setText(f"Config: {d}"),
        mode=SyncMode.FROM_SYNC
    )

Method 2: bind_properties() - Multiple Properties of ONE Widget
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For synchronizing multiple properties of a single widget to dict keys:

.. code-block:: python

    # ComboBox with both items and selection
    combo_sync = WidgetSync(initial_value={
        'items': ["Red", "Green", "Blue"],
        'selection': "Red"
    })

    # Bind multiple properties of ONE combobox
    combo_sync.bind_properties(
        my_combobox,
        property_map={
            'items': {
                'signal': None,  # FROM_SYNC only
                'getter': lambda: [my_combobox.itemText(i)
                                   for i in range(my_combobox.count())],
                'setter': lambda items: (my_combobox.clear(),
                                        my_combobox.addItems(items)),
                'mode': SyncMode.FROM_SYNC
            },
            'selection': {
                'signal': my_combobox.currentTextChanged,
                'getter': lambda: my_combobox.currentText(),
                'setter': lambda text: my_combobox.setCurrentText(text),
                'mode': SyncMode.BIDIRECTIONAL
            }
        }
    )

    # Update items programmatically
    combo_sync.value = {
        'items': ["Apple", "Banana", "Orange"],
        'selection': "Apple"
    }

**Using Qt property names (auto-generation):**

.. code-block:: python

    # Shorter syntax using 'property' key
    widget_sync = WidgetSync(initial_value={'width': 100, 'height': 50})

    widget_sync.bind_properties(
        my_widget,
        property_map={
            'width': {'property': 'minimumWidth'},   # Auto-generates getter/setter
            'height': {'property': 'minimumHeight'}  # Signal auto-detected
        }
    )

Method 3: bind_dict() - DIFFERENT Widgets to Dict Keys
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For mapping different widgets to different dictionary keys:

.. code-block:: python

    # RGB color with separate sliders
    color_sync = WidgetSync(initial_value={'r': 128, 'g': 64, 'b': 192})

    # Each slider controls one color component
    color_sync.bind_dict(
        property_map={
            'r': {
                'widget': red_slider,
                'property': 'value'  # Auto-generates getter/setter/signal
            },
            'g': {
                'widget': green_slider,
                'property': 'value'
            },
            'b': {
                'widget': blue_slider,
                'property': 'value'
            }
        }
    )

    # Now changing any slider updates color_sync.value['r'/'g'/'b']
    # And changing color_sync.value updates all sliders

**Manual getter/setter (full control):**

.. code-block:: python

    position_sync = WidgetSync(initial_value={'x': 0, 'y': 0, 'z': 0})

    position_sync.bind_dict(
        property_map={
            'x': {
                'widget': x_spinbox,
                'signal': x_spinbox.valueChanged,
                'getter': lambda: x_spinbox.value(),
                'setter': lambda v: x_spinbox.setValue(v)
            },
            'y': {
                'widget': y_spinbox,
                'signal': y_spinbox.valueChanged,
                'getter': lambda: y_spinbox.value(),
                'setter': lambda v: y_spinbox.setValue(v)
            },
            'z': {
                'widget': z_spinbox,
                'signal': z_spinbox.valueChanged,
                'getter': lambda: z_spinbox.value(),
                'setter': lambda v: z_spinbox.setValue(v)
            }
        }
    )

Validation with DictSync
~~~~~~~~~~~~~~~~~~~~~~~~~

Add validators to ensure dict values stay within constraints:

.. code-block:: python

    def validate_rgb(color):
        """Clamp RGB values to 0-255"""
        return {
            'r': max(0, min(255, color.get('r', 0))),
            'g': max(0, min(255, color.get('g', 0))),
            'b': max(0, min(255, color.get('b', 0)))
        }

    color_sync = WidgetSync(
        initial_value={'r': 128, 'g': 64, 'b': 192},
        validator=validate_rgb
    )

    # Bind sliders
    color_sync.bind_dict(property_map={
        'r': {'widget': r_slider, 'property': 'value'},
        'g': {'widget': g_slider, 'property': 'value'},
        'b': {'widget': b_slider, 'property': 'value'}
    })

    # Values automatically clamped
    color_sync.value = {'r': 300, 'g': -50, 'b': 100}
    print(color_sync.value)  # {'r': 255, 'g': 0, 'b': 100}

Common DictSync Patterns
~~~~~~~~~~~~~~~~~~~~~~~~

**Pattern 1: ComboBox Items + Selection**

.. code-block:: python

    class DeviceSelector(QWidget):
        def __init__(self):
            super().__init__()
            self.combo = QComboBox()

            # Sync both items and current selection
            self.device_sync = WidgetSync(initial_value={
                'devices': ["Device A", "Device B"],
                'current': "Device A"
            })

            self.device_sync.bind_properties(
                self.combo,
                property_map={
                    'devices': {
                        'setter': lambda items: (self.combo.clear(),
                                                self.combo.addItems(items)),
                        'mode': SyncMode.FROM_SYNC
                    },
                    'current': {
                        'signal': self.combo.currentTextChanged,
                        'getter': lambda: self.combo.currentText(),
                        'setter': lambda t: self.combo.setCurrentText(t)
                    }
                }
            )

**Pattern 2: Multi-Widget Configuration**

.. code-block:: python

    class ServerConfig(QWidget):
        def __init__(self):
            super().__init__()
            self.host_edit = QLineEdit()
            self.port_spin = QSpinBox()
            self.ssl_check = QCheckBox()

            # All settings in one dict
            self.config_sync = WidgetSync(initial_value={
                'host': 'localhost',
                'port': 8080,
                'ssl': False
            })

            # Map each widget to a config key
            self.config_sync.bind_dict(property_map={
                'host': {'widget': self.host_edit, 'property': 'text'},
                'port': {'widget': self.port_spin, 'property': 'value'},
                'ssl': {'widget': self.ssl_check, 'property': 'checked'}
            })

            # Access full config
            config = self.config_sync.value
            # Save/load entire config at once
            self.config_sync.value = load_config_from_file()

**Pattern 3: Separate Syncs vs Single Dict**

Sometimes you need separate syncs for items and selection:

.. code-block:: python

    # Approach A: Separate syncs (items change independently of selection)
    self.items_sync = WidgetSync(initial_value=["A", "B", "C"])
    self.items_sync.bind(combo, setter=lambda items: combo.addItems(items),
                         mode=SyncMode.FROM_SYNC)

    self.selection_sync = WidgetSync.for_combobox(combo, initial="A")

    # Approach B: Single dict sync (items and selection always change together)
    self.combo_sync = WidgetSync(initial_value={'items': ["A", "B", "C"],
                                                  'current': "A"})
    self.combo_sync.bind_properties(combo, property_map={...})

**When to use which:**

* Separate syncs: Items can change without affecting selection
* Single dict: Atomic state updates (items + selection always consistent)


Extending Widget Sync
----------------------

You can extend the widget sync system to create custom synchronization tools.

Understanding the Architecture
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The widget sync system has three main classes:

1. **BaseWidgetSync** - Abstract base class with all connection management
2. **ValueSync** - Synchronizes single values (int, str, bool, etc.)
3. **DictSync** - Synchronizes dictionary values
4. **WidgetSync** - Smart factory that auto-selects ValueSync or DictSync

To create custom synchronization:

* Subclass ``BaseWidgetSync`` for completely custom sync types
* Extend ``WidgetSyncFactories`` for custom factory methods
* Use ``WidgetSync`` directly for most common scenarios

Creating a Custom Sync Class
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To create a custom sync class, subclass ``BaseWidgetSync`` and implement required methods:

.. code-block:: python

    from pymodaq_gui.utils.widget_sync import BaseWidgetSync, SyncMode
    from typing import Any

    class ListSync(BaseWidgetSync):
        """Synchronize list values with validation"""

        def __init__(self, initial_value=None, max_length=None):
            self._max_length = max_length
            self._value = initial_value or []
            self._previous_value = self._value.copy()
            self._data_type = list
            super().__init__(validator=self._validate_list)

        def _validate_list(self, value):
            """Ensure value is a list with max_length"""
            if not isinstance(value, list):
                raise TypeError(f"Expected list, got {type(value).__name__}")
            if self._max_length and len(value) > self._max_length:
                return value[:self._max_length]
            return value

        def set_value(self, new_value, emit=True):
            """Update the list value"""
            validated = self._validate_list(new_value)
            self._previous_value = self._value.copy()
            self._value = validated
            if emit:
                self.value_changed.emit(self._value)

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, new_value):
            self.set_value(new_value, emit=True)

        def _get_bind_property_key(self):
            """Return None for entire list binding"""
            return None

        def _get_bind_value(self):
            """Return full list for widget initialization"""
            return self._value

    # Usage
    list_sync = ListSync(initial_value=["A", "B", "C"], max_length=5)

    list_sync.bind(
        list_widget,
        signal=list_widget.itemChanged,
        getter=lambda: [list_widget.item(i).text()
                       for i in range(list_widget.count())],
        setter=lambda items: (list_widget.clear(),
                             list_widget.addItems(items))
    )

Required Methods
~~~~~~~~~~~~~~~~

When subclassing ``BaseWidgetSync``, you must implement:

1. **__init__()** - Initialize ``_value``, ``_previous_value``, ``_data_type``
2. **set_value(new_value, emit=True)** - Update value and emit signal
3. **value property** - Get/set the synchronized value
4. **_get_bind_property_key()** - Return property key for bind() callbacks
5. **_get_bind_value()** - Return value for widget initialization

Available Helper Methods
~~~~~~~~~~~~~~~~~~~~~~~~

``BaseWidgetSync`` provides many helper methods you can use:

**Connection Management:**

.. code-block:: python

    # Create callbacks for widget ↔ sync communication
    widget_to_sync_cb = self._create_widget_to_sync_callback(
        connection_key, widget_ref, getter, mode, to_sync_transform, property_key
    )
    sync_to_widget_cb = self._create_sync_to_widget_callback(
        connection_key, widget_ref, setter, mode, from_sync_transform, property_key
    )

    # Store connection info
    self._set_connection(widget_id, property_key, connection_info)

    # Retrieve connection
    connection = self._get_connection(widget_id, property_key)

    # Setup automatic cleanup when widget is destroyed
    self._setup_widget_destruction_callback(widget, connection_keys)

**Widget Control:**

.. code-block:: python

    # Temporarily disable/enable syncing
    self.disable(widget)
    self.enable(widget)
    is_syncing = self.is_enabled(widget)

    # Remove widget connection
    self.unbind(widget)
    self.unbind_all()

**Property Binding (for DictSync-like behavior):**

.. code-block:: python

    # Setup binding for a single property
    connection_info = self._setup_property_binding(
        widget, widget_ref, property_key, config
    )

Custom Factory Methods
~~~~~~~~~~~~~~~~~~~~~~

Extend ``WidgetSyncFactories`` to add custom factory methods:

.. code-block:: python

    from pymodaq_gui.utils.widget_sync import WidgetSyncFactories, WidgetSync

    class MyFactories(WidgetSyncFactories):
        """Custom factories for my application widgets"""

        @classmethod
        def for_color_picker(cls, widget, initial='#000000'):
            """Factory for custom color picker widget"""
            return cls.for_property(
                widget,
                property_name='color',
                signal_name='colorChanged',
                initial=initial,
                data_type=str
            )

        @classmethod
        def for_vector3d(cls, widget, initial=None):
            """Factory for 3D vector widget"""
            if initial is None:
                initial = {'x': 0.0, 'y': 0.0, 'z': 0.0}

            sync = WidgetSync(initial_value=initial)
            sync.bind_properties(
                widget,
                property_map={
                    'x': {'property': 'xValue'},
                    'y': {'property': 'yValue'},
                    'z': {'property': 'zValue'}
                }
            )
            return sync

    # Combine with WidgetSync
    class MyWidgetSync(WidgetSync, MyFactories):
        """Enhanced WidgetSync with custom factories"""
        pass

    # Usage
    sync = MyWidgetSync.for_color_picker(my_color_widget, initial='#FF0000')
    sync = MyWidgetSync.for_vector3d(my_vector_widget)

Real-World Example: Custom Range Sync
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class RangeSync(BaseWidgetSync):
        """Synchronize a range (min, max) across widgets"""

        def __init__(self, initial_min=0, initial_max=100):
            self._value = {'min': initial_min, 'max': initial_max}
            self._previous_value = self._value.copy()
            self._data_type = dict
            super().__init__(validator=self._validate_range)

        def _validate_range(self, value):
            """Ensure min <= max"""
            min_val = value.get('min', 0)
            max_val = value.get('max', 100)
            if min_val > max_val:
                min_val, max_val = max_val, min_val
            return {'min': min_val, 'max': max_val}

        def set_value(self, new_value, emit=True):
            validated = self._validate_range(new_value)
            self._previous_value = self._value.copy()
            self._value = validated
            if emit:
                self.value_changed.emit(self._value)

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, new_value):
            self.set_value(new_value, emit=True)

        def _get_bind_property_key(self):
            return None

        def _get_bind_value(self):
            return self._value

        def bind_range_widget(self, widget):
            """Convenience method for range widgets"""
            self.bind_dict(
                property_map={
                    'min': {
                        'widget': widget,
                        'signal': widget.lowerValueChanged,
                        'getter': lambda: widget.lowerValue(),
                        'setter': lambda v: widget.setLowerValue(v)
                    },
                    'max': {
                        'widget': widget,
                        'signal': widget.upperValueChanged,
                        'getter': lambda: widget.upperValue(),
                        'setter': lambda v: widget.setUpperValue(v)
                    }
                }
            )

    # Usage
    range_sync = RangeSync(initial_min=0, initial_max=100)
    range_sync.bind_range_widget(my_range_slider)

Common Patterns
---------------

Toolbar and Menu Sync
~~~~~~~~~~~~~~~~~~~~~

Keep toolbar and menu items synchronized:

.. code-block:: python

    class MyWindow(QMainWindow):
        def __init__(self):
            super().__init__()

            # Create toolbar and menu actions
            self.toolbar_auto = QCheckBox("Auto")
            self.menu_auto = QAction("Auto Mode", self)
            self.menu_auto.setCheckable(True)

            # Sync them
            self.auto_sync = WidgetSync.for_checkbox(self.toolbar_auto)

            # Bind menu action
            self.auto_sync.bind(
                self.menu_auto,
                signal=self.menu_auto.toggled,
                getter=lambda: self.menu_auto.isChecked(),
                setter=lambda v: self.menu_auto.setChecked(v)
            )


Multi-View Synchronization
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Keep multiple views of the same data synchronized:

.. code-block:: python

    # Main view slider
    main_sync = WidgetSync.for_slider(main_slider, initial=50)

    # Add compact view
    main_sync.add(compact_slider)

    # Add detailed view with transforms
    main_sync.bind(
        detailed_label,
        setter=lambda v: detailed_label.setText(
            f"Value: {v} ({v/100:.0%})"
        ),
        mode=SyncMode.FROM_SYNC
    )

Dynamic Widget Management
~~~~~~~~~~~~~~~~~~~~~~~~~

Manage widgets that are created and destroyed dynamically:

.. code-block:: python

    class DynamicPanel(QWidget):
        def __init__(self):
            super().__init__()
            self.sync = WidgetSync(initial_value=50)
            self.widgets = []

        def add_widget(self):
            """Add a new widget to the panel"""
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)

            # Bind to sync
            self.sync.bind(
                slider,
                signal=slider.valueChanged,
                getter=lambda: slider.value(),
                setter=lambda v: slider.setValue(v)
            )

            self.widgets.append(slider)
            self.layout().addWidget(slider)

        def remove_widget(self, slider):
            """Remove a widget from the panel"""
            self.sync.unbind(slider)
            self.widgets.remove(slider)
            slider.deleteLater()

        def pause_widget(self, slider):
            """Temporarily pause syncing for a widget"""
            self.sync.disable(slider)

        def resume_widget(self, slider):
            """Resume syncing for a widget"""
            self.sync.enable(slider)

        def get_connection_info(self):
            """Get info about active connections"""
            return {
                'count': self.sync.connection_count,
                'widgets': self.sync.connected_widgets
            }

API Reference
-------------

.. WidgetSync Class
.. ~~~~~~~~~~~~~~~~

.. .. autoclass:: pymodaq_gui.utils.widget_sync.WidgetSync
..    :members:
..    :undoc-members:

.. SyncMode Enum
.. ~~~~~~~~~~~~~

.. .. autoclass:: pymodaq_gui.utils.widget_sync.SyncMode
..    :members:

.. WidgetSyncFactories Mixin
.. ~~~~~~~~~~~~~~~~~~~~~~~~~~

.. .. autoclass:: pymodaq_gui.utils.widget_sync.WidgetSyncFactories
..    :members:
..    :undoc-members:

Examples
--------

See the complete example in:

.. code-block:: bash

    python -m pymodaq_gui.examples.widget_sync_example


Best Practices
--------------

DO:
~~~

* ✅ Use ``add()`` for widgets of the same type (default ``match='type'``)
* ✅ Use ``add(widget, match='property')`` for different types with compatible properties
* ✅ Use ``bind()`` for complete control over getter/setter/transforms
* ✅ Use ``SyncMode.FROM_SYNC`` for read-only displays
* ✅ Use factory methods for common widget types
* ✅ Use ``data_type`` parameter for explicit type checking
* ✅ Use ``disable()``/``enable()`` for temporary pauses
* ✅ Use ``unbind()`` for permanent removal
* ✅ Check ``connection_count`` and ``connected_widgets`` for debugging

DON'T:
~~~~~~

* ❌ Don't use ``add()`` without considering the ``match`` parameter
* ❌ Don't create circular sync chains (A→B→C→A)
* ❌ Don't disconnect/reconnect frequently (use ``disable()``/``enable()`` instead)
* ❌ Don't manually disconnect unless necessary (automatic cleanup works)
* ❌ Don't forget to handle value transformations when syncing different types
* ❌ Don't mix incompatible data types without proper transforms


See Also
--------

* :ref:`contributing` - Contributing guidelines
* :ref:`api` - Full API reference

Example Files
~~~~~~~~~~~~~

Run these examples to see widget synchronization in action:

.. code-block:: bash

    # Dict synchronization examples (bind_properties and bind_dict)
    python -m pymodaq_gui.examples.dict_sync_example

    # ComboBox synchronization (items + selection)
    python -m pymodaq_gui.examples.combobox_sync_example

    # Multi-property synchronization patterns
    python -m pymodaq_gui.examples.multi_property_sync_example

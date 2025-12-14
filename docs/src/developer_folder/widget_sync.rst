.. _widget_sync:

Widget Synchronization
======================

.. contents::
   :local:
   :depth: 2

Overview
--------

The ``widget_sync`` module provides a simple, powerful way to synchronize widget properties across multiple Qt widgets.
It eliminates the need for manual signal management, feedback loop prevention, and connection cleanup.

Why Use Widget Sync?
~~~~~~~~~~~~~~~~~~~~~

**The Problem:** Manual signal/slot management becomes complex quickly:

.. code-block:: python

    # Manual approach - repetitive and error-prone ❌
    def __init__(self):
        self.slider1.valueChanged.connect(self._on_slider1_changed)
        self.slider2.valueChanged.connect(self._on_slider2_changed)
        self.slider3.valueChanged.connect(self._on_slider3_changed)

    def _on_slider1_changed(self, value):
        # Block signals to prevent feedback loop
        self.slider2.blockSignals(True)
        self.slider3.blockSignals(True)
        self.slider2.setValue(value)
        self.slider3.setValue(value)
        self.slider2.blockSignals(False)
        self.slider3.blockSignals(False)

    # ... repeat for slider2 and slider3 ...

**The Solution:** Widget sync handles everything automatically:

.. code-block:: python

    # With widget_sync - simple and automatic ✅
    def __init__(self):
        self.sync = WidgetSync.for_slider(self.slider1, initial=50)
        self.sync.add(self.slider2)
        self.sync.add(self.slider3)
        # Done! All three stay in sync, no feedback loops, automatic cleanup

**Key features:**

* Automatic bidirectional synchronization
* Built-in feedback loop prevention
* Multiple sync modes (bidirectional, to_sync, from_sync)
* Value transformations between widgets
* Automatic cleanup when widgets are deleted
* No memory leaks (uses weak references)
* Easy extension with custom factory methods

Quick Start Guide
-----------------

Choose your approach based on what you're synchronizing:

**Single Value (Most Common)**

Use factory methods for common widget types:

.. code-block:: python

    from pymodaq_gui.utils.widget_sync import WidgetSync

    # Checkboxes
    sync = WidgetSync.for_checkbox(checkbox1, initial=True)
    sync.add(checkbox2)
    sync.add(checkbox3)

    # Sliders / SpinBoxes
    sync = WidgetSync.for_spinbox(spinbox1, initial=50)
    sync.add(spinbox2, match='property')  # Works with different compatible types

    # ComboBoxes
    sync = WidgetSync.for_combobox(combo1, initial=0)  # By index
    sync = WidgetSync.for_combobox(combo1, initial="Option A", use_text=True)  # By text

**Multiple Related Values (Dictionary)**

Use dict-based sync for related properties:

.. code-block:: python

    # RGB color with separate sliders
    color_sync = WidgetSync(initial_value={'r': 128, 'g': 64, 'b': 192})

    color_sync.bind_dict({
        'r': {'widget': red_slider, 'property': 'value'},
        'g': {'widget': green_slider, 'property': 'value'},
        'b': {'widget': blue_slider, 'property': 'value'}
    })

**Custom Widgets**

Use generic property binding:

.. code-block:: python

    # Any Qt property
    sync = WidgetSync.for_property(
        widget,
        property_name='myProperty',
        signal_name='myPropertyChanged',  # Optional, auto-detected
        initial=100
    )

Understanding WidgetSync Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The widget_sync system has three main classes:

* **WidgetSync** - Smart factory that auto-detects what you need (use this!)

  * Pass a single value → Uses ``ValueSync`` internally
  * Pass a dict → Uses ``DictSync`` internally
  * Includes all factory methods (``for_checkbox``, ``for_spinbox``, etc.)

* **ValueSync** - For single values (int, str, bool, float, custom objects)

  * Used automatically when you call ``WidgetSync(initial_value=42)``

* **DictSync** - For dictionary values with multiple keys

  * Used automatically when you call ``WidgetSync(initial_value={'a': 1})``

* **BaseWidgetSync** - Base class for advanced extensions (rarely needed)

**Most users only need WidgetSync** - it automatically chooses the right implementation.

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

.. tip::
   **Example:** :file:`examples/widget_sync/1_basic_sync_example.py` demonstrates:

   - Checkbox synchronization across multiple views (Tab 1)
   - Different widget types for the same value (Tab 2)
   - Value transforms for unit conversions and inverted checkboxes (Tabs 3 & 5)
   - Enable/disable patterns and many widget types (Tabs 4, 6, 7)

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

Understanding ``add()`` vs ``bind()``
--------------------------------------

**Important:** The ``add()`` method is only available for **single-value sync** (ValueSync), not for dictionary sync (DictSync).

Why the Difference?
~~~~~~~~~~~~~~~~~~~

**ValueSync** (single values):
  * All widgets represent the **same logical property** (e.g., a checkbox state)
  * Can auto-detect property/signal from first widget and reuse for others
  * ``add()`` provides convenience: "add another widget just like the first one"

**DictSync** (multiple properties):
  * Different dict keys map to **different properties or widgets**
  * Each binding needs explicit configuration (which key? which property?)
  * Must use ``bind()``, ``bind_properties()``, or ``bind_dict()``

Quick Reference
~~~~~~~~~~~~~~~

.. code-block:: python

    # ✅ ValueSync - add() works
    sync = WidgetSync.for_checkbox(checkbox1, initial=True)
    sync.add(checkbox2)  # Reuses 'checked' property from checkbox1
    sync.add(checkbox3)  # Works!

    # ✅ DictSync - must use bind_dict() or bind_properties()
    color_sync = WidgetSync(initial_value={'r': 128, 'g': 64, 'b': 192})
    # color_sync.add(red_slider)  # ❌ Won't work - no add() method!
    color_sync.bind_dict({  # ✅ Must specify which property goes to which key
        'r': {'widget': red_slider, 'property': 'value'},
        'g': {'widget': green_slider, 'property': 'value'}
    })

.. tip::
   **Rule of thumb:**

   * Single value → Use ``add()``
   * Dictionary → Use ``bind_dict()`` or ``bind_properties()``

Method Availability by Sync Type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Method
     - ValueSync (single value)
     - DictSync (dictionary)
   * - ``add()``
     - ✅ Available
     - ❌ Not available
   * - ``bind()``
     - ✅ Available
     - ✅ Available
   * - ``bind_properties()``
     - ❌ Not available
     - ✅ Available
   * - ``bind_dict()``
     - ❌ Not available
     - ✅ Available
   * - Factory methods
     - ✅ ``for_checkbox()``, etc.
     - ❌ (use ``WidgetSync(initial_value={...})``)

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

Initialization Control (init_from)
-----------------------------------

The ``init_from`` parameter controls what happens when you connect a widget.

Understanding init_from
~~~~~~~~~~~~~~~~~~~~~~~~

When you bind a widget to a sync, there are three possibilities for initial values:

.. code-block:: python

    sync = WidgetSync(initial_value=100)
    widget.setValue(50)  # Widget has different value

    # What should happen when we connect them?

**Three Options:**

1. **init_from='sync'** (default) - Widget gets sync's value
2. **init_from='widget'** - Sync gets widget's value (and propagates to other widgets)
3. **init_from=None** - No initialization, keep current values

Examples
~~~~~~~~

**Option 1: init_from='sync' (Default Behavior)**

.. code-block:: python

    sync = WidgetSync(initial_value=100)

    spinbox.setValue(50)  # Widget starts at 50

    # Default: widget immediately updates to sync's value
    sync.bind(
        spinbox,
        signal=spinbox.valueChanged,
        getter=spinbox.value,
        setter=spinbox.setValue,
        init_from='sync'  # Default, can be omitted
    )

    print(spinbox.value())  # 100 - widget updated to sync's value!

**Option 2: init_from='widget' (Sync Takes Widget's Value)**

.. code-block:: python

    sync = WidgetSync(initial_value=100)
    spinbox1.setValue(50)
    spinbox2.setValue(75)

    # Already connected
    sync.bind(spinbox1, ..., init_from='sync')
    print(spinbox1.value())  # 100

    # Connect spinbox2 with init_from='widget'
    sync.bind(spinbox2, ..., init_from='widget')

    # Sync AND spinbox1 update to spinbox2's value!
    print(sync.value)         # 75
    print(spinbox1.value())   # 75
    print(spinbox2.value())   # 75

**Option 3: init_from=None (No Initialization)**

.. code-block:: python

    sync = WidgetSync(initial_value=100)
    spinbox.setValue(50)

    # No initialization - values stay different
    sync.bind(spinbox, ..., init_from=None)

    print(sync.value)         # 100 - unchanged
    print(spinbox.value())    # 50  - unchanged

    # But future changes do sync!
    sync.value = 75
    print(spinbox.value())    # 75  - now they sync

When to Use Each Option
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - init_from
     - Use When
     - Example
   * - ``'sync'`` (default)
     - Sync holds the "source of truth"
     - Loading settings into UI widgets
   * - ``'widget'``
     - Widget holds current state you want to propagate
     - Connecting to an already-configured widget
   * - ``None``
     - Values are temporarily different but should sync going forward
     - Testing, debugging, or complex initialization

Requirements and Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**init_from='widget' Requirements:**

* Mode must have TO_SYNC capability (``TO_SYNC`` or ``BIDIRECTIONAL``)
* Must provide a ``getter`` to read widget's value
* Will raise ``ValueError`` if these requirements aren't met

**init_from='sync' Requirements:**

* Mode must have FROM_SYNC capability (``FROM_SYNC`` or ``BIDIRECTIONAL``)
* Must provide a ``setter`` to update widget
* With ``TO_SYNC`` mode, silently skips initialization (no setter available)

Per-Property init_from (DictSync)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For ``bind_dict()`` and ``bind_properties()``, you can override ``init_from`` per property:

.. code-block:: python

    # Global default: init_from='sync'
    sync = WidgetSync(initial_value={'host': 'localhost', 'port': 8080})

    sync.bind_dict(
        property_map={
            'host': {
                'widget': host_edit,
                'property': 'text',
                # Uses global default 'sync'
            },
            'port': {
                'widget': port_spin,
                'property': 'value',
                'init_from': 'widget'  # Override: use widget's current value
            }
        },
        init_from='sync'  # Global default
    )

    # Result: 'host' uses sync's value, 'port' uses widget's value

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
    # IMPORTANT: slider2 still has its old value (50)
    # enable() does NOT auto-update the widget

    slider1.setValue(60)  # Now slider2 updates to 60

    # Check if enabled
    if sync.is_enabled(slider2):
        print("Slider 2 is syncing")

**Use cases:**

* Temporarily pause sync during batch operations
* Conditional syncing based on application state
* Prevent feedback loops during complex updates
* Testing and debugging

**Key differences:**

* ``disable()`` - Temporarily stops syncing, connection remains, widget keeps old value
* ``unbind()`` - Removes connection entirely, needs reconnection
* ``enable()`` - Resumes syncing but widget keeps old value (no auto-update)
* ``bind()`` - Creates connection and immediately updates widget to current sync value

**Critical Behavior Note:**

When you re-bind a widget with ``bind()``, it **automatically updates** to the current sync value.
When you re-enable a widget with ``enable()``, it **keeps its old value** until the next sync event.

.. code-block:: python

    # Demonstrate the difference
    sync = WidgetSync.for_slider(master, initial=50)
    sync.add(slaveA)
    sync.add(slaveB)

    master.setValue(70)  # All at 70

    sync.disable(slaveA)  # Disable A
    sync.unbind(slaveB)   # Unbind B

    master.setValue(30)  # A and B don't update

    sync.enable(slaveA)  # A stays at 70 (no auto-update!)
    sync.bind(slaveB, ...)  # B jumps to 30 (auto-updates!)

    master.setValue(50)  # Now all three update to 50

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

.. important::
   **DictSync does NOT have an ``add()`` method.**

   You must use:

   * ``bind_dict()`` - For different widgets mapped to dict keys
   * ``bind_properties()`` - For multiple properties of ONE widget
   * ``bind()`` - For custom dict handling

   This is because each dict key needs explicit configuration - there's no "pattern" to auto-detect
   like with single-value sync.

.. tip::
   **Example:** :file:`examples/widget_sync/2_dict_sync_example.py` demonstrates:

   - ``bind_properties()``: Multiple properties of ONE widget (Tab 1 - ComboBox items + selection)
   - ``bind_dict()``: Different widgets to dict keys (Tab 2 - RGB color sliders)
   - Validators for dict values (Tab 3 - Clamping, auto-swapping min/max)
   - Custom dict widgets with ``bind()`` (Tab 4 - JSON editor)

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

DictSync provides four binding methods:

1. **bind()** - For widgets that work with entire dict (JSON editors, displays)
2. **bind_properties()** - For multiple properties of ONE widget (regular Qt widgets)
3. **bind_parameter()** - For pyqtgraph Parameters (avoids blockSignals issue)
4. **bind_dict()** - For DIFFERENT widgets mapped to dict keys

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

Binding Parameters with bind_parameter()
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``bind_parameter()`` method is specifically designed for binding pyqtgraph Parameters
to DictSync. Unlike ``bind_properties()``, it avoids the ``blockSignals()`` issue that
prevents parameter tree widgets from updating visually.

**When to Use Which Method:**

- Use ``bind_properties()`` for regular Qt widgets (QSpinBox, QComboBox, etc.)
- Use ``bind_parameter()`` for pyqtgraph Parameters

**Why bind_parameter() Exists:**

The ``blockSignals()`` mechanism used by ``bind_properties()`` prevents feedback loops,
but it also prevents parameter tree widgets from updating. Parameters manage their own
internal widgets, so we need callback disconnection instead of signal blocking.

Basic Parameter Binding
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from pymodaq_gui.parameter import Parameter, ParameterTree
    from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode

    # Create parameters
    params = [
        {'title': 'Threshold:', 'name': 'threshold', 'type': 'float',
         'value': 0.5, 'limits': (0.0, 1.0)},
        {'title': 'Buffer Size:', 'name': 'buffer_size', 'type': 'int',
         'value': 1024, 'limits': (128, 8192)},
    ]

    settings = Parameter.create(name='settings', type='group',
                               children=params)
    tree = ParameterTree()
    tree.setParameters(settings)

    # Create sync with toolbar widgets
    sync = WidgetSync(initial_value={
        'threshold': 0.5,
        'buffer_size': 1024
    })

    # Bind toolbar widgets (regular Qt widgets)
    sync.bind_properties(
        threshold_spinbox,
        property_map={'threshold': {'property': 'value'}}
    )

    sync.bind_properties(
        buffer_spinbox,
        property_map={'buffer_size': {'property': 'value'}}
    )

    # Bind parameters (use bind_parameter - NOT bind_properties!)
    sync.bind_parameter(
        settings.child('threshold'),
        property_map={
            'threshold': {
                'signal': settings.child('threshold').sigValueChanged,
                'getter': settings.child('threshold').value,
                'setter': settings.child('threshold').setValue,
            }
        }
    )

    sync.bind_parameter(
        settings.child('buffer_size'),
        property_map={
            'buffer_size': {
                'signal': settings.child('buffer_size').sigValueChanged,
                'getter': settings.child('buffer_size').value,
                'setter': settings.child('buffer_size').setValue,
            }
        }
    )

Now changing values in the toolbar spinboxes updates the parameter tree, and vice versa!

Shortcut Syntax for Simple Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For simple parameter value synchronization, use the shortcut syntax:

.. code-block:: python

    # Shortcut: Auto-generates sigValueChanged, value(), setValue()
    sync.bind_parameter(
        threshold_param,
        property_map={
            'threshold': {'param': threshold_param}
        }
    )

    # Equivalent to:
    sync.bind_parameter(
        threshold_param,
        property_map={
            'threshold': {
                'signal': threshold_param.sigValueChanged,
                'getter': threshold_param.value,
                'setter': threshold_param.setValue,
                'mode': SyncMode.BIDIRECTIONAL
            }
        }
    )

The shortcut syntax is ideal for simple cases where you just want to sync the parameter value.

Binding List Parameters (ComboBox)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

List parameters require syncing both the options (limits) and the selected value:

.. code-block:: python

    # Create a list parameter
    params = [
        {'title': 'Algorithm:', 'name': 'algorithm', 'type': 'list',
         'limits': ['FFT', 'Wavelet', 'Correlation'], 'value': 'FFT'},
    ]

    settings = Parameter.create(name='settings', type='group',
                               children=params)
    algorithm_param = settings.child('algorithm')

    # Create sync for both limits and value
    sync = WidgetSync(initial_value={
        'algorithms': ['FFT', 'Wavelet', 'Correlation'],
        'algorithm': 'FFT'
    })

    # Bind toolbar combobox (regular Qt widget)
    sync.bind_properties(
        algorithm_combo,
        property_map={
            'algorithms': {
                'signal': None,  # FROM_SYNC only
                'getter': lambda: [algorithm_combo.itemText(i)
                                  for i in range(algorithm_combo.count())],
                'setter': lambda items: (algorithm_combo.clear(),
                                        algorithm_combo.addItems(items)),
                'mode': SyncMode.FROM_SYNC
            },
            'algorithm': {
                'signal': algorithm_combo.currentTextChanged,
                'getter': lambda: algorithm_combo.currentText(),
                'setter': lambda text: algorithm_combo.setCurrentText(text),
            }
        }
    )

    # Bind parameter (use bind_parameter!)
    sync.bind_parameter(
        algorithm_param,
        property_map={
            'algorithms': {
                'getter': lambda: algorithm_param.opts['limits'],
                'setter': algorithm_param.setLimits,
                'mode': SyncMode.FROM_SYNC,
            },
            'algorithm': {
                'signal': algorithm_param.sigValueChanged,
                'getter': algorithm_param.value,
                'setter': algorithm_param.setValue,
            }
        }
    )

Now the combobox, parameter value, and parameter tree all stay synchronized!

Parameter Signal Details
^^^^^^^^^^^^^^^^^^^^^^^^^

**Important:** Parameter signals emit ``(param, value)`` tuples, not just values:

.. code-block:: python

    # Parameter signals emit (param, value)
    def on_param_changed(param, value):
        print(f"{param.name()} changed to {value}")

    my_param.sigValueChanged.connect(on_param_changed)

The ``bind_parameter()`` method automatically handles this by extracting the value
from the ``(param, value)`` tuple before passing it to the sync system.

Complete Example
^^^^^^^^^^^^^^^^

See ``pymodaq_gui/examples/widget_sync/6_parameter_binding_example.py`` for a complete
working example showing:

- Syncing multiple parameter types (list, int, float, bool)
- Toolbar + parameter tree staying synchronized
- Both shortcut and manual syntax
- Programmatic value changes

.. code-block:: bash

    python -m pymodaq_gui.examples.widget_sync.6_parameter_binding_example

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

**For most users:** Use ``ValueSync`` or ``DictSync`` directly with validators and transforms.
Subclassing is rarely needed.

**For library developers:** This section explains when and how to extend the sync system.

.. tip::
   **Example:** :file:`examples/widget_sync/3_advanced_sync_example.py` demonstrates:

   - Multiple syncs on the same widget (Tab 1 - ListWidget with items + selection)
   - Dynamic property addition/removal (Tab 2 - Adding properties at runtime)
   - Custom sync classes extending BaseWidgetSync (Tab 3 - RangeSync example)

Understanding the Architecture
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The widget sync system has four main classes:

1. **BaseWidgetSync** - Internal base class providing connection management infrastructure
2. **ValueSync** - Synchronizes single values (int, str, bool, custom objects)
3. **DictSync** - Synchronizes dictionary values with multiple keys
4. **WidgetSync** - Smart factory that auto-selects ValueSync or DictSync based on initial_value

**Internal Design Note:**

To maximize code reuse (~900 lines of shared infrastructure), both ValueSync and DictSync
use dict storage internally:

* ``ValueSync(42)`` internally stores: ``{"__value__": 42}``
* ``DictSync({'r': 255})`` stores: ``{'r': 255}``

This allows unified callback routing at the cost of wrapping overhead for ValueSync.
This is an implementation detail - users work with the unwrapped values.

When to Extend
~~~~~~~~~~~~~~

**Don't subclass if you can use:**

* ``DictSync`` with a ``validator`` parameter (handles 90% of custom validation logic)
* Transform functions (``to_sync_transform`` / ``from_sync_transform``)
* Custom factory methods (see below)

**Do subclass ``BaseWidgetSync`` only for:**

* **Computed/derived values** - Storage format differs from exposed format (e.g., HSV ↔ RGB, center/width ↔ min/max)
* **Custom propagation strategies** - Debouncing, throttling, batched updates
* **Persistent sync** - Auto-save to file/database, network synchronization
* **Complex behaviors** - Undo/redo history, conditional propagation

Extension Options
~~~~~~~~~~~~~~~~~

There are three ways to extend the widget sync system:

1. **Custom Factory Methods** (Easiest) - Add convenience methods for your widget types
2. **Custom Validators** (Common) - Use DictSync/ValueSync with validation functions
3. **Custom Sync Classes** (Advanced) - Subclass BaseWidgetSync for computed values or custom behavior

Option 1: Custom Factory Methods (Easiest)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extend ``WidgetSyncFactories`` to add convenience methods for your custom widgets:

.. code-block:: python

    from pymodaq_gui.utils.widget_sync import WidgetSync, WidgetSyncFactories

    class MyWidgetSync(WidgetSync, WidgetSyncFactories):
        """Enhanced WidgetSync with custom factory methods"""

        @classmethod
        def for_my_custom_widget(cls, widget, initial=None):
            """Factory for my custom widget type"""
            return cls.for_property(
                widget,
                property_name='customValue',
                signal_name='customValueChanged',
                initial=initial
            )

    # Usage
    sync = MyWidgetSync.for_my_custom_widget(my_widget, initial=100)
    sync.add(another_custom_widget)

Option 2: Custom Validators (Common)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For validation logic, use DictSync or ValueSync with a validator function:

.. code-block:: python

    from pymodaq_gui.utils.widget_sync import DictSync

    # Example: Range validation with auto-swap
    def range_validator(value):
        """Ensure min <= max, swap if needed"""
        min_val, max_val = value['min'], value['max']
        if min_val > max_val:
            return {'min': max_val, 'max': min_val}
        return value

    sync = DictSync({'min': 20, 'max': 80}, validator=range_validator)
    sync.bind_dict({
        'min': {'widget': min_spinbox, 'property': 'value'},
        'max': {'widget': max_spinbox, 'property': 'value'}
    })

    # No subclassing needed! Much simpler than creating a custom class.

Option 3: Custom Sync Classes (Advanced)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Only subclass ``BaseWidgetSync`` when you need computed/derived values or custom
propagation logic that can't be achieved with validators.

**Example: When NOT to subclass**

Don't create a custom RangeSync class just for validation - use DictSync + validator as shown above.

**Example: When TO subclass - ColorSync**

Subclass when storage format differs from exposed format:

.. code-block:: python

    from pymodaq_gui.utils.widget_sync import BaseWidgetSync

    class ColorSync(BaseWidgetSync):
        """
        Sync colors with HSV ↔ RGB conversion.

        Stores: HSV internally (easier for brightness/saturation)
        Exposes: RGB for display widgets
        """

        def __init__(self, h=0, s=100, v=100):
            super().__init__()
            self._h = h  # Hue: 0-360
            self._s = s  # Saturation: 0-100
            self._v = v  # Value/Brightness: 0-100
            self._data_type = dict
            self._value = self._hsv_to_rgb_dict()
            self._previous_value = self._value.copy()

        @property
        def value(self):
            """Return as RGB dict for widgets"""
            return self._hsv_to_rgb_dict()

        @value.setter
        def value(self, rgb_dict):
            """Accept RGB, store as HSV"""
            self._rgb_to_hsv(rgb_dict['r'], rgb_dict['g'], rgb_dict['b'])
            new_value = self._hsv_to_rgb_dict()
            if self._value != new_value:
                self._previous_value = self._value.copy()
                self._value = new_value
                self.value_changed.emit(self._value)

        def set_value(self, rgb_dict, emit=True):
            """Set RGB value"""
            self._rgb_to_hsv(rgb_dict['r'], rgb_dict['g'], rgb_dict['b'])
            new_value = self._hsv_to_rgb_dict()
            if self._value != new_value:
                self._previous_value = self._value.copy()
                self._value = new_value
                if emit:
                    self.value_changed.emit(self._value)

        def _get_internal_storage_key(self):
            """Return None for dict-like binding"""
            return None

        def _get_user_facing_value(self):
            """Return current RGB dict"""
            return self.value

        # Convenience methods leveraging HSV storage
        def adjust_brightness(self, delta):
            """Adjust brightness (much easier in HSV than RGB!)"""
            self._v = max(0, min(100, self._v + delta))
            new_value = self._hsv_to_rgb_dict()
            if self._value != new_value:
                self._previous_value = self._value.copy()
                self._value = new_value
                self.value_changed.emit(self._value)

        def _hsv_to_rgb_dict(self):
            """Convert HSV to RGB dict"""
            # ... conversion logic ...
            return {'r': r, 'g': g, 'b': b}

        def _rgb_to_hsv(self, r, g, b):
            """Convert RGB to HSV and store"""
            # ... conversion logic ...
            self._h, self._s, self._v = h, s, v

    # Usage
    color_sync = ColorSync(h=0, s=100, v=100)  # Red
    color_sync.bind_dict({
        'r': {'widget': r_slider, 'property': 'value'},
        'g': {'widget': g_slider, 'property': 'value'},
        'b': {'widget': b_slider, 'property': 'value'}
    })

    # Brightness adjustment is easier in HSV!
    color_sync.adjust_brightness(10)  # Can't do this with DictSync alone

Required Methods
~~~~~~~~~~~~~~~~

When subclassing ``BaseWidgetSync``, you must implement these five methods:

1. **__init__()** - Initialize ``_value``, ``_previous_value``, ``_data_type``, call ``super().__init__()``
2. **set_value(new_value, emit=True)** - Update value and optionally emit ``value_changed`` signal
3. **value property** - Get/set the synchronized value (property with getter and setter)
4. **_get_internal_storage_key()** - Return ``"__value__"`` for single-value sync, ``None`` for dict sync
5. **_get_user_facing_value()** - Return value for widget initialization (unwrapped for ValueSync, direct for DictSync)

**Note on methods 4 and 5:** These are internal plumbing methods for the base class infrastructure.
They handle the difference between ValueSync (which wraps values in ``{"__value__": x}``) and
DictSync (which stores dicts directly). For most custom syncs with dict-like behavior, return ``None``
from ``_get_internal_storage_key()`` and return ``self.value`` from ``_get_user_facing_value()``.

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

.. tip::
   **Example:** :file:`examples/widget_sync/4_dynamic_widgets_example.py` demonstrates:

   - Dynamic add/remove of synchronized sliders (Tab 1 - Audio mixer)
   - Widget cloning with automatic sync (Tab 2 - Control panel duplication)
   - Automatic cleanup when widgets are destroyed

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

Extending Widget Sync (Advanced)
---------------------------------

For library developers who need to extend the widget sync system.

.. tip::
   **Example:** :file:`examples/widget_sync/5_extending_sync_example.py` demonstrates all three extension approaches:

   - Tab 1: Custom factory methods (range spinboxes, slider with label)
   - Tab 2: Custom validators (value clamping, range auto-swap)
   - Tab 3: Custom sync class (CoordinateSync for image coordinate systems)

See the "Extending Widget Sync" section above for detailed documentation on:

- Option 1: Custom Factory Methods (Easiest)
- Option 2: Custom Validators (Common)
- Option 3: Custom Sync Classes (Advanced)

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

Complete examples demonstrating widget synchronization are available:

.. code-block:: bash

    # Level 1: Basic synchronization (checkboxes, sliders, spinboxes)
    python -m pymodaq_gui.examples.widget_sync.1_basic_sync_example

    # Level 2: Dictionary synchronization (RGB colors, coordinates)
    python -m pymodaq_gui.examples.widget_sync.2_dict_sync_example

    # Level 3: Advanced patterns (transforms, conditional syncing)
    python -m pymodaq_gui.examples.widget_sync.3_advanced_sync_example

    # Level 4: Dynamic widget management
    python -m pymodaq_gui.examples.widget_sync.4_dynamic_widgets_example

    # Level 5: Extending widget_sync (custom factories, validators, sync classes)
    python -m pymodaq_gui.examples.widget_sync.5_extending_sync_example

    # Level 6: Parameter binding (pyqtgraph Parameters with bind_parameter())
    python -m pymodaq_gui.examples.widget_sync.6_parameter_binding_example

See Also
--------

* :ref:`contributing` - Contributing guidelines
* :ref:`api` - Full API reference



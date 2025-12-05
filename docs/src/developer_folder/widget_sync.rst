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
    sync.add(spinbox)  # Stays in sync

    # Add read-only display
    sync.connect(
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
        initial=50
    )

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
    sync.connect(label, setter=lambda v: label.setText(str(v)),
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

    # Boolean ↔ ComboBox index
    bool_sync = WidgetSync.for_checkbox(checkbox, initial=True)

    bool_sync.connect(
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

    sync.connect(
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
* ``disconnect()`` - Removes connection entirely, needs reconnection

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

    # Permanently disconnect widget
    sync.disconnect(widget)
    # or
    sync.remove(widget)  # Alias for disconnect

    # Disconnect all (useful when deleting the sync itself)
    sync.disconnect_all()

**When to use what:**

* ``disable()`` - Temporary pause, keeps connection setup, fast to re-enable
* ``disconnect()`` - Permanent removal, requires full reconnection
* Automatic cleanup - Widget deletion triggers cleanup automatically


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

            # Connect menu action
            self.auto_sync.connect(
                self.menu_auto,
                signal=self.menu_auto.toggled,
                getter=lambda: self.menu_auto.isChecked(),
                setter=lambda v: self.menu_auto.setChecked(v)
            )

Settings Panel
~~~~~~~~~~~~~~

Manage complex settings with multiple syncs:

.. code-block:: python

    class SettingsPanel(QWidget):
        def __init__(self):
            super().__init__()

            # Create syncs for different settings
            self.syncs = {
                'auto_mode': WidgetSync.for_checkbox(self.auto_cb, initial=False),
                'sample_rate': WidgetSync.for_spinbox(self.rate_spin, initial=1000),
                'averaging': WidgetSync.for_spinbox(self.avg_spin, initial=10),
            }

        def get_settings(self):
            """Get all settings as dict"""
            return {key: sync.value for key, sync in self.syncs.items()}

        def set_settings(self, settings):
            """Set all settings from dict"""
            for key, value in settings.items():
                if key in self.syncs:
                    self.syncs[key].value = value

Multi-View Synchronization
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Keep multiple views of the same data synchronized:

.. code-block:: python

    # Main view slider
    main_sync = WidgetSync.for_slider(main_slider, initial=50)

    # Add compact view
    main_sync.add(compact_slider)

    # Add detailed view with transforms
    main_sync.connect(
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

            # Connect to sync
            self.sync.connect(
                slider,
                signal=slider.valueChanged,
                getter=lambda: slider.value(),
                setter=lambda v: slider.setValue(v)
            )

            self.widgets.append(slider)
            self.layout().addWidget(slider)

        def remove_widget(self, slider):
            """Remove a widget from the panel"""
            self.sync.disconnect(slider)
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

WidgetSync Class
~~~~~~~~~~~~~~~~

.. autoclass:: pymodaq_gui.utils.widget_sync.WidgetSync
   :members:
   :undoc-members:

SyncMode Enum
~~~~~~~~~~~~~

.. autoclass:: pymodaq_gui.utils.widget_sync.SyncMode
   :members:

WidgetSyncFactories Mixin
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: pymodaq_gui.utils.widget_sync.WidgetSyncFactories
   :members:
   :undoc-members:

Examples
--------

See the complete example in:

.. code-block:: bash

    python -m pymodaq_gui.examples.widget_sync_example


Best Practices
--------------

DO:
~~~

* ✅ Use ``add()`` for widgets of the same type
* ✅ Use ``connect()`` for different widget types
* ✅ Use ``SyncMode.FROM_SYNC`` for read-only displays
* ✅ Use factory methods for common cases
* ✅ Create custom factories for your widget types
* ✅ Use ``disable()``/``enable()`` for temporary pauses
* ✅ Use ``disconnect()`` for permanent removal
* ✅ Check ``connection_count`` and ``connected_widgets`` for debugging

DON'T:
~~~~~~

* ❌ Don't use ``add()`` with different widget types (use ``connect()`` instead)
* ❌ Don't create circular sync chains (A→B→C→A)
* ❌ Don't disconnect/reconnect frequently (use ``disable()``/``enable()`` instead)
* ❌ Don't manually disconnect unless necessary (automatic cleanup works)
* ❌ Don't forget to handle value transformations when syncing different types


See Also
--------

* :ref:`contributing` - Contributing guidelines
* :ref:`api` - Full API reference
* Example code: ``pymodaq_gui/examples/widget_sync_example.py``

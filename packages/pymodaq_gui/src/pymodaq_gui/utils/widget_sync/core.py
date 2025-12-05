"""
Core widget synchronization classes and enums.

Implementation for syncing widget properties across multiple widgets.

"""
from __future__ import annotations

from qtpy.QtCore import QObject, Signal
from qtpy.QtWidgets import QWidget
from enum import Enum
from typing import Callable, Any, Iterator, Type
from contextlib import contextmanager
from weakref import ref, ReferenceType

ValueTransform = Callable[[Any], Any]
WidgetGetter = Callable[[], Any]
WidgetSetter = Callable[[Any], None]
ConnectionInfo = dict[str, Any]  # Connection metadata dictionary


class SyncMode(Enum):
    """Synchronization modes for widget connections"""
    BIDIRECTIONAL = "bidirectional"  # Widget ↔ Sync (default)
    TO_SYNC = "to_sync"  # Widget → Sync only
    FROM_SYNC = "from_sync"  # Sync → Widget only


class DataType(Enum):
    """
    Supported data types for widget synchronization.

    Each sync instance is associated with a specific data type, ensuring
    type safety when connecting widgets and transforming values.
    """
    BOOL = bool
    INT = int
    FLOAT = float
    STR = str
    OBJECT = object  # For custom types or when type checking is disabled


class WidgetSync(QObject):
    """
    Lightweight widget synchronization for keeping widget properties in sync.

    Philosophy: Simple by default, powerful when needed.
    - Core responsibility: Sync a single value across multiple widgets
    - Exception-safe widget updates
    - Automatic cleanup when widgets are deleted

    Features:
    - Bidirectional sync between widgets and internal state
    - Value transformation per widget (widget <-> sync)
    - Automatic widget lifecycle management
    - Multiple sync modes (bidirectional, to_sync, from_sync)
    - Clean disconnect by widget reference

    Example:
        # Create sync for a checkbox
        sync = WidgetSync.for_checkbox(my_checkbox, initial=True)

        # Add more checkboxes
        sync.add(another_checkbox)
        sync.add(third_checkbox, mode=SyncMode.FROM_SYNC)  # read-only

        # Change value programmatically
        sync.value = False  # All checkboxes update

        # Remove a widget
        sync.remove(another_checkbox)
    """

    value_changed = Signal(object)  # Emitted when value changes

    def __init__(self, initial_value: Any = None, data_type: Type | DataType | None = None) -> None:
        """
        Initialize widget sync with an initial value and optional type checking.

        Parameters
        ----------
        initial_value : Any
            Initial value for the sync
        data_type : Type | DataType, optional
            Expected data type for values. If None, inferred from initial_value.
            Use DataType.OBJECT to disable type checking.

        Examples
        --------
        >>> # Type inferred from initial value
        >>> sync = WidgetSync(initial_value=True)  # data_type = bool

        >>> # Explicit type
        >>> sync = WidgetSync(initial_value=0, data_type=int)

        >>> # Disable type checking
        >>> sync = WidgetSync(initial_value=None, data_type=DataType.OBJECT)
        """
        super().__init__()
        self._data_type = self._resolve_type(initial_value, data_type)
        self._value: Any = self._validate_value(initial_value)
        # Dict mapping widget id() to connection info for O(1) lookup
        # Key: id(widget), Value: ConnectionInfo dict
        self._connections: dict[int, ConnectionInfo] = {}

    def _resolve_type(self, initial_value: Any, data_type: Type | DataType | None) -> Type:
        """
        Resolve the data type for this sync.

        Parameters
        ----------
        initial_value : Any
            Initial value
        data_type : Type | DataType, optional
            Explicit type or None to infer

        Returns
        -------
        Type
            Resolved Python type
        """
        if data_type is not None:
            # Use explicit type
            if isinstance(data_type, DataType):
                return data_type.value
            return data_type

        # Infer from initial value
        if initial_value is None:
            return object  # No type checking if no initial value
        return type(initial_value)

    def _validate_value(self, value: Any) -> Any:
        """
        Validate value matches expected type.

        Parameters
        ----------
        value : Any
            Value to validate

        Returns
        -------
        Any
            The value if valid

        Raises
        ------
        TypeError
            If value doesn't match expected type
        """
        if value is None or self._data_type is object:
            return value

        if not isinstance(value, self._data_type):
            raise TypeError(
                f"Value has type {type(value).__name__}, "
                f"but sync expects {self._data_type.__name__}"
            )
        return value

    def _is_compatible_type(self, value: Any) -> bool:
        """
        Check if value is compatible with sync's data type.

        Parameters
        ----------
        value : Any
            Value to check

        Returns
        -------
        bool
            True if compatible
        """
        if value is None or self._data_type is object:
            return True
        return isinstance(value, self._data_type)

    def _data_type_name(self) -> str:
        """Get human-readable name of data type"""
        if hasattr(self._data_type, '__name__'):
            return self._data_type.__name__
        return str(self._data_type)

    @property
    def data_type(self) -> Type:
        """
        Get the data type for this sync.

        Returns
        -------
        Type
            Python type (bool, int, float, str, object)
        """
        return self._data_type

    @property
    def value(self) -> Any:
        """Get current synced value"""
        return self._value

    @value.setter
    def value(self, new_value: Any) -> None:
        """Set value and emit change signal"""
        self.set_value(new_value, emit=True)

    def set_value(self, new_value: Any, emit: bool = True) -> None:
        """
        Set value with optional emission control.

        Parameters
        ----------
        new_value : Any
            The new value to set
        emit : bool, optional
            Whether to emit value_changed signal (default: True)

        Raises
        ------
        TypeError
            If new_value doesn't match expected data type
        """
        # Validate type
        new_value = self._validate_value(new_value)

        if self._value != new_value:
            self._value = new_value
            if emit:
                self.value_changed.emit(new_value)

    @contextmanager
    def _block_signals(self, widget: QWidget) -> Iterator[None]:
        """
        Context manager for exception-safe signal blocking.

        Ensures signals are always unblocked even if setter raises.

        Parameters
        ----------
        widget : QWidget
            The widget whose signals to block

        Yields
        ------
        None
        """
        was_blocked: bool = widget.signalsBlocked()
        widget.blockSignals(True)
        try:
            yield
        finally:
            widget.blockSignals(was_blocked)

    def connect(self,
                widget: QWidget,
                signal: Signal | None = None,
                getter: WidgetGetter | None = None,
                setter: WidgetSetter | None = None,
                mode: SyncMode | None = None,
                to_sync_transform: ValueTransform | None = None,
                from_sync_transform: ValueTransform | None = None) -> None:
        """
        Connect a widget to this sync.

        Parameters
        ----------
        widget : QWidget
            The widget to connect
        signal : Signal, optional
            The signal to listen to (auto-required for TO_SYNC/BIDIRECTIONAL modes)
        getter : callable, optional
            Function to get value from widget: () -> value
            Required for TO_SYNC and BIDIRECTIONAL modes
        setter : callable, optional
            Function to set value on widget: (value) -> None
            Required for FROM_SYNC and BIDIRECTIONAL modes
        mode : SyncMode, optional
            Synchronization mode. If None, auto-inferred from parameters:
            - Both getter and setter provided: BIDIRECTIONAL
            - Only getter provided: TO_SYNC
            - Only setter provided: FROM_SYNC
        to_sync_transform : callable, optional
            Transform value from widget to sync: (widget_value) -> sync_value
        from_sync_transform : callable, optional
            Transform value from sync to widget: (sync_value) -> widget_value

        Raises
        ------
        ValueError
            If neither getter nor setter provided, or if mode requirements not met
        RuntimeError
            If transforms raise exceptions

        Examples
        --------
        # Auto-inferred modes (mode parameter omitted):
        sync.connect(label, setter=lambda v: label.setText(str(v)))  # FROM_SYNC
        sync.connect(button, button.clicked, getter=lambda: True)     # TO_SYNC
        sync.connect(spinbox, spinbox.valueChanged,
                     getter=lambda: spinbox.value(),
                     setter=lambda v: spinbox.setValue(v))            # BIDIRECTIONAL

        # Explicit mode override:
        sync.connect(widget, signal, getter=getter, setter=setter,
                     mode=SyncMode.FROM_SYNC)  # Override auto-inference
        """
        # Auto-infer mode if not specified
        if mode is None:
            if getter is not None and setter is not None:
                mode = SyncMode.BIDIRECTIONAL
            elif getter is not None:
                mode = SyncMode.TO_SYNC
            elif setter is not None:
                mode = SyncMode.FROM_SYNC
            else:
                raise ValueError(
                    "Must provide at least getter or setter parameter"
                )

        # Validate signal requirement
        if mode in (SyncMode.BIDIRECTIONAL, SyncMode.TO_SYNC) and signal is None:
            raise ValueError(f"signal parameter is required for {mode.value} mode")

        # Validate getter/setter requirements
        if mode in (SyncMode.BIDIRECTIONAL, SyncMode.TO_SYNC): 
            if getter is None:
                raise ValueError(f"getter parameter is required for {mode.value} mode")
            else:  # Type checking: validate getter returns correct type (after transform)
                try:
                    test_value = getter()
                    # Apply to_sync transform if provided
                    if to_sync_transform:
                        test_value = to_sync_transform(test_value)
                    # Check type compatibility
                    if not self._is_compatible_type(test_value):
                        raise TypeError(
                            f"Getter returns {type(test_value).__name__}, "
                            f"but sync expects {self._data_type_name()}. "
                            f"Widget: {type(widget).__name__}"
                        )
                except TypeError:
                    raise  # Re-raise type errors
                except Exception as e:
                    # Log other errors but don't fail - the getter might need the widget to be in a specific state
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Could not validate getter for {type(widget).__name__}: {e}"
                    )

        if mode in (SyncMode.BIDIRECTIONAL, SyncMode.FROM_SYNC):
            if setter is None:
                raise ValueError(f"setter parameter is required for {mode.value} mode")
            else:  # Type checking: validate setter returns correct type (after transform)
                # TODO: Implement setter type checking if needed
                pass

        # Store weak references to avoid circular references and memory leaks
        widget_ref = ref(widget)
        widget_id = id(widget)  # Store id for dict key

        # Use weak reference to self to avoid accessing invalid self during cleanup
        sync_weak = ref(self)

        def on_destroyed():
            """Cleanup callback when widget is destroyed"""
            sync = sync_weak()
            if sync is not None:
                sync._on_widget_destroyed(widget_id)

        widget.destroyed.connect(on_destroyed)

        connection_info = {
            'widget_id': widget_id,  # Store for easier lookup
            'widget_ref': widget_ref,
            'widget_type': type(widget).__name__,  # Store widget type for pattern matching
            'signal': signal,
            'getter': getter,
            'setter': setter,
            'mode': mode,
            'to_sync_transform': to_sync_transform,
            'from_sync_transform': from_sync_transform,
            'callbacks': [],
            'enabled': True,  # Connection enabled by default
            # Connection pattern info for add() method (set by factories)
            'property_name': None,  # Will be set by for_property()
            'signal_name': None,    # Will be set by for_property()
        }

        # Widget → Sync connection
        if mode in (SyncMode.BIDIRECTIONAL, SyncMode.TO_SYNC):
            def on_widget_change(*args):
                """Handle widget value changes"""
                widget_obj = widget_ref()
                if widget_obj is None:
                    return  # Widget was deleted

                # Check if connection is enabled
                conn = self._connections.get(widget_id)
                if conn is None or not conn.get('enabled', True):
                    return  # Connection disabled

                try:
                    value = args[0] if args else getter()
                    if to_sync_transform:
                        value = to_sync_transform(value)
                    self.set_value(value, emit=True)
                except Exception as e:
                    # Log error instead of raising to avoid crashing Qt event loop
                    import logging
                    logging.getLogger(__name__).error(
                        f"Error syncing from widget {type(widget).__name__}: {e}",
                        exc_info=True
                    )

            signal.connect(on_widget_change)
            connection_info['callbacks'].append(('widget', on_widget_change))

        # Sync → Widget connection
        if mode in (SyncMode.BIDIRECTIONAL, SyncMode.FROM_SYNC):
            def on_sync_change(value):
                """Handle sync value changes"""
                widget_obj = widget_ref()
                if widget_obj is None:
                    return  # Widget was deleted

                # Check if connection is enabled
                conn = self._connections.get(widget_id)
                if conn is None or not conn.get('enabled', True):
                    return  # Connection disabled

                try:
                    if from_sync_transform:
                        value = from_sync_transform(value)
                    with self._block_signals(widget_obj):
                        setter(value)
                except Exception as e:
                    # Log error instead of raising to avoid crashing Qt event loop
                    import logging
                    logging.getLogger(__name__).error(
                        f"Error updating widget {type(widget).__name__}: {e}",
                        exc_info=True
                    )

            self.value_changed.connect(on_sync_change)
            # Store 2-tuple for sync callbacks to avoid circular reference
            connection_info['callbacks'].append(('sync', on_sync_change))

        # Initialize widget with current value
        if mode in (SyncMode.BIDIRECTIONAL, SyncMode.FROM_SYNC) and self._value is not None:
            try:
                value = self._value
                if from_sync_transform:
                    value = from_sync_transform(value)
                with self._block_signals(widget):
                    setter(value)
            except Exception as e:
                raise RuntimeError(
                    f"Error initializing widget {type(widget).__name__}: {e}"
                ) from e

        self._connections[widget_id] = connection_info

    def _disconnect_callbacks(self, callbacks: list) -> None:
        """
        Disconnect sync callbacks from value_changed signal.

        Qt auto-cleans widget callbacks, so we only disconnect sync callbacks.

        Parameters
        ----------
        callbacks : list
            List of callback tuples (callback_type, callback)
        """
        for callback_type, callback in callbacks:
            if callback_type == 'sync':
                try:
                    self.value_changed.disconnect(callback)
                except (TypeError, RuntimeError):
                    pass  # Already disconnected

    def _on_widget_destroyed(self, widget_id: int) -> None:
        """
        Callback when a connected widget is destroyed.

        Called by Qt's destroyed signal.

        Parameters
        ----------
        widget_id : int
            The id() of the destroyed widget
        """
        self.disconnect(widget_id)

    def disconnect(self, widget: QWidget | int) -> None:
        """
        Disconnect a widget by reference or ID.

        Parameters
        ----------
        widget : QWidget | int
            The widget to disconnect, or its ID
        """
        # Handle both widget object and widget_id
        widget_id = widget if isinstance(widget, int) else id(widget)

        conn = self._connections.get(widget_id)
        if conn is not None:
            self._disconnect_callbacks(conn['callbacks'])
            del self._connections[widget_id]

    def disconnect_all(self) -> None:
        """Disconnect all connected widgets."""
        for conn in self._connections.values():
            self._disconnect_callbacks(conn['callbacks'])
        self._connections.clear()

    def add(self, widget: QWidget, mode: SyncMode = SyncMode.BIDIRECTIONAL,
            match: str = 'type',
            to_sync_transform: ValueTransform | None = None,
            from_sync_transform: ValueTransform | None = None) -> None:
        """
        Convenience method to add a widget using auto-detected property sync.

        Automatically detects the property/signal pattern from existing connections.

        Parameters
        ----------
        widget : QWidget
            Widget to add
        mode : SyncMode, optional
            Sync mode (default: BIDIRECTIONAL)
        match : str, optional
            Pattern matching strategy (default: 'type'):

            - 'type': Match exact widget type (QSlider → QSlider only, safest)
            - 'property': Match by property/signal names (QSlider + QSpinBox both work)
        to_sync_transform : callable, optional
            Transform value from widget to sync
        from_sync_transform : callable, optional
            Transform value from sync to widget

        Raises
        ------
        TypeError
            If no connection pattern found, or if widget doesn't have the required signal
        ValueError
            If match parameter has invalid value

        Examples
        --------
        >>> # Type matching (default) - only same widget types
        >>> sync = WidgetSync.for_slider(slider1)
        >>> sync.add(slider2)  # OK - both QSlider

        >>> # Property matching - different widget types with same property
        >>> sync = WidgetSync.for_slider(slider1)
        >>> sync.add(spinbox, match='property')  # OK - both use 'value'/'valueChanged'
        """
        if match not in ('type', 'property'):
            raise ValueError(f"match must be 'type' or 'property', got {match!r}")

        widget_type = type(widget).__name__
        property_name = None
        signal_name = None

        if match == 'type':
            # Look for existing connection with exact matching widget type
            for conn in self._connections.values():
                if conn['widget_type'] == widget_type:
                    # Found exact type match - use this pattern
                    property_name = conn.get('property_name')
                    signal_name = conn.get('signal_name')
                    if property_name and signal_name:
                        break
        else:  # match == 'property'
            # Look for any connection with property/signal info
            for conn in self._connections.values():
                property_name = conn.get('property_name')
                signal_name = conn.get('signal_name')
                if property_name and signal_name:
                    # Found pattern - check if widget is compatible
                    if hasattr(widget, signal_name):
                        break
                    else:
                        # Reset and continue searching
                        property_name = None
                        signal_name = None

        # If no pattern found, raise error
        if property_name is None or signal_name is None:
            match_hint = (
                "try match='property' to allow different widget types"
                if match == 'type' else ""
            )
            raise TypeError(
                f"Cannot use add() for {widget_type}: no connection pattern found "
                f"(match='{match}').\n\n"
                f"💡 Solutions:\n"
                f"{('  - ' + match_hint + chr(10)) if match_hint else ''}"
                f"  - Use connect() directly:\n\n"
                f"    sync.connect(\n"
                f"        widget,\n"
                f"        signal=widget.appropriate_signal,\n"
                f"        getter=lambda: widget.get_value(),\n"
                f"        setter=lambda v: widget.set_value(v),\n"
                f"        mode=SyncMode.{mode.name}\n"
                f"    )"
            )

        # Check if widget has the required signal
        if not hasattr(widget, signal_name):
            raise TypeError(
                f"Cannot use add() to connect {widget_type}: "
                f"it doesn't have the '{signal_name}' signal.\n\n"
                f"💡 Solution: Use connect() instead of add():\n\n"
                f"    sync.connect(\n"
                f"        widget,\n"
                f"        signal=widget.appropriate_signal,\n"
                f"        getter=lambda: widget.get_value(),\n"
                f"        setter=lambda v: widget.set_value(v),\n"
                f"        mode=SyncMode.{mode.name}\n"
                f"    )"
            )

        # Get signal and create getter/setter using weak reference to avoid keeping widget alive
        from weakref import ref
        signal = getattr(widget, signal_name)
        prop_name = property_name  # Local variable to avoid closure issues
        widget_ref = ref(widget)  # Weak reference to widget

        # Getter/setter use weak reference to avoid circular reference
        def getter():
            w = widget_ref()
            return w.property(prop_name) if w is not None else None

        def setter(value):
            w = widget_ref()
            if w is not None:
                w.setProperty(prop_name, value)

        # Connect the widget
        self.connect(widget, signal, getter, setter, mode,
                    to_sync_transform, from_sync_transform)

    def remove(self, widget: QWidget) -> None:
        """
        Convenience method to remove a widget.

        Alias for disconnect() for consistency with add().

        Parameters
        ----------
        widget : QWidget
            Widget to remove
        """
        self.disconnect(widget)

    def enable(self, widget: QWidget | int) -> None:
        """
        Enable a widget's connection.

        When enabled, the widget will sync bidirectionally with other widgets.

        Parameters
        ----------
        widget : QWidget | int
            The widget to enable, or its ID

        Raises
        ------
        ValueError
            If widget is not connected
        """
        widget_id = widget if isinstance(widget, int) else id(widget)
        conn = self._connections.get(widget_id)
        if conn is None:
            raise ValueError(f"Widget is not connected to this sync")
        conn['enabled'] = True

    def disable(self, widget: QWidget | int) -> None:
        """
        Disable a widget's connection temporarily.

        When disabled, the widget will not receive updates from the sync,
        and its changes will not affect other widgets. The connection remains
        in place and can be re-enabled later.

        This is useful for:
        - Temporarily pausing sync during complex operations
        - Conditional syncing based on application state
        - Testing/debugging

        Parameters
        ----------
        widget : QWidget | int
            The widget to disable, or its ID

        Raises
        ------
        ValueError
            If widget is not connected

        Example
        -------
        >>> sync = WidgetSync.for_slider(slider1)
        >>> sync.add(slider2)
        >>> sync.disable(slider2)  # slider2 stops syncing
        >>> slider1.setValue(75)   # slider2 doesn't update
        >>> sync.enable(slider2)   # Re-enable slider2
        >>> slider2.value()        # Still has old value until next update
        """
        widget_id = widget if isinstance(widget, int) else id(widget)
        conn = self._connections.get(widget_id)
        if conn is None:
            raise ValueError(f"Widget is not connected to this sync")
        conn['enabled'] = False

    def is_enabled(self, widget: QWidget | int) -> bool:
        """
        Check if a widget's connection is enabled.

        Parameters
        ----------
        widget : QWidget | int
            The widget to check, or its ID

        Returns
        -------
        bool
            True if enabled, False if disabled

        Raises
        ------
        ValueError
            If widget is not connected
        """
        widget_id = widget if isinstance(widget, int) else id(widget)
        conn = self._connections.get(widget_id)
        if conn is None:
            raise ValueError(f"Widget is not connected to this sync")
        return conn.get('enabled', True)

    @property
    def connected_widgets(self) -> list[QWidget]:
        """
        Get list of currently connected widgets.

        Returns only widgets that haven't been deleted.

        Returns
        -------
        list[QWidget]
            List of active widget references

        Example
        -------
        >>> sync = WidgetSync.for_checkbox(cb1)
        >>> sync.add(cb2)
        >>> sync.add(cb3)
        >>> len(sync.connected_widgets)  # Returns 3
        3
        """
        widgets = []
        for conn in self._connections.values():
            widget = conn['widget_ref']()
            if widget is not None:
                widgets.append(widget)
        return widgets
    

    @property
    def connection_count(self) -> int:
        """
        Get count of active connections.

        Returns
        -------
        int
            Number of currently connected widgets

        Example
        -------
        >>> sync = WidgetSync.for_spinbox(spin1)
        >>> sync.add(spin2)
        >>> sync.connection_count  # Returns 2
        2
        """
        return len(self._connections)

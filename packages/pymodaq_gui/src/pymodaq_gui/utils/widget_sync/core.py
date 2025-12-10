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


class BaseWidgetSync(QObject):
    """
    Base class for widget synchronization.

    Provides common functionality for connection management, callbacks,
    feedback loop prevention, and widget lifecycle management.

    Subclasses must implement: set_value(), value property getter/setter
    """

    value_changed = Signal(object)  # Emitted when value changes

    def __init__(self) -> None:
        """Initialize base sync - called by subclasses."""
        super().__init__()
        # Connection storage with composite keys (widget_id, property_key)
        self._connections: dict[tuple[int, str | None], ConnectionInfo] = {}
        # Track which widget is currently sending an update
        self._sender_widget_id: int | None = None
        # Will be initialized by subclasses
        self._value: Any = None
        self._previous_value: Any = None
        self._validator: Callable[[Any], Any] | None = None
        self._data_type: Type = object

    def set_value(self, new_value: Any, emit: bool = True) -> None:
        """Set value - must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement set_value()")

    @property
    def value(self) -> Any:
        """Get current value - must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement value property getter")

    @value.setter
    def value(self, new_value: Any) -> None:
        """Set current value - must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement value property setter")

    def _get_bind_property_key(self) -> str | None:
        """
        Get the property_key to use for bind() callbacks.

        Returns "__value__" for ValueSync, None for DictSync.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement _get_bind_property_key()")

    def _get_bind_value(self) -> Any:
        """
        Get the value to initialize widgets with in bind().

        Returns unwrapped value for ValueSync, full dict for DictSync.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement _get_bind_value()")

    # Connection Management Methods

    def _get_connection(self, widget_id: int, property_key: str | None = None) -> ConnectionInfo | None:
        """Get connection by composite key."""
        return self._connections.get((widget_id, property_key))

    def _set_connection(self, widget_id: int, property_key: str | None, connection_info: ConnectionInfo) -> None:
        """Set connection with composite key."""
        connection_info['property_key'] = property_key
        self._connections[(widget_id, property_key)] = connection_info

    def _remove_connection(self, widget_id: int, property_key: str | None = None) -> None:
        """Remove connection and disconnect callbacks."""
        key = (widget_id, property_key)
        if conn := self._connections.get(key):
            self._disconnect_callbacks(conn['callbacks'])
            del self._connections[key]

    def _get_connection_keys_for_widget(self, widget_id: int) -> list[tuple[int, str | None]]:
        """Get all connection keys for a widget."""
        return [k for k in self._connections if k[0] == widget_id]

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

    # Widget Lifecycle Methods

    def _setup_widget_destruction_callback(
        self,
        widget: QWidget,
        connection_keys: list[tuple[int, str | None]]
    ) -> None:
        """Setup callback for widget destruction."""
        sync_weak = ref(self)

        def on_destroyed():
            sync = sync_weak()
            if sync is not None:
                for key in connection_keys:
                    sync._remove_connection(key[0], key[1])

        widget.destroyed.connect(on_destroyed)

    def _on_widget_destroyed(self, widget_id: int) -> None:
        """
        Callback when a connected widget is destroyed.

        Called by Qt's destroyed signal.

        Parameters
        ----------
        widget_id : int
            The id() of the destroyed widget
        """
        self.unbind(widget_id)

    def unbind(self, widget: QWidget | int) -> None:
        """
        Unbind a widget by reference or ID.

        Removes ALL connections for the widget (both regular and property connections).

        Parameters
        ----------
        widget : QWidget | int
            The widget to unbind, or its ID
        """
        # Handle both widget object and widget_id
        widget_id = widget if isinstance(widget, int) else id(widget)

        # Remove all connections for this widget (both regular and property connections)
        connection_keys = self._get_connection_keys_for_widget(widget_id)
        for key in connection_keys:
            self._remove_connection(key[0], key[1])

    def unbind_all(self) -> None:
        """Unbind all connected widgets (both regular and property connections)."""
        # Disconnect all callbacks from the unified connections dictionary
        for conn in self._connections.values():
            self._disconnect_callbacks(conn['callbacks'])
        self._connections.clear()

    # Widget Control Methods

    def enable(self, widget: QWidget | int) -> None:
        """
        Enable a widget's connections.

        When enabled, the widget will sync bidirectionally with other widgets.
        This enables ALL connections for the widget (both regular and property connections).

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
        connection_keys = self._get_connection_keys_for_widget(widget_id)

        if not connection_keys:
            raise ValueError(f"Widget is not connected to this sync")

        # Enable all connections for this widget
        for key in connection_keys:
            conn = self._connections.get(key)
            if conn is not None:
                conn['enabled'] = True

    def disable(self, widget: QWidget | int) -> None:
        """
        Disable a widget's connections temporarily.

        When disabled, the widget will not receive updates from the sync,
        and its changes will not affect other widgets. The connections remain
        in place and can be re-enabled later.

        This disables ALL connections for the widget (both regular and property connections).

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
        connection_keys = self._get_connection_keys_for_widget(widget_id)

        if not connection_keys:
            raise ValueError(f"Widget is not connected to this sync")

        # Disable all connections for this widget
        for key in connection_keys:
            conn = self._connections.get(key)
            if conn is not None:
                conn['enabled'] = False


    def check_connection_mode(self, mode: SyncMode | None, setter, getter, property_key=None) -> SyncMode:
        # Auto-infer mode
        if mode is None:
            if getter is not None and setter is not None:
                mode = SyncMode.BIDIRECTIONAL
            elif getter is not None:
                mode = SyncMode.TO_SYNC
            elif setter is not None:
                mode = SyncMode.FROM_SYNC
            else:
                if property_key is not None:
                    raise ValueError(
                        f"Property '{property_key}': Must provide at least getter or setter"
                    )       
        return mode                

    def validate_property_connection(self, mode: SyncMode, setter, getter, signal=None, property_key=None) -> None:        
        key_string = ""
        if property_key is not None:
            key_string = f"Property '{property_key}': "
        # Validate signal requirement
        if mode in (SyncMode.BIDIRECTIONAL, SyncMode.TO_SYNC) and signal is None:
            raise ValueError(f"{key_string}signal is required for {mode.value} mode")

        # Validate getter/setter requirements
        if mode in (SyncMode.BIDIRECTIONAL, SyncMode.TO_SYNC) and getter is None:
                raise ValueError(f"{key_string}getter parameter is required for {mode.value} mode")

        if mode in (SyncMode.BIDIRECTIONAL, SyncMode.FROM_SYNC) and setter is None:
                raise ValueError(f"{key_string}setter parameter is required for {mode.value} mode")


    def is_enabled(self, widget: QWidget | int) -> bool:
        """
        Check if a widget's connections are enabled.

        Returns True only if ALL connections for the widget are enabled.

        Parameters
        ----------
        widget : QWidget | int
            The widget to check, or its ID

        Returns
        -------
        bool
            True if all connections are enabled, False otherwise

        Raises
        ------
        ValueError
            If widget is not connected
        """
        widget_id = widget if isinstance(widget, int) else id(widget)
        connection_keys = self._get_connection_keys_for_widget(widget_id)

        if not connection_keys:
            raise ValueError(f"Widget is not connected to this sync")

        # Return True only if ALL connections are enabled
        return all(
            self._connections.get(key, {}).get('enabled', True)
            for key in connection_keys
        )

    # Widget Binding Methods

    def bind(self, widget: QWidget, signal: Signal | None = None,
             getter: WidgetGetter | None = None, setter: WidgetSetter | None = None,
             mode: SyncMode | None = None,
             to_sync_transform: ValueTransform | None = None,
             from_sync_transform: ValueTransform | None = None) -> None:
        """
        Bind a widget to this sync.

        For ValueSync: Binds the widget to the single value.
        For DictSync: Binds the widget to the entire dict value.

        Parameters
        ----------
        widget : QWidget
            The widget to connect
        signal : Signal, optional
            The signal to listen to (required for TO_SYNC/BIDIRECTIONAL modes)
        getter : callable, optional
            Function to get value from widget: () -> value
            Required for TO_SYNC and BIDIRECTIONAL modes
        setter : callable, optional
            Function to set value on widget: (value) -> None
            Required for FROM_SYNC and BIDIRECTIONAL modes
        mode : SyncMode, optional
            Synchronization mode. If None, auto-inferred from parameters
        to_sync_transform : callable, optional
            Transform value from widget to sync: (widget_value) -> sync_value
        from_sync_transform : callable, optional
            Transform value from sync to widget: (sync_value) -> widget_value

        Raises
        ------
        ValueError
            If neither getter nor setter provided, or if mode requirements not met
        """

        mode = self.check_connection_mode(mode, setter, getter)
        self.validate_property_connection(mode, setter, getter, signal)

        # Get widget references
        widget_id = id(widget)
        widget_ref = ref(widget)
        connection_key = (widget_id, None)

        # Initialize connection info
        connection_info = {
            'widget_id': widget_id,
            'widget_ref': widget_ref,
            'widget_type': type(widget).__name__,
            'signal': signal,
            'getter': getter,
            'setter': setter,
            'mode': mode,
            'to_sync_transform': to_sync_transform,
            'from_sync_transform': from_sync_transform,
            'callbacks': [],
            'enabled': True,
            'property_name': None,
            'signal_name': None,
        }

        # Get property_key for callbacks (subclass-specific)
        property_key_for_callbacks = self._get_bind_property_key()

        # Create widget→sync callback (TO_SYNC or BIDIRECTIONAL)
        if mode in (SyncMode.TO_SYNC, SyncMode.BIDIRECTIONAL):
            callback = self._create_widget_to_sync_callback(
                connection_key=connection_key,
                widget_ref=widget_ref,
                property_key=property_key_for_callbacks,
                getter=getter,
                to_sync_transform=to_sync_transform
            )
            signal.connect(callback)
            connection_info['callbacks'].append(('widget', callback))

        # Create sync→widget callback (FROM_SYNC or BIDIRECTIONAL)
        if mode in (SyncMode.FROM_SYNC, SyncMode.BIDIRECTIONAL):
            callback = self._create_sync_to_widget_callback(
                connection_key=connection_key,
                widget_ref=widget_ref,
                property_key=property_key_for_callbacks,
                setter=setter,
                from_sync_transform=from_sync_transform
            )
            self.value_changed.connect(callback)
            connection_info['callbacks'].append(('sync', callback))

        # Initialize widget with current value (FROM_SYNC or BIDIRECTIONAL)
        if mode in (SyncMode.FROM_SYNC, SyncMode.BIDIRECTIONAL):
            value_to_set = self._get_bind_value()
            if from_sync_transform:
                value_to_set = from_sync_transform(value_to_set)
            with self._block_signals(widget):
                setter(value_to_set)

        # Setup widget destruction callback and store connection
        self._setup_widget_destruction_callback(widget, [connection_key])
        self._set_connection(widget_id, None, connection_info)

    # Callback Creation Methods

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

    def _create_widget_to_sync_callback(
        self,
        connection_key: tuple[int, str | None],
        widget_ref: ReferenceType,
        getter: WidgetGetter,
        to_sync_transform: ValueTransform | None,
        property_key: str | None
    ) -> Callable:
        """Create callback for widget → sync updates."""
        def on_widget_change(*args):
            widget_obj = widget_ref()
            if widget_obj is None:
                return

            conn = self._connections.get(connection_key)
            if conn is None or not conn.get('enabled', True):
                return

            try:
                value = args[0] if args else getter()
                if to_sync_transform:
                    value = to_sync_transform(value)

                # Track this widget as the sender to prevent feedback loop
                # Store only widget_id to block ALL property updates on this widget
                widget_id = connection_key[0]
                self._sender_widget_id = widget_id
                try:
                    # Property connection: update dict key
                    if property_key is not None:
                        # In single-value mode, set_value expects unwrapped value
                        if property_key == "__value__":
                            self.set_value(value, emit=True)
                        # In dict mode, set_value expects the full dict
                        elif isinstance(self._value, dict):
                            new_dict = self._value.copy()
                            new_dict[property_key] = value
                            self.set_value(new_dict, emit=True)
                    # Regular connection: update entire value
                    else:
                        self.set_value(value, emit=True)
                finally:
                    # Always clear sender after update
                    self._sender_widget_id = None
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Error syncing from widget {type(widget_obj).__name__}: {e}",
                    exc_info=True
                )

        return on_widget_change

    def _create_sync_to_widget_callback(
        self,
        connection_key: tuple[int, str | None],
        widget_ref: ReferenceType,
        setter: WidgetSetter,
        from_sync_transform: ValueTransform | None,
        property_key: str | None
    ) -> Callable:
        """Create callback for sync → widget updates."""
        def on_sync_change(value):
            widget_obj = widget_ref()
            if widget_obj is None:
                return

            conn = self._connections.get(connection_key)
            if conn is None or not conn.get('enabled', True):
                return

            # Skip updating the widget that triggered this change (prevent feedback loop)
            # Check widget_id only, so ALL properties on the sender widget are skipped
            widget_id = connection_key[0]
            if self._sender_widget_id == widget_id:
                return

            try:
                # Property connection: extract dict key
                if property_key is not None:
                    # In single-value mode, property_key is "__value__" and value is already unwrapped
                    if property_key == "__value__":
                        # Value is already unwrapped, use it directly
                        # Check if it actually changed
                        if self._previous_value and isinstance(self._previous_value, dict):
                            old_prop_value = self._previous_value.get("__value__")
                            if old_prop_value == value:
                                return  # Value didn't change, skip update
                    # In dict mode, extract the specific property from the dict
                    elif isinstance(value, dict) and property_key in value:
                        new_prop_value = value[property_key]

                        # Optimization: Only update if this specific property changed
                        # Compare old and new dict values for this property
                        if self._previous_value and isinstance(self._previous_value, dict):
                            old_prop_value = self._previous_value.get(property_key)
                            if old_prop_value == new_prop_value:
                                return  # Property didn't change, skip update

                        value = new_prop_value
                    else:
                        return

                if from_sync_transform:
                    value = from_sync_transform(value)
                with self._block_signals(widget_obj):
                    setter(value)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Error updating widget {type(widget_obj).__name__}: {e}",
                    exc_info=True
                )

        return on_sync_change

    # Properties

    @property
    def connected_widgets(self) -> list[QWidget]:
        """
        Get list of currently connected widgets.

        Returns only widgets that haven't been deleted.
        Includes both regular connections and property connections.

        Returns
        -------
        list[QWidget]
            List of active widget references (unique widgets)

        Example
        -------
        >>> sync = WidgetSync.for_checkbox(cb1)
        >>> sync.add(cb2)
        >>> sync.add(cb3)
        >>> len(sync.connected_widgets)  # Returns 3
        3
        """
        widgets = []
        widget_ids = set()

        # Iterate through unified connections dictionary
        for conn in self._connections.values():
            widget = conn['widget_ref']()
            if widget is not None and id(widget) not in widget_ids:
                widgets.append(widget)
                widget_ids.add(id(widget))

        return widgets

    @property
    def connection_count(self) -> int:
        """
        Get count of active connections.

        Includes both regular connections and property connections.

        Returns
        -------
        int
            Number of currently connected widgets/properties

        Example
        -------
        >>> sync = WidgetSync.for_spinbox(spin1)
        >>> sync.add(spin2)
        >>> sync.connection_count  # Returns 2
        2
        """
        return len(self._connections)

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


class ValueSync(BaseWidgetSync):
    """
    Synchronize a single value across multiple widgets.

    Supports any data type (int, str, bool, float, custom objects).
    Use bind() to connect widgets.
    """

    def __init__(self, initial_value: Any = None, data_type: Type | DataType | None = None,
                 validator: Callable[[Any], Any] | None = None) -> None:
        """
        Initialize value sync with a single value.

        Parameters
        ----------
        initial_value : Any
            Initial value for the sync (must not be a dict)
        data_type : Type | DataType, optional
            Expected data type. If None, inferred from initial_value.
        validator : callable, optional
            Optional validator function: (value) -> value
        """
        super().__init__()

        # Reject dict values
        if isinstance(initial_value, dict):
            raise TypeError(
                "ValueSync does not accept dict values. Use DictSync instead."
            )

        self._validator = validator
        self._data_type = self._resolve_type(initial_value, data_type)

        # Validate and wrap the initial value
        validated_value = self._validate_value(initial_value)
        self._value = {"__value__": validated_value}
        self._previous_value = self._value.copy()

    @property
    def value(self) -> Any:
        """Get current synced value."""
        return self._value.get("__value__")

    @value.setter
    def value(self, new_value: Any) -> None:
        """Set value and emit change signal."""
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
        # Apply validator first (if provided)
        validated_value = new_value
        if self._validator is not None:
            try:
                validated_value = self._validator(new_value)
            except Exception as e:
                # Log error and keep current value
                import logging
                logging.getLogger(__name__).error(
                    f"Validator raised exception: {e}. Keeping current value.",
                    exc_info=True
                )
                return

        # Validate type
        validated_value = self._validate_value(validated_value)

        # Wrap in dict
        new_dict_value = {"__value__": validated_value}

        if self._value != new_dict_value:
            # Store previous value for property change detection
            self._previous_value = self._value.copy()
            self._value = new_dict_value
            if emit:
                # Emit unwrapped value for user-facing signal handlers
                self.value_changed.emit(validated_value)

    def _get_bind_property_key(self) -> str:
        """Return '__value__' for ValueSync bind() callbacks."""
        return "__value__"

    def _get_bind_value(self) -> Any:
        """Return unwrapped value for ValueSync bind() initialization."""
        return self._value.get("__value__")

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
            - 'type': Match exact widget type (safest)
            - 'property': Match by property/signal names
        to_sync_transform : callable, optional
            Transform value from widget to sync
        from_sync_transform : callable, optional
            Transform value from sync to widget

        Raises
        ------
        TypeError
            If no connection pattern found
        ValueError
            If match parameter has invalid value
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
                    if hasattr(widget, signal_name):
                        break
                    else:
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
                f"  - Use bind() directly:\n\n"
                f"    sync.bind(\n"
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
                f"Cannot use add() to bind {widget_type}: "
                f"it doesn't have the '{signal_name}' signal.\n\n"
                f"💡 Solution: Use bind() instead"
            )

        # Get signal and create getter/setter using weak reference
        signal = getattr(widget, signal_name)
        prop_name = property_name
        widget_ref = ref(widget)

        def getter():
            w = widget_ref()
            return w.property(prop_name) if w is not None else None

        def setter(value):
            w = widget_ref()
            if w is not None:
                w.setProperty(prop_name, value)

        # Bind the widget
        self.bind(widget, signal, getter, setter, mode,
                  to_sync_transform, from_sync_transform)

    # Helper Methods

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


class DictSync(BaseWidgetSync):
    """
    Synchronize dict values with multiple properties or widgets.

    DictSync provides three binding methods:

    1. **bind()** - Bind widgets that work with the entire dict
       (e.g., JSON editor, config display)

    2. **bind_properties()** - Bind multiple properties of ONE widget to dict keys
       (e.g., ComboBox with both 'items' and 'selection' properties)

    3. **bind_dict()** - Bind DIFFERENT widgets to different dict keys
       (e.g., separate R/G/B sliders for a color dict)

    Examples
    --------
    >>> # Bind multiple properties of one widget
    >>> sync = DictSync({'items': ['A', 'B'], 'current': 'A'})
    >>> sync.bind_properties(combobox, property_map={
    ...     'items': {'setter': lambda v: (combo.clear(), combo.addItems(v))},
    ...     'current': {'property': 'currentText'}
    ... })
    >>>
    >>> # Bind different widgets to dict keys
    >>> color_sync = DictSync({'r': 128, 'g': 64, 'b': 192})
    >>> color_sync.bind_dict(property_map={
    ...     'r': {'widget': r_slider, 'property': 'value'},
    ...     'g': {'widget': g_slider, 'property': 'value'},
    ...     'b': {'widget': b_slider, 'property': 'value'}
    ... })
    """

    def __init__(self, initial_value: dict | None = None,
                 validator: Callable[[Any], Any] | None = None) -> None:
        """
        Initialize dict sync with a dictionary value.

        Parameters
        ----------
        initial_value : dict, optional
            Initial dict value for the sync (must be a dict)
        validator : callable, optional
            Optional validator function: (value) -> value
        """
        super().__init__()

        # Require dict value
        if initial_value is not None and not isinstance(initial_value, dict):
            raise TypeError(
                f"DictSync requires a dict value, got {type(initial_value).__name__}. "
                f"Use ValueSync for single values."
            )

        self._validator = validator
        self._data_type = dict
        self._value = initial_value.copy() if initial_value else {}
        self._previous_value = self._value.copy()

    @property
    def value(self) -> dict:
        """Get current synced dict value."""
        return self._value

    @value.setter
    def value(self, new_value: dict) -> None:
        """Set dict value and emit change signal."""
        self.set_value(new_value, emit=True)

    def set_value(self, new_value: dict, emit: bool = True) -> None:
        """
        Set dict value with optional emission control.

        Parameters
        ----------
        new_value : dict
            The new dict value to set
        emit : bool, optional
            Whether to emit value_changed signal (default: True)

        Raises
        ------
        TypeError
            If new_value is not a dict
        """
        if not isinstance(new_value, dict):
            raise TypeError(
                f"Sync is in dict mode and requires dict values, but got {type(new_value).__name__}"
            )

        # Apply validator if provided
        validated_value = new_value
        if self._validator is not None:
            try:
                validated_value = self._validator(new_value)
            except Exception as e:
                # Log error and keep current value
                import logging
                logging.getLogger(__name__).error(
                    f"Validator raised exception: {e}. Keeping current value.",
                    exc_info=True
                )
                return

        if self._value != validated_value:
            # Store previous value for property change detection
            self._previous_value = self._value.copy()
            self._value = validated_value.copy()
            if emit:
                self.value_changed.emit(self._value)

    def _get_bind_property_key(self) -> None:
        """Return None for DictSync bind() callbacks (entire dict)."""
        return None

    def _get_bind_value(self) -> dict:
        """Return full dict for DictSync bind() initialization."""
        return self._value

    def _setup_property_binding(self, widget: QWidget, widget_ref: ReferenceType,
                                property_key: str, config: dict[str, Any]) -> dict:
        """
        Helper to setup a single property binding (factorizes bind_properties/bind_dict logic).

        Returns connection_info dict ready to be stored.
        """
        widget_id = id(widget)
        signal = config.get('signal')
        getter = config.get('getter')
        setter = config.get('setter')
        mode = config.get('mode')
        property_name = config.get('property')

        # AUTO-GENERATION: If 'property' key is provided, auto-generate getter/setter
        if property_name is not None:
            prop_name = property_name

            # Auto-generate getter with weak reference
            if getter is None:
                def make_property_getter(prop=prop_name, wref=widget_ref):
                    w = wref()
                    return w.property(prop) if w is not None else None
                getter = make_property_getter

            # Auto-generate setter with weak reference
            if setter is None:
                def make_property_setter(value, prop=prop_name, wref=widget_ref):
                    w = wref()
                    if w is not None:
                        w.setProperty(prop, value)
                setter = make_property_setter

            # Auto-detect signal from Qt property system
            if signal is None and mode in (SyncMode.BIDIRECTIONAL, SyncMode.TO_SYNC, None):
                try:
                    meta = widget.metaObject()
                    prop_index = meta.indexOfProperty(prop_name)
                    if prop_index != -1:
                        prop = meta.property(prop_index)
                        notify_signal = prop.notifySignal()
                        if notify_signal.isValid():
                            signal_name = notify_signal.name().data().decode()
                            signal = getattr(widget, signal_name, None)
                except Exception:
                    pass

        mode = self.check_connection_mode(mode, setter, getter, property_key)
        self.validate_property_connection(mode, setter, getter, signal, property_key)

        # Create connection info
        connection_key = (widget_id, property_key)
        connection_info = {
            'widget_id': widget_id,
            'widget_ref': widget_ref,
            'widget_type': type(widget).__name__,
            'property_key': property_key,
            'signal': signal,
            'getter': getter,
            'setter': setter,
            'mode': mode,
            'callbacks': [],
            'enabled': True
        }

        # Create and connect callbacks
        if mode in (SyncMode.BIDIRECTIONAL, SyncMode.TO_SYNC):
            callback = self._create_widget_to_sync_callback(
                connection_key, widget_ref, getter, None, property_key
            )
            signal.connect(callback)
            connection_info['callbacks'].append(('widget', callback))

        if mode in (SyncMode.BIDIRECTIONAL, SyncMode.FROM_SYNC):
            callback = self._create_sync_to_widget_callback(
                connection_key, widget_ref, setter, None, property_key
            )
            self.value_changed.connect(callback)
            connection_info['callbacks'].append(('sync', callback))

        # Initialize widget with current value
        if mode in (SyncMode.BIDIRECTIONAL, SyncMode.FROM_SYNC):
            if property_key in self._value:
                try:
                    with self._block_signals(widget):
                        setter(self._value[property_key])
                except Exception as e:
                    raise RuntimeError(
                        f"Error initializing property '{property_key}' on widget {type(widget).__name__}: {e}"
                    ) from e

        return connection_info

    def bind_properties(self, widget: QWidget,
                       property_map: dict[str, dict[str, Any]]) -> None:
        """
        Bind multiple properties of ONE widget to different dict keys.

        **IMPORTANT**: This method is designed for synchronizing multiple properties
        of a SINGLE widget. All properties control the same widget passed as the first
        parameter.

        Parameters
        ----------
        widget : QWidget
            The widget to bind (all properties control THIS widget)
        property_map : dict[str, dict]
            Mapping of dict keys to property configurations.
            Each key maps to a dict with EITHER:

            **Simple syntax (recommended for Qt properties):**
            - 'property': str - Qt property name (auto-generates getter/setter)
            - 'signal': Signal | str (optional, auto-detected if omitted)
            - 'mode': SyncMode (optional, default: BIDIRECTIONAL)

            **Advanced syntax (for custom logic):**
            - 'signal': Signal | None (required for TO_SYNC/BIDIRECTIONAL)
            - 'getter': callable () -> value (required for TO_SYNC/BIDIRECTIONAL)
            - 'setter': callable (value) -> None (required for FROM_SYNC/BIDIRECTIONAL)
            - 'mode': SyncMode (optional, default: inferred from getter/setter)

        Raises
        ------
        TypeError
            If sync value is not a dict
        ValueError
            If property configuration is invalid
        """
        widget_ref = ref(widget)
        widget_id = id(widget)

        # Collect all connection keys for destruction callback
        all_connection_keys = [(widget_id, prop_key) for prop_key in property_map.keys()]

        # Bind each property using factorized helper
        for property_key, config in property_map.items():
            connection_info = self._setup_property_binding(widget, widget_ref, property_key, config)
            self._set_connection(widget_id, property_key, connection_info)

        # Setup widget destruction callback once for all properties
        self._setup_widget_destruction_callback(widget, all_connection_keys)

    def bind_dict(self, property_map: dict[str, dict[str, Any]]) -> None:
        """
        Bind different widgets to different dict keys.

        Each property in the dict value is controlled by its own widget.

        **Key Difference from bind_properties():**
        - `bind_properties()`: Multiple properties of ONE widget → dict keys
        - `bind_dict()`: Multiple different widgets → dict keys (one widget per key)

        Parameters
        ----------
        property_map : dict[str, dict]
            Mapping of dict keys to widget configurations.
            Each key maps to a dict that MUST include:

            **Required:**
            - 'widget': QWidget - The widget for this property

            **Simple syntax (recommended for Qt properties):**
            - 'property': str - Qt property name (auto-generates getter/setter)
            - 'signal': Signal | str (optional, auto-detected if omitted)
            - 'mode': SyncMode (optional, default: BIDIRECTIONAL)

            **Advanced syntax (for custom logic):**
            - 'signal': Signal | None (required for TO_SYNC/BIDIRECTIONAL)
            - 'getter': callable () -> value (required for TO_SYNC/BIDIRECTIONAL)
            - 'setter': callable (value) -> None (required for FROM_SYNC/BIDIRECTIONAL)
            - 'mode': SyncMode (optional, default: inferred from getter/setter)

        Raises
        ------
        TypeError
            If sync value is not a dict
        ValueError
            If property configuration is invalid or missing 'widget' key
        """
        # Track all widgets for cleanup
        widgets_to_setup = {}  # widget_id -> list of connection keys

        # Bind each property
        for property_key, config in property_map.items():
            # Get the widget for this property (REQUIRED)
            widget = config.get('widget')
            if widget is None:
                raise ValueError(
                    f"Property '{property_key}': 'widget' key is required in bind_dict(). "
                    f"Each property must specify which widget it controls."
                )

            widget_id = id(widget)
            widget_ref = ref(widget)

            # Use factorized helper to setup property binding
            connection_info = self._setup_property_binding(widget, widget_ref, property_key, config)
            self._set_connection(widget_id, property_key, connection_info)

            # Track for destruction callback setup
            if widget_id not in widgets_to_setup:
                widgets_to_setup[widget_id] = []
            widgets_to_setup[widget_id].append((widget_id, property_key))

        # Setup widget destruction callbacks (one per unique widget)
        for widget_id, connection_keys in widgets_to_setup.items():
            # Get any widget reference from the connections
            first_key = connection_keys[0]
            widget_ref = self._connections[first_key]['widget_ref']
            widget = widget_ref()
            if widget is not None:
                self._setup_widget_destruction_callback(widget, connection_keys)

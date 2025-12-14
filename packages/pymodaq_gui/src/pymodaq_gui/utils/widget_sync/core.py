"""
Core widget synchronization classes and enums.

Implementation for syncing widget properties across multiple widgets.

"""
from __future__ import annotations

from qtpy.QtCore import QObject, Signal
from qtpy.QtWidgets import QWidget
from enum import Enum
from typing import Callable, Any, Iterator, Type, Literal
from contextlib import contextmanager
from weakref import ref, ReferenceType
from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))

ValueTransform = Callable[[Any], Any]
WidgetGetter = Callable[[], Any]
WidgetSetter = Callable[[Any], None]
ConnectionInfo = dict[str, Any]  # Connection metadata dictionary
InitFrom = Literal['sync', 'widget', None]  # Initialization source control


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

    def _get_internal_storage_key(self) -> str | None:
        """
        Get the internal dict key used for value storage.

        This is an implementation detail for routing callbacks between ValueSync and DictSync.
        The base class uses dict storage internally for both sync types:
        - ValueSync: Returns "__value__" (single value wrapped in dict: {"__value__": 42})
        - DictSync: Returns None (multi-key dict: {"r": 255, "g": 128, "b": 64})

        This allows unified callback routing in the base class.

        Note
        ----
        Internal method. Most users should not need to subclass BaseWidgetSync.
        Use ValueSync or DictSync directly instead.

        Returns
        -------
        str or None
            "__value__" for ValueSync, None for DictSync
        """
        raise NotImplementedError("Subclasses must implement _get_internal_storage_key()")

    def _get_user_facing_value(self) -> Any:
        """
        Get the value in user-facing format for widget initialization.

        This handles internal representation differences between ValueSync and DictSync:
        - ValueSync: Unwraps {"__value__": 42} → 42 (removes internal wrapper)
        - DictSync: Returns dict directly {"r": 255, "g": 128} → {"r": 255, "g": 128}

        Used by bind() and initialization logic to present the correct value format
        to widgets.

        Note
        ----
        Internal method for BaseWidgetSync infrastructure. Not intended for external use.

        Returns
        -------
        Any
            Unwrapped value for ValueSync, full dict for DictSync
        """
        raise NotImplementedError("Subclasses must implement _get_user_facing_value()")

    # Helper Methods

    def _apply_validator(self, value: Any) -> Any:
        """
        Apply validator if present, with error handling.

        Parameters
        ----------
        value : Any
            Value to validate

        Returns
        -------
        Any
            Validated value

        Raises
        ------
        ValueError
            If validation fails (logs error before raising)

        Notes
        -----
        If validation fails, logs error and raises ValueError
        to signal that the calling method should abort the value update.
        """
        if self._validator is None:
            return value

        try:
            return self._validator(value)
        except Exception as e:
            logger.error(
                f"Validator raised exception: {e}. Keeping current value.",
                exc_info=True
            )
            raise ValueError(f"Validation failed: {e}") from e

    def _make_property_getter(self, widget_ref: ReferenceType, property_name: str) -> WidgetGetter:
        """
        Create a getter function for a Qt property with weak reference.

        Parameters
        ----------
        widget_ref : ReferenceType
            Weak reference to the widget
        property_name : str
            Qt property name

        Returns
        -------
        WidgetGetter
            Getter function that safely accesses the property
        """
        def getter():
            w = widget_ref()
            return w.property(property_name) if w is not None else None
        return getter

    def _make_property_setter(self, widget_ref: ReferenceType, property_name: str) -> WidgetSetter:
        """
        Create a setter function for a Qt property with weak reference.

        Parameters
        ----------
        widget_ref : ReferenceType
            Weak reference to the widget
        property_name : str
            Qt property name

        Returns
        -------
        WidgetSetter
            Setter function that safely sets the property
        """
        def setter(value):
            w = widget_ref()
            if w is not None:
                w.setProperty(property_name, value)
        return setter

    def _create_connection_info(
        self,
        widget: QWidget,
        widget_ref: ReferenceType,
        signal: Signal | None = None,
        getter: WidgetGetter | None = None,
        setter: WidgetSetter | None = None,
        mode: SyncMode | None = None,
        to_sync_transform: ValueTransform | None = None,
        from_sync_transform: ValueTransform | None = None,
        property_key: str | None = None,
        property_name: str | None = None,
        signal_name: str | None = None
    ) -> ConnectionInfo:
        """
        Create a standardized connection_info dictionary.

        Ensures all connection_info dicts have the same structure across
        bind(), bind_properties(), and bind_dict().

        Parameters
        ----------
        widget : QWidget
            The widget being connected
        widget_ref : ReferenceType
            Weak reference to the widget
        signal : Signal, optional
            Qt signal for widget→sync updates
        getter : WidgetGetter, optional
            Function to get value from widget
        setter : WidgetSetter, optional
            Function to set value on widget
        mode : SyncMode, optional
            Synchronization mode
        to_sync_transform : ValueTransform, optional
            Transform function widget→sync
        from_sync_transform : ValueTransform, optional
            Transform function sync→widget
        property_key : str, optional
            Dict key for property bindings (e.g., 'r', 'g', 'b')
            None for regular bind()
        property_name : str, optional
            Qt property name (e.g., 'value', 'text', 'checked')
            Used for introspection in add()
        signal_name : str, optional
            Qt signal name (e.g., 'valueChanged', 'textChanged')
            Used for introspection in add()

        Returns
        -------
        ConnectionInfo
            Standardized connection info dictionary with all fields
        """
        return {
            'widget_id': id(widget),
            'widget_ref': widget_ref,
            'widget_type': type(widget).__name__,
            'signal': signal,
            'getter': getter,
            'setter': setter,
            'mode': mode,
            'to_sync_transform': to_sync_transform,
            'from_sync_transform': from_sync_transform,
            'property_key': property_key,
            'property_name': property_name,
            'signal_name': signal_name,
            'callbacks': [],
            'enabled': True,
        }

    # Connection Management Methods

    def _get_connection(self, widget_id: int, property_key: str | None = None) -> ConnectionInfo | None:
        """Get connection by composite key."""
        return self._connections.get((widget_id, property_key))

    def _set_connection(self, widget_id: int, property_key: str | None, connection_info: ConnectionInfo) -> None:
        """Set connection with composite key."""
        connection_info['property_key'] = property_key
        self._connections[(widget_id, property_key)] = connection_info

    def _remove_connection(self, widget_id: int, property_key: str | None = None,
                          is_destruction: bool = False) -> None:
        """
        Remove connection and disconnect callbacks.

        Parameters
        ----------
        widget_id : int
            Widget ID
        property_key : str | None
            Property key
        is_destruction : bool
            True if called during widget destruction (skip parameter signal disconnection)
        """
        key = (widget_id, property_key)
        if conn := self._connections.get(key):
            param_callbacks = conn.get('param_callbacks') if not is_destruction else None
            self._disconnect_callbacks(conn['callbacks'], param_callbacks)
            del self._connections[key]

    def _get_connection_keys_for_widget(self, widget_id: int) -> list[tuple[int, str | None]]:
        """Get all connection keys for a widget."""
        return [k for k in self._connections if k[0] == widget_id]

    def _disconnect_callbacks(self, callbacks: list, param_callbacks: dict = None) -> None:
        """
        Disconnect sync callbacks from value_changed signal.

        Qt auto-cleans widget callbacks, so we only disconnect sync callbacks.

        Parameters
        ----------
        callbacks : list
            List of callback tuples (callback_type, callback)
        param_callbacks : dict, optional
            Dict of parameter-specific callbacks to disconnect (for bind_parameter)
        """
        for callback_type, callback in callbacks:
            if callback_type == 'sync':
                try:
                    self.value_changed.disconnect(callback)
                except (TypeError, RuntimeError):
                    pass  # Already disconnected

        # Disconnect parameter signal callbacks (only if param_callbacks is provided)
        # Note: param_callbacks is None during widget destruction to avoid Qt warnings
        # when the Parameter is being destroyed. Qt automatically disconnects signals
        # during object destruction, so explicit disconnection is not needed and can
        # cause warnings.
        if param_callbacks:
            for key, value in list(param_callbacks.items()):
                if key[1] == 'param_to_sync':
                    # value is (signal, callback)
                    signal, callback = value
                    try:
                        signal.disconnect(callback)
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
                    # Pass is_destruction=True to skip parameter signal disconnection
                    sync._remove_connection(key[0], key[1], is_destruction=True)

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

    def _validate_init_from(
        self,
        init_from: InitFrom,
        mode: SyncMode,
        getter: WidgetGetter | None,
        setter: WidgetSetter | None,
        property_key: str | None = None
    ) -> None:
        """
        Validate init_from parameter compatibility with mode and getter/setter.

        Parameters
        ----------
        init_from : InitFrom
            Initialization source ('sync', 'widget', or None)
        mode : SyncMode
            Synchronization mode
        getter : WidgetGetter, optional
            Widget value getter function
        setter : WidgetSetter, optional
            Widget value setter function
        property_key : str, optional
            Property key for error messages (dict sync only)

        Raises
        ------
        ValueError
            If init_from is incompatible with mode or missing required getter/setter
        """
        key_string = f"Property '{property_key}': " if property_key else ""

        if init_from == 'widget':
            if mode not in (SyncMode.TO_SYNC, SyncMode.BIDIRECTIONAL):
                raise ValueError(
                    f"{key_string}init_from='widget' requires mode with TO_SYNC capability "
                    f"(TO_SYNC or BIDIRECTIONAL), but got {mode.value}"
                )
            if getter is None:
                raise ValueError(
                    f"{key_string}init_from='widget' requires getter to read widget's value"
                )

        if init_from == 'sync':
            if mode in (SyncMode.FROM_SYNC, SyncMode.BIDIRECTIONAL) and setter is None:
                raise ValueError(
                    f"{key_string}init_from='sync' with {mode.value} mode requires setter"
                )

    def _handle_initialization(
        self,
        init_from: InitFrom,
        mode: SyncMode,
        widget: QWidget,
        getter: WidgetGetter | None,
        setter: WidgetSetter | None,
        property_key: str | None,
        to_sync_transform: ValueTransform | None,
        from_sync_transform: ValueTransform | None
    ) -> None:
        """
        Handle widget initialization based on init_from parameter.

        Centralized logic used by bind(), bind_properties(), and bind_dict()
        to provide consistent initialization behavior across all three code paths.

        Parameters
        ----------
        init_from : InitFrom
            Initialization source: 'sync' (widget←sync), 'widget' (sync←widget), or None (no init)
        mode : SyncMode
            Synchronization mode
        widget : QWidget
            Widget being initialized
        getter : WidgetGetter, optional
            Function to get value from widget
        setter : WidgetSetter, optional
            Function to set value on widget
        property_key : str, optional
            Property key for dict sync (None for regular bind())
        to_sync_transform : ValueTransform, optional
            Transform widget→sync
        from_sync_transform : ValueTransform, optional
            Transform sync→widget
        """
        if init_from is None:
            return  # No initialization

        if init_from == 'sync':
            # Initialize widget with sync's value
            if mode not in (SyncMode.FROM_SYNC, SyncMode.BIDIRECTIONAL):
                return  # Mode doesn't support sync→widget
            if setter is None:
                return

            # Get value to set
            if property_key is not None:
                if property_key == "__value__":
                    # ValueSync: use unwrapped value
                    value_to_set = self._get_user_facing_value()
                else:
                    # DictSync: extract from dict
                    if property_key not in self._value:
                        return  # Property doesn't exist yet
                    value_to_set = self._value[property_key]
            else:
                # Regular bind(): use full value
                value_to_set = self._get_user_facing_value()

            # Apply transform
            if from_sync_transform:
                value_to_set = from_sync_transform(value_to_set)

            # Set on widget with signals blocked
            try:
                with self._block_signals(widget):
                    setter(value_to_set)
            except Exception as e:
                logger.error(
                    f"Error initializing widget {type(widget).__name__} from sync: {e}",
                    exc_info=True
                )

        elif init_from == 'widget':
            # Initialize sync with widget's value
            if getter is None:
                raise ValueError("init_from='widget' requires getter")

            # Get value from widget
            try:
                widget_value = getter()
            except Exception as e:
                logger.error(
                    f"Error reading initial value from widget {type(widget).__name__}: {e}",
                    exc_info=True
                )
                return

            # Apply transform
            if to_sync_transform:
                widget_value = to_sync_transform(widget_value)

            # Update sync value
            widget_id = id(widget)
            self._sender_widget_id = widget_id
            try:
                if property_key is not None:
                    if property_key == "__value__":
                        # ValueSync: set unwrapped value
                        self.set_value(widget_value, emit=True)
                    elif isinstance(self._value, dict):
                        # DictSync: update dict key
                        new_dict = self._value.copy()
                        new_dict[property_key] = widget_value
                        self.set_value(new_dict, emit=True)
                else:
                    # Regular bind(): set full value
                    self.set_value(widget_value, emit=True)
            finally:
                # Always clear sender
                self._sender_widget_id = None

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
             from_sync_transform: ValueTransform | None = None,
             init_from: InitFrom = 'sync') -> None:
        """
        Bind a widget to this sync.

        For ValueSync: Binds the widget to the single value.
        For DictSync: Binds the widget to the entire dict value.

        **IMPORTANT:** When binding with FROM_SYNC or BIDIRECTIONAL mode, the widget
        is immediately initialized with the current sync value. This is different
        from enable(), which does NOT update the widget value. One can disable this behavior by using
        the init_from parameter.

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
        init_from : InitFrom, optional
            Initialization source: 'sync' (default - widget gets sync's value),
            'widget' (sync gets widget's value), or None (no initialization).
            When 'widget' is used with BIDIRECTIONAL mode, all other connected
            widgets also receive the widget's value.

        Raises
        ------
        ValueError
            If neither getter nor setter provided, or if mode requirements not met

        Example
        -------
        >>> sync = WidgetSync(initial_value=100)
        >>> sync.bind(slider, signal=slider.valueChanged,
        ...           getter=slider.value, setter=slider.setValue)
        >>> slider.value()  # Returns 100 - widget was initialized!
        """

        mode = self.check_connection_mode(mode, setter, getter)
        self.validate_property_connection(mode, setter, getter, signal)

        # Validate init_from parameter
        self._validate_init_from(init_from, mode, getter, setter)

        # Get widget references
        widget_id = id(widget)
        widget_ref = ref(widget)
        connection_key = (widget_id, None)

        # Create standardized connection info
        connection_info = self._create_connection_info(
            widget=widget,
            widget_ref=widget_ref,
            signal=signal,
            getter=getter,
            setter=setter,
            mode=mode,
            to_sync_transform=to_sync_transform,
            from_sync_transform=from_sync_transform,
            property_key=None,  # Regular bind() doesn't use property_key
            property_name=None,
            signal_name=None,
        )

        # Get property_key for callbacks (subclass-specific)
        property_key_for_callbacks = self._get_internal_storage_key()

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

        # Handle initialization based on init_from parameter
        self._handle_initialization(
            init_from=init_from,
            mode=mode,
            widget=widget,
            getter=getter,
            setter=setter,
            property_key=None,  # Regular bind() doesn't use property_key
            to_sync_transform=to_sync_transform,
            from_sync_transform=from_sync_transform
        )

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
                logger.error(
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
                logger.error(
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
        try:
            validated_value = self._apply_validator(new_value)
        except ValueError:
            # Validation failed (already logged), abort
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

    def _get_internal_storage_key(self) -> str:
        """Return '__value__' for ValueSync bind() callbacks."""
        return "__value__"

    def _get_user_facing_value(self) -> Any:
        """Return unwrapped value for ValueSync bind() initialization."""
        return self._value.get("__value__")

    def add(self, widget: QWidget, mode: SyncMode = SyncMode.BIDIRECTIONAL,
            match: str = 'type',
            to_sync_transform: ValueTransform | None = None,
            from_sync_transform: ValueTransform | None = None,
            init_from: InitFrom = 'sync') -> None:
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
        init_from : InitFrom, optional
            Initialization source: 'sync' (default), 'widget', or None.
            See bind() for details.

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
        widget_ref = ref(widget)

        # Use helper methods to create getter/setter
        getter = self._make_property_getter(widget_ref, property_name)
        setter = self._make_property_setter(widget_ref, property_name)

        # Bind the widget
        self.bind(widget, signal, getter, setter, mode,
                  to_sync_transform, from_sync_transform, init_from)

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
        validated_value = self._apply_validator(new_value)

        if self._value != validated_value:
            # Store previous value for property change detection
            self._previous_value = self._value.copy()
            self._value = validated_value.copy()
            if emit:
                self.value_changed.emit(self._value)

    def _get_internal_storage_key(self) -> None:
        """Return None for DictSync bind() callbacks (entire dict)."""
        return None

    def _get_user_facing_value(self) -> dict:
        """Return full dict for DictSync bind() initialization."""
        return self._value

    def _setup_property_binding(self, widget: QWidget, widget_ref: ReferenceType,
                                property_key: str, config: dict[str, Any],
                                global_init_from: InitFrom = 'sync') -> dict:
        """
        Configure and connect a single property binding.

        Shared setup logic used by both bind_properties() and bind_dict() to provide
        consistent behavior for property-based connections.

        Returns connection_info dict ready to be stored.
        """
        widget_id = id(widget)
        signal = config.get('signal')
        getter = config.get('getter')
        setter = config.get('setter')
        mode = config.get('mode')
        property_name = config.get('property')

        # Extract init_from (per-property override or global default)
        init_from = config.get('init_from', global_init_from)

        # AUTO-GENERATION: If 'property' key is provided, auto-generate getter/setter
        if property_name is not None:
            # Use helper methods to create getter/setter
            if getter is None:
                getter = self._make_property_getter(widget_ref, property_name)

            if setter is None:
                setter = self._make_property_setter(widget_ref, property_name)

            # Auto-detect signal from Qt property system
            if signal is None and mode in (SyncMode.BIDIRECTIONAL, SyncMode.TO_SYNC, None):
                try:
                    meta = widget.metaObject()
                    prop_index = meta.indexOfProperty(property_name)
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

        # Validate init_from
        self._validate_init_from(init_from, mode, getter, setter, property_key)

        # Create standardized connection info
        connection_key = (widget_id, property_key)
        connection_info = self._create_connection_info(
            widget=widget,
            widget_ref=widget_ref,
            signal=signal,
            getter=getter,
            setter=setter,
            mode=mode,
            to_sync_transform=None,  # Property bindings don't support transforms
            from_sync_transform=None,
            property_key=property_key,  # Dict key (e.g., 'r', 'g', 'b')
            property_name=property_name,  # Qt property name if auto-generated
            signal_name=None,  # Could be added if we extract it
        )

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

        # Handle initialization
        self._handle_initialization(
            init_from=init_from,
            mode=mode,
            widget=widget,
            getter=getter,
            setter=setter,
            property_key=property_key,
            to_sync_transform=None,  # Property bindings don't support transforms
            from_sync_transform=None
        )

        return connection_info

    def bind_properties(self, widget: QWidget,
                       property_map: dict[str, dict[str, Any]],
                       init_from: InitFrom = 'sync') -> None:
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
            - 'init_from': InitFrom (optional, overrides global init_from for this property)

            **Advanced syntax (for custom logic):**
            - 'signal': Signal | None (required for TO_SYNC/BIDIRECTIONAL)
            - 'getter': callable () -> value (required for TO_SYNC/BIDIRECTIONAL)
            - 'setter': callable (value) -> None (required for FROM_SYNC/BIDIRECTIONAL)
            - 'mode': SyncMode (optional, default: inferred from getter/setter)
            - 'init_from': InitFrom (optional, overrides global init_from for this property)
        init_from : InitFrom, optional
            Global default for initialization source. Can be overridden per-property
            by including 'init_from' in the property config dict.

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

        # Configure and connect each property
        for property_key, config in property_map.items():
            connection_info = self._setup_property_binding(
                widget, widget_ref, property_key, config, init_from
            )
            self._set_connection(widget_id, property_key, connection_info)

        # Setup widget destruction callback once for all properties
        self._setup_widget_destruction_callback(widget, all_connection_keys)

    def bind_parameter(self, parameter, property_map: dict[str, dict[str, Any]],
                      init_from: InitFrom = 'sync') -> None:
        """
        Bind multiple properties of a Parameter to different dict keys.

        **IMPORTANT**: Use this method instead of bind_properties() for pyqtgraph
        Parameters. bind_properties() uses blockSignals() which prevents parameter
        tree widgets from updating. This method uses callback disconnection instead.

        Parameters
        ----------
        parameter : Parameter
            The pyqtgraph Parameter to bind
        property_map : dict[str, dict]
            Mapping of dict keys to parameter property configurations.
            Each key maps to a dict with:

            **Shortcut for parameter value** (most common case):
            - 'param': Parameter - Automatically uses sigValueChanged, value(), setValue()
              This is equivalent to specifying signal/getter/setter manually

            **OR Manual specification**:
            - 'getter': callable () -> value - Function to get parameter value
            - 'setter': callable (value) -> None - Function to set parameter value
            - 'signal': Signal (optional) - Parameter signal for bidirectional sync
              (Note: Parameter signals emit (param, value), this is handled automatically)
            - 'mode': SyncMode (optional) - BIDIRECTIONAL, TO_SYNC, or FROM_SYNC
              (default: BIDIRECTIONAL if signal provided, else FROM_SYNC)

        init_from : InitFrom, optional
            Initialization source: 'sync' (default), 'widget', or 'none'

        Raises
        ------
        TypeError
            If sync value is not a dict
        ValueError
            If property configuration is invalid

        Examples
        --------
        >>> # Shortcut syntax (recommended for simple value sync)
        >>> sync = WidgetSync(initial_value={'threshold': 0.5})
        >>> sync.bind_parameter(
        ...     threshold_param,
        ...     property_map={'threshold': {'param': threshold_param}}
        ... )

        >>> # Manual syntax (for custom getter/setter or limits)
        >>> algo_sync = WidgetSync(initial_value={'algorithms': [...], 'algorithm': 'FFT'})
        >>> algo_sync.bind_parameter(
        ...     algorithm_param,
        ...     property_map={
        ...         'algorithms': {
        ...             'getter': lambda: algorithm_param.opts['limits'],
        ...             'setter': algorithm_param.setLimits,
        ...             'mode': SyncMode.FROM_SYNC,
        ...         },
        ...         'algorithm': {'param': algorithm_param}  # Shortcut for value
        ...     }
        ... )

        See Also
        --------
        bind_properties : For regular Qt widgets (uses blockSignals)
        bind_dict : For binding different widgets to different dict keys
        """
        if not isinstance(self.value, dict):
            raise TypeError(
                f"bind_parameter() requires DictSync (sync value must be dict). "
                f"Got {type(self.value).__name__}"
            )

        param_id = id(parameter)
        param_ref = ref(parameter)

        # Collect all connection keys for destruction callback
        all_connection_keys = [(param_id, prop_key) for prop_key in property_map.keys()]

        # Store param callbacks for feedback loop prevention across all properties
        # This dict is shared across all properties of this parameter
        all_param_callbacks = {}

        for property_key, config in property_map.items():
            # Check for shortcut syntax
            if 'param' in config:
                # Shortcut: {'param': parameter} auto-generates signal/getter/setter
                param_obj = config['param']
                signal = param_obj.sigValueChanged
                getter = param_obj.value
                setter = param_obj.setValue
                mode = config.get('mode', SyncMode.BIDIRECTIONAL)
            else:
                # Manual specification
                signal = config.get('signal')
                getter = config.get('getter')
                setter = config.get('setter')
                mode = config.get('mode', SyncMode.BIDIRECTIONAL if signal else SyncMode.FROM_SYNC)

                if not getter and not setter:
                    raise ValueError(
                        f"Property '{property_key}': Must provide at least 'getter' or 'setter', "
                        f"or use shortcut syntax with 'param'"
                    )

            # Initialize value based on init_from
            if init_from == 'sync' and setter:
                initial_value = self.value.get(property_key)
                if initial_value is not None and getter:
                    current_value = getter()
                    if initial_value != current_value:
                        setter(initial_value)
            elif init_from == 'widget' and getter:
                initial_value = getter()
                if property_key not in self.value or self.value[property_key] != initial_value:
                    new_dict = self.value.copy()
                    new_dict[property_key] = initial_value
                    self.value = new_dict

            # Create connection info for this property
            connection_info: ConnectionInfo = {
                'widget': parameter,
                'widget_ref': param_ref,
                'callbacks': [],
                'enabled': True,
                'property_key': property_key,
                'param_callbacks': all_param_callbacks  # Share across all properties
            }

            # Parameter → Sync (TO_SYNC or BIDIRECTIONAL)
            if mode in (SyncMode.TO_SYNC, SyncMode.BIDIRECTIONAL) and signal and getter:
                def make_param_to_sync_callback(key, get_fn, callbacks_ref):
                    def on_param_change(param, value):
                        # Get actual value using getter
                        actual_value = get_fn()
                        if actual_value != self.value.get(key):
                            new_dict = self.value.copy()
                            new_dict[key] = actual_value
                            # Get the reverse callback to disconnect it
                            reverse_cb = callbacks_ref.get((key, 'sync_to_param'))
                            if reverse_cb:
                                self.value_changed.disconnect(reverse_cb)
                            try:
                                self.value = new_dict
                            finally:
                                if reverse_cb:
                                    self.value_changed.connect(reverse_cb)
                    return on_param_change

                callback = make_param_to_sync_callback(property_key, getter, all_param_callbacks)
                signal.connect(callback)
                all_param_callbacks[(property_key, 'param_to_sync')] = (signal, callback)
                # Note: Don't add to connection_info['callbacks'] - Qt auto-disconnects

            # Sync → Parameter (FROM_SYNC or BIDIRECTIONAL)
            if mode in (SyncMode.FROM_SYNC, SyncMode.BIDIRECTIONAL) and setter:
                def make_sync_to_param_callback(key, set_fn, get_fn, sig, mode_val, callbacks_ref):
                    def on_sync_change(value_dict):
                        new_value = value_dict.get(key)
                        if new_value is not None:
                            # Check if value changed
                            current_value = get_fn() if get_fn else None
                            if new_value != current_value:
                                # Get the forward callback to disconnect it
                                if sig and mode_val == SyncMode.BIDIRECTIONAL:
                                    forward_cb_info = callbacks_ref.get((key, 'param_to_sync'))
                                    if forward_cb_info:
                                        sig.disconnect(forward_cb_info[1])
                                    try:
                                        set_fn(new_value)
                                    finally:
                                        if forward_cb_info:
                                            sig.connect(forward_cb_info[1])
                                else:
                                    # FROM_SYNC mode - no disconnection needed
                                    set_fn(new_value)
                    return on_sync_change

                callback = make_sync_to_param_callback(property_key, setter, getter, signal, mode, all_param_callbacks)
                self.value_changed.connect(callback)
                all_param_callbacks[(property_key, 'sync_to_param')] = callback
                connection_info['callbacks'].append(('sync', callback))

            # Store this property's connection
            self._set_connection(param_id, property_key, connection_info)

        # Setup parameter destruction callback once for all properties
        self._setup_widget_destruction_callback(parameter, all_connection_keys)

    def bind_dict(self, property_map: dict[str, dict[str, Any]],
                 init_from: InitFrom = 'sync') -> None:
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
            - 'init_from': InitFrom (optional, overrides global init_from for this property)

            **Advanced syntax (for custom logic):**
            - 'signal': Signal | None (required for TO_SYNC/BIDIRECTIONAL)
            - 'getter': callable () -> value (required for TO_SYNC/BIDIRECTIONAL)
            - 'setter': callable (value) -> None (required for FROM_SYNC/BIDIRECTIONAL)
            - 'mode': SyncMode (optional, default: inferred from getter/setter)
            - 'init_from': InitFrom (optional, overrides global init_from for this property)
        init_from : InitFrom, optional
            Global default for initialization source. Can be overridden per-property
            by including 'init_from' in the property config dict.

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

            # Configure and connect this property
            connection_info = self._setup_property_binding(
                widget, widget_ref, property_key, config, init_from
            )
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

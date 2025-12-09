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

    def __init__(self, initial_value: Any = None, data_type: Type | DataType | None = None,
                 validator: Callable[[Any], Any] | None = None) -> None:
        """
        Initialize widget sync with an initial value and optional type checking.

        Parameters
        ----------
        initial_value : Any
            Initial value for the sync
        data_type : Type | DataType, optional
            Expected data type for values. If None, inferred from initial_value.
            Use DataType.OBJECT to disable type checking.
        validator : callable, optional
            Optional validator function to correct/constrain values.
            Signature: (value) -> value (returns corrected value)
            Called before type validation when setting value.

        Examples
        --------
        >>> # Type inferred from initial value
        >>> sync = WidgetSync(initial_value=True)  # data_type = bool

        >>> # Explicit type
        >>> sync = WidgetSync(initial_value=0, data_type=int)

        >>> # Disable type checking
        >>> sync = WidgetSync(initial_value=None, data_type=DataType.OBJECT)

        >>> # With validator
        >>> sync = WidgetSync(initial_value=50, validator=lambda v: max(0, min(100, v)))
        """
        super().__init__()
        self._validator = validator
        self._data_type = self._resolve_type(initial_value, data_type)
        self._value: Any = self._validate_value(initial_value)
        # Unified connection storage with composite keys
        # Key: (widget_id, property_key | None), Value: ConnectionInfo dict
        # - (widget_id, None) for regular bind() connections
        # - (widget_id, "key") for property connections from bind_properties()
        self._connections: dict[tuple[int, str | None], ConnectionInfo] = {}

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
        # Apply validator first (if provided)
        if self._validator is not None:
            try:
                new_value = self._validator(new_value)
            except Exception as e:
                # Log error and keep current value
                import logging
                logging.getLogger(__name__).error(
                    f"Validator raised exception: {e}. Keeping current value.",
                    exc_info=True
                )
                return

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

    def bind(self,
             widget: QWidget,
             signal: Signal | None = None,
             getter: WidgetGetter | None = None,
             setter: WidgetSetter | None = None,
             mode: SyncMode | None = None,
             to_sync_transform: ValueTransform | None = None,
             from_sync_transform: ValueTransform | None = None) -> None:
        """
        Bind a widget to this sync.

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
        sync.bind(label, setter=lambda v: label.setText(str(v)))  # FROM_SYNC
        sync.bind(button, button.clicked, getter=lambda: True)     # TO_SYNC
        sync.bind(spinbox, spinbox.valueChanged,
                  getter=lambda: spinbox.value(),
                  setter=lambda v: spinbox.setValue(v))            # BIDIRECTIONAL

        # Explicit mode override:
        sync.bind(widget, signal, getter=getter, setter=setter,
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
        widget_id = id(widget)
        connection_key = (widget_id, None)  # None for regular bind() connections

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
            # Connection pattern info for add() method (set by factories)
            'property_name': None,  # Will be set by for_property()
            'signal_name': None,    # Will be set by for_property()
        }

        # Widget → Sync connection
        if mode in (SyncMode.BIDIRECTIONAL, SyncMode.TO_SYNC):
            callback = self._create_widget_to_sync_callback(
                connection_key, widget_ref, getter, to_sync_transform, None
            )
            signal.connect(callback)
            connection_info['callbacks'].append(('widget', callback))

        # Sync → Widget connection
        if mode in (SyncMode.BIDIRECTIONAL, SyncMode.FROM_SYNC):
            callback = self._create_sync_to_widget_callback(
                connection_key, widget_ref, setter, from_sync_transform, None
            )
            self.value_changed.connect(callback)
            connection_info['callbacks'].append(('sync', callback))

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

        # Setup widget destruction callback and store connection
        self._setup_widget_destruction_callback(widget, [connection_key])
        self._set_connection(widget_id, None, connection_info)

    def bind_properties(self,
                       widget: QWidget,
                       property_map: dict[str, dict[str, Any]]) -> None:
        """
        Bind multiple properties of ONE widget to different keys in a dict value.

        **IMPORTANT**: This method is designed for synchronizing multiple properties
        of a SINGLE widget. All properties control the same widget passed as the first
        parameter. The simplified 'property' syntax auto-generates getter/setter for
        this widget.

        **For different widgets mapped to dict keys, use bind_dict() instead.**

        This method allows syncing multiple properties from the same widget to different
        keys in the sync's value dict. Each property can have its own signal, getter,
        setter, and mode. When a signal fires, only its corresponding dict key is updated.

        Requires sync value to be a dict.

        **NEW: Simplified Property Syntax**
        Use 'property' key for automatic getter/setter generation with Qt properties:
        - Auto-generates getter/setter using widget.property()/setProperty()
        - Auto-detects signal from Qt property system
        - Uses weak references internally (memory safe)

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

        See Also
        --------
        bind_dict : For binding different widgets to different dict keys

        Examples
        --------
        Example 1: SpinBox configuration (min/max/current)
        >>> config_sync = WidgetSync(initial_value={'min': 0, 'max': 100, 'current': 50})
        >>> config_sync.bind_properties(
        ...     spinbox,  # All properties control this ONE spinbox
        ...     property_map={
        ...         'min': {'property': 'minimum', 'mode': SyncMode.FROM_SYNC},
        ...         'max': {'property': 'maximum', 'mode': SyncMode.FROM_SYNC},
        ...         'current': {'property': 'value'}  # Signal auto-detected, BIDIRECTIONAL
        ...     }
        ... )
        >>> # Change all properties at once
        >>> config_sync.value = {'min': 10, 'max': 1000, 'current': 100}

        Example 2: ComboBox with items + selection
        >>> sync = WidgetSync(initial_value={'items': ["A", "B"], 'selection': "A"})
        >>> sync.bind_properties(
        ...     combobox,  # All properties control this ONE combobox
        ...     property_map={
        ...         'items': {  # Advanced: custom logic for items list
        ...             'setter': lambda items: (combobox.clear(), combobox.addItems(items)),
        ...             'mode': SyncMode.FROM_SYNC
        ...         },
        ...         'selection': {'property': 'currentText'}  # Simple: auto-detected
        ...     }
        ... )
        >>> # Update combobox
        >>> sync.value = {'items': ["X", "Y", "Z"], 'selection': "Y"}

        Example 3: WRONG - Different widgets (use bind_dict() instead!)
        >>> # DON'T DO THIS - different widgets require bind_dict():
        >>> color_sync = WidgetSync(initial_value={'r': 255, 'g': 0, 'b': 0})
        >>> # WRONG: trying to control g_slider/b_slider via bind_properties(r_slider)
        >>> # RIGHT: use bind_dict() - see bind_dict() docstring for correct approach
        """
        # Validate that value is a dict
        if not isinstance(self._value, dict):
            raise TypeError(
                f"bind_properties() requires sync value to be a dict, "
                f"but got {type(self._value).__name__}"
            )

        widget_id = id(widget)
        widget_ref = ref(widget)

        # Collect all connection keys for destruction callback
        all_connection_keys = [(widget_id, prop_key) for prop_key in property_map.keys()]

        # Bind each property
        for property_key, config in property_map.items():
            # Validate property key exists in value dict
            if property_key not in self._value:
                raise ValueError(
                    f"Property key '{property_key}' not found in sync value dict. "
                    f"Available keys: {list(self._value.keys())}"
                )

            signal = config.get('signal')
            getter = config.get('getter')
            setter = config.get('setter')
            mode = config.get('mode')
            property_name = config.get('property')

            # AUTO-GENERATION: If 'property' key is provided, auto-generate getter/setter
            if property_name is not None:
                # Capture property name in local variable for closure
                prop_name = property_name

                # Auto-generate getter with weak reference (if not explicitly provided)
                if getter is None:
                    def make_property_getter(prop=prop_name, wref=widget_ref):
                        w = wref()
                        return w.property(prop) if w is not None else None
                    getter = make_property_getter

                # Auto-generate setter with weak reference (if not explicitly provided)
                if setter is None:
                    def make_property_setter(value, prop=prop_name, wref=widget_ref):
                        w = wref()
                        if w is not None:
                            w.setProperty(prop, value)
                    setter = make_property_setter

                # Auto-detect signal from Qt property system (if not provided)
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
                        # If auto-detection fails, signal remains None
                        # Will be caught by validation below if needed
                        pass

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
                        f"Property '{property_key}': Must provide at least getter or setter"
                    )

            # Validate signal requirement
            if mode in (SyncMode.BIDIRECTIONAL, SyncMode.TO_SYNC) and signal is None:
                raise ValueError(
                    f"Property '{property_key}': signal is required for {mode.value} mode"
                )

            # Validate getter/setter requirements
            if mode in (SyncMode.BIDIRECTIONAL, SyncMode.TO_SYNC) and getter is None:
                raise ValueError(
                    f"Property '{property_key}': getter is required for {mode.value} mode"
                )

            if mode in (SyncMode.BIDIRECTIONAL, SyncMode.FROM_SYNC) and setter is None:
                raise ValueError(
                    f"Property '{property_key}': setter is required for {mode.value} mode"
                )

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

            # Widget → Sync connection
            if mode in (SyncMode.BIDIRECTIONAL, SyncMode.TO_SYNC):
                callback = self._create_widget_to_sync_callback(
                    connection_key, widget_ref, getter, None, property_key
                )
                signal.connect(callback)
                connection_info['callbacks'].append(('widget', callback))

            # Sync → Widget connection
            if mode in (SyncMode.BIDIRECTIONAL, SyncMode.FROM_SYNC):
                callback = self._create_sync_to_widget_callback(
                    connection_key, widget_ref, setter, None, property_key
                )
                self.value_changed.connect(callback)
                connection_info['callbacks'].append(('sync', callback))

            # Initialize widget with current value
            if mode in (SyncMode.BIDIRECTIONAL, SyncMode.FROM_SYNC):
                try:
                    if property_key in self._value:
                        with self._block_signals(widget):
                            setter(self._value[property_key])
                except Exception as e:
                    raise RuntimeError(
                        f"Error initializing property '{property_key}' on widget {type(widget).__name__}: {e}"
                    ) from e

            self._set_connection(widget_id, property_key, connection_info)

        # Setup widget destruction callback once for all properties
        self._setup_widget_destruction_callback(widget, all_connection_keys)

    def bind_dict(self, property_map: dict[str, dict[str, Any]]) -> None:
        """
        Bind different widgets to different dict keys.

        Each property in the dict value is controlled by its own widget. This method
        is designed for synchronizing multiple different widgets where each widget
        corresponds to a specific key in the sync's dict value.

        **Key Difference from bind_properties():**
        - `bind_properties()`: Multiple properties of ONE widget → dict keys
        - `bind_dict()`: Multiple different widgets → dict keys (one widget per key)

        Requires sync value to be a dict. Each property must specify its widget
        using the 'widget' key in its configuration.

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

        Examples
        --------
        Example 1: RGB sliders (different widgets, one per color)
        >>> color_sync = WidgetSync(initial_value={'r': 255, 'g': 0, 'b': 0})
        >>> color_sync.bind_dict({
        ...     'r': {'widget': r_slider, 'property': 'value'},
        ...     'g': {'widget': g_slider, 'property': 'value'},
        ...     'b': {'widget': b_slider, 'property': 'value'}
        ... })
        >>> # All three sliders sync to their respective dict keys
        >>> color_sync.value = {'r': 128, 'g': 128, 'b': 128}

        Example 2: Form fields (different widget types)
        >>> user_sync = WidgetSync(initial_value={
        ...     'name': 'John', 'email': 'john@example.com', 'role': 'User'
        ... })
        >>> user_sync.bind_dict({
        ...     'name': {'widget': name_field, 'property': 'text'},
        ...     'email': {'widget': email_field, 'property': 'text'},
        ...     'role': {'widget': role_combo, 'property': 'currentText'}
        ... })

        Example 3: Display options (separate checkboxes)
        >>> display_sync = WidgetSync(initial_value={
        ...     'grid': True, 'legend': True, 'autoscale': False
        ... })
        >>> display_sync.bind_dict({
        ...     'grid': {'widget': grid_check, 'property': 'checked'},
        ...     'legend': {'widget': legend_check, 'property': 'checked'},
        ...     'autoscale': {'widget': autoscale_check, 'property': 'checked'}
        ... })

        Example 4: Mixed simple and advanced syntax
        >>> config_sync = WidgetSync(initial_value={'value': 50, 'enabled': True})
        >>> config_sync.bind_dict({
        ...     'value': {'widget': slider, 'property': 'value'},  # Simple
        ...     'enabled': {  # Advanced with custom logic
        ...         'widget': checkbox,
        ...         'signal': checkbox.toggled,
        ...         'getter': lambda: checkbox.isChecked(),
        ...         'setter': lambda v: checkbox.setChecked(v)
        ...     }
        ... })
        """
        # Validate that value is a dict
        if not isinstance(self._value, dict):
            raise TypeError(
                f"bind_dict() requires sync value to be a dict, "
                f"but got {type(self._value).__name__}"
            )

        # Track all connection keys and widgets for cleanup
        all_connection_keys = []
        widgets_to_setup = {}  # widget_id -> list of connection keys

        # Bind each property
        for property_key, config in property_map.items():
            # Validate property key exists in value dict
            if property_key not in self._value:
                raise ValueError(
                    f"Property key '{property_key}' not found in sync value dict. "
                    f"Available keys: {list(self._value.keys())}"
                )

            # Get the widget for this property (REQUIRED)
            widget = config.get('widget')
            if widget is None:
                raise ValueError(
                    f"Property '{property_key}': 'widget' key is required in bind_dict(). "
                    f"Each property must specify which widget it controls."
                )

            widget_id = id(widget)
            widget_ref = ref(widget)

            signal = config.get('signal')
            getter = config.get('getter')
            setter = config.get('setter')
            mode = config.get('mode')
            property_name = config.get('property')

            # AUTO-GENERATION: If 'property' key is provided, auto-generate getter/setter
            if property_name is not None:
                # Capture property name in local variable for closure
                prop_name = property_name

                # Auto-generate getter with weak reference (if not explicitly provided)
                if getter is None:
                    def make_property_getter(prop=prop_name, wref=widget_ref):
                        w = wref()
                        return w.property(prop) if w is not None else None
                    getter = make_property_getter

                # Auto-generate setter with weak reference (if not explicitly provided)
                if setter is None:
                    def make_property_setter(value, prop=prop_name, wref=widget_ref):
                        w = wref()
                        if w is not None:
                            w.setProperty(prop, value)
                    setter = make_property_setter

                # Auto-detect signal from Qt property system (if not provided)
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
                        # If auto-detection fails, signal remains None
                        # Will be caught by validation below if needed
                        pass

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
                        f"Property '{property_key}': Must provide at least getter or setter"
                    )

            # Validate signal requirement
            if mode in (SyncMode.BIDIRECTIONAL, SyncMode.TO_SYNC) and signal is None:
                raise ValueError(
                    f"Property '{property_key}': signal is required for {mode.value} mode"
                )

            # Validate getter/setter requirements
            if mode in (SyncMode.BIDIRECTIONAL, SyncMode.TO_SYNC) and getter is None:
                raise ValueError(
                    f"Property '{property_key}': getter is required for {mode.value} mode"
                )

            if mode in (SyncMode.BIDIRECTIONAL, SyncMode.FROM_SYNC) and setter is None:
                raise ValueError(
                    f"Property '{property_key}': setter is required for {mode.value} mode"
                )

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

            # Widget → Sync connection
            if mode in (SyncMode.BIDIRECTIONAL, SyncMode.TO_SYNC):
                callback = self._create_widget_to_sync_callback(
                    connection_key, widget_ref, getter, None, property_key
                )
                signal.connect(callback)
                connection_info['callbacks'].append(('widget', callback))

            # Sync → Widget connection
            if mode in (SyncMode.BIDIRECTIONAL, SyncMode.FROM_SYNC):
                callback = self._create_sync_to_widget_callback(
                    connection_key, widget_ref, setter, None, property_key
                )
                self.value_changed.connect(callback)
                connection_info['callbacks'].append(('sync', callback))

            # Initialize widget with current value
            if mode in (SyncMode.BIDIRECTIONAL, SyncMode.FROM_SYNC):
                try:
                    if property_key in self._value:
                        with self._block_signals(widget):
                            setter(self._value[property_key])
                except Exception as e:
                    raise RuntimeError(
                        f"Error initializing property '{property_key}' on widget {type(widget).__name__}: {e}"
                    ) from e

            self._set_connection(widget_id, property_key, connection_info)

            # Track for destruction callback setup
            all_connection_keys.append(connection_key)
            if widget_id not in widgets_to_setup:
                widgets_to_setup[widget_id] = []
            widgets_to_setup[widget_id].append(connection_key)

        # Setup widget destruction callbacks (one per unique widget)
        for widget_id, connection_keys in widgets_to_setup.items():
            # Get any widget reference from the connections
            first_key = connection_keys[0]
            widget_ref = self._connections[first_key]['widget_ref']
            widget = widget_ref()
            if widget is not None:
                self._setup_widget_destruction_callback(widget, connection_keys)

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

                # Property connection: update dict key
                if property_key is not None:
                    if isinstance(self._value, dict):
                        new_dict = self._value.copy()
                        new_dict[property_key] = value
                        self.set_value(new_dict, emit=True)
                # Regular connection: update entire value
                else:
                    self.set_value(value, emit=True)
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

            try:
                # Property connection: extract dict key
                if property_key is not None:
                    if isinstance(value, dict) and property_key in value:
                        value = value[property_key]
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
                f"💡 Solution: Use bind() instead of add():\n\n"
                f"    sync.bind(\n"
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

        # Bind the widget
        self.bind(widget, signal, getter, setter, mode,
                  to_sync_transform, from_sync_transform)

    def remove(self, widget: QWidget) -> None:
        """
        Convenience method to remove a widget.

        Alias for unbind() for consistency with add().

        Parameters
        ----------
        widget : QWidget
            Widget to remove
        """
        self.unbind(widget)

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

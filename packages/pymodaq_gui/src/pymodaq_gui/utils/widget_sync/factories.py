"""
Factory methods for common widget types.

This module can be extended by users to add their own factory methods.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from weakref import ref

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget
    from .core import WidgetSync, SyncMode


class WidgetSyncFactories:
    """
    Mixin class providing factory methods for common Qt widgets.

    Users can create their own factory methods by:
    1. Inheriting from WidgetSync
    2. Adding their own @classmethod factories

    Example:
        class MyWidgetSync(WidgetSync):
            @classmethod
            def for_my_custom_widget(cls, widget, initial=None):
                return cls.for_property(widget, 'customProperty', 'customSignal', initial)
    """

    @classmethod
    def for_property(cls,
                     widget: QWidget,
                     property_name: str,
                     signal_name: str | None = None,
                     initial: Any = None,
                     mode: SyncMode | None = None,
                     data_type: type | None = None,
                     validator: Any = None) -> WidgetSync:
        """
        Create a sync for any Qt property with auto-detection.

        This is the most flexible factory - all others build on this.

        Parameters
        ----------
        widget : QWidget
            The first widget to sync
        property_name : str
            Name of the Qt property (e.g., 'checked', 'value', 'text')
        signal_name : str, optional
            Name of the change signal. If None, auto-detects from property
        initial : Any, optional
            Initial value (if None, uses widget's current value)
        mode : SyncMode, optional
            Sync mode (default: BIDIRECTIONAL)
        data_type : type, optional
            Explicit data type for type checking (default: inferred from initial)
        validator : callable, optional
            Optional validator function to correct/constrain values

        Returns
        -------
        WidgetSync
            A new sync instance with the widget connected

        Example
        -------
        >>> sync = WidgetSync.for_property(my_spinbox, 'value', initial=50)
        >>> sync.add(other_spinbox)  # Add more spinboxes
        """
        # Import here to avoid circular dependency
        from .core import WidgetSync, SyncMode as SM

        if mode is None:
            mode = SM.BIDIRECTIONAL

        # Get property metadata for auto-detection
        meta = widget.metaObject()
        prop_index = meta.indexOfProperty(property_name)

        if prop_index == -1:
            raise ValueError(
                f"Property '{property_name}' not found on {type(widget).__name__}"
            )

        prop = meta.property(prop_index)

        # Auto-detect signal if not provided
        if signal_name is None:
            notify_signal = prop.notifySignal()
            if notify_signal.isValid():
                signal_name = notify_signal.name().data().decode()
            else:
                raise ValueError(
                    f"Property '{property_name}' has no notify signal. "
                    f"Please provide signal_name explicitly."
                )

        # Get signal object
        try:
            signal = getattr(widget, signal_name)
        except AttributeError:
            raise ValueError(
                f"Signal '{signal_name}' not found on {type(widget).__name__}"
            )

        # Store property name in local variable to avoid capturing self in lambda
        prop_name = property_name

        # Create weak reference to widget to avoid circular references
        widget_ref = ref(widget)

        # Create getter/setter using weak reference
        def getter():
            w = widget_ref()
            return w.property(prop_name) if w is not None else None

        def setter(value):
            w = widget_ref()
            if w is not None:
                w.setProperty(prop_name, value)

        # Determine initial value
        if initial is None:
            initial = widget.property(prop_name)  # Use widget directly before connecting

        # Create sync and bind
        sync = cls(initial_value=initial, data_type=data_type, validator=validator)
        sync.bind(widget, signal, getter, setter, mode)

        # Store pattern info in the connection for add() method to use
        widget_id = id(widget)
        connection_key = (widget_id, None)  # Use composite key (widget_id, property_key)
        if connection_key in sync._connections:
            sync._connections[connection_key]['property_name'] = property_name
            sync._connections[connection_key]['signal_name'] = signal_name

        return sync

    @classmethod
    def for_checkbox(cls, checkbox, initial: bool = False,
                     mode = None, validator = None) -> WidgetSync:
        """
        Create a sync for checkbox widgets.

        Parameters
        ----------
        checkbox : QCheckBox
            The first checkbox to sync
        initial : bool, optional
            Initial checked state (default: False)
        mode : SyncMode, optional
            Sync mode (default: BIDIRECTIONAL)
        validator : callable, optional
            Optional validator function

        Returns
        -------
        WidgetSync
            A new sync instance

        Example
        -------
        >>> sync = WidgetSync.for_checkbox(my_checkbox, initial=True)
        >>> sync.add(another_checkbox)
        """
        from .core import SyncMode
        if mode is None:
            mode = SyncMode.BIDIRECTIONAL
        return cls.for_property(checkbox, 'checked', 'toggled', initial, mode, validator=validator)

    @classmethod
    def for_spinbox(cls, spinbox, initial: int | float = 0,
                    mode = None, validator = None) -> WidgetSync:
        """
        Create a sync for QSpinBox or QDoubleSpinBox widgets.

        Parameters
        ----------
        spinbox : QSpinBox | QDoubleSpinBox
            The first spinbox to sync
        initial : int or float, optional
            Initial value (default: 0)
        mode : SyncMode, optional
            Sync mode (default: BIDIRECTIONAL)
        validator : callable, optional
            Optional validator function

        Returns
        -------
        WidgetSync
            A new sync instance

        Example
        -------
        >>> sync = WidgetSync.for_spinbox(spinbox1, initial=50)
        >>> sync.add(spinbox2)
        >>> sync.add(spinbox3)
        """
        from .core import SyncMode
        if mode is None:
            mode = SyncMode.BIDIRECTIONAL
        return cls.for_property(spinbox, 'value', 'valueChanged', initial, mode, validator=validator)

    @classmethod
    def for_slider(cls, slider, initial: int = 0,
                   mode = None, validator = None) -> WidgetSync:
        """
        Create a sync for QSlider widgets.

        Parameters
        ----------
        slider : QSlider
            The first slider to sync
        initial : int, optional
            Initial value (default: 0)
        mode : SyncMode, optional
            Sync mode (default: BIDIRECTIONAL)
        validator : callable, optional
            Optional validator function

        Returns
        -------
        WidgetSync
            A new sync instance

        Example
        -------
        >>> sync = WidgetSync.for_slider(slider1, initial=75)
        >>> sync.add(slider2)
        """
        from .core import SyncMode
        if mode is None:
            mode = SyncMode.BIDIRECTIONAL
        return cls.for_property(slider, 'value', 'valueChanged', initial, mode, validator=validator)

    @classmethod
    def for_combobox(cls, combobox, initial: int | str = 0,
                     use_text: bool = False,
                     mode = None, validator = None) -> WidgetSync:
        """
        Create a sync for QComboBox widgets.

        Parameters
        ----------
        combobox : QComboBox
            The first combobox to sync
        initial : int or str, optional
            Initial value - index if use_text=False, text if use_text=True (default: 0)
        use_text : bool, optional
            If True, sync currentText; if False, sync currentIndex (default: False)
        mode : SyncMode, optional
            Sync mode (default: BIDIRECTIONAL)
        validator : callable, optional
            Optional validator function

        Returns
        -------
        WidgetSync
            A new sync instance

        Examples
        --------
        >>> # Sync by index (default)
        >>> sync = WidgetSync.for_combobox(combo1, initial=0)
        >>> sync.add(combo2)

        >>> # Sync by text
        >>> sync = WidgetSync.for_combobox(combo1, initial="Option A", use_text=True)
        >>> sync.add(combo2)
        """
        from .core import SyncMode
        if mode is None:
            mode = SyncMode.BIDIRECTIONAL
        if use_text:
            return cls.for_property(combobox, 'currentText', 'currentTextChanged',
                                   initial, mode, validator=validator)
        else:
            return cls.for_property(combobox, 'currentIndex', 'currentIndexChanged',
                                   initial, mode, validator=validator)

    @classmethod
    def for_lineedit(cls, lineedit, initial: str = "",
                     mode = None, validator = None) -> WidgetSync:
        """
        Create a sync for QLineEdit widgets.

        Parameters
        ----------
        lineedit : QLineEdit
            The first line edit to sync
        initial : str, optional
            Initial text (default: "")
        mode : SyncMode, optional
            Sync mode (default: BIDIRECTIONAL)
        validator : callable, optional
            Optional validator function

        Returns
        -------
        WidgetSync
            A new sync instance

        Example
        -------
        >>> sync = WidgetSync.for_lineedit(edit1, initial="Hello")
        >>> sync.add(edit2)
        """
        from .core import SyncMode
        if mode is None:
            mode = SyncMode.BIDIRECTIONAL
        return cls.for_property(lineedit, 'text', 'textChanged', initial, mode, validator=validator)

"""
Qt Widget Synchronization
=================================
Basic Usage - Single Values:
    >>> from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode
    >>>
    >>> # Create sync for checkboxes
    >>> sync = WidgetSync.for_checkbox(checkbox1, initial=True)
    >>> sync.add(checkbox2)
    >>> sync.add(checkbox3)
    >>>
    >>> # Change value programmatically
    >>> sync.value = False  # All checkboxes update

Dict Synchronization:
    >>> # Auto-detects DictSync for dict values
    >>> color_sync = WidgetSync(initial_value={'r': 128, 'g': 64, 'b': 192})
    >>>
    >>> # Bind different widgets to dict keys
    >>> color_sync.bind_dict(property_map={
    ...     'r': {'widget': r_slider, 'property': 'value'},
    ...     'g': {'widget': g_slider, 'property': 'value'},
    ...     'b': {'widget': b_slider, 'property': 'value'}
    ... })
    >>>
    >>> # Change dict value - all sliders update
    >>> color_sync.value = {'r': 255, 'g': 0, 'b': 0}

Advanced Usage - Custom Factories:
    >>> from pymodaq_gui.utils.widget_sync import WidgetSync, WidgetSyncFactories
    >>>
    >>> class MyFactories(WidgetSyncFactories):
    ...     @classmethod
    ...     def for_my_widget(cls, widget, initial=None):
    ...         return cls.for_property(widget, 'myProp', 'mySignal', initial)
    >>>
    >>> class MySync(WidgetSync, MyFactories):
    ...     pass
    >>>
    >>> sync = MySync.for_my_widget(my_widget)
"""

from .core import (
    BaseWidgetSync,
    ValueSync,
    DictSync,
    SyncMode,
    DataType
)
from .factories import WidgetSyncFactories
from typing import Any, Callable, Type

# Smart main class that auto-selects ValueSync or DictSync
class WidgetSync(WidgetSyncFactories):
    """
    Smart widget synchronization that auto-detects whether to use ValueSync or DictSync.

    This is the main class users should use. It automatically:
    - Uses ValueSync for single values (int, str, bool, float, etc.)
    - Uses DictSync for dict values
    - Includes factory methods for common widgets (for_checkbox, for_spinbox, etc.)

    For extending with custom factories:
        >>> class MySync(WidgetSync, MyCustomFactories):
        ...     pass

    For direct use of specialized classes:
        >>> from pymodaq_gui.utils.widget_sync import ValueSync, DictSync
        >>> value_sync = ValueSync(initial_value=50)
        >>> dict_sync = DictSync(initial_value={'a': 1, 'b': 2})
    """

    def __new__(cls, initial_value: Any = None, data_type: Type | DataType | None = None,
                validator: Callable[[Any], Any] | None = None):
        """
        Auto-detect and return the appropriate sync class.

        Parameters
        ----------
        initial_value : Any
            Initial value (dict → DictSync, anything else → ValueSync)
        data_type : Type | DataType, optional
            Expected data type (for ValueSync only)
        validator : callable, optional
            Optional validator function

        Returns
        -------
        ValueSync or DictSync
            The appropriate sync instance based on initial_value type
        """
        # Auto-detect: if initial_value is a dict, use DictSync
        if isinstance(initial_value, dict):
            # DictSync doesn't use data_type parameter
            return DictSync(initial_value=initial_value, validator=validator)
        else:
            # Use ValueSync for everything else
            return ValueSync(initial_value=initial_value, data_type=data_type, validator=validator)


__all__ = [
    'WidgetSync',        # Main class (uses ValueSync + factories)
    'ValueSync',         # For single-value synchronization
    'DictSync',          # For dict-value synchronization
    'BaseWidgetSync',    # For type hints and advanced usage
    'SyncMode',          # Synchronization modes
    'DataType',          # Data type specification
    'WidgetSyncFactories',  # For custom factory extensions
]

"""
Qt Widget Synchronization

Simple, powerful widget property synchronization for Qt applications.

Basic Usage:
    >>> from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode
    >>>
    >>> # Create sync for checkboxes
    >>> sync = WidgetSync.for_checkbox(checkbox1, initial=True)
    >>> sync.add(checkbox2)
    >>> sync.add(checkbox3)
    >>>
    >>> # Change value programmatically
    >>> sync.value = False  # All checkboxes update

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

from .core import WidgetSync as WidgetSyncBase, SyncMode, DataType
from .factories import WidgetSyncFactories

# Combine base class with factory methods for convenience
class WidgetSync(WidgetSyncBase, WidgetSyncFactories):
    """
    Widget synchronization with built-in factory methods.

    This is the main class users should use. It combines:
    - Base WidgetSync functionality (connect, disconnect, value management)
    - Factory methods for common widgets (for_checkbox, for_spinbox, etc.)

    For extending with custom factories:
        >>> class MySync(WidgetSync, MyCustomFactories):
        ...     pass

    For base class without factories:
        >>> from pymodaq_gui.utils.widget_sync.core import WidgetSync as BaseSync
    """
    pass


__all__ = [
    'WidgetSync',
    'SyncMode',
    'DataType',  # Export for type hints and explicit type specification
    'WidgetSyncFactories',  # Export for custom extensions
]

__version__ = '0.1.0'

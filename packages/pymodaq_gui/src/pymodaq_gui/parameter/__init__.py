from contextlib import contextmanager
from typing import Any

from qtpy import QtWidgets

from pyqtgraph.parametertree import parameterTypes, Parameter, ParameterTree
from . import pymodaq_ptypes
from .enums import ParameterChangeType


@contextmanager
def change_transaction(param: Parameter,
                       change_type: ParameterChangeType | str = None,
                       value: Any = None,
                       emitter: Any = None,
                       emit_signal: bool = True):
    """
    Context manager to isolate multiple structural or value updates on a parameter
    (or its children) while completely suppressing intermediate cascading signals.

    Upon exiting the transaction, a single unified change signal is manually
    committed using the designated emitter Parameter object, unless emit_signal
    is explicitly set to False.

    Parameters
    ----------
    change_type : ParameterChangeType or str, optional
        The change type string to put in the emitted event tuple.
        If None, it automatically detects 'value' or 'limits' changes.
    value : any, optional
        The value payload to emit. If None and change_type is 'value',
        self.value() will be used automatically.
    emitter : Parameter, optional
        The specific Parameter instance to emit the signal from.
        If None, it defaults to the absolute root parameter of the tree.
    emit_signal : bool, default True
        If True, dispatches a single unified signal upon exiting the context.
        If False, suppresses all notifications completely (silent transaction).
    """
    # 1. Walk up to the root parameter using parent()
    root = param
    while root.parent() is not None:
        root = root.parent()

    # Set default emitter target to root if not explicitly provided
    if emitter is None:
        emitter = root

    # Store the initial state to allow automatic detection at the end
    old_value = param.value()
    old_limits = param.opts.get('limits', None)

    # 2. Globally block tree-wide signals at the root level
    root.blockTreeChangeSignal()
    if emitter is not root:
        emitter.blockTreeChangeSignal()
    try:
        yield

        # 3. Clear the queue of transient/garbage events accumulated by Qt widgets
        root.treeStateChanges = []
        if emitter is not root:
            emitter.treeStateChanges = []
    finally:
        # 4. Always guarantee unblocking the tree even if an exception occurs
        if emitter is not root:
            emitter.unblockTreeChangeSignal()
        root.unblockTreeChangeSignal()

    # 5. Skip signal generation completely if silent mode is requested
    if not emit_signal:
        return

    # 6. Smart automatic detection if no custom change type was requested
    if change_type is None:
        new_limits = param.opts.get('limits', None)

        if old_value != param.value():
            resolved_type = "value"
            resolved_value = param.value() if value is None else value
        elif old_limits != new_limits:
            resolved_type = "limits"
            resolved_value = new_limits if value is None else value
        else:
            resolved_type = "value"
            resolved_value = param.value() if value is None else value
    else:
        # Accept both ParameterChangeType Enum or a raw string for custom events
        resolved_type = change_type.value if hasattr(change_type, 'value') else str(change_type)

        if value is None and resolved_type == "value":
            resolved_value = param.value()
        else:
            resolved_value = value

    # 7. Manually dispatch exactly one stabilized signal from the designated emitter
    emitter.sigTreeStateChanged.emit(emitter, [(param, resolved_type, resolved_value)])


__parameter_value_old_fun = Parameter.value
def __parameter_value_monkey_path(self):
    try:
        return __parameter_value_old_fun(self)
    except ValueError:
        return None

Parameter.value = __parameter_value_monkey_path
Parameter.change_transaction = change_transaction



class ParameterTree(ParameterTree):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.header().setVisible(True)
        self.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        #self.header().setMinimumSectionSize(150)

"""Context objects describing who is invoking a control-module call (e.g. ``grab_data``)
and which part of PyMoDAQ's HDF5 file structure that call corresponds to.

Plugins receive a :class:`CallerInfo` (or one of its subclasses) as the ``caller`` kwarg
so they can mirror PyMoDAQ's file layout in their own files, without inventing independent
session bookkeeping.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class CallerInfo:
    """Generic caller context: the HDF5 file PyMoDAQ is writing to and the active node.

    Outside of any extension-driven acquisition (live view, manual snap) no caller is
    passed at all, so plugins must treat it as optional::

        def grab_data(self, Naverage=1, **kwargs):
            caller = kwargs.get('caller')  # None when not driven by an extension
            if caller is not None and caller.h5_file_path is not None:
                out_dir = Path(caller.h5_file_path).parent / caller.node_name
                ...
    """
    h5_file_path: Optional[str] = None
    """Absolute path to the HDF5 file being written by PyMoDAQ."""
    node_name: Optional[str] = None
    """Name of the active HDF5 group for this call, e.g. ``'Scan001'``."""
    caller_name: Optional[str] = None
    """A descriptive label for what produced this caller. An extension sets its own name
    (e.g. ``'DAQScan'``); the module's own self-derived fallback (see
    ``ControlModule.get_caller``) sets the class name of its current
    ``module_and_data_saver`` instead, since it has no notion of which extension (if any)
    last configured that saver."""
    caller_type: Optional[str] = None
    """Class name of this caller object, e.g. ``'DAQScanCaller'``. Auto-filled from
    ``type(self).__name__`` in :meth:`__post_init__` unless explicitly overridden, so
    a plugin can reliably tell caller shapes apart (and therefore which extra fields, if
    any, a given caller carries) without needing an explicit import of every caller
    subclass to ``isinstance``-check against."""

    def __post_init__(self):
        if self.caller_type is None:
            self.caller_type = type(self).__name__

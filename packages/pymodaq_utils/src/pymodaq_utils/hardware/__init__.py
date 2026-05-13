"""Hardware discovery caches for PyMoDAQ plugins.

Each backend (:mod:`~pymodaq_utils.hardware.visa`,
:mod:`~pymodaq_utils.hardware.serial_ports`) queries the OS exactly once per
process. Subsequent calls reuse the cached result, so plugin startup cost is
paid at most once regardless of how many plugins share the same backend.

Quick reference::

    # VISA-based plugin (Newport, Thorlabs, PI, ...)
    from pymodaq_utils.hardware.visa import list_serial_resources
    ports = list_serial_resources()

    # pyserial-based plugin (Arduino, Ocean Optics, ...)
    from pymodaq_utils.hardware.serial_ports import list_resources
    ports = list_resources()

    # After hot-plugging a device
    from pymodaq_utils.hardware import invalidate_all_caches
    invalidate_all_caches()
"""
from .visa import invalidate_cache as _invalidate_visa
from .serial_ports import invalidate_cache as _invalidate_serial


def invalidate_all_caches() -> None:
    """Clear both the VISA and serial discovery caches.

    Call this after hot-plugging a device so the next call to any
    ``list_*`` function re-discovers the current set of instruments.
    """
    _invalidate_visa()
    _invalidate_serial()

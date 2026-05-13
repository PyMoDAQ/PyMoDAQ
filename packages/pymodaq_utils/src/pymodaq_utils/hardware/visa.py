"""VISA hardware discovery cache.

Wraps :mod:`pyvisa` to enumerate available VISA resources exactly once per
process. ``pyvisa`` is an optional dependency: if it is not installed, or no
VISA backend is found, all functions return empty lists silently.

Typical usage in a plugin::

    from pymodaq_utils.hardware.visa import list_serial_resources

    ports = list_serial_resources()  # e.g. ['ASRL/dev/ttyUSB0::INSTR']

After hot-plugging a device, refresh the cache with::

    from pymodaq_utils.hardware.visa import invalidate_cache
    invalidate_cache()
"""
from .base import HardwareCache


class VisaCache(HardwareCache):
    _cache = None

    @classmethod
    def _fetch(cls) -> dict:
        try:
            import pyvisa
            rm = pyvisa.ResourceManager()
            info = dict(rm.list_resources_info())
            rm.close()
            return info
        except Exception:
            return {}

    @classmethod
    def list_resources(cls) -> list[str]:
        """All available VISA resource strings (e.g. 'GPIB0::5::INSTR')."""
        return list(cls._get_cache().keys())

    @classmethod
    def list_serial_resources(cls) -> list[str]:
        """ASRL (serial-over-VISA) resource strings only.

        Linux:   'ASRL/dev/ttyUSB0::INSTR'
        Windows: 'ASRL3::INSTR'
        """
        return [r for r in cls._get_cache() if r.startswith('ASRL')]

    @classmethod
    def list_resource_aliases(cls) -> list[str]:
        """Human-readable aliases where available (e.g. 'COM3' on Windows)."""
        return [i.alias for i in cls._get_cache().values() if i.alias]


def list_resources() -> list[str]:
    """All available VISA resource strings (e.g. 'GPIB0::5::INSTR', 'TCPIP0::...')."""
    return VisaCache.list_resources()


def list_serial_resources() -> list[str]:
    """ASRL (serial-over-VISA) resource strings only.

    Linux:   ``'ASRL/dev/ttyUSB0::INSTR'``
    Windows: ``'ASRL3::INSTR'``
    """
    return VisaCache.list_serial_resources()


def list_resource_aliases() -> list[str]:
    """Human-readable aliases where available (e.g. ``'COM3'`` on Windows)."""
    return VisaCache.list_resource_aliases()


def invalidate_cache() -> None:
    """Clear the VISA resource cache so the next call re-discovers."""
    VisaCache.invalidate_cache()

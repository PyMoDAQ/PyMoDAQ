"""pyserial hardware discovery cache.

Wraps :mod:`serial.tools.list_ports` to enumerate available serial ports
exactly once per process. ``pyserial`` is an optional dependency: if it is
not installed, all functions return empty lists and a warning is logged.

Typical usage in a plugin::

    from pymodaq_utils.hardware.serial_ports import list_resources

    ports = list_resources()  # e.g. ['/dev/ttyUSB0', 'COM3']

After hot-plugging a device, refresh the cache with::

    from pymodaq_utils.hardware.serial_ports import invalidate_cache
    invalidate_cache()
"""
import pymodaq_utils.logger as logger_module
from .base import HardwareCache

logger = logger_module.set_logger(logger_module.get_module_name(__file__))


class SerialPortsCache(HardwareCache):
    _cache = None

    @classmethod
    def _fetch(cls) -> list:
        try:
            from serial.tools.list_ports import comports
            return list(comports())
        except ImportError:
            logger.warning('pyserial is not installed — serial port discovery unavailable. '
                           'Install it with: pip install pyserial')
            return []
        except Exception as e:
            logger.warning(f'Serial port discovery failed: {e}')
            return []

    @classmethod
    def list_resources(cls) -> list[str]:
        """Serial port device strings (e.g. '/dev/ttyUSB0', 'COM3')."""
        return [p.device for p in cls._get_cache()]

    @classmethod
    def list_port_descriptions(cls) -> list[str]:
        """Human-readable descriptions for each serial port."""
        return [p.description for p in cls._get_cache()]


def list_resources() -> list[str]:
    """Serial port device strings (e.g. '/dev/ttyUSB0', 'COM3')."""
    return SerialPortsCache.list_resources()


def list_port_descriptions() -> list[str]:
    """Human-readable descriptions for each serial port."""
    return SerialPortsCache.list_port_descriptions()


def invalidate_cache() -> None:
    """Clear the serial port cache so the next call re-discovers."""
    SerialPortsCache.invalidate_cache()

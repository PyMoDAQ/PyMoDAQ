# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

from serializall import SerializableBase, SerializableFactory

from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter.utils import ParameterWithPath, compareValuesParameter
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import get_entrypoints
from pymodaq_utils.enums import BaseEnum

from pymodaq.utils.scanner.scan_factory import ScannerFactory


logger = set_logger(get_module_name(__file__))
ser_factory = SerializableFactory()

if TYPE_CHECKING:
    from pymodaq.utils.scanner import Scanner


def register_scanner(parent_module_name: str = 'pymodaq.utils.scanner'):
    scanners = []
    try:
        scanner_module = import_module(f'{parent_module_name}.scanners')

        scanner_path = Path(scanner_module.__path__[0])

        for file in scanner_path.iterdir():
            if file.is_file() and 'py' in file.suffix and file.stem != '__init__':
                try:
                    scanners.append(import_module(f'.{file.stem}', scanner_module.__name__))
                except (ModuleNotFoundError, Exception) as e:
                    pass
    except ModuleNotFoundError:
        pass
    finally:
        return scanners


def register_scanners() -> list:
    scanners = register_scanner('pymodaq.utils.scanner')
    discovered_scanners_plugins = get_entrypoints('pymodaq.scanners')
    for entry in discovered_scanners_plugins:
        scanners.extend(register_scanner(entry.value))
    return scanners


register_scanners()
scanner_factory = ScannerFactory()
ScanType = BaseEnum('ScanType', ['NoScan'] + scanner_factory.scan_types())


@SerializableFactory.register_decorator()
class ScanRepr(SerializableBase):
    def __init__(self, scanner: 'Scanner' = None):
        super().__init__()
        self.actuators: list[str] = []
        self.scanner_settings = Parameter(name='scanner')
        self.sub_scanner_settings = Parameter(name='sub_scanner')

        if scanner is not None:
            self.actuators = [act.title for act in scanner.actuators]
            self.scanner_settings.restoreState(scanner.settings.saveState())
            self.sub_scanner_settings.restoreState(scanner.scanner.settings.saveState())

    def __eq__(self, other: 'ScanRepr'):
        return (self.actuators == other.actuators and
                compareValuesParameter(self.scanner_settings, other.scanner_settings, with_self=False) and
                compareValuesParameter(self.sub_scanner_settings, other.sub_scanner_settings, with_self=False))

    @staticmethod
    def serialize(obj: 'ScanRepr') -> bytes:
        actuators = [act for act in obj.actuators]
        scanner_settings = ParameterWithPath(obj.scanner_settings)
        subscan_settings = ParameterWithPath(obj.sub_scanner_settings)

        bytes_string = b''
        bytes_string += ser_factory.get_apply_serializer(actuators)
        bytes_string += ser_factory.get_apply_serializer(scanner_settings)
        bytes_string += ser_factory.get_apply_serializer(subscan_settings)
        return bytes_string

    @staticmethod
    def deserialize(bytes_str: bytes) -> tuple["ScanRepr", bytes]:
        actuators, remaining_bytes = ser_factory.get_apply_deserializer(bytes_str, False)
        scanner_settings, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)
        subscan_settings, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)

        scan_repr = ScanRepr()
        scan_repr.actuators = actuators
        scan_repr.scanner_settings = scanner_settings.parameter
        scan_repr.sub_scanner_settings = subscan_settings.parameter
        return scan_repr, remaining_bytes


class ScannerException(Exception):
    """Raised when there is an error related to the Scanner class (see pymodaq.da_utils.scanner)"""
    pass


class ScanInfo:
    """Container class for a given scan details

    It includes the number of steps and all the positions for the selected actuators. It also contains these positions
    as scan axes for easier use.

    Parameters
    ----------

    Nsteps: int
        Number of steps of the scan
    positions: ndarray
        multidimensional array. the first dimension has a length of Nsteps and each element is an actuator position
    positions_indexes: ndarray
        multidimensional array of Nsteps 0th dimension length where each element is the index
        of the corresponding positions within the axis_unique
    axes_unique: list of ndarray
        list of sorted (and with unique values) 1D arrays of unique positions of each defined axes
    selected_actuators: List[str]
        The actuators to be used for this scan
    kwargs: dict of other named parameters to be saved as attributes

    Attributes
    ----------
    Nsteps: int
        Number of steps of the scan
    positions: ndarray
        multidimensional array. the first dimension has a length of Nsteps and each element is an actuator position
    positions_indexes: ndarray
        multidimensional array of Nsteps 0th dimension length where each element is the index
        of the corresponding positions within the axis_unique
    axes_unique: list of ndarray
        list of sorted (and with unique values) 1D arrays of unique positions of each defined axes
    kwargs: dict of other named attributes
    """
    def __init__(self, Nsteps=0, positions=None, axes_indexes=None, axes_unique=None, selected_actuators=[],
                 **kwargs):
        self.Nsteps = Nsteps
        self.positions = positions
        self.axes_indexes = axes_indexes
        self.axes_unique = axes_unique
        self.selected_actuators = selected_actuators
        for k in kwargs:
            setattr(self, k, kwargs[k])

    def __repr__(self):
        return f'Scan of {self.selected_actuators} with {self.Nsteps} positions'





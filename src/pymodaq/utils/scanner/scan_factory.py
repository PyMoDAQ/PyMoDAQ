# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Callable, Union, List, Tuple, TYPE_CHECKING


import numpy as np
from qtpy import QtWidgets

from pymodaq_utils.factory import ObjectFactory
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.abstract import abstract_attribute
from pymodaq_utils import math_utils as mutils
from pymodaq_utils import config as configmod

from pymodaq_gui.managers.parameter_manager import ParameterManager, Parameter

from pymodaq_data.data import Axis, DataDistribution

from pymodaq.utils.scanner.scan_config import ScanConfig
from pymodaq_gui.config import ConfigSaverLoader


if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pymodaq.utils.scanner.scan_selector import Selector


logger = set_logger(get_module_name(__file__))
config = configmod.Config()


class ScanParameterManager(ParameterManager):
    settings_name = 'scanner_settings'

    def __init__(self):
        super().__init__()
        self.settings_tree.header().setVisible(True)
        self.settings_tree.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.settings_tree.header().setMinimumSectionSize(150)
        self.settings_tree.setMinimumHeight(150)


class ScannerBase(ScanParameterManager, metaclass=ABCMeta):
    """Abstract class for all Scanners

    Attributes
    ----------
    scan_type: str
        String defining the main identifier
    scan_subtype: str
        String defining the second identifier
    params: List[dict]
        list specifying the scanner set of parameters to properly configure all the scan steps
    positions: np.ndarray
        ndarray of all positions. First dimension is number of actuators, second is positions of a given actuator at
        each step
    axes_unique: List[np.ndarray]
        list of ndarrays representing unique values of steps for each actuator in the scan
    axes_indexes: np.ndarray
        ndarray of indexes from axes_unique for each value in positions
    n_steps: int
        Number of scan steps. Equal to the second dimension of positions
    n_axes: int
        Number of actuators/scan axes. Equal to the first dimension of positions
    """
    scan_type: str = abstract_attribute()
    scan_subtype: str = abstract_attribute()

    params: List[dict] = abstract_attribute()
    axes_unique: List[np.ndarray] = abstract_attribute()
    axes_indexes: np.ndarray = abstract_attribute()
    n_steps: int = abstract_attribute()
    n_axes: int = abstract_attribute()
    distribution: DataDistribution = abstract_attribute()
    save_settings = True

    def __init__(self, actuators: List[DAQ_Move] = None):
        super().__init__()
        self.positions: np.ndarray = None
        self.n_steps = 1
        self.config = ScanConfig()
        base_path = [act.title for act in actuators] + [self.scan_type, self.scan_subtype]

        self.config_saver_loader = ConfigSaverLoader(self.settings,
                                                     self.config,
                                                     base_path)

        self.actuators: List[DAQ_Move] = actuators

        self.set_settings_titles()
        self.set_settings_values()

        if self.check_steps():
            self.set_scan()

    def set_settings_titles(self):
        """Update the settings accordingly with the selected actuators"""
        ...

    def set_settings_values(self, param: Parameter = None):
        self.config_saver_loader.load_config(param)

    @property
    def actuators(self) -> List[DAQ_Move]:
        return self._actuators

    @actuators.setter
    def actuators(self, actuators: List[DAQ_Move]):
        self._actuators = actuators
        base_path = self.actuators_name + [self.scan_type, self.scan_subtype]
        self.config_saver_loader.base_path = base_path

    @property
    def actuators_name(self) -> List[str]:
        return [act.title for act in self.actuators]

    def check_steps(self):
        steps_limit = config('scan', 'steps_limit')
        n_steps = self.evaluate_steps()
        return n_steps <= steps_limit

    def __call__(self, **kwargs):
        return self(**kwargs)

    @abstractmethod
    def set_scan(self):
        """To be reimplemented. Calculations of all mandatory attributes from the settings"""
        ...

    @abstractmethod
    def get_nav_axes(self) -> List[Axis]:
        """To be reimplemented. Calculations of all navigation axes from attributes"""
        ...

    @abstractmethod
    def get_scan_shape(self) -> Tuple[int]:
        """To be reimplemented. Calculations of all the final shape of the scan"""
        ...

    @abstractmethod
    def get_indexes_from_scan_index(self, scan_index: int) -> Tuple[int]:
        """To be reimplemented. Calculations of indexes within the scan"""
        ...

    def get_info_from_positions(self, positions: np.ndarray):
        """Set mandatory attributes from a ndarray of positions"""
        if positions is not None:
            if len(positions.shape) == 1:
                positions = np.expand_dims(positions, 1)
            axes_unique = []
            for ax in positions.T:
                axes_unique.append(np.unique(ax))
            axes_indexes = np.zeros_like(positions, dtype=int)
            for ind in range(positions.shape[0]):
                for ind_pos, pos in enumerate(positions[ind]):
                    axes_indexes[ind, ind_pos] = mutils.find_index(axes_unique[ind_pos], pos)[0][0]

            self.n_axes = len(axes_unique)
            self.axes_unique = axes_unique
            self.axes_indexes = axes_indexes
            self.positions = positions
            self.n_steps = positions.shape[0]

    @abstractmethod
    def evaluate_steps(self):
        """To be reimplemented. Quick evaluation of the number of steps to stop the calculation if the evaluation os above the
        configured limit
        """
        ...

    def update_model(self):
        """Method to reimplement and use for scanners using table_view types Parameters to set and apply the underlying
        model

        See Also
        --------
        SequentialScanner, TabularScanner, pymodaq.utils.parameter.pymodaq_ptypes.tableview
        """
        ...

    def save_scan_parameters(self):
        if self.save_settings:
            self.config_saver_loader.save_config()

    @abstractmethod
    def update_from_scan_selector(self, scan_selector: Selector):
        """To be reimplemented. Process the Selector object to set the Scanner settings

        See Also
        --------
        Selector, ScanSelector
        """
        ...


class ScannerFactory(ObjectFactory):
    """Factory class registering and storing Scanners"""

    @classmethod
    def register(cls) -> Callable:
        """ To be used as a decorator

        Register in the class registry a new scanner class using its 2 identifiers: scan_type and scan_sub_type
        """
        def inner_wrapper(wrapped_class: ScannerBase) -> Callable:
            if cls.__name__ not in cls._builders:
                cls._builders[cls.__name__] = {}
            key = wrapped_class.scan_type
            sub_key = wrapped_class.scan_subtype

            if key not in cls._builders[cls.__name__]:
                cls._builders[cls.__name__][key] = {}
            if sub_key not in cls._builders[cls.__name__][key]:
                cls._builders[cls.__name__][key][sub_key] = wrapped_class
            else:
                logger.warning(f'The {cls.__name__}/{key}/{sub_key} builder is already registered. Replacing it')
            return wrapped_class

        return inner_wrapper

    @classmethod
    def create(cls, key, sub_key, **kwargs) -> ScannerBase:
        builder = cls._builders[cls.__name__].get(key).get(sub_key)
        if not builder:
            raise ValueError(key)
        return builder(**kwargs)

    def get(self, scan_type, scan_sub_type, **kwargs):
        return self.create(scan_type, scan_sub_type, **kwargs)

    def scan_types(self) -> List[str]:
        """Returns the list of scan types, main identifier of a given scanner"""
        return sorted(list(self.builders[self.__class__.__name__].keys()))

    def scan_sub_types(self, scan_type: str) -> List[str]:
        """Returns the list of scan subtypes, second identifier of a given scanner of type scan_type"""
        return list(self.builders[self.__class__.__name__][scan_type].keys())


# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Callable, Union, List, Tuple, TYPE_CHECKING


import numpy as np

from pymodaq.utils.managers.parameter_manager import ParameterManager, Parameter
from pymodaq.utils.factory import ObjectFactory
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.data import Axis, DataDistribution
from pymodaq.utils.abstract import abstract_attribute
from pymodaq.utils import math_utils as mutils
from pymodaq.utils import config as configmod

if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pymodaq.utils.plotting.scan_selector import Selector


logger = set_logger(get_module_name(__file__))
config = configmod.Config()


class ScanParameterManager(ParameterManager):
    settings_name = 'scanner_settings'

    def __init__(self):
        super().__init__()
        self.settings_tree.header().setVisible(False)
        self.settings_tree.setMinimumHeight(150)


class ScannerBase(ScanParameterManager, metaclass=ABCMeta):
    """Abstract class for all Scanners

    Attributes
    ----------
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
    params: List[dict] = abstract_attribute()
    axes_unique: List[np.ndarray] = abstract_attribute()
    axes_indexes: np.ndarray = abstract_attribute()
    n_steps: int = abstract_attribute()
    n_axes: int = abstract_attribute()
    distribution: DataDistribution = abstract_attribute()

    def __init__(self, actuators: List[DAQ_Move] = None):
        super().__init__()
        self.positions: np.ndarray = None
        self.n_steps = 1
        self._actuators: List[DAQ_Move] = None

        self.actuators = actuators

        self.set_settings_titles()

        if self.check_steps():
            self.set_scan()

    def set_settings_titles(self):
        """Update the settings accordingly with the selected actuators"""
        ...

    @property
    def actuators(self):
        return self._actuators

    @actuators.setter
    def actuators(self, actuators_name: List[DAQ_Move]):
        self._actuators = actuators_name

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
        """To be reimplemented. Quick evaluation of the current numbers of scan steps from the settings
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

    def value_changed(self, param):
        self.evaluate_steps()

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
    def register(cls, key: str, sub_key: str = '') -> Callable:
        def inner_wrapper(wrapped_class: Union[Callable]) -> Callable:
            if cls.__name__ not in cls._builders:
                cls._builders[cls.__name__] = {}
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


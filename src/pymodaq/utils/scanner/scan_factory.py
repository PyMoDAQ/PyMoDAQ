# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""
from abc import ABCMeta, abstractmethod
from typing import Callable, Union, List

import numpy as np

from pymodaq.utils.managers.parameter_manager import ParameterManager
from pymodaq.utils.factory import ObjectFactory
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.abstract import abstract_attribute
from pymodaq.utils import math_utils as mutils
from pymodaq.utils import config as configmod


logger = set_logger(get_module_name(__file__))
config = configmod.Config()

SCANNER_SETTINGS_NAME = 'scanner_settings'


class ScanParameterManager(ParameterManager):
    def __init__(self):
        super().__init__()
        self.settings.setName(SCANNER_SETTINGS_NAME)


class ScannerBase(metaclass=ABCMeta):
    """

    Parameters
    ----------
    n_axes
    starts
    stops
    steps
    positions

    Attributes
    ----------
    params: List[dict]
    """
    params: list = abstract_attribute()
    axes_unique: List[np.ndarray] = abstract_attribute()
    axes_indexes: np.ndarray = abstract_attribute()
    n_steps = abstract_attribute()
    n_axes = abstract_attribute()

    def __init__(self):
        self.positions: np.ndarray = None
        self.n_steps = 1

        if self.check_steps():
            self.set_scan()

    def check_steps(self):
        steps_limit = config('scan', 'steps_limit')
        n_steps = self.evaluate_steps()
        return n_steps <= steps_limit

    def __call__(self, **kwargs):
        return self(**kwargs)

    @abstractmethod
    def set_scan(self):
        ...

    def get_info_from_positions(self, positions: np.ndarray):
        """Get a scan infos from a ndarray of positions"""
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

            self.n_axes = positions.shape[0]
            self.axes_unique = axes_unique
            self.axes_indexes = axes_indexes
            self.positions = positions

    @abstractmethod
    def evaluate_steps(self):
        ...


class ScannerFactory(ObjectFactory):

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

    def scan_types(self):
        return list(self.builders[self.__class__.__name__].keys())

    def scan_sub_types(self, scan_type: str):
        return list(self.builders[self.__class__.__name__][scan_type].keys())




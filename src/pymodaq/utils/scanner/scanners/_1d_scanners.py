# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""
from typing import List, Tuple

import numpy as np
from pymodaq.utils.data import Axis
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils import math_utils as mutils
from pymodaq.utils import config as configmod


from ..scan_factory import ScannerFactory, ScannerBase, ScanParameterManager

logger = set_logger(get_module_name(__file__))
config = configmod.Config()


@ScannerFactory.register('Scan1D', 'Linear')
class Scan1DLinear(ScannerBase):
    params = [
        {'title': 'Start:', 'name': 'start', 'type': 'float', 'value': config('scan', 'scan1D', 'start')},
        {'title': 'Stop:', 'name': 'stop', 'type': 'float', 'value': config('scan', 'scan1D', 'stop')},
        {'title': 'Step:', 'name': 'step', 'type': 'float', 'value': config('scan', 'scan1D', 'step')}
        ]
    n_axes = 1

    def __init__(self, actuators: List = None, **_ignored):
        ScannerBase.__init__(self, actuators=actuators)

    def set_scan(self):
        self.positions = mutils.linspace_step(self.settings['start'], self.settings['stop'],
                                              self.settings['step'])
        self.get_info_from_positions(self.positions)

    def evaluate_steps(self) -> int:
        n_steps = int(np.abs((self.settings['stop'] - self.settings['start']) / self.settings['step']) + 1)
        return n_steps

    def get_nav_axes(self) -> List[Axis]:
        return [Axis(label=f'{self.actuators[0].title}',
                     units=f'{self.actuators[0].units}',
                     data=np.squeeze(self.positions))]

    def get_scan_shape(self) -> Tuple[int]:
        return len(self.positions),

    def get_indexes_from_scan_index(self, scan_index: int) -> Tuple[int]:
        """To be reimplemented. Calculations of indexes within the scan"""
        return tuple(self.axes_indexes[scan_index])


@ScannerFactory.register('Scan1D', 'Random')
class Scan1DRandom(Scan1DLinear):
    def __init__(self, actuators: List = None, **_ignored):
        super().__init__(actuators=actuators)

    def set_scan(self):
        self.positions = mutils.linspace_step(self.settings['start'], self.settings['stop'],
                                              self.settings['step'])
        np.random.shuffle(self.positions)
        self.get_info_from_positions(self.positions)


try:
    import adaptive


    @ScannerFactory.register('Scan1D', 'Adaptive')
    class Scan1DAdaptive(Scan1DLinear):
        params = [
            {'title': 'Loss type', 'name': 'scan_loss', 'type': 'list',
             'limits': ['default', 'curvature', 'uniform'], 'tip': 'Type of loss used by the algo. to determine next points'},
            {'title': 'Start:', 'name': 'start', 'type': 'float', 'value': config('scan', 'scan1D', 'start')},
            {'title': 'Stop:', 'name': 'stop', 'type': 'float', 'value': config('scan', 'scan1D', 'stop')},
            ]

        def __init__(self, actuators: List = None, **_ignored):
            super().__init__(actuators=actuators)

        def set_scan(self):
            self.axes_unique = [np.array([])]
            self.axes_indexes = np.array([], dtype=np.int)
            self.positions = np.array([self.settings['start'], self.settings['stop']])

        def evaluate_steps(self) -> int:
            return 1

        def get_nav_axes(self) -> List[Axis]:
            return [Axis(label=f'{self.actuators[0].mod_name} axis',
                         units=f'{self.actuators[0].units}',
                         data=self.positions[0])]

        def get_scan_shape(self) -> Tuple[int]:
            return len(self.positions),

except ModuleNotFoundError:
    logger.info('adaptive module is not present, no adaptive scan possible')


# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""
import numpy as np
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils import math_utils as mutils
from pymodaq.utils import config as configmod

from .scan_factory import ScannerFactory, ScannerBase, ScanParameterManager

logger = set_logger(get_module_name(__file__))
config = configmod.Config()


@ScannerFactory.register('Scan2D', 'Linear')
class Scan2DLinear(ScannerBase, ScanParameterManager):
    params = [{'title': 'Start Ax1:', 'name': 'start_axis1', 'type': 'float',
               'value': config('scan', 'scan2D', 'start1')},
              {'title': 'Start Ax2:', 'name': 'start_axis2', 'type': 'float',
               'value': config('scan', 'scan2D', 'start2')},
              {'title': 'Step Ax1:', 'name': 'step_axis1', 'type': 'float',
               'value': config('scan', 'scan2D', 'step1')},
              {'title': 'Step Ax2:', 'name': 'step_axis2', 'type': 'float',
               'value': config('scan', 'scan2D', 'step2')},
              {'title': 'Stop Ax1:', 'name': 'stop_axis1', 'type': 'float',
               'value': config('scan', 'scan2D', 'stop1')},
              {'title': 'Stop Ax2:', 'name': 'stop_axis2', 'type': 'float',
               'value': config('scan', 'scan2D', 'stop2')},
              ]
    n_axes = 2

    def __init__(self, positions: np.ndarray = None):
        ScanParameterManager.__init__(self)
        ScannerBase.__init__(self, positions)

    def get_pos(self):
        starts = np.array([self.settings['start_axis1'], self.settings['start_axis2']])
        stops = np.array([self.settings['stop_axis1'], self.settings['stop_axis2']])
        steps = np.array([self.settings['step_axis1'], self.settings['step_axis2']])
        return starts, stops, steps

    def evaluate_steps(self) -> int:
        starts, stops, steps = self.get_pos()
        n_steps = 1
        for ind in range(starts.size):
            n_steps *= np.abs((stops[ind] - starts[ind]) / steps[ind]) + 1
        return n_steps

    def set_scan(self):
        starts, stops, steps = self.get_pos()
        if np.any(np.abs(steps) < 1e-12) or \
                np.any(np.sign(stops - starts) != np.sign(steps)) or \
                np.any(starts == stops):

            return np.array([starts])

        else:
            axis_1_unique = mutils.linspace_step(starts[0], stops[0], steps[0])
            axis_2_unique = mutils.linspace_step(starts[1], stops[1], steps[1])

            positions = []
            for ind_x, pos1 in enumerate(axis_1_unique):
                for ind_y, pos2 in enumerate(axis_2_unique):
                    positions.append([pos1, pos2])

        self.get_info_from_positions(np.array(positions))


@ScannerFactory.register('Scan2D', 'LinearBack&Force')
class Scan2DLinearBF(Scan2DLinear):
    def __init__(self, positions: np.ndarray = None):
        super().__init__(positions)

    def set_scan(self):
        starts, stops, steps = self.get_pos()
        if np.any(np.abs(steps) < 1e-12) or \
                np.any(np.sign(stops - starts) != np.sign(steps)) or \
                np.any(starts == stops):

            return np.array([starts])

        else:
            axis_1_unique = mutils.linspace_step(starts[0], stops[0], steps[0])
            axis_2_unique = mutils.linspace_step(starts[1], stops[1], steps[1])

            positions = []
            for ind_x, pos1 in enumerate(axis_1_unique):
                for ind_y, pos2 in enumerate(axis_2_unique):
                    if not mutils.odd_even(ind_x):
                        positions.append([pos1, pos2])
                    else:
                        positions.append([pos1, axis_2_unique[len(axis_2_unique) - ind_y - 1]])

        self.get_info_from_positions(np.array(positions))


@ScannerFactory.register('Scan2D', 'Random')
class Scan2DRandom(Scan2DLinear):
    def __init__(self, positions: np.ndarray = None):
        super().__init__(positions)

    def set_scan(self):
        super().set_scan()
        np.random.shuffle(self.positions)
        self.get_info_from_positions(self.positions)


try:
    import adaptive


    @ScannerFactory.register('Scan2D', 'Adaptive')
    class Scan2DAdaptive(Scan2DLinear):
        params = [
            {'title': 'Loss type', 'name': 'scan_loss', 'type': 'list',
             'limits': ['default', 'curvature', 'uniform'],
             'tip': 'Type of loss used by the algo. to determine next points'},

            {'title': 'Start Ax1:', 'name': 'start_axis1', 'type': 'float',
             'value': config('scan', 'scan2D', 'start1')},
            {'title': 'Start Ax2:', 'name': 'start_axis2', 'type': 'float',
             'value': config('scan', 'scan2D', 'start2')},
            {'title': 'Stop Ax1:', 'name': 'stop_axis1', 'type': 'float',
             'value': config('scan', 'scan2D', 'stop1')},
            {'title': 'Stop Ax2:', 'name': 'stop_axis2', 'type': 'float',
             'value': config('scan', 'scan2D', 'stop2')},
            ]

        def __init__(self, positions: np.ndarray = None):
            super().__init__(positions)

        def set_scan(self):

            self.axes_unique = [np.array([]), np.array([])]
            self.axes_indexes = np.array([], dtype=np.int)
            self.positions = np.zeros((0, 2))

        def evaluate_steps(self) -> int:
            return 1

except ModuleNotFoundError:
    logger.info('adaptive module is not present, no adaptive scan possible')


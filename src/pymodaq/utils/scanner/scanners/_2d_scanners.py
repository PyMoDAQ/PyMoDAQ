# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""
from typing import List, Tuple

import numpy as np
from pymodaq.utils.data import Axis, DataDistribution
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils import math_utils as mutils
from pymodaq.utils import config as configmod
from pymodaq.utils.plotting.scan_selector import Selector

from ..scan_factory import ScannerFactory, ScannerBase, ScanParameterManager

logger = set_logger(get_module_name(__file__))
config = configmod.Config()


@ScannerFactory.register('Scan2D', 'Linear')
class Scan2DLinear(ScannerBase):
    params = [{'title': 'Start Ax1:', 'name': 'start_axis1', 'type': 'float',
               'value': config('scan', 'scan2D', 'linear', 'start1')},
              {'title': 'Start Ax2:', 'name': 'start_axis2', 'type': 'float',
               'value': config('scan', 'scan2D', 'linear', 'start2')},
              {'title': 'Step Ax1:', 'name': 'step_axis1', 'type': 'float',
               'value': config('scan', 'scan2D', 'linear', 'step1')},
              {'title': 'Step Ax2:', 'name': 'step_axis2', 'type': 'float',
               'value': config('scan', 'scan2D', 'linear', 'step2')},
              {'title': 'Stop Ax1:', 'name': 'stop_axis1', 'type': 'float',
               'value': config('scan', 'scan2D', 'linear', 'stop1')},
              {'title': 'Stop Ax2:', 'name': 'stop_axis2', 'type': 'float',
               'value': config('scan', 'scan2D', 'linear', 'stop2')},
              ]
    n_axes = 2
    distribution = DataDistribution['uniform']

    def __init__(self, actuators: List = None, **_ignored):
        super().__init__(actuators=actuators)
        self.axes_unique = []

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
        return int(n_steps)

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

    def set_settings_titles(self):
        if len(self.actuators) == 2:
            self.settings.child('start_axis1').setOpts(title=f'{self.actuators[0].title} start:')
            self.settings.child('stop_axis1').setOpts(title=f'{self.actuators[0].title} stop:')
            self.settings.child('step_axis1').setOpts(title=f'{self.actuators[0].title} step:')
            self.settings.child('start_axis2').setOpts(title=f'{self.actuators[1].title} start:')
            self.settings.child('stop_axis2').setOpts(title=f'{self.actuators[1].title} stop:')
            self.settings.child('step_axis2').setOpts(title=f'{self.actuators[1].title} step:')

    def get_nav_axes(self) -> List[Axis]:
        return [Axis(label=f'{act.title}',
                     units=f'{act.units}',
                     data=self.axes_unique[ind],
                     index=ind) for ind, act in enumerate(self.actuators)]

    def get_scan_shape(self) -> Tuple[int]:
        return tuple([len(axis) for axis in self.axes_unique])

    def get_indexes_from_scan_index(self, scan_index: int) -> Tuple[int]:
        """To be reimplemented. Calculations of indexes within the scan"""
        return tuple(self.axes_indexes[scan_index])

    def update_from_scan_selector(self, scan_selector: Selector):
        coordinates = scan_selector.get_coordinates()
        if coordinates.shape == (2, 2):
            self.settings.child('start_axis1').setValue(coordinates[0, 0])
            self.settings.child('start_axis2').setValue(coordinates[0, 1])
            self.settings.child('stop_axis1').setValue(coordinates[1, 0])
            self.settings.child('stop_axis2').setValue(coordinates[1, 1])


@ScannerFactory.register('Scan2D', 'LinearBack&Force')
class Scan2DLinearBF(Scan2DLinear):
    def __init__(self, actuators: List = None, **_ignored):
        super().__init__(actuators=actuators)

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
    def __init__(self, actuators: List = None, **_ignored):
        super().__init__(actuators=actuators)

    def set_scan(self):
        super().set_scan()
        np.random.shuffle(self.positions)
        self.get_info_from_positions(self.positions)


@ScannerFactory.register('Scan2D', 'Spiral')
class Scan2DSpiral(Scan2DLinear):
    params = [{'title': 'Center Ax1:', 'name': 'center_axis1', 'type': 'float',
               'value': config('scan', 'scan2D', 'spiral', 'center1')},
              {'title': 'Center Ax2:', 'name': 'center_axis2', 'type': 'float',
               'value': config('scan', 'scan2D', 'spiral', 'center2')},
              {'title': 'Rmax Ax1:', 'name': 'rmax_axis1', 'type': 'float',
               'value': config('scan', 'scan2D', 'spiral', 'rmax1')},
              {'title': 'Rmax Ax2:', 'name': 'rmax_axis2', 'type': 'float',
               'value': config('scan', 'scan2D', 'spiral', 'rmax2')},
              {'title': 'Npts/axis', 'name': 'npts_by_axis', 'type': 'int', 'min': 1,
               'value': config('scan', 'scan2D', 'spiral', 'npts')},
              {'title': 'Step Ax1:', 'name': 'step_axis1', 'type': 'float', 'value': 0., 'readonly': True},
              {'title': 'Step Ax2:', 'name': 'step_axis2', 'type': 'float', 'value': 0., 'readonly': True},
              ]

    def __init__(self, actuators: List = None, **_ignored):
        super().__init__(actuators=actuators)

    def set_settings_titles(self):
        if len(self.actuators) == 2:
            self.settings.child('center_axis1').setOpts(title=f'Center {self.actuators[0].title}:')
            self.settings.child('rmax_axis1').setOpts(title=f'Rmax {self.actuators[0].title}:')
            self.settings.child('step_axis1').setOpts(title=f'Step {self.actuators[0].title}:')
            self.settings.child('center_axis2').setOpts(title=f'Center {self.actuators[1].title}:')
            self.settings.child('rmax_axis2').setOpts(title=f'Rmax {self.actuators[1].title}:')
            self.settings.child('step_axis2').setOpts(title=f'Step {self.actuators[1].title}:')

    def value_changed(self, param):
        starts, rmaxs, rsteps = self.get_pos()
        self.settings.child('step_axis1').setValue(rsteps[0])
        self.settings.child('step_axis2').setValue(rsteps[1])

    def get_pos(self):
        """Get centers, radius and n steps from settings

        Returns
        ----------
        centers: np.ndarray
            containing the center positions of the scan
        rmaxs: np.ndarray
            containing the maximum radius (ellipse axes) in each direction
        r_steps: np.ndarray
            steps size in both directions
        """
        centers = np.array([self.settings['center_axis1'], self.settings['center_axis2']])
        rmaxs = np.array([self.settings['rmax_axis1'], self.settings['rmax_axis2']])
        r_steps = 2 * rmaxs / self.settings['npts_by_axis']
        return centers, rmaxs, r_steps

    def evaluate_steps(self) -> int:
        return int(self.settings['npts_by_axis'] + 1) ** 2

    def set_scan(self):
        starts, rmaxs, rsteps = self.get_pos()

        if np.any(np.array(rmaxs) == 0) or np.any(np.abs(rmaxs) < 1e-12) or np.any(np.abs(rsteps) < 1e-12):
            positions = np.array([starts])

        else:
            Nlin = self.settings['npts_by_axis'] / 2
            axis_1_indexes = [0]
            axis_2_indexes = [0]
            ind = 0
            flag = True

            while flag:
                if mutils.odd_even(ind):
                    step = 1
                else:
                    step = -1
                if flag:

                    for ind_step in range(ind):
                        axis_1_indexes.append(axis_1_indexes[-1] + step)
                        axis_2_indexes.append(axis_2_indexes[-1])
                        if len(axis_1_indexes) >= (2 * Nlin + 1) ** 2:
                            flag = False
                            break
                if flag:
                    for ind_step in range(ind):
                        axis_1_indexes.append(axis_1_indexes[-1])
                        axis_2_indexes.append(axis_2_indexes[-1] + step)
                        if len(axis_1_indexes) >= (2 * Nlin + 1) ** 2:
                            flag = False
                            break
                ind += 1

            positions = []
            for ind in range(len(axis_1_indexes)):
                positions.append(np.array([axis_1_indexes[ind] * rsteps[0] + starts[0],
                                           axis_2_indexes[ind] * rsteps[1] + starts[1]]))

        self.get_info_from_positions(np.array(positions))

    def update_from_scan_selector(self, scan_selector: Selector):
        coordinates = scan_selector.get_coordinates()
        if coordinates.shape == (2, 2):
            self.settings.child('center_axis1').setValue((coordinates[0, 0] + coordinates[1, 0]) / 2)
            self.settings.child('center_axis2').setValue((coordinates[0, 1] + coordinates[1, 1]) / 2)
            self.settings.child('rmax_axis1').setValue(abs(coordinates[1, 0] - coordinates[0, 0]) / 2)
            self.settings.child('rmax_axis2').setValue(abs(coordinates[1, 1] - coordinates[0, 1]) / 2)


try:
    import adaptive

    @ScannerFactory.register('Scan2D', 'Adaptive')
    class Scan2DAdaptive(Scan2DLinear):
        params = [
            {'title': 'Loss type', 'name': 'scan_loss', 'type': 'list',
             'limits': ['default', 'curvature', 'uniform'],
             'tip': 'Type of loss used by the algo. to determine next points'},

            {'title': 'Start Ax1:', 'name': 'start_axis1', 'type': 'float',
             'value': config('scan', 'scan2D', 'linear', 'start1')},
            {'title': 'Start Ax2:', 'name': 'start_axis2', 'type': 'float',
             'value': config('scan', 'scan2D', 'linear', 'start2')},
            {'title': 'Stop Ax1:', 'name': 'stop_axis1', 'type': 'float',
             'value': config('scan', 'scan2D', 'linear', 'stop1')},
            {'title': 'Stop Ax2:', 'name': 'stop_axis2', 'type': 'float',
             'value': config('scan', 'scan2D', 'linear', 'stop2')},
            ]
        distribution = DataDistribution['spread']

        def __init__(self, actuators: List = None, **_ignored):
            super().__init__(actuators=actuators)

        def set_scan(self):

            self.axes_unique = [np.array([]), np.array([])]
            self.axes_indexes = np.array([], dtype=int)
            self.positions = np.zeros((0, 2))

        def evaluate_steps(self) -> int:
            return 1

        def get_nav_axes(self) -> List[Axis]:
            return [Axis(label=f'{act.mod_name} axis',
                         units=f'{act.units}',
                         data=self.positions[:, ind],
                         index=ind) for ind, act in enumerate(self.actuators)]

        def get_scan_shape(self) -> Tuple[int]:
            return ()  # unknown shape

except ModuleNotFoundError:
    logger.info('adaptive module is not present, no adaptive scan possible')


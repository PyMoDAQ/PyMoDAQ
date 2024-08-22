# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""
from typing import List, Tuple, TYPE_CHECKING

import numpy as np
from pymodaq_data.data import Axis, DataDistribution
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import math_utils as mutils
from pymodaq_utils import config as configmod
from pymodaq.utils.scanner.scan_selector import Selector

from ..scan_factory import ScannerFactory, ScannerBase, ScanParameterManager

logger = set_logger(get_module_name(__file__))
config = configmod.Config()

if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move


class Scan2DBase(ScannerBase):    
    params = [{'title': 'Ax1:', 'name': 'axis1', 'type': 'group',
                'children':[]
                }, 
                {'title': 'Ax2:', 'name': 'axis2', 'type': 'group',
                'children':[]
                }, 
                ]
    axes = ('axis1','axis2')    
    n_axes = 2
    def __init__(self, actuators: List['DAQ_Move'] = None, **_ignored):
        super().__init__(actuators=actuators)
        self.axes_unique = []

        
@ScannerFactory.register()
class Scan2DLinear(Scan2DBase):    
    
    params = [{'title': 'Ax1:', 'name': 'axis1', 'type': 'group',
               'children':[
              {'title': 'Start Ax1:', 'name': 'start_axis1', 'type': 'float',
               'value': 0.},
              {'title': 'Stop Ax1:', 'name': 'stop_axis1', 'type': 'float',
               'value': 1.},
              {'title': 'Step Ax1:', 'name': 'step_axis1', 'type': 'float',
               'value': 0.1},
              ]}, 
              {'title': 'Ax2:', 'name': 'axis2', 'type': 'group',
               'children':[
              {'title': 'Start Ax2:', 'name': 'start_axis2', 'type': 'float',
               'value': 0.},
              {'title': 'Stop Ax2:', 'name': 'stop_axis2', 'type': 'float',
               'value': 1.},
              {'title': 'Step Ax2:', 'name': 'step_axis2', 'type': 'float',
               'value': 0.1},
               ]},
              ]    
    n_axes = 2
    distribution = DataDistribution['uniform']
    scan_type = 'Scan2D'
    scan_subtype = 'Linear'

    def __init__(self, actuators: List['DAQ_Move'] = None, **_ignored):
        super().__init__(actuators=actuators)

    def get_pos(self):
        starts = np.array([self.settings[ax, f'start_{ax}'] for ax in self.axes])
        stops = np.array([self.settings[ax, f'stop_{ax}'] for ax in self.axes])
        steps = np.array([self.settings[ax, f'step_{ax}'] for ax in self.axes])
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
            for i,ax in enumerate(self.axes):            
                title = self.actuators[i].title
                self.settings.child(ax).setOpts(title=title)                
                self.settings.child(ax, f'start_{ax}').setOpts(title=f'{title} start:')
                self.settings.child(ax, f'stop_{ax}').setOpts(title=f'{title} stop:')
                self.settings.child(ax, f'step_{ax}').setOpts(title=f'{title} step:')

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
            for i,ax in enumerate(self.axes):            
                self.settings.child(ax,f'start_{ax}').setValue(coordinates[0, i])
                self.settings.child(ax,f'stop_{ax}').setValue(coordinates[1, i])


@ScannerFactory.register()
class Scan2DLinearBF(Scan2DLinear):
    scan_subtype = 'LinearBackForce'

    def __init__(self, actuators: List['DAQ_Move'] = None, **_ignored):
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


@ScannerFactory.register()
class Scan2DRandom(Scan2DLinear):
    scan_subtype = 'Random'

    def __init__(self, actuators: List['DAQ_Move'] = None, **_ignored):
        super().__init__(actuators=actuators)

    def set_scan(self):
        super().set_scan()
        np.random.shuffle(self.positions)
        self.get_info_from_positions(self.positions)


@ScannerFactory.register()
class Scan2DSpiral(Scan2DLinear):
    scan_subtype = 'Spiral'
    params = [{'title': 'Npts/axis', 'name': 'npts_by_axis', 'type': 'int', 'min': 1,
               'value': 10},
              {'title': 'Ax1:', 'name': 'axis1', 'type': 'group',
               'children': [
                   {'title': 'Center Ax1:', 'name': 'center_axis1', 'type': 'float',
                    'value': 0.},
                   {'title': 'Rmax Ax1:', 'name': 'rmax_axis1', 'type': 'float',
                    'value': 5.},
                   {'title': 'Step Ax1:', 'name': 'step_axis1', 'type': 'float',
                    'value': 0., 'readonly': True},
               ]},
              {'title': 'Ax2:', 'name': 'axis2', 'type': 'group',
               'children': [
                   {'title': 'Center Ax2:', 'name': 'center_axis2', 'type': 'float',
                    'value': 0.},
                   {'title': 'Rmax Ax2:', 'name': 'rmax_axis2', 'type': 'float',
                    'value': 5.},
                   {'title': 'Step Ax2:', 'name': 'step_axis2', 'type': 'float',
                    'value': 0., 'readonly': True},
               ]},
              ]  
   
    def __init__(self, actuators: List['DAQ_Move'] = None, **_ignored):
        super().__init__(actuators=actuators)

    def set_settings_titles(self):
        if len(self.actuators) == 2:
            for i,ax in enumerate(self.axes):            
                title = self.actuators[i].title
                self.settings.child(ax).setOpts(title=title)                
                self.settings.child(ax, f'center_{ax}').setOpts(title=f'{title} center:')
                self.settings.child(ax, f'rmax_{ax}').setOpts(title=f'{title} rmax:')
                self.settings.child(ax, f'step_{ax}').setOpts(title=f'{title} step:')

    def value_changed(self, param):
        starts, rmaxs, rsteps = self.get_pos()
        for i,ax in enumerate(self.axes):            
                self.settings.child(ax,f'step_{ax}').setValue(rsteps[i])
        # self.settings.child('step_axis2').setValue(rsteps[1])

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
        centers = np.array([self.settings[ax, f'center_{ax}'] for ax in self.axes])
        rmaxs = np.array([self.settings[ax, f'rmax_{ax}'] for ax in self.axes])
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
            for i,ax in enumerate(self.axes):            
                self.settings.child(ax, f'center_{ax}').setValue(
                    (coordinates[0, i] + coordinates[1, i]) / 2)
                self.settings.child(ax, f'rmax_{ax}').setValue(
                    (coordinates[0, i] - coordinates[1, i]) / 2)


try:
    import adaptive

    @ScannerFactory.register()
    class Scan2DAdaptive(Scan2DLinear):
        scan_subtype = 'Adaptive'

        params = [
            {'title': 'Loss type', 'name': 'scan_loss', 'type': 'list',
             'limits': ['default', 'curvature', 'uniform'],
             'tip': 'Type of loss used by the algo. to determine next points'},

            {'title': 'Ax1:', 'name': 'axis1', 'type': 'group',
               'children':[
              {'title': 'Start Ax1:', 'name': 'start_axis1', 'type': 'float',
               'value': config('scan', 'scan2D', 'linear', 'start1')},
              {'title': 'Stop Ax1:', 'name': 'stop_axis1', 'type': 'float',
               'value': config('scan', 'scan2D', 'linear', 'stop1')},              
              {'title': 'Step Ax1:', 'name': 'step_axis1', 'type': 'float',
               'value': config('scan', 'scan2D', 'linear', 'step1')},
              ]}, 
              {'title': 'Ax2:', 'name': 'axis2', 'type': 'group',
               'children':[
              {'title': 'Start Ax2:', 'name': 'start_axis2', 'type': 'float',
               'value': config('scan', 'scan2D', 'linear', 'start2')},
              {'title': 'Stop Ax2:', 'name': 'stop_axis2', 'type': 'float',
               'value': config('scan', 'scan2D', 'linear', 'stop2')},              
              {'title': 'Step Ax2:', 'name': 'step_axis2', 'type': 'float',
               'value': config('scan', 'scan2D', 'linear', 'step2')},              
               ]},
            ]
        distribution = DataDistribution['spread']

        def __init__(self, actuators: List['DAQ_Move'] = None, **_ignored):
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


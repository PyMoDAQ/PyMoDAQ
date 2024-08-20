# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""
from typing import List, Tuple, Any, TYPE_CHECKING
import re
import numpy as np

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import math_utils as mutils
from pymodaq_utils import config as configmod

from pymodaq_data.data import Axis, DataDistribution

from pymodaq.utils.scanner.scan_selector import Selector

from ..scan_factory import ScannerFactory, ScannerBase, ScanParameterManager

if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move

logger = set_logger(get_module_name(__file__))
config = configmod.Config()


class Scan1DBase(ScannerBase):
    scan_type = 'Scan1D'

    params = []
    n_axes = 1
    distribution = DataDistribution['uniform']

    def __init__(self, actuators: List = None, **_ignored):
        super().__init__(actuators=actuators)

    def get_nav_axes(self) -> List[Axis]:
        return [Axis(label=f'{self.actuators[0].title}',
                     units=f'{self.actuators[0].units}',
                     data=np.squeeze(self.positions))]

    def get_scan_shape(self) -> Tuple[int]:
        return len(self.positions),

    def get_indexes_from_scan_index(self, scan_index: int) -> Tuple[int]:
        """To be reimplemented. Calculations of indexes within the scan"""
        return (scan_index,)

    def update_from_scan_selector(self, scan_selector: Selector):
        pass


@ScannerFactory.register()
class Scan1DLinear(Scan1DBase):
    """ Defines a linear scan between start and stop values with steps of length defined in the step setting"""

    scan_subtype = 'Linear'
    params = [
        {'title': 'Start:', 'name': 'start', 'type': 'float', 'value': 0.},
        {'title': 'Stop:', 'name': 'stop', 'type': 'float', 'value': 1.},
        {'title': 'Step:', 'name': 'step', 'type': 'float', 'value': 0.1}
        ]
    n_axes = 1
    distribution = DataDistribution['uniform']

    def __init__(self, actuators: List['DAQ_Move'] = None, **_ignored):
        super().__init__(actuators=actuators)

    def set_scan(self):
        self.positions = mutils.linspace_step(self.settings['start'], self.settings['stop'],
                                              self.settings['step'])
        self.get_info_from_positions(self.positions)

    def set_settings_titles(self):
        if len(self.actuators) == 1:
            self.settings.child('start').setOpts(title=f'{self.actuators[0].title} start:')
            self.settings.child('stop').setOpts(title=f'{self.actuators[0].title} stop:')
            self.settings.child('step').setOpts(title=f'{self.actuators[0].title} step:')

    def evaluate_steps(self) -> int:
        n_steps = int(np.abs((self.settings['stop'] - self.settings['start']) / self.settings['step']) + 1)
        return n_steps

    def update_from_scan_selector(self, scan_selector: Selector):
        coordinates = scan_selector.get_coordinates()
        if coordinates.shape == (2, 2) or coordinates.shape == (2, 1):
            self.settings.child('start').setValue(coordinates[0, 0])
            self.settings.child('stop').setValue(coordinates[1, 0])


@ScannerFactory.register()
class Scan1DRandom(Scan1DLinear):
    """ Defines a  random linear scan by first initializing a linear one between start and stop values with
    steps of length defined in the step setting, then shuffling the values."""

    scan_subtype = 'Random'

    def __init__(self, actuators: List = None, **_ignored):
        super().__init__(actuators=actuators)

    def set_scan(self):
        self.positions = mutils.linspace_step(self.settings['start'], self.settings['stop'],
                                              self.settings['step'])
        np.random.shuffle(self.positions)
        self.get_info_from_positions(self.positions)
        self.set_settings_titles()

        
@ScannerFactory.register()
class Scan1DSparse(Scan1DBase):
    """ Syntax goes as start:step:stop or with single entry

    * 0:0.2:1 will give [0 0.2 0.4 0.6 0.8 1]
    * 0 will give [0]

    Separate entries with comma or new line:

    * 0:0.2:1,5 will give [0 0.2 0.4 0.6 0.8 1 5]
    * 0:0.2:1,5:1:7 will give [0 0.2 0.4 0.6 0.8 1 5 6 7]
    """

    scan_subtype = 'Sparse'
    params = [
        {'title': 'Parsed string:', 'name': 'parsed_string', 'type': 'text', 'value': '0:0.1:1', }
        ]
    n_axes = 1
    distribution = DataDistribution['uniform']  # because in 1D it doesn't matter is spread or
    # uniform, one can easily plot both types on a regulat 1D plot

    def __init__(self, actuators: List['DAQ_Move'] = None, **_ignored):
        super().__init__(actuators=actuators)
        self.settings.child('parsed_string').setOpts(tip=self.__doc__)

    def set_scan(self):
        try:
            range_strings = re.findall("[^,\s]+", self.settings['parsed_string'])
            series = np.asarray([])
            for range_string in range_strings:
                number_strings = re.findall("[^:]+", range_string)  # Extract the numbers by splitting on :.
                this_range = np.asarray([])
                if len(number_strings) == 3:  # 3 Numbers specify a range
                    start, step, stop = [float(number) for number in number_strings]
                    this_range = mutils.linspace_step(start, stop, step)
                elif len(number_strings) == 1:  # 1 number just specifies a single number
                    this_range = np.asarray([float(number_strings[0])])
                series = np.concatenate((series, this_range))

            self.positions = np.atleast_1d(np.squeeze(series))
            self.get_info_from_positions(self.positions)
        except Exception as e:
            pass  # many things could happen when parsing strings

    def set_settings_titles(self):
        if len(self.actuators) == 1:
            self.settings.child('start').setOpts(title=f'{self.actuators[0].title} start:')

    def evaluate_steps(self) -> int:
        """Quick evaluation of the number of steps to stop the calculation if the evaluation os above the
        configured limit"""
        self.set_scan()  # no possible quick evaluation, easiest to process it
        return self.n_steps

    def set_settings_titles(self):
        if len(self.actuators) == 1:
            self.settings.child('parsed_string').setOpts(title=f'{self.actuators[0].title} Parsed string:')

try:
    import adaptive


    @ScannerFactory.register()
    class Scan1DAdaptive(Scan1DBase):

        scan_subtype = 'Adaptive'
        params = [
            {'title': 'Loss type', 'name': 'scan_loss', 'type': 'list',
             'limits': ['default', 'curvature', 'uniform'], 'tip': 'Type of loss used by the algo. to determine next points'},
            {'title': 'Start:', 'name': 'start', 'type': 'float', 'value': 0.},
            {'title': 'Stop:', 'name': 'stop', 'type': 'float', 'value': 1.},
            ]
        distribution = DataDistribution['spread']

        def __init__(self, actuators: List['DAQ_Move'] = None, **_ignored):
            super().__init__(actuators=actuators)

        def set_scan(self):
            self.axes_unique = [np.array([])]
            self.axes_indexes = np.array([], dtype=int)
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


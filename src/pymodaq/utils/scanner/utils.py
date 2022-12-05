# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""


import numpy as np
from qtpy import QtCore

from pymodaq.utils.plotting.utils.plot_utils import QVector
import pymodaq.utils.math_utils as mutils
from pymodaq.utils import gui_utils as gutils
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.config import Config

logger = set_logger(get_module_name(__file__))
config = Config()


class ScannerException(Exception):
    """Raised when there is an error related to the Scanner class (see pymodaq.da_utils.scanner)"""
    pass


def set_scan_spiral(starts, rmaxs, rsteps, nsteps=None, oversteps=10000):
    """Calculate the positions to describe a spiral type scan, starting from a center position and spiraling out from it

    Parameters
    ----------
    starts: (sequence like) containing the center positions of the scan
    rmaxs: (sequence like) containing the maximum radius (ellipse axes) in each direction
    rsteps: (sequence like) containing the step size for each axis
    nsteps: (int) If not None, this is used together with rsteps to calculate rmaxs
    oversteps: (int) maximum number of calculated steps (stops the steps calculation if over the first power of 2 greater than oversteps)

    Returns
    -------
    ndarray of all positions for each axis

    See Also
    --------
    ScanParameters
    """
    if np.isscalar(rmaxs):
        rmaxs = np.ones(starts.shape) * rmaxs
    else:
        rmaxs = np.array(rmaxs)
    if np.isscalar(rsteps):
        rsteps = np.ones(starts.shape) * rsteps
    else:
        rsteps = np.array(rsteps)

    starts = np.array(starts)

    if nsteps is not None:
        rmaxs = np.rint(nsteps / 2) * rsteps

    if np.any(np.array(rmaxs) == 0) or np.any(np.abs(rmaxs) < 1e-12) or np.any(np.abs(rsteps) < 1e-12):
        positions = np.array([starts])
        return positions

    ind = 0
    flag = True
    oversteps = mutils.greater2n(oversteps)  # make sure the position matrix is still a square

    Nlin = np.trunc(rmaxs / rsteps)
    if not np.all(Nlin == Nlin[0]):
        raise ScannerException(f'For Spiral 2D scans both axis should have same length, here: {Nlin.shape}')
    else:
        Nlin = Nlin[0]

    axis_1_indexes = [0]
    axis_2_indexes = [0]
    while flag:
        if mutils.odd_even(ind):
            step = 1
        else:
            step = -1
        if flag:

            for ind_step in range(ind):
                axis_1_indexes.append(axis_1_indexes[-1] + step)
                axis_2_indexes.append(axis_2_indexes[-1])
                if len(axis_1_indexes) >= (2 * Nlin + 1) ** 2 or len(axis_1_indexes) >= oversteps:
                    flag = False
                    break
        if flag:
            for ind_step in range(ind):

                axis_1_indexes.append(axis_1_indexes[-1])
                axis_2_indexes.append(axis_2_indexes[-1] + step)
                if len(axis_1_indexes) >= (2 * Nlin + 1) ** 2 or len(axis_1_indexes) >= oversteps:
                    flag = False
                    break
        ind += 1

    positions = []
    for ind in range(len(axis_1_indexes)):
        positions.append(np.array([axis_1_indexes[ind] * rsteps[0] + starts[0],
                                   axis_2_indexes[ind] * rsteps[1] + starts[1]]))

    return np.array(positions)


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
    def __init__(self, Nsteps=0, positions=None, axes_indexes=None, axes_unique=None, **kwargs):
        self.Nsteps = Nsteps
        self.positions = positions
        self.axes_indexes = axes_indexes
        self.axes_unique = axes_unique
        for k in kwargs:
            setattr(self, k, kwargs[k])

    def __repr__(self):
        if self.positions is not None:
            return f'[ScanInfo with {self.Nsteps} positions of shape {self.positions.shape})'
        else:
            return '[ScanInfo with position is None)'


class ScanParameters:
    """Utility class to define and store information about scans to be done

    Composition of a ScanInfo object. You can directly access the ScanInfo attributes from ScanParameters

    Parameters
    ----------
    Naxes: int
        number of axes used to do the scan
    scan_type: str
        one value of the ScanType list items
    scan_subtype: str
        one value of the SCAN_SUBTYPES dict items for the scan_type key
    starts: list of floats
        list of starts position of each axis
    stops: list of floats
        list of stops position of each axis
    steps: list of floats
        list of steps position of each axis
    positions: ndarray
        containing the positions already calculated from some method. If not None, this is used to define the scan_info
        (otherwise one use the starts, stops and steps)
    adaptive_loss

    Attributes
    ----------
    Naxes
    scan_info: ScanInfo
    scan_type: str
    scan_subtype: str
    starts
    stops
    steps

    See Also
    --------
    ScanInfo, SCAN_TYPES, SCAN_SUBTYPES
    """

    def __init__(self, Naxes=1, scan_type='Scan1D', scan_subtype='Linear', starts=None, stops=None, steps=None,
                 positions=None, adaptive_loss=None):
        self.Naxes = Naxes
        if scan_type not in ScanType.names():
            raise ValueError(
                f'Chosen scan_type value ({scan_type}) is not possible. Should be among : {str(ScanType.names())}')
        if scan_subtype not in SCAN_SUBTYPES[scan_type]['limits']:
            raise ValueError(
                f'Chosen scan_subtype value ({scan_subtype}) is not possible. Should be among'
                f' : {str(SCAN_SUBTYPES[scan_type]["limits"])}')
        self.scan_type = scan_type
        self.scan_subtype = scan_subtype
        self.adaptive_loss = adaptive_loss
        self.vectors = None

        # if positions is not None:
        #     self.starts = np.min(positions, axis=0)
        #     self.stops = np.max(positions, axis=0)
        # else:
        self.starts = starts
        self.stops = stops

        self.steps = steps

        self.scan_info = ScanInfo(Nsteps=0, positions=positions, adaptive_loss=adaptive_loss)

        self.set_scan()

    def __getattr__(self, item):
        if item == 'Nsteps':
            return self.scan_info.Nsteps
        elif item == 'positions':
            return self.scan_info.positions
        elif item == 'axes_indexes':
            return self.scan_info.axes_indexes
        elif item == 'axes_unique':
            return self.scan_info.axes_unique
        else:
            if hasattr(self.scan_info, item):
                return getattr(self.scan_info, item)
            else:
                raise ValueError(f'no attribute named {item}')

    def get_info_from_positions(self, positions):
        """Get a ScanInfo object from a ndarray of positions"""
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

            return ScanInfo(Nsteps=positions.shape[0], axes_unique=axes_unique,
                            axes_indexes=axes_indexes, positions=positions, adaptive_loss=self.adaptive_loss)
        else:
            return ScanInfo()

    def set_scan(self):
        """Process the parameters to calculate all the positions

        In case the number of steps is higher that the configured steps limit returns an empty ScanInfo with only the
        the calculated number of steps (for further warning to the user)

        Returns
        -------
        ScanInfo
        """
        steps_limit = config('scan', 'steps_limit')
        Nsteps = self.evaluate_steps()
        if Nsteps > steps_limit:
            self.scan_info = ScanInfo(Nsteps=Nsteps)
            return self.scan_info

        if self.scan_type == "Scan1D":
            if self.positions is not None:
                positions = self.positions
            else:
                positions = mutils.linspace_step(self.starts[0], self.stops[0], self.steps[0])

            if self.scan_subtype == "Linear":
                self.scan_info = self.get_info_from_positions(positions)

            elif self.scan_subtype == 'Linear back to start':
                positions = np.insert(positions, range(1, len(positions) + 1), positions[0], axis=0)
                self.scan_info = self.get_info_from_positions(positions)

            elif self.scan_subtype == 'Random':
                np.random.shuffle(positions)
                self.scan_info = self.get_info_from_positions(positions)

            elif self.scan_subtype == 'Adaptive':
                # return an "empty" ScanInfo as positions will be "set" during the scan
                self.scan_info = ScanInfo(Nsteps=0, positions=np.array([0, 1]), axes_unique=[np.array([])],
                                          axes_indexes=np.array([]), adaptive_loss=self.adaptive_loss)

            else:               # pragma: no cover
                raise ScannerException(f'The chosen scan_subtype: {str(self.scan_subtype)} is not known')

        elif self.scan_type == "Scan2D":
            if self.scan_subtype != 'Adaptive':
                if np.abs((self.stops[0]-self.starts[0]) / self.steps[0]) > steps_limit:
                    return ScanInfo()

            if self.scan_subtype == 'Spiral':
                positions = set_scan_spiral(self.starts, self.stops, self.steps)
                self.scan_info = self.get_info_from_positions(positions)

            elif self.scan_subtype == 'Back&Forth':
                positions = set_scan_linear(self.starts, self.stops, self.steps, back_and_force=True)
                self.scan_info = self.get_info_from_positions(positions)

            elif self.scan_subtype == 'Linear':
                positions = set_scan_linear(self.starts, self.stops, self.steps, back_and_force=False)
                self.scan_info = self.get_info_from_positions(positions)

            elif self.scan_subtype == 'Random':
                positions = set_scan_random(self.starts, self.stops, self.steps)
                self.scan_info = self.get_info_from_positions(positions)

            elif self.scan_subtype == 'Adaptive':
                # return an "empty" ScanInfo as positions will be "set" during the scan
                self.scan_info = ScanInfo(Nsteps=0, positions=np.zeros([0, 2]), axes_unique=[np.array([])],
                                          axes_indexes=np.array([]), adaptive_loss=self.adaptive_loss)
            else:
                raise ScannerException(f'The chosen scan_subtype: {str(self.scan_subtype)} is not known')

        elif self.scan_type == "Sequential":
            if self.scan_subtype == 'Linear':
                positions = set_scan_sequential(self.starts, self.stops, self.steps)
                self.scan_info = self.get_info_from_positions(positions)
            else:
                raise ScannerException(f'The chosen scan_subtype: {str(self.scan_subtype)} is not known')

        elif self.scan_type == 'Tabular':
            if self.scan_subtype == 'Linear':
                if self.positions is not None:
                    self.starts = np.min(self.positions, axis=0)
                    self.stops = np.max(self.positions, axis=0)
                self.scan_info = self.get_info_from_positions(self.positions)
            elif self.scan_subtype == 'Adaptive':
                # return an "empty" ScanInfo as positions will be "set" during the scan
                # but adds some usefull info such as total length and list of vectors
                self.vectors = []
                length = 0.

                for ind in range(len(self.starts)):
                    self.vectors.append(QVector(self.starts[ind][0], self.starts[ind][1],
                                           self.stops[ind][0], self.stops[ind][1]))
                    length += self.vectors[-1].norm()

                self.scan_info = ScanInfo(Nsteps=0, positions=np.zeros([0, self.Naxes]), axes_unique=[np.array([])],
                                          axes_indexes=np.array([]), vectors=self.vectors, length=length,
                                          adaptive_loss=self.adaptive_loss)
            else:
                raise ScannerException(f'The chosen scan_subtype: {str(self.scan_subtype)} is not known')
        return self.scan_info

    def evaluate_steps(self):
        """Quick method to evaluated the number of steps for a given scan type and subtype"""
        Nsteps = 1
        if self.starts is not None:
            for ind in range(len(self.starts)):
                if self.scan_subtype == 'Adaptive':
                    Nsteps = 1
                elif self.scan_subtype != 'Spiral':
                    Nsteps *= np.abs((self.stops[ind] - self.starts[ind]) / self.steps[ind])+1
                else:
                    Nsteps *= np.abs(2 * (self.stops[ind] / self.steps[ind]) + 1)
        return Nsteps

    def __repr__(self):
        if self.vectors is not None:
            bounds = f'bounds as vectors: {self.vectors} and curvilinear step: {self.steps}'
        else:
            bounds = f' bounds (starts/stops/steps): {self.starts}/{self.stops}/{self.steps})'

        if self.scan_subtype != 'Adaptive':
            return f'[{self.scan_type}/{self.scan_subtype}] scanner with {self.scan_info.Nsteps} positions and ' + bounds
        else:
            return f'[{self.scan_type}/{self.scan_subtype}] scanner with unknown (yet) positions to reach and ' + bounds


class TableModelSequential(gutils.TableModel):
    """Table Model for the Model/View Qt framework dedicated to the Sequential scan mode"""
    def __init__(self, data, **kwargs):
        header = ['Actuator', 'Start', 'Stop', 'Step']
        if 'header' in kwargs:
            header = kwargs.pop('header')
        editable = [False, True, True, True]
        if 'editable' in kwargs:
            editable = kwargs.pop('editable')
        super().__init__(data, header, editable=editable, **kwargs)

    def __repr__(self):
        return f'{self.__class__.__name__} from module {self.__class__.__module__}'

    def validate_data(self, row, col, value):
        """
        make sure the values and signs of the start, stop and step values are "correct"
        Parameters
        ----------
        row: (int) row within the table that is to be changed
        col: (int) col within the table that is to be changed
        value: (float) new value for the value defined by row and col

        Returns
        -------
        bool: True is the new value is fine (change some other values if needed) otherwise False
        """
        start = self.data(self.index(row, 1), QtCore.Qt.DisplayRole)
        stop = self.data(self.index(row, 2), QtCore.Qt.DisplayRole)
        step = self.data(self.index(row, 3), QtCore.Qt.DisplayRole)
        isstep = False
        if col == 1:  # the start
            start = value
        elif col == 2:  # the stop
            stop = value
        elif col == 3:  # the step
            isstep = True
            step = value

        if np.abs(step) < 1e-12 or start == stop:
            return False
        if np.sign(stop - start) != np.sign(step):
            if isstep:
                self._data[row][2] = -stop
            else:
                self._data[row][3] = -step
        return True


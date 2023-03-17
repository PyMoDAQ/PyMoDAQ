# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""


import numpy as np
from qtpy import QtCore
from qtpy.QtCore import Slot

from pymodaq.utils.plotting.utils.plot_utils import QVector
import pymodaq.utils.math_utils as mutils
from pymodaq.utils import gui_utils as gutils
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.config import Config
from pymodaq.utils.scanner.scan_factory import ScannerFactory
from pymodaq.utils.enums import BaseEnum

logger = set_logger(get_module_name(__file__))
config = Config()

scanner_factory = ScannerFactory()
ScanType = BaseEnum('ScanType', ['NoScan'] + scanner_factory.scan_types())


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





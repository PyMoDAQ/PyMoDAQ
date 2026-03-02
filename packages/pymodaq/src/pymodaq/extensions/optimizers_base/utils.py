# -*- coding: utf-8 -*-
"""
Created the 31/08/2023

@author: Sebastien Weber
"""
from typing import TYPE_CHECKING
import numpy as np
from collections import namedtuple

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.enums import StrEnum
from pymodaq_utils.config import CacheConfig

from pymodaq_data.data import (DataToExport, DataCalculated)

from pymodaq.utils.data import DataActuator, DataToActuators

if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move

logger = set_logger(get_module_name(__file__))


class StopType(StrEnum):
    NONE = 'None'
    ITER = 'Iter'
    PREDICT = 'Predict'
    BEST = 'Best'

    def tip(self):
        if self == StopType.NONE:
            return 'Stopping only after the number of iteration has been reached'
        elif self == StopType.ITER:
            return 'Stopping only after the number of iteration has been reached'
        elif self == StopType.PREDICT:
            return ('Stopping either after the number of iteration has been reached or the last N'
                    'tested coordinates have a standard deviation less than tolerance')
        elif self == StopType.BEST:
            return ('Stopping either after the number of iteration has been reached or the N best '
                    'coordinates have a standard deviation less than tolerance')


StoppingParameters = namedtuple('StoppingParameters',
                                ['niter', 'stop_type', 'tolerance', 'npoints'])

class PredictionError(Exception):
    pass


def individual_as_dte(individual: dict[str, float], actuators: list['DAQ_Move'],
                      name: str = 'Individual') -> DataToExport:
    """ Create a DataToExport from the individual coordinates and the list of selected actuators"""
    return DataToExport(
        name,
        data=[DataCalculated(actuators[ind].title,
                             data=[np.atleast_1d(individual[actuators[ind].title])],
                             units=actuators[ind].units,
                             labels=[actuators[ind].title],
                             origin=name)
              for ind in range(len(individual))],)


def individual_as_dta(individual: dict[str, float], actuators: list['DAQ_Move'],
                      name: str = 'Individual', mode='abs') -> DataToActuators:
    """ Create a DataToActuators from the individual coordinates and the list of selected actuators"""
    return DataToActuators(
        name, mode=mode,
        data=[DataActuator(actuators[ind].title,
                           data=[np.atleast_1d(individual[actuators[ind].title])],
                           units=actuators[ind].units,
                           labels=[actuators[ind].title],
                           origin=name)
              for ind in range(len(individual))],)


class OptimizerConfig(CacheConfig):
    """Main class to deal with configuration values for this plugin

    To b subclassed for real implementation if needed, see Optimizer class attribute config_saver
    """
    config_template_path = None
    config_name = f"optimizer_settings"


def find_key_in_nested_dict(dic, key):
    stack = [dic]
    while stack:
        d = stack.pop()
        if key in d:
            return d[key]
        for v in d.values():
            if isinstance(v, dict):
                stack.append(v)
            if isinstance(v, list):
                stack += v

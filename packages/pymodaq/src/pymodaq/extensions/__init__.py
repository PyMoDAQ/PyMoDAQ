# -*- coding: utf-8 -*-
"""
Created the 25/10/2022

@author: Sebastien Weber
"""
from pymodaq_utils.enums import StrEnum


from .utils import get_extensions
from .pid.utils import get_models


from pymodaq.extensions.scan.daq_scan import DAQScan
from .daq_logger.daq_logger import DAQ_Logger
from .pid.pid_controller import DAQ_PID

from .bayesian.bayesian_optimization import BayesianOptimization
from .adaptive_optim.adaptive_optimization import AdaptiveOptimisation

from .data_mixer.data_mixer import DataMixer
from .console import Console




class ExtensionEnum(StrEnum):
    SCANNER = 'Scanner'
    LOGGER = 'Logger'
    PID = 'PID'
    BAYESIAN = 'Bayesian'
    ADAPTIVE = 'Adaptive'
    DATAMIXER = 'DataMixer'
    CONSOLE = 'QtConsole'


internal_extensions = {
    ExtensionEnum.SCANNER.value: DAQScan,
    ExtensionEnum.LOGGER.value: DAQ_Logger,
    ExtensionEnum.PID.value: DAQ_PID,
    ExtensionEnum.BAYESIAN.value: BayesianOptimization,
    ExtensionEnum.ADAPTIVE.value: AdaptiveOptimisation,
    ExtensionEnum.DATAMIXER.value: DataMixer,
    ExtensionEnum.CONSOLE.value: Console,
}




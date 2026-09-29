from typing import Mapping, Union

from pymodaq_data.data import DataToExport

from pymodaq.utils.h5modules.module_saving import (
    LoggerSaver, GroupModuleType, DetectorTimeSaver, ActuatorTimeSaver, Node)
from aenum import extend_enum

from pymodaq_data.h5modules.backends import GROUP

extend_enum(GroupModuleType, 'RAMP')


class RampSaver(LoggerSaver):
    """Implementation of the ModuleSaver class dedicated to Ramping module

    Parameters
    ----------
    h5saver
    module
    """
    group_type = GroupModuleType.RAMP



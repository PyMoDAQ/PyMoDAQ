from typing import TYPE_CHECKING

from pymodaq_utils.enums import StrEnum
from pymodaq_utils.config import GlobalConfig
from pymodaq_utils.logger import set_logger, get_module_name

if TYPE_CHECKING:
    pass

config = GlobalConfig()
logger = set_logger(get_module_name(__file__))


class ModuleType(StrEnum):
    Actuator = "actuator"
    Detector = "detector"
    Control = 'control'  # either actuator or detector
    Other = 'other'
    NONE = 'None'



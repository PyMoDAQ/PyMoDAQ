import random

from pymodaq.utils.data import DataActuator
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq_data import DataToExport, DataDim

from pymodaq_utils.enums import StrEnum
from pymodaq_utils.config import GlobalConfig as Config, get_set_config_dir
from pymodaq.utils.config import get_set_roi_manager_path
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import utils
from pymodaq_gui.parameter.pymodaq_ptypes import registerParameterType, GroupParameter
from pymodaq.utils.managers.state.state_manager import StateManager

config = Config()
logger = set_logger(get_module_name(__file__))


def get_set_roi_path(subfolder: str = ''):
    """ creates and return the config folder path for rois files
    """
    return get_set_roi_manager_path()

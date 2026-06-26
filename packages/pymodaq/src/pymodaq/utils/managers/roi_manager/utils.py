import random

from pymodaq.utils.data import DataActuator
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq_data import DataToExport, DataDim

from pymodaq_utils.enums import StrEnum
from pymodaq_utils.config import GlobalConfig as Config, get_set_config_dir
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import utils
from pymodaq_gui.parameter.pymodaq_ptypes import registerParameterType, GroupParameter
from pymodaq.utils.managers.state.state_manager import StateManager

config = Config()
logger = set_logger(get_module_name(__file__))



class ModulesManager(ModulesManager):  # noqa imported from Overshooter
    """ Customized version of the ModulesManager """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.available_data = DataToExport(self.__class__.__name__)

    def get_det_data_list(self) -> DataToExport:
        """Do a snap of selected detectors and get_actuator_value of connected actuators
        , to get the list of all the data and processed data"""

        data_det: DataToExport = super().get_det_data_list()

        if len(self.actuators) == 0:
            data_act = DataToExport(name=__class__.__name__, control_module='DAQ_Move')
        else:
            self.connect_actuators()
            dte_act_to_move = DataToExport('Actuators', control_module='DAQ_MOVE')
            for mod in self.actuators:
                dte_act_to_move.append(mod.current_value)
            data_act = self.move_actuators(dte_act_to_move)
            self.connect_actuators(False)
        data_det.append(data_act)

        data_list0D = []
        for dwa in data_det.get_data_from_dim(DataDim.Data0D):
            data_list0D.extend([f'{dwa.origin}/{dwa.name}/{label}' for label in dwa.labels])

        self.available_data = data_list0D[:]
        return data_det


def get_set_roi_path(subfolder: str = ''):
    """ creates and return the config folder path for rois files
    """
    target_path = get_set_config_dir('rois', user=True)
    target_path.mkdir(parents=True, exist_ok=True)
    return target_path

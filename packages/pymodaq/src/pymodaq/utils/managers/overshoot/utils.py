import random

from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq_data import DataToExport, DataDim

from pymodaq_utils.enums import StrEnum
from pymodaq_utils.config import GlobalConfig as Config, get_set_config_dir
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import utils
from pymodaq_gui.parameter.pymodaq_ptypes import registerParameterType, GroupParameter
from pymodaq.utils.managers.configurator.configurator import Configurator

config = Config()
logger = set_logger(get_module_name(__file__))


def find_last_index(list_children: list = [], name_prefix='', format_string='02.0f'):
    # Custom function to find last available index
    child_indexes = ([int(par.name()[len(name_prefix) + 1:]) for par in list_children if name_prefix in par.name()])
    if child_indexes == []:
        newindex = 0
    else:
        newindex = max(child_indexes) + 1
    return f'{newindex:{format_string}}'


class TriggerDirection(StrEnum):
    ABOVE = 'Above'
    BELOW = 'Below'


def create_overshoot_param(typ: str, configurations: list[str]) -> list[dict]:
    return [
        {'title': 'Module:', 'name': 'module', 'type': 'str', 'value': typ.split('/')[0],
         'readonly': True},
        {'title': 'DataName:', 'name': 'name', 'type': 'str', 'value': typ.split('/')[1],
         'readonly': True},
        {'title': 'Trigger:', 'name': 'trigger', 'type': 'led', 'value': True},
        {'title': 'Direction:', 'name': 'direction', 'type': 'list',
         'value': TriggerDirection.ABOVE.value, 'limits': TriggerDirection.names()},
        {'title': 'Value:', 'name': 'value', 'type': 'float', 'value': 0,},
        {'title': 'Configuration:', 'name': 'configuration', 'type': 'list',
         'limits': configurations, 'value': configurations[0]},
    ]


class PresetScalableGroupOverShoot(GroupParameter):
    """
    """

    def __init__(self, **opts):
        opts['type'] = 'group_overshoot'
        opts['addText'] = "Add"
        opts['addList'] = []
        opts['configurations'] = []
        super().__init__(**opts)

    def addNew(self, typ: str):
        """
        """
        name_prefix = 'overshoot'
        new_index = find_last_index(self.children(), name_prefix, format_string='02.0f')
        child = {'title': f'Overshoot {new_index}',
                 'name': f'{name_prefix}{new_index}',
                 'type': 'group',
                 'removable': True,
                 'children': create_overshoot_param(typ,
                                                    self.opts['configurations'])}
        self.addChild(child)


registerParameterType('group_overshoot', PresetScalableGroupOverShoot, override=True)


class ModulesManager(ModulesManager):
    """ Customized version of the ModulesManager """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.available_data = DataToExport(self.__class__.__name__)

    def get_det_data_list(self) -> DataToExport:
        """Do a snap of selected detectors and get_actuator_value of connected actuators
        , to get the list of all the data and processed data"""

        if len(self.detectors) == 0:
            data_det = DataToExport(name=__class__.__name__, control_module='DAQ_Viewer')
        else:
            self.connect_detectors()
            data_det: DataToExport = self.grab_data()
            self.connect_detectors(False)

        if len(self.actuators) == 0:
            data_act = DataToExport(name=__class__.__name__, control_module='DAQ_Move')
        else:
            self.connect_actuators()
            data_act = self.move_actuators()
            self.connect_actuators(False)

        data_list0D = data_det.get_full_names(DataDim.Data0D)
        data_list0D.extend(data_act.get_full_names(DataDim.Data0D))
        self.settings.child('data_dimensions', 'det_data_list0D').setValue(
            dict(all_items=data_list0D, selected=[]))

        self.available_data = data_list0D[:]
        return data_det


def get_set_overshooter_path(subfolder: str = ''):
    """ creates and return the config folder path for overshooter files
    """
    target_path = get_set_config_dir('overshooter_configs').joinpath(subfolder)
    target_path.mkdir(parents=True, exist_ok=True)
    return target_path

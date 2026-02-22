import random

from pymodaq_utils.enums import StrEnum
from pymodaq_utils.config import GlobalConfig as Config
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
    UP = 'Up'
    DOWN = 'Down'


def create_overshoot_param(typ: str, configurations: list[str]) -> list[dict]:
    return [
        {'title': 'Module:', 'name': 'module', 'type': 'str', 'value': typ.split('/')[0],
         'readonly': True},
        {'title': 'DataName:', 'name': 'name', 'type': 'str', 'value': typ.split('/')[1],
         'readonly': True},
        {'title': 'Trigger:', 'name': 'trigger', 'type': 'led', 'value': True},
        {'title': 'Direction:', 'name': 'name', 'type': 'list',
         'value': TriggerDirection.UP.value, 'limits': TriggerDirection.names},
        {'title': 'Configuration:', 'name': 'configuration', 'type': 'list',
         'limits': configurations, 'value': configurations[0]},
    ]


class PresetScalableGroupOverShoot(GroupParameter):
    """
    """

    def __init__(self, **opts):
        opts['type'] = 'group_overshoot'
        opts['addText'] = "Add"
        super().__init__(**opts)

    def addNew(self, typ: tuple, configurations: list[str] = None):
        """
        """
        if configurations is None:
            configurations = []
        name_prefix = 'overshoot'
        typ = typ[-1]  # Only need last entry here
        new_index = find_last_index(self.children(), name_prefix, format_string='02.0f')
        child = {'title': f'Overshoot {new_index}',
                 'name': f'{name_prefix}{new_index}',
                 'type': 'group',
                 'removable': True,
                 'children': create_overshoot_param(typ, configurations)}
        self.addChild(child)


registerParameterType('group_overshoot', PresetScalableGroupOverShoot, override=True)

import random

from pymodaq_utils.enums import StrEnum
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import utils
from pymodaq.utils.managers.modules_manager import ModuleType
from pymodaq_gui.parameter.pymodaq_ptypes import registerParameterType, GroupParameter
from pymodaq_gui.parameter.utils import get_param_dict_from_name

from pymodaq.control_modules.instruments import DET_TYPES, ACTUATOR_TYPES, ACTUATOR_NAMES
from pymodaq.control_modules.daq_move_ui.factory import ActuatorUIFactory
from pymodaq.control_modules.utils import create_controller_param
from pymodaq.utils.config import Config

config = Config()
logger = set_logger(get_module_name(__file__))

# Fixed names that will sort the plugin in remote/mock
REMOTE_ITEMS  = {'LECODirector', 'TCPServer'}
MOCK_ITEMS = {}


class PresetAction(StrEnum):
    COPY = 'copy_preset'
    NEW = 'create_new_preset'
    DELETE = 'delete_preset'
    SAVE = 'save_preset'
    RELOAD = 'reload_preset'


def iterative_show_pb(params):
    for param in params:
        if param['type'] == 'itemselect' or param['type'] == 'list':
            param['show_pb'] = True
        elif 'children' in param:
            iterative_show_pb(param['children'])


def find_last_index(list_children:list=[], name_prefix ='',format_string='02.0f'):
    # Custom function to find last available index
    child_indexes = ([int(par.name()[len(name_prefix) + 1:]) for par in list_children if name_prefix in par.name()])
    if child_indexes == []:
        newindex = 0
    else:
        newindex = max(child_indexes) + 1
    return f'{newindex:{format_string}}'


def categorize_items(item_list, remote_items=None, mock_items=None):
    """
    Core function: categorize any list of items into Mock/Plugin/Remote.
    
    Args:
        item_list: List of items to categorize
        remote_items: Custom set of remote items (optional)
        mock_items: Custom set of mock items (optional)
    
    Returns: dict {category: [items]} with only non-empty categories
    """
    remote_items = remote_items or REMOTE_ITEMS
    mock_items = mock_items or MOCK_ITEMS
    
    categorized = {'Remote': [], 'Mock': [], 'Plugin': []}
    
    for item in item_list:
        if item in remote_items:
            categorized['Remote'].append(item)
        elif item in mock_items or 'mock' in item.lower():
            categorized['Mock'].append(item)
        else:
            categorized['Plugin'].append(item)
    
    # Return only non-empty categories
    return {k: v for k, v in categorized.items() if v}


def add_category_layers(dimension_dict, remote_items=None, mock_items=None):
    """
    Add category layers to a dimension dictionary.
    Uses categorize_items for each dimension.
    
    Args:
        dimension_dict: {dimension: [items]}
    
    Returns: {dimension: {category: [items]}}
    """
    result = {}
    
    for dimension, items in dimension_dict.items():
        # Reuse the core categorization function
        result[dimension] = categorize_items(items, remote_items, mock_items)
    
    return result


def make_actuator_controller_param(typ: str) -> dict:
    parent_module = utils.find_dict_in_list_from_key_val(ACTUATOR_TYPES, 'name', typ)
    class_ = getattr(getattr(parent_module['module'], 'daq_move_' + typ),
                        'DAQ_Move_' + typ)
    params_hardware = getattr(class_, 'params')

    controller_dict = get_param_dict_from_name(params_hardware, 'controller')
    axis_dict = get_param_dict_from_name(controller_dict['children'], 'axis')
    axis_names = axis_dict['limits']
    axis_name = axis_dict['value']
    controller_dict = create_controller_param(axis_name=axis_name, axis_names=axis_names)
    controller_dict['expanded'] = False
    return controller_dict


def make_detector_controller_param():
        controller_dict = create_controller_param()
        controller_dict['expanded'] = False
        return controller_dict


def create_info_param(module_type: ModuleType,
                      module_class_name: str,
                      dim: str = None) -> dict:
    """ Create a generic info parameter dictionary for a ControlModule in a Preset. """

    if module_type == ModuleType.Actuator:
        ui = ActuatorUIFactory.keys()
        ui_default = config('actuator', 'ui')
    else:
        ui = []
        ui_default = None

    info_param = \
        {'title': 'Info:', 'name': 'info', 'type': 'group', 'expanded': False, 'children': [
            {'title': 'Type:', 'name': 'type', 'type': 'str', 'value': module_class_name, 'readonly': True},
        ]}
    if dim is not None:
        info_param['children'].append(
            {'title': 'Dim:', 'name': 'dim', 'type': 'str', 'value': dim, 'readonly': True})
    if len(ui) > 0:
        info_param['children'].append(
            {'title': 'ui:', 'name': 'ui', 'type': 'list', 'value': ui_default, 'limits': ui})
    info_param['children'].append({'title': 'Init?:', 'name': 'init', 'type': 'bool', 'value': True})
    return info_param

    
class PresetScalableGroupMove(GroupParameter):
    """
    """

    def __init__(self, **opts):
        opts['type'] = 'groupmove'
        opts['addText'] = "Add"
        opts['addMenu'] = categorize_items(ACTUATOR_NAMES)
        super().__init__(**opts)

    def addNew(self, typ: tuple):
        """
        """
        name_prefix = ModuleType.Actuator.value
        typ = typ[-1] #Only need last entry here
        new_index = find_last_index(self.children(), name_prefix, format_string='02.0f')
        child = {'title': f'Actuator {new_index}',
                 'name': f'{name_prefix}{new_index}',
                 'type': 'group',
                 'removable': True,
                 'children': [
                     {'title': 'Name:', 'name': 'name', 'type': 'str', 'value': f'{name_prefix} {new_index}'},
                     create_info_param(ModuleType.Actuator, typ),
                     make_actuator_controller_param(typ),
                 ]}
        self.addChild(child)

registerParameterType('groupmove', PresetScalableGroupMove, override=True)


class PresetScalableGroupDet(GroupParameter):
    """
        =============== ==============
        **Attributes**    **Type**
        *opts*            dictionnary
        *options*         string list
        =============== ==============

        See Also
        --------
    """

    def __init__(self, **opts):
        opts['type'] = 'groupdet'
        opts['addText'] = "Add"
        options = {
        'DAQ0D': [name for name in [plugin['name'] for plugin in DET_TYPES['DAQ0D']]],
        'DAQ1D': [name for name in [plugin['name'] for plugin in DET_TYPES['DAQ1D']]],
        'DAQ2D': [name for name in [plugin['name'] for plugin in DET_TYPES['DAQ2D']]],
        'DAQND': [name for name in [plugin['name'] for plugin in DET_TYPES['DAQND']]],
         }
        opts['addMenu'] = add_category_layers(options)

        super().__init__(**opts)

    def addNew(self, typ:tuple):
        """
            Add a child.

            =============== ===========  ================
            **Parameters**    **Type**   **Description*
            *typ*             string     the viewer name
            =============== ===========  ================
        """

        name_prefix = ModuleType.Detector.value
        typ_full = "/".join((typ[0],typ[-1])) #Only need first and last element to retrieve associated plugin
        new_index = find_last_index(list_children=self.children(), name_prefix=name_prefix, format_string='02.0f')
        child = {'title': f'Detector {new_index}', 'name': f'{name_prefix}{new_index}',
                 'type': 'group', 'removable': True,
                 'children': [
                     {'title': 'Name:', 'name': 'name', 'type': 'str', 'value': f'{name_prefix} {new_index}'},
                     create_info_param(ModuleType.Detector, typ[-1], dim=typ[0]),
                     make_detector_controller_param()
                 ]}

        self.addChild(child)


registerParameterType('groupdet', PresetScalableGroupDet, override=True)

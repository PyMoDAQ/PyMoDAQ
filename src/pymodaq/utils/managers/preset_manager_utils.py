import random

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import utils

from pymodaq_gui.parameter.pymodaq_ptypes import registerParameterType, GroupParameter
from pymodaq_gui.parameter.utils import get_param_dict_from_name

from pymodaq.control_modules.move_utility_classes import params as daq_move_params
from pymodaq.control_modules.viewer_utility_classes import params as daq_viewer_params
from pymodaq.utils.daq_utils import get_plugins

logger = set_logger(get_module_name(__file__))

DAQ_Move_Stage_type = get_plugins('daq_move')
DAQ_0DViewer_Det_types = get_plugins('daq_0Dviewer')
DAQ_1DViewer_Det_types = get_plugins('daq_1Dviewer')
DAQ_2DViewer_Det_types = get_plugins('daq_2Dviewer')
DAQ_NDViewer_Det_types = get_plugins('daq_NDviewer')

# Fixed names that will sort the plugin in remote/mock
REMOTE_ITEMS  = {'LECODirector', 'TCPServer'}
MOCK_ITEMS = {}

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


def make_move_params(typ):
    params = daq_move_params
    iterative_show_pb(params)

    parent_module = utils.find_dict_in_list_from_key_val(DAQ_Move_Stage_type, 'name', typ)
    class_ = getattr(getattr(parent_module['module'], 'daq_move_' + typ),
                        'DAQ_Move_' + typ)
    params_hardware = getattr(class_, 'params')
    iterative_show_pb(params_hardware)

    for main_child in params:
        if main_child['name'] == 'move_settings':
            main_child['children'] = params_hardware
            controller_dict = get_param_dict_from_name(params_hardware, 'controller_ID')
            controller_dict['value'] = random.randint(0, 9999)

        elif main_child['name'] == 'main_settings':
            typ_dict = get_param_dict_from_name(main_child['children'], 'move_type')
            typ_dict['value'] = typ

    return params


def make_viewer_params(typ):
        params = daq_viewer_params
        iterative_show_pb(params)

        for main_child in params:
            if main_child['name'] == 'main_settings':
                for child in main_child['children']:
                    if child['name'] == 'DAQ_type':
                        child['value'] = typ[0:5]
                    if child['name'] == 'detector_type':
                        child['value'] = typ[6:]
                    if child['name'] == 'controller_status':
                        child['visible'] = True

        if '0D' in typ:
            parent_module = utils.find_dict_in_list_from_key_val(DAQ_0DViewer_Det_types, 'name', typ[6:])
            class_ = getattr(getattr(parent_module['module'], 'daq_0Dviewer_' + typ[6:]), 'DAQ_0DViewer_' + typ[6:])
        elif '1D' in typ:
            parent_module = utils.find_dict_in_list_from_key_val(DAQ_1DViewer_Det_types, 'name', typ[6:])
            class_ = getattr(getattr(parent_module['module'], 'daq_1Dviewer_' + typ[6:]), 'DAQ_1DViewer_' + typ[6:])
        elif '2D' in typ:
            parent_module = utils.find_dict_in_list_from_key_val(DAQ_2DViewer_Det_types, 'name', typ[6:])
            class_ = getattr(getattr(parent_module['module'], 'daq_2Dviewer_' + typ[6:]), 'DAQ_2DViewer_' + typ[6:])
        elif 'ND' in typ:
            parent_module = utils.find_dict_in_list_from_key_val(DAQ_NDViewer_Det_types, 'name', typ[6:])
            class_ = getattr(getattr(parent_module['module'], 'daq_NDviewer_' + typ[6:]), 'DAQ_NDViewer_' + typ[6:])
        for main_child in params:
            if main_child['name'] == 'main_settings':
                for child in main_child['children']:
                    if child['name'] == 'axes':
                        child['visible'] = True

        params_hardware = getattr(class_, 'params')
        iterative_show_pb(params_hardware)

        for main_child in params:
            # Was this condition useful? 
            # if main_child['name'] == 'detector_settings':
            #     while len(main_child['children']) > 0:
            #         for child in main_child['children']:
            #             main_child['children'].remove(child)

            #     main_child['children'].extend(params_hardware)
            if main_child['name'] == 'detector_settings':
                main_child['children'] = params_hardware
        controller_dict = get_param_dict_from_name(main_child['children'], 'controller_ID')
        controller_dict['value'] = random.randint(0, 9999)

        return params
    
class PresetScalableGroupMove(GroupParameter):
    """
        |

        ================ =============
        **Attributes**    **Type**
        *opts*            dictionnary
        ================ =============

        See Also
        --------
        hardware.DAQ_Move_Stage_type
    """

    def __init__(self, **opts):
        opts['type'] = 'groupmove'
        opts['addText'] = "Add"
        opts['addMenu'] = categorize_items([mov['name'] for mov in DAQ_Move_Stage_type])
        super().__init__(**opts)

    def addNew(self, typ:tuple):
        """
            Add a child.

            =============== ===========
            **Parameters**   **Type**
            *typ*            string
            =============== ===========
        """
        name_prefix = 'move'
        typ = typ[-1] #Only need last entry here
        new_index = find_last_index(self.children(), name_prefix, format_string='02.0f')
        params = make_move_params(typ)
        child = {'title': f'Actuator {new_index}',
            'name': f'{name_prefix}{new_index}',
            'type': 'group',
            'removable': True, 'renamable': False,
            'children': [
                {'title': 'Name:', 'name': 'name', 'type': 'str',
                'value': f'Move {new_index}'},
                {'title': 'Init?:', 'name': 'init', 'type': 'bool', 'value': True},
                {'title': 'Settings:', 'name': 'params', 'type': 'group', 'children': params},
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
        'DAQ0D': [name for name in [plugin['name'] for plugin in DAQ_0DViewer_Det_types]],
        'DAQ1D': [name for name in [plugin['name'] for plugin in DAQ_1DViewer_Det_types]],
        'DAQ2D': [name for name in [plugin['name'] for plugin in DAQ_2DViewer_Det_types]],
        'DAQND': [name for name in [plugin['name'] for plugin in DAQ_NDViewer_Det_types]],
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
        try:
            name_prefix = 'det'
            typ = "/".join((typ[0],typ[-1])) #Only need first and last element to retrieve associated plugin
            new_index = find_last_index(list_children=self.children(), name_prefix=name_prefix, format_string='02.0f')
            params = make_viewer_params(typ)
            child = {'title': f'Det {new_index}', 'name': f'{name_prefix}{new_index}',
                        'type': 'group', 'children': [
                {'title': 'Name:', 'name': 'name', 'type': 'str', 'value': f'Det {new_index}'},
                {'title': 'Init?:', 'name': 'init', 'type': 'bool', 'value': True},
                {'title': 'Settings:', 'name': 'params', 'type': 'group', 'children': params},
            ], 'removable': True, 'renamable': False}            

            self.addChild(child)
        except Exception as e:
            print(str(e))


registerParameterType('groupdet', PresetScalableGroupDet, override=True)

import random
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_move.utility_classes import params as daq_move_params
from pymodaq.daq_viewer.utility_classes import params as daq_viewer_params

from pyqtgraph.parametertree.Parameter import registerParameterType
from pymodaq.daq_utils.parameter.pymodaq_ptypes import GroupParameterCustom as GroupParameter

logger = utils.set_logger(utils.get_module_name(__file__))

DAQ_Move_Stage_type = utils.get_plugins('daq_move')
DAQ_0DViewer_Det_types = utils.get_plugins('daq_0Dviewer')
DAQ_1DViewer_Det_types = utils.get_plugins('daq_1Dviewer')
DAQ_2DViewer_Det_types = utils.get_plugins('daq_2Dviewer')
DAQ_NDViewer_Det_types = utils.get_plugins('daq_NDviewer')


def iterative_show_pb(params):
    for param in params:
        if param['type'] == 'itemselect' or param['type'] == 'list':
            param['show_pb'] = True
        elif 'children' in param:
            iterative_show_pb(param['children'])


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
        opts['addList'] = [mov['name'] for mov in DAQ_Move_Stage_type]
        super().__init__(**opts)

    def addNew(self, typ):
        """
            Add a child.

            =============== ===========
            **Parameters**   **Type**
            *typ*            string
            =============== ===========
        """
        name_prefix = 'move'

        child_indexes = [int(par.name()[len(name_prefix) + 1:]) for par in self.children()]

        if child_indexes == []:
            newindex = 0
        else:
            newindex = max(child_indexes) + 1

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
            elif main_child['name'] == 'main_settings':
                for child in main_child['children']:
                    if child['name'] == 'move_type':
                        child['value'] = typ
                    if child['name'] == 'controller_ID':
                        child['value'] = random.randint(0, 9999)

        child = {'title': 'Actuator {:02.0f}'.format(newindex), 'name': f'{name_prefix}{newindex:02.0f}',
                 'type': 'group',
                 'removable': True, 'children': [
                {'title': 'Name:', 'name': 'name', 'type': 'str', 'value': 'Move {:02.0f}'.format(newindex)},
                {'title': 'Init?:', 'name': 'init', 'type': 'bool', 'value': True},
                {'title': 'Settings:', 'name': 'params', 'type': 'group', 'children': params
                 }], 'removable': True, 'renamable': False}

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
        options = []
        for name in [plugin['name'] for plugin in DAQ_0DViewer_Det_types]:
            options.append('DAQ0D/' + name)
        for name in [plugin['name'] for plugin in DAQ_1DViewer_Det_types]:
            options.append('DAQ1D/' + name)
        for name in [plugin['name'] for plugin in DAQ_2DViewer_Det_types]:
            options.append('DAQ2D/' + name)
        for name in [plugin['name'] for plugin in DAQ_NDViewer_Det_types]:
            options.append('DAQND/' + name)
        opts['addList'] = options

        super().__init__(**opts)

    def addNew(self, typ):
        """
            Add a child.

            =============== ===========  ================
            **Parameters**    **Type**   **Description*
            *typ*             string     the viewer name
            =============== ===========  ================
        """
        try:
            name_prefix = 'det'
            child_indexes = [int(par.name()[len(name_prefix) + 1:]) for par in self.children()]

            if child_indexes == []:
                newindex = 0
            else:
                newindex = max(child_indexes) + 1

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
                        if child['name'] == 'controller_ID':
                            child['value'] = random.randint(0, 9999)

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
                if main_child['name'] == 'detector_settings':
                    while len(main_child['children']) != 1:
                        for child in main_child['children']:
                            if child['name'] != 'ROIselect':
                                main_child['children'].remove(child)

                    main_child['children'].extend(params_hardware)

            child = {'title': 'Det {:02.0f}'.format(newindex), 'name': f'{name_prefix}{newindex:02.0f}',
                     'type': 'group', 'children': [
                {'title': 'Name:', 'name': 'name', 'type': 'str', 'value': 'Det {:02.0f}'.format(newindex)},
                {'title': 'Init?:', 'name': 'init', 'type': 'bool', 'value': True},
                {'title': 'Settings:', 'name': 'params', 'type': 'group', 'children': params},
            ], 'removable': True, 'renamable': False}

            self.addChild(child)
        except Exception as e:
            print(str(e))


registerParameterType('groupdet', PresetScalableGroupDet, override=True)

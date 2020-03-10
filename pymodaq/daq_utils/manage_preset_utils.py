import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter, ParameterTree
import pymodaq.daq_utils.custom_parameter_tree as custom_tree# to be placed after importing Parameter
from pyqtgraph.parametertree.Parameter import registerParameterType
import random
from pymodaq_plugins import daq_move_plugins as movehardware
from pymodaq.daq_viewer.utility_classes import params as daq_viewer_params
from pymodaq.daq_move.utility_classes import params as daq_move_params

from pymodaq_plugins.daq_viewer_plugins import plugins_2D, plugins_1D, plugins_0D, plugins_ND
from pymodaq.daq_utils.daq_utils import make_enum

DAQ_Move_Stage_type = make_enum('daq_move')
DAQ_0DViewer_Det_type = make_enum('daq_0Dviewer')
DAQ_1DViewer_Det_type = make_enum('daq_1Dviewer')
DAQ_2DViewer_Det_type = make_enum('daq_2Dviewer')
DAQ_NDViewer_Det_type = make_enum('daq_NDviewer')

class PresetScalableGroupMove( pTypes.GroupParameter):
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
        opts['addList'] = DAQ_Move_Stage_type.names('daq_move')
        pTypes.GroupParameter.__init__(self, **opts)

    def addNew(self, typ):
        """
            Add a child.

            =============== ===========
            **Parameters**   **Type**
            *typ*            string
            =============== ===========
        """
        childnames = [par.name() for par in self.children()]
        if childnames == []:
            newindex = 0
        else:
            newindex = len(childnames)

        params = daq_move_params
        for param in params:
            if param['type'] == 'itemselect' or param['type'] == 'list':
                param['show_pb'] = True

        class_ = getattr(getattr(movehardware, 'daq_move_' + typ), 'DAQ_Move_' + typ)
        params_hardware = getattr(class_, 'params')
        for param in params_hardware:
            if param['type'] == 'itemselect' or param['type'] == 'list':
                param['show_pb'] = True

        for main_child in params:
            if main_child['name'] == 'move_settings':
                main_child['children'] = params_hardware
            elif main_child['name'] == 'main_settings':
                for child in main_child['children']:
                    if child['name'] == 'move_type':
                        child['value'] = typ
                    if child['name'] == 'controller_ID':
                        child['value'] = random.randint(0, 9999)

        child = {'title': 'Move {:02.0f}'.format(newindex), 'name': 'move{:02.0f}'.format(newindex), 'type': 'group',
                 'removable': True, 'children': [
                {'title': 'Name:', 'name': 'name', 'type': 'str', 'value': 'Move {:02.0f}'.format(newindex)},
                {'title': 'Init?:', 'name': 'init', 'type': 'bool', 'value': True},
                {'title': 'Settings:', 'name': 'params', 'type': 'group', 'children': params
                 }], 'removable': True, 'renamable': False}

        self.addChild(child)
registerParameterType('groupmove', PresetScalableGroupMove, override=True)

class PresetScalableGroupDet( pTypes.GroupParameter):
    """
        =============== ==============
        **Attributes**    **Type**
        *opts*            dictionnary
        *options*         string list
        =============== ==============

        See Also
        --------
        pymodaq.daq_utils.daq_utils.make_enum
    """
    def __init__(self, **opts):
        opts['type'] = 'groupdet'
        opts['addText'] = "Add"
        options=[]
        for name in DAQ_0DViewer_Det_type.names('daq_0Dviewer'):
            options.append('DAQ0D/'+name)
        for name in DAQ_1DViewer_Det_type.names('daq_1Dviewer'):
            options.append('DAQ1D/'+name)
        for name in DAQ_2DViewer_Det_type.names('daq_2Dviewer'):
            options.append('DAQ2D/'+name)
        for name in DAQ_NDViewer_Det_type.names('daq_NDviewer'):
            options.append('DAQND/'+name)
        opts['addList'] = options

        pTypes.GroupParameter.__init__(self, **opts)

    def addNew(self, typ):
        """
            Add a child.

            =============== ===========  ================
            **Parameters**    **Type**   **Description*
            *typ*             string     the viewer name
            =============== ===========  ================
        """
        try:
            childnames=[par.name() for par in self.children()]
            if childnames==[]:
                newindex=0
            else:
                newindex=len(childnames)

            params = daq_viewer_params
            for param in params:
                if param['type'] == 'itemselect' or param['type'] == 'list':
                    param['show_pb'] = True

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
                class_ = getattr(getattr(plugins_0D, 'daq_0Dviewer_' + typ[6:]), 'DAQ_0DViewer_' + typ[6:])
            elif '1D' in typ:
                class_ = getattr(getattr(plugins_1D, 'daq_1Dviewer_' + typ[6:]), 'DAQ_1DViewer_' + typ[6:])
            elif '2D' in typ:
                class_ = getattr(getattr(plugins_2D, 'daq_2Dviewer_' + typ[6:]), 'DAQ_2DViewer_' + typ[6:])
            elif 'ND' in typ:
                class_ = getattr(getattr(plugins_ND, 'daq_NDviewer_' + typ[6:]), 'DAQ_NDViewer_' + typ[6:])
            for main_child in params:
                if main_child['name'] == 'main_settings':
                    for child in main_child['children']:
                        if child['name'] == 'axes':
                            child['visible'] = True

            params_hardware = getattr(class_, 'params')
            for param in params_hardware:
                if param['type'] == 'itemselect' or param['type'] == 'list':
                    param['show_pb'] = True

            for main_child in params:
                if main_child['name'] == 'detector_settings':
                    while len(main_child['children']) != 1:
                        for child in main_child['children']:
                            if child['name'] != 'ROIselect':
                                main_child['children'].remove(child)

                    main_child['children'].extend(params_hardware)

            child = {'title': 'Det {:02.0f}'.format(newindex) ,'name': 'det{:02.0f}'.format(newindex), 'type': 'group', 'children': [
                    {'title': 'Name:', 'name': 'name', 'type': 'str', 'value': 'Det {:02.0f}'.format(newindex)},
                    {'title': 'Init?:', 'name': 'init', 'type': 'bool', 'value': True},
                    {'title': 'Settings:', 'name': 'params', 'type': 'group', 'children': params},
                    ], 'removable': True, 'renamable': False}

            self.addChild(child)
        except Exception as e:
            print(str(e))
registerParameterType('groupdet', PresetScalableGroupDet, override=True)

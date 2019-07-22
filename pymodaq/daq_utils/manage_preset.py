from PyQt5 import QtWidgets
import sys
import os
import random

import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter, ParameterTree
import pymodaq.daq_utils.custom_parameter_tree as custom_tree# to be placed after importing Parameter
from pyqtgraph.parametertree.Parameter import registerParameterType

from pymodaq.daq_move.daq_move_main import DAQ_Move
from pymodaq_plugins import daq_move_plugins as movehardware
from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer
from pymodaq_plugins.daq_viewer_plugins import plugins_2D, plugins_1D, plugins_0D
from pymodaq.daq_utils.daq_utils import get_set_pid_path, select_file, make_enum
from pymodaq.daq_utils.h5saver import H5Saver
import importlib
from pymodaq.daq_utils.pid.pid_params import params as pid_params

DAQ_Move_Stage_type=make_enum('daq_move')
DAQ_0DViewer_Det_type=make_enum('daq_0Dviewer')
DAQ_1DViewer_Det_type=make_enum('daq_1Dviewer')
DAQ_2DViewer_Det_type=make_enum('daq_2Dviewer')

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
        childnames=[par.name() for par in self.children()]
        if childnames==[]:
            newindex=0
        else:
            newindex=len(childnames)

        params=DAQ_Move.params
        for param in params:
            if param['type']=='itemselect' or param['type']=='list':
                param['show_pb']=True


        class_=getattr(getattr(movehardware,'daq_move_'+typ),'DAQ_Move_'+typ)
        params_hardware=getattr(class_,'params')
        for param in params_hardware:
            if param['type']=='itemselect' or param['type']=='list':
                param['show_pb']=True


        for main_child in params:
            if main_child['name']=='move_settings':
                main_child['children']=params_hardware
            elif main_child['name']=='main_settings':
                for child in main_child['children']:
                    if child['name']=='move_type':
                        child['value']=typ
                    if child['name']=='controller_ID':
                        child['value']=random.randint(0,9999)

        child={'title': 'Move {:02.0f}'.format(newindex) ,'name': 'move{:02.0f}'.format(newindex), 'type': 'group', 'removable': True, 'children': [
                {'title': 'Name:' , 'name': 'name', 'type': 'str', 'value': 'Move {:02.0f}'.format(newindex)},
                {'title': 'Init?:' , 'name': 'init', 'type': 'bool', 'value': True},
                {'title': 'Settings:', 'name': 'params', 'type': 'group', 'children': params
               }],'removable':True, 'renamable':False}

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

            params=DAQ_Viewer.params
            for param in params:
                if param['type']=='itemselect' or param['type']=='list':
                    param['show_pb']=True

            for main_child in params:
                if main_child['name']=='main_settings':
                    for child in main_child['children']:
                        if child['name']=='DAQ_type':
                            child['value']=typ[0:5]
                        if child['name']=='detector_type':
                            child['value']=typ[6:]
                        if child['name']=='controller_status':
                            child['visible']=True
                        if child['name']=='controller_ID':
                            child['value']=random.randint(0,9999)

            if '0D' in typ:
                class_=getattr(getattr(plugins_0D,'daq_0Dviewer_'+typ[6:]),'DAQ_0DViewer_'+typ[6:])
            elif '1D' in typ:
                class_=getattr(getattr(plugins_1D,'daq_1Dviewer_'+typ[6:]),'DAQ_1DViewer_'+typ[6:])
            elif '2D' in typ:
                class_=getattr(getattr(plugins_2D,'daq_2Dviewer_'+typ[6:]),'DAQ_2DViewer_'+typ[6:])
            for main_child in params:
                if main_child['name']=='main_settings':
                    for child in main_child['children']:
                        if child['name']=='axes':
                            child['visible']=True

            params_hardware=getattr(class_,'params')
            for param in params_hardware:
                if param['type']=='itemselect' or param['type']=='list':
                    param['show_pb']=True

            for main_child in params:
                if main_child['name']=='detector_settings':
                    while len(main_child['children'])!=1:
                        for child in main_child['children']:
                            if child['name']!='ROIselect':
                                main_child['children'].remove(child)

                    main_child['children'].extend(params_hardware)

            child={'title': 'Det {:02.0f}'.format(newindex) ,'name': 'det{:02.0f}'.format(newindex), 'type': 'group', 'children': [
                    {'title': 'Name:' , 'name': 'name', 'type': 'str', 'value': 'Det {:02.0f}'.format(newindex)},
                    {'title': 'Init?:' , 'name': 'init', 'type': 'bool', 'value': True},
                    {'title': 'Settings:', 'name': 'params', 'type': 'group', 'children': params
                   }],'removable':True, 'renamable':False}

            self.addChild(child)
        except Exception as e:
            print(str(e))
registerParameterType('groupdet', PresetScalableGroupDet, override=True)


#check if preset_mode directory exists on the drive
from pymodaq.daq_utils.daq_utils import get_set_local_dir
local_path = get_set_local_dir()

pid_path = get_set_pid_path()

preset_path= os.path.join(local_path, 'preset_modes')
if not os.path.isdir(preset_path):
    os.makedirs(preset_path)


class PresetManager():
    def __init__(self,msgbox=False):

        self.preset_params=None
        self.pid_type = False
        if msgbox:
            msgBox=QtWidgets.QMessageBox()
            msgBox.setText("Preset Manager?");
            msgBox.setInformativeText("What do you want to do?");
            cancel_button = msgBox.addButton(QtWidgets.QMessageBox.Cancel)
            new_button=msgBox.addButton("New", QtWidgets.QMessageBox.ActionRole)
            modify_button=msgBox.addButton('Modify', QtWidgets.QMessageBox.AcceptRole)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
            ret = msgBox.exec()

            if msgBox.clickedButton() == new_button:
                self.set_new_preset()

            elif msgBox.clickedButton() == modify_button:
                path = select_file(start_path=preset_path,save=False, ext='xml')
                if path != '':
                    self.set_file_preset(str(path))
            else: #cancel
                pass

    def set_file_preset(self, filename,show=True):
        """

        """
        self.pid_type = False
        children = custom_tree.XML_file_to_parameter(filename)
        self.preset_params = Parameter.create(title='Preset', name='Preset', type='group', children=children)
        if show:
            self.show_preset()


    def set_PID_preset(self, pid_model):
        self.pid_type = True
        filename = os.path.join(get_set_pid_path(), pid_model + '.xml')
        if os.path.isfile(filename):
            children = custom_tree.XML_file_to_parameter(filename)
            self.preset_params = Parameter.create(title='Preset', name='Preset', type='group', children=children)

        else:
            model_mod = importlib.import_module('pymodaq_pid_models')
            model = importlib.import_module('.' + pid_model, model_mod.__name__ + '.models')
            model_class = getattr(model, pid_model)
            actuators = model_class.actuators
            actuators_name = model_class.actuators_name
            detectors_type = model_class.detectors_type
            detectors_name = model_class.detectors_name
            detectors = model_class.detectors

            param = [
                    {'title': 'Filename:', 'name': 'filename', 'type': 'str', 'value': pid_model, 'readonly': True},
                        ]

            params_move = [{'title': 'Moves:', 'name': 'Moves', 'type': 'groupmove'}]  # PresetScalableGroupMove(name="Moves")]
            params_det = [{'title': 'Detectors:', 'name': 'Detectors',
                           'type': 'groupdet'}]  # [PresetScalableGroupDet(name="Detectors")]
            self.preset_params=Parameter.create(title='Preset', name='Preset', type='group', children=param+params_move+params_det)

            QtWidgets.QApplication.processEvents()
            for ind_act, act in enumerate(actuators):
                self.preset_params.child(('Moves')).addNew(act)
                self.preset_params.child('Moves', 'move{:02.0f}'.format(ind_act), 'name').setValue(
                    actuators_name[ind_act])
                QtWidgets.QApplication.processEvents()

            for ind_det, det in enumerate(detectors):
                self.preset_params.child(('Detectors')).addNew(detectors_type[ind_det]+'/'+det)
                self.preset_params.child('Detectors','det{:02.0f}'.format(ind_det), 'name').setValue(detectors_name[ind_det])
                QtWidgets.QApplication.processEvents()

        self.show_preset()

    def get_set_pid_model_params(self, model_file):
        model_mod = importlib.import_module('pymodaq_pid_models')
        self.preset_params.child('pid_settings', 'models', 'model_params').clearChildren()
        model = importlib.import_module('.' + model_file, model_mod.__name__+'.models')
        model_class = getattr(model, model_file)
        params = getattr(model_class, 'params')
        self.preset_params.child('pid_settings', 'models', 'model_params').addChildren(params)

    def set_new_preset(self):
        self.pid_type = False
        param = [
                {'title': 'Filename:', 'name': 'filename', 'type': 'str', 'value': 'preset_default'},
                {'title': 'Use PID as actuator:', 'name': 'use_pid', 'type': 'bool', 'value': False},
                {'title': 'Saving options:', 'name': 'saving_options', 'type': 'group', 'children': H5Saver.params},
                {'title': 'PID Settings:', 'name': 'pid_settings', 'type': 'group', 'visible': False, 'children': pid_params},
                ]
        params_move = [{'title': 'Moves:', 'name': 'Moves', 'type': 'groupmove'}]  # PresetScalableGroupMove(name="Moves")]
        params_det = [{'title': 'Detectors:', 'name': 'Detectors',
                       'type': 'groupdet'}]  # [PresetScalableGroupDet(name="Detectors")]
        self.preset_params=Parameter.create(title='Preset', name='Preset', type='group', children=param+params_move+params_det)
        self.preset_params.child('saving_options', 'save_type').hide()
        self.preset_params.child('saving_options', 'save_2D').hide()
        self.preset_params.child('saving_options', 'do_save').hide()
        self.preset_params.child('saving_options', 'N_saved').hide()
        self.preset_params.child('saving_options', 'custom_name').hide()
        self.preset_params.child('saving_options', 'show_file').hide()
        self.preset_params.child('saving_options', 'current_scan_name').hide()
        self.preset_params.child('saving_options', 'current_scan_path').hide()
        self.preset_params.child('saving_options', 'current_h5_file').hide()



        self.preset_params.sigTreeStateChanged.connect(self.parameter_tree_changed)

        self.show_preset()

    def parameter_tree_changed(self, param, changes):
        """
            Check for changes in the given (parameter,change,information) tuple list.
            In case of value changed, update the DAQscan_settings tree consequently.

            =============== ============================================ ==============================
            **Parameters**    **Type**                                     **Description**
            *param*           instance of pyqtgraph parameter              the parameter to be checked
            *changes*         (parameter,change,information) tuple list    the current changes state
            =============== ============================================ ==============================
        """
        for param, change, data in changes:
            path = self.preset_params.childPath(param)
            if change == 'childAdded':pass

            elif change == 'value':

                if param.name() == 'use_pid':
                    self.preset_params.child(('pid_settings')).show(param.value())
                if param.name() == 'model_class':
                    self.get_set_pid_model_params(param.value())

            elif change == 'parent':pass

    def show_preset(self):
        """

        """
        dialog = QtWidgets.QDialog()
        vlayout = QtWidgets.QVBoxLayout()
        tree = ParameterTree()
        tree.setMinimumWidth(400)
        tree.setMinimumHeight(500)
        tree.setParameters(self.preset_params, showTop=False)

        vlayout.addWidget(tree)
        dialog.setLayout(vlayout)
        buttonBox = QtWidgets.QDialogButtonBox(parent=dialog)

        buttonBox.addButton('Save', buttonBox.AcceptRole)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.addButton('Cancel', buttonBox.RejectRole)
        buttonBox.rejected.connect(dialog.reject)

        vlayout.addWidget(buttonBox)
        dialog.setWindowTitle('Fill in information about this preset')
        res = dialog.exec()

        if self.pid_type:
            path = pid_path
        else:
            path = preset_path

        if res == dialog.Accepted:
            # save preset parameters in a xml file
            #start = os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]
            #start = os.path.join("..",'daq_scan')
            custom_tree.parameter_to_xml_file(self.preset_params, os.path.join(path,
                                                                               self.preset_params.child(
                                                                                   ('filename')).value()))

            if not self.pid_type:
                #check if overshoot configuration and layout configuration with same name exists => delete them if yes
                overshoot_path = os.path.join(local_path, 'overshoot_configurations')
                file = os.path.splitext(self.preset_params.child(('filename')).value())[0]
                file = os.path.join(overshoot_path, file + '.xml')
                if os.path.isfile(file):
                    os.remove(file)

                layout_path = os.path.join(local_path, 'layout')
                file = os.path.splitext(self.preset_params.child(('filename')).value())[0]
                file = os.path.join(layout_path, file +'.dock')
                if os.path.isfile(file):
                    os.remove(file)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    #prog = PresetManager(True)

    prog = PresetManager(False)
    #prog.set_PID_preset('PIDModelMock')
    prog.set_new_preset()
    sys.exit(app.exec_())
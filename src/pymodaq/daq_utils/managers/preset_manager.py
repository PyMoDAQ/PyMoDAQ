from PyQt5 import QtWidgets
import sys
import os
from pyqtgraph.parametertree import Parameter, ParameterTree
from pymodaq.daq_utils.parameter import ioxml
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils import gui_utils
from pymodaq.daq_utils.managers import preset_manager_utils
import importlib
from pathlib import Path

logger = utils.set_logger(utils.get_module_name(__file__))

# check if preset_mode directory exists on the drive

pid_path = utils.get_set_pid_path()
preset_path = utils.get_set_preset_path()
overshoot_path = utils.get_set_overshoot_path()
layout_path = utils.get_set_layout_path()

pid_models = [mod['name'] for mod in utils.get_models()]

class PresetManager:
    def __init__(self, msgbox=False, path=None, extra_params=[], param_options=[]):

        if path is None:
            path = preset_path
        else:
            assert isinstance(path, Path)

        self.extra_params = extra_params
        self.param_options = param_options
        self.preset_path = path
        self.preset_params = None
        self.pid_type = False
        if msgbox:
            msgBox = QtWidgets.QMessageBox()
            msgBox.setText("Preset Manager?")
            msgBox.setInformativeText("What do you want to do?")
            cancel_button = msgBox.addButton(QtWidgets.QMessageBox.Cancel)
            new_button = msgBox.addButton("New", QtWidgets.QMessageBox.ActionRole)
            modify_button = msgBox.addButton('Modify', QtWidgets.QMessageBox.AcceptRole)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
            ret = msgBox.exec()

            if msgBox.clickedButton() == new_button:
                self.set_new_preset()

            elif msgBox.clickedButton() == modify_button:
                path = gui_utils.select_file(start_path=self.preset_path, save=False, ext='xml')
                if path != '':
                    self.set_file_preset(str(path))
            else:  # cancel
                pass

    def set_file_preset(self, filename, show=True):
        """

        """
        status = False
        self.pid_type = False
        children = ioxml.XML_file_to_parameter(filename)
        self.preset_params = Parameter.create(title='Preset', name='Preset', type='group', children=children)
        if show:
            status = self.show_preset()
        return status

    def get_set_pid_model_params(self, model_file):
        self.preset_params.child('model_settings').clearChildren()
        model = utils.get_models(model_file)
        if model is not None:
            params = model['class'].params
            self.preset_params.child('model_settings').addChildren(params)

    def set_new_preset(self):
        self.pid_type = False
        param = [
            {'title': 'Filename:', 'name': 'filename', 'type': 'str', 'value': 'preset_default'},
            {'title': 'Use PID as actuator:', 'name': 'use_pid', 'type': 'bool', 'value': False},
            # {'title': 'Saving options:', 'name': 'saving_options', 'type': 'group', 'children': H5Saver.params},
            {'title': 'PID models:', 'name': 'pid_models', 'type': 'list', 'visible': False,
             'values': pid_models},
            {'title': 'Model Settings:', 'name': 'model_settings', 'type': 'group', 'visible': False, 'children': []},
        ]
        params_move = [
            {'title': 'Moves:', 'name': 'Moves', 'type': 'groupmove'}]  # PresetScalableGroupMove(name="Moves")]
        params_det = [{'title': 'Detectors:', 'name': 'Detectors',
                       'type': 'groupdet'}]  # [PresetScalableGroupDet(name="Detectors")]
        self.preset_params = Parameter.create(title='Preset', name='Preset', type='group',
                                              children=param + self.extra_params + params_move + params_det)
        try:
            for option in self.param_options:
                if 'path' in option and 'options_dict' in option:
                    self.preset_params.child(option['path']).setOpts(**option['options_dict'])
        except Exception as e:
            logger.exception(str(e))

        if len(pid_models) != 0:
            self.get_set_pid_model_params(pid_models[0])

        self.preset_params.sigTreeStateChanged.connect(self.parameter_tree_changed)

        status = self.show_preset()
        return status

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
            if change == 'childAdded':
                pass

            elif change == 'value':

                if param.name() == 'use_pid':
                    self.preset_params.child('pid_models').show(param.value())
                    self.preset_params.child('model_settings').show(param.value())
                if param.name() == 'pid_models' and param.value() != '':
                    self.get_set_pid_model_params(param.value())

            elif change == 'parent':
                pass

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
        dialog.setWindowTitle('Fill in information about this manager')
        res = dialog.exec()

        if self.pid_type:
            path = pid_path
        else:
            path = self.preset_path

        if res == dialog.Accepted:
            # save managers parameters in a xml file
            # start = os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]
            # start = os.path.join("..",'daq_scan')
            ioxml.parameter_to_xml_file(
                self.preset_params, os.path.join(path, self.preset_params.child('filename').value()))

            if not self.pid_type:
                # check if overshoot configuration and layout configuration with same name exists => delete them if yes
                file = os.path.splitext(self.preset_params.child('filename').value())[0]
                file = os.path.join(overshoot_path, file + '.xml')
                if os.path.isfile(file):
                    os.remove(file)

                file = os.path.splitext(self.preset_params.child('filename').value())[0]
                file = os.path.join(layout_path, file + '.dock')
                if os.path.isfile(file):
                    os.remove(file)

        return res == dialog.Accepted


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # prog = PresetManager(True)
    prog = PresetManager(True)

    sys.exit(app.exec_())

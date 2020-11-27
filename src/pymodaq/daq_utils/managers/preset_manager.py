from PyQt5 import QtWidgets
import sys
import os
from pyqtgraph.parametertree import Parameter, ParameterTree
from pymodaq.daq_utils.parameter import ioxml
from pymodaq.daq_utils.parameter import pymodaq_ptypes
from pymodaq.daq_utils.managers import preset_manager_utils
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils import gui_utils
from pymodaq.daq_utils.h5modules import H5Saver
import importlib
from pymodaq.daq_utils.pid.pid_params import params as pid_params
from pathlib import Path

logger = utils.set_logger(utils.get_module_name(__file__))

# check if preset_mode directory exists on the drive

pid_path = utils.get_set_pid_path()
preset_path = utils.get_set_preset_path()
overshoot_path = utils.get_set_overshoot_path()
layout_path = utils.get_set_layout_path()


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

    def set_PID_preset(self, pid_model):
        self.pid_type = True
        filename = os.path.join(utils.get_set_pid_path(), pid_model + '.xml')
        if os.path.isfile(filename):
            children = ioxml.XML_file_to_parameter(filename)
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

            params_move = [
                {'title': 'Actuators:', 'name': 'Moves', 'type': 'groupmove'}]  # PresetScalableGroupMove(name="Moves")]
            params_det = [{'title': 'Detectors:', 'name': 'Detectors',
                           'type': 'groupdet'}]  # [PresetScalableGroupDet(name="Detectors")]
            self.preset_params = Parameter.create(title='Preset', name='Preset', type='group',
                                                  children=param + params_move + params_det)

            QtWidgets.QApplication.processEvents()
            for ind_act, act in enumerate(actuators):
                self.preset_params.child(('Moves')).addNew(act)
                self.preset_params.child('Moves', 'move{:02.0f}'.format(ind_act), 'name').setValue(
                    actuators_name[ind_act])
                QtWidgets.QApplication.processEvents()

            for ind_det, det in enumerate(detectors):
                self.preset_params.child(('Detectors')).addNew(detectors_type[ind_det] + '/' + det)
                self.preset_params.child('Detectors', 'det{:02.0f}'.format(ind_det), 'name').setValue(
                    detectors_name[ind_det])
                QtWidgets.QApplication.processEvents()

        status = self.show_preset()
        return status

    def get_set_pid_model_params(self, model_file):
        model_mod = importlib.import_module('pymodaq_pid_models')
        self.preset_params.child('pid_settings', 'models', 'model_params').clearChildren()
        model = importlib.import_module('.' + model_file, model_mod.__name__ + '.models')
        model_class = getattr(model, model_file)
        params = getattr(model_class, 'params')
        self.preset_params.child('pid_settings', 'models', 'model_params').addChildren(params)

    def set_new_preset(self):
        self.pid_type = False
        param = [
            {'title': 'Filename:', 'name': 'filename', 'type': 'str', 'value': 'preset_default'},
            {'title': 'Use PID as actuator:', 'name': 'use_pid', 'type': 'bool', 'value': False},
            # {'title': 'Saving options:', 'name': 'saving_options', 'type': 'group', 'children': H5Saver.params},
            {'title': 'PID Settings:', 'name': 'pid_settings', 'type': 'group', 'visible': False,
             'children': pid_params},
        ]
        params_move = [
            {'title': 'Moves:', 'name': 'Moves', 'type': 'groupmove'}]  # PresetScalableGroupMove(name="Moves")]
        params_det = [{'title': 'Detectors:', 'name': 'Detectors',
                       'type': 'groupdet'}]  # [PresetScalableGroupDet(name="Detectors")]
        self.preset_params = Parameter.create(title='Preset', name='Preset', type='group',
                                              children=param + self.extra_params + params_move + params_det)
        # self.preset_params.child('saving_options', 'save_type').hide()
        # self.preset_params.child('saving_options', 'save_2D').hide()
        # self.preset_params.child('saving_options', 'do_save').hide()
        # self.preset_params.child('saving_options', 'N_saved').hide()
        # self.preset_params.child('saving_options', 'custom_name').hide()
        # self.preset_params.child('saving_options', 'show_file').hide()
        # self.preset_params.child('saving_options', 'current_scan_name').hide()
        # self.preset_params.child('saving_options', 'current_scan_path').hide()
        # self.preset_params.child('saving_options', 'current_h5_file').hide()
        try:
            for option in self.param_options:
                if 'path' in option and 'options_dict' in option:
                    self.preset_params.child(option['path']).setOpts(**option['options_dict'])
        except Exception as e:
            logger.exception(str(e))

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
                    self.preset_params.child(('pid_settings')).show(param.value())
                if param.name() == 'model_class' and param.value() != '':
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

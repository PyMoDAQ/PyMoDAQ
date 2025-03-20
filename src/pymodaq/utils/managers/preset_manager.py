import os
from pathlib import Path
import sys

from qtpy import QtWidgets

import pymodaq_utils.config as config_mod
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_gui.utils.file_io import select_file
from pymodaq_gui.parameter import ParameterTree, Parameter
from pymodaq_gui.parameter import ioxml
from pymodaq_gui.messenger import dialog as dialogbox
from pymodaq.utils import config as config_mod_pymodaq
from pymodaq.extensions import get_models

import pymodaq.utils.managers.preset_manager_utils  # to register move and det types

logger = set_logger(get_module_name(__file__))

# check if preset_mode directory exists on the drive
preset_path = config_mod_pymodaq.get_set_preset_path()
overshoot_path = config_mod_pymodaq.get_set_overshoot_path()
layout_path = config_mod_pymodaq.get_set_layout_path()


class PresetManager:
    def __init__(self, msgbox=False, path=None, extra_params=[], param_options=[]):

        if path is None:
            path = preset_path
        else:
            assert isinstance(path, Path)

        self.extra_params = extra_params
        self.param_options = param_options
        self.preset_path = path
        self.preset_params: Parameter = None

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
                path = select_file(start_path=self.preset_path, save=False, ext='xml')
                if path != '':
                    self.set_file_preset(str(path))
            else:  # cancel
                pass

    @property
    def filename(self) -> str:
        try:
            return self.preset_params['filename']
        except:
            return None

    def set_file_preset(self, filename, show=True):
        """

        """
        status = False
        children = ioxml.XML_file_to_parameter(filename)
        self.preset_params = Parameter.create(title='Preset', name='Preset', type='group', children=children)
        if show:
            status = self.show_preset()
        return status


    def set_new_preset(self):
        param = [
            {'title': 'Filename:', 'name': 'filename', 'type': 'str', 'value': 'preset_default'},
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
                if len(data) > 1:
                    if 'params' in data[0].children():
                        data[0].child('params', 'main_settings', 'module_name').setValue(data[0].child('name').value())

            elif change == 'value':
                if param.name() == 'name':
                    param.parent().child('params', 'main_settings', 'module_name').setValue(param.value())

            elif change == 'parent':
                pass

    def show_preset(self):
        """

        """
        dialog = QtWidgets.QDialog()
        vlayout = QtWidgets.QVBoxLayout()
        tree = ParameterTree()
        # tree.setMinimumWidth(400)
        # tree.setMinimumHeight(500)
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

        path = self.preset_path
        file= None

        if res == dialog.Accepted:
            # save managers parameters in a xml file
            # start = os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]
            # start = os.path.join("..",'daq_scan')
            filename_without_extension = self.filename

            try:
                ioxml.parameter_to_xml_file(self.preset_params,
                                            path.joinpath(filename_without_extension),
                                            overwrite=False)
            except FileExistsError as currenterror:
                # logger.warning(str(currenterror)+"File " + filename_without_extension + ".xml exists")
                logger.warning(f"{currenterror} File {filename_without_extension}.xml exists")
                user_agreed = dialogbox(title='Overwrite confirmation',
                                        message="File exist do you want to overwrite it ?")
                if user_agreed:
                    ioxml.parameter_to_xml_file(self.preset_params,
                                                path.joinpath(filename_without_extension))
                    logger.warning(f"File {filename_without_extension}.xml overwriten at user request")
                else:
                    logger.warning(f"File {filename_without_extension}.xml wasn't saved at user request")
                    # emit status signal to dashboard to write : did not save ?
                pass

            # check if overshoot configuration and layout configuration with same name exists => delete them if yes
            over_shoot_file = overshoot_path.joinpath(self.filename + '.xml')
            over_shoot_file.unlink(missing_ok=True)

            layout_file = layout_path.joinpath(self.filename + '.dock')
            layout_file.unlink(missing_ok=True)

        return res == dialog.Accepted


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # prog = PresetManager(True)
    prog = PresetManager(True)

    sys.exit(app.exec_())

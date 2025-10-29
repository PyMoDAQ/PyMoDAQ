import os
from typing import Union
from pathlib import Path
import sys

from qtpy import QtWidgets
from qtpy.QtWidgets import QMessageBox, QDialogButtonBox, QDialog

import pymodaq_utils.config as config_mod
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.messenger import dialog, messagebox

from pymodaq_gui.utils.file_io import select_file
from pymodaq_gui.parameter import ParameterTree, Parameter
from pymodaq_gui.parameter import ioxml
from pymodaq_gui.messenger import dialog as dialogbox
from pymodaq_gui.utils.custom_app import CustomApp
from pymodaq.utils import config as config_mod_pymodaq

from pymodaq.utils.config import get_set_preset_path
from pymodaq.utils.managers.preset.utils  import PresetAction  # Also to register move and det types
from pymodaq.utils.managers.modules_manager import ModuleType

logger = set_logger(get_module_name(__file__))

# check if preset_mode directory exists on the drive
preset_path = config_mod_pymodaq.get_set_preset_path()
overshoot_path = config_mod_pymodaq.get_set_overshoot_path()
layout_path = config_mod_pymodaq.get_set_layout_path()


class PresetManager(CustomApp):

    def __init__(self ):
        super().__init__(parent=QtWidgets.QMainWindow())

        self.preset_path: Path = None
        self.preset_params: Parameter = None

        self.main_widget = QtWidgets.QWidget()
        self.mainwindow.setCentralWidget(self.main_widget)

        self.setup_ui()

    def setup_docks(self):
        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addWidget(self.settings_tree)
        self.tree.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.main_widget.setLayout(vlayout)

    def setup_actions(self):
        self.add_widget('preset_label', QtWidgets.QLabel('Configuration from Preset:'))
        self.add_widget('presets', QtWidgets.QComboBox(), tip='Name of the current preset',
                        kwargs={'setReadOnly': True})
        self.get_action('presets').addItems([
            path.stem for path in get_set_preset_path().iterdir() if path.suffix == '.xml'])

        self.add_action(PresetAction.NEW, 'New Preset', 'Add2',
                        tip='Create a new preset file')
        self.add_action(PresetAction.DELETE, 'Delete Preset', 'remove',
                        tip='Delete the current preset file')
        self.add_action(PresetAction.SAVE, 'Save Preset', 'Save',
                        tip='Save/Update the current configuration')
        self.add_action(PresetAction.RELOAD, 'Reload Preset', 'Refresh',
                        tip='Reload the current preset file')

    def connect_things(self):
        self.connect_action('presets', self.update_preset,
                            signal_name='currentTextChanged')
        self.connect_action(PresetAction.NEW, self.create_preset)
        self.connect_action(PresetAction.DELETE, self.delete_preset)
        self.connect_action(PresetAction.SAVE, self.save_check)
        self.connect_action(PresetAction.RELOAD, lambda: self.update_preset())

        self.get_action('presets').setCurrentText('preset_default')

    def update_preset(self, preset_file: Union[Path, str] = None):
        if preset_file is None:
            preset_file = get_set_preset_path().joinpath(
                f"{self.get_action('presets').currentText()}.xml"
            )
        if isinstance(preset_file, str):
            preset_file = get_set_preset_path().joinpath(f'{preset_file}.xml')
        if preset_file.exists():
            self.settings = preset_file
        else:
            params_act = [{'title': 'Actuators:', 'name': ModuleType.Actuator.value, 'type': 'groupmove'}]
            # PresetScalableGroupMove(name='Moves')]
            params_det = [
                {'title': 'Detectors:', 'name': ModuleType.Detector.value, 'type': 'groupdet'}
            ]  # [PresetScalableGroupDet(name='Detectors')]
            self.settings = Parameter.create(title='Preset', name='Preset', type='group',
                                             children=params_act + params_det,)

    def create_preset(self):
        text, ok = QtWidgets.QInputDialog.getText(None, 'Enter a NEW Preset name',
                                                  'Preset name:', QtWidgets.QLineEdit.Normal)
        if ok and text != '':
            self.get_action('presets').addItem(text)
            self.get_action('presets').setCurrentText(text)

    def delete_preset(self):
        current_preset = self.get_action('presets').currentText()
        user_agreed = dialogbox(
            title='Delete confirmation',
            message=f'Are you sure you want to delete the preset {current_preset} ?',
        )
        if user_agreed:
            preset_file = get_set_preset_path().joinpath(f'{current_preset}.xml')

            preset_file.unlink(missing_ok=True)
            logger.info(f'Preset file {preset_file} deleted')
            self.get_action('presets').removeItem(
                self.get_action('presets').currentIndex()
            )

    def save_check(self):
        current_preset = get_set_preset_path().joinpath(f"{self.get_action('presets').currentText()}.xml")
        if current_preset.exists():
            user_agreed = dialog(
                title='Overwrite confirmation',
                message='File exist do you want to overwrite it ?',
            )
            if not user_agreed:
                return
        ioxml.parameter_to_xml_file(
            self.settings,
            current_preset,
            overwrite=True,
        )
        logger.warning(
            f'File {current_preset} overwriten at user request'
        )

        # check if overshoot configuration and layout configuration with same name exists => delete them if yes
        over_shoot_file = overshoot_path.joinpath(f'{current_preset.stem}.xml')
        over_shoot_file.unlink(missing_ok=True)

        layout_file = layout_path.joinpath(f'{current_preset.stem}.dock')
        layout_file.unlink(missing_ok=True)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    prog = PresetManager()
    prog.mainwindow.show()

    sys.exit(app.exec_())

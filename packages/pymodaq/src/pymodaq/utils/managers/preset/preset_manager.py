import os
from typing import Union, TYPE_CHECKING
from pathlib import Path
import sys

from qtpy import QtWidgets, QtCore
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.messenger import dialog


from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter import ioxml
from pymodaq_gui.messenger import dialog as dialogbox
from pymodaq_gui.utils.custom_app import CustomApp
from pymodaq.utils import config as config_mod_pymodaq

from pymodaq.utils.config import get_set_preset_path
from pymodaq.utils.managers.preset.utils  import PresetAction  # Also to register move and det types
from pymodaq.utils.managers.modules_manager import ModuleType
from pymodaq.utils.exceptions import DetectorError, ActuatorError, MasterSlaveError

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer

logger = set_logger(get_module_name(__file__))

# check if preset_mode directory exists on the drive
preset_path = config_mod_pymodaq.get_set_preset_path()
overshoot_path = config_mod_pymodaq.get_set_overshoot_path()
layout_path = config_mod_pymodaq.get_set_layout_path()




class PresetManager(CustomApp):

    new_file = QtCore.Signal()

    def __init__(self ):
        super().__init__(parent=QtWidgets.QMainWindow())

        self.preset_path: Path = None
        self.preset_params: Parameter = None

        self.main_widget = QtWidgets.QWidget()
        self.mainwindow.setCentralWidget(self.main_widget)

        self.setup_ui()

    def show(self):
        self.mainwindow.show()

    def setup_docks(self):
        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addWidget(self.settings_tree)
        self.main_widget.setLayout(vlayout)

    @property
    def preset_filename(self) -> Path:
        """ Get the full path of the current preset file """
        return get_set_preset_path().joinpath(self.preset + '.xml')

    @property
    def preset(self) -> str:
        """ Get/Set the name of the current preset """
        return self.get_action('presets').currentText()

    @preset.setter
    def preset(self, preset_name: str):
        self.update_preset(preset_name)

    @property
    def presets(self) -> list[str]:
        """ Get/Set the name of all existing presets """
        return [path.stem for path in get_set_preset_path().iterdir() if path.suffix == '.xml']

    @property
    def presets_filename(self) -> list[Path]:
        """ Get the full path of the current preset file """
        return [path for path in get_set_preset_path().iterdir() if path.suffix == '.xml']

    def setup_actions(self):
        self.add_widget('preset_label', QtWidgets.QLabel('Configuration from Preset:'))
        self.add_widget('presets', QtWidgets.QComboBox(), tip='Name of the current preset',
                        kwargs={'setReadOnly': True})
        self.get_action('presets').addItems(self.presets + ['...'])

        self.add_action(PresetAction.COPY, 'Copy Preset', 'EditCopy')
        self.add_action(PresetAction.NEW, 'New Preset', 'ListAdd',
                        tip='Create a new preset file')
        self.add_action(PresetAction.DELETE, 'Delete Preset', 'ListRemove',
                        tip='Delete the current preset file')
        self.add_action(PresetAction.SAVE, 'Save Preset', 'DocumentSave',
                        tip='Save/Update the current configuration')
        self.add_action(PresetAction.RELOAD, 'Reload Preset', 'ViewRefresh',
                        tip='Reload the current preset file')

    def connect_things(self):
        self.connect_action('presets', self.update_preset,
                            signal_name='currentTextChanged')
        self.connect_action(PresetAction.COPY, self.copy_preset)
        self.connect_action(PresetAction.NEW, self.create_preset)
        self.connect_action(PresetAction.DELETE, self.delete_preset)
        self.connect_action(PresetAction.SAVE, lambda: self.save_check())
        self.connect_action(PresetAction.RELOAD, lambda: self.update_preset())

        self.get_action('presets').setCurrentText('preset_default')

    def update_preset(self, preset_file: Union[Path, str] = None):
        if preset_file == '...':
            self.create_preset()
            return

        if preset_file is None:
            preset_file = self.preset_filename

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
        self.get_action('presets').setCurrentText(preset_file.stem)

    def create_preset(self):
        text, ok = QtWidgets.QInputDialog.getText(None, 'Enter a NEW Preset name',
                                                  'Preset name:', QtWidgets.QLineEdit.EchoMode.Normal)
        if ok and text != '':
            presets = [self.get_action('presets').itemText(ind).lower() for
                       ind in range(self.get_action('presets').count())]
            if text.lower() not in presets:
                presets.append(text.lower())
                presets.sort()
                index = presets.index(text.lower())
                self.get_action('presets').insertItem(index-1, text)

            self.get_action('presets').setCurrentText(text)
            self.save_check()

    def copy_preset(self):
        text, ok = QtWidgets.QInputDialog.getText(None, 'Enter a NEW Preset name',
                                                  'Preset name:', QtWidgets.QLineEdit.EchoMode.Normal)
        if ok and text != '':
            self.save_check(text)
            presets = [self.get_action('presets').itemText(ind).lower() for
                       ind in range(self.get_action('presets').count())]
            if text.lower() not in presets:
                presets.append(text.lower())
                presets.sort()
                index = presets.index(text.lower())
                self.get_action('presets').insertItem(index-1, text)

            self.get_action('presets').setCurrentText(text)


    def delete_preset(self):
        current_preset = self.preset
        if current_preset == '...':
            return
        user_agreed = dialogbox(
            title='Delete confirmation',
            message=f'Are you sure you want to delete the preset {current_preset} ?',
        )
        if user_agreed:
            self.connect_action('presets', signal_name='currentTextChanged', connect=False)
            preset_file = get_set_preset_path().joinpath(f'{current_preset}.xml')

            preset_file.unlink(missing_ok=True)
            self.remove_preset_related_files(current_preset)

            logger.info(f'Preset file {preset_file} deleted')
            self.get_action('presets').removeItem(
                self.get_action('presets').currentIndex()
            )
            self.connect_action('presets', self.update_preset, signal_name='currentTextChanged')
            self.new_file.emit()  # notify that a preset has been deleted

    @staticmethod
    def remove_preset_related_files(preset_name: str):
        config_mod_pymodaq.get_set_roi_path().joinpath(preset_name).unlink(missing_ok=True)
        config_mod_pymodaq.get_set_layout_path().joinpath(preset_name).unlink(missing_ok=True)
        config_mod_pymodaq.get_set_overshoot_path().joinpath(preset_name).unlink(missing_ok=True)
        config_mod_pymodaq.get_set_remote_path().joinpath(preset_name).unlink(missing_ok=True)

    def save_check(self, preset_name: str = None):
        if preset_name is not None:
            current_preset = get_set_preset_path().joinpath(preset_name+'.xml')
        else:
            current_preset = self.preset_filename
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

        self.remove_preset_related_files(current_preset.stem)
        self.new_file.emit()

    def apply_preset_to_dashboard(self, preset: Union[str, Path], dashboard: 'DashBoard')\
            -> tuple[list['DAQ_Move'], list['DAQ_Viewer']]:
        """
        Load a preset file and create corresponding Control Modules in the Dashboard

        """
        self.update_preset(preset)

        actuators_modules = []
        detector_modules = []
        actuator_docks = []
        det_docks_settings = []
        det_docks_viewer = []

        # ################################################################
        # ##### sort plugins by IDs and within the same IDs by Master and Slave status
        plugins = []
        plugins += [
            {"type": ModuleType.Actuator, "value": child}
            for child in self.settings.child(ModuleType.Actuator.value).children()
        ]
        plugins += [
            {"type": ModuleType.Detector, "value": child}
            for child in self.settings.child(ModuleType.Detector.value).children()
        ]
        for plug in plugins:
            plug["ID"] = plug["value"].child("controller", "controller_ID").value()
            plug["status"] = plug["value"].child("controller", "controller_status").value()

        IDs = list(set([plug["ID"] for plug in plugins]))
        # %%
        plugins_sorted = []
        for id in IDs:
            plug_Ids = []
            for plug in plugins:
                if plug["ID"] == id:
                    plug_Ids.append(plug)
            plug_Ids.sort(key=lambda status: status["status"])
            plugins_sorted.append(plug_Ids)
        #################################################################
        #######################

        ind_det = -1
        for plug_IDs in plugins_sorted:
            for ind_plugin, plugin in enumerate(plug_IDs):
                plug_name = plugin["value"].child("name").value()
                plug_init = plugin["value"].child("init").value()
                plug_type = plugin["value"].child("type").value()


                dashboard.splash_sc.showMessage(
                    "Loading {:s} module: {:s}".format(plugin["type"], plug_name)
                )

                if plugin["type"] == ModuleType.Actuator:
                    dashboard.add_move(plug_name, None, plug_type, actuator_docks, None, actuators_modules)
                    if ind_plugin == 0:  # should be a master type plugin
                        if plugin["status"] != "Master":
                            raise MasterSlaveError(
                                f"The instrument {plug_name} should"
                                f" be defined as Master"
                            )
                        if plug_init:
                            actuators_modules[-1].init_hardware_ui()
                            QtWidgets.QApplication.processEvents()
                            dashboard.poll_init(actuators_modules[-1])
                            QtWidgets.QApplication.processEvents()
                            master_controller = actuators_modules[-1].controller
                        elif plugin["status"] == "Master" and len(plug_IDs) > 1:
                            raise MasterSlaveError(
                                f"The instrument {plug_name} defined as Master has to be "
                                f"initialized (init checked in the preset) in order to init "
                                f"its associated slave instrument"
                            )
                    else:
                        if plugin["status"] != "Slave":
                            raise MasterSlaveError(
                                f"The instrument {plug_name} should"
                                f" be defined as slave"
                            )
                        if plug_init:
                            actuators_modules[-1].controller = master_controller
                            actuators_modules[-1].init_hardware_ui()
                            QtWidgets.QApplication.processEvents()
                            dashboard.poll_init(actuators_modules[-1])
                            QtWidgets.QApplication.processEvents()
                else:
                    ind_det += 1
                    plug_dim = plugin["value"].child("dim").value()
                    dashboard.add_det(plug_name, None, det_docks_settings, det_docks_viewer, detector_modules,
                                      plug_type=plug_dim, plug_subtype=plug_type)
                    QtWidgets.QApplication.processEvents()

                    if ind_plugin == 0:  # should be a master type plugin
                        if plugin["status"] != "Master":
                            raise MasterSlaveError(
                                f"The instrument {plug_name} should"
                                f" be defined as Master"
                            )
                        if plug_init:
                            detector_modules[-1].init_hardware_ui()
                            QtWidgets.QApplication.processEvents()
                            dashboard.poll_init(detector_modules[-1])
                            QtWidgets.QApplication.processEvents()
                            master_controller = detector_modules[-1].controller

                        elif plugin["status"] == "Master" and len(plug_IDs) > 1:
                            raise MasterSlaveError(
                                f"The instrument {plug_name} defined as Master has to be "
                                f"initialized (init checked in the preset) in order to init "
                                f"its associated slave instrument"
                            )
                    else:
                        if plugin["status"] != "Slave":
                            raise MasterSlaveError(
                                f"The instrument {plug_name} should"
                                f" be defined as Slave"
                            )
                        if plug_init:
                            detector_modules[-1].controller = master_controller
                            detector_modules[-1].init_hardware_ui()
                            QtWidgets.QApplication.processEvents()
                            dashboard.poll_init(detector_modules[-1])
                            QtWidgets.QApplication.processEvents()

                    detector_modules[-1].settings.child(
                        "main_settings", "overshoot"
                    ).show()
                    detector_modules[-1].overshoot_signal[bool].connect(
                        dashboard.stop_moves_from_overshoot
                    )

        QtWidgets.QApplication.processEvents()
    #     # restore dock state if saved
    #
    #     self.title = self.preset_file.stem
    #     path = layout_path.joinpath(self.title + ".dock")
    #     if path.is_file():
    #         self.load_layout_state(path)
    #
    #     self.mainwindow.setWindowTitle(f"PyMoDAQ Dashboard: {self.title}")
    #     if self.pid_module is not None:
    #         self.pid_module.set_module_manager(detector_modules, actuators_modules)
    #     return actuators_modules, detector_modules
    # else:
    #     logger.error("Invalid file selected")
    #     return actuators_modules, detector_modules



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    prog = PresetManager()
    prog.mainwindow.show()

    sys.exit(app.exec_())

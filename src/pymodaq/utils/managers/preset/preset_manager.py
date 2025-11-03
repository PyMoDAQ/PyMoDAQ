from typing import Union, TYPE_CHECKING
from pathlib import Path
import sys

from qtpy import QtWidgets
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.messenger import dialog, messagebox
from pymodaq_gui.utils.dock import Dock

from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter import ioxml
from pymodaq.utils import config as config_mod_pymodaq

from pymodaq.utils.config import get_set_preset_path
from pymodaq.utils.managers.utils import ManagerBase, ManagerExternalActions
from pymodaq.utils.managers.modules_manager import ModuleType

from pymodaq.utils.exceptions import DetectorError, ActuatorError, MasterSlaveError
from pymodaq.control_modules.utils import ControllerStatus

from pymodaq.utils.managers.preset import utils  #  necessary to register preset parameter types

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer

logger = set_logger(get_module_name(__file__))

# check if preset_mode directory exists on the drive
preset_path = config_mod_pymodaq.get_set_preset_path()
overshoot_path = config_mod_pymodaq.get_set_overshoot_path()
layout_path = config_mod_pymodaq.get_set_layout_path()


class PresetManager(ManagerBase):

    params_act = [{'title': 'Actuators:', 'name': ModuleType.Actuator.value, 'type': 'groupmove'}]
    # PresetScalableGroupMove(name='Moves')]
    params_det = [{'title': 'Detectors:', 'name': ModuleType.Detector.value, 'type': 'groupdet'}]
    # [PresetScalableGroupDet(name='Detectors')][]

    params = params_act + params_det

    entry_type='preset'
    entry_extension='.xml'

    def __init__(self,
                 dashboard: 'DashBoard' = None,
                 menu: QtWidgets.QMenu = None,
                 toolbar: QtWidgets.QToolBar = None):

        super().__init__(dashboard=dashboard, menu=menu, toolbar=toolbar)

    ### Reimplemented Methods ####################################################
    def save_entries(self):
        """ Particular implementation to save entries for this inherited Manager """
        ioxml.parameter_to_xml_file(
            self.settings,
            self.entry_filename,
            overwrite=True,
        )

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        """Get the folder path where the managed entries are stored."""
        return get_set_preset_path()

    def apply_entry(self, entry: Union[str, Path] = None, **kwargs):
        """ Apply the selected entry file to the dashboard and adds Control Modules specified in it
        """
        try:

            if isinstance(entry, str):
                entry = self.get_entry_folder().joinpath(f'{entry}.xml')

            if len(self.dashboard.actuators_modules) != 0 or len(self.dashboard.detector_modules) != 0:
                ret = dialog(f'Warning!',
                             f'Are you sure you want '
                             f'to load a new {self.entry_type.capitalize()}: {entry}? \n')
                if ret:
                    self.dashboard.remove_actuators(self.dashboard.actuators_modules)
                    self.dashboard.remove_detectors(self.dashboard.detector_modules)
                else:
                    return

            self.dashboard.mainwindow.setVisible(False)
            for area in self.dashboard.dockarea.tempAreas:
                area.window().setVisible(False)

            self.dashboard.splash_sc.show()
            QtWidgets.QApplication.processEvents()
            self.dashboard.splash_sc.raise_()
            self.dashboard.splash_sc.showMessage("Loading Modules, please wait")
            logger.info(f"Loading {self.entry_type.capitalize()} file: {entry}")

            try:
                actuators_modules, detector_modules = self.create_control_modules_from_preset(entry)
            except (ActuatorError, DetectorError, MasterSlaveError) as error:
                self.dashboard.splash_sc.close()
                self.dashboard.mainwindow.setVisible(True)
                for area in self.dashboard.dockarea.tempAreas:
                    area.window().setVisible(True)
                messagebox(
                    severity="critical",
                    title=f"{self.entry_type.capitalize()} loading error",
                    text=f"""
                                <p>{error}</p>
                                <p>This error may be related to:</p>
                                <p>Saved {self.entry_type.capitalize()} file is not compatible anymore.</p>
                                <p>Please recreate the {self.entry_type.capitalize()} at <b>{entry}</b>.</p>
                     """,
                )
                logger.exception(str(error))

                self.dashboard.quit_fun()
                return

            if not (not actuators_modules and not detector_modules):
                self.dashboard.update_status(
                    f"{self.entry_type.capitalize()} mode ({entry.name}) has been loaded",
                    log_type="log",
                )
                self.dashboard.settings.child("loaded_files", "preset_file").setValue(
                    entry.name
                )
                self.dashboard.actuators_modules = actuators_modules
                self.dashboard.detector_modules = detector_modules

                self.dashboard.update_module_manager()

                for mov in actuators_modules:
                    mov.init_signal.connect(self.dashboard.update_init_tree)
                for det in detector_modules:
                    det.init_signal.connect(self.dashboard.update_init_tree)

                self.dashboard.splash_sc.close()
                self.dashboard.mainwindow.setVisible(True)
                for area in self.dashboard.dockarea.tempAreas:
                    area.window().setVisible(True)

                self.dashboard.update_init_tree()

                self.applied_entry.emit(entry.stem)

            logger.info(f"{self.entry_type.capitalize()} file: {entry} has been loaded")

        except Exception as e:
            logger.exception(str(e))

    def update_entry(self, entry: Union[str, Path] = None, **kwargs):
        """ Update the Manager UI after a given entry as been selected/updated """
        if entry.exists():
            self.settings = entry
        else:

            self.settings = Parameter.create(title='Preset', name='Preset', type='group',
                                             children=self.params)

    def setup_actions(self):
        #  nothing more than the base actions from the base class
        pass

    def connect_things(self):
        self.new_entry.connect(self.remove_preset_related_files)
        self.deleted_entry.connect(self.remove_preset_related_files)

    @staticmethod
    def remove_preset_related_files(preset_name: str):
        for file in config_mod_pymodaq.get_set_configurator_path(preset_name).iterdir():
            file.unlink(missing_ok=True)
        config_mod_pymodaq.get_set_configurator_path(preset_name).rmdir()
        config_mod_pymodaq.get_set_roi_path().joinpath(preset_name).unlink(missing_ok=True)
        config_mod_pymodaq.get_set_layout_path().joinpath(preset_name).unlink(missing_ok=True)
        config_mod_pymodaq.get_set_overshoot_path().joinpath(preset_name).unlink(missing_ok=True)
        config_mod_pymodaq.get_set_remote_path().joinpath(preset_name).unlink(missing_ok=True)

    def create_control_modules_from_preset(self, preset_file: Path) -> tuple[list['DAQ_Move'], list['DAQ_Viewer']]:
        """
        Load a preset file and create corresponding Control Modules in the Dashboard

        """
        actuators_modules: list[DAQ_Move] = []
        detector_modules: list[DAQ_Viewer] = []

        actuator_docks: list[Dock] = []
        detector_docks_settings: list[Dock] = []
        detector_docks_viewer: list[Dock] = []
        actuator_widgets: list[QtWidgets.QWidget] = []

        # ################################################################
        # ##### sort plugins by IDs and within the same IDs by Master and Slave status
        plugins = []
        plugins += [
            {"type": ModuleType.Actuator,
             "settings": child}
            for child in self.settings.child(ModuleType.Actuator.value).children()
        ]
        plugins += [
            {"type": ModuleType.Detector, "settings": child}
            for child in self.settings.child(ModuleType.Detector.value).children()
        ]
        for plug in plugins:
            plug["ID"] = plug["settings"].child("controller", "controller_ID").value()
            plug["status"] = plug["settings"].child("controller", "controller_status").value()

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

        # Add Control Modules to the Dashboard
        ind_det = -1
        for plug_IDs in plugins_sorted:
            for ind_plugin, plugin in enumerate(plug_IDs):
                plug_name = plugin["settings"].child("name").value()
                plug_type = plugin["settings"].child("info", "type").value()
                plug_init = plugin["settings"].child("info", "init").value()

                self.dashboard.splash_sc.showMessage(
                    "Loading {:s} module: {:s}".format(plugin["type"], plug_name)
                )

                if plugin["type"] == ModuleType.Actuator:

                    self.dashboard.add_move(plug_name, None, plug_type, actuator_docks, actuator_widgets,
                                            actuators_modules,
                                            ui_identifier=plugin["settings"].child("info", "ui").value())

                    if ind_plugin == 0:  # should be a master type plugin
                        if plugin["status"] != ControllerStatus.MASTER:
                            raise MasterSlaveError(f"The instrument {plug_name} should"
                                                   f" be defined as Master")
                        if plug_init:
                            actuators_modules[-1].apply_controller_parameters(plugin["settings"].child("controller"))
                            actuators_modules[-1].init_hardware_ui()
                            actuators_modules[-1].master = True
                            QtWidgets.QApplication.processEvents()
                            self.dashboard.poll_init(actuators_modules[-1])
                            QtWidgets.QApplication.processEvents()
                            master_controller = actuators_modules[-1].controller

                        elif plugin["status"] == ControllerStatus.MASTER and len(plug_IDs) > 1:
                            raise MasterSlaveError(
                                f"The instrument {plug_name} defined as Master has to be "
                                f"initialized (init checked in the preset) in order to init "
                                f"its associated slave instrument"
                            )
                    else:
                        if plugin["status"] != ControllerStatus.SLAVE:
                            raise MasterSlaveError(f"The instrument {plug_name} should"
                                                   f" be defined as slave")
                        if plug_init:
                            actuators_modules[-1].apply_controller_parameters(plugin["settings"].child("controller"))
                            actuators_modules[-1].controller = master_controller
                            actuators_modules[-1].init_hardware_ui()
                            QtWidgets.QApplication.processEvents()
                            self.dashboard.poll_init(actuators_modules[-1])
                            QtWidgets.QApplication.processEvents()
                else:
                    ind_det += 1
                    plug_dim = plugin["settings"].child("info", "dim").value()
                    self.dashboard.add_det(plug_name, None,
                                           detector_docks_settings, detector_docks_viewer, detector_modules,
                                           plug_dim, plug_type)
                    QtWidgets.QApplication.processEvents()

                    if ind_plugin == 0:  # should be a master type plugin
                        if plugin["status"] != ControllerStatus.MASTER:
                            raise MasterSlaveError(
                                f"The instrument {plug_name} should"
                                f" be defined as Master"
                            )
                        if plug_init:
                            detector_modules[-1].apply_controller_parameters(plugin["settings"].child("controller"))
                            detector_modules[-1].init_hardware_ui()
                            QtWidgets.QApplication.processEvents()
                            self.dashboard.poll_init(detector_modules[-1])
                            QtWidgets.QApplication.processEvents()
                            master_controller = detector_modules[-1].controller
                        elif plugin["status"] == ControllerStatus.MASTER and len(plug_IDs) > 1:
                            raise MasterSlaveError(
                                f"The instrument {plug_name} defined as Master has to be "
                                f"initialized (init checked in the preset) in order to init "
                                f"its associated slave instrument"
                            )
                    else:
                        if plugin["status"] != ControllerStatus.SLAVE:
                            raise MasterSlaveError(
                                f"The instrument {plug_name} should"
                                f" be defined as Slave"
                            )
                        if plug_init:
                            detector_modules[-1].controller = master_controller
                            detector_modules[-1].apply_controller_parameters(plugin["settings"].child("controller"))
                            detector_modules[-1].init_hardware_ui()
                            QtWidgets.QApplication.processEvents()
                            self.dashboard.poll_init(detector_modules[-1])
                            QtWidgets.QApplication.processEvents()

        QtWidgets.QApplication.processEvents()
        # restore dock state if saved

        self.dashboard.title = self.entry

        self.dashboard.mainwindow.setWindowTitle(f"PyMoDAQ Dashboard: {self.dashboard.title}")

        return actuators_modules, detector_modules


if __name__ == '__main__':
    from pymodaq_gui.utils.utils import mkQApp
    app = mkQApp('PresetManager')

    external_ui = QtWidgets.QMainWindow()
    toolbar = QtWidgets.QToolBar()
    menu = QtWidgets.QMenu('Preset Manager Menu')
    external_ui.addToolBar(toolbar)
    external_ui.menuBar().addMenu(menu)

    prog = PresetManager(menu=menu, toolbar=toolbar)
    prog.update_entry_base()
    prog.mainwindow.show()
    external_ui.show()
    sys.exit(app.exec_())

from typing import Union, TYPE_CHECKING
from pathlib import Path
import sys

from qtpy import QtWidgets

from pymodaq_gui.config_saver_loader import get_set_roi_path
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.messenger import dialog, messagebox
from pymodaq_gui.utils.dock import Dock

from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter import ioxml

from pymodaq.utils.config import get_set_preset_path, get_set_overshoot_path, get_set_layout_path, \
    get_set_configurator_path, get_set_remote_path
from pymodaq_gui.managers.manager_base import ManagerBase
from pymodaq.utils.managers.modules.utils import ModuleType

from pymodaq.utils.exceptions import DetectorError, ActuatorError, MasterSlaveError
from pymodaq.control_modules.utils import ControllerStatus
from pymodaq.utils.daq_utils import copy_preset
from pymodaq.utils.managers.preset import utils  # to register groupemove and groupdet Parameters

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer

logger = set_logger(get_module_name(__file__))

# check if preset_mode directory exists on the drive
preset_path = get_set_preset_path()
overshoot_path = get_set_overshoot_path()
layout_path = get_set_layout_path()


class PresetManager(ManagerBase):

    params_act = [{'title': 'Actuators:', 'name': ModuleType.Actuator.value, 'type': 'groupmove'}]
    # PresetScalableGroupMove(name='Moves')]
    params_det = [{'title': 'Detectors:', 'name': ModuleType.Detector.value, 'type': 'groupdet'}]
    # [PresetScalableGroupDet(name='Detectors')][]

    params = params_act + params_det

    entry_type = 'preset'
    entry_extension ='.xml'

    def __init__(self,
                 dashboard: 'DashBoard' = None):

        super().__init__(dashboard=dashboard)

    ### Reimplemented Methods ####################################################
    def list_managed_entries_path(self, **kwargs_to_entry_folder) -> list[Path]:
        """Should return a list of Path objects representing managed entries.

        Example:
        --------
        [path for path in get_set_preset_path().iterdir() if path.suffix == self.entry_extension]
        """
        entry_path = self.get_entry_folder(**kwargs_to_entry_folder)
        if not entry_path.exists():
            entry_path.mkdir(parents=True)
        if not entry_path.joinpath(f'default{self.entry_extension}').exists():
            copy_preset()
            self.update_entry()
        return [path for path in entry_path.iterdir() if path.suffix == self.entry_extension]

    def do_things_for_new_creation(self):
        for child in self.settings.child(ModuleType.Actuator.value).children():
            child.remove()
        for child in self.settings.child(ModuleType.Detector.value).children():
            child.remove()

    def save_entries(self, entry_path: Path = None):
        """ Particular implementation to save entries for this inherited Manager """

        if entry_path is None:
            entry_path = self.entry_filepath

        ioxml.parameter_to_xml_file(
            self.settings,
            entry_path,
            overwrite=True,
        )

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        """Get the folder path where the managed entries are stored."""
        return get_set_preset_path()

    def _execute_entry(self, entry: Path = None, **kwargs) -> bool:
        """ Execute the selected entry file to the dashboard and adds Control Modules specified in it

        Returns True if the entry has been applied otherwise False

        Should not be called directly, use :attr:`execute_entry` instead.
        """
        try:
            if len(self.dashboard.actuators_modules) != 0 or len(self.dashboard.detector_modules) != 0:
                ret = dialog(title=f'Warning!',
                             message=f'Are you sure you want '
                                     f'to load a new {self.entry_type.capitalize()}: {entry.stem}? \n')
                if ret:
                    self.dashboard.remove_actuators(self.dashboard.actuators_modules)
                    self.dashboard.remove_detectors(self.dashboard.detector_modules)
                    for area in self.dashboard.dockarea.tempAreas:
                        area.window().close()
                else:
                    return False

            if ('Moves' in [child.name() for child in self.settings.children()] or
                    'Detectors' in [child.name() for child in self.settings.children()]):
                plugins_sorted, plugin_list_message = self.list_control_modules_from_old_preset()
            else:
                plugins_sorted, plugin_list_message = self.list_control_modules_from_preset()

            self.show_subentries(plugin_list_message, title=f'Loading Preset: {self.entry}')

            self.dashboard.mainwindow.setVisible(False)
            for area in self.dashboard.dockarea.tempAreas:
                area.window().setVisible(False)

            QtWidgets.QApplication.processEvents()
            logger.info(f"Loading {self.entry_type.capitalize()} file: {entry}")

            try:
                if ('Moves' in [child.name() for child in self.settings.children()] or
                        'Detectors' in [child.name() for child in self.settings.children()]):
                    actuators_modules, detector_modules = self.create_control_modules_from_old_preset(plugins_sorted)
                else:
                    actuators_modules, detector_modules = (
                        self.create_control_modules_from_preset(plugins_sorted))
            except (ActuatorError, DetectorError, MasterSlaveError) as error:

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
                return False

            if not (not actuators_modules and not detector_modules):
                self.dashboard.update_status(
                    f"{self.entry_type.capitalize()} mode ({entry.name}) has been loaded",
                    log_type="log",
                )
                self.dashboard.actuators_modules = actuators_modules
                self.dashboard.detector_modules = detector_modules

                for mov in actuators_modules:
                    mov.init_signal.connect(self.dashboard.update_init_tree)
                for det in detector_modules:
                    det.init_signal.connect(self.dashboard.update_init_tree)

                self.dashboard.mainwindow.setVisible(True)
                for area in self.dashboard.dockarea.tempAreas:
                    area.window().setVisible(True)

                self.dashboard.update_init_tree()

            logger.info(f"{self.entry_type.capitalize()} file: {entry} has been loaded")
            return True

        except Exception as e:
            logger.exception(str(e))
            return False

    def _update_entry(self, entry: Union[str, Path] = None, **kwargs):
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
        for file in get_set_configurator_path(preset_name).iterdir():
            file.unlink(missing_ok=True)
        get_set_configurator_path(preset_name).rmdir()
        get_set_roi_path().joinpath(preset_name).unlink(missing_ok=True)
        get_set_layout_path().joinpath(preset_name).unlink(missing_ok=True)
        get_set_overshoot_path().joinpath(preset_name).unlink(missing_ok=True)
        get_set_remote_path().joinpath(preset_name).unlink(missing_ok=True)


    def list_control_modules_from_preset(self):
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

        plugin_list_message = []
        for plug_id in plugins_sorted:
            for plugin in plug_id:
                plugin_list_message.append(
                    f"Initializing {plugin['settings']['info', 'type']} {plugin['type'].value.capitalize()}:"
                    f" {plugin['settings']['name']}")

        return plugins_sorted, plugin_list_message

    def create_control_modules_from_preset(self, plugins_sorted) -> tuple[list['DAQ_Move'], list['DAQ_Viewer']]:
        """
        Load a preset file and create corresponding Control Modules in the Dashboard

        """
        actuators_modules: list[DAQ_Move] = []
        detector_modules: list[DAQ_Viewer] = []

        actuator_docks: list[Dock] = []
        detector_docks_viewer: list[Dock] = []
        actuator_widgets: list[QtWidgets.QWidget] = []

        # Add Control Modules to the Dashboard
        ind_module = -1
        ind_det = -1
        for plug_IDs in plugins_sorted:
            for ind_plugin, plugin in enumerate(plug_IDs):
                ind_module += 1
                plug_name = plugin["settings"].child("name").value()
                plug_type = plugin["settings"].child("info", "type").value()
                plug_init = plugin["settings"].child("info", "init").value()

                if plugin["type"] == ModuleType.Actuator or plugin["type"] == 'move':

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
                            self.dashboard.modules_manager.poll_init(actuators_modules[-1])
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
                            self.dashboard.modules_manager.poll_init(actuators_modules[-1])
                            QtWidgets.QApplication.processEvents()

                    self.subentries_model.set_status(ind_module, True)

                else:
                    ind_det += 1
                    plug_dim = plugin["settings"].child("info", "dim").value()
                    self.dashboard.add_det(plug_name, None,
                                           detector_docks_viewer, detector_modules,
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
                            self.dashboard.modules_manager.poll_init(detector_modules[-1])
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
                            self.dashboard.modules_manager.poll_init(detector_modules[-1])
                            QtWidgets.QApplication.processEvents()

                    self.subentries_model.set_status(ind_module, True)

        QtWidgets.QApplication.processEvents()
        self.close_subentries_display()
        # restore dock state if saved

        self.dashboard.title = self.entry

        self.dashboard.mainwindow.setWindowTitle(f"PyMoDAQ Dashboard: {self.dashboard.title}")

        return actuators_modules, detector_modules

    ##### BACKCOMPATIBILITY ###########
    def list_control_modules_from_old_preset(self):
        plugins = []
        plugins += [
            {"type": "move", "value": child}
            for child in self.settings.child("Moves").children()
        ]
        plugins += [
            {"type": "det", "value": child}
            for child in self.settings.child("Detectors").children()
        ]
        for plug in plugins:
            if plug["type"] == "det":
                try:
                    plug["ID"] = plug["value"][
                        "params", "detector_settings", "controller_ID"
                    ]
                    plug["status"] = plug["value"][
                        "params", "detector_settings", "controller_status"
                    ]
                except KeyError as e:
                    raise DetectorError
            else:
                try:
                    plug["ID"] = plug["value"][
                        "params", "move_settings", "multiaxes", "controller_ID"
                    ]
                    plug["status"] = plug["value"][
                        "params", "move_settings", "multiaxes", "multi_status"
                    ]
                except KeyError as e:
                    raise ActuatorError

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

        plugin_list_message = []
        for plug_id in plugins_sorted:
            for plugin in plug_id:
                module_type = ModuleType.Actuator if plugin['type'] == 'move' else ModuleType.Detector
                inst_plugin = (plugin['value']['params', 'main_settings', 'move_type'].capitalize()
                               if plugin['type'] == 'move'
                               else plugin['value']['params', 'main_settings', 'DAQ_type'] +
                                    '/' +
                                    plugin['value']['params', 'main_settings', 'detector_type'].capitalize())
                plugin_list_message.append(
                    f"Initializing {module_type} "
                    f"{inst_plugin}:"
                    f" {plugin['value']['name']}")

        return plugins_sorted, plugin_list_message

    def create_control_modules_from_old_preset(self, plugins_sorted) -> tuple[list['DAQ_Move'], list['DAQ_Viewer']]:
        """ allows to use old style presets to create control modules """

        actuators_modules: list[DAQ_Move] = []
        detector_modules: list[DAQ_Viewer] = []

        actuator_docks: list[Dock] = []
        detector_docks_viewer: list[Dock] = []
        actuator_widgets: list[QtWidgets.QWidget] = []

        ind_module = -1
        ind_det = -1
        for plug_IDs in plugins_sorted:
            for ind_plugin, plugin in enumerate(plug_IDs):
                ind_module += 1
                plug_name = plugin["value"].child("name").value()
                plug_init = plugin["value"].child("init").value()
                plug_settings = plugin["value"].child("params")

                if plugin["type"] == "move":
                    plug_type = plug_settings.child(
                        "main_settings", "move_type"
                    ).value()
                    self.dashboard.add_move(
                        plug_name,
                        None,
                        plug_type,
                        actuator_docks,
                        actuator_widgets,
                        actuators_modules,
                    )

                    if ind_plugin == 0:  # should be a master type plugin
                        if plugin["status"] != "Master":
                            raise MasterSlaveError(
                                f"The instrument {plug_name} should"
                                f" be defined as Master"
                            )
                        if plug_init:
                            actuators_modules[-1].init_hardware_ui()
                            QtWidgets.QApplication.processEvents()
                            self.dashboard.modules_manager.poll_init(actuators_modules[-1])
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
                            self.dashboard.modules_manager.poll_init(actuators_modules[-1])
                            QtWidgets.QApplication.processEvents()

                    self.subentries_model.set_status(ind_module, True)

                else:
                    ind_det += 1
                    plug_subtype = plug_settings["main_settings", "detector_type"]
                    plug_type = plug_settings['main_settings', 'DAQ_type']
                    self.dashboard.add_det(
                        plug_name,
                        None,
                        detector_docks_viewer,
                        detector_modules,
                        plug_type=plug_type,
                        plug_subtype=plug_subtype,
                    )
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
                            self.dashboard.modules_manager.poll_init(detector_modules[-1])
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
                            self.dashboard.modules_manager.poll_init(detector_modules[-1])
                            QtWidgets.QApplication.processEvents()

                    self.subentries_model.set_status(ind_module, True)

        QtWidgets.QApplication.processEvents()
        self.close_subentries_display()
        # restore dock state if saved

        self.dashboard.title = self.entry

        self.dashboard.mainwindow.setWindowTitle(f"PyMoDAQ Dashboard: {self.dashboard.title}")

        return actuators_modules, detector_modules
    ###################################


if __name__ == '__main__':
    from pymodaq_gui.qt_utils import mkQApp

    app = mkQApp('PresetManager')

    prog = PresetManager()
    external_ui = QtWidgets.QMainWindow()

    toolbar, menu = prog.get_external_toolbar_menu()
    external_ui.addToolBar(toolbar)
    external_ui.menuBar().addMenu(menu)

    prog.update_entry()
    prog.enable_actions(True)
    prog.mainwindow.show()
    external_ui.show()
    sys.exit(app.exec())

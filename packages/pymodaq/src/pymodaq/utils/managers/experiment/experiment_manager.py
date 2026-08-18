from dataclasses import dataclass
import qtpy
import warnings
from typing import Union, TYPE_CHECKING, Any

from pymodaq.control_modules.instruments import DAQTypesEnum

try:
    state_machine_available = True
    if qtpy.API_NAME.lower() == 'pyqt6':
        from PyQt6.QtStateMachine import QStateMachine, QState, QFinalState, QSignalTransition
    elif qtpy.API_NAME.lower() == 'pyside6':
        from qtpy.QtStateMachine import QStateMachine, QState, QFinalState, QSignalTransition
    elif qtpy.API_NAME.lower() == 'pyqt5':
        from PyQt5.QtCore.QtStateMachine import QStateMachine, QState, QFinalState, QSignalTransition
except ImportError:
    state_machine_available = False

from pymodaq.control_modules.move_utility_classes import HW_SETTINGS_KEY as ACTUATOR_SETTINGS_KEY
from pymodaq.control_modules.viewer_utility_classes import HW_SETTINGS_KEY as DETECTOR_SETTINGS_KEY
from pathlib import Path
import sys

from qtpy import QtWidgets, QtCore

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.messenger import dialog, messagebox
from pymodaq_gui.utils.dock import Dock

from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter import ioxml

from pymodaq.utils.config import get_set_experiment_path, get_set_overshoot_path, get_set_state_path, get_set_remote_path
from pymodaq_gui.config import get_set_layout_path, get_set_roi_path
from pymodaq_gui.managers.manager_base import ManagerBase
from pymodaq.utils.managers.modules.utils import ModuleType

from pymodaq.utils.exceptions import DetectorError, ActuatorError, MasterSlaveError
from pymodaq.control_modules.utils import ControllerStatus
from pymodaq.utils.daq_utils import copy_experiment
from pymodaq.utils.managers.experiment import utils  # noqa , to register groupemove and groupdet Parameters

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer

logger = set_logger(get_module_name(__file__))

# check if experiment directory exists on the drive
experiment_path = get_set_experiment_path()
overshoot_path = get_set_overshoot_path()
layout_path = get_set_layout_path()


@dataclass()
class PluginInfo:
    id: int
    name: str
    class_name: str
    type: ModuleType
    settings: Parameter
    is_master: bool
    do_init: bool
    ui: str = None
    daq_type: DAQTypesEnum = None


class ExperimentManager(ManagerBase):

    params_act = [{'title': 'Actuators:', 'name': ModuleType.Actuator.value, 'type': 'groupmove'}]
    params_det = [{'title': 'Detectors:', 'name': ModuleType.Detector.value, 'type': 'groupdet'}]

    params = params_act + params_det

    entry_type = 'experiment'
    entry_extension ='.xml'
    icon_name = 'experiment'

    def __init__(self,
                 dashboard: 'DashBoard' = None):

        super().__init__(dashboard=dashboard)
        self.actuators_modules: list[DAQ_Move] = []
        self.detector_modules: list[DAQ_Viewer] = []

    ### Reimplemented Methods ####################################################
    def list_managed_entries_path(self, **kwargs_to_entry_folder) -> list[Path]:
        """Should return a list of Path objects representing managed entries.

        Example:
        --------
        [path for path in get_set_experiment_path().iterdir() if path.suffix == self.entry_extension]
        """
        entry_path = self.get_entry_folder(**kwargs_to_entry_folder)
        if not entry_path.exists():
            entry_path.mkdir(parents=True)
        if not entry_path.joinpath(f'default{self.entry_extension}').exists():
            copy_experiment()
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
        return get_set_experiment_path()

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

            plugins_sorted, plugin_list_message = self.list_control_modules_from_preset()

            self.show_subentries(plugin_list_message, title=f'Loading Experiment: {self.entry}')

            self.dashboard.mainwindow.setVisible(False)
            for area in self.dashboard.dockarea.tempAreas:
                area.window().setVisible(False)

            QtWidgets.QApplication.processEvents()
            logger.info(f"Loading {self.entry_type.capitalize()} file: {entry}")


            if state_machine_available:
                self.create_control_modules_using_machine(plugins_sorted)
            else:
                self.create_control_modules_from_preset(plugins_sorted)
                self.finalize_execute()

        except Exception as e:
            self.dashboard.mainwindow.setVisible(True)
            for area in self.dashboard.dockarea.tempAreas:
                area.window().setVisible(True)
            logger.exception(str(e))
            return False

    def finalize_execute(self):
        self.close_subentries_display()
        self.dashboard.title = self.entry
        self.dashboard.mainwindow.setWindowTitle(f"PyMoDAQ Dashboard: {self.dashboard.title}")

        if not (not self.actuators_modules and not self.detector_modules):
            self.dashboard.update_status(
                f"{self.entry_type.capitalize()} ({self.entry_filepath.name}) has been loaded",
                log_type="log",
            )
            self.dashboard.actuators_modules = list(self.actuators_modules)
            self.dashboard.detector_modules = list(self.detector_modules)

            for module in self.actuators_modules + self.detector_modules:
                module.init_signal.connect(self.dashboard.update_init_tree)

            self.dashboard.mainwindow.setVisible(True)
            for area in self.dashboard.dockarea.tempAreas:
                area.window().setVisible(True)

            self.dashboard.update_init_tree()

        logger.info(f"{self.entry_type.capitalize()} file: {self.entry_filepath} has been loaded")
        self.set_entry_applied(True)


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
        for file in get_set_state_path(preset_name).iterdir():
            file.unlink(missing_ok=True)
        get_set_state_path(preset_name).rmdir()
        get_set_roi_path().joinpath(preset_name).unlink(missing_ok=True)
        get_set_layout_path().joinpath(preset_name).unlink(missing_ok=True)
        get_set_overshoot_path().joinpath(preset_name).unlink(missing_ok=True)
        get_set_remote_path().joinpath(preset_name).unlink(missing_ok=True)


    @staticmethod
    def _group_plugins_by_id(plugins: list[PluginInfo]) -> list[list[PluginInfo]]:
        """Group a flat list of plugin dicts by their 'ID' key, sorted by 'status' within each group."""
        IDs = list(set(plug.id for plug in plugins))

        plugins_sorted = []
        for id in IDs:
            plug_ids: list[PluginInfo] = [plug for plug in plugins if plug.id == id]  # group plugins having the same id
            plug_ids.sort(key=lambda p: p.is_master, reverse=True)  # sort them with the fist being Master (
            plugins_sorted.append(plug_ids)
        return plugins_sorted

    def list_control_modules_from_preset(self) -> tuple[list[list[PluginInfo]], list[str]]:
        # ################################################################

        # ##### sort plugins by IDs and within the same IDs by Master and Slave status
        plugins: list[PluginInfo] = []

        for child in (self.settings.child(ModuleType.Actuator.value).children() +
            self.settings.child(ModuleType.Detector.value).children()):
            plugins.append(
                PluginInfo(
                    id = child['controller', 'controller_ID'],
                    name = child['name'],
                    class_name=child['info', 'type'],
                    type = ModuleType.Actuator if ModuleType.Actuator.value.lower() == child.parent().name().lower() else ModuleType.Detector,
                    settings=child,
                    is_master=child["controller", "controller_status"] == ControllerStatus.MASTER.value,
                    do_init=child['info', 'init'],
                    ui = child['info', 'ui'] if 'ui' in [ch.name() for ch in child.child('info').children()] else None,
                    daq_type=DAQTypesEnum[child['info', 'dim']] if 'dim' in [ch.name() for ch in child.child('info').children()] else None,
                )
            )

        plugins_sorted = self._group_plugins_by_id(plugins)

        plugin_list_message = []
        for plug_id in plugins_sorted:
            for plugin in plug_id:
                plugin_list_message.append(
                    f"Initializing {plugin.class_name} {plugin.type.value.capitalize()}:"
                    f" {plugin.name}")

        return plugins_sorted, plugin_list_message

    def create_control_modules_from_preset(self, plugins_sorted: list[list[PluginInfo]]) -> tuple[list['DAQ_Move'], list['DAQ_Viewer']]:
        """
        Load a experiment file and create corresponding Control Modules in the Dashboard

        """
        self.actuators_modules: list[DAQ_Move] = []
        self.detector_modules: list[DAQ_Viewer] = []

        # Add Control Modules to the Dashboard
        ind_module = -1
        for plug_IDs in plugins_sorted:
            for ind_plugin, plugin in enumerate(plug_IDs):
                ind_module += 1
                plug_name = plugin.name
                plug_type = plugin.class_name
                plug_init = plugin.do_init

                if plugin.type == ModuleType.Actuator:

                    self.actuators_modules.append(self.dashboard.add_move(plug_name, plug_type,
                                                                          ui_identifier=plugin.ui))

                    if ind_plugin == 0:  # should be a master type plugin
                        if not plugin.is_master:
                            raise MasterSlaveError(f"The instrument {plug_name} should"
                                                   f" be defined as Master")
                        if plug_init:
                            self.actuators_modules[-1].apply_controller_parameters(plugin.settings.child("controller"))
                            self.actuators_modules[-1].init_hardware_ui()
                            self.actuators_modules[-1].master = True
                            QtWidgets.QApplication.processEvents()
                            self.dashboard.modules_manager.poll_init(self.actuators_modules[-1])
                            QtWidgets.QApplication.processEvents()
                            master_controller = self.actuators_modules[-1].controller

                        elif plugin.is_master and len(plug_IDs) > 1:
                            raise MasterSlaveError(
                                f"The instrument {plug_name} defined as Master has to be "
                                f"initialized (init checked in the experiment) in order to init "
                                f"its associated slave instrument",
                            )
                    else:
                        if plugin.is_master:
                            raise MasterSlaveError(f"The instrument {plug_name} should"
                                                   f" be defined as slave")
                        if plug_init:
                            self.actuators_modules[-1].apply_controller_parameters(plugin.settings.child("controller"))
                            self.actuators_modules[-1].controller = master_controller
                            self.actuators_modules[-1].init_hardware_ui()
                            QtWidgets.QApplication.processEvents()
                            self.dashboard.modules_manager.poll_init(self.actuators_modules[-1])
                            QtWidgets.QApplication.processEvents()

                    self.subentries_model.set_status(ind_module, True)

                else:
                    plug_daq_type = plugin.daq_type
                    self.detector_modules.append(self.dashboard.add_det(plug_name,
                                                                        plug_daq_type,
                                                                        plug_type))
                    QtWidgets.QApplication.processEvents()

                    if ind_plugin == 0:  # should be a master type plugin
                        if not plugin.is_master:
                            raise MasterSlaveError(
                                f"The instrument {plug_name} should"
                                f" be defined as Master",
                            )
                        if plug_init:
                            self.detector_modules[-1].apply_controller_parameters(plugin.settings.child("controller"))
                            self.detector_modules[-1].init_hardware_ui()
                            QtWidgets.QApplication.processEvents()
                            self.dashboard.modules_manager.poll_init(self.detector_modules[-1])
                            QtWidgets.QApplication.processEvents()
                            master_controller = self.detector_modules[-1].controller
                        elif plugin.is_master and len(plug_IDs) > 1:
                            raise MasterSlaveError(
                                f"The instrument {plug_name} defined as Master has to be "
                                f"initialized (init checked in the experiment) in order to init "
                                f"its associated slave instrument",
                            )
                    else:
                        if plugin.is_master:
                            raise MasterSlaveError(
                                f"The instrument {plug_name} should"
                                f" be defined as Slave",
                            )
                        if plug_init:
                            self.detector_modules[-1].controller = master_controller
                            self.detector_modules[-1].apply_controller_parameters(plugin.settings.child("controller"))
                            self.detector_modules[-1].init_hardware_ui()
                            QtWidgets.QApplication.processEvents()
                            self.dashboard.modules_manager.poll_init(self.detector_modules[-1])
                            QtWidgets.QApplication.processEvents()

                self.subentries_model.set_status(ind_module, True)

        QtWidgets.QApplication.processEvents()

        return self.actuators_modules, self.detector_modules

    def create_control_modules_using_machine(self, plugins_sorted):
        self.actuators_modules: list[DAQ_Move] = []
        self.detector_modules: list[DAQ_Viewer] = []

        self.machine = CreateAddModules(self, plugins_sorted)
        self.machine.all_instruments_added.connect(self.finalize_execute)
        self.machine.start()


class CreateAddModules(QtCore.QObject):

    instrument_created = QtCore.Signal()
    all_instruments_added = QtCore.Signal()
    module_added = QtCore.Signal()
    controller_obtained = QtCore.Signal()

    def __init__(self, manager: ExperimentManager, plugins: list[list[PluginInfo]], parent=None):
        super().__init__(parent)
        self.manager = manager

        self._current_module: DAQ_Move | DAQ_Viewer = None
        self._current_plugin: PluginInfo = None
        self._current_controller: Any = None

        self.machine = QStateMachine()
        self.create_module_state = QState()
        self.set_module_type_state = QState()
        self.add_module_state = QState()
        self.init_module_state = QState()
        self.get_controller_state = QState()
        self.done_module_state = QFinalState()

        self.setup_machine()
        self.plugins = plugins
        self.ind_master_plugin = 0
        self.ind_id_plugin = 0
        self._ind_module = -1

    def start(self):
        self.machine.start()

    def setup_machine(self):

        self.machine.addState(self.create_module_state)
        self.machine.addState(self.set_module_type_state)
        self.machine.addState(self.add_module_state)
        self.machine.addState(self.init_module_state)
        self.machine.addState(self.get_controller_state)
        self.machine.addState(self.done_module_state)
        self.machine.setInitialState(self.create_module_state)

        self.create_module_state.entered.connect(self.create_module)
        self.set_module_type_state.entered.connect(self.set_module_type)
        self.add_module_state.entered.connect(self.add_module)
        self.init_module_state.entered.connect(self.init_module)
        self.get_controller_state.entered.connect(self.get_controller)


        self.create_module_state.addTransition(self.instrument_created,
                                               self.set_module_type_state)
        self.add_module_state.addTransition(self.module_added, self.init_module_state)
        self.get_controller_state.addTransition(self.controller_obtained, self.create_module_state)
        self.done_module_state.entered.connect(self.all_instruments_added.emit)

    def create_module(self):
        if self.ind_master_plugin == len(self.plugins):
            self.manager.close_subentries_display()
            self.create_module_state.addTransition(self.done_module_state)
            return

        self._current_plugin: PluginInfo = self.plugins[self.ind_master_plugin][self.ind_id_plugin]
        plugin_info = self._current_plugin

        if self._current_plugin.is_master and not self._current_plugin.do_init:
            self.machine.stop()
            raise MasterSlaveError(
                                f"The instrument {plugin_info.name} defined as Master has to be "
                                f"initialized (init checked in the experiment) in order to init "
                                f"its associated slave instrument",
                            )
        elif self._current_plugin.is_master and self.ind_id_plugin > 0:
            self.machine.stop()
            raise MasterSlaveError(
                f"The instrument {plugin_info.name} should be defined as Slave",
            )
        elif not self._current_plugin.is_master and self.ind_id_plugin == 0:
            self.machine.stop()
            raise MasterSlaveError(
                f"The instrument {plugin_info.name} should be defined as Master",
            )

        # loop through all the plugin info (first by common id, then...)
        if self.ind_id_plugin == len(self.plugins[self.ind_master_plugin]) - 1:
            self.ind_master_plugin += 1
            self.ind_id_plugin = 0
        else:
            self.ind_id_plugin += 1
        self._ind_module += 1

        # clear previous transitions dependent on created module if any before changing the reference of self._current_module
        for transition in self.set_module_type_state.transitions():
            self.set_module_type_state.removeTransition(transition)
        for transition in self.init_module_state.transitions():
            self.init_module_state.removeTransition(transition)

        # create module
        if plugin_info.type == ModuleType.Actuator:
            self._current_module = self.manager.dashboard.create_actuator(
                plugin_info.name, plugin_info.class_name,
                ui_identifier=plugin_info.ui)
            self.manager.actuators_modules.append(self._current_module)

        elif plugin_info.type == ModuleType.Detector:
            self._current_module = self.manager.dashboard.create_detector(plugin_info.name,
                                                                          plugin_info.daq_type)
            self.manager.detector_modules.append(self._current_module)

        # create next transitions if module dependent
        self.set_module_type_state.addTransition(self._current_module.instrument_changed, self.add_module_state)
        self.init_module_state.addTransition(self._current_module.init_signal, self.get_controller_state)

        # fire signal to move on to the set_type state
        self.instrument_created.emit()

    def set_module_type(self):
        if self._current_plugin.type == ModuleType.Actuator:
            self.manager.dashboard.set_actuator_type(self._current_module, self._current_plugin.class_name)
        else:
            self.manager.dashboard.set_detector_type(self._current_module,
                                                     self._current_plugin.daq_type,
                                                     self._current_plugin.class_name)

        # signal to transition to next state is done within each module through its instrument_changed signal

    def add_module(self):
        if self._current_plugin.type == ModuleType.Actuator:
            self.manager.dashboard.add_actuator(self._current_module)
        else:
            self.manager.dashboard.add_detector(self._current_module)

        #manually fire the signal to transition
        self.module_added.emit()

    def init_module(self):
        self._current_module.apply_controller_parameters(self._current_plugin.settings.child("controller"))

        if not self._current_plugin.is_master:
            self._current_module.controller = self._current_controller
        self._current_module.init_hardware_ui()

    def get_controller(self):
        if self._current_plugin.is_master:
            self._current_controller = self._current_module.controller
        self.manager.subentries_model.set_status(self._ind_module, True)
        self.controller_obtained.emit()


if __name__ == '__main__':
    from pymodaq_gui.qt_utils import mkQApp

    app = mkQApp('ExperimentManager')

    prog = ExperimentManager()
    external_ui = QtWidgets.QMainWindow()

    toolbar, menu = prog.get_external_toolbar_menu()
    external_ui.addToolBar(toolbar)
    external_ui.menuBar().addMenu(menu)

    prog.update_entry()
    prog.enable_actions(True)
    prog.mainwindow.show()
    external_ui.show()
    sys.exit(app.exec())

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import itertools
import sys
import datetime
import subprocess
from pathlib import Path

from typing import Union, List, Any, TYPE_CHECKING, Sequence, Callable
import argparse

from qtpy import QtGui, QtWidgets, QtCore
from qtpy.QtCore import Qt, QThread, Signal, QSize
from qtpy.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QDialogButtonBox,
    QMessageBox,
)

from pymodaq.control_modules.thread_commands import ControllerStatus
from pymodaq.utils.managers.modules import ModuleType
from pymodaq.utils.managers.modules.loader import ModuleLoader, PluginInfo
from pymodaq.utils.managers.roi_manager.roi_manager import ROIManager
from pymodaq.control_modules.instruments import find_actuator_class_from_name
from pymodaq.control_modules.enums import DAQTypesEnum
from pymodaq.control_modules.move_utility_classes import UiType
from pymodaq.control_modules.utils import ControllerAndThread
from pymodaq.utils.managers.roi_manager.roi_manager import ROIManager

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import utils
from pymodaq_utils.utils import ThreadCommand
from pymodaq_utils.config import GlobalConfig as Config
from pymodaq_utils.enums import BaseEnum, StrEnum

from pymodaq_gui.parameter import ParameterTree, Parameter
from pymodaq_gui.utils import DockArea, Dock, select_file
import pymodaq_gui.utils.layout as layout_mod
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.managers.roi_viewer_manager import ROISaver
from pymodaq_gui.utils.custom_app import CustomApp
from pymodaq_gui.utils.shared_ui import MenuToolbarNames
from pymodaq_gui.config import get_set_layout_path, get_set_roi_path
from pymodaq_gui.utils.widgets.window import make_window

from pymodaq.utils.managers.modules.modules_manager import ModulesManager
from pymodaq.utils.managers.experiment.experiment_manager import ExperimentManager
from pymodaq.utils.managers.overshoot.overshooter import Overshooter
from pymodaq.utils.compact_dock_manager import ActuatorCompactDock, DetectorCompactDock
from pymodaq.utils.daq_utils import get_instrument_plugins

from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.control_modules.daq_move_ui.factory import ActuatorUIFactory
from pymodaq.control_modules.daq_viewer_ui.viewer_selector import SelectedModule
from pymodaq.utils.gui_utils.loader_utils import create_extension
from pymodaq.utils.leco.pymodaq_listener import LECODashboardCommands, DashboardActorListener, LECOComponentMixin
from pymodaq.utils.managers.extension.extension_manager import ExtensionManager

from pymodaq.extensions.utils import get_extensions
from pymodaq.extensions import ExtensionEnum
from pymodaq.utils.shared_ui import SharedUI
from pymodaq.utils.managers.state.state_manager import StateManager

from pymodaq_gui.managers.manager_base import ManagerActions # should be imported afterwards



if TYPE_CHECKING:
    from pymodaq.extensions.custom_ext import CustomExt

logger = set_logger(get_module_name(__file__))

config = Config()


get_instrument_plugins()
extensions = get_extensions()


class ManagerEnums(BaseEnum):
    experiment = 0
    remote = 1
    overshoot = 2
    roi = 3
    configuration = 4
    

class PymodaqUpdateTableWidget(QTableWidget):
    """
    A class to represent PyMoDAQ and its subpackages'
    available updates as a table.
    """

    def __init__(self):
        super().__init__()
        self._row = 0

    def setHorizontalHeaderLabels(self, labels):
        super().setHorizontalHeaderLabels(labels)
        self.setColumnCount(len(labels))

    def append_row(self, package, current_version, available_version):
        # Add labels
        self.setItem(self._row, 0, QTableWidgetItem(str(package)))
        self.setItem(self._row, 1, QTableWidgetItem(str(current_version)))
        self.setItem(self._row, 2, QTableWidgetItem(str(available_version)))

        self._row += 1

    def sizeHint(self):
        self.resizeColumnsToContents()
        self.resizeRowsToContents()

        # Compute the size to adapt the window (header + borders + sum of all the elements)
        width = (
            self.verticalHeader().width()
            + self.frameWidth() * 2
            + sum([self.columnWidth(i) for i in range(self.columnCount())])
        )

        height = (
            self.horizontalHeader().height()
            + self.frameWidth() * 2
            + sum([self.rowHeight(i) for i in range(self.rowCount())])
        )

        return QSize(width, height)


class DashBoard(CustomApp, LECOComponentMixin):
    """
    Main class initializing a DashBoard interface to display det and move modules and logger"""
    status_signal = Signal(str)
    config_changed = QtCore.Signal()
    # will be emitted when the user changed anything in the configuration files (emitted from SharedUI)
    # included in CustomExt by default but Dashboard is special with that respect

    settings_name = "dashboard_settings"
    _splash_sc = None

    params = [
        {"title": "Log level", "name": "log_level", "type": "list",
         "value": config("utils", "general", "debug_level")[0],
         "limits": config("utils", "general", "debug_level")},
        {"title": "Loaded experiments", "name": "loaded_files", "type": "group",
         "children": [
             {"title": "Preset file", "name": "preset_file", "type": "str", "value": "", "readonly": True,},
             {"title": "Overshoot file", "name": "overshoot_file", "type": "str", "value": "", "readonly": True,},
             {"title": "Layout file", "name": "layout_file", "type": "str", "value": "", "readonly": True},
             {"title": "ROI file", "name": "roi_file", "type": "str", "value": "", "readonly": True},
             {"title": "Remote file", "name": "remote_file", "type": "str", "value": "", "readonly": True},
         ],
         },
        {"title": "Actuators Init.", "name": "actuators", "type": "group","children": []},
        {"title": "Detectors Init.", "name": "detectors", "type": "group", "children": []},
    ]

    def __init__(self, parent: Union[DockArea]):
        """

        Parameters
        ----------
        """

        CustomApp.__init__(self, parent, create_app_toolbar=False)
        LECOComponentMixin.__init__(self, DashboardActorListener)

        logger.info("Initializing Dashboard")
        self.extra_params = []
        self._docks_viewer: list[Dock] = []
        self.wait_time = 1000
        self.log_module = None
        self.pid_module = None
        self.pid_window = None
        self.retriever_module = None
        self.database_module = None
        self.extensions: dict[str, CustomExt] = dict([])
        self.extension_windows = []
        self.experiment_manager: ExperimentManager = None  # instanciation in do_things_after_ui_setup
        self.state_manager: StateManager = None  # instanciation in do_things_after_ui_setup
        self.overshooter: Overshooter = None  # instanciation in do_things_after_ui_setup
        self.roi_manager: ROIManager = None  # instanciation in do_things_after_ui_setup
        self.dockarea.dock_signal.connect(self.save_layout_state_auto)

        self.title = ""

        self.module_loader: ModuleLoader = None
        self.roi_saver: ROISaver = None

        self.remote_timer = QtCore.QTimer(self)
        self.remote_manager = None
        self.shortcuts = dict([])
        self.joysticks = dict([])
        self.ispygame_init = False

        self.modules_manager = ModulesManager()

        self.actuators_modules: list[DAQ_Move] = []
        self.detector_modules: list[DAQ_Viewer] = []

        self.compact_actuator_manager: ActuatorCompactDock = None
        self.compact_detector_manager: DetectorCompactDock = None

        self._scripted_experiment_load = False

        self.setup_ui()

        logger.info("Dashboard Initialized")

    @property
    def actuators_modules(self) -> list[DAQ_Move]:
        return self.modules_manager.actuators_all

    @actuators_modules.setter
    def actuators_modules(self, modules: list[DAQ_Move]):
        self.modules_manager.actuators_all = modules

    @property
    def detector_modules(self) -> list[DAQ_Viewer]:
        return self.modules_manager.detectors_all

    @detector_modules.setter
    def detector_modules(self, modules: list[DAQ_Viewer]):
        self.modules_manager.detectors_all = modules

    def do_things_after_ui_setup(self):
        self.experiment_manager = ExperimentManager(dashboard=self)
        self.experiment_manager.update_entry()
        self.experiment_manager.entry = 'default'
        self.experiment_manager.applied_entry.connect(self.do_things_after_experiment_set)
        self.state_manager = StateManager(dashboard=self)
        self.experiment_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('experiment'),
                                                          menu=self.get_menu('experiment'))
        self.experiment_manager.update_menu(self.get_menu('experiment'))
        self.state_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('state'),
                                                     menu=self.get_menu('state'))
        self.state_manager.update_menu(self.get_menu('state'))
        self.roi_manager = ROIManager(dashboard=self)
        self.roi_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('rois'),
                                                   menu=self.get_menu('rois'))
        self.overshooter = Overshooter(dashboard=self)
        self.overshooter.get_external_toolbar_menu(toolbar=self.get_toolbar('overshooter'),
                                                   menu=self.get_menu('overshooter'))

        self.affect_to(self.experiment_manager.get_action(ManagerActions.NEW), self.get_menu(MenuToolbarNames.FILE))
        self.extension_manager = ExtensionManager(dashboard=self)
        self.extension_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('extension'))


        self.get_toolbar('state').setEnabled(False)
        self.get_toolbar('overshooter').setEnabled(False)
        self.experiment_manager.enable_actions(True)

    def do_things_after_experiment_set(self, experiment_name: str):

        self.state_manager.update_menu(self.get_menu('state'))
        self.get_menu('state').setEnabled(True)
        self.get_toolbar('state').setEnabled(True)

        self.get_menu('rois').setEnabled(True)
        self.get_toolbar('rois').setEnabled(True)

        self.get_menu('overshooter').setEnabled(True)
        self.get_toolbar('overshooter').setEnabled(True)

        self.get_menu('extensions').setEnabled(True)

        self.state_manager.enable_actions(True)
        self.roi_manager.enable_actions(True)
        self.overshooter.enable_actions(True)
        self.state_manager.execute_entry(self.state_manager.entry_filepath)

        self.extension_manager.enable_actions(True)

        if self._scripted_experiment_load:
            self._scripted_experiment_load = False
            self._leco_commands_signal.emit(ThreadCommand(LECODashboardCommands.APPLIED_EXPERIMENT_DONE, True))
        for device in itertools.chain(self.actuators_modules, self.detector_modules):
            self._connect_leco_request.connect(device.connect_leco)
        self._connect_leco_request.emit(self._connected)

    def get_leco_name(self) -> str:
        return "dashboard"

    def get_leco_host_port(self) -> tuple[str, int]:
        host = config("utils", "network", "leco-server", "host")
        port = config("utils", "network", "leco-server", "port")

        return host, port

    def process_leco_commands(self, status: ThreadCommand) -> None:
        if status.command == LECODashboardCommands.GET_DEVICES:
            devices = {
                'actuators': [ actuator.get_leco_name() for actuator in self.actuators_modules],
                'detectors': [ detector.get_leco_name() for detector in self.detector_modules],
            }
            self._leco_commands_signal.emit(ThreadCommand(LECODashboardCommands.SEND_DEVICES, devices))
        elif status.command == LECODashboardCommands.GET_STATES:
            entries = self.state_manager.entries if self.state_manager.is_action_enabled(ManagerActions.LIST) else []
            self._leco_commands_signal.emit(ThreadCommand(LECODashboardCommands.SEND_STATES, entries))
        elif status.command == LECODashboardCommands.APPLY_STATE:
            configuration = status.attribute
            loaded = False
            if (configuration in self.state_manager.entries and
                self.state_manager.is_action_enabled(ManagerActions.EXECUTE)
            ):

                self.state_manager.entry = configuration
                self.state_manager.execute_entry(self.state_manager.entry_filepath)
                loaded = True

            self._leco_commands_signal.emit(ThreadCommand(LECODashboardCommands.APPLIED_STATE_DONE, loaded))
        elif status.command == LECODashboardCommands.GET_EXPERIMENTS:
            self._leco_commands_signal.emit(ThreadCommand(LECODashboardCommands.SEND_EXPERIMENTS, self.experiment_manager.entries))
        elif status.command == LECODashboardCommands.APPLY_EXPERIMENT:
            experiment = status.attribute
            if experiment not in self.experiment_manager.entries:
                self._leco_commands_signal.emit(ThreadCommand(LECODashboardCommands.APPLIED_EXPERIMENT_DONE, False))
            else:
                self._scripted_experiment_load = True
                self.experiment_manager.entry = experiment
                self.experiment_manager.execute_entry(self.experiment_manager.entry_filepath)

    def add_status(self, txt):
        """
        Add the QListWisgetItem initialized with txt informations to the User Interface
         logger_list and to the save_parameters.logger array.

        =============== =========== ======================
        **Parameters**    **Type**   **Description**
        *txt*             string     the log info to add.
        =============== =========== ======================
        """
        try:
            now = datetime.datetime.now()
            new_item = QtWidgets.QListWidgetItem(
                now.strftime("%Y/%m/%d %H:%M:%S") + ": " + txt,
            )
            self.logger_list.addItem(new_item)

        except Exception as e:
            logger.exception(str(e))

    def _remove_module_list(self, modules: list[DAQ_Move | DAQ_Viewer],
                            module_list:list[DAQ_Move | DAQ_Viewer],
                            compact_manager_attr,
                            remove_dock_widgets=False):
        """Remove a list of control modules, clean up compact manager and docks.

        Parameters
        ----------
        modules: list
            Modules to remove.
        module_list: list
            The dashboard-level list (self.actuators_modules or self.detector_modules)
            from which modules are removed.
        compact_manager_attr: str
            Name of the compact manager attribute on self.
        remove_dock_widgets: bool
            Whether to call dock.removeWidgets() before dock.close() (needed for actuators).
        """
        for module in modules[:]:
            try:
                if module in module_list:
                    module_list.remove(module)
                compact_manager = getattr(self, compact_manager_attr)
                if compact_manager:
                    if compact_manager.remove_module(module):
                        compact_manager.close()
                        setattr(self, compact_manager_attr, None)
                module.quit_fun()
                dock = self.dockarea.docks.get(module.title, None)
                if dock:
                    self.docks_viewer.remove(dock) #dereference the dock
                    if remove_dock_widgets:
                        dock.removeWidgets()
                    dock.close()
            except Exception as e:
                logger.exception(str(e))

    def remove_detectors(self, detector_modules: List[DAQ_Viewer] = None):
        """
        Remove the given list of detectors from the dashboard.
        Parameters
        ----------
        detector_modules: List[DAQ_Viewer]
            List of DAQ_Viewer instances to be removed.
        """
        if detector_modules is None:
            detector_modules = []
        self._remove_module_list(detector_modules, self.detector_modules,
                                 'compact_detector_manager')

    def remove_actuators(self, actuator_modules: List[DAQ_Move] = None):
        """
        Remove the given list of actuators from the dashboard.
        Parameters
        ----------
        actuator_modules: List[DAQ_Move]
            List of DAQ_Move instances to be removed.
        """
        if actuator_modules is None:
            actuator_modules = []
        self._remove_module_list(actuator_modules, self.actuators_modules,
                                 'compact_actuator_manager', remove_dock_widgets=True)

    def get_docks_from_modules(
        self, modules: Sequence[Union["DAQ_Move", "DAQ_Viewer"]],
    ) -> List[Dock]:
        """
        Get a list of Dock instances from the given modules.

        Parameters
        ----------
        modules: Sequence[DAQ_Move/DAQ_Viewer]
            Sequence of DAQ_Move or DAQ_Viewer instances.

        Returns
        -------
        List[Dock]
            List of Dock instances corresponding to the given modules.
        """
        docks = []
        for module in modules:
            if hasattr(module, "dock"):
                docks.append(module.dock)
        return docks

    def remove_modules(
        self, modules: List[Union["DAQ_Move", "DAQ_Viewer", "str"]] = None,
    ):
        """
        Remove the given list of actuators/detectors from the dashboard.

        Parameters
        ----------
        modules: List[DAQ_Move/DAQ_Viewer]
            List of DAQ_Move/DAQ_Viewer instances to be removed.
        """
        if modules is None:
            modules = []
        try:
            actuators_modules = []
            detector_modules = []
            for module in modules:
                if isinstance(module, DAQ_Move):  # Test if module is an instance of DAQ_Move
                    actuators_modules.append(module)
                elif isinstance(module, DAQ_Viewer):  # Test if module is an instance of DAQ_Viewer
                    detector_modules.append(module)
                if isinstance(module, str):  # Test if module is a string (name of the module)
                    actuators_modules.extend(
                        self.modules_manager.get_mods_from_names([module], "act"))  # For actuators

                    detector_modules.extend(
                        self.modules_manager.get_mods_from_names([module], "det"),  # For detectors
                    )
            if (hasattr(self, "actuators_modules")) & (
                self.actuators_modules is not None
            ):  # Remove actuators
                self.remove_actuators(actuators_modules)
            if (hasattr(self, "detector_modules")) & (
                self.detector_modules is not None
            ):  # Remove detectors
                self.remove_detectors(detector_modules)
        except Exception as e:
            logger.exception(str(e))

    def load_extension(self, ext_enum: ExtensionEnum,
                       win: QtWidgets.QMainWindow = None,
                       ) -> 'CustomExt':
        shared_ui, ext_module = create_extension(
            self, extensions[ext_enum].klass,
            window=win,
        )
        self.extensions[ext_enum] = ext_module
        ext_module.shared_ui = shared_ui
        ext_module.status_signal.connect(self.add_status)
        shared_ui.show()
        ext_module.set_action_checked('show_dashboard', True)

        return ext_module

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        """
        Create the menubar object looking like :
        """
        self.add_menu(MenuToolbarNames.FILE, 'File', menubar)

        self.add_menu(MenuToolbarNames.VIEW, 'View', menubar)

        self.add_menu('docked', 'Docked', MenuToolbarNames.VIEW)

        self.add_menu(MenuToolbarNames.TOOLS, 'Tools', menubar)
        self.add_menu('experiment', 'Experiment', MenuToolbarNames.TOOLS, icon_name=ExperimentManager.icon_name)
        self.add_menu('state', 'State', MenuToolbarNames.TOOLS, icon_name=StateManager.icon_name)
        self.get_menu('state').setEnabled(False)
        self.add_menu('rois', 'Rois', MenuToolbarNames.TOOLS, icon_name=ROIManager.icon_name)
        self.get_menu('rois').setEnabled(False)
        self.add_menu('overshooter', 'Overshooter', MenuToolbarNames.TOOLS, icon_name=Overshooter.icon_name)
        self.get_menu('overshooter').setEnabled(False)

        # self.remote_menu = self.add_menu('remote', "Remote/Shortcuts Control")
        # self.update_remote_menu()

        # extensions menu
        self.extensions_menu = self.add_menu('extensions', "Extensions", MenuToolbarNames.TOOLS)
        self.get_menu('extensions').setEnabled(False)

        self.add_toolbar('experiment', 'Experiment', parent=self.mainwindow,
                         add_break=False)
        self.add_toolbar('state', 'State', parent=self.mainwindow,
                         add_break=False)
        self.add_toolbar('rois', 'rois', parent=self.mainwindow,
                         add_break=False)
        self.add_toolbar('overshooter', 'Overshoot', parent=self.mainwindow,
                         add_break=False)
        self.add_toolbar('extension', 'Extension', parent=self.mainwindow, add_break=False)
        self.toolbar.addSeparator()

    def setup_actions(self):
        self.add_action("load_layout", "Load Layout", "",
                        "Load the Saved Docks layout corresponding to the current experiment",
                        auto_toolbar=False, menu='docked')
        self.add_action("save_layout", "Save Layout", "",
                        "Save the Saved Docks layout corresponding to the current experiment",
                        auto_toolbar=False, menu='docked')
        self.add_action("show_log_widget", "Show/hide log window", "", checkable=True, auto_toolbar=False,
                        menu=MenuToolbarNames.VIEW)

        for ext_name in ExtensionEnum.names():
            self.add_action(ExtensionEnum[ext_name], ExtensionEnum[ext_name].value,
                            auto_toolbar=False, menu='extensions',
                            icon_name=extensions[ExtensionEnum[ext_name]].klass.icon_name)

        self.add_action("state", "State", auto_toolbar=False)

    def connect_things(self):
        self.status_signal[str].connect(self.add_status)
        self.connect_action("load_layout", self.load_layout_state)
        self.connect_action("save_layout", self.save_layout_state)
        self.connect_action("show_log_widget", self.show_log_widget)

        # self.connect_action('show_remote', self.show_remote)
        # self.connect_action("new_remote", self.create_remote)
        # self.connect_action("modify_remote", self.modify_remote)
        
        # for file in get_set_remote_path().iterdir():
        #     if file.suffix == ".xml":
        #         self.connect_action(
        #             self.get_action_from_file(file, ManagerEnums.remote),
        #             self.create_menu_slot_remote(get_set_remote_path().joinpath(file)),
        #         )
        for ext_name in ExtensionEnum.names():
            self.connect_action(ExtensionEnum[ext_name],
                                self.create_extension_slot(ExtensionEnum[ext_name]))

    # def update_remote_menu(self):
    #     self.remote_menu.addAction(self.get_action("show_remote"))
    #     self.connect_action('show_remote', self.show_remote)
    #     self.remote_menu.addSeparator()
    #
    #     self.remote_menu.addAction(self.get_action('new_remote'))
    #     self.connect_action('new_remote', self.create_remote)
    #     self.remote_menu.addAction(self.get_action('modify_remote'))
    #     self.connect_action('modify_remote', self.modify_remote)
    #     self.remote_menu.addSeparator()
    #     load_remote_menu = self.remote_menu.addMenu("Load remote config.")
    #
    #     for file in get_set_remote_path().iterdir():
    #         if file.suffix == ".xml":
    #             load_remote_menu.addAction(
    #                 self.get_action(self.get_action_from_file(file, ManagerEnums.remote))
    #             )
    #
    # def create_remote(self):
    #     try:
    #         if self.preset_file is not None:
    #             self.remote_manager.set_new_remote(self.preset_file.stem)
    #             self.add_action(
    #                 self.get_action_from_file(self.preset_file, ManagerEnums.remote),
    #                 self.preset_file.stem,
    #                 "",
    #             )
    #             self.setup_menu(self.menubar)
    #             self.connect_action(
    #                 self.get_action_from_file(self.preset_file, ManagerEnums.remote),
    #                 self.create_menu_slot_remote(get_set_remote_path().joinpath(self.preset_file.name)),
    #             )
    #
    #     except Exception as e:
    #         logger.exception(str(e))
    #
    # def modify_remote(self):
    #     try:
    #         path = select_file(
    #             start_path=get_set_remote_path(),
    #             save=False,
    #             ext="xml",
    #         )
    #         if path != "":
    #             self.remote_manager.set_file_remote(path)
    #
    #         else:  # cancel
    #             pass
    #     except Exception as e:
    #         logger.exception(str(e))
    #
    # def show_remote(self, show=True):
    #     self.remote_widget.setVisible(show)
    #     self.remote_widget.closeEvent = lambda event: self.set_action_checked('show_remote', False)

    def show_log_widget(self, show=True):
        self.logger_widget.setVisible(show)
        self.logger_widget.closeEvent = lambda event: self.set_action_checked('show_log_widget', False)

    # def create_menu_slot_roi(self, filename):
    #     return lambda: self.set_roi_configuration(filename)
    #
    # def create_menu_slot_remote(self, filename):
    #     return lambda: self.set_remote_configuration(filename)

    def create_extension_slot(self, extenum: ExtensionEnum):
        return lambda: self.load_extension(extenum)

    def quit_fun(self):
        """
        Quit the current instance of DashBoard and close on cascade move and detector modules.

        See Also
        --------
        quit_fun
        """
        try:
            self.connect_leco(connect=False)
            self.remote_timer.stop()

            for ext in self.extensions:
                if hasattr(self.extensions[ext], "quit_fun"):
                    self.extensions[ext].quit_fun()
            for mov in self.actuators_modules:
                try:
                    mov.init_signal.disconnect(self.update_init_tree)
                except TypeError:
                    pass
            for det in self.detector_modules:
                try:
                    det.init_signal.disconnect(self.update_init_tree)
                except TypeError:
                    pass

            # Removing control modules
            self.remove_actuators(self.actuators_modules)
            self.remove_detectors(self.detector_modules)

            self.experiment_manager.quit_fun()
            self.state_manager.quit_fun()
            self.overshooter.quit_fun()

            # Removing dock areas (I don't know what this is for)
            areas = self.dockarea.tempAreas[:]
            for area in areas:
                area.win.close()

            if hasattr(self, "mainwindow"):
                self.mainwindow.close()

            if self.pid_window is not None:
                self.pid_window.close()


        except Exception as e:
            logger.exception(str(e))
        finally:
            QtWidgets.QApplication.processEvents()

    def restart_fun(self, ask=False):
        ret = False
        mssg = QMessageBox()
        if ask:
            mssg.setText(
                "You have to restart the application to take the"
                " modifications into account!",
            )
            mssg.setInformativeText("Do you want to restart?")
            mssg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            ret = mssg.exec()

        if ret == QMessageBox.StandardButton.Ok or not ask:
            self.quit_fun()
            subprocess.call([sys.executable, __file__])

    def load_layout_state(self, file=None):
        """
        Load and restore a layout state from the select_file obtained pathname file.

        See Also
        --------
        utils.select_file
        """
        try:
            file = layout_mod.load_layout_state(self.dockarea, file)
            self.settings.child("loaded_files", "layout_file").setValue(file)
        except Exception as e:
            logger.exception(str(e))

    def save_layout_state(self, file=None):
        """
        Save the current layout state in the select_file obtained pathname file.
        Once done dump the pickle.

        See Also
        --------
        utils.select_file
        """
        try:
            layout_mod.save_layout_state(self.dockarea, file)
        except Exception as e:
            logger.exception(str(e))

    def save_layout_state_auto(self):
        if self.experiment_file is not None:
            path = get_set_layout_path().joinpath(self.experiment_file.stem + ".dock")
            self.save_layout_state(path)

    def add_move(
            self,
            plug_name: str = None,
            plug_type: str = None,
            ui_identifier: str = None,
            **kwargs,
    ) -> DAQ_Move:        

        actuator = self.create_actuator(plug_name, plug_type, ui_identifier)

        self.set_actuator_type(actuator, plug_type)

        self.add_actuator(actuator)
        return  actuator

    def create_actuator(self, name: str, class_name: str, ui_identifier: str) -> DAQ_Move:
        actuator_class = find_actuator_class_from_name(class_name)
        forced_ui = actuator_class.ui_type
        ui_identifier = forced_ui if forced_ui != UiType.NONE else ui_identifier

        if ui_identifier is not None:
            pass
        else:
            ui_identifier = config("pymodaq", "actuator", "ui")
        mov_mod_tmp = DAQ_Move(QtWidgets.QWidget(),
                               name,
                               ui_identifier=ui_identifier,
                               settings_dock=self.settings_dock,
                               controls_dock=self.controls_dock,
                               )
        mov_mod_tmp.bounds_signal[bool].connect(self.do_stuff_from_out_bounds)
        return mov_mod_tmp

    def set_actuator_type(self, actuator: DAQ_Move, class_name: str):
        actuator.actuator = class_name  # will fire instrument_changed when done

    def add_actuator(self, actuator: DAQ_Move):
        # Create compact manager if needed
        if self.compact_actuator_manager is None:
            self.compact_actuator_manager = ActuatorCompactDock(
                "Actuators",
                self.dockarea,
                orientation=Qt.Orientation.Vertical,
            )
            if self.compact_detector_manager is not None:
                self.compact_actuator_manager.show('bottom', self.compact_detector_manager.dock)
            else:
                self.compact_actuator_manager.show("top")

        QtWidgets.QApplication.processEvents()

        self.compact_actuator_manager.add_module(actuator)
        return actuator

    def add_move_from_extension(
        self, *args, modules: list[PluginInfo] = None,
        **kwargs,
    ):
        """Specific method to add DAQ_Moves within the Dashboard. This Particular actuator
        should be defined in the plugin of the extension and is used to mimic an actuator while
        move_abs is actually triggering an action on the extension which loaded it

        For an exemple, see the PyMoDAQ builtin PID extension

        Parameters
        ----------
        modules: list[PluginInfo]


        Deprecated:
        name: str
            The name to print on the UI title
        instrument_name: str
            The name of the instrument class, for instance PID for the daq_move_PID
            module and the DAQ_Move_PID instrument class
        instrument_controller: ControllerAndThread
            whatever object is used to communicate between the instrument module and the extension
            which created it
        ui_identifier: str
            One of the possible registered UI
        kwargs: named arguments to be passed to add_move
        """
        if modules is None:
            modules = [
                PluginInfo(
                    id=0,
                    name=args[0],
                    class_name=args[1],
                    type=ModuleType.Actuator,
                    settings=None,
                    is_master=False,
                    do_init=True,
                    ui=None,
                    daq_type=None,
                    controller=args[2]
                ),
            ]
        self.module_loader = ModuleLoader(self, [[mod] for mod in modules])
        self.module_loader.all_instruments_added.connect(self.modules_manager.add_modules)
        self.module_loader.start()


    @property
    def docks_viewer(self):
        return self._docks_viewer

    @property
    def n_docks_viewer(self) -> int:
        return len(self._docks_viewer)

    def add_det(self,
                plug_name,
                plug_type: DAQTypesEnum | str = DAQTypesEnum.DAQ0D,
                plug_subtype: str = None) -> DAQ_Viewer:

        det_mod_tmp = self.create_detector(plug_name, plug_type)

        self.set_detector_type(det_mod_tmp, plug_type, plug_subtype)

        self.add_detector(det_mod_tmp)
        return  det_mod_tmp

    def add_detector(self, detector: DAQ_Viewer):

        # Create compact manager if needed
        if self.compact_detector_manager is None:
            self.compact_detector_manager = DetectorCompactDock(
                "Detectors",
                self.dockarea,
                orientation=Qt.Orientation.Vertical,
            )
            self.compact_detector_manager.show("top")

        # Create individual detector dock
        self.docks_viewer.append(Dock(detector.title, size=(350, 350)))
        if self.n_docks_viewer == 1:
            self.dockarea.addDock(self.docks_viewer[-1], "bottom")
            self.dockarea.moveDock(self.settings_dock, 'right', None)
            self.settings_dock.setVisible(False)
            self.dockarea.moveDock(self.rois_dock, 'right', None)
            self.rois_dock.setVisible(False)
            self.dockarea.moveDock(self.controls_dock, 'right', None)
            self.controls_dock.setVisible(False)
        else:
            self.dockarea.addDock(self._docks_viewer[-1], "right", self._docks_viewer[-2])

        self.compact_detector_manager.add_module(detector)
        self._docks_viewer[-1].addWidget(detector.parent)
        return detector

    def create_detector(self, name: str, daq_type: DAQTypesEnum) -> DAQ_Viewer:
        widget = QtWidgets.QWidget()

        det_mod_tmp = DAQ_Viewer(
            widget,
            title=name,
            daq_type=daq_type.name,
            settings_dock=self.settings_dock,
            rois_dock=self.rois_dock,
        )
        return det_mod_tmp

    def set_detector_type(self, detector: DAQ_Viewer, daq_type: DAQTypesEnum, class_name: str):
        detector.detector = SelectedModule(daq_type, class_name)  # will fire instrument_changed when done
        
    def move_utils_docks(self, position='right'):
        self.dockarea.moveDock(self.settings_dock, position, None)
        self.settings_dock.setVisible(False)
        self.dockarea.moveDock(self.rois_dock, position, None)
        self.rois_dock.setVisible(False)
        self.dockarea.moveDock(self.controls_dock, position, None)
        self.controls_dock.setVisible(False)

    def override_det_from_extension(self, overriden_grabbers: Sequence[str] = None):
        """(Experimental) If an extension adding detectors within the Dashboard need to,
         it could call this method.

        Then if some other extension trigger a grab from it, the request of a grab won't be done twice

        Parameters
        ----------
        overriden_grabbers: Sequence[str]
            sequence of detector names whose corresponding modules should set their
            attribute override_grab_from_extension to True.
        """
        if overriden_grabbers is not None:
            for mod_name in overriden_grabbers:
                mod = self.modules_manager.get_mod_from_name(mod_name, "det")
                if mod is not None:
                    mod.override_grab_from_extension = True

    def add_det_from_extension(
            self, *args,
            modules: list[PluginInfo] = None,
            callback: Callable = None,
            **kwargs,
    ):
        """Specific method to add a DAQ_Viewer within the Dashboard. This Particular detector
        should be defined in the plugin of the extension and is used to mimic a grab while data
        are actually coming from the extension which loaded it

        For an exemple, see the pymodaq_plugins_datamixer plugin and its DataMixer extension
        or the DAQ_PID extension

        Parameters
        ----------
        modules: list[PluginInfo]
        callback: a callable method (slot like) that will receive the *list of added modules* when done

        Deprecated:
        -----------
        name: str
            The name to print on the UI title
        daq_type: str
            either DAQ0D, DAQ1D, DAQ2D or DAQND depending the type of the instrument
        instrument_name: str
            The name of the instrument class, for instance DataMixer for the daq_0Dviewer_DataMixer
            module and the DAQ_0DViewer_DataMixer instrument class
        instrument_controller: ControllerAndThread
            whatever object is used to communicate between the instrument module and the extension
            which created it
        """
        if modules is None:
            modules = [
                PluginInfo(
                    id=0,
                    name=args[0],
                    class_name=args[2],
                    type=ModuleType.Detector,
                    settings=None,
                    is_master=False,
                    do_init=True,
                    ui=None,
                    daq_type=DAQTypesEnum[args[1]] ,
                    controller=args[3]
                ),
            ]
        self.module_loader = ModuleLoader(self, [[mod] for mod in modules])
        self.module_loader.all_instruments_added.connect(self.modules_manager.add_modules)
        if callback is not None:
            self.module_loader.all_instruments_added.connect(callback)
        self.module_loader.start()


    # def set_remote_configuration(self, filename):
    #     if not isinstance(filename, Path):
    #         filename = Path(filename)
    #     ext = filename.suffix
    #     if ext == ".xml":
    #         self.remote_file = filename
    #         self.remote_manager.remote_changed.connect(self.activate_remote)
    #         self.remote_manager.set_file_remote(filename, show=False)
    #         self.settings.child("loaded_files", "remote_file").setValue(filename)
    #         self.remote_manager.set_remote_configuration()
    #         self.remote_widget.layout().addWidget(self.remote_manager.remote_settings_tree)
    #         self.get_action('show_remote').trigger()

    # def activate_remote(self, remote_action, activate_all=False):
    #     """
    #     remote_action = dict(action_type='shortcut' or 'joystick',
    #                         action_name='blabla',
    #                         action_dict= either:
    #                             dict(shortcut=action.child(('shortcut')).value(), activated=True,
    #                              name=f'action{ind:02d}', action=action.child(('action')).value(),
    #                               module_name=module, module_type=module_type)
    #
    #                             or:
    #                              dict(joystickID=action.child(('joystickID')).value(),
    #                                  actionner_type=action.child(('actionner_type')).value(),
    #                                  actionnerID=action.child(('actionnerID')).value(),
    #                                  activated=True, name=f'action{ind:02d}',
    #                                  module_name=module, module_type=module_type)
    #
    #     """
    #     if remote_action["action_type"] == "shortcut":
    #         if remote_action["action_name"] not in self.shortcuts:
    #             self.shortcuts[remote_action["action_name"]] = QtWidgets.QShortcut(
    #                 QtGui.QKeySequence(remote_action["action_dict"]["shortcut"]),
    #                 self.dockarea,
    #             )
    #         self.activate_shortcut(
    #             self.shortcuts[remote_action["action_name"]],
    #             remote_action["action_dict"],
    #             activate=remote_action["action_dict"]["activated"],
    #         )
    #
    #     elif remote_action["action_type"] == "joystick":
    #         if not self.ispygame_init:
    #             self.init_pygame()
    #
    #         if remote_action["action_name"] not in self.joysticks:
    #             self.joysticks[remote_action["action_name"]] = remote_action[
    #                 "action_dict"
    #             ]

    def init_pygame(self):
        try:
            import pygame

            self.pygame = pygame
            pygame.init()
            pygame.joystick.init()
            joystick_count = pygame.joystick.get_count()
            self.joysticks_obj = []
            for ind in range(joystick_count):
                self.joysticks_obj.append(dict(obj=pygame.joystick.Joystick(ind)))
                self.joysticks_obj[-1]["obj"].init()
                self.joysticks_obj[-1]["id"] = self.joysticks_obj[-1]["obj"].get_id()

            self.remote_timer.timeout.connect(self.pygame_loop)
            self.ispygame_init = True
            self.remote_timer.start(10)

        except ImportError as e:
            logger.warning("No pygame module installed. Needed for joystick control")

    def pygame_loop(self):
        """
        check is event correspond to any
         dict(joystickID=action.child(('joystickID')).value(),
             actionner_type=action.child(('actionner_type')).value(),
             actionnerID=action.child(('actionnerID')).value(),
             activated=True, name=f'action{ind:02d}',
             module_name=module, module_type=module_type)
        contained in self.joysticks
        """

        for action_dict in self.joysticks.values():
            if (
                action_dict["activated"]
                and action_dict["actionner_type"].lower() == "axis"
            ):
                if action_dict["module_type"] == "act":
                    joy = utils.find_dict_in_list_from_key_val(
                        self.joysticks_obj, "id", action_dict["joystickID"],
                    )
                    val = joy["obj"].get_axis(action_dict["actionnerID"])
                    if abs(val) > 1e-4:
                        module = self.modules_manager.get_mod_from_name(
                            action_dict["module_name"], mod=action_dict["module_type"],
                        )
                        action = getattr(module, action_dict["action"])
                        if module.move_done_bool:
                            action(
                                val
                                * 1
                                * module.settings.child(
                                    module._hw_settings_name, "epsilon"
                                ).value()
                            )

        # # For other actions use the event loop
        for event in self.pygame.event.get():  # User did something.
            selection = dict([])
            if "joy" in event.dict:
                selection.update(dict(joy=event.joy))
            if event.type == self.pygame.JOYBUTTONDOWN:
                selection.update(dict(button=event.button))
            elif event.type == self.pygame.JOYAXISMOTION:
                selection.update(dict(axis=event.axis, value=event.value))
            elif event.type == self.pygame.JOYHATMOTION:
                selection.update(dict(hat=event.hat, value=event.value))
            if len(selection) > 1:
                for action_dict in self.joysticks.values():
                    if action_dict["activated"]:
                        module = self.modules_manager.get_mod_from_name(
                            action_dict["module_name"], mod=action_dict["module_type"],
                        )
                        if action_dict["module_type"] == "det":
                            action = getattr(module, action_dict["action"])
                        else:
                            action = getattr(module, action_dict["action"])

                        if action_dict["joystickID"] == selection["joy"]:
                            if (
                                action_dict["actionner_type"].lower() == "button"
                                and "button" in selection
                            ):
                                if action_dict["actionnerID"] == selection["button"]:
                                    action()
                            elif (
                                action_dict["actionner_type"].lower() == "hat"
                                and "hat" in selection
                            ):
                                if action_dict["actionnerID"] == selection["hat"]:
                                    action(selection["value"])

        QtWidgets.QApplication.processEvents()

    def activate_shortcut(self, shortcut, action=None, activate=True):
        """
        action = dict(shortcut=action.child(('shortcut')).value(), activated=True,
         name=f'action{ind:02d}',
                             action=action.child(('action')).value(), module_name=module)
        Parameters
        ----------
        shortcut
        action
        activate

        Returns
        -------

        """
        if activate:
            shortcut.activated.connect(self.create_activated_shortcut(action))
        else:
            try:
                shortcut.activated.disconnect()
            except Exception:
                pass

    def create_activated_shortcut(self, action):
        module = self.modules_manager.get_mod_from_name(
            action["module_name"], mod=action["module_type"],
        )
        if action["module_type"] == "det":
            return lambda: getattr(module, action["action"])()
        else:
            return lambda: getattr(module, action["action"])()

    @property
    def move_modules(self):
        """
        for back compatibility
        """
        return self.actuators_modules

    @property
    def experiment_file(self) -> Path:
        return self.experiment_manager.entry_filepath

    @property
    def experiment_name(self) -> str:
        return self.experiment_manager.entry

    def _update_init_tree_for(self, modules, settings_key):
        for mod in modules:
            name = "".join(mod.title.split())  # remove empty spaces
            if mod.title not in [
                child.title()
                for child in putils.iter_children_params(
                    self.settings.child(settings_key), []
                )
            ]:
                self.settings.child(settings_key).addChild(
                    {"title": mod.title, "name": name, "type": "led", "value": False}
                )
                QtWidgets.QApplication.processEvents()
            self.settings.child(settings_key, name).setValue(mod.initialized_state)

    def update_init_tree(self):
        self._update_init_tree_for(self.actuators_modules, "actuators")
        self._update_init_tree_for(self.detector_modules, "detectors")

    def do_stuff_from_out_bounds(self, out_of_bounds: bool):
        if out_of_bounds:
            logger.warning("Some actuators reached their bounds")
            if self.extensions[ExtensionEnum.SCANNER] is not None:
                logger.warning("Stopping the DAQScan for out of bounds")
                self.extensions[ExtensionEnum.SCANNER].stop_scan()

    def stop_moves(self, *args, **kwargs):
        """
        Foreach module of the move module object list, stop motion.

        See Also
        --------
        stop_scan,  DAQ_Move_main.daq_move.stop_motion
        """
        if self.extensions[ExtensionEnum.SCAN] is not None:
            self.extensions[ExtensionEnum.SCAN].stop_scan()

        for mod in self.actuators_modules:
            mod.stop_motion()

    def setup_docks_and_widgets(self):
        # %% create logger dock
        self.logger_widget = QtWidgets.QWidget(windowTitle='Logger')
        self.logger_widget.setLayout(QtWidgets.QVBoxLayout())
        self.logger_widget.setVisible(False)

        self.logger_list = QtWidgets.QListWidget()
        self.logger_list.setMinimumWidth(300)

        splitter = QtWidgets.QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.settings_tree)
        splitter.addWidget(self.logger_list)
        self.logger_widget.layout().addWidget(splitter)

        self.remote_widget = QtWidgets.QWidget(windowTitle='Remote Manager')
        self.remote_widget.setLayout(QtWidgets.QVBoxLayout())
        self.remote_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.remote_widget.setVisible(False)

        self.settings_dock = Dock('Settings', )
        self.settings_dock.label.setDim(True)
        self.dockarea.addDock(self.settings_dock, position='right')
        self.settings_dock.setVisible(False)

        self.rois_dock = Dock('ROIs', )
        self.rois_dock.label.setDim(True)
        self.dockarea.addDock(self.rois_dock, position='right')
        self.rois_dock.setVisible(False)

        self.controls_dock = Dock('Controls', )
        self.controls_dock.label.setDim(True)
        self.dockarea.addDock(self.controls_dock, position='right')
        self.controls_dock.setVisible(False)

    def value_changed(self, param: Parameter):
        if param.name() == "log_level":
            logger.setLevel(param.value())

    def show_file_attributes(self, type_info="dataset"):
        """
        Switch the type_info value.

        In case of :
            * *scan* : Set parameters showing top false
            * *dataset* : Set parameters showing top false
            * *managers* : Set parameters showing top false.
            Add the save/cancel buttons to the accept/reject dialog
            (to save managers parameters in a xml file).

        Finally, in case of accepted managers type info,
        save the managers parameters in a xml file.

        =============== =========== ====================================
        **Parameters**    **Type**    **Description**
        *type_info*       string      The file type information between
                                        * scan
                                        * dataset
                                        * managers
        =============== =========== ====================================
        """
        dialog = QtWidgets.QDialog()
        vlayout = QtWidgets.QVBoxLayout()
        tree = ParameterTree()
        tree.setMinimumWidth(400)
        tree.setMinimumHeight(500)
        if type_info == "scan":
            tree.setParameters(self.scan_attributes, showTop=False)
        elif type_info == "dataset":
            tree.setParameters(self.dataset_attributes, showTop=False)

        vlayout.addWidget(tree)
        dialog.setLayout(vlayout)
        buttonBox = QDialogButtonBox(parent=dialog)
        buttonBox.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        buttonBox.addButton("Apply", QDialogButtonBox.ButtonRole.AcceptRole)
        buttonBox.rejected.connect(dialog.reject)
        buttonBox.accepted.connect(dialog.accept)

        vlayout.addWidget(buttonBox)
        dialog.setWindowTitle("Fill in information about this {}".format(type_info))
        res = dialog.exec()
        return res

    def update_status(self, txt: str, wait_time: int = None, log_type=None):
        """Show txt in the status bar and emit the status signal."""
        super().update_status(txt, wait_time)
        self.status_signal.emit(txt)
        logger.info(txt)


def load_dashboard_with_arguments(show_dashboard=True, load_extension=True):

    extensions_names = ExtensionEnum.values()
    # Command-line argument parsing
    parser = argparse.ArgumentParser(prog="dashboard",
                                     description="PyMoDAQ dashboard. "
                                                 "Command-line options only affect GUI initial state.",
                                     )

    parser.add_argument("-x", "--experiment", metavar="EXPERIMENT_NAME",
                        help="experiment name to load at startup")
    parser.add_argument("-c", "--config", metavar="CONFIG_NAME",
                        help="config name to execute (ignored if no experiment provided), deprecated, use -s for state")
    parser.add_argument("-s", "--state", metavar="STATE_NAME",
                        help="State name to execute (ignored if no experiment provided)")
    if load_extension:
        parser.add_argument("-e", "--extension", metavar="EXTENSION_NAME",
                            help="extension name to execute (ignored if no experiment provided), valid "
                                 'values are within: "' + '\" \"'.join(extensions_names) +'"')

    args, unknown_args = parser.parse_known_args()

    if load_extension:
        extension_name = args.extension.upper() if args.extension is not None else args.extension
    else:
        extension_name = None

    # If experiment name is supplied, load dashboard with this experiment
    if args.experiment:
        dashboard, extension, win = load_dashboard_with_experiment(
            experiment_name=args.experiment,
            extension_name=extension_name,
            state_name=args.state if args.state is not None else args.config,
            show_dashboard=show_dashboard
        )

    # If no command-line arguments are supplied, start empty
    else:
        win, dashboard = create_load_dashboard(show_dashboard=show_dashboard)
        extension = None
    return win, dashboard, extension


def create_load_dashboard(show_dashboard=True) -> tuple[SharedUI, DashBoard]:

    win, area = make_window(title='PyMoDAQ Dashboard')
    win.resize(1000, 500)

    shared_ui = SharedUI(win, show=show_dashboard)
    dashboard = DashBoard(area)
    dashboard.shared_ui = shared_ui
    shared_ui.affect_application(dashboard)
    return shared_ui, dashboard


def load_dashboard_with_experiment(experiment_name: str,
                                   extension_name: str = None,
                                   configuration_name: str = None,
                                   state_name: str = None,
                                   show_dashboard=True)  -> tuple[DashBoard, 'CustomExt', SharedUI]:

    """ Load the Dashboard using a given experiment then load an extension

    Parameters
    ----------
    configuration_name: str (deprecated, use state)
    state_name: str
    experiment_name: str
        The filename (without extension) defining the experiment to be loaded in the Dashboard
    extension_name: str
        The name of the extension. Either the builtins ones:
        * 'DAQScan'
        * 'DAQLogger'
        * 'DAQ_PID'
        * 'Bayesian'

        or the ones defined within a plugin
    show_dashboard: bool
        show dashboard at startup  or not (if no extension provided, it is shown)
    Returns
    -------

    """
    from pymodaq.utils.config import get_set_experiment_path
    shared_ui, dashboard = create_load_dashboard(show_dashboard=show_dashboard if extension_name is not None else True)

    experiment_path = get_set_experiment_path().joinpath(f'{experiment_name}.xml')
    experiment_name = experiment_path.stem
    extension = None

    if experiment_name in dashboard.experiment_manager.entries:
        dashboard.experiment_manager.entry = experiment_name
        if state_name is None:
            # backcompatibility
            state_name = configuration_name
        if state_name is not None:
            dashboard.state_manager.entry = state_name
        dashboard.experiment_manager.execute_entry(experiment_path)

        if extension_name in ExtensionEnum.names():
            extension = dashboard.load_extension(ExtensionEnum[extension_name])
        else:
            extension = None

    else:
        msgBox = QMessageBox()
        msgBox.setText(f"The default file specified in the configuration file does not exists!\n"
                       f"{experiment_name}\n"
                       f"Impossible to load the {extension_name} extension")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Ok)
        ret = msgBox.exec()
    return dashboard, extension, shared_ui



def main():
    from pymodaq_gui.qt_utils import mkQApp
    # Create application and main window
    app = mkQApp('Dashboard')

    load_dashboard_with_arguments(show_dashboard=True)

    # SharedUI shows the dashboard on creation; preserve visibility changes
    # made while loading.
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

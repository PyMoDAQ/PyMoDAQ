#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import datetime
import subprocess
import logging
from pathlib import Path
from importlib import import_module

from typing import Tuple, Union, List, Any, TYPE_CHECKING, Sequence, Iterable
import argparse

from qtpy import QtGui, QtWidgets, QtCore
from qtpy.QtCore import Qt, QThread, Signal, QSize
from qtpy.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QDialogButtonBox,
    QMessageBox,
)
import numpy as np

from pymodaq.control_modules.daq_viewer_ui.viewer_selector import SelectedModule
from pymodaq.utils.gui_utils.loader_utils import create_extension

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import utils
from pymodaq_utils.utils import get_version, find_dict_in_list_from_key_val
from pymodaq_utils.config import GlobalConfig as Config
from pymodaq_utils.enums import BaseEnum, StrEnum

from pymodaq_gui.parameter import ParameterTree, Parameter
from pymodaq_gui.utils import DockArea, Dock, select_file
import pymodaq_gui.utils.layout as layout_mod
from pymodaq_gui.messenger import messagebox, dialog
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.managers.roi_manager import ROISaver
from pymodaq_gui.utils.custom_app import CustomApp

from pymodaq.utils.managers.modules.modules_manager import ModulesManager, ModuleType
from pymodaq.utils.managers.preset.preset_manager import PresetManager
from pymodaq_gui.managers.manager_base import Menu
from pymodaq.utils.managers.overshoot.overshooter import Overshooter
from pymodaq.utils.managers.remote_manager import RemoteManager
from pymodaq.utils.compact_dock_manager import ActuatorCompactDock, DetectorCompactDock
from pymodaq.utils.exceptions import DetectorError, ActuatorError, MasterSlaveError
from pymodaq.utils.daq_utils import get_instrument_plugins

from pymodaq.utils.config import (get_set_preset_path, get_set_overshoot_path,
                                  get_set_roi_path, get_set_remote_path, get_set_layout_path)
from pymodaq.utils.gui_utils.widgets.window import make_window

from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.control_modules.daq_move_ui.factory import ActuatorUIFactory

from pymodaq.extensions.utils import get_extensions
from pymodaq.extensions import  ExtensionEnum
from pymodaq.utils.shared_ui import SharedUI


from pymodaq.utils.config import Config as ControlModulesConfig
from pymodaq.utils.managers.configurator.configurator import Configurator

if TYPE_CHECKING:
    from pymodaq.extensions.custom_ext import CustomExt

logger = set_logger(get_module_name(__file__))

config = Config()


get_instrument_plugins()
extensions = get_extensions()


class ManagerEnums(BaseEnum):
    preset = 0
    remote = 1
    overshoot = 2
    roi = 3
    configuration = 4
    
    
class PresetActions(StrEnum):
    Open = "open_preset"
    New = "new_preset"
    Modify = "modify_preset"
    Label = "preset_label"
    List = "preset_list"
    Load = "load_preset"


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


class DashBoard(CustomApp):
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
         "limits": config("utils", "general", "debug_level"),},
        {"title": "Loaded presets", "name": "loaded_files", "type": "group",
         "children": [
             {"title": "Layout file", "name": "layout_file", "type": "str", "value": "", "readonly": True,},
             {"title": "ROI file", "name": "roi_file", "type": "str", "value": "", "readonly": True,},
             {"title": "Remote file", "name": "remote_file", "type": "str", "value": "", "readonly": True,},
         ],
         },
        {"title": "Actuators Init.", "name": "actuators", "type": "group","children": [],},
        {"title": "Detectors Init.", "name": "detectors", "type": "group", "children": [],},
    ]

    def __init__(self, parent: Union[DockArea]):
        """

        Parameters
        ----------
        """

        super().__init__(parent)

        logger.info("Initializing Dashboard")
        self.extra_params = []

        self.wait_time = 1000
        self.log_module = None
        self.pid_module = None
        self.pid_window = None
        self.retriever_module = None
        self.database_module = None
        self.extensions: dict[str, CustomExt] = dict([])
        self.extension_windows = []
        self.preset_manager: PresetManager = None  # instanciation in do_things_after_ui_setup
        self.configurator: Configurator = None # instanciation in do_things_after_ui_setup
        self.overshooter: Overshooter = None # instanciation in do_things_after_ui_setup

        self.dockarea.dock_signal.connect(self.save_layout_state_auto)

        self.title = ""


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
        self.preset_manager = PresetManager(dashboard=self)
        self.preset_manager.update_entry()
        self.preset_manager.entry = 'default'
        self.preset_manager.applied_entry.connect(self.do_things_after_preset_set)
        self.configurator = Configurator(dashboard=self)
        self.preset_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('preset'),
                                                      menu=self.get_menu('preset'))
        self.preset_manager.update_menu(self.get_menu('preset'))
        self.configurator.get_external_toolbar_menu(toolbar=self.get_toolbar('configurator'),
                                                    menu=self.get_menu('configurator'))
        self.configurator.update_menu(self.get_menu('configurator'))
        self.overshooter = Overshooter(dashboard=self)
        self.overshooter.get_external_toolbar_menu(toolbar=self.get_toolbar('overshooter'),
                                                   menu=self.get_menu('overshooter'))

        self.get_toolbar('configurator').setEnabled(False)
        self.get_toolbar('overshooter').setEnabled(False)
        self.preset_manager.enable_actions(True)

    def do_things_after_preset_set(self, preset_name: str):

        self.configurator.update_menu(self.get_menu('configurator'))

        self.get_menu('configurator').setEnabled(True)
        self.get_toolbar('configurator').setEnabled(True)
        self.get_menu('overshooter').setEnabled(True)
        self.get_toolbar('overshooter').setEnabled(True)
        self.configurator.enable_actions(True)
        self.overshooter.enable_actions(True)
        self.configurator._execute_entry(self.configurator.entry_filepath)

        for menu in (self.roi_menu, self.remote_menu, self.extensions_menu):
            menu.setEnabled(True)

        self.mainwindow.show()

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
                now.strftime("%Y/%m/%d %H:%M:%S") + ": " + txt
            )
            self.logger_list.addItem(new_item)

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
        try:
            for detector_module in detector_modules[:]:
                if detector_module in self.detector_modules:
                    self.detector_modules.remove(detector_module)


                # Remove from compact dock manager
                if self.compact_detector_manager:
                    is_empty = self.compact_detector_manager.remove_module(detector_module)
                    if is_empty:
                        self.compact_detector_manager.close()
                        self.compact_detector_manager = None
                detector_module.quit_fun()

                # Close individual detector dock
                dock = self.dockarea.docks.get(f"{detector_module.title}", None)
                if dock:
                    dock.close()
        except Exception as e:
            logger.exception(str(e))

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
        try:
            for actuator_module in actuator_modules[:]:
                if actuator_module in self.actuators_modules:
                    self.actuators_modules.remove(actuator_module)
                # Remove from compact dock manager
                if self.compact_actuator_manager:
                    is_empty = self.compact_actuator_manager.remove_module(actuator_module)
                    if is_empty:
                        self.compact_actuator_manager.close()
                        self.compact_actuator_manager = None

                actuator_module.quit_fun()
                
                # Close individual actuator dock (for non-compact actuators)
                dock:Dock = self.dockarea.docks.get(actuator_module.title, None)
                if dock:
                    dock.removeWidgets()
                    dock.close()
        except Exception as e:
            logger.exception(str(e))

    def get_docks_from_modules(
        self, modules: Sequence[Union["DAQ_Move", "DAQ_Viewer"]]
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
        self, modules: List[Union["DAQ_Move", "DAQ_Viewer", "str"]] = None
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
                        self.modules_manager.get_mods_from_names([module,], "act",))  # For actuators

                    detector_modules.extend(
                        self.modules_manager.get_mods_from_names([module,], "det",)  # For detectors
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
                       win: QtWidgets.QMainWindow = None
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

    def setup_actions(self):
        self.add_action("load_layout", "Load Layout", "",
                        "Load the Saved Docks layout corresponding to the current preset",
                        auto_toolbar=False,)
        self.add_action("save_layout", "Save Layout", "",
                        "Save the Saved Docks layout corresponding to the current preset",
                        auto_toolbar=False,)
        self.add_action("show_log_widget", "Show/hide log window", "", checkable=True, auto_toolbar=False)

        self.add_toolbar('preset', 'Preset Toolbar', parent=self.mainwindow,
                         add_break=False)
        self.add_toolbar('configurator', 'Configurator Toolbar', parent=self.mainwindow,
                         add_break=False)
        self.add_toolbar('overshooter', 'Overshoot Toolbar', parent=self.mainwindow,
                         add_break=False)
        self.toolbar.addSeparator()

        self.add_action("save_roi", "Save ROIs as a file", "", auto_toolbar=False)
        self.add_action("modify_roi", "Modify ROI file", "", auto_toolbar=False)

        for file in get_set_roi_path().iterdir():
            if file.suffix == ".xml":
                self.add_action(
                    self.get_action_from_file(file, ManagerEnums.roi),
                    file.stem,
                    "",
                    auto_toolbar=False,
                )
        self.add_action('show_remote', "Show/Hide Remote", 'visibility',
                        icon_checked='visibility_off', auto_toolbar=False)
        self.add_action("new_remote", "Create New Remote", "", auto_toolbar=False)
        self.add_action("modify_remote", "Modify Remote file", "", auto_toolbar=False)
        for file in get_set_remote_path().iterdir():
            if file.suffix == ".xml":
                self.add_action(
                    self.get_action_from_file(file, ManagerEnums.remote),
                    file.stem,
                    "",
                    auto_toolbar=False,
                )
        self.toolbar.addSeparator()
        for ext_name in ExtensionEnum.names():
            self.add_action(ExtensionEnum[ext_name], ExtensionEnum[ext_name].value,
                            auto_toolbar=False)

        self.add_action("configurator", "Configurator", auto_toolbar=False)

    def connect_things(self):
        self.status_signal[str].connect(self.add_status)
        self.connect_action("load_layout", self.load_layout_state)
        self.connect_action("save_layout", self.save_layout_state)
        self.connect_action("show_log_widget", self.show_log_widget)

        self.connect_action("save_roi", self.create_roi_file)
        self.connect_action("modify_roi", self.modify_roi)

        for file in get_set_roi_path().iterdir():
            if file.suffix == ".xml":
                self.connect_action(
                    self.get_action_from_file(file, ManagerEnums.roi),
                    self.create_menu_slot_roi(get_set_roi_path().joinpath(file)),
                )
        self.connect_action('show_remote', self.show_remote)
        self.connect_action("new_remote", self.create_remote)
        self.connect_action("modify_remote", self.modify_remote)
        
        for file in get_set_remote_path().iterdir():
            if file.suffix == ".xml":
                self.connect_action(
                    self.get_action_from_file(file, ManagerEnums.remote),
                    self.create_menu_slot_remote(get_set_remote_path().joinpath(file)),
                )
        for ext_name in ExtensionEnum.names():
            self.connect_action(ExtensionEnum[ext_name],
                                self.create_extension_slot(ExtensionEnum[ext_name]))

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        """
        Create the menubar object looking like :
        """
        #menubar.clear()

        settings_menu = self.add_menu('settings', 'Settings', auto_menu=False)
        settings_menu.addAction(self.get_action("show_log_widget"))

        docked_menu = settings_menu.addMenu("Docked windows")
        docked_menu.addAction(self.get_action("load_layout"))
        docked_menu.addAction(self.get_action("save_layout"))

        self.add_menu('preset', 'Preset', auto_menu=False)
        self.add_menu('configurator', 'Configurator', auto_menu=False)
        self.get_menu('configurator').setEnabled(False)
        self.add_menu('overshooter', 'Overshooter', auto_menu=False)
        self.get_menu('overshooter').setEnabled(False)

        self.roi_menu = self.add_menu('roi', 'ROI', auto_menu=False)
        self.update_roi_menu()

        self.remote_menu = self.add_menu('remote', "Remote/Shortcuts Control")
        self.update_remote_menu()

        # extensions menu
        self.extensions_menu = self.add_menu('extensions', "Extensions")
        for ext_name in ExtensionEnum.names():
            self.extensions_menu.addAction(self.get_action(ExtensionEnum[ext_name]))

        status = True

        for menu in (self.roi_menu, self.remote_menu, self.extensions_menu):
            menu.setEnabled(not status)
        settings_menu.setEnabled(True)
        self.get_menu('preset').setEnabled(status)


    def update_roi_menu(self):
        self.roi_menu.clear()
        self.roi_menu.addAction(self.get_action("save_roi"))
        self.roi_menu.addAction(self.get_action("modify_roi"))
        self.roi_menu.addSeparator()
        load_roi_menu = self.roi_menu.addMenu("Load roi configs")

        for file in get_set_roi_path().iterdir():
            if file.suffix == ".xml":
                load_roi_menu.addAction(
                    self.get_action(self.get_action_from_file(file, ManagerEnums.roi))
                )

    def update_remote_menu(self):
        self.remote_menu.clear()
        self.remote_menu.addAction(self.get_action("show_remote"))
        self.connect_action('show_remote', self.show_remote)
        self.remote_menu.addSeparator()

        self.remote_menu.addAction(self.get_action('new_remote'))
        self.connect_action('new_remote', self.create_remote)
        self.remote_menu.addAction(self.get_action('modify_remote'))
        self.connect_action('modify_remote', self.modify_remote)
        self.remote_menu.addSeparator()
        load_remote_menu = self.remote_menu.addMenu("Load remote config.")

        for file in get_set_remote_path().iterdir():
            if file.suffix == ".xml":
                load_remote_menu.addAction(
                    self.get_action(self.get_action_from_file(file, ManagerEnums.remote))
                )

    def create_remote(self):
        try:
            if self.preset_file is not None:
                self.remote_manager.set_new_remote(self.preset_file.stem)
                self.add_action(
                    self.get_action_from_file(self.preset_file, ManagerEnums.remote),
                    self.preset_file.stem,
                    "",
                )
                self.setup_menu(self.menubar)
                self.connect_action(
                    self.get_action_from_file(self.preset_file, ManagerEnums.remote),
                    self.create_menu_slot_remote(get_set_remote_path().joinpath(self.preset_file.name)),
                )

        except Exception as e:
            logger.exception(str(e))

    def modify_remote(self):
        try:
            path = select_file(
                start_path=get_set_remote_path(),
                save=False,
                ext="xml",
            )
            if path != "":
                self.remote_manager.set_file_remote(path)

            else:  # cancel
                pass
        except Exception as e:
            logger.exception(str(e))

    def show_remote(self, show=True):
        self.remote_widget.setVisible(show)
        self.remote_widget.closeEvent = lambda event: self.set_action_checked('show_remote', False)

    def show_log_widget(self, show=True):
        self.logger_widget.setVisible(show)
        self.logger_widget.closeEvent = lambda event: self.set_action_checked('show_log_widget', False)

    def create_menu_slot_roi(self, filename):
        return lambda: self.set_roi_configuration(filename)

    def create_menu_slot_remote(self, filename):
        return lambda: self.set_remote_configuration(filename)

    def create_extension_slot(self, extenum: ExtensionEnum):
        return lambda: self.load_extension(extenum)

    def create_roi_file(self):
        try:
            if self.preset_file is not None:
                self.roi_saver.set_new_roi(self.preset_file.stem)
                self.add_action(
                    self.get_action_from_file(self.preset_file, ManagerEnums.roi),
                    self.preset_file.stem,
                    "",
                )
                self.setup_menu(self.menubar)
                self.connect_action(
                    self.get_action_from_file(self.preset_file, ManagerEnums.roi),
                    self.create_menu_slot_roi(get_set_roi_path().joinpath(self.preset_file.name)),
                )


        except Exception as e:
            logger.exception(str(e))

    @staticmethod
    def get_action_from_file(file: Path, manager: ManagerEnums):
        return f"{file.stem}_{manager.name}"

    def modify_roi(self):
        try:
            path = select_file(
                start_path=get_set_roi_path(), save=False, ext="xml"
            )
            if path != "":
                self.roi_saver.set_file_roi(path)

            else:  # cancel
                pass
        except Exception as e:
            logger.exception(str(e))

    def quit_fun(self):
        """
        Quit the current instance of DashBoard and close on cascade move and detector modules.

        See Also
        --------
        quit_fun
        """
        try:
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

            for module in self.actuators_modules:
                try:
                    module.quit_fun()
                    QtWidgets.QApplication.processEvents()
                    QThread.msleep(1000)
                    QtWidgets.QApplication.processEvents()
                except Exception:
                    pass

            for module in self.detector_modules:
                try:
                    module.quit_fun()
                    QtWidgets.QApplication.processEvents()
                    QThread.msleep(1000)
                    QtWidgets.QApplication.processEvents()
                except Exception:
                    pass

            self.preset_manager.quit_fun()
            self.configurator.quit_fun()
            self.overshooter.quit_fun()

            areas = self.dockarea.tempAreas[:]
            for area in areas:
                area.win.close()
                QtWidgets.QApplication.processEvents()
                QThread.msleep(1000)
                QtWidgets.QApplication.processEvents()

            if hasattr(self, "mainwindow"):
                self.mainwindow.close()

            if self.pid_window is not None:
                self.pid_window.close()

        except Exception as e:
            logger.exception(str(e))

    def restart_fun(self, ask=False):
        ret = False
        mssg = QMessageBox()
        if ask:
            mssg.setText(
                "You have to restart the application to take the"
                " modifications into account!"
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
        if self.preset_file is not None:
            path = get_set_layout_path().joinpath(self.preset_file.stem + ".dock")
            self.save_layout_state(path)

    def add_move(
            self,
            plug_name: str = None,
            plug_settings: Parameter = None,
            plug_type: str = None,
            actuator_docks: list[Dock] = None,
            actuator_widgets: list[QtWidgets.QWidget] = None,
            actuators_modules: list[DAQ_Move] = None,
            ui_identifier: str = None,
            **kwargs
    ) -> DAQ_Move:        
        if actuator_docks is None:
            actuator_docks = []
        if actuator_widgets is None:
            actuator_widgets = []
        if actuators_modules is None:
            actuators_modules = []      

        if ui_identifier is not None:
            pass
        elif plug_settings is None:
            ui_identifier = config("pymodaq", "actuator", "ui")
        else:
            try:
                ui_identifier = plug_settings["main_settings", "ui_type"]
            except KeyError:
                ui_identifier = config("pymodaq", "actuator", "ui")

        is_compact = (
            ActuatorUIFactory.get(ui_identifier).is_compact
            if ui_identifier is not None
            else False
        )

        if is_compact:
            # Create compact manager if needed
            if self.compact_actuator_manager is None:
                self.compact_actuator_manager = ActuatorCompactDock(
                    "Simple Actuators",
                    self.dockarea,
                    orientation=Qt.Orientation.Vertical,
                )
                self.compact_actuator_manager.show("top")
            dock = None  # Compact widgets don't have individual docks

        else:
            dock = Dock(plug_name, size=(150, 250))
            actuator_docks.append(dock)

            if len(actuator_docks) == 1:
                self.dockarea.addDock(dock, "top")
            else:
                self.dockarea.addDock(dock, "above", actuator_docks[-2])
        QtWidgets.QApplication.processEvents()

        actuator_widgets.append(QtWidgets.QWidget())
        mov_mod_tmp = DAQ_Move(actuator_widgets[-1], plug_name, ui_identifier=ui_identifier)

        mov_mod_tmp.actuator = plug_type
        QtWidgets.QApplication.processEvents()

        if plug_settings is not None:
            try:
                putils.set_param_from_param(mov_mod_tmp.settings, plug_settings)
            except KeyError as e:
                mssg = (
                    f"Could not set this setting: {str(e)}\n"
                    f"The Preset is no more compatible with the plugin {plug_type}"
                )
                logger.warning(mssg)
                self.splash_sc.showMessage(mssg)
        QtWidgets.QApplication.processEvents()

        mov_mod_tmp.bounds_signal[bool].connect(self.do_stuff_from_out_bounds)

        # Add widget to appropriate container
        if is_compact:
            self.compact_actuator_manager.add_module(mov_mod_tmp)
        else:
            dock.addWidget(actuator_widgets[-1])

        actuators_modules.append(mov_mod_tmp)
        return mov_mod_tmp

    def add_move_from_extension(
        self, name: str, instrument_name: str, instrument_controller: Any,
            ui_identifier = None,
            **kwargs
    ):
        """Specific method to add a DAQ_Move within the Dashboard. This Particular actuator
        should be defined in the plugin of the extension and is used to mimic an actuator while
        move_abs is actually triggering an action on the extension which loaded it

        For an exemple, see the PyMoDAQ builtin PID extension

        Parameters
        ----------
        name: str
            The name to print on the UI title
        instrument_name: str
            The name of the instrument class, for instance PID for the daq_move_PID
            module and the DAQ_Move_PID instrument class
        instrument_controller: object
            whatever object is used to communicate between the instrument module and the extension
            which created it
        ui_identifier: str
            One of the possible registered UI
        kwargs: named arguments to be passed to add_move
        """
        actuator = self.add_move(name, None, instrument_name, [], [], [],
                                 ui_identifier=ui_identifier,
                                 **kwargs)
        actuator.controller = instrument_controller
        actuator.master = False
        actuator.init_hardware_ui()
        QtWidgets.QApplication.processEvents()
        self.modules_manager.poll_init(actuator)
        QtWidgets.QApplication.processEvents()

        # Update actuators modules and module manager
        self.actuators_modules.append(actuator)

    def add_det(self, plug_name, plug_settings, detector_docks_viewer,
                detector_modules, plug_type: str = None,  plug_subtype: str = None) -> DAQ_Viewer:
        if plug_type is None:
            plug_type = plug_settings.child("main_settings", "DAQ_type").value()
        if plug_subtype is None:
            plug_subtype = plug_settings.child("main_settings", "detector_type").value()

        # Create compact manager if needed
        if self.compact_detector_manager is None:
            self.compact_detector_manager = DetectorCompactDock(
                "DAQ Viewer Toolbars",
                self.dockarea,
                orientation=Qt.Orientation.Vertical,
            )
            self.compact_detector_manager.show("top")

        # Create individual detector dock
        detector_docks_viewer.append(Dock(plug_name, size=(350, 350)))
        if len(detector_modules) == 0:
            self.dockarea.addDock(detector_docks_viewer[-1], "bottom")
        else:
            self.dockarea.addDock(detector_docks_viewer[-1], "right", detector_docks_viewer[-2])
        widget = QtWidgets.QWidget()
        detector_docks_viewer[-1].addWidget(widget)
        det_mod_tmp = DAQ_Viewer(
            widget,
            title=plug_name,
            daq_type=plug_type,
        )

        self.compact_detector_manager.add_module(det_mod_tmp)
        QtWidgets.QApplication.processEvents()
        det_mod_tmp.detector = SelectedModule(plug_type, plug_subtype)
        QtWidgets.QApplication.processEvents()

        if plug_settings is not None:
            try:
                putils.set_param_from_param(det_mod_tmp.settings, plug_settings)
            except KeyError as e:
                mssg = (
                    f"Could not set this setting: {str(e)}\n"
                    f"The Preset is no more compatible with the plugin {plug_subtype}"
                )
                logger.warning(mssg)
                self.splash_sc.showMessage(mssg)

        detector_modules.append(det_mod_tmp)
        return det_mod_tmp

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
        self, name: str, daq_type: str, instrument_name: str, instrument_controller: Any
    ):
        """Specific method to add a DAQ_Viewer within the Dashboard. This Particular detector
        should be defined in the plugin of the extension and is used to mimic a grab while data
        are actually coming from the extension which loaded it

        For an exemple, see the pymodaq_plugins_datamixer plugin and its DataMixer extension
        or the DAQ_PID extension

        Parameters
        ----------
        name: str
            The name to print on the UI title
        daq_type: str
            either DAQ0D, DAQ1D, DAQ2D or DAQND depending the type of the instrument
        instrument_name: str
            The name of the instrument class, for instance DataMixer for the daq_0Dviewer_DataMixer
            module and the DAQ_0DViewer_DataMixer instrument class
        instrument_controller: object
            whatever object is used to communicate between the instrument module and the extension
            which created it
        """
        detector = self.add_det(
            name, None, [], [], plug_type=daq_type, plug_subtype=instrument_name
        )
        detector.controller = instrument_controller
        detector.master = False
        detector.init_hardware_ui()
        QtWidgets.QApplication.processEvents()
        self.modules_manager.poll_init(detector)
        QtWidgets.QApplication.processEvents()

        # Update actuators modules and module manager
        self.detector_modules.append(detector)

    def set_roi_configuration(self, filename):
        if not isinstance(filename, Path):
            filename = Path(filename)
        try:
            if filename.suffix == ".xml":
                file = filename.stem
                self.settings.child("loaded_files", "roi_file").setValue(file)
                self.update_status(
                    "ROI configuration ({}) has been loaded".format(file),
                    log_type="log",
                )
                self.roi_saver.set_file_roi(filename, show=False)

        except Exception as e:
            logger.exception(str(e))

    def set_remote_configuration(self, filename):
        if not isinstance(filename, Path):
            filename = Path(filename)
        ext = filename.suffix
        if ext == ".xml":
            self.remote_file = filename
            self.remote_manager.remote_changed.connect(self.activate_remote)
            self.remote_manager.set_file_remote(filename, show=False)
            self.settings.child("loaded_files", "remote_file").setValue(filename)
            self.remote_manager.set_remote_configuration()
            self.remote_widget.layout().addWidget(self.remote_manager.remote_settings_tree)
            self.get_action('show_remote').trigger()

    def activate_remote(self, remote_action, activate_all=False):
        """
        remote_action = dict(action_type='shortcut' or 'joystick',
                            action_name='blabla',
                            action_dict= either:
                                dict(shortcut=action.child(('shortcut')).value(), activated=True,
                                 name=f'action{ind:02d}', action=action.child(('action')).value(),
                                  module_name=module, module_type=module_type)

                                or:
                                 dict(joystickID=action.child(('joystickID')).value(),
                                     actionner_type=action.child(('actionner_type')).value(),
                                     actionnerID=action.child(('actionnerID')).value(),
                                     activated=True, name=f'action{ind:02d}',
                                     module_name=module, module_type=module_type)

        """
        if remote_action["action_type"] == "shortcut":
            if remote_action["action_name"] not in self.shortcuts:
                self.shortcuts[remote_action["action_name"]] = QtWidgets.QShortcut(
                    QtGui.QKeySequence(remote_action["action_dict"]["shortcut"]),
                    self.dockarea,
                )
            self.activate_shortcut(
                self.shortcuts[remote_action["action_name"]],
                remote_action["action_dict"],
                activate=remote_action["action_dict"]["activated"],
            )

        elif remote_action["action_type"] == "joystick":
            if not self.ispygame_init:
                self.init_pygame()

            if remote_action["action_name"] not in self.joysticks:
                self.joysticks[remote_action["action_name"]] = remote_action[
                    "action_dict"
                ]

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
                        self.joysticks_obj, "id", action_dict["joystickID"]
                    )
                    val = joy["obj"].get_axis(action_dict["actionnerID"])
                    if abs(val) > 1e-4:
                        module = self.modules_manager.get_mod_from_name(
                            action_dict["module_name"], mod=action_dict["module_type"]
                        )
                        action = getattr(module, action_dict["action"])
                        if module.move_done_bool:
                            action(
                                val
                                * 1
                                * module.settings.child(
                                    "move_settings", "epsilon"
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
                            action_dict["module_name"], mod=action_dict["module_type"]
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
            action["module_name"], mod=action["module_type"]
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
    def preset_file(self) -> Path:
        return self.preset_manager.entry_filepath

    def update_init_tree(self):
        for act in self.actuators_modules:
            name = "".join(act.title.split())  # remove empty spaces
            if act.title not in [
                ac.title()
                for ac in putils.iter_children_params(
                    self.settings.child("actuators"), []
                )
            ]:
                self.settings.child("actuators").addChild(
                    {"title": act.title, "name": name, "type": "led", "value": False}
                )
                QtWidgets.QApplication.processEvents()
            self.settings.child("actuators", name).setValue(act.initialized_state)

        for det in self.detector_modules:
            name = "".join(det.title.split())  # remove empty spaces
            if det.title not in [
                de.title()
                for de in putils.iter_children_params(
                    self.settings.child("detectors"), []
                )
            ]:
                self.settings.child("detectors").addChild(
                    {"title": det.title, "name": name, "type": "led", "value": False}
                )
                QtWidgets.QApplication.processEvents()
            self.settings.child("detectors", name).setValue(det.initialized_state)

    def do_stuff_from_out_bounds(self, out_of_bounds: bool):
        if out_of_bounds:
            logger.warning(f"Some actuators reached their bounds")
            if self.extensions[ExtensionEnum.SCAN] is not None:
                logger.warning(f"Stopping the DAQScan for out of bounds")
                self.extensions[ExtensionEnum.SCAN].stop_scan()

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

    def setup_docks(self):
        # %% create logger dock
        self.logger_widget = QtWidgets.QWidget(windowTitle='Logger')
        self.logger_widget.setLayout(QtWidgets.QVBoxLayout())
        self.logger_widget.setVisible(False)

        self.logger_list = QtWidgets.QListWidget()
        self.logger_list.setMinimumWidth(300)

        splitter = QtWidgets.QSplitter(Qt.Vertical)
        splitter.addWidget(self.settings_tree)
        splitter.addWidget(self.logger_list)
        self.logger_widget.layout().addWidget(splitter)

        self.remote_widget = QtWidgets.QWidget(windowTitle='Remote Manager')
        self.remote_widget.setLayout(QtWidgets.QVBoxLayout())
        self.remote_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.remote_widget.setVisible(False)


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

    def update_status(self, txt, wait_time=0, log_type=None):
        """
        Show the txt message in the status bar with a delay of wait_time ms.

        =============== =========== =======================
        **Parameters**    **Type**    **Description**
        *txt*             string      The message to show
        *wait_time*       int         the delay of showing
        *log_type*        string      the type of the log
        =============== =========== =======================
        """
        try:
            if log_type is not None:
                self.status_signal.emit(txt)
                logging.info(txt)
        except Exception as e:
            pass


def create_load_dashboard() -> tuple[SharedUI, DashBoard]:
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle("PyMoDAQ Dashboard")

    shared_ui = SharedUI(win)
    dashboard = DashBoard(area)
    shared_ui.affect_application(dashboard)
    return shared_ui, dashboard


def load_dashboard_with_preset(preset_name: str,
                               extension_name: str = None,
                               configuration_name: str = None)  -> tuple[DashBoard, 'CustomExt', SharedUI]:

    """ Load the Dashboard using a given preset then load an extension

    Parameters
    ----------
    configuration_name: str
    preset_name: str
        The filename (without extension) defining the preset to be loaded in the Dashboard
    extension_name: str
        The name of the extension. Either the builtins ones:
        * 'DAQScan'
        * 'DAQLogger'
        * 'DAQ_PID'
        * 'Bayesian'

        or the ones defined within a plugin

    Returns
    -------

    """
    from pymodaq.utils.config import get_set_configurator_path, get_set_preset_path
    shared_ui, dashboard = create_load_dashboard()

    preset_path = get_set_preset_path().joinpath(f'{preset_name}.xml')
    preset_name = preset_path.stem
    extension = None

    if preset_name in dashboard.preset_manager.entries:
        dashboard.preset_manager.entry = preset_name
        dashboard.preset_manager.execute_entry(preset_path)
        if configuration_name is not None:
            configuration_path = get_set_configurator_path().joinpath(preset_name).joinpath(f'{configuration_name}.config')
            dashboard.configurator.entry = configuration_name
            dashboard.configurator.execute_entry(configuration_path)
        if extension_name in ExtensionEnum.names():
            extension = dashboard.load_extension(ExtensionEnum[extension_name])
        else:
            extension = None

    else:
        msgBox = QMessageBox()
        msgBox.setText(f"The default file specified in the configuration file does not exists!\n"
                       f"{preset_name}\n"
                       f"Impossible to load the {extension_name} extension")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Ok)
        ret = msgBox.exec()
    return dashboard, extension, shared_ui



def main():
    from pymodaq_gui.qt_utils import mkQApp
    # Create application and main window
    app = mkQApp('Dashboard')

    extensions_names = ExtensionEnum.values()
    # Command-line argument parsing
    parser = argparse.ArgumentParser(prog="dashboard",
                                     description="PyMoDAQ dashboard. "
                                                 "Command-line options only affect GUI initial state."
                                     )
    parser.add_argument("-p", "--preset", metavar="PRESET_NAME",
                        help="preset name to load at startup")
    parser.add_argument("-c", "--config", metavar="CONFIG_NAME",
                        help="config name to execute (ignored if no preset provided)")
    parser.add_argument("-e", "--extension", metavar="EXTENSION_NAME",
                        help="extension name to execute (ignored if no preset provided), valid "
                             'values are within: "' + '\" \"'.join(extensions_names) +'"')
    args = parser.parse_args()

    # If preset name is supplied, load dashboard with this preset
    if args.preset:
        dashboard, extension, win = load_dashboard_with_preset(preset_name=args.preset,
                                                               extension_name=args.extension,
                                                               configuration_name=args.config
                                                               )


    # If no command-line arguments are supplied, start empty
    else:
        win, dashboard = create_load_dashboard()

    win.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

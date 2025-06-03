#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import datetime
import subprocess
import logging
from pathlib import Path
from importlib import import_module
from packaging import version as version_mod
from typing import Tuple, List, Any, TYPE_CHECKING


from qtpy import QtGui, QtWidgets, QtCore
from qtpy.QtCore import Qt, QObject, Slot, QThread, Signal, QSize
from qtpy.QtWidgets import QTableWidget, QTableWidgetItem, QCheckBox, QWidget, QLabel, QDialogButtonBox, QDialog
from time import perf_counter
import numpy as np

from pymodaq_plugin_manager.manager import PluginManager
from pymodaq_plugin_manager.validate import get_pypi_pymodaq

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import utils
from pymodaq_utils.utils import get_version, find_dict_in_list_from_key_val
from pymodaq_utils import config as configmod
from pymodaq_utils.enums import BaseEnum

from pymodaq_gui.parameter import ParameterTree, Parameter
from pymodaq_gui.utils import DockArea, Dock, select_file
import pymodaq_gui.utils.layout as layout_mod
from pymodaq_gui.messenger import messagebox
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.managers.roi_manager import ROISaver
from pymodaq_gui.utils.custom_app import CustomApp

from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq.utils.managers.preset_manager import PresetManager
from pymodaq.utils.managers.overshoot_manager import OvershootManager
from pymodaq.utils.managers.remote_manager import RemoteManager
from pymodaq.utils.exceptions import DetectorError, ActuatorError, MasterSlaveError
from pymodaq.utils.daq_utils import get_instrument_plugins
from pymodaq.utils.leco.utils import start_coordinator
from pymodaq.utils import config as config_mod_pymodaq

from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq_gui.utils.splash import get_splash_sc

from pymodaq import extensions as extmod

logger = set_logger(get_module_name(__file__))
config = configmod.Config()

get_instrument_plugins()
extensions = extmod.get_extensions()


local_path = configmod.get_set_local_dir()
now = datetime.datetime.now()
preset_path = config_mod_pymodaq.get_set_preset_path()
log_path = configmod.get_set_log_path()
layout_path = config_mod_pymodaq.get_set_layout_path()
overshoot_path = config_mod_pymodaq.get_set_overshoot_path()
roi_path = config_mod_pymodaq.get_set_roi_path()
remote_path = config_mod_pymodaq.get_set_remote_path()


class ManagerEnums(BaseEnum):
    preset = 0
    remote = 1
    overshoot = 2
    roi = 3

class PymodaqUpdateTableWidget(QTableWidget):
    '''
        A class to represent PyMoDAQ and its subpackages'
        available updates as a table.
    '''
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
        width  = self.verticalHeader().width()  \
        	   + self.frameWidth() * 2 \
        	   + sum([self.columnWidth(i) for i in range(self.columnCount())])
        
        height = self.horizontalHeader().height() \
        	   + self.frameWidth() * 2 \
        	   + sum([self.rowHeight(i) for i in range(self.rowCount())])

        return QSize(width, height)

class DashBoard(CustomApp):
    """
    Main class initializing a DashBoard interface to display det and move modules and logger """
    status_signal = Signal(str)
    preset_loaded_signal = Signal(bool)
    new_preset_created = Signal()

    settings_name = 'dashboard_settings'
    _splash_sc = None

    params = [
            {'title': 'Log level', 'name': 'log_level', 'type': 'list',
             'value': config('general', 'debug_level'),
             'limits': config('general', 'debug_levels')},

            {'title': 'Loaded presets', 'name': 'loaded_files', 'type': 'group', 'children': [
                {'title': 'Preset file', 'name': 'preset_file', 'type': 'str', 'value': '',
                 'readonly': True},
                {'title': 'Overshoot file', 'name': 'overshoot_file', 'type': 'str', 'value': '',
                 'readonly': True},
                {'title': 'Layout file', 'name': 'layout_file', 'type': 'str', 'value': '',
                 'readonly': True},
                {'title': 'ROI file', 'name': 'roi_file', 'type': 'str', 'value': '',
                 'readonly': True},
                {'title': 'Remote file', 'name': 'remote_file', 'type': 'str', 'value': '',
                 'readonly': True},
            ]},
            {'title': 'Actuators Init.', 'name': 'actuators', 'type': 'group', 'children': []},
            {'title': 'Detectors Init.', 'name': 'detectors', 'type': 'group', 'children': []},
        ]

    def __init__(self, dockarea):
        """

        Parameters
        ----------
        parent: (dockarea) instance of the modified pyqtgraph Dockarea (see daq_utils)
        """
        
        super().__init__(dockarea)

        logger.info('Initializing Dashboard')
        self.extra_params = []
        self.preset_path = preset_path
        self.wait_time = 1000
        self.scan_module = None
        self.log_module = None
        self.pid_module = None
        self.pid_window = None
        self.retriever_module = None
        self.database_module = None
        self.extensions = dict([])
        self.extension_windows = []

        self.dockarea.dock_signal.connect(self.save_layout_state_auto)

        self.title = ''

        self.overshoot_manager = None
        self.preset_manager = None
        self.roi_saver: ROISaver = None

        self.remote_timer = QtCore.QTimer()
        self.remote_manager = None
        self.shortcuts = dict([])
        self.joysticks = dict([])
        self.ispygame_init = False

        self.modules_manager: ModulesManager = None

        self.overshoot = False
        self.preset_file = None
        self.actuators_modules = []
        self.detector_modules = []

        self.setup_ui()

        self.mainwindow.setVisible(True)

        logger.info('Dashboard Initialized')

        if config('general', 'check_version'):
            if self.check_update(show=False):
                sys.exit(0)

    @classmethod
    @property
    def splash_sc(cls) -> QtWidgets.QSplashScreen:
        if cls._splash_sc is None:
            cls._splash_sc = get_splash_sc()
        return cls._splash_sc

    def set_preset_path(self, path):
        self.preset_path = path
        self.set_extra_preset_params(self.extra_params)
        self.create_menu(self.menubar)

    def set_extra_preset_params(self, params, param_options=[]):
        self.extra_params = params
        self.preset_manager = PresetManager(path=self.preset_path, extra_params=params,
                                            param_options=param_options)

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
            new_item = QtWidgets.QListWidgetItem(now.strftime('%Y/%m/%d %H:%M:%S') + ": " + txt)
            self.logger_list.addItem(new_item)

        except Exception as e:
            logger.exception(str(e))

    def clear_move_det_controllers(self):
        """
            Remove all docks containing Moves or Viewers.

            See Also
            --------
            quit_fun, update_status
        """
        try:
            # remove all docks containing Moves or Viewers
            if hasattr(self, 'actuators_modules'):
                if self.actuators_modules is not None:
                    for module in self.actuators_modules:
                        module.quit_fun()
                self.actuators_modules = []

            if hasattr(self, 'detector_modules'):
                if self.detector_modules is not None:
                    for module in self.detector_modules:
                        module.quit_fun()
                self.detector_modules = []
        except Exception as e:
            logger.exception(str(e))

    def load_scan_module(self, win=None):
        if win is None:
            win = QtWidgets.QMainWindow()
        area = DockArea()
        win.setCentralWidget(area)
        self.scan_module = extmod.DAQScan(dockarea=area, dashboard=self)
        self.extensions['DAQScan'] = self.scan_module
        self.scan_module.status_signal.connect(self.add_status)
        #win.setWindowTitle("DAQScan")
        win.show()
        return self.scan_module

    def load_log_module(self, win=None):
        if win is None:
            win = QtWidgets.QMainWindow()
        area = DockArea()
        win.setCentralWidget(area)
        self.log_module = extmod.DAQ_Logger(dockarea=area, dashboard=self)
        self.extensions['DAQ_Logger'] = self.log_module
        self.log_module.status_signal.connect(self.add_status)
        win.show()
        return self.log_module

    def load_pid_module(self, win=None):
        if win is None:
            self.pid_window = QtWidgets.QMainWindow()
        else:
            self.pid_window = win
        dockarea = DockArea()
        self.pid_window.setCentralWidget(dockarea)
        self.pid_window.setWindowTitle('PID Controller')
        self.pid_module = extmod.DAQ_PID(dockarea=dockarea, dashboard=self)
        self.extensions['DAQ_PID'] = self.pid_module
        self.pid_window.show()
        return self.pid_module

    def load_console(self):
        dock_console = Dock('QTConsole')
        self.dockarea.addDock(dock_console, 'bottom')
        qtconsole = extmod.QtConsole(style_sheet=config('style', 'syntax_highlighting'),
                                    syntax_style=config('style', 'syntax_highlighting'),
                                    custom_banner=extmod.console.BANNER)
        dock_console.addWidget(qtconsole)
        self.extensions['qtconsole'] = qtconsole

        qtconsole.push_variables(dict(dashboard=self, mods=self.modules_manager, np=np))

        return qtconsole

    def load_bayesian(self, win=None):
        if win is None:
            self.bayesian_window = QtWidgets.QMainWindow()
        else:
            self.bayesian_window = win
        dockarea = DockArea()
        self.bayesian_window.setCentralWidget(dockarea)
        self.bayesian_window.setWindowTitle('Bayesian Optimiser')
        self.bayesian_module = extmod.BayesianOptimisation(dockarea=dockarea, dashboard=self)
        self.extensions['bayesian'] = self.bayesian_module
        self.bayesian_window.show()
        return self.bayesian_module

    def load_extension_from_name(self, name: str) -> dict:
        return self.load_extensions_module(find_dict_in_list_from_key_val(extensions, 'name', name))

    def load_extensions_module(self, ext: dict):
        """ Init and load an extension from a plugin package

        ext: dict
            dictionary containing info on the extension plugin package and class to be loaded,
             it contains four
            keys:

            * pkg: the name of the plugin package
            * module: the module name where your extension class is defined
            * class_name: the name of the class defining the extension
            * name: a nice name for your extension to be displayed in the menu

        See Also
        --------
        pymodaq.extensions.utils.get_extensions
        """

        self.extension_windows.append(QtWidgets.QMainWindow())
        area = DockArea()
        self.extension_windows[-1].setCentralWidget(area)
        self.extension_windows[-1].resize(1000, 500)
        self.extension_windows[-1].setWindowTitle(ext['name'])
        module = import_module(f"{ext['pkg']}.extensions.{ext['module']}")
        klass = getattr(module, ext['class_name'])
        self.extensions[ext['class_name']] = klass(area, dashboard=self)
        self.extension_windows[-1].show()
        return self.extensions[ext['class_name']]

    def setup_actions(self):
        self.add_action('log', 'Log File', '', "Show Log File in default editor",
                        auto_toolbar=False)
        self.add_action('quit', 'Quit', 'close2', "Quit program")
        self.toolbar.addSeparator()
        self.add_action('config', 'Configuration file', 'tree', "General Settings")
        self.add_action('restart', 'Restart', '', "Restart the Dashboard",
                        auto_toolbar=False)
        self.add_action('leco', 'Run Leco Coordinator', '', 'Run a Coordinator on this localhost',
                        auto_toolbar=False)
        self.add_action('load_layout', 'Load Layout', '',
                        'Load the Saved Docks layout corresponding to the current preset',
                        auto_toolbar=False)
        self.add_action('save_layout', 'Save Layout', '',
                        'Save the Saved Docks layout corresponding to the current preset',
                        auto_toolbar=False)
        self.add_action('log_window', 'Show/hide log window', '', checkable=True,
                        auto_toolbar=False)
        self.add_action('new_preset', 'New Preset', '',
                        'Create a new experimental setup configuration file: a "preset"',
                        auto_toolbar=False)
        self.add_action('modify_preset', 'Modify Preset', '',
                        'Modify an existing experimental setup configuration file: a "preset"',
                        auto_toolbar=False)

        self.add_widget('preset_list', QtWidgets.QComboBox, toolbar=self.toolbar,
                        signal_str='currentTextChanged', slot=self.update_preset_action)
        self.add_action('load_preset', 'LOAD', 'Open',
                        tip='Load the selected Preset: ')
        self.update_preset_action_list()

        self.add_action('new_overshoot', 'New Overshoot', '',
                        'Create a new experimental setup overshoot configuration file',
                        auto_toolbar=False)
        self.add_action('modify_overshoot', 'Modify Overshoot', '',
                        'Modify an existing experimental setup overshoot configuration file',
                        auto_toolbar=False)

        for ind_file, file in enumerate(config_mod_pymodaq.get_set_overshoot_path().iterdir()):
            if file.suffix == '.xml':
                self.add_action(self.get_action_from_file(file, ManagerEnums.overshoot), file.stem,
                                auto_toolbar=False)

        self.add_action('save_roi', 'Save ROIs as a file', '', auto_toolbar=False)
        self.add_action('modify_roi', 'Modify ROI file', '', auto_toolbar=False)

        for ind_file, file in enumerate(config_mod_pymodaq.get_set_roi_path().iterdir()):
            if file.suffix == '.xml':
                self.add_action(self.get_action_from_file(file, ManagerEnums.roi), file.stem,
                                '', auto_toolbar=False)

        self.add_action('new_remote', 'Create New Remote', '', auto_toolbar=False)
        self.add_action('modify_remote', 'Modify Remote file', '', auto_toolbar=False)
        for ind_file, file in enumerate(config_mod_pymodaq.get_set_remote_path().iterdir()):
            if file.suffix == '.xml':
                self.add_action(self.get_action_from_file(file, ManagerEnums.remote),
                                file.stem, '', auto_toolbar=False)
        self.add_action('activate_overshoot', 'Activate overshoot', 'Error',
                        tip='if activated, apply an overshoot if one is configured',
                        checkable=True, enabled=False)
        self.toolbar.addSeparator()
        self.add_action('do_scan', 'Do Scans', 'surfacePlot',
                        tip='Open the DAQ Scan extension to acquire data as a function of '
                            'one or more parameter')
        self.toolbar.addSeparator()
        self.add_action('do_log', 'Log data', '', auto_toolbar=False)
        self.add_action('do_pid', 'PID module', auto_toolbar=False)
        self.add_action('console', 'IPython Console', auto_toolbar=False)
        self.add_action('bayesian', 'Bayesian Optimisation', auto_toolbar=False)

        self.add_action('about', 'About', 'information2')
        self.add_action('help', 'Help', 'help1')
        self.get_action('help').setShortcut(QtGui.QKeySequence('F1'))
        self.add_action('check_update', 'Check Updates', '', auto_toolbar=False)
        self.toolbar.addSeparator()
        self.add_action('plugin_manager', 'Plugin Manager', '')

    def update_preset_action_list(self):
        presets = []
        self.get_action('preset_list').clear()
        for ind_file, file in enumerate(self.preset_path.iterdir()):
            if file.suffix == '.xml':
                filestem = file.stem
                if not self.has_action(self.get_action_from_file(file, ManagerEnums.preset)):
                    self.add_action(self.get_action_from_file(file, ManagerEnums.preset),
                                    filestem, '', f'Load the {filestem}.xml preset',
                                    auto_toolbar=False)
                presets.append(filestem)

        self.get_action('preset_list').addItems(presets)

    def update_preset_action(self, preset_name: str):
        self.get_action('load_preset').setToolTip(f'Load the {preset_name}.xml preset file!')

    def connect_things(self):
        self.status_signal[str].connect(self.add_status)
        self.connect_action('log', self.show_log)
        self.connect_action('config', self.show_config)
        self.connect_action('quit', self.quit_fun)
        self.connect_action('restart', self.restart_fun)
        self.connect_action('leco', start_coordinator)
        self.connect_action('load_layout', self.load_layout_state)
        self.connect_action('save_layout', self.save_layout_state)
        self.connect_action('log_window', self.logger_dock.setVisible)
        self.connect_action('new_preset', self.create_preset)
        self.connect_action('modify_preset', self.modify_preset)

        for ind_file, file in enumerate(self.preset_path.iterdir()):
            if file.suffix == '.xml':
                self.connect_action(self.get_action_from_file(file, ManagerEnums.preset),
                                    self.create_menu_slot(self.preset_path.joinpath(file)))
        self.connect_action('load_preset',
                            lambda: self.set_preset_mode(
                                self.preset_path.joinpath(
                                    f"{self.get_action('preset_list').currentText()}.xml")))
        self.connect_action('new_overshoot', self.create_overshoot)
        self.connect_action('modify_overshoot', self.modify_overshoot)
        self.connect_action('activate_overshoot', self.activate_overshoot)

        for ind_file, file in enumerate(config_mod_pymodaq.get_set_overshoot_path().iterdir()):
            if file.suffix == '.xml':
                self.connect_action(self.get_action_from_file(file, ManagerEnums.overshoot),
                    self.create_menu_slot_over(
                        config_mod_pymodaq.get_set_overshoot_path().joinpath(file)))

        self.connect_action('save_roi', self.create_roi_file)
        self.connect_action('modify_roi', self.modify_roi)

        for ind_file, file in enumerate(config_mod_pymodaq.get_set_roi_path().iterdir()):
            if file.suffix == '.xml':
                self.connect_action(self.get_action_from_file(file, ManagerEnums.roi),
                    self.create_menu_slot_roi(config_mod_pymodaq.get_set_roi_path().joinpath(file)))

        self.connect_action('new_remote', self.create_remote)
        self.connect_action('modify_remote', self.modify_remote)
        for ind_file, file in enumerate(config_mod_pymodaq.get_set_remote_path().iterdir()):
            if file.suffix == '.xml':
                self.connect_action(self.get_action_from_file(file, ManagerEnums.remote),
                    self.create_menu_slot_remote(
                        config_mod_pymodaq.get_set_remote_path().joinpath(file)))

        self.connect_action('do_scan', lambda: self.load_scan_module())
        self.connect_action('do_log', lambda: self.load_log_module())
        self.connect_action('do_pid', lambda: self.load_pid_module())
        self.connect_action('console', lambda: self.load_console())
        self.connect_action('bayesian', lambda: self.load_bayesian())

        self.connect_action('about', self.show_about)
        self.connect_action('help', self.show_help)
        self.connect_action('check_update', lambda: self.check_update(True))
        self.connect_action('plugin_manager', self.start_plugin_manager)

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        """
            Create the menubar object looking like :
        """
        menubar.clear()

        # %% create Settings menu
        self.file_menu = menubar.addMenu('File')
        self.file_menu.addAction(self.get_action('log'))
        self.file_menu.addAction(self.get_action('config'))
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.get_action('quit'))
        self.file_menu.addAction(self.get_action('restart'))

        self.settings_menu = menubar.addMenu('Settings')
        self.settings_menu.addAction(self.get_action('leco'))
        docked_menu = self.settings_menu.addMenu('Docked windows')
        docked_menu.addAction(self.get_action('load_layout'))
        docked_menu.addAction(self.get_action('save_layout'))

        docked_menu.addSeparator()
        docked_menu.addAction(self.get_action('log_window'))

        self.preset_menu = menubar.addMenu('Preset Modes')
        self.preset_menu.addAction(self.get_action('new_preset'))
        self.preset_menu.addAction(self.get_action('modify_preset'))
        self.preset_menu.addSeparator()
        self.load_preset_menu = self.preset_menu.addMenu('Load presets')

        for ind_file, file in enumerate(self.preset_path.iterdir()):
            if file.suffix == '.xml':
                self.load_preset_menu.addAction(
                    self.get_action(self.get_action_from_file(file, ManagerEnums.preset)))

        self.overshoot_menu = menubar.addMenu('Overshoot Modes')
        self.overshoot_menu.addAction(self.get_action('new_overshoot'))
        self.overshoot_menu.addAction(self.get_action('modify_overshoot'))
        self.overshoot_menu.addAction(self.get_action('activate_overshoot'))
        self.overshoot_menu.addSeparator()
        load_overshoot_menu = self.overshoot_menu.addMenu('Load Overshoots')

        for ind_file, file in enumerate(config_mod_pymodaq.get_set_overshoot_path().iterdir()):
            if file.suffix == '.xml':
                load_overshoot_menu.addAction(
                    self.get_action(self.get_action_from_file(file, ManagerEnums.overshoot)))

        self.roi_menu = menubar.addMenu('ROI Modes')
        self.roi_menu.addAction(self.get_action('save_roi'))
        self.roi_menu.addAction(self.get_action('modify_roi'))
        self.roi_menu.addSeparator()
        load_roi_menu = self.roi_menu.addMenu('Load roi configs')

        for ind_file, file in enumerate(config_mod_pymodaq.get_set_roi_path().iterdir()):
            if file.suffix == '.xml':
                load_roi_menu.addAction(
                    self.get_action(self.get_action_from_file(file, ManagerEnums.roi)))

        self.remote_menu = menubar.addMenu('Remote/Shortcuts Control')
        self.remote_menu.addAction('New remote config.', self.create_remote)
        self.remote_menu.addAction('Modify remote config.', self.modify_remote)
        self.remote_menu.addSeparator()
        load_remote_menu = self.remote_menu.addMenu('Load remote config.')

        for ind_file, file in enumerate(config_mod_pymodaq.get_set_remote_path().iterdir()):
            if file.suffix == '.xml':
                load_remote_menu.addAction(
                    self.get_action(self.get_action_from_file(file, ManagerEnums.remote)))

        # extensions menu
        self.extensions_menu = menubar.addMenu('Extensions')
        self.extensions_menu.addAction(self.get_action('do_scan'))
        self.extensions_menu.addAction(self.get_action('do_log'))
        self.extensions_menu.addAction(self.get_action('do_pid'))
        self.extensions_menu.addAction(self.get_action('console'))
        self.extensions_menu.addAction(self.get_action('bayesian'))

        # extensions from plugins
        extensions_actions = []
        for ext in extensions:
            extensions_actions.append(self.extensions_menu.addAction(ext['name']))
            extensions_actions[-1].triggered.connect(self.create_menu_slot_ext(ext))

        # help menu
        help_menu = menubar.addMenu('?')
        help_menu.addAction(self.get_action('about'))
        help_menu.addAction(self.get_action('help'))
        help_menu.addSeparator()
        help_menu.addAction(self.get_action('check_update'))
        help_menu.addAction(self.get_action('plugin_manager'))

        self.overshoot_menu.setEnabled(False)
        self.roi_menu.setEnabled(False)
        self.remote_menu.setEnabled(False)
        self.extensions_menu.setEnabled(False)
        self.file_menu.setEnabled(True)
        self.settings_menu.setEnabled(True)
        self.preset_menu.setEnabled(True)

    def start_plugin_manager(self):
        self.win_plug_manager = QtWidgets.QMainWindow()
        self.win_plug_manager.setWindowTitle('PyMoDAQ Plugin Manager')
        widget = QtWidgets.QWidget()
        self.win_plug_manager.setCentralWidget(widget)
        self.plugin_manager = PluginManager(widget)
        self.plugin_manager.quit_signal.connect(self.quit_fun)
        self.plugin_manager.restart_signal.connect(self.restart_fun)
        self.win_plug_manager.show()

    def create_menu_slot(self, filename):
        return lambda: self.set_preset_mode(filename)

    def create_menu_slot_ext(self, ext):
        return lambda: self.load_extensions_module(ext)

    def create_menu_slot_roi(self, filename):
        return lambda: self.set_roi_configuration(filename)

    def create_menu_slot_over(self, filename):
        return lambda: self.set_overshoot_configuration(filename)

    def create_menu_slot_remote(self, filename):
        return lambda: self.set_remote_configuration(filename)

    def create_roi_file(self):
        try:
            if self.preset_file is not None:
                self.roi_saver.set_new_roi(self.preset_file.stem)
                self.add_action(self.get_action_from_file(self.preset_file,
                                                          ManagerEnums.roi),
                                self.preset_file.stem, '')
                self.setup_menu(self.menubar)

        except Exception as e:
            logger.exception(str(e))

    def create_remote(self):
        try:
            if self.preset_file is not None:
                self.remote_manager.set_new_remote(self.preset_file.stem)
                self.add_action(self.get_action_from_file(self.preset_file,
                                                          ManagerEnums.remote),
                                self.preset_file.stem, '')
                self.setup_menu(self.menubar)

        except Exception as e:
            logger.exception(str(e))

    def create_overshoot(self):
        try:
            if self.preset_file is not None:
                self.overshoot_manager.set_new_overshoot(self.preset_file.stem)
                self.add_action(self.get_action_from_file(self.preset_file,
                                                          ManagerEnums.overshoot),
                                self.preset_file.stem, '')
                self.setup_menu(self.menubar)
        except Exception as e:
            logger.exception(str(e))

    def create_preset(self):
        try:
            status = self.preset_manager.set_new_preset()
            if status:
                self.update_preset_action_list()
                self.setup_menu(self.menubar)
                self.new_preset_created.emit()
        except Exception as e:
            logger.exception(str(e))

    @staticmethod
    def get_action_from_file(file: Path, manager: ManagerEnums):
        return f'{file.stem}_{manager.name}'

    def modify_remote(self):
        try:
            path = select_file(start_path=config_mod_pymodaq.get_set_remote_path(), save=False,
                               ext='xml')
            if path != '':
                self.remote_manager.set_file_remote(path)

            else:  # cancel
                pass
        except Exception as e:
            logger.exception(str(e))

    def modify_overshoot(self):
        try:
            path = select_file(start_path=config_mod_pymodaq.get_set_overshoot_path(),
                               save=False, ext='xml')
            if path != '':
                self.overshoot_manager.set_file_overshoot(path)

            else:  # cancel
                pass
        except Exception as e:
            logger.exception(str(e))

    def modify_roi(self):
        try:
            path = select_file(start_path=config_mod_pymodaq.get_set_roi_path(),
                               save=False, ext='xml')
            if path != '':
                self.roi_saver.set_file_roi(path)

            else:  # cancel
                pass
        except Exception as e:
            logger.exception(str(e))

    def modify_preset(self):
        try:
            path = select_file(start_path=self.preset_path, save=False, ext='xml')
            if path != '':
                modified = self.preset_manager.set_file_preset(path)

                if modified:
                    self.remove_preset_related_files(path.name)
                    if self.detector_modules:
                        mssg = QtWidgets.QMessageBox()
                        mssg.setText('You have to restart the application to take the modifications'
                                     ' into account!\n\n'
                                     'The related files: ROI, Layout, Overshoot and Remote will be'
                                     ' deleted if existing!\n\n'
                                     'Quitting the application...')
                        mssg.exec()
                        self.restart_fun()

            else:  # cancel
                pass
        except Exception as e:
            logger.exception(str(e))

    def remove_preset_related_files(self, name):
        config_mod_pymodaq.get_set_roi_path().joinpath(name).unlink(missing_ok=True)
        config_mod_pymodaq.get_set_layout_path().joinpath(name).unlink(missing_ok=True)
        config_mod_pymodaq.get_set_overshoot_path().joinpath(name).unlink(missing_ok=True)
        config_mod_pymodaq.get_set_remote_path().joinpath(name).unlink(missing_ok=True)

    def quit_fun(self):
        """
            Quit the current instance of DAQ_scan and close on cascade move and detector modules.

            See Also
            --------
            quit_fun
        """
        try:
            self.remote_timer.stop()

            for ext in self.extensions:
                if hasattr(self.extensions[ext], 'quit_fun'):
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
            areas = self.dockarea.tempAreas[:]
            for area in areas:
                area.win.close()
                QtWidgets.QApplication.processEvents()
                QThread.msleep(1000)
                QtWidgets.QApplication.processEvents()

            if hasattr(self, 'mainwindow'):
                self.mainwindow.close()

            if self.pid_window is not None:
                self.pid_window.close()

        except Exception as e:
            logger.exception(str(e))

    def restart_fun(self, ask=False):
        ret = False
        mssg = QtWidgets.QMessageBox()
        if ask:
            mssg.setText('You have to restart the application to take the'
                         ' modifications into account!')
            mssg.setInformativeText("Do you want to restart?")
            mssg.setStandardButtons(mssg.Ok | mssg.Cancel)
            ret = mssg.exec()

        if ret == mssg.Ok or not ask:
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
            self.settings.child('loaded_files', 'layout_file').setValue(file)
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
            path = layout_path.joinpath(self.preset_file.stem + '.dock')
            self.save_layout_state(path)

    def add_move(self, plug_name, plug_settings, plug_type, move_docks, move_forms,
                 actuators_modules) -> DAQ_Move:

        move_docks.append(Dock(plug_name, size=(150, 250)))
        if len(move_docks) == 1:
            self.dockarea.addDock(move_docks[-1], 'right', self.logger_dock)
        else:
            self.dockarea.addDock(move_docks[-1], 'above', move_docks[-2])
        move_forms.append(QtWidgets.QWidget())
        mov_mod_tmp = DAQ_Move(move_forms[-1], plug_name)

        mov_mod_tmp.actuator = plug_type
        QtWidgets.QApplication.processEvents()
        mov_mod_tmp.manage_ui_actions('quit', 'setEnabled', False)

        if plug_settings is not None:
            try:
                putils.set_param_from_param(mov_mod_tmp.settings, plug_settings)
            except KeyError as e:
                mssg = f'Could not set this setting: {str(e)}\n' \
                       f'The Preset is no more compatible with the plugin {plug_type}'
                logger.warning(mssg)
                self.splash_sc.showMessage(mssg)
        QtWidgets.QApplication.processEvents()

        mov_mod_tmp.bounds_signal[bool].connect(self.do_stuff_from_out_bounds)
        move_docks[-1].addWidget(move_forms[-1])
        actuators_modules.append(mov_mod_tmp)
        return mov_mod_tmp

    def add_move_from_extension(self, name: str, instrument_name: str,
                                instrument_controller: Any):
        """ Specific method to add a DAQ_Move within the Dashboard. This Particular actuator
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
        """
        actuator = self.add_move(name, None, instrument_name, [], [], [])
        actuator.controller = instrument_controller
        actuator.master = False
        actuator.init_hardware_ui()
        QtWidgets.QApplication.processEvents()
        self.poll_init(actuator)
        QtWidgets.QApplication.processEvents()

        # Update actuators modules and module manager
        self.actuators_modules.append(actuator)
        self.update_module_manager()

    def add_det(self, plug_name, plug_settings, det_docks_settings, det_docks_viewer,
                detector_modules, plug_type: str = None, plug_subtype: str = None) -> DAQ_Viewer:
        if plug_type is None:
            plug_type = plug_settings.child('main_settings', 'DAQ_type').value()
        if plug_subtype is None:
            plug_subtype = plug_settings.child('main_settings', 'detector_type').value()
        det_docks_settings.append(Dock(plug_name + " settings", size=(150, 250)))
        det_docks_viewer.append(Dock(plug_name + " viewer", size=(350, 350)))
        if len(detector_modules) == 0:
            self.logger_dock.area.addDock(det_docks_settings[-1], 'bottom')
            # dockarea of the logger dock
        else:
            self.dockarea.addDock(det_docks_settings[-1], 'right',
                                  detector_modules[-1].viewer_docks[-1])
        self.dockarea.addDock(det_docks_viewer[-1], 'right', det_docks_settings[-1])
        det_mod_tmp = DAQ_Viewer(self.dockarea, title=plug_name, daq_type=plug_type,
                                 dock_settings=det_docks_settings[-1],
                                 dock_viewer=det_docks_viewer[-1])
        QtWidgets.QApplication.processEvents()
        det_mod_tmp.detector = plug_subtype
        QtWidgets.QApplication.processEvents()
        det_mod_tmp.manage_ui_actions('quit', 'setEnabled', False)

        if plug_settings is not None:
            try:
                putils.set_param_from_param(det_mod_tmp.settings, plug_settings)
            except KeyError as e:
                mssg = f'Could not set this setting: {str(e)}\n' \
                       f'The Preset is no more compatible with the plugin {plug_subtype}'
                logger.warning(mssg)
                self.splash_sc.showMessage(mssg)

        detector_modules.append(det_mod_tmp)
        return det_mod_tmp

    def add_det_from_extension(self, name: str, daq_type: str, instrument_name: str,
                               instrument_controller: Any):
        """ Specific method to add a DAQ_Viewer within the Dashboard. This Particular detector
        should be defined in the plugin of the extension and is used to mimic a grab while data
        are actually coming from the extension which loaded it

        For an exemple, see the pymodaq_plugins_datamixer plugin and its DataMixer extension

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
        detector = self.add_det(name, None, [], [], [],
                                plug_type=daq_type,
                                plug_subtype=instrument_name)
        detector.controller = instrument_controller
        detector.master = False
        detector.init_hardware_ui()
        QtWidgets.QApplication.processEvents()
        self.poll_init(detector)
        QtWidgets.QApplication.processEvents()

        # Update actuators modules and module manager
        self.detector_modules.append(detector)
        self.update_module_manager()

    def update_module_manager(self):
        if self.modules_manager is None:
            self.modules_manager = ModulesManager(self.detector_modules, self.actuators_modules)
        else:
            self.modules_manager.actuators_all = self.actuators_modules
            self.modules_manager.detectors_all = self.detector_modules

    def set_file_preset(self, filename) -> Tuple[List[DAQ_Move], List[DAQ_Viewer]]:
        """
            Set a file managers from the converted xml file given by the filename parameter.


            =============== =========== ===================================================
            **Parameters**    **Type**    **Description**
            *filename*        string      the name of the xml file to be converted/treated
            =============== =========== ===================================================

            Returns
            -------
            (Object list, Object list) tuple
                The updated (Move modules list, Detector modules list).

           """
        actuators_modules = []
        detector_modules = []
        if not isinstance(filename, Path):
            filename = Path(filename)

        if filename.suffix == '.xml':
            self.preset_file = filename
            self.preset_manager.set_file_preset(filename, show=False)
            move_docks = []
            det_docks_settings = []
            det_docks_viewer = []
            move_forms = []

            # ################################################################
            # ##### sort plugins by IDs and within the same IDs by Master and Slave status
            plugins = []
            plugins += [{'type': 'move', 'value': child} for child in
                        self.preset_manager.preset_params.child('Moves').children()]
            plugins += [{'type': 'det', 'value': child} for child in
                        self.preset_manager.preset_params.child('Detectors').children()]

            for plug in plugins:
                if plug["type"] == 'det':
                    plug['ID'] = plug['value']['params', 'detector_settings', 'controller_ID']
                    plug['status'] = plug['value']['params', 'detector_settings',
                        'controller_status']
                else:
                    plug['ID'] = plug['value']['params', 'move_settings',
                        'multiaxes', 'controller_ID']
                    plug['status'] = plug['value'][
                            'params', 'move_settings', 'multiaxes', 'multi_status']


            IDs = list(set([plug['ID'] for plug in plugins]))
            # %%
            plugins_sorted = []
            for id in IDs:
                plug_Ids = []
                for plug in plugins:
                    if plug['ID'] == id:
                        plug_Ids.append(plug)
                plug_Ids.sort(key=lambda status: status['status'])
                plugins_sorted.append(plug_Ids)
            #################################################################
            #######################

            ind_det = -1
            for plug_IDs in plugins_sorted:
                for ind_plugin, plugin in enumerate(plug_IDs):
                    plug_name = plugin['value'].child('name').value()
                    plug_init = plugin['value'].child('init').value()
                    plug_settings = plugin['value'].child('params')
                    self.splash_sc.showMessage(
                        'Loading {:s} module: {:s}'.format(plugin['type'], plug_name))

                    if plugin['type'] == 'move':
                        plug_type = plug_settings.child('main_settings', 'move_type').value()
                        self.add_move(plug_name, plug_settings, plug_type, move_docks, move_forms,
                                      actuators_modules)

                        if ind_plugin == 0:  # should be a master type plugin
                            if plugin['status'] != "Master":
                                raise MasterSlaveError(f'The instrument {plug_name} should'
                                                       f' be defined as Master')
                            if plug_init:
                                actuators_modules[-1].init_hardware_ui()
                                QtWidgets.QApplication.processEvents()
                                self.poll_init(actuators_modules[-1])
                                QtWidgets.QApplication.processEvents()
                                master_controller = actuators_modules[-1].controller
                            elif plugin['status'] == "Master" and len(plug_IDs) > 1:
                                raise MasterSlaveError(
                                    f'The instrument {plug_name} defined as Master has to be '
                                    f'initialized (init checked in the preset) in order to init '
                                    f'its associated slave instrument'
                                )
                        else:
                            if plugin['status'] != "Slave":
                                raise MasterSlaveError(f'The instrument {plug_name} should'
                                                       f' be defined as slave')
                            if plug_init:
                                actuators_modules[-1].controller = master_controller
                                actuators_modules[-1].init_hardware_ui()
                                QtWidgets.QApplication.processEvents()
                                self.poll_init(actuators_modules[-1])
                                QtWidgets.QApplication.processEvents()
                    else:
                        ind_det += 1
                        self.add_det(plug_name, plug_settings, det_docks_settings, det_docks_viewer,
                                     detector_modules)
                        QtWidgets.QApplication.processEvents()

                        if ind_plugin == 0:  # should be a master type plugin
                            if plugin['status'] != "Master":
                                raise MasterSlaveError(f'The instrument {plug_name} should'
                                                       f' be defined as Master')
                            if plug_init:
                                detector_modules[-1].init_hardware_ui()
                                QtWidgets.QApplication.processEvents()
                                self.poll_init(detector_modules[-1])
                                QtWidgets.QApplication.processEvents()
                                master_controller = detector_modules[-1].controller
                            elif plugin['status'] == "Master" and len(plug_IDs) > 1:
                                raise MasterSlaveError(
                                    f'The instrument {plug_name} defined as Master has to be '
                                    f'initialized (init checked in the preset) in order to init '
                                    f'its associated slave instrument'
                                )
                        else:
                            if plugin['status'] != "Slave":
                                raise MasterSlaveError(f'The instrument {plug_name} should'
                                                       f' be defined as Slave')
                            if plug_init:
                                detector_modules[-1].controller = master_controller
                                detector_modules[-1].init_hardware_ui()
                                QtWidgets.QApplication.processEvents()
                                self.poll_init(detector_modules[-1])
                                QtWidgets.QApplication.processEvents()

                        detector_modules[-1].settings.child('main_settings', 'overshoot').show()
                        detector_modules[-1].overshoot_signal[bool].connect(self.stop_moves_from_overshoot)

            QtWidgets.QApplication.processEvents()
            # restore dock state if saved

            self.title = self.preset_file.stem
            path = layout_path.joinpath(self.title + '.dock')
            if path.is_file():
                self.load_layout_state(path)

            self.mainwindow.setWindowTitle(f'PyMoDAQ Dashboard: {self.title}')
            if self.pid_module is not None:
                self.pid_module.set_module_manager(detector_modules, actuators_modules)
            return actuators_modules, detector_modules
        else:
            logger.error('Invalid file selected')
            return actuators_modules, detector_modules

    def poll_init(self, module):
        is_init = False
        tstart = perf_counter()
        while not is_init:
            QThread.msleep(1000)
            QtWidgets.QApplication.processEvents()
            is_init = module.initialized_state
            if perf_counter() - tstart > 60:  # timeout of 60sec
                break
        return is_init

    def set_roi_configuration(self, filename):
        if not isinstance(filename, Path):
            filename = Path(filename)
        try:
            if filename.suffix == '.xml':
                file = filename.stem
                self.settings.child('loaded_files', 'roi_file').setValue(file)
                self.update_status('ROI configuration ({}) has been loaded'.format(file),
                                   log_type='log')
                self.roi_saver.set_file_roi(filename, show=False)

        except Exception as e:
            logger.exception(str(e))

    def set_remote_configuration(self, filename):
        if not isinstance(filename, Path):
            filename = Path(filename)
        ext = filename.suffix
        if ext == '.xml':
            self.remote_file = filename
            self.remote_manager.remote_changed.connect(self.activate_remote)
            self.remote_manager.set_file_remote(filename, show=False)
            self.settings.child('loaded_files', 'remote_file').setValue(filename)
            self.remote_manager.set_remote_configuration()
            self.remote_dock.addWidget(self.remote_manager.remote_settings_tree)
            self.remote_dock.setVisible(True)

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
        if remote_action['action_type'] == 'shortcut':
            if remote_action['action_name'] not in self.shortcuts:
                self.shortcuts[remote_action['action_name']] = \
                    QtWidgets.QShortcut(
                        QtGui.QKeySequence(remote_action['action_dict']['shortcut']), self.dockarea)
            self.activate_shortcut(self.shortcuts[remote_action['action_name']],
                                   remote_action['action_dict'],
                                   activate=remote_action['action_dict']['activated'])

        elif remote_action['action_type'] == 'joystick':
            if not self.ispygame_init:
                self.init_pygame()

            if remote_action['action_name'] not in self.joysticks:
                self.joysticks[remote_action['action_name']] = remote_action['action_dict']

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
                self.joysticks_obj[-1]['obj'].init()
                self.joysticks_obj[-1]['id'] = self.joysticks_obj[-1]['obj'].get_id()

            self.remote_timer.timeout.connect(self.pygame_loop)
            self.ispygame_init = True
            self.remote_timer.start(10)

        except ImportError as e:
            logger.warning('No pygame module installed. Needed for joystick control')

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
            if action_dict['activated'] and action_dict['actionner_type'].lower() == 'axis':
                if action_dict['module_type'] == 'act':
                    joy = utils.find_dict_in_list_from_key_val(self.joysticks_obj, 'id',
                                                               action_dict['joystickID'])
                    val = joy['obj'].get_axis(action_dict['actionnerID'])
                    if abs(val) > 1e-4:
                        module = self.modules_manager.get_mod_from_name(
                            action_dict['module_name'],
                            mod=action_dict['module_type'])
                        action = getattr(module, action_dict['action'])
                        if module.move_done_bool:
                            action(val * 1 * module.settings.child(
                                'move_settings', 'epsilon').value())

        # # For other actions use the event loop
        for event in self.pygame.event.get():  # User did something.
            selection = dict([])
            if 'joy' in event.dict:
                selection.update(dict(joy=event.joy))
            if event.type == self.pygame.JOYBUTTONDOWN:
                selection.update(dict(button=event.button))
            elif event.type == self.pygame.JOYAXISMOTION:
                selection.update(dict(axis=event.axis, value=event.value))
            elif event.type == self.pygame.JOYHATMOTION:
                selection.update(dict(hat=event.hat, value=event.value))
            if len(selection) > 1:
                for action_dict in self.joysticks.values():
                    if action_dict['activated']:
                        module = self.modules_manager.get_mod_from_name(
                            action_dict['module_name'],
                            mod=action_dict['module_type'])
                        if action_dict['module_type'] == 'det':
                            action = getattr(module, action_dict['action'])
                        else:
                            action = getattr(module, action_dict['action'])

                        if action_dict['joystickID'] == selection['joy']:
                            if (action_dict['actionner_type'].lower() == 'button' and
                                    'button' in selection):
                                if action_dict['actionnerID'] == selection['button']:
                                    action()
                            elif (action_dict['actionner_type'].lower() == 'hat' and
                                  'hat' in selection):
                                if action_dict['actionnerID'] == selection['hat']:
                                    action(selection['value'])

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
            shortcut.activated.connect(
                self.create_activated_shortcut(action))
        else:
            try:
                shortcut.activated.disconnect()
            except Exception:
                pass

    def create_activated_shortcut(self, action):
        module = self.modules_manager.get_mod_from_name(action['module_name'],
                                                        mod=action['module_type'])
        if action['module_type'] == 'det':
            return lambda: getattr(module, action['action'])()
        else:
            return lambda: getattr(module, action['action'])()

    def set_overshoot_configuration(self, filename):
        try:
            if not isinstance(filename, Path):
                filename = Path(filename)

            if filename.suffix == '.xml':
                file = filename.stem
                self.settings.child('loaded_files', 'overshoot_file').setValue(file)
                self.update_status('Overshoot configuration ({}) has been loaded'.format(file),
                                   log_type='log')
                self.overshoot_manager.set_file_overshoot(filename, show=False)
                self.set_action_enabled('activate_overshoot', True)
                self.set_action_checked('activate_overshoot', False)
                self.get_action('activate_overshoot').trigger()

        except Exception as e:
            logger.exception(str(e))

    def activate_overshoot(self, status: bool):
        try:
            self.overshoot_manager.activate_overshoot(self.detector_modules,
                                                      self.actuators_modules,
                                                      status)
        except Exception as e:
            logger.warning(f'Could not load the overshoot file:\n{str(e)}')
            self.set_action_checked('activate_overshoot', False)
            self.set_action_enabled('activate_overshoot', False)

    @property
    def move_modules(self):
        """
        for back compatibility
        """
        return self.actuators_modules

    def set_preset_mode(self, filename):
        """
            | Set the managers mode from the given filename.
            |
            | In case of "mock" or "canon" move, set the corresponding managers calling
            set_(*)_preset procedure.
            |
            | Else set the managers file using set_file_preset function.
            | Once done connect the move and detector modules to logger to recipe/transmit
            informations.

            Finally update DAQ_scan_settings tree with :
                * Detectors
                * Move
                * plot_form.

            =============== =========== =============================================
            **Parameters**    **Type**    **Description**
            *filename*        string      the name of the managers file to be treated
            =============== =========== =============================================

            See Also
            --------
            set_Mock_preset, set_canon_preset, set_file_preset, add_status, update_status
        """
        try:
            if not isinstance(filename, Path):
                filename = Path(filename)

            self.get_action('preset_list').setCurrentText(filename.stem)

            self.mainwindow.setVisible(False)
            for area in self.dockarea.tempAreas:
                area.window().setVisible(False)

            self.splash_sc.show()
            QtWidgets.QApplication.processEvents()
            self.splash_sc.raise_()
            self.splash_sc.showMessage('Loading Modules, please wait')
            QtWidgets.QApplication.processEvents()
            self.clear_move_det_controllers()
            QtWidgets.QApplication.processEvents()

            logger.info(f'Loading Preset file: {filename}')

            try:
                actuators_modules, detector_modules = self.set_file_preset(filename)
            except (ActuatorError, DetectorError, MasterSlaveError) as error:
                self.splash_sc.close()
                self.mainwindow.setVisible(True)
                for area in self.dockarea.tempAreas:
                    area.window().setVisible(True)
                messagebox(text=f'{str(error)}\nQuitting the application...',
                           title='Incompatibility')
                logger.exception(str(error))

                self.quit_fun()
                return

            if not (not actuators_modules and not detector_modules):
                self.update_status('Preset mode ({}) has been loaded'.format(filename.name),
                                   log_type='log')
                self.settings.child('loaded_files', 'preset_file').setValue(filename.name)
                self.actuators_modules = actuators_modules
                self.detector_modules = detector_modules

                self.update_module_manager()

                #####################################################
                self.overshoot_manager = OvershootManager(
                    det_modules=[det.title for det in detector_modules],
                    actuators_modules=[move.title for move in actuators_modules])
                # load overshoot if present
                file = filename.name
                path = overshoot_path.joinpath(file)
                if path.is_file():
                    self.set_overshoot_configuration(path)

                self.remote_manager = RemoteManager(
                    actuators=[move.title for move in actuators_modules],
                    detectors=[det.title for det in detector_modules])
                # load remote file if present
                file = filename.name
                path = remote_path.joinpath(file)
                if path.is_file():
                    self.set_remote_configuration(path)

                self.roi_saver = ROISaver(det_modules=detector_modules)
                # load roi saver if present
                path = roi_path.joinpath(file)
                if path.is_file():
                    self.set_roi_configuration(path)

                # connecting to logger
                for mov in actuators_modules:
                    mov.init_signal.connect(self.update_init_tree)
                for det in detector_modules:
                    det.init_signal.connect(self.update_init_tree)

                self.splash_sc.close()
                self.mainwindow.setVisible(True)
                for area in self.dockarea.tempAreas:
                    area.window().setVisible(True)
                if self.pid_window is not None:
                    self.pid_window.show()

                self.load_preset_menu.setEnabled(False)
                self.set_action_enabled('load_preset', False)
                self.set_action_enabled('preset_list', False)
                self.overshoot_menu.setEnabled(True)
                self.roi_menu.setEnabled(True)
                self.remote_menu.setEnabled(True)
                self.extensions_menu.setEnabled(True)
                self.file_menu.setEnabled(True)
                self.settings_menu.setEnabled(True)
                self.update_init_tree()

                self.preset_loaded_signal.emit(True)

            logger.info(f'Preset file: {filename} has been loaded')

        except Exception as e:
            logger.exception(str(e))

    def update_init_tree(self):
        for act in self.actuators_modules:
            name = ''.join(act.title.split())  # remove empty spaces
            if act.title not in [ac.title() for ac in putils.iter_children_params(
                    self.settings.child('actuators'), [])]:

                self.settings.child('actuators').addChild(
                    {'title': act.title, 'name': name, 'type': 'led', 'value': False})
                QtWidgets.QApplication.processEvents()
            self.settings.child('actuators', name).setValue(act.initialized_state)

        for det in self.detector_modules:
            name = ''.join(det.title.split())  # remove empty spaces
            if det.title not in [de.title() for de in putils.iter_children_params(
                    self.settings.child('detectors'), [])]:
                self.settings.child('detectors').addChild(
                    {'title': det.title, 'name': name, 'type': 'led', 'value': False})
                QtWidgets.QApplication.processEvents()
            self.settings.child('detectors', name).setValue(det.initialized_state)

    def do_stuff_from_out_bounds(self, out_of_bounds: bool):

        if out_of_bounds:
            logger.warning(f'Some actuators reached their bounds')
            if self.scan_module is not None:
                logger.warning(f'Stopping the DAQScan for out of bounds')
                self.scan_module.stop_scan()

    def stop_moves_from_overshoot(self, overshoot):
        self.overshoot = overshoot
        self.stop_moves()

    def stop_moves(self, *args, **kwargs):
        """
            Foreach module of the move module object list, stop motion.

            See Also
            --------
            stop_scan,  DAQ_Move_main.daq_move.stop_motion
        """
        if self.scan_module is not None:
            self.scan_module.stop_scan()

        for mod in self.actuators_modules:
            mod.stop_motion()

    def show_log(self):
        import webbrowser
        webbrowser.open(logging.getLogger('pymodaq').handlers[0].baseFilename)

    def show_config(self):
        from pymodaq_gui.utils.widgets.tree_toml import TreeFromToml
        config_tree = TreeFromToml()
        config_tree.show_dialog()

    def setup_docks(self):

        # %% create logger dock
        self.logger_dock = Dock("Logger")
        self.logger_list = QtWidgets.QListWidget()
        self.logger_list.setMinimumWidth(300)

        splitter = QtWidgets.QSplitter(Qt.Vertical)
        splitter.addWidget(self.settings_tree)
        splitter.addWidget(self.logger_list)
        self.logger_dock.addWidget(splitter)

        self.remote_dock = Dock('Remote controls')
        self.dockarea.addDock(self.remote_dock, 'top')
        self.dockarea.addDock(self.logger_dock, 'above', self.remote_dock)
        self.logger_dock.setVisible(True)

        self.remote_dock.setVisible(False)
        self.preset_manager = PresetManager(path=self.preset_path, extra_params=self.extra_params)

    @property
    def menubar(self):
        return self._menubar

    def parameter_tree_changed(self, param, changes):
        """
            Foreach value changed, update :
                * Viewer in case of **DAQ_type** parameter name
                * visibility of button in case of **show_averaging** parameter name
                * visibility of naverage in case of **live_averaging** parameter name
                * scale of axis **else** (in 2D pymodaq type)

            Once done emit the update settings signal to link the commit.


        """

        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':
                pass
            elif change == 'value':
                if param.name() == 'log_level':
                    logger.setLevel(param.value())
            elif change == 'parent':
                pass

    def show_about(self):
        self.splash_sc.setVisible(True)
        self.splash_sc.showMessage(
            f"PyMoDAQ version {get_version('pymodaq')}\n"
            f"Modular Acquisition with Python\n"
            f"Written by Sébastien Weber")

    def check_update(self, show=True):

        try:
            packages = ['pymodaq_utils', 'pymodaq_data', 'pymodaq_gui', 'pymodaq']
            current_versions = [version_mod.parse(get_version(p)) for p in packages]
            available_versions = [version_mod.parse(get_pypi_pymodaq(p)['version']) for p in packages]
            new_versions = np.greater(available_versions, current_versions)
            # Combine package and version information and select only the ones with a newer version available

            
            packages_data = np.array(list(zip(packages, current_versions, available_versions)))[new_versions]

            if len(packages_data) > 0:
                #Create a QDialog window and different graphical components
                dialog = QtWidgets.QDialog()
                dialog.setWindowTitle("Update check")
                
                vlayout = QtWidgets.QVBoxLayout()

                message_label = QLabel("New versions of PyMoDAQ packages available!\nUse your package manager to update.")
                message_label.setAlignment(Qt.AlignCenter)
                

                table = PymodaqUpdateTableWidget()
                table.setRowCount(len(packages_data)) 
                table.setColumnCount(3)
                table.setHorizontalHeaderLabels(["Package", "Current version", "New version"])
                     
                for p in packages_data:
                    table.append_row(p[0], p[1], p[2])


                # The vlayout contains the message, the table and the buttons                
                # and is connected to the dialog window
                vlayout.addWidget(message_label)
                vlayout.addWidget(table)
                dialog.setLayout(vlayout)

                ret = dialog.exec()

            else:
                if show:
                    msgBox = QtWidgets.QMessageBox()
                    msgBox.setWindowTitle("Update check")
                    msgBox.setText("Everything is up to date!")
                    ret = msgBox.exec()
        except Exception as e:
            logger.exception("Error while checking the available PyMoDAQ version")

        return False

    def show_file_attributes(self, type_info='dataset'):
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
        if type_info == 'scan':
            tree.setParameters(self.scan_attributes, showTop=False)
        elif type_info == 'dataset':
            tree.setParameters(self.dataset_attributes, showTop=False)

        vlayout.addWidget(tree)
        dialog.setLayout(vlayout)
        buttonBox = QtWidgets.QDialogButtonBox(parent=dialog)
        buttonBox.addButton('Cancel', buttonBox.RejectRole)
        buttonBox.addButton('Apply', buttonBox.AcceptRole)
        buttonBox.rejected.connect(dialog.reject)
        buttonBox.accepted.connect(dialog.accept)

        vlayout.addWidget(buttonBox)
        dialog.setWindowTitle('Fill in information about this {}'.format(type_info))
        res = dialog.exec()
        return res

    def show_help(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("http://pymodaq.cnrs.fr"))

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


def main():
    from pymodaq_gui.utils.utils import mkQApp

    app = mkQApp('Dashboard')

    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    prog = DashBoard(area)

    win.show()

    app.exec()


if __name__ == '__main__':
    main()

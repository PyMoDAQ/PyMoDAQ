#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import datetime
import subprocess
import pickle
import logging
from pathlib import Path
from importlib import import_module
from packaging import version as version_mod
from pyqtgraph.parametertree import Parameter, ParameterTree
from qtpy import QtGui, QtWidgets, QtCore
from qtpy.QtCore import Qt, QObject, Slot, QThread, Signal, QLocale
from time import perf_counter

from pymodaq.daq_utils.gui_utils import DockArea, Dock, select_file
import pymodaq.daq_utils.gui_utils.layout as layout_mod
from pymodaq.daq_utils.messenger import messagebox
from pymodaq.daq_utils.parameter import utils as putils
import pymodaq.daq_utils.parameter.pymodaq_ptypes as ptypes  # to be placed after importing Parameter
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils.managers.modules_manager import ModulesManager
from pymodaq.daq_utils.daq_utils import get_version
from pymodaq.daq_utils.managers.preset_manager import PresetManager
from pymodaq.daq_utils.managers.overshoot_manager import OvershootManager
from pymodaq.daq_utils.managers.remote_manager import RemoteManager
from pymodaq.daq_utils.managers.roi_manager import ROISaver
from pymodaq.daq_utils.exceptions import DetectorError, ActuatorError
from pymodaq.daq_utils import config as configmod

from pymodaq.daq_move.daq_move_main import DAQ_Move
from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer

from pymodaq.daq_scan import DAQ_Scan
from pymodaq.daq_logger import DAQ_Logger
from pymodaq.pid.pid_controller import DAQ_PID
from pymodaq_plugin_manager.manager import PluginManager
from pymodaq_plugin_manager.validate import get_pypi_pymodaq


logger = utils.set_logger(utils.get_module_name(__file__))

config = configmod.Config()

local_path = configmod.get_set_local_dir()
now = datetime.datetime.now()
preset_path = configmod.get_set_preset_path()
log_path = configmod.get_set_log_path()
layout_path = configmod.get_set_layout_path()
overshoot_path = configmod.get_set_overshoot_path()
roi_path = configmod.get_set_roi_path()
remote_path = configmod.get_set_remote_path()

extensions = utils.get_extensions()


class DashBoard(QObject):
    """
    Main class initializing a DashBoard interface to display det and move modules and logger """
    status_signal = Signal(str)
    preset_loaded_signal = Signal(bool)
    new_preset_created = Signal()

    def __init__(self, dockarea):
        """

        Parameters
        ----------
        parent: (dockarea) instance of the modified pyqtgraph Dockarea (see daq_utils)
        """
        
        super().__init__()
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

        self.dockarea = dockarea
        self.dockarea.dock_signal.connect(self.save_layout_state_auto)
        self.mainwindow = dockarea.parent()
        self.title = ''
        splash_path = Path(__file__).parent.joinpath('splash.png')

        splash = QtGui.QPixmap(str(splash_path))
        self.splash_sc = QtWidgets.QSplashScreen(splash, Qt.WindowStaysOnTopHint)
        self.overshoot_manager = None
        self.preset_manager = None
        self.roi_saver = None

        self.remote_timer = QtCore.QTimer()
        self.remote_manager = None
        self.shortcuts = dict([])
        self.joysticks = dict([])
        self.ispygame_init = False

        self.modules_manager = None

        self.overshoot = False
        self.preset_file = None
        self.actuators_modules = []
        self.detector_modules = []
        self.setupUI()

        logger.info('Dashboard Initialized')

        if config('general', 'check_version'):
            self.check_version(show=False)

    def set_preset_path(self, path):
        self.preset_path = path
        self.set_extra_preset_params(self.extra_params)
        self.create_menu(self.menubar)

    def set_extra_preset_params(self, params, param_options=[]):
        self.extra_params = params
        self.preset_manager = PresetManager(path=self.preset_path, extra_params=params, param_options=param_options)

    @Slot(str)
    def add_status(self, txt):
        """
            Add the QListWisgetItem initialized with txt informations to the User Interface logger_list and to the save_parameters.logger array.

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
        self.scan_module = DAQ_Scan(dockarea=area, dashboard=self)
        self.extensions['DAQ_Scan'] = self.scan_module
        self.scan_module.status_signal.connect(self.add_status)
        win.show()
        return self.scan_module

    def load_log_module(self, win=None):
        if win is None:
            win = QtWidgets.QMainWindow()
        area = DockArea()
        win.setCentralWidget(area)
        self.log_module = DAQ_Logger(dockarea=area, dashboard=self)
        self.extensions['DAQ_Logger'] = self.log_module
        self.log_module.status_signal.connect(self.add_status)
        win.show()
        return self.log_module

    def load_pid_module(self, win=None):
        if win is None:
            self.pid_window = QtWidgets.QMainWindow()
        else:
            self.pid_window = win

        self.pid_window.showFullScreen()
        dockarea = DockArea()
        self.pid_window.setCentralWidget(dockarea)
        self.pid_window.setWindowTitle('PID extension module')
        self.pid_module = DAQ_PID(dockarea=dockarea)
        self.pid_module.set_module_manager(self.detector_modules, self.actuators_modules)
        self.extensions['DAQ_PID'] = self.pid_module
        self.pid_window.show()
        return self.pid_module

    def load_extensions_module(self, ext):
        self.extension_windows.append(QtWidgets.QMainWindow())
        area = DockArea()
        self.extension_windows[-1].setCentralWidget(area)
        self.extension_windows[-1].resize(1000, 500)
        self.extension_windows[-1].setWindowTitle(ext['name'])
        pkg = ext['module']
        module = import_module(f'{pkg.__name__}.{pkg.module_name}', pkg)
        klass = getattr(module, pkg.klass_name)
        self.extensions[pkg.klass_name] = klass(dockarea=area, dashboard=self)
        self.extension_windows[-1].show()
        return self.extensions[pkg.klass_name]

    def create_menu(self, menubar):
        """
            Create the menubar object looking like :
        """
        menubar.clear()

        # %% create Settings menu
        self.file_menu = menubar.addMenu('File')
        self.file_menu.addAction('Show log file', self.show_log)
        self.file_menu.addAction('Show configuration file', self.show_config)
        self.file_menu.addSeparator()
        quit_action = self.file_menu.addAction('Quit')
        restart_action = self.file_menu.addAction('Restart')
        quit_action.triggered.connect(self.quit_fun)
        restart_action.triggered.connect(self.restart_fun)

        self.settings_menu = menubar.addMenu('Settings')
        docked_menu = self.settings_menu.addMenu('Docked windows')
        action_load = docked_menu.addAction('Load Layout')
        action_save = docked_menu.addAction('Save Layout')

        action_load.triggered.connect(self.load_layout_state)
        action_save.triggered.connect(self.save_layout_state)

        docked_menu.addSeparator()
        action_show_log = docked_menu.addAction('Show/hide log window')
        action_show_log.setCheckable(True)
        action_show_log.toggled.connect(self.logger_dock.setVisible)

        self.preset_menu = menubar.addMenu('Preset Modes')
        action_new_preset = self.preset_menu.addAction('New Preset')
        # action.triggered.connect(lambda: self.show_file_attributes(type_info='managers'))
        action_new_preset.triggered.connect(self.create_preset)
        action_modify_preset = self.preset_menu.addAction('Modify Preset')
        action_modify_preset.triggered.connect(self.modify_preset)
        self.preset_menu.addSeparator()
        self.load_preset = self.preset_menu.addMenu('Load presets')

        slots = dict([])
        for ind_file, file in enumerate(self.preset_path.iterdir()):
            if file.suffix == '.xml':
                filestem = file.stem
                slots[filestem] = self.load_preset.addAction(filestem)
                slots[filestem].triggered.connect(
                    self.create_menu_slot(self.preset_path.joinpath(file)))

        self.overshoot_menu = menubar.addMenu('Overshoot Modes')
        action_new_overshoot = self.overshoot_menu.addAction('New Overshoot')
        # action.triggered.connect(lambda: self.show_file_attributes(type_info='managers'))
        action_new_overshoot.triggered.connect(self.create_overshoot)
        action_modify_overshoot = self.overshoot_menu.addAction('Modify Overshoot')
        action_modify_overshoot.triggered.connect(self.modify_overshoot)
        self.overshoot_menu.addSeparator()
        load_overshoot = self.overshoot_menu.addMenu('Load Overshoots')

        slots_over = dict([])
        for ind_file, file in enumerate(configmod.get_set_overshoot_path().iterdir()):
            if file.suffix == '.xml':
                filestem = file.stem
                slots_over[filestem] = load_overshoot.addAction(filestem)
                slots_over[filestem].triggered.connect(
                    self.create_menu_slot_over(configmod.get_set_overshoot_path().joinpath(file)))

        self.roi_menu = menubar.addMenu('ROI Modes')
        action_new_roi = self.roi_menu.addAction('Save Current ROIs as a file')
        action_new_roi.triggered.connect(self.create_roi_file)
        action_modify_roi = self.roi_menu.addAction('Modify roi config')
        action_modify_roi.triggered.connect(self.modify_roi)
        self.roi_menu.addSeparator()
        load_roi = self.roi_menu.addMenu('Load roi configs')

        slots = dict([])
        for ind_file, file in enumerate(configmod.get_set_roi_path().iterdir()):
            if file.suffix == '.xml':
                filestem = file.stem
                slots[filestem] = load_roi.addAction(filestem)
                slots[filestem].triggered.connect(
                    self.create_menu_slot_roi(configmod.get_set_roi_path().joinpath(file)))

        self.remote_menu = menubar.addMenu('Remote/Shortcuts Control')
        self.remote_menu.addAction('New remote config.', self.create_remote)
        self.remote_menu.addAction('Modify remote config.', self.modify_remote)
        self.remote_menu.addSeparator()
        load_remote = self.remote_menu.addMenu('Load remote config.')

        slots = dict([])
        for ind_file, file in enumerate(configmod.get_set_remote_path().iterdir()):
            if file.suffix == '.xml':
                filestem = file.stem
                slots[filestem] = load_remote.addAction(filestem)
                slots[filestem].triggered.connect(
                    self.create_menu_slot_remote(configmod.get_set_remote_path().joinpath(file)))

        # actions menu
        self.actions_menu = menubar.addMenu('Extensions')
        action_scan = self.actions_menu.addAction('Do Scans')
        action_scan.triggered.connect(lambda: self.load_scan_module())
        action_log = self.actions_menu.addAction('Log data')
        action_log.triggered.connect(lambda: self.load_log_module())
        action_pid = self.actions_menu.addAction('PID module')
        action_pid.triggered.connect(lambda: self.load_pid_module())

        extensions_actions = []
        for ext in extensions:
            extensions_actions.append(self.actions_menu.addAction(ext['name']))
            extensions_actions[-1].triggered.connect(self.create_menu_slot_ext(ext))


        # help menu
        help_menu = menubar.addMenu('?')
        action_about = help_menu.addAction('About')
        action_about.triggered.connect(self.show_about)
        action_help = help_menu.addAction('Help')
        action_help.triggered.connect(self.show_help)
        action_help.setShortcut(QtGui.QKeySequence('F1'))

        help_menu.addSeparator()
        action_update = help_menu.addAction('Check Version')
        action_update.triggered.connect(lambda: self.check_version(True))

        action_plugin_manager = help_menu.addAction('Plugin Manager')
        action_plugin_manager.triggered.connect(self.start_plugin_manager)

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
                self.create_menu(self.menubar)

        except Exception as e:
            logger.exception(str(e))

    def create_remote(self):
        try:
            if self.preset_file is not None:
                self.remote_manager.set_new_remote(self.preset_file.stem)
                self.create_menu(self.menubar)

        except Exception as e:
            logger.exception(str(e))

    def create_overshoot(self):
        try:
            if self.preset_file is not None:
                self.overshoot_manager.set_new_overshoot(self.preset_file.stem)
                self.create_menu(self.menubar)
        except Exception as e:
            logger.exception(str(e))

    def create_preset(self):
        try:
            self.preset_manager.set_new_preset()
            self.create_menu(self.menubar)
            self.new_preset_created.emit()
        except Exception as e:
            logger.exception(str(e))

    def modify_remote(self):
        try:
            path = select_file(start_path=configmod.get_set_remote_path(), save=False, ext='xml')
            if path != '':
                self.remote_manager.set_file_remote(path)

            else:  # cancel
                pass
        except Exception as e:
            logger.exception(str(e))

    def modify_overshoot(self):
        try:
            path = select_file(start_path=configmod.get_set_overshoot_path(), save=False, ext='xml')
            if path != '':
                self.overshoot_manager.set_file_overshoot(path)

            else:  # cancel
                pass
        except Exception as e:
            logger.exception(str(e))

    def modify_roi(self):
        try:
            path = select_file(start_path=configmod.get_set_roi_path(), save=False, ext='xml')
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
                        mssg.setText('You have to restart the application to take the modifications into account!\n\n'
                                     'The related files: ROI, Layout, Overshoot and Remote will be deleted'
                                     ' if existing!\n\n'
                                     'Quitting the application...')
                        mssg.exec()
                        self.restart_fun()

            else:  # cancel
                pass
        except Exception as e:
            logger.exception(str(e))

    def remove_preset_related_files(self, name):
        configmod.get_set_roi_path().joinpath(name).unlink(missing_ok=True)
        configmod.get_set_layout_path().joinpath(name).unlink(missing_ok=True)
        configmod.get_set_overshoot_path().joinpath(name).unlink(missing_ok=True)
        configmod.get_set_remote_path().joinpath(name).unlink(missing_ok=True)

    def quit_fun(self):
        """
            Quit the current instance of DAQ_scan and close on cascade move and detector modules.

            See Also
            --------
            quit_fun
        """
        try:
            self.remote_timer.stop()

            for mov in self.actuators_modules:
                mov.init_signal.disconnect(self.update_init_tree)
            for det in self.detector_modules:
                det.init_signal.disconnect(self.update_init_tree)

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
            mssg.setText('You have to restart the application to take the modifications into account!')
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

    def add_move(self, plug_name, plug_settings, plug_type, move_docks, move_forms, actuators_modules):
        """Add an actuator module to the dashboard

        Parameters
        ----------
        plug_name : str
            Title of the actuator module
        plug_settings : GroupParameter
            Settings of the actuator module
        plug_type : str
            Plugin type (i.e. "SmarActMCS")
        move_docks : list of Dock
            List of the actuators pyqtgraph docks (floating subwindows in the dashboard main window)
        move_forms : list of Ui_Form
            List of forms that define the graphical aspects of the UI of the modules
        actuators_modules : list of DAQ_Move objects
            The actuator modules of the dashboard

        """
        move_docks.append(Dock(plug_name, size=(150, 250)))
        if len(move_docks) == 1:
            self.dockarea.addDock(move_docks[-1], 'right', self.logger_dock)
        else:
            self.dockarea.addDock(move_docks[-1], 'above', move_docks[-2])
        move_forms.append(QtWidgets.QWidget())
        mov_mod_tmp = DAQ_Move(move_forms[-1], plug_name)

        mov_mod_tmp.ui.Stage_type_combo.setCurrentText(plug_type)
        mov_mod_tmp.ui.Quit_pb.setEnabled(False)
        QtWidgets.QApplication.processEvents()

        if plug_settings is not None:
            try:
                utils.set_param_from_param(mov_mod_tmp.settings, plug_settings)
            except KeyError as e:
                mssg = f'Could not set this setting: {str(e)}\n' \
                       f'The Preset is no more compatible with the plugin {plug_type}'
                logger.warning(mssg)
                self.splash_sc.showMessage(mssg, color=Qt.white)
        QtWidgets.QApplication.processEvents()

        mov_mod_tmp.bounds_signal[bool].connect(self.stop_moves)
        move_docks[-1].addWidget(move_forms[-1])
        actuators_modules.append(mov_mod_tmp)

    def set_file_preset(self, filename):
        """Load a preset file.

        Return the lists of actuator and detector modules defined in the preset file.

        Parameters
        ----------
        filename : str
            The full name of the xml file to be converted/treated

        Returns
        -------
        actuators_modules, detector_modules : tuple list of DAQ_Move, list of DAQ_Viewer
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

            # Sort plugins by IDs and within the same IDs by Master and Slave status
            plugins = []
            plugins += [{'type': 'move', 'value': child} for child in
                        self.preset_manager.preset_params.child('Moves').children()]
            plugins += [{'type': 'det', 'value': child} for child in
                        self.preset_manager.preset_params.child('Detectors').children()]

            for plug in plugins:
                plug['ID'] = plug['value'].child('params', 'main_settings', 'controller_ID').value()
                if plug["type"] == 'det':
                    plug['status'] = plug['value'].child('params', 'detector_settings', 'controller_status').value()
                else:
                    if 'multiaxes' in [child.name() for child in plug['value'].child('params',
                                                                                     'move_settings').children()]:
                        plug['status'] = plug['value'].child('params', 'move_settings',
                                                             'multiaxes', 'multi_status').value()
                    else:
                        plug['status'] = 'Master'

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
                    self.splash_sc.showMessage('Loading {:s} module: {:s}'.format(plugin['type'], plug_name),
                                               color=Qt.white)

                    if plugin['type'] == 'move':
                        try:
                            plug_type = plug_settings.child('main_settings', 'move_type').value()
                            self.add_move(plug_name, plug_settings, plug_type, move_docks, move_forms, actuators_modules)

                            if ind_plugin == 0:  # should be a master type plugin
                                if plugin['status'] != "Master":
                                    logger.error('error in the master/slave type for plugin {}'.format(plug_name))
                                if plug_init:
                                    actuators_modules[-1].ui.IniStage_pb.click()
                                    QtWidgets.QApplication.processEvents()
                                    self.poll_init(actuators_modules[-1])
                                    QtWidgets.QApplication.processEvents()
                                    master_controller = actuators_modules[-1].controller
                            else:
                                if plugin['status'] != "Slave":
                                    logger.error('error in the master/slave type for plugin {}'.format(plug_name))
                                if plug_init:
                                    actuators_modules[-1].controller = master_controller
                                    actuators_modules[-1].ui.IniStage_pb.click()
                                    QtWidgets.QApplication.processEvents()
                                    self.poll_init(actuators_modules[-1])
                                    QtWidgets.QApplication.processEvents()
                        except ActuatorError as e:
                            self.splash_sc.close()
                            messagebox(text=f'{str(e)}\nQuitting the application...', title='Incompatibility')
                            logger.exception(str(e))
                            self.quit_fun()
                            return
                    else:
                        try:
                            ind_det += 1
                            plug_type = plug_settings.child('main_settings', 'DAQ_type').value()
                            plug_subtype = plug_settings.child('main_settings', 'detector_type').value()

                            det_docks_settings.append(Dock(plug_name + " settings", size=(150, 250)))
                            det_docks_viewer.append(Dock(plug_name + " viewer", size=(350, 350)))
                            if ind_det == 0:
                                self.logger_dock.area.addDock(det_docks_settings[-1],
                                                              'bottom')  # dockarea of the logger dock
                            else:
                                self.dockarea.addDock(det_docks_settings[-1], 'right', det_docks_viewer[-2])
                            self.dockarea.addDock(det_docks_viewer[-1], 'right', det_docks_settings[-1])
                            det_mod_tmp = DAQ_Viewer(self.dockarea, dock_settings=det_docks_settings[-1],
                                                     dock_viewer=det_docks_viewer[-1], title=plug_name,
                                                     DAQ_type=plug_type, parent_scan=self)
                            det_mod_tmp.detector = plug_subtype
                            det_mod_tmp.ui.Quit_pb.setEnabled(False)
                            detector_modules.append(det_mod_tmp)

                            try:
                                utils.set_param_from_param(det_mod_tmp.settings, plug_settings)
                            except KeyError as e:
                                mssg = f'Could not set this setting: {str(e)}\n'\
                                       f'The Preset is no more compatible with the plugin {plug_subtype}'
                                logger.warning(mssg)
                                self.splash_sc.showMessage(mssg, color=Qt.white)

                            QtWidgets.QApplication.processEvents()

                            try:
                                if ind_plugin == 0:  # should be a master type plugin
                                    if plugin['status'] != "Master":
                                        logger.error('error in the master/slave type for plugin {}'.format(plug_name))
                                    if plug_init:
                                        detector_modules[-1].ui.IniDet_pb.click()
                                        QtWidgets.QApplication.processEvents()
                                        self.poll_init(detector_modules[-1])
                                        QtWidgets.QApplication.processEvents()
                                        master_controller = detector_modules[-1].controller
                                else:
                                    if plugin['status'] != "Slave":
                                        logger.error('error in the master/slave type for plugin {}'.format(plug_name))
                                    if plug_init:
                                        detector_modules[-1].controller = master_controller
                                        detector_modules[-1].ui.IniDet_pb.click()
                                        QtWidgets.QApplication.processEvents()
                                        self.poll_init(detector_modules[-1])
                                        QtWidgets.QApplication.processEvents()
                            except Exception as e:
                                logger.exception(str(e))

                            detector_modules[-1].settings.child('main_settings', 'overshoot').show()
                            detector_modules[-1].overshoot_signal[bool].connect(self.stop_moves)
                        except DetectorError as e:
                            self.splash_sc.close()
                            messagebox(text=f'{str(e)}\nQuitting the application...', title='Incompatibility')
                            logger.exception(str(e))
                            self.quit_fun()
                            return
            QtWidgets.QApplication.processEvents()
            # restore dock state if saved

            self.title = self.preset_file.stem
            path = layout_path.joinpath(self.title + '.dock')
            if path.is_file():
                self.load_layout_state(path)

            self.mainwindow.setWindowTitle(f'PyMoDAQ Dashboard: {self.title}')
            # if self.pid_module is not None:
            #     self.pid_module.set_module_manager(detector_modules, actuators_modules)
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
                    QtWidgets.QShortcut(QtGui.QKeySequence(remote_action['action_dict']['shortcut']), self.dockarea)
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

        # # Specifi action for axis to get their values even if it doesn't change (in which case it would'nt trigger events)
        for action_dict in self.joysticks.values():
            if action_dict['activated'] and action_dict['actionner_type'].lower() == 'axis':
                if action_dict['module_type'] == 'act':
                    joy = utils.find_dict_in_list_from_key_val(self.joysticks_obj, 'id', action_dict['joystickID'])
                    val = joy['obj'].get_axis(action_dict['actionnerID'])
                    if abs(val) > 1e-4:
                        module = self.modules_manager.get_mod_from_name(action_dict['module_name'],
                                                                        mod=action_dict['module_type'])
                        action = getattr(module, action_dict['action'])
                        if module.move_done_bool:
                            action(val * 1 * module.settings.child('move_settings', 'epsilon').value())

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
                        module = self.modules_manager.get_mod_from_name(action_dict['module_name'],
                                                                        mod=action_dict['module_type'])
                        if action_dict['module_type'] == 'det':
                            action = getattr(module, action_dict['action'])
                        else:
                            action = getattr(module, action_dict['action'])

                        if action_dict['joystickID'] == selection['joy']:
                            if action_dict['actionner_type'].lower() == 'button' and 'button' in selection:
                                if action_dict['actionnerID'] == selection['button']:
                                    action()
                            elif action_dict['actionner_type'].lower() == 'hat' and 'hat' in selection:
                                if action_dict['actionnerID'] == selection['hat']:
                                    action(selection['value'])

        QtWidgets.QApplication.processEvents()

    def activate_shortcut(self, shortcut, action=None, activate=True):
        """
        action = dict(shortcut=action.child(('shortcut')).value(), activated=True, name=f'action{ind:02d}',
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
        module = self.modules_manager.get_mod_from_name(action['module_name'], mod=action['module_type'])
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

                det_titles = [det.title for det in self.detector_modules]
                move_titles = [move.title for move in self.actuators_modules]

                for det_param in self.overshoot_manager.overshoot_params.child(('Detectors')).children():
                    if det_param.child(('trig_overshoot')).value():
                        det_index = det_titles.index(det_param.opts['title'])
                        det_module = self.detector_modules[det_index]
                        det_module.settings.child('main_settings', 'overshoot', 'stop_overshoot').setValue(True)
                        det_module.settings.child('main_settings', 'overshoot', 'overshoot_value').setValue(
                            det_param.child(('overshoot_value')).value())
                        for move_param in det_param.child(('params')).children():
                            if move_param.child(('move_overshoot')).value():
                                move_index = move_titles.index(move_param.opts['title'])
                                move_module = self.actuators_modules[move_index]
                                det_module.overshoot_signal.connect(
                                    self.create_overshoot_fun(move_module, move_param.child(('position')).value()))

        except Exception as e:
            logger.exception(str(e))

    def create_overshoot_fun(self, move_module, position):
        return lambda: move_module.move_Abs(position)

    @property
    def move_modules(self):
        """
        for back compatibility
        """
        return self.actuators_modules

    def set_preset_mode(self, filename):
        """Load a preset file.

        This method is called from the dashboard UI main menu: Preset modes > Load preset > <preset name>

        Parameters
        ----------
        filename : str
            Complete path of the preset file

        See Also
        --------
        set_file_preset, add_status, update_status

        """
        try:
            if not isinstance(filename, Path):
                filename = Path(filename)
            self.mainwindow.setVisible(False)
            for area in self.dockarea.tempAreas:
                area.window().setVisible(False)

            self.splash_sc.show()
            QtWidgets.QApplication.processEvents()
            self.splash_sc.raise_()
            self.splash_sc.showMessage('Loading Modules, please wait', color=Qt.white)
            QtWidgets.QApplication.processEvents()
            self.clear_move_det_controllers()
            QtWidgets.QApplication.processEvents()

            logger.info(f'Loading Preset file: {filename}')
            actuators_modules, detector_modules = self.set_file_preset(filename)

            if not (not actuators_modules and not detector_modules):
                self.update_status('Preset mode ({}) has been loaded'.format(filename.name), log_type='log')
                self.settings.child('loaded_files', 'preset_file').setValue(filename.name)
                self.actuators_modules = actuators_modules
                self.detector_modules = detector_modules

                self.modules_manager = ModulesManager(self.detector_modules, self.actuators_modules)
                self.overshoot_manager = OvershootManager(det_modules=[det.title for det in detector_modules],
                                                          actuators_modules=[move.title for move in actuators_modules])
                # load overshoot if present
                file = filename.name
                path = overshoot_path.joinpath(file)
                if path.is_file():
                    self.set_overshoot_configuration(path)

                self.remote_manager = RemoteManager(actuators=[move.title for move in actuators_modules],
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
                    mov.status_signal[str].connect(self.add_status)
                    mov.init_signal.connect(self.update_init_tree)
                for det in detector_modules:
                    det.status_signal[str].connect(self.add_status)
                    det.init_signal.connect(self.update_init_tree)

                self.splash_sc.close()
                self.mainwindow.setVisible(True)
                for area in self.dockarea.tempAreas:
                    area.window().setVisible(True)
                if self.pid_window is not None:
                    self.pid_window.show()

                self.load_preset.setEnabled(False)
                self.overshoot_menu.setEnabled(True)
                self.roi_menu.setEnabled(True)
                self.remote_menu.setEnabled(True)
                self.actions_menu.setEnabled(True)
                self.file_menu.setEnabled(True)
                self.settings_menu.setEnabled(True)
                self.update_init_tree()

            # If the preset is configured to use the pid extension
            if self.preset_manager.preset_params.child('use_pid').value():
                self.load_pid_module()

                self.pid_module.settings.child('models', 'model_class').setValue(
                    self.preset_manager.preset_params.child('pid_models').value())
                QtWidgets.QApplication.processEvents()
                self.pid_module.ini_model()

                QtWidgets.QApplication.processEvents()

                for child in putils.iter_children_params(self.preset_manager.preset_params.child('model_settings'),
                                                         []):
                    preset_path = self.preset_manager.preset_params.child('model_settings').childPath(child)
                    path = ['models', 'model_params']
                    path.extend(preset_path)
                    self.pid_module.settings.child(*path).setValue(child.value())

                model_class = utils.get_models(
                    self.preset_manager.preset_params.child('pid_models').value())['class']

                # Add a mock actuator module that will control each setpoint defined in the model.
                for setp in model_class.setpoints_names:
                    self.add_move(setp, None, 'PID', [], [], actuators_modules)
                    actuators_modules[-1].controller = dict(
                        curr_point=self.pid_module.curr_points_signal,
                        setpoint=self.pid_module.setpoints_signal,
                        emit_curr_points=self.pid_module.emit_curr_points_sig)
                    actuators_modules[-1].ui.IniStage_pb.click()
                    QtWidgets.QApplication.processEvents()
                    self.poll_init(actuators_modules[-1])
                    QtWidgets.QApplication.processEvents()

            self.preset_loaded_signal.emit(True)
            logger.info(f'Preset file: {filename} has been loaded')

        except Exception as e:
            logger.error(f'Preset file: {filename} has not been loaded properly')
            logger.exception(str(e))

    def update_init_tree(self):
        for act in self.actuators_modules:
            name = ''.join(act.title.split())  # remove empty spaces
            if act.title not in [ac.title() for ac in putils.iter_children_params(self.settings.child(('actuators')), [])]:

                self.settings.child(('actuators')).addChild(
                    {'title': act.title, 'name': name, 'type': 'led', 'value': False})
                QtWidgets.QApplication.processEvents()
            self.settings.child('actuators', name).setValue(act.initialized_state)

        for det in self.detector_modules:
            name = ''.join(det.title.split())  # remove empty spaces
            if det.title not in [de.title() for de in putils.iter_children_params(self.settings.child(('detectors')), [])]:
                self.settings.child(('detectors')).addChild(
                    {'title': det.title, 'name': name, 'type': 'led', 'value': False})
                QtWidgets.QApplication.processEvents()
            self.settings.child('detectors', name).setValue(det.initialized_state)

    Slot(bool)
    def stop_moves(self, overshoot):
        """
            Foreach module of the move module object list, stop motion.

            See Also
            --------
            stop_scan,  DAQ_Move_main.daq_move.stop_Motion
        """
        self.overshoot = overshoot
        if self.scan_module is not None:
            self.scan_module.stop_scan()

        for mod in self.actuators_modules:
            mod.stop_Motion()

    def show_log(self):
        import webbrowser
        webbrowser.open(logging.getLogger('pymodaq').handlers[0].baseFilename)

    def show_config(self):
        config_tree = configmod.TreeFromToml()
        config_tree.show_dialog()

    def setupUI(self):

        # %% create logger dock
        self.logger_dock = Dock("Logger")
        self.logger_list = QtWidgets.QListWidget()
        self.logger_list.setMinimumWidth(300)
        self.init_tree = ParameterTree()
        self.init_tree.setMinimumWidth(300)
        splitter = QtWidgets.QSplitter(Qt.Vertical)
        splitter.addWidget(self.init_tree)
        splitter.addWidget(self.logger_list)
        self.logger_dock.addWidget(splitter)

        self.settings = Parameter.create(name='init_settings', type='group', children=[
            {'title': 'Log level', 'name': 'log_level', 'type': 'list', 'value': config('general', 'debug_level'),
             'limits': config('general', 'debug_levels')},

            {'title': 'Loaded presets', 'name': 'loaded_files', 'type': 'group', 'children': [
                {'title': 'Preset file', 'name': 'preset_file', 'type': 'str', 'value': '', 'readonly': True},
                {'title': 'Overshoot file', 'name': 'overshoot_file', 'type': 'str', 'value': '', 'readonly': True},
                {'title': 'Layout file', 'name': 'layout_file', 'type': 'str', 'value': '', 'readonly': True},
                {'title': 'ROI file', 'name': 'roi_file', 'type': 'str', 'value': '', 'readonly': True},
                {'title': 'Remote file', 'name': 'remote_file', 'type': 'str', 'value': '', 'readonly': True},
            ]},
            {'title': 'Actuators Init.', 'name': 'actuators', 'type': 'group', 'children': []},
            {'title': 'Detectors Init.', 'name': 'detectors', 'type': 'group', 'children': []},
        ])
        self.init_tree.setParameters(self.settings, showTop=False)
        self.remote_dock = Dock('Remote controls')
        self.dockarea.addDock(self.remote_dock, 'top')
        self.dockarea.addDock(self.logger_dock, 'above', self.remote_dock)
        self.logger_dock.setVisible(True)

        self.remote_dock.setVisible(False)
        self.preset_manager = PresetManager(path=self.preset_path, extra_params=self.extra_params)

        # creating the menubar
        self.menubar = self.mainwindow.menuBar()
        self.create_menu(self.menubar)
        self.overshoot_menu.setEnabled(False)
        self.roi_menu.setEnabled(False)
        self.remote_menu.setEnabled(False)
        self.actions_menu.setEnabled(False)
        #        connecting
        self.status_signal[str].connect(self.add_status)

        self.file_menu.setEnabled(True)
        # self.actions_menu.setEnabled(True)
        self.settings_menu.setEnabled(True)
        self.preset_menu.setEnabled(True)
        self.mainwindow.setVisible(True)

    def parameter_tree_changed(self, param, changes):
        """
            Foreach value changed, update :
                * Viewer in case of **DAQ_type** parameter name
                * visibility of button in case of **show_averaging** parameter name
                * visibility of naverage in case of **live_averaging** parameter name
                * scale of axis **else** (in 2D pymodaq type)

            Once done emit the update settings signal to link the commit.

            =============== =================================== ================================================================
            **Parameters**    **Type**                           **Description**
            *param*           instance of ppyqtgraph parameter   the parameter to be checked
            *changes*         tuple list                         Contain the (param,changes,info) list listing the changes made
            =============== =================================== ================================================================

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
            "PyMoDAQ version {:}\nModular Acquisition with Python\nWritten by Sébastien Weber".format(get_version()),
            QtCore.Qt.AlignRight, QtCore.Qt.white)

    def check_version(self, show=True):
        try:
            current_version = version_mod.parse(get_version())
            available_version = [version_mod.parse(ver) for ver in get_pypi_pymodaq('pymodaq')['versions']]
            msgBox = QtWidgets.QMessageBox()
            if max(available_version) > current_version:
                msgBox.setText(f"A new version of PyMoDAQ is available, {str(max(available_version))}!")
                msgBox.setInformativeText("Do you want to install it?")
                msgBox.setStandardButtons(msgBox.Ok | msgBox.Cancel)
                msgBox.setDefaultButton(msgBox.Ok)

                ret = msgBox.exec()

                if ret == msgBox.Ok:
                    command = [sys.executable, '-m', 'pip', 'install', f'pymodaq=={str(max(available_version))}']
                    subprocess.Popen(command)

                    self.restart_fun()
            else:
                if show:
                    msgBox.setText(f"Your version of PyMoDAQ, {str(current_version)}, is up to date!")
                    ret = msgBox.exec()
        except Exception as e:
            logger.exception("Error while checking the available PyMoDAQ version")

    def show_file_attributes(self, type_info='dataset'):
        """
            Switch the type_info value.

            In case of :
                * *scan* : Set parameters showing top false
                * *dataset* : Set parameters showing top false
                * *managers* : Set parameters showing top false. Add the save/cancel buttons to the accept/reject dialog (to save managers parameters in a xml file).

            Finally, in case of accepted managers type info, save the managers parameters in a xml file.

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


def main(init_qt=True):
    if init_qt:  # used for the test suite
        app = QtWidgets.QApplication(sys.argv)
        if config('style', 'darkstyle'):
            import qdarkstyle
            app.setStyleSheet(qdarkstyle.load_stylesheet(qdarkstyle.DarkPalette))

    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    # win.setVisible(False)
    prog = DashBoard(area)
    if init_qt:
        sys.exit(app.exec_())
    return prog, win


if __name__ == '__main__':
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Automated scanning module functionalities for PyMoDAQ

Contains all objects related to the DAQScan module, to do automated scans, saving data...
"""

from collections import OrderedDict
from typing import TYPE_CHECKING, Union

from pymodaq.control_modules.daq_viewer_ui.ui_base import ActionIconNames
from pymodaq.utils.h5modules.module_saving import LoggerSaver
from pymodaq_gui.managers.runner_thread_manager import WorkerThreadManager
from pymodaq_gui.messenger import messagebox

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.utils.dock import Dock, DockArea
from pymodaq_utils.config import GlobalConfig as Config
from pymodaq_gui.parameter import ioxml

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import QObject, Slot, QThread, Signal, Qt

from pymodaq_gui.utils.widgets import QLED


from pymodaq.extensions.daq_logger.h5logging import H5Logger
from pymodaq.utils.managers.modules.modules_manager import ModulesManager
from pymodaq.utils.data import DataActuator, DataToExport
from pymodaq.utils.custom_ext import CustomExt
from pymodaq_gui.utils.enums import MenuToolbarNames

from pymodaq_gui.utils.widgets import QSpinBox_ro

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard


config = Config()
logger = set_logger(get_module_name(__file__))


class LoggerStatusBarManager:
    def __init__(self, logger: 'DAQLogger'):
        self.logger = logger

        self._start_log_time: QtWidgets.QDateTimeEdit = None
        self._logging_state: QLED = None
        self._n_saved_sb: QSpinBox_ro = None

    @property
    def log_time(self) -> QtCore.QDateTime:
        return self._start_log_time.dateTime()

    @log_time.setter
    def log_time(self, date_time: QtCore.QDateTime):
        self._start_log_time.setDateTime(date_time)

    @property
    def is_logging(self) -> bool:
        return self._logging_state.get_state()

    @is_logging.setter
    def is_logging(self, is_logging: bool):
        self._logging_state.set_as(is_logging)

    @property
    def n_saved(self) -> bool:
        return self._n_saved_sb.value()

    @n_saved.setter
    def n_saved(self, n_saved: bool):
        self._n_saved_sb.setValue(n_saved)

    @property
    def statusbar(self):
        return self.logger.statusbar

    def set_permanent_status(self, status: str):
        self.logger.set_permanent_status(status)

    def create_permanent_widgets(self):
        self._start_log_time = QtWidgets.QDateTimeEdit()
        self._start_log_time.setReadOnly(True)
        self._start_log_time.setToolTip('Logging started at:')
        self.statusbar.addPermanentWidget(self._start_log_time)

        self._logging_state = QLED()
        self._logging_state.setToolTip('logging status: green (running), red (idle)')
        self._logging_state.clickable = False
        self.statusbar.addPermanentWidget(self._logging_state)

        self._n_saved_sb = QSpinBox_ro()
        self._n_saved_sb.setToolTip('Total number of saved data')
        self.statusbar.addPermanentWidget(self._n_saved_sb)


class DAQLogger(CustomExt):
    """
    Main class initializing a DAQ_Logger module
    """
    show_h5file_statusbar_widgets = True
    icon_name = 'home_storage'
    params = [
        {'title': 'Worker:', 'name': 'worker', 'type': 'group', 'children': [
            {'title': 'Worker Running:', 'name': 'worker_running', 'type': 'led', 'value': False, 'readonly': True},
            {'title': 'Worker tasks:', 'name': 'worker_tasks', 'type': 'int', 'value': 0, 'readonly': True},
        ]},
    ]

    def __init__(self, dockarea: DockArea = None,
                 dashboard: 'DashBoard' = None,
                 ):
        """
        """

        super().__init__(dockarea,
                         dashboard,
                         add_toolbar_break=False)

        self.status_manager = LoggerStatusBarManager(self)
        self._module_and_data_saver = LoggerSaver(self)
        self.logging = Logging(self)

        self.setup_ui()

    def do_things_after_experiment_set(self, experiment_name: str, show_dashboard: bool = None):
        self.enable_start_stop(True)
        super().do_things_after_experiment_set(experiment_name, show_dashboard)

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        """
        """
        self.add_toolbar(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), self.mainwindow,
                         toolbar=self.h5_manager.toolbar, add_break=False)
        self.add_menu(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), parent_menu=menubar)
        self.add_menu(MenuToolbarNames.TOOLS, MenuToolbarNames.TOOLS.capitalize(), parent_menu=menubar)
        self.add_menu('actions', 'Actions', parent_menu=menubar)


        self.create_dashboard_toolbar(add_break=False)

    def setup_docks_and_widgets(self):
        logger.debug('setting docks')
        self.docks['detectors'] = Dock("Detectors")
        splitter = QtWidgets.QSplitter(Qt.Orientation.Vertical)
        self.docks['detectors'].addWidget(splitter)
        splitter.addWidget(self.settings_tree)
        splitter.addWidget(self.modules_manager.settings_tree)
        self.dockarea.addDock(self.docks['detectors'])

        self.docks['logger_settings'] = Dock("Logger Settings")
        self.dockarea.addDock(self.docks['logger_settings'], 'right', self.docks['detectors'])
        self.docks['logger_settings'].setVisible(False)
        self.docks['logger_settings'].addWidget(self.settings_tree)
        self.docks['logger_settings'].addWidget(self.h5_manager.h5saver.settings_tree)

        self.populate_status_bar()

    def populate_status_bar(self):
        super().populate_status_bar()
        self.status_manager.create_permanent_widgets()
        self.status_manager.set_permanent_status('Initializing')

    def setup_actions(self):
        '''
        subclass method from ActionManager
        '''
        logger.debug('setting actions')
        self.add_action('start', 'Start Logging', 'motion_play', "Start the Logging",
                        menu='actions', icon_color=self.get_theme().green)
        self.add_action('stop', 'Stop Logging', 'stop_circle', "Stop the Logging",
                        menu='actions', icon_color=self.get_theme().red)
        self.add_action('pause', 'Pause Logging', 'pause_circle', "Pause/resume the Logging",
                        checkable=True, menu='actions',
                        icon_checked_color=self.get_theme().orange)

        self.toolbar.addSeparator()
        self.add_action('grab_all', 'Grab All', ActionIconNames.GRAB,
                        "Grab/Stop all selected detectors's data and actuators's value",
                        checkable=True,
                        icon_checked=ActionIconNames.GRAB_STOP,
                        icon_checked_color=self.get_theme().green)
        logger.debug('actions set')

        self.enable_start_stop(False)

    def enable_start_stop(self, enable=True):
        """If True enable main buttons to launch/stop scan"""
        self.set_action_enabled('start', enable)
        self.set_action_enabled('stop', enable)
        self.set_action_enabled('pause', enable)
        if enable:
            self.set_action_checked('pause', False)

    def connect_things(self):
        self.status_signal[str].connect(self.dashboard.add_status)

        self.connect_action('start', self.logging.start_logging)
        self.connect_action('pause', self.logging.pause_logging)
        self.connect_action('stop', lambda: self.logging.stop_logging('Logging Stopped by the User'))
        self.connect_action('grab_all', self.start_stop_all)

    def quit_fun(self) -> bool:
        """
            Quit the current instance of DAQ_scan and close on cascade move and detector modules.

            See Also
            --------
            quit_fun
        """
        if self.logging.is_running:
            messagebox(title='Running',
                       text='The Logging is running, first stop it')
            return False
        elif self.settings['worker', 'worker_tasks'] > 0:
            messagebox(title='Running',
                       text='The Saver is finishing the savings')
            self.logging.stop_logging("User prompted a quit of the Application,"
                                      " Stopping the Logging")
            return False

        self.h5_manager.close_file()
        return super().quit_fun()

    def start_stop_all(self, start=True):
        for det in self.modules_manager.detectors:
            det.grab() if start else det.stop_grab()
        for act in self.modules_manager.actuators:
            act.grab() if start else act.stop_grab()


    @property
    def module_and_data_saver(self) -> LoggerSaver:
        return super().module_and_data_saver



class SaverWorker(QtCore.QObject):
    """ Worker in separated thread receiving the data from a DataGenerator
    and adding them into the enlargeable arrays with the H5file using the
     LoggerModuleSaver """

    n_saved = QtCore.Signal(int)
    data_to_save_signal = QtCore.Signal(DataToExport)


    def __init__(self, saver: LoggerSaver, parent=None):
        super().__init__(parent)
        self.saver = saver
        self._n_saved = 0
        self._show_thread = True

        self.data_to_save_signal.connect(self.save_data, QtCore.Qt.ConnectionType.QueuedConnection)

    @QtCore.Slot(DataToExport)
    def save_data(self, dte: DataToExport):
        if self._show_thread:
            print(f'Saving data in Qthread{self.thread()}')
            self._show_thread = False
        self.saver.add_data(dte,)
        self._n_saved += 1
        self.n_saved.emit(self._n_saved)


class Logging(QObject):
    _worker_done = QtCore.Signal()

    def __init__(self, logger: DAQLogger, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.thread_manager = WorkerThreadManager(parent=self)
        self.logger.modules_manager.actuators_changed.connect(self.update_connections)
        self.logger.modules_manager.detectors_changed.connect(self.update_connections)

        self.saver_worker: SaverWorker = None
        self._n_emitted = 0

    @property
    def saver(self) -> LoggerSaver:
        return self.logger.module_and_data_saver

    @property
    def is_running(self) -> bool:
        return self.logger.status_manager.is_logging

    @is_running.setter
    def is_running(self, value: bool):
        self.logger.status_manager.is_logging = value

    @property
    def n_saved(self) -> int:
        return self.logger.status_manager.n_saved

    @n_saved.setter
    def n_saved(self, value: int):
        self.logger.status_manager.n_saved = value

    @property
    def modules_manager(self) -> ModulesManager:
        """ Convenience property"""
        return self.logger.modules_manager

    def _update_status(self, msg: str):
        """ convenience method to update the status signal """
        self.logger.update_status(msg)
        logger.info(msg)

    def start_logging(self):
        """
            Start a logging.
        """
        self._update_status('Initializing')
        self._init_logging()

        self.logger.set_action_enabled('start', False)
        self.logger.status_manager.log_time = QtCore.QDateTime.currentDateTime()
        self.logger.status_manager.set_permanent_status('Starting logging')
        self.is_running = True

        self._connect_control_modules()
        self._n_emitted = 0
        self.n_saved = 0

    def update_connections(self):
        self._disconnect_control_modules()
        self._connect_control_modules()

    def _connect_control_modules(self):
        """ Connect only the selected control modules"""
        for detector in self.logger.modules_manager.detectors:
            detector.grab_done_signal.connect(self.save_detector)
        for actuator in self.logger.modules_manager.actuators:
            actuator.current_value_signal.connect(self.format_and_save_actuator)

    def _disconnect_control_modules(self):
        """ Disconnect all the Control Modules """
        for detector in self.logger.modules_manager.detectors_all:
            # disconnect all in case one changed the list of logged modules
            try:
                detector.grab_done_signal.disconnect(self.save_detector)
            except TypeError:
                pass
        for actuator in self.logger.modules_manager.actuators:
            try:
                actuator.move_done_signal.disconnect(self.format_and_save_actuator)
            except TypeError:
                pass

    def save_detector(self, dte: DataToExport):
        self._n_emitted += 1
        self.n_saved += 1
        self.saver_worker.data_to_save_signal.emit(dte)

    def format_and_save_actuator(self, dwa: DataActuator):
        self._n_emitted += 1
        self.n_saved += 1
        self.saver_worker.data_to_save_signal.emit(DataToExport(name=dwa.name,
                                                                data=[dwa]))

    def _init_logging(self):
        try:
            self._worker_done.disconnect(self.terminate_worker)
        except TypeError:
            pass
        self.saver.h5saver = self.logger.h5saver
        self.saver.get_set_node(new=True)

        # managing saver worker
        self.saver_worker = SaverWorker(saver=self.saver,)
        self.thread_manager.create_thread_for_worker('saver', self.saver_worker)
        self.saver_worker.n_saved.connect(self.update_worker_ntask)
        self.thread_manager.start_thread('saver')
        self.logger.settings['worker', 'worker_running'] = self.thread_manager.get_thread('saver').isRunning()

    @QtCore.Slot(int)
    def update_worker_ntask(self, n_saved: int):
        n_tasks = self._n_emitted - n_saved
        self.logger.settings['worker', 'worker_tasks'] = n_tasks

        if n_tasks == 0:
            self._worker_done.emit()

    def terminate_worker(self):
        """ Will terminate/close/stops a few things when the worker is done working"""
        # stopping the plotting before flushing/closing the file
        #1 disconnecting the connection to here (fired once)
        try:
            self._worker_done.disconnect(self.terminate_worker)
        except TypeError:
            pass
        try: #2 disconnect the data production from the saving
            self.saver_worker.data_to_save_signal.disconnect(self.saver_worker.save_data)
        except TypeError:
            pass

        #3 quit the thread managing the data saving (nothing left in the loop and no more connection)
        self.thread_manager.exit_worker_thread('saver', delete_worker=True)

        #4 flushing/closing the file to be able to create new groups...
        self.logger.h5_manager.close_file()

        #5 updating GUI info
        self.logger.settings['worker', 'worker_running'] = self.thread_manager.get_thread('saver').isRunning()


    def pause_logging(self, do_pause=True):
        if do_pause:
            self.is_running = False
            self._disconnect_control_modules()
        else:
            self.is_running = True
            self._connect_control_modules()

        self._on_scan_pausing(do_pause)

    def stop_logging(self, msg: str = None):
        """
        """
        self.is_running = False

        #1 Stop the emission of data immediately
        self._disconnect_control_modules()

        #2 terminate the saver worker once its queue is empty
        if self.logger.settings['worker', 'worker_tasks'] == 0:
            self.terminate_worker()
        else:
            self._worker_done.connect(self.terminate_worker)

        #3 update the GUI
        self.logger.set_action_checked('pause', False)
        self.logger.set_action_enabled('start', True)
        if msg is not None:
            self._update_status(msg)
            self.logger.status_manager.set_permanent_status(msg)

    @staticmethod
    def format_actuators_data(data_act: DataActuator) -> DataToExport:
        return DataToExport(name=data_act.name, data=[data_act])

    def _on_scan_pausing(self, pausing=True):
        if pausing:
            message = "Logging has been paused"
        else:
            message = "Logging resumed"

        self._update_status(message)
        self.logger.status_manager.set_permanent_status(message)
        self.logger.status_manager.is_logging = not pausing



def main():
    import sys
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import load_dashboard_with_arguments
    from pymodaq.utils.gui_utils.loader_utils import create_extension

    app = mkQApp('DAQ Logger')

    win, dashboard, _ = load_dashboard_with_arguments(show_dashboard=False,
                                                      load_extension=False,
                                                      )
    win.mainwindow.setVisible(False)
    win_ext, logger = create_extension(dashboard, DAQLogger, show_extension=True)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Automated scanning module functionalities for PyMoDAQ

Contains all objects related to the DAQScan module, to do automated scans, saving data...
"""

from typing import TYPE_CHECKING

from pymodaq.control_modules.enums import ActionIconNames
from pymodaq.utils.h5modules.module_saving import LoggerSaver
from pymodaq_gui.messenger import messagebox
from pymodaq_gui.utils.custom_app import WorkFlowActions

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.utils.dock import Dock, DockArea
from pymodaq_utils.config import GlobalConfig as Config

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Qt

from pymodaq_gui.utils.widgets import MultistateLED, StatusPalette, Status
from pymodaq_utils.enums import StrEnum

from pymodaq.utils.data import DataActuator, DataToExport
from pymodaq.utils.custom_ext import CustomExt
from pymodaq_gui.utils.enums import MenuToolbarNames

from pymodaq_gui.utils.widgets import QSpinBox_ro
from pymodaq_gui.utils.app_worker import ExtensionWorker, SaverWorker
from pymodaq_data.h5modules.data_saving import DataBundle

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard


config = Config()
logger = set_logger(get_module_name(__file__))


class LoggerLedState(StrEnum):
    """States of the DAQ_Logger logging-status LED."""
    IDLE = 'idle'
    RUNNING = 'running'
    ERROR = 'error'


class LoggerStatusBarManager:
    def __init__(self, logger: 'DAQLogger'):
        self.logger = logger

        self._start_log_time: QtWidgets.QDateTimeEdit = None
        self._logging_state: MultistateLED = None
        self._n_saved_sb: QSpinBox_ro = None

    @property
    def log_time(self) -> QtCore.QDateTime:
        return self._start_log_time.dateTime()

    @log_time.setter
    def log_time(self, date_time: QtCore.QDateTime):
        self._start_log_time.setDateTime(date_time)

    @property
    def is_logging(self) -> bool:
        return self._logging_state.get_state() == LoggerLedState.RUNNING

    @is_logging.setter
    def is_logging(self, is_logging: bool):
        self._logging_state.set_state(LoggerLedState.RUNNING if is_logging else LoggerLedState.IDLE)

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

        self._logging_state = MultistateLED(
            states=[
                (LoggerLedState.IDLE,    StatusPalette.color(Status.OFF)),
                (LoggerLedState.RUNNING, StatusPalette.color(Status.RUNNING)),
                (LoggerLedState.ERROR,   StatusPalette.color(Status.CRITICAL)),
            ],
            readonly=True,
        )
        self._logging_state.setToolTip('Logging state: idle / running / error')
        self.statusbar.addPermanentWidget(self._logging_state)

        self._n_saved_sb = QSpinBox_ro()
        self._n_saved_sb.setToolTip('Total number of saved data')
        self.statusbar.addPermanentWidget(self._n_saved_sb)


class DAQLogger(CustomExt):
    """
    Main class initializing a DAQ_Logger module
    """
    show_h5file_statusbar_widgets = True
    show_workflow_actions = True
    icon_name = 'home_storage'
    params = [] + SaverWorker.params


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

    def do_things_after_ui_setup(self):
        self.set_action_visible(WorkFlowActions.LOG, False) # hide as it should always be True for this extension

    def do_things_after_experiment_set(self, experiment_name: str, show_dashboard: bool = None):
        self.enable_workflow_actions(True)
        super().do_things_after_experiment_set(experiment_name, show_dashboard)

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        """
        """
        self.add_toolbar(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), self.mainwindow,
                         toolbar=self.h5_manager.toolbar, add_break=False)
        self.add_menu(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), parent_menu=menubar)
        self.add_menu(MenuToolbarNames.TOOLS, MenuToolbarNames.TOOLS.capitalize(), parent_menu=menubar)

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

        self.toolbar.addSeparator()
        self.add_action('grab_all', 'Grab All', ActionIconNames.GRAB,
                        "Grab/Stop all selected detectors's data and actuators's value",
                        checkable=True,
                        icon_checked=ActionIconNames.GRAB_STOP,
                        icon_checked_color=self.get_theme().green)
        logger.debug('actions set')

        self.enable_workflow_actions(False)

    def connect_things(self):
        self.status_signal[str].connect(self.dashboard.add_status)

        self.connect_action(WorkFlowActions.START, self.logging.start)
        self.connect_action(WorkFlowActions.PAUSE, self.logging.pause)
        self.connect_action(WorkFlowActions.STOP, lambda: self.logging.stop('Logging Stopped by the User'))
        self.connect_action('grab_all', self.start_stop_all)

    def _quit_fun(self) -> bool:
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

        elif self.settings[SaverWorker.worker_setting_name, 'worker_tasks'] > 0:
            messagebox(title='Running',
                       text='The Saver is finishing the savings')
            self.logging.stop("User prompted a quit of the Application,"
                                      " Stopping the Logging")
            return False

        self.h5_manager.close_file()
        return True

    def start_stop_all(self, start=True):
        for det in self.modules_manager.detectors:
            det.grab() if start else det.stop_grab()
        for act in self.modules_manager.actuators:
            act.grab() if start else act.stop_grab()

    @property
    def module_and_data_saver(self) -> LoggerSaver:
        return super().module_and_data_saver


class Logging(ExtensionWorker):

    def __init__(self, logger: DAQLogger, parent=None):
        self._app: DAQLogger = logger
        super().__init__(app=logger, parent=parent)

        self._app.modules_manager.actuators_changed.connect(self.update_connections)
        self._app.modules_manager.detectors_changed.connect(self.update_connections)

    @property
    def n_saved(self) -> int:
        return self._app.status_manager.n_saved

    @n_saved.setter
    def n_saved(self, value: int):
        self._app.status_manager.n_saved = value

    def _update_status(self, msg: str):
        """ convenience method to update the status signal """
        self._app.update_status(msg)
        logger.info(msg)

    def _start(self):
        """
            Start a logging.
        """
        self.module_and_data_saver.get_set_node(new=True)

        self._app.status_manager.log_time = QtCore.QDateTime.currentDateTime()
        self._app.status_manager.set_permanent_status('Starting logging')
        self._app.status_manager.is_logging = True
        self.n_saved = 0
        self.update_connections()

    def update_connections(self):
        if self.is_running:
            self._disconnect_control_modules()
            self._connect_control_modules()

    def _connect_control_modules(self):
        """ Connect only the selected control modules"""
        for detector in self._app.modules_manager.detectors:
            detector.grab_done_signal.connect(self.save_detector)
        for actuator in self._app.modules_manager.actuators:
            actuator.current_value_signal.connect(self.format_and_save_actuator)

    def _disconnect_control_modules(self):
        """ Disconnect all the Control Modules """
        for detector in self._app.modules_manager.detectors_all:
            # disconnect all in case one changed the list of logged modules
            try:
                detector.grab_done_signal.disconnect(self.save_detector)
            except TypeError:
                pass
        for actuator in self._app.modules_manager.actuators:
            try:
                actuator.move_done_signal.disconnect(self.format_and_save_actuator)
            except TypeError:
                pass

    def save_detector(self, dte: DataToExport):
        self.thread_manager.n_jobs[SaverWorker.name] += 1
        self.n_saved += 1
        self.saver_worker.data_to_save_signal.emit(DataBundle(dte=dte))

    def format_and_save_actuator(self, dwa: DataActuator):
        self.thread_manager.n_jobs[SaverWorker.name] += 1
        self.n_saved += 1
        self.saver_worker.data_to_save_signal.emit(
            DataBundle(dte=DataToExport(name=dwa.name,
                                        data=[dwa])))

    def _pause(self, do_pause=True):
        if do_pause:
            self._disconnect_control_modules()
        else:
            self._connect_control_modules()
        self._app.status_manager.is_logging = not do_pause

    def _stop(self, msg: str = None):
        """
        """

        #1 Stop the emission of data immediately
        self._disconnect_control_modules()
        self._app.status_manager.is_logging = False

        if msg is not None:
            self._app.status_manager.set_permanent_status(msg)


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

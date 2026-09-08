#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Automated scanning module functionalities for PyMoDAQ

Contains all objects related to the DAQScan module, to do automated scans, saving data...
"""

from collections import OrderedDict
from typing import TYPE_CHECKING, Union

from pymodaq_gui.managers.runner_thread_manager import WorkerThreadManager

from extensions.daq_logger.abstract import AbstractLogger
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


try:
    import sqlalchemy
    from pymodaq.extensions.daq_logger.db.db_logger import DataBaseLogger
    is_sql = True
except Exception as e:
    DataBaseLogger = None
    is_sql = False
    logger.info('To enable logging to database install: sqalchemy and sqlalchemy_utils packages as'
                ' well as the backend for your specific database, for instance psycopg2 for'
                ' PostGreSQL database')

LOG_TYPES = ['None', 'H5 File']
if is_sql:
    LOG_TYPES.append('SQL DataBase')



class LoggerStatusBarManager:
    def __init__(self, logger: 'DAQ_Logger'):
        self.logger = logger

        self._start_log_time: QtWidgets.QDateTimeEdit = None
        self._logging_state: QLED = None
        self._n_saved_sb: QSpinBox_ro = None

    @property
    def log_time(self) -> QtCore.QDateTime:
        return self._start_log_time.dateTime()

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


class DAQ_Logger(CustomExt):
    """
    Main class initializing a DAQ_Logger module
    """
    show_h5file_statusbar_widgets = True
    icon_name = ''
    params = [
        {'title': 'Log Type:', 'name': 'log_type', 'type': 'str', 'value': '', 'readonly': True},
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

        self.logger: Union[H5Logger, DataBaseLogger] = None
        self.status_manager = LoggerStatusBarManager(self)

        self.logging = Logging(self)

        self.setup_ui()

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
        self.add_action('settings', 'Show Logging Settings', 'settings', menu='actions',
                        checkable=True, icon_checked_color=self.get_theme().green)
        self.toolbar.addSeparator()
        log_type_combo = QtWidgets.QComboBox()
        log_type_combo.addItems(LOG_TYPES)
        log_type_combo.currentTextChanged.connect(self.set_log_type)
        self.add_widget('log_type', log_type_combo,
                        tip='Select the logging backend',
                        toolbar=self.toolbar)

        self.toolbar.addSeparator()
        self.add_action('grab_all', 'Grab All', 'run_all', "Grab all selected detectors's data and actuators's value",
                        checkable=False, toolbar=self.toolbar)
        self.add_action('stop_all', 'Stop All', 'stop_all', "Stop all selected detectors and actuators",
                        checkable=False, toolbar=self.toolbar)


        self.enable_start_stop(False)

        logger.debug('actions set')

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
        self.connect_action('grab_all', self.start_all)
        self.connect_action('stop_all', self.stop_all)

        self.connect_action('settings', self.show_dock_settings)

    def show_dock_settings(self, show: bool = True):
        self.docks['logger_settings'].setVisible(show)

    def value_changed(self, param):
        if param.name() == 'log_type':
            if param.value() != 'None':
                self.enable_start_stop(True)
                self.set_logger(param.value())

    def set_logger(self, logger_interface):
        if self.logger is not None:
            self.logger.close()
            self.docks['logger_settings'].removeWidgets()

        if logger_interface == 'H5 File':
            self.logger = H5Logger(self.modules_manager, app=self)
        elif logger_interface == 'SQL DataBase':
            self.logger = DataBaseLogger(self.dashboard.experiment_file.stem,
                                         app=self,)
        else:
            return
        # bad idea to put it there logger.addHandler(self.logger.get_handler())
        self.docks['logger_settings'].addWidget(self.logger.settings_tree)


    def quit_fun(self) -> bool:
        """
            Quit the current instance of DAQ_scan and close on cascade move and detector modules.

            See Also
            --------
            quit_fun
        """
        try:
            self.logger.close()
        except Exception as e:
            logger.exception(str(e))

        return super().quit_fun()

    def start_all(self):
        for det in self.modules_manager.detectors:
            det.grab()
        for act in self.modules_manager.actuators:
            act.grab()

    def stop_all(self):
        for det in self.modules_manager.detectors:
            det.stop_grab()
        for act in self.modules_manager.actuators:
            act.stop_grab()

    def stop(self):
        """ Programmatic method to stop action in the extension

        Irrelevant for the DAQLogger as it doesn't do anything on the control modules

        """
        pass

    def set_log_type(self, log_type):
        self.settings.child('log_type').setValue(log_type)



class SaverWorker(QtCore.QObject):
    """ Worker in separated thread receiving the data from a DataGenerator
    and adding them into the enlargeable arrays with the H5file using the
     LoggerModuleSaver """

    n_saved = QtCore.Signal(int)
    data_to_save_signal = QtCore.Signal(DataToExport)


    def __init__(self, saver: H5Logger | DataBaseLogger):
        super().__init__()
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

    def __init__(self, logger: DAQ_Logger, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.thread_manager = WorkerThreadManager(parent=self)

        self.saver_worker: SaverWorker = None
        self._n_emitted = 0

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
        if self._init_logging():
            self.logger.status_manager.set_permanent_status('Starting logging')
            self.logger.status_manager.is_logging = True


            self._connect_control_modules()
            self._n_emitted = 0
            self.n_saved = 0
        else:
            self._update_status('Initialization Failed')
            self.logger.enable_start_stop(False)

    def _connect_control_modules(self):
        for detector in self.logger.modules_manager.detectors:
            detector.grab_done_signal.connect(self.save_detector)
        for actuator in self.logger.modules_manager.actuators:
            actuator.move_done_signal.connect(self.format_and_save_actuator)

    def _disconnect_control_modules(self):
        for detector in self.logger.modules_manager.detectors:
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

    def _init_logging(self) -> bool:
        try:
            self._worker_done.disconnect(self.terminate_worker)
        except TypeError:
            pass
        self.logger.logger.update_app(self.logger)
        status_backend = self.set_logging()
        if status_backend:
            # managing saver worker
            self.saver_worker = SaverWorker(saver=self.logger.logger,)
            self.thread_manager.create_thread_for_worker('saver', self.saver_worker)
            self.saver_worker.n_saved.connect(self.update_worker_ntask)
            self.thread_manager.start_thread('saver')
            self.logger.settings['worker', 'worker_running'] = True

        return status_backend

    def save_settings(self):
        """
        """
        if self.logger is not None:
            self.logger.status_manager.n_saved = 0

            settings_str = b'<All_settings>'
            settings_str += ioxml.parameter_to_xml_string(self.logger.dashboard.settings)
            settings_str += ioxml.parameter_to_xml_string(self.logger.settings)
            settings_str += ioxml.parameter_to_xml_string(self.logger.logger.settings)
            settings_str += b'</All_settings>'

            if not self.logger.logger.init_logger(settings_str):
                return False
            #
            return True
        else:
            return False

    def set_logging(self):
        """

        """
        status = self.save_settings()

        if status:
            modules_log = self.modules_manager.detectors_all + self.modules_manager.actuators_all
            if modules_log != []:
                # # check if the modules are initialized
                # for module in modules_log:
                #     if not module.initialized_state:
                #         logger.error(f'module {module.title} is not initialized')
                #         return False
                #
                # # create the detectors in the chosen logger
                # for mod in modules_log:
                #     settings_str = b'<All_settings>'
                #     settings_str += ioxml.parameter_to_xml_string(mod.settings)
                #
                #     if mod.module_type == 'DAQ_Viewer':
                #         for viewer in mod.ui.viewers:
                #             if hasattr(viewer, 'roi_manager'):
                #                 settings_str += ioxml.parameter_to_xml_string(
                #                     viewer.roi_manager.settings)
                #     settings_str += b'</All_settings>'
                #     if mod.module_type == 'DAQ_Viewer':
                #         self.logger.logger.add_detector(mod.title, settings_str)
                #     elif mod.module_type == 'DAQ_Move':
                #         self.logger.logger.add_actuator(mod.title, settings_str)

                self.logger.enable_start_stop(True)
                return True
            else:
                self.logger.update_status('Cannot start logging... No detectors selected')
                self.logger.enable_start_stop(False)
                return False

        else:
            self.logger.update_status('Cannot start logging... check connections')
            self.logger.enable_start_stop(False)
            return False


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
        self.logger.logger.close()
        self.logger.h5_manager.update_file_status_led()

        #5 updating GUI info
        self.logger.enable_start_stop(True)
        self.logger.settings['worker', 'worker_running'] = False

    def pause_logging(self, do_pause=True):
        if do_pause:
            self.is_running = False
            self._disconnect_control_modules()
        else:
            self.is_running = True
            self._connect_control_modules()

        self.modules_manager.enable_modules(do_pause)
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
        if msg is not None:
            self._update_status(msg)


    @staticmethod
    def format_actuators_data(data_act: DataActuator) -> DataToExport:
        return DataToExport(name=data_act.name, data=[data_act])

    def _on_scan_pausing(self, pausing=True):
        if pausing:
            message = "Logging has been paused"
        else:
            message = "Logging resumed"

        self._update_status(message)



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
    win_ext, logger = create_extension(dashboard, DAQ_Logger, show_extension=True)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

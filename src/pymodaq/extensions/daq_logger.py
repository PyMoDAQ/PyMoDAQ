#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Automated scanning module functionalities for PyMoDAQ

Contains all objects related to the DAQScan module, to do automated scans, saving data...
"""

import sys
from collections import OrderedDict
import datetime
from typing import TYPE_CHECKING, Union

from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.gui_utils.custom_app import CustomApp
from pymodaq.utils.gui_utils.dock import Dock
from pymodaq.utils.config import Config, get_set_preset_path
import pymodaq.utils.parameter.ioxml
import numpy as np
from qtpy import QtWidgets
from qtpy.QtCore import QObject, Slot, QThread, Signal, Qt
from pymodaq.utils import data as data_mod
from pymodaq.utils.gui_utils.widgets import QLED
from pymodaq.utils.gui_utils.dock import DockArea
from pymodaq.utils import daq_utils as utils
from pymodaq.utils.h5modules.h5logging import H5Logger
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq.utils.data import DataToExport, DataActuator, DataWithAxes


if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard



config = Config()
logger = set_logger(get_module_name(__file__))


try:
    import sqlalchemy
    from pymodaq.utils.db.db_logger.db_logger import DataBaseLogger
    is_sql = True
except Exception as e:
    is_sql = False
    logger.info('To enable logging to database install: sqalchemy and sqlalchemy_utils packages as well as the '
                'backend for your specific database, for instance psycopg2 for PostGreSQL database')

LOG_TYPES = ['None', 'H5 File']
if is_sql:
    LOG_TYPES.append('SQL DataBase')


class DAQ_Logger(CustomApp):
    """
    Main class initializing a DAQ_Logger module
    """
    command_DAQ_signal = Signal(list)
    status_signal = Signal(str)

    params = [
        {'title': 'Log Type:', 'name': 'log_type', 'type': 'str', 'value': '', 'readonly': True},
    ]

    def __init__(self, dockarea: DockArea = None, dashboard: 'DashBoard' = None):
        """

        Parameters
        ----------
        dockarea: DockArea
            instance of the modified pyqtgraph Dockarea
        dashboard: DashBoard
            instance of the pymodaq dashboard
        """

        super().__init__(dockarea, dashboard)

        self.wait_time = 1000

        self.logger_thread = None
        self.logger: Union[H5Logger, DataBaseLogger] = None
        self.setup_ui()

    def setup_actions(self):
        '''
        subclass method from ActionManager
        '''
        logger.debug('setting actions')
        self.add_action('quit', 'Quit', 'close2', "Quit program", toolbar=self.toolbar)
        self.toolbar.addSeparator()
        self.add_action('start', 'Start Logging', 'run2', "Start the logging",
                        checkable=True, toolbar=self.toolbar)
        self.add_action('stop', 'Stop', 'stop', 'Stop/pause logging',
                        checkable=False, toolbar=self.toolbar)

        log_type_combo = QtWidgets.QComboBox()
        log_type_combo.addItems(LOG_TYPES)
        log_type_combo.currentTextChanged.connect(self.set_log_type)
        self._actions['log_type'] = self.toolbar.addWidget(log_type_combo)
        self.toolbar.addSeparator()
        self.add_action('grab_all', 'Grab All', 'run_all', "Grab all selected detectors's data and actuators's value",
                        checkable=False, toolbar=self.toolbar)
        self.add_action('stop_all', 'Stop All', 'stop_all', "Stop all selected detectors and actuators",
                        checkable=False, toolbar=self.toolbar)
        self.add_action('infos', 'Log infos', 'information2', "Show log file",
                        checkable=False, toolbar=self.toolbar)

        self.set_action_enabled('start', False)
        self.set_action_enabled('stop', False)

        logger.debug('actions set')

    def setup_docks(self):
        logger.debug('setting docks')
        self.docks['detectors'] = Dock("Detectors")
        splitter = QtWidgets.QSplitter(Qt.Vertical)
        self.docks['detectors'].addWidget(splitter)
        splitter.addWidget(self.settings_tree)
        splitter.addWidget(self.modules_manager.settings_tree)
        self.dockarea.addDock(self.docks['detectors'])

        self.docks['logger_settings'] = Dock("Logger Settings")
        self.dockarea.addDock(self.docks['logger_settings'], 'right', self.docks['detectors'])

        self.statusbar.setMaximumHeight(25)
        self.status_widget = QtWidgets.QLabel('Initializing')
        self.statusbar.addPermanentWidget(self.status_widget)

        self.start_log_time = QtWidgets.QDateTimeEdit()
        self.start_log_time.setReadOnly(True)
        self.start_log_time.setToolTip('Logging started at:')
        self.statusbar.addPermanentWidget(self.start_log_time)

        self.logging_state = QLED()
        self.logging_state.setToolTip('logging status: green (running), red (idle)')
        self.logging_state.clickable = False
        self.statusbar.addPermanentWidget(self.logging_state)

    def connect_things(self):
        self.status_signal[str].connect(self.dashboard.add_status)
        self._actions['quit'].connect_to(self.quit_fun)

        self._actions['start'].connect_to(self.start_logging)
        self._actions['stop'].connect_to(self.stop_logging)
        self._actions['grab_all'].connect_to(self.start_all)
        self._actions['stop_all'].connect_to(self.stop_all)

        self._actions['infos'].connect_to(self.dashboard.show_log)

    def setup_menu(self):
        """
        """
        file_menu = self.mainwindow.menuBar().addMenu('File')
        self.affect_to('infos', file_menu)

    def value_changed(self, param):
        if param.name() == 'log_type':
            if param.value() != 'None':
                self.set_action_enabled('start', True)
                self.set_action_enabled('stop', True)
                self.set_logger(param.value())

    def set_logger(self, logger_interface):
        if self.logger is not None:
            self.logger.close()
            self.docks['logger_settings'].removeWidgets()

        if logger_interface == 'H5 File':
            self.logger = H5Logger(self.modules_manager)
        elif logger_interface == 'SQL DataBase':
            self.logger = DataBaseLogger(self.dashboard.preset_file.stem)
        else:
            return

        self.docks['logger_settings'].addWidget(self.logger.settings_tree)

    def quit_fun(self):
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

        self.dockarea.close()

    def set_continuous_save(self):
        """
            Set a continous save file using the base path located file with
            a header-name containing date as a string.

            See Also
            --------
            daq_utils.set_current_scan_path
        """
        if self.logger is not None:
            self.do_continuous_save = True
            self.logger.settings.child('N_saved').show()
            self.logger.settings.child('N_saved').setValue(0)

            settings_str = b'<All_settings>'
            settings_str += pymodaq.utils.parameter.ioxml.parameter_to_xml_string(self.dashboard.settings)
            settings_str += pymodaq.utils.parameter.ioxml.parameter_to_xml_string(
                self.dashboard.preset_manager.preset_params)
            if self.dashboard.settings.child('loaded_files', 'overshoot_file').value() != '':
                settings_str += pymodaq.utils.parameter.ioxml.parameter_to_xml_string(
                    self.dashboard.overshoot_manager.overshoot_params)
            if self.dashboard.settings.child('loaded_files', 'roi_file').value() != '':
                settings_str += pymodaq.utils.parameter.ioxml.parameter_to_xml_string(
                    self.dashboard.roi_saver.roi_presets)
            settings_str += pymodaq.utils.parameter.ioxml.parameter_to_xml_string(self.settings)
            settings_str += pymodaq.utils.parameter.ioxml.parameter_to_xml_string(self.logger.settings)
            settings_str += b'</All_settings>'

            if not self.logger.init_logger(settings_str):
                return False
            logger.addHandler(self.logger.get_handler())
            return True
        else:
            return False

    def set_logging(self):
        """

        """
        status = self.set_continuous_save()
        if status:
            modules_log = self.modules_manager.detectors_all + self.modules_manager.actuators_all
            if modules_log != []:
                # check if the modules are initialized
                for module in modules_log:
                    if not module.initialized_state:
                        logger.error(f'module {module.title} is not initialized')
                        return False

                # create the detectors in the chosen logger
                for mod in modules_log:
                    settings_str = b'<All_settings>'
                    settings_str += pymodaq.utils.parameter.ioxml.parameter_to_xml_string(mod.settings)

                    if mod.module_type == 'DAQ_Viewer':
                        for viewer in mod.ui.viewers:
                            if hasattr(viewer, 'roi_manager'):
                                settings_str += pymodaq.utils.parameter.ioxml.parameter_to_xml_string(
                                    viewer.roi_manager.settings)
                    settings_str += b'</All_settings>'
                    if mod.module_type == 'DAQ_Viewer':
                        self.logger.add_detector(mod.title, settings_str)
                    elif mod.module_type == 'DAQ_Move':
                        self.logger.add_actuator(mod.title, settings_str)

                self._actions['start'].setEnabled(True)
                self._actions['stop'].setEnabled(True)
                return True
            else:
                self.update_status('Cannot start logging... No detectors selected')
                self._actions['start'].setEnabled(False)
                self._actions['stop'].setEnabled(True)
                return False

        else:
            self.update_status('Cannot start logging... check connections')
            self._actions['start'].setEnabled(False)
            self._actions['stop'].setEnabled(True)
            return False

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

    def set_log_type(self, log_type):
        self.settings.child('log_type').setValue(log_type)

    def start_logging(self):
        """
            Start a logging.
        """
        self.status_widget.setText('Starting logging')

        self.overshoot = False
        res = self.set_logging()

        # mandatory to deal with multithreads
        if self.logger_thread is not None:
            self.command_DAQ_signal.disconnect()
            if self.logger_thread.isRunning():
                self.logger_thread.exit()
                while not self.logger_thread.isFinished():
                    QThread.msleep(100)
                self.logger_thread = None

        self.logger_thread = QThread()

        log_acquisition = DAQ_Logging(self.settings, self.logger, self.modules_manager)

        log_acquisition.moveToThread(self.logger_thread)

        self.command_DAQ_signal[list].connect(log_acquisition.queue_command)
        log_acquisition.status_sig[list].connect(self.thread_status)

        self.logger_thread.log_acquisition = log_acquisition
        self.logger_thread.start()

        self._actions['start'].setEnabled(False)
        QtWidgets.QApplication.processEvents()
        self.logging_state.set_as_false()

        self.command_DAQ_signal.emit(["start_logging"])
        self.status_widget.setText('Running acquisition')

    def stop_logging(self):
        """
            Emit the command_DAQ signal "stop_acquisiion".

            See Also
            --------
            set_ini_positions
        """
        preset_items_det = self.modules_manager.detectors
        for det in preset_items_det:
            det.stop()
        self.command_DAQ_signal.emit(["stop_acquisition"])

        if not self.dashboard.overshoot:
            status = 'Data Logging has been stopped by user'
        else:
            status = 'Data Logging has been stopped due to overshoot'

        self.update_status(status)
        self._actions['start'].setEnabled(True)

    @Slot(list)
    def thread_status(self, status):  # general function to get datas/infos from all threads back to the main
        """
            | General function to get datas/infos from all threads back to the main.
            |

            Switch the status with :
                * *"Update status"* : Update the status bar with the status attribute txt message
                * *"Update_scan_index"* : Set the value of the User Interface - indice_scan_sb attribute.
                * *"Scan_done"* : Save the scan and init the positions
                * *"Timeout"* : Set the "Timeout occured" in the User Interface-log message

            See Also
            --------
            update_status, save_scan, set_ini_positions
        """
        if status[0] == "Update_Status":
            self.update_status(status[1], wait_time=self.wait_time)

        elif status[0] == "Timeout":
            self.status_widget.setText('Timeout occurred')

    def update_status(self, txt, wait_time=0):
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
            self.statusbar.showMessage(txt, wait_time)
            logger.info(txt)
        except Exception as e:
            logger.exception(str(e))


class DAQ_Logging(QObject):
    """

    """

    scan_data_tmp = Signal(OrderedDict)
    status_sig = Signal(list)

    def __init__(self, settings=None, logger=None, modules_manager: ModulesManager = None):

        """
            DAQ_Logging deal with the acquisition part of daq_scan.

            See Also
            --------
            custom_tree.parameter_to_xml_string
        """
        
        super(QObject, self).__init__()

        self.stop_logging_flag = False
        self.settings = settings
        self.ini_time = 0
        self.ind_log = 0
        self.modules_manager: ModulesManager = modules_manager
        self.modules_manager.detectors_changed.connect(self.update_connect_detectors)
        self.modules_manager.actuators_changed.connect(self.update_connect_actuators)
        self.data_logger = logger

    @Slot(list)
    def queue_command(self, command):
        """
            Treat the queue of commands from the current command to act, between :
                * *start_logging*
                * *stop_acquisition*
                * *set_ini_position*
                * *move_stages*

            =============== ============== =========================
            **Parameters**    **Type**      **Description**
            command           string list   the command string list
            =============== ============== =========================

            See Also
            --------
            start_logging, set_ini_positions, move_stages
        """
        if command[0] == "start_logging":
            self.start_logging()

        elif command[0] == "stop_acquisition":
            self.stop_scan_flag = True
            self.stop_logging()

    def do_save_continuous(self, data):
        """

        """
        try:
            self.data_logger.add_data(data)
        except Exception as e:
            logger.exception(str(e))

    def format_actuators_data(self, data_act: DataActuator):
        data = data_mod.DataToExport(name=data_act.name, data=[data_act])
        self.do_save_continuous(data)

    def connect_actuators(self, connect=True):
        """Connect actuators to DAQ_Logging do_save_continuous method

        Parameters
        ----------
        connect: bool
            If True make the connection else disconnect
        """
        self.modules_manager.connect_actuators(connect=connect, slot=self.format_actuators_data, signal='current_value')

    def update_connect_actuators(self):
        try:
            self.connect_actuators(False)
        except:
            pass
        self.connect_actuators()

    def connect_detectors(self, connect=True):
        """Connect detectors to DAQ_Logging do_save_continuous method

        Parameters
        ----------
        connect: bool
            If True make the connection else disconnect
        """
        self.modules_manager.connect_detectors(connect=connect, slot=self.do_save_continuous)

    def update_connect_detectors(self):
        try:
            self.connect_detectors(False)
        except :
            pass
        self.connect_detectors()

    def stop_logging(self):
        try:
            self.connect_detectors(connect=False)
            self.connect_actuators(connect=False)
        except Exception as e:
            logger.exception(str(e))

        if self.stop_logging_flag:
            status = 'Data Acquisition has been stopped by user'
            self.status_sig.emit(["Update_Status", status])
        if self.data_logger is not None:
            self.data_logger.stop_logger()

    def start_logging(self):
        try:
            self.connect_detectors()
            self.connect_actuators()
            self.stop_logging_flag = False
            self.status_sig.emit(["Update_Status", "Acquisition has started"])

        except Exception as e:
            logger.exception(str(e))


def main():
    from pymodaq.dashboard import DashBoard
    from pathlib import Path
    from pymodaq.utils.gui_utils.dock import DockArea

    config = Config()
    app = QtWidgets.QApplication(sys.argv)
    if config('style', 'darkstyle'):
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet())

    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    # win.setVisible(False)
    prog = DashBoard(area)
    file = Path(get_set_preset_path()).joinpath(f"{config('presets', 'default_preset_for_logger')}.xml")
    if file.exists():
        prog.set_preset_mode(file)
        prog.load_log_module()
    else:
        msgBox = QtWidgets.QMessageBox()
        msgBox.setText(f"The default file specified in the configuration file does not exists!\n"
                       f"{file}\n"
                       f"Impossible to load the Logger Module")
        msgBox.setStandardButtons(msgBox.Ok)
        ret = msgBox.exec()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Automated scanning module functionalities for PyMoDAQ

Contains all objects related to the DAQ_Scan module, to do automated scans, saving data...
"""

import sys
from collections import OrderedDict
import numpy as np
import logging

import pymodaq.daq_utils.parameter.ioxml
from pyqtgraph.dockarea import Dock
from pyqtgraph.parametertree import Parameter, ParameterTree
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal, QLocale

from pymodaq.daq_utils.managers.modules_manager import ModulesManager
from pymodaq.daq_utils.plotting.qled import QLED
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils import gui_utils as gutils
from pymodaq.daq_utils.h5modules import H5Saver, H5LogHandler

logger = utils.set_logger(utils.get_module_name(__file__))
try:
    import sqlalchemy
    from pymodaq.daq_utils.db.db_logger.db_logger import DbLoggerGUI, DBLogHandler

    is_sql = True
except Exception as e:
    is_sql = False
    logger.warning(str(e))
    logger.info('To enable logging to database install: sqalchemy and sql_alchemy_utils packages')


class DAQ_Logger(QObject):
    """
    Main class initializing a DAQ_Scan module with its dashboard and scanning control panel
    """
    command_DAQ_signal = pyqtSignal(list)
    status_signal = pyqtSignal(str)

    params = [
        {'title': 'Log Type:', 'name': 'log_type', 'type': 'str', 'value': '', 'readonly': True},
    ]

    def __init__(self, dockarea=None, dashboard=None):
        """

        Parameters
        ----------
        dockarea: (dockarea) instance of the modified pyqtgraph Dockarea (see daq_utils)
        dashboard: (DashBoard) instance of the pymodaq dashboard
        """
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super().__init__()
        self.dockarea = dockarea
        self.dashboard = dashboard
        if dashboard is None:
            raise Exception('No valid dashboard initialized')
        self.mainwindow = self.dockarea.parent()
        self.wait_time = 1000

        self.logger_thread = None
        self.detector_modules = self.dashboard.detector_modules
        self.det_modules_log = []
        self.log_types = ['None', 'H5 File']
        if is_sql:
            self.log_types.append('SQL DataBase')

        self.logger = None  # should be a reference either to self.h5saver or self.dblogger depending the choice of the user
        self.h5saver = H5Saver(save_type='logger')
        if is_sql:
            self.dblogger = DbLoggerGUI(self.dashboard.preset_file.stem)
        else:
            self.dblogger = None
        self.modules_manager = ModulesManager()

        self.setupUI()
        self.setup_modules(self.dashboard.title)

        self.h5saver.settings_tree.setVisible(False)
        if is_sql:
            self.dblogger.settings_tree.setVisible(False)

    def create_menu(self):
        """
        """
        # %% create Settings menu
        menubar = QtWidgets.QMenuBar()
        menubar.setMaximumHeight(30)
        self.ui.layout.insertWidget(0, menubar)

        self.file_menu = menubar.addMenu('File')

    def quit_fun(self):
        """
            Quit the current instance of DAQ_scan and close on cascade move and detector modules.

            See Also
            --------
            quit_fun
        """
        try:
            self.h5saver.close_file()
        except Exception as e:
            logger.exception(str(e))
        try:
            self.dblogger.close()
        except Exception as e:
            logger.exception(str(e))
        self.ui.logger_dock.close()

    def parameter_tree_changed(self, param, changes):
        """
            Check for changes in the given (parameter,change,information) tuple list.
            In case of value changed, update the DAQscan_settings tree consequently.

            =============== ============================================ ==============================
            **Parameters**    **Type**                                     **Description**
            *param*           instance of pyqtgraph parameter              the parameter to be checked
            *changes*         (parameter,change,information) tuple list    the current changes state
            =============== ============================================ ==============================
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
                if param.name() == 'log_type':
                    if param.value() == 'H5 File':
                        self.logger = self.h5saver
                    elif param.value() == 'SQL DataBase':
                        self.logger = self.dblogger
                self.h5saver.settings_tree.setVisible(param.value() == 'H5 File')
                if self.dblogger is not None:
                    self.dblogger.settings_tree.setVisible(param.value() == 'SQL DataBase')
            elif change == 'parent':
                pass

    def setup_modules(self, filename):
        """

        """
        try:
            ######################################################################
            # setting moves and det in tree
            preset_items_det = []
            items_det = [module.title for module in self.detector_modules]
            if items_det != []:
                preset_items_det = items_det

            self.modules_manager.set_detectors(self.detector_modules, preset_items_det)

        except Exception as e:
            logger.exception(str(e))

    def set_continuous_save(self):
        """
            Set a continous save file using the base path located file with
            a header-name containing date as a string.

            See Also
            --------
            daq_utils.set_current_scan_path
        """
        self.do_continuous_save = True
        self.logger.settings.child(('N_saved')).show()
        self.logger.settings.child(('N_saved')).setValue(0)

        settings_str = b'<All_settings>'
        settings_str += pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(self.dashboard.settings)
        settings_str += pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(
            self.dashboard.preset_manager.preset_params)
        if self.dashboard.settings.child('loaded_files', 'overshoot_file').value() != '':
            settings_str += pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(
                self.dashboard.overshoot_manager.overshoot_params)
        if self.dashboard.settings.child('loaded_files', 'roi_file').value() != '':
            settings_str += pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(
                self.dashboard.roi_saver.roi_presets)
        settings_str += pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(self.settings)
        settings_str += pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(self.logger.settings)
        settings_str += b'</All_settings>'

        if self.settings.child(('log_type')).value() == 'H5 File':
            self.logger.settings.child(('base_name')).setValue('DataLogging')
            self.h5saver.init_file(update_h5=True, metadata=dict(settings=settings_str))
            logger.addHandler(H5LogHandler(self.h5saver))
            self.h5saver.h5_file.flush()

        elif self.settings.child(('log_type')).value() == 'SQL DataBase':
            if not self.logger.settings.child('connected_db').value():
                status = self.logger.connect_db()
                if not status:
                    logger.critical('the Database is not and cannot be connnect')
                    self.update_status('the Database is not and cannot be connnect')
                    return False

            self.logger.add_config(settings_str)
            logger.addHandler(DBLogHandler(self.logger))

        return True

    def set_logging(self):
        """

        """
        status = self.set_continuous_save()
        if status:
            det_modules_log = self.modules_manager.detectors
            if det_modules_log != []:
                # check if the modules are initialized
                for module in det_modules_log:
                    if not module.initialized_state:
                        logger.error(f'module {module.title} is not initialized')
                        return False

                # create the detectors in the chosen logger
                for det in det_modules_log:
                    settings_str = b'<All_settings>'
                    settings_str += pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(det.settings)
                    for viewer in det.ui.viewers:
                        if hasattr(viewer, 'roi_manager'):
                            settings_str += pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(
                                viewer.roi_manager.settings)
                    settings_str += b'</All_settings>'

                    if self.settings.child(('log_type')).value() == 'H5 File':
                        if det.title not in self.h5saver.raw_group.children_name():
                            det_group = self.h5saver.add_det_group(self.h5saver.raw_group, det.title, settings_str)
                            self.h5saver.add_navigation_axis(np.array([0.0, ]),
                                                             det_group, 'time_axis', enlargeable=True,
                                                             title='Time axis',
                                                             metadata=dict(label='Time axis', units='timestamp',
                                                                           nav_index=0))

                    elif self.settings.child(('log_type')).value() == 'SQL DataBase':
                        self.logger.add_detectors([dict(name=det.title, xml_settings=settings_str)])

                self.ui.start_button.setEnabled(True)
                self.ui.stop_button.setEnabled(True)
                return True
            else:
                self.update_status('Cannot start logging... No detectors selected')
                self.ui.start_button.setEnabled(False)
                self.ui.stop_button.setEnabled(True)
                return False

        else:
            self.update_status('Cannot start logging... check connections')
            self.ui.start_button.setEnabled(False)
            self.ui.stop_button.setEnabled(True)
            return False

    def show_log(self):
        import webbrowser
        webbrowser.open(logger.handlers[0].baseFilename)

    def setupUI(self):

        self.ui = QObject()

        widget_settings = QtWidgets.QWidget()
        self.ui.layout = QtWidgets.QVBoxLayout()

        widget_settings.setLayout(self.ui.layout)

        widget_buttons = QtWidgets.QWidget()
        layout_buttons = QtWidgets.QHBoxLayout()
        widget_buttons.setLayout(layout_buttons)
        self.ui.layout.addWidget(widget_buttons)

        iconquit = QtGui.QIcon()
        iconquit.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/close2.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.quit_button = QtWidgets.QPushButton(iconquit, 'Quit')

        iconstart = QtGui.QIcon()
        iconstart.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/run2.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.start_button = QtWidgets.QPushButton(iconstart, '')
        self.ui.start_button.setToolTip('Start logging into h5file or database')

        iconstop = QtGui.QIcon()
        iconstop.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/stop.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.stop_button = QtWidgets.QPushButton(iconstop, '')
        self.ui.stop_button.setToolTip('Stop/pause logging')

        log_type_combo = QtWidgets.QComboBox()
        log_type_combo.addItems(self.log_types)
        log_type_combo.currentTextChanged.connect(self.set_log_type)

        iconstartall = QtGui.QIcon()
        iconstartall.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/run_all.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.startall_button = QtWidgets.QPushButton(iconstartall, '')
        self.ui.startall_button.setToolTip('Grab all selected detectors')

        layout_buttons.addWidget(self.ui.quit_button)
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.ui.startall_button)
        layout_buttons.addWidget(log_type_combo)
        layout_buttons.addWidget(self.ui.start_button)
        layout_buttons.addWidget(self.ui.stop_button)

        # %% create logger dock and make it a floating window
        self.ui.logger_dock = Dock("Logger", size=(1, 1), autoOrientation=False)
        # give this dock the minimum possible size
        self.ui.logger_dock.setOrientation('vertical')
        self.ui.logger_dock.addWidget(widget_settings)
        self.dockarea.addDock(self.ui.logger_dock, 'left')
        self.ui.logger_dock.float()

        widget_hor = QtWidgets.QWidget()
        layout_hor = QtWidgets.QHBoxLayout()

        main_sett_widget = QtWidgets.QWidget()
        main_sett_widget.setLayout(QtWidgets.QVBoxLayout())

        widget_hor.setLayout(layout_hor)
        self.ui.layout.addWidget(widget_hor)

        self.settings_tree = ParameterTree()
        self.settings_tree.setMinimumWidth(300)
        layout_hor.addWidget(main_sett_widget)
        main_sett_widget.layout().addWidget(self.settings_tree)
        main_sett_widget.layout().addWidget(self.modules_manager.settings_tree)

        self.modules_manager.settings.child('modules', 'actuators').hide()
        self.modules_manager.settings.child(('data_dimensions')).hide()
        self.modules_manager.settings.child(('actuators_positions')).hide()

        self.h5saver.settings_tree.setMinimumWidth(300)
        layout_hor.addWidget(self.h5saver.settings_tree)

        if is_sql:
            self.dblogger.settings_tree.setMinimumWidth(300)
            layout_hor.addWidget(self.dblogger.settings_tree)

        self.settings = Parameter.create(name='Settings', type='group', children=self.params)
        self.settings_tree.setParameters(self.settings, showTop=False)
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

        # %% init and set the status bar
        self.ui.statusbar = QtWidgets.QStatusBar(self.dockarea)
        self.ui.statusbar.setMaximumHeight(25)
        self.ui.layout.addWidget(self.ui.statusbar)
        self.ui.log_message = QtWidgets.QLabel('Initializing')
        self.ui.statusbar.addPermanentWidget(self.ui.log_message)

        self.ui.start_log_time = QtWidgets.QDateTimeEdit()
        self.ui.start_log_time.setReadOnly(True)
        self.ui.start_log_time.setToolTip('Logging started at:')

        self.ui.logging_state = QLED()
        self.ui.logging_state.setToolTip('logging status: green (running), red (idle)')
        self.ui.logging_state.clickable = False

        self.ui.statusbar.addPermanentWidget(self.ui.start_log_time)
        self.ui.statusbar.addPermanentWidget(self.ui.logging_state)
        self.ui.layout.addWidget(self.ui.statusbar)

        #       connecting
        self.status_signal[str].connect(self.dashboard.add_status)
        self.ui.quit_button.clicked.connect(self.quit_fun)

        self.ui.start_button.clicked.connect(self.start_logging)
        self.ui.stop_button.clicked.connect(self.stop_logging)
        self.ui.startall_button.clicked.connect(self.start_all)

        self.create_menu()

    def start_all(self):
        preset_items_det = self.modules_manager.detectors
        for det in preset_items_det:
            det.ui.grab_pb.click()

    def set_log_type(self, log_type):

        self.settings.child(('log_type')).setValue(log_type)

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

            See Also
            --------
            custom_tree.parameter_to_xml_file, create_menu
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

    def show_file_content(self):
        try:
            self.h5saver.init_file(addhoc_file_path=self.h5saver.settings.child(('current_h5_file')).value())
            self.h5saver.show_file_content()
        except Exception as e:
            logger.exception(str(e))

    def start_logging(self):
        """
            Start a logging.
        """
        self.ui.log_message.setText('Starting logging')

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

        self.ui.start_button.setEnabled(False)
        QtWidgets.QApplication.processEvents()
        self.ui.logging_state.set_as_false()

        self.command_DAQ_signal.emit(["start_logging"])
        self.ui.log_message.setText('Running acquisition')

    def stop_logging(self):
        """
            Emit the command_DAQ signal "stop_acquisiion".

            See Also
            --------
            set_ini_positions
        """
        preset_items_det = self.modules_manager.detectors
        for det in preset_items_det:
            det.ui.stop_pb.click()
        self.command_DAQ_signal.emit(["stop_acquisition"])

        if not self.dashboard.overshoot:
            status = 'Data Logging has been stopped by user'
        else:
            status = 'Data Logging has been stopped due to overshoot'

        self.update_status(status)
        self.ui.start_button.setEnabled(True)

    @pyqtSlot(list)
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
            self.ui.log_message.setText('Timeout occurred')

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
            self.ui.statusbar.showMessage(txt, wait_time)
            logging.info(txt)
        except Exception as e:
            logger.exception(str(e))


class DAQ_Logging(QObject):
    """
        =========================== ========================================
        **Attributes**               **Type**

        =========================== ========================================

    """
    scan_data_tmp = pyqtSignal(OrderedDict)
    status_sig = pyqtSignal(list)

    def __init__(self, settings=None, logger=None, modules_manager=[]):

        """
            DAQ_Logging deal with the acquisition part of daq_scan.

            See Also
            --------
            custom_tree.parameter_to_xml_string
        """
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(QObject, self).__init__()

        self.stop_logging_flag = False
        self.settings = settings
        self.ini_time = 0
        self.ind_log = 0
        self.modules_manager = modules_manager

        self.data_logger = logger
        if isinstance(self.data_logger, H5Saver):
            self.logger_type = "h5saver"
        elif isinstance(self.data_logger, DbLoggerGUI):
            self.logger_type = "dblogger"

    @pyqtSlot(list)
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

    def do_save_continuous(self, datas):
        """
        method used to perform continuous saving of data, for instance for logging. Will save datas as a function of
        time in a h5 file set when *continuous_saving* parameter as been set.

        Parameters
        ----------
        datas:  list of OrderedDict as exported by detector plugins

        """
        try:
            det_name = datas['name']
            if self.logger_type == 'h5saver':
                det_group = self.data_logger.get_group_by_title(self.data_logger.raw_group, det_name)
                time_array = self.data_logger.get_node(det_group, 'Logger_time_axis')
                time_array.append(np.array([datas['acq_time_s']]))

                data_types = ['data0D', 'data1D']
                if self.data_logger.settings.child(('save_2D')).value():
                    data_types.extend(['data2D', 'dataND'])

                for data_type in data_types:
                    if data_type in datas.keys() and len(datas[data_type]) != 0:
                        if not self.data_logger.is_node_in_group(det_group, data_type):
                            data_group = self.data_logger.add_data_group(det_group, data_type,
                                                                         metadata=dict(type='scan'))
                        else:
                            data_group = self.data_logger.get_node(det_group, utils.capitalize(data_type))
                        for ind_channel, channel in enumerate(datas[data_type]):
                            channel_group = self.data_logger.get_group_by_title(data_group, channel)
                            if channel_group is None:
                                channel_group = self.data_logger.add_CH_group(data_group, title=channel)
                                data_array = self.data_logger.add_data(channel_group, datas[data_type][channel],
                                                                       scan_type='scan1D', enlargeable=True)
                            else:
                                data_array = self.data_logger.get_node(channel_group, 'Data')
                            if data_type == 'data0D':
                                data_array.append(np.array([datas[data_type][channel]['data']]))
                            else:
                                data_array.append(datas[data_type][channel]['data'])
                self.data_logger.h5_file.flush()

            elif self.logger_type == 'dblogger':
                self.data_logger.add_datas(datas)

            self.data_logger.settings.child(('N_saved')).setValue(
                self.data_logger.settings.child(('N_saved')).value() + 1)

        except Exception as e:
            logger.exception(str(e))

    def stop_logging(self):
        try:
            self.modules_manager.connect_detectors(connect=False, slot=self.do_save_continuous)
        except Exception as e:
            logger.exception(str(e))

        if self.stop_logging_flag:
            status = 'Data Acquisition has been stopped by user'
            self.status_sig.emit(["Update_Status", status])
        if self.logger_type == 'h5saver':
            self.data_logger.flush()

    def start_logging(self):
        try:
            self.modules_manager.connect_detectors(slot=self.do_save_continuous)
            self.stop_logging_flag = False
            self.status_sig.emit(["Update_Status", "Acquisition has started"])

        except Exception as e:
            logger.exception(str(e))


def main():
    from pymodaq.dashboard import DashBoard
    from pymodaq.daq_utils.daq_utils import load_config, get_set_preset_path
    from pathlib import Path

    config = load_config()
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = gutils.DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    # win.setVisible(False)
    prog = DashBoard(area)
    file = Path(get_set_preset_path()).joinpath(f"{config['presets']['default_preset_for_logger']}.xml")
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

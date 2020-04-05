#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Automated scanning module functionalities for PyMoDAQ

Contains all objects related to the DAQ_Scan module, to do automated scans, saving data...
"""

import sys
from collections import OrderedDict
import numpy as np
import os
import logging

from pyqtgraph.dockarea import Dock
from pyqtgraph.parametertree import Parameter, ParameterTree
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QDate, QTime

from pymodaq.daq_utils.daq_utils import getLineInfo
import pymodaq.daq_utils.custom_parameter_tree as custom_tree# to be placed after importing Parameter
from pymodaq.daq_utils.plotting.qled import QLED
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils import gui_utils as gutils
from pymodaq.daq_utils.h5modules import H5Saver


class DAQ_Logger(QObject):
    """
    Main class initializing a DAQ_Scan module with its dashboard and scanning control panel
    """
    command_DAQ_signal = pyqtSignal(list)
    log_signal = pyqtSignal(str)

    params = [
        {'title': 'Log Type:', 'name': 'log_type', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Detectors', 'name': 'detectors', 'type': 'group', 'children': [
            {'name': 'Detectors', 'type': 'itemselect'},
        ]},
        {'title': 'Time Flow:', 'name': 'time_flow', 'type': 'group', 'expanded': False, 'children': [
            {'title': 'Wait time (ms)', 'name': 'wait_time', 'type': 'int', 'value': 0},
            {'title': 'Timeout (ms)', 'name': 'timeout', 'type': 'int', 'value': 10000},
        ]},
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
        self.log_types = ['H5 File', 'SQL DataBase']

        self.h5saver = H5Saver(save_type='logger')
        self.is_h5_initialized = False


        self.setupUI()
        self.setup_modules(self.dashboard.title)



    def create_menu(self):
        """
        """
        #%% create Settings menu
        menubar = QtWidgets.QMenuBar()
        menubar.setMaximumHeight(30)
        self.ui.verticalLayout.insertWidget(0, menubar)

        self.file_menu = menubar.addMenu('File')
        load_action = self.file_menu.addAction('Load file')
        load_action.triggered.connect(self.load_file)
        self.file_menu.addSeparator()
        save_action = self.file_menu.addAction('Save file as')
        save_action.triggered.connect(self.save_file)
        show_action = self.file_menu.addAction('Show file content')
        show_action.triggered.connect(self.show_file_content)

        self.settings_menu = menubar.addMenu('Settings')
        action_navigator = self.settings_menu.addAction('Show Navigator')
        action_navigator.triggered.connect(self.show_navigator)

    def load_file(self):
        self.h5saver.load_file(self.h5saver.h5_file_path)

    def quit_fun(self):
        """
            Quit the current instance of DAQ_scan and close on cascade move and detector modules.

            See Also
            --------
            quit_fun
        """
        try:
            self.h5saver.close_file()
            self.dashboard.quit_fun()
        except Exception as e:
            pass

    def save_file(self):
        if not os.path.isdir(self.h5saver.settings.child(('base_path')).value()):
            os.mkdir(self.h5saver.settings.child(('base_path')).value())
        filename = gutils.select_file(self.h5saver.settings.child(('base_path')).value(), save=True, ext='h5')
        self.h5saver.h5_file.copy_file(str(filename))

    def save_metadata(self, node, type_info='dataset_info'):
        """
            Switch the type_info value with :
                * *'dataset_info'* : Give the params attributes the dataset_attributes values
                * *'dataset'* : Give the params attributes the scan_attributes values

            |
            | Once done, course the params and add string casted date/time metadata as an element of attributes array.
            | Save the contents of given parameter object into a xml string unde the attributes settings.

            =============== =================== =========================================
            **Parameters**    **Type**           **Description**
            *node*            pytables h5 node   Root node to be treated
            *type_info*       string             File type info between :
                                                    * 'dataset_info'
                                                    * 'scan_info'
            =============== =================== =========================================

            See Also
            --------
            custom_tree.parameter_to_xml_string
        """

        attr = node._v_attrs
        if type_info == 'dataset_info':
            attr['type']='dataset'
            params=self.dataset_attributes
        else:
            attr['type'] = 'scan'
            params = self.scan_attributes
        for child in params.child((type_info)).children():
            if type(child.value()) is QDateTime:
                attr[child.name()]=child.value().toString('dd/mm/yyyy HH:MM:ss')
            else:
                attr[child.name()]=child.value()
        if type_info == 'dataset_info':
            #save contents of given parameter object into an xml string under the attribute settings
            settings_str = b'<All_settings title="All Settings" type="group">' + \
                           custom_tree.parameter_to_xml_string(params) + \
                           custom_tree.parameter_to_xml_string(self.settings) + \
                           custom_tree.parameter_to_xml_string(self.dashboard.preset_manager.preset_params)  + b'</All_settings>'

            attr.settings = settings_str


        elif type_info=='scan_info':
            settings_str = b'<All_settings title="All Settings" type="group">' + \
                           custom_tree.parameter_to_xml_string(params) + \
                           custom_tree.parameter_to_xml_string(self.settings) + \
                           custom_tree.parameter_to_xml_string(self.h5saver.settings) + \
                           custom_tree.parameter_to_xml_string(self.scanner.settings) + b'</All_settings>'

            attr.settings = settings_str

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
            if change == 'childAdded':pass

            elif change == 'value':
                pass

            elif change == 'parent':pass

    def set_metadata_about_current_scan(self):
        """
            Set the date/time and author values of the scan_info child of the scan_attributes tree.
            Show the 'scan' file attributes.

            See Also
            --------
            show_file_attributes
        """
        date=QDateTime(QDate.currentDate(),QTime.currentTime())
        self.scan_attributes.child('scan_info','date_time').setValue(date)
        self.scan_attributes.child('scan_info','author').setValue(self.dataset_attributes.child('dataset_info','author').value())
        res = self.show_file_attributes('scan')
        return res

    def set_metadata_about_dataset(self):
        """
            Set the date value of the data_set_info-date_time child of the data_set_attributes tree.
            Show the 'dataset' file attributes.

            See Also
            --------
            show_file_attributes
        """
        date = QDateTime(QDate.currentDate(),QTime.currentTime())
        self.dataset_attributes.child('dataset_info', 'date_time').setValue(date)
        res = self.show_file_attributes('dataset')
        return res

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

            self.settings.child('detectors', 'Detectors').setValue(dict(all_items=items_det, selected=preset_items_det))

        except Exception as e:
            self.update_status(getLineInfo()+str(e), self.wait_time, log_type='log')

    def set_continuous_save(self):
        """
            Set a continous save file using the base path located file with
            a header-name containing date as a string.

            See Also
            --------
            daq_utils.set_current_scan_path
        """
        self.do_continuous_save = True
        self.is_h5_initialized = False
        self.h5saver.settings.child(('base_name')).setValue('Data')
        self.h5saver.settings.child(('N_saved')).show()
        self.h5saver.settings.child(('N_saved')).setValue(0)

        settings_str = b'<All_settings>'
        settings_str += custom_tree.parameter_to_xml_string(self.dashboard.settings)
        settings_str += custom_tree.parameter_to_xml_string(self.dashboard.preset_manager.preset_params)
        if self.dashboard.settings.child('loaded_files', 'overshoot_file').value() != '':
            settings_str += custom_tree.parameter_to_xml_string(self.dashboard.overshoot_manager.overshoot_params)
        if self.dashboard.settings.child('loaded_files', 'roi_file').value() != '':
            settings_str += custom_tree.parameter_to_xml_string(self.dashboard.roi_saver.roi_presets)
        settings_str += custom_tree.parameter_to_xml_string(self.settings)
        settings_str += custom_tree.parameter_to_xml_string(self.h5saver.settings)
        settings_str += b'</All_settings>'

        self.h5saver.init_file(update_h5=True, metadata=dict(settings=settings_str))



        self.h5saver.h5_file.flush()


    def set_logging(self):
        """
        Sets the current scan given the selected settings. Makes some checks, increments the h5 file scans.
        In case the dialog is cancelled, return False and aborts the scan
        """
        try:

            self.set_continuous_save()

            det_names_scan = self.settings.child('detectors', 'Detectors').value()[
                'selected']  # names of all selected detector modules initialized
            det_names = [mod.title for mod in self.detector_modules]
            self.det_modules_log = []  # list of detector modules used for this scan
            for name in det_names_scan:
                self.det_modules_log.append(self.detector_modules[det_names.index(name)])


            #check if the modules are initialized
            for module in self.det_modules_log:
                if not module.initialized_state:
                    raise Exception('module '+module.title+" is not initialized")

            self.ui.start_button.setEnabled(True)
            self.ui.stop_button.setEnabled(True)



            return True

        except Exception as e:
            self.update_status(getLineInfo() + str(e), wait_time=self.wait_time, log_type='log')
            self.ui.start_button.setEnabled(False)
            self.ui.stop_button.setEnabled(False)

    def show_log(self):
        import webbrowser
        webbrowser.open(logging.getLoggerClass().root.handlers[0].baseFilename)

    def setupUI(self):

        self.ui = QObject()

        widget_settings = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()

        widget_settings.setLayout(layout)

        widget_buttons = QtWidgets.QWidget()
        layout_buttons = QtWidgets.QHBoxLayout()
        widget_buttons.setLayout(layout_buttons)
        layout.addWidget(widget_buttons)
        
        iconquit = QtGui.QIcon()
        iconquit.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/close2.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.quit_button = QtWidgets.QPushButton(iconquit, 'Quit')

        iconstart = QtGui.QIcon()
        iconstart.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/run2.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.start_button = QtWidgets.QPushButton(iconstart,'')
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
        self.ui.startall_button = QtWidgets.QPushButton(iconstartall,'')
        self.ui.startall_button.setToolTip('Grab all selected detectors')

        layout_buttons.addWidget(self.ui.quit_button)
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.ui.startall_button)
        layout_buttons.addWidget(log_type_combo)
        layout_buttons.addWidget(self.ui.start_button)
        layout_buttons.addWidget(self.ui.stop_button)


        #%% create logger dock and make it a floating window
        self.ui.logger_dock = Dock("Scan", size=(1, 1), autoOrientation=False)     ## give this dock the minimum possible size
        self.ui.logger_dock.setOrientation('vertical')
        self.ui.logger_dock.addWidget(widget_settings)
        self.dockarea.addDock(self.ui.logger_dock, 'left')
        self.ui.logger_dock.float()

        widget_hor = QtWidgets.QWidget()
        layout_hor = QtWidgets.QHBoxLayout()
        widget_hor.setLayout(layout_hor)
        layout.addWidget(widget_hor)

        self.settings_tree = ParameterTree()
        self.settings_tree.setMinimumWidth(300)
        layout_hor.addWidget(self.settings_tree)
        layout_hor.addWidget(self.h5saver.settings_tree)
        self.h5saver.settings_tree.setMinimumWidth(300)
        self.h5saver.settings.sigTreeStateChanged.connect(self.parameter_tree_changed) #trigger action from "do_save'  boolean
        self.settings = Parameter.create(name='Settings', type='group', children=self.params)
        self.settings_tree.setParameters(self.settings, showTop=False)
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

        # %% init and set the status bar
        self.ui.statusbar = QtWidgets.QStatusBar(self.dockarea)
        self.ui.statusbar.setMaximumHeight(25)
        layout.addWidget(self.ui.statusbar)
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
        layout.addWidget(self.ui.statusbar)


#       connecting
        self.log_signal[str].connect(self.dashboard.add_log)
        self.ui.quit_button.clicked.connect(self.quit_fun)

        self.ui.start_button.clicked.connect(self.start_logging)
        self.ui.stop_button.clicked.connect(self.stop_logging)
        self.ui.startall_button.clicked.connect(self.start_all)

    def get_det_from_preset(self):
        preset_items_det = []
        for det in self.settings.child('detectors', 'Detectors').value()['selected']:
            for module in self.detector_modules:
                if module.title == det:
                    preset_items_det.append(module)
        return preset_items_det

    def start_all(self):
        preset_items_det = self.get_det_from_preset()
        for det in preset_items_det:
            det.ui.grab_pb.click()

    def set_log_type(self, log_type):
        if log_type not in self.log_types:
            raise IOError('Invalid output for the logs')

        self.settings.child(('log_type')).setValue(log_type)

        self.h5saver.settings_tree.setVisible(log_type == 'H5 File')

    def show_file_attributes(self, type_info='dataset'):
        """
            Switch the type_info value.

            In case of :
                * *scan* : Set parameters showing top false
                * *dataset* : Set parameters showing top false
                * *preset* : Set parameters showing top false. Add the save/cancel buttons to the accept/reject dialog (to save preset parameters in a xml file).

            Finally, in case of accepted preset type info, save the preset parameters in a xml file.

            =============== =========== ====================================
            **Parameters**    **Type**    **Description**
            *type_info*       string      The file type information between
                                            * scan
                                            * dataset
                                            * preset
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
        res=dialog.exec()
        return res

    def show_file_content(self):
        try:
            self.h5saver.init_file(addhoc_file_path=self.h5saver.settings.child(('current_h5_file')).value())
            self.h5saver.show_file_content()
        except Exception as e:
            self.update_status(getLineInfo()+ str(e),self.wait_time,log_type='log')

    def start_logging(self):
        """
            Start a logging.
        """
        self.ui.log_message.setText('Starting logging')

        self.overshoot = False
        res = self.set_logging()

        #mandatory to deal with multithreads
        if self.logger_thread is not None:
            self.command_DAQ_signal.disconnect()
            if self.logger_thread.isRunning():
                self.logger_thread.exit()
                while not self.logger_thread.isFinished():
                    QThread.msleep(100)
                self.logger_thread = None

        self.logger_thread = QThread()

        log_acquisition = DAQ_Logging(self.settings, self.h5saver.settings, self.det_modules_log)

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
        preset_items_det = self.get_det_from_preset()
        for det in preset_items_det:
            det.ui.stop_pb.click()

        self.ui.log_message.setText('Stopping acquisition')
        self.command_DAQ_signal.emit(["stop_acquisition"])

        if not self.dashboard.overshoot:
            status = 'Data Acquisition has been stopped by user'
        else:
            status = 'Data Acquisition has been stopped due to overshoot'

        self.update_status(status, log_type='log')
        self.ui.log_message.setText('')
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
            if len(status) > 2:
                self.update_status(status[1], wait_time=self.wait_time, log_type=status[2])
            else:
                self.update_status(status[1], wait_time=self.wait_time)

        elif status[0] == "Timeout":
            self.ui.log_message.setText('Timeout occurred')

    def update_status(self,txt,wait_time=0,log_type=None):
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
            self.ui.statusbar.showMessage(txt,wait_time)
            if log_type is not None:
                self.log_signal.emit(txt)
                logging.info(txt)
        except Exception as e:
            pass


class DAQ_Logging(QObject):
    """
        =========================== ========================================
        **Attributes**               **Type**

        =========================== ========================================

    """
    scan_data_tmp = pyqtSignal(OrderedDict)
    status_sig = pyqtSignal(list)
    def __init__(self, settings=None, h5saver=None, det_modules_log=[]):

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
        self.det_modules_log = det_modules_log
        self.detector_modules_names = [mod.title for mod in self.det_modules_log]
        self.grab_done_signals = [mod.grab_done_signal for mod in self.det_modules_log]
        self.det_modules_settings = [mod.settings for mod in self.det_modules_log]

        self.h5saver = H5Saver()
        self.h5saver.settings.restoreState(h5saver.saveState())
        self.h5saver.init_file(addhoc_file_path=self.h5saver.settings.child(('current_h5_file')).value())
        self.is_h5_initialized = False

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
            self.is_h5_initialized = False
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
            det_group = self.h5saver.get_group_by_title(self.h5saver.raw_group, det_name)
            time_array = self.h5saver.get_node(det_group, 'Logger_x_axis')
            self.h5saver.append(time_array, np.array([datas['acq_time_s']]))

            data_types = ['data0D', 'data1D']
            if self.h5saver.settings.child(('save_2D')).value():
                data_types.extend(['data2D', 'dataND'])

            for data_type in data_types:
                if data_type in datas.keys() and len(datas[data_type]) != 0:
                    if not self.h5saver.is_node_in_group(det_group, data_type):
                        data_group = self.h5saver.add_data_group(det_group, data_type, metadata=dict(type='scan'))
                    else:
                        data_group = self.h5saver.get_node(det_group, utils.capitalize(data_type))
                    for ind_channel, channel in enumerate(datas[data_type]):
                        channel_group = self.h5saver.get_group_by_title(data_group, channel)
                        if channel_group is None:
                            channel_group = self.h5saver.add_CH_group(data_group, title=channel)
                            data_array = self.h5saver.add_data(channel_group, datas[data_type][channel],
                                                               scan_type='scan1D', enlargeable=True)
                        else:
                            data_array = self.h5saver.get_node(channel_group, 'Data')
                        if data_type == 'data0D':
                            self.h5saver.append(data_array, np.array([datas[data_type][channel]['data']]))
                        else:
                            self.h5saver.append(data_array, datas[data_type][channel]['data'])

            self.h5saver.h5_file.flush()
            self.h5saver.settings.child(('N_saved')).setValue(self.h5saver.settings.child(('N_saved')).value()+1)

        except Exception as e:
            self.status_sig.emit(["Update_Status", getLineInfo()+str(e), 'log'])

    def stop_logging(self):
        try:
            for sig in self.grab_done_signals:
                sig.disconnect(self.do_save_continuous)
        except Exception as e:
            pass

        if self.stop_logging_flag:
            status = 'Data Acquisition has been stopped by user'
            self.status_sig.emit(["Update_Status", status, 'log'])

        self.h5saver.h5_file.flush()


    def start_logging(self):
        try:

            for det in self.det_modules_log:
                if not self.h5saver.is_node_in_group(self.h5saver.raw_group, det.title):
                    settings_str = b'<All_settings>'
                    settings_str += custom_tree.parameter_to_xml_string(det.settings)
                    for viewer in det.ui.viewers:
                        if hasattr(det.ui.viewers[0], 'roi_manager'):
                            settings_str += custom_tree.parameter_to_xml_string(det.ui.viewers[0].roi_manager.settings)
                    settings_str += b'</All_settings>'

                    det_group = self.h5saver.add_det_group(self.h5saver.raw_group, det.title, settings_str)
                    self.h5saver.add_navigation_axis(np.array([0.0, ]),
                          det_group, 'x_axis', enlargeable=True,
                          title='Time axis', metadata=dict(label='Time axis', units='timestamp'))


            for sig in self.grab_done_signals:
                sig.connect(self.do_save_continuous)

            self.stop_logging_flag = False
            self.status_sig.emit(["Update_Status", "Acquisition has started", 'log'])
            self.det_done_flag = False

            # for det in self.det_modules_log:
            #     det.ui.grab_pb.click()

        except Exception as e:
            self.status_sig.emit(["Update_Status", getLineInfo() + str(e), 'log'])




if __name__ == '__main__':
    from pymodaq.dashboard import DashBoard

    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = gutils.DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    # win.setVisible(False)
    prog = DashBoard(area)
    prog.set_preset_mode('C:\\Users\\weber\\pymodaq_local\\preset_modes\\preset_logger.xml')
    # QThread.msleep(4000)

    prog.load_log_module()
    sys.exit(app.exec_())
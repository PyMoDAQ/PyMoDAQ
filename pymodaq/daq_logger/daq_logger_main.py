#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Automated scanning module functionalities for PyMoDAQ

Contains all objects related to the DAQ_Scan module, to do automated scans, saving data...
"""

import sys
from collections import OrderedDict
import numpy as np
from pathlib import Path
import datetime
import time
import os
import logging

from pyqtgraph.dockarea import Dock
from pyqtgraph.parametertree import Parameter, ParameterTree
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QTimer, QDateTime, QDate, QTime

from pymodaq.daq_utils.daq_utils import getLineInfo
from pymodaq.daq_scan.gui.daq_scan_gui import Ui_Form
from pymodaq.version import get_version
import pymodaq.daq_utils.custom_parameter_tree as custom_tree# to be placed after importing Parameter
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D
from pymodaq.daq_utils.plotting.viewer1D.viewer1D_main import Viewer1D
from pymodaq.daq_utils.plotting.navigator import Navigator
from pymodaq.daq_utils.scanner import Scanner
from pymodaq.daq_move.daq_move_main import DAQ_Move
from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer
from pymodaq.daq_utils.plotting.qled import QLED
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils.h5saver import H5Saver


class DAQ_Logger(QObject):
    """
    Main class initializing a DAQ_Scan module with its dashboard and scanning control panel
    """
    command_DAQ_signal = pyqtSignal(list)
    log_signal = pyqtSignal(str)

    params = [
        {'title': 'Log Type:', 'name': 'log_type', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Loaded presets', 'name': 'loaded_files', 'type': 'group', 'children': [
            {'title': 'Preset file', 'name': 'preset_file', 'type': 'str', 'value': '', 'readonly': True},
            {'title': 'Overshoot file', 'name': 'overshoot_file', 'type': 'str', 'value': '', 'readonly': True},
            {'title': 'Layout file', 'name': 'layout_file', 'type': 'str', 'value': '', 'readonly': True},
        ]},
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

        self.log_types = ['H5 File', 'SQL DataBase']

        self.h5saver = H5Saver()
        #self.h5saver.settings.child(('do_save')).hide()
        #self.h5saver.settings.child(('custom_name')).hide()
        self.h5saver.new_file_sig.connect(self.create_new_file)
        self.is_h5_initialized = False


        self.setupUI()
        self.setup_modules(self.dashboard.title)

    def set_continuous_save(self):
        """
            Set a continous save file using the base path located file with
            a header-name containing date as a string.

            See Also
            --------
            daq_utils.set_current_scan_path
        """
        if self.h5saver.settings.child(('do_save')).value():
            self.do_continuous_save = True
            self.is_h5_initialized = False
            self.h5saver.settings.child(('base_name')).setValue('Data')
            self.h5saver.settings.child(('N_saved')).show()
            self.h5saver.settings.child(('N_saved')).setValue(0)
            self.h5saver.init_file(update_h5=True)

            settings_str = b'<All_settings>' + custom_tree.parameter_to_xml_string(self.settings)
            if hasattr(self.ui.viewers[0], 'roi_manager'):
                settings_str += custom_tree.parameter_to_xml_string(self.ui.viewers[0].roi_manager.settings)
            settings_str += custom_tree.parameter_to_xml_string(self.h5saver.settings)
            settings_str += b'</All_settings>'

            self.continuous_group = self.h5saver.add_det_group(self.h5saver.raw_group, "Continuous saving", settings_str)
            self.h5saver.h5_file.flush()
        else:
            self.do_continuous_save=False
            self.h5saver.settings.child(('N_saved')).hide()

            try:
                self.h5saver.close()
            except Exception as e:
                pass

    def do_save_continuous(self, datas):
        """
        method used to perform continuous saving of data, for instance for logging. Will save datas as a function of
        time in a h5 file set when *continuous_saving* parameter as been set.

        Parameters
        ----------
        datas:  list of OrderedDict as exported by detector plugins

        """
        try:
            #init the enlargeable arrays
            if not self.is_h5_initialized:
                self.channel_arrays = OrderedDict([])
                self.ini_time = time.perf_counter()
                self.time_array = self.h5saver.add_navigation_axis(np.array([0.0, ]),
                              self.h5saver.raw_group, 'x_axis', enlargeable=True,
                              title='Time axis', metadata=dict(label='Time axis', units='second'))

                data_types = ['data0D', 'data1D']
                if self.h5saver.settings.child(('save_2D')).value():
                    data_types.append('data2D')

                for data_type in data_types:
                    if data_type in datas.keys() and len(datas[data_type]) != 0:
                        if not self.h5saver.is_node_in_group(self.continuous_group, data_type):
                            self.channel_arrays[data_type] = OrderedDict([])

                            data_group=self.h5saver.add_data_group(self.continuous_group, data_type)
                            for ind_channel, channel in enumerate(datas[data_type]): #list of OrderedDict

                                channel_group = self.h5saver.add_CH_group(data_group, title=channel)
                                self.channel_arrays[data_type]['parent'] = channel_group
                                self.channel_arrays[data_type][channel] = self.h5saver.add_data(channel_group,
                                        datas[data_type][channel], scan_type='scan1D', enlargeable = True)
                self.is_h5_initialized = True

            dt=np.array([time.perf_counter()-self.ini_time])
            self.h5saver.append(self.time_array,dt)

            data_types = ['data0D', 'data1D']
            if self.h5saver.settings.child(('save_2D')).value():
                data_types.append('data2D')

            for data_type in data_types:
                if data_type in datas.keys() and len(datas[data_type]) != 0:
                    for ind_channel, channel in enumerate(datas[data_type]):
                        self.h5saver.append(self.channel_arrays[data_type][channel],
                                                  datas[data_type][channel]['data'])

            self.h5saver.h5_file.flush()
            self.h5saver.settings.child(('N_saved')).setValue(self.h5saver.settings.child(('N_saved')).value()+1)

        except Exception as e:
            self.update_status(getLineInfo()+ str(e),self.wait_time,'log')

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
        except Exception as e:
            pass

    def save_file(self):
        if not os.path.isdir(self.h5saver.settings.child(('base_path')).value()):
            os.mkdir(self.h5saver.settings.child(('base_path')).value())
        filename = utils.select_file(self.h5saver.settings.child(('base_path')).value(), save=True, ext='h5')
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
                if param.name() == 'do_save':
                    self.set_continuous_save()

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
            self.settings.child('loaded_files', 'preset_file').setValue(os.path.split(filename)[1])

            ######################################################################
            # setting moves and det in tree
            preset_items_det = []
            items_det = [module.title for module in self.detector_modules]
            if items_det != []:
                preset_items_det = [items_det[0]]

            self.settings.child('detectors', 'Detectors').setValue(dict(all_items=items_det, selected=preset_items_det))

            self.create_new_file(True)


        except Exception as e:
            self.update_status(getLineInfo()+str(e), self.wait_time, log_type='log')

    def create_new_file(self, new_file):
        self.h5saver.init_file(update_h5=new_file)
        res = self.update_file_settings(new_file)
        if new_file:
            pass
        return res

    def set_scan(self):
        """
        Sets the current scan given the selected settings. Makes some checks, increments the h5 file scans.
        In case the dialog is cancelled, return False and aborts the scan
        """
        try:
            # set the filename and path
            res = self.create_new_file(False)
            if not res:
                return

            #reinit these objects
            self.scan_data_1D = []
            self.scan_data_1D_average = []
            self.scan_data_2D = []
            self.scan_data_2D_average = []


            scan_path=Path(self.h5saver.settings.child(('current_scan_path')).value())
            current_filename=self.h5saver.settings.child(('current_scan_name')).value()
            # set the moves positions according to data from user
            move_names_scan=self.settings.child('detectors', 'Moves').value()['selected'] #selected move modules names
            move_names=[mod.title for mod in self.move_modules] # names of all move modules initialized
            self.move_modules_scan=[] #list of move modules used for this scan
            for name in move_names_scan:
                self.move_modules_scan.append(self.move_modules[move_names.index(name)])#create list of modules used for this current scan

            det_names_scan=self.settings.child('detectors', 'Detectors').value()['selected']# names of all selected detector modules initialized
            det_names=[mod.title for mod in self.detector_modules]
            self.det_modules_scan=[]#list of detector modules used for this scan
            for name in det_names_scan:
                self.det_modules_scan.append(self.detector_modules[det_names.index(name)])

            self.scan_saves=[]

            self.scan_parameters = self.scanner.set_scan()

            if self.scanner.settings.child('scan_options','scan_type').value() == "Scan1D":
                if self.scanner.settings.child('scan_options','scan1D_settings','scan1D_selection').value() == 'Manual':
                    Nmove_module = 1
                else:  # from ROI
                    Nmove_module = 2
                if len(move_names_scan) != Nmove_module:
                    msgBox = QtWidgets.QMessageBox(parent=None)
                    msgBox.setWindowTitle("Error")
                    msgBox.setText("There are not enough or too much selected move modules")
                    ret = msgBox.exec()
                    return

                self.scan_moves = [[[move_names_scan[ind_pos], pos[ind_pos]] for ind_pos in range(Nmove_module)] for
                                   pos in self.scan_parameters.positions]
                ###############################
                #old stuff when all data where saved in separated files but still needed to perform the scan (only the paths are not)
                for ind,pos in enumerate(self.scan_moves):
                    self.scan_saves.append([OrderedDict(det_name=det_name,file_path=str(scan_path.joinpath(current_filename+"_"+det_name+'_{:03d}.h5'.format(ind))),indexes=OrderedDict(indx=ind)) for det_name in det_names_scan])


            elif self.scanner.settings.child('scan_options','scan_type').value() == "Scan2D":
                Nmove_module = 2
                if len(move_names_scan) < Nmove_module:
                    msgBox = QtWidgets.QMessageBox(parent=None)
                    msgBox.setWindowTitle("Error")
                    msgBox.setText("There are not enough selected move modules")
                    ret = msgBox.exec();
                    return
                self.scan_moves = [[[move_names_scan[ind_pos], pos[ind_pos]] for ind_pos in range(Nmove_module)] for
                                   pos in self.scan_parameters.positions]
                for ind,pos in enumerate(self.scan_moves):
                    ind1=self.scan_parameters.axis_2D_1_indexes[ind]
                    ind2=self.scan_parameters.axis_2D_2_indexes[ind]
                    self.scan_saves.append([OrderedDict(det_name=det_name,file_path=str(scan_path.joinpath(current_filename+"_"+det_name+'_{:03d}_{:03d}.h5'.format(ind1,ind2))),indexes=OrderedDict(indx=ind1,indy=ind2)) for det_name in det_names_scan])



            self.ui.N_scan_steps_sb.setValue(self.scan_parameters.Nsteps)



            #check if the modules are initialized

            for module in self.move_modules_scan:
                if not module.initialized_state:
                    raise Exception('module '+module.title+" is not initialized")

            for module in self.det_modules_scan:
                if not module.initialized_state:
                    raise Exception('module '+module.title+" is not initialized")

            self.ui.start_button.setEnabled(True)
            self.ui.stop_button.setEnabled(True)



            return True

        except Exception as e:
            self.update_status(getLineInfo()+ str(e),wait_time=self.wait_time,log_type='log')
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

        layout_buttons.addWidget(self.ui.quit_button)
        layout_buttons.addStretch()
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

        self.ui.start_button.clicked.connect(self.start_scan)
        self.ui.stop_button.clicked.connect(self.stop_scan)

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

    def start_scan(self):
        """
            Start an acquisition calling the set_scan function.
            Emit the command_DAQ signal "start_acquisition".

            See Also
            --------
            set_scan
        """
        self.ui.log_message.setText('Starting acquisition')
        self.overshoot = False
        self.plot_2D_ini=False
        self.plot_1D_ini = False
        res = self.set_scan()
        if res:

            # save settings from move modules
            move_modules_names = [mod.title for mod in self.move_modules_scan]
            for ind_move, move_name in enumerate(move_modules_names):
                move_group_name = 'Move{:03d}'.format(ind_move)
                if not self.h5saver.is_node_in_group(self.h5saver.current_scan_group, move_group_name):
                    self.h5saver.add_move_group(self.h5saver.current_scan_group, title='',
                                                                           settings_as_xml=custom_tree.parameter_to_xml_string(
                                                                               self.move_modules_scan[ind_move].settings),
                                                                           metadata=dict(name=move_name))

            # save settings from detector modules
            detector_modules_names = [mod.title for mod in self.det_modules_scan]
            for ind_det, det_name in enumerate(detector_modules_names):
                det_group_name = 'Detector{:03d}'.format(ind_det)
                if not self.h5saver.is_node_in_group(self.h5saver.current_scan_group, det_group_name):
                    settings_str = custom_tree.parameter_to_xml_string(self.det_modules_scan[ind_det].settings)
                    try:
                        if 'Data0D' not in [viewer.viewer_type for viewer in
                                            self.det_modules_scan[ind_det].ui.viewers]:  # no roi_settings in viewer0D
                            settings_str = b'<All_settings title="All Settings" type="group">' + settings_str
                            for ind_viewer, viewer in enumerate(self.det_modules_scan[ind_det].ui.viewers):
                                if hasattr(viewer, 'roi_manager'):
                                    settings_str += '<Viewer{:0d}_ROI_settings title="ROI Settings" type="group">'.format(
                                        ind_viewer).encode()
                                    settings_str += custom_tree.parameter_to_xml_string(
                                        viewer.roi_manager.settings) + '</Viewer{:0d}_ROI_settings>'.format(ind_viewer).encode()
                            settings_str += b'</All_settings>'
                    except Exception as e:
                        self.update_status(getLineInfo() + str(e), wait_time=self.wait_time, log_type='log')

                    self.h5saver.add_det_group(self.h5saver.current_scan_group,
                                                                         settings_as_xml=settings_str,
                                                                         metadata=dict(name=det_name))


            #mandatory to deal with multithreads
            if self.logger_thread is not None:
                self.command_DAQ_signal.disconnect()
                if self.logger_thread.isRunning():
                    self.logger_thread.exit()
                    while not self.logger_thread.isFinished():
                        QThread.msleep(100)
                    self.logger_thread = None

            self.logger_thread = QThread()

            scan_acquisition = DAQ_Scan_Acquisition(self.settings, self.scanner.settings, self.h5saver.settings,
                            self.scan_moves,
                            self.scan_saves,
                            [mod.command_stage for mod in self.move_modules_scan],
                            [mod.command_detector for mod in self.det_modules_scan],
                            [mod.move_done_signal for mod in self.move_modules_scan],
                            [mod.grab_done_signal for mod in self.det_modules_scan],
                            [mod.settings.child('main_settings', 'Naverage').value() for mod in self.det_modules_scan],
                            move_modules_names,
                            detector_modules_names,
                             [mod.settings for mod in self.move_modules_scan],
                             [mod.settings for mod in self.det_modules_scan],
                             )
            scan_acquisition.moveToThread(self.logger_thread)

            self.command_DAQ_signal[list].connect(scan_acquisition.queue_command)
            scan_acquisition.scan_data_tmp[OrderedDict].connect(self.update_scan_GUI)
            scan_acquisition.status_sig[list].connect(self.thread_status)

            self.logger_thread.scan_acquisition = scan_acquisition
            self.logger_thread.start()

            self.ui.set_scan_pb.setEnabled(False)
            self.ui.set_ini_positions_pb.setEnabled(False)
            self.ui.start_button.setEnabled(False)
            QtWidgets.QApplication.processEvents()
            self.ui.scan_done_LED.set_as_false()



            self.command_DAQ_signal.emit(["start_acquisition"])

            self.ui.log_message.setText('Running acquisition')

    def stop_scan(self):
        """
            Emit the command_DAQ signal "stop_acquisiion".

            See Also
            --------
            set_ini_positions
        """
        self.ui.log_message.setText('Stoping acquisition')
        self.command_DAQ_signal.emit(["stop_acquisition"])

        if not self.dashboard.overshoot:
            self.set_ini_positions() #do not set ini position again in case overshoot fired
            status = 'Data Acquisition has been stopped by user'
        else:
            status = 'Data Acquisition has been stopped due to overshoot'

        self.update_status(status, log_type='log')
        self.ui.log_message.setText('')

        self.ui.set_scan_pb.setEnabled(True)
        self.ui.set_ini_positions_pb.setEnabled(True)
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


class DAQ_Scan_Acquisition(QObject):
    """
        =========================== ========================================
        **Attributes**               **Type**
        *scan_data_tmp*              instance of pyqtSignal
        *status_sig*                 instance of pyqtSignal
        *stop_scan_flag*             boolean
        *settings*                   instance og pyqtgraph.parametertree
        *filters*                    instance of tables.Filters
        *ind_scan*                   int
        *detector_modules*           Object list
        *detector_modules_names*     string list
        *move_modules*               Object list
        *move_modules_names*         string list
        *scan_moves*                 float list
        *scan_x_axis*                float array
        *scan_y_axis*                float array
        *scan_z_axis*                float array
        *scan_x_axis_unique*         float array
        *scan_y_axis_unique*         float array
        *scan_z_axis_unique*         float array
        *scan_shape*                 int
        *Nscan_steps*                int
        *scan_read_positions*        list
        *scan_read_datas*            list
        *scan_saves*                 dictionnary list
        *move_done_flag*             boolean
        *det_done_flag*              boolean
        *timeout_scan_flag*          boolean
        *timer*                      instance of QTimer
        *move_done_positions*        OrderedDict
        *det_done_datas*             OrderedDict
        *h5_file*                    instance class File from tables module
        *h5_file_current_group*      instance of Group
        *h5_file_det_groups*         Group list
        *h5_file_move_groups*        Group list
        *h5_file_channels_group*     Group dictionnary
        =========================== ========================================

    """
    scan_data_tmp=pyqtSignal(OrderedDict)
    status_sig = pyqtSignal(list)
    def __init__(self,settings=None,scan_settings = None, h5saver=None,
                 scan_moves=[],scan_saves=[],
                 move_modules_commands = [],
                 detector_modules_commands = [],
                 move_done_signals = [] ,
                 grab_done_signals = [],
                 det_averaging = [],
                 move_modules_name = [],
                 det_modules_name = [],
                 move_modules_settings = [],
                 det_modules_settings = []):

        """
            DAQ_Scan_Acquisition deal with the acquisition part of daq_scan.

            See Also
            --------
            custom_tree.parameter_to_xml_string
        """
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(QObject, self).__init__()

        self.stop_scan_flag = False
        self.settings = settings
        self.scan_settings = scan_settings
        self.Naverage = self.settings.child('scan_options', 'scan_average').value()
        self.ind_average = 0
        self.ind_scan = 0

        self.detector_modules_names = det_modules_name

        self.move_modules_names = move_modules_name
        self.move_modules_commands = move_modules_commands
        self.detector_modules_commands = detector_modules_commands
        self.grab_done_signals = grab_done_signals
        self.move_done_signals = move_done_signals
        self.det_averaging = det_averaging
        self.move_modules_settings = move_modules_settings
        self.det_modules_settings = det_modules_settings

        self.scan_moves = scan_moves
        self.scan_x_axis = None
        self.scan_y_axis = None
        self.scan_z_axis = None
        self.scan_x_axis_unique = None
        self.scan_y_axis_unique = None
        self.scan_z_axis_unique = None
        self.scan_shape = None
        self.Nscan_steps = len(scan_moves)
        self.scan_read_positions = []
        self.scan_read_datas = []
        self.scan_saves = scan_saves
        self.move_done_flag = False
        self.det_done_flag = False
        self.timeout_scan_flag = False
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timeout)
        self.move_done_positions = OrderedDict()
        self.det_done_datas = OrderedDict()
        self.h5saver = H5Saver()
        self.h5saver.settings.restoreState(h5saver.saveState())
        self.h5saver.init_file(addhoc_file_path=self.h5saver.settings.child(('current_h5_file')).value())

        self.h5_det_groups = []
        self.h5_move_groups = []
        self.channel_arrays = OrderedDict([])
        # save settings from move modules
        for ind_move, move_name in enumerate(self.move_modules_names):
            move_group_name = 'Move{:03d}'.format(ind_move)
            self.h5_move_groups.append(self.h5saver.h5_file.get_node(self.h5saver.current_scan_group, move_group_name))

        #save settings from detector modules
        for ind_det,det_name in enumerate(self.detector_modules_names):
            det_group_name = 'Detector{:03d}'.format(ind_det)
            self.h5_det_groups.append(self.h5saver.h5_file.get_node(self.h5saver.current_scan_group, det_group_name))

    @pyqtSlot(list)
    def queue_command(self,command):
        """
            Treat the queue of commands from the current command to act, between :
                * *start_acquisition*
                * *stop_acquisition*
                * *set_ini_position*
                * *move_stages*

            =============== ============== =========================
            **Parameters**    **Type**      **Description**
            command           string list   the command string list
            =============== ============== =========================

            See Also
            --------
            start_acquisition, set_ini_positions, move_stages
        """
        if command[0]=="start_acquisition":
            self.start_acquisition()


        elif command[0]=="stop_acquisition":
            self.stop_scan_flag=True

        elif command[0]=="set_ini_positions":
            self.set_ini_positions()

        elif command[0]=="move_stages":
            self.move_stages(command[1])

    def set_ini_positions(self):
        """
            | Set the positions from the scan_move attribute.
            |
            | Move all activated modules to specified positions.
            | Check the module corresponding to the name assigned in pos.

            See Also
            --------
            DAQ_Move_main.daq_move.move_Abs
        """
        try:
            positions=self.scan_moves[0]
            for ind_move,pos in enumerate(positions): #move all activated modules to specified positions
                # if pos[0]!=self.move_modules[ind_move].title: # check the module correspond to the name assigned in pos
                #     raise Exception('wrong move module assignment')
                #self.move_modules[ind_move].move_Abs(pos[1])
                self.move_modules_commands[ind_move].emit(utils.ThreadCommand(command="move_Abs", attributes=[pos[1]]))

        except Exception as e:
            self.status_sig.emit(["Update_Status",getLineInfo()+ str(e),'log'])

    pyqtSlot(str,float)
    def move_done(self,name,position):
        """
            | Update the move_done_positions attribute if needed.
            | If position attribute is setted, for all move modules launched, update scan_read_positions with a [modulename, position] list.

            ============== ============ =================
            **Parameters**    **Type**    **Description**
            *name*            string     the module name
            *position*        float      ???
            ============== ============ =================
        """
        try:
            if name not in list(self.move_done_positions.keys()):
                self.move_done_positions[name]=position

            if len(self.move_done_positions.items())==len(self.move_modules_names):


                list_tmp=[]
                for name_tmp in self.move_modules_names:
                    list_tmp.append([name_tmp,self.move_done_positions[name_tmp]])
                self.scan_read_positions=list_tmp

                self.move_done_flag=True
                #print(self.scan_read_positions[-1])
        except Exception as e:
            self.status_sig.emit(["Update_Status",getLineInfo()+ str(e),'log'])

    def init_data(self):
        self.channel_arrays = OrderedDict([])
        for ind_det, det_name in enumerate(self.detector_modules_names):
            datas = self.det_done_datas[det_name]
            det_group = self.h5_det_groups[ind_det]
            self.channel_arrays[det_name] = OrderedDict([])
            data_types = ['data0D', 'data1D']
            if self.h5saver.settings.child(('save_2D')).value():
                data_types.extend(['data2D', 'dataND'])

            for data_type in data_types:
                if data_type in datas.keys():
                    if datas[data_type] is not None:
                        if len(datas[data_type]) != 0:
                            data_raw_roi = [datas[data_type][key]['type'] for key in datas[data_type]]
                            if not (self.h5saver.settings.child(('save_raw_only')).value() and 'raw' not in data_raw_roi):
                                if not self.h5saver.is_node_in_group(det_group, data_type):
                                    self.channel_arrays[det_name][data_type] = OrderedDict([])

                                    data_group = self.h5saver.add_data_group(det_group, data_type)
                                    for ind_channel, channel in enumerate(datas[data_type]):  # list of OrderedDict
                                        if not(self.h5saver.settings.child(('save_raw_only')).value() and datas[data_type][channel]['type'] != 'raw'):
                                            channel_group = self.h5saver.add_CH_group(data_group, title=channel)
                                            self.channel_arrays[det_name][data_type]['parent'] = channel_group
                                            self.channel_arrays[det_name][data_type][channel] = self.h5saver.add_data(channel_group,
                                                        datas[data_type][channel],
                                                        scan_type=self.scan_settings.child('scan_options', 'scan_type').value(),
                                                        scan_shape=self.scan_shape, init=True, add_scan_dim=True)
            pass

    pyqtSlot(OrderedDict) #edict(name=self.title,data0D=None,data1D=None,data2D=None)
    def det_done(self,data):
        """
            | Initialize 0D/1D/2D datas from given data parameter.
            | Update h5_file group and array.
            | Save 0D/1D/2D datas.

            =============== ============================== ======================================
            **Parameters**    **Type**                      **Description**
            *data*          Double precision float array   The initializing data of the detector
            =============== ============================== ======================================
        """
        try:
            if data['name'] not in list(self.det_done_datas.keys()):
                self.det_done_datas[data['name']]=data
            if len(self.det_done_datas.items())==len(self.detector_modules_names):

                self.scan_read_datas=self.det_done_datas[self.settings.child('scan_options','plot_from').value()].copy()

                if self.ind_scan == 0 and self.ind_average == 0:#first occurence=> initialize the channels
                    self.init_data()

                if len(self.scan_saves[self.ind_scan][0]['indexes'])==1:
                    indexes=[self.scan_saves[self.ind_scan][0]['indexes']['indx']]
                elif len(self.scan_saves[self.ind_scan][0]['indexes'])==2:
                    indexes=[self.scan_saves[self.ind_scan][0]['indexes']['indx'],self.scan_saves[self.ind_scan][0]['indexes']['indy']]
                else:
                    raise Exception('Wrong indexes dimensionality')

                if self.Naverage > 1:
                    indexes.append(self.ind_average)

                indexes=tuple(indexes)

                for ind_det, det_name in enumerate(self.detector_modules_names):
                    datas = self.det_done_datas[det_name]

                    data_types = ['data0D', 'data1D']
                    if self.h5saver.settings.child(('save_2D')).value():
                        data_types.extend(['data2D', 'dataND'])


                    for data_type in data_types:
                        if data_type in datas.keys():
                            if datas[data_type] is not None:
                                if len(datas[data_type]) != 0:
                                    for ind_channel, channel in enumerate(datas[data_type]):
                                        if not(self.h5saver.settings.child(('save_raw_only')).value() and datas[data_type][channel]['type'] != 'raw'):
                                            self.channel_arrays[det_name][data_type][channel].__setitem__(indexes,
                                                value=self.det_done_datas[det_name][data_type][channel]['data'])

                self.det_done_flag=True

                self.scan_data_tmp.emit(OrderedDict(positions=self.scan_read_positions,datas=self.scan_read_datas))
        except Exception as e:
            self.status_sig.emit(["Update_Status",getLineInfo()+ str(e),'log'])

    def timeout(self):
        """
            Send the status signal *'Time out during acquisition'* and stop the timer.
        """
        self.timeout_scan_flag=True
        self.timer.stop()
        self.status_sig.emit(["Update_Status","Timeout during acquisition",'log'])
        self.status_sig.emit(["Timeout"])

    def move_stages(self,positions):
        """
            Move all the activated modules to the specified positions.

            =============== ============ =============================================
            **Parameters**    **Type**    **Description**
            *positions*       tuple list  The list of the positions related to indices
            =============== ============ =============================================

            See Also
            --------
            DAQ_Move_main.daq_move.move_Abs, move_done, det_done, wait_for_move_done, wait_for_det_done, det_done
        """
        for ind_move,pos in enumerate(positions): #move all activated modules to specified positions
            #self.move_modules[ind_move].move_Abs(pos)
            self.move_modules_commands[ind_move].emit(utils.ThreadCommand(command="move_Abs", attributes=[pos]))

    def start_acquisition(self):
        try:


            status=''
            # for mod in self.move_modules:
            #     mod.move_done_signal.connect(self.move_done)
            # for mod in self.detector_modules:
            #     mod.grab_done_signal.connect(self.det_done)

            for sig in self.move_done_signals:
                sig.connect(self.move_done)
            for sig in self.grab_done_signals:
                sig.connect(self.det_done)

            self.scan_read_positions=[]
            self.scan_read_datas=[]
            self.stop_scan_flag=False
            Naxis=len(self.scan_moves[0])


            self.scan_x_axis=np.array([pos[0][1] for pos in self.scan_moves])
            self.scan_x_axis_unique=np.unique(self.scan_x_axis)

            if not self.h5saver.is_node_in_group(self.h5saver.current_scan_group, 'scan_x_axis'):
                x_axis_meta = dict(units=self.move_modules_settings[0].child('move_settings', 'units').value(),
                              label=self.move_modules_names[0])
                self.h5saver.add_navigation_axis(self.scan_x_axis, self.h5saver.current_scan_group, axis='x_axis', metadata=x_axis_meta)

            if self.scan_settings.child('scan_options','scan_type').value() == 'Scan1D': #"means scan 1D"
                if self.scan_settings.child('scan_options','scan1D_settings','scan1D_type').value()=='Linear back to start':
                    self.scan_shape=[len(self.scan_x_axis)]

                else:
                    self.scan_shape=[len(self.scan_x_axis_unique)]
                if Naxis == 2: #means 1D scan along a line in a 2D plane
                    self.scan_y_axis = np.array([pos[1][1] for pos in self.scan_moves])
                    if not self.h5saver.is_node_in_group(self.h5saver.current_scan_group, 'scan_y_axis'):
                        y_axis_meta = dict(units=self.move_modules_settings[1].settings.child('move_settings', 'units').value(),
                                      label=self.move_modules_names[1])

                        self.h5saver.add_navigation_axis(self.scan_y_axis, self.h5saver.current_scan_group,
                                                         axis='y_axis', metadata=y_axis_meta)
                    self.scan_y_axis_unique = np.unique(self.scan_y_axis)

            else:
                self.scan_shape=[len(self.scan_x_axis_unique)]

            if self.scan_settings.child('scan_options','scan_type').value() == 'Scan2D':#"means scan 2D"
                self.scan_y_axis=np.array([pos[1][1] for pos in self.scan_moves])
                self.scan_y_axis_unique=np.unique(self.scan_y_axis)
                if not self.h5saver.is_node_in_group(self.h5saver.current_scan_group, 'scan_y_axis'):
                    y_axis_meta = dict(units=self.move_modules_settings[1].child('move_settings', 'units').value(),
                                  label=self.move_modules_names[1])
                    self.h5saver.add_navigation_axis(self.scan_y_axis, self.h5saver.current_scan_group,
                    axis='y_axis', metadata=y_axis_meta)
                self.scan_shape.append(len(self.scan_y_axis_unique))
            elif Naxis>2:#"means scan 3D" not implemented yet
                pass

            if self.Naverage > 1:
                self.scan_shape.append(self.Naverage)

            self.status_sig.emit(["Update_Status","Acquisition has started",'log'])

            for ind_average in range(self.Naverage):
                self.ind_average=ind_average
                for ind_scan,positions in enumerate(self.scan_moves): #move motors of modules
                    self.ind_scan=ind_scan
                    self.status_sig.emit(["Update_scan_index",[ind_scan,ind_average]])
                    if self.stop_scan_flag or  self.timeout_scan_flag:

                        break
                    self.move_done_positions=OrderedDict()
                    self.move_done_flag=False
                    for ind_move,pos in enumerate(positions): #move all activated modules to specified positions
                        # if pos[0]!=self.move_modules[ind_move].title: # check the module correspond to the name assigned in pos
                        #     raise Exception('wrong move module assignment')
                        #self.move_modules[ind_move].move_Abs(pos[1])
                        self.move_modules_commands[ind_move].emit(utils.ThreadCommand(command="move_Abs",attributes=[pos[1]]))

                    self.wait_for_move_done()

                    paths =self.scan_saves[ind_scan] #start acquisition
                    if self.stop_scan_flag or  self.timeout_scan_flag:
                        if self.stop_scan_flag:
                            status='Data Acquisition has been stopped by user'
                            self.status_sig.emit(["Update_Status",status,'log'])
                        break
                    self.det_done_flag=False
                    self.det_done_datas=OrderedDict()
                    for ind_det, path in enumerate(paths): #path on the form edict(det_name=...,file_path=...,indexes=...)
                        # if path['det_name']!=self.detector_modules[ind_det].title: # check the module correspond to the name assigned in path
                        #     raise Exception('wrong det module assignment')
                        #self.detector_modules[ind_det].snapshot(str(path['file_path']),dosave=False) #do not save each grabs in independant files
                        self.detector_modules_commands[ind_det].emit(utils.ThreadCommand("single",
                                  [self.det_averaging[ind_det],str(path['file_path'])]))
                    self.wait_for_det_done()
            self.h5saver.h5_file.flush()
            for sig in self.move_done_signals:
                sig.disconnect(self.move_done)
            for sig in self.grab_done_signals:
                sig.disconnect(self.det_done)

            # for mod in self.move_modules:
            #     mod.move_done_signal.disconnect(self.move_done)
            # for mod in self.detector_modules:
            #     mod.grab_done_signal.disconnect(self.det_done)
            self.status_sig.emit(["Update_Status","Acquisition has finished",'log'])
            self.status_sig.emit(["Scan_done"])

            self.timer.stop()
        except Exception as e:
            self.status_sig.emit(["Update_Status",getLineInfo()+ str(e),'log'])

    def wait_for_det_done(self):
        self.timeout_scan_flag=False
        self.timer.start(self.settings.child('time_flow','timeout').value())
        while not(self.det_done_flag or  self.timeout_scan_flag):
            #wait for grab done signals to end
            QtWidgets.QApplication.processEvents()

    def wait_for_move_done(self):
        self.timeout_scan_flag=False
        self.timer.start(self.settings.child('time_flow','timeout').value())


        while not(self.move_done_flag or  self.timeout_scan_flag):
            #wait for move done signals to end
            QtWidgets.QApplication.processEvents()





if __name__ == '__main__':
    from pymodaq.daq_utils.dashboard import DashBoard

    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = utils.DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    # win.setVisible(False)
    prog = DashBoard(area)
    sys.exit(app.exec_())

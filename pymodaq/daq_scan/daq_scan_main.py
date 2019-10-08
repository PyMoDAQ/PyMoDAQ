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
import pickle
import os
import logging

from pyqtgraph.dockarea import Dock
from pyqtgraph.parametertree import Parameter, ParameterTree
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QTimer, QDateTime, QDate, QTime

from pymodaq.daq_utils.daq_utils import getLineInfo
from pymodaq.daq_utils.pid.pid_controller import DAQ_PID
from pymodaq.daq_scan.gui.daq_scan_gui import Ui_Form
from pymodaq.version import get_version
import pymodaq.daq_utils.custom_parameter_tree as custom_tree# to be placed after importing Parameter
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D
from pymodaq.daq_utils.plotting.viewer1D.viewer1D_main import Viewer1D
from pymodaq.daq_utils.plotting.navigator import Navigator
from pymodaq.daq_utils.manage_preset import PresetManager
from pymodaq.daq_utils.overshoot_manager import OvershootManager
from pymodaq.daq_utils.scanner import Scanner
from pymodaq.daq_move.daq_move_main import DAQ_Move
from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer
from pymodaq.daq_utils.plotting.qled import QLED
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils.h5saver import H5Saver

local_path = utils.get_set_local_dir()
now=datetime.datetime.now()
log_path=os.path.join(local_path,'logging')
if not os.path.isdir(log_path):
    os.makedirs(log_path)

layout_path = os.path.join(local_path,'layout')
if not os.path.isdir(layout_path):
    os.makedirs(layout_path)

overshoot_path= os.path.join(local_path, 'overshoot_configurations')
if not os.path.isdir(overshoot_path):
    os.makedirs(overshoot_path)

logging.basicConfig(filename=os.path.join(log_path,'daq_scan_{}.log'.format(now.strftime('%Y%m%d_%H_%M_%S'))),level=logging.DEBUG)


class QSpinBox_ro(QtWidgets.QSpinBox):
    def __init__(self, **kwargs):
        super(QtWidgets.QSpinBox,self).__init__()
        self.setMaximum(100000)
        self.setReadOnly(True)
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)


class DAQ_Scan(QtWidgets.QWidget,QObject):
    """
    Main class initializing a DAQ_Scan module with its dashboard and scanning control panel
    """
    command_DAQ_signal=pyqtSignal(list)
    log_signal=pyqtSignal(str)

    params = [
        {'title': 'Loaded presets', 'name': 'loaded_files', 'type': 'group', 'children': [
            {'title': 'Preset file', 'name': 'preset_file', 'type': 'str', 'value': ''},
            {'title': 'Overshoot file', 'name': 'overshoot_file', 'type': 'str', 'value': ''},
            {'title': 'Layout file', 'name': 'layout_file', 'type': 'str', 'value': ''},
        ]},
        {'title': 'Moves/Detectors', 'name': 'Move_Detectors', 'type': 'group', 'children': [
            {'name': 'Detectors', 'type': 'itemselect'},
            {'name': 'Moves', 'type': 'itemselect'}
        ]},
        {'title': 'Time Flow:', 'name': 'time_flow', 'type': 'group', 'expanded': False, 'children': [
            {'title': 'Wait time (ms)', 'name': 'wait_time', 'type': 'int', 'value': 0},
            {'title': 'Timeout (ms)', 'name': 'timeout', 'type': 'int', 'value': 10000},
        ]},
        {'title': 'Scan options', 'name': 'scan_options', 'type': 'group', 'children': [
            {'title': 'Naverage:', 'name': 'scan_average', 'type': 'int', 'value': 1, 'min': 1},
            {'title': 'Plot from:', 'name': 'plot_from', 'type': 'list'},]},
    ]

    def __init__(self,parent):
        """

        Parameters
        ----------
        parent: (dockarea) instance of the modified pyqtgraph Dockarea (see daq_utils)
        """
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(DAQ_Scan,self).__init__()
        self.title='daq_scan'
        splash_path = os.path.join(os.path.split(__file__)[0], 'splash.png')
        splash = QtGui.QPixmap(splash_path)
        self.splash_sc=QtWidgets.QSplashScreen(splash,Qt.WindowStaysOnTopHint)
        self.init_prog=True
        self.dockarea=parent
        self.dockarea.dock_signal.connect(self.save_layout_state_auto)
        self.mainwindow=parent.parent()

        self.preset_file = None
        self.wait_time=1000
        self.navigator = None
        self.scan_x_axis = None
        self.scan_y_axis = None
        self.scan_data_1D = np.array([])
        self.scan_data_2D = []
        self.ind_scan = 0
        self.ind_average=0
        self.scan_data_2D_to_save = []
        self.scan_data_1D_to_save = []
        self.plot_1D_ini = False
        self.plot_2D_ini = False

        self.scan_thread = None
        self.move_modules = []
        self.detector_modules = []
        self.pid_controller = None

        self.h5saver = H5Saver()
        self.h5saver.settings.child(('do_save')).hide()
        self.h5saver.settings.child(('custom_name')).hide()
        self.h5saver.new_file_sig.connect(self.create_new_file)
        self.h5arrays = OrderedDict([])
        self.det_modules_scan = []
        self.move_modules_scan = []

        self.overshoot = False

        self.setupUI()

    @pyqtSlot(str)
    def add_log(self,txt):
        """
            Add the QListWisgetItem initialized with txt informations to the User Interface logger_list and to the save_parameters.logger array.

            =============== =========== ======================
            **Parameters**    **Type**   **Description**
            *txt*             string     the log info to add.
            =============== =========== ======================
        """
        try:
            now=datetime.datetime.now()
            new_item=QtWidgets.QListWidgetItem(now.strftime('%Y/%m/%d %H:%M:%S')+": "+txt)
            self.ui.logger_list.addItem(new_item)
            if self.h5saver.h5_file.isopen:
                self.h5saver.append(self.h5saver.logger_array, now.strftime('%Y/%m/%d %H:%M:%S')+": "+txt)

        except:
            pass

    def clear_move_det_controllers(self):
        """
            Remove all docks containing Moves or Viewers.

            See Also
            --------
            quit_fun, update_status
        """
        try:
        #remove all docks containing Moves or Viewers
            if hasattr(self,'move_modules'):
                if self.move_modules is not None:
                    for module in self.move_modules:
                        module.quit_fun()
                self.move_modules=None

            if hasattr(self,'detector_modules'):
                if self.detector_modules is not None:
                    for module in self.detector_modules:
                        module.quit_fun()
                self.detector_modules=None
        except Exception as e:
            
            self.update_status(getLineInfo()+ str(e),self.wait_time,log_type='log')

    def create_average_dock(self):
        self.ui.average_dock = Dock("Averaging")
        average_tab = QtWidgets.QTabWidget()
        average1D_widget = QtWidgets.QWidget()
        average2D_widget = QtWidgets.QWidget()

        # %% init the 1D viewer
        self.ui.average1D_graph = Viewer1D(average1D_widget)

        # %% init the 2D viewer
        self.ui.average2D_graph = Viewer2D(average2D_widget)

        average_tab.addTab(average1D_widget,'1D plot Average')
        average_tab.addTab(average2D_widget,'2D plot Average')

        self.ui.average_dock.addWidget(average_tab)
        self.dockarea.addDock(self.ui.average_dock,'right',self.ui.scan_dock)


        self.ui.average_dock.setVisible(False)

    def create_menu(self,menubar):
        """
            Create the menubar object looking like :
                * **Docked windows**
                    * Load Layout
                    * Save Layout
                    * Clear Moves/Detector
                    * Show/Hide Log Window
                * **Preset Modes**
                    * Create a preset
                * **Load Presets**
                    * Mock preset
                    * Canon preset

            | Connect each action to his referenced function.
            |
            | Finnaly store the directory list of xml files paths into the load_actions list.

            =============== ======================= =====================================
            **Parameters**   **Type**                 **Description**
            *menubar*         instance of QMenuBar    The generic menubar object of menu
            =============== ======================= =====================================

            See Also
            --------
            clear_move_det_controllers, load_layout_state, save_layout_state, show_file_attributes, set_preset_mode
        """
        menubar.clear()

        #%% create Settings menu
        self.file_menu=menubar.addMenu('File')
        load_action=self.file_menu.addAction('Load file')
        load_action.triggered.connect(self.load_file)
        save_action=self.file_menu.addAction('Save file')
        save_action.triggered.connect(self.save_file)
        show_action=self.file_menu.addAction('Show file content')
        show_action.triggered.connect(self.show_file_content)

        self.file_menu.addSeparator()
        quit_action=self.file_menu.addAction('Quit')
        quit_action.triggered.connect(self.quit_fun)

        self.settings_menu=menubar.addMenu('Settings')
        action_navigator = self.settings_menu.addAction('Show Navigator')
        docked_menu=self.settings_menu.addMenu('Docked windows')
        action_load=docked_menu.addAction('Load Layout')
        action_save=docked_menu.addAction('Save Layout')
        action_clear=self.settings_menu.addAction('Clear moves/Detectors')
        action_clear.triggered.connect(self.clear_move_det_controllers)
        action_navigator.triggered.connect(self.show_navigator)


        action_load.triggered.connect(self.load_layout_state)
        action_save.triggered.connect(self.save_layout_state)

        docked_menu.addSeparator()
        action_show_log=docked_menu.addAction('Show/hide log window')
        action_show_log.setCheckable(True)
        action_show_log.toggled.connect(self.ui.logger_dock.setVisible)



        self.preset_menu=menubar.addMenu('Preset Modes')
        action_new_preset=self.preset_menu.addAction('New preset')
        #action.triggered.connect(lambda: self.show_file_attributes(type_info='preset'))
        action_new_preset.triggered.connect(self.create_preset)
        action_modify_preset=self.preset_menu.addAction('Modify preset')
        action_modify_preset.triggered.connect(self.modify_preset)
        self.preset_menu.addSeparator()
        load_preset=self.preset_menu.addMenu('Load presets')

        slots=dict([])
        for ind_file,file in enumerate(os.listdir(os.path.join(local_path,'preset_modes'))):
            if file.endswith(".xml"):
                (filesplited, ext)=os.path.splitext(file)
                slots[filesplited]=load_preset.addAction(filesplited)
                slots[filesplited].triggered.connect(self.create_menu_slot(os.path.join(local_path,'preset_modes',file)))

        self.overshoot_menu=menubar.addMenu('Overshoot Modes')
        action_new_overshoot=self.overshoot_menu.addAction('New Overshoot')
        #action.triggered.connect(lambda: self.show_file_attributes(type_info='preset'))
        action_new_overshoot.triggered.connect(self.create_overshoot)
        action_modify_overshoot=self.overshoot_menu.addAction('Modify Overshoot')
        action_modify_overshoot.triggered.connect(self.modify_overshoot)
        self.overshoot_menu.addSeparator()
        load_overshoot=self.overshoot_menu.addMenu('Load Overshoots')

        slots_over=dict([])
        for ind_file,file in enumerate(os.listdir(os.path.join(local_path,'overshoot_configurations'))):
            if file.endswith(".xml"):
                (filesplited, ext)=os.path.splitext(file)
                slots_over[filesplited]=load_overshoot.addAction(filesplited)
                slots_over[filesplited].triggered.connect(self.create_menu_slot_over(os.path.join(local_path,'overshoot_configurations',file)))





        #help menu
        help_menu=menubar.addMenu('?')
        action_about=help_menu.addAction('About')
        action_about.triggered.connect(self.show_about)
        action_help=help_menu.addAction('Help')
        action_help.triggered.connect(self.show_help)
        action_help.setShortcut(QtCore.Qt.Key_F1)

    def open_PID(self):
        area = self.dockarea.addTempArea()
        self.pid_controller = DAQ_PID(area, [], [])

    def create_menu_slot(self,filename):
        return lambda: self.set_preset_mode(filename)

    def create_menu_slot_over(self,filename):
        return lambda: self.set_overshoot_configuration(filename)

    def create_overshoot(self):
        try:
            if self.preset_file is not None:
                file = os.path.split(self.preset_file)[1]
                file = os.path.splitext(file)[0]
            self.overshoot_manager.set_new_overshoot(file)
            self.create_menu(self.menubar)
        except Exception as e:
            self.update_status(getLineInfo()+ str(e),log_type='log')

    def create_preset(self):
        try:
            self.preset_manager.set_new_preset()
            self.create_menu(self.menubar)
        except Exception as e:
            self.update_status(getLineInfo()+ str(e),log_type='log')

    def load_file(self):
        self.h5saver.load_file()
        self.update_file_settings()

    def load_layout_state(self, file=None):
        """
            Load and restore a layout state from the select_file obtained pathname file.

            See Also
            --------
            utils.select_file
        """
        try:
            if file is None:
                file=utils.select_file(save=False, ext='dock')
            if file is not None:
                with open(str(file), 'rb') as f:
                    dockstate = pickle.load(f)
                    self.dockarea.restoreState(dockstate)
            file = os.path.split(file)[1]
            self.settings.child('loaded_files', 'layout_file').setValue(file)
        except: pass

    def modify_overshoot(self):
        try:
            path = utils.select_file(start_path=os.path.join(local_path,'overshoot_configurations'), save=False, ext='xml')
            if path != '':
                self.overshoot_manager.set_file_overshoot(str(path))

            else:  # cancel
                pass
        except Exception as e:
            self.update_status(getLineInfo()+ str(e),log_type='log')

    def modify_preset(self):
        try:
            path = utils.select_file(start_path=os.path.join(local_path,'preset_modes'), save=False, ext='xml')
            if path != '':
                self.preset_manager.set_file_preset(str(path))

            else:  # cancel
                pass
        except Exception as e:
            self.update_status(getLineInfo()+ str(e),log_type='log')

    @pyqtSlot(float, float)
    def move_to_crosshair(self,posx=None,posy=None):
        """
            Compute the scaled position from the given x/y position and send the command_DAQ signal with computed values as attributes.


            =============== =========== ==============================
            **Parameters**    **Type**   **Description**
            *posx*           float       the original x position
            *posy*           float       the original y position
            =============== =========== ==============================

            See Also
            --------
            update_status
        """
        if self.ui.move_to_crosshair_cb.isChecked() or self.navigator.moveat_action.isChecked():
            if "2D" in self.scanner.settings.child('scan_options','scan_type').value():
                if len(self.move_modules_scan)==2 and posx is not None and posy is not None:
                    posx_real=posx*self.ui.scan2D_graph.scaled_xaxis.scaling+self.ui.scan2D_graph.scaled_xaxis.offset
                    posy_real=posy*self.ui.scan2D_graph.scaled_yaxis.scaling+self.ui.scan2D_graph.scaled_yaxis.offset
                    self.command_DAQ_signal.emit(["move_stages",[posx_real,posy_real]])
                else:
                    self.update_status("not valid configuration, check number of stages and scan2D option",log_type='log')

    def quit_fun(self):
        """
            Quit the current instance of DAQ_scan and close on cascade move and detector modules.

            See Also
            --------
            quit_fun
        """
        try:
            try:
                self.h5saver.close_file()
            except:
                pass

            for module in self.move_modules:
                try:
                    module.quit_fun()
                    QtWidgets.QApplication.processEvents()
                    QThread.msleep(1000)
                    QtWidgets.QApplication.processEvents()
                except:
                    pass

            for module in self.detector_modules:
                try:
                    module.quit_fun()
                    QtWidgets.QApplication.processEvents()
                    QThread.msleep(1000)
                    QtWidgets.QApplication.processEvents()
                except:
                    pass
            areas=self.dockarea.tempAreas[:]
            for area in areas:
                area.win.close()
                QtWidgets.QApplication.processEvents()
                QThread.msleep(1000)
                QtWidgets.QApplication.processEvents()


            #save scan settings related to the current preset
            if self.preset_file is not None:
                file = os.path.split(self.preset_file)[1]
                # path = os.path.join(scan_conf_path, file)
                # custom_tree.parameter_to_xml_file(self.settings, path)

            if hasattr(self,'mainwindow'):
                self.mainwindow.close()




        except Exception as e:
            pass



    def save_scan(self):
        """

        """
        try:
            self.h5saver.init_file(addhoc_file_path=self.h5saver.settings.child(('current_h5_file')).value())
            #create Live scan node (may be empty if no possible live data could be plotted) but mandatory for
            # incrementing scan index, otherwise current scan is overwritten
            if '1D' in self.scanner.settings.child('scan_options', 'scan_type').value():
                live_group = self.h5saver.add_live_scan_group(self.h5saver.current_scan_group, '1D', title='',
                                                              settings_as_xml='', metadata=dict([]))
            elif '2D' in self.scanner.settings.child('scan_options', 'scan_type').value():
                live_group = self.h5saver.add_live_scan_group(self.h5saver.current_scan_group, '2D', title='',
                                                              settings_as_xml='', metadata=dict([]))

            # save scan1D
            if len(self.scan_data_1D) != 0:

                if self.settings.child('scan_options', 'scan_average').value() <= 1:
                    datas = OrderedDict([])
                    for ind in range(self.scan_data_1D.shape[1]):
                        datas['Scan_Data_{:03d}'.format(ind)] = OrderedDict([])
                        datas['Scan_Data_{:03d}'.format(ind)]['data'] = self.scan_data_1D[:,ind]
                        datas['Scan_Data_{:03d}'.format(ind)]['x_axis'] = dict(data=self.scan_x_axis,
                                units=self.move_modules_scan[0].settings.child('move_settings', 'units').value(),
                                label=self.move_modules_scan[0].title)


                    for ind_channel, channel in enumerate(datas):  # list of OrderedDict
                        channel_group = self.h5saver.add_CH_group(live_group, title=channel)
                        self.h5saver.add_data_live_scan(channel_group, datas['Scan_Data_{:03d}'.format(ind_channel)] ,
                                             scan_type='scan1D')

                else:
                    averaged_datas = OrderedDict([])
                    for ind in range(self.scan_data_1D.shape[1]):
                        averaged_datas['Scan_Data_{:03d}'.format(ind)] = OrderedDict([])
                        averaged_datas['Scan_Data_{:03d}'.format(ind)]['data'] = self.scan_data_1D_average[:, ind]
                        averaged_datas['Scan_Data_{:03d}'.format(ind)]['x_axis'] = dict(data=self.scan_x_axis,
                                 units=self.move_modules_scan[0].settings.child('move_settings','units').value(),
                                 label=self.move_modules_scan[0].title)

                    for ind_channel, channel in enumerate(averaged_datas):  # list of OrderedDict
                        channel_group = self.h5saver.add_CH_group(live_group, title=channel)
                        self.h5saver.add_data_live_scan(channel_group, averaged_datas['Scan_Data_Average_{:03d}'.format(ind_channel)],
                                                        scan_type='scan1D')

                if self.settings.child('scan_options', 'scan_average').value() > 1:
                    png = self.ui.average1D_graph.parent.grab().toImage()
                else:
                    png = self.ui.scan1D_graph.parent.grab().toImage()
                png = png.scaled(100, 100, QtCore.Qt.KeepAspectRatio)
                buffer = QtCore.QBuffer()
                buffer.open(QtCore.QIODevice.WriteOnly)
                png.save(buffer, "png")
                string = buffer.data().data()
                live_group._v_attrs['pixmap1D'] = string



            if self.scan_data_2D != []:

                if len(self.move_modules_scan) == 1:
                    scan_type = 'scan1D'
                elif len(self.move_modules_scan) == 2:
                    scan_type = 'scan2D'

                if self.settings.child('scan_options', 'scan_average').value() <= 1:
                    datas = OrderedDict([])
                    for ind, data2D in enumerate(self.scan_data_2D):
                        datas['Scan_Data_{:03d}'.format(ind)] = OrderedDict([])
                        datas['Scan_Data_{:03d}'.format(ind)]['data'] = data2D
                        datas['Scan_Data_{:03d}'.format(ind)]['x_axis'] = dict(data=self.ui.scan2D_graph.x_axis,
                                units=self.ui.scan2D_graph.scaling_options['scaled_xaxis']['units'],
                                label=self.ui.scan2D_graph.scaling_options['scaled_xaxis']['label'],)
                        datas['Scan_Data_{:03d}'.format(ind)]['y_axis'] = dict(data=self.ui.scan2D_graph.y_axis,
                                units=self.ui.scan2D_graph.scaling_options['scaled_yaxis']['units'],
                                label=self.ui.scan2D_graph.scaling_options['scaled_yaxis']['label'])

                    for ind_channel, channel in enumerate(datas):  # list of OrderedDict
                        channel_group = self.h5saver.add_CH_group(live_group, title=channel)
                        self.h5saver.add_data_live_scan(channel_group, datas['Scan_Data_{:03d}'.format(ind_channel)],
                                             scan_type=scan_type)

                else:
                    averaged_datas = OrderedDict([])
                    for ind, data2D in enumerate(self.scan_data_2D_average):
                        averaged_datas['Scan_Data_Average_{:03d}'.format(ind)] = OrderedDict([])
                        averaged_datas['Scan_Data_Average_{:03d}'.format(ind)]['data'] = data2D
                        averaged_datas['Scan_Data_Average_{:03d}'.format(ind)]['x_axis'] = dict(data=self.ui.scan2D_graph.x_axis,
                                units=self.ui.scan2D_graph.scaling_options['scaled_xaxis']['units'],
                                label=self.ui.scan2D_graph.scaling_options['scaled_xaxis']['label'],)

                        averaged_datas['Scan_Data_Average_{:03d}'.format(ind)]['y_axis'] = dict(data=self.ui.scan2D_graph.y_axis,
                                units=self.ui.scan2D_graph.scaling_options['scaled_yaxis']['units'],
                                label=self.ui.scan2D_graph.scaling_options['scaled_yaxis']['label'])

                    for ind_channel, channel in enumerate(averaged_datas):  # dict of OrderedDict
                        channel_group = self.h5saver.add_CH_group(live_group, title=channel)
                        self.h5saver.add_data_live_scan(channel_group, averaged_datas['Scan_Data_Average_{:03d}'.format(ind_channel)],
                                             scan_type=scan_type)



                if self.settings.child('scan_options', 'scan_average').value() > 1:
                    png = self.ui.average2D_graph.parent.grab().toImage()
                else:
                    png = self.ui.scan2D_graph.parent.grab().toImage()
                png = png.scaled(100, 100, QtCore.Qt.KeepAspectRatio)
                buffer = QtCore.QBuffer()
                buffer.open(QtCore.QIODevice.WriteOnly)
                png.save(buffer, "png")
                string = buffer.data().data()
                live_group._v_attrs['pixmap2D'] = string


            if self.navigator is not None:
                self.navigator.update_2Dscans()

        except Exception as e:
            self.update_status(getLineInfo()+ str(e),wait_time=self.wait_time,log_type='log')

    def save_file(self):
        if not os.path.isdir(self.h5saver.settings.child(('base_path')).value()):
            os.mkdir(self.h5saver.settings.child(('base_path')).value())
        filename=utils.select_file(self.h5saver.settings.child(('base_path')).value(), save=True, ext='h5')
        self.h5saver.h5_file.copy_file(str(filename))

    def save_layout_state(self, file = None):
        """
            Save the current layout state in the select_file obtained pathname file.
            Once done dump the pickle.

            See Also
            --------
            utils.select_file
        """
        try:
            dockstate = self.dockarea.saveState()
            if file is None:
                file=utils.select_file(start_path=None, save=True, ext='dock')
            if file is not None:
                with open(str(file), 'wb') as f:
                    pickle.dump(dockstate, f, pickle.HIGHEST_PROTOCOL)
        except: pass

    def save_layout_state_auto(self):
        if self.preset_file is not None:
            file = os.path.split(self.preset_file)[1]
            file = os.path.splitext(file)[0]
            path = os.path.join(layout_path, file+'.dock')
            self.save_layout_state(path)

    def save_metadata(self,node,type_info='dataset_info'):
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

        attr=node._v_attrs
        if type_info=='dataset_info':
            attr['type']='dataset'
            params=self.dataset_attributes
        else:
            attr['type']='scan'
            params=self.scan_attributes
        for child in params.child((type_info)).children():
            if type(child.value()) is QDateTime:
                attr[child.name()]=child.value().toString('dd/mm/yyyy HH:MM:ss')
            else:
                attr[child.name()]=child.value()
        #save contents of given parameter object into an xml string under the attribute settings
        attr.settings=custom_tree.parameter_to_xml_string(params)
        if type_info=='scan_info':
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

                if param.name() == 'Detectors':
                    self.update_plot_det_items(param)

                elif param.name() == 'scan_average':
                    self.show_average_dock(param.value() > 1)
            elif change == 'parent':pass

    def show_average_dock(self, show = True):
        self.ui.average_dock.setVisible(show)
        self.ui.indice_average_sb.setVisible(show)
        if show:
            self.ui.average_dock.setStretch(100, 100)

    def set_file_preset(self,filename):
        """
            Set a file preset from the converted xml file given by the filename parameter.


            =============== =========== ===================================================
            **Parameters**    **Type**    **Description**
            *filename*        string      the name of the xml file to be converted/treated
            =============== =========== ===================================================

            Returns
            -------
            (Object list, Object list) tuple
                The updated (Move modules list, Detector modules list).

            See Also
            --------
            custom_tree.XML_file_to_parameter, set_param_from_param, stop_moves, update_status,DAQ_Move_main.daq_move, DAQ_viewer_main.daq_viewer
        """
        if os.path.splitext(filename)[1] == '.xml':
            self.preset_file = filename
            self.preset_manager.set_file_preset(filename, show=False)
            self.move_docks = []
            self.det_docks_settings = []
            self.det_docks_viewer = []
            move_forms = []
            move_modules = []
            detector_modules = []
            move_types = []


            ### set daq scan settings set in preset
            try:
                for child in self.preset_manager.preset_params.child(('saving_options')).children():
                    self.h5saver.settings.child((child.name())).setValue(child.value())
            except Exception as e:
                self.update_status(getLineInfo()+ str(e), 'log')

            ## set PID if checked in preset
            try:
                if self.preset_manager.preset_params.child(('use_pid')).value():
                    self.open_PID()
                    QtWidgets.QApplication.processEvents()
                    for child in custom_tree.iter_children_params(self.preset_manager.preset_params.child(('pid_settings')), []):
                        preset_path = self.preset_manager.preset_params.child(('pid_settings')).childPath(child)
                        self.pid_controller.settings.child(*preset_path).setValue(child.value())

                    move_modules.append(self.pid_controller)

            except Exception as e:
                self.update_status(getLineInfo()+ str(e), 'log')

            #################################################################
            ###### sort plugins by IDs and within the same IDs by Master and Slave status
            plugins=[{'type': 'move', 'value': child} for child in self.preset_manager.preset_params.child(('Moves')).children()]+[{'type': 'det', 'value': child} for child in self.preset_manager.preset_params.child(('Detectors')).children()]

            for plug in plugins:
                plug['ID']=plug['value'].child('params','main_settings','controller_ID').value()
                if plug["type"]=='det':
                    plug['status']=plug['value'].child('params','detector_settings','controller_status').value()
                else:
                    plug['status']=plug['value'].child('params','move_settings', 'multiaxes', 'multi_status').value()

            IDs=list(set([plug['ID'] for plug in plugins]))
            #%%
            plugins_sorted=[]
            for id in IDs:
                plug_Ids=[]
                for plug in plugins:
                    if plug['ID']==id:
                        plug_Ids.append(plug)
                plug_Ids.sort(key=lambda status: status['status'])
                plugins_sorted.append(plug_Ids)
            #################################################################
            #######################

            ind_move=-1
            ind_det=-1
            for plug_IDs in plugins_sorted:
                for ind_plugin, plugin in enumerate(plug_IDs):


                    plug_name=plugin['value'].child(('name')).value()
                    plug_init=plugin['value'].child(('init')).value()
                    plug_settings=plugin['value'].child(('params'))
                    self.splash_sc.showMessage('Loading {:s} module: {:s}'.format(plugin['type'],plug_name),color = Qt.white)
                    if plugin['type'] == 'move':
                        ind_move+=1
                        plug_type=plug_settings.child('main_settings','move_type').value()
                        self.move_docks.append(Dock(plug_name, size=(150,250)))
                        if ind_move==0:
                            self.dockarea.addDock(self.move_docks[-1], 'right',self.ui.logger_dock)
                        else:
                            self.dockarea.addDock(self.move_docks[-1], 'above',self.move_docks[-2])
                        move_forms.append(QtWidgets.QWidget())
                        mov_mod_tmp=DAQ_Move(move_forms[-1],plug_name)

                        mov_mod_tmp.ui.Stage_type_combo.setCurrentText(plug_type)
                        mov_mod_tmp.ui.Quit_pb.setEnabled(False)
                        QtWidgets.QApplication.processEvents()

                        utils.set_param_from_param(mov_mod_tmp.settings,plug_settings)
                        QtWidgets.QApplication.processEvents()

                        mov_mod_tmp.bounds_signal[bool].connect(self.stop_moves)
                        self.move_docks[-1].addWidget(move_forms[-1])
                        move_modules.append(mov_mod_tmp)

                        try:
                            if ind_plugin==0: #should be a master type plugin
                                if plugin['status']!="Master":
                                    raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                                if plug_init:
                                    move_modules[-1].ui.IniStage_pb.click()
                                    QtWidgets.QApplication.processEvents()
                                    if 'Mock' in plug_type:
                                        QThread.msleep(500)
                                    else:
                                        QThread.msleep(4000)  # to let enough time for real hardware to init properly
                                    QtWidgets.QApplication.processEvents()
                                    master_controller=move_modules[-1].controller
                            else:
                                if plugin['status']!="Slave":
                                    raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                                if plug_init:
                                    move_modules[-1].controller=master_controller
                                    move_modules[-1].ui.IniStage_pb.click()
                                    QtWidgets.QApplication.processEvents()
                                    if 'Mock' in plug_type:
                                        QThread.msleep(500)
                                    else:
                                        QThread.msleep(4000)  # to let enough time for real hardware to init properly
                                    QtWidgets.QApplication.processEvents()
                        except Exception as e:
                            self.update_status(getLineInfo()+ str(e),'log')


                    else:
                        ind_det+=1
                        plug_type=plug_settings.child('main_settings','DAQ_type').value()
                        plug_subtype=plug_settings.child('main_settings','detector_type').value()

                        self.det_docks_settings.append(Dock(plug_name+" settings", size=(150,250)))
                        self.det_docks_viewer.append(Dock(plug_name+" viewer", size=(350,350)))

                        if ind_det==0:
                            self.ui.logger_dock.area.addDock(self.det_docks_settings[-1], 'bottom') #dockarea of the logger dock
                        else:
                            self.dockarea.addDock(self.det_docks_settings[-1], 'right',self.det_docks_viewer[-2])
                        self.dockarea.addDock(self.det_docks_viewer[-1],'right',self.det_docks_settings[-1])

                        det_mod_tmp=DAQ_Viewer(self.dockarea,dock_settings=self.det_docks_settings[-1],
                                                            dock_viewer=self.det_docks_viewer[-1],title=plug_name,
                                               DAQ_type=plug_type, parent_scan=self)
                        detector_modules.append(det_mod_tmp)
                        detector_modules[-1].ui.Detector_type_combo.setCurrentText(plug_subtype)
                        detector_modules[-1].ui.Quit_pb.setEnabled(False)
                        utils.set_param_from_param(det_mod_tmp.settings,plug_settings)
                        QtWidgets.QApplication.processEvents()


                        try:
                            if ind_plugin==0: #should be a master type plugin
                                if plugin['status']!="Master":
                                    raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                                if plug_init:
                                    detector_modules[-1].ui.IniDet_pb.click()
                                    QtWidgets.QApplication.processEvents()
                                    if 'Mock' in plug_subtype:
                                        QThread.msleep(500)
                                    else:
                                        QThread.msleep(4000)  # to let enough time for real hardware to init properly
                                    QtWidgets.QApplication.processEvents()
                                    master_controller=detector_modules[-1].controller
                            else:
                                if plugin['status']!="Slave":
                                    raise Exception('error in the master/slave type for plugin {}'.format(plug_name))
                                if plug_init:
                                    detector_modules[-1].controller=master_controller
                                    detector_modules[-1].ui.IniDet_pb.click()
                                    QtWidgets.QApplication.processEvents()
                                    if 'Mock' in plug_subtype:
                                        QThread.msleep(500)
                                    else:
                                        QThread.msleep(4000)  # to let enough time for real hardware to init properly
                                    QtWidgets.QApplication.processEvents()
                        except Exception as e:
                            self.update_status(getLineInfo()+ str(e),'log')

                        detector_modules[-1].settings.child('main_settings','overshoot').show()
                        detector_modules[-1].overshoot_signal[bool].connect(self.stop_moves)

            QtWidgets.QApplication.processEvents()
            #restore dock state if saved
            file = os.path.split(self.preset_file)[1]
            file = os.path.splitext(file)[0]
            path = os.path.join(layout_path, file + '.dock')
            if os.path.isfile(path):
                self.load_layout_state(path)



            return move_modules,detector_modules
        else:
            raise Exception('Invalid file selected')

    def set_ini_positions(self):
        """
            Send the command_DAQ signal with "set_ini_positions" list item as an attribute.
        """
        self.command_DAQ_signal.emit(["set_ini_positions"])


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
        date=QDateTime(QDate.currentDate(),QTime.currentTime())
        self.dataset_attributes.child('dataset_info','date_time').setValue(date)
        res = self.show_file_attributes('dataset')
        return res


    def set_overshoot_configuration(self,filename):
        try:
            if os.path.splitext(filename)[1]=='.xml':
                file = os.path.split(filename)[1]
                self.settings.child('loaded_files', 'overshoot_file').setValue(file)
                self.update_status('Overshoot configuration ({}) has been loaded'.format(os.path.split(filename)[1]),log_type='log')
                self.overshoot_manager.set_file_overshoot(filename,show=False)

                det_titles=[det.title for det in self.detector_modules]
                move_titles=[move.title for move in self.move_modules]

                for det_param in self.overshoot_manager.overshoot_params.child(('Detectors')).children():
                    if det_param.child(('trig_overshoot')).value():
                        det_index = det_titles.index(det_param.opts['title'])
                        det_module = self.detector_modules[det_index]
                        det_module.settings.child('main_settings','overshoot','stop_overshoot').setValue(True)
                        det_module.settings.child('main_settings','overshoot','overshoot_value').setValue(det_param.child(('overshoot_value')).value())
                        for move_param in det_param.child(('params')).children():
                            if move_param.child(('move_overshoot')).value():
                                move_index = move_titles.index(move_param.opts['title'])
                                move_module = self.move_modules[move_index]
                                det_module.overshoot_signal.connect(self.create_overshoot_fun(move_module,move_param.child(('position')).value()))

        except Exception as e:
            self.update_status(getLineInfo()+ str(e),self.wait_time,log_type='log')

    def create_overshoot_fun(self,move_module,position):
        return lambda: move_module.move_Abs(position)

    def set_preset_mode(self,filename):
        """
            | Set the preset mode from the given filename.
            |
            | In case of "mock" or "canon" move, set the corresponding preset calling set_(*)_preset procedure.
            |
            | Else set the preset file using set_file_preset function.
            | Once done connect the move and detector modules to logger to recipe/transmit informations.

            Finally update DAQ_scan_settings tree with :
                * Detectors
                * Move
                * plot_form.

            =============== =========== =============================================
            **Parameters**    **Type**    **Description**
            *filename*        string      the name of the preset file to be treated
            =============== =========== =============================================

            See Also
            --------
            set_Mock_preset, set_canon_preset, set_file_preset, add_log, update_status
        """
        try:
            self.mainwindow.setVisible(False)
            for area in self.dockarea.tempAreas:
                area.window().setVisible(False)

            self.splash_sc.show()
            QtWidgets.QApplication.processEvents()
            self.splash_sc.raise_()
            self.splash_sc.showMessage('Loading Modules, please wait',color = Qt.white)
            QtWidgets.QApplication.processEvents()
            self.clear_move_det_controllers()
            QtWidgets.QApplication.processEvents()


            move_modules, detector_modules= self.set_file_preset(filename)
            self.update_status('Preset mode ({}) has been loaded'.format(os.path.split(filename)[1]),log_type='log')
            self.settings.child('loaded_files', 'preset_file').setValue(os.path.split(filename)[1])
            self.move_modules = move_modules
            self.detector_modules = detector_modules

            ######################################################################
            #set scan selector
            items = OrderedDict()
            if self.navigator is not None:
                items["Navigator"] = dict(viewers=[self.navigator.viewer], names=["Navigator"])
            for det in self.detector_modules:
                if len([view for view in det.ui.viewers if view.viewer_type=='Data2D']) != 0:
                    items[det.title] = dict(viewers=[view for view in det.ui.viewers if view.viewer_type == 'Data2D'],
                                        names=[view.title for view in det.ui.viewers if view.viewer_type == 'Data2D'],)
            items["DAQ_Scan"] = dict(viewers=[self.ui.scan2D_graph], names=["DAQ_Scan"])

            if self.navigator is not None:
                items = OrderedDict(Navigator=dict(viewers=[self.navigator.viewer], names=["Navigator"]))
                items.update(self.scanner.scan_selector.viewers_items)

            self.scanner.viewers_items = items

            self.scanner.scan_selector.widget.setVisible(False)
            self.scanner.scan_selector.settings.child('scan_options', 'scan_type').hide()

            self.scanner.scan_selector.widget.setVisible(False)
            self.scanner.scan_selector.show_scan_selector(visible=False)

            #####################################################
            self.overshoot_manager = OvershootManager(det_modules=[det.title for det in detector_modules], move_modules=[move.title for move in move_modules])
            #load overshoot if present
            file = os.path.split(self.preset_file)[1]
            path = os.path.join(overshoot_path, file)
            if os.path.isfile(path):
                self.set_overshoot_configuration(path)


            #connecting to logger
            for mov in move_modules:
                mov.log_signal[str].connect(self.add_log)
                mov.init_signal.connect(self.update_init_tree)
            for det in detector_modules:
                det.log_signal[str].connect(self.add_log)
                det.init_signal.connect(self.update_init_tree)
            #setting moves and det in tree
            preset_items_det=[]
            preset_items_move=[]
            items_det=[module.title for module in detector_modules]
            if items_det!=[]:
                preset_items_det=[items_det[0]]

            items_move=[module.title for module in move_modules]
            if items_move!=[]:
                preset_items_move=[items_move[0]]

            self.settings.child('Move_Detectors', 'Detectors').setValue(dict(all_items=items_det, selected=preset_items_det))
            self.settings.child('Move_Detectors', 'Moves').setValue(dict(all_items=items_move, selected=preset_items_move))
            self.settings.child('scan_options', 'plot_from').setLimits(preset_items_det)
            if preset_items_det!=[]:
                self.settings.child('scan_options', 'plot_from').setValue(preset_items_det[0])

            self.splash_sc.close()
            self.mainwindow.setVisible(True)
            for area in self.dockarea.tempAreas:
                area.window().setVisible(True)
            self.show_average_dock(False)

            self.ui.scan_dock.setEnabled(True)
            self.file_menu.setEnabled(True)
            self.settings_menu.setEnabled(True)
            self.overshoot_menu.setEnabled(True)

            self.create_new_file(True)
            self.update_init_tree()

        except Exception as e:

            self.update_status(getLineInfo()+ str(e), self.wait_time, log_type='log')

    def create_new_file(self, new_file):
        self.h5saver.init_file(update_h5=new_file)
        res = self.update_file_settings(new_file)
        if new_file:
            self.ui.start_scan_pb.setEnabled(False)
            self.ui.stop_scan_pb.setEnabled(False)
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
            move_names_scan=self.settings.child('Move_Detectors', 'Moves').value()['selected'] #selected move modules names
            move_names=[mod.title for mod in self.move_modules] # names of all move modules initialized
            self.move_modules_scan=[] #list of move modules used for this scan
            for name in move_names_scan:
                self.move_modules_scan.append(self.move_modules[move_names.index(name)])#create list of modules used for this current scan

            det_names_scan=self.settings.child('Move_Detectors', 'Detectors').value()['selected']# names of all selected detector modules initialized
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

            self.ui.start_scan_pb.setEnabled(True)
            self.ui.stop_scan_pb.setEnabled(True)



            return True

        except Exception as e:
            self.update_status(getLineInfo()+ str(e),wait_time=self.wait_time,log_type='log')
            self.ui.start_scan_pb.setEnabled(False)
            self.ui.stop_scan_pb.setEnabled(False)

    def setupUI(self):
        self.ui=Ui_Form()
        widgetsettings=QtWidgets.QWidget()
        self.ui.setupUi(widgetsettings)
        self.mainwindow.setVisible(False)

        #%% create scan dock and make it a floating window
        self.ui.scan_dock = Dock("Scan", size=(1, 1), autoOrientation=False)     ## give this dock the minimum possible size
        self.ui.scan_dock.setOrientation('vertical')

        self.ui.scan_dock.addWidget(widgetsettings)
        self.dockarea.addDock(self.ui.scan_dock,'left')



        #%% create logger dock
        self.ui.logger_dock=Dock("Logger")
        self.ui.logger_list=QtWidgets.QListWidget()
        self.ui.logger_list.setMinimumWidth(300)
        self.init_tree = ParameterTree()
        self.init_tree.setMinimumWidth(300)
        self.ui.logger_dock.addWidget(self.init_tree)
        self.ui.logger_dock.addWidget(self.ui.logger_list)

        self.init_settings=Parameter.create(name='init_settings', type='group', children=[
            {'title': 'Actuators Init.', 'name': 'actuators', 'type': 'group', 'children': []},
            {'title': 'Detectors Init.', 'name': 'detectors', 'type': 'group', 'children': []},
            ])
        self.init_tree.setParameters(self.init_settings, showTop=False)

        self.dockarea.addDock(self.ui.logger_dock,'top')
        self.ui.logger_dock.setVisible(True)
        self.ui.logger_dock.float()

        #%% init the 1D viewer
        self.ui.scan1D_graph_widget = QtWidgets.QWidget()
        self.ui.scan1D_graph = Viewer1D(self.ui.scan1D_graph_widget)
        self.ui.scan1D_layout.addWidget(self.ui.scan1D_graph_widget)

        #%% init the 2D viewer
        self.ui.scan2D_graph_widget=QtWidgets.QWidget()
        self.ui.scan2D_graph=Viewer2D(self.ui.scan2D_graph_widget)
        self.ui.scan2D_layout.addWidget(self.ui.scan2D_graph_widget)
        self.ui.scan2D_graph.ui.Show_histogram.setChecked(False)
        self.ui.scan2D_graph.ui.histogram_blue.setVisible(False)
        self.ui.scan2D_graph.ui.histogram_green.setVisible(False)
        self.ui.scan2D_graph.ui.histogram_red.setVisible(False)
        self.ui.scan2D_graph.ui.Ini_plot_pb.setVisible(False)
        self.ui.scan2D_graph.ui.FlipUD_pb.setVisible(False)
        self.ui.scan2D_graph.ui.FlipLR_pb.setVisible(False)
        self.ui.scan2D_graph.ui.rotate_pb.setVisible(False)
        self.ui.move_to_crosshair_cb = QtWidgets.QCheckBox("Move at doubleClicked")

        self.ui.scan2D_graph.ui.horizontalLayout_2.addWidget(self.ui.move_to_crosshair_cb)
        self.ui.scan2D_graph.sig_double_clicked.connect(self.move_to_crosshair)

        #%% init and set the status bar
        self.ui.statusbar=QtWidgets.QStatusBar(self.dockarea)
        self.ui.statusbar.setMaximumHeight(25)
        self.ui.StatusBarLayout.addWidget(self.ui.statusbar)
        self.ui.log_message=QtWidgets.QLabel('Initializing')
        self.ui.statusbar.addPermanentWidget(self.ui.log_message)
        self.ui.N_scan_steps_sb=QSpinBox_ro()
        self.ui.N_scan_steps_sb.setToolTip('Total number of steps')
        self.ui.indice_scan_sb=QSpinBox_ro()
        self.ui.indice_scan_sb.setToolTip('Current step value')
        self.ui.indice_average_sb=QSpinBox_ro()
        self.ui.indice_average_sb.setToolTip('Current average value')
        self.ui.scan_done_LED=QLED()
        self.ui.scan_done_LED.setToolTip('Scan done state')
        self.ui.statusbar.addPermanentWidget(self.ui.N_scan_steps_sb)
        self.ui.statusbar.addPermanentWidget(self.ui.indice_scan_sb)
        self.ui.statusbar.addPermanentWidget(self.ui.indice_average_sb)
        self.ui.indice_average_sb.setVisible(False)
        self.ui.statusbar.addPermanentWidget(self.ui.scan_done_LED)

        self.plot_colors=utils.plot_colors

        self.ui.splitter.setSizes([500, 1200])


        self.ui.scan_done_LED.set_as_false()
        self.ui.scan_done_LED.clickable=False
        self.ui.start_scan_pb.setEnabled(False)
        self.ui.stop_scan_pb.setEnabled(False)

        #displaying the settings
        widget_settings = QtWidgets.QWidget()
        settings_layout = QtWidgets.QGridLayout()
        widget_settings.setLayout(settings_layout)
        self.ui.settings_layout.addWidget(widget_settings)

        self.settings_tree = ParameterTree()
        self.settings_tree.setMinimumWidth(300)
        settings_layout.addWidget(self.settings_tree, 0, 0, 2 ,1)
        settings_layout.addWidget(self.h5saver.settings_tree, 0, 1, 1, 1)
        self.h5saver.settings_tree.setMinimumWidth(300)
        self.settings=Parameter.create(name='Settings', type='group', children=self.params)

        self.settings_tree.setParameters(self.settings, showTop=False)
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)
        self.scan_parameters=utils.ScanParameters()#contains information about scan to be done, such as Nsteps, x_axis...


        self.scanner = Scanner()
        settings_layout.addWidget(self.scanner.settings_tree, 1, 1, 1, 1)



        #params about dataset attributes and scan attibutes
        date=QDateTime(QDate.currentDate(),QTime.currentTime())
        params_dataset=[{'title': 'Dataset information', 'name': 'dataset_info', 'type': 'group', 'children':[
                            {'title': 'Author:', 'name': 'author', 'type': 'str', 'value': 'Sebastien Weber'},
                            {'title': 'Date/time:', 'name': 'date_time', 'type': 'date_time', 'value': date},
                            {'title': 'Sample:', 'name': 'sample', 'type': 'str', 'value':''},
                            {'title': 'Experiment type:', 'name': 'experiment_type', 'type': 'str', 'value': ''},
                            {'title': 'Description:', 'name': 'description', 'type': 'text', 'value': ''}]}]

        params_scan=[{'title': 'Scan information', 'name': 'scan_info', 'type': 'group', 'children':[
                            {'title': 'Author:', 'name': 'author', 'type': 'str', 'value': 'Sebastien Weber'},
                            {'title': 'Date/time:', 'name': 'date_time', 'type': 'date_time', 'value': date},
                            {'title': 'Scan type:', 'name': 'scan_type', 'type': 'list', 'value':'Scan1D', 'values':['Scan1D','Scan2D']},
                            {'title': 'Scan name:', 'name': 'scan_name', 'type': 'str', 'value': '', 'readonly': True},
                            {'title': 'Description:', 'name': 'description', 'type': 'text', 'value': ''},
                            ]}]


        self.preset_manager=PresetManager()
        self.overshoot_manager = OvershootManager(det_modules=[],move_modules=[])

        self.dataset_attributes=Parameter.create(name='Attributes', type='group', children=params_dataset)
        self.scan_attributes=Parameter.create(name='Attributes', type='group', children=params_scan)

        #creating the Average dock plots
        self.create_average_dock()

        #creating the menubar
        self.menubar=self.mainwindow.menuBar()
        self.create_menu(self.menubar)

#        connecting
        self.log_signal[str].connect(self.add_log)
        self.ui.set_scan_pb.clicked.connect(self.set_scan)
        self.ui.quit_pb.clicked.connect(self.quit_fun)

        self.ui.start_scan_pb.clicked.connect(self.start_scan)
        self.ui.stop_scan_pb.clicked.connect(self.stop_scan)
        self.ui.set_ini_positions_pb.clicked.connect(self.set_ini_positions)

        self.ui.tabWidget.removeTab(2)

        self.ui.scan_dock.setEnabled(False)
        self.file_menu.setEnabled(False)
        self.settings_menu.setEnabled(False)
        self.overshoot_menu.setEnabled(False)
        self.preset_menu.setEnabled(True)
        self.mainwindow.setVisible(True)


    def update_init_tree(self):
        for act in self.move_modules:
            if act.title not in custom_tree.iter_children(self.init_settings.child(('actuators')), []):
                self.init_settings.child(('actuators')).addChild({'title': act.title, 'name': act.title, 'type': 'led', 'value': False})
            QtWidgets.QApplication.processEvents()
            self.init_settings.child('actuators', act.title).setValue(act.initialized_state)

        for act in self.detector_modules:
            if act.title not in custom_tree.iter_children(self.init_settings.child(('detectors')), []):
                self.init_settings.child(('detectors')).addChild({'title': act.title, 'name': act.title, 'type': 'led', 'value': False})
            QtWidgets.QApplication.processEvents()
            self.init_settings.child('detectors', act.title).setValue(act.initialized_state)


    def show_about(self):
        self.splash_sc.setVisible(True)
        self.splash_sc.showMessage("PyMoDAQ version {:}\nModular Acquisition with Python\nWritten by Sébastien Weber".format(get_version()), QtCore.Qt.AlignRight, QtCore.Qt.white)

    def show_file_attributes(self,type_info='dataset'):
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
        dialog=QtWidgets.QDialog()
        vlayout=QtWidgets.QVBoxLayout()
        tree = ParameterTree()
        tree.setMinimumWidth(400)
        tree.setMinimumHeight(500)
        if type_info=='scan':
            tree.setParameters(self.scan_attributes, showTop=False)
        elif type_info=='dataset':
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

    def show_help(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("http://pymodaq.cnrs.fr"))

    def show_navigator(self):
        if self.navigator is None:
            #loading navigator

            widgnav = QtWidgets.QWidget()
            self.navigator = Navigator(widgnav)

            self.navigator.log_signal[str].connect(self.add_log)
            self.navigator.settings.child('settings', 'Load h5').hide()
            self.navigator.loadaction.setVisible(False)

            self.ui.navigator_layout.addWidget(widgnav)
            self.navigator.sig_double_clicked.connect(self.move_to_crosshair)

            self.scanner.scan_selector.remove_scan_selector()
            items = OrderedDict(Navigator=dict(viewers=[self.navigator.viewer], names=["Navigator"]))
            items.update(self.scanner.scan_selector.viewers_items)
            self.scanner.viewers_items = items


            self.ui.tabWidget.setCurrentIndex(self.ui.tabWidget.addTab(self.ui.tab_navigator, 'Navigator'))

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
                                if '0D' not in viewer.viewer_type:
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
            if self.scan_thread is not None:
                self.command_DAQ_signal.disconnect()
                if self.scan_thread.isRunning():
                    self.scan_thread.exit()
                    while not self.scan_thread.isFinished():
                        QThread.msleep(100)
                    self.scan_thread = None

            self.scan_thread = QThread()

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
            scan_acquisition.moveToThread(self.scan_thread)

            self.command_DAQ_signal[list].connect(scan_acquisition.queue_command)
            scan_acquisition.scan_data_tmp[OrderedDict].connect(self.update_scan_GUI)
            scan_acquisition.status_sig[list].connect(self.thread_status)

            self.scan_thread.scan_acquisition = scan_acquisition
            self.scan_thread.start()

            self.ui.set_scan_pb.setEnabled(False)
            self.ui.set_ini_positions_pb.setEnabled(False)
            self.ui.start_scan_pb.setEnabled(False)
            QtWidgets.QApplication.processEvents()
            self.ui.scan_done_LED.set_as_false()



            self.command_DAQ_signal.emit(["start_acquisition"])

            self.ui.log_message.setText('Running acquisition')

    pyqtSlot(bool)
    def stop_moves(self,overshoot):
        """
            Foreach module of the move module object list, stop motion.

            See Also
            --------
            stop_scan,  DAQ_Move_main.daq_move.stop_Motion
        """
        self.overshoot = overshoot
        self.stop_scan()
        for mod in self.move_modules:
            mod.stop_Motion()


    def stop_scan(self):
        """
            Emit the command_DAQ signal "stop_acquisiion".

            See Also
            --------
            set_ini_positions
        """
        self.ui.log_message.setText('Stoping acquisition')
        self.command_DAQ_signal.emit(["stop_acquisition"])

        if not self.overshoot:
            self.set_ini_positions() #do not set ini position again in case overshoot fired
            status = 'Data Acquisition has been stopped by user'
        else:
            status = 'Data Acquisition has been stopped due to overshoot'

        self.update_status(status, log_type='log')
        self.ui.log_message.setText('')

        self.ui.set_scan_pb.setEnabled(True)
        self.ui.set_ini_positions_pb.setEnabled(True)
        self.ui.start_scan_pb.setEnabled(True)

    @pyqtSlot(list)
    def thread_status(self,status): # general function to get datas/infos from all threads back to the main
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
        if status[0]=="Update_Status":
            if len(status)>2:
                self.update_status(status[1],wait_time=self.wait_time,log_type=status[2])
            else:
                self.update_status(status[1],wait_time=self.wait_time)

        elif status[0]=="Update_scan_index":
            #status[1] = [ind_scan,ind_average]
            self.ind_scan=status[1][0]
            self.ui.indice_scan_sb.setValue(status[1][0])
            self.ind_average = status[1][1]
            self.ui.indice_average_sb.setValue(status[1][1])

        elif status[0]=="Scan_done":
            self.ui.scan_done_LED.set_as_true()
            self.save_scan()
            if not self.overshoot:
                self.set_ini_positions()
            self.ui.set_scan_pb.setEnabled(True)
            self.ui.set_ini_positions_pb.setEnabled(True)
            self.ui.start_scan_pb.setEnabled(True)
        elif status[0]=="Timeout":
            self.ui.log_message.setText('Timeout occurred')

    def update_1D_graph(self,datas):
        """
            Update the 1D graphic window in the Graphic Interface with the given datas.

            Depending of scan type :
                * *'Linear back to start'* scan :
                    * Calibrate axis positions between graph and scan
                    * Update scan datas from the given datas values
                    * Set data on item attribute
                * *'linear'* or else scan :
                    * Calibrate axis positions between graph and scan
                    * Update scan datas from the given datas values

            =============== ============================== =====================================
            **Parameters**    **Type**                      **Description**
            *datas*          Double precision float array   The datas to be showed in the graph
            =============== ============================== =====================================

            See Also
            --------
            update_status
        """
        try:
            self.scan_y_axis=np.array([])
            if not self.plot_1D_ini: #init the datas
                self.plot_1D_ini = True

                self.scan_x_axis=np.min(self.scan_parameters.axis_2D_1)*np.ones((self.scan_parameters.Nsteps))
                self.scan_data_1D=np.zeros((self.scan_parameters.Nsteps,len(datas)))
                if self.settings.child('scan_options', 'scan_average').value() > 1:
                    self.scan_data_1D_average = np.zeros((self.scan_parameters.Nsteps, len(datas)))

                self.ui.scan1D_graph.set_axis_label(axis_settings=dict(orientation='bottom', label=self.move_modules_scan[0].title,
                                    units=self.move_modules_scan[0].settings.child('move_settings','units').value()))
                self.ui.scan1D_graph.set_axis_label(axis_settings=dict(orientation='left', label=self.settings.child('scan_options', 'plot_from').value(), units=''))

            if self.scanner.settings.child('scan_options','scan1D_settings', 'scan1D_selection').value() == 'Manual':
                self.scan_x_axis[self.ind_scan]=self.scan_positions[0][1]
            else: #in case of PolyLines scans, impossible to plot linearly so just use the scan index
                self.scan_x_axis[self.ind_scan] = self.ind_scan
            #to test random mode:
            #self.scan_data_1D[self.ind_scan, :] =np.random.rand((1))* np.array([np.exp(-(self.scan_x_axis[self.ind_scan]-50)**2/20**2),np.exp(-(self.scan_x_axis[self.ind_scan]-50)**6/10**6)]) # np.array(list(datas.values()))
            #self.scan_data_1D[self.ind_scan, :] =  np.array(list(datas.values()))
            self.scan_data_1D[self.ind_scan, :] = np.array([datas[key]['data'] for key in datas])

            if self.settings.child('scan_options', 'scan_average').value() > 1:
                self.scan_data_1D_average[self.ind_scan,:] = (self.ind_average*self.scan_data_1D_average[self.ind_scan,:] +  self.scan_data_1D[self.ind_scan, :])/(self.ind_average+1)


            x_axis_sorted, indices = np.unique(self.scan_x_axis, return_index=True)
            data_sorted = list(self.scan_data_1D.T)
            data_sorted=[data[indices] for data in data_sorted]
            x_axis = dict(data=x_axis_sorted,
                          label=self.move_modules_scan[0].title,
                          units=self.move_modules_scan[0].settings.child('move_settings','units').value())
            self.ui.scan1D_graph.x_axis = x_axis
            self.ui.scan1D_graph.show_data(data_sorted)


            if self.settings.child('scan_options', 'scan_average').value() > 1:
                data_averaged_sorted=list(self.scan_data_1D_average.T)
                data_averaged_sorted = [data[indices] for data in data_averaged_sorted]
                self.ui.average1D_graph.x_axis = x_axis_sorted
                self.ui.average1D_graph.show_data(data_averaged_sorted)

        except Exception as e:
            self.update_status(getLineInfo()+ str(e),wait_time=self.wait_time,log_type='log')

    def update_2D_graph(self,datas):
        """
            Update the 2D graphic window in the Graphic Interface with the given datas (if not none).

            Depending on scan type :
                * *2D scan* :
                    * Calibrate the axis positions between graphic and scan
                    * Update scan datas with the given datas values.
                    * Set an image with the updated scan data
                * *1D scan* :
                    * Calibrate the axis positions between graphic and scan
                    * Update scan datas with the given datas values.
                    * Concatenate 1D vectors to make a 2D image
                    * Set an image with the updated scan data

            =============== =============================== ===========================
            **Parameters**    **Type**                       **Description**
            *datas*           double precision float array   the data values to update
            =============== =============================== ===========================

            See Also
            --------
            update_status
        """
        try:

            if "2D" in self.scanner.settings.child('scan_options','scan_type').value():    #scan2D type cartography
                if not(self.plot_2D_ini):#init the data
                    self.plot_2D_ini=True
                    self.scan_x_axis=self.scan_parameters.axis_2D_1
                    self.scan_y_axis=self.scan_parameters.axis_2D_2
                    self.ui.scan2D_graph.x_axis = dict(data=self.scan_x_axis,
                                units=self.move_modules_scan[0].settings.child('move_settings','units').value(),
                                label=self.move_modules_scan[0].title)
                    self.ui.scan2D_graph.y_axis = dict(data=self.scan_y_axis,
                                units=self.move_modules_scan[1].settings.child('move_settings','units').value(),
                                label=self.move_modules_scan[1].title)

                    self.scan_data_2D=[np.zeros((len(self.scan_parameters.axis_2D_2),len(self.scan_parameters.axis_2D_1))) for ind in range(min((3,len(datas))))]
                    if self.settings.child('scan_options', 'scan_average').value() > 1:
                        self.ui.average2D_graph.x_axis = dict(data=self.scan_x_axis,
                                                           units=self.move_modules_scan[0].settings.child(
                                                               'move_settings', 'units').value(),
                                                           label=self.move_modules_scan[0].title)
                        self.ui.average2D_graph.y_axis = dict(data=self.scan_y_axis,
                                                           units=self.move_modules_scan[1].settings.child(
                                                               'move_settings', 'units').value(),
                                                           label=self.move_modules_scan[1].title)
                        self.scan_data_2D_average = [np.zeros((len(self.scan_parameters.axis_2D_2),len(self.scan_parameters.axis_2D_1))) for ind in range(min((3,len(datas))))]

                pos_axis_1=self.scan_positions[0][1]
                pos_axis_2=self.scan_positions[1][1]
                #self.scan_data_2D_to_save[self.ind_scan,:]=np.concatenate((np.array([pos_axis_1,pos_axis_2]),np.array(datas['datas'][:])))


                ind_pos_axis_1=self.scan_parameters.axis_2D_1_indexes[self.ind_scan]
                ind_pos_axis_2=self.scan_parameters.axis_2D_2_indexes[self.ind_scan]
                for ind_plot in range(min((3,len(datas)))):
                    keys = list(datas.keys())
                    self.scan_data_2D[ind_plot][ind_pos_axis_2,ind_pos_axis_1]=datas[keys[ind_plot]]['data']

                    if self.settings.child('scan_options', 'scan_average').value() > 1:
                        self.scan_data_2D_average[ind_plot][ind_pos_axis_2, ind_pos_axis_1] = \
                            (self.ind_average * self.scan_data_2D_average[ind_plot][ind_pos_axis_2, ind_pos_axis_1] +
                             datas[keys[ind_plot]]['data']) / (self.ind_average + 1)

                self.ui.scan2D_graph.setImage(*self.scan_data_2D)

                if self.settings.child('scan_options', 'scan_average').value() > 1:
                    self.ui.average2D_graph.setImage(*self.scan_data_2D_average)

            else: # scan 1D with concatenation of vectors making a 2D image
                if not(self.plot_2D_ini): #init the data
                    self.plot_2D_ini=True

                    data=datas[list(datas.keys())[0]]
                    Ny=len(data[list(data.keys())[0]])

                    self.scan_y_axis=np.array([])
                    if self.scanner.settings.child('scan_options','scan1D_settings','scan1D_type').value()=='Linear back to start':
                        self.scan_x_axis=self.scan_parameters.axis_2D_1[0::2]
                    else:
                        self.scan_x_axis=self.scan_parameters.axis_2D_1

                    Nx=len(self.scan_x_axis)
                    self.ui.scan2D_graph.x_axis = dict(data=self.scan_x_axis,
                                units=self.move_modules_scan[0].settings.child('move_settings','units').value(),
                                label=self.move_modules_scan[0].title)


                    det_names = [det.title for det in self.detector_modules]
                    ind_plot_det = det_names.index(self.settings.child('scan_options', 'plot_from').value())
                    if 'x_axis'in data.keys():
                        self.scan_y_axis=data['x_axis']['data']
                        label = data['x_axis']['label']
                        units = data['x_axis']['units']
                    else:
                        self.scan_y_axis=np.linspace(0,Ny-1,Ny)
                        label = ''
                        units = ''


                    if self.detector_modules[ind_plot_det].ui.viewers[0].viewer_type == 'Data1D':
                        if label == '':
                            label = self.detector_modules[ind_plot_det].ui.viewers[0].axis_settings['label']
                    if units == '':
                        units = self.detector_modules[ind_plot_det].ui.viewers[0].axis_settings['units']

                    self.ui.scan2D_graph.y_axis = dict(data=self.scan_y_axis,
                                                       units=units,
                                                       label='{:s} {:s}'.format(self.detector_modules[ind_plot_det].title, label))
                    self.scan_data_2D=[]
                    self.scan_data_2D_average = []
                    for ind,key in enumerate(datas):
                        if ind>=3:
                            break
                        self.scan_data_2D.append(np.zeros([datas[key]['data'].shape[0]]+[Nx]))
                        if self.settings.child('scan_options', 'scan_average').value() > 1:
                            self.scan_data_2D_average.append(np.zeros([datas[key]['data'].shape[0]]+[Nx]))

                if self.scanner.settings.child('scan_options','scan1D_settings','scan1D_type').value()=='Linear back to start':
                    if not utils.odd_even(self.ind_scan):
                        for ind_plot,key in enumerate(datas.keys()):
                            self.scan_data_2D[ind_plot][:,int(self.ind_scan/2)]=datas[key]['data']
                            if self.settings.child('scan_options', 'scan_average').value() > 1:
                                self.scan_data_2D_average[ind_plot][:,int(self.ind_scan/2)]=\
                                (self.ind_average*self.scan_data_2D_average[ind_plot][:,int(self.ind_scan/2)]+datas[key]['data'])/(self.ind_average+1)

                else:
                    ind_scan = utils.find_index(self.scan_x_axis,self.scan_positions[0][1])[0][0]
                    for ind_plot,key in enumerate(datas.keys()):
                        if ind_plot >= 3:
                            break
                        self.scan_data_2D[ind_plot][:,ind_scan]=datas[key]['data']

                        if self.settings.child('scan_options', 'scan_average').value() > 1:
                            self.scan_data_2D_average[ind_plot][:, ind_scan] = (self.ind_average*self.scan_data_2D_average[ind_plot][:, ind_scan]+datas[key]['data']) / (self.ind_average+1)

                self.ui.scan2D_graph.setImage(*self.scan_data_2D)
                if self.settings.child('scan_options', 'scan_average').value() > 1:
                    self.ui.average2D_graph.setImage(*self.scan_data_2D_average)


        except Exception as e:
            self.update_status(getLineInfo()+ str(e),wait_time=self.wait_time,log_type='log')

    def update_file_settings(self,new_file=False):
        try:
            if self.h5saver.current_scan_group is None:
                new_file = True


            if new_file:
                self.set_metadata_about_dataset()
                self.save_metadata(self.h5saver.raw_group, 'dataset_info')

            if self.h5saver.current_scan_name is None:
                self.h5saver.add_scan_group()
            elif not self.h5saver.is_node_in_group(self.h5saver.raw_group, self.h5saver.current_scan_name):
                self.h5saver.add_scan_group()

            if self.navigator is not None:
                self.navigator.update_h5file(self.h5saver.h5_file)
                self.navigator.settings.child('settings', 'filepath').setValue(self.h5saver.h5_file.filename)

            #set attributes to the current group, such as scan_type....
            self.scan_attributes.child('scan_info','scan_type').setValue(self.scanner.settings.child('scan_options','scan_type').value())
            self.scan_attributes.child('scan_info','scan_name').setValue(self.h5saver.current_scan_group._v_name)
            self.scan_attributes.child('scan_info','description').setValue(self.h5saver.current_scan_group._v_attrs['description'])
            res = self.set_metadata_about_current_scan()
            self.save_metadata(self.h5saver.current_scan_group,'scan_info')
            return res

        except Exception as e:
            self.update_status(getLineInfo()+ str(e),wait_time=self.wait_time,log_type='log')

    def update_plot_det_items(self,param):
        """
            Add the scan_options-plot_form child to the DAQscan_settings tree from the selected value of the given parameter.

            =============== ================================= ========================
            **Parameters**    **Type**                         **Description**
            *param*           instance of pyqtgraph parameter  the parameter to treat
            =============== ================================= ========================
        """
        items=param.value()['selected']
        self.settings.child('scan_options', 'plot_from').setOpts(limits=items)


    @pyqtSlot(OrderedDict)
    def update_scan_GUI(self, datas):
        """
            Update the graph in the Graphic Interface from the given datas switching 0D/1D/2D consequently.

            =============== =============================== ===========================
            **Parameters**    **Type**                       **Description**
            *datas*           double precision float array   the data values to update
            =============== =============================== ===========================

            See Also
            --------
            update_2D_graph, update_1D_graph, update_status
        """
        #datas=edict(positions=self.scan_read_positions,datas=self.scan_read_datas)
        self.scan_positions=datas['positions']
        try:
            if "2D" in self.scanner.settings.child('scan_options','scan_type').value(): #means 2D cartography type scan
                if 'data0D' in datas['datas'].keys():
                    if not (datas['datas']['data0D'] is None or datas['datas']['data0D'] == OrderedDict()):
                        self.update_2D_graph(datas['datas']['data0D'])
                    else:
                        self.scan_data_2D = []
                #if 'data1D' in datas['datas'].keys():
                #    self.update_3D_graph(data['datas']['data1D'])
            else:
                if 'data0D' in datas['datas'].keys():
                    if not( datas['datas']['data0D'] is None or datas['datas']['data0D'] == OrderedDict()):
                        self.update_1D_graph(datas['datas']['data0D'])
                    else:
                        self.scan_data_1D = []
                if 'data1D' in datas['datas'].keys():
                    if not( datas['datas']['data1D'] is None or datas['datas']['data1D'] == OrderedDict()):
                        self.update_2D_graph(datas['datas']['data1D'])
                    else:
                        self.scan_data_2D = []

        except Exception as e:
            self.update_status(getLineInfo()+ str(e),wait_time=self.wait_time,log_type='log')


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
                data_types.append('data2D')

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
                        data_types.append('data2D')


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
    app = QtWidgets.QApplication(sys.argv)

    splash_path = os.path.join(os.path.split(__file__)[0],'splash.png')
    splash = QtGui.QPixmap(splash_path)
    if splash is None:
        print('no splash')
    splash_sc=QtWidgets.QSplashScreen(splash, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

    splash_sc.show()
    QtWidgets.QApplication.processEvents()
    splash_sc.raise_()
    splash_sc.showMessage('Loading Main components',color=Qt.white)
    QtWidgets.QApplication.processEvents()
    QtWidgets.QApplication.processEvents()

    win = QtWidgets.QMainWindow()
    win.setVisible(False)
    area = utils.DockArea()
    win.setCentralWidget(area)
    win.resize(1000,500)
    win.setWindowTitle('pymodaq Scan')

    #win.setVisible(False)
    prog = DAQ_Scan(area)
    QThread.sleep(0)
    win.show()
    splash_sc.finish(win)
    #win.setVisible(True)
    
    
    sys.exit(app.exec_())


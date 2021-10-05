#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Automated scanning module functionalities for PyMoDAQ

Contains all objects related to the DAQ_Scan module, to do automated scans, saving data...
"""

import sys
from collections import OrderedDict
import numpy as np
from pathlib import Path
import os

import pymodaq.daq_utils.parameter.ioxml

from pyqtgraph.parametertree import Parameter, ParameterTree
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QDate, QTime
from pymodaq.daq_utils import exceptions
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D
from pymodaq.daq_utils.plotting.viewer1D.viewer1D_main import Viewer1D
from pymodaq.daq_utils.plotting.viewer1D.viewer1Dbasic import Viewer1DBasic
from pymodaq.daq_utils.plotting.navigator import Navigator
from pymodaq.daq_utils.scanner import Scanner, adaptive, adaptive_losses
from pymodaq.daq_utils.managers.batchscan_manager import BatchScanner
from pymodaq.daq_utils.managers.modules_manager import ModulesManager
from pymodaq.daq_utils.plotting.qled import QLED

from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils import gui_utils as gutils
from pymodaq.daq_utils.h5modules import H5Saver
from pymodaq.daq_utils.parameter.pymodaq_ptypes import GroupParameterCustom as GroupParameter

config = utils.load_config()
logger = utils.set_logger(utils.get_module_name(__file__))



class DAQ_Scan(QObject):
    """
    Main class initializing a DAQ_Scan module with its dashboard and scanning control panel
    """
    command_DAQ_signal = pyqtSignal(list)
    status_signal = pyqtSignal(str)

    params = [
        {'title': 'Time Flow:', 'name': 'time_flow', 'type': 'group', 'expanded': False, 'children': [
            {'title': 'Wait time step (ms)', 'name': 'wait_time', 'type': 'int', 'value': 0,
             'tip': 'Wait time in ms after each step of acquisition (move and grab)'},
            {'title': 'Wait time between (ms)', 'name': 'wait_time_between', 'type': 'int',
             'value': 0,
             'tip': 'Wait time in ms between move and grab processes'},
            {'title': 'Timeout (ms)', 'name': 'timeout', 'type': 'int', 'value': 10000},
        ]},
        {'title': 'Scan options', 'name': 'scan_options', 'type': 'group', 'children': [
            {'title': 'Naverage:', 'name': 'scan_average', 'type': 'int', 'value': 1, 'min': 1},
            {'title': 'Plot from:', 'name': 'plot_from', 'type': 'list'}, ]},
    ]

    def __init__(self, dockarea=None, dashboard=None):
        """

        Parameters
        ----------
        dockarea: (dockarea) instance of the modified pyqtgraph Dockarea (see daq_utils)
        dashboard: (DashBoard) instance of the pymodaq dashboard
        """
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        logger.info('Initializing DAQ_Scan')
        super().__init__()
        self.dockarea = dockarea
        self.dashboard = dashboard
        if dashboard is None:
            raise Exception('No valid dashboard initialized')
        self.mainwindow = self.dockarea.parent()

        self.wait_time = 1000
        self.navigator = None
        self.scan_x_axis = None
        self.scan_y_axis = None
        self.scan_data_1D = np.array([])
        self.scan_data_1D_average = np.array([])
        self.scan_data_2D = []
        self.scan_data_2D_average = []
        self.curvilinear_values = []
        self.ind_scan = 0
        self.ind_average = 0
        self.scan_positions = []
        self.scan_data_2D_to_save = []
        self.scan_data_1D_to_save = []
        self.plot_1D_ini = False
        self.plot_2D_ini = False

        self.scan_thread = None
        self.modules_manager = ModulesManager(self.dashboard.detector_modules, self.dashboard.actuators_modules)

        self.h5saver = H5Saver()
        self.h5saver.settings.child(('do_save')).hide()
        self.h5saver.settings.child(('custom_name')).hide()
        self.h5saver.new_file_sig.connect(self.create_new_file)
        self.h5arrays = OrderedDict([])

        self.scanner = Scanner(actuators=self.modules_manager.actuators, adaptive_losses=adaptive_losses)
        self.scan_parameters = None

        self.batcher = None
        self.batch_started = False
        self.ind_batch = 0


        self.modules_manager.actuators_changed[list].connect(self.update_actuators)
        self.modules_manager.detectors_changed[list].connect(self.update_plot_det_items)

        self.setupUI()
        self.setup_modules(self.dashboard.title)
        self.set_config()
        self.scanner.set_config()

        logger.info('DAQ_Scan Initialized')

    def set_config(self):
        self.settings.child('time_flow', 'wait_time').setValue(config['scan']['timeflow']['wait_time'])
        self.settings.child('time_flow', 'wait_time_between').setValue(config['scan']['timeflow']['wait_time'])
        self.settings.child('time_flow', 'timeout').setValue(config['scan']['timeflow']['timeout'])

        self.settings.child('scan_options',  'scan_average').setValue(config['scan']['Naverage'])

    @pyqtSlot(list)
    def update_actuators(self, actuators):
        self.scanner.actuators = actuators

    def create_average_dock(self):
        self.ui.average_dock = gutils.Dock("Averaging")
        average_tab = QtWidgets.QTabWidget()
        average1D_widget = QtWidgets.QWidget()
        average2D_widget = QtWidgets.QWidget()

        # %% init the 1D viewer
        self.ui.average1D_graph = Viewer1D(average1D_widget)

        # %% init the 2D viewer
        self.ui.average2D_graph = Viewer2D(average2D_widget)

        average_tab.addTab(average1D_widget, '1D plot Average')
        average_tab.addTab(average2D_widget, '2D plot Average')

        self.ui.average_dock.addWidget(average_tab)
        self.dockarea.addDock(self.ui.average_dock, 'right', self.ui.scan_dock)

        self.ui.average_dock.setVisible(False)

    def create_menu(self):
        """
        """
        # %% create Settings menu

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
        action_batcher = self.settings_menu.addAction('Show Batch Scanner')
        action_batcher.triggered.connect(lambda: self.show_batcher(menubar))

    def show_batcher(self, menubar):
        self.batcher = BatchScanner(self.dockarea, self.modules_manager.actuators_name,
                                    self.modules_manager.detectors_name)
        self.batcher.create_menu(menubar)
        self.batcher.setupUI()
        self.ui.start_batch_pb.setVisible(True)

    def load_file(self):
        self.h5saver.load_file(self.h5saver.h5_file_path)

    def move_to_crosshair(self, posx=None, posy=None):
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
        try:
            if self.ui.move_to_crosshair_cb.isChecked():
                if "2D" in self.scanner.settings.child('scan_type').value():
                    if len(self.modules_manager.actuators) == 2 and posx is not None and posy is not None:
                        posx_real = posx * self.ui.scan2D_graph.scaled_xaxis.scaling + self.ui.scan2D_graph.scaled_xaxis.offset
                        posy_real = posy * self.ui.scan2D_graph.scaled_yaxis.scaling + self.ui.scan2D_graph.scaled_yaxis.offset
                        self.move_at(posx_real, posy_real)
                    else:
                        self.update_status("not valid configuration, check number of stages and scan2D option",
                                           log_type='log')
        except Exception as e:
            logger.exception(str(e))
            # self.update_status(getLineInfo()+ str(e),log_type='log')

    def move_at(self, posx_real, posy_real):
        self.command_DAQ_signal.emit(["move_stages", [posx_real, posy_real]])

    def quit_fun(self):
        """
            Quit the current instance of DAQ_scan and close on cascade move and detector modules.

            See Also
            --------
            quit_fun
        """
        try:
            self.h5saver.close_file()
            self.ui.average_dock.close()
            self.ui.scan_dock.close()

        except Exception as e:
            logger.exception(str(e))

    def save_scan(self):
        """
        save live data and adds metadata to write that the scan is done
        """
        try:
            scan_type = self.scanner.scan_parameters.scan_type
            isadaptive = self.scanner.scan_parameters.scan_subtype == 'Adaptive'

            self.h5saver.current_scan_group.attrs['scan_done'] = True
            self.h5saver.init_file(addhoc_file_path=self.h5saver.settings.child(('current_h5_file')).value())
            # create Live scan node (may be empty if no possible live data could be plotted) but mandatory for
            # incrementing scan index, otherwise current scan is overwritten
            if scan_type == 'Scan1D' or \
                    (scan_type == 'Sequential' and self.scanner.scan_parameters.Naxes == 1) or \
                    (scan_type == 'Sequential' and self.scanner.scan_parameters.Naxes > 2) or \
                    scan_type == 'Tabular':
                live_group = self.h5saver.add_live_scan_group(self.h5saver.current_scan_group, '1D', title='',
                                                              settings_as_xml='', metadata=dict([]))
            else:  # scan_type == 'Scan2D' or\
                #  (scan_type == 'Sequential' and self.scanner.scan_parameters.Naxes == 2):
                live_group = self.h5saver.add_live_scan_group(self.h5saver.current_scan_group, '2D', title='',
                                                              settings_as_xml='', metadata=dict([]))

            # save scan1D
            if len(self.scan_data_1D) != 0:

                if self.settings.child('scan_options', 'scan_average').value() <= 1:
                    datas = OrderedDict([])
                    for ind in range(self.scan_data_1D.shape[1]):
                        datas['Scan_Data_{:03d}'.format(ind)] = OrderedDict([])
                        datas['Scan_Data_{:03d}'.format(ind)]['data'] = self.scan_data_1D[:, ind]
                        if len(self.scan_data_1D[:, 0]) > 1:  # means data are 1D (so save corresponding axis)
                            if scan_type == 'Scan1D' or \
                                    (scan_type == 'Sequential' and self.scanner.scan_parameters.Naxes == 1):
                                datas['Scan_Data_{:03d}'.format(ind)]['x_axis'] = utils.Axis(
                                    data=self.scan_x_axis,
                                    units=self.modules_manager.actuators[0].settings.child(
                                        'move_settings', 'units').value(),
                                    label=self.modules_manager.actuators[0].title)
                            else:
                                datas['Scan_Data_{:03d}'.format(ind)]['x_axis'] = utils.Axis(data=self.scan_x_axis,
                                                                                             units='',
                                                                                             label='Scan indexes')

                    for ind_channel, channel in enumerate(datas):  # list of OrderedDict
                        channel_group = self.h5saver.add_CH_group(live_group, title=channel)
                        self.h5saver.add_data_live_scan(channel_group, datas['Scan_Data_{:03d}'.format(ind_channel)],
                                                        scan_type='scan1D',
                                                        scan_subtype=self.scanner.scan_parameters.scan_subtype)

                else:
                    averaged_datas = OrderedDict([])
                    for ind in range(self.scan_data_1D.shape[1]):
                        averaged_datas['Scan_Data_{:03d}'.format(ind)] = OrderedDict([])
                        averaged_datas['Scan_Data_{:03d}'.format(ind)]['data'] = self.scan_data_1D_average[:, ind]
                        if scan_type == 'Scan1D' or \
                                (scan_type == 'Sequential' and self.scanner.scan_parameters.Naxes == 1):
                            averaged_datas['Scan_Data_{:03d}'.format(ind)]['x_axis'] = utils.Axis(
                                data=self.scan_x_axis,
                                units=self.modules_manager.actuators[0].settings.child(
                                    'move_settings', 'units').value(),
                                label=self.modules_manager.actuators[0].title)
                        else:
                            averaged_datas['Scan_Data_{:03d}'.format(ind)]['x_axis'] = utils.Axis(
                                data=self.scan_x_axis, units='', label='Scan indexes')

                    for ind_channel, channel in enumerate(averaged_datas):  # list of OrderedDict
                        channel_group = self.h5saver.add_CH_group(live_group, title=channel)
                        self.h5saver.add_data_live_scan(channel_group,
                                                        averaged_datas['Scan_Data_{:03d}'.format(ind_channel)],
                                                        scan_type='scan1D',
                                                        scan_subtype=self.scanner.scan_parameters.scan_subtype)

                if self.settings.child('scan_options', 'scan_average').value() > 1:
                    string = gutils.widget_to_png_to_bytes(self.ui.average1D_graph.parent)
                else:
                    string = gutils.widget_to_png_to_bytes(self.ui.scan1D_graph.parent)
                live_group.attrs['pixmap1D'] = string

            elif self.scan_data_2D != []:  #if live data is saved as 1D not needed to save as 2D

                if len(self.modules_manager.actuators) == 1:
                    scan_type = 'scan1D'
                elif len(self.modules_manager.actuators) == 2:
                    scan_type = 'scan2D'
                if not isadaptive:
                    if self.settings.child('scan_options', 'scan_average').value() <= 1:
                        datas = OrderedDict([])
                        for ind, data2D in enumerate(self.scan_data_2D):
                            datas['Scan_Data_{:03d}'.format(ind)] = OrderedDict([])
                            datas['Scan_Data_{:03d}'.format(ind)]['data'] = data2D.T
                            datas['Scan_Data_{:03d}'.format(ind)]['x_axis'] = dict(
                                data=self.ui.scan2D_graph.x_axis,
                                units=self.ui.scan2D_graph.scaling_options['scaled_xaxis']['units'],
                                label=self.ui.scan2D_graph.scaling_options['scaled_xaxis']['label'])
                            if scan_type == 'scan2D':
                                datas['Scan_Data_{:03d}'.format(ind)]['y_axis'] = dict(
                                    data=self.ui.scan2D_graph.y_axis,
                                    units=self.ui.scan2D_graph.scaling_options['scaled_yaxis']['units'],
                                    label=self.ui.scan2D_graph.scaling_options['scaled_yaxis']['label'])

                        for ind_channel, channel in enumerate(datas):  # list of OrderedDict
                            channel_group = self.h5saver.add_CH_group(live_group, title=channel)
                            self.h5saver.add_data_live_scan(channel_group,
                                                            datas['Scan_Data_{:03d}'.format(ind_channel)],
                                                            scan_type=scan_type,
                                                            scan_subtype=self.scanner.scan_parameters.scan_subtype)

                    else:
                        averaged_datas = OrderedDict([])
                        for ind, data2D in enumerate(self.scan_data_2D_average):
                            averaged_datas['Scan_Data_{:03d}'.format(ind)] = OrderedDict([])
                            averaged_datas['Scan_Data_{:03d}'.format(ind)]['data'] = data2D.T
                            averaged_datas['Scan_Data_{:03d}'.format(ind)]['x_axis'] = dict(
                                data=self.ui.scan2D_graph.x_axis,
                                units=self.ui.scan2D_graph.scaling_options['scaled_xaxis']['units'],
                                label=self.ui.scan2D_graph.scaling_options['scaled_xaxis']['label'], )
                            if scan_type == 'scan2D':
                                averaged_datas['Scan_Data_{:03d}'.format(ind)]['y_axis'] = dict(
                                    data=self.ui.scan2D_graph.y_axis,
                                    units=self.ui.scan2D_graph.scaling_options['scaled_yaxis']['units'],
                                    label=self.ui.scan2D_graph.scaling_options['scaled_yaxis']['label'])

                        for ind_channel, channel in enumerate(averaged_datas):  # dict of OrderedDict
                            channel_group = self.h5saver.add_CH_group(live_group, title=channel)
                            self.h5saver.add_data_live_scan(channel_group, averaged_datas[
                                'Scan_Data_{:03d}'.format(ind_channel)],
                                scan_type=scan_type, scan_subtype=self.scanner.scan_parameters.scan_subtype)

                else:
                    channel_group = self.h5saver.add_CH_group(live_group, title='Scan_Data_000')
                    self.h5saver.add_data_live_scan(channel_group, dict(data=self.scan_data_2D[:, 2],
                                                                        x_axis=self.scan_data_2D[:, 0],
                                                                        y_axis=self.scan_data_2D[:, 1]),
                                                    scan_type=scan_type,
                                                    scan_subtype=self.scanner.scan_parameters.scan_subtype)

                if self.settings.child('scan_options', 'scan_average').value() > 1:
                    string = gutils.widget_to_png_to_bytes(self.ui.average2D_graph.parent)
                else:
                    string = gutils.widget_to_png_to_bytes(self.ui.scan2D_graph.parent)
                live_group.attrs['pixmap2D'] = string

            if self.navigator is not None:
                self.navigator.update_2Dscans()

        except Exception as e:
            logger.exception(str(e))

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

        attr = node.attrs
        if type_info == 'dataset_info':
            attr['type'] = 'dataset'
            params = self.dataset_attributes
        else:
            attr['type'] = 'scan'
            params = self.scan_attributes
        for child in params.child((type_info)).children():
            if type(child.value()) is QDateTime:
                attr[child.name()] = child.value().toString('dd/mm/yyyy HH:MM:ss')
            else:
                attr[child.name()] = child.value()
        if type_info == 'dataset_info':
            # save contents of given parameter object into an xml string under the attribute settings
            settings_str = b'<All_settings title="All Settings" type="group">' + \
                           pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(params) + \
                           pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(self.settings)
                           # pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(
                           #     self.dashboard.preset_manager.preset_params) +\
            settings_str += b'</All_settings>'
            attr['settings'] = settings_str

        elif type_info == 'scan_info':
            settings_all = [pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(params),
                           pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(self.settings),
                           pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(self.h5saver.settings),
                           pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(self.scanner.settings)]

            settings_str = b'<All_settings title="All Settings" type="group">'
            for set in settings_all:
                if len(settings_str + set) < 60000:
                    # size limit for any object header (including all the other attributes) is 64kb
                    settings_str += set
                else:
                    break
            settings_str += b'</All_settings>'
            attr['settings'] = settings_str

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
                if param.name() == 'scan_average':
                    self.show_average_dock(param.value() > 1)

            elif change == 'parent':
                pass

    def show_average_dock(self, show=True):
        self.ui.average_dock.setVisible(show)
        self.ui.indice_average_sb.setVisible(show)
        if show:
            self.ui.average_dock.setStretch(100, 100)

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
        date = QDateTime(QDate.currentDate(), QTime.currentTime())
        self.scan_attributes.child('scan_info', 'date_time').setValue(date)
        self.scan_attributes.child('scan_info', 'author').setValue(
            self.dataset_attributes.child('dataset_info', 'author').value())
        if not self.batch_started:
            res = self.show_file_attributes('scan')
        else:
            res = True
        return res

    def set_metadata_about_dataset(self):
        """
            Set the date value of the data_set_info-date_time child of the data_set_attributes tree.
            Show the 'dataset' file attributes.

            See Also
            --------
            show_file_attributes
        """
        date = QDateTime(QDate.currentDate(), QTime.currentTime())
        self.dataset_attributes.child('dataset_info', 'date_time').setValue(date)
        res = self.show_file_attributes('dataset')
        return res

    def setup_modules(self, filename):
        """

        """
        try:

            ######################################################################
            # set scan selector
            items = OrderedDict()
            if self.navigator is not None:
                items["Navigator"] = dict(viewers=[self.navigator.viewer], names=["Navigator"])
            for det in self.modules_manager.detectors_all:
                if len([view for view in det.ui.viewers if view.viewer_type == 'Data2D']) != 0:
                    items[det.title] = dict(viewers=[view for view in det.ui.viewers if view.viewer_type == 'Data2D'],
                                            names=[view.title for view in det.ui.viewers if
                                                   view.viewer_type == 'Data2D'], )
            items["DAQ_Scan"] = dict(viewers=[self.ui.scan2D_graph], names=["DAQ_Scan"])

            if self.navigator is not None:
                items = OrderedDict(Navigator=dict(viewers=[self.navigator.viewer], names=["Navigator"]))
                items.update(self.scanner.scan_selector.viewers_items)

            self.scanner.viewers_items = items

            self.scanner.scan_selector.widget.setVisible(False)
            self.scanner.scan_selector.settings.child('scan_options', 'scan_type').hide()

            self.scanner.scan_selector.widget.setVisible(False)
            self.scanner.scan_selector.show_scan_selector(visible=False)

            # setting moves and det in tree
            preset_items_det = [mod for ind, mod in enumerate(self.modules_manager.detectors_all) if ind == 0]
            self.settings.child('scan_options', 'plot_from').setLimits([mod.title for mod in preset_items_det])
            if preset_items_det != []:
                self.settings.child('scan_options', 'plot_from').setValue(preset_items_det[0].title)

            self.show_average_dock(False)

            self.ui.scan_dock.setEnabled(True)
            self.file_menu.setEnabled(True)
            self.settings_menu.setEnabled(True)
            self.create_new_file(True)

        except Exception as e:
            logger.exception(str(e))
            # self.update_status(getLineInfo()+str(e), self.wait_time, log_type='log')

    def create_new_file(self, new_file):
        self.h5saver.init_file(update_h5=new_file)
        res = self.update_file_settings(new_file)
        self.h5saver.current_scan_group.attrs['scan_done'] = False
        if new_file:
            self.ui.start_scan_pb.setEnabled(False)
            self.ui.stop_scan_pb.setEnabled(False)
        return res

    def set_scan(self, scan=None):
        """
        Sets the current scan given the selected settings. Makes some checks, increments the h5 file scans.
        In case the dialog is cancelled, return False and aborts the scan
        """
        try:
            # set the filename and path
            res = self.create_new_file(False)
            if not res:
                return

            # reinit these objects
            self.scan_data_1D = []
            self.scan_data_1D_average = []
            self.scan_data_2D = []
            self.scan_data_2D_average = []

            scan_params = self.scanner.set_scan()
            if scan_params.scan_info.positions is None:
                gutils.show_message(f"An error occurred when establishing the scan steps. Actual settings "
                                    f"gives approximately {int(scan_params.Nsteps)} steps."
                                    f" Please check the steps number "
                                    f"limit in the config file ({config['scan']['steps_limit']}) or modify"
                                    f" your scan settings.")


            if len(self.modules_manager.actuators) != self.scanner.scan_parameters.Naxes:
                gutils.show_message("There are not enough or too much selected move modules for this scan")
                return

            if self.scanner.scan_parameters.scan_subtype == 'Adaptive':
                if len(self.modules_manager.get_selected_probed_data('0D')) == 0:
                    gutils.show_message("In adaptive mode, you have to pick a 0D signal from which the algorithm will"
                                   " determine the next positions to scan, see 'probe_data' in the modules selector"
                                   " panel")
                    return

            self.ui.N_scan_steps_sb.setValue(self.scanner.scan_parameters.Nsteps)

            # check if the modules are initialized
            for module in self.modules_manager.actuators:
                if not module.initialized_state:
                    raise exceptions.DAQ_ScanException('module ' + module.title + " is not initialized")

            for module in self.modules_manager.detectors:
                if not module.initialized_state:
                    raise exceptions.DAQ_ScanException('module ' + module.title + " is not initialized")

            self.ui.start_scan_pb.setEnabled(True)
            self.ui.stop_scan_pb.setEnabled(True)

            return True

        except Exception as e:
            logger.exception(str(e))
            self.ui.start_scan_pb.setEnabled(False)
            self.ui.stop_scan_pb.setEnabled(False)

    def setupUI(self):
        self.ui = QObject()
        widgetsettings = QtWidgets.QWidget()
        self.ui.verticalLayout = QtWidgets.QVBoxLayout()
        widgetsettings.setLayout(self.ui.verticalLayout)
        self.ui.StatusBarLayout = QtWidgets.QHBoxLayout()
        self.ui.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.ui.verticalLayout.addWidget(self.ui.splitter)
        self.ui.verticalLayout.addLayout(self.ui.StatusBarLayout)

        self.ui.horizontalLayout = QtWidgets.QHBoxLayout()
        sett_widget = QtWidgets.QWidget()
        self.ui.settings_layout = QtWidgets.QVBoxLayout()
        sett_widget.setLayout(self.ui.settings_layout)
        self.ui.horizontalLayout.addWidget(sett_widget)

        # ###########################BUTTONS##################
        widget_buttons = QtWidgets.QWidget()
        self.ui.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        widget_buttons.setLayout(self.ui.horizontalLayout_2)

        iconquit = QtGui.QIcon()
        iconquit.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/close2.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.quit_pb = QtWidgets.QPushButton(iconquit, 'Quit')

        iconstart = QtGui.QIcon()
        iconstart.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/run2.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.start_scan_pb = QtWidgets.QPushButton(iconstart, '')
        self.ui.start_scan_pb.setToolTip('Start Scan')

        iconstop = QtGui.QIcon()
        iconstop.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/stop.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.stop_scan_pb = QtWidgets.QPushButton(iconstop, '')
        self.ui.stop_scan_pb.setToolTip('Stop Scan (or skip current one if Batch scan running)')

        self.ui.set_scan_pb = QtWidgets.QPushButton('Set Scan')
        self.ui.set_scan_pb.setToolTip('Process the scanner settings and prepare the modules for coming scan')
        self.ui.set_ini_positions_pb = QtWidgets.QPushButton('Init Positions')
        self.ui.set_ini_positions_pb.setToolTip(
            'Set Move Modules to their initial position as defined in the current scan')

        iconstartbatch = QtGui.QIcon()
        iconstartbatch.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/run_all.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.start_batch_pb = QtWidgets.QPushButton(iconstartbatch, '')
        self.ui.start_batch_pb.setToolTip('Start the batch of scans defined in the batch manager')
        self.ui.start_batch_pb.setVisible(False)

        self.ui.horizontalLayout_2.addWidget(self.ui.quit_pb)
        self.ui.horizontalLayout_2.addStretch()
        self.ui.horizontalLayout_2.addWidget(self.ui.set_scan_pb)
        self.ui.horizontalLayout_2.addWidget(self.ui.set_ini_positions_pb)
        self.ui.horizontalLayout_2.addWidget(self.ui.start_batch_pb)
        self.ui.horizontalLayout_2.addWidget(self.ui.start_scan_pb)
        self.ui.horizontalLayout_2.addWidget(self.ui.stop_scan_pb)

        self.ui.settings_layout.addWidget(widget_buttons)
        self.ui.splitter.addWidget(sett_widget)

        # ##################TAB########################################
        self.ui.tabWidget = QtWidgets.QTabWidget()

        self.ui.tab_plot1D = QtWidgets.QWidget()
        self.ui.scan1D_layout = QtWidgets.QVBoxLayout()
        self.ui.tab_plot1D.setLayout(self.ui.scan1D_layout)

        self.ui.tab_plot2D = QtWidgets.QWidget()
        self.ui.scan2D_layout = QtWidgets.QVBoxLayout()
        self.ui.tab_plot2D.setLayout(self.ui.scan2D_layout)

        self.ui.tab_navigator = QtWidgets.QWidget()
        self.ui.navigator_layout = QtWidgets.QVBoxLayout()
        self.ui.tab_navigator.setLayout(self.ui.navigator_layout)

        self.ui.tabWidget.addTab(self.ui.tab_plot1D, "")
        self.ui.tabWidget.addTab(self.ui.tab_plot2D, "")
        self.ui.tabWidget.addTab(self.ui.tab_navigator, "")
        self.ui.tabWidget.setTabText(self.ui.tabWidget.indexOf(self.ui.tab_plot1D), '1D plot')
        self.ui.tabWidget.setTabText(self.ui.tabWidget.indexOf(self.ui.tab_plot2D), '2D plot')
        self.ui.tabWidget.setTabText(self.ui.tabWidget.indexOf(self.ui.tab_navigator), 'Navigator')

        self.ui.splitter.addWidget(self.ui.tabWidget)
        ##################################################################

        # %% create scan dock and make it a floating window
        self.ui.scan_dock = gutils.Dock("Scan", size=(1, 1), autoOrientation=False)  # give this dock the minimum possible size
        self.ui.scan_dock.setOrientation('vertical')
        self.ui.scan_dock.addWidget(widgetsettings)

        self.dockarea.addDock(self.ui.scan_dock, 'left')
        self.ui.scan_dock.float()

        # %% init the 1D viewer
        self.ui.scan1D_graph_widget = QtWidgets.QSplitter(orientation=QtCore.Qt.Vertical)
        self.ui.scan1D_layout.addWidget(self.ui.scan1D_graph_widget)

        scan1D_widget = QtWidgets.QWidget()
        self.ui.scan1D_graph = Viewer1D(scan1D_widget)
        self.ui.scan1D_graph_widget.addWidget(scan1D_widget)

        # this subgraph is used to display axes values when performing scans as a function of multiple axes, and so
        # impossible to plot in usual 1D or 2D graphs
        scan1D_subgraph_widget = QtWidgets.QWidget()
        self.ui.scan1D_subgraph = Viewer1DBasic(scan1D_subgraph_widget)
        self.ui.scan1D_graph_widget.addWidget(scan1D_subgraph_widget)
        self.ui.scan1D_subgraph.show(False)

        # %% init the 2D viewer
        self.ui.scan2D_graph_widget = QtWidgets.QSplitter(orientation=QtCore.Qt.Vertical)
        self.ui.scan2D_layout.addWidget(self.ui.scan2D_graph_widget)

        scan2D_graph_widget = QtWidgets.QWidget()
        self.ui.scan2D_graph = Viewer2D(scan2D_graph_widget)
        self.ui.scan2D_graph_widget.addWidget(scan2D_graph_widget)

        # this subgraph is used to display axes values when performing scans as a function of multiple axes, and so
        # impossible to plot in usual 1D or 2D graphs
        scan2D_subgraph_widget = QtWidgets.QWidget()
        self.ui.scan2D_subgraph = Viewer1DBasic(scan2D_subgraph_widget)
        self.ui.scan2D_graph_widget.addWidget(scan2D_subgraph_widget)
        self.ui.scan2D_subgraph.show(False)

        self.ui.scan2D_graph.ui.Show_histogram.setChecked(False)
        self.ui.scan2D_graph.ui.histogram_blue.setVisible(False)
        self.ui.scan2D_graph.ui.histogram_green.setVisible(False)
        self.ui.scan2D_graph.ui.histogram_red.setVisible(False)
        self.ui.scan2D_graph.ui.Ini_plot_pb.setVisible(False)
        self.ui.scan2D_graph.ui.FlipUD_pb.setVisible(False)
        self.ui.scan2D_graph.ui.FlipLR_pb.setVisible(False)
        self.ui.scan2D_graph.ui.rotate_pb.setVisible(False)

        self.move_to_crosshair_action = gutils.QAction(
            QtGui.QIcon(QtGui.QPixmap(':/icons/Icon_Library/move_contour.png')),"Move at doubleClicked")
        self.move_to_crosshair_action.setCheckable(True)
        self.ui.move_to_crosshair_cb = self.move_to_crosshair_action

        self.ui.scan2D_graph.toolbar_button.addAction(self.move_to_crosshair_action)
        self.ui.scan2D_graph.sig_double_clicked.connect(self.move_to_crosshair)

        # %% init and set the status bar
        self.ui.statusbar = QtWidgets.QStatusBar(self.dockarea)
        self.ui.statusbar.setMaximumHeight(25)
        self.ui.StatusBarLayout.addWidget(self.ui.statusbar)
        self.ui.status_message = QtWidgets.QLabel('Initializing')
        self.ui.statusbar.addPermanentWidget(self.ui.status_message)
        self.ui.N_scan_steps_sb = gutils.QSpinBox_ro()
        self.ui.N_scan_steps_sb.setToolTip('Total number of steps')
        self.ui.indice_scan_sb = gutils.QSpinBox_ro()
        self.ui.indice_scan_sb.setToolTip('Current step value')
        self.ui.indice_average_sb = gutils.QSpinBox_ro()
        self.ui.indice_average_sb.setToolTip('Current average value')
        self.ui.scan_done_LED = QLED()
        self.ui.scan_done_LED.setToolTip('Scan done state')
        self.ui.statusbar.addPermanentWidget(self.ui.N_scan_steps_sb)
        self.ui.statusbar.addPermanentWidget(self.ui.indice_scan_sb)
        self.ui.statusbar.addPermanentWidget(self.ui.indice_average_sb)
        self.ui.indice_average_sb.setVisible(False)
        self.ui.statusbar.addPermanentWidget(self.ui.scan_done_LED)

        self.plot_colors = utils.plot_colors
        self.ui.splitter.setSizes([500, 1200])

        self.ui.scan_done_LED.set_as_false()
        self.ui.scan_done_LED.clickable = False

        # displaying the settings
        widget_settings = QtWidgets.QWidget()
        settings_layout = QtWidgets.QGridLayout()
        widget_settings.setLayout(settings_layout)
        self.ui.settings_layout.addWidget(widget_settings)

        self.settings_tree = ParameterTree()
        self.settings_tree.setMinimumWidth(300)

        settings_layout.addWidget(self.modules_manager.settings_tree, 0, 0, 1, 1)
        self.ui.toolbox = QtWidgets.QToolBox()
        settings_layout.addWidget(self.ui.toolbox, 0, 1, 1, 1)

        self.ui.toolbox.addItem(self.settings_tree, 'General Settings')
        self.ui.toolbox.addItem(self.h5saver.settings_tree, 'Save Settings')
        self.ui.toolbox.addItem(self.scanner.settings_tree, 'Scanner Settings')
        self.ui.toolbox.setCurrentIndex(2)

        self.h5saver.settings_tree.setMinimumWidth(300)
        self.settings = Parameter.create(name='Settings', type='group', children=self.params)

        self.settings_tree.setParameters(self.settings, showTop=False)
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

        # params about dataset attributes and scan attibutes
        date = QDateTime(QDate.currentDate(), QTime.currentTime())
        params_dataset = [{'title': 'Dataset information', 'name': 'dataset_info', 'type': 'group', 'children': [
            {'title': 'Author:', 'name': 'author', 'type': 'str', 'value': config['user']['name']},
            {'title': 'Date/time:', 'name': 'date_time', 'type': 'date_time', 'value': date},
            {'title': 'Sample:', 'name': 'sample', 'type': 'str', 'value': ''},
            {'title': 'Experiment type:', 'name': 'experiment_type', 'type': 'str', 'value': ''},
            {'title': 'Description:', 'name': 'description', 'type': 'text', 'value': ''}]}]

        params_scan = [{'title': 'Scan information', 'name': 'scan_info', 'type': 'group', 'children': [
            {'title': 'Author:', 'name': 'author', 'type': 'str', 'value': config['user']['name']},
            {'title': 'Date/time:', 'name': 'date_time', 'type': 'date_time', 'value': date},
            {'title': 'Scan type:', 'name': 'scan_type', 'type': 'list', 'value': 'Scan1D',
             'values': ['Scan1D', 'Scan2D']},
            {'title': 'Scan name:', 'name': 'scan_name', 'type': 'str', 'value': '', 'readonly': True},
            {'title': 'Description:', 'name': 'description', 'type': 'text', 'value': ''},
        ]}]

        self.dataset_attributes = Parameter.create(name='Attributes', type='group', children=params_dataset)
        self.scan_attributes = Parameter.create(name='Attributes', type='group', children=params_scan)

        # creating the Average dock plots
        self.create_average_dock()

        # creating the menubar
        self.create_menu()

        #        connecting
        self.ui.set_scan_pb.clicked.connect(self.set_scan)
        self.ui.quit_pb.clicked.connect(self.quit_fun)

        self.ui.start_scan_pb.clicked.connect(self.start_scan)
        self.ui.start_batch_pb.clicked.connect(self.start_scan_batch)
        self.ui.stop_scan_pb.clicked.connect(self.stop_scan)
        self.ui.set_ini_positions_pb.clicked.connect(self.set_ini_positions)

        self.ui.tabWidget.removeTab(2)

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

    def show_navigator(self):
        if self.navigator is None:
            # loading navigator

            widgnav = QtWidgets.QWidget()
            self.navigator = Navigator(widgnav)

            self.navigator.log_signal[str].connect(self.dashboard.add_status)
            self.navigator.settings.child('settings', 'Load h5').hide()
            self.navigator.loadaction.setVisible(False)

            self.ui.navigator_layout.addWidget(widgnav)
            self.navigator.sig_double_clicked.connect(self.move_at)

            self.scanner.scan_selector.remove_scan_selector()
            items = OrderedDict(Navigator=dict(viewers=[self.navigator.viewer], names=["Navigator"]))
            items.update(self.scanner.scan_selector.viewers_items)
            self.scanner.viewers_items = items

            self.ui.tabWidget.setCurrentIndex(self.ui.tabWidget.addTab(self.ui.tab_navigator, 'Navigator'))
            self.set_scan()  # to load current scans into the navigator

    def start_scan_batch(self):
        self.batch_started = True
        self.ind_batch = 0
        self.loop_scan_batch()

    def loop_scan_batch(self):
        if self.ind_batch >= len(self.batcher.scans_names):
            self.stop_scan()
            return
        self.scanner = self.batcher.scans[self.batcher.scans_names[self.ind_batch]]
        actuators, detectors = self.batcher.get_act_dets()
        self.set_scan_batch(actuators[self.batcher.scans_names[self.ind_batch]],
                            detectors[self.batcher.scans_names[self.ind_batch]])
        self.start_scan()

    def set_scan_batch(self, actuators, detectors):
        self.modules_manager.selected_detectors_name = detectors
        self.modules_manager.selected_actuators_name = actuators
        QtWidgets.QApplication.processEvents()


    def start_scan(self):
        """
            Start an acquisition calling the set_scan function.
            Emit the command_DAQ signal "start_acquisition".

            See Also
            --------
            set_scan
        """
        self.ui.status_message.setText('Starting acquisition')
        self.dashboard.overshoot = False
        self.plot_2D_ini = False
        self.plot_1D_ini = False
        self.bkg_container = None
        self.scan_positions = []
        self.curvilinear_values = []
        res = self.set_scan()
        if res:

            # deactivate module controls usiong remote_control
            if hasattr(self.dashboard, 'remote_manager'):
                remote_manager = getattr(self.dashboard, 'remote_manager')
                remote_manager.activate_all(False)

            # save settings from move modules
            move_modules_names = [mod.title for mod in self.modules_manager.actuators]
            for ind_move, move_name in enumerate(move_modules_names):
                move_group_name = 'Move{:03d}'.format(ind_move)
                if not self.h5saver.is_node_in_group(self.h5saver.current_scan_group, move_group_name):
                    self.h5saver.add_move_group(self.h5saver.current_scan_group, title='',
                                                settings_as_xml=pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(
                                                    self.modules_manager.actuators[ind_move].settings),
                                                metadata=dict(name=move_name))

            # save settings from detector modules
            detector_modules_names = [mod.title for mod in self.modules_manager.detectors]
            for ind_det, det_name in enumerate(detector_modules_names):
                det_group_name = 'Detector{:03d}'.format(ind_det)
                if not self.h5saver.is_node_in_group(self.h5saver.current_scan_group, det_group_name):
                    settings_str = pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(
                        self.modules_manager.detectors[ind_det].settings)
                    try:
                        if 'Data0D' not in [viewer.viewer_type for viewer in
                                            self.modules_manager.detectors[
                                                ind_det].ui.viewers]:  # no roi_settings in viewer0D
                            settings_str = b'<All_settings title="All Settings" type="group">' + settings_str
                            for ind_viewer, viewer in enumerate(self.modules_manager.detectors[ind_det].ui.viewers):
                                if hasattr(viewer, 'roi_manager'):
                                    settings_str += '<Viewer{:0d}_ROI_settings title="ROI Settings" type="group">'.format(
                                        ind_viewer).encode()
                                    settings_str += pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(
                                        viewer.roi_manager.settings) + '</Viewer{:0d}_ROI_settings>'.format(
                                        ind_viewer).encode()
                            settings_str += b'</All_settings>'
                    except Exception as e:
                        logger.exception(str(e))

                    self.h5saver.add_det_group(self.h5saver.current_scan_group,
                                               settings_as_xml=settings_str, metadata=dict(name=det_name))

            # mandatory to deal with multithreads
            if self.scan_thread is not None:
                self.command_DAQ_signal.disconnect()
                if self.scan_thread.isRunning():
                    self.scan_thread.terminate()
                    while not self.scan_thread.isFinished():
                        QThread.msleep(100)
                    self.scan_thread = None

            self.scan_thread = QThread()

            scan_acquisition = DAQ_Scan_Acquisition(self.settings, self.scanner.settings, self.h5saver.settings,
                                                    self.modules_manager, self.scanner.scan_parameters)
            if config['scan']['scan_in_thread']:
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
            self.ui.status_message.setText('Running acquisition')
            logger.info('Running acquisition')

    def stop_scan(self):
        """
            Emit the command_DAQ signal "stop_acquisiion".

            See Also
            --------
            set_ini_positions
        """
        self.ui.status_message.setText('Stoping acquisition')
        self.command_DAQ_signal.emit(["stop_acquisition"])

        if not self.dashboard.overshoot:
            self.set_ini_positions()  # do not set ini position again in case overshoot fired
            status = 'Data Acquisition has been stopped by user'
        else:
            status = 'Data Acquisition has been stopped due to overshoot'

        self.update_status(status, log_type='log')
        self.ui.status_message.setText('')

        self.ui.set_scan_pb.setEnabled(True)
        self.ui.set_ini_positions_pb.setEnabled(True)
        self.ui.start_scan_pb.setEnabled(True)

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

        elif status[0] == "Update_scan_index":
            # status[1] = [ind_scan,ind_average]
            self.ind_scan = status[1][0]
            self.ui.indice_scan_sb.setValue(status[1][0])
            self.ind_average = status[1][1]
            self.ui.indice_average_sb.setValue(status[1][1])

        elif status[0] == "Scan_done":
            self.ui.scan_done_LED.set_as_true()
            self.save_scan()
            if not self.batch_started:
                if not self.dashboard.overshoot:
                    self.set_ini_positions()
                self.ui.set_scan_pb.setEnabled(True)
                self.ui.set_ini_positions_pb.setEnabled(True)
                self.ui.start_scan_pb.setEnabled(True)

                # reactivate module controls usiong remote_control
                if hasattr(self.dashboard, 'remote_manager'):
                    remote_manager = getattr(self.dashboard, 'remote_manager')
                    remote_manager.activate_all(True)
            else:
                self.ind_batch += 1
                self.loop_scan_batch()

        elif status[0] == "Timeout":
            self.ui.status_message.setText('Timeout occurred')

    def update_1D_graph(self, datas, display_as_sequence=False, isadaptive=False, bkg=None):
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
            scan_type = self.scanner.scan_parameters.scan_type
            # self.scan_y_axis = np.array([])
            if not self.plot_1D_ini:  # init the datas
                self.plot_1D_ini = True
                self.ui.scan1D_subgraph.show(display_as_sequence)
                if isadaptive:
                    self.scan_data_1D = np.expand_dims(np.array([datas[key]['data'] for key in datas]), 0)
                else:
                    if not display_as_sequence:
                        if self.scanner.scan_parameters.scan_subtype == 'Linear back to start':
                            self.scan_x_axis = np.array(self.scanner.scan_parameters.positions[0::2, 0])
                        else:
                            self.scan_x_axis = np.array(self.scanner.scan_parameters.positions[:, 0])

                    else:
                        self.scan_x_axis = np.linspace(0, len(self.scanner.scan_parameters.positions) - 1,
                                                       len(self.scanner.scan_parameters.positions))
                        self.ui.scan1D_subgraph.show_data(
                            [positions for positions in self.scanner.scan_parameters.positions.T])
                        self.ui.scan1D_subgraph.update_labels(self.scanner.actuators)
                        self.ui.scan1D_subgraph.set_axis_label(axis_settings=dict(orientation='bottom',
                                                                                  label='Scan index', units=''))

                    self.scan_data_1D = np.zeros((self.scanner.scan_parameters.Nsteps, len(datas)))
                    if self.settings.child('scan_options', 'scan_average').value() > 1:
                        self.scan_data_1D_average = np.zeros((self.scanner.scan_parameters.Nsteps, len(datas)))

                self.ui.scan1D_graph.set_axis_label(axis_settings=dict(orientation='left',
                                                                       label=self.settings.child('scan_options',
                                                                                                 'plot_from').value(),
                                                                       units=''))

            if display_as_sequence:
                self.ui.scan1D_subgraph.show_data(
                    [positions for positions in np.array(self.scan_positions).T])
                self.ui.scan1D_subgraph.update_labels(self.scanner.actuators)
                self.ui.scan1D_subgraph.set_axis_label(axis_settings=dict(orientation='bottom',
                                                                          label='Scan index', units=''))

            # to test random mode:
            # self.scan_data_1D[self.ind_scan, :] =np.random.rand((1))* np.array([np.exp(-(self.scan_x_axis[self.ind_scan]-50)**2/20**2),np.exp(-(self.scan_x_axis[self.ind_scan]-50)**6/10**6)]) # np.array(list(datas.values()))
            # self.scan_data_1D[self.ind_scan, :] =  np.array(list(datas.values()))

            if isadaptive:
                if self.ind_scan != 0:

                    self.scan_data_1D = np.vstack((self.scan_data_1D, np.array([
                        self.get_data_live_bkg(datas, key, bkg) for key in datas])))

                if not display_as_sequence:
                    self.scan_x_axis = np.array(self.scan_positions)
                else:
                    if isadaptive:
                        self.scan_x_axis = np.array(self.curvilinear_values)
                    else:
                        self.scan_x_axis = np.linspace(0, len(self.scan_positions) - 1,
                                                       len(self.scan_positions))
            else:
                if self.scanner.scan_parameters.scan_subtype == 'Linear back to start':
                    if not utils.odd_even(self.ind_scan):

                        self.scan_data_1D[int(self.ind_scan / 2), :] = \
                            np.array([self.get_data_live_bkg(datas, key, bkg) for key in datas])

                        if self.settings.child('scan_options', 'scan_average').value() > 1:
                            self.scan_data_1D_average[self.ind_scan, :] = \
                                (self.ind_average * self.scan_data_1D_average[
                                    int(self.ind_scan / 2), :] + self.scan_data_1D[
                                    int(self.ind_scan / 2), :]) / (self.ind_average + 1)

                else:
                    self.scan_data_1D[self.ind_scan, :] = \
                        np.array([self.get_data_live_bkg(datas, key, bkg) for key in datas])

                    if self.settings.child('scan_options', 'scan_average').value() > 1:
                        self.scan_data_1D_average[self.ind_scan, :] = \
                            (self.ind_average * self.scan_data_1D_average[self.ind_scan, :] + self.scan_data_1D[
                                self.ind_scan, :]) / (self.ind_average + 1)

            x_axis_sorted, indices = np.unique(self.scan_x_axis, return_index=True)
            data_sorted = list(self.scan_data_1D.T)
            data_sorted = [data[indices] for data in data_sorted]

            if not display_as_sequence:
                x_axis = utils.Axis(data=x_axis_sorted,
                                    label=self.modules_manager.actuators[0].title,
                                    units=self.modules_manager.actuators[0].settings.child('move_settings',
                                                                                           'units').value())
            else:
                if isadaptive:
                    x_axis = utils.Axis(data=x_axis_sorted, label='Curvilinear value', units='')
                else:
                    x_axis = utils.Axis(data=x_axis_sorted, label='Scan index', units='')

            self.ui.scan1D_graph.x_axis = x_axis
            self.ui.scan1D_graph.show_data(data_sorted)

            if self.settings.child('scan_options', 'scan_average').value() > 1:
                data_averaged_sorted = list(self.scan_data_1D_average.T)
                data_averaged_sorted = [data[indices] for data in data_averaged_sorted]
                self.ui.average1D_graph.x_axis = x_axis_sorted
                self.ui.average1D_graph.show_data(data_averaged_sorted)

        except Exception as e:
            logger.exception(str(e))

    def get_data_live_bkg(self, datas, key, bkg):
        bkg_flag = False
        if bkg is not None:
            if key in bkg:
                bkg_flag = True
        if bkg_flag:
            data = datas[key]['data'] - bkg[key]['data']
        else:
            data = datas[key]['data']
        return data

    def update_2D_graph(self, datas, display_as_sequence=False, isadaptive=False, bkg=None):
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
            scan_type = self.scanner.scan_parameters.scan_type
            if scan_type == 'Scan2D' or \
                    (scan_type == 'Sequential' and self.scanner.scan_parameters.Naxes == 2) or \
                    (scan_type == 'Tabular' and self.scanner.scan_parameters.Naxes == 2):

                if not self.plot_2D_ini:  # init the data
                    # self.ui.scan1D_subgraph.show(False)
                    self.plot_2D_ini = True
                    if isadaptive:
                        self.scan_x_axis2D = np.array(self.scan_positions)[:, 0]
                        self.scan_y_axis = np.array(self.scan_positions)[:, 1]
                        key = list(datas.keys())[0]
                        if bkg is not None:
                            self.scan_data_2D = \
                                np.hstack((self.scan_positions[-1], datas[key]['data'] - bkg[key]['data']))
                        else:
                            self.scan_data_2D = \
                                np.hstack((self.scan_positions[-1], datas[key]['data']))
                    else:
                        self.scan_x_axis2D = self.scanner.scan_parameters.axes_unique[0]
                        self.scan_y_axis = self.scanner.scan_parameters.axes_unique[1]
                        self.scan_data_2D = [np.zeros((len(self.scan_y_axis),
                                                       len(self.scan_x_axis2D)))
                                             for ind in range(min((3, len(datas))))]
                    self.ui.scan2D_graph.x_axis = dict(data=self.scan_x_axis2D,
                                                       units=self.modules_manager.actuators[0].settings.child(
                                                           'move_settings', 'units').value(),
                                                       label=self.modules_manager.actuators[0].title)
                    self.ui.scan2D_graph.y_axis = dict(data=self.scan_y_axis,
                                                       units=self.modules_manager.actuators[1].settings.child(
                                                           'move_settings', 'units').value(),
                                                       label=self.modules_manager.actuators[1].title)

                    if self.settings.child('scan_options', 'scan_average').value() > 1:
                        self.ui.average2D_graph.x_axis = dict(data=self.scan_x_axis2D,
                                                              units=self.modules_manager.actuators[0].settings.child(
                                                                  'move_settings', 'units').value(),
                                                              label=self.modules_manager.actuators[0].title)
                        self.ui.average2D_graph.y_axis = dict(data=self.scan_y_axis,
                                                              units=self.modules_manager.actuators[1].settings.child(
                                                                  'move_settings', 'units').value(),
                                                              label=self.modules_manager.actuators[1].title)
                        self.scan_data_2D_average = [np.zeros((len(self.scanner.scan_parameters.axis_2D_2),
                                                               len(self.scanner.scan_parameters.axis_2D_1)))
                                                     for ind in range(min((3, len(datas))))]

                if not isadaptive:
                    ind_pos_axis_1 = self.scanner.scan_parameters.axes_indexes[self.ind_scan, 0]
                    ind_pos_axis_2 = self.scanner.scan_parameters.axes_indexes[self.ind_scan, 1]
                    for ind_plot in range(min((3, len(datas)))):
                        keys = list(datas.keys())

                        self.scan_data_2D[ind_plot][ind_pos_axis_2, ind_pos_axis_1] = \
                            self.get_data_live_bkg(datas, keys[ind_plot], bkg)

                        if self.settings.child('scan_options', 'scan_average').value() > 1:
                            self.scan_data_2D_average[ind_plot][ind_pos_axis_2, ind_pos_axis_1] = \
                                (self.ind_average * self.scan_data_2D_average[ind_plot][
                                    ind_pos_axis_2, ind_pos_axis_1] + datas[
                                    keys[ind_plot]]['data']) / (self.ind_average + 1)
                    self.ui.scan2D_graph.setImage(*self.scan_data_2D)

                    if self.settings.child('scan_options', 'scan_average').value() > 1:
                        self.ui.average2D_graph.setImage(*self.scan_data_2D_average)

                else:
                    if self.ind_scan != 0:
                        key = list(datas.keys())[0]

                        self.scan_data_2D = np.vstack((self.scan_data_2D,
                                                       np.hstack((self.scan_positions[-1],
                                                                  self.get_data_live_bkg(datas, key, bkg)))))

                    if len(self.scan_data_2D) > 3:  # at least 3 point to make a triangulation image
                        self.ui.scan2D_graph.setImage(data_spread=self.scan_data_2D)

            else:  # scan 1D with concatenation of vectors making a 2D image
                if not self.plot_2D_ini:  # init the data
                    self.plot_2D_ini = True
                    if display_as_sequence:
                        self.ui.scan2D_subgraph.show(True)
                        self.ui.scan2D_subgraph.show_data(
                            [positions for positions in self.scanner.scan_parameters.positions.T])
                        self.ui.scan2D_subgraph.update_labels(self.scanner.actuators)

                    data = datas[list(datas.keys())[0]]
                    Ny = len(data[list(data.keys())[0]])

                    self.scan_y_axis = np.array([])

                    Nx = len(self.scanner.scan_parameters.positions)
                    if not display_as_sequence:

                        if self.scanner.scan_parameters.scan_subtype == 'Linear back to start':
                            self.scan_x_axis2D = np.array(self.scanner.scan_parameters.positions[0::2, 0])
                        else:
                            self.scan_x_axis2D = np.array(self.scanner.scan_parameters.positions[:, 0])

                        x_axis = utils.Axis(data=self.scan_x_axis2D,
                                            label=self.modules_manager.actuators[0].title,
                                            units=self.modules_manager.actuators[0].settings.child('move_settings',
                                                                                                   'units').value())

                    else:
                        x_axis = utils.Axis(data=self.scan_x_axis2D,
                                            label='Scan index',
                                            units='')
                        self.scan_x_axis2D = np.linspace(0, Nx - 1, Nx)

                    self.ui.scan2D_graph.x_axis = x_axis
                    self.ui.scan2D_subgraph.x_axis = x_axis

                    det_names = [det.title for det in self.modules_manager.detectors_all]
                    ind_plot_det = det_names.index(self.settings.child('scan_options', 'plot_from').value())
                    if 'x_axis' in data.keys():
                        self.scan_y_axis = data['x_axis']['data']
                        label = data['x_axis']['label']
                        units = data['x_axis']['units']
                    else:
                        self.scan_y_axis = np.linspace(0, Ny - 1, Ny)
                        label = 'pixels'
                        units = 'index'

                    if self.modules_manager.detectors_all[ind_plot_det].ui.viewers[0].viewer_type == 'Data1D':
                        if label == '':
                            label = self.modules_manager.detectors_all[ind_plot_det].ui.viewers[0].axis_settings['label']
                        if units == '':
                            units = self.modules_manager.detectors_all[ind_plot_det].ui.viewers[0].axis_settings['units']

                    self.ui.scan2D_graph.y_axis = dict(data=self.scan_y_axis,
                                                       units=units,
                                                       label=f'{self.modules_manager.detectors_all[ind_plot_det].title} {label}')
                    self.scan_data_2D = []
                    self.scan_data_2D_average = []
                    for ind, key in enumerate(datas):
                        if ind >= 3:
                            break
                        self.scan_data_2D.append(np.zeros([datas[key]['data'].shape[0]] + [Nx]))
                        if self.settings.child('scan_options', 'scan_average').value() > 1:
                            self.scan_data_2D_average.append(np.zeros([datas[key]['data'].shape[0]] + [Nx]))

                if self.scanner.scan_parameters.scan_subtype == 'Linear back to start':
                    if not utils.odd_even(self.ind_scan):
                        for ind_plot, key in enumerate(datas.keys()):

                            self.scan_data_2D[ind_plot][:, int(self.ind_scan / 2)] = \
                                self.get_data_live_bkg(datas, key, bkg)

                            if self.settings.child('scan_options', 'scan_average').value() > 1:
                                self.scan_data_2D_average[ind_plot][:, int(self.ind_scan / 2)] = \
                                    (self.ind_average * self.scan_data_2D_average[ind_plot][
                                        :, int(self.ind_scan / 2)] + datas[key]['data']) / (self.ind_average + 1)

                else:
                    if not display_as_sequence:
                        ind_pos_axis = self.scanner.scan_parameters.axes_indexes[self.ind_scan, 0]
                    else:
                        ind_pos_axis = self.ind_scan

                    for ind_plot, key in enumerate(datas.keys()):
                        if ind_plot >= 3:
                            break
                        self.scan_data_2D[ind_plot][:, ind_pos_axis] = self.get_data_live_bkg(datas, key, bkg)

                        if self.settings.child('scan_options', 'scan_average').value() > 1:
                            self.scan_data_2D_average[ind_plot][:, self.ind_scan] = \
                                (self.ind_average * self.scan_data_2D_average[ind_plot][:, ind_pos_axis] + datas[key][
                                    'data']) \
                                / (self.ind_average + 1)

                self.ui.scan2D_graph.setImage(*self.scan_data_2D)
                if self.settings.child('scan_options', 'scan_average').value() > 1:
                    self.ui.average2D_graph.setImage(*self.scan_data_2D_average)

        except Exception as e:
            logger.exception(str(e))

    def update_file_settings(self, new_file=False):
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

            # set attributes to the current group, such as scan_type....
            self.scan_attributes.child('scan_info', 'scan_type').setValue(
                self.scanner.settings.child('scan_type').value())
            self.scan_attributes.child('scan_info', 'scan_name').setValue(self.h5saver.current_scan_group.name)
            self.scan_attributes.child('scan_info', 'description').setValue(
                self.h5saver.current_scan_group.attrs['description'])
            res = self.set_metadata_about_current_scan()
            self.save_metadata(self.h5saver.current_scan_group, 'scan_info')
            return res

        except Exception as e:
            logger.exception(str(e))

    def update_plot_det_items(self, dets):
        """
        """
        self.settings.child('scan_options', 'plot_from').setOpts(limits=dets)

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

        self.scan_positions.append(self.modules_manager.order_positions(datas['positions']))
        scan_type = utils.capitalize(self.scanner.scan_parameters.scan_type)

        display_as_sequence = (scan_type == 'Sequential' and self.scanner.scan_parameters.Naxes > 2) or \
                              (scan_type == 'Tabular' and not self.scanner.scan_parameters.Naxes == 1)

        tabular2D = scan_type == 'Tabular' and self.scanner.scan_parameters.Naxes == 2
        isadaptive = self.scanner.scan_parameters.scan_subtype == 'Adaptive'
        if 'curvilinear' in datas:
            self.curvilinear_values.append(datas['curvilinear'])

        if self.bkg_container is None:
            det_name = self.settings.child('scan_options', 'plot_from').value()
            det_mod = self.modules_manager.get_mod_from_name(det_name)
            if det_mod.bkg is not None and det_mod.is_bkg:
                self.bkg_container = OrderedDict([])
                det_mod.process_data(det_mod.bkg, self.bkg_container)

        try:
            if scan_type == 'Scan1D' or \
                    (scan_type == 'Sequential' and self.scanner.scan_parameters.Naxes == 1) or \
                    (scan_type == 'Sequential' and self.scanner.scan_parameters.Naxes > 2) or \
                    (scan_type == 'Tabular' and self.scanner.scan_parameters.Naxes == 1) or \
                    (scan_type == 'Tabular' and self.scanner.scan_parameters.Naxes > 2):

                if 'data0D' in datas['datas'].keys():
                    if not (datas['datas']['data0D'] is None or datas['datas']['data0D'] == OrderedDict()):
                        if self.bkg_container is None:
                            bkg = None
                        else:
                            bkg = self.bkg_container['data0D']
                        self.update_1D_graph(datas['datas']['data0D'], display_as_sequence=display_as_sequence,
                                             isadaptive=isadaptive, bkg=bkg)
                    else:
                        self.scan_data_1D = []
                if 'data1D' in datas['datas'].keys():
                    if not (datas['datas']['data1D'] is None or datas['datas']['data1D'] == OrderedDict()):
                        if self.bkg_container is None:
                            bkg = None
                        else:
                            bkg = self.bkg_container['data1D']
                        self.update_2D_graph(datas['datas']['data1D'], display_as_sequence=display_as_sequence,
                                             isadaptive=isadaptive, bkg=bkg)
                    # else:
                    #     self.scan_data_2D = []

            if scan_type == 'Scan2D' or \
                    (scan_type == 'Sequential' and self.scanner.scan_parameters.Naxes == 2) or \
                    tabular2D:
                # means 2D cartography type scan

                if 'data0D' in datas['datas'].keys():
                    if not (datas['datas']['data0D'] is None or datas['datas']['data0D'] == OrderedDict()):
                        if self.bkg_container is None:
                            bkg = None
                        else:
                            bkg = self.bkg_container['data0D']
                        self.update_2D_graph(datas['datas']['data0D'], display_as_sequence=display_as_sequence,
                                             isadaptive=isadaptive or tabular2D, bkg=bkg)
                    else:
                        self.scan_data_2D = []

        except Exception as e:
            logger.exception(str(e))

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
        self.ui.statusbar.showMessage(txt, wait_time)
        self.status_signal.emit(txt)
        logger.info(txt)


class DAQ_Scan_Acquisition(QObject):
    """
        =========================== ========================================

        =========================== ========================================

    """
    scan_data_tmp = pyqtSignal(OrderedDict)
    status_sig = pyqtSignal(list)

    def __init__(self, settings=None, scan_settings=None, h5saver=None, modules_manager=None, scan_parameters=None):

        """
            DAQ_Scan_Acquisition deal with the acquisition part of daq_scan, that is transferring commands to modules,
            getting back data, saviong and letting know th UI about the scan status

        """
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(QObject, self).__init__()

        self.stop_scan_flag = False
        self.settings = settings
        self.scan_settings = scan_settings
        self.Naverage = self.settings.child('scan_options', 'scan_average').value()
        self.ind_average = 0
        self.ind_scan = 0
        self.scan_parameters = scan_parameters
        self.isadaptive = self.scan_parameters.scan_subtype == 'Adaptive'
        self.curvilinear_array = None
        self.modules_manager = modules_manager
        self.modules_manager.timeout_signal.connect(self.timeout)
        self.timeout_scan_flag = False

        self.curvilinear = None  # used for adaptive/Tabular scan mode

        self.scan_x_axis = None
        self.scan_x_axis2D = None
        self.scan_y_axis = None
        self.scan_z_axis = None
        self.scan_x_axis_unique = None
        self.scan_y_axis_unique = None
        self.scan_z_axis_unique = None
        self.scan_shape = None

        self.scan_read_positions = []
        self.scan_read_datas = []
        self.move_done_flag = False
        self.det_done_flag = False

        self.det_done_datas = OrderedDict()

        self.h5saver = H5Saver()
        self.h5saver.settings.restoreState(h5saver.saveState())
        self.h5saver.init_file(addhoc_file_path=self.h5saver.settings.child(('current_h5_file')).value())

        self.h5_det_groups = []
        self.h5_move_groups = []
        self.channel_arrays = OrderedDict([])

        # save settings from move modules
        for ind_move in range(self.modules_manager.Nactuators):
            move_group_name = 'Move{:03d}'.format(ind_move)
            self.h5_move_groups.append(self.h5saver.get_node(self.h5saver.current_scan_group, move_group_name))

        # save settings from detector modules
        for ind_det in range(self.modules_manager.Ndetectors):
            det_group_name = 'Detector{:03d}'.format(ind_det)
            self.h5_det_groups.append(self.h5saver.get_node(self.h5saver.current_scan_group, det_group_name))

    @pyqtSlot(list)
    def queue_command(self, command):
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
        if command[0] == "start_acquisition":
            self.start_acquisition()

        elif command[0] == "stop_acquisition":
            self.stop_scan_flag = True

        elif command[0] == "set_ini_positions":
            self.set_ini_positions()

        elif command[0] == "move_stages":
            self.modules_manager.move_actuators(command[1])

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
            if self.scan_parameters.scan_subtype != 'Adaptive':
                self.modules_manager.move_actuators(list(self.scan_parameters.positions[0]))

        except Exception as e:
            logger.exception(str(e))

    def init_data(self):
        self.channel_arrays = OrderedDict([])
        for ind_det, det_name in enumerate(self.modules_manager.get_names(self.modules_manager.detectors)):
            datas = self.modules_manager.det_done_datas[det_name]
            det_group = self.h5_det_groups[ind_det]
            self.channel_arrays[det_name] = OrderedDict([])
            data_types = ['data0D', 'data1D']
            if self.h5saver.settings.child(('save_2D')).value():
                data_types.extend(['data2D', 'dataND'])

            det_mod = self.modules_manager.get_mod_from_name(det_name)
            if det_mod.bkg is not None and det_mod.is_bkg:
                bkg_container = OrderedDict([])
                det_mod.process_data(det_mod.bkg, bkg_container)

            for data_type in data_types:
                if data_type in datas.keys():
                    if datas[data_type] is not None:
                        if len(datas[data_type]) != 0:
                            data_raw_roi = [datas[data_type][key]['source'] for key in datas[data_type]]
                            if not (self.h5saver.settings.child(
                                    ('save_raw_only')).value() and 'raw' not in data_raw_roi):
                                if not self.h5saver.is_node_in_group(det_group, data_type):
                                    self.channel_arrays[det_name][data_type] = OrderedDict([])
                                    data_group = self.h5saver.add_data_group(det_group, data_type)
                                    for ind_channel, channel in enumerate(datas[data_type]):  # list of OrderedDict
                                        if not (
                                            self.h5saver.settings.child(
                                                'save_raw_only').value() and datas[
                                                data_type][channel]['source'] != 'raw'):
                                            channel_group = self.h5saver.add_CH_group(data_group, title=channel)
                                            self.channel_arrays[det_name][data_type]['parent'] = channel_group
                                            data_tmp = datas[data_type][channel]

                                            if det_mod.bkg is not None and det_mod.is_bkg:
                                                if channel in bkg_container[data_type]:
                                                    data_tmp['bkg'] = bkg_container[data_type][channel]['data']
                                                    if data_tmp['bkg'].shape == ():  # in case one get a numpy.float64 object
                                                        data_tmp['bkg'] = np.array([data_tmp['bkg']])

                                            self.channel_arrays[det_name][data_type][channel] = \
                                                self.h5saver.add_data(channel_group,
                                                                      data_tmp,
                                                                      scan_type=self.scan_parameters.scan_type,
                                                                      scan_subtype=self.scan_parameters.scan_subtype,
                                                                      scan_shape=self.scan_shape, init=True,
                                                                      add_scan_dim=True,
                                                                      enlargeable=self.isadaptive)
            pass

    def det_done(self, det_done_datas, positions=[]):
        """
            | Initialize 0D/1D/2D datas from given data parameter.
            | Update h5_file group and array.
            | Save 0D/1D/2D... datas.
        Parameters
        ----------
        det_done_datas: (OrderedDict) on the form OrderedDict
                    (det0=OrderedDict(data0D=None, data1D=None, data2D=None, dataND=None),
                     det1=OrderedDict(data0D=None, data1D=None, data2D=None, dataND=None),...)
        """
        try:
            self.scan_read_datas = det_done_datas[
                self.settings.child('scan_options', 'plot_from').value()].copy()

            if self.ind_scan == 0 and self.ind_average == 0:  # first occurence=> initialize the channels
                self.init_data()

            if not self.isadaptive:
                if self.scan_parameters.scan_type == 'Tabular':
                    indexes = np.array([self.ind_scan])
                else:
                    indexes = self.scan_parameters.axes_indexes[self.ind_scan]

                if self.Naverage > 1:
                    indexes = list(indexes)
                    indexes.append(self.ind_average)

                indexes = tuple(indexes)

            if self.isadaptive:
                for ind_ax, nav_axis in enumerate(self.navigation_axes):
                    nav_axis.append(np.array(positions[ind_ax]))

            for ind_det, det_name in enumerate(self.modules_manager.get_names(self.modules_manager.detectors)):
                datas = det_done_datas[det_name]

                data_types = ['data0D', 'data1D']
                if self.h5saver.settings.child(('save_2D')).value():
                    data_types.extend(['data2D', 'dataND'])

                for data_type in data_types:
                    if data_type in datas.keys():
                        if datas[data_type] is not None:
                            if len(datas[data_type]) != 0:
                                for ind_channel, channel in enumerate(datas[data_type]):
                                    if not (self.h5saver.settings.child(
                                            'save_raw_only').value() and datas[data_type][channel]['source'] != 'raw'):
                                        if not self.isadaptive:
                                            self.channel_arrays[
                                                det_name][data_type][channel].__setitem__(
                                                indexes, value=det_done_datas[det_name][data_type][channel]['data'])
                                        else:
                                            data = det_done_datas[det_name][data_type][channel]['data']
                                            if isinstance(data, float) or isinstance(data, int):
                                                data = np.array([data])
                                            self.channel_arrays[det_name][data_type][channel].append(data)

            self.det_done_flag = True

            self.scan_data_tmp.emit(OrderedDict(positions=self.modules_manager.move_done_positions,
                                                datas=self.scan_read_datas,
                                                curvilinear=self.curvilinear))
        except Exception as e:
            logger.exception(str(e))
            # self.status_sig.emit(["Update_Status", getLineInfo() + str(e), 'log'])

    def timeout(self):
        """
            Send the status signal *'Time out during acquisition'*.
        """
        self.timeout_scan_flag = True
        self.status_sig.emit(["Update_Status", "Timeout during acquisition", 'log'])
        self.status_sig.emit(["Timeout"])

    def start_acquisition(self):
        try:

            self.modules_manager.connect_actuators()
            self.modules_manager.connect_detectors()

            self.scan_read_positions = []
            self.scan_read_datas = []
            self.stop_scan_flag = False
            Naxes = self.scan_parameters.Naxes
            scan_type = self.scan_parameters.scan_type
            self.navigation_axes = []

            if scan_type == 'Scan1D' or scan_type == 'Scan2D':
                """creates the X_axis and Y_axis valid only for 1D or 2D scans """
                if self.isadaptive:
                    self.scan_x_axis = np.array([0.0, ])
                    self.scan_x_axis_unique = np.array([0.0, ])
                else:
                    self.scan_x_axis = self.scan_parameters.positions[:, 0]
                    self.scan_x_axis_unique = self.scan_parameters.axes_unique[0]

                if not self.h5saver.is_node_in_group(self.h5saver.current_scan_group, 'scan_x_axis'):
                    x_axis_meta = dict(
                        units=self.modules_manager.actuators[0].settings.child('move_settings', 'units').value(),
                        label=self.modules_manager.get_names(self.modules_manager.actuators)[0],
                        nav_index=0)

                    self.navigation_axes.append(self.h5saver.add_navigation_axis(self.scan_x_axis,
                                                                                 self.h5saver.current_scan_group,
                                                                                 axis='x_axis',
                                                                                 metadata=x_axis_meta,
                                                                                 enlargeable=self.isadaptive))

                if not self.isadaptive:
                    if self.scan_parameters.scan_subtype == 'Linear back to start':
                        self.scan_shape = [len(self.scan_x_axis)]
                    else:
                        self.scan_shape = [len(self.scan_x_axis_unique)]
                else:
                    self.scan_shape = [0]

                if scan_type == 'Scan2D':  # "means scan 2D"
                    if self.isadaptive:
                        self.scan_y_axis = np.array([0.0, ])
                        self.scan_y_axis_unique = np.array([0.0, ])
                    else:
                        self.scan_y_axis = self.scan_parameters.positions[:, 1]
                        self.scan_y_axis_unique = self.scan_parameters.axes_unique[1]

                    if not self.h5saver.is_node_in_group(self.h5saver.current_scan_group, 'scan_y_axis'):
                        y_axis_meta = dict(
                            units=self.modules_manager.actuators[1].settings.child('move_settings', 'units').value(),
                            label=self.modules_manager.get_names(self.modules_manager.actuators)[1],
                            nav_index=1)
                        self.navigation_axes.append(self.h5saver.add_navigation_axis(self.scan_y_axis,
                                                                                     self.h5saver.current_scan_group,
                                                                                     axis='y_axis',
                                                                                     metadata=y_axis_meta,
                                                                                     enlargeable=self.isadaptive))
                    if not self.isadaptive:
                        self.scan_shape.append(len(self.scan_y_axis_unique))
                    else:
                        self.scan_shape.append(0)

            elif scan_type == 'Sequential':
                """Creates axes labelled by the index within the sequence"""
                self.scan_shape = [len(ax) for ax in self.scan_parameters.axes_unique]
                for ind in range(Naxes):
                    if not self.h5saver.is_node_in_group(self.h5saver.current_scan_group,
                                                         'scan_{:02d}_axis'.format(ind)):
                        axis_meta = dict(
                            units=self.modules_manager.actuators[ind].settings.child('move_settings', 'units').value(),
                            label=self.modules_manager.get_names(self.modules_manager.actuators)[ind],
                            nav_index=ind)
                        self.navigation_axes.append(
                            self.h5saver.add_navigation_axis(self.scan_parameters.axes_unique[ind],
                                                             self.h5saver.current_scan_group,
                                                             axis=f'{ind:02d}_axis', metadata=axis_meta))

            elif scan_type == 'Tabular':
                """Creates axes labelled by the index within the sequence"""
                if not self.isadaptive:
                    self.scan_shape = [self.scan_parameters.Nsteps, ]
                    nav_axes = [self.scan_parameters.positions[:, ind] for ind in range(Naxes)]
                else:
                    self.scan_shape = [0, Naxes]
                    nav_axes = [np.array([0.0, ]) for ind in range(Naxes)]

                for ind in range(Naxes):
                    if not self.h5saver.is_node_in_group(self.h5saver.current_scan_group,
                                                         'scan_{:02d}_axis'.format(ind)):
                        axis_meta = dict(
                            units=self.modules_manager.actuators[ind].settings.child('move_settings', 'units').value(),
                            label=self.modules_manager.get_names(self.modules_manager.actuators)[ind],
                            nav_index=ind)
                        self.navigation_axes.append(self.h5saver.add_navigation_axis(nav_axes[ind],
                                                                                     self.h5saver.current_scan_group,
                                                                                     axis=f'{ind:02d}_axis',
                                                                                     metadata=axis_meta,
                                                                                     enlargeable=self.isadaptive))

                if self.isadaptive:
                    if not self.h5saver.is_node_in_group(self.h5saver.current_scan_group, 'Curvilinear_axis'):
                        axis_meta = dict(units='',
                                         label='Curvilinear coordinate',
                                         nav_index=-1)
                        self.curvilinear_array = self.h5saver.add_navigation_axis(np.array([0.0, ]),
                                                                                  self.h5saver.current_scan_group,
                                                                                  axis='curvilinear_axis',
                                                                                  metadata=axis_meta,
                                                                                  enlargeable=self.isadaptive)

            if self.Naverage > 1:
                self.scan_shape.append(self.Naverage)

            if self.isadaptive:
                """
                adaptive_losses = dict(
                loss1D=['default', 'curvature', 'uniform'],
                loss2D=['default', 'resolution', 'uniform', 'triangle'])
                """
                if self.scan_parameters.scan_type == 'Scan1D' or self.scan_parameters.scan_type == 'Tabular':
                    if self.scan_parameters.adaptive_loss == 'curvature':
                        loss = adaptive.learner.learner1D.curvature_loss_function()
                    elif self.scan_parameters.adaptive_loss == 'uniform':
                        loss = adaptive.learner.learner1D.uniform_loss
                    else:
                        loss = adaptive.learner.learner1D.default_loss
                    if self.scan_parameters.scan_type == 'Scan1D':
                        bounds = [self.scan_parameters.starts[0], self.scan_parameters.stops[0]]
                    else:
                        length = 0.
                        for vec in self.scan_parameters.vectors:
                            length += vec.norm()
                        bounds = [0., length]

                    learner = adaptive.learner.learner1D.Learner1D(None, bounds=bounds,
                                                                   loss_per_interval=loss)

                elif self.scan_parameters.scan_type == 'Scan2D':
                    if self.scan_parameters.adaptive_loss == 'resolution':
                        loss = adaptive.learner.learner2D.resolution_loss_function(
                            min_distance=self.scan_parameters.steps[0] / 100,
                            max_distance=self.scan_parameters.steps[1] / 100)
                    elif self.scan_parameters.adaptive_loss == 'uniform':
                        loss = adaptive.learner.learner2D.uniform_loss
                    elif self.scan_parameters.adaptive_loss == 'triangle':
                        loss = adaptive.learner.learner2D.triangle_loss
                    else:
                        loss = adaptive.learner.learner2D.default_loss

                    learner = adaptive.learner.learner2D.Learner2D(None,
                                                                   bounds=[b for b in zip(self.scan_parameters.starts,
                                                                                          self.scan_parameters.stops)],
                                                                   loss_per_triangle=loss)

                else:
                    logger.warning('Adaptive for more than 2 axis is not currently done (sequential adaptive)')
                    return

            self.status_sig.emit(["Update_Status", "Acquisition has started", 'log'])

            self.timeout_scan_flag = False
            for ind_average in range(self.Naverage):
                self.ind_average = ind_average
                self.ind_scan = -1
                while True:
                    self.ind_scan += 1
                    if not self.isadaptive:
                        if self.ind_scan >= len(self.scan_parameters.positions):
                            break
                        positions = self.scan_parameters.positions[self.ind_scan]  # get positions
                    else:
                        positions = learner.ask(1)[0][-1]  # next point to probe
                        if self.scan_parameters.scan_type == 'Tabular':  # translate normalized curvilinear position to real coordinates
                            self.curvilinear = positions
                            length = 0.
                            for v in self.scan_parameters.vectors:
                                length += v.norm()
                                if length >= self.curvilinear:
                                    vec = v
                                    frac_curvilinear = (self.curvilinear - (length - v.norm())) / v.norm()
                                    break

                            position = (vec.vectorize() * frac_curvilinear).translate_to(vec.p1()).p2()
                            positions = [position.x(), position.y()]

                    self.status_sig.emit(["Update_scan_index", [self.ind_scan, ind_average]])

                    if self.stop_scan_flag or self.timeout_scan_flag:
                        break

                    #move motors of modules and wait for move completion
                    positions = self.modules_manager.order_positions(self.modules_manager.move_actuators(positions))

                    QThread.msleep(self.settings.child('time_flow', 'wait_time_between').value())

                    #grab datas and wait for grab completion
                    self.det_done(self.modules_manager.grab_datas(positions=positions), positions)

                    if self.isadaptive:
                        det_channel = self.modules_manager.get_selected_probed_data()
                        det, channel = det_channel[0].split('/')
                        if self.scan_parameters.scan_type == 'Tabular':
                            self.curvilinear_array.append(np.array([self.curvilinear]))
                            new_positions = self.curvilinear
                        elif self.scan_parameters.scan_type == 'Scan1D':
                            new_positions = positions[0]
                        else:
                            new_positions = positions[:]

                        learner.tell(new_positions, self.modules_manager.det_done_datas[det]['data0D'][channel]['data'])

                    # daq_scan wait time
                    QThread.msleep(self.settings.child('time_flow', 'wait_time').value())

            self.h5saver.h5_file.flush()
            self.modules_manager.connect_actuators(False)
            self.modules_manager.connect_detectors(False)

            self.status_sig.emit(["Update_Status", "Acquisition has finished", 'log'])
            self.status_sig.emit(["Scan_done"])

        except Exception as e:
            logger.exception(str(e))
            # self.status_sig.emit(["Update_Status", getLineInfo() + str(e), 'log'])

    def wait_for_det_done(self):
        self.timeout_scan_flag = False
        self.timer.start(self.settings.child('time_flow', 'timeout').value())
        while not (self.det_done_flag or self.timeout_scan_flag):
            # wait for grab done signals to end
            QtWidgets.QApplication.processEvents()


def main():
    from pymodaq.dashboard import DashBoard
    from pymodaq.daq_utils.daq_utils import get_set_preset_path
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = gutils.DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    prog = DashBoard(area)
    file = Path(get_set_preset_path()).joinpath(f"{config['presets']['default_preset_for_scan']}.xml")
    if file.exists():
        prog.set_preset_mode(file)
        prog.load_scan_module()
    else:
        msgBox = QtWidgets.QMessageBox()
        msgBox.setText(f"The default file specified in the configuration file does not exists!\n"
                       f"{file}\n"
                       f"Impossible to load the DAQ_Scan Module")
        msgBox.setStandardButtons(msgBox.Ok)
        ret = msgBox.exec()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

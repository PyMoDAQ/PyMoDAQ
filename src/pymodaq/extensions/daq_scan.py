#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Automated scanning module functionalities for PyMoDAQ

Contains all objects related to the DAQScan module, to do automated scans, saving data...
"""
from __future__ import annotations
from collections import OrderedDict
import logging
import os
from pathlib import Path
import sys
import tempfile
from typing import List, Tuple, TYPE_CHECKING

import numpy as np
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import QObject, Slot, QThread, Signal, QDateTime, QDate, QTime

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import Config
from pymodaq_utils import utils

from pymodaq_data import data as data_mod
from pymodaq_data.h5modules import data_saving

from pymodaq_gui.parameter import ioxml
from pymodaq_gui.plotting.data_viewers import ViewersEnum
from pymodaq_gui.managers.parameter_manager import ParameterManager, Parameter, ParameterTree
from pymodaq_gui.plotting.navigator import Navigator
from pymodaq_gui.messenger import messagebox
from pymodaq_gui import utils as gutils
from pymodaq_gui.h5modules.saving import H5Saver

from pymodaq.utils.scanner.scanner import Scanner
from pymodaq.utils.managers.batchscan_manager import BatchScanner
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq.post_treatment.load_and_plot import LoaderPlotter
from pymodaq.extensions.daq_scan_ui import DAQScanUI
from pymodaq.utils.h5modules import module_saving
from pymodaq.utils.scanner.scan_selector import ScanSelector, SelectorItem
from pymodaq.utils.data import DataActuator


if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard

config = Config()

logger = set_logger(get_module_name(__file__))

SHOW_POPUPS = config('scan', 'show_popups')


class DAQ_ScanException(Exception):
    """Raised when an error occur within the DAQScan"""
    pass


class ScanDataTemp:
    """Convenience class to hold temporary data to be plotted in the live plots"""
    def __init__(self, scan_index: int, indexes: Tuple[int], data: data_mod.DataToExport):
        self.scan_index = scan_index
        self.indexes = indexes
        self.data = data


class DAQScan(QObject, ParameterManager):
    """
    Main class initializing a DAQScan module with its dashboard and scanning control panel
    """
    settings_name = 'daq_scan_settings'
    command_daq_signal = Signal(utils.ThreadCommand)
    status_signal = Signal(str)
    live_data_1D_signal = Signal(list)

    params = [
        {'title': 'Time Flow:', 'name': 'time_flow', 'type': 'group', 'expanded': False,
         'children': [
            {'title': 'Wait time step (ms)', 'name': 'wait_time', 'type': 'int', 'value': 0,
             'tip': 'Wait time in ms after each step of acquisition (move and grab)'},
            {'title': 'Wait time between (ms)', 'name': 'wait_time_between', 'type': 'int',
             'value': 0,
             'tip': 'Wait time in ms between move and grab processes'},
            {'title': 'Timeout (ms)', 'name': 'timeout', 'type': 'int', 'value': 10000},
        ]},
        {'title': 'Scan options', 'name': 'scan_options', 'type': 'group', 'children': [
            {'title': 'Naverage:', 'name': 'scan_average', 'type': 'int',
             'value': config('scan', 'Naverage'), 'min': 1},
            {'title': 'Plot on top:', 'name': 'average_on_top', 'type': 'bool',
             'value': config('scan', 'average_on_top'),
             'tip': 'At the second iteration will plot the averaged scan on top (True) of the current one'
                    'or in a second panel (False)'},
        ]},

        {'title': 'Plotting options', 'name': 'plot_options', 'type': 'group', 'children': [
            {'title': 'Get data', 'name': 'plot_probe', 'type': 'bool_push'},
            {'title': 'Group 0D data:', 'name': 'group0D', 'type': 'bool', 'value': True},
            {'title': 'Plot 0Ds:', 'name': 'plot_0d', 'type': 'itemselect', 'checkbox': True},
            {'title': 'Plot 1Ds:', 'name': 'plot_1d', 'type': 'itemselect', 'checkbox': True},
            {'title': 'Prepare Viewers', 'name': 'prepare_viewers', 'type': 'bool_push'},
            {'title': 'Plot at each step?', 'name': 'plot_at_each_step', 'type': 'bool',
             'value': True},
            {'title': 'Refresh Plots (ms)', 'name': 'refresh_live', 'type': 'int',
             'value': 1000, 'visible': False},
            ]},
    ]

    def __init__(self, dockarea: gutils.DockArea = None, dashboard: DashBoard = None):
        """

        Parameters
        ----------
        dockarea: DockArea
            instance of the modified pyqtgraph Dockarea
        dashboard: DashBoard
            instance of the pymodaq dashboard

        """
        
        logger.info('Initializing DAQScan')
        QObject.__init__(self)
        ParameterManager.__init__(self)

        self.title = __class__.__name__

        self.dockarea: gutils.DockArea = dockarea
        self.dashboard: DashBoard = dashboard
        if dashboard is None:
            raise Exception('No valid dashboard initialized')

        self.mainwindow = self.dockarea.parent()
        self.ui: DAQScanUI = DAQScanUI(self.dockarea)

        self.wait_time = 1000

        self.navigator: Navigator = None
        self.scan_selector: ScanSelector = None

        self.ind_scan = 0
        self.ind_average = 0

        self._metada_dataset_set = False

        self.curvilinear_values = []
        self.plot_colors = utils.plot_colors

        self.scan_thread: QThread = None
        self._h5saver: H5Saver = None
        self._module_and_data_saver: module_saving.ScanSaver = None

        self.modules_manager = ModulesManager(self.dashboard.detector_modules, self.dashboard.actuators_modules)
        self.modules_manager.settings.child('data_dimensions').setOpts(expanded=False)
        self.modules_manager.settings.child('actuators_positions').setOpts(expanded=False)
        self.modules_manager.detectors_changed.connect(self.clear_plot_from)

        self.module_and_data_saver = module_saving.ScanSaver(self)

        self.extended_saver: data_saving.DataToExportExtendedSaver = None
        self.h5temp: H5Saver = None
        self.temp_path: tempfile.TemporaryDirectory = None

        self.h5saver.settings.child('do_save').hide()
        self.h5saver.settings.child('custom_name').hide()
        self.h5saver.new_file_sig.connect(self.create_new_file)

        self.scanner = Scanner(actuators=self.modules_manager.actuators)  # , adaptive_losses=adaptive_losses)
        self.scan_parameters = None

        self.batcher: BatchScanner = None
        self.batch_started = False
        self.ind_batch = 0

        self.modules_manager.actuators_changed[list].connect(self.update_actuators)

        self.setup_ui()
        self.ui.command_sig.connect(self.process_ui_cmds)

        self.create_dataset_settings()

        self.set_config()

        self.live_plotter = LoaderPlotter(self.dockarea)
        self.live_timer = QtCore.QTimer()
        self.live_timer.timeout.connect(self.update_live_plots)

        self.ui.enable_start_stop(True)
        logger.info('DAQScan Initialized')

    def plot_from(self):
        self.modules_manager.get_det_data_list()
        data0D = self.modules_manager.settings['data_dimensions', 'det_data_list0D']
        data1D = self.modules_manager.settings['data_dimensions', 'det_data_list1D']
        data0D['selected'] = data0D['all_items']
        data1D['selected'] = data1D['all_items']
        self.settings.child('plot_options', 'plot_0d').setValue(data0D)
        self.settings.child('plot_options', 'plot_1d').setValue(data1D)

    def setup_ui(self):
        self.ui.populate_toolbox_widget([self.settings_tree, self.h5saver.settings_tree],
                                        ['General Settings', 'Save Settings'])

        self.ui.set_scanner_settings(self.scanner.parent_widget)
        self.ui.set_modules_settings(self.modules_manager.settings_tree)

        self.plotting_settings_tree = ParameterTree()
        self.plotting_settings_tree.setParameters(self.settings.child('plot_options'))
        self.ui.set_plotting_settings(self.plotting_settings_tree)

    ################
    #  CONFIG/SETUP UI / EXIT

    def set_config(self):
        self.settings.child('time_flow', 'wait_time').setValue(config['scan']['timeflow']['wait_time'])
        self.settings.child('time_flow', 'wait_time_between').setValue(config['scan']['timeflow']['wait_time'])
        self.settings.child('time_flow', 'timeout').setValue(config['scan']['timeflow']['timeout'])

        self.settings.child('scan_options',  'scan_average').setValue(config['scan']['Naverage'])

    def process_ui_cmds(self, cmd: utils.ThreadCommand):
        """Process commands sent by actions done in the ui

        Parameters
        ----------
        cmd: ThreadCommand
            Possible values are:
                * quit
                * ini_positions
                * start
                * start_batch
                * stop
                * move_at
                * show_log
                * load
                * save
                * show_file
                * navigator
                * batch
                * viewers_changed
        """
        if cmd.command == 'quit':
            self.quit_fun()
        elif cmd.command == 'ini_positions':
            self.set_ini_positions()
        elif cmd.command == 'start':
            self.start_scan()
        elif cmd.command == 'start_batch':
            self.start_scan_batch()
        elif cmd.command == 'stop':
            self.stop_scan()
        elif cmd.command == 'move_at':
            self.move_to_crosshair()
        elif cmd.command == 'show_log':
            self.show_log()
        elif cmd.command == 'load':
            self.load_file()
        elif cmd.command == 'save':
            self.save_file()
        elif cmd.command == 'show_file':
            self.show_file_content()
        elif cmd.command == 'navigator':
            self.show_navigator()
        elif cmd.command == 'batch':
            self.show_batcher(self.ui.menubar)
        elif cmd.command == 'viewers_changed':
            ...

    def show_log(self):
        """Open the log file in the default text editor"""
        import webbrowser
        webbrowser.open(logger.parent.handlers[0].baseFilename)

    def quit_fun(self):
        """
            Quit the current instance of DAQ_scan

            See Also
            --------
            quit_fun
        """
        try:
            if self.temp_path is not None:
                try:
                    self.h5temp.close()
                    self.temp_path.cleanup()
                except Exception as e:
                    logger.exception(str(e))

            self.close_file()
            self.mainwindow.close()

        except Exception as e:
            logger.exception(str(e))

    def create_dataset_settings(self):
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
            {'title': 'Scan type:', 'name': 'scan_type', 'type': 'str', 'value': ''},
            {'title': 'Scan subtype:', 'name': 'scan_sub_type', 'type': 'str', 'value': ''},
            {'title': 'Scan name:', 'name': 'scan_name', 'type': 'str', 'value': '', 'readonly': True},
            {'title': 'Description:', 'name': 'description', 'type': 'text', 'value': ''},
        ]}]

        self.dataset_attributes = Parameter.create(name='Attributes', type='group', children=params_dataset)
        self.scan_attributes = Parameter.create(name='Attributes', type='group', children=params_scan)
    ###################
    # external modules

    def show_batcher(self, menubar):
        self.batcher = BatchScanner(self.dockarea, self.modules_manager.actuators_all,
                                    self.modules_manager.detectors_all)
        self.batcher.create_menu(menubar)
        self.batcher.setupUI()
        self.ui.set_action_visible('start_batch', True)

    def start_scan_batch(self):
        self.batch_started = True
        self.ind_batch = 0
        self.loop_scan_batch()

    def loop_scan_batch(self):
        if self.ind_batch >= len(self.batcher.scans_names):
            self.stop_scan()
            return
        self.scanner = self.batcher.get_scan(self.batcher.scans_names[self.ind_batch])
        actuators, detectors = self.batcher.get_act_dets()
        self.set_scan_batch(actuators[self.batcher.scans_names[self.ind_batch]],
                            detectors[self.batcher.scans_names[self.ind_batch]])
        self.start_scan()

    def set_scan_batch(self, actuators, detectors):
        self.modules_manager.selected_detectors_name = detectors
        self.modules_manager.selected_actuators_name = actuators
        QtWidgets.QApplication.processEvents()

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
        if SHOW_POPUPS:
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
        else:
            res = True
        return res

    def show_file_content(self):
        try:
            self.h5saver.show_file_content()
        except Exception as e:
            logger.exception(str(e))

    def show_navigator(self):

        if self.navigator is None:
            # loading navigator
            self.navigator_dock = gutils.Dock('Navigator')
            widgnav = QtWidgets.QWidget()
            self.navigator_dock.addWidget(widgnav)
            self.dockarea.addDock(self.navigator_dock)
            self.navigator_dock.float()

            self.navigator = Navigator(widgnav)

            self.navigator.log_signal[str].connect(self.dashboard.add_status)
            self.navigator.settings.child('settings', 'Load h5').hide()
            self.navigator.set_action_visible('load_scan', False)

            self.navigator.sig_double_clicked.connect(self.move_at)
            self.navigator.h5saver = self.h5saver
            self.navigator.list_2D_scans()

        self.show_scan_selector()

    def show_scan_selector(self):
        viewer_items = []
        if self.navigator is not None:
            viewer_items.append(SelectorItem(self.navigator.viewer, name='Navigator'))
        #
        # for viewer in self.live_plotter.viewers:
        #     viewer_items.update({viewer.title: dict(viewers=[viewer], names=[viewer.title])})
        self.scan_selector = ScanSelector(viewer_items)

        self.ui.add_scanner_settings(self.scan_selector.settings_tree)

        self.scan_selector.scan_select_signal.connect(self.scanner.update_from_scan_selector)

    ################
    #  LOADING SAVING

    def load_file(self):
        self.h5saver.load_file(self.h5saver.h5_file_path)

    def save_file(self):
        if not os.path.isdir(self.h5saver.settings['base_path']):
            os.mkdir(self.h5saver.settings['base_path'])
        filename = gutils.file_io.select_file(self.h5saver.settings['base_path'], save=True, ext='h5')
        self.h5saver.h5_file.copy_file(str(filename), overwrite=True)

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
        for child in params.child(type_info).children():
            if type(child.value()) is QDateTime:
                attr[child.name()] = child.value().toString('dd/mm/yyyy HH:MM:ss')
            else:
                attr[child.name()] = child.value()
        if type_info == 'dataset_info':
            # save contents of given parameter object into an xml string under the attribute settings
            settings_str = b'<All_settings title="All Settings" type="group">' + \
                           ioxml.parameter_to_xml_string(params) + \
                           ioxml.parameter_to_xml_string(self.settings)
                           # ioxml.parameter_to_xml_string(
                           #     self.dashboard.preset_manager.preset_params) +\
            settings_str += b'</All_settings>'
            attr['settings'] = settings_str

        elif type_info == 'scan_info':
            settings_all = [ioxml.parameter_to_xml_string(params),
                           ioxml.parameter_to_xml_string(self.settings),
                           ioxml.parameter_to_xml_string(self.h5saver.settings),
                           ioxml.parameter_to_xml_string(self.scanner.settings)]

            settings_str = b'<All_settings title="All Settings" type="group">'
            for set in settings_all:
                if len(settings_str + set) < 60000:
                    # size limit for any object header (including all the other attributes) is 64kb
                    settings_str += set
                else:
                    break
            settings_str += b'</All_settings>'
            attr['settings'] = settings_str

    def create_new_file(self, new_file):
        if new_file:
            self._metada_dataset_set = False
            self.close_file()

        self.module_and_data_saver.h5saver = self.h5saver  # force it for detectors to update their h5saver
        res = self.update_file_settings()
        if new_file:
            self.ui.enable_start_stop()
        return res

    @property
    def h5saver(self):
        if self._h5saver is None:
            self._h5saver = H5Saver(backend=config('general', 'hdf5_backend'))
        if self._h5saver.h5_file is None:
            self._h5saver.init_file(update_h5=True)
        if not self._h5saver.isopen():
            self._h5saver.init_file(addhoc_file_path=self._h5saver.settings['current_h5_file'])
        return self._h5saver

    @h5saver.setter
    def h5saver(self, h5saver_temp: H5Saver):
        self._h5saver = h5saver_temp

    def close_file(self):
        self.h5saver.close_file()

    @property
    def module_and_data_saver(self):
        if not self._module_and_data_saver.h5saver.isopen():
            self._module_and_data_saver.h5saver = self.h5saver
        return self._module_and_data_saver

    @module_and_data_saver.setter
    def module_and_data_saver(self, mod: module_saving.ScanSaver):
        self._module_and_data_saver = mod
        self._module_and_data_saver.h5saver = self.h5saver

    def update_file_settings(self):
        try:
            res = True
            if not self._metada_dataset_set:
                res = self.set_metadata_about_dataset()
                self.save_metadata(self.h5saver.raw_group, 'dataset_info')

            if self.navigator is not None:
                self.navigator.update_h5file(self.h5saver.h5_file)
                self.navigator.settings.child('settings', 'filepath').setValue(self.h5saver.h5_file.filename)

            return res

        except Exception as e:
            logger.exception(str(e))

    def update_scan_info(self):
        # set attributes to the current group, such as scan_type....
        self.scan_attributes.child('scan_info', 'scan_type').setValue(
            self.scanner.settings.child('scan_type').value())
        self.scan_attributes.child('scan_info', 'scan_sub_type').setValue(
            self.scanner.settings.child('scan_sub_type').value())
        scan_node = self.module_and_data_saver.get_set_node(new=False)
        if scan_node.attrs['scan_done']:
            scan_name = self.module_and_data_saver.get_next_node_name()
        else:
            scan_name = scan_node.name
        self.scan_attributes.child('scan_info', 'scan_name').setValue(scan_name)
        self.scan_attributes.child('scan_info', 'description').setValue('')
        self.h5saver.settings.child('current_scan_name').setValue(scan_name)

        res = self.set_metadata_about_current_scan()
        return res

    #  PROCESS MODIFICATIONS
    def update_actuators(self, actuators: List[str]):
        self.scanner.actuators = self.modules_manager.actuators

    def move_to_crosshair(self, *args, **kwargs):
        if self.ui.is_action_checked('move_at'):
            self.modules_manager.connect_actuators()
            self.live_plotter.connect_double_clicked(self.move_at)
        else:
            self.live_plotter.disconnect(self.move_at)
            self.modules_manager.connect_actuators(False)

    def move_at(self, posx: float, posy: float = None):
        if logging.getLevelName(logger.level) == 'DEBUG':
            print(f'clicked at: {posx}, {posy}')
        positions = [posx, posy]
        positions = positions[:self.scanner.n_axes]
        actuators = self.modules_manager.actuators
        dte = data_mod.DataToExport(name="move_at")
        for ind, pos in enumerate(positions):
            dte.append(DataActuator(actuators[ind].title, data=float(pos)))

        self.modules_manager.move_actuators(dte, polling=False)

    def value_changed(self, param):
        """

        """
        if param.name() == 'scan_average':
            self.ui.show_average_step(param.value() > 1)
        elif param.name() == 'prepare_viewers':
            self.prepare_viewers()
        elif param.name() == 'plot_probe':
            self.plot_from()
        elif param.name() == 'plot_at_each_step':
            self.settings.child('plot_options', 'refresh_live').show(not param.value())

    def clear_plot_from(self):
        self.settings.child('plot_options', 'plot_0d').setValue(dict(all_items=[], selected=[]))
        self.settings.child('plot_options', 'plot_1d').setValue(dict(all_items=[], selected=[]))

    def check_number_type_viewers(self) -> Tuple[
        List[ViewersEnum],
        List[str],
        bool]:
        """ Assert from selected options the number and type of needed viewers for live plotting

        Return
        ------
        List[ViewersEnum]: the list of needed viewers
         List[str]: the list of data names to be plotted in the corresponding viewer
        """
        viewer2D_overload = False
        viewers_enum = [ViewersEnum.Viewer0D.increase_dim(self.scanner.n_axes)
                        for _ in range(len(self.settings['plot_options', 'plot_0d']['selected']))]
        data_names = self.settings['plot_options', 'plot_0d']['selected'][:]

        if self.settings['plot_options', 'group0D'] and len(viewers_enum) > 0 and ViewersEnum.Viewer1D in viewers_enum:
            viewers_enum = [ViewersEnum.Viewer1D]
            data_names = [self.live_plotter.grouped_data0D_fullname]
        elif (self.settings['plot_options', 'group0D'] and len(viewers_enum) > 0 and
              ViewersEnum.Viewer2D in viewers_enum):
            viewers_enum = [ViewersEnum.Viewer2D]
            n2Dplots = len(data_names)
            if (self.settings['scan_options', 'scan_average'] > 1 and
                self.settings['scan_options', 'average_on_top']):
                n2Dplots *= 2
            if n2Dplots > 3:
                viewer2D_overload = True
            data_names = [self.live_plotter.grouped_data0D_fullname]

        if self.scanner.n_axes <= 1:
            viewers_enum.extend([ViewersEnum.Viewer1D.increase_dim(self.scanner.n_axes)
                                 for _ in range(len(self.settings['plot_options', 'plot_1d']['selected']))])
            data_names.extend(self.settings['plot_options', 'plot_1d']['selected'][:])
        if not self.settings['scan_options', 'average_on_top']:

            viewers_enum = viewers_enum + viewers_enum
            data_names = data_names + [f'{data_name}_averaged' for data_name in data_names]

        return viewers_enum, data_names, viewer2D_overload

    def prepare_viewers(self):
        """ Assert from selected options the number and type of needed viewers for live plotting
        and prepare them on the live plot panel
        """
        viewers_enum, data_names, _ = self.check_number_type_viewers()
        self.live_plotter.prepare_viewers(viewers_enum, viewers_name=data_names)

    def update_status(self, txt: str, wait_time=0):
        """ Show the txt message in the status bar with a delay of wait_time ms.

        add an info log in the logger

        Parameters
        ----------
        txt: str
            the message to log
        wait_time: int
            leave the message apparent in the status bar for this duration in ms
        """
        self.ui.display_status(txt, wait_time)
        self.status_signal.emit(txt)
        logger.info(txt)

    def thread_status(self, status: utils.ThreadCommand):
        """ General function to get datas/infos from child thread back to the main.

        Possible commands are:

        * "Update_Status"
        * "Update_scan_index"
        * "Scan_done"
        * "Timeout"
        """
        if status.command == "Update_Status":
            self.update_status(status.attribute, wait_time=self.wait_time)

        elif status.command == "Update_scan_index":
            # status[1] = [ind_scan,ind_average]
            self.ind_scan = status.attribute[0]
            self.ui.set_scan_step(status.attribute[0] + 1)
            self.ind_average = status.attribute[1]
            self.ui.set_scan_step_average(status.attribute[1] + 1)

        elif status.command == "Scan_done":

            self.modules_manager.reset_signals()
            self.live_timer.stop()
            self.ui.set_scan_done()
            scan_node = self.module_and_data_saver.get_last_node()
            scan_node.attrs['scan_done'] = True
            self.module_and_data_saver.flush()
            self.close_file()

            if not self.batch_started:
                if not self.dashboard.overshoot:
                    self.set_ini_positions()
                self.ui.set_action_enabled('ini_positions', True)
                self.ui.set_action_enabled('start', True)

                # reactivate module controls using remote_control
                if hasattr(self.dashboard, 'remote_manager'):
                    remote_manager = getattr(self.dashboard, 'remote_manager')
                    remote_manager.activate_all(True)
                if self.navigator is not None:
                    self.navigator.list_2D_scans()
            else:
                self.ind_batch += 1
                self.loop_scan_batch()

        elif status.command == "Timeout":
            self.ui.set_permanent_status('Timeout occurred')

        elif status.command == 'add_data':
            self.module_and_data_saver.add_data(**status.attribute)

        elif status.command == 'add_nav_axes':
            self.module_and_data_saver.add_nav_axes(status.attribute)

    ############
    #  PLOTTING

    def save_temp_live_data(self, scan_data: ScanDataTemp):
        if scan_data.scan_index == 0:
            nav_axes = self.scanner.get_nav_axes()
            Naverage = self.settings['scan_options', 'scan_average']
            if Naverage > 1:
                for nav_axis in nav_axes:
                    nav_axis.index += 1
                nav_axes.append(data_mod.Axis('Average',
                                              data=np.linspace(0, Naverage - 1, Naverage),
                                              index=0))

            self.extended_saver.add_nav_axes(self.h5temp.raw_group, nav_axes)

        self.extended_saver.add_data(self.h5temp.raw_group, scan_data.data, scan_data.indexes,
                                     distribution=self.scanner.distribution)
        if self.settings['plot_options', 'plot_at_each_step']:
            self.update_live_plots()

    def update_live_plots(self):

        if self.settings['scan_options', 'scan_average'] > 1:
            average_axis = 0
        else:
            average_axis = None
        try:
            self.live_plotter.load_plot_data(group_0D=self.settings['plot_options', 'group0D'],
                                             average_axis=average_axis,
                                             average_index=self.ind_average,
                                             separate_average= not self.settings['scan_options', 'average_on_top'],
                                             target_at=self.scanner.positions[self.ind_scan],
                                             last_step=(self.ind_scan ==
                                                        self.scanner.positions.size - 1 and
                                                        self.ind_average ==
                                                        self.settings[
                                                            'scan_options', 'scan_average'] - 1))
        except Exception as e:
            logger.exception(str(e))
    #################
    #  SCAN FLOW

    def set_scan(self, scan=None) -> bool:
        """
        Sets the current scan given the selected settings. Makes some checks,
        increments the h5 file scans.
        In case the dialog is cancelled, return False and aborts the scan
        """
        try:
            res = self.update_scan_info()
            if not res:
                return False

            is_oversteps = self.scanner.set_scan()
            if is_oversteps:
                messagebox(
                    text=f"An error occurred when establishing the scan steps. Actual settings "
                         f"gives approximately {int(self.scanner.n_steps)} steps."
                         f" Please check the steps number "
                         f"limit in the config file ({config['scan']['steps_limit']}) or modify"
                         f" your scan settings.")

            _, _, viewer2D_overload = self.check_number_type_viewers()
            if viewer2D_overload:
                messagebox(text=
                           'The number of live data chosen and the selected options '
                           'will not be able to render fully on the 2D live viewers. Consider changing '
                           'the options, such as "plot on top" for the averaging or "Group 0D data" '
                           'or the number of selected data')
                return False

            if self.modules_manager.Nactuators != self.scanner.n_axes:
                messagebox(
                    text="There are not enough or too much selected move modules for this scan")
                return False

            ## TODO the stuff about adaptive scans have to be moved into a dedicated extension. M
            ## Most similat to the Bayesian one!
            if self.scanner.scan_sub_type == 'Adaptive':
                #todo include this in scanners objects for the adaptive scanners
                if len(self.modules_manager.get_selected_probed_data('0D')) == 0:
                    messagebox(
                        text="In adaptive mode, you have to pick a 0D signal from which the "
                             "algorithm will determine the next positions to scan, see 'probe_data'"
                             " in the modules selector panel")
                    return False

            self.ui.n_scan_steps = self.scanner.n_steps

            # check if the modules are initialized
            for module in self.modules_manager.actuators:
                if not module.initialized_state:
                    raise DAQ_ScanException('module ' + module.title + " is not initialized")

            for module in self.modules_manager.detectors:
                if not module.initialized_state:
                    raise DAQ_ScanException('module ' + module.title + " is not initialized")

            self.ui.enable_start_stop(True)
            return True

        except Exception as e:
            logger.exception(str(e))
            self.ui.enable_start_stop(False)

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
        self._metada_dataset_set = True
        return res

    def start_scan(self):
        """
            Start an acquisition calling the set_scan function.
            Emit the command_DAQ signal "start_acquisition".

            See Also
            --------
            set_scan
        """
        self.ui.display_status('Starting acquisition')
        self.dashboard.overshoot = False
        #deactivate double_clicked
        if self.ui.is_action_checked('move_at'):
            self.ui.get_action('move_at').trigger()

        res = self.set_scan()
        if res:
            # deactivate module controls using remote_control
            if hasattr(self.dashboard, 'remote_manager'):
                remote_manager = getattr(self.dashboard, 'remote_manager')
                remote_manager.activate_all(False)

            new_scan = self.module_and_data_saver.get_last_node().attrs['scan_done'] # get_last_node
            scan_node = self.module_and_data_saver.get_set_node(new=new_scan)
            self.save_metadata(scan_node, 'scan_info')

            self._init_live()
            Naverage = self.settings['scan_options', 'scan_average']
            if Naverage > 1:
                scan_shape = [Naverage]
                scan_shape.extend(self.scanner.get_scan_shape())
            else:
                scan_shape = self.scanner.get_scan_shape()
            for det in self.modules_manager.detectors:
                det.module_and_data_saver = (
                    module_saving.DetectorExtendedSaver(det, scan_shape))
            self.module_and_data_saver.h5saver = self.h5saver  # force the update as the h5saver ill also be set on each detectors

            # mandatory to deal with multithreads
            if self.scan_thread is not None:
                self.command_daq_signal.disconnect()
                if self.scan_thread.isRunning():
                    self.scan_thread.terminate()
                    while not self.scan_thread.isFinished():
                        QThread.msleep(100)
                    self.scan_thread = None

            self.scan_thread = QThread()

            scan_acquisition = DAQScanAcquisition(self.settings, self.scanner, self.modules_manager,
                                                  )

            if config['scan']['scan_in_thread']:
                scan_acquisition.moveToThread(self.scan_thread)
            self.command_daq_signal[utils.ThreadCommand].connect(scan_acquisition.queue_command)
            scan_acquisition.scan_data_tmp[ScanDataTemp].connect(self.save_temp_live_data)
            scan_acquisition.status_sig[utils.ThreadCommand].connect(self.thread_status)

            self.scan_thread.scan_acquisition = scan_acquisition
            self.scan_thread.start()

            self.ui.set_action_enabled('ini_positions', False)
            self.ui.set_action_enabled('start', False)
            self.ui.set_scan_done(False)
            if not self.settings['plot_options', 'plot_at_each_step']:
                self.live_timer.start(self.settings['plot_options', 'refresh_live'])
            self.command_daq_signal.emit(utils.ThreadCommand('start_acquisition'))
            self.ui.set_permanent_status('Running acquisition')
            logger.info('Running acquisition')

    def _init_live(self):
        Naverage = self.settings['scan_options', 'scan_average']
        if Naverage > 1:
            scan_shape = [Naverage]
            scan_shape.extend(self.scanner.get_scan_shape())
        else:
            scan_shape = self.scanner.get_scan_shape()
        if self.temp_path is not None:
            try:
                self.h5temp.close()
                self.temp_path.cleanup()
            except Exception as e:
                logger.exception(str(e))

        self.h5temp = H5Saver()
        self.temp_path = tempfile.TemporaryDirectory(prefix='pymo')
        addhoc_file_path = Path(self.temp_path.name).joinpath('temp_data.h5')
        self.h5temp.init_file(custom_naming=True, addhoc_file_path=addhoc_file_path)
        self.extended_saver: data_saving.DataToExportExtendedSaver =\
            data_saving.DataToExportExtendedSaver(self.h5temp, extended_shape=scan_shape)
        self.live_plotter.h5saver = self.h5temp

        self.prepare_viewers()
        QtWidgets.QApplication.processEvents()

    def set_ini_positions(self):
        """
            Send the command_DAQ signal with "set_ini_positions" list item as an attribute.
        """
        self.command_daq_signal.emit(utils.ThreadCommand("set_ini_positions"))

    def stop_scan(self):
        """
            Emit the command_DAQ signal "stop_acquisition".

            See Also
            --------
            set_ini_positions
        """
        self.ui.set_permanent_status('Stoping acquisition')
        self.command_daq_signal.emit(utils.ThreadCommand("stop_acquisition"))
        scan_node = self.module_and_data_saver.get_last_node()
        scan_node.attrs['scan_done'] = True

        if not self.dashboard.overshoot:
            self.set_ini_positions()  # do not set ini position again in case overshoot fired
            status = 'Data Acquisition has been stopped by user'
        else:
            status = 'Data Acquisition has been stopped due to overshoot'

        self.update_status(status)
        self.ui.set_permanent_status('')

        self.ui.set_action_enabled('ini_positions', True)
        self.ui.set_action_enabled('start', True)

    def do_scan(self, start_scan=True):
        """Public method to start the scan programmatically"""
        if start_scan:
            if not self.ui.is_action_enabled('start'):
                self.ui.get_action('set_scan').trigger()
                QtWidgets.QApplication.processEvents()
            self.ui.get_action('start').trigger()
        else:
            self.ui.get_action('stop').trigger()


class DAQScanAcquisition(QObject):
    """
        =========================== ========================================

        =========================== ========================================

    """
    scan_data_tmp = Signal(ScanDataTemp)
    status_sig = Signal(utils.ThreadCommand)

    def __init__(self, scan_settings: Parameter = None, scanner: Scanner = None,
                 modules_manager: ModulesManager = None,):

        """
        DAQScanAcquisition deal with the acquisition part of daq_scan, that is transferring commands to modules,
        getting back data, saviong and letting know th UI about the scan status

        """

        super().__init__()

        self.scan_settings = scan_settings
        self.modules_manager = modules_manager
        self.scanner = scanner

        self.stop_scan_flag = False
        self.Naverage = self.scan_settings['scan_options', 'scan_average']
        self.ind_average = 0
        self.ind_scan = 0

        self.isadaptive = self.scanner.scan_sub_type == 'Adaptive'

        self.modules_manager.timeout_signal.connect(self.timeout)
        self.timeout_scan_flag = False


        self.move_done_flag = False
        self.det_done_flag = False

        self.det_done_datas = data_mod.DataToExport('ScanData')

        scan_shape = self.scanner.get_scan_shape()
        if self.Naverage > 1:
            self.scan_shape = [self.Naverage]
            self.scan_shape.extend(scan_shape)
        else:
            self.scan_shape = scan_shape

    def queue_command(self, command: utils.ThreadCommand):
        """Process the commands sent by the main ui

        Parameters
        ----------
        command: utils.ThreadCommand
        """
        if command.command == "start_acquisition":
            self.start_acquisition()

        elif command.command == "stop_acquisition":
            self.stop_scan_flag = True

        elif command.command == "set_ini_positions":
            self.set_ini_positions()

        elif command.command == "move_stages":
            self.modules_manager.move_actuators(command.attribute, polling=False)

    def set_ini_positions(self):
        """ Set the actuators's positions totheir initial value as defined in the scanner  """
        try:
            if self.scanner.scan_sub_type != 'Adaptive':
                self.modules_manager.move_actuators(self.scanner.positions_at(0), polling=False)

        except Exception as e:
            logger.exception(str(e))

    def start_acquisition(self):
        try:
            #todo hoaw to apply newlayout to adaptive mode? => cannot has to be a new extension

            self.modules_manager.connect_actuators()
            self.modules_manager.connect_detectors()

            self.stop_scan_flag = False

            Naxes = self.scanner.n_axes
            scan_type = self.scanner.scan_type
            self.navigation_axes = self.scanner.get_nav_axes()
            self.status_sig.emit(utils.ThreadCommand("Update_Status",
                                                     attribute="Acquisition has started"))

            self.timeout_scan_flag = False
            for ind_average in range(self.Naverage):
                self.ind_average = ind_average
                self.ind_scan = -1
                while True:
                    self.ind_scan += 1
                    if not self.isadaptive:
                        if self.ind_scan >= len(self.scanner.positions):
                            break
                        positions = self.scanner.positions_at(self.ind_scan)  # get positions
                    else:
                        pass
                        #todo update for v4
                        # positions = learner.ask(1)[0][-1]  # next point to probe
                        # if self.scanner.scan_type == 'Tabular':  # translate normalized curvilinear position to real coordinates
                        #     self.curvilinear = positions
                        #     length = 0.
                        #     for v in self.scanner.vectors:
                        #         length += v.norm()
                        #         if length >= self.curvilinear:
                        #             vec = v
                        #             frac_curvilinear = (self.curvilinear - (length - v.norm())) / v.norm()
                        #             break
                        #
                        #     position = (vec.vectorize() * frac_curvilinear).translate_to(vec.p1()).p2()
                        #     positions = [position.x(), position.y()]

                    self.status_sig.emit(
                        utils.ThreadCommand("Update_scan_index",
                                            attribute=[self.ind_scan, ind_average]))

                    if self.stop_scan_flag or self.timeout_scan_flag:
                        break

                    #move motors of modules and wait for move completion
                    positions = self.modules_manager.order_positions(self.modules_manager.move_actuators(positions))

                    QThread.msleep(self.scan_settings['time_flow', 'wait_time_between'])

                    #grab datas and wait for grab completion
                    self.det_done(self.modules_manager.grab_datas(positions=positions), positions)

                    if self.isadaptive:
                        #todo update for v4
                        # det_channel = self.modules_manager.get_selected_probed_data()
                        # det, channel = det_channel[0].split('/')
                        # if self.scanner.scan_type == 'Tabular':
                        #     self.curvilinear_array.append(np.array([self.curvilinear]))
                        #     new_positions = self.curvilinear
                        # elif self.scanner.scan_type == 'Scan1D':
                        #     new_positions = positions[0]
                        # else:
                        #     new_positions = positions[:]
                        # learner.tell(new_positions, self.modules_manager.det_done_datas[det]['data0D'][channel]['data'])
                        pass

                    # daq_scan wait time
                    QThread.msleep(self.scan_settings.child('time_flow', 'wait_time').value())

            self.modules_manager.timeout_signal.disconnect()
            self.modules_manager.connect_actuators(False)
            self.modules_manager.connect_detectors(False)

            self.status_sig.emit(utils.ThreadCommand("Update_Status",
                                                     attribute="Acquisition has finished"))
            self.status_sig.emit(utils.ThreadCommand("Scan_done"))


        except Exception as e:
            logger.exception(str(e))

    def det_done(self, det_done_datas: data_mod.DataToExport, positions):
        """

        """
        try:
            indexes = self.scanner.get_indexes_from_scan_index(self.ind_scan)
            if self.Naverage > 1:
                indexes = [self.ind_average] + list(indexes)
            indexes = tuple(indexes)
            if self.ind_scan == 0:
                nav_axes = self.scanner.get_nav_axes()
                if self.Naverage > 1:
                    for nav_axis in nav_axes:
                        nav_axis.index += 1
                    nav_axes.append(data_mod.Axis('Average', data=np.linspace(0, self.Naverage - 1, self.Naverage),
                                                  index=0))
                self.status_sig.emit(utils.ThreadCommand("add_nav_axes", nav_axes))

            self.status_sig.emit(
                utils.ThreadCommand("add_data",
                                    dict(indexes=indexes, distribution=self.scanner.distribution)))

            #todo related to adaptive (solution lies along the Enlargeable data saver)
            if self.isadaptive:
                for ind_ax, nav_axis in enumerate(self.navigation_axes):
                    nav_axis.append(np.array(positions[ind_ax]))

            self.det_done_flag = True

            full_names: list = self.scan_settings['plot_options', 'plot_0d']['selected'][:]
            full_names.extend(self.scan_settings['plot_options', 'plot_1d']['selected'][:])
            data_temp = det_done_datas.get_data_from_full_names(full_names, deepcopy=False)
            n_nav_axis_selection = 2-len(indexes) + 1 if self.Naverage > 1 else 2-len(indexes)
            data_temp = data_temp.get_data_with_naxes_lower_than(n_nav_axis_selection)  # maximum Data2D included nav indexes

            self.scan_data_tmp.emit(ScanDataTemp(self.ind_scan, indexes, data_temp))

        except Exception as e:
            logger.exception(str(e))

    def timeout(self):
        """
            Send the status signal *'Time out during acquisition'*.
        """
        self.timeout_scan_flag = True
        self.status_sig.emit(utils.ThreadCommand("Update_Status",
                                                 attribute="Timeout during acquisition"))
        self.status_sig.emit(utils.ThreadCommand("Timeout"))


def main():
    from pymodaq_gui.utils.utils import mkQApp
    from pymodaq.utils.gui_utils.loader_utils import load_dashboard_with_preset

    app = mkQApp('DAQScan')
    preset_file_name = config('presets', f'default_preset_for_scan')

    dashboard, extension, win = load_dashboard_with_preset(preset_file_name, 'DAQScan')

    app.exec()

    return dashboard, extension, win


if __name__ == '__main__':
    main()


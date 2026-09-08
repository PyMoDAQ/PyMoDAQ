#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Automated scanning module functionalities for PyMoDAQ

Contains all objects related to the DAQScan module, to do automated scans, saving data...
"""

from __future__ import annotations
import dataclasses
import logging
import os
from pathlib import Path
import tempfile
from typing import List, Tuple, TYPE_CHECKING

import numpy as np
from qtpy import QtWidgets, QtCore
from qtpy.QtWidgets import QDialogButtonBox
from qtpy.QtCore import QObject, QThread, Signal, QDateTime, QDate, QTime, QTimer

from managers.h5manager import FileAction, H5Manager
from plotting.data_viewers import ViewerDispatcher
from pymodaq.control_modules.enums import MoveType
from pymodaq.utils.custom_ext import CustomExt
from pymodaq.utils.managers.modules import ModuleType
from pymodaq_data.plotting.utils import PlotColors

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import GlobalConfig as Config
from pymodaq_utils import utils

from pymodaq_data import DataDistribution, DataDim, DataToExport, Axis
from pymodaq_data.h5modules import data_saving

from pymodaq_gui.parameter import ioxml, Parameter
from pymodaq_gui.plotting.data_viewers import ViewersEnum
from pymodaq_gui.managers.parameter_manager import ParameterTree
from pymodaq_gui.plotting.navigator import Navigator
from pymodaq_gui.messenger import messagebox
from pymodaq_gui import utils as gutils
from pymodaq_gui.h5modules.saving import H5Saver
from pymodaq_gui.utils.enums import MenuToolbarNames

from pymodaq.utils.scanner.scanner import Scanner
from pymodaq.utils.managers.batchscan_manager import BatchScanner
from pymodaq.utils.managers.modules.modules_manager import ModulesManager
from pymodaq.post_treatment.load_and_plot import LoaderPlotter

from pymodaq.utils.h5modules import module_saving
from pymodaq.utils.scanner.scan_selector import ScanSelector, SelectorItem
from pymodaq.utils.data import DataActuator
from pymodaq.extensions.scan.manager.scan_manager import ScanManager
from pymodaq_gui.utils.widgets.spinbox import QSpinBox_ro
from pymodaq_gui.utils.widgets import QLED
from pymodaq_gui.utils.custom_app import CustomApp

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard

config = Config()

logger = set_logger(get_module_name(__file__))

SHOW_POPUPS = config('pymodaq', 'scan', 'show_popups')


class DAQ_ScanException(Exception):
    """Raised when an error occur within the DAQScan"""
    pass

class ScanStepError(Exception):
    """Raised when an error occurs during a scan step"""


@dataclasses.dataclass
class ScanData:
    """Convenience class to hold data to be saved or plotted"""
    dte: DataToExport
    indexes: list[int]
    distribution: DataDistribution
    scan_index: int


class ScanStatusBarManager:

    def __init__(self, scan: DAQScan):
        self.scan = scan

        self._n_scan_steps_sb: QSpinBox_ro = None
        self._indice_scan_sb: QSpinBox_ro = None
        self._indice_average_sb: QSpinBox_ro = None

        self._scan_done_LED: QLED = None

    @property
    def statusbar(self):
        return self.scan.statusbar

    def set_permanent_status(self, status: str):
        self.scan.set_permanent_status(status)

    def create_permanent_widgets(self):

        #custom app already creates a permanent label one can access with set_permanent_status
        self._n_scan_steps_sb = QSpinBox_ro()
        self._n_scan_steps_sb.setToolTip('Total number of steps')
        self._indice_scan_sb = QSpinBox_ro()
        self._indice_scan_sb.setToolTip('Current step value')
        self._indice_average_sb = QSpinBox_ro()
        self._indice_average_sb.setToolTip('Current average value')

        self._scan_done_LED = QLED()
        self._scan_done_LED.set_as_false()
        self._scan_done_LED.clickable = False
        self._scan_done_LED.setToolTip('Scan done state')

        self.statusbar.insertPermanentWidget(1, self._n_scan_steps_sb) # 1 because there is already the permanent label
        self.statusbar.insertPermanentWidget(2, self._indice_scan_sb)
        self.statusbar.insertPermanentWidget(3, self._indice_average_sb)
        self._indice_average_sb.setVisible(False)
        self.statusbar.insertPermanentWidget(4, self._scan_done_LED)

    @property
    def n_scan_steps(self):
        return self._n_scan_steps_sb.value()

    @n_scan_steps.setter
    def n_scan_steps(self, nsteps: int):
        self._n_scan_steps_sb.setValue(nsteps)

    def set_scan_step(self, step_ind: int):
        self._indice_scan_sb.setValue(step_ind)

    def show_average_step(self, show: bool = True):
        self._indice_average_sb.setVisible(show)

    def set_scan_step_average(self, step_ind: int):
        self._indice_average_sb.setValue(step_ind)

    def set_scan_done(self, done=True):
        self._scan_done_LED.set_as(done)


class DAQScan(CustomExt):
    """
    Main class initializing a DAQScan module with its dashboard and scanning control panel
    """
    settings_name = 'daq_scan_settings'
    show_h5file_statusbar_widgets = True

    command_daq_signal = Signal(utils.ThreadCommand)
    scan_done_signal = QtCore.Signal()

    icon_name = 'qr_code_scanner'

    params = [
        {'title': 'Worker:', 'name': 'worker', 'type': 'group', 'children': [
            {'title': 'Worker Running:', 'name': 'worker_running', 'type': 'led', 'value': False, 'readonly': True},
            {'title': 'Worker tasks:', 'name': 'worker_tasks', 'type': 'int', 'value': 0, 'readonly': True},
        ]},
        {'title': 'Time Flow:', 'name': 'time_flow', 'type': 'group', 'expanded': False,
         'children': [
            {'title': 'Wait time step (ms)', 'name': 'wait_time', 'type': 'int', 'value': 0,
             'tip': 'Wait time in ms after each step of acquisition (move and grab)'},
            {'title': 'Wait time between (ms)', 'name': 'wait_time_between', 'type': 'int',
             'value': 0,
             'tip': 'Wait time in ms between move and grab processes'},
        ]},
        {'title': 'Scan options', 'name': 'scan_options', 'type': 'group', 'children': [
            {'title': 'Naverage:', 'name': 'scan_average', 'type': 'int',
             'value': config('pymodaq', 'scan', 'Naverage'), 'min': 1},
            {'title': 'Plot on top:', 'name': 'average_on_top', 'type': 'bool',
             'value': config('pymodaq', 'scan', 'average_on_top'),
             'tip': 'At the second iteration will plot the averaged scan on top (True) of the current one'
                    'or in a second panel (False)'},
            {'title': 'Go to ini. positions:', 'name': 'go_to_ini_positions', 'type': 'bool',
             'value': True,
             'tip': 'Move actuators back to their initial positions when the scan ends or is stopped'},
            {'title': 'Stop on timeout:', 'name': 'stop_on_timeout', 'type': 'bool',
             'value': config('pymodaq', 'scan', 'stop_on_timeout'),
             'tip': 'If a hardware timeout occurs while waiting for an actuator or detector, '
                    'stop the scan. If unchecked, the scan will move on to the next step'},
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

        super().__init__(parent=dockarea,
                         dashboard=dashboard,
                         add_toolbar_break=False)

        self.wait_time = 1000
        self._show_popups: bool = SHOW_POPUPS # wether to show or not the popups
        self.navigator: Navigator = None
        self.scan_selector: ScanSelector = None
        self.scan_acquisition: DAQScanAcquisition = None

        self.ind_scan = 0
        self.ind_average = 0

        self._metada_dataset_set = False

        self.curvilinear_values = []
        self.plot_colors = PlotColors()

        self.modules_manager.settings.child('probe_data').setOpts(expanded=False)
        self.modules_manager.settings.child('test_actuator').setOpts(expanded=False)
        self.modules_manager.detectors_changed.connect(self.clear_plot_from)


        self.h5_manager.get_h5saver(create_new_file=False).file_changed_sig.connect(self._on_file_changed)

        self._module_and_data_saver = module_saving.ScanSaver(self)


        self.extended_saver: data_saving.DataToExportExtendedSaver = None
        self.h5temp: H5Saver = None
        self.temp_path: tempfile.TemporaryDirectory = None

        self.scanner = Scanner(actuators=self.modules_manager.actuators_all,
                               selected_actuators=self.modules_manager.actuators)
        self.scan_parameters = None

        self.batcher: BatchScanner = None
        self.batch_started = False
        self.ind_batch = 0

        self.modules_manager.actuators_changed[list].connect(self.update_actuators)

        self.dock_command: gutils.Dock = None

        self.status_manager = ScanStatusBarManager(self)

        self.setup_ui()



        self.h5_manager.command_sig.connect(self.process_cmds)

        self.create_dataset_settings()

        self.set_config()

        self.live_plotter = LoaderPlotter(self.dockarea)
        self.live_timer = QtCore.QTimer(self)
        self.live_timer.timeout.connect(self.update_live_plots)

        self.scan_manager = ScanManager(self)
        self.scan_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('scan_manager'),
                                                    menu=self.get_menu('scan_manager'))

        if self.dashboard.experiment_manager.entry_applied:
            self.enable_start_stop(True)
            self.ini_scan_manager()

        logger.info('DAQScan Initialized')


    def ini_scan_manager(self):
        self.scan_manager.enable_actions()
        self.scan_manager.modules_manager.actuators_all = self.modules_manager.actuators_all
        self.scan_manager.modules_manager.detectors_all = self.modules_manager.detectors_all

    def get_app_toolbars(self) -> list[QtWidgets.QToolBar]:
        """ Get the main toolbars widget to be eventually added in the main window toolbararea

        Default is the default toolbar. To be reimplemented if needed
        """
        return [self.toolbar, self.get_toolbar('scan_manager')]

    def plot_from(self):
        self.modules_manager.get_det_data_list()
        data0D_names = self.modules_manager.get_probed_data_full_names(DataDim.Data0D)
        data1D_names = self.modules_manager.get_probed_data_full_names(DataDim.Data1D)
        self.settings.child('plot_options', 'plot_0d').setValue(
            dict(all_items=data0D_names, selected=data0D_names))
        self.settings.child('plot_options', 'plot_1d').setValue(
            dict(all_items=data1D_names, selected=data1D_names))

    ####

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        """ Mandatory even if empty"""
        self.add_toolbar(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), self.mainwindow,
                         toolbar=self.h5_manager.toolbar)
        self.add_menu(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), parent_menu=menubar)
        self.add_menu(MenuToolbarNames.TOOLS, MenuToolbarNames.TOOLS.capitalize(), parent_menu=menubar)
        self.add_menu('actions', 'Actions', parent_menu=menubar)

        self.add_toolbar('scan_manager', 'Scan Manager', parent=self.mainwindow,
                         add_break=False)
        self.add_menu('scan_manager', 'Scan Manager', MenuToolbarNames.TOOLS, icon_name=ScanManager.icon_name)

    def setup_docks_and_widgets(self):
        """ Mandatory even if empty"""
        self.dock_command = gutils.Dock('Scan Command')
        self.dockarea.addDock(self.dock_command)

        widget_command = QtWidgets.QWidget()
        widget_command.setLayout(QtWidgets.QVBoxLayout())
        self.dock_command.addWidget(widget_command)

        splitter_widget = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter_v_widget = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        widget_command.layout().addWidget(splitter_widget)
        splitter_widget.addWidget(splitter_v_widget)
        self.module_widget = QtWidgets.QWidget()
        self.module_widget.setLayout(QtWidgets.QVBoxLayout())
        self.module_widget.setMinimumWidth(220)
        self.module_widget.setMaximumWidth(400)

        self.plotting_widget = QtWidgets.QWidget()
        self.plotting_widget.setLayout(QtWidgets.QVBoxLayout())
        self.plotting_widget.setMinimumWidth(220)
        self.plotting_widget.setMaximumWidth(400)

        self.plotting_settings_tree = ParameterTree()
        self.plotting_widget.layout().addWidget(self.plotting_settings_tree)

        settings_widget = QtWidgets.QWidget()
        settings_widget.setLayout(QtWidgets.QVBoxLayout())
        settings_widget.setMinimumWidth(220)

        splitter_v_widget.addWidget(self.module_widget)
        splitter_v_widget.addWidget(self.plotting_widget)

        splitter_v_widget.setSizes([400, 400])
        splitter_widget.addWidget(settings_widget)

        self.populate_status_bar()

        self.settings_toolbox = QtWidgets.QToolBox()
        settings_widget.layout().addWidget(self.settings_toolbox)
        self.scanner_widget = QtWidgets.QWidget()
        self.scanner_widget.setLayout(QtWidgets.QVBoxLayout())
        self.settings_toolbox.addItem(self.scanner_widget, 'Scanner Settings')

        self.create_dashboard_toolbar(add_break=False)

        self.populate_toolbox_widget([self.settings_tree,
                                      self.h5_manager.get_h5saver().settings_tree],
                                     ['General Settings', 'Save Settings'])

        self.set_scanner_settings(self.scanner.parent_widget)
        self.set_modules_settings(self.modules_manager.settings_tree)

        self.plotting_settings_tree.setParameters(self.settings.child('plot_options'))


    def setup_actions(self):
        self.add_action('ini_positions', 'Init Positions', 'arrows_input', menu='actions')
        self.set_action_enabled('ini_positions', False)
        self.add_action('start', 'Start Scan', 'motion_play', "Start the scan",
                        menu='actions', icon_color=self.get_theme().green)
        self.add_action('start_batch', 'Start ScanBatches', 'run_all', "Start the batch of scans", menu='actions')
        self.add_action('stop', 'Stop Scan', 'stop_circle', "Stop the scan",
                        menu='actions', icon_color=self.get_theme().red)
        self.add_action('pause', 'Pause Scan', 'pause_circle', "Pause/resume the scan",
                        checkable=True, menu='actions',
                        icon_checked_color=self.get_theme().orange)
        self.add_action('move_at', 'Move at doubleClicked', 'moving',
                        "Move to positions where you double clicked", checkable=True, menu='actions')

        self._toolbar.addSeparator()
        self.add_action('navigator', 'Show Navigator', '', menu=MenuToolbarNames.TOOLS, auto_toolbar=False)
        self.add_action('batch', 'Show Batch Scanner', '', menu=MenuToolbarNames.TOOLS, auto_toolbar=False)
        self.set_action_visible('start_batch', False)

    def connect_things(self):
        self.scanner.scanner_updated_signal.connect(self.do_things_after_scanner_changed)

        self.connect_action('ini_positions', self.set_ini_positions)
        self.connect_action('start', self.start_scan)
        self.connect_action('start_batch', self.start_scan_batch)
        self.connect_action('stop', self.stop_scan)
        self.connect_action('pause', self.pause_scan)
        self.connect_action('move_at', self.move_to_crosshair)

        self.connect_action('navigator', self.show_navigator)
        self.connect_action('batch', lambda: self.show_batcher(self.menubar))

    def process_cmds(self, cmd: utils.ThreadCommand):
        """Process commands sent by actions done in the ui

        Parameters
        ----------
        cmd: ThreadCommand
            Possible values are:
                * load
                * viewers_changed
        """
        if cmd.command == FileAction.LOAD:
            self.load_file()

    def do_things_after_scanner_changed(self):
        self.set_action_enabled('ini_positions',
                                self.scanner.actuators == self.modules_manager.actuators)

    def do_things_after_ui_setup(self):
        self.enable_start_stop(False)

    def do_things_after_experiment_set(self, experiment_name: str):
        """ This method is called whenever a experiment entry has been set.

        Its main purpose is to update the list of control modules in the manager and
        some other actions.

        Can be reimplemented to add some more evolved actions
        """

        super().do_things_after_experiment_set(experiment_name)

        # set the module saver type and applies its h5saver to submodules
        self._module_and_data_saver = module_saving.ScanSaver(self)

        self.enable_start_stop(True)

        if hasattr(self, 'scan_manager'):
            self.ini_scan_manager()

    @property
    def module_and_data_saver(self) -> module_saving.ScanSaver:
        return super().module_and_data_saver

    ################
    #  CONFIG/SETUP UI / EXIT

    def set_config(self):
        self.settings.child('time_flow', 'wait_time').setValue(config('pymodaq', 'scan', 'timeflow', 'wait_time'))
        self.settings.child('time_flow', 'wait_time_between').setValue(config('pymodaq', 'scan', 'timeflow', 'wait_time'))

        self.settings.child('scan_options', 'scan_average').setValue(config('pymodaq', 'scan', 'Naverage'))
        self.settings.child('scan_options', 'stop_on_timeout').setValue(
            config('pymodaq', 'scan', 'stop_on_timeout'))

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

            self.h5_manager.close_file()

            super().quit_fun()

        except Exception as e:
            logger.exception(str(e))

    def create_dataset_settings(self):
        # params about dataset attributes and scan attibutes
        date = QDateTime(QDate.currentDate(), QTime.currentTime())
        params_dataset = [{'title': 'Dataset information', 'name': 'dataset_info', 'type': 'group', 'children': [
            {'title': 'Author:', 'name': 'author', 'type': 'str', 'value': config('utils', 'user', 'name')},
            {'title': 'Date/time:', 'name': 'date_time', 'type': 'date_time', 'value': date},
            {'title': 'Sample:', 'name': 'sample', 'type': 'str', 'value': ''},
            {'title': 'Experiment type:', 'name': 'experiment_type', 'type': 'str', 'value': ''},
            {'title': 'Description:', 'name': 'description', 'type': 'text', 'value': ''}]}]

        params_scan = [{'title': 'Scan information', 'name': 'scan_info', 'type': 'group', 'children': [
            {'title': 'Author:', 'name': 'author', 'type': 'str', 'value': config('utils', 'user', 'name')},
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
        self.set_action_visible('start_batch', True)

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

    def override_popups(self, override=True):
        self._show_popups = override

    def cancel_override_popups(self):
        self._show_popups = SHOW_POPUPS

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
        if self._show_popups:
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
            buttonBox = QDialogButtonBox(parent=dialog)
            buttonBox.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
            buttonBox.addButton("Apply", QDialogButtonBox.ButtonRole.AcceptRole)
            buttonBox.rejected.connect(dialog.reject)
            buttonBox.accepted.connect(dialog.accept)

            vlayout.addWidget(buttonBox)
            dialog.setWindowTitle('Fill in information about this {}'.format(type_info))
            res = dialog.exec()
        else:
            res = True
        return res

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

        self.scanner_widget.layout().addWidget(self.scan_selector.settings_tree)

        self.scan_selector.scan_select_signal.connect(self.scanner.update_from_scan_selector)

    def populate_toolbox_widget(self, widgets: List[QtWidgets.QWidget], names: List[str]):
        for widget, name in zip(widgets, names):
            self.settings_toolbox.addItem(widget, name)

    def set_scanner_settings(self, settings_tree: QtWidgets.QWidget):
        while True:
            child = self.scanner_widget.layout().takeAt(0)
            if not child:
                break
            child.widget().deleteLater()
            QtWidgets.QApplication.processEvents()

        self.scanner_widget.layout().addWidget(settings_tree)

    def set_modules_settings(self, settings_widget):
        self.module_widget.layout().addWidget(settings_widget)

    def populate_status_bar(self):
        super().populate_status_bar()
        self.status_manager.create_permanent_widgets()
        self.status_manager.set_permanent_status('Initializing')

    def enable_start_stop(self, enable=True):
        """If True enable main buttons to launch/stop scan"""
        self.set_action_enabled('start', enable)
        self.set_action_enabled('stop', enable)
        self.set_action_enabled('pause', enable)
        if enable:
            self.set_action_checked('pause', False)

    ################
    #  LOADING SAVING

    def load_file(self):
        # Opening an existing file resets the dataset metadata so the user is prompted
        # to confirm/update it on the next scan (restores behaviour lost in past versions).
        self._metada_dataset_set = False
        self.update_file_settings()

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

            for name, param in ((self.__class__.__name__.lower(), self.settings),
                                ('scan_info', params),
                                ('saver', self.h5saver.settings),
                                ('scanner', self.scanner.settings),):

                _settings = Parameter.create(name=f'{name}_settings', type='group',
                                             children=[param.saveState()])
                attr[name] = ioxml.parameter_to_xml_string(_settings)


            for instrument in self.modules_manager.modules_all:
                instrument_settings = Parameter.create(name=f'{instrument.title}_settings', type='group',
                                                      children=[instrument.settings.saveState()])
                attr[f'{instrument.title}_settings'] = ioxml.parameter_to_xml_string(instrument_settings)


    def _on_file_changed(self, file_path: str):
        """Called when H5Saver switches to a different file (e.g. browse)."""
        self.h5_manager.update_file_status_led()
        file_name = Path(file_path).name
        scan_name = self.h5saver.settings['current_scan_name']
        if scan_name:
            self.status_manager.set_permanent_status(f'{file_name} | {scan_name}')
        else:
            self.status_manager.set_permanent_status(file_name)

    def update_file_settings(self):
        try:
            res = True
            if not self._metada_dataset_set:
                res = self.set_metadata_about_dataset()
                self.save_metadata(self.h5saver.raw_group, 'dataset_info')

            if self.navigator is not None:
                self.navigator.update_h5file(self.h5saver.h5_file)
                self.navigator.settings.child('settings', 'filepath').setValue(self.h5saver.h5_file.filename)

            file_name = Path(self.h5saver.settings['current_h5_file']).name
            scan_name = self.h5saver.settings['current_scan_name']
            if scan_name:
                self.status_manager.set_permanent_status(f'{file_name} | {scan_name}')
            else:
                self.status_manager.set_permanent_status(file_name)

            return res

        except Exception as e:
            logger.exception(str(e))

    def update_scan_info(self):
        # set attributes to the current group, such as scan_type....
        self.scan_attributes.child('scan_info', 'scan_type').setValue(
            self.scanner.settings.child('scan_type').value())
        self.scan_attributes.child('scan_info', 'scan_sub_type').setValue(
            self.scanner.settings.child('scan_sub_type').value())
        # Every Start creates a new scan node; predict the name it will receive.
        last_node = self.module_and_data_saver.get_last_node()
        if last_node is None:
            scan_name = (utils.capitalize(module_saving.GroupModuleType.SCAN.name.lower())
                         + '000')
        else:
            scan_name = self.module_and_data_saver.get_next_node_name()
        self.scan_attributes.child('scan_info', 'scan_name').setValue(scan_name)
        self.scan_attributes.child('scan_info', 'description').setValue('')
        self.h5saver.settings.child('current_scan_name').setValue(scan_name)

        file_name = Path(self.h5saver.settings['current_h5_file']).name
        self.status_manager.set_permanent_status(f'{file_name} | {scan_name}')

        res = self.set_metadata_about_current_scan()
        return res

    #  PROCESS MODIFICATIONS
    def update_actuators(self, actuators: List[str]):
        self.scanner.actuators = self.modules_manager.actuators

    def move_to_crosshair(self, *args, **kwargs):
        if self.is_action_checked('move_at'):
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
        dte = DataToExport(name="move_at")
        for ind, pos in enumerate(positions):
            dte.append(DataActuator(actuators[ind].title, data=float(pos), units=actuators[ind].units))

        self.modules_manager.move_actuators(dte, polling=False)

    def value_changed(self, param):
        """

        """
        if param.name() == 'scan_average':
            self.status_manager.show_average_step(param.value() > 1)
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
        if (self.settings['scan_options', 'scan_average'] > 1 and
                not self.settings['scan_options', 'average_on_top']):

            viewers_enum = viewers_enum + viewers_enum
            data_names = data_names + [f'{data_name}_averaged' for data_name in data_names]

        return viewers_enum, data_names, viewer2D_overload

    def prepare_viewers(self):
        """ Assert from selected options the number and type of needed viewers for live plotting
        and prepare them on the live plot panel
        """
        viewers_enum, data_names, _ = self.check_number_type_viewers()
        self.live_plotter.prepare_viewers(viewers_enum, viewers_name=data_names)

    def thread_status(self, status: utils.ThreadCommand):
        """ General function to get datas/infos from child thread back to the main.

        Possible commands are:

        * "Update_Status"
        * "Update_scan_index"
        * "Scan_done"
        * "Timeout"
        """
        if status.command == "Update_Status":
            if isinstance(status.attribute, (tuple, list)):
                txt, wait_time = status.attribute
            else:
                txt, wait_time = status.attribute, self.wait_time
            self.update_status(txt, wait_time=wait_time)

        elif status.command == "Update_scan_index":
            # status[1] = [ind_scan,ind_average]
            self.ind_scan = status.attribute[0]
            self.status_manager.set_scan_step(status.attribute[0] + 1)
            self.ind_average = status.attribute[1]
            self.status_manager.set_scan_step_average(status.attribute[1] + 1)

        elif status.command == "Scan_done":

            self.modules_manager.reset_signals()
            self.live_timer.stop()
            self.status_manager.set_scan_done()
            self.scan_done_signal.emit()
            try:
                self.module_and_data_saver.flush()
                if self.h5saver.settings['close_after_scan']:
                    self.h5_manager.close_file()
            except Exception as e:
                logger.error(f"Error finalizing scan file: {e}")
                try:
                    self.h5_manager.close_file()
                except Exception:
                    pass

            if not self.batch_started:
                if self.settings['scan_options', 'go_to_ini_positions']:
                    self.set_ini_positions()
                self.set_action_enabled('ini_positions', True)
                self.set_action_enabled('start', True)

                # reactivate module controls using remote_control
                remote_manager = getattr(self.dashboard, 'remote_manager', None)
                if remote_manager is not None:
                    remote_manager.activate_all(True)
                if self.navigator is not None:
                    self.navigator.list_2D_scans()
            else:
                self.ind_batch += 1
                self.loop_scan_batch()

        elif status.command == "Timeout":
            self.status_manager.set_permanent_status(status.attribute or 'Timeout occurred')

    ############
    #  PLOTTING

    def save_temp_live_data(self, scan_data: ScanData):
        if scan_data.scan_index == 0:
            if self.scanner.scanner.do_process_data:
                viewers_enum, data_names, _ = self.check_number_type_viewers()
                for dwa in scan_data.dte:
                    if dwa.get_full_name() not in data_names:
                        viewer_enum = ViewersEnum.get_viewers_enum_from_data(dwa).increase_dim(self.scanner.n_axes)

                        if self.settings['plot_options', 'group0D'] and ViewersEnum.get_viewers_enum_from_data(dwa) == ViewersEnum.Viewer0D:
                            if not ViewersEnum.Viewer0D.increase_dim(self.scanner.n_axes) in viewers_enum:
                                viewers_enum.append(viewer_enum)
                                data_names.append(self.live_plotter.grouped_data0D_fullname)
                        else:
                            viewers_enum.append(viewer_enum)
                            data_names.append(dwa.get_full_name())

                self.live_plotter.prepare_viewers(viewers_enum, viewers_name=data_names)

            nav_axes = self.scanner.get_nav_axes()
            Naverage = self.settings['scan_options', 'scan_average']
            if Naverage > 1:
                for nav_axis in nav_axes:
                    nav_axis.index += 1
                nav_axes.append(Axis('Average',
                                     data=np.linspace(0, Naverage - 1, Naverage),
                                     index=0))

            self.extended_saver.add_nav_axes(self.h5temp.raw_group, nav_axes)

        self.extended_saver.add_data(self.h5temp.raw_group,
                                     scan_data.dte,
                                     scan_data.indexes,
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
                                             remove_navigation=self.scanner.distribution == DataDistribution.uniform,
                                             average_axis=average_axis,
                                             average_index=self.ind_average,
                                             separate_average=not self.settings['scan_options', 'average_on_top'],
                                             target_at=self.scanner.positions[self.ind_scan],
                                             last_step=(self.ind_scan ==
                                                        self.scanner.n_steps - 1 and
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
                         f"limit in the config file ({config('pymodaq', 'scan', 'steps_limit')}) or modify"
                         f" your scan settings.")

            _, _, viewer2D_overload = self.check_number_type_viewers()
            if viewer2D_overload:
                messagebox(text='The number of live data chosen and the selected options '
                           'will not be able to render fully on the 2D live viewers. Consider changing '
                           'the options, such as "plot on top" for the averaging or "Group 0D data" '
                           'or the number of selected data')
                return False

            if self.modules_manager.Nactuators != self.scanner.n_axes:
                messagebox(
                    text="There are not enough or too much selected move modules for this scan")
                return False

            self.status_manager.n_scan_steps = self.scanner.n_steps

            # check if the modules are initialized
            for module in self.modules_manager.actuators:
                if not module.initialized_state:
                    raise DAQ_ScanException('module ' + module.title + " is not initialized")

            for module in self.modules_manager.detectors:
                if not module.initialized_state:
                    raise DAQ_ScanException('module ' + module.title + " is not initialized")

            self.enable_start_stop(True)
            return True

        except Exception as e:
            logger.exception(str(e))
            self.enable_start_stop(False)

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
        self.update_status('Starting acquisition')
        #deactivate double_clicked
        if self.is_action_checked('move_at'):
            self.get_action('move_at').trigger()

        self.module_and_data_saver.h5saver = self.h5saver
        res = self.set_scan()
        if res:
            # deactivate module controls using remote_control

            remote_manager = getattr(self.dashboard, 'remote_manager', None)
            if remote_manager is not None:
                remote_manager.activate_all(False)

            scan_node = self.module_and_data_saver.get_set_node(new=True)
            self.save_metadata(scan_node, 'scan_info')

            self._init_live()
            Naverage = self.settings['scan_options', 'scan_average']
            nav_axes = self.scanner.get_nav_axes()
            if Naverage > 1:
                scan_shape = [Naverage]
                scan_shape.extend(self.scanner.get_scan_shape())
                for nav_axis in nav_axes:
                    nav_axis.index += 1
                nav_axes.insert(0, Axis('Average',
                                        data=np.linspace(0, Naverage - 1, Naverage),
                                        index=0))
            else:
                scan_shape = self.scanner.get_scan_shape()

            self.module_and_data_saver.set_scan_shape(scan_shape)
            self.module_and_data_saver.h5saver = self.h5saver
            # force the update to all submodules and to take into consideration the scan shape
            self.module_and_data_saver.initialize_time_array(scan_shape)

            if self.h5saver.swmr_mode:
                interval = self.h5saver.settings['backend', 'swmr_options', 'flush_interval']
                self.h5saver.set_swmr_flush_interval(interval)

            if self.scan_acquisition is None:
                self.ini_scan_acquisition()

            self.set_action_enabled('ini_positions', False)
            self.set_action_enabled('start', False)
            self.set_action_enabled('pause', True)
            self.set_action_checked('pause', False)
            self.status_manager.set_scan_done(False)
            if not self.settings['plot_options', 'plot_at_each_step']:
                self.live_timer.start(self.settings['plot_options', 'refresh_live'])
            self.command_daq_signal.emit(utils.ThreadCommand('start_acquisition'))
            self.status_manager.set_permanent_status('Running acquisition')
            logger.info('Running acquisition')

    def ini_scan_acquisition(self):
        self.scan_acquisition = DAQScanAcquisition(self)
        self.command_daq_signal[utils.ThreadCommand].connect(self.scan_acquisition.queue_command)
        self.scan_acquisition.scan_data_tmp[ScanData].connect(self.save_temp_live_data)
        self.scan_acquisition.status_sig[utils.ThreadCommand].connect(self.thread_status)

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
        """ Set the actuators's positions to their initial value as defined in the scanner  """
        self.scanner.set_scan()
        if self.modules_manager.actuators == self.scanner.actuators:
            self.modules_manager.connect_actuators()
            self.modules_manager.move_actuators(self.scanner.positions_at(0), polling=True)
            self.modules_manager.connect_actuators(False)

    def stop(self):
        """ Programmatic method to stop any action in the extension
        """
        self.stop_scan()

    def stop_scan(self):
        """
            Emit the command_DAQ signal "stop_acquisition".

            See Also
            --------
            set_ini_positions
        """
        self.status_manager.set_permanent_status('Stoping acquisition')
        self.command_daq_signal.emit(utils.ThreadCommand("stop_acquisition"))

        if self.settings['scan_options', 'go_to_ini_positions']:
            self.set_ini_positions()
        status = 'Data Acquisition has been stopped by user'

        self.update_status(status)
        self.status_manager.set_permanent_status('')

        self.set_action_enabled('ini_positions', True)
        self.set_action_enabled('start', True)
        self.set_action_enabled('pause', False)
        self.set_action_checked('pause', False)

    def pause_scan(self):
        """Toggle pause on the running acquisition."""
        paused = self.is_action_checked('pause')
        self.command_daq_signal.emit(utils.ThreadCommand('pause_acquisition', attribute=paused))
        if paused:
            self.status_manager.set_permanent_status('Acquisition paused')
        else:
            self.status_manager.set_permanent_status('Running acquisition')

    def do_scan(self, start_scan=True):
        """Public method to start the scan programmatically"""
        if start_scan:
            if not self.is_action_enabled('start'):
                self.get_action('set_scan').trigger()
                QtWidgets.QApplication.processEvents()
            self.get_action('start').trigger()
        else:
            self.get_action('stop').trigger()




class SaverWorker(QtCore.QObject):
    """ Worker in separated thread receiving the data from a DataGenerator
    and adding them into the enlargeable arrays with the H5file using the
     DataToExportTimedSaver """

    n_saved = QtCore.Signal(int)
    data_to_save_signal = QtCore.Signal(ScanData)
    nav_axes_signal = QtCore.Signal(list)

    def __init__(self, saver: module_saving.ScanSaver):
        super().__init__()
        self.saver: module_saving.ScanSaver  = saver
        self._n_saved = 0
        self._show_thread = True

        self.data_to_save_signal.connect(self.save_data, QtCore.Qt.ConnectionType.QueuedConnection)
        self.nav_axes_signal.connect(self.add_nav_axes, QtCore.Qt.ConnectionType.QueuedConnection)

    @QtCore.Slot(ScanData)
    def save_data(self, data: ScanData):
        if self._show_thread:
            print(f'Saving data in Qthread{self.thread()}')
            self._show_thread = False
        self.saver.add_data(data.dte, indexes=data.indexes, distribution=data.distribution,)
        self.saver.add_time(data.indexes)
        self._n_saved += 1
        self.n_saved.emit(self._n_saved)

    @QtCore.Slot(list)
    def add_nav_axes(self, axes: list[Axis]):
        self.saver.add_nav_axes(axes)



class DAQScanAcquisition(CustomApp):
    """
        =========================== ========================================

        =========================== ========================================

    """
    scan_data_tmp = Signal(ScanData)
    status_sig = Signal(utils.ThreadCommand)
    h5_data_array_ready_signal = Signal()
    scan_step_failed_signal = Signal(ScanStepError)
    _worker_done = QtCore.Signal()

    def __init__(self, daq_scan: DAQScan):

        """
        DAQScanAcquisition deal with the acquisition part of daq_scan, that is transferring commands to modules,
        getting back data, saviong and letting know th UI about the scan status

        """

        super().__init__()
        self.daq_scan = daq_scan

        self.saver_worker: SaverWorker = None
        self._n_emitted = 0

        self._running = False
        self.timeout_scan_flag = False  # for testing purpose in asserting timeout has been fired

        self.Naverage = self.daq_scan.settings['scan_options', 'scan_average']
        self._ind_average: int = None
        self._ind_scan: int = None

        self._current_dte_to_be_plotted: DataToExport = None
        self._current_indexes: tuple[int] = None

    @property
    def _h5_manager(self) -> H5Manager:
        """ Convenience property"""
        return self.daq_scan.h5_manager

    @property
    def _modules_manager(self) -> ModulesManager:
        """ Convenience property"""
        return self.daq_scan.modules_manager

    @property
    def _settings(self) -> Parameter:
        """ Convenience property"""
        return self.daq_scan.settings

    @property
    def _scanner(self) -> Scanner:
        """ Convenience property"""
        return self.daq_scan.scanner

    @property
    def _module_and_data_saver(self) -> module_saving.ScanSaver:
        """ Convenience property"""
        return self.daq_scan.module_and_data_saver


    def queue_command(self, command: utils.ThreadCommand):
        """Process the commands sent by the main ui

        Parameters
        ----------
        command: utils.ThreadCommand
        """
        if command.command == "start_acquisition":
            self.start()

        elif command.command == "stop_acquisition":
            self.stop(msg='User has stopped the acquisition')

        elif command.command == "pause_acquisition":
            self.pause()

        elif command.command == "move_stages":
            self._modules_manager.move_actuators(command.attribute, polling=False)

    def start(self):
        self._running = True
        self.set_ini_positions()

    def pause(self, do_pause: bool = True):
        if do_pause:
            self._running = False
        else:
            self._running = True

        self._modules_manager.enable_modules(do_pause)
        self._on_scan_pausing(do_pause)
        if not do_pause:
            self.advance()

    def stop(self, msg: str):
        self._running = False


        try: #1 immediately stop the emission of data to the saver worker
            self.saver_worker.data_to_save_signal.disconnect(self.saver_worker.save_data)
        except (TypeError, AttributeError):
            pass

        #2 disconnect all other signals
        try:
            self.scan_step_failed_signal.disconnect(self._on_scan_step_failed)
        except (TypeError, AttributeError):
            pass
        try:
            self._modules_manager.timeout_signal.disconnect(self.timeout)
        except (TypeError, AttributeError):
            pass
        self._modules_manager.connect_actuators(False)
        self._modules_manager.connect_detectors(False)
        self._modules_manager.enable_modules(True)

        #3 terminate the saver worker once its queue is empty
        if self._settings['worker', 'worker_tasks'] == 0:
            self.terminate_worker()
        else:
            self._worker_done.connect(self.terminate_worker)

        #4 update the GUI
        self.daq_scan.set_action_checked('pause', False)
        self._update_status(msg)
        self.status_sig.emit(utils.ThreadCommand("Scan_done"))

    def set_ini_positions(self):
        """ Set the actuators's positions to their initial value as defined in the scanner  """
        self._modules_manager.move_actuators_with_callback(
            self._scanner.positions_at(0),
            mode=MoveType.ABS,
            callback=self._on_ini_positions)

    def _on_ini_positions(self, dte: DataToExport):
        self._update_status("Initial values of actuators reached!")
        self._modules_manager.forget_callback(self._on_ini_positions,
                                             module_type=ModuleType.Actuator,
                                             disconnect_modules=True)
        if self._running:
            self.init_scan()
            self.advance()

    def init_scan(self):
        try:

            self._running = True
            print(f'Main Qthread: {self.thread()}')
            try:
                self._worker_done.disconnect(self.terminate_worker)
            except TypeError:
                pass

            # managing saver worker
            self._module_and_data_saver.h5saver = self.daq_scan.h5saver
            self.saver_worker = SaverWorker(saver=self.module_and_data_saver,)
            self.thread_manager.create_thread_for_worker('saver', self.saver_worker)
            self.saver_worker.n_saved.connect(self.update_worker_ntask)
            self.thread_manager.start_thread('saver')


            self._modules_manager.connect_actuators(True)
            self._modules_manager.connect_detectors(True)
            self._modules_manager.timeout_signal.connect(self.timeout)

            self.scan_step_failed_signal.connect(self._on_scan_step_failed)

            self._modules_manager.enable_modules(False)
            self._update_status("Acquisition has started")
            self._ind_average = 0
            self._ind_scan = -1

        except Exception as e:
            self.scan_step_failed_signal.emit(ScanStepError(f"Error at init step:\n"
                                                            f"{str(e)}"))

    @QtCore.Slot(int)
    def update_worker_ntask(self, n_saved: int):
        n_tasks = self._n_emitted - n_saved
        self._settings['worker', 'worker_tasks'] = n_tasks

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
        self._module_and_data_saver.h5saver.flush()
        self._module_and_data_saver.h5saver.close_file()
        self.h5_manager.update_file_status_led()

        #5 updating GUI info
        self.daq_scan.enable_start_stop(True)
        self._settings['worker', 'worker_running'] = False

    def _on_scan_pausing(self, pausing=True):
        if pausing:
            message = "Acquisition has been paused"
        else:
            message = "Acquisition resumed"

        self._update_status(message)
        logger.info(message)

    def advance(self):
        try:
            if not self._running:
                return

            if self._ind_average == self.Naverage-1 and self._ind_scan == self._scanner.n_steps-1:
                self.stop('The acquisition has finished')
                return
            elif self._ind_scan == self._scanner.n_steps-1:
                self._ind_average += 1
                self._ind_scan = -1

            self._ind_scan += 1


            positions = self.get_next_position()

            self._modules_manager.move_actuators_with_callback(
                positions,
                mode=MoveType.ABS,
                callback=self._on_move_done,
                do_connect_modules=False)

        except Exception as e:
            self.scan_step_failed_signal.emit(ScanStepError(f"Error at advance step:\n"
                                                            f"ind_step: {self._ind_scan}:\n"
                                                            f"ind_average: {self._ind_average}:\n"
                                                            f"{str(e)}"))

    def get_next_position(self) -> DataToExport:
        try:

            self.status_sig.emit(
                utils.ThreadCommand("Update_scan_index",
                                    attribute=[self._ind_scan, self._ind_average]))
            return self._scanner.positions_at(self._ind_scan)  # get positions
        except Exception as e:
            self.scan_step_failed_signal.emit(ScanStepError(f"Error when getting next step position:\n"
                                                            f"ind_step: {self._ind_scan}:\n"
                                                            f"ind_average: {self._ind_average}:\n"
                                                            f"{str(e)}"))

    def _on_move_done(self, move_dte: DataToExport):
        try:
            self._modules_manager.forget_callback(self._on_move_done,
                                                 module_type=ModuleType.Actuator,
                                                 disconnect_modules=False)
            self._modules_manager.order_positions(move_dte)

            QTimer.singleShot(int(self._settings['time_flow', 'wait_time_between']),
                              self.grab_data)
        except Exception as e:
            self.scan_step_failed_signal.emit(ScanStepError(f"Error at move_done step:\n"
                                                            f"ind_step: {self._ind_scan}:\n"
                                                            f"ind_average: {self._ind_average}:\n"
                                                            f"{str(e)}"))

    def grab_data(self):
        try:
            self._modules_manager.grab_data_with_callback(check_do_override=True,
                                                         Naverage=None,
                                                         callback=self._on_grab_done,
                                                         do_connect_modules=False)
        except Exception as e:
            self.scan_step_failed_signal.emit(ScanStepError(f"Error at grab step:\n"
                                                            f"ind_step: {self._ind_scan}:\n"
                                                            f"ind_average: {self._ind_average}:\n"
                                                            f"{str(e)}"))

    def _on_grab_done(self, dte_grabed: DataToExport):
        try:
            self._modules_manager.forget_callback(self._on_grab_done,
                                                 module_type=ModuleType.Detector,
                                                 disconnect_modules=False)
            self.det_done(dte_grabed)

        except Exception as e:
            self.scan_step_failed_signal.emit(ScanStepError(f"Error at grab_done step:\n"
                                                            f"ind_step: {self._ind_scan}:\n"
                                                            f"ind_average: {self._ind_average}:\n"
                                                            f"{str(e)}"))

    def det_done(self, dte_grabbed):
        """

        """
        self._current_indexes = self._scanner.get_indexes_from_scan_index(self._ind_scan)
        if self.Naverage > 1:
            self._current_indexes = [self._ind_average] + list(self._current_indexes)
        self._current_indexes = tuple(self._current_indexes)

        if self._ind_scan == 0:
            self._update_status("Creating the arrays nodes in the h5file, please be patient")
            QThread.msleep(50)
            nav_axes = self._scanner.get_nav_axes()
            if self.Naverage > 1:
                for nav_axis in nav_axes:
                    nav_axis.index += 1
                nav_axes.append(Axis('Average',
                                     data=np.linspace(0, self.Naverage - 1, self.Naverage),
                                              index=0))
            self.saver_worker.nav_axes_signal.emit(nav_axes)

        if self._scanner.scanner.do_process_data:
            # extra data to be saved at the same time!
            dte_grabbed.append(self._scanner.scanner.process_data(dte_grabbed))
        else:
            full_names: list = self._settings['plot_options', 'plot_0d']['selected'][:]
            full_names.extend(self._settings['plot_options', 'plot_1d']['selected'][:])
            self._current_dte_to_be_plotted = dte_grabbed.get_data_from_full_names(full_names, deepcopy=True)
            n_nav_axis_selection = 2-len(self._current_indexes) + 1 if self.Naverage > 1 else 2-len(self._current_indexes)
            self._current_dte_to_be_plotted = self._current_dte_to_be_plotted.get_data_with_naxes_lower_than(n_nav_axis_selection)  # maximum Data2D included nav indexes

        self.saver_worker.data_to_save_signal.emit(
            ScanData(
                indexes=list(self._current_indexes),
                distribution=self._scanner.distribution,
                scan_index=self._ind_scan,
                dte=dte_grabbed,))

    def _on_h5data_ready(self):
        self.scan_data_tmp.emit(
            ScanData(dte=self._current_dte_to_be_plotted,
                     scan_index=self._ind_scan,
                     indexes=list(self._current_indexes),
                     distribution=self._scanner.distribution,
                     ))

        QTimer.singleShot(int(self._settings['time_flow', 'wait_time']),
                          self._on_scan_step_done)

    def _on_scan_step_done(self):
        try:
            self.advance()
        except Exception as e:
            self.scan_step_failed_signal.emit(ScanStepError(f"Error at det_done step:\n"
                                                            f"ind_step: {self._ind_scan}:\n"
                                                            f"ind_average: {self._ind_average}:\n"
                                                            f"{str(e)}"))

    def timeout(self, missing_modules: List[str] = None):
        """
            Send the status signal *'Time out during acquisition'*.

            Parameters
            ----------
            missing_modules: list of str
                Names of the actuators or detectors that did not answer in time
        """
        if missing_modules:
            msg = f'Timeout during acquisition, no answer received from: {", ".join(missing_modules)}'
        else:
            msg = 'Timeout during acquisition'
        self._update_status(msg)
        self.timeout_scan_flag = True
        self.status_sig.emit(utils.ThreadCommand("Timeout", attribute=msg))
        logger.warning(msg)
        if self._settings['scan_options', 'stop_on_timeout']:
            self.stop(msg=f'Scan stopped due to a Timeout')
        else:
            self.advance()

    def _update_status(self, msg: str):
        """ convenience method to update the status signal """
        self.status_sig.emit(utils.ThreadCommand("Update_Status", attribute=msg))
        logger.info(msg)

    def _on_scan_step_failed(self, exception: ScanStepError):
        logger.warning(exception)
        self.status_sig.emit(utils.ThreadCommand("Scan_done"))
        self.stop(msg=f'Scan stopped due to a failure during a step')


def main():
    import sys
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import load_dashboard_with_arguments
    from pymodaq.utils.gui_utils.loader_utils import create_extension

    app = mkQApp('DAQScan')

    win, dashboard, _ = load_dashboard_with_arguments(show_dashboard=False,
                                                      load_extension=False,
                                                      )
    win.mainwindow.setVisible(False)

    win_ext, scan = create_extension(dashboard, DAQScan,
                                     show_extension=True)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()


# -*- coding: utf-8 -*-
"""
Created on Wed Jan 10 16:54:14 2018

@author: Weber Sébastien
"""
import os

from control_modules.utils import ControlModule
from pymodaq.daq_utils.gui_utils.file_io import select_file
import pymodaq.daq_utils.gui_utils.utils
from qtpy import QtGui, QtWidgets, QtCore
from qtpy.QtCore import Qt, QObject, Slot, QThread, Signal, QRectF
import sys
from typing import List
import pymodaq.daq_utils.scanner
import copy

from pymodaq.daq_utils.plotting.data_viewers.viewer0D import Viewer0D
from pymodaq.daq_utils.plotting.data_viewers.viewer1D import Viewer1D
from pymodaq.daq_utils.plotting.data_viewers.viewer2D import Viewer2D
from pymodaq.daq_utils.plotting.data_viewers.viewerND import ViewerND
from pymodaq.daq_utils.scanner import Scanner
from pymodaq.daq_utils.plotting.navigator import Navigator
from pymodaq.daq_utils.tcp_server_client import TCPClient
from pymodaq.daq_utils.gui_utils.widgets.lcd import LCD
from pymodaq.daq_utils.config import Config, get_set_local_dir
from pymodaq.daq_utils import gui_utils as gutils
from pymodaq.daq_utils.h5modules import browse_data
from pymodaq.daq_utils.daq_utils import ThreadCommand
from pymodaq.daq_utils.exceptions import DetectorError

from collections import OrderedDict
import numpy as np

from pyqtgraph.parametertree import Parameter, ParameterTree
from pymodaq.daq_utils.parameter import ioxml
from pymodaq.daq_utils.parameter import utils as putils

from easydict import EasyDict as edict
from pymodaq.control_modules.viewer_utility_classes import params as daq_viewer_params
import pickle
import time
import datetime
import tables
from pathlib import Path
from pymodaq.daq_utils.h5modules import H5Saver
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils.messenger import deprecation_msg
from pymodaq.daq_utils.gui_utils import DockArea, Dock, get_splash_sc
from pymodaq.daq_utils.managers.parameter_manager import ParameterManager, Parameter
from pymodaq.control_modules.daq_viewer_ui import DAQ_Viewer_UI

from pymodaq.control_modules.utils import DAQ_TYPES, DET_TYPES, get_viewer_plugins

logger = utils.set_logger(utils.get_module_name(__file__))
config = Config()

local_path = get_set_local_dir()

class DAQ_Viewer(ParameterManager, ControlModule):
    """ Main PyMoDAQ class to drive detectors

    Qt object and generic UI to drive actuators.

    Attributes
    ----------

    See Also
    --------
    :class:`ControlModule`, :class:`ParameterManager`
    """

    custom_sig = Signal(ThreadCommand)  # particular case where DAQ_Viewer  is used for a custom module

    grab_done_signal = Signal(OrderedDict)
    # OrderedDict(name=self._title,x_axis=None,y_axis=None,z_axis=None,data0D=None,data1D=None,data2D=None)

    update_settings_signal = Signal(edict)
    overshoot_signal = Signal(bool)
    status_signal = Signal(str)

    params = daq_viewer_params

    def __init__(self, parent, dock_settings=None, dock_viewer=None, title="Testing"):

        # TODO
        # check the use case of controller_ID if None remove it

        self.logger = utils.set_logger(f'{logger.name}.{title}')
        self.logger.info(f'Initializing DAQ_Viewer: {title}')

        QObject.__init__(self)
        ParameterManager.__init__(self)
        ControlModule.__init__(self)

        if isinstance(parent, DockArea):
            self.dockarea = parent
        else:
            self.dockarea = None

        self.parent = parent
        if parent is not None:
            self.ui = DAQ_Viewer_UI(parent, title)
        else:
            self.ui = None

        if self.ui is not None:
            self.ui.daq_types = DAQ_TYPES
            self.ui.detectors = [det_dict['name'] for det_dict in DET_TYPES[config('viewer', 'daq_type')]]
            self.ui.add_setting_tree(self.settings_tree)
            self.ui.command_sig.connect(self.process_ui_cmds)

        self.splash_sc = get_splash_sc()

        self._title = title

        self._daq_type = config('viewer', 'daq_type')
        self._detectors = [det_dict['name'] for det_dict in DET_TYPES[self._daq_type]]
        self._detector = self._detectors[0]
        self._viewer_types = []

        self._grabing = False
        self._do_bkg = False
        self._take_bkg = False

        self.h5saver_continuous = H5Saver(save_type='detector')
        self.time_array = None
        self.channel_arrays = []
        self._ini_time_cs = 0  # used for the continuous saving
        self.do_continuous_save = False
        self.is_continuous_initialized = False
        self.file_continuous_save = None
        
        self.grab_done = False
        self.start_grab_time = 0.  # used for the refreshing rate
        self.received_data = 0
        
        self.navigator = None
        self.scanner = None
        self.lcd = None

        self.bkg = None  # buffer to store background
        self.measurement_module = None

        self.save_file_pathname = None  # to store last active path, will be an Path object
        self.ind_continuous_grab = 0

        self.snapshot_pathname = None
        self.current_datas = None
        self.data_to_save_export = None

        self.do_save_data = False

        self.setup_ui(dock_settings, dock_viewer)
        self.set_setting_tree()  # to activate parameters of default Mock detector
        self.show_settings()

        self.grab_done_signal[OrderedDict].connect(self.save_export_data)

        self.daq_type = config('viewer', 'daq_type')

    def process_ui_cmds(self, cmd: utils.ThreadCommand):
        """Process commands sent by actions done in the ui

        Parameters
        ----------
        cmd: ThreadCommand
            Possible values are :
            * init
            * quit
            * grab
            * snap
            * stop
            * show_log
            * detector_changed
            * daq_type_changed
            * save_current
            * save_new
            * do_bkg
            * take_bkg
        """

        if cmd.command == 'init':
            self.init_hardware(cmd.attribute[0])
        elif cmd.command == 'quit':
            self.quit_fun()
        elif cmd.command == 'stop':
            self.stop()
        elif cmd.command == 'show_log':
            self.show_log()
        elif cmd.command == 'navigator':
            self.show_navigator()
        elif cmd.command == 'grab':
            self.grab_data(cmd.attribute, snap_state=False)
        elif cmd.command == 'snap':
            self.grab_data(False, snap_state=True)
        elif cmd.command == 'save_new':
            self.save_new()
        elif cmd.command == 'save_current':
            self.save_current()
        elif cmd.command == 'open':
            self.load_data()
        elif cmd.command == 'detector_changed':
            self.detector = cmd.attribute

        elif cmd.command == 'daq_type_changed':
            self.daq_type = cmd.attribute
        elif cmd.command == 'take_bkg':
            self.take_bkg()
        elif cmd.command == 'do_bkg':
            self._do_bkg = cmd.attribute


    @property
    def viewer_docks(self):
        if self.ui is not None:
            return self.ui.viewer_docks

    @property
    def daq_type(self):
        return self._daq_type

    @daq_type.setter
    def daq_type(self, daq_type):
        """
        """
        self._daq_type = daq_type
        if self.ui is not None:
            self.ui.daq_type = daq_type
        self.settings.child('main_settings', 'DAQ_type').setValue(daq_type)
        self.detectors = [det_dict['name'] for det_dict in DET_TYPES[daq_type]]

    @property
    def detector(self):
        return self._detector

    @detector.setter
    def detector(self, det):
        self._detector = det
        if self.ui is not None:
            self.ui.detector = det
        self.set_setting_tree()

    @property
    def detectors(self):
        return self._detectors

    @detectors.setter
    def detectors(self, detectors):
        self._detectors = detectors
        if self.ui is not None:
            self.ui.detectors = detectors


    @property
    def grab_state(self):
        return self._grabing

    @property
    def do_bkg(self):
        return self._do_bkg


    #######################
    #  INIT QUIT

    def setup_ui(self, dock_settings, dock_viewer):
        if self.ui is not None:
            self.ui.add_setting_tree(self.settings_tree)

            for dock in self.ui.viewer_docks:
                dock.setEnabled(False)

        self.h5saver_continuous.settings_tree.setVisible(False)
        self.h5saver_continuous.settings.sigTreeStateChanged.connect(
            self.parameter_tree_changed)  # trigger action from "do_save"  boolean


    def quit_fun(self):
        """
            | close the current instance of daq_viewer_main emmiting the quit signal.
            | Treat an exception if an error during the detector unitializing has occured.

        """
        # insert anything that needs to be closed before leaving

        if self._initialized_state:  # means  initialized
            self.init_hardware(False)
        self.quit_signal.emit()

        if self.lcd is not None:
            try:
                self.lcd.parent.close()
            except Exception as e:
                self.logger.exception(str(e))
        try:
            for dock in self.ui.viewer_docks:
                dock.close()  # the dock viewers
        except Exception as e:
            self.logger.exception(str(e))
        if hasattr(self, 'nav_dock'):
            self.nav_dock.close()




    ######################################
    #  Methods for running the acquisition

    def init_hardware_ui(self, do_init=True):
        if self.ui is not None:
            self.ui.do_init()

    def init_det(self):
        deprecation_msg(f'The function *init_det* is deprecated, use init_hardware_ui')
        self.init_hardware_ui(True)

    def ini_det_fun(self):
        deprecation_msg(f'The function *ini_det_fun* is deprecated, use init_hardware')
        self.init_hardware(True)

    def init_hardware(self, do_init=True):
        """
            | If Init detector button checked, init the detector and connect the data detector, the data detector temp, the status and the update_settings signals to their corresponding function.
            | Once done start the detector linked thread.
            |
            | Else send the "close" thread command.

            See Also
            --------
            set_enabled_grab_buttons, daq_utils.ThreadCommand, DAQ_Detector
        """
        if not do_init:
            try:
                self.command_hardware.emit(ThreadCommand(command="close"))
                if self.ui is not None:
                    self.ui.detector_init = False
            except Exception as e:
                self.logger.exception(str(e))
        else:            
            try:
                hardware = DAQ_Detector(self._title, self.settings, self.detector)
                self._hardware_thread = QThread()
                hardware.moveToThread(self._hardware_thread)

                self.command_hardware[ThreadCommand].connect(hardware.queue_command)
                hardware.data_detector_sig[list].connect(self.show_data)
                hardware.data_detector_temp_sig[list].connect(self.show_temp_data)
                hardware.status_sig[ThreadCommand].connect(self.thread_status)
                self.update_settings_signal[edict].connect(hardware.update_settings)

                self._hardware_thread.hardware = hardware
                self._hardware_thread.start()
                self.command_hardware.emit(ThreadCommand("ini_detector", attribute=[
                    self.settings.child('detector_settings').saveState(), self.controller]))

                for dock in self.ui.viewer_docks:
                    dock.setEnabled(True)

            except Exception as e:
                self.logger.exception(str(e))
                self.set_enabled_grab_buttons(enable=False)

    def snap(self):
        if self.ui is not None:
            self.ui.do_snap()

    def grab(self):
        if self.ui is not None:
            self.ui.do_grab()

    def snapshot(self, pathname=None, dosave=False, send_to_tcpip=False):
        """
            Do one single grab and save the data in pathname.

            =============== =========== =================================================
            **Parameters**    **Type**    **Description**
            *pathname*        string      the pathname to the location os the saved file
            =============== =========== =================================================

            See Also
            --------
            grab, update_status
        """
        try:
            self.do_save_data = dosave
            if pathname is None:
                raise (Exception("filepathanme has not been defined in snapshot"))
            self.save_file_pathname = pathname

            self.grab_data(grab_state=False, send_to_tcpip=send_to_tcpip, snap_state=True)
        except Exception as e:
            self.logger.exception(str(e))

    def grab_data(self, grab_state=False, send_to_tcpip=False, snap_state=False):
        """
        """
        self._grabing = grab_state
        self._send_to_tcpip = send_to_tcpip
        self.grab_done = False

        if self.ui is not None:
            self.ui.data_ready = False

        self.start_grab_time = time.perf_counter()
        if snap_state:
            self.update_status(f'{self._title}: Snap')
            self.command_hardware.emit(
                ThreadCommand("single", [self.settings.child('main_settings', 'Naverage').value()]))
        else:
            if not grab_state:
                self.update_status(f'{self._title}: Stop Grab')
                self.command_hardware.emit(ThreadCommand("stop_grab", ))
            else:
                self.thread_status(ThreadCommand("update_channels", ))
                self.update_status(f'{self._title}: Continuous Grab')
                self.command_hardware.emit(
                    ThreadCommand("grab", [self.settings.child('main_settings', 'Naverage').value()]))

    def take_bkg(self):
        """
            Save a new file if bkg check button is on.

            See Also
            --------
            save_new
        """
        self._take_bkg = True
        self.snap()

    def stop(self):
        self.update_status(f'{self._title}: Stop Grab')
        self.command_hardware.emit(ThreadCommand("stop_all", ))

    @Slot()
    def raise_timeout(self):
        """
            Print the "timeout occured" error message in the status bar via the update_status method.

            See Also
            --------
            update_status
        """
        self.update_status("Timeout occured", log_type="log")


    ############ LOADING SAVING
    ###########################
    ###### LOADING ##########

    def load_data(self):
        """Opens a H5 file in the H5Browser module
        """
        browse_data()


    ####### SAVING########

    def set_continuous_save(self):
        """
            Set a continous save file using the base path located file with
            a header-name containing date as a string.

            See Also
            --------
            daq_utils.set_current_scan_path
        """
        if self.h5saver_continuous.settings.child(('do_save')).value():
            self.do_continuous_save = True
            self.is_continuous_initialized = False
            self.h5saver_continuous.settings.child(('base_name')).setValue('Data')
            self.h5saver_continuous.settings.child(('N_saved')).show()
            self.h5saver_continuous.settings.child(('N_saved')).setValue(0)
            self.h5saver_continuous.init_file(update_h5=True)

            settings_str = ioxml.parameter_to_xml_string(self.settings)
            settings_str = b'<All_settings>' + settings_str
            if hasattr(self.ui.viewers[0], 'roi_manager'):
                settings_str += ioxml.parameter_to_xml_string(self.ui.viewers[0].roi_manager.settings)
            settings_str += ioxml.parameter_to_xml_string(self.h5saver_continuous.settings) + b'</All_settings>'
            self.scan_continuous_group = self.h5saver_continuous.add_scan_group("Continuous Saving")
            self.continuous_group = self.h5saver_continuous.add_det_group(self.scan_continuous_group,
                                                                          "Continuous saving", settings_str)
            self.h5saver_continuous.h5_file.flush()
        else:
            self.do_continuous_save = False
            self.h5saver_continuous.settings.child(('N_saved')).hide()

            try:
                self.h5saver_continuous.close()
            except Exception as e:
                self.logger.exception(str(e))

    def do_save_continuous(self, datas):
        """
        method used to perform continuous saving of data, for instance for logging. Will save datas as a function of
        time in a h5 file set when *continuous_saving* parameter as been set.

        Parameters
        ----------
        datas:  list of OrderedDict as exported by detector plugins

        """
        try:
            # init the enlargeable arrays
            if not self.is_continuous_initialized:
                self.channel_arrays = OrderedDict([])
                self._ini_time_cs = time.perf_counter()
                self.time_array = self.h5saver_continuous.add_navigation_axis(np.array([0.0, ]),
                                                                              self.scan_continuous_group, 'x_axis',
                                                                              enlargeable=True,
                                                                              title='Time axis',
                                                                              metadata=dict(nav_index=0,
                                                                                            label='Time axis',
                                                                                            units='second'))

                data_dims = ['data0D', 'data1D']
                if self.h5saver_continuous.settings.child('save_2D').value():
                    data_dims.extend(['data2D', 'dataND'])

                if self.bkg is not None and self._do_bkg:
                    bkg_container = OrderedDict([])
                    self.process_data(self.bkg, bkg_container)

                for data_dim in data_dims:
                    if data_dim in datas.keys() and len(datas[data_dim]) != 0:
                        if not self.h5saver_continuous.is_node_in_group(self.continuous_group, data_dim):
                            self.channel_arrays[data_dim] = OrderedDict([])

                            data_group = self.h5saver_continuous.add_data_group(self.continuous_group, data_dim)
                            for ind_channel, channel in enumerate(datas[data_dim]):  # list of OrderedDict

                                channel_group = self.h5saver_continuous.add_CH_group(data_group, title=channel)
                                self.channel_arrays[data_dim]['parent'] = channel_group
                                if self.bkg is not None and self._do_bkg:
                                    if channel in bkg_container[data_dim]:
                                        datas[data_dim][channel]['bkg'] = bkg_container[data_dim][channel]['data']
                                datas[data_dim][channel]['data'] =\
                                    utils.ensure_ndarray(datas[data_dim][channel]['data'])
                                self.channel_arrays[data_dim][channel] = \
                                    self.h5saver_continuous.add_data(channel_group, datas[data_dim][channel],
                                                                     scan_type='scan1D', enlargeable=True)
                self.is_continuous_initialized = True

            dt = np.array([time.perf_counter() - self._ini_time_cs])
            self.time_array.append(dt)

            data_dims = ['data0D', 'data1D']
            if self.h5saver_continuous.settings.child('save_2D').value():
                data_dims.extend(['data2D', 'dataND'])

            for data_dim in data_dims:
                if data_dim in datas.keys() and len(datas[data_dim]) != 0:
                    for ind_channel, channel in enumerate(datas[data_dim]):
                        if isinstance(datas[data_dim][channel]['data'], float) or isinstance(
                                datas[data_dim][channel]['data'], int):
                            datas[data_dim][channel]['data'] = np.array([datas[data_dim][channel]['data']])
                        self.channel_arrays[data_dim][channel].append(datas[data_dim][channel]['data'])

            self.h5saver_continuous.h5_file.flush()
            self.h5saver_continuous.settings.child('N_saved').setValue(
                self.h5saver_continuous.settings.child('N_saved').value() + 1)

        except Exception as e:
            self.logger.exception(str(e))

    def save_current(self):
        """


            See Also
            --------
            gutils.select_file, save_export_data
        """
        self.do_save_data = True
        self.save_file_pathname = select_file(start_path=self.save_file_pathname, save=True,
                                                                                  ext='h5')  # see daq_utils
        self.save_export_data(self.data_to_save_export)

    def save_new(self):
        """
            Do a new save from the select_file obtained pathname into a h5 file structure.

            See Also
            --------
            gutils.select_file, snapshot
        """
        self.do_save_data = True
        self.save_file_pathname = select_file(start_path=self.save_file_pathname, save=True,
                                                                                  ext='h5')  # see daq_utils
        self.snapshot(pathname=self.save_file_pathname, dosave=True)

    def save_datas(self, path=None, datas=None):
        """
            Save procedure of .h5 file data.
            Course the data array and with :
            * **0D data** : store corresponding datas in a h5 file group (a node of the h5 tree)
            * **1D data** : store corresponding datas in a h5 file group (a node of the h5 tree) with a special array for x_axis values
            * **2D data** : store corresponding datas in a h5 file group (a node of the h5 tree) with a special array for x_axis and y_axis values.

            =============== ============= ========================================
            **Parameters**   **Type**     **Description**
            *path*           string        the path name of the file to be saved.
            *datas*          dictionnary   the raw datas to save.
            =============== ============= ========================================
        """
        if path is not None:
            path = Path(path)
        h5saver = H5Saver(save_type='detector')
        h5saver.init_file(update_h5=True, custom_naming=False, addhoc_file_path=path)

        settings_str = b'<All_settings>' + ioxml.parameter_to_xml_string(self.settings)
        if hasattr(self.ui.viewers[0], 'roi_manager'):
            settings_str += ioxml.parameter_to_xml_string(self.ui.viewers[0].roi_manager.settings)
        settings_str += ioxml.parameter_to_xml_string(h5saver.settings)
        settings_str += b'</All_settings>'

        det_group = h5saver.add_det_group(h5saver.raw_group, "Data", settings_str)
        if 'external_h5' in datas:
            try:
                external_group = h5saver.add_group('external_data', 'external_h5', det_group)
                if not datas['external_h5'].isopen:
                    h5saver = H5Saver()
                    h5saver.init_file(addhoc_file_path=datas['external_h5'].filename)
                    h5_file = h5saver.h5_file
                else:
                    h5_file = datas['external_h5']
                h5_file.copy_children(h5_file.get_node('/'), external_group, recursive=True)
                h5_file.flush()
                h5_file.close()

            except Exception as e:
                self.logger.exception(str(e))
        try:
            self.channel_arrays = OrderedDict([])
            data_dims = ['data1D']  # we don't recrod 0D data in this mode (only in continuous)
            if h5saver.settings.child(('save_2D')).value():
                data_dims.extend(['data2D', 'dataND'])

            if self.bkg is not None and self._do_bkg:
                bkg_container = OrderedDict([])
                self.process_data(self.bkg, bkg_container)

            for data_dim in data_dims:
                if datas[data_dim] is not None:
                    if data_dim in datas.keys() and len(datas[data_dim]) != 0:
                        if not h5saver.is_node_in_group(det_group, data_dim):
                            self.channel_arrays[data_dim] = OrderedDict([])

                            data_group = h5saver.add_data_group(det_group, data_dim)
                            for ind_channel, channel in enumerate(datas[data_dim]):  # list of OrderedDict

                                channel_group = h5saver.add_CH_group(data_group, title=channel)

                                self.channel_arrays[data_dim]['parent'] = channel_group
                                if self.bkg is not None and self._do_bkg:
                                    if channel in bkg_container[data_dim]:
                                        datas[data_dim][channel]['bkg'] = bkg_container[data_dim][channel]['data']
                                self.channel_arrays[data_dim][channel] = h5saver.add_data(channel_group,
                                                                                          datas[data_dim][channel],
                                                                                          scan_type='',
                                                                                          enlargeable=False)

                                if data_dim == 'data2D' and 'Data2D' in self._viewer_types:
                                    ind_viewer = self._viewer_types.index('Data2D')
                                    string = pymodaq.daq_utils.gui_utils.utils.widget_to_png_to_bytes(self.ui.viewers[ind_viewer].parent)
                                    self.channel_arrays[data_dim][channel].attrs['pixmap2D'] = string
        except Exception as e:
            self.logger.exception(str(e))

        try:
            (root, filename) = os.path.split(str(path))
            filename, ext = os.path.splitext(filename)
            image_path = os.path.join(root, filename + '.png')
            self.dockarea.parent().grab().save(image_path)
        except Exception as e:
            self.logger.exception(str(e))

        h5saver.close_file()

    @Slot(OrderedDict)
    def save_export_data(self, datas):
        """
            Store in data_to_save_export buffer the data to be saved and do save at self.snapshot_pathname.

            ============== ============= ======================
            **Parameters**   **Type**     **Description**
            *datas*         dictionnary  the data to be saved
            ============== ============= ======================

            See Also
            --------
            save_datas
        """

        if self.do_save_data:
            self.save_datas(self.save_file_pathname, datas)
            self.do_save_data = False

    ######################
    #  ### DATAMANAGEMENT

    @Slot(OrderedDict)
    def get_data_from_viewer(self, datas):
        """
            Emit the grab done signal with datas as an attribute.

            =============== ===================== ===================
            **Parameters**    **Type**             **Description**
            *datas*           ordered dictionnary  the datas to show
            =============== ===================== ===================
        """
        # datas=OrderedDict(name=self._title,data0D=None,data1D=None,data2D=None)
        if self.data_to_save_export is not None:  # means that somehow datas are not initialized so no further procsessing
            self.received_data += 1
            for key in datas:
                if not (key == 'name' or key == 'acq_time_s'):
                    if datas[key] is not None:
                        if self.data_to_save_export[key] is None:
                            self.data_to_save_export[key] = OrderedDict([])
                        for k in datas[key]:
                            if datas[key][k]['source'] != 'raw':
                                name = f'{self._title}_{datas["name"]}_{k}'
                                self.data_to_save_export[key][name] = utils.DataToExport(**datas[key][k])
                                # if name not in self.data_to_save_export[key]:
                                #
                                # self.data_to_save_export[key][name].update(datas[key][k])

            if self.received_data == len(self.ui.viewers):
                if self.do_continuous_save:
                    self.do_save_continuous(self.data_to_save_export)

                self.grab_done = True
                self.grab_done_signal.emit(self.data_to_save_export)

    def set_datas_to_viewers(self, datas, temp=False):
        for ind, data in enumerate(datas):
            self.ui.viewers[ind].title = data['name']
            if data['name'] != '':
                self.ui.viewer_docks[ind].setTitle(self._title + ' ' + data['name'])
            if data['dim'].lower() != 'datand':
                self.set_xy_axis(data, ind)

            if data['dim'] == 'Data0D':
                if 'labels' in data.keys():
                    self.ui.viewers[ind].labels = data['labels']
                if temp:
                    self.ui.viewers[ind].show_data_temp(data['data'])
                else:
                    self.ui.viewers[ind].show_data(data['data'])

            elif data['dim'] == 'Data1D':
                if 'labels' in data.keys():
                    self.ui.viewers[ind].labels = data['labels']
                if temp:
                    self.ui.viewers[ind].show_data_temp(data['data'])
                else:
                    self.ui.viewers[ind].show_data(data['data'])

            elif data['dim'] == 'Data2D':
                if temp:
                    self.ui.viewers[ind].show_data_temp(data)
                else:
                    self.ui.viewers[ind].show_data(data)

            else:
                if 'nav_axes' in data.keys():
                    nav_axes = data['nav_axes']
                else:
                    nav_axes = None

                kwargs = dict()
                if 'nav_x_axis' in data.keys():
                    kwargs['nav_x_axis'] = data['nav_x_axis']
                if 'nav_y_axis' in data.keys():
                    kwargs['nav_y_axis'] = data['nav_y_axis']
                if 'x_axis' in data.keys():
                    kwargs['x_axis'] = data['x_axis']
                if 'y_axis' in data.keys():
                    kwargs['y_axis'] = data['y_axis']

                if isinstance(data['data'], list):
                    dat = data['data'][0]
                else:
                    dat = data['data']

                if temp:
                    self.ui.viewers[ind].show_data_temp(dat, nav_axes=nav_axes, **kwargs)
                else:
                    self.ui.viewers[ind].show_data(dat, nav_axes=nav_axes, **kwargs)

    def init_show_data(self, datas):
        self.process_overshoot(datas)
        self._viewer_types = [data['dim'] for data in datas]
        if self.ui is not None:
            self.ui.update_viewer(self._viewer_types)

    def process_data(self, datas, container):

        data0D = OrderedDict([])
        data1D = OrderedDict([])
        data2D = OrderedDict([])
        dataND = OrderedDict([])

        for ind_data, data in enumerate(datas):
            if 'external_h5' in data.keys():
                container['external_h5'] = data.pop('external_h5')
            data_tmp = copy.deepcopy(data)
            data_dim = data_tmp['dim']
            if data_dim.lower() != 'datand':
                self.set_xy_axis(data_tmp, ind_data)
            data_arrays = data_tmp.pop('data')

            name = data_tmp.pop('name')
            for ind_sub_data, dat in enumerate(data_arrays):
                if 'labels' in data_tmp:
                    data_tmp.pop('labels')
                subdata_tmp = utils.DataToExport(name=self._title, data=dat, **data_tmp)
                sub_name = f'{self._title}_{name}_CH{ind_sub_data:03}'
                if data_dim.lower() == 'data0d':
                    subdata_tmp['data'] = subdata_tmp['data'][0]
                    data0D[sub_name] = subdata_tmp
                elif data_dim.lower() == 'data1d':
                    if 'x_axis' not in subdata_tmp:
                        Nx = len(dat)
                        x_axis = utils.Axis(data=np.linspace(0, Nx - 1, Nx))
                        subdata_tmp['x_axis'] = x_axis
                    data1D[sub_name] = subdata_tmp
                elif data_dim.lower() == 'data2d':
                    if 'x_axis' not in subdata_tmp:
                        Nx = dat.shape[1]
                        x_axis = utils.Axis(data=np.linspace(0, Nx - 1, Nx))
                        subdata_tmp['x_axis'] = x_axis
                    if 'y_axis' not in subdata_tmp:
                        Ny = dat.shape[0]
                        y_axis = utils.Axis(data=np.linspace(0, Ny - 1, Ny))
                        subdata_tmp['y_axis'] = y_axis
                    data2D[sub_name] = subdata_tmp
                elif data_dim.lower() == 'datand':
                    dataND[sub_name] = subdata_tmp

        container['data0D'] = data0D
        container['data1D'] = data1D
        container['data2D'] = data2D
        container['dataND'] = dataND

    @Slot(list)
    def show_data(self, datas: List[utils.DataFromPlugins]):
        """

        """
        try:
            if self.settings.child('main_settings', 'tcpip', 'tcp_connected').value() and self._send_to_tcpip:
                self.command_tcpip.emit(ThreadCommand('data_ready', datas))
            if self.ui is not None:
                self.ui.data_ready = True
            self.init_show_data(datas)

            if self.settings.child('main_settings', 'live_averaging').value():
                self.settings.child('main_settings', 'N_live_averaging').setValue(self.ind_continuous_grab)
                # #self.ui.current_Naverage.setValue(self.ind_continuous_grab)
                self.ind_continuous_grab += 1
                if self.ind_continuous_grab > 1:
                    try:
                        for ind, dic in enumerate(datas):
                            dic['data'] = [((self.ind_continuous_grab - 1) * self.current_datas[ind]['data'][
                                ind_channel] + dic['data'][ind_channel]) / self.ind_continuous_grab for ind_channel in
                                range(len(dic['data']))]
                    except Exception as e:
                        self.logger.exception(str(e))

            # store raw data for further processing
            Ndatas = len(datas)
            acq_time = datetime.datetime.now().timestamp()
            name = self._title
            self.data_to_save_export = OrderedDict(Ndatas=Ndatas, acq_time_s=acq_time, name=name,
                                                   control_module='DAQ_Viewer')

            self.process_data(datas, self.data_to_save_export)

            if self._take_bkg:
                self.bkg = copy.deepcopy(datas)
            # process bkg if needed
            if self._do_bkg and self.bkg is not None:
                try:
                    for ind_channels, channels in enumerate(datas):
                        for ind_channel, channel in enumerate(channels['data']):
                            datas[ind_channels]['data'][ind_channel] -= self.bkg[ind_channels]['data'][ind_channel]
                except Exception as e:
                    self.logger.exception(str(e))

            if self._grabing:  # if live
                refresh = time.perf_counter() - self.start_grab_time > self.settings.child('main_settings',
                                                                                           'refresh_time').value() /\
                          1000
                if refresh:
                    self.start_grab_time = time.perf_counter()
            else:
                refresh = True  # if single
            if self.settings.child('main_settings', 'show_data').value() and refresh:
                self.received_data = 0  # so that data send back from viewers can be properly counted
                self.set_datas_to_viewers(datas)
            else:
                if self.do_continuous_save:
                    self.do_save_continuous(self.data_to_save_export)

                self.grab_done = True
                self.grab_done_signal.emit(self.data_to_save_export)

            self.current_datas = datas

        except Exception as e:
            self.logger.exception(str(e))

    @Slot(list)
    def show_temp_data(self, datas):
        """
            | Show the given datas in the different pannels but do not send processed datas signal.

            =============== ====================== ========================
            **Parameters**    **Type**               **Description**
            datas             list  of OrderedDict   the datas to be showed.
            =============== ====================== ========================

        """
        self.init_show_data(datas)
        self.set_datas_to_viewers(datas, temp=True)

    @property
    def viewers(self):
        if self.ui is not None:
            return self.ui.viewers



    #####################
    ##### PROCESS CHANGES
    #####################

    def log_messages(self, txt):
        self.status_signal.emit(txt)
        self.logger.info(txt)

    def update_status(self, txt, log=True):
        """
            | Show the given txt message in the status bar with
            | Emit a log signal if log_type parameter is defined.

            =============== =========== =====================================
            **Parameters**    **Type**   **Description**
            *txt*             string     the message to show
            *log_type*        string     the type of  the log signal to emit
            =============== =========== =====================================
        """
        if self.ui is not None:
            self.ui.display_status(txt)
        self.status_signal.emit(txt)
        if log:
            self.logger.info(txt)

    def value_changed(self, param):
        path = putils.get_param_path(param)

        if param.name() == 'DAQ_type':
            self.h5saver_continuous.settings.child('do_save').setValue(False)
            self.settings.child('main_settings', 'axes').show(param.value() == 'DAQ2D')

        elif param.name() == 'show_averaging':
            self.settings.child('main_settings', 'live_averaging').setValue(False)
            self.update_settings_signal.emit(edict(path=path, param=param, change='value'))

        elif param.name() == 'live_averaging':
            self.settings.child('main_settings', 'show_averaging').setValue(False)
            if param.value():
                self.settings.child('main_settings', 'N_live_averaging').show()
                self.ind_continuous_grab = 0
                self.settings.child('main_settings', 'N_live_averaging').setValue(0)
            else:
                self.settings.child('main_settings', 'N_live_averaging').hide()
        elif param.name() in putils.iter_children(self.settings.child('main_settings', 'axes'), []):
            if self.daq_type == "DAQ2D":
                if param.name() == 'use_calib':
                    if param.value() != 'None':
                        params = ioxml.XML_file_to_parameter(
                            os.path.join(local_path, 'camera_calibrations', param.value() + '.xml'))
                        param_obj = Parameter.create(name='calib', type='group', children=params)
                        self.settings.child('main_settings', 'axes').restoreState(
                            param_obj.child(('axes')).saveState(), addChildren=False, removeChildren=False)
                        self.settings.child('main_settings', 'axes').show()
                else:
                    for viewer in self.ui.viewers:
                        viewer.set_scaling_axes(self.get_scaling_options())
        elif param.name() in putils.iter_children(self.settings.child('detector_settings', 'ROIselect'),
                                                  []) and 'ROIselect' in param.parent().name():  # to be sure
            # a param named 'y0' for instance will not collide with the y0 from the ROI
            if self.daq_type == "DAQ2D":
                try:
                    self.ui.viewers[0].ROI_select_signal.disconnect(self.update_ROI)
                except Exception as e:
                    self.logger.exception(str(e))
                if self.settings.child('detector_settings', 'ROIselect', 'use_ROI').value():
                    if not self.ui.viewers[0].is_action_checked('ROIselect'):
                        self.ui.viewers[0].get_action('ROIselect').trigger()
                        QtWidgets.QApplication.processEvents()
                self.ui.viewers[0].ROIselect.setPos(
                    self.settings.child('detector_settings', 'ROIselect', 'x0').value(),
                    self.settings.child('detector_settings', 'ROIselect', 'y0').value())
                self.ui.viewers[0].ROIselect.setSize(
                    [self.settings.child('detector_settings', 'ROIselect', 'width').value(),
                     self.settings.child('detector_settings', 'ROIselect', 'height').value()])
                self.ui.viewers[0].ROI_select_signal.connect(self.update_ROI)

        elif param.name() == 'continuous_saving_opt':
            self.h5saver_continuous.settings_tree.setVisible(param.value())

        elif param.name() == 'do_save':
            self.set_continuous_save()

        elif param.name() == 'wait_time':
            self.command_hardware.emit(ThreadCommand('update_wait_time', [param.value()]))

        elif param.name() == 'connect_server':
            if param.value():
                self.connect_tcp_ip()
            else:
                self.command_tcpip.emit(ThreadCommand('quit', ))

        elif param.name() == 'ip_address' or param.name == 'port':
            self.command_tcpip.emit(
                ThreadCommand('update_connection', dict(ipaddress=self.settings.child('main_settings', 'tcpip',
                                                                                      'ip_address').value(),
                                                        port=self.settings.child('main_settings', 'tcpip',
                                                                                 'port').value())))

        if path is not None:
            if 'main_settings' not in path:
                self.update_settings_signal.emit(edict(path=path, param=param, change='value'))

                if self.settings.child('main_settings', 'tcpip', 'tcp_connected').value():
                    self.command_tcpip.emit(ThreadCommand('send_info', dict(path=path, param=param)))

    def param_deleted(self, param):
        if param.name() not in putils.iter_children(self.settings.child('main_settings'), []):
            self.update_settings_signal.emit(edict(path=['detector_settings'], param=param, change='parent'))

    def set_setting_tree(self):
        """
            Set the local setting tree instance cleaning the current one and populate it with
            standard options corresponding to the pymodaq type viewer (0D, 1D or 2D).

            See Also
            --------
            update_status
        """

        try:
            if len(self.settings.child('detector_settings').children()) > 0:
                for child in self.settings.child('detector_settings').children()[1:]:
                    # leave just the ROIselect group
                    child.remove()
            det_params, _class = get_viewer_plugins(self.daq_type, self.detector)
            self.settings.child('detector_settings').addChildren(det_params.children())
        except Exception as e:
            self.logger.exception(str(e))

    def process_overshoot(self, datas):
        if self.settings.child('main_settings', 'overshoot', 'stop_overshoot').value():
            for channels in datas:
                for channel in channels['data']:
                    if any(channel >= self.settings.child('main_settings', 'overshoot', 'overshoot_value').value()):
                        self.overshoot_signal.emit(True)


    def get_scaling_options(self):
        """
            Return the initialized dictionnary containing the scaling options.


            Returns
            -------
            dictionnary
                scaling options dictionnary.

        """
        scaling_options = utils.ScalingOptions(
            scaled_xaxis=utils.ScaledAxis(label=self.settings.child('main_settings', 'axes', 'xaxis', 'xlabel').value(),
                                          units=self.settings.child('main_settings', 'axes', 'xaxis', 'xunits').value(),
                                          offset=self.settings.child('main_settings', 'axes', 'xaxis',
                                                                     'xoffset').value(),
                                          scaling=self.settings.child('main_settings', 'axes', 'xaxis',
                                                                      'xscaling').value()),
            scaled_yaxis=utils.ScaledAxis(label=self.settings.child('main_settings', 'axes', 'yaxis', 'ylabel').value(),
                                          units=self.settings.child('main_settings', 'axes', 'yaxis', 'yunits').value(),
                                          offset=self.settings.child('main_settings', 'axes', 'yaxis',
                                                                     'yoffset').value(),
                                          scaling=self.settings.child('main_settings', 'axes', 'yaxis',
                                                                      'yscaling').value()))
        return scaling_options

    def set_xy_axis(self, data, ind_viewer):
        if 'x_axis' in data.keys():
            self.ui.viewers[ind_viewer].x_axis = data['x_axis']
            if self.settings.child('main_settings', 'tcpip', 'tcp_connected').value():
                self.command_tcpip.emit(ThreadCommand('x_axis', [data['x_axis']]))

        if 'y_axis' in data.keys():
            self.ui.viewers[ind_viewer].y_axis = data['y_axis']
            if self.settings.child('main_settings', 'tcpip', 'tcp_connected').value():
                self.command_tcpip.emit(ThreadCommand('y_axis', [data['y_axis']]))

    def show_settings(self):
        """
            Set the settings tree visible if the corresponding button is checked.
        """
        if self.ui is not None:
            self.ui.show_settings(True)

    @Slot(ThreadCommand)
    def thread_status(self, status):  # general function to get datas/infos from all threads back to the main
        """
            General function to get datas/infos from all threads back to the main.

            In case of :
                * **Update_Status**   *command* : update the status from the given status attribute
                * **ini_detector**    *command* : update the status with "detector initialized" value and init state if attribute not null.
                * **close**           *command* : close the current thread and delete corresponding attribute on cascade.
                * **grab**            *command* : Do nothing
                * **x_axis**          *command* : update x_axis from status attribute and User Interface viewer consequently.
                * **y_axis**          *command* : update y_axis from status attribute and User Interface viewer consequently.
                * **Update_channel**  *command* : update the viewer channels in case of 0D DAQ_type
                * **Update_settings** *command* : Update the "detector setting" node in the settings tree.

            =============== ================ =======================================================
            **Parameters**   **Type**            **Description**

            *status*        ThreadCommand()     instance of ThreadCommand containing two attribute:
                                                    * command   : string
                                                    * attribute: list
            =============== ================ =======================================================

            See Also
            --------
            update_status, set_enabled_grab_buttons, raise_timeout
        """
        if status.command == "Update_Status":
            if len(status.attribute) > 1:
                self.update_status(status.attribute[0], log=status.attribute[1])
            else:
                self.update_status(status.attribute[0])

        elif status.command == "ini_detector":
            self.update_status("detector initialized: " + str(status.attribute[0]['initialized']))
            if self.ui is not None:
                self.ui.detector_init = status.attribute[0]['initialized']
            if status.attribute[0]['initialized']:
                self.controller = status.attribute[0]['controller']
                self._initialized_state = True
            else:
                self._initialized_state = False

            self.init_signal.emit(self._initialized_state)

        elif status.command == "close":
            try:
                self.update_status(status.attribute[0])
                self._hardware_thread.exit()
                self._hardware_thread.wait()
                finished = self._hardware_thread.isFinished()
                if finished:
                    delattr(self, 'detector_thread')
                else:
                    self.update_status('thread is locked?!', 'log')
            except Exception as e:
                self.logger.exception(str(e))

            self._initialized_state = False
            self.init_signal.emit(self._initialized_state)

        elif status.command == "grab":
            pass

        elif status.command == "x_axis":
            try:
                x_axis = status.attribute[0]
                if isinstance(x_axis, list):
                    if len(x_axis) == len(self.ui.viewers):
                        for ind, viewer in enumerate(self.ui.viewers):
                            viewer.x_axis = x_axis[ind]
                    x_axis = x_axis[0]
                else:
                    for viewer in self.ui.viewers:
                        viewer.x_axis = x_axis

                if self.settings.child('main_settings', 'tcpip', 'tcp_connected').value():
                    self.command_tcpip.emit(ThreadCommand('x_axis', [x_axis]))

            except Exception as e:
                self.logger.exception(str(e))

        elif status.command == "y_axis":
            try:
                y_axis = status.attribute[0]
                if isinstance(y_axis, list):
                    if len(y_axis) == len(self.ui.viewers):
                        for ind, viewer in enumerate(self.ui.viewers):
                            viewer.y_axis = y_axis[ind]
                    y_axis = y_axis[0]
                else:
                    for viewer in self.ui.viewers:
                        viewer.y_axis = y_axis

                if self.settings.child('main_settings', 'tcpip', 'tcp_connected').value():
                    self.command_tcpip.emit(ThreadCommand('y_axis', [y_axis]))

            except Exception as e:
                self.logger.exception(str(e))

        elif status.command == "update_channels":
            pass
            # if self.DAQ_type=='DAQ0D':
            #    for viewer in self.ui.viewers:
            #        viewer.update_channels()

        elif status.command == 'update_main_settings':
            # this is a way for the plugins to update main settings of the ui (solely values, limits and options)
            try:
                if status.attribute[2] == 'value':
                    self.settings.child('main_settings', *status.attribute[0]).setValue(status.attribute[1])
                elif status.attribute[2] == 'limits':
                    self.settings.child('main_settings', *status.attribute[0]).setLimits(status.attribute[1])
                elif status.attribute[2] == 'options':
                    self.settings.child('main_settings', *status.attribute[0]).setOpts(**status.attribute[1])
            except Exception as e:
                self.logger.exception(str(e))

        elif status.command == 'update_settings':
            # using this the settings shown in the UI for the plugin reflects the real plugin settings
            try:
                self.settings.sigTreeStateChanged.disconnect(
                    self.parameter_tree_changed)  # any changes on the detcetor settings will update accordingly the gui
            except Exception as e:
                self.logger.exception(str(e))
            try:
                if status.attribute[2] == 'value':
                    self.settings.child('detector_settings', *status.attribute[0]).setValue(status.attribute[1])
                elif status.attribute[2] == 'limits':
                    self.settings.child('detector_settings', *status.attribute[0]).setLimits(status.attribute[1])
                elif status.attribute[2] == 'options':
                    self.settings.child('detector_settings', *status.attribute[0]).setOpts(**status.attribute[1])
                elif status.attribute[2] == 'childAdded':
                    child = Parameter.create(name='tmp')
                    child.restoreState(status.attribute[1][0])
                    self.settings.child('detector_settings', *status.attribute[0]).addChild(status.attribute[1][0])

            except Exception as e:
                self.logger.exception(str(e))
            self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

        elif status.command == 'raise_timeout':
            self.raise_timeout()

        elif status.command == 'show_splash':
            self.ui.settings_tree.setEnabled(False)
            self.splash_sc.show()
            self.splash_sc.raise_()
            self.splash_sc.showMessage(status.attribute[0], color=Qt.white)

        elif status.command == 'close_splash':
            self.splash_sc.close()
            self.ui.settings_tree.setEnabled(True)

        elif status.command == 'init_lcd':
            if self.lcd is not None:
                try:
                    self.lcd.parent.close()
                except Exception as e:
                    self.logger.exception(str(e))
            # lcd module
            lcd = QtWidgets.QWidget()
            self.lcd = LCD(lcd, **status.attribute[0])
            lcd.setVisible(True)
            QtWidgets.QApplication.processEvents()

        elif status.command == 'lcd':
            self.lcd.setvalues(status.attribute[0])

        elif status.command == 'show_navigator':
            show = True
            if len(status.attribute) != 0:
                show = status.attribute[0]
            self.show_navigator(show)
            QtWidgets.QApplication.processEvents()

        elif status.command == 'show_scanner':
            show = True
            if len(status.attribute) != 0:
                show = status.attribute[0]
            self.show_scanner(show)
            QtWidgets.QApplication.processEvents()

        elif status.command == 'stop':
            self.stop()

        self.custom_sig.emit(status)  # to be used if needed in custom application connected to this module

    def update_com(self):
        self.command_hardware.emit(ThreadCommand('update_com', []))

    @Slot(pymodaq.daq_utils.scanner.ScanParameters)
    def update_from_scanner(self, scan_parameters):
        self.command_hardware.emit(ThreadCommand('update_scanner', [scan_parameters]))

    def show_ROI(self):
        if self.DAQ_type == "DAQ2D":
            self.settings.child('detector_settings', 'ROIselect').setOpts(
                visible=self.ui.viewers[0].is_action_checked('ROIselect'))
            pos = self.ui.viewers[0].ROIselect.pos()
            size = self.ui.viewers[0].ROIselect.size()
            self.update_ROI(QRectF(pos[0], pos[1], size[0], size[1]))

    @Slot(QRectF)
    def update_ROI(self, rect=QRectF(0, 0, 1, 1)):
        if self.DAQ_type == "DAQ2D":
            self.settings.child('detector_settings', 'ROIselect', 'x0').setValue(int(rect.x()))
            self.settings.child('detector_settings', 'ROIselect', 'y0').setValue(int(rect.y()))
            self.settings.child('detector_settings', 'ROIselect', 'width').setValue(max([1, int(rect.width())]))
            self.settings.child('detector_settings', 'ROIselect', 'height').setValue(max([1, int(rect.height())]))

    ######################
    ### EXTERNAL actions

    def send_to_nav(self):
        datas = dict()
        keys = list(self.data_to_save_export['data2D'].keys())
        datas['x_axis'] = self.data_to_save_export['data2D'][keys[0]]['x_axis']
        datas['y_axis'] = self.data_to_save_export['data2D'][keys[0]]['y_axis']
        datas['names'] = keys
        datas['data'] = []
        for k in self.data_to_save_export['data2D']:
            datas['data'].append(self.data_to_save_export['data2D'][k]['data'].T)
        png = self.ui.viewers[0].parent.grab().toImage()
        png = png.scaled(100, 100, QtCore.Qt.KeepAspectRatio)
        buffer = QtCore.QBuffer()
        buffer.open(QtCore.QIODevice.WriteOnly)
        png.save(buffer, "png")
        datas['pixmap2D'] = buffer.data().data()

        self.navigator.show_image(datas)

    def show_scanner(self, show=True):
        if self.scanner is None:
            items = OrderedDict([])
            if self.navigator is not None:
                items['Navigator'] = dict(viewers=[self.navigator.viewer], names=["Navigator"])
            viewers_title = [view.title for view in self.ui.viewers if view.viewer_type == 'Data2D']
            if len(viewers_title) > 0:
                items[self._title] = dict(viewers=[view for view in self.ui.viewers if view.viewer_type == 'Data2D'],
                                         names=viewers_title)

            self.scanner = Scanner(items, scan_type='Scan2D')
            self.scanner.settings_tree.setMinimumHeight(300)
            self.scanner.settings_tree.setMinimumWidth(300)
            # self.scanner.settings.child('scan_options', 'scan_type').setValue('Scan2D')
            # self.scanner.settings.child('scan_options', 'scan2D_settings', 'scan2D_selection').setValue('FromROI')

            # self.navigator.sett_layout.insertWidget(0, self.scanner.settings_tree)
            self.ui.settings_layout.addWidget(self.scanner.settings_tree)

            QtWidgets.QApplication.processEvents()
            self.scanner.settings.child('scan_options', 'scan_type').setValue('Scan2D')
            # self.scanner.settings.child('scan_options', 'scan_type').hide()
            self.scanner.settings.child('scan_options', 'scan2D_settings', 'scan2D_type').setValue('Linear')
            # self.scanner.settings.child('scan_options', 'scan2D_settings', 'scan2D_type').hide()
            self.scanner.scan_params_signal[pymodaq.daq_utils.scanner.ScanParameters].connect(self.update_from_scanner)
            QtWidgets.QApplication.processEvents()
            self.scanner.set_scan()

        self.scanner.settings_tree.setVisible(show)

    def show_navigator(self, show=True):
        if self.navigator is None:
            self.nav_dock = Dock('Navigator')
            self.widgnav = QtWidgets.QWidget()
            self.navigator = Navigator(self.widgnav)
            self.nav_dock.addWidget(self.widgnav)
            self.dockarea.addDock(self.nav_dock)
            self.nav_dock.float()
            self.navigator.settings.child('settings', 'Load h5').hide()
            self.navigator.loadaction.setVisible(False)
            self.navigator.sig_double_clicked.connect(self.move_at_navigator)
            self.ui.navigator_pb.setVisible(True)

            if self.scanner is not None:
                items = self.scanner.viewers_items
                if 'Navigator' not in items:
                    items['Navigator'] = dict(viewers=[self.navigator.viewer], names=["Navigator"])
                    self.scanner.viewers_items = items

        self.widgnav.setVisible(show)

    @Slot(float, float)
    def move_at_navigator(self, posx, posy):
        self.command_hardware.emit(ThreadCommand("move_at_navigator", [posx, posy]))

    ###########################
    #  TCPIP stuff

    def connect_tcp_ip(self):
        if self.settings.child('main_settings', 'tcpip', 'connect_server').value():
            self._tcpclient_thread = QThread()

            tcpclient = TCPClient(self.settings.child('main_settings', 'tcpip', 'ip_address').value(),
                                  self.settings.child('main_settings', 'tcpip', 'port').value(),
                                  self.settings.child(('detector_settings')))
            tcpclient.moveToThread(self._tcpclient_thread)
            self._tcpclient_thread.tcpclient = tcpclient
            tcpclient.cmd_signal.connect(self.process_tcpip_cmds)

            self.command_tcpip[ThreadCommand].connect(tcpclient.queue_command)

            self._tcpclient_thread.start()
            tcpclient.init_connection(extra_commands=[ThreadCommand('get_axis', )])

    @Slot(ThreadCommand)
    def process_tcpip_cmds(self, status):
        if 'Send Data' in status.command:
            self.snapshot('', send_to_tcpip=True)
        elif status.command == 'connected':
            self.settings.child('main_settings', 'tcpip', 'tcp_connected').setValue(True)

        elif status.command == 'disconnected':
            self.settings.child('main_settings', 'tcpip', 'tcp_connected').setValue(False)

        elif status.command == 'Update_Status':
            self.thread_status(status)

        elif status.command == 'set_info':
            param_dict = ioxml.XML_string_to_parameter(status.attribute[1])[0]
            param_tmp = Parameter.create(**param_dict)
            param = self.settings.child('detector_settings', *status.attribute[0][1:])

            param.restoreState(param_tmp.saveState())

        elif status.command == 'get_axis':
            self.command_hardware.emit(
                ThreadCommand('get_axis', ))  # tells the plugin to emit its axes so that the server will receive them


class DAQ_Detector(QObject):
    """
        ========================= ==========================
        **Attributes**              **Type**
        *status_sig*                instance of pyqt Signal
        *data_detector_sig*         instance of pyqt Signal
        *data_detector_temp_sig*    instance of pyqt Signal

        *waiting_for_data*          boolean
        *controller*                ???
        *detector_name*             string
        *detector*                  ???
        *controller_adress*         ???
        *grab_state*                boolean
        *single_grab*               boolean
        *x_axis*                    1D numpy array
        *y_axis*                    1D numpy array
        *datas*                     dictionnary
        *ind_average*               int
        *Naverage*                  int
        *average_done*              boolean
        *hardware_averaging*        boolean
        *show_averaging*            boolean
        *wait_time*                 int
        *daq_type*                  string
        ========================= ==========================
    """
    status_sig = Signal(ThreadCommand)
    data_detector_sig = Signal(list)
    data_detector_temp_sig = Signal(list)

    def __init__(self, title, settings_parameter, detector_name):
        super().__init__()
        self.waiting_for_data = False
        self.controller = None
        self.logger = utils.set_logger(f'{logger.name}.{title}.detector')
        self.detector_name = detector_name
        self.detector = None
        self.controller_adress = None
        self.grab_state = False
        self.single_grab = False
        self.datas = None
        self.ind_average = 0
        self.Naverage = None
        self.average_done = False
        self.hardware_averaging = False
        self.show_averaging = False
        self.wait_time = settings_parameter.child('main_settings', 'wait_time').value()
        self.daq_type = settings_parameter.child('main_settings', 'DAQ_type').value()

    @Slot(edict)
    def update_settings(self, settings_parameter_dict):
        """
            | Set attribute values in case of "main_settings" path with corresponding parameter values.
            | Recursively call the method on detector class attribute else.

            ======================== ============== ======================================
            **Parameters**             **Type**      **Description**
            settings_parameter_dict    dictionnary   the (pathname,parameter) dictionnary
            ======================== ============== ======================================

            See Also
            --------
            update_settings
        """

        path = settings_parameter_dict['path']
        param = settings_parameter_dict['param']
        if path[0] == 'main_settings':
            if hasattr(self, path[-1]):
                setattr(self, path[-1], param.value())

        elif path[0] == 'detector_settings':
            self.detector.update_settings(settings_parameter_dict)

    @Slot(ThreadCommand)
    def queue_command(self, command: ThreadCommand):
        """
            Treat the given command parameter from his name :
              * **ini_detector** : Send the corresponding Thread command via a status signal.
              * **close**        : Send the corresponding Thread command via a status signal.
              * **grab**         : Call the local grab method with command(s) attribute.
              * **single**       : Call the local single method with command(s) attribute.
              * **stop_grab**    : Send the correpsonding Thread command via a status signal.

            =============== ================= ============================
            **Parameters**    *Type*           **Description**
            *command*         ThreadCommand()  The command to be treated
            =============== ================= ============================

            See Also
            --------
            grab, single, daq_utils.ThreadCommand
        """
        if command.command == "ini_detector":
            status = self.ini_detector(*command.attribute)
            self.status_sig.emit(ThreadCommand(command.command, [status, 'log']))

        elif command.command == "close":
            status = self.close()
            self.status_sig.emit(ThreadCommand(command.command, [status, 'log']))

        elif command.command == "grab":
            self.single_grab = False
            self.grab_state = True
            self.grab_data(*command.attribute)

        elif command.command == "single":
            self.single_grab = True
            self.grab_state = True
            self.single(*command.attribute)

        elif command.command == "stop_grab":
            self.grab_state = False
            # self.status_sig.emit(ThreadCommand("Update_Status", ['Stoping grab']))

        elif command.command == "stop_all":
            self.grab_state = False
            self.detector.stop()
            QtWidgets.QApplication.processEvents()

        elif command.command == 'update_scanner':
            self.detector.update_scanner(command.attribute[0])

        elif command.command == 'move_at_navigator':
            self.detector.move_at_navigator(*command.attribute)

        elif command.command == 'update_com':
            self.detector.update_com()

        elif command.command == 'update_wait_time':
            self.wait_time = command.attribute[0]

        elif command.command == 'get_axis':
            self.detector.get_axis()

        else:  # custom commands for particular plugins (see spectrometer module 'get_spectro_wl' for instance)
            if hasattr(self.detector, command.command):
                cmd = getattr(self.detector, command.command)
                cmd(*command.attribute)

    def ini_detector(self, params_state=None, controller=None):
        """
            Init the detector from params_state parameter and DAQ_type class attribute :
                * in **0D** profile : update the local status and send the "x_axis" Thread command via a status signal
                * in **1D** profile : update the local status and send the "x_axis" Thread command via a status signal
                * in **2D** profile : update the local status and send the "x_axis" and the "y_axis" Thread command via a status signal

            =============== =========== ==========================================
            **Parameters**    **Type**    **Description**
            *params_state*     ???         the parameter's state of initialization
            =============== =========== ==========================================

            See Also
            --------
            ini_detector, daq_utils.ThreadCommand
        """
        try:
            # status="Not initialized"
            status = edict(initialized=False, info="", x_axis=None, y_axis=None)
            det_params, _class = get_viewer_plugins(self.daq_type, self.detector_name)
            self.detector = _class(self, params_state)
            self.detector.data_grabed_signal.connect(self.data_ready)
            self.detector.data_grabed_signal_temp.connect(self.emit_temp_data)
            status.update(self.detector.ini_detector(controller))

            if status['x_axis'] is not None:
                x_axis = status['x_axis']
                self.status_sig.emit(ThreadCommand("x_axis", [x_axis]))
            if status['y_axis'] is not None:
                y_axis = status['y_axis']
                self.status_sig.emit(ThreadCommand("y_axis", [y_axis]))

            self.hardware_averaging = _class.hardware_averaging  # to check if averaging can be done directly by the hardware or done here software wise

            return status
        except Exception as e:
            self.logger.exception(str(e))
            return status

    @Slot(list)
    def emit_temp_data(self, datas):
        self.data_detector_temp_sig.emit(datas)

    @Slot(list)
    def data_ready(self, datas):
        """
            | Update the local datas attribute from the given datas parameter if the averaging has to be done software wise.
            |
            | Else emit the data detector signals with datas parameter as an attribute.

            =============== ===================== =========================
            **Parameters**    **Type**             **Description**
            *datas*           list                the datas to be emitted.
            =============== ===================== =========================

            See Also
            --------
            daq_utils.ThreadCommand
        """

        # datas validation check for backcompatibility with plugins not exporting new DataFromPlugins list of objects

        for dat in datas:
            if not isinstance(dat, utils.DataFromPlugins):
                if 'type' in dat:
                    dat['dim'] = dat['type']
                    dat['type'] = 'raw'

        if not self.hardware_averaging:  # to execute if the averaging has to be done software wise
            self.ind_average += 1
            if self.ind_average == 1:
                self.datas = datas
            else:
                try:
                    for indpannel, dic in enumerate(datas):
                        self.datas[indpannel]['data'] = \
                            [((self.ind_average - 1) * self.datas[indpannel]['data'][ind] + datas[indpannel]['data'][
                                ind]) / self.ind_average for ind in range(len(datas[indpannel]['data']))]

                    if self.show_averaging:
                        self.emit_temp_data(self.datas)

                except Exception as e:
                    self.logger.exception(str(e))

            if self.ind_average == self.Naverage:
                self.average_done = True
                self.data_detector_sig.emit(self.datas)
                self.ind_average = 0
        else:
            self.data_detector_sig.emit(datas)
        self.waiting_for_data = False
        if not self.grab_state:
            # self.status_sig.emit(["Update_Status","Grabing braked"])
            self.detector.stop()

    def single(self, Naverage=1, args_as_dict={}):
        """
            Call the grab method with Naverage parameter as an attribute.

            =============== =========== ==================
            **Parameters**    **Type**    **Description**
            *Naverage*        int
            *savepath*           str        eventual savepath
            =============== =========== ==================

            See Also
            --------
            daq_utils.ThreadCommand, grab
        """
        try:
            self.grab_data(Naverage, live=False, **args_as_dict)

        except Exception as e:
            self.logger.exception(str(e))

    def grab_data(self, Naverage=1, live=True, **kwargs):
        """
            | Update status with 'Start Grabing' Update_status sub command of the Thread command.
            | Process events and grab naverage is needed.

            =============== =========== ==================
            **Parameters**    **Type**    **Description**
            *Naverage*        int
            =============== =========== ==================

            See Also
            --------
            daq_utils.ThreadCommand, grab
        """
        try:
            self.ind_average = 0
            self.Naverage = Naverage
            if Naverage > 1:
                self.average_done = False
            # self.status_sig.emit(ThreadCommand("Update_Status", [f'Start Grabing']))
            self.waiting_for_data = False

            # for live mode:two possibilities: either snap one data and regrab softwarewise (while True) or if
            # self.detector.live_mode_available is True all data is continuously emited from the plugin
            if self.detector.live_mode_available:
                kwargs['wait_time'] = self.wait_time
            else:
                kwargs['wait_time'] = 0
            while True:
                try:
                    if not self.waiting_for_data:
                        self.waiting_for_data = True
                        self.detector.grab_data(Naverage, live=live, **kwargs)
                    QtWidgets.QApplication.processEvents()
                    if self.single_grab:
                        if self.hardware_averaging:
                            break
                        else:
                            if self.average_done:
                                break
                    else:
                        QThread.msleep(self.wait_time) #if in live mode apply a waiting time after acquisition
                    if not self.grab_state:
                        break
                    if self.detector.live_mode_available:
                        break
                except Exception as e:
                    self.logger.exception(str(e))

        except Exception as e:
            self.logger.exception(str(e))

    def close(self):
        """
            close the current instance of DAQ_Detector.
        """
        try:
            status = self.detector.close()
        except Exception as e:
            self.logger.exception(str(e))
            status = str(e)
        return status


def main(init_qt=True):
    if init_qt: # used for the test suite
        app = QtWidgets.QApplication(sys.argv)
        if config('style', 'darkstyle'):
            import qdarkstyle
            app.setStyleSheet(qdarkstyle.load_stylesheet(qdarkstyle.DarkPalette))

    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Viewer')

    viewer = DAQ_Viewer(area, title="Testing")

    win.show()

    if init_qt:
        sys.exit(app.exec_())
    return viewer, win


if __name__ == '__main__':

    main()

# -*- coding: utf-8 -*-
"""
Created on Wed Jan 10 16:54:14 2018

@author: Weber Sébastien
"""
from __future__ import annotations
from importlib import import_module

from collections import OrderedDict
import copy

import os
from pathlib import Path
from random import randint
import sys
from typing import List, Tuple, Union, Optional
import time

from easydict import EasyDict as edict
import numpy as np
from qtpy import QtWidgets
from qtpy.QtCore import Qt, QObject, Slot, QThread, Signal


from pymodaq_data.data import DataToExport, Axis, DataDistribution
from pymodaq.utils.data import DataFromPlugins

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq.control_modules.utils import ParameterControlModule

from pymodaq_gui.utils.file_io import select_file
from pymodaq_gui.utils.widgets.lcd import LCD

from pymodaq_utils.config import Config, get_set_local_dir
from pymodaq_gui.h5modules.browsing import browse_data
from pymodaq_gui.h5modules.saving import H5Saver
from pymodaq.utils.h5modules import module_saving
from pymodaq_data.h5modules.backends import Node
from pymodaq_utils.utils import ThreadCommand

from pymodaq_gui.parameter import ioxml, Parameter
from pymodaq_gui.parameter import utils as putils
from pymodaq.control_modules.viewer_utility_classes import params as daq_viewer_params
from pymodaq_utils import utils
from pymodaq_utils.warnings import deprecation_msg
from pymodaq_gui.utils import DockArea, Dock
from pymodaq_gui.utils.utils import mkQApp

from pymodaq.utils.gui_utils import get_splash_sc
from pymodaq.control_modules.daq_viewer_ui import DAQ_Viewer_UI
from pymodaq.control_modules.utils import DET_TYPES, get_viewer_plugins, DAQTypesEnum, DetectorError
from pymodaq_gui.plotting.data_viewers.viewer import ViewerBase
from pymodaq_gui.plotting.data_viewers import ViewersEnum
from pymodaq_utils.enums import enum_checker
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base

from pymodaq.utils.leco.pymodaq_listener import ViewerActorListener, LECOClientCommands

logger = set_logger(get_module_name(__file__))
config = Config()

local_path = get_set_local_dir()


class DAQ_Viewer(ParameterControlModule):
    """ Main PyMoDAQ class to drive detectors

    Qt object and generic UI to drive actuators. The class is giving you full functionality to select (daq_detector),
    initialize detectors (init_hardware), grab or snap data (grab_data) and save them (save_new, save_current). If
    a DockArea is given as parent widget, the full User Interface (DAQ_Viewer_UI) is loaded allowing easy control of the
    instrument.

    Attributes
    ----------
    grab_done_signal: Signal[DataToExport]
        Signal emitted when the data from the plugin (and eventually from the data viewers) has been received. To be
        used by connected objects.
    custom_sig: Signal[ThreadCommand]
        use this to propagate info/data coming from the hardware plugin to another object
    overshoot_signal: Signal[bool]
        This signal is emitted when some 0D data from the plugin is higher than the overshoot threshold set in the
        settings

    See Also
    --------
    ControlModule, DAQ_Viewer_UI, ParameterManager

    Notes
    -----
    A particular signal from the 2D DataViewer is directly connected to the plugin: ROI_select_signal. The position and
    size of the corresponding ROI is then directly transferred to a plugin function named `ROISelect` that you have to
    create if one want to receive infos from the ROI
    """
    settings_name = 'daq_viewer_settings'
    custom_sig = Signal(ThreadCommand)  # particular case where DAQ_Viewer is used for a custom module

    grab_done_signal = Signal(DataToExport)

    overshoot_signal = Signal(bool)
    data_saved = Signal()
    grab_status = Signal(bool)

    params = daq_viewer_params

    listener_class = ViewerActorListener

    def __init__(self, parent: DockArea=None, title="Testing",
                 daq_type=config('viewer', 'daq_type'),
                 dock_settings=None, dock_viewer=None,
                 **kwargs):

        self.logger = set_logger(f'{logger.name}.{title}')
        self.logger.info(f'Initializing DAQ_Viewer: {title}')

        super().__init__(**kwargs)

        daq_type = enum_checker(DAQTypesEnum, daq_type)
        self._daq_type: DAQTypesEnum = daq_type

        self._viewer_types: List[ViewersEnum] = []
        self._viewers: List[ViewerBase] = []

        if isinstance(parent, DockArea):
            self.dockarea = parent
        else:
            self.dockarea = None

        self.parent = parent
        if parent is not None:
            self.ui: DAQ_Viewer_UI = DAQ_Viewer_UI(parent, title, daq_type=daq_type,
                                                   dock_settings=dock_settings,
                                                   dock_viewer=dock_viewer)
        else:
            self.ui: Optional[DAQ_Viewer_UI] = None

        if self.ui is not None:
            QtWidgets.QApplication.processEvents()
            self.ui.add_setting_tree(self.settings_tree)
            self.ui.command_sig.connect(self.process_ui_cmds)
            self.viewers = self.ui.viewers
            self._viewer_types = self.ui.viewer_types

        self.splash_sc = get_splash_sc()

        self._title = title

        self.module_and_data_saver: Union[None,
                                          module_saving.DetectorSaver,
                                          module_saving.DetectorEnlargeableSaver,
                                          module_saving.DetectorExtendedSaver] = None
        self._h5saver_continuous: Optional[H5Saver] = None
        self._ind_continuous_grab = 0
        self.setup_continuous_saving()

        self.settings.child('main_settings', 'DAQ_type').setValue(self.daq_type.name)
        self._detectors: List[str] = [det_dict['name'] for det_dict in DET_TYPES[self.daq_type.name]]
        if len(self._detectors) > 0:  # will be 0 if no valid plugins are installed
            self._detector: str = self._detectors[0]
        else:
            raise DetectorError('No detected Detector')
        self.settings.child('main_settings', 'detector_type').setValue(self._detector)

        self._grabing: bool = False
        self._do_bkg: bool = False
        self._take_bkg: bool = False

        self._grab_done: bool = False
        self._start_grab_time: float = 0.  # used for the refreshing rate
        self._received_data: int = 0

        self._lcd: Optional[LCD] = None

        self._bkg: Optional[DataToExport] = None  # buffer to store background

        self._save_file_pathname: Optional[Path] = None  # to store last active path, will be an Path object
        
        self._snapshot_pathname: Optional[Path] = None
        self._data_to_save_export: Optional[DataToExport] = None

        self._do_save_data: bool = False

        self._set_setting_tree()  # to activate parameters of default Mock detector

        self.grab_done_signal.connect(self._save_export_data)
        self.update_plugin_config()

    def __repr__(self):
        return f'{self.__class__.__name__}: {self.title} ({self.daq_type}/{self.detector}'

    def setup_continuous_saving(self):
        """Configure the objects dealing with the continuous saving mode"""
        self.module_and_data_saver = module_saving.DetectorSaver(self)
        self._h5saver_continuous = H5Saver(save_type='detector')
        self._h5saver_continuous.show_settings(False)
        self._h5saver_continuous.settings.child('do_save').sigValueChanged.connect(self._init_continuous_save)
        if self.ui is not None:
            self.ui.add_setting_tree(self._h5saver_continuous.settings_tree)

    def process_ui_cmds(self, cmd: utils.ThreadCommand):
        """Process commands sent by actions done in the ui

        Parameters
        ----------
        cmd: ThreadCommand
            Possible values are:
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
                * viewers_changed
                * show_config
        """

        if cmd.command == 'init':
            self.init_hardware(cmd.attribute[0])
        elif cmd.command == 'quit':
            self.quit_fun()
        elif cmd.command == 'stop':
            self.stop()
        elif cmd.command == 'show_log':
            self.show_log()
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
            if cmd.attribute != '':
                self.detector_changed_from_ui(cmd.attribute)
        elif cmd.command == 'daq_type_changed':
            if cmd.attribute != '':
                self.daq_type_changed_from_ui(cmd.attribute)
        elif cmd.command == 'take_bkg':
            self.take_bkg()
        elif cmd.command == 'do_bkg':
            self.do_bkg = cmd.attribute
        elif cmd.command == 'viewers_changed':
            self._viewer_types: List[ViewersEnum] = cmd.attribute['viewer_types']
            self.viewers = cmd.attribute['viewers']
        elif cmd.command == 'show_config':
            self.config = self.show_config(self.config)
            self.ui.config = self.config

    @property
    def bkg(self) -> DataToExport:
        """Get the background data object"""
        return self._bkg

    @property
    def viewer_docks(self) -> List[Dock]:
        """list of Viewer Docks from the UI"""
        if self.ui is not None:
            return self.ui.viewer_docks

    @property
    def viewers_docks(self) -> List[Dock]:
        """list of Viewer Docks from the UI, for back compatibility"""
        deprecation_msg('viewers_docks is a deprecated property use viewer_docks instead')
        return self.viewer_docks

    @property
    def master(self) -> bool:
        """ Get/Set programmatically the Master/Slave status of a detector"""
        if self.initialized_state:
            return self.settings['detector_settings', 'controller_status'] == 'Master'
        else:
            return True

    @master.setter
    def master(self, is_master: bool):
        if self.initialized_state:
            self.settings.child('detector_settings', 'controller_status').setValue(
                'Master' if is_master else 'Slave')

    def daq_type_changed_from_ui(self, daq_type: DAQTypesEnum):
        """ Apply changes from the selection of a different DAQTypesEnum in the UI

        Parameters
        ----------
        daq_type: DAQTypesEnum
        """
        daq_type = enum_checker(DAQTypesEnum, daq_type)
        self._daq_type = daq_type
        self.settings.child('main_settings', 'DAQ_type').setValue(daq_type.name)
        self.detectors = [det_dict['name'] for det_dict in DET_TYPES[daq_type.name]]
        self.detector = self.detectors[0]

    @property
    def daq_type(self) -> DAQTypesEnum:
        """Get/Set the daq_type as a DAQTypesEnum

        Update the detector property with the list of available detectors of a given daq_type
        """
        return self._daq_type

    @daq_type.setter
    def daq_type(self, daq_type: DAQTypesEnum):
        daq_type = enum_checker(DAQTypesEnum, daq_type)

        self._daq_type = daq_type
        if self.ui is not None:
            self.ui.daq_type = daq_type
        self.settings.child('main_settings', 'DAQ_type').setValue(daq_type.name)
        self.detectors = [det_dict['name'] for det_dict in DET_TYPES[daq_type.name]]
        self.detector = self.detectors[0]

    @property
    def daq_types(self) -> List[str]:
        """List of available DAQ_TYPES as keys of the DAQTypesEnum"""
        return DAQTypesEnum.names()

    def detector_changed_from_ui(self, detector: str):
        self._detector = detector
        self.update_plugin_config()
        self._set_setting_tree()

    @property
    def detector(self) -> str:
        """:obj:`str`: Get/Set the currently selected detector among available detectors"""
        return self._detector

    @detector.setter
    def detector(self, det: str):
        if det not in self.detectors:
            raise ValueError(f'{det} is not a valid Detector: {self.detectors}')
        self._detector = det
        self.update_plugin_config()
        if self.ui is not None:
            self.ui.detector = det
        self._set_setting_tree()

    @property
    def Naverage(self):
        return self.settings['main_settings', 'Naverage']

    @Naverage.setter
    def Naverage(self, ngrab: int):
        if ngrab >= 1:
            self.settings.child('main_settings', 'Naverage').setValue(ngrab)

    def update_plugin_config(self):
        parent_module = utils.find_dict_in_list_from_key_val(DET_TYPES[self.daq_type.name], 'name', self.detector)
        mod = import_module(parent_module['module'].__package__.split('.')[0])
        if hasattr(mod, 'config'):
            self.plugin_config = mod.config

    def detectors_changed_from_ui(self, detectors: List[str]):
        self._detectors = detectors

    @property
    def detectors(self) -> str:
        """:obj:`list` of :obj:`str`: List of available detectors of the current daq_type (DAQTypesEnum)"""
        return self._detectors

    @detectors.setter
    def detectors(self, detectors):
        self._detectors = detectors
        if self.ui is not None:
            self.ui.detectors = detectors

    @property
    def grab_state(self):
        """:obj:`bool`: Get the current grabbing status"""
        return self._grabing

    @property
    def do_bkg(self) -> bool:
        """:obj:`bool`: Get/Set if background subtraction should be done"""
        return self._do_bkg

    @do_bkg.setter
    def do_bkg(self, doit: bool):
        self._do_bkg = doit

    @property
    def viewers(self) -> List[ViewerBase]:
        """:obj:`list`: Get/Set the Viewers (instances of real implementation of ViewerBase class) from the UI"""
        if self.ui is not None:
            return self._viewers

    @viewers.setter
    def viewers(self, viewers: List[ViewerBase]):
        for viewer in self._viewers:
            try:
                viewer.data_to_export_signal.disconnect()
            except:
                pass
        for ind_viewer, viewer in enumerate(viewers):
            viewer.data_to_export_signal.connect(self._get_data_from_viewer)
            #deprecated:
            viewer.ROI_select_signal.connect(
                lambda roi_info: self.command_hardware.emit(ThreadCommand('ROISelect', roi_info)))
            #use that now
            viewer.roi_select_signal.connect(
                lambda roi_info: self.command_hardware.emit(
                    ThreadCommand('roi_select',
                                  dict(roi_info=roi_info, ind_viewer=ind_viewer))))
            viewer.crosshair_dragged.connect(
                lambda crosshair_info: self.command_hardware.emit(
                    ThreadCommand('crosshair',
                                  dict(crosshair_info=crosshair_info, ind_viewer=ind_viewer))))


        self._viewers = viewers

    def quit_fun(self):
        """ Quit the application, closing the hardware and other modules """

        # insert anything that needs to be closed before leaving

        if self._initialized_state:  # means  initialized
            self.init_hardware(False)
        self.quit_signal.emit()

        if self._lcd is not None:
            try:
                self._lcd.parent.close()
            except Exception as e:
                self.logger.exception(str(e))

        try:
            if self.ui is not None:
                self.ui.close()

        except Exception as e:
            self.logger.exception(str(e))

        if __name__ == '__main__':
            self.parent.close()

    #  #####################################
    #  Methods for running the acquisition

    def init_hardware(self, do_init=True):
        """ Init the selected detector

        Parameters
        ----------
        do_init: bool
            If True, create a DAQ_Detector instance and move it into a separated thread, connected its signals/slots
            to the DAQ_Viewer object (self)
            If False, force the instrument to close and kill the Thread (still not done properly in some cases)
        """
        if not do_init:
            try:
                self.command_hardware.emit(ThreadCommand(command="close"))
                QtWidgets.QApplication.processEvents()
                if self.ui is not None:
                    self.ui.detector_init = False

            except Exception as e:
                self.logger.exception(str(e))
        else:            
            try:

                hardware = DAQ_Detector(self._title, self.settings, self.detector)
                self._hardware_thread = QThread()
                if self.config('viewer', 'viewer_in_thread'):
                    hardware.moveToThread(self._hardware_thread)

                self.command_hardware[ThreadCommand].connect(hardware.queue_command)
                hardware.data_detector_sig[DataToExport].connect(self.show_data)
                hardware.data_detector_temp_sig[DataToExport].connect(self.show_temp_data)
                hardware.status_sig[ThreadCommand].connect(self.thread_status)
                self._update_settings_signal[edict].connect(hardware.update_settings)

                self._hardware_thread.hardware = hardware
                if self.config('viewer', 'viewer_in_thread'):
                    self._hardware_thread.start()
                self.command_hardware.emit(ThreadCommand("ini_detector", attribute=[
                    self.settings.child('detector_settings').saveState(), self.controller]))
                if self.ui is not None:
                    for dock in self.ui.viewer_docks:
                        dock.setEnabled(True)

            except Exception as e:
                self.logger.exception(str(e))

    def snap(self):
        """ Launch a single grab """
        self.grab_data(False, snap_state=True)

    def grab(self):
        """ Launch a continuous grab """
        if self.ui is not None:
            self.manage_ui_actions('grab', 'setChecked', not self._grabing)
            self.grab_data(not self._grabing, snap_state=False)

    def snapshot(self, pathname=None, dosave=False, send_to_tcpip=False):
        """Do one single grab (snap) and eventually save the data.

        Parameters
        ----------
        pathname: str or Path object
            The path where to save data
        dosave: bool
            Do save or just grab data
        send_to_tcpip: bool
            If True, send the grabbed data through the TCP/IP pipe
        """
        try:
            self._do_save_data = dosave
            if pathname is None:
                raise (ValueError("filepathanme has not been defined in snapshot"))

            self._save_file_pathname = pathname
            self.grab_data(grab_state=False, send_to_tcpip=send_to_tcpip, snap_state=True)
        except Exception as e:
            self.logger.exception(str(e))

    def grab_data(self, grab_state=False, send_to_tcpip=False, snap_state=False):
        """ Generic method to grab or snap data from the selected (and initialized) detector

        Parameters
        ----------
        grab_state: bool
            Defines the grab status: if True: do live grabbing if False stops the grab
        send_to_tcpip: bool
            If True, send the grabbed data through the TCP/IP pipe
        snap_state: bool
            if True performs a single grab
        """
        self._grabing = grab_state
        self._send_to_tcpip = send_to_tcpip
        self._grab_done = False

        if self.ui is not None:
            self.ui.data_ready = False

        self._start_grab_time = time.perf_counter()
        if snap_state:
            self.update_status(f'{self._title}: Snap')
            self.command_hardware.emit(
                ThreadCommand("single", dict(Naverage=self.settings['main_settings', 'Naverage'])))
        else:
            if not grab_state:
                self.update_status(f'{self._title}: Stop Grab')
                self.command_hardware.emit(ThreadCommand("stop_grab", ))
            else:
                self.thread_status(ThreadCommand("update_channels", ))
                self.update_status(f'{self._title}: Continuous Grab')
                self.command_hardware.emit(
                    ThreadCommand("grab", dict(Naverage=self.settings['main_settings', 'Naverage'])))

    def take_bkg(self):
        """ Do a snap and store data to be used as background into an attribute: `self._bkg`

        The content of the bkg will be saved if data is further saved with do_bkg property set to True
        """
        self._take_bkg = True
        self.grab_data(snap_state=True)

    def stop_grab(self):
        """ Stop the current continuous grabbing and unchecked the stop button of the UI

        See Also
        --------
        :meth:`stop`
        """
        if self.ui is not None:
            self.manage_ui_actions('grab', 'setChecked', False)
        self.stop()

    def stop(self):
        """ Stop the current continuous grabbing """
        self.update_status(f'{self._title}: Stop Grab')
        self.command_hardware.emit(ThreadCommand("stop_all", ))
        self._grabing = False

    @Slot()
    def _raise_timeout(self):
        """  Print the "timeout occurred" error message in the status bar via the update_status method.
        """
        self.update_status("Timeout occured", log_type="log")

    @staticmethod
    def load_data():
        """Opens a H5 file in the H5Browser module

        Convenience static method.
        """
        browse_data()

    def save_current(self):
        """Save current data into a h5file"""
        self._do_save_data = True
        self._save_file_pathname = select_file(start_path=self._save_file_pathname, save=True,
                                                                                  ext='h5')  # see daq_utils
        self._save_export_data(self._data_to_save_export)

    def save_new(self):
        """Snap data and save them into a h5file"""
        self._do_save_data = True
        self._save_file_pathname = select_file(start_path=self._save_file_pathname, save=True,
                                                                                  ext='h5')  # see daq_utils
        self.snapshot(pathname=self._save_file_pathname, dosave=True)

    def _init_continuous_save(self):
        """ Initialize the continuous saving H5Saver object

        Update the module_and_data_saver attribute as :class:`DetectorEnlargeableSaver` object
        """
        if self._h5saver_continuous.settings.child('do_save').value():

            self._h5saver_continuous.settings.child('base_name').setValue('Data')
            self._h5saver_continuous.settings.child('N_saved').show()
            self._h5saver_continuous.settings.child('N_saved').setValue(0)
            self.module_and_data_saver.h5saver = self._h5saver_continuous
            self._h5saver_continuous.init_file(update_h5=True)

            self.module_and_data_saver = module_saving.DetectorEnlargeableSaver(self)
            self.module_and_data_saver.h5saver = self._h5saver_continuous
            self.module_and_data_saver.get_set_node()

            self.grab_done_signal.connect(self.append_data)
        else:
            self._do_continuous_save = False
            self._h5saver_continuous.settings.child('N_saved').hide()
            self.grab_done_signal.disconnect(self.append_data)

            try:
                self._h5saver_continuous.close()
            except Exception as e:
                self.logger.exception(str(e))

    def append_data(self, dte: DataToExport = None, where: Union[Node, str] = None):
        """Appends current DataToExport to a DetectorEnlargeableSaver

        Method to be used when performing continuous saving into a h5file (continuous mode or DAQ_Logger)

        Parameters
        ----------
        dte: DataToExport
            not really used
        where: Node or str
        See Also
        --------
        :class:`DetectorEnlargeableSaver`
        """
        if dte is None:
            dte = self._data_to_save_export
        self._add_data_to_saver(dte, init_step=self._h5saver_continuous.settings['N_saved'] == 0,
                                where=where)
        self._h5saver_continuous.settings.child('N_saved').setValue(self._h5saver_continuous.settings['N_saved'] + 1)

    def insert_data(self, indexes: Tuple[int], where: Union[Node, str] = None,
                    distribution=DataDistribution['uniform']):
        """Insert DataToExport to a DetectorExtendedSaver at specified indexes

        Method to be used when saving into an already initialized array within a h5file (DAQ_Scan for instance)

        Parameters
        ----------
        indexes: tuple(int)
            The indexes within the extended array where to place these data
        where: Node or str
        distribution: DataDistribution enum

        See Also
        --------
        DAQ_Scan, DetectorExtendedSaver
        """
        self._add_data_to_saver(self._data_to_save_export, init_step=np.all(np.array(indexes) == 0), where=where,
                                indexes=indexes, distribution=distribution)

    def _add_data_to_saver(self, dte: DataToExport, init_step=False, where=None, **kwargs):
        """Adds DataToExport data to the current node using the declared module_and_data_saver

        Filters the data to be saved by DataSource as specified in the current H5Saver (see self.module_and_data_saver)

        Parameters
        ----------
        dte: DataToExport
            The data to be saved
        init_step: bool
            If True, means this is the first step of saving (if multisaving), then save background if any and a png image
        kwargs: dict
            Other named parameters to be passed as is to the module_and_data_saver

        See Also
        --------
        DetectorSaver, DetectorEnlargeableSaver, DetectorExtendedSaver

        """
        if dte is not None:
            detector_node = self.module_and_data_saver.get_set_node(where)
            dte = dte if not self.module_and_data_saver.h5saver.settings['save_raw_only'] else \
                dte.get_data_from_source('raw')  # filters depending on the source: raw or calculated

            dte = DataToExport(name=dte.name, data=  # filters depending on the extra argument 'save'
                               [dwa for dwa in dte if ('do_save' not in dwa.extra_attributes) or
                                ('do_save' in dwa.extra_attributes and dwa.do_save)])

            self.module_and_data_saver.add_data(detector_node, dte, **kwargs)

            if init_step:
                if self._do_bkg and self._bkg is not None:
                    self.module_and_data_saver.add_bkg(detector_node, self._bkg)

    def _save_data(self, path=None, dte: DataToExport = None):
        """Private. Practical implementation to save data into a h5file altogether with metadata, axes, background...

        Parameters
        ----------
        path: Path
            where to save the data as returned from browse_file for instance
        dte: DataToExport

        See Also
        --------
        browse_file, _get_data_from_viewers
        """
        if path is not None:
            path = Path(path)
        h5saver = H5Saver(save_type='detector')
        h5saver.init_file(update_h5=True, custom_naming=False, addhoc_file_path=path)
        self.module_and_data_saver = module_saving.DetectorSaver(self)
        self.module_and_data_saver.h5saver = h5saver

        self._add_data_to_saver(dte, init_step=True)

        if self.ui is not None:
            (root, filename) = os.path.split(str(path))
            filename, ext = os.path.splitext(filename)
            image_path = os.path.join(root, filename + '.png')
            self.dockarea.parent().grab().save(image_path)

        h5saver.close_file()
        self.data_saved.emit()

    @Slot(DataToExport)
    def _save_export_data(self, data: DataToExport):
        """Auxiliary method (Slot) to receive all data (raw and processed from rois) and save them

        Parameters
        ----------
        data: DataToExport

        See Also
        --------
        _save_data
        """

        if self._do_save_data:
            self._save_data(self._save_file_pathname, data)
            self._do_save_data = False

    def _get_data_from_viewer(self, data: DataToExport):
        """Get all data emitted by the current viewers

        Each viewer *data_to_export_signal* is connected to this slot. The collected data is stored in another
        DataToExport `self._data_to_save_export` for further processing. All raw data are also stored in this attribute.
        When all viewers have emitted this signal, the collected data are emitted  with the
        `grab_done_signal` signal.

        Parameters
        ---------_
        data: DataToExport
            All data collected from the viewers

        """
        if self._data_to_save_export is not None:  # means that somehow data are not initialized so no further procsessing
            self._received_data += 1
            if len(data) != 0:
                for dat in data:
                    dat.origin = f'{self.title} - {dat.origin}' if dat.origin is not None else f'{self.title}'
                self._data_to_save_export.append(data)

            if self._received_data == len(self.viewers):
                self._grab_done = True
                self.grab_done_signal.emit(self._data_to_save_export)

    @property
    def current_data(self) -> DataToExport:
        """ Get the current data stored internally"""
        return self._data_to_save_export

    @Slot(DataToExport)
    def show_temp_data(self, data: DataToExport):
        """Send data to their dedicated viewers but those will not emit processed data signal

        Slot receiving data from plugins emitted with the `data_grabed_signal_temp`

        Parameters
        ----------
        data: list of DataFromPlugins
        """
        self._init_show_data(data)
        if self.ui is not None:
            self.set_data_to_viewers(data, temp=True)

    @Slot(DataToExport)
    def show_data(self, dte: DataToExport):
        """Send data to their dedicated viewers

        Slot receiving data from plugins emitted with the `data_grabed_signal`
        Process the data as specified in the settings, display them into the dedicated data viewers depending on the
        settings:
            * create a container (OrderedDict `_data_to_save_export`) with info from this DAQ_Viewer (title), a timestamp...
            * call `_process_data`
            * do background subtraction if any
            * check refresh time (if set in the settings) to send or not data to data viewers
            * either send to the data viewers (if refresh time is ok and/or show data option in settings is set)
            * either
                * send grab_done_signal (to the slot _save_export_data ) to save the data

        Parameters
        ----------
        dte: DataToExport

        See Also
        --------
        _init_show_data, _process_data
        """
        try:
            dte = dte.deepcopy()
            if self.settings['main_settings', 'tcpip', 'tcp_connected'] and self._send_to_tcpip:
                self._command_tcpip.emit(ThreadCommand('data_ready', dte))
            if self.settings['main_settings', 'leco', 'leco_connected'] and self._send_to_tcpip:
                self._command_tcpip.emit(ThreadCommand('data_ready', dte))
            if self.ui is not None:
                self.ui.data_ready = True

            if self.settings['main_settings', 'live_averaging']:
                self.settings.child('main_settings', 'N_live_averaging').setValue(self._ind_continuous_grab)
                _current_data = dte.deepcopy()

                self._ind_continuous_grab += 1
                if self._ind_continuous_grab > 1:
                    self._data_to_save_export = \
                        _current_data.average(self._data_to_save_export, self._ind_continuous_grab)
            else:
                for dwa in dte:
                    dwa.origin = self._title
                self._data_to_save_export = DataToExport(self._title, control_module='DAQ_Viewer', data=dte.data)

            if self._take_bkg:
                self._bkg = self._data_to_save_export.deepcopy()
                self._take_bkg = False

            if self._grabing:  # if live
                refresh_time = self.settings['main_settings', 'refresh_time']
                refresh = time.perf_counter() - self._start_grab_time > refresh_time / 1000
                if refresh:
                    self._start_grab_time = time.perf_counter()
            else:
                refresh = True  # if single
            if self.ui is not None and self.settings.child('main_settings', 'show_data').value() and refresh:
                self._received_data = 0  # so that data send back from viewers can be properly counted
                data_to_plot = self._data_to_save_export.get_data_from_attribute('do_plot', True, deepcopy=True)
                data_to_plot.append(self._data_to_save_export.get_data_from_missing_attribute('do_plot', deepcopy=True))
                # process bkg if needed
                if self.do_bkg and self._bkg is not None:
                    data_to_plot -= self._bkg

                self._init_show_data(data_to_plot)
                self.set_data_to_viewers(data_to_plot)
            else:
                self._grab_done = True
                self.grab_done_signal.emit(self._data_to_save_export)

        except Exception as e:
            self.logger.exception(str(e))

    def _init_show_data(self, dte: DataToExport):
        """Processing before showing data

        * process the data to check if they overshoot
        * check the data dimensionality to update the dedicated viewers

        Parameters
        ----------
        dte: DataToExport

        See Also
        --------
        _process_overshoot
        """
        self._process_overshoot(dte)

        self._viewer_types = [ViewersEnum(dwa.dim.name) for dwa in dte if
                              ('do_plot' not in dwa.extra_attributes) or
                              ('do_plot' in dwa.extra_attributes and dwa.do_plot)]
        if self.ui is not None:
            if self.ui.viewer_types != self._viewer_types:
                self.ui.update_viewers(self._viewer_types)

    def set_data_to_viewers(self, dte: DataToExport, temp=False):
        """Process data dimensionality and send appropriate data to their data viewers

        Parameters
        ----------
        dte: DataToExport
        temp: bool
            if True notify the data viewers to display data as temporary (meaning not exporting processed data from roi)

        See Also
        --------
        ViewerBase, Viewer0D, Viewer1D, Viewer2D
        """
        for ind, dwa in enumerate(dte):
            if ('do_plot' not in dwa.extra_attributes) or \
                    ('do_plot' in dwa.extra_attributes and dwa.do_plot):
                self.viewers[ind].title = dwa.name
                self.viewer_docks[ind].setTitle(self._title + ' ' + dwa.name)

                if temp:
                    self.viewers[ind].show_data_temp(dwa)
                else:
                    self.viewers[ind].show_data(dwa)

    def value_changed(self, param: Parameter):
        """ParameterManager subclassed method. Process events from value changed by user in the UI Settings

        Parameters
        ----------
        param: Parameter
            a given parameter whose value has been changed by user
        """
        super().value_changed(param=param)

        path = self.settings.childPath(param)
        if param.name() == 'DAQ_type':
            self._h5saver_continuous.settings.child('do_save').setValue(False)
            self.settings.child('main_settings', 'axes').show(param.value() == 'DAQ2D')

        elif param.name() == 'show_averaging':
            self.settings.child('main_settings', 'live_averaging').setValue(False)
            self._update_settings_signal.emit(edict(path=path, param=param, change='value'))

        elif param.name() == 'live_averaging':
            self.settings.child('main_settings', 'show_averaging').setValue(False)
            if param.value():
                self.settings.child('main_settings', 'N_live_averaging').show()
                self._ind_continuous_grab = 0
                self.settings.child('main_settings', 'N_live_averaging').setValue(0)
            else:
                self.settings.child('main_settings', 'N_live_averaging').hide()
            #self._update_settings_signal.emit(edict(path=path, param=param, change='value'))

        elif param.name() in putils.iter_children(self.settings.child('main_settings', 'axes'), []):
            if self.daq_type.name == "DAQ2D":
                if param.name() == 'use_calib':
                    if param.value() != 'None':
                        params = ioxml.XML_file_to_parameter(
                            os.path.join(local_path, 'camera_calibrations', param.value() + '.xml'))
                        param_obj = Parameter.create(name='calib', type='group', children=params)
                        self.settings.child('main_settings', 'axes').restoreState(
                            param_obj.child('axes').saveState(), addChildren=False, removeChildren=False)
                        self.settings.child('main_settings', 'axes').show()
                else:
                    for viewer in self.viewers:
                        viewer.x_axis, viewer.y_axis = self.get_scaling_options()

        elif param.name() == 'continuous_saving_opt':
            self._h5saver_continuous.show_settings(param.value())

        elif param.name() == 'wait_time':
            self.command_hardware.emit(ThreadCommand('update_wait_time', [param.value()]))

        self._update_settings(param=param)

    def child_added(self, param, data):
        """ Adds a child in the settings attribute

        Parameters
        ----------
        param: Parameter
            the parameter where child will be added
        data: Parameter
            the child parameter
        """
        if param.name() not in putils.iter_children(self.settings.child('main_settings'), []):
            self._update_settings_signal.emit(edict(path=putils.get_param_path(param)[1:], param=data[0],
                                                    change='childAdded'))

    def param_deleted(self, param):
        """ Remove a child from the settings attribute

        Parameters
        ----------
        param: Parameter
            a given parameter whose value has been changed by user
        """
        if param.name() not in putils.iter_children(self.settings.child('main_settings'), []):
            self._update_settings_signal.emit(edict(path=['detector_settings'], param=param, change='parent'))

    def _set_setting_tree(self):
        """Apply the specific settings of the selected detector (plugin)

        Remove previous ones and load on the fly the new ones

        See Also
        --------
        pymodaq.control_modules.utils:get_viewer_plugins
        """

        try:
            if len(self.settings.child('detector_settings').children()) > 0:
                for child in self.settings.child('detector_settings').children():
                    child.remove()

            det_params, _class = get_viewer_plugins(self.daq_type.name, self.detector)
            self.settings.child('detector_settings').addChildren(det_params.children())
            self.settings.child('main_settings', 'module_name').setValue(self._title)
        except Exception as e:
            self.logger.exception(str(e))

    def _process_overshoot(self, dte: DataToExport):
        """Compare data value (0D) to the given overshoot setting
        """
        if self.settings.child('main_settings', 'overshoot', 'stop_overshoot').value():
            for dwa in dte:
                for data_array in dwa.data:
                    if np.any(data_array >= self.settings['main_settings', 'overshoot',
                                                          'overshoot_value']):
                        self.overshoot_signal.emit(True)

    def get_scaling_options(self):
        """Create axes scaling options depending on the ('main_settings', 'axes') settings

        Returns
        -------
        Tuple[Axis]
        """
        scaled_xaxis = Axis(label=self.settings['main_settings', 'axes', 'xaxis', 'xlabel'],
                            units=self.settings['main_settings', 'axes', 'xaxis', 'xunits'],
                            offset=self.settings['main_settings', 'axes', 'xaxis', 'xoffset'],
                            scaling=self.settings['main_settings', 'axes', 'xaxis', 'xscaling'])
        scaled_yaxis = Axis(label=self.settings['main_settings', 'axes', 'yaxis', 'ylabel'],
                            units=self.settings['main_settings', 'axes', 'yaxis', 'yunits'],
                            offset=self.settings['main_settings', 'axes', 'yaxis', 'yoffset'],
                            scaling=self.settings['main_settings', 'axes', 'yaxis', 'yscaling'])
        return scaled_xaxis, scaled_yaxis

    def thread_status(self, status: ThreadCommand):
        """Get back info (using the ThreadCommand object) from the hardware

        And re-emit this ThreadCommand using the custom_sig signal if it should be used in a higher level module

        Commands valid for all control modules are defined in the parent class, here are described only the specific
        ones

        Parameters
        ----------
        status: ThreadCommand
            The info returned from the hardware, the command (str) can be either:
                * ini_detector: update the status with "detector initialized" value and init state if attribute not null.
                * grab : emit grab_status(True)
                * grab_stopped: emit grab_status(False)
                * init_lcd: display a LCD panel
                * lcd: display on the LCD panel, the content of the attribute
                * stop: stop the grab
        """
        super().thread_status(status, 'detector')

        if status.command == "ini_detector":
            self.update_status("detector initialized: " + str(status.attribute['initialized']))
            if self.ui is not None:
                self.ui.detector_init = status.attribute['initialized']
            if status.attribute['initialized']:
                self.controller = status.attribute['controller']
                self._initialized_state = True
            else:
                self._initialized_state = False

            self.init_signal.emit(self._initialized_state)

        elif status.command == "grab":
            self.grab_status.emit(True)

        elif status.command == 'grab_stopped':
            self.grab_status.emit(False)

        elif status.command == 'init_lcd':
            if self._lcd is not None:
                try:
                    self._lcd.parent.close()
                except Exception as e:
                    self.logger.exception(str(e))
            # lcd module
            lcd = QtWidgets.QWidget()
            self._lcd = LCD(lcd, **status.attribute)
            lcd.setVisible(True)
            QtWidgets.QApplication.processEvents()

        elif status.command == 'lcd':
            """status.attribute should be a list of numpy arrays of shape (1,)"""
            self._lcd.setvalues(status.attribute)

        elif status.command == 'stop':
            self.stop_grab()

    def connect_tcp_ip(self):
        super().connect_tcp_ip(params_state=self.settings.child('detector_settings'),
                               client_type="GRABBER")

    @Slot(ThreadCommand)
    def process_tcpip_cmds(self, status: ThreadCommand) -> None:
        """Receive commands from the TCP Server (if connected) and process them

        Parameters
        ----------
        status: ThreadCommand
            Possible commands are:
            * 'Send Data: to trigger a snapshot
            * 'connected': show that connection is ok
            * 'disconnected': show that connection is not OK
            * 'Update_Status': update a status command
            * 'set_info': receive settings from the server side and update them on this side

        See Also
        --------
        connect_tcp_ip, TCPServer

        """
        if super().process_tcpip_cmds(status=status) is None:
            return
        if 'Send Data' in status.command:
            self.snapshot('', send_to_tcpip=True)

        elif status.command == LECOClientCommands.LECO_CONNECTED:
            self.settings.child('main_settings', 'leco', 'leco_connected').setValue(True)

        elif status.command == LECOClientCommands.LECO_DISCONNECTED:
            self.settings.child('main_settings', 'leco', 'leco_connected').setValue(False)

        elif status.command == 'set_info':
            path_in_settings = status.attribute[0]
            param_as_xml = status.attribute[1]
            param_dict = ioxml.XML_string_to_parameter(param_as_xml)[0]
            param_tmp = Parameter.create(**param_dict)
            param = self.settings.child('detector_settings', *path_in_settings[1:])
            param.restoreState(param_tmp.saveState())

        elif status.command == 'get_axis':
            raise DeprecationWarning('Do not use this, the axis are in the data objects')
            self.command_hardware.emit(
                ThreadCommand('get_axis', ))  # tells the plugin to emit its axes so that the server will receive them


class DAQ_Detector(QObject):
    """ Worker class to control the instrument plugin

    Attributes
    ----------
    detector: real instance of the instrument plugin class
    controller: DAQ_Viewer_base
        wrapper object used to control a given instrument in the instrument plugin
    controller_adress: int
        unique integer used to identify a controller shared among multiple instrument plugins

    """
    status_sig = Signal(ThreadCommand)
    data_detector_sig = Signal(DataToExport)
    data_detector_temp_sig = Signal(DataToExport)

    def __init__(self, title, settings_parameter, detector_name):
        super().__init__()
        self.waiting_for_data = False
        self.controller = None
        self.logger = set_logger(f'{logger.name}.{title}.detector')
        self._title = title
        self.detector_name = detector_name
        self.detector: DAQ_Viewer_base = None
        self.controller_adress: int = None
        self.grab_state = False
        self.single_grab = False
        self.datas: DataToExport = None
        self.ind_average = 0
        self.Naverage = 1
        self.average_done = False
        self.hardware_averaging = False
        self.show_averaging = False
        self.wait_time = settings_parameter['main_settings', 'wait_time']
        self.daq_type = DAQTypesEnum[settings_parameter['main_settings', 'DAQ_type']]

    @property
    def title(self):
        return self._title

    def update_settings(self, settings_parameter_dict):
        """ Apply a Parameter serialized as a dict to the instrument plugin class or to self

        Parameters
        ----------
        settings_parameter_dict: dict
            dictionary serializing a Parameter object

        Examples
        --------
        If the parameter is of the form ('detector_settings', 'xxx') then the parameter is sent to the instrument
        plugin class.
        """

        path = settings_parameter_dict['path']
        param = settings_parameter_dict['param']
        if path[0] == 'main_settings':
            if hasattr(self, path[-1]):
                setattr(self, path[-1], param.value())

        elif path[0] == 'detector_settings':
            self.detector.update_settings(settings_parameter_dict)

    def queue_command(self, command: ThreadCommand):
        """Transfer command from the main module to the hardware module

        Parameters
        ----------
        command: ThreadCommand
            The specific (or generic) command (str) to pass to the hardware,  either:
            * ini_detector
            * close
            * grab
            * single
            * stop_grab
            * stop_all
            * update_scanner
            * move_at_navigator
            * update_wait_time
            * get_axis
            * any string that the hardware is able to understand
        """
        if command.command == "ini_detector":
            status = self.ini_detector(*command.attribute)
            self.status_sig.emit(ThreadCommand(command.command, status))

        elif command.command == "close":
            status = self.close()
            self.status_sig.emit(ThreadCommand(command.command, [status, 'log']))

        elif command.command == "grab":
            self.single_grab = False
            self.grab_state = True
            self.grab_data(**command.attribute)

        elif command.command == "single":
            self.single_grab = True
            self.grab_state = True
            self.single(**command.attribute)

        elif command.command == "stop_grab":
            self.grab_state = False
            self.status_sig.emit(ThreadCommand("Update_Status", ['Stoping grab']))

        elif command.command == "stop_all":
            self.grab_state = False
            self.detector.stop()
            QtWidgets.QApplication.processEvents()
            self.status_sig.emit(ThreadCommand("Update_Status", ['Stoping grab']))

        elif command.command == 'update_scanner':
            self.detector.update_scanner(command.attribute[0])

        elif command.command == 'move_at_navigator':
            self.detector.move_at_navigator(*command.attribute)

        elif command.command == 'update_wait_time':
            self.wait_time = command.attribute[0]

        elif command.command == 'get_axis':
            self.detector.get_axis()

        else:  # custom commands for particular plugins
            if hasattr(self.detector, command.command):
                cmd = getattr(self.detector, command.command)
                if isinstance(command.attribute, list):
                    cmd(*command.attribute)
                elif isinstance(command.attribute, dict):
                    cmd(**command.attribute)
                else:
                    cmd(command.attribute)

    def ini_detector(self, params_state=None, controller=None):
        """ Initialize an instrument plugin class and tries to apply preset settings

        When the instrument is initialized from the Dashboard using a Preset, tries to apply the preset
        settings to the instrument instance

        Parameters
        ----------
        params_state: dict
        controller: wrapper
        """
        try:
            # status="Not initialized"
            status = edict(initialized=False, info="", x_axis=None, y_axis=None)
            det_params, class_ = get_viewer_plugins(self.daq_type.name, self.detector_name)
            self.detector: DAQ_Viewer_base = class_(self, params_state)

            try:
                self.detector.dte_signal.connect(self.data_ready)
                self.detector.dte_signal_temp.connect(self.emit_temp_data)
                infos = self.detector.ini_detector(controller)
                status.controller = self.detector.controller

            except Exception as e:
                logger.exception("Hardware couldn't be initialized", exc_info=e)
                infos = str(e), False
                status.controller = None

            if isinstance(infos, edict):
                status.update(infos)
            else:
                status.info = infos[0]
                status.initialized = infos[1]

            self.hardware_averaging = class_.hardware_averaging  # to check if averaging can be done directly by
            # the hardware or done here software wise

            return status
        except Exception as e:
            self.logger.exception(str(e))
            return status

    def emit_temp_data(self, data: DataToExport):
        """ Convenience method to export temporary data using the data_detector_temp_sig Signal

        Parameters
        ----------
        data: DataToExport
        """
        self.data_detector_temp_sig.emit(data)

    def data_ready(self, data: DataToExport):
        """ Process the data received from the instrument plugin class

        Processing here is eventual software averaging if it was not possible in the instrument plugin class

        Parameters
        ----------
        data: DataToExport
        """
        do_averaging = self.Naverage > 1 and not self.hardware_averaging

        if do_averaging:  # to execute if the averaging has to be done software wise
            self.ind_average += 1
            if self.ind_average == 1:
                self.datas = data.deepcopy()
            else:
                self.datas = data.average(self.datas, self.ind_average)

            if self.show_averaging:
                self.emit_temp_data(self.datas)

            if self.ind_average == self.Naverage:
                self.average_done = True
                self.data_detector_sig.emit(self.datas)
                self.ind_average = 0
        else:
            self.average_done = True  # expected to make sure the single_grab stop by itself
            self.data_detector_sig.emit(data)
        self.waiting_for_data = False
        if not self.grab_state:
            self.detector.stop()

    def single(self, Naverage=1, *args, **kwargs):
        """ Convenience function to grab a single set of data

        Parameters
        ----------
        Naverage: int
            The number of data to average before displaying
        kwargs: optional named arguments
        """
        self.grab_data(Naverage, live=False, **kwargs)

    def grab_data(self, Naverage=1, live=True, **kwargs):
        """ General method to grab data from the instrument plugin class

        Will check if the plugin class can do hardware averaging (if NAverage > 1) and and live_mode, otherwise
        do both software wise here

        Parameters
        ----------
        Naverage: int
            The number of data to average
        live: bool
            Try to run the instrument plugin class grabbing in live mode
        kwargs: optional named arguments passed to the grab_data method of the instrument plugin class
        """
        try:
            self.ind_average = 0
            self.Naverage = Naverage
            if Naverage > 1:
                self.average_done = False
            self.waiting_for_data = False

            # for live mode:two possibilities: either snap one data and regrab softwarewise
            # (while True) or if self.detector.live_mode_available is True all data is continuously
            # emitted from the plugin
            if self.detector.live_mode_available:
                kwargs['wait_time'] = self.wait_time
            else:
                kwargs['wait_time'] = 0
            self.status_sig.emit(ThreadCommand('grab'))
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
                        QThread.msleep(self.wait_time)  # if in grab mode apply a waiting time
                        # after acquisition
                    if not self.grab_state:
                        break   # if not in grab mode  breaks the while loop
                    if self.detector.live_mode_available and (not self.hardware_averaging and
                                                              self.average_done):
                        break  # if live can be done in the plugin breaks the while loop except
                        # if average is asked but not done hardware wise
                except Exception as e:
                    self.logger.exception(str(e))
            self.status_sig.emit(ThreadCommand('grab_stopped'))

        except Exception as e:
            self.logger.exception(str(e))

    def close(self):
        """ Call the close method of the instrument plugin class
        """
        if self.detector is not None and self.detector.controller is not None:
            status = self.detector.close()
            return status


def prepare_docks(area, title):
    """ Static method to init docks to be used within a DAQ_Viewer

    Parameters
    ----------
    area
    title

    Returns
    -------

    """
    dock_settings = Dock(title + " settings", size=(150, 250))
    dock_viewer = Dock(title + " viewer", size=(350, 350))
    area.addDock(dock_settings)
    area.addDock(dock_viewer, 'right', dock_settings)
    return dict(dock_settings=dock_settings, dock_viewer=dock_viewer)


def main(init_qt=True, init_det=False):
    """ Method called to start the DAQ_Viewer in standalone mode"""

    if init_qt:  # used for the test suite
        app = mkQApp("PyMoDAQ Viewer")

    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.show()

    title = "Testing"
    viewer = DAQ_Viewer(area, title="Testing", daq_type=config('viewer', 'daq_type'),
                        **prepare_docks(area, title))
    if init_det:
        viewer.init_hardware_ui(init_det)

    if init_qt:
        sys.exit(app.exec_())
    return viewer, win


if __name__ == '__main__':
    main(init_det=False)

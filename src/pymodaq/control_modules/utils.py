# -*- coding: utf-8 -*-
"""
Created the 03/10/2022

@author: Sebastien Weber
"""
from easydict import EasyDict as edict

from qtpy import QtCore
from qtpy.QtCore import Signal, QObject
from pymodaq.utils.gui_utils import CustomApp
from pymodaq.utils.daq_utils import ThreadCommand, get_plugins, find_dict_in_list_from_key_val
from pymodaq.utils.config import Config
from pymodaq.utils.parameter import Parameter
from pymodaq.utils.enums import BaseEnum, enum_checker
from pymodaq.utils.plotting.data_viewers.viewer import ViewersEnum


class DAQTypesEnum(BaseEnum):
    """enum relating a given DAQType and a viewer type
    See Also
    --------
    pymodaq.utils.plotting.data_viewers.viewer.ViewersEnum
    """
    DAQ0D = 'Viewer0D'
    DAQ1D = 'Viewer1D'
    DAQ2D = 'Viewer2D'
    DAQND = 'ViewerND'

    def to_data_type(self):
        return ViewersEnum[self.value].value

    def to_viewer_type(self):
        return self.value

    def to_daq_type(self):
        return self.name

    def increase_dim(self, ndim: int):
        dim = self.get_dim()
        if dim != 'N':
            dim_as_int = int(dim) + ndim
            if dim_as_int > 2:
                dim = 'N'
            else:
                dim = str(dim_as_int)
        else:
            dim = 'N'
        return DAQTypesEnum(f'Viewer{dim}D')

    def get_dim(self):
        return self.value.split('Viewer')[1].split('D')[0]

DAQ_TYPES = DAQTypesEnum

DET_TYPES = {'DAQ0D': get_plugins('daq_0Dviewer'),
             'DAQ1D': get_plugins('daq_1Dviewer'),
             'DAQ2D': get_plugins('daq_2Dviewer'),
             'DAQND': get_plugins('daq_NDviewer'),}


config = Config()


class ViewerError(Exception):
    pass


def get_viewer_plugins(daq_type, det_name):
    parent_module = find_dict_in_list_from_key_val(DET_TYPES[daq_type], 'name', det_name)
    match_name = daq_type.lower()
    match_name = f'{match_name[0:3]}_{match_name[3:].upper()}viewer_'
    obj = getattr(getattr(parent_module['module'], match_name + det_name),
                  f'{match_name[0:7].upper()}{match_name[7:]}{det_name}')
    params = getattr(obj, 'params')
    det_params = Parameter.create(name='Det Settings', type='group', children=params)
    return det_params, obj


class ControlModule(QObject):
    """Abstract Base class common to both DAQ_Move and DAQ_Viewer control modules

    Attributes
    ----------
    init_signal : Signal[bool]
        This signal is emitted when the chosen hardware is correctly initialized
    command_hardware : Signal[ThreadCommand]
        This signal is used to communicate with the instrument plugin within a separate thread
    command_tcpip : Signal[ThreadCommand]
        This signal is used to communicate through the TCP/IP Network
    quit_signal : Signal[]
        This signal is emitted when the user requested to stop the module
    """
    init_signal = Signal(bool)
    command_hardware = Signal(ThreadCommand)
    _command_tcpip = Signal(ThreadCommand)
    quit_signal = Signal()
    _update_settings_signal = Signal(edict)
    status_sig = Signal(str)

    def __init__(self):
        super().__init__()
        self._title = ""

        # the hardware controller instance set after initialization and to be used by other modules if they share the
        # same controller
        self.controller = None
        self._initialized_state = False
        self._send_to_tcpip = False
        self._tcpclient_thread = None
        self._hardware_thread = None
        self.module_and_data_saver = None

    def __repr__(self):
        return f'{self.__class__.__name__}: {self.title}'

    @property
    def module_type(self):
        """str: Get the module type, either DAQ_Move or DAQ_viewer"""
        return type(self).__name__

    @property
    def initialized_state(self):
        """bool: Check if the module is initialized"""
        return self._initialized_state

    @property
    def title(self):
        """str: get the title of the module"""
        return self._title

    def grab(self):
        """Programmatic entry to grab data from detectors or current value from actuator"""
        raise NotImplementedError

    def stop_grab(self):
        """Programmatic entry to stop data grabbing from detectors or current value polling from actuator"""
        raise NotImplementedError

    def quit_fun(self):
        """Programmatic entry to quit the controle module"""
        raise NotImplementedError

    def init_hardware(self, do_init=True):
        """Programmatic entry to initialize/deinitialize the control module

        Parameters
        ----------
        do_init : bool
            if True initialize the selected hardware else deinitialize it

        See Also
        --------
        :meth:`init_hardware_ui`
        """
        raise NotImplementedError

    def init_hardware_ui(self, do_init=True):
        """Programmatic entry to simulate a click on the user interface init button

        Parameters
        ----------
        do_init : bool
            if True initialize the selected hardware else deinitialize it

        Notes
        -----
        This method should be preferred to :meth:`init_hardware`
        """
        raise NotImplementedError

    def show_log(self):
        """Open the log file in the default text editor"""
        import webbrowser
        webbrowser.open(self.logger.parent.handlers[0].baseFilename)

    def update_status(self, txt, log=True):
        """Display a message in the ui status bar and eventually log the message

        Parameters
        ----------
        txt : str
            message to display
        log : bool
            if True, log the message in the logger
        """
        if self.ui is not None:
            self.ui.display_status(txt)
        self.status_sig.emit(txt)
        if log:
            self.logger.info(txt)

    def manage_ui_actions(self, action_name: str, attribute: str, value):
        """Method to manage actions for the UI (if any).

        Will try to apply the given value to the given attribute of the corresponding action

        Parameters
        ----------
        action_name: str
        attribute: method signature or attribute
        value: object
            actual type and value depend on the triggered attribute

        Examples
        --------
        >>>manage_ui_actions('quit', 'setEnabled', False)
        # will disable the quit action (button) on the UI
        """
        if self.ui is not None:
            if self.ui.has_action(action_name):
                action = self.ui.get_action(action_name)
                if hasattr(action, attribute):
                    attr = getattr(action, attribute)
                    if callable(attr):
                        attr(value)
                    else:
                        attr = value


class ControlModuleUI(CustomApp):
    """ Base Class for ControlModules UIs

    Attributes
    ----------
    command_sig: Signal[Threadcommand]
        This signal is emitted whenever some actions done by the user has to be
        applied on the main module. Possible commands are:
        See specific implementation

    See Also
    --------
    :class:`daq_move_ui.DAQ_Move_UI`, :class:`daq_viewer_ui.DAQ_Viewer_UI`
    """
    command_sig = QtCore.Signal(ThreadCommand)

    def __init__(self, parent):
        super().__init__(parent)

    def display_status(self, txt, wait_time=config('general', 'message_status_persistence')):
        if self.statusbar is not None:
            self.statusbar.showMessage(txt, wait_time)

    def do_init(self, do_init=True):
        """Programmatically press the Init button
        API entry
        Parameters
        ----------
        do_init: bool
            will fire the Init button depending on the argument value and the button check state
        """
        raise NotImplementedError

    def send_init(self):
        """Shoudl be implemented to send to the main app the fact that someone pressed init"""
        raise NotImplementedError
# -*- coding: utf-8 -*-
"""
Created the 03/10/2022

@author: Sebastien Weber
"""
from random import randint
from typing import Optional, Type, Union
from easydict import EasyDict as edict

from qtpy.QtCore import Signal, QObject, Qt, Slot, QThread

from pymodaq.control_modules.thread_commands import ThreadStatus
from pymodaq_utils.utils import ThreadCommand, find_dict_in_list_from_key_val
from pymodaq_utils.config import Config
from pymodaq_utils.enums import BaseEnum
from pymodaq_utils.logger import get_base_logger, set_logger, get_module_name

from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq_gui.parameter.utils import ParameterWithPath
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.plotting.data_viewers import ViewersEnum
from pymodaq_gui.h5modules.saving import H5Saver

from pymodaq.utils.tcp_ip.tcp_server_client import TCPClient
from pymodaq.utils.exceptions import DetectorError
from pymodaq.utils.leco.pymodaq_listener import ActorListener, LECOClientCommands, LECOCommands

from pymodaq.utils.daq_utils import get_plugins
from pymodaq.utils.h5modules.module_saving import DetectorSaver, ActuatorSaver
from pymodaq.utils.config import Config as ControlModulesConfig


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
             'DAQND': get_plugins('daq_NDviewer'),
             }

if len(DET_TYPES['DAQ0D']) == 0:
    raise DetectorError('No installed Detector')


config_utils = Config()
config = ControlModulesConfig()
logger = set_logger(get_module_name(__file__))


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
    custom_sig = Signal(ThreadCommand)
    ui = None

    def __init__(self):
        super().__init__()
        self._title = ""
        self.config = config
        # the hardware controller instance set after initialization and to be used by other modules if they share the
        # same controller
        self.controller = None
        self._initialized_state = False
        self._send_to_tcpip = False
        self._tcpclient_thread = None
        self._hardware_thread = None

        self.plugin_config: Optional[Config] = None

        self._h5saver: Optional[H5Saver] = None
        self._module_and_data_saver = None

    def __repr__(self):
        return f'{self.__class__.__name__}: {self.title}'

    def create_new_file(self, new_file: bool):
        if new_file:
            self.close_file()

        self.module_and_data_saver.h5saver = self.h5saver
        return True

    @property
    def h5saver(self):
        if self._h5saver is None:
            self._h5saver = H5Saver(backend=config_utils('general', 'hdf5_backend'))
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
    def module_and_data_saver(self, mod: Union[DetectorSaver, ActuatorSaver]):
        self._module_and_data_saver = mod
        self._module_and_data_saver.h5saver = self.h5saver


    def custom_command(self, command: str, **kwargs):
        self.command_hardware.emit(ThreadCommand(command, kwargs))

    def thread_status(self, status: ThreadCommand, control_module_type='detector'):
        """Get back info (using the ThreadCommand object) from the hardware

        And re-emit this ThreadCommand using the custom_sig signal if it should be used in a higher level module


        Parameters
        ----------
        status: ThreadCommand
            The info returned from the hardware, the command (str) can be either:
                * Update_Status: display messages and log info (deprecated)
                * update_status: display info on the UI status bar
                * close: close the current thread and delete corresponding attribute on cascade.
                * update_settings: Update the "detector setting" node in the settings tree.
                * update_main_settings: update the "main setting" node in the settings tree
                * raise_timeout:
                * show_splash: Display the splash screen with attribute as message
                * close_splash
                * show_config: display the plugin configuration
        """

        if status.command == "Update_Status":
            # legacy
            if len(status.attribute) > 1:
                self.update_status(status.attribute[0], log=status.attribute[1])
            else:
                self.update_status(status.attribute[0])

        elif status.command == ThreadStatus.UPDATE_STATUS:
            self.update_status(status.attribute)

        elif status.command == ThreadStatus.CLOSE:
            try:
                self.update_status(status.attribute[0])
                self._hardware_thread.quit()
                terminated = self._hardware_thread.wait(5000)
                if not terminated:
                    self._hardware_thread.terminate()
                    self._hardware_thread.wait()
                    self.update_status('thread is locked?!', 'log')
            except Exception as e:
                logger.exception(f'Wrong call to the "close" command: \n{str(e)}')

            self._initialized_state = False
            self.init_signal.emit(self._initialized_state)

        elif status.command == ThreadStatus.UPDATE_MAIN_SETTINGS:
            # this is a way for the plugins to update main settings of the ui (solely values, limits and options)
            try:
                if status.attribute[2] == 'value':
                    self.settings.child('main_settings', *status.attribute[0]).setValue(status.attribute[1])
                elif status.attribute[2] == 'limits':
                    self.settings.child('main_settings', *status.attribute[0]).setLimits(status.attribute[1])
                elif status.attribute[2] == 'options':
                    self.settings.child('main_settings', *status.attribute[0]).setOpts(**status.attribute[1])
            except Exception as e:
                logger.exception(f'Wrong call to the "update_main_settings" command: \n{str(e)}')

        elif status.command == ThreadStatus.UPDATE_SETTINGS:
            # using this the settings shown in the UI for the plugin reflects the real plugin settings
            try:
                self.settings.sigTreeStateChanged.disconnect(
                    self.parameter_tree_changed)  # any changes on the detcetor settings will update accordingly the gui
            except Exception as e:
                logger.exception(str(e))
            try:
                if status.attribute[2] == 'value':
                    self.settings.child(f'{control_module_type}_settings',
                                        *status.attribute[0]).setValue(status.attribute[1])
                elif status.attribute[2] == 'limits':
                    self.settings.child(f'{control_module_type}_settings',
                                        *status.attribute[0]).setLimits(status.attribute[1])

                elif status.attribute[2] == 'options':
                    self.settings.child(f'{control_module_type}_settings',
                                        *status.attribute[0]).setOpts(**status.attribute[1])
                elif status.attribute[2] == 'childAdded':
                    child = Parameter.create(name='tmp')
                    child.restoreState(status.attribute[1][0])
                    self.settings.child(f'{control_module_type}_settings',
                                        *status.attribute[0]).addChild(status.attribute[1][0])

            except Exception as e:
                logger.exception(f'Wrong call to the "update_settings" command: \n{str(e)}')
            self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

        elif status.command == ThreadStatus.UPDATE_UI:
            try:
                if self.ui is not None:
                    if hasattr(self.ui, status.attribute):
                        getattr(self.ui, status.attribute)(*status.args,
                                                           **status.kwargs)
            except Exception as e:
                logger.info(f'Wrong call to the "update_ui" command: \n{str(e)}')

        elif status.command == ThreadStatus.RAISE_TIMEOUT:
            self.raise_timeout()

        elif status.command == ThreadStatus.SHOW_SPLASH:
            self.settings_tree.setEnabled(False)
            self.splash_sc.show()
            self.splash_sc.raise_()
            self.splash_sc.showMessage(status.attribute, color=Qt.white)

        elif status.command == ThreadStatus.CLOSE_SPLASH:
            self.splash_sc.close()
            self.settings_tree.setEnabled(True)

        self.custom_sig.emit(status)  # to be used if needed in custom application connected to this module

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

    def _add_data_to_saver(self, *args, **kwargs):
        raise NotImplementedError

    def append_data(self, *args, **kwargs):
        raise NotImplementedError

    def insert_data(self, *args, **kwargs):
        raise NotImplementedError

    def quit_fun(self):
        """Programmatic entry to quit the control module"""
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
        if self.ui is not None:
            self.ui.do_init(do_init)

    def show_log(self):
        """Open the log file in the default text editor"""
        import webbrowser
        webbrowser.open(get_base_logger(logger).handlers[0].baseFilename)

    def show_config(self, config: Config) -> Config:
        """ Display in a tree the current configuration"""
        if config is not None:
            from pymodaq_gui.utils.widgets.tree_toml import TreeFromToml
            config_tree = TreeFromToml(config)
            config_tree.show_dialog()

            return ControlModulesConfig()

    def update_status(self, txt: str, log=True):
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
            logger.info(txt)

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


class ParameterControlModule(ParameterManager, ControlModule):
    """Base class for a control module with parameters."""

    _update_settings_signal = Signal(edict)

    listener_class: Type[ActorListener] = ActorListener

    def __init__(self, **kwargs):
        ParameterManager.__init__(self, action_list=('save', 'update'))
        ControlModule.__init__(self)

    def value_changed(self, param: Parameter) -> Optional[Parameter]:
        """ParameterManager subclassed method. Process events from value changed by user in the UI Settings

        Parameters
        ----------
        param: Parameter
            a given parameter whose value has been changed by user
        """
        if param.name() == 'plugin_config':
            self.show_config(self.plugin_config)

        elif param.name() == 'connect_server':
            if param.value():
                self.connect_tcp_ip()
            else:
                self._command_tcpip.emit(ThreadCommand('quit', ))

        elif param.name() == 'ip_address' or param.name == 'port':
            self._command_tcpip.emit(
                ThreadCommand('update_connection',
                              dict(ipaddress=self.settings['main_settings', 'tcpip', 'ip_address'],
                                   port=self.settings['main_settings', 'tcpip', 'port'])))

        elif param.name() == 'connect_leco_server':
            self.connect_leco(param.value())

        elif param.name() == "name":
            name = param.value()
            try:
                self._leco_client.name = name
            except AttributeError:
                pass

        else:
            # not handled
            return param

    def _update_settings(self, param: Parameter):
        # I do not understand what it does
        path = self.settings.childPath(param)
        if path is not None:
            if 'main_settings' not in path:
                self._update_settings_signal.emit(edict(path=path, param=param, change='value'))
                if self.settings.child('main_settings', 'tcpip', 'tcp_connected').value():
                    self._command_tcpip.emit(ThreadCommand('send_info', dict(path=path, param=param)))
                if self.settings.child('main_settings', 'leco', 'leco_connected').value():
                    self._command_tcpip.emit(
                        ThreadCommand(LECOCommands.SEND_INFO,
                                      ParameterWithPath(param, path)))

    def connect_tcp_ip(self, params_state=None, client_type: str = "GRABBER") -> None:
        """Init a TCPClient in a separated thread to communicate with a distant TCp/IP Server

        Use the settings: ip_address and port to specify the connection

        See Also
        --------
        TCPServer
        """
        if self.settings.child('main_settings', 'tcpip', 'connect_server').value():
            self._tcpclient_thread = QThread()

            tcpclient = TCPClient(self.settings.child('main_settings', 'tcpip', 'ip_address').value(),
                                  self.settings.child('main_settings', 'tcpip', 'port').value(),
                                  params_state=params_state,
                                  client_type=client_type)
            tcpclient.moveToThread(self._tcpclient_thread)
            self._tcpclient_thread.tcpclient = tcpclient
            tcpclient.cmd_signal.connect(self.process_tcpip_cmds)

            self._command_tcpip[ThreadCommand].connect(tcpclient.queue_command)
            self._tcpclient_thread.started.connect(tcpclient.init_connection)

            self._tcpclient_thread.start()

    def get_leco_name(self) -> str:
        name = self.settings["main_settings", "leco", "leco_name"]
        if name == '':
            # take the module name as alternative
            name = self.settings["main_settings", "module_name"]
        if name == '':
            # a name is required, invent one
            name = f"viewer_{randint(0, 10000)}"
            name = self.settings.child("main_settings", "leco", "leco_name").setValue(name)
        return name

    def get_leco_host_port(self) -> tuple:
        host = self.settings["main_settings", "leco", "host"]
        port = self.settings["main_settings", "leco", "port"]
        if host == '':
            # take the localhost as default
            host = 'localhost'
        if port == '':
            # take the default port as 12300
            port = 12300
        return (host, port)    

    def connect_leco(self, connect: bool) -> None:
        if connect:
            name = self.get_leco_name()
            host, port = self.get_leco_host_port()
            try:
                self._leco_client.name = name
            except AttributeError:
                self._leco_client = self.listener_class(name=name, host=host, port=port)
                self._leco_client.cmd_signal.connect(self.process_tcpip_cmds)
            self._command_tcpip[ThreadCommand].connect(self._leco_client.queue_command)
            self._leco_client.start_listen()
            # self._leco_client.cmd_signal.emit(ThreadCommand(LECOCommands.SET_INFO, attribute=["detector_settings", ""]))
        else:
            self._command_tcpip.emit(ThreadCommand(LECOCommands.QUIT, ))
            try:
                self._command_tcpip[ThreadCommand].disconnect(self._leco_client.queue_command)
            except TypeError:
                pass  # already disconnected

    @Slot(ThreadCommand)
    def process_tcpip_cmds(self, status: ThreadCommand) -> Optional[ThreadCommand]:
        if status.command == 'connected':
            self.settings.child('main_settings', 'tcpip', 'tcp_connected').setValue(True)

        elif status.command == 'disconnected':
            self.settings.child('main_settings', 'tcpip', 'tcp_connected').setValue(False)

        elif status.command == LECOClientCommands.LECO_CONNECTED:
            self.settings.child('main_settings', 'leco', 'leco_connected').setValue(True)

        elif status.command == LECOClientCommands.LECO_DISCONNECTED:
            self.settings.child('main_settings', 'leco', 'leco_connected').setValue(False)

        elif status.command == 'Update_Status':
            self.thread_status(status)

        elif status.command == 'set_info':
            """ The Director sent a parameter to be updated"""
            path_in_settings = status.attribute.path
            if 'move' in self.__class__.__name__.lower():
                common_param = 'move_settings'
            else:
                common_param = 'detector_settings'
            if common_param in path_in_settings:
                param = self.settings.child(*path_in_settings)
            elif 'settings_client' in path_in_settings:
                param = self.settings.child(common_param, *path_in_settings[1:])
            else:
                param = self.settings.child(common_param, *path_in_settings)

            param.setValue(status.attribute.parameter.value())

        elif status.command == LECOCommands.GET_SETTINGS:
            """ The Director requested the content of the actuator settings"""
            if 'move' in self.__class__.__name__.lower():
                common_param = 'move_settings'
            else:
                common_param = 'detector_settings'
            self._command_tcpip.emit(
                ThreadCommand(LECOCommands.SET_DIRECTOR_SETTINGS,
                              ioxml.parameter_to_xml_string(
                                  self.settings.child(common_param))))

        else:
            # not handled
            return status



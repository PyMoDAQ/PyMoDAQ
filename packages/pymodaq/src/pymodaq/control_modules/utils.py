# -*- coding: utf-8 -*-
"""
Created the 03/10/2022

@author: Sebastien Weber
"""

from random import randint
from typing import Optional, Type, Union, TYPE_CHECKING
from easydict import EasyDict as edict
from qtpy import QtWidgets

from qtpy.QtCore import Signal, QObject, Qt, Slot, QThread

from pymodaq_utils.utils import ThreadCommand
from pymodaq_utils.config import GlobalConfig as Config
from pymodaq_utils.logger import get_base_logger, set_logger, get_module_name
from pymodaq_utils.enums import StrEnum

from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq_gui.parameter.utils import ParameterWithPath
from pymodaq_gui.parameter.ioxml import VALID_FOR_CONFIGURATION
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.h5modules.saving import H5Saver

from pymodaq.utils.leco.pymodaq_listener import ActorListener, LECOClientCommands, LECOCommands, LECOComponentMixin
from pymodaq.utils.h5modules.module_saving import DetectorSaver, ActuatorSaver
from pymodaq.control_modules.thread_commands import ThreadStatus

if TYPE_CHECKING:
    from .daq_move_ui.ui_base import DAQ_Move_UI_Base
    from .daq_viewer_ui.ui_base import DAQ_Viewer_UI


config = Config()
logger = set_logger(get_module_name(__file__))




class ControleModuleType(StrEnum):
    DAQ_MOVE = 'DAQ_Move'
    DAQ_VIEWER = 'DAQ_Viewer'


class ControllerStatus(StrEnum):
    MASTER = 'Master'
    SLAVE = 'Slave'





def create_controller_param(axis_name: str = None, axis_names: Optional[list[str]] = None) -> dict:
    controller_param = {'title': 'Controller:', 'name': 'controller', 'type': 'group', 'children': [
        {'title': 'Controller Status:', 'name': 'controller_status', 'type': 'list',
         'value': ControllerStatus.MASTER.value,
         'limits': [ControllerStatus.MASTER.value, ControllerStatus.SLAVE.value]},
        {'title': 'Controller ID:', 'name': 'controller_ID', 'type': 'int', 'value': randint(0, 9999),
         'default': 0, 'readonly': False},

    ]}
    if axis_names is not None and axis_name is not None:
        controller_param['children'].append({'title': 'Axis:', 'name': 'axis', 'type': 'list',
                                             'limits': axis_names.copy(),
                                             'value': axis_name,
                                             VALID_FOR_CONFIGURATION: False})
    return controller_param


def create_remote_connection_params() -> list[dict]:
    """Create common remote connection parameter definitions (LECO)

    These parameters are shared between DAQ_Move and DAQ_Viewer control modules
    and provide the settings for connecting to LECO instances.

    Returns
    -------
    list of dict
        Parameter definitions for LECO remote connections
    """
    return [

        {'title': 'LECO options:', 'name': 'leco', 'type': 'group', 'visible': True,
         'expanded': False, 'children': [
            {'title': 'Connect:', 'name': 'connect_leco_server', 'type': 'bool_push',
             'label': 'Connect', 'value': False},
            {'title': 'Connected?:', 'name': 'leco_connected', 'type': 'led', 'value': False,
             VALID_FOR_CONFIGURATION: False, 'readonly': True},
            {'title': 'Name', 'name': 'leco_name', 'type': 'str', 'value': "", 'default': ""},
            {'title': 'Host:', 'name': 'host', 'type': 'str',
             'value': config('utils', 'network', "leco-server", "host"), "default": "localhost"},
            {'title': 'Port:', 'name': 'port', 'type': 'int',
             'value': config('utils', 'network', 'leco-server', 'port')},
        ]},
    ]




class ControlModule(QObject):
    """Abstract Base class common to both DAQ_Move and DAQ_Viewer control modules

    Attributes
    ----------
    init_signal : Signal[bool]
        This signal is emitted when the chosen hardware is correctly initialized
    command_hardware : Signal[ThreadCommand]
        This signal is used to communicate with the instrument plugin within a separate thread
    quit_signal : Signal[]
        This signal is emitted when the user requested to stop the module
    """
    init_signal = Signal(bool)
    command_hardware = Signal(ThreadCommand)
    quit_signal = Signal()
    _update_settings_signal = Signal(edict)
    status_sig = Signal(str)
    custom_sig = Signal(ThreadCommand)
    ui = None

    def __init__(self):
        QObject.__init__(self)

        self.ui: Union['DAQ_Move_UI_Base', 'DAQ_Viewer_UI'] = None

        self._title = ""
        self.config = config
        # the hardware controller instance set after initialization and to be used by other modules if they share the
        # same controller
        self.controller = None
        self._initialized_state = False
        self._send_to_leco = False
        self._send_to_leco = False
        self._send_to_leco = False
        self._hardware_thread = None

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
            self._h5saver = H5Saver(backend=config('data', 'data_saving', 'backend')[0])
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
        if self._module_and_data_saver.h5saver is None or not self._module_and_data_saver.h5saver.isopen():
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
    def module_type(self) -> ControleModuleType:
        """Get the module type, either DAQ_Move or DAQ_viewer"""
        return ControleModuleType(type(self).__name__)

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

    def stop_module(self):
        """ Programmatic entry to stop the Control module either moving, polling or grabbing"""
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


class ParameterControlModule(ParameterManager,LECOComponentMixin, ControlModule):
    """Base class for a control module with parameters."""

    _update_settings_signal = Signal(edict)

    def __init__(self, listener_class=Type[ActorListener], **kwargs):
        ParameterManager.__init__(self, action_list=kwargs.get("action_list", ("search", "save", "update")))
        LECOComponentMixin.__init__(self, listener_class)
        ControlModule.__init__(self)

    def apply_controller_parameters(self, controller_param: Parameter):
        """Apply controller parameters (Master/Slave, ID, eventually axes) to the ControlModule instance

        Parameters
        ----------
        controller_param: Parameter
            Parameter object containing the controller parameters
        """
        try:
            if self.module_type == ControleModuleType.DAQ_VIEWER:
                controller_settings = self.settings.child('detector_settings', 'controller')
            elif self.module_type == ControleModuleType.DAQ_MOVE:
                controller_settings = self.settings.child('move_settings', 'controller')
            else:
                raise TypeError('Unknown ControlModuleType')
            controller_settings.restoreState(controller_param.saveState())

        except Exception as e:
            logger.exception(f'Error applying controller parameters: {str(e)}')

    def value_changed(self, param: Parameter) -> Optional[Parameter]:
        """ParameterManager subclassed method. Process events from value changed by user in the UI Settings

        Parameters
        ----------
        param: Parameter
            a given parameter whose value has been changed by user
        """
        if param.name() == 'connect_leco_server':
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
                if self.settings.child('main_settings', 'leco', 'leco_connected').value():
                    self._leco_commands_signal.emit(
                        ThreadCommand(LECOCommands.SEND_INFO,
                                      ParameterWithPath(param, path)))


    def get_leco_name(self) -> str:
        name = (self.settings["main_settings", "leco", "leco_name"] or
                self.settings["main_settings", "module_name"] or
                f"viewer_{randint(0, 10000)}"
                )
        self.settings.child("main_settings", "leco", "leco_name").setValue(name)
        return name

    def get_leco_host_port(self) -> tuple[str, int]:
        host = (self.settings["main_settings", "leco", "host"] or 'localhost')
        port = (self.settings["main_settings", "leco", "port"] or 12300)

        return host, port


    @Slot(ThreadCommand)
    def process_leco_commands(self, status: ThreadCommand) -> Optional[ThreadCommand]:
        """Process LECO commands common to all control modules.

        Parameters
        ----------
        status: ThreadCommand
            Possible commands are:

            * :attr:`LECOClientCommands.LECO_CONNECTED`: mark the LECO connection as active in the settings.
            * :attr:`LECOClientCommands.LECO_DISCONNECTED`: mark the LECO connection as inactive in the settings.
            * :attr:`LECOCommands.GET_SETTINGS`: send the module settings back to the Director as an XML string.
        Returns
        -------
        Optional[ThreadCommand]
            ``None`` if the command was handled, or the original command object if it is not recognized by this
             implementation (so subclasses can continue processing it).
        """
        if status.command == LECOClientCommands.LECO_CONNECTED:
            self.settings.child('main_settings', 'leco', 'leco_connected').setValue(True)
        elif status.command == LECOClientCommands.LECO_DISCONNECTED:
            self.settings.child('main_settings', 'leco', 'leco_connected').setValue(False)
        elif status.command == LECOCommands.GET_SETTINGS:
            """ The Director requested the content of the actuator settings"""
            common_param = 'move_settings' if 'move' in self.__class__.__name__.lower() else 'detector_settings'
            settings_xml = ioxml.parameter_to_xml_string(self.settings.child(common_param))
            self._leco_commands_signal.emit(ThreadCommand(LECOCommands.SET_DIRECTOR_SETTINGS, settings_xml))
        else:
            # not handled
            return status
        return None



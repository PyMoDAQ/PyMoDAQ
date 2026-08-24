# -*- coding: utf-8 -*-
"""
Created the 03/10/2022

@author: Sebastien Weber
"""
import dataclasses
from random import randint
from typing import Optional, Type, Union, TYPE_CHECKING, Any
from easydict import EasyDict as edict

from qtpy import QtWidgets
from qtpy.QtCore import Signal, QObject, Qt, Slot, QThread

from pymodaq_utils.utils import ThreadCommand
from pymodaq_utils.config import GlobalConfig as Config
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.parameter.utils import ParameterWithPath
from pymodaq_gui.parameter.ioxml import VALID_FOR_CONFIGURATION
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.h5modules.saving import H5Saver

from pymodaq.utils.leco.pymodaq_listener import ActorListener, LECOClientCommands, LECOCommands, LECOComponentMixin
from pymodaq.utils.h5modules.module_saving import DetectorSaver, ActuatorSaver
from pymodaq.control_modules.thread_commands import (ThreadStatus, ControlToHardware,
                                                     ControleModuleType, ControllerStatus)  # noqa: F401

if TYPE_CHECKING:
    from .daq_move_ui.ui_base import DAQMoveUI
    from .daq_viewer_ui.ui_base import DAQ_Viewer_UI


config = Config()
logger = set_logger(get_module_name(__file__))

class HardwareWorkerBase(QObject):
    """Abstract base shared by ActuatorWorker and DetectorWorker.

    Provides common signals, a unified plugin reference, shared update_settings
    dispatch, and a queue_command handler for the commands that both
    worker classes share (ini_hardware, close).

    Subclasses must implement:
        ini_hardware(params_state, controller) -> edict
        close() -> str
    and set class attribute:
        _kind: str  e.g. 'actuator' or 'detector'
    The settings key is derived automatically as "<kind>_settings".
    """

    status_sig = Signal(ThreadCommand)

    # Subclasses set _kind to 'actuator' or 'detector'.
    # _plugin_settings_key is derived automatically as "<kind>_settings".
    _kind: str = ''

    @property
    def _plugin_settings_key(self) -> str:
        return f"{self._kind}_settings"

    def __init__(self, title: str, plugin_name: str) -> None:
        super().__init__()
        self._title = title
        self._plugin_name = plugin_name
        self.plugin = None              # set by subclass after ini_hardware
        self.controller_address = None

    @property
    def title(self) -> str:
        return self._title

    @property
    def plugin_name(self) -> str:
        return self._plugin_name

    def ini_hardware(self, params_state=None, controller=None):
        raise NotImplementedError

    def update_settings(self, settings_parameter_dict) -> None:
        """Route a settings change to either main_settings or the plugin subtree."""
        path = settings_parameter_dict['path']
        param = settings_parameter_dict['param']
        if path[0] == 'main_settings':
            if hasattr(self, path[-1]):
                setattr(self, path[-1], param.value())
        elif path[0] == self._plugin_settings_key:
            if self.plugin is not None:
                self.plugin.update_settings(settings_parameter_dict)

    def _dispatch_custom_command(self, command) -> None:
        """Forward an unrecognised ThreadCommand to the plugin instance."""
        if self.plugin is not None and hasattr(self.plugin, command.command):
            cmd = getattr(self.plugin, command.command)
            if isinstance(command.attribute, list):
                cmd(*command.attribute)
            elif isinstance(command.attribute, dict):
                cmd(**command.attribute)
            else:
                cmd(command.attribute)

    def close_hardware(self):
        status = self.close()
        self.status_sig.emit(ThreadCommand(ThreadStatus.CLOSE, [status]))


    def queue_command(self, command) -> bool:
        """Handle commands shared by all hardware workers.

        Returns True if the command was consumed, False so the subclass
        can handle its own commands.
        """
        if command.command == ControlToHardware.INI_HARDWARE:
            status = self.ini_hardware(*command.attribute)
            self.status_sig.emit(ThreadCommand(ThreadStatus.INI_HARDWARE, status))
        elif command.command == ControlToHardware.CLOSE:
            self.close_hardware()
        else:
            return False
        return True


class QThreadCustom(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._hardwares = {}

    def add_hardware(self, name: str, worker: HardwareWorkerBase):
            self._hardwares[name] = worker

    def remove_hardware(self, name) -> HardwareWorkerBase:
        return self._hardwares.pop(name, None)

    @property
    def hardware_names(self) -> list[str]:
        return list(self._hardwares.keys())


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


@dataclasses.dataclass
class ControllerAndThread:
    """ Container for the control module worker thread and hardware plugin "controller" object and some related status
     """
    thread: QThreadCustom | None = None  # the thread shared by a master and its slaves
    controller: Any = None  # the controller shared by a master and its slaves
    is_master: bool = True
    id: int = None  # integer as defined in the ExperimentManager (One Master and multiple Slaves share it)
    initialized: bool = False


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
    instrument_changed = Signal() # emitted when an instrument change finished doing things on the ui
    timeout_signal = Signal(str)
    ui = None

    def __init__(self):
        QObject.__init__(self)

        self.ui: Union['DAQMoveUI', 'DAQ_Viewer_UI'] = None

        self._title = ""

        self._controller_and_thread = ControllerAndThread()
        # the hardware controller instance set after initialization and to be used by other modules if they share the
        # same controller

        self.config = config
        # Fallback logger; subclasses should set self.logger before calling super().__init__()
        # so that log messages carry the instance title.
        if not hasattr(self, 'logger'):
            self.logger = logger

        self._send_to_leco = False

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

    def raise_timeout(self):
        """Handle a timeout event: display a status message."""
        self.update_status("Timeout occurred")
        self.timeout_signal.emit(self.title)

    def thread_status(self, status: ThreadCommand):
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
            # Thread teardown is now handled synchronously in _close_hardware() via
            # wait().  This handler just updates state and UI.
            try:
                self.update_status(status.attribute[0])
            except Exception as e:
                self.logger.exception(f'Wrong call to the "close" command: \n{str(e)}')

            self._controller_and_thread.initialized = False
            self.init_signal.emit(self._controller_and_thread.initialized)

        elif status.command == ThreadStatus.UPDATE_UI:
            try:
                if self.ui is not None:
                    if hasattr(self.ui, status.attribute):
                        getattr(self.ui, status.attribute)(*status.args,
                                                           **status.kwargs)
            except Exception as e:
                self.logger.info(f'Wrong call to the "update_ui" command: \n{str(e)}')

        elif status.command == ThreadStatus.RAISE_TIMEOUT:
            self.raise_timeout()

        self.custom_sig.emit(status)  # to be used if needed in custom application connected to this module

    @property
    def module_type(self) -> ControleModuleType:
        """Get the module type, either DAQ_Move or DAQ_viewer"""
        return ControleModuleType(type(self).__name__)

    @property
    def initialized_state(self):
        """bool: Check if the module is initialized"""
        return self._controller_and_thread.initialized

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
            self.ui.update_status(txt)
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
class ParameterControlModule(ParameterManager,LECOComponentMixin, ControlModule):
    """Base class for a control module with parameters."""

    _update_settings_signal = Signal(edict)

    # Subclasses set _hw_kind to the short module kind name (e.g. 'actuator', 'detector').
    # The full settings key is derived automatically as "<kind>_settings".
    _hw_kind: str = ''

    @property
    def _hw_settings_name(self) -> str:
        return f"{self._hw_kind}_settings"

    @property
    def _ui_init_attr(self) -> str:
        return f"{self._hw_kind}_init"

    def __init__(self, listener_class = Type[ActorListener], **kwargs):
        ParameterManager.__init__(self, action_list=kwargs.get("action_list", ("search", "save", "update")))
        LECOComponentMixin.__init__(self, listener_class)
        ControlModule.__init__(self)

    def thread_status(self, status: ThreadCommand):
        """Extend base thread_status with parameter-tree commands.

        Handles UPDATE_MAIN_SETTINGS, UPDATE_SETTINGS, SHOW_SPLASH and CLOSE_SPLASH
        which require access to ParameterManager attributes (settings, settings_tree, splash_sc).
        All other commands are forwarded to the base implementation.
        """
        if status.command == ThreadStatus.UPDATE_MAIN_SETTINGS:
            # this is a way for the plugins to update main settings of the ui (solely values, limits and options)
            try:
                if status.attribute[2] == 'value':
                    self.settings.child('main_settings', *status.attribute[0]).setValue(status.attribute[1])
                elif status.attribute[2] == 'limits':
                    self.settings.child('main_settings', *status.attribute[0]).setLimits(status.attribute[1])
                elif status.attribute[2] == 'options':
                    self.settings.child('main_settings', *status.attribute[0]).setOpts(**status.attribute[1])
            except Exception as e:
                self.logger.exception(f'Wrong call to the "update_main_settings" command: \n{str(e)}')
            self.custom_sig.emit(status)

        elif status.command == ThreadStatus.UPDATE_SETTINGS:
            # using this the settings shown in the UI for the plugin reflects the real plugin settings
            try:
                self.settings.sigTreeStateChanged.disconnect(self.parameter_tree_changed)
            except Exception as e:
                self.logger.exception(str(e))
            try:
                if status.attribute[2] == 'value':
                    self.settings.child(self._hw_settings_name,
                                        *status.attribute[0]).setValue(status.attribute[1])
                elif status.attribute[2] == 'limits':
                    self.settings.child(self._hw_settings_name,
                                        *status.attribute[0]).setLimits(status.attribute[1])
                elif status.attribute[2] == 'options':
                    self.settings.child(self._hw_settings_name,
                                        *status.attribute[0]).setOpts(**status.attribute[1])
                elif status.attribute[2] == 'childAdded':
                    child = Parameter.create(name='tmp')
                    child.restoreState(status.attribute[1][0])
                    self.settings.child(self._hw_settings_name,
                                        *status.attribute[0]).addChild(status.attribute[1][0])
            except Exception as e:
                self.logger.exception(f'Wrong call to the "update_settings" command: \n{str(e)}')
            self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)
            self.custom_sig.emit(status)

        elif status.command == ThreadStatus.SHOW_SPLASH:
            self.settings_tree.setEnabled(False)
            self.splash_sc.show()
            self.splash_sc.raise_()
            self.splash_sc.showMessage(status.attribute, color=Qt.white)
            self.custom_sig.emit(status)

        elif status.command == ThreadStatus.CLOSE_SPLASH:
            self.splash_sc.close()
            self.settings_tree.setEnabled(True)
            self.custom_sig.emit(status)

        else:
            super().thread_status(status)

    def apply_controller_parameters(self, controller_param: Parameter):
        """Apply controller parameters (Master/Slave, ID, eventually axes) to the ControlModule instance

        Parameters
        ----------
        controller_param: Parameter
            Parameter object containing the controller parameters
        """
        try:
            controller_settings = self.settings.child(self._hw_settings_name, 'controller')
            controller_settings.restoreState(controller_param.saveState())
        except Exception as e:
            self.logger.exception(f'Error applying controller parameters: {str(e)}')

    def value_changed(self, param: Parameter):
        """Handle any settings value change.

        Template method that runs in three steps:

        1. Handle parameters common to all control modules (LECO connection).
        2. Call :meth:`_module_value_changed` so subclasses can handle their
           own parameters without overriding this method.
        3. Propagate non-``main_settings`` changes to the hardware thread via
           ``_update_settings_signal`` and, when LECO is connected, via
           ``_leco_commands_signal``.
        """
        if param.name() == 'connect_leco_server':
            self.connect_leco(param.value())
        elif param.name() == "name":
            try:
                self._leco_client.name = param.value()
            except AttributeError:
                pass
        elif param.name() in ('controller_status', 'controller_ID'):
            self.controller_and_thread.is_master = (
                    self.settings[self._hw_settings_name, 'controller', 'controller_status'] == ControllerStatus.MASTER)
            self.controller_and_thread.id = self.settings[self._hw_settings_name, 'controller', 'controller_ID']

        self._module_value_changed(param)

        path = self.settings.childPath(param)
        if (path is not None and
                'main_settings' not in path and
                'saver_settings' not in path):
            self._update_settings_signal.emit(edict(path=path, param=param, change='value'))
            if self.settings.child('main_settings', 'leco', 'leco_connected').value():
                self._leco_commands_signal.emit(
                    ThreadCommand(LECOCommands.SEND_INFO, ParameterWithPath(param, path)))

    def _module_value_changed(self, param: Parameter):
        """Override in subclasses to handle module-specific parameter changes.

        Called from :meth:`value_changed` after LECO params are handled and
        before hardware-thread propagation.  Do *not* call ``super()`` or
        emit ``_update_settings_signal`` for non-``main_settings`` params —
        the base :meth:`value_changed` does that automatically.
        """
        pass

    def quit_fun(self):
        """Programmatic quitting: deinit hardware, emit quit signal, run cleanup hook, close UI."""
        if self._controller_and_thread.initialized:
            self.init_hardware(False)
            # The hardware worker emits status_sig(CLOSE) just before self-exiting.
            # That signal is queued on the main thread.  Flush it now so that
            # thread_status(CLOSE) (which calls update_status / display_status)
            # fires while the UI is still alive, not later when it may be closed.
            QtWidgets.QApplication.processEvents()

        self._quit_cleanup()
        try:
            if self.ui is not None:
                self.ui.close()
        except Exception as e:
            self.logger.exception(str(e))
        self.quit_signal.emit()

    def _quit_cleanup(self):
        """Override in subclasses to add module-specific teardown before UI close."""
        pass

    def _pre_close_hardware(self):
        """Called at the very start of :meth:`_close_hardware` before the close command is sent.

        Override in subclasses to stop timers or other activity that could race
        with hardware shutdown (e.g. DAQ_Move stops its refresh timer here).
        """
        pass

    def _close_hardware(self):
        """Send CLOSE to the hardware thread and block until it stops.

        Calls quit() on the thread (from the main thread) then wait(), making
        quit_fun() synchronous with respect to hardware-thread teardown and
        eliminating the race condition where a new preset was loaded before the
        old thread had fully stopped.  
        """
        self._pre_close_hardware()
        # Disconnect LECO *before* processEvents().  connect_leco(False) calls
        # Listener.stop_listen() which joins the zmq listener thread.
        self.connect_leco(False)
        try:
            self.command_hardware.emit(ThreadCommand(ControlToHardware.CLOSE))  #terminate worker actions
            QtWidgets.QApplication.processEvents()

            hardware = self.controller_and_thread.thread.remove_hardware(self.title) #remove the handle onto the hardware worker even if slave
            hardware.status_sig.disconnect()

            if (self.controller_and_thread.is_master and self.controller_and_thread.thread is not None and
                    self.controller_and_thread.thread.isRunning()):

                for hardware_name in self.controller_and_thread.thread.hardware_names:
                    hardware = self.controller_and_thread.thread.remove_hardware(hardware_name)
                    hardware.close_hardware()
                    hardware.status_sig.disconnect()
                QtWidgets.QApplication.processEvents()
                self.controller_and_thread.thread.quit()


                if not self.controller_and_thread.thread.wait(5000):
                    self.controller_and_thread.thread.terminate()
                    self.controller_and_thread.thread.wait()
                    self.logger.warning('Hardware thread did not stop cleanly; terminated.')
                self.controller_and_thread.thread = None

            if self.ui is not None and self._ui_init_attr:
                setattr(self.ui, self._ui_init_attr, False)
        except Exception as e:
            self.logger.exception(str(e))

    # ------------------------------------------------------------------
    # init_hardware template method
    # ------------------------------------------------------------------

    #: The ThreadCommand name sent to the hardware thread to initialise it.
    #: Subclasses must set this to the appropriate enum value, e.g.
    #: ``ControlToHardwareMove.INI_STAGE`` or ``ControlToHardwareViewer.INI_DETECTOR``.
    _ini_hw_cmd: str = ''

    def init_hardware(self, do_init=True):
        """Init or deinit the selected instrument plugin.

        The deinit path is handled by :meth:`_close_hardware`.
        The init path follows a template:

        1. :meth:`_create_hardware` — instantiate the hardware worker (abstract)
        2. :meth:`_setup_hardware_thread` — move worker to thread and start it
        3. connect common signals (``command_hardware``, ``status_sig``, ``_update_settings_signal``)
        4. :meth:`_connect_hardware_signals` — connect module-specific extra signals
        5. emit the ini command via :meth:`_ini_hardware_command`
        6. :meth:`_post_hardware_init` — any post-init UI work
        7. ``connect_leco(True)``
        """
        if not do_init:
            self._close_hardware()
            return
        try:
            hardware = self._create_hardware()
            if self.controller_and_thread.is_master:
                self.controller_and_thread.thread = QThreadCustom()
            else:
                if self.controller_and_thread.thread is None or not self.controller_and_thread.thread.isRunning():
                    if self.ui is not None:
                        self.ui.init_action.setChecked(False)
                    raise ValueError("You set this module as slave but no Master Controller is set")

            self._setup_hardware_thread(hardware)

            self.command_hardware[ThreadCommand].connect(hardware.queue_command)
            hardware.status_sig[ThreadCommand].connect(self.thread_status)
            self._update_settings_signal[edict].connect(hardware.update_settings)
            self._connect_hardware_signals(hardware)

            self.controller_and_thread.thread.add_hardware(self.title, hardware) # to hold a reference
            self.command_hardware.emit(self._ini_hardware_command())
            self._post_hardware_init()
        except Exception as e:
            self.logger.exception(str(e))

    @property
    def controller_and_thread(self) -> ControllerAndThread | None:
        return self._controller_and_thread

    @controller_and_thread.setter
    def controller_and_thread(self, controller: ControllerAndThread | None) -> None:
        self._controller_and_thread = controller

    def _create_hardware(self):
        """Instantiate and return the hardware worker object. Must be overridden."""
        raise NotImplementedError

    def _setup_hardware_thread(self, hardware):
        """Move *hardware* to the thread and start it.

        Default: always move and start. Override when the move/start should be
        conditional (e.g. DAQ_Viewer's ``viewer_in_thread`` config option).
        """
        hardware.moveToThread(self.controller_and_thread.thread)
        self.controller_and_thread.thread.finished.connect(hardware.deleteLater)
        if self.controller_and_thread.is_master:
            self.controller_and_thread.thread.start()

    def _connect_hardware_signals(self, hardware):
        """Connect module-specific signals from *hardware*. Default: no-op."""
        pass

    def _ini_hardware_command(self) -> ThreadCommand:
        """Return the ThreadCommand that triggers hardware initialisation.

        Default uses :attr:`_ini_hw_cmd` as the command name and
        ``[hw_settings.saveState(), self.controller]`` as the attribute.
        Override if the attribute structure differs.
        """
        return ThreadCommand(
            self._ini_hw_cmd,
            attribute=[self.settings.child(self._hw_settings_name).saveState(),
                       self._controller_and_thread.controller],
        )

    def _post_hardware_init(self):
        """Called after the ini command is emitted. Default: no-op."""
        pass

    @property
    def master(self) -> bool:
        """Get/Set programmatically the Master/Slave status of the module's controller."""
        if self.initialized_state:
            return self._controller_and_thread.is_master
        return True

    @master.setter
    def master(self, is_master: bool):
        if self.initialized_state:
            self.settings.child(self._hw_settings_name, 'controller', 'controller_status').setValue(
                ControllerStatus.MASTER if is_master else ControllerStatus.SLAVE)
            self.controller_and_thread.is_master = self.master

    def param_deleted(self, param):
        """Propagate parameter deletion to the hardware thread."""
        if param.name() not in putils.iter_children(self.settings.child('main_settings'), []):
            self._update_settings_signal.emit(
                edict(path=[self._hw_settings_name], param=param, change='parent')
            )

    def child_added(self, param, data):
        """Propagate child addition to the hardware thread."""
        path = self.settings.childPath(param)
        if path is not None and 'main_settings' not in path:
            self._update_settings_signal.emit(
                edict(path=path, param=data[0], change='childAdded')
            )

    def _load_plugin_params(self) -> Optional[Parameter]:
        """Return the plugin-specific Parameter tree to populate the hw settings subtree.

        Override in subclasses to return the Parameter loaded from the plugin class.
        The base implementation returns None (no children added).
        """
        return None

    def _reload_plugin_settings(self):
        """Clear the hw settings subtree and repopulate it from the current plugin.

        Sets ``main_settings/module_name``, clears all children of the
        ``_hw_settings_name`` group, then calls :meth:`_load_plugin_params` and
        adds the returned Parameter's children.
        """
        self.settings.child('main_settings', 'module_name').setValue(self._title)
        try:
            for child in self.settings.child(self._hw_settings_name).children():
                child.remove()
            plugin_params = self._load_plugin_params()
            if plugin_params is not None:
                self.settings.child(self._hw_settings_name).addChildren(plugin_params.children())
        except Exception as e:
            self.logger.exception(str(e))

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
            settings_xml = ioxml.parameter_to_xml_string(self.settings.child(self._hw_settings_name))
            self._leco_commands_signal.emit(ThreadCommand(LECOCommands.SET_DIRECTOR_SETTINGS, settings_xml))
        else:
            # not handled
            return status
        return None



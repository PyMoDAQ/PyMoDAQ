from abc import ABC, abstractmethod

from pymodaq_utils.enums import StrEnum

import logging
from threading import Event
from typing import cast, Optional, Union, List, Sequence, Type

from pyleco.core import COORDINATOR_PORT
from pyleco.json_utils.errors import JSONRPCError, RECEIVER_UNKNOWN, NODE_UNKNOWN
from pyleco.utils.listener import Listener, PipeHandler
from qtpy.QtCore import QObject, Signal  # type: ignore

from pymodaq_data.data import DataWithAxes
from serializall import SerializableFactory, SerializableBase
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import ioxml
from pymodaq_gui.parameter.utils import ParameterWithPath

from pymodaq.utils.leco.utils import binary_serialization_to_kwargs
from pymodaq.utils.leco.rpc_method_definitions import (
    GenericMethods,
    MoveMethods,
    ViewerMethods,
    GenericDirectorMethods,
    MoveDirectorMethods,
    ViewerDirectorMethods, DashboardMethods, DashboardDirectorMethods,
)


# Commands for ThreadCommand
class LECOClientCommands(StrEnum):
    LECO_CONNECTED = "leco_connected"
    LECO_DISCONNECTED = "leco_disconnected"


class LECOCommands(StrEnum):
    CONNECT = "ini_connection"
    QUIT = "quit"
    GET_SETTINGS = 'get_settings'
    SET_DIRECTOR_SETTINGS = 'set_director_settings'
    SET_INFO = 'set_info'
    SEND_INFO = 'send_info'


class LECOMoveCommands(StrEnum):
    POSITION = 'position_is'
    MOVE_DONE = 'move_done'
    UNITS_CHANGED = 'units_changed'
    STOP = 'stop_motion'
    MOVE_ABS = 'move_abs'
    MOVE_REL = 'move_rel'
    MOVE_HOME = 'move_home'
    GET_ACTUATOR_VALUE = 'get_actuator_value'


class LECOViewerCommands(StrEnum):
    DATA_READY = 'data_ready'
    GRAB = 'grab'
    SNAP = 'snap'
    STOP = 'stop_grab'

class LECODashboardCommands(StrEnum):
    GET_DEVICES = 'get_devices'
    SEND_DEVICES = 'send_devices'
    GET_CONFIGURATIONS = 'get_configurations'
    SEND_CONFIGURATIONS = 'send_configurations'
    APPLY_CONFIGURATION = 'apply_configuration'
    APPLIED_CONFIGURATION_DONE = 'applied_configuration_done'
    GET_PRESETS = 'get_presets'
    SEND_PRESETS = 'send_presets'
    APPLY_PRESET = 'apply_preset'
    APPLIED_PRESET_DONE = 'applied_preset_done'

class ListenerSignals(QObject):
    cmd_signal = Signal(ThreadCommand)
    """
    Possible messages sendable via `cmd_signal`
        For all modules: Info, Infos, Info_xml, set_info

        For a detector: Send Data 0D, Send Data 1D, Send Data 2D

        For an actuator: move_abs, move_home, move_rel, check_position, stop_motion
    """
    # message = Signal(Message)


class PymodaqPipeHandler(PipeHandler):

    def __init__(self, name: str, signals: ListenerSignals, **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.signals = signals
        self.register_data_types_for_deserialization()

    def register_data_types_for_deserialization(
        self, types: Optional[Sequence[type[SerializableBase]]] = None
    ) -> None:
        """Register different data types for deserialization in subclasses."""
        if types is None:
            return
        for cls in types:
            SerializableFactory().register_from_type(
                cls, cls.serialize, cls.deserialize
            )

class ActorHandler(PymodaqPipeHandler):
    def register_data_types_for_deserialization(
        self, types: Optional[Sequence[type[SerializableBase]]] = None
    ) -> None:
        all_types: Sequence[type[SerializableBase]] = [DataWithAxes]
        if types:
            all_types.extend(types)  # type: ignore
        super().register_data_types_for_deserialization(all_types)

    def register_rpc_methods(self) -> None:
        super().register_rpc_methods()
        self.register_binary_rpc_method(
            self.set_info, name=GenericMethods.SET_INFO, accept_binary_input=True
        )
        self.register_rpc_method(self.send_data_grab, name=ViewerMethods.GRAB)
        self.register_rpc_method(self.send_data_snap, name=ViewerMethods.SNAP)
        self.register_binary_rpc_method(
            self.move_abs, accept_binary_input=True, name=MoveMethods.MOVE_ABS
        )
        self.register_binary_rpc_method(
            self.move_rel, accept_binary_input=True, name=MoveMethods.MOVE_REL
        )
        self.register_rpc_method(self.move_home, name=MoveMethods.MOVE_HOME)
        self.register_rpc_method(self.get_actuator_value, name=MoveMethods.GET_ACTUATOR_VALUE)
        self.register_rpc_method(self.stop_motion, name=MoveMethods.STOP_MOTION)
        self.register_rpc_method(self.stop_grab, name=ViewerMethods.STOP)
        self.register_rpc_method(self.get_settings, name=GenericMethods.GET_SETTINGS)
        self.register_rpc_method(self.get_devices, name=DashboardMethods.GET_DEVICES)
        self.register_rpc_method(self.get_configurations, name=DashboardMethods.GET_CONFIGURATIONS)
        self.register_rpc_method(self.apply_configuration, name=DashboardMethods.APPLY_CONFIGURATION)
        self.register_rpc_method(self.get_presets, name=DashboardMethods.GET_PRESETS)
        self.register_rpc_method(self.apply_preset, name=DashboardMethods.APPLY_PRESET)
    @staticmethod
    def extract_pymodaq_object(
        value: Optional[Union[float, str]], additional_payload: Optional[List[bytes]]
    ):
        if value is None and additional_payload:
            return cast(
                DataWithAxes, SerializableFactory().get_apply_deserializer(additional_payload[0])
            )
        else:
            return value

    # generic commands
    def set_info(self,
                 parameter: Optional[Union[float, str]],
                 additional_payload: Optional[List[bytes]] = None,
                 ) -> None:
        assert additional_payload
        param = cast(
            ParameterWithPath, SerializableFactory().get_apply_deserializer(additional_payload[0])
        )
        self.signals.cmd_signal.emit(ThreadCommand(LECOCommands.SET_INFO, attribute=param))

    def get_settings(self):
        self.signals.cmd_signal.emit(ThreadCommand(LECOCommands.GET_SETTINGS))

    # dashboard commands
    def get_devices(self):
        self.signals.cmd_signal.emit(ThreadCommand(LECODashboardCommands.GET_DEVICES))

    def get_configurations(self):
        self.signals.cmd_signal.emit(ThreadCommand(LECODashboardCommands.GET_CONFIGURATIONS))

    def apply_configuration(self, configuration : str):
        self.signals.cmd_signal.emit(ThreadCommand(LECODashboardCommands.APPLY_CONFIGURATION, attribute=configuration))

    def get_presets(self):
        self.signals.cmd_signal.emit(ThreadCommand(LECODashboardCommands.GET_PRESETS))

    def apply_preset(self, preset : str):
        self.signals.cmd_signal.emit(ThreadCommand(LECODashboardCommands.APPLY_PRESET, attribute=preset))

    # detector commands
    def send_data_grab(self,) -> None:
        self.signals.cmd_signal.emit(ThreadCommand(LECOViewerCommands.GRAB))

    def send_data_snap(self,) -> None:
        self.signals.cmd_signal.emit(ThreadCommand(LECOViewerCommands.SNAP))

    # actuator commands
    def move_abs(
        self,
        position: Optional[Union[float, str]],
        additional_payload: Optional[List[bytes]] = None,
    ) -> None:
        """Move to an absolute position.

        :param position: Deprecated, should be None and content transferred binary.
        :param additional_payload: binary frames containing the position as PyMoDAQ `DataActuator`.
        """
        pos = self.extract_pymodaq_object(position, additional_payload)
        self.signals.cmd_signal.emit(ThreadCommand(LECOMoveCommands.MOVE_ABS, pos))

    def move_rel(
        self,
        position: Optional[Union[float, str]],
        additional_payload: Optional[List[bytes]] = None,
    ) -> None:
        """Move by a relative position.

        :param position: Deprecated, should be None and content transferred binary.
        :param additional_payload: binary frames containing the position as PyMoDAQ `DataActuator`.
        """
        pos = self.extract_pymodaq_object(position, additional_payload)
        self.signals.cmd_signal.emit(ThreadCommand(LECOMoveCommands.MOVE_REL, pos))

    def move_home(self) -> None:
        self.signals.cmd_signal.emit(ThreadCommand(LECOMoveCommands.MOVE_HOME))

    def get_actuator_value(self) -> None:
        """Request that the actuator value is sent later on."""
        # according to DAQ_Move, this supersedes "check_position"
        self.signals.cmd_signal.emit(ThreadCommand(LECOMoveCommands.GET_ACTUATOR_VALUE))

    def stop_motion(self,) -> None:
        self.signals.cmd_signal.emit(ThreadCommand(LECOMoveCommands.STOP))

    def stop_grab(self,) -> None:
        self.signals.cmd_signal.emit(ThreadCommand(LECOViewerCommands.STOP))


# to be able to separate them later on
MoveActorHandler = ActorHandler
ViewerActorHandler = ActorHandler
DashboardActorHandler = ActorHandler


class PymodaqListener(Listener):
    """A Listener prepared for PyMoDAQ.

    :param name: Name of this module.
    :param host: Host name of the communication server.
    :param port: Port number of the communication server.
    """
    remote_names: set[str]

    local_methods = ["pong", "set_log_level"]

    def __init__(self,
                 name: str,
                 handler_class: Type[PymodaqPipeHandler] = PymodaqPipeHandler,
                 host: str = "localhost",
                 port: int = COORDINATOR_PORT,
                 logger: Optional[logging.Logger] = None,
                 timeout: float = 1,
                 **kwargs) -> None:
        super().__init__(name, host, port, logger=logger, timeout=timeout,
                         **kwargs)
        self.remote_names = set()
        self.signals = ListenerSignals()
        # self.signals.message.connect(self.handle_message)
        self.cmd_signal = self.signals.cmd_signal
        self._handler_class = handler_class

    def _listen(self, name: str, stop_event: Event, coordinator_host: str, coordinator_port: int,
                data_host: str, data_port: int) -> None:
        self.message_handler = self._handler_class(name,
                                                   host=coordinator_host, port=coordinator_port,
                                                   data_host=data_host, data_port=data_port,
                                                   signals=self.signals,
                                                   )
        self.message_handler.register_on_name_change_method(self.indicate_sign_in_out)
        self.message_handler.listen(stop_event=stop_event)

    def stop_listen(self) -> None:
        super().stop_listen()
        try:
            del self.communicator
        except AttributeError:
            pass
        self.signals.cmd_signal.emit(ThreadCommand(LECOClientCommands.LECO_DISCONNECTED))

    def indicate_sign_in_out(self, full_name: str):
        if "." in full_name:
            self.signals.cmd_signal.emit(ThreadCommand(LECOClientCommands.LECO_CONNECTED))
        else:
            self.signals.cmd_signal.emit(ThreadCommand(LECOClientCommands.LECO_DISCONNECTED))


class ActorListener(PymodaqListener):
    """Listener for modules being an Actor (being remote controlled)."""

    def __init__(self,
                 name: str,
                 handler_class: Type[ActorHandler] = ActorHandler,
                 host: str = "localhost",
                 port: int = COORDINATOR_PORT,
                 logger: Optional[logging.Logger] = None,
                 timeout: float = 1,
                 **kwargs) -> None:
        super().__init__(name, handler_class=handler_class, host=host, port=port,
                         logger=logger, timeout=timeout,
                         **kwargs)

    def start_listen(self) -> None:
        super().start_listen()
        self.message_handler.register_rpc_method(
            self.set_remote_name, name=GenericMethods.SET_REMOTE_NAME
        )

    def set_remote_name(self, name: str) -> None:
        """Define what the name of the remote for answers is."""
        self.remote_names.add(name)

    def remove_remote_name(self, name: str) -> None:
        self.remote_names.discard(name)

    def queue_command(self, command: ThreadCommand) -> None:
        """Queue a command to send it via LECO to the server."""

        # generic commands
        if command.command == LECOCommands.CONNECT:
            try:
                if self.thread.is_alive():
                    return  # already started
            except AttributeError:
                pass  # start later on, as there is no thread.
            self.start_listen()

        elif command.command == LECOCommands.QUIT:
            try:
                self.stop_listen()
            except Exception:
                pass
            finally:
                self.cmd_signal.emit(ThreadCommand('disconnected'))

        elif command.attribute is not None:
            # here are all methods requiring an attribute in the ThreadCommand

            if command.command == LECOViewerCommands.DATA_READY:
                value = command.attribute
                self.send_rpc_message_to_remote(
                    method=ViewerDirectorMethods.SET_DATA,
                    **binary_serialization_to_kwargs(value),
                )

            elif command.command == LECOCommands.SEND_INFO:
                self.send_rpc_message_to_remote(
                    method=GenericDirectorMethods.SET_DIRECTOR_INFO,
                    **binary_serialization_to_kwargs(command.attribute, data_key='parameter'))

            elif command.command == LECOMoveCommands.POSITION:
                value = command.attribute
                if isinstance(value, (list, tuple)):
                    value = value[0]  # for backward compatibility with attributes list
                self.send_rpc_message_to_remote(
                    method=MoveDirectorMethods.SEND_POSITION,
                    **binary_serialization_to_kwargs(pymodaq_object=value, data_key="data"),
                )

            elif command.command == LECOMoveCommands.MOVE_DONE:
                value = command.attribute
                if isinstance(value, (list, tuple)):
                    value = value[0]  # for backward compatibility with attributes list
                self.send_rpc_message_to_remote(
                    method=MoveDirectorMethods.SET_MOVE_DONE,
                    **binary_serialization_to_kwargs(value, data_key="data"),
                )

            elif command.command == LECOMoveCommands.UNITS_CHANGED:
                units: str = command.attribute
                self.send_rpc_message_to_remote(
                    method=MoveDirectorMethods.SET_UNITS,
                    units=units.encode(),
                )

            elif command.command == LECOCommands.SET_DIRECTOR_SETTINGS:
                self.send_rpc_message_to_remote(
                    method=GenericDirectorMethods.SET_DIRECTOR_SETTINGS,
                    settings=command.attribute.decode(),
                )
            elif command.command == LECODashboardCommands.SEND_DEVICES:
                self.send_rpc_message_to_remote(
                    method=DashboardDirectorMethods.SEND_DEVICES,
                    **binary_serialization_to_kwargs(command.attribute, data_key="data")
                )
            elif command.command == LECODashboardCommands.SEND_CONFIGURATIONS:
                self.send_rpc_message_to_remote(
                    method=DashboardDirectorMethods.SEND_CONFIGURATIONS,
                    configurations=command.attribute
                )
            elif command.command == LECODashboardCommands.SEND_PRESETS:
                self.send_rpc_message_to_remote(
                    method=DashboardDirectorMethods.SEND_PRESETS,
                    presets=command.attribute
                )
            elif command.command == LECODashboardCommands.APPLIED_PRESET_DONE:
                self.send_rpc_message_to_remote(
                    method=DashboardDirectorMethods.APPLIED_PRESET_DONE,
                    done=command.attribute
                )
            elif command.command == LECODashboardCommands.APPLIED_CONFIGURATION_DONE:
                self.send_rpc_message_to_remote(
                    method=DashboardDirectorMethods.APPLIED_CONFIGURATION_DONE,
                    done=command.attribute
                )
        else:
            raise IOError("Unknown TCP client command")

    def send_rpc_message_to_remote(self, method: str, **kwargs) -> None:
        if not self.remote_names:
            return
        for name in list(self.remote_names):
            try:
                self.communicator.ask_rpc(receiver=name, method=method, **kwargs)
            except JSONRPCError as exc:
                if exc.rpc_error.code in (RECEIVER_UNKNOWN.code, NODE_UNKNOWN.code):
                    self.remove_remote_name(name)


# to be able to separate them later on
MoveActorListener = ActorListener
ViewerActorListener = ActorListener
DashboardActorListener = ActorListener


class LECOComponentMixin:
    """Mixin class adding LECO network connectivity to a PyMoDAQ component.

    This mixin provides the interface for connecting a PyMoDAQ module (actuator,
    detector, or dashboard) to the LECO (Laboratory Equipment Communication
    Orchestration) network. It manages the lifecycle of an :class:`ActorListener`
    that runs in a background thread and bridges incoming LECO remote-procedure
    calls to Qt signals and vice versa.

    Subclasses must implement :meth:`get_leco_name`, :meth:`get_leco_host_port`,
    and :meth:`process_leco_commands`.

    The class-level signal :attr:`_leco_commands_signal` is used to forward
    outgoing :class:`~pymodaq_utils.utils.ThreadCommand` objects to the listener's
    queue so that they are transmitted over LECO from the Qt thread.
    """

    _leco_commands_signal = Signal(ThreadCommand)

    def __init__(self, listener_class: Type[ActorListener], **kwargs):
        """Initialize the mixin.

        :param listener_class: The :class:`ActorListener` subclass to instantiate
            when establishing a LECO connection.
        """
        self._leco_client: Optional[ActorListener] = None
        self._listener_class: Type[ActorListener] = listener_class

    def connect_leco(self, connect: bool) -> None:
        """Connect to or disconnect from the LECO network.

        When *connect* is ``True``, an :class:`ActorListener` is created (or
        reused if one already exists) and started.  The listener's
        ``cmd_signal`` is wired to :meth:`process_leco_commands` so that
        incoming LECO commands are dispatched to this component, and
        :attr:`_leco_commands_signal` is connected to the listener's
        :meth:`~ActorListener.queue_command` so that outgoing commands can be
        sent from the Qt thread.

        When *connect* is ``False``, a :attr:`~LECOCommands.QUIT` command is
        emitted to stop the listener gracefully, and both signal/slot connections
        (to :meth:`~ActorListener.queue_command` and from ``cmd_signal``) are removed.

        :param connect: ``True`` to establish the connection, ``False`` to
            tear it down.
        """
        if connect:
            name = self.get_leco_name()
            host, port = self.get_leco_host_port()
            try:
                self._leco_client.name = name
            except AttributeError:
                self._leco_client = self._listener_class(name=name, host=host, port=port)
                self._leco_client.cmd_signal.connect(self.process_leco_commands)
            self._leco_commands_signal.connect(self._leco_client.queue_command)
            self._leco_client.start_listen()
        else:
            self._leco_commands_signal.emit(ThreadCommand(LECOCommands.QUIT, ))
            if self._leco_client is not None:
                try:
                    self._leco_commands_signal.disconnect(self._leco_client.queue_command)
                except TypeError:
                    pass  # already disconnected    
                try:
                    self._leco_client.cmd_signal.disconnect(self.process_leco_commands)
                except TypeError:
                    pass  # already disconnected

    def get_leco_name(self) -> str:
        """Return the LECO component name used to register on the network.

        :returns: The name string that uniquely identifies this component on the
            LECO coordinator.
        :raises NotImplementedError: Must be overridden by subclasses.
        """
        raise NotImplementedError

    def get_leco_host_port(self) -> tuple[str, int]:
        """Return the host and port of the LECO coordinator to connect to.

        :returns: A ``(host, port)`` tuple where *host* is the hostname or IP
            address of the coordinator and *port* is its TCP port number.
        :raises NotImplementedError: Must be overridden by subclasses.
        """
        raise NotImplementedError

    def process_leco_commands(self, status: ThreadCommand) -> Optional[ThreadCommand]:
        """Handle an incoming command forwarded from the LECO listener.

        This slot is connected to the listener's ``cmd_signal`` and is called
        whenever a remote LECO peer sends a command to this component (e.g.
        grab, snap, move_abs).  Subclasses should dispatch on
        ``status.command`` and take the appropriate action.

        :param status: The :class:`~pymodaq_utils.utils.ThreadCommand` received
            from the listener, carrying the command name and optional attribute
            payload.
        :returns: Optionally a :class:`~pymodaq_utils.utils.ThreadCommand` for
            further processing, or ``None``.
        :raises NotImplementedError: Must be overridden by subclasses.
        """
        raise NotImplementedError

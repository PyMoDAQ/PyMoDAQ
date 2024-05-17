
try:
    from enum import StrEnum  # type: ignore
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass
import logging
from threading import Event
from typing import Optional, Union, List, Type

from pyleco.core import COORDINATOR_PORT
from pyleco.utils.listener import Listener, PipeHandler
from qtpy.QtCore import QObject, Signal  # type: ignore

from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import ioxml
from pymodaq.utils.tcp_ip.serializer import DataWithAxes, SERIALIZABLE, DeSerializer
from pymodaq.utils.leco.utils import serialize_object


class LECOClientCommands(StrEnum):
    LECO_CONNECTED = "leco_connected"
    LECO_DISCONNECTED = "leco_disconnected"


class LECOCommands(StrEnum):
    CONNECT = "ini_connection"
    QUIT = "quit"


class LECOMoveCommands(StrEnum):
    POSITION = 'position_is'
    MOVE_DONE = 'move_done'


class LECOViewerCommands(StrEnum):
    DATA_READY = 'data_ready'


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


class ActorHandler(PymodaqPipeHandler):

    def register_rpc_methods(self) -> None:
        super().register_rpc_methods()
        self.register_rpc_method(self.set_info)
        self.register_rpc_method(self.send_data)
        self.register_rpc_method(self.move_abs)
        self.register_rpc_method(self.move_rel)
        self.register_rpc_method(self.move_home)
        self.register_rpc_method(self.get_actuator_value)
        self.register_rpc_method(self.stop_motion)

    @staticmethod
    def extract_dwa_object(data_string: str) -> DataWithAxes:
        """Extract a DataWithAxes object from the received message."""
        desererializer = DeSerializer.from_b64_string(data_string)
        return desererializer.dwa_deserialization()

    # generic commands
    def set_info(self, path: List[str], param_dict_str: str) -> None:
        self.signals.cmd_signal.emit(ThreadCommand("set_info", attribute=[path, param_dict_str]))

    # detector commands
    def send_data(self, grabber_type: str = "") -> None:
        self.signals.cmd_signal.emit(ThreadCommand(f"Send Data {grabber_type}"))

    # actuator commands
    def move_abs(self, position: Union[float, str]) -> None:
        pos = self.extract_dwa_object(position) if isinstance(position, str) else position
        self.signals.cmd_signal.emit(ThreadCommand("move_abs", attribute=[pos]))

    def move_rel(self, position: Union[float, str]) -> None:
        pos = self.extract_dwa_object(position) if isinstance(position, str) else position
        self.signals.cmd_signal.emit(ThreadCommand("move_rel", attribute=[pos]))

    def move_home(self) -> None:
        self.signals.cmd_signal.emit(ThreadCommand("move_home"))

    def get_actuator_value(self) -> None:
        """Request that the actuator value is sent later on."""
        # according to DAQ_Move, this supersedes "check_position"
        self.signals.cmd_signal.emit(ThreadCommand("get_actuator_value"))

    def stop_motion(self,) -> None:
        # not implemented in DAQ_Move!
        self.signals.cmd_signal.emit(ThreadCommand("stop_motion"))


# to be able to separate them later on
MoveActorHandler = ActorHandler
ViewerActorHandler = ActorHandler


class PymodaqListener(Listener):
    """A Listener prepared for PyMoDAQ.

    :param name: Name of this module.
    :param host: Host name of the communication server.
    :param port: Port number of the communication server.
    """
    remote_name: str = ""

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
        self.message_handler.register_rpc_method(self.set_remote_name)

    def set_remote_name(self, name: str) -> None:
        """Define what the name of the remote for answers is."""
        self.remote_name = name

    # @Slot(ThreadCommand)
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

        elif command.command == 'update_connection':
            # self.ipaddress = command.attribute['ipaddress']
            # self.port = command.attribute['port']
            pass  # TODO change name?

        elif command.command == LECOViewerCommands.DATA_READY:
            # code from the original:
            # self.data_ready(data=command.attribute)
            # def data_ready(data): self.send_data(datas[0]['data'])
            value = command.attribute  # type: ignore
            self.communicator.ask_rpc(
                receiver=self.remote_name,
                method="set_data",
                data=serialize_object(value),
            )

        elif command.command == 'send_info':
            path = command.attribute['path']  # type: ignore
            param = command.attribute['param']  # type: ignore
            self.communicator.ask_rpc(
                receiver=self.remote_name,
                method="set_info",
                path=path,
                param_dict_str=ioxml.parameter_to_xml_string(param).decode())

        elif command.command == LECOMoveCommands.POSITION:
            value = command.attribute[0]  # type: ignore
            self.communicator.ask_rpc(receiver=self.remote_name,
                                      method="set_position",
                                      position=serialize_object(value),
                                      )

        elif command.command == LECOMoveCommands.MOVE_DONE:
            value = command.attribute[0]  # type: ignore
            self.communicator.ask_rpc(receiver=self.remote_name,
                                      method="set_move_done",
                                      position=serialize_object(value),
                                      )

        elif command.command == 'x_axis':
            value = command.attribute[0]  # type: ignore
            if isinstance(value, SERIALIZABLE):
                self.communicator.ask_rpc(receiver=self.remote_name,
                                          method="set_x_axis",
                                          data=serialize_object(value),
                                          )
            elif isinstance(value, dict):
                self.communicator.ask_rpc(receiver=self.remote_name, method="set_x_axis", **value)
            else:
                raise ValueError("Nothing to send!")

        elif command.command == 'y_axis':
            value = command.attribute[0]  # type: ignore
            if isinstance(value, SERIALIZABLE):
                self.communicator.ask_rpc(receiver=self.remote_name,
                                          method="set_y_axis",
                                          data=serialize_object(value),
                                          )
            elif isinstance(value, dict):
                self.communicator.ask_rpc(receiver=self.remote_name, method="set_y_axis", **value)
            else:
                raise ValueError("Nothing to send!")

        else:
            raise IOError('Unknown TCP client command')


# to be able to separate them later on
MoveActorListener = ActorListener
ViewerActorListener = ActorListener

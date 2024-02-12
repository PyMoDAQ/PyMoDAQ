
try:
    from enum import StrEnum  # type: ignore
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass
import logging
from threading import Event, get_ident
from typing import Any, Optional, Union

from qtpy.QtCore import QObject, Signal  # type: ignore

from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import ioxml
from pymodaq.utils.leco.utils import PYMODAQ_MESSAGE_TYPE, PymodaqMessage, get_pymodaq_data
from pymodaq.utils.tcp_ip.serializer import DataWithAxes, SERIALIZABLE, DeSerializer

from pyleco.core import COORDINATOR_PORT
from pyleco.core.message import Message
from pyleco.utils.listener import Listener, PipeHandler, CommunicatorPipe


class LECO_Client_Commands(StrEnum):
    LECO_CONNECTED = "leco_connected"
    LECO_DISCONNECTED = "leco_disconnected"


class ListenerSignals(QObject):
    cmd_signal = Signal(ThreadCommand)
    """
    Possible messages sendable via `cmd_signal`
        For all modules: Info, Infos, Info_xml, set_info

        For a detector: Send Data 0D, Send Data 1D, Send Data 2D

        For an actuator: move_abs, move_home, move_rel, check_position, stop_motion
    """
    # message = Signal(Message)


class PymodaqCommunicator(CommunicatorPipe):
    """Communicator offering pymodaq specifics."""

    def ask_rpc_pymodaq(self, receiver: Union[bytes, str], method: str,
                        timeout: Optional[float] = None,
                        pymodaq_data: Optional[SERIALIZABLE] = None,
                        **kwargs) -> Union[Any, DeSerializer]:
        """Send a message with an optional pymodaq object and return the answer."""
        command_string = self.rpc_generator.build_request_str(
            method=method,
            **kwargs)
        message = PymodaqMessage(receiver=receiver, data=command_string, pymodaq_data=pymodaq_data)
        response = self.ask_message(message, timeout=timeout)
        # for pyleco>0.1.0 the following can be simplified to self.interpret_rpc_response(response)
        response_value = self.rpc_generator.get_result_from_response(response.payload[0])
        if response_value is None:
            response_data = get_pymodaq_data(message=response)
            return response_data
        else:
            return response_value

    def ask_rpc_flexible(self, receiver: Union[bytes, str], method: str,
                         timeout: Optional[float] = None,
                         pymodaq_data: Optional[SERIALIZABLE] = None,
                         pymodaq_data_name: str = "data",
                         **kwargs) -> Union[Any, DeSerializer]:
        """Send a value, either serialized, or via json."""
        if isinstance(pymodaq_data, SERIALIZABLE):
            return self.ask_rpc_pymodaq(receiver=receiver, method=method, timeout=timeout, **kwargs)
        else:
            kwargs[pymodaq_data_name] = pymodaq_data
            return self.ask_rpc(receiver=receiver, method=method, timeout=timeout, **kwargs)


class PymodaqPipeHandler(PipeHandler):
    """A pipe-MessageHandler which can read / write pymodaq messages.

    1. Whenever a message of pymodaq type arrives, the message is stored in a temporary variable.
    2. The JSON message is evaluated calling an appropriate method.
    3. The called methods can access the stored message.
       - If, for example, the required value is None, they may look in the pymodaq_data of the
         message for the value.
       - If they want to send a pymodaq object as a response, they may store it in another variable.
    4. Finally, the response will be sent.
    """

    current_msg: Optional[PymodaqMessage]
    return_paymodaq_data: Optional[SERIALIZABLE]

    def __init__(self, name: str, signals: ListenerSignals, **kwargs):
        super().__init__(name, **kwargs)
        self.signals = signals

    def _read_socket_message(self, timeout: Optional[float] = None) -> Message:
        if self.socket.poll(int(timeout or self.timeout * 1000)):
            return PymodaqMessage.from_frames(*self.socket.recv_multipart())
        raise TimeoutError("Reading timed out")

    def handle_message(self, message: PymodaqMessage) -> None:
        if message.header_elements.message_type == PYMODAQ_MESSAGE_TYPE:
            response = self.handle_pymodaq_message(message=message)
            self.send_message(response)
        else:
            return super().handle_message(message)

    def finish_handle_commands(self, message: PymodaqMessage) -> None:
        # pyleco <0.1.1
        if message.header_elements.message_type == PYMODAQ_MESSAGE_TYPE:
            response = self.handle_pymodaq_message(message=message)
            self.send_message(response)
        else:
            super().finish_handle_commands(message)  # type: ignore

    def handle_pymodaq_message(self, message: PymodaqMessage) -> PymodaqMessage:
        # Prepare storage
        self.current_msg = message
        self.return_paymodaq_data = None
        # Handle message
        self.log.info(f"Handling commands of {message}.")
        reply = self.rpc.process_request(message.payload[0])
        response = PymodaqMessage(
            receiver=message.sender,
            conversation_id=message.conversation_id,
            data=reply,
            pymodaq_data=self.return_paymodaq_data,
            )
        # Reset storage
        self.current_msg = None
        self.return_paymodaq_data = None
        return response

    def create_communicator(self, **kwargs) -> PymodaqCommunicator:
        """Create a communicator wherever you want to access the pipe handler."""
        com = PymodaqCommunicator(buffer=self.buffer, pipe_port=self.pipe_port,
                                  handler=self,
                                  **kwargs)
        self._communicators[get_ident()] = com
        return com


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

    def extract_dwa_object(self) -> DataWithAxes:
        """Extract a DataWithAxes object from the received message."""
        if self.current_msg and (deserializer := get_pymodaq_data(self.current_msg)):
            return deserializer.dwa_deserialization()
        else:
            raise ValueError(
                "You have to specify the position as float or as an DataWithAxes object.")

    # generic commands
    def set_info(self, path: list[str], param_dict_str: str) -> None:
        self.signals.cmd_signal.emit(ThreadCommand("set_info", attribute=[path, param_dict_str]))

    # detector commands
    def send_data(self, grabber_type: str = "") -> None:
        self.signals.cmd_signal.emit(ThreadCommand(f"Send Data {grabber_type}"))

    # actuator commands
    def move_abs(self, position: Optional[float] = None) -> None:
        pos = self.extract_dwa_object() if position is None else position
        self.signals.cmd_signal.emit(ThreadCommand("move_abs", attribute=[pos]))

    def move_rel(self, position: Optional[float] = None) -> None:
        pos = self.extract_dwa_object() if position is None else position
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
    communicator: PymodaqCommunicator

    local_methods = ["pong", "set_log_level"]

    def __init__(self,
                 name: str,
                 handler_class: type[PymodaqPipeHandler] = PymodaqPipeHandler,
                 host: str = "localhost",
                 port: int = COORDINATOR_PORT,
                 logger: Optional[logging.Logger] = None,
                 timeout: float = 1,
                 **kwargs) -> None:
        super().__init__(name, host, port, logger=logger, timeout=timeout,
                         **kwargs)
        print("start listener as", name)
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
        self.signals.cmd_signal.emit(ThreadCommand(LECO_Client_Commands.LECO_DISCONNECTED))

    def indicate_sign_in_out(self, full_name: str):
        if "." in full_name:
            self.signals.cmd_signal.emit(ThreadCommand(LECO_Client_Commands.LECO_CONNECTED))
        else:
            self.signals.cmd_signal.emit(ThreadCommand(LECO_Client_Commands.LECO_DISCONNECTED))

    def get_communicator(self, **kwargs) -> PymodaqCommunicator:
        return super().get_communicator(**kwargs)  # type: ignore


class ActorListener(PymodaqListener):
    """Listener for modules being an Actor (being remote controlled)."""

    def __init__(self,
                 name: str,
                 handler_class: type[ActorHandler] = ActorHandler,
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
        print("COMMAND", command)

        # generic commands
        if command.command == "ini_connection":
            try:
                if self.thread.is_alive():
                    return  # already started
            except AttributeError:
                pass  # start later on, as there is no thread.
            self.start_listen()

        elif command.command == "quit":
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

        elif command.command == 'data_ready':
            # code from the original:
            # self.data_ready(data=command.attribute)
            # def data_ready(data): self.send_data(datas[0]['data'])
            value = command.attribute[0]['data']  # type: ignore
            self.communicator.ask_rpc_flexible(
                receiver=self.remote_name,
                method="set_data",
                pymodaq_data=value,
            )

        elif command.command == 'send_info':
            path = command.attribute['path']  # type: ignore
            param = command.attribute['param']  # type: ignore
            self.communicator.ask_rpc(
                receiver=self.remote_name,
                method="set_info",
                path=path,
                param_dict_str=ioxml.parameter_to_xml_string(param).decode())

        elif command.command == 'position_is':
            value = command.attribute[0]  # type: ignore
            self.communicator.ask_rpc_flexible(receiver=self.remote_name,
                                               method="set_position",
                                               pymodaq_data=value,
                                               pymodaq_data_name="position")

        elif command.command == 'move_done':
            value = command.attribute[0]  # type: ignore
            self.communicator.ask_rpc_flexible(receiver=self.remote_name,
                                               method="set_move_done",
                                               pymodaq_data=value,
                                               pymodaq_data_name="position")

        elif command.command == 'x_axis':
            value = command.attribute[0]  # type: ignore
            if isinstance(value, SERIALIZABLE):
                self.communicator.ask_rpc_pymodaq(receiver=self.remote_name,
                                                  method="set_x_axis", pymodaq_data=value)
            elif isinstance(value, dict):
                self.communicator.ask_rpc(receiver=self.remote_name, method="set_x_axis", **value)
            else:
                raise ValueError("Nothing to send!")

        elif command.command == 'y_axis':
            value = command.attribute[0]  # type: ignore
            if isinstance(value, SERIALIZABLE):
                self.communicator.ask_rpc_pymodaq(receiver=self.remote_name,
                                                  method="set_y_axis", pymodaq_data=value)
            elif isinstance(value, dict):
                self.communicator.ask_rpc(receiver=self.remote_name, method="set_y_axis", **value)
            else:
                raise ValueError("Nothing to send!")

        else:
            raise IOError('Unknown TCP client command')


# to be able to separate them later on
MoveActorListener = ActorListener
ViewerActorListener = ActorListener

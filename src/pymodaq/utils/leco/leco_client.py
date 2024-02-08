
try:
    from enum import StrEnum  # type: ignore
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass
import logging
from typing import Optional

import numpy as np
from qtpy.QtCore import QObject, Signal  # type: ignore

from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import ioxml
from pymodaq.utils.leco.utils import create_pymodaq_message, PYMODAQ_MESSAGE_TYPE

from pyleco.core import COORDINATOR_PORT
from pyleco.core.message import Message
from pyleco.utils.listener import Listener, PipeHandler
from pyleco.utils import listener
from pyleco.directors.director import Director


class LECO_Client_Commands(StrEnum):
    LECO_CONNECTED = "leco_connected"
    LECO_DISCONNECTED = "leco_disconnected"


class PymodaqPipeHandler(PipeHandler):

    current_msg: Optional[Message]
    return_payload: Optional[list[bytes]]

    def finish_handle_commands(self, message: Message) -> None:
        if message.header_elements.message_type == PYMODAQ_MESSAGE_TYPE:
            self.handle_pymodaq_commands(msg=message)
        else:
            super().finish_handle_commands(message)

    def handle_pymodaq_commands(self, msg: Message) -> None:
        if b'"method":' in msg.payload[0]:
            # Prepare storage
            self.current_msg = msg
            self.return_payload = None
            # Handle message
            self.log.info(f"Handling commands of {msg}.")
            reply = self.rpc.process_request(msg.payload[0])
            response = create_pymodaq_message(
                receiver=msg.sender,
                conversation_id=msg.conversation_id,
                data=reply,
                pymodaq_data=self.return_payload)

            if self.return_payload:
                response.payload += self.return_payload
            self.send_message(response)
            # Reset storage
            self.current_msg = None
            self.return_payload = None
        else:
            self.log.error(f"Unknown message from {msg.sender!r} received: {msg.payload[0]!r}")


listener.PipeHandler = PymodaqPipeHandler  # inject modified pipe handler


class PymodaqListener(Listener):
    """A Listener prepared for PyMoDAQ.

    :param name: Name of this module.
    :param host: Host name of the communication server.
    :param port: Port number of the communication server.
    """
    remote_name: str = ""

    def __init__(self,
                 name: str,
                 host: str = "localhost",
                 port: int = COORDINATOR_PORT,
                 logger: logging.Logger | None = None,
                 timeout: float = 1,
                 **kwargs) -> None:
        super().__init__(name, host, port, logger=logger, timeout=timeout,
                         **kwargs)
        print("start listener as", name)
        self.signals = self.ListenerSignals()
        # self.signals.message.connect(self.handle_message)
        self.cmd_signal = self.signals.cmd_signal
        self.request_buffer: dict[str, list[Message]] = {}

    local_methods = ["pong", "set_log_level"]

    class ListenerSignals(QObject):
        cmd_signal = Signal(ThreadCommand)
        """
        Possible messages sendable via `cmd_signal`
            For all modules: Info, Infos, Info_xml, set_info

            For a detector: Send Data 0D, Send Data 1D, Send Data 2D

            For an actuator: move_abs, move_home, move_rel, check_position, stop_motion
        """
        # message = Signal(Message)

    def start_listen(self) -> None:
        print("start listening")
        super().start_listen()
        # self.message_handler.finish_handle_commands = self.finish_handle_commands  # type: ignore
        self.message_handler.register_on_name_change_method(self.indicate_sign_in_out)
        communicator = self.message_handler.get_communicator()
        if self.message_handler.namespace is not None:
            self.signals.cmd_signal.emit(ThreadCommand(LECO_Client_Commands.LECO_CONNECTED))
        self.director = Director(actor=self.remote_name, communicator=communicator)
        for method in (
            self.set_remote_name,
            self.set_info,
            self.move_abs,
            self.move_rel,
            self.move_home,
            self.get_actuator_value,
            self.stop_motion,
        ):
            communicator.register_rpc_method(method=method)

    def stop_listen(self) -> None:
        super().stop_listen()
        self.signals.cmd_signal.emit(ThreadCommand(LECO_Client_Commands.LECO_DISCONNECTED))

    def indicate_sign_in_out(self, full_name: str):
        if "." in full_name:
            self.signals.cmd_signal.emit(ThreadCommand(LECO_Client_Commands.LECO_CONNECTED))
        else:
            self.signals.cmd_signal.emit(ThreadCommand(LECO_Client_Commands.LECO_DISCONNECTED))

    def set_remote_name(self, name: str) -> None:
        """Define what the name of the remote for answers is."""
        self.remote_name = name
        try:
            self.director.actor = name
        except AttributeError:
            pass

    # generic commands
    def set_info(self, path: list[str], param_dict_str: str) -> None:
        self.signals.cmd_signal.emit(ThreadCommand("set_info", attribute=[path, param_dict_str]))

    # detector commands
    def send_data(self, grabber_type: str = "") -> None:
        self.signals.cmd_signal.emit(ThreadCommand(f"Send Data {grabber_type}"))

    # actuator commands
    def move_abs(self, position: float) -> None:
        self.signals.cmd_signal.emit(ThreadCommand("move_abs", attribute=[position]))

    def move_rel(self, position: float) -> None:
        self.signals.cmd_signal.emit(ThreadCommand("move_rel", attribute=[position]))

    def move_home(self) -> None:
        self.signals.cmd_signal.emit(ThreadCommand("move_home"))

    def get_actuator_value(self) -> None:
        """Request that the actuator value is sent later on."""
        # according to DAQ_Move, this supersedes "check_position"
        self.signals.cmd_signal.emit(ThreadCommand("get_actuator_value"))

    def stop_motion(self,) -> None:
        # not implemented in DAQ_Move!
        self.signals.cmd_signal.emit(ThreadCommand("stop_motion"))

    # @Slot(ThreadCommand)
    def queue_command(self, command: ThreadCommand) -> None:
        """Queue a command to send it via LECO to the server."""
        print("command", command)

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
            if True:  # TODO if we have a pymodaq data object
                command_string = self.communicator.rpc_generator.build_request_str(method="set_data", data=None)
                pymodaq_data = b""  # TODO serialized pymodaq data object
                message = create_pymodaq_message(receiver=self.director.actor, data=command_string,
                                                 pymodaq_data=pymodaq_data)
                response = self.director.ask_message(message)
                self.communicator.interpret_rpc_response(response)
            else:  # it is a plain value
                self.director.ask_rpc(method="set_data", data=command.attribute[0]['data'])

        elif command.command == 'send_info':
            self.director.ask_rpc(method="set_info",
                                  path=command.attribute['path'],
                                  param_dict_str=ioxml.parameter_to_xml_string(command.attribute['param']))

        elif command.command == 'position_is':
            self.director.ask_rpc(method="set_position", position=command.attribute[0].value())

        elif command.command == 'move_done':
            # name of parameter unknown
            self.director.ask_rpc(method="set_move_done", position=command.attribute[0].value())

        elif command.command == 'x_axis':
            if isinstance(command.attribute[0], np.ndarray):
                self.director.ask_rpc(method="set_x_axis", data=command.attribute[0])
            elif isinstance(command.attribute[0], dict):
                self.director.ask_rpc(method="set_x_axis", **command.attribute[0])
            else:
                raise ValueError("Nothing to send!")

        elif command.command == 'y_axis':
            if isinstance(command.attribute[0], np.ndarray):
                self.director.ask_rpc(method="set_y_axis", data=command.attribute[0])
            elif isinstance(command.attribute[0], dict):
                self.director.ask_rpc(method="set_y_axis", **command.attribute[0])
            else:
                raise ValueError("Nothing to send!")

        else:
            raise IOError('Unknown TCP client command')

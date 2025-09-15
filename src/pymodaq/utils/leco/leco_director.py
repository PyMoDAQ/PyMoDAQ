
import random

from pyleco.core import COORDINATOR_PORT
from pymodaq_utils.enums import StrEnum
from typing import Callable, cast, Sequence, List, Optional, Union

from pyleco.json_utils.errors import JSONRPCError, RECEIVER_UNKNOWN
import pymodaq_gui.parameter.utils as putils
from pymodaq_utils.config import Config
# object used to send info back to the main thread:
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter import ioxml
from pymodaq_gui.parameter.utils import ParameterWithPath
from qtpy.QtCore import QTimer

from pymodaq.utils.leco.director_utils import GenericDirector
from pymodaq.utils.leco.pymodaq_listener import PymodaqListener
from pymodaq.utils.leco.rpc_method_definitions import GenericDirectorMethods, MoveDirectorMethods
from pymodaq_utils.serialize.factory import SerializableFactory
from pymodaq.control_modules.thread_commands import ThreadStatus, ThreadStatusMove

config = Config()

class DirectorCommands(StrEnum):
    SET_SETTINGS = GenericDirectorMethods.SET_DIRECTOR_SETTINGS
    SET_INFO = GenericDirectorMethods.SET_DIRECTOR_INFO

    SEND_POSITION = MoveDirectorMethods.SEND_POSITION  # to display the actor position
    SET_MOVE_DONE = MoveDirectorMethods.SET_MOVE_DONE
    SET_UNITS = MoveDirectorMethods.SET_UNITS  # to set units accordingly to the one of the actor


class DirectorReceivedCommands(StrEnum):
    MOVE_DONE = ThreadStatusMove.MOVE_DONE
    GET_ACTUATOR_VALUE = ThreadStatusMove.GET_ACTUATOR_VALUE

config = Config()

leco_parameters = [
    {'title': 'Actor name:', 'name': 'actor_name', 'type': 'str', 'value': "actor_name",
     'tip': 'Name of the actor plugin to communicate with.'},
    {'title': 'Coordinator Host:', 'name': 'host', 'type': 'str', 'value': config('network', "leco-server", "host")},
    {'title': 'Coordinator Port:', 'name': 'port', 'type': 'int', 'value': config('network', "leco-server", "port")},
    {'title': 'Settings PyMoDAQ Client:', 'name': 'settings_client', 'type': 'group', 'children': []},
]


class LECODirector:
    """
    This is a mixin for a Control module to direct another, remote module (analogous to TCP Server).


    """

    controller: GenericDirector
    settings: Parameter
    _title: str

    def __init__(self, host: str = 'localhost', port : int = COORDINATOR_PORT, **kwargs) -> None:

        name = f'{self._title}_{random.randrange(0, 10000)}_director'

        self.listener = PymodaqListener(name=name, host=host, port=port)
        self.listener.start_listen()

        self.communicator = self.listener.get_communicator()

        #registering rpc methods common to all Directors
        self.register_rpc_methods((
            self.set_director_settings,
        ))
        self.register_binary_rpc_methods((
            self.set_director_info,
        ))

    def register_binary_rpc_methods(self, methods: Sequence[Callable]) -> None:
        for method in methods:
            self.listener.register_binary_rpc_method(method, accept_binary_input=True)

    def register_rpc_methods(self, methods: Sequence[Callable]) -> None:
        for method in methods:
            self.communicator.register_rpc_method(method=method)

    def commit_settings(self, param) -> None:
        self.commit_leco_settings(param=param)

    def commit_leco_settings(self, param: Parameter) -> None:
        if param.name() == "actor_name":
            self.controller.actor = param.value()
        elif param.name() in putils.iter_children(self.settings.child('settings_client'), []):
            self.controller.set_info(param=param)

    def close(self) -> None:
        """ Clear the content of the settings_clients setting"""
        self.settings.child('settings_client').clearChildren()
        self.listener.stop_listen()

    def start_timer(self) -> None:
        """To be called in child classes."""
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_actor_connection)
        try:
            # cast is used by the type checker to infer the returned type (when many are possible)
            timeout = cast(int, config("network", "leco-server", "heartbeat-timeout"))
        except KeyError:
            timeout = 1000
        self.timer.start(timeout)  # in milli seconds

    def check_actor_connection(self) -> None:
        try:
            self.controller.ask_rpc("pong", timeout=0.1)
        except JSONRPCError as exc:
            if exc.rpc_error.code == RECEIVER_UNKNOWN.code:
                self.emit_status(ThreadCommand(ThreadStatus.UPDATE_UI, "do_init", args=[False]))
            else:
                self.emit_status(
                    ThreadCommand(
                        ThreadStatus.UPDATE_STATUS,
                        f"Connection error to actor: {exc.rpc_error.message}",
                    )
                )

    def stop(self):
        """
            not implemented.
        """
        pass
        return ""

    def emit_status(self, status: ThreadCommand) -> None:
        """ Emit the status_sig signal with the given status ThreadCommand back to the main GUI.
        """
        super().emit_status(status=status)  # type: ignore

    # Methods accessible via remote calls
    def set_director_info(self,
                 parameter: Optional[Union[float, str]],
                 additional_payload: Optional[List[bytes]] = None,
                 ) -> None:
        """ Write the value of a param updated from the actor to here in the
        Parameter with path: ('move_settings', 'settings_client')
        """
        GenericDirectorMethods.SET_DIRECTOR_INFO  # defined here
        assert additional_payload
        # cast is used by the type checker to infer the returned type (when many are possible)
        param = cast(
            ParameterWithPath, SerializableFactory().get_apply_deserializer(additional_payload[0])
        )

        try:
            path = ['settings_client']
            path.extend(param.path[1:])

            self.settings.child(*path).setValue(param.value())
        except Exception as e:
            print(f'could not set the param {param} in the director:\n'
                  f'{str(e)}')

    def set_director_settings(self, settings: bytes):
        """ Get the content of the actor settings to pe populated in this plugin
        'settings_client' parameter"""
        GenericDirectorMethods.SET_DIRECTOR_INFO  # defined here
        params = ioxml.XML_string_to_parameter(settings)
        self.settings.child('settings_client').addChildren(params)

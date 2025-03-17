
import random
from pymodaq_utils.enums import StrEnum
from typing import Callable, Sequence, List, Optional, Union

import pymodaq_gui.parameter.utils as putils
# object used to send info back to the main thread:
from pymodaq_utils.utils import ThreadCommand
from pymodaq.utils.config import Config
from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter import ioxml
from pymodaq_gui.parameter.utils import ParameterWithPath

from pymodaq.utils.leco.director_utils import GenericDirector
from pymodaq.utils.leco.pymodaq_listener import PymodaqListener
from pymodaq_utils.serialize.factory import SerializableFactory
from pymodaq.control_modules.thread_commands import ThreadStatusMove

config = Config()

class DirectorCommands(StrEnum):
    SET_SETTINGS = 'set_settings'
    SET_INFO = 'set_info'

    SEND_POSITION = 'send_position'  # to display the actor position
    SET_MOVE_DONE = 'set_move_done'
    SET_UNITS = 'set_units'  # to set units accordingly to the one of the actor


class DirectorReceivedCommands(StrEnum):
    MOVE_DONE = ThreadStatusMove.MOVE_DONE
    GET_ACTUATOR_VALUE = ThreadStatusMove.GET_ACTUATOR_VALUE


leco_parameters = [
    {'title': 'Actor name:', 'name': 'actor_name', 'type': 'str', 'value': "actor_name",
     'tip': 'Name of the actor plugin to communicate with.'},
    {'title': 'Coordinator Host:', 'name': 'host', 'type': 'str', 'value': config('network', "leco-server", "host")},
    {'title': 'Settings PyMoDAQ Client:', 'name': 'settings_client', 'type': 'group', 'children': []},
]


class LECODirector:
    """
    This is a mixin for a Control module to direct another, remote module (analogous to TCP Server).


    """

    controller: GenericDirector
    settings: Parameter
    _title: str

    def __init__(self, host: str = 'localhost', **kwargs) -> None:

        name = f'{self._title}_{random.randrange(0, 10000)}_director'

        self.listener = PymodaqListener(name=name, host=host)
        self.listener.start_listen()

        self.communicator = self.listener.get_communicator()

        #registering rpc methods common to all Directors
        self.register_rpc_methods((
            self.set_settings,
        ))
        self.register_binary_rpc_methods((
            self.set_info,
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
    def set_info(self,
                 parameter: Optional[Union[float, str]],
                 additional_payload: Optional[List[bytes]] = None,
                 ) -> None:
        """ Write the value of a param upfated from the actor to here in the
        Parameter with path: ('move_settings', 'settings_client')
        """
        param: ParameterWithPath = SerializableFactory().get_apply_deserializer(additional_payload[0])

        try:
            path = ['settings_client']
            path.extend(param.path[1:])

            self.settings.child(*path).setValue(param.value())
        except Exception as e:
            print(f'could not set the param {param} in the director:\n'
                  f'{str(e)}')

    def set_settings(self, settings: bytes):
        """ Get the content of the actor settings to pe populated in this plugin
        'settings_client' parameter"""
        params = ioxml.XML_string_to_parameter(settings)
        self.settings.child('settings_client').addChildren(params)


from typing import Callable, Sequence

from pyleco.utils.listener import Listener, CommunicatorPipe
from pyleco.utils import listener

import pymodaq.utils.parameter.utils as putils
# object used to send info back to the main thread:
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import Parameter

from pymodaq.utils.leco.director_utils import GenericDirector
from pymodaq.utils.leco.leco_client import PymodaqPipeHandler


leco_parameters = [
    {'title': 'Actor name:', 'name': 'actor_name', 'type': 'str', 'value': "actor_name",
     'text': 'Name of the actor plugin to communicate with.'},
]


listener.PipeHandler = PymodaqPipeHandler


class LECODirector:
    """
    This is a mixin for a Control module to direct another, remote module (analogous to TCP Server).

        ================= ==============================
        **Attributes**      **Type**
        *command_server*    instance of Signal
        *x_axis*            1D numpy array
        *y_axis*            1D numpy array
        *data*              double precision float array
        ================= ==============================

        See Also
        --------
        utility_classes.DAQ_TCP_server
    """
    message_list = ["Quit", "Status", "Done", "Server Closed", "Info", "Infos", "Info_xml",
                    "move_abs", 'move_home', 'move_rel', 'get_actuator_value', 'stop_motion',
                    'position_is', 'move_done',
                    ]
    socket_types: list[str]

    controller: GenericDirector
    settings: Parameter

    communicator: CommunicatorPipe

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        try:
            name = self.settings.child("main_settings", 'module_name').value()
        except Exception as exc:
            print("name not available", exc)
            name = "director_whatever"

        print("name", name)
        # TODO use the same Listener as the LECOActorModule
        self._listener = Listener(name=name)
        self._listener.start_listen()
        self.communicator = self._listener.get_communicator()
        self.register_rpc_methods((
            self.set_info,
        ))

    def register_rpc_methods(self, methods: Sequence[Callable]) -> None:
        for method in methods:
            self.communicator.register_rpc_method(method=method)

    def commit_settings(self, param: Parameter) -> None:
        raise NotImplementedError

    def commit_leco_settings(self, param: Parameter) -> None:
        if param.name() == "actor_name":
            self.controller.actor = param.value()
        elif param.name() in putils.iter_children(self.settings.child('settings_client'), []):
            self.controller.set_info(param=param)

    def close(self) -> None:
        self._listener.stop_listen()

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
    def set_info(self, path: list[str], param_dict_str: str) -> None:
        self.emit_status(ThreadCommand("set_info", attribute=[path, param_dict_str]))

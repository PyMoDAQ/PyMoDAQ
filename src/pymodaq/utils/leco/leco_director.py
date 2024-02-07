
from typing import Callable, Sequence

from pyleco.directors.director import Director
from pyleco.utils.listener import Listener, CommunicatorPipe

import pymodaq.utils.parameter.utils as putils
# object used to send info back to the main thread:
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import Parameter, ioxml

leco_parameters = [
    {'title': 'Actor name:', 'name': 'actor_name', 'type': 'str', 'value': "actor_name",
     'text': 'Name of the actor plugin to communicate with.'},
]


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

    controller: Director
    settings: Parameter

    communicator: CommunicatorPipe

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        name = self.settings.child('module_name').value()

        print("name", name)
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
        if param.name() == "remote_name":
            self.controller.actor = param.value()
        elif param.name() in putils.iter_children(self.settings.child('settings_client'), []):
            self.controller.ask_rpc(method="set_info",
                                    path=putils.get_param_path(param)[2:],
                                    param_dict_str=ioxml.parameter_to_xml_string(param))

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

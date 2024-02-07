"""
Utils for the Director Modules

These directors correspond to the PymodaqListener
"""

from typing import Optional

import pymodaq.utils.parameter.utils as putils
from pymodaq.utils.parameter import Parameter, ioxml

from pyleco.directors.director import Director


class GenericDirector(Director):
    """Director helper to control some Module remotely."""

    def set_remote_name(self, name: Optional[str] = None):
        """Set the remote name of the Module (i.e. where it should send responses to)."""
        self.ask_rpc(method="set_remote_name", name=name or self.communicator.name)

    def set_info(self, param: Parameter):
        # It removes the first two parts (main_settings and detector_settings?)
        self.set_info_str(path=putils.get_param_path(param)[2:],
                          param_dict_str=ioxml.parameter_to_xml_string(param).decode())

    def set_info_str(self, path: list[str], param_dict_str: str) -> None:
        self.ask_rpc(method="sef_info", path=path, param_dict_str=param_dict_str)


class DetectorDirector(GenericDirector):
    def send_data(self, grabber_type: str = "") -> None:
        self.ask_rpc("send_data", grabber_type=grabber_type)


class ActuatorDirector(GenericDirector):
    def move_abs(self, position: float) -> None:
        self.ask_rpc("move_abs", position=position)

    def move_rel(self, position: float) -> None:
        self.ask_rpc("move_rel", position=position)

    def move_home(self) -> None:
        self.ask_rpc("move_home")

    def get_actuator_value(self) -> None:
        """Request that the actuator value is sent later on.

        Later the `set_data` method will be called.
        """
        # according to DAQ_Move, this supersedes "check_position"
        self.ask_rpc("get_actuator_value")

    def stop_motion(self,) -> None:
        # not implemented in DAQ_Move!
        self.ask_rpc("stop_motion")

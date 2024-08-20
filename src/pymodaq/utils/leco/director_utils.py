"""
Utils for the Director Modules

These directors correspond to the PymodaqListener
"""

from typing import Optional, Union, List

from pyleco.directors.director import Director

import pymodaq_gui.parameter.utils as putils
from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq.control_modules.move_utility_classes import DataActuator
from pymodaq.utils.leco.utils import serialize_object


class GenericDirector(Director):
    """Director helper to control some Module remotely."""

    def set_remote_name(self, name: Optional[str] = None):
        """Set the remote name of the Module (i.e. where it should send responses to)."""
        self.ask_rpc(method="set_remote_name", name=name or self.communicator.name)

    def set_info(self, param: Parameter):
        # It removes the first two parts (main_settings and detector_settings?)
        self.set_info_str(path=putils.get_param_path(param)[2:],
                          param_dict_str=ioxml.parameter_to_xml_string(param).decode())

    def set_info_str(self, path: List[str], param_dict_str: str) -> None:
        self.ask_rpc(method="sef_info", path=path, param_dict_str=param_dict_str)


class DetectorDirector(GenericDirector):
    def send_data(self, grabber_type: str = "") -> None:
        self.ask_rpc("send_data", grabber_type=grabber_type)


class ActuatorDirector(GenericDirector):
    def move_abs(self, position: Union[float, DataActuator]) -> None:
        self.ask_rpc("move_abs", position=serialize_object(position))

    def move_rel(self, position: Union[float, DataActuator]) -> None:
        self.ask_rpc("move_rel", position=serialize_object(position))

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

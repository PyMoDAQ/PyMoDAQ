"""
Utils for the Director Modules

These directors correspond to the PymodaqListener
"""

from typing import Optional, Union, List

from pyleco.directors.director import Director

import pymodaq_gui.parameter.utils as putils
from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq.utils.data import DataActuator
from pymodaq.utils.leco.utils import binary_serialization_to_kwargs, SerializableFactory
from pymodaq.utils.leco.rpc_method_definitions import GenericMethods, MoveMethods, ViewerMethods

from pymodaq_gui.parameter.utils import ParameterWithPath



class GenericDirector(Director):
    """Director helper to control some Module remotely."""

    def set_remote_name(self, name: Optional[str] = None):
        """Set the remote name of the Module (i.e. where it should send responses to)."""
        self.ask_rpc(method=GenericMethods.SET_REMOTE_NAME, name=name or self.communicator.name)

    def set_info(self, param: Parameter):
        # It removes the first two parts (main_settings and detector_settings?)
        pwp = ParameterWithPath(param, putils.get_param_path(param)[2:])
        self.ask_rpc(method=GenericMethods.SET_INFO,
                     **binary_serialization_to_kwargs(pwp, data_key='parameter'))

    def get_settings(self,) -> None:
        self.ask_rpc(GenericMethods.GET_SETTINGS)


class DetectorDirector(GenericDirector):
    def send_data_grab(self) -> None:
        self.ask_rpc(ViewerMethods.GRAB)

    def send_data_snap(self) -> None:
        self.ask_rpc(ViewerMethods.SNAP)

    def stop_grab(self) -> None:
        self.ask_rpc(ViewerMethods.STOP)


class ActuatorDirector(GenericDirector):
    def move_abs(self, position: Union[list, float, DataActuator]) -> None:
        self.ask_rpc(
            MoveMethods.MOVE_ABS, **binary_serialization_to_kwargs(position, data_key="position")
        )

    def move_rel(self, position: Union[list, float, DataActuator]) -> None:
        self.ask_rpc(
            MoveMethods.MOVE_REL, **binary_serialization_to_kwargs(position, data_key="position")
        )

    def move_home(self) -> None:
        self.ask_rpc(MoveMethods.MOVE_HOME)

    def get_actuator_value(self) -> None:
        """Request that the actuator value is sent later on.

        Later the `set_data` method will be called.
        """
        # according to DAQ_Move, this supersedes "check_position"
        self.ask_rpc(MoveMethods.GET_ACTUATOR_VALUE)

    def stop_motion(self,) -> None:
        # not implemented in DAQ_Move!
        self.ask_rpc(MoveMethods.STOP_MOTION)


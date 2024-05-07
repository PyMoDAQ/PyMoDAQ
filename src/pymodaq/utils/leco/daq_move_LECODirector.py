"""
LECO Director instrument plugin are to be used to communicate (and control) remotely real
instrument plugin through TCP/IP using the LECO Protocol

For this to work a coordinator must be instantiated can be done within the dashboard or directly
running: `python -m pyleco.coordinators.coordinator`

"""

from typing import Union

from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, comon_parameters_fun, main,
                                                          DataActuatorType, DataActuator)

from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import Parameter

from pymodaq.utils.leco.leco_director import LECODirector, leco_parameters
from pymodaq.utils.leco.director_utils import ActuatorDirector
from pymodaq.utils.tcp_ip.serializer import DeSerializer


class DAQ_Move_LECODirector(LECODirector, DAQ_Move_base):
    """A control module, which in the dashboard, allows to control a remote Move module.

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
    settings: Parameter
    controller: ActuatorDirector

    is_multiaxes = False
    axes_names = []
    params_client = []  # parameters of a client grabber
    data_actuator_type = DataActuatorType['float']  # DataActuatorType['DataActuator']

    message_list = LECODirector.message_list + ["move_abs", 'move_home', 'move_rel',
                                                'get_actuator_value', 'stop_motion', 'position_is',
                                                'move_done']
    socket_types = ["ACTUATOR"]
    params = [
    ] + comon_parameters_fun(is_multiaxes=is_multiaxes, axes_names=axes_names) + leco_parameters

    def __init__(self, parent=None, params_state=None, **kwargs) -> None:
        super().__init__(parent=parent,
                         params_state=params_state, **kwargs)
        self.register_rpc_methods((
            self.set_info,
            self.set_position,
            self.set_move_done,
            self.set_x_axis,
            self.set_y_axis,
        ))

        # copied, I think it is good:
        self.settings.child('bounds').hide()
        self.settings.child('scaling').hide()
        self.settings.child('epsilon').setValue(1)

    def commit_settings(self, param) -> None:
        self.commit_leco_settings(param=param)

    def ini_stage(self, controller=None):
        """Actuator communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator by controller
            (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        actor_name = self.settings.child("actor_name").value()
        self.controller = self.ini_stage_init(  # type: ignore
            old_controller=controller,
            new_controller=ActuatorDirector(actor=actor_name, communicator=self.communicator),
            )
        try:
            self.controller.set_remote_name(self.communicator.full_name)  # type: ignore
        except TimeoutError:
            print("Timeout setting remote name.")  # TODO change to real logging
        # self.settings.child('infos').addChildren(self.params_client)

        self.settings.child('units').hide()
        self.settings.child('epsilon').hide()

        self.status.info = "LECODirector"
        self.status.controller = self.controller
        self.status.initialized = True
        return self.status

    def move_abs(self, position: DataActuator) -> None:
        position = self.check_bound(position)
        position = self.set_position_with_scaling(position)

        self.controller.move_abs(position=position)

        self.target_value = position

    def move_rel(self, position: DataActuator) -> None:
        position = self.check_bound(self.current_value + position) - self.current_value  # type: ignore  # noqa
        self.target_value = position + self.current_value

        position = self.set_position_relative_with_scaling(position)
        self.controller.move_rel(position=position)

    def move_home(self):
        self.controller.move_home()

    def get_actuator_value(self) -> DataActuator:
        """
        Get the current hardware position with scaling conversion given by
        `get_position_with_scaling`.

        See Also
        --------
            daq_move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        self.controller.set_remote_name(self.communicator.full_name)  # to ensure communication
        self.controller.get_actuator_value()
        return self._current_value

    def stop_motion(self) -> None:
        """
            See Also
            --------
            daq_move_base.move_done
        """
        self.controller.stop_motion()

    # Methods accessible via remote calls
    def _set_position_value(self, position: Union[str, float]) -> DataActuator:
        if isinstance(position, str):
            deserializer = DeSerializer.from_b64_string(position)
            pos = deserializer.dwa_deserialization()
        else:
            pos = DataActuator(data=position)
        pos = self.get_position_with_scaling(pos)  # type: ignore
        self._current_value = pos
        return pos

    def set_position(self, position: Union[str, float]) -> None:
        pos = self._set_position_value(position=position)
        self.emit_status(ThreadCommand('get_actuator_value', [pos]))

    def set_move_done(self, position: Union[str, float]) -> None:
        pos = self._set_position_value(position=position)
        self.emit_status(ThreadCommand('move_done', [pos]))

    def set_x_axis(self, data, label: str = "", units: str = "") -> None:
        raise NotImplementedError("where is it handled?")

    def set_y_axis(self, data, label: str = "", units: str = "") -> None:
        raise NotImplementedError("where is it handled?")


if __name__ == '__main__':
    main(__file__)

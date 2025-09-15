"""
LECO Director instrument plugin are to be used to communicate (and control) remotely real
instrument plugin through TCP/IP using the LECO Protocol

For this to work a coordinator must be instantiated can be done within the dashboard or directly
running: `python -m pyleco.coordinators.coordinator`

"""

import numpy as np

from typing import Optional, Union

from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, comon_parameters_fun, main,
                                                          DataActuatorType, DataActuator)
from pymodaq.control_modules.thread_commands import ThreadStatus, ThreadStatusMove

from pymodaq_utils.utils import ThreadCommand
from pymodaq_utils.utils import find_dict_in_list_from_key_val
from pymodaq_utils.serialize.factory import SerializableFactory
from pymodaq_gui.parameter import Parameter

from pymodaq.utils.leco.leco_director import (LECODirector, leco_parameters, DirectorCommands,
                                              DirectorReceivedCommands)
from pymodaq.utils.leco.director_utils import ActuatorDirector

from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))


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
    controller: Optional[ActuatorDirector]
    _axis_names = ['']
    _controller_units = ['']
    _epsilon = 1

    params_client = []  # parameters of a client grabber
    data_actuator_type = DataActuatorType.DataActuator
    params = comon_parameters_fun(axis_names=_axis_names, epsilon=_epsilon) + leco_parameters

    for param_name in ('multiaxes', 'units', 'epsilon', 'bounds', 'scaling'):
        param_dict = find_dict_in_list_from_key_val(params, 'name', param_name)
        if param_dict is not None:
            param_dict['visible'] = False

    def __init__(
        self, parent=None, params_state=None, host: Optional[str] = None, port: Optional[int] = None, **kwargs
    ) -> None:
        DAQ_Move_base.__init__(self, parent=parent, params_state=params_state)
        if host is not None:
            self.settings["host"] = host
        if port is not None:
            self.settings["port"] = port
        LECODirector.__init__(self, host=self.settings["host"], port=self.settings["port"])
        self.register_rpc_methods((
            self.set_units,  # to set units accordingly to the one of the actor
        ))

        self.register_binary_rpc_methods((
            self.send_position,  # to display the actor position
            self.set_move_done,  # to set the move as done
        ))
        self.start_timer()
        # To distinguish how to encode positions, it needs to now if it deals
        # with a json-accepting or a binary-accepting actuator
        # It is set to False by default. It then use the first received message
        # from the actuator that should contain its position to decide if it
        # need to switch to json.
        self.json = False

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
        actor_name = self.settings["actor_name"]

        if self.is_master:
            self.controller = ActuatorDirector(actor=actor_name, communicator=self.communicator)
            try:
                self.controller.set_remote_name(self.communicator.full_name)
            except TimeoutError:
                logger.warning("Timeout setting remote name.")
        else:
            self.controller = controller

        self.json = False
        # send a command to the Actor whose name is actor_name to send its settings
        self.controller.get_settings()

        info = f"LECODirector: {self._title} is initialized"
        initialized = True
        return info, initialized

    def move_abs(self, position: DataActuator) -> None:
        position = self.check_bound(position)
        position = self.set_position_with_scaling(position)
        self.target_value = position
        if self.json:
            # if it's 0D, just send the position as a scalar
            if hasattr(self, 'shape') and self.shape == ():
                position = position.value(self.axis_unit)
            else:
                # Until the GUI allows for it (next line), we send the single value repeated
                # position = [data.m_as(self.axis_unit) for data in position.quantities]
                position = np.full(self.shape, position.value(self.axis_unit)).tolist()
        self.controller.move_abs(position=position)

    def move_rel(self, position: DataActuator) -> None:
        position = self.check_bound(self.current_value + position) - self.current_value  # type: ignore  # noqa
        self.target_value = position + self.current_value

        position = self.set_position_relative_with_scaling(position)
        if self.json:
            # if it's 0D, just send the position as a scalar
            if hasattr(self, 'ndim') and self.shape == ():
                position = position.value(self.axis_unit)
            else:
                # Until the GUI allows for it (next line), we send the single value repeated
                #position = [data.m_as(self.axis_unit) for data in position.quantities]
                position = np.full(self.shape, position.value(self.axis_unit)).tolist()

        self.controller.move_rel(position=position)

    def move_home(self):
        self.controller.move_home()

    def get_actuator_value(self) -> DataActuator:
        """ Get the current hardware value """
        self.controller.get_actuator_value()
        return self._current_value

    def stop_motion(self) -> None:
        """
        """
        self.controller.stop_motion()

    # Methods accessible via remote calls
    def _set_position_value(
        self, data: Union[dict, list, str, float, None], additional_payload=None
    ) -> DataActuator:

        # This is the first received message, if position is set then
        # it's included in the json payload and the director should
        # usejson


        if data is not None:
            position = data.get('position', [])

            self.shape = np.array(position).shape
            position = [np.atleast_1d(position)]

            pos = DataActuator(data=position)
            self.json = True
        elif additional_payload:
            pos = SerializableFactory().get_apply_deserializer(additional_payload[0])
        else:
            raise ValueError("No position given")
        pos = self.get_position_with_scaling(pos)  # type: ignore
        self._current_value = pos
        return pos

    def send_position(self, data: Union[dict, list, str, float, None], additional_payload=None) -> None:
        pos = self._set_position_value(data=data, additional_payload=additional_payload)
        self.emit_status(ThreadCommand(ThreadStatusMove.GET_ACTUATOR_VALUE, pos))

    def set_move_done(self, data: Union[dict, list, str, float, None], additional_payload=None) -> None:
        pos = self._set_position_value(data=data, additional_payload=additional_payload)
        self.emit_status(ThreadCommand(ThreadStatusMove.MOVE_DONE, pos))

    def set_units(self, units: str, additional_payload=None) -> None:
        if units not in self.axis_units:
            self.axis_units.append(units)
        self.axis_unit = units

    def set_director_settings(self, settings: bytes):
        """ Get the content of the actor settings to pe populated in this plugin
        'settings_client' parameter

        Then set the plugin units from this information"""
        super().set_director_settings(settings)
        self.axis_unit = self.settings['settings_client', 'units']

    def close(self) -> None:
        """ Clear the content of the settings_clients setting"""
        super().close()


if __name__ == '__main__':
    main(__file__, init=False)

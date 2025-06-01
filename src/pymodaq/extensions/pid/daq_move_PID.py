from collections import deque
import numpy as np

from pymodaq_utils.utils import ThreadCommand

from pymodaq.control_modules.move_utility_classes import (
    DAQ_Move_base,
    DataActuator,
    DataActuatorType,
    comon_parameters_fun,
)
from pymodaq.extensions.pid.actuator_controller import PIDController


class DAQ_Move_PID(DAQ_Move_base):
    """ """

    _controller_units = ""
    data_actuator_type = DataActuatorType.DataActuator
    is_multiaxes = False
    stage_names = [
        "",
    ]
    params = [  # elements to be added in order to control your custom stage
        {
            "title": "Check stability:",
            "name": "check_stab",
            "type": "bool",
            "value": False,
            "default": "False",
            "tip": "Activate to only trigger move_done once ready",
            "children": [
                {
                    "title": "Stable:",
                    "name": "is_stab",
                    "type": "led",
                    "value": False,
                    "default": False,
                },
                {
                    "title": "Threshold:",
                    "name": "threshold",
                    "type": "float",
                    "value": 0.1,
                    "default": 0.1,
                    "min": 0,
                },
                {
                    "title": "Queue length:",
                    "name": "stab_queue",
                    "type": "int",
                    "default": 10,
                    "value": 50,
                    "min": 0,
                },
                {
                    "title": "Clear queue:",
                    "name": "clear_queue",
                    "type": "bool",
                    "default": False,
                    "value": False,
                },
            ],
        },
    ] + comon_parameters_fun(is_multiaxes, stage_names, master=False)
    # params = comon_parameters_fun(is_multiaxes, stage_names, master=False)

    def ini_attributes(self):
        self.controller: PIDController = None
        self.last_positions = deque(maxlen=self.settings["check_stab","stab_queue"])

    def update_position(self, dict_val: dict):
        self.current_value = dict_val[self.parent.title]

    def get_actuator_value(self):
        self.controller.emit_curr_points.emit()
        pos = self.current_value
        self.last_positions.append(np.squeeze( self.current_value.data))
        return pos

    def close(self):
        pass

    def user_condition_to_reach_target(self):
        cond = super().user_condition_to_reach_target()
        parameter_stab = self.settings.child("check_stab")
        if parameter_stab.value():
            cond = np.std(np.array(self.last_positions)-np.squeeze(self.target_value.data)) < parameter_stab["threshold"]
        return cond

    def commit_settings(self, param):
        if param.name() == "check_stab":
            pass
        elif param.name() == "stab_queue":
            self.last_positions = deque(self.last_positions, maxlen=param.value())

    def ini_stage(self, controller: PIDController = None):
        """ """
        self.controller = controller

        self.controller.curr_point.connect(self.update_position)

        info = "PID stage"
        initialized = True
        return info, initialized

    def move_abs(self, position: DataActuator):
        """ """
        position = self.check_bound(position)
        self.target_value = position

        self.controller.setpoint.emit({self.parent.title: self.target_value})

    def move_rel(self, position: DataActuator):
        """ """
        position = self.check_bound(self.current_value + position) - self.current_value
        self.target_value = position + self.current_value

        self.controller.setpoint.emit({self.parent.title: self.target_value})
        self.poll_moving()

    def move_home(self):
        """ """
        self.emit_status(ThreadCommand("Update_Status", ["Move Home not implemented"]))

    def stop_motion(self):
        """
        Call the specific move_done function (depending on the hardware).

        See Also
        --------
        move_done
        """
        self.move_done()

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
            "tooltip": "Activate to only trigger move_done once standard deviation over queue length is below threshold",
            "children": [
                {
                    "title": "Stable:",
                    "name": "is_stab",
                    "type": "led",
                    "value": False,
                    "default": False,
                    "tooltip": "Red if the standard deviation of the last positions is above threshold, green if below",
                },
                {
                    "title": "Current stability:",
                    "name": "current_stab",
                    "type": "float",
                    "value": 0,
                    "default": 0,
                    "readonly": True,
                    "tooltip": "",
                },
                {
                    "title": "Threshold:",
                    "name": "threshold",
                    "type": "float",
                    "value": 0.1,
                    "default": 0.1,
                    "min": 0,
                    "tooltip": "Standard deviation threshold to consider the stage stable",
                },
                {
                    "title": "Queue length:",
                    "name": "queue_length",
                    "type": "int",
                    "default": 10,
                    "value": 50,
                    "min": 0,
                    "tooltip": "Length of the queue used to compute the standard deviation for stability check",
                },
            ],
        },
    ] + comon_parameters_fun(is_multiaxes, stage_names, master=False)
    # params = comon_parameters_fun(is_multiaxes, stage_names, master=False)

    def ini_attributes(self):
        self.controller: PIDController = None
        self.last_positions = deque(maxlen=self.settings["check_stab", "queue_length"])

    def update_position(self, dict_val: dict):
        self.current_value = dict_val[self.parent.title]

    def get_actuator_value(self):
        self.controller.emit_curr_points.emit()
        pos = self.current_value
        return pos

    def close(self):
        pass

    def user_condition_to_reach_target(self):
        cond = super().user_condition_to_reach_target()
        parameter_stab = self.settings.child("check_stab")

        if parameter_stab.value():
            if len(self.controller.queue_points) >= self.settings["check_stab", "queue_length"]:
                self.last_positions = deque(
                    self.controller.queue_points, maxlen=self.settings["check_stab", "queue_length"]
                )
                current_stab = np.std(self.last_positions)
                parameter_stab.child("current_stab").setValue(current_stab)
                cond = current_stab <= parameter_stab["threshold"]
            else:
                cond = False

            parameter_stab.child("is_stab").setValue(cond)

        return cond

    def commit_settings(self, param):
        if param.name() == "check_stab":
            pass
        elif param.name() == "queue_length":
            self.last_positions = deque(
                self.controller.queue_points, maxlen=self.settings["check_stab", "queue_length"]
            )
            param.setOpts(max=self.controller.queue_points.maxlen)

    def ini_stage(self, controller: PIDController = None):
        """ """
        self.controller = controller
        self.controller.curr_point.connect(self.update_position)

        self.settings.child("check_stab", "queue_length").setValue(self.controller.queue_points.maxlen)

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

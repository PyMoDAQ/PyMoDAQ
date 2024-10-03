from pymodaq_utils.utils import ThreadCommand

from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, comon_parameters_fun,
                                                          DataActuatorType, DataActuator)

from pymodaq.extensions.pid.actuator_controller import PIDController


class DAQ_Move_PID(DAQ_Move_base):
    """
    """
    _controller_units = ''
    data_actuator_type = DataActuatorType.DataActuator
    is_multiaxes = False
    stage_names = ['',]

    params = comon_parameters_fun(is_multiaxes, stage_names, master=False)

    def ini_attributes(self):
        self.controller: PIDController = None

    def update_position(self, dict_val: dict):
        self.current_value = dict_val[self.parent.title]

    def get_actuator_value(self):
        self.controller.emit_curr_points.emit()
        pos = self.current_value
        return pos

    def close(self):
        pass

    def commit_settings(self, param):
        pass

    def ini_stage(self, controller=None):
        """
        """
        self.controller = controller

        self.controller.curr_point.connect(self.update_position)

        info = "PID stage"
        initialized = True
        return info, initialized

    def move_abs(self, position: DataActuator):
        """
        """
        position = self.check_bound(position)
        self.target_position = position

        self.controller.setpoint.emit({self.parent.title: self.target_position})

    def move_rel(self, position: DataActuator):
        """
        """
        position = self.check_bound(self.current_value + position) - self.current_value
        self.target_position = position + self.current_value

        self.controller.setpoint.emit({self.parent.title: self.target_position})
        self.poll_moving()

    def move_home(self):
        """
        """
        self.emit_status(ThreadCommand('Update_Status', ['Move Home not implemented']))

    def stop_motion(self):
        """
          Call the specific move_done function (depending on the hardware).

          See Also
          --------
          move_done
        """
        self.move_done()

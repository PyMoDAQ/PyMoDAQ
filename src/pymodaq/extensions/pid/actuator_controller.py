from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pid_controller import DAQ_PID


class PIDController:
    """ Fake controller object for the DAQ_Move_PID"""

    def __init__(self, daq_pid: 'DAQ_PID'):
        self.curr_point = daq_pid.curr_points_signal
        self.setpoint = daq_pid.setpoints_signal
        self.emit_curr_points = daq_pid.emit_curr_points_sig
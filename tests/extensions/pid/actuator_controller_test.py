from pymodaq.extensions.pid.actuator_controller import PIDController
from pymodaq.extensions.pid.pid_controller import DAQ_PID


def test_PIDController_attributes():

    assert hasattr(DAQ_PID, 'curr_points_signal')
    assert hasattr(DAQ_PID, 'setpoints_signal')
    assert hasattr(DAQ_PID, 'emit_curr_points_sig')

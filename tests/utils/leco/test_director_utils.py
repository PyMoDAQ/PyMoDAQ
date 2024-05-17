
import pytest

try:
    from pyleco.test import FakeDirector

    from pymodaq.utils.leco.director_utils import ActuatorDirector, DetectorDirector
    from pymodaq.utils.leco.pymodaq_listener import MoveActorHandler, ViewerActorHandler


    class FakeActuatorDirector(FakeDirector, ActuatorDirector):
        """Replaces the ask_rpc method."""


    class FakeDetectorDirector(FakeDirector, DetectorDirector):
        """Replaces the ask_rpc method."""


    @pytest.fixture
    def actuator_director():
        data_logger_director = FakeActuatorDirector(remote_class=MoveActorHandler)
        return data_logger_director


    @pytest.fixture
    def detector_director():
        data_logger_director = FakeDetectorDirector(remote_class=ViewerActorHandler)
        return data_logger_director


    @pytest.mark.parametrize("method", (  # "set_info param",
                                        "move_rel 5",
                                        "move_abs 10",
                                        "move_home",
                                        ))
    def test_method_call_existing_remote_methods_act(actuator_director: FakeActuatorDirector, method):
        """Test that the remote method exists."""
        actuator_director.return_value = None
        m, *args = method.split()
        getattr(actuator_director, m)(*args)
        # asserts that no error is raised in the "ask_rpc" method


    @pytest.mark.parametrize("method", (  # "set_info param",
                                        "send_data",
                                        ))
    def test_method_call_existing_remote_methods_det(detector_director: FakeDetectorDirector, method):
        """Test that the remote method exists."""
        detector_director.return_value = None
        m, *args = method.split()
        getattr(detector_director, m)(*args)
        # asserts that no error is raised in the "ask_rpc" method

except ImportError:
    pass
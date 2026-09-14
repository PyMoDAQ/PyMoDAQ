
import pymodaq_scripting.devices as devices


def test_has_devices():
    assert hasattr(devices, 'Actuator')
    assert hasattr(devices, 'Detector')
    assert hasattr(devices, 'Dashboard')
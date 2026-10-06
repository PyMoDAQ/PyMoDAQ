import pytest

from pymodaq.control_modules.capabilities import control, measurement
from pymodaq.control_modules.controller import Controller, controller_class


def test_quantity_named_like_a_controller_attribute_is_rejected():
    class Clashing:
        read = measurement(units='V')

    with pytest.raises(ValueError, match="'read'"):
        controller_class(Clashing)


def test_quantity_named_like_an_instance_attribute_is_rejected():
    class Clashing:
        settings = control(units='V')

    with pytest.raises(ValueError, match="'settings'"):
        controller_class(Clashing)


def test_controller_class_is_cached_per_device_class():
    class Device:
        position = control(units='mm')

    assert controller_class(Device) is controller_class(Device)
    assert issubclass(controller_class(Device), Controller)
    assert isinstance(controller_class(Device).position, property)


def test_status_is_a_valid_quantity_name():
    from pymodaq.control_modules.capabilities import measurement

    class Device:
        status = measurement(values=['idle', 'running'])

    assert isinstance(getattr(controller_class(Device), 'status'), property)


def test_a_name_clash_leaves_no_hardware_thread_behind():
    from pymodaq.control_modules.capabilities import measurement
    from pymodaq.control_modules.hardware_registry import HardwareKey, HardwareRegistry

    class Device:
        read = measurement()  # 'read' is a Controller method

    registry = HardwareRegistry()
    key = HardwareKey(hardware_class=Device, controller_id=0)
    with pytest.raises(ValueError, match='clash'):
        registry.attach(key, Device)
    assert not registry.is_known(key)

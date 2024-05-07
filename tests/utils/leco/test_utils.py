
import pytest

from pymodaq.control_modules.daq_move import DataActuator

from pymodaq.utils.leco.utils import serialize_object


@pytest.mark.parametrize("value", (
        5,
        6.7,
        "some value",
))
def test_native_json_object(value):
    assert serialize_object(value) == value


def test_data_actuator():
    value = DataActuator(data=10.5)
    serialized = serialize_object(value)
    assert isinstance(serialized, str)

from __future__ import annotations
from typing import Any

import pytest

from pymodaq.control_modules.daq_move import DataActuator
from pymodaq.utils.daq_utils import ThreadCommand

from pymodaq.utils.leco.utils import serialize_object, thread_command_to_leco_tuple, leco_tuple_to_thread_command, create_leco_transfer_tuple


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


@pytest.mark.parametrize("obj, tup", (
        (7, (7, [])),
        (1+2j, (None, [b"\x00\x00\x00\x06scalar\x00\x00\x00\x04<c16\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\xf0?\x00\x00\x00\x00\x00\x00\x00@"]))
))
def test_create_leco_transfer_tuple(obj: Any, tup: tuple[Any, list[bytes]]):
    assert create_leco_transfer_tuple(obj) == tup


class Test_thread_command_leco_tuple_conversion:

    test_tuples: list[tuple[ThreadCommand, tuple[dict, list[bytes]]]] = [
        (
            ThreadCommand(command="command", attribute=[7]),
            ({"type": "ThreadCommand", "command": "command", "attribute": [7]}, []),
        ),
        (
            ThreadCommand(command="binary", attribute=[1 + 2j]),
            (
                {"type": "ThreadCommand", "command": "binary", "attribute": [None], "binary": [0]},
                [
                    b"\x00\x00\x00\x06scalar\x00\x00\x00\x04<c16\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\xf0?\x00\x00\x00\x00\x00\x00\x00@"
                ],
            ),
        ),
    ]

    @pytest.mark.parametrize("tc, tup", test_tuples)
    def test_to_tuple(self, tc, tup):
        assert thread_command_to_leco_tuple(tc) == tup

    @pytest.mark.parametrize("tc, tup", test_tuples)
    def test_to_tc(self, tc, tup):
        assert leco_tuple_to_thread_command(*tup) == tc

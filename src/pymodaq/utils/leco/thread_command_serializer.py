"""
(De)Serialze ThreadCommands to be sent via LECO
"""

from __future__ import annotations
from enum import IntEnum
from typing import Any, get_args

from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import Parameter, ioxml
from pymodaq.utils.tcp_ip.serializer import SERIALIZABLE, Serializer, DeSerializer  # type: ignore  # noqa
from .utils import JSON_TYPES


class BinaryTypes(IntEnum):
    PARAMETER = 1
    SERIALIZER = 2



def thread_command_to_leco_tuple(thread_command: ThreadCommand) -> tuple[dict[str, Any], list[bytes]]:
    """Convert a thread_command to a dictionary and a list of bytes."""
    d: dict[str, Any] = {"type": "ThreadCommand", "command": thread_command.command}
    b: list[bytes] = []
    binary_dict: list[tuple[int, int]] = []
    if thread_command.attribute is None:
        pass
    elif isinstance(thread_command.attribute, list):
        # quite often it is a list of attributes
        for i, el in enumerate(thread_command.attribute):
            if isinstance(el, get_args(JSON_TYPES)):
                continue
            elif isinstance(el, Parameter):
                b.append(ioxml.parameter_to_xml_string(el))
                binary_dict.append((i, BinaryTypes.PARAMETER))
                thread_command.attribute[i] = None
            elif isinstance(el, get_args(SERIALIZABLE)):
                b.append(Serializer(el).to_bytes())
                binary_dict.append((i, BinaryTypes.SERIALIZER))
                thread_command.attribute[i] = None
        d["binary"] = binary_dict
        d["attribute"] = thread_command.attribute
    return d, b


def leco_tuple_to_thread_command(command_dict: dict[str, Any], additional: list[bytes]) -> ThreadCommand:
    """Convert a leco tuple to a ThreadCommand."""
    assert command_dict.pop("type") == "ThreadCommand", "The message is not a ThreadCommand!"
    binary = command_dict.pop("binary", [])
    attribute = command_dict.pop("attribute", None)
    for i, item in enumerate(binary):
        position, b_type = item
        if b_type == BinaryTypes.SERIALIZER:
            attribute[position] = DeSerializer(additional[i]).object_deserialization()
        elif b_type == Parameter:
            attribute[position] = ioxml.XML_string_to_parameter


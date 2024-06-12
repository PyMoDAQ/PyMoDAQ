from __future__ import annotations
import subprocess
import sys
from typing import Any, Union, get_args

# import also the DeSerializer for easier imports in dependents
from pymodaq.utils.tcp_ip.serializer import SERIALIZABLE, Serializer, DeSerializer  # type: ignore  # noqa
from pymodaq.utils.logger import set_logger
from pymodaq.utils.daq_utils import ThreadCommand


logger = set_logger('leco_utils')

JSON_TYPES = Union[str, int, float]


def serialize_object(pymodaq_object: Union[SERIALIZABLE, Any]) -> Union[str, Any]:
    """Serialize a pymodaq object, if it is not JSON compatible."""
    if isinstance(pymodaq_object, get_args(JSON_TYPES)):
        return pymodaq_object
    elif isinstance(pymodaq_object, get_args(SERIALIZABLE)):
        return Serializer(pymodaq_object).to_b64_string()
    else:
        raise ValueError(f"{pymodaq_object} of type '{type(pymodaq_object).__name__}' is neither "
                         "JSON serializable, nor via PyMoDAQ.")


def create_leco_transfer_tuple(pymodaq_object: Union[SERIALIZABLE, Any]) -> tuple[Any, list[bytes]]:
    """Create a tuple to send via LECO, either directly or binary encoded."""
    if isinstance(pymodaq_object, get_args(JSON_TYPES)):
        return pymodaq_object, []
    elif isinstance(pymodaq_object, get_args(SERIALIZABLE)):
        return None, [Serializer(pymodaq_object).to_bytes()]
    else:
        raise ValueError(f"{pymodaq_object} of type '{type(pymodaq_object).__name__}' is neither "
                         "JSON serializable, nor via PyMoDAQ.")


def thread_command_to_dict(thread_command: ThreadCommand) -> dict[str, Any]:
    return {
        "type": "ThreadCommand",
        "command": thread_command.command,
        "attribute": thread_command.attribute,
    }


def thread_command_to_leco_tuple(thread_command: ThreadCommand) -> tuple[dict[str, Any], list[bytes]]:
    """Convert a thread_command to a dictionary and a list of bytes."""
    d: dict[str, Any] = {"type": "ThreadCommand", "command": thread_command.command}
    b: list[bytes] = []
    binary_dict: list[int] = []
    if thread_command.attribute is None:
        pass
    elif isinstance(thread_command.attribute, list):
        # quite often it is a list of attributes
        attribute = thread_command.attribute.copy()
        for i, el in enumerate(attribute):
            if isinstance(el, get_args(JSON_TYPES)):
                continue
            elif isinstance(el, get_args(SERIALIZABLE)):
                b.append(Serializer(el).to_bytes())
                binary_dict.append(i)
                attribute[i] = None
        d["binary"] = binary_dict
        d["attribute"] = attribute
    return d, b


def leco_tuple_to_thread_command(command_dict: dict[str, Any], additional: list[bytes]) -> ThreadCommand:
    """Convert a leco tuple to a ThreadCommand."""
    assert command_dict.pop("type") == "ThreadCommand", "The message is not a ThreadCommand!"
    binary = command_dict.pop("binary", [])
    attribute = command_dict.pop("attribute", None)
    for i, position in enumerate(binary):
        attribute[position] = DeSerializer(
            additional[i]
        ).type_and_object_deserialization()
    return ThreadCommand(attribute=attribute, **command_dict)


def run_coordinator():
    command = [sys.executable, '-m', 'pyleco.coordinators.coordinator']
    subprocess.Popen(command)


def run_proxy_server() -> None:
    command = [sys.executable, "-m", "pyleco.coordinators.proxy_server"]
    subprocess.Popen(command)


def start_coordinator():
    from pyleco.directors.director import Director
    try:
        with Director(actor="COORDINATOR") as director:
            if director.communicator.namespace is None:
                run_coordinator()
            else:
                logger.info('Coordinator already running')
    except ConnectionRefusedError as e:
        run_coordinator()
        run_proxy_server()


from __future__ import annotations
from base64 import b64encode
import subprocess
import sys
from typing import Any, Optional, Union, get_args

from typing import Any, Optional, Union, get_args, TypeVar

from pymodaq.utils import data
from pymodaq_utils.serialize.factory import SerializableFactory

from pymodaq_utils.logger import set_logger


logger = set_logger('leco_utils')
JSON_TYPES = Union[str, int, float]

ser_factory = SerializableFactory()

SERIALIZABLE = Union[ser_factory.get_serializables()]


def serialize_object(pymodaq_object: Union[SERIALIZABLE, Any]) -> Union[str, Any]:
    """Serialize a pymodaq object, if it is not JSON compatible."""
    if isinstance(pymodaq_object, get_args(JSON_TYPES)):
        return pymodaq_object
    binary = SerializableFactory().get_apply_serializer(pymodaq_object)
    return b64encode(binary).decode()


def binary_serialization(
    pymodaq_object: Union[SERIALIZABLE, Any],
) -> tuple[Optional[Any], Optional[list[bytes]]]:
    """Serialize (binary) a pymodaq object, if it is not JSON compatible."""
    if isinstance(pymodaq_object, get_args(JSON_TYPES)):
        return pymodaq_object, None
    return None, [SerializableFactory().get_apply_serializer(pymodaq_object)]



def binary_serialization_to_kwargs(
    pymodaq_object: Union[SERIALIZABLE, Any], data_key: str = "data"
) -> dict[str, Any]:
    """Create a dictionary of data parameters and of additional payload to send."""
    d, b = binary_serialization(pymodaq_object=pymodaq_object)
    return {data_key: d, "additional_payload": b}


def run_coordinator():
    command = [sys.executable, '-m', 'pyleco.coordinators.coordinator']
    subprocess.Popen(command)


def start_coordinator():
    from pyleco.directors.director import Director
    try:
        with Director(actor="COORDINATOR") as director:
            if director.communicator.namespace is None:
                run_coordinator()
            else:
                logger.info('Coordinator already running')
    except ConnectionRefusedError:
        run_coordinator()

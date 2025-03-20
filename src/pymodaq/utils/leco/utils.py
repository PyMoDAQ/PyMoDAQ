from __future__ import annotations
import subprocess
import sys
from typing import Any, Optional, Union, get_args, TypeVar

from pymodaq.utils import data
# import also the DeSerializer for easier imports in dependents
from pymodaq_utils.serialize.serializer_legacy import Serializer, DeSerializer, SerializableFactory

# type: ignore  # noqa
from pymodaq_utils.logger import set_logger


logger = set_logger('leco_utils')
ser_factory = SerializableFactory()
JSON_TYPES = Union[str, int, float]



def serialize_object(pymodaq_object: Union[SERIALIZABLE, Any]) -> Union[str, Any]:
    """Serialize a pymodaq object, if it is not JSON compatible."""
    if isinstance(pymodaq_object, get_args(JSON_TYPES)):
        return pymodaq_object
    else:
        return Serializer(pymodaq_object).to_b64_string() # will raise a proper error if the object
    #is not serializable


## this form below is to be compatible with python <= 3.10
## for py>= 3.11 this could be written SERIALIZABLE = Union[ser_factory.get_serializables()]
SERIALIZABLE = Union[ser_factory.get_serializables()[0]]
for klass in ser_factory.get_serializables()[1:]:
    SERIALIZABLE = Union[SERIALIZABLE, klass]


def binary_serialization(
    pymodaq_object: Union[SERIALIZABLE, Any],
) -> tuple[Optional[Any], Optional[list[bytes]]]:
    """Serialize (binary) a pymodaq object, if it is not JSON compatible."""
    if isinstance(pymodaq_object, get_args(JSON_TYPES)):
        return pymodaq_object, None
    elif isinstance(pymodaq_object, get_args(SERIALIZABLE)):
        return None, [Serializer(pymodaq_object).to_bytes()]
    else:
        raise ValueError(
            f"{pymodaq_object} of type '{type(pymodaq_object).__name__}' is neither "
            "JSON serializable, nor via PyMoDAQ."
        )


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
    except ConnectionRefusedError as e:
        run_coordinator()


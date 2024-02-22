import subprocess
import sys
from typing import Any, Union

# import also the DeSerializer for easier imports in dependents
from pymodaq.utils.tcp_ip.serializer import SERIALIZABLE, Serializer, DeSerializer  # type: ignore  # noqa


JSON_TYPES = Union[str, int, float]


def serialize_object(pymodaq_object: Union[SERIALIZABLE, Any]) -> Union[str, Any]:
    """Serialize a pymodaq object, if it is not JSON compatible."""
    if isinstance(pymodaq_object, JSON_TYPES):
        return pymodaq_object
    elif isinstance(pymodaq_object, SERIALIZABLE):
        return Serializer(pymodaq_object).to_b64_string()
    else:
        raise ValueError(f"{pymodaq_object} of type '{type(pymodaq_object).__name__}' is neither "
                         "JSON serializable, nor via PyMoDAQ.")


def start_coordinator():
    from pyleco.directors.director import Director

    with Director(actor="COORDINATOR") as director:
        if director.communicator.namespace is None:
            command = [sys.executable, '-m', 'pyleco.coordinators.coordinator']
            subprocess.run(command, shell=True)

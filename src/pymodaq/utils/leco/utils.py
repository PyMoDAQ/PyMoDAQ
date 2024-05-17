import subprocess
import sys
from typing import Any, Union, get_args

# import also the DeSerializer for easier imports in dependents
from pymodaq.utils.tcp_ip.serializer import SERIALIZABLE, Serializer, DeSerializer  # type: ignore  # noqa
from pymodaq.utils.logger import set_logger


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


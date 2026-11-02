"""Read legacy pickled content without being able to run code

PyMoDAQ used to store some data (strings in .h5 files, dock layouts) with pickle, which can run arbitrary
code when loaded. New files do not use pickle anymore, this module only exists so that legacy files can
still be read: only plain data (str, bytes, numbers, tuples, lists, dicts, sets...) is rebuilt, any
attempt to reference another object is refused.
"""
import io
import pickle
from typing import Any

# The few non-primitive builtins/stdlib objects a legitimate legacy file may contain
_ALLOWED_GLOBALS = {
    ('collections', 'OrderedDict'),
    ('builtins', 'set'),
    ('builtins', 'frozenset'),
    ('builtins', 'complex'),
    ('builtins', 'bytearray'),
}


class UnsafePickleError(pickle.UnpicklingError):
    """Raised when legacy content tries to build something else than plain data"""


class _RestrictedUnpickler(pickle.Unpickler):
    def __init__(self, file, extra_allowed=()):
        super().__init__(file)
        self._allowed = _ALLOWED_GLOBALS | set(extra_allowed)

    def find_class(self, module: str, name: str):
        if (module, name) in self._allowed:
            return super().find_class(module, name)
        raise UnsafePickleError(f'Refused to load {module}.{name} from legacy content: only plain data '
                                f'is allowed')

    def persistent_load(self, pid):
        raise UnsafePickleError('Refused to load an external object reference from legacy content')


def restricted_loads(data: bytes, extra_allowed=()) -> Any:
    """Equivalent of pickle.loads restricted to plain data, raises UnsafePickleError otherwise

    Parameters
    ----------
    data: bytes
    extra_allowed: iterable of (module name, object name)
        Other harmless objects that the content may refer to
    """
    return _RestrictedUnpickler(io.BytesIO(data), extra_allowed).load()


def restricted_load(file, extra_allowed=()) -> Any:
    """Equivalent of pickle.load restricted to plain data, raises UnsafePickleError otherwise"""
    return _RestrictedUnpickler(file, extra_allowed).load()

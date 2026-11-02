"""Read legacy pickled content without being able to run code

PyMoDAQ used to store some data (strings in .h5 files, dock layouts) with pickle, which can run arbitrary
code when loaded. New files do not use pickle anymore, this module only exists so that legacy files can
still be read: only plain data (str, bytes, numbers, tuples, lists, dicts, sets...) is rebuilt, any
attempt to reference another object is refused.
"""
import io
import pickle
import warnings
from typing import Any

# The few non-primitive builtins/stdlib objects a legitimate legacy file may contain
_ALLOWED_GLOBALS = {
    ('collections', 'OrderedDict'),
    ('builtins', 'set'),
    ('builtins', 'frozenset'),
    ('builtins', 'complex'),
    ('builtins', 'bytearray'),
}


class LegacyFormatWarning(UserWarning):
    """Emitted when a file is read in a legacy format that should be migrated"""


def warn_legacy_format(what: str):
    """Tell the user that what is read uses a legacy format and how to migrate it

    Python shows a given warning once, so the user is not flooded when a file holds many legacy values
    """
    warnings.warn(LegacyFormatWarning(f'{what} was written in a legacy format (pickle) by an older version of '
                                      f'PyMoDAQ. It is still read, but you should migrate it with the '
                                      f'pymodaq_migrate command, and only keep files from sources you trust.'),
                  stacklevel=3)


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

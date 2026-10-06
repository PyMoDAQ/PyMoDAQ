"""Contextual help of the PyMoDAQ modules.

By convention, the help of a module (control module, manager, extension...) is a short markdown text stored in a file
named ``help.md`` in the same folder as the python file defining the module. The same text is used as the introduction
of the module documentation.
"""
import inspect
from pathlib import Path
from types import ModuleType
from typing import Optional, Union

from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))

HELP_FILE_NAME = 'help.md'


def get_help_text(obj: Union[type, object, ModuleType, str, Path]) -> Optional[str]:
    """Get the markdown help text associated with a module, a class or an object

    Parameters
    ----------
    obj: type, object, ModuleType, str or Path
        A class, an instance, a python module, or the path of a file (or a folder) from which the help is looked for.
        The help file is ``help.md`` in the folder of the file defining the object.

    Returns
    -------
    str or None
        The markdown text, None if no help file is found.
    """
    if isinstance(obj, (str, Path)):
        path = Path(obj)
    else:
        if not isinstance(obj, (type, ModuleType)):
            obj = type(obj)
        try:
            path = Path(inspect.getfile(obj))
        except (TypeError, OSError):
            logger.warning(f'Could not find the source file of {obj}')
            return None

    help_path = (path if path.is_dir() else path.parent) / HELP_FILE_NAME
    if not help_path.is_file():
        return None
    return help_path.read_text(encoding='utf-8')

# -*- coding: utf-8 -*-
"""Actions run when a file written by PyMoDAQ is opened or really closed.

The backends call :meth:`FileActions.notify_opened` when a file is opened to write and
:meth:`FileActions.notify_closed` when it is closed for good (not when ``finalize_swmr``
keeps it open to write more). Anything that has to react to a finished file, such as
copying it to a storage server, registers here and does not need to know the savers.
"""
from pathlib import Path
import threading
from typing import Callable, Dict, List, NamedTuple, Optional

from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))

FileEvent = Callable[[Path], None]  # what an action calls: it receives the path of the file


class FileAction(NamedTuple):
    """The two callables of an action, either of them can be None"""
    on_opened: Optional[FileEvent] = None
    on_closed: Optional[FileEvent] = None


class FileActions:
    """Registry of the actions run on file events, kept by name

    An action is made of two optional callables receiving the :class:`~pathlib.Path` of the
    file: ``on_opened`` and ``on_closed``. They are called in the thread that opens or closes
    the file, so they should return quickly and hand long work to a thread of their own.
    A failing action is logged and never stops the saving.
    """
    _actions: Dict[str, FileAction] = {}  # the registered actions, by name
    _lock = threading.RLock()  # actions can be registered while a file is closed in another thread

    @classmethod
    def register(cls, name: str, on_closed: Optional[FileEvent] = None,
                 on_opened: Optional[FileEvent] = None):
        """Register (or replace) the action called ``name``"""
        with cls._lock:
            cls._actions[name] = FileAction(on_opened, on_closed)

    @classmethod
    def unregister(cls, name: str):
        with cls._lock:
            cls._actions.pop(name, None)

    @classmethod
    def names(cls) -> List[str]:
        with cls._lock:
            return list(cls._actions)

    @classmethod
    def notify_opened(cls, path: Path):
        """Run the ``on_opened`` callables: a file is open to write"""
        cls._notify('on_opened', path)

    @classmethod
    def notify_closed(cls, path: Path):
        """Run the ``on_closed`` callables: a file written by PyMoDAQ is closed"""
        cls._notify('on_closed', path)

    @classmethod
    def _notify(cls, event: str, path: Path):
        """Call, for each action, its ``on_opened`` or ``on_closed`` callable (``event`` is that name)"""
        with cls._lock:
            actions = list(cls._actions.items())  # a copy: an action may register another one

        for name, action in actions:
            fun = getattr(action, event)
            if fun is None:
                continue
            try:
                fun(Path(path))
            except Exception as e:  # an action must not stop the saving, nor the other actions
                logger.warning(f'The action "{name}" failed on the {event} event of {path}: {e}')

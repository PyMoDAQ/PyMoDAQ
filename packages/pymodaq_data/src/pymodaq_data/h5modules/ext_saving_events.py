# -*- coding: utf-8 -*-
"""Events sent when an extension starts and ends a saving (a scan, a logging, a ramp...)

An extension that saves data (see :class:`~pymodaq.utils.h5modules.module_saving.ExtensionSaver`) tells the
registered actions when a saving starts and when it ends. An action receives a :class:`ExtSavingInfo` and can, for
instance, create an entry in an electronic lab notebook, then update it. The action does not need to know
the extensions: it only reads the information given in the :class:`ExtSavingInfo`.

The files themselves are announced by :class:`~pymodaq_data.h5modules.file_actions.FileActions`, not here.
"""
import dataclasses
from datetime import datetime
from pathlib import Path
import threading
from types import MappingProxyType
from typing import Any, Callable, Dict, List, Mapping, Optional
import uuid

from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))


def iso_now() -> str:
    """The current time in ISO 8601 with the offset to UTC, for instance ``2026-11-27T15:04:05+01:00``"""
    return datetime.now().astimezone().isoformat(timespec='seconds')


def freeze(value: Any) -> Any:
    """A copy of a value that cannot be modified: dicts become read-only mappings, lists tuples and sets frozensets

    Other values are returned as they are, they should be simple (text, numbers, booleans...).
    """
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze(item) for item in value)
    return value


@dataclasses.dataclass(frozen=True)
class ExtSavingInfo:
    """What is known about a saving. It cannot be modified: the end of a saving gets a new one, made with :meth:`ended`

    Attributes
    ----------
    saving_id: str
        Identifies the saving, the same one at its start and at its end
    extension: str
        Title of the extension that does the saving
    h5_path: Path, optional
        The h5 file in which the data of the saving are written
    started_at: str
        ISO 8601 time with the offset to UTC, taken when the saving started
    ended_at: str, optional
        Same, taken when the saving ended. None while the saving is going on
    payload: Mapping
        Free information given by the extension (see ``CustomApp.saving_payload``), for instance the scan type. It is a
        read-only copy, so a listener cannot change what the others receive
    snapshot_path: Path, optional
        A PNG picture of the extension at the end of the saving, None if there is none
    """
    extension: str
    h5_path: Optional[Path] = None
    payload: Mapping[str, Any] = dataclasses.field(default_factory=dict)
    saving_id: str = dataclasses.field(default_factory=lambda: uuid.uuid4().hex)
    started_at: str = dataclasses.field(default_factory=iso_now)
    ended_at: Optional[str] = None
    snapshot_path: Optional[Path] = None

    def __post_init__(self):
        object.__setattr__(self, 'payload', freeze(self.payload))  # a frozen dataclass is set with object.__setattr__

    def ended(self, snapshot_path: Optional[Path] = None) -> 'ExtSavingInfo':
        """The same saving, with its end time taken now and the picture taken at its end"""
        return dataclasses.replace(self, ended_at=iso_now(), snapshot_path=snapshot_path)


ExtSavingEvent = Callable[[ExtSavingInfo], None]  # what an action calls: it receives the information on the saving


@dataclasses.dataclass(frozen=True)
class ExtSavingAction:
    """The two functions of an action, each of them can be None. It cannot be modified once created"""
    on_started: Optional[ExtSavingEvent] = None
    on_ended: Optional[ExtSavingEvent] = None


class ExtSavingEvents:
    """List of the actions to call when an extension starts or ends a saving, each one has a name

    As :class:`~pymodaq_data.h5modules.file_actions.FileActions`, the class is used directly, as a registry,
    and is never instantiated. The functions are called in the thread of the extension, so they should return
    quickly and give a long work to a thread of their own. If an action fails, the error is logged and the
    saving continues.
    """
    _actions: Dict[str, ExtSavingAction] = {}  # the registered actions, by name
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        raise TypeError(f'{cls.__name__} is a registry: use its class methods, do not create an instance')

    @classmethod
    def register(cls, name: str, on_started: Optional[ExtSavingEvent] = None, on_ended: Optional[ExtSavingEvent] = None):
        """Register (or replace) the action called ``name``"""
        with cls._lock:
            cls._actions[name] = ExtSavingAction(on_started, on_ended)

    @classmethod
    def unregister(cls, name: str):
        with cls._lock:
            cls._actions.pop(name, None)

    @classmethod
    def names(cls) -> List[str]:
        with cls._lock:
            return list(cls._actions)

    @classmethod
    def notify_started(cls, info: ExtSavingInfo):
        """Run the ``on_started`` functions: a run has just started"""
        cls._notify('on_started', info)

    @classmethod
    def notify_ended(cls, info: ExtSavingInfo):
        """Run the ``on_ended`` functions: a run is over and its file is closed"""
        cls._notify('on_ended', info)

    @classmethod
    def _notify(cls, event: str, info: ExtSavingInfo):
        with cls._lock:
            actions = list(cls._actions.items())  # a copy: an action may register another one

        for name, action in actions:
            fun = getattr(action, event)
            if fun is None:
                continue
            try:
                fun(info)
            except Exception as e:  # an action must not stop the saving, nor the other actions
                logger.warning(f'The action "{name}" failed on the {event} event of the saving of '
                               f'{info.extension}: {e}')

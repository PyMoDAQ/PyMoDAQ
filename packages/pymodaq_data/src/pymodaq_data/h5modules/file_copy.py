# -*- coding: utf-8 -*-
"""Automatic copy of the closed h5 files to another folder (a NAS for instance)

What happens to a file
----------------------
1. PyMoDAQ closes the h5 file. The :class:`~pymodaq_data.h5modules.file_actions.FileActions` registry
   tells the copier (:meth:`FileCopier.on_closed`).
2. The copier does not copy at once: PyMoDAQ sometimes closes a file and opens it again to write more
   (to update attributes for instance). It starts a timer of ``delay`` seconds instead. If the file is
   opened again meanwhile, the timer is cancelled (:meth:`FileCopier.on_opened`) and a new one starts at
   the next close. So a file is copied once, ``delay`` seconds after its last close.
3. When the timer ends, the copy is made in the thread of the timer (:meth:`FileCopier._run`).
   The local file is never moved nor deleted. The copy is written under a temporary name
   (``.part``) then replaces the previous copy of the file, so the destination mirrors the last version
   and does not keep a history.
4. Two checks protect the copy:

   * the sha256 of the copy, computed again by reading it, must be the one of what was read from the file;
   * the size and modification time of the file must be the same before and after the copy, otherwise
     the file was written to meanwhile and the copy starts again (at most :data:`MAX_ATTEMPTS` times).

5. A copy that fails (destination not reachable, file locked...) is logged, sent to the listeners and
   remembered in a small file of the configuration folder (``pending_copies.json``). It is tried again the
   next time the copier is enabled, which is at the start of PyMoDAQ if the copy is enabled in the
   configuration.
6. The copies still planned when PyMoDAQ stops are made at once (see :meth:`FileCopier.flush`).

Where the copies go
-------------------
``destination`` is the folder, as seen from this computer, where the copies are written. ``url_prefix`` is
not used to copy: it only builds the web or network address of a copy for other people and programs
(an electronic lab notebook for instance), by being put before the path of the copy relative to the base path
of the ``H5Saver``. For a ``destination`` of ``/mnt/nas/data`` and a ``url_prefix`` of ``smb://nas/data``, the
file ``<base path>/20261126/Dataset_000.h5`` is written to ``/mnt/nas/data/20261126/Dataset_000.h5`` and its url is
``smb://nas/data/20261126/Dataset_000.h5``.
"""
import atexit
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import threading
from typing import BinaryIO, Callable, Dict, Iterator, List, Optional, Tuple, Union
from urllib.parse import quote

from pymodaq_utils.config import GlobalConfig as Config, get_set_config_dir
from pymodaq_utils.logger import set_logger, get_module_name

from .file_actions import FileActions

config = Config()
logger = set_logger(get_module_name(__file__))

CHUNK_SIZE = 4 * 1024 * 1024  # bytes read at once, big files are never loaded entirely in memory
MAX_ATTEMPTS = 3  # number of tries when the file keeps changing during the copy
PENDING_FILE_NAME = 'pending_copies.json'  # in the configuration folder
ACTION_NAME = 'copy'  # name of the copier in the FileActions registry

# What identifies a version of a file without reading it: its size and modification time in nanoseconds
FileSignature = Tuple[int, int]


class CopyError(Exception):
    """A copy that could not be made or checked"""


@dataclasses.dataclass
class CopyResult:
    """What a copy did, sent to the listeners

    ``error`` is None when the copy succeeded, in which case ``destination``, ``sha256`` and
    ``url`` (None without a url prefix) describe the copy.
    """
    source: Path
    destination: Optional[Path] = None
    sha256: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


# ---------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------

def read_chunks(file: BinaryIO) -> Iterator[bytes]:
    """Yield the content of an open binary file piece by piece"""
    while True:
        chunk = file.read(CHUNK_SIZE)
        if not chunk:
            return
        yield chunk


def sha256_of(path: Path) -> str:
    """The sha256 of a file, as a hexadecimal string"""
    digest = hashlib.sha256()
    with open(path, 'rb') as file:
        for chunk in read_chunks(file):
            digest.update(chunk)
    return digest.hexdigest()


def signature_of(path: Path) -> FileSignature:
    """Size and modification time of a file: they change if the file is written to"""
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


class FileCopier:
    """Copies the files it is told are closed to a destination folder

    Parameters
    ----------
    enabled: bool
        if False nothing is copied
    destination: str or Path
        the folder, as seen from this computer, receiving the copies
    url_prefix: str
        what is put before the relative path of a copy to build its url (``smb://nas/data``). It is not
        used to copy. No url is built when empty
    delay: float
        seconds to wait after the last close of a file before copying it
    source_root: str or Path, optional
        folder from which the relative path of the copies is taken, usually the base path of an
        H5Saver (see :meth:`add_source_root` to give several). Outside of the source roots the last
        folder and the name of the file are kept
    """

    def __init__(self, enabled: bool = False, destination: Union[str, Path] = '', url_prefix: str = '',
                 delay: float = 30., source_root: Union[str, Path, None] = None):
        # the timers run in other threads: everything below that they share is protected by this lock
        self._lock = threading.RLock()
        self._timers: Dict[Path, threading.Timer] = {}  # planned copies, by file
        self._open: set = set()  # files known to be open right now
        self._listeners: List[Callable[[CopyResult], None]] = []

        self.enabled = False
        self.destination = destination
        self.url_prefix = url_prefix
        self.delay = delay
        self.source_roots: List[Path] = []
        if source_root:
            self.add_source_root(source_root)
        self.configure(enabled=enabled)  # not set above so that enabling retries the failed copies

    @classmethod
    def from_config(cls) -> 'FileCopier':
        """A copier set from the ``data_saving.copy`` section of the configuration"""
        return cls(enabled=config('data', 'data_saving', 'copy', 'enabled'),
                   destination=config('data', 'data_saving', 'copy', 'destination_path'),
                   url_prefix=config('data', 'data_saving', 'copy', 'url_prefix'),
                   delay=config('data', 'data_saving', 'copy', 'delay'))

    def configure(self, **kwargs):
        """Change any of the parameters of the constructor, by name

        Enabling the copier tries again, in a thread, the copies that failed earlier.
        """
        enabled = kwargs.pop('enabled', None)
        for name in kwargs:
            if name not in ('destination', 'url_prefix', 'delay'):
                raise TypeError(f'Unknown copy parameter: {name}')

        with self._lock:
            for name, value in kwargs.items():
                setattr(self, name, value)
            was_enabled = self.enabled
            if enabled is not None:
                self.enabled = bool(enabled)

        if self.enabled and not was_enabled:
            self.retry_pending_in_thread()

    def add_source_root(self, path: Union[str, Path]):
        """Add a folder from which the relative path of the copied files is taken (the base path of
        an H5Saver). The deepest one containing a file is used."""
        path = Path(path).resolve()
        with self._lock:
            if path not in self.source_roots:
                self.source_roots.append(path)

    def add_listener(self, fun: Callable[[CopyResult], None]):
        """``fun`` receives a :class:`CopyResult` after each copy, from the thread making the copy"""
        self._listeners.append(fun)

    def remove_listener(self, fun: Callable[[CopyResult], None]):
        if fun in self._listeners:
            self._listeners.remove(fun)

    # -----------------------------------------------------------------------------------------
    # file events: called by the FileActions registry
    # -----------------------------------------------------------------------------------------

    def on_opened(self, path: Path):
        """A file is open again: its planned copy, if any, is cancelled"""
        path = Path(path)
        with self._lock:
            self._open.add(path)
            planned = self._timers.pop(path, None)
        if planned is not None:
            planned.cancel()

    def on_closed(self, path: Path):
        """A file is closed: plan its copy ``delay`` seconds later, replacing any earlier plan"""
        path = Path(path)
        with self._lock:
            self._open.discard(path)
            if not self.enabled or not str(self.destination):
                return

            earlier_plan = self._timers.pop(path, None)
            if earlier_plan is not None:
                earlier_plan.cancel()

            timer = threading.Timer(self.delay, self._run, args=(path,))
            timer.daemon = True  # a pending copy must not keep PyMoDAQ from stopping, flush() deals with it
            self._timers[path] = timer
            timer.start()

    def flush(self):
        """Copy now, in this thread, the files whose copy is planned (at the exit of PyMoDAQ)"""
        with self._lock:
            planned = dict(self._timers)
            self._timers.clear()
        for path, timer in planned.items():
            timer.cancel()
            self._run(path, from_timer=False)

    # -----------------------------------------------------------------------------------------
    # where a copy goes
    # -----------------------------------------------------------------------------------------

    def relative_path(self, path: Path) -> Path:
        """Path of a file below the deepest source root containing it, or its last folder and name"""
        path = Path(path)
        with self._lock:
            deepest_first = sorted(self.source_roots, key=lambda root: len(root.parts), reverse=True)
        for root in deepest_first:
            try:
                return path.resolve().relative_to(root)
            except ValueError:  # the file is not below this root
                continue
        return Path(path.parent.name) / path.name

    def destination_for(self, path: Path) -> Path:
        """Where the copy of a file is written"""
        return Path(self.destination) / self.relative_path(path)

    def url_for(self, path: Path) -> Optional[str]:
        """The url of the copy of a file, None if there is no url prefix"""
        if not self.url_prefix:
            return None
        return self.url_prefix.rstrip('/') + '/' + quote(self.relative_path(path).as_posix())

    # -----------------------------------------------------------------------------------------
    # the copy itself
    # -----------------------------------------------------------------------------------------

    def copy(self, path: Union[str, Path]) -> CopyResult:
        """Copy ``path`` now, in this thread. Raises :class:`CopyError` if it did not work"""
        path = Path(path)
        destination = self.destination_for(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + '.part')

        for _attempt in range(MAX_ATTEMPTS):
            signature_before = signature_of(path)

            if self._is_copied(destination, signature_before):
                return CopyResult(path, destination, sha256_of(destination), self.url_for(path))

            sha256_read = self._write_copy(path, temporary)

            if signature_of(path) != signature_before:
                continue  # the file was written to during the copy: start again

            if sha256_of(temporary) != sha256_read:
                temporary.unlink(missing_ok=True)
                raise CopyError(f'The copy of {path} is not identical to the file')

            self._finish_copy(path, temporary, destination)
            return CopyResult(path, destination, sha256_read, self.url_for(path))

        temporary.unlink(missing_ok=True)
        raise CopyError(f'{path} kept changing during the copy')

    @staticmethod
    def _is_copied(destination: Path, signature: FileSignature) -> bool:
        """True if the destination already holds this version of the file

        A copy gets the modification time of its file (see :meth:`_finish_copy`), so the same size and
        time mean the same version, without reading anything.
        """
        return destination.exists() and signature_of(destination) == signature

    @staticmethod
    def _write_copy(path: Path, temporary: Path) -> str:
        """Write the copy under its temporary name and return the sha256 of what was read"""
        digest = hashlib.sha256()
        with open(path, 'rb') as source, open(temporary, 'wb') as copy:
            for chunk in read_chunks(source):
                digest.update(chunk)
                copy.write(chunk)
        return digest.hexdigest()

    @staticmethod
    def _finish_copy(path: Path, temporary: Path, destination: Path):
        """Give the copy the modification time of its file, then put it in place of the previous copy"""
        stat = path.stat()
        os.utime(temporary, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        os.replace(temporary, destination)  # in one step: the destination never holds half a file

    def _run(self, path: Path, from_timer: bool = True):
        """Make the copy of a file and tell the listeners: what a timer does when it ends"""
        with self._lock:
            if from_timer:
                self._timers.pop(path, None)
            if path in self._open:
                return  # opened again since the copy was planned

        try:
            if not path.exists():
                raise CopyError(f'{path} does not exist anymore')
            result = self.copy(path)
            self._forget_pending(path)
        except Exception as e:
            logger.warning(f'The copy of {path} failed, it will be tried again at the next start: {e}')
            result = CopyResult(path, error=str(e))
            self._remember_pending(path)

        for listener in list(self._listeners):
            try:
                listener(result)
            except Exception as e:  # a listener must not stop the others
                logger.warning(f'A listener of the copies failed: {e}')

    # -----------------------------------------------------------------------------------------
    # the copies to try again: the paths of the files are kept in a json file
    # -----------------------------------------------------------------------------------------

    @staticmethod
    def pending_file() -> Path:
        return get_set_config_dir('data', user=True) / PENDING_FILE_NAME

    def _read_pending(self) -> List[str]:
        try:
            return list(json.loads(self.pending_file().read_text()))
        except (OSError, ValueError):  # no file yet, or not readable
            return []

    def _write_pending(self, paths: List[str]):
        try:
            self.pending_file().write_text(json.dumps(sorted(set(paths))))
        except OSError as e:
            logger.warning(f'The list of the copies to retry could not be saved: {e}')

    def _remember_pending(self, path: Path):
        with self._lock:
            self._write_pending(self._read_pending() + [str(path)])

    def _forget_pending(self, path: Path):
        with self._lock:
            paths = self._read_pending()
            if str(path) in paths:
                self._write_pending([other for other in paths if other != str(path)])

    def retry_pending(self):
        """Copy again, in this thread, the files whose copy failed during an earlier session"""
        with self._lock:
            paths = [Path(path) for path in self._read_pending()]

        for path in paths:
            if path in self._open:
                continue  # it will be copied after its next close
            if not path.exists():
                self._forget_pending(path)  # moved or deleted: nothing to copy anymore
                continue
            self._run(path, from_timer=False)

    def retry_pending_in_thread(self):
        threading.Thread(target=self.retry_pending, daemon=True, name='retry_pending_copies').start()


# The copier of the application: set from the configuration, and called when a file is opened or closed
copier = FileCopier.from_config()
FileActions.register(ACTION_NAME, on_closed=copier.on_closed, on_opened=copier.on_opened)
atexit.register(copier.flush)

# -*- coding: utf-8 -*-
"""Automatic copy of the closed h5 files to another folder (a NAS for instance)

A file is copied a few seconds after its last close: if it is opened again in the meantime
(PyMoDAQ sometimes reopens a file to update attributes) the copy is cancelled and planned
again at the next close. The copy never moves or deletes the local file.

The copy goes through a temporary name and replaces the previous copy once checked, so the
destination is a mirror and not a history. The checks are:

* the sha256 of the copy, computed again by reading it, equals the one of what was read;
* the size and modification time of the source did not change during the copy. If they did,
  the file was written meanwhile and the copy starts again.

A copy that fails (destination not reachable, file locked...) is logged, reported to the
listeners and kept in a small file of the configuration folder to be tried again the next
time the copier is enabled.
"""
import atexit
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import threading
from typing import Callable, Dict, List, Optional, Union
from urllib.parse import quote

from pymodaq_utils.config import GlobalConfig as Config, get_set_config_dir
from pymodaq_utils.logger import set_logger, get_module_name

from .file_actions import FileActions

config = Config()
logger = set_logger(get_module_name(__file__))

CHUNK_SIZE = 4 * 1024 * 1024
MAX_ATTEMPTS = 3
PENDING_FILE_NAME = 'pending_copies.json'
ACTION_NAME = 'copy'


class CopyError(Exception):
    pass


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


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b''):
            digest.update(chunk)
    return digest.hexdigest()


class FileCopier:
    """Copies the files it is told are closed to a destination folder

    Parameters
    ----------
    enabled: bool
        if False nothing is copied
    destination: str or Path
        the folder receiving the copies
    url_prefix: str
        what is put before the relative path of the copy to build its url (``smb://nas/data``).
        No url is built when empty
    delay: float
        seconds to wait after the last close of a file before copying it
    source_root: str or Path, optional
        folder from which the relative path of the copies is taken, usually the base path of an
        H5Saver (see :meth:`add_source_root` to give several). Outside of the source roots the last
        folder and the name of the file are kept
    """

    def __init__(self, enabled: bool = False, destination: Union[str, Path] = '', url_prefix: str = '',
                 delay: float = 30., source_root: Union[str, Path, None] = None):
        self._lock = threading.RLock()
        self._timers: Dict[Path, threading.Timer] = {}
        self._open: set = set()
        self._listeners: List[Callable[[CopyResult], None]] = []
        self.enabled = False
        self.destination = destination
        self.url_prefix = url_prefix
        self.delay = delay
        self.source_roots: List[Path] = []
        if source_root:
            self.add_source_root(source_root)
        self.configure(enabled=enabled)

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
        """``fun`` receives a :class:`CopyResult` after each copy, from the copy's thread"""
        self._listeners.append(fun)

    def remove_listener(self, fun: Callable[[CopyResult], None]):
        if fun in self._listeners:
            self._listeners.remove(fun)

    # events

    def on_opened(self, path: Path):
        """A file is open again: its planned copy is cancelled"""
        path = Path(path)
        with self._lock:
            self._open.add(path)
            timer = self._timers.pop(path, None)
        if timer is not None:
            timer.cancel()

    def on_closed(self, path: Path):
        """A file is closed: plan its copy ``delay`` seconds later"""
        path = Path(path)
        with self._lock:
            self._open.discard(path)
            if not self.enabled or not str(self.destination):
                return
            timer = self._timers.pop(path, None)
            if timer is not None:
                timer.cancel()
            timer = threading.Timer(self.delay, self._run, args=(path,))
            timer.daemon = True
            self._timers[path] = timer
            timer.start()

    def flush(self):
        """Copy now, in this thread, the files whose copy is planned (at the exit of PyMoDAQ)"""
        with self._lock:
            paths = list(self._timers)
            timers = list(self._timers.values())
            self._timers.clear()
        for timer in timers:
            timer.cancel()
        for path in paths:
            self._run(path, from_timer=False)

    # copy

    def relative_path(self, path: Path) -> Path:
        path = Path(path)
        with self._lock:
            roots = sorted(self.source_roots, key=lambda root: len(root.parts), reverse=True)
        for root in roots:
            try:
                return path.resolve().relative_to(root)
            except ValueError:
                continue
        return Path(path.parent.name) / path.name

    def destination_for(self, path: Path) -> Path:
        return Path(self.destination) / self.relative_path(path)

    def url_for(self, path: Path) -> Optional[str]:
        if not self.url_prefix:
            return None
        return self.url_prefix.rstrip('/') + '/' + quote(self.relative_path(path).as_posix())

    def copy(self, path: Union[str, Path]) -> CopyResult:
        """Copy ``path`` now, in this thread. Raises :class:`CopyError` if it did not work"""
        path = Path(path)
        dest = self.destination_for(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + '.part')
        for _ in range(MAX_ATTEMPTS):
            before = path.stat()
            if dest.exists():
                dest_stat = dest.stat()
                if (dest_stat.st_size, dest_stat.st_mtime_ns) == (before.st_size, before.st_mtime_ns):
                    # same size and time: this is the copy made earlier, kept by the os.utime below
                    return CopyResult(path, dest, sha256_of(dest), self.url_for(path))
            digest = hashlib.sha256()
            with open(path, 'rb') as src, open(tmp, 'wb') as dst:
                for chunk in iter(lambda: src.read(CHUNK_SIZE), b''):
                    digest.update(chunk)
                    dst.write(chunk)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                continue  # written during the copy: start again
            if sha256_of(tmp) != digest.hexdigest():
                tmp.unlink(missing_ok=True)
                raise CopyError(f'The copy of {path} is not identical to the file')
            os.utime(tmp, ns=(after.st_atime_ns, after.st_mtime_ns))
            os.replace(tmp, dest)
            return CopyResult(path, dest, digest.hexdigest(), self.url_for(path))
        tmp.unlink(missing_ok=True)
        raise CopyError(f'{path} kept changing during the copy')

    def _run(self, path: Path, from_timer: bool = True):
        with self._lock:
            if from_timer:
                self._timers.pop(path, None)
            if path in self._open:
                return
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
            except Exception as e:
                logger.warning(f'A listener of the copies failed: {e}')

    # copies to try again

    @staticmethod
    def pending_file() -> Path:
        return get_set_config_dir('data', user=True) / PENDING_FILE_NAME

    def _read_pending(self) -> List[str]:
        try:
            return list(json.loads(self.pending_file().read_text()))
        except (OSError, ValueError):
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
                self._write_pending([p for p in paths if p != str(path)])

    def retry_pending(self):
        """Copy again, in this thread, the files whose copy failed during an earlier session"""
        with self._lock:
            paths = [Path(p) for p in self._read_pending()]
        for path in paths:
            if path in self._open:
                continue
            if not path.exists():
                self._forget_pending(path)
                continue
            self._run(path, from_timer=False)

    def retry_pending_in_thread(self):
        threading.Thread(target=self.retry_pending, daemon=True, name='retry_pending_copies').start()


copier = FileCopier.from_config()
FileActions.register(ACTION_NAME, on_closed=copier.on_closed, on_opened=copier.on_opened)
atexit.register(copier.flush)

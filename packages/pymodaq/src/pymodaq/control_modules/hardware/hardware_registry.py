"""Share one hardware thread between the subscribers of a physical device.

A :class:`HardwareRegistry` maps a :class:`HardwareKey` to the hardware thread that owns
the plugin, and to the settings tree the GUI shows for it.  The first :meth:`attach` for a
key creates the thread; later attaches share it.  :meth:`detach` removes one subscriber, and
the last one stops the thread.
"""
from __future__ import annotations

import gc
import threading
from dataclasses import dataclass
from typing import Any, ClassVar

from pymodaq.control_modules.hardware.capabilities import Capabilities
from pymodaq.control_modules.hardware.controller import controller_class
from pymodaq.control_modules.hardware.hardware_thread import HardwareThread, make_plugin_settings
from pymodaq_utils.logger import set_logger, get_module_name
from qtpy import QtCore

logger = set_logger(get_module_name(__file__))

__all__ = ['HardwareKey', 'HardwareRegistry']


@dataclass(frozen=True)
class HardwareKey:
    """Identity of one physical device.

    Parameters
    ----------
    hardware_class :
        The plugin's ``hardware_class`` if it declares one (several plugins can drive the same
        hardware), otherwise the plugin class itself.
    controller_id :
        User-assigned integer that tells apart two devices of the same hardware class.
    """

    hardware_class: type
    controller_id: int


@dataclass
class _Entry:
    thread: Any                 # HardwareThread (Any allows test doubles)
    controller: Any             # the GUI-side Controller that subscribers use
    plugin_class: type
    ref_count: int = 1


class HardwareRegistry:
    """Map a :class:`HardwareKey` to its hardware thread and settings.

    Thread-safe for concurrent attach and detach.  Use the process-wide instance from
    :meth:`get`; tests create their own with ``HardwareRegistry()``.
    """

    _global: ClassVar[HardwareRegistry | None] = None
    _global_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        self._entries: dict[HardwareKey, _Entry] = {}
        self._lock = threading.Lock()

    @classmethod
    def get(cls) -> HardwareRegistry:
        """Return the process-wide registry, and close its devices when the application quits."""
        with cls._global_lock:
            if cls._global is None:
                cls._global = cls()
                import qtpy.QtWidgets as QtWidgets
                app = QtWidgets.QApplication.instance()
                if app is not None:
                    app.aboutToQuit.connect(cls._global.close_all)
            return cls._global

    @classmethod
    def _reset_global(cls) -> None:
        """Forget the process-wide registry. For tests only; close devices with :meth:`close_all` first."""
        with cls._global_lock:
            cls._global = None

    def attach(self, key: HardwareKey, plugin_class: type, params_state: dict | None = None) -> Any:
        """Return the :class:`Controller` of *key*, creating the hardware thread on first use.

        ``params_state`` is only used by the first attach.  A later attach must use the same
        plugin class, since one device has one plugin.
        """
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None:
                if entry.plugin_class is not plugin_class:
                    raise ValueError(f'{key} is already attached with {entry.plugin_class.__name__}, '
                                     f'not {plugin_class.__name__}')
                entry.ref_count += 1
                return entry.controller
            # Build the class before the thread starts: a quantity name clash raises here.
            cls = controller_class(plugin_class)
            settings = make_plugin_settings(plugin_class, params_state)
            thread = self._make_thread(plugin_class, params_state)
            controller = cls(thread, settings, Capabilities.from_device(plugin_class))
            self._entries[key] = _Entry(thread=thread, controller=controller, plugin_class=plugin_class)
            return controller

    def detach(self, key: HardwareKey) -> None:
        """Release one reference to *key*. The last one stops its hardware thread."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return
            entry.ref_count -= 1
            if entry.ref_count > 0:
                return
            del self._entries[key]
        self._teardown(entry)

    def ref_count(self, key: HardwareKey) -> int:
        with self._lock:
            entry = self._entries.get(key)
            return entry.ref_count if entry is not None else 0

    def is_known(self, key: HardwareKey) -> bool:
        with self._lock:
            return key in self._entries

    def close_all(self) -> None:
        """Stop every hardware thread, whatever its reference count. Used at application quit."""
        with self._lock:
            entries = list(self._entries.values())
            self._entries.clear()
        for entry in entries:
            self._teardown(entry)

    def _make_thread(self, plugin_class: type, params_state: dict | None) -> Any:
        """Create a ``HardwareThread`` for *plugin_class*, move it to a new QThread and start the thread.

        The plugin is created later, by ``ini_hardware``, so the caller can connect signals first.
        Tests override this method to inject a double.

        ``gc.collect()`` runs first, deliberately: starting a QThread while Python's cyclic GC
        happens to sweep a leftover, thread-affinitized QTimer/QThread from some earlier, unrelated
        device - its own cleanup already correct, just not yet collected - was found to crash
        (reproduced on Linux/PySide6; see device_module_status.md). Collecting first, on this
        thread, before a new one starts, keeps that collection from ever racing a thread's startup.
        """
        gc.collect()
        thread_obj = HardwareThread(plugin_class, params_state)
        qt_thread = QtCore.QThread()
        thread_obj.moveToThread(qt_thread)
        thread_obj.parent_qt_thread = qt_thread  # keeps the QThread referenced while it runs
        qt_thread.start()
        return thread_obj

    def _teardown(self, entry: _Entry) -> None:
        """Stop the hardware thread of *entry*. Called without the registry lock held.

        Hardware is closed on the hardware thread, through a blocking queued call, then the
        QThread is asked to quit and *unconditionally* waited for - never just for up to some
        bound and then given up on. Returning while it might still be running would leave its
        QObject/QTimer children affinitized to a thread nothing then confirms is dead: garbage
        collected at some later, unrelated moment, from whatever thread that GC pass happens to
        run on - exactly what Qt's own cross-thread-deletion guards exist to catch (this used to
        be handled by stashing the pair in a list "to keep it referenced", but that list dies
        with this registry the moment the caller drops it, same problem one step removed). A
        thread whose QThread has already stopped has no event loop left to run the close, so it
        is skipped.

        The BlockingQueuedConnection call below is skipped entirely when *thread_obj* already
        lives on the calling thread - not as a shortcut, but because that connection type
        deadlocks when caller and target share a thread (it blocks until the target's event loop
        processes the call, and the caller is the one that would have to pump it). In production
        every entry's thread is moveToThread()'d in _make_thread, so this only triggers for a
        test double that skips that step - but the check itself is Qt's own thread-identity
        rule, not a test-only carve-out.

        A move-back-to-the-main-thread fix was tried here (and inside close_hardware) and
        reverted: moveToThread() must be called from the object's own current thread, so it has
        to happen from inside close_hardware - but changing self's own thread affinity from
        within a slot that is itself running via BlockingQueuedConnection corrupts Qt's own
        return-to-caller bookkeeping for that call, breaking later, unrelated
        QMetaObject.invokeMethod() calls (confirmed: this regressed PyQt6, previously 100%
        reliable, to a different fatal crash). See device_module_status.md.
        """
        entry.controller.close()
        thread_obj = entry.thread
        if thread_obj.thread() is QtCore.QThread.currentThread():
            thread_obj.close_hardware()
            return
        qt_thread = thread_obj.parent_qt_thread  # kept referenced here so it isn't GC'd mid-run
        if not qt_thread.isRunning():
            return
        QtCore.QMetaObject.invokeMethod(
            thread_obj, 'close_hardware', QtCore.Qt.ConnectionType.BlockingQueuedConnection)
        qt_thread.quit()
        if not qt_thread.wait(2000):
            logger.warning('Hardware thread taking longer than 2 s to stop; waiting for it to finish')
            qt_thread.wait()

"""GUI-side handle to one device.

A :class:`Controller` is created by the registry for each device. It talks to the device's
:class:`~pymodaq.control_modules.hardware.hardware_thread.HardwareThread` through signals only, so the
plugin is only ever called on the hardware thread. Each declared measurement or control becomes a
property: a control's setter queues a write, and a getter returns the latest value received.
"""
from __future__ import annotations

import functools
import threading

from qtpy.QtCore import QObject, QTimer, Qt, Signal

from pymodaq_utils.config import GlobalConfig as Config
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq.control_modules.hardware.capabilities import Access, Capabilities, Quantity
from pymodaq.control_modules.hardware.subscription import Subscription

__all__ = ['Controller', 'controller_class']

logger = set_logger(get_module_name(__file__))
config = Config()

# Defaults come from config_template.toml's [hardware_module] section; both stay plain module
# globals (not inlined where used) so a test can still monkeypatch them directly, as before.
WRITE_TIMEOUT_S = config('pymodaq', 'hardware_module', 'write_timeout_s')
READ_TIMEOUT_S = config('pymodaq', 'hardware_module', 'read_timeout_s')


def _quantity_property(quantity: Quantity) -> property:
    name = quantity.name

    def getter(self: Controller):
        return self._last_values.get(name)

    if quantity.access is Access.CONTROL:
        def setter(self: Controller, value):
            self.write_requested.emit(name, value)

        return property(getter, setter, doc=quantity.docs)
    return property(getter, doc=quantity.docs)


class Controller(QObject):
    """One per device. Created by the registry, before the device is initialised.

    The controller must exist before ``ini_hardware`` runs, so that it receives the status
    that announces the device is open.
    """

    write_requested = Signal(str, object)      # → thread.request_write
    action_requested = Signal(str, str, object)  # → thread.request_action: (channel, action name, checked)
    subscribe_requested = Signal(object)       # → thread.subscribe
    unsubscribe_requested = Signal(object)     # → thread.unsubscribe
    device_status = Signal(bool, str)          # ← thread.hardware_status
    device_error = Signal(str)                 # ← thread.error: an operation failed, the device is still open
    written = Signal(str, object)              # ← thread.write_done: (name, value) after a write succeeded
    write_failed = Signal(str, str)            # ← thread.write_failed: (name, message), the device is still open
    action_done = Signal(str, str, object)     # ← thread.action_done: (name, action name, result or None)
    action_failed = Signal(str, str, str)      # ← thread.action_failed: (name, action name, message)
    read_failed = Signal(str, str)             # ← thread.read_failed, or a read() that timed out
    new_reading = Signal(str, object, float)   # ← a poll's reading: (name, data, wall-clock read time)

    def __init__(self, thread, settings, capabilities: Capabilities, parent: QObject | None = None):
        super().__init__(parent)
        self.capabilities = capabilities
        self.settings = settings
        self.thread = thread
        self._connected = False
        self._syncing_from_device = False  # True while applying a setting the plugin changed itself
        self._last_values: dict[str, object] = {}
        self._polled: dict[str, Subscription] = {}
        # One-shot read()/read_blocking() subscriptions, kept alive here until released - see
        # _track_until_released.
        self._pending_reads: set[Subscription] = set()
        # Outstanding requests, one QTimer per (kind, name): started when sent, stopped by whichever
        # answer arrives first. Lives here, not in a GUI, so a script gets the same guarantee a widget
        # does - on timeout, write_failed/read_failed fire same as a real rejection would.
        self._timers: dict[tuple[str, str], QTimer] = {}
        self.write_requested.connect(thread.request_write)
        self.write_requested.connect(self._start_write_timeout)
        self.action_requested.connect(thread.request_action)
        self.subscribe_requested.connect(thread.subscribe)
        self.unsubscribe_requested.connect(thread.unsubscribe)
        thread.hardware_status.connect(self._on_status)
        thread.error.connect(self.device_error)
        thread.write_done.connect(self.written)
        thread.write_done.connect(self._stop_write_timeout)
        thread.write_failed.connect(self.write_failed)
        thread.write_failed.connect(self._stop_write_timeout)
        thread.action_done.connect(self.action_done)
        self.action_done.connect(self._on_action_done)
        thread.action_failed.connect(self.action_failed)
        thread.read_failed.connect(self.read_failed)
        thread.read_failed.connect(self._stop_read_timeout)
        thread.capabilities.connect(self._on_instance_capabilities)
        thread.settings_changed.connect(self._on_device_settings_changed)

    @property
    def connected(self) -> bool:
        return self._connected

    def _on_instance_capabilities(self, capabilities: Capabilities) -> None:
        """Keep the capabilities the plugin reported after open, for introspection. Attributes stay class-level."""
        self.capabilities = capabilities

    def _on_device_settings_changed(self, path: list, data: object, change: str) -> None:
        """Apply a setting the plugin changed itself. The flag stops it looping back as a GUI edit.

        *change* picks the matching ``Parameter`` method - lets e.g. a plugin discovering its real
        choices only once open update the Settings dock via ``setLimits()`` from inside its own
        ``open()``/``commit_settings``. ``'childAdded'``'s *data* is ``(state, pos)`` - a fresh
        ``Parameter`` built from *state* here, never the original object the thread serialized it
        from (see ``hardware_thread.py``'s ``_on_plugin_settings_changed``). Runs as a queued,
        cross-thread slot, so any failure is caught here rather than left to crash it.
        """
        self._syncing_from_device = True
        try:
            param = self.settings.child(*path)
            if change == 'value':
                param.setValue(data)
            elif change == 'limits':
                param.setLimits(data)
            elif change == 'options':
                param.setOpts(**data)
            elif change == 'childAdded':
                state, pos = data
                param.insertChild(pos, state, existOk=True)
        except Exception as exc:
            logger.exception(f'applying a device-driven settings change failed: {change!r}')
            self.device_error.emit(str(exc))
        finally:
            self._syncing_from_device = False

    def _on_status(self, connected: bool, info: str) -> None:
        self._connected = connected
        if not connected:
            self._polled.clear()  # the thread released these subscriptions when it closed the device
            for kind, name in list(self._timers):
                self._stop_timeout(kind, name)
        self.device_status.emit(connected, info)

    def _on_action_done(self, name: str, action_name: str, result: object) -> None:
        """An ``interrupts=True`` action resolves whatever write was in flight too."""
        quantity = self._quantity_named(name)
        action = quantity.actions.get(action_name) if quantity is not None else None
        if action is not None and action.interrupts:
            self._stop_write_timeout(name)

    def _quantity_named(self, name: str) -> Quantity | None:
        """The declared quantity called *name*, looked up fresh (capabilities can be replaced)."""
        for quantity in self.capabilities.measurements + self.capabilities.controls:
            if quantity.name == name:
                return quantity
        return None

    # ── Timeouts: one QTimer per (kind, name), started on request, stopped by whichever answer ──
    #
    # No lambda on the timeout connection: PyQt/PySide only auto-drops a connection once its
    # receiver is destroyed when that receiver is a bound method connected directly - a lambda
    # is just a generic callable to the binding, so it gets no such protection, and calling
    # through one into an already-destroyed Controller is exactly how this used to crash. kind/
    # name travel as Qt properties on the timer itself instead, read back via sender() in one
    # plain bound-method slot.

    def _start_timeout(self, kind: str, name: str, seconds: float) -> None:
        self._stop_timeout(kind, name)  # a new request replaces the wait, only the latest matters
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(int(seconds * 1000))
        timer.setProperty('kind', kind)
        timer.setProperty('name', name)
        timer.timeout.connect(self._on_timeout)
        self._timers[kind, name] = timer
        timer.start()

    def _stop_timeout(self, kind: str, name: str) -> None:
        timer = self._timers.pop((kind, name), None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def _on_timeout(self) -> None:
        timer = self.sender()
        kind, name = timer.property('kind'), timer.property('name')
        if (kind, name) not in self._timers:
            return  # the answer, an interrupting action, or a disconnect already ended the wait
        self._stop_timeout(kind, name)
        if kind == 'write':
            self.write_failed.emit(name, f'no response within {WRITE_TIMEOUT_S:.0f} s')
        else:
            self.read_failed.emit(name, f'no response within {READ_TIMEOUT_S:.0f} s')

    def _start_write_timeout(self, name: str, _value: object = None) -> None:
        self._start_timeout('write', name, WRITE_TIMEOUT_S)

    def _stop_write_timeout(self, name: str, _value: object = None) -> None:
        self._stop_timeout('write', name)

    def _start_read_timeout(self, name: str) -> None:
        self._start_timeout('read', name, READ_TIMEOUT_S)

    def _stop_read_timeout(self, name: str, _value: object = None) -> None:
        self._stop_timeout('read', name)

    def _require_open(self, name: str) -> None:
        if not self._connected:
            raise RuntimeError(f'cannot access {name!r}: the device is not open')

    def poll(self, name: str, period_ms: float, policy: str = 'latest') -> Subscription:
        """Read *name* every *period_ms* so that its property stays up to date.

        *policy* is :class:`Subscription`'s own: ``'latest'`` (the default - a slow consumer
        skips readings instead of queuing them, right for a display) or ``'all'`` (no reading is
        ever dropped, right for lossless recording - see ``Subscription``'s own docstring).
        Polling a name again with the same period and policy returns the same subscription;
        a different period or policy raises, since one physical poll can only honor one policy.
        Raises RuntimeError if the device is not open.
        """
        self._require_open(name)
        if name in self._polled:
            existing = self._polled[name]
            if existing.period_ms != period_ms:
                raise ValueError(f'{name!r} is already polled every {existing.period_ms} ms')
            if existing.policy != policy:
                raise ValueError(f'{name!r} is already polled with policy {existing.policy!r}')
            return existing
        sub = Subscription(name, period_ms, policy=policy)
        sub.on_data = lambda data, read_time: self._on_reading(name, data, read_time, sub)
        self._polled[name] = sub
        self.subscribe_requested.emit(sub)
        return sub

    def stop_poll(self, name: str) -> None:
        """Stop polling *name*. Its property keeps the last value received."""
        sub = self._polled.pop(name, None)
        if sub is not None:
            self.unsubscribe_requested.emit(sub)

    def run_action(self, name: str, action_name: str, checked: bool | None = None) -> None:
        """Call *name*'s declared *action_name* callback. A no-op if it has none. Raises if closed.

        *checked* is the button's new state for a ``checkable`` action, forwarded to the callback as
        its second argument; leave it ``None`` for a plain, non-checkable action.
        """
        self._require_open(name)
        self.action_requested.emit(name, action_name, checked)

    def stop(self, name: str) -> None:
        """Call *name*'s declared ``stop`` action. A no-op if it has none. Raises if the device is closed."""
        self.run_action(name, 'stop')

    def _track_until_released(self, sub: Subscription) -> None:
        """Keep a strong reference to a one-shot *sub* until the hardware thread releases it.

        Nothing else holds one once the ``read``/``read_blocking`` call that creates it returns,
        and a bound-method connection (``sub.data_ready`` -> ``sub._deliver``, see
        ``Subscription.__init__``) only weakly tracks its own receiver - exactly the protection
        ``_on_timeout``'s own comment describes, which here would silently drop the one reading
        this object exists for, before it ever arrives, instead of protecting anything.
        """
        self._pending_reads.add(sub)
        sub.released.connect(functools.partial(self._pending_reads.discard, sub))

    def read(self, name: str, on_value) -> Subscription:
        """Read *name* once, asynchronously: *on_value(data)* is called when the reading arrives."""
        self._require_open(name)
        self._start_read_timeout(name)
        sub = Subscription(name, None)

        def _on_value(data, _read_time):
            self._stop_read_timeout(name)
            on_value(data)

        sub.on_data = _on_value
        self._track_until_released(sub)
        self.subscribe_requested.emit(sub)
        return sub

    def read_blocking(self, name: str, timeout: float = 5.0):
        """Read *name* once and wait for the value. For scripts only: never call it from the hardware thread."""
        if self.thread.is_device_thread():
            raise RuntimeError('read_blocking would wait on the hardware thread that must answer it')
        self._require_open(name)
        done = threading.Event()
        result: dict[str, object] = {}

        def on_value(data, _read_time):
            result['value'] = data
            done.set()

        # auto_delete=False: a script thread has no event loop to run a queued deletion.
        # Direct: the hardware thread calls on_value itself, so the script thread needs no event loop.
        sub = Subscription(name, None, auto_delete=False, connection_type=Qt.ConnectionType.DirectConnection)
        sub.on_data = on_value
        self._track_until_released(sub)
        self.subscribe_requested.emit(sub)
        if not done.wait(timeout):
            raise TimeoutError(f'no reading of {name!r} within {timeout} s')
        return result['value']

    def close(self) -> None:
        """Stop every poll, fail any read still in flight, and stop any outstanding write/read-timeout wait.

        A read()/read_blocking() already queued on the hardware thread when this runs may still be
        answered - closing does not reach back to cancel it - but nothing here waits for that: a
        pending one-shot read is dropped and reported failed immediately, same as a real timeout.
        """
        for sub in self._polled.values():
            self.unsubscribe_requested.emit(sub)
        self._polled.clear()
        for sub in list(self._pending_reads):
            self.read_failed.emit(sub.channel, 'the device was closed')
        self._pending_reads.clear()
        for kind, name in list(self._timers):
            self._stop_timeout(kind, name)

    def _on_reading(self, name: str, data: object, read_time: float, sub: Subscription) -> None:
        self._last_values[name] = data
        self.new_reading.emit(name, data, read_time)


@functools.lru_cache(maxsize=None)
def controller_class(device_cls: type) -> type:
    """A :class:`Controller` subclass with one property per quantity declared on *device_cls*.

    A quantity may not reuse the name of an existing :class:`Controller` attribute, since the
    property would replace it.
    """
    caps = Capabilities.from_device(device_cls)
    quantities = caps.measurements + caps.controls
    reserved = set(dir(Controller)) | {'capabilities', 'settings', 'thread'}
    taken = sorted(q.name for q in quantities if q.name in reserved)
    if taken:
        raise ValueError(f'{device_cls.__name__}: quantity names {taken} clash with Controller attributes')
    attrs = {q.name: _quantity_property(q) for q in quantities}
    return type(f'{device_cls.__name__}Controller', (Controller,), attrs)

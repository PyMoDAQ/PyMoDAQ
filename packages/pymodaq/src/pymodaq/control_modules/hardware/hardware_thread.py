"""HardwareThread owns one plugin and serialises all access to it.

One ``HardwareThread`` lives in a dedicated ``QThread`` (see
:class:`~pymodaq.control_modules.hardware.hardware_registry.HardwareRegistry`).
Requests from GUI subscribers arrive as queued slot calls, so the plugin is never
called from two threads at once.

Plugins use the new API: ``open(settings)``, ``close()``, ``read(names, fresh)``,
``write(name, value)`` and optionally ``commit_settings(param)``.  Legacy
``DAQ_Move_base`` / ``DAQ_Viewer_base`` plugins are handled by the existing modules
and are not run in this thread.

Channels are named by the plugin's capabilities.  ``write_done`` carries the channel
name; readings go to the subscriptions that asked for them.
"""
from __future__ import annotations

import copy
import functools
import threading
import time
from typing import Any, Callable

from pymodaq.control_modules.hardware.capabilities import Capabilities
from pymodaq.control_modules.hardware.subscription import Subscription
from pymodaq_utils.logger import set_logger, get_module_name
from qtpy.QtCore import QObject, QSignalBlocker, QTimer, Signal, Slot

logger = set_logger(get_module_name(__file__))

__all__ = ['HardwareThread', 'make_plugin_settings']


def make_plugin_settings(plugin_class: type, params_state: dict | None = None) -> Any:
    """A settings tree built from ``plugin_class.params``, restored from *params_state* when given."""
    from pymodaq_gui.parameter import Parameter
    settings = Parameter.create(name='Settings', type='group', children=getattr(plugin_class, 'params', []))
    if params_state is not None:
        settings.restoreState(params_state, addChildren=False, removeChildren=False)
    return settings


def _when_open(method: Callable) -> Callable:
    """Run a method only while the plugin is open; report a failure through ``error``."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if self._plugin is None:
            return None
        try:
            return method(self, *args, **kwargs)
        except Exception as exc:
            logger.exception(f'{method.__name__} failed')
            self.error.emit(str(exc))
            return None

    return wrapper


def _schedule_once(timer: QTimer, period_ms: float) -> None:
    """Start *timer* as a single shot ``period_ms`` from now, pulling a pending shot forward if needed."""
    period = max(1, int(period_ms))
    if timer.isActive():
        if timer.remainingTime() <= period:
            return
        timer.stop()
    timer.setInterval(period)
    timer.start()


class HardwareThread(QObject):
    """Owns the plugin instance and its settings tree; runs in the hardware thread.

    Signals fire in the GUI thread through Qt's queued delivery.  Slots run in the
    hardware thread's event loop.

    Attributes
    ----------
    _plugin_class : type
        The plugin class to instantiate in :meth:`ini_hardware`.
    _params_state : dict or None
        Saved settings state, restored once when the plugin's settings tree is built.
    _plugin : Any or None
        The open plugin instance, or ``None`` before open / after close.
    _plugin_settings : Parameter or None
        The plugin's settings tree, built by :func:`make_plugin_settings`; ``None`` while closed.
    _timers : dict[float, QTimer]
        One single-shot ``QTimer`` per distinct polling period, keyed by ``period_ms``.
    _subscribers : dict[str, list[Subscription]]
        Channel name -> the open subscriptions currently reading it.
    _device_ident : int or None
        The hardware thread's ``threading.get_ident()``, recorded by :meth:`ini_hardware` and
        checked by :meth:`is_device_thread`.
    _pushed : set[str]
        Names of measurements declared ``push=True``: delivered through :meth:`_push_reading`
        instead of ever being polled.
    _settings_of : dict[str, str]
        Control name -> the plugin settings parameter it writes through, for a
        ``setting``-backed control (bypasses ``write``).
    _get_of : dict[str, Callable]
        Quantity name -> its declared ``get`` callback, used instead of ``read``.
    _set_of : dict[str, Callable]
        Control name -> its declared ``set`` callback, used instead of ``write``.
    _actions_of : dict[str, dict[str, Action]]
        Quantity name -> {action name: Action}, dispatched by :meth:`request_action`.
    """

    # ── Outcome of a request: one pair per kind, done/failed, always (channel, ...) first ──
    write_done = Signal(str, object)                    # (channel, value)
    write_failed = Signal(str, str)                      # (channel, message): the plugin's write raised
    action_done = Signal(str, str, object)                # (channel, action name, result): ran without
                                                           # error; result is None when the callback, as
                                                           # most do, reported nothing back
    action_failed = Signal(str, str, str)                 # (channel, action name, message): the callback raised
    read_failed = Signal(str, str)                        # (channel, message): a read/poll raised

    # ── Device status, not tied to one request ──
    hardware_status = Signal(bool, str)                 # (connected, info): open and close only
    capabilities = Signal(object)                       # Capabilities the plugin instance sets after open
    error = Signal(str)                                 # anything else unexpected; the plugin stays open
    settings_changed = Signal(list, object, str)        # (path, data, change): the plugin changed its own settings

    # ── Internal plumbing, not part of the outward signal surface above ──
    _push_requested = Signal(str, object, float)        # (channel, data, read time), from any thread

    def __init__(self, plugin_class: type, params_state: dict | None = None) -> None:
        super().__init__()
        self._plugin_class = plugin_class
        self._params_state: dict | None = params_state
        self._plugin: Any = None
        self._plugin_settings: Any = None
        self._timers: dict[float, QTimer] = {}
        self._subscribers: dict[str, list[Subscription]] = {}
        self._device_ident: int | None = None
        caps = Capabilities.from_device(plugin_class)
        self._pushed: set[str] = {q.name for q in caps.measurements if q.push}
        self._settings_of: dict[str, str] = {q.name: q.setting for q in caps.controls if q.setting}
        self._get_of: dict[str, Callable] = {q.name: q.get for q in caps.measurements + caps.controls if q.get}
        self._set_of: dict[str, Callable] = {q.name: q.set for q in caps.controls if q.set}
        self._pre_set_of: dict[str, Callable] = {q.name: q.pre_set for q in caps.controls if q.pre_set}
        self._post_set_of: dict[str, Callable] = {q.name: q.post_set for q in caps.controls if q.post_set}
        # a measurement's channel can have these too, same as a control's - see request_action
        self._actions_of: dict[str, dict[str, Any]] = {
            q.name: dict(q.actions) for q in caps.measurements + caps.controls if q.actions
        }
        self._push_requested.connect(self._on_push_requested)

    # ── Plugin lifecycle ─────────────────────────────────────────────────────

    def is_device_thread(self) -> bool:
        """True when called on the hardware thread. Safe from any Python thread."""
        return threading.get_ident() == self._device_ident

    @Slot()
    def ini_hardware(self) -> None:
        """Create the plugin and open the hardware.

        Idempotent: a second call while the plugin exists only re-confirms the status.
        """
        self._device_ident = threading.get_ident()
        if self._plugin is not None:
            self.hardware_status.emit(True, 'Hardware already initialized')
            return
        try:
            self._plugin_settings = make_plugin_settings(self._plugin_class, self._params_state)
            self._plugin_settings.sigTreeStateChanged.connect(self._on_plugin_settings_changed)
            plugin = self._plugin_class()
            plugin.push_reading = self._push_reading
            plugin.open(self._plugin_settings)
            self._plugin = plugin
        except Exception as exc:
            self._release_plugin()
            self.hardware_status.emit(False, str(exc))
            return
        instance_caps = getattr(plugin, 'capabilities', None)
        if instance_caps is not None:
            self.capabilities.emit(instance_caps)
        self.hardware_status.emit(True, f'{self._plugin_class.__name__} connected')

    @Slot()
    def close_hardware(self) -> None:
        """Release every subscription, close the plugin and forget its settings.

        Does nothing if the plugin is already closed, so repeated calls emit no duplicate status.
        """
        if self._plugin is None:
            return
        self._release_all_subscriptions()
        self._plugin_settings = None
        self._release_plugin()
        self.hardware_status.emit(False, 'Closed')

    def _release_plugin(self) -> None:
        if self._plugin is None:
            return
        try:
            self._plugin.close()
        except Exception:
            logger.exception('Error while closing the plugin')
        self._plugin = None

    # ── Settings ─────────────────────────────────────────────────────────────

    @Slot(list, object, str)
    @_when_open
    def update_settings(self, path: list, data: object, change: str) -> None:
        """Apply a GUI settings edit to the plugin's tree, then call ``commit_settings``."""
        with QSignalBlocker(self._plugin_settings):
            param = self._plugin_settings.child(*path) if path else self._plugin_settings
            param.setValue(data)
        commit = getattr(self._plugin, 'commit_settings', None)
        if commit is not None:
            commit(param)

    def _on_plugin_settings_changed(self, _, changes) -> None:
        """Forward a settings change the plugin makes itself.

        A GUI-originated change is applied under a ``QSignalBlocker`` in ``update_settings``, so it never
        reaches here; only the plugin's own changes do.
        """
        for param, change, data in changes:
            if change != 'value':
                continue
            path = self._plugin_settings.childPath(param)
            if path is not None:
                self.settings_changed.emit(path, data, change)

    # ── One-shot requests ────────────────────────────────────────────────────

    @Slot(str, object)
    @_when_open
    def request_write(self, channel: str, value: object) -> None:
        """Set *channel* to *value*: its own ``set``, a setting-backed control's ``commit_settings``, or ``write``.

        Whichever of those actually applies the value (or none, if the control has only
        ``pre_set``/``post_set``, or neither), the value is then always stored as ``plugin.<channel>``
        too - every control ends up with a live attribute mirroring its last successful write, with no
        plugin code needed for that part. ``pre_set``, if declared, runs first (raise to reject, same
        as ``set``/``write()`` raising); ``post_set`` runs after the value has been stored.

        Emits ``write_done``, or ``write_failed`` on error.
        """
        try:
            pre_set = self._pre_set_of.get(channel)
            if pre_set is not None:
                pre_set(self._plugin, value)
            setter = self._set_of.get(channel)
            setting_name = self._settings_of.get(channel)
            if setter is not None:
                setter(self._plugin, value)
            elif setting_name is not None:
                # Unblocked, unlike update_settings: the GUI settings tree was not touched by this write,
                # so it needs the settings_changed signal to find out, the same way it hears a plugin's own change.
                param = self._plugin_settings.child(setting_name)
                param.setValue(value)
                commit = getattr(self._plugin, 'commit_settings', None)
                if commit is not None:
                    commit(param)
            else:
                write = getattr(self._plugin, 'write', None)
                if write is not None:
                    write(channel, value)
            setattr(self._plugin, channel, value)
            post_set = self._post_set_of.get(channel)
            if post_set is not None:
                post_set(self._plugin, value)
        except Exception as exc:
            logger.exception(f'write of {channel!r} failed')
            self.write_failed.emit(channel, str(exc))
            return
        self.write_done.emit(channel, value)

    @Slot(str, str, object)
    @_when_open
    def request_action(self, channel: str, action_name: str, checked: bool | None = None) -> None:
        """Call *channel*'s declared *action_name* callback, if it has one. A no-op otherwise.

        Mirrors ``request_write``'s done/failed shape: ``action_done(channel, action_name, result)`` on
        success, ``action_failed(channel, action_name, message)`` if the callback raised. ``result`` is
        the callback's return value, or ``None`` when it has nothing to report (what most callbacks do).
        Never treated as a write - no settling of its own.

        *checked* is a ``checkable`` action's new button state, passed to the callback as a second
        argument (``callback(plugin, checked)``); ``None`` for a plain action.

        See ``device_module_connections.md`` ("Actions") for how the GUI side uses ``action_done`` /
        ``action_failed`` (e.g. why only ``stop`` clears a row's pending state).
        """
        action = self._actions_of.get(channel, {}).get(action_name)
        if action is None:
            return
        try:
            result = action.callback(self._plugin, checked) if action.checkable else action.callback(self._plugin)
        except Exception as exc:
            logger.exception(f'action {action_name!r} of {channel!r} failed')
            self.action_failed.emit(channel, action_name, str(exc))
            return
        self.action_done.emit(channel, action_name, result)

    # ── Pushed readings ──────────────────────────────────────────────────────

    def _push_reading(self, channel: str, data: object) -> None:
        """Called by the plugin from any thread, e.g. an SDK callback. The reading is queued to the hardware thread."""
        self._push_requested.emit(channel, data, time.time())

    @Slot(str, object, float)
    @_when_open
    def _on_push_requested(self, channel: str, data: object, read_time: float) -> None:
        self._fan_out(channel, data, read_time)

    # ── Periodic polling ─────────────────────────────────────────────────────

    @Slot(object)
    def subscribe(self, sub: Subscription) -> None:
        """Send readings of ``sub.channel`` to *sub* every ``sub.period_ms``.

        One timer serves every subscription with the same period, and each tick reads
        all of those channels in one call.  A one-shot subscription (no period) gets one
        reading and is released.  Requests made while the plugin is closed are dropped.
        """
        if self._plugin is None:
            self.error.emit(f'Subscription to {sub.channel!r} dropped: the device is not open')
            sub.released.emit()
            return
        if sub.period_ms is None:
            self._read_one_shot(sub)
            return
        self._subscribers.setdefault(sub.channel, []).append(sub)
        if sub.channel not in self._pushed:
            self._ensure_timer(sub.period_ms)

    def _read_one_shot(self, sub: Subscription) -> None:
        try:
            self._read_now(sub)
        finally:
            sub.released.emit()

    @_when_open
    def _read_now(self, sub: Subscription) -> None:
        try:
            data = self._read_channel(sub.channel)
        except Exception as exc:
            logger.exception(f'read of {sub.channel!r} failed')
            self.read_failed.emit(sub.channel, str(exc))
            return
        self._send(sub, data, time.time())

    def _read_channel(self, channel: str) -> object:
        """One channel's value: its own ``get`` if declared, otherwise a single-channel ``read``."""
        getter = self._get_of.get(channel)
        if getter is not None:
            return getter(self._plugin)
        dte = self._plugin.read(names=[channel], fresh=True)
        return dte.get_data_from_name(channel)

    def _send(self, sub: Subscription, data: object, read_time: float) -> None:
        if not sub.try_claim():
            return
        selected = sub.transform(copy.deepcopy(data)) if sub.transform is not None else data
        sub.data_ready.emit(selected, False, read_time)

    @Slot(object)
    def unsubscribe(self, sub: Subscription) -> None:
        """Stop sending readings to *sub*, then release it so the consumer can delete it.

        A subscription the thread no longer holds (already released, or dropped while closed) is ignored.
        """
        subs = self._subscribers.get(sub.channel, [])
        if sub not in subs:
            return
        subs.remove(sub)
        if not subs:
            self._subscribers.pop(sub.channel, None)
        if not self._subscriptions_at(sub.period_ms):
            self._drop_timer(sub.period_ms)
        sub.released.emit()

    def _subscriptions(self) -> list[Subscription]:
        return [sub for subs in self._subscribers.values() for sub in subs]

    def _subscriptions_at(self, period_ms: float) -> list[Subscription]:
        return [sub for sub in self._subscriptions() if sub.period_ms == period_ms]

    def _ensure_timer(self, period_ms: float) -> None:
        timer = self._timers.get(period_ms)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda p=period_ms: self._on_period_tick(p))
            self._timers[period_ms] = timer
        _schedule_once(timer, period_ms)

    def _drop_timer(self, period_ms: float) -> None:
        timer = self._timers.pop(period_ms, None)
        if timer is not None:
            timer.stop()
            # The lambda above closes over self, so self -> _timers -> timer -> (connection) ->
            # lambda -> self is a genuine reference cycle: only Python's cyclic GC can free it,
            # at an unpredictable later point, possibly after this thread has already stopped -
            # exactly what QTimer's own cross-thread-deletion guard warns about. Disconnecting
            # breaks the cycle synchronously, right here, on this timer's own thread.
            timer.timeout.disconnect()
            timer.deleteLater()

    def _on_period_tick(self, period_ms: float) -> None:
        """One read for every channel subscribed at *period_ms*, then schedule the next tick.

        Scheduling happens after the read completes, so a slow read is never overlapped.
        """
        try:
            self._read_period(period_ms)
        finally:
            if period_ms in self._timers:
                _schedule_once(self._timers[period_ms], period_ms)

    @_when_open
    def _read_period(self, period_ms: float) -> None:
        """One read for the channels sharing this period.

        One batched ``read`` call answers the channels without their own ``get``. A channel that
        declares one is read individually instead, since declaring it opts that channel out of
        the plugin's batching.
        """
        subs = self._subscriptions_at(period_ms)
        if not subs:
            return
        channels = sorted({sub.channel for sub in subs} - self._pushed)
        if not channels:
            return
        batched = [channel for channel in channels if channel not in self._get_of]
        try:
            dte = self._plugin.read(names=batched, fresh=True) if batched else None
        except Exception as exc:
            logger.exception(f'batched read of {batched} failed')
            for channel in batched:
                self.read_failed.emit(channel, str(exc))
            return
        for channel in channels:
            getter = self._get_of.get(channel)
            try:
                data = getter(self._plugin) if getter is not None else dte.get_data_from_name(channel)
            except Exception as exc:
                logger.exception(f'read of {channel!r} failed')
                self.read_failed.emit(channel, str(exc))
                continue
            self._deliver(channel, data, period_ms)

    def _deliver(self, channel: str, data: object, period_ms: float) -> None:
        """Send one channel's data to its subscriptions at *period_ms* only."""
        if any(sub.period_ms == period_ms for sub in self._subscribers.get(channel, [])):
            self._fan_out(channel, data, time.time(), period_ms)

    def _fan_out(self, channel: str, data: object, read_time: float, period_ms: float | None = None) -> None:
        """Send *data* to the subscriptions of *channel*, at *period_ms* when given.

        Subscribers without a transform share the same object, so it must be read-only for them.
        A transform receives its own copy.

        *read_time* is wall-clock (``time.time()``), not ``time.monotonic()``, deliberately: it
        ends up as a reading's ``DataWithAxes.timestamp`` (see ``Channel._emit`` in
        ``channel.py``), which is documented repo-wide as "seconds since epoch" and already used
        that way for H5 time-axis saving, DAQ_Logger's DB rows, and plot titles - monotonic time
        would be silently wrong there, and nothing in this class needs the adjustment-immunity
        monotonic time would otherwise buy, since *read_time* is never compared against another
        reading's *within* this class, only forwarded.
        """
        for sub in list(self._subscribers.get(channel, [])):
            if period_ms is None or sub.period_ms == period_ms:
                self._send(sub, data, read_time)

    def _release_all_subscriptions(self) -> None:
        for timer in self._timers.values():
            timer.stop()
            timer.timeout.disconnect()  # breaks the self-referencing cycle - see _drop_timer
            timer.deleteLater()
        self._timers.clear()
        subs = self._subscriptions()
        self._subscribers.clear()
        for sub in subs:
            sub.released.emit()

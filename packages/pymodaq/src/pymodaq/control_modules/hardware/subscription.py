"""A consumer's request for readings of one channel, shared by the hardware thread and its consumers."""
from __future__ import annotations

import threading
from typing import Any, Callable

from pymodaq_utils.logger import set_logger, get_module_name
from qtpy.QtCore import QObject, Qt, Signal

logger = set_logger(get_module_name(__file__))


class Subscription(QObject):
    """One consumer's request for periodic readings of one channel.

    Created in the GUI thread and owned by the consumer. The hardware thread emits
    ``data_ready`` on it, and Qt delivers the signal to the consumer's thread.

    A subscription with ``period_ms=None`` is a one-shot read: the hardware thread reads the
    channel once, sends the reading, and releases the subscription.

    ``transform`` selects what the consumer receives from the channel's data, for
    example a ROI slice, so a recording can keep only the region it needs. The
    selection is applied on the hardware thread, before the signal is sent.

    ``policy`` sets what happens when the consumer is behind:

    - ``'all'`` (default): every reading is sent. Readings queue up until the consumer
      acknowledges them, and a warning is logged once the backlog exceeds ``max_pending``.
      Use it for recording.
    - ``'latest'``: a reading is sent only when the previous one has been acknowledged,
      so a slow consumer skips readings instead of queuing them. Use it for display.

    A consumer that wants Qt to call it back sets :attr:`on_data` to a ``(data, read_time) ->
    None`` callback - :meth:`_deliver` acknowledges the reading, then calls it. A consumer that
    connects its own slot to ``data_ready`` directly (e.g. a script polling ``pending`` itself)
    keeps full control and calls :meth:`acknowledge` itself; :attr:`on_data` left unset, nothing
    about that reading is touched automatically.
    """

    data_ready = Signal(object, bool, float)  # (data of this channel, is_temp, wall-clock read time)
    released = Signal()                       # emitted by the hardware thread once it has dropped this subscription

    POLICIES = ('all', 'latest')

    def __init__(self, channel: str, period_ms: float | None, parent: QObject | None = None,
                 transform: Callable[[Any], Any] | None = None, policy: str = 'all',
                 max_pending: int = 100, auto_delete: bool = True,
                 connection_type: Qt.ConnectionType = Qt.ConnectionType.AutoConnection) -> None:
        super().__init__(parent)
        if policy not in self.POLICIES:
            raise ValueError(f'policy must be one of {self.POLICIES}, got {policy!r}')
        if period_ms is not None and period_ms <= 0:
            raise ValueError(f'period_ms must be positive or None for a one-shot read, got {period_ms}')
        self.channel = channel
        self.period_ms = period_ms
        self.transform = transform
        self.policy = policy
        self.max_pending = max_pending
        self._pending = 0
        self._lock = threading.Lock()
        self._backlog_warned = False
        # The consumer's own (data, read_time) -> None callback, set after construction (see
        # Controller.poll/read/read_blocking). data_ready is always connected to _deliver, a bound
        # method of this Subscription itself, never a lambda the consumer connects directly: a
        # lambda closing over `sub` gets none of Qt's own auto-disconnect protection (that only
        # tracks a bound method's __self__), so calling into one after this object's own
        # auto_delete has run is a real use-after-free risk, not just a logical one - the same
        # class of bug _start_timeout's own comment (controller.py) already documents and avoids,
        # just for a different signal.
        self.on_data: Callable[[Any, float], None] | None = None
        self.data_ready.connect(self._deliver, connection_type)
        if auto_delete:
            self.released.connect(self.deleteLater)

    def _deliver(self, data: Any, _is_temp: bool, read_time: float) -> None:
        if self.on_data is not None:
            self.acknowledge()
            self.on_data(data, read_time)

    @property
    def pending(self) -> int:
        """Readings sent and not yet acknowledged by the consumer."""
        with self._lock:
            return self._pending

    def try_claim(self) -> bool:
        """Hardware thread: reserve a slot for one reading, or refuse it under the ``latest`` policy."""
        with self._lock:
            if self.policy == 'latest' and self._pending > 0:
                return False
            self._pending += 1
            if self._pending > self.max_pending and not self._backlog_warned:
                self._backlog_warned = True
                logger.warning(f'Subscription to {self.channel!r} has {self._pending} unacknowledged readings')
            return True

    def acknowledge(self) -> None:
        """Consumer: mark one reading as handled."""
        with self._lock:
            self._pending = max(0, self._pending - 1)
            if self._pending <= self.max_pending:
                self._backlog_warned = False

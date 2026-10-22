"""Tests for HardwareThread.

Design: one physical hardware device → one HardwareThread → one new-style plugin instance.
GUI modules are subscribers; they never touch the SDK.

Mock plugins use the new-style API (open / close / read / write).

Qt is required (HardwareThread is a QObject) but no GUI is shown.
Slots are called directly in the test thread for the core logic tests.
Timer firing is verified with qtbot.
"""
from __future__ import annotations

import time

import pytest

from pymodaq.control_modules.hardware.capabilities import Action, control, measurement
from pymodaq.control_modules.hardware.hardware_thread import HardwareThread
from pymodaq.control_modules.hardware.subscription import Subscription


# ---------------------------------------------------------------------------
# Mock plugin helpers
# ---------------------------------------------------------------------------

FAKE_DTE = object()   # stand-in for DataToExport


class MockPlugin:
    """New-style plugin stub: records every call, raises on demand."""

    def __init__(self):
        self.open_called_with = None   # settings passed to open()
        self.close_called = False
        self.query_calls: list = []    # list of names lists
        self.change_calls: list = []   # list of (name, value)
        self.commit_calls: list = []   # list of (path, data, change)

        self._open_raises: Exception | None = None
        self._query_raises: Exception | None = None
        self._change_raises: Exception | None = None
        self._capabilities = None

    def open(self, settings) -> None:
        self.open_called_with = settings
        if self._open_raises:
            raise self._open_raises

    def close(self) -> None:
        self.close_called = True

    def read(self, names=None, fresh=True):
        self.query_calls.append(names)
        if self._query_raises:
            raise self._query_raises
        return _StubDTE(names)

    def write(self, name, value) -> None:
        self.change_calls.append((name, value))
        if self._change_raises:
            raise self._change_raises

    def commit_settings(self, param) -> None:
        """Plugins receive a Parameter object from commit_settings."""
        self.commit_calls.append(param)

    @property
    def capabilities(self):
        return self._capabilities


class FakeSettings:
    """Stand-in for pymodaq_gui Parameter."""
    def saveState(self):
        return None
    def child(self, *path):
        return self


def make_plugin_class(plugin_instance: MockPlugin) -> type:
    """Return a plugin class whose constructor always returns *plugin_instance*.

    Subclasses the instance's own class (MockPlugin by default), so class attributes such as
    a MockPlugin subclass's ``params`` are kept, and the new-style detection still sees ``open``.
    """
    instance = plugin_instance

    class _PluginClass(type(plugin_instance)):
        def __new__(cls, *args, **kwargs):
            return instance

    _PluginClass.__name__ = 'MockPluginClass'
    return _PluginClass


def make_thread(plugin_instance: MockPlugin | None = None) -> tuple[HardwareThread, MockPlugin]:
    """Return a (HardwareThread, MockPlugin) pair, not yet initialised."""
    if plugin_instance is None:
        plugin_instance = MockPlugin()
    plugin_cls = make_plugin_class(plugin_instance)
    thread_obj = HardwareThread(plugin_class=plugin_cls, params_state=None)
    return thread_obj, plugin_instance


def make_initialised_thread(plugin_instance: MockPlugin) -> tuple[HardwareThread, MockPlugin]:
    """Like make_thread(), but also runs ini_hardware() - for tests that need a MockPlugin
    subclass declaring its own channels/settings (make_thread()'s own default covers the plain
    'axis_x' case; this one takes an already-built instance so a test can still close over a
    local `calls` list from inside its subclass's own body)."""
    thread_obj, plugin_instance = make_thread(plugin_instance)
    thread_obj.ini_hardware()
    return thread_obj, plugin_instance


# ---------------------------------------------------------------------------
# Signal collector
# ---------------------------------------------------------------------------

class Collector:
    """Accumulate Qt signal emissions for assertions."""

    def __init__(self):
        self.calls: list = []

    def __call__(self, *args):
        self.calls.append(args)

    @property
    def count(self) -> int:
        return len(self.calls)

    def last(self):
        return self.calls[-1] if self.calls else None


# ---------------------------------------------------------------------------
# ini_hardware
# ---------------------------------------------------------------------------

class TestIniHardware:

    def test_ini_calls_plugin_open(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        assert plugin.open_called_with is not None

    def test_ini_passes_plugin_settings_to_open(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        # Plugin receives the hardware-thread-owned _plugin_settings Parameter,
        # not the shared GUI-thread hw_settings.
        assert plugin.open_called_with is thread_obj._plugin_settings

    def test_ini_stores_plugin_instance(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        assert thread_obj._plugin is plugin

    def test_ini_emits_hardware_status_true(self, qapp):
        thread_obj, plugin = make_thread()
        collector = Collector()
        thread_obj.hardware_status.connect(collector)
        thread_obj.ini_hardware()
        assert collector.count == 1
        connected, _ = collector.last()
        assert connected is True

    def test_ini_emits_instance_capabilities_when_the_plugin_sets_them(self, qapp):
        thread_obj, plugin = make_thread()
        fake_caps = object()
        plugin._capabilities = fake_caps
        collector = Collector()
        thread_obj.capabilities.connect(collector)
        thread_obj.ini_hardware()
        assert collector.count == 1
        assert collector.last()[0] is fake_caps

    def test_ini_emits_no_instance_capabilities_when_none_set(self, qapp):
        thread_obj, plugin = make_thread()
        collector = Collector()
        thread_obj.capabilities.connect(collector)
        thread_obj.ini_hardware()
        assert collector.count == 0

    def test_ini_failure_emits_hardware_status_false(self, qapp):
        thread_obj, plugin = make_thread()
        plugin._open_raises = RuntimeError('device not found')
        collector = Collector()
        thread_obj.hardware_status.connect(collector)
        thread_obj.ini_hardware()
        connected, info = collector.last()
        assert connected is False
        assert 'device not found' in info

    def test_ini_failure_leaves_plugin_none(self, qapp):
        thread_obj, plugin = make_thread()
        plugin._open_raises = RuntimeError('oops')
        thread_obj.ini_hardware()
        assert thread_obj._plugin is None


# ---------------------------------------------------------------------------
# close_hardware
# ---------------------------------------------------------------------------

class TestCloseHardware:

    def test_close_calls_plugin_close(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        thread_obj.close_hardware()
        assert plugin.close_called

    def test_close_sets_plugin_to_none(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        thread_obj.close_hardware()
        assert thread_obj._plugin is None

    def test_close_emits_hardware_status_false(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        collector = Collector()
        thread_obj.hardware_status.connect(collector)
        thread_obj.close_hardware()
        connected, _ = collector.last()
        assert connected is False

    def test_close_before_ini_is_safe(self, qapp):
        thread_obj, _ = make_thread()
        thread_obj.close_hardware()  # must not raise

    def test_close_stops_polling(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        thread_obj.subscribe(Subscription('ch', 1000.0))
        assert 1000.0 in thread_obj._timers
        thread_obj.close_hardware()
        assert thread_obj._timers == {}
        assert thread_obj._subscribers == {}


# one-shot reads
# ---------------------------------------------------------------------------

class TestOneShotRead:

    def test_one_shot_calls_plugin_read(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        thread_obj.subscribe(Subscription('axis_x', None))
        assert plugin.query_calls == [['axis_x']]

    def test_one_shot_delivers_the_reading_then_releases(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        sub = Subscription('axis_x', None)
        got, released = Collector(), Collector()
        sub.data_ready.connect(got)
        sub.released.connect(released)
        thread_obj.subscribe(sub)
        assert got.count == 1
        assert got.calls[0][0] == ('data', 'axis_x')
        assert released.count == 1

    def test_one_shot_is_not_polled(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        thread_obj.subscribe(Subscription('axis_x', None))
        assert thread_obj._timers == {}
        assert thread_obj._subscribers == {}

    def test_one_shot_before_ini_releases_without_data(self, qapp):
        thread_obj, plugin = make_thread()
        sub = Subscription('axis_x', None)
        got, released = Collector(), Collector()
        sub.data_ready.connect(got)
        sub.released.connect(released)
        thread_obj.subscribe(sub)
        assert got.count == 0
        assert released.count == 1
        assert plugin.query_calls == []

    def test_one_shot_exception_emits_read_failed_and_releases(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        plugin._query_raises = RuntimeError('read failed')
        statuses, failed, released = Collector(), Collector(), Collector()
        thread_obj.hardware_status.connect(statuses)
        thread_obj.read_failed.connect(failed)
        sub = Subscription('axis_x', None)
        sub.released.connect(released)
        thread_obj.subscribe(sub)
        assert failed.last() == ('axis_x', 'read failed')
        assert statuses.count == 0
        assert thread_obj._plugin is not None
        assert released.count == 1

    def test_subscribe_before_ini_is_dropped_and_released(self, qapp):
        thread_obj, plugin = make_thread()
        released, errors = Collector(), Collector()
        thread_obj.error.connect(errors)
        sub = Subscription('axis_x', 100.0)
        sub.released.connect(released)
        thread_obj.subscribe(sub)
        assert released.count == 1
        assert 'not open' in errors.last()[0]
        assert thread_obj._subscribers == {}
        assert thread_obj._timers == {}

    def test_one_shot_applies_its_transform(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        sub = Subscription('axis_x', None, transform=lambda data: ('roi', data))
        got = Collector()
        sub.data_ready.connect(got)
        thread_obj.subscribe(sub)
        assert got.calls[0][0] == ('roi', ('data', 'axis_x'))


# ---------------------------------------------------------------------------
# request_write
# ---------------------------------------------------------------------------

class TestRequestWrite:

    def test_request_write_calls_plugin_write(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        thread_obj.request_write('axis_x', 42.0)
        assert plugin.change_calls == [('axis_x', 42.0)]

    def test_request_write_emits_write_done(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        collector = Collector()
        thread_obj.write_done.connect(collector)
        thread_obj.request_write('axis_x', 42.0)
        assert collector.count == 1
        channel, value = collector.last()
        assert channel == 'axis_x'
        assert value == 42.0

    def test_request_write_before_ini_is_noop(self, qapp):
        thread_obj, plugin = make_thread()
        collector = Collector()
        thread_obj.write_done.connect(collector)
        thread_obj.request_write('axis_x', 0.0)
        assert collector.count == 0
        assert plugin.change_calls == []

    def test_request_write_exception_emits_write_failed_and_keeps_plugin_open(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        plugin._change_raises = RuntimeError('write failed')
        failures, statuses = Collector(), Collector()
        thread_obj.write_failed.connect(failures)
        thread_obj.hardware_status.connect(statuses)
        thread_obj.request_write('axis_x', 0.0)
        assert failures.last() == ('axis_x', 'write failed')
        assert statuses.count == 0
        assert thread_obj._plugin is not None


# ---------------------------------------------------------------------------
# request_action
# ---------------------------------------------------------------------------

class TestRequestAction:

    def _thread_with_stop(self, qapp):
        calls = []

        class _Plugin(MockPlugin):
            axis_x = control(lo=0, hi=10, stop=lambda plugin: calls.append('stopped'))

        thread_obj, instance = make_initialised_thread(_Plugin())
        return thread_obj, instance, calls

    def test_request_action_calls_the_declared_callback(self, qapp):
        thread_obj, plugin, calls = self._thread_with_stop(qapp)
        thread_obj.request_action('axis_x', 'stop')
        assert calls == ['stopped']

    def test_request_action_for_a_channel_without_one_is_a_noop(self, qapp):
        thread_obj, plugin = make_thread()  # axis_x has no actions
        thread_obj.ini_hardware()
        thread_obj.request_action('axis_x', 'stop')  # must not raise

    def test_request_action_for_an_undeclared_name_is_a_noop(self, qapp):
        thread_obj, plugin, calls = self._thread_with_stop(qapp)
        thread_obj.request_action('axis_x', 'home')  # 'stop' is declared, 'home' is not
        assert calls == []

    def test_request_action_before_ini_is_a_noop(self, qapp):
        thread_obj, plugin, calls = self._thread_with_stop(qapp)
        thread_obj._plugin = None  # simulate not open, without re-running ini
        thread_obj.request_action('axis_x', 'stop')
        assert calls == []

    def test_several_actions_on_one_channel_are_dispatched_by_name(self, qapp):
        calls = []

        class _Plugin(MockPlugin):
            axis_x = control(lo=0, hi=10, stop=lambda plugin: calls.append('stopped'),
                             actions={'home': lambda plugin: calls.append('homed')})

        thread_obj, instance = make_initialised_thread(_Plugin())
        thread_obj.request_action('axis_x', 'home')
        thread_obj.request_action('axis_x', 'stop')
        assert calls == ['homed', 'stopped']

    def test_request_action_exception_emits_action_failed_not_write_failed_or_action_done(self, qapp):
        def _raise(plugin):
            raise RuntimeError('cannot stop')

        class _Plugin(MockPlugin):
            axis_x = control(lo=0, hi=10, stop=_raise)

        thread_obj, instance = make_initialised_thread(_Plugin())
        failed_action, failed_write, done = Collector(), Collector(), Collector()
        thread_obj.action_failed.connect(failed_action)
        thread_obj.write_failed.connect(failed_write)
        thread_obj.action_done.connect(done)
        thread_obj.request_action('axis_x', 'stop')
        assert failed_action.last() == ('axis_x', 'stop', 'cannot stop')
        assert failed_write.count == 0
        assert done.count == 0

    def test_request_action_emits_action_done_with_none_when_the_callback_reports_nothing(self, qapp):
        thread_obj, plugin, calls = self._thread_with_stop(qapp)  # its stop callback returns nothing
        done = Collector()
        thread_obj.action_done.connect(done)
        thread_obj.request_action('axis_x', 'stop')
        assert done.last() == ('axis_x', 'stop', None)

    def test_request_action_emits_action_done_with_the_callbacks_return_value(self, qapp):
        class _Plugin(MockPlugin):
            axis_x = control(lo=0, hi=10, stop=lambda plugin: 7.5)

        thread_obj, instance = make_initialised_thread(_Plugin())
        done = Collector()
        thread_obj.action_done.connect(done)
        thread_obj.request_action('axis_x', 'stop')
        assert done.last() == ('axis_x', 'stop', 7.5)

    def test_a_measurement_can_declare_an_action_too(self, qapp):
        calls = []

        class _Plugin(MockPlugin):
            spectrum = measurement(shape=(4,), actions={'take_background': lambda plugin: calls.append('bkg')})

        thread_obj, instance = make_initialised_thread(_Plugin())
        thread_obj.request_action('spectrum', 'take_background')
        assert calls == ['bkg']

    def test_a_checkable_actions_callback_receives_the_checked_state(self, qapp):
        calls = []

        class _Plugin(MockPlugin):
            spectrum = measurement(shape=(4,), actions={
                'subtract_bkg': Action(lambda plugin, checked: calls.append(checked), checkable=True),
            })

        thread_obj, instance = make_initialised_thread(_Plugin())
        thread_obj.request_action('spectrum', 'subtract_bkg', True)
        thread_obj.request_action('spectrum', 'subtract_bkg', False)
        assert calls == [True, False]

    def test_a_non_checkable_actions_callback_is_still_called_with_one_argument(self, qapp):
        thread_obj, plugin, calls = self._thread_with_stop(qapp)
        thread_obj.request_action('axis_x', 'stop', None)  # explicit None, same as omitting it
        assert calls == ['stopped']


# ---------------------------------------------------------------------------
# start_grab / stop_grab
# ---------------------------------------------------------------------------


class _StubDTE:
    """Minimal DataToExport: returns the named channel's data."""

    def __init__(self, names):
        self.names = names

    def get_data_from_name(self, name):
        return ('data', name)


class TestSubscriptions:

    def _thread_with_stub(self):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        return thread_obj, plugin

    def test_subscriber_receives_only_its_channel(self, qapp, qtbot):
        thread_obj, plugin = self._thread_with_stub()
        spectrum, temperature = Subscription('spectrum', 50.0), Subscription('temperature', 50.0)
        got_spectrum, got_temperature = Collector(), Collector()
        spectrum.data_ready.connect(got_spectrum)
        temperature.data_ready.connect(got_temperature)
        thread_obj.subscribe(spectrum)
        thread_obj.subscribe(temperature)
        qtbot.wait(150)
        thread_obj.unsubscribe(spectrum)
        thread_obj.unsubscribe(temperature)
        assert got_spectrum.count >= 1 and got_temperature.count >= 1
        assert all(call[0] == ('data', 'spectrum') for call in got_spectrum.calls)
        assert all(call[0] == ('data', 'temperature') for call in got_temperature.calls)

    def test_two_subscribers_on_one_channel_both_receive(self, qapp):
        thread_obj, plugin = self._thread_with_stub()
        first, second = Subscription('ch', 100.0), Subscription('ch', 100.0)
        a, b = Collector(), Collector()
        first.data_ready.connect(a)
        second.data_ready.connect(b)
        thread_obj.subscribe(first)
        thread_obj.subscribe(second)
        thread_obj._on_period_tick(100.0)
        thread_obj._on_period_tick(100.0)
        assert a.count == b.count == 2
        thread_obj.unsubscribe(first)
        thread_obj.unsubscribe(second)

    def test_unsubscribed_channel_is_no_longer_read(self, qapp):
        thread_obj, plugin = self._thread_with_stub()
        sub = Subscription('ch', 100.0)
        thread_obj.subscribe(sub)
        thread_obj.unsubscribe(sub)
        assert 'ch' not in thread_obj._subscribers
        assert thread_obj._timers == {}

    def test_channel_is_extracted_once_per_read(self, qapp):
        thread_obj, plugin = self._thread_with_stub()
        extractions = []

        class _CountingDTE(_StubDTE):
            def get_data_from_name(self, name):
                extractions.append(name)
                return super().get_data_from_name(name)

        plugin.read = lambda names=None, fresh=True: _CountingDTE(names)
        subs = [Subscription('ch', 100.0), Subscription('ch', 100.0), Subscription('ch', 100.0)]
        for sub in subs:
            sub.data_ready.connect(lambda data, is_temp, stamp: None)
            thread_obj.subscribe(sub)
        thread_obj._on_period_tick(100.0)
        assert extractions == ['ch']
        for sub in subs:
            thread_obj.unsubscribe(sub)


# ---------------------------------------------------------------------------
# update_settings
# ---------------------------------------------------------------------------

class TestUpdateSettings:

    def test_update_settings_calls_commit_settings(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        # path=[] means root _plugin_settings node — always present regardless of params.
        thread_obj.update_settings([], 42, 'value')
        # commit_settings receives the root _plugin_settings Parameter node.
        assert len(plugin.commit_calls) == 1
        assert plugin.commit_calls[0] is thread_obj._plugin_settings

    def test_update_settings_before_ini_is_noop(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.update_settings(['param'], 1, 'value')  # must not raise
        assert plugin.commit_calls == []

    def test_update_settings_plugin_without_commit_settings(self, qapp):
        """Plugins that don't implement commit_settings are skipped silently."""
        class _PluginNoCommit:
            def open(self, settings): pass
            def close(self): pass
            def read(self, names=None, fresh=True): return FAKE_DTE
            def write(self, name, value): pass
            capabilities = None

        thread_obj, _ = make_initialised_thread(_PluginNoCommit())
        thread_obj.update_settings(['param'], 1, 'value')  # must not raise


# ---------------------------------------------------------------------------
# Channel routing (single plugin)
# ---------------------------------------------------------------------------

class TestChannelRouting:
    """One plugin instance handles all channels — no dispatch logic needed."""

    def test_any_channel_name_is_passed_through(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        for ch in ('axis_x', 'axis_y', 'temperature', 'arbitrary'):
            thread_obj.subscribe(Subscription(ch, None))
        assert plugin.query_calls == [['axis_x'], ['axis_y'], ['temperature'], ['arbitrary']]


class TestIniHardwareIdempotent:

    def test_second_ini_does_not_reopen_hardware(self, qapp):
        thread_obj, plugin = make_thread()
        opens = []
        plugin.open = lambda settings: opens.append(settings)
        thread_obj.ini_hardware()
        thread_obj.ini_hardware()
        assert len(opens) == 1

    def test_failed_ini_releases_the_plugin(self, qapp):
        thread_obj, plugin = make_thread()
        plugin._open_raises = RuntimeError('no device')
        statuses = []
        thread_obj.hardware_status.connect(lambda ok, info: statuses.append((ok, info)))

        thread_obj.ini_hardware()

        assert thread_obj._plugin is None
        assert statuses[-1][0] is False


class TestSubscriptionTransformAndTime:

    def test_transform_selects_what_the_subscriber_receives(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        sub = Subscription('ch', 100.0, transform=lambda data: ('roi', data[1]))
        got = Collector()
        sub.data_ready.connect(got)
        thread_obj.subscribe(sub)
        thread_obj._on_period_tick(100.0)
        thread_obj.unsubscribe(sub)
        assert got.calls[0][0] == ('roi', 'ch')

    def test_each_subscriber_gets_its_own_transform(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        whole = Subscription('ch', 100.0)
        roi = Subscription('ch', 100.0, transform=lambda data: 'roi')
        got_whole, got_roi = Collector(), Collector()
        whole.data_ready.connect(got_whole)
        roi.data_ready.connect(got_roi)
        thread_obj.subscribe(whole)
        thread_obj.subscribe(roi)
        thread_obj._on_period_tick(100.0)
        thread_obj.unsubscribe(whole)
        thread_obj.unsubscribe(roi)
        assert got_whole.calls[0][0] == ('data', 'ch')
        assert got_roi.calls[0][0] == 'roi'

    def test_read_time_is_monotonic_and_sent_with_each_reading(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        sub = Subscription('ch', 100.0)
        got = Collector()
        sub.data_ready.connect(got)
        thread_obj.subscribe(sub)
        thread_obj._on_period_tick(100.0)
        thread_obj._on_period_tick(100.0)
        thread_obj.unsubscribe(sub)
        first, second = got.calls[0][2], got.calls[1][2]
        assert isinstance(first, float) and second >= first


class TestSubscriptionBackpressure:

    def _thread(self):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        return thread_obj

    def test_latest_skips_readings_until_acknowledged(self, qapp):
        thread_obj = self._thread()
        sub = Subscription('ch', 100.0, policy='latest')
        got = Collector()
        sub.data_ready.connect(got)
        thread_obj.subscribe(sub)
        thread_obj._on_period_tick(100.0)
        thread_obj._on_period_tick(100.0)
        assert got.count == 1
        sub.acknowledge()
        thread_obj._on_period_tick(100.0)
        assert got.count == 2
        thread_obj.unsubscribe(sub)

    def test_all_never_skips_and_counts_the_backlog(self, qapp):
        thread_obj = self._thread()
        sub = Subscription('ch', 100.0, policy='all')
        got = Collector()
        sub.data_ready.connect(got)
        thread_obj.subscribe(sub)
        for _ in range(5):
            thread_obj._on_period_tick(100.0)
        assert got.count == 5
        assert sub.pending == 5
        for _ in range(5):
            sub.acknowledge()
        assert sub.pending == 0
        thread_obj.unsubscribe(sub)

    def test_backlog_beyond_limit_logs_a_warning_but_keeps_data(self, qapp, caplog):
        thread_obj = self._thread()
        sub = Subscription('ch', 100.0, max_pending=2)
        got = Collector()
        sub.data_ready.connect(got)
        thread_obj.subscribe(sub)
        for _ in range(4):
            thread_obj._on_period_tick(100.0)
        assert got.count == 4
        assert 'unacknowledged readings' in caplog.text
        thread_obj.unsubscribe(sub)

    def test_unknown_policy_rejected(self):
        with pytest.raises(ValueError):
            Subscription('ch', 100.0, policy='sometimes')


class TestSubscriptionRelease:

    def test_unsubscribe_releases_the_subscription(self, qapp, qtbot):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        sub = Subscription('ch', 100.0)
        released = Collector()
        sub.released.connect(released)
        thread_obj.subscribe(sub)
        assert released.count == 0
        thread_obj.unsubscribe(sub)
        assert released.count == 1


class TestPeriods:

    def _thread(self):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        reads = []

        def read(names=None, fresh=True):
            reads.append((tuple(names), time.monotonic()))
            return _StubDTE(names)

        plugin.read = read
        return thread_obj, reads

    def test_subscriptions_at_one_period_share_one_timer(self, qapp):
        thread_obj, _ = self._thread()
        a, b = Subscription('a', 100.0), Subscription('b', 100.0)
        thread_obj.subscribe(a)
        thread_obj.subscribe(b)
        assert list(thread_obj._timers) == [100.0]
        thread_obj.unsubscribe(a)
        thread_obj.unsubscribe(b)

    def test_one_read_serves_every_channel_at_that_period(self, qapp):
        thread_obj, reads = self._thread()
        subs = [Subscription('a', 100.0), Subscription('b', 100.0)]
        for sub in subs:
            thread_obj.subscribe(sub)
        thread_obj._on_period_tick(100.0)
        assert reads[-1][0] == ('a', 'b')
        for sub in subs:
            thread_obj.unsubscribe(sub)

    def test_slow_channel_is_not_read_at_the_fast_rate(self, qapp):
        thread_obj, reads = self._thread()
        fast, slow = Subscription('fast', 50.0), Subscription('slow', 1000.0)
        thread_obj.subscribe(fast)
        thread_obj.subscribe(slow)
        thread_obj._on_period_tick(50.0)
        assert reads[-1][0] == ('fast',)
        thread_obj._on_period_tick(1000.0)
        assert reads[-1][0] == ('slow',)
        thread_obj.unsubscribe(fast)
        thread_obj.unsubscribe(slow)

    def test_unsubscribing_the_last_one_at_a_period_drops_its_timer(self, qapp):
        thread_obj, _ = self._thread()
        fast, slow = Subscription('fast', 50.0), Subscription('slow', 1000.0)
        thread_obj.subscribe(fast)
        thread_obj.subscribe(slow)
        thread_obj.unsubscribe(fast)
        assert list(thread_obj._timers) == [1000.0]
        thread_obj.unsubscribe(slow)
        assert thread_obj._timers == {}

    def test_timer_is_single_shot(self, qapp):
        thread_obj, _ = self._thread()
        sub = Subscription('ch', 100.0)
        thread_obj.subscribe(sub)
        assert thread_obj._timers[100.0].isSingleShot()
        thread_obj.unsubscribe(sub)

    def test_failed_read_still_rearms_the_timer(self, qapp):
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        plugin._query_raises = RuntimeError('bus error')
        plugin.read = lambda names=None, fresh=True: (_ for _ in ()).throw(RuntimeError('bus error'))
        sub = Subscription('ch', 100.0)
        failed = Collector()
        thread_obj.read_failed.connect(failed)
        thread_obj.subscribe(sub)
        thread_obj._on_period_tick(100.0)
        assert failed.last() == ('ch', 'bus error')
        assert thread_obj._timers[100.0].isActive()
        thread_obj.unsubscribe(sub)

    def test_close_releases_every_subscription(self, qapp):
        thread_obj, _ = self._thread()
        subs = [Subscription('a', 100.0), Subscription('b', 1000.0)]
        released = Collector()
        for sub in subs:
            sub.released.connect(released)
            thread_obj.subscribe(sub)
        thread_obj.close_hardware()
        assert released.count == 2
        assert thread_obj._timers == {}
        assert thread_obj._subscribers == {}

    def test_non_positive_period_rejected(self):
        with pytest.raises(ValueError):
            Subscription('ch', 0.0)


class TestPushedReadings:

    def test_reading_pushed_from_another_thread_reaches_the_subscriber(self, qapp, qtbot):
        import threading
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        sub = Subscription('ch', 10000.0)
        got = Collector()
        sub.data_ready.connect(got)
        thread_obj.subscribe(sub)

        worker = threading.Thread(target=plugin.push_reading, args=('ch', 42))
        worker.start()
        worker.join()
        qtbot.waitUntil(lambda: got.count == 1, timeout=2000)

        assert got.calls[0][0] == 42
        thread_obj.unsubscribe(sub)

    def test_push_after_close_is_ignored(self, qapp, qtbot):
        import threading
        thread_obj, plugin = make_thread()
        thread_obj.ini_hardware()
        sub = Subscription('ch', 10000.0)
        got = Collector()
        sub.data_ready.connect(got)
        thread_obj.subscribe(sub)
        thread_obj.close_hardware()

        worker = threading.Thread(target=plugin.push_reading, args=('ch', 42))
        worker.start()
        worker.join()
        qtbot.wait(100)

        assert got.count == 0


# ---------------------------------------------------------------------------
# settings_changed: the plugin changes its own settings
# ---------------------------------------------------------------------------

class TestSettingsChanged:

    def _thread_with_gain(self, qapp):
        class _GainPlugin(MockPlugin):
            params = [{'name': 'gain', 'type': 'float', 'value': 1.0}]

        return make_initialised_thread(_GainPlugin())

    def test_a_change_the_plugin_makes_itself_is_forwarded(self, qapp):
        thread_obj, plugin = self._thread_with_gain(qapp)
        changed = Collector()
        thread_obj.settings_changed.connect(changed)
        thread_obj._plugin_settings.child('gain').setValue(5.0)  # as the plugin would, on its own
        assert changed.last() == (['gain'], 5.0, 'value')

    def test_a_gui_driven_change_is_not_forwarded(self, qapp):
        """update_settings applies it under a QSignalBlocker, so it must not loop back as a device change."""
        thread_obj, plugin = self._thread_with_gain(qapp)
        changed = Collector()
        thread_obj.settings_changed.connect(changed)
        thread_obj.update_settings(['gain'], 7.0, 'value')
        assert changed.count == 0
        assert thread_obj._plugin_settings.child('gain').value() == 7.0

    def test_a_limits_change_the_plugin_makes_itself_is_forwarded(self, qapp):
        """Mirrors the legacy ThreadStatus.UPDATE_SETTINGS handler's 'limits' case
        (control_modules/utils.py) - e.g. a plugin discovering its real choices only once open."""
        thread_obj, plugin = self._thread_with_gain(qapp)
        changed = Collector()
        thread_obj.settings_changed.connect(changed)
        thread_obj._plugin_settings.child('gain').setLimits((0, 10))
        assert changed.last() == (['gain'], (0, 10), 'limits')

    def test_an_options_change_the_plugin_makes_itself_is_forwarded(self, qapp):
        thread_obj, plugin = self._thread_with_gain(qapp)
        changed = Collector()
        thread_obj.settings_changed.connect(changed)
        thread_obj._plugin_settings.child('gain').setOpts(readonly=True)
        assert changed.last() == (['gain'], {'readonly': True}, 'options')

    def test_a_child_added_by_the_plugin_is_forwarded_serialized(self, qapp):
        """A new child's own data is (child, pos) with child a live Parameter belonging to this
        thread's own settings tree - unsafe to hand across the thread boundary as-is, so it's
        serialized (saveState()) before being forwarded, mirroring the legacy send_param_status
        (control_modules/plugin_base.py)."""
        class _GroupPlugin(MockPlugin):
            params = [{'name': 'group', 'type': 'group', 'children': []}]

        thread_obj, plugin = make_initialised_thread(_GroupPlugin())
        changed = Collector()
        thread_obj.settings_changed.connect(changed)
        thread_obj._plugin_settings.child('group').addChild({'name': 'new_child', 'type': 'float', 'value': 2.5})
        path, data, change = changed.last()
        assert path == ['group'] and change == 'childAdded'
        state, pos = data
        assert isinstance(state, dict) and state['name'] == 'new_child' and state['value'] == 2.5


# ---------------------------------------------------------------------------
# get / set: a quantity that answers its own read or write
# ---------------------------------------------------------------------------

class TestGetSet:

    def _thread_with_get_set(self, qapp):
        calls = {'get': [], 'set': []}

        class _Plugin(MockPlugin):
            fast = measurement(get=lambda plugin: (calls['get'].append('fast'), 7.0)[1])
            slow = measurement()  # no get: still goes through read(), batched with other such channels
            level = control(get=lambda plugin: (calls['get'].append('level'), 3.0)[1],
                            set=lambda plugin, value: calls['set'].append(value))

        thread_obj, instance = make_initialised_thread(_Plugin())
        return thread_obj, instance, calls

    def test_a_set_callback_is_used_instead_of_write(self, qapp):
        thread_obj, plugin, calls = self._thread_with_get_set(qapp)
        thread_obj.request_write('level', 9.0)
        assert calls['set'] == [9.0]
        assert plugin.change_calls == []  # write() was not used

    def test_a_single_channel_read_uses_get(self, qapp):
        thread_obj, plugin, calls = self._thread_with_get_set(qapp)
        sub = Subscription('fast', None)
        got = Collector()
        sub.data_ready.connect(got)
        thread_obj.subscribe(sub)
        assert calls['get'] == ['fast']
        assert plugin.query_calls == []  # read() was not used
        assert got.last()[0] == 7.0

    def test_a_periodic_read_batches_channels_without_their_own_get(self, qapp):
        thread_obj, plugin, calls = self._thread_with_get_set(qapp)
        got_fast, got_slow = Collector(), Collector()
        fast_sub = Subscription('fast', 100.0)
        slow_sub = Subscription('slow', 100.0)
        fast_sub.data_ready.connect(got_fast)
        slow_sub.data_ready.connect(got_slow)
        thread_obj.subscribe(fast_sub)
        thread_obj.subscribe(slow_sub)
        thread_obj._on_period_tick(100.0)
        thread_obj.unsubscribe(fast_sub)
        thread_obj.unsubscribe(slow_sub)
        # 'fast' has its own get: answered directly, not through the batched read() call.
        assert calls['get'] == ['fast']
        assert plugin.query_calls == [['slow']]
        assert got_fast.last()[0] == 7.0
        assert got_slow.last()[0] == ('data', 'slow')


class TestAutomaticStorage:
    """request_write stores plugin.<name> = value after every successful write, regardless of
    set=/write()/neither - not just for a control with pre_set=/post_set=. Resolved
    entirely in HardwareThread.request_write itself, so these tests exercise it directly."""

    def _thread_with_plain_control(self):
        class _Plugin(MockPlugin):
            level = control()

        return make_initialised_thread(_Plugin())

    def test_a_plain_write_stores_the_attribute_and_still_calls_write(self, qapp):
        thread_obj, plugin = self._thread_with_plain_control()
        thread_obj.request_write('level', 9.0)
        assert plugin.level == 9.0
        assert plugin.change_calls == [('level', 9.0)]  # write() still runs - unlike attr= before it

    def test_a_never_written_control_reads_back_none(self, qapp):
        thread_obj, plugin = self._thread_with_plain_control()
        assert plugin.level is None

    def test_write_failing_leaves_the_attribute_unset(self, qapp):
        class _Plugin(MockPlugin):
            level = control()

        plugin = _Plugin()
        plugin._change_raises = RuntimeError('nope')
        thread_obj, plugin = make_initialised_thread(plugin)
        failed = Collector()
        thread_obj.write_failed.connect(failed)
        thread_obj.request_write('level', 9.0)
        assert failed.calls == [('level', 'nope')]
        assert plugin.level is None  # write() raised before storage ran


class TestPreSetPostSet:
    """pre_set=/post_set= hook into the same write TestAutomaticStorage covers, wrapping the
    storage instead of replacing it."""

    def _thread_with_hooks(self, pre_set=None, post_set=None):
        class _Plugin(MockPlugin):
            level = control(pre_set=pre_set, post_set=post_set)

        return make_initialised_thread(_Plugin())

    def test_pre_set_raising_rejects_the_write_before_anything_else_runs(self, qapp):
        def _reject(plugin, value):
            raise RuntimeError('disabled')

        thread_obj, plugin = self._thread_with_hooks(pre_set=_reject)
        failed = Collector()
        thread_obj.write_failed.connect(failed)
        thread_obj.request_write('level', 9.0)
        assert failed.calls == [('level', 'disabled')]
        assert plugin.level is None       # storage never ran
        assert plugin.change_calls == []  # write() never ran either - pre_set runs first

    def test_post_set_sees_the_value_already_stored(self, qapp):
        seen = []
        thread_obj, plugin = self._thread_with_hooks(post_set=lambda plugin, value: seen.append(plugin.level))
        thread_obj.request_write('level', 9.0)
        assert seen == [9.0]

    def test_write_is_optional_when_the_plugin_does_not_define_it(self, qapp):
        class _NoWritePlugin:
            level = control(post_set=lambda plugin, value: None)

            def open(self, settings):
                pass

            def close(self):
                pass

        thread_obj, plugin = make_initialised_thread(_NoWritePlugin())
        thread_obj.request_write('level', 9.0)
        assert plugin.level == 9.0  # storage + post_set alone are enough; write() was never required

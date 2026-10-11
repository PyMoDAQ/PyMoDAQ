"""Tests for Controller: the GUI-side handle to a device, over a real hardware thread."""
from __future__ import annotations

import threading

import numpy as np
import pytest

from pymodaq.control_modules.hardware import controller as controller_module
from pymodaq.control_modules.hardware.capabilities import Action, control, measurement
from pymodaq.control_modules.hardware.controller import Controller, controller_class
from pymodaq.control_modules.hardware.hardware_registry import HardwareKey, HardwareRegistry


class _Reading:
    def __init__(self, names):
        self._arrays = {name: np.arange(4.0) + 1 for name in names}

    def get_data_from_name(self, name):
        return self._arrays[name]


class Spectrometer:
    params: list = []
    spectrum = measurement(units='counts', shape=(4,))
    exposure = control(units='ms', lo=1, hi=1000, epsilon=0.1)

    def __init__(self):
        self.written = []

    def open(self, settings):
        pass

    def close(self):
        pass

    def read(self, names=None, fresh=True):
        return _Reading(names)

    def write(self, name, value):
        self.written.append((name, value))


@pytest.fixture
def registry():
    registry = HardwareRegistry()
    yield registry
    registry.close_all()


def attach(registry, hardware_class=Spectrometer, controller_id=0):
    key = HardwareKey(hardware_class=hardware_class, controller_id=controller_id)
    return key, registry.attach(key, hardware_class)


class TestGeneratedProperties:

    def test_one_property_per_declared_quantity(self):
        cls = controller_class(Spectrometer)
        assert issubclass(cls, Controller)
        assert isinstance(getattr(cls, 'spectrum'), property)
        assert isinstance(getattr(cls, 'exposure'), property)

    def test_measurement_property_has_no_setter(self):
        assert controller_class(Spectrometer).spectrum.fset is None

    def test_control_property_has_a_setter(self):
        assert controller_class(Spectrometer).exposure.fset is not None


class TestDeviceState:

    def test_connected_follows_the_device_status(self, registry, qtbot):
        key, ctrl = attach(registry)
        assert ctrl.connected is False
        ctrl.thread.ini_hardware()
        assert ctrl.connected is True
        ctrl.thread.close_hardware()
        assert ctrl.connected is False

    def test_controller_is_created_before_the_device_is_initialised(self, registry):
        key, ctrl = attach(registry)
        assert isinstance(ctrl, Controller)
        assert ctrl.capabilities.controls[0].name == 'exposure'


class TestWrite:

    def test_setting_a_control_writes_it_on_the_device(self, registry, qtbot):
        key, ctrl = attach(registry)
        ctrl.thread.ini_hardware()
        plugin = ctrl.thread._plugin
        ctrl.exposure = 20.0
        qtbot.waitUntil(lambda: plugin.written == [('exposure', 20.0)], timeout=2000)

    def test_a_successful_write_emits_written(self, registry, qtbot):
        key, ctrl = attach(registry)
        ctrl.thread.ini_hardware()
        with qtbot.waitSignal(ctrl.written, timeout=2000) as blocker:
            ctrl.exposure = 20.0
        assert blocker.args == ['exposure', 20.0]


class TestWriteTimeout:
    """written/write_failed never reaching this Controller at all must not leave a write
    outstanding forever - for a script driving it directly, same as for any GUI built on it."""

    def test_a_write_with_no_response_times_out(self, registry, qtbot, monkeypatch):
        monkeypatch.setattr(controller_module, 'WRITE_TIMEOUT_S', 0.05)
        key, ctrl = attach(registry)
        ctrl.thread.ini_hardware()
        # Simulate the answer never reaching this Controller at all - not the device refusing,
        # which write_failed already covers without any of this. Disconnects Controller's own
        # outgoing signal, not one owned by the hardware-thread object - thread-safe either way.
        ctrl.write_requested.disconnect(ctrl.thread.request_write)
        with qtbot.waitSignal(ctrl.write_failed, timeout=2000) as blocker:
            ctrl.exposure = 20.0
        name, message = blocker.args
        assert name == 'exposure'
        assert 'no response' in message

    def test_a_timely_response_cancels_the_write_timeout(self, registry, qtbot, monkeypatch):
        monkeypatch.setattr(controller_module, 'WRITE_TIMEOUT_S', 0.05)
        key, ctrl = attach(registry)
        ctrl.thread.ini_hardware()
        failures = []
        ctrl.write_failed.connect(lambda name, message: failures.append((name, message)))
        with qtbot.waitSignal(ctrl.written, timeout=2000):
            ctrl.exposure = 20.0
        qtbot.wait(150)  # well past the patched timeout - the already-cancelled timer must not fire late
        assert failures == []

    def test_a_successful_stop_cancels_the_write_timeout(self, registry, qtbot, monkeypatch):
        monkeypatch.setattr(controller_module, 'WRITE_TIMEOUT_S', 0.05)
        key, ctrl = attach(registry, hardware_class=Stoppable, controller_id=29)
        ctrl.thread.ini_hardware()
        ctrl.write_requested.disconnect(ctrl.thread.request_write)  # the write's own answer never arrives
        failures = []
        ctrl.write_failed.connect(lambda name, message: failures.append((name, message)))
        ctrl.axis = 5.0
        with qtbot.waitSignal(ctrl.action_done, timeout=2000):
            ctrl.stop('axis')
        qtbot.wait(150)  # well past the patched timeout - stop already resolved it, nothing left to time out
        assert failures == []

    def test_any_interrupts_action_cancels_it_not_just_one_named_stop(self, registry, qtbot, monkeypatch):
        monkeypatch.setattr(controller_module, 'WRITE_TIMEOUT_S', 0.05)

        class Abortable(Spectrometer):
            axis = control(units='mm', lo=0, hi=10,
                           actions={'abort': Action(lambda plugin: None, interrupts=True)})

        key, ctrl = attach(registry, hardware_class=Abortable, controller_id=30)
        ctrl.thread.ini_hardware()
        ctrl.write_requested.disconnect(ctrl.thread.request_write)
        failures = []
        ctrl.write_failed.connect(lambda name, message: failures.append((name, message)))
        ctrl.axis = 5.0
        with qtbot.waitSignal(ctrl.action_done, timeout=2000):
            ctrl.run_action('axis', 'abort')
        qtbot.wait(150)
        assert failures == []


class Stoppable(Spectrometer):
    axis = control(units='mm', lo=0, hi=10, stop=lambda plugin: plugin.stop_calls.append(True),
                   actions={'home': lambda plugin: plugin.home_calls.append(True)})

    def __init__(self):
        super().__init__()
        self.stop_calls = []
        self.home_calls = []


class TestReadTimeout:
    """Mirrors TestWriteTimeout: read() getting no answer at all must not hang forever either."""

    def test_a_read_with_no_response_times_out(self, registry, qtbot, monkeypatch):
        monkeypatch.setattr(controller_module, 'READ_TIMEOUT_S', 0.05)
        key, ctrl = attach(registry)
        ctrl.thread.ini_hardware()
        ctrl.subscribe_requested.disconnect(ctrl.thread.subscribe)  # the request never reaches the thread
        with qtbot.waitSignal(ctrl.read_failed, timeout=2000) as blocker:
            ctrl.read('exposure', lambda data: None)
        name, message = blocker.args
        assert name == 'exposure'
        assert 'no response' in message

    def test_a_timely_response_cancels_the_read_timeout(self, registry, qtbot, monkeypatch):
        monkeypatch.setattr(controller_module, 'READ_TIMEOUT_S', 0.05)
        key, ctrl = attach(registry)
        ctrl.thread.ini_hardware()
        failures = []
        ctrl.read_failed.connect(lambda name, message: failures.append((name, message)))
        received = []
        ctrl.read('exposure', received.append)
        qtbot.waitUntil(lambda: bool(received), timeout=2000)
        qtbot.wait(150)  # well past the patched timeout - the already-cancelled timer must not fire late
        assert failures == []

    def test_a_real_read_failure_is_relayed(self, registry, qtbot):
        key, ctrl = attach(registry)
        ctrl.thread.ini_hardware()
        ctrl.thread._plugin.read = lambda names=None, fresh=True: (_ for _ in ()).throw(RuntimeError('bus error'))
        with qtbot.waitSignal(ctrl.read_failed, timeout=2000) as blocker:
            ctrl.read('exposure', lambda data: None)
        assert blocker.args == ['exposure', 'bus error']


class TestStop:

    def test_stop_calls_the_declared_callback(self, registry, qtbot):
        key, ctrl = attach(registry, hardware_class=Stoppable, controller_id=23)
        ctrl.thread.ini_hardware()
        plugin = ctrl.thread._plugin
        ctrl.stop('axis')
        qtbot.waitUntil(lambda: plugin.stop_calls == [True], timeout=2000)

    def test_stop_before_open_raises(self, registry):
        key, ctrl = attach(registry)
        with pytest.raises(RuntimeError, match='not open'):
            ctrl.stop('exposure')

    def test_run_action_calls_a_differently_named_declared_callback(self, registry, qtbot):
        key, ctrl = attach(registry, hardware_class=Stoppable, controller_id=24)
        ctrl.thread.ini_hardware()
        plugin = ctrl.thread._plugin
        ctrl.run_action('axis', 'home')
        qtbot.waitUntil(lambda: plugin.home_calls == [True], timeout=2000)
        assert plugin.stop_calls == []  # only 'home' was called, not 'stop'

    def test_run_action_before_open_raises(self, registry):
        key, ctrl = attach(registry)
        with pytest.raises(RuntimeError, match='not open'):
            ctrl.run_action('exposure', 'home')

    def test_a_successful_action_emits_action_done_with_no_result(self, registry, qtbot):
        key, ctrl = attach(registry, hardware_class=Stoppable, controller_id=25)
        ctrl.thread.ini_hardware()
        with qtbot.waitSignal(ctrl.action_done, timeout=2000) as blocker:
            ctrl.stop('axis')
        assert blocker.args == ['axis', 'stop', None]  # Stoppable's stop callback reports nothing

    def test_an_action_returning_a_value_is_carried_by_action_done(self, registry, qtbot):
        class Reporting(Spectrometer):
            axis = control(units='mm', lo=0, hi=10, stop=lambda plugin: 4.2)

        key, ctrl = attach(registry, hardware_class=Reporting, controller_id=26)
        ctrl.thread.ini_hardware()
        with qtbot.waitSignal(ctrl.action_done, timeout=2000) as blocker:
            ctrl.stop('axis')
        assert blocker.args == ['axis', 'stop', 4.2]

    def test_a_failing_action_emits_action_failed(self, registry, qtbot):
        class Faulty(Spectrometer):
            axis = control(units='mm', lo=0, hi=10,
                           stop=lambda plugin: (_ for _ in ()).throw(RuntimeError('refused')))

        key, ctrl = attach(registry, hardware_class=Faulty, controller_id=27)
        ctrl.thread.ini_hardware()
        with qtbot.waitSignal(ctrl.action_failed, timeout=2000) as blocker:
            ctrl.stop('axis')
        assert blocker.args == ['axis', 'stop', 'refused']

    def test_run_action_forwards_the_checked_state_to_a_checkable_callback(self, registry, qtbot):
        class WithToggle(Spectrometer):
            spectrum = measurement(units='counts', shape=(4,), actions={
                'subtract_bkg': Action(lambda plugin, checked: plugin.toggle_calls.append(checked),
                                       checkable=True),
            })

            def __init__(self):
                super().__init__()
                self.toggle_calls = []

        key, ctrl = attach(registry, hardware_class=WithToggle, controller_id=28)
        ctrl.thread.ini_hardware()
        plugin = ctrl.thread._plugin
        ctrl.run_action('spectrum', 'subtract_bkg', True)
        qtbot.waitUntil(lambda: plugin.toggle_calls == [True], timeout=2000)


class TestLifecycle:

    def test_attach_poll_write_detach(self, registry, qtbot):
        key, ctrl = attach(registry)
        ctrl.thread.ini_hardware()
        plugin = ctrl.thread._plugin
        ctrl.poll('spectrum', 20.0)
        ctrl.exposure = 50.0
        qtbot.waitUntil(lambda: ctrl.spectrum is not None and len(plugin.written) == 1, timeout=2000)
        assert list(ctrl.spectrum) == [1.0, 2.0, 3.0, 4.0]
        assert plugin.written == [('exposure', 50.0)]
        registry.detach(key)
        assert not registry.is_known(key)


class TestPoll:

    def test_polled_measurement_updates_its_property(self, registry, qtbot):
        key, ctrl = attach(registry)
        ctrl.thread.ini_hardware()
        assert ctrl.spectrum is None
        ctrl.poll('spectrum', 20.0)
        qtbot.waitUntil(lambda: ctrl.spectrum is not None, timeout=2000)
        assert list(ctrl.spectrum) == [1.0, 2.0, 3.0, 4.0]

    def test_poll_before_open_raises(self, registry):
        key, ctrl = attach(registry)
        with pytest.raises(RuntimeError, match='not open'):
            ctrl.poll('spectrum', 20.0)

    def test_read_before_open_raises(self, registry):
        key, ctrl = attach(registry)
        with pytest.raises(RuntimeError, match='not open'):
            ctrl.read('spectrum', lambda data: None)

    def test_polls_are_cleared_when_the_device_closes(self, registry, qtbot):
        key, ctrl = attach(registry)
        ctrl.thread.ini_hardware()
        ctrl.poll('spectrum', 20.0)
        ctrl.thread.close_hardware()
        assert ctrl._polled == {}
        ctrl.thread.ini_hardware()
        assert ctrl.poll('spectrum', 20.0) is not None

    def test_polling_again_with_the_same_period_returns_the_same_subscription(self, registry):
        key, ctrl = attach(registry)
        ctrl.thread.ini_hardware()
        assert ctrl.poll('spectrum', 20.0) is ctrl.poll('spectrum', 20.0)

    def test_polling_again_with_another_period_raises(self, registry):
        key, ctrl = attach(registry)
        ctrl.thread.ini_hardware()
        ctrl.poll('spectrum', 20.0)
        with pytest.raises(ValueError, match='already polled'):
            ctrl.poll('spectrum', 50.0)

    def test_stop_poll_keeps_the_last_value(self, registry, qtbot):
        key, ctrl = attach(registry)
        ctrl.thread.ini_hardware()
        ctrl.poll('spectrum', 20.0)
        qtbot.waitUntil(lambda: ctrl.spectrum is not None, timeout=2000)
        ctrl.stop_poll('spectrum')
        last = ctrl.spectrum
        qtbot.wait(100)
        assert ctrl.spectrum is last
        assert 'spectrum' not in ctrl._polled

    def test_stop_poll_of_an_unpolled_name_is_a_noop(self, registry):
        key, ctrl = attach(registry)
        ctrl.stop_poll('spectrum')


class TestBlockingRead:

    def test_script_thread_gets_the_reading(self, registry, qtbot):
        key, ctrl = attach(registry)
        ctrl.thread.ini_hardware()
        result = {}

        def script():
            result['value'] = ctrl.read_blocking('spectrum', timeout=3)

        worker = threading.Thread(target=script)
        worker.start()
        qtbot.waitUntil(lambda: not worker.is_alive(), timeout=5000)
        assert list(result['value']) == [1.0, 2.0, 3.0, 4.0]

    def test_fails_at_once_when_the_device_is_not_open(self, registry):
        key, ctrl = attach(registry)
        with pytest.raises(RuntimeError, match='not open'):
            ctrl.read_blocking('spectrum')


class TestNewReading:

    def test_each_poll_reading_is_announced(self, registry, qtbot):
        key, ctrl = attach(registry)
        ctrl.thread.ini_hardware()
        with qtbot.waitSignal(ctrl.new_reading, timeout=2000) as blocker:
            ctrl.poll('spectrum', 20.0)
        assert blocker.args[0] == 'spectrum'
        ctrl.stop_poll('spectrum')


class Gained(Spectrometer):
    params = [{'name': 'gain', 'type': 'float', 'value': 1.0}]


class TestDeviceSettingsChanged:

    def test_a_plugin_driven_change_updates_the_settings_tree(self, registry, qtbot):
        key, ctrl = attach(registry, hardware_class=Gained, controller_id=20)
        ctrl.thread.ini_hardware()
        ctrl.thread._plugin_settings.child('gain').setValue(3.0)  # as the plugin would, on its own
        qtbot.waitUntil(lambda: ctrl.settings.child('gain').value() == 3.0, timeout=2000)

    def test_it_does_not_loop_back_as_a_write_to_the_device_settings(self, registry, qtbot):
        key, ctrl = attach(registry, hardware_class=Gained, controller_id=21)
        ctrl.thread.ini_hardware()
        calls = []
        ctrl.settings.sigTreeStateChanged.connect(lambda *_: calls.append(None))
        ctrl.thread._plugin_settings.child('gain').setValue(3.0)
        qtbot.waitUntil(lambda: ctrl.settings.child('gain').value() == 3.0, timeout=2000)
        # the device tree is unaffected a second time: no write was queued back to it
        assert ctrl.thread._plugin_settings.child('gain').value() == 3.0
        assert not ctrl._syncing_from_device


class Exposed(Spectrometer):
    params = [{'name': 'exposure', 'type': 'float', 'value': 1.0, 'limits': (1, 1000)}]
    exposure = control(units='ms', lo=1, hi=1000, setting=True)


class TestSettingBackedControl:

    def test_setting_the_property_commits_the_setting_not_write(self, registry, qtbot):
        key, ctrl = attach(registry, hardware_class=Exposed, controller_id=22)
        ctrl.thread.ini_hardware()
        ctrl.exposure = 500.0  # the scan-style write: a plain property assignment
        qtbot.waitUntil(lambda: ctrl.settings.child('exposure').value() == 500.0, timeout=2000)
        plugin = ctrl.thread._plugin
        assert plugin.written == []  # write() was never called for it


class TestConfigDefaults:
    """WRITE_TIMEOUT_S/READ_TIMEOUT_S come from config_template.toml's [hardware_module] section,
    not a hardcoded literal - but stay plain module globals (not read fresh on every call) so
    the rest of this file can keep monkeypatching them directly, as it did before this moved to
    config."""

    def test_write_timeout_comes_from_config(self):
        from pymodaq_utils.config import GlobalConfig as Config
        config = Config()
        assert controller_module.WRITE_TIMEOUT_S == config('pymodaq', 'hardware_module', 'write_timeout_s')

    def test_read_timeout_comes_from_config(self):
        from pymodaq_utils.config import GlobalConfig as Config
        config = Config()
        assert controller_module.READ_TIMEOUT_S == config('pymodaq', 'hardware_module', 'read_timeout_s')

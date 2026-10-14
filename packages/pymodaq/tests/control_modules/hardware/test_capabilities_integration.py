"""Integration test: one new-style plugin declaring mixed ``Capabilities``
(one ``Observable`` detector channel + one ``ContinuousVariable`` axis),
driven end-to-end through ``HardwareThread``.

This validates that the ``capabilities.py`` dataclasses are sufficient to
describe a real multi-channel instrument, and that HardwareThread's
existing new-style dispatch (``read`` / ``write``) works against such a plugin.
"""
from __future__ import annotations

import numpy as np

from pymodaq.control_modules.hardware.hardware_thread import HardwareThread
from pymodaq.control_modules.hardware.subscription import Subscription
from pymodaq.control_modules.hardware.capabilities import Capabilities, control, measurement
from pymodaq.utils.data import DataActuator, DataFromPlugins, DataToExport


SPECTRUM_SHAPE = (16,)


def one_shot(thread_obj, channel):
    """Read *channel* once through a one-shot subscription; return the collector of its readings."""
    sub = Subscription(channel, None)
    collector = Collector()
    sub.data_ready.connect(collector)
    thread_obj.subscribe(sub)
    return collector


class MockSpectrometerWithAxis:
    """New-style plugin: one 'position' axis (Variable) + one 'spectrum'
    detector channel (Observable). The spectrum baseline tracks the axis
    position so a write-then-snap round trip is observable.
    """

    params: list = []

    spectrum = measurement(label='Spectrum', units='counts', shape=SPECTRUM_SHAPE)
    position = control(label='Position', units='mm', lo=0.0, hi=10.0, epsilon=0.01)

    def __init__(self):
        self._position = 0.0
        self.open_called_with = None
        self.query_calls: list = []
        self.change_calls: list = []

    def open(self, settings) -> None:
        self.open_called_with = settings

    def close(self) -> None:
        pass

    def read(self, names=None, fresh=True):
        names = list(names) if names else ['spectrum', 'position']
        self.query_calls.append(names)
        dte = DataToExport('mock_spectrometer')
        for name in names:
            if name == 'spectrum':
                data = np.arange(SPECTRUM_SHAPE[0], dtype='float64') + self._position
                dte.append(DataFromPlugins(name='spectrum', data=[data]))
            elif name == 'position':
                dte.append(DataActuator('position', data=[np.array([self._position])]))
        return dte

    def write(self, name, value) -> None:
        self.change_calls.append((name, value))
        if name == 'position':
            self._position = float(value)

    def commit_settings(self, param) -> None:
        pass


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


def make_thread() -> HardwareThread:
    return HardwareThread(plugin_class=MockSpectrometerWithAxis, params_state=None)


class TestMixedCapabilitiesNewStylePlugin:

    def test_declared_capabilities_are_collected_from_the_class(self):
        caps: Capabilities = Capabilities.from_device(MockSpectrometerWithAxis)
        assert caps.measurements[0].name == 'spectrum'
        assert caps.controls[0].name == 'position'
        assert [m.name for m in caps.measurements] == ['spectrum']
        assert caps.measurements[0].shape == SPECTRUM_SHAPE
        assert [c.name for c in caps.controls] == ['position']
        assert caps.controls[0].lo == 0.0
        assert caps.controls[0].hi == 10.0
        assert caps.controls[0].epsilon == 0.01

    def test_snap_observable_channel_returns_declared_shape(self, qapp):
        thread_obj = make_thread()
        thread_obj.ini_hardware()

        collector = one_shot(thread_obj, 'spectrum')

        assert collector.count == 1
        spectrum, is_temp, _ = collector.last()
        assert is_temp is False
        assert spectrum.data[0].shape == SPECTRUM_SHAPE

    def test_write_then_read_variable_channel_round_trips(self, qapp):
        thread_obj = make_thread()
        thread_obj.ini_hardware()
        change_collector = Collector()
        thread_obj.write_done.connect(change_collector)

        thread_obj.request_write('position', 5.0)
        assert change_collector.count == 1
        assert change_collector.last() == ('position', 5.0)

        position, _, _ = one_shot(thread_obj, 'position').last()
        assert position.data[0][0] == 5.0

    def test_write_to_position_shifts_spectrum_baseline(self, qapp):
        thread_obj = make_thread()
        thread_obj.ini_hardware()
        thread_obj.request_write('position', 2.0)

        spectrum, _, _ = one_shot(thread_obj, 'spectrum').last()
        assert spectrum.data[0][0] == 2.0

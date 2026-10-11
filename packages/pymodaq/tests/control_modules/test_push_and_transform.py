import numpy as np

from pymodaq.control_modules.hardware.capabilities import Capabilities, measurement
from pymodaq.control_modules.hardware.hardware_thread import HardwareThread
from pymodaq.control_modules.hardware.subscription import Subscription


class _DTE:
    def __init__(self, data):
        self._data = data

    def get_data_from_name(self, name):
        return self._data[name]


class PushingPlugin:
    pushed = measurement(units='', push=True)
    polled = measurement(units='')
    params: list = []

    def __init__(self):
        self.read_names: list = []

    def open(self, settings):
        pass

    def close(self):
        pass

    def read(self, names=None, fresh=True):
        self.read_names.append(list(names))
        return _DTE({name: np.array([1.0, 2.0]) for name in names})


def make_thread():
    thread_obj = HardwareThread(plugin_class=PushingPlugin)
    thread_obj.ini_hardware()
    return thread_obj, thread_obj._plugin


class Collector:
    def __init__(self):
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)


def test_push_flag_round_trips_through_dict():
    caps = Capabilities.from_device(PushingPlugin)
    restored = Capabilities.from_dict(caps.to_dict())
    flags = {q.name: q.push for q in restored.measurements}
    assert flags == {'pushed': True, 'polled': False}


def test_pushed_channel_is_never_polled():
    thread_obj, plugin = make_thread()
    sub = Subscription('pushed', 20.0)
    thread_obj.subscribe(sub)
    assert 'pushed' not in thread_obj._timers
    thread_obj._read_period(20.0)
    assert plugin.read_names == []


def test_pushed_reading_reaches_subscribers_of_the_channel():
    thread_obj, plugin = make_thread()
    sub = Subscription('pushed', 20.0)
    got = Collector()
    sub.data_ready.connect(got)
    thread_obj.subscribe(sub)
    plugin.push_reading('pushed', np.array([7.0]))
    assert len(got.calls) == 1
    np.testing.assert_array_equal(got.calls[0][0], [7.0])


def test_transform_gets_a_copy_and_does_not_change_other_subscribers():
    thread_obj, plugin = make_thread()

    def zero_first(data):
        data[0] = 0.0
        return data

    mutating = Subscription('polled', 20.0, transform=zero_first)
    plain = Subscription('polled', 20.0)
    got_mutating, got_plain = Collector(), Collector()
    mutating.data_ready.connect(got_mutating)
    plain.data_ready.connect(got_plain)
    thread_obj.subscribe(mutating)
    thread_obj.subscribe(plain)
    thread_obj._read_period(20.0)
    np.testing.assert_array_equal(got_plain.calls[0][0], [1.0, 2.0])
    np.testing.assert_array_equal(got_mutating.calls[0][0], [0.0, 2.0])

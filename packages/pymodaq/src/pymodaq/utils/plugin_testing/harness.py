"""Helpers to exercise instrument plugins without hardware and without any visible GUI.

A plugin is driven the way PyMoDAQ's workers do it, but in the calling thread: the signals emitted by the plugin
(``move_done_signal``, ``dte_signal``) are waited for in a local Qt event loop, with a timeout. Keep the communication
with the instrument behind a small wrapper class (in the ``hardware`` folder of the plugin package), write a fake of it
with the same public methods, and run the real plugin class against the fake::

    from pymodaq.utils.plugin_testing import make_actuator, move_abs_and_wait

    def test_move_abs(monkeypatch):
        monkeypatch.setattr(daq_move_xxxx, 'XxxxWrapper', FakeWrapper)  # name of the wrapper in the plugin module
        actuator = make_actuator(daq_move_xxxx.DAQ_Move_Xxxx)
        assert actuator.initialized
        position = move_abs_and_wait(actuator, 2.5)  # a float is in the axis unit of the actuator
        assert position.value() == pytest.approx(2.5)
        actuator.close()

What the Dashboard does and the helpers reproduce: the target given to the plugin is expressed in the axis unit of the
actuator, ``move_done_signal`` is only emitted after ``poll_moving`` has been called, and a slave axis of a multi-axes
controller is given the controller of its master.
"""
from time import perf_counter, sleep
from typing import Callable, Optional, Union

from pyqtgraph import mkQApp
from qtpy.QtWidgets import QApplication

from pymodaq_data.data import DataToExport

from pymodaq.control_modules.thread_commands import ControllerStatus
from pymodaq.utils.data import DataActuator

TIMEOUT_MS = 5000


class SignalTimeout(AssertionError):
    """The expected signal was not emitted before the timeout."""


def wait_for_signal(signal, action: Callable[[], object], timeout_ms: int = TIMEOUT_MS,
                    poll: Optional[Callable[[], object]] = None):
    """Call ``action`` and return the first argument of the next emission of ``signal``.

    Raises ``SignalTimeout`` if nothing is emitted within ``timeout_ms``. The signal can be emitted before
    ``action`` returns (synchronous plugins): it is not missed. While waiting, the Qt events are processed and
    ``poll`` (if given) is called every few milliseconds. The wait does not rely on Qt timers, whose delivery slows
    down in a process where other tests left many widgets alive.
    """
    received = []

    def slot(*args):
        received.append(args[0] if args else None)

    signal.connect(slot)
    try:
        action()
        deadline = perf_counter() + timeout_ms / 1000
        while not received and perf_counter() < deadline:
            if poll is not None:
                poll()
            QApplication.processEvents()
            if not received:
                sleep(0.005)
    finally:
        signal.disconnect(slot)
    if not received:
        raise SignalTimeout(f'no signal emitted within {timeout_ms} ms')
    return received[0]


def _instantiate(plugin_class, controller, settings):
    # the plugins use Qt timers and signals: a QApplication must exist. pyqtgraph's mkQApp creates a bare one, without
    # the PyMoDAQ theme (applying it queues style events for every widget alive and is only useful in tests of the GUI)
    mkQApp('plugin_test')
    plugin = plugin_class()
    if controller is not None:
        # a plugin is given an existing controller only as a slave axis of a multi-axes controller
        plugin.settings.child('controller', 'controller_status').setValue(ControllerStatus.SLAVE)
    for name, value in settings.items():
        plugin.settings.child(name).setValue(value)
    return plugin


def make_actuator(plugin_class, controller=None, **settings):
    """Instantiate an actuator plugin and initialize it, as the Dashboard does.

    ``controller`` is only given for a slave axis of a multi-axes plugin (it is then set as ``Slave``), a master
    creates its own. The keyword arguments set top level settings before the initialization. Returns the plugin, with
    ``initialized`` and ``init_info`` set from the return of ``ini_stage``.
    """
    plugin = _instantiate(plugin_class, controller, settings)
    plugin.init_info, plugin.initialized = plugin.ini_stage(controller)
    return plugin


def make_detector(plugin_class, controller=None, **settings):
    """Instantiate a detector plugin and initialize it, as the Dashboard does (see ``make_actuator``)."""
    plugin = _instantiate(plugin_class, controller, settings)
    plugin.init_info, plugin.initialized = plugin.ini_detector(controller)
    return plugin


def _in_axis_unit(plugin, value: Union[float, DataActuator]) -> DataActuator:
    # the worker converts the target to the axis unit before calling the plugin: a plugin never receives another unit
    if not isinstance(value, DataActuator):
        return DataActuator(plugin._title, data=value, units=plugin.axis_unit)
    return value.units_as(plugin.axis_unit, inplace=False)


def _start_move(plugin, move: Callable[[], object]):
    # same sequence as ActuatorWorker.move_abs: reset the flags, move, then poll until the target is reached
    plugin.move_is_done = False
    plugin.ispolling = True
    move()
    plugin.poll_moving()


def _move_and_wait(plugin, move: Callable[[], object], timeout_ms: int) -> DataActuator:
    last_poll = [perf_counter()]

    def poll():
        # what the polling timer of the plugin does, at the same pace, but called from the wait loop
        if plugin.poll_timer.isActive() and perf_counter() - last_poll[0] >= plugin.poll_timer.interval() / 1000:
            last_poll[0] = perf_counter()
            plugin.check_target_reached()

    try:
        return wait_for_signal(plugin.move_done_signal, lambda: _start_move(plugin, move), timeout_ms, poll=poll)
    finally:
        plugin.poll_timer.stop()


def move_abs_and_wait(plugin, position: Union[float, DataActuator], timeout_ms: int = TIMEOUT_MS) -> DataActuator:
    """Move to an absolute position and return the position reported at the end.

    A float is taken in the axis unit of the actuator, a ``DataActuator`` in another unit is converted.
    """
    position = _in_axis_unit(plugin, position)
    return _move_and_wait(plugin, lambda: plugin.move_abs(position), timeout_ms)


def move_rel_and_wait(plugin, shift: Union[float, DataActuator], timeout_ms: int = TIMEOUT_MS) -> DataActuator:
    """Move by a relative amount (see ``move_abs_and_wait`` for the units) and return the position reported at the end"""
    shift = _in_axis_unit(plugin, shift)
    return _move_and_wait(plugin, lambda: plugin.move_rel(shift), timeout_ms)


def move_home_and_wait(plugin, timeout_ms: int = TIMEOUT_MS) -> DataActuator:
    """Send the actuator home and return the position reported at the end"""
    return _move_and_wait(plugin, plugin.move_home, timeout_ms)


def grab_and_wait(plugin, naverage: int = 1, timeout_ms: int = TIMEOUT_MS, **kwargs) -> DataToExport:
    """Start a grab and return the ``DataToExport`` emitted by the detector plugin"""
    return wait_for_signal(plugin.dte_signal, lambda: plugin.grab_data(naverage, **kwargs), timeout_ms)


def assert_units(data: DataToExport, units: Optional[str] = None):
    """Check that every data object of ``data`` carries a unit (and the given one, if ``units`` is not None)"""
    for dwa in data:
        assert dwa.units is not None and dwa.units != '', f'{dwa.name} has no units'
        if units is not None:
            assert dwa.units == units, f'{dwa.name} is in {dwa.units}, expected {units}'

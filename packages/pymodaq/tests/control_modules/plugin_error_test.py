"""An exception raised by a plugin is shown in the control module, not only logged"""
from types import SimpleNamespace

import pytest
import qt_themes
from pytest import fixture
from qtpy import QtWidgets

from pymodaq_utils.config import GlobalConfig
from pymodaq_utils.utils import ThreadCommand

from pymodaq.control_modules.daq_move import DAQ_Move, ActuatorWorker
from pymodaq.control_modules.daq_move_ui.ui_base import MoveLedState
from pymodaq_gui.utils.widgets import StatusPalette, Status
from pymodaq.control_modules.daq_viewer import DAQ_Viewer, DetectorWorker
from pymodaq.control_modules.thread_commands import (ThreadStatus, ThreadStatusMove, ControlToHardwareMove,
                                                     ControlToHardwareViewer)
from pymodaq.control_modules.move_utility_classes import DataActuatorType
from pymodaq.utils.data import DataActuator

config = GlobalConfig()


class StubActuator:
    axis_unit = 'mm'
    data_actuator_type = DataActuatorType.DataActuator
    ispolling = True
    controller = None

    def move_abs(self, position):
        raise RuntimeError('position out of range')

    def poll_moving(self):
        raise AssertionError('the polling must not start after a refused move')


class StubDetector:
    controller = None
    live_mode_available = False

    def grab_data(self, Naverage=1, live=True, **kwargs):
        raise RuntimeError('camera unplugged')


def _detector_worker() -> DetectorWorker:
    settings = {('main_settings', 'wait_time'): 0}
    return DetectorWorker('camera', settings, SimpleNamespace(module_name='stub', daq_type='DAQ2D'))


class Recorder:
    def __init__(self, signal):
        self.statuses = []
        signal.connect(self.statuses.append)


class TestWorkers:
    def test_actuator_worker_reports_a_refused_move(self, qapp):
        worker = ActuatorWorker('stub', DataActuator(data=0., units='mm'), 'axis')
        worker.plugin = StubActuator()
        recorder = Recorder(worker.status_sig)
        worker.queue_command(ThreadCommand(ControlToHardwareMove.MOVE_ABS, [DataActuator(data=500., units='mm')]))
        assert len(recorder.statuses) == 1
        status = recorder.statuses[0]
        assert status.command == ThreadStatus.ERROR
        assert 'position out of range' in status.attribute and ControlToHardwareMove.MOVE_ABS in status.attribute

    def test_detector_worker_reports_a_failed_grab(self, qapp):
        worker = _detector_worker()
        worker.plugin = StubDetector()
        worker.hardware_averaging = True
        worker.single_grab = True
        recorder = Recorder(worker.status_sig)
        worker.grab_data(Naverage=1, live=False)
        errors = [status for status in recorder.statuses if status.command == ThreadStatus.ERROR]
        assert errors and 'camera unplugged' in errors[0].attribute

    def test_detector_worker_reports_an_error_in_a_command(self, qapp):
        worker = _detector_worker()
        recorder = Recorder(worker.status_sig)
        worker.plugin = None  # a stop command on a worker without plugin raises
        worker.queue_command(ThreadCommand(ControlToHardwareViewer.STOP_GRAB))
        assert [status.command for status in recorder.statuses] == [ThreadStatus.ERROR]


@fixture
def theme(qtbot):
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0], style=config('gui', 'style', 'style')[0])
    return qt_themes.get_theme()


@fixture(params=['move', 'viewer'])
def module(request, qtbot, theme):
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    module = DAQ_Move(widget) if request.param == 'move' else DAQ_Viewer(widget)
    widget.show()
    yield module
    module.quit_fun()
    widget.close()


class TestControlModule:
    def test_error_is_displayed_and_marks_the_module(self, module):
        name_style = module.ui.get_action('name').widget.styleSheet()
        messages = []
        module.status_sig.connect(messages.append)
        module.thread_status(ThreadCommand(ThreadStatus.ERROR, 'move_abs: position out of range'))
        assert module._in_error
        assert messages == ['Error: move_abs: position out of range']
        assert module.ui.get_action('name').widget.styleSheet() == name_style  # the name colour is not changed

    def test_a_message_does_not_clear_the_error(self, module):
        module.thread_status(ThreadCommand(ThreadStatus.ERROR, 'oops'))
        module.thread_status(ThreadCommand(ThreadStatus.UPDATE_STATUS, 'just a message'))
        assert module._in_error

    def test_module_is_back_to_normal_when_the_hardware_answers(self, module):
        module.thread_status(ThreadCommand(ThreadStatus.ERROR, 'oops'))
        module.thread_status(ThreadCommand(ThreadStatus.CLOSE, ['Hardware closed']))  # any answer of the hardware
        assert not module._in_error


def test_move_status_led_follows_the_error(qtbot, theme):
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    move = DAQ_Move(widget)
    widget.show()
    led = move.ui.status_led
    icon_colors = []
    move.ui.get_action('ini_actuator').set_icon = lambda name, color: icon_colors.append(color)  # init button colour

    move.thread_status(ThreadCommand(ThreadStatus.ERROR, 'move_abs: position out of range'))
    assert not icon_colors  # an error of a command does not touch the init button
    assert led.get_state() == MoveLedState.ERROR
    assert led.toolTip() == 'move_abs: position out of range'
    assert dict(led._states)[MoveLedState.ERROR] == StatusPalette.color(Status.ERROR)

    move.thread_status(ThreadCommand(ThreadStatus.CLOSE, ['Hardware closed']))  # the hardware answers
    assert led.get_state() == MoveLedState.UNINITIALIZED
    assert led.toolTip() == ''

    move.thread_status(ThreadCommand(ThreadStatus.ERROR, 'oops'))
    move.ui.move_done = False  # what DAQ_Move does when it sends a move order
    assert led.get_state() == MoveLedState.MOVING

    move.thread_status(ThreadCommand(ThreadStatus.INI_HARDWARE, dict(initialized=False, info='no device found')))
    assert led.get_state() == MoveLedState.ERROR  # a failed initialization is shown, not only a grey LED
    assert led.toolTip() == 'no device found'
    assert icon_colors[-1] == theme.orange  # the init button: orange after a failed initialization
    move.thread_status(ThreadCommand(ThreadStatus.INI_HARDWARE, dict(initialized=True, info='', controller=None)))
    assert led.get_state() == MoveLedState.IDLE
    assert icon_colors[-1] == theme.green

    move.quit_fun()
    widget.close()


class TestPolling:
    @staticmethod
    def _plugin(fail_in_loop: bool):
        calls = SimpleNamespace(timer_stopped=False, statuses=[], values=[])

        def get_actuator_value():
            raise RuntimeError('encoder lost')

        return SimpleNamespace(
            calls=calls, settings={'timeout': 100}, move_is_done=False, start_time=0, _current_value=None,
            _condition_to_reach_target=lambda: not fail_in_loop, get_actuator_value=get_actuator_value,
            poll_timer=SimpleNamespace(stop=lambda: setattr(calls, 'timer_stopped', True)),
            emit_status=calls.statuses.append, emit_value=calls.values.append,
            epsilon=0.1, _target_value=None,
        )

    @pytest.mark.parametrize('fail_in_loop', [True, False])
    def test_error_while_polling_is_reported(self, fail_in_loop):
        from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
        plugin = self._plugin(fail_in_loop)
        DAQ_Move_base.check_target_reached(plugin)
        assert plugin.calls.timer_stopped
        assert [status.command for status in plugin.calls.statuses] == [ThreadStatus.ERROR]
        assert 'encoder lost' in plugin.calls.statuses[0].attribute
        assert not plugin.calls.values  # no value is emitted after the failure


def test_viewer_init_button_colours(qtbot, theme):
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    viewer = DAQ_Viewer(widget)
    widget.show()
    icon_colors = []
    viewer.ui.get_action('ini_detector').set_icon = lambda name, color: icon_colors.append(color)

    viewer.thread_status(ThreadCommand(ThreadStatus.INI_HARDWARE, dict(initialized=False, info='no camera')))
    assert icon_colors[-1] == theme.orange  # failed initialization
    viewer.thread_status(ThreadCommand(ThreadStatus.CLOSE, ['Hardware closed']))
    assert icon_colors[-1] == theme.red  # deinitialized
    viewer.thread_status(ThreadCommand(ThreadStatus.ERROR, 'camera unplugged'))
    assert icon_colors[-1] == theme.red  # an error of a command does not touch the init button

    viewer.quit_fun()
    widget.close()

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


def _led_state(module):
    return module.ui.status_led.get_state() if isinstance(module, DAQ_Move) else None


class TestControlModule:
    def test_error_is_displayed_and_marks_the_module(self, module):
        messages = []
        module.status_sig.connect(messages.append)
        module.thread_status(ThreadCommand(ThreadStatus.ERROR, 'move_abs: position out of range'))
        assert module._in_error
        assert messages == ['Error: move_abs: position out of range']

    def test_name_color_is_not_changed(self, module):
        before = module.ui.get_action('name').widget.styleSheet()
        module.thread_status(ThreadCommand(ThreadStatus.ERROR, 'oops'))
        assert module.ui.get_action('name').widget.styleSheet() == before

    def test_a_message_does_not_clear_the_error(self, module):
        module.thread_status(ThreadCommand(ThreadStatus.ERROR, 'oops'))
        module.thread_status(ThreadCommand(ThreadStatus.UPDATE_STATUS, 'just a message'))
        assert module._in_error

    def test_module_is_back_to_normal_when_the_hardware_answers(self, module):
        module.thread_status(ThreadCommand(ThreadStatus.ERROR, 'oops'))
        module.thread_status(ThreadCommand(ThreadStatus.CLOSE, ['Hardware closed']))  # any answer of the hardware
        assert not module._in_error


class TestMoveLed:
    @fixture
    def move(self, qtbot, theme):
        widget = QtWidgets.QWidget()
        qtbot.addWidget(widget)
        move = DAQ_Move(widget)
        widget.show()
        yield move
        move.quit_fun()
        widget.close()

    def test_led_is_orange_with_the_error_as_tooltip(self, move):
        move.thread_status(ThreadCommand(ThreadStatus.ERROR, 'move_abs: position out of range'))
        led = move.ui.status_led
        assert led.get_state() == MoveLedState.ERROR
        assert led.toolTip() == 'move_abs: position out of range'
        assert dict(led._states)[MoveLedState.ERROR] == StatusPalette.color(Status.ERROR)

    def test_led_goes_back_when_the_hardware_answers(self, move):
        move.thread_status(ThreadCommand(ThreadStatus.ERROR, 'oops'))
        move.thread_status(ThreadCommand(ThreadStatus.CLOSE, ['Hardware closed']))
        assert move.ui.status_led.get_state() == MoveLedState.UNINITIALIZED
        assert move.ui.status_led.toolTip() == ''

    def test_next_move_order_replaces_the_error(self, move):
        move.thread_status(ThreadCommand(ThreadStatus.ERROR, 'oops'))
        move.ui.move_done = False  # what DAQ_Move does when it sends a move order
        assert move.ui.status_led.get_state() == MoveLedState.MOVING

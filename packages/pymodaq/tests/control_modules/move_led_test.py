"""The status LED of DAQ_Move shows a move even when the order is not sent through DAQ_Move.move_abs"""
import pytest
import qt_themes
from qtpy import QtWidgets

from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.thread_commands import ControlToHardwareMove
from pymodaq.control_modules.ui_utils import LedState
from pymodaq.utils.data import DataActuator
from pymodaq_utils.config import GlobalConfig
from pymodaq_utils.utils import ThreadCommand

config = GlobalConfig()


@pytest.fixture
def actuator(qtbot):
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0], style=config('gui', 'style', 'style')[0])
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    prog = DAQ_Move(widget)
    widget.show()
    prog.ui.actuator_init = True  # as if initialized
    yield prog
    prog.quit_fun()
    widget.close()


@pytest.mark.parametrize('command', [ControlToHardwareMove.MOVE_ABS, ControlToHardwareMove.MOVE_REL,
                                     ControlToHardwareMove.MOVE_HOME])
def test_direct_move_command_turns_the_led_to_running(actuator, command):
    assert not actuator.ui._is_busy()
    actuator.command_hardware.emit(ThreadCommand(command, attribute=[DataActuator('a', data=1.), True]))
    assert actuator.ui._is_busy()
    assert not actuator.move_done_bool


def test_other_commands_do_not(actuator):
    actuator.command_hardware.emit(ThreadCommand(ControlToHardwareMove.STOP_MOTION))
    assert not actuator.ui._is_busy()


# ---- DAQ_Viewer ----
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.control_modules.thread_commands import ControlToHardwareViewer
from pymodaq_data.data import DataToExport


@pytest.fixture
def detector(qtbot):
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0], style=config('gui', 'style', 'style')[0])
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    prog = DAQ_Viewer(widget)
    widget.show()
    prog.ui.detector_init = True  # as if initialized
    yield prog
    prog.quit_fun()
    widget.close()


@pytest.mark.parametrize('command', [ControlToHardwareViewer.SINGLE, ControlToHardwareViewer.GRAB])
def test_direct_grab_command_turns_the_viewer_led_to_running_until_data(detector, command):
    assert not detector.ui._is_busy()
    detector.command_hardware.emit(ThreadCommand(command, dict(Naverage=1)))
    assert detector.ui._is_busy()
    detector.grab_done_signal.emit(DataToExport('d'))
    assert not detector.ui._is_busy()


def test_stop_grab_clears_the_viewer_led(detector):
    detector.command_hardware.emit(ThreadCommand(ControlToHardwareViewer.SINGLE, dict(Naverage=1)))
    detector.command_hardware.emit(ThreadCommand(ControlToHardwareViewer.STOP_GRAB))
    assert not detector.ui._is_busy()

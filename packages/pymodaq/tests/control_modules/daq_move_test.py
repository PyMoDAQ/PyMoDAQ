import numpy as np

from qtpy import QtWidgets
import pytest
from pytest import fixture
import qt_themes
from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.move_utility_classes import HW_SETTINGS_KEY as ACTUATOR_SETTINGS_KEY
from pymodaq.control_modules.utils import ControlModule

from pymodaq_utils.config import GlobalConfig
from pymodaq.utils.data import DataActuator

config = GlobalConfig()


@fixture
def daq_move_no_ui(qtbot):
    prog = DAQ_Move()
    yield prog
    prog.quit()
    qtbot.wait(200)


@fixture
def daq_move_ui(qtbot):
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0],
                        style=config('gui', 'style', 'style')[0])
    prog = DAQ_Move(widget)
    widget.show()
    yield prog
    prog.quit()
    qtbot.wait(200)


class TestMantatoryAttributes:
    def test_methods(self, daq_move_no_ui):
        assert 'units' in daq_move_no_ui.__dir__()
        assert hasattr(daq_move_no_ui, 'title')


class TestMethods:
    def test_overriden(self):
        assert ControlModule.stop_grab != DAQ_Move.stop_grab
        assert ControlModule.grab != DAQ_Move.grab
        assert ControlModule.quit != DAQ_Move.quit
        assert ControlModule.init_hardware != DAQ_Move.init_hardware


class TestDAQMove:
    def test_data_emit(self, daq_move_ui, qtbot):
        daq_move_ui.actuator = 'Mock'

        with qtbot.waitSignal(daq_move_ui.init_signal, timeout=10000) as blocker:
            daq_move_ui.init_hardware_ui(True)
        assert blocker.args[0] is True

        POSITION = 34.5
        TIMEOUT = int(2 * daq_move_ui.settings[ACTUATOR_SETTINGS_KEY, 'tau'])
        with qtbot.waitSignal(daq_move_ui.move_done_signal, timeout=TIMEOUT) as blocker:
            with qtbot.waitSignal(daq_move_ui.current_value_signal, timeout=1000) as val_blocker:
                daq_move_ui.move_abs(POSITION)

        assert isinstance(val_blocker.args[0], DataActuator)
        assert val_blocker.args[0].name == daq_move_ui.title

        data = blocker.args[0]
        assert isinstance(data, DataActuator)
        assert data.value() == pytest.approx(POSITION,
                                             abs=daq_move_ui.settings[ACTUATOR_SETTINGS_KEY, 'epsilon'])
        assert data.name == daq_move_ui.title

    def test_axis_management(self, daq_move_ui):
        daq_move_ui.actuator = 'Mock'
        pass
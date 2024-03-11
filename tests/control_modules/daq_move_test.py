import os
from collections import OrderedDict
import numpy as np

from qtpy import QtWidgets, QtCore
import pytest
from pytest import fixture, approx

from pymodaq.control_modules import daq_move as daqmv
from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.utils import ControlModule

from pymodaq.utils.conftests import qtbotskip, main_modules_skip
from pymodaq.utils.config import Config

from pymodaq.utils.data import DataActuator

config = Config()
config_viewer = daqmv.config


@fixture
def init_qt(qtbot):
    return qtbot


@fixture
def ini_daq_move_without_ui(init_qt):
    qtbot = init_qt
    prog = DAQ_Move()
    return prog, qtbot


@fixture
def ini_daq_move_ui(init_qt):
    qtbot = init_qt
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    prog = DAQ_Move(widget)
    widget.show()
    yield prog, qtbot, widget
    widget.close()


class TestMantatoryAttributes:
    def test_methods(self, ini_daq_move_without_ui):
        actuator, qtbot = ini_daq_move_without_ui
        assert 'units' in actuator.__dir__()
        assert hasattr(actuator, 'title')


class TestMethods:
    def test_overriden(self):
        assert ControlModule.stop_grab != DAQ_Move.stop_grab
        assert ControlModule.grab != DAQ_Move.grab
        assert ControlModule.quit_fun != DAQ_Move.quit_fun
        assert ControlModule.init_hardware != DAQ_Move.init_hardware


class TestDAQMove:
    def test_data_emit(self, ini_daq_move_ui):
        daq_move, qtbot, widget = ini_daq_move_ui
        daq_move.actuator = 'Mock'

        with qtbot.waitSignal(daq_move.init_signal, timeout=10000) as blocker:
            daq_move.init_hardware_ui(True)
        assert blocker.args[0] is True

        POSITION = 34.5
        TIMEOUT = int(2 * daq_move.settings['move_settings', 'tau'])
        with qtbot.waitSignal(daq_move.move_done_signal, timeout=TIMEOUT) as blocker:
            with qtbot.waitSignal(daq_move.current_value_signal, timeout=1000) as val_blocker:
                daq_move.move_abs(POSITION)
        assert isinstance(val_blocker.args[0], DataActuator)
        assert val_blocker.args[0].name == daq_move.title

        data = blocker.args[0]
        assert isinstance(data, DataActuator)

        assert data.value() == pytest.approx(POSITION,
                                             abs=daq_move.settings['move_settings', 'epsilon'])
        assert data.name == daq_move.title

        daq_move.quit_fun()
        QtWidgets.QApplication.processEvents() #make sure to properly terminate all the threads!

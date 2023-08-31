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
        assert ControlModule.init_hardware_ui != DAQ_Move.init_hardware_ui



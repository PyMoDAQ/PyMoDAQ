import os
from collections import OrderedDict
import numpy as np

from qtpy import QtWidgets, QtCore
import pytest
from pytest import fixture, approx

from pymodaq.control_modules import daq_move as daqmv
from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.utils import ControlModule
from pymodaq.daq_utils.gui_utils.dock import DockArea
from pymodaq.control_modules.utils import DAQ_TYPES, DET_TYPES, get_viewer_plugins
from pymodaq.daq_utils.conftests import qtbotskip, main_modules_skip
from pymodaq.daq_utils.config import Config
from pymodaq.daq_utils.parameter import utils as putils
from pymodaq.daq_utils.parameter import Parameter
from pymodaq.daq_utils.h5modules import H5BrowserUtil

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
    return prog, qtbot, widget


class TestMethods:
    def test_overriden(self):
        assert ControlModule.stop_grab != DAQ_Move.stop_grab
        assert ControlModule.grab != DAQ_Move.grab
        assert ControlModule.quit_fun != DAQ_Move.quit_fun
        assert ControlModule.init_hardware != DAQ_Move.init_hardware
        assert ControlModule.init_hardware_ui != DAQ_Move.init_hardware_ui


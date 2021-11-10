from qtpy import QtWidgets, QtCore
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_viewer import daq_viewer_main as daqvm
import pyqtgraph as pg
from pathlib import Path
import pytest
from pytest import fixture, approx
import numpy as np
import pyqtgraph as pg

@fixture
def init_qt(qtbot):
    return qtbot

class TestGeneral:

    def test_main(self, init_qt):
        qtbot = init_qt
        daqvm.main(False)


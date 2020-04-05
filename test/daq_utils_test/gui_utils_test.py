import numpy as np
from PyQt5 import QtWidgets
import pytest
from pymodaq.daq_utils import daq_utils
from pymodaq.daq_utils import gui_utils as gutils
from pyqtgraph.dockarea import Dock
import datetime

class TestDockArea:
    moved = False
    def track_signal(self):
        self.moved = True

    def test_dockarea(self, qtbot):
        area = gutils.DockArea()
        dock1 = Dock('test1')
        dock2 = Dock('tes2')
        area.addDock(dock1)
        area.addDock(dock2)

        area.dock_signal.connect(self.track_signal)
        area.moveDock(dock2, 'below', dock1)
        QtWidgets.QApplication.processEvents()
        assert self.moved is True



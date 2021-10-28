import numpy as np
from qtpy import QtWidgets, QtCore
import sys
import pytest
from pymodaq.daq_utils import daq_utils
from pymodaq.daq_utils import gui_utils as gutils
from pyqtgraph.dockarea import Dock, DockArea
import datetime

#
# class TestDockArea:
#     moved = False
#
#     def track_signal(self):
#         self.moved = True
#
#     def test_dockarea(self, qtbot):
#         area = gutils.DockArea()
#         dock1 = Dock('test1')
#         dock2 = Dock('tes2')
#         area.addDock(dock1)
#         area.addDock(dock2)
#
#         area.dock_signal.connect(self.track_signal)
#         area.moveDock(dock2, 'below', dock1)
#         QtWidgets.QApplication.processEvents()
#         assert self.moved is True

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.show()

    dock = Dock(name='Test Dock', area=area)
    area.addDock(dock)

    QtCore.QThread.sleep(2)
    dock.close()
    QtWidgets.QApplication.processEvents()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
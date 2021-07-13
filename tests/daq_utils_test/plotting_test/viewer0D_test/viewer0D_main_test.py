from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QLocale
import sys
import numpy as np
import pytest

from pymodaq.daq_utils.plotting.viewer0D import viewer0D_main as v_0D

def test_0D_viewer(qtbot):
    # Form = QtWidgets.QWidget()
    # prog = v_0D.Viewer0D(Form)
    # from pymodaq.daq_utils.daq_utils import gauss1D
    #
    # x = np.linspace(0, 200, 201)
    # y1 = gauss1D(x, 75, 25)
    # y2 = gauss1D(x, 120, 50, 2)
    # Form.show()
    # for ind, data in enumerate(y1):
    #     prog.show_data([[data], [y2[ind]]])
    #     QtWidgets.QApplication.processEvents()
    #
    # qtbot.addWidget(prog)
    # qtbot.mouseClick(prog.ui.clear_pb, QtCore.Qt.LeftButton)
    # assert np.array_equal(prog.x_axis, np.array([]))
    pass
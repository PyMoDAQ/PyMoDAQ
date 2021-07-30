from PyQt5 import QtWidgets
from unittest import mock

from pyqtgraph.graphicsItems.LinearRegionItem import LinearRegionItem
from pymodaq.daq_utils.exceptions import ExpectedError
from pymodaq.daq_utils.plotting.viewer1D.viewer1Dbasic import Viewer1DBasic

class TestViewer1DBasic:
    def test_init(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer1DBasic()

        assert isinstance(prog.parent, QtWidgets.QWidget)
        assert not prog.data_to_export
        assert not prog.datas
        assert not prog._x_axis
        assert not prog.labels

        qtbot.addWidget(Form)

    def test_show(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer1DBasic()

        prog.parent.setVisible(False)
        assert not prog.parent.isVisible()

        prog.show()
        assert prog.parent.isVisible()

        prog.show(False)
        assert not prog.parent.isVisible()

        qtbot.addWidget(Form)

    def test_update_region(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer1DBasic()

        ROI = LinearRegionItem()

        prog.update_region(ROI)

        qtbot.addWidget(Form)

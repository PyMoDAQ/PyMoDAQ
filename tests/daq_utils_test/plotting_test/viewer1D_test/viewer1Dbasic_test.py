from PyQt5 import QtWidgets
from unittest import mock
import pytest
import numpy as np

from pyqtgraph.graphicsItems.PlotItem.PlotItem import PlotItem
from pyqtgraph.graphicsItems.InfiniteLine import InfiniteLine
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

    def test_update_line(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer1DBasic()

        IL = InfiniteLine()

        prog.update_line(IL)

        qtbot.addWidget(Form)

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1Dbasic.logger.exception')
    def test_update_labels(self, mock_except, qtbot):
        mock_except.side_effect = [ExpectedError]

        Form = QtWidgets.QWidget()
        prog = Viewer1DBasic()

        datas = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)
        prog.datas = datas

        item = PlotItem()
        prog.legend.addItem(item, 'item_00')
        prog.plot_channels = ['CH_00', 'CH_01', 'CH_02', 'CH_03']

        labels = ['CH_00', 'CH_01']

        prog.update_labels(labels)

        assert prog._labels == ['CH_00', 'CH_01', 'CH02', 'CH03']

        prog.legend = None

        with pytest.raises(ExpectedError):
            prog.update_labels(labels)

        qtbot.addWidget(Form)

    def test_show_data(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer1DBasic()

        datas = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)

        prog.plot_channels = ['CH_00', 'CH_01', 'CH_02', 'CH_03']

        item = PlotItem()
        prog.legend.addItem(item, 'item_00')

        prog.show_data(datas)

        qtbot.addWidget(Form)

    def test_x_axis(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer1DBasic()

        data = np.linspace(1, 10, 10)
        label = ['CH_00', 'CH_01']
        units = 'nm'

        x_axis = {'data': data, 'label': label, 'units': units}

        prog.x_axis = x_axis

        assert np.array_equal(prog._x_axis, data)

        qtbot.addWidget(Form)

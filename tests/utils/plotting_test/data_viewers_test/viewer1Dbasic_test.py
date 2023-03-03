from qtpy import QtWidgets
import pytest
import numpy as np

from pyqtgraph.graphicsItems.PlotItem.PlotItem import PlotItem
from pyqtgraph.graphicsItems.InfiniteLine import InfiniteLine
from pyqtgraph.graphicsItems.LinearRegionItem import LinearRegionItem
from pymodaq.utils.plotting.data_viewers.viewer1Dbasic import Viewer1DBasic
from pymodaq.utils.conftests import qtbotskip
pytestmark = pytest.mark.skipif(qtbotskip, reason='qtbot issues but tested locally')


@pytest.fixture
def init_viewer1Dbasic(qtbot):
    form = QtWidgets.QWidget()
    prog = Viewer1DBasic(form)
    qtbot.addWidget(form)
    yield prog
    form.close()


class TestViewer1DBasic:
    def test_init(self, init_viewer1Dbasic):
        prog = init_viewer1Dbasic

        assert isinstance(prog.parent, QtWidgets.QWidget)
        assert not prog.data_to_export
        assert not prog.datas
        assert not prog._x_axis
        assert not prog.labels

    def test_show(self, init_viewer1Dbasic):
        prog = init_viewer1Dbasic

        prog.parent.setVisible(False)
        assert not prog.parent.isVisible()

        prog.show()
        assert prog.parent.isVisible()

        prog.show(False)
        assert not prog.parent.isVisible()

    def test_update_region(self, init_viewer1Dbasic):
        prog = init_viewer1Dbasic

        ROI = LinearRegionItem()

        prog.update_region(ROI)

    def test_update_line(self, init_viewer1Dbasic):
        prog = init_viewer1Dbasic

        IL = InfiniteLine()

        prog.update_line(IL)

    def test_update_labels(self, init_viewer1Dbasic):

        prog = init_viewer1Dbasic
        datas = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)
        prog.datas = datas
        item = PlotItem()
        prog.legend.addItem(item, 'item_00')
        prog.plot_channels = ['CH_00', 'CH_01', 'CH_02', 'CH_03']
        labels = ['CH_00', 'CH_01']
        prog.update_labels(labels)
        assert prog._labels == ['CH_00', 'CH_01', 'CH02', 'CH03']
        prog.legend = None
        prog.update_labels(labels)

    def test_show_data(self, init_viewer1Dbasic):
        prog = init_viewer1Dbasic

        datas = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)

        prog.plot_channels = ['CH_00', 'CH_01', 'CH_02', 'CH_03']

        item = PlotItem()
        prog.legend.addItem(item, 'item_00')

        prog.show_data(datas)

    def test_x_axis(self, init_viewer1Dbasic):
        prog = init_viewer1Dbasic

        data = np.linspace(1, 10, 10)
        label = ['CH_00', 'CH_01']
        units = 'nm'

        x_axis = {'data': data, 'label': label, 'units': units}

        prog.x_axis = x_axis

        assert np.array_equal(prog._x_axis, data)

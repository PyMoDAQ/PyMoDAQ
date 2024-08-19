from pyqtgraph.parametertree import Parameter
import pyqtgraph as pg
import numpy as np
import pytest

from qtpy import QtWidgets
from pyqtgraph import ROI
from unittest import mock
from collections import OrderedDict

from pymodaq.utils import data as data_mod
from pymodaq.utils import math_utils as mutils
from pymodaq.post_treatment.daq_measurement.daq_measurement_main import DAQ_Measurement
from pymodaq.utils.plotting.data_viewers.viewer1D import Viewer1D
from pymodaq.utils.exceptions import ExpectedError, Expected_1, Expected_2
from pymodaq.utils.conftests import qtbotskip
from pymodaq.utils.math_utils import gauss1D

#pytestmark = pytest.mark.skipif(qtbotskip, reason='qtbot issues but tested locally')


@pytest.fixture
def init_viewer1d(qtbot):
    widget = QtWidgets.QWidget()
    prog = Viewer1D(widget)
    qtbot.addWidget(widget)
    x = np.linspace(0, 200, 201)
    y1 = mutils.gauss1D(x, 75, 25)
    y2 = mutils.gauss1D(x, 120, 50, 2)
    data = data_mod.DataRaw('mydata', data=[y1, y2],
                   axes=[data_mod.Axis('myaxis', 'units', data=x)])
    yield prog, data
    widget.close()


class TestLineoutPlotter:
    # Most test should be made in the base class
    pass


class TestDataDisplayer:
    #TODO
    pass


class TestView1D:
    #TODO
    pass


class TestViewer1D:
    def test_init(self, init_viewer1d):
        prog, data = init_viewer1d
        assert prog.viewer_type == 'Data1D'
        assert prog.parent is not None

    def test_do_math(self, init_viewer1d):
        prog, data = init_viewer1d
        assert not prog.is_action_checked('do_math')
        prog.get_action('do_math').trigger()
        assert prog.is_action_checked('do_math')
        prog.get_action('do_math').trigger()
        assert not prog.is_action_checked('do_math')

    def test_scatter(self, init_viewer1d):
        prog, data = init_viewer1d
        prog.show_data(data)
        assert not prog.is_action_checked('scatter')
        prog.get_action('scatter').trigger()
        assert prog.is_action_checked('scatter')

    def test_xyplot_action(self, init_viewer1d):
        prog, data = init_viewer1d
        prog.show_data(data)
        assert prog.is_action_visible('scatter')
        assert prog.labels == data.labels

        assert not prog.is_action_checked('xyplot')
        prog.get_action('xyplot').trigger()
        assert prog.is_action_checked('xyplot')
        prog.get_action('xyplot').trigger()
        assert not prog.is_action_checked('xyplot')

    def test_crosshairClicked(self, init_viewer1d):
        prog, data = init_viewer1d
        prog.trigger_action('crosshair')
        assert prog.is_action_visible('x_label')
        assert prog.is_action_visible('y_label')

    def test_extra_scatter(self, init_viewer1d):
        prog, data = init_viewer1d

        xlow = np.linspace(0, 200, 21)
        ylow = gauss1D(xlow, 75, 25)

        scatter_dwa = data_mod.DataRaw(
            'scatter', data=[ylow],
            axes=[data_mod.Axis('myaxis', 'units', data=xlow, index=0, spread_order=0)],
            labels=['subsampled'],
            symbol='d',
            symbol_size=18)

        prog.show_data(data, scatter_dwa=scatter_dwa)

    def test_unsorted(self, init_viewer1d):
        prog, data = init_viewer1d

        x = np.linspace(0, 200, 201)
        xaxis = np.concatenate((x, x[::-1]))
        y = gauss1D(x, 75, 25)
        yaxis = np.concatenate((y, -y))
        data = data_mod.DataRaw('mydata', data=[yaxis],
                                axes=[data_mod.Axis('myaxis', 'units', data=xaxis)])
        prog.show_data(data)

    def test_random(self, init_viewer1d):
        prog, data = init_viewer1d
        x = np.random.randint(201, size=201)
        y1 = gauss1D(x, 75, 25)
        y2 = gauss1D(x, 120, 50, 2)

        QtWidgets.QApplication.processEvents()
        data = data_mod.DataRaw(
            'mydata', data=[y1, y2],
            axes=[data_mod.Axis('myaxis', 'units', data=x, index=0, spread_order=0)],
            nav_indexes=(0, ))
        prog.show_data(data)

    def test_errors(self, init_viewer1d):
        prog, data = init_viewer1d
        x = np.linspace(0, 200, 201)
        y1 = gauss1D(x, 75, 25)
        y2 = gauss1D(x, 120, 50, 2)

        QtWidgets.QApplication.processEvents()
        data = data_mod.DataRaw(
            'mydata', data=[y1, y2],
            axes=[data_mod.Axis('myaxis', 'units', data=x, index=0, spread_order=0)],
            errors=(np.random.random_sample(x.shape),
                    np.random.random_sample(x.shape)))
        prog.show_data(data)

    def test_nans(self, init_viewer1d):
        prog, data = init_viewer1d

        x = np.linspace(0, 200, 201)
        y = gauss1D(x, 75, 25)

        y[100:150] = np.nan
        data = data_mod.DataRaw('mydata', data=[y],
                                axes=[data_mod.Axis('myaxis', 'units', data=x)])
        prog.show_data(data)

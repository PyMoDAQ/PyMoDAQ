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


pytestmark = pytest.mark.skipif(qtbotskip, reason='qtbot issues but tested locally')


@pytest.fixture
def init_prog(qtbot):
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
    def test_init(self, init_prog):
        prog, data = init_prog
        assert prog.viewer_type == 'Data1D'
        assert prog.parent is not None

    def test_do_math(self, init_prog):
        prog, data = init_prog
        assert not prog.is_action_checked('do_math')
        prog.get_action('do_math').trigger()
        assert prog.is_action_checked('do_math')
        prog.get_action('do_math').trigger()
        assert not prog.is_action_checked('do_math')

    def test_scatter(self, init_prog):
        prog, data = init_prog
        prog.show_data(data)
        assert not prog.is_action_checked('scatter')
        prog.get_action('scatter').trigger()
        assert prog.is_action_checked('scatter')

    def test_xyplot_action(self, init_prog):
        prog, data = init_prog
        prog.show_data(data)
        assert prog.is_action_visible('scatter')
        assert prog.labels == data.labels

        assert not prog.is_action_checked('xyplot')
        prog.get_action('xyplot').trigger()
        assert prog.is_action_checked('xyplot')
        prog.get_action('xyplot').trigger()
        assert not prog.is_action_checked('xyplot')

    def test_crosshairClicked(self, init_prog):
        prog, data = init_prog
        prog.trigger_action('crosshair')
        assert prog.is_action_visible('x_label')
        assert prog.is_action_visible('y_label')



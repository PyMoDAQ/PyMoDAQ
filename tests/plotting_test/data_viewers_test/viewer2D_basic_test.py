from qtpy import QtWidgets
from pymodaq.utils.plotting.data_viewers.viewer2D_basic import Viewer2DBasic
from pymodaq.utils.plotting.utils.plot_utils import View_cust
from pymodaq.utils.plotting.widgets import ImageWidget

import pytest
import numpy as np
from pymodaq.utils.conftests import qtbotskip
pytestmark = pytest.mark.skipif(qtbotskip, reason='qtbot issues but tested locally')

@pytest.fixture
def init_viewer2d_basic(qtbot):
    form = QtWidgets.QWidget()
    prog = Viewer2DBasic(form)
    prog.setupUI()
    qtbot.addWidget(form)
    yield prog
    form.close()


@pytest.fixture
def init_image(qtbot):
    form = QtWidgets.QWidget()
    img = ImageWidget(form)
    img.setupUI()
    qtbot.addWidget(form)
    yield img
    form.close()


@pytest.fixture
def init_view(qtbot):
    form = QtWidgets.QWidget()
    view = View_cust()
    qtbot.addWidget(form)
    yield view
    form.close()


class TestViewer2DBasic:
    def test_init(self, init_viewer2d_basic):
        prog = init_viewer2d_basic

        assert isinstance(prog, Viewer2DBasic)

        prog = Viewer2DBasic()

        assert isinstance(prog.parent, QtWidgets.QWidget)

    def test_scale_axis(self, init_viewer2d_basic):
        prog = init_viewer2d_basic

        xaxis = np.linspace(1, 10, 10)
        yaxis = np.linspace(11, 20, 10)

        result = prog.scale_axis(xaxis=xaxis, yaxis=yaxis)

        assert np.array_equal(xaxis, result[0])
        assert np.array_equal(yaxis, result[1])


class TestImageWidget:
    def test_init(self, init_image):
        img = init_image

        assert isinstance(img, ImageWidget)


class TestView_cust:
    def test_init(self, init_view):
        view = init_view

        assert isinstance(view, View_cust)


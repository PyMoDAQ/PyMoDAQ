import pytest

from qtpy import QtWidgets
from pymodaq.daq_utils.plotting.viewerND.viewerND_main import ViewerND


@pytest.fixture
def init_prog(qtbot):
    form = QtWidgets.QWidget()
    prog = ViewerND()
    qtbot.addWidget(form)
    return prog


class TestViewer2D:
    def test_init(self, init_prog):
        prog = init_prog

        assert isinstance(prog, ViewerND)
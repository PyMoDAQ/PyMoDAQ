import pytest

from qtpy import QtWidgets
from pymodaq.daq_utils.plotting.data_viewers.viewerND import ViewerND


@pytest.fixture
def init_prog(qtbot):
    form = QtWidgets.QWidget()
    prog = ViewerND()
    qtbot.addWidget(form)
    yield prog
    form.close()


class TestViewer2D:
    def test_init(self, init_prog):
        prog = init_prog

        assert isinstance(prog, ViewerND)

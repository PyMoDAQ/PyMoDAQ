import pytest

from qtpy import QtWidgets
from pymodaq.utils.plotting.data_viewers.viewerND import ViewerND
from pymodaq.utils.conftests import qtbotskip
pytestmark = pytest.mark.skipif(qtbotskip, reason='qtbot issues but tested locally')


@pytest.fixture
def init_viewernd(qtbot):
    widget = QtWidgets.QWidget()
    prog = ViewerND(widget)
    qtbot.addWidget(widget)
    yield prog
    widget.close()



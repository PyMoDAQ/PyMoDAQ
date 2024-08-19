import numpy as np
import pytest

from qtpy import QtWidgets
from pymodaq.utils.plotting.data_viewers.viewerND import ViewerND
from pymodaq.utils.conftests import qtbotskip
from pymodaq.utils import data as data_mod
from scipy.spatial import Delaunay as Triangulation

# pytestmark = pytest.mark.skipif(qtbotskip, reason='qtbot issues but tested locally')
@pytest.fixture
def init_viewernd(qtbot):
    widget = QtWidgets.QWidget()
    prog = ViewerND(widget)
    qtbot.addWidget(widget)
    widget.show()
    yield prog
    widget.close()


class TestSpread:

    def test_linear_spread(self, init_viewernd):
        viewer = init_viewernd

        xaxis = data_mod.Axis(label='xaxis', data=np.array([0., 1, 2]), index=0, spread_order=0)
        yaxis = data_mod.Axis(label='yaxis', data=np.array([0., 1, 2]), index=0, spread_order=1)
        data = np.array([10, 12, 8])

        data_spread = data_mod.DataRaw(name='spread',
                                       distribution=data_mod.DataDistribution['spread'],
                                       data=[data],
                                       nav_indexes=(0,),
                                       axes=[xaxis, yaxis])


        viewer.show_data(data_spread)

        pass

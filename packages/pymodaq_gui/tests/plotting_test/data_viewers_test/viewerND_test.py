import numpy as np
import pytest

from qtpy import QtWidgets
from pymodaq_gui.plotting.data_viewers import ViewerND, ViewerError

from pymodaq_data import data as data_mod
from pymodaq_utils import math_utils as mutils


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

    def test_2D_spread_1D_signal(self, init_viewernd, qtbot):
        viewer = init_viewernd

        # Parameter
        param = np.linspace(1, 10, 10)

        # generating Npts of spread 2D data
        N = 200

        x_axis_array = np.random.randint(-20, 50, size=N)
        y_axis_array = np.random.randint(20, 40, size=N)

        x_axis = data_mod.Axis('xaxis', 'm', data=x_axis_array, index=0, spread_order=0)
        y_axis = data_mod.Axis('yaxis', 'm', data=y_axis_array, index=0, spread_order=1)
        param_axis = data_mod.Axis('Param', 'eV', data=param, index=1)

        data_spread_1x2 = []
        for i in param :
            data_list = []
            for ind in range(N):
                data_list.append(mutils.gauss2D(x_axis.get_data()[ind], 10+i, 15,
                                                y_axis.get_data()[ind], 30-i, 5))
            data_array = np.squeeze(np.array(data_list))
            data_spread_1x2.append(data_array)
        data_spread_1x2 = np.array(data_spread_1x2).T

        data_2D_1x2_spread = data_mod.DataRaw('data2DSpread', data=[data_spread_1x2],
                                     axes=[x_axis, y_axis, param_axis],
                                     distribution='spread',
                                     nav_indexes=(0,))

        # keep the viewer and close its window: a window left open around a deleted
        # viewer crashes when repainted (e.g. by a later theme change)
        plotted = data_2D_1x2_spread.plot('qt')
        qtbot.addWidget(plotted.parent)
        QtWidgets.QApplication.processEvents()
        pass


class TestNavIntegrationRoiSelect:
    """Moving a navigator ROIselect refreshes the signal integrated over the selected nav range"""

    @staticmethod
    def integrated_signal(viewer: ViewerND) -> float:
        # the signal viewer gets the data at the crosshair plus the nav integrated data
        return float(np.mean(viewer.viewer1D._raw_data[1]))

    def test_navigator1D(self, init_viewernd):
        viewer = init_viewernd
        data_array = np.repeat(np.arange(10.)[:, None], 5, axis=1)  # value = nav index
        dwa = data_mod.DataRaw('nav1D', data=[data_array], nav_indexes=(0,))
        dwa.create_missing_axes()
        viewer.show_data(dwa)
        viewer.get_action('integrate_nav').trigger()
        assert self.integrated_signal(viewer) == pytest.approx(4.5)  # whole nav range

        viewer.navigator1D.view.get_action('ROIselect').trigger()
        viewer.navigator1D.view.ROIselect.setRegion((2, 5))

        assert self.integrated_signal(viewer) == pytest.approx(3.)  # nav indexes 2 to 4

    def test_navigator2D(self, init_viewernd):
        viewer = init_viewernd
        ind_y, ind_x = np.meshgrid(np.arange(10.), np.arange(10.), indexing='ij')
        data_array = np.repeat((10 * ind_y + ind_x)[:, :, None], 5, axis=2)
        dwa = data_mod.DataRaw('nav2D', data=[data_array], nav_indexes=(0, 1))
        dwa.create_missing_axes()
        viewer.show_data(dwa)
        viewer.get_action('integrate_nav').trigger()
        assert self.integrated_signal(viewer) == pytest.approx(49.5)  # whole nav range

        viewer.navigator2D.view.get_action('ROIselect').trigger()
        viewer.navigator2D.view.ROIselect.setPos((2, 3))
        viewer.navigator2D.view.ROIselect.setSize((3, 4))

        # y nav indexes 3 to 6, x nav indexes 2 to 4
        assert self.integrated_signal(viewer) == pytest.approx(48.)


def test_data_5d(init_viewernd):
    viewer = init_viewernd

    data_array = np.random.rand(5, 11, 15, 6, 20)
    dwa = data_mod.DataRaw('random', data=[data_array])
    dwa.create_missing_axes()

    dwa.nav_indexes = (0, 1, 2, 3)
    viewer.show_data(dwa)

    dwa.nav_indexes = (0, 1, 2, 3, 4)
    viewer.show_data(dwa)

    dwa.nav_indexes = (0, 1)
    with pytest.raises(ViewerError):
        viewer.show_data(dwa)

    dwa.nav_indexes = (0,)
    with pytest.raises(ViewerError):
        viewer.show_data(dwa)


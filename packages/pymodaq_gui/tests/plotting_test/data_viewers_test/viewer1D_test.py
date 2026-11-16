from pymodaq_gui.parameter import Parameter
import pyqtgraph as pg
import numpy as np
import pytest

from qtpy import QtWidgets
from pyqtgraph import ROI
from unittest import mock
from collections import OrderedDict

from pymodaq_data import data as data_mod
from pymodaq_utils import math_utils as mutils

from pymodaq_gui.plotting.data_viewers.viewer1D import Viewer1D
from pymodaq_gui.managers.roi_viewer_manager import ROIFactory, ROIDim

from pymodaq_utils.math_utils import gauss1D


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

    def test_roi_channels_follow_labels(self, init_viewer1d):
        """The channels of an ROI must follow the labels of the data and never keep stale ones"""
        prog, data = init_viewer1d
        x = np.linspace(0, 200, 201)
        y1 = mutils.gauss1D(x, 75, 25)
        y2 = mutils.gauss1D(x, 120, 50, 2)
        axes = [data_mod.Axis('myaxis', 'units', data=x)]

        prog.show_data(data_mod.DataRaw('mydata', data=[y1, y2], labels=['Mock1', 'Mock2'], axes=axes))
        prog.get_action('roi').trigger()
        roi_manager = prog.view.roi_manager
        roi_manager.add_roi_programmatically(
            ROIFactory.get_descriptors_from_dimensionality(ROIDim.ROI1D)[0])

        prog.show_data(data_mod.DataRaw('mydata', data=[y1, y2], labels=['CH00', 'CH01'], axes=axes))

        use_channel = roi_manager.get_roi_from_index(0).param['use_channel']
        assert use_channel['all_items'] == ['CH00', 'CH01']
        assert use_channel['selected'] == ['CH00', 'CH01']

    def test_do_math_toggle_hides_and_shows_roi_graphics(self, init_viewer1d):
        """Toggling 'do_math' off must hide the ROI graphic items, not just the panel
        (regression test for https://github.com/PyMoDAQ/PyMoDAQ/issues/1435)"""
        prog, data = init_viewer1d
        prog.show_data(data)
        prog.get_action('do_math').trigger()
        roi_manager = prog.view.roi_manager
        roi_manager.add_roi_programmatically(
            ROIFactory.get_descriptors_from_dimensionality(ROIDim.ROI1D)[0])

        assert roi_manager.ROIs[0].roi.isVisible()

        prog.get_action('do_math').trigger()  # closing the roi panel also does this
        assert not roi_manager.ROIs[0].roi.isVisible()

        prog.get_action('do_math').trigger()
        assert roi_manager.ROIs[0].roi.isVisible()

    def test_show_data_emits_with_roi_present_but_do_math_off(self, init_viewer1d, qtbot):
        """Once a ROI exists, turning 'do_math' off (as closing the roi panel does) must fall
        back to a direct data_to_export_signal emission. Before the fix, show_data() kept
        routing through the (now inactive) roi filter whenever any ROI existed, so the signal
        silently stopped firing -- which is what makes a DAQ_Viewer's probe_detectors() time
        out (https://github.com/PyMoDAQ/PyMoDAQ/issues/1435)."""
        prog, data = init_viewer1d
        prog.show_data(data)
        prog.get_action('do_math').trigger()
        prog.view.roi_manager.add_roi_programmatically(
            ROIFactory.get_descriptors_from_dimensionality(ROIDim.ROI1D)[0])
        qtbot.wait(0)

        prog.get_action('do_math').trigger()  # closing the roi panel also does this
        assert not prog.is_action_checked('do_math')
        assert len(prog.view.roi_manager.ROIs) == 1  # the ROI itself is still there

        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000):
            prog.show_data(data)

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

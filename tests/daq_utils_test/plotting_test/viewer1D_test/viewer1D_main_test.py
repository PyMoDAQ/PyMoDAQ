from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np
import pytest
from unittest import mock


from pymodaq.daq_utils.plotting.viewer1D.viewer1D_main import Viewer1D
from pymodaq.daq_utils.exceptions import ExpectedError, Expected_1, Expected_2


class TestViewer1D:
    def test_init(self, qtbot):
        prog = Viewer1D(None)

        assert isinstance(prog, Viewer1D)
        assert prog.viewer_type == 'Data1D'
        assert prog.title == 'viewer1D'
        assert prog.parent is not None

        qtbot.addWidget(prog)

    def test_Do_math_pb(self, qtbot):
        prog = Viewer1D(None)

        qtbot.addWidget(prog)

        x = np.linspace(0, 200, 201)
        data1D = np.linspace(x, x + 190, 20)

        prog.data_to_export = {'data0D': x}
        prog.measurement_dict['datas'] = data1D

        assert not prog.ui.Do_math_pb.isChecked()
        prog.ui.Do_math_pb.trigger()
        assert prog.ui.Do_math_pb.isChecked()
        prog.ui.Do_math_pb.trigger()
        assert not prog.ui.Do_math_pb.isChecked()

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.Viewer1D.show_measurement')
    def test_do_measurements_pb(self, mock_show, qtbot):
        mock_show.return_value = None
        prog = Viewer1D(None)

        qtbot.addWidget(prog)

        x = np.linspace(0, 200, 201)
        data1D = np.linspace(x, x + 190, 20)

        prog.data_to_export = {'data0D': x}
        prog.measurement_dict['datas'] = data1D

        assert not prog.ui.do_measurements_pb.isChecked()
        assert not prog.ui.Do_math_pb.isChecked()
        prog.ui.do_measurements_pb.trigger()
        assert prog.ui.do_measurements_pb.isChecked()
        assert prog.ui.Do_math_pb.isChecked()
        prog.ui.do_measurements_pb.trigger()
        assert not prog.ui.do_measurements_pb.isChecked()
        assert prog.ui.Do_math_pb.isChecked()

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.logger.exception')
    def test_zoom_pb(self, mock_exception, qtbot):
        mock_exception.return_value = None
        prog = Viewer1D(None)

        x = np.linspace(0, 200, 201)
        data1D = np.linspace(x, x + 190, 20)
        colors = np.linspace(1, 20, 20)

        prog.datas = data1D
        prog.measurement_dict['datas'] = data1D
        prog.plot_colors = colors
        prog.x_axis = np.linspace(0, 200, 201)

        qtbot.addWidget(prog)

        assert not prog.ui.zoom_pb.isChecked()
        prog.ui.zoom_pb.trigger()
        assert prog.ui.zoom_pb.isChecked()
        prog.ui.zoom_pb.trigger()
        assert not prog.ui.zoom_pb.isChecked()

    def test_scatter(self, qtbot):
        prog = Viewer1D(None)

        qtbot.addWidget(prog)

        assert not prog.ui.scatter.isChecked()
        prog.ui.scatter.trigger()
        assert prog.ui.scatter.isChecked()

    def test_xyplot_action(self, qtbot):
        prog = Viewer1D(None)
        prog.labels = ['label_1', 'label_2']
        prog.legend = prog.viewer.plotwidget.plotItem.legend

        qtbot.addWidget(prog)

        assert prog.legend.isVisible()
        assert not prog.ui.xyplot_action.isChecked()
        prog.ui.xyplot_action.trigger()
        assert not prog.legend.isVisible()
        assert prog.ui.xyplot_action.isChecked()
        prog.ui.xyplot_action.trigger()
        assert prog.legend.isVisible()
        assert not prog.ui.xyplot_action.isChecked()

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.logger.exception')
    def test_do_scatter(self, mock_logger, qtbot):
        mock_logger.side_effect = [ExpectedError]
        prog = Viewer1D(None)

        with pytest.raises(ExpectedError):
            prog.do_scatter()

        qtbot.addWidget(prog)

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.Viewer1D.update_graph1D')
    def test_do_xy(self, mock_graph, qtbot):
        mock_graph.side_effect = [Expected_1, Expected_2]
        prog = Viewer1D(None)
        prog.labels = ['label_1', 'label_2']
        prog.legend = prog.viewer.plotwidget.plotItem.legend

        prog.ui.xyplot_action.setChecked(True)
        with pytest.raises(Expected_1):
            prog.do_xy()

        assert prog.viewer.plotwidget.plotItem.getAxis('bottom').labelText == prog.labels[0]
        assert prog.viewer.plotwidget.plotItem.getAxis('left').labelText == prog.labels[1]

        prog.ui.xyplot_action.setChecked(False)
        with pytest.raises(Expected_2):
            prog.do_xy()

        assert prog.viewer.plotwidget.plotItem.getAxis('bottom').labelText == prog.axis_settings['label']
        assert prog.viewer.plotwidget.plotItem.getAxis('left').labelText == ''

        qtbot.addWidget(prog)

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.Viewer1D.show_math')
    def test_update_lineouts(self, mock_math, qtbot):
        mock_math.side_effect = [ExpectedError]
        prog = Viewer1D(None)

        opts = mock.Mock()
        opts.index.return_value = 'index'

        child = mock.Mock()
        child.value.return_value = 'child_value'
        child.opts = {'limits': opts}

        settings = mock.Mock()
        settings.child.return_value = child

        prog.roi_manager.settings = settings

        mock_obj = mock.Mock()
        mock_obj.getRegion.side_effect = [1, 2, 3]
        mock_obj.setPen.return_value = None

        ROI = {'ind1': mock_obj, 'ind2': mock_obj, 'ind3': mock_obj}

        prog.roi_manager.ROIs = ROI

        prog.lo_items = ROI

        prog.update_lineouts()

        meas_dict = prog.measurement_dict

        assert meas_dict['datas'] == prog.datas
        assert meas_dict['ROI_bounds'] == [1, 2, 3]
        assert meas_dict['channels'] == ['index', 'index', 'index']
        assert meas_dict['operations'] ==  ['child_value', 'child_value', 'child_value']

        qtbot.addWidget(prog)

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.Viewer1D.update_lineouts')
    def test_remove_ROI(self, mock_update, qtbot):
        mock_update.side_effect = [Expected_1]
        prog = Viewer1D(None)

        prog.lo_items = {'item1': 1, 'item2': 2, 'item3': 3}
        prog.measure_data_dict = {'Lineout_item1:': 1, 'Lineout_item2:': 2, 'Lineout_item3:': 3}

        GraphLineouts = mock.Mock()
        GraphLineouts.plotItem.removeItem.side_effect = [None, Expected_2]

        prog.ui.Graph_Lineouts = GraphLineouts

        with pytest.raises(Expected_1):
            prog.remove_ROI('item1')

        assert not 'item1' in prog.lo_items
        assert 'item2' in prog.lo_items
        assert not 'Lineout_item1:' in prog.measure_data_dict
        assert 'Lineout_item3:' in prog.measure_data_dict

        with pytest.raises(Expected_2):
            prog.remove_ROI('item2')

        assert not 'item2' in prog.lo_items
        assert 'item3' in prog.lo_items
        assert 'Lineout_item2:' in prog.measure_data_dict

        qtbot.addWidget(prog)

    def test_add_lineout(self, qtbot):
        pass

    def test_clear_lo(self, qtbot):
        prog = Viewer1D(None)

        prog.lo_data = [1, 2, 3]

        prog.clear_lo()

        assert prog.lo_data == [[], [], []]

        qtbot.addWidget(prog)

    def test_crosshairClicked(self, qtbot):
        prog = Viewer1D(None)

        prog.ui.crosshair_pb.setChecked(True)
        prog.ui.x_label.setVisible(False)
        prog.ui.y_label.setVisible(False)

        prog.crosshairClicked()

        assert prog.ui.x_label.isVisible()
        assert prog.ui.y_label.isVisible()

        prog.ui.crosshair_pb.setChecked(False)

        prog.crosshairClicked()

        assert not prog.ui.x_label.isVisible()
        assert not prog.ui.y_label.isVisible()

        qtbot.addWidget(prog)

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.logger.exception')
    def test_do_math_fun(self, mock_logger, qtbot):
        mock_logger.side_effect = [ExpectedError]
        prog = Viewer1D(None)

        prog.ui.Do_math_pb.setChecked(True)
        prog.do_math_fun()

        prog.ui.Do_math_pb.setChecked(False)
        prog.do_math_fun()

        roi_manager = mock.Mock()
        roi_manager.roiwidget.hide.side_effect = [Exception]

        prog.roi_manager = roi_manager

        with pytest.raises(ExpectedError):
            prog.do_math_fun()

        qtbot.addWidget(prog)

    def test_do_zoom(self, qtbot):
        prog = Viewer1D(None)

        prog.do_zoom()

        viewer = mock.Mock()
        viewer.plotwidget.setXRange.side_effect = [ExpectedError]
        prog.viewer = viewer

        with pytest.raises(ExpectedError):
            prog.do_zoom()

        qtbot.addWidget(prog)

    def test_enable_zoom(self, qtbot):
        pass

    def test_ini_data_plots(self, qtbot):
        pass

    def test_update_labels(self, qtbot):
        pass

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.Viewer1D.update_labels')
    def test_labels(self, mock_update, qtbot):
        mock_update.side_effect = [None, ExpectedError]
        prog = Viewer1D(None)

        prog.labels = 'labels'
        assert prog.labels == 'labels'

        with pytest.raises(ExpectedError):
            prog.labels = 'error'

        qtbot.addWidget(prog)

    def test_lock_aspect_ratio(self, qtbot):
        prog = Viewer1D(None)

        prog.ui.aspect_ratio_pb.setChecked(False)
        prog.lock_aspect_ratio()
        assert not prog.viewer.plotwidget.plotItem.vb.state['aspectLocked']

        prog.ui.aspect_ratio_pb.setChecked(True)
        prog.lock_aspect_ratio()
        assert prog.viewer.plotwidget.plotItem.vb.state['aspectLocked']

        qtbot.addWidget(prog)

    def test_open_measurement_module(self, qtbot):
        pass

    def test_remove_plots(self, qtbot):
        prog = Viewer1D(None)

        item1 = pg.PlotItem()
        item_legend = pg.PlotItem()
        channels = [item1]
        prog.plot_channels = channels
        prog.legend = item_legend
        prog.viewer.plotwidget.plotItem.items = []
        assert prog.plot_channels

        for channel in channels:
            prog.viewer.plotwidget.addItem(channel)
        prog.viewer.plotwidget.addItem(prog.legend)

        assert len(prog.viewer.plotwidget.plotItem.items) == 2

        prog.remove_plots()

        assert not prog.plot_channels
        assert len(prog.viewer.plotwidget.plotItem.items) == 0

        qtbot.addWidget(prog)

    def test_set_axis_labels(self, qtbot):
        pass

    def test_show_data(self, qtbot):
        pass

    def test_show_data_temp(self, qtbot):
        pass

    def test_show_math(self, qtbot):
        pass

    def test_show_measurement(self, qtbot):
        pass

    def test_update_crosshair_data(self, qtbot):
        pass

    def test_update_graph1D(self, qtbot):
        pass

    def test_update_measurement_module(self, qtbot):
        pass

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.logger.info')
    def test_update_status(self, mock_info, qtbot):
        mock_info.side_effect = [ExpectedError]
        prog = Viewer1D(None)

        with pytest.raises(ExpectedError):
            prog.update_status('')

        qtbot.addWidget(prog)

    def test_x_axis(self, qtbot):
        pass

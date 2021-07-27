from pyqtgraph.parametertree import Parameter
import pyqtgraph as pg
import numpy as np
import pytest
import sys

from PyQt5 import QtWidgets
from unittest import mock
from collections import OrderedDict
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_measurement.daq_measurement_main import DAQ_Measurement
from pymodaq.daq_utils.plotting.viewer1D.viewer1D_main import Viewer1D, Viewer1D_math
from pymodaq.daq_utils.managers.roi_manager import LinearROI
from pymodaq.daq_utils.gui_utils import QAction
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

    # @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.Viewer1D.show_math')
    # def test_update_lineouts(self, mock_math, qtbot):
    #     mock_math.side_effect = [None]
    #     prog = Viewer1D(None)
    #     datas = [4, 5, 6]
    #     prog.datas = datas
    #
    #     opts = mock.Mock()
    #     opts.index.return_value = 'index'
    #
    #     child = mock.Mock()
    #     child.value.return_value = [1, 2, 3]
    #     child.opts = {'limits': opts}
    #
    #     settings = mock.Mock()
    #     settings.child.return_value = child
    #
    #     prog.roi_manager.settings = settings
    #
    #     mock_obj = mock.Mock()
    #     mock_obj.getRegion.side_effect = [1, 2, 3]
    #     mock_obj.setPen.return_value = None
    #
    #     ind1 = mock_obj
    #     ind2 = mock_obj
    #     ind3 = mock_obj
    #
    #     params = [{'name': 'type', 'type': None, 'value': '1D'},
    #               {'name': 'Color', 'value': 2}]
    #
    #     ind1 = Parameter.create(name='ROI_01', type='group', children=params)
    #     # ind2 = pg.PlotItem(name='ind2')
    #     # ind3 = pg.PlotItem(name='ind3')
    #
    #     parameter_list = {'ind1': ind1, 'ind2': ind2, 'ind3': ind3}
    #
    #     ROI_01 = LinearROI()
    #     ROI_02 = LinearROI(pos=[0, 2])
    #     ROI_03 = LinearROI(pos=[5, 7])
    #
    #     ROI = {'ROI_01': ROI_01, 'ROI_02': ROI_02, 'ROI_03': ROI_03}
    #
    #     # prog.roi_manager.setupUI()
    #
    #     prog.roi_manager.ROIs = ROI
    #
    #     assert prog.roi_manager.ROIs['ROI_01'].getRegion() == (0, 10)
    #     assert prog.roi_manager.ROIs['ROI_02'].getRegion() == (0, 2)
    #     assert prog.roi_manager.ROIs['ROI_03'].getRegion() == (5, 7)
    #
    #     prog.lo_items = ROI
    #
    #     # for ind, key in enumerate(parameter_list):
    #     #     prog.roi_manager.settings.addChild(parameter_list[key])
    #     #     assert prog.roi_manager.settings.child('ROIs', key, 'math_function')
    #
    #     prog.update_lineouts()
    #
    #     meas_dict = prog.measurement_dict
    #
    #     assert meas_dict['datas'] == datas  # DONE
    #     assert meas_dict['ROI_bounds'] == [(0, 10), (0, 2), (5, 7)]  # DONE
    #     assert meas_dict['channels'] == ['index', 'index', 'index']
    #     assert meas_dict['operations'] == [[1, 2, 3], [1, 2, 3], [1, 2, 3]]
    #
    #     qtbot.addWidget(prog)

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

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.logger.exception')
    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.Viewer1D.update_graph1D')
    def test_enable_zoom(self, mock_graph, mock_except, qtbot):
        mock_graph.return_value = None
        mock_except.side_effect = [ExpectedError]

        prog = Viewer1D(None)

        datas = np.linspace(np.linspace(1, 10, 10), np.linspace(91, 100, 10), 10)
        prog.datas = datas
        prog._x_axis = datas

        prog.plot_colors = np.linspace(1, 10, 10)

        prog.setupUI()

        prog.ui.zoom_pb.setChecked(True)
        assert prog.ui.zoom_pb.isChecked()

        prog.enable_zoom()

        assert prog.ui.zoom_region.getRegion() == (np.min(prog._x_axis), np.max(prog._x_axis))
        assert not prog.ui.zoom_widget.isHidden()

        prog.ui.zoom_pb.setChecked(False)
        assert not prog.ui.zoom_pb.isChecked()

        prog.enable_zoom()

        assert prog.ui.zoom_widget.isHidden()

        with pytest.raises(ExpectedError):
            prog.enable_zoom()

        qtbot.addWidget(prog)

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.logger.exception')
    def test_ini_data_plots(self, mock_except, qtbot):
        mock_except.side_effect = [ExpectedError]

        prog = Viewer1D()

        prog._labels = ['x_axis', 'y_axis', 'z_axis']

        prog.ini_data_plots(3)

        assert len(prog.legend.items) == 3
        assert len(prog.plot_channels) == 3

        prog.ini_data_plots(2)

        assert len(prog.legend.items) == 2
        assert len(prog.plot_channels) == 2

        with pytest.raises(ExpectedError):
            prog.ini_data_plots(4)

        qtbot.addWidget(prog)

    def test_update_labels(self, qtbot):
        prog = Viewer1D()

        prog.datas = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)

        prog.update_labels()
        assert prog._labels == ['CH0', 'CH1']

        prog.ini_data_plots(2)

        prog.update_labels(['x_axis', 'y_axis'])
        assert prog._labels == ['x_axis', 'y_axis']
        assert len(prog.legend.items) == 2

        prog.datas = [np.linspace(1, 10, 10)]

        prog.update_labels()

        qtbot.addWidget(prog)
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

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.DAQ_Measurement.Quit_fun')
    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.Viewer1D.update_measurement_module')
    def test_open_measurement_module(self, mock_meas, mock_quit, qtbot):
        mock_meas.side_effect = [Expected_1]
        mock_quit.side_effect = [Expected_2]

        prog = Viewer1D()

        prog.measurement_module = None

        prog.ui.Do_math_pb.setChecked(False)
        assert not prog.ui.Do_math_pb.isChecked()

        prog.ui.do_measurements_pb.setChecked(True)
        assert prog.ui.do_measurements_pb.isChecked()

        with pytest.raises(Expected_1):
            prog.open_measurement_module()

        assert prog.ui.Do_math_pb.isChecked()
        assert prog.ui.Measurement_widget.isVisible()
        assert prog.measurement_module

        prog.ui.do_measurements_pb.setChecked(False)
        assert not prog.ui.do_measurements_pb.isChecked()

        with pytest.raises(Expected_2):
            prog.open_measurement_module()

        qtbot.addWidget(prog)

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
        prog = Viewer1D()

        prog.set_axis_label()

        axis_settings = dict(orientation='bottom', label='x axis', units='pxls')

        axis = prog.viewer.plotwidget.plotItem.getAxis(axis_settings['orientation'])
        assert axis.labelText == axis_settings['label']
        assert axis.labelUnits == axis_settings['units']

        axis_settings = dict(orientation='bottom', label='label', units='nm')

        prog.set_axis_label(axis_settings=axis_settings)

        axis = prog.viewer.plotwidget.plotItem.getAxis(axis_settings['orientation'])
        assert axis.labelText == axis_settings['label']
        assert axis.labelUnits == axis_settings['units']

        qtbot.addWidget(prog)

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.logger.exception')
    def test_show_data(self, mock_except, qtbot):
        mock_except.side_effect = [ExpectedError]

        prog = Viewer1D()

        datas = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)
        labels = ['CH0', 'CH1']
        x_axis = datas[1]

        prog.show_data(datas, labels, x_axis)

        assert np.array_equal(prog.datas, datas)

        export = prog.data_to_export
        assert export['name'] == prog.title
        assert isinstance(export['data0D'], OrderedDict)
        assert not export['data2D']

        for ind, data in enumerate(datas):
            assert isinstance(export['data1D']['CH{:03d}'.format(ind)],
                              utils.DataToExport)

        assert np.array_equal(prog.x_axis, x_axis)
        assert prog.labels == labels

        prog.ui.do_measurements_pb.setChecked(True)

        datas = [np.linspace(1, 10, 10)]
        labels = ['CH0']
        x_axis = datas[0]

        with pytest.raises(ExpectedError):
            prog.show_data(datas, labels, x_axis)

        assert np.array_equal(prog.datas, datas)

        export = prog.data_to_export
        assert export['name'] == prog.title
        assert isinstance(export['data0D'], OrderedDict)
        assert not export['data2D']

        for ind, data in enumerate(datas):
            assert isinstance(export['data1D']['CH{:03d}'.format(ind)],
                              utils.DataToExport)

        assert np.array_equal(prog.x_axis, x_axis)
        assert prog.labels == labels

        qtbot.addWidget(prog)

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.logger.exception')
    def test_show_data_temp(self, mock_except, qtbot):
        mock_except.side_effect = [ExpectedError]

        prog = Viewer1D()
        prog.labels = ['CH0', 'CH1']
        prog.x_axis = None

        datas = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)
        x_axis = np.linspace(0, 9, 10)

        prog.show_data_temp(datas)

        assert np.array_equal(prog.datas, datas)
        for ind, data in enumerate(datas):
            assert np.array_equal(prog.plot_channels[ind].getData(), (x_axis, data))

        datas = [np.linspace(1, 5, 5)]
        x_axis = np.linspace(0, 4, 5)

        prog.show_data_temp(datas)

        assert np.array_equal(prog.datas, datas)
        for ind, data in enumerate(datas):
            assert np.array_equal(prog.plot_channels[ind].getData(), (x_axis, data))

        with pytest.raises(ExpectedError):
            prog.show_data_temp(None)

        qtbot.addWidget(prog)

    def test_show_math(self, qtbot):
        prog = Viewer1D()

        item = mock.Mock()
        item.setData.return_value = None

        data_to_export_signal = mock.Mock()
        data_to_export_signal.emit.side_effect = [ExpectedError]

        prog.data_to_export_signal = data_to_export_signal

        prog.data_to_export = {'data0D': {}}

        prog.measure_data_dict = {}

        prog.lo_items = {'key_0': item, 'key_1': item, 'key_2': item,
                    'key_3': item, 'key_4': item, 'key_5': item}

        prog.lo_data = {'key_0': 1, 'key_1': 2, 'key_2': 3,
                    'key_3': 4, 'key_4': 5, 'key_5': 6}

        data_lo = [10, 20, 30, 40, 50, 60]
        result = [[1, 10], [2, 20], [3, 30], [4, 40], [5, 50], [6, 60]]

        prog.ui.do_measurements_pb.setChecked(False)

        with pytest.raises(ExpectedError):
            prog.show_math(data_lo)

        for ind, key in enumerate(prog.lo_data):
            assert np.array_equal(prog.lo_data[key], result[ind])

        assert prog.data_to_export['acq_time_s']

        qtbot.addWidget(prog)

    def test_show_measurement(self, qtbot):
        prog = Viewer1D()

        prog.measure_data_dict = {'Meas.0:': 0, 'Meas.1:': 0, 'Meas.2:': 0,
                                  'Meas.3:': 0, 'Meas.4:': 0, 'Meas.5:': 0}

        export = {'Measure_000': 0, 'Measure_001': 0, 'Measure_002': 0,
                  'Measure_003': 0, 'Measure_004': 0, 'Measure_005': 0}

        prog.data_to_export = OrderedDict(data0D=export, acq_time_s=None)

        data_meas = [1, 2, 3, 4, 5, 6]

        prog.show_measurement(data_meas)

        assert prog.roi_manager.settings.child('measurements').value() == prog.measure_data_dict
        assert prog.data_to_export['acq_time_s']

        for ind in range(len(data_meas)):
            assert prog.measure_data_dict['Meas.{}:'.format(ind)] == data_meas[ind]

        qtbot.addWidget(prog)

    def test_update_crosshair_data(self, qtbot):
        prog = Viewer1D()

        prog.datas = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)
        prog._x_axis = np.linspace(1, 10, 10)

        posx = 7
        posy = 0
        indx = 6

        x_text = 'x={:.6e} '.format(posx)
        y_text = 'y='

        for data in prog.datas:
            y_text += '{:.6e} / '.format(data[indx])

        prog.update_crosshair_data(posx, posy)
        assert prog.ui.x_label.text() == x_text
        assert prog.ui.y_label.text() == y_text

        qtbot.addWidget(prog)

    def test_update_graph1D(self, qtbot):
        pass

    def test_update_measurement_module(self, qtbot):
        prog = Viewer1D()

        Form = prog.ui.Measurement_widget
        prog.measurement_module = DAQ_Measurement(Form)

        datas = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)

        x_data = datas[1]

        prog.measurement_dict = {'x_axis': x_data, 'datas': datas}

        prog.update_measurement_module()

        assert np.array_equal(prog.measurement_module.xdata, x_data)
        assert np.array_equal(prog.measurement_module.ydata, datas[0])

        qtbot.addWidget(prog)

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.logger.info')
    def test_update_status(self, mock_info, qtbot):
        mock_info.side_effect = [ExpectedError]
        prog = Viewer1D(None)

        with pytest.raises(ExpectedError):
            prog.update_status('')

        qtbot.addWidget(prog)

    def test_x_axis(self, qtbot):
        prog = Viewer1D()

        data = np.linspace(1, 10, 10)
        x_axis = {'data': data, 'label': 'CH0', 'units': 'nm'}

        prog.x_axis = x_axis

        assert np.array_equal(prog._x_axis, data)
        assert np.array_equal(prog.measurement_dict['x_axis'], data)
        assert prog.axis_settings['label'] == 'CH0'
        assert prog.axis_settings['units'] == 'nm'

        prog.x_axis = data

        assert np.array_equal(prog._x_axis, data)
        assert np.array_equal(prog.measurement_dict['x_axis'], data)
        assert prog.axis_settings['label'] == 'Pxls'
        assert prog.axis_settings['units'] == ''

        qtbot.addWidget(prog)


class TestViewer1D_math:
    def test_init(self, qtbot):
        prog_quit = Viewer1D(None)

        prog = Viewer1D_math()

        assert prog.datas == prog.ROI_bounds == prog.operations == prog.channels == []
        assert not prog.x_axis

        qtbot.addWidget(prog_quit)

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.logger.exception')
    def test_update_math(self, mock_except, qtbot):
        mock_except.side_effect = [None, ExpectedError]

        prog_quit = Viewer1D(None)

        prog = Viewer1D_math()

        datas = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)
        ROI_bounds = [[12, 17], [12, 17], [12, 17], [12, 17]]
        x_axis = datas[1]
        operations = ['Mean', 'Sum', 'half-life', 'expotime']
        channels = [0, 1, 0, 0]

        measurement_dict = dict(datas=datas, ROI_bounds=ROI_bounds, x_axis=x_axis,
                                operations=operations, channels=channels)

        result = prog.update_math(measurement_dict=measurement_dict)

        sub_data = []
        indexes = utils.find_index(x_axis, ROI_bounds[0])
        ind1, ind2 = indexes[0][0], indexes[1][0]

        for ind in range(len(operations)):
            sub_data.append(datas[channels[ind]][ind1:ind2])

        assert result[0] == float(np.mean(sub_data[0]))
        assert result[1] == float(np.sum(sub_data[1]))
        assert result[2] == result[3] == 0

        assert not prog.update_math(None)

        with pytest.raises(ExpectedError):
            prog.update_math(None)

        qtbot.addWidget(prog_quit)

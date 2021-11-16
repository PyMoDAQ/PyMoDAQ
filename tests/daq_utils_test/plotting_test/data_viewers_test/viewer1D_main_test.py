from pyqtgraph.parametertree import Parameter
import pyqtgraph as pg
import numpy as np
import pytest

from qtpy import QtWidgets
from pyqtgraph import ROI
from unittest import mock
from collections import OrderedDict
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_measurement.daq_measurement_main import DAQ_Measurement
from pymodaq.daq_utils.plotting.data_viewers.viewer1D import Viewer1D, Viewer1D_math
from pymodaq.daq_utils.exceptions import ExpectedError, Expected_1, Expected_2
from pymodaq.daq_utils.conftests import qtbotskip
pytestmark = pytest.mark.skipif(qtbotskip, reason='qtbot issues but tested locally')

@pytest.fixture
def init_prog(qtbot):
    form = QtWidgets.QWidget()
    prog = Viewer1D(form)
    qtbot.addWidget(prog)
    yield prog
    form.close()



@pytest.fixture
def init_prog_math(qtbot):
    form = QtWidgets.QWidget()
    prog = Viewer1D_math()
    qtbot.addWidget(form)
    yield prog
    form.close()


class TestViewer1D:
    def test_init(self, init_prog):
        prog = init_prog
        prog = Viewer1D(None)

        assert isinstance(prog, Viewer1D)
        assert prog.viewer_type == 'Data1D'
        assert prog.title == 'viewer1D'
        assert prog.parent is not None

    def test_Do_math_pb(self, init_prog):
        prog = init_prog

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
    def test_do_measurements_pb(self, mock_show, init_prog):
        mock_show.return_value = None
        prog = init_prog

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

    def test_zoom_pb(self, init_prog):
        prog = init_prog

        x = np.linspace(0, 200, 201)
        data1D = np.linspace(x, x + 190, 20)
        colors = np.linspace(1, 20, 20)

        prog.datas = [data1D]
        prog.measurement_dict['datas'] = [data1D]
        prog.plot_colors = colors
        prog.x_axis = np.linspace(0, 200, 201)

        assert not prog.ui.zoom_pb.isChecked()
        prog.ui.zoom_pb.trigger()
        assert prog.ui.zoom_pb.isChecked()
        prog.ui.zoom_pb.trigger()
        assert not prog.ui.zoom_pb.isChecked()

    def test_scatter(self, init_prog):
        prog = init_prog

        assert not prog.ui.scatter.isChecked()
        prog.ui.scatter.trigger()
        assert prog.ui.scatter.isChecked()

    def test_xyplot_action(self, init_prog):
        prog = init_prog
        prog.labels = ['label_1', 'label_2']
        prog.legend = prog.viewer.plotwidget.plotItem.legend

        assert prog.legend.isVisible()
        assert not prog.ui.xyplot_action.isChecked()
        prog.ui.xyplot_action.trigger()
        assert not prog.legend.isVisible()
        assert prog.ui.xyplot_action.isChecked()
        prog.ui.xyplot_action.trigger()
        assert prog.legend.isVisible()
        assert not prog.ui.xyplot_action.isChecked()

    def test_do_scatter(self, init_prog):
        prog = init_prog
        prog.do_scatter()

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.Viewer1D.update_graph1D')
    def test_do_xy(self, mock_graph, init_prog):
        mock_graph.side_effect = [Expected_1, Expected_2]
        prog = init_prog
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


    @pytest.mark.skip
    def test_update_lineouts(self, init_prog):
        prog = init_prog

        ROI_m = mock.Mock()
        ROI_m.getRegion.return_value = 1

        prog.data_to_export = OrderedDict()

        prog.datas = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)

        ROI_dict = {'ROI_00': ROI_m((0, 0)), 'ROI_01': ROI_m((1, 1)),
                    'ROI_02': ROI_m((2, 2)), 'ROI_03': ROI_m((3, 3))}

        prog.roi_manager.ROIs = ROI_dict

        item_param_0 = Parameter(name='ROI_00')
        item_param_1 = Parameter(name='ROI_01')
        item_param_2 = Parameter(name='ROI_02')
        item_param_3 = Parameter(name='ROI_03')

        item_params = [item_param_0, item_param_1, item_param_2, item_param_3]

        for ind, item_param in enumerate(item_params):
            math_param = Parameter(name='math_function')
            math_param.setValue('Mean')
            channel_param = Parameter(name='use_channel')
            channel_param.setValue(1)
            L = [0, 1, 2, 3]
            channel_param.opts['limits'] = L
            color_param = Parameter(name='Color')
            color_param.setValue(1)

            children = [math_param, channel_param, color_param]
            item_param.addChildren(children)

        rois_param = Parameter(name='ROIs', children=item_params)

        prog.roi_manager.settings = Parameter(name='settings', children=[rois_param])

        prog.lo_items = prog.roi_manager.ROIs

        prog.update_lineouts()

        assert np.array_equal(prog.measurement_dict['datas'], prog.datas)
        assert prog.measurement_dict['channels'] == [1, 1, 1, 1]
        assert prog.measurement_dict['operations'] == ['Mean', 'Mean', 'Mean', 'Mean']

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.Viewer1D.update_lineouts')
    def test_remove_ROI(self, mock_update, init_prog):
        mock_update.side_effect = [Expected_1]
        prog = init_prog

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

    @pytest.mark.skip
    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.logger.exception')
    def test_add_lineout(self, mock_except, init_prog):
        mock_except.side_effect = [None, ExpectedError]

        prog = init_prog

        ROI_dict = {'ROI_00': ROI((0, 0)), 'ROI_01': ROI((1, 1)),
                    'ROI_02': ROI((2, 2)), 'ROI_03': ROI((3, 3))}

        prog.roi_manager.ROIs = ROI_dict

        item_param_0 = Parameter(name='ROI_00')
        item_param_1 = Parameter(name='ROI_01')
        item_param_2 = Parameter(name='ROI_02')
        item_param_3 = Parameter(name='ROI_03')

        item_params = [item_param_0, item_param_1, item_param_2, item_param_3]

        for item_param in item_params:
            channel_param = Parameter(name='use_channel', type=[])
            color_param = Parameter(name='Color', type=[])

            children = [channel_param, color_param]
            item_param.addChildren(children)

        rois_param = Parameter(name='ROIs', children=item_params)

        prog.roi_manager.settings = Parameter(name='settings', children=[rois_param])

        prog.labels = ['label_0', 'label_1', 'label_2', 'label_3']

        prog.add_lineout(1)

        item = prog.roi_manager.ROIs['ROI_01']
        item_param = prog.roi_manager.settings.child('ROIs', 'ROI_01')

        assert item_param.child('use_channel').value() == prog.labels[0]
        for ind in prog.lo_items:
            assert np.array_equal(prog.lo_data[ind], np.zeros((1,)))

        item_param_4 = Parameter(name='ROI_04')

        channel_param = Parameter(name='use_channel')
        color_param = Parameter(name='Color')

        children = [channel_param, color_param]
        item_param_4.addChildren(children)

        prog.roi_manager.settings.child('ROIs').addChild(item_param_4)

        prog._labels = []

        with pytest.raises(ExpectedError):
            prog.add_lineout(4)

    def test_clear_lo(self, init_prog):
        prog = init_prog

        prog.lo_data = [1, 2, 3]

        prog.clear_lo()

        assert prog.lo_data == [[], [], []]

    def test_crosshairClicked(self, init_prog):
        prog = init_prog

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

    def test_do_math_fun(self,  init_prog):
        prog = init_prog

        prog.ui.Do_math_pb.setChecked(True)
        prog.do_math_fun()

        prog.ui.Do_math_pb.setChecked(False)
        prog.do_math_fun()
        roi_manager = mock.Mock()
        roi_manager.roiwidget.hide.side_effect = [Exception]
        prog.roi_manager = roi_manager
        prog.do_math_fun()

    def test_do_zoom(self, init_prog):
        prog = init_prog

        prog.do_zoom()

        viewer = mock.Mock()
        viewer.plotwidget.setXRange.side_effect = [ExpectedError]
        prog.viewer = viewer

        with pytest.raises(ExpectedError):
            prog.do_zoom()

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.Viewer1D.update_graph1D')
    def test_enable_zoom(self, mock_graph, init_prog):
        mock_graph.return_value = None

        prog = init_prog

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
        prog.enable_zoom()

    def test_ini_data_plots(self,  init_prog):
        prog = init_prog
        prog._labels = ['x_axis', 'y_axis', 'z_axis']
        prog.ini_data_plots(3)

        assert len(prog.legend.items) == 3
        assert len(prog.plot_channels) == 3

        prog.ini_data_plots(2)

        assert len(prog.legend.items) == 2
        assert len(prog.plot_channels) == 2
        prog.ini_data_plots(4)

    def test_update_labels(self, init_prog):
        prog = init_prog

        prog.datas = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)

        prog.update_labels()
        assert prog._labels == ['CH00', 'CH01']

        prog.ini_data_plots(2)

        prog.update_labels(['x_axis', 'y_axis'])
        assert prog._labels == ['x_axis', 'y_axis']
        assert len(prog.legend.items) == 2

        prog.datas = [np.linspace(1, 10, 10)]

        prog.update_labels()

    @mock.patch('pymodaq.daq_utils.plotting.viewer1D.viewer1D_main.Viewer1D.update_labels')
    def test_labels(self, mock_update, init_prog):
        mock_update.side_effect = [None, ExpectedError]

        prog = init_prog

        prog.labels = 'labels'
        assert prog.labels == 'labels'

        with pytest.raises(ExpectedError):
            prog.labels = 'error'

    def test_lock_aspect_ratio(self, init_prog):
        prog = init_prog

        prog.ui.aspect_ratio_pb.setChecked(False)
        prog.lock_aspect_ratio()
        assert not prog.viewer.plotwidget.plotItem.vb.state['aspectLocked']

        prog.ui.aspect_ratio_pb.setChecked(True)
        prog.lock_aspect_ratio()
        assert prog.viewer.plotwidget.plotItem.vb.state['aspectLocked']

    def test_open_measurement_module(self, init_prog):
        prog = init_prog

        prog.measurement_module = None

        prog.ui.Do_math_pb.setChecked(False)
        assert not prog.ui.Do_math_pb.isChecked()

        prog.ui.do_measurements_pb.setChecked(True)
        assert prog.ui.do_measurements_pb.isChecked()

        with pytest.raises(IndexError):
            prog.open_measurement_module()

        assert prog.ui.Do_math_pb.isChecked()
        assert prog.ui.Measurement_widget.isVisible()
        assert prog.measurement_module

        prog.ui.do_measurements_pb.setChecked(False)
        assert not prog.ui.do_measurements_pb.isChecked()

        prog.open_measurement_module()

    def test_remove_plots(self, init_prog):
        prog = init_prog

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

    def test_set_axis_labels(self, init_prog):
        prog = init_prog

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

    def test_show_data(self, init_prog):
        prog = init_prog

        datas = [np.linspace(1, 10, 10), np.linspace(11, 20, 10)]
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

    def test_show_data_temp(self, init_prog):
        prog = init_prog
        prog.labels = ['CH0', 'CH1']
        prog.x_axis = None

        datas = [np.linspace(1, 10, 10), np.linspace(11, 20, 10)]
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

        prog.show_data_temp(None)

    def test_show_math(self, init_prog):
        prog = init_prog

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

    def test_show_measurement(self, init_prog):
        prog = init_prog

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

    def test_update_crosshair_data(self, init_prog):
        prog = init_prog

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

    def test_update_graph1D(self, init_prog):
        prog = init_prog

        datas = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)

        prog.datas = datas
        prog.update_labels(prog.labels)
        prog.data_to_export = OrderedDict(name=prog.title, data0D=OrderedDict(), data1D=OrderedDict(), data2D=None)
        for ind, data in enumerate(datas):
            prog.data_to_export['data1D']['CH{:03d}'.format(ind)] = utils.DataToExport()

        prog.ini_data_plots(len(datas))

        prog.zoom_plot = []
        for ind, data in enumerate(datas):
            channel = prog.ui.Graph_zoom.plot()
            channel.setPen(prog.plot_colors[ind])
            prog.zoom_plot.append(channel)

        prog.ui.zoom_pb.setChecked(True)
        prog.ui.Do_math_pb.setChecked(True)
        prog.ui.scatter.setChecked(True)

        prog.update_graph1D(datas)

        x_axis = np.linspace(0, len(datas[0]), len(datas[0]), endpoint=False)

        assert np.array_equal(prog.x_axis, x_axis)

        for ind, data in enumerate(datas):
            data1D = prog.data_to_export['data1D']['CH{:03d}'.format(ind)]
            dx_axis = data1D['x_axis']

            assert np.array_equal(prog.plot_channels[ind].getData()[0], prog.x_axis)
            assert np.array_equal(prog.plot_channels[ind].getData()[1], data)
            assert np.array_equal(prog.zoom_plot[ind].getData()[0], prog.x_axis)
            assert np.array_equal(prog.zoom_plot[ind].getData()[1], data)
            assert data1D['name'] == prog.title
            assert np.array_equal(data1D['name'], prog.title)
            assert np.array_equal(dx_axis['data'], prog.x_axis)
            assert np.array_equal(dx_axis['units'], prog.axis_settings['units'])
            assert np.array_equal(dx_axis['label'], prog.axis_settings['label'])

        assert np.array_equal(prog.measurement_dict['datas'], datas)
        assert np.array_equal(prog.measurement_dict['x_axis'], prog.x_axis)

        datas = np.linspace(np.linspace(1, 10, 5), np.linspace(11, 20, 5), 2)
        prog.datas = datas

        prog.ui.xyplot_action.setChecked(True)

        prog.update_graph1D(datas)

        x_axis = np.linspace(0, len(datas[0]), len(datas[0]), endpoint=False)

        assert np.array_equal(prog.x_axis, x_axis)
        assert not prog.plot_channels[1].getData()[0]
        assert not prog.plot_channels[1].getData()[1]
        assert np.array_equal(prog.plot_channels[0].getData()[0], datas[0])
        assert np.array_equal(prog.plot_channels[0].getData()[1], datas[1])

    def test_update_measurement_module(self, init_prog):
        prog = init_prog

        Form = prog.ui.Measurement_widget
        prog.measurement_module = DAQ_Measurement(Form)

        datas = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)

        x_data = datas[1]

        prog.measurement_dict = {'x_axis': x_data, 'datas': datas}

        prog.update_measurement_module()

        assert np.array_equal(prog.measurement_module.xdata, x_data)
        assert np.array_equal(prog.measurement_module.ydata, datas[0])

    def test_update_status(self, init_prog):
        prog = init_prog

        prog.update_status('')

    def test_x_axis(self, init_prog):
        prog = init_prog

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


class TestViewer1D_math:
    def test_init(self, init_prog_math):
        prog = init_prog_math

        assert prog.datas == prog.ROI_bounds == prog.operations == prog.channels == []
        assert not prog.x_axis

    def test_update_math(self, init_prog_math):
        prog = init_prog_math
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

        prog.update_math(None)

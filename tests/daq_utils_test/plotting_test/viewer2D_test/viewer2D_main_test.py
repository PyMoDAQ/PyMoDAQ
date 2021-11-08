from qtpy import QtWidgets, QtCore
from pymodaq.daq_utils.plotting.viewer2D import Viewer2D
from pymodaq.daq_utils.exceptions import ExpectedError
from pyqtgraph.parametertree import Parameter
import pyqtgraph as pg
from pymodaq.daq_utils.plotting.graph_items import PlotCurveItem
from unittest import mock

import pytest
import numpy as np
import pyqtgraph as pg

from pyqtgraph import ROI


@pytest.fixture
def init_prog(qtbot):
    form = QtWidgets.QWidget()
    prog = Viewer2D()
    qtbot.addWidget(form)
    return prog

def generate_data():
    Nx = 100
    Ny = 200
    data_random = np.random.normal(size=(Ny, Nx))
    x = np.linspace(0, Nx - 1, Nx)
    y = np.linspace(0, Ny - 1, Ny)
    from pymodaq.daq_utils.daq_utils import gauss2D

    data_red = 3 * gauss2D(x, 0.2 * Nx, Nx / 5, y, 0.3 * Ny, Ny / 5, 1, 90) * np.sin(x/5)**2
    data_green = 3 * gauss2D(x, 0.2 * Nx, Nx / 5, y, 0.3 * Ny, Ny / 5, 1, 0)
    data_blue = data_random + 3 * gauss2D(x, 0.7 * Nx, Nx / 5, y, 0.2 * Ny, Ny / 5, 1)
    data_blue = pg.gaussianFilter(data_blue, (2, 2))
    data_spread = np.load('triangulation_data.npy')

    return data_red, data_green, data_blue, data_spread


def init_raw_data(request):
    request.raw_data = dict()

    request.raw_data['blue'] = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)
    request.raw_data['green'] = np.linspace(np.linspace(11, 20, 10), np.linspace(21, 30, 10), 2)
    request.raw_data['red'] = np.linspace(np.linspace(21, 30, 10), np.linspace(31, 40, 10), 2)
    request.raw_data['spread'] = np.linspace(np.linspace(31, 40, 10), np.linspace(41, 50, 10), 2)

    request.isdata["blue"] = True
    request.isdata["green"] = True
    request.isdata["red"] = True
    request.isdata["spread"] = True


def init_roi(request):
    request.data_to_export = dict(data0D=dict(), data1D=dict(), data2D=dict())

    roi_dict = dict()

    request.roi_manager.ROIs = roi_dict

    item_params = []

    colors = mock.Mock()
    colors.value.side_effect = ['blue', 'green', 'red', 'spread', None]

    for ind in range(5):
        roi_dict['ROI_{:02d}'.format(ind)] = ROI((ind, ind))

        math_param = Parameter(name='math_function')
        math_param.setValue('Mean')
        channel_param = Parameter(name='use_channel')
        channel_param.setValue(colors.value())
        test_list = [0, 1, 2, 3]
        channel_param.opts['limits'] = test_list
        color_param = Parameter(name='Color')
        color_param.setValue(1)

        children = [math_param, channel_param, color_param]
        item_param = Parameter(name='ROI_{:02d}'.format(ind))
        item_param.addChildren(children)

        item_params.append(item_param)

        request.ui.RoiCurve_H['ROI_{:02d}'.format(ind)] = PlotCurveItem(pen=1)
        request.ui.Lineout_H.plotItem.addItem(request.ui.RoiCurve_H['ROI_{:02d}'.format(ind)])

        request.ui.RoiCurve_V['ROI_{:02d}'.format(ind)] = PlotCurveItem(pen=1)
        request.ui.Lineout_V.plotItem.addItem(request.ui.RoiCurve_V['ROI_{:02d}'.format(ind)])

        request.ui.RoiCurve_integrated['ROI_{:02d}'.format(ind)] = PlotCurveItem(pen=1)
        request.ui.Lineout_integrated.plotItem.addItem(request.ui.RoiCurve_integrated['ROI_{:02d}'.format(ind)])

        request.data_integrated_plot['ROI_{:02d}'.format(ind)] = np.zeros((2, 1))

    rois_param = Parameter(name='ROIs', children=item_params)

    request.roi_manager.settings = Parameter(name='settings', children=[rois_param])

    for ind, key in enumerate(request.roi_manager.ROIs):
        color = request.roi_manager.settings.child('ROIs', key, 'use_channel').value()

        if color == 'blue':
            request.ui.img_blue.scene().addItem(request.roi_manager.ROIs[key])
        elif color == 'green':
            request.ui.img_green.scene().addItem(request.roi_manager.ROIs[key])
        elif color == 'red':
            request.ui.img_red.scene().addItem(request.roi_manager.ROIs[key])
        if color is not None:
            request.data_integrated_plot[key] = request.raw_data[color]


class TestViewer2D:
    def test_init(self, init_prog):
        prog = init_prog

        assert isinstance(prog, Viewer2D)

    def test_show_data_setImagered(self, init_prog):
        prog = init_prog
        prog.parent.show()
        data_red, data_green, data_blue, data_spread = generate_data()

        prog.setImage(data_red=data_red)

    def test_show_data_setImageredgreen(self, init_prog):
        prog = init_prog
        prog.parent.show()
        data_red, data_green, data_blue, data_spread = generate_data()

        prog.setImage(data_red=data_red, data_green=data_green)

    def test_show_data_setImageSpread(self, init_prog):
        prog = init_prog
        prog.parent.show()
        data_red, data_green, data_blue, data_spread = generate_data()

        prog.setImage(data_spread=data_spread)

    def test_red_action(self, init_prog):
        prog = init_prog

        prog.red_action.setChecked(False)
        prog.ui.img_red.setVisible(False)

        prog.red_action.trigger()

        assert prog.red_action.isChecked()
        assert prog.ui.img_red.isVisible()

    def test_green_action(self, init_prog):
        prog = init_prog

        prog.green_action.setChecked(False)
        prog.ui.img_green.setVisible(False)

        prog.green_action.trigger()

        assert prog.green_action.isChecked()
        assert prog.ui.img_green.isVisible()

    def test_blue_action(self, init_prog):
        prog = init_prog

        prog.blue_action.setChecked(False)
        prog.ui.img_blue.setVisible(False)

        prog.blue_action.trigger()

        assert prog.blue_action.isChecked()
        assert prog.ui.img_blue.isVisible()

    def test_spread_action(self, init_prog):
        prog = init_prog

        prog.spread_action.setChecked(False)
        prog.ui.img_spread.setVisible(False)

        prog.spread_action.trigger()

        assert prog.spread_action.isChecked()
        assert prog.ui.img_spread.isVisible()

    def test_histo_action(self, init_prog):
        prog = init_prog

        prog.parent.show()

        init_raw_data(prog)
        prog.blue_action.setChecked(True)

        prog.histo_action.trigger()

        assert prog.histo_action.isChecked()
        assert prog.ui.histogram_blue.isVisible()
        assert prog.ui.histogram_blue.region.getRegion() == (1, 20)

    def test_roi_action(self, init_prog):
        prog = init_prog

        prog.parent.show()

        prog.roi_action.setChecked(False)
        prog.roi_manager.roiwidget.setVisible(False)

        prog.roi_action.trigger()

        assert prog.roi_action.isChecked()
        assert prog.roi_manager.roiwidget.isVisible()

    def test_isocurve_action(self, init_prog):
        prog = init_prog

        init_raw_data(prog)

        prog.isocurve_action.setChecked(False)
        prog.histo_action.setChecked(False)

        prog.isocurve_action.trigger()

        assert prog.isocurve_action.isChecked()
        assert prog.histo_action.isChecked()

    def test_ini_plot_action(self, init_prog):
        prog = init_prog

        prog.data_integrated_plot = dict(a=None, b=None, c=None)

        prog.ini_plot_action.trigger()

        for k in prog.data_integrated_plot:
            assert np.array_equal(prog.data_integrated_plot[k], np.zeros((2, 1)))

    def test_aspect_ratio_action(self, init_prog):
        prog = init_prog

        prog.aspect_ratio_action.setChecked(False)
        prog.image_widget.plotitem.vb.setAspectLocked(lock=False)

        prog.aspect_ratio_action.trigger()

        assert prog.aspect_ratio_action.isChecked()
        assert prog.image_widget.plotitem.vb.state['aspectLocked']

    def test_auto_levels_action(self, init_prog):
        prog = init_prog

        prog.auto_levels_action.setChecked(True)
        prog.ui.histogram_red.region.setVisible(False)
        prog.ui.histogram_green.region.setVisible(False)
        prog.ui.histogram_blue.region.setVisible(False)

        prog.auto_levels_action.trigger()

        assert not prog.auto_levels_action.isChecked()
        assert prog.ui.histogram_red.region.isVisible()
        assert prog.ui.histogram_green.region.isVisible()
        assert prog.ui.histogram_blue.region.isVisible()

    def test_crosshair_action(self, init_prog):
        prog = init_prog

        prog.crosshair_action.setChecked(False)
        prog.ui.crosshair.setVisible(False)
        prog.position_action.setVisible(False)

        prog.crosshair_action.trigger()

        assert prog.crosshair_action.isChecked()
        assert prog.ui.crosshair.isVisible()
        assert prog.position_action.isVisible()

    def test_ROIselect_action(self, init_prog):
        prog = init_prog

        prog.ROIselect_action.setChecked(False)
        prog.ui.ROIselect.setVisible(False)

        prog.ROIselect_action.trigger()

        assert prog.ROIselect_action.isChecked()
        assert prog.ui.ROIselect.isVisible()

    def test_FlipUD_action(self, init_prog):
        prog = init_prog

        init_raw_data(prog)
        prog.isdata['red'] = False
        prog.isdata['green'] = False
        prog.isdata['blue'] = False
        prog.isdata['spread'] = False

        prog.FlipUD_action.setChecked(False)

        prog.FlipUD_action.trigger()

        assert prog.FlipUD_action.isChecked()
        assert prog.isdata['red']
        assert prog.isdata['green']
        assert prog.isdata['blue']
        assert prog.isdata['spread']

    def test_FlipLR_action(self, init_prog):
        prog = init_prog

        init_raw_data(prog)
        prog.isdata['red'] = False
        prog.isdata['green'] = False
        prog.isdata['blue'] = False
        prog.isdata['spread'] = False

        prog.FlipLR_action.setChecked(False)

        prog.FlipLR_action.trigger()

        assert prog.FlipLR_action.isChecked()
        assert prog.isdata['red']
        assert prog.isdata['green']
        assert prog.isdata['blue']
        assert prog.isdata['spread']

    def test_rotate_action(self, init_prog):
        prog = init_prog

        init_raw_data(prog)
        prog.isdata['red'] = False
        prog.isdata['green'] = False
        prog.isdata['blue'] = False
        prog.isdata['spread'] = False

        prog.rotate_action.setChecked(False)

        prog.rotate_action.trigger()

        assert prog.rotate_action.isChecked()
        assert prog.isdata['red']
        assert prog.isdata['green']
        assert prog.isdata['blue']
        assert prog.isdata['spread']

    def test_remove_ROI(self, init_prog):
        prog = init_prog
        prog.setupROI()

        init_raw_data(prog)
        init_roi(prog)

        prog.lo_items = prog.roi_manager.ROIs

        prog.add_ROI(newindex=0, roi_type='ROI_00')

        prog.remove_ROI(roi_name='ROI_00')

        assert 'ROI_00' not in prog.ui.RoiCurve_H
        assert 'ROI_00' not in prog.ui.RoiCurve_V
        assert 'ROI_00' not in prog.ui.RoiCurve_integrated

    def test_add_ROI(self, init_prog):
        prog = init_prog
        prog.setupROI()

        init_raw_data(prog)
        init_roi(prog)

        prog.lo_items = prog.roi_manager.ROIs

        prog.isdata['red'] = True

        prog.add_ROI(newindex=0, roi_type='ROI_00')

        assert isinstance(prog.ui.RoiCurve_H['ROI_00'], PlotCurveItem)
        assert isinstance(prog.ui.RoiCurve_V['ROI_00'], PlotCurveItem)
        assert isinstance(prog.ui.RoiCurve_integrated['ROI_00'], PlotCurveItem)
        assert prog.roi_manager.settings.child('ROIs', 'ROI_00', 'use_channel').value() == 'red'

        prog.isdata['red'] = False
        prog.isdata['green'] = True

        prog.add_ROI(newindex=0, roi_type='ROI_00')

        assert prog.roi_manager.settings.child('ROIs', 'ROI_00', 'use_channel').value() == 'green'

        prog.isdata['green'] = False
        prog.isdata['blue'] = True

        prog.add_ROI(newindex=0, roi_type='ROI_00')

        assert prog.roi_manager.settings.child('ROIs', 'ROI_00', 'use_channel').value() == 'blue'

        prog.isdata['blue'] = False
        prog.isdata['spread'] = True

        prog.add_ROI(newindex=0, roi_type='ROI_00')

        assert prog.roi_manager.settings.child('ROIs', 'ROI_00', 'use_channel').value() == 'spread'

    def test_crosshairChanged(self, init_prog):
        prog = init_prog

        assert not prog.crosshairChanged()

        init_raw_data(prog)

        data_red = prog.raw_data['red']
        prog.ui.img_red.setImage(data_red, autoLevels=prog.autolevels)

        prog.isdata['spread'] = False

        prog.ui.crosshair_H_blue.setData(y=None, x=None)
        prog.ui.crosshair_V_blue.setData(y=None, x=None)
        prog.ui.crosshair_H_green.setData(y=None, x=None)
        prog.ui.crosshair_V_green.setData(y=None, x=None)
        prog.ui.crosshair_H_red.setData(y=None, x=None)
        prog.ui.crosshair_V_red.setData(y=None, x=None)

        assert np.array_equal(prog.ui.crosshair_H_blue.getData()[0], np.array([]))
        assert np.array_equal(prog.ui.crosshair_H_blue.getData()[1], np.array([]))
        assert np.array_equal(prog.ui.crosshair_V_blue.getData()[0], np.array([]))
        assert np.array_equal(prog.ui.crosshair_V_blue.getData()[1], np.array([]))
        assert np.array_equal(prog.ui.crosshair_H_green.getData()[0], np.array([]))
        assert np.array_equal(prog.ui.crosshair_H_green.getData()[1], np.array([]))
        assert np.array_equal(prog.ui.crosshair_V_green.getData()[0], np.array([]))
        assert np.array_equal(prog.ui.crosshair_V_green.getData()[1], np.array([]))
        assert np.array_equal(prog.ui.crosshair_H_red.getData()[0], np.array([]))
        assert np.array_equal(prog.ui.crosshair_H_red.getData()[1], np.array([]))
        assert np.array_equal(prog.ui.crosshair_V_red.getData()[0], np.array([]))
        assert np.array_equal(prog.ui.crosshair_V_red.getData()[1], np.array([]))

        prog.crosshairChanged(1, 1)

        assert not np.array_equal(prog.ui.crosshair_H_blue.getData()[0], np.array([]))
        assert not np.array_equal(prog.ui.crosshair_H_blue.getData()[1], np.array([]))
        assert not np.array_equal(prog.ui.crosshair_V_blue.getData()[0], np.array([]))
        assert not np.array_equal(prog.ui.crosshair_V_blue.getData()[1], np.array([]))
        assert not np.array_equal(prog.ui.crosshair_H_green.getData()[0], np.array([]))
        assert not np.array_equal(prog.ui.crosshair_H_green.getData()[1], np.array([]))
        assert not np.array_equal(prog.ui.crosshair_V_green.getData()[0], np.array([]))
        assert not np.array_equal(prog.ui.crosshair_V_green.getData()[1], np.array([]))
        assert not np.array_equal(prog.ui.crosshair_H_red.getData()[0], np.array([]))
        assert not np.array_equal(prog.ui.crosshair_H_red.getData()[1], np.array([]))
        assert not np.array_equal(prog.ui.crosshair_V_red.getData()[0], np.array([]))
        assert not np.array_equal(prog.ui.crosshair_V_red.getData()[1], np.array([]))

    def test_crosshairClicked(self, init_prog):
        prog = init_prog

        prog.ui.crosshair.setVisible(False)
        prog.position_action.setVisible(False)

        prog.ui.crosshair_H_blue.setVisible(False)
        prog.ui.crosshair_V_blue.setVisible(False)

        prog.ui.crosshair_H_green.setVisible(False)
        prog.ui.crosshair_V_green.setVisible(False)

        prog.ui.crosshair_H_red.setVisible(False)
        prog.ui.crosshair_V_red.setVisible(False)

        prog.ui.crosshair_H_spread.setVisible(False)
        prog.ui.crosshair_V_spread.setVisible(False)

        init_raw_data(prog)

        prog.crosshair_action.setChecked(True)

        prog.crosshairClicked()

        assert prog.ui.crosshair.isVisible()
        assert prog.position_action.isVisible()

        assert prog.ui.crosshair_H_blue.isVisible()
        assert prog.ui.crosshair_V_blue.isVisible()

        assert prog.ui.crosshair_H_green.isVisible()
        assert prog.ui.crosshair_V_green.isVisible()

        assert prog.ui.crosshair_H_red.isVisible()
        assert prog.ui.crosshair_V_red.isVisible()

        assert prog.ui.crosshair_H_spread.isVisible()
        assert prog.ui.crosshair_V_spread.isVisible()

    def test_double_clicked(self, init_prog):
        prog = init_prog

        prog.double_clicked(posx=10, posy=20)

        assert prog.ui.crosshair.vLine.value() == 10
        assert prog.ui.crosshair.hLine.value() == 20

    def test_ini_plot(self, init_prog):
        prog = init_prog

        for ind in range(10):
            prog.data_integrated_plot['plot_{:02d}'.format(ind)] = None

        prog.ini_plot()

        for key in prog.data_integrated_plot.keys():
            assert np.array_equal(prog.data_integrated_plot[key], np.zeros((2, 1)))

    def test_lock_aspect_ratio(self, init_prog):
        prog = init_prog

        prog.image_widget.plotitem.vb.setAspectLocked(lock=False)
        assert not prog.image_widget.plotitem.vb.state['aspectLocked']

        prog.aspect_ratio_action.setChecked(True)
        assert prog.aspect_ratio_action.isChecked()

        prog.lock_aspect_ratio()

        assert prog.image_widget.plotitem.vb.state['aspectLocked']

        prog.aspect_ratio_action.setChecked(False)
        assert not prog.aspect_ratio_action.isChecked()

        prog.lock_aspect_ratio()

        assert not prog.image_widget.plotitem.vb.state['aspectLocked']

    @pytest.mark.skip(reason='Test not implemented')
    def test_restore_state(self, init_prog):
        prog = init_prog

    # @pytest.mark.skip(reason="Test not finished")
    def test_roi_changed(self, init_prog):
        prog = init_prog

        init_raw_data(prog)

        init_roi(prog)

        prog.data_to_export = dict(data0D=dict(), data1D=dict(), data2D=dict())

        prog.roi_changed()

    def test_update_roi(self, init_prog):
        prog = init_prog

        init_raw_data(prog)
        init_roi(prog)

        for ind in range(4):
            prog.add_ROI(ind, 'ROI_{:02d}'.format(ind))

        change_1 = [prog.roi_manager.settings.child('ROIs', 'ROI_00', 'Color'), 'value', 1]
        change_2 = [None, 'childAdded', None]
        change_3 = [prog.roi_manager.settings.child('ROIs', 'ROI_01'), 'parent', None]

        changes = [change_1, change_2, change_3]

        prog.update_roi(changes)

        assert prog.ui.RoiCurve_H['ROI_00'].opts['pen'].color().getRgb() == (255, 170, 0, 255)
        assert prog.ui.RoiCurve_V['ROI_00'].opts['pen'].color().getRgb() == (255, 170, 0, 255)
        assert prog.ui.RoiCurve_integrated['ROI_00'].opts['pen'].color().getRgb() == (255, 170, 0, 255)

        assert 'ROI_01' not in prog.ui.RoiCurve_H
        assert 'ROI_01' not in prog.ui.RoiCurve_V
        assert 'ROI_01' not in prog.ui.RoiCurve_integrated

    def test_roi_clicked(self, init_prog):
        prog = init_prog

        roi_dict = {'ROI_00': ROI((0, 0))}

        prog.roi_manager.ROIs = roi_dict

        item_param_0 = Parameter(name='ROI_00')

        color_param = Parameter(name='Color')
        color_param.setValue(1)

        children = [color_param]
        item_param_0.addChildren(children)

        item_params = [item_param_0]

        rois_param = Parameter(name='ROIs', children=item_params)

        prog.roi_manager.settings = Parameter(name='settings', children=[rois_param])

        prog.add_ROI(0, 'ROI_00')

        prog.roi_action.setChecked(True)

        prog.roi_clicked()

        assert prog.ui.RoiCurve_H['ROI_00'].isVisible()
        assert prog.ui.RoiCurve_V['ROI_00'].isVisible()
        assert prog.ui.RoiCurve_integrated['ROI_00'].isVisible()

        prog.roi_action.setChecked(False)

        prog.roi_clicked()

        assert not prog.ui.RoiCurve_H['ROI_00'].isVisible()
        assert not prog.ui.RoiCurve_V['ROI_00'].isVisible()
        assert not prog.ui.RoiCurve_integrated['ROI_00'].isVisible()

    def test_scale_axis(self, init_prog):
        prog = init_prog

        x_data = np.linspace(2, 10, 5)
        label = 'label'
        units = 'nm'

        x_axis = {'data': x_data, 'label': label, 'units': units}

        prog.x_axis = x_axis

        y_data = np.linspace(10, 2, 5)
        label = 'label'
        units = 'nm'

        y_axis = {'data': y_data, 'label': label, 'units': units}

        prog.y_axis = y_axis

        x, y = prog.scale_axis(xaxis_pxl=1, yaxis_pxl=1)

        assert x == 4
        assert y == 8

    def test_unscale_axis(self, init_prog):
        prog = init_prog

        x_data = np.linspace(2, 10, 5)
        label = 'label'
        units = 'nm'

        x_axis = {'data': x_data, 'label': label, 'units': units}

        prog.x_axis = x_axis

        y_data = np.linspace(10, 2, 5)
        label = 'label'
        units = 'nm'

        y_axis = {'data': y_data, 'label': label, 'units': units}

        prog.y_axis = y_axis

        x, y = prog.unscale_axis(xaxis=4, yaxis=8)

        assert x == 1
        assert y == 1

    def test_selected_region_changed(self, init_prog):
        prog = init_prog

        roi_select_signal = mock.Mock()
        roi_select_signal.emit.side_effect = [ExpectedError]

        prog.setupUI()
        prog.ROI_select_signal = roi_select_signal

        prog.ROIselect_action.setChecked(True)

        with pytest.raises(ExpectedError):
            prog.selected_region_changed()

    def test_set_autolevels(self, init_prog):
        prog = init_prog

        prog.ui.histogram_blue.imageItem().setLevels(None)
        prog.ui.histogram_green.imageItem().setLevels(None)
        prog.ui.histogram_red.imageItem().setLevels(None)

        prog.ui.histogram_blue.region.setVisible(True)
        prog.ui.histogram_green.region.setVisible(True)
        prog.ui.histogram_red.region.setVisible(True)
        prog.auto_levels_action.setChecked(True)

        prog.set_autolevels()

        assert not prog.ui.histogram_blue.region.isVisible()
        assert not prog.ui.histogram_green.region.isVisible()
        assert not prog.ui.histogram_red.region.isVisible()

        prog.auto_levels_action.setChecked(False)

        prog.set_autolevels()

        blue = prog.ui.histogram_blue
        green = prog.ui.histogram_green
        red = prog.ui.histogram_red

        assert np.array_equal(blue.imageItem().getLevels(), blue.getLevels())
        assert np.array_equal(green.imageItem().getLevels(), green.getLevels())
        assert np.array_equal(red.imageItem().getLevels(), red.getLevels())

        assert prog.ui.histogram_blue.region.isVisible()
        assert prog.ui.histogram_green.region.isVisible()
        assert prog.ui.histogram_red.region.isVisible()

    def test_set_scaling_axes(self, init_prog):
        prog = init_prog

        scaled_xaxis = dict(scaling=1, offset=3, label='x_axis', units='nm')

        scaled_yaxis = dict(scaling=3, offset=2.5, label='y_axis', units='dm')

        scaling_options = dict(scaled_xaxis=scaled_xaxis, scaled_yaxis=scaled_yaxis)

        prog.set_scaling_axes(scaling_options=scaling_options)

        x_axis = prog.scaled_xaxis
        y_axis = prog.scaled_yaxis

        assert x_axis.scaling == scaled_xaxis['scaling']
        assert x_axis.offset == scaled_xaxis['offset']
        assert x_axis.labelText == scaled_xaxis['label']
        assert x_axis.labelUnits == scaled_xaxis['units']

        assert y_axis.scaling == scaled_yaxis['scaling']
        assert y_axis.offset == scaled_yaxis['offset']
        assert y_axis.labelText == scaled_yaxis['label']
        assert y_axis.labelUnits == scaled_yaxis['units']

        assert x_axis.range == pytest.approx([-4.1981733, 10.1981733], 0.01)
        assert y_axis.range == pytest.approx([-14.0014728, 19.0014728], 0.01)

    def test_transform_image(self, init_prog):
        prog = init_prog

        data = np.linspace(np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2),
                           np.linspace(np.linspace(21, 30, 10), np.linspace(31, 40, 10), 2), 2)

        prog.FlipUD_action.setChecked(False)
        prog.FlipLR_action.setChecked(False)
        prog.rotate_action.setChecked(False)

        result = prog.transform_image(data=data)
        data_2 = np.mean(data, axis=0)

        assert np.array_equal(result, data_2)

        prog.FlipUD_action.setChecked(True)

        result = prog.transform_image(data=data)
        data_3 = np.flipud(data_2)

        assert np.array_equal(result, data_3)

        prog.FlipLR_action.setChecked(True)

        result = prog.transform_image(data=data)
        data_4 = np.fliplr(data_3)

        assert np.array_equal(result, data_4)

        prog.rotate_action.setChecked(True)

        result = prog.transform_image(data=data)
        data_5 = np.flipud(np.transpose(data_4))

        assert np.array_equal(result, data_5)

        assert not prog.transform_image(data=None)

    def test_set_image_transform(self, init_prog):
        prog = init_prog

        init_raw_data(prog)

        prog.FlipUD_action.setVisible(False)
        prog.FlipLR_action.setVisible(False)
        prog.rotate_action.setVisible(False)

        data_red, data_blue, data_green  = prog.set_image_transform()

        assert prog.FlipUD_action.isVisible()
        assert prog.FlipLR_action.isVisible()
        assert prog.rotate_action.isVisible()

        assert np.array_equal(data_blue, prog.raw_data['blue'])
        assert np.array_equal(data_green, prog.raw_data['green'])
        assert np.array_equal(data_red, prog.raw_data['red'])

    def test_set_visible_items(self, init_prog):
        prog = init_prog

        prog.parent.show()

        prog.histo_action.setChecked(True)

        prog.isdata = dict()
        prog.isdata['blue'] = False
        prog.isdata['green'] = False
        prog.isdata['red'] = False
        prog.isdata['spread'] = False

        prog.blue_action.setChecked(True)
        prog.blue_action.setVisible(True)
        prog.ui.histogram_blue.setVisible(True)

        prog.green_action.setChecked(True)
        prog.green_action.setVisible(True)
        prog.ui.histogram_green.setVisible(True)

        prog.red_action.setChecked(True)
        prog.red_action.setVisible(True)
        prog.ui.histogram_red.setVisible(True)

        prog.spread_action.setChecked(True)
        prog.spread_action.setVisible(True)
        prog.ui.histogram_spread.setVisible(True)

        prog.set_visible_items()

        assert not prog.blue_action.isChecked()
        assert not prog.blue_action.isVisible()
        assert not prog.ui.histogram_blue.isVisible()

        assert not prog.green_action.isChecked()
        assert not prog.green_action.isVisible()
        assert not prog.ui.histogram_green.isVisible()

        assert not prog.red_action.isChecked()
        assert not prog.red_action.isVisible()
        assert not prog.ui.histogram_red.isVisible()

        assert not prog.spread_action.isChecked()
        assert not prog.spread_action.isVisible()
        assert not prog.ui.histogram_spread.isVisible()

        init_raw_data(prog)

        prog.set_visible_items()

        assert prog.blue_action.isChecked()
        assert prog.blue_action.isVisible()
        assert prog.ui.histogram_blue.isVisible()

        assert prog.green_action.isChecked()
        assert prog.green_action.isVisible()
        assert prog.ui.histogram_green.isVisible()

        assert prog.red_action.isChecked()
        assert prog.red_action.isVisible()
        assert prog.ui.histogram_red.isVisible()

        assert prog.spread_action.isChecked()
        assert prog.spread_action.isVisible()
        assert prog.ui.histogram_spread.isVisible()

    def test_setImage(self, init_prog):
        prog = init_prog

        prog.setImage()

        assert not prog.isdata['blue']
        assert not prog.isdata['green']
        assert not prog.isdata['red']
        assert not prog.isdata['spread']
        assert prog.data_to_export['acq_time_s']

        init_raw_data(prog)
        prog.roi_action.setChecked(True)
        prog.isocurve_action.setChecked(True)
        prog.crosshair_action.setChecked(True)

        data = prog.raw_data

        prog.setImage(data['red'], data['green'], data['blue'], data['spread'])

        assert prog.isdata['blue']
        assert prog.isdata['green']
        assert prog.isdata['red']
        assert prog.isdata['spread']

        shape = data['red'].shape
        assert np.array_equal(prog.x_axis, np.linspace(0, shape[1]-1, shape[1]))
        assert np.array_equal(prog.y_axis, np.linspace(0, shape[0]-1, shape[0]))
        assert np.array_equal(prog.x_axis_scaled, prog.x_axis)
        assert np.array_equal(prog.y_axis_scaled, prog.y_axis)
        for ind in range (4):
            assert prog.data_to_export['data2D']['CH{:03d}'.format(ind)]

        assert np.array_equal(prog.ui.iso.data, pg.gaussianFilter(data['red'], (2, 2)))

        prog.isdata = None

        prog.setImage()

    def test_setImageTemp(self, init_prog):
        prog = init_prog

        prog.setImageTemp()

        assert not prog.isdata['blue']
        assert not prog.isdata['green']
        assert not prog.isdata['red']
        assert not prog.isdata['spread']

        data_blue = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)
        data_green = np.linspace(np.linspace(11, 20, 10), np.linspace(21, 30, 10), 2)
        data_red = np.linspace(np.linspace(21, 30, 10), np.linspace(31, 40, 10), 2)
        data_spread = np.linspace(np.linspace(31, 40, 10), np.linspace(41, 50, 10), 2)

        prog.setImageTemp(data_blue=data_blue, data_green=data_green, data_red=data_red, data_spread=data_spread)

        assert prog.isdata['blue']
        assert prog.isdata['green']
        assert prog.isdata['red']
        assert prog.isdata['spread']

        assert np.array_equal(prog.ui.img_blue.image, data_blue)
        assert np.array_equal(prog.ui.img_green.image, data_green)
        assert np.array_equal(prog.ui.img_red.image, data_red)
        assert np.array_equal(prog.ui.img_spread.image, data_spread)

    def test_mapfromview(self, init_prog):
        prog = init_prog

        graphitem = 'None'
        x = None
        y = None

        prog.mapfromview(graphitem=graphitem, x=x, y=y)

        graphitem = 'red'
        x = 1
        y = 2

        result = prog.mapfromview(graphitem=graphitem, x=x, y=y)
        assert result == (x, y)

    def test_setObjectName(self, init_prog):
        prog = init_prog

        prog.setObjectName('test')

        assert prog.parent.objectName() == 'test'

    def test_show_hide_histogram(self, init_prog):
        prog = init_prog

        prog.parent.show()

        init_raw_data(prog)

        prog.blue_action.setChecked(True)
        prog.green_action.setChecked(True)
        prog.red_action.setChecked(True)
        prog.spread_action.setChecked(True)
        prog.histo_action.setChecked(True)

        prog.show_hide_histogram()

        assert prog.ui.histogram_blue.isVisible()
        assert prog.ui.histogram_blue.region.getRegion() == (1, 20)
        assert prog.ui.histogram_green.isVisible()
        assert prog.ui.histogram_green.region.getRegion() == (11, 30)
        assert prog.ui.histogram_red.isVisible()
        assert prog.ui.histogram_red.region.getRegion() == (21, 40)
        assert prog.ui.histogram_spread.isVisible()
        assert prog.ui.histogram_spread.region.getRegion() == (31, 50)

    def test_show_hide_iso(self, init_prog):
        prog = init_prog

        prog.isocurve_action.setChecked(True)
        prog.histo_action.setChecked(False)

        prog.raw_data = dict()
        prog.raw_data['red'] = np.linspace(1, 10, 10)

        prog.show_hide_iso()

        assert prog.histo_action.isChecked()
        result = pg.gaussianFilter(prog.raw_data['red'], (2, 2))
        for val1, val2 in zip(prog.ui.iso.data, result):
            assert val1 == pytest.approx(val2)

    @pytest.mark.skip(reason="Test not implemented")
    def test_show_lineouts(self, init_prog):
        prog = init_prog

    @pytest.mark.skip(reason="Test not implemented")
    def test_show_ROI_select(self, init_prog):
        prog = init_prog

        prog.setupUI()
        prog.parent.show()

        #prog.ui.ROIselect.setVisible(False)
        #prog.ROIselect_action.setChecked(True)
        #prog.show_ROI_select()
        prog.ROIselect_action.trigger()

        assert prog.ui.ROIselect.isVisible()

    def test_update_image(self, init_prog):
        prog = init_prog

        init_raw_data(prog)

        prog.update_image()

        assert prog.isdata['blue']
        assert prog.isdata['green']
        assert prog.isdata['red']
        assert prog.isdata['spread']

        assert np.array_equal(prog.ui.img_blue.image, prog.raw_data['blue'])
        assert np.array_equal(prog.ui.img_green.image, prog.raw_data['green'])
        assert np.array_equal(prog.ui.img_red.image, prog.raw_data['red'])
        assert np.array_equal(prog.ui.img_spread.image, prog.raw_data['spread'])

    def test_update_selection_area_visibility(self, init_prog):
        prog = init_prog

        prog.ui.img_blue.setVisible(False)
        prog.ui.img_green.setVisible(False)
        prog.ui.img_red.setVisible(False)

        prog.blue_action.setChecked(True)
        prog.green_action.setChecked(True)
        prog.red_action.setChecked(True)

        prog.update_selection_area_visibility()

        assert prog.ui.img_blue.isVisible()
        assert prog.ui.img_green.isVisible()
        assert prog.ui.img_red.isVisible()

        prog.blue_action.setChecked(False)
        prog.green_action.setChecked(False)
        prog.red_action.setChecked(False)

        prog.update_selection_area_visibility()

        assert not prog.ui.img_blue.isVisible()
        assert not prog.ui.img_green.isVisible()
        assert not prog.ui.img_red.isVisible()

    def test_update_crosshair_data(self, init_prog):
        prog = init_prog

        init_raw_data(prog)

        data_red = prog.raw_data['red']
        prog.ui.img_red.setImage(data_red, autoLevels=prog.autolevels)

        prog.isdata['spread'] = False

        prog.position_action.setText('')

        prog.update_crosshair_data(1, 1)

        assert 'r' in prog.position_action.text()
        assert 'b' in prog.position_action.text()
        assert 'g' in prog.position_action.text()

    def test_updateIsocurve(self, init_prog):
        prog = init_prog

        prog.ui.isoLine.setValue(5)

        prog.updateIsocurve()

        assert prog.ui.iso.level == 5

    def test_x_axis(self, init_prog):
        prog = init_prog

        prog.x_axis_scaled = 'x_axis_scaled'

        assert prog.x_axis == 'x_axis_scaled'

    def test_x_axis_setter(self, init_prog):
        prog = init_prog

        data = np.linspace(1, 10, 10)
        label = 'label'
        units = 'nm'

        x_axis = {'data': data, 'label': label, 'units': units}

        prog.x_axis = x_axis

        scaled_axis = prog.scaling_options['scaled_xaxis']
        assert scaled_axis['offset'] == 1
        assert scaled_axis['scaling'] == 1
        assert scaled_axis['label'] == label
        assert scaled_axis['units'] == units

        x_axis = np.linspace(10, 1, 10)

        prog.x_axis = x_axis

        scaled_axis = prog.scaling_options['scaled_xaxis']
        assert scaled_axis['offset'] == 10
        assert scaled_axis['scaling'] == -1
        assert scaled_axis['label'] == ''
        assert scaled_axis['units'] == ''

        x_axis = [10]

        prog.x_axis = x_axis

        scaled_axis = prog.scaling_options['scaled_xaxis']
        assert scaled_axis['offset'] == 0
        assert scaled_axis['scaling'] == 1

    def test_set_axis_label(self, init_prog):
        prog = init_prog

        prog.set_axis_label()

        scaled_xaxis = prog.scaling_options['scaled_xaxis']
        assert scaled_xaxis['orientation'] == 'bottom'
        assert scaled_xaxis['label'] == 'x axis'
        assert scaled_xaxis['units'] == 'pxls'

        axis_settings = dict(orientation='left', label='y axis', units='nm')

        prog.set_axis_label(axis_settings=axis_settings)

        scaled_xaxis = prog.scaling_options['scaled_yaxis']
        assert scaled_xaxis['orientation'] == 'left'
        assert scaled_xaxis['label'] == 'y axis'
        assert scaled_xaxis['units'] == 'nm'

    def test_y_axis(self, init_prog):
        prog = init_prog

        prog.y_axis_scaled = 'y_axis_scaled'

        assert prog.y_axis == 'y_axis_scaled'

    def test_y_axis_setter(self, init_prog):
        prog = init_prog

        data = np.linspace(1, 10, 10)
        label = 'label'
        units = 'nm'

        y_axis = {'data': data, 'label': label, 'units': units}

        prog.y_axis = y_axis

        scaled_axis = prog.scaling_options['scaled_yaxis']
        assert scaled_axis['offset'] == 1
        assert scaled_axis['scaling'] == 1
        assert scaled_axis['label'] == label
        assert scaled_axis['units'] == units

        y_axis = np.linspace(10, 1, 10)

        prog.y_axis = y_axis

        scaled_axis = prog.scaling_options['scaled_yaxis']
        assert scaled_axis['offset'] == 10
        assert scaled_axis['scaling'] == -1
        assert scaled_axis['label'] == ''
        assert scaled_axis['units'] == ''

        y_axis = [10]

        prog.y_axis = y_axis

        scaled_axis = prog.scaling_options['scaled_yaxis']
        assert scaled_axis['offset'] == 0
        assert scaled_axis['scaling'] == 1

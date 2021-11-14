import pymodaq.daq_utils.managers.action_manager
import pymodaq.daq_utils.plotting.utils.filter
import pymodaq.daq_utils.plotting.utils.plot_utils
from qtpy import QtWidgets, QtCore
from pymodaq.daq_utils.plotting.data_viewers.viewer2D import Viewer2D
from pymodaq.daq_utils.plotting.data_viewers import viewer2D as v2d
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils.exceptions import ViewerError
from pymodaq.daq_utils.managers.roi_manager import ROIManager
from pathlib import Path
import pytest
from pytest import fixture, approx
import numpy as np
import pyqtgraph as pg

from pyqtgraph import mkPen

@fixture
def init_qt(qtbot):
    return qtbot

def init_data():
    Nx = 100
    Ny = 200
    data_random = np.random.normal(size=(Ny, Nx))
    x = np.linspace(0, Nx - 1, Nx)
    y = np.linspace(0, Ny - 1, Ny)
    from pymodaq.daq_utils.daq_utils import gauss2D

    data_red = 3 * gauss2D(x, 0.2 * Nx, Nx / 5, y, 0.3 * Ny, Ny / 5, 1, 90) * np.sin(x / 5) ** 2
    data_green = 24 * gauss2D(x, 0.2 * Nx, Nx / 5, y, 0.3 * Ny, Ny / 5, 1, 0)
    data_blue = 10 * gauss2D(x, 0.7 * Nx, Nx / 5, y, 0.2 * Ny, Ny / 5, 1)
    data_blue = pg.gaussianFilter(data_blue, (2, 2))
    here = Path(__file__).parent
    data_spread = np.load(str(here.joinpath('triangulation_data.npy')))
    return data_red, data_green, data_blue, data_spread


@fixture
def init_prog(qtbot):
    form = QtWidgets.QWidget()
    prog = Viewer2D()
    qtbot.addWidget(form)

    prog.parent.show()
    
    return prog, qtbot

@fixture
def init_prog_show_data(init_prog, distribution='uniform'):
    prog, qtbot = init_prog
    data_red, data_green, data_blue, data_spread = init_data()
    if distribution == 'uniform':
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green, data_blue])
    else:
        data = utils.DataFromPlugins(distribution='uniform', data=[data_spread])
    prog.show_data(data)
    return prog, qtbot, (data_red, data_green, data_blue, data_spread)


def create_one_roi(prog, qtbot, roitype='RectROI'):
    prog.view.get_action('roi').trigger()
    QtWidgets.QApplication.processEvents()
    with qtbot.waitSignal(prog.view.roi_manager.new_ROI_signal, timeout=10000) as blocker:
        prog.view.roi_manager.add_roi_programmatically(roitype)
    index_roi = blocker.args[0]
    roi_type = blocker.args[1]

    roi = prog.view.roi_manager.get_roi_from_index(index_roi)
    QtWidgets.QApplication.processEvents()
    return index_roi, roi, roi_type


class TestImageFactory:
    @pytest.mark.parametrize('item_type', ['uniform', 'spread'])
    def test_create_image(self, init_qt, item_type):
        image_item = v2d.image_item_factory(item_type=item_type)
        assert isinstance(image_item, pg.ImageItem)

    @pytest.mark.parametrize('axisOrder', ('row-major', 'col-major'))
    def test_axisorder(self, init_qt, axisOrder):
        image_item = v2d.image_item_factory('uniform', axisOrder)

    def test_axisorder(self, init_qt):
        axisOrder = 'a random order'
        with pytest.raises(ValueError):
            image_item = v2d.image_item_factory('uniform', axisOrder)


class TestHistoFactory:
    @pytest.mark.parametrize('gradient', ['red', 'spread'])
    def test_create_histo(self, init_qt, gradient):
        histo = v2d.histogram_factory(gradient=gradient)
        assert isinstance(histo, pg.HistogramLUTWidget)

    def test_wrong_gradient(self, init_qt):
        with pytest.raises(KeyError):
            histo = v2d.histogram_factory(gradient='yuipof135748f')

    def test_set_image(self, init_qt):
        image_item = pg.graphicsItems.ImageItem.ImageItem(np.random.rand(10,50))
        histo = v2d.histogram_factory(image_item, gradient='red')

        assert histo.imageItem() is image_item


class TestCurveFactory:
    @pytest.mark.parametrize('pen', list(v2d.COLORS_DICT.keys())+v2d.COLOR_LIST)
    def test_create_curve(self, init_qt, pen):
        curve = v2d.curve_item_factory(pen=pen)
        assert isinstance(curve, pg.PlotCurveItem)

    def test_wrong_pen(self, init_qt):
        with pytest.raises(ValueError):
            curve = v2d.curve_item_factory(pen='this is not a valid color key')


class TestData0DWithHistory:
    def test_add_datas_list(self, init_qt):
        Nsamplesinhisto = 2
        data_histo = pymodaq.daq_utils.plotting.utils.plot_utils.Data0DWithHistory(Nsamplesinhisto)
        dat = [[1, 2], [np.array([1]), 2], [1, 2], [1, 2], [1, 2], [1, 2]]
        for ind, d in enumerate(dat):
            data_histo.add_datas(d)
            assert data_histo._data_length == ind+1
            assert np.any(data_histo.xaxis == approx(np.linspace(max(0, ind+1-Nsamplesinhisto), ind+1,
                                                                 min(Nsamplesinhisto, ind+1)
                                                                 , endpoint=False, dtype=float)))
            assert 'data_00' in data_histo.datas
            assert 'data_01' in data_histo.datas

    def test_add_datas(self, init_qt):
        data_histo = pymodaq.daq_utils.plotting.utils.plot_utils.Data0DWithHistory()
        dat = [dict(CH0=1, CH1=2.), dict(CH0=np.array([1]), CH1=2.), dict(CH0=1, CH1=2.), dict(CH0=1, CH1=2.)]
        for ind, d in enumerate(dat):
            data_histo.add_datas(d)
            assert data_histo._data_length == ind+1
            assert np.any(data_histo.xaxis == approx(np.linspace(0, ind+1, ind+1, endpoint=False)))
            assert 'CH0' in data_histo.datas
            assert 'CH1' in data_histo.datas

    def test_add_datas_and_clear(self, init_qt):
        data_histo = pymodaq.daq_utils.plotting.utils.plot_utils.Data0DWithHistory()
        dat = [dict(CH0=1, CH1=2.), dict(CH0=np.array([1]), CH1=2.), dict(CH0=1, CH1=2.), dict(CH0=1, CH1=2.)]
        for ind, d in enumerate(dat):
            data_histo.add_datas(d)
        data_histo.clear_data()

        assert data_histo.datas == dict([])
        assert data_histo._data_length == 0


class TestExtractAxis:
    def test_info_data_is_None(self):
        axis = utils.Axis(label='mylabel', units='myunits')
        assert pymodaq.daq_utils.plotting.utils.plot_utils.AxisInfosExtractor.extract_axis_info(axis) == (1, 0, 'mylabel', 'myunits')

    def test_info(self):
        axis = utils.Axis(label='mylabel', units='myunits', data=np.array([5, 20, 35]))
        assert pymodaq.daq_utils.plotting.utils.plot_utils.AxisInfosExtractor.extract_axis_info(axis) == (15, 5, 'mylabel', 'myunits')

    def test_info_data_is_ndarray(self):
        axis = np.array([5, 20, 35])
        assert pymodaq.daq_utils.plotting.utils.plot_utils.AxisInfosExtractor.extract_axis_info(axis) == (15, 5, '', '')

    def test_info_data_is_ndarray_scalingisneg(self):
        axis = np.array([35, 20, 5])
        assert pymodaq.daq_utils.plotting.utils.plot_utils.AxisInfosExtractor.extract_axis_info(axis) == (-15, 35, '', '')

    def test_info_neg_scaling(self):
        axis = utils.Axis(label='mylabel', units='myunits', data=np.array([35, 20, 5]))
        assert pymodaq.daq_utils.plotting.utils.plot_utils.AxisInfosExtractor.extract_axis_info(axis) == (-15, 35, 'mylabel', 'myunits')


class TestLineoutData:
    def test_with_error(self):
        with pytest.raises(ValueError):
            pymodaq.daq_utils.plotting.utils.filter.LineoutData(hor_axis=np.random.random(10), hor_data=np.random.random(12))

        with pytest.raises(ValueError):
            pymodaq.daq_utils.plotting.utils.filter.LineoutData(ver_axis=np.random.random(10), ver_data=np.random.random(12))

    def test_intdataisnotnone(self):
        pymodaq.daq_utils.plotting.utils.filter.LineoutData(ver_axis=np.random.random(10), ver_data=np.random.random(10), int_data=np.array([10]))

    def test_intdataisnone(self):
        pymodaq.daq_utils.plotting.utils.filter.LineoutData(ver_axis=np.random.random(10), ver_data=np.random.random(10))


class TestLineoutPlotter:
    pass


class TestViewer2D:
    def test_init(self, init_prog):
        prog, qtbot = init_prog
        assert isinstance(prog, Viewer2D)

    @pytest.mark.parametrize('dim', [(0,), (10,), (3, 3, 3)])
    def test_viewer_error(self, init_prog, dim):
        prog, qtbot = init_prog
        data = prog.format_data_as_datafromplugins(data_red=np.zeros(dim))
        with pytest.raises(ViewerError):
            prog.show_data(data)


    def test_show_data_triggers_data_to_export_signal(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])

        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000) as blocker:
            prog.show_data(data)

        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000) as blocker:
            prog.show_data(data)

    def test_show_data_setImagered(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        with qtbot.waitSignal(prog.data_to_export_signal, timeout=10000) as blocker:
            prog.setImage(data_red=data_red)

        data_to_export_from_signal = blocker.args[0]
        for elt in ['acq_time_s', 'name', 'data0D', 'data1D']:
            assert elt in prog.data_to_export.keys()
            assert elt in data_to_export_from_signal

        assert prog.data_to_export == data_to_export_from_signal
        assert prog.data_to_export['name'] == prog.title
        assert len(data_to_export_from_signal['data0D']) == 0
        assert len(data_to_export_from_signal['data1D']) == 0

    @pytest.mark.xfail
    def test_setimage_temp(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        with qtbot.waitSignal(prog.data_to_export_signal, timeout=500) as blocker:
            prog.setImageTemp(data_red=data_red)

    def test_show_data_setImageredblue(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        
        prog.setImage(data_red=data_red, data_blue=data_blue)
        assert prog.view.is_action_checked('red')
        assert prog.view.is_action_checked('green')
        assert prog.view.is_action_checked('blue')

    def test_show_data_setImageSpread(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        
        prog.setImage(data_spread=data_spread)

        assert prog.view.is_action_checked('red')
        assert not prog.view.is_action_checked('green')
        assert not prog.view.is_action_checked('blue')

    def test_show_data_uniform(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_blue])
        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000) as blocker:
            prog.show_data(data)

        assert prog.view.is_action_checked('red')
        assert prog.view.is_action_checked('green')
        assert not prog.view.is_action_checked('blue')
        assert prog.isdata['red']
        assert prog.isdata['green']
        assert not prog.isdata['blue']

    def test_show_data_spread(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        
        data = utils.DataFromPlugins(distribution='spread', data=[data_spread, data_spread])
        prog.show_data(data)
        assert prog.view.is_action_checked('red')
        assert prog.view.is_action_checked('green')
        assert not prog.view.is_action_checked('blue')

    def test_update_data_roi(self, init_prog_show_data):
        prog, qtbot, _ = init_prog_show_data
        create_one_roi(prog, qtbot)
        QtWidgets.QApplication.processEvents()

        with qtbot.waitSignal(prog.roi_lineout_signal, timeout=1000) as blocker:
            prog.update_data()

    def test_update_data_crosshair(self, init_prog_show_data):
        prog, qtbot, _ = init_prog_show_data
        prog.view.get_action('crosshair').trigger()
        QtWidgets.QApplication.processEvents()

        with qtbot.waitSignal(prog.crosshair_lineout_signal, timeout=1000) as blocker:
            prog.update_data()


class TestAxis:
    @pytest.mark.parametrize('position', ('left', 'bottom', 'right', 'top'))
    def test_axis_label(self, init_prog, position):
        prog, qtbot = init_prog
        UNITS= 'myunits'
        LABEL = 'mylabel'

        prog.view.set_axis_label(position, label=LABEL, units=UNITS)
        assert prog.view.get_axis_label(position) == (LABEL, UNITS)

    def test_get_axis_error(self, init_prog):
        prog, qtbot = init_prog

        with pytest.raises(KeyError):
            prog.view.get_axis_label('unvalid key')

    def test_set_scaling_axes(self, init_prog):
        prog, qtbot = init_prog
        XUNITS= 'myxunits'
        XLABEL = 'myxlabel'
        XSCALING = 0.1
        XOFFSET = 24

        YUNITS= 'myyunits'
        YLABEL = 'myylabel'
        YSCALING = -2.1
        YOFFSET = 0.87

        x_scaling_options = utils.ScaledAxis(scaling=XSCALING, offset=XOFFSET, label=XLABEL, units=XUNITS)
        y_scaling_options = utils.ScaledAxis(scaling=YSCALING, offset=YOFFSET, label=YLABEL, units=YUNITS)
        prog.set_scaling_axes(utils.ScalingOptions(x_scaling_options, y_scaling_options))

        assert prog.x_axis.axis_units == XUNITS
        assert prog.x_axis.axis_label == XLABEL
        assert prog.x_axis.axis_offset == XOFFSET
        assert prog.x_axis.axis_scaling == XSCALING
        assert prog.y_axis.axis_units == YUNITS
        assert prog.y_axis.axis_label == YLABEL
        assert prog.y_axis.axis_offset == YOFFSET
        assert prog.y_axis.axis_scaling == YSCALING

    def test_scale_axis(self, init_prog):
        prog, qtbot = init_prog
        XSCALING = 0.1
        XOFFSET = 24
        YSCALING = -2.1
        YOFFSET = 0.87
        prog.x_axis.axis_scaling = XSCALING
        prog.x_axis.axis_offset = XOFFSET
        prog.y_axis.axis_scaling = YSCALING
        prog.y_axis.axis_offset = YOFFSET

        xaxis = np.linspace(0., 10., 20)
        yaxis = np.linspace(0, 20., 10)
        xscaled , yscaled = prog.view.scale_axis(xaxis, yaxis)
        assert np.any(xscaled == approx(xaxis * XSCALING + XOFFSET))
        assert np.any(yscaled == approx(yaxis * YSCALING + YOFFSET))

        xaxis_bis, yaxis_bis = prog.view.unscale_axis(*prog.view.scale_axis(xaxis, yaxis))
        assert np.any(xaxis_bis == approx(xaxis))
        assert np.any(yaxis_bis == approx(yaxis))


class TestActions:
    @pytest.mark.parametrize('action', ['position', 'red', 'green', 'blue', 'autolevels', 'auto_levels_sym',
                                        'histo', 'roi', 'isocurve', 'aspect_ratio', 'crosshair',
                                        'ROIselect', 'flip_ud', 'flip_lr', 'rotate'])
    def test_actionhas(self, qtbot, action):
        action_manager = pymodaq.daq_utils.managers.action_manager.ActionManager()
        assert action_manager.has_action(action)

    @pytest.mark.parametrize('color', ['red', 'green', 'blue'])
    def test_color_action(self, init_prog, color):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        prog.setImage(data_red=data_red, data_green=data_green, data_blue=data_blue)

        assert prog.view.data_displayer.get_image(color).isVisible()
        assert prog.view.is_action_checked(color)

        prog.view.get_action(color).trigger()

        assert not prog.view.is_action_checked(color)
        assert not prog.view.data_displayer.get_image(color).isVisible()

    def test_histo_action(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()

        
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        prog.view.get_action('histo').trigger()

        assert prog.view.is_action_checked('histo')
        assert prog.view.histogrammer.get_histogram('red').isVisible()
        assert prog.view.histogrammer.get_histogram('green').isVisible()
        assert not prog.view.histogrammer.get_histogram('blue').isVisible()

    def test_histo_autolevel_action(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green, data_blue])
        prog.show_data(data)
        prog.view.get_action('histo').trigger()

        assert prog.view.histogrammer.get_histogram('red').getLevels() == approx((0, 1.))
        assert prog.view.histogrammer.get_histogram('green').getLevels() == approx((0, 1.))
        assert prog.view.histogrammer.get_histogram('blue').getLevels() == approx((0, 1.))

        prog.view.get_action('autolevels').trigger()

        assert prog.view.histogrammer.get_histogram('red').getLevels() == approx((0, 2.9392557954529277))
        assert prog.view.histogrammer.get_histogram('green').getLevels() == approx((0., 24.0))
        assert prog.view.histogrammer.get_histogram('blue').getLevels() ==\
               approx((5.693320370703248e-09, 9.83017824174412))

    def test_autolevel_action(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        prog.view.get_action('autolevels').trigger()
        assert prog.view.histogrammer.autolevels
        assert prog.view.data_displayer.autolevels

        prog.view.get_action('autolevels').trigger()
        assert not prog.view.histogrammer.autolevels
        assert not prog.view.data_displayer.autolevels


class TestHistogrammer:
    @pytest.mark.parametrize('color', ['red', 'green', 'blue'])
    def test_get_histogram(self, init_prog, color):
        prog, qtbot = init_prog

        assert color in prog.view.histogrammer.get_histograms()
        assert prog.view.histogrammer.get_histogram(color) == prog.view.histogrammer.get_histograms()[color]

    def test_get_histogram_name_error(self, init_prog):
        prog, qtbot = init_prog
        with pytest.raises(KeyError):
            prog.view.histogrammer.get_histogram('not a valid identifier')

    def test_histo_connected_to_image(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green, data_blue])
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()
        for color in ['red', 'green', 'blue']:
            assert prog.view.histogrammer.get_histogram(color).getLookupTable == \
                   prog.view.data_displayer.get_image(color).lut

    def test_histo_connected_to_image_spread(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        
        data = utils.DataFromPlugins(distribution='spread', data=[data_spread, data_spread, data_spread])
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()
        for color in ['red', 'green', 'blue']:
            assert prog.view.histogrammer.get_histogram(color).getLookupTable == \
                   prog.view.data_displayer.get_image(color).lut

    @pytest.mark.parametrize('histo', ['red', 'blue', 'green', 'all'])
    @pytest.mark.parametrize('gradient', ['blue', 'green', 'spread'])
    def test_setgradient(self, init_prog_show_data, histo, gradient):
        prog, qtbot, _ = init_prog_show_data
        prog.view.histogrammer.set_gradient(histo, gradient)


class TestROI:
    def test_roi_action(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        create_one_roi(prog, qtbot, roitype='RectROI')

        assert prog.view.is_action_checked('roi')
        assert prog.view.roi_manager.roiwidget.isVisible()

    def test_add_roi(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='RectROI')
        assert roi_type == 'RectROI'
        assert index_roi == 0
        assert len(prog.view.lineout_plotter.get_roi_curves_triplet()) == 1

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='EllipseROI')
        assert roi_type == 'EllipseROI'
        assert index_roi == 1
        assert len(prog.view.lineout_plotter.get_roi_curves_triplet()) == 2

    def test_remove_roi(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='RectROI')

        prog.view.roi_manager.remove_roi_programmatically(index_roi)
        QtWidgets.QApplication.processEvents()

        assert len(prog.view.lineout_plotter._roi_curves) == 0

    def test_update_color_roi(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='RectROI')

        prog.view.roi_manager.settings.child('ROIs', ROIManager.roi_format(index_roi), 'Color').setValue('b')
        roi = prog.view.roi_manager.get_roi_from_index(index_roi)
        QtWidgets.QApplication.processEvents()
        assert roi.pen == mkPen('b')

    def test_data_from_roi(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='RectROI')
        roi.setPos((0, 0))

        assert prog.view.is_action_checked('roi')

        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000) as blocker:
            roi.setSize((data_red.T).shape)
            roi.setPos((0, 0))

        data_to_export = blocker.args[0]
        assert len(data_to_export['data1D']) != 0
        assert len(data_to_export['data0D']) != 0

        assert f'{prog.title}_Hlineout_{ROIManager.roi_format(index_roi)}' in data_to_export['data1D']
        assert f'{prog.title}_Vlineout_{ROIManager.roi_format(index_roi)}' in data_to_export['data1D']
        assert f'{prog.title}_Integrated_{ROIManager.roi_format(index_roi)}' in data_to_export['data0D']

        hlineout = data_to_export['data1D'][f'{prog.title}_Hlineout_{ROIManager.roi_format(index_roi)}']
        vlineout = data_to_export['data1D'][f'{prog.title}_Vlineout_{ROIManager.roi_format(index_roi)}']
        intlineout = data_to_export['data0D'][f'{prog.title}_Integrated_{ROIManager.roi_format(index_roi)}']

        assert np.any(hlineout['data'] == approx(np.mean(data_red, 0)))
        assert np.any(vlineout['data'] == approx(np.mean(data_red, 1)))
        assert np.any(intlineout['data'] == approx(np.mean(data_red)))

    def test_data_from_roi_spread(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()

        data = utils.DataFromPlugins(distribution='spread', data=[data_spread])
        prog.show_data(data)

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='RectROI')
        roi.setPos((0, 0))

        assert prog.view.is_action_checked('roi')

        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000) as blocker:
            roi.setSize((data_red.T).shape)
            roi.setPos((0, 0))

        data_to_export = blocker.args[0]
        assert len(data_to_export['data1D']) != 0
        assert len(data_to_export['data0D']) != 0

        assert f'{prog.title}_Hlineout_{ROIManager.roi_format(index_roi)}' in data_to_export['data1D']
        assert f'{prog.title}_Vlineout_{ROIManager.roi_format(index_roi)}' in data_to_export['data1D']
        assert f'{prog.title}_Integrated_{ROIManager.roi_format(index_roi)}' in data_to_export['data0D']

    def test_data_from_roi_without_data(self, init_prog):
        prog, qtbot = init_prog

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='RectROI')
        roi.setPos((0, 0))

        assert prog.view.is_action_checked('roi')


class TestIsocurve:

    def test_isocurve_action(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        prog.view.get_action('isocurve').trigger()

        assert prog.view.is_action_checked('isocurve')
        assert prog.view.is_action_checked('histo')

    @pytest.mark.parametrize('histo', ['blue', 'green', 'red'])
    @pytest.mark.parametrize('im_source', ['blue', 'green', 'red'])
    def test_isocurve_parent(self, init_prog, im_source, histo):
        prog, qtbot = init_prog
        prog.view.isocurver.update_image_source(prog.view.data_displayer.get_image(im_source))
        prog.view.isocurver.update_histogram_parent(prog.view.histogrammer.get_histogram(histo))

    def test_change_isoline(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        ISOLEVEL = 0.1

        prog.view.get_action('isocurve').trigger()
        prog.view.isocurver._isoLine.setValue(ISOLEVEL)
        prog.view.isocurver._isoLine.sigDragged.emit(prog.view.isocurver._isoLine)
        QtWidgets.QApplication.processEvents()
        assert prog.view.isocurver._isocurve_item.level == ISOLEVEL


class TestAspectRatio:
    def test_aspect_ratio_action(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        prog.view.get_action('aspect_ratio').trigger()
        assert prog.view.is_action_checked('aspect_ratio')
        assert prog.view.image_widget.plotitem.vb.state['aspectLocked']

        prog.view.get_action('aspect_ratio').trigger()
        assert not prog.view.is_action_checked('aspect_ratio')
        assert not prog.view.image_widget.plotitem.vb.state['aspectLocked']


class TestCrosshair:
    def test_crosshair_action(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)
        assert not prog.view.is_action_visible('position')

        prog.view.get_action('crosshair').trigger()
        QtWidgets.QApplication.processEvents()

        assert prog.view.is_action_checked('crosshair')
        assert prog.view.is_action_visible('position')
        assert prog.view.crosshair.isVisible()
        for image_key in v2d.IMAGE_TYPES:
            for curve_key, curve in prog.view.lineout_plotter.get_crosshair_curves_triplet()[image_key].items():
                assert curve.isVisible()
                assert curve == prog.view.lineout_plotter.get_crosshair_curve_triplet(image_key)[curve_key]

        prog.view.get_action('crosshair').trigger()
        QtWidgets.QApplication.processEvents()

        prog.view.get_action('roi').trigger()  # will keep lineout_widgets visible so we can check
        # if crosshair lineouts are still visible
        QtWidgets.QApplication.processEvents()

        assert not prog.view.is_action_checked('crosshair')
        assert not prog.view.is_action_visible('position')
        assert not prog.view.crosshair.isVisible()
        for image_key in v2d.IMAGE_TYPES:
            for curve in prog.view.lineout_plotter.get_crosshair_curves_triplet()[image_key].values():
                assert not curve.isVisible()

    def test_setpos_crosshair(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()
        XCROSS = 24
        YCROSS = 75

        with qtbot.waitSignal(prog.crosshair_dragged, timeout=1000) as blocker:
            prog.view.get_action('crosshair').trigger()

        with qtbot.waitSignal(prog.crosshair_dragged, timeout=1000) as blocker:
            prog.view.crosshair.set_crosshair_position(XCROSS, YCROSS)

        assert blocker.args[0] == approx(XCROSS)
        assert blocker.args[1] == approx(YCROSS)

    @pytest.mark.parametrize('position', [(24, 75), (300, 10), (50, 300)])
    def test_get_crosshair_lineout_uniform(self, init_prog, position):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        datas = dict(red=data_red, green=data_green)
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()

        XCROSS, YCROSS = position

        prog.view.get_action('crosshair').trigger()
        QtWidgets.QApplication.processEvents()

        with qtbot.waitSignal(prog.view.lineout_plotter.crosshair_lineout_plotted, timeout=1000) as blocker:
            prog.view.crosshair.set_crosshair_position(XCROSS, YCROSS)

        crosshair_dict = blocker.args[0]
        for data_key, lineout_data in crosshair_dict.items():
            if YCROSS < 0 or YCROSS > datas[data_key].shape[0]:
                assert np.any(lineout_data.hor_data == approx(np.zeros((datas[data_key].shape[1],))))
            else:
                assert np.any(lineout_data.hor_data == approx(datas[data_key][YCROSS, :]))
            if XCROSS < 0 or XCROSS > datas[data_key].shape[1]:
                assert np.any(lineout_data.ver_data == approx(np.zeros((datas[data_key].shape[0],))))
            else:
                assert np.any(lineout_data.ver_data == approx(datas[data_key][:, XCROSS]))

    @pytest.mark.parametrize('position', [(-2., -3), (2., 1.), (50, 300)])
    def test_get_crosshair_lineout_spread(self, init_prog, position):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        data = utils.DataFromPlugins(distribution='spread', data=[data_spread])
        datas = dict(spread=data_spread)
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()

        red_image_item = prog.view.data_displayer.get_image('red')
        XCROSS, YCROSS = position

        prog.view.get_action('crosshair').trigger()
        QtWidgets.QApplication.processEvents()

        with qtbot.waitSignal(prog.view.lineout_plotter.crosshair_lineout_plotted, timeout=1000) as blocker:
            prog.view.crosshair.set_crosshair_position(XCROSS, YCROSS)

        crosshair_dict = blocker.args[0]
        data_H_index = slice(None, None, 1)
        data_V_index = slice(None, None, 1)
        for data_key, lineout_data in crosshair_dict.items():
            points, hor_data = red_image_item.get_points_at('y', position[1])
            x_sorted_indexes = np.argsort(points[:, 0])
            hor_data = hor_data[x_sorted_indexes][data_H_index]

            points, ver_data = red_image_item.get_points_at('x', position[0])
            x_sorted_indexes = np.argsort(points[:, 1])
            ver_data = ver_data[x_sorted_indexes][data_V_index]

            assert np.any(lineout_data.hor_data == approx(hor_data))
            assert np.any(lineout_data.ver_data == approx(ver_data))

    def test_crosshair_doubleclicked(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        prog.view.get_action('crosshair').trigger()
        with qtbot.waitSignal(prog.sig_double_clicked, timeout=10000) as blocker:
            prog.view.get_double_clicked().emit(10.5, 20.9)

        assert prog.view.get_crosshair_position()[0] == approx(10.5)
        assert prog.view.get_crosshair_position()[1] == approx(20.9)


class TestRoiSelect:
    def test_ROIselect_action(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()

        prog.view.get_action('ROIselect').trigger()
        with qtbot.waitSignal(prog.ROI_select_signal, timeout=1000) as blocker:
            prog.view.ROIselect.setSize((20, 35))

        with qtbot.waitSignal(prog.ROI_select_signal, timeout=1000) as blocker:
            prog.view.ROIselect.setPos((45, 123))

        assert isinstance(blocker.args[0], QtCore.QRectF)
        assert blocker.args[0].x() == 45
        assert blocker.args[0].y() == 123
        assert blocker.args[0].width() == 20
        assert blocker.args[0].height() == 35


class TestImageDisplayer:
    def test_get_image(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()

        with pytest.raises(KeyError):
            prog.view.data_displayer.get_image('not a valid image name')

    def test_update_display_items(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()

        data = utils.DataFromPlugins(distribution='spread', data=[data_spread])
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()

class TestModifyImages:
    def test_FlipUD_action(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        datas = dict(red=data_red, green=data_green)

        with qtbot.waitSignal(prog.data_to_show_signal, timeout=1000) as blocker:
            prog.show_data(data)

        for ind, data_to_show in enumerate(blocker.args[0]['data']):
            assert np.any(data_to_show == approx(data['data'][ind]))

        with qtbot.waitSignal(prog.data_to_show_signal, timeout=1000) as blocker:
            prog.view.get_action('flip_ud').trigger()
        for ind, data_to_show in enumerate(blocker.args[0]['data']):
            assert np.any(data_to_show == approx(np.flipud(data['data'][ind])))

    def test_FlipLR_action(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        with qtbot.waitSignal(prog.data_to_show_signal, timeout=1000) as blocker:
            prog.view.get_action('flip_lr').trigger()
        for ind, data_to_show in enumerate(blocker.args[0]['data']):
            assert np.any(data_to_show == approx(np.fliplr(data['data'][ind])))

        with qtbot.waitSignal(prog.data_to_show_signal, timeout=1000) as blocker:
            prog.view.get_action('flip_lr').trigger()
        for ind, data_to_show in enumerate(blocker.args[0]['data']):
            assert np.any(data_to_show == approx(data['data'][ind]))

    def test_rotate_action(self, init_prog):
        prog, qtbot = init_prog
        data_red, data_green, data_blue, data_spread = init_data()
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        with qtbot.waitSignal(prog.data_to_show_signal, timeout=1000) as blocker:
            prog.view.get_action('rotate').trigger()
        for ind, data_to_show in enumerate(blocker.args[0]['data']):
            assert np.any(data_to_show == approx(np.flipud(np.transpose(data['data'][ind]))))

        with qtbot.waitSignal(prog.data_to_show_signal, timeout=1000) as blocker:
            prog.view.get_action('rotate').trigger()
        for ind, data_to_show in enumerate(blocker.args[0]['data']):
            assert np.any(data_to_show == approx(data['data'][ind]))


class TestMiscellanous:
    def test_double_clicked(self, init_prog):
        prog, qtbot = init_prog
        with qtbot.waitSignal(prog.sig_double_clicked, timeout=10000) as blocker:
            prog.view.get_double_clicked().emit(10.5, 20.9)

        assert blocker.args[0] == approx(10.5)
        assert blocker.args[1] == approx(20.9)
from qtpy import QtWidgets, QtCore
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D
from pymodaq.daq_utils.plotting.viewer2D import viewer2D_main as v2d
from pymodaq.daq_utils.exceptions import ExpectedError
from pymodaq.daq_utils import daq_utils as utils
from pyqtgraph.parametertree import Parameter
import pyqtgraph as pg
from pymodaq.daq_utils.plotting.graph_items import PlotCurveItem
from pymodaq.daq_utils.managers.roi_manager import ROIManager
from unittest import mock
from pathlib import Path
import pytest
from pytest import fixture, approx
import numpy as np
import pyqtgraph as pg

from pyqtgraph import ROI, mkPen

@fixture
def init_qt(qtbot):
    return qtbot


@fixture
def init_prog(qtbot):
    form = QtWidgets.QWidget()
    prog = Viewer2D()
    qtbot.addWidget(form)
    Nx = 100
    Ny = 200
    data_random = np.random.normal(size=(Ny, Nx))
    x = np.linspace(0, Nx - 1, Nx)
    y = np.linspace(0, Ny - 1, Ny)
    from pymodaq.daq_utils.daq_utils import gauss2D

    data_red = 3 * gauss2D(x, 0.2 * Nx, Nx / 5, y, 0.3 * Ny, Ny / 5, 1, 90) * np.sin(x/5)**2
    data_green = 24 * gauss2D(x, 0.2 * Nx, Nx / 5, y, 0.3 * Ny, Ny / 5, 1, 0)
    data_blue = 10 * gauss2D(x, 0.7 * Nx, Nx / 5, y, 0.2 * Ny, Ny / 5, 1)
    data_blue = pg.gaussianFilter(data_blue, (2, 2))
    here = Path(__file__).parent
    data_spread = np.load(str(here.joinpath('triangulation_data.npy')))
    prog.parent.show()
    
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


class TestData0DWithHistory:
    def test_add_datas_list(self, init_qt):
        Nsamplesinhisto = 2
        data_histo = v2d.Data0DWithHistory(Nsamplesinhisto)
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
        data_histo = v2d.Data0DWithHistory()
        dat = [dict(CH0=1, CH1=2.), dict(CH0=np.array([1]), CH1=2.), dict(CH0=1, CH1=2.), dict(CH0=1, CH1=2.)]
        for ind, d in enumerate(dat):
            data_histo.add_datas(d)
            assert data_histo._data_length == ind+1
            assert np.any(data_histo.xaxis == approx(np.linspace(0, ind+1, ind+1, endpoint=False)))
            assert 'CH0' in data_histo.datas
            assert 'CH1' in data_histo.datas

    def test_add_datas_and_clear(self, init_qt):
        data_histo = v2d.Data0DWithHistory()
        dat = [dict(CH0=1, CH1=2.), dict(CH0=np.array([1]), CH1=2.), dict(CH0=1, CH1=2.), dict(CH0=1, CH1=2.)]
        for ind, d in enumerate(dat):
            data_histo.add_datas(d)
        data_histo.clear_data()

        assert data_histo.datas == dict([])
        assert data_histo._data_length == 0


class TestExtractAxis:
    def test_info_data_is_None(self):
        axis = utils.Axis(label='mylabel', units='myunits')
        assert v2d.extract_axis_info(axis) == (1, 0, 'mylabel', 'myunits')

    def test_info(self):
        axis = utils.Axis(label='mylabel', units='myunits', data=np.array([5, 20, 35]))
        assert v2d.extract_axis_info(axis) == (15, 5, 'mylabel', 'myunits')

    def test_info_data_is_ndarray(self):
        axis = np.array([5, 20, 35])
        assert v2d.extract_axis_info(axis) == (15, 5, '', '')

    def test_info_neg_scaling(self):
        axis = utils.Axis(label='mylabel', units='myunits', data=np.array([35, 20, 5]))
        assert v2d.extract_axis_info(axis) == (-15, 35, 'mylabel', 'myunits')


class TestLineoutData:
    def test_with_error(self):
        with pytest.raises(ValueError):
            v2d.LineoutData(hor_axis=np.random.random(10), hor_data=np.random.random(12))

        with pytest.raises(ValueError):
            v2d.LineoutData(ver_axis=np.random.random(10), ver_data=np.random.random(12))


class TestViewer2D:
    def test_init(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        assert isinstance(prog, Viewer2D)

    def test_double_clicked(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        with qtbot.waitSignal(prog.sig_double_clicked, timeout=10000) as blocker:
            prog.view.get_double_clicked().emit(10.5, 20.9)

        assert blocker.args[0] == approx(10.5)
        assert blocker.args[1] == approx(20.9)

    def test_show_data_triggers_data_to_export_signal(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog

        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])

        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000) as blocker:
            prog.show_data(data)

        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000) as blocker:
            prog.show_data(data)

    def test_show_data_setImagered(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        
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

    def test_show_data_setImageredblue(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        
        prog.setImage(data_red=data_red, data_blue=data_blue)
        assert prog.view.is_action_checked('red')
        assert prog.view.is_action_checked('green')
        assert prog.view.is_action_checked('blue')

    def test_show_data_setImageSpread(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        
        prog.setImage(data_spread=data_spread)

        assert prog.view.is_action_checked('red')
        assert not prog.view.is_action_checked('green')
        assert not prog.view.is_action_checked('blue')

    def test_show_data_uniform(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        
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
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        
        data = utils.DataFromPlugins(distribution='spread', data=[data_spread, data_spread])
        prog.show_data(data)
        assert prog.view.is_action_checked('red')
        assert prog.view.is_action_checked('green')
        assert not prog.view.is_action_checked('blue')

    @pytest.mark.parametrize('color', ['red', 'green', 'blue'])
    def test_color_action(self, init_prog, color):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        prog.setImage(data_red=data_red, data_green=data_green, data_blue=data_blue)

        assert prog.view.data_displayer.get_image(color).isVisible()
        assert prog.view.is_action_checked(color)

        prog.view.get_action(color).trigger()

        assert not prog.view.is_action_checked(color)
        assert not prog.view.data_displayer.get_image(color).isVisible()

    def test_histo_action(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog

        
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        prog.view.get_action('histo').trigger()

        assert prog.view.is_action_checked('histo')
        assert prog.view.histogrammer.get_histogram('red').isVisible()
        assert prog.view.histogrammer.get_histogram('green').isVisible()
        assert not prog.view.histogrammer.get_histogram('blue').isVisible()

    def test_histo_autolevel_action(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        
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


class TestHistogrammer:
    def test_histo_connected_to_image(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green, data_blue])
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()
        for color in ['red', 'green', 'blue']:
            assert prog.view.histogrammer.get_histogram(color).getLookupTable == \
                   prog.view.data_displayer.get_image(color).lut

    def test_histo_connected_to_image_spread(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        
        data = utils.DataFromPlugins(distribution='spread', data=[data_spread, data_spread, data_spread])
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()
        for color in ['red', 'green', 'blue']:
            assert prog.view.histogrammer.get_histogram(color).getLookupTable == \
                   prog.view.data_displayer.get_image(color).lut


class TestROI:
    def test_roi_action(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        create_one_roi(prog, qtbot, roitype='RectROI')

        assert prog.view.is_action_checked('roi')
        assert prog.view.roi_manager.roiwidget.isVisible()

    def test_add_roi(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='RectROI')
        assert roi_type == 'RectROI'
        assert index_roi == 0
        assert len(prog.view.lineout_plotter.get_roi_curves()) == 1

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='EllipseROI')
        assert roi_type == 'EllipseROI'
        assert index_roi == 1
        assert len(prog.view.lineout_plotter.get_roi_curves()) == 2

    def test_remove_roi(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='RectROI')

        prog.view.roi_manager.remove_roi_programmatically(index_roi)
        QtWidgets.QApplication.processEvents()

        assert len(prog.view.lineout_plotter._roi_curves) == 0

    def test_update_color_roi(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='RectROI')

        prog.view.roi_manager.settings.child('ROIs', ROIManager.roi_format(index_roi), 'Color').setValue('b')
        roi = prog.view.roi_manager.get_roi_from_index(index_roi)
        QtWidgets.QApplication.processEvents()
        assert roi.pen == mkPen('b')

    def test_data_from_roi(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        
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

class TestIsocurve:

    def test_isocurve_action(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)

        prog.view.get_action('isocurve').trigger()

        assert prog.view.is_action_checked('isocurve')
        assert prog.view.is_action_checked('histo')


class TestAspectRatio:
    def test_aspect_ratio_action(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
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
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        prog.show_data(data)
        assert not prog.view.is_action_visible('position')

        prog.view.get_action('crosshair').trigger()

        QtWidgets.QApplication.processEvents()
        assert prog.view.is_action_checked('crosshair')
        assert prog.view.is_action_visible('position')
        assert prog.view.crosshair.isVisible()

    def test_setpos_crosshair(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
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
    def test_get_crosshair_lineout(self, init_prog, position):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        data = utils.DataFromPlugins(distribution='uniform', data=[data_red, data_green])
        datas = dict(red=data_red, green=data_green)
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()

        XCROSS, YCROSS = position

        prog.view.get_action('crosshair').trigger()
        QtWidgets.QApplication.processEvents()
        assert 'red' in prog.view.lineout_plotter.get_crosshair_curves()
        assert 'green' in prog.view.lineout_plotter.get_crosshair_curves()

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

    def test_crosshair_doubleclicked(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
        prog.view.get_action('crosshair').trigger()
        with qtbot.waitSignal(prog.sig_double_clicked, timeout=10000) as blocker:
            prog.view.get_double_clicked().emit(10.5, 20.9)

        assert prog.view.get_crosshair_position()[0] == approx(10.5)
        assert prog.view.get_crosshair_position()[1] == approx(20.9)

class TestRoiSelect:
    def test_ROIselect_action(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog

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

class TestModifyImages:
    def test_FlipUD_action(self, init_prog):
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
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
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
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
        prog, qtbot, (data_red, data_green, data_blue, data_spread) = init_prog
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

class TestScaling:
    pass

class TestMiscellanous:
    pass
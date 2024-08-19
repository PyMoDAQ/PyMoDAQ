from typing import Tuple

import pymodaq.utils.managers.action_manager
import pymodaq.utils.plotting.utils.filter
import pymodaq.utils.plotting.utils.plot_utils
from qtpy import QtWidgets, QtCore

from pymodaq.utils import data as data_mod
from pymodaq.utils.plotting.data_viewers.viewer2D import Viewer2D
from pymodaq.utils.plotting.data_viewers import viewer2D as v2d
from pymodaq.utils.exceptions import ViewerError
from pymodaq.utils.managers.roi_manager import ROIManager
import pymodaq.utils.plotting.utils.plot_utils as plot_utils
from pathlib import Path
import pytest
from pytest import fixture, approx
import numpy as np
import pyqtgraph as pg
from pymodaq.utils.plotting.utils.plot_utils import RoiInfo, Point

from pyqtgraph import mkPen
from pymodaq.utils.conftests import qtbotskip

pytestmark = pytest.mark.skipif(False, reason='qtbot issues but tested locally')

@fixture
def init_qt(qtbot):
    return qtbot


def init_data(Ndata=1, uniform=True):
    Nx = 100
    Ny = 200
    data_random = np.random.normal(size=(Ny, Nx))
    x = np.linspace(0, Nx - 1, Nx)
    y = np.linspace(0, Ny - 1, Ny)
    from pymodaq.utils.math_utils import gauss2D
    if uniform:
        data_red = 3 * gauss2D(x, 0.2 * Nx, Nx / 5, y, 0.3 * Ny, Ny / 5, 1, 90) * np.sin(x / 5) ** 2
        data_green = 24 * gauss2D(x, 0.2 * Nx, Nx / 5, y, 0.3 * Ny, Ny / 5, 1, 0)
        data_blue = 10 * gauss2D(x, 0.7 * Nx, Nx / 5, y, 0.2 * Ny, Ny / 5, 1)
        data_blue = pg.gaussianFilter(data_blue, (2, 2))
        data_list = [data_red, data_green, data_blue]
        data = data_mod.DataRaw('raw', data=[data_list[ind] for ind in range(min(3, Ndata))])
    else:
        here = Path(__file__).parent
        data_spread = np.load(str(here.joinpath('triangulation_data.npy')))
        axes = [data_mod.Axis(data=data_spread[:, 0], index=0, label='x_axis', units='xunits', spread_order=0),
                data_mod.Axis(data=data_spread[:, 1], index=0, label='y_axis', units='yunits', spread_order=1)]
        data_list = [data_spread[:, 2] for _ in range(Ndata)]
        data = data_mod.DataRaw('raw', distribution='spread', dim='DataND', data=data_list, nav_indexes=(0,),
                                axes=axes)

    return data


@fixture
def init_viewer2D(qtbot) -> Tuple[Viewer2D, None]:
    form = QtWidgets.QWidget()
    prog = Viewer2D()
    qtbot.addWidget(form)

    prog.parent.show()
    
    yield prog, qtbot
    form.close()

@fixture
def init_prog_show_data(init_viewer2D, distribution='uniform'):
    prog, qtbot = init_viewer2D
    data = init_data(3, uniform=(distribution == 'uniform'))
    prog.show_data(data)
    return prog, qtbot, data


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


class TestData0DWithHistory:
    def test_add_datas_list(self, init_qt):
        Nsamplesinhisto = 2
        data_histo = plot_utils.Data0DWithHistory(Nsamplesinhisto)
        dat = [[1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2]]
        for ind, d in enumerate(dat):
            data_histo.add_datas(d)
            assert data_histo._data_length == ind+1
            assert np.any(data_histo.xaxis == approx(np.linspace(max(0, ind+1-Nsamplesinhisto), ind+1,
                                                                 min(Nsamplesinhisto, ind+1)
                                                                 , endpoint=False, dtype=float)))
            assert 'data_00' in data_histo.datas
            assert 'data_01' in data_histo.datas

    def test_add_datas(self, init_qt):
        data_histo = plot_utils.Data0DWithHistory()
        dat = [dict(CH0=1, CH1=2.), dict(CH0=np.array([1]), CH1=2.), dict(CH0=1, CH1=2.), dict(CH0=1, CH1=2.)]
        for ind, d in enumerate(dat):
            data_histo.add_datas(d)
            assert data_histo._data_length == ind+1
            assert np.any(data_histo.xaxis == approx(np.linspace(0, ind+1, ind+1, endpoint=False)))
            assert 'CH0' in data_histo.datas
            assert 'CH1' in data_histo.datas

    def test_add_datas_and_clear(self, init_qt):
        data_histo = plot_utils.Data0DWithHistory()
        dat = [dict(CH0=1, CH1=2.), dict(CH0=np.array([1]), CH1=2.), dict(CH0=1, CH1=2.), dict(CH0=1, CH1=2.)]
        for ind, d in enumerate(dat):
            data_histo.add_datas(d)
        data_histo.clear_data()

        assert data_histo.datas == dict([])
        assert data_histo._data_length == 0


class TestViewer2D:
    def test_init(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        assert isinstance(prog, Viewer2D)

    def test_show_data_triggers_data_to_export_signal(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()

        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000) as blocker:
            prog.show_data(data)

        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000) as blocker:
            prog.show_data(data)

    @pytest.mark.xfail
    def test_show_data_temp(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()
        with qtbot.waitSignal(prog.data_to_export_signal, timeout=500) as blocker:
            prog.show_data_temp(data)

    def test_show_data_setImageredblue(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data(3)
        
        prog.show_data(data)
        assert prog.view.is_action_checked('red')
        assert prog.view.is_action_checked('green')
        assert prog.view.is_action_checked('blue')
        assert prog.view.is_action_visible('red')
        assert prog.view.is_action_visible('green')
        assert prog.view.is_action_visible('blue')

    def test_show_data_uniform(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data(2)
        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000) as blocker:
            prog.show_data(data)

        assert prog.view.is_action_checked('red')
        assert prog.view.is_action_checked('green')
        assert prog.view.is_action_checked('blue')
        assert prog.view.is_action_visible('red')
        assert prog.view.is_action_visible('green')
        assert not prog.view.is_action_visible('blue')
        assert prog.isdata['red']
        assert prog.isdata['green']
        assert not prog.isdata['blue']

    def test_show_data_spread(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data(2, uniform=False)

        prog.show_data(data)
        assert prog.view.is_action_checked('red')
        assert prog.view.is_action_checked('green')
        assert prog.view.is_action_checked('blue')
        assert prog.view.is_action_visible('red')
        assert prog.view.is_action_visible('green')
        assert not prog.view.is_action_visible('blue')

    def test_update_data_roi(self, init_prog_show_data):
        prog, qtbot, _ = init_prog_show_data
        create_one_roi(prog, qtbot)
        QtWidgets.QApplication.processEvents()

        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000) as blocker:
            prog.update_data()

    def test_update_data_crosshair(self, init_prog_show_data):
        prog, qtbot, _ = init_prog_show_data
        prog.view.get_action('crosshair').trigger()
        QtWidgets.QApplication.processEvents()

        with qtbot.waitSignal(prog.crosshair_dragged, timeout=1000) as blocker:
            prog.update_data()


class TestAxis:
    @pytest.mark.parametrize('position', ('left', 'bottom', 'right', 'top'))
    def test_axis_label(self, init_viewer2D, position):
        prog, qtbot = init_viewer2D
        UNITS= 'myunits'
        LABEL = 'mylabel'

        prog.view.set_axis_label(position, label=LABEL, units=UNITS)
        assert prog.view.get_axis_label(position) == (LABEL, UNITS)

    def test_get_axis_error(self, init_viewer2D):
        prog, qtbot = init_viewer2D

        with pytest.raises(KeyError):
            prog.view.get_axis_label('unvalid key')

    def test_scale_axis(self, init_viewer2D):
        prog, qtbot = init_viewer2D
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
    def test_actionhas(self, init_viewer2D, action):
        prog, qtbot = init_viewer2D
        assert prog.view.has_action(action)

    @pytest.mark.parametrize('color', ['red', 'green', 'blue'])
    def test_color_action(self, init_viewer2D, color):
        prog, qtbot = init_viewer2D
        data = init_data(3)
        prog.show_data(data)

        assert prog.view.data_displayer.get_image(color).isVisible()
        assert prog.view.is_action_checked(color)

        prog.view.get_action(color).trigger()

        assert not prog.view.is_action_checked(color)
        assert not prog.view.data_displayer.get_image(color).isVisible()

    def test_histo_action(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data(2)
        prog.show_data(data)

        prog.view.get_action('histo').trigger()

        assert prog.view.is_action_checked('histo')
        assert prog.view.histogrammer.get_histogram('red').isVisible()
        assert prog.view.histogrammer.get_histogram('green').isVisible()
        assert not prog.view.histogrammer.get_histogram('blue').isVisible()

    def test_histo_autolevel_action(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data(3)
        prog.show_data(data)

        # the 4.2.x_dev added the autotriggering of this autolevels on first display of data
        # prog.view.get_action('histo').trigger()
        #
        # assert prog.view.histogrammer.get_histogram('red').getLevels() == approx((0, 1.))
        # assert prog.view.histogrammer.get_histogram('green').getLevels() == approx((0, 1.))
        # assert prog.view.histogrammer.get_histogram('blue').getLevels() == approx((0, 1.))
        #
        # prog.view.get_action('autolevels').trigger()

        assert prog.view.histogrammer.get_histogram('red').getLevels() == approx((0, 2.9392557954529277))
        assert prog.view.histogrammer.get_histogram('green').getLevels() == approx((0., 24.0))
        assert prog.view.histogrammer.get_histogram('blue').getLevels() ==\
               approx((5.693320370703248e-09, 9.83017824174412))

    def test_autolevel_action(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        prog.view.get_action('autolevels').trigger()
        assert prog.view.histogrammer.autolevels
        assert prog.view.data_displayer.autolevels

        prog.view.get_action('autolevels').trigger()
        assert not prog.view.histogrammer.autolevels
        assert not prog.view.data_displayer.autolevels


class TestHistogrammer:
    @pytest.mark.parametrize('color', ['red', 'green', 'blue'])
    def test_get_histogram(self, init_viewer2D, color):
        prog, qtbot = init_viewer2D

        assert color in prog.view.histogrammer.get_histograms()
        assert prog.view.histogrammer.get_histogram(color) == prog.view.histogrammer.get_histograms()[color]

    def test_get_histogram_name_error(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        with pytest.raises(KeyError):
            prog.view.histogrammer.get_histogram('not a valid identifier')

    @pytest.mark.parametrize('histo', ['red', 'blue', 'green', 'all'])
    @pytest.mark.parametrize('gradient', ['blue', 'green', 'spread'])
    def test_setgradient(self, init_prog_show_data, histo, gradient):
        prog, qtbot, _ = init_prog_show_data
        prog.view.histogrammer.set_gradient(histo, gradient)


class TestROI:
    def test_roi_action(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()
        prog.show_data(data)
        create_one_roi(prog, qtbot, roitype='RectROI')

        assert prog.view.is_action_checked('roi')
        assert prog.view.roi_manager.roiwidget.isVisible()

    def test_add_roi(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()
        prog.show_data(data)

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='RectROI')
        assert roi_type == 'RectROI'
        assert index_roi == 0

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='EllipseROI')
        assert roi_type == 'EllipseROI'
        assert index_roi == 1

    def test_remove_roi(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()
        prog.show_data(data)

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='RectROI')

        prog.view.roi_manager.remove_roi_programmatically(index_roi)
        QtWidgets.QApplication.processEvents()

    def test_update_color_roi(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()
        prog.show_data(data)

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='RectROI')

        prog.view.roi_manager.settings.child('ROIs', ROIManager.roi_format(index_roi), 'Color').setValue('b')
        roi = prog.view.roi_manager.get_roi_from_index(index_roi)
        QtWidgets.QApplication.processEvents()
        assert roi.pen == mkPen('b')

    def test_data_from_roi(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()
        prog.show_data(data)

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='RectROI')
        roi.setPos((0, 0))

        assert prog.view.is_action_checked('roi')

        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000) as blocker:
            roi.setSize((data[0].T).shape)
            roi.setPos((0, 0))

        data_to_export: data_mod.DataToExport = blocker.args[0]
        assert len(data_to_export.get_data_from_dim('data1D')) != 0
        assert len(data_to_export.get_data_from_dim('data0D')) != 0

        assert f'Hlineout_{ROIManager.roi_format(index_roi)}' in data_to_export.get_names()
        assert f'Vlineout_{ROIManager.roi_format(index_roi)}' in \
               data_to_export.get_names('data1D')
        assert f'Integrated_{ROIManager.roi_format(index_roi)}' in \
               data_to_export.get_names('data0D')

        hlineout = data_to_export.get_data_from_name(f'Hlineout_{ROIManager.roi_format(index_roi)}')
        vlineout = data_to_export.get_data_from_name(f'Vlineout_{ROIManager.roi_format(index_roi)}')
        intlineout = data_to_export.get_data_from_name(f'Integrated_{ROIManager.roi_format(index_roi)}')

        assert np.any(hlineout.data[0] == approx(np.mean(data[0], 0)))
        assert np.any(vlineout.data[0] == approx(np.mean(data[0], 1)))
        assert np.any(intlineout.data[0] == approx(np.mean(data[0])))

    def test_data_from_roi_spread(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data(uniform=False)
        prog.show_data(data)

        index_roi, roi, roi_type = create_one_roi(prog, qtbot, roitype='RectROI')
        roi.setPos((0, 0))

        assert prog.view.is_action_checked('roi')
        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000) as blocker:
            roi.setSize((10, 10))
            roi.setPos((0, 0))

        data_to_export = blocker.args[0]
        assert len(data_to_export.get_data_from_dim('data1D')) != 0
        assert len(data_to_export.get_data_from_dim('data0D')) != 0

        assert f'Hlineout_{ROIManager.roi_format(index_roi)}' in data_to_export.get_names('data1D')
        assert f'Vlineout_{ROIManager.roi_format(index_roi)}' in data_to_export.get_names('data1D')
        assert f'Integrated_{ROIManager.roi_format(index_roi)}' in data_to_export.get_names('data0D')


    def test_show_roi(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        prog.show_roi(show=True, show_roi_widget=True)
        assert prog.is_action_checked('roi')
        assert prog.view.roi_manager.roiwidget.isVisible()

        prog.show_roi(show=True, show_roi_widget=False)
        assert prog.is_action_checked('roi')
        assert not prog.view.roi_manager.roiwidget.isVisible()

        prog.show_roi(show=False, show_roi_widget=False)
        assert not prog.is_action_checked('roi')
        assert not prog.view.roi_manager.roiwidget.isVisible()

        prog.show_roi(show=False, show_roi_widget=True)
        assert not prog.is_action_checked('roi')
        assert prog.view.roi_manager.roiwidget.isVisible()


class TestIsocurve:

    def test_isocurve_action(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()
        prog.show_data(data)

        prog.view.get_action('isocurve').trigger()

        assert prog.view.is_action_checked('isocurve')
        assert prog.view.is_action_checked('histo')

    @pytest.mark.parametrize('histo', ['blue', 'green', 'red'])
    @pytest.mark.parametrize('im_source', ['blue', 'green', 'red'])
    def test_isocurve_parent(self, init_viewer2D, im_source, histo):
        prog, qtbot = init_viewer2D
        prog.view.isocurver.update_image_source(prog.view.data_displayer.get_image(im_source))
        prog.view.isocurver.update_histogram_parent(prog.view.histogrammer.get_histogram(histo))

    def test_change_isoline(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()
        prog.show_data(data)

        ISOLEVEL = 0.1

        prog.view.get_action('isocurve').trigger()
        prog.view.isocurver._isoLine.setValue(ISOLEVEL)
        prog.view.isocurver._isoLine.sigDragged.emit(prog.view.isocurver._isoLine)
        QtWidgets.QApplication.processEvents()
        assert prog.view.isocurver._isocurve_item.level == ISOLEVEL


class TestAspectRatio:
    def test_aspect_ratio_action(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()
        prog.show_data(data)

        assert prog.view.is_action_checked('aspect_ratio')
        assert prog.view.image_widget.plotitem.vb.state['aspectLocked']

        prog.view.get_action('aspect_ratio').trigger()
        assert not prog.view.is_action_checked('aspect_ratio')
        assert not prog.view.image_widget.plotitem.vb.state['aspectLocked']

        prog.view.get_action('aspect_ratio').trigger()
        assert prog.view.is_action_checked('aspect_ratio')
        assert prog.view.image_widget.plotitem.vb.state['aspectLocked']


class TestCrosshair:
    def test_crosshair_action(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()
        prog.show_data(data)
        assert not prog.view.is_action_visible('position')

        prog.view.get_action('crosshair').trigger()
        QtWidgets.QApplication.processEvents()

        assert prog.view.is_action_checked('crosshair')
        assert prog.view.is_action_visible('position')
        assert prog.view.crosshair.isVisible()

        prog.view.get_action('crosshair').trigger()
        QtWidgets.QApplication.processEvents()

        prog.view.get_action('roi').trigger()  # will keep lineout_widgets visible so we can check
        # if crosshair lineouts are still visible
        QtWidgets.QApplication.processEvents()

        assert not prog.view.is_action_checked('crosshair')
        assert not prog.view.is_action_visible('position')
        assert not prog.view.crosshair.isVisible()

    def test_setpos_crosshair(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()
        XCROSS = 24
        YCROSS = 75

        with qtbot.waitSignal(prog.view.get_crosshair_signal(), timeout=1000) as blocker:
            prog.view.get_action('crosshair').trigger()

        with qtbot.waitSignal(prog.crosshair_dragged, timeout=1000) as blocker:
            prog.view.crosshair.set_crosshair_position(XCROSS, YCROSS)

        assert blocker.args[0] == approx(XCROSS)
        assert blocker.args[1] == approx(YCROSS)

    def test_crosshair_doubleclicked(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        prog.view.get_action('crosshair').trigger()
        with qtbot.waitSignal(prog.sig_double_clicked, timeout=10000) as blocker:
            prog.view.get_double_clicked().emit(10.5, 20.9)

        assert prog.view.get_crosshair_position()[0] == approx(10.5)
        assert prog.view.get_crosshair_position()[1] == approx(20.9)


class TestRoiSelect:
    def test_ROIselect_action(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        SIZE = [20, 35]
        POS = [45, 123]
        prog.view.get_action('ROIselect').trigger()
        with qtbot.waitSignal(prog.roi_select_signal, timeout=1000) as blocker:
            prog.view.ROIselect.setSize(SIZE)

        with qtbot.waitSignal(prog.roi_select_signal, timeout=1000) as blocker:
            prog.view.ROIselect.setPos(POS)

        assert isinstance(blocker.args[0], RoiInfo)
        assert blocker.args[0].origin == Point(POS[-1::-1])
        assert blocker.args[0].size == Point(SIZE[-1::-1])


class TestImageDisplayer:
    def test_get_image(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()

        with pytest.raises(KeyError):
            prog.view.data_displayer.get_image('not a valid image name')

    def test_update_display_items(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()

        data = init_data(uniform=False)
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()


class TestModifyImages:
    def test_FlipUD_action(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()

        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000) as blocker:
            prog.show_data(data)
        assert np.any(prog._datas[0] == approx(data[0]))

        prog.view.get_action('flip_ud').trigger()
        QtWidgets.QApplication.processEvents()
        assert np.any(prog._datas[0] == approx(np.flipud(data[0])))

    def test_FlipLR_action(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()
        prog.show_data(data)

        with qtbot.waitSignal(prog.data_to_export_signal, timeout=1000) as blocker:
            prog.show_data(data)

        prog.view.get_action('flip_lr').trigger()
        QtWidgets.QApplication.processEvents()
        assert np.any(prog._datas[0] == approx(np.fliplr(data[0])))

        prog.view.get_action('flip_lr').trigger()
        QtWidgets.QApplication.processEvents()
        assert np.any(prog._datas[0] == approx(data[0]))

    def test_rotate_action(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        data = init_data()
        prog.show_data(data)
        QtWidgets.QApplication.processEvents()
        prog.view.get_action('rotate').trigger()
        QtWidgets.QApplication.processEvents()
        assert np.any(prog._datas[0] == approx(np.flipud(np.transpose(data[0]))))


class TestMiscellanous:
    def test_double_clicked(self, init_viewer2D):
        prog, qtbot = init_viewer2D
        with qtbot.waitSignal(prog.sig_double_clicked, timeout=10000) as blocker:
            prog.view.get_double_clicked().emit(10.5, 20.9)

        assert blocker.args[0] == approx(10.5)
        assert blocker.args[1] == approx(20.9)
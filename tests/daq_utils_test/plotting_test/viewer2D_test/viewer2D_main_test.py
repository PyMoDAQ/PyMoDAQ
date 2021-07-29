from PyQt5 import QtWidgets
from pymodaq.daq_utils.plotting.viewer2D import Viewer2D
from pymodaq.daq_utils.exceptions import ExpectedError, Expected_1, Expected_2

import pytest
import numpy as np


class TestViewer2D:
    def test_init(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer2D()

        assert isinstance(prog, Viewer2D)

        qtbot.addWidget(Form)

    @pytest.mark.skip(reason="Test not implemented")
    def test_remove_ROI(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_add_ROI(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_crosshairChanged(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_crosshairClicked(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_double_clicked(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_ini_plot(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_lock_aspect_ratio(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_move_left_splitter(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_move_right_splitter(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_restore_state(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_roi_changed(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_update_roi(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_roi_clicked(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_scale_axis(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_unscale_axis(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_selected_region_changed(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_set_autolevels(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_set_scaling_axes(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_transform_image(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_set_image_transform(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_set_visible_items(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_setImage(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_setImageTemp(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_mapfromview(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_setObjectName(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_show_hide_histogram(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_show_hide_iso(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_show_lineouts(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_show_ROI_select(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_update_image(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_update_selection_area_visibility(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_update_crosshair_data(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_updateIsocurve(self, qtbot):
        pass

    def test_x_axis(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer2D()

        prog.x_axis_scaled = 'x_axis_scaled'

        assert prog.x_axis == 'x_axis_scaled'

        qtbot.addWidget(Form)

    def test_x_axis_setter(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer2D()

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

        qtbot.addWidget(Form)

    def test_set_axis_label(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer2D()

        prog.set_axis_label()

        scaled_xaxis = prog.scaling_options['scaled_xaxis']
        assert scaled_xaxis['orientation'] == 'bottom'
        assert scaled_xaxis['label'] == 'x axis'
        assert scaled_xaxis['units'] == 'pxls'

        qtbot.addWidget(Form)
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_y_axis(self, qtbot):
        pass

    @pytest.mark.skip(reason="Test not implemented")
    def test_y_axis_setter(self, qtbot):
        pass

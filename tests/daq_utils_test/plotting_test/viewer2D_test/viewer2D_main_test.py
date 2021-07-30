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

    def test_crosshairClicked(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer2D()

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

        prog.isdata["blue"] = True
        prog.isdata["green"] = True
        prog.isdata["red"] = True
        prog.isdata["spread"] = True

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

        qtbot.addWidget(Form)

    def test_double_clicked(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer2D()

        prog.double_clicked(posx=10, posy=20)

        assert prog.ui.crosshair.vLine.value() == 10
        assert prog.ui.crosshair.hLine.value() == 20

        qtbot.addWidget(Form)

    def test_ini_plot(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer2D()

        for ind in range(10):
            prog.data_integrated_plot['plot_{:02d}'.format(ind)] = None

        prog.ini_plot()

        for key in prog.data_integrated_plot.keys():
            assert np.array_equal(prog.data_integrated_plot[key], np.zeros((2, 1)))

        qtbot.addWidget(Form)

    def test_lock_aspect_ratio(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer2D()

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

        qtbot.addWidget(Form)

    @pytest.mark.skip(reason="Access violation problem")
    def test_move_left_splitter(self, qtbot):
        pass

    @pytest.mark.skip(reason="Access violation problem")
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

    def test_scale_axis(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer2D()

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

        qtbot.addWidget(Form)

    def test_unscale_axis(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer2D()

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

        qtbot.addWidget(Form)

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

    def test_setObjectName(self, qtbot):
        Form = QtWidgets.QWidget()
        Form.setObjectName('Form')
        prog = Viewer2D(Form)

        prog.setObjectName('test')

        assert prog.parent.objectName() == 'test'

        qtbot.addWidget(Form)

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

    def test_updateIsocurve(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer2D()

        prog.ui.isoLine.setValue(5)

        prog.updateIsocurve()

        assert prog.ui.iso.level == 5

        qtbot.addWidget(Form)

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

        axis_settings = dict(orientation='left', label='y axis', units='nm')

        prog.set_axis_label(axis_settings=axis_settings)

        scaled_xaxis = prog.scaling_options['scaled_yaxis']
        assert scaled_xaxis['orientation'] == 'left'
        assert scaled_xaxis['label'] == 'y axis'
        assert scaled_xaxis['units'] == 'nm'

        qtbot.addWidget(Form)

    def test_y_axis(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer2D()

        prog.y_axis_scaled = 'y_axis_scaled'

        assert prog.y_axis == 'y_axis_scaled'

        qtbot.addWidget(Form)

    def test_y_axis_setter(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer2D()

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

        qtbot.addWidget(Form)

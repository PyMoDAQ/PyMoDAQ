from PyQt5 import QtWidgets, QtCore
import numpy as np
import pytest
from unittest import mock


from pymodaq.daq_utils.plotting.viewer1D.viewer1D_main import Viewer1D
from pymodaq.daq_utils.exceptions import ExpectedError


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
from PyQt5 import QtWidgets, QtCore
import numpy as np
import pytest
from unittest import mock

from pymodaq.daq_utils.daq_utils import gauss1D
from pymodaq.daq_utils.plotting.viewer0D.viewer0D_main import Viewer0D
from pymodaq.daq_utils.exceptions import ExpectedError


class TestViewer0D:
    def test_init(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer0D(Form)
        qtbot.addWidget(prog)
        assert isinstance(prog, Viewer0D)
        assert prog.parent == Form
        assert prog.title == 'viewer0D'
        
        prog = Viewer0D(None)
        assert isinstance(prog.parent, QtWidgets.QWidget)

    def test_clear_pb(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer0D(Form)

        x = np.linspace(0, 200, 201)
        y1 = gauss1D(x, 75, 25)
        y2 = gauss1D(x, 120, 50, 2)

        for ind, data in enumerate(y1):
            prog.show_data([[data], [y2[ind]]])
            QtWidgets.QApplication.processEvents()

        qtbot.addWidget(prog)
        for data in prog.datas:
            assert data.size != 0
        assert prog.x_axis.size != 0

        qtbot.mouseClick(prog.ui.clear_pb, QtCore.Qt.LeftButton)

        for data in prog.datas:
            assert data.size == 0
        assert prog.x_axis.size == 0

    def test_Nhistory_sb(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer0D(Form)

        qtbot.addWidget(prog)
        assert prog.ui.Nhistory_sb.value() == 200
        prog.ui.Nhistory_sb.clear()
        qtbot.keyClicks(prog.ui.Nhistory_sb, '300')
        assert prog.ui.Nhistory_sb.value() == 300

    def test_show_datalist_pb(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer0D(Form)

        Form.show()

        qtbot.addWidget(prog)
        qtbot.mouseClick(prog.ui.show_datalist_pb, QtCore.Qt.LeftButton)
        assert prog.ui.values_list.isVisible()
        qtbot.mouseClick(prog.ui.show_datalist_pb, QtCore.Qt.LeftButton)
        assert not prog.ui.values_list.isVisible()
        
    def test_clear_data(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer0D(Form)

        x = np.linspace(0, 200, 201)
        y1 = gauss1D(x, 75, 25)
        y2 = gauss1D(x, 120, 50, 2)
        for ind, data in enumerate(y1):
            prog.show_data([[data], [y2[ind]]])
            QtWidgets.QApplication.processEvents()
        
        for data in prog.datas:
            assert len(data) > 0
        assert len(prog.x_axis) > 0

        prog.clear_data()

        for data in prog.datas:
            assert data.size == 0
        assert prog.x_axis.size == 0

        qtbot.addWidget(prog)
        
    @mock.patch('pymodaq.daq_utils.plotting.viewer0D.viewer0D_main.logger.exception')
    @mock.patch('pymodaq.daq_utils.plotting.viewer0D.viewer0D_main.Viewer0D.update_Graph1D')
    def test_show_data(self, mock_update, mock_logger, qtbot):
        mock_update.side_effect = [None, Exception]
        mock_logger.side_effect = [ExpectedError]
        Form = QtWidgets.QWidget()
        prog = Viewer0D(Form)

        x = np.linspace(0, 200, 2)
        y1 = gauss1D(x, 75, 25)
        y2 = gauss1D(x, 120, 50, 2)
        Form.show()
        with pytest.raises(ExpectedError):
            for ind, data in enumerate(y1):
                prog.show_data([[data], [y2[ind]]])
                QtWidgets.QApplication.processEvents()
        
        qtbot.addWidget(prog)

    def test_show_data_list(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer0D(Form)
        Form.show()

        prog.ui.show_datalist_pb.setChecked(True)
        assert not prog.ui.values_list.isVisible() == prog.ui.show_datalist_pb.isChecked()
        prog.show_data_list(None)
        assert prog.ui.values_list.isVisible() == prog.ui.show_datalist_pb.isChecked()
        
        qtbot.addWidget(prog)
        
    def test_show_data_temp(self, qtbot):       
        Form = QtWidgets.QWidget()
        prog = Viewer0D(Form)
        
        assert not prog.show_data_temp(None)

        qtbot.addWidget(prog)
        
    # def test_update_Graph1D(self, qtbot):
    #     Form = QtWidgets.QWidget()
    #     prog = Viewer0D(Form)
    #
    #     qtbot.addWidget(prog)
        
    def test_update_channels(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer0D(Form)

        x = np.linspace(0, 200, 2)
        y1 = gauss1D(x, 75, 25)
        y2 = gauss1D(x, 120, 50, 2)
        for ind, data in enumerate(y1):
            prog.show_data([[data], [y2[ind]]])
            QtWidgets.QApplication.processEvents()
            
        assert prog.plot_channels
        prog.update_channels()
        assert prog.plot_channels is None

        qtbot.addWidget(prog)
        
    def test_update_labels(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer0D(Form)

        x = np.linspace(0, 200, 2)
        y1 = gauss1D(x, 75, 25)
        y2 = gauss1D(x, 120, 50, 2)
        
        for ind, data in enumerate(y1):
            prog.show_data([[data], [y2[ind]]])
            QtWidgets.QApplication.processEvents()

        assert len(prog.plot_channels) == 2
        labels = ['axis_1', 'axis_2']
        prog.labels = labels
        for item, label in zip(prog.legend.items, labels):
            assert item[1].text == label

        qtbot.addWidget(prog)
        
    def test_update_status(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer0D(Form)
        
        assert not prog.update_status(txt='test')
        
        qtbot.addWidget(prog)
        
    def test_update_x_axis(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer0D(Form)
        
        Nhistory = 50
        prog.update_x_axis(Nhistory=Nhistory)
        
        assert prog.Nsamples == Nhistory
        assert np.array_equal(prog.x_axis, np.linspace(0, Nhistory - 1, Nhistory))

        qtbot.addWidget(prog)
    
    def test_labels(self, qtbot):
        Form = QtWidgets.QWidget()
        prog = Viewer0D(Form)

        assert not prog.labels
        prog.labels = 'test_label'
        assert prog.labels == 'test_label'
        
        qtbot.addWidget(prog)

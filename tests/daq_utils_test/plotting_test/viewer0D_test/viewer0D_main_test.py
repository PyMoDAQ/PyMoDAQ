from qtpy import QtWidgets, QtCore
import numpy as np
import pytest
from unittest import mock

from pymodaq.daq_utils.daq_utils import gauss1D
from pymodaq.daq_utils.plotting.viewer0D.viewer0D_main import Viewer0D
from pymodaq.daq_utils.exceptions import ExpectedError
from collections import OrderedDict


@pytest.fixture
def init_prog(qtbot):
    form = QtWidgets.QWidget()
    prog = Viewer0D(form)
    form.show()
    qtbot.addWidget(form)
    return prog, qtbot

@pytest.mark.skip
class TestViewer0D:
    def test_init(self, init_prog):
        prog, qtbot = init_prog
        assert isinstance(prog, Viewer0D)
        assert isinstance(prog.parent, QtWidgets.QWidget)
        assert prog.title == 'viewer0D'
        
        prog = Viewer0D(None)
        assert isinstance(prog.parent, QtWidgets.QWidget)

    @pytest.mark.skip  # causes error on pytest on github actions ??
    # File "/opt/hostedtoolcache/Python/3.8.12/x64/lib/python3.8/site-packages/pyqtgraph/graphicsItems/AxisItem.py",
    # line 1126 in generateDrawSpecs
    def test_clear_pb(self, init_prog):
        prog, qtbot = init_prog

        x = np.linspace(0, 200, 201)
        y1 = gauss1D(x, 75, 25)
        y2 = gauss1D(x, 120, 50, 2)

        for ind, data in enumerate(y1):
            prog.show_data([[data], [y2[ind]]])
            QtWidgets.QApplication.processEvents()

        for data in prog.datas:
            assert data.size != 0
        assert prog.x_axis.size != 0

        qtbot.mouseClick(prog.ui.clear_pb, QtCore.Qt.LeftButton)

        for data in prog.datas:
            assert data.size == 0
        assert prog.x_axis.size == 0

    def test_Nhistory_sb(self, init_prog):
        prog, qtbot = init_prog

        assert prog.ui.Nhistory_sb.value() == 200
        prog.ui.Nhistory_sb.clear()
        qtbot.keyClicks(prog.ui.Nhistory_sb, '300')
        assert prog.ui.Nhistory_sb.value() == 300

    def test_show_datalist_pb(self, init_prog):
        prog, qtbot = init_prog

        prog.parent.show()

        qtbot.mouseClick(prog.ui.show_datalist_pb, QtCore.Qt.LeftButton)
        assert prog.ui.values_list.isVisible()
        qtbot.mouseClick(prog.ui.show_datalist_pb, QtCore.Qt.LeftButton)
        assert not prog.ui.values_list.isVisible()
        
    def test_clear_data(self, init_prog):
        prog, qtbot = init_prog

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

    @mock.patch('pymodaq.daq_utils.plotting.viewer0D.viewer0D_main.logger.exception')
    @mock.patch('pymodaq.daq_utils.plotting.viewer0D.viewer0D_main.Viewer0D.update_Graph1D')
    def test_show_data(self, mock_update, mock_logger, init_prog):
        mock_update.side_effect = [None, Exception]
        mock_logger.side_effect = [ExpectedError]

        prog, qtbot = init_prog

        x = np.linspace(0, 200, 2)
        y1 = gauss1D(x, 75, 25)
        y2 = gauss1D(x, 120, 50, 2)
        prog.parent.show()
        with pytest.raises(ExpectedError):
            for ind, data in enumerate(y1):
                prog.show_data([[data], [y2[ind]]])
                QtWidgets.QApplication.processEvents()

    def test_show_data_list(self, init_prog):
        prog, qtbot = init_prog
        prog.parent.show()

        prog.ui.show_datalist_pb.setChecked(True)
        assert not prog.ui.values_list.isVisible() == prog.ui.show_datalist_pb.isChecked()
        prog.show_data_list(None)
        assert prog.ui.values_list.isVisible() == prog.ui.show_datalist_pb.isChecked()
        
    def test_show_data_temp(self, init_prog):
        prog, qtbot = init_prog
        
        assert not prog.show_data_temp(None)

    @mock.patch('pymodaq.daq_utils.plotting.viewer0D.viewer0D_main.logger.exception')
    def test_update_Graph1D(self, mock_except, init_prog):
        mock_except.side_effect = [ExpectedError]

        prog, qtbot = init_prog

        datas = np.linspace(np.linspace(1, 10, 10), np.linspace(11, 20, 10), 2)

        prog.datas = datas
        prog.Nsamples = 10
        prog.x_axis = np.linspace(1, 19, 19)

        prog.plot_channels = []
        for i in range(2):
            channel = prog.ui.Graph1D.plot(y=np.array([]))
            channel.setPen(1)
            prog.plot_channels.append(channel)

        prog.data_to_export = OrderedDict(data0D={})

        prog.update_Graph1D(datas)

        assert np.array_equal(prog.plot_channels[0].getData(), np.array((np.array(prog.x_axis),
                                                          np.append(datas[0], datas[0])[1:])))
        assert np.array_equal(prog.plot_channels[1].getData(), np.array((np.array(prog.x_axis),
                                                          np.append(datas[1], datas[1])[1:])))

        assert prog.data_to_export['data0D']['CH000']
        assert prog.data_to_export['data0D']['CH001']

        data_tot = np.array([np.append(datas[0], datas[0])[1:], np.append(datas[1], datas[1])[1:]])
        assert np.array_equal(np.array(prog.datas), data_tot)

        with pytest.raises(ExpectedError):
            prog.update_Graph1D(None)
        
    def test_update_channels(self, init_prog):
        prog, qtbot = init_prog

        x = np.linspace(0, 200, 2)
        y1 = gauss1D(x, 75, 25)
        y2 = gauss1D(x, 120, 50, 2)
        for ind, data in enumerate(y1):
            prog.show_data([[data], [y2[ind]]])
            QtWidgets.QApplication.processEvents()
            
        assert prog.plot_channels
        prog.update_channels()
        assert prog.plot_channels is None
        
    def test_update_labels(self, init_prog):
        prog, qtbot = init_prog

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
        
    def test_update_status(self, init_prog):
        prog, qtbot = init_prog
        
        assert not prog.update_status(txt='test')
        
    def test_update_x_axis(self, init_prog):
        prog, qtbot = init_prog
        
        Nhistory = 50
        prog.update_x_axis(Nhistory=Nhistory)
        
        assert prog.Nsamples == Nhistory
        assert np.array_equal(prog.x_axis, np.linspace(0, Nhistory - 1, Nhistory))

    def test_labels(self, init_prog):
        prog, qtbot = init_prog

        assert not prog.labels
        prog.labels = 'test_label'
        assert prog.labels == 'test_label'

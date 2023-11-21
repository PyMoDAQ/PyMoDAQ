import os
from collections import OrderedDict
import numpy as np

from qtpy import QtWidgets, QtCore
import pytest
from pytest import fixture, approx

from pymodaq.control_modules import daq_viewer as daqvm
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.control_modules.utils import ControlModule
from pymodaq.utils.gui_utils.dock import DockArea
from pymodaq.control_modules.utils import DET_TYPES, get_viewer_plugins, DAQTypesEnum
from pymodaq.utils.conftests import qtbotskip, main_modules_skip
from pymodaq.utils.config import Config
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.parameter import Parameter
from pymodaq.utils.h5modules.browsing import H5BrowserUtil

config = Config()
config_viewer = daqvm.config
config_viewer['viewer', 'viewer_in_thread'] = True


@fixture
def init_qt(qtbot):
    return qtbot


@fixture
def ini_daq_viewer_without_ui(init_qt):
    qtbot = init_qt
    prog = daqvm.DAQ_Viewer()
    yield prog, qtbot
    prog.quit_fun()
    QtWidgets.QApplication.processEvents()


@fixture
def ini_daq_viewer_ui(init_qt):
    qtbot = init_qt
    dockarea = DockArea()
    qtbot.addWidget(dockarea)
    prog = daqvm.DAQ_Viewer(dockarea)
    yield prog, qtbot, dockarea
    prog.quit_fun()
    QtWidgets.QApplication.processEvents()


class TestMethods:
    def test_overriden(self):
        assert ControlModule.stop_grab != DAQ_Viewer.stop_grab
        assert ControlModule.grab != DAQ_Viewer.grab
        assert ControlModule.quit_fun != DAQ_Viewer.quit_fun
        assert ControlModule.init_hardware != DAQ_Viewer.init_hardware


class TestWithoutUI:
    def test_instanciation(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui

        assert prog.viewers is None
        assert prog.viewer_docks is None

    def test_daq_type_detector(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui
        assert prog.daq_types == DAQTypesEnum.names()
        assert prog.daq_type == config('viewer', 'daq_type')
        assert prog.detectors == [det_dict['name'] for det_dict in DET_TYPES[prog.daq_type.name]]
        assert prog.detector == prog.detectors[0]


    @pytest.mark.parametrize("daq_type", DAQTypesEnum.names())
    def test_daq_type_changed(self, ini_daq_viewer_without_ui, daq_type):
        prog, qtbot = ini_daq_viewer_without_ui
        prog.daq_type = daq_type
        assert prog.detectors == [det_dict['name'] for det_dict in DET_TYPES[daq_type]]

    @pytest.mark.parametrize("det", [det_dict['name'] for det_dict in DET_TYPES['DAQ0D']])
    def test_detector_changed(self, ini_daq_viewer_without_ui, det):
        prog, qtbot = ini_daq_viewer_without_ui
        prog.daq_type = 'DAQ0D'
        prog.detector = det
        det_params, _class = get_viewer_plugins(prog.daq_type.name, prog.detector)
        assert putils.iter_children(prog.settings.child('detector_settings'), []) == \
            putils.iter_children(det_params, [])

@pytest.mark.skip
class TestWithUI:

    @pytest.mark.parametrize("daq_type", DAQTypesEnum.names())
    def test_daq_type_changed(self, ini_daq_viewer_ui, daq_type):
        prog, qtbot, dockarea = ini_daq_viewer_ui
        prog.daq_type = daq_type
        assert prog.detectors == [det_dict['name'] for det_dict in DET_TYPES[daq_type]]
        assert len(prog.viewers) == 1
        assert prog.viewers[0].viewer_type == f'Data{daq_type[3:]}'

    def test_process_commands(self, ini_daq_viewer_ui):
        prog, qtbot, dockarea = ini_daq_viewer_ui

        with qtbot.waitSignal(prog.ui.command_sig) as blocker:
            qtbot.mouseClick(prog.ui._ini_det_pb, QtCore.Qt.LeftButton)
        assert blocker.args[0].command == 'init'
        with qtbot.waitSignal(prog.ui.command_sig) as blocker:
            prog.ui.get_action('stop').trigger()
        assert blocker.args[0].command == 'stop'


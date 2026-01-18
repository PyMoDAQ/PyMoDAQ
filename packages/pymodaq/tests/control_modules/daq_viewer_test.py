import os
from collections import OrderedDict
import numpy as np

from qtpy import QtWidgets, QtCore
import pytest
from pytest import fixture, approx
import qt_themes
from pymodaq.control_modules.daq_viewer_ui.viewer_selector import SelectedModule
from pymodaq_gui.utils.dock import DockArea

from pymodaq.control_modules import daq_viewer as daqvm
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.control_modules.utils import ControlModule
from pymodaq.control_modules.instruments import DET_TYPES, get_viewer_plugins, DAQTypesEnum
from pymodaq.utils.conftests import qtbotskip, main_modules_skip
from pymodaq.utils.config import Config
from pymodaq_utils.config import Config as ConfigUtils
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.parameter import Parameter
from pymodaq_data.h5modules.browsing import H5BrowserUtil

config = Config()
config_utils = ConfigUtils()
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
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    qt_themes.set_theme(theme=config_utils('style', 'theme')[0],
                        style=config_utils('style', 'style')[0])
    prog = daqvm.DAQ_Viewer(widget, 'test')
    yield prog, qtbot, widget
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


    @pytest.mark.parametrize("det", [det_dict['name'] for det_dict in DET_TYPES['DAQ0D']])
    def test_detector_changed(self, ini_daq_viewer_without_ui, det):
        prog, qtbot = ini_daq_viewer_without_ui
        daq_type = 'DAQ0D'
        prog.detector = SelectedModule(DAQTypesEnum[daq_type], det)
        det_params, _class = get_viewer_plugins(prog.detector.daq_type.name, prog.detector.module_name)
        assert putils.iter_children(prog.settings.child('detector_settings'), []) == \
            putils.iter_children(det_params, [])

#@pytest.mark.skip
class TestWithUI:

    @pytest.mark.parametrize("daq_type", DAQTypesEnum.names())
    def test_daq_type_changed(self, ini_daq_viewer_ui, daq_type):
        prog, qtbot, dockarea = ini_daq_viewer_ui
        with qtbot.waitSignal(prog.ui.command_sig) as blocker:
            prog.detector = SelectedModule(DAQTypesEnum[daq_type], 'Mock')
        assert len(prog.viewers) == 1
        assert prog.viewers[0].viewer_type == f'Data{daq_type[3:]}'


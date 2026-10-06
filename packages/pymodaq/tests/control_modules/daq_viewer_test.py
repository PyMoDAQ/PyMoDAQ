import os
from collections import OrderedDict
import numpy as np

from qtpy import QtWidgets, QtCore
import pytest
from pytest import fixture, approx
import qt_themes
from pymodaq.control_modules.daq_viewer_ui.viewer_selector import SelectedModule
from pymodaq.utils.gui_utils.loader_utils import create_load_daq_viewer
from pymodaq_gui.utils.dock import DockArea

from pymodaq.control_modules import daq_viewer as daqvm
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.control_modules.viewer_utility_classes import HW_SETTINGS_KEY as DETECTOR_SETTINGS_KEY
from pymodaq.control_modules.utils import ControlModule
from pymodaq.control_modules.instruments import DET_TYPES, get_viewer_plugins
from pymodaq.control_modules.enums import DAQTypesEnum
from pymodaq.utils.conftests import qtbotskip, main_modules_skip
from pymodaq.utils.config import GlobalConfig

from pymodaq_gui.parameter import utils as putils


config = GlobalConfig()

config_viewer = config['pymodaq', 'viewer']
config_viewer['viewer_in_thread'] = True


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
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0],
                        style=config('gui', 'style', 'style')[0])
    shared_ui, prog = create_load_daq_viewer()
    shared_ui.show()

    qtbot.addWidget(shared_ui.mainwindow)


    yield prog, qtbot, shared_ui.mainwindow
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
        assert putils.iter_children(prog.settings.child(DETECTOR_SETTINGS_KEY), []) == \
            putils.iter_children(det_params, [])

    def test_main_settings_recall_detector(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui
        prog.detector = SelectedModule(DAQTypesEnum['DAQ1D'], 'Mock')
        assert prog.settings['main_settings', 'DAQ_type'] == 'DAQ1D'
        assert prog.settings['main_settings', 'detector_type'] == 'Mock'

    def test_removed_main_settings(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui
        main_settings = prog.settings.child('main_settings')
        assert 'overshoot' not in main_settings.names
        assert 'axes' not in main_settings.names


#@pytest.mark.skip
class TestWithUI:

    @pytest.mark.parametrize("daq_type", DAQTypesEnum.names())
    def test_daq_type_changed(self, ini_daq_viewer_ui, daq_type):
        prog, qtbot, dockarea = ini_daq_viewer_ui
        with qtbot.waitSignal(prog.ui.command_sig) as blocker:
            prog.daq_type = daq_type
        assert len(prog.viewers) == 1
        assert prog.viewers[0].viewer_type == f'Data{daq_type[3:]}'


    @pytest.mark.parametrize("daq_type", DAQTypesEnum.names())
    def test_detector_changed(self, ini_daq_viewer_ui, daq_type):
        prog, qtbot, dockarea = ini_daq_viewer_ui
        with qtbot.waitSignal(prog.ui.command_sig) as blocker:
            prog.detector = SelectedModule(DAQTypesEnum[daq_type], 'Mock')
        assert len(prog.viewers) == 1
        assert prog.viewers[0].viewer_type == f'Data{daq_type[3:]}'


    @pytest.mark.parametrize("daq_type", DAQTypesEnum.names())
    def test_detector_name_changed(self, ini_daq_viewer_ui, daq_type):
        prog, qtbot, dockarea = ini_daq_viewer_ui
        with qtbot.waitSignal(prog.ui.command_sig) as blocker:
            prog.daq_type = daq_type
        with qtbot.waitSignal(prog.ui.command_sig) as blocker:
            prog.detector = 'Mock'
        assert len(prog.viewers) == 1
        assert prog.viewers[0].viewer_type == f'Data{daq_type[3:]}'

def test_viewers_roi_select_and_crosshair_forwarding(ini_daq_viewer_ui):
    """ROIselect and crosshair of each viewer are forwarded to the plugin with the right viewer index"""
    from pymodaq_gui.plotting.data_viewers.viewer2D import Viewer2D
    from pymodaq_gui.plotting.items.roi import RoiInfo, RectROI
    from pymodaq.control_modules.thread_commands import ControlToHardwareViewer

    prog, qtbot, win = ini_daq_viewer_ui
    viewers = [Viewer2D(QtWidgets.QWidget()) for _ in range(3)]
    commands = []
    prog.command_hardware.connect(commands.append)

    prog.viewers = viewers[:2]
    roi_info = RoiInfo((1., 2.), (3., 4.), roi_class=RectROI)
    viewers[1].roi_select_signal.emit(roi_info)
    viewers[0].crosshair_dragged.emit(5., 6.)

    roi_cmds = [cmd for cmd in commands if cmd.command == ControlToHardwareViewer.ROI_SELECT]
    cross_cmds = [cmd for cmd in commands if cmd.command == ControlToHardwareViewer.CROSSHAIR]
    assert roi_cmds[-1].attribute == dict(roi_info=roi_info, ind_viewer=1)
    assert cross_cmds[-1].attribute == dict(crosshair_info=(5., 6.), ind_viewer=0)

    # after a change of viewers, the old ones are no more forwarded
    prog.viewers = viewers[2:]
    commands.clear()
    viewers[1].roi_select_signal.emit(roi_info)
    viewers[0].crosshair_dragged.emit(5., 6.)
    assert len(commands) == 0
    viewers[2].crosshair_dragged.emit(7., 8.)
    assert commands[-1].attribute == dict(crosshair_info=(7., 8.), ind_viewer=0)

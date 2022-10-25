import os
from collections import OrderedDict
import numpy as np

from qtpy import QtWidgets, QtCore
import pytest
from pytest import fixture, approx

from pymodaq.control_modules import daq_viewer as daqvm
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.control_modules.utils import ControlModule
from pymodaq.daq_utils.gui_utils.dock import DockArea
from pymodaq.control_modules.utils import DAQ_TYPES, DET_TYPES, get_viewer_plugins
from pymodaq.daq_utils.conftests import qtbotskip, main_modules_skip
from pymodaq.daq_utils.config import Config
from pymodaq.daq_utils.parameter import utils as putils
from pymodaq.daq_utils.parameter import Parameter
from pymodaq.daq_utils.h5modules import H5BrowserUtil

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
    return prog, qtbot


@fixture
def ini_daq_viewer_ui(init_qt):
    qtbot = init_qt
    dockarea = DockArea()
    qtbot.addWidget(dockarea)
    prog = daqvm.DAQ_Viewer(dockarea)
    return prog, qtbot, dockarea


class TestMethods:
    def test_overriden(self):
        assert ControlModule.stop_grab != DAQ_Viewer.stop_grab
        assert ControlModule.grab != DAQ_Viewer.grab
        assert ControlModule.quit_fun != DAQ_Viewer.quit_fun
        assert ControlModule.init_hardware != DAQ_Viewer.init_hardware
        assert ControlModule.init_hardware_ui != DAQ_Viewer.init_hardware_ui



class TestWithoutUI:
    def test_instanciation(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui

        assert prog.viewers is None
        assert prog.viewer_docks is None

        prog.quit_fun()

    def test_daq_type_detector(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui
        assert prog.daq_types == DAQ_TYPES
        assert prog.daq_type == config('viewer', 'daq_type')
        assert prog.detectors == [det_dict['name'] for det_dict in DET_TYPES[prog.daq_type]]
        assert prog.detector == prog.detectors[0]

    @pytest.mark.parametrize("daq_type", DAQ_TYPES)
    def test_daq_type_changed(self, ini_daq_viewer_without_ui, daq_type):
        prog, qtbot = ini_daq_viewer_without_ui
        prog.daq_type = daq_type
        assert prog.detectors == [det_dict['name'] for det_dict in DET_TYPES[daq_type]]

    @pytest.mark.parametrize("det", [det_dict['name'] for det_dict in DET_TYPES['DAQ0D']])
    def test_detector_changed(self, ini_daq_viewer_without_ui, det):
        prog, qtbot = ini_daq_viewer_without_ui
        prog.daq_type = 'DAQ0D'
        prog.detector = det
        det_params, _class = get_viewer_plugins(prog.daq_type, prog.detector)
        assert putils.iter_children(prog.settings.child('detector_settings'), []) == \
            putils.iter_children(det_params, [])

    def test_init_hardware(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui
        prog.daq_type = 'DAQ0D'
        with qtbot.waitSignal(prog.init_signal) as blocker:
            prog.init_hardware(do_init=True)
        assert prog._initialized_state
        assert blocker.args[0]
        with qtbot.waitSignal(prog.init_signal) as blocker:
            prog.init_hardware(do_init=False)
        assert not prog._initialized_state
        assert not blocker.args[0]
        prog.quit_fun()

    def test_grab_data_snap(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui
        with qtbot.waitSignal(prog.init_signal) as blocker:
            prog.init_hardware(do_init=True)
        assert blocker.args[0]

        with qtbot.waitSignal(prog.grab_done_signal) as blocker:
            prog.grab_data(snap_state=True)
        assert blocker.args[0]['Ndatas'] == 1
        assert blocker.args[0]['control_module'] == 'DAQ_Viewer'
        assert blocker.args[0]['data1D'] != OrderedDict([])
        prog.quit_fun()

    def test_grab_data_snapshot(self, ini_daq_viewer_without_ui, tmp_path):
        prog, qtbot = ini_daq_viewer_without_ui
        with qtbot.waitSignal(prog.init_signal) as blocker:
            prog.init_hardware(do_init=True)
        assert blocker.args[0]

        with qtbot.assertNotEmitted(prog.data_saved) as blocker:
            prog.snapshot(pathname=tmp_path.joinpath('test.h5'))

        with qtbot.waitSignals([prog.data_saved, prog.grab_done_signal, ], order='strict') as blocker:
            prog.snapshot(pathname=tmp_path.joinpath('test.h5'), dosave=True)

        assert blocker.all_signals_and_args[1].args[0]['Ndatas'] == 1
        assert blocker.all_signals_and_args[1].args[0]['control_module'] == 'DAQ_Viewer'
        assert blocker.all_signals_and_args[1].args[0]['data1D'] != OrderedDict([])
        prog.quit_fun()

    def test_grab_data_live(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui
        with qtbot.waitSignal(prog.init_signal) as blocker:
            prog.init_hardware(do_init=True)
        assert blocker.args[0]

        with qtbot.waitSignals([prog.grab_done_signal, prog.grab_done_signal, prog.grab_done_signal]) as blocker:
            prog.grab_data(grab_state=True)
        assert prog.grab_state

        prog.grab_data(grab_state=False)

        with qtbot.waitSignal(prog.init_signal) as blocker:
            prog.init_hardware(False)
        prog.quit_fun()

    def test_grab_data_live_stop(self, ini_daq_viewer_without_ui):
        prog, qtbot = ini_daq_viewer_without_ui
        with qtbot.waitSignal(prog.init_signal) as blocker:
            prog.init_hardware(do_init=True)
        assert blocker.args[0]

        with qtbot.waitSignal(prog.grab_status) as blocker:
            prog.grab_data(grab_state=True)
        assert blocker.args[0]
        assert prog.grab_state

        with qtbot.waitSignal(prog.grab_status) as blocker:
            prog.stop()
        assert not blocker.args[0]
        assert not prog.grab_state

        with qtbot.waitSignal(prog.init_signal) as blocker:
            prog.init_hardware(False)
        prog.quit_fun()

    def test_grab_data_snap_bkg(self, ini_daq_viewer_without_ui, tmp_path):
        prog, qtbot = ini_daq_viewer_without_ui
        with qtbot.waitSignal(prog.init_signal) as blocker:
            prog.init_hardware(do_init=True)
        assert blocker.args[0]
        assert prog._bkg is None

        with qtbot.waitSignal(prog.grab_done_signal) as blocker:
            prog.take_bkg()

        assert prog._bkg is not None
        keys = list(prog._data_to_save_export['data1D'].keys())
        assert np.any(prog._bkg[0].data[0] == pytest.approx(prog._data_to_save_export['data1D'][keys[0]].data))
        assert np.any(prog._bkg[0].data[1] == pytest.approx(prog._data_to_save_export['data1D'][keys[1]].data))

        prog.do_bkg = True
        with qtbot.waitSignals([prog.data_saved, prog.grab_done_signal, ], order='strict') as blocker:
            prog.snapshot(pathname=tmp_path.joinpath('test.h5'), dosave=True)

        h5browser = H5BrowserUtil()
        h5browser.open_file(tmp_path.joinpath('test.h5'))
        assert np.any(h5browser.get_h5_data('/Raw_datas/Detector000/Data1D/Ch000/Bkg')[0] ==
                      pytest.approx(prog._bkg[0].data[0]))
        h5browser.close_file()

        prog.quit_fun()


class TestWithUI:
    def test_init_ui(self, ini_daq_viewer_ui):
        prog, qtbot, dockarea = ini_daq_viewer_ui

    @pytest.mark.parametrize("daq_type", DAQ_TYPES)
    def test_daq_type_changed(self, ini_daq_viewer_ui, daq_type):
        prog, qtbot, dockarea = ini_daq_viewer_ui
        prog.daq_type = daq_type
        assert prog.detectors == [det_dict['name'] for det_dict in DET_TYPES[daq_type]]
        assert len(prog.viewers) == 1
        assert prog.viewers[0].viewer_type == f'Data{daq_type[3:]}'
        prog.quit_fun()

    def test_process_commands(self, ini_daq_viewer_ui):
        prog, qtbot, dockarea = ini_daq_viewer_ui

        with qtbot.waitSignal(prog.ui.command_sig) as blocker:
            qtbot.mouseClick(prog.ui._ini_det_pb, QtCore.Qt.LeftButton)
        assert blocker.args[0].command == 'init'
        with qtbot.waitSignal(prog.ui.command_sig) as blocker:
            prog.ui.get_action('stop').trigger()
        assert blocker.args[0].command == 'stop'

        prog.quit_fun()

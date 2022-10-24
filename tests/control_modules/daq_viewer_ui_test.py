# -*- coding: utf-8 -*-
"""
Created the 03/10/2022

@author: Sebastien Weber
"""
import pytest
from pytest import fixture
from pymodaq.daq_utils.conftests import qtbotskip, main_modules_skip
from pymodaq.control_modules.daq_viewer_ui import DAQ_Viewer_UI
from pymodaq.daq_utils.gui_utils.dock import DockArea

pytestmark = pytest.mark.skipif(qtbotskip, reason='qtbot issues but tested locally')


@fixture
def init_qt(qtbot):
    return qtbot

@fixture
def ini_daq_viewer_ui(init_qt):
    qtbot = init_qt
    dockarea = DockArea()
    daq_types = ['DAQ0D', 'DAQ1D', 'DAQ2D', 'DAQND']
    detectors = [f'MyDetector{ind}' for ind in range(5)]
    qtbot.addWidget(dockarea)
    prog = DAQ_Viewer_UI(dockarea)

    prog.detectors = detectors
    prog.daq_types = daq_types
    return prog, qtbot, dockarea


def test_api_attributes(ini_daq_viewer_ui):
    """Make sure the API attribute and methods used from other modules are present
    """
    daq_viewer, qtbot, dockarea = ini_daq_viewer_ui
    assert hasattr(daq_viewer, 'command_sig')
    assert hasattr(daq_viewer, 'title')
    assert hasattr(daq_viewer, 'detector')
    assert hasattr(daq_viewer, 'detectors')
    assert hasattr(daq_viewer, 'daq_type')
    assert hasattr(daq_viewer, 'daq_types')
    assert hasattr(daq_viewer, 'add_setting_tree')
    assert hasattr(daq_viewer, 'add_viewer')
    assert hasattr(daq_viewer, 'do_init')
    assert hasattr(daq_viewer, 'detector_init')
    assert hasattr(daq_viewer, 'do_grab')
    assert hasattr(daq_viewer, 'do_snap')
    assert hasattr(daq_viewer, 'statusbar')

def test_private_attributes(ini_daq_viewer_ui):
    """Make sure the private attribute and methods used from other modules are present
    """
    daq_viewer, qtbot, dockarea = ini_daq_viewer_ui
    assert hasattr(daq_viewer, '_detector_widget')
    assert hasattr(daq_viewer, '_settings_widget')
    assert hasattr(daq_viewer, '_info_detector')
    assert hasattr(daq_viewer, '_daq_types_combo')
    assert hasattr(daq_viewer, '_detectors_combo')
    assert hasattr(daq_viewer, '_ini_det_pb')
    assert hasattr(daq_viewer, '_ini_state_led')

    assert hasattr(daq_viewer, '_enable_grab_buttons')
    assert hasattr(daq_viewer, '_grab')
    assert hasattr(daq_viewer, '_send_init')
    assert hasattr(daq_viewer, '_enable_detchoices')


def test_combo(ini_daq_viewer_ui):
    daq_viewer, qtbot, dockarea = ini_daq_viewer_ui
    daq_types = ['DAQ0D', 'DAQ1D', 'DAQ2D', 'DAQND']
    detectors = [f'MyDetector{ind}' for ind in range(5)]
    daq_viewer.daq_types = daq_types
    daq_viewer.detectors = detectors

    assert [daq_viewer._daq_types_combo.itemText(ind) for ind in range(daq_viewer._daq_types_combo.count())] ==\
           daq_types
    assert [daq_viewer._detectors_combo.itemText(ind) for ind in range(daq_viewer._detectors_combo.count())] ==\
           detectors


def test_signals(ini_daq_viewer_ui):
    """Testing that the triggering of actions and push buttons sends the correct signal to external application"""
    daq_viewer, qtbot, dockarea = ini_daq_viewer_ui

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('grab').trigger()
    assert blocker.args[0].command == 'grab'
    assert blocker.args[0].attribute

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('grab').trigger()
    assert not blocker.args[0].attribute

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('snap').trigger()
    assert blocker.args[0].command == 'snap'

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('log').trigger()
    assert blocker.args[0].command == 'show_log'

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('stop').trigger()
    assert blocker.args[0].command == 'stop'

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('quit').trigger()
    assert blocker.args[0].command == 'quit'

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.detector = daq_viewer.detectors[1]
    assert blocker.args[0].command == 'detector_changed'
    assert blocker.args[0].attribute == daq_viewer.detectors[1]

    with qtbot.waitSignals([daq_viewer.command_sig, daq_viewer.command_sig]) as blocker:
        daq_viewer.daq_type = daq_viewer.daq_types[1]

    assert blocker.all_signals_and_args[0].args[0].command == 'daq_type_changed'
    assert blocker.all_signals_and_args[0].args[0].attribute == daq_viewer.daq_types[1]
    assert blocker.all_signals_and_args[1].args[0].command == 'viewers_changed'
    assert blocker.all_signals_and_args[1].args[0].attribute['viewer_types'][0] == f'Data{daq_viewer.daq_types[1][3:]}'

    daq_viewer.daq_type = daq_viewer.daq_types[1]
    daq_viewer.detector = daq_viewer.detectors[2]

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer._ini_det_pb.click()

    assert blocker.args[0].command == 'init'
    assert blocker.args[0].attribute[0]
    assert blocker.args[0].attribute[1] == daq_viewer.daq_types[1]
    assert blocker.args[0].attribute[2] == daq_viewer.detectors[2]

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('save_current').trigger()
    assert blocker.args[0].command == 'save_current'

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('save_new').trigger()
    assert blocker.args[0].command == 'save_new'

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('open').trigger()
    assert blocker.args[0].command == 'open'

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer._do_bkg_cb.click()
    assert blocker.args[0].command == 'do_bkg'
    assert blocker.args[0].attribute

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer._take_bkg_pb.click()
    assert blocker.args[0].command == 'take_bkg'


def test_do_init(ini_daq_viewer_ui):
    IND_daq_type = 1
    IND_det_type = 2

    daq_viewer, qtbot, dockarea = ini_daq_viewer_ui
    daq_viewer.daq_type = daq_viewer.daq_types[IND_daq_type]
    daq_viewer.detector = daq_viewer.detectors[IND_det_type]

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.do_init(True)
    assert blocker.args[0].command == 'init'
    assert blocker.args[0].attribute[0]
    assert blocker.args[0].attribute[1] == daq_viewer.daq_types[IND_daq_type]
    assert blocker.args[0].attribute[2] == daq_viewer.detectors[IND_det_type]

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.do_init(False)
    assert blocker.args[0].command == 'init'
    assert not blocker.args[0].attribute[0]
    assert blocker.args[0].attribute[1] == daq_viewer.daq_types[IND_daq_type]
    assert blocker.args[0].attribute[2] == daq_viewer.detectors[IND_det_type]

    # if triggered twice with same boolean, no action is performed
    with pytest.raises(qtbot.TimeoutError):
        with qtbot.waitSignal(daq_viewer.command_sig, timeout=100) as blocker:
            daq_viewer.do_init(False)


def test_is_init(ini_daq_viewer_ui):
    IND_daq_type = 1
    IND_det_type = 2

    daq_viewer, qtbot, dockarea = ini_daq_viewer_ui
    daq_viewer.daq_type = daq_viewer.daq_types[IND_daq_type]
    daq_viewer.detector = daq_viewer.detectors[IND_det_type]

    daq_viewer.detector_init = True
    assert daq_viewer.detector_init
    assert daq_viewer._info_detector.text() == f'{daq_viewer.daq_type} : {daq_viewer.detector}'

    daq_viewer.detector_init = False
    assert not daq_viewer.detector_init
    assert daq_viewer._info_detector.text() == ''


def test_do_grab(ini_daq_viewer_ui):
    daq_viewer, qtbot, dockarea = ini_daq_viewer_ui

    daq_viewer.do_init(True)
    with pytest.raises(qtbot.TimeoutError):
        with qtbot.waitSignal(daq_viewer.command_sig, timeout=100) as blocker:
            daq_viewer.do_grab(False)

    with qtbot.waitSignal(daq_viewer.command_sig, timeout=100) as blocker:
        daq_viewer.do_grab(True)
    assert blocker.args[0].command == 'grab'
    assert blocker.args[0].attribute

    with qtbot.waitSignal(daq_viewer.command_sig, timeout=100) as blocker:
        daq_viewer.do_grab(False)
    assert blocker.args[0].command == 'grab'
    assert not blocker.args[0].attribute


def test_show_settings(ini_daq_viewer_ui):
    daq_viewer, qtbot, dockarea = ini_daq_viewer_ui
    dockarea.show()
    daq_viewer.get_action('show_settings').trigger()

    def is_visible():
        assert daq_viewer._detector_widget.isVisible()
    qtbot.waitUntil(is_visible)


def test_update_viewers(ini_daq_viewer_ui):
    daq_viewer, qtbot, dockarea = ini_daq_viewer_ui
    dockarea.show()

    assert len(daq_viewer.viewers) == 1

    data_dims = ['Data0D', 'Data2D']
    daq_viewer.update_viewers(data_dims)

    assert len(daq_viewer.viewers) == len(data_dims)
    assert daq_viewer.viewer_types == data_dims

    v0 = daq_viewer.viewers[0]

    data_dims = ['Data0D', 'Data1D', 'Data2D']
    daq_viewer.update_viewers(data_dims)
    assert len(daq_viewer.viewers) == len(data_dims)
    assert daq_viewer.viewer_types == data_dims
    assert daq_viewer.viewers[0] is v0

    daq_viewer.update_viewers([])
    assert len(daq_viewer.viewers) == 0

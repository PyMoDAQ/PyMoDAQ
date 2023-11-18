# -*- coding: utf-8 -*-
"""
Created the 03/10/2022

@author: Sebastien Weber
"""
import pytest
from pytest import fixture
from pymodaq.utils.conftests import qtbotskip, main_modules_skip
from pymodaq.control_modules.daq_viewer_ui import DAQ_Viewer_UI
from pymodaq.utils.gui_utils.dock import DockArea
from qtpy import QtWidgets

pytestmark = pytest.mark.skipif(True, reason='qtbot issues but tested locally')


@fixture
def ini_daq_viewer_ui(qtbot):
    win = QtWidgets.QMainWindow()
    qtbot.addWidget(win)
    area = DockArea()
    win.setCentralWidget(area)
    daq_types = ['DAQ0D', 'DAQ1D', 'DAQ2D', 'DAQND']
    detectors = [f'MyDetector{ind}' for ind in range(5)]
    prog = DAQ_Viewer_UI(area)
    win.show()
    prog.detectors = detectors
    prog.daq_types = daq_types
    yield prog, qtbot
    prog.close()
    prog.parent.close()
    QtWidgets.QApplication.processEvents()

@pytestmark
def test_api_attributes(ini_daq_viewer_ui):
    """Make sure the API attribute and methods used from other modules are present
    """
    daq_viewer, qtbot = ini_daq_viewer_ui
    attributes = daq_viewer.__dir__()[:]
    assert 'command_sig' in attributes
    assert 'title' in attributes
    assert 'detector' in attributes
    assert 'detectors' in attributes
    assert 'daq_type' in attributes
    assert 'daq_types' in attributes
    assert 'add_setting_tree' in attributes
    assert 'add_viewer' in attributes
    assert 'do_init' in attributes
    assert 'detector_init' in attributes
    assert 'do_grab' in attributes
    assert 'do_snap' in attributes
    assert 'statusbar' in attributes


@pytestmark
def test_private_attributes(ini_daq_viewer_ui):
    """Make sure the private attribute and methods used from other modules are present
    """
    daq_viewer, qtbot = ini_daq_viewer_ui
    attributes = daq_viewer.__dir__()[:]
    assert '_detector_widget' in attributes
    assert '_settings_widget' in attributes
    assert '_info_detector' in attributes
    assert '_daq_types_combo' in attributes
    assert '_detectors_combo' in attributes
    assert '_ini_det_pb' in attributes
    assert '_ini_state_led' in attributes

    assert '_enable_grab_buttons' in attributes
    assert '_grab' in attributes
    #assert '_send_init' in attributes
    assert '_enable_detchoices' in attributes


@pytestmark
def test_combo(ini_daq_viewer_ui):
    daq_viewer, qtbot = ini_daq_viewer_ui
    daq_types = ['DAQ0D', 'DAQ1D', 'DAQ2D', 'DAQND']
    detectors = [f'MyDetector{ind}' for ind in range(5)]
    daq_viewer.daq_types = daq_types
    daq_viewer.detectors = detectors

    assert [daq_viewer._daq_types_combo.itemText(ind) for ind in range(daq_viewer._daq_types_combo.count())] ==\
           daq_types
    assert [daq_viewer._detectors_combo.itemText(ind) for ind in range(daq_viewer._detectors_combo.count())] ==\
           detectors


@pytestmark
def test_signals(ini_daq_viewer_ui):
    """Testing that the triggering of actions and push buttons sends the correct signal to external application"""
    daq_viewer, qtbot = ini_daq_viewer_ui

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
    assert blocker.all_signals_and_args[1].args[0].attribute['viewer_types'][0] == f'Viewer{daq_viewer.daq_types[1][3:]}'

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


@pytestmark
def test_do_init(ini_daq_viewer_ui):
    IND_daq_type = 1
    IND_det_type = 2

    daq_viewer, qtbot = ini_daq_viewer_ui
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


@pytestmark
def test_is_init(ini_daq_viewer_ui):
    IND_daq_type = 1
    IND_det_type = 2

    daq_viewer, qtbot = ini_daq_viewer_ui
    daq_viewer.daq_type = daq_viewer.daq_types[IND_daq_type]
    daq_viewer.detector = daq_viewer.detectors[IND_det_type]

    daq_viewer.detector_init = True
    assert daq_viewer.detector_init
    assert daq_viewer._info_detector.text() == f'{daq_viewer.daq_type.name} : {daq_viewer.detector}'

    daq_viewer.detector_init = False
    assert not daq_viewer.detector_init
    assert daq_viewer._info_detector.text() == ''


@pytestmark
def test_do_grab(ini_daq_viewer_ui):
    daq_viewer, qtbot = ini_daq_viewer_ui

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


@pytestmark
def test_update_viewers(ini_daq_viewer_ui):
    daq_viewer, qtbot = ini_daq_viewer_ui

    assert len(daq_viewer.viewers) == 1

    data_dims = ['Viewer0D', 'Viewer2D']
    daq_viewer.update_viewers(data_dims)

    assert len(daq_viewer.viewers) == len(data_dims)
    assert daq_viewer.viewer_types == data_dims

    v0 = daq_viewer.viewers[0]

    data_dims = ['Viewer0D', 'Viewer1D', 'Viewer2D']
    daq_viewer.update_viewers(data_dims)
    assert len(daq_viewer.viewers) == len(data_dims)
    assert daq_viewer.viewer_types == data_dims
    assert daq_viewer.viewers[0] is v0

    daq_viewer.update_viewers([])
    assert len(daq_viewer.viewers) == 0

# -*- coding: utf-8 -*-
"""
Created the 03/10/2022

@author: Sebastien Weber
"""
import pytest
from pytest import fixture

from pymodaq.control_modules.daq_viewer_ui.viewer_selector import SelectedModule
from pymodaq.utils.conftests import qtbotskip, main_modules_skip
from pymodaq.control_modules.daq_viewer_ui.ui_base import DAQ_Viewer_UI, options, DAQTypesEnum
from pymodaq_gui.utils.dock import DockArea
from qtpy import QtWidgets
from pymodaq.control_modules.thread_commands import UiToMainViewer
import qt_themes

from pymodaq_utils.config import Config
config = Config()


pytestmark = pytest.mark.skipif(False, reason='qtbot issues but tested locally')


@fixture
def ini_daq_viewer_ui(qtbot):
    win = QtWidgets.QMainWindow()
    qtbot.addWidget(win)
    qt_themes.set_theme(theme=config('style', 'theme')[0],
                        style=config('style', 'style')[0])

    widget = QtWidgets.QWidget()
    win.setCentralWidget(widget)
    prog = DAQ_Viewer_UI(widget)
    win.show()
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
    assert 'add_setting_tree' in attributes
    assert 'add_viewer' in attributes
    assert 'do_init' in attributes
    assert 'detector_init' in attributes
    assert 'do_grab' in attributes
    assert 'do_snap' in attributes


@pytestmark
def test_signals(ini_daq_viewer_ui):
    """Testing that the triggering of actions and push buttons sends the correct signal to external application"""
    daq_viewer, qtbot = ini_daq_viewer_ui

    daq_viewer.detector_init = True

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('grab').trigger()
    assert blocker.args[0].command == 'grab'
    assert blocker.args[0].attribute

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('grab').trigger()
    assert blocker.args[0].command == UiToMainViewer.GRAB
    assert not blocker.args[0].attribute

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('snap').trigger()
    assert blocker.args[0].command == UiToMainViewer.SNAP

    daq_viewer.detector_init = False

    assert daq_viewer.viewer_types[0] == DAQTypesEnum.DAQ0D.to_viewer_type()

    MOD = SelectedModule(daq_type=DAQTypesEnum.DAQ1D, module_name='Mock')
    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.detector = MOD
    assert blocker.args[0].command == UiToMainViewer.DETECTOR_CHANGED
    assert blocker.args[0].attribute == MOD

    assert daq_viewer.viewer_types[0] == MOD.daq_type.to_viewer_type()


    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('ini_detector').trigger()

    assert blocker.args[0].command == UiToMainViewer.INIT
    assert blocker.args[0].attribute[0]
    assert blocker.args[0].attribute[1] == MOD

    daq_viewer.detector_init = True # in real implementation of the DAQ_Viewer, this command is called
    #after the right return from the plugin instrument

    assert daq_viewer.is_action_enabled('save_current')

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('save_current').trigger()
    assert blocker.args[0].command == UiToMainViewer.SAVE_CURRENT

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('background_subtract').trigger()
    assert blocker.args[0].command == UiToMainViewer.DO_BKG
    assert blocker.args[0].attribute

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.get_action('background_snap').trigger()
    assert blocker.args[0].command == UiToMainViewer.TAKE_BKG


@pytestmark
def test_do_init(ini_daq_viewer_ui):
    IND_daq_type = 1
    IND_det_type = 2
    daq_type = DAQTypesEnum[DAQTypesEnum.names()[IND_daq_type]]
    det_name = options[daq_type.name][IND_det_type]

    detector  = SelectedModule(daq_type,det_name)

    daq_viewer, qtbot = ini_daq_viewer_ui
    daq_viewer.detector = detector

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.do_init(True)
    assert blocker.args[0].command == UiToMainViewer.INIT
    assert blocker.args[0].attribute[0]
    assert blocker.args[0].attribute[1] == detector

    with qtbot.waitSignal(daq_viewer.command_sig) as blocker:
        daq_viewer.do_init(False)
    assert blocker.args[0].command == UiToMainViewer.INIT
    assert not blocker.args[0].attribute[0]
    assert blocker.args[0].attribute[1] == detector

    # if triggered twice with same boolean, no action is performed
    with pytest.raises(qtbot.TimeoutError):
        with qtbot.waitSignal(daq_viewer.command_sig, timeout=100) as blocker:
            daq_viewer.do_init(False)


@pytestmark
def test_do_grab(ini_daq_viewer_ui):
    daq_viewer, qtbot = ini_daq_viewer_ui

    daq_viewer.do_init(True)
    daq_viewer.detector_init = True # in real implementation of the DAQ_Viewer, this command is called
    #after the right return from the plugin instrument

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

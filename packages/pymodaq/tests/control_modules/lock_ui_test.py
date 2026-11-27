"""Tests of the lock of the control module UIs (used while a scan runs)"""
import pytest
import qt_themes
from qtpy import QtWidgets

from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq_utils.config import GlobalConfig

config = GlobalConfig()


@pytest.fixture(params=['move', 'viewer'])
def module(qtbot, request):
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0], style=config('gui', 'style', 'style')[0])
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    prog = DAQ_Move(widget) if request.param == 'move' else DAQ_Viewer(widget)
    widget.show()
    yield prog
    prog.quit_fun()
    widget.close()


def _enabled(ui):
    return {name: ui._action_enabled(name) for name in ui.actions_names}


def test_lock_keeps_display_widgets_enabled(module):
    ui = module.ui
    before = _enabled(ui)
    ui.lock_user_actions(True)
    for name in ui.actions_names:
        if name in ui.LOCK_EXEMPT:
            assert ui._action_enabled(name) == before[name]
        else:
            assert not ui._action_enabled(name)
    assert ui.toolbar.isEnabled()
    assert ui.status_led.isEnabled()
    ui.lock_user_actions(False)
    assert _enabled(ui) == before


def test_state_changes_while_locked_are_applied_on_unlock(module):
    ui = module.ui
    ui.enable_actions(True)
    names = [n for n in ui.actions_names if n not in ui.LOCK_EXEMPT and ui._action_enabled(n)]
    ui.enable_actions(False)
    before = _enabled(ui)
    ui.lock_user_actions(True)
    ui.enable_actions(True)  # e.g. an internal refresh during the scan
    assert not any(ui._action_enabled(n) for n in names)
    ui.lock_user_actions(False)
    assert [n for n in names if not ui._action_enabled(n)] == []
    assert before != _enabled(ui)


def test_modules_manager_enable_modules(module):
    from pymodaq.utils.managers.modules import ModulesManager
    manager = ModulesManager.__new__(ModulesManager)
    manager.__class__ = type('M', (ModulesManager,), {'modules_all': property(lambda self: [module])})
    before = _enabled(module.ui)
    manager.enable_modules(False)
    assert module.ui.user_actions_locked
    manager.enable_modules(True)
    assert not module.ui.user_actions_locked
    assert _enabled(module.ui) == before

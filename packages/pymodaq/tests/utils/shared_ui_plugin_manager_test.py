import pytest
import qt_themes
from qtpy import QtCore, QtWidgets

from pymodaq.utils import shared_ui as shared_ui_module


class FakePluginManager(QtCore.QObject):
    """The real manager fetches the plugins from the network in a thread: not needed here"""
    quit_signal = QtCore.Signal()
    restart_signal = QtCore.Signal()
    created = 0

    def __init__(self, parent):
        super().__init__()
        type(self).created += 1


@pytest.fixture
def shared_ui(qtbot, monkeypatch):
    monkeypatch.setattr(shared_ui_module, 'PluginManager', FakePluginManager)
    FakePluginManager.created = 0
    qt_themes.set_theme('dracula')
    win = QtWidgets.QMainWindow()
    qtbot.addWidget(win)
    ui = shared_ui_module.SharedUI(win, show=False)
    yield ui
    manager_win = getattr(ui, 'win_plug_manager', None)
    if manager_win is not None:
        manager_win.close()


def test_plugin_manager_window_is_opened_once(shared_ui):
    shared_ui.start_plugin_manager()
    first = shared_ui.win_plug_manager
    assert first.isVisible()
    assert FakePluginManager.created == 1

    shared_ui.start_plugin_manager()  # already open: brought to the front, no second window
    assert shared_ui.win_plug_manager is first
    assert FakePluginManager.created == 1


def test_plugin_manager_window_is_reopened_after_closing(shared_ui):
    shared_ui.start_plugin_manager()
    first = shared_ui.win_plug_manager
    first.close()
    assert not first.isVisible()

    shared_ui.start_plugin_manager()
    assert shared_ui.win_plug_manager is not first
    assert shared_ui.win_plug_manager.isVisible()
    assert FakePluginManager.created == 2

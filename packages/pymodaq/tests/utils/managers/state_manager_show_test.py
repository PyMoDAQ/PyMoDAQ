from unittest.mock import MagicMock

import pytest
import qt_themes

from pymodaq.utils.managers.state.state_manager import StateManager
from pymodaq.utils.managers.modules import module_settings_manager as msm
from pymodaq_gui.parameter import Parameter
from pymodaq_utils.config import GlobalConfig

config = GlobalConfig()


def modules_settings(names):
    return Parameter.create(name='control_modules', type='group', children=[
        dict(name=name, type='int', value=1) for name in names])


@pytest.fixture
def state_manager(qtbot, monkeypatch):
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0], style=config('gui', 'style', 'style')[0])
    names = ['a']
    monkeypatch.setattr(msm.ModulesSettingsManager, 'create_settings_all',
                        lambda self, actuators, detectors: modules_settings(names))
    state_manager = StateManager()
    monkeypatch.setattr(state_manager, 'dashboard', MagicMock())
    qtbot.addWidget(state_manager.mainwindow)
    state_manager.names = names
    yield state_manager
    state_manager.quit_fun()
    state_manager.mainwindow.close()


def test_show_builds_the_tree_only_when_the_modules_changed(state_manager, monkeypatch):
    calls = []
    original = StateManager.update_settings
    monkeypatch.setattr(StateManager, 'update_settings',
                        lambda self, settings=None: (calls.append(1), original(self, settings))[1])

    state_manager.show()
    state_manager.show()
    assert len(calls) == 1

    state_manager.names.append('b')
    state_manager.show()
    assert len(calls) == 2
    assert [child.name() for child in state_manager.settings.children()] == ['a', 'b']


def test_show_rebuilds_after_the_settings_were_replaced(state_manager):
    state_manager.show()
    state_manager.update_settings(modules_settings(['other']))
    state_manager.show()
    assert [child.name() for child in state_manager.settings.children()] == ['a']


def test_setting_the_tree_several_times_does_not_stack_slots(state_manager, monkeypatch):
    resized = []
    tree = state_manager.tree
    monkeypatch.setattr(tree, 'resizeColumnToContents', lambda col: resized.append(col))
    for _ in range(5):
        state_manager.update_settings(modules_settings(['a']))
    resized.clear()
    tree.itemExpanded.emit(tree.topLevelItem(0))
    assert len(resized) == 1

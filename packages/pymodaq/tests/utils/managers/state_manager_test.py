import threading
# -*- coding: utf-8 -*-
"""
Created the 07/11/2023

@author: Sebastien Weber
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from qtpy import QtWidgets, QtCore

import qt_themes
from pymodaq_utils.config import GlobalConfig
from pymodaq.utils.managers.state.state_manager import StateManager
from pymodaq.utils.managers.state.subentries import (
    SubEntryHandlerFactory, StateSubEntryHandlerTypes)


factory = SubEntryHandlerFactory()
config = GlobalConfig()


@pytest.fixture
def init_qt(qtbot):
    qt_themes.set_theme(
        theme=config('gui', 'style', 'theme')[0],
        style=config('gui', 'style', 'style')[0],
    )
    return qtbot


@pytest.fixture
def ini_state_manager(init_qt):

    qtbot = init_qt

    external_ui = QtWidgets.QMainWindow()

    state_manager = StateManager()
    state_manager.settings = Path(__file__).parent.joinpath('settings.xml')

    state_manager.update_entry()
    qtbot.addWidget(state_manager.mainwindow)
    state_manager.mainwindow.show()
    qtbot.addWidget(external_ui)

    yield state_manager, qtbot

    state_manager.mainwindow.close()
    external_ui.close()


class TestStateManager:

    def test_ini(self, ini_state_manager):
        """
        """
        state_manager, qtbot = ini_state_manager

        assert state_manager.entry_type == 'state'
        assert state_manager.entry_extension == '.state'


class TestExecution:

    @pytest.fixture
    def delayed_state_manager(self, ini_state_manager, monkeypatch):
        """ StateManager whose execution ends 200 ms after the call, as when an actuator moves """
        state_manager, qtbot = ini_state_manager
        monkeypatch.setattr(state_manager, 'dashboard', MagicMock())
        monkeypatch.setattr(state_manager, 'save_new_history_entry', lambda: None)

        def delayed_execute_entry(entry_path=None, **kwargs):
            state_manager._execution_pending = True
            QtCore.QTimer.singleShot(200, state_manager.finalize)
            return None

        monkeypatch.setattr(state_manager, '_execute_entry', delayed_execute_entry)
        return state_manager, qtbot

    def test_blocking_by_default(self, delayed_state_manager):
        state_manager, qtbot = delayed_state_manager
        assert state_manager.is_action_checked('blocking_execution')

        state_manager.execute_entry()
        assert state_manager.entry_applied
        assert not state_manager._execution_pending

    def test_non_blocking(self, delayed_state_manager):
        state_manager, qtbot = delayed_state_manager

        with qtbot.waitSignal(state_manager.applied_entry, timeout=2000):
            state_manager.execute_entry(blocking=False)
            assert not state_manager.entry_applied
        assert state_manager.entry_applied

    def test_non_blocking_from_action(self, delayed_state_manager):
        state_manager, qtbot = delayed_state_manager
        state_manager.set_action_checked('blocking_execution', False)

        with qtbot.waitSignal(state_manager.applied_entry, timeout=2000):
            state_manager.execute_entry()
            assert not state_manager.entry_applied

    def test_entry_applied_reset_on_new_execution(self, delayed_state_manager):
        state_manager, qtbot = delayed_state_manager
        state_manager.execute_entry()
        assert state_manager.entry_applied

        with qtbot.waitSignal(state_manager.applied_entry, timeout=2000):
            state_manager.execute_entry(blocking=False)
            assert not state_manager.entry_applied

    def test_blocking_timeout(self, delayed_state_manager):
        """ The wait stops after the timeout, the execution goes on and ends normally """
        state_manager, qtbot = delayed_state_manager
        state_manager._execute_entry = lambda *args, **kwargs: setattr(state_manager, '_execution_pending', True)

        state_manager.execute_entry(timeout=0.05)  # nothing ends the execution
        assert state_manager._execution_pending
        assert not state_manager.entry_applied

        with qtbot.waitSignal(state_manager.applied_entry, timeout=2000):
            state_manager.finalize()
        assert state_manager.entry_applied

    def test_blocking_from_another_thread_does_not_wait(self, delayed_state_manager):
        state_manager, qtbot = delayed_state_manager
        state_manager.dashboard = MagicMock()
        waited = []

        def run():
            state_manager._wait_until_applied()
            waited.append(True)

        thread = threading.Thread(target=run)
        thread.start()
        thread.join(2)
        assert waited and not thread.is_alive()


class TestSpecialEntryFactory:

    def test_registered_entries(self):
        for entry in StateSubEntryHandlerTypes.values():
            assert entry in factory.entries
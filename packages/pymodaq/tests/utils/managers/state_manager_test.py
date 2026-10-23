import gc
import time
import threading
from contextlib import contextmanager
# -*- coding: utf-8 -*-
"""
Created the 07/11/2023

@author: Sebastien Weber

Context: the tests asserting that a call returns "at once" (``test_blocking_without_blocking_the_caller``,
``test_non_blocking``) time it with ``no_garbage_collection``. The state manager windows and their large parameter
trees are not freed as soon as a test ends: with PySide6 on the CI runners a garbage collection starting inside the
timed call could take minutes (up to 886 s measured) to free them, and fail the assertion whatever the code does.
This only keeps the measure reliable, it does not make the collections faster: the leaks themselves are a
separate matter (see issue #1275).
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from qtpy import QtWidgets, QtCore

import qt_themes
from pymodaq_utils.config import GlobalConfig
from pymodaq.utils.managers.state import state_manager as state_manager_module
from pymodaq.utils.managers.state.state_manager import StateManager
from pymodaq.utils.managers.state.subentries import (
    SubEntryHandlerFactory, StateSubEntryHandlerTypes, ActuatorValueSubEntryHandler)


factory = SubEntryHandlerFactory()
config = GlobalConfig()


@contextmanager
def no_garbage_collection():
    """ Keep a timed call from being stretched by a garbage collection

    With PySide6 the collections free the large widget trees left by the previous tests, which took minutes on
    the CI runners.
    """
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        yield
    finally:
        if was_enabled:
            gc.enable()


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

    splash = getattr(state_manager, 'splash_subentries', None)  # shown when a state is executed
    if splash is not None:
        try:
            splash.close()
            splash.deleteLater()
        except RuntimeError:  # already deleted by the test
            pass
    for window in (state_manager.mainwindow, external_ui):
        window.close()
        window.deleteLater()
    # deferred deletions are not run by processEvents: without this the windows (and their large
    # parameter trees) pile up from test to test and slow down every garbage collection
    QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    qtbot.wait(10)


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
            state_manager._resolve_blocking()
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

    def test_blocking_option_saved_in_the_state(self, delayed_state_manager, tmp_path):
        """ The sequencer executes a state by name: the options stored in the file decide, not the current actions """
        state_manager, qtbot = delayed_state_manager
        state_manager.set_action_checked('parallel_execution', True)
        state_manager.set_action_checked('blocking_execution', False)
        path = tmp_path / 'nonblocking.state'
        state_manager.save_entries(path)

        state_manager.set_action_checked('parallel_execution', False)  # actions now say sequential/blocking
        state_manager.update_entry(path)
        assert state_manager.is_action_checked('parallel_execution')
        assert not state_manager.is_action_checked('blocking_execution')

        state_manager.set_action_checked('blocking_execution', True)
        state_manager.set_action_checked('parallel_execution', False)
        with qtbot.waitSignal(state_manager.applied_entry, timeout=2000):
            state_manager.execute_entry(path, block_caller=False)
            assert not state_manager.blocking_wanted
            assert not state_manager._blocking_subentries

    def test_state_file_without_blocking_option(self, delayed_state_manager, tmp_path):
        """ Files written before the option existed only have the parallel flag"""
        from pymodaq.utils.managers.state.state_manager import ser_factory
        state_manager, qtbot = delayed_state_manager
        path = tmp_path / 'old.state'
        path.write_bytes(ser_factory.get_apply_serializer(True))
        state_manager.update_entry(path)
        assert state_manager.is_action_checked('parallel_execution')
        assert state_manager.is_action_checked('blocking_execution')

    def test_execute_uses_the_current_settings_not_the_file(self, delayed_state_manager, tmp_path, monkeypatch):
        """ Options changed in the manager and not saved are the ones executed, the file is not modified """
        state_manager, qtbot = delayed_state_manager
        monkeypatch.setattr(state_manager, 'get_entry_folder', lambda **kwargs: tmp_path)
        state_manager.set_action_checked('parallel_execution', True)
        state_manager.set_action_checked('blocking_execution', True)
        state_manager.save_entries(state_manager.entry_filepath)
        saved = state_manager.entry_filepath.read_bytes()

        state_manager.set_action_checked('blocking_execution', False)  # not saved
        with qtbot.waitSignal(state_manager.applied_entry, timeout=2000):
            state_manager.execute_current_entry()
            assert not state_manager._blocking_subentries
        assert state_manager.is_action_checked('parallel_execution')
        assert not state_manager.is_action_checked('blocking_execution')
        assert state_manager.entry_filepath.read_bytes() == saved

    def test_execute_a_named_entry_loads_it(self, delayed_state_manager, tmp_path, monkeypatch):
        """ From the outside (a name or a path), the selected entry is loaded then executed """
        state_manager, qtbot = delayed_state_manager
        monkeypatch.setattr(state_manager, 'get_entry_folder', lambda **kwargs: tmp_path)
        state_manager.set_action_checked('parallel_execution', True)
        state_manager.set_action_checked('blocking_execution', False)
        state_manager.save_entries(state_manager.entry_filepath)

        state_manager.set_action_checked('blocking_execution', True)  # not saved: replaced by the file
        with qtbot.waitSignal(state_manager.applied_entry, timeout=2000):
            state_manager.execute_entry(state_manager.entry)
            assert not state_manager._blocking_subentries
        assert not state_manager.is_action_checked('blocking_execution')

    @pytest.mark.parametrize('answer, saved, executed', [
        (QtWidgets.QMessageBox.StandardButton.Save, True, True),
        (QtWidgets.QMessageBox.StandardButton.Discard, False, True),
        (QtWidgets.QMessageBox.StandardButton.Cancel, False, False),
    ])
    def test_ask_before_executing_unsaved(self, delayed_state_manager, tmp_path, monkeypatch, answer, saved, executed):
        state_manager, qtbot = delayed_state_manager
        monkeypatch.setattr(state_manager, 'get_entry_folder', lambda **kwargs: tmp_path)
        monkeypatch.setattr(type(state_manager), 'ask_before_executing_unsaved', True)
        questions = []
        monkeypatch.setattr(state_manager, '_ask_unsaved_changes', lambda: questions.append(1) or answer)
        state_manager.set_action_checked('parallel_execution', True)
        state_manager.save_entries(state_manager.entry_filepath)
        before = state_manager.entry_filepath.read_bytes()
        assert not state_manager.has_unsaved_changes()

        state_manager.execute_current_entry()  # nothing differs: no question
        qtbot.wait(300)
        assert questions == []

        state_manager.set_action_checked('blocking_execution', False)
        assert state_manager.has_unsaved_changes()
        state_manager.entry_applied = False
        state_manager.execute_current_entry()
        qtbot.wait(300)
        assert questions == [1]
        assert (state_manager.entry_filepath.read_bytes() != before) == saved
        assert state_manager.entry_applied == executed

    def test_no_question_by_default(self, delayed_state_manager, tmp_path, monkeypatch):
        state_manager, qtbot = delayed_state_manager
        monkeypatch.setattr(state_manager, 'get_entry_folder', lambda **kwargs: tmp_path)
        monkeypatch.setattr(state_manager, '_ask_unsaved_changes',
                            lambda: pytest.fail('should not ask when the option is off'))
        state_manager.set_action_checked('parallel_execution', True)
        state_manager.save_entries(state_manager.entry_filepath)
        state_manager.set_action_checked('blocking_execution', False)
        assert state_manager.has_unsaved_changes()
        state_manager.execute_current_entry()
        qtbot.wait(300)
        assert state_manager.entry_applied

    def test_non_blocking_from_action(self, delayed_state_manager):
        state_manager, qtbot = delayed_state_manager
        state_manager.set_action_checked('parallel_execution', True)
        state_manager.set_action_checked('blocking_execution', False)

        with qtbot.waitSignal(state_manager.applied_entry, timeout=2000):
            state_manager.execute_entry()
            assert not state_manager.entry_applied

    def test_sequential_execution_always_blocks(self, delayed_state_manager):
        """ The blocking action is only selectable for a parallel execution """
        state_manager, qtbot = delayed_state_manager
        state_manager.set_action_checked('parallel_execution', True)
        state_manager.set_action_checked('blocking_execution', False)
        assert state_manager.is_action_enabled('blocking_execution')
        assert not state_manager.blocking_wanted

        state_manager.set_action_checked('parallel_execution', False)
        assert not state_manager.is_action_enabled('blocking_execution')
        assert state_manager.is_action_checked('blocking_execution')
        assert state_manager.blocking_wanted
        state_manager.execute_entry()
        assert state_manager.entry_applied

        state_manager.set_action_checked('parallel_execution', True)  # the choice of the user is restored
        assert not state_manager.is_action_checked('blocking_execution')
        assert state_manager.is_action_enabled('blocking_execution')

    def test_parallel_subentries_are_identified_by_their_index(self, delayed_state_manager):
        """ All sub-entries are started before the first one ends: the loop counter is then past the last one """
        state_manager, qtbot = delayed_state_manager
        entries = [MagicMock(entry_type=StateSubEntryHandlerTypes.SETTINGS) for _ in range(2)]
        state_manager.config_subentries = entries
        state_manager._ind_subentry = len(entries)
        state_manager.subentries_model = MagicMock()
        state_manager._processed_subentries = 0
        state_manager.set_action_checked('parallel_execution', True)

        state_manager._on_executed(0)
        state_manager._on_executed(1)
        state_manager.subentries_model.set_status.assert_any_call(1, True)
        assert state_manager.entry_applied

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

    def test_blocking_timeout_from_config(self, delayed_state_manager, monkeypatch):
        state_manager, qtbot = delayed_state_manager
        state_manager._execute_entry = lambda *args, **kwargs: setattr(state_manager, '_execution_pending', True)
        monkeypatch.setattr(state_manager_module, 'config',
                            lambda *args: 0.05 if args[-1] == 'execution_timeout_s' else None)

        state_manager.execute_entry()  # returns after the timeout of the configuration
        assert state_manager._execution_pending

        with qtbot.waitSignal(state_manager.applied_entry, timeout=2000):
            state_manager.finalize()

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


class FakeSubEntryHandler(QtCore.QObject):
    """ Sub-entry whose module needs 300 ms to do what is asked (an actuator moving) """
    executed_signal = QtCore.Signal(int)
    execution_failed = QtCore.Signal(Exception)

    def __init__(self, *args, ind_subentry=None, blocking=True, **kwargs):
        super().__init__()
        self._ind_subentry = ind_subentry
        self.blocking = blocking

    def execute_subentry(self, entry, dashboard=None):
        if self.blocking:
            QtCore.QTimer.singleShot(300, lambda: self.executed_signal.emit(self._ind_subentry))
        else:
            self.executed_signal.emit(self._ind_subentry)


class TestWithSubEntries:
    """ The whole chain: sub-entries ending asynchronously, in sequential and in parallel mode """

    @pytest.fixture
    def state_with_subentries(self, ini_state_manager, monkeypatch):
        state_manager, qtbot = ini_state_manager
        monkeypatch.setattr(state_manager, 'dashboard', MagicMock())
        monkeypatch.setattr(state_manager, 'save_new_history_entry', lambda: None)
        experiment_manager = MagicMock(applied_entry_name='default')
        monkeypatch.setattr(StateManager, 'experiment_manager', property(lambda self: experiment_manager))
        monkeypatch.setattr(StateManager, 'experiment_filename', property(lambda self: 'default'))
        subentries = [MagicMock(entry_type=StateSubEntryHandlerTypes.WAIT) for _ in range(3)]
        monkeypatch.setattr(state_manager_module, 'read_binary_and_deserialize',
                            lambda path: [False] + subentries)
        monkeypatch.setattr(state_manager_module.handler_factory, 'get_subentry_handler',
                            lambda entry_type: FakeSubEntryHandler)
        return state_manager, qtbot

    @pytest.mark.parametrize('parallel, min_duration', [(True, 0.25), (False, 0.85)])
    def test_blocking(self, state_with_subentries, parallel, min_duration):
        """ The caller waits for the modules (in parallel they are all waited for together)"""
        state_manager, qtbot = state_with_subentries
        state_manager.set_action_checked('parallel_execution', parallel)

        t0 = time.perf_counter()
        state_manager.execute_entry(blocking=True)
        assert time.perf_counter() - t0 > min_duration
        assert state_manager.entry_applied

    @pytest.mark.parametrize('parallel', [True, False])
    def test_blocking_without_blocking_the_caller(self, state_with_subentries, parallel):
        """ Wait for the modules but not in the call: used by the sequencer """
        state_manager, qtbot = state_with_subentries
        state_manager.set_action_checked('parallel_execution', parallel)

        with qtbot.waitSignal(state_manager.applied_entry, timeout=5000):
            with no_garbage_collection():
                t0 = time.perf_counter()
                state_manager.execute_entry(blocking=True, block_caller=False)
                duration = time.perf_counter() - t0
            assert duration < 0.2  # returned at once
            assert not state_manager.entry_applied
        assert state_manager.entry_applied

    def test_splash_deleted_before_it_is_closed(self, state_with_subentries):
        """ The splash is closed after a delay: deleting it in between must not raise in the event loop """
        state_manager, qtbot = state_with_subentries
        state_manager.execute_entry(blocking=False)
        state_manager.splash_subentries.deleteLater()
        QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        state_manager.close_subentries_display(50)  # as finalize does, when the splash is gone
        qtbot.wait(150)

    def test_non_blocking(self, state_with_subentries):
        """ In parallel, the modules are only started: everything is over at once, whatever the time they need """
        state_manager, qtbot = state_with_subentries
        state_manager.set_action_checked('parallel_execution', True)

        with no_garbage_collection():
            t0 = time.perf_counter()
            state_manager.execute_entry(blocking=False)
            duration = time.perf_counter() - t0
        assert duration < 0.2
        assert state_manager.entry_applied


class TestActuatorHandlerBlocking:

    @pytest.mark.parametrize('blocking', [True, False])
    def test_executed_when_started_or_when_moved(self, init_qt, blocking):
        handler = ActuatorValueSubEntryHandler(MagicMock(), MagicMock(), ind_subentry=3, blocking=blocking)
        module = MagicMock(initialized_state=True, units='mm')
        dashboard = MagicMock()
        dashboard.modules_manager.get_mod_from_name.return_value = module
        entry = MagicMock(module_name='act', setting=MagicMock())
        entry.setting.parameter.opts = {'suffix': 'mm'}
        entry.setting.parameter.value.return_value = 1.
        executed = []
        handler.executed_signal.connect(executed.append)
        handler.get_module = lambda entry, dashboard: module

        handler.execute_subentry(entry, dashboard)
        module.move_abs.assert_called_once()
        assert executed == ([] if blocking else [3])  # blocking: waits for move_done_signal
        assert module.move_done_signal.connect.called == blocking


class TestSpecialEntryFactory:

    def test_registered_entries(self):
        for entry in StateSubEntryHandlerTypes.values():
            assert entry in factory.entries
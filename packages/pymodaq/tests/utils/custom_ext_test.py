# -*- coding: utf-8 -*-
"""Lifecycle of a CustomExt: order of the hooks called by setup_ui, the experiment hook and the quit guard"""
import warnings

import pytest

from pymodaq_gui.utils.custom_app import WorkFlowActions

from pymodaq.utils.custom_ext import CustomExt
from pymodaq.utils.plugin_testing import loaded_extension


class RecordingExt(CustomExt):
    """Extension recording the hooks that the base classes call"""
    can_quit = True

    def __init__(self, parent, dashboard):
        super().__init__(parent, dashboard)
        self.calls = []
        self.setup_ui()

    def _record(self, name, *args):
        self.calls.append((name, *args))

    def setup_docks_and_widgets(self):
        self._record('setup_docks_and_widgets')
        super().setup_docks_and_widgets()

    def setup_menus_and_toolbars(self, menubar=None):
        self._record('setup_menus_and_toolbars')
        super().setup_menus_and_toolbars(menubar)

    def setup_workflow_actions(self):
        self._record('setup_workflow_actions')
        super().setup_workflow_actions()

    def setup_actions(self):
        self._record('setup_actions')
        super().setup_actions()

    def connect_things(self):
        self._record('connect_things')
        super().connect_things()

    def do_things_after_ui_setup(self):
        self._record('do_things_after_ui_setup')
        super().do_things_after_ui_setup()

    def do_things_after_experiment_set(self, experiment_name, show_dashboard=None):
        self._record('do_things_after_experiment_set', experiment_name)
        super().do_things_after_experiment_set(experiment_name, show_dashboard)

    def _quit_fun(self):
        self._record('_quit_fun')
        return self.can_quit


class WorkflowExt(RecordingExt):
    show_workflow_actions = True


class DeprecatedHooksExt(CustomExt):
    def __init__(self, parent, dashboard):
        super().__init__(parent, dashboard)
        self.calls = []
        self.setup_ui()

    def setup_docks(self):
        self.calls.append('setup_docks')

    def setup_menu(self, menubar=None):
        self.calls.append('setup_menu')

    def _quit_fun(self):
        return True


def test_setup_ui_calls_the_hooks_in_order():
    with loaded_extension(RecordingExt) as (dashboard, extension):
        assert [call[0] for call in extension.calls] == ['setup_docks_and_widgets', 'setup_menus_and_toolbars',
                                                         'setup_actions', 'connect_things', 'do_things_after_ui_setup']


def test_workflow_actions_are_set_up_between_menus_and_actions():
    with loaded_extension(WorkflowExt) as (dashboard, extension):
        assert [call[0] for call in extension.calls] == ['setup_docks_and_widgets', 'setup_menus_and_toolbars',
                                                         'setup_workflow_actions', 'setup_actions',
                                                         'connect_things', 'do_things_after_ui_setup']
        assert extension.has_action(WorkFlowActions.START)


def test_no_workflow_actions_by_default():
    with loaded_extension(RecordingExt) as (dashboard, extension):
        assert not extension.has_action(WorkFlowActions.START)


def test_deprecated_hooks_are_still_called_with_a_warning():
    with pytest.warns(DeprecationWarning):
        with loaded_extension(DeprecatedHooksExt) as (dashboard, extension):
            assert 'setup_docks' in extension.calls
            assert 'setup_menu' in extension.calls


def test_experiment_hook_called_when_an_experiment_is_applied():
    with loaded_extension(RecordingExt) as (dashboard, extension):
        extension.calls.clear()
        dashboard.experiment_manager.applied_entry.emit('an_experiment')
        assert extension.calls == [('do_things_after_experiment_set', 'an_experiment')]


def test_quit_fun_is_a_guard():
    with loaded_extension(RecordingExt) as (dashboard, extension):
        extension.can_quit = False
        extension.mainwindow.show()
        assert extension.quit_fun() is False
        assert extension.mainwindow.isVisible()  # refused: nothing was closed

        extension.can_quit = True
        assert extension.quit_fun() is True
        assert not extension.mainwindow.isVisible()


def test_default_quit_guard_refuses():
    class NoGuard(CustomExt):
        def __init__(self, parent, dashboard):
            super().__init__(parent, dashboard)
            self.setup_ui()

    with loaded_extension(NoGuard) as (dashboard, extension):
        assert extension.quit_fun() is False


def test_stop_must_be_reimplemented():
    with loaded_extension(RecordingExt) as (dashboard, extension):
        with pytest.raises(NotImplementedError):
            extension.stop()


def test_app_toolbars():
    with loaded_extension(RecordingExt) as (dashboard, extension):
        assert extension.get_app_toolbars() == [extension.toolbar]

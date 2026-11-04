# -*- coding: utf-8 -*-
"""
Created the 16/09/2026

@author: Constant Schouder
"""
import pytest
from qtpy import QtWidgets

from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.managers.workflow_manager import bind_transition, action_name_for
from pymodaq_gui.managers.standard_workflow import (
    StandardTransitions, standard_workflow, bind_standard_workflow_actions, bind_pause_action)


class TestStandardWorkflow:
    """ The template: start/pause/resume/stop/finished over IDLE/RUNNING/PAUSED/STOPPING. """

    def test_starts_idle(self, qtbot):
        workflow = standard_workflow()
        assert not workflow.can_trigger(StandardTransitions.PAUSE)
        assert not workflow.can_trigger(StandardTransitions.STOP)
        assert workflow.can_trigger(StandardTransitions.START)

    def test_full_lifecycle(self, qtbot):
        workflow = standard_workflow()

        assert workflow.trigger(StandardTransitions.START)
        assert workflow.can_trigger(StandardTransitions.PAUSE)
        assert workflow.can_trigger(StandardTransitions.STOP)
        assert not workflow.can_trigger(StandardTransitions.START)

        assert workflow.trigger(StandardTransitions.PAUSE)
        assert workflow.can_trigger(StandardTransitions.RESUME)
        assert workflow.can_trigger(StandardTransitions.STOP)

        assert workflow.trigger(StandardTransitions.RESUME)
        assert workflow.can_trigger(StandardTransitions.PAUSE)

        assert workflow.trigger(StandardTransitions.STOP)
        assert not workflow.can_trigger(StandardTransitions.STOP)  # already stopping

        assert workflow.trigger(StandardTransitions.FINISHED)
        assert workflow.can_trigger(StandardTransitions.START)  # back to idle

    def test_stop_is_legal_directly_from_paused(self, qtbot):
        workflow = standard_workflow()
        workflow.trigger(StandardTransitions.START)
        workflow.trigger(StandardTransitions.PAUSE)
        assert workflow.trigger(StandardTransitions.STOP)

    def test_pause_illegal_when_idle(self, qtbot):
        workflow = standard_workflow()
        assert not workflow.trigger(StandardTransitions.PAUSE)

    def test_finished_is_legal_directly_from_running(self, qtbot):
        """ A worker finishing on its own (all steps done, a timeout, a step failure) never
        goes through 'stop' at all -- it confirms completion straight from RUNNING, with no
        stop request on the app side. Generic to any acquisition-style workflow, found by
        porting daq_scan. """
        workflow = standard_workflow()
        workflow.trigger(StandardTransitions.START)
        assert workflow.trigger(StandardTransitions.FINISHED)
        assert workflow.state == 'IDLE'


@pytest.fixture
def action_manager(qtbot):
    return ActionManager(toolbar=QtWidgets.QToolBar(), menu=QtWidgets.QMenu())


class TestBindStandardWorkflowActions:
    """ The template-specific binder: start/stop plus the pause/resume
    toggle merge -- NOT meant to work on an arbitrary graph. """

    def test_registers_the_three_actions(self, qtbot, action_manager):
        workflow = standard_workflow()
        bind_standard_workflow_actions(action_manager, workflow)
        assert action_manager.has_action('start')
        assert action_manager.has_action('stop')
        assert action_manager.has_action('pause')

    def test_non_default_workflow_gets_namespaced_action_names(self, qtbot, action_manager):
        workflow = standard_workflow('seq1')
        bind_standard_workflow_actions(action_manager, workflow)
        assert action_manager.has_action('seq1_start')
        assert not action_manager.has_action('start')

    def test_two_workflows_share_one_action_manager_without_collision(self, qtbot, action_manager):
        main = standard_workflow()
        seq1 = standard_workflow('seq1')
        bind_standard_workflow_actions(action_manager, main)
        bind_standard_workflow_actions(action_manager, seq1)

        main.trigger(StandardTransitions.START)

        assert not action_manager.is_action_enabled('start')
        assert action_manager.is_action_enabled('seq1_start')  # untouched by main's transition

    def test_initial_sync_on_bind(self, qtbot, action_manager):
        workflow = standard_workflow()
        bind_standard_workflow_actions(action_manager, workflow)
        assert action_manager.is_action_enabled('start')
        assert not action_manager.is_action_enabled('stop')
        assert not action_manager.is_action_enabled('pause')

    def test_clicking_start_action_triggers_the_workflow(self, qtbot, action_manager):
        workflow = standard_workflow()
        bind_standard_workflow_actions(action_manager, workflow)
        action_manager.get_action('start').trigger()
        assert workflow.state == 'RUNNING'
        assert action_manager.is_action_enabled('stop')
        assert not action_manager.is_action_enabled('start')

    def test_pause_action_toggles_pause_and_resume(self, qtbot, action_manager):
        workflow = standard_workflow()
        bind_standard_workflow_actions(action_manager, workflow)
        action_manager.get_action('start').trigger()

        action_manager.get_action('pause').trigger()
        assert workflow.state == 'PAUSED'
        assert action_manager.is_action_checked('pause')

        action_manager.get_action('pause').trigger()  # same button, now resumes
        assert workflow.state == 'RUNNING'
        assert not action_manager.is_action_checked('pause')

    def test_bind_works_on_a_workflow_extended_beyond_the_template(self, qtbot, action_manager):
        """ bind_standard_workflow_actions only knows START/PAUSE/RESUME/STOP
        by name -- it should not care that 'custom' also has an ERROR
        state/'fail' transition it knows nothing about. """
        workflow = standard_workflow('custom')
        workflow.add_transition('fail', ['RUNNING'], 'ERROR')
        bind_standard_workflow_actions(action_manager, workflow)

        workflow.trigger(StandardTransitions.START)
        workflow.trigger('fail')

        assert workflow.state == 'ERROR'
        assert not action_manager.is_action_enabled('custom_stop')
        assert not action_manager.is_action_enabled('custom_start')

    def test_extended_transition_bound_separately_via_generic_primitive(self, qtbot, action_manager):
        """ e.g. an extra 'fail' transition bolted onto standard_workflow()
        -- bound with the generic bind_transition() from
        workflow_manager.py (two-line pattern, no dedicated wrapper), not
        this template-specific binder, since 'fail' isn't part of the
        standard start/pause/resume/stop set. """
        workflow = standard_workflow('custom')
        workflow.add_transition('fail', ['RUNNING'], 'ERROR')
        bind_standard_workflow_actions(action_manager, workflow)
        fail_action = action_manager.add_action(action_name_for(workflow, 'fail'), 'Mark failed')
        bind_transition(fail_action, workflow, 'fail')

        assert not action_manager.is_action_enabled('custom_fail')
        action_manager.get_action('custom_start').trigger()
        assert action_manager.is_action_enabled('custom_fail')
        action_manager.get_action('custom_fail').trigger()
        assert workflow.state == 'ERROR'

    def test_returns_the_three_bindings(self, qtbot, action_manager):
        workflow = standard_workflow()
        bindings = bind_standard_workflow_actions(action_manager, workflow)
        assert set(bindings) == {'start', 'stop', 'pause'}
        assert bindings['start'].widget is action_manager.get_action('start')
        assert bindings['stop'].widget is action_manager.get_action('stop')
        assert bindings['pause'].widget is action_manager.get_action('pause')

    def test_actions_have_objectname_set(self, qtbot, action_manager):
        """ No dedicated name field on Binding -- Qt's own
        objectName() is the generic identifier instead. """
        workflow = standard_workflow('scan')
        bind_standard_workflow_actions(action_manager, workflow)
        assert action_manager.get_action('scan_start').objectName() == 'scan_start'
        assert action_manager.get_action('scan_pause').objectName() == 'scan_pause'

    def test_on_start_runs_then_trigger_fires_automatically(self, qtbot, action_manager):
        """ The daq_scan case: 'start' needs real validation first; trigger() then fires
        automatically afterward unless the callback returns False. """
        workflow = standard_workflow()
        calls = []

        def validate(*_):
            calls.append(True)

        bind_standard_workflow_actions(action_manager, workflow, on_start=validate)
        action_manager.get_action('start').trigger()
        assert calls == [True]
        assert workflow.state == 'RUNNING'

    def test_on_start_can_refuse_to_enter_running(self, qtbot, action_manager):
        workflow = standard_workflow()
        bind_standard_workflow_actions(action_manager, workflow, on_start=lambda *_: False)
        action_manager.get_action('start').trigger()
        assert workflow.state == 'IDLE'  # validation refused: trigger() was skipped

    def test_on_stop_runs_then_trigger_fires_automatically(self, qtbot, action_manager):
        workflow = standard_workflow()
        calls = []

        def do_stop(*_):
            calls.append(True)

        bind_standard_workflow_actions(action_manager, workflow, on_stop=do_stop)
        workflow.trigger(StandardTransitions.START)
        action_manager.get_action('stop').trigger()
        assert calls == [True]
        assert workflow.state == 'STOPPING'

    def test_omitting_on_start_on_stop_keeps_the_bare_trigger_default(self, qtbot, action_manager):
        """ Backward compatible: no on_start/on_stop behaves exactly like before. """
        workflow = standard_workflow()
        bind_standard_workflow_actions(action_manager, workflow)
        action_manager.get_action('start').trigger()
        assert workflow.state == 'RUNNING'

    def test_on_pause_resume_runs_then_trigger_any_fires_automatically(self, qtbot, action_manager):
        """ daq_scan's pause_scan(): same single-implementation-for-button-and-script pattern
        as on_start/on_stop -- must NOT call trigger_any() itself, since unlike a single
        trigger() the toggle isn't idempotent (see bind_pause_action's docstring). """
        workflow = standard_workflow()
        calls = []

        def do_pause_resume():
            calls.append(True)

        bind_standard_workflow_actions(action_manager, workflow, on_pause_resume=do_pause_resume)
        workflow.trigger(StandardTransitions.START)
        action_manager.get_action('pause').trigger()
        assert calls == [True]
        assert workflow.state == 'PAUSED'


class TestBindPauseAction:
    """ bind_pause_action() exposed on its own, so a caller hand-wiring
    'start' itself (e.g. daq_scan.py) can still reuse this piece. """

    def test_can_be_used_standalone_without_start_or_stop(self, qtbot, action_manager):
        workflow = standard_workflow()
        binding = bind_pause_action(action_manager, workflow)
        assert action_manager.has_action('pause')
        assert not action_manager.has_action('start')

        workflow.trigger(StandardTransitions.START)
        assert action_manager.is_action_enabled('pause')

        action_manager.get_action('pause').trigger()
        assert workflow.state == 'PAUSED'
        assert action_manager.is_action_checked('pause')
        assert binding.is_bound

# -*- coding: utf-8 -*-
"""
Created the 16/09/2026

@author: Constant Schouder
"""
import pytest
from qtpy import QtWidgets

from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.managers.workflow_manager import (
    Workflow, WorkflowManager, bind_sync, bind_transition, bind_enabled, bind_enabled_to_states,
    bind_enabled_to_transition, action_name_for, DEFAULT_WORKFLOW_NAME)


class TestWorkflowEngine:
    """ The generic FSM: states/transitions are data, nothing hardcoded. """

    def test_first_state_added_is_default(self, qtbot):
        workflow = Workflow('test')
        assert workflow.state is None
        workflow.add_state('A')
        assert workflow.state == 'A'
        workflow.add_state('B')
        assert workflow.state == 'A'  # second add_state doesn't move it

    def test_default_kwarg_overrides(self, qtbot):
        workflow = Workflow('test')
        workflow.add_state('A')
        workflow.add_state('B', default=True)
        assert workflow.state == 'B'

    def test_add_transition_implicitly_registers_states(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        assert workflow.state == 'A'  # from_states[0] was the first state ever seen
        assert workflow.can_trigger('go')
        assert not workflow.can_trigger('back')  # unknown transition

    def test_can_trigger_any_is_an_or(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        workflow.add_transition('back', ['B'], 'A')
        assert workflow.can_trigger_any('go', 'back')  # 'go' is legal from A, 'back' isn't
        assert not workflow.can_trigger_any('back', 'nope')  # neither legal from A
        workflow.trigger('go')
        assert workflow.can_trigger_any('go', 'back')  # now 'back' is legal, 'go' isn't

    def test_can_trigger_all_is_an_and(self, qtbot):
        workflow = Workflow('test')
        workflow.add_state('A')
        workflow.add_transition('go', ['A'], 'B')
        workflow.add_transition('also_from_a', ['A'], 'C')
        assert workflow.can_trigger_all('go', 'also_from_a')  # both legal from A
        assert not workflow.can_trigger_all('go', 'nope')  # 'nope' unknown
        workflow.trigger('go')
        assert not workflow.can_trigger_all('go', 'also_from_a')  # neither legal from B

    def test_can_trigger_defaults_to_any(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        workflow.add_transition('nope_from_a', ['B'], 'C')
        assert workflow.can_trigger('go', 'nope_from_a') == workflow.can_trigger_any('go', 'nope_from_a')

    def test_can_trigger_how_all_delegates_to_can_trigger_all(self, qtbot):
        workflow = Workflow('test')
        workflow.add_state('A')
        workflow.add_transition('go', ['A'], 'B')
        workflow.add_transition('also_from_a', ['A'], 'C')
        assert workflow.can_trigger('go', 'also_from_a', how='all') == \
            workflow.can_trigger_all('go', 'also_from_a')
        assert workflow.can_trigger('go', how='all') is True

    def test_can_trigger_invalid_how_raises(self, qtbot):
        workflow = Workflow('test')
        workflow.add_state('A')
        with pytest.raises(ValueError):
            workflow.can_trigger('go', how='xor')

    def test_trigger_moves_state_and_returns_true(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        assert workflow.trigger('go') is True
        assert workflow.state == 'B'

    def test_trigger_any_fires_the_first_legal_one(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        workflow.add_transition('back', ['B'], 'A')
        assert workflow.trigger_any('back', 'go') is True  # 'back' illegal from A, 'go' isn't
        assert workflow.state == 'B'
        assert workflow.trigger_any('back', 'go') is True  # now 'back' is the legal one
        assert workflow.state == 'A'

    def test_trigger_any_returns_false_if_none_are_legal(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        workflow.add_transition('back', ['B'], 'A')
        assert workflow.trigger_any('back', 'nope') is False
        assert workflow.state == 'A'

    def test_trigger_illegal_from_current_state_is_a_noop(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        workflow.add_transition('back', ['B'], 'A')
        assert workflow.trigger('back') is False  # currently in A, 'back' needs B
        assert workflow.state == 'A'

    def test_trigger_unknown_transition_is_a_noop(self, qtbot):
        workflow = Workflow('test')
        workflow.add_state('A')
        assert workflow.trigger('nope') is False
        assert workflow.state == 'A'

    def test_state_changed_signal(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        seen = []
        workflow.state_changed.connect(lambda old, new: seen.append((old, new)))
        workflow.trigger('go')
        assert seen == [('A', 'B')]

    def test_state_changed_not_emitted_on_illegal_trigger(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        seen = []
        workflow.state_changed.connect(lambda old, new: seen.append((old, new)))
        workflow.trigger('nope')
        assert seen == []

    def test_hooks_fire_in_order_transition_then_exit_then_enter(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        order = []
        workflow.on('go', lambda old, new: order.append('transition'))
        workflow.on_exit('A', lambda old, new: order.append('exit'))
        workflow.on_enter('B', lambda old, new: order.append('enter'))
        workflow.trigger('go')
        assert order == ['transition', 'exit', 'enter']

    def test_hooks_receive_old_and_new_state(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        seen = []
        workflow.on('go', lambda old, new: seen.append((old, new)))
        workflow.trigger('go')
        assert seen == [('A', 'B')]

    def test_hooks_do_not_fire_on_illegal_trigger(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        calls = []
        workflow.on('go', lambda old, new: calls.append(True))
        workflow.trigger('nope')
        assert calls == []

    def test_guard_blocks_trigger_even_when_state_is_legal(self, qtbot):
        workflow = Workflow('test')
        allowed = False
        workflow.add_transition('go', ['A'], 'B', guard=lambda: allowed)
        assert not workflow.can_trigger('go')
        assert workflow.trigger('go') is False
        assert workflow.state == 'A'

        allowed = True
        assert workflow.can_trigger('go')
        assert workflow.trigger('go') is True
        assert workflow.state == 'B'

    def test_guard_none_means_always_allowed_from_a_legal_state(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')  # no guard
        assert workflow.can_trigger('go')

    def test_guard_does_not_run_hooks_or_emit_state_changed_when_it_refuses(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B', guard=lambda: False)
        calls = []
        workflow.on('go', lambda old, new: calls.append(True))
        workflow.state_changed.connect(lambda old, new: calls.append(True))
        workflow.trigger('go')
        assert calls == []

    def test_can_extend_a_graph_with_extra_states_after_the_fact(self, qtbot):
        """ The whole point: nobody needs to edit this module to add a state. """
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        workflow.add_transition('fail', ['B'], 'ERROR')
        errors = []
        workflow.on('fail', lambda old, new: errors.append((old, new)))
        workflow.trigger('go')
        workflow.trigger('fail')
        assert workflow.state == 'ERROR'
        assert errors == [('B', 'ERROR')]

    def test_revalidate_emits_revalidated_not_state_changed(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        state_changes = []
        revalidations = []
        workflow.state_changed.connect(lambda old, new: state_changes.append((old, new)))
        workflow.revalidated.connect(lambda: revalidations.append(True))

        workflow.revalidate()
        assert revalidations == [True]
        assert state_changes == []  # nothing transitioned
        assert workflow.state == 'A'  # unaffected

    def test_none_is_rejected_as_a_state(self, qtbot):
        """ None is the internal sentinel for "no state assigned yet"; ambiguity is why
        this is rejected. """
        workflow = Workflow('test')
        with pytest.raises(ValueError):
            workflow.add_state(None)
        with pytest.raises(ValueError):
            workflow.add_transition('go', ['A'], None)

    def test_empty_transition_name_is_rejected(self, qtbot):
        workflow = Workflow('test')
        with pytest.raises(ValueError):
            workflow.add_transition('', ['A'], 'B')

    def test_exit_hook_still_sees_the_old_state_via_self_state(self, qtbot):
        """ State is only committed right before enter hooks run, so an exit hook
        reading workflow.state directly (not just the old_state arg) still sees the
        state it's leaving. """
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        seen = []
        workflow.on_exit('A', lambda old, new: seen.append(workflow.state))
        workflow.trigger('go')
        assert seen == ['A']

    def test_enter_hook_sees_the_new_state_via_self_state(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        seen = []
        workflow.on_enter('B', lambda old, new: seen.append(workflow.state))
        workflow.trigger('go')
        assert seen == ['B']

    def test_off_removes_a_transition_hook(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        calls = []
        callback = lambda old, new: calls.append(True)
        workflow.on('go', callback)
        workflow.off('go', callback)
        workflow.trigger('go')
        assert calls == []

    def test_off_enter_and_off_exit_remove_their_hooks(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        calls = []
        enter_cb = lambda old, new: calls.append('enter')
        exit_cb = lambda old, new: calls.append('exit')
        workflow.on_enter('B', enter_cb)
        workflow.on_exit('A', exit_cb)
        workflow.off_enter('B', enter_cb)
        workflow.off_exit('A', exit_cb)
        workflow.trigger('go')
        assert calls == []

    def test_off_raises_if_callback_not_registered(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        with pytest.raises(ValueError):
            workflow.off('go', lambda old, new: None)

    def test_transition_enter_exit_hooks_list_registered_callbacks(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        transition_cb = lambda old, new: None
        enter_cb = lambda old, new: None
        exit_cb = lambda old, new: None
        workflow.on('go', transition_cb)
        workflow.on_enter('B', enter_cb)
        workflow.on_exit('A', exit_cb)
        assert workflow.transition_hooks('go') == [transition_cb]
        assert workflow.enter_hooks('B') == [enter_cb]
        assert workflow.exit_hooks('A') == [exit_cb]
        assert workflow.transition_hooks('nope') == []  # unknown name, empty not KeyError


class TestWorkflowManager:

    def test_add_workflow_registers_under_its_own_name(self, qtbot):
        manager = WorkflowManager()
        workflow = Workflow(DEFAULT_WORKFLOW_NAME)
        workflow.add_state('A')
        registered = manager.add_workflow(workflow)
        assert registered is workflow
        assert manager[DEFAULT_WORKFLOW_NAME] is workflow
        assert manager.main is workflow

    def test_add_named_workflow(self, qtbot):
        manager = WorkflowManager()
        workflow = Workflow('seq1')
        workflow.add_state('A')
        manager.add_workflow(workflow)
        assert manager['seq1'] is workflow
        assert manager.main is None  # no 'main' was ever added

    def test_duplicate_name_raises(self, qtbot):
        manager = WorkflowManager()
        manager.add_workflow(Workflow('seq1'))
        with pytest.raises(ValueError):
            manager.add_workflow(Workflow('seq1'))

    def test_len_and_iter(self, qtbot):
        manager = WorkflowManager()
        manager.add_workflow(Workflow(DEFAULT_WORKFLOW_NAME))
        manager.add_workflow(Workflow('seq1'))
        assert len(manager) == 2
        assert {w.name for w in manager} == {DEFAULT_WORKFLOW_NAME, 'seq1'}


@pytest.fixture
def action_manager(qtbot):
    return ActionManager(toolbar=QtWidgets.QToolBar(), menu=QtWidgets.QMenu())


class TestBindSync:
    """ Arbitrary sync_slot (not just setEnabled), optionally with a click. """

    def test_sync_slot_can_write_more_than_one_thing(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        widget = QtWidgets.QPushButton('Widget')
        widget.setCheckable(True)
        writes = []

        def sync_slot(*_):
            writes.append(workflow.state)
            widget.setEnabled(workflow.state == 'A')
            widget.setChecked(workflow.state == 'B')

        bind_sync(widget, workflow, sync_slot)
        assert writes == ['A']
        assert widget.isEnabled() and not widget.isChecked()

        workflow.trigger('go')
        assert writes == ['A', 'B']
        assert not widget.isEnabled() and widget.isChecked()

    def test_click_slot_and_sync_slot_both_wired(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        widget = QtWidgets.QPushButton('Widget')
        clicks = []

        binding = bind_sync(widget, workflow, lambda *_: widget.setEnabled(workflow.state == 'A'),
                            signal_name='clicked', click_slot=lambda *_: clicks.append(True))
        widget.click()
        assert clicks == [True]
        assert workflow.state == 'A'  # click_slot didn't trigger anything itself

        workflow.trigger('go')
        assert not widget.isEnabled()
        binding.unbind()
        widget.click()
        assert clicks == [True]  # unbound: no longer connected

    def test_no_click_when_signal_name_omitted(self, qtbot):
        """ signal_name=None (the default): no click wiring at all, same
        as bind_enabled()/bind_enabled_to_states(). """
        workflow = Workflow('test')
        widget = QtWidgets.QPushButton('Widget')
        bind_sync(widget, workflow, lambda *_: widget.setEnabled(True))
        widget.click()  # must not raise, nothing connected to it


class TestBindTransition:
    """ click -> trigger(transition) by default, enabled synced to
    can_trigger(transition) -- the common single-write bind_sync() shape. """

    def test_wires_a_bare_qaction_with_no_action_manager(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        action = QtWidgets.QAction('Go')

        bind_transition(action, workflow, 'go')
        assert action.isEnabled()  # 'go' is legal from A

        action.trigger()
        assert workflow.state == 'B'
        assert not action.isEnabled()  # 'go' no longer legal from B

    def test_works_on_a_qpushbutton_via_signal_name(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        button = QtWidgets.QPushButton('Go')

        bind_transition(button, workflow, 'go', signal_name='clicked')
        assert button.isEnabled()

        button.click()
        assert workflow.state == 'B'
        assert not button.isEnabled()

    def test_auto_unbinds_when_the_widget_is_destroyed(self, qtbot):
        """ Qt itself guarantees `destroyed` fires exactly once when the
        underlying C++ object goes away (e.g. its parent widget/toolbar
        is torn down) -- not something to re-verify here. What's under
        test is that bind_transition reacts to it: emitting `destroyed`
        directly is the standard way to exercise that reaction without
        fighting deleteLater()'s deferred, event-loop-dependent timing. """
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        action = QtWidgets.QAction('Go')
        binding = bind_transition(action, workflow, 'go')
        assert binding.is_bound

        action.destroyed.emit()
        assert not binding.is_bound

        # no crash trying action.setEnabled() on what's now a dead object
        workflow.trigger('go')
        assert workflow.state == 'B'

    def test_sync_reflects_guard_after_a_successful_transition(self, qtbot):
        """ Drives the engine directly rather than via action.trigger():
        QAction.trigger() on a disabled action emits `triggered` under
        PyQt5 but not under PySide6/likely PyQt6 -- a real cross-backend
        Qt inconsistency, not something to rely on. So the enabled sync
        isn't just cosmetic on those backends: it's load-bearing for the
        click to fire at all, which is exactly why bind_transition keeps
        it live via state_changed. """
        workflow = Workflow('test')
        allowed = False
        workflow.add_transition('go', ['A'], 'B', guard=lambda: allowed)
        action = QtWidgets.QAction('Go')
        bind_transition(action, workflow, 'go')
        assert not action.isEnabled()  # guard denies

        allowed = True
        assert workflow.can_trigger('go')  # the engine sees the guard change immediately
        assert workflow.trigger('go')
        assert workflow.state == 'B'
        assert not action.isEnabled()  # resynced: 'go' isn't legal from B either, guard aside

    def test_resync_picks_up_a_guard_change_with_no_state_change(self, qtbot):
        workflow = Workflow('test')
        allowed = [False]
        workflow.add_transition('go', ['A'], 'B', guard=lambda: allowed[0])
        action = QtWidgets.QAction('Go')
        binding = bind_transition(action, workflow, 'go')
        assert not action.isEnabled()

        allowed[0] = True
        assert not action.isEnabled()  # stale: no state_changed fired

        binding.resync()
        assert action.isEnabled()

    def test_workflow_revalidate_also_resyncs_this_binding(self, qtbot):
        workflow = Workflow('test')
        allowed = [False]
        workflow.add_transition('go', ['A'], 'B', guard=lambda: allowed[0])
        action = QtWidgets.QAction('Go')
        bind_transition(action, workflow, 'go')
        assert not action.isEnabled()

        allowed[0] = True
        workflow.revalidate()
        assert action.isEnabled()

    def test_resync_is_a_noop_after_unbind(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        action = QtWidgets.QAction('Go')
        binding = bind_transition(action, workflow, 'go')
        binding.unbind()
        binding.resync()  # must not raise, and must not touch the (possibly dead) widget

    def test_click_slot_override_runs_instead_of_bare_trigger(self, qtbot):
        """ The 'start' case: validation with real side effects has to run on click, and only
        that callback decides whether/when to actually call trigger(). """
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        action = QtWidgets.QAction('Go')
        calls = []

        def validate_then_go(*_):
            calls.append(True)
            # validation succeeds: decide to trigger ourselves
            workflow.trigger('go')

        bind_transition(action, workflow, 'go', click_slot=validate_then_go)
        action.trigger()
        assert calls == [True]
        assert workflow.state == 'B'  # the callback's own trigger() call took effect

    def test_click_slot_override_can_refuse_to_trigger(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        action = QtWidgets.QAction('Go')

        def validation_fails(*_):
            pass  # never calls trigger()

        bind_transition(action, workflow, 'go', click_slot=validation_fails)
        action.trigger()
        assert workflow.state == 'A'  # nothing happened -- the callback chose not to trigger

    def test_enabled_sync_is_unchanged_by_a_click_slot_override(self, qtbot):
        """ Whether click bare-triggers or runs a custom callback, the enabled state still
        tracks can_trigger(transition) exactly the same way. """
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        action = QtWidgets.QAction('Go')
        bind_transition(action, workflow, 'go', click_slot=lambda *_: workflow.trigger('go'))
        assert action.isEnabled()

        action.trigger()
        assert workflow.state == 'B'
        assert not action.isEnabled()  # 'go' no longer legal from B

    def test_unbind_disconnects_a_click_slot_override_too(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        action = QtWidgets.QAction('Go')
        calls = []
        binding = bind_transition(action, workflow, 'go', click_slot=lambda *_: calls.append(True))

        binding.unbind()
        action.trigger()
        assert calls == []


class TestBindTransitionOnAnActionManagerAction:
    """ bind_transition() used on an action created via
    action_manager.add_action(action_name_for(...), ...) -- the
    two-line pattern that replaces the old bind_transition_action()
    wrapper: no dedicated function, just the two primitives composed
    at the call site. """

    def test_binds_an_arbitrary_transition_on_an_arbitrary_graph(self, qtbot, action_manager):
        workflow = Workflow(DEFAULT_WORKFLOW_NAME)
        workflow.add_transition('go', ['A'], 'B')
        name = action_name_for(workflow, 'go')
        action = action_manager.add_action(name, 'Go')
        binding = bind_transition(action, workflow, 'go')
        assert binding.widget is action
        assert action_manager.has_action('go')
        assert action_manager.is_action_enabled('go')

        action_manager.get_action('go').trigger()
        assert workflow.state == 'B'
        assert not action_manager.is_action_enabled('go')  # 'go' no longer legal from B

    def test_action_name_for_namespaces_non_default_workflow(self, qtbot, action_manager):
        workflow = Workflow('seq1')
        workflow.add_transition('go', ['A'], 'B')
        name = action_name_for(workflow, 'go')
        assert name == 'seq1_go'
        action = action_manager.add_action(name, 'Go')
        bind_transition(action, workflow, 'go')
        assert action_manager.has_action('seq1_go')

    def test_unbind_disconnects_click_and_sync(self, qtbot, action_manager):
        workflow = Workflow(DEFAULT_WORKFLOW_NAME)
        workflow.add_transition('go', ['A'], 'B')
        workflow.add_transition('back', ['B'], 'A')
        action = action_manager.add_action(action_name_for(workflow, 'go'), 'Go')
        binding = bind_transition(action, workflow, 'go')
        assert binding.is_bound

        binding.unbind()
        assert not binding.is_bound

        # click no longer drives the workflow...
        action_manager.get_action('go').trigger()
        assert workflow.state == 'A'

        # ...and the action's enabled flag is frozen where it was, no
        # longer resynced when the workflow transitions via other means
        workflow.trigger('go')
        assert workflow.state == 'B'
        assert action_manager.is_action_enabled('go')  # stale: still True from before unbind

    def test_unbind_is_safe_to_call_twice(self, qtbot, action_manager):
        workflow = Workflow(DEFAULT_WORKFLOW_NAME)
        workflow.add_transition('go', ['A'], 'B')
        action = action_manager.add_action(action_name_for(workflow, 'go'), 'Go')
        binding = bind_transition(action, workflow, 'go')
        binding.unbind()
        binding.unbind()  # must not raise
        assert not binding.is_bound


class TestBindEnabled:
    """ The general form bind_enabled_to_states()/bind_enabled_to_transition()
    are thin wrappers over -- an arbitrary predicate, for a condition
    neither canned one covers (e.g. daq_scan's 'ini_positions': a state
    check *and* an external condition). """

    def test_enabled_reflects_an_arbitrary_predicate(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        widget = QtWidgets.QPushButton('Widget')
        external_ok = [True]

        bind_enabled(widget, workflow, lambda: workflow.state == 'A' and external_ok[0])
        assert widget.isEnabled()

        workflow.trigger('go')
        assert not widget.isEnabled()  # state half of the predicate now false

    def test_external_half_of_the_predicate_needs_revalidate(self, qtbot):
        """ Like a guard, the external half of a composite predicate can
        change with no transition of its own -- state_changed alone
        won't pick it up, revalidate() is what resyncs it. """
        workflow = Workflow('test')
        widget = QtWidgets.QPushButton('Widget')
        external_ok = [True]

        bind_enabled(widget, workflow, lambda: external_ok[0])
        assert widget.isEnabled()

        external_ok[0] = False
        assert widget.isEnabled()  # stale: nothing told the binding to recheck

        workflow.revalidate()
        assert not widget.isEnabled()

    def test_no_transition_is_ever_triggered_by_this_binding(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        widget = QtWidgets.QPushButton('Widget')
        bind_enabled(widget, workflow, lambda: True)
        widget.click()
        assert workflow.state == 'A'  # unaffected


class TestBindEnabledToStates:
    """ The state-membership analog of bind_transition(): no click side,
    just widget.setEnabled() kept synced to `workflow.state in states`. """

    def test_enabled_only_while_in_one_of_the_given_states(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        workflow.add_transition('back', ['B'], 'A')
        widget = QtWidgets.QPushButton('Init')

        bind_enabled_to_states(widget, workflow, ['A'])
        assert widget.isEnabled()  # currently in A

        workflow.trigger('go')
        assert not widget.isEnabled()  # now in B, not in {A}

        workflow.trigger('back')
        assert widget.isEnabled()  # back in A

    def test_accepts_several_states(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        workflow.add_transition('fail', ['B'], 'ERROR')
        widget = QtWidgets.QPushButton('Widget')

        bind_enabled_to_states(widget, workflow, ['A', 'B'])
        assert widget.isEnabled()

        workflow.trigger('go')
        assert widget.isEnabled()  # B is also in the allowed set

        workflow.trigger('fail')
        assert not widget.isEnabled()  # ERROR isn't

    def test_no_transition_is_ever_triggered_by_this_binding(self, qtbot):
        """ Unlike bind_transition(), there's no click side at all: nothing
        here should ever call workflow.trigger(). """
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        widget = QtWidgets.QPushButton('Widget')
        bind_enabled_to_states(widget, workflow, ['A'])
        widget.click()
        assert workflow.state == 'A'  # unaffected

    def test_auto_unbinds_when_the_widget_is_destroyed(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        widget = QtWidgets.QPushButton('Widget')
        binding = bind_enabled_to_states(widget, workflow, ['A'])
        assert binding.is_bound

        widget.destroyed.emit()
        assert not binding.is_bound

        # no crash trying widget.setEnabled() on what's now a dead object
        workflow.trigger('go')
        assert workflow.state == 'B'

    def test_unbind_stops_resync_and_is_safe_to_call_twice(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        widget = QtWidgets.QPushButton('Widget')
        binding = bind_enabled_to_states(widget, workflow, ['A'])

        binding.unbind()
        assert not binding.is_bound
        binding.unbind()  # must not raise

        # widget's enabled flag is frozen where it was, no longer resynced
        workflow.trigger('go')
        assert workflow.state == 'B'
        assert widget.isEnabled()  # stale: still True from before unbind

    def test_resync_is_safe_and_recomputes_from_current_state(self, qtbot):
        """ bind_enabled_to_states() has no guard-like external dependency of
        its own (state membership is all there is), so resync() here just
        has to be safe to call and reflect whatever the current state is
        -- the meaningful "picked up a change state_changed didn't"
        exercise belongs to bind_enabled_to_transition's guard, tested
        under TestBindEnabledToTransition. """
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        widget = QtWidgets.QPushButton('Widget')
        binding = bind_enabled_to_states(widget, workflow, ['A'])
        assert widget.isEnabled()

        binding.resync()
        assert widget.isEnabled()  # unchanged: still in A

    def test_workflow_revalidate_also_resyncs_this_binding(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        widget = QtWidgets.QPushButton('Widget')
        bind_enabled_to_states(widget, workflow, ['A'])
        assert widget.isEnabled()

        workflow.revalidate()  # must not raise, and enabled state stays correct
        assert widget.isEnabled()


class TestBindEnabledToTransition:
    """ The transition-legality analog of bind_enabled_to_states(): no
    click side, just widget.setEnabled() kept synced to
    `workflow.can_trigger(transition)`. """

    def test_enabled_reflects_can_trigger(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        widget = QtWidgets.QPushButton('Widget')

        bind_enabled_to_transition(widget, workflow, 'go')
        assert widget.isEnabled()

        workflow.trigger('go')
        assert not widget.isEnabled()  # 'go' no longer legal from B

    def test_reflects_a_guard_too(self, qtbot):
        workflow = Workflow('test')
        allowed = False
        workflow.add_transition('go', ['A'], 'B', guard=lambda: allowed)
        widget = QtWidgets.QPushButton('Widget')

        bind_enabled_to_transition(widget, workflow, 'go')
        assert not widget.isEnabled()  # state is legal but guard refuses

    def test_resync_picks_up_a_guard_change_with_no_state_change(self, qtbot):
        """ The whole point of .resync(): a guard's external condition can
        flip without any transition ever firing, so state_changed alone
        never re-syncs it -- the caller must call .resync() itself from
        wherever that external event is handled. """
        workflow = Workflow('test')
        allowed = [False]
        workflow.add_transition('go', ['A'], 'B', guard=lambda: allowed[0])
        widget = QtWidgets.QPushButton('Widget')
        binding = bind_enabled_to_transition(widget, workflow, 'go')
        assert not widget.isEnabled()

        allowed[0] = True
        assert not widget.isEnabled()  # stale: no state_changed fired

        binding.resync()
        assert widget.isEnabled()

    def test_workflow_revalidate_also_resyncs_this_binding(self, qtbot):
        """ The common-case counterpart to test_resync_picks_up_a_guard_change...:
        a single workflow.revalidate() call from wherever entry_applied (or
        whatever the guard reads) changed, rather than the caller keeping a
        reference to this specific binding just to call .resync() on it. """
        workflow = Workflow('test')
        allowed = [False]
        workflow.add_transition('go', ['A'], 'B', guard=lambda: allowed[0])
        widget = QtWidgets.QPushButton('Widget')
        bind_enabled_to_transition(widget, workflow, 'go')
        assert not widget.isEnabled()

        allowed[0] = True
        workflow.revalidate()
        assert widget.isEnabled()

    def test_no_transition_is_ever_triggered_by_this_binding(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        widget = QtWidgets.QPushButton('Widget')
        bind_enabled_to_transition(widget, workflow, 'go')
        widget.click()
        assert workflow.state == 'A'  # unaffected

    def test_auto_unbinds_when_the_widget_is_destroyed(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        widget = QtWidgets.QPushButton('Widget')
        binding = bind_enabled_to_transition(widget, workflow, 'go')
        assert binding.is_bound

        widget.destroyed.emit()
        assert not binding.is_bound

        # no crash trying widget.setEnabled() on what's now a dead object
        workflow.trigger('go')
        assert workflow.state == 'B'

    def test_unbind_stops_resync_and_is_safe_to_call_twice(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        widget = QtWidgets.QPushButton('Widget')
        binding = bind_enabled_to_transition(widget, workflow, 'go')

        binding.unbind()
        assert not binding.is_bound
        binding.unbind()  # must not raise

        workflow.trigger('go')
        assert workflow.state == 'B'
        assert widget.isEnabled()  # stale: still True from before unbind

    def test_resync_is_a_noop_after_unbind(self, qtbot):
        workflow = Workflow('test')
        workflow.add_transition('go', ['A'], 'B')
        widget = QtWidgets.QPushButton('Widget')
        binding = bind_enabled_to_transition(widget, workflow, 'go')
        binding.unbind()
        binding.resync()  # must not raise, and must not touch the (possibly dead) widget

import copy
import logging

import pytest

from qtpy import QtCore

from pymodaq_data import DataToExport

from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltFactory, ElementError
from pymodaq.extensions.sequencer.utilities.elements.button import AddButtonPlaceholder
from pymodaq.extensions.sequencer.utilities.elements.choice import ChoiceElt
from pymodaq.extensions.sequencer.utilities.elements.group import GroupElt
from pymodaq.extensions.sequencer.utilities.elements.root import RootElt
from pymodaq.extensions.sequencer.utilities.elements.switch import SwitchElt
from pymodaq.extensions.sequencer.utilities.elements.wait import WaitElt
from pymodaq.extensions.sequencer.utilities.holders.rule import CONTINUE, MANUAL_OVERRIDE_ID
from pymodaq.extensions.sequencer.utilities.holders.modules_manager_binding import ModulesManagerBinding
from pymodaq.extensions.sequencer.utilities.elements.grab import GrabElt
from pymodaq.extensions.sequencer.utilities.elements.while_loop import WhileElt
from pymodaq.extensions.sequencer.utilities.states import TrackedTransition
from pymodaq.utils.managers.modules_manager import ModulesManagerParam
from pymodaq.extensions.sequencer.models.composite_choice_model import CompositeChoiceModel

seq_factory = SeqEltFactory()


class FakeDetector:
    def __init__(self, title):
        self.title = title


class FakeModulesManager:
    def __init__(self, titles):
        self.detectors_all = [FakeDetector(t) for t in titles]
        self.actuators_all = []


class FakeAppliedEntry:
    def __init__(self):
        self._slots = []

    def connect(self, slot):
        self._slots.append(slot)


class FakeExperimentManager:
    def __init__(self):
        self.applied_entry = FakeAppliedEntry()


class FakeDashboard:
    def __init__(self, titles):
        self.modules_manager = FakeModulesManager(titles)
        self.experiment_manager = FakeExperimentManager()


class TestElements:

    def test_registered_elements(self, ):
        for elt in ('button', 'choice', 'grab', 'group', 'move', 'repeat', 'root', 'scanner',
                   'sequence', 'state', 'switch', 'wait', 'while'):
            assert elt in seq_factory.elements

    def test_grab_elt_construction(self, qtbot):
        """ Regression test: GrabElt used to reference ModulesManager settings children
        ('probe_data', 'test_actuator') that don't exist, raising a KeyError on every
        construction. It should only hide the actuator-related children (it's detector-only).
        """
        elt = GrabElt(1)
        settings = elt.modules_manager.settings
        assert settings.child(ModulesManagerParam.ACTUATORS).opts['visible'] is False
        assert settings.child(ModulesManagerParam.PROBE_ACTUATORS).opts['visible'] is False
        assert settings.child(ModulesManagerParam.PROBE_ACTUATORS_RESULTS).opts['visible'] is False
        assert settings.child(ModulesManagerParam.DETECTORS).opts['visible'] is True

    def test_choice_elt_default_model_is_trivial(self, qtbot):
        """ Regression: ChoiceElt's default used to resolve to choice_factory.models[0] -
        whichever choice_models/*.py file pkgutil happens to import first, alphabetically.
        Harmless while that was always 'false', but adding composite_choice_model.py here makes
        'composite' sort first, which would otherwise silently flip every new ChoiceElt's
        default from the trivial 'false' model to the much heavier composite one. """
        elt = ChoiceElt(1)
        assert elt.choice_model.model_name == 'false'


class TestModulesManagerBinding:
    """ filter_selected: the "preserve selection across a catalog refresh" logic shared by
    GrabElt and ThresholdChoiceModel - factored out after it was independently hand-rolled
    (and once got it wrong: force-selecting everything instead of preserving the user's
    choice) by more than one of them."""

    def test_keeps_order_and_drops_unavailable(self):
        result = ModulesManagerBinding.filter_selected(['det1', 'det2', 'det3'], ['det3', 'det1'])
        assert result == ['det1', 'det3']

    def test_nothing_dropped_when_all_available(self):
        result = ModulesManagerBinding.filter_selected(['det1', 'det2'], ['det1', 'det2', 'det3'])
        assert result == ['det1', 'det2']


class FakeAction(QtCore.QObject):
    triggered = QtCore.Signal(bool)


class TestCompositeStateTransitions:
    """ CompositeState.clear_transitions() - called by Sequence.recursive_disconnect_elts()
    before every run, even the first, since the tree may have been edited since the last one -
    only tears down transitions explicitly registered as ephemeral via
    track_transition()/add_external_transition(); anything added directly via addTransition()
    (an element's own permanent behavior, e.g. a SwitchElt Rule's go_to transition) survives by
    construction, with no opt-in needed. This replaces an earlier, inverted design
    (transitions_to_keep, an opt-in allowlist for permanent transitions) that caused the
    stuck-ChoiceElt bug: a permanent transition not added to that allowlist was wiped the same
    as the genuinely ephemeral ones around it.

    Regression coverage for a second bug found while fixing that one: addTransition() returns
    None (not the transition) when passed an already-built transition object rather than a
    (signal, target) pair, so track_transition()/add_external_transition() were appending None
    to the ephemeral list - meaning clear_transitions() never actually removed anything through
    that path, and the (now-deleted) blunt "clear everything not kept" sweep was silently doing
    all the real work.
    """

    def test_tracked_transitions_dont_leak_across_repeated_clears(self, qtbot):
        root = RootElt()
        elt = WaitElt(1, parent=root)
        target = WaitElt(2, parent=root)
        action = FakeAction()

        counts = []
        for _ in range(4):
            elt.mstate.clear_state_and_transitions()
            elt.mstate.add_external_transition(action.triggered, target.mstate)
            counts.append(len(elt.mstate.transitions()))

        assert counts == [counts[0]] * len(counts)

    def test_untracked_transition_survives_the_clear(self, qtbot):
        root = RootElt()
        elt = WaitElt(1, parent=root)
        target = WaitElt(2, parent=root)
        action = FakeAction()

        permanent = TrackedTransition(action.triggered, elt.mstate, target.mstate)
        elt.mstate.addTransition(permanent)

        elt.mstate.clear_state_and_transitions()

        assert permanent in elt.mstate.transitions()


class TestChoiceElt:
    """ ChoiceElt's True/False branching: the permanently-locked 2-Rule case of SwitchElt's
    general Rule list (see TestSwitchElt, below) - one Rule holds the pluggable ChoiceModel
    and the True target, the mandatory fallback Rule holds the False target. Regression
    coverage for three bugs the composition refactor surfaced and fixed, none of which had
    prior test coverage: a
    composition refactor surfaced and fixed, none of which had prior test coverage: a
    copy-paste error message, a None-target crash, and a dashboard refresh that silently wiped
    the user's detector selection."""

    def test_go_to_true_false_round_trip(self, qtbot):
        root = RootElt()
        elt = ChoiceElt(1, parent=root)
        waits = [WaitElt(10 + i, parent=root) for i in range(2)]
        root._children = [elt] + waits
        elt.go_to_true = waits[0].id
        elt.go_to_false = waits[1].id

        saved = elt.to_dict_custom()
        reloaded = ChoiceElt(1, parent=root)
        reloaded.from_dict_custom(dict(saved))

        assert reloaded.to_dict_custom() == saved
        assert reloaded == elt

    def test_branch_transitions_survive_sequence_restart(self, qtbot):
        """ Regression: Sequence.start_sequence() clears per-run tree wiring on every element's
        mstate before each run (recursive_disconnect_elts, so a stale pass's wiring doesn't leak
        into the next one) - CompositeState.clear_transitions() only tears down transitions
        explicitly registered as ephemeral (track_transition()/add_external_transition()).
        Rule's True/False ValueTransitions are added with a plain addTransition(), so they're
        permanent by construction and were never at risk from this clear - but that wasn't
        always true: this test used to catch the inverse bug, where they *were* wiped (via an
        opt-in transitions_to_keep allowlist they weren't registered in) and never recreated,
        leaving the element stuck forever after the first Start.
        """
        root = RootElt()
        elt = ChoiceElt(1, parent=root)
        wait_t = WaitElt(2, parent=root)
        wait_f = WaitElt(3, parent=root)
        root._children = [elt, wait_t, wait_f]
        elt.go_to_true = wait_t.id
        elt.go_to_false = wait_f.id

        elt.mstate.clear_state_and_transitions()  # what recursive_disconnect_elts() does

        transitions = elt.mstate.transitions()
        assert elt._condition_rule.transition in transitions
        assert elt.fallback_rule.transition in transitions
        assert elt._condition_rule.transition.targetState() is wait_t.mstate
        assert elt.fallback_rule.transition.targetState() is wait_f.mstate

    def test_check_set_is_valid_names_the_actual_missing_branch(self, qtbot):
        """ Regression: both branches' error messages used to say 'False', even when True's
        own target was the one that was broken. """
        root = RootElt()
        elt = ChoiceElt(1, parent=root)
        wait = WaitElt(10, parent=root)
        root._children = [elt, wait]
        elt.go_to_false = wait.id
        # go_to_true is never set - its target stays unresolved
        with pytest.raises(ElementError, match='True'):
            elt.check_set_is_valid()

    def test_update_target_states_tolerates_an_unresolved_target(self, qtbot):
        """ Regression: used to crash with AttributeError instead of leaving a transition's
        target unresolved when the stored id no longer refers to a real element. """
        root = RootElt()
        elt = ChoiceElt(1, parent=root)
        wait = WaitElt(10, parent=root)
        root._children = [elt, wait]
        elt.go_to_true = wait.id
        elt.go_to_false = 9999  # never resolves to a real element
        for rule in elt.rules:
            rule.update_target_state()  # must not raise

    def test_continue_branch_round_trips(self, qtbot):
        """ A branch set to CONTINUE serializes as the plain string, not an id - no special
        casing needed in to_dict_custom/from_dict_custom. """
        root = RootElt()
        elt = ChoiceElt(1, parent=root)
        wait = WaitElt(10, parent=root)
        root._children = [elt, wait]
        elt.go_to_true = CONTINUE
        elt.go_to_false = wait.id

        saved = elt.to_dict_custom()
        assert saved['go_to_true'] == CONTINUE
        reloaded = ChoiceElt(1, parent=root)
        reloaded.from_dict_custom(dict(saved))
        assert reloaded.go_to_true == CONTINUE
        assert reloaded == elt

    def test_continue_branch_resolves_to_next_state(self, qtbot):
        """ CONTINUE resolves against elt.mstate.next_state - whatever
        Sequence.recursive_connect_elts() wires this element's own forward progress to - not a
        specific element id. """
        root = RootElt()
        elt = ChoiceElt(1, parent=root)
        wait_a = WaitElt(2, parent=root)
        wait_b = WaitElt(3, parent=root)
        root._children = [elt, wait_a, wait_b]
        elt.go_to_true = CONTINUE
        elt.go_to_false = wait_b.id

        elt.mstate.next_state = wait_a.mstate  # what recursive_connect_elts() would set
        for rule in elt.rules:
            rule.update_target_state()

        assert elt._condition_rule.transition.targetState() is wait_a.mstate

    def test_continue_branch_always_re_resolves(self, qtbot):
        """ Unlike a real element id (only resolved when still unset), a CONTINUE branch must
        be re-resolved every call: what "continue" points at can change across runs if the tree
        was restructured in between, so a stale, already-resolved target can't be left to
        stick. """
        root = RootElt()
        elt = ChoiceElt(1, parent=root)
        wait_a = WaitElt(2, parent=root)
        wait_b = WaitElt(3, parent=root)
        root._children = [elt, wait_a, wait_b]
        elt.go_to_true = CONTINUE
        elt.go_to_false = wait_b.id

        elt.mstate.next_state = wait_a.mstate
        for rule in elt.rules:
            rule.update_target_state()
        assert elt._condition_rule.transition.targetState() is wait_a.mstate

        # tree restructured: a new element now follows elt instead
        inserted = WaitElt(4, parent=root)
        elt.mstate.next_state = inserted.mstate
        for rule in elt.rules:
            rule.update_target_state()
        assert elt._condition_rule.transition.targetState() is inserted.mstate

    def test_combo_index_vs_deprecated_index_stay_independent(self, qtbot):
        """ The target combo's own index numbering (0 = Continue, 1+ = real elements) must not
        leak into the deprecated set_go_to_true/set_go_to_false's plain index into
        get_ids(...) with no Continue offset - sharing one numbering would silently break
        anyone still using the deprecated index-based setters. """
        root = RootElt()
        elt = ChoiceElt(1, parent=root)
        wait_a = WaitElt(2, parent=root)
        wait_b = WaitElt(3, parent=root)
        root._children = [elt, wait_a, wait_b]
        ids = elt.get_ids(without_ids=(elt.id,), without_types=(AddButtonPlaceholder,))

        assert elt._combo_index_to_value(0) == CONTINUE
        assert ids[0] == wait_a.id
        assert elt._combo_index_to_value(1) == ids[0]

    def test_dashboard_refresh_preserves_detector_selection(self, qtbot):
        """ Regression: ThresholdChoiceModel.updated_module_manager used to force-select every
        detector on each dashboard refresh (ModulesManager.detectors_all's setter wipes the
        selection as a side effect) instead of preserving-and-filtering the user's choice, the
        way GrabElt.filter_selected_wrt_manager already did correctly. """
        elt = ChoiceElt(1)
        elt.choice_model = 'threshold'
        model = elt.choice_model
        model.settings['detectors'] = dict(all_items=['det1', 'det2'], selected=['det1'])

        elt.dashboard = FakeDashboard(['det1', 'det2'])
        elt.do_things_with_dashboard()

        assert model.settings['detectors']['selected'] == ['det1']


class TestSwitchElt:
    """ SwitchElt's general N-way Rule list: an ordered (condition, target) Rule list,
    evaluated top to bottom, first match wins, with a mandatory always-matching fallback
    Rule. ChoiceElt (TestChoiceElt, above) is the permanently-locked 2-Rule case of this. """

    def test_starts_with_only_the_fallback(self, qtbot):
        """ A brand-new SwitchElt starts minimal: just the fallback, nothing to configure. """
        elt = SwitchElt(1)
        assert len(elt.rules) == 1
        assert elt.rules[0] is elt.fallback_rule
        assert elt.fallback_rule.condition.model.model_name == 'true'

    def test_add_rule_inserts_before_the_fallback(self, qtbot):
        elt = SwitchElt(1)
        rule = elt.add_rule()
        assert elt.rules == [rule, elt.fallback_rule]

        rule_2 = elt.add_rule()
        assert elt.rules == [rule, rule_2, elt.fallback_rule]

    def test_remove_rule(self, qtbot):
        elt = SwitchElt(1)
        rule = elt.add_rule()
        other = elt.add_rule()
        elt.remove_rule(rule.id)
        assert elt.rules == [other, elt.fallback_rule]

    def test_remove_rule_cannot_remove_the_fallback(self, qtbot):
        elt = SwitchElt(1)
        elt.remove_rule(elt.fallback_rule.id)
        assert elt.rules == [elt.fallback_rule]

    def test_first_matching_rule_wins(self, qtbot):
        root = RootElt()
        elt = SwitchElt(1, parent=root)
        targets = [WaitElt(10 + i, parent=root) for i in range(3)]
        root._children = [elt] + targets

        rule_1 = elt.add_rule()
        rule_1.condition.model = 'false'
        rule_1.go_to = targets[0].id
        rule_2 = elt.add_rule()
        rule_2.condition.model = 'true'
        rule_2.go_to = targets[1].id
        elt.fallback_rule.go_to = targets[2].id

        resolved = []
        elt.go_to_signal.connect(lambda rule_id: resolved.append(rule_id))
        elt._execute()

        assert resolved == [rule_2.id]

    def test_fallback_always_matches_when_nothing_else_does(self, qtbot):
        root = RootElt()
        elt = SwitchElt(1, parent=root)
        wait = WaitElt(10, parent=root)
        root._children = [elt, wait]
        rule = elt.add_rule()
        rule.condition.model = 'false'
        rule.go_to = wait.id
        elt.fallback_rule.go_to = wait.id

        resolved = []
        elt.go_to_signal.connect(lambda rule_id: resolved.append(rule_id))
        elt._execute()

        assert resolved == [elt.fallback_rule.id]

    def test_manual_override_bypasses_rule_evaluation(self, qtbot):
        root = RootElt()
        elt = SwitchElt(1, parent=root)
        wait_rule_target = WaitElt(10, parent=root)
        wait_override_target = WaitElt(11, parent=root)
        root._children = [elt, wait_rule_target, wait_override_target]
        rule = elt.add_rule()
        rule.condition.model = 'true'
        rule.go_to = wait_rule_target.id
        elt.fallback_rule.go_to = wait_rule_target.id

        elt.manual_override_target = wait_override_target.id
        elt.manual_override_enabled = True

        resolved = []
        elt.go_to_signal.connect(lambda rule_id: resolved.append(rule_id))
        elt._execute()

        assert resolved == [MANUAL_OVERRIDE_ID]
        assert elt._manual_target.transition.targetState() is wait_override_target.mstate

    def test_check_set_is_valid_names_the_broken_rule(self, qtbot):
        root = RootElt()
        elt = SwitchElt(1, parent=root)
        wait = WaitElt(10, parent=root)
        root._children = [elt, wait]
        rule = elt.add_rule()
        rule.condition.model = 'false'
        # rule.go_to is never set - its target stays unresolved
        elt.fallback_rule.go_to = wait.id
        with pytest.raises(ElementError, match=rule.label):
            elt.check_set_is_valid()

    def test_check_set_is_valid_warns_on_overlapping_rules(self, qtbot, caplog):
        root = RootElt()
        elt = SwitchElt(1, parent=root)
        wait = WaitElt(10, parent=root)
        root._children = [elt, wait]
        rule_1 = elt.add_rule()
        rule_1.condition.model = 'true'
        rule_1.go_to = wait.id
        rule_2 = elt.add_rule()
        rule_2.condition.model = 'true'
        rule_2.go_to = wait.id
        elt.fallback_rule.go_to = wait.id

        with caplog.at_level(logging.WARNING):
            elt.check_set_is_valid()

        assert 'overlap' in caplog.text.lower()

    def test_check_set_is_valid_does_not_warn_when_rules_dont_overlap(self, qtbot, caplog):
        root = RootElt()
        elt = SwitchElt(1, parent=root)
        wait = WaitElt(10, parent=root)
        root._children = [elt, wait]
        rule = elt.add_rule()
        rule.condition.model = 'false'
        rule.go_to = wait.id
        elt.fallback_rule.go_to = wait.id

        with caplog.at_level(logging.WARNING):
            elt.check_set_is_valid()

        assert 'overlap' not in caplog.text.lower()

    def test_save_load_round_trip(self, qtbot):
        root = RootElt()
        elt = SwitchElt(1, parent=root)
        waits = [WaitElt(10 + i, parent=root) for i in range(2)]
        root._children = [elt] + waits
        rule = elt.add_rule()
        rule.condition.model = 'true'
        rule.go_to = waits[0].id
        elt.fallback_rule.go_to = CONTINUE
        elt.manual_override_enabled = True
        elt.manual_override_target = waits[1].id

        saved = elt.to_dict_custom()
        reloaded = SwitchElt(1, parent=root)
        # deepcopy: unlike ChoiceElt/WhileElt's flat to_dict_custom, SwitchElt's 'rules' and
        # 'fallback' are nested dicts/lists - from_dict_custom pops keys out of them in place,
        # so a shallow dict(saved) would let that mutate `saved` itself through the shared
        # nested objects.
        reloaded.from_dict_custom(copy.deepcopy(saved))

        assert reloaded.to_dict_custom() == saved
        assert reloaded == elt

    def test_choice_elt_cannot_add_or_remove_rules(self, qtbot):
        """ ChoiceElt is the permanently-locked 2-Rule case: no add/remove-Rule affordance. """
        elt = ChoiceElt(1)
        assert elt.rules_locked is True
        with pytest.raises(ElementError):
            elt.add_rule()
        with pytest.raises(ElementError):
            elt.remove_rule(elt.fallback_rule.id)

    def test_rule_added_after_dashboard_attach_is_bound_to_it(self, qtbot):
        """ Regression: do_things_with_dashboard() only binds whatever rules exist at the
        moment self.dashboard is set. ChoiceElt's one rule always exists by then (built in
        __init__, before any dashboard can be attached), but a SwitchElt's rules are normally
        added later, via add_rule() - once the element is already sitting in a
        dashboard-attached tree. A rule created that way used to keep an empty ModulesManager
        forever, so its threshold condition's detector list silently stayed empty. """
        elt = SwitchElt(1)
        elt.dashboard = FakeDashboard(['det1', 'det2'])
        elt.do_things_with_dashboard()

        rule = elt.add_rule()
        rule.condition.model = 'threshold'

        assert rule.condition.model.settings['detectors']['all_items'] == ['det1', 'det2']


class TestCompositeChoiceModel:
    """ AND/OR/XOR composite choice model: sub-conditions are TrueChoiceModel/FalseChoiceModel
    (deterministic, no dashboard/detectors needed) combined by the chosen boolean operator"""

    def _make_composite(self, qtbot, *bool_values: bool) -> CompositeChoiceModel:
        elt = ChoiceElt(1)
        elt.choice_model = 'composite'
        composite: CompositeChoiceModel = elt.choice_model
        for value in bool_values:
            composite.add_condition('true' if value else 'false')
        return composite

    @pytest.mark.parametrize('values,expected', [
        ((True, True), True),
        ((True, False), False),
        ((False, False), False),
        ((True, True, True), True),
    ])
    def test_and(self, qtbot, values, expected):
        composite = self._make_composite(qtbot, *values)
        composite.settings['operator'] = 'AND'
        assert composite.evaluate(DataToExport('test')) is expected

    @pytest.mark.parametrize('values,expected', [
        ((True, False), True),
        ((False, False), False),
        ((True, True), True),
    ])
    def test_or(self, qtbot, values, expected):
        composite = self._make_composite(qtbot, *values)
        composite.settings['operator'] = 'OR'
        assert composite.evaluate(DataToExport('test')) is expected

    @pytest.mark.parametrize('values,expected', [
        ((True, False), True),
        ((True, True), False),
        ((True, True, True), True),
        ((False, False), False),
    ])
    def test_xor(self, qtbot, values, expected):
        composite = self._make_composite(qtbot, *values)
        composite.settings['operator'] = 'XOR'
        assert composite.evaluate(DataToExport('test')) is expected

    def test_no_conditions_is_false(self, qtbot):
        composite = self._make_composite(qtbot)
        assert composite.evaluate(DataToExport('test')) is False

    def test_remove_condition(self, qtbot):
        composite = self._make_composite(qtbot, True, False)
        composite.settings['operator'] = 'AND'
        row = composite.settings.child('conditions').children()[0]
        row.remove()
        assert len(composite._conditions) == 1
        # only the 'false' condition remains
        assert composite.evaluate(DataToExport('test')) is False

    def test_save_load_round_trip(self, qtbot):
        composite = self._make_composite(qtbot, True, False)
        composite.settings['operator'] = 'OR'
        saved = composite.to_dict()

        elt = ChoiceElt(2)
        elt.choice_model = 'composite'
        reloaded: CompositeChoiceModel = elt.choice_model
        reloaded.from_dict(dict(saved))

        assert reloaded.to_dict() == saved
        assert reloaded.evaluate(DataToExport('test')) is True


class TestGroupElt:
    """ Plain non-looping container: runs children once, then finishes - unlike RepeatElt
    (counts) or RootElt (singular, auto-created), this is addable anywhere like any other
    element (not filtered out of the tree view's "Add Element" menu, unlike 'root'/'button').
    """

    def test_runs_children_once_then_finishes(self, qtbot):
        elt = GroupElt(1)
        calls = []
        elt.children_signal.connect(lambda: calls.append('children'))
        elt.done_signal.connect(lambda: calls.append('done'))

        elt._execute()
        assert calls == ['children']

        elt._execute()
        assert calls == ['children', 'done']

    def test_runs_again_after_finishing(self, qtbot):
        """ A Group can itself be the child of a repeat/while - must be re-runnable """
        elt = GroupElt(1)
        calls = []
        elt.children_signal.connect(lambda: calls.append('children'))
        elt.done_signal.connect(lambda: calls.append('done'))

        elt._execute()
        elt._execute()
        elt._execute()
        assert calls == ['children', 'done', 'children']

    def test_not_in_add_element_exclusion_list(self):
        from pymodaq.extensions.sequencer.utilities.elements.root import RootElt
        from pymodaq.extensions.sequencer.utilities.elements.button import AddButtonPlaceholder
        assert GroupElt.elt_name not in (RootElt.elt_name, AddButtonPlaceholder.elt_name)


class TestWhileElt:
    """ Condition-driven loop: re-emits children_signal while its ChoiceModel evaluates True,
    done_signal once False. Sub-conditions reuse TrueChoiceModel/FalseChoiceModel, same
    deterministic, no-dashboard-needed pattern as TestCompositeChoiceModel."""

    def _make_while(self, bool_value: bool) -> WhileElt:
        elt = WhileElt(1)
        elt.choice_model = 'true' if bool_value else 'false'
        return elt

    def test_loops_while_true(self, qtbot):
        elt = self._make_while(True)
        calls = []
        elt.children_signal.connect(lambda: calls.append('children'))
        elt.done_signal.connect(lambda: calls.append('done'))

        for _ in range(3):
            elt._execute()
        assert calls == ['children', 'children', 'children']

    def test_finishes_immediately_when_false(self, qtbot):
        elt = self._make_while(False)
        calls = []
        elt.children_signal.connect(lambda: calls.append('children'))
        elt.done_signal.connect(lambda: calls.append('done'))

        elt._execute()
        assert calls == ['done']

    def test_condition_reevaluated_each_pass(self, qtbot):
        """ Flipping the condition mid-loop (e.g. a threshold crossed) stops it on the next
        pass, same as a real while loop - the condition is not cached. """
        elt = self._make_while(True)
        calls = []
        elt.children_signal.connect(lambda: calls.append('children'))
        elt.done_signal.connect(lambda: calls.append('done'))

        elt._execute()
        elt._execute()
        elt.choice_model = 'false'
        elt._execute()
        assert calls == ['children', 'children', 'done']

    def test_save_load_round_trip(self, qtbot):
        elt = self._make_while(True)
        saved = elt.to_dict_custom()

        reloaded = WhileElt(2)
        reloaded.from_dict_custom(dict(saved))

        assert reloaded.choice_model.model_name == 'true'
        assert reloaded.to_dict_custom() == saved




class TestGrabElt:
    def test_creation(self, qtbot):
        """Creating the element hides the actuator related parameters of the ModulesManager"""
        from pymodaq.extensions.sequencer.utilities.elements.grab import GrabElt
        from pymodaq.utils.managers.modules_manager import ModulesManagerParam

        elt = GrabElt(1)
        settings = elt.modules_manager.settings
        for name in (ModulesManagerParam.ACTUATORS, ModulesManagerParam.PROBE_ACTUATORS,
                     ModulesManagerParam.PROBE_ACTUATORS_RESULTS):
            assert not settings.child(name).opts['visible']
        assert settings.child(ModulesManagerParam.DETECTORS).opts['visible']

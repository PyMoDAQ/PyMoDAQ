import pytest

from pymodaq_data import DataToExport

from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltFactory, ElementError
from pymodaq.extensions.sequencer.utilities.elements.choice import ChoiceElt
from pymodaq.extensions.sequencer.utilities.elements.group import GroupElt
from pymodaq.extensions.sequencer.utilities.elements.root import RootElt
from pymodaq.extensions.sequencer.utilities.elements.wait import WaitElt
from pymodaq.extensions.sequencer.utilities.elements.while_loop import WhileElt
from pymodaq.extensions.sequencer.models.composite_choice_model import CompositeChoiceModel

seq_factory = SeqEltFactory()


class TestElements:

    def test_registered_elements(self, ):
        for elt in ('button', 'choice', 'grab', 'group', 'move', 'repeat', 'root', 'scanner',
                   'sequence', 'state', 'wait', 'while'):
            assert elt in seq_factory.elements


class TestChoiceElt:
    """ ChoiceElt's True/False branching: BranchHolder holds the two targets/transitions,
    ConditionHolder holds the pluggable ChoiceModel. Regression coverage for three bugs the
    composition refactor surfaced and fixed, none of which had prior test coverage: a
    copy-paste error message, a None-target crash, and a dashboard refresh that silently wiped
    the user's detector selection."""

    def test_default_model_is_trivial(self, qtbot):
        elt = ChoiceElt(1)
        assert elt.choice_model.model_name in ('true', 'false')

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
        elt.branches.update_target_states()  # must not raise

    def test_dashboard_refresh_preserves_detector_selection(self, qtbot):
        """ Regression: ThresholdChoiceModel.updated_module_manager used to force-select every
        detector on each dashboard refresh (ModulesManager.detectors_all's setter wipes the
        selection as a side effect) instead of preserving-and-filtering the user's choice, the
        way GrabElt.filter_selected_wrt_manager already did correctly. """
        elt = ChoiceElt(1)
        elt.choice_model = 'threshold'
        model = elt.choice_model
        model.settings['detectors'] = dict(all_items=['det1', 'det2'], selected=['det1'])

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

        elt.dashboard = FakeDashboard(['det1', 'det2'])
        elt.do_things_with_dashboard()

        assert model.settings['detectors']['selected'] == ['det1']


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



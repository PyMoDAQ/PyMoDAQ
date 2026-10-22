import pytest

from pymodaq_data import DataToExport

from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltFactory
from pymodaq.extensions.sequencer.utilities.elements.grab import GrabElt
from pymodaq.utils.managers.modules_manager import ModulesManagerParam
from pymodaq.extensions.sequencer.utilities.elements.choice import ChoiceElt
from pymodaq.extensions.sequencer.models.composite_choice_model import CompositeChoiceModel

seq_factory = SeqEltFactory()


class TestElements:

    def test_registered_elements(self, ):
        for elt in ('button', 'choice', 'grab', 'move', 'repeat', 'root', 'scanner', 'sequence', 'state', 'wait'):
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



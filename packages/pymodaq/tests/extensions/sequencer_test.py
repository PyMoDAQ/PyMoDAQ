import pytest

from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltFactory
from pymodaq.extensions.sequencer.utilities.elements.grab import GrabElt
from pymodaq.utils.managers.modules_manager import ModulesManagerParam

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



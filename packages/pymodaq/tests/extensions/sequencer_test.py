import pytest

from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltFactory

seq_factory = SeqEltFactory()


class TestElements:

    def test_registered_elements(self, ):
        for elt in ('button', 'choice', 'grab', 'move', 'repeat', 'root', 'scanner', 'sequence', 'state', 'wait'):
            assert elt in seq_factory.elements




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

import pytest

from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltFactory

seq_factory = SeqEltFactory()


class TestElements:

    def test_registered_elements(self, ):
        for elt in ('button', 'choice', 'grab', 'move', 'repeat', 'root', 'scanner', 'sequence', 'state', 'wait'):
            assert elt in seq_factory.elements



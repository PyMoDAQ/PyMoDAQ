import warnings
import pytest
from qtpy import QtWidgets
from pymodaq_gui.parameter import Parameter, ParameterTree


@pytest.fixture
def tree(qtbot):
    form = QtWidgets.QWidget()
    prog = ParameterTree(form)
    form.show()
    qtbot.addWidget(form)
    yield prog
    form.close()


# ---------------------------------------------------------------------------
# LedParameter  ('led')
# ---------------------------------------------------------------------------

class TestLedParameter:

    def test_default_value_is_false(self, tree):
        p = Parameter.create(name='led', type='led', value=False)
        tree.setParameters(p, showTop=False)
        assert p.value() is False

    def test_set_true(self, tree):
        p = Parameter.create(name='led', type='led', value=False)
        tree.setParameters(p, showTop=False)
        p.setValue(True)
        assert p.value() is True

    def test_set_false(self, tree):
        p = Parameter.create(name='led', type='led', value=True)
        tree.setParameters(p, showTop=False)
        p.setValue(False)
        assert p.value() is False

    def test_signal_emitted_on_change(self, tree, qtbot):
        p = Parameter.create(name='led', type='led', value=False)
        tree.setParameters(p, showTop=False)
        with qtbot.waitSignal(p.sigValueChanged, timeout=500):
            p.setValue(True)

    def test_signal_not_emitted_when_unchanged(self, tree, qtbot):
        p = Parameter.create(name='led', type='led', value=True)
        tree.setParameters(p, showTop=False)
        with qtbot.assertNotEmitted(p.sigValueChanged):
            p.setValue(True)

    def test_pyqtgraph_cannot_override_led_clickable(self, tree, qtbot):
        """Regression: pyqtgraph has no setReadOnly to call (hasattr is False); w.clickable stays False."""
        p = Parameter.create(name='led', type='led', value=False)
        tree.setParameters(p, showTop=False)
        widget = tree.listAllItems()[0].widget
        assert not hasattr(widget, 'setReadOnly')
        assert widget.clickable is False


# ---------------------------------------------------------------------------
# LedPushParameter  ('led_push') — same logic, clickable
# ---------------------------------------------------------------------------

class TestLedPushParameter:

    def test_roundtrip(self, tree):
        p = Parameter.create(name='led_push', type='led_push', value=False)
        tree.setParameters(p, showTop=False)
        p.setValue(True)
        assert p.value() is True
        p.setValue(False)
        assert p.value() is False


# ---------------------------------------------------------------------------
# MultistateLedParameter  ('multistate_led')
# ---------------------------------------------------------------------------

class TestMultistateLedParameter:

    STATES = [('idle', '#888888'), ('running', '#00b400'), ('error', '#c80000')]

    def test_default_two_state(self, tree):
        p = Parameter.create(name='ms', type='multistate_led', value='false')
        tree.setParameters(p, showTop=False)
        assert p.value() == 'false'

    def test_custom_states_roundtrip(self, tree):
        p = Parameter.create(name='ms', type='multistate_led',
                             value='idle', states=self.STATES)
        tree.setParameters(p, showTop=False)
        p.setValue('running')
        assert p.value() == 'running'
        p.setValue('error')
        assert p.value() == 'error'

    def test_signal_emitted_on_state_change(self, tree, qtbot):
        p = Parameter.create(name='ms', type='multistate_led',
                             value='idle', states=self.STATES)
        tree.setParameters(p, showTop=False)
        with qtbot.waitSignal(p.sigValueChanged, timeout=500):
            p.setValue('running')

    def test_invalid_state_raises(self, tree):
        p = Parameter.create(name='ms', type='multistate_led',
                             value='idle', states=self.STATES)
        tree.setParameters(p, showTop=False)
        # pyqtgraph swallows exceptions in its valueChanged event loop,
        # so we test the widget directly.
        widget = tree.listAllItems()[0].widget
        with pytest.raises(ValueError):
            widget.set_state('unknown')


# ---------------------------------------------------------------------------
# ActionLedParameter  ('action_led')
# ---------------------------------------------------------------------------

class TestActionLedParameter:

    def test_default_value_is_false_string(self, tree):
        p = Parameter.create(name='act', type='action_led', value='false')
        tree.setParameters(p, showTop=False)
        assert p.value() == 'false'

    def test_set_state_by_string(self, tree):
        p = Parameter.create(name='act', type='action_led', value='false')
        tree.setParameters(p, showTop=False)
        p.setValue('true')
        assert p.value() == 'true'

    def test_bool_true_coerced_with_warning(self, tree):
        p = Parameter.create(name='act', type='action_led', value='false')
        tree.setParameters(p, showTop=False)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            p.setValue(True)
            assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
        assert p.value() == 'true'

    def test_bool_false_coerced_with_warning(self, tree):
        p = Parameter.create(name='act', type='action_led', value='true')
        tree.setParameters(p, showTop=False)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            p.setValue(False)
            assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
        assert p.value() == 'false'

    def test_sigactivated_emitted_on_button_click(self, tree, qtbot):
        p = Parameter.create(name='act', type='action_led', value='false')
        tree.setParameters(p, showTop=False)
        widget = tree.listAllItems()[0].widget
        with qtbot.waitSignal(p.sigActivated, timeout=500):
            widget.button.click()

    def test_custom_states(self, tree):
        states = [('idle', '#888888'), ('running', '#00b400'), ('error', '#c80000')]
        p = Parameter.create(name='act', type='action_led', value='idle', states=states)
        tree.setParameters(p, showTop=False)
        p.setValue('running')
        assert p.value() == 'running'

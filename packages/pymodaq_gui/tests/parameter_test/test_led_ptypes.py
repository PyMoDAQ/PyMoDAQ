import warnings
import pytest
from qtpy import QtWidgets
from pymodaq_gui.parameter import Parameter, ParameterTree
from pymodaq_gui.utils.widgets import LedState


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
        assert p.value() == LedState.FALSE

    def test_custom_states_roundtrip(self, tree):
        p = Parameter.create(name='ms', type='multistate_led',
                             value='idle', limits=self.STATES)
        tree.setParameters(p, showTop=False)
        p.setValue('running')
        assert p.value() == 'running'
        p.setValue('error')
        assert p.value() == 'error'

    def test_signal_emitted_on_state_change(self, tree, qtbot):
        p = Parameter.create(name='ms', type='multistate_led',
                             value='idle', limits=self.STATES)
        tree.setParameters(p, showTop=False)
        with qtbot.waitSignal(p.sigValueChanged, timeout=500):
            p.setValue('running')

    def test_invalid_state_raises(self, tree):
        p = Parameter.create(name='ms', type='multistate_led',
                             value='idle', limits=self.STATES)
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
        assert p.value() == LedState.FALSE

    def test_set_state_by_string(self, tree):
        p = Parameter.create(name='act', type='action_led', value='false')
        tree.setParameters(p, showTop=False)
        p.setValue('true')
        assert p.value() == LedState.TRUE

    def test_bool_true_coerced_with_warning(self, tree):
        p = Parameter.create(name='act', type='action_led', value='false')
        tree.setParameters(p, showTop=False)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            p.setValue(True)
            assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
        assert p.value() == LedState.TRUE

    def test_bool_false_coerced_with_warning(self, tree):
        p = Parameter.create(name='act', type='action_led', value='true')
        tree.setParameters(p, showTop=False)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            p.setValue(False)
            assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
        assert p.value() == LedState.FALSE

    def test_sigactivated_emitted_on_button_click(self, tree, qtbot):
        p = Parameter.create(name='act', type='action_led', value='false')
        tree.setParameters(p, showTop=False)
        widget = tree.listAllItems()[0].widget
        with qtbot.waitSignal(p.sigActivated, timeout=500):
            widget.button.click()

    def test_checkable_button_tells_if_it_is_pressed_or_released(self, tree):
        p = Parameter.create(name='act', type='action_led', value='false', checkable=True)
        tree.setParameters(p, showTop=False)
        widget = tree.listAllItems()[0].widget
        checked = []
        p.sigActivated.connect(lambda param: checked.append(param.opts['checked']))
        widget.button.click()
        widget.button.click()
        assert checked == [True, False]

    def test_checkable_button_follows_the_checked_option(self, tree):
        p = Parameter.create(name='act', type='action_led', value='false', checkable=True)
        tree.setParameters(p, showTop=False)
        widget = tree.listAllItems()[0].widget
        activated = []
        p.sigActivated.connect(activated.append)
        widget.button.click()
        p.setOpts(checked=False)  # for instance the action failed in the plugin
        assert not widget.button.isChecked()
        assert len(activated) == 1  # releasing it from the plugin does not activate the parameter again

    def test_button_is_not_checkable_by_default(self, tree):
        p = Parameter.create(name='act', type='action_led', value='false')
        tree.setParameters(p, showTop=False)
        assert not tree.listAllItems()[0].widget.button.isCheckable()

    def test_states_of_the_status_workflow(self, tree):
        from pymodaq_gui.utils.status_palette import Status, StatusPalette
        p = Parameter.create(name='act', type='action_led', value=Status.OFF, limits='status')
        tree.setParameters(p, showTop=False)
        led = tree.listAllItems()[0].widget.led
        assert led.state_names() == list(Status)
        p.setValue(Status.RUNNING)
        assert led.get_state() == Status.RUNNING
        assert led._states[led._index][1] == StatusPalette.color(Status.RUNNING)

    def test_subset_of_the_status_workflow_by_names(self, tree):
        from pymodaq_gui.utils.status_palette import Status
        p = Parameter.create(name='act', type='action_led', value=Status.OFF,
                             limits=[Status.OFF, Status.RUNNING, Status.IDLE, Status.ERROR])
        tree.setParameters(p, showTop=False)
        led = tree.listAllItems()[0].widget.led
        assert led.state_names() == [Status.OFF, Status.RUNNING, Status.IDLE, Status.ERROR]

    def test_names_of_the_status_workflow_survive_xml(self, tmp_path):
        from pymodaq_gui.parameter import ioxml
        from pymodaq_gui.utils.status_palette import Status
        root = Parameter.create(name='root', type='group', children=[
            dict(name='act', type='action_led', value=Status.OFF, checkable=True,
                 limits=[Status.OFF, Status.RUNNING, Status.IDLE])])
        ioxml.parameter_to_xml_file(root, tmp_path / 'settings.xml')
        loaded = ioxml.XML_file_to_parameter(tmp_path / 'settings.xml')
        assert loaded[0]['limits'] == ['off', 'running', 'idle']

    @pytest.mark.parametrize('ptype', ['multistate_led', 'action_led'])
    def test_states_option_is_deprecated_but_still_works(self, tree, ptype):
        with pytest.warns(DeprecationWarning):
            p = Parameter.create(name='led', type=ptype, value='running',
                                 states=[('idle', '#888888'), ('running', '#00b400')])
        assert p.opts['limits'] == [('idle', '#888888'), ('running', '#00b400')]
        with pytest.warns(DeprecationWarning):
            p.setOpts(states=[('a', '#888888'), ('b', '#00b400')])
        assert p.opts['limits'] == [('a', '#888888'), ('b', '#00b400')]

    @pytest.mark.parametrize('ptype', ['multistate_led', 'action_led'])
    def test_states_follow_the_limits(self, tree, ptype):
        from pymodaq_gui.utils.status_palette import Status
        p = Parameter.create(name='led', type=ptype, value=Status.OFF, limits=[Status.OFF, Status.IDLE])
        tree.setParameters(p, showTop=False)
        widget = tree.listAllItems()[0].widget
        led = widget.led if ptype == 'action_led' else widget
        assert led.state_names() == [Status.OFF, Status.IDLE]
        p.setLimits([Status.OFF, Status.RUNNING, Status.ERROR])
        assert led.state_names() == [Status.OFF, Status.RUNNING, Status.ERROR]
        p.setValue(Status.ERROR)
        p.setLimits('status')
        assert led.state_names() == list(Status)
        assert led.get_state() == Status.ERROR

    @pytest.mark.parametrize('ptype', ['multistate_led', 'action_led'])
    def test_setlimits_normalizes_status_members_like_construction(self, tree, ptype):
        """Regression: Parameter.setLimits writes opts['limits'] directly and bypasses setOpts, so the
        StrEnum-to-str normalization done at construction time must also apply there, or opts['limits']
        keeps raw enum objects and XML serialization produces invalid Python syntax."""
        from pymodaq_gui.utils.status_palette import Status
        p = Parameter.create(name='led', type=ptype, value=Status.OFF, limits=[Status.OFF, Status.IDLE])
        tree.setParameters(p, showTop=False)
        p.setLimits([Status.OFF, Status.RUNNING, Status.ERROR])
        assert p.opts['limits'] == ['off', 'running', 'error']
        assert all(type(state) is str for state in p.opts['limits'])

    def test_setlimits_survives_xml_roundtrip(self, tmp_path):
        from pymodaq_gui.parameter import ioxml
        from pymodaq_gui.utils.status_palette import Status
        root = Parameter.create(name='root', type='group', children=[
            dict(name='act', type='action_led', value=Status.OFF, limits=[Status.OFF, Status.IDLE])])
        root.child('act').setLimits([Status.OFF, Status.RUNNING, Status.ERROR])
        ioxml.parameter_to_xml_file(root, tmp_path / 'settings.xml')
        loaded = ioxml.XML_file_to_parameter(tmp_path / 'settings.xml')
        assert loaded[0]['limits'] == ['off', 'running', 'error']

    def test_status_limits_survive_xml(self, tmp_path):
        from pymodaq_gui.parameter import ioxml
        root = Parameter.create(name='root', type='group', children=[
            dict(name='act', type='action_led', value='off', limits='status')])
        ioxml.parameter_to_xml_file(root, tmp_path / 'settings.xml')
        loaded = ioxml.XML_file_to_parameter(tmp_path / 'settings.xml')
        assert loaded[0]['limits'] == 'status'

    def test_unknown_states_option(self, tree):
        p = Parameter.create(name='act', type='action_led', value='off', limits='nope')
        with pytest.raises(ValueError):
            tree.setParameters(p, showTop=False)

    def test_custom_states(self, tree):
        states = [('idle', '#888888'), ('running', '#00b400'), ('error', '#c80000')]
        p = Parameter.create(name='act', type='action_led', value='idle', limits=states)
        tree.setParameters(p, showTop=False)
        p.setValue('running')
        assert p.value() == 'running'

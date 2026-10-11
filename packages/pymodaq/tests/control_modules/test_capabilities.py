"""Tests for the pymeasure-style capability declarations."""
import json

import pytest

from pymodaq.control_modules.hardware.capabilities import (
    Access,
    Action,
    Capabilities,
    Domain,
    Quantity,
    control,
    measurement,
    toolbar_widgets,
)


class Spectrometer:
    spectrum = measurement(units='counts', shape=(1024,), docs='Spectrum')
    temperature = measurement(units='K')
    status = measurement(values=['idle', 'running'])
    exposure = control(units='ms', lo=1, hi=1000, epsilon=0.1)
    trigger = control(values=['internal', 'external'])


class TestDeclaration:

    def test_attribute_name_becomes_quantity_name(self):
        assert Spectrometer.spectrum.name == 'spectrum'

    def test_factories_set_access(self):
        assert Spectrometer.temperature.access is Access.MEASUREMENT
        assert Spectrometer.exposure.access is Access.CONTROL

    def test_domain_follows_arguments(self):
        assert Spectrometer.exposure.domain is Domain.CONTINUOUS
        assert Spectrometer.status.domain is Domain.DISCRETE

    def test_discrete_measurement_is_allowed(self):
        assert Spectrometer.status.access is Access.MEASUREMENT
        assert Spectrometer.status.values == ['idle', 'running']

    def test_defaults(self):
        q = measurement()
        assert q.units == ''
        assert q.dtype == 'float64'
        assert q.shape == (1,)
        assert q.values == []

    def test_name_must_be_identifier(self):
        # called directly: Python < 3.12 wraps errors raised from __set_name__ in a RuntimeError
        with pytest.raises(ValueError, match='identifiers'):
            measurement().__set_name__(Spectrometer, 'bad name')


class TestValidation:

    def test_inverted_limits_rejected(self):
        with pytest.raises(ValueError):
            control(lo=5, hi=1)

    def test_partial_limits_allowed(self):
        assert control(lo=5).lo == 5

    def test_negative_epsilon_rejected(self):
        with pytest.raises(ValueError):
            control(epsilon=-0.1)

    def test_values_and_range_are_exclusive(self):
        with pytest.raises(ValueError):
            control(values=[1, 2], lo=0)

    def test_non_positive_shape_rejected(self):
        with pytest.raises(ValueError):
            measurement(shape=(0,))

    def test_none_shape_dimension_allowed(self):
        assert measurement(shape=(None,)).shape == (None,)

    def test_duplicate_names_rejected(self):
        a = measurement()
        a.name = 'x'
        b = control()
        b.name = 'x'
        with pytest.raises(ValueError, match='duplicated'):
            Capabilities(measurements=[a], controls=[b])


class TestFromDevice:

    def test_collects_measurements_and_controls(self):
        caps = Capabilities.from_device(Spectrometer)
        assert [q.name for q in caps.measurements] == ['spectrum', 'temperature', 'status']
        assert [q.name for q in caps.controls] == ['exposure', 'trigger']

    def test_accepts_an_instance(self):
        caps = Capabilities.from_device(Spectrometer())
        assert len(caps.measurements) == 3

    def test_subclass_inherits_and_overrides(self):
        class Child(Spectrometer):
            exposure = control(units='s', lo=0, hi=10)

        caps = Capabilities.from_device(Child)
        exposure = [q for q in caps.controls if q.name == 'exposure'][0]
        assert exposure.units == 's'
        assert len(caps.controls) == 2

    def test_device_without_declarations_is_empty(self):
        caps = Capabilities.from_device(object)
        assert caps.measurements == [] and caps.controls == []
        assert not caps.has_measurements()
        assert not caps.has_controls()

    def test_has_helpers_reflect_content(self):
        caps = Capabilities.from_device(Spectrometer)
        assert caps.has_measurements()
        assert caps.has_controls()
        assert not Capabilities(measurements=[Spectrometer.temperature]).has_controls()


class TestSerialization:

    def test_round_trip_preserves_every_field(self):
        caps = Capabilities.from_device(Spectrometer)
        restored = Capabilities.from_dict(json.loads(json.dumps(caps.to_dict())))
        assert restored.to_dict() == caps.to_dict()
        assert restored.controls[0].access is Access.CONTROL
        assert restored.measurements[0].shape == (1024,)

    def test_dict_carries_access_and_domain(self):
        d = Spectrometer.status.to_dict()
        assert d['access'] == 'measurement'
        assert d['domain'] == 'discrete'
        assert d['values'] == ['idle', 'running']


class TestToolbarWidgets:

    def test_continuous_control_follows_the_move_toolbar(self):
        assert toolbar_widgets(Spectrometer.exposure) == ['value', 'show_controls']

    def test_stop_is_not_a_default_but_a_callback_adds_it(self):
        # stop is device-specific (e.g. a motor axis), unlike value/show_controls, so it is opt-in
        assert 'stop' not in toolbar_widgets(control(lo=0, hi=1))
        widgets = toolbar_widgets(control(lo=0, hi=1, stop=lambda plugin: None))
        assert widgets == ['value', 'show_controls', 'stop']

    def test_a_declared_action_can_still_have_no_button(self):
        # button=False is the action's own knob for this, not ui_remove (see toolbar_widgets):
        # the action stays registered (callable via run_action/scripting), only its button is gone.
        q = control(lo=0, hi=1, actions={'stop': Action(lambda plugin: None, button=False)})
        assert 'stop' not in toolbar_widgets(q)
        assert 'stop' in q.actions

    def test_discrete_control_gets_a_selector(self):
        assert toolbar_widgets(Spectrometer.trigger) == ['selector']

    def test_discrete_measurement_gets_a_label(self):
        assert toolbar_widgets(Spectrometer.status) == ['label', 'grab']

    def test_scalar_measurement_gets_read_and_graph(self):
        assert toolbar_widgets(Spectrometer.temperature) == ['read', 'grab', 'show_graph']

    def test_array_measurement_gets_the_viewer_toolbar(self):
        assert toolbar_widgets(Spectrometer.spectrum) == ['snap', 'grab', 'show_graph', 'save']

    @pytest.mark.parametrize('shape', [(1, 1), (None,), (3,)])
    def test_non_scalar_shapes_count_as_arrays(self, shape):
        assert toolbar_widgets(measurement(shape=shape)) == ['snap', 'grab', 'show_graph', 'save']

    def test_declaration_adds_widgets(self):
        q = control(lo=0, hi=1, ui_add=('slider',))
        assert toolbar_widgets(q)[-1] == 'slider'

    def test_declaration_removes_widgets(self):
        q = control(lo=0, hi=1, ui_remove=('show_controls',))
        assert 'show_controls' not in toolbar_widgets(q)

    def test_added_widget_already_in_defaults_is_not_duplicated(self):
        q = measurement(ui_add=('show_graph',))
        assert toolbar_widgets(q).count('show_graph') == 1

    def test_unknown_widget_rejected(self):
        with pytest.raises(ValueError, match='unknown widgets'):
            control(ui_add=('spinner_of_doom',))

    def test_overrides_survive_serialization(self):
        q = Quantity.from_dict(control(lo=0, hi=1, ui_add=('slider',), ui_remove=('stop',)).to_dict())
        assert q.ui_add == ('slider',)
        assert 'stop' not in toolbar_widgets(q)

    def test_widget_toggle_replaces_the_default_selector_outright(self):
        q = control(values=['off', 'on'], widget='toggle')
        assert toolbar_widgets(q) == ['toggle']

    def test_widget_survives_serialization(self):
        q = Quantity.from_dict(control(values=['off', 'on'], widget='toggle').to_dict())
        assert q.widget == 'toggle'
        assert toolbar_widgets(q) == ['toggle']

    def test_no_widget_override_by_default(self):
        assert control(lo=0, hi=1).widget is None

    def test_toggle_needs_exactly_two_values(self):
        with pytest.raises(ValueError, match="two-valued discrete control"):
            control(values=['idle', 'running', 'error'], widget='toggle')
        with pytest.raises(ValueError, match="two-valued discrete control"):
            control(lo=0, hi=1, widget='toggle')  # continuous: no values at all

    def test_only_a_control_can_use_widget_toggle(self):
        # measurement() doesn't expose widget= at all (same as stop=/merge_into); bypassing the
        # factory still hits the same _validate() check Quantity(Access.CONTROL, ...) does.
        with pytest.raises(ValueError, match="two-valued discrete control"):
            Quantity(Access.MEASUREMENT, values=['idle', 'running'], widget='toggle')

    def test_toggle_is_the_only_supported_override(self):
        with pytest.raises(ValueError, match="only supported override"):
            control(values=['off', 'on'], widget='selector')

    def test_ui_add_no_longer_accepts_toggle(self):
        # toggle is a representation (widget=), not a companion widget (ui_add/ui_remove) - see
        # toolbar_widgets' docstring for the three-way split.
        with pytest.raises(ValueError, match='unknown widgets'):
            control(values=['off', 'on'], ui_add=('toggle',))


class TestReadback:

    def test_true_creates_a_measurement_named_after_the_control(self):
        class Stage:
            x = control(units='mm', lo=0, hi=50, readback=True)

        caps = Capabilities.from_device(Stage)
        readback = caps.measurements[0]
        assert caps.controls[0].readback == 'x_readback'
        assert readback.name == 'x_readback'
        assert readback.units == 'mm' and readback.access is Access.MEASUREMENT
        assert readback.lo is None  # a readback has no limits

    def test_a_string_names_the_created_measurement(self):
        class Stage:
            x = control(readback='x_position')

        caps = Capabilities.from_device(Stage)
        assert [q.name for q in caps.measurements] == ['x_position']
        assert caps.controls[0].readback == 'x_position'

    def test_a_declared_measurement_is_linked_not_duplicated(self):
        class Stage:
            x = control(readback='x_position')
            x_position = measurement(units='mm')

        caps = Capabilities.from_device(Stage)
        assert [q.name for q in caps.measurements] == ['x_position']

    def test_the_readback_survives_serialization(self):
        class Stage:
            x = control(units='mm', readback=True)

        caps = Capabilities.from_device(Stage)
        restored = Capabilities.from_dict(json.loads(json.dumps(caps.to_dict())))
        assert restored.to_dict() == caps.to_dict()
        assert [q.name for q in restored.measurements] == ['x_readback']

    def test_no_readback_by_default(self):
        class Stage:
            x = control()

        caps = Capabilities.from_device(Stage)
        assert caps.controls[0].readback is False and caps.measurements == []

    def test_any_string_names_the_readback(self):
        class Stage:
            z = control(units='mm', readback='my_z_readback')

        caps = Capabilities.from_device(Stage)
        assert caps.controls[0].readback == 'my_z_readback'
        assert [q.name for q in caps.measurements] == ['my_z_readback']

    def test_two_controls_cannot_share_an_explicit_readback(self):
        class Stage:
            x = control(units='mm', readback='position')
            y = control(units='mm', readback='position')

        with pytest.raises(ValueError, match="readback 'position' is declared by both 'x' and 'y'"):
            Capabilities.from_device(Stage)


class TestSetting:

    def test_true_uses_the_controls_own_name(self):
        class Stage:
            exposure = control(units='ms', lo=1, hi=1000, setting=True)

        caps = Capabilities.from_device(Stage)
        assert caps.controls[0].setting == 'exposure'

    def test_a_string_names_a_different_parameter(self):
        class Stage:
            exposure = control(units='ms', setting='exp_time')

        caps = Capabilities.from_device(Stage)
        assert caps.controls[0].setting == 'exp_time'

    def test_only_a_control_can_be_backed_by_a_setting(self):
        with pytest.raises(ValueError, match='only a control'):
            measurement()
            Quantity(Access.MEASUREMENT, setting=True)

    def test_no_setting_by_default(self):
        class Stage:
            exposure = control(units='ms')

        caps = Capabilities.from_device(Stage)
        assert caps.controls[0].setting is False

    def test_two_controls_cannot_share_a_setting(self):
        class Stage:
            x = control(units='mm', setting='offset')
            y = control(units='mm', setting='offset')

        with pytest.raises(ValueError, match="setting 'offset' is declared by both 'x' and 'y'"):
            Capabilities.from_device(Stage)

    def test_the_setting_survives_serialization(self):
        class Stage:
            exposure = control(units='ms', setting=True)

        caps = Capabilities.from_device(Stage)
        restored = Capabilities.from_dict(json.loads(json.dumps(caps.to_dict())))
        assert restored.controls[0].setting == 'exposure'


class TestGetSet:

    def test_get_is_kept_on_a_measurement(self):
        getter = lambda plugin: 42
        q = measurement(get=getter)
        assert q.get is getter

    def test_get_and_set_are_kept_on_a_control(self):
        getter = lambda plugin: 1.0
        setter = lambda plugin, value: None
        q = control(get=getter, set=setter)
        assert q.get is getter and q.set is setter

    def test_no_get_or_set_by_default(self):
        assert measurement().get is None
        assert control().get is None and control().set is None

    def test_a_measurement_cannot_have_a_set_callback(self):
        with pytest.raises(ValueError, match='only a control'):
            Quantity(Access.MEASUREMENT, set=lambda plugin, value: None)

    def test_set_and_setting_are_exclusive(self):
        with pytest.raises(ValueError, match='pick one'):
            control(setting=True, set=lambda plugin, value: None)

    def test_get_and_set_are_not_serialized(self):
        q = control(units='ms', get=lambda plugin: 1.0, set=lambda plugin, value: None)
        assert 'get' not in q.to_dict() and 'set' not in q.to_dict()


class TestStop:

    def test_kept_on_a_control(self):
        stopper = lambda plugin: None
        q = control(stop=stopper)
        assert q.actions['stop'].callback is stopper

    def test_no_stop_by_default(self):
        assert control().actions == {}

    def test_a_measurement_cannot_have_a_stop_callback(self):
        with pytest.raises(ValueError, match='only a control'):
            Quantity(Access.MEASUREMENT, stop=lambda plugin: None)

    def test_stop_is_not_serialized(self):
        q = control(stop=lambda plugin: None)
        assert 'actions' not in q.to_dict()


class TestActions:

    def test_stop_is_a_shorthand_for_an_action_named_stop(self):
        stopper = lambda plugin: None
        q = control(stop=stopper)
        assert q.actions.keys() == {'stop'}
        assert q.actions['stop'].callback is stopper
        assert q.actions['stop'].icon == 'stop_circle'  # keeps its familiar look

    def test_a_bare_callback_is_wrapped_in_an_action(self):
        homer = lambda plugin: None
        q = control(actions={'home': homer})
        assert q.actions['home'].callback is homer
        assert q.actions['home'].icon == ''  # no icon unless given one

    def test_an_explicit_action_keeps_its_icon_and_label(self):
        homer = lambda plugin: None
        q = control(actions={'home': Action(homer, icon='home', label='Home axis')})
        assert q.actions['home'] == Action(homer, icon='home', label='Home axis')

    def test_several_actions_can_be_declared_together(self):
        q = control(stop=lambda plugin: None, actions={'home': lambda plugin: None})
        assert q.actions.keys() == {'stop', 'home'}

    def test_a_measurement_can_have_actions_too(self):
        # e.g. "take background" on a spectrum: nothing about an action requires a value to write,
        # so this is not control-specific the way stop= is (see TestStop)
        q = measurement(actions={'take_background': lambda plugin: None})
        assert toolbar_widgets(q) == ['read', 'grab', 'show_graph', 'take_background']

    def test_a_checkable_actions_callback_also_takes_the_new_checked_state(self):
        q = control(actions={'subtract_bkg': Action(lambda plugin, checked: None, checkable=True)})
        assert q.actions['subtract_bkg'].checkable is True

    def test_not_checkable_by_default(self):
        q = control(actions={'home': lambda plugin: None})
        assert q.actions['home'].checkable is False

    def test_no_actions_by_default(self):
        assert control().actions == {}

    def test_a_custom_action_name_adds_its_own_widget(self):
        q = control(actions={'home': lambda plugin: None})
        assert toolbar_widgets(q) == ['value', 'show_controls', 'home']

    def test_several_custom_actions_each_add_their_own_widget(self):
        q = control(actions={'home': lambda plugin: None, 'zero': lambda plugin: None})
        assert set(toolbar_widgets(q)) >= {'home', 'zero'}

    def test_a_custom_action_can_be_declared_without_a_button(self):
        q = control(actions={'home': Action(lambda plugin: None, button=False)})
        assert 'home' not in toolbar_widgets(q)
        assert 'home' in q.actions

    def test_button_is_true_by_default(self):
        q = control(actions={'home': lambda plugin: None})
        assert q.actions['home'].button is True

    def test_ui_remove_no_longer_accepts_an_action_name(self):
        # button=False (above) is the action's own knob for this now - see toolbar_widgets' docstring.
        with pytest.raises(ValueError, match='unknown widgets'):
            control(actions={'home': lambda plugin: None}, ui_remove=('home',))

    def test_actions_are_not_serialized(self):
        q = control(actions={'home': lambda plugin: None})
        assert 'actions' not in q.to_dict()


class TestMergeInto:

    def test_binary_control_merges_into_another_controls_row(self):
        class Stage:
            x = control(units='mm', lo=0, hi=50)
            x_enable = control(values=['disabled', 'enabled'], merge_into='x')

        caps = Capabilities.from_device(Stage)
        assert [c.name for c in caps.controls if c.merge_into] == ['x_enable']

    def test_merge_target_must_be_a_declared_quantity(self):
        class Stage:
            x_enable = control(values=['disabled', 'enabled'], merge_into='x')

        with pytest.raises(ValueError, match="not a declared quantity"):
            Capabilities.from_device(Stage)

    def test_binary_control_merges_into_a_measurements_row_too(self):
        # merge_into is about where the button is drawn, not writability: the enable control still
        # dispatches its write the normal way, whether it rides along a control's row or a channel's
        class Spectrometer:
            spectrum = measurement(shape=(4,))
            spectrum_enable = control(values=['disabled', 'enabled'], merge_into='spectrum')

        caps = Capabilities.from_device(Spectrometer)
        assert [c.name for c in caps.controls if c.merge_into] == ['spectrum_enable']

    def test_cannot_merge_into_itself(self):
        class Stage:
            x = control(values=['disabled', 'enabled'], merge_into='x')

        with pytest.raises(ValueError, match='cannot merge into its own row'):
            Capabilities.from_device(Stage)

    def test_merges_cannot_chain(self):
        class Stage:
            x = control(units='mm', lo=0, hi=50)
            x_enable = control(values=['disabled', 'enabled'], merge_into='x')
            x_enable_confirm = control(values=['no', 'yes'], merge_into='x_enable')

        with pytest.raises(ValueError, match='cannot chain'):
            Capabilities.from_device(Stage)

    def test_merged_control_needs_exactly_two_values(self):
        with pytest.raises(ValueError, match='needs exactly two values'):
            control(values=['idle', 'running', 'error'], merge_into='x')

    def test_only_a_control_can_be_merged(self):
        with pytest.raises(ValueError, match='only a control'):
            Quantity(Access.MEASUREMENT, values=['off', 'on'], merge_into='x')

    def test_no_merge_by_default(self):
        assert control().merge_into is None

    def test_merge_into_survives_serialization(self):
        q = control(values=['disabled', 'enabled'], merge_into='x')
        restored = Quantity.from_dict(q.to_dict())
        assert restored.merge_into == 'x'

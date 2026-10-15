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
    instr_get,
    instr_set,
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

    def test_2d_shape_is_allowed(self):
        assert measurement(shape=(32, 32)).shape == (32, 32)

    def test_a_shape_of_any_dimension_is_allowed_here(self):
        # Quantity itself has no opinion on dimensionality - it's pure declaration, with no
        # consumer in view. HardwareModule (a separate, Qt-aware consumer) only has
        # Viewer0D/Viewer1D/Viewer2D wired up today and rejects anything past 2D on its own side,
        # at its own construction time - see test_hardware_module.py - rather than this layer
        # baking in one particular consumer's current limitation.
        assert measurement(shape=(4, 4, 3)).shape == (4, 4, 3)

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


class TestWidgetClass:
    """widget_class= substitutes the Qt class HardwareModule builds for a control's representation.
    Only a type/compatibility check happens here - capabilities.py stays Qt-free on purpose, so the
    real "does it expose the right property and signal" check happens in HardwareModule, where Qt is
    actually in scope (see RepresentationRule in hardware_module.py)."""

    def test_a_class_is_accepted_on_a_control(self):
        q = control(lo=0, hi=1, widget_class=object)
        assert q.widget_class is object

    def test_none_is_the_default(self):
        assert control(lo=0, hi=1).widget_class is None

    def test_only_a_control_can_use_it(self):
        with pytest.raises(ValueError, match='only a control'):
            Quantity(Access.MEASUREMENT, widget_class=object)

    def test_must_be_a_class_not_an_instance(self):
        with pytest.raises(ValueError, match='must be a class'):
            control(lo=0, hi=1, widget_class=object())

    def test_not_serialized(self):
        # a live class reference, same treatment as get=/set=/actions=
        q = Quantity.from_dict(control(lo=0, hi=1, widget_class=object).to_dict())
        assert q.widget_class is None


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
        assert readback.get is None  # the control has no get= of its own to default to

    def test_the_auto_created_readback_defaults_to_the_controls_own_get(self):
        # A control answering its own read directly has nothing separate for a readback to report -
        # exactly the exposure_readback case: no plugin code needed beyond readback=True.
        getter = lambda plugin: plugin.exposure
        class Stage:
            exposure = control(units='ms', readback=True, get=getter)

        caps = Capabilities.from_device(Stage)
        readback = caps.measurements[0]
        assert readback.name == 'exposure_readback'
        assert readback.get is getter

    def test_a_pre_declared_readback_is_not_overridden_by_the_default(self):
        own_getter = lambda plugin: plugin.other_source
        class Stage:
            exposure_readback = measurement(units='ms', get=own_getter)
            exposure = control(units='ms', readback=True, get=lambda plugin: plugin.exposure)

        caps = Capabilities.from_device(Stage)
        assert len(caps.measurements) == 1  # linked, not duplicated - same as any declared readback
        assert caps.measurements[0].get is own_getter  # the control's get= never touches it

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

    def test_a_readback_cannot_collide_with_an_unrelated_controls_name(self):
        """Unlike test_a_declared_measurement_is_linked_not_duplicated above: reusing an existing
        *measurement* by name is the documented way to attach a readback, but a control's own name
        is a different namespace - silently aliasing it as a readback would make it look read-only
        where it's actually still writable, so this must raise rather than quietly link the two."""
        class Stage:
            x = control(units='mm', readback=True)  # auto-names 'x_readback'
            x_readback = control(units='mm')  # an unrelated control that happens to collide

        with pytest.raises(ValueError, match="'x' declares readback 'x_readback', which is itself "
                                              "a declared control"):
            Capabilities.from_device(Stage)


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

    def test_get_and_set_are_not_serialized(self):
        q = control(units='ms', get=lambda plugin: 1.0, set=lambda plugin, value: None)
        assert 'get' not in q.to_dict() and 'set' not in q.to_dict()


class TestGetTrueAndMethodNameSugar:
    """get=True and the str form of get/set/pre_set/post_set: both pure sugar, resolved by
    Capabilities.__post_init__ into a real callable, never by Quantity/control()/measurement()
    themselves - same pattern readback=True already uses."""

    def test_a_bare_quantity_does_not_resolve_get_true_itself(self):
        q = control(get=True)
        assert q.get is True

    def test_get_true_reads_the_controls_own_attribute(self):
        class Stage:
            position = control(units='mm', get=True)

        caps = Capabilities.from_device(Stage)
        plugin = Stage()
        plugin.position = 3.0
        assert caps.controls[0].get(plugin) == 3.0

    def test_get_true_reads_a_measurements_own_attribute_too(self):
        class Sensor:
            temperature = measurement(units='K', get=True)

        caps = Capabilities.from_device(Sensor)
        plugin = Sensor()
        plugin.temperature = 295.0
        assert caps.measurements[0].get(plugin) == 295.0

    def test_get_string_calls_the_named_method_with_no_argument(self):
        class Sensor:
            temperature = measurement(units='K', get='_read_temperature')

            def _read_temperature(self):
                return 42.0

        caps = Capabilities.from_device(Sensor)
        assert caps.measurements[0].get(Sensor()) == 42.0

    def test_set_string_calls_the_named_method_with_the_value(self):
        class Stage:
            position = control(units='mm', set='_apply')

            def _apply(self, value):
                self.applied = value

        caps = Capabilities.from_device(Stage)
        plugin = Stage()
        caps.controls[0].set(plugin, 5.0)
        assert plugin.applied == 5.0

    def test_pre_set_and_post_set_strings_call_the_named_methods_with_the_value(self):
        class Stage:
            position = control(units='mm', pre_set='_validate', post_set='_after')

            def _validate(self, value):
                self.validated = value

            def _after(self, value):
                self.after = value

        caps = Capabilities.from_device(Stage)
        plugin = Stage()
        caps.controls[0].pre_set(plugin, 5.0)
        caps.controls[0].post_set(plugin, 5.0)
        assert plugin.validated == 5.0 and plugin.after == 5.0

    def test_the_readback_default_sees_a_resolved_get_not_the_literal_true_or_string(self):
        class Sensor:
            exposure = control(units='ms', readback=True, get=True)

        plugin = Sensor()
        plugin.exposure = 7.0
        caps = Capabilities.from_device(Sensor)
        readback = caps.measurements[0]
        assert callable(readback.get) and readback.get(plugin) == 7.0


class TestInstrGetSet:
    """instr_get/instr_set: bridging get=/set= to a *composed* instrument's own method, by direct
    reference, instead of a one-line bridge method per quantity. See hardware/README.md,
    "Wrapping an existing instrument object", for why plain inheritance doesn't need either."""

    class MyInstr:
        """Stands in for a real driver class - no PyMoDAQ import, plain methods."""

        def __init__(self):
            self.trigger_source = 'internal'

        def get_trigger(self):
            return self.trigger_source

        def set_trigger(self, value):
            self.trigger_source = value

    def test_instr_get_calls_the_method_on_the_named_attribute(self):
        class Spectrometer:
            controller: TestInstrGetSet.MyInstr
            trigger = measurement(values=['internal', 'external'],
                                   get=instr_get(TestInstrGetSet.MyInstr.get_trigger))

        plugin = Spectrometer()
        plugin.controller = TestInstrGetSet.MyInstr()
        plugin.controller.trigger_source = 'external'
        caps = Capabilities.from_device(Spectrometer)
        assert caps.measurements[0].get(plugin) == 'external'

    def test_instr_set_calls_the_method_on_the_named_attribute(self):
        class Spectrometer:
            controller: TestInstrGetSet.MyInstr
            trigger = control(values=['internal', 'external'],
                               set=instr_set(TestInstrGetSet.MyInstr.set_trigger))

        plugin = Spectrometer()
        plugin.controller = TestInstrGetSet.MyInstr()
        caps = Capabilities.from_device(Spectrometer)
        caps.controls[0].set(plugin, 'external')
        assert plugin.controller.trigger_source == 'external'

    def test_default_attr_is_controller_matching_the_old_style_convention(self):
        plugin = type('Plugin', (), {})()
        plugin.controller = TestInstrGetSet.MyInstr()
        getter = instr_get(TestInstrGetSet.MyInstr.get_trigger)
        assert getter(plugin) == 'internal'

    def test_attr_can_be_overridden_for_a_differently_named_attribute(self):
        plugin = type('Plugin', (), {})()
        plugin.spectrometer_driver = TestInstrGetSet.MyInstr()
        getter = instr_get(TestInstrGetSet.MyInstr.get_trigger, attr='spectrometer_driver')
        assert getter(plugin) == 'internal'

    def test_resolution_is_lazy_the_attribute_need_not_exist_at_declaration_time(self):
        # control()/measurement() run in the class body, before any instance - and so
        # self.controller - exists; instr_get/instr_set must not touch it until actually called.
        class Spectrometer:
            controller: TestInstrGetSet.MyInstr
            trigger = measurement(get=instr_get(TestInstrGetSet.MyInstr.get_trigger))

        plugin = Spectrometer()  # controller still unset here, same as before open() runs
        plugin.controller = TestInstrGetSet.MyInstr()  # assigned later, e.g. inside open()
        caps = Capabilities.from_device(Spectrometer)
        assert caps.measurements[0].get(plugin) == 'internal'

    def test_instr_get_and_instr_set_are_not_serialized(self):
        q = control(get=instr_get(TestInstrGetSet.MyInstr.get_trigger),
                    set=instr_set(TestInstrGetSet.MyInstr.set_trigger))
        assert 'get' not in q.to_dict() and 'set' not in q.to_dict()


class TestQuantityDescriptor:
    """Quantity.__get__/__set__: every declared quantity is a live, directly readable/writable
    attribute on plugin instances, storage owned here - unconditional, the same for every
    control/measurement regardless of get=/set=/pre_set=/post_set=/read()/write()."""

    def test_reading_and_writing_work_with_no_init_assignment_at_all(self):
        # The case this whole mechanism exists for: no __init__ boilerplate, from anywhere.
        class Stage:
            position = control(units='mm')

        plugin = Stage()
        plugin.position = 15
        assert plugin.position == 15

    def test_a_never_written_quantity_reads_back_none_not_the_declaration(self):
        # The footgun this fixes: before Quantity was a descriptor, a never-shadowed name read
        # back the Quantity object itself - silently, with no error.
        class Stage:
            position = control(units='mm')

        assert Stage().position is None

    def test_class_level_access_still_returns_the_declaration(self):
        # Stage.position (no instance) is unaffected - only instance-level access changed.
        class Stage:
            position = control(units='mm')

        assert isinstance(Stage.position, Quantity)

    def test_from_device_discovery_is_unaffected(self):
        # Capabilities.from_device walks __mro__/vars(), which bypasses __get__/__set__ entirely -
        # confirmed directly, not just inferred from every other passing test.
        class Stage:
            position = control(units='mm')

        caps = Capabilities.from_device(Stage)
        assert caps.controls[0].name == 'position'

    def test_a_quantity_still_supports_plain_instance_shadowing(self):
        # Backward compatible: a plugin that assigns self.<name> for its own bookkeeping sees the
        # exact same result it always did - same storage key, just reached through __set__ now
        # instead of plain attribute shadowing.
        class Spectro:
            spectrum = measurement(units='counts', shape=(4,))

        plugin = Spectro()
        plugin.spectrum = 'cached value'
        assert plugin.spectrum == 'cached value'


class TestPreSetPostSet:
    """pre_set=/post_set= are optional hooks around a control's write; the unconditional storage
    they wrap (plugin.<name> = value after a successful write) is HardwareThread.request_write's
    job, not Quantity's/Capabilities' - see test_hardware_thread.py for that sequencing. This class
    only covers declaration and validation."""

    def test_neither_is_set_by_default(self):
        q = control()
        assert q.pre_set is None and q.post_set is None

    def test_only_a_control_can_have_pre_set(self):
        # measurement() doesn't even accept pre_set= (control-only in its signature); the
        # underlying Quantity check is still exercised directly, same as TestGetSet does for set=.
        with pytest.raises(ValueError, match='only a control'):
            Quantity(Access.MEASUREMENT, pre_set=lambda plugin, value: None)

    def test_only_a_control_can_have_post_set(self):
        with pytest.raises(ValueError, match='only a control'):
            Quantity(Access.MEASUREMENT, post_set=lambda plugin, value: None)

    def test_pre_set_and_a_set_callback_are_exclusive(self):
        with pytest.raises(ValueError, match='pick one'):
            control(pre_set=lambda plugin, value: None, set=lambda plugin, value: None)

    def test_post_set_and_a_set_callback_are_exclusive(self):
        with pytest.raises(ValueError, match='pick one'):
            control(post_set=lambda plugin, value: None, set=lambda plugin, value: None)

    def test_both_may_be_given_together(self):
        q = control(pre_set=lambda plugin, value: None, post_set=lambda plugin, value: None)
        assert q.pre_set is not None and q.post_set is not None

    def test_neither_is_serialized_same_as_get_set(self):
        class Stage:
            position = control(units='mm', pre_set=lambda plugin, value: None,
                               post_set=lambda plugin, value: None)

        caps = Capabilities.from_device(Stage)
        d = caps.to_dict()
        assert 'pre_set' not in d['controls'][0] and 'post_set' not in d['controls'][0]


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

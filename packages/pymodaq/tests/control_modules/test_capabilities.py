"""Tests for the pymeasure-style capability declarations."""
import json

import pytest

from pymodaq.control_modules.capabilities import (
    Access,
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
        assert toolbar_widgets(Spectrometer.exposure) == ['value', 'move_done_led', 'stop', 'show_controls']

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

    def test_the_setting_survives_serialization(self):
        class Stage:
            exposure = control(units='ms', setting=True)

        caps = Capabilities.from_device(Stage)
        restored = Capabilities.from_dict(json.loads(json.dumps(caps.to_dict())))
        assert restored.controls[0].setting == 'exposure'

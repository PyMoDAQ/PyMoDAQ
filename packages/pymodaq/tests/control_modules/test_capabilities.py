"""Tests for pymodaq.control_modules.capabilities."""
import json

import pytest

from pymodaq.control_modules.capabilities import (
    Capabilities,
    ContinuousVariable,
    DiscreteVariable,
    Observable,
    Variable,
    infer_capabilities,
)


# ── Observable ───────────────────────────────────────────────────────────────

class TestObservable:
    def test_defaults(self):
        obs = Observable(name='spectrum')
        assert obs.name == 'spectrum'
        assert obs.label == ''
        assert obs.units == ''
        assert obs.dtype == 'float64'
        assert obs.shape == (1,)

    def test_custom_fields(self):
        obs = Observable(name='counts', label='Photon counts', units='counts',
                         dtype='uint16', shape=(1024,))
        assert obs.units == 'counts'
        assert obs.dtype == 'uint16'
        assert obs.shape == (1024,)

    def test_to_dict_is_json_compatible(self):
        obs = Observable(name='x', label='X', units='nm', dtype='float32', shape=(512, 512))
        d = obs.to_dict()
        assert d['name'] == 'x'
        assert d['label'] == 'X'
        assert d['units'] == 'nm'
        assert d['dtype'] == 'float32'
        assert d['shape'] == [512, 512]   # list, not tuple — JSON-safe
        json.dumps(d)   # must not raise

    def test_roundtrip(self):
        obs = Observable(name='temp', label='Temperature', units='K',
                         dtype='float64', shape=(1,))
        assert Observable.from_dict(obs.to_dict()) == obs

    def test_roundtrip_nd_shape(self):
        obs = Observable(name='img', shape=(480, 640))
        result = Observable.from_dict(obs.to_dict())
        assert result.shape == (480, 640)

    def test_from_dict_tolerates_missing_optional_fields(self):
        obs = Observable.from_dict({'name': 'v'})
        assert obs.label == ''
        assert obs.units == ''
        assert obs.dtype == 'float64'
        assert obs.shape == (1,)

    def test_shape_with_none_dimension(self):
        obs = Observable(name='hits', shape=(None,))
        result = Observable.from_dict(obs.to_dict())
        assert result.shape == (None,)

    def test_shape_mixed_none_and_fixed(self):
        obs = Observable(name='waveform', shape=(None, 4))
        result = Observable.from_dict(obs.to_dict())
        assert result.shape == (None, 4)


# ── Variable (base) ───────────────────────────────────────────────────────────

class TestVariableBase:
    def test_is_observable(self):
        var = Variable(name='x')
        assert isinstance(var, Observable)

    def test_defaults(self):
        var = Variable(name='wavelength')
        assert var.name == 'wavelength'
        assert var.label == ''
        assert var.units == ''

    def test_to_dict_has_kind_variable(self):
        var = Variable(name='x')
        assert var.to_dict()['kind'] == 'variable'

    def test_roundtrip(self):
        var = Variable(name='gain', label='Gain', units='dB')
        result = Variable.from_dict(var.to_dict())
        assert result == var


# ── ContinuousVariable ────────────────────────────────────────────────────────

class TestContinuousVariable:
    def test_is_variable(self):
        cv = ContinuousVariable(name='pos')
        assert isinstance(cv, Variable)
        assert isinstance(cv, Observable)

    def test_defaults(self):
        cv = ContinuousVariable(name='pos')
        assert cv.lo is None
        assert cv.hi is None
        assert cv.epsilon == 0.0

    def test_to_dict_has_kind_continuous(self):
        cv = ContinuousVariable(name='pos')
        assert cv.to_dict()['kind'] == 'continuous'

    def test_to_dict_is_json_compatible(self):
        cv = ContinuousVariable(name='pos', lo=None, hi=None, epsilon=0.001)
        d = cv.to_dict()
        serialized = json.dumps(d)
        loaded = json.loads(serialized)
        assert loaded['lo'] is None
        assert loaded['hi'] is None

    def test_roundtrip_bounded(self):
        cv = ContinuousVariable(name='pos', label='Position', units='mm',
                                lo=-50.0, hi=50.0, epsilon=0.001)
        result = ContinuousVariable.from_dict(cv.to_dict())
        assert result == cv

    def test_roundtrip_unbounded(self):
        cv = ContinuousVariable(name='gain', units='dB')
        result = ContinuousVariable.from_dict(cv.to_dict())
        assert result == cv

    def test_from_dict_tolerates_missing_fields(self):
        cv = ContinuousVariable.from_dict({'name': 'x'})
        assert cv.lo is None
        assert cv.hi is None
        assert cv.epsilon == 0.0


# ── DiscreteVariable ──────────────────────────────────────────────────────────

class TestDiscreteVariable:
    def test_is_variable(self):
        dv = DiscreteVariable(name='mode')
        assert isinstance(dv, Variable)
        assert isinstance(dv, Observable)

    def test_defaults(self):
        dv = DiscreteVariable(name='mode')
        assert dv.choices == []

    def test_to_dict_has_kind_discrete(self):
        dv = DiscreteVariable(name='mode')
        assert dv.to_dict()['kind'] == 'discrete'

    def test_roundtrip_string_choices(self):
        dv = DiscreteVariable(name='coupling', choices=['AC', 'DC', 'GND'])
        result = DiscreteVariable.from_dict(dv.to_dict())
        assert result == dv

    def test_roundtrip_int_choices(self):
        dv = DiscreteVariable(name='gain', choices=[1, 2, 3, 4])
        result = DiscreteVariable.from_dict(dv.to_dict())
        assert result == dv

    def test_roundtrip_float_choices(self):
        dv = DiscreteVariable(name='power', choices=[5.0, 10.0, 25.0])
        result = DiscreteVariable.from_dict(dv.to_dict())
        assert result == dv

    def test_to_dict_is_json_compatible(self):
        dv = DiscreteVariable(name='filter', choices=['ND1', 'ND2', 'ND4'])
        json.dumps(dv.to_dict())   # must not raise

    def test_from_dict_tolerates_missing_fields(self):
        dv = DiscreteVariable.from_dict({'name': 'mode'})
        assert dv.choices == []


# ── Capabilities ─────────────────────────────────────────────────────────────

class TestCapabilities:
    def test_defaults_are_empty(self):
        caps = Capabilities()
        assert caps.observables == []
        assert caps.variables == []

    def test_has_observables_with_observable(self):
        caps = Capabilities(observables=[Observable(name='data')])
        assert caps.has_observables() is True

    def test_has_observables_with_variable(self):
        # Variables count as readable quantities
        caps = Capabilities(variables=[Variable(name='pos')])
        assert caps.has_observables() is True

    def test_has_observables_empty(self):
        caps = Capabilities()
        assert caps.has_observables() is False

    def test_has_variables_true(self):
        caps = Capabilities(variables=[Variable(name='pos')])
        assert caps.has_variables() is True

    def test_has_variables_false_when_only_observables(self):
        caps = Capabilities(observables=[Observable(name='data')])
        assert caps.has_variables() is False

    def test_to_dict_roundtrip_empty(self):
        caps = Capabilities()
        assert Capabilities.from_dict(caps.to_dict()) == caps

    def test_to_dict_roundtrip_with_contents(self):
        caps = Capabilities(
            observables=[Observable(name='spectrum', units='counts', shape=(1024,))],
            variables=[ContinuousVariable(name='position', units='mm',
                                          lo=-50.0, hi=50.0, epsilon=0.001)],
        )
        result = Capabilities.from_dict(caps.to_dict())
        assert result.observables[0] == caps.observables[0]
        assert result.variables[0] == caps.variables[0]

    def test_to_dict_is_json_compatible(self):
        caps = Capabilities(
            observables=[Observable(name='data')],
            variables=[ContinuousVariable(name='pos', lo=None, hi=100.0)],
        )
        json.dumps(caps.to_dict())   # must not raise

    def test_from_dict_tolerates_missing_keys(self):
        caps = Capabilities.from_dict({})
        assert caps.observables == []
        assert caps.variables == []

    def test_from_dict_dispatches_continuous(self):
        caps = Capabilities(variables=[ContinuousVariable(name='x', lo=-1.0, hi=1.0)])
        result = Capabilities.from_dict(caps.to_dict())
        assert isinstance(result.variables[0], ContinuousVariable)

    def test_from_dict_dispatches_discrete(self):
        caps = Capabilities(variables=[DiscreteVariable(name='mode', choices=['A', 'B'])])
        result = Capabilities.from_dict(caps.to_dict())
        assert isinstance(result.variables[0], DiscreteVariable)

    def test_from_dict_dispatches_base_variable(self):
        caps = Capabilities(variables=[Variable(name='x')])
        result = Capabilities.from_dict(caps.to_dict())
        assert type(result.variables[0]) is Variable


# ── infer_capabilities ───────────────────────────────────────────────────────

class TestInferCapabilities:

    # ── Explicit declaration ─────────────────────────────────────────────────

    def test_explicit_capabilities_returned_directly(self):
        declared = Capabilities(
            observables=[Observable(name='spectrum', shape=(2048,))],
        )
        class MyPlugin:
            capabilities = declared

        result = infer_capabilities(MyPlugin())
        assert result is declared

    def test_explicit_capabilities_on_class_itself(self):
        declared = Capabilities(variables=[Variable(name='position', units='mm')])
        class MyPlugin:
            capabilities = declared

        assert infer_capabilities(MyPlugin) is declared

    # ── Actuator heuristic ───────────────────────────────────────────────────

    def test_single_axis_string_units(self):
        class MockMove:
            _controller_units = 'mm'
            _axis_names = None
            _epsilons = 0.01

        caps = infer_capabilities(MockMove())
        assert caps.has_variables()
        assert len(caps.variables) == 1
        var = caps.variables[0]
        assert isinstance(var, ContinuousVariable)
        assert var.name == 'position'
        assert var.units == 'mm'
        assert var.epsilon == pytest.approx(0.01)

    def test_multiaxis_list(self):
        class MockMove:
            _controller_units = ['mm', 'mm', 'deg']
            _axis_names = ['x', 'y', 'theta']
            _epsilons = [0.001, 0.001, 0.01]

        caps = infer_capabilities(MockMove())
        assert len(caps.variables) == 3
        assert all(isinstance(v, ContinuousVariable) for v in caps.variables)
        assert caps.variables[0].name == 'x'
        assert caps.variables[0].units == 'mm'
        assert caps.variables[2].name == 'theta'
        assert caps.variables[2].units == 'deg'
        assert caps.variables[2].epsilon == pytest.approx(0.01)

    def test_multiaxis_dict(self):
        class MockMove:
            _controller_units = {'x': 'mm', 'y': 'mm'}
            _axis_names = {'x': 0, 'y': 1}
            _epsilons = {'x': 0.001, 'y': 0.002}

        caps = infer_capabilities(MockMove())
        assert len(caps.variables) == 2
        assert all(isinstance(v, ContinuousVariable) for v in caps.variables)
        names = [v.name for v in caps.variables]
        assert 'x' in names and 'y' in names
        y_var = next(v for v in caps.variables if v.name == 'y')
        assert y_var.epsilon == pytest.approx(0.002)

    def test_axis_names_empty_list_defaults_to_position(self):
        class MockMove:
            _controller_units = 'nm'
            _axis_names = []
            _epsilons = None

        caps = infer_capabilities(MockMove())
        assert caps.variables[0].name == 'position'

    def test_no_epsilons_defaults_epsilon_to_zero(self):
        class MockMove:
            _controller_units = 'um'
            _axis_names = None
            _epsilons = None

        caps = infer_capabilities(MockMove())
        assert caps.variables[0].epsilon == 0.0

    def test_scalar_epsilon_applied_to_all_axes(self):
        class MockMove:
            _controller_units = ['mm', 'mm']
            _axis_names = ['a', 'b']
            _epsilons = 0.5

        caps = infer_capabilities(MockMove())
        assert all(v.epsilon == pytest.approx(0.5) for v in caps.variables)

    def test_controller_units_only_no_axis_names(self):
        class MockMove:
            _controller_units = 'V'
            _axis_names = None
            _epsilons = None

        caps = infer_capabilities(MockMove())
        assert caps.has_variables()
        assert caps.variables[0].units == 'V'

    def test_variables_only_no_observables_for_actuator(self):
        class MockMove:
            _controller_units = 'mm'
            _axis_names = None
            _epsilons = None

        caps = infer_capabilities(MockMove())
        assert caps.observables == []

    def test_has_observables_true_for_actuator(self):
        # has_observables counts variables too
        class MockMove:
            _controller_units = 'mm'
            _axis_names = None
            _epsilons = None

        caps = infer_capabilities(MockMove())
        assert caps.has_observables() is True

    # ── Detector fallback ────────────────────────────────────────────────────

    def test_detector_fallback_no_attributes(self):
        class MockViewer:
            pass

        caps = infer_capabilities(MockViewer())
        assert caps.has_observables()
        assert not caps.has_variables()
        assert caps.observables[0].name == 'data'

    def test_detector_fallback_units_empty(self):
        class MockViewer:
            pass

        caps = infer_capabilities(MockViewer())
        assert caps.observables[0].units == ''

    # ── Edge cases ───────────────────────────────────────────────────────────

    def test_units_list_shorter_than_axis_names_padded_with_empty(self):
        class MockMove:
            _controller_units = ['mm']       # only one unit for two axes
            _axis_names = ['x', 'y']
            _epsilons = None

        caps = infer_capabilities(MockMove())
        assert caps.variables[0].units == 'mm'
        assert caps.variables[1].units == ''  # padded

    def test_epsilons_list_shorter_than_axis_names_padded_with_zero(self):
        class MockMove:
            _controller_units = ['mm', 'mm']
            _axis_names = ['x', 'y']
            _epsilons = [0.1]                # only one epsilon for two axes

        caps = infer_capabilities(MockMove())
        assert caps.variables[0].epsilon == pytest.approx(0.1)
        assert caps.variables[1].epsilon == 0.0  # padded

"""Tests for the RepresentationFactory registry: what gets built for a control's own
representation ('value'/'selector'/'toggle'), independent of HardwareModule itself."""
import pytest
from qtpy import QtWidgets

from pymodaq.control_modules.hardware.capabilities import control
from pymodaq.control_modules.representations import (
    RepresentationFactory,
    RepresentationRule,
    representation_of,
)


class TestRepresentationOf:

    def test_a_continuous_control_is_value(self):
        assert representation_of(control(lo=0, hi=1)) == 'value'

    def test_a_discrete_control_is_selector_by_default(self):
        assert representation_of(control(values=['idle', 'running'])) == 'selector'

    def test_a_two_valued_control_asking_for_toggle_is_toggle(self):
        assert representation_of(control(values=['off', 'on'], widget='toggle')) == 'toggle'


class TestRepresentationFactory:

    @pytest.mark.parametrize('kind,default_class,property_name,commit_signal', [
        ('value', QtWidgets.QDoubleSpinBox, 'value', 'editingFinished'),
        ('selector', QtWidgets.QComboBox, 'currentIndex', 'activated'),
        ('toggle', QtWidgets.QPushButton, 'checked', 'toggled'),
    ])
    def test_each_kind_is_registered_with_its_own_rule(self, kind, default_class, property_name,
                                                        commit_signal):
        rule = RepresentationFactory.create(kind)
        assert isinstance(rule, RepresentationRule)
        assert rule.default_class is default_class
        assert rule.property_name == property_name
        assert rule.commit_signal == commit_signal

    def test_an_unregistered_kind_raises(self):
        with pytest.raises(ValueError):
            RepresentationFactory.create('dial')

    def test_value_and_slider_are_a_plain_passthrough(self):
        rule = RepresentationFactory.create('value')
        quantity = control(lo=0, hi=1)
        assert rule.to_widget(5.0, quantity) == 5.0
        assert rule.from_widget(5.0, quantity) == 5.0
        assert rule.extra_setter is None

    def test_selector_translates_between_index_and_value(self):
        rule = RepresentationFactory.create('selector')
        quantity = control(values=['idle', 'running', 'error'])
        assert rule.to_widget('running', quantity) == 1
        assert rule.from_widget(1, quantity) == 'running'

    def test_toggle_translates_between_checked_and_value(self):
        rule = RepresentationFactory.create('toggle')
        quantity = control(values=['off', 'on'], widget='toggle')
        assert rule.to_widget('on', quantity) is True
        assert rule.to_widget('off', quantity) is False
        assert rule.from_widget(True, quantity) == 'on'
        assert rule.from_widget(False, quantity) == 'off'

    def test_toggle_has_an_extra_setter_for_its_own_text(self, qtbot):
        rule = RepresentationFactory.create('toggle')
        button = QtWidgets.QPushButton()
        rule.extra_setter(button, 'on')
        assert button.text() == 'on'

    def test_registering_a_new_kind_does_not_touch_hardware_module(self):
        """The whole point of the factory: a fourth kind is a new @register'd function somewhere,
        not an edit to a shared dict in hardware_module.py."""
        @RepresentationFactory.register('dial')
        def _dial_representation(**_ignored):
            return RepresentationRule(default_class=QtWidgets.QDial, property_name='value',
                                      commit_signal='sliderReleased')
        try:
            rule = RepresentationFactory.create('dial')
            assert rule.default_class is QtWidgets.QDial
        finally:
            del RepresentationFactory._builders['RepresentationFactory']['dial']

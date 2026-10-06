"""Tests for HardwareModule: the widget built from capabilities, over a real hardware thread."""
from __future__ import annotations

import numpy as np
import pytest
from qtpy import QtWidgets

from qtpy.QtCore import Qt

from pymodaq.control_modules.capabilities import control, measurement
from pymodaq.control_modules.hardware_module import HardwareModule
from pymodaq.control_modules.hardware_registry import HardwareKey, HardwareRegistry


class _Reading:
    def __init__(self, names):
        self._arrays = {name: np.array([2.5]) for name in names}

    def get_data_from_name(self, name):
        return self._arrays[name]


class Camera:
    params: list = []
    temperature = measurement(units='K')
    status = measurement(values=['idle', 'running'])
    exposure = control(units='ms', lo=1, hi=1000, epsilon=0.1)
    trigger = control(values=['internal', 'external'])

    def __init__(self):
        self.written = []

    def open(self, settings):
        pass

    def close(self):
        pass

    def read(self, names=None, fresh=True):
        return _Reading(names)

    def write(self, name, value):
        self.written.append((name, value))


@pytest.fixture
def registry():
    registry = HardwareRegistry()
    yield registry
    registry.close_all()


@pytest.fixture
def module(registry, qtbot):
    key = HardwareKey(hardware_class=Camera, controller_id=0)
    widget = HardwareModule(key, Camera, registry=registry)
    qtbot.addWidget(widget)
    yield widget
    widget.release()


class TestLayout:

    def test_instrument_toolbar_is_on_top(self, module):
        toolbar = module.get_toolbar('instrument')
        assert module.toolBarArea(toolbar) == Qt.ToolBarArea.TopToolBarArea

    def test_channel_dock_is_on_the_left_with_one_toolbar_per_quantity(self, module):
        assert module.dockWidgetArea(module.channels_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
        for name in ('temperature', 'status', 'exposure', 'trigger'):
            assert module.has_toolbar(name)

    def test_value_widgets_follow_the_declaration(self, module):
        spin = module._value_widgets['exposure']
        assert isinstance(spin, QtWidgets.QDoubleSpinBox)
        assert spin.minimum() == 1 and spin.maximum() == 1000
        assert spin.suffix() == ' ms'
        assert isinstance(module._value_widgets['trigger'], QtWidgets.QComboBox)

    def test_every_measurement_has_a_display(self, module):
        assert set(module._displays) == {'temperature', 'status'}

    def test_status_starts_closed(self, module):
        assert module.status_label.text() == 'not open'


class TestDevice:

    def test_initialize_opens_the_device(self, module, qtbot):
        module.initialize()
        qtbot.waitUntil(lambda: module.status_label.text().startswith('open'), timeout=2000)

    def test_a_spin_edit_writes_the_device(self, module, qtbot):
        module.initialize()
        qtbot.waitUntil(lambda: module.controller.connected, timeout=2000)
        spin = module._value_widgets['exposure']
        spin.setValue(20.0)
        spin.editingFinished.emit()
        plugin = module.controller.thread._plugin
        qtbot.waitUntil(lambda: plugin.written == [('exposure', 20.0)], timeout=2000)

    def test_a_device_write_updates_the_widget_without_writing_back(self, module, qtbot):
        module.initialize()
        qtbot.waitUntil(lambda: module.controller.connected, timeout=2000)
        module.controller.exposure = 50.0
        plugin = module.controller.thread._plugin
        qtbot.waitUntil(lambda: module._value_widgets['exposure'].value() == 50.0, timeout=2000)
        assert plugin.written == [('exposure', 50.0)]

    def test_read_button_shows_the_value(self, module, qtbot):
        module.initialize()
        qtbot.waitUntil(lambda: module.controller.connected, timeout=2000)
        module.get_action('temperature_read').trigger()
        qtbot.waitUntil(lambda: module._displays['temperature'].text() == '2.5 K', timeout=2000)


class TestRelease:

    def test_release_detaches_from_the_registry(self, registry, qtbot):
        key = HardwareKey(hardware_class=Camera, controller_id=3)
        widget = HardwareModule(key, Camera, registry=registry)
        qtbot.addWidget(widget)
        assert registry.is_known(key)
        widget.release()
        assert not registry.is_known(key)

    def test_closing_the_widget_releases_it(self, registry, qtbot):
        key = HardwareKey(hardware_class=Camera, controller_id=4)
        widget = HardwareModule(key, Camera, registry=registry)
        qtbot.addWidget(widget)
        widget.close()
        assert not registry.is_known(key)

    def test_a_widget_edit_after_release_is_ignored(self, registry, qtbot):
        key = HardwareKey(hardware_class=Camera, controller_id=5)
        widget = HardwareModule(key, Camera, registry=registry)
        qtbot.addWidget(widget)
        spin = widget._value_widgets['exposure']
        widget.release()
        spin.setValue(20.0)
        spin.editingFinished.emit()  # no controller left to write to


class TestViews:

    def test_a_control_has_no_graph(self, module):
        assert not module.has_action('exposure_show_graph')
        assert module.has_action('temperature_show_graph')

    def test_show_graph_opens_a_view_without_polling(self, module, qtbot):
        module.initialize()
        qtbot.waitUntil(lambda: module.controller.connected, timeout=2000)
        module.get_action('temperature_show_graph').trigger()
        assert not module._views['temperature'].isHidden()
        assert 'temperature' not in module.controller._polled

    def test_a_read_fills_the_trace(self, module, qtbot):
        module.initialize()
        qtbot.waitUntil(lambda: module.controller.connected, timeout=2000)
        module.get_action('temperature_show_graph').trigger()
        module.get_action('temperature_read').trigger()
        qtbot.waitUntil(lambda: len(module._history['temperature']) == 1, timeout=2000)
        assert module._displays['temperature'].text() == '2.5 K'

    def test_closing_the_view_unchecks_show_graph(self, module, qtbot):
        module.get_action('temperature_show_graph').trigger()
        module._views['temperature'].close()
        assert not module.get_action('temperature_show_graph').isChecked()


class TestGrab:

    @pytest.fixture
    def scope(self, registry, qtbot):
        class Scope(Camera):
            spectrum = measurement(shape=(4,))

        widget = HardwareModule(HardwareKey(hardware_class=Scope, controller_id=7), Scope, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        yield widget
        widget.release()

    def test_grab_polls_the_array_while_checked(self, scope, qtbot):
        scope.get_action('spectrum_grab').trigger()
        assert 'spectrum' in scope.controller._polled
        qtbot.waitUntil(lambda: scope._displays['spectrum'].text() != '-', timeout=2000)

    def test_unchecking_grab_stops_the_poll(self, scope):
        scope.get_action('spectrum_grab').trigger()
        scope.get_action('spectrum_grab').trigger()
        assert 'spectrum' not in scope.controller._polled

    def test_closing_the_device_unchecks_grab(self, scope, qtbot):
        scope.get_action('spectrum_grab').trigger()
        scope.get_action('ini').trigger()  # Ini. toggles the device closed
        qtbot.waitUntil(lambda: not scope.controller.connected, timeout=2000)
        assert not scope.get_action('spectrum_grab').isChecked()

    def test_grab_restarts_when_the_device_reopens(self, scope, qtbot):
        scope.get_action('spectrum_grab').trigger()
        scope.controller.thread.close_hardware()
        qtbot.waitUntil(lambda: not scope.controller.connected, timeout=2000)
        scope.controller.thread.ini_hardware()
        qtbot.waitUntil(lambda: 'spectrum' in scope.controller._polled, timeout=2000)


class TestInstrumentToolbar:

    def test_ini_opens_and_closes_the_device(self, module, qtbot):
        module.get_action('ini').trigger()
        qtbot.waitUntil(lambda: module.controller.connected, timeout=2000)
        assert module.get_action('ini').isChecked()
        module.get_action('ini').trigger()
        qtbot.waitUntil(lambda: not module.controller.connected, timeout=2000)
        assert not module.get_action('ini').isChecked()

    def test_settings_button_toggles_the_settings_dock(self, module):
        module.get_action('show_settings').trigger()
        assert not module.settings_dock.isHidden()
        module.get_action('show_settings').trigger()
        assert module.settings_dock.isHidden()


class TestReadActions:

    def test_a_discrete_measurement_can_be_read(self, module, qtbot):
        module.initialize()
        qtbot.waitUntil(lambda: module.controller.connected, timeout=2000)
        module.get_action('status_read').trigger()
        qtbot.waitUntil(lambda: module._displays['status'].text() == '2.5', timeout=2000)  # Camera returns 2.5 for every name

    def test_an_array_can_be_read_once(self, registry, qtbot):
        class Scope(Camera):
            spectrum = measurement(shape=(4,))

        key = HardwareKey(hardware_class=Scope, controller_id=9)
        widget = HardwareModule(key, Scope, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        widget.get_action('spectrum_read').trigger()
        qtbot.waitUntil(lambda: widget._displays['spectrum'].text() != '-', timeout=2000)
        widget.release()


class TestCaptions:

    def test_the_label_is_shown_and_the_name_is_kept(self, registry, qtbot):
        class Labelled(Camera):
            temperature = measurement(units='K', label='Sensor temperature')

        widget = HardwareModule(HardwareKey(hardware_class=Labelled, controller_id=8), Labelled, registry=registry)
        qtbot.addWidget(widget)
        assert widget.controller.capabilities.measurements[0].name == 'temperature'
        assert widget.get_toolbar('temperature').findChildren(QtWidgets.QLabel)[0].text() == 'SENSOR TEMPERATURE'
        widget.release()

    def test_without_a_label_the_name_is_made_readable(self, module):
        assert module.get_toolbar('temperature').findChildren(QtWidgets.QLabel)[0].text() == 'TEMPERATURE'


class TestSettings:

    def test_an_edit_in_the_settings_dock_reaches_the_plugin(self, registry, qtbot):
        class Gained(Camera):
            params = [{'name': 'gain', 'type': 'float', 'value': 1.0}]

            def __init__(self):
                super().__init__()
                self.committed = []

            def commit_settings(self, param):
                self.committed.append((param.name(), param.value()))

        widget = HardwareModule(HardwareKey(hardware_class=Gained, controller_id=6), Gained, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        widget.controller.settings.child('gain').setValue(3.0)
        plugin = widget.controller.thread._plugin
        qtbot.waitUntil(lambda: ('gain', 3.0) in plugin.committed, timeout=2000)
        widget.release()

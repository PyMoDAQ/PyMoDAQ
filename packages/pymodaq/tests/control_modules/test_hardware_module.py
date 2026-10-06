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
        qtbot.waitUntil(lambda: module._displays['temperature'].text() == '2.5', timeout=2000)


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

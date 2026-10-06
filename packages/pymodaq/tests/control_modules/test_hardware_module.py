"""Tests for HardwareModule: the widget built from capabilities, over a real hardware thread."""
from __future__ import annotations

import numpy as np
import pytest
from qtpy import QtWidgets

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


class TestRows:

    def test_one_row_per_quantity_with_the_default_widgets(self, module):
        assert isinstance(module._value_widgets['exposure'], QtWidgets.QDoubleSpinBox)
        assert isinstance(module._value_widgets['trigger'], QtWidgets.QComboBox)
        assert 'status' in module._displays
        assert 'temperature' in module._displays

    def test_exposure_range_follows_the_declaration(self, module):
        spin = module._value_widgets['exposure']
        assert spin.minimum() == 1 and spin.maximum() == 1000
        assert spin.suffix() == ' ms'

    def test_status_line_starts_closed(self, module):
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
        button = [b for b in module.findChildren(QtWidgets.QPushButton) if b.text() == 'Read'][0]
        button.click()
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

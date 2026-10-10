"""Tests for HardwareModule: the widget built from capabilities, over a real hardware thread."""
from __future__ import annotations

import numpy as np
import pytest
from qtpy import QtWidgets

from qtpy.QtCore import Qt

from pymodaq.control_modules.capabilities import Action, control, measurement
from pymodaq.control_modules.hardware_module import HardwareModule, SLIDER_WIDTH, _colors
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
        assert 'SENSOR TEMPERATURE' in [l.text() for l in widget.get_toolbar('temperature').findChildren(QtWidgets.QLabel)]
        widget.release()

    def test_without_a_label_the_name_is_made_readable(self, module):
        assert 'TEMPERATURE' in [l.text() for l in module.get_toolbar('temperature').findChildren(QtWidgets.QLabel)]


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

    def test_a_device_driven_change_updates_the_dock_widget(self, registry, qtbot):
        """Guards against blocking the Parameter's signals on the GUI side, which would also silence the dock."""
        class Gained(Camera):
            params = [{'name': 'gain', 'type': 'float', 'value': 1.0}]

        widget = HardwareModule(HardwareKey(hardware_class=Gained, controller_id=7), Gained, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        widget.controller.thread._plugin_settings.child('gain').setValue(9.0)  # as the plugin would, on its own
        qtbot.waitUntil(lambda: widget.controller.settings.child('gain').value() == 9.0, timeout=2000)
        item = next(iter(widget.controller.settings.child('gain').items))
        assert item.widget.value() == 9.0  # the dock's own widget refreshed, not just the model
        widget.release()


class TestChannelLeds:

    def led(self, module, name):
        return module._led_color(name).name()

    def test_leds_are_grey_while_the_device_is_closed(self, module):
        assert self.led(module, 'temperature') == '#9e9e9e'

    def test_leds_are_green_when_the_device_is_open(self, module, qtbot):
        module.initialize()
        qtbot.waitUntil(lambda: module.controller.connected, timeout=2000)
        assert self.led(module, 'temperature') == module._led_color('temperature').name() != '#9e9e9e'
        assert self.led(module, 'exposure') == _colors().green.name()

    def test_a_grabbed_channel_is_blue(self, module, qtbot):
        module.initialize()
        qtbot.waitUntil(lambda: module.controller.connected, timeout=2000)
        module.get_action('temperature_grab').trigger()
        assert self.led(module, 'temperature') == _colors().blue.name()

    def test_a_rejected_write_turns_the_led_red_until_the_next_good_write(self, registry, qtbot):
        class Faulty(Camera):
            def write(self, name, value):
                if value == 'external':
                    raise RuntimeError('link down')
                super().write(name, value)

        widget = HardwareModule(HardwareKey(hardware_class=Faulty, controller_id=10), Faulty, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        combo = widget._value_widgets['trigger']
        combo.setCurrentIndex(1)
        combo.activated.emit(1)  # 'external' is rejected
        qtbot.waitUntil(lambda: self.led(widget, 'trigger') == _colors().red.name(), timeout=2000)
        assert 'link down' in widget.status_label.text()
        combo.setCurrentIndex(0)
        combo.activated.emit(0)  # 'internal' is accepted
        qtbot.waitUntil(lambda: self.led(widget, 'trigger') == _colors().green.name(), timeout=2000)
        widget.release()


class TestSlider:

    @pytest.fixture
    def stage(self, registry, qtbot):
        class Axis(Camera):
            x = control(units='mm', lo=0, hi=50, ui_add=('slider',))

        widget = HardwareModule(HardwareKey(hardware_class=Axis, controller_id=11), Axis, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        yield widget
        widget.release()

    def test_releasing_the_slider_writes_its_value_in_the_range(self, stage, qtbot):
        slider = stage._sliders['x']
        slider.setValue(500)  # half of the 0 to 50 mm range
        slider.sliderReleased.emit()
        plugin = stage.controller.thread._plugin
        qtbot.waitUntil(lambda: ('x', 25.0) in plugin.written, timeout=2000)  # setValue and release both write

    def test_a_device_write_moves_the_slider_without_writing_back(self, stage, qtbot):
        plugin = stage.controller.thread._plugin
        stage.controller.x = 10.0
        qtbot.waitUntil(lambda: stage._sliders['x'].value() == 200, timeout=2000)
        assert plugin.written == [('x', 10.0)]

    def test_a_slider_has_a_channel_row_with_the_same_columns(self, stage):
        assert stage._sliders['x'].width() == SLIDER_WIDTH


class TestToggle:

    @pytest.fixture
    def powered(self, registry, qtbot):
        class Switch(Camera):
            powered = control(values=['off', 'on'], widget='toggle')

        widget = HardwareModule(HardwareKey(hardware_class=Switch, controller_id=13), Switch, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        yield widget
        widget.release()

    def test_a_toggle_opts_into_a_checkable_button_instead_of_a_selector(self, powered):
        button = powered._value_widgets['powered']
        assert isinstance(button, QtWidgets.QPushButton)
        assert button.isCheckable()
        assert button.text() == 'off'

    def test_clicking_the_button_writes_the_second_value(self, powered, qtbot):
        button = powered._value_widgets['powered']
        button.setChecked(True)
        plugin = powered.controller.thread._plugin
        qtbot.waitUntil(lambda: plugin.written == [('powered', 'on')], timeout=2000)
        assert button.text() == 'on'

    def test_a_device_write_updates_the_button_without_writing_back(self, powered, qtbot):
        plugin = powered.controller.thread._plugin
        powered.controller.powered = 'on'
        qtbot.waitUntil(lambda: powered._value_widgets['powered'].isChecked(), timeout=2000)
        assert powered._value_widgets['powered'].text() == 'on'
        assert plugin.written == [('powered', 'on')]  # the programmatic update did not write again


class TestReadbackRows:

    @pytest.fixture
    def axis(self, registry, qtbot):
        class Axis(Camera):
            x = control(units='mm', lo=0, hi=50, readback='temperature')

        widget = HardwareModule(HardwareKey(hardware_class=Axis, controller_id=12), Axis, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        yield widget
        widget.release()

    def test_the_readback_is_in_its_controls_row(self, axis):
        assert not axis.has_toolbar('temperature')
        assert axis.has_toolbar('x')
        assert axis.has_action('temperature_grab')

    def test_the_readback_display_follows_its_reading(self, axis, qtbot):
        axis.get_action('temperature_read').trigger()
        qtbot.waitUntil(lambda: axis._displays['temperature'].text() == '2.5 K', timeout=2000)

    def test_the_led_of_the_row_turns_blue_when_the_readback_is_grabbed(self, axis):
        axis.get_action('temperature_grab').trigger()
        assert axis._led_color('x').name() == _colors().blue.name()

    def test_the_led_widget_itself_refreshes_not_just_the_colour_lookup(self, axis):
        # _refresh_led is called with the readback's own name here, not the row: it must still
        # find and repaint the row's MultistateLED, not just leave _led_state correct on paper.
        axis.get_action('temperature_grab').trigger()
        led = axis._leds['x']
        assert led.get_state() == 'active'


class _Values:
    """A reading holding the given arrays, one per channel."""

    def __init__(self, arrays):
        self._arrays = arrays

    def get_data_from_name(self, name):
        return self._arrays[name]


class TestNamedReadback:

    def test_a_named_readback_is_read_through_the_device(self, registry, qtbot):
        class Stage:
            params: list = []
            z = control(units='mm', lo=0, hi=10, readback='my_z_readback')
            readings = {'my_z_readback': 4.5}

            def open(self, settings):
                pass

            def close(self):
                pass

            def read(self, names=None, fresh=True):
                return _Values({name: np.array([self.readings[name]]) for name in names})

            def write(self, name, value):
                pass

        widget = HardwareModule(HardwareKey(hardware_class=Stage, controller_id=13), Stage, registry=registry)
        qtbot.addWidget(widget)
        assert widget.has_action('my_z_readback_read')  # the readback is in the z row
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        widget.get_action('my_z_readback_read').trigger()
        qtbot.waitUntil(lambda: widget._displays['my_z_readback'].text() == '4.5 mm', timeout=2000)
        widget.release()


class SettlingStage(Camera):
    """A control whose readback trails the target until advance() is called: real settling, not instant."""

    z = control(units='mm', lo=0, hi=50, epsilon=0.5, readback=True)

    def __init__(self):
        super().__init__()
        self._position = 0.0
        self.target = None

    def write(self, name, value):
        super().write(name, value)
        if name == 'z':
            self.target = value  # the device accepts the move at once; getting there takes longer

    def read(self, names=None, fresh=True):
        arrays = {}
        for name in names:
            arrays[name] = np.array([self._position]) if name == 'z_readback' else np.array([2.5])
        return _Values(arrays)

    def advance(self):
        """Simulates the device reaching the target, as if polled motion had caught up."""
        if self.target is not None:
            self._position = self.target


class TestSettle:
    """A control with a readback and an epsilon stays pending until the readback reaches the target."""

    @pytest.fixture
    def stage(self, registry, qtbot):
        widget = HardwareModule(HardwareKey(hardware_class=SettlingStage, controller_id=14),
                                SettlingStage, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        yield widget
        widget.release()

    def test_a_plain_write_without_readback_and_epsilon_clears_at_once(self, module, qtbot):
        # Camera.exposure has no readback: nothing to settle towards, so write_done is enough (unchanged
        # behaviour, kept here so a regression in _settles() shows up in both directions).
        module.initialize()
        qtbot.waitUntil(lambda: module.controller.connected, timeout=2000)
        spin = module._value_widgets['exposure']
        spin.setValue(20.0)
        spin.editingFinished.emit()
        qtbot.waitUntil(lambda: module._led_color('exposure').name() == _colors().green.name(), timeout=2000)

    def test_led_stays_orange_after_write_done_until_the_readback_settles(self, stage, qtbot):
        plugin = stage.controller.thread._plugin
        spin = stage._value_widgets['z']
        spin.setValue(20.0)
        spin.editingFinished.emit()
        qtbot.waitUntil(lambda: plugin.target == 20.0, timeout=2000)  # the write reached the plugin
        assert stage._led_color('z').name() == _colors().orange.name()  # but the readback hasn't moved
        plugin.advance()  # now it has
        qtbot.waitUntil(lambda: stage._led_color('z').name() == _colors().green.name(), timeout=3000)

    def test_a_rejected_write_cancels_the_settle_watch(self, registry, qtbot):
        class Faulty(SettlingStage):
            def write(self, name, value):
                raise RuntimeError('stalled')

        widget = HardwareModule(HardwareKey(hardware_class=Faulty, controller_id=15), Faulty, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        spin = widget._value_widgets['z']
        spin.setValue(20.0)
        spin.editingFinished.emit()
        qtbot.waitUntil(lambda: widget._led_color('z').name() == _colors().red.name(), timeout=2000)
        assert 'z' not in widget._settle_timers
        widget.release()


class StoppableAxis(Camera):
    z = control(units='mm', lo=0, hi=50, stop=lambda plugin: plugin.stop_calls.append(True))

    def __init__(self):
        super().__init__()
        self.stop_calls = []


class TestStopButton:
    """stop is opt-in: only a control that declares a stop callback gets the button."""

    def test_a_control_without_a_stop_callback_has_no_stop_action(self, module):
        assert not module.has_action('exposure_stop')

    def test_a_control_with_a_stop_callback_gets_one(self, registry, qtbot):
        widget = HardwareModule(HardwareKey(hardware_class=StoppableAxis, controller_id=16),
                                StoppableAxis, registry=registry)
        qtbot.addWidget(widget)
        assert widget.has_action('z_stop')
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        plugin = widget.controller.thread._plugin
        widget.get_action('z_stop').trigger()
        qtbot.waitUntil(lambda: plugin.stop_calls == [True], timeout=2000)
        widget.release()


class StoppableSettlingStage(SettlingStage):
    """Like SettlingStage, but z's stop freezes the target at the current position and reports it
    back - the stage example's real pattern, exercised together with settling."""

    z = control(units='mm', lo=0, hi=50, epsilon=0.5, readback=True, stop=lambda plugin: plugin._freeze())

    def _freeze(self):
        self.target = self._position
        return self.target


class FailingStopStage(SettlingStage):
    """z's stop always raises, as a real hardware refusal would."""

    z = control(units='mm', lo=0, hi=50, epsilon=0.5, readback=True,
               stop=lambda plugin: (_ for _ in ()).throw(RuntimeError('refused')))


class TestStopConfirmation:
    """A row's pending/rejected state clears for stop only once it is confirmed to have run, not
    optimistically when the button is clicked - a real hardware refusal must not look like success."""

    def test_a_failing_stop_does_not_clear_the_pending_state(self, registry, qtbot):
        widget = HardwareModule(HardwareKey(hardware_class=FailingStopStage, controller_id=28),
                                FailingStopStage, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        spin = widget._value_widgets['z']
        spin.setValue(20.0)
        spin.editingFinished.emit()
        qtbot.waitUntil(lambda: 'z' in widget._pending, timeout=2000)  # accepted, now settling (orange)
        widget.get_action('z_stop').trigger()
        qtbot.wait(300)  # give the (failing) stop every chance to run and report back
        assert 'z' in widget._pending  # the callback raised: must not look like a successful stop
        assert widget._led_color('z').name() != _colors().green.name()
        widget.release()

    def test_a_successful_stop_clears_the_pending_state_once_confirmed(self, registry, qtbot):
        widget = HardwareModule(HardwareKey(hardware_class=StoppableSettlingStage, controller_id=29),
                                StoppableSettlingStage, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        plugin = widget.controller.thread._plugin
        spin = widget._value_widgets['z']
        spin.setValue(20.0)
        spin.editingFinished.emit()
        qtbot.waitUntil(lambda: 'z' in widget._pending, timeout=2000)  # accepted, now settling (orange)
        plugin._position = 7.0  # the axis is partway there when stop is pressed
        widget.get_action('z_stop').trigger()
        qtbot.waitUntil(lambda: 'z' not in widget._pending, timeout=2000)
        assert widget._led_color('z').name() == _colors().green.name()

    def test_a_successful_stop_updates_the_spinbox_to_the_frozen_position(self, registry, qtbot):
        widget = HardwareModule(HardwareKey(hardware_class=StoppableSettlingStage, controller_id=30),
                                StoppableSettlingStage, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        plugin = widget.controller.thread._plugin
        spin = widget._value_widgets['z']
        spin.setValue(20.0)
        spin.editingFinished.emit()
        qtbot.waitUntil(lambda: 'z' in widget._pending, timeout=2000)
        plugin._position = 7.0
        widget.get_action('z_stop').trigger()
        qtbot.waitUntil(lambda: spin.value() == 7.0, timeout=2000)  # not left at the stale 20.0


class HomableAxis(Camera):
    z = control(units='mm', lo=0, hi=50, actions={'home': lambda plugin: plugin.home_calls.append(True)})

    def __init__(self):
        super().__init__()
        self.home_calls = []


class TestCustomAction:
    """A control's one declared action, under its own name, not just 'stop'."""

    def test_the_button_is_named_and_labelled_after_the_action(self, registry, qtbot):
        widget = HardwareModule(HardwareKey(hardware_class=HomableAxis, controller_id=17),
                                HomableAxis, registry=registry)
        qtbot.addWidget(widget)
        assert widget.has_action('z_home')
        assert widget.get_action('z_home').text() == 'Home'
        widget.release()

    def test_clicking_it_calls_the_action(self, registry, qtbot):
        widget = HardwareModule(HardwareKey(hardware_class=HomableAxis, controller_id=18),
                                HomableAxis, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        plugin = widget.controller.thread._plugin
        widget.get_action('z_home').trigger()
        qtbot.waitUntil(lambda: plugin.home_calls == [True], timeout=2000)
        widget.release()


class MeasurementWithAction(Camera):
    temperature = measurement(units='K', actions={'take_background': lambda plugin: plugin.bkg_calls.append(True)})

    def __init__(self):
        super().__init__()
        self.bkg_calls = []


class CheckableAction(Camera):
    temperature = measurement(units='K', actions={
        'subtract_bkg': Action(lambda plugin, checked: plugin.toggle_calls.append(checked), checkable=True),
    })

    def __init__(self):
        super().__init__()
        self.toggle_calls = []


class TestActionOnAMeasurement:
    """An action isn't control-specific: a measurement can declare one too (e.g. a spectrum's
    background capture), and a checkable one reports which way it flipped."""

    def test_a_measurement_can_have_an_action_button(self, registry, qtbot):
        widget = HardwareModule(HardwareKey(hardware_class=MeasurementWithAction, controller_id=30),
                                MeasurementWithAction, registry=registry)
        qtbot.addWidget(widget)
        assert widget.has_action('temperature_take_background')
        widget.release()

    def test_clicking_a_measurements_action_calls_it(self, registry, qtbot):
        widget = HardwareModule(HardwareKey(hardware_class=MeasurementWithAction, controller_id=31),
                                MeasurementWithAction, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        plugin = widget.controller.thread._plugin
        widget.get_action('temperature_take_background').trigger()
        qtbot.waitUntil(lambda: plugin.bkg_calls == [True], timeout=2000)
        widget.release()

    def test_a_checkable_action_reports_the_new_checked_state_each_click(self, registry, qtbot):
        widget = HardwareModule(HardwareKey(hardware_class=CheckableAction, controller_id=32),
                                CheckableAction, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        plugin = widget.controller.thread._plugin
        button = widget.get_action('temperature_subtract_bkg')
        assert button.isCheckable()
        button.trigger()  # checks it
        qtbot.waitUntil(lambda: plugin.toggle_calls == [True], timeout=2000)
        button.trigger()  # unchecks it
        qtbot.waitUntil(lambda: plugin.toggle_calls == [True, False], timeout=2000)
        widget.release()


class StageWithEnable(Camera):
    x = control(units='mm', lo=0, hi=50)
    x_enable = control(values=['disabled', 'enabled'], merge_into='x',
                       set=lambda plugin, value: plugin.enable_writes.append(value))

    def __init__(self):
        super().__init__()
        self.enable_writes = []


class TestMergedAction:
    """merge_into: a binary control rendered as a checkable action in another control's own row."""

    @pytest.fixture
    def stage(self, registry, qtbot):
        widget = HardwareModule(HardwareKey(hardware_class=StageWithEnable, controller_id=19),
                                StageWithEnable, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        yield widget
        widget.release()

    def test_the_merged_control_has_no_row_of_its_own(self, stage):
        assert not stage.has_toolbar('x_enable')
        assert stage.has_toolbar('x')

    def test_it_renders_as_a_checkable_action_on_the_hosts_row(self, stage):
        action = stage.get_action('x_enable_merged')
        assert action.isCheckable()
        assert not action.isChecked()

    def test_triggering_it_writes_the_merged_controls_second_value(self, stage, qtbot):
        plugin = stage.controller.thread._plugin
        stage.get_action('x_enable_merged').trigger()
        qtbot.waitUntil(lambda: plugin.enable_writes == ['enabled'], timeout=2000)

    def test_a_device_write_updates_the_action_without_writing_back(self, stage, qtbot):
        plugin = stage.controller.thread._plugin
        stage.controller.x_enable = 'enabled'
        qtbot.waitUntil(lambda: stage.get_action('x_enable_merged').isChecked(), timeout=2000)
        assert plugin.enable_writes == ['enabled']  # the programmatic update did not write again

class StageWithFailingEnable(Camera):
    x = control(units='mm', lo=0, hi=50)
    x_enable = control(values=['disabled', 'enabled'], merge_into='x',
                       set=lambda plugin, value: (_ for _ in ()).throw(RuntimeError('nope')))


class TestMergedActionFailure:

    def test_a_rejected_merged_write_turns_the_hosts_row_red(self, registry, qtbot):
        widget = HardwareModule(HardwareKey(hardware_class=StageWithFailingEnable, controller_id=20),
                                StageWithFailingEnable, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        widget.get_action('x_enable_merged').trigger()
        qtbot.waitUntil(lambda: widget._led_color('x').name() == _colors().red.name(), timeout=2000)
        widget.release()


class CameraWithChannelEnable(Camera):
    temperature_enable = control(values=['disabled', 'enabled'], merge_into='temperature',
                                 set=lambda plugin, value: plugin.enable_writes.append(value))

    def __init__(self):
        super().__init__()
        self.enable_writes = []


class TestMergedActionOnAMeasurement:
    """merge_into isn't control-only either: a channel's enable rides along its own row the same
    way an axis's enable does - the write still goes through the control's own set, only where the
    button is drawn changes."""

    @pytest.fixture
    def camera(self, registry, qtbot):
        widget = HardwareModule(HardwareKey(hardware_class=CameraWithChannelEnable, controller_id=33),
                                CameraWithChannelEnable, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        yield widget
        widget.release()

    def test_the_merged_control_has_no_row_of_its_own(self, camera):
        assert not camera.has_toolbar('temperature_enable')
        assert camera.has_toolbar('temperature')

    def test_triggering_it_writes_the_merged_controls_second_value(self, camera, qtbot):
        plugin = camera.controller.thread._plugin
        camera.get_action('temperature_enable_merged').trigger()
        qtbot.waitUntil(lambda: plugin.enable_writes == ['enabled'], timeout=2000)


class TestWidgetSync:
    """A quantity shown by several widgets (value spinbox, slider, ...) all stay in sync with one write."""

    @pytest.fixture
    def axis(self, registry, qtbot):
        class Axis(Camera):
            x = control(units='mm', lo=0, hi=50, ui_add=('slider',))

        widget = HardwareModule(HardwareKey(hardware_class=Axis, controller_id=22), Axis, registry=registry)
        qtbot.addWidget(widget)
        widget.initialize()
        qtbot.waitUntil(lambda: widget.controller.connected, timeout=2000)
        yield widget
        widget.release()

    def test_a_device_write_updates_both_the_spinbox_and_the_slider(self, axis, qtbot):
        axis.controller.x = 25.0
        qtbot.waitUntil(lambda: axis._value_widgets['x'].value() == 25.0, timeout=2000)
        assert axis._sliders['x'].value() == 500  # half of the 0-50 mm range

    def test_writing_through_the_slider_updates_the_spinbox_too(self, axis, qtbot):
        axis._sliders['x'].setValue(200)  # 20% of 0-50 mm
        axis._sliders['x'].sliderReleased.emit()
        qtbot.waitUntil(lambda: axis._value_widgets['x'].value() == 10.0, timeout=2000)

    def test_a_write_from_the_controller_updates_both_widgets_too(self, axis, qtbot):
        axis._value_widgets['x'].setValue(25.0)
        axis._value_widgets['x'].editingFinished.emit()
        qtbot.waitUntil(lambda: axis._sliders['x'].value() == 500, timeout=2000)
        axis.controller.x = 10.0
        qtbot.waitUntil(lambda: axis._value_widgets['x'].value() == 10.0, timeout=2000)
        assert axis._sliders['x'].value() == 200

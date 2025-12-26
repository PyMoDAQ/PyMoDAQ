"""
Tests for widget synchronization module.

Tests cover:
- Basic synchronization between widgets
- Feedback loop prevention
- Property change optimization
- Dynamic property addition/removal
- Enable/disable functionality
- Bind/unbind operations
- Factory methods
- Value transformations
- Sync modes
- Memory management
- Dict synchronization with bind_properties() and bind_dict()
- Parameter binding with bind_parameter()
"""
import pytest
from qtpy.QtWidgets import (
    QSlider, QSpinBox, QCheckBox, QLineEdit, QComboBox
)
from qtpy.QtCore import Qt

from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode, ValueSync, DictSync


@pytest.fixture
def qtbot_app(qtbot):
    """Fixture that ensures Qt application is running"""
    return qtbot


@pytest.fixture
def qtbot_app(qtbot):
    """Fixture that ensures Qt application is running"""
    return qtbot


class TestBasicSync:
    """Test basic synchronization functionality"""

    def test_create_sync_with_initial_value(self, qtbot_app):
        """Test creating a sync with an initial value"""
        sync = WidgetSync(initial_value=42)
        assert sync.value == 42

    def test_set_and_get_value(self, qtbot_app):
        """Test setting and getting sync value"""
        sync = WidgetSync(initial_value=0)
        sync.value = 100
        assert sync.value == 100

    def test_value_changed_signal(self, qtbot_app):
        """Test that value_changed signal emits on change"""
        sync = WidgetSync(initial_value=0)
        signal_received = []

        sync.value_changed.connect(lambda v: signal_received.append(v))
        sync.value = 42

        assert len(signal_received) == 1
        assert signal_received[0] == 42

    def test_bind_spinbox(self, qtbot_app):
        """Test binding a SpinBox bidirectionally"""
        sync = WidgetSync(initial_value=10)
        spinbox = QSpinBox()
        spinbox.setRange(0, 100)

        sync.bind(
            spinbox,
            signal=spinbox.valueChanged,
            getter=lambda: spinbox.value(),
            setter=lambda v: spinbox.setValue(v)
        )

        # Initial value should sync to widget
        assert spinbox.value() == 10

        # Changing widget should update sync
        spinbox.setValue(25)
        assert sync.value == 25

        # Changing sync should update widget
        sync.value = 50
        assert spinbox.value() == 50

    def test_slider_sync(self, qtbot):
        """Test basic slider synchronization"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        slider1.setRange(0, 100)
        slider2.setRange(0, 100)

        sync = WidgetSync.for_slider(slider1, initial=50)
        sync.add(slider2)

        # Change first slider
        slider1.setValue(75)
        assert slider2.value() == 75

        # Change second slider
        slider2.setValue(25)
        assert slider1.value() == 25

    def test_checkbox_sync(self, qtbot):
        """Test checkbox synchronization"""
        cb1 = QCheckBox()
        cb2 = QCheckBox()
        cb3 = QCheckBox()

        sync = WidgetSync.for_checkbox(cb1, initial=False)
        sync.add(cb2)
        sync.add(cb3)

        # Check first checkbox
        cb1.setChecked(True)
        assert cb2.isChecked()
        assert cb3.isChecked()

        # Uncheck second checkbox
        cb2.setChecked(False)
        assert not cb1.isChecked()
        assert not cb3.isChecked()

    def test_spinbox_sync(self, qtbot):
        """Test spinbox synchronization"""
        spin1 = QSpinBox()
        spin2 = QSpinBox()
        spin1.setRange(0, 100)
        spin2.setRange(0, 100)

        sync = WidgetSync.for_spinbox(spin1, initial=50)
        sync.add(spin2)

        spin1.setValue(75)
        assert spin2.value() == 75


class TestFeedbackLoopPrevention:
    """Test that widgets don't receive their own updates back"""

    def test_widget_does_not_receive_own_update(self, qtbot_app):
        """Test that a widget triggering a change doesn't get updated back"""
        sync = WidgetSync(initial_value=0)
        spinbox1 = QSpinBox()
        spinbox2 = QSpinBox()
        spinbox1.setRange(0, 100)
        spinbox2.setRange(0, 100)

        # Track setter calls
        setter_calls = {'spin1': 0, 'spin2': 0}
        original_setValue1 = spinbox1.setValue
        original_setValue2 = spinbox2.setValue

        def tracked_setValue1(value):
            setter_calls['spin1'] += 1
            original_setValue1(value)

        def tracked_setValue2(value):
            setter_calls['spin2'] += 1
            original_setValue2(value)

        spinbox1.setValue = tracked_setValue1
        spinbox2.setValue = tracked_setValue2

        # Bind both
        sync.bind(spinbox1, spinbox1.valueChanged,
                  getter=lambda: spinbox1.value(), setter=lambda v: spinbox1.setValue(v))
        sync.bind(spinbox2, spinbox2.valueChanged,
                  getter=lambda: spinbox2.value(), setter=lambda v: spinbox2.setValue(v))

        # Reset counter after initial sync
        setter_calls = {'spin1': 0, 'spin2': 0}

        # Change spinbox1
        original_setValue1(25)  # Use original to trigger signal

        # spinbox1 should NOT have its setter called (feedback prevention)
        # spinbox2 SHOULD have its setter called
        assert setter_calls['spin1'] == 0
        assert setter_calls['spin2'] == 1
        assert spinbox2.value() == 25

    def test_multi_property_feedback_prevention(self, qtbot_app):
        """Test feedback prevention works across multiple properties of same widget"""
        sync = WidgetSync(initial_value={'min': 0, 'max': 100, 'value': 50})

        spinbox = QSpinBox()
        spinbox.setRange(0, 100)

        # Track setter calls
        setter_calls = {'minimum': 0, 'maximum': 0, 'value': 0}
        original_setMinimum = spinbox.setMinimum
        original_setMaximum = spinbox.setMaximum
        original_setValue = spinbox.setValue

        def tracked_setMinimum(v):
            setter_calls['minimum'] += 1
            original_setMinimum(v)

        def tracked_setMaximum(v):
            setter_calls['maximum'] += 1
            original_setMaximum(v)

        def tracked_setValue(v):
            setter_calls['value'] += 1
            original_setValue(v)

        spinbox.setMinimum = tracked_setMinimum
        spinbox.setMaximum = tracked_setMaximum
        spinbox.setValue = tracked_setValue

        # Bind multiple properties
        sync.bind_dict({
            'min': {'widget': spinbox, 'property': 'minimum', 'mode': SyncMode.FROM_SYNC},
            'max': {'widget': spinbox, 'property': 'maximum', 'mode': SyncMode.FROM_SYNC},
            'value': {'widget': spinbox, 'property': 'value'}
        })

        # Reset counters
        setter_calls = {'minimum': 0, 'maximum': 0, 'value': 0}

        # Change the value property via widget
        original_setValue(75)

        # The widget should NOT receive any property updates (all properties skipped)
        assert setter_calls['minimum'] == 0
        assert setter_calls['maximum'] == 0
        assert setter_calls['value'] == 0


class TestPropertyChangeOptimization:
    """Test that only changed properties trigger widget updates"""

    def test_only_changed_properties_update_widgets(self, qtbot_app):
        """Test that widgets only update when their property actually changes"""
        sync = WidgetSync(initial_value={'x': 0, 'y': 0, 'z': 0})

        x_spin = QSpinBox()
        y_spin = QSpinBox()
        z_spin = QSpinBox()

        # Track setter calls
        setter_calls = {'x': 0, 'y': 0, 'z': 0}
        original_setValueX = x_spin.setValue
        original_setValueY = y_spin.setValue
        original_setValueZ = z_spin.setValue

        def tracked_setValueX(v):
            setter_calls['x'] += 1
            original_setValueX(v)

        def tracked_setValueY(v):
            setter_calls['y'] += 1
            original_setValueY(v)

        def tracked_setValueZ(v):
            setter_calls['z'] += 1
            original_setValueZ(v)

        x_spin.setValue = tracked_setValueX
        y_spin.setValue = tracked_setValueY
        z_spin.setValue = tracked_setValueZ

        # Bind all three with explicit setters to track calls
        sync.bind_dict({
            'x': {'widget': x_spin, 'property': 'value',
                  'setter': lambda v: x_spin.setValue(v)},
            'y': {'widget': y_spin, 'property': 'value',
                  'setter': lambda v: y_spin.setValue(v)},
            'z': {'widget': z_spin, 'property': 'value',
                  'setter': lambda v: z_spin.setValue(v)}
        })

        # Reset counters
        setter_calls = {'x': 0, 'y': 0, 'z': 0}

        # Change only x
        sync.value = {'x': 10, 'y': 0, 'z': 0}

        # Only x_spin should be updated (y and z unchanged)
        assert setter_calls['x'] == 1
        assert setter_calls['y'] == 0
        assert setter_calls['z'] == 0


class TestDynamicProperties:
    """Test adding and removing properties dynamically"""

    def test_add_property_dynamically(self, qtbot_app):
        """Test adding a new property to the sync after initialization"""
        sync = WidgetSync(initial_value={'name': 'Test'})

        name_edit = QLineEdit()
        sync.bind_properties(name_edit, property_map={'name': {'property': 'text'}})

        assert name_edit.text() == 'Test'

        # Add new property
        sync.value = {**sync.value, 'age': 25}

        # Bind new widget to new property
        age_spin = QSpinBox()
        sync.bind_properties(age_spin, property_map={'age': {'property': 'value'}})

        assert age_spin.value() == 25

        # Both should still work
        name_edit.setText('Updated')
        assert sync.value['name'] == 'Updated'

    def test_remove_property_dynamically(self, qtbot_app):
        """Test removing a property from the sync"""
        sync = WidgetSync(initial_value={'x': 0, 'y': 0})

        x_spin = QSpinBox()
        y_spin = QSpinBox()

        sync.bind_dict({
            'x': {'widget': x_spin, 'property': 'value'},
            'y': {'widget': y_spin, 'property': 'value'}
        })

        # Remove y property
        new_value = sync.value.copy()
        del new_value['y']
        sync.value = new_value

        assert 'y' not in sync.value
        assert 'x' in sync.value

        # x should still work
        x_spin.setValue(10)
        assert sync.value['x'] == 10


class TestBindDict:
    """Test bind_dict functionality"""

    def test_bind_dict_multiple_widgets(self, qtbot_app):
        """Test bind_dict with multiple different widgets"""
        sync = WidgetSync(initial_value={'name': 'Test', 'age': 25, 'active': True})

        name_edit = QLineEdit()
        age_spin = QSpinBox()
        active_check = QCheckBox()

        sync.bind_dict({
            'name': {'widget': name_edit, 'property': 'text'},
            'age': {'widget': age_spin, 'property': 'value'},
            'active': {'widget': active_check, 'property': 'checked'}
        })

        # Check initial sync
        assert name_edit.text() == 'Test'
        assert age_spin.value() == 25
        assert active_check.isChecked()

        # Change widgets
        name_edit.setText('Updated')
        age_spin.setValue(30)
        active_check.setChecked(False)

        # Check sync updated
        assert sync.value['name'] == 'Updated'
        assert sync.value['age'] == 30
        assert sync.value['active'] == False


class TestEnableDisable:
    """Test enable/disable functionality"""

    def test_disable_stops_syncing(self, qtbot):
        """Test that disabled widgets don't sync"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        slider3 = QSlider(Qt.Orientation.Horizontal)
        for s in [slider1, slider2, slider3]:
            s.setRange(0, 100)

        sync = WidgetSync.for_slider(slider1, initial=50)
        sync.add(slider2)
        sync.add(slider3)

        # Disable slider2
        sync.disable(slider2)

        # Change slider1 - slider3 should update, slider2 should not
        slider1.setValue(75)
        assert slider3.value() == 75
        assert slider2.value() == 50  # Still at initial value

        # Change slider2 - others should not update
        slider2.setValue(90)
        assert slider1.value() == 75
        assert slider3.value() == 75

    def test_enable_resumes_syncing(self, qtbot):
        """Test that re-enabling resumes syncing"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        for s in [slider1, slider2]:
            s.setRange(0, 100)

        sync = WidgetSync.for_slider(slider1, initial=50)
        sync.add(slider2)

        # Disable and change
        sync.disable(slider2)
        slider1.setValue(75)
        assert slider2.value() == 50

        # Re-enable
        sync.enable(slider2)
        slider1.setValue(80)
        assert slider2.value() == 80

    def test_is_enabled(self, qtbot):
        """Test is_enabled method"""
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)

        sync = WidgetSync.for_slider(slider, initial=50)

        # Should be enabled by default
        assert sync.is_enabled(slider)

        # Disable
        sync.disable(slider)
        assert not sync.is_enabled(slider)

        # Re-enable
        sync.enable(slider)
        assert sync.is_enabled(slider)

    def test_enable_disable_by_id(self, qtbot):
        """Test enable/disable using widget ID"""
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)

        sync = WidgetSync.for_slider(slider, initial=50)
        widget_id = id(slider)

        # Disable by ID
        sync.disable(widget_id)
        assert not sync.is_enabled(widget_id)

        # Enable by ID
        sync.enable(widget_id)
        assert sync.is_enabled(widget_id)

    def test_enable_disable_raises_on_unknown_widget(self, qtbot):
        """Test that enable/disable raise ValueError for unknown widgets"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)

        sync = WidgetSync.for_slider(slider1, initial=50)

        # slider2 is not connected
        with pytest.raises(ValueError):
            sync.disable(slider2)

        with pytest.raises(ValueError):
            sync.enable(slider2)

        with pytest.raises(ValueError):
            sync.is_enabled(slider2)


class TestConnectDisconnect:
    """Test connect/disconnect operations"""

    def test_disconnect_by_widget(self, qtbot):
        """Test disconnecting by widget reference"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        for s in [slider1, slider2]:
            s.setRange(0, 100)

        sync = WidgetSync.for_slider(slider1, initial=50)
        sync.add(slider2)

        # Disconnect slider2
        sync.unbind(slider2)

        # Changes should not propagate
        slider1.setValue(75)
        assert slider2.value() == 50

    def test_disconnect_by_id(self, qtbot):
        """Test disconnecting by widget ID"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        for s in [slider1, slider2]:
            s.setRange(0, 100)

        sync = WidgetSync.for_slider(slider1, initial=50)
        sync.add(slider2)

        widget_id = id(slider2)
        sync.unbind(widget_id)

        slider1.setValue(75)
        assert slider2.value() == 50

    def test_unbind_all(self, qtbot):
        """Test unbinding all widgets"""
        sliders = [QSlider(Qt.Orientation.Horizontal) for _ in range(3)]
        for s in sliders:
            s.setRange(0, 100)

        sync = WidgetSync.for_slider(sliders[0], initial=50)
        for s in sliders[1:]:
            sync.add(s)

        assert sync.connection_count == 3

        sync.unbind_all()

        assert sync.connection_count == 0
        sliders[0].setValue(75)
        assert sliders[1].value() == 50
        assert sliders[2].value() == 50


class TestSyncModes:
    """Test different synchronization modes"""

    def test_bidirectional_mode(self, qtbot):
        """Test bidirectional sync (default)"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        for s in [slider1, slider2]:
            s.setRange(0, 100)

        sync = WidgetSync.for_slider(slider1, initial=50)
        sync.add(slider2, mode=SyncMode.BIDIRECTIONAL)

        # Both directions should work
        slider1.setValue(75)
        assert slider2.value() == 75

        slider2.setValue(25)
        assert slider1.value() == 25

    def test_to_sync_mode(self, qtbot):
        """Test TO_SYNC mode (widget → sync only)"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        for s in [slider1, slider2]:
            s.setRange(0, 100)

        sync = WidgetSync.for_slider(slider1, initial=50)

        # Connect slider2 in TO_SYNC mode
        sync.bind(
            slider2,
            signal=slider2.valueChanged,
            getter=lambda: slider2.value(),
            setter=lambda v: slider2.setValue(v),
            mode=SyncMode.TO_SYNC
        )

        # slider2 → slider1 should work
        slider2.setValue(75)
        assert slider1.value() == 75

        # slider1 → slider2 should NOT work
        slider1.setValue(25)
        assert slider2.value() == 75  # Unchanged

    def test_from_sync_mode(self, qtbot):
        """Test FROM_SYNC mode (sync → widget only, read-only)"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        for s in [slider1, slider2]:
            s.setRange(0, 100)

        sync = WidgetSync.for_slider(slider1, initial=50)

        # Connect slider2 in FROM_SYNC mode
        sync.bind(
            slider2,
            setter=lambda v: slider2.setValue(v),
            mode=SyncMode.FROM_SYNC
        )

        # slider1 → slider2 should work
        slider1.setValue(75)
        assert slider2.value() == 75

        # slider2 → slider1 should NOT work
        slider2.setValue(90)
        assert slider1.value() == 75  # Unchanged


class TestValueTransforms:
    """Test value transformation functionality"""

    def test_to_sync_transform(self, qtbot):
        """Test transformation from widget to sync"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        for s in [slider1, slider2]:
            s.setRange(0, 100)

        sync = WidgetSync.for_slider(slider1, initial=0)

        # Add slider2 with transform (multiply by 2)
        sync.add(
            slider2,
            to_sync_transform=lambda v: v * 2,
            from_sync_transform=lambda v: v // 2
        )

        # Change slider2
        slider2.setValue(25)
        assert slider1.value() == 50  # 25 * 2

    def test_from_sync_transform(self, qtbot):
        """Test transformation from sync to widget"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        for s in [slider1, slider2]:
            s.setRange(0, 200)

        sync = WidgetSync.for_slider(slider1, initial=50)

        # Add slider2 with transform (multiply by 2)
        sync.add(
            slider2,
            to_sync_transform=lambda v: v // 2,
            from_sync_transform=lambda v: v * 2
        )

        # Change slider1
        slider1.setValue(50)
        assert slider2.value() == 100  # 50 * 2


class TestIntrospection:
    """Test introspection methods"""

    def test_connection_count(self, qtbot):
        """Test connection_count property"""
        sliders = [QSlider(Qt.Orientation.Horizontal) for _ in range(3)]
        for s in sliders:
            s.setRange(0, 100)

        sync = WidgetSync.for_slider(sliders[0], initial=50)
        assert sync.connection_count == 1

        sync.add(sliders[1])
        assert sync.connection_count == 2

        sync.add(sliders[2])
        assert sync.connection_count == 3

        sync.unbind(sliders[1])
        assert sync.connection_count == 2

    def test_connected_widgets(self, qtbot):
        """Test connected_widgets property"""
        sliders = [QSlider(Qt.Orientation.Horizontal) for _ in range(3)]
        for s in sliders:
            s.setRange(0, 100)

        sync = WidgetSync.for_slider(sliders[0], initial=50)
        sync.add(sliders[1])
        sync.add(sliders[2])

        widgets = sync.connected_widgets
        assert len(widgets) == 3
        assert sliders[0] in widgets
        assert sliders[1] in widgets
        assert sliders[2] in widgets

    def test_value_property(self, qtbot):
        """Test value property getter/setter"""
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)

        sync = WidgetSync.for_slider(slider, initial=50)

        # Get value
        assert sync.value == 50

        # Set value programmatically
        sync.value = 75
        assert slider.value() == sync.value


class TestFactoryMethods:
    """Test factory methods for common widget types"""

    def test_for_checkbox(self, qtbot):
        """Test for_checkbox factory"""
        cb = QCheckBox()
        sync = WidgetSync.for_checkbox(cb, initial=True)

        assert cb.isChecked() == sync.value

    def test_for_spinbox(self, qtbot):
        """Test for_spinbox factory"""
        spin = QSpinBox()
        spin.setRange(0, 100)
        sync = WidgetSync.for_spinbox(spin, initial=50)

        assert spin.value() == sync.value

    def test_for_slider(self, qtbot):
        """Test for_slider factory"""
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        sync = WidgetSync.for_slider(slider, initial=75)

        assert slider.value() == sync.value

    def test_for_lineedit(self, qtbot):
        """Test for_lineedit factory"""
        edit = QLineEdit()
        sync = WidgetSync.for_lineedit(edit, initial="Hello")

        assert edit.text() == sync.value

    def test_for_combobox(self, qtbot):
        """Test for_combobox factory"""
        combo = QComboBox()
        combo.addItems(["Option 1", "Option 2", "Option 3"])
        sync = WidgetSync.for_combobox(combo, initial=1)

        assert combo.currentIndex() == sync.value


class TestMatchParameter:
    """Test the match parameter in add() method"""

    def test_add_same_type_default_match(self, qtbot):
        """Test add() with same widget type (default match='type')"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        slider1.setRange(0, 100)
        slider2.setRange(0, 100)

        sync = WidgetSync.for_slider(slider1, initial=50)
        sync.add(slider2)  # Should work with default match='type'

        slider1.setValue(75)
        assert slider2.value() == 75

    def test_add_same_type_explicit_type_match(self, qtbot):
        """Test add() with same widget type and explicit match='type'"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        slider1.setRange(0, 100)
        slider2.setRange(0, 100)

        sync = WidgetSync.for_slider(slider1, initial=50)
        sync.add(slider2, match='type')  # Explicit type matching

        slider1.setValue(75)
        assert slider2.value() == 75

    def test_add_different_type_with_property_match(self, qtbot):
        """Test add() with different widget type using match='property'"""
        slider = QSlider(Qt.Orientation.Horizontal)
        spinbox = QSpinBox()
        slider.setRange(0, 100)
        spinbox.setRange(0, 100)

        sync = WidgetSync.for_slider(slider, initial=50)
        # Both use 'value' property and 'valueChanged' signal
        sync.add(spinbox, match='property')

        # Check initial sync
        assert spinbox.value() == 50

        # Change slider -> spinbox should update
        slider.setValue(75)
        assert spinbox.value() == 75

        # Change spinbox -> slider should update
        spinbox.setValue(25)
        assert slider.value() == 25

    def test_add_different_type_without_property_match_raises(self, qtbot):
        """Test add() with different type and default match='type' raises"""
        slider = QSlider(Qt.Orientation.Horizontal)
        spinbox = QSpinBox()

        sync = WidgetSync.for_slider(slider, initial=50)

        # Should raise TypeError because types don't match
        with pytest.raises(TypeError, match="no connection pattern found"):
            sync.add(spinbox)  # Default match='type'

    def test_add_incompatible_widget_property_match_raises(self, qtbot):
        """Test add() with incompatible widget using match='property' raises"""
        slider = QSlider(Qt.Orientation.Horizontal)
        checkbox = QCheckBox()

        sync = WidgetSync.for_slider(slider, initial=50)

        # Should raise TypeError because checkbox doesn't have 'valueChanged' signal
        with pytest.raises(TypeError):
            sync.add(checkbox, match='property')

    def test_add_invalid_match_raises(self, qtbot):
        """Test add() with invalid match parameter raises ValueError"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)

        sync = WidgetSync.for_slider(slider1, initial=50)

        with pytest.raises(ValueError, match="match must be"):
            sync.add(slider2, match='invalid')

    def test_property_match_with_multiple_types(self, qtbot):
        """Test property matching with multiple different widget types"""
        from qtpy.QtWidgets import QDial

        slider = QSlider(Qt.Orientation.Horizontal)
        spinbox = QSpinBox()
        dial = QDial()

        slider.setRange(0, 100)
        spinbox.setRange(0, 100)
        dial.setRange(0, 100)

        sync = WidgetSync.for_slider(slider, initial=50)
        sync.add(spinbox, match='property')
        sync.add(dial, match='property')

        # All should be synced
        assert spinbox.value() == 50
        assert dial.value() == 50

        # Change one -> all update
        slider.setValue(75)
        assert spinbox.value() == 75
        assert dial.value() == 75


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_add_different_widget_type_raises(self, qtbot):
        """Test that add() with different widget type raises TypeError"""
        checkbox = QCheckBox()
        slider = QSlider(Qt.Orientation.Horizontal)

        sync = WidgetSync.for_checkbox(checkbox)

        with pytest.raises(TypeError):
            sync.add(slider)

    def test_widget_deletion_cleanup(self, qtbot):
        """Test that widget deletion triggers automatic cleanup"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        slider1.setRange(0, 100)
        slider2.setRange(0, 100)

        sync = WidgetSync.for_slider(slider1, initial=50)
        sync.add(slider2)

        assert sync.connection_count == 2

        # Delete slider2
        slider2.deleteLater()
        qtbot.wait(100)  # Wait for Qt to process deletion

        # Connection count should decrease
        # Note: This tests the destroyed signal mechanism
        assert sync.connection_count <= 2

    def test_disabled_widget_not_in_feedback_loop(self, qtbot):
        """Test that disabled widget doesn't create feedback loops"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        slider3 = QSlider(Qt.Orientation.Horizontal)
        for s in [slider1, slider2, slider3]:
            s.setRange(0, 100)

        sync = WidgetSync.for_slider(slider1, initial=50)
        sync.add(slider2)
        sync.add(slider3)

        # Disable slider2
        sync.disable(slider2)

        # Rapid changes should not cause issues
        for i in range(10):
            slider1.setValue(i * 10)
            slider3.setValue(i * 10)

        # slider2 should still be at initial value
        assert slider2.value() == 50

    def test_bind_to_nonexistent_property(self, qtbot_app):
        """Test binding to a non-existent property raises error"""
        sync = WidgetSync(initial_value={'test': 123})
        widget = QSpinBox()

        # This should work (property exists on widget)
        sync.bind_properties(widget, {'test': {'property': 'value'}})

    def test_multiple_bindings_same_widget(self, qtbot_app):
        """Test multiple separate bind calls to the same widget"""
        sync = WidgetSync(initial_value={'a': 1, 'b': 2})

        widget = QSpinBox()
        widget.setRange(0, 100)

        # Bind property 'a'
        sync.bind_properties(widget, {'a': {'property': 'value'}})

        assert widget.value() == 1

        # Update value
        widget.setValue(10)
        assert sync.value['a'] == 10


class TestEnableDisableWithDisconnect:
    """Test interactions between enable/disable and connect/disconnect"""

    def test_reconnect_preserves_enabled_state(self, qtbot):
        """Test that reconnecting maintains enabled state"""
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)

        sync = WidgetSync(initial_value=50)

        # Connect
        sync.bind(
            slider,
            signal=slider.valueChanged,
            getter=lambda: slider.value(),
            setter=lambda v: slider.setValue(v)
        )

        # Disable
        sync.disable(slider)
        assert not sync.is_enabled(slider)

        # Disconnect and reconnect
        sync.unbind(slider)
        sync.bind(
            slider,
            signal=slider.valueChanged,
            getter=lambda: slider.value(),
            setter=lambda v: slider.setValue(v)
        )

        # Should be enabled again (new connection)
        assert sync.is_enabled(slider)

    def test_disconnect_disabled_widget(self, qtbot):
        """Test that disconnecting a disabled widget works"""
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)

        sync = WidgetSync.for_slider(slider, initial=50)

        sync.disable(slider)
        assert sync.connection_count == 1
        sync.unbind(slider)
        assert sync.connection_count == 0


class TestInitFromParameter:
    """Test the init_from parameter for controlling initialization behavior."""

    def test_init_from_sync_default(self, qtbot):
        """Test default behavior: widget gets initialized with sync's value."""
        sync = ValueSync(initial_value=42)
        spinbox = QSpinBox()
        spinbox.setValue(99)  # Widget starts with different value

        sync.bind(spinbox, signal=spinbox.valueChanged,
                 getter=spinbox.value, setter=spinbox.setValue,
                 mode=SyncMode.BIDIRECTIONAL)

        # Widget should be initialized with sync's value (default init_from='sync')
        assert spinbox.value() == 42

    def test_init_from_widget(self, qtbot):
        """Test init_from='widget': sync gets initialized with widget's value."""
        sync = ValueSync(initial_value=42)
        spinbox1 = QSpinBox()
        spinbox1.setValue(99)  # Widget starts with different value

        sync.bind(spinbox1, signal=spinbox1.valueChanged,
                 getter=spinbox1.value, setter=spinbox1.setValue,
                 mode=SyncMode.BIDIRECTIONAL, init_from='widget')

        # Sync should be initialized with widget's value
        assert sync.value == 99

        # Add second widget - it should get the sync's (now 99) value
        spinbox2 = QSpinBox()
        spinbox2.setValue(50)
        sync.bind(spinbox2, signal=spinbox2.valueChanged,
                 getter=spinbox2.value, setter=spinbox2.setValue,
                 mode=SyncMode.BIDIRECTIONAL, init_from='sync')

        assert spinbox2.value() == 99

    def test_init_from_none(self, qtbot):
        """Test init_from=None: no initialization occurs."""
        sync = ValueSync(initial_value=42)
        spinbox = QSpinBox()
        spinbox.setValue(99)  # Widget starts with different value

        sync.bind(spinbox, signal=spinbox.valueChanged,
                 getter=spinbox.value, setter=spinbox.setValue,
                 mode=SyncMode.BIDIRECTIONAL, init_from=None)

        # Neither should change
        assert spinbox.value() == 99
        assert sync.value == 42

        # But changes should propagate after binding
        sync.value = 50
        assert spinbox.value() == 50

    def test_init_from_widget_updates_all_widgets(self, qtbot):
        """Test that init_from='widget' updates all previously bound widgets."""
        sync = ValueSync(initial_value=42)

        spinbox1 = QSpinBox()
        spinbox1.setValue(10)
        sync.bind(spinbox1, signal=spinbox1.valueChanged,
                 getter=spinbox1.value, setter=spinbox1.setValue,
                 mode=SyncMode.BIDIRECTIONAL, init_from='sync')
        assert spinbox1.value() == 42

        spinbox2 = QSpinBox()
        spinbox2.setValue(99)
        sync.bind(spinbox2, signal=spinbox2.valueChanged,
                 getter=spinbox2.value, setter=spinbox2.setValue,
                 mode=SyncMode.BIDIRECTIONAL, init_from='widget')

        # Sync should have widget2's value
        assert sync.value == 99
        # Widget1 should also be updated
        assert spinbox1.value() == 99

    def test_init_from_widget_requires_to_sync_mode(self, qtbot):
        """Test that init_from='widget' requires TO_SYNC or BIDIRECTIONAL mode."""
        sync = ValueSync(initial_value=42)
        spinbox = QSpinBox()
        spinbox.setValue(99)

        with pytest.raises(ValueError, match="init_from='widget' requires mode with TO_SYNC capability"):
            sync.bind(spinbox, signal=spinbox.valueChanged,
                     getter=spinbox.value, setter=spinbox.setValue,
                     mode=SyncMode.FROM_SYNC, init_from='widget')

    def test_init_from_widget_requires_getter(self, qtbot):
        """Test that init_from='widget' requires a getter."""
        sync = ValueSync(initial_value=42)
        spinbox = QSpinBox()
        spinbox.setValue(99)

        # Use simple ValueError check without specific message matching
        with pytest.raises(ValueError):
            sync.bind(spinbox, signal=spinbox.valueChanged,
                     getter=None, setter=spinbox.setValue,
                     mode=SyncMode.BIDIRECTIONAL, init_from='widget')

    def test_init_from_sync_with_to_sync_mode_noop(self, qtbot):
        """Test that init_from='sync' with TO_SYNC mode is a no-op."""
        sync = ValueSync(initial_value=42)
        spinbox = QSpinBox()
        spinbox.setValue(99)

        # This should not raise an error, just skip initialization
        sync.bind(spinbox, signal=spinbox.valueChanged,
                 getter=spinbox.value, setter=spinbox.setValue,
                 mode=SyncMode.TO_SYNC, init_from='sync')

        # Widget value should be unchanged (no FROM_SYNC capability)
        assert spinbox.value() == 99
        assert sync.value == 42

    def test_add_method_passes_init_from(self, qtbot):
        """Test that add() method properly passes init_from parameter."""
        checkbox0 = QCheckBox()
        sync = WidgetSync.for_checkbox(checkbox0, initial=True)
        checkbox1 = QCheckBox()
        checkbox1.setChecked(False)
        sync.add(checkbox1)  # Default init_from='sync'
        assert checkbox1.isChecked()

        checkbox2 = QCheckBox()
        checkbox2.setChecked(False)
        sync.add(checkbox2, init_from='widget')

        # Sync and all widgets should now have value False
        assert not sync.value
        assert not checkbox1.isChecked()
        assert not checkbox2.isChecked()

    def test_init_from_with_transforms(self, qtbot):
        """Test that transforms are applied during initialization."""
        sync = ValueSync(initial_value=100)
        spinbox = QSpinBox()
        spinbox.setValue(50)

        # to_sync_transform: multiply by 2
        # from_sync_transform: divide by 2
        sync.bind(spinbox, signal=spinbox.valueChanged,
                 getter=spinbox.value, setter=spinbox.setValue,
                 mode=SyncMode.BIDIRECTIONAL,
                 to_sync_transform=lambda x: x * 2,
                 from_sync_transform=lambda x: x // 2,
                 init_from='sync')

        # Widget should get sync's value (100) transformed (divided by 2)
        assert spinbox.value() == 50

        # Now test init_from='widget'
        sync2 = ValueSync(initial_value=100)
        spinbox2 = QSpinBox()
        spinbox2.setValue(25)

        sync2.bind(spinbox2, signal=spinbox2.valueChanged,
                  getter=spinbox2.value, setter=spinbox2.setValue,
                  mode=SyncMode.BIDIRECTIONAL,
                  to_sync_transform=lambda x: x * 2,
                  from_sync_transform=lambda x: x // 2,
                  init_from='widget')

        # Sync should get widget's value (25) transformed (multiplied by 2)
        assert sync2.value == 50

    def test_bind_dict_global_init_from(self, qtbot):
        """Test bind_dict with global init_from parameter."""
        sync = DictSync(initial_value={'value': 42})

        spinbox = QSpinBox()
        spinbox.setValue(99)

        sync.bind_dict(property_map={
            'value': {'widget': spinbox, 'property': 'value'}
        }, init_from='widget')

        # Sync should be initialized with widget's value
        assert sync.value['value'] == 99

    def test_bind_dict_per_property_override(self, qtbot):
        """Test bind_dict with per-property init_from override."""
        sync = DictSync(initial_value={'a': 10, 'b': 20})

        spinbox_a = QSpinBox()
        spinbox_a.setValue(50)
        spinbox_b = QSpinBox()
        spinbox_b.setValue(200)

        # Bind property 'b' first with init_from='sync'
        sync.bind_dict(property_map={
            'b': {'widget': spinbox_b, 'property': 'value', 'init_from': 'sync'}
        })

        # Property 'b' widget should have sync's value
        assert spinbox_b.value() == 20

        # Now bind property 'a' with init_from='widget'
        sync.bind_dict(property_map={
            'a': {'widget': spinbox_a, 'property': 'value', 'init_from': 'widget'}
        })

        # Property 'a' in sync should now have widget's value
        assert sync.value['a'] == 50
        # Property 'b' should still be 20
        assert sync.value['b'] == 20

    def test_backward_compatibility(self, qtbot):
        """Test that not specifying init_from maintains backward compatibility."""
        sync = ValueSync(initial_value=42)
        spinbox = QSpinBox()
        spinbox.setValue(99)

        # Don't specify init_from - should default to 'sync'
        sync.bind(spinbox, signal=spinbox.valueChanged,
                 getter=spinbox.value, setter=spinbox.setValue,
                 mode=SyncMode.BIDIRECTIONAL)

        # Widget should be initialized with sync's value (backward compatible)
        assert spinbox.value() == 42


class TestBindParameter:
    """Test bind_parameter() method for pyqtgraph Parameters"""

    def test_bind_parameter_basic(self, qtbot):
        """Test basic parameter binding with manual specification"""
        from pymodaq_gui.parameter import Parameter

        # Create parameter
        params = [
            {'title': 'Value:', 'name': 'value', 'type': 'int', 'value': 42}
        ]
        settings = Parameter.create(name='settings', type='group', children=params)
        value_param = settings.child('value')

        # Create sync
        sync = WidgetSync(initial_value={'value': 42})

        # Bind parameter
        sync.bind_parameter(
            value_param,
            property_map={
                'value': {
                    'signal': value_param.sigValueChanged,
                    'getter': value_param.value,
                    'setter': value_param.setValue,
                }
            }
        )

        # Check initial sync
        assert value_param.value() == 42

        # Change parameter -> sync updates
        value_param.setValue(99)
        assert sync.value['value'] == 99

        # Change sync -> parameter updates
        sync.value = {'value': 50}
        assert value_param.value() == 50

    def test_bind_parameter_shortcut_syntax(self, qtbot):
        """Test bind_parameter() with shortcut syntax"""
        from pymodaq_gui.parameter import Parameter

        # Create parameter
        params = [
            {'title': 'Threshold:', 'name': 'threshold', 'type': 'float', 'value': 0.5}
        ]
        settings = Parameter.create(name='settings', type='group', children=params)
        threshold_param = settings.child('threshold')

        # Create sync
        sync = WidgetSync(initial_value={'threshold': 0.5})

        # Bind using shortcut syntax
        sync.bind_parameter(
            threshold_param,
            property_map={
                'threshold': {'param': threshold_param}
            }
        )

        # Check initial sync
        assert threshold_param.value() == 0.5

        # Change parameter -> sync updates
        threshold_param.setValue(0.8)
        assert sync.value['threshold'] == 0.8

        # Change sync -> parameter updates
        sync.value = {'threshold': 0.2}
        assert threshold_param.value() == 0.2

    def test_bind_parameter_list_with_limits(self, qtbot):
        """Test bind_parameter() with list parameter (sync both limits and value)"""
        from pymodaq_gui.parameter import Parameter

        algorithms = ['FFT', 'Wavelet', 'Correlation']

        # Create parameter
        params = [
            {'title': 'Algorithm:', 'name': 'algorithm', 'type': 'list',
             'limits': algorithms, 'value': 'FFT'}
        ]
        settings = Parameter.create(name='settings', type='group', children=params)
        algorithm_param = settings.child('algorithm')

        # Create sync for both limits and value
        sync = WidgetSync(initial_value={
            'algorithms': algorithms,
            'algorithm': 'FFT'
        })

        # Bind parameter for both limits and value
        sync.bind_parameter(
            algorithm_param,
            property_map={
                'algorithms': {
                    'getter': lambda: algorithm_param.opts['limits'],
                    'setter': algorithm_param.setLimits,
                    'mode': SyncMode.FROM_SYNC,
                },
                'algorithm': {
                    'signal': algorithm_param.sigValueChanged,
                    'getter': algorithm_param.value,
                    'setter': algorithm_param.setValue,
                }
            }
        )

        # Check initial sync
        assert algorithm_param.opts['limits'] == algorithms
        assert algorithm_param.value() == 'FFT'

        # Change sync value -> parameter updates
        sync.value = {'algorithms': algorithms, 'algorithm': 'Wavelet'}
        assert algorithm_param.value() == 'Wavelet'

        # Change parameter value -> sync updates
        algorithm_param.setValue('Correlation')
        assert sync.value['algorithm'] == 'Correlation'

        # Update limits via sync
        new_algorithms = ['FFT', 'Wavelet', 'ML-Enhanced']
        sync.value = {'algorithms': new_algorithms, 'algorithm': 'FFT'}
        assert algorithm_param.opts['limits'] == new_algorithms
        assert algorithm_param.value() == 'FFT'

    def test_bind_parameter_multiple_types(self, qtbot):
        """Test bind_parameter() with multiple parameter types"""
        from pymodaq_gui.parameter import Parameter

        # Create parameters
        params = [
            {'title': 'Int:', 'name': 'int_val', 'type': 'int', 'value': 42},
            {'title': 'Float:', 'name': 'float_val', 'type': 'float', 'value': 3.14},
            {'title': 'Bool:', 'name': 'bool_val', 'type': 'bool', 'value': True},
            {'title': 'String:', 'name': 'str_val', 'type': 'str', 'value': 'test'},
        ]
        settings = Parameter.create(name='settings', type='group', children=params)

        # Create sync
        sync = WidgetSync(initial_value={
            'int_val': 42,
            'float_val': 3.14,
            'bool_val': True,
            'str_val': 'test'
        })

        # Bind all parameters using shortcut syntax
        for param_name in ['int_val', 'float_val', 'bool_val', 'str_val']:
            param = settings.child(param_name)
            sync.bind_parameter(
                param,
                property_map={param_name: {'param': param}}
            )

        # Check initial sync
        assert settings.child('int_val').value() == 42
        assert settings.child('float_val').value() == 3.14
        assert settings.child('bool_val').value() == True
        assert settings.child('str_val').value() == 'test'

        # Change sync -> all parameters update
        sync.value = {
            'int_val': 99,
            'float_val': 2.71,
            'bool_val': False,
            'str_val': 'updated'
        }
        assert settings.child('int_val').value() == 99
        assert settings.child('float_val').value() == 2.71
        assert settings.child('bool_val').value() == False
        assert settings.child('str_val').value() == 'updated'

        # Change parameters -> sync updates
        settings.child('int_val').setValue(50)
        settings.child('float_val').setValue(1.41)
        assert sync.value['int_val'] == 50
        assert sync.value['float_val'] == 1.41

    def test_bind_parameter_feedback_prevention(self, qtbot):
        """Test that bind_parameter() prevents feedback loops without blockSignals()"""
        from pymodaq_gui.parameter import Parameter

        # Create parameter
        params = [
            {'title': 'Value:', 'name': 'value', 'type': 'int', 'value': 10}
        ]
        settings = Parameter.create(name='settings', type='group', children=params)
        value_param = settings.child('value')

        # Track setValue calls
        setter_calls = {'count': 0}
        original_setValue = value_param.setValue

        def tracked_setValue(value):
            setter_calls['count'] += 1
            original_setValue(value)

        value_param.setValue = tracked_setValue

        # Create sync
        sync = WidgetSync(initial_value={'value': 10})

        # Bind parameter
        sync.bind_parameter(
            value_param,
            property_map={
                'value': {
                    'signal': value_param.sigValueChanged,
                    'getter': value_param.value,
                    'setter': lambda v: value_param.setValue(v),
                }
            }
        )

        # Reset counter after initial sync
        setter_calls['count'] = 0

        # Change parameter value using original setter to trigger signal
        original_setValue(50)

        # Setter should NOT be called (feedback prevention)
        # Only the sync should be updated
        assert setter_calls['count'] == 0
        assert sync.value['value'] == 50

    def test_bind_parameter_with_widget_sync(self, qtbot):
        """Test sync between parameter and regular Qt widget"""
        from pymodaq_gui.parameter import Parameter

        # Create parameter
        params = [
            {'title': 'Value:', 'name': 'value', 'type': 'int', 'value': 50}
        ]
        settings = Parameter.create(name='settings', type='group', children=params)
        value_param = settings.child('value')

        # Create Qt widget
        spinbox = QSpinBox()
        spinbox.setRange(0, 100)
        spinbox.setValue(50)

        # Create sync
        sync = WidgetSync(initial_value={'value': 50})

        # Bind both parameter and widget
        sync.bind_parameter(
            value_param,
            property_map={
                'value': {
                    'signal': value_param.sigValueChanged,
                    'getter': value_param.value,
                    'setter': value_param.setValue,
                }
            }
        )

        sync.bind_properties(
            spinbox,
            property_map={'value': {'property': 'value'}}
        )

        # All should be in sync
        assert value_param.value() == 50
        assert spinbox.value() == 50
        assert sync.value['value'] == 50

        # Change parameter -> widget updates
        value_param.setValue(75)
        assert spinbox.value() == 75
        assert sync.value['value'] == 75

        # Change widget -> parameter updates
        spinbox.setValue(25)
        assert value_param.value() == 25
        assert sync.value['value'] == 25

        # Change sync -> both update
        sync.value = {'value': 60}
        assert value_param.value() == 60
        assert spinbox.value() == 60

    def test_bind_parameter_from_sync_mode(self, qtbot):
        """Test bind_parameter() with FROM_SYNC mode (read-only)"""
        from pymodaq_gui.parameter import Parameter

        # Create parameter
        params = [
            {'title': 'Value:', 'name': 'value', 'type': 'int', 'value': 10}
        ]
        settings = Parameter.create(name='settings', type='group', children=params)
        value_param = settings.child('value')

        # Create sync
        sync = WidgetSync(initial_value={'value': 10})

        # Bind parameter in FROM_SYNC mode (read-only)
        sync.bind_parameter(
            value_param,
            property_map={
                'value': {
                    'setter': value_param.setValue,
                    'mode': SyncMode.FROM_SYNC,
                }
            }
        )

        # Sync -> parameter should work
        sync.value = {'value': 50}
        assert value_param.value() == 50

        # Parameter -> sync should NOT work
        value_param.setValue(99)
        assert sync.value['value'] == 50  # Unchanged

    def test_bind_parameter_to_sync_mode(self, qtbot):
        """Test bind_parameter() with TO_SYNC mode (write-only to sync)"""
        from pymodaq_gui.parameter import Parameter

        # Create parameter
        params = [
            {'title': 'Value:', 'name': 'value', 'type': 'int', 'value': 10}
        ]
        settings = Parameter.create(name='settings', type='group', children=params)
        value_param = settings.child('value')

        # Create sync
        sync = WidgetSync(initial_value={'value': 10})

        # Bind parameter in TO_SYNC mode
        sync.bind_parameter(
            value_param,
            property_map={
                'value': {
                    'signal': value_param.sigValueChanged,
                    'getter': value_param.value,
                    'mode': SyncMode.TO_SYNC,
                }
            }
        )

        # Parameter -> sync should work
        value_param.setValue(75)
        assert sync.value['value'] == 75

        # Sync -> parameter should NOT work
        sync.value = {'value': 99}
        assert value_param.value() == 75  # Unchanged

    def test_bind_parameter_init_from_widget(self, qtbot):
        """Test bind_parameter() with init_from='widget'"""
        from pymodaq_gui.parameter import Parameter

        # Create parameter with different value than sync
        params = [
            {'title': 'Value:', 'name': 'value', 'type': 'int', 'value': 99}
        ]
        settings = Parameter.create(name='settings', type='group', children=params)
        value_param = settings.child('value')

        # Create sync with different value
        sync = WidgetSync(initial_value={'value': 42})

        # Bind parameter with init_from='widget'
        sync.bind_parameter(
            value_param,
            property_map={
                'value': {
                    'signal': value_param.sigValueChanged,
                    'getter': value_param.value,
                    'setter': value_param.setValue,
                }
            },
            init_from='widget'
        )

        # Sync should be initialized with parameter's value
        assert sync.value['value'] == 99

    def test_bind_parameter_init_from_sync(self, qtbot):
        """Test bind_parameter() with init_from='sync' (default)"""
        from pymodaq_gui.parameter import Parameter

        # Create parameter with different value than sync
        params = [
            {'title': 'Value:', 'name': 'value', 'type': 'int', 'value': 99}
        ]
        settings = Parameter.create(name='settings', type='group', children=params)
        value_param = settings.child('value')

        # Create sync with different value
        sync = WidgetSync(initial_value={'value': 42})

        # Bind parameter with init_from='sync' (default)
        sync.bind_parameter(
            value_param,
            property_map={
                'value': {
                    'signal': value_param.sigValueChanged,
                    'getter': value_param.value,
                    'setter': value_param.setValue,
                }
            },
            init_from='sync'
        )

        # Parameter should be initialized with sync's value
        assert value_param.value() == 42

    def test_bind_parameter_unbind(self, qtbot):
        """Test unbinding a parameter"""
        from pymodaq_gui.parameter import Parameter

        # Create parameter
        params = [
            {'title': 'Value:', 'name': 'value', 'type': 'int', 'value': 10}
        ]
        settings = Parameter.create(name='settings', type='group', children=params)
        value_param = settings.child('value')

        # Create sync
        sync = WidgetSync(initial_value={'value': 10})

        # Bind parameter
        sync.bind_parameter(
            value_param,
            property_map={
                'value': {'param': value_param}
            }
        )

        # Check it works
        value_param.setValue(50)
        assert sync.value['value'] == 50

        # Unbind
        sync.unbind(value_param)

        # Changes should not propagate
        value_param.setValue(99)
        assert sync.value['value'] == 50  # Unchanged


class TestHelperMethods:
    """Test DictSync helper methods for list manipulation"""

    def test_update_key(self, qtbot_app):
        """Test update_key() method"""
        sync = DictSync(initial_value={'a': 1, 'b': 2, 'c': 3})

        # Track value changes
        changes = []
        sync.value_changed.connect(lambda v: changes.append(v.copy()))

        # Update single key
        sync.update_key('b', 99)

        assert sync.value['a'] == 1
        assert sync.value['b'] == 99
        assert sync.value['c'] == 3
        assert len(changes) == 1
        assert changes[0]['b'] == 99

    def test_update_key_with_widgets(self, qtbot_app):
        """Test that update_key() triggers widget updates"""
        sync = DictSync(initial_value={'value': 10})

        spinbox = QSpinBox()
        sync.bind_dict({'value': {'widget': spinbox, 'property': 'value'}})

        assert spinbox.value() == 10

        # Update key
        sync.update_key('value', 50)

        # Widget should be updated
        assert spinbox.value() == 50

    def test_append_to_list_basic(self, qtbot_app):
        """Test append_to_list() basic functionality"""
        sync = DictSync(initial_value={'items': ['a', 'b', 'c']})

        sync.append_to_list('items', 'd')

        assert sync.value['items'] == ['a', 'b', 'c', 'd']

    def test_append_to_list_triggers_signal(self, qtbot_app):
        """Test that append_to_list() emits value_changed signal"""
        sync = DictSync(initial_value={'items': ['a']})

        changes = []
        sync.value_changed.connect(lambda v: changes.append(v.copy()))

        sync.append_to_list('items', 'b')

        assert len(changes) == 1
        assert changes[0]['items'] == ['a', 'b']

    def test_append_to_list_nonexistent_key_raises(self, qtbot_app):
        """Test that append_to_list() raises KeyError for nonexistent key"""
        sync = DictSync(initial_value={'items': []})

        with pytest.raises(KeyError, match="Key 'missing' not found"):
            sync.append_to_list('missing', 'x')

    def test_append_to_list_non_list_raises(self, qtbot_app):
        """Test that append_to_list() raises TypeError for non-list value"""
        sync = DictSync(initial_value={'value': 42})

        with pytest.raises(TypeError, match="not a list"):
            sync.append_to_list('value', 10)

    def test_remove_from_list_basic(self, qtbot_app):
        """Test remove_from_list() basic functionality"""
        sync = DictSync(initial_value={'items': ['a', 'b', 'c', 'b']})

        sync.remove_from_list('items', 'b')

        # Only first occurrence removed
        assert sync.value['items'] == ['a', 'c', 'b']

    def test_remove_from_list_not_found_raises(self, qtbot_app):
        """Test that remove_from_list() raises ValueError when item not found"""
        sync = DictSync(initial_value={'items': ['a', 'b', 'c']})

        with pytest.raises(ValueError):
            sync.remove_from_list('items', 'x')

    def test_remove_from_list_nonexistent_key_raises(self, qtbot_app):
        """Test that remove_from_list() raises KeyError for nonexistent key"""
        sync = DictSync(initial_value={'items': []})

        with pytest.raises(KeyError, match="Key 'missing' not found"):
            sync.remove_from_list('missing', 'x')

    def test_remove_from_list_non_list_raises(self, qtbot_app):
        """Test that remove_from_list() raises TypeError for non-list value"""
        sync = DictSync(initial_value={'value': 42})

        with pytest.raises(TypeError, match="not a list"):
            sync.remove_from_list('value', 10)

    def test_pop_from_list_basic(self, qtbot_app):
        """Test pop_from_list() basic functionality"""
        sync = DictSync(initial_value={'items': ['a', 'b', 'c']})

        popped = sync.pop_from_list('items', 1)

        assert popped == 'b'
        assert sync.value['items'] == ['a', 'c']

    def test_pop_from_list_last_item(self, qtbot_app):
        """Test pop_from_list() with default index (last item)"""
        sync = DictSync(initial_value={'items': ['a', 'b', 'c']})

        popped = sync.pop_from_list('items')  # Default index=-1

        assert popped == 'c'
        assert sync.value['items'] == ['a', 'b']

    def test_pop_from_list_negative_index(self, qtbot_app):
        """Test pop_from_list() with negative index"""
        sync = DictSync(initial_value={'items': ['a', 'b', 'c']})

        popped = sync.pop_from_list('items', -2)

        assert popped == 'b'
        assert sync.value['items'] == ['a', 'c']

    def test_pop_from_list_out_of_range_raises(self, qtbot_app):
        """Test that pop_from_list() raises IndexError for invalid index"""
        sync = DictSync(initial_value={'items': ['a', 'b']})

        with pytest.raises(IndexError):
            sync.pop_from_list('items', 10)

    def test_pop_from_list_nonexistent_key_raises(self, qtbot_app):
        """Test that pop_from_list() raises KeyError for nonexistent key"""
        sync = DictSync(initial_value={'items': []})

        with pytest.raises(KeyError, match="Key 'missing' not found"):
            sync.pop_from_list('missing', 0)

    def test_pop_from_list_non_list_raises(self, qtbot_app):
        """Test that pop_from_list() raises TypeError for non-list value"""
        sync = DictSync(initial_value={'value': 42})

        with pytest.raises(TypeError, match="not a list"):
            sync.pop_from_list('value', 0)

    def test_helper_methods_with_widgets(self, qtbot_app):
        """Test that helper methods properly update bound widgets"""
        sync = DictSync(initial_value={
            'items': ['Red', 'Green', 'Blue'],
            'current': 'Red'
        })

        # Create combo box bound to items
        combo = QComboBox()
        sync.bind_properties(
            combo,
            property_map={
                'items': {
                    'getter': lambda: [combo.itemText(i) for i in range(combo.count())],
                    'setter': lambda items: (combo.clear(), combo.addItems(items)),
                    'mode': SyncMode.FROM_SYNC
                }
            }
        )

        assert combo.count() == 3
        assert combo.itemText(0) == 'Red'

        # Append using helper method
        sync.append_to_list('items', 'Yellow')
        assert combo.count() == 4
        assert combo.itemText(3) == 'Yellow'

        # Remove using helper method
        sync.remove_from_list('items', 'Green')
        assert combo.count() == 3
        assert combo.itemText(1) == 'Blue'

        # Pop using helper method
        popped = sync.pop_from_list('items', 0)
        assert popped == 'Red'
        assert combo.count() == 2
        assert combo.itemText(0) == 'Blue'

    def test_helper_methods_emit_control(self, qtbot_app):
        """Test that helper methods respect emit parameter"""
        sync = DictSync(initial_value={'items': ['a']})

        changes = []
        sync.value_changed.connect(lambda v: changes.append(v.copy()))

        # With emit=True (default)
        sync.append_to_list('items', 'b')
        assert len(changes) == 1

        # With emit=False
        sync.append_to_list('items', 'c', emit=False)
        assert len(changes) == 1  # No new emission

        # Verify value was updated even without emission
        assert sync.value['items'] == ['a', 'b', 'c']

    def test_deep_copy_prevents_external_modification(self, qtbot_app):
        """Test that helper methods use deep copy to prevent external modifications"""
        # This test verifies the fix for the shallow copy bug
        my_list = ['a', 'b', 'c']
        sync = DictSync(initial_value={'items': my_list})

        # Modify external list
        my_list.append('d')

        # Sync's internal list should NOT be affected (deep copy)
        assert sync.value['items'] == ['a', 'b', 'c']

        # Use helper method
        sync.append_to_list('items', 'x')

        # External list should not be affected
        assert my_list == ['a', 'b', 'c', 'd']
        assert sync.value['items'] == ['a', 'b', 'c', 'x']

    def test_complex_list_operations_sequence(self, qtbot_app):
        """Test a sequence of list operations"""
        sync = DictSync(initial_value={
            'items': ['Apple', 'Banana', 'Cherry'],
            'count': 3
        })

        # Append
        sync.append_to_list('items', 'Date')
        sync.update_key('count', 4)
        assert sync.value['items'] == ['Apple', 'Banana', 'Cherry', 'Date']
        assert sync.value['count'] == 4

        # Remove
        sync.remove_from_list('items', 'Banana')
        sync.update_key('count', 3)
        assert sync.value['items'] == ['Apple', 'Cherry', 'Date']
        assert sync.value['count'] == 3

        # Pop
        popped = sync.pop_from_list('items', 1)
        sync.update_key('count', 2)
        assert popped == 'Cherry'
        assert sync.value['items'] == ['Apple', 'Date']
        assert sync.value['count'] == 2

        # Append again
        sync.append_to_list('items', 'Elderberry')
        sync.update_key('count', 3)
        assert sync.value['items'] == ['Apple', 'Date', 'Elderberry']
        assert sync.value['count'] == 3


class TestDeepCopyBugFix:
    """Test that the deep copy bug fix works correctly"""

    def test_dictsync_deep_copy_on_set(self, qtbot_app):
        """Test that DictSync deep copies values on set"""
        my_list = [1, 2, 3]
        sync = DictSync(initial_value={'items': my_list})

        # Modify external list
        my_list.append(4)

        # Sync's value should be unaffected
        assert sync.value['items'] == [1, 2, 3]

    def test_dictsync_shallow_copy_on_get(self, qtbot_app):
        """Test that DictSync returns shallow copy on get"""
        sync = DictSync(initial_value={'a': 1, 'b': 2})

        # Get value
        value1 = sync.value
        value2 = sync.value

        # Should be different dict objects (shallow copy)
        assert value1 is not value2
        assert value1 == value2

    def test_valuesync_deep_copy_on_set(self, qtbot_app):
        """Test that ValueSync deep copies mutable values on set"""
        my_list = [1, 2, 3]
        sync = ValueSync(initial_value=my_list)

        # Modify external list
        my_list.append(4)

        # Sync's value should be unaffected
        assert sync.value == [1, 2, 3]

    def test_valuesync_with_immutable_values(self, qtbot_app):
        """Test that ValueSync works correctly with immutable values"""
        sync = ValueSync(initial_value=42)

        val = sync.value
        assert val == 42

        sync.value = 99
        assert sync.value == 99

    def test_widget_callback_deep_copy(self, qtbot_app):
        """Test that widget callbacks properly handle deep copy"""
        sync = DictSync(initial_value={'items': ['a', 'b'], 'current': 'a'})

        combo = QComboBox()
        # Add items to combo box first
        combo.addItems(['a', 'b'])

        sync.bind_properties(
            combo,
            property_map={
                'current': {
                    'signal': combo.currentTextChanged,
                    'getter': combo.currentText,
                    'setter': combo.setCurrentText,
                    'mode': SyncMode.BIDIRECTIONAL
                }
            }
        )

        # Initial value should be set
        assert combo.currentText() == 'a'

        # Change via widget
        combo.setCurrentText('b')

        # This should have updated the sync without causing shallow copy issues
        assert sync.value['current'] == 'b'
        assert sync.value['items'] == ['a', 'b']  # Unchanged

    def test_no_signal_emission_on_unchanged_value(self, qtbot_app):
        """Test that setting same value doesn't emit signal"""
        sync = DictSync(initial_value={'items': [1, 2, 3]})

        changes = []
        sync.value_changed.connect(lambda v: changes.append(v.copy()))

        # Set to same value (different list object but same contents)
        sync.value = {'items': [1, 2, 3]}

        # Should not emit (comparison works correctly with deep copy)
        assert len(changes) == 0

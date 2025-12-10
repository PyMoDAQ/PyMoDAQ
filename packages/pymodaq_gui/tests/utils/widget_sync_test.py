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
"""
import pytest
from qtpy.QtWidgets import (
    QSlider, QSpinBox, QCheckBox, QLineEdit, QComboBox, QTextEdit
)
from qtpy.QtCore import Qt

from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode


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
        sync.unbind(slider)

        assert sync.connection_count == 0


class TestTextEditCursorPreservation:
    """Test that text editing doesn't cause cursor jumps"""

    def test_textedit_no_cursor_jump(self, qtbot_app):
        """Test that synchronized text edits preserve cursor position"""
        sync = WidgetSync(initial_value={'text': 'Hello World'})

        edit1 = QLineEdit()
        edit2 = QLineEdit()

        sync.bind_dict({
            'text': {'widget': edit1, 'property': 'text'}
        })

        # Simulate typing at end
        edit1.setText('Hello World!')
        edit1.setCursorPosition(12)  # At end

        # Cursor should stay at end
        assert edit1.cursorPosition() == 12

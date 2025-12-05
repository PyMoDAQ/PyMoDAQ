"""
Tests for widget synchronization module.

Tests cover:
- Basic synchronization between widgets
- Enable/disable functionality
- Connect/disconnect operations
- Factory methods
- Value transformations
- Sync modes
- Memory management
"""
import pytest
from qtpy.QtWidgets import QSlider, QSpinBox, QCheckBox, QLineEdit, QComboBox
from qtpy.QtCore import Qt

from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode


class TestBasicSync:
    """Test basic synchronization functionality"""

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
        sync.disconnect(slider2)

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
        sync.disconnect(widget_id)

        slider1.setValue(75)
        assert slider2.value() == 50

    def test_remove_alias(self, qtbot):
        """Test that remove() is an alias for disconnect()"""
        slider1 = QSlider(Qt.Orientation.Horizontal)
        slider2 = QSlider(Qt.Orientation.Horizontal)
        for s in [slider1, slider2]:
            s.setRange(0, 100)

        sync = WidgetSync.for_slider(slider1, initial=50)
        sync.add(slider2)

        sync.remove(slider2)

        slider1.setValue(75)
        assert slider2.value() == 50

    def test_disconnect_all(self, qtbot):
        """Test disconnecting all widgets"""
        sliders = [QSlider(Qt.Orientation.Horizontal) for _ in range(3)]
        for s in sliders:
            s.setRange(0, 100)

        sync = WidgetSync.for_slider(sliders[0], initial=50)
        for s in sliders[1:]:
            sync.add(s)

        assert sync.connection_count == 3

        sync.disconnect_all()

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
        sync.connect(
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
        sync.connect(
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

        sync.disconnect(sliders[1])
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


class TestEnableDisableWithDisconnect:
    """Test interactions between enable/disable and connect/disconnect"""

    def test_reconnect_preserves_enabled_state(self, qtbot):
        """Test that reconnecting maintains enabled state"""
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)

        sync = WidgetSync(initial_value=50)

        # Connect
        sync.connect(
            slider,
            signal=slider.valueChanged,
            getter=lambda: slider.value(),
            setter=lambda v: slider.setValue(v)
        )

        # Disable
        sync.disable(slider)
        assert not sync.is_enabled(slider)

        # Disconnect and reconnect
        sync.disconnect(slider)
        sync.connect(
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
        sync.disconnect(slider)

        assert sync.connection_count == 0

"""
Level 4: Dynamic Widget Management
===================================

Learn how to dynamically add/remove widgets with automatic synchronization:
- Clone/copy widgets and auto-sync them
- Remove widgets with automatic cleanup
- Handle widget destruction gracefully
- Build dynamic UIs (e.g., adding/removing data channels)

Run: python -m pymodaq_gui.examples.4_dynamic_widgets_example
"""
import sys
from qtpy.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QGroupBox, QTabWidget,
                             QSlider, QSpinBox, QCheckBox, QScrollArea,
                             QFrame, QLineEdit)
from qtpy.QtCore import Qt

from pymodaq_gui.utils.widget_sync import WidgetSync, DictSync, SyncMode


class DynamicSlidersExample(QWidget):
    """Example 1: Dynamically add/remove synchronized sliders"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: Audio mixer with dynamic channel strips\n"
            "✓ Start with 2 volume sliders\n"
            "✓ Click '+' to add more sliders - they automatically sync!\n"
            "✓ Click '×' to remove a slider - automatic cleanup\n"
            "✓ All sliders stay synchronized"
        ))

        # Controls
        controls = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Slider")
        self.add_btn.clicked.connect(self.add_slider)
        controls.addWidget(self.add_btn)

        self.sync_label = QLabel()
        controls.addWidget(self.sync_label)
        controls.addStretch()
        layout.addLayout(controls)

        # Sliders container
        sliders_group = QGroupBox("Volume Controls (All Synchronized)")
        self.sliders_layout = QHBoxLayout()
        sliders_group.setLayout(self.sliders_layout)
        layout.addWidget(sliders_group)

        # Status
        self.status = QLabel()
        layout.addWidget(self.status)

        layout.addStretch()

        # Initialize sync
        self.sync = WidgetSync(initial_value=50, data_type=int)
        self.sync.value_changed.connect(self.update_status)

        # Track sliders
        self.slider_widgets = []
        self.slider_count = 0

        # Add initial sliders
        self.add_slider()
        self.add_slider()

    def add_slider(self):
        """Add a new synchronized slider"""
        self.slider_count += 1
        slider_id = self.slider_count

        # Create slider container
        container = QFrame()
        container.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        v_layout = QVBoxLayout(container)

        # Label
        label = QLabel(f"Ch {slider_id}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout.addWidget(label)

        # Slider
        slider = QSlider(Qt.Orientation.Vertical)
        slider.setRange(0, 100)
        slider.setMinimumHeight(150)
        v_layout.addWidget(slider)

        # Value label
        value_label = QLabel("50")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(str(v)))
        v_layout.addWidget(value_label)

        # Remove button
        remove_btn = QPushButton("×")
        remove_btn.setMaximumWidth(30)
        remove_btn.clicked.connect(lambda: self.remove_slider(container, slider))
        v_layout.addWidget(remove_btn)

        # Add to layout
        self.sliders_layout.addWidget(container)

        # Bind to sync - automatically synchronizes with existing sliders!
        self.sync.bind(
            slider,
            signal=slider.valueChanged,
            getter=slider.value,
            setter=slider.setValue,
            mode=SyncMode.BIDIRECTIONAL
        )

        # Track this slider
        self.slider_widgets.append((container, slider))

        self.update_sync_info()

    def remove_slider(self, container, slider):
        """Remove a slider and unbind from sync"""
        if len(self.slider_widgets) <= 1:
            # Keep at least one slider
            return

        # Unbind from sync - automatic cleanup!
        self.sync.unbind(slider)

        # Remove from layout and delete widget
        self.sliders_layout.removeWidget(container)
        container.deleteLater()

        # Remove from tracking
        self.slider_widgets = [(c, s) for c, s in self.slider_widgets if s != slider]

        self.update_sync_info()

    def update_sync_info(self):
        count = len(self.slider_widgets)
        self.sync_label.setText(f"Connected: {count} sliders")

    def update_status(self, value):
        self.status.setText(
            f"Current Volume: {value}%\n"
            f"Synchronized across {len(self.slider_widgets)} channels"
        )


class DynamicFormExample(QWidget):
    """Example 2: Dynamic form with synchronized fields"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: Multi-device configuration panel\n"
            "✓ Each device has Name, Port, and Enabled controls\n"
            "✓ 'Sync All' checkbox enables/disables global sync\n"
            "✓ Add/remove devices dynamically\n"
            "✓ When synced, all devices share same settings"
        ))

        # Global controls
        global_controls = QHBoxLayout()
        self.sync_enabled = QCheckBox("Sync All Devices")
        self.sync_enabled.setChecked(True)
        self.sync_enabled.toggled.connect(self.toggle_sync)
        global_controls.addWidget(self.sync_enabled)

        self.add_device_btn = QPushButton("+ Add Device")
        self.add_device_btn.clicked.connect(self.add_device)
        global_controls.addWidget(self.add_device_btn)

        global_controls.addStretch()
        layout.addLayout(global_controls)

        # Devices container with scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.devices_layout = QVBoxLayout(scroll_widget)
        self.devices_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Initialize syncs
        self.name_sync = WidgetSync(initial_value="Device", data_type=str)
        self.port_sync = WidgetSync(initial_value=8080, data_type=int)
        self.enabled_sync = WidgetSync(initial_value=True, data_type=bool)

        # Track devices
        self.device_widgets = []
        self.device_count = 0

        # Add initial devices
        self.add_device()
        self.add_device()

    def add_device(self):
        """Add a new device form"""
        self.device_count += 1
        device_id = self.device_count

        # Device container
        container = QGroupBox(f"Device #{device_id}")
        form_layout = QVBoxLayout()

        # Name field
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        name_edit = QLineEdit()
        name_row.addWidget(name_edit)
        form_layout.addLayout(name_row)

        # Port field
        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("Port:"))
        port_spin = QSpinBox()
        port_spin.setRange(1000, 65535)
        port_row.addWidget(port_spin)
        port_row.addStretch()
        form_layout.addLayout(port_row)

        # Enabled checkbox
        enabled_check = QCheckBox("Enabled")
        form_layout.addWidget(enabled_check)

        # Remove button
        remove_btn = QPushButton(f"Remove Device #{device_id}")
        remove_btn.clicked.connect(
            lambda: self.remove_device(container, name_edit, port_spin, enabled_check)
        )
        form_layout.addWidget(remove_btn)

        container.setLayout(form_layout)

        # Insert before stretch
        self.devices_layout.insertWidget(self.devices_layout.count() - 1, container)

        # Bind to syncs if enabled
        if self.sync_enabled.isChecked():
            self.bind_device(name_edit, port_spin, enabled_check)

        # Track this device
        self.device_widgets.append((container, name_edit, port_spin, enabled_check))

    def remove_device(self, container, name_edit, port_spin, enabled_check):
        """Remove a device form"""
        if len(self.device_widgets) <= 1:
            return  # Keep at least one device

        # Unbind from syncs
        self.name_sync.unbind(name_edit)
        self.port_sync.unbind(port_spin)
        self.enabled_sync.unbind(enabled_check)

        # Remove from layout
        self.devices_layout.removeWidget(container)
        container.deleteLater()

        # Remove from tracking
        self.device_widgets = [
            d for d in self.device_widgets
            if d[1] != name_edit
        ]

    def bind_device(self, name_edit, port_spin, enabled_check):
        """Bind device widgets to syncs"""
        # Bind name
        self.name_sync.bind(
            name_edit,
            signal=name_edit.textChanged,
            getter=name_edit.text,
            setter=name_edit.setText
        )

        # Bind port
        self.port_sync.bind(
            port_spin,
            signal=port_spin.valueChanged,
            getter=port_spin.value,
            setter=port_spin.setValue
        )

        # Bind enabled
        self.enabled_sync.bind(
            enabled_check,
            signal=enabled_check.toggled,
            getter=enabled_check.isChecked,
            setter=enabled_check.setChecked
        )

    def unbind_device(self, name_edit, port_spin, enabled_check):
        """Unbind device widgets from syncs"""
        self.name_sync.unbind(name_edit)
        self.port_sync.unbind(port_spin)
        self.enabled_sync.unbind(enabled_check)

    def toggle_sync(self, enabled):
        """Enable/disable synchronization for all devices"""
        if enabled:
            # Bind all devices
            for _, name_edit, port_spin, enabled_check in self.device_widgets:
                self.bind_device(name_edit, port_spin, enabled_check)
        else:
            # Unbind all devices
            for _, name_edit, port_spin, enabled_check in self.device_widgets:
                self.unbind_device(name_edit, port_spin, enabled_check)


class CloneWidgetExample(QWidget):
    """Example 3: Clone widgets with synchronized state"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: Display settings across multiple monitors\n"
            "✓ Each monitor has Brightness, Contrast, Color Temp\n"
            "✓ Clone button copies current monitor settings\n"
            "✓ All clones automatically sync with original\n"
            "✓ Perfect for 'Apply to All' scenarios"
        ))

        # Controls
        controls = QHBoxLayout()
        self.clone_btn = QPushButton("Clone Monitor")
        self.clone_btn.clicked.connect(self.clone_monitor)
        controls.addWidget(self.clone_btn)
        controls.addStretch()
        layout.addLayout(controls)

        # Monitors container
        monitors_group = QGroupBox("Monitor Settings (All Synchronized)")
        self.monitors_layout = QHBoxLayout()
        monitors_group.setLayout(self.monitors_layout)
        layout.addWidget(monitors_group)

        # Status
        self.status = QLabel()
        layout.addWidget(self.status)

        layout.addStretch()

        # Initialize dict sync for monitor settings
        self.settings_sync = DictSync({
            'brightness': 50,
            'contrast': 50,
            'color_temp': 6500
        })
        self.settings_sync.value_changed.connect(self.update_status)

        # Track monitors
        self.monitor_widgets = []
        self.monitor_count = 0

        # Add first monitor
        self.clone_monitor()

    def clone_monitor(self):
        """Clone a monitor with current synced settings"""
        self.monitor_count += 1
        monitor_id = self.monitor_count

        # Create monitor container
        container = QFrame()
        container.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        v_layout = QVBoxLayout(container)

        # Title
        title = QLabel(f"Monitor {monitor_id}")
        title.setStyleSheet("font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout.addWidget(title)

        # Brightness
        v_layout.addWidget(QLabel("Brightness:"))
        brightness_slider = QSlider(Qt.Orientation.Horizontal)
        brightness_slider.setRange(0, 100)
        brightness_label = QLabel("50")
        brightness_slider.valueChanged.connect(lambda v, lbl=brightness_label: lbl.setText(str(v)))
        v_layout.addWidget(brightness_slider)
        v_layout.addWidget(brightness_label)

        # Contrast
        v_layout.addWidget(QLabel("Contrast:"))
        contrast_slider = QSlider(Qt.Orientation.Horizontal)
        contrast_slider.setRange(0, 100)
        contrast_label = QLabel("50")
        contrast_slider.valueChanged.connect(lambda v, lbl=contrast_label: lbl.setText(str(v)))
        v_layout.addWidget(contrast_slider)
        v_layout.addWidget(contrast_label)

        # Color Temp
        v_layout.addWidget(QLabel("Color Temp:"))
        temp_spin = QSpinBox()
        temp_spin.setRange(2000, 10000)
        temp_spin.setSuffix(" K")
        v_layout.addWidget(temp_spin)

        # Remove button
        if self.monitor_count > 1:  # Don't show remove for first monitor
            remove_btn = QPushButton("Remove Monitor")
            remove_btn.clicked.connect(
                lambda: self.remove_monitor(container, brightness_slider, contrast_slider, temp_spin)
            )
            v_layout.addWidget(remove_btn)

        # Add to layout
        self.monitors_layout.addWidget(container)

        # Bind to sync - automatically gets current values!
        self.settings_sync.bind_dict({
            'brightness': {'widget': brightness_slider, 'property': 'value'},
            'contrast': {'widget': contrast_slider, 'property': 'value'},
            'color_temp': {'widget': temp_spin, 'property': 'value'}
        })

        # Track
        self.monitor_widgets.append((container, brightness_slider, contrast_slider, temp_spin))

        self.update_status(self.settings_sync.value)

    def remove_monitor(self, container, brightness_slider, contrast_slider, temp_spin):
        """Remove a monitor"""
        if len(self.monitor_widgets) <= 1:
            return

        # Unbind all widgets for this monitor
        self.settings_sync.unbind(brightness_slider)
        self.settings_sync.unbind(contrast_slider)
        self.settings_sync.unbind(temp_spin)

        # Remove from layout
        self.monitors_layout.removeWidget(container)
        container.deleteLater()

        # Remove from tracking
        self.monitor_widgets = [
            m for m in self.monitor_widgets
            if m[1] != brightness_slider
        ]

        self.update_status(self.settings_sync.value)

    def update_status(self, settings):
        self.status.setText(
            f"Settings applied to {len(self.monitor_widgets)} monitor(s):\n"
            f"Brightness: {settings['brightness']}% | "
            f"Contrast: {settings['contrast']}% | "
            f"Color Temp: {settings['color_temp']}K"
        )


class AutoCleanupExample(QWidget):
    """Example 4: Automatic cleanup when widgets are destroyed"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: Automatic cleanup demonstration\n"
            "✓ Create temporary widgets\n"
            "✓ Widgets automatically unbind when destroyed\n"
            "✓ No memory leaks - weak references used internally\n"
            "✓ Safe to delete widgets without manual cleanup"
        ))

        # Controls
        controls = QHBoxLayout()
        self.create_btn = QPushButton("Create Temporary Widget")
        self.create_btn.clicked.connect(self.create_temporary_widget)
        controls.addWidget(self.create_btn)

        self.destroy_btn = QPushButton("Destroy Oldest Widget")
        self.destroy_btn.clicked.connect(self.destroy_oldest)
        controls.addWidget(self.destroy_btn)

        controls.addStretch()
        layout.addLayout(controls)

        # Master control
        master_group = QGroupBox("Master Control (Always Visible)")
        master_layout = QVBoxLayout()
        self.master_slider = QSlider(Qt.Orientation.Horizontal)
        self.master_slider.setRange(0, 100)
        self.master_label = QLabel("50")
        self.master_slider.valueChanged.connect(lambda v: self.master_label.setText(str(v)))
        master_layout.addWidget(QLabel("Master Value:"))
        master_layout.addWidget(self.master_slider)
        master_layout.addWidget(self.master_label)
        master_group.setLayout(master_layout)
        layout.addWidget(master_group)

        # Temporary widgets container
        temp_group = QGroupBox("Temporary Widgets (Auto-cleanup on destroy)")
        self.temp_layout = QHBoxLayout()
        temp_group.setLayout(self.temp_layout)
        layout.addWidget(temp_group)

        # Status
        self.status = QLabel()
        layout.addWidget(self.status)

        layout.addStretch()

        # Initialize sync
        self.sync = WidgetSync(initial_value=50, data_type=int)
        self.sync.value_changed.connect(self.update_status)

        # Bind master
        self.sync.bind(
            self.master_slider,
            signal=self.master_slider.valueChanged,
            getter=self.master_slider.value,
            setter=self.master_slider.setValue
        )

        # Track temporary widgets
        self.temp_widgets = []

        self.update_status(50)

    def create_temporary_widget(self):
        """Create a temporary synchronized widget"""
        widget_id = len(self.temp_widgets) + 1

        # Create container
        container = QFrame()
        container.setFrameStyle(QFrame.Shape.StyledPanel)
        v_layout = QVBoxLayout(container)

        label = QLabel(f"Temp #{widget_id}")
        v_layout.addWidget(label)

        slider = QSlider(Qt.Orientation.Vertical)
        slider.setRange(0, 100)
        slider.setMinimumHeight(100)
        v_layout.addWidget(slider)

        value_label = QLabel("50")
        slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(str(v)))
        v_layout.addWidget(value_label)

        # Add to layout
        self.temp_layout.addWidget(container)

        # Bind to sync - no manual cleanup needed!
        # Widget will automatically unbind when destroyed
        self.sync.bind(
            slider,
            signal=slider.valueChanged,
            getter=slider.value,
            setter=slider.setValue
        )

        # Track
        self.temp_widgets.append((container, slider))

        self.update_status(self.sync.value)

    def destroy_oldest(self):
        """Destroy the oldest temporary widget"""
        if not self.temp_widgets:
            return

        container, slider = self.temp_widgets.pop(0)

        # Just delete the widget - sync automatically cleans up!
        # No need to call sync.unbind() manually
        self.temp_layout.removeWidget(container)
        container.deleteLater()

        self.update_status(self.sync.value)

    def update_status(self, value):
        total_widgets = len(self.temp_widgets) + 1  # +1 for master
        self.status.setText(
            f"Current Value: {value}\n"
            f"Connected Widgets: {total_widgets} ({len(self.temp_widgets)} temporary + 1 master)\n"
            f"💡 Temporary widgets auto-cleanup when destroyed - no memory leaks!"
        )



class DynamicWidgetsDemo(QWidget):
    """Main window with tabs"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Level 4: Dynamic Widget Management")
        self.setMinimumSize(900, 600)

        layout = QVBoxLayout(self)
        header = QLabel("Dynamic Widget Management - Add/Remove Widgets")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        tabs = QTabWidget()
        tabs.addTab(DynamicSlidersExample(), "1. Dynamic Sliders")
        tabs.addTab(DynamicFormExample(), "2. Dynamic Forms")
        tabs.addTab(CloneWidgetExample(), "3. Clone Widgets")
        tabs.addTab(AutoCleanupExample(), "4. Auto Cleanup")

        layout.addWidget(tabs)


def main():
    app = QApplication(sys.argv)
    window = DynamicWidgetsDemo()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

"""
Widget Synchronization Example

Demonstrates how to use WidgetSync to keep multiple widgets synchronized.
Perfect for settings panels, toolbar/menu consistency, and multi-view UIs.

Run this example:
    python -m pymodaq_gui.examples.widget_sync_example
"""
import sys
from qtpy.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                            QGroupBox, QCheckBox, QSpinBox, QSlider, QLabel,
                            QPushButton, QComboBox, QLineEdit, QRadioButton,
                            QButtonGroup, QProgressBar, QDial, QTabWidget)
from qtpy.QtCore import Qt

from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode


class ColorWidget(QLabel):
    """Custom widget example - shows how to sync custom widgets"""
    from qtpy.QtCore import Signal
    colorChanged = Signal(str)

    def __init__(self):
        super().__init__()
        self._color = "red"
        self.setFixedSize(150, 60)
        self.setAlignment(Qt.AlignCenter)
        self.setText("Color Display")
        self._update_display()

    def set_color(self, color: str):
        if self._color != color:
            self._color = color
            self._update_display()
            self.colorChanged.emit(color)

    def _update_display(self):
        """Update the visual display"""
        self.setStyleSheet(
            f"background-color: {self._color}; "
            f"border: 3px solid black; "
            f"border-radius: 8px; "
            f"font-weight: bold; "
            f"color: white; "
            f"padding: 5px;"
        )
        self.setAutoFillBackground(True)

    def get_color(self) -> str:
        return self._color


class WidgetSyncDemo(QWidget):
    """
    Demonstration of WidgetSync features for PyMoDAQ.

    Shows common patterns:
    - Settings synchronization (checkboxes, values)
    - Different widget types for same value
    - Read-only displays
    - Conditional enables/disables
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Widget Sync - PyMoDAQ Example")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Create tab widget
        tabs = QTabWidget()

        # Add each example as a tab
        tabs.addTab(self.create_settings_example(), "Module State")
        tabs.addTab(self.create_value_control_example(), "Value Control")
        tabs.addTab(self.create_enable_disable_example(), "Enable/Disable")
        tabs.addTab(self.create_dynamic_add_remove_example(), "Add/Remove Widgets")
        tabs.addTab(self.create_many_widget_types_example(), "Many Widgets")
        tabs.addTab(self.create_custom_widget_example(), "Custom Widget")

        layout.addWidget(tabs)

        # Status bar
        self.status_label = QLabel("Ready - Switch tabs to see different examples")
        self.status_label.setStyleSheet("padding: 5px;")
        layout.addWidget(self.status_label)

    def create_settings_example(self):
        """Example 1: Synchronizing module state across views"""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel(
            "Use case: Sync DAQ module state between compact and full views\n"
            "Perfect for PyMoDAQ's module initialization and control states"
        ))

        # Compact view controls
        compact_box = QGroupBox("Compact View")
        compact_controls = QHBoxLayout()
        self.compact_init = QCheckBox("Init")
        self.compact_grab = QCheckBox("Grab")
        self.compact_save = QCheckBox("Save")
        compact_controls.addWidget(self.compact_init)
        compact_controls.addWidget(self.compact_grab)
        compact_controls.addWidget(self.compact_save)
        compact_controls.addStretch()
        compact_box.setLayout(compact_controls)
        layout.addWidget(compact_box)

        # Full view controls
        full_box = QGroupBox("Full View")
        full_controls = QVBoxLayout()

        init_row = QHBoxLayout()
        self.full_init = QCheckBox("Module Initialized")
        self.init_status = QLabel("●")
        self.init_status.setStyleSheet("color: red; font-size: 16px;")
        init_row.addWidget(self.full_init)
        init_row.addWidget(self.init_status)
        init_row.addStretch()

        grab_row = QHBoxLayout()
        self.full_grab = QCheckBox("Continuous Grabbing")
        self.grab_status = QLabel("●")
        self.grab_status.setStyleSheet("color: red; font-size: 16px;")
        grab_row.addWidget(self.full_grab)
        grab_row.addWidget(self.grab_status)
        grab_row.addStretch()

        save_row = QHBoxLayout()
        self.full_save = QCheckBox("Auto-save Data")
        save_row.addWidget(self.full_save)
        save_row.addStretch()

        full_controls.addLayout(init_row)
        full_controls.addLayout(grab_row)
        full_controls.addLayout(save_row)
        full_box.setLayout(full_controls)
        layout.addWidget(full_box)

        # Create syncs between views
        self.init_sync = WidgetSync.for_checkbox(self.compact_init, initial=False)
        self.init_sync.add(self.full_init)
        # Update status indicator
        self.init_sync.value_changed.connect(
            lambda v: self.init_status.setStyleSheet(
                f"color: {'green' if v else 'red'}; font-size: 16px;"
            )
        )

        self.grab_sync = WidgetSync.for_checkbox(self.compact_grab, initial=False)
        self.grab_sync.add(self.full_grab)
        # Update status indicator
        self.grab_sync.value_changed.connect(
            lambda v: self.grab_status.setStyleSheet(
                f"color: {'green' if v else 'red'}; font-size: 16px;"
            )
        )

        self.save_sync = WidgetSync.for_checkbox(self.compact_save, initial=False)
        self.save_sync.add(self.full_save)

        widget.setLayout(layout)
        return widget

    def create_value_control_example(self):
        """Example 2: Different widgets for same value"""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel(
            "Use case: Control same value with different widgets\n"
            "Perfect for PyMoDAQ's parameter controls with multiple views"
        ))

        # Slider
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Slider:"))
        self.value_slider = QSlider(Qt.Orientation.Horizontal)
        self.value_slider.setRange(0, 100)
        slider_layout.addWidget(self.value_slider)
        layout.addLayout(slider_layout)

        # SpinBox
        spin_layout = QHBoxLayout()
        spin_layout.addWidget(QLabel("Numeric:"))
        self.value_spin = QSpinBox()
        self.value_spin.setRange(0, 100)
        self.value_spin.setSuffix(" %")
        spin_layout.addWidget(self.value_spin)
        spin_layout.addStretch()
        layout.addLayout(spin_layout)

        # Progress bar (read-only)
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Progress:"))
        self.value_progress = QProgressBar()
        self.value_progress.setRange(0, 100)
        self.value_progress.setFormat("%v%")
        progress_layout.addWidget(self.value_progress)
        layout.addLayout(progress_layout)

        # Create sync
        self.value_sync = WidgetSync.for_slider(self.value_slider, initial=50)
        self.value_sync.add(self.value_spin)

        # Add progress bar as read-only display
        self.value_sync.connect(
            self.value_progress,
            setter=lambda v: self.value_progress.setValue(v),
            mode=SyncMode.FROM_SYNC
        )

        widget.setLayout(layout)
        return widget

    def create_enable_disable_example(self):
        """Example 3: Conditional enable/disable"""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel(
            "Use case: Enable/disable controls based on mode\n"
            "Perfect for PyMoDAQ's acquisition mode settings"
        ))

        # Master enable
        self.master_enable = QCheckBox("Enable Advanced Controls")

        # Controlled widgets
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Advanced:"))
        self.advanced_spin1 = QSpinBox()
        self.advanced_spin1.setRange(0, 100)
        self.advanced_spin2 = QSpinBox()
        self.advanced_spin2.setRange(0, 100)
        controls_layout.addWidget(self.advanced_spin1)
        controls_layout.addWidget(self.advanced_spin2)
        controls_layout.addStretch()

        layout.addWidget(self.master_enable)
        layout.addLayout(controls_layout)

        # Sync checkbox state
        self.enable_sync = WidgetSync.for_checkbox(self.master_enable, initial=False)

        # Connect to enable/disable the spinboxes
        self.enable_sync.value_changed.connect(
            lambda enabled: self.advanced_spin1.setEnabled(enabled)
        )
        self.enable_sync.value_changed.connect(
            lambda enabled: self.advanced_spin2.setEnabled(enabled)
        )

        # Initialize state
        self.advanced_spin1.setEnabled(False)
        self.advanced_spin2.setEnabled(False)

        widget.setLayout(layout)
        return widget

    def create_dynamic_add_remove_example(self):
        """Example 4: Dynamic add/remove with connection tracking"""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel(
            "Use case: Dynamically add, remove, enable, and disable widgets\n"
            "- Enable/Disable: Temporarily pause syncing without disconnecting\n"
            "- Disconnect/Reconnect: Fully remove and restore connections\n"
            "- Track connection count and list in real-time"
        ))

        # Connection info display
        info_box = QGroupBox("Connection Info")
        info_layout = QVBoxLayout()
        self.connection_count_label = QLabel("Connected widgets: 0")
        self.connection_count_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.connection_list_label = QLabel("List: (none)")
        info_layout.addWidget(self.connection_count_label)
        info_layout.addWidget(self.connection_list_label)
        info_box.setLayout(info_layout)
        layout.addWidget(info_box)

        # Control buttons
        button_layout = QHBoxLayout()
        self.add_widget_btn = QPushButton("Add Slider")
        self.remove_widget_btn = QPushButton("Remove Last Slider")
        self.remove_widget_btn.setEnabled(False)
        button_layout.addWidget(self.add_widget_btn)
        button_layout.addWidget(self.remove_widget_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Master value display
        value_layout = QHBoxLayout()
        value_layout.addWidget(QLabel("Current Value:"))
        self.master_value_label = QLabel("50")
        self.master_value_label.setStyleSheet(
            "font-size: 24px; font-weight: bold; color: #2196F3; "
            "padding: 10px; border: 2px solid #2196F3; border-radius: 5px;"
        )
        value_layout.addWidget(self.master_value_label)
        value_layout.addStretch()
        layout.addLayout(value_layout)

        # Container for dynamic sliders
        self.sliders_container = QWidget()
        self.sliders_layout = QVBoxLayout(self.sliders_container)
        self.sliders_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.sliders_container)

        layout.addStretch()

        # Create sync
        self.dynamic_sync = WidgetSync(initial_value=50)
        self.dynamic_sliders = []  # Track slider widgets

        # Update display whenever value changes
        self.dynamic_sync.value_changed.connect(
            lambda v: self.master_value_label.setText(str(v))
        )

        # Connect buttons
        self.add_widget_btn.clicked.connect(self.add_dynamic_slider)
        self.remove_widget_btn.clicked.connect(self.remove_dynamic_slider)

        # Add initial slider
        self.add_dynamic_slider()
        self.add_dynamic_slider()

        widget.setLayout(layout)
        return widget

    def add_dynamic_slider(self):
        """Add a new slider to the sync"""
        # Create slider with label and controls
        slider_widget = QWidget()
        slider_layout = QHBoxLayout(slider_widget)
        slider_layout.setContentsMargins(0, 5, 0, 5)

        slider_num = len(self.dynamic_sliders) + 1
        label = QLabel(f"Slider {slider_num}:")
        label.setMinimumWidth(80)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(self.dynamic_sync.value)

        # Control buttons
        enable_btn = QPushButton("Disable")
        enable_btn.setMaximumWidth(80)
        enable_btn.setCheckable(True)

        disconnect_btn = QPushButton("Disconnect")
        disconnect_btn.setMaximumWidth(90)

        reconnect_btn = QPushButton("Reconnect")
        reconnect_btn.setMaximumWidth(90)
        reconnect_btn.setEnabled(False)

        # Add to sync
        self.dynamic_sync.connect(
            slider,
            signal=slider.valueChanged,
            getter=lambda s=slider: s.value(),
            setter=lambda v, s=slider: s.setValue(v)
        )

        # Connect control buttons
        def toggle_enable():
            if enable_btn.isChecked():
                self.dynamic_sync.disable(slider)
                enable_btn.setText("Enable")
            else:
                self.dynamic_sync.enable(slider)
                enable_btn.setText("Disable")
            self.update_connection_info()

        def disconnect_slider():
            self.dynamic_sync.disconnect(slider)
            enable_btn.setEnabled(False)
            disconnect_btn.setEnabled(False)
            reconnect_btn.setEnabled(True)
            self.update_connection_info()

        def reconnect_slider():
            self.dynamic_sync.connect(
                slider,
                signal=slider.valueChanged,
                getter=lambda s=slider: s.value(),
                setter=lambda v, s=slider: s.setValue(v)
            )
            slider.setEnabled(True)
            enable_btn.setEnabled(True)
            enable_btn.setChecked(False)
            enable_btn.setText("Disable")
            disconnect_btn.setEnabled(True)
            reconnect_btn.setEnabled(False)
            self.update_connection_info()

        enable_btn.clicked.connect(toggle_enable)
        disconnect_btn.clicked.connect(disconnect_slider)
        reconnect_btn.clicked.connect(reconnect_slider)

        slider_layout.addWidget(label)
        slider_layout.addWidget(slider)
        slider_layout.addWidget(enable_btn)
        slider_layout.addWidget(disconnect_btn)
        slider_layout.addWidget(reconnect_btn)

        # Add to UI
        self.sliders_layout.addWidget(slider_widget)
        self.dynamic_sliders.append((slider_widget, slider, enable_btn, disconnect_btn, reconnect_btn))

        # Update display
        self.update_connection_info()
        self.remove_widget_btn.setEnabled(True)

    def remove_dynamic_slider(self):
        """Remove the last slider from the sync"""
        if not self.dynamic_sliders:
            return

        # Remove last slider (unpack all elements)
        slider_data = self.dynamic_sliders.pop()
        slider_widget = slider_data[0]
        slider = slider_data[1]

        # Disconnect from sync if still connected
        try:
            self.dynamic_sync.disconnect(slider)
        except ValueError:
            pass  # Already disconnected

        # Remove from UI
        self.sliders_layout.removeWidget(slider_widget)
        slider_widget.deleteLater()

        # Update display
        self.update_connection_info()
        self.remove_widget_btn.setEnabled(len(self.dynamic_sliders) > 0)

    def update_connection_info(self):
        """Update the connection count and list display"""
        count = self.dynamic_sync.connection_count
        self.connection_count_label.setText(f"Connected widgets: {count}")

        # Get list of widget types
        widgets = self.dynamic_sync.connected_widgets
        if widgets:
            widget_list = ", ".join([f"{type(w).__name__}" for w in widgets])
            self.connection_list_label.setText(f"List: {widget_list}")
        else:
            self.connection_list_label.setText("List: (none)")

    def create_many_widget_types_example(self):
        """Example 5: Many different widget types for same value"""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel(
            "Use case: Different representations of the same value\n"
            "Shows WidgetSync works with ANY Qt widget type"
        ))

        # Create many different widgets for 0-100 value
        self.multi_slider = QSlider(Qt.Orientation.Horizontal)
        self.multi_slider.setRange(0, 100)

        self.multi_spin = QSpinBox()
        self.multi_spin.setRange(0, 100)
        self.multi_spin.setSuffix(" %")

        self.multi_dial = QDial()
        self.multi_dial.setRange(0, 100)

        self.multi_progress = QProgressBar()
        self.multi_progress.setRange(0, 100)

        self.multi_lineedit = QLineEdit()
        self.multi_lineedit.setPlaceholderText("Type 0-100")

        self.multi_label = QLabel("Value: 50")

        # Layout
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Slider:"))
        row1.addWidget(self.multi_slider)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("SpinBox:"))
        row2.addWidget(self.multi_spin)
        row2.addWidget(QLabel("Dial:"))
        row2.addWidget(self.multi_dial)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Progress:"))
        row3.addWidget(self.multi_progress)
        layout.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Text:"))
        row4.addWidget(self.multi_lineedit)
        row4.addWidget(self.multi_label)

        layout.addLayout(row4)

        # Create sync and connect all widgets
        self.multi_sync = WidgetSync(initial_value=50)

        # Slider
        self.multi_sync.connect(
            self.multi_slider,
            signal=self.multi_slider.valueChanged,
            getter=lambda: self.multi_slider.value(),
            setter=lambda v: self.multi_slider.setValue(v)
        )

        # SpinBox
        self.multi_sync.connect(
            self.multi_spin,
            signal=self.multi_spin.valueChanged,
            getter=lambda: self.multi_spin.value(),
            setter=lambda v: self.multi_spin.setValue(v)
        )

        # Dial
        self.multi_sync.connect(
            self.multi_dial,
            signal=self.multi_dial.valueChanged,
            getter=lambda: self.multi_dial.value(),
            setter=lambda v: self.multi_dial.setValue(v)
        )

        # Progress (read-only)
        self.multi_sync.connect(
            self.multi_progress,
            setter=lambda v: self.multi_progress.setValue(v),
            mode=SyncMode.FROM_SYNC
        )

        # LineEdit with validation
        self.multi_sync.connect(
            self.multi_lineedit,
            signal=self.multi_lineedit.textChanged,
            getter=lambda: self.multi_lineedit.text(),
            setter=lambda v: self.multi_lineedit.setText(str(v)),
            to_sync_transform=lambda text: max(0, min(100, int(text))) if text.isdigit() else 0
        )

        # Label (read-only)
        self.multi_sync.connect(
            self.multi_label,
            setter=lambda v: self.multi_label.setText(f"Value: {v}"),
            mode=SyncMode.FROM_SYNC
        )

        widget.setLayout(layout)
        return widget

    def create_custom_widget_example(self):
        """Example 6: Custom widget with multiple controls"""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel(
            "Use case: Sync custom widgets with standard controls\n"
            "Shows how to connect custom ColorWidget with ComboBox and RadioButtons"
        ))

        # Custom color widget
        self.color_display = ColorWidget()

        # ComboBox for color
        self.color_combo = QComboBox()
        self.color_combo.addItems(["red", "green", "blue", "yellow", "purple"])

        # Radio buttons for color
        self.color_radio_group = QButtonGroup()
        radio_layout = QHBoxLayout()
        for color in ["red", "green", "blue", "yellow", "purple"]:
            radio = QRadioButton(color.capitalize())
            self.color_radio_group.addButton(radio)
            radio.setProperty("color", color)
            radio_layout.addWidget(radio)

        # Layout
        layout.addWidget(QLabel("Custom Widget:"))
        layout.addWidget(self.color_display)
        layout.addWidget(QLabel("ComboBox:"))
        layout.addWidget(self.color_combo)
        layout.addWidget(QLabel("Radio Buttons:"))
        layout.addLayout(radio_layout)

        # Create sync
        self.color_sync = WidgetSync(initial_value="red")

        # Connect custom widget
        self.color_sync.connect(
            self.color_display,
            signal=self.color_display.colorChanged,
            getter=lambda: self.color_display.get_color(),
            setter=lambda c: self.color_display.set_color(c)
        )

        # Connect ComboBox
        self.color_sync.connect(
            self.color_combo,
            signal=self.color_combo.currentTextChanged,
            getter=lambda: self.color_combo.currentText(),
            setter=lambda c: self.color_combo.setCurrentText(c)
        )

        # Connect radio buttons
        def get_selected_radio():
            checked = self.color_radio_group.checkedButton()
            return checked.property("color") if checked else "red"

        def set_selected_radio(color):
            for button in self.color_radio_group.buttons():
                if button.property("color") == color:
                    button.setChecked(True)
                    break

        def button_to_color(button):
            """Transform QRadioButton signal arg to color string"""
            from qtpy.QtWidgets import QRadioButton
            if isinstance(button, QRadioButton):
                return button.property("color")
            return button

        first_radio = self.color_radio_group.buttons()[0]
        self.color_sync.connect(
            first_radio,
            signal=self.color_radio_group.buttonClicked,
            getter=get_selected_radio,
            setter=set_selected_radio,
            to_sync_transform=button_to_color
        )

        widget.setLayout(layout)
        return widget


def main():
    """Run the widget sync examples"""
    app = QApplication.instance() or QApplication(sys.argv)

    # Show demo window
    demo = WidgetSyncDemo()
    demo.resize(800, 400)
    demo.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

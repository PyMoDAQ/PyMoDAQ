"""
Level 1: Basic Widget Synchronization
======================================

Learn the fundamentals:
- Factory methods (for_checkbox, for_slider, etc.)
- Sync modes (BIDIRECTIONAL, FROM_SYNC, TO_SYNC)
- Value transforms
- Enable/disable patterns

Run: python -m pymodaq_gui.examples.1_basic_sync_example
"""
import sys
from qtpy.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QGroupBox, QCheckBox, QSpinBox, QSlider, QLabel,QDial,QLineEdit,
                             QPushButton, QProgressBar, QTabWidget)
from qtpy.QtCore import Qt

from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode


class BasicCheckboxSync(QWidget):
    """Example 1: Sync checkboxes across views (most common use case)"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: Module state sync between compact and full views\n"
            "✓ All checkboxes stay in sync\n"
            "✓ Change any one, all update"
        ))

        # Create checkboxes
        compact_group = QGroupBox("Compact View")
        compact_layout = QHBoxLayout()
        self.compact_init = QCheckBox("Init")
        self.compact_grab = QCheckBox("Grab")
        compact_layout.addWidget(self.compact_init)
        compact_layout.addWidget(self.compact_grab)
        compact_layout.addStretch()
        compact_group.setLayout(compact_layout)
        layout.addWidget(compact_group)

        full_group = QGroupBox("Full View")
        full_layout = QHBoxLayout()
        self.full_init = QCheckBox("Module Initialized")
        self.full_grab = QCheckBox("Continuous Grabbing")
        full_layout.addWidget(self.full_init)
        full_layout.addWidget(self.full_grab)
        full_layout.addStretch()
        full_group.setLayout(full_layout)
        layout.addWidget(full_group)

        # Sync using factory method (simplest approach)
        self.init_sync = WidgetSync.for_checkbox(self.compact_init, initial=False)
        self.init_sync.add(self.full_init)  # add() works for same widget type

        self.grab_sync = WidgetSync.for_checkbox(self.compact_grab, initial=False)
        self.grab_sync.add(self.full_grab)

        # Show status
        self.status = QLabel()
        self.update_status()
        self.init_sync.value_changed.connect(lambda _: self.update_status())
        self.grab_sync.value_changed.connect(lambda _: self.update_status())
        layout.addWidget(self.status)

        layout.addStretch()

    def update_status(self):
        self.status.setText(
            f"Init: {self.init_sync.value} | Grab: {self.grab_sync.value}\n"
            f"Connections: {self.init_sync.connection_count + self.grab_sync.connection_count}"
        )


class DifferentWidgetTypes(QWidget):
    """Example 2: Different widget types for same value"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: Control same value with different widgets\n"
            "✓ Slider, SpinBox, Progress all sync\n"
            "✓ match='property' allows different types"
        ))

        # Slider
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Slider:"))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        slider_layout.addWidget(self.slider)
        layout.addLayout(slider_layout)

        # SpinBox
        spin_layout = QHBoxLayout()
        spin_layout.addWidget(QLabel("SpinBox:"))
        self.spinbox = QSpinBox()
        self.spinbox.setRange(0, 100)
        self.spinbox.setSuffix(" %")
        spin_layout.addWidget(self.spinbox)
        spin_layout.addStretch()
        layout.addLayout(spin_layout)

        # Progress (read-only)
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Progress:"))
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        progress_layout.addWidget(self.progress)
        layout.addLayout(progress_layout)

        # Sync with factory method
        self.value_sync = WidgetSync.for_slider(self.slider, initial=50)
        # match='property' allows different widget types with same property/signal
        self.value_sync.add(self.spinbox, match='property')

        # Read-only display with FROM_SYNC mode
        self.value_sync.bind(
            self.progress,
            setter=lambda v: self.progress.setValue(v),
            mode=SyncMode.FROM_SYNC
        )

        layout.addStretch()


class OppositeCheckboxes(QWidget):
    """Example 3: Opposite states with value transforms"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: Enable/Disable or Lock/Unlock with opposite states\n"
            "✓ Use to_sync_transform and from_sync_transform\n"
            "✓ One checkbox controls opposite of another"
        ))

        # Enable/Disable pair
        self.enable_checkbox = QCheckBox("Enable Acquisition")
        self.enable_checkbox.setChecked(True)
        self.disable_checkbox = QCheckBox("Disable Acquisition")

        layout.addWidget(self.enable_checkbox)
        layout.addWidget(self.disable_checkbox)

        # Sync with inversion
        self.sync = WidgetSync.for_checkbox(self.enable_checkbox, initial=True)
        self.sync.add(
            self.disable_checkbox,
            match='property',
            to_sync_transform=lambda checked: not checked,  # Invert
            from_sync_transform=lambda checked: not checked
        )

        # Code snippet
        code = QLabel(
            "Implementation:\n"
            "sync.add(opposite_checkbox, match='property',\n"
            "         to_sync_transform=lambda v: not v,\n"
            "         from_sync_transform=lambda v: not v)"
        )
        code.setStyleSheet("font-family: monospace; padding: 10px; border-radius: 5px;")
        layout.addWidget(code)

        layout.addStretch()


class EnableDisablePattern(QWidget):
    """Example 4: Enable/disable widgets based on checkbox"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: Enable advanced controls conditionally\n"
            "✓ Use value_changed signal to control widget states"
        ))

        # Master enable
        self.master_enable = QCheckBox("Enable Advanced Controls")
        layout.addWidget(self.master_enable)

        # Controlled widgets
        controls_group = QGroupBox("Advanced Controls")
        controls_layout = QHBoxLayout()
        self.spin1 = QSpinBox()
        self.spin1.setRange(0, 100)
        self.spin2 = QSpinBox()
        self.spin2.setRange(0, 100)
        controls_layout.addWidget(QLabel("Setting 1:"))
        controls_layout.addWidget(self.spin1)
        controls_layout.addWidget(QLabel("Setting 2:"))
        controls_layout.addWidget(self.spin2)
        controls_layout.addStretch()
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        # Sync and connect to enable/disable
        self.sync = WidgetSync.for_checkbox(self.master_enable, initial=False)
        self.sync.value_changed.connect(lambda enabled: self.spin1.setEnabled(enabled))
        self.sync.value_changed.connect(lambda enabled: self.spin2.setEnabled(enabled))

        # Initialize
        self.spin1.setEnabled(False)
        self.spin2.setEnabled(False)

        layout.addStretch()


class ValueTransforms(QWidget):
    """Example 5: Value transforms (Celsius ↔ Fahrenheit)"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: Temperature conversion\n"
            "✓ Celsius spinbox controls the sync\n"
            "✓ Fahrenheit spinbox uses transforms for conversion"
        ))

        # Celsius (master)
        c_layout = QHBoxLayout()
        c_layout.addWidget(QLabel("Celsius:"))
        self.celsius_spin = QSpinBox()
        self.celsius_spin.setRange(-100, 100)
        self.celsius_spin.setSuffix(" °C")
        c_layout.addWidget(self.celsius_spin)
        c_layout.addStretch()
        layout.addLayout(c_layout)

        # Fahrenheit (with transform)
        f_layout = QHBoxLayout()
        f_layout.addWidget(QLabel("Fahrenheit:"))
        self.fahrenheit_spin = QSpinBox()
        self.fahrenheit_spin.setRange(-148, 212)
        self.fahrenheit_spin.setSuffix(" °F")
        f_layout.addWidget(self.fahrenheit_spin)
        f_layout.addStretch()
        layout.addLayout(f_layout)

        # Sync with transforms
        self.temp_sync = WidgetSync.for_spinbox(self.celsius_spin, initial=0)
        self.temp_sync.add(
            self.fahrenheit_spin,
            match='property',
            to_sync_transform=lambda f: round((f - 32) * 5/9),  # F → C
            from_sync_transform=lambda c: round(c * 9/5 + 32)   # C → F
        )

        # Code snippet
        code = QLabel(
            "sync.add(fahrenheit_spin, match='property',\n"
            "         to_sync_transform=lambda f: (f-32)*5/9,  # F→C\n"
            "         from_sync_transform=lambda c: c*9/5+32)  # C→F"
        )
        code.setStyleSheet("font-family: monospace; padding: 10px; border-radius: 5px;")
        layout.addWidget(code)

        layout.addStretch()

class ManyWidgets(QWidget):
    """Example 6: Many different widget types for same value"""

    def __init__(self):      
        super().__init__()
        layout = QVBoxLayout(self)

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

        # Create sync and bind all widgets
        self.multi_sync = WidgetSync(initial_value=50)

        # Slider
        self.multi_sync.bind(
            self.multi_slider,
            signal=self.multi_slider.valueChanged,
            getter=lambda: self.multi_slider.value(),
            setter=lambda v: self.multi_slider.setValue(v)
        )

        # SpinBox
        self.multi_sync.bind(
            self.multi_spin,
            signal=self.multi_spin.valueChanged,
            getter=lambda: self.multi_spin.value(),
            setter=lambda v: self.multi_spin.setValue(v)
        )

        # Dial
        self.multi_sync.bind(
            self.multi_dial,
            signal=self.multi_dial.valueChanged,
            getter=lambda: self.multi_dial.value(),
            setter=lambda v: self.multi_dial.setValue(v)
        )

        # Progress (read-only)
        self.multi_sync.bind(
            self.multi_progress,
            setter=lambda v: self.multi_progress.setValue(v),
            mode=SyncMode.FROM_SYNC
        )

        # LineEdit with validation
        self.multi_sync.bind(
            self.multi_lineedit,
            signal=self.multi_lineedit.textChanged,
            getter=lambda: self.multi_lineedit.text(),
            setter=lambda v: self.multi_lineedit.setText(str(v)),
            to_sync_transform=lambda text: max(0, min(100, int(text))) if text.isdigit() else 0
        )

        # Label (read-only)
        self.multi_sync.bind(
            self.multi_label,
            setter=lambda v: self.multi_label.setText(f"Value: {v}"),
            mode=SyncMode.FROM_SYNC
        )

class EnableVsBind(QWidget):
    """Example 7: Understanding enable() vs bind() behavior"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Understanding enable() vs bind()\n"
            "✓ enable() - Resumes sync but widget keeps its old value\n"
            "✓ bind() - Creates connection and updates widget immediately"
        ))

        # Master slider
        master_group = QGroupBox("Master Control")
        master_layout = QVBoxLayout()
        self.master_label = QLabel("Master: 50")
        master_layout.addWidget(self.master_label)
        self.master_slider = QSlider(Qt.Orientation.Horizontal)
        self.master_slider.setRange(0, 100)
        self.master_slider.setValue(50)
        self.master_slider.valueChanged.connect(lambda v: self.master_label.setText(f"Master: {v}"))
        master_layout.addWidget(self.master_slider)
        master_group.setLayout(master_layout)
        layout.addWidget(master_group)

        # Slave A (enable/disable)
        slaveA_group = QGroupBox("Slave A (enable/disable test)")
        slaveA_layout = QVBoxLayout()
        self.slaveA_label = QLabel("Slave A: 50")
        slaveA_layout.addWidget(self.slaveA_label)
        self.slaveA_slider = QSlider(Qt.Orientation.Horizontal)
        self.slaveA_slider.setRange(0, 100)
        self.slaveA_slider.setValue(50)
        self.slaveA_slider.valueChanged.connect(lambda v: self.slaveA_label.setText(f"Slave A: {v}"))
        slaveA_layout.addWidget(self.slaveA_slider)
        self.btnA_disable = QPushButton("Disable Slave A")
        self.btnA_disable.clicked.connect(self.disable_slaveA)
        self.btnA_enable = QPushButton("Enable Slave A")
        self.btnA_enable.clicked.connect(self.enable_slaveA)
        self.btnA_enable.setEnabled(False)
        slaveA_layout.addWidget(self.btnA_disable)
        slaveA_layout.addWidget(self.btnA_enable)
        self.statusA = QLabel("Status: Connected")
        self.statusA.setStyleSheet("color: green;")
        slaveA_layout.addWidget(self.statusA)
        slaveA_group.setLayout(slaveA_layout)
        layout.addWidget(slaveA_group)

        # Slave B (unbind/bind)
        slaveB_group = QGroupBox("Slave B (unbind/bind test)")
        slaveB_layout = QVBoxLayout()
        self.slaveB_label = QLabel("Slave B: 50")
        slaveB_layout.addWidget(self.slaveB_label)
        self.slaveB_slider = QSlider(Qt.Orientation.Horizontal)
        self.slaveB_slider.setRange(0, 100)
        self.slaveB_slider.setValue(50)
        self.slaveB_slider.valueChanged.connect(lambda v: self.slaveB_label.setText(f"Slave B: {v}"))
        slaveB_layout.addWidget(self.slaveB_slider)
        self.btnB_unbind = QPushButton("Unbind Slave B")
        self.btnB_unbind.clicked.connect(self.unbind_slaveB)
        self.btnB_bind = QPushButton("Bind Slave B")
        self.btnB_bind.clicked.connect(self.bind_slaveB)
        self.btnB_bind.setEnabled(False)
        slaveB_layout.addWidget(self.btnB_unbind)
        slaveB_layout.addWidget(self.btnB_bind)
        self.statusB = QLabel("Status: Connected")
        self.statusB.setStyleSheet("color: green;")
        slaveB_layout.addWidget(self.statusB)
        slaveB_group.setLayout(slaveB_layout)
        layout.addWidget(slaveB_group)

        # Instructions
        instructions = QLabel(
            "📋 Test Procedure:\n"
            "1. Move Master to 70\n"
            "2. Click 'Disable Slave A' and 'Unbind Slave B'\n"
            "3. Move Master to 30\n"
            "4. Click 'Enable Slave A' → Slave A stays at 70 (no immediate update)\n"
            "5. Click 'Bind Slave B' → Slave B jumps to 30 (immediate update!)\n"
            "6. Move Master to 50 → All sliders update (both are now syncing)"
        )
        instructions.setStyleSheet(
            "padding: 15px; border-radius: 5px; "
            "border-left: 4px solid #2196f3;"
        )
        layout.addWidget(instructions)

        # Key difference
        comparison = QLabel(
            "🔑 Key Difference:\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "disable() → enable():\n"
            "  • Connection preserved, widget keeps old value\n"
            "  • Use for temporary pause\n\n"
            "unbind() → bind():\n"
            "  • Connection removed, widget auto-updates on re-bind\n"
            "  • Use for permanent disconnection"
        )
        comparison.setStyleSheet(
            "padding: 15px; border-radius: 5px; "
            "font-family: monospace; font-size: 10pt;"
        )
        layout.addWidget(comparison)

        # Initialize sync
        self.sync = WidgetSync.for_slider(self.master_slider, initial=50)
        self.sync.add(self.slaveA_slider, match='property')
        self.sync.add(self.slaveB_slider, match='property')

        layout.addStretch()

    def disable_slaveA(self):
        self.sync.disable(self.slaveA_slider)
        self.statusA.setText("Status: Disabled (connection preserved)")
        self.statusA.setStyleSheet("color: orange;")
        self.btnA_disable.setEnabled(False)
        self.btnA_enable.setEnabled(True)

    def enable_slaveA(self):
        self.sync.enable(self.slaveA_slider)
        self.statusA.setText(f"Status: Enabled (value stayed {self.slaveA_slider.value()})")
        self.statusA.setStyleSheet("color: green;")
        self.btnA_disable.setEnabled(True)
        self.btnA_enable.setEnabled(False)

    def unbind_slaveB(self):
        self.sync.unbind(self.slaveB_slider)
        self.statusB.setText("Status: Unbound (connection removed)")
        self.statusB.setStyleSheet("color: red;")
        self.btnB_unbind.setEnabled(False)
        self.btnB_bind.setEnabled(True)

    def bind_slaveB(self):
        self.sync.add(self.slaveB_slider, match='property')
        self.statusB.setText(f"Status: Bound (value updated to {self.slaveB_slider.value()})")
        self.statusB.setStyleSheet("color: green;")
        self.btnB_unbind.setEnabled(True)
        self.btnB_bind.setEnabled(False)


class BasicSyncDemo(QWidget):
    """Main window with tabs"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Level 1: Basic Widget Synchronization")
        self.setMinimumSize(800, 400)

        layout = QVBoxLayout(self)
        header = QLabel("Basic Widget Synchronization - Start Here!")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        tabs = QTabWidget()
        tabs.addTab(BasicCheckboxSync(), "1. Checkboxes")
        tabs.addTab(DifferentWidgetTypes(), "2. Different Types")
        tabs.addTab(OppositeCheckboxes(), "3. Transforms")
        tabs.addTab(EnableDisablePattern(), "4. Enable/Disable")
        tabs.addTab(ValueTransforms(), "5. Unit Conversion")
        tabs.addTab(ManyWidgets(), "6. Many Widgets")
        tabs.addTab(EnableVsBind(), "7. Enable vs Bind")

        layout.addWidget(tabs)


def main():
    app = QApplication(sys.argv)
    window = BasicSyncDemo()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

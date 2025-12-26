"""
Level 2: Dictionary Synchronization
====================================

Learn dict-based synchronization:
- bind_properties(): Multiple properties of ONE widget
- bind_dict(): Different widgets mapped to dict keys
- bind(): Custom complex widget behavior
- Validation with dicts

Run: python -m pymodaq_gui.examples.2_dict_sync_example
"""
import sys
import json
from qtpy.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QComboBox, QPushButton, QLabel, QGroupBox,QLineEdit,
                             QTabWidget, QSpinBox, QSlider, QTextEdit)
from qtpy.QtCore import Qt
from qtpy.QtGui import QPalette, QColor

from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode


class ComboBoxPropertiesExample(QWidget):
    """Example 1: bind_properties() for ONE widget with multiple properties"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: ComboBox with synchronized items AND selection\n"
            "✓ Single dict: {'items': [...], 'current': '...'}\n"
            "✓ bind_properties() for ONE widget\n"
            "✓ Each property has its own signal/getter/setter"
        ))

        # Create 3 synchronized comboboxes
        combos_group = QGroupBox("3 Synchronized ComboBoxes")
        combos_layout = QHBoxLayout()

        self.combo1 = QComboBox()
        self.combo2 = QComboBox()
        self.combo3 = QComboBox()

        combos_layout.addWidget(QLabel("View 1:"))
        combos_layout.addWidget(self.combo1)
        combos_layout.addWidget(QLabel("View 2:"))
        combos_layout.addWidget(self.combo2)
        combos_layout.addWidget(QLabel("View 3:"))
        combos_layout.addWidget(self.combo3)

        combos_group.setLayout(combos_layout)
        layout.addWidget(combos_group)

        # Create dict sync
        self.combo_sync = WidgetSync(initial_value={
            'items': ["Red", "Green", "Blue", "Yellow"],
            'current': "Red"
        })

        # Bind each combobox using bind_properties()
        for combo in [self.combo1, self.combo2, self.combo3]:
            self.combo_sync.bind_properties(
                combo,
                property_map={
                    'items': {
                        'signal': None,  # FROM_SYNC only
                        'getter': lambda c=combo: [c.itemText(i) for i in range(c.count())],
                        'setter': lambda items, c=combo: (c.clear(), c.addItems(items)),
                        'mode': SyncMode.FROM_SYNC
                    },
                    'current': {
                        'signal': combo.currentTextChanged,
                        'getter': lambda c=combo: c.currentText(),
                        'setter': lambda text, c=combo: c.setCurrentText(text),
                        'mode': SyncMode.BIDIRECTIONAL
                    }
                }
            )

        # Controls
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Change to:"))

        colors_btn = QPushButton("Colors")
        colors_btn.clicked.connect(
            lambda: setattr(self.combo_sync, 'value',
                          {'items': ["Red", "Green", "Blue"], 'current': "Red"})
        )
        controls.addWidget(colors_btn)

        fruits_btn = QPushButton("Fruits")
        fruits_btn.clicked.connect(
            lambda: setattr(self.combo_sync, 'value',
                          {'items': ["Apple", "Banana", "Orange"], 'current': "Apple"})
        )
        controls.addWidget(fruits_btn)

        layout.addLayout(controls)

        # Status
        self.status = QLabel()
        self.update_status()
        self.combo_sync.value_changed.connect(lambda _: self.update_status())
        layout.addWidget(self.status)

        layout.addStretch()

    def update_status(self):
        v = self.combo_sync.value
        self.status.setText(
            f"Items: {v['items']}\nCurrent: {v['current']}\n"
            f"Connections: {self.combo_sync.connection_count}"
        )


class RGBSlidersExample(QWidget):
    """Example 2: bind_dict() for DIFFERENT widgets to dict keys"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: RGB color controlled by 3 different sliders\n"
            "✓ Single dict: {'r': 128, 'g': 64, 'b': 192}\n"
            "✓ bind_dict() maps each slider to a dict key\n"
            "✓ Each widget controls one dict value"
        ))

        # RGB sliders
        sliders_group = QGroupBox("Color Sliders")
        sliders_layout = QVBoxLayout()

        self.r_slider = self._create_slider("Red")
        self.g_slider = self._create_slider("Green")
        self.b_slider = self._create_slider("Blue")

        sliders_layout.addLayout(self.r_slider[1])
        sliders_layout.addLayout(self.g_slider[1])
        sliders_layout.addLayout(self.b_slider[1])

        sliders_group.setLayout(sliders_layout)
        layout.addWidget(sliders_group)

        # Color preview
        self.preview = QLabel("Color Preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(80)
        self.preview.setAutoFillBackground(True)
        layout.addWidget(self.preview)

        # Create dict sync with validation
        def validate_rgb(rgb):
            return {
                'r': max(0, min(255, rgb.get('r', 0))),
                'g': max(0, min(255, rgb.get('g', 0))),
                'b': max(0, min(255, rgb.get('b', 0)))
            }

        self.color_sync = WidgetSync(
            initial_value={'r': 128, 'g': 64, 'b': 192},
            validator=validate_rgb
        )

        # bind_dict() - different widgets to different dict keys
        self.color_sync.bind_dict({
            'r': {'widget': self.r_slider[0], 'property': 'value'},
            'g': {'widget': self.g_slider[0], 'property': 'value'},
            'b': {'widget': self.b_slider[0], 'property': 'value'}
        })

        # Bind preview with bind()
        self.color_sync.bind(
            self.preview,
            setter=lambda rgb: self._update_preview(rgb),
            mode=SyncMode.FROM_SYNC
        )

        # Initial update
        self._update_preview(self.color_sync.value)

        # Presets
        presets = QHBoxLayout()
        presets.addWidget(QLabel("Presets:"))

        red_btn = QPushButton("Red")
        red_btn.clicked.connect(lambda: setattr(self.color_sync, 'value', {'r': 255, 'g': 0, 'b': 0}))
        presets.addWidget(red_btn)

        green_btn = QPushButton("Green")
        green_btn.clicked.connect(lambda: setattr(self.color_sync, 'value', {'r': 0, 'g': 255, 'b': 0}))
        presets.addWidget(green_btn)

        blue_btn = QPushButton("Blue")
        blue_btn.clicked.connect(lambda: setattr(self.color_sync, 'value', {'r': 0, 'g': 0, 'b': 255}))
        presets.addWidget(blue_btn)

        layout.addLayout(presets)
        layout.addStretch()

    def _create_slider(self, name):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 255)
        label = QLabel(f"{name}: 0")
        slider.valueChanged.connect(lambda v, l=label, n=name: l.setText(f"{n}: {v}"))

        row = QHBoxLayout()
        row.addWidget(label)
        row.addWidget(slider)

        return slider, row

    def _update_preview(self, rgb):
        palette = self.preview.palette()
        palette.setColor(QPalette.Window, QColor(rgb['r'], rgb['g'], rgb['b']))
        self.preview.setPalette(palette)


class ConfigurationFormExample(QWidget):
    """Example 3: bind_dict() for configuration with multiple widgets"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: Device configuration form\n"
            "✓ Dict: {'exposure': 100, 'gain': 10, 'fps': '60'}\n"
            "✓ bind_dict() for all controls at once\n"
            "✓ Cleaner than multiple bind_properties() calls"
        ))

        # Controls
        controls_group = QGroupBox("Camera Settings")
        controls_layout = QVBoxLayout()

        # Exposure
        exp_layout = QHBoxLayout()
        exp_layout.addWidget(QLabel("Exposure (ms):"))
        self.exposure_spin = QSpinBox()
        self.exposure_spin.setRange(1, 1000)
        exp_layout.addWidget(self.exposure_spin)
        exp_layout.addStretch()
        controls_layout.addLayout(exp_layout)

        # Gain
        gain_layout = QHBoxLayout()
        gain_layout.addWidget(QLabel("Gain (dB):"))
        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(0, 40)
        gain_layout.addWidget(self.gain_slider)
        self.gain_label = QLabel("0")
        self.gain_label.setMinimumWidth(30)
        gain_layout.addWidget(self.gain_label)
        controls_layout.addLayout(gain_layout)

        # FPS
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("Target FPS:"))
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["30", "60", "120", "240"])
        fps_layout.addWidget(self.fps_combo)
        fps_layout.addStretch()
        controls_layout.addLayout(fps_layout)

        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        # Status
        self.status_display = QLabel()
        self.status_display.setStyleSheet(
            "padding: 15px; color: #4fc3f7; "
            "font-family: monospace; border-radius: 5px;"
        )
        layout.addWidget(self.status_display)

        # Initialize sync
        self.camera_sync = WidgetSync(initial_value={
            'exposure': 100,
            'gain': 10,
            'fps': '60'
        })

        # bind_dict() - bind all controls at once!
        self.camera_sync.bind_dict({
            'exposure': {'widget': self.exposure_spin, 'property': 'value'},
            'gain': {'widget': self.gain_slider, 'property': 'value'},
            'fps': {'widget': self.fps_combo, 'property': 'currentText'}
        })

        # Bind gain label (FROM_SYNC)
        self.camera_sync.bind(
            self.gain_label,
            setter=lambda s: self.gain_label.setText(str(s['gain'])),
            mode=SyncMode.FROM_SYNC
        )

        # Bind status display (FROM_SYNC)
        self.camera_sync.bind(
            self.status_display,
            setter=self._update_status,
            mode=SyncMode.FROM_SYNC
        )
        self._update_status(self.camera_sync.value)

        # Presets
        presets = QHBoxLayout()
        presets.addWidget(QLabel("Presets:"))

        lowlight_btn = QPushButton("Low Light")
        lowlight_btn.clicked.connect(
            lambda: setattr(self.camera_sync, 'value', {'exposure': 500, 'gain': 30, 'fps': '30'})
        )
        presets.addWidget(lowlight_btn)

        highspeed_btn = QPushButton("High Speed")
        highspeed_btn.clicked.connect(
            lambda: setattr(self.camera_sync, 'value', {'exposure': 10, 'gain': 5, 'fps': '240'})
        )
        presets.addWidget(highspeed_btn)

        balanced_btn = QPushButton("Balanced")
        balanced_btn.clicked.connect(
            lambda: setattr(self.camera_sync, 'value', {'exposure': 100, 'gain': 10, 'fps': '60'})
        )
        presets.addWidget(balanced_btn)

        layout.addLayout(presets)
        layout.addStretch()

    def _update_status(self, state):
        frame_time = 1000 / int(state['fps'])
        self.status_display.setText(
            f"Camera Status\n"
            f"Exposure:  {state['exposure']:4d} ms\n"
            f"Gain:      {state['gain']:4d} dB\n"
            f"FPS:       {state['fps']:>4s} ({frame_time:.2f}ms/frame)"
        )


class HelperMethodsExample(QWidget):
    """Example 4: Using DictSync helper methods for list manipulation"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: Dynamic list management with helper methods\n"
            "✓ append_to_list() - Add items safely\n"
            "✓ remove_from_list() - Remove items safely\n"
            "✓ pop_from_list() - Remove by index\n"
            "✓ update_key() - Update individual keys\n"
            "✓ All methods handle deep copying internally!"
        ))

        # Display area
        display_group = QGroupBox("Current State")
        display_layout = QVBoxLayout()

        self.items_display = QLabel()
        self.items_display.setStyleSheet(
            "padding: 10px; "
            "font-family: monospace; border-radius: 5px;"
        )
        display_layout.addWidget(self.items_display)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # Initialize sync with a list of items
        self.list_sync = WidgetSync(initial_value={
            'items': ['Apple', 'Banana', 'Cherry'],
            'current': 'Apple',
            'count': 3
        })

        # Update display when value changes
        self.list_sync.value_changed.connect(lambda _: self.update_display())
        self.update_display()

        # Controls
        controls_group = QGroupBox("List Operations")
        controls_layout = QVBoxLayout()

        # Add item controls
        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("Add item:"))
        self.add_input = QLineEdit()
        self.add_input.setPlaceholderText("Enter item name...")
        add_layout.addWidget(self.add_input)

        add_btn = QPushButton("Append")
        add_btn.clicked.connect(self.append_item)
        add_layout.addWidget(add_btn)
        controls_layout.addLayout(add_layout)

        # Remove item controls
        remove_layout = QHBoxLayout()
        remove_layout.addWidget(QLabel("Remove item:"))
        self.remove_input = QLineEdit()
        self.remove_input.setPlaceholderText("Enter item name...")
        remove_layout.addWidget(self.remove_input)

        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self.remove_item)
        remove_layout.addWidget(remove_btn)
        controls_layout.addLayout(remove_layout)

        # Pop item controls
        pop_layout = QHBoxLayout()
        pop_layout.addWidget(QLabel("Pop by index:"))
        self.pop_spin = QSpinBox()
        self.pop_spin.setRange(-10, 10)
        self.pop_spin.setValue(0)
        pop_layout.addWidget(self.pop_spin)

        pop_btn = QPushButton("Pop")
        pop_btn.clicked.connect(self.pop_item)
        pop_layout.addWidget(pop_btn)

        pop_last_btn = QPushButton("Pop Last")
        pop_last_btn.clicked.connect(lambda: self.pop_item(-1))
        pop_layout.addWidget(pop_last_btn)
        controls_layout.addLayout(pop_layout)

        # Update current
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("Set current:"))
        self.current_combo = QComboBox()
        current_layout.addWidget(self.current_combo)

        set_current_btn = QPushButton("Update")
        set_current_btn.clicked.connect(self.update_current)
        current_layout.addWidget(set_current_btn)
        controls_layout.addLayout(current_layout)

        # Bind combo to items list (display only)
        self.list_sync.bind_properties(
            self.current_combo,
            property_map={
                'items': {
                    'getter': lambda: [self.current_combo.itemText(i)
                                     for i in range(self.current_combo.count())],
                    'setter': lambda items: (self.current_combo.clear(),
                                           self.current_combo.addItems(items)),
                    'mode': SyncMode.FROM_SYNC
                }
            }
        )

        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        # Info box
        info = QLabel(
            "💡 All operations use helper methods that handle deep copying internally.\n"
            "This prevents the shallow copy bug and ensures proper change detection!"
        )
        info.setStyleSheet("color: #0288d1; padding: 10px; font-style: italic;")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()

    def append_item(self):
        item = self.add_input.text().strip()
        if item:
            try:
                # Use helper method - handles copying internally
                self.list_sync.append_to_list('items', item)
                self.list_sync.update_key('count', len(self.list_sync.value['items']))
                self.add_input.clear()
            except (KeyError, TypeError) as e:
                print(f"Error: {e}")

    def remove_item(self):
        item = self.remove_input.text().strip()
        if item:
            try:
                # Use helper method - handles copying internally
                self.list_sync.remove_from_list('items', item)
                self.list_sync.update_key('count', len(self.list_sync.value['items']))
                self.remove_input.clear()
            except (KeyError, TypeError, ValueError) as e:
                print(f"Error: {e}")

    def pop_item(self, index=None):
        if index is None:
            index = self.pop_spin.value()
        try:
            # Use helper method - handles copying internally
            popped = self.list_sync.pop_from_list('items', index)
            self.list_sync.update_key('count', len(self.list_sync.value['items']))
            print(f"Popped: {popped}")
        except (KeyError, TypeError, IndexError) as e:
            print(f"Error: {e}")

    def update_current(self):
        current = self.current_combo.currentText()
        if current:
            # Use helper method - handles copying internally
            self.list_sync.update_key('current', current)

    def update_display(self):
        v = self.list_sync.value
        items_str = ', '.join(f"'{item}'" for item in v.get('items', []))
        self.items_display.setText(
            f"Items: [{items_str}]\n"
            f"Current: '{v.get('current', 'N/A')}'\n"
            f"Count: {v.get('count', 0)}\n\n"
            f"Internal dict:\n{v}"
        )


class MixedBindingExample(QWidget):
    """Example 5: Mix bind(), bind_dict(), and custom logic"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: Settings with JSON editor\n"
            "✓ bind_dict() for individual controls\n"
            "✓ bind() for JSON editor (custom getter/setter)\n"
            "✓ bind() for display-only status\n"
            "✓ All approaches work together!"
        ))

        # Individual controls
        controls_group = QGroupBox("Individual Controls")
        controls_layout = QVBoxLayout()

        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperature:"))
        self.temp_spin = QSpinBox()
        self.temp_spin.setRange(0, 100)
        self.temp_spin.setSuffix(" °C")
        temp_layout.addWidget(self.temp_spin)
        temp_layout.addStretch()
        controls_layout.addLayout(temp_layout)

        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(0, 100)
        speed_layout.addWidget(self.speed_slider)
        self.speed_label = QLabel("0")
        speed_layout.addWidget(self.speed_label)
        controls_layout.addLayout(speed_layout)

        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        # JSON editor
        json_group = QGroupBox("JSON Editor (Full State)")
        json_layout = QVBoxLayout()

        json_info = QLabel("Edit JSON directly - all controls update!")
        json_info.setStyleSheet("color: #666; font-style: italic;")
        json_layout.addWidget(json_info)

        self.json_editor = QTextEdit()
        self.json_editor.setMaximumHeight(100)
        self.json_editor.setStyleSheet("font-family: monospace;")
        json_layout.addWidget(self.json_editor)

        json_group.setLayout(json_layout)
        layout.addWidget(json_group)

        # Initialize sync
        self.settings_sync = WidgetSync(initial_value={
            'temperature': 25,
            'speed': 50
        })

        # 1. bind_dict() for controls
        self.settings_sync.bind_dict({
            'temperature': {'widget': self.temp_spin, 'property': 'value'},
            'speed': {'widget': self.speed_slider, 'property': 'value'}
        })

        # 2. bind() for speed label (FROM_SYNC)
        self.settings_sync.bind(
            self.speed_label,
            setter=lambda s: self.speed_label.setText(str(s['speed'])),
            mode=SyncMode.FROM_SYNC
        )

        # 3. bind() for JSON editor (BIDIRECTIONAL with custom getter/setter)
        def json_getter():
            try:
                text = self.json_editor.toPlainText().strip()
                return json.loads(text) if text else {}
            except json.JSONDecodeError:
                return self.settings_sync.value

        self.settings_sync.bind(
            self.json_editor,
            signal=self.json_editor.textChanged,
            getter=json_getter,
            setter=lambda d: self.json_editor.setPlainText(json.dumps(d, indent=2))
        )

        # Code snippet
        code = QLabel(
            "Implementation:\n"
            "settings_sync.bind_dict({'temperature': {...}, 'speed': {...}})\n"
            "settings_sync.bind(json_editor, getter=parse_json, setter=format_json)"
        )
        code.setStyleSheet("font-family: monospace; padding: 10px;")
        layout.addWidget(code)

        layout.addStretch()


class DictSyncDemo(QWidget):
    """Main window with tabs"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Level 2: Dictionary Synchronization")
        self.setMinimumSize(750, 450)

        layout = QVBoxLayout(self)
        header = QLabel("Dictionary Synchronization - Intermediate Patterns")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        tabs = QTabWidget()
        tabs.addTab(ComboBoxPropertiesExample(), "1. bind_properties()")
        tabs.addTab(RGBSlidersExample(), "2. bind_dict()")
        tabs.addTab(ConfigurationFormExample(), "3. Config Forms")
        tabs.addTab(HelperMethodsExample(), "4. Helper Methods")
        tabs.addTab(MixedBindingExample(), "5. Mixed Binding")

        layout.addWidget(tabs)


def main():
    app = QApplication(sys.argv)
    window = DictSyncDemo()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

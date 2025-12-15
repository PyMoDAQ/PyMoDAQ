"""
Level 3: Advanced Synchronization Patterns
==========================================

Learn advanced techniques:
- Multiple syncs on same widget
- Dynamic properties (add/remove at runtime)
- Complex real-world scenarios
- Extending WidgetSync with custom sync classes

Run: python -m pymodaq_gui.examples.3_advanced_sync_example
"""
import sys
import json
from qtpy.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QPushButton, QLabel, QGroupBox,
                             QTabWidget, QSpinBox, QSlider, QLineEdit,
                             QCheckBox, QTextEdit)
from qtpy.QtCore import Qt
from qtpy.QtGui import QPalette, QColor

from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode, BaseWidgetSync


class MultipleSyncsExample(QWidget):
    """Example 1: Same widget in multiple syncs"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: ListWidget with separate item and selection syncs\n"
            "✓ items_sync: Controls what items are available (FROM_SYNC)\n"
            "✓ index_sync: Controls which item is selected (BIDIRECTIONAL)\n"
            "✓ Same widget participates in TWO different syncs!"
        ))

        # List widgets
        lists_group = QGroupBox("2 Synchronized ListWidgets")
        lists_layout = QHBoxLayout()

        self.list1 = QListWidget()
        self.list2 = QListWidget()

        lists_layout.addWidget(QLabel("List 1:"))
        lists_layout.addWidget(self.list1)
        lists_layout.addWidget(QLabel("List 2:"))
        lists_layout.addWidget(self.list2)

        lists_group.setLayout(lists_layout)
        layout.addWidget(lists_group)

        # SpinBox for index
        index_layout = QHBoxLayout()
        index_layout.addWidget(QLabel("Selected Index:"))
        self.index_spinbox = QSpinBox()
        self.index_spinbox.setRange(0, 10)
        index_layout.addWidget(self.index_spinbox)
        index_layout.addStretch()
        layout.addLayout(index_layout)

        # Sync 1: Items (FROM_SYNC only)
        self.items_sync = WidgetSync(initial_value=["Red", "Green", "Blue", "Yellow"])

        for list_widget in [self.list1, self.list2]:
            self.items_sync.bind(
                list_widget,
                setter=lambda items, lw=list_widget: (lw.clear(), lw.addItems(items)),
                mode=SyncMode.FROM_SYNC
            )

        # Sync 2: Index (BIDIRECTIONAL)
        self.index_sync = WidgetSync.for_spinbox(self.index_spinbox, initial=0)

        for list_widget in [self.list1, self.list2]:
            self.index_sync.bind(
                list_widget,
                signal=list_widget.currentRowChanged,
                getter=lambda lw=list_widget: lw.currentRow(),
                setter=lambda idx, lw=list_widget: lw.setCurrentRow(idx),
            )

        # Controls
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Change items:"))

        colors_btn = QPushButton("Colors")
        colors_btn.clicked.connect(
            lambda: setattr(self.items_sync, 'value', ["Red", "Green", "Blue", "Yellow"])
        )
        controls.addWidget(colors_btn)

        fruits_btn = QPushButton("Fruits")
        fruits_btn.clicked.connect(
            lambda: setattr(self.items_sync, 'value', ["Apple", "Banana", "Orange", "Grape"])
        )
        controls.addWidget(fruits_btn)

        layout.addLayout(controls)

        # Status
        self.status = QLabel()
        self.update_status()
        self.items_sync.value_changed.connect(lambda _: self.update_status())
        self.index_sync.value_changed.connect(lambda _: self.update_status())
        layout.addWidget(self.status)

        layout.addStretch()

    def update_status(self):
        items = self.items_sync.value
        idx = self.index_sync.value
        selected = items[idx] if 0 <= idx < len(items) else "None"
        self.status.setText(
            f"Items: {items}\n"
            f"Selected: {selected} (index {idx})\n"
            f"List1 participates in: items_sync + index_sync"
        )


class DynamicPropertiesExample(QWidget):
    """Example 2: Add/remove properties and widgets dynamically"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: Configuration that grows over time\n"
            "✓ Start with basic properties (name, version)\n"
            "✓ Add optional properties dynamically (author, license, description)\n"
            "✓ Remove properties when no longer needed"
        ))

        # Current state display
        display_group = QGroupBox("Current Configuration (Live)")
        display_layout = QVBoxLayout()

        self.display = QTextEdit()
        self.display.setReadOnly(True)
        self.display.setMaximumHeight(80)
        self.display.setStyleSheet("font-family: monospace;")
        display_layout.addWidget(self.display)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # Fixed properties
        fixed_group = QGroupBox("Fixed Properties")
        fixed_layout = QVBoxLayout()

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        fixed_layout.addLayout(name_layout)

        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("Version:"))
        self.version_spin = QSpinBox()
        self.version_spin.setRange(1, 100)
        version_layout.addWidget(self.version_spin)
        version_layout.addStretch()
        fixed_layout.addLayout(version_layout)

        fixed_group.setLayout(fixed_layout)
        layout.addWidget(fixed_group)

        # Dynamic properties container
        self.dynamic_group = QGroupBox("Optional Properties (Add Below)")
        self.dynamic_layout = QVBoxLayout()
        self.dynamic_group.setLayout(self.dynamic_layout)
        layout.addWidget(self.dynamic_group)

        # Controls
        controls_group = QGroupBox("Add/Remove Properties")
        controls_layout = QHBoxLayout()

        self.add_author_btn = QPushButton("+ Author")
        self.add_author_btn.clicked.connect(self.add_author)
        controls_layout.addWidget(self.add_author_btn)

        self.add_license_btn = QPushButton("+ License")
        self.add_license_btn.clicked.connect(self.add_license)
        controls_layout.addWidget(self.add_license_btn)

        self.remove_author_btn = QPushButton("− Author")
        self.remove_author_btn.clicked.connect(lambda: self.remove_property('author'))
        self.remove_author_btn.setEnabled(False)
        controls_layout.addWidget(self.remove_author_btn)

        self.remove_license_btn = QPushButton("− License")
        self.remove_license_btn.clicked.connect(lambda: self.remove_property('license'))
        self.remove_license_btn.setEnabled(False)
        controls_layout.addWidget(self.remove_license_btn)

        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        layout.addStretch()

        # Initialize sync with fixed properties
        self.config_sync = WidgetSync(initial_value={
            'name': 'MyProject',
            'version': 1
        })

        # Bind fixed properties
        self.config_sync.bind_properties(
            self.name_edit,
            property_map={'name': {'property': 'text'}}
        )
        self.config_sync.bind_properties(
            self.version_spin,
            property_map={'version': {'property': 'value'}}
        )

        # Bind display
        self.config_sync.value_changed.connect(self.update_display)
        self.update_display(self.config_sync.value)

        # Track dynamic widgets
        self.author_edit = None
        self.license_edit = None

    def update_display(self, value):
        self.display.setPlainText(json.dumps(value, indent=2))

    def add_author(self):
        if self.author_edit is not None:
            return

        # Add property to sync state
        self.config_sync.value = {**self.config_sync.value, 'author': 'Unknown'}

        # Create widget
        author_layout = QHBoxLayout()
        author_layout.addWidget(QLabel("Author:"))
        self.author_edit = QLineEdit()
        author_layout.addWidget(self.author_edit)
        self.dynamic_layout.addLayout(author_layout)

        # Bind widget to new property
        self.config_sync.bind_properties(
            self.author_edit,
            property_map={'author': {'property': 'text'}}
        )

        # Update buttons
        self.add_author_btn.setEnabled(False)
        self.remove_author_btn.setEnabled(True)

    def add_license(self):
        if self.license_edit is not None:
            return

        # Add property
        self.config_sync.value = {**self.config_sync.value, 'license': 'MIT'}

        # Create widget
        license_layout = QHBoxLayout()
        license_layout.addWidget(QLabel("License:"))
        self.license_edit = QLineEdit()
        license_layout.addWidget(self.license_edit)
        self.dynamic_layout.addLayout(license_layout)

        # Bind widget
        self.config_sync.bind_properties(
            self.license_edit,
            property_map={'license': {'property': 'text'}}
        )

        # Update buttons
        self.add_license_btn.setEnabled(False)
        self.remove_license_btn.setEnabled(True)

    def remove_property(self, prop_name):
        # Remove from sync state
        new_value = self.config_sync.value.copy()
        if prop_name in new_value:
            del new_value[prop_name]
            self.config_sync.value = new_value

        # Remove and unbind widget
        if prop_name == 'author' and self.author_edit:
            self.config_sync.unbind(self.author_edit)
            self.author_edit.deleteLater()
            self.author_edit = None
            self.add_author_btn.setEnabled(True)
            self.remove_author_btn.setEnabled(False)

        elif prop_name == 'license' and self.license_edit:
            self.config_sync.unbind(self.license_edit)
            self.license_edit.deleteLater()
            self.license_edit = None
            self.add_license_btn.setEnabled(False)
            self.remove_license_btn.setEnabled(False)


class ComplexScenarioExample(QWidget):
    """Example 3: Real-world complex scenario with multiple syncs"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: Data visualization settings\n"
            "✓ Channel selection (items + index) - dict sync\n"
            "✓ Color (RGB) - dict sync with bind_dict()\n"
            "✓ Display options (3 checkboxes) - dict sync\n"
            "✓ Preset buttons load complete configurations"
        ))

        # Channels
        channels_group = QGroupBox("Channels")
        channels_layout = QHBoxLayout()

        self.channel_list = QListWidget()
        channels_layout.addWidget(self.channel_list)

        channels_group.setLayout(channels_layout)
        layout.addWidget(channels_group)

        # Color
        color_group = QGroupBox("Line Color")
        color_layout = QVBoxLayout()

        self.r_slider = self._create_slider("R")
        self.g_slider = self._create_slider("G")
        self.b_slider = self._create_slider("B")

        color_layout.addLayout(self.r_slider[1])
        color_layout.addLayout(self.g_slider[1])
        color_layout.addLayout(self.b_slider[1])

        self.color_preview = QLabel("Color")
        self.color_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.color_preview.setMinimumHeight(40)
        self.color_preview.setAutoFillBackground(True)
        color_layout.addWidget(self.color_preview)

        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        # Display options
        display_group = QGroupBox("Display Options")
        display_layout = QHBoxLayout()

        self.grid_check = QCheckBox("Grid")
        self.legend_check = QCheckBox("Legend")
        self.autoscale_check = QCheckBox("Autoscale")

        display_layout.addWidget(self.grid_check)
        display_layout.addWidget(self.legend_check)
        display_layout.addWidget(self.autoscale_check)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # Initialize syncs
        # 1. Channel sync
        self.channel_sync = WidgetSync(initial_value={
            'channels': ["Ch0", "Ch1", "Ch2", "Ch3"],
            'index': 0
        })

        self.channel_sync.bind_properties(
            self.channel_list,
            property_map={
                'channels': {
                    'signal': None,
                    'getter': lambda: [self.channel_list.item(i).text()
                                     for i in range(self.channel_list.count())],
                    'setter': lambda items: (self.channel_list.clear(),
                                            self.channel_list.addItems(items)),
                    'mode': SyncMode.FROM_SYNC
                },
                'index': {
                    'signal': self.channel_list.currentRowChanged,
                    'getter': lambda: self.channel_list.currentRow(),
                    'setter': lambda idx: self.channel_list.setCurrentRow(idx),
                    'mode': SyncMode.BIDIRECTIONAL
                }
            }
        )

        # 2. Color sync
        self.color_sync = WidgetSync(initial_value={'r': 255, 'g': 100, 'b': 0})

        self.color_sync.bind_dict({
            'r': {'widget': self.r_slider[0], 'property': 'value'},
            'g': {'widget': self.g_slider[0], 'property': 'value'},
            'b': {'widget': self.b_slider[0], 'property': 'value'}
        })

        self.color_sync.value_changed.connect(self.update_color_preview)
        self.update_color_preview(self.color_sync.value)

        # 3. Display options sync
        self.display_sync = WidgetSync(initial_value={
            'grid': True,
            'legend': True,
            'autoscale': False
        })

        self.display_sync.bind_dict({
            'grid': {'widget': self.grid_check, 'property': 'checked'},
            'legend': {'widget': self.legend_check, 'property': 'checked'},
            'autoscale': {'widget': self.autoscale_check, 'property': 'checked'}
        })

        # Presets
        presets = QHBoxLayout()
        presets.addWidget(QLabel("Presets:"))

        default_btn = QPushButton("Default")
        default_btn.clicked.connect(lambda: self.load_preset(
            ['Ch0', 'Ch1', 'Ch2', 'Ch3'], 0,
            {'r': 255, 'g': 100, 'b': 0},
            {'grid': True, 'legend': True, 'autoscale': False}
        ))
        presets.addWidget(default_btn)

        thermal_btn = QPushButton("Thermal")
        thermal_btn.clicked.connect(lambda: self.load_preset(
            ['Temperature', 'Pressure', 'Humidity'], 0,
            {'r': 255, 'g': 0, 'b': 0},
            {'grid': True, 'legend': False, 'autoscale': True}
        ))
        presets.addWidget(thermal_btn)

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

    def load_preset(self, channels, index, color, display):
        self.channel_sync.value = {'channels': channels, 'index': index}
        self.color_sync.value = color
        self.display_sync.value = display

    def update_color_preview(self, rgb):
        self.color_preview.setStyleSheet(
            f"background-color: rgb({rgb['r']}, {rgb['g']}, {rgb['b']}); "
            f"border: 1px solid black;"
        )


class InitFromExample(QWidget):
    """Example 4: Controlling initialization with init_from parameter"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Use Case: Control who initializes whom when binding\n"
            "✓ init_from='sync' (default) - Widget gets sync's value\n"
            "✓ init_from='widget' - Sync gets widget's value\n"
            "✓ init_from=None - No initialization, preserve both values\n"
            "✓ Works with bind(), bind_dict(), and bind_properties()"
        ))

        # Example 1: Basic init_from modes
        basic_group = QGroupBox("1. Basic init_from Modes (using bind())")
        basic_layout = QVBoxLayout()

        basic_layout.addWidget(QLabel(
            "WATCH: When you click Bind, observe what value each widget shows!\n"
            "The widget starts at 100, sync starts at 50 - who wins?"
        ))

        # Sync value display
        sync_layout = QHBoxLayout()
        sync_layout.addWidget(QLabel("Sync Value:"))
        self.sync_value_spin = QSpinBox()
        self.sync_value_spin.setRange(0, 200)
        self.sync_value_spin.setValue(50)
        sync_layout.addWidget(self.sync_value_spin)
        sync_layout.addStretch()
        basic_layout.addLayout(sync_layout)

        # Three demo spinboxes
        self.demo_sync = WidgetSync(initial_value=50)
        self.demo_sync.bind(
            self.sync_value_spin,
            signal=self.sync_value_spin.valueChanged,
            getter=self.sync_value_spin.value,
            setter=self.sync_value_spin.setValue
        )

        # init_from='sync' (default)
        sync_row = QHBoxLayout()
        sync_row.addWidget(QLabel("init_from='sync':"))
        self.sync_mode_spin = QSpinBox()
        self.sync_mode_spin.setRange(0, 200)
        self.sync_mode_spin.setValue(100)  # Start with different value
        sync_row.addWidget(self.sync_mode_spin)
        self.bind_sync_btn = QPushButton("Bind (widget ← 50)")
        self.bind_sync_btn.clicked.connect(self.bind_sync_mode)
        sync_row.addWidget(self.bind_sync_btn)
        self.unbind_sync_btn = QPushButton("Reset")
        self.unbind_sync_btn.clicked.connect(self.unbind_sync_mode)
        self.unbind_sync_btn.setEnabled(False)
        sync_row.addWidget(self.unbind_sync_btn)
        sync_row.addStretch()
        basic_layout.addLayout(sync_row)

        # init_from='widget'
        widget_row = QHBoxLayout()
        widget_row.addWidget(QLabel("init_from='widget':"))
        self.widget_mode_spin = QSpinBox()
        self.widget_mode_spin.setRange(0, 200)
        self.widget_mode_spin.setValue(100)
        widget_row.addWidget(self.widget_mode_spin)
        self.bind_widget_btn = QPushButton("Bind (sync ← 100)")
        self.bind_widget_btn.clicked.connect(self.bind_widget_mode)
        widget_row.addWidget(self.bind_widget_btn)
        self.unbind_widget_btn = QPushButton("Reset")
        self.unbind_widget_btn.clicked.connect(self.unbind_widget_mode)
        self.unbind_widget_btn.setEnabled(False)
        widget_row.addWidget(self.unbind_widget_btn)
        widget_row.addStretch()
        basic_layout.addLayout(widget_row)

        # init_from=None
        none_row = QHBoxLayout()
        none_row.addWidget(QLabel("init_from=None:"))
        self.none_mode_spin = QSpinBox()
        self.none_mode_spin.setRange(0, 200)
        self.none_mode_spin.setValue(100)
        none_row.addWidget(self.none_mode_spin)
        self.bind_none_btn = QPushButton("Bind (no change)")
        self.bind_none_btn.clicked.connect(self.bind_none_mode)
        none_row.addWidget(self.bind_none_btn)
        self.unbind_none_btn = QPushButton("Reset")
        self.unbind_none_btn.clicked.connect(self.unbind_none_mode)
        self.unbind_none_btn.setEnabled(False)
        none_row.addWidget(self.unbind_none_btn)
        none_row.addStretch()
        basic_layout.addLayout(none_row)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Example 2: bind_dict with init_from
        dict_group = QGroupBox("2. bind_dict() - Initialize RGB from sliders OR from sync")
        dict_layout = QVBoxLayout()

        dict_layout.addWidget(QLabel(
            "SCENARIO: You have RGB sliders at specific positions.\n"
            "CHOICE 1: Overwrite sliders with sync's colors (init_from='sync')\n"
            "CHOICE 2: Capture slider positions into sync (init_from='widget')\n"
            "Try both! Reset sliders between attempts to see the difference."
        ))

        # Control buttons at top
        control_row = QHBoxLayout()
        self.reset_sliders_btn = QPushButton("Reset Sliders (R=128, G=64, B=192)")
        self.reset_sliders_btn.clicked.connect(self.reset_color_sliders)
        control_row.addWidget(self.reset_sliders_btn)

        self.unbind_color_btn = QPushButton("Unbind All")
        self.unbind_color_btn.clicked.connect(self.unbind_color)
        self.unbind_color_btn.setEnabled(False)
        control_row.addWidget(self.unbind_color_btn)
        dict_layout.addLayout(control_row)

        # Color sliders
        self.color_r_slider = self._create_slider("R", 128)
        self.color_g_slider = self._create_slider("G", 64)
        self.color_b_slider = self._create_slider("B", 192)

        dict_layout.addLayout(self.color_r_slider[1])
        dict_layout.addLayout(self.color_g_slider[1])
        dict_layout.addLayout(self.color_b_slider[1])

        # Color preview
        self.color_preview = QLabel("Color Preview")
        self.color_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.color_preview.setMinimumHeight(40)
        self.color_preview.setAutoFillBackground(True)
        self.update_color_preview_manual()
        dict_layout.addWidget(self.color_preview)

        # Bind buttons
        bind_row = QHBoxLayout()

        bind_from_sync_btn = QPushButton("Bind: Sliders ← Sync (255, 100, 50)")
        bind_from_sync_btn.clicked.connect(self.bind_color_from_sync)
        bind_row.addWidget(bind_from_sync_btn)

        bind_from_widget_btn = QPushButton("Bind: Sync ← Sliders (current)")
        bind_from_widget_btn.clicked.connect(self.bind_color_from_widget)
        bind_row.addWidget(bind_from_widget_btn)

        dict_layout.addLayout(bind_row)

        self.color_status = QLabel("Not bound. Adjust sliders, then choose a bind option above.")
        dict_layout.addWidget(self.color_status)

        dict_group.setLayout(dict_layout)
        layout.addWidget(dict_group)

        # Example 3: bind_dict with per-property init_from
        props_group = QGroupBox("3. bind_dict() - Per-Property init_from (Mixed Sources)")
        props_layout = QVBoxLayout()

        props_layout.addWidget(QLabel(
            "SCENARIO: A config with 2 properties. Where does each get its initial value?\n"
            "We'll bind with MIXED init_from: 'name' from widget, 'enabled' from sync.\n"
            "BEFORE: Widget shows (name='MyWidget', enabled=True), Sync has (name='DefaultName', enabled=False)\n"
            "AFTER: BOTH will have (name='MyWidget' from widget, enabled=False from sync)"
        ))

        # Before state
        before_box = QGroupBox("BEFORE Binding")
        before_layout = QVBoxLayout()
        before_layout.addWidget(QLabel("Widget state: name='MyWidget', enabled=True"))
        before_layout.addWidget(QLabel("Sync state: name='DefaultName', enabled=False"))
        before_box.setLayout(before_layout)
        before_box.setStyleSheet("QGroupBox {  }")
        props_layout.addWidget(before_box)

        # Config widgets
        config_widget_box = QGroupBox("Widget Controls")
        config_widget_layout = QVBoxLayout()

        config_row1 = QHBoxLayout()
        config_row1.addWidget(QLabel("Name:"))
        self.config_name_edit = QLineEdit()
        self.config_name_edit.setText("MyWidget")
        config_row1.addWidget(self.config_name_edit)
        config_widget_layout.addLayout(config_row1)

        self.config_enabled_check = QCheckBox("Enabled")
        self.config_enabled_check.setChecked(True)
        config_widget_layout.addWidget(self.config_enabled_check)

        config_widget_box.setLayout(config_widget_layout)
        props_layout.addWidget(config_widget_box)

        # Bind button
        bind_buttons = QHBoxLayout()
        bind_props_btn = QPushButton("Bind with Mixed init_from")
        bind_props_btn.clicked.connect(self.bind_config_properties)
        bind_buttons.addWidget(bind_props_btn)

        self.unbind_config_btn = QPushButton("Unbind & Reset")
        self.unbind_config_btn.clicked.connect(self.unbind_config)
        self.unbind_config_btn.setEnabled(False)
        bind_buttons.addWidget(self.unbind_config_btn)
        props_layout.addLayout(bind_buttons)

        self.config_status = QLabel("Not bound yet. Click 'Bind with Mixed init_from' to see the result!")
        self.config_status.setWordWrap(True)
        self.config_status.setStyleSheet("padding: 10px; border: 1px solid #0066cc;")
        props_layout.addWidget(self.config_status)

        props_group.setLayout(props_layout)
        layout.addWidget(props_group)

        layout.addStretch()

        # Initialize state
        self.color_sync = None
        self.config_sync = None

    def _create_slider(self, name, initial_value):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 255)
        slider.setValue(initial_value)
        label = QLabel(f"{name}: {initial_value}")
        slider.valueChanged.connect(lambda v, l=label, n=name: l.setText(f"{n}: {v}"))

        row = QHBoxLayout()
        row.addWidget(label)
        row.addWidget(slider)

        return slider, row

    def bind_sync_mode(self):
        """Bind with init_from='sync' (default)"""
        self.demo_sync.bind(
            self.sync_mode_spin,
            signal=self.sync_mode_spin.valueChanged,
            getter=self.sync_mode_spin.value,
            setter=self.sync_mode_spin.setValue,
            init_from='sync'  # Widget gets sync's value (50)
        )
        self.bind_sync_btn.setEnabled(False)
        self.unbind_sync_btn.setEnabled(True)

    def unbind_sync_mode(self):
        """Unbind and reset"""
        self.demo_sync.unbind(self.sync_mode_spin)
        self.sync_mode_spin.setValue(100)
        self.bind_sync_btn.setEnabled(True)
        self.unbind_sync_btn.setEnabled(False)

    def bind_widget_mode(self):
        """Bind with init_from='widget'"""
        self.demo_sync.bind(
            self.widget_mode_spin,
            signal=self.widget_mode_spin.valueChanged,
            getter=self.widget_mode_spin.value,
            setter=self.widget_mode_spin.setValue,
            init_from='widget'  # Sync gets widget's value (100)
        )
        self.bind_widget_btn.setEnabled(False)
        self.unbind_widget_btn.setEnabled(True)

    def unbind_widget_mode(self):
        """Unbind and reset"""
        self.demo_sync.unbind(self.widget_mode_spin)
        self.widget_mode_spin.setValue(100)
        self.demo_sync.value = 50  # Reset sync value
        self.bind_widget_btn.setEnabled(True)
        self.unbind_widget_btn.setEnabled(False)

    def bind_none_mode(self):
        """Bind with init_from=None"""
        self.demo_sync.bind(
            self.none_mode_spin,
            signal=self.none_mode_spin.valueChanged,
            getter=self.none_mode_spin.value,
            setter=self.none_mode_spin.setValue,
            init_from=None  # No initialization
        )
        self.bind_none_btn.setEnabled(False)
        self.unbind_none_btn.setEnabled(True)

    def unbind_none_mode(self):
        """Unbind and reset"""
        self.demo_sync.unbind(self.none_mode_spin)
        self.none_mode_spin.setValue(100)
        self.demo_sync.value = 50  # Reset sync value
        self.bind_none_btn.setEnabled(True)
        self.unbind_none_btn.setEnabled(False)

    def reset_color_sliders(self):
        """Reset sliders to default positions"""
        self.color_r_slider[0].setValue(128)
        self.color_g_slider[0].setValue(64)
        self.color_b_slider[0].setValue(192)
        self.update_color_preview_manual()
        self.color_status.setText("Sliders reset to R=128, G=64, B=192. Choose a bind option.")

    def unbind_color(self):
        """Unbind color sliders"""
        if self.color_sync:
            self.color_sync.unbind(self.color_r_slider[0])
            self.color_sync.unbind(self.color_g_slider[0])
            self.color_sync.unbind(self.color_b_slider[0])
            self.color_sync = None
        self.unbind_color_btn.setEnabled(False)
        self.color_status.setText("Unbound. You can now try the other bind option!")
        self.update_color_preview_manual()

    def update_color_preview_manual(self):
        """Update preview based on slider positions (when not bound)"""
        r = self.color_r_slider[0].value()
        g = self.color_g_slider[0].value()
        b = self.color_b_slider[0].value()
        self.color_preview.setStyleSheet(
            f"background-color: rgb({r}, {g}, {b}); "
            f"border: 1px solid black;"
        )

    def bind_color_from_sync(self):
        """Bind color sliders with init_from='sync'"""
        if self.color_sync:
            self.unbind_color()

        self.color_sync = WidgetSync(initial_value={'r': 255, 'g': 100, 'b': 50})

        self.color_sync.bind_dict({
            'r': {'widget': self.color_r_slider[0], 'property': 'value'},
            'g': {'widget': self.color_g_slider[0], 'property': 'value'},
            'b': {'widget': self.color_b_slider[0], 'property': 'value'}
        }, init_from='sync')  # Sliders get sync's values

        self.color_sync.value_changed.connect(self.update_color_preview)
        self.update_color_preview(self.color_sync.value)

        self.color_status.setText(
            "✓ Bound with init_from='sync'\n"
            "RESULT: Sliders jumped to sync's values (R=255, G=100, B=50)\n"
            "Try 'Unbind All' then 'Reset Sliders' to test the other mode!"
        )
        self.unbind_color_btn.setEnabled(True)

    def bind_color_from_widget(self):
        """Bind color sliders with init_from='widget'"""
        if self.color_sync:
            self.unbind_color()

        # Capture current slider values
        current_r = self.color_r_slider[0].value()
        current_g = self.color_g_slider[0].value()
        current_b = self.color_b_slider[0].value()

        self.color_sync = WidgetSync(initial_value={'r': 0, 'g': 0, 'b': 0})

        self.color_sync.bind_dict({
            'r': {'widget': self.color_r_slider[0], 'property': 'value'},
            'g': {'widget': self.color_g_slider[0], 'property': 'value'},
            'b': {'widget': self.color_b_slider[0], 'property': 'value'}
        }, init_from='widget')  # Sync gets current slider values

        self.color_sync.value_changed.connect(self.update_color_preview)
        self.update_color_preview(self.color_sync.value)

        self.color_status.setText(
            f"✓ Bound with init_from='widget'\n"
            f"RESULT: Sync captured slider values (R={current_r}, G={current_g}, B={current_b})\n"
            f"Sliders stayed where they were. Now try the other mode!"
        )
        self.unbind_color_btn.setEnabled(True)

    def bind_config_properties(self):
        """Bind config with per-property init_from"""
        if self.config_sync:
            self.unbind_config()

        self.config_sync = WidgetSync(initial_value={
            'name': 'DefaultName',
            'enabled': False
        })

        # Use bind_dict with per-property init_from override
        self.config_sync.bind_dict({
            'name': {
                'widget': self.config_name_edit,
                'property': 'text',
                'init_from': 'widget'  # Sync gets widget's "MyWidget"
            },
            'enabled': {
                'widget': self.config_enabled_check,
                'property': 'checked',
                'init_from': 'sync'  # Widget gets sync's False
            }
        })

        self.config_status.setText(
            f"✓ BOUND with mixed init_from!\n\n"
            f"RESULT in sync: name='{self.config_sync.value['name']}' (from widget), "
            f"enabled={self.config_sync.value['enabled']} (stayed in sync)\n\n"
            f"RESULT in widgets: Name stayed 'MyWidget', Checkbox changed to {self.config_enabled_check.isChecked()}\n\n"
            f"KEY POINT: Different properties can initialize from different sources!"
        )
        self.unbind_config_btn.setEnabled(True)

    def unbind_config(self):
        """Unbind and reset config"""
        if self.config_sync:
            self.config_sync.unbind(self.config_name_edit)
            self.config_sync.unbind(self.config_enabled_check)
            self.config_sync = None
        self.config_name_edit.setText("MyWidget")
        self.config_enabled_check.setChecked(True)
        self.config_status.setText("Reset! Try binding again to see the effect.")
        self.unbind_config_btn.setEnabled(False)

    def update_color_preview(self, rgb):
        self.color_preview.setStyleSheet(
            f"background-color: rgb({rgb['r']}, {rgb['g']}, {rgb['b']}); "
            f"border: 1px solid black;"
        )



class AdvancedSyncDemo(QWidget):
    """Main window with tabs"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Level 3: Advanced Synchronization")
        self.setMinimumSize(750, 500)

        layout = QVBoxLayout(self)
        header = QLabel("Advanced Synchronization - Expert Patterns")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        tabs = QTabWidget()
        tabs.addTab(MultipleSyncsExample(), "1. Multiple Syncs")
        tabs.addTab(DynamicPropertiesExample(), "2. Dynamic Properties")
        tabs.addTab(ComplexScenarioExample(), "3. Complex Scenario")
        tabs.addTab(InitFromExample(), "4. init_from Parameter")

        layout.addWidget(tabs)


def main():
    app = QApplication(sys.argv)
    window = AdvancedSyncDemo()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

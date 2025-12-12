"""
Level 5: Extending Widget Sync
================================

Learn the three ways to extend widget_sync:

1. Custom Factory Methods (Easiest)
   - Add convenience methods for your custom widget types
   - No subclassing needed, just extend WidgetSyncFactories

2. Custom Validators (Common)
   - Add validation/transformation logic without subclassing
   - Use with ValueSync or DictSync directly
   - Perfect for business logic constraints

3. Custom Sync Classes (Advanced)
   - Only when you need computed/derived values
   - Storage format differs from exposed format
   - Examples: Unit conversions, color space transformations

Run: python -m pymodaq_gui.examples.widget_sync.6_extending_sync_example
"""
import sys
from qtpy.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QGroupBox, QLabel, QPushButton, QTabWidget,
                             QSpinBox, QSlider, QLineEdit, QDoubleSpinBox)
from qtpy.QtCore import Qt, Signal

from pymodaq_gui.utils.widget_sync import (WidgetSync, WidgetSyncFactories,
                                           BaseWidgetSync, SyncMode, DictSync)


# =============================================================================
# Example 1: Custom Factory Methods (Easiest)
# =============================================================================

class CustomWidgetSyncFactories(WidgetSyncFactories):
    """
    Extend WidgetSyncFactories to add convenience methods for custom widgets.

    This is the easiest way to extend widget_sync - no need to subclass
    BaseWidgetSync, just add factory methods.
    """

    @classmethod
    def for_range_spinbox(cls, min_spinbox, max_spinbox, initial_min=0,
                         initial_max=100, validator=None):
        """
        Factory for synchronizing min/max spinboxes as a dict.

        This creates a DictSync for two related spinboxes representing a range.

        Parameters
        ----------
        min_spinbox : QSpinBox
            SpinBox for minimum value
        max_spinbox : QSpinBox
            SpinBox for maximum value
        initial_min : int
            Initial minimum value
        initial_max : int
            Initial maximum value
        validator : callable, optional
            Validator to ensure min <= max

        Returns
        -------
        WidgetSync
            A DictSync instance with both spinboxes connected

        Example
        -------
        >>> sync = CustomWidgetSync.for_range_spinbox(min_spin, max_spin)
        >>> sync.value  # {'min': 0, 'max': 100}
        """
        # Default validator: ensure min <= max, auto-swap if needed
        if validator is None:
            def default_validator(value):
                min_val, max_val = value['min'], value['max']
                if min_val > max_val:
                    return {'min': max_val, 'max': min_val}
                return value
            validator = default_validator

        # Create dict sync
        sync = cls(initial_value={'min': initial_min, 'max': initial_max},
                  validator=validator)

        # Bind both spinboxes
        sync.bind_dict({
            'min': {'widget': min_spinbox, 'property': 'value'},
            'max': {'widget': max_spinbox, 'property': 'value'}
        })

        return sync

    @classmethod
    def for_slider_with_label(cls, slider, label, initial=50,
                             format_func=None, validator=None):
        """
        Factory for slider with synchronized read-only label.

        Parameters
        ----------
        slider : QSlider
            The slider widget
        label : QLabel
            Label to display the value
        initial : int
            Initial value
        format_func : callable, optional
            Function to format value for display: (value) -> str
            Default: str(value)
        validator : callable, optional
            Optional validator function

        Returns
        -------
        WidgetSync
            A ValueSync with slider (bidirectional) and label (read-only)
        """
        if format_func is None:
            format_func = str

        sync = cls.for_slider(slider, initial=initial, validator=validator)

        # Add label as read-only display
        sync.bind(
            label,
            setter=lambda v: label.setText(format_func(v)),
            mode=SyncMode.FROM_SYNC
        )

        return sync


# Custom WidgetSync class with our factories
class CustomWidgetSync(WidgetSync, CustomWidgetSyncFactories):
    """
    Enhanced WidgetSync with custom factory methods.

    Inherits all standard factories plus our custom ones.
    """
    pass


class FactoryMethodsExample(QWidget):
    """Example 1: Custom factory methods for common patterns"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Option 1: Custom Factory Methods (Easiest)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✓ Extend WidgetSyncFactories with @classmethod\n"
            "✓ No need to subclass BaseWidgetSync\n"
            "✓ Perfect for common patterns in your application\n"
            "✓ Combines existing sync functionality with convenience API"
        ))

        # Example 1: Range spinboxes
        range_group = QGroupBox("Range SpinBoxes (Custom Factory)")
        range_layout = QVBoxLayout()

        spin_row = QHBoxLayout()
        spin_row.addWidget(QLabel("Min:"))
        self.min_spin = QSpinBox()
        self.min_spin.setRange(0, 1000)
        spin_row.addWidget(self.min_spin)

        spin_row.addWidget(QLabel("Max:"))
        self.max_spin = QSpinBox()
        self.max_spin.setRange(0, 1000)
        spin_row.addWidget(self.max_spin)
        spin_row.addStretch()
        range_layout.addLayout(spin_row)

        # Use custom factory
        self.range_sync = CustomWidgetSync.for_range_spinbox(
            self.min_spin,
            self.max_spin,
            initial_min=20,
            initial_max=80
        )

        status = QLabel()
        self.range_sync.value_changed.connect(
            lambda v: status.setText(f"Range: [{v['min']}, {v['max']}]")
        )
        status.setText(f"Range: [{self.range_sync.value['min']}, {self.range_sync.value['max']}]")
        range_layout.addWidget(status)

        range_group.setLayout(range_layout)
        layout.addWidget(range_group)

        # Example 2: Slider with label
        slider_group = QGroupBox("Slider with Label (Custom Factory)")
        slider_layout = QVBoxLayout()

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        slider_layout.addWidget(self.slider)

        self.slider_label = QLabel()
        self.slider_label.setStyleSheet(
            "font-size: 20pt; font-weight: bold; color: #2196f3;"
        )
        slider_layout.addWidget(self.slider_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Use custom factory with formatting
        self.slider_sync = CustomWidgetSync.for_slider_with_label(
            self.slider,
            self.slider_label,
            initial=50,
            format_func=lambda v: f"{v}%"
        )

        slider_group.setLayout(slider_layout)
        layout.addWidget(slider_group)

        # Code example
        code = QLabel(
            "Implementation:\n"
            "class CustomFactories(WidgetSyncFactories):\n"
            "    @classmethod\n"
            "    def for_range_spinbox(cls, min_spin, max_spin, ...):\n"
            "        sync = cls(initial_value={'min': ..., 'max': ...})\n"
            "        sync.bind_dict(...)\n"
            "        return sync\n"
            "\n"
            "class MySync(WidgetSync, CustomFactories):\n"
            "    pass\n"
            "\n"
            "# Usage:\n"
            "sync = MySync.for_range_spinbox(min_spin, max_spin)"
        )
        code.setStyleSheet("font-family: monospace; padding: 10px; font-size: 9pt;")
        layout.addWidget(code)

        layout.addStretch()


# =============================================================================
# Example 2: Custom Validators (Common)
# =============================================================================

class ValidatorsExample(QWidget):
    """Example 2: Custom validators for business logic"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Option 2: Custom Validators (Common)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✓ Add validation/transformation without subclassing\n"
            "✓ Works with ValueSync or DictSync\n"
            "✓ Perfect for business logic constraints\n"
            "✓ Can auto-correct invalid values"
        ))

        # Example 1: Clamping validator
        clamp_group = QGroupBox("Clamping Validator (Auto-correct)")
        clamp_layout = QVBoxLayout()

        clamp_layout.addWidget(QLabel(
            "Use Case: Power setting must stay in safe range 0-100 W\n"
            "Try entering 150 or -50 - it will auto-clamp on Enter/focus loss"
        ))

        input_row = QHBoxLayout()
        input_row.addWidget(QLabel("Power:"))
        self.clamp_lineedit = QLineEdit()
        self.clamp_lineedit.setPlaceholderText("Type any value, press Enter")
        input_row.addWidget(self.clamp_lineedit)
        input_row.addWidget(QLabel("W"))
        input_row.addStretch()
        clamp_layout.addLayout(input_row)

        # Display widgets showing clamped value
        display_row = QHBoxLayout()
        display_row.addWidget(QLabel("Display 1:"))
        self.clamp_spin1 = QSpinBox()
        self.clamp_spin1.setRange(0, 100)
        self.clamp_spin1.setReadOnly(True)
        self.clamp_spin1.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.clamp_spin1.setSuffix(" W")
        display_row.addWidget(self.clamp_spin1)

        display_row.addWidget(QLabel("Display 2:"))
        self.clamp_spin2 = QSpinBox()
        self.clamp_spin2.setRange(0, 100)
        self.clamp_spin2.setReadOnly(True)
        self.clamp_spin2.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.clamp_spin2.setSuffix(" W")
        display_row.addWidget(self.clamp_spin2)
        display_row.addStretch()
        clamp_layout.addLayout(display_row)

        def clamp_validator(value):
            """Clamp value to 0-100 range."""
            try:
                val = int(value)
                clamped = max(0, min(100, val))
                return clamped
            except (ValueError, TypeError):
                return 0

        self.clamp_sync = WidgetSync(initial_value=50, validator=clamp_validator)

        # Bind input (can type anything)
        self.clamp_sync.bind(
            self.clamp_lineedit,
            signal=self.clamp_lineedit.editingFinished,
            getter=lambda: self.clamp_lineedit.text(),
            setter=lambda v: self.clamp_lineedit.setText(str(v))
        )

        # Bind displays (read-only, show clamped value)
        self.clamp_sync.bind(
            self.clamp_spin1,
            setter=lambda v: self.clamp_spin1.setValue(v),
            mode=SyncMode.FROM_SYNC
        )
        self.clamp_sync.bind(
            self.clamp_spin2,
            setter=lambda v: self.clamp_spin2.setValue(v),
            mode=SyncMode.FROM_SYNC
        )

        clamp_status = QLabel()
        self.clamp_sync.value_changed.connect(
            lambda v: clamp_status.setText(
                f"✓ Validated value: {v} W (safe range enforced)"
            )
        )
        clamp_status.setText(f"✓ Validated value: {self.clamp_sync.value} W")
        clamp_status.setStyleSheet("color: green; font-weight: bold;")
        clamp_layout.addWidget(clamp_status)

        clamp_group.setLayout(clamp_layout)
        layout.addWidget(clamp_group)

        # Example 2: Range validator with auto-swap
        range_group = QGroupBox("Range Validator (Auto-swap if invalid)")
        range_layout = QVBoxLayout()

        range_layout.addWidget(QLabel(
            "Use Case: Scan range start/stop must be ordered\n"
            "Set Start=800 and Stop=200 → they auto-swap to ensure start < stop"
        ))

        spin_row = QHBoxLayout()
        spin_row.addWidget(QLabel("Scan Start:"))
        self.range_start = QSpinBox()
        self.range_start.setRange(0, 1000)
        self.range_start.setSuffix(" nm")
        spin_row.addWidget(self.range_start)

        spin_row.addWidget(QLabel("Scan Stop:"))
        self.range_stop = QSpinBox()
        self.range_stop.setRange(0, 1000)
        self.range_stop.setSuffix(" nm")
        spin_row.addWidget(self.range_stop)
        spin_row.addStretch()
        range_layout.addLayout(spin_row)

        def range_validator(value):
            """Ensure start <= stop, swap if needed."""
            start, stop = value['start'], value['stop']
            if start > stop:
                return {'start': stop, 'stop': start}
            return value

        self.range_sync = WidgetSync(
            initial_value={'start': 200, 'stop': 800},
            validator=range_validator
        )

        self.range_sync.bind_dict({
            'start': {'widget': self.range_start, 'property': 'value'},
            'stop': {'widget': self.range_stop, 'property': 'value'}
        })

        range_status = QLabel()
        def update_range_status(v):
            swapped = (v['start'] == self.range_sync._previous_value.get('stop') and
                      v['stop'] == self.range_sync._previous_value.get('start'))
            text = f"Valid range: [{v['start']}, {v['stop']}] nm"
            if swapped:
                text += " ⚠ (auto-swapped!)"
                range_status.setStyleSheet("color: orange; font-weight: bold;")
            else:
                range_status.setStyleSheet("color: green; font-weight: bold;")
            range_status.setText(text)

        self.range_sync.value_changed.connect(update_range_status)
        update_range_status(self.range_sync.value)
        range_layout.addWidget(range_status)

        range_group.setLayout(range_layout)
        layout.addWidget(range_group)

        # Code example
        code = QLabel(
            "Implementation:\n"
            "def clamp_validator(value):\n"
            "    return max(0, min(100, value))\n"
            "\n"
            "sync = WidgetSync(initial_value=50, validator=clamp_validator)\n"
            "sync.bind(spinbox, ...)\n"
            "\n"
            "# For dicts:\n"
            "def range_validator(value):\n"
            "    if value['min'] > value['max']:\n"
            "        return {'min': value['max'], 'max': value['min']}\n"
            "    return value\n"
            "\n"
            "sync = WidgetSync(\n"
            "    initial_value={'min': 0, 'max': 100},\n"
            "    validator=range_validator\n"
            ")"
        )
        code.setStyleSheet("font-family: monospace; padding: 10px; font-size: 9pt;")
        layout.addWidget(code)

        layout.addStretch()


# =============================================================================
# Example 3: Custom Sync Classes (Advanced)
# =============================================================================

class CoordinateSync(DictSync):
    """
    Custom sync for image coordinates with different origin conventions.

    Imaging systems use different coordinate conventions:
    - Top-left origin (0,0) at top-left, Y increases downward (standard computer graphics)
    - Bottom-left origin (0,0) at bottom-left, Y increases upward (scientific plotting)
    - Center origin (0,0) at center, useful for optical systems

    This stores coordinates internally in top-left convention but allows
    widgets to display in any convention.

    This demonstrates when to subclass BaseWidgetSync:
    - Storage format differs from display formats
    - Automatic coordinate transformation
    - Can't be done with simple validators (needs image height context)
    """

    value_changed = Signal(dict)  # Emits {'x': int, 'y': int} in top-left coords

    def __init__(self, image_width=1024, image_height=768, initial_x=512, initial_y=384):
        super().__init__()
        self._image_width = image_width
        self._image_height = image_height
        self._data_type = dict
        self._value = {'x': initial_x, 'y': initial_y}  # Store in top-left coords
        self._previous_value = self._value.copy()

    @property
    def value(self):
        """Get coordinates in top-left convention."""
        return self._value.copy()

    @value.setter
    def value(self, coords):
        """Set coordinates in top-left convention."""
        self.set_value(coords, emit=True)

    def set_value(self, coords, emit=True):
        """Set coordinates in top-left convention with optional emission control."""
        if self._value != coords:
            self._previous_value = self._value.copy()
            self._value = coords.copy()
            if emit:
                self.value_changed.emit(self._value)

    def _get_internal_storage_key(self):
        """Return None for dict storage."""
        return None

    def _get_user_facing_value(self):
        """Return coordinates in top-left convention."""
        return self._value.copy()

    def bind_top_left(self, x_widget, y_widget):
        """Bind widgets using top-left origin (standard computer graphics)."""
        self.bind_dict({
            'x': {
                'widget': x_widget,
                'signal': x_widget.valueChanged,
                'getter': x_widget.value,
                'setter': x_widget.setValue
            },
            'y': {
                'widget': y_widget,
                'signal': y_widget.valueChanged,
                'getter': y_widget.value,
                'setter': y_widget.setValue
            }
        })

    def bind_bottom_left(self, x_widget, y_widget):
        """Bind widgets using bottom-left origin (scientific plotting)."""
        height = self._image_height

        self.bind_dict({
            'x': {
                'widget': x_widget,
                'signal': x_widget.valueChanged,
                'getter': x_widget.value,
                'setter': x_widget.setValue
            },
            'y': {
                'widget': y_widget,
                'signal': y_widget.valueChanged,
                'getter': lambda: height - y_widget.value(),  # Flip Y
                'setter': lambda y: y_widget.setValue(height - y)
            }
        })

    def bind_center(self, x_widget, y_widget):
        """Bind widgets using center origin (optical systems)."""
        cx = self._image_width // 2
        cy = self._image_height // 2

        self.bind_dict({
            'x': {
                'widget': x_widget,
                'signal': x_widget.valueChanged,
                'getter': lambda: x_widget.value() + cx,  # Offset to center
                'setter': lambda x: x_widget.setValue(x - cx)
            },
            'y': {
                'widget': y_widget,
                'signal': y_widget.valueChanged,
                'getter': lambda: y_widget.value() + cy,
                'setter': lambda y: y_widget.setValue(y - cy)
            }
        })


class CustomSyncExample(QWidget):
    """Example 3: Custom sync class for computed/derived values"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Option 3: Custom Sync Classes (Advanced)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✓ Only when storage format differs from display format\n"
            "✓ Subclass BaseWidgetSync\n"
            "✓ Implement: __init__, value property, set_value(), helpers\n"
            "✓ Example: Image coordinates with different origin conventions"
        ))

        coord_group = QGroupBox("Coordinate Sync (Multiple Origins)")
        coord_layout = QVBoxLayout()

        coord_layout.addWidget(QLabel(
            "Use Case: 1024×768 image with different coordinate systems\n"
            "Stored internally as top-left origin, displayed in three conventions"
        ))

        # Top-left origin (standard computer graphics)
        tl_row = QHBoxLayout()
        tl_row.addWidget(QLabel("Top-Left (0,0):"))
        self.tl_x = QSpinBox()
        self.tl_x.setRange(0, 1023)
        self.tl_x.setPrefix("X=")
        tl_row.addWidget(self.tl_x)
        self.tl_y = QSpinBox()
        self.tl_y.setRange(0, 767)
        self.tl_y.setPrefix("Y=")
        tl_row.addWidget(self.tl_y)
        tl_row.addWidget(QLabel("(standard graphics)"))
        tl_row.addStretch()
        coord_layout.addLayout(tl_row)

        # Bottom-left origin (scientific plotting)
        bl_row = QHBoxLayout()
        bl_row.addWidget(QLabel("Bottom-Left (0,0):"))
        self.bl_x = QSpinBox()
        self.bl_x.setRange(0, 1023)
        self.bl_x.setPrefix("X=")
        bl_row.addWidget(self.bl_x)
        self.bl_y = QSpinBox()
        self.bl_y.setRange(0, 767)
        self.bl_y.setPrefix("Y=")
        bl_row.addWidget(self.bl_y)
        bl_row.addWidget(QLabel("(scientific plot)"))
        bl_row.addStretch()
        coord_layout.addLayout(bl_row)

        # Center origin (optical systems)
        center_row = QHBoxLayout()
        center_row.addWidget(QLabel("Center (0,0):"))
        self.center_x = QSpinBox()
        self.center_x.setRange(-512, 511)
        self.center_x.setPrefix("X=")
        center_row.addWidget(self.center_x)
        self.center_y = QSpinBox()
        self.center_y.setRange(-384, 383)
        self.center_y.setPrefix("Y=")
        center_row.addWidget(self.center_y)
        center_row.addWidget(QLabel("(optical system)"))
        center_row.addStretch()
        coord_layout.addLayout(center_row)

        # Create custom sync (start at center of image)
        self.coord_sync = CoordinateSync(
            image_width=1024,
            image_height=768,
            initial_x=512,
            initial_y=384
        )

        # Bind all three coordinate systems
        self.coord_sync.bind_top_left(self.tl_x, self.tl_y)
        self.coord_sync.bind_bottom_left(self.bl_x, self.bl_y)
        self.coord_sync.bind_center(self.center_x, self.center_y)

        # Status
        status = QLabel()
        self.coord_sync.value_changed.connect(
            lambda coords: status.setText(
                f"✓ Stored (top-left): X={coords['x']}, Y={coords['y']}"
            )
        )
        status.setText(f"✓ Stored (top-left): X={self.coord_sync.value['x']}, Y={self.coord_sync.value['y']}")
        status.setStyleSheet("font-weight: bold; padding: 5px; color: green;")
        coord_layout.addWidget(status)

        coord_group.setLayout(coord_layout)
        layout.addWidget(coord_group)

        # Code example
        code = QLabel(
            "Implementation:\n"
            "class CoordinateSync(DictSync):\n"
            "    def __init__(self, image_width, image_height, initial_x, initial_y):\n"
            "        super().__init__()\n"
            "        self._value = {'x': initial_x, 'y': initial_y}  # Store top-left\n"
            "    \n"
            "    def bind_bottom_left(self, x_widget, y_widget):\n"
            "        # Y-axis flip: bottom-left Y=0 is top-left Y=height\n"
            "        self.bind_dict({\n"
            "            'x': {'widget': x_widget, 'getter': x_widget.value, ...},\n"
            "            'y': {'widget': y_widget,\n"
            "                  'getter': lambda: self._image_height - y_widget.value() - 1,\n"
            "                  'setter': lambda v: y_widget.setValue(self._image_height - v - 1)}\n"
            "        })\n"
            "\n"
            "# Usage:\n"
            "coord = CoordinateSync(1024, 768, 512, 384)\n"
            "coord.bind_top_left(tl_x, tl_y)      # Direct mapping\n"
            "coord.bind_bottom_left(bl_x, bl_y)   # Y-axis flipped\n"
            "coord.bind_center(c_x, c_y)          # Origin at center"
        )
        code.setStyleSheet("font-family: monospace; padding: 10px; font-size: 9pt;")
        layout.addWidget(code)

        layout.addStretch()


class ExtendingSyncDemo(QWidget):
    """Main window with extension examples"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Level 6: Extending Widget Sync")
        self.setMinimumSize(900, 700)

        layout = QVBoxLayout(self)

        header = QLabel("Extending Widget Sync - Three Approaches")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        description = QLabel(
            "Learn when and how to extend widget_sync for your needs.\n"
            "Most users only need Options 1 or 2. Option 3 is for advanced cases."
        )
        description.setWordWrap(True)
        description.setStyleSheet("padding: 5px 10px; color: #666;")
        layout.addWidget(description)

        tabs = QTabWidget()
        tabs.addTab(FactoryMethodsExample(), "1. Factory Methods")
        tabs.addTab(ValidatorsExample(), "2. Validators")
        tabs.addTab(CustomSyncExample(), "3. Custom Sync Class")

        layout.addWidget(tabs)


def main():
    app = QApplication(sys.argv)
    window = ExtendingSyncDemo()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

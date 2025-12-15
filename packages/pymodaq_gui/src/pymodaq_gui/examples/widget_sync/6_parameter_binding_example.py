"""
Example 6: Parameter Binding with bind_parameter()
===================================================

Demonstrates how to bind pyqtgraph Parameters to WidgetSync using the new
bind_parameter() method, which avoids the blockSignals() issue that prevents
parameter tree widgets from updating.

Key Concepts
------------
- Use bind_parameter() for pyqtgraph Parameters (not bind_properties())
- Sync both parameter opts (limits) and values
- Bidirectional synchronization between parameter tree and external widgets
- Clean API without manual signal connection boilerplate
- Multiple tabs with different parameter groups

Run
---
python -m pymodaq_gui.examples.widget_sync.6_parameter_binding_example
"""

import sys
from qtpy.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QSpinBox, QCheckBox,
                             QGroupBox, QMainWindow, QDockWidget,
                             QPushButton, QDoubleSpinBox, QTabWidget, QLineEdit,
                             QFormLayout)
from qtpy.QtCore import Qt

from pymodaq_gui.parameter import Parameter, ParameterTree
from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode


class ParameterBindingExample(QMainWindow):
    """
    Example showing how to use bind_parameter() to sync Parameters with widgets.

    Demonstrates:
    - Syncing list parameters (opts + value)
    - Syncing numeric parameters (int, float)
    - Syncing boolean and string parameters
    - Multiple tabs with different parameter groups
    - Parameter tree staying synchronized with all tabs
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Example 6: Parameter Binding with Tabs")
        self.resize(1200, 700)

        # Data lists
        self.algorithms = ['FFT', 'Wavelet', 'Correlation', 'ML-Enhanced', 'Adaptive']
        self.modes = ['Continuous', 'Single Shot', 'Triggered']
        self.units = ['mm', 'µm', 'nm']

        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Description
        desc = QLabel(
            "bind_parameter() Method for Parameters\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• Use bind_parameter() for pyqtgraph Parameters\n"
            "• Use bind_properties() for regular Qt widgets\n"
            "• Change values in any tab → parameter tree updates\n"
            "• Change values in tree → all tabs update\n"
            "• No manual signal connections needed!"
        )
        desc.setStyleSheet("font-family: monospace; padding: 10px;")
        layout.addWidget(desc)

        # Create tab widget for different control groups
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create parameters
        self.params = [
            {'title': 'Processing:', 'name': 'processing', 'type': 'group', 'children': [
                {'title': 'Algorithm:', 'name': 'algorithm', 'type': 'list',
                 'limits': self.algorithms, 'value': 'FFT'},
                {'title': 'Buffer Size:', 'name': 'buffer_size', 'type': 'int',
                 'value': 1024, 'limits': (128, 8192), 'step': 128},
                {'title': 'Threshold:', 'name': 'threshold', 'type': 'float',
                 'value': 0.5, 'limits': (0.0, 1.0), 'step': 0.1},
                {'title': 'Auto Process:', 'name': 'auto_process', 'type': 'bool',
                 'value': True},
            ]},
            {'title': 'Acquisition:', 'name': 'acquisition', 'type': 'group', 'children': [
                {'title': 'Mode:', 'name': 'mode', 'type': 'list',
                 'limits': self.modes, 'value': 'Continuous'},
                {'title': 'Samples:', 'name': 'samples', 'type': 'int',
                 'value': 100, 'limits': (10, 10000)},
                {'title': 'Averaging:', 'name': 'averaging', 'type': 'int',
                 'value': 1, 'limits': (1, 100)},
                {'title': 'Enable Trigger:', 'name': 'enable_trigger', 'type': 'bool',
                 'value': False},
            ]},
            {'title': 'Position:', 'name': 'position', 'type': 'group', 'children': [
                {'title': 'Units:', 'name': 'units', 'type': 'list',
                 'limits': self.units, 'value': 'mm'},
                {'title': 'Target:', 'name': 'target', 'type': 'float',
                 'value': 10.0, 'limits': (0.0, 100.0), 'step': 0.1},
                {'title': 'Speed:', 'name': 'speed', 'type': 'float',
                 'value': 1.0, 'limits': (0.1, 10.0), 'step': 0.1},
                {'title': 'Label:', 'name': 'label', 'type': 'str',
                 'value': 'Position 1'},
            ]},
        ]

        self.settings = Parameter.create(name='settings', type='group',
                                        children=self.params, showTop=False)

        # Create tab pages with widgets
        self.create_processing_tab()
        self.create_acquisition_tab()
        self.create_position_tab()

        # Create parameter tree in dock
        self.settings_dock = QDockWidget("Full Parameter Tree", self)
        self.tree = ParameterTree()
        self.tree.setParameters(self.settings, showTop=False)
        self.settings_dock.setWidget(self.tree)
        self.addDockWidget(Qt.RightDockWidgetArea, self.settings_dock)

        # Status display
        status_group = QGroupBox("Synchronization Status")
        status_layout = QVBoxLayout(status_group)
        self.status_label = QLabel()
        self.status_label.setStyleSheet("padding: 10px; font-family: monospace;")
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_group)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ✅ SETUP SYNCHRONIZATION
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        # Create DictSync with initial parameter values
        self.sync = WidgetSync(initial_value={
            # Processing
            'algorithms': self.algorithms,
            'algorithm': 'FFT',
            'buffer_size': 1024,
            'threshold': 0.5,
            'auto_process': True,
            # Acquisition
            'modes': self.modes,
            'mode': 'Continuous',
            'samples': 100,
            'averaging': 1,
            'enable_trigger': False,
            # Position
            'units_list': self.units,
            'units': 'mm',
            'target': 10.0,
            'speed': 1.0,
            'label': 'Position 1',
        })

        # Bind all widgets and parameters
        self.bind_processing()
        self.bind_acquisition()
        self.bind_position()

        # Update status when sync changes
        self.sync.value_changed.connect(self.update_status)
        self.update_status(self.sync.value)

    def create_processing_tab(self):
        """Create Processing tab with widgets"""
        tab = QWidget()
        layout = QFormLayout(tab)

        # Algorithm combo
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(self.algorithms)
        self.algorithm_combo.setCurrentText('FFT')
        layout.addRow("Algorithm:", self.algorithm_combo)

        # Buffer size spinner
        self.buffer_spin = QSpinBox()
        self.buffer_spin.setRange(128, 8192)
        self.buffer_spin.setSingleStep(128)
        self.buffer_spin.setValue(1024)
        self.buffer_spin.setSuffix(" samples")
        layout.addRow("Buffer Size:", self.buffer_spin)

        # Threshold spinner
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.0, 1.0)
        self.threshold_spin.setSingleStep(0.1)
        self.threshold_spin.setValue(0.5)
        self.threshold_spin.setDecimals(2)
        layout.addRow("Threshold:", self.threshold_spin)

        # Auto process checkbox
        self.auto_check = QCheckBox()
        self.auto_check.setChecked(True)
        layout.addRow("Auto Process:", self.auto_check)

        # Test button
        test_btn = QPushButton("Set Test Values")
        test_btn.clicked.connect(self.set_test_values)
        layout.addRow("", test_btn)

        self.tabs.addTab(tab, "Processing")

    def create_acquisition_tab(self):
        """Create Acquisition tab with widgets"""
        tab = QWidget()
        layout = QFormLayout(tab)

        # Mode combo
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(self.modes)
        self.mode_combo.setCurrentText('Continuous')
        layout.addRow("Mode:", self.mode_combo)

        # Samples spinner
        self.samples_spin = QSpinBox()
        self.samples_spin.setRange(10, 10000)
        self.samples_spin.setValue(100)
        layout.addRow("Samples:", self.samples_spin)

        # Averaging spinner
        self.averaging_spin = QSpinBox()
        self.averaging_spin.setRange(1, 100)
        self.averaging_spin.setValue(1)
        layout.addRow("Averaging:", self.averaging_spin)

        # Enable trigger checkbox
        self.trigger_check = QCheckBox()
        self.trigger_check.setChecked(False)
        layout.addRow("Enable Trigger:", self.trigger_check)

        self.tabs.addTab(tab, "Acquisition")

    def create_position_tab(self):
        """Create Position tab with widgets"""
        tab = QWidget()
        layout = QFormLayout(tab)

        # Units combo
        self.units_combo = QComboBox()
        self.units_combo.addItems(self.units)
        self.units_combo.setCurrentText('mm')
        layout.addRow("Units:", self.units_combo)

        # Target spinner
        self.target_spin = QDoubleSpinBox()
        self.target_spin.setRange(0.0, 100.0)
        self.target_spin.setSingleStep(0.1)
        self.target_spin.setValue(10.0)
        self.target_spin.setDecimals(1)
        layout.addRow("Target:", self.target_spin)

        # Speed spinner
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.1, 10.0)
        self.speed_spin.setSingleStep(0.1)
        self.speed_spin.setValue(1.0)
        self.speed_spin.setDecimals(1)
        layout.addRow("Speed:", self.speed_spin)

        # Label edit
        self.label_edit = QLineEdit()
        self.label_edit.setText('Position 1')
        layout.addRow("Label:", self.label_edit)

        self.tabs.addTab(tab, "Position")

    def bind_processing(self):
        """Bind Processing tab widgets and parameters"""
        processing_group = self.settings.child('processing')

        # Bind widgets (regular Qt widgets - use bind_properties)
        self.sync.bind_properties(
            self.algorithm_combo,
            property_map={
                'algorithms': {
                    'signal': None,
                    'getter': lambda: [self.algorithm_combo.itemText(i)
                                      for i in range(self.algorithm_combo.count())],
                    'setter': lambda items: (self.algorithm_combo.clear(),
                                            self.algorithm_combo.addItems(items)),
                    'mode': SyncMode.FROM_SYNC,
                },
                'algorithm': {
                    'signal': self.algorithm_combo.currentTextChanged,
                    'getter': lambda: self.algorithm_combo.currentText(),
                    'setter': lambda text: self.algorithm_combo.setCurrentText(text),
                }
            }
        )

        self.sync.bind_properties(
            self.buffer_spin,
            property_map={'buffer_size': {'property': 'value'}}
        )

        self.sync.bind_properties(
            self.threshold_spin,
            property_map={'threshold': {'property': 'value'}}
        )

        self.sync.bind_properties(
            self.auto_check,
            property_map={'auto_process': {'property': 'checked'}}
        )

        # Bind parameters (use bind_parameter - NOT bind_properties!)
        self.sync.bind_parameter(
            processing_group.child('algorithm'),
            property_map={
                'algorithms': {
                    'getter': lambda: processing_group.child('algorithm').opts['limits'],
                    'setter': lambda limits: processing_group.child('algorithm').setLimits(limits),
                    'mode': SyncMode.FROM_SYNC,
                },
                'algorithm': {'param': processing_group.child('algorithm')}
            }
        )

        self.sync.bind_parameter(
            processing_group.child('buffer_size'),
            property_map={'buffer_size': {'param': processing_group.child('buffer_size')}}
        )

        self.sync.bind_parameter(
            processing_group.child('threshold'),
            property_map={'threshold': {'param': processing_group.child('threshold')}}
        )

        self.sync.bind_parameter(
            processing_group.child('auto_process'),
            property_map={'auto_process': {'param': processing_group.child('auto_process')}}
        )

    def bind_acquisition(self):
        """Bind Acquisition tab widgets and parameters"""
        acquisition_group = self.settings.child('acquisition')

        # Bind widgets
        self.sync.bind_properties(
            self.mode_combo,
            property_map={
                'modes': {
                    'signal': None,
                    'getter': lambda: [self.mode_combo.itemText(i)
                                      for i in range(self.mode_combo.count())],
                    'setter': lambda items: (self.mode_combo.clear(),
                                            self.mode_combo.addItems(items)),
                    'mode': SyncMode.FROM_SYNC,
                },
                'mode': {'property': 'currentText'}
            }
        )

        self.sync.bind_properties(self.samples_spin, property_map={'samples': {'property': 'value'}})
        self.sync.bind_properties(self.averaging_spin, property_map={'averaging': {'property': 'value'}})
        self.sync.bind_properties(self.trigger_check, property_map={'enable_trigger': {'property': 'checked'}})

        # Bind parameters
        self.sync.bind_parameter(
            acquisition_group.child('mode'),
            property_map={
                'modes': {
                    'getter': lambda: acquisition_group.child('mode').opts['limits'],
                    'setter': lambda limits: acquisition_group.child('mode').setLimits(limits),
                    'mode': SyncMode.FROM_SYNC,
                },
                'mode': {'param': acquisition_group.child('mode')}
            }
        )

        self.sync.bind_parameter(acquisition_group.child('samples'),
                                property_map={'samples': {'param': acquisition_group.child('samples')}})
        self.sync.bind_parameter(acquisition_group.child('averaging'),
                                property_map={'averaging': {'param': acquisition_group.child('averaging')}})
        self.sync.bind_parameter(acquisition_group.child('enable_trigger'),
                                property_map={'enable_trigger': {'param': acquisition_group.child('enable_trigger')}})

    def bind_position(self):
        """Bind Position tab widgets and parameters"""
        position_group = self.settings.child('position')

        # Bind widgets
        self.sync.bind_properties(
            self.units_combo,
            property_map={
                'units_list': {
                    'signal': None,
                    'getter': lambda: [self.units_combo.itemText(i)
                                      for i in range(self.units_combo.count())],
                    'setter': lambda items: (self.units_combo.clear(),
                                            self.units_combo.addItems(items)),
                    'mode': SyncMode.FROM_SYNC,
                },
                'units': {'property': 'currentText'}
            }
        )

        self.sync.bind_properties(self.target_spin, property_map={'target': {'property': 'value'}})
        self.sync.bind_properties(self.speed_spin, property_map={'speed': {'property': 'value'}})
        self.sync.bind_properties(self.label_edit, property_map={'label': {'property': 'text'}})

        # Bind parameters
        self.sync.bind_parameter(
            position_group.child('units'),
            property_map={
                'units_list': {
                    'getter': lambda: position_group.child('units').opts['limits'],
                    'setter': lambda limits: position_group.child('units').setLimits(limits),
                    'mode': SyncMode.FROM_SYNC,
                },
                'units': {'param': position_group.child('units')}
            }
        )

        self.sync.bind_parameter(position_group.child('target'),
                                property_map={'target': {'param': position_group.child('target')}})
        self.sync.bind_parameter(position_group.child('speed'),
                                property_map={'speed': {'param': position_group.child('speed')}})
        self.sync.bind_parameter(position_group.child('label'),
                                property_map={'label': {'param': position_group.child('label')}})

    def set_test_values(self):
        """Programmatically change values to test synchronization"""
        self.sync.value = {
            # Processing
            'algorithms': self.algorithms,
            'algorithm': 'Wavelet',
            'buffer_size': 2048,
            'threshold': 0.8,
            'auto_process': False,
            # Acquisition
            'modes': self.modes,
            'mode': 'Triggered',
            'samples': 500,
            'averaging': 5,
            'enable_trigger': True,
            # Position
            'units_list': self.units,
            'units': 'µm',
            'target': 50.0,
            'speed': 5.0,
            'label': 'Test Position',
        }

    def update_status(self, value_dict):
        """Update status display"""
        status_text = f"""
Sync State:
  Processing:
    Algorithm:    {value_dict.get('algorithm', 'N/A')}
    Buffer Size:  {value_dict.get('buffer_size', 'N/A')}
    Threshold:    {value_dict.get('threshold', 'N/A')}
    Auto Process: {value_dict.get('auto_process', 'N/A')}

  Acquisition:
    Mode:          {value_dict.get('mode', 'N/A')}
    Samples:       {value_dict.get('samples', 'N/A')}
    Averaging:     {value_dict.get('averaging', 'N/A')}
    Enable Trigger:{value_dict.get('enable_trigger', 'N/A')}

  Position:
    Units:   {value_dict.get('units', 'N/A')}
    Target:  {value_dict.get('target', 'N/A')}
    Speed:   {value_dict.get('speed', 'N/A')}
    Label:   {value_dict.get('label', 'N/A')}

✅ All synchronized across tabs and parameter tree!
        """
        self.status_label.setText(status_text.strip())


def main():
    """Run the example"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = ParameterBindingExample()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

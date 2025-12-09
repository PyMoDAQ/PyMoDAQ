"""
ComboBox Synchronization Examples - Items and Selection

Demonstrates different approaches to synchronizing both the dropdown items
and the current selection across multiple QComboBoxes.

Run this example:
    python -m pymodaq_gui.examples.combobox_sync_example
"""
import sys
from qtpy.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QComboBox, QPushButton, QLabel, QGroupBox, QTabWidget,
                             QLineEdit)
from qtpy.QtCore import Qt

from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode


class TwoSyncsExample(QWidget):
    """Example using two separate syncs: one for items, one for selection"""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Info
        info = QLabel(
            "Two Separate Syncs Approach:\n"
            "✓ One sync for the items list (FROM_SYNC mode)\n"
            "✓ One sync for the current selection (BIDIRECTIONAL)\n"
            "✓ Good when items change independently from selection"
        )
        info.setStyleSheet("padding: 10px; background-color: #e3f2fd; border-radius: 5px;")
        layout.addWidget(info)

        # ComboBoxes
        combos_group = QGroupBox("Synchronized ComboBoxes")
        combos_layout = QHBoxLayout()

        self.combo1 = QComboBox()
        self.combo2 = QComboBox()
        self.combo3 = QComboBox()

        combos_layout.addWidget(QLabel("Combo 1:"))
        combos_layout.addWidget(self.combo1)
        combos_layout.addWidget(QLabel("Combo 2:"))
        combos_layout.addWidget(self.combo2)
        combos_layout.addWidget(QLabel("Combo 3:"))
        combos_layout.addWidget(self.combo3)

        combos_group.setLayout(combos_layout)
        layout.addWidget(combos_group)

        # Initialize syncs
        initial_items = ["Red", "Green", "Blue", "Yellow"]

        # Sync 1: Items list (programmatic control only)
        self.items_sync = WidgetSync(initial_value=initial_items)

        for combo in [self.combo1, self.combo2, self.combo3]:
            self.items_sync.bind(
                combo,
                setter=lambda items, c=combo: self._set_combo_items(c, items),
                mode=SyncMode.FROM_SYNC
            )

        # Sync 2: Current selection
        self.selection_sync = WidgetSync.for_combobox(
            self.combo1,
            initial="Red",
            use_text=True
        )
        self.selection_sync.add(self.combo2, match='property')
        self.selection_sync.add(self.combo3, match='property')

        # Controls
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()

        # Change items
        items_row = QHBoxLayout()
        items_row.addWidget(QLabel("New items (comma-separated):"))
        self.items_input = QLineEdit()
        self.items_input.setPlaceholderText("e.g., Apple, Banana, Orange")
        items_row.addWidget(self.items_input)
        change_items_btn = QPushButton("Change Items")
        change_items_btn.clicked.connect(self.change_items)
        items_row.addWidget(change_items_btn)
        controls_layout.addLayout(items_row)

        # Preset buttons
        presets_row = QHBoxLayout()
        presets_row.addWidget(QLabel("Presets:"))

        colors_btn = QPushButton("Colors")
        colors_btn.clicked.connect(lambda: setattr(self.items_sync, 'value', ["Red", "Green", "Blue", "Yellow"]))
        presets_row.addWidget(colors_btn)

        fruits_btn = QPushButton("Fruits")
        fruits_btn.clicked.connect(lambda: setattr(self.items_sync, 'value', ["Apple", "Banana", "Orange", "Grape"]))
        presets_row.addWidget(fruits_btn)

        numbers_btn = QPushButton("Numbers")
        numbers_btn.clicked.connect(lambda: setattr(self.items_sync, 'value', ["One", "Two", "Three", "Four"]))
        presets_row.addWidget(numbers_btn)

        controls_layout.addLayout(presets_row)

        # Status
        self.status_label = QLabel()
        self.update_status()
        controls_layout.addWidget(self.status_label)

        # Connect selection changes to update status
        self.selection_sync.value_changed.connect(lambda _: self.update_status())

        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        layout.addStretch()

    def _set_combo_items(self, combo, items):
        """Set combo items while preserving selection if possible"""
        current = combo.currentText()
        # combo.blockSignals(True)
        combo.clear()
        combo.addItems(items)

        # Restore selection if still valid
        index = combo.findText(current)
        if index >= 0:
            combo.setCurrentIndex(index)
        elif items and hasattr(self, 'selection_sync'):
            # Update to first item if previous selection no longer exists
            self.selection_sync.value = items[0]

        # combo.blockSignals(False)

    def change_items(self):
        """Change items from user input"""
        text = self.items_input.text().strip()
        if text:
            items = [item.strip() for item in text.split(',') if item.strip()]
            if items:
                self.items_sync.value = items
                self.items_input.clear()

    def update_status(self):
        """Update status display"""
        items = self.items_sync.value
        selection = self.selection_sync.value
        self.status_label.setText(
            f"Items: {items}\n"
            f"Current selection: {selection}"
        )


class CompositeStateExample(QWidget):
    """Example using a single sync with composite state (dict)"""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Info
        info = QLabel(
            "Composite State Approach:\n"
            "✓ Single sync with dict containing both items and selection\n"
            "✓ Items and selection always change together\n"
            "✓ Good for scenarios where state is atomic"
        )
        info.setStyleSheet("padding: 10px; background-color: #f3e5f5; border-radius: 5px;")
        layout.addWidget(info)

        # ComboBoxes
        combos_group = QGroupBox("Synchronized ComboBoxes")
        combos_layout = QHBoxLayout()

        self.combo1 = QComboBox()
        self.combo2 = QComboBox()
        self.combo3 = QComboBox()

        combos_layout.addWidget(QLabel("Combo 1:"))
        combos_layout.addWidget(self.combo1)
        combos_layout.addWidget(QLabel("Combo 2:"))
        combos_layout.addWidget(self.combo2)
        combos_layout.addWidget(QLabel("Combo 3:"))
        combos_layout.addWidget(self.combo3)

        combos_group.setLayout(combos_layout)
        layout.addWidget(combos_group)

        # Create composite sync
        initial_state = {
            'items': ["Cat", "Dog", "Bird", "Fish"],
            'current': "Cat"
        }
        self.combo_sync = WidgetSync(initial_value=initial_state)

        # Bind all combos
        for combo in [self.combo1, self.combo2, self.combo3]:
            self.combo_sync.bind(
                combo,
                signal=combo.currentTextChanged,
                getter=lambda c=combo: self._get_combo_state(c),
                setter=lambda state, c=combo: self._set_combo_state(c, state),
                to_sync_transform=lambda _text, c=combo: self._get_combo_state(c)
            )

        # Controls
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()

        # Preset scenarios
        presets_row = QHBoxLayout()
        presets_row.addWidget(QLabel("Load Scenario:"))

        animals_btn = QPushButton("Animals")
        animals_btn.clicked.connect(lambda: setattr(self.combo_sync, 'value', {
            'items': ["Cat", "Dog", "Bird", "Fish"],
            'current': "Dog"
        }))
        presets_row.addWidget(animals_btn)

        shapes_btn = QPushButton("Shapes")
        shapes_btn.clicked.connect(lambda: setattr(self.combo_sync, 'value', {
            'items': ["Circle", "Square", "Triangle"],
            'current': "Circle"
        }))
        presets_row.addWidget(shapes_btn)

        sizes_btn = QPushButton("Sizes")
        sizes_btn.clicked.connect(lambda: setattr(self.combo_sync, 'value', {
            'items': ["Small", "Medium", "Large", "XLarge"],
            'current': "Medium"
        }))
        presets_row.addWidget(sizes_btn)

        controls_layout.addLayout(presets_row)

        # Status
        self.status_label = QLabel()
        self.update_status()
        self.combo_sync.value_changed.connect(lambda _: self.update_status())
        controls_layout.addWidget(self.status_label)

        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        layout.addStretch()

    def _get_combo_state(self, combo):
        """Get complete combo state"""
        return {
            'items': [combo.itemText(i) for i in range(combo.count())],
            'current': combo.currentText()
        }

    def _set_combo_state(self, combo, state):
        """Set complete combo state"""
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(state['items'])
        index = combo.findText(state['current'])
        if index >= 0:
            combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def update_status(self):
        """Update status display"""
        state = self.combo_sync.value
        self.status_label.setText(
            f"Items: {state['items']}\n"
            f"Current selection: {state['current']}"
        )


class PracticalExample(QWidget):
    """Practical example: sync selection, update items programmatically"""

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Info
        info = QLabel(
            "Practical Approach:\n"
            "✓ Use factory for selection sync\n"
            "✓ Update items programmatically via helper method\n"
            "✓ Most common real-world scenario"
        )
        info.setStyleSheet("padding: 10px; background-color: #e8f5e9; border-radius: 5px;")
        layout.addWidget(info)

        # ComboBoxes
        combos_group = QGroupBox("Synchronized ComboBoxes")
        combos_layout = QHBoxLayout()

        self.combo1 = QComboBox()
        self.combo2 = QComboBox()
        self.combo3 = QComboBox()
        self.combos = [self.combo1, self.combo2, self.combo3]

        # Initialize with same items
        initial_items = ["Morning", "Afternoon", "Evening", "Night"]
        for combo in self.combos:
            combo.addItems(initial_items)

        combos_layout.addWidget(QLabel("Combo 1:"))
        combos_layout.addWidget(self.combo1)
        combos_layout.addWidget(QLabel("Combo 2:"))
        combos_layout.addWidget(self.combo2)
        combos_layout.addWidget(QLabel("Combo 3:"))
        combos_layout.addWidget(self.combo3)

        combos_group.setLayout(combos_layout)
        layout.addWidget(combos_group)

        # Sync only the selection
        self.selection_sync = WidgetSync.for_combobox(
            self.combo1,
            initial="Morning",
            use_text=True
        )
        self.selection_sync.add(self.combo2, match='property')
        self.selection_sync.add(self.combo3, match='property')

        # Controls
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()

        # Change items
        presets_row = QHBoxLayout()
        presets_row.addWidget(QLabel("Change items to:"))

        times_btn = QPushButton("Times of Day")
        times_btn.clicked.connect(
            lambda: self.update_combo_items(["Morning", "Afternoon", "Evening", "Night"])
        )
        presets_row.addWidget(times_btn)

        seasons_btn = QPushButton("Seasons")
        seasons_btn.clicked.connect(
            lambda: self.update_combo_items(["Spring", "Summer", "Autumn", "Winter"])
        )
        presets_row.addWidget(seasons_btn)

        weekdays_btn = QPushButton("Weekdays")
        weekdays_btn.clicked.connect(
            lambda: self.update_combo_items(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        )
        presets_row.addWidget(weekdays_btn)

        controls_layout.addLayout(presets_row)

        # Status
        self.status_label = QLabel()
        self.update_status()
        self.selection_sync.value_changed.connect(lambda _: self.update_status())
        controls_layout.addWidget(self.status_label)

        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        layout.addStretch()

    def update_combo_items(self, new_items):
        """Update items in all synced comboboxes"""
        current = self.selection_sync.value  # Remember current selection

        # Update items in all combos
        for combo in self.combos:
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(new_items)
            combo.blockSignals(False)

        # Restore selection if still valid, otherwise select first item
        if current in new_items:
            self.selection_sync.value = current
        elif new_items:
            self.selection_sync.value = new_items[0]

    def update_status(self):
        """Update status display"""
        items = [self.combo1.itemText(i) for i in range(self.combo1.count())]
        selection = self.selection_sync.value
        self.status_label.setText(
            f"Items: {items}\n"
            f"Current selection: {selection}"
        )


class ComboBoxSyncDemo(QWidget):
    """Main window with tabs for different approaches"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ComboBox Synchronization: Items + Selection")
        self.setMinimumSize(800, 400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(
            "ComboBox Synchronization Examples\n"
            "Three different approaches to sync both items and selection"
        )
        header.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(header)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(PracticalExample(), "1. Practical (Recommended)")
        tabs.addTab(TwoSyncsExample(), "2. Two Syncs")
        tabs.addTab(CompositeStateExample(), "3. Composite State")

        layout.addWidget(tabs)


def main():
    app = QApplication(sys.argv)
    window = ComboBoxSyncDemo()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

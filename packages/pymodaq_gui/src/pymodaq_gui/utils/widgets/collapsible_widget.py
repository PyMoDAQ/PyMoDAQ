from qtpy.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
    QLineEdit,
)
from qtpy.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal
import sys

symbol_pairs = [
    ("▲", "▼"),
    ("◀", "▶"),
    ("◄", "►"),
    ("↑", "↓"),
    ("→", "←"),
    ("⬆", "⬇"),
    ("⬅", "➡"),
]
symbol_map = {}
for sym1, sym2 in symbol_pairs:
    symbol_map[sym1] = sym2
    symbol_map[sym2] = sym1

class CollapsibleWidget(QWidget):

    toggled_signal = Signal(bool)  # Emits True when expanded, False when collapsed

    def __init__(
        self,
        toggle_widget,
        collapsible_widget,
        direction="top",
        content_before_toggle=True,
        animation_duration=300,
        parent=None,
    ):
        """
        Create a collapsible widget container with multiple direction support.

        Args:
            toggle_widget: Widget that is always displayed (the button/trigger)
            collapsible_widget: Widget that will be shown/hidden when toggling
            direction: Direction where content appears ('top', 'bottom', 'left', 'right')
            content_before_toggle: If True, content appears before toggle widget in layout
            animation_duration: Duration of the animation in milliseconds
            parent: Parent widget
        """
        super().__init__(parent)
        self.toggle_widget = toggle_widget
        self.collapsible_widget = collapsible_widget
        self.direction = direction.lower()
        self.content_before_toggle = content_before_toggle
        self.animation_duration = animation_duration
        self.is_expanded = False

        # Store original text if toggle_widget is a button for symbol flipping
        self.original_text = None
        if isinstance(self.toggle_widget, QPushButton):
            self.original_text = self.toggle_widget.text()

        self.init_ui()
        self.connect_signals()

    def connect_signals(self):
        self.toggled_signal.connect(self._update_toggle_symbol)

    def init_ui(self):
        # Wrap collapsible widget in a container for animation
        self.collapsible_container = QFrame()
        self.collapsible_container.setFrameShape(QFrame.Shape.NoFrame)
        # self.collapsible_container.setStyleSheet("background: transparent;")
        container_layout = QVBoxLayout(self.collapsible_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.collapsible_widget)

        # Set initial collapsed state based on direction
        if self.direction in ["top", "bottom"]:
            self.collapsible_container.setMaximumHeight(0)
            self.collapsible_container.setMinimumHeight(0)
            self.content_size = self.collapsible_container.sizeHint().height()
            self.animated_property = b"maximumHeight"
        else:  # left or right
            self.collapsible_container.setMaximumWidth(0)
            self.collapsible_container.setMinimumWidth(0)
            self.content_size = self.collapsible_container.sizeHint().width()
            self.animated_property = b"maximumWidth"

        # Connect toggle widget click to toggle function
        if hasattr(self.toggle_widget, "clicked"):
            self.toggle_widget.clicked.connect(self.toggle_content)

        # Create animation for smooth expand/collapse
        self.animation = QPropertyAnimation(
            self.collapsible_container, self.animated_property
        )
        self.animation.setDuration(self.animation_duration)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Arrange widgets based on direction and content_before_toggle
        if self.direction in ["top", "bottom"]:
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            if self.content_before_toggle:
                main_layout.addWidget(self.collapsible_container)
                main_layout.addWidget(self.toggle_widget)
            else:
                main_layout.addWidget(self.toggle_widget)
                main_layout.addWidget(self.collapsible_container)

        else:  # left or right
            main_layout = QHBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)

            if self.content_before_toggle:
                main_layout.addWidget(self.collapsible_container)
                main_layout.addWidget(self.toggle_widget)
            else:
                main_layout.addWidget(self.toggle_widget)
                main_layout.addWidget(self.collapsible_container)

    def toggle_content(self):
        """Toggle the visibility of the collapsible widget with animation"""
        if self.is_expanded:
            # Collapse animation
            self.animation.setStartValue(self.content_size)
            self.animation.setEndValue(0)
            self.is_expanded = False
        else:
            # Expand animation
            # Update content size in case it changed
            if self.direction in ["top", "bottom"]:
                self.content_size = self.collapsible_container.sizeHint().height()
            else:
                self.content_size = self.collapsible_container.sizeHint().width()

            self.animation.setStartValue(0)
            self.animation.setEndValue(self.content_size)
            self.is_expanded = True

        # Start the animation
        self.animation.start()
        
        self.toggled_signal.emit(self.is_expanded)

    def _update_toggle_symbol(self, expanded):
        """Update the toggle button symbol based on expanded state"""
        if not isinstance(self.toggle_widget, QPushButton) or not self.original_text:
            return
        text = self.original_text if not expanded else symbol_map[self.original_text]        
        self.toggle_widget.setText(text)
        
    def set_expanded(self, expanded):
        """Programmatically set the expanded state without animation"""
        if expanded and not self.is_expanded:
            if self.direction in ["top", "bottom"]:
                self.content_size = self.collapsible_container.sizeHint().height()
                self.collapsible_container.setMaximumHeight(self.content_size)
            else:
                self.content_size = self.collapsible_container.sizeHint().width()
                self.collapsible_container.setMaximumWidth(self.content_size)
            self.is_expanded = True
        elif not expanded and self.is_expanded:
            if self.direction in ["top", "bottom"]:
                self.collapsible_container.setMaximumHeight(0)
            else:
                self.collapsible_container.setMaximumWidth(0)
            self.is_expanded = False


# Demo application
if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("Collapsible Widget - All Directions Demo")
    window.setGeometry(100, 100, 800, 600)

    main_layout = QVBoxLayout(window)
    main_layout.addWidget(QLabel("<h3>Collapsible Widget - All Directions</h3>"))

    # Create a horizontal layout for left/right examples
    h_layout = QHBoxLayout()

    # LEFT direction example
    left_section = QWidget()
    left_layout = QVBoxLayout(left_section)
    left_layout.addWidget(QLabel("<b>LEFT Direction</b>"))

    toggle_left = QPushButton("◀")
    toggle_left.setFixedWidth(30)
    toggle_left.setStyleSheet("""
        QPushButton {
            background-color: #17a2b8;
            color: white;
            border: none;
            font-size: 16px;
        }
        QPushButton:hover {
            background-color: #138496;
        }
    """)

    content_left = QFrame()
    content_left.setStyleSheet("background-color: #d1ecf1; border: 2px solid #17a2b8;")
    content_left_layout = QVBoxLayout(content_left)
    content_left_layout.addWidget(QLabel("Left Panel"))
    content_left_layout.addWidget(QPushButton("Option 1"))
    content_left_layout.addWidget(QPushButton("Option 2"))

    collapsible_left = CollapsibleWidget(
        toggle_left, content_left, direction="left", content_before_toggle=True
    )
    left_layout.addWidget(collapsible_left)
    left_layout.addStretch()

    h_layout.addWidget(left_section)

    # RIGHT direction example
    right_section = QWidget()
    right_layout = QVBoxLayout(right_section)
    right_layout.addWidget(QLabel("<b>RIGHT Direction</b>"))

    toggle_right = QPushButton("▶")
    toggle_right.setFixedWidth(30)
    toggle_right.setStyleSheet("""
        QPushButton {
            background-color: #28a745;
            color: white;
            border: none;
            font-size: 16px;
        }
        QPushButton:hover {
            background-color: #218838;
        }
    """)

    content_right = QFrame()
    content_right.setStyleSheet("background-color: #d4edda; border: 2px solid #28a745;")
    content_right_layout = QVBoxLayout(content_right)
    content_right_layout.addWidget(QLabel("Right Panel"))
    content_right_layout.addWidget(QLineEdit("Setting 1"))
    content_right_layout.addWidget(QLineEdit("Setting 2"))

    collapsible_right = CollapsibleWidget(
        toggle_right, content_right, direction="right", content_before_toggle=False
    )
    right_layout.addWidget(collapsible_right)
    right_layout.addStretch()

    h_layout.addWidget(right_section)

    main_layout.addLayout(h_layout)

    # TOP direction example
    main_layout.addWidget(QLabel("<b>TOP Direction</b>"))

    toggle_top = QPushButton("▲")
    toggle_top.setStyleSheet("""
        QPushButton {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 8px;
        }
        QPushButton:hover {
            background-color: #0056b3;
        }
    """)

    content_top = QFrame()
    content_top.setStyleSheet("background-color: #cce5ff; border: 2px solid #007bff;")
    content_top_layout = QVBoxLayout(content_top)
    content_top_layout.addWidget(QLabel("Top Content Area"))
    content_top_layout.addWidget(QPushButton("Action Button"))

    collapsible_top = CollapsibleWidget(
        toggle_top, content_top, direction="top", content_before_toggle=True
    )
    main_layout.addWidget(collapsible_top)

    # BOTTOM direction example
    main_layout.addWidget(QLabel("<b>BOTTOM Direction</b>"))

    toggle_bottom = QPushButton("▼")
    toggle_bottom.setStyleSheet("""
        QPushButton {
            background-color: #ffc107;
            color: black;
            border: none;
            padding: 8px;
        }
        QPushButton:hover {
            background-color: #e0a800;
        }
    """)

    content_bottom = QFrame()
    content_bottom.setStyleSheet(
        "background-color: #fff3cd; border: 2px solid #ffc107;"
    )
    content_bottom_layout = QVBoxLayout(content_bottom)
    content_bottom_layout.addWidget(QLabel("Bottom Content Area"))
    content_bottom_layout.addWidget(QLabel("Additional Information"))

    collapsible_bottom = CollapsibleWidget(
        toggle_bottom, content_bottom, direction="bottom", content_before_toggle=False
    )
    main_layout.addWidget(collapsible_bottom)

    main_layout.addStretch()

    window.show()
    sys.exit(app.exec_())

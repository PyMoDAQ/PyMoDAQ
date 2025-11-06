from qtpy.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout
from qtpy.QtCore import Qt, QSize, QTimer, Signal
from qtpy.QtGui import QIcon, QPixmap, QPainter, QColor
import sys


class SearchLineEdit(QLineEdit):
    # New signal that fires only after debounce delay
    searchTextChanged = Signal(str)

    def __init__(self, parent=None, debounce_ms=300):
        super().__init__(parent)

        # Debounce timer
        self.debounce_ms = debounce_ms
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._emit_debounced_search)

        # Connect to the native textChanged signal
        self.textChanged.connect(self._on_text_changed)

        # Set placeholder text
        self.setPlaceholderText("Search...")

        # Create a simple search icon
        self.search_icon = self.create_search_icon()

        # Style the QLineEdit
        self.setStyleSheet("""
            QLineEdit {
                padding-left: 30px;
                padding-right: 10px;
                border: 1px solid #ccc;
                border-radius: 15px;
                background-color: #f5f5f5;
                min-height: 30px;
                font-size: 13px;
                color: #333;                           
            }
            QLineEdit:focus {
                border: 1px solid #4a90e2;
                background-color: white;
                color: #000;                           
            }
        """)

        # Set fixed width for small widget
        self.setFixedWidth(200)


    def _on_text_changed(self, text):
        """Called on every keystroke"""
        # Stop any pending search
        self.search_timer.stop()

        # If search is cleared, emit immediately for better UX
        if not text.strip():
            self.searchTextChanged.emit(text)
        else:
            # Otherwise, start debounce timer
            self.search_timer.start(self.debounce_ms)

    def _emit_debounced_search(self):
        """Emit the debounced signal"""
        self.searchTextChanged.emit(self.text())

    def create_search_icon(self):
        """Create a simple magnifying glass icon"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw magnifying glass
        pen = painter.pen()
        pen.setColor(QColor("#888"))
        pen.setWidth(2)
        painter.setPen(pen)

        # Circle
        painter.drawEllipse(2, 2, 9, 9)
        # Handle
        painter.drawLine(10, 10, 14, 14)

        painter.end()
        return QIcon(pixmap)

    def paintEvent(self, event):
        super().paintEvent(event)

        # Draw the search icon
        painter = QPainter(self)
        icon_size = QSize(16, 16)
        icon_rect = self.search_icon.pixmap(icon_size).rect()
        icon_rect.moveCenter(self.rect().center())
        icon_rect.moveLeft(8)

        self.search_icon.paint(painter, icon_rect)


# Demo application
class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Search Widget Demo")
        self.setGeometry(100, 100, 300, 150)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # Create search widget
        self.search = SearchLineEdit(debounce_ms=300)

        # Connect to DEBOUNCED signal (not textChanged)
        self.search.searchTextChanged.connect(self.on_search_changed)

        # You can still access immediate changes if needed:
        # self.search.textChanged.connect(self.on_immediate_change)

        layout.addWidget(self.search)
        layout.addStretch()

        self.setLayout(layout)

    def on_search_changed(self, text):
        print(f"Debounced search: '{text}'")
        # This is where you'd call filter_parameter_tree()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    sys.exit(app.exec())

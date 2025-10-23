"""
PatternCompleter Examples - PyQt6 Auto-completion System

This demonstrates various use cases for the PatternCompleter mixin class.
All examples are accessible through tabs in a single window.
"""

from qtpy.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QHBoxLayout,
    QPushButton,
)
from qtpy.QtCore import QTimer
from pymodaq_gui.utils.widgets.pattern_completer import (
    PatternLineEdit,
    PatternTextEdit,
    PatternPlainTextEdit,
    PatternCompleterDelegate,
)
import sys


# ============================================================================
# EXAMPLE 1: Basic Usage with QLineEdit
# ============================================================================
def create_basic_example():
    """Simple mention system with @ trigger"""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    layout.addWidget(QLabel("<b>Example 1: Basic Usage</b>"))
    layout.addWidget(QLabel("Type @ to mention someone"))

    # Create a line edit with pattern completion
    line_edit = PatternLineEdit()

    # Add @ mentions completer
    users = ["Alice Johnson", "Bob Smith", "Charlie Brown", "Diana Prince"]
    line_edit.add_completer("@", users)

    line_edit.setPlaceholderText("Type @ to mention someone...")
    layout.addWidget(line_edit)
    layout.addStretch()

    return widget


# ============================================================================
# EXAMPLE 2: Multiple Patterns
# ============================================================================
def create_multiple_patterns_example():
    """Text editor with multiple completion triggers"""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    layout.addWidget(QLabel("<b>Example 2: Multiple Patterns</b>"))
    layout.addWidget(QLabel("Try typing @ for mentions, # for hashtags, :: for emojis"))

    text_edit = PatternTextEdit()

    # @ for user mentions
    users = ["Alice", "Bob", "Charlie", "Diana"]
    text_edit.add_completer("@", users)

    # # for hashtags
    tags = ["python", "pyqt6", "programming", "development", "tutorial"]
    text_edit.add_completer("#", tags)

    # :: for emojis
    emojis = ["smile 😊", "heart ❤️", "thumbsup 👍", "fire 🔥", "rocket 🚀"]
    text_edit.add_completer("::", emojis)

    text_edit.setPlaceholderText(
        "Try typing:\n  @ for mentions\n  # for hashtags\n  :: for emojis"
    )
    layout.addWidget(text_edit)

    return widget


# ============================================================================
# EXAMPLE 3: Global Configuration
# ============================================================================
def create_global_config_example():
    """Configure appearance and behavior globally"""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    layout.addWidget(QLabel("<b>Example 3: Global Configuration</b>"))
    layout.addWidget(
        QLabel("Notice the green border when typing @ (visual indicator enabled)")
    )

    # Initialize with global settings
    line_edit = PatternLineEdit(
        min_width=200,  # Minimum popup width
        max_width=600,  # Maximum popup width
        visual_indicator=True,  # Show green border when active
        case_sensitive=False,  # Case-insensitive by default
        auto_resize=True,  # Auto-resize popup to fit content
        word_wrap=False,  # Don't wrap long items
    )

    countries = ["United States", "United Kingdom", "Canada", "Australia", "Germany"]
    line_edit.add_completer("@", countries)

    line_edit.setPlaceholderText("Type @ - notice the green border!")
    layout.addWidget(line_edit)
    layout.addStretch()

    return widget


# ============================================================================
# EXAMPLE 4: Per-Pattern Configuration
# ============================================================================
def create_per_pattern_config_example():
    """Different settings for each pattern"""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    layout.addWidget(QLabel("<b>Example 4: Per-Pattern Configuration</b>"))
    layout.addWidget(QLabel("@ is case-insensitive, :: is case-sensitive"))

    text_edit = PatternTextEdit()

    # Case-insensitive user mentions with visual indicator
    users = ["Alice", "Bob", "Charlie"]
    text_edit.add_completer("@", users, visual_indicator=True, case_sensitive=False)

    # Case-sensitive programming keywords
    keywords = ["def", "class", "import", "return", "if", "else"]
    text_edit.add_completer(
        "::",
        keywords,
        case_sensitive=True,  # Exact case matching
        min_width=150,
        max_width=300,
    )

    text_edit.setPlaceholderText(
        "@ mentions are case-insensitive (try '@ali' or '@ALI')\n"
        ":: keywords are case-sensitive (try '::def' vs '::DEF')"
    )
    layout.addWidget(text_edit)

    return widget


# ============================================================================
# EXAMPLE 5: Word Wrap Example
# ============================================================================
def create_word_wrap_example():
    """
    Demonstrates word wrap feature for long completion items
    """
    widget = QWidget()
    layout = QVBoxLayout(widget)

    layout.addWidget(QLabel("<b>Example 5: Word Wrap</b>"))

    info_label = QLabel(
        "<b>What is Word Wrap?</b><br>"
        "• <b>word_wrap=False</b> (default): Long items are truncated or need scrolling<br>"
        "• <b>word_wrap=True</b>: Long items wrap to multiple lines in popup<br><br>"
        "Click buttons below to toggle word wrap and see the difference!"
    )
    layout.addWidget(info_label)

    # Button controls
    button_layout = QHBoxLayout()
    btn_no_wrap = QPushButton("Without Word Wrap")
    btn_with_wrap = QPushButton("With Word Wrap")
    button_layout.addWidget(btn_no_wrap)
    button_layout.addWidget(btn_with_wrap)
    layout.addLayout(button_layout)

    line_edit = PatternLineEdit()

    # Long completion items that benefit from word wrap
    long_items = [
        "Alice Johnson - Senior Developer at Tech Corp",
        "Bob Smith - Product Manager with 10 years experience",
        "Charlie Brown - UX Designer specializing in mobile applications",
        "Diana Prince - Data Scientist working on machine learning projects",
    ]

    # Start without word wrap
    line_edit.add_completer("@", long_items, word_wrap=False, max_width=300)

    def set_no_wrap():
        line_edit.update_completer_config("@", word_wrap=False)
        line_edit.setPlaceholderText("Type @ - items are truncated (word_wrap=False)")

    def set_with_wrap():
        line_edit.update_completer_config("@", word_wrap=True)
        line_edit.setPlaceholderText(
            "Type @ - items wrap to multiple lines (word_wrap=True)"
        )

    btn_no_wrap.clicked.connect(set_no_wrap)
    btn_with_wrap.clicked.connect(set_with_wrap)

    line_edit.setPlaceholderText("Type @ - items are truncated (word_wrap=False)")
    layout.addWidget(line_edit)
    layout.addStretch()

    return widget


# ============================================================================
# EXAMPLE 6: Dynamic Updates
# ============================================================================
def create_dynamic_updates_example():
    """Update completions dynamically"""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    layout.addWidget(QLabel("<b>Example 6: Dynamic Updates</b>"))
    counter_label = QLabel("Completions update every 2 seconds!")
    layout.addWidget(counter_label)

    text_edit = PatternTextEdit()
    text_edit.add_completer("@", ["Alice", "Bob"])
    text_edit.setPlaceholderText("Type @ to see completions. Watch them change!")
    layout.addWidget(text_edit)

    # Simulate dynamic updates
    counter = [0]

    def update_users():
        counter[0] += 1
        new_users = [f"User{i}" for i in range(counter[0], counter[0] + 5)]
        text_edit.update_completions("@", new_users)
        counter_label.setText(f"Update #{counter[0]}: {', '.join(new_users)}")

    timer = QTimer(widget)
    timer.timeout.connect(update_users)
    timer.start(2000)

    return widget


# ============================================================================
# EXAMPLE 7: Table Widget with Delegate
# ============================================================================
def create_table_delegate_example():
    """Use PatternCompleter in table cells"""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    layout.addWidget(QLabel("<b>Example 7: Table Delegate</b>"))
    layout.addWidget(QLabel("Double-click cells and type @ for users or # for tags"))

    table = QTableWidget(5, 2)
    table.setHorizontalHeaderLabels(["Assigned To", "Tags"])

    # Create delegate with pattern completion
    delegate = PatternCompleterDelegate(min_width=200, visual_indicator=True)
    # Add completers for the delegate
    users = ["Alice", "Bob", "Charlie", "Diana"]
    tags = ["urgent", "review", "bug", "feature", "documentation"]
    delegate.add_completer("@", users)
    delegate.add_completer("#", tags)

    # Apply delegate to both columns
    table.setItemDelegateForColumn(0, delegate)
    table.setItemDelegateForColumn(1, delegate)
    # It is possible to use different delegates for each column but one has to keep the instance alive (with self. ...)

    # Add some sample data
    for i in range(5):
        table.setItem(i, 0, QTableWidgetItem(f"Task {i + 1}"))
        table.setItem(i, 1, QTableWidgetItem(""))

    layout.addWidget(table)

    return widget


# ============================================================================
# EXAMPLE 8: Code Editor Style
# ============================================================================
def create_code_editor_example():
    """IDE-like code completion"""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    layout.addWidget(QLabel("<b>Example 8: Code Editor Style</b>"))
    layout.addWidget(QLabel("Python-style completion: :keyword or ::builtin"))

    editor = PatternPlainTextEdit(
        min_width=250, max_width=500, case_sensitive=True, auto_resize=True
    )

    # Python keywords
    keywords = [
        "def",
        "class",
        "import",
        "from",
        "return",
        "if",
        "else",
        "elif",
        "for",
        "while",
        "try",
        "except",
        "with",
        "as",
        "pass",
        "break",
    ]

    # Built-in functions
    builtins = [
        "print()",
        "len()",
        "range()",
        "enumerate()",
        "zip()",
        "map()",
        "filter()",
        "sorted()",
        "sum()",
        "max()",
        "min()",
    ]

    editor.add_completer(":", keywords, case_sensitive=True)
    editor.add_completer("::", builtins)

    editor.setPlaceholderText(
        "Python-style completion:\n"
        "  :def → keywords\n"
        "  ::print → built-in functions\n\n"
        "Try typing ':for' or '::pri'"
    )

    layout.addWidget(editor)

    return widget


# ============================================================================
# Main Application with Tabs
# ============================================================================
class PatternCompleterDemo(QMainWindow):
    """Main demo window with all examples in tabs"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PatternCompleter Examples - Interactive Demo")
        self.setGeometry(100, 100, 800, 600)

        # Create tab widget
        tabs = QTabWidget()

        # Add all example tabs
        tabs.addTab(create_basic_example(), "1. Basic")
        tabs.addTab(create_multiple_patterns_example(), "2. Multiple Patterns")
        tabs.addTab(create_global_config_example(), "3. Global Config")
        tabs.addTab(create_per_pattern_config_example(), "4. Per-Pattern Config")
        tabs.addTab(create_word_wrap_example(), "5. Word Wrap")
        tabs.addTab(create_dynamic_updates_example(), "6. Dynamic Updates")
        tabs.addTab(create_table_delegate_example(), "7. Table Delegate")
        # tabs.addTab(create_code_editor_example(), "8. Code Editor") #Not working currently

        self.setCentralWidget(tabs)


# ============================================================================
# Run Application
# ============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle("Fusion")

    # Create and show demo window
    demo = PatternCompleterDemo()
    demo.show()

    sys.exit(app.exec())

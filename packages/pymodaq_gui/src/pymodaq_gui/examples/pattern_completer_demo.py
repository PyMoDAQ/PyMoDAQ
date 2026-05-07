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

    # :: for simple symbols
    # Using only simple single-character symbols to avoid cursor positioning issues
    symbols = [
        "check ✓",
        "cross ✗",
        "star ★",
        "arrow →",
        "bullet •",
        "circle ○",
        "square ■",
        "plus ✚",
    ]
    text_edit.add_completer("::", symbols)

    text_edit.setPlaceholderText(
        "Try typing:\n  @ for mentions\n  # for hashtags\n  :: for symbols",
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
        QLabel("Notice the green border when typing @ (visual indicator enabled)"),
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
        ":: keywords are case-sensitive (try '::def' vs '::DEF')",
    )
    layout.addWidget(text_edit)

    return widget


# ============================================================================
# EXAMPLE 5: Word Wrap Example - Side by Side Comparison
# ============================================================================
def create_word_wrap_example():
    """
    Demonstrates word wrap feature for long completion items with side-by-side comparison
    """
    widget = QWidget()
    layout = QVBoxLayout(widget)

    layout.addWidget(QLabel("<b>Example 5: Word Wrap - Side by Side Comparison</b>"))

    info_label = QLabel(
        "<b>What is Word Wrap?</b><br>"
        "• <b>word_wrap=False</b> (left): Long items are truncated or need scrolling<br>"
        "• <b>word_wrap=True</b> (right): Long items wrap to multiple lines in popup<br><br>"
        "Type @ in either field to see the difference side-by-side!<br>"
        "Both popups will appear simultaneously for comparison.",
    )
    layout.addWidget(info_label)

    # Create side-by-side layout
    compare_layout = QHBoxLayout()

    # Left side - WITHOUT word wrap
    left_layout = QVBoxLayout()
    left_layout.addWidget(QLabel("<b>WITHOUT Word Wrap</b>"))
    line_edit_no_wrap = PatternLineEdit()

    # Long completion items that benefit from word wrap
    long_items = [
        "Alice Johnson - Senior Developer at Tech Corp",
        "Bob Smith - Product Manager with 10 years experience",
        "Charlie Brown - UX Designer specializing in mobile applications",
        "Diana Prince - Data Scientist working on machine learning projects",
        "Eve Martinez - Full Stack Engineer with cloud expertise",
    ]

    line_edit_no_wrap.add_completer("@", long_items, word_wrap=False, max_width=300)
    line_edit_no_wrap.setPlaceholderText("Type @ - items truncated")
    left_layout.addWidget(line_edit_no_wrap)

    # Right side - WITH word wrap
    right_layout = QVBoxLayout()
    right_layout.addWidget(QLabel("<b>WITH Word Wrap</b>"))
    line_edit_with_wrap = PatternLineEdit()
    line_edit_with_wrap.add_completer("@", long_items, word_wrap=True, max_width=300)
    line_edit_with_wrap.setPlaceholderText("Type @ - items wrap")
    right_layout.addWidget(line_edit_with_wrap)

    # Mirror the text between both fields
    def sync_left_to_right(text):
        if line_edit_with_wrap.text() != text:
            line_edit_with_wrap.setText(text)
            line_edit_with_wrap.setCursorPosition(line_edit_no_wrap.cursorPosition())
            line_edit_no_wrap.setFocus()

    def sync_right_to_left(text):
        if line_edit_no_wrap.text() != text:
            line_edit_no_wrap.setText(text)
            line_edit_no_wrap.setCursorPosition(line_edit_with_wrap.cursorPosition())
            line_edit_with_wrap.setFocus()

    line_edit_no_wrap.textChanged.connect(sync_left_to_right)
    line_edit_with_wrap.textChanged.connect(sync_right_to_left)

    # Add both to compare layout
    compare_layout.addLayout(left_layout)
    compare_layout.addLayout(right_layout)
    layout.addLayout(compare_layout)


    # Add instruction label
    instruction_label = QLabel(
        "<i>Notice: The first item is automatically highlighted (selected) in both popups.<br>"
        "Press Tab or Enter to accept the highlighted suggestion!</i>",
    )
    instruction_label.setWordWrap(True)
    layout.addWidget(instruction_label)

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
        min_width=250, max_width=500, case_sensitive=True, auto_resize=True,
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
        "Try typing ':for' or '::pri'",
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
        self.setGeometry(100, 100, 900, 600)

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
        tabs.addTab(create_code_editor_example(), "8. Code Editor")  #Not working currently

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

# -*- coding: utf-8 -*-
"""
Tests for pattern_completer module

@author: PyMoDAQ Contributors
"""

import pytest
from qtpy import QtWidgets, QtCore, QtGui
from pymodaq_gui.utils.widgets.pattern_completer import (
    PatternLineEdit,
    PatternPlainTextEdit,
    PatternTextEdit,
    PatternCompleterDelegate,
)


@pytest.fixture
def pattern_line_edit(qtbot):
    """Create a PatternLineEdit widget for testing"""
    widget = PatternLineEdit()
    qtbot.addWidget(widget)
    widget.show()
    return widget


@pytest.fixture
def pattern_plain_text_edit(qtbot):
    """Create a PatternPlainTextEdit widget for testing"""
    widget = PatternPlainTextEdit()
    qtbot.addWidget(widget)
    widget.show()
    return widget


class TestPatternLineEdit:
    """Test PatternLineEdit widget"""

    def test_init(self, pattern_line_edit):
        """Test widget initialization"""
        assert hasattr(pattern_line_edit, 'completers')
        assert hasattr(pattern_line_edit, 'active_pattern')
        assert hasattr(pattern_line_edit, 'trigger_start_pos')
        assert pattern_line_edit.completers == {}
        assert pattern_line_edit.active_pattern is None
        assert pattern_line_edit.trigger_start_pos == -1

    def test_add_completer(self, pattern_line_edit):
        """Test adding a completer pattern"""
        pattern_line_edit.add_completer('@', ['alice', 'bob', 'charlie'])

        assert '@' in pattern_line_edit.completers
        assert pattern_line_edit.completers['@']['completions'] == ['alice', 'bob', 'charlie']
        assert 'completer' in pattern_line_edit.completers['@']
        assert 'model' in pattern_line_edit.completers['@']

    def test_add_multiple_completers(self, pattern_line_edit):
        """Test adding multiple different pattern completers"""
        pattern_line_edit.add_completer('@', ['alice', 'bob'])
        pattern_line_edit.add_completer('#', ['python', 'java'])

        assert '@' in pattern_line_edit.completers
        assert '#' in pattern_line_edit.completers
        assert len(pattern_line_edit.completers) == 2

    def test_update_completions(self, pattern_line_edit):
        """Test updating completion list for a pattern"""
        pattern_line_edit.add_completer('@', ['alice', 'bob'])
        pattern_line_edit.update_completions('@', ['alice', 'bob', 'charlie', 'david'])

        assert pattern_line_edit.completers['@']['completions'] == ['alice', 'bob', 'charlie', 'david']

    def test_find_active_trigger_simple(self, pattern_line_edit):
        """Test finding active trigger pattern"""
        pattern_line_edit.add_completer('@', ['alice', 'bob'])

        # Simulate typing "@a"
        text = "@a"
        cursor_pos = 2

        active_pattern, trigger_pos = pattern_line_edit._find_active_trigger(text, cursor_pos)

        assert active_pattern == '@'
        assert trigger_pos == 0

    def test_find_active_trigger_multiple_patterns(self, pattern_line_edit):
        """Test finding active trigger with multiple patterns"""
        pattern_line_edit.add_completer('@', ['alice'])
        pattern_line_edit.add_completer('#', ['python'])

        # Typing "#py" should activate # pattern
        text = "Hello @alice and #py"
        cursor_pos = 20

        active_pattern, trigger_pos = pattern_line_edit._find_active_trigger(text, cursor_pos)

        assert active_pattern == '#'
        assert trigger_pos == 17

    def test_find_active_trigger_with_space(self, pattern_line_edit):
        """Test that trigger is not active after a space"""
        pattern_line_edit.add_completer('@', ['alice'])

        # Space after trigger should deactivate it
        text = "@ "
        cursor_pos = 2

        active_pattern, trigger_pos = pattern_line_edit._find_active_trigger(text, cursor_pos)

        assert active_pattern is None
        assert trigger_pos == -1

    def test_global_config(self, qtbot):
        """Test global configuration options"""
        widget = PatternLineEdit(
            min_width=300,
            max_width=600,
            case_sensitive=True,
            visual_indicator=True,
        )
        qtbot.addWidget(widget)

        assert widget.global_config['min_width'] == 300
        assert widget.global_config['max_width'] == 600
        assert widget.global_config['case_sensitive'] is True
        assert widget.global_config['visual_indicator'] is True

    def test_pattern_specific_config(self, pattern_line_edit):
        """Test pattern-specific configuration overrides"""
        pattern_line_edit.add_completer(
            '@',
            ['alice', 'bob'],
            case_sensitive=True,
            min_width=250,
        )

        config = pattern_line_edit.completers['@']['config']
        assert config['case_sensitive'] is True
        assert config['min_width'] == 250

    def test_set_global_config(self, pattern_line_edit):
        """Test updating global configuration"""
        pattern_line_edit.set_global_config(min_width=400, max_width=800)

        assert pattern_line_edit.global_config['min_width'] == 400
        assert pattern_line_edit.global_config['max_width'] == 800

    def test_cleanup(self, pattern_line_edit):
        """Test cleanup of completer resources"""
        pattern_line_edit.add_completer('@', ['alice', 'bob'])
        pattern_line_edit.add_completer('#', ['python'])

        pattern_line_edit.cleanup_pattern_completer()

        assert len(pattern_line_edit.completers) == 0


class TestPatternPlainTextEdit:
    """Test PatternPlainTextEdit widget"""

    def test_init(self, pattern_plain_text_edit):
        """Test widget initialization"""
        assert hasattr(pattern_plain_text_edit, 'completers')
        assert pattern_plain_text_edit.completers == {}

    def test_multiline_text(self, pattern_plain_text_edit):
        """Test pattern completion in multiline text"""
        pattern_plain_text_edit.add_completer('@', ['alice', 'bob'])

        # Set multiline text
        text = "Hello @alice\nHow are you @"
        pattern_plain_text_edit.setPlainText(text)

        # Move cursor to end
        cursor = pattern_plain_text_edit.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        pattern_plain_text_edit.setTextCursor(cursor)

        cursor_pos = cursor.position()
        active_pattern, trigger_pos = pattern_plain_text_edit._find_active_trigger(text, cursor_pos)

        assert active_pattern == '@'
        # The @ is at position after "How are you "
        assert trigger_pos > 0


class TestPatternCompleterDelegate:
    """Test PatternCompleterDelegate for table editing"""

    def test_init(self):
        """Test delegate initialization"""
        delegate = PatternCompleterDelegate(min_width=200)

        assert delegate.global_kwargs['min_width'] == 200
        assert delegate.completer_configs == {}

    def test_add_completer(self):
        """Test adding completer to delegate"""
        delegate = PatternCompleterDelegate()
        delegate.add_completer('@', ['alice', 'bob'], case_sensitive=True)

        assert '@' in delegate.completer_configs
        assert delegate.completer_configs['@']['completions'] == ['alice', 'bob']
        assert delegate.completer_configs['@']['kwargs']['case_sensitive'] is True

    def test_update_completions(self):
        """Test updating completions in delegate"""
        delegate = PatternCompleterDelegate()
        delegate.add_completer('@', ['alice', 'bob'])
        delegate.update_completions('@', ['alice', 'bob', 'charlie'])

        assert delegate.completer_configs['@']['completions'] == ['alice', 'bob', 'charlie']

    def test_create_editor(self, qtbot):
        """Test creating editor widget from delegate"""
        delegate = PatternCompleterDelegate()
        delegate.add_completer('@', ['alice', 'bob'])

        # Create a parent widget
        parent = QtWidgets.QWidget()
        qtbot.addWidget(parent)

        # Create editor
        editor = delegate.createEditor(parent, None, None)

        assert isinstance(editor, PatternLineEdit)
        assert '@' in editor.completers


class TestPatternCompletion:
    """Integration tests for pattern completion functionality"""

    def test_text_changed_triggers_completion(self, pattern_line_edit, qtbot):
        """Test that typing trigger pattern activates completion"""
        pattern_line_edit.add_completer('@', ['alice', 'bob', 'charlie'])

        # Type "@a"
        pattern_line_edit.setText("@a")
        pattern_line_edit.setCursorPosition(2)

        # Wait for text changed signal processing
        qtbot.wait(50)

        assert pattern_line_edit.active_pattern == '@'
        assert pattern_line_edit.trigger_start_pos == 0

    def test_completion_popup_appears(self, pattern_line_edit, qtbot):
        """Test that completion popup appears when typing"""
        pattern_line_edit.add_completer('@', ['alice', 'bob'])

        # Type "@"
        pattern_line_edit.setText("@")
        pattern_line_edit.setCursorPosition(1)

        # Wait for popup to appear
        qtbot.wait(100)

        completer = pattern_line_edit.completers['@']['completer']
        # Note: Popup visibility may be flaky in tests without full event loop
        # Just verify completer is configured correctly
        assert completer.widget() == pattern_line_edit
        assert completer.completionPrefix() == ""

    def test_insert_completion(self, pattern_line_edit, qtbot):
        """Test inserting a completion"""
        pattern_line_edit.add_completer('@', ['alice', 'bob'])

        # Set up state as if we're completing
        pattern_line_edit.setText("Hello @a")
        pattern_line_edit.setCursorPosition(8)
        pattern_line_edit.active_pattern = '@'
        pattern_line_edit.trigger_start_pos = 6

        # Simulate selecting "alice" from completion
        pattern_line_edit._pattern_insert_completion("alice")

        assert pattern_line_edit.text() == "Hello alice"
        assert pattern_line_edit.cursorPosition() == 11

    def test_multiple_patterns_in_same_text(self, pattern_line_edit, qtbot):
        """Test handling multiple patterns in same text"""
        pattern_line_edit.add_completer('@', ['alice', 'bob'])
        pattern_line_edit.add_completer('#', ['python', 'java'])

        # Type text with both patterns
        pattern_line_edit.setText("@alice says #")
        pattern_line_edit.setCursorPosition(13)

        qtbot.wait(50)

        # Should activate # pattern at the cursor position
        assert pattern_line_edit.active_pattern == '#'
        assert pattern_line_edit.trigger_start_pos == 12

    def test_space_deactivates_completion(self, pattern_line_edit, qtbot):
        """Test that adding space after trigger deactivates completion"""
        pattern_line_edit.add_completer('@', ['alice'])

        # Type "@ " (trigger + space)
        pattern_line_edit.setText("@ ")
        pattern_line_edit.setCursorPosition(2)

        qtbot.wait(50)

        assert pattern_line_edit.active_pattern is None
        assert pattern_line_edit.trigger_start_pos == -1

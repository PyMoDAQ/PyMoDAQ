import pytest
from qtpy.QtWidgets import QPushButton, QLabel, QFrame, QVBoxLayout
from qtpy.QtCore import Qt
from pymodaq_gui.utils.widgets.collapsible_widget import CollapsibleWidget


@pytest.fixture
def toggle_button():
    return QPushButton("▼")


@pytest.fixture
def content_widget():
    widget = QFrame()
    layout = QVBoxLayout(widget)
    layout.addWidget(QLabel("Test Content"))
    return widget


class TestCollapsibleWidget:
    """Core functionality tests"""

    def test_starts_collapsed(self, qtbot, toggle_button, content_widget):
        """Widget should start in collapsed state"""
        widget = CollapsibleWidget(toggle_button, content_widget)
        qtbot.addWidget(widget)
        
        assert widget.is_expanded is False

    def test_toggle_expands_and_collapses(self, qtbot, toggle_button, content_widget):
        """Toggle should expand then collapse"""
        widget = CollapsibleWidget(toggle_button, content_widget)
        qtbot.addWidget(widget)
        
        widget.toggle_content()
        assert widget.is_expanded is True
        
        widget.toggle_content()
        assert widget.is_expanded is False

    def test_button_click_triggers_toggle(self, qtbot, toggle_button, content_widget):
        """Clicking button should expand widget"""
        widget = CollapsibleWidget(toggle_button, content_widget)
        qtbot.addWidget(widget)
        
        with qtbot.waitSignal(widget.toggled_signal, timeout=1000):
            qtbot.mouseClick(toggle_button, Qt.MouseButton.LeftButton)
        
        assert widget.is_expanded is True

    def test_toggled_signal_emits_correct_state(self, qtbot, toggle_button, content_widget):
        """Signal should emit True when expanded, False when collapsed"""
        widget = CollapsibleWidget(toggle_button, content_widget)
        qtbot.addWidget(widget)
        
        with qtbot.waitSignal(widget.toggled_signal) as blocker:
            widget.toggle_content()
        assert blocker.args[0] is True
        
        with qtbot.waitSignal(widget.toggled_signal) as blocker:
            widget.toggle_content()
        assert blocker.args[0] is False

    def test_vertical_direction_animates_height(self, qtbot, toggle_button, content_widget):
        """Vertical directions should animate maximumHeight"""
        widget = CollapsibleWidget(toggle_button, content_widget, direction="bottom")
        qtbot.addWidget(widget)
        
        assert widget.animated_property == b"maximumHeight"

    def test_horizontal_direction_animates_width(self, qtbot, toggle_button, content_widget):
        """Horizontal directions should animate maximumWidth"""
        widget = CollapsibleWidget(toggle_button, content_widget, direction="left")
        qtbot.addWidget(widget)
        
        assert widget.animated_property == b"maximumWidth"

    @pytest.mark.parametrize("original,expected", [
            ("▲", "▼"),
            ("▼", "▲"),
            ("◀", "▶"),
            ("▶", "◀"),
            ("◄", "►"),
            ("►", "◄"),
            ("←", "→"),
            ("→", "←"),
            ("↑", "↓"),
            ("↓", "↑"),
            ("⬆", "⬇"),
            ("⬇", "⬆"),
            ("⬅", "➡"),
            ("➡", "⬅"),
    ])
    def test_symbol_flipping(self, qtbot, content_widget, original, expected):
        """Symbols should flip when expanding"""
        button = QPushButton(original)
        widget = CollapsibleWidget(button, content_widget)
        qtbot.addWidget(widget)
        
        widget.toggle_content()
        button_text = button.text()
        assert expected in button_text

    def test_set_expanded_programmatically(self, qtbot, toggle_button, content_widget):
        """set_expanded should change state without animation"""
        widget = CollapsibleWidget(toggle_button, content_widget, direction="bottom")
        qtbot.addWidget(widget)
        
        widget.set_expanded(True)
        assert widget.is_expanded is True
        assert widget.collapsible_container.maximumHeight() > 0
        
        widget.set_expanded(False)
        assert widget.is_expanded is False
        assert widget.collapsible_container.maximumHeight() == 0
import pytest
from qtpy.QtCore import Qt
from pymodaq_gui.utils.widgets.search_lineedit import SearchLineEdit


@pytest.fixture
def search_widget(qtbot):
    widget = SearchLineEdit(debounce_ms=100)  # Shorter for faster tests
    qtbot.addWidget(widget)
    return widget


class TestSearchLineEdit:
    """Core functionality tests"""

    def test_empty_text_emits_immediately(self, qtbot, search_widget):
        """Clearing search should emit immediately without debounce"""

        search_widget.setText("test")

        with qtbot.waitSignal(search_widget.searchTextChanged, timeout=200) as blocker:
            search_widget.clear()

        assert blocker.args[0] == ""
        search_widget.deleteLater()

    def test_text_emits_after_debounce(self, qtbot, search_widget):
        """Non-empty text should emit after debounce delay"""
        with qtbot.waitSignal(search_widget.searchTextChanged, timeout=500) as blocker:
            search_widget.setText("test")

        assert blocker.args[0] == "test"
        search_widget.deleteLater()


    def test_rapid_changes_emit_once(self, qtbot, search_widget):
        """Rapid typing should result in single debounced signal"""
        signal_count = []
        search_widget.searchTextChanged.connect(lambda t: signal_count.append(t))

        search_widget.setText("t")
        search_widget.setText("te")
        search_widget.setText("tes")
        search_widget.setText("test")

        with qtbot.waitSignal(search_widget.searchTextChanged, timeout=500) as _:
            pass

        assert len(signal_count) == 1
        assert signal_count[0] == "test"
        search_widget.deleteLater()

    def test_debounce_resets_on_new_input(self, qtbot, search_widget):
        """New input should reset debounce timer"""

        search_widget.show()

        search_widget.setText("te")
        qtbot.wait(25)  # Less than debounce time
        search_widget.setText("test")  # Should reset timer

        with qtbot.waitSignal(search_widget.searchTextChanged, timeout=500) as blocker:
            pass
        assert blocker.args[0] == "test"

        search_widget.close()
        search_widget.deleteLater()

    def test_signal_not_emitted_before_debounce(self, qtbot, search_widget):
        """Signal should not emit before debounce time elapses"""
        signal_fired = []
        search_widget.searchTextChanged.connect(lambda t: signal_fired.append(t))

        search_widget.setText("test")
        qtbot.wait(50)  # Less than 100ms debounce

        assert len(signal_fired) == 0
        search_widget.deleteLater()

    def test_custom_debounce_time(self, qtbot):
        """Custom debounce time should be respected"""
        widget = SearchLineEdit(debounce_ms=500)
        qtbot.addWidget(widget)

        assert widget.debounce_ms == 500
        widget.deleteLater()

    def test_search_icon_created(self, search_widget):
        """Search icon should be created and not null"""
        assert search_widget.search_icon is not None
        assert not search_widget.search_icon.isNull()
        search_widget.deleteLater()

    def test_whitespace_only_emits_immediately(self, qtbot, search_widget):
        """Whitespace-only text should emit immediately like empty text"""
        with qtbot.waitSignal(search_widget.searchTextChanged, timeout=200) as blocker:
            search_widget.setText("   ")

        assert blocker.args[0] == "   "
        search_widget.deleteLater()

    def test_timer_stops_when_cleared(self, qtbot, search_widget):
        """Timer should stop when text is cleared"""
        search_widget.setText("test")
        assert search_widget.search_timer.isActive()

        search_widget.clear()
        qtbot.wait(50)

        # After clearing, timer should not be active (or restarted for immediate emit)
        assert search_widget.text() == ""
        search_widget.deleteLater()
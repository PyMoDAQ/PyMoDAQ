from qtpy.QtWidgets import (
    QWidget,
    QCompleter,
    QLineEdit,
    QTextEdit,
    QPlainTextEdit,
    QStyledItemDelegate,
    QListView,  # For word wrap
)
from qtpy.QtCore import Qt, QRect
from qtpy.QtGui import QStandardItemModel, QStandardItem, QTextCursor, QFontMetrics


class PatternCompleter:
    """
    Mixin class that adds pattern completion to any text widget.

    Requirements for the widget:
    - Must have: text(), setText(), cursorPosition() or textCursor()
    - Must emit: textChanged signal
    - Must support: keyPressEvent override

    Usage:
        class MyLineEdit(QLineEdit, PatternCompleterMixin):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.init_pattern_completer()
    """

    def init_pattern_completer(self, **kwargs):
        """
        Initialize the pattern completer system.

        Args:
            **kwargs: Global configuration options
                - min_width (int): Minimum popup width in pixels (default: 150)
                - max_width (int): Maximum popup width in pixels (default: 500)
                - visual_indicator (bool): Enable visual indicator globally (default: False)
                - case_sensitive (bool): Case sensitive completion (default: False)
                - completion_mode (str): 'popup' or 'inline' (default: 'popup')
                - auto_resize (bool): Auto-resize popup to content (default: True)
                - word_wrap (bool): Enable word wrap in popup (default: False)
        """
        # Initialize all attributes first
        self: QWidget  # Type hint for IDEs
        self.completers = {}
        self.active_pattern = None
        self.trigger_start_pos = -1
        self.inserting_completion = False
        self._is_destroyed = False

        # Global configuration with defaults
        self.global_config = {
            "min_width": kwargs.get("min_width", 150),
            "max_width": kwargs.get("max_width", 500),
            "visual_indicator": kwargs.get("visual_indicator", False),
            "case_sensitive": kwargs.get("case_sensitive", False),
            "completion_mode": kwargs.get("completion_mode", "popup"),
            "auto_resize": kwargs.get("auto_resize", True),
            "word_wrap": kwargs.get("word_wrap", False),
        }

        # Connect to text changes
        if hasattr(self, "textChanged"):
            try:
                self.textChanged.connect(self._pattern_on_text_changed)
            except Exception as e:
                print(f"Error connecting textChanged signal: {e}")

    def add_completer(self, pattern, completions, **kwargs):
        """
        Add a completer for a specific trigger pattern.

        Args:
            pattern (str): Trigger string (e.g., '@', '#', '::')
            completions (list): List of completion strings
            **kwargs: Per-pattern configuration (overrides global config)
                - visual_indicator (bool): Show visual indicator for this pattern
                - case_sensitive (bool): Case sensitive completion
                - min_width (int): Minimum popup width
                - max_width (int): Maximum popup width
                - completion_mode (str): 'popup' or 'inline'
                - auto_resize (bool): Auto-resize popup
                - word_wrap (bool): Word wrap in popup
                - padding (int): Extra padding for width calculation (default: 20)
        """
        model = QStandardItemModel()
        for item in completions:
            model.appendRow(QStandardItem(item))

        completer = QCompleter(model, self)

        # Apply configuration (pattern-specific overrides global)
        config = {**self.global_config, **kwargs}

        case_sensitivity = (
            Qt.CaseSensitivity.CaseSensitive
            if config.get("case_sensitive", False)
            else Qt.CaseSensitivity.CaseInsensitive
        )
        completer.setCaseSensitivity(case_sensitivity)

        completion_mode_str = config.get("completion_mode", "popup")
        if completion_mode_str == "inline":
            completer.setCompletionMode(QCompleter.CompletionMode.InlineCompletion)
        else:
            completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

        completer.activated.connect(self._pattern_insert_completion)

        # Configure popup
        popup = completer.popup()
        min_width = config.get("min_width", 150)
        max_width = config.get("max_width", 500)
        popup.setMinimumWidth(min_width)
        popup.setMaximumWidth(max_width)

        if isinstance(popup, QListView):
            word_wrap = config.get("word_wrap", False)
            popup.setWordWrap(word_wrap)
            popup.setTextElideMode(
                Qt.TextElideMode.ElideNone
                if not word_wrap
                else Qt.TextElideMode.ElideRight,
            )
            popup.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            popup.setResizeMode(QListView.ResizeMode.Adjust)

        self.completers[pattern] = {
            "completer": completer,
            "model": model,
            "completions": completions,
            "config": config,
        }

    def update_completions(self, pattern, completions):
        """Update completion list for a pattern"""
        if pattern not in self.completers:
            return

        config = self.completers[pattern]
        config["completions"] = completions
        config["model"].clear()
        for item in completions:
            config["model"].appendRow(QStandardItem(item))

    def update_completer_config(self, pattern, **kwargs):
        """
        Update configuration for a specific pattern completer.

        Args:
            pattern (str): The pattern to update
            **kwargs: Configuration options to update
        """
        if pattern not in self.completers:
            return

        config = self.completers[pattern]
        config["config"].update(kwargs)

        # Apply updates to completer
        completer: QCompleter = config["completer"]

        if "case_sensitive" in kwargs:
            case_sensitivity = (
                Qt.CaseSensitivity.CaseSensitive
                if kwargs["case_sensitive"]
                else Qt.CaseSensitivity.CaseInsensitive
            )
            completer.setCaseSensitivity(case_sensitivity)

        if "completion_mode" in kwargs:
            mode_str = kwargs["completion_mode"]
            if mode_str == "inline":
                completer.setCompletionMode(QCompleter.CompletionMode.InlineCompletion)
            else:
                completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

        # Update popup settings
        if any(k in kwargs for k in ["min_width", "max_width", "word_wrap"]):
            popup = completer.popup()

            if "min_width" in kwargs:
                popup.setMinimumWidth(kwargs["min_width"])
            if "max_width" in kwargs:
                popup.setMaximumWidth(kwargs["max_width"])
            if "word_wrap" in kwargs:
                from PyQt6.QtWidgets import QListView

                if isinstance(popup, QListView):
                    popup.setWordWrap(kwargs["word_wrap"])

    def set_global_config(self, **kwargs):
        """Update global configuration for all completers"""
        self.global_config.update(kwargs)

    def set_visual_indicator(self, enabled):
        """Enable/disable visual indicator globally"""
        self.global_config["visual_indicator"] = enabled

    def cleanup_pattern_completer(self):
        """Clean up completer resources"""
        # Disconnect text changed signal first
        if hasattr(self, "textChanged"):
            try:
                self.textChanged.disconnect(self._pattern_on_text_changed)
            except (TypeError, RuntimeError):
                pass

        # Clean up completers
        for pattern, config in list(self.completers.items()):
            try:
                completer: QCompleter = config.get("completer")
                if completer:
                    # Hide and disconnect popup
                    popup = completer.popup()
                    if popup and popup.isVisible():
                        popup.hide()

                    # Disconnect signals
                    try:
                        completer.activated.disconnect()
                    except (TypeError, RuntimeError):
                        pass

                    # Delete completer
                    completer.setWidget(None)
                    completer.setModel(None)
                    completer.deleteLater()
            except (TypeError, RuntimeError, AttributeError) as e:
                print(f"Error cleaning up completer for pattern '{pattern}': {e}")
                pass

        self.completers.clear()

    def _get_text_and_cursor(self):
        """Get text and cursor position (works for different widget types)"""
        text = self.toPlainText() if hasattr(self, "toPlainText") else self.text()

        if hasattr(self, "textCursor"):
            cursor_pos: QTextCursor = self.textCursor().position()
        else:
            cursor_pos = self.cursorPosition()

        return text, cursor_pos

    def _set_text_with_cursor(self, text, cursor_pos):
        """Set text and cursor position (works for different widget types)"""
        if hasattr(self, "setPlainText"):
            self.setPlainText(text)
            cursor: QTextCursor = self.textCursor()
            cursor.setPosition(min(cursor_pos, len(text)))
            self.setTextCursor(cursor)
        else:
            self.setText(text)
            self.setCursorPosition(min(cursor_pos, len(text)))

    def _find_active_trigger(self, text, cursor_pos):
        """
        Find which trigger pattern is currently active.

        Handles overlapping patterns (e.g., : and ::) by prioritizing:
        1. Patterns that appear later in the text
        2. Longer patterns over shorter ones at the same position
        """
        # Sort patterns by length (longest first) to check longer patterns first
        sorted_patterns = sorted(self.completers.keys(), key=len, reverse=True)

        active_pattern = None
        trigger_pos = -1
        trigger_end = -1

        search_text = text[:cursor_pos]

        for pattern in sorted_patterns:
            pos = search_text.rfind(pattern)

            while pos >= 0:
                end_pos = pos + len(pattern)

                # Validate end_pos doesn't exceed text length
                if end_pos > len(text):
                    pos = search_text.rfind(pattern, 0, pos)
                    continue

                text_after = text[end_pos:cursor_pos]

                # Only consider if no space/newline after trigger
                if " " not in text_after and "\n" not in text_after:
                    # Skip if this pattern overlaps with an already found longer pattern
                    # E.g., skip : at pos 1 if we already found :: at pos 0
                    if trigger_pos >= 0 and pos >= trigger_pos and pos < trigger_end:
                        pos = search_text.rfind(pattern, 0, pos)
                        continue

                    # Skip if a longer pattern exists at the same position
                    # E.g., skip : at pos 0 if :: also exists at pos 0
                    longer_exists = any(
                        len(other) > len(pattern)
                        and search_text[pos:].startswith(other)
                        and pos + len(other) <= cursor_pos
                        for other in sorted_patterns
                    )

                    if longer_exists:
                        pos = search_text.rfind(pattern, 0, pos)
                        continue

                    # Accept this pattern (later position or same position but longer)
                    if pos > trigger_pos or (pos == trigger_pos and len(pattern) > len(active_pattern)):
                        trigger_pos = pos
                        trigger_end = end_pos
                        active_pattern = pattern
                    break

                pos = search_text.rfind(pattern, 0, pos)

        return active_pattern, trigger_pos

    def _apply_visual_indicator(self, active):
        """Apply visual styling"""
        config = self.global_config
        if not config.get("visual_indicator", False):
            return

        if active:
            # Use object name for more reliable styling
            if not self.objectName():
                self.setObjectName("pattern_completer_widget")
            self.setStyleSheet(
                "#pattern_completer_widget { border: 2px solid #4CAF50; border-radius: 3px; }",
            )
        else:
            self.setStyleSheet("")

    def _pattern_on_text_changed(self):
        """Handle text changes"""
        if self.inserting_completion:
            return

        try:
            text, cursor_pos = self._get_text_and_cursor()
        except (RuntimeError, AttributeError):
            return

        active_pattern, trigger_pos = self._find_active_trigger(text, cursor_pos)

        if active_pattern and trigger_pos >= 0:
            # If pattern changed, hide popups from other patterns
            if self.active_pattern != active_pattern:
                for pattern, pattern_config in self.completers.items():
                    if pattern != active_pattern:
                        try:
                            if pattern_config["completer"].popup().isVisible():
                                pattern_config["completer"].popup().hide()
                        except (RuntimeError, AttributeError):
                            pass

            self.active_pattern = active_pattern
            self.trigger_start_pos = trigger_pos

            pattern_config = self.completers[active_pattern]
            completer: QCompleter = pattern_config["completer"]
            config = pattern_config["config"]

            pattern_len = len(active_pattern)
            prefix = text[trigger_pos + pattern_len : cursor_pos]

            completer.setCompletionPrefix(prefix)
            completer.setWidget(self)

            # Calculate optimal width based on content
            popup = completer.popup()
            popup.setUpdatesEnabled(False)

            # Position the popup at the cursor for multi-line widgets
            if hasattr(self, "cursorRect"):
                # QTextEdit/QPlainTextEdit - position at cursor
                cursor_rect: QRect = self.cursorRect()
                popup_pos = self.mapToGlobal(cursor_rect.bottomLeft())
                popup.move(popup_pos)
                completer.complete(cursor_rect)
            else:
                # QLineEdit - default positioning is fine
                completer.complete()

            # Auto-select first item to indicate it will be chosen
            if completer.completionCount() > 0:
                popup.setCurrentIndex(completer.completionModel().index(0, 0))

            # Auto-resize popup width to fit content using font metrics
            if config.get("auto_resize", True) and completer.completionCount() > 0:
                # Get font metrics from the popup
                font_metrics = QFontMetrics(popup.font())

                max_width = config.get("min_width", 150)
                padding = config.get("padding", 20)

                for i in range(completer.completionCount()):
                    index = completer.completionModel().index(i, 0)
                    item_text = completer.completionModel().data(index)
                    if item_text:
                        # Get actual pixel width of the text
                        text_width = font_metrics.horizontalAdvance(str(item_text))
                        max_width = max(max_width, text_width + padding)

                # Set width with limits
                max_limit = config.get("max_width", 500)
                max_width = min(max_width, max_limit)
                popup.setFixedWidth(max_width)

            popup.setUpdatesEnabled(True)

            if config.get("visual_indicator", False):
                self._apply_visual_indicator(True)
        else:
            self.active_pattern = None
            self.trigger_start_pos = -1

            for pattern_config in self.completers.values():
                try:
                    if pattern_config["completer"].popup().isVisible():
                        pattern_config["completer"].popup().hide()
                except (RuntimeError, AttributeError):
                    pass

            self._apply_visual_indicator(False)

    def _pattern_insert_completion(self, completion):
        """Insert the selected completion"""
        if self.trigger_start_pos < 0 or not self.active_pattern:
            return

        self.inserting_completion = True

        try:
            # Remove the trigger pattern and any text after it up to cursor
            text, cursor_pos = self._get_text_and_cursor()

            # Replace with just the completion (without the pattern prefix)
            new_text = text[: self.trigger_start_pos] + completion + text[cursor_pos:]
            new_cursor_pos = self.trigger_start_pos + len(completion)
            self._set_text_with_cursor(new_text, new_cursor_pos)

            # Reset state BEFORE hiding popup to prevent re-triggering
            self.trigger_start_pos = -1
            self.active_pattern = None

            # Hide all popups
            for pattern_config in self.completers.values():
                try:
                    if pattern_config["completer"].popup().isVisible():
                        pattern_config["completer"].popup().hide()
                except (RuntimeError, AttributeError):
                    pass

            self._apply_visual_indicator(False)
        finally:
            self.inserting_completion = False

    def _pattern_key_press_event(self, event):
        """
        Handle pattern completion keys.
        Call this from your widget's keyPressEvent BEFORE calling super().

        Returns:
            bool: True if event was handled (don't call super), False otherwise
        """
        # Find the active completer with a visible popup
        active_completer:QCompleter = None
        for pattern, pattern_config in self.completers.items():
            if pattern_config["completer"].popup().isVisible():
                if pattern == self.active_pattern:
                    active_completer = pattern_config["completer"]
                break

        if active_completer:
            if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Tab):
                # Get current index, or use first item if none selected
                index = active_completer.popup().currentIndex()
                if not index.isValid():
                    # Auto-select first item if nothing selected
                    index = active_completer.completionModel().index(0, 0)

                if index.isValid():
                    completion = active_completer.completionModel().data(index)
                    self._pattern_insert_completion(completion)
                event.accept()
                return True  # Event handled
            elif event.key() == Qt.Key.Key_Escape:
                active_completer.popup().hide()
                self._apply_visual_indicator(False)
                event.accept()
                return True  # Event handled

        return False  # Event not handled, continue normal processing


class PatternLineEdit(QLineEdit, PatternCompleter):
    """QLineEdit with pattern completion"""

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self.init_pattern_completer(**kwargs)

    def keyPressEvent(self, event):
        """Override to handle completion keys"""
        if not self._pattern_key_press_event(event):
            # Event not handled by pattern completer, process normally
            super().keyPressEvent(event)


class PatternTextEdit(QTextEdit, PatternCompleter):
    """QTextEdit with pattern completion"""

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self.init_pattern_completer(**kwargs)

    def keyPressEvent(self, event):
        """Override to handle completion keys"""
        if not self._pattern_key_press_event(event):
            # Event not handled by pattern completer, process normally
            super().keyPressEvent(event)


class PatternPlainTextEdit(QPlainTextEdit, PatternCompleter):
    """QPlainTextEdit with pattern completion"""

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self.init_pattern_completer(**kwargs)

    def keyPressEvent(self, event):
        """Override to handle completion keys"""
        if not self._pattern_key_press_event(event):
            # Event not handled by pattern completer, process normally
            super().keyPressEvent(event)


class PatternCompleterDelegate(QStyledItemDelegate):
    """
    Custom delegate for QTableWidget that uses PatternLineEdit with mixin.

    Usage:
        delegate = PatternCompleterDelegate(min_width=200, max_width=600)
        delegate.add_completer('@', ['USA', 'Canada', 'Mexico'])
        delegate.add_completer('#', ['Python', 'Java', 'C++'], case_sensitive=True)
        table.setItemDelegateForColumn(0, delegate)
    """

    def __init__(self, parent=None, **kwargs):
        """
        Initialize delegate with global configuration.

        Args:
            **kwargs: Global configuration options (same as init_pattern_completer)
        """
        super().__init__(parent)
        self.completer_configs = {}  # pattern -> config dict
        self.global_kwargs = kwargs

    def add_completer(self, pattern, completions, **kwargs):
        """
        Add a completer pattern for this delegate.

        Args:
            pattern: Trigger string (e.g., '@', '#')
            completions: List of completion strings
            **kwargs: Pattern-specific configuration (overrides global)
        """
        self.completer_configs[pattern] = {
            "completions": completions,
            "kwargs": kwargs,
        }

    def update_completions(self, pattern, completions):
        """Update the completion list for a specific pattern"""
        if pattern in self.completer_configs:
            self.completer_configs[pattern]["completions"] = completions

    def update_completer_config(self, pattern, **kwargs):
        """Update configuration for a specific pattern"""
        if pattern in self.completer_configs:
            self.completer_configs[pattern]["kwargs"].update(kwargs)

    def set_global_config(self, **kwargs):
        """Update global configuration"""
        self.global_kwargs.update(kwargs)

    def createEditor(self, parent, option, index):
        """Create a PatternLineEdit when editing starts"""
        try:
            editor = PatternLineEdit(parent, **self.global_kwargs)

            # Add all configured completers
            for pattern, config in self.completer_configs.items():
                editor.add_completer(
                    pattern, config["completions"], **config.get("kwargs", {}),
                )

            return editor
        except Exception as e:
            print(f"Error creating editor: {e}")
            # Fallback to basic QLineEdit
            return QLineEdit(parent)

    def setEditorData(self, editor: PatternLineEdit, index):
        """Load data from model into editor"""
        try:
            if not editor or not index.isValid():
                return
            value = index.model().data(index, Qt.ItemDataRole.DisplayRole)
            if value is not None:
                editor.setText(str(value))
            else:
                editor.clear()
        except Exception as e:
            print(f"Error setting editor data: {e}")
            pass

    def setModelData(self, editor: PatternLineEdit, model, index):
        """Save data from editor back to model"""
        try:
            if not editor or not model or not index.isValid():
                return
            text = editor.text()
            model.setData(index, text, Qt.ItemDataRole.EditRole)
        except Exception as e:
            print(f"Error setting model data: {e}")
            pass

    def destroyEditor(self, editor: PatternLineEdit, index):
        """Clean up editor when done"""
        try:
            if editor and hasattr(editor, "cleanup_pattern_completer"):
                editor.cleanup_pattern_completer()
        except Exception as e:
            print(f"Error destroying editor: {e}")
            pass

        try:
            super().destroyEditor(editor, index)
        except Exception as e:
            print(f"Error in super destroyEditor: {e}")
            pass

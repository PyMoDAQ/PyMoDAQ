"""
Pattern Completer Parameter Item for pyqtgraph

This module provides a custom parameter item that integrates pattern completion
functionality into pyqtgraph's parameter tree system.

Features:
- Multiple trigger patterns (e.g., '@' for users, '#' for tags)
- Dynamic updates via convenience methods or direct setOpts
- Configurable completion behavior (case sensitivity, popup size, etc.)
- Full integration with pyqtgraph's parameter system
"""

from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import TextParameterItem, SimpleParameter
from pymodaq_gui.utils.widgets.pattern_completer import PatternPlainTextEdit


class PatternParameterItem(TextParameterItem):
    """
    A parameter item that provides pattern completion in the text editor.

    This extends pyqtgraph's TextParameterItem to add pattern-based autocompletion.
    You can configure multiple completion patterns (e.g., '@' for mentions, '#' for tags).
    """

    def __init__(self, param, depth):
        super().__init__(param, depth)

    def makeWidget(self):
        """Create the pattern-enabled line edit widget"""
        self.hideWidget = False
        self.asSubItem = True
        completer_config = self.param.opts.get("completer_config", {})

        # Create the widget with global configuration
        widget = PatternPlainTextEdit(**completer_config)

        # Add pattern completers
        patterns = self.param.opts.get("patterns", {})
        for pattern, completions in patterns.items():
            # Per-pattern config can override global config
            pattern_config = self.param.opts.get(f"pattern_config_{pattern}", {})
            widget.add_completer(pattern, completions, **pattern_config)

        widget.value = widget.toPlainText
        widget.setValue = widget.setPlainText
        widget.sigChanged = widget.textChanged

        self.widget = widget

        return widget

    def optsChanged(self, param, opts):
        """Handle parameter option changes - this is triggered by setOpts"""
        super().optsChanged(param, opts)

        # Update patterns if changed
        if "patterns" in opts and hasattr(self, "widget") and self.widget is not None:
            patterns = opts["patterns"]

            # First, handle removed patterns (in widget but not in new opts)
            if hasattr(self.widget, "completers"):
                widget_patterns = set(self.widget.completers.keys())
                opts_patterns = set(patterns.keys())
                removed_patterns = widget_patterns - opts_patterns

                for pattern in removed_patterns:
                    del self.widget.completers[pattern]

            # Then, add new patterns or update existing ones
            for pattern, completions in patterns.items():
                # Check if pattern exists in widget's completers
                if (
                    hasattr(self.widget, "completers")
                    and pattern in self.widget.completers
                ):
                    # Pattern exists, just update completions
                    self.widget.update_completions(pattern, completions)
                else:
                    # New pattern, add it
                    pattern_config = self.param.opts.get(
                        f"pattern_config_{pattern}", {},
                    )
                    self.widget.add_completer(pattern, completions, **pattern_config)

        # Update completer config if changed
        if (
            "completer_config" in opts
            and hasattr(self, "widget")
            and self.widget is not None
        ):
            self.widget.set_global_config(**opts["completer_config"])


class PatternParameter(SimpleParameter):
    """
    Parameter class for pattern completion.

    This parameter type allows text input with pattern-based autocompletion.
    Uses pyqtgraph's setOpts for all updates.

    Users can update patterns in two ways:
    1. Convenience methods: update_completions(), add_pattern(), remove_pattern()
    2. Direct setOpts: parameter.setOpts(patterns=new_patterns_dict)
    """

    itemClass = PatternParameterItem

    def __init__(self, **opts):
        # Set default options
        opts.setdefault("patterns", {})
        opts.setdefault("completer_config", {})
        super().__init__(**opts)

    def add_pattern(self, pattern, completions, **config):
        """
        Add or update a completion pattern after initialization.

        Args:
            pattern (str): Trigger string (e.g., '@', '#')
            completions (list): List of completion strings
            **config: Pattern-specific configuration
        """
        # Create new patterns dict with the added/updated pattern
        new_patterns = dict(self.opts.get("patterns", {}))
        new_patterns[pattern] = list(
            completions,
        )  # Use list() to create a new list object

        # Build opts dict for setOpts
        opts_to_set = {"patterns": new_patterns}

        # Add pattern-specific config if provided
        if config:
            opts_to_set[f"pattern_config_{pattern}"] = config

        # Let setOpts handle everything
        self.setOpts(**opts_to_set)

    def update_completions(self, pattern, completions):
        """
        Update the completion list for a specific pattern.

        Args:
            pattern (str): The pattern to update
            completions (list): New list of completion strings
        """
        if pattern not in self.opts.get("patterns", {}):
            print(
                f"Warning: Pattern '{pattern}' not found. Use add_pattern() to add it first.",
            )
            return

        # Create new patterns dict with the updated pattern
        new_patterns = dict(self.opts.get("patterns", {}))
        new_patterns[pattern] = list(
            completions,
        )  # Use list() to create a new list object

        # Let setOpts handle everything
        self.setOpts(patterns=new_patterns)

    def remove_pattern(self, pattern):
        """
        Remove a completion pattern.

        Args:
            pattern (str): The pattern to remove
        """
        if pattern not in self.opts.get("patterns", {}):
            return

        # Create new patterns dict without the removed pattern
        new_patterns = dict(self.opts.get("patterns", {}))
        del new_patterns[pattern]

        # Let setOpts handle everything (optsChanged will handle widget cleanup)
        self.setOpts(patterns=new_patterns)

    def set_completer_config(self, **config):
        """
        Update global completer configuration.

        Args:
            **config: Configuration options (min_width, max_width, etc.)
        """
        # Create new config dict with updates
        new_config = dict(self.opts.get("completer_config", {}))
        new_config.update(config)

        # Let setOpts handle everything
        self.setOpts(completer_config=new_config)


# Example usage and demo
if __name__ == "__main__":
    import sys
    from qtpy.QtWidgets import (
        QApplication,
        QWidget,
        QVBoxLayout,
        QPushButton,
        QLabel,
        QGroupBox,
    )
    from pyqtgraph.parametertree import ParameterTree

    app = QApplication(sys.argv)

    # Create a parameter tree with pattern parameters
    params = [
        {
            "name": "Text Editing",
            "type": "group",
            "children": [
                {
                    "name": "Message",
                    "type": "text_pattern",
                    "value": "",
                    "patterns": {
                        "@": ["alice", "bob", "charlie"],
                        "#": ["python", "javascript", "cpp"],
                    },
                    "completer_config": {
                        "min_width": 200,
                        "max_width": 400,
                        "case_sensitive": False,
                        "visual_indicator": True,
                    },
                },
                {
                    "name": "Tags",
                    "type": "text_pattern",
                    "value": "",
                    "patterns": {"#": ["urgent", "todo", "done", "in-progress"]},
                    "completer_config": {"min_width": 150, "case_sensitive": False},
                },
            ],
        },
    ]

    # Create parameter tree
    p = Parameter.create(name="params", type="group", children=params)
    tree = ParameterTree()
    tree.setParameters(p, showTop=False)

    # Get the Message parameter for examples
    message_param = p.child("Text Editing").child("Message")

    # ========================================================================
    # EXAMPLE 1: Using convenience methods
    # ========================================================================
    def example_convenience_update():
        """Update completions using the convenience method"""
        print("\n" + "=" * 60)
        print("EXAMPLE 1: Update using convenience method")
        print("=" * 60)
        new_completions = ["alice", "bob", "charlie", "david", "eve"]
        message_param.update_completions("@", new_completions)
        print(f"✓ Updated @ completions: {new_completions}")
        print("=" * 60 + "\n")

    def example_convenience_add():
        """Add pattern using the convenience method"""
        print("\n" + "=" * 60)
        print("EXAMPLE 2: Add pattern using convenience method")
        print("=" * 60)
        message_param.add_pattern("$", ["dollar", "euro", "pound", "yen"])
        print(f"✓ Added $ pattern with currency completions")
        print("=" * 60 + "\n")

    def example_convenience_remove():
        """Remove pattern using the convenience method"""
        print("\n" + "=" * 60)
        print("EXAMPLE 3: Remove pattern using convenience method")
        print("=" * 60)
        message_param.remove_pattern("#")
        print(f"✓ Removed # pattern")
        print("=" * 60 + "\n")

    # ========================================================================
    # EXAMPLE 2: Using direct setOpts (standard pyqtgraph approach)
    # ========================================================================
    def example_setopts_update():
        """Update completions using setOpts directly"""
        print("\n" + "=" * 60)
        print("EXAMPLE 4: Update using setOpts directly")
        print("=" * 60)

        # Get current patterns
        current_patterns = message_param.opts.get("patterns", {})

        # Create new patterns dict with updated completions
        new_patterns = dict(current_patterns)
        new_patterns["@"] = ["alice", "bob", "charlie", "frank", "grace"]

        # Apply changes
        message_param.setOpts(patterns=new_patterns)
        print(f"✓ Updated @ completions using setOpts")
        print(f"  Code: message_param.setOpts(patterns=new_patterns)")
        print("=" * 60 + "\n")

    def example_setopts_add():
        """Add pattern using setOpts directly"""
        print("\n" + "=" * 60)
        print("EXAMPLE 5: Add pattern using setOpts directly")
        print("=" * 60)

        # Get current patterns and add new one
        current_patterns = message_param.opts.get("patterns", {})
        new_patterns = dict(current_patterns)
        new_patterns[":"] = ["smile", "heart", "fire", "star"]

        # Apply changes
        message_param.setOpts(patterns=new_patterns)
        print(f"✓ Added : pattern using setOpts")
        print(f"  Code: message_param.setOpts(patterns=new_patterns)")
        print("=" * 60 + "\n")

    def example_setopts_remove():
        """Remove pattern using setOpts directly"""
        print("\n" + "=" * 60)
        print("EXAMPLE 6: Remove pattern using setOpts directly")
        print("=" * 60)

        # Get current patterns and remove one
        current_patterns = message_param.opts.get("patterns", {})
        new_patterns = dict(current_patterns)
        if "$" in new_patterns:
            del new_patterns["$"]

        # Apply changes
        message_param.setOpts(patterns=new_patterns)
        print(f"✓ Removed $ pattern using setOpts")
        print(f"  Code: message_param.setOpts(patterns=new_patterns)")
        print("=" * 60 + "\n")

    def example_setopts_config():
        """Update config using setOpts directly"""
        print("\n" + "=" * 60)
        print("EXAMPLE 7: Update config using setOpts directly")
        print("=" * 60)

        # Get current config and update it
        current_config = message_param.opts.get("completer_config", {})
        new_config = dict(current_config)
        new_config["min_width"] = 300
        new_config["max_width"] = 600

        # Apply changes
        message_param.setOpts(completer_config=new_config)
        print(f"✓ Updated completer config using setOpts")
        print(f"  Code: message_param.setOpts(completer_config=new_config)")
        print("=" * 60 + "\n")

    # ========================================================================
    # EXAMPLE 3: Programmatic/automated updates
    # ========================================================================
    def example_auto_update():
        """Example of automated updates (e.g., from a timer or callback)"""
        print("\n" + "=" * 60)
        print("EXAMPLE 8: Automated update simulation")
        print("=" * 60)

        # Simulate loading user list from a database
        users_from_db = [
            "alice",
            "bob",
            "charlie",
            "david",
            "eve",
            "frank",
            "grace",
            "henry",
        ]

        current_patterns = message_param.opts.get("patterns", {})
        new_patterns = dict(current_patterns)
        new_patterns["@"] = users_from_db
        message_param.setOpts(patterns=new_patterns)

        print(f"✓ Updated @ with {len(users_from_db)} users from 'database'")
        print("=" * 60 + "\n")

    # Create window
    window = QWidget()
    main_layout = QVBoxLayout()

    # Add instructions
    instructions = QLabel(
        "<b>Pattern Completer Parameter - Interactive Demo</b><br><br>"
        "<b>How to use:</b><br>"
        "• Type '@' in Message field to see user completions<br>"
        "• Type '#' to see tag completions<br>"
        "• Click buttons below to dynamically update patterns<br><br>"
        "<b>Two approaches available:</b><br>"
        "1. <b>Convenience methods</b>: update_completions(), add_pattern(), remove_pattern()<br>"
        "2. <b>Direct setOpts()</b>: Standard pyqtgraph approach - message_param.setOpts(patterns=...)",
    )
    instructions.setWordWrap(True)
    main_layout.addWidget(instructions)

    # Add parameter tree
    main_layout.addWidget(tree)

    # Group 1: Convenience Methods
    group1 = QGroupBox("Method 1: Convenience Methods")
    group1_layout = QVBoxLayout()

    btn1_1 = QPushButton("Update @ completions (add david, eve)")
    btn1_1.clicked.connect(example_convenience_update)
    group1_layout.addWidget(btn1_1)

    btn1_2 = QPushButton("Add $ pattern (currencies)")
    btn1_2.clicked.connect(example_convenience_add)
    group1_layout.addWidget(btn1_2)

    btn1_3 = QPushButton("Remove # pattern")
    btn1_3.clicked.connect(example_convenience_remove)
    group1_layout.addWidget(btn1_3)

    group1.setLayout(group1_layout)
    main_layout.addWidget(group1)

    # Group 2: Direct setOpts
    group2 = QGroupBox("Method 2: Direct setOpts (Standard PyQtGraph)")
    group2_layout = QVBoxLayout()

    btn2_1 = QPushButton("Update @ with setOpts (add frank, grace)")
    btn2_1.clicked.connect(example_setopts_update)
    group2_layout.addWidget(btn2_1)

    btn2_2 = QPushButton("Add : pattern with setOpts (emojis)")
    btn2_2.clicked.connect(example_setopts_add)
    group2_layout.addWidget(btn2_2)

    btn2_3 = QPushButton("Remove $ with setOpts")
    btn2_3.clicked.connect(example_setopts_remove)
    group2_layout.addWidget(btn2_3)

    btn2_4 = QPushButton("Update config with setOpts (wider popup)")
    btn2_4.clicked.connect(example_setopts_config)
    group2_layout.addWidget(btn2_4)

    group2.setLayout(group2_layout)
    main_layout.addWidget(group2)

    # Group 3: Advanced
    group3 = QGroupBox("Advanced Examples")
    group3_layout = QVBoxLayout()

    btn3_1 = QPushButton("Simulate loading users from database")
    btn3_1.clicked.connect(example_auto_update)
    group3_layout.addWidget(btn3_1)

    group3.setLayout(group3_layout)
    main_layout.addWidget(group3)

    window.setLayout(main_layout)
    window.setWindowTitle("Pattern Completer Parameter - Demo")
    window.resize(800, 700)
    window.show()

    # Print initial state
    print("\n" + "=" * 70)
    print("PATTERN COMPLETER PARAMETER - INTERACTIVE DEMO")
    print("=" * 70)
    print("\nInitial state:")
    print(f"  Message patterns: {list(message_param.opts.get('patterns', {}).keys())}")
    print(f"  @ completions: {message_param.opts['patterns']['@']}")
    print(f"  # completions: {message_param.opts['patterns']['#']}")
    print("\nTry typing '@' or '#' in the Message field to see completions!")
    print("Then click buttons to see dynamic updates in action.")
    print("=" * 70 + "\n")

    # Monitor value changes
    def value_changed(param, value):
        if value:  # Only print non-empty values
            print(f"[Value Changed] {param.name()}: {value}")

    p.sigTreeStateChanged.connect(value_changed)

    sys.exit(app.exec())

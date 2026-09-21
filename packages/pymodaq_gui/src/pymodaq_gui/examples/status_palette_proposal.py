"""
PyMoDAQ Status Color Palette — Community Proposal
==================================================

Run this file directly to display the proposed color convention::

    python status_palette_proposal.py

The widget shows all six states with their LED color, name, logging-level
analogy, and intended meaning.  Colors are drawn from the active qt_themes
theme — use the combobox at the top to switch themes live.
"""

import sys

import qt_themes
from qtpy import QtCore, QtGui, QtWidgets

from pymodaq_gui.utils.widgets.multistate_led import MultistateLED
from pymodaq_gui.utils.status_palette import StatusPalette, _DEFINITIONS


# ── Available themes ────────────────────────────────────────────────────────
try:
    # qt_themes may expose a list of theme names — use it if available
    _THEME_NAMES: list[str] = sorted(qt_themes.list_themes())
except AttributeError:
    _THEME_NAMES = [
        'atom_one', 'blender',
        'catppuccin_frappe', 'catppuccin_latte',
        'catppuccin_macchiato', 'catppuccin_mocha',
        'dracula', 'github_dark', 'github_light',
        'modern_dark', 'modern_light', 'monokai',
        'nord', 'one_dark_two',
    ]


# Human-readable descriptions for each state
_DESCRIPTIONS = {
    'off':      'Module absent, not initialized, or hardware not yet connected.',
    'idle':     'Initialized and ready — waiting for a user command or trigger.',
    'running':  'A command is in flight: moving, acquiring, or processing data.',
    'warning':  'Non-fatal issue detected — still functional, attention advised.',
    'error':    'An operation failed. Module may still recover, attention advised.',
    'critical': 'Unrecoverable fault — timeout, hardware error, or fatal exception.',
}

# Logging-level analogy for the reference table
_LOG_LEVEL = {
    'off':      '—',
    'idle':     '—',
    'running':  '—',
    'warning':  'WARNING',
    'error':    'ERROR',
    'critical': 'CRITICAL',
}


class StatusPaletteWidget(QtWidgets.QWidget):
    """Standalone reference widget for the PyMoDAQ status color proposal."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('PyMoDAQ — Status Color Palette Proposal')
        self._content_widget = None
        self._build_skeleton()
        self._refresh_colors()

    # ── Fixed structure (built once) ────────────────────────────────────────

    def _build_skeleton(self):
        self._root = QtWidgets.QVBoxLayout(self)
        self._root.setSpacing(12)
        self._root.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QtWidgets.QLabel('PyMoDAQ — Proposed Status Color Convention')
        font = title.font()
        font.setPointSize(font.pointSize() + 3)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._root.addWidget(title)

        subtitle = QtWidgets.QLabel(
            'A shared six-state vocabulary for LEDs, icons, and status bars.\n'
            'Upper three states align with Python logging severity levels '
            '(WARNING / ERROR / CRITICAL).\n'
            'Colors adapt to the active qt_themes dark / light theme.'
        )
        subtitle.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        self._root.addWidget(subtitle)

        # Theme selector row
        theme_row = QtWidgets.QHBoxLayout()
        theme_row.addWidget(QtWidgets.QLabel('<b>Theme:</b>'))

        self._theme_combo = QtWidgets.QComboBox()
        self._theme_combo.addItems(_THEME_NAMES)
        self._theme_combo.setMinimumWidth(180)

        # Pre-select the currently active theme
        try:
            from pymodaq_gui import config
            current_theme = config('gui', 'style', 'theme')[0]
            idx = self._theme_combo.findText(current_theme)
            if idx >= 0:
                self._theme_combo.setCurrentIndex(idx)
        except Exception:
            pass

        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)
        theme_row.addWidget(self._theme_combo)
        theme_row.addStretch()
        self._root.addLayout(theme_row)

        self._root.addWidget(_hline())

    # ── Color-dependent content (rebuilt on every theme change) ─────────────

    def _refresh_colors(self):
        """Tear down and rebuild all color-dependent widgets."""
        if self._content_widget is not None:
            self._root.removeWidget(self._content_widget)
            self._content_widget.hide()
            self._content_widget.deleteLater()

        self._content_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self._content_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── State reference table ───────────────────────────────────────
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        headers = ['', 'State', 'log level', 'Theme attribute', 'Description']
        for col, header in enumerate(headers):
            lbl = QtWidgets.QLabel(f'<b>{header}</b>')
            grid.addWidget(lbl, 0, col)

        states = StatusPalette.as_states()
        for row, (name, color) in enumerate(states, start=1):
            # LED fixed to its own state for visual reference
            led = MultistateLED(states=[(name, color)], size=24)
            led.set_state(name)
            grid.addWidget(led, row, 0, QtCore.Qt.AlignmentFlag.AlignCenter)

            # State name coloured to match the LED
            name_lbl = QtWidgets.QLabel(f'<b>{name}</b>')
            name_lbl.setStyleSheet(
                f'color: {color.name()}; font-family: monospace; font-size: 13px;'
            )
            grid.addWidget(name_lbl, row, 1)

            # Logging analogy
            log_lbl = QtWidgets.QLabel(_LOG_LEVEL.get(name, '—'))
            log_lbl.setStyleSheet('font-size: 11px; color: gray;')
            grid.addWidget(log_lbl, row, 2)

            # Theme attribute
            _, attr, _ = _DEFINITIONS[row - 1]
            attr_lbl = QtWidgets.QLabel(f'theme.<i>{attr}</i>')
            attr_lbl.setStyleSheet('color: gray; font-size: 11px;')
            grid.addWidget(attr_lbl, row, 3)

            # Description
            desc_lbl = QtWidgets.QLabel(_DESCRIPTIONS[name])
            desc_lbl.setWordWrap(True)
            grid.addWidget(desc_lbl, row, 4)

        grid.setColumnStretch(4, 1)
        layout.addLayout(grid)

        layout.addWidget(_hline())

        # ── Live demo ───────────────────────────────────────────────────
        demo_box = QtWidgets.QGroupBox('Live demo — click the LED to cycle through states')
        demo_layout = QtWidgets.QHBoxLayout(demo_box)
        demo_layout.setSpacing(12)

        demo_led = MultistateLED(
            states=StatusPalette.as_states(),
            readonly=False,
            clickable_cycle=True,
            size=32,
        )
        init_name = demo_led.get_state()
        init_color = StatusPalette.color(init_name)

        demo_state_lbl = QtWidgets.QLabel(f'<b>{init_name}</b>')
        demo_state_lbl.setStyleSheet(f'color: {init_color.name()};')
        demo_state_lbl.setMinimumWidth(80)

        demo_desc_lbl = QtWidgets.QLabel(_DESCRIPTIONS[init_name])
        demo_desc_lbl.setWordWrap(True)

        def _on_state_change(state_name: str):
            color = StatusPalette.color(state_name)
            demo_state_lbl.setText(f'<b>{state_name}</b>')
            demo_state_lbl.setStyleSheet(f'color: {color.name()};')
            demo_desc_lbl.setText(_DESCRIPTIONS[state_name])

        demo_led.state_changed.connect(_on_state_change)

        demo_layout.addWidget(demo_led)
        demo_layout.addWidget(demo_state_lbl)
        demo_layout.addWidget(demo_desc_lbl, stretch=1)
        layout.addWidget(demo_box)

        # ── Usage snippet ───────────────────────────────────────────────
        layout.addWidget(_hline())
        layout.addWidget(QtWidgets.QLabel('<b>Usage</b>'))

        snippet = QtWidgets.QPlainTextEdit()
        snippet.setReadOnly(True)
        snippet.setMaximumHeight(110)
        snippet.setFont(QtGui.QFont('monospace'))
        snippet.setPlainText(
            'from pymodaq_gui.utils.status_palette import StatusPalette\n'
            'from pymodaq_gui.utils.widgets.multistate_led import MultistateLED\n\n'
            '# In a widget\n'
            'led = MultistateLED(states=StatusPalette.as_states())\n'
            "led.set_state('running')\n\n"
            '# In a parameter tree\n'
            "params = [{'name': 'status', 'type': 'action_multistate_led',\n"
            "           'value': 'off', 'states': StatusPalette.as_states()}]"
        )
        layout.addWidget(snippet)

        self._root.addWidget(self._content_widget)

    # ── Slot ────────────────────────────────────────────────────────────────

    def _on_theme_changed(self, name: str):
        try:
            qt_themes.set_theme(name)
        except Exception:
            pass
        self._refresh_colors()


def _hline() -> QtWidgets.QFrame:
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
    return line


def main():
    from pymodaq_gui.qt_utils import mkQApp
    app = mkQApp('StatusPaletteProposal')
    w = StatusPaletteWidget()
    w.resize(820, 580)
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

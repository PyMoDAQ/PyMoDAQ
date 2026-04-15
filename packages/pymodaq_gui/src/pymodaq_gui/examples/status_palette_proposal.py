"""
PyMoDAQ Status Color Palette — Community Proposal
==================================================

Run this file directly to display the proposed color convention::

    python status_palette_proposal.py

The widget shows all five states with their LED color, name, and
intended meaning.  Colors are drawn from the active qt_themes theme,
so run with ``QT_THEMES=dark`` / ``QT_THEMES=light`` (or via PyMoDAQ
settings) to see how they adapt.
"""

import sys
from qtpy import QtCore, QtGui, QtWidgets

from pymodaq_gui.utils.widgets.multistate_led import MultistateLED
from pymodaq_gui.utils.status_palette import StatusPalette, _DEFINITIONS


# Human-readable descriptions for each state
_DESCRIPTIONS = {
    'off':     'Module absent, not initialized, or hardware not yet connected.',
    'idle':    'Initialized and ready — waiting for a user command or trigger.',
    'running': 'A command is in flight: moving, acquiring, or processing data.',
    'warning': 'Non-fatal issue detected — still functional, attention advised.',
    'error':   'An operation failed. Module may still recover, attention advised.',    
    'critical':   'Fault occurred — last operation failed or hardware error.',
}


class StatusPaletteWidget(QtWidgets.QWidget):
    """Standalone reference widget for the PyMoDAQ status color proposal."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('PyMoDAQ — Status Color Palette Proposal')
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        # ── Title ──────────────────────────────────────────────────────
        title = QtWidgets.QLabel('PyMoDAQ — Proposed Status Color Convention')
        font = title.font()
        font.setPointSize(font.pointSize() + 3)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        subtitle = QtWidgets.QLabel(
            'A shared five-state vocabulary for LEDs, icons, and status bars.\n'
            'Colors adapt to the active qt_themes dark / light theme.'
        )
        subtitle.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        root.addWidget(_hline())

        # ── State rows ─────────────────────────────────────────────────
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        # Header row
        for col, header in enumerate(['', 'State', 'Theme attribute', 'Description']):
            lbl = QtWidgets.QLabel(f'<b>{header}</b>')
            grid.addWidget(lbl, 0, col)

        states = StatusPalette.as_states()
        for row, (name, color) in enumerate(states, start=1):
            # LED — fixed to this single state, full-size for visibility
            led = MultistateLED(states=[(name, color)], size=24)
            led.set_state(name)
            grid.addWidget(led, row, 0, QtCore.Qt.AlignmentFlag.AlignCenter)

            # State name — bold, colored to match the LED
            name_lbl = QtWidgets.QLabel(f'<b>{name}</b>')
            name_lbl.setStyleSheet(
                f'color: {color.name()}; font-family: monospace; font-size: 13px;'
            )
            grid.addWidget(name_lbl, row, 1)

            # Theme attribute
            _, attr, _ = _DEFINITIONS[row - 1]
            attr_lbl = QtWidgets.QLabel(f'theme.<i>{attr}</i>')
            attr_lbl.setStyleSheet('color: gray; font-size: 11px;')
            grid.addWidget(attr_lbl, row, 2)

            # Description
            desc_lbl = QtWidgets.QLabel(_DESCRIPTIONS[name])
            desc_lbl.setWordWrap(True)
            grid.addWidget(desc_lbl, row, 3)

        grid.setColumnStretch(3, 1)
        root.addLayout(grid)

        root.addWidget(_hline())

        # ── Live demo row ───────────────────────────────────────────────
        demo_box = QtWidgets.QGroupBox('Live demo — click the LED to cycle through states')
        demo_layout = QtWidgets.QHBoxLayout(demo_box)
        demo_layout.setSpacing(12)

        demo_led = MultistateLED(
            states=StatusPalette.as_states(),
            readonly=False,
            clickable_cycle=True,
            size=32,
        )
        demo_state_lbl = QtWidgets.QLabel(f'<b>{demo_led.get_state()}</b>')
        demo_state_lbl.setMinimumWidth(80)
        demo_desc_lbl = QtWidgets.QLabel(_DESCRIPTIONS[demo_led.get_state()])
        demo_desc_lbl.setWordWrap(True)

        def _on_state_change(name):
            color = StatusPalette.color(name)
            demo_state_lbl.setText(f'<b>{name}</b>')
            demo_state_lbl.setStyleSheet(f'color: {color.name()};')
            demo_desc_lbl.setText(_DESCRIPTIONS[name])

        demo_led.state_changed.connect(_on_state_change)

        demo_layout.addWidget(demo_led)
        demo_layout.addWidget(demo_state_lbl)
        demo_layout.addWidget(demo_desc_lbl, stretch=1)
        root.addWidget(demo_box)

        # ── Usage snippet ───────────────────────────────────────────────
        root.addWidget(_hline())

        snippet_lbl = QtWidgets.QLabel('<b>Usage</b>')
        root.addWidget(snippet_lbl)

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
        root.addWidget(snippet)


def _hline() -> QtWidgets.QFrame:
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
    return line


def main():
    from pymodaq_gui.qt_utils import mkQApp
    app = mkQApp('StatusPaletteProposal')
    w = StatusPaletteWidget()
    w.resize(780, 520)
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

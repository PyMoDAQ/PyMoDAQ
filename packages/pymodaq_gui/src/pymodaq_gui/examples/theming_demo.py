"""
PyMoDAQ Theming Demo — Status Color Palette + Material Icon Toolbar
=====================================================================

Run this file directly::

    python theming_demo.py

Switching theme at runtime
--------------------------
Switching theme (combobox, or the Play button to auto-cycle through every
``qt_themes`` theme) calls ``pymodaq_gui.qt_utils.apply_theme(name)``, which
sets the palette and style, keeps PyMoDAQ's dark-theme checkbox rule and
emits ``theme_signaller.theme_changed``. Then:

- the toolbar, built *once* with an ``ActionManager``, re-colors itself.
  ``MaterialIcon`` (pymodaq_gui.resources.material_icons) bakes the palette
  color into a pixmap at construction (see ``SVGIcon._init_colors``), so each
  action keeps what its icon is made of and rebuilds it with the current theme
  colors on ``theme_changed`` (``ActionManager.refresh_icons()`` does it on
  demand). Colors given by name (``ThemeColor.GREEN``, ``'green'``,
  ``StatusPalette.role('running')``) follow the new theme; literal colors
  (``'#3f8f7f'``) are kept, as is any color of an action created with
  ``follow_theme=False``;
- the status-color reference table and the live ``MultistateLED`` demo
  (community-proposed six-state convention, see ``utils/status_palette.py``)
  are plain widgets with colors computed once, so they are rebuilt.

The toolbar also shows two independent, non-animated uses of icon color:

- a *momentary* action (Refresh / Save / Stop) tinted from the same
  six-state ``StatusPalette`` convention as the LEDs above it;
- a *checkable* action (Pause / Grid / Zoom) whose icon carries two distinct
  pixmaps, one per ``QIcon.State`` (On/Off), from ``icon_checked_color``.
  Qt swaps between them on its own from ``QAction.isChecked()``; click a
  toggle button to see it.
"""

import sys

import qt_themes
from qtpy import QtCore, QtGui, QtWidgets

from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.qt_utils import apply_theme
from pymodaq_gui.utils.widgets.multistate_led import MultistateLED
from pymodaq_gui.utils.status_palette import StatusPalette, _DEFINITIONS


# ── Available themes ────────────────────────────────────────────────────────
try:
    _THEME_NAMES: list[str] = sorted(qt_themes.get_themes().keys())
except AttributeError:
    _THEME_NAMES = [
        'atom_one', 'blender',
        'catppuccin_frappe', 'catppuccin_latte',
        'catppuccin_macchiato', 'catppuccin_mocha',
        'dracula', 'github_dark', 'github_light',
        'modern_dark', 'modern_light', 'monokai',
        'nord', 'one_dark_two',
    ]


# ── Status-palette reference data ───────────────────────────────────────────

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


# ── Icon toolbar data ────────────────────────────────────────────────────────

# (icon name, label, tooltip, status_key, checkable, checked_color, start_checked)
#
# icon names all confirmed present in resources/icons.toml.
#
# Two independent, non-animated uses of color:
#  - status_key: a *momentary* action tinted from the six-state StatusPalette
#    convention -- refresh/save/stop always show that color, checked or not.
#  - checkable + checked_color: a *toggle* action whose icon literally has two
#    pixmaps, one per QIcon.State (On/Off) -- exactly what action_manager.py's
#    own QAction does for icon_checked/icon_unchecked. Qt swaps between them
#    natively based on QAction.isChecked(); no timer, no manual repaint.
# Theme colors follow theme changes; _ACCENT_ON, a literal, is kept.
_ACCENT_ON = '#3f8f7f'  # generic "toggled on" tint for plain UI toggles (not a device state)
_STATUS_NAMES = {'off', 'idle', 'running', 'warning', 'error', 'critical'}


def _resolve_checked_color(spec: str) -> str:
    """A checked_color entry is either a StatusPalette state name or a literal hex."""
    if spec in _STATUS_NAMES:
        return StatusPalette.role(spec)  # a theme colour name: follows the theme
    return spec


_TOOLBAR_ACTIONS = [
    # icon,          label,     tooltip,                                    status_key, checkable, checked_color, start_checked
    ('home',         'Home',    'Go to the dashboard home',                 None,       False, None,         False),
    ('search',       'Search',  'Search modules',                           None,       False, None,         False),
    ('tune',         'Tune',    'Open actuator settings',                   None,       False, None,         False),
    ('settings',     'Settings','Open preferences',                         None,       False, None,         False),
    ('refresh',      'Refresh', 'Refresh the view — acquisition in flight', 'running',  False, None,         False),
    ('save',         'Save',    'Save the current state — ready',           'idle',     False, None,         False),
    ('pause_circle', 'Pause',   'Toggle pause — checked means paused',      None,       True,  'warning',    False),
    ('stop',         'Stop',    'Stop the current module — critical fault', 'critical', False, None,         False),
    ('grid_on',      'Grid',    'Toggle the grid overlay',                  None,       True,  _ACCENT_ON,   True),
    ('zoom_in',      'Zoom',    'Toggle zoom lock',                         None,       True,  _ACCENT_ON,   False),
    ('folder_open',  'Open',    'Open a file',                              None,       False, None,         False),
]


class ThemingDemo(QtWidgets.QWidget):
    """Standalone demo: status-color LEDs + a MaterialIcon toolbar, both retheme correctly."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('PyMoDAQ — Theming Demo (status colors + icons)')
        self._content_widget = None
        self._build_skeleton()
        self._build_toolbar()
        self._rebuild_status_widgets()

    # ── Fixed structure (built once) ────────────────────────────────────────

    def _build_skeleton(self):
        self._root = QtWidgets.QVBoxLayout(self)
        self._root.setSpacing(12)
        self._root.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QtWidgets.QLabel('PyMoDAQ — Theming Demo')
        font = title.font()
        font.setPointSize(font.pointSize() + 3)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._root.addWidget(title)

        subtitle = QtWidgets.QLabel(
            'A shared six-state status vocabulary for LEDs, icons, and status bars,\n'
            'plus a MaterialIcon toolbar built once with an ActionManager: its icons re-color\n'
            'themselves on every theme change. Use the combobox below to switch themes live.'
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

        self._play_button = QtWidgets.QPushButton('▶ Play')
        self._play_button.setCheckable(True)
        self._play_button.setToolTip('Cycle through all themes automatically')
        self._play_button.toggled.connect(self._on_play_toggled)
        theme_row.addWidget(self._play_button)

        theme_row.addWidget(QtWidgets.QLabel('every'))
        self._interval_spin = QtWidgets.QSpinBox()
        self._interval_spin.setRange(200, 10000)
        self._interval_spin.setSingleStep(100)
        self._interval_spin.setValue(1200)
        self._interval_spin.setSuffix(' ms')
        self._interval_spin.valueChanged.connect(self._on_interval_changed)
        theme_row.addWidget(self._interval_spin)

        theme_row.addStretch()
        self._root.addLayout(theme_row)

        self._cycle_timer = QtCore.QTimer(self)
        self._cycle_timer.setInterval(self._interval_spin.value())
        self._cycle_timer.timeout.connect(self._cycle_to_next_theme)

        self._root.addWidget(_hline())

        self._toolbar_layout = QtWidgets.QVBoxLayout()
        self._root.addLayout(self._toolbar_layout)

        # State table + LED demo + snippet easily exceed a
        # reasonable fixed window height once the table rows are sized
        # correctly (see _rebuild_status_widgets); scroll rather than let anything
        # after the table get squeezed into whatever space is left.
        self._scroll_area = QtWidgets.QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self._root.addWidget(self._scroll_area, 1)

    def _build_toolbar(self):
        """Material icon toolbar, built once: its actions re-color themselves on theme change."""
        toolbar_box = QtWidgets.QGroupBox(
            'Material icon toolbar — status-tinted + checkable actions'
        )
        toolbar_layout = QtWidgets.QVBoxLayout(toolbar_box)

        toolbar = QtWidgets.QToolBar()
        toolbar.setIconSize(QtCore.QSize(28, 28))
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self._action_manager = ActionManager(toolbar=toolbar)

        for (icon_name, label, tooltip, status_key, checkable,
             checked_color, start_checked) in _TOOLBAR_ACTIONS:
            # Theme colours by name (StatusPalette.role -> ThemeColor): they follow the theme
            self._action_manager.add_action(
                icon_name, label, icon_name, tip=tooltip,
                checkable=checkable, checked=start_checked,
                icon_color=StatusPalette.role(status_key) if status_key is not None else None,
                icon_checked_color=_resolve_checked_color(checked_color) if checkable else None,
            )

        toolbar_layout.addWidget(toolbar)
        self._toolbar_layout.addWidget(toolbar_box)

    # ── Color-dependent widgets (rebuilt on every theme change) ─────────────

    def _rebuild_status_widgets(self):
        """Tear down and rebuild the status table and LED demo, whose colors are computed once."""
        # QScrollArea.setWidget() below takes ownership of the new widget and
        # deletes whatever widget it previously held -- no manual teardown needed.
        self._content_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self._content_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── State reference table ───────────────────────────────────────
        # Built from QHBoxLayout rows stacked in a QVBoxLayout, not a
        # QGridLayout: QGridLayout does not reliably size a row to a
        # word-wrapped QLabel's real (multi-line) height, which made
        # longer descriptions overlap the row below. A column of QHBoxLayout
        # rows does not have that limitation.
        col_widths = [28, 90, 90, 150]  # LED, State, log level, Theme attribute

        header_row = QtWidgets.QHBoxLayout()
        header_row.setSpacing(16)
        for header, width in zip(['', 'State', 'log level', 'Theme attribute'], col_widths):
            lbl = QtWidgets.QLabel(f'<b>{header}</b>')
            lbl.setFixedWidth(width)
            header_row.addWidget(lbl)
        header_row.addWidget(QtWidgets.QLabel('<b>Description</b>'), 1)
        layout.addLayout(header_row)

        states = StatusPalette.as_states()
        for (name, color), (_, attr, _) in zip(states, _DEFINITIONS):
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(16)

            # LED fixed to its own state for visual reference
            led = MultistateLED(states=[(name, color)], size=24)
            led.set_state(name)
            led.setFixedWidth(col_widths[0])
            row.addWidget(led)

            # State name coloured to match the LED
            name_lbl = QtWidgets.QLabel(f'<b>{name}</b>')
            name_lbl.setStyleSheet(
                f'color: {color.name()}; font-family: monospace; font-size: 13px;'
            )
            name_lbl.setFixedWidth(col_widths[1])
            row.addWidget(name_lbl)

            # Logging analogy
            log_lbl = QtWidgets.QLabel(_LOG_LEVEL.get(name, '—'))
            log_lbl.setStyleSheet('font-size: 11px; color: gray;')
            log_lbl.setFixedWidth(col_widths[2])
            row.addWidget(log_lbl)

            # Theme attribute
            attr_lbl = QtWidgets.QLabel(f'theme.<i>{attr}</i>')
            attr_lbl.setStyleSheet('color: gray; font-size: 11px;')
            attr_lbl.setFixedWidth(col_widths[3])
            row.addWidget(attr_lbl)

            # Description -- wraps onto 2 lines for the longer entries; the
            # row's own height follows it correctly since this is a linear
            # (not grid) layout.
            desc_lbl = QtWidgets.QLabel(_DESCRIPTIONS[name])
            desc_lbl.setWordWrap(True)
            row.addWidget(desc_lbl, 1)

            layout.addLayout(row)

        layout.addWidget(_hline())

        # ── Live LED demo ───────────────────────────────────────────────
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

        layout.addWidget(_hline())

        # ── Usage snippet ───────────────────────────────────────────────
        layout.addWidget(QtWidgets.QLabel('<b>Usage</b>'))

        snippet = QtWidgets.QPlainTextEdit()
        snippet.setReadOnly(True)
        snippet.setMaximumHeight(200)
        snippet.setFont(QtGui.QFont('monospace'))
        snippet.setPlainText(
            'from pymodaq_gui.utils.status_palette import StatusPalette\n'
            'from pymodaq_gui.utils.widgets.multistate_led import MultistateLED\n'
            'from pymodaq_gui.managers.action_manager import ActionManager\n'
            'from pymodaq_gui.qt_utils import apply_theme\n\n'
            '# LED, in a widget\n'
            'led = MultistateLED(states=StatusPalette.as_states())\n'
            "led.set_state('running')\n\n"
            '# LED, in a parameter tree\n'
            "params = [{'name': 'status', 'type': 'action_multistate_led',\n"
            "           'value': 'off', 'states': StatusPalette.as_states()}]\n\n"
            "# Action tinted with a status color, following theme changes\n"
            "manager.add_action('refresh', 'Refresh', 'refresh',\n"
            "                   icon_color=StatusPalette.role('running'))\n"
            "apply_theme('nord')  # icons follow, no rebuild needed"
        )
        layout.addWidget(snippet)

        self._scroll_area.setWidget(self._content_widget)

        self.setWindowTitle(
            f'PyMoDAQ — Theming Demo (status colors + icons) — {self._theme_combo.currentText()}'
        )

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_theme_changed(self, name: str):
        if apply_theme(name) is None:
            return
        self._rebuild_status_widgets()

    def _on_play_toggled(self, checked: bool):
        if checked:
            self._play_button.setText('■ Stop')
            self._cycle_timer.start()
        else:
            self._play_button.setText('▶ Play')
            self._cycle_timer.stop()

    def _on_interval_changed(self, value: int):
        self._cycle_timer.setInterval(value)

    def _cycle_to_next_theme(self):
        count = self._theme_combo.count()
        if count == 0:
            return
        next_index = (self._theme_combo.currentIndex() + 1) % count
        self._theme_combo.setCurrentIndex(next_index)

    def closeEvent(self, event):
        self._cycle_timer.stop()
        super().closeEvent(event)


def _hline() -> QtWidgets.QFrame:
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
    return line


def main():
    from pymodaq_gui.qt_utils import mkQApp
    app = mkQApp('ThemingDemo')
    w = ThemingDemo()
    w.resize(880, 820)
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

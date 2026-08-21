"""Manager for compact docks with stacked module rows.

Three-layer hierarchy
---------------------
CompactDockManager   – generic row manager, no module knowledge
ModuleCompactDock    – adds module awareness, alignment, lock wiring
ActuatorCompactDock  – actuator-specific alignment/actions
DetectorCompactDock  – detector-specific alignment/actions
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Qt, Signal
from pymodaq_gui.utils import Dock, DockArea
from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.utils.styling import create_icon
from pymodaq_gui.utils.widgets.collapsible_widget import CollapsibleWidget

try:
    from pymodaq_utils.config import GlobalConfig as _PymConfig
    _pymodaq_config = _PymConfig()
except Exception:
    _pymodaq_config = None

if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer


# ── Control-panel placement ────────────────────────────────────────────────────
# Maps a position name to the parameters needed to build the CollapsibleWidget
# and the orientation of the control toolbar.
#
#   direction            – collapse/expand direction passed to CollapsibleWidget
#   content_before_toggle – True  → [content][toggle]   (right / top panels)
#                           False → [toggle][content]   (left  / bottom panels)
#   horizontal           – True  → modules_row uses QHBoxLayout (left/right)
#                           False → outer_vlay puts collapsible above/below main
#   toggle_symbol        – arrow char shown when the panel is *collapsed*
#   toolbar_orient       – Qt orientation of the control toolbar
#
_PANEL_POSITIONS: dict = {
    'right':  dict(direction='left', content_before_toggle=True,
                   horizontal=True, toggle_symbol='◀',
                   toolbar_orient=Qt.Orientation.Vertical),
    'left':   dict(direction='right', content_before_toggle=False,
                   horizontal=True, toggle_symbol='▶',
                   toolbar_orient=Qt.Orientation.Vertical),
    'top':    dict(direction='bottom', content_before_toggle=False,
                   horizontal=False, toggle_symbol='▼',
                   toolbar_orient=Qt.Orientation.Horizontal),
    'bottom': dict(direction='top', content_before_toggle=True,
                   horizontal=False, toggle_symbol='▲',
                   toolbar_orient=Qt.Orientation.Horizontal),
}
_POSITION_CYCLE = ('right', 'bottom', 'left', 'top')

# Maps each position to the icon that represents it visually.
# 'dock_to_left' shows the panel on the left; its h-mirror = panel on the right.
# 'dock_to_bottom' shows the panel at the bottom; its v-mirror = panel at the top.
_POSITION_ICONS: dict = {
    'left':  dict(icon_name='dock_to_left', flip_h=True, flip_v=False),
    'right':   dict(icon_name='dock_to_left', flip_h=False, flip_v=False),
    'bottom': dict(icon_name='dock_to_bottom', flip_h=False, flip_v=False),
    'top':    dict(icon_name='dock_to_bottom', flip_h=False, flip_v=True),
}


def _read_panel_position() -> str:
    """Read the saved control-panel position from PyMoDAQ config (default: 'right')."""
    try:
        pos = _pymodaq_config('pymodaq', 'compact_dock', 'control_panel_position')
        if pos in _PANEL_POSITIONS:
            return pos
    except Exception:
        pass
    return 'right'


def _save_panel_position(position: str) -> None:
    """Persist the control-panel position to PyMoDAQ config (best-effort)."""
    try:
        _pymodaq_config['pymodaq', 'compact_dock', 'control_panel_position'] = position
    except Exception:
        pass


# Action names that should be disabled while the dock-level lock is active.
LOCKABLE_ACTIONS = frozenset({
    # actuator — buttons
    'move_abs', 'move_abs_2', 'move_rel_plus', 'move_rel_minus', 'stop',
    # actuator — spinboxes
    'abs_green', 'abs_red', 'rel_move',
    # detector
    'snap', 'grab', 'save_current', 'background_snap', 'background_subtract',
})


@dataclass
class _RowData:
    toolbar: QtWidgets.QWidget
    module: object = None   # DAQ_Move | DAQ_Viewer | None


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — generic base
# ─────────────────────────────────────────────────────────────────────────────

class CompactDockManager(QtCore.QObject, ActionManager):
    """Generic compact-dock manager.

    Manages a vertical (or horizontal) stack of toolbar rows inside a
    :class:`QMainWindow` embedded in a :class:`Dock`. 

    Signals
    -------
    lock_changed(bool)
        Emitted when the lock action is toggled.  *True* = locked.
    """

    lock_changed = Signal(bool)

    def __init__(self, title: str, dockarea: DockArea,
                 orientation: Qt.Orientation = Qt.Orientation.Vertical, **kwargs):
        """
        Parameters
        ----------
        title:
            Title of the dock.
        dockarea:
            Parent dock area.
        orientation:
            Vertical → top-to-bottom row stacking; Horizontal → left-to-right.
        """
        QtCore.QObject.__init__(self)

        self.dock = Dock(title)
        self.dockarea = dockarea
        self.orientation = orientation

        self.toolbar_area = (
            Qt.ToolBarArea.TopToolBarArea if orientation == Qt.Orientation.Vertical
            else Qt.ToolBarArea.LeftToolBarArea
        )

        # ── Control toolbar (collective actions, pinned to the collapsible panel)
        self.control_toolbar = QtWidgets.QToolBar("Controls")
        self.control_toolbar.setFloatable(False)
        self.control_toolbar.setMovable(False)

        # ── Outer container ────────────────────────────────────────────────────
        self._outer_container = QtWidgets.QWidget()
        self._outer_vlay = QtWidgets.QVBoxLayout(self._outer_container)
        self._outer_vlay.setContentsMargins(0, 0, 0, 0)
        self._outer_vlay.setSpacing(0)
        self.dock.addWidget(self._outer_container)

        # QMainWindow handles toolbar drag-and-drop for module rows.
        # Its position in the layout is determined by _apply_position.
        self.main_window = QtWidgets.QMainWindow()

        # Zero-height central widget so QMainWindow shrinks to its toolbar rows
        _central = QtWidgets.QWidget()
        _central.setFixedHeight(0)
        self.main_window.setCentralWidget(_central)

        # Will be built/rebuilt by _apply_position
        self.collapsible_widget = None
        self._modules_row = None
        self._panel_position = None
        self._position_btn = None   # QToolButton created in _create_actions

        ActionManager.__init__(self, toolbar=self.control_toolbar)

        self._rows: dict[QtWidgets.QWidget, _RowData] = {}
        self.is_locked = False
        self._create_actions()

        # Apply initial position from config
        self._apply_position(_read_panel_position())

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def modules(self):
        """Live view of all non-None module instances in row order."""
        return [r.module for r in self._rows.values() if r.module is not None]

    # ── Action setup ──────────────────────────────────────────────────────────

    def _create_actions(self):
        """Create the lock action and the position picker.  Subclasses call ``super()`` first."""
        self.add_action('lock', 'Lock', icon_name='lock_open_right', checkable=True,
                        toolbar=self.control_toolbar,
                        tip='Lock/Unlock all module actions',
                        icon_checked='lock', icon_color='green', icon_checked_color='orange')
        self.connect_action('lock', self.toggle_lock)

        # ── Position picker: QToolButton with a drop-down menu ─────────────────
        # Each entry shows the icon for that position and checks itself when active.
        self._position_menu = QtWidgets.QMenu(self._position_btn)
        _labels = {'right': 'Dock right', 'left': 'Dock left',
                   'top': 'Dock top', 'bottom': 'Dock bottom'}
        for pos, cfg in _POSITION_ICONS.items():
            icon = create_icon(cfg['icon_name'], flip_h=cfg['flip_h'], flip_v=cfg['flip_v'])
            act = self._position_menu.addAction(icon, _labels[pos])
            act.setCheckable(True)
            act.setData(pos)
            act.triggered.connect(lambda checked, p=pos: self._apply_position(p))

        self._position_btn = QtWidgets.QToolButton()
        self._position_btn.setMenu(self._position_menu)
        self._position_btn.setToolTip('Control panel position')
        self._position_btn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.control_toolbar.addWidget(self._position_btn)

    # ── Row management ────────────────────────────────────────────────────────

    def _configure_toolbar(self, toolbar: QtWidgets.QToolBar):
        toolbar.setFloatable(False)
        toolbar.setMovable(True)
        toolbar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        toolbar.setAllowedAreas(self.toolbar_area)
        toolbar.setOrientation(
            Qt.Orientation.Horizontal if self.orientation == Qt.Orientation.Vertical
            else Qt.Orientation.Vertical,
        )

    def add_widget(self, widget: QtWidgets.QWidget,
                   create_toolbar: bool = True,
                   module=None):
        """Add a row to the compact dock.

        Parameters
        ----------
        widget:
            Widget to display.  When *create_toolbar* is False this must
            already be a :class:`QToolBar`.
        create_toolbar:
            If True a wrapper :class:`QToolBar` is created around *widget*.
            If False *widget* itself is used as the toolbar row.
        module:
            Associated module instance (stored for external inspection via
            :attr:`modules`).  The base class never calls methods on it.
        """
        if create_toolbar:
            toolbar = QtWidgets.QToolBar()
            toolbar.addWidget(widget)
        else:
            toolbar = widget

        self._configure_toolbar(toolbar)

        if self._rows:
            self.main_window.addToolBarBreak(self.toolbar_area)
        self.main_window.addToolBar(self.toolbar_area, toolbar)

        self._rows[widget] = _RowData(toolbar=toolbar, module=module)

    def remove_widget(self, widget: QtWidgets.QWidget) -> bool:
        """Remove a row from the compact dock.

        Returns True when the dock is now empty.
        """
        keys = list(self._rows.keys())
        if widget not in keys:
            return len(self._rows) == 0

        idx = keys.index(widget)
        row = self._rows.pop(widget)

        # removeToolBarBreak(t) removes the break *before* t.
        if idx > 0:
            self.main_window.removeToolBarBreak(row.toolbar)
        elif len(keys) > 1:
            # First row removed; orphaned break now sits before the new first row.
            self.main_window.removeToolBarBreak(self._rows[keys[1]].toolbar)

        self.main_window.removeToolBar(row.toolbar)

        # Only delete the wrapper toolbar, not the module's own toolbar.
        if widget is not row.toolbar:
            row.toolbar.deleteLater()

        return len(self._rows) == 0

    # ── Dock positioning ───────────────────────────────────────────────────────

    def show(self, position: str = "top", relative_to: Optional[Dock] = None):
        """Show the dock in the dockarea."""
        if relative_to:
            self.dockarea.addDock(self.dock, position, relative_to)
        else:
            self.dockarea.addDock(self.dock, position)

    def close(self):
        """Close and clean up the dock."""
        self.dock.close()

    # ── Lock ──────────────────────────────────────────────────────────────────

    def toggle_lock(self, checked: bool):
        """Set the lock state and emit :attr:`lock_changed`."""
        self.is_locked = checked
        self.lock_changed.emit(checked)

    # ── Collapsible panel position ─────────────────────────────────────────────

    def _apply_position(self, position: str):
        """Rebuild the collapsible-panel layout for *position*.

        Tears down the existing ``collapsible_widget`` and ``_modules_row``
        (if any), then recreates them according to ``_PANEL_POSITIONS[position]``.
        Saves the new position to config.
        """
        if position not in _PANEL_POSITIONS:
            position = 'right'
        params = _PANEL_POSITIONS[position]

        # -- Tear down existing layout -----------------------------------
        # Detach main_window from whatever layout it currently lives in.
        self.main_window.setParent(None)

        if self.collapsible_widget is not None:
            # Save control_toolbar before deleting the collapsible wrapper.
            self.control_toolbar.setParent(None)
            self.collapsible_widget.setParent(None)
            self.collapsible_widget.deleteLater()
            self.collapsible_widget = None

        if self._modules_row is not None:
            self._modules_row.setParent(None)
            self._modules_row.deleteLater()
            self._modules_row = None

        # Flush any widgets still referenced by the outer layout.
        while self._outer_vlay.count():
            item = self._outer_vlay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

        # -- Update control_toolbar orientation --------------------------
        self.control_toolbar.setOrientation(params['toolbar_orient'])

        # -- Create new collapsible widget -------------------------------
        # toggle_symbol is the collapsed-state arrow; CollapsibleWidget flips
        # it via symbol_map when the panel is expanded.
        toggle_btn = QtWidgets.QPushButton(params['toggle_symbol'])
        if params['horizontal']:
            toggle_btn.setFixedWidth(16)
        else:
            toggle_btn.setFixedHeight(16)

        self.collapsible_widget = CollapsibleWidget(
            toggle_widget=toggle_btn,
            collapsible_widget=self.control_toolbar,
            direction=params['direction'],
            content_before_toggle=params['content_before_toggle'],
        )

        # -- Place widgets in the outer layout ---------------------------
        if params['horizontal']:
            # Left / right: collapsible panel sits beside the toolbar rows.
            self._modules_row = QtWidgets.QWidget()
            hlay = QtWidgets.QHBoxLayout(self._modules_row)
            hlay.setContentsMargins(0, 0, 0, 0)
            hlay.setSpacing(0)
            if position == 'right':
                hlay.addWidget(self.main_window)
                hlay.addWidget(self.collapsible_widget)
            else:  # 'left'
                hlay.addWidget(self.collapsible_widget)
                hlay.addWidget(self.main_window)
            self._outer_vlay.addWidget(self._modules_row)
        else:
            # Top / bottom: collapsible panel stacks above/below toolbar rows.
            self._modules_row = None
            if position == 'top':
                self._outer_vlay.addWidget(self.collapsible_widget)
                self._outer_vlay.addWidget(self.main_window)
            else:  # 'bottom'
                self._outer_vlay.addWidget(self.main_window)
                self._outer_vlay.addWidget(self.collapsible_widget)

        self._panel_position = position
        _save_panel_position(position)
        self._update_position_btn_icon()

    def _update_position_btn_icon(self):
        """Sync the position button's icon and menu check-marks with the current position."""
        if self._position_btn is None:
            return
        cfg = _POSITION_ICONS.get(self._panel_position, _POSITION_ICONS['right'])
        self._position_btn.setIcon(
            create_icon(cfg['icon_name'], flip_h=cfg['flip_h'], flip_v=cfg['flip_v']),
        )
        menu = self._position_btn.menu()
        if menu is not None:
            for act in menu.actions():
                act.setChecked(act.data() == self._panel_position)

    def _cycle_position(self):
        """Advance to the next position in :data:`_POSITION_CYCLE`."""
        try:
            idx = _POSITION_CYCLE.index(self._panel_position)
        except ValueError:
            idx = -1
        next_pos = _POSITION_CYCLE[(idx + 1) % len(_POSITION_CYCLE)]
        self._apply_position(next_pos)


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — module-aware middle layer
# ─────────────────────────────────────────────────────────────────────────────

class ModuleCompactDock(CompactDockManager):
    """Adds module awareness, cross-row alignment, and lock wiring.

    Subclasses provide alignment hints via :meth:`_get_module_align_widgets`.
    """

    def __init__(self, title: str, dockarea: DockArea,
                 orientation: Qt.Orientation = Qt.Orientation.Vertical):
        super().__init__(title, dockarea, orientation)
        self.lock_changed.connect(self._apply_lock)

    # ── Public API ────────────────────────────────────────────────────────────

    def add_module(self, module):
        """Add a module's toolbar as a new row."""
        super().add_widget(module.ui.toolbar, create_toolbar=False, module=module)
        self._update_alignment()

    def remove_module(self, module) -> bool:
        """Remove a module row.  Returns True when the dock is now empty."""
        is_empty = super().remove_widget(module.ui.toolbar)
        self._update_alignment()
        return is_empty

    # ── Alignment hook ────────────────────────────────────────────────────────

    def _get_module_align_widgets(self, module) -> dict:
        """Return ``{group_name: widget}`` pairs for cross-row alignment.

        Override in subclasses to supply the actual widgets.
        """
        return {}

    def _update_alignment(self):
        """Set a common fixed width for each alignment group across all rows."""
        groups: dict[str, list[QtWidgets.QWidget]] = {}
        for module in self.modules:
            for name, widget in self._get_module_align_widgets(module).items():
                groups.setdefault(name, []).append(widget)

        for widgets in groups.values():
            if not widgets:
                continue
            for w in widgets:
                w.setMinimumWidth(0)
                w.setMaximumWidth(16777215)
            max_width = max(w.sizeHint().width() for w in widgets)
            for w in widgets:
                w.setFixedWidth(max_width)

    # ── Collective action helper ───────────────────────────────────────────────

    def _apply_to_modules(self, action_name: str, checked: bool = None):
        """Trigger *action_name* on every module that exposes it.

        Parameters
        ----------
        action_name:
            Name of the action as registered in the module's ActionManager.
        checked:
            For checkable actions, the desired target state.  The action is
            triggered only when its current state differs, so the connected
            slot is always called with the correct value.
            Pass ``None`` for non-checkable (one-shot) actions.
        """
        for module in self.modules:
            if not module.ui.has_action(action_name):
                continue
            action = module.ui.get_action(action_name)
            if checked is None:
                action.trigger()
            elif action.isChecked() != checked:
                action.trigger()

    # ── Lock wiring ───────────────────────────────────────────────────────────

    def _apply_lock(self, locked: bool):
        """Enable/disable lockable actions on every module."""
        for module in self.modules:
            for name in LOCKABLE_ACTIONS:
                if not module.ui.has_action(name):
                    continue
                module.ui.set_action_enabled(name, not locked)
                # set_action_enabled calls setEnabled on the stored object, which
                # for a WidgetActionProxy is the proxy shell (inherits QWidget.setEnabled)
                # and does NOT forward to the wrapped widget via __getattr__.
                # Explicitly disable the underlying widget when present.
                widget = getattr(module.ui.get_action(name), 'widget', None)
                if widget is not None:
                    widget.setEnabled(not locked)


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3 — specialisations
# ─────────────────────────────────────────────────────────────────────────────

class ActuatorCompactDock(ModuleCompactDock):
    """Compact dock specialised for DAQ_Move (actuator) modules."""

    def _get_module_align_widgets(self, module) -> dict:
        widgets = {}
        ui = module.ui
        if ui.has_action('name'):
            widgets['name'] = ui.get_action('name').widget
        if hasattr(ui, 'actuators_combo'):
            widgets['selector'] = ui.actuators_combo
        return widgets

    def _create_actions(self):
        super()._create_actions()
        self.control_toolbar.addSeparator()
        self.add_action('show_graph', 'Graph', icon_name='bid_landscape',
                        checkable=True, toolbar=self.control_toolbar,
                        tip='Show/Hide graphs on all actuators',
                        icon_checked='bid_landscape_disabled',
                        icon_color='green', icon_checked_color='red', checked=True)
        self.connect_action('show_graph', lambda checked: self._apply_to_modules('show_graph', checked))

        self.add_action('refresh_value', 'Refresh', icon_name='repeat',
                        checkable=True, toolbar=self.control_toolbar,
                        tip='Toggle continuous refresh on all actuators',
                        icon_checked='repeat_on', icon_checked_color='green')
        self.connect_action('refresh_value', lambda checked: self._apply_to_modules('refresh_value', checked))


class DetectorCompactDock(ModuleCompactDock):
    """Compact dock specialised for DAQ_Viewer (detector) modules."""

    def _get_module_align_widgets(self, module) -> dict:
        widgets = {}
        ui = module.ui
        if ui.has_action('name'):
            widgets['name'] = ui.get_action('name').widget
        if ui.has_action('selector'):
            widgets['selector'] = ui.get_action('selector').widget
        return widgets

    def _create_actions(self):
        super()._create_actions()
        self.control_toolbar.addSeparator()
        self.add_action('snap', 'Snap', icon_name='looks_one',
                        toolbar=self.control_toolbar,
                        tip='Snap all detectors')
        self.connect_action('snap', lambda: self._apply_to_modules('snap'))

        self.add_action('grab', 'Grab', icon_name='repeat',
                        checkable=True, toolbar=self.control_toolbar,
                        tip='Toggle grab on all detectors',
                        icon_checked='repeat_on', icon_checked_color='green')
        self.connect_action('grab', lambda checked: self._apply_to_modules('grab', checked))

        self.add_action('show_graphs', 'Show', icon_name='bid_landscape',
                        checkable=True, toolbar=self.control_toolbar,
                        tip='Show/Hide graphs on all detectors',
                        icon_checked='bid_landscape_disabled',
                        icon_color='green', icon_checked_color='red')
        self.connect_action('show_graphs', lambda checked: self._apply_to_modules('show_graphs', checked))

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
from pymodaq_gui.utils.widgets.collapsible_widget import CollapsibleWidget

if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer


# Action names that should be disabled while the dock-level lock is active.
LOCKABLE_ACTIONS = frozenset({
    # actuator
    'move_abs', 'move_abs_2', 'move_rel_plus', 'move_rel_minus', 'stop',
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

        # ── Control toolbar (collective actions, pinned right / bottom) ────────
        self.control_toolbar = QtWidgets.QToolBar("Controls")
        self.control_toolbar.setFloatable(False)
        self.control_toolbar.setMovable(False)
        self.control_toolbar.setOrientation(Qt.Orientation.Vertical)

        # ── Outer container ────────────────────────────────────────────────────
        outer_container = QtWidgets.QWidget()
        outer_vlay = QtWidgets.QVBoxLayout(outer_container)
        outer_vlay.setContentsMargins(0, 0, 0, 0)
        outer_vlay.setSpacing(0)
        self.dock.addWidget(outer_container)

        # Middle row: QMainWindow (toolbar rows) + collapsible right panel
        modules_row = QtWidgets.QWidget()
        modules_hlay = QtWidgets.QHBoxLayout(modules_row)
        modules_hlay.setContentsMargins(0, 0, 0, 0)
        modules_hlay.setSpacing(0)
        outer_vlay.addWidget(modules_row)

        # QMainWindow handles toolbar drag-and-drop for module rows
        self.main_window = QtWidgets.QMainWindow()
        modules_hlay.addWidget(self.main_window)

        # Zero-height central widget so QMainWindow shrinks to its toolbar rows
        _central = QtWidgets.QWidget()
        _central.setFixedHeight(0)
        self.main_window.setCentralWidget(_central)

        # Collapsible control panel pinned to the right of the toolbar rows.
        # Collapsed: [◀]    Expanded: [actions …][▶]
        toggle_btn = QtWidgets.QPushButton("◀")
        toggle_btn.setFixedWidth(16)
        self.collapsible_widget = CollapsibleWidget(
            toggle_widget=toggle_btn,
            collapsible_widget=self.control_toolbar,
            direction="left",
            content_before_toggle=True,
        )
        modules_hlay.addWidget(self.collapsible_widget)

        ActionManager.__init__(self, toolbar=self.control_toolbar)

        self._rows: dict[QtWidgets.QWidget, _RowData] = {}
        self.is_locked = False
        self._create_actions()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def modules(self):
        """Live view of all non-None module instances in row order."""
        return [r.module for r in self._rows.values() if r.module is not None]

    # ── Action setup ──────────────────────────────────────────────────────────

    def _create_actions(self):
        """Create the lock action.  Subclasses should call ``super()`` first."""
        self.add_action('lock', 'Lock', icon_name='lock_open_right', checkable=True,
                        toolbar=self.control_toolbar,
                        tip='Lock/Unlock all module actions',
                        icon_checked='lock', icon_color='green', icon_checked_color='orange')
        self.connect_action('lock', self.toggle_lock)

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
            else Qt.Orientation.Vertical
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

    # ── Lock wiring ───────────────────────────────────────────────────────────

    def _apply_lock(self, locked: bool):
        """Enable/disable lockable actions on every module."""
        for module in self.modules:
            for name in LOCKABLE_ACTIONS:
                if module.ui.has_action(name):
                    module.ui.set_action_enabled(name, not locked)


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
        # TODO: add actuator-specific collective actions (e.g. move-all, stop-all)


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
        # TODO: add detector-specific collective actions (e.g. snap-all, grab-all)

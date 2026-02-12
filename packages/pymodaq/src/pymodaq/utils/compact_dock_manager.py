"""Manager for compact docks with draggable widgets"""

from typing import Optional, List, TYPE_CHECKING
from qtpy import QtWidgets, QtGui, QtCore
from qtpy.QtCore import Qt, Signal
from pymodaq_gui.utils import Dock, DockArea
from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.utils.widgets.collapsible_widget import CollapsibleWidget

if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer


class CompactDockManager(QtCore.QObject, ActionManager):
    """Manages a compact dock with vertical/horizontal widget stacking and drag/drop support"""

    remove_module = Signal(object)       # emitted with the module instance to remove
    add_module_requested = Signal()      # emitted when the + Add Module button is clicked

    def __init__(self, title: str, dockarea: DockArea,
                 orientation: Qt.Orientation = Qt.Orientation.Vertical,
                 module_type: str = 'actuator'):
        """
        Parameters
        ----------
        title: str
            Title of the dock
        dockarea: DockArea
            Parent dock area
        orientation: Qt.Orientation
            Vertical for top-to-bottom stacking, Horizontal for left-to-right
        module_type: str
            Type of modules in this dock: 'actuator' or 'detector'
        """
        QtCore.QObject.__init__(self)

        self.dock = Dock(title)
        self.dockarea = dockarea
        self.orientation = orientation
        self.module_type = module_type

        # Map orientation to toolbar area
        self.toolbar_area = (
            Qt.ToolBarArea.TopToolBarArea if orientation == Qt.Orientation.Vertical
            else Qt.ToolBarArea.LeftToolBarArea
        )

        # Create control toolbar for collective actions
        self.control_toolbar = QtWidgets.QToolBar("Controls")
        self.control_toolbar.setFloatable(False)
        self.control_toolbar.setMovable(False)

        # ── Outer container (vertical): [module rows | collapsible]  +  [add btn] ──
        outer_container = QtWidgets.QWidget()
        outer_vlay = QtWidgets.QVBoxLayout(outer_container)
        outer_vlay.setContentsMargins(0, 0, 0, 0)
        outer_vlay.setSpacing(0)
        self.dock.addWidget(outer_container)

        # Middle row: QMainWindow (drag-drop toolbars) + collapsible right panel
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
        # Collapsed: [◀]    Expanded: [actions …][◀]
        toggle_btn = QtWidgets.QPushButton("◀")
        toggle_btn.setFixedWidth(16)
        self.collapsible_widget = CollapsibleWidget(
            toggle_widget=toggle_btn,
            collapsible_widget=self.control_toolbar,
            direction="left",
            content_before_toggle=True,
        )
        modules_hlay.addWidget(self.collapsible_widget)

        # "+ Add Module" button – visible only in edit mode
        self.add_btn = QtWidgets.QPushButton("+ Add Module")
        self.add_btn.setVisible(False)
        self.add_btn.clicked.connect(self.add_module_requested)
        outer_vlay.addWidget(self.add_btn)

        # Initialize ActionManager with the control toolbar
        ActionManager.__init__(self, toolbar=self.control_toolbar)

        # Per-module state
        self.modules: List = []
        self.module_toolbars: List[QtWidgets.QToolBar] = []
        self.module_widgets: List[QtWidgets.QWidget] = []
        self._remove_actions: List[QtWidgets.QAction] = []
        self._spacer_actions: List[QtWidgets.QAction] = []

        self.is_locked = False
        self._edit_mode = False

        self._create_actions()

    # ── Action setup ──────────────────────────────────────────────────────────

    def _create_actions(self):
        """Create all actions using ActionManager"""
        # Edit mode toggle
        self.add_action('edit_mode', 'Edit', icon_name='edit', checkable=True,
                        toolbar=self.control_toolbar,
                        tip='Toggle edit mode to add / remove modules',
                        icon_checked_color='orange')
        self.connect_action('edit_mode', self._toggle_edit_mode)
        self.control_toolbar.addSeparator()

        # Flip orientation
        flip_icon = "⇅" if self.orientation == Qt.Orientation.Vertical else "⇆"
        self.add_action('flip_orientation', flip_icon, toolbar=self.control_toolbar,
                        tip="Switch between Vertical (⇅) and Horizontal (⇆) ordering")
        self.connect_action('flip_orientation', self.flip_orientation)
        self.control_toolbar.addSeparator()

        # Module-type-specific collective actions
        if self.module_type == 'actuator':
            self._create_actuator_actions()
        elif self.module_type == 'detector':
            self._create_detector_actions()

    def _create_actuator_actions(self):
        self.add_action('lock', 'Lock', icon_name='lock_open_right', checkable=True,
                        toolbar=self.control_toolbar,
                        tip='Lock/Unlock all actuator actions',
                        icon_checked='lock', icon_color='green', icon_checked_color='orange')
        self.connect_action('lock', self.toggle_lock)

    def _create_detector_actions(self):
        self.add_action('lock', 'Lock', icon_name='lock_open_right', checkable=True,
                        toolbar=self.control_toolbar,
                        tip='Lock/Unlock all detector actions',
                        icon_checked='lock', icon_color='green', icon_checked_color='orange')
        self.connect_action('lock', self.toggle_lock)

    # ── Alignment helpers ──────────────────────────────────────────────────────

    def _get_align_widgets(self, module) -> dict:
        """Return widgets that need cross-module width alignment for *module*."""
        widgets = {}
        ui = getattr(module, 'ui', None)
        if ui is None:
            return widgets
        if ui.has_action('name'):
            widgets['name'] = ui.get_action('name').widget
        if self.module_type == 'actuator' and hasattr(ui, 'actuators_combo'):
            widgets['selector'] = ui.actuators_combo
        elif self.module_type == 'detector' and ui.has_action('selector'):
            widgets['selector'] = ui.get_action('selector').widget
        return widgets

    def _update_alignment(self):
        """Set a common fixed width for each alignment group across all modules."""
        groups: dict[str, list[QtWidgets.QWidget]] = {}
        for module in self.modules:
            for name, widget in self._get_align_widgets(module).items():
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

    # ── Module management ──────────────────────────────────────────────────────

    def add_widget(self, widget: QtWidgets.QWidget, create_toolbar: bool = True, module=None):
        """
        Add a widget (module row) to the compact dock.

        Parameters
        ----------
        widget: QWidget
            Widget to add, or an existing QToolBar when create_toolbar=False
        create_toolbar: bool
            If True, wraps widget in a new QToolBar for drag/drop
        module: DAQ_Move or DAQ_Viewer
            Associated module instance
        """
        if create_toolbar:
            toolbar = QtWidgets.QToolBar()
            toolbar.addWidget(widget)
            self.module_widgets.append(widget)
        else:
            toolbar = widget
            self.module_widgets.append(widget)

        if module is not None:
            self.modules.append(module)

        toolbar.setFloatable(False)
        toolbar.setMovable(True)
        toolbar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        toolbar.setAllowedAreas(self.toolbar_area)

        if self.orientation == Qt.Orientation.Vertical:
            toolbar.setOrientation(Qt.Orientation.Horizontal)
        else:
            toolbar.setOrientation(Qt.Orientation.Vertical)

        # ── Spacer + remove button (far right of row, edit-mode only) ──
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        spacer_action = toolbar.addWidget(spacer)
        spacer_action.setVisible(self._edit_mode)
        self._spacer_actions.append(spacer_action)

        remove_action = QtWidgets.QAction("✕", toolbar)
        remove_action.setToolTip("Remove this module")
        remove_action.setVisible(self._edit_mode)
        if module is not None:
            remove_action.triggered.connect(
                lambda _checked=False, m=module: self.remove_module.emit(m)
            )
        toolbar.addAction(remove_action)
        self._remove_actions.append(remove_action)

        if len(self.module_toolbars) > 0:
            self.main_window.addToolBarBreak(self.toolbar_area)

        self.main_window.addToolBar(self.toolbar_area, toolbar)
        self.module_toolbars.append(toolbar)

        self._update_alignment()

    def remove_widget(self, widget: QtWidgets.QWidget, module=None) -> bool:
        """
        Remove a widget from the dock.

        Returns True if the dock is now empty.
        """
        if widget in self.module_widgets:
            idx = self.module_widgets.index(widget)
            toolbar: QtWidgets.QToolBar = self.module_toolbars[idx]

            toolbar.removeAction(self._spacer_actions[idx])
            toolbar.removeAction(self._remove_actions[idx])
            self._spacer_actions.pop(idx)
            self._remove_actions.pop(idx)

            self.module_widgets.remove(widget)
            self.module_toolbars.remove(toolbar)

            if module is not None and module in self.modules:
                self.modules.remove(module)

            self.main_window.removeToolBar(toolbar)
            toolbar.deleteLater()

        self._update_alignment()
        return len(self.module_widgets) == 0

    # ── Edit mode ─────────────────────────────────────────────────────────────

    def _toggle_edit_mode(self, checked: bool):
        """Show/hide per-module remove buttons and the add-module button."""
        self._edit_mode = checked
        self.add_btn.setVisible(checked)
        for act in self._remove_actions:
            act.setVisible(checked)
        for act in self._spacer_actions:
            act.setVisible(checked)

    # ── Dock positioning ───────────────────────────────────────────────────────

    def show(self, position: str = "top", relative_to: Optional[Dock] = None):
        """Show the dock in the dockarea."""
        if relative_to:
            self.dockarea.addDock(self.dock, position, relative_to)
        else:
            self.dockarea.addDock(self.dock, position)

    def close(self):
        """Close and cleanup the dock."""
        self.dock.close()

    # ── Orientation flip ───────────────────────────────────────────────────────

    def flip_orientation(self):
        """Switch between vertical (⇅) and horizontal (⇆) ordering of toolbars"""
        if self.orientation == Qt.Orientation.Vertical:
            self.orientation = Qt.Orientation.Horizontal
            new_toolbar_area = Qt.ToolBarArea.LeftToolBarArea
            toolbar_orientation = Qt.Orientation.Vertical
            new_icon = "⇆"
        else:
            self.orientation = Qt.Orientation.Vertical
            new_toolbar_area = Qt.ToolBarArea.TopToolBarArea
            toolbar_orientation = Qt.Orientation.Horizontal
            new_icon = "⇅"

        self.set_action_text('flip_orientation', new_icon)

        current_toolbars = self.module_toolbars[:]
        for toolbar in current_toolbars:
            self.main_window.removeToolBar(toolbar)

        self.toolbar_area = new_toolbar_area

        for i, toolbar in enumerate(current_toolbars):
            toolbar.setAllowedAreas(self.toolbar_area)
            toolbar.setOrientation(toolbar_orientation)
            if i > 0:
                self.main_window.addToolBarBreak(self.toolbar_area)
            self.main_window.addToolBar(self.toolbar_area, toolbar)
            toolbar.setVisible(True)
            toolbar.show()

        self.main_window.update()
        QtWidgets.QApplication.processEvents()

    # ── Collective actions ─────────────────────────────────────────────────────

    def toggle_lock(self, checked: bool):
        """Lock/unlock all module actions."""
        self.is_locked = checked
        for module in self.modules:
            try:
                if hasattr(module, 'ui'):
                    for action_name in getattr(module.ui, 'actions_names', []):
                        if hasattr(module.ui, 'set_action_enabled'):
                            module.ui.set_action_enabled(action_name, not checked)
            except Exception:
                pass

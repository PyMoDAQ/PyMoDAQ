"""Manager for compact docks with draggable widgets"""

from typing import Optional, List, TYPE_CHECKING
from qtpy import QtWidgets, QtGui
from qtpy.QtCore import Qt
from pymodaq_gui.utils import Dock, DockArea
from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.messenger import messagebox
from pymodaq_gui.utils.widgets.collapsible_widget import CollapsibleWidget

if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer


class CompactDockManager(ActionManager):
    """Manages a compact dock with vertical/horizontal widget stacking and drag/drop support"""

    def __init__(self, title: str, dockarea: DockArea, orientation: Qt.Orientation = Qt.Orientation.Vertical,
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
        self.control_toolbar.setOrientation(Qt.Orientation.Vertical)
        # Outer container: QMainWindow (drag-drop toolbars) | CollapsibleWidget
        # Using a plain QWidget so the collapsible sits directly beside the
        # toolbar rows without a QMainWindow central-widget gap.
        outer = QtWidgets.QWidget()
        outer_layout = QtWidgets.QHBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        self.dock.addWidget(outer)

        # QMainWindow handles toolbar drag-and-drop for module rows.
        self.main_window = QtWidgets.QMainWindow()
        outer_layout.addWidget(self.main_window)

        # Zero-height central widget so the QMainWindow shrinks to its toolbar rows.
        central_widget = QtWidgets.QWidget()
        central_widget.setFixedHeight(0)
        self.main_window.setCentralWidget(central_widget)
        # self.main_window.centralWidget().setVisible(False)
        # Collapsible control panel placed directly to the right of the toolbar rows.
        # Layout when expanded:  [… actions …] [▶]
        # Layout when collapsed:               [◀]
        toggle_btn = QtWidgets.QPushButton("◀")
        toggle_btn.setFixedWidth(16)
        self.collapsible_widget = CollapsibleWidget(
            toggle_widget=toggle_btn,
            collapsible_widget=self.control_toolbar,
            direction="left",
            content_before_toggle=True,   # toolbar to the LEFT of the toggle button
        )
        outer_layout.addWidget(self.collapsible_widget)

        # Initialize ActionManager with the control toolbar
        ActionManager.__init__(self, toolbar=self.control_toolbar)
        # Track modules and their widgets
        self.modules: List = []  # List of DAQ_Move or DAQ_Viewer instances
        self.module_toolbars = []  # List of QToolBar objects for drag/drop (renamed to avoid ActionManager conflict)
        self.module_widgets = []   # List of widgets added to toolbars

        # Track locked state
        self.is_locked = False

        # Create actions
        self._create_actions()

    def _create_actions(self):
        """Create all actions using ActionManager"""
        # Flip orientation action (dynamic icon)
        flip_icon = "⇅" if self.orientation == Qt.Orientation.Vertical else "⇆"
        self.add_action('flip_orientation', flip_icon, toolbar=self.control_toolbar,
                       tip="Switch between Vertical (⇅) and Horizontal (⇆) ordering")
        self.connect_action('flip_orientation', self.flip_orientation)
        self.add_action('lock', 'Lock', icon_name='lock_open_right', checkable=True, toolbar=self.control_toolbar,
                       tip="Lock/Unlock all module actions",icon_checked='lock',icon_color='green',icon_checked_color='orange')
        self.connect_action('lock', self.toggle_lock)
        self.add_action('add', 'Add module', icon_name='add_circle', checkable=True, toolbar=self.control_toolbar,
                       tip="Add a module to dashboard",icon_checked='add',icon_color='blue')
        self.connect_action('add', self.toggle_lock)

        
        # Add separator
        self.control_toolbar.addSeparator()

    #     # Module-specific collective actions
    #     if self.module_type == 'actuator':
    #         self._create_actuator_actions()
    #     elif self.module_type == 'detector':
    #         self._create_detector_actions()

    # def _create_actuator_actions(self):
    #     """Create collective actions for actuators"""
    #     self.add_action('lock', 'Lock', icon_name='lock_open_right', checkable=True, toolbar=self.control_toolbar,
    #                    tip="Lock/Unlock all actuator actions",icon_checked='lock',icon_color='green',icon_checked_color='orange')
    #     self.connect_action('lock', self.toggle_lock)

    # def _create_detector_actions(self):
    #     """Create collective actions for detectors"""

    #     self.add_action('lock', 'Lock', icon_name='lock_open_right', checkable=True, toolbar=self.control_toolbar,
    #                    tip="Lock/Unlock all actuator actions",icon_checked='lock',icon_color='green',icon_checked_color='orange')
    #     self.connect_action('lock', self.toggle_lock)

    def _get_align_widgets(self, module) -> dict:
        """Return the widgets that need cross-module width alignment for *module*.

        Returns a dict mapping a group name to the widget:
          - ``'name'``     : the title label
          - ``'selector'`` : the actuator combo-box or detector selector widget
        """
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
        """Set a common fixed width for each alignment group across all modules.

        This ensures that name labels and selector widgets are the same width
        in every row so that the action icons line up visually.
        """
        groups: dict[str, list[QtWidgets.QWidget]] = {}
        for module in self.modules:
            for group_name, widget in self._get_align_widgets(module).items():
                groups.setdefault(group_name, []).append(widget)

        for widgets in groups.values():
            if not widgets:
                continue
            # Reset any previous constraint so sizeHint() is meaningful
            for w in widgets:
                w.setMinimumWidth(0)
                w.setMaximumWidth(16777215)  # Qt's QWIDGETSIZE_MAX
            max_width = max(w.sizeHint().width() for w in widgets)
            for w in widgets:
                w.setFixedWidth(max_width)

    def add_widget(self, widget: QtWidgets.QWidget, create_toolbar: bool = True, module=None):
        """
        Add a widget to the compact dock

        Parameters
        ----------
        widget: QtWidgets.QWidget
            Widget to add
        create_toolbar: bool
            If True, wraps widget in a QToolBar for drag/drop.
            If False, assumes widget is already a QToolBar
        module: DAQ_Move or DAQ_Viewer
            Reference to the module instance for collective actions
        """
        if create_toolbar:
            toolbar = QtWidgets.QToolBar()
            toolbar.addWidget(widget)
            self.module_widgets.append(widget)
        else:
            toolbar = widget
            self.module_widgets.append(widget)

        # Track module for collective actions
        if module is not None:
            self.modules.append(module)

        # Configure toolbar for compact display
        toolbar.setFloatable(False)  # Prevent floating windows
        toolbar.setMovable(True)     # Allow dragging within the same area only

        # Set size policy to expand
        toolbar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding
        )

        # Lock toolbar to only the current area (prevent dragging to other areas)
        allowed_areas = self.toolbar_area
        toolbar.setAllowedAreas(allowed_areas)

        # Set toolbar internal orientation based on current area
        # TopToolBarArea (vertical stacking) → Horizontal toolbar (items left-to-right)
        # LeftToolBarArea (horizontal stacking) → Vertical toolbar (items top-to-bottom)
        if self.orientation == Qt.Orientation.Vertical:
            toolbar.setOrientation(Qt.Orientation.Horizontal)
        else:
            toolbar.setOrientation(Qt.Orientation.Vertical)

        # Add toolbar break before adding (except for first toolbar)
        if len(self.module_toolbars) > 0:
            self.main_window.addToolBarBreak(self.toolbar_area)

        self.main_window.addToolBar(self.toolbar_area, toolbar)
        self.module_toolbars.append(toolbar)

        # Realign name labels and selectors so icons stay in the same column
        self._update_alignment()

    def remove_widget(self, widget: QtWidgets.QWidget, module=None) -> bool:
        """
        Remove a widget and return True if dock is now empty

        Parameters
        ----------
        widget: QtWidgets.QWidget
            Widget to remove
        module: DAQ_Move or DAQ_Viewer
            Reference to the module instance to remove from tracking

        Returns
        -------
        bool
            True if dock is now empty and should be closed
        """
        if widget in self.module_widgets:
            idx = self.module_widgets.index(widget)
            toolbar:QtWidgets.QToolBar = self.module_toolbars[idx]

            # Remove from lists
            self.module_widgets.remove(widget)
            self.module_toolbars.remove(toolbar)

            # Remove module from tracking
            if module is not None and module in self.modules:
                self.modules.remove(module)

            # Remove from main window
            self.main_window.removeToolBar(toolbar)
            toolbar.deleteLater()

        self._update_alignment()
        return len(self.module_widgets) == 0

    def show(self, position: str = "top", relative_to: Optional[Dock] = None):
        """
        Show the dock in the dockarea

        Parameters
        ----------
        position: str
            Position relative to relative_to dock or absolute position
        relative_to: Dock, optional
            Reference dock for relative positioning
        """
        if relative_to:
            self.dockarea.addDock(self.dock, position, relative_to)
        else:
            self.dockarea.addDock(self.dock, position)

    def flip_orientation(self):
        """Switch between vertical (⇅) and horizontal (⇆) ordering of toolbars"""
        # Toggle orientation
        if self.orientation == Qt.Orientation.Vertical:
            self.orientation = Qt.Orientation.Horizontal
            new_toolbar_area = Qt.ToolBarArea.LeftToolBarArea
            toolbar_orientation = Qt.Orientation.Vertical  # Items stack vertically within each toolbar
            new_icon = "⇆"
        else:
            self.orientation = Qt.Orientation.Vertical
            new_toolbar_area = Qt.ToolBarArea.TopToolBarArea
            toolbar_orientation = Qt.Orientation.Horizontal  # Items laid out horizontally within each toolbar
            new_icon = "⇅"

        # Update the flip button icon
        self.set_action_text('flip_orientation', new_icon)

        # Store current toolbars (make a copy)
        current_toolbars = self.module_toolbars[:]

        # Remove all toolbars from current area
        for toolbar in current_toolbars:
            self.main_window.removeToolBar(toolbar)

        # Update toolbar area
        self.toolbar_area = new_toolbar_area

        # Re-add toolbars to new area with appropriate orientation
        for i, toolbar in enumerate(current_toolbars):
            # Update allowed areas for this toolbar
            toolbar.setAllowedAreas(self.toolbar_area)

            # Set the toolbar's internal orientation to match the new layout
            toolbar.setOrientation(toolbar_orientation)

            # Add toolbar break before each (except first)
            if i > 0:
                self.main_window.addToolBarBreak(self.toolbar_area)

            # Re-add the toolbar
            self.main_window.addToolBar(self.toolbar_area, toolbar)
            toolbar.setVisible(True)  # Ensure it's visible
            toolbar.show()  # Force show

        # Force layout update
        self.main_window.update()
        QtWidgets.QApplication.processEvents()

    def close(self):
        """Close and cleanup the dock"""
        self.dock.close()

    # Collective Action Methods

    def toggle_lock(self, checked: bool):
        """Lock/unlock all module actions"""
        self.is_locked = checked
        # Disable/enable individual module actions
        for module in self.modules:
            try:
                if hasattr(module, 'ui'):
                    # Disable all actions in the module's UI
                    for action_name in getattr(module.ui, 'actions_names', []):
                        if hasattr(module.ui, 'set_action_enabled'):
                            module.ui.set_action_enabled(action_name, not checked)
            except Exception as e:
                pass  # Silently ignore if module doesn't support action management

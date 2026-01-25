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
        
        # Create QMainWindow to enable toolbar dragging
        self.main_window = QtWidgets.QMainWindow()
        self.dock.addWidget(self.main_window)

        # # Create a minimal central widget to avoid empty space
        # # Use a small but visible widget to avoid layout issues
        # central_widget = QtWidgets.QWidget()
        # central_widget.setSizePolicy(
        #     QtWidgets.QSizePolicy.Policy.MinimumExpanding,
        #     QtWidgets.QSizePolicy.Policy.Minimum
        # )
        # central_widget.setLayout(QtWidgets.QVBoxLayout())

        # toggle_top = QtWidgets.QPushButton("▲")
        # self.collapsible_widget = CollapsibleWidget(
        #     toggle_widget=toggle_top,
        #     collapsible_widget=self.control_toolbar,
        #     direction="bottom",
        #     content_before_toggle=False,
        #     parent=self.main_window
        # )        
        # central_widget.layout().addWidget(self.collapsible_widget)
        # self.main_window.setCentralWidget(central_widget)

        # self.main_window.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.control_toolbar)



        # Initialize ActionManager with the control toolbar
        ActionManager.__init__(self, toolbar=self.control_toolbar)
        # Add control toolbar to the main window at the bottom
        self.main_window.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.control_toolbar)
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

        # Add separator
        self.control_toolbar.addSeparator()

        # Module-specific collective actions
        if self.module_type == 'actuator':
            self._create_actuator_actions()
        elif self.module_type == 'detector':
            self._create_detector_actions()

    def _create_actuator_actions(self):
        """Create collective actions for actuators"""
        self.add_action('init_all', 'Init All', icon_name='cable', toolbar=self.control_toolbar,
                       tip="Initialize all actuators")
        self.connect_action('init_all', self.init_all_modules)

        self.add_action('deinit_all', 'Deinit All', icon_name='cable', toolbar=self.control_toolbar,
                       tip="Deinitialize all actuators")
        self.connect_action('deinit_all', self.deinit_all_modules)

        self.add_action('stop_all', 'Stop All', icon_name='stop', toolbar=self.control_toolbar,
                       tip="Emergency stop all actuators")
        self.connect_action('stop_all', self.stop_all_modules)

        self.add_action('home_all', 'Home All', icon_name='home2', toolbar=self.control_toolbar,
                       tip="Move all actuators to home position")
        self.connect_action('home_all', self.home_all_modules)

        self.add_action('lock', 'Lock', icon_name='lock_open_right', checkable=True, toolbar=self.control_toolbar,
                       tip="Lock/Unlock all actuator actions",icon_checked='lock',icon_color='green',icon_checked_color='orange')
        self.connect_action('lock', self.toggle_lock)

    def _create_detector_actions(self):
        """Create collective actions for detectors"""
        self.add_action('init_all', 'Init All', icon_name='cable', toolbar=self.control_toolbar,
                       tip="Initialize all detectors")
        self.connect_action('init_all', self.init_all_modules)

        self.add_action('deinit_all', 'Deinit All', icon_name='cable', toolbar=self.control_toolbar,
                       tip="Deinitialize all detectors")
        self.connect_action('deinit_all', self.deinit_all_modules)

        self.add_action('grab_all', 'Grab All', icon_name='videocam', toolbar=self.control_toolbar,
                       tip="Start continuous acquisition on all detectors")
        self.connect_action('grab_all', self.grab_all_modules)

        self.add_action('stop_all', 'Stop All', icon_name='videocam_off', toolbar=self.control_toolbar,
                       tip="Stop acquisition on all detectors")
        self.connect_action('stop_all', self.stop_all_modules)

        self.add_action('single_shot_all', 'Single All', icon_name='camera', toolbar=self.control_toolbar,
                       tip="Trigger single acquisition on all detectors")
        self.connect_action('single_shot_all', self.single_shot_all_modules)

        self.add_action('save_all', 'Save All', icon_name='save_as', toolbar=self.control_toolbar,
                       tip="Save data from all detectors")
        self.connect_action('save_all', self.save_all_modules)

        self.add_action('lock', 'Lock', icon_name='lock_open_right', checkable=True, toolbar=self.control_toolbar,
                       tip="Lock/Unlock all actuator actions",icon_checked='lock',icon_color='green',icon_checked_color='orange')
        self.connect_action('lock', self.toggle_lock)

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

    def init_all_modules(self):
        """Initialize all modules that are currently not initialized"""
        action_name = 'ini_actuator' if self.module_type == 'actuator' else 'ini_detector'

        # First, find all modules that need initialization
        modules_to_init = []
        for module in self.modules:            
            try:
                
                if hasattr(module, 'ui') and hasattr(module.ui, 'get_action'):
                    action = module.ui.get_action(action_name)
                    if action and not action.isChecked():  # Not initialized
                        modules_to_init.append((module, action))
            except Exception as e:
                pass

        # Now trigger them
        for module, action in modules_to_init:
            try:
                action.trigger()
                QtWidgets.QApplication.processEvents()  # Process events after each trigger
            except Exception as e:
                messagebox(severity='warning', title='Init Error',
                          text=f'Failed to initialize {module.title}: {str(e)}')

    def deinit_all_modules(self):
        """Deinitialize all modules that are currently initialized (with confirmation)"""
        action_name = 'ini_actuator' if self.module_type == 'actuator' else 'ini_detector'

        # First, find all modules that need deinitialization
        modules_to_deinit = []
        for module in self.modules:
            try:
                if hasattr(module, 'ui') and hasattr(module.ui, 'get_action'):
                    action = module.ui.get_action(action_name)
                    if action and action.isChecked():  # Currently initialized
                        modules_to_deinit.append((module, action))
            except Exception as e:
                pass

        if not modules_to_deinit:
            return  # Nothing to deinitialize

        # Ask for confirmation
        ret = messagebox(severity='question', title='Confirm Deinit All',
                        text=f'Deinitialize {len(modules_to_deinit)} initialized {self.module_type}s?')
        if ret:  # Returns True if Ok is clicked
            for module, action in modules_to_deinit:
                try:
                    action.trigger()  # This will deinitialize (uncheck the action)
                    QtWidgets.QApplication.processEvents()  # Process events after each trigger
                except Exception as e:
                    messagebox(severity='warning', title='Deinit Error',
                              text=f'Failed to deinitialize {module.title}: {str(e)}')

    def stop_all_modules(self):
        """Stop all modules by triggering their stop action"""
        for module in self.modules:
            try:
                if hasattr(module, 'ui') and hasattr(module.ui, 'get_action'):
                    action = module.ui.get_action('stop')
                    if action:
                        action.trigger()
                # For detectors, also uncheck the grab action if it's checked
                if self.module_type == 'detector':
                    grab_action = module.ui.get_action('grab')
                    if grab_action and grab_action.isChecked():
                        grab_action.trigger()  # This will stop the grab
            except Exception as e:
                messagebox(severity='warning', title='Stop Error',
                          text=f'Failed to stop {module.title}: {str(e)}')

    def home_all_modules(self):
        """Move all actuators to home position by clicking the find home button"""
        for module in self.modules:
            try:
                if hasattr(module, 'ui') and hasattr(module.ui, 'find_home_pb'):
                    # find_home_pb is a PushButtonIcon, click it
                    module.ui.find_home_pb.click()
            except Exception as e:
                messagebox(severity='warning', title='Home Error',
                          text=f'Failed to home {module.title}: {str(e)}')

    def grab_all_modules(self):
        """Start continuous acquisition on all detectors by triggering the grab action"""
        for module in self.modules:
            try:
                if hasattr(module, 'ui') and hasattr(module.ui, 'get_action'):
                    action = module.ui.get_action('grab')
                    if action and not action.isChecked():  # Only trigger if not already grabbing
                        action.trigger()
            except Exception as e:
                messagebox(severity='warning', title='Grab Error',
                          text=f'Failed to start grab on {module.title}: {str(e)}')

    def single_shot_all_modules(self):
        """Trigger single acquisition on all detectors by triggering the snap action"""
        for module in self.modules:
            try:
                if hasattr(module, 'ui') and hasattr(module.ui, 'get_action'):
                    action = module.ui.get_action('snap')
                    if action:
                        action.trigger()
            except Exception as e:
                messagebox(severity='warning', title='Single Shot Error',
                          text=f'Failed to trigger single on {module.title}: {str(e)}')

    def save_all_modules(self):
        """Save data from all detectors by triggering the save_current action"""
        for module in self.modules:
            try:
                if hasattr(module, 'ui') and hasattr(module.ui, 'get_action'):
                    action = module.ui.get_action('save_current')
                    if action:
                        action.trigger()
            except Exception as e:
                messagebox(severity='warning', title='Save Error',
                          text=f'Failed to save data from {module.title}: {str(e)}')

    def toggle_lock(self, checked: bool):
        """Lock/unlock all module actions"""
        self.is_locked = checked

        # Update action states based on lock status
        action_names = []
        if self.module_type == 'actuator':
            action_names = ['init_all', 'deinit_all', 'stop_all', 'home_all']
        elif self.module_type == 'detector':
            action_names = ['init_all', 'deinit_all', 'grab_all', 'stop_all',
                           'single_shot_all', 'save_all']

        # Disable/enable collective actions
        self.set_action_enabled(action_names, not checked)

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

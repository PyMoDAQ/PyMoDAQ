import numbers
from pathlib import Path
from typing import List, Union, Dict, Optional, Tuple, Any

from qtpy import QtWidgets, QtCore, QtGui
from pymodaq_gui.parameter.utils import filter_parameter_tree
from pymodaq_gui.utils.widgets.collapsible_widget import CollapsibleWidget
from pymodaq_gui.utils.widgets.search_lineedit import SearchLineEdit
from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.parameter import Parameter, ParameterTree, ioxml, utils
from pymodaq_gui.utils.file_io import select_file
from pymodaq_utils.config import get_set_config_dir

from pymodaq_utils.logger import set_logger, get_module_name


logger = set_logger(get_module_name(__file__))


class ParameterTreeWidget(ActionManager):
    """Widget that combines a ParameterTree with a toolbar for parameter management.

    This class provides a complete UI for managing parameters, including actions for
    saving, loading, updating settings, and searching through the parameter tree.
    The toolbar can be collapsed to save screen space.

    Parameters
    ----------
    action_list : tuple, optional
        Tuple of action names to include in the toolbar. Valid values are:
        'save', 'update', 'load', and 'search'. Default is ('save', 'update', 'load').
    tree: The class def of the ParameterTree to be used. To allow the use of modified
        ParameterTree that would allow specific dragdrop for instance)

    Attributes
    ----------
    widget : QtWidgets.QWidget
        The main widget containing the toolbar and parameter tree
    tree : ParameterTree
        A custom parameter tree for displaying and editing parameters
    toolbar : QtWidgets.QToolBar
        Toolbar containing action buttons for parameter management
    collapsible_widget : CollapsibleWidget
        Widget that allows the toolbar to be collapsed/expanded
    """

    def __init__(self, action_list: tuple = ("save", "update", "load"),
                 tree: ParameterTree = None):
        super().__init__()

        self.widget = QtWidgets.QWidget()
        self.widget.setLayout(QtWidgets.QVBoxLayout())

        toolbar = QtWidgets.QToolBar()
        self.set_toolbar(toolbar)
        if tree is None:
            tree = ParameterTree()
        self.tree: ParameterTree = tree

        self.widget.header = (
            self.tree.header
        )  # for back-compatibility, widget behave a bit like a ParameterTree
        self.widget.listAllItems = self.tree.listAllItems  # for back-compatibility

        # self.tree.setMinimumWidth(150)
        # self.tree.setMinimumHeight(300)
        toggle_top = QtWidgets.QPushButton("▼")
        self.collapsible_widget = CollapsibleWidget(
            toggle_widget=toggle_top,
            collapsible_widget=self.toolbar,
            direction="top",
            content_before_toggle=False,
        )

        # Making the buttons
        self.setup_actions(action_list)
        self.widget.layout().addWidget(self.collapsible_widget)
        self.widget.layout().addWidget(self.tree)
        self.widget.layout().setContentsMargins(0, 0, 0, 0)
        # Setup keyboard shortcuts
        if "search" in action_list:
            self._setup_search_shortcuts()

    def _setup_search_shortcuts(self):
        """Setup keyboard shortcuts for search functionality.

        Creates two keyboard shortcuts:
        - Ctrl+F: Activates the search field and expands the toolbar if collapsed
        - Esc: Collapses the toolbar and removes focus from the search field
        """
        self.search_activate_shortcut = QtGui.QShortcut(
            QtGui.QKeySequence("Ctrl+F"), self.widget
        )
        self.search_activate_shortcut.activated.connect(self.activate_search)

        self.search_escape_shortcut = QtGui.QShortcut(
            QtGui.QKeySequence("Esc"), self.widget
        )
        self.search_escape_shortcut.activated.connect(self.collapse_toolbar)

    def activate_search(self):
        """Show the collapsible widget and focus on the search field.

        Expands the toolbar if it's currently collapsed, then sets focus to the
        search field and selects all existing text for easy replacement.
        """
        # Expand the collapsible widget if it's collapsed
        self.collapsible_widget.toggle_content()
        # Get the search widget and set focus
        search_widget: SearchLineEdit = self.get_action("search_settings")
        if search_widget:
            search_widget.setFocus()
            search_widget.selectAll()  # Optional: select all text for easy replacement

    def collapse_toolbar(self):
        """Collapse the toolbar and clear search field focus.

        If the toolbar is currently expanded, this method collapses it and
        removes focus from the search field, effectively canceling the search mode.
        """
        if self.collapsible_widget.is_expanded:
            self.collapsible_widget.toggle_content()
            search_widget: SearchLineEdit = self.get_action("search_settings")
            if search_widget:
                search_widget.clearFocus()

    def setup_actions(self, action_list: tuple = ("search", "save", "update", "load")):
        """Create and configure toolbar actions based on the provided action list.

        Parameters
        ----------
        action_list : tuple, optional
            Tuple of action names to include. Valid values are:
            - 'search': Adds a search field with debounced text input
            - 'save': Adds a button to save settings to an XML file
            - 'update': Adds a button to update settings from an XML file
            - 'load': Adds a button to load settings from an XML file
            Default is ('search', 'save', 'update', 'load').

        See Also
        --------
        ActionManager.add_action : Base class method for adding actions
        """
        # Search action
        self.add_widget(
            "search_settings",
            klass=SearchLineEdit(self.toolbar, debounce_ms=200),
            visible="search" in action_list,
        )
        self.toolbar.addSeparator()

        # Saving action
        self.add_action(
            "save_settings",
            "Save Settings",
            "saveTree",
            "Save current settings in an xml file",
            visible="save" in action_list,
        )
        # Update action
        self.add_action(
            "update_settings",
            "Update Settings",
            "updateTree",
            "Update the settings from an xml file, the settings structure loaded must be identical to the current one",
            visible="update" in action_list,
        )
        # Load action
        self.add_action(
            "load_settings",
            "Load Settings",
            "openTree",
            "Load current settings from an xml file, the current settings structure is erased and is replaced by the new one",
            visible="load" in action_list,
        )


class ParameterManager:
    """Class dealing with Parameter and ParameterTree management.

    This class provides a complete parameter management system with support for
    saving, loading, and updating parameters from XML files. It also includes
    search functionality and callback methods for responding to parameter changes.

    Parameters
    ----------
    settings_name : str, optional
        The name to assign to the root Parameter object. If None, uses the
        class attribute 'settings_name'. Default is None.
    action_list : tuple, optional
        Tuple of action names to include in the toolbar. Valid values are:
        'search', 'save', 'update', and 'load'.
        Default is ('search', 'save', 'update', 'load').
    tree: ParameterTree
        Allow the use of modified ParameterTree (allowing drag/drop for instance)

    Attributes
    ----------
    params : list of dicts
        Class attribute defining the Parameter tree structure. Should be overridden
        in subclasses to define the specific parameter hierarchy.
    settings_name : str
        The particular name given to the root Parameter object (self.settings)
    settings : Parameter
        The root Parameter object containing all parameter definitions
    settings_tree : QWidget
        Widget holding a ParameterTree and a toolbar for interacting with the tree
    tree : ParameterTree
        The underlying ParameterTree widget for displaying parameters

    Examples
    --------
    >>> class MyManager(ParameterManager):
    ...     settings_name = 'my_settings'
    ...     params = [
    ...         {'title': 'Main:', 'name': 'main_settings', 'type': 'group', 'children': [
    ...             {'title': 'Value:', 'name': 'value', 'type': 'int', 'value': 0},
    ...         ]},
    ...     ]
    ...
    ...     def value_changed(self, param):
    ...         if param.name() == 'value':
    ...             print(f'Value changed to: {param.value()}')
    """

    settings_name = "custom_settings"
    params = []

    def __init__(
            self,
            settings_name: Optional[str] = None,
            action_list: tuple = ("search", "save", "update", "load"),
            tree: ParameterTree = None
    ):
        self._current_filter_text = ""
        if settings_name is None:
            settings_name = self.settings_name
        # create a settings tree to be shown eventually in a dock
        # object containing the settings defined in the preamble
        # create a settings tree to be shown eventually in a dock
        self._settings_tree = ParameterTreeWidget(action_list, tree)

        self._settings_tree.get_action(f"save_settings").connect_to(
            self.save_settings_slot
        )
        self._settings_tree.get_action(f"update_settings").connect_to(
            self.update_settings_slot
        )
        self._settings_tree.get_action(f"load_settings").connect_to(
            self.load_settings_slot
        )
        # Add this line to connect the search widget
        if "search" in action_list:
            self._settings_tree.get_action("search_settings").searchTextChanged.connect(
                self.search_settings_slot
            )
        self._settings_tree.collapsible_widget.toggled_signal.connect(
            self.on_toolbar_toggled
        )

        self.settings = Parameter.create(
            name=settings_name, type="group", children=self.params, showTop=False
        )  # create a Parameter
        # object containing the settings defined in the preamble
        self._settings_tree.tree.header().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents
        )

    @property
    def settings_tree(self) -> QtWidgets.QWidget:
        """QWidget: The main widget containing the parameter tree and toolbar."""
        return self._settings_tree.widget

    @property
    def tree(self) -> ParameterTree:
        """ParameterTree: The underlying parameter tree widget."""
        return self._settings_tree.tree

    @property
    def settings(self) -> Parameter:
        """Parameter: The root parameter object containing all settings."""
        return self._settings

    @settings.setter
    def settings(self, settings: Union[Parameter, List[Dict[str, str]], Path]):
        """Set the settings parameter from various input types.

        Parameters
        ----------
        settings : Parameter, list of dict, or Path
            The settings to load. Can be:
            - A Parameter object
            - A list of dictionaries defining parameter structure
            - A Path to an XML file containing saved parameters
        """
        settings = self.create_parameter(settings)
        self._settings = settings
        self.tree.setParameters(
            self._settings, showTop=False
        )  # load the tree with this parameter object
        self._settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

    @staticmethod
    def create_parameter(
        settings: Union[Parameter, List[Dict[str, str]], Path],
    ) -> Parameter:
        """Create a Parameter object from various input types.

        Parameters
        ----------
        settings : Parameter, list of dict, Path, or str
            The settings to convert. Can be:
            - A Parameter object (creates a copy)
            - A list of dictionaries defining parameter structure
            - A Path or string pointing to an XML file with saved parameters

        Returns
        -------
        Parameter
            A new Parameter object created from the input settings

        Raises
        ------
        TypeError
            If settings is not one of the supported types

        Examples
        --------
        >>> params_list = [{'title': 'Value', 'name': 'val', 'type': 'int', 'value': 5}]
        >>> param = ParameterManager.create_parameter(params_list)
        >>> print(param.child('val').value())
        5
        """
        if isinstance(settings, List):
            _settings = Parameter.create(
                title="Settings",
                name="settings",
                type="group",
                children=settings,
                showTop=False,
            )
        elif isinstance(settings, Path) or isinstance(settings, str):
            settings = Path(settings)
            _settings = Parameter.create(
                title="Settings",
                name="settings",
                type="group",
                showTop=False,
                children=ioxml.XML_file_to_parameter(str(settings)),
            )
        elif isinstance(settings, Parameter):
            _settings = Parameter.create(
                title="Settings", name=settings.name(), type="group", showTop=False
            )
            _settings.restoreState(settings.saveState())
        else:
            raise TypeError(f"Cannot create Parameter object from {settings}")
        return _settings

    def parameter_tree_changed(self, param, changes):
        """Handle changes in the parameter tree and dispatch to specific handlers.

        This method is called whenever any change occurs in the parameter tree.
        It processes the changes and calls the appropriate handler method based
        on the type of change.

        Parameters
        ----------
        param : Parameter
            The parameter object that emitted the change signal
        changes : list of tuple
            List of changes, where each change is a tuple of
            (parameter, change_type, data)

        Notes
        -----
        The following change types are handled:
        - 'childAdded': A new child parameter was added
        - 'value': A parameter value was changed
        - 'parent': A parameter was removed (parent changed to None)
        - 'options': Parameter options were modified
        - 'limits': Parameter limits were changed
        """
        for param, change, data in changes:
            path = self._settings.childPath(param)
            if change == "childAdded":
                self.child_added(param, data)

            elif change == "value":
                self.value_changed(param)

            elif change == "parent":
                self.param_deleted(param)

            elif change == "options":
                self.options_changed(param, data)

            elif change == "limits":
                self.limits_changed(param, data)

    def value_changed(self, param: Parameter):
        """Non-mandatory method to be subclassed for actions to perform when a parameter value changes.

        This method is called automatically when a parameter's value is changed using
        the setValue() method. Override this method in subclasses to implement
        custom behavior in response to value changes.

        Parameters
        ----------
        param : Parameter
            The parameter whose value has just changed

        Examples
        --------
        >>> def value_changed(self, param):
        ...     if param.name() == 'enable_feature':
        ...         if param.value():
        ...             print('Feature enabled')
        ...             self.settings.child('status', 'ready').setValue(True)
        ...         else:
        ...             print('Feature disabled')

        Notes
        -----
        For this method to be triggered, changes must be made using the Parameter.setValue()
        method, not by direct attribute assignment.
        """
        ...

    def child_added(self, param: Parameter, data: Parameter):
        """Non-mandatory method to be subclassed for actions to perform when a child parameter is added.

        This method is called automatically when a new child parameter is added to the
        parameter tree. Override this method in subclasses to implement custom behavior
        in response to parameter additions.

        Parameters
        ----------
        param : Parameter
            The parent parameter to which the child is being added
        data : Parameter
            The child parameter that was added

        Examples
        --------
        >>> def child_added(self, param, data):
        ...     if param.name() == 'dynamic_list':
        ...         print(f'New item added: {data.name()}')
        ...         self.update_item_count()

        Notes
        -----
        For this method to be triggered, one of the following Parameter methods must be used:
        - addChild()
        - addChildren()
        - insertChildren()
        """
        pass

    def param_deleted(self, param: Parameter):
        """Non-mandatory method to be subclassed for actions to perform when a parameter is deleted.

        This method is called automatically when a parameter is removed from the
        parameter tree. Override this method in subclasses to implement custom
        cleanup or notification behavior.

        Parameters
        ----------
        param : Parameter
            The parameter that has been deleted from the tree

        Examples
        --------
        >>> def param_deleted(self, param):
        ...     if param.name() == 'temporary_setting':
        ...         print(f'Temporary setting {param.name()} was removed')
        ...         self.cleanup_related_resources(param)

        Notes
        -----
        For this method to be triggered, the Parameter.removeChild() method must be used.
        """
        pass

    def options_changed(self, param: Parameter, data: Dict[str, Any]):
        """Non-mandatory method to be subclassed for actions to perform when parameter options change.

        This method is called automatically when options of a parameter are modified
        using the setOpts() method. Override this method in subclasses to respond
        to option changes such as visibility, enabled state, or other properties.

        Parameters
        ----------
        param : Parameter
            The parameter whose options have been changed
        data : dict
            Dictionary where keys are option names (strings) and values are the
            new option values. Common options include 'visible', 'enabled', 'readonly', etc.

        Examples
        --------
        >>> def options_changed(self, param, data):
        ...     if param.name() == 'advanced_mode' and 'visible' in data:
        ...         if data['visible']:
        ...             print('Advanced options are now visible')
        ...         else:
        ...             print('Advanced options are now hidden')

        Notes
        -----
        For this method to be triggered, the Parameter.setOpts() method must be used.
        """
        pass

    def limits_changed(
        self, param: Parameter, data: Tuple[numbers.Number, numbers.Number]
    ):
        """Non-mandatory method to be subclassed for actions to perform when parameter limits change.

        This method is called automatically when the limits (min/max bounds) of a
        parameter are changed. Override this method in subclasses to respond to
        limit changes, such as validating dependent parameters or updating the UI.

        Parameters
        ----------
        param : Parameter
            The parameter whose limits have been changed
        data : tuple of numbers
            Tuple containing (min_limit, max_limit). For numeric parameters, these
            are typically float or int values. For specialized parameters, could be
            other comparable objects.

        Examples
        --------
        >>> def limits_changed(self, param, data):
        ...     if param.name() == 'temperature':
        ...         min_temp, max_temp = data
        ...         print(f'Temperature range updated: {min_temp}°C to {max_temp}°C')
        ...         self.validate_current_temperature()

        Notes
        -----
        For this method to be triggered, the Parameter.setLimits() method must be used.
        """
        pass

    def save_settings_slot(self, file_path: Path = None):
        """Save the current settings to an XML file.

        Opens a file dialog for the user to select a save location, or uses the
        provided file path. The settings are serialized to XML format and saved
        to disk.

        Parameters
        ----------
        file_path : Path, optional
            Path where the settings should be saved. If None or False, opens a
            file dialog for the user to select a location. The file extension
            must be '.xml'. Default is None.

        Notes
        -----
        The starting directory for the file dialog is the user's config folder
        with a 'settings' subfolder. The file is automatically given a .xml
        extension if not already present.

        Examples
        --------
        >>> manager = ParameterManager()
        >>> # Interactive save
        >>> manager.save_settings_slot()
        >>> # Programmatic save
        >>> manager.save_settings_slot(Path('my_settings.xml'))
        """
        if file_path is None or file_path is False:
            file_path = select_file(
                get_set_config_dir("settings", user=True),
                save=True,
                ext="xml",
                filter="*.xml",
                force_save_extension=True,
            )
        else:
            file_path = Path(file_path)
            if ".xml" != file_path.suffix:
                return
        if file_path:
            ioxml.parameter_to_xml_file(self.settings, file_path.resolve())
            logger.info(f"The settings have been successfully saved at {file_path}")

    def _get_settings_from_file(self):
        """Open a file dialog to select an XML settings file.

        Returns
        -------
        Path or None
            Path to the selected XML file, or None if the dialog was cancelled

        Notes
        -----
        The file dialog starts in the user's config folder with a 'settings' subfolder.
        """
        return select_file(
            get_set_config_dir("settings", user=True),
            save=False,
            ext="xml",
            filter="*.xml",
            force_save_extension=True,
        )

    def load_settings_slot(self, file_path: Path = None):
        """Load settings from an XML file, replacing current settings entirely.

        Opens a file dialog for the user to select a file, or uses the provided
        file path. The current parameter tree structure is completely replaced
        with the loaded settings.

        Parameters
        ----------
        file_path : Path, optional
            Path to the XML file containing saved settings. If None or False,
            opens a file dialog for the user to select a file. Default is None.

        Notes
        -----
        The starting directory for the file dialog is the user's config folder
        with a 'settings' subfolder. This method completely replaces the current
        settings structure, unlike update_settings_slot() which requires matching
        structure.

        Warning
        -------
        This operation replaces all current settings. Any unsaved changes will be lost.

        Examples
        --------
        >>> manager = ParameterManager()
        >>> # Interactive load
        >>> manager.load_settings_slot()
        >>> # Programmatic load
        >>> manager.load_settings_slot(Path('saved_settings.xml'))

        See Also
        --------
        update_settings_slot : Update settings while preserving structure
        save_settings_slot : Save current settings to file
        """
        if file_path is None or file_path is False:
            file_path = self._get_settings_from_file()
        if file_path:
            self.settings = file_path.resolve()
            logger.info(f"The settings from {file_path} have been successfully loaded")

    def update_settings_slot(self, file_path: Path = None):
        """Update settings from an XML file with matching structure validation.

        Opens a file dialog for the user to select a file, or uses the provided
        file path. The loaded settings must have the same structure (parameter names
        and hierarchy) as the current settings. Only the values are updated, not
        the structure.

        Parameters
        ----------
        file_path : Path, optional
            Path to the XML file containing settings to apply. If None or False,
            opens a file dialog for the user to select a file. Default is None.

        Notes
        -----
        The starting directory for the file dialog is the user's config folder
        with a 'settings' subfolder. The loaded settings must have identical
        structure (same parameter names and children) as the current settings,
        otherwise the update is rejected with a warning message.

        Examples
        --------
        >>> manager = ParameterManager()
        >>> # Interactive update
        >>> manager.update_settings_slot()
        >>> # Programmatic update
        >>> manager.update_settings_slot(Path('compatible_settings.xml'))

        See Also
        --------
        load_settings_slot : Load settings without structure validation
        save_settings_slot : Save current settings to file
        """
        if file_path is None or file_path is False:
            file_path = self._get_settings_from_file()
        if file_path:
            _settings = self.create_parameter(file_path.resolve())
            # Checking if both parameters have the same structure
            sameStruct = utils.compareStructureParameter(self.settings, _settings)
            if sameStruct:  # Update if true
                self.settings = _settings
                logger.info(
                    f"The settings from {file_path} have been successfully applied"
                )
            else:
                logger.info(
                    f"The loaded settings from {file_path} do not match the current settings structure and cannot be applied."
                )

    def _apply_filter(self, text: str):
        """Apply search filter to the parameter tree with optimized updates.

        Parameters
        ----------
        text : str
            The search text to filter parameters by. Empty string shows all parameters.

        Notes
        -----
        Uses a tree change blocker to batch UI updates for better performance when
        filtering large parameter trees.
        """
        with self.settings.treeChangeBlocker():
            # Filter each child independently to avoid calling show() on the root parameter
            # This prevents issues with the root parameter name when showTop=False
            for child in self.settings.children():
                filter_parameter_tree(child, text)                            

    def search_settings_slot(self, text: str = ""):
        """Handle search text changes and filter the parameter tree.

        This slot is connected to the search widget's text changed signal. It stores
        the current search text and applies the filter to show only matching parameters.

        Parameters
        ----------
        text : str, optional
            The search text to filter parameters by. Empty string shows all
            parameters. Default is "".

        Notes
        -----
        The search is typically case-insensitive and matches against parameter
        names and titles.
        """
        self._current_filter_text = text
        self._apply_filter(text)

    def on_toolbar_toggled(self):
        """Handle toolbar expand/collapse events and manage search filter state.

        When the toolbar is expanded, restores the previous search filter.
        When collapsed, clears the search filter to show all parameters again.

        Notes
        -----
        This ensures that collapsing the toolbar (which hides the search field)
        also clears any active search filter, providing a consistent user experience.
        """
        search_widget = self._settings_tree.get_action("search_settings")

        if search_widget:
            if self._settings_tree.collapsible_widget.is_expanded:
                self._current_filter_text = search_widget.text()
            else:
                self._current_filter_text = ""
            self._apply_filter(self._current_filter_text)

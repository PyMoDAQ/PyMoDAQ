import warnings
from collections.abc import Iterable
from pathlib import Path
from typing import Callable, Iterable as IterableType, Union

from multipledispatch import dispatch
from pymodaq_utils.warnings import deprecation_msg
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtWidgets import QAction as QtQAction

here = Path(__file__).parent
icon_folder = here.parent.joinpath('QtDesigner_Ressources/Icon_Library/')
QtCore.QDir.addSearchPath('icons', str(icon_folder))

def create_icon(icon_name: Union[str, Path]):
    icon = QtGui.QIcon()
    if Path(icon_name).is_file(): # Test if icon is in path
        icon.addPixmap(QtGui.QPixmap(icon_name), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
    else:
        pixmap = QtGui.QPixmap(f"icons:{icon_name}.png") # Test if icon is in pymodaq's library
        if pixmap.isNull(): 
            if hasattr(QtGui.QIcon,'ThemeIcon') and hasattr(QtGui.QIcon.ThemeIcon, icon_name): # Test if icon is in Qt's library
                icon = QtGui.QIcon.fromTheme(getattr(QtGui.QIcon.ThemeIcon, icon_name))
            elif hasattr(QtWidgets.QStyle.StandardPixmap, icon_name):
                pixmapi = getattr(QtWidgets.QStyle.StandardPixmap, icon_name)
                icon = QtWidgets.QWidget().style().standardIcon(pixmapi)
        else:
            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap(pixmap), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
    return icon


class QAction(QtQAction):
    """
    QAction subclass to mimic signals as pushbuttons. Done to be sure of backcompatibility
    when I moved from pushbuttons to QAction
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def click(self):
        deprecation_msg("click for PyMoDAQ's QAction is deprecated, use *trigger*",
                        stacklevel=3)
        self.trigger()

    @property
    def clicked(self):
        deprecation_msg("clicked for PyMoDAQ's QAction is deprecated, use *trigger*",
                        stacklevel=3)
        return self.triggered

    def connect_to(self, slot):
        self.triggered.connect(slot)

    def set_icon(self, icon_name: str):
        self.setIcon(create_icon(icon_name))

    def __repr__(self):
        return f'QAction {self.text()}'


def addaction(name: str = '', icon_name: Union[str, Path, QtGui.QIcon]= '', tip='', checkable=False, checked=False,
              slot: Callable = None, toolbar: QtWidgets.QToolBar = None,
              menu: QtWidgets.QMenu = None, visible=True, shortcut: Union[str, QtCore.Qt.Key]=None,
              enabled=True):
    """Create a new action and add it eventually to a toolbar and a menu

    Parameters
    ----------
    name: str
        Displayed name if should be displayed (for instance in menus)
    icon_name: str / Path / QtGui.QIcon / enum name
        str/Path: the png file name/path to produce the icon
        QtGui.QIcon: the instance of a QIcon element
        ThemeIcon enum: the value of QtGui.QIcon.ThemeIcon (requires Qt>=6.7)
    tip: str
        a tooltip to be displayed when hovering above the action
    checkable: bool
        set the checkable state of the action
    checked: bool
        set the current state of the action
    slot: callable
        Method or function that will be called when the action is triggered
    toolbar: QToolBar
        a toolbar where action should be added.
    menu: QMenu
        a menu where action should be added.
    visible: bool
        display or not the action in the toolbar/menu
    shortcut: str or Qt.Key
        a string defining a shortcut for this action
    enabled: bool
        set the enabled state
    """

    if icon_name is None or icon_name == '':
        action = QAction(name)
    elif isinstance(icon_name, QtGui.QIcon):
        action = QAction(icon_name, name, None)
    else:
        action = QAction(create_icon(icon_name), name, None)

    if slot is not None:
        action.connect_to(slot)
    action.setCheckable(checkable)
    if checkable:
        action.setChecked(checked)
    action.setToolTip(tip)
    if toolbar is not None:
        toolbar.addAction(action)
    if menu is not None:
        menu.addAction(action)
    if shortcut is not None:
        action.setShortcut(shortcut)
    action.setVisible(visible)
    action.setEnabled(enabled)
    return action


def addwidget(klass: Union[str, QtWidgets.QWidget, object], *args, tip='', toolbar: QtWidgets.QToolBar = None,
              visible=True,
              signal_str=None, slot: Callable=None, setters: dict = None, enabled=True, **kwargs):
    """Create and eventually add a widget to a toolbar

    Parameters
    ----------
    klass: str or QWidget or QWidget instance
        should be a custom widget class or the name of a standard widget of QWidgets
    args: list
     variable arguments passed as is to the widget constructor
    tip: str
        a tooltip to be displayed when hovering above the widget
    toolbar: QToolBar
        a toolbar where the widget should be added.
    visible: bool
        display or not the action in the toolbar/menu
    signal_str: str
        an attribute of type Signal of the widget
    slot: Callable
        a callable connected to the signal
    enabled: bool
        enable state of the widget
    kwargs: dict
        variable named arguments used as is in the widget constructor
    setters: dict
        method/value pair of the widget (for instance setMaximumWidth)
    Returns
    -------
    QtWidgets.QWidget
    """
    if setters is None:
        setters = {}
    if isinstance(klass, str):
        if hasattr(QtWidgets, klass):
            widget: QtWidgets.QWidget = getattr(QtWidgets, klass)(*args)
        else:
            return None
    elif isinstance(klass, QtWidgets.QWidget):
        widget = klass
    else:
        try:
            widget = klass(*args, **kwargs)
        except:
            return None

    if toolbar is not None:
        class WidgetActionProxy(QtWidgets.QWidget):
            '''
                Wrapper class of a Widget and its associated toolbar Action.

                All methods call are forwarded to the wrapped Widget. Even its class name
                is copied.

                Only the setVisible method is different, as the Action need to be hidden.

               (monkey-patching setVisible on the widget wasn't compatible with PySide6)
            '''
            def __init__(self, widget : QtWidgets.QWidget, action : QtWidgets.QAction):
                super().__init__(widget.parent())
                self.setParent(widget)

                self._widget = widget
                self._action = action

            def setVisible(self, visible : bool):
                self._action.setVisible(visible)
                self._widget.setVisible(visible)
                super().setVisible(visible)

            def __getattr__(self, name : str):
                return getattr(self._widget, name)

            @property
            def __class__(self):
                return self._widget.__class__


        action: QtWidgets.QAction = toolbar.addWidget(widget)
        action.setVisible(visible)
        action.setToolTip(tip)
        widget = WidgetActionProxy(widget, action)
    else:
        widget.setVisible(visible)
        widget.setToolTip(tip)

    if isinstance(signal_str, str) and slot is not None:
        if hasattr(widget, signal_str):
            getattr(widget, signal_str).connect(slot)

    for setter in setters:
        if hasattr(widget, setter):
            getattr(widget, setter)(setters[setter])
    widget.setEnabled(enabled)
    return widget


class ActionManager:
    """MixIn Class to be used by all UserInterface to manage their QActions and the action they are connected to

    Parameters
    ----------
    toolbar: QToolbar, optional
        The toolbar to use as default
    menu: QMenu, option
        The menu to use as default
    """
    def __init__(self, toolbar: QtWidgets.QToolBar = None, menu: QtWidgets.QMenu = None):
        self._actions: dict[str, QAction] = {}
        self._menus: dict[str, QtWidgets.QMenu] = {}
        self._toolbars: dict[str, QtWidgets.QToolBar] = {}

        # Store defaults in dicts
        if menu is not None:
            self._menus['_default'] = menu
        if toolbar is not None:
            self._toolbars['_default'] = toolbar

        #self.setup_actions()

    @property
    def _menu(self) -> QtWidgets.QMenu:
        """Get the default menu (backward compatibility)"""
        return self._menus.get('_default', None)

    @property
    def _toolbar(self) -> QtWidgets.QToolBar:
        """Get the default toolbar (backward compatibility)"""
        return self._toolbars.get('_default', None)

    def setup_actions(self):
        """Method where to create actions to be subclassed. Mandatory

        Examples
        --------
        >>> self.add_action('Quit', 'close2', "Quit program")
        >>> self.add_action('Grab', 'camera', "Grab from camera", checkable=True)
        >>> self.add_action('Load', 'Open', "Load target file (.h5, .png, .jpg) or data from camera", checkable=False)
        >>> self.add_action('Save', 'SaveAs', "Save current data", checkable=False)

        See Also
        --------
        ActionManager.add_action
        """
        raise NotImplementedError(f'You have to define actions here in the following form:'
                                  f'{self.setup_actions.__doc__}')

    def add_action(self, short_name: str = '', name: str = '', icon_name: Union[str, Path, QtGui.QIcon] = '', tip='',
                   checkable=False,
                   checked=False, toolbar: Union[str, QtWidgets.QToolBar, None]=None,
                   menu: Union[str, QtWidgets.QMenu, None] = None,
                   visible=True, shortcut: Union[str, QtCore.Qt.Key]=None, auto_toolbar=True, auto_menu=True,
                   enabled=True):
        """Create a new action and add it to toolbar and menu

        Parameters
        ----------
        short_name: str
            the name as referenced in the dict self.actions
        name: str
            Displayed name if should be displayed in
        icon_name: str / Path / QtGui.QIcon / enum name
            str/Path: the png file name/path to produce the icon
            QtGui.QIcon: the instance of a QIcon element
            ThemeIcon enum: the value of QtGui.QIcon.ThemeIcon (requires Qt>=6.7)
        tip: str
            a tooltip to be displayed when hovering above the action
        checkable: bool
            set the checkable state of the action
        checked: bool
            set the current state of the action
        toolbar: str or QToolBar or None
            a toolbar where action should be added. Can be:
            - None: adds to the default menu (self._toolbar)
            - str: toolbar name as registered via add_toolbar()
            - QToolbar: direct QToolbar instance
              Actions can also be added later see *affect_to*
        menu: str or QMenu or None
            Where to add the action. Can be:
            - None: adds to the default menu (self._menu)
            - str: menu name as registered via add_menu()
            - QMenu: direct QMenu instance
            Actions can also be added later see *affect_to*
        visible: bool
            display or not the action in the toolbar/menu
        auto_toolbar: bool
            if True add this action to the defined toolbar
        auto_menu: bool
            if True add this action to the defined menu
        enabled: bool
            set the enabled state of this action
        See Also
        --------
        affect_to, pymodaq.resources.QtDesigner_Ressources.Icon_Library,
        pymodaq.utils.managers.action_manager.add_action
        """
        if auto_toolbar:
            if toolbar is None:
                toolbar = self._toolbar
            elif isinstance(toolbar, str):
                toolbar = self.get_toolbar(toolbar)
            elif not isinstance(toolbar, QtWidgets.QToolBar):
                raise TypeError(f'toolbar must be either None, a string, or QToolBar, got {type(toolbar)}')

        if auto_menu:
            if menu is None:
                menu = self._menu
            elif isinstance(menu, str):
                menu = self.get_menu(menu)
            elif not isinstance(menu, QtWidgets.QMenu):
                raise TypeError(f'menu must be either None, a string, or QMenu, got {type(menu)}')
        self._actions[short_name] = addaction(name, icon_name, tip, checkable=checkable,
                                              checked=checked, toolbar=toolbar, menu=menu,
                                              visible=visible, shortcut=shortcut, enabled=enabled)
        return self._actions[short_name]

    def add_widget(self, short_name, klass: Union[str, QtWidgets.QWidget, object], *args, tip='',
                   toolbar: Union[str, QtWidgets.QToolBar] = None, visible=True, signal_str=None,
                   slot: Callable=None, enabled=True, auto_toolbar=True, **kwargs):
        """Create and add a widget to a toolbar

        Parameters
        ----------
        short_name: str
            the name as referenced in the dict self.actions
        klass: str or QWidget or QWidget instance
            should be a custom widget class or the name of a standard widget of QWidgets
        args: list
         variable arguments passed as is to the widget constructor
        tip: str
            a tooltip to be displayed when hovering above the widget
        toolbar: QToolBar
            a toolbar where the widget should be added.
        visible: bool
            display or not the action in the toolbar/menu
        signal_str: str
            an attribute of type Signal of the widget
        slot: Callable
            a callable connected to the signal
        enabled: bool
            enable state of the widget
        auto_toolbar: bool
            if True add this action to the defined toolbar
        kwargs: dict
            variable named arguments passed as is to the widget constructor
        Returns
        -------
        QtWidgets.QWidget
        """
        if auto_toolbar:
            if toolbar is None:
                toolbar = self._toolbar
            elif isinstance(toolbar, str):
                toolbar = self.get_toolbar(toolbar)
            elif not isinstance(toolbar, QtWidgets.QToolBar):
                raise TypeError(f'toolbar must be either None, a string, or QToolBar, got {type(toolbar)}')

        widget = addwidget(klass, *args, tip=tip, toolbar=toolbar, visible=visible, signal_str=signal_str,
                           slot=slot, enabled=enabled, **kwargs)

        if widget is not None:
            self._actions[short_name] = widget
        else:
            warnings.warn(UserWarning(f'Impossible to add the widget {short_name} and type {klass} to the toolbar'))
        return widget

    def add_menu(self, short_name: str, title: str, menu: QtWidgets.QMenu = None,
                 icon_name: Union[str, Path, QtGui.QIcon] = '', auto_menu=True) -> QtWidgets.QMenu:
        """Create and add a menu to a parent menu

        Parameters
        ----------
        short_name: str
            the name as referenced in the dict self._menus
        title: str
            Displayed title of the menu
        menu: QMenu, optional
            a parent menu where this menu should be added. If None, uses the default menu
        icon_name: str / Path / QtGui.QIcon / enum name, optional
            str/Path: the png file name/path to produce the icon
            QtGui.QIcon: the instance of a QIcon element
            ThemeIcon enum: the value of QtGui.QIcon.ThemeIcon (requires Qt>=6.7)
        auto_menu: bool
            if True add this menu to the defined parent menu

        Returns
        -------
        QtWidgets.QMenu
            The created menu

        See Also
        --------
        add_action, get_menu
        """
        if auto_menu:
            if menu is None:
                menu = self._menu

        new_menu = QtWidgets.QMenu(title)

        # Set icon if provided
        if icon_name and icon_name != '':
            if isinstance(icon_name, QtGui.QIcon):
                new_menu.setIcon(icon_name)
            else:
                new_menu.setIcon(create_icon(icon_name))

        # Add to parent menu if specified
        if menu is not None:
            menu.addMenu(new_menu)

        # Store reference
        self._menus[short_name] = new_menu

        return new_menu

    def reference_toolbar(self, short_name: str, toolbar: QtWidgets.QToolBar):
        """ Add an existing toolbar to the list of managed toolbars"""
        if short_name not in self._toolbars:
            self._toolbars[short_name] = toolbar
        else:
            raise KeyError(f'Toolbar {short_name} is already existing')

    def reference_menu(self, short_name: str, menu: QtWidgets.QMenu):
        """ Add an existing toolbar to the list of managed toolbars"""
        if short_name not in self._menus:
            self._menus[short_name] = menu
        else:
            raise KeyError(f'Menu {short_name} is already existing')

    def add_toolbar(self, short_name: str, title: str = '', parent: QtWidgets.QWidget = None) -> QtWidgets.QToolBar:
        """Create and add a toolbar

        Parameters
        ----------
        short_name: str
            the name as referenced in the dict self._toolbars
        title: str, optional
            Displayed title of the toolbar
        parent: QWidget, optional
            parent widget for the toolbar (typically a QMainWindow)

        Returns
        -------
        QtWidgets.QToolBar
            The created toolbar

        See Also
        --------
        add_action, get_toolbar
        """
        toolbar = QtWidgets.QToolBar(title, parent)
        self._toolbars[short_name] = toolbar
        return toolbar

    def set_toolbar(self, toolbar):
        """Set the default toolbar

        Parameters
        ----------
        toolbar: QtWidgets.QToolBar
            The toolbar to set as default
        """
        self._toolbars['_default'] = toolbar

    def set_menu(self, menu):
        """Set the default menu

        Parameters
        ----------
        menu: QtWidgets.QMenu
            The menu to set as default
        """
        self._menus['_default'] = menu

    def set_action_text(self, action_name: str, text: str):
        """Convenience method to set the displayed text on an action

        Parameters
        ----------
        action_name: str
            The action name as defined in setup_actions
        text: str
            The text to display
        """
        self.get_action(action_name).setText(text)

    @property
    def actions(self) -> list[QAction]:
        return list(self._actions.values())

    @property
    def actions_names(self) -> list[str]:
        return list(self._actions.keys())

    def get_action(self, name) -> Union[QAction, QtWidgets.QWidget]:
        """Getter of a given action

        Parameters
        ----------
        name: str
            The action name as defined in setup_actions

        Returns
        -------
        QAction
        """
        if self.has_action(name):
            return self._actions[name]
        else:
            raise KeyError(f'The action with name: {name} is not referenced'
                           f' in the view actions: {self._actions.keys()}')

    def has_action(self, action_name) -> bool:
        """Check if an action has been defined
        Parameters
        ----------
        action_name: str
            The action name as defined in setup_actions

        Returns
        -------
        bool: True if the action exists, False otherwise
        """
        return action_name in self._actions

    def get_menu(self, name: str) -> QtWidgets.QMenu:
        """Getter of a given menu

        Parameters
        ----------
        name: str
            The menu name as defined when calling add_menu

        Returns
        -------
        QMenu
        """
        if self.has_menu(name):
            return self._menus[name]
        else:
            raise KeyError(f'The menu with name: {name} is not referenced'
                           f' in the menus: {self._menus.keys()}')

    def has_menu(self, menu_name: str) -> bool:
        """Check if a menu has been defined

        Parameters
        ----------
        menu_name: str
            The menu name as defined when calling add_menu

        Returns
        -------
        bool: True if the menu exists, False otherwise
        """
        return menu_name in self._menus

    def get_toolbar(self, name: str) -> QtWidgets.QToolBar:
        """Getter of a given toolbar

        Parameters
        ----------
        name: str
            The toolbar name as defined when calling add_toolbar

        Returns
        -------
        QToolBar
        """
        if self.has_toolbar(name):
            return self._toolbars[name]
        else:
            raise KeyError(f'The toolbar with name: {name} is not referenced'
                           f' in the toolbars: {self._toolbars.keys()}')

    def has_toolbar(self, toolbar_name: str) -> bool:
        """Check if a toolbar has been defined

        Parameters
        ----------
        toolbar_name: str
            The toolbar name as defined when calling add_toolbar

        Returns
        -------
        bool: True if the toolbar exists, False otherwise
        """
        return toolbar_name in self._toolbars

    @property
    def menus(self) -> list[QtWidgets.QMenu]:
        """Get all menus"""
        return list(self._menus.values())

    @property
    def menus_names(self) -> list[str]:
        """Get all menu names"""
        return list(self._menus.keys())

    @property
    def toolbars(self) -> list[QtWidgets.QToolBar]:
        """Get all toolbars"""
        return list(self._toolbars.values())

    @property
    def toolbars_names(self) -> list[str]:
        """Get all toolbar names"""
        return list(self._toolbars.keys())

    @property
    def toolbar(self) -> QtWidgets.QToolBar:
        """Get the default toolbar"""
        return self._toolbar

    @property
    def menu(self) -> QtWidgets.QMenu:
        """Get the default menu"""
        return self._menu

    def affect_to(self, action_name, obj: Union[QtWidgets.QToolBar, QtWidgets.QMenu]):
        """Affect action to an object either a toolbar or a menu

        Parameters
        ----------
        action_name: str
            The action name as defined in setup_actions
        obj: QToolbar or QMenu
            The object where to add the action
        """
        if isinstance(obj, QtWidgets.QToolBar) or isinstance(obj, QtWidgets.QMenu):
            obj.addAction(self._actions[action_name])

    def connect_action(self, name, slot=None, connect=True, signal_name=''):
        """Connect (or disconnect) the action referenced by name to the given slot

        Parameters
        ----------
        name: str
            key of the action as referenced in the self._actions dict
        slot: method
            a method/function
        connect: bool
            if True connect the trigger signal of the action to the defined slot else disconnect it
        signal_name: str
            try to use it as a signal (for widgets added...) otherwise use the *triggered* signal
        """
        signal = 'triggered'
        if name in self._actions:
            if hasattr(self._actions[name], signal_name):
                signal = signal_name
            if connect:
                getattr(self._actions[name], signal).connect(slot)
            else:
                try:
                    getattr(self._actions[name], signal).disconnect()
                except (TypeError,) as e:
                    pass  # the action was not connected
        else:
            raise KeyError(f'The action with name: {name} is not referenced'
                           f' in the view actions: {self._actions.keys()}')

    @dispatch(str)
    def is_action_visible(self, action_name: str):
        """Check the visibility of a given action or the list of an action"""
        if action_name in self._actions:
            return self._actions[action_name].isVisible()
        else:
            raise KeyError(f'The action with name: {action_name} is not referenced'
                           f' in the actions list: {self._actions}')

    @dispatch(Iterable)
    def is_action_visible(self, actions_name: IterableType):
        """Check the visibility of a given action or the list of an action"""
        isvisible = False
        for action_name in actions_name:
            isvisible = isvisible and self.is_action_visible(action_name)
        return isvisible

    @dispatch(str)
    def is_action_checked(self, action_name: str):
        """Get the CheckState of a given action or a list of actions"""
        if action_name in self._actions:
            return self._actions[action_name].isChecked()
        else:
            raise KeyError(f'The action with name: {action_name} is not referenced'
                           f' in the actions list: {self._actions}')

    @dispatch(Iterable)
    def is_action_checked(self, actions_name: IterableType):
        """Get the CheckState of a given action or a list of actions"""
        ischecked = False
        for action_name in actions_name:
            ischecked = ischecked and self.is_action_checked(action_name)
        return ischecked

    @dispatch(str, bool)
    def set_action_visible(self, action_name: str, visible=True):
        """Set the visibility of a given action or a list of an action"""
        if action_name in self._actions:
            self._actions[action_name].setVisible(visible)
        else:
            raise KeyError(f'The action with name: {action_name} is not referenced'
                           f' in the actions list: {self._actions}')

    @dispatch(Iterable, bool)
    def set_action_visible(self, actions_name: IterableType, visible=True):
        """Set the visibility of a given action or a list of an action"""
        for action_name in actions_name:
            self.set_action_visible(action_name, visible)

    @dispatch(str, bool)
    def set_action_checked(self, action_name: str, checked=True):
        """Set the CheckedState of a given action or a list of actions"""
        if action_name in self._actions:
            self._actions[action_name].setChecked(checked)
        else:
            raise KeyError(f'The action with name: {action_name} is not referenced'
                           f' in the actions list: {self._actions}')

    @dispatch(Iterable, bool)
    def set_action_checked(self, actions_name: IterableType, checked=True):
        """Set the CheckedState of a given action or a list of actions"""
        for action_name in actions_name:
            self.set_action_checked(action_name, checked)

    @dispatch(str, bool)
    def set_action_enabled(self, action_name: str, enabled=True):
        """Set the EnabledState of a given action or a list of actions"""
        if action_name in self._actions:
            self._actions[action_name].setEnabled(enabled)
        else:
            raise KeyError(f'The action with name: {action_name} is not referenced'
                           f' in the actions list: {self._actions}')

    @dispatch(Iterable, bool)
    def set_action_enabled(self, actions_name: IterableType, enabled=True):
        """Set the EnabledState of a given action or a list of actions"""
        for action_name in actions_name:
            self.set_action_enabled(action_name, enabled)

    @dispatch(str)
    def is_action_enabled(self, action_name: str):
        """Get the EnabledState of a given action or a list of actions"""
        if action_name in self._actions:
            return self._actions[action_name].isEnabled()
        else:
            raise KeyError(f'The action with name: {action_name} is not referenced'
                           f' in the actions list: {self._actions}')

    @dispatch(Iterable)
    def is_action_checked(self, actions_name: IterableType):
        """Get the EnabledState of a given action or a list of actions"""
        is_enabled = False
        for action_name in actions_name:
            is_enabled = is_enabled and self.is_action_enabled(action_name)
        return is_enabled

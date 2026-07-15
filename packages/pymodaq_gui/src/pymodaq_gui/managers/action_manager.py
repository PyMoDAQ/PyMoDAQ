import warnings
from collections.abc import Iterable
from collections import OrderedDict
from pathlib import Path
from typing import Callable, Iterable as IterableType, Union, OrderedDict as OrderedDictType

from multipledispatch import dispatch
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtWidgets import QAction as QtQAction

from pymodaq_gui.utils.styling import create_icon
from pymodaq_utils.warnings import deprecation_msg
from pymodaq_utils.config import GlobalConfig as Config

try:
    from pymodaq_gui.resources.material_icons import MaterialIcon
except ImportError:
    pass  #this could happen when creating /importing new MaterialIcons

config = Config()
resource_folder = Path(__file__).parent.parent.joinpath('resources')
QtCore.QDir.addSearchPath('icons', str(resource_folder.joinpath('icon_library')))


class QAction(QtQAction):
    """
    QAction subclass to mimic signals as pushbuttons. Done to be sure of backcompatibility
    when I moved from pushbuttons to QAction
    """
    def __init__(self, icon_unchecked: Union[None, str, QtGui.QIcon],
                 name='',
                 icon_checked: Union[str, QtGui.QIcon] = None,
                 icon_color: Union[QtGui.QColor, bytes, str]=None,
                 icon_checked_color: Union[QtGui.QColor, bytes, str]=None,
                 flip_h: bool = False,
                 flip_v: bool = False,
                 rotate: int = 0,
                 fill: bool = None,
                 ):

        if icon_unchecked is not None:
            self.icon_unchecked = create_icon(icon_unchecked, icon_color, icon_checked_color,
                                              flip_h=flip_h, flip_v=flip_v, rotate=rotate,
                                              fill=fill)
            super().__init__(self.icon_unchecked, name)
        else:
            super().__init__(name)

        if icon_unchecked is not None and icon_checked is not None and not isinstance(icon_checked, QtGui.QIcon):
            icon_checked = create_icon(icon_checked, icon_checked_color, icon_checked_color,
                                       flip_h=flip_h, flip_v=flip_v, rotate=rotate,
                                       fill=fill)
            if isinstance(icon_unchecked, MaterialIcon):
                self.icon_unchecked.set_icon(icon_checked, state=QtGui.QIcon.State.On)
            else:
                self.icon_checked = icon_checked
                if icon_checked is not None:
                    self.triggered.connect(lambda: self.set_icon())

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

    def set_icon(self, icon_name: str = None,
                 icon_color: Union[QtGui.QColor, bytes, str]=None):
        if icon_name is None:
            if self.isChecked():
                icon_name = self.icon_checked
            else:
                icon_name = self.icon_unchecked
        self.setIcon(create_icon(icon_name, icon_color))

    def __repr__(self):
        return f'QAction {self.text()}'


class WidgetActionProxy(QtWidgets.QWidget):
    """ Wrapper class of a Widget and its associated toolbar Action.
    All methods call are forwarded to the wrapped Widget. Even its class name
    is copied.

    Only the setVisible method is different, as the Action need to be hidden.
    (monkey-patching setVisible on the widget wasn't compatible with PySide6)
    """
    def __init__(self, widget : QtWidgets.QWidget, action : QtWidgets.QAction):
        super().__init__(widget.parent())
        self.setParent(widget)

        self._widget = widget
        self._action = action

    def setVisible(self, visible : bool):
        self._action.setVisible(visible)
        self._widget.setVisible(visible)
        super().setVisible(visible)

    def isVisible(self) -> bool:
        return self.widget.isVisible()

    @property
    def widget(self) -> QtWidgets.QWidget:
        return self._widget

    @property
    def action(self) -> QtWidgets.QAction:
        return self._action

    def __getattr__(self, name : str):
        return getattr(self._widget, name)

    @property
    def __class__(self):
        return self._widget.__class__


def addaction(name: str = '', icon_name: Union[str, Path, QtGui.QIcon]= '', tip='', checkable=False, checked=False,
              slot: Callable = None, toolbar: QtWidgets.QToolBar = None,
              menu: QtWidgets.QMenu = None, visible=True, shortcut: Union[str, QtCore.Qt.Key, QtGui.QKeySequence]=None,
              enabled=True, icon_checked: Union[str, Path, QtGui.QIcon] = None,
              icon_color: Union[QtGui.QColor, str] = None,
              icon_checked_color: Union[QtGui.QColor, str] = None,
              flip_h: bool = False,
              flip_v: bool = False,
              before: QtQAction = None,
              action: QtQAction | QtWidgets.QWidgetAction = None,
              fill: bool = None,
              rotate: int = 0
              ):
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
    shortcut: str, QKey or QKeySequence
        Using this shortcut will trigger the action
    enabled: bool
        set the enabled state
    icon_checked: : str / Path / QtGui.QIcon / enum name
        str/Path: the png file name/path to produce the icon
        QtGui.QIcon: the instance of a QIcon element
        ThemeIcon enum: the value of QtGui.QIcon.ThemeIcon (requires Qt>=6.7)
        Optional, if set, will be the icon when the action is checked (checkable will be set to True)
    icon_color: QtGui.QColor / str
        color to be applied (if possible) to the unchecked icon
    icon_checked_color: QtGui.QColor / str
        color to be applied to the checked icon (if any)
    flip_h: bool
        mirror the icon horizontally (left ↔ right)
    flip_v: bool
        mirror the icon vertically (top ↔ bottom)
    rotate: int
        rotate the icon by the given value in degrees
    before: QAction, optional
        if set, the action is inserted before this action in the toolbar/menu;
        if None the action is appended at the end
    action: QAction, QWidgetAction, optional
    fill: bool, optional
        Fill or not the icon, if None left to the user configuration
    rotate: int, optional
        Rotate the icon by this value in degree
    """
    if action is None:
        if icon_name is None or icon_name == '':
            action = QAction(None, name)
        else:
            action = QAction(icon_name, name, icon_checked=icon_checked,
                             icon_color=icon_color, icon_checked_color=icon_checked_color,
                             flip_h=flip_h, flip_v=flip_v, rotate=rotate, fill=fill)

    if slot is not None:
        action.connect_to(slot)
    if icon_checked is not None:
        checkable = True
    action.setCheckable(checkable)
    if checkable:
        action.setChecked(checked)
        if checked and hasattr(action, 'icon_checked'):
            action.set_icon()
    action.setToolTip(tip)
    if toolbar is not None:
        if before is not None:
            toolbar.insertAction(before, action)
        else:
            toolbar.addAction(action)
    if menu is not None:
        if before is not None:
            menu.insertAction(before, action)
        else:
            menu.addAction(action)
    if shortcut is not None:
        action.setShortcut(shortcut)
    action.setVisible(visible)
    action.setEnabled(enabled)
    return action


def addwidget(klass: Union[str, QtWidgets.QWidget, object], *args, tip='',
              toolbar: QtWidgets.QToolBar = None,
              visible=True, signal_str=None, slot: Callable=None,
              setters: dict = None, enabled=True, **kwargs) -> Union[WidgetActionProxy, QtWidgets.QWidget]:
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

        action: QtWidgets.QAction = toolbar.addWidget(widget)
        action.setVisible(visible)
        widget.setToolTip(tip)
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
        self._actions: OrderedDictType[str, QAction] = OrderedDict([])
        self._menus: OrderedDictType[str, QtWidgets.QMenu] = OrderedDict([])
        self._toolbars: OrderedDictType[str, QtWidgets.QToolBar] = OrderedDict([])

        self._toolbar: QtWidgets.QToolBar = None
        self._menu: QtWidgets.QMenu = None

        if toolbar is not None:
            self.reference_toolbar('default', toolbar)
            self.set_toolbar(toolbar)
        if menu is not None:
            self.reference_menu('default', menu)
            self.set_menu(menu)

    def _resolve_toolbar(self, toolbar: Union[str, QtWidgets.QToolBar, None],
                         auto: bool = True) -> Union[QtWidgets.QToolBar, None]:
        """Resolve a toolbar reference to a QToolBar instance.

        Parameters
        ----------
        toolbar: str, QToolBar, or None
            str: looked up by name via get_toolbar
            QToolBar: returned as-is
            None + auto=True: returns the default toolbar (creating one if needed)
            None + auto=False: returns None
        """
        if toolbar is not None:
            if isinstance(toolbar, str):
                return self.get_toolbar(toolbar)
            if not isinstance(toolbar, QtWidgets.QToolBar):
                raise TypeError(f'toolbar must be None, a str, or QToolBar, got {type(toolbar)}')
            return toolbar
        return self.toolbar if auto else None

    def _resolve_menu(self, menu: Union[str, QtWidgets.QMenu, None],
                      auto: bool = True) -> Union[QtWidgets.QMenu, None]:
        """Resolve a menu reference to a QMenu instance.

        Parameters
        ----------
        menu: str, QMenu, QMenuBar, or None
            str: looked up by name via get_menu
            QMenu/QMenuBar: returned as-is
            None + auto=True: returns the default menu (creating one if needed)
            None + auto=False: returns None
        """
        if menu is not None:
            if isinstance(menu, str):
                return self.get_menu(menu)
            if not isinstance(menu, (QtWidgets.QMenu, QtWidgets.QMenuBar)):
                raise TypeError(f'menu must be None, a str, QMenu, or QMenuBar, got {type(menu)}')
            return menu
        return self.menu if auto else None

    def _resolve_action(self, action: Union[str, 'QAction', WidgetActionProxy, None]) -> Union['QAction', None]:
        """Resolve an action reference to a QAction instance.

        Parameters
        ----------
        action: str, QAction, WidgetActionProxy, or None
            str: looked up by name via get_action
            WidgetActionProxy: unwrapped to its underlying QAction
            QAction: returned as-is
            None: returned as None
        """
        if action is None:
            return None
        if isinstance(action, str):
            action = self.get_action(action)
        if isinstance(action, WidgetActionProxy):
            return action._action
        if isinstance(action, QtWidgets.QMenu):
            return action.menuAction()
        if not isinstance(action, QtQAction):
            raise TypeError(f'action must be None, a str, QAction, WidgetActionProxy, or QMenu, got {type(action)}')
        return action

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

    def add_action(self, short_name: str = '', name: str = '',
                   icon_name: Union[str, Path, QtGui.QIcon] = '', tip='',
                   checkable=False,
                   checked=False,
                   toolbar: Union[str, QtWidgets.QToolBar, None]=None,
                   menu: Union[str, QtWidgets.QMenu, None] = None,
                   visible=True, shortcut: Union[str, QtCore.Qt.Key, QtGui.QKeySequence]=None,
                   auto_toolbar=True, auto_menu=False,
                   enabled=True, icon_checked: Union[str, Path, QtGui.QIcon] = None,
                   icon_color: Union[QtGui.QColor, bytes, str]=None,
                   icon_checked_color: Union[QtGui.QColor, bytes, str]=None,
                   flip_h: bool = False,
                   flip_v: bool = False,
                   before: Union[str, 'QAction', WidgetActionProxy, None] = None,
                   action: QtQAction | QtWidgets.QWidgetAction = None,
                   fill: bool = None,
                   rotate: int = 0
                   ):
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
        shortcut: str, QKey or QKeySequence
            Using this shortcut will trigger the action
        auto_toolbar: bool
            if True add this action to the defined toolbar
        auto_menu: bool
            if True add this action to the defined menu
        enabled: bool
            set the enabled state of this action
        icon_checked: : str / Path / QtGui.QIcon / enum name
            str/Path: the png file name/path to produce the icon
            QtGui.QIcon: the instance of a QIcon element
            ThemeIcon enum: the value of QtGui.QIcon.ThemeIcon (requires Qt>=6.7)
            Optional, if set, will be the icon when the action is checked
        icon_color: QtGui.QColor / str
            color to be applied (if possible) to the unchecked icon
        icon_checked_color: QtGui.QColor / str
            color to be applied to the checked icon (if any)
        flip_h: bool
            mirror the icon horizontally (left ↔ right)
        flip_v: bool
            mirror the icon vertically (top ↔ bottom)
        rotate: int
            rotate the icon by the given value in degree
        before: str, QAction, WidgetActionProxy, or None, optional
            if set, the action is inserted before this action in the toolbar/menu;
            accepts a short_name str, a QAction instance, or a WidgetActionProxy
        action: QAction, QWidgetAction, optional
        fill: bool, optional
            Fill or not the icon, if None left to the user configuration
        rotate: int, optional
            Rotate the icon by this value in degree

        See Also
        --------
        affect_to, pymodaq.resources.QtDesigner_Ressources.icon_library,
        pymodaq.utils.managers.action_manager.add_action
        """
        toolbar = self._resolve_toolbar(toolbar, auto=auto_toolbar)
        menu = self._resolve_menu(menu, auto=auto_menu)
        before = self._resolve_action(before)

        self._actions[short_name] = addaction(name, icon_name, tip, checkable=checkable,
                                              checked=checked, toolbar=toolbar, menu=menu,
                                              visible=visible, shortcut=shortcut, enabled=enabled,
                                              icon_checked=icon_checked,
                                              icon_color=icon_color,
                                              icon_checked_color=icon_checked_color,
                                              flip_h=flip_h,
                                              flip_v=flip_v,
                                              before=before,
                                              action=action,
                                              fill=fill,
                                              rotate=rotate)
        return self._actions[short_name]

    def add_widget(self, short_name, klass: Union[str, QtWidgets.QWidget, object], *args, tip='',
                   toolbar: Union[str, QtWidgets.QToolBar] = None, visible=True, signal_str=None,
                   slot: Callable=None, enabled=True, auto_toolbar=True,
                   **kwargs) -> Union[WidgetActionProxy, QtWidgets.QWidget]:
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
        toolbar = self._resolve_toolbar(toolbar, auto=auto_toolbar)

        widget = addwidget(klass, *args, tip=tip, toolbar=toolbar, visible=visible, signal_str=signal_str,
                           slot=slot, enabled=enabled, **kwargs)

        if widget is not None:
            self._actions[short_name] = widget
        else:
            warnings.warn(UserWarning(f'Impossible to add the widget {short_name} and type {klass} to the toolbar'))
        return widget

    def add_menu(self, short_name: str, title: str = '',
                 parent_menu: QtWidgets.QMenuBar | QtWidgets.QMenu | str = None,
                 icon_name: Union[str, Path, QtGui.QIcon] = '', auto_menu=True,
                 menu: QtWidgets.QMenu = None,
                 before: Union[QtWidgets.QMenu, str, None] = None) -> QtWidgets.QMenu:
        """Create and add a menu to a parent menu

        Parameters
        ----------
        short_name: str
            the name as referenced in the dict self._menus
        title: str, optional
            Displayed title of the menu. When *menu* is also provided and *title*
            is non-empty, the title overrides the instance's own title.
        parent_menu: QMenuBar, QMenu, str, optional
            the parent menu or menubar where this menu should be added. If None, uses the default menu
        icon_name: str / Path / QtGui.QIcon / enum name, optional
            str/Path: the png file name/path to produce the icon
            QtGui.QIcon: the instance of a QIcon element
            ThemeIcon enum: the value of QtGui.QIcon.ThemeIcon (requires Qt>=6.7)
        auto_menu: bool
            if True add this menu to the defined parent menu
        menu: QMenu, optional
            an existing QMenu instance to register instead of creating a new one.
        before: QMenu, str, or None, optional
            if specified, the new menu will be inserted before this menu (by instance or short_name);
            if None the menu is appended at the end

        Returns
        -------
        QtWidgets.QMenu
            The created (or provided) menu

        See Also
        --------
        add_action, get_menu
        """
        if auto_menu and parent_menu is None:
            parent_menu = self._menu
        elif isinstance(parent_menu, str):
            parent_menu = self.get_menu(parent_menu)
        before = self._resolve_menu(before, auto=False)

        if menu is None:
            new_menu = QtWidgets.QMenu(title, parent=parent_menu)
        else:
            new_menu = menu
            if title:
                new_menu.setTitle(title)

        # Set icon if provided
        if icon_name and icon_name != '':
            if isinstance(icon_name, QtGui.QIcon):
                new_menu.setIcon(icon_name)
            else:
                new_menu.setIcon(create_icon(icon_name))

        # Add to parent menu if specified
        if parent_menu is not None:
            if before is None:
                parent_menu.addMenu(new_menu)
            else:
                parent_menu.insertMenu(before.menuAction(), new_menu)

        # Store reference
        self._menus[short_name] = new_menu
        if len(self._menus) == 1:
            self.set_menu(new_menu)

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

    def add_toolbar(self, short_name: str, title: str = '', parent: QtWidgets.QWidget = None,
                    toolbar: QtWidgets.QToolBar = None,
                    area=QtCore.Qt.ToolBarArea.TopToolBarArea, add_break=True,
                    before: Union[str, QtWidgets.QToolBar, None] = None) -> QtWidgets.QToolBar:
        """Create and add a toolbar

        Parameters
        ----------
        short_name: str
            the name as referenced in the dict self._toolbars
        title: str, optional
            Displayed title of the toolbar
        parent: QWidget, optional
            parent widget for the toolbar (typically a QMainWindow)
        toolbar: QToolbar, optional
            A given toolbar, if None, it is created
        area: Qt.ToolBarArea, optional
            the area where this toolbar should be added, valid only for a QMainWindow parent
        add_break: bool, optional
            If True, a toolbar break is added in the given area before adding the toolbar, valid only for a
            QMainWindow parent
        before: str or QToolBar or None, optional
            if specified, the new toolbar will be inserted before this toolbar (by instance or short_name)
        Returns
        -------
        QtWidgets.QToolBar
            The created toolbar

        See Also
        --------
        add_action, get_toolbar
        """
        before = self._resolve_toolbar(before, auto=False)

        if isinstance(parent, QtWidgets.QMainWindow) and add_break:
            parent.addToolBarBreak(area)
        if toolbar is None:
            toolbar = QtWidgets.QToolBar(title, parent)
        else:
            toolbar.setParent(parent)

        if isinstance(parent, QtWidgets.QMainWindow):
            if before is None:
                parent.addToolBar(area, toolbar)
            else:
                parent.insertToolBar(before, toolbar)
        self._toolbars[short_name] = toolbar
        return toolbar

    def set_toolbar(self, toolbar: Union[QtWidgets.QToolBar, str]):
        """Set the default toolbar

        Parameters
        ----------
        toolbar: QtWidgets.QToolBar or str
            The toolbar to set as default
        """
        if isinstance(toolbar, str):
            toolbar = self.get_toolbar(toolbar)
        self._toolbar = toolbar

    def set_menu(self, menu):
        """Set the default menu

        Parameters
        ----------
        menu: QtWidgets.QMenu
            The menu to set as default
        """
        self._menu = menu

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

    def get_action(self, name) -> Union[QAction, WidgetActionProxy]:
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
        if self._toolbar is None:
            if len(self.toolbars_names) != 0:
                self._toolbar = self.toolbars[0]
            else:
                self._toolbar = self.add_toolbar('default', 'Default')
        return self._toolbar

    @property
    def menu(self) -> QtWidgets.QMenu:
        """Get the default menu"""
        if self._menu is None:
            if len(self.menus_names) != 0:
                self._menu = self.menus[0]
            else:
                self._menu = self.add_menu('default', 'Default')
        return self._menu

    def affect_to(self, action_name: Union[str, QAction, WidgetActionProxy], obj: Union[QtWidgets.QToolBar, QtWidgets.QMenu]):
        """Affect action to an object either a toolbar or a menu

        Parameters
        ----------
        action_name: str
            The action name as defined in setup_actions
        obj: QToolbar or QMenu
            The object where to add the action
        """
        if isinstance(obj, (QtWidgets.QToolBar, QtWidgets.QMenu)):
            if isinstance(action_name, QAction):
                obj.addAction(action_name)
            elif isinstance(action_name, WidgetActionProxy):
                obj.addAction(action_name._action)
            else:
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
                    if slot is not None:
                        getattr(self._actions[name], signal).disconnect(slot)
                    else:
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
            if hasattr(self._actions[action_name], 'icon_checked'):
                self._actions[action_name].set_icon()
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
            if hasattr(self._actions[action_name], 'widget'):
                self._actions[action_name].widget.setEnabled(enabled)  # action proxy with widget
            else:
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

import warnings
from collections.abc import Iterable
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Iterable as IterableType, Optional, Union, OrderedDict as OrderedDictType

import qt_themes
from multipledispatch import dispatch
from multipledispatch.dispatcher import MethodDispatcher, str_signature
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtWidgets import QAction as QtQAction

from pymodaq_gui.qt_utils import apply_theme, theme_signaller
from pymodaq_gui.utils.styling import create_icon, create_color, as_theme_role, get_current_theme
from pymodaq_utils.utils import find_keys_from_val
from pymodaq_utils.warnings import deprecation_msg
from pymodaq_utils.config import GlobalConfig as Config

try:
    from pymodaq_gui.resources.material_icons import MaterialIcon
except ImportError:
    pass  #this could happen when creating /importing new MaterialIcons

config = Config()

TOOLBAR_BUTTON_STYLES = {
    'icon_only': QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly,
    'text_only': QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly,
    'text_beside_icon': QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon,
    'text_under_icon': QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon,
    'follow_style': QtCore.Qt.ToolButtonStyle.ToolButtonFollowStyle,
}
TOOLBAR_BUTTON_STYLE_LABELS = {
    'icon_only': 'Icons only',
    'text_only': 'Text only',
    'text_beside_icon': 'Text beside icons',
    'text_under_icon': 'Text under icons',
    'follow_style': 'Follow system style',
}


def get_toolbar_button_style() -> QtCore.Qt.ToolButtonStyle | None:
    """The toolbar button style set in the configuration, None if it is not set or not valid"""
    name = config.get(('gui', 'style', 'toolbar_button_style'), [None])[0]
    return TOOLBAR_BUTTON_STYLES.get(name)


class ToolbarStyleSignaller(QtCore.QObject):
    style_changed = QtCore.Signal(object)


toolbar_style_signaller = ToolbarStyleSignaller()


class ToolbarStyleChecks(QtCore.QObject):
    """Keeps the checkable toolbar style actions in sync, lives as long as the menu it is parented to"""

    def __init__(self, actions: dict[str, QtGui.QAction], parent: QtCore.QObject) -> None:
        super().__init__(parent)
        self._actions = actions
        toolbar_style_signaller.style_changed.connect(self.sync)

    @QtCore.Slot(object)
    def sync(self, style: QtCore.Qt.ToolButtonStyle) -> None:
        for name, action in self._actions.items():
            action.setChecked(TOOLBAR_BUTTON_STYLES[name] == style)


class ThemeChecks(QtCore.QObject):
    """Keeps the checkable theme actions in sync, lives as long as the menu it is parented to"""

    def __init__(self, actions: dict[str, QtGui.QAction], themes: dict[str, qt_themes.Theme],
                 parent: QtCore.QObject):
        super().__init__(parent)
        self._actions = actions
        self._themes = themes
        theme_signaller.theme_changed.connect(self.sync)

    @QtCore.Slot(object)
    def sync(self, theme: qt_themes.Theme):
        for name, action in self._actions.items():
            action.setChecked(self._themes[name] == theme)


class MenuIconRefresher(QtCore.QObject):
    """Rebuilds a menu icon on theme change, lives as long as the menu it is parented to"""

    def __init__(self, icon_name: Union[str, Path], parent: QtWidgets.QMenu):
        super().__init__(parent)
        self._icon_name = icon_name
        theme_signaller.theme_changed.connect(self.refresh)

    @QtCore.Slot(object)
    def refresh(self, _theme=None):
        self.parent().setIcon(create_icon(self._icon_name))


resource_folder = Path(__file__).parent.parent.joinpath('resources')
QtCore.QDir.addSearchPath('icons', str(resource_folder.joinpath('icon_library')))


class QAction(QtQAction):
    """
    QAction subclass to mimic signals as pushbuttons. Done to be sure of backcompatibility
    when I moved from pushbuttons to QAction
    """
    def __init__(self, icon_unchecked: Union[None, str, Path, QtGui.QIcon],
                 name: str = '',
                 icon_checked: Optional[Union[str, Path, QtGui.QIcon]] = None,
                 icon_color: Optional[Union[QtGui.QColor, bytes, str]] = None,
                 icon_checked_color: Optional[Union[QtGui.QColor, bytes, str]] = None,
                 flip_h: bool = False,
                 flip_v: bool = False,
                 rotate: int = 0,
                 fill: Optional[bool] = None,
                 follow_theme: bool = True,
                 ) -> None:
        super().__init__(name)
        # What the icon is made of, kept so it can be rebuilt (refresh_icon) when the
        # theme changes: icons bake their colours at construction. With follow_theme,
        # theme colours are kept by name (see as_theme_role); otherwise they are
        # resolved now and kept as fixed colours.
        self._icon_spec = None
        # Only icons given by name/path are rebuilt: an icon instance keeps the
        # palette it was built under, rebuilding it would not follow the theme.
        self._icon_rebuildable = isinstance(icon_unchecked, (str, Path))
        self._icon_set_explicitly = False
        self._checked_icon_connected = False
        if icon_unchecked is not None:
            keep = as_theme_role if follow_theme else create_color
            self._icon_spec = dict(icon_unchecked=icon_unchecked, icon_checked=icon_checked,
                                   icon_color=keep(icon_color),
                                   icon_checked_color=keep(icon_checked_color),
                                   flip_h=flip_h, flip_v=flip_v, rotate=rotate, fill=fill)
            self._build_icons()
            self.setIcon(self.icon_unchecked)
            if self._icon_rebuildable:
                # follow theme changes (apply_theme), whichever window triggers them;
                # a slot of this QObject, so Qt disconnects it when the action is deleted
                theme_signaller.theme_changed.connect(self.refresh_icon)

    def _build_icons(self):
        spec = self._icon_spec
        transforms = dict(flip_h=spec['flip_h'], flip_v=spec['flip_v'], rotate=spec['rotate'],
                          fill=spec['fill'])
        self.icon_unchecked = create_icon(spec['icon_unchecked'], spec['icon_color'],
                                          spec['icon_checked_color'], **transforms)
        icon_checked = spec['icon_checked']
        if icon_checked is not None and not isinstance(icon_checked, QtGui.QIcon):
            icon_checked = create_icon(icon_checked, spec['icon_checked_color'],
                                       spec['icon_checked_color'], **transforms)
            if isinstance(spec['icon_unchecked'], MaterialIcon):
                self.icon_unchecked.set_icon(icon_checked, state=QtGui.QIcon.State.On)
            else:
                self.icon_checked = icon_checked
                if not self._checked_icon_connected:
                    self.triggered.connect(lambda: self.set_icon())
                    self._checked_icon_connected = True

    @QtCore.Slot()
    @QtCore.Slot(object)
    def refresh_icon(self, _theme=None):
        """Rebuild the icon(s) with the current theme colours. Called automatically
        when :func:`pymodaq_gui.qt_utils.apply_theme` changes the theme.

        No-op for actions created without icon or with an icon instance (QIcon,
        MaterialIcon) rather than a name, and for actions whose icon was then replaced
        with ``set_icon(icon)``: their owner manages that icon (e.g. a state colour),
        rebuilding the original one would undo it.
        """
        if self._icon_spec is None or not self._icon_rebuildable or self._icon_set_explicitly:
            return
        self._build_icons()
        if self.isChecked() and getattr(self, 'icon_checked', None) is not None:
            self.setIcon(self.icon_checked)
        else:
            self.setIcon(self.icon_unchecked)

    def click(self) -> None:
        deprecation_msg("click for PyMoDAQ's QAction is deprecated, use *trigger*",
                        stacklevel=3)
        self.trigger()

    @property
    def clicked(self) -> Any:
        deprecation_msg("clicked for PyMoDAQ's QAction is deprecated, use *trigger*",
                        stacklevel=3)
        return self.triggered

    def connect_to(self, slot: Callable[..., Any]) -> None:
        """Connect the *triggered* signal to a slot"""
        self.triggered.connect(slot)

    def set_icon(self, icon_name: Optional[Union[str, Path, QtGui.QIcon]] = None,
                 icon_color: Optional[Union[QtGui.QColor, bytes, str]] = None) -> None:
        """Set the icon of the action, by default the one of the current checked state"""
        if icon_name is None:
            if self.isChecked():
                icon_name = self.icon_checked
            else:
                icon_name = self.icon_unchecked
            if icon_color is None:
                # Already built with their colours: passing them through create_icon
                # again would reset a MaterialIcon to the default palette colour.
                self.setIcon(icon_name)
                return
        else:
            self._icon_set_explicitly = True
        self.setIcon(create_icon(icon_name, icon_color))

    def __repr__(self) -> str:
        return f'QAction {self.text()}'


class WidgetActionProxy(QtWidgets.QWidget):
    """ Wrapper class of a Widget and its associated toolbar Action.
    All methods call are forwarded to the wrapped Widget. Even its class name
    is copied.

    Only the setVisible method is different, as the Action need to be hidden.
    (monkey-patching setVisible on the widget wasn't compatible with PySide6)
    """
    def __init__(self, widget : QtWidgets.QWidget, action : QtWidgets.QAction) -> None:
        super().__init__(widget.parent())  # type: ignore[arg-type]
        self.setParent(widget)

        self._widget = widget
        self._action = action

    def setVisible(self, visible : bool) -> None:
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

    def __getattr__(self, name : str) -> Any:
        return getattr(self._widget, name)

    @property  # type: ignore[misc]
    def __class__(self):  # no annotation: a runtime type checker would recurse on this very property
        return self._widget.__class__


def addaction(name: str = '', icon_name: Union[str, Path, QtGui.QIcon, None] = '', tip: str = '',
              checkable: bool = False, checked: bool = False,
              slot: Optional[Callable[..., Any]] = None, toolbar: Optional[QtWidgets.QToolBar] = None,
              menu: Optional[QtWidgets.QMenu] = None, visible: bool = True,
              shortcut: Optional[Union[str, QtCore.Qt.Key, QtGui.QKeySequence]] = None,
              enabled: bool = True, icon_checked: Optional[Union[str, Path, QtGui.QIcon]] = None,
              icon_color: Optional[Union[QtGui.QColor, bytes, str]] = None,
              icon_checked_color: Optional[Union[QtGui.QColor, bytes, str]] = None,
              flip_h: bool = False,
              flip_v: bool = False,
              before: Optional[QtQAction] = None,
              action: Optional[QAction] = None,
              fill: Optional[bool] = None,
              rotate: int = 0,
              follow_theme: bool = True,
              ) -> QAction:
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
    icon_color: ThemeColor / str / QtGui.QColor
        color to be applied (if possible) to the unchecked icon. Give theme colours by
        name (ThemeColor.GREEN or 'green') so they follow theme changes
    icon_checked_color: ThemeColor / str / QtGui.QColor
        color to be applied to the checked icon (if any), same as icon_color
    flip_h: bool
        mirror the icon horizontally (left ↔ right)
    flip_v: bool
        mirror the icon vertically (top ↔ bottom)
    rotate: int
        rotate the icon by the given value in degrees
    before: QAction, optional
        if set, the action is inserted before this action in the toolbar/menu;
        if None the action is appended at the end
    action: pymodaq_gui.managers.action_manager.QAction, optional
        An existing action to configure instead of creating a new one
    fill: bool, optional
        Fill or not the icon, if None left to the user configuration
    rotate: int, optional
        Rotate the icon by this value in degree
    follow_theme: bool
        True (default): colours given as theme colours (:class:`~pymodaq_gui.utils.styling.ThemeColor`,
        their names, or values resolved from the theme) follow theme changes. False: the
        colours are resolved once, here, and kept as they are

    Returns
    -------
    QAction
        The created (or given) action
    """
    if action is None:
        if icon_name is None or icon_name == '':
            action = QAction(None, name)
        else:
            action = QAction(icon_name, name, icon_checked=icon_checked,
                             icon_color=icon_color, icon_checked_color=icon_checked_color,
                             flip_h=flip_h, flip_v=flip_v, rotate=rotate, fill=fill,
                             follow_theme=follow_theme)

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
    if action.parent() is None and (toolbar is not None or menu is not None):
        # an unparented action is never deleted while a slot connected to it (often a lambda holding the
        # UI) is alive: it would keep the whole UI alive after it is closed
        action.setParent(toolbar if toolbar is not None else menu)
    if shortcut is not None:
        action.setShortcut(shortcut)
    action.setVisible(visible)
    action.setEnabled(enabled)
    return action


def addwidget(klass: Union[str, QtWidgets.QWidget, Callable[..., QtWidgets.QWidget]], *args: Any, tip: str = '',
              toolbar: Optional[QtWidgets.QToolBar] = None,
              visible: bool = True, signal_str: Optional[str] = None,
              slot: Optional[Callable[..., Any]] = None,
              setters: Optional[dict] = None, enabled: bool = True,
              before: Optional[QtQAction] = None,
              **kwargs: Any) -> Optional[Union[WidgetActionProxy, QtWidgets.QWidget]]:
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
    before: QAction optional
        if not None, insert this widget before this action
    kwargs: dict
        variable named arguments used as is in the widget constructor
    setters: dict
        method/value pair of the widget (for instance setMaximumWidth)
    Returns
    -------
    QtWidgets.QWidget
        The widget (wrapped in a WidgetActionProxy if added to a toolbar), None if it could not be created
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
        action: QtWidgets.QAction
        if before is None:
            action = toolbar.addWidget(widget)  # type: ignore[assignment]
        else:
            action = toolbar.insertWidget(before, widget)  # type: ignore[assignment]
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


class _InstanceMethodDispatcher(MethodDispatcher):
    """ MethodDispatcher that does not store the instance it is accessed from

    multipledispatch's MethodDispatcher, shared by all instances, keeps the last one in an attribute: the last UI
    that called each method stayed alive after it was closed.
    """
    __slots__ = ()

    def __get__(self, instance: Any, owner: Any) -> Any:
        if instance is None:
            return self
        return lambda *args, **kwargs: self._call(instance, *args, **kwargs)

    def _call(self, instance: Any, *args: Any, **kwargs: Any) -> Any:
        types = tuple([type(arg) for arg in args])
        func = self.dispatch(*types)
        if not func:
            raise NotImplementedError(f'Could not find signature for {self.name}: <{str_signature(types)}>')
        return func(instance, *args, **kwargs)


def _delete_later(obj: QtCore.QObject, only_if_orphan: bool = False) -> None:
    try:
        if not only_if_orphan or obj.parent() is None:
            obj.deleteLater()
    except RuntimeError:  # the C++ object was already deleted (e.g. with its parent)
        pass


class ActionManager:
    """MixIn Class to be used by all UserInterface to manage their QActions and the action they are connected to

    Parameters
    ----------
    toolbar: QToolbar, optional
        The toolbar to use as default
    menu: QMenu, option
        The menu to use as default
    """
    def __init__(self, toolbar: Optional[QtWidgets.QToolBar] = None, menu: Optional[QtWidgets.QMenu] = None) -> None:
        self._actions: OrderedDictType[str, QAction] = OrderedDict([])
        self._menus: OrderedDictType[str, QtWidgets.QMenu] = OrderedDict([])
        self._menu_icon_names: dict[str, Union[str, Path]] = {}
        self._toolbars: OrderedDictType[str, QtWidgets.QToolBar] = OrderedDict([])

        self._toolbar: Optional[QtWidgets.QToolBar] = None
        self._menu: Optional[QtWidgets.QMenu] = None

        self._action_group_buttons: dict[str, QtWidgets.QToolButton] = {}
        self._action_group_secondary: dict[str, list[str]] = {}

        if toolbar is not None:
            self.reference_toolbar('default', toolbar)
            self.set_toolbar(toolbar)
        if menu is not None:
            self.reference_menu('default', menu)
            self.set_menu(menu)

    def delete_actions(self) -> None:
        """Schedule the deletion of all the QActions referenced in this manager, and of its toolbars and
        menus that have no parent

        A Qt object keeps the slots connected to its signals (often lambdas holding the manager) alive as
        long as the C++ object exists. Unparented actions, toolbars or menus therefore keep the whole UI that
        created them alive after it is closed, out of reach of Python's garbage collector. Call this when the
        UI is closed for good.

        .. versionadded:: 5.3.9
        """
        for action in self._actions.values():
            _delete_later(action)
        for widget in list(self._toolbars.values()) + list(self._menus.values()):
            # the ones with a parent are owned (and deleted) by a window that may not be closed
            _delete_later(widget, only_if_orphan=True)

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

    def _resolve_action(self, action: Union[str, 'QAction', WidgetActionProxy, None]) -> Optional[QtQAction]:
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

    def setup_actions(self) -> None:
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
                   icon_name: Union[str, Path, QtGui.QIcon] = '', tip: str = '',
                   checkable: bool = False,
                   checked: bool = False,
                   toolbar: Union[str, QtWidgets.QToolBar, None] = None,
                   menu: Union[str, QtWidgets.QMenu, None] = None,
                   visible: bool = True,
                   shortcut: Optional[Union[str, QtCore.Qt.Key, QtGui.QKeySequence]] = None,
                   auto_toolbar: bool = True, auto_menu: bool = False,
                   enabled: bool = True, icon_checked: Optional[Union[str, Path, QtGui.QIcon]] = None,
                   icon_color: Optional[Union[QtGui.QColor, bytes, str]] = None,
                   icon_checked_color: Optional[Union[QtGui.QColor, bytes, str]] = None,
                   flip_h: bool = False,
                   flip_v: bool = False,
                   before: Union[str, 'QAction', WidgetActionProxy, None] = None,
                   action: Optional[QAction] = None,
                   fill: Optional[bool] = None,
                   rotate: int = 0,
                   follow_theme: bool = True,
                   ) -> QAction:
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

            - None: adds to the default toolbar (self._toolbar)
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
        icon_checked: str / Path / QtGui.QIcon / enum name
            str/Path: the png file name/path to produce the icon
            QtGui.QIcon: the instance of a QIcon element
            ThemeIcon enum: the value of QtGui.QIcon.ThemeIcon (requires Qt>=6.7)
            Optional, if set, will be the icon when the action is checked
        icon_color: ThemeColor / str / QtGui.QColor
            color to be applied (if possible) to the unchecked icon. Give theme colours by
            name (ThemeColor.GREEN or 'green') so they follow theme changes
        icon_checked_color: ThemeColor / str / QtGui.QColor
            color to be applied to the checked icon (if any), same as icon_color
        flip_h: bool
            mirror the icon horizontally (left ↔ right)
        flip_v: bool
            mirror the icon vertically (top ↔ bottom)
        rotate: int
            rotate the icon by the given value in degree
        before: str, QAction, WidgetActionProxy, or None, optional
            if set, the action is inserted before this action in the toolbar/menu;
            accepts a short_name str, a QAction instance, or a WidgetActionProxy
        action: pymodaq_gui.managers.action_manager.QAction, optional
            An existing action to register instead of creating a new one
        fill: bool, optional
            Fill or not the icon, if None left to the user configuration
        rotate: int, optional
            Rotate the icon by this value in degree
        follow_theme: bool
            True (default): colours given as theme colours (:class:`~pymodaq_gui.utils.styling.ThemeColor`,
            their names, or values resolved from the theme) follow theme changes. False: the
            colours are resolved once, here, and kept as they are

        Returns
        -------
        QAction
            The created action, also referenced as *short_name*

        See Also
        --------
        affect_to
        """
        toolbar_obj = self._resolve_toolbar(toolbar, auto=auto_toolbar)
        menu_obj = self._resolve_menu(menu, auto=auto_menu)
        before_action = self._resolve_action(before)

        self._actions[short_name] = addaction(name, icon_name, tip, checkable=checkable,
                                              checked=checked, toolbar=toolbar_obj, menu=menu_obj,
                                              visible=visible, shortcut=shortcut, enabled=enabled,
                                              icon_checked=icon_checked,
                                              icon_color=icon_color,
                                              icon_checked_color=icon_checked_color,
                                              flip_h=flip_h,
                                              flip_v=flip_v,
                                              before=before_action,
                                              action=action,
                                              fill=fill,
                                              rotate=rotate,
                                              follow_theme=follow_theme)
        return self._actions[short_name]

    def refresh_icons(self) -> None:
        """Rebuild the icons of all managed actions and menus with the current theme colours.

        Icons bake their colours when created. This is done automatically when
        :func:`pymodaq_gui.qt_utils.apply_theme` changes the theme; call it if the
        palette was changed by other means. Only icons given by name are rebuilt,
        see :meth:`QAction.refresh_icon`.
        """
        for action in self._actions.values():
            if isinstance(action, QAction):
                action.refresh_icon()
        for short_name, icon_name in self._menu_icon_names.items():
            menu = self._menus.get(short_name)
            if menu is not None:
                menu.setIcon(create_icon(icon_name))

    def remove_action(self, toolbar: QtWidgets.QToolBar | str | None = None,
                      action: str | QAction | WidgetActionProxy | None = None) -> None:
        """Remove an action from a toolbar and forget it

        Parameters
        ----------
        toolbar: QToolBar, str or None
            The toolbar (or its name) to remove the action from. If None, the action is not removed from a toolbar
        action: str, QAction, WidgetActionProxy or None
            The action (or its short_name) to remove
        """
        toolbar_obj = self._resolve_toolbar(toolbar, auto=False)

        try:
            action_object = self._resolve_action(action)
            if toolbar_obj is not None and action_object is not None:
                toolbar_obj.removeAction(action_object)
            if isinstance(action, str):
                self._actions.pop(action, None)
            else:
                action_str_list = find_keys_from_val(self._actions, action)
                if len(action_str_list) > 0:
                    self._actions.pop(action_str_list[0], None)
        except KeyError:
            pass

    def add_widget(self, short_name: str,
                   klass: Union[str, QtWidgets.QWidget, Callable[..., QtWidgets.QWidget]], *args: Any, tip: str = '',
                   toolbar: Union[str, QtWidgets.QToolBar, None] = None, visible: bool = True,
                   signal_str: Optional[str] = None,
                   slot: Optional[Callable[..., Any]] = None, enabled: bool = True, auto_toolbar: bool = True,
                   before: Union[str, 'QAction', WidgetActionProxy, None] = None,
                   **kwargs: Any) -> Union[WidgetActionProxy, QtWidgets.QWidget]:
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
        before: str, QAction, WidgetActionProxy, or None, optional
            if set, the action is inserted before this action in the toolbar/menu;
            accepts a short_name str, a QAction instance, or a WidgetActionProxy
        kwargs: dict
            variable named arguments passed as is to the widget constructor
        Returns
        -------
        QtWidgets.QWidget
        """
        toolbar_obj = self._resolve_toolbar(toolbar, auto=auto_toolbar)
        before_action = self._resolve_action(before)

        widget = addwidget(klass, *args, tip=tip, toolbar=toolbar_obj, visible=visible, signal_str=signal_str,
                           slot=slot, enabled=enabled,
                           before=before_action,
                           **kwargs)

        if widget is not None:
            self._actions[short_name] = widget
        else:
            warnings.warn(UserWarning(f'Impossible to add the widget {short_name} and type {klass} to the toolbar'))
        return widget  # type: ignore[return-value]  # None (with a warning) if the widget could not be created

    def add_action_group(self, short_name: str, name: str = '',
                         icon_name: Union[str, Path, QtGui.QIcon] = '', tip: str = '',
                         checkable: bool = False, checked: bool = False,
                         icon_checked: Union[str, Path, QtGui.QIcon, None] = None,
                         icon_color: Union[QtGui.QColor, bytes, str, None] = None,
                         icon_checked_color: Union[QtGui.QColor, bytes, str, None] = None,
                         toolbar: Union[str, QtWidgets.QToolBar, None] = None,
                         secondary_actions: IterableType[dict] = (),
                         visible: bool = True, enabled: bool = True,
                         follow_theme: bool = True,
                         ) -> QtWidgets.QToolButton:
        """Add several related actions to a toolbar under a single button, to avoid
        overloading the toolbar with one slot per action.

        The button shows and triggers a *primary* action directly (a regular action,
        created and registered exactly like :meth:`add_action`, so
        :meth:`connect_action`, :meth:`is_action_checked`, :meth:`set_action_checked`
        ... all keep working on its ``short_name`` unchanged). A small dropdown arrow
        next to it reveals the *secondary* actions, each created the same way as
        :meth:`add_action` would from its spec dict, but added only to the dropdown,
        never to a toolbar directly.

        If there are no secondary actions, or none of them is currently visible, the button
        behaves like a plain toolbar action (no dropdown arrow). The arrow reappears as soon as
        a secondary action becomes visible again (e.g. through :meth:`set_action_visible`).

        Parameters
        ----------
        short_name: str
            the name of the primary action, as referenced in self._actions
        name, icon_name, tip, checkable, checked, icon_checked, icon_color,
        icon_checked_color, follow_theme:
            forwarded to :meth:`add_action` for the primary action
        toolbar: str or QToolBar or None
            the toolbar the button is added to (defaults to the default toolbar)
        secondary_actions: iterable of dict
            one spec per dropdown entry, using the same keys as :meth:`add_action`
            (at least ``short_name``); order is preserved in the dropdown menu
        visible, enabled: bool
            forwarded to the primary action

        Returns
        -------
        QtWidgets.QToolButton
            the created button, already added to the toolbar

        See Also
        --------
        add_action
        """
        toolbar_obj = self._resolve_toolbar(toolbar, auto=True)

        primary = self.add_action(short_name, name, icon_name, tip,
                                  checkable=checkable, checked=checked,
                                  toolbar=None, menu=None,
                                  auto_toolbar=False, auto_menu=False,
                                  visible=visible, enabled=enabled,
                                  icon_checked=icon_checked,
                                  icon_color=icon_color,
                                  icon_checked_color=icon_checked_color,
                                  follow_theme=follow_theme)

        button = QtWidgets.QToolButton(toolbar_obj)
        button.setDefaultAction(primary)
        # Unlike actions added via addAction(), this standalone widget is not kept in sync with
        # the toolbar's own toolButtonStyle automatically: apply the current global style now,
        # and keep following later changes, exactly as add_toolbar() does for the toolbar itself.
        style = get_toolbar_button_style()
        button.setToolButtonStyle(style if style is not None
                                  else QtCore.Qt.ToolButtonStyle.ToolButtonFollowStyle)
        toolbar_style_signaller.style_changed.connect(button.setToolButtonStyle)

        secondary_names = []
        if secondary_actions:
            dropdown = QtWidgets.QMenu(button)
            for spec in secondary_actions:
                spec = dict(spec)
                spec_short_name = spec.pop('short_name')
                self.add_action(spec_short_name, toolbar=None, menu=None,
                                auto_toolbar=False, auto_menu=False, **spec)
                dropdown.addAction(self._actions[spec_short_name])
                secondary_names.append(spec_short_name)
            button.setMenu(dropdown)

        self._action_group_buttons[short_name] = button
        self._action_group_secondary[short_name] = secondary_names
        self._refresh_action_group_popup(short_name)

        if toolbar_obj is not None:
            toolbar_obj.addWidget(button)
        return button

    def _refresh_action_group_popup(self, group_name: str) -> None:
        """Show the dropdown arrow of an add_action_group toolbutton only while at least one
        of its secondary actions is visible; hide it (and fall back to a plain button) otherwise.

        Called automatically by :meth:`add_action_group` and by :meth:`set_action_visible` on any
        action that belongs to a group, so toolbars built from dynamically shown/hidden actions
        stay tidy without extra bookkeeping from the caller.
        """
        button = self._action_group_buttons.get(group_name)
        if button is None:
            return
        secondary_names = self._action_group_secondary.get(group_name, [])
        if any(self._actions[name].isVisible() for name in secondary_names):
            button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        else:
            button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.DelayedPopup)

    def add_menu(self, short_name: str, title: str = '',
                 parent_menu: QtWidgets.QMenuBar | QtWidgets.QMenu | str | None = None,
                 icon_name: Union[str, Path, QtGui.QIcon] = '', auto_menu: bool = True,
                 menu: Optional[QtWidgets.QMenu] = None,
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
        parent: Union[QtWidgets.QMenuBar, QtWidgets.QMenu, None]
        if isinstance(parent_menu, str):
            parent = self.get_menu(parent_menu)
        elif auto_menu and parent_menu is None:
            parent = self._menu
        else:
            parent = parent_menu
        before = self._resolve_menu(before, auto=False)

        if menu is None:
            new_menu = QtWidgets.QMenu(title, parent=parent)
        else:
            new_menu = menu
            if title:
                new_menu.setTitle(title)

        if new_menu.parent() is None:
            # an unparented menu outlives the UI, and the slots connected to its actions keep the UI alive
            owner = parent if parent is not None else self if isinstance(self, QtWidgets.QWidget) else None
            if owner is not None:
                new_menu.setParent(owner, new_menu.windowFlags())

        # Set icon if provided
        if icon_name and icon_name != '':
            if isinstance(icon_name, QtGui.QIcon):
                new_menu.setIcon(icon_name)
            else:
                new_menu.setIcon(create_icon(icon_name))
                self._menu_icon_names[short_name] = icon_name
                MenuIconRefresher(icon_name, parent=new_menu)

        # Add to parent menu if specified
        if parent is not None:
            if before is None:
                parent.addMenu(new_menu)
            else:
                parent.insertMenu(before.menuAction(), new_menu)

        # Store reference
        self._menus[short_name] = new_menu
        if len(self._menus) == 1:
            self.set_menu(new_menu)

        return new_menu

    def reference_toolbar(self, short_name: str, toolbar: QtWidgets.QToolBar) -> None:
        """ Add an existing toolbar to the list of managed toolbars"""
        if short_name not in self._toolbars:
            self._toolbars[short_name] = toolbar
        else:
            raise KeyError(f'Toolbar {short_name} is already existing')

    def reference_menu(self, short_name: str, menu: QtWidgets.QMenu) -> None:
        """ Add an existing menu to the list of managed menus"""
        if short_name not in self._menus:
            self._menus[short_name] = menu
        else:
            raise KeyError(f'Menu {short_name} is already existing')

    def add_toolbar(self, short_name: str, title: str = '', parent: Optional[QtWidgets.QWidget] = None,
                    toolbar: Optional[QtWidgets.QToolBar] = None,
                    area: QtCore.Qt.ToolBarArea = QtCore.Qt.ToolBarArea.TopToolBarArea, add_break: bool = True,
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
        before_toolbar = self._resolve_toolbar(before, auto=False)

        if isinstance(parent, QtWidgets.QMainWindow) and add_break:
            parent.addToolBarBreak(area)
        if toolbar is None:
            toolbar = QtWidgets.QToolBar(title, parent)
        else:
            toolbar.setParent(parent)

        if isinstance(parent, QtWidgets.QMainWindow):
            if before_toolbar is None:
                parent.addToolBar(area, toolbar)
            else:
                parent.insertToolBar(before_toolbar, toolbar)
        style = get_toolbar_button_style()
        if style is not None:
            toolbar.setToolButtonStyle(style)
        toolbar_style_signaller.style_changed.connect(toolbar.setToolButtonStyle)
        self._toolbars[short_name] = toolbar
        return toolbar

    def setup_toolbar_style_menu(self, parent_menu: QtWidgets.QMenu | str) -> None:
        """Add a 'Toolbar style' submenu choosing how the toolbar buttons of all windows are drawn"""
        style_menu = self.add_menu('toolbar_style', 'Toolbar style', parent_menu=parent_menu)
        group = QtGui.QActionGroup(style_menu)
        group.setExclusive(True)

        current_name = config.get(('gui', 'style', 'toolbar_button_style'), ['icon_only'])[0]
        actions: dict[str, QtGui.QAction] = {}
        for name, label in TOOLBAR_BUTTON_STYLE_LABELS.items():
            action: QtGui.QAction = style_menu.addAction(label)  # type: ignore[assignment]
            action.setCheckable(True)
            action.setChecked(name == current_name)
            action.setActionGroup(group)
            action.triggered.connect(lambda _checked, n=name: self.apply_toolbar_style(n))
            actions[name] = action
        ToolbarStyleChecks(actions, parent=style_menu)

    def setup_theme_menu(self, parent_menu: QtWidgets.QMenu | str) -> None:
        """Add a 'Theme' submenu choosing the qt_themes theme of the whole application"""
        theme_menu = self.add_menu('theme', 'Theme', parent_menu=parent_menu)
        group = QtGui.QActionGroup(theme_menu)
        group.setExclusive(True)

        themes = dict(sorted(qt_themes.get_themes().items()))
        current = get_current_theme()
        actions = {}
        for name in themes:
            action = theme_menu.addAction(name.replace('_', ' ').capitalize())
            action.setCheckable(True)
            action.setChecked(themes[name] == current)
            action.setActionGroup(group)
            action.triggered.connect(lambda _checked, n=name: self.apply_qt_theme(n))
            actions[name] = action
        ThemeChecks(actions, themes, parent=theme_menu)

    def apply_qt_theme(self, name: str) -> None:
        """Apply a qt_themes theme to the whole application and persist it as the default"""
        if apply_theme(name) is None:
            return
        # pymodaq uses the first element of the configured list
        themes = list(config('gui', 'style', 'theme'))
        config['gui', 'style', 'theme'] = [name] + [t for t in themes if t != name]
        config.save()

    def apply_toolbar_style(self, name: str) -> None:
        """Persist the toolbar button style and apply it to all toolbars"""
        config['gui', 'style', 'toolbar_button_style'] = [name]
        config.save()
        toolbar_style_signaller.style_changed.emit(TOOLBAR_BUTTON_STYLES[name])

    def set_toolbar(self, toolbar: Union[QtWidgets.QToolBar, str]) -> None:
        """Set the default toolbar

        Parameters
        ----------
        toolbar: QtWidgets.QToolBar or str
            The toolbar to set as default
        """
        if isinstance(toolbar, str):
            toolbar = self.get_toolbar(toolbar)
        self._toolbar = toolbar

    def set_menu(self, menu: QtWidgets.QMenu | str) -> None:
        """Set the default menu

        Parameters
        ----------
        menu: QtWidgets.QMenu
            The menu to set as default
        """
        if isinstance(menu, str):
            menu = self.get_menu(menu)
        self._menu = menu

    def set_action_text(self, action_name: str, text: str) -> None:
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
        """Get all the actions (and widgets added to a toolbar) managed here"""
        return list(self._actions.values())

    @property
    def actions_names(self) -> list[str]:
        """Get all the action names"""
        return list(self._actions.keys())

    def get_action(self, name: str) -> Union[QAction, WidgetActionProxy]:
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

    def has_action(self, action_name: str) -> bool:
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

    def affect_to(self, action_name: Union[str, QAction, WidgetActionProxy],
                  obj: Union[QtWidgets.QToolBar, QtWidgets.QMenu]) -> None:
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

    def connect_action(self, name: str, slot: Optional[Callable[..., Any]] = None, connect: bool = True,
                       signal_name: str = '') -> None:
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
    def is_action_visible(self, action_name: str) -> bool:
        """Check the visibility of a given action or the list of an action"""
        if action_name in self._actions:
            return self._actions[action_name].isVisible()
        else:
            raise KeyError(f'The action with name: {action_name} is not referenced'
                           f' in the actions list: {self._actions}')

    @dispatch(Iterable)  # type: ignore[no-redef]
    def is_action_visible(self, actions_name: IterableType) -> bool:
        """Check the visibility of a list of actions

        Returns
        -------
        bool
            True if all the actions are visible (and for an empty list)
        """
        return all(self.is_action_visible(action_name) for action_name in actions_name)

    @dispatch(str)
    def is_action_checked(self, action_name: str) -> bool:
        """Get the CheckState of a given action or a list of actions"""
        if action_name in self._actions:
            return self._actions[action_name].isChecked()
        else:
            raise KeyError(f'The action with name: {action_name} is not referenced'
                           f' in the actions list: {self._actions}')

    @dispatch(Iterable)  # type: ignore[no-redef]
    def is_action_checked(self, actions_name: IterableType) -> bool:
        """Get the CheckState of a list of actions

        Returns
        -------
        bool
            True if all the actions are checked (and for an empty list)
        """
        return all(self.is_action_checked(action_name) for action_name in actions_name)

    @dispatch(str, bool)
    def set_action_visible(self, action_name: str, visible: bool = True) -> None:
        """Set the visibility of a given action or a list of an action"""
        if action_name in self._actions:
            self._actions[action_name].setVisible(visible)
            for group_name, secondary_names in self._action_group_secondary.items():
                if action_name in secondary_names:
                    self._refresh_action_group_popup(group_name)
        else:
            raise KeyError(f'The action with name: {action_name} is not referenced'
                           f' in the actions list: {self._actions}')

    @dispatch(Iterable, bool)  # type: ignore[no-redef]
    def set_action_visible(self, actions_name: IterableType, visible: bool = True) -> None:
        """Set the visibility of a given action or a list of an action"""
        for action_name in actions_name:
            self.set_action_visible(action_name, visible)

    @dispatch(str, bool)
    def set_action_checked(self, action_name: str, checked: bool = True) -> None:
        """Set the CheckedState of a given action or a list of actions"""
        if action_name in self._actions:
            self._actions[action_name].setChecked(checked)
            if hasattr(self._actions[action_name], 'icon_checked'):
                self._actions[action_name].set_icon()
        else:
            raise KeyError(f'The action with name: {action_name} is not referenced'
                           f' in the actions list: {self._actions}')

    @dispatch(Iterable, bool)  # type: ignore[no-redef]
    def set_action_checked(self, actions_name: IterableType, checked: bool = True) -> None:
        """Set the CheckedState of a given action or a list of actions"""
        for action_name in actions_name:
            self.set_action_checked(action_name, checked)

    @dispatch(str, bool)
    def set_action_enabled(self, action_name: str, enabled: bool = True) -> None:
        """Set the EnabledState of a given action or a list of actions"""
        if action_name in self._actions:
            if hasattr(self._actions[action_name], 'widget'):
                self._actions[action_name].widget.setEnabled(enabled)  # action proxy with widget
            else:
                self._actions[action_name].setEnabled(enabled)
        else:
            raise KeyError(f'The action with name: {action_name} is not referenced'
                           f' in the actions list: {self._actions}')

    @dispatch(Iterable, bool)  # type: ignore[no-redef]
    def set_action_enabled(self, actions_name: IterableType, enabled: bool = True) -> None:
        """Set the EnabledState of a given action or a list of actions"""
        for action_name in actions_name:
            self.set_action_enabled(action_name, enabled)

    @dispatch(str)
    def is_action_enabled(self, action_name: str) -> bool:
        """Get the EnabledState of a given action or a list of actions"""
        if action_name in self._actions:
            return self._actions[action_name].isEnabled()
        else:
            raise KeyError(f'The action with name: {action_name} is not referenced'
                           f' in the actions list: {self._actions}')

    @dispatch(Iterable)  # type: ignore[no-redef]
    def is_action_enabled(self, actions_name: IterableType) -> bool:
        """Get the EnabledState of a list of actions

        Returns
        -------
        bool
            True if all the actions are enabled (and for an empty list)
        """
        return all(self.is_action_enabled(action_name) for action_name in actions_name)


for _dispatcher in vars(ActionManager).values():
    if isinstance(_dispatcher, MethodDispatcher):
        _dispatcher.__class__ = _InstanceMethodDispatcher

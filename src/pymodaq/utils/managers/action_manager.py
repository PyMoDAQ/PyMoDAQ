import warnings

import pymodaq.utils.messenger
from multipledispatch import dispatch
from typing import Union, Callable, List

from qtpy import QtGui, QtWidgets, QtCore
from qtpy.QtWidgets import QAction

from pymodaq.resources.QtDesigner_Ressources import QtDesigner_ressources_rc
from pathlib import Path


def create_icon(icon_name: str):
    icon = QtGui.QIcon()
    if Path(icon_name).is_file():
        icon.addPixmap(QtGui.QPixmap(icon_name), QtGui.QIcon.Normal,
                       QtGui.QIcon.Off)
    else:
        icon.addPixmap(QtGui.QPixmap(f":/icons/Icon_Library/{icon_name}.png"), QtGui.QIcon.Normal,
                       QtGui.QIcon.Off)
    return icon


class QAction(QAction):
    """
    QAction subclass to mimic signals as pushbuttons. Done to be sure of backcompatibility when I moved from
    pushbuttons to QAction
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def click(self):
        pymodaq.utils.messenger.deprecation_msg("click for PyMoDAQ's QAction is deprecated, use *trigger*",
                                                stacklevel=3)
        self.trigger()

    @property
    def clicked(self):
        pymodaq.utils.messenger.deprecation_msg("clicked for PyMoDAQ's QAction is deprecated, use *trigger*",
                                                stacklevel=3)
        return self.triggered

    def connect_to(self, slot):
        self.triggered.connect(slot)

    def set_icon(self, icon_name: str):
        self.setIcon(create_icon(icon_name))


def addaction(name: str = '', icon_name: str = '', tip='', checkable=False, checked=False,
              slot: Callable = None, toolbar: QtWidgets.QToolBar = None,
              menu: QtWidgets.QMenu = None, visible=True, shortcut=None):
    """Create a new action and add it eventually to a toolbar and a menu

    Parameters
    ----------
    name: str
        Displayed name if should be displayed (for instance in menus)
    icon_name: str
        png file name to produce the icon
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
    """
    if icon_name != '':
        action = QAction(create_icon(icon_name), name, None)
    else:
        action = QAction(name)

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
    return action


def addwidget(klass: Union[str, QtWidgets.QWidget], *args, tip='', toolbar: QtWidgets.QToolBar = None, visible=True,
              signal_str=None, slot: Callable=None, setters = {}, **kwargs):
    """Create and eventually add a widget to a toolbar

    Parameters
    ----------
    klass: str or QWidget
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
    kwargs: dict
        variable named arguments used as is in the widget constructor
    setters: dict
        method/value pair of the widget (for instance setMaximumWidth)
    Returns
    -------
    QtWidgets.QWidget
    """
    if isinstance(klass, str):
        if hasattr(QtWidgets, klass):
            widget: QtWidgets.QWidget = getattr(QtWidgets, klass)(*args)
        else:
            return None
    else:
        try:
            widget = klass(*args, **kwargs)
        except:
            return None
    widget.setVisible(visible)
    widget.setToolTip(tip)
    if toolbar is not None:
        toolbar.addWidget(widget)
    if isinstance(signal_str, str) and slot is not None:
        if hasattr(widget, signal_str):
            getattr(widget, signal_str).connect(slot)

    for setter in setters:
        if hasattr(widget, setter):
            getattr(widget, setter)(setters[setter])

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
    def __init__(self, toolbar=None, menu=None):
        self._actions = dict([])
        self._toolbar = toolbar
        self._menu = menu

        #self.setup_actions()

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

    def add_action(self, short_name: str = '', name: str = '', icon_name: str = '', tip='', checkable=False,
                   checked=False, toolbar=None, menu=None,
                   visible=True, shortcut=None, auto_toolbar=True, auto_menu=True):
        """Create a new action and add it to toolbar and menu

        Parameters
        ----------
        short_name: str
            the name as referenced in the dict self.actions
        name: str
            Displayed name if should be displayed in
        icon_name: str
            png file name to produce the icon
        tip: str
            a tooltip to be displayed when hovering above the action
        checkable: bool
            set the checkable state of the action
        checked: bool
            set the current state of the action            
        toolbar: QToolBar
            a toolbar where action should be added. Actions can also be added later see *affect_to*
        menu: QMenu
            a menu where action should be added. Actions can also be added later see *affect_to*
        visible: bool
            display or not the action in the toolbar/menu

        See Also
        --------
        affect_to, pymodaq.resources.QtDesigner_Ressources.Icon_Library,
        pymodaq.utils.managers.action_manager.add_action
        """
        if auto_toolbar:
            if toolbar is None:
                toolbar = self._toolbar
        if auto_menu:
            if menu is None:
                menu = self._menu
        self._actions[short_name] = addaction(name, icon_name, tip, checkable=checkable, checked=checked, toolbar=toolbar, menu=menu,
                                              visible=visible, shortcut=shortcut)

    def add_widget(self, short_name, klass: Union[str, QtWidgets.QWidget], *args, tip='',
                   toolbar: QtWidgets.QToolBar = None, visible=True, signal_str=None, slot: Callable=None, **kwargs):
        """Create and add a widget to a toolbar

        Parameters
        ----------
        short_name: str
            the name as referenced in the dict self.actions
        klass: str or QWidget
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
        kwargs: dict
            variable named arguments passed as is to the widget constructor
        Returns
        -------
        QtWidgets.QWidget
        """
        if toolbar is None:
            toolbar = self._toolbar
        widget = addwidget(klass, *args, tip=tip, toolbar=toolbar, visible=visible, signal_str=signal_str,
                           slot=slot, **kwargs)
        if widget is not None:
            self._actions[short_name] = widget
        else:
            warnings.warn(UserWarning(f'Impossible to add the widget {short_name} and type {klass} to the toolbar'))

    def set_toolbar(self, toolbar):
        """affect a toolbar to self

        Parameters
        ----------
        toolbar:
            QtWidgets.QToolBar
        """
        self._toolbar = toolbar

    def set_menu(self, menu):
        """affect a menu to self

        Parameters
        ----------
        menu:
            QtWidgets.QMenu
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
    def actions(self) -> List[QAction]:
        return list(self._actions.values())

    def get_action(self, name) -> QAction:
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

    @property
    def toolbar(self):
        """Get the default toolbar"""
        return self._toolbar

    @property
    def menu(self):
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

    def connect_action(self, name, slot, connect=True, signal_name=''):
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

    @dispatch(list)
    def is_action_visible(self, actions_name: list):
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

    @dispatch(list)
    def is_action_checked(self, actions_name: list):
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

    @dispatch(list, bool)
    def set_action_visible(self, actions_name: list, visible=True):
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

    @dispatch(list, bool)
    def set_action_checked(self, actions_name: list, checked=True):
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

    @dispatch(list, bool)
    def set_action_enabled(self, actions_name: list, enabled=True):
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

    @dispatch(list)
    def is_action_checked(self, actions_name: list):
        """Get the EnabledState of a given action or a list of actions"""
        is_enabled = False
        for action_name in actions_name:
            is_enabled = is_enabled and self.is_action_enabled(action_name)
        return is_enabled
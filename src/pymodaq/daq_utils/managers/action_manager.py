import pymodaq.daq_utils.messenger
from multipledispatch import dispatch
from typing import Union

from qtpy import QtGui, QtWidgets, QtCore
from qtpy.QtWidgets import QAction

from pymodaq.resources.QtDesigner_Ressources import QtDesigner_ressources_rc
from pathlib import Path


class QAction(QAction):
    """
    QAction subclass to mimic signals as pushbuttons. Done to be sure of backcompatibility when I moved from
    pushbuttons to QAction
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def click(self):
        pymodaq.daq_utils.messenger.deprecation_msg("click for PyMoDAQ's QAction is deprecated, use *trigger*",
                                                    stacklevel=3)
        self.trigger()

    @property
    def clicked(self):
        pymodaq.daq_utils.messenger.deprecation_msg("clicked for PyMoDAQ's QAction is deprecated, use *trigger*",
                                                    stacklevel=3)
        return self.triggered

    def connect_to(self, slot):
        self.triggered.connect(slot)


def addaction(name='', icon_name='', tip='', checkable=False, slot=None, toolbar=None, menu=None):
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
    slot: callable
        Method or function that will be called when the action is triggered
    toolbar: QToolBar
        a toolbar where action should be added.
    menu: QMenu
        a menu where action should be added.
    """
    if icon_name != '':
        icon = QtGui.QIcon()
        if Path(icon_name).is_file():
            icon.addPixmap(QtGui.QPixmap(icon_name), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
        else:
            icon.addPixmap(QtGui.QPixmap(f":/icons/Icon_Library/{icon_name}.png"), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
        action = QAction(icon, name, None)
    else:
        action = QAction(name)

    if slot is not None:
        action.connect_to(slot)
    action.setCheckable(checkable)
    action.setToolTip(tip)
    if toolbar is not None:
        toolbar.addAction(action)
    if menu is not None:
        menu.addAction(action)
    return action


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
        """Method where to create actions

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

    def add_action(self, short_name='', name='', icon_name='', tip='', checkable=False, toolbar=None, menu=None):
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
        toolbar: QToolBar
            a toolbar where action should be added. Actions can also be added later see *affect_to*
        menu: QMenu
            a menu where action should be added. Actions can also be added later see *affect_to*

        See Also
        --------
        affect_to, pymodaq.resources.QtDesigner_Ressources.Icon_Library,
        pymodaq.daq_utils.managers.action_manager.add_action
        """
        if toolbar is None:
            toolbar = self._toolbar
        if menu is None:
            menu = self._menu
        self._actions[short_name] = addaction(name, icon_name, tip, checkable=checkable, toolbar=toolbar, menu=menu)

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

    def get_action(self, name):
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

    def has_action(self, action_name):
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

    def connect_action(self, name, slot, connect=True):
        """Connect (or disconnect) the action referenced by name to the given slot

        Parameters
        ----------
        name: str
            key of the action as referenced in the self._actions dict
        slot: method
            a method/function
        connect: bool
            if True connect the trigger signal of the action to the defined slot else disconnect it
        """
        if name in self._actions:
            if connect:
                self._actions[name].triggered.connect(slot)
            else:
                try:
                    self._actions[name].triggered.disconnect()
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

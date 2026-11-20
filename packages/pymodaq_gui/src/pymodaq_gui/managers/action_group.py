"""Groups of actions under a single toolbar button (or a submenu of another group)

Built by :meth:`pymodaq_gui.managers.action_manager.ActionManager.add_action_group`, which also re-exports these
names: ``from pymodaq_gui.managers.action_manager import ActionGroup, Indicator`` keeps working.
"""
from __future__ import annotations

from collections import OrderedDict
from enum import Enum
from typing import TYPE_CHECKING, Optional, OrderedDict as OrderedDictType

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtWidgets import QAction as QtQAction

from pymodaq_gui.utils.menu_utils import StickyMenu
from pymodaq_gui.utils.status_palette import Status, StatusPalette
from pymodaq_gui.utils.widgets.push import ToolButtonIcon

if TYPE_CHECKING:  # action_manager imports this module
    from pymodaq_gui.managers.action_manager import QAction


class Indicator(Enum):
    """What the icon of a group of actions tells about its entries

    Groups hide their entries in a dropdown: the colour of the group icon tells when they are not in their default
    state, see :meth:`ActionManager.set_action_group_indicator`. The colours are the status ones
    (:class:`~pymodaq_gui.utils.status_palette.StatusPalette`), red being kept for real faults.
    """
    DEFAULT = None  # neutral: the entries are in their default state
    # the group is actively changing the data (e.g. a transform is applied): green
    ACTIVE = StatusPalette.role(Status.IDLE)
    # part of what the group controls is hidden (e.g. some channels): yellow
    PARTIAL = StatusPalette.role(Status.WARNING)
    # nothing the group controls is shown (e.g. no visible channel): orange
    EMPTY = StatusPalette.role(Status.ERROR)


class _FaceMirror(QtCore.QObject):
    """Keeps the submenu entry of a nested group in line with the face of the group

    A child of the menu. Under PySide6 the entry of the menu may be deleted before the face (e.g. with the
    toolbar): the mirror then disconnects itself.
    """

    def __init__(self, face: QtGui.QAction, menu: QtWidgets.QMenu) -> None:
        super().__init__(menu)
        self._face = face
        self._menu = menu
        face.changed.connect(self.mirror)
        self.mirror()

    @QtCore.Slot()
    def mirror(self) -> None:
        try:
            entry = self._menu.menuAction()
            entry.setIcon(self._face.icon())
            entry.setText(self._face.text())
            entry.setToolTip(self._face.toolTip())
            entry.setEnabled(self._face.isEnabled())
            entry.setVisible(self._face.isVisible())
        except RuntimeError:  # the menu or its entry was deleted before the face
            try:
                self._face.changed.disconnect(self.mirror)
            except (RuntimeError, TypeError):
                pass


class ActionGroup(QtCore.QObject):
    """The state of a group of actions: its entries, their checked state, its indicator

    A group is displayed either by a toolbar button (:class:`ActionGroupButton`) or, when nested in another
    group, by a submenu of that group. Its *face* is the action whose icon, text and tooltip represent the
    group: its primary action when it has one, else an action that is not registered.

    Created by :meth:`ActionManager.add_action_group`, get it back with :meth:`ActionManager.get_action_group`.

    Signals
    -------
    entry_toggled: (key: str, checked: bool)
        an entry was checked/unchecked, by the user or by code
    entries_changed:
        entries were added/removed, or one of them changed (visibility, enabled state...)
    """
    entry_toggled = QtCore.Signal(str, bool)
    entries_changed = QtCore.Signal()

    def __init__(self, name: str, face: QAction, has_primary: bool = True, exclusive: bool = False,
                 nested: bool = False, parent: Optional[QtCore.QObject] = None,
                 menu_parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.name = name
        self.face = face
        self.has_primary = has_primary
        self.exclusive = exclusive
        self._entries: OrderedDictType[str, QAction] = OrderedDict()
        self._entry_names: dict[str, str] = {}  # key -> short name the entry is registered with
        self._remembered: dict[str, bool] = {}  # key -> checked state, kept when entries are replaced
        self._subgroups: list['ActionGroup'] = []
        self._action_group = QtGui.QActionGroup(self) if exclusive else None
        if self._action_group is not None:
            self._action_group.setExclusive(True)
        self._indicator = Indicator.DEFAULT
        # what the face shows in the default state, taken again each time the indicator leaves it (the owner
        # may have changed the tooltip meanwhile)
        self._base_tip = face.toolTip()
        self._base_colors = face._icon_spec_colors()

        # checkable entries do not close it. Created with its Qt parent: a menu first owned by Python and
        # reparented later can be deleted twice under PySide6 once its actions are deleted (delete_actions)
        self.menu = StickyMenu(menu_parent)
        if nested:
            _FaceMirror(face, self.menu)
            if has_primary:
                self.menu.addAction(face)
                self.menu.addSeparator()

    # entries
    def keys(self) -> list[str]:
        return list(self._entries.keys())

    def get_entry(self, key: str) -> QAction:
        return self._entries[key]

    def entry_name(self, key: str) -> str:
        """The short name the entry of this key is registered with in the ActionManager"""
        return self._entry_names[key]

    def remembered_checked(self, key: str, default: bool) -> bool:
        return self._remembered.get(key, default)

    def has_key(self, key: str) -> bool:
        return key in self._entries

    def is_checked(self, key: str) -> bool:
        return self._entries[key].isChecked()

    def set_checked(self, key: str, checked: bool = True) -> None:
        self._entries[key].setChecked(checked)

    def add_entry(self, key: str, action: QAction, short_name: str, before_subgroups: bool = False,
                  notify: bool = True) -> None:
        """Add an entry to the menu, at its end or, with *before_subgroups*, before the nested groups

        With ``notify=False`` the caller emits :attr:`entries_changed` once it has added all its entries.
        """
        if self.has_key(key):
            raise KeyError(f'The group {self.name} already has an entry with key {key}')
        self._entries[key] = action
        self._entry_names[key] = short_name
        if action.isCheckable():
            self._remembered[key] = action.isChecked()
        if self._action_group is not None:
            self._action_group.addAction(action)
        if before_subgroups and self._subgroups:
            self.menu.insertAction(self._subgroups[0].menu.menuAction(), action)
        else:
            self.menu.addAction(action)
        # slots of this QObject (no lambda): Qt drops the connections if the group is deleted first
        action.toggled.connect(self._on_entry_toggled)
        action.changed.connect(self.entries_changed)
        # e.g. its icon rebuilt after a theme change: the face may show it
        action.changed.connect(self._show_checked_entry_on_face)
        self._show_checked_entry_on_face()
        if notify:
            self.entries_changed.emit()

    def add_subgroup(self, group: 'ActionGroup', notify: bool = True) -> None:
        self._subgroups.append(group)
        self.menu.addMenu(group.menu)
        group.entries_changed.connect(self.entries_changed)
        if notify:
            self.entries_changed.emit()

    def clear_entries(self, notify: bool = True) -> list[str]:
        """Remove all the (non nested) entries, return the short names they were registered with

        Nested groups stay. With ``notify=False`` the caller emits :attr:`entries_changed`.
        """
        names = []
        for key, action in self._entries.items():
            self.menu.removeAction(action)
            if self._action_group is not None:
                self._action_group.removeAction(action)
            try:
                action.toggled.disconnect()
                action.changed.disconnect()
            except (RuntimeError, TypeError):
                pass
            action.deleteLater()
            names.append(self._entry_names[key])
        self._entries.clear()
        self._entry_names.clear()
        if notify:
            self.entries_changed.emit()
        return names

    def has_entries(self) -> bool:
        return len(self._entries) > 0 or len(self._subgroups) > 0

    def is_available(self) -> bool:
        """True if at least one entry (or nested group) can be used: visible and enabled"""
        return (any(action.isVisible() and action.isEnabled() for action in self._entries.values()) or
                any(group.is_available() for group in self._subgroups))

    @QtCore.Slot(bool)
    def _on_entry_toggled(self, checked: bool) -> None:
        sender = self.sender()
        key = next((key for key, action in self._entries.items() if action is sender or action == sender), None)
        if key is None:
            return
        self._remembered[key] = checked
        if checked:
            self._show_checked_entry_on_face()
        self.entry_toggled.emit(key, checked)

    @QtCore.Slot()
    def _show_checked_entry_on_face(self) -> None:
        """An exclusive group without primary shows the icon of its checked entry"""
        if self.exclusive and not self.has_primary:
            for action in self._entries.values():
                if action.isChecked():
                    self.face.setIcon(action.icon())

    # indicator
    @property
    def indicator(self) -> Indicator:
        return self._indicator

    def set_indicator(self, indicator: Indicator, tip: str = '') -> None:
        """Colour the face icon (and append *tip* to its tooltip) to tell about the state of the entries

        The tooltip and colours of the default state are the ones of the face when it leaves that state, so a
        tooltip set by the owner meanwhile is kept. A face whose icon cannot be rebuilt (no icon, or an icon
        instance) only gets the tooltip; so does an exclusive group without primary, whose face shows the icon of
        its checked entry.
        """
        if self._indicator is Indicator.DEFAULT:
            self._base_tip = self.face.toolTip()
            self._base_colors = self.face._icon_spec_colors()
        self._indicator = indicator
        if indicator is Indicator.DEFAULT:
            self.face._set_icon_spec_colors(*self._base_colors)
        else:
            self.face.set_icon_colors(indicator.value, indicator.value)
        self.face.setToolTip(f'{self._base_tip}\n{tip}' if (tip and self._base_tip) else (tip or self._base_tip))
        # rebuilding the face icon replaced the icon of the checked entry
        self._show_checked_entry_on_face()


class ActionGroupButton(ToolButtonIcon):
    """The toolbar button displaying a top level :class:`ActionGroup`

    With a primary action, clicking the button triggers it and a dropdown arrow gives the entries (while at least one
    of them is visible and enabled). Without primary, clicking the button opens the entries.
    """

    def __init__(self, group: ActionGroup, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent=parent, follow_toolbar_style=True)
        self.action_group = group
        self._toolbar_action: Optional[QtQAction] = None
        self.setDefaultAction(group.face)
        group.entries_changed.connect(self._refresh_menu)
        # a QToolButton follows the enabled state of its default action, not its visibility
        group.face.visibleChanged.connect(self._follow_face_visibility)
        self._refresh_menu()

    def add_to_toolbar(self, toolbar: QtWidgets.QToolBar) -> None:
        """Add the button to *toolbar*, shown while the face of the group is visible"""
        self._toolbar_action = toolbar.addWidget(self)
        self._follow_face_visibility()

    @QtCore.Slot()
    def _follow_face_visibility(self) -> None:
        try:
            visible = self.action_group.face.isVisible()
            if self._toolbar_action is not None:
                self._toolbar_action.setVisible(visible)
            else:
                self.setVisible(visible)
        except RuntimeError:  # the toolbar was deleted before the face
            pass

    @QtCore.Slot()
    def _refresh_menu(self) -> None:
        menu = self.action_group.menu if self.action_group.has_entries() else None
        if self.menu() is not menu:
            self.setMenu(menu)
        if not self.action_group.has_primary:
            self.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        elif self.action_group.has_entries() and self.action_group.is_available():
            self.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        else:
            self.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.DelayedPopup)

"""Shared utility for building nested QMenu structures.

Uses ``QMenu(title, parent)`` to create submenus so that Qt takes C++
ownership and PySide6 does not garbage-collect them prematurely.
"""
from typing import Callable, Optional

from qtpy import QtWidgets, QtGui


class StickyMenu(QtWidgets.QMenu):
    """A :class:`QMenu` that stays open after an action is triggered.

    By default the menu remains open only when a **checkable** action is
    clicked (the typical use-case for toolbar-visibility toggles).  Pass
    ``sticky_all=True`` to keep the menu open after *any* action click,
    which is useful for multi-selection menus.  For fine-grained control
    supply a *sticky_predicate*: a callable that receives the triggered
    ``QAction`` and returns ``True`` when the menu should stay open.

    Parameters
    ----------
    *args :
        Forwarded to :class:`QMenu` (title, parent, …).
    sticky_all : bool
        When ``True`` the menu never closes on a click regardless of whether
        the action is checkable.  Ignored if *sticky_predicate* is given.
    sticky_predicate : callable(QAction) -> bool, optional
        Custom predicate that decides per-action whether the menu stays open.
        When provided, *sticky_all* is ignored.
    **kwargs :
        Forwarded to :class:`QMenu`.
    """

    def __init__(self, *args, sticky_all: bool = False,
                 sticky_predicate: Optional[Callable[[QtWidgets.QAction], bool]] = None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        if sticky_predicate is not None:
            self._is_sticky = sticky_predicate
        elif sticky_all:
            self._is_sticky = lambda action: True
        else:
            self._is_sticky = lambda action: action.isCheckable()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        action = self.activeAction()
        if action and self._is_sticky(action):
            action.trigger()
        else:
            super().mouseReleaseEvent(event)


def build_menu_from_iterable(
    menu: QtWidgets.QMenu,
    items,
    leaf_callback: Callable,
    path: tuple = (),
) -> None:
    """Populate *menu* recursively from a nested dict / list / tuple.

    Parameters
    ----------
    menu : QMenu
        The menu to populate.
    items : dict | list | tuple | str
        The menu content:

        * ``dict``  — keys become submenu titles (when the corresponding
          value is a non-empty container) or leaf action labels (otherwise).
        * ``list`` / ``tuple`` — each element is either a ``str`` (leaf
          action) or a single-key ``dict`` (submenu or leaf).
        * ``str`` — shorthand for ``[str]``.

    leaf_callback : callable(name: str, path: tuple[str, ...]) -> None
        Invoked when a leaf action is triggered.  *name* is the action
        label; *path* is the full tuple of labels from the root to that
        action.
    path : tuple[str, ...]
        Accumulated prefix — callers should leave this at its default.
    """
    if isinstance(items, str):
        items = [items]

    if isinstance(items, dict):
        for key, value in items.items():
            _handle_item(menu, key, value, path, leaf_callback)
    elif isinstance(items, (list, tuple)):
        for item in items:
            if isinstance(item, dict):
                for key, value in item.items():
                    _handle_item(menu, key, value, path, leaf_callback)
            elif isinstance(item, str):
                _add_leaf(menu, item, path + (item,), leaf_callback)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _handle_item(menu, key, value, path, leaf_callback):
    new_path = path + (key,)
    if isinstance(value, (dict, list, tuple)) and value:
        # Create submenu with QMenu(title, parent) so Qt owns the C++ object
        submenu = QtWidgets.QMenu(key, menu)
        menu.addAction(submenu.menuAction())
        build_menu_from_iterable(submenu, value, leaf_callback, new_path)
    else:
        _add_leaf(menu, key, new_path, leaf_callback)


def _add_leaf(menu, name, path, leaf_callback):
    action = menu.addAction(name)
    action.triggered.connect(
        lambda checked=False, n=name, p=path: leaf_callback(n, p)
    )

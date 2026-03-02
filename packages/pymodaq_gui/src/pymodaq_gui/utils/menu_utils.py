"""Shared utility for building nested QMenu structures.

Uses ``QMenu(title, parent)`` to create submenus so that Qt takes C++
ownership and PySide6 does not garbage-collect them prematurely.
"""
from typing import Callable

from qtpy import QtWidgets


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

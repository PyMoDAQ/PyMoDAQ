from typing import Callable, Optional

from qtpy import QtWidgets, QtCore


class ContextMenuListWidget(QtWidgets.QListWidget):
    """QListWidget base class with a fully composable right-click context menu.

    Actions are registered via :meth:`addContextMenuAction` (single entry) or
    :meth:`addContextMenuActions` (bulk dict). Each callback receives two
    arguments:

    * **clicked** (``str | None``) — text of the item under the cursor, or
      ``None`` when right-clicking on empty space.
    * **selected** (``list[str]``) — texts of all currently selected items,
      as returned by :meth:`_get_selected_names`.

    Pass ``label=None`` (or a ``None`` key in the dict) to insert a separator.

    Examples
    --------
    >>> w = ContextMenuListWidget()
    >>> # dict-based registration (recommended)
    >>> w.addContextMenuActions({
    ...     'Probe': lambda clicked, sel: print(clicked, sel),
    ...     None: None,           # separator
    ...     'Viewers': {          # submenu
    ...         'Show': show_fn,
    ...         'Hide': hide_fn,
    ...     },
    ...     'Data': {'Export': {'Export CSV': export_fn}},
    ... })
    >>> # single-action registration
    >>> w.addContextMenuAction('Probe', lambda clicked, sel: print(clicked, sel))
    """

    def __init__(self):
        super().__init__()
        # Each entry: (label, callback, path)
        self._context_actions: list[
            tuple[Optional[str], Optional[Callable], tuple[str, ...]]
        ] = []
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def addContextMenuActions(self, spec: dict, *, _path: tuple[str, ...] = ()):
        """Register multiple actions from a nested dict.

        Keys are action labels (``str``) or ``None`` for a separator.
        Values are either:

        * **callable** — leaf action, ``callback(clicked, selected)``
        * **dict** — submenu; the key becomes the submenu title and the
          value is recursed into.
        * ``None`` — used together with a ``None`` key to insert a separator.

        Parameters
        ----------
        spec : dict
            Menu specification (see examples in the class docstring).
        """
        for label, value in spec.items():
            if label is None:
                self.addContextMenuAction(None, path=_path)
            elif isinstance(value, dict):
                self.addContextMenuActions(value, _path=_path + (label,))
            else:
                self.addContextMenuAction(label, value, path=_path)

    def clearContextMenuActions(self):
        """Remove all registered context menu actions."""
        self._context_actions.clear()

    def addContextMenuAction(
        self,
        label: Optional[str],
        callback: Optional[Callable] = None,
        *,
        path: tuple[str, ...] = (),
    ):
        """Register a single action (or separator) in the right-click menu.

        Parameters
        ----------
        label : str or None
            Menu entry text. ``None`` inserts a separator.
        callback : callable, optional
            ``callback(clicked: str | None, selected: list[str]) -> None``
            Ignored when *label* is ``None``.
        path : tuple of str, optional
            Submenu hierarchy. ``path=('View', 'Data')`` places the action
            inside *View → Data*. Defaults to top-level (empty tuple).
        """
        self._context_actions.append((label, callback, path))

    # ------------------------------------------------------------------
    # Overridable hook
    # ------------------------------------------------------------------

    def _get_selected_names(self) -> list[str]:
        """Return the texts of all currently *selected* items.

        Subclasses that use a different selection model (e.g. checkboxes)
        should override this method.
        """
        return [item.text() for item in self.selectedItems()]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_context_menu(self, pos: QtCore.QPoint) -> Optional[QtWidgets.QMenu]:
        """Build and return the context menu for *pos* without showing it.

        Returns ``None`` when no actions have been registered.
        Separating construction from display makes the logic independently testable.
        """
        if not self._context_actions:
            return None

        list_item = self.itemAt(pos)
        clicked: Optional[str] = list_item.text() if list_item is not None else None
        selected: list[str] = self._get_selected_names()

        root_menu = QtWidgets.QMenu(self)
        path_to_menu: dict[tuple[str, ...], QtWidgets.QMenu] = {(): root_menu}

        for label, callback, path in self._context_actions:
            for depth in range(len(path)):
                prefix = path[: depth + 1]
                if prefix not in path_to_menu:
                    parent_menu = path_to_menu[path[:depth]]
                    # Use QMenu(title, parent) so Qt takes C++ ownership and
                    # PySide6 does not garbage-collect the submenu wrapper.
                    submenu = QtWidgets.QMenu(path[depth], parent_menu)
                    parent_menu.addAction(submenu.menuAction())
                    path_to_menu[prefix] = submenu

            target_menu = path_to_menu[path]
            if label is None:
                target_menu.addSeparator()
            else:
                target_menu.addAction(
                    label,
                    lambda cb=callback, cl=clicked, sel=selected: cb(cl, sel),
                )

        # Keep a reference on self so the root menu (and its Qt-owned children)
        # stays alive until the next right-click replaces it.
        self._active_context_menu = root_menu
        return root_menu

    def _show_context_menu(self, pos: QtCore.QPoint):
        menu = self._build_context_menu(pos)
        if menu is not None:
            menu.exec(self.mapToGlobal(pos))


def main(init_qt=True):
    import sys

    if init_qt:
        app = QtWidgets.QApplication(sys.argv)

    w = ContextMenuListWidget()
    w.addItems(['detector A', 'detector B', 'detector C'])
    w.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def _log(action, clicked, selected):
        print(f'[{action}] clicked={clicked!r}  selected={selected}')

    w.addContextMenuActions({
        'Probe': lambda cl, sel: _log('Probe', cl, sel),
        None: None,
        'Viewers': {
            'Show':     lambda cl, sel: _log('Show', cl, sel),
            'Hide':     lambda cl, sel: _log('Hide', cl, sel),
            None: None,
            'Settings': lambda cl, sel: _log('Settings', cl, sel),
        },
        'Data': {
            'Export': {
                'Export CSV': lambda cl, sel: _log('Export CSV', cl, sel),
            },
        },
    })

    w.setWindowTitle('ContextMenuListWidget demo')
    w.show()

    if init_qt:
        sys.exit(app.exec())


if __name__ == '__main__':
    main()

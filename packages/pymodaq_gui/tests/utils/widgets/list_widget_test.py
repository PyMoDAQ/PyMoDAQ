import pytest
from qtpy import QtCore, QtWidgets

from pymodaq_gui.utils.widgets.list_widget import ContextMenuListWidget


@pytest.fixture
def widget(qtbot):
    w = ContextMenuListWidget()
    w.addItems(['alpha', 'beta', 'gamma'])
    qtbot.addWidget(w)
    return w


class TestAddContextMenuAction:
    def test_flat_action_stored(self, widget):
        widget.addContextMenuAction('Do something', lambda cl, sel: None)
        assert len(widget._context_actions) == 1
        label, _, path = widget._context_actions[0]
        assert label == 'Do something'
        assert path == ()

    def test_separator_stored(self, widget):
        widget.addContextMenuAction(None)
        label, cb, path = widget._context_actions[0]
        assert label is None
        assert cb is None
        assert path == ()

    def test_nested_action_stored(self, widget):
        widget.addContextMenuAction('Show', lambda cl, sel: None, path=('Viewers',))
        _, _, path = widget._context_actions[0]
        assert path == ('Viewers',)

    def test_multiple_actions_accumulate(self, widget):
        widget.addContextMenuAction('A', lambda cl, sel: None)
        widget.addContextMenuAction('B', lambda cl, sel: None)
        assert len(widget._context_actions) == 2


class TestGetSelectedNames:
    def test_returns_highlighted_selection(self, widget):
        widget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        widget.item(0).setSelected(True)
        widget.item(2).setSelected(True)
        assert widget._get_selected_names() == ['alpha', 'gamma']

    def test_empty_selection(self, widget):
        assert widget._get_selected_names() == []


class TestBuildContextMenu:
    def test_returns_none_when_no_actions(self, widget):
        assert widget._build_context_menu(QtCore.QPoint(0, 0)) is None

    def test_returns_menu_when_actions_registered(self, widget):
        widget.addContextMenuAction('Go', lambda cl, sel: None)
        menu = widget._build_context_menu(QtCore.QPoint(0, 0))
        assert menu is not None
        assert isinstance(menu, QtWidgets.QMenu)

    def test_flat_actions_appear_at_root(self, widget):
        widget.addContextMenuAction('A', lambda cl, sel: None)
        widget.addContextMenuAction('B', lambda cl, sel: None)
        menu = widget._build_context_menu(QtCore.QPoint(0, 0))
        labels = [a.text() for a in menu.actions() if not a.isSeparator()]
        assert labels == ['A', 'B']

    def test_separator_in_menu(self, widget):
        widget.addContextMenuAction('A', lambda cl, sel: None)
        widget.addContextMenuAction(None)
        widget.addContextMenuAction('B', lambda cl, sel: None)
        menu = widget._build_context_menu(QtCore.QPoint(0, 0))
        assert any(a.isSeparator() for a in menu.actions())

    def test_nested_submenu_created(self, widget):
        widget.addContextMenuAction('Show', lambda cl, sel: None, path=('Viewers',))
        widget.addContextMenuAction('Hide', lambda cl, sel: None, path=('Viewers',))
        menu = widget._build_context_menu(QtCore.QPoint(0, 0))
        submenus = [a.menu() for a in menu.actions() if a.menu() is not None]
        assert len(submenus) == 1
        assert submenus[0].title() == 'Viewers'
        assert len(submenus[0].actions()) == 2

    def test_deeply_nested_submenu(self, widget):
        widget.addContextMenuAction('Export CSV', lambda cl, sel: None,
                                    path=('Data', 'Export'))
        root = widget._build_context_menu(QtCore.QPoint(0, 0))
        data_menu = next(a.menu() for a in root.actions()
                         if a.menu() and a.menu().title() == 'Data')
        export_menu = next(a.menu() for a in data_menu.actions()
                           if a.menu() and a.menu().title() == 'Export')
        assert export_menu.actions()[0].text() == 'Export CSV'

    def test_shared_submenu_prefix(self, widget):
        """Two actions with the same path prefix must share the same QMenu instance."""
        widget.addContextMenuAction('A', lambda cl, sel: None, path=('Sub',))
        widget.addContextMenuAction('B', lambda cl, sel: None, path=('Sub',))
        menu = widget._build_context_menu(QtCore.QPoint(0, 0))
        submenus = [a.menu() for a in menu.actions() if a.menu() is not None]
        assert len(submenus) == 1          # only one 'Sub' submenu
        assert len(submenus[0].actions()) == 2

    def test_callback_receives_clicked_item(self, widget):
        received = []
        widget.addContextMenuAction('Go', lambda cl, sel: received.append((cl, sel)))
        pos = widget.visualItemRect(widget.item(0)).center()
        menu = widget._build_context_menu(pos)
        menu.actions()[0].trigger()
        assert received[0][0] == 'alpha'

    def test_callback_receives_none_on_empty_space(self, widget):
        received = []
        widget.addContextMenuAction('Go', lambda cl, sel: received.append((cl, sel)))
        menu = widget._build_context_menu(QtCore.QPoint(0, 10_000))
        menu.actions()[0].trigger()
        assert received[0][0] is None

    def test_callback_receives_selected_items(self, widget):
        received = []
        widget.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        widget.item(1).setSelected(True)   # 'beta'
        widget.addContextMenuAction('Go', lambda cl, sel: received.append((cl, sel)))
        pos = widget.visualItemRect(widget.item(0)).center()
        menu = widget._build_context_menu(pos)
        menu.actions()[0].trigger()
        assert 'beta' in received[0][1]

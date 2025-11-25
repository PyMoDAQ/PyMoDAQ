# -*- coding: utf-8 -*-
"""
Created the 08/11/2024

@author: Constant Schouder
"""

from packaging.version import Version

import pytest
from qtpy import QtWidgets, QtGui, QtCore
from pymodaq_gui.managers.action_manager import ActionManager


version_qt = QtCore.qVersion()


@pytest.fixture
def ini_qt_widget(init_qt):
    qtbot = init_qt
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    widget.show()
    yield qtbot, widget
    widget.close()


def is_icon_null(
    action_manager,
    action_name,
):
    action = action_manager.get_action(action_name)
    return action.icon().isNull()


def test_icon(qtbot):
    action_manager = ActionManager(toolbar=QtWidgets.QToolBar(), menu=QtWidgets.QMenu())

    action_manager.add_action(short_name="no_icon", name="my_no_icon", icon_name="")

    assert is_icon_null(action_manager, "no_icon")

    action_manager.add_action(
        short_name="icon_from_pymodaq", name="an_icon_from_pymodaq", icon_name="NewFile"
    )
    assert not is_icon_null(action_manager, "icon_from_pymodaq")

    if Version(version_qt) > Version("6.7"):
        action_manager.add_action(
            short_name="icon_from_Qt", name="an_icon_from_Qt", icon_name="WindowClose"
        )
        assert not is_icon_null(action_manager, "icon_from_Qt")

        icon = QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.WindowClose)
        action_manager.add_action(
            short_name="icon", name="an_icon_from_Qt", icon_name=icon
        )
        assert not is_icon_null(action_manager, "icon")



def test_action_properties(qtbot):
    action_manager = ActionManager(toolbar=QtWidgets.QToolBar(), menu=QtWidgets.QMenu())

    action_manager.add_action(short_name="no_icon", name="my_no_icon", icon_name="")
    action_manager.add_action(
        short_name="icon_from_pymodaq", name="an_icon_from_pymodaq", icon_name="NewFile"
    )

    assert action_manager.get_action('no_icon') == action_manager._actions['no_icon']

    assert 'no_icon' in action_manager.actions_names
    assert 'icon_from_pymodaq' in action_manager.actions_names

    assert action_manager.get_action('no_icon') in action_manager.actions
    assert isinstance(action_manager.get_action('icon_from_pymodaq'), QtWidgets.QAction)


def test_menu_creation(qtbot):
    """Test creating menus"""
    menu = QtWidgets.QMenu()
    action_manager = ActionManager(toolbar=QtWidgets.QToolBar(), menu=menu)

    # Create a simple menu
    file_menu = action_manager.add_menu('file_menu', 'File')

    assert action_manager.has_menu('file_menu')
    assert action_manager.get_menu('file_menu') == file_menu
    assert 'file_menu' in action_manager.menus_names
    assert file_menu in action_manager.menus
    assert isinstance(file_menu, QtWidgets.QMenu)
    assert file_menu.title() == 'File'


def test_menu_with_icon(qtbot):
    """Test creating menus with icons"""
    menu = QtWidgets.QMenu()
    action_manager = ActionManager(toolbar=QtWidgets.QToolBar(), menu=menu)

    # Create menu with icon
    edit_menu = action_manager.add_menu('edit_menu', 'Edit', icon_name='NewFile')

    assert not edit_menu.icon().isNull()


def test_nested_menus(qtbot):
    """Test creating nested menus (menu within menu)"""
    menu = QtWidgets.QMenu()
    action_manager = ActionManager(toolbar=QtWidgets.QToolBar(), menu=menu)

    # Create parent menu
    parent_menu = action_manager.add_menu('parent', 'Parent Menu')

    # Create child menu within parent
    child_menu = action_manager.add_menu('child', 'Child Menu', menu=parent_menu)

    assert action_manager.has_menu('parent')
    assert action_manager.has_menu('child')

    # Check that child menu is in parent's menu actions
    # Qt wraps menus in QActions, so we check if any action's menu() returns our child
    parent_menus = [action.menu() for action in parent_menu.actions() if action.menu() is not None]
    assert child_menu in parent_menus


def test_add_action_to_menu_by_name(qtbot):
    """Test adding actions to menu using menu name"""
    menu = QtWidgets.QMenu()
    action_manager = ActionManager(toolbar=QtWidgets.QToolBar(), menu=menu)

    # Create menu
    action_manager.add_menu('file_menu', 'File')

    # Add action to menu using name
    action_manager.add_action('open', 'Open', icon_name='Open', menu='file_menu')

    assert action_manager.has_action('open')
    file_menu = action_manager.get_menu('file_menu')
    action = action_manager.get_action('open')
    assert action in file_menu.actions()


def test_add_action_to_menu_by_object(qtbot):
    """Test adding actions to menu using QMenu object"""
    menu = QtWidgets.QMenu()
    action_manager = ActionManager(toolbar=QtWidgets.QToolBar(), menu=menu)

    # Create menu
    edit_menu = action_manager.add_menu('edit_menu', 'Edit')

    # Add action to menu using QMenu object
    action_manager.add_action('copy', 'Copy', menu=edit_menu)

    assert action_manager.has_action('copy')
    action = action_manager.get_action('copy')
    assert action in edit_menu.actions()


def test_multiple_actions_in_menu(qtbot):
    """Test adding multiple actions to the same menu"""
    menu = QtWidgets.QMenu()
    action_manager = ActionManager(toolbar=QtWidgets.QToolBar(), menu=menu)

    # Create menu
    action_manager.add_menu('file_menu', 'File')

    # Add multiple actions
    action_manager.add_action('new', 'New', menu='file_menu')
    action_manager.add_action('open', 'Open', menu='file_menu')
    action_manager.add_action('save', 'Save', menu='file_menu')

    file_menu = action_manager.get_menu('file_menu')
    assert len(file_menu.actions()) == 3


def test_menu_without_auto_menu(qtbot):
    """Test creating menu without automatically adding it to parent menu"""
    menu = QtWidgets.QMenu()
    action_manager = ActionManager(toolbar=QtWidgets.QToolBar(), menu=menu)

    # Create menu without auto-adding
    floating_menu = action_manager.add_menu('floating', 'Floating Menu', auto_menu=False)

    assert action_manager.has_menu('floating')
    # Menu should not be in the main menu's actions
    menu_submenus = [action.menu() for action in menu.actions() if action.menu() is not None]
    assert floating_menu not in menu_submenus


def test_menu_getter_errors(qtbot):
    """Test error handling for menu getters"""
    action_manager = ActionManager(toolbar=QtWidgets.QToolBar(), menu=QtWidgets.QMenu())

    # Test getting non-existent menu
    with pytest.raises(KeyError):
        action_manager.get_menu('nonexistent')

    # Test has_menu for non-existent
    assert not action_manager.has_menu('nonexistent')


def test_add_action_invalid_menu_type(qtbot):
    """Test error handling when passing invalid menu type"""
    menu = QtWidgets.QMenu()
    action_manager = ActionManager(toolbar=QtWidgets.QToolBar(), menu=menu)

    # Try to add action with invalid menu type
    with pytest.raises(TypeError):
        action_manager.add_action('test', 'Test Action', menu=123)


def test_shared_menu(qtbot):
    """Test that the same menu can be added to multiple parent menus"""
    menu = QtWidgets.QMenu()
    action_manager = ActionManager(toolbar=QtWidgets.QToolBar(), menu=menu)

    # Create two parent menus
    file_menu = action_manager.add_menu('file', 'File')
    view_menu = action_manager.add_menu('view', 'View')

    # Create a shared menu (add to file menu first)
    shared_menu = action_manager.add_menu('recent', 'Recent Files', menu=file_menu)

    # Add the same menu to view menu
    view_menu.addMenu(shared_menu)

    # Verify it appears in both menus
    file_submenus = [action.menu() for action in file_menu.actions() if action.menu() is not None]
    view_submenus = [action.menu() for action in view_menu.actions() if action.menu() is not None]

    assert shared_menu in file_submenus
    assert shared_menu in view_submenus

    # Add action to shared menu
    action_manager.add_action('recent_1', 'Project1.py', menu=shared_menu)

    # Verify action appears in the shared menu (accessible from both parent menus)
    assert len(shared_menu.actions()) == 1
    assert action_manager.get_action('recent_1') in shared_menu.actions()


# ========== Toolbar Tests ==========

def test_toolbar_creation(qtbot):
    """Test creating toolbars"""
    action_manager = ActionManager(toolbar=QtWidgets.QToolBar(), menu=QtWidgets.QMenu())

    # Create a toolbar
    file_toolbar = action_manager.add_toolbar('file_toolbar', 'File Toolbar')

    assert action_manager.has_toolbar('file_toolbar')
    assert action_manager.get_toolbar('file_toolbar') == file_toolbar
    assert 'file_toolbar' in action_manager.toolbars_names
    assert file_toolbar in action_manager.toolbars
    assert isinstance(file_toolbar, QtWidgets.QToolBar)
    assert file_toolbar.windowTitle() == 'File Toolbar'


def test_multiple_toolbars(qtbot):
    """Test creating multiple toolbars"""
    action_manager = ActionManager()

    file_toolbar = action_manager.add_toolbar('file', 'File')
    edit_toolbar = action_manager.add_toolbar('edit', 'Edit')
    view_toolbar = action_manager.add_toolbar('view', 'View')

    assert len(action_manager.toolbars) == 3
    assert len(action_manager.toolbars_names) == 3
    assert action_manager.has_toolbar('file')
    assert action_manager.has_toolbar('edit')
    assert action_manager.has_toolbar('view')


def test_toolbar_getter_errors(qtbot):
    """Test error handling for toolbar getters"""
    action_manager = ActionManager()

    with pytest.raises(KeyError):
        action_manager.get_toolbar('nonexistent')

    assert not action_manager.has_toolbar('nonexistent')


def test_set_toolbar(qtbot):
    """Test setting default toolbar"""
    action_manager = ActionManager()

    toolbar = QtWidgets.QToolBar()
    action_manager.set_toolbar(toolbar)

    assert action_manager.toolbar == toolbar
    assert action_manager._toolbar == toolbar


def test_set_menu(qtbot):
    """Test setting default menu"""
    action_manager = ActionManager()

    menu = QtWidgets.QMenu()
    action_manager.set_menu(menu)

    assert action_manager.menu == menu
    assert action_manager._menu == menu


def test_add_action_to_toolbar(qtbot):
    """Test adding actions to toolbar"""
    toolbar = QtWidgets.QToolBar()
    action_manager = ActionManager(toolbar=toolbar)

    action_manager.add_action('save', 'Save', icon_name='SaveAs', auto_toolbar=True)

    assert action_manager.has_action('save')
    action = action_manager.get_action('save')
    assert action in toolbar.actions()


def test_add_action_to_menu_and_toolbar(qtbot):
    """Test adding action to both menu and toolbar"""
    menu = QtWidgets.QMenu()
    toolbar = QtWidgets.QToolBar()
    action_manager = ActionManager(toolbar=toolbar, menu=menu)

    file_menu = action_manager.add_menu('file', 'File')
    action_manager.add_action('open', 'Open', icon_name='Open',
                             menu='file', auto_toolbar=True)

    action = action_manager.get_action('open')
    assert action in file_menu.actions()
    assert action in toolbar.actions()


def test_affect_to_toolbar(qtbot):
    """Test adding action to toolbar using affect_to"""
    toolbar1 = QtWidgets.QToolBar()
    toolbar2 = QtWidgets.QToolBar()
    action_manager = ActionManager(toolbar=toolbar1)

    action_manager.add_action('copy', 'Copy', auto_toolbar=True)
    action_manager.affect_to('copy', toolbar2)

    action = action_manager.get_action('copy')
    assert action in toolbar1.actions()
    assert action in toolbar2.actions()


def test_affect_to_menu(qtbot):
    """Test adding action to menu using affect_to"""
    menu1 = QtWidgets.QMenu()
    menu2 = QtWidgets.QMenu()
    action_manager = ActionManager(menu=menu1)

    action_manager.add_action('paste', 'Paste', auto_menu=True)
    action_manager.affect_to('paste', menu2)

    action = action_manager.get_action('paste')
    assert action in menu1.actions()
    assert action in menu2.actions()


# ========== Action State Tests ==========

def test_checkable_action(qtbot):
    """Test creating checkable actions"""
    action_manager = ActionManager()

    action_manager.add_action('toggle', 'Toggle', checkable=True, checked=True)

    action = action_manager.get_action('toggle')
    assert action.isCheckable()
    assert action.isChecked()


def test_set_action_checked(qtbot):
    """Test setting action checked state"""
    action_manager = ActionManager()

    action_manager.add_action('toggle', 'Toggle', checkable=True, checked=False)

    assert not action_manager.is_action_checked('toggle')

    action_manager.set_action_checked('toggle', True)
    assert action_manager.is_action_checked('toggle')

    action_manager.set_action_checked('toggle', False)
    assert not action_manager.is_action_checked('toggle')


def test_set_action_checked_multiple(qtbot):
    """Test setting checked state for multiple actions"""
    action_manager = ActionManager()

    action_manager.add_action('toggle1', 'Toggle 1', checkable=True)
    action_manager.add_action('toggle2', 'Toggle 2', checkable=True)

    action_manager.set_action_checked(['toggle1', 'toggle2'], True)

    assert action_manager.is_action_checked('toggle1')
    assert action_manager.is_action_checked('toggle2')


def test_set_action_visible(qtbot):
    """Test setting action visibility"""
    action_manager = ActionManager()

    action_manager.add_action('hidden', 'Hidden', visible=False)

    assert not action_manager.is_action_visible('hidden')

    action_manager.set_action_visible('hidden', True)
    assert action_manager.is_action_visible('hidden')

    action_manager.set_action_visible('hidden', False)
    assert not action_manager.is_action_visible('hidden')


def test_set_action_visible_multiple(qtbot):
    """Test setting visibility for multiple actions"""
    action_manager = ActionManager()

    action_manager.add_action('action1', 'Action 1')
    action_manager.add_action('action2', 'Action 2')

    action_manager.set_action_visible(['action1', 'action2'], False)

    assert not action_manager.is_action_visible('action1')
    assert not action_manager.is_action_visible('action2')


def test_set_action_enabled(qtbot):
    """Test setting action enabled state"""
    action_manager = ActionManager()

    action_manager.add_action('disabled', 'Disabled', enabled=False)

    assert not action_manager.is_action_enabled('disabled')

    action_manager.set_action_enabled('disabled', True)
    assert action_manager.is_action_enabled('disabled')

    action_manager.set_action_enabled('disabled', False)
    assert not action_manager.is_action_enabled('disabled')


def test_set_action_enabled_multiple(qtbot):
    """Test setting enabled state for multiple actions"""
    action_manager = ActionManager()

    action_manager.add_action('action1', 'Action 1')
    action_manager.add_action('action2', 'Action 2')

    action_manager.set_action_enabled(['action1', 'action2'], False)

    assert not action_manager.is_action_enabled('action1')
    assert not action_manager.is_action_enabled('action2')


def test_set_action_text(qtbot):
    """Test setting action text"""
    action_manager = ActionManager()

    action_manager.add_action('rename', 'Original')
    action = action_manager.get_action('rename')
    assert action.text() == 'Original'

    action_manager.set_action_text('rename', 'Modified')
    assert action.text() == 'Modified'


def test_action_with_shortcut(qtbot):
    """Test creating action with keyboard shortcut"""
    action_manager = ActionManager()

    action_manager.add_action('save', 'Save', shortcut='Ctrl+S')

    action = action_manager.get_action('save')
    assert action.shortcut().toString() == 'Ctrl+S'


def test_action_with_tooltip(qtbot):
    """Test creating action with tooltip"""
    action_manager = ActionManager()

    action_manager.add_action('help', 'Help', tip='Get help')

    action = action_manager.get_action('help')
    assert action.toolTip() == 'Get help'


# ========== Widget Tests ==========

def test_add_widget_to_toolbar(qtbot):
    """Test adding widget to toolbar"""
    toolbar = QtWidgets.QToolBar()
    action_manager = ActionManager(toolbar=toolbar)

    widget = action_manager.add_widget('search', 'QLineEdit',
                                      tip='Search', visible=True)

    assert action_manager.has_action('search')
    assert isinstance(widget, QtWidgets.QLineEdit)


def test_add_widget_with_signal(qtbot):
    """Test adding widget with signal connection"""
    toolbar = QtWidgets.QToolBar()
    action_manager = ActionManager(toolbar=toolbar)

    called = []

    def on_text_changed(text):
        called.append(text)

    widget = action_manager.add_widget('input', 'QLineEdit',
                                      signal_str='textChanged',
                                      slot=on_text_changed)

    widget.setText('test')
    qtbot.wait(10)

    assert 'test' in called


def test_add_custom_widget(qtbot):
    """Test adding custom widget class"""
    toolbar = QtWidgets.QToolBar()
    action_manager = ActionManager(toolbar=toolbar)

    class CustomWidget(QtWidgets.QLabel):
        def __init__(self):
            super().__init__("Custom")

    widget = action_manager.add_widget('custom', CustomWidget)

    assert isinstance(widget, CustomWidget)
    assert widget.text() == "Custom"


# ========== Connection Tests ==========

def test_connect_action(qtbot):
    """Test connecting action to slot"""
    action_manager = ActionManager()

    triggered_actions = []

    def on_action_triggered():
        triggered_actions.append('test_action')

    action_manager.add_action('test_action', 'Test')
    action_manager.connect_action('test_action', on_action_triggered)

    action = action_manager.get_action('test_action')
    action.trigger()

    qtbot.wait(10)
    assert 'test_action' in triggered_actions


def test_disconnect_action(qtbot):
    """Test disconnecting action from slot"""
    action_manager = ActionManager()

    triggered_count = []

    def on_action_triggered():
        triggered_count.append(1)

    action_manager.add_action('test', 'Test')
    action_manager.connect_action('test', on_action_triggered, connect=True)

    action = action_manager.get_action('test')
    action.trigger()
    qtbot.wait(10)

    assert len(triggered_count) == 1

    # Disconnect
    action_manager.connect_action('test', on_action_triggered, connect=False)
    action.trigger()
    qtbot.wait(10)

    # Should still be 1, not 2
    assert len(triggered_count) == 1


def test_has_action(qtbot):
    """Test has_action method"""
    action_manager = ActionManager()

    action_manager.add_action('exists', 'Exists')

    assert action_manager.has_action('exists')
    assert not action_manager.has_action('does_not_exist')


def test_action_getter_errors(qtbot):
    """Test error handling for action getters"""
    action_manager = ActionManager()

    with pytest.raises(KeyError):
        action_manager.get_action('nonexistent')


# ========== Integration Tests ==========

def test_complex_menu_toolbar_structure(qtbot):
    """Test complex structure with nested menus and multiple toolbars"""
    menu = QtWidgets.QMenu()
    action_manager = ActionManager(menu=menu)

    # Create toolbar
    toolbar = action_manager.add_toolbar('main', 'Main Toolbar')

    # Create nested menu structure
    file_menu = action_manager.add_menu('file', 'File')
    recent_menu = action_manager.add_menu('recent', 'Recent', menu=file_menu)

    # Add actions to both menu and toolbar
    action_manager.add_action('new', 'New', icon_name='NewFile',
                             menu='file', toolbar=toolbar)
    action_manager.add_action('open', 'Open', icon_name='Open',
                             menu='file', toolbar=toolbar)

    # Add action to submenu only
    action_manager.add_action('recent1', 'Recent 1', menu=recent_menu,
                             auto_toolbar=False)

    # Verify structure
    assert len(action_manager.menus) == 3
    assert len(action_manager.toolbars) == 1
    assert len(action_manager.actions) == 3

    # Verify actions in correct places
    assert action_manager.get_action('new') in file_menu.actions()
    assert action_manager.get_action('new') in toolbar.actions()
    assert action_manager.get_action('recent1') in recent_menu.actions()
    assert action_manager.get_action('recent1') not in toolbar.actions()


def test_action_manager_without_toolbar_or_menu(qtbot):
    """Test ActionManager works without default toolbar or menu"""
    action_manager = ActionManager()

    # Should be able to create actions
    action_manager.add_action('standalone', 'Standalone', auto_toolbar=False, auto_menu=False)

    assert action_manager.has_action('standalone')
    action = action_manager.get_action('standalone')
    assert isinstance(action, QtWidgets.QAction)


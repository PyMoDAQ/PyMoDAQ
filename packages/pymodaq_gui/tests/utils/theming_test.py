"""
Tests for changing the qt_themes theme at runtime: apply_theme, theme-aware
colour resolution and rebuilding ActionManager icons (refresh_icons).
"""
from collections import Counter

import pytest
import qt_themes
from qtpy import QtCore, QtGui, QtWidgets

from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.qt_utils import WhiteCheckboxStyle, apply_theme, theme_signaller
from pymodaq_gui.utils.styling import as_theme_role, create_color, get_current_theme

DARK = 'catppuccin_mocha'
LIGHT = 'catppuccin_latte'
ICON = 'home'


@pytest.fixture
def restore_theme(qtbot):
    """Put back the application palette, style and theme as they were before the test."""
    app = QtWidgets.QApplication.instance()
    style = app.style()
    was_proxy = isinstance(style, WhiteCheckboxStyle)
    base_style = style.baseStyle() if isinstance(style, QtWidgets.QProxyStyle) else style
    style_name = base_style.objectName() or 'fusion'
    palette = QtGui.QPalette(app.palette())
    theme_property = app.property('theme')
    yield
    app.setStyle(style_name)
    if was_proxy:
        app.setStyle(WhiteCheckboxStyle(app.style()))
    app.setPalette(palette)
    app.setProperty('theme', theme_property)


def dominant_color(icon: QtGui.QIcon, state=QtGui.QIcon.State.Off) -> str:
    """Most frequent fully opaque colour of the icon as Qt renders it.

    Goes through a plain QIcon: MaterialIcon.pixmap is overridden in Python and
    ignores the colours added with set_color, unlike Qt's own rendering."""
    image = QtGui.QIcon(icon).pixmap(QtCore.QSize(20, 20), QtGui.QIcon.Mode.Normal, state).toImage()
    counts = Counter(image.pixelColor(x, y).name()
                     for x in range(image.width()) for y in range(image.height())
                     if image.pixelColor(x, y).alpha() == 255)
    return counts.most_common(1)[0][0]


def make_manager(qtbot) -> ActionManager:
    manager = ActionManager(toolbar=QtWidgets.QToolBar(), menu=QtWidgets.QMenu())
    qtbot.addWidget(manager.toolbar)
    qtbot.addWidget(manager.menu)
    return manager


def test_themes_differ():
    """The tests below rely on these two themes having distinct colours."""
    dark, light = qt_themes.get_theme(DARK), qt_themes.get_theme(LIGHT)
    assert dark.is_dark_theme() and not light.is_dark_theme()
    for role in ('red', 'green', 'text'):
        assert getattr(dark, role) != getattr(light, role)


class TestApplyTheme:
    def test_apply_by_name_sets_current_theme(self, qtbot, restore_theme):
        theme = apply_theme(LIGHT)
        assert theme == qt_themes.get_theme(LIGHT)
        assert get_current_theme() == theme

    def test_emits_theme_changed(self, qtbot, restore_theme):
        with qtbot.waitSignal(theme_signaller.theme_changed) as blocker:
            apply_theme(DARK)
        assert blocker.args[0] == qt_themes.get_theme(DARK)

    def test_unknown_name_changes_nothing(self, qtbot, restore_theme):
        apply_theme(DARK)
        with qtbot.assertNotEmitted(theme_signaller.theme_changed):
            assert apply_theme('no_such_theme') is None
        assert get_current_theme() == qt_themes.get_theme(DARK)

    @pytest.mark.parametrize('first, second', [(DARK, LIGHT), (LIGHT, DARK)])
    def test_widgets_under_style_sheet_follow(self, qtbot, restore_theme, first, second):
        """Widgets under a style sheet (e.g. in a pyqtgraph Dock) take their palette when
        polished: they must be re-polished after the new palette is set."""
        apply_theme(first)
        parent = QtWidgets.QWidget()
        parent.setStyleSheet('QWidget { border: 1px solid gray; }')
        child = QtWidgets.QTextEdit(parent)
        qtbot.addWidget(parent)
        parent.show()
        theme = apply_theme(second)
        assert child.palette().base().color() == \
            QtWidgets.QApplication.palette().base().color()
        assert QtWidgets.QApplication.palette().text().color() == theme.text

    def test_checkbox_style_follows_darkness(self, qtbot, restore_theme):
        app = QtWidgets.QApplication.instance()
        apply_theme(DARK)
        assert isinstance(app.style(), WhiteCheckboxStyle)
        apply_theme(LIGHT)
        assert not isinstance(app.style(), WhiteCheckboxStyle)
        apply_theme(DARK)  # re-applied after the style was replaced
        assert isinstance(app.style(), WhiteCheckboxStyle)


class TestThemeColors:
    def test_create_color_uses_current_theme(self, qtbot, restore_theme):
        apply_theme(DARK)
        assert create_color('red') == qt_themes.get_theme(DARK).red
        apply_theme(LIGHT)
        assert create_color('red') == qt_themes.get_theme(LIGHT).red

    def test_create_color_non_role_strings(self, qtbot, restore_theme):
        apply_theme(DARK)
        assert create_color('#123456') == QtGui.QColor('#123456')
        assert create_color('not a colour') is None

    def test_as_theme_role(self, qtbot, restore_theme):
        theme = apply_theme(DARK)
        assert as_theme_role(theme.green) == 'green'
        assert as_theme_role('orange') == 'orange'
        assert as_theme_role(None) is None
        other = QtGui.QColor(1, 2, 3)
        assert as_theme_role(other) is other

    def test_as_theme_role_prefers_hue(self, qtbot, restore_theme):
        theme = apply_theme('github_dark')
        assert theme.primary == theme.blue  # ambiguous colour in this theme
        assert as_theme_role(theme.blue) == 'blue'


class TestRefreshIcons:
    def test_role_color_follows_theme(self, qtbot, restore_theme):
        dark = apply_theme(DARK)
        manager = make_manager(qtbot)
        manager.add_action('a', 'A', ICON, icon_color='red')
        manager.add_action('b', 'B', ICON, icon_color=dark.red)  # resolved QColor, as apps do
        assert dominant_color(manager.get_action('b').icon()) == dark.red.name()

        light = apply_theme(LIGHT)
        manager.refresh_icons()
        assert dominant_color(manager.get_action('a').icon()) == light.red.name()
        assert dominant_color(manager.get_action('b').icon()) == light.red.name()

    def test_icons_follow_apply_theme_automatically(self, qtbot, restore_theme):
        apply_theme(DARK)
        manager = make_manager(qtbot)
        action = manager.add_action('a', 'A', ICON, icon_color='green')
        light = apply_theme(LIGHT)  # no refresh_icons() call
        assert dominant_color(action.icon()) == light.green.name()

    def test_deleted_action_does_not_break_theme_change(self, qtbot, restore_theme):
        manager = make_manager(qtbot)
        action = manager.add_action('a', 'A', ICON)
        manager.remove_action(action='a')
        action.deleteLater()
        del action
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        apply_theme(LIGHT)  # must not raise on the deleted action
        apply_theme(DARK)

    def test_default_color_follows_palette(self, qtbot, restore_theme):
        apply_theme(DARK)
        manager = make_manager(qtbot)
        action = manager.add_action('a', 'A', ICON)
        apply_theme(LIGHT)
        manager.refresh_icons()
        expected = QtWidgets.QApplication.palette().color(
            QtGui.QPalette.ColorGroup.Normal, QtGui.QPalette.ColorRole.WindowText)
        assert dominant_color(action.icon()) == expected.name()

    def test_literal_color_kept(self, qtbot, restore_theme):
        apply_theme(DARK)
        manager = make_manager(qtbot)
        action = manager.add_action('a', 'A', ICON, icon_color='#123456')
        apply_theme(LIGHT)
        manager.refresh_icons()
        assert dominant_color(action.icon()) == '#123456'

    def test_checked_color_and_state_kept(self, qtbot, restore_theme):
        apply_theme(DARK)
        manager = make_manager(qtbot)
        action = manager.add_action('a', 'A', ICON, checkable=True, checked=True,
                                    icon_checked_color='green')
        light = apply_theme(LIGHT)
        manager.refresh_icons()
        assert action.isChecked()
        assert dominant_color(action.icon(), QtGui.QIcon.State.On) == light.green.name()

    def test_explicitly_set_icon_left_alone(self, qtbot, restore_theme):
        """An owner that swaps the icon itself (e.g. DAQ_Viewer's snap state
        colour) must not see it reverted to the original icon by a refresh."""
        dark = apply_theme(DARK)
        manager = make_manager(qtbot)
        action = manager.add_action('a', 'A', ICON, icon_color='red')
        action.set_icon(ICON, icon_color='#123456')
        apply_theme(LIGHT)
        manager.refresh_icons()
        assert dominant_color(action.icon()) == '#123456'

    def test_checkable_toggle_still_refreshed(self, qtbot, restore_theme):
        """set_icon() without argument (the checked/unchecked swap) is internal."""
        apply_theme(DARK)
        manager = make_manager(qtbot)
        action = manager.add_action('a', 'A', ICON, icon_checked='close', icon_color='red',
                                    checkable=True)
        action.trigger()  # checks it and swaps to the checked icon via set_icon()
        assert action.isChecked()
        manager.refresh_icons()
        light = apply_theme(LIGHT)
        manager.refresh_icons()
        action.trigger()  # back to unchecked
        assert dominant_color(action.icon()) == light.red.name()

    def test_toggle_keeps_icon_color(self, qtbot, restore_theme):
        """Checking then unchecking must not reset icon_color to the default colour."""
        manager = make_manager(qtbot)
        action = manager.add_action('a', 'A', ICON, icon_checked='close', icon_color='#123456',
                                    checkable=True)
        action.trigger()
        action.trigger()
        assert not action.isChecked()
        assert dominant_color(action.icon()) == '#123456'

    def test_icon_instance_not_rebuilt(self, qtbot, restore_theme):
        from pymodaq_gui.resources.material_icons import MaterialIcon
        apply_theme(DARK)
        manager = make_manager(qtbot)
        action = manager.add_action('a', 'A', MaterialIcon(ICON, style=MaterialIcon.ROUNDED),
                                    icon_color='#123456')
        apply_theme(LIGHT)
        manager.refresh_icons()
        assert dominant_color(action.icon()) == '#123456'

    def test_actions_without_icon_or_with_qicon(self, qtbot, restore_theme):
        manager = make_manager(qtbot)
        manager.add_action('none', 'No icon', '')
        given = QtGui.QIcon(QtGui.QPixmap(4, 4))
        manager.add_action('qicon', 'QIcon', given)
        manager.refresh_icons()  # must not raise
        assert manager.get_action('none').icon().isNull()
        assert not manager.get_action('qicon').icon().isNull()

    def test_menu_icon_refreshed(self, qtbot, restore_theme):
        apply_theme(DARK)
        manager = make_manager(qtbot)
        menu = manager.add_menu('m', 'Menu', icon_name=ICON)
        apply_theme(LIGHT)  # automatic
        expected = QtWidgets.QApplication.palette().color(
            QtGui.QPalette.ColorGroup.Normal, QtGui.QPalette.ColorRole.WindowText)
        assert dominant_color(menu.icon()) == expected.name()

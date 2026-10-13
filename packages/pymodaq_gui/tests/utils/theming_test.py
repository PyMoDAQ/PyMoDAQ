"""
Tests for changing the qt_themes theme at runtime: apply_theme, theme-aware
colour resolution, rebuilding ActionManager icons (refresh_icons) and plot colours.
"""
from collections import Counter

import numpy as np
import pyqtgraph as pg
import pytest
import qt_themes
from qtpy import QtCore, QtGui, QtWidgets

import pymodaq_gui
from pymodaq_data import data as data_mod
from pymodaq_data.plotting.utils import PlotColors

from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.plotting import plot_theme
from pymodaq_gui.plotting.data_viewers.viewer0D import Viewer0D
from pymodaq_gui.plotting.data_viewers.viewer1D import Viewer1D
from pymodaq_gui.plotting.data_viewers.viewer2D import Viewer2D
from pymodaq_gui.plotting.widgets import PlotWidget
from pymodaq_gui.qt_utils import WhiteCheckboxStyle, apply_theme, theme_signaller
from pymodaq_gui.utils.status_palette import StatusPalette, Status
from pymodaq_gui.utils.styling import ThemeColor, as_theme_role, create_color, get_current_theme

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
    # apply_theme also sets the plot colours (global pyqtgraph options and configuration)
    pg_options = {key: pg.getConfigOption(key) for key in ('background', 'foreground')}
    plot_colors = list(plot_theme.config('data', 'plotting', 'plot_colors'))
    foreground = plot_theme.plot_foreground()
    yield
    app.setStyle(style_name)
    if was_proxy:
        app.setStyle(WhiteCheckboxStyle(app.style()))
    app.setPalette(palette)
    app.setProperty('theme', theme_property)
    pg.setConfigOptions(**pg_options)
    plot_theme.config['data', 'plotting', 'plot_colors'] = plot_colors
    plot_theme._foreground = foreground
    pymodaq_gui.foreground_color = foreground


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


class TestThemeMenu:
    @pytest.fixture
    def no_config_save(self, monkeypatch):
        """apply_qt_theme persists to the user config: keep it in memory only."""
        from pymodaq_gui.managers import action_manager
        saved = list(action_manager.config('gui', 'style', 'theme'))
        monkeypatch.setattr(action_manager.config, 'save', lambda *args, **kwargs: None)
        yield action_manager.config
        action_manager.config['gui', 'style', 'theme'] = saved

    def test_menu_lists_themes_with_current_checked(self, qtbot, restore_theme):
        apply_theme(DARK)
        manager = make_manager(qtbot)
        manager.setup_theme_menu(manager.menu)
        actions = manager.get_menu('theme').actions()
        assert len(actions) == len(qt_themes.get_themes())
        assert [a.text() for a in actions if a.isChecked()] == ['Catppuccin mocha']

    def test_selecting_applies_persists_and_syncs(self, qtbot, restore_theme, no_config_save):
        apply_theme(DARK)
        manager = make_manager(qtbot)
        other = make_manager(qtbot)  # e.g. a second window with its own menu
        manager.setup_theme_menu(manager.menu)
        other.setup_theme_menu(other.menu)
        icon_action = other.add_action('a', 'A', ICON, icon_color='red')

        latte = next(a for a in manager.get_menu('theme').actions() if a.text() == 'Catppuccin latte')
        latte.trigger()

        light = qt_themes.get_theme(LIGHT)
        assert get_current_theme() == light
        assert no_config_save('gui', 'style', 'theme')[0] == LIGHT
        assert [a.text() for a in other.get_menu('theme').actions() if a.isChecked()] == \
            ['Catppuccin latte']
        assert dominant_color(icon_action.icon()) == light.red.name()


class TestThemeColorNames:
    @pytest.mark.parametrize('name', sorted(qt_themes.get_themes()))
    def test_every_theme_defines_every_theme_color(self, name):
        theme = qt_themes.get_themes()[name]
        for role in ThemeColor:
            color = getattr(theme, role.value, None)
            assert isinstance(color, QtGui.QColor) and color.isValid(), (name, role)

    def test_theme_color_is_a_plain_name(self):
        assert ThemeColor.GREEN == 'green'
        assert isinstance(ThemeColor.GREEN, str)

    def test_as_theme_role_returns_theme_color(self, qtbot, restore_theme):
        theme = apply_theme(DARK)
        assert as_theme_role(theme.green) is ThemeColor.GREEN

    def test_status_palette_role(self, qtbot, restore_theme):
        theme = apply_theme(DARK)
        assert StatusPalette.role(Status.RUNNING) is ThemeColor.BLUE
        for status in Status:
            assert StatusPalette.color(status) == getattr(theme, StatusPalette.role(status).value)
        with pytest.raises(ValueError):
            StatusPalette.role('nope')


class TestFollowTheme:
    def test_theme_color_follows(self, qtbot, restore_theme):
        apply_theme(DARK)
        manager = make_manager(qtbot)
        action = manager.add_action('a', 'A', ICON, icon_color=ThemeColor.GREEN)
        light = apply_theme(LIGHT)
        assert dominant_color(action.icon()) == light.green.name()

    @pytest.mark.parametrize('color', [ThemeColor.GREEN, 'green', 'resolved'])
    def test_follow_theme_false_keeps_creation_color(self, qtbot, restore_theme, color):
        dark = apply_theme(DARK)
        if color == 'resolved':
            color = dark.green
        manager = make_manager(qtbot)
        action = manager.add_action('a', 'A', ICON, icon_color=color, icon_checked_color='red',
                                    checkable=True, follow_theme=False)
        apply_theme(LIGHT)
        assert dominant_color(action.icon()) == dark.green.name()
        assert dominant_color(action.icon(), QtGui.QIcon.State.On) == dark.red.name()


WHITE, BLACK = (255, 255, 255), (0, 0, 0)


def rgb(color) -> tuple:
    color = pg.mkColor(color)
    return color.red(), color.green(), color.blue()


def background(view: pg.GraphicsView) -> tuple:
    return rgb(view.backgroundBrush().color())


def data_1d(labels=('a', 'b')) -> data_mod.DataRaw:
    x = np.linspace(0, 10, 11)
    return data_mod.DataRaw('data', data=[x * (ind + 1) for ind in range(len(labels))],
                            labels=list(labels), axes=[data_mod.Axis('x', 'm', data=x)])


@pytest.fixture
def viewer1d(qtbot):
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    viewer = Viewer1D(widget)
    yield viewer
    widget.close()


class TestPlotTheme:
    @pytest.mark.parametrize('name, back, fore', [(DARK, 'k', WHITE), (LIGHT, 'w', BLACK)])
    def test_new_plots_colours(self, qtbot, restore_theme, name, back, fore):
        apply_theme(name)
        assert pg.getConfigOption('background') == back
        assert plot_theme.plot_foreground() == fore
        assert pymodaq_gui.foreground_color == fore
        assert PlotColors()[0] == fore  # the first curve colour, read when created
        assert background(PlotWidget()) == rgb(back)

    def test_configuration_file_not_written(self, qtbot, restore_theme, monkeypatch):
        def fail(*args, **kwargs):
            raise AssertionError('the configuration file should not be written')
        monkeypatch.setattr(plot_theme.config, 'save', fail)
        apply_theme(LIGHT)
        apply_theme(DARK)

    def test_open_viewer1d_follows(self, qtbot, restore_theme, viewer1d):
        apply_theme(DARK)
        viewer1d.show_data(data_1d())
        displayer = viewer1d.view.data_displayer
        second = rgb(displayer.get_plot_item(1).opts['pen'].color())
        assert rgb(displayer.get_plot_item(0).opts['pen'].color()) == WHITE

        apply_theme(LIGHT)
        assert rgb(displayer.get_plot_item(0).opts['pen'].color()) == BLACK
        assert rgb(displayer.get_plot_item(1).opts['pen'].color()) == second  # not a foreground one
        assert background(viewer1d.view.plot_widget) == WHITE
        assert rgb(viewer1d.view.roi_target.pen.color()) == BLACK
        bottom = viewer1d.view.plotitem.getAxis('bottom')
        assert rgb(bottom.pen().color()) == rgb('k')
        assert rgb(bottom.textPen().color()) == rgb('k')

        viewer1d.show_data(data_1d(('c', 'd', 'e')))  # curves created after the change
        assert rgb(displayer.get_plot_item(0).opts['pen'].color()) == BLACK

    def test_line_width_and_alpha_kept(self, qtbot, restore_theme):
        apply_theme(DARK)
        widget = PlotWidget()
        qtbot.addWidget(widget)
        curve = widget.plot([0, 1], [0, 1], pen=pg.mkPen((255, 255, 255, 100), width=3))
        apply_theme(LIGHT)
        pen = curve.opts['pen']
        assert (rgb(pen.color()), pen.color().alpha(), pen.width()) == (BLACK, 100, 3)

    def test_open_viewer0d_follows(self, qtbot, restore_theme):
        apply_theme(DARK)
        widget = QtWidgets.QWidget()
        qtbot.addWidget(widget)
        viewer = Viewer0D(widget)
        viewer.show_data(data_mod.DataRaw('d', data=[np.array([1.]), np.array([2.])], labels=['a', 'b']))
        items = viewer.view.data_displayer._plot_items
        assert rgb(items['a'].opts['pen'].color()) == WHITE

        apply_theme(LIGHT)
        assert rgb(items['a'].opts['pen'].color()) == BLACK
        assert rgb(items['b'].opts['pen'].color()) != BLACK
        viewer.show_data(data_mod.DataRaw('d', data=[np.array([1.])], labels=['c']))
        assert rgb(viewer.view.data_displayer._plot_items['c'].opts['pen'].color()) == BLACK
        widget.close()

    def test_viewer0d_custom_colours_kept(self, qtbot, restore_theme):
        apply_theme(DARK)
        widget = QtWidgets.QWidget()
        qtbot.addWidget(widget)
        viewer = Viewer0D(widget)
        displayer = viewer.view.data_displayer
        displayer.update_colors([dict(color=(1, 2, 3))])
        apply_theme(LIGHT)
        assert displayer.colors[0]['color'] == (1, 2, 3)
        viewer.show_data(data_mod.DataRaw('d', data=[np.array([1.])], labels=['a']))
        assert rgb(displayer._plot_items['a'].opts['pen'].color()) == (1, 2, 3)
        widget.close()

    def test_custom_background_and_axis_kept(self, qtbot, restore_theme):
        apply_theme(DARK)
        widget = PlotWidget()
        qtbot.addWidget(widget)
        widget.setBackground((10, 20, 30))
        widget.getPlotItem().getAxis('left').setPen((40, 50, 60))
        apply_theme(LIGHT)
        assert background(widget) == (10, 20, 30)
        assert rgb(widget.getPlotItem().getAxis('left').pen().color()) == (40, 50, 60)
        assert rgb(widget.getPlotItem().getAxis('bottom').pen().color()) == rgb('k')

    def test_viewer2d_histograms_follow(self, qtbot, restore_theme):
        apply_theme(DARK)
        widget = QtWidgets.QWidget()
        qtbot.addWidget(widget)
        viewer = Viewer2D(widget)
        histogram = viewer.view.histogrammer.get_histogram('red')
        assert background(histogram) == BLACK
        apply_theme(LIGHT)
        assert background(histogram) == WHITE
        assert background(viewer.view.image_widget) == WHITE
        widget.close()

    def test_deleted_plot_does_not_break_theme_change(self, qtbot, restore_theme):
        widget = PlotWidget()
        widget.deleteLater()
        del widget
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        apply_theme(LIGHT)  # must not raise on the deleted plot
        apply_theme(DARK)

"""Groups of actions under a single toolbar button (or a submenu): ActionManager.add_action_group and co"""
import pytest
from qtpy import QtWidgets, QtCore, QtGui

from pymodaq_gui.managers.action_manager import ActionManager, ActionGroup, Indicator
from pymodaq_gui.utils.styling import ThemeColor, create_color


@pytest.fixture
def action_manager(qtbot):
    manager = ActionManager(toolbar=QtWidgets.QToolBar())
    qtbot.addWidget(manager.toolbar)
    return manager


def checkable(short_name, **kwargs):
    return dict(short_name=short_name, name=short_name, checkable=True, **kwargs)


def icon_color(icon: QtGui.QIcon) -> tuple:
    """The average colour of the (nearly) opaque pixels of an icon"""
    image = icon.pixmap(20, 20).toImage()
    colors = [image.pixelColor(x, y) for x in range(image.width()) for y in range(image.height())]
    colors = [color for color in colors if color.alpha() >= 200]
    assert len(colors) > 0, 'empty icon'
    return tuple(round(sum(getattr(color, component)() for color in colors) / len(colors))
                 for component in ('red', 'green', 'blue'))


def shown(toolbar: QtWidgets.QToolBar, button: QtWidgets.QWidget) -> bool:
    """True if the toolbar shows the button (the visibility of the toolbar action holding it)"""
    action = next(action for action in toolbar.actions() if toolbar.widgetForAction(action) is button)
    return action.isVisible()


def assert_icon_color(icon: QtGui.QIcon, color):
    expected = create_color(color) if not isinstance(color, tuple) else QtGui.QColor(*color)
    assert icon_color(icon) == pytest.approx((expected.red(), expected.green(), expected.blue()), abs=3)


def test_reexported_by_action_manager():
    from pymodaq_gui.managers import action_group
    assert (ActionGroup, Indicator) == (action_group.ActionGroup, action_group.Indicator)


class TestGroupHandle:
    def test_button_carries_the_group(self, action_manager):
        button = action_manager.add_action_group('transform', 'Transform', 'flip', checkable=True,
                                                 secondary_actions=[checkable('flip_ud')])

        assert isinstance(button, QtWidgets.QToolButton)
        assert isinstance(button.group, ActionGroup)
        assert action_manager.get_action_group('transform') is button.group
        assert button.group.keys() == ['flip_ud']

    def test_unknown_group_raises(self, action_manager):
        with pytest.raises(KeyError):
            action_manager.get_action_group('nope')

    def test_entry_toggled(self, action_manager, qtbot):
        group = action_manager.add_action_group('transform', 'Transform', 'flip', checkable=True,
                                                secondary_actions=[checkable('flip_ud'), checkable('flip_lr')]).group

        with qtbot.waitSignal(group.entry_toggled) as blocker:
            action_manager.get_action('flip_lr').trigger()

        assert blocker.args == ['flip_lr', True]
        assert group.is_checked('flip_lr')
        assert not group.is_checked('flip_ud')

        group.set_checked('flip_lr', False)
        assert not action_manager.is_action_checked('flip_lr')


class TestExclusive:
    def test_one_entry_checked_at_most(self, action_manager):
        group = action_manager.add_action_group(
            'xmode', 'X axis', 'function', primary=False, exclusive=True,
            secondary_actions=[checkable('x_a', checked=True), checkable('x_b'), checkable('x_c')]).group
        toggles = []
        group.entry_toggled.connect(lambda key, checked: toggles.append((key, checked)))

        group.set_checked('x_b', True)

        assert [key for key in group.keys() if group.is_checked(key)] == ['x_b']
        assert ('x_a', False) in toggles and ('x_b', True) in toggles


class TestWithoutPrimary:
    def test_button_only_opens_the_menu(self, action_manager):
        button = action_manager.add_action_group('channels', 'Channels', 'layers', primary=False,
                                                 secondary_actions=[checkable('channel_0', checked=True)])

        assert 'channels' not in action_manager.actions_names
        assert button.popupMode() == QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup
        assert button.menu().actions() == [action_manager.get_action('channel_0')]
        assert button.toolTip() != '' or button.text() == 'Channels'

    def test_exclusive_button_shows_the_checked_entry(self, action_manager):
        button = action_manager.add_action_group(
            'xmode', 'X axis', 'function', primary=False, exclusive=True,
            secondary_actions=[checkable('x_a', icon_name='timer', checked=True), checkable('x_b', icon_name='sort')])

        button.group.set_checked('x_b', True)

        assert button.icon().cacheKey() == action_manager.get_action('x_b').icon().cacheKey()

    def test_exclusive_button_keeps_the_checked_entry_with_an_indicator(self, action_manager):
        button = action_manager.add_action_group(
            'xmode', 'X axis', 'function', primary=False, exclusive=True,
            secondary_actions=[checkable('x_a', icon_name='timer', checked=True), checkable('x_b', icon_name='sort')])

        for indicator in (Indicator.ACTIVE, Indicator.DEFAULT):
            action_manager.set_action_group_indicator('xmode', indicator, 'tip')
            assert button.icon().cacheKey() == action_manager.get_action('x_a').icon().cacheKey()

    def test_button_options(self, action_manager):
        button = action_manager.add_action_group('channels', 'Channels', 'layers', primary=False,
                                                 icon_color=ThemeColor.BLUE, enabled=False, visible=False,
                                                 secondary_actions=[checkable('channel_0')])

        assert_icon_color(button.icon(), ThemeColor.BLUE)
        assert not button.isEnabled()
        assert not shown(action_manager.toolbar, button)

        button.group.face.setVisible(True)
        assert shown(action_manager.toolbar, button)


class TestVisibility:
    def test_button_follows_the_primary(self, action_manager):
        button = action_manager.add_action_group('transform', 'Transform', 'flip', checkable=True,
                                                 secondary_actions=[checkable('flip_ud')])
        assert shown(action_manager.toolbar, button)

        action_manager.set_action_visible('transform', False)
        assert not shown(action_manager.toolbar, button)

        action_manager.set_action_visible('transform', True)
        assert shown(action_manager.toolbar, button)

    def test_hidden_from_creation(self, action_manager):
        button = action_manager.add_action_group('transform', 'Transform', 'flip', checkable=True, visible=False,
                                                 secondary_actions=[checkable('flip_ud')])

        assert not shown(action_manager.toolbar, button)


class TestDynamicEntries:
    def test_entries_are_replaced(self, action_manager):
        group = action_manager.add_action_group('channels', 'Channels', 'layers', primary=False).group

        action_manager.set_action_group_entries('channels', [checkable('channel_0', key='a', checked=True),
                                                             checkable('channel_1', key='b', checked=True)])
        assert group.keys() == ['a', 'b']

        action_manager.set_action_group_entries('channels', [checkable('channel_0', key='c', checked=True)])
        assert group.keys() == ['c']
        assert 'channel_1' not in action_manager.actions_names
        assert action_manager.get_action_group('channels').menu.actions() == [action_manager.get_action('channel_0')]

    def test_checked_state_is_remembered_by_key(self, action_manager):
        group = action_manager.add_action_group('channels', 'Channels', 'layers', primary=False).group
        action_manager.set_action_group_entries('channels', [checkable('channel_0', key='a', checked=True),
                                                             checkable('channel_1', key='b', checked=True)])
        group.set_checked('b', False)

        # 'b' moved to another position and a new channel appeared
        action_manager.set_action_group_entries('channels', [checkable('channel_0', key='b', checked=True),
                                                             checkable('channel_1', key='c', checked=True)])

        assert not group.is_checked('b')
        assert group.is_checked('c')
        assert not action_manager.is_action_checked('channel_0')

    def test_checked_state_remembered_when_checkable_through_icon_checked(self, action_manager):
        group = action_manager.add_action_group('channels', 'Channels', 'layers', primary=False).group
        spec = dict(short_name='channel_0', key='a', name='a', icon_name='visibility', icon_checked='visibility_off')
        action_manager.set_action_group_entries('channels', [spec])
        group.set_checked('a', True)

        action_manager.set_action_group_entries('channels', [spec])

        assert group.is_checked('a')

    def test_entries_changed_once_per_replacement(self, action_manager):
        group = action_manager.add_action_group('channels', 'Channels', 'layers', primary=False).group
        emitted = []
        group.entries_changed.connect(lambda: emitted.append(True))

        action_manager.set_action_group_entries('channels', [checkable(f'channel_{ind}') for ind in range(5)])

        assert len(emitted) == 1

    def test_nested_groups_stay_after_the_new_entries(self, action_manager):
        group = action_manager.add_action_group(
            'view', 'View', 'visibility', primary=False,
            secondary_actions=[checkable('aspect_ratio'),
                               dict(group='grid', name='Grid', icon_name='grid_on', checkable=True)]).group
        grid_entry = action_manager.get_action_group('grid').menu.menuAction()

        for _ in range(2):  # replacing twice keeps the nested group, once
            action_manager.set_action_group_entries('view', [checkable('ratio_1'), checkable('ratio_2')])

        assert group.menu.actions() == [action_manager.get_action('ratio_1'), action_manager.get_action('ratio_2'),
                                        grid_entry]

    def test_nested_group_spec_rejected(self, action_manager):
        action_manager.add_action_group('view', 'View', 'visibility', primary=False)

        with pytest.raises(ValueError):
            action_manager.set_action_group_entries('view', [dict(group='grid', name='Grid')])
        assert not action_manager.has_action_group('grid')

    def test_duplicate_key_registers_nothing(self, action_manager):
        action_manager.add_action_group('channels', 'Channels', 'layers', primary=False)

        with pytest.raises(KeyError):
            action_manager.set_action_group_entries('channels', [checkable('channel_0', key='a'),
                                                                 checkable('channel_1', key='a')])
        assert 'channel_1' not in action_manager.actions_names


class TestDropdownArrow:
    def test_follows_enabled_entries(self, action_manager):
        button = action_manager.add_action_group('transform', 'Transform', 'flip', checkable=True,
                                                 secondary_actions=[checkable('flip_ud')])
        assert button.popupMode() == QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup

        action_manager.set_action_enabled('flip_ud', False)
        assert button.popupMode() == QtWidgets.QToolButton.ToolButtonPopupMode.DelayedPopup

        action_manager.set_action_enabled('flip_ud', True)
        assert button.popupMode() == QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup


class TestMenuStaysOpen:
    @staticmethod
    def click_entry(qtbot, menu: QtWidgets.QMenu, action):
        menu.popup(QtCore.QPoint(0, 0))
        qtbot.waitExposed(menu)
        qtbot.mouseClick(menu, QtCore.Qt.MouseButton.LeftButton, pos=menu.actionGeometry(action).center())

    def test_checkable_entry_keeps_it_open(self, action_manager, qtbot):
        group = action_manager.add_action_group('transform', 'Transform', 'flip', checkable=True,
                                                secondary_actions=[checkable('flip_ud')]).group

        self.click_entry(qtbot, group.menu, action_manager.get_action('flip_ud'))

        assert action_manager.is_action_checked('flip_ud')
        assert group.menu.isVisible()
        group.menu.hide()

    def test_plain_entry_closes_it(self, action_manager, qtbot):
        group = action_manager.add_action_group('bkg', 'Background', 'texture_minus', checkable=True,
                                                secondary_actions=[dict(short_name='snap', name='Snap')]).group
        triggered = []
        action_manager.connect_action('snap', lambda: triggered.append(True))

        self.click_entry(qtbot, group.menu, action_manager.get_action('snap'))

        assert triggered == [True]
        assert not group.menu.isVisible()


class TestIndicator:
    @pytest.mark.parametrize('indicator, color', [(Indicator.ACTIVE, ThemeColor.GREEN),
                                                  (Indicator.PARTIAL, ThemeColor.YELLOW),
                                                  (Indicator.EMPTY, ThemeColor.ORANGE)])
    def test_icon_colour(self, action_manager, indicator, color):
        button = action_manager.add_action_group('channels', 'Channels', 'layers', primary=False,
                                                 secondary_actions=[checkable('channel_0')])
        action_manager.set_action_group_indicator('channels', indicator)

        assert button.group.indicator is indicator
        assert_icon_color(button.icon(), color)

    def test_tooltip_and_back_to_default(self, action_manager):
        button = action_manager.add_action_group('channels', 'Channels', 'layers', tip='Show the legend',
                                                 checkable=True, secondary_actions=[checkable('channel_0')])
        default_color = icon_color(button.icon())

        action_manager.set_action_group_indicator('channels', Indicator.PARTIAL, 'Ch2 hidden')
        assert 'Show the legend' in button.toolTip() and 'Ch2 hidden' in button.toolTip()

        action_manager.set_action_group_indicator('channels', Indicator.DEFAULT)
        assert button.toolTip() == 'Show the legend'
        assert_icon_color(button.icon(), default_color)

    def test_status_colours(self):
        from pymodaq_gui.utils.status_palette import Status, StatusPalette
        assert [indicator.value for indicator in (Indicator.ACTIVE, Indicator.PARTIAL, Indicator.EMPTY)] == \
               [StatusPalette.role(state) for state in (Status.IDLE, Status.WARNING, Status.ERROR)]

    def test_tooltip_set_by_the_owner_is_kept(self, action_manager):
        button = action_manager.add_action_group('save', 'Save', 'save', tip='Continuous save', checkable=True,
                                                 secondary_actions=[checkable('new_file')])
        action_manager.get_action('save').setToolTip('Continuous save (current file: a.h5)')

        action_manager.set_action_group_indicator('save', Indicator.ACTIVE, 'Saving')
        assert button.toolTip() == 'Continuous save (current file: a.h5)\nSaving'

        action_manager.set_action_group_indicator('save', Indicator.DEFAULT)
        assert button.toolTip() == 'Continuous save (current file: a.h5)'

    def test_fixed_colour_stays_fixed(self, action_manager):
        fixed = create_color(ThemeColor.GREEN)  # a QColor equal to a theme colour, kept fixed
        action_manager.add_action_group('transform', 'Transform', 'flip', checkable=True, icon_color=fixed,
                                        follow_theme=False, secondary_actions=[checkable('flip_ud')])
        face = action_manager.get_action('transform')

        action_manager.set_action_group_indicator('transform', Indicator.PARTIAL)
        action_manager.set_action_group_indicator('transform', Indicator.DEFAULT)

        color = face._icon_spec_colors()[0]
        assert isinstance(color, QtGui.QColor) and not isinstance(color, ThemeColor)
        assert color == fixed


class TestNested:
    def test_group_in_a_submenu(self, action_manager):
        button = action_manager.add_action_group(
            'view', 'View', 'visibility', primary=False,
            secondary_actions=[
                checkable('aspect_ratio'),
                dict(group='transform', name='Transform', icon_name='flip', checkable=True,
                     secondary_actions=[checkable('flip_ud'), checkable('flip_lr')])])
        transform = action_manager.get_action_group('transform')

        submenu_actions = [action for action in button.menu().actions() if action.menu() is not None]
        assert [action.menu() for action in submenu_actions] == [transform.menu]
        # the primary of the nested group is its first entry, then come its own entries
        entries = [action for action in transform.menu.actions() if not action.isSeparator()]
        assert entries == [action_manager.get_action(name) for name in ('transform', 'flip_ud', 'flip_lr')]
        assert transform.keys() == ['flip_ud', 'flip_lr']
        assert button.group.keys() == ['aspect_ratio']

    def test_nested_indicator_on_the_submenu_entry(self, action_manager):
        button = action_manager.add_action_group(
            'view', 'View', 'visibility', primary=False,
            secondary_actions=[dict(group='transform', name='Transform', icon_name='flip', checkable=True,
                                    secondary_actions=[checkable('flip_ud')])])
        transform = action_manager.get_action_group('transform')
        action_manager.set_action_group_indicator('transform', Indicator.ACTIVE)

        assert_icon_color(transform.menu.menuAction().icon(), ThemeColor.GREEN)

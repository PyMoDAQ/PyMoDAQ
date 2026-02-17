# -*- coding: utf-8 -*-
"""Tests for pymodaq.utils.compact_dock_manager."""
from unittest.mock import MagicMock, patch, PropertyMock
import pytest
from qtpy import QtWidgets
from qtpy.QtCore import Qt

from pymodaq_gui.utils import DockArea
from pymodaq.utils.compact_dock_manager import (
    CompactDockManager,
    ModuleCompactDock,
    ActuatorCompactDock,
    DetectorCompactDock,
    LOCKABLE_ACTIONS,
    _PANEL_POSITIONS,
    _POSITION_CYCLE,
    _POSITION_ICONS,
    _read_panel_position,
    _save_panel_position,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_dockarea(qtbot):
    area = DockArea()
    qtbot.addWidget(area)
    area.show()
    return area


def make_manager(qtbot, cls=CompactDockManager):
    area = make_dockarea(qtbot)
    mgr = cls("Test", area)
    qtbot.addWidget(mgr.dock)
    return mgr


def _make_mock_action(checkable=False, checked=False, enabled=True):
    """Return a minimal QAction-like mock."""
    action = MagicMock()
    action.isCheckable.return_value = checkable
    action.isChecked.return_value = checked
    action.isEnabled.return_value = enabled
    return action


def _make_mock_ui(action_names=()):
    """Return a mock module UI with the given action names registered."""
    ui = MagicMock()
    actions = {name: _make_mock_action() for name in action_names}
    ui.has_action.side_effect = lambda n: n in actions
    ui.get_action.side_effect = lambda n: actions[n]
    ui.set_action_enabled.return_value = None
    # toolbar must be a real QToolBar so it can be added to QMainWindow
    ui.toolbar = QtWidgets.QToolBar()
    return ui, actions


def _make_mock_module(action_names=()):
    """Return a mock module with a minimal UI."""
    module = MagicMock()
    module.ui, actions = _make_mock_ui(action_names)
    return module, actions


# ── _PANEL_POSITIONS sanity checks ────────────────────────────────────────────

class TestPanelPositionsConstants:
    def test_all_four_positions_present(self):
        assert set(_PANEL_POSITIONS.keys()) == {'right', 'left', 'top', 'bottom'}

    def test_cycle_covers_all_positions(self):
        assert set(_POSITION_CYCLE) == set(_PANEL_POSITIONS.keys())
        assert len(_POSITION_CYCLE) == len(_PANEL_POSITIONS)

    @pytest.mark.parametrize("pos", _PANEL_POSITIONS)
    def test_required_keys_present(self, pos):
        params = _PANEL_POSITIONS[pos]
        for key in ('direction', 'content_before_toggle', 'horizontal',
                    'toggle_symbol', 'toolbar_orient'):
            assert key in params, f"'{key}' missing from _PANEL_POSITIONS['{pos}']"

    def test_horizontal_positions_use_hbox(self):
        assert _PANEL_POSITIONS['right']['horizontal'] is True
        assert _PANEL_POSITIONS['left']['horizontal'] is True

    def test_vertical_positions_use_vbox(self):
        assert _PANEL_POSITIONS['top']['horizontal'] is False
        assert _PANEL_POSITIONS['bottom']['horizontal'] is False

    def test_right_collapses_leftward(self):
        assert _PANEL_POSITIONS['right']['direction'] == 'left'

    def test_left_collapses_rightward(self):
        assert _PANEL_POSITIONS['left']['direction'] == 'right'

    def test_top_collapses_downward(self):
        # Panel at top: expand downward (▼)
        assert _PANEL_POSITIONS['top']['direction'] == 'bottom'
        assert _PANEL_POSITIONS['top']['toggle_symbol'] == '▼'

    def test_bottom_collapses_upward(self):
        # Panel at bottom: expand upward (▲)
        assert _PANEL_POSITIONS['bottom']['direction'] == 'top'
        assert _PANEL_POSITIONS['bottom']['toggle_symbol'] == '▲'

    def test_toolbar_orientation_horizontal_for_left_right(self):
        assert _PANEL_POSITIONS['right']['toolbar_orient'] == Qt.Orientation.Vertical
        assert _PANEL_POSITIONS['left']['toolbar_orient'] == Qt.Orientation.Vertical

    def test_toolbar_orientation_horizontal_for_top_bottom(self):
        assert _PANEL_POSITIONS['top']['toolbar_orient'] == Qt.Orientation.Horizontal
        assert _PANEL_POSITIONS['bottom']['toolbar_orient'] == Qt.Orientation.Horizontal


# ── _read_panel_position / _save_panel_position ───────────────────────────────

class TestPanelPositionConfig:
    def test_read_returns_default_when_config_unavailable(self):
        import pymodaq.utils.compact_dock_manager as mod
        orig = mod._pymodaq_config
        mod._pymodaq_config = None
        try:
            assert _read_panel_position() == 'right'
        finally:
            mod._pymodaq_config = orig

    def test_read_returns_default_on_exception(self):
        import pymodaq.utils.compact_dock_manager as mod
        cfg = MagicMock()
        cfg.side_effect = Exception("no config")
        orig = mod._pymodaq_config
        mod._pymodaq_config = cfg
        try:
            assert _read_panel_position() == 'right'
        finally:
            mod._pymodaq_config = orig

    def test_read_returns_valid_saved_value(self):
        import pymodaq.utils.compact_dock_manager as mod
        cfg = MagicMock()
        cfg.return_value = 'bottom'
        orig = mod._pymodaq_config
        mod._pymodaq_config = cfg
        try:
            assert _read_panel_position() == 'bottom'
        finally:
            mod._pymodaq_config = orig

    def test_read_ignores_invalid_saved_value(self):
        import pymodaq.utils.compact_dock_manager as mod
        cfg = MagicMock()
        cfg.return_value = 'diagonal'
        orig = mod._pymodaq_config
        mod._pymodaq_config = cfg
        try:
            assert _read_panel_position() == 'right'
        finally:
            mod._pymodaq_config = orig

    def test_save_does_not_raise_on_none_config(self):
        import pymodaq.utils.compact_dock_manager as mod
        orig = mod._pymodaq_config
        mod._pymodaq_config = None
        try:
            _save_panel_position('left')   # must not raise
        finally:
            mod._pymodaq_config = orig


# ── CompactDockManager.__init__ ───────────────────────────────────────────────

class TestCompactDockManagerInit:
    def test_dock_has_correct_title(self, qtbot):
        mgr = make_manager(qtbot)
        assert mgr.dock.title() == "Test"

    def test_main_window_created(self, qtbot):
        mgr = make_manager(qtbot)
        assert isinstance(mgr.main_window, QtWidgets.QMainWindow)

    def test_control_toolbar_created(self, qtbot):
        mgr = make_manager(qtbot)
        assert isinstance(mgr.control_toolbar, QtWidgets.QToolBar)

    def test_initial_panel_position_is_valid(self, qtbot):
        mgr = make_manager(qtbot)
        assert mgr._panel_position in _PANEL_POSITIONS

    def test_collapsible_widget_created(self, qtbot):
        from pymodaq_gui.utils.widgets.collapsible_widget import CollapsibleWidget
        mgr = make_manager(qtbot)
        assert isinstance(mgr.collapsible_widget, CollapsibleWidget)

    def test_rows_dict_starts_empty(self, qtbot):
        mgr = make_manager(qtbot)
        assert mgr._rows == {}

    def test_is_locked_starts_false(self, qtbot):
        mgr = make_manager(qtbot)
        assert mgr.is_locked is False

    def test_lock_action_exists(self, qtbot):
        mgr = make_manager(qtbot)
        assert mgr.has_action('lock')

    def test_position_btn_created(self, qtbot):
        mgr = make_manager(qtbot)
        assert isinstance(mgr._position_btn, QtWidgets.QToolButton)

    def test_position_btn_has_menu_with_four_entries(self, qtbot):
        mgr = make_manager(qtbot)
        assert mgr._position_btn.menu() is not None
        assert len(mgr._position_btn.menu().actions()) == len(_POSITION_ICONS)


# ── CompactDockManager._apply_position ────────────────────────────────────────

class TestApplyPosition:
    @pytest.mark.parametrize("pos", _PANEL_POSITIONS)
    def test_sets_panel_position(self, qtbot, pos):
        mgr = make_manager(qtbot)
        mgr._apply_position(pos)
        assert mgr._panel_position == pos

    def test_invalid_position_falls_back_to_right(self, qtbot):
        mgr = make_manager(qtbot)
        mgr._apply_position('diagonal')
        assert mgr._panel_position == 'right'

    def test_right_creates_modules_row(self, qtbot):
        mgr = make_manager(qtbot)
        mgr._apply_position('right')
        assert mgr._modules_row is not None

    def test_left_creates_modules_row(self, qtbot):
        mgr = make_manager(qtbot)
        mgr._apply_position('left')
        assert mgr._modules_row is not None

    def test_top_no_modules_row(self, qtbot):
        mgr = make_manager(qtbot)
        mgr._apply_position('top')
        assert mgr._modules_row is None

    def test_bottom_no_modules_row(self, qtbot):
        mgr = make_manager(qtbot)
        mgr._apply_position('bottom')
        assert mgr._modules_row is None

    def test_right_main_window_before_collapsible(self, qtbot):
        mgr = make_manager(qtbot)
        mgr._apply_position('right')
        hlay = mgr._modules_row.layout()
        assert hlay.itemAt(0).widget() is mgr.main_window
        assert hlay.itemAt(1).widget() is mgr.collapsible_widget

    def test_left_collapsible_before_main_window(self, qtbot):
        mgr = make_manager(qtbot)
        mgr._apply_position('left')
        hlay = mgr._modules_row.layout()
        assert hlay.itemAt(0).widget() is mgr.collapsible_widget
        assert hlay.itemAt(1).widget() is mgr.main_window

    def test_top_collapsible_above_main_window(self, qtbot):
        mgr = make_manager(qtbot)
        mgr._apply_position('top')
        outer = mgr._outer_vlay
        assert outer.itemAt(0).widget() is mgr.collapsible_widget
        assert outer.itemAt(1).widget() is mgr.main_window

    def test_bottom_main_window_above_collapsible(self, qtbot):
        mgr = make_manager(qtbot)
        mgr._apply_position('bottom')
        outer = mgr._outer_vlay
        assert outer.itemAt(0).widget() is mgr.main_window
        assert outer.itemAt(1).widget() is mgr.collapsible_widget

    @pytest.mark.parametrize("pos", ('right', 'left'))
    def test_horizontal_toolbar_orientation_is_vertical(self, qtbot, pos):
        mgr = make_manager(qtbot)
        mgr._apply_position(pos)
        assert mgr.control_toolbar.orientation() == Qt.Orientation.Vertical

    @pytest.mark.parametrize("pos", ('top', 'bottom'))
    def test_vertical_toolbar_orientation_is_horizontal(self, qtbot, pos):
        mgr = make_manager(qtbot)
        mgr._apply_position(pos)
        assert mgr.control_toolbar.orientation() == Qt.Orientation.Horizontal

    def test_toggle_symbol_matches_position(self, qtbot):
        """The toggle button text must be the collapsed-state symbol for each position."""
        from pymodaq_gui.utils.widgets.collapsible_widget import CollapsibleWidget
        for pos, params in _PANEL_POSITIONS.items():
            mgr = make_manager(qtbot)
            mgr._apply_position(pos)
            cw = mgr.collapsible_widget
            # CollapsibleWidget stores the initial button text in original_text
            assert cw.original_text == params['toggle_symbol'], \
                f"Position '{pos}': expected '{params['toggle_symbol']}', got '{cw.original_text}'"

    def test_apply_twice_does_not_duplicate_widgets_in_outer_layout(self, qtbot):
        mgr = make_manager(qtbot)
        mgr._apply_position('right')
        mgr._apply_position('right')
        # Outer layout should contain exactly one _modules_row
        outer = mgr._outer_vlay
        count = outer.count()
        assert count == 1

    def test_apply_position_top_then_right_cleans_up(self, qtbot):
        mgr = make_manager(qtbot)
        mgr._apply_position('top')
        mgr._apply_position('right')
        # After switching back to horizontal layout, outer should have one _modules_row
        assert mgr._outer_vlay.count() == 1
        assert mgr._modules_row is not None

    def test_apply_position_right_then_top_cleans_up(self, qtbot):
        mgr = make_manager(qtbot)
        mgr._apply_position('right')
        mgr._apply_position('top')
        # After switching to vertical, outer should have two widgets (collapsible + main_window)
        assert mgr._outer_vlay.count() == 2
        assert mgr._modules_row is None

    def test_control_toolbar_survives_position_change(self, qtbot):
        mgr = make_manager(qtbot)
        original_toolbar = mgr.control_toolbar
        mgr._apply_position('bottom')
        assert mgr.control_toolbar is original_toolbar

    def test_rows_survive_position_change(self, qtbot):
        mgr = make_manager(qtbot)
        widget = QtWidgets.QLabel("row")
        mgr.add_widget(widget, create_toolbar=True)
        mgr._apply_position('left')
        assert widget in mgr._rows


# ── CompactDockManager position button ────────────────────────────────────────

class TestPositionButton:
    def test_position_icons_covers_all_positions(self):
        assert set(_POSITION_ICONS.keys()) == set(_PANEL_POSITIONS.keys())

    def test_position_btn_icon_updated_on_apply(self, qtbot):
        mgr = make_manager(qtbot)
        for pos in _POSITION_ICONS:
            mgr._apply_position(pos)
            # Button must have a non-null icon after each position change
            assert not mgr._position_btn.icon().isNull()

    def test_position_btn_menu_checks_current_position(self, qtbot):
        mgr = make_manager(qtbot)
        for pos in _POSITION_ICONS:
            mgr._apply_position(pos)
            checked = [a for a in mgr._position_btn.menu().actions() if a.isChecked()]
            assert len(checked) == 1
            assert checked[0].data() == pos

    def test_menu_action_triggers_apply_position(self, qtbot):
        mgr = make_manager(qtbot)
        mgr._apply_position('right')
        # Find the 'left' menu entry and trigger it
        left_act = next(a for a in mgr._position_btn.menu().actions()
                        if a.data() == 'left')
        left_act.trigger()
        assert mgr._panel_position == 'left'

    def test_cycle_position_helper_still_works(self, qtbot):
        mgr = make_manager(qtbot)
        mgr._apply_position('right')
        mgr._cycle_position()
        assert mgr._panel_position == 'bottom'

    def test_full_cycle_returns_to_start(self, qtbot):
        mgr = make_manager(qtbot)
        mgr._apply_position('right')
        for _ in _POSITION_CYCLE:
            mgr._cycle_position()
        assert mgr._panel_position == 'right'


# ── CompactDockManager row management ─────────────────────────────────────────

class TestRowManagement:
    def test_add_widget_creates_row(self, qtbot):
        mgr = make_manager(qtbot)
        w = QtWidgets.QLabel("hello")
        mgr.add_widget(w)
        assert w in mgr._rows

    def test_add_widget_no_toolbar_wrapping(self, qtbot):
        mgr = make_manager(qtbot)
        tb = QtWidgets.QToolBar()
        mgr.add_widget(tb, create_toolbar=False)
        assert tb in mgr._rows
        assert mgr._rows[tb].toolbar is tb

    def test_remove_widget_returns_true_when_last(self, qtbot):
        mgr = make_manager(qtbot)
        w = QtWidgets.QLabel("hello")
        mgr.add_widget(w)
        assert mgr.remove_widget(w) is True

    def test_remove_widget_returns_false_when_others_remain(self, qtbot):
        mgr = make_manager(qtbot)
        w1 = QtWidgets.QLabel("a")
        w2 = QtWidgets.QLabel("b")
        mgr.add_widget(w1)
        mgr.add_widget(w2)
        assert mgr.remove_widget(w1) is False

    def test_remove_nonexistent_widget(self, qtbot):
        mgr = make_manager(qtbot)
        w = QtWidgets.QLabel("ghost")
        # Should not raise; returns whether dock is empty
        result = mgr.remove_widget(w)
        assert result is True  # dock was empty to begin with

    def test_remove_widget_clears_from_rows(self, qtbot):
        mgr = make_manager(qtbot)
        w = QtWidgets.QLabel("hello")
        mgr.add_widget(w)
        mgr.remove_widget(w)
        assert w not in mgr._rows

    def test_modules_property_only_returns_non_none(self, qtbot):
        mgr = make_manager(qtbot)
        w1 = QtWidgets.QLabel("a")
        w2 = QtWidgets.QLabel("b")
        sentinel = object()
        mgr.add_widget(w1, module=sentinel)
        mgr.add_widget(w2, module=None)
        assert mgr.modules == [sentinel]

    def test_multiple_rows_added_sequentially(self, qtbot):
        mgr = make_manager(qtbot)
        widgets = [QtWidgets.QLabel(str(i)) for i in range(5)]
        for w in widgets:
            mgr.add_widget(w)
        assert len(mgr._rows) == 5


# ── CompactDockManager lock ───────────────────────────────────────────────────

class TestLock:
    def test_toggle_lock_sets_is_locked(self, qtbot):
        mgr = make_manager(qtbot)
        mgr.toggle_lock(True)
        assert mgr.is_locked is True
        mgr.toggle_lock(False)
        assert mgr.is_locked is False

    def test_toggle_lock_emits_signal(self, qtbot):
        mgr = make_manager(qtbot)
        received = []
        mgr.lock_changed.connect(received.append)
        mgr.toggle_lock(True)
        assert received == [True]
        mgr.toggle_lock(False)
        assert received == [True, False]


# ── ModuleCompactDock ─────────────────────────────────────────────────────────

class TestModuleCompactDock:
    def test_add_module_registers_row(self, qtbot):
        mgr = make_manager(qtbot, cls=ModuleCompactDock)
        module, _ = _make_mock_module()
        mgr.add_module(module)
        assert module.ui.toolbar in mgr._rows

    def test_remove_module_returns_true_when_empty(self, qtbot):
        mgr = make_manager(qtbot, cls=ModuleCompactDock)
        module, _ = _make_mock_module()
        mgr.add_module(module)
        assert mgr.remove_module(module) is True

    def test_remove_module_returns_false_when_others_remain(self, qtbot):
        mgr = make_manager(qtbot, cls=ModuleCompactDock)
        m1, _ = _make_mock_module()
        m2, _ = _make_mock_module()
        mgr.add_module(m1)
        mgr.add_module(m2)
        assert mgr.remove_module(m1) is False

    def test_modules_property_lists_added_modules(self, qtbot):
        mgr = make_manager(qtbot, cls=ModuleCompactDock)
        m1, _ = _make_mock_module()
        m2, _ = _make_mock_module()
        mgr.add_module(m1)
        mgr.add_module(m2)
        assert m1 in mgr.modules
        assert m2 in mgr.modules

    def test_apply_lock_calls_set_action_enabled(self, qtbot):
        mgr = make_manager(qtbot, cls=ModuleCompactDock)
        lockable = next(iter(LOCKABLE_ACTIONS))
        module, actions = _make_mock_module(action_names=[lockable])
        mgr.add_module(module)

        mgr._apply_lock(True)
        module.ui.set_action_enabled.assert_called_with(lockable, False)

        mgr._apply_lock(False)
        module.ui.set_action_enabled.assert_called_with(lockable, True)

    def test_apply_lock_disables_widget_proxy(self, qtbot):
        """WidgetActionProxy.widget must be disabled, not just the proxy shell."""
        mgr = make_manager(qtbot, cls=ModuleCompactDock)
        lockable = next(iter(LOCKABLE_ACTIONS))
        module, actions = _make_mock_module(action_names=[lockable])
        # Attach a mock .widget attribute to simulate WidgetActionProxy
        mock_widget = MagicMock()
        actions[lockable].widget = mock_widget
        mgr.add_module(module)

        mgr._apply_lock(True)
        mock_widget.setEnabled.assert_called_with(False)

        mgr._apply_lock(False)
        mock_widget.setEnabled.assert_called_with(True)

    def test_apply_lock_skips_modules_without_action(self, qtbot):
        mgr = make_manager(qtbot, cls=ModuleCompactDock)
        module, _ = _make_mock_module(action_names=[])  # no lockable actions
        mgr.add_module(module)
        # Should not raise
        mgr._apply_lock(True)

    def test_apply_to_modules_triggers_non_checkable(self, qtbot):
        mgr = make_manager(qtbot, cls=ModuleCompactDock)
        module, actions = _make_mock_module(action_names=['snap'])
        mgr.add_module(module)
        mgr._apply_to_modules('snap', checked=None)
        actions['snap'].trigger.assert_called_once()

    def test_apply_to_modules_triggers_checkable_when_state_differs(self, qtbot):
        mgr = make_manager(qtbot, cls=ModuleCompactDock)
        module, actions = _make_mock_module(action_names=['grab'])
        actions['grab'].isChecked.return_value = False
        mgr.add_module(module)
        mgr._apply_to_modules('grab', checked=True)
        actions['grab'].trigger.assert_called_once()

    def test_apply_to_modules_skips_when_state_matches(self, qtbot):
        mgr = make_manager(qtbot, cls=ModuleCompactDock)
        module, actions = _make_mock_module(action_names=['grab'])
        actions['grab'].isChecked.return_value = True
        mgr.add_module(module)
        mgr._apply_to_modules('grab', checked=True)
        actions['grab'].trigger.assert_not_called()

    def test_apply_to_modules_skips_missing_action(self, qtbot):
        mgr = make_manager(qtbot, cls=ModuleCompactDock)
        module, _ = _make_mock_module(action_names=[])
        mgr.add_module(module)
        # Must not raise
        mgr._apply_to_modules('nonexistent', checked=None)


# ── LOCKABLE_ACTIONS completeness ─────────────────────────────────────────────

class TestLockableActions:
    def test_actuator_spinboxes_are_lockable(self):
        for name in ('abs_green', 'abs_red', 'rel_move'):
            assert name in LOCKABLE_ACTIONS

    def test_actuator_buttons_are_lockable(self):
        for name in ('move_abs', 'move_abs_2', 'move_rel_plus', 'move_rel_minus', 'stop'):
            assert name in LOCKABLE_ACTIONS

    def test_detector_actions_are_lockable(self):
        for name in ('snap', 'grab', 'save_current', 'background_snap', 'background_subtract'):
            assert name in LOCKABLE_ACTIONS


# ── ActuatorCompactDock ───────────────────────────────────────────────────────

class TestActuatorCompactDock:
    def test_has_lock_action(self, qtbot):
        mgr = make_manager(qtbot, cls=ActuatorCompactDock)
        assert mgr.has_action('lock')

    def test_has_position_btn(self, qtbot):
        mgr = make_manager(qtbot, cls=ActuatorCompactDock)
        assert isinstance(mgr._position_btn, QtWidgets.QToolButton)

    def test_has_show_graph_action(self, qtbot):
        mgr = make_manager(qtbot, cls=ActuatorCompactDock)
        assert mgr.has_action('show_graph')

    def test_has_refresh_value_action(self, qtbot):
        mgr = make_manager(qtbot, cls=ActuatorCompactDock)
        assert mgr.has_action('refresh_value')

    def test_show_graph_is_checkable(self, qtbot):
        mgr = make_manager(qtbot, cls=ActuatorCompactDock)
        assert mgr.get_action('show_graph').isCheckable()

    def test_refresh_value_is_checkable(self, qtbot):
        mgr = make_manager(qtbot, cls=ActuatorCompactDock)
        assert mgr.get_action('refresh_value').isCheckable()

    def test_show_graph_triggers_apply_to_modules(self, qtbot):
        mgr = make_manager(qtbot, cls=ActuatorCompactDock)
        module, actions = _make_mock_module(action_names=['show_graph'])
        # Global show_graph starts checked=True; triggering it emits checked=False.
        # _apply_to_modules only fires when the module state differs from the target,
        # so the module action must currently be True (≠ False target).
        actions['show_graph'].isChecked.return_value = True
        mgr.add_module(module)
        # Trigger the global show_graph action (currently checked=True → flips to False)
        mgr.get_action('show_graph').trigger()
        actions['show_graph'].trigger.assert_called()


# ── DetectorCompactDock ───────────────────────────────────────────────────────

class TestDetectorCompactDock:
    def test_has_lock_action(self, qtbot):
        mgr = make_manager(qtbot, cls=DetectorCompactDock)
        assert mgr.has_action('lock')

    def test_has_position_btn(self, qtbot):
        mgr = make_manager(qtbot, cls=DetectorCompactDock)
        assert isinstance(mgr._position_btn, QtWidgets.QToolButton)

    def test_has_snap_action(self, qtbot):
        mgr = make_manager(qtbot, cls=DetectorCompactDock)
        assert mgr.has_action('snap')

    def test_has_grab_action(self, qtbot):
        mgr = make_manager(qtbot, cls=DetectorCompactDock)
        assert mgr.has_action('grab')

    def test_has_show_graphs_action(self, qtbot):
        mgr = make_manager(qtbot, cls=DetectorCompactDock)
        assert mgr.has_action('show_graphs')

    def test_snap_is_not_checkable(self, qtbot):
        mgr = make_manager(qtbot, cls=DetectorCompactDock)
        assert not mgr.get_action('snap').isCheckable()

    def test_grab_is_checkable(self, qtbot):
        mgr = make_manager(qtbot, cls=DetectorCompactDock)
        assert mgr.get_action('grab').isCheckable()

    def test_show_graphs_is_checkable(self, qtbot):
        mgr = make_manager(qtbot, cls=DetectorCompactDock)
        assert mgr.get_action('show_graphs').isCheckable()

    def test_snap_triggers_apply_to_modules(self, qtbot):
        mgr = make_manager(qtbot, cls=DetectorCompactDock)
        module, actions = _make_mock_module(action_names=['snap'])
        mgr.add_module(module)
        mgr.get_action('snap').trigger()
        actions['snap'].trigger.assert_called()

    def test_grab_triggers_apply_to_modules(self, qtbot):
        mgr = make_manager(qtbot, cls=DetectorCompactDock)
        module, actions = _make_mock_module(action_names=['grab'])
        actions['grab'].isChecked.return_value = False
        mgr.add_module(module)
        mgr.get_action('grab').trigger()
        actions['grab'].trigger.assert_called()

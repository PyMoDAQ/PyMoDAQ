"""
Tests for preset execution when modules are already initialized.

Regression tests for the bug where a single try/except around the cleanup
loop caused remaining modules to be skipped if one module's quit_fun() raised.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from qtpy import QtWidgets

import qt_themes
from pymodaq.dashboard import create_load_dashboard
from pymodaq.utils.config import get_set_preset_path
from pymodaq_utils.config import GlobalConfig

config = GlobalConfig()


@pytest.fixture
def init_qt(qtbot):
    qt_themes.set_theme(
        theme=config('gui', 'style', 'theme')[0],
        style=config('gui', 'style', 'style')[0],
    )
    return qtbot


@pytest.fixture
def dashboard(init_qt):
    qtbot = init_qt
    shared_ui, db = create_load_dashboard()
    qtbot.addWidget(shared_ui.mainwindow)
    shared_ui.show()
    yield db
    db.quit_fun()


# ---------------------------------------------------------------------------
# Unit tests: remove_actuators / remove_detectors loop resilience
# ---------------------------------------------------------------------------

class TestRemoveActuatorsLoopResilient:
    """remove_actuators must clean up ALL modules even if one raises."""

    def _make_mock_module(self, title, raises=False):
        m = MagicMock()
        m.title = title
        if raises:
            m.quit_fun.side_effect = RuntimeError("simulated C++ object deleted")
        return m

    def test_all_modules_quit_called_when_first_raises(self, dashboard):
        """
        Regression test: if module[0].quit_fun() raises, module[1].quit_fun()
        must still be called.
        """
        mod0 = self._make_mock_module("Move0", raises=True)
        mod1 = self._make_mock_module("Move1", raises=False)

        # Inject mocks directly into the modules manager list
        dashboard.modules_manager._actuators = [mod0, mod1]
        # Ensure compact manager is None so we hit the simpler path
        dashboard.compact_actuator_manager = None

        dashboard.remove_actuators([mod0, mod1])

        mod0.quit_fun.assert_called_once()
        mod1.quit_fun.assert_called_once()

    def test_all_modules_quit_called_when_last_raises(self, dashboard):
        mod0 = self._make_mock_module("Move0", raises=False)
        mod1 = self._make_mock_module("Move1", raises=True)

        dashboard.modules_manager._actuators = [mod0, mod1]
        dashboard.compact_actuator_manager = None

        dashboard.remove_actuators([mod0, mod1])

        mod0.quit_fun.assert_called_once()
        mod1.quit_fun.assert_called_once()

    def test_all_modules_quit_called_when_middle_raises(self, dashboard):
        mods = [self._make_mock_module(f"Move{i}", raises=(i == 1)) for i in range(3)]

        dashboard.modules_manager._actuators = list(mods)
        dashboard.compact_actuator_manager = None

        dashboard.remove_actuators(list(mods))

        for m in mods:
            m.quit_fun.assert_called_once()

    def test_modules_removed_from_list_even_when_quit_raises(self, dashboard):
        """After remove_actuators, the modules list should be empty."""
        mod0 = self._make_mock_module("Move0", raises=True)
        mod1 = self._make_mock_module("Move1", raises=True)

        dashboard.modules_manager._actuators = [mod0, mod1]
        dashboard.compact_actuator_manager = None

        dashboard.remove_actuators([mod0, mod1])

        assert dashboard.actuators_modules == []


class TestRemoveDetectorsLoopResilient:
    """remove_detectors must clean up ALL modules even if one raises."""

    def _make_mock_module(self, title, raises=False):
        m = MagicMock()
        m.title = title
        if raises:
            m.quit_fun.side_effect = RuntimeError("simulated C++ object deleted")
        return m

    def test_all_modules_quit_called_when_first_raises(self, dashboard):
        mod0 = self._make_mock_module("Det0", raises=True)
        mod1 = self._make_mock_module("Det1", raises=False)

        dashboard.modules_manager._detectors = [mod0, mod1]
        dashboard.compact_detector_manager = None

        dashboard.remove_detectors([mod0, mod1])

        mod0.quit_fun.assert_called_once()
        mod1.quit_fun.assert_called_once()

    def test_all_modules_quit_called_when_middle_raises(self, dashboard):
        mods = [self._make_mock_module(f"Det{i}", raises=(i == 1)) for i in range(3)]

        dashboard.modules_manager._detectors = list(mods)
        dashboard.compact_detector_manager = None

        dashboard.remove_detectors(list(mods))

        for m in mods:
            m.quit_fun.assert_called_once()

    def test_modules_removed_from_list_even_when_quit_raises(self, dashboard):
        mod0 = self._make_mock_module("Det0", raises=True)
        mod1 = self._make_mock_module("Det1", raises=True)

        dashboard.modules_manager._detectors = [mod0, mod1]
        dashboard.compact_detector_manager = None

        dashboard.remove_detectors([mod0, mod1])

        assert dashboard.detector_modules == []


# ---------------------------------------------------------------------------
# Integration test: execute preset twice (the original reported bug)
# ---------------------------------------------------------------------------

class TestPresetExecutedTwice:
    """
    When a preset is executed while modules are already loaded, the old modules
    must be fully cleaned up and new modules created.
    """

    def test_second_execute_cleans_old_modules(self, dashboard):
        """
        Execute the default preset once, then execute it a second time.
        The second execution must succeed and the module count must match
        the preset (not double).
        """
        # First execution
        dashboard.preset_manager.execute_entry()
        assert dashboard.preset_manager.entry_applied is True

        n_actuators_after_first = len(dashboard.actuators_modules)
        n_detectors_after_first = len(dashboard.detector_modules)

        # Patch dialog so it auto-confirms (returns True) without showing UI
        with patch(
            "pymodaq.utils.managers.preset.preset_manager.dialog",
            return_value=True,
        ):
            dashboard.preset_manager.execute_entry()

        assert dashboard.preset_manager.entry_applied is True

        # Module count after second load must equal first load, not double
        assert len(dashboard.actuators_modules) == n_actuators_after_first
        assert len(dashboard.detector_modules) == n_detectors_after_first

    def test_second_execute_with_one_failing_module_still_loads_new_modules(
        self, dashboard
    ):
        """
        If one module's quit_fun() raises during cleanup, the second preset
        execution must still complete. We inject a single stray mock module
        (no real hardware thread) with a failing quit_fun, then execute the
        preset a second time and verify the mock was attempted and the new
        real modules loaded correctly.
        """
        # First execution to populate real modules
        dashboard.preset_manager.execute_entry()
        assert dashboard.preset_manager.entry_applied is True

        expected_n_actuators = len(dashboard.actuators_modules)
        expected_n_detectors = len(dashboard.detector_modules)

        # Inject a stray mock actuator that has no real hardware thread
        # but whose quit_fun raises — simulating a partially-deleted module
        stray = MagicMock()
        stray.title = "__stray_mock__"
        stray.quit_fun.side_effect = RuntimeError("simulated C++ widget deleted")
        dashboard.modules_manager._actuators.append(stray)

        with patch(
            "pymodaq.utils.managers.preset.preset_manager.dialog",
            return_value=True,
        ):
            dashboard.preset_manager.execute_entry()

        assert dashboard.preset_manager.entry_applied is True
        # stray module's quit_fun was attempted
        stray.quit_fun.assert_called_once()
        # Real module count restored correctly (stray excluded)
        assert len(dashboard.actuators_modules) == expected_n_actuators
        assert len(dashboard.detector_modules) == expected_n_detectors

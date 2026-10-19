from unittest.mock import MagicMock

import pytest

from pymodaq_gui.managers.manager_base import ManagerBase
from pymodaq_gui.managers.settings.settings_manager import SettingsManager
from pymodaq_gui.qt_utils import mkQApp

from pymodaq.utils.custom_ext import CustomExt, DashBoardToolbarActions
from pymodaq.utils.dashboard_mixin import DashboardMixin, DashBoardToolbarActions as MixinActions
from pymodaq.extensions.scan.manager.scan_manager import ScanManager
from pymodaq.utils.managers.experiment.experiment_manager import ExperimentManager
from pymodaq.utils.managers.extension.extension_manager import ExtensionManager
from pymodaq.utils.managers.overshoot.overshooter import Overshooter
from pymodaq.utils.managers.roi_manager.roi_manager import ROIManager
from pymodaq.utils.managers.modules.modules_manager import ModuleType
from pymodaq.utils.managers.state.state_manager import StateManager


@pytest.fixture
def qapp():
    return mkQApp('dashboard_mixin_test')


def test_lower_packages_do_not_know_the_dashboard():
    assert not issubclass(ManagerBase, DashboardMixin)
    assert not issubclass(SettingsManager, DashboardMixin)
    assert not hasattr(ManagerBase, 'modules_manager')


@pytest.mark.parametrize('manager_class', [ROIManager, ExperimentManager, ExtensionManager,
                                           Overshooter, StateManager, ScanManager])
def test_managers_working_on_the_dashboard(manager_class):
    assert issubclass(manager_class, DashboardMixin)
    assert issubclass(manager_class, ManagerBase)
    # each manager decides if its entries can be executed (the base one never can)
    assert 'can_execute_entry' in vars(manager_class)


def test_mixin_is_shared_with_extensions_and_managers():
    assert issubclass(CustomExt, DashboardMixin)
    assert DashBoardToolbarActions is MixinActions  # still importable from custom_ext


def test_manager_without_dashboard(qapp):
    manager = ExperimentManager()
    assert manager.dashboard is None
    assert not manager.is_dashboard_available
    assert manager.modules_manager is None
    assert not manager.can_execute_entry()


def test_base_manager_does_not_execute_entries(qapp):
    assert not SettingsManager().can_execute_entry()


@pytest.fixture
def dashboard():
    from pymodaq.dashboard import create_load_dashboard
    mkQApp('dashboard_mixin_test')
    shared_ui, dashboard = create_load_dashboard(show_dashboard=False)
    yield dashboard
    dashboard.quit_fun()
    for widget in (shared_ui.parent, dashboard.tree):
        widget.close()
        widget.deleteLater()


def test_manager_with_dashboard(dashboard):
    for manager in (dashboard.experiment_manager, dashboard.state_manager,
                    dashboard.roi_manager, dashboard.overshooter, dashboard.extension_manager):
        assert manager.dashboard is dashboard
        assert manager.is_dashboard_available
        assert manager.modules_manager is not None
    for manager in (dashboard.experiment_manager, dashboard.state_manager, dashboard.roi_manager,
                    dashboard.overshooter, dashboard.extension_manager):
        assert manager.can_execute_entry()


def test_managers_only_looking_modules_up_use_the_one_of_the_dashboard(dashboard):
    """Their own copy would stay empty until an experiment is applied: executing a state before then failed"""
    assert dashboard.state_manager.modules_manager is dashboard.modules_manager
    assert dashboard.roi_manager.modules_manager is dashboard.modules_manager
    # the ones selecting their own modules keep an instance of their own
    assert dashboard.overshooter.modules_manager is not dashboard.modules_manager
    assert dashboard.experiment_manager.modules_manager is not dashboard.modules_manager

    module = MagicMock()
    module.title = 'act'
    dashboard.modules_manager.actuators_all = [module]  # as when modules are added, no experiment applied
    assert dashboard.state_manager.modules_manager.get_mod_from_name('act', ModuleType.Actuator) is module


def test_state_manager_without_dashboard_has_no_modules_manager(qapp):
    assert StateManager().modules_manager is None


def test_dashboard_is_available_in_setup_ui(dashboard):
    seen = []

    class MyManager(DashboardMixin, ManagerBase):
        entry_type = 'mine'
        entry_extension = '.mine'

        def setup_ui(self):
            seen.append((self.dashboard, self.modules_manager))
            super().setup_ui()

    try:
        MyManager(dashboard=dashboard)
    except Exception:
        pass  # the abstract parts of a bare manager are not the point here
    assert seen and seen[0][0] is dashboard and seen[0][1] is not None


def test_managers_windows_are_closed_when_the_dashboard_quits(dashboard):
    managers = (dashboard.experiment_manager, dashboard.state_manager, dashboard.overshooter,
                dashboard.roi_manager)
    for manager in managers:
        manager.mainwindow.show()
    dashboard.quit_fun()
    assert not any(manager.mainwindow.isVisible() for manager in managers)


def test_qt_side_is_initialized_before_the_dashboard_is_set(dashboard, monkeypatch):
    """The dashboard (and its ModulesManager) are set once CustomApp (QObject...) is initialized"""
    seen = []
    init_dashboard = DashboardMixin.init_dashboard

    def checking_init_dashboard(self, *args, **kwargs):
        seen.append(hasattr(self, 'mainwindow'))
        init_dashboard(self, *args, **kwargs)

    monkeypatch.setattr(DashboardMixin, 'init_dashboard', checking_init_dashboard)
    ExperimentManager(dashboard=dashboard)
    assert seen == [True]


def test_unknown_keyword_of_a_manager_is_refused(qapp):
    with pytest.raises(TypeError):
        SettingsManager(dashboard=None)

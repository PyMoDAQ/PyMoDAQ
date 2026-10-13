import pytest

from pymodaq_gui.managers.manager_base import ManagerBase
from pymodaq_gui.managers.settings.settings_manager import SettingsManager
from pymodaq_gui.qt_utils import mkQApp

from pymodaq.utils.custom_ext import CustomExt, DashBoardToolbarActions
from pymodaq.utils.dashboard_mixin import DashboardMixin, DashBoardToolbarActions as MixinActions
from pymodaq.utils.managers.manager_with_dashboard import ManagerWithDashboard
from pymodaq.utils.managers.experiment.experiment_manager import ExperimentManager
from pymodaq.utils.managers.extension.extension_manager import ExtensionManager
from pymodaq.utils.managers.overshoot.overshooter import Overshooter
from pymodaq.utils.managers.roi_manager.roi_manager import ROIManager
from pymodaq.utils.managers.state.state_manager import StateManager


@pytest.fixture
def qapp():
    return mkQApp('manager_with_dashboard_test')


def test_lower_packages_do_not_know_the_dashboard():
    assert not issubclass(ManagerBase, DashboardMixin)
    assert not issubclass(SettingsManager, DashboardMixin)
    assert not hasattr(ManagerBase, 'modules_manager')


@pytest.mark.parametrize('manager_class', [ROIManager, ExperimentManager, ExtensionManager,
                                           Overshooter])
def test_managers_working_on_the_dashboard(manager_class):
    assert issubclass(manager_class, ManagerWithDashboard)


def test_mixin_is_shared_with_extensions_and_state_manager():
    assert issubclass(CustomExt, DashboardMixin)
    assert issubclass(StateManager, DashboardMixin)
    assert issubclass(ManagerWithDashboard, DashboardMixin)
    assert DashBoardToolbarActions is MixinActions  # still importable from custom_ext


def test_manager_without_dashboard(qapp):
    manager = ExperimentManager()
    assert manager.dashboard is None
    assert manager.modules_manager is None
    assert not manager.can_execute_entry()


def test_base_manager_does_not_execute_entries(qapp):
    assert not SettingsManager().can_execute_entry()


@pytest.fixture
def dashboard():
    from pymodaq.dashboard import create_load_dashboard
    mkQApp('manager_with_dashboard_test')
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
        assert manager.modules_manager is not None
    assert dashboard.overshooter.can_execute_entry()


def test_dashboard_is_available_in_setup_ui(dashboard):
    seen = []

    class MyManager(ManagerWithDashboard):
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

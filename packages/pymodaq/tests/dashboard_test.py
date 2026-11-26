import sys
import tempfile
from pathlib import Path

import pymodaq.dashboard as dashboard_module
from pymodaq_gui import qt_utils
from pymodaq.utils.config import get_set_experiment_path
from pymodaq_utils.config import GlobalConfig
from pytest import fixture, raises
from pymodaq.dashboard import create_load_dashboard

import qt_themes
from pymodaq.utils.dashboard_mixin import DashboardMixin
from pymodaq_gui.managers.manager_base import ManagerBase

experiment_path = get_set_experiment_path()
config = GlobalConfig()


@fixture
def init_qt(qtbot):
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0],
                        style=config('gui', 'style', 'style')[0])
    return qtbot


class ExtraManager(DashboardMixin, ManagerBase):
    entry_type = 'extra'
    entry_extension = '.extra'
    icon_name = 'select'
    quit_called = False
    folder = None

    def get_entry_folder(self, **kwargs_to_entry_folder):
        if ExtraManager.folder is None:
            ExtraManager.folder = Path(tempfile.mkdtemp())
        return ExtraManager.folder

    def _update_entry(self, entry: str):
        pass

    def save_entries(self, entry_path=None):
        entry_path.write_text('')

    def quit_fun(self):
        ExtraManager.quit_called = True
        super().quit_fun()


class TestGeneral:
    def test_import(self, init_qt):
        qtbot = init_qt
        shared_ui, dashboard = create_load_dashboard()
        qtbot.addWidget(shared_ui.mainwindow)
        shared_ui.show()

        dashboard.experiment_manager.execute_entry()

        shared_ui.quit_fun()  # quits the dashboard too, as its Quit action

    def test_main_preserves_dashboard_visibility_after_loading(
        self, init_qt, monkeypatch
    ):
        qtbot = init_qt
        shared_ui, dashboard = create_load_dashboard()
        qtbot.addWidget(shared_ui.mainwindow)

        class ApplicationStub:
            @staticmethod
            def exec():
                return 0

        try:
            assert shared_ui.mainwindow.isVisible()
            shared_ui.hide()

            monkeypatch.setattr(
                sys, 'argv', ['dashboard', '--experiment', 'test']
            )
            monkeypatch.setattr(
                qt_utils, 'mkQApp', lambda _: ApplicationStub()
            )
            monkeypatch.setattr(
                dashboard_module,
                'load_dashboard_with_experiment',
                lambda **_: (dashboard, None, shared_ui),
            )

            with raises(SystemExit) as exit_info:
                dashboard_module.main()

            assert exit_info.value.code == 0
            assert not shared_ui.mainwindow.isVisible()
        finally:
            shared_ui.quit_fun()  # quits the dashboard too, as its Quit action


def test_quit_while_loading_experiment(init_qt):
    """Quitting during the (asynchronous) loading of an experiment should stop the loading and the hardware
    threads of the modules already created"""
    qtbot = init_qt
    shared_ui, dashboard = create_load_dashboard()
    qtbot.addWidget(shared_ui.mainwindow)

    dashboard.experiment_manager.execute_entry()
    loader = dashboard.experiment_manager.loader
    modules = loader._modules[:]
    assert not loader._finished  # still loading
    threads = [module.controller_and_thread.thread for module in modules]

    shared_ui.quit_fun()  # quits the dashboard too, as its Quit action

    for thread in threads:
        assert thread is None or not thread.isRunning()
    for module in modules:
        thread = module.controller_and_thread.thread
        assert thread is None or not thread.isRunning()

    qtbot.wait(500)  # pending signals should not resume the loading
    assert len(loader._modules) == len(modules)


class TestExtraManagers:
    def test_extra_manager_is_created_and_enabled_with_the_experiment(self, init_qt, monkeypatch):
        qtbot = init_qt
        monkeypatch.setattr(dashboard_module, 'get_extra_managers', lambda: {'extra': ExtraManager})
        monkeypatch.setattr(dashboard_module, 'show_toolbar_in_dashboard', lambda name: True)
        ExtraManager.quit_called = False
        shared_ui, dashboard = create_load_dashboard()
        qtbot.addWidget(shared_ui.mainwindow)
        shared_ui.show()

        manager = dashboard.extra_managers['extra']
        assert isinstance(manager, ExtraManager)
        assert manager.dashboard is dashboard
        assert not dashboard.get_menu('manager_extra').isEnabled()

        dashboard.experiment_manager.execute_entry()
        qtbot.waitUntil(lambda: dashboard.get_menu('manager_extra').isEnabled(), timeout=30000)  # async loading

        assert dashboard.get_toolbar('manager_extra').isEnabled()

        shared_ui.quit_fun()
        assert ExtraManager.quit_called

    def test_toolbar_is_not_added_when_deactivated_in_the_preferences(self, init_qt, monkeypatch):
        qtbot = init_qt
        monkeypatch.setattr(dashboard_module, 'get_extra_managers', lambda: {'extra': ExtraManager})
        monkeypatch.setattr(dashboard_module, 'show_toolbar_in_dashboard', lambda name: False)
        shared_ui, dashboard = create_load_dashboard()
        qtbot.addWidget(shared_ui.mainwindow)
        shared_ui.show()

        assert 'extra' in dashboard.extra_managers
        assert 'manager_extra' not in dashboard._toolbars  # no toolbar in the dashboard
        assert dashboard.get_menu('manager_extra') is not None  # but the menu is there

        dashboard.experiment_manager.execute_entry()
        qtbot.waitUntil(lambda: dashboard.get_menu('manager_extra').isEnabled(), timeout=30000)

        shared_ui.quit_fun()

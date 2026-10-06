import sys

import pymodaq.dashboard as dashboard_module
from pymodaq_gui import qt_utils
from pymodaq.utils.config import get_set_experiment_path
from pymodaq_utils.config import GlobalConfig
from pytest import fixture, raises
from pymodaq.dashboard import create_load_dashboard

import qt_themes

preset_path = get_set_experiment_path()
config = GlobalConfig()


@fixture
def init_qt(qtbot):
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0],
                        style=config('gui', 'style', 'style')[0])
    return qtbot


class TestGeneral:
    def test_import(self, init_qt):
        qtbot = init_qt
        shared_ui, dashboard = create_load_dashboard()
        qtbot.addWidget(shared_ui.mainwindow)
        shared_ui.show()

        dashboard.experiment_manager.execute_entry()

        dashboard.quit_fun()

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
            dashboard.quit_fun()


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

    dashboard.quit_fun()

    for thread in threads:
        assert thread is None or not thread.isRunning()
    for module in modules:
        thread = module.controller_and_thread.thread
        assert thread is None or not thread.isRunning()

    qtbot.wait(500)  # pending signals should not resume the loading
    assert len(loader._modules) == len(modules)

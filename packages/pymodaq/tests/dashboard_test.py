from pymodaq.utils.config import get_set_experiment_path
from pymodaq_utils.config import GlobalConfig
from pytest import fixture, mark
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

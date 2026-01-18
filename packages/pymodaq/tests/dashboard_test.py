from pymodaq.utils.config import Config, get_set_preset_path
from pytest import fixture, mark
from pymodaq.utils.gui_utils.loader_utils import create_load_dashboard


preset_path = get_set_preset_path()
config = Config()

@fixture
def init_qt(qtbot):
    return qtbot


class TestGeneral:
    def test_import(self, init_qt):
        qtbot = init_qt
        shared_ui, dashboard = create_load_dashboard()
        qtbot.addWidget(shared_ui.mainwindow)
        shared_ui.show()

        dashboard.preset_manager.execute_entry()

        dashboard.quit_fun()

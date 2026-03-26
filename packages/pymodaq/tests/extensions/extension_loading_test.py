from qtpy import QtWidgets

from pymodaq.utils.config import get_set_preset_path
from pymodaq_utils.config import GlobalConfig
from pytest import fixture, mark
from pymodaq.dashboard import create_load_dashboard, extensions

import qt_themes

preset_path = get_set_preset_path()
config = GlobalConfig()

@fixture
def init_qt(qtbot):
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0],
                        style=config('gui', 'style', 'style')[0])
    return qtbot

@fixture
def dashboard(init_qt):
    qtbot = init_qt
    shared_ui, dashboard = create_load_dashboard()
    qtbot.addWidget(shared_ui.mainwindow)
    shared_ui.show()

    # dashboard.preset_manager.execute_entry()
    yield dashboard
    dashboard.quit_fun()



class TestExtensions:
    @mark.parametrize('ext', extensions)
    def test_load(self, dashboard, ext):
        dashboard = dashboard

        dashboard.load_extension(ext)
        QtWidgets.QApplication.processEvents()





from qtpy import QtWidgets

from pymodaq.utils.config import get_set_experiment_path
from pymodaq_utils.config import GlobalConfig
from pytest import fixture, mark
from pymodaq.dashboard import create_load_dashboard, extensions

import qt_themes

experiment_path = get_set_experiment_path()
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
    shared_ui.show()

    yield dashboard

    shared_ui.quit()
    qtbot.wait(200)



class TestExtensions:
    @mark.parametrize('ext', extensions)
    def test_load(self, dashboard, ext):
        dashboard.load_extension(ext)
        QtWidgets.QApplication.processEvents()





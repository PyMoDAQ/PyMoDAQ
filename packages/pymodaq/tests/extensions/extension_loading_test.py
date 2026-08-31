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
    qtbot.addWidget(shared_ui.parent)
    qtbot.addWidget(dashboard.tree)
    # dashboard.preset_manager.execute_entry()
    yield dashboard, qtbot
    dashboard.quit_fun()
    # CRITICAL: Let the main thread finish all deferred pyqtgraph signals
    # block_signals=False ensures timers can still trigger
    qtbot.wait_active(dashboard.parent)

    # Alternative: Flush the event loop multiple times to clear the queue
    for _ in range(10):
        QtWidgets.QApplication.processEvents()



class TestExtensions:
    @mark.parametrize('ext', extensions)
    def test_load(self, dashboard, ext):
        dashboard, qtbot = dashboard

        ext = dashboard.load_extension(ext)
        qtbot.addWidget(ext.parent)
        qtbot.addWidget(ext.tree)
        QtWidgets.QApplication.processEvents()
        ext.quit_fun()





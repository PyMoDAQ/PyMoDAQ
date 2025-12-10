from pymodaq_gui.utils.dock import DockArea, Dock
from pymodaq.utils.config import Config, get_set_preset_path
from pytest import fixture, mark
from pymodaq.utils import daq_utils as utils

from pymodaq.utils.conftests import qtbotskip, main_modules_skip

preset_path = get_set_preset_path()
config = Config()

@fixture
def init_qt(qtbot):
    return qtbot


class TestGeneral:
    def test_import(self, init_qt):
        qtbot = init_qt
        from qtpy import QtWidgets
        from pymodaq.dashboard import DashBoard

        win = QtWidgets.QMainWindow()
        qtbot.addWidget(win)
        area = DockArea()
        win.setCentralWidget(area)
        win.resize(1000, 500)
        win.setWindowTitle('PyMoDAQ Dashboard')

        dashboard = DashBoard(area)
        win.show()
        dashboard.preset_manager.execute_entry()

        dashboard.quit_fun()

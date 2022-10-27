import pymodaq.utils.gui_utils.dock
from pymodaq.utils.config import Config, get_set_preset_path
from pytest import fixture, mark
from pymodaq.utils import daq_utils as utils

from pymodaq.utils.conftests import qtbotskip, main_modules_skip
pytestmark = mark.skipif(qtbotskip, reason='qtbot issues but tested locally')

preset_path = get_set_preset_path()
config = Config()

@fixture
def init_qt(qtbot):
    return qtbot

@mark.skipif(main_modules_skip, reason='main module heavy qt5 testing')
class TestGeneral:
    def test_main_setfilepreset_quit(self, init_qt):
        qtbot = init_qt
        from qtpy import QtWidgets
        from pymodaq.dashboard import DashBoard
        from pymodaq.utils import gui_utils as gutils

        win = QtWidgets.QMainWindow()
        qtbot.addWidget(win)
        area = pymodaq.utils.gui_utils.dock.DockArea()
        win.setCentralWidget(area)
        win.resize(1000, 500)
        win.setWindowTitle('PyMoDAQ Dashboard')

        dashboard = DashBoard(area)
        file = preset_path.joinpath(f"{config('presets', 'default_preset_for_scan')}.xml")

        dashboard.set_preset_mode(file)

        dashboard.quit_fun()

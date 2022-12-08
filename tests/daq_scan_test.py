from pathlib import Path

import pymodaq.utils.gui_utils.dock
from pymodaq.utils.config import Config, get_set_preset_path
from pytest import fixture, mark
from pymodaq.utils.conftests import qtbotskip, main_modules_skip


pytestmark = mark.skipif(qtbotskip, reason='qtbot issues but tested locally')

preset_path = get_set_preset_path()
config = Config()



@fixture
def init_qt(qtbot):
    return qtbot

@fixture
def main(qtbot):
    from qtpy import QtWidgets
    from pymodaq.dashboard import DashBoard
    from extensions.daq_scan import DAQScan
    from pymodaq.utils import gui_utils as gutils

    win = QtWidgets.QMainWindow()
    area = pymodaq.utils.gui_utils.dock.DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    dashboard = DashBoard(area)
    file = Path(get_set_preset_path()).joinpath(f"{config('presets', 'default_preset_for_scan')}.xml")
    dashboard.set_preset_mode(file)

    winscan = QtWidgets.QMainWindow()
    areascan = pymodaq.utils.gui_utils.dock.DockArea()
    win.setCentralWidget(area)
    daq_scan = DAQScan(dockarea=areascan, dashboard=dashboard, show_popup=False)
    daq_scan.status_signal.connect(dashboard.add_status)
    winscan.show()
    qtbot.addWidget(win)
    qtbot.addWidget(winscan)
    yield dashboard, daq_scan, win
    win.close()
    winscan.close()


@mark.skipif(main_modules_skip, reason='main module heavy qt5 testing')
class TestGeneral:

    def test_main(self, main):
        dashboard, daq_scan, win = main




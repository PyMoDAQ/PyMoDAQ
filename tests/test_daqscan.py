from pathlib import Path
from pytest import fixture, approx
from pymodaq.daq_utils import daq_utils as utils
from pymodaq import daq_scan as dscan

preset_path = utils.get_set_preset_path()
config = utils.load_config()


@fixture
def init_qt(qtbot):
    return qtbot

@fixture
def main(qtbot):
    from qtpy import QtWidgets
    from pymodaq.dashboard import DashBoard
    from pymodaq.daq_scan import DAQ_Scan
    from pymodaq.daq_utils.daq_utils import get_set_preset_path
    from pymodaq.daq_utils import gui_utils as gutils

    win = QtWidgets.QMainWindow()
    area = gutils.DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    dashboard = DashBoard(area)
    file = Path(get_set_preset_path()).joinpath(f"{config['presets']['default_preset_for_scan']}.xml")
    dashboard.set_preset_mode(file)

    winscan = QtWidgets.QMainWindow()
    areascan = gutils.DockArea()
    win.setCentralWidget(area)
    daq_scan = DAQ_Scan(dockarea=areascan, dashboard=dashboard, show_popup=False)
    daq_scan.status_signal.connect(dashboard.add_status)
    winscan.show()
    qtbot.addWidget(win)
    qtbot.addWidget(winscan)
    return dashboard, daq_scan, win


class TestGeneral:

    def test_main(self, main):
        dashboard, daq_scan, win = main




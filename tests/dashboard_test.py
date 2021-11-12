from pathlib import Path
from pytest import fixture, approx, mark
from pymodaq.daq_utils import daq_utils as utils
from pymodaq import daq_scan as dscan

preset_path = utils.get_set_preset_path()
config = utils.load_config()

@fixture
def init_qt(qtbot):
    return qtbot


class TestGeneral:
    @mark.skip
    def test_main_setfilepreset_quit(self, init_qt):
        qtbot = init_qt
        from qtpy import QtWidgets
        from pymodaq.dashboard import DashBoard
        from pymodaq.daq_utils import gui_utils as gutils

        win = QtWidgets.QMainWindow()
        area = gutils.DockArea()
        win.setCentralWidget(area)
        win.resize(1000, 500)
        win.setWindowTitle('PyMoDAQ Dashboard')

        dashboard = DashBoard(area)
        file = preset_path.joinpath(f"{config['presets']['default_preset_for_scan']}.xml")

        dashboard.set_preset_mode(file)

        dashboard.quit_fun()

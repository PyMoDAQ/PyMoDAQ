from pathlib import Path
from pytest import fixture, approx

from pymodaq import daq_scan as dscan
from pymodaq.daq_utils import daq_utils as utils


preset_path = utils.get_set_preset_path()


@fixture
def init_qt(qtbot):
    return qtbot


class TestGeneral:

    def test_main(self, init_qt):
        qtbot = init_qt
        dashboard, daq_scan, win = dscan.main(False)


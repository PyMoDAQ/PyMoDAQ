from pathlib import Path
from pytest import fixture, approx

from pymodaq import dashboard as dashmod
from pymodaq.daq_utils import daq_utils as utils


preset_path = utils.get_set_preset_path()


@fixture
def init_qt(qtbot):
    return qtbot


class TestGeneral:

    def test_main_setfilepreset_quit(self, init_qt):
        qtbot = init_qt
        dashboard, win = dashmod.main(False)
        with qtbot.waitSignal(dashboard.preset_loaded_signal, timeout=20000) as blocker:
            dashboard.set_preset_mode(preset_path.joinpath('preset_default.xml'))
        assert blocker.args[0]

        dashboard.quit_fun()
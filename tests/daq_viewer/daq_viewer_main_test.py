from pymodaq.daq_viewer import daq_viewer_main as daqvm
import pytest
from pytest import fixture
from pymodaq.daq_utils.conftests import qtbotskip
pytestmark = pytest.mark.skipif(qtbotskip, reason='qtbot issues but tested locally')


@fixture
def init_qt(qtbot):
    return qtbot


class TestGeneral:

    @pytest.mark.parametrize('daq_type', ['DAQ0D', 'DAQ1D', 'DAQ2D'])
    def test_main_set_daqtype_init_snap_desinit_quit(self, init_qt, daq_type):
        qtbot = init_qt
        viewer, win = daqvm.main(False)
        qtbot.addWidget(win)
        viewer.daq_type = daq_type
        with qtbot.waitSignal(viewer.init_signal) as blocker:
            viewer.init_det()
        assert blocker.args[0]

        with qtbot.waitSignal(viewer.grab_done_signal) as blocker:
            viewer.snap()

        with qtbot.waitSignal(viewer.init_signal) as blocker:
            viewer.init_det()
        assert not blocker.args[0]

        with qtbot.waitSignal(viewer.quit_signal) as blocker:
            viewer.quit_fun()

        win.close()



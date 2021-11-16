from pymodaq.daq_move import daq_move_main as daqmm
from pytest import fixture, approx


@fixture
def init_qt(qtbot):
    return qtbot


class TestGeneral:

    def test_main_set_daqtype_init_snap_desinit_quit(self, init_qt):
        qtbot = init_qt
        mover, win = daqmm.main(False)
        qtbot.addWidget(win)
        with qtbot.waitSignal(mover.init_signal) as blocker:
            mover.init()
        assert blocker.args[0]
        MOVETITLE = 'mymover'
        MOVETARGET = 257
        mover.title = MOVETITLE
        mover.ui.Abs_position_sb.setValue(MOVETARGET)
        with qtbot.waitSignal(mover.move_done_signal) as blocker:
            mover.ui.Move_Abs_pb.click()

        assert blocker.args[0] == MOVETITLE
        assert blocker.args[1] == MOVETARGET
        win.close()


from collections import OrderedDict

from qtpy import QtWidgets, QtCore
import numpy as np
import pytest

from pymodaq.utils.math_utils import gauss1D
from pymodaq.utils.plotting.data_viewers.viewer0D import Viewer0D
from pymodaq.utils import data as data_mod
from pymodaq.utils.conftests import qtbotskip

pytestmark = pytest.mark.skipif(qtbotskip, reason='qtbot issues but tested locally')

@pytest.fixture
def init_viewer0d(qtbot):
    form = QtWidgets.QWidget()
    prog = Viewer0D(form)
    form.show()
    qtbot.addWidget(form)
    yield prog, qtbot
    form.close()


class Data0D:
    num = 0

    def __init__(self, Npts=11):
        self.x = np.linspace(0, 200, Npts)
        self.y1 = gauss1D(self.x, 75, 25)
        self.y2 = gauss1D(self.x, 120, 50, 2)

    def __iter__(self):
        return iter([data_mod.DataRaw('data0D',
                                      data=[np.array((self.y1[ind],)), np.array((self.y2[ind],))])
                     for ind in range(len(self.x))])

    def __next__(self):
        if self.num > len(self.x):
            raise StopIteration
        else:
            self.num += 1
            return self.num - 1


class TestViewer0D:
    def test_init(self, init_viewer0d):
        prog, qtbot = init_viewer0d
        assert isinstance(prog, Viewer0D)
        assert isinstance(prog.parent, QtWidgets.QWidget)
        assert prog.title == 'Viewer0D'
        
        prog = Viewer0D(None)
        assert isinstance(prog.parent, QtWidgets.QWidget)

    def test_actions(self, init_viewer0d):
        prog, qtbot = init_viewer0d
        for action_name in ['clear', 'Nhistory', 'show_data_as_list']:
            assert prog.view.has_action(action_name)

    def test_clear_action(self, init_viewer0d):
        prog, qtbot = init_viewer0d

        for data in Data0D():
            prog.show_data(data)
            QtWidgets.QApplication.processEvents()

        assert prog.view.data_displayer.axis.size != 0

        prog.view.get_action('clear').trigger()

        assert prog.view.data_displayer.axis.size == 0

    def test_show_datalist(self, init_viewer0d):
        prog, qtbot = init_viewer0d

        prog.parent.show()

        prog.view.get_action('show_data_as_list').trigger()
        assert prog.view.values_list.isVisible()
        prog.view.get_action('show_data_as_list').trigger()
        assert not prog.view.values_list.isVisible()
        
    def test_clear_data(self, init_viewer0d):
        prog, qtbot = init_viewer0d

        for data in Data0D():
            prog.show_data(data)
            QtWidgets.QApplication.processEvents()
        
        assert prog.view.data_displayer.axis.size != 0
        prog.view.data_displayer.clear_data()
        assert prog.view.data_displayer.axis.size == 0


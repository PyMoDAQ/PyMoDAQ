from collections import OrderedDict

from qtpy import QtWidgets, QtCore
import numpy as np
import pytest

from pymodaq_utils.math_utils import gauss1D
from pymodaq_gui.plotting.data_viewers.viewer0D import Viewer0D
from pymodaq_data import data as data_mod


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
        prog.parent.deleteLater()

    def test_actions(self, init_viewer0d):
        prog, qtbot = init_viewer0d
        for action_name in ['clear', 'Nhistory', 'show_data_as_list', 'show_min_max', 'sync_x_axis']:
            assert prog.view.has_action(action_name)
        prog.parent.deleteLater()

    def test_sync_x_axis_on_by_default(self, init_viewer0d):
        """sync_x_axis action is checked by default and Data0DWithHistory reflects it."""
        prog, qtbot = init_viewer0d
        assert prog.view.is_action_checked('sync_x_axis')
        assert prog.view.data_displayer._data.sync_x_axis
        prog.parent.deleteLater()

    def test_sync_x_axis_on_resets_history_on_new_label(self, init_viewer0d):
        """With sync ON, adding a new channel resets all histories so curves share the same x-origin."""
        prog, qtbot = init_viewer0d
        displayer = prog.view.data_displayer
        N = 5
        for _ in range(N):
            prog.show_data(data_mod.DataRaw('data0D',
                                            data=[np.array([1.0]), np.array([2.0])],
                                            labels=['ch1', 'ch2']))
        assert displayer._data.size == N

        prog.show_data(data_mod.DataRaw('data0D',
                                        data=[np.array([1.0]), np.array([2.0]), np.array([3.0])],
                                        labels=['ch1', 'ch2', 'ch3']))
        assert displayer._data.size == 1  # history was reset
        prog.parent.deleteLater()

    def test_sync_x_axis_off_preserves_history_on_new_label(self, init_viewer0d):
        """With sync OFF, existing channels keep their history; the new channel is NaN-padded."""
        prog, qtbot = init_viewer0d
        displayer = prog.view.data_displayer
        # toggle action off (it starts checked → trigger unchecks it)
        prog.view.get_action('sync_x_axis').trigger()
        assert not displayer._data.sync_x_axis

        N = 5
        for _ in range(N):
            prog.show_data(data_mod.DataRaw('data0D',
                                            data=[np.array([1.0]), np.array([2.0])],
                                            labels=['ch1', 'ch2']))
        assert displayer._data.size == N

        prog.show_data(data_mod.DataRaw('data0D',
                                        data=[np.array([1.0]), np.array([2.0]), np.array([3.0])],
                                        labels=['ch1', 'ch2', 'ch3']))
        assert displayer._data.size == N + 1
        assert np.sum(np.isnan(displayer._data.data['ch3'])) == N  # first N entries are NaN
        prog.parent.deleteLater()

    def test_smart_diff_preserves_unchanged_plot_items(self, init_viewer0d):
        """update_display_items only adds/removes changed labels; untouched items are the same object."""
        prog, qtbot = init_viewer0d
        displayer = prog.view.data_displayer

        prog.show_data(data_mod.DataRaw('data0D',
                                        data=[np.array([1.0]), np.array([2.0])],
                                        labels=['ch1', 'ch2']))
        assert set(displayer._plot_items.keys()) == {'ch1', 'ch2'}
        old_ch1_item = displayer._plot_items['ch1']

        # Replace ch2 with ch3 — ch1 should survive untouched
        prog.show_data(data_mod.DataRaw('data0D',
                                        data=[np.array([1.0]), np.array([3.0])],
                                        labels=['ch1', 'ch3']))
        assert set(displayer._plot_items.keys()) == {'ch1', 'ch3'}
        assert displayer._plot_items['ch1'] is old_ch1_item
        prog.parent.deleteLater()

    def test_update_colors_no_rebuild(self, init_viewer0d):
        """update_colors updates pens in-place without removing/re-adding plot items."""
        prog, qtbot = init_viewer0d
        displayer = prog.view.data_displayer

        prog.show_data(data_mod.DataRaw('data0D', data=[np.array([1.0])], labels=['ch1']))
        old_item = displayer._plot_items['ch1']

        from pymodaq_data.plotting.utils import PlotColors
        new_colors = [dict(color=color) for color in PlotColors()]
        displayer.update_colors(new_colors)

        assert displayer._plot_items['ch1'] is old_item
        prog.parent.deleteLater()

    def test_clear_action(self, init_viewer0d):
        prog, qtbot = init_viewer0d

        for data in Data0D():
            prog.show_data(data)
            QtWidgets.QApplication.processEvents()

        assert prog.view.data_displayer.axis.size != 0

        prog.view.get_action('clear').trigger()

        assert prog.view.data_displayer.axis.size == 0
        prog.parent.deleteLater()
    def test_show_datalist(self, init_viewer0d):
        prog, qtbot = init_viewer0d

        prog.parent.show()

        prog.view.get_action('show_data_as_list').trigger()
        assert prog.view.values_list.isVisible()
        prog.view.get_action('show_data_as_list').trigger()
        assert not prog.view.values_list.isVisible()
        prog.parent.deleteLater()

    def test_clear_data(self, init_viewer0d):
        prog, qtbot = init_viewer0d

        for data in Data0D():
            prog.show_data(data)
            QtWidgets.QApplication.processEvents()
        
        assert prog.view.data_displayer.axis.size != 0
        prog.view.data_displayer.clear_data()
        assert prog.view.data_displayer.axis.size == 0
        prog.parent.deleteLater()

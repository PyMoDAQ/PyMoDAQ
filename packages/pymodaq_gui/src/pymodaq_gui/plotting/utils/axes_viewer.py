# -*- coding: utf-8 -*-
"""
Created the 26/01/2023

@author: Sebastien Weber
"""
from typing import List

from qtpy import QtWidgets, QtCore

from pymodaq_gui.plotting.data_viewers.viewer1Dbasic import Viewer1DBasic
from pymodaq_data.data import Axis
from pymodaq_utils.math_utils import find_index


class AxesViewer(QtCore.QObject):
    navigation_changed = QtCore.Signal()

    def __init__(self, parent_widget: QtWidgets.QWidget):
        super().__init__()
        self._axes: List[Axis]
        self.parent = parent_widget
        self.parent.setLayout(QtWidgets.QVBoxLayout())
        self.nav_axes_viewers: List[Viewer1DBasic] = []

    def clear_viewers(self):
        while len(self.nav_axes_viewers) != 0:
            viewer = self.nav_axes_viewers.pop(0)
            self.parent.layout().removeWidget(viewer.parent)
            viewer.parent.close()

    def add_viewers(self, nviewers: int):
        widgets = []
        for ind in range(nviewers):
            widgets.append(QtWidgets.QWidget())
            self.parent.layout().addWidget(widgets[-1])
            self.nav_axes_viewers.append(Viewer1DBasic(widgets[-1], show_line=True))

    def set_nav_viewers(self, axes: List[Axis]):
        self._axes = axes
        if len(self.nav_axes_viewers) != len(axes):
            self.clear_viewers()
            self.add_viewers(len(axes))

        for ind in range(len(axes)):
            self.nav_axes_viewers[ind].roi_line_signal.connect(self._emit_nav_signal)
            self.nav_axes_viewers[ind].show_data([axes[ind].get_data()])
            self.nav_axes_viewers[ind].set_axis_label(dict(orientation='bottom',
                                                           label='Scan index',
                                                           units=''))
            self.nav_axes_viewers[ind].set_axis_label(dict(orientation='left',
                                                           label=axes[ind].label,
                                                           units=axes[ind].units))

    def _emit_nav_signal(self):
        self.navigation_changed.emit()

    def get_crosshairs(self):
        return tuple([viewer.get_line_position() for viewer in self.nav_axes_viewers])

    def get_indexes(self):
        return [int(cross) for cross in self.get_crosshairs()]

    def setVisible(self, show=True):
        """convenience method to show or hide the paretn widget"""
        self.parent.setVisible(show)


if __name__ == '__main__':
    import sys
    import numpy as np
    app = QtWidgets.QApplication(sys.argv)

    widget = QtWidgets.QWidget()
    prog = AxesViewer(widget)
    widget.show()
    labels = ['']
    N = 2
    axes = [Axis(label=f'Axis{ind:02d}', units='s', data=np.random.rand(50)) for ind in range(N)]
    prog.set_nav_viewers(axes)

    def print_positions():
        print(prog.get_crosshairs())

    prog.navigation_changed.connect(print_positions)

    sys.exit(app.exec_())


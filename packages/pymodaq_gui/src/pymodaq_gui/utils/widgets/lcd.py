from typing import List, Sequence

import numpy as np

from qtpy import QtWidgets
from qtpy.QtCore import QObject, QThread
from pymodaq_gui.plotting.data_viewers.viewer0D import Viewer0D
from pymodaq_data.data import DataRaw
import sys


class LCD(QObject):

    def __init__(self, parent: QtWidgets.QWidget,
                 Nvals=0, labels: Sequence[str] = None,
                 digits=3, show_graph=True, **kwargs):
        super().__init__()
        self.Nvals = Nvals
        self.labels = labels if labels is not None else ['CH{:d}'.format(ind) for ind in range(self.Nvals)]
        self.parent = parent
        self.viewer0D = None
        self.digits = digits
        self.show_graph = show_graph
        self.setupui()

        self.viewer_widget.setVisible(self.show_graph)

    def setvalues(self, values: List[np.ndarray], show_graph: bool = None):
        """
        display values on lcds
        Parameters
        ----------
        values: list of 0D ndarray
        show_graph: bool
            set the graph visibility

        Returns
        -------

        """
        if show_graph is None:
            show_graph = self.show_graph
        while len(values) < self.Nvals:
            values.append(np.array([0.]))
        if len(values) > self.Nvals:
            values = values[:self.Nvals]
        vals = []
        for ind, val in enumerate(values):
            self.lcds[ind].display(val[0])
            vals.append(val)
        self.viewer_widget.setVisible(show_graph)
        if show_graph:
            self.viewer0D.show_data(DataRaw(name='LCD', data=values))

    def setupui(self):

        while len(self.labels) < self.Nvals:
            self.labels.append('')

        vlayout = QtWidgets.QVBoxLayout()
        hsplitter = QtWidgets.QSplitter()
        vlayout.addWidget(hsplitter)
        self.parent.setLayout(vlayout)
        self.viewer_widget = QtWidgets.QWidget()
        self.viewer0D = Viewer0D(self.viewer_widget)
        self.viewer0D.labels = self.labels

        vlayout = QtWidgets.QVBoxLayout()

        lcd_layouts = []
        labels = []
        self.lcds = []

        for ind in range(self.Nvals):
            lcd_layouts.append(QtWidgets.QVBoxLayout())
            labels.append(QtWidgets.QLabel(self.labels[ind]))
            labels[-1].setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
            self.lcds.append(QtWidgets.QLCDNumber())
            self.lcds[-1].setDigitCount(self.digits)
            lcd_layouts[-1].addWidget(labels[-1])
            lcd_layouts[-1].addWidget(self.lcds[-1])
            vlayout.addLayout(lcd_layouts[-1])

            if ind != self.Nvals - 1:
                hFrame = QtWidgets.QFrame()
                hFrame.setFrameShape(QtWidgets.QFrame.HLine)
                vlayout.addWidget(hFrame)

        lcd_widget = QtWidgets.QWidget()
        lcd_widget.setLayout(vlayout)
        hsplitter.addWidget(lcd_widget)
        hsplitter.addWidget(self.viewer_widget)
        self.parent.resize(800, 500)
        hsplitter.setSizes([400, 300])


if __name__ == '__main__':
    from pymodaq_utils.math_utils import gauss1D
    import numpy as np

    x = np.linspace(0, 200, 201)
    y1 = 100 * gauss1D(x, 75, 100)
    y2 = gauss1D(x, 120, 100, 2)
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()

    prog = LCD(widget, Nvals=2, show_graph=False)
    widget.show()
    for ind in range(len(x)):
        prog.setvalues([np.atleast_1d(y1[ind]),
                        np.atleast_1d(y2[ind])])
        QtWidgets.QApplication.processEvents()
        QThread.msleep(100)
    sys.exit(app.exec())


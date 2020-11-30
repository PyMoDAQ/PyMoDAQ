from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject
from pymodaq.daq_utils.plotting.viewer0D.viewer0D_main import Viewer0D
import sys
import numpy as np

class LCD(QObject):

    def __init__(self, parent, **kwargs):
        super(LCD, self).__init__()
        self.Nvals = None
        self.labels = None
        self.parent = parent
        self.viewer0D = None
        self.digits = 3
        self.setupui(**kwargs)

    def setvalues(self, values):
        """
        display values on lcds
        Parameters
        ----------
        values: list of list of numerical values (int or float)

        Returns
        -------

        """
        while len(values) < self.Nvals:
            values.append(np.array([0.]))
        if len(values) > self.Nvals:
            values = values[:self.Nvals]
        vals = []
        for ind, val in enumerate(values):
            self.lcds[ind].display(val[0])
            vals.append(val)
        self.viewer0D.show_data(vals)

    def setupui(self, **kwargs):
        if 'digits' in kwargs:
            self.digits = kwargs['digits']
        if 'Nvals' in kwargs:
            self.Nvals = kwargs['Nvals']
        else:
            self.Nvals = 1
        if 'labels' in kwargs:
            self.labels = kwargs['labels']
        else:
            self.labels = ['CH{:d}'.format(ind) for ind in range(self.Nvals)]

        while len(self.labels) < self.Nvals:
            self.labels.append('')

        vlayout = QtWidgets.QVBoxLayout()
        hsplitter = QtWidgets.QSplitter()
        vlayout.addWidget(hsplitter)
        self.parent.setLayout(vlayout)
        form = QtWidgets.QWidget()
        self.viewer0D = Viewer0D(form)
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
        hsplitter.addWidget(form)
        self.parent.resize(800, 500)
        hsplitter.setSizes([400, 300])


if __name__ == '__main__':
    from pymodaq.daq_utils.daq_utils import gauss1D
    import numpy as np

    x = np.linspace(0, 200, 201)
    y1 = gauss1D(x, 75, 25)
    y2 = gauss1D(x, 120, 50, 2)
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()

    prog = LCD(Form, Nvals=2)
    Form.show()
    for ind, data in enumerate(y1):
        prog.setvalues([data])
        QtWidgets.QApplication.processEvents()
    sys.exit(app.exec_())

import numpy
import numpy as np
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QObject, pyqtSignal
from pyqtgraph import LinearRegionItem

from pymodaq.daq_utils.daq_utils import ftAxis_time, ft, find_index, gauss1D, ift, set_logger, get_module_name
from pymodaq.daq_utils.plotting.viewer1D.viewer1Dbasic import Viewer1DBasic

logger = set_logger(get_module_name(__file__))


class FourierFilterer(QObject):
    filter_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(FourierFilterer, self).__init__()
        if parent is None:
            parent = QtWidgets.QWidget()

        self.parent = parent

        self.raw_data = None
        self.data = None
        self.data_fft = None
        self.filter = None
        self.xaxis = None
        self.yaxis = None
        self.xaxisft = None
        self.yaxisft = None

        self.frequency = 0
        self.phase = 0

        self.c = None
        self.viewer2D = None
        self.setUI()

    def setUI(self):
        self.vlayout = QtWidgets.QVBoxLayout()
        self.parent.setLayout(self.vlayout)

        form = QtWidgets.QWidget()
        self.viewer1D = Viewer1DBasic(form)
        self.vlayout.addWidget(form)
        self.fftbutton1D = QtWidgets.QPushButton()
        self.fftbutton1D.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/FFT.png"), QtGui.QIcon.Normal,
                       QtGui.QIcon.Off)
        self.fftbutton1D.setIcon(icon)
        self.fftbutton1D.setCheckable(True)
        self.fftbutton1D.clicked.connect(self.update_plot)

        vbox = self.viewer1D.parent.layout()
        widg = QtWidgets.QWidget()
        hbox = QtWidgets.QHBoxLayout()
        widg.setLayout(hbox)
        vbox.insertWidget(0, widg)
        hbox.addWidget(self.fftbutton1D)
        hbox.addStretch()

        self.viewer1D.ROI = LinearRegionItem(values=[0, 100])
        self.viewer1D.plotwidget.plotItem.addItem(self.viewer1D.ROI)
        self.data_filtered_plot = self.viewer1D.plotwidget.plotItem.plot()
        self.data_filtered_plot.setPen('w')
        self.viewer1D.ROI.sigRegionChangeFinished.connect(self.set_data)

        self.viewer1D.ROIfft = LinearRegionItem()
        self.viewer1D.plotwidget.plotItem.addItem(self.viewer1D.ROIfft)
        self.viewer1D.ROIfft.sigRegionChangeFinished.connect(self.update_filter)

        self.parent.show()

    def calculate_fft(self):

        ftaxis, axis = ftAxis_time(len(self.xaxis), np.max(self.xaxis) - np.min(self.xaxis))
        self.xaxisft = ftaxis / (2 * np.pi)
        self.data_fft = ft(self.data)

    def show_data(self, data):
        """
        show data and fft
        Parameters
        ----------
        data: (dict) with keys 'data', optionally 'xaxis' and 'yaxis'
        """
        try:
            self.raw_data = data

            if 'xaxis' in data:
                self.xaxis = data['xaxis']
            else:
                self.xaxis = np.arange(0, data['data'].shape[0], 1)
                self.raw_data['xaxis'] = self.xaxis
            # self.viewer1D.ROI.setRegion((np.min(self.xaxis), np.max(self.xaxis)))
            self.set_data()
        except Exception as e:
            logger.exception(str(e))

    def set_data(self):
        xlimits = self.viewer1D.ROI.getRegion()
        indexes = find_index(self.raw_data['xaxis'], xlimits)
        self.data = self.raw_data['data'][indexes[0][0]:indexes[1][0]]
        self.xaxis = self.raw_data['xaxis'][indexes[0][0]:indexes[1][0]]
        try:
            self.calculate_fft()
        except Exception as e:
            logger.exception(str(e))
        self.viewer1D.x_axis = self.xaxis
        self.update_plot()

    def update_filter(self):
        try:
            xmin, xmax = self.viewer1D.ROIfft.getRegion()
            self.filter = gauss1D(self.xaxisft, np.mean([xmin, xmax]), xmax - xmin)
            self.data = np.real(ift(self.filter * self.data_fft))
            index = np.argmax(self.filter * self.data_fft)
            self.frequency = self.xaxisft[index]
            self.phase = np.angle(self.data_fft[index])

            self.filter_changed.emit(dict(frequency=self.frequency, phase=self.phase))
            self.update_plot()
        except Exception as e:
            logger.exception(str(e))

    def update_plot(self):

        if self.fftbutton1D.isChecked():
            if self.data_fft is not None:
                if self.filter is not None:
                    self.viewer1D.show_data([np.abs(self.data_fft), np.max(np.abs(self.data_fft)) * self.filter])
                else:
                    self.viewer1D.show_data([np.abs(self.data_fft)])
                self.viewer1D.x_axis = dict(data=self.xaxisft, label='freq.')
                self.viewer1D.ROIfft.setVisible(True)
                self.viewer1D.ROI.setVisible(False)
                self.data_filtered_plot.setVisible(False)
        else:
            if self.raw_data is not None:
                self.viewer1D.show_data([self.raw_data['data']])
                self.viewer1D.x_axis = dict(data=self.raw_data['xaxis'], label='Pxls')
                self.data_filtered_plot.setData(self.xaxis, self.data)
                self.data_filtered_plot.setVisible(True)
                self.viewer1D.ROIfft.setVisible(False)
                self.viewer1D.ROI.setVisible(True)


class LSqEllipse:

    def fit(self, data):
        """Lest Squares fitting algorithm

        Theory taken from (*)
        Solving equation Sa=lCa. with a = |a b c d f g> and a1 = |a b c>
            a2 = |d f g>

        Args
        ----
        data (list:list:float): list of two lists containing the x and y data of the
            ellipse. of the form [[x1, x2, ..., xi],[y1, y2, ..., yi]]

        Returns
        ------
        coef (list): list of the coefficients describing an ellipse
           [a,b,c,d,f,g] corresponding to ax**2+2bxy+cy**2+2dx+2fy+g
        """
        x, y = numpy.asarray(data, dtype=float)

        # Quadratic part of design matrix [eqn. 15] from (*)
        D1 = numpy.mat(numpy.vstack([x ** 2, x * y, y ** 2])).T
        # Linear part of design matrix [eqn. 16] from (*)
        D2 = numpy.mat(numpy.vstack([x, y, numpy.ones(len(x))])).T

        # forming scatter matrix [eqn. 17] from (*)
        S1 = D1.T * D1
        S2 = D1.T * D2
        S3 = D2.T * D2

        # Constraint matrix [eqn. 18]
        C1 = numpy.mat('0. 0. 2.; 0. -1. 0.; 2. 0. 0.')

        # Reduced scatter matrix [eqn. 29]
        M = C1.I * (S1 - S2 * S3.I * S2.T)

        # M*|a b c >=l|a b c >. Find eigenvalues and eigenvectors from this equation [eqn. 28]
        eval, evec = numpy.linalg.eig(M)

        # eigenvector must meet constraint 4ac - b^2 to be valid.
        cond = 4 * numpy.multiply(evec[0, :], evec[2, :]) - numpy.power(evec[1, :], 2)
        a1 = evec[:, numpy.nonzero(cond.A > 0)[1]]

        # |d f g> = -S3^(-1)*S2^(T)*|a b c> [eqn. 24]
        a2 = -S3.I * S2.T * a1

        # eigenvectors |a b c d f g>
        self.coef = numpy.vstack([a1, a2])
        self._save_parameters()

    def _save_parameters(self):
        """finds the important parameters of the fitted ellipse

        Theory taken form http://mathworld.wolfram

        Args
        -----
        coef (list): list of the coefficients describing an ellipse
           [a,b,c,d,f,g] corresponding to ax**2+2bxy+cy**2+2dx+2fy+g

        Returns
        _______
        center (List): of the form [x0, y0]
        width (float): major axis
        height (float): minor axis
        phi (float): rotation of major axis form the x-axis in radians
        """

        # eigenvectors are the coefficients of an ellipse in general form
        # a*x^2 + 2*b*x*y + c*y^2 + 2*d*x + 2*f*y + g = 0 [eqn. 15) from (**) or (***)
        a = self.coef[0, 0]
        b = self.coef[1, 0] / 2.
        c = self.coef[2, 0]
        d = self.coef[3, 0] / 2.
        f = self.coef[4, 0] / 2.
        g = self.coef[5, 0]

        # finding center of ellipse [eqn.19 and 20] from (**)
        x0 = (c * d - b * f) / (b ** 2. - a * c)
        y0 = (a * f - b * d) / (b ** 2. - a * c)

        # Find the semi-axes lengths [eqn. 21 and 22] from (**)
        numerator = 2 * (a * f * f + c * d * d + g * b * b - 2 * b * d * f - a * c * g)
        denominator1 = (b * b - a * c) * ((c - a) * numpy.sqrt(1 + 4 * b * b / ((a - c) * (a - c))) - (c + a))
        denominator2 = (b * b - a * c) * ((a - c) * numpy.sqrt(1 + 4 * b * b / ((a - c) * (a - c))) - (c + a))
        width = numpy.sqrt(numerator / denominator1)
        height = numpy.sqrt(numerator / denominator2)

        # angle of counterclockwise rotation of major-axis of ellipse to x-axis [eqn. 23] from (**)
        # or [eqn. 26] from (***).
        phi = .5 * numpy.arctan((2. * b) / (a - c))

        self._center = [x0, y0]
        self._width = width
        self._height = height
        self._phi = phi

    @property
    def center(self):
        return self._center

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def phi(self):
        """angle of counterclockwise rotation of major-axis of ellipse to x-axis
        [eqn. 23] from (**)
        """
        return self._phi

    def parameters(self):
        return self.center, self.width, self.height, self.phi


def make_test_ellipse(center=[1, 1], width=1, height=.6, phi=3.14 / 5):
    """Generate Elliptical data with noise

    Args
    ----
    center (list:float): (<x_location>, <y_location>)
    width (float): semimajor axis. Horizontal dimension of the ellipse (**)
    height (float): semiminor axis. Vertical dimension of the ellipse (**)
    phi (float:radians): tilt of the ellipse, the angle the semimajor axis
        makes with the x-axis

    Returns
    -------
    data (list:list:float): list of two lists containing the x and y data of the
        ellipse. of the form [[x1, x2, ..., xi],[y1, y2, ..., yi]]
    """
    t = numpy.linspace(0, 2 * numpy.pi, 1000)
    x_noise, y_noise = numpy.random.rand(2, len(t))

    ellipse_x = center[0] + width * numpy.cos(t) * numpy.cos(phi) - height * numpy.sin(t) * numpy.sin(
        phi) + x_noise / 2.
    ellipse_y = center[1] + width * numpy.cos(t) * numpy.sin(phi) + height * numpy.sin(t) * numpy.cos(
        phi) + y_noise / 2.

    return [ellipse_x, ellipse_y]


if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    prog = FourierFilterer()

    from pymodaq.daq_utils.daq_utils import gauss1D

    xdata = np.linspace(0, 400, 401)
    x0 = 50
    dx = 20
    tau = 27
    tau2 = 100
    ydata_gauss = 10 * gauss1D(xdata, x0, dx) + np.random.rand(len(xdata))
    ydata_expodec = np.zeros((len(xdata)))
    ydata_expodec[:50] = 10 * gauss1D(xdata[:50], x0, dx, 2)
    ydata_expodec[50:] = 10 * np.exp(-(xdata[50:] - x0) / tau)  # +10*np.exp(-(xdata[50:]-x0)/tau2)
    ydata_expodec += 2 * np.random.rand(len(xdata))
    ydata_sin = 10 + 2 * np.sin(2 * np.pi * 0.1 * xdata - np.deg2rad(55)) + np.sin(
        2 * np.pi * 0.008 * xdata - np.deg2rad(-10)) + 2 * np.random.rand(len(xdata))

    prog.show_data(dict(data=ydata_sin, xaxis=xdata))
    sys.exit(app.exec_())

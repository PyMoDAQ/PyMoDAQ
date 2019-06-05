from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize, QByteArray, QBuffer


from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree
from pymodaq.QtDesigner_Ressources import QtDesigner_ressources_rc
from pyqtgraph.graphicsItems.LinearRegionItem import LinearRegionItem
from scipy.signal import find_peaks
import sys
import tables
import numpy as np
from pymodaq.daq_utils.plotting.viewer1D.viewer1Dbasic import Viewer1DBasic
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D
from pymodaq.daq_utils.daq_utils import ft, ft2, ftAxis, ift, ift2, ftAxis_time, gauss2D, gauss1D, find_index
from collections import OrderedDict

import warnings
import os

class FourierFilterer(QObject):
    filter_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(FourierFilterer,self).__init__()
        if parent is None:
            parent = QtWidgets.QWidget()

        self.parent = parent

        self.raw_data =None
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

        self.viewer1D.ROI = LinearRegionItem(values=[0,100])
        self.viewer1D.plotwidget.plotItem.addItem(self.viewer1D.ROI)
        self.data_filtered_plot = self.viewer1D.plotwidget.plotItem.plot()
        self.data_filtered_plot.setPen('w')
        self.viewer1D.ROI.sigRegionChangeFinished.connect(self.set_data)

        self.viewer1D.ROIfft = LinearRegionItem()
        self.viewer1D.plotwidget.plotItem.addItem(self.viewer1D.ROIfft)
        self.viewer1D.ROIfft.sigRegionChangeFinished.connect(self.update_filter)

        self.parent.show()


    def calculate_fft(self):

        ftaxis, axis = ftAxis_time(len(self.xaxis), np.max(self.xaxis)-np.min(self.xaxis))
        self.xaxisft = ftaxis/(2*np.pi)
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
        except:
            pass

    def set_data(self):
        xlimits = self.viewer1D.ROI.getRegion()
        indexes = find_index(self.raw_data['xaxis'], xlimits)
        self.data = self.raw_data['data'][indexes[0][0]:indexes[1][0]]
        self.xaxis = self.raw_data['xaxis'][indexes[0][0]:indexes[1][0]]
        try:
            self.calculate_fft()
        except:
            pass
        self.viewer1D.x_axis = self.xaxis
        self.update_plot()

    def update_filter(self):
        try:
            xmin, xmax = self.viewer1D.ROIfft.getRegion()
            self.filter = gauss1D(self.xaxisft, np.mean([xmin,xmax]),xmax-xmin)
            self.data =np.real(ift(self.filter * self.data_fft))
            index = np.argmax(self.filter * self.data_fft)
            self.frequency = self.xaxisft[index]
            self.phase = np.angle(self.data_fft[index])

            self.filter_changed.emit(dict(frequency=self.frequency, phase=self.phase))
            self.update_plot()
        except:
            pass

    def update_plot(self):

        if self.fftbutton1D.isChecked():
            if self.data_fft is not None:
                if self.filter is not None:
                    self.viewer1D.show_data([np.abs(self.data_fft), np.max(np.abs(self.data_fft)) * self.filter])
                else:
                    self.viewer1D.show_data([np.abs(self.data_fft)])
                self.viewer1D.x_axis = dict(data=self.xaxisft, label ='freq.')
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


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv);
    prog = FourierFilterer()

    from pymodaq.daq_utils.daq_utils import gauss1D, gauss2D
    xdata=np.linspace(0,400,401)
    x0=50
    dx=20
    tau = 27
    tau2=100
    ydata_gauss=10*gauss1D(xdata,x0,dx)+np.random.rand(len(xdata))
    ydata_expodec = np.zeros((len(xdata)))
    ydata_expodec[:50] = 10*gauss1D(xdata[:50],x0,dx,2)
    ydata_expodec[50:] = 10*np.exp(-(xdata[50:]-x0)/tau)#+10*np.exp(-(xdata[50:]-x0)/tau2)
    ydata_expodec += 2*np.random.rand(len(xdata))
    ydata_sin =10+2*np.sin(2*np.pi*0.1*xdata-np.deg2rad(55))+np.sin(2*np.pi*0.008*xdata-np.deg2rad(-10))+2*np.random.rand(len(xdata))

    prog.show_data(dict(data=ydata_sin, xaxis=xdata))
    sys.exit(app.exec_())

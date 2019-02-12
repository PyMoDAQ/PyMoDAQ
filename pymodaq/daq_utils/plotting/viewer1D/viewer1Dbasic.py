from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize
import sys
import pyqtgraph as pg
import numpy as np
from pymodaq.daq_utils import daq_utils as utils



class Viewer1DBasic(QtWidgets.QWidget,QObject):
    """this plots 1D data on a plotwidget. one linear region to select data
    """
    def __init__(self,parent=None):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(Viewer1DBasic, self).__init__()
        if parent is None:
            parent = QtWidgets.QWidget()
            parent.show()

        self.parent = parent

        self.plot_colors = utils.plot_colors

        self.data_to_export = None
        self.datas = None
        self._x_axis = None

        self.labels = []
        self.plot_channels = None
        self.legend = None
        self.setup_ui()

    def setup_ui(self):
        vboxlayout = QtWidgets.QVBoxLayout()
        self.plotwidget = pg.PlotWidget()
        self.parent.setLayout(vboxlayout)
        vboxlayout.addWidget(self.plotwidget)

        self.legend = self.plotwidget.addLegend()

    @pyqtSlot(list)
    def show_data(self, datas):
        if datas is not None:
            self.datas = datas

            if self.labels == [] or len(self.labels) != len(datas):
                self._labels = ["CH{}".format(ind) for ind in range(len(datas))]

            if self.plot_channels == None: #initialize data and plots
                self.ini_data_plots(len(datas))
            elif len(self.plot_channels) != len(datas):
                self.remove_plots()
                self.ini_data_plots(len(datas))

            for ind_plot, data in enumerate(datas):
                if self._x_axis is None or len(self._x_axis) != len(data):
                    self._x_axis = np.linspace(0,len(data), len(data), endpoint=False)

                self.plot_channels[ind_plot].setData(x=self._x_axis, y=data)

    def ini_data_plots(self, Nplots):
        self.plot_channels=[]

        channels = []
        for ind in range(Nplots):
            channel=self.plotwidget.plot()
            channel.setPen(self.plot_colors[ind])
            self.legend.addItem(channel, self._labels[ind])
            channels.append(ind)
            self.plot_channels.append(channel)

    def remove_plots(self):
        if self.plot_channels is not None:
            for channel in self.plot_channels:
                self.plotwidget.removeItem(channel)
            self.plot_channels = None
        if self.legend is not None:
            items = [item[1].text for item in self.legend.items]
            for item in items:
                self.legend.removeItem(item)

    def set_axis_label(self,axis_settings=dict(orientation='bottom', label='x axis', units='pxls')):
        axis = self.plotwidget.plotItem.getAxis(axis_settings['orientation'])
        axis.setLabel(text=axis_settings['label'], units=axis_settings['units'])

    @property
    def x_axis(self):
        return self._x_axis

    @x_axis.setter
    def x_axis(self, x_axis):
        label = 'Pxls'
        units = ''
        if isinstance(x_axis, dict):
            if 'data' in x_axis:
                xdata = x_axis['data']
            if 'label' in x_axis:
                label = x_axis['label']
            if 'units' in x_axis:
                units = x_axis['units']
        else:
            xdata = x_axis
        self._x_axis = xdata
        self.show_data(self.datas)
        self.set_axis_label(dict(orientation='bottom',label=label,units=units))



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    Form=QtWidgets.QWidget()
    prog = Viewer1DBasic(Form)

    from pymodaq.daq_utils.daq_utils import gauss1D
    x=np.linspace(0,200,201)
    y1=gauss1D(x,75,25)
    y2=gauss1D(x,120,50,2)
    tau_half = 27
    tau2=100
    x0=50
    dx=20
    ydata_expodec = np.zeros((len(x)))
    ydata_expodec[:50] = 1*gauss1D(x[:50],x0,dx,2)
    ydata_expodec[50:] = 1*np.exp(-(x[50:]-x0)/(tau_half/np.log(2)))#+1*np.exp(-(x[50:]-x0)/tau2)
    ydata_expodec += 0.1*np.random.rand(len(x))

    prog.show_data([y1, y2, ydata_expodec])
    Form.show()
    prog.x_axis
    sys.exit(app.exec_())
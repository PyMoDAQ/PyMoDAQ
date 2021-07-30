from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import pyqtSlot, QObject, QThread, pyqtSignal, QLocale, QDateTime, QSize
import sys
import pyqtgraph as pg
import numpy as np
from pymodaq.daq_utils import daq_utils as utils

logger = utils.set_logger(utils.get_module_name(__file__))


class Viewer1DBasic(QObject):
    """this plots 1D data on a plotwidget. one linear region to select data, one infinite line to select point
    """
    roi_region_signal = pyqtSignal(tuple)
    roi_line_signal = pyqtSignal(float)

    def __init__(self, parent=None, show_region=False, show_line=False):
        """

        Parameters
        ----------
        parent

        Attributes
        ----------
        parent: (QWidget)
        roi_region: (pyqtgraph LinerrRegionItem)
        roi_line: (pyqtgraph InfiniteLine graphitem)
        Properties
        ----------
        labels: (list of str)
        x_axis: (Axis or dict)

        """
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super().__init__()
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

        self.show_roi_region(show_region)
        self.show_roi_line(show_line)

    def show(self, state=True):
        self.parent.setVisible(state)

    def setup_ui(self):
        vboxlayout = QtWidgets.QVBoxLayout()
        self.plotwidget = pg.PlotWidget()
        self.parent.setLayout(vboxlayout)
        vboxlayout.addWidget(self.plotwidget)
        vboxlayout.setContentsMargins(0, 0, 0, 0)

        self.legend = self.plotwidget.addLegend()
        self.roi_region = pg.LinearRegionItem()
        self.roi_line = pg.InfiniteLine(movable=True)
        self.plotwidget.plotItem.addItem(self.roi_region)
        self.plotwidget.plotItem.addItem(self.roi_line)
        self.roi_region.sigRegionChanged.connect(self.update_region)
        self.roi_line.sigPositionChanged.connect(self.update_line)

    def show_roi_region(self, show=True):
        self.roi_region.setVisible(show)

    def show_roi_line(self, show=True):
        self.roi_line.setVisible(show)

    def update_region(self, item):
        self.roi_region_signal.emit(item.getRegion())

    def update_line(self, item):
        self.roi_line_signal.emit(item.getPos()[0])

    @property
    def labels(self):
        return self._labels

    @labels.setter
    def labels(self, labels):
        self._labels = labels
        self.update_labels(labels)

    def update_labels(self, labels=[]):
        try:
            if self.datas is not None:
                labels_tmp = labels[:]
                if self.labels == labels:
                    if self.labels == [] or len(self.labels) < len(self.datas):
                        self._labels = ["CH{}".format(ind) for ind in range(len(self.datas))]
                else:
                    flag = True
                    while flag:
                        items = [item[1].text for item in self.legend.items]
                        if len(items) == 0:
                            flag = False
                        else:
                            self.legend.removeItem(items[0])

                    if len(labels) < len(self.plot_channels):
                        for ind in range(len(labels), len(self.plot_channels)):
                            labels_tmp.append('CH{:02d}'.format(ind))

                    if len(labels_tmp) == len(self.plot_channels):
                        for ind, channel in enumerate(self.plot_channels):
                            self.legend.addItem(channel, labels_tmp[ind])

                    self._labels = labels_tmp

        except Exception as e:
            logger.exception(str(e))

    @pyqtSlot(list)
    def show_data(self, datas):
        if datas is not None:
            self.datas = datas

            if self.labels == [] or len(self.labels) != len(datas):
                self.update_labels(self.labels)

            if self.plot_channels is None:  # initialize data and plots
                self.ini_data_plots(len(datas))
            elif len(self.plot_channels) != len(datas):
                self.remove_plots()
                self.ini_data_plots(len(datas))

            for ind_plot, data in enumerate(datas):
                if self._x_axis is None or len(self._x_axis) != len(data):
                    self._x_axis = np.linspace(0, len(data), len(data), endpoint=False)

                self.plot_channels[ind_plot].setData(x=self.x_axis, y=data)

    def ini_data_plots(self, Nplots):
        self.plot_channels = []

        channels = []
        for ind in range(Nplots):
            channel = self.plotwidget.plot()
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

    def set_axis_label(self, axis_settings=dict(orientation='bottom', label='x axis', units='pxls')):
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
        self.set_axis_label(dict(orientation='bottom', label=label, units=units))


if __name__ == '__main__':  # pragma: no cover
    app = QtWidgets.QApplication(sys.argv)

    def print_region(xx):
        print(xx)

    def print_line(x):
        print(x)

    Form = QtWidgets.QWidget()
    prog = Viewer1DBasic(Form)
    # prog.show_roi_region()
    prog.show_roi_line()
    prog.roi_region_signal.connect(print_region)
    prog.roi_line_signal.connect(print_line)
    from pymodaq.daq_utils.daq_utils import gauss1D

    x = np.linspace(0, 200, 201)
    y1 = gauss1D(x, 75, 25)
    y2 = gauss1D(x, 120, 50, 2)
    tau_half = 27
    tau2 = 100
    x0 = 50
    dx = 20
    ydata_expodec = np.zeros((len(x)))
    ydata_expodec[:50] = 1 * gauss1D(x[:50], x0, dx, 2)
    ydata_expodec[50:] = 1 * np.exp(-(x[50:] - x0) / (tau_half / np.log(2)))  # +1*np.exp(-(x[50:]-x0)/tau2)
    ydata_expodec += 0.1 * np.random.rand(len(x))

    prog.show_data([y1, y2, ydata_expodec])

    Form.show()
    prog.x_axis
    prog.update_labels(labels=['sig0', 'tralala', 'ouhaouh'])
    sys.exit(app.exec_())

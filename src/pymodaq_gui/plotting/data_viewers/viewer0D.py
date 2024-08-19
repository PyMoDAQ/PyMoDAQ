from typing import List, Union, Dict
from numbers import Real

from qtpy import QtWidgets, QtGui
from qtpy.QtCore import QObject, Slot, Signal, Qt
import sys
import pyqtgraph

from pymodaq_utils import utils
from pymodaq_data import data as data_mod
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.plotting.data_viewers.viewer import ViewerBase
from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.plotting.widgets import PlotWidget
from pymodaq_gui.plotting.utils.plot_utils import Data0DWithHistory

import numpy as np
from collections import OrderedDict
import datetime

logger = set_logger(get_module_name(__file__))
PLOT_COLORS = [dict(color=color) for color in utils.plot_colors]


class DataDisplayer(QObject):
    """
    This Object deals with the display of 0D data  on a plotitem
    """

    updated_item = Signal(list)
    labels_changed = Signal(list)

    def __init__(self, plotitem: pyqtgraph.PlotItem, plot_colors=PLOT_COLORS):
        super().__init__()
        self._plotitem = plotitem
        self.colors = plot_colors
        self._plotitem.addLegend()
        self._plot_items: List[pyqtgraph.PlotDataItem] = []
        self._min_lines: List[pyqtgraph.InfiniteLine] = []
        self._max_lines: List[pyqtgraph.InfiniteLine] = []
        self._data = Data0DWithHistory()

        self._mins: List = []
        self._maxs: List = []

        self._show_lines: bool = False

        axis = self._plotitem.getAxis('bottom')
        axis.setLabel(text='Samples', units='S')

    def update_colors(self, colors: List[QtGui.QPen]):
        self.colors[0:len(colors)] = colors
        self.update_data(self._data.last_data, force_update=True)

    @property
    def legend(self) -> pyqtgraph.LegendItem:
        return self._plotitem.legend

    @property
    def legend_names(self) -> List[str]:
        return [item[1].text for item in self.legend.items]

    @property
    def axis(self):
        return self._data.xaxis

    def clear_data(self):
        self._data.clear_data()
        self._mins = []
        self._maxs = []

    def update_axis(self, history_length: int):
        self._data.length = history_length

    @property
    def Ndata(self):
        return len(self._data.last_data) if self._data.last_data is not None else 0

    def update_data(self, data: data_mod.DataWithAxes, force_update=False):
        if data is not None:
            if len(data) != len(self._plot_items) or force_update or data.labels != self.legend_names:
                self.update_display_items(data)

            self._data.add_datas(data)
            for ind, data_str in enumerate(self._data.datas):
                self._plot_items[ind].setData(self._data.xaxis, self._data.datas[data_str])
            if len(self._mins) != len(self._data.datas):
                self._mins = []
                self._maxs = []

            for ind, label in enumerate(self._data.datas):
                if len(self._mins) != len(self._data.datas):
                    self._mins.append(float(np.min(self._data.datas[label])))
                    self._maxs.append(float(np.max(self._data.datas[label])))
                else:
                    self._mins[ind] = min(self._mins[ind], float(np.min(self._data.datas[label])))
                    self._maxs[ind] = max(self._maxs[ind], float(np.max(self._data.datas[label])))
                self._min_lines[ind].setValue(self._mins[ind])
                self._max_lines[ind].setValue(self._maxs[ind])

    def update_display_items(self, data: data_mod.DataWithAxes = None):
        while len(self._plot_items) > 0:
            plot_item = self._plotitem.removeItem(self._plot_items.pop(0))
            self.legend.removeItem(plot_item)
            self._plotitem.removeItem(self._max_lines.pop(0))
            self._plotitem.removeItem(self._min_lines.pop(0))
        if data is not None:
            for ind in range(len(data)):
                self._plot_items.append(pyqtgraph.PlotDataItem(pen=self.colors[ind]))
                self._plotitem.addItem(self._plot_items[-1])
                self.legend.addItem(self._plot_items[-1], data.labels[ind])
                max_line = pyqtgraph.InfiniteLine(angle=0,
                                                  pen=pyqtgraph.mkPen(color=self.colors[ind]['color'],
                                                                      style=Qt.DashLine))
                min_line = pyqtgraph.InfiniteLine(angle=0,
                                                  pen=pyqtgraph.mkPen(color=self.colors[ind]['color'],
                                                                      style=Qt.DashLine))
                self._max_lines.append(max_line)
                self._min_lines.append(min_line)
                max_line.setVisible(self._show_lines)
                min_line.setVisible(self._show_lines)
                self._plotitem.addItem(self._max_lines[-1])
                self._plotitem.addItem(self._min_lines[-1])

            self.updated_item.emit(self._plot_items)
            self.labels_changed.emit(data.labels)

    def show_min_max(self, show=True):
        self._show_lines = show
        for line in self._max_lines:
            line.setVisible(show)
        for line in self._min_lines:
            line.setVisible(show)


class View0D(ActionManager, QObject):
    def __init__(self, parent_widget: QtWidgets.QWidget = None, show_toolbar=True,
                 no_margins=False):
        QObject.__init__(self)
        ActionManager.__init__(self, toolbar=QtWidgets.QToolBar())

        self.no_margins = no_margins
        self.data_displayer: DataDisplayer = None
        self.other_data_displayers: Dict[str, DataDisplayer] = {}
        self.plot_widget: PlotWidget = PlotWidget()
        self.values_list = QtWidgets.QListWidget()

        self.setup_actions()

        self.parent_widget = parent_widget
        if self.parent_widget is None:
            self.parent_widget = QtWidgets.QWidget()
            self.parent_widget.show()

        self.data_displayer = DataDisplayer(self.plotitem)

        self._setup_widgets()
        self._connect_things()
        self._prepare_ui()
        if not show_toolbar:
            self.splitter.setSizes([0,1])

        self.get_action('Nhistory').setValue(200) #default history length

    def setup_actions(self):
        self.add_action('clear', 'Clear plot', 'clear2', 'Clear the current plots')
        self.add_widget('Nhistory', pyqtgraph.SpinBox, tip='Set the history length of the plot',
                        setters=dict(setMaximumWidth=100))
        self.add_action('show_data_as_list', 'Show numbers', 'ChnNum', 'If triggered, will display last data as numbers'
                                                                       'in a side panel', checkable=True)
        self.add_action('show_min_max', 'Show Min/Max lines', 'Statistics',
                        'If triggered, will display horizontal dashed lines for min/max of data', checkable=True)

    def _setup_widgets(self):
        self.splitter = QtWidgets.QSplitter(Qt.Vertical)
        self.parent_widget.setLayout(QtWidgets.QVBoxLayout())
        if self.no_margins:
            self.parent_widget.layout().setContentsMargins(0, 0, 0, 0)

        self.parent_widget.layout().addWidget(self.splitter)
        self.splitter.addWidget(self.toolbar)
        self.splitter.setStretchFactor(0, 0)

        splitter_hor = QtWidgets.QSplitter(Qt.Horizontal)
        self.splitter.addWidget(splitter_hor)

        splitter_hor.addWidget(self.plot_widget)
        splitter_hor.addWidget(self.values_list)

        font = QtGui.QFont()
        font.setPointSize(20)
        self.values_list.setFont(font)

    def _connect_things(self):
        self.connect_action('clear', self.data_displayer.clear_data)
        self.connect_action('show_data_as_list', self.show_data_list)
        self.connect_action('Nhistory', self.data_displayer.update_axis, signal_name='valueChanged')
        self.connect_action('show_min_max', self.data_displayer.show_min_max)

    def _prepare_ui(self):
        """add here everything needed at startup"""
        self.values_list.setVisible(False)

    def get_double_clicked(self):
        return self.plot_widget.view.sig_double_clicked

    @property
    def plotitem(self):
        return self.plot_widget.plotItem

    def display_data(self, data: data_mod.DataWithAxes, displayer: str = None, **kwargs):
        if displayer is None:
            self.data_displayer.update_data(data)
        elif displayer in self.other_data_displayers:
            self.other_data_displayers[displayer].update_data(data)
        if self.is_action_checked('show_data_as_list'):
            self.values_list.clear()
            self.values_list.addItems(['{:.03e}'.format(dat[0]) for dat in data])
            QtWidgets.QApplication.processEvents()

    def show_data_list(self, state=None):
        if state is None:
            state = self.is_action_checked('show_data_as_list')
        self.values_list.setVisible(state)

    def add_data_displayer(self, displayer_name: str, plot_colors=PLOT_COLORS):
        self.other_data_displayers[displayer_name] = DataDisplayer(self.plotitem, plot_colors)
        self.connect_action('clear', self.other_data_displayers[displayer_name].clear_data)

    def remove_data_displayer(self, displayer_name: str):
        displayer = self.other_data_displayers.pop(displayer_name, None)
        if displayer is not None:
            displayer.update_display_items()


class Viewer0D(ViewerBase):
    """this plots 0D data on a plotwidget with history. Display as numbers in a table is possible.

    Datas and measurements are then exported with the signal data_to_export_signal
    """

    def __init__(self, parent=None, title='', show_toolbar=True, no_margins=False):
        super().__init__(parent, title)
        self.view = View0D(self.parent, show_toolbar=show_toolbar, no_margins=no_margins)
        self._labels = []

    def update_colors(self, colors: list, displayer=None):
        if displayer is None:
            self.view.data_displayer.update_colors(colors)
        elif displayer in self.view.other_data_displayers:
            self.view.other_data_displayers[displayer].update_colors(colors)

    @property
    def labels(self):
        return self._labels

    @labels.setter
    def labels(self, labels):
        if labels != self._labels:
            self._labels = labels

    @Slot(list)
    def _show_data(self, data: data_mod.DataRaw):
        self.labels = data.labels
        self.view.display_data(data)
        self.data_to_export_signal.emit(self.data_to_export)


def main_view():
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()
    prog = View0D(widget)
    widget.show()
    sys.exit(app.exec_())


def main():
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()
    prog = Viewer0D(widget, show_toolbar=False)
    from pymodaq_utils.math_utils import gauss1D

    x = np.linspace(0, 200, 201)
    y1 = gauss1D(x, 75, 25) + 0.1*np.random.rand(len(x))
    y2 = 0.7 * gauss1D(x, 120, 50, 2) + 0.2*np.random.rand(len(x))
    widget.show()
    prog.get_action('show_data_as_list').trigger()
    for ind, data in enumerate(y1):
        prog.show_data(data_mod.DataRaw('mydata', data=[np.array([data]), np.array([y2[ind]])],
                                        labels=['lab1', 'lab2']))
        QtWidgets.QApplication.processEvents()

    sys.exit(app.exec_())


if __name__ == '__main__':  # pragma: no cover
    #main_view()
    main()

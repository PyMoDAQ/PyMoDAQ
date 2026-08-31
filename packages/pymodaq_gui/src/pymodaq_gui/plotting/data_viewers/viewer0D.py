from typing import List, Union, Dict
from numbers import Real

from qtpy import QtWidgets, QtGui
from qtpy.QtCore import QObject, Slot, Signal, Qt
import sys
import pyqtgraph
from pyqtgraph import mkPen

from pymodaq_utils.config import GlobalConfig
from pymodaq_utils.logger import set_logger, get_module_name

import pyqtgraph as pg

from pymodaq_gui.utils.widgets import SpinBox
from pymodaq_utils import utils

from pymodaq_data import data as data_mod
from pymodaq_data.plotting.utils import PlotColors

from pymodaq_gui.plotting.data_viewers.viewer import ViewerBase
from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.plotting.widgets import PlotWidget
from pymodaq_gui.plotting.utils.plot_utils import Data0DWithHistory
from pymodaq_gui import foreground_color
from pymodaq_gui.utils.dock import Dock

import numpy as np
from collections import OrderedDict
import datetime

logger = set_logger(get_module_name(__file__))
PLOT_COLORS = [dict(color=color) for color in PlotColors()]
config = GlobalConfig()


class DataDisplayer(QObject):
    """
    This Object deals with the display of 0D data  on a plotitem
    """

    updated_item = Signal(list)
    labels_changed = Signal(list)

    def __init__(self, plotitem: pyqtgraph.PlotItem, plot_colors=None):
        super().__init__()
        if plot_colors is None:
            plot_colors = PLOT_COLORS
        self._plotitem = plotitem
        self.colors = plot_colors
        self._do_scatter = False
        self._do_xy = False
        self._plotitem.addLegend()
        self._plot_items: Dict[str, pg.PlotDataItem] = {}
        self._min_lines: Dict[str, pg.InfiniteLine] = {}
        self._max_lines: Dict[str, pg.InfiniteLine] = {}
        self._data = Data0DWithHistory()
        self.use_timestamps = False

        self._mins: Dict[str, float] = {}
        self._maxs: Dict[str, float] = {}
        self._color_indices: Dict[str, int] = {}

        self._show_lines: bool = False

        axis = self._plotitem.getAxis('bottom')
        axis.setLabel(text='Samples', units='S')

    def _next_color_index(self) -> int:
        """Return the lowest color index not currently in use."""
        used = set(self._color_indices.values())
        for i in range(len(self.colors)):
            if i not in used:
                return i
        return len(self._plot_items) % len(self.colors)

    def _add_label(self, label: str, units: str):
        color_idx = self._next_color_index()
        self._color_indices[label] = color_idx
        color = self.colors[color_idx]
        width = color.pop('width', self.linewidth)
        plot_item = pyqtgraph.PlotDataItem(pen=mkPen(width=width,
                                                     **color))
        self._plot_items[label] = plot_item
        self._plotitem.addItem(plot_item)
        self.legend.addItem(plot_item, f"{label} ({units})")
        dash_pen = pyqtgraph.mkPen(color=color['color'],
                                   style=Qt.PenStyle.DashLine,
                                   )
        max_line = pyqtgraph.InfiniteLine(angle=0, pen=dash_pen)
        min_line = pyqtgraph.InfiniteLine(angle=0, pen=dash_pen)
        self._max_lines[label] = max_line
        self._min_lines[label] = min_line
        max_line.setVisible(self._show_lines)
        min_line.setVisible(self._show_lines)
        self._plotitem.addItem(max_line)
        self._plotitem.addItem(min_line)

    def set_sync_x_axis(self, sync: bool):
        """When True (default), adding a new channel resets all histories so all
        curves start from the same x-index.  When False, existing channels keep
        their history and the new channel is NaN-padded from the left."""
        self._data.sync_x_axis = sync

    def set_use_timestamps(self, use_timestamps: bool = False):
        self.use_timestamps = use_timestamps

        axis = self._plotitem.getAxis('bottom')
        if use_timestamps:
            axis.setLabel(text='Timestamps', units='s')
        else:
            axis.setLabel(text='Samples', units='S')
        self.update_plots()

    def _remove_label(self, label: str):
        if label in self._plot_items:
            plot_item = self._plot_items.pop(label)
            self._plotitem.removeItem(plot_item)
            self.legend.removeItem(plot_item)
        if label in self._max_lines:
            self._plotitem.removeItem(self._max_lines.pop(label))
        if label in self._min_lines:
            self._plotitem.removeItem(self._min_lines.pop(label))
        self._color_indices.pop(label, None)
        self._mins.pop(label, None)
        self._maxs.pop(label, None)

    @property
    def linewidth(self) -> int:
        return config('data', 'plotting', 'linewidth')

    def update_colors(self, colors: List[dict]):
        self.colors[0:len(colors)] = colors
        symbol_size = 5
        symbol = 'o'

        for label, color_idx in self._color_indices.items():
            color = self.colors[color_idx]
            width = color.pop('width', self.linewidth)

            if self._do_scatter:
                pen = None
                symbol_type = symbol
                brush = color['color']
            else:
                pen = mkPen(width=width, **color)
                symbol_type = None
                brush = None
            self._plot_items[label].setPen(pen)
            self._plot_items[label].setSymbolBrush(brush)
            self._plot_items[label].setSymbol(symbol_type)
            self._plot_items[label].setSymbolSize(symbol_size)

            dash_pen = pg.mkPen(color=color['color'], style=Qt.PenStyle.DashLine)
            self._max_lines[label].setPen(dash_pen)
            self._min_lines[label].setPen(dash_pen)
        self.update_plots()

    def update_scatter(self, do_scatter=False):
        self._do_scatter = do_scatter
        self.update_colors(self.colors)

    def update_xyplot(self, do_xy=True):
        self._do_xy = do_xy
        self.update_plots()
        labels = list(self._data.data.keys())
        plot_items = [self._plot_items[label] for label in labels]
        xaxis = self._plotitem.getAxis('bottom')
        yaxis = self._plotitem.getAxis('left')
        if do_xy and len(labels) >= 2:
            plot_items[0].setVisible(False)
            xaxis.setLabel(text=labels[0], units='')
        else:
            plot_items[0].setVisible(True)
            self.set_use_timestamps(self.use_timestamps)

    @property
    def legend(self) -> pg.LegendItem:
        return self._plotitem.legend

    @property
    def legend_names(self) -> List[str]:
        return [item[1].text for item in self.legend.items]

    @property
    def axis(self):
        if self.use_timestamps:
            return self._data.timestamps
        else:
            return self._data.xaxis

    def clear_data(self):
        self._data.clear_data()
        self._mins = {}
        self._maxs = {}

    def update_axis(self, history_length: int):
        self._data.length = history_length

    @property
    def Ndata(self):
        return len(self._data.last_data) if self._data.last_data is not None else 0

    def update_data(self, data: data_mod.DataWithAxes, force_update=False):
        if data is not None:
            if set(data.labels) != set(self._plot_items.keys()) or force_update:
                self.update_display_items(data)

            self._data.add_data(data)
            self.update_plots()

    def update_plots(self):

        if self._do_xy and len(self._data.data) >= 2:
            labels = list(self._data.data.keys())
            plot_items = [self._plot_items[label] for label in labels]
            data_list = [self._data.data[label] for label in labels]
            for ind in range(1, len(data_list)):
                plot_items[ind].setData(data_list[0], data_list[ind])
        else:
            for label, plot_item in self._plot_items.items():
                if label in self._data.data:
                    plot_item.setData(self.axis, self._data.data[label])

        for label, values in self._data.data.items():
            if label not in self._mins:
                self._mins[label] = float(np.nanmin(values))
                self._maxs[label] = float(np.nanmax(values))
            else:
                self._mins[label] = min(self._mins[label], float(np.nanmin(values)))
                self._maxs[label] = max(self._maxs[label], float(np.nanmax(values)))
            if label in self._min_lines:
                self._min_lines[label].setValue(self._mins[label])
                self._max_lines[label].setValue(self._maxs[label])

    def update_display_items(self, data: data_mod.DataWithAxes = None):
        new_labels = set(data.labels) if data is not None else set()
        current_labels = set(self._plot_items.keys())

        for label in current_labels - new_labels:
            self._remove_label(label)

        if data is not None:
            for label in data.labels:
                if label not in self._plot_items:
                    self._add_label(label, data.units)

        if new_labels != current_labels:
            self.updated_item.emit(list(self._plot_items.values()))
            self.labels_changed.emit(data.labels if data is not None else [])

    def show_min_max(self, show=True):
        self._show_lines = show
        for line in self._max_lines.values():
            line.setVisible(show)
        for line in self._min_lines.values():
            line.setVisible(show)


class View0D(ActionManager, QObject):
    def __init__(self, parent_widget: QtWidgets.QWidget = None, show_toolbar=True,
                 no_margins=False, title=''):
        QObject.__init__(self)
        ActionManager.__init__(self, toolbar=QtWidgets.QToolBar())
        self._title = title
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

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
        self._title = value

    def setup_actions(self):
        self.add_action('clear', 'Clear plot', 'ink_eraser', 'Clear the current plots')
        self.add_widget('Nhistory', SpinBox, tip='Set the history length of the plot',
                        setters=dict(setMaximumWidth=100))
        self.add_action('show_data_as_list', 'Show numbers', 'pin', 'If triggered, will display last data as numbers'
                                                                       'in a side panel', checkable=True)
        self.add_action('show_min_max', 'Show Min/Max lines', 'contrast_square',
                        'If triggered, will display horizontal dashed lines for min/max of data', checkable=True)
        self.add_action('use_timestamps', 'Use Timestamps', 'timer_off',
                        'Use timestamps as axis', checkable=True,
                        icon_checked='timer')
        self.add_action('scatter', 'Scatter', 'scatter_plot', 'Switch between line or scatter plots',
                        checkable=True)
        self.add_action('xyplot', 'XYPlotting', 'function',
                        'Switch between normal or XY representation (valid for 2 channels)',
                        checkable=True,
                        visible=False)
        self.add_action('sync_x_axis', 'Sync X axis', 'sync_disabled',
                        'If checked, adding a new channel resets all histories so curves '
                        'share the same x-axis origin', checkable=True, checked=True,
                        icon_checked='sync_lock',
                        icon_color='#F9A825', icon_checked_color='#607D8B')

    def _setup_widgets(self):
        self.splitter = QtWidgets.QSplitter(Qt.Orientation.Vertical)
        self.parent_widget.setLayout(QtWidgets.QVBoxLayout())
        if self.no_margins:
            self.parent_widget.layout().setContentsMargins(0, 0, 0, 0)

        self.parent_widget.layout().addWidget(self.splitter)
        self.splitter.addWidget(self.toolbar)
        self.splitter.setStretchFactor(0, 0)

        splitter_hor = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
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
        self.connect_action('sync_x_axis', self.data_displayer.set_sync_x_axis)
        self.connect_action('use_timestamps', self.data_displayer.set_use_timestamps)
        self.connect_action('use_timestamps', self.set_x_axis_type)
        self.connect_action('scatter', self.data_displayer.update_scatter)
        self.connect_action('xyplot', self.data_displayer.update_xyplot)
        self.connect_action('xyplot', self.set_x_axis_type)

    def set_x_axis_type(self):
        if self.is_action_checked('use_timestamps') and not self.is_action_checked('xyplot'):
            self.plot_widget.plotItem.setAxisItems({'bottom': pg.DateAxisItem()})
        else:
            self.plot_widget.plotItem.setAxisItems({'bottom': pg.AxisItem('bottom')})


    def _prepare_ui(self):
        """add here everything needed at startup"""
        self.values_list.setVisible(False)
        self.get_action('Nhistory').setValue(config('gui', 'viewer', 'viewer0D', 'Nhistory'))
        for action_name in ('show_data_as_list', 'show_min_max'):
            if config('gui', 'viewer', 'viewer0D', action_name):
                self.get_action(action_name).trigger()
        if not config('gui', 'viewer', 'viewer0D', 'sync_x_axis'):
            self.get_action('sync_x_axis').trigger()

    def get_double_clicked(self):
        return self.plot_widget.view.sig_double_clicked

    @property
    def plotitem(self):
        return self.plot_widget.plotItem

    def display_data(self, data: data_mod.DataWithAxes, displayer: str = None, **kwargs):
        self.set_action_visible('xyplot', len(data) >= 2)
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

    def __init__(self, parent=None, title='', show_toolbar=True,
                 no_margins=False,
                 rois_dock: Dock = None):
        super().__init__(parent, title)
        self.view = View0D(self.parent, show_toolbar=show_toolbar,
                           no_margins=no_margins, title=title)
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
    sys.exit(app.exec())


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
    prog.get_action('use_timestamps').trigger()
    for ind, data in enumerate(y1):
        prog.show_data(data_mod.DataRaw('mydata', data=[np.array([data]),
                                                        np.array([y2[ind]]),
                                                        -np.array([y2[ind]])],
                                        labels=['lab1', 'lab2'], units="V"))
        QtWidgets.QApplication.processEvents()

    sys.exit(app.exec())


if __name__ == '__main__':  # pragma: no cover
    #main_view()
    main()

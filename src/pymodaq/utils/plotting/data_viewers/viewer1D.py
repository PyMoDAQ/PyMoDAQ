import sys
import datetime
from collections import OrderedDict
from typing import List, Iterable

from qtpy import QtWidgets
from qtpy.QtCore import QObject, Slot, Signal, Qt, QRectF
import pyqtgraph as pg
import numpy as np

from pymodaq.utils.data import DataRaw, DataFromRoi, Axis, DataToExport, DataCalculated, DataWithAxes
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.plotting.items.crosshair import Crosshair
from pymodaq.utils import daq_utils as utils
import pymodaq.utils.math_utils as mutils
from pymodaq.utils.managers.action_manager import ActionManager
from pymodaq.utils.plotting.data_viewers.viewer import ViewerBase

from pymodaq.utils.managers.roi_manager import ROIManager
from pymodaq.utils.plotting.utils.filter import Filter1DFromCrosshair, Filter1DFromRois
from pymodaq.utils.plotting.utils.lineout import LineoutPlotter
from pymodaq.utils.plotting.widgets import PlotWidget


logger = set_logger(get_module_name(__file__))

PLOT_COLORS = utils.plot_colors


class LineoutPlotter(LineoutPlotter):
    """class to manage and display data filtered out into lineouts (1D, 0D)

    Should be inherited and subclass some methods as appropriate

    Parameters
    ----------
    graph_widgets: OrderedDict
        Includes plotwidgets to display data
    roi_manager:
        The ROIManager to create ROIs and manage their properties
    crosshair:
        The Crosshair object
    """
    lineout_widgets = ['int']

    def __init__(self, graph_widgets: OrderedDict, roi_manager: ROIManager, crosshair: Crosshair):
        super().__init__(graph_widgets, roi_manager, crosshair)

    def plot_other_lineouts(self, roi_dicts):
        pass

    def plot_other_crosshair_lineouts(self, crosshair_dict):
        pass


class DataDisplayer(QObject):
    """
    This Object deals with the display of 1D data  on a plotitem
    """

    updated_item = Signal(list)
    labels_changed = Signal(list)

    def __init__(self, plotitem: pg.PlotItem):
        super().__init__()
        self._plotitem = plotitem
        self._plotitem.addLegend()
        self._plot_items: List[pg.PlotDataItem] = []
        self._overlay_items: List[pg.PlotDataItem] = []
        self._axis: Axis = None
        self._data: DataRaw = None

        self._doxy = False
        self._do_sort = False

    @property
    def legend(self):
        return self._plotitem.legend

    def update_axis(self, axis: Axis):
        self._axis = axis.copy()
        if self._axis.get_data() is None:  # create real data vector once here for subsequent use
            self._axis.create_linear_data(axis.size)

    def get_axis(self) -> Axis:
        return self._axis

    def get_plot_items(self):
        return self._plot_items

    def get_plot_item(self, index: int):
        return self._plot_items[index]

    def update_data(self, data: DataRaw, do_xy=False, sort_data=False):
        self._data = data
        if len(data) != len(self._plot_items):
            self.update_display_items(data)
        self.update_plot(do_xy, data, sort_data)

    def update_xy(self, do_xy=False):
        self._doxy = do_xy
        self.update_plot(do_xy, sort_data=self._do_sort)

    def update_sort(self, do_sort=False):
        self._do_sort = do_sort
        self.update_plot(self._doxy, sort_data=self._do_sort)

    def update_plot(self, do_xy=True, data=None, sort_data=False):
        if data is None:
            data = self._data
        if sort_data:
            data = data.sort_data()

        axis = data.get_axis_from_index(0, create=False)[0]
        if axis is not None:
            self.update_axis(axis)

        self._doxy = do_xy
        self._do_sort = sort_data

        self.update_xyplot(do_xy, data)

    def update_xyplot(self, do_xy=True, data=None):
        if data is None:
            data = self._data

        for ind_data, dat in enumerate(data.data):
            if data.size > 0:
                if not do_xy:
                    if self._axis is None:
                        self.update_axis(Axis('index', data=Axis.create_simple_linear_data(dat.size)))
                    self._plot_items[ind_data].setData(self._axis.get_data(), dat)
                else:
                    self._plot_items[ind_data].setData(np.array([]), np.array([]))

        if do_xy and len(data) == 2:
            self._plot_items[0].setData(data.data[0], data.data[1])
            axis = self._plotitem.getAxis('bottom')
            axis.setLabel(text=data.labels[0], units='')
            axis = self._plotitem.getAxis('left')
            axis.setLabel(text=data.labels[1], units='')
            self.legend.setVisible(False)

        else:
            axis = self._plotitem.getAxis('bottom')
            axis.setLabel(text=self._axis.label, units=self._axis.units)
            axis = self._plotitem.getAxis('left')
            axis.setLabel(text='', units='')
            self.legend.setVisible(True)

    def plot_with_scatter(self, with_scatter=True):
        symbol_size = 5
        for ind, plot_item in enumerate(self.get_plot_items()):
            if with_scatter:
                pen = None
                symbol = 'o'
                brush = PLOT_COLORS[ind]

            else:
                pen = PLOT_COLORS[ind]
                symbol = None
                brush = None

            plot_item.setPen(pen)
            plot_item.setSymbolBrush(brush)
            plot_item.setSymbol(symbol)
            plot_item.setSymbolSize(symbol_size)

    def update_display_items(self, data: DataRaw):
        while len(self._plot_items) > 0:
            self._plotitem.removeItem(self._plot_items.pop(0))
        for ind in range(len(data)):
            self._plot_items.append(pg.PlotDataItem(pen=PLOT_COLORS[ind]))
            self._plotitem.addItem(self._plot_items[-1])
            self.legend.addItem(self._plot_items[-1], data.labels[ind])
        self.updated_item.emit(self._plot_items)
        self.labels_changed.emit(data.labels)

    @property
    def labels(self):
        return self._data.labels

    def legend_items(self):
        return [item[1].text for item in self.legend.items]

    def show_overlay(self, show=True):
        if not show:
            while len(self._overlay_items) > 0:
                self._plotitem.removeItem(self._overlay_items.pop(0))
        else:
            for ind in range(len(self._data)):
                pen = pg.mkPen(color=PLOT_COLORS[ind], style=Qt.CustomDashLine)
                pen.setDashPattern([10, 10])
                self._overlay_items.append(pg.PlotDataItem(pen=pen))
                self._plotitem.addItem(self._overlay_items[-1])
                if self._do_sort:
                    self._overlay_items[ind].setData(self._axis.get_data(),
                                                     self._data.sort_data()[ind])
                else:
                    self._overlay_items[ind].setData(self._axis.get_data(), self._data[ind])



class View1D(ActionManager, QObject):
    def __init__(self, parent_widget: QtWidgets.QWidget = None):
        QObject.__init__(self)
        ActionManager.__init__(self, toolbar=QtWidgets.QToolBar())

        self.data_displayer: DataDisplayer = None
        self.plot_widget: PlotWidget = None
        self.lineout_widgets: PlotWidget = None
        self.graphical_widgets: dict = None
        self.crosshair: Crosshair = None

        self.roi_target = pg.InfiniteLine(pen='w')
        self.ROIselect = pg.LinearRegionItem(pen='w')

        self.setup_actions()

        self.parent_widget = parent_widget
        if self.parent_widget is None:
            self.parent_widget = QtWidgets.QWidget()
            self.parent_widget.show()

        self.plot_widget = PlotWidget()
        self.roi_manager = ROIManager('1D')
        self.data_displayer = DataDisplayer(self.plotitem)

        self.setup_widgets()

        self.lineout_plotter = LineoutPlotter(self.graphical_widgets, self.roi_manager, self.crosshair)
        self.connect_things()
        self.prepare_ui()

        self.plotitem.addItem(self.roi_target)
        self.plotitem.addItem(self.ROIselect)
        self.roi_target.setVisible(False)
        self.ROIselect.setVisible(False)

    def move_roi_target(self, pos: Iterable[float], **kwargs):
        if not self.roi_target.isVisible():
            self.roi_target.setVisible(True)
        self.roi_target.setPos(pos[0])

    def get_double_clicked(self):
        return self.plot_widget.view.sig_double_clicked

    def display_roi_lineouts(self, roi_dict):
        self.lineout_plotter.plot_roi_lineouts(roi_dict)

    @property
    def axis(self):
        """Get the current axis used to display data"""
        return self.data_displayer.get_axis()

    @property
    def plotitem(self):
        return self.plot_widget.plotItem

    def get_crosshair_signal(self):
        """Convenience function from the Crosshair"""
        return self.crosshair.crosshair_dragged

    def get_crosshair_position(self):
        """Convenience function from the Crosshair"""
        return self.crosshair.get_positions()

    def set_crosshair_position(self, *positions):
        """Convenience function from the Crosshair"""
        self.crosshair.set_crosshair_position(*positions)

    def display_data(self, data: DataWithAxes):
        self.set_action_visible('xyplot', len(data) == 2)
        self.data_displayer.update_data(data, self.is_action_checked('xyplot'), self.is_action_checked('sort'))

    def prepare_ui(self):
        self.show_hide_crosshair(False)
        self.show_lineout_widgets()

    def do_math(self):
        try:
            if self.is_action_checked('do_math'):
                self.roi_manager.roiwidget.show()
                self.lineout_widgets.show()
            else:
                self.lineout_widgets.hide()
                self.roi_manager.roiwidget.hide()

        except Exception as e:
            logger.exception(str(e))

    @Slot(int, str)
    def update_roi_channels(self, index, roi_type=''):
        """Update the use_channel setting each time a ROI is added"""
        item_param = self.roi_manager.settings.child('ROIs', self.roi_manager.roi_format(index))
        item_param.child('use_channel').setOpts(limits=self.data_displayer.labels)
        item_param.child('use_channel').setValue(self.data_displayer.labels[0])

    def setup_widgets(self):
        self.parent_widget.setLayout(QtWidgets.QVBoxLayout())
        splitter_hor = QtWidgets.QSplitter(Qt.Horizontal)
        self.parent_widget.layout().addWidget(splitter_hor)

        splitter_ver = QtWidgets.QSplitter(Qt.Vertical)
        splitter_hor.addWidget(splitter_ver)
        splitter_hor.addWidget(self.roi_manager.roiwidget)
        self.roi_manager.roiwidget.hide()

        splitter_ver.addWidget(self.toolbar)

        self.lineout_widgets = PlotWidget()
        self.graphical_widgets = dict(lineouts=dict(int=self.lineout_widgets))

        splitter_ver.addWidget(self.plot_widget)
        splitter_ver.addWidget(self.lineout_widgets)
        self.roi_manager.viewer_widget = self.plot_widget

        self.crosshair = Crosshair(self.plotitem, orientation='vertical')
        self.show_hide_crosshair()

    def connect_things(self):
        self.connect_action('aspect_ratio', self.lock_aspect_ratio)

        self.connect_action('do_math', self.do_math)
        self.connect_action('do_math', self.lineout_plotter.roi_clicked)

        self.connect_action('scatter', self.data_displayer.plot_with_scatter)
        self.connect_action('xyplot', self.data_displayer.update_xy)
        self.connect_action('sort', self.data_displayer.update_sort)
        self.connect_action('crosshair', self.show_hide_crosshair)
        self.connect_action('crosshair', self.lineout_plotter.crosshair_clicked)
        self.connect_action('overlay', self.data_displayer.show_overlay)
        self.connect_action('ROIselect', self.show_ROI_select)

        self.roi_manager.new_ROI_signal.connect(self.update_roi_channels)
        self.data_displayer.labels_changed.connect(self.roi_manager.update_use_channel)

    def show_ROI_select(self):
        self.ROIselect.setVisible(self.is_action_checked('ROIselect'))

    def show_lineout_widgets(self):
        state = self.is_action_checked('do_math') or self.is_action_checked('crosshair')
        for lineout_name in LineoutPlotter.lineout_widgets:
            lineout = self.lineout_plotter.get_lineout_widget(lineout_name)
            lineout.setMouseEnabled(state, state)
            lineout.showAxis('left', state)
            lineout.setVisible(state)
            lineout.update()

    def setup_actions(self):
        self.add_action('do_math', 'Math', 'Calculator', 'Do Math using ROI', checkable=True)
        self.add_action('crosshair', 'Crosshair', 'reset', 'Show data cursor', checkable=True)
        self.add_action('aspect_ratio', 'AspectRatio', 'Zoom_1_1', 'Fix the aspect ratio', checkable=True)
        self.add_action('scatter', 'Scatter', 'Marker', 'Switch between line or scatter plots', checkable=True)
        self.add_action('xyplot', 'XYPlotting', '2d',
                        'Switch between normal or XY representation (valid for 2 channels)', checkable=True,
                        visible=False)
        self.add_action('overlay', 'Overlay', 'overlay', 'Plot overlays of current data', checkable=True)
        self.add_action('sort', 'Sort Data', 'sort_ascend', 'Display data in a sorted fashion with respect to axis',
                        checkable=True)
        self.add_action('ROIselect', 'ROI Select', 'Select_24',
                        tip='Show/Hide ROI selection area', checkable=True)
        self.add_action('x_label', 'x:')
        self.add_action('y_label', 'y:')

    def lock_aspect_ratio(self):
        if self.is_action_checked('aspect_ratio'):
            self.plotitem.vb.setAspectLocked(lock=True, ratio=1)
        else:
            self.plotitem.vb.setAspectLocked(lock=False)

    def update_crosshair_data(self, crosshair_dict: dict):
        try:
            string = "y="
            for key in crosshair_dict:
                string += "{:.3e} / ".format(crosshair_dict[key]['value'])
            self.get_action('y_label').setText(string)
            self.get_action('x_label').setText(f"x={crosshair_dict[key]['pos']:.3e} ")

        except Exception as e:
            pass

    @Slot(bool)
    def show_hide_crosshair(self, show=True):
        self.crosshair.setVisible(show)
        self.set_action_visible('x_label', show)
        self.set_action_visible('y_label', show)
        if self.is_action_checked('crosshair'):
            range = self.plotitem.vb.viewRange()
            self.crosshair.set_crosshair_position(xpos=np.mean(np.array(range[0])))

    def add_plot_item(self, item):
        self.plotitem.addItem(item)


class Viewer1D(ViewerBase):
    """this plots 1D data on a plotwidget. Math and measurement can be done on it.

    Datas and measurements are then exported with the signal data_to_export_signal
    """
    ROI_select_signal = Signal(QRectF)

    def __init__(self, parent: QtWidgets.QWidget = None, title=''):
        super().__init__(parent=parent, title=title)

        self.view = View1D(self.parent)

        self.filter_from_rois = Filter1DFromRois(self.view.roi_manager)
        self.filter_from_rois.register_activation_signal(self.view.get_action('do_math').triggered)
        self.filter_from_rois.register_target_slot(self.process_roi_lineouts)

        self.filter_from_crosshair = Filter1DFromCrosshair(self.view.crosshair)
        self.filter_from_crosshair.register_activation_signal(self.view.get_action('crosshair').triggered)
        self.filter_from_crosshair.register_target_slot(self.process_crosshair_lineouts)

        self.prepare_connect_ui()

        self._labels = []

    @property
    def roi_manager(self):
        """Convenience method """
        return self.view.roi_manager

    @property
    def roi_target(self) -> pg.InfiniteLine:
        return self.view.roi_target

    def move_roi_target(self, pos: Iterable[float] = None):
        """move a specific read only ROI at the given position on the viewer"""
        self.view.move_roi_target(pos)

    @property
    def crosshair(self):
        """Convenience method """
        return self.view.crosshair

    def set_crosshair_position(self, xpos, ypos=0):
        """Convenience method to set the crosshair positions"""
        self.view.crosshair.set_crosshair_position(xpos=xpos, ypos=ypos)

    def add_plot_item(self, item):
        self.view.add_plot_item(item)

    @Slot(dict)
    def process_crosshair_lineouts(self, crosshair_dict):
        self.view.update_crosshair_data(crosshair_dict)
        self.crosshair_dragged.emit(*self.view.crosshair.get_positions())

    @Slot(dict)
    def process_roi_lineouts(self, roi_dict):
        self.view.display_roi_lineouts(roi_dict)
        self.measure_data_dict = dict([])
        for roi_key, lineout_data in roi_dict.items():
            if not self._display_temporary:
                if lineout_data.hor_data.size != 0:
                    self.data_to_export.append(
                        DataFromRoi(name=f'Hlineout_{roi_key}', data=[lineout_data.hor_data],
                                    axes=[Axis(data=lineout_data.hor_axis.get_data(),
                                               units=lineout_data.hor_axis.units,
                                               label=lineout_data.hor_axis.label,
                                               index=0)]))

                    self.data_to_export.append(DataCalculated(name=f'Integrated_{roi_key}',
                                                              data=[lineout_data.math_data]))

            self.measure_data_dict[f'{roi_key}:'] = lineout_data.math_data

            QtWidgets.QApplication.processEvents()

        self.view.roi_manager.settings.child('measurements').setValue(self.measure_data_dict)
        if not self._display_temporary:
            self.data_to_export_signal.emit(self.data_to_export)
        self.ROI_changed.emit()

    def prepare_connect_ui(self):
        self.view.ROIselect.sigRegionChangeFinished.connect(self.selected_region_changed)
        self._data_to_show_signal.connect(self.view.display_data)
        self.view.lineout_plotter.roi_changed.connect(self.roi_changed)
        self.view.get_crosshair_signal().connect(self.crosshair_changed)
        self.view.get_double_clicked().connect(self.double_clicked)

    def selected_region_changed(self):
        if self.view.is_action_checked('ROIselect'):
            pos = self.view.ROIselect.getRegion()
            self.ROI_select_signal.emit(QRectF(pos[0], pos[1], 0, 0))

    @Slot(float, float)
    def double_clicked(self, posx, posy=0):
        if self.view.is_action_checked('crosshair'):
            self.view.crosshair.set_crosshair_position(posx)
            self.crosshair_changed()
        self.sig_double_clicked.emit(posx, posy)

    @Slot(dict)
    def roi_changed(self):
        self.filter_from_rois.filter_data(self._raw_data)

    def crosshair_changed(self):
        self.filter_from_crosshair.filter_data(self._raw_data)

    def activate_roi(self, activate=True):
        self.view.set_action_checked('do_math', activate)
        self.view.get_action('do_math').triggered.emit(activate)

    @property
    def labels(self):
        return self._labels

    @labels.setter
    def labels(self, labels):
        if labels != self._labels:
            self._labels = labels

    def _show_data(self, data: DataWithAxes):
        self.labels = data.labels

        self.get_axis_from_view(data)
        self.view.display_data(data)

        if len(self.view.roi_manager.ROIs) == 0:
            self.data_to_export_signal.emit(self.data_to_export)
        else:
            self.roi_changed()
        if self.view.is_action_checked('crosshair'):
            self.crosshair_changed()

    def get_axis_from_view(self, data: DataWithAxes):
        if len(data.axes) == 0:
            if self.view.axis is not None:
                data.axes = [self.view.axis]

    def update_status(self, txt):
        logger.info(txt)


def main():
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    prog = Viewer1D(Form)

    from pymodaq.utils.math_utils import gauss1D

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

    # x = np.sin(np.linspace(0,6*np.pi,201))
    # y = np.sin(np.linspace(0, 6*np.pi, 201)+np.pi/2)
    data = DataRaw('mydata', data=[y1, ydata_expodec],
                   axes=[Axis('myaxis', 'units', data=x)])

    Form.show()
    prog.view.get_action('do_math').trigger()

    def print_data(data: DataToExport):
        print(data.data)
        print('******')
        print(data.get_data_from_dim('Data1D'))
        print('******')
        print(data.get_data_from_dim('Data0D'))
        print('***********************************')

    #prog.data_to_export_signal.connect(print_data)


    QtWidgets.QApplication.processEvents()
    prog.show_data(data)
    QtWidgets.QApplication.processEvents()
    sys.exit(app.exec_())


def main_unsorted():
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()
    prog = Viewer1D(widget)

    from pymodaq.utils.daq_utils import gauss1D

    x = np.linspace(0, 200, 201)
    xaxis = np.concatenate((x, x[::-1]))
    y = gauss1D(x, 75, 25)
    yaxis = np.concatenate((y, -y))
    data = DataRaw('mydata', data=[yaxis],
                   axes=[Axis('myaxis', 'units', data=xaxis)])
    widget.show()
    prog.show_data(data)

    sys.exit(app.exec_())

def main_random():
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()
    prog = Viewer1D(widget)

    from pymodaq.utils.math_utils import gauss1D
    x = np.random.randint(201, size=201)
    y1 = gauss1D(x, 75, 25)
    y2 = gauss1D(x, 120, 50, 2)

    QtWidgets.QApplication.processEvents()
    data = DataRaw('mydata', data=[y1, y2],
                   axes=[Axis('myaxis', 'units', data=x, index=0, spread_order=0)],
                   nav_indexes=(0, ))

    widget.show()
    prog.show_data(data)
    QtWidgets.QApplication.processEvents()
    sys.exit(app.exec_())


def main_view1D():
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()
    prog = View1D(widget)
    widget.show()
    sys.exit(app.exec_())


def main_nans():
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()
    prog = Viewer1D(widget)

    from pymodaq.utils.daq_utils import gauss1D

    x = np.linspace(0, 200, 201)
    y = gauss1D(x, 75, 25)

    y[100:150] = np.nan
    data = DataRaw('mydata', data=[y],
                   axes=[Axis('myaxis', 'units', data=x)])

    widget.show()
    prog.show_data(data)

    sys.exit(app.exec_())


if __name__ == '__main__':  # pragma: no cover
    # main()
    main_random()
    #main_view1D()
    #main_nans()

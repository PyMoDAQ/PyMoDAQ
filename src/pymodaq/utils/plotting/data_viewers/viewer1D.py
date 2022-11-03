import sys
import datetime
from collections import OrderedDict
from typing import List
from qtpy import QtWidgets
from qtpy.QtCore import QObject, Slot, Signal, Qt
from qtpy.QtGui import QIcon, QPixmap
import pyqtgraph as pg
import numpy as np

from pymodaq.utils import data as data_mod
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.plotting.items.crosshair import Crosshair
from pymodaq.utils import daq_utils as utils
import pymodaq.utils.math_utils as mutils
from pymodaq.utils.managers.action_manager import ActionManager
from pymodaq.utils.plotting.data_viewers.viewerbase import ViewerBase
from pymodaq.utils.plotting.data_viewers.viewer1Dbasic import Viewer1DBasic
from pymodaq.utils.managers.roi_manager import ROIManager
from pymodaq.utils.plotting.utils.filter import Filter1DFromCrosshair, Filter1DFromRois
from pymodaq.utils.plotting.utils.lineout import LineoutPlotter, curve_item_factory

# from pymodaq.daq_measurement.daq_measurement_main import DAQ_Measurement
DAQ_Measurement = None

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

    updated_item = Signal(dict)

    def __init__(self, plotitem):
        super().__init__()
        self._plotitem = plotitem
        self._plot_items: List[pg.PlotDataItem] = []
        self._axis = None

    def update_axis(self, axis: data_mod.Axis):
        self._axis = axis

    def get_plot_items(self):
        return self._plot_items

    def get_plot_item(self, index: int):
        return self._plot_items[index]

    def update_data(self, data):
        if len(data) != len(self._plot_items):
            self.update_display_items(len(data))

        axis = data.get_axis_from_index(0, create=False)
        if axis is not None:
            self.update_axis(axis)

        for ind_data, data in enumerate(data.data):
            if data.size > 0:
                self._plot_items[ind_data].setData(self._axis.data, data)

    def plot_with_scatter(self, with_scatter=True):
        symbolSize = 5
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
            plot_item.setSymbolSize(symbolSize)

    def update_display_items(self, ncurve: int):
        while len(self._plot_items) > 0:
            self._plotitem.removeItem(self._plot_items.pop(0))

        for ind in range(ncurve):
            self._plot_items.append(pg.PlotDataItem())
            self._plotitem.addItem(self._plot_items[-1])
        self.updated_item.emit(self._plot_items)


class View1D(ActionManager, QObject):
    def __init__(self, parent_widget: QtWidgets.QWidget = None):
        QObject.__init__(self)
        ActionManager.__init__(self, toolbar=QtWidgets.QToolBar())

        self._data = None

        self.data_displayer: DataDisplayer = None
        self.plot_widget: pg.PlotWidget = None

        self.setup_actions()
        self.roi_manager = ROIManager('1D')

        self.parent_widget = parent_widget
        if self.parent_widget is None:
            self.parent_widget = QtWidgets.QWidget()
            self.parent_widget.show()

        self.setup_widgets()

        self.lineout_plotter = LineoutPlotter(self.graphical_widgets, self.roi_manager, self.crosshair)
        self.connect_things()
        self.prepare_ui()

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

    def display_data(self, data: data_mod.DataRaw):
        self.data_displayer.update_data(data)

    def prepare_ui(self):
        self.show_hide_crosshair(False)
        self.show_lineout_widgets()

    def do_xy(self):
        if self.ui.xyplot_action.isChecked():
            axis = self.plotitem.getAxis('bottom')
            axis.setLabel(text=self.labels[0], units='')
            axis = self.plotitem.getAxis('left')
            axis.setLabel(text=self.labels[1], units='')
            self.legend.setVisible(False)
        else:
            self.set_axis_label(dict(orientation='bottom', label=self.axis_settings['label'],
                                     units=self.axis_settings['units']))
            axis = self.plotitem.getAxis('left')
            axis.setLabel(text='', units='')
            self.legend.setVisible(True)
        self.update_graph1D(self._data)

    def enable_zoom(self):
        try:
            if not self.is_action_checked('zoom'):
                if self.zoom_plot != []:
                    for plot in self.zoom_plot:
                        self.graph_zoom.removeItem(plot)
                self.zoom_widget.hide()
                self.zoom_region.sigRegionChanged.disconnect(self.do_zoom)

            else:
                self.zoom_plot = []
                for ind, data in enumerate(self._data):
                    channel = self.graph_zoom.plot()
                    channel.setPen(self.plot_colors[ind])
                    self.zoom_plot.append(channel)
                self.update_graph1D(self._data)
                self.zoom_region.setRegion([np.min(self._x_axis), np.max(self._x_axis)])

                self.zoom_widget.show()
                self.zoom_region.sigRegionChanged.connect(self.do_zoom)
        except Exception as e:
            logger.exception(str(e))

    def do_math_fun(self):
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
    def add_lineout(self, index, roi_type=''):
        try:
            item = self.roi_manager.ROIs['ROI_{:02d}'.format(index)]
            item_param = self.roi_manager.settings.child('ROIs', 'ROI_{:02d}'.format(index))
            item_param.child(('use_channel')).setOpts(limits=self.labels)
            if len(self.labels) == 0:  # pragma: no cover
                lab = ''
            else:
                lab = self.labels[0]
            item_param.child(('use_channel')).setValue(lab)
            item.sigRegionChanged.connect(self.update_lineouts)
            item.sigRegionChangeFinished.connect(lambda: self.ROI_changed_finished.emit())
            for child in putils.iter_children_params(item_param, childlist=[]):
                if child.type() != 'group':
                    child.sigValueChanged.connect(self.update_lineouts)

            item_lo = self.lineout_widgets.plot()
            item_lo.setPen(item_param.child(('Color')).value())
            self.lo_items['ROI_{:02d}'.format(index)] = item_lo
            self.lo_data = OrderedDict([])
            for k in self.lo_items:
                self.lo_data[k] = np.zeros((1,))
            self.update_lineouts()
        except Exception as e:
            logger.exception(str(e))

    @Slot(str)
    def remove_ROI(self, roi_name):
        if roi_name in self.lo_items:
            item = self.lo_items.pop(roi_name)
            self.lineout_widgets.plotItem.removeItem(item)
        if f'Lineout_{roi_name}:' in self.measure_data_dict:
            self.measure_data_dict.pop(f'Lineout_{roi_name}:')
            self.update_lineouts()

    def setup_widgets(self):

        self.parent_widget.setLayout(QtWidgets.QVBoxLayout())
        splitter_hor = QtWidgets.QSplitter(Qt.Horizontal)
        self.parent_widget.layout().addWidget(splitter_hor)

        splitter_ver = QtWidgets.QSplitter(Qt.Vertical)
        splitter_hor.addWidget(splitter_ver)
        splitter_hor.addWidget(self.roi_manager.roiwidget)
        self.roi_manager.roiwidget.hide()

        splitter_ver.addWidget(self.toolbar)

        self.lineout_widgets = pg.PlotWidget()
        self.plot_widget = pg.PlotWidget()
        self.data_displayer = DataDisplayer(self.plotitem)
        self.graphical_widgets = dict(lineouts=dict(int=self.lineout_widgets))

        splitter_ver.addWidget(self.plot_widget)
        splitter_ver.addWidget(self.lineout_widgets)
        self.roi_manager.viewer_widget = self.plot_widget

        self.setup_zoom()

        self.legend = None
        self.axis_settings = dict(orientation='bottom', label='x axis', units='pxls')

        self.xaxis_item = self.plotitem.getAxis('bottom')
        self.lineout_widgets.hide()
      
        # #crosshair
        self.crosshair = Crosshair(self.plotitem, orientation='vertical')
        self.crosshair.crosshair_dragged.connect(self.update_crosshair_data)
        self.show_hide_crosshair()


    def connect_things(self):
        self.connect_action('aspect_ratio', self.lock_aspect_ratio)

        # #Connecting buttons:
        self.connect_action('do_math', self.do_math_fun)
        self.connect_action('do_math', self.lineout_plotter.roi_clicked)

        self.connect_action('zoom', self.enable_zoom)
        self.connect_action('scatter', self.data_displayer.plot_with_scatter)
        self.connect_action('xyplot', self.do_xy)
        self.connect_action('crosshair', self.show_hide_crosshair)
        self.connect_action('crosshair', self.lineout_plotter.crosshair_clicked)

        self.roi_manager.new_ROI_signal.connect(self.add_lineout)
        self.roi_manager.remove_ROI_signal.connect(self.remove_ROI)

    def show_lineout_widgets(self):
        state = self.is_action_checked('do_math') or self.is_action_checked('crosshair')
        for lineout_name in LineoutPlotter.lineout_widgets:
            lineout = self.lineout_plotter.get_lineout_widget(lineout_name)
            lineout.setMouseEnabled(state, state)
            lineout.showAxis('left', state)
            lineout.setVisible(state)
            lineout.update()

    def setup_actions(self):
        self.add_action('zoom', 'Zoom Widget', 'Zoom_to_Selection', tip='Display a Zoom Widget', checkable=True)
        self.add_action('do_math', 'Math', 'Calculator', 'Do Math using ROI', checkable=True)
        self.add_action('crosshair', 'Crosshair', 'reset', 'Show data cursor', checkable=True)
        self.add_action('aspect_ratio', 'AspectRatio', 'Zoom_1_1', 'Fix the aspect ratio', checkable=True)
        self.add_action('scatter', 'Scatter', 'Marker', 'Switch between line or scatter plots', checkable=True)
        self.add_action('xyplot', 'XYPlotting', '2d',
                        'Switch between normal or XY representation (valid for 2 channels)', checkable=True,
                        visible=False)
        self.add_action('x_label', 'x:')
        self.add_action('y_label', 'y:')

    def setup_zoom(self):
        # create and set the zoom widget
        # self.zoom_widget=Dock("1DViewer zoom", size=(300, 100), closable=True)
        self.zoom_widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()

        self.graph_zoom = pg.PlotWidget()
        layout.addWidget(self.graph_zoom)
        self.zoom_widget.setLayout(layout)

        self.zoom_region = pg.LinearRegionItem()
        self.zoom_region.setZValue(-10)
        self.zoom_region.setBrush('r')
        self.zoom_region.setOpacity(0.2)
        self.graph_zoom.addItem(self.zoom_region)
        self.zoom_plot = []
        # self.dockarea.addDock(self.zoom_widget)
        self.zoom_widget.setVisible(False)

    def lock_aspect_ratio(self):
        if self.is_action_checked('aspect_ratio'):
            self.plotitem.vb.setAspectLocked(lock=True, ratio=1)
        else:
            self.plotitem.vb.setAspectLocked(lock=False)

    def update_crosshair_data(self, posx, posy, name=""):
        try:
            indx = mutils.find_index(self._x_axis, posx)[0][0]

            string = "y="
            for data in self._data:
                string += "{:.6e} / ".format(data[indx])
            self.get_action('y_label').setText(string)
            self.get_action('x_label').setText("x={:.6e} ".format(posx))

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


class Viewer1D(ViewerBase):
    """this plots 1D data on a plotwidget. Math and measurement can be done on it.

    Datas and measurements are then exported with the signal data_to_export_signal
    """

    math_signal = Signal(OrderedDict)  # OrderedDict:=[x_axis=...,data=...,ROI_bounds=...,operation=]
    ROI_changed_finished = Signal()
    convenience_attributes = ('is_action_checked', 'is_action_visible', 'set_action_checked', 'set_action_visible',
                              'get_action', 'addAction', 'toolbar', 'crosshair',
                              'viewer', 'scale_axis', 'unscale_axis', 'roi_manager', 'show_roi_target',
                              'move_scale_roi_target', 'get_data_at')

    def __init__(self, parent=None, title=''):
        super().__init__()


        # self.roi_manager.ROI_changed_finished.connect(self.update_lineouts)

        self.view = View1D(parent)

        self.filter_from_rois = Filter1DFromRois(self.view.roi_manager)
        self.filter_from_rois.register_activation_signal(self.view.get_action('do_math').triggered)
        self.filter_from_rois.register_target_slot(self.process_roi_lineouts)

        self.filter_from_crosshair = Filter1DFromCrosshair(self.view.crosshair)
        self.filter_from_crosshair.register_activation_signal(self.view.get_action('crosshair').triggered)
        self.filter_from_crosshair.register_target_slot(self.process_crosshair_lineouts)

        self.prepare_connect_ui()

        self.add_attributes_from_view()



        self.math_module = Viewer1D_math()


        self._labels = []
        self.plot_channels = None
        self.plot_colors = utils.plot_colors
        self.color_list = ROIManager.color_list
        self.lo_items = OrderedDict([])
        self.lo_data = OrderedDict([])
        self.ROI_bounds = []

        self._x_axis = None

        self._data = []  # datas on each channel. list of 1D arrays
        self.data_to_export = None
        self.measurement_dict = OrderedDict(x_axis=None, datas=[], ROI_bounds=[], operations=[], channels=[])
        # OrderedDict to be send to the daq_measurement module
        self.measure_data_dict = OrderedDict()
        # dictionnary with data to be put in the table on the form: key="Meas.{}:".format(ind)
        # and value is the result of a given lineout or measurement

    def prepare_connect_ui(self):
        self._data_to_show_signal.connect(self.view.display_data)
        self.view.lineout_plotter.roi_changed.connect(self.roi_changed)
        self.view.get_crosshair_signal().connect(self.crosshair_changed)
        self.view.get_double_clicked().connect(self.double_clicked)

    def activate_roi(self, activate=True):
        self.set_action_checked('do_math', activate)
        self.get_action('do_math').triggered.emit(activate)

    def update_lineouts(self):
        try:
            operations = []
            channels = []
            for ind, key in enumerate(self.roi_manager.ROIs):
                operations.append(self.roi_manager.settings.child('ROIs', key, 'math_function').value())
                channels.append(
                    self.roi_manager.settings.child('ROIs', key,
                                                    'use_channel').opts['limits'].index(
                        self.roi_manager.settings.child('ROIs',
                                                        key, 'use_channel').value()))
                self.lo_items[key].setPen(self.roi_manager.settings.child('ROIs', key,
                                                                          'Color').value())

            self.measurement_dict['datas'] = self._data
            self.measurement_dict['ROI_bounds'] = [self.roi_manager.ROIs[item].getRegion() for item in
                                                   self.roi_manager.ROIs]
            self.measurement_dict['channels'] = channels
            self.measurement_dict['operations'] = operations

            data_lo = self.math_module.update_math(self.measurement_dict)
            self.show_math(data_lo)
        except Exception as e:
            pass

    def clear_lo(self):
        self.lo_data = [[] for ind in range(len(self.lo_data))]
        self.update_lineouts()

    def do_zoom(self):
        bounds = self.zoom_region.getRegion()
        self.data_displayer.plotwidget.setXRange(bounds[0], bounds[1])

    def ini_data_plots(self, Nplots):
        try:
            self.plot_channels = []
            # if self.legend is not None:
            #     self.data_displayer.plotwidget.plotItem.removeItem(self.legend)
            self.legend = self.data_displayer.plotwidget.plotItem.legend
            flag = True
            while flag:
                items = [item[1].text for item in self.legend.items]
                if len(items) == 0:
                    flag = False
                else:
                    self.legend.removeItem(items[0])
            channels = []
            for ind in range(Nplots):
                channel = self.data_displayer.plotwidget.plot()
                channel.setPen(self.plot_colors[ind])
                self.legend.addItem(channel, self._labels[ind])
                channels.append(ind)
                self.plot_channels.append(channel)
        except Exception as e:
            logger.exception(str(e))

    def update_labels(self, labels=[]):
        try:
            labels_tmp = labels[:]
            if self.labels == labels:
                if self.labels == [] or len(self.labels) < len(self._data):
                    self._labels = [f"CH{ind:02d}" for ind in range(len(self._data))]
            else:
                if self.legend is not None:
                    flag = True
                    while flag:
                        items = [item[1].text for item in self.legend.items]
                        if len(items) == 0:
                            flag = False
                        else:
                            self.legend.removeItem(items[0])

                    if len(labels) < len(self.plot_channels):
                        for ind in range(len(labels), len(self.plot_channels)):
                            labels_tmp.append(f'CH{ind:02d}')

                    if len(labels_tmp) == len(self.plot_channels):
                        for ind, channel in enumerate(self.plot_channels):
                            self.legend.addItem(channel, labels_tmp[ind])

                    self._labels = labels_tmp

            if self.labels != labels:
                for ind in range(len(self.roi_manager.ROIs)):
                    val = self.roi_manager.settings.child('ROIs', 'ROI_{:02d}'.format(ind), 'use_channel').value()
                    self.roi_manager.settings.child('ROIs', 'ROI_{:02d}'.format(ind), 'use_channel').setOpts(
                        limits=self.labels)
                    if val not in self.labels:
                        self.roi_manager.settings.child('ROIs', 'ROI_{:02d}'.format(ind), 'use_channel').setValue(
                            self.labels[0])

            self.ui.xyplot_action.setVisible(len(self.labels) == 2)


        except Exception as e:
            logger.exception(str(e))

    @property
    def labels(self):
        return self._labels

    @labels.setter
    def labels(self, labels):
        self.update_labels(labels)
        self._labels = labels




    def remove_plots(self):
        if self.plot_channels is not None:
            for channel in self.plot_channels:
                self.data_displayer.plotwidget.removeItem(channel)
            self.plot_channels = None
        if self.legend is not None:
            self.data_displayer.plotwidget.removeItem(self.legend)

    def set_axis_label(self, axis_settings=dict(orientation='bottom', label='x axis', units='pxls')):
        axis = self.data_displayer.plotwidget.plotItem.getAxis(axis_settings['orientation'])
        axis.setLabel(text=axis_settings['label'], units=axis_settings['units'])
        self.axis_settings = axis_settings

    @Slot(list)
    def _show_data(self, data: data_mod.DataRaw):
        try:
            self._data = data
            self.update_labels(self.labels)

            self.data_to_export = OrderedDict(name=self.title, data0D=OrderedDict(), data1D=OrderedDict(), data2D=None)
            for ind, data in enumerate(datas):
                self.data_to_export['data1D']['CH{:03d}'.format(ind)] = data_mod.DataToExport()

            if self.plot_channels == [] or self.plot_channels is None:  # initialize data and plots
                self.ini_data_plots(len(datas))

            elif len(self.plot_channels) != len(datas):
                self.remove_plots()
                self.ini_data_plots(len(datas))

            if x_axis is not None:
                self.set_x_axis(x_axis)

            self.update_graph1D(datas)



            if labels is not None:
                self.update_labels(labels)

            if self.ui.do_measurements_pb.isChecked():
                self.update_measurement_module()

        except Exception as e:
            logger.exception(str(e))


    @Slot(list)
    def show_math(self, data_lo):
        # self.data_to_export=OrderedDict(x_axis=None,y_axis=None,z_axis=None,data0D=None,data1D=None,data2D=None)
        if len(data_lo) != 0:
            for ind, key in enumerate(self.lo_items):
                self.measure_data_dict["Lineout_{:s}:".format(key)] = data_lo[ind]
                self.data_to_export['data0D']['Measure_{:03d}'.format(ind)] =\
                    data_mod.DataToExport(name=self.title, data=np.array([data_lo[ind]]), source='roi')
            self.roi_manager.settings.child(('measurements')).setValue(self.measure_data_dict)

            for ind, key in enumerate(self.lo_items):
                self.lo_data[key] = np.append(self.lo_data[key], data_lo[ind])
                self.lo_items[key].setData(y=self.lo_data[key])

        if not (self.ui.do_measurements_pb.isChecked()):  # otherwise you export data from measurement
            self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()
            self.data_to_export_signal.emit(self.data_to_export)

    @Slot(list)
    def show_measurement(self, data_meas):
        ind_offset = len(self.data_to_export['data0D'])
        for ind, res in enumerate(data_meas):
            self.measure_data_dict["Meas.{}:".format(ind)] = res
            self.data_to_export['data0D']['Measure_{:03d}'.format(ind + ind_offset)] = \
                data_mod.DataToExport(name=self.title, data=np.array([res]), source='roi')
        self.roi_manager.settings.child('measurements').setValue(self.measure_data_dict)
        self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()
        self.data_to_export_signal.emit(self.data_to_export)


    def update_graph1D(self, datas):
        # self.data_to_export=OrderedDict(data0D=OrderedDict(),data1D=OrderedDict(),data2D=None)
        try:

            pens = []
            symbolBrushs = []
            symbolSize = 5
            for ind, ch in enumerate(self.plot_channels):
                if self.ui.scatter.isChecked():
                    pens.append(None)
                    symbol = 'o'
                    symbolBrushs.append(self.plot_colors[ind])
                else:
                    pens.append(self.plot_colors[ind])
                    symbol = None

                    symbolBrushs.append(None)

            if self.x_axis is None:
                self._x_axis = np.linspace(0, len(datas[0]), len(datas[0]), endpoint=False)
            elif len(self.x_axis) != len(datas[0]):
                self._x_axis = np.linspace(0, len(datas[0]), len(datas[0]), endpoint=False)

            for ind_plot, data in enumerate(datas):
                if not self.ui.xyplot_action.isChecked() or len(datas) == 0:
                    self.plot_channels[ind_plot].setData(x=self.x_axis, y=data, pen=pens[ind_plot], symbol=symbol,
                                                     symbolBrush=symbolBrushs[ind_plot], symbolSize=symbolSize,
                                                     pxMode=True)
                else:
                    self.plot_channels[ind_plot].setData(x=np.array([]), y=np.array([]), pen=pens[ind_plot], symbol=symbol,
                                                         symbolBrush=symbolBrushs[ind_plot], symbolSize=symbolSize,
                                                         pxMode=True)
                if self.ui.zoom_pb.isChecked():
                    self.zoom_plot[ind_plot].setData(x=self.x_axis, y=data)
                x_axis = data_mod.Axis(data=self.x_axis, units=self.axis_settings['units'],
                                         label=self.axis_settings['label'])
                self.data_to_export['data1D']['CH{:03d}'.format(ind_plot)].update(
                    OrderedDict(name=self.title, data=data, x_axis=x_axis, source='raw'))  # to be saved or exported

            if self.ui.xyplot_action.isChecked() and len(datas) > 1:
                self.plot_channels[0].setData(x=datas[0], y=datas[1], pen=pens[0], symbol=symbol,
                                              symbolBrush=symbolBrushs[0], symbolSize=symbolSize,
                                              pxMode=True)

            if not self.ui.Do_math_pb.isChecked():  # otherwise math is done and then data is exported
                self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()
                self.data_to_export_signal.emit(self.data_to_export)
            else:
                self.measurement_dict['datas'] = datas
                if self.measurement_dict['x_axis'] is None:
                    self.measurement_dict['x_axis'] = self._x_axis
                data_lo = self.math_module.update_math(self.measurement_dict)
                self.show_math(data_lo)

        except Exception as e:
            logger.exception(str(e))



    def update_status(self, txt):
        logger.info(txt)

    @property
    def x_axis(self):
        return self._x_axis

    @x_axis.setter
    def x_axis(self, x_axis):
        self.set_x_axis(x_axis)
        if self._data:
            self.show_data_temp(self._data)

    def set_x_axis(self, x_axis):
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
        self.measurement_dict['x_axis'] = self._x_axis
        self.set_axis_label(dict(orientation='bottom', label=label, units=units))


class Viewer1D_math(QObject):
    status_sig = Signal(list)

    def __init__(self):
        super(QObject, self).__init__()
        self._data = []
        self.ROI_bounds = []
        self.x_axis = None
        self.operations = []
        self.channels = []

    def update_math(self, measurement_dict):
        try:
            if 'datas' in measurement_dict:
                self._data = measurement_dict['datas']
            if 'ROI_bounds' in measurement_dict:
                self.ROI_bounds = measurement_dict['ROI_bounds']
            if 'x_axis' in measurement_dict:
                self.x_axis = measurement_dict['x_axis']
            if 'operations' in measurement_dict:
                self.operations = measurement_dict['operations']
            if 'channels' in measurement_dict:
                self.channels = measurement_dict['channels']

            # self.status_sig.emit(["Update_Status","doing math"])
            data_lo = []
            for ind_meas in range(len(self.operations)):
                indexes = mutils.find_index(self.x_axis, self.ROI_bounds[ind_meas])
                ind1 = indexes[0][0]
                ind2 = indexes[1][0]
                sub_data = self._data[self.channels[ind_meas]][ind1:ind2]
                sub_xaxis = self.x_axis[ind1:ind2]

                if self.operations[ind_meas] == "Mean":
                    data_lo.append(float(np.mean(sub_data)))
                elif self.operations[ind_meas] == "Sum":
                    data_lo.append(float(np.sum(sub_data)))
                elif self.operations[ind_meas] == 'half-life' or self.operations[ind_meas] == 'expotime':
                    ind_x0 = mutils.find_index(sub_data, np.max(sub_data))[0][0]
                    x0 = sub_xaxis[ind_x0]
                    sub_xaxis = sub_xaxis[ind_x0:]
                    sub_data = sub_data[ind_x0:]
                    offset = sub_data[-1]
                    N0 = np.max(sub_data) - offset
                    if self.operations[ind_meas] == 'half-life':
                        time = sub_xaxis[mutils.find_index(sub_data - offset, 0.5 * N0)[0][0]] - x0
                    elif self.operations[ind_meas] == 'expotime':
                        time = sub_xaxis[mutils.find_index(sub_data - offset, 0.37 * N0)[0][0]] - x0
                    data_lo.append(time)

            return data_lo
        except Exception as e:
            logger.exception(str(e))
            return []


def main():
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    prog = Viewer1D(Form)

    from pymodaq.utils.daq_utils import gauss1D

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

    Form.show()
    prog.ui.Do_math_pb.click()
    QtWidgets.QApplication.processEvents()
    prog.x_axis = x
    # prog.show_data([y, y+2])
    prog.show_data([y1, y2, ydata_expodec])
    QtWidgets.QApplication.processEvents()
    prog.update_labels(['coucou', 'label2'])
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

    widget.show()
    prog.show_data([yaxis], x_axis=xaxis)

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

    widget.show()
    prog.show_data([y], x_axis=x)

    sys.exit(app.exec_())

if __name__ == '__main__':  # pragma: no cover
    #main()
    #main_unsorted()
    main_view1D()
    #main_nans()

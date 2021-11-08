from functools import singledispatchmethod
from collections import OrderedDict
import copy
import datetime
import numpy as np
import sys

from multipledispatch import dispatch

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import QObject, Slot, Signal, QPointF
import pyqtgraph as pg
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients

from pymodaq.daq_utils.managers.roi_manager import ROIManager
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_basic import ImageWidget
from pymodaq.daq_utils.plotting.graph_items import ImageItem, PlotCurveItem, TriangulationItem, AxisItem_Scaled, AXIS_POSITIONS
from pymodaq.daq_utils.plotting.crosshair import Crosshair
from pymodaq.daq_utils.gui_utils import DockArea, ActionManager
import pymodaq.daq_utils.daq_utils as utils
from pymodaq.resources.QtDesigner_Ressources import QtDesigner_ressources_rc


logger = utils.set_logger(utils.get_module_name(__file__))

Gradients.update(OrderedDict([
    ('red', {'ticks': [(0.0, (0, 0, 0, 255)), (1.0, (255, 0, 0, 255))], 'mode': 'rgb'}),
    ('green', {'ticks': [(0.0, (0, 0, 0, 255)), (1.0, (0, 255, 0, 255))], 'mode': 'rgb'}),
    ('blue', {'ticks': [(0.0, (0, 0, 0, 255)), (1.0, (0, 0, 255, 255))], 'mode': 'rgb'}),
    ('spread', {'ticks': [(0.0, (0, 0, 0, 255)), (1.0, (255, 255, 255, 255))], 'mode': 'rgb'}),]))

COLORS_DICT = dict(red=(255, 0, 0), green=(0, 255, 0), blue=(0, 0, 255), spread=(128, 128, 128))
IMAGE_TYPES = ['red', 'green', 'blue']
LINEOUT_WIDGETS = ['hor', 'ver', 'int']
COLOR_LIST = utils.plot_colors


def image_item_factory(item_type='uniform', axisOrder='row-major'):
    if item_type == 'uniform':
        image = ImageItem()
        image.setOpts(axisOrder=axisOrder)
    elif item_type == 'spread':
        image = TriangulationItem()
    image.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
    return image


def histogram_factory(image_item=None, gradient='red'):
    """
    Create a pyqtgraph HistogramLUTWidget widget (histogram) and link it to the corresponding image_item
    Parameters
    ----------
    image_item: (ImageItem) the image item to be linked with the histogram
    gradient: (str) either 'red', 'green', 'blue', 'spread' or one of the Gradients

    Returns
    -------
    HistogramLUTWidget instance
    """

    if gradient not in Gradients:
        return KeyError(f'Possible gradient are {Gradients} not {gradient}')

    histo = pg.HistogramLUTWidget()
    if image_item is not None:
        histo.setImageItem(image_item)

    histo.gradient.loadPreset(gradient)
    return histo


def curve_item_factory(pen='red'):
    """
    Create a PlotCurveItem with the given pen
    Parameters
    ----------
    pen: any type of arguments accepted by pyqtgraph.function.mkColor or one of the COLORS_DICT key

    Returns
    -------
    PlotCurveItem
    """
    if isinstance(pen, str):
        if pen in COLORS_DICT:
            pen = COLORS_DICT[pen]

    return PlotCurveItem(pen=pen)


class Data0DWithHistory:
    def __init__(self):
        super().__init__()
        self._datas = dict([])
        self.Nsamples = 200
        self._xaxis = None
        self._data_length = 0

    @dispatch(list)
    def add_datas(self, datas: list):
        datas = {f'data_{ind:02d}': datas[ind] for ind in datas}
        self.add_datas(datas)

    @dispatch(dict)
    def add_datas(self, datas: dict):
        """
        add datas on the form of a dict of key/data pairs (data is a numpy 0D array)
        Parameters
        ----------
        datas: (dict)

        Returns
        -------

        """
        if len(datas) != len(self._datas):
            self.clear_data()

        self._data_length += 1

        if self._data_length > self.Nsamples:
            self._xaxis += 1
        else:
            self._xaxis = np.linspace(0, self._data_length, self._data_length, endpoint=False)

        for data_key, data in datas.items():
            if self._data_length == 1:
                self._datas[data_key] = data
            else:
                self._datas[data_key] = np.concatenate((self._datas[data_key], data))

            if self._data_length > self.Nsamples:
                self._datas[data_key] = self._datas[data_key][1:]

    @property
    def datas(self):
        return self._datas

    @property
    def xaxis(self):
        return self._xaxis

    def clear_data(self):
        self._datas = dict([])
        self._data_length = 0

def extract_axis_info(axis):
    label = ''
    units = ''
    if isinstance(axis, dict):
        if 'data' in axis:
            data = axis['data']
        if 'label' in axis:
            label = axis['label']
        if 'units' in axis:
            units = axis['units']
    else:
        data = axis

    if len(data) > 1:
        scaling = data[1] - data[0]
        if scaling > 0:
            offset = np.min(data)
        else:
            offset = np.max(data)
    else:
        scaling = 1.
        offset = 0.
    return scaling, offset, label, units


class LineoutData:
    def __init__(self, hor_axis=None, ver_axis=None, hor_data=None, ver_data=None, int_data=None):
        super().__init__()
        if len(hor_axis) != len(hor_data):
            raise ValueError(f'Horizontal lineout data and axis must have the same size')
        if len(ver_axis) != len(ver_data):
            raise ValueError(f'Horizontal lineout data and axis must have the same size')

        self.hor_axis = hor_axis
        self.ver_axis = ver_axis
        self.hor_data = hor_data
        self.ver_data = ver_data
        if int_data is None:
            self.int_data = np.array([np.sum(self.ver_data)])
        else:
            self.int_data = int_data


class FilterFromCrosshair:
    def __init__(self, graph_items):
        self._graph_items = graph_items
        self._data_index, self._y = 0., 0.

    def filter_data(self, datas: utils.DataFromPlugins):
        data_type = datas['distribution']
        data_dict = dict([])
        for data_index in range(len(IMAGE_TYPES)):
            if data_index < len(datas['data']):
                data = datas['data'][data_index]
                image_type = IMAGE_TYPES[data_index]
                if data_type == 'uniform':
                    data_dict[image_type] = self.get_data_from_uniform(image_type, data)
                elif data_type == 'spread':
                    data_dict[image_type] = self.get_data_from_spread(image_type, data)
        return data_dict

    def get_data_from_uniform(self, data_key, data):
        hor_axis, ver_axis = \
            np.linspace(0, self._graph_items[data_key].width() - 1, self._graph_items[data_key].width()),\
            np.linspace(0, self._graph_items[data_key].height() - 1, self._graph_items[data_key].height())

        indx, indy = self.mapfromview(self._x, self._y, data_key)

        data_H_index = slice(None, None, 1)
        data_V_index = slice(None, None, 1)
        H_indexes = (utils.rint(indy), data_H_index)
        V_indexes = (data_V_index, utils.rint(indx))

        out_of_bounds = False
        if H_indexes[0] >= 0 and H_indexes[0] < len(ver_axis):
            hor_data = data[H_indexes]
        else:
            out_of_bounds = True
            hor_data = np.zeros(hor_axis.shape)
        if V_indexes[1] >= 0 and V_indexes[1] < len(hor_axis):
            ver_data = data[V_indexes]
        else:
            out_of_bounds = True
            ver_data = np.zeros(ver_axis.shape)
        if out_of_bounds:
            ind_data = 0.
        else:
            ind_data = data[utils.rint(indy), utils.rint(indx)]
        return LineoutData(hor_axis=hor_axis, ver_axis=ver_axis, hor_data=hor_data, ver_data=ver_data,
                           int_data=ind_data)

    def get_data_from_spread(self, data_key, data):
        data_H_index = slice(None, None, 1)
        data_V_index = slice(None, None, 1)
        posx, posy = self.mapfromview(self._x, self._y, data_key)

        points, data = self._graph_items[data_key].get_points_at(axis='y', val=posy)
        x_sorted_indexes = np.argsort(points[:, 0])
        hor_axis = points[x_sorted_indexes, 0][data_H_index]

        hor_data = data[x_sorted_indexes][data_H_index]

        points, data = self.img_spread.get_points_at(axis='x', val=posx)
        y_sorted_indexes = np.argsort(points[:, 1])
        ver_axis = points[y_sorted_indexes, 1][data_V_index]

        ver_data = data[y_sorted_indexes][data_V_index]

        return LineoutData(hor_axis=hor_axis, ver_axis=ver_axis, hor_data=hor_data, ver_data=ver_data,
                           int_data=self._graph_items[data_key].get_val_at((posx, posy)))

    def update_filter(self, positions):
        self._x, self._y = self.mapfromview(*positions)

    def mapfromview(self, x, y, item_key='red'):
        """
        get item coordinates from view coordinates
        Parameters
        ----------
        x: (float) x coordinate in the view reference frame
        y: (float) y coordinate in the view refernece frame

        Returns
        -------
        x: (float) coordinate in the item reference frame
        y: (float) coordinate in the item reference frame
        """
        point = self._graph_items[item_key].mapFromView(QtCore.QPointF(x, y))
        return point.x(), point.y()


class FilterFromRois:
    def __init__(self, roi_settings, graph_item):

        self._roi_settings = roi_settings

        self._graph_item = graph_item
        self.axes = (0, 1)
        self._ROIs = None

    def update_filter(self, ROIs):
        self._ROIs = ROIs

    def filter_data(self, datas: utils.DataFromPlugins):
        data_dict = dict([])
        for roi_key, roi in self._ROIs.items():
            image_key = self._roi_settings.child('ROIs', roi_key, 'use_channel').value()
            image_index = IMAGE_TYPES.index(image_key)

            data_type = datas['distribution']
            data = datas['data'][image_index]
            data_dict[roi_key] = self.get_xydata_from_roi(data_type, roi, data)
        return data_dict

    def get_xydata_from_roi(self, data_type, roi, data):

        if data is not None:
            if data_type == 'spread':
                xvals, yvals, data = self.get_xydata_spread(data, roi)
                ind_xaxis = np.argsort(xvals)
                ind_yaxis = np.argsort(yvals)
                xvals = xvals[ind_xaxis]
                yvals = yvals[ind_yaxis]
                data_H = data[ind_xaxis]
                data_V = data[ind_yaxis]
            else:
                xvals, yvals, data = self.get_xydata(data, roi)
                data_H = np.mean(data, axis=0)
                data_V = np.mean(data, axis=1)

            return LineoutData(hor_axis=xvals, ver_axis=yvals, hor_data=data_H, ver_data=data_V)

    def data_from_roi(self, data, roi):

        data, coords = roi.getArrayRegion(data, self._graph_item, self.axes, returnMappedCoords=True)
        return data, coords

    def get_xydata(self, data, roi):
        data, coords = self.data_from_roi(data, roi)

        if data is not None:
            xvals = np.linspace(np.min(np.min(coords[1, :, :])), np.max(np.max(coords[1, :, :])),
                                data.shape[1])
            yvals = np.linspace(np.min(np.min(coords[0, :, :])), np.max(np.max(coords[0, :, :])),
                                data.shape[0])
        else:
            xvals = yvals = data = np.array([])
        return xvals, yvals, data

    def get_xydata_spread(self, data, roi):
        xvals = []
        yvals = []
        data_out = []
        for ind in range(data.shape[0]):
            # invoke the QPainterpath of the ROI (from the shape method)
            if roi.shape().contains(QPointF(data[ind, 0] - roi.pos().x(),
                                            data[ind, 1] - roi.pos().y())):
                xvals.append(data[ind, 0])
                yvals.append(data[ind, 1])
                data_out.append(data[ind, 2])
        data_out = np.array(data_out)
        xvals = np.array(xvals)
        yvals = np.array(yvals)
        return xvals, yvals, data_out


class ActionManager(ActionManager):
    def __init__(self, toolbar=None):
        super().__init__(toolbar=toolbar)

    def setup_actions(self):

        self.addaction('position', '(,)')
        self.addaction('red', 'Red Channel', 'r_icon', tip='Show/Hide Red Channel', checkable=True)
        self.addaction('green', 'Green Channel', 'g_icon', tip='Show/Hide Green Channel', checkable=True)
        self.addaction('blue', 'Blue Channel', 'b_icon', tip='Show/Hide Blue Channel', checkable=True)
        self.addaction('autolevels', 'AutoLevels', 'autoscale',
                       tip='Scale Histogram to Min/Max intensity', checkable=True)
        self.addaction('auto_levels_sym', 'AutoLevels Sym.', 'autoscale',
                       tip='Make the autoscale of the histograms symetric with respect to 0', checkable=True)

        self.addaction('histo', 'Histogram', 'Histogram', tip='Show/Hide Histogram', checkable=True)
        self.addaction('roi', 'ROI', 'Region', tip='Show/Hide ROI Manager', checkable=True)
        self.addaction('isocurve', 'IsoCurve', 'meshPlot', tip='Show/Hide Isocurve', checkable=True)
        self.addaction('init_plot', 'Init. Plot', 'Refresh', tip='Initialize the plots')

        self.addaction('aspect_ratio', 'Aspect Ratio', 'Zoom_1_1', tip='Fix Aspect Ratio', checkable=True)

        self.addaction('crosshair', 'CrossHair', 'reset', tip='Show/Hide data Crosshair', checkable=True)
        self.addaction('ROIselect', 'ROI Select', 'Select_24',
                       tip='Show/Hide ROI selection area', checkable=True)
        self.addaction('flip_ud', 'Flip UD', 'scale_vertically',
                       tip='Flip the image up/down', checkable=True)
        self.addaction('flip_lr', 'Flip LR', 'scale_horizontally',
                       tip='Flip the image left/right', checkable=True)
        self.addaction('rotate', 'Rotate', 'rotation2',
                       tip='Rotate the image', checkable=True)


class ImageDisplayer(QObject):
    """
    This Object deals with the display of 2D data  with a plotitem
    """

    updated_item = Signal(dict)

    def __init__(self, plotitem):
        super().__init__()
        self._plotitem = plotitem
        self.display_type = 'uniform'
        self._image_items = dict([])
        self._autolevels = False

        self.update_display_items()

    def get_images(self):
        return self._image_items

    def get_image(self, name):
        if name not in self._image_items:
            raise KeyError(f'The image {name} is not defined in {self.__class__.__name__}')
        else:
            return self._image_items[name]

    @property
    def autolevels(self):
        return self._autolevels

    @Slot(bool)
    def set_autolevels(self, isautolevel):
        self._autolevels = isautolevel

    def update_data(self, datas):
        if datas['distribution'] != self.display_type:
            self.display_type = datas['distribution']
            self.update_display_items()
        for ind_data, data in enumerate(datas['data']):
            self._image_items[IMAGE_TYPES[ind_data]].setImage(data, self.autolevels)

    def update_display_items(self):
        if not self._image_items:
            for key in self._image_items:
                self._plotitem.removeItem(self._image_items.pop(key))

        for img_key in IMAGE_TYPES:
            self._image_items[img_key] = image_item_factory(self.display_type)
            self._plotitem.addItem(self._image_items[img_key])
        self.updated_item.emit(self._image_items)


    def update_image_visibility(self, are_items_visible):
        if len(are_items_visible) != len(self._image_items):
            raise ValueError(f'The length of the argument is not equal with the number of images')
        for ind, key in enumerate(IMAGE_TYPES):
            self._image_items[key].setVisible(are_items_visible[ind])


class Histogrammer(QObject):
    def __init__(self, histogram_container):
        super().__init__()
        self._histograms = dict([])
        self.histogram_container = histogram_container
        self.setup_histograms()
        self._autolevels = False

    def setup_histograms(self):
        for histo_key in IMAGE_TYPES:
            self._histograms[histo_key] = histogram_factory(None, gradient=histo_key)
            self.add_histogram(self._histograms[histo_key])
            self._histograms[histo_key].setVisible(False)

    def get_histogram(self, name):
        if name not in self._histograms:
            raise KeyError(f'The histogram {name} is not defined in {self.__class__.__name__}')
        else:
            return self._histograms[name]

    @property
    def autolevels(self):
        return self._autolevels

    @Slot(bool)
    def set_autolevels(self, isautolevels=True):
        self._autolevels = isautolevels

    @Slot(bool)
    def activated(self, histo_action_checked):
        if histo_action_checked:
            for histo in self._histograms.values():
                histo.regionChanged()
        for histo in self._histograms.values():
            histo.region.setVisible(not self.autolevels)

    def affect_histo_to_imageitems(self, image_items):
        for img_key in IMAGE_TYPES:
            self._histograms[img_key].setImageItem(image_items[img_key])

    def add_histogram(self, histogram):
        self.histogram_container.layout().addWidget(histogram)

    def show_hide_histogram(self, checked, are_items_visible):
        if checked:
            for ind_histo, histo_name in enumerate(IMAGE_TYPES):
                self._histograms[histo_name].setVisible(are_items_visible[ind_histo])


class IsoCurver(QObject):
    def __init__(self, image_source, histogram_parent):
        super().__init__()
        self._histogram_parent = histogram_parent
        self.setup_iso_curve()
        self.update_image_source(image_source)
        self.update_histogram_parent(histogram_parent)
        self.show_hide_iso(False)

    def setup_iso_curve(self, parent_image_item='red'):
        # # Isocurve drawing
        self._isocurve_item = pg.IsocurveItem(level=0.8, pen='g', axisOrder='row-major')
        self._isocurve_item.setZValue(5)

        # # Draggable line for setting isocurve level
        self._isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
        self._isoLine.setValue(0.8)
        self._isoLine.setZValue(1000)  # bring iso line above contrast controls

        self._isoLine.sigDragged.connect(self.update_isocurve)

    def update_image_source(self, image_source):
        self._isocurve_item.setParentItem(image_source)

    def update_histogram_parent(self, histogram):
        if histogram != self._histogram_parent:
            histogram.vb.removeItem(self._isoLine)
            self._histogram_parent = histogram
        histogram.vb.addItem(self._isoLine)
        histogram.vb.setMouseEnabled(y=False)  # makes user interaction a little easier

    def update_isocurve(self):
        self._isocurve_item.setLevel(self._isoLine.value())

    def set_isocurve_data(self, data):
        self._isocurve_item.setData(data)

    @Slot(bool)
    def show_hide_iso(self, show=True):
        if show:
            self._isocurve_item.show()
            self._isoLine.show()
        else:
            self._isocurve_item.hide()
            self._isoLine.hide()


class LineoutPlotter(QObject):

    roi_changed = Signal(dict)

    def __init__(self, graph_widgets, roi_manager, crosshair):
        super().__init__()

        self._roi_manager = roi_manager
        self._crosshair = crosshair

        self._lineout_widgets = graph_widgets['lineouts']

        self.integrated_data = Data0DWithHistory()

        self._roi_curves = OrderedDict()
        self._crosshair_curves = OrderedDict()
        self._data_integrated = []

        self.setup_crosshair()

    def plot_roi_lineouts(self, roi_dicts):
        self.integrated_data.add_datas({roi_key: roi_dicts[roi_key].int_data for roi_key in roi_dicts})
        for roi_key, lineout_data in roi_dicts.items():
            if roi_key in self._roi_curves:
                self._roi_curves[roi_key]['hor'].setData(lineout_data.hor_axis, lineout_data.hor_data)
                self._roi_curves[roi_key]['ver'].setData(lineout_data.ver_data, lineout_data.ver_axis)
                self._roi_curves[roi_key]['int'].setData(self.integrated_data.xaxis,
                                                         self.integrated_data.datas[roi_key])

    def plot_crosshair_lineouts(self, crosshair_dict):
        for data_key, lineout_data in crosshair_dict.items():
            if data_key in self._crosshair_curves:
                self._crosshair_curves[data_key]['hor'].setData(lineout_data.hor_axis, lineout_data.hor_data)
                self._crosshair_curves[data_key]['ver'].setData(lineout_data.ver_data, lineout_data.ver_axis)

    def get_lineout_widget(self, name):
        if name not in LINEOUT_WIDGETS:
            raise KeyError(f'The lineout_widget reference should be within {LINEOUT_WIDGETS} not {name}')
        return self._lineout_widgets[name]

    @Slot(list)
    def update_roi(self, changes):
        for param, change, param_value in changes:
            if change == 'value':
                if param.name() == 'Color':
                    key = param.parent().name()
                    for curve in self._roi_curves[key].values():
                        curve.setPen(param_value)

            elif change == 'childAdded':
                pass
            elif change == 'parent':
                key = param.name()
                for lineout_name in LINEOUT_WIDGETS:
                    self.view.get_lineout_widget(lineout_name).removeItem(self._roi_curves[key].pop[lineout_name])

        self.roi_changed.emit(self._roi_manager.ROIs)

    @Slot(str)
    def remove_ROI(self, roi_name):
        index = int(roi_name.split('_')[1])
        self.remove_roi_lineout_items(index)

        self.roi_changed.emit(self._roi_manager.ROIs)

    @Slot(int, str)
    def add_ROI(self, newindex, roi_type):
        item = self._roi_manager.ROIs['ROI_{:02d}'.format(newindex)]
        item.sigRegionChanged.connect(lambda: self.roi_changed.emit(self._roi_manager.ROIs))
        item_param = self._roi_manager.settings.child('ROIs', 'ROI_{:02d}'.format(newindex))
        color = item_param.child(('Color')).value()

        self.add_roi_lineout_items(newindex, color)
        self.roi_changed.emit(self._roi_manager.ROIs)

    def add_roi_lineout_items(self, index, pen):
        """
        Add specifics lineouts generated from ROIs
        Parameters
        ----------
        index: (int) index of the ROI generating these lineouts
        pen: (str, tuple) any argument able to generate a QPen, see pyqtgraph.functions.mkPen
        """
        self._roi_curves[f'ROI_{index:02d}'] = \
            {curv_key: curve_item_factory(pen) for curv_key in LINEOUT_WIDGETS}
        self.add_lineout_items(*self._roi_curves[f'ROI_{index:02d}'].values())

    def remove_roi_lineout_items(self, index):
        """
        Remove specifics lineouts generated from ROI referenced by a unique integer
        Parameters
        ----------
        index: (int) index of the ROI generating these lineouts
        """
        items = self._roi_curves.pop(f'ROI_{index:02d}')
        self.remove_lineout_items(*items.values())

    def add_lineout_items(self, *curve_items):
        """
        Add Curve items sequentially to lineouts widgets: (hor, ver and int)
        Parameters
        ----------
        curve_items: (PlotCurveItem) at most 3 of them
        """
        for ind, curve_item in enumerate(curve_items):
            self.get_lineout_widget(LINEOUT_WIDGETS[ind]).addItem(curve_item)

    def remove_lineout_items(self, *curve_items):
        """
        Remove Curve items sequentially to lineouts widgets: (hor, ver and int)
        Parameters
        ----------
        curve_items: (PlotCurveItem) at most 3 of them
        """

        for ind, curve_item in enumerate(curve_items):
            self.get_lineout_widget(LINEOUT_WIDGETS[ind]).removeItem(curve_item)

    @Slot(bool)
    def roi_clicked(self, isroichecked=True):
        self._roi_manager.roiwidget.setVisible(isroichecked)

        for k, roi in self._roi_manager.ROIs.items():
            roi.setVisible(isroichecked)
            for item in self.get_roi_curves()[k].values():
                item.setVisible(isroichecked)

    def get_roi_curves(self):
        return self._roi_curves

    def setup_crosshair(self):
        for image_key in IMAGE_TYPES:
            self._crosshair_curves[image_key] = \
                {curv_key: curve_item_factory(image_key) for curv_key in LINEOUT_WIDGETS}
            self.add_lineout_items(self._crosshair_curves[image_key]['hor'], self._crosshair_curves[image_key]['ver'])

    def show_crosshair_curves(self, curve_key, show=True):
        for curve in self._crosshair_curves[curve_key]:
            curve.setVisible(show)


class View2D(QObject):

    def __init__(self, parent):
        super().__init__()
        # setting the gui
        self.parent = parent
        self.image_widget = ImageWidget()
        self.setupUI()

        self.action_manager = ActionManager(self.toolbar)
        self.histogrammer = Histogrammer(self.widget_histo)
        self.data_displayer = ImageDisplayer(self.plotitem)
        self.histogrammer.affect_histo_to_imageitems(self.data_displayer.get_images())
        self.isocurver = IsoCurver(self.data_displayer.get_image('red'), self.histogrammer.get_histogram('red'))
        self.roi_manager = ROIManager(self.image_widget, '2D')
        self.crosshair = Crosshair(self.image_widget)
        self.lineout_plotter = LineoutPlotter(self.graphical_widgets, self.roi_manager, self.crosshair)

        self.data_displayer.updated_item.connect(self.histogrammer.affect_histo_to_imageitems)
        self.action_manager.connect_action('histo', self.data_displayer.set_autolevels)
        self.action_manager.connect_action('histo', self.histogrammer.activated)
        self.action_manager.connect_action('autolevels', self.histogrammer.set_autolevels)
        self.action_manager.connect_action('isocurve', self.isocurver.show_hide_iso)
        self.action_manager.connect_action('isocurve', self.action_manager.get_action('histo').trigger())

        self.setupROI()

        self.prepare_connect_internal_ui()

        self.set_axis_label('bottom', label='', units='Pxls')
        self.set_axis_label('left', label='', units='Pxls')

    def __getattr__(self, item):
        """
        If item is not found in self, try to look for an attribute in ActionManager such as:
        is_action_visible, is_action_checked, set_action_visible, set_action_checked, connect_action
        """
        if self.action_manager is not None:
            if hasattr(self.action_manager, item):
                return getattr(self.action_manager, item)
        raise AttributeError(f'Attribute {item} cannot be found in self nor in action_manager')

    def display_images(self, datas):
        self.data_displayer.update_data(datas)
        if self.is_action_checked('isocurve'):
            self.isocurver.set_isocurve_data(datas['data'][0])

    def display_roi_lineouts(self, roi_dict):
        self.lineout_plotter.plot_roi_lineouts(roi_dict)

    def display_crosshair_lineouts(self, crosshair_dict):
        self.lineout_plotter.plot_crosshair_lineouts(crosshair_dict)

    def prepare_connect_internal_ui(self):

        for key in IMAGE_TYPES:
            self.connect_action(key, self.notify_visibility_data_displayer)

        self.connect_action('aspect_ratio', self.lock_aspect_ratio)

        self.connect_action('histo', self.show_hide_histogram)

        self.connect_action('roi', self.lineout_plotter.roi_clicked)
        self.connect_action('roi', self.show_lineout_widgets)

        self.ROIselect.setVisible(False)
        self.connect_action('ROIselect', self.show_ROI_select)

        self.connect_action('crosshair', self.show_hide_crosshair)
        self.connect_action('crosshair', self.show_lineout_widgets)
        self.show_hide_crosshair()

        self.show_lineout_widgets()

    def show_lineout_widgets(self):
        state = self.is_action_checked('roi') or self.is_action_checked('crosshair')
        for lineout_name in LINEOUT_WIDGETS:
            lineout = self.lineout_plotter.get_lineout_widget(lineout_name)
            lineout.setMouseEnabled(state, state)
            lineout.showAxis('left', state)
            lineout.setVisible(state)
            lineout.update()
        self.prepare_image_widget_for_lineouts()

    def get_visible_images(self):
        are_items_visible = []
        for key in IMAGE_TYPES:
            are_items_visible.append(self.is_action_checked(key))
        return are_items_visible

    def notify_visibility_data_displayer(self):
        are_items_visible = self.get_visible_images()
        self.data_displayer.update_image_visibility(are_items_visible)

    @Slot(bool)
    def show_hide_histogram(self, show=True):
        are_items_visible = self.get_visible_images()
        self.histogrammer.show_hide_histogram(show, are_items_visible)

    def prepare_image_widget_for_lineouts(self, ratio=0.7):
        QtGui.QGuiApplication.processEvents()
        self.splitter_VRight.splitterMoved[int, int].emit(int(ratio * self.parent.height()), 1)
        self.splitter.moveSplitter(int(ratio * self.parent.width()), 1)
        self.splitter_VLeft.moveSplitter(int(ratio * self.parent.height()), 1)
        self.splitter_VLeft.splitterMoved[int, int].emit(int(ratio * self.parent.height()), 1)
        QtGui.QGuiApplication.processEvents()

    def get_view_range(self):
        return self.image_widget.view.viewRange()

    def lock_aspect_ratio(self):
        lock = self.is_action_checked('aspect_ratio')
        self.plotitem.vb.setAspectLocked(lock=lock, ratio=1)

    def setupUI(self):
        vertical_layout = QtWidgets.QVBoxLayout()
        vertical_layout.setContentsMargins(5, 5, 5, 5)
        self.parent.setLayout(vertical_layout)
        splitter_vertical = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        vertical_layout.addWidget(splitter_vertical)

        # ###### Actions ##########
        self.toolbar = QtWidgets.QToolBar()
        splitter_vertical.addWidget(self.toolbar)
        # ############################

        # ####### Graphs, ImageItem, Histograms ############
        self.graphs_widget = QtWidgets.QWidget()
        self.graphs_widget.setLayout(QtWidgets.QHBoxLayout())
        self.graphs_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.setupGraphs(self.graphs_widget.layout())
        splitter_vertical.addWidget(self.graphs_widget)

        self.ROIselect = pg.RectROI([0, 0], [10, 10], centered=True, sideScalers=True)
        self.plotitem.addItem(self.ROIselect)

        self.splitter_VLeft.splitterMoved[int, int].connect(self.move_right_splitter)
        self.splitter_VRight.splitterMoved[int, int].connect(self.move_left_splitter)

    @Slot(int, int)
    def move_left_splitter(self, pos, index):
        self.splitter_VLeft.blockSignals(True)
        self.splitter_VLeft.moveSplitter(pos, index)
        self.splitter_VLeft.blockSignals(False)

    @Slot(int, int)
    def move_right_splitter(self, pos, index):
        self.splitter_VRight.blockSignals(True)
        self.splitter_VRight.moveSplitter(pos, index)
        self.splitter_VRight.blockSignals(False)


    def setupGraphs(self, graphs_layout):
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        graphs_layout.addWidget(self.splitter)

        self.widget_histo = QtWidgets.QWidget()
        graphs_layout.addWidget(self.widget_histo)
        self.widget_histo.setLayout(QtWidgets.QHBoxLayout())

        self.splitter_VLeft = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.splitter_VRight = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        self.splitter.addWidget(self.splitter_VLeft)
        self.splitter.addWidget(self.splitter_VRight)

        self._lineout_widgets = {widg_key: pg.PlotWidget() for widg_key in LINEOUT_WIDGETS}
        self.graphical_widgets = dict(lineouts=self._lineout_widgets, image=self.image_widget)
        self.splitter_VLeft.addWidget(self.image_widget)
        self.splitter_VLeft.addWidget(self._lineout_widgets['hor'])
        self.splitter_VRight.addWidget(self._lineout_widgets['ver'])
        self.splitter_VRight.addWidget(self._lineout_widgets['int'])

        self.image_widget.add_scaled_axis('right')
        self.image_widget.add_scaled_axis('top')

    def setupROI(self):
        self.roi_manager.new_ROI_signal.connect(self.lineout_plotter.add_ROI)
        self.roi_manager.remove_ROI_signal.connect(self.lineout_plotter.remove_ROI)
        self.roi_manager.roi_settings_changed.connect(self.lineout_plotter.update_roi)
        self.splitter.addWidget(self.roi_manager.roiwidget)
        self.roi_manager.roiwidget.setVisible(False)


    def get_double_clicked(self):
        return self.image_widget.view.sig_double_clicked


    def get_axis(self, position='left'):
        return self.image_widget.getAxis(position)

    @property
    def plotitem(self):
        return self.image_widget.plotitem

    def set_gradient(self, histo='red', gradient='grey'):
        """
        Change the color gradient of the specified histogram
        Parameters
        ----------
        histo: (str) either 'red', 'green', 'blue', 'spread' or 'all'
        gradient: (str or Gradient)
        """
        if gradient in Gradients:
            if histo == 'all':
                for key in IMAGE_TYPES:
                    self._histograms[key].item.gradient.loadPreset(gradient)
            else:
                self._histograms[histo].item.gradient.loadPreset(gradient)

    def get_crosshair_signal(self):
        """Convenience function from the Crosshair"""
        return self.crosshair.crosshair_dragged

    def get_crosshair_position(self):
        """Convenience function from the Crosshair"""
        return self.crosshair.get_positions()

    def set_crosshair_position(self, *positions):
        """Convenience function from the Crosshair"""
        self.crosshair.set_crosshair_position(*positions)

    def show_hide_crosshair(self):
        if self.is_action_checked('crosshair'):
            self.crosshair.setVisible(True)
            self.set_action_visible('position', True)

            range = self.get_view_range()
            self.set_crosshair_position(np.mean(np.array(range[0])), np.mean(np.array(range[0])))

        else:
            self.set_action_visible('position', False)
            self.crosshair.setVisible(False)

    def show_ROI_select(self):
        self.ROIselect.setVisible(self.is_action_checked('ROIselect'))

    def set_axis_label(self, position, label='', units=''):
        """
        Convenience method to set label and unit of any view axes
        Parameters
        ----------
        position: (str) any of AXIS_POSITIONS
        label: (str) text of the axis label
        units: (str) units of the axis label
        """
        axis = self.get_axis(position)
        axis.setLabel(text=label, units=units)

    def get_axis_label(self, position):
        axis = self.get_axis(position)
        return axis.axis_label, axis.axis_offset

    @property
    def axis_units(self):
        return self.labelUnits

    def set_axis_scaling(self, position='top', scaling=1, offset=0, label='', units='Pxls'):
        """
        Method used to update the scaling of the right and top axes in order to translate pixels to real coordinates
        Parameters
        ----------
        position: (str) axis position either one of AXIS_POSITIONS
        scaling: (float) scaling of the axis
        offset: (float) offset of the axis
        label: (str) text of the axis label
        units: (str) units of the axis label
        """

        self.get_axis(position).axis_scaling = scaling
        self.get_axis(position).axis_offset = offset
        self.set_axis_label(position, label=label, units=units)

    def scale_axis(self, xaxis, yaxis):
        x_offset, x_scaling, y_offset, y_scaling = self.get_axis_scaling_offset()
        return xaxis * x_scaling + x_offset, yaxis * y_scaling + y_offset

    def unscale_axis(self, xaxis, yaxis):
        x_offset, x_scaling, y_offset, y_scaling = self.get_axis_scaling_offset()
        return (xaxis - x_offset) / x_scaling, (yaxis - y_offset) / y_scaling

    def get_axis_scaling_offset(self):
        x_offset = self.get_axis('top').axis_offset
        x_scaling = self.get_axis('top').axis_scaling
        y_offset = self.get_axis('right').axis_offset
        y_scaling = self.get_axis('right').axis_scaling
        return x_offset, x_scaling, y_offset, y_scaling


class Viewer2D(QObject):
    data_to_export_signal = Signal(OrderedDict)  # OrderedDict(name=self.DAQ_type,data0D=None,data1D=None,data2D=None)

    crosshair_dragged = Signal(float, float)  # signal used to pass crosshair position to other modules in
    crosshair_clicked = Signal(bool)
    # scaled axes units
    sig_double_clicked = Signal(float, float)

    ROI_changed = Signal()
    ROI_select_signal = Signal(QtCore.QRectF)

    def __init__(self, parent=None):
        super().__init__()

        self.viewer_type = 'Data2D'  # by default
        self.title = "2DViewer"
        self.isdata = dict([])

        if parent is None:
            parent = QtWidgets.QWidget()
            parent.show()
            self.parent = parent

        self.view = View2D(parent)
        filter_from_rois = FilterFromRois(self.view.roi_manager.settings, self.view.data_displayer.get_image('red'))
        filter_from_crosshair = FilterFromCrosshair(self.view.data_displayer.get_images())
        self.model = Model2D(self.view, filter_from_rois, filter_from_crosshair)

        self.model.data_to_show_signal[dict].connect(self.view.display_images)
        self.view.lineout_plotter.roi_changed.connect(self.model.roi_changed)
        self.model.roi_lineout_signal.connect(self.process_roi_lineouts)
        self.model.crosshair_lineout_signal.connect(self.process_crosshair_lineouts)

        self.prepare_connect_ui()

    def setImageTemp(self, data_red=None, data_green=None, data_blue=None, data_spread=None):
        pass

    def setImage(self, data_red=None, data_green=None, data_blue=None, data_spread=None):
        self.show_data(data_red=data_red, data_green=data_green, data_blue=data_blue, data_spread=data_spread)

    @dispatch()
    def show_data(self, data_red=None, data_green=None, data_blue=None, data_spread=None):
        """
        for back compatibility
        """
        if data_spread is None:
            distribution = 'uniform'
            shape = (0, 0)
            for data in [data_red, data_green, data_blue]:
                if data is not None:
                    shape = data.shape
                    break

            data_list = [data_red if data_red is not None else np.zeros(shape),
                         data_green if data_green is not None else np.zeros(shape),
                         data_blue if data_blue is not None else np.zeros(shape),
                         ]
        else:
            distribution = 'spread'
            data_list = [data_spread]

        datas = utils.DataFromPlugins(name='', distribution=distribution, data=data_list)
        self.show_data(datas)

    def show_data_temp(self, datas: utils.DataFromPlugins):
        self.display_temporary = True
        self.show_data(datas)

    @dispatch(utils.DataFromPlugins)
    def show_data(self, datas: utils.DataFromPlugins):
        """
        numpy arrays to be plotted and eventually filtered using ROI...
        Parameters
        ----------
        datas: (utils.DataToExport)

        """
        self.data_to_export = OrderedDict(name=self.title, data0D=OrderedDict(), data1D=OrderedDict())
        self._datas = copy.deepcopy(datas)
        self.display_temporary = False

        self.isdata['red'] = len(datas['data']) > 0
        self.isdata['green'] = len(datas['data']) > 1
        self.isdata['blue'] = len(datas['data']) > 2


        self.set_visible_items()
        self.update_model_data()

        self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()
        self.data_to_export_signal.emit(self.data_to_export)

    def set_visible_items(self):
        for key in IMAGE_TYPES:
            if self.view.is_action_checked(key) and not self.isdata[key]:  # turn it off if it was on but there is no data
                self.view.set_action_checked(key, False)
                self.view.set_action_visible(key, False)

            elif self.isdata[key]:
                self.view.set_action_checked(key, True)
                self.view.set_action_visible(key, True)

            self.view.notify_visibility_data_displayer()
            self.view.show_hide_histogram(True)


    def update_model_data(self):
        self.model.set_data(self.set_image_transform())

    def set_image_transform(self):
        """
        Deactivate some tool buttons if data type is "spread" then apply transform_image
        """

        self.view.set_action_visible('flip_ud', self._datas['distribution'] != 'spread')
        self.view.set_action_visible('flip_lr', self._datas['distribution'] != 'spread')
        self.view.set_action_visible('rotate', self._datas['distribution'] != 'spread')
        if self._datas['distribution'] != 'spread':
            for ind_data in range(len(self._datas['data'])):
                self._datas['data'][ind_data] = self.transform_image(self._datas['data'][ind_data])
        return self._datas

    def transform_image(self, data):
        if data is not None:
            if len(data.shape) > 2:
                data = np.mean(data, axis=0)
            if self.view.is_action_checked('flip_ud'):
                data = np.flipud(data)
            if self.view.is_action_checked('flip_lr'):
                data = np.fliplr(data)
            if self.view.is_action_checked('rotate'):
                data = np.flipud(np.transpose(data))
        return data

    def update_crosshair_data(self, crosshair_dict):
        try:
            posx, posy = self.view.get_crosshair_position()
            (posx_scaled, posy_scaled) = self.view.scale_axis(posx, posy)

            dat = f'({posx_scaled:.1e}, {posy_scaled:.1e})'
            for image_key in IMAGE_TYPES:
                if self.view.is_action_checked(image_key):
                    dat += f' {image_key}={crosshair_dict[image_key].int_data:.1e},'

            self.view.set_action_text('position', dat)

        except Exception as e:
            print(e)

    def prepare_connect_ui(self):
        # selection area checkbox
        self.view.set_action_visible('red', True)
        self.view.set_action_checked('red', True)
        self.view.set_action_visible('green', True)
        self.view.set_action_checked('green', True)
        self.view.set_action_visible('blue', True)
        self.view.set_action_checked('blue', True)

        self.view.ROIselect.sigRegionChangeFinished.connect(self.selected_region_changed)

        self.view.connect_action('flip_ud', slot=self.update_model_data)
        self.view.connect_action('flip_lr', slot=self.update_model_data)
        self.view.connect_action('rotate', slot=self.update_model_data)
        self.view.connect_action('autolevels', slot=self.update_model_data)
        self.view.connect_action('isocurve', slot=self.update_model_data)

        self.view.get_crosshair_signal().connect(self.model.crosshair_changed)

        self.view.get_double_clicked().connect(self.double_clicked)

    def selected_region_changed(self):
        if self.view.is_action_checked('ROIselect'):
            pos = self.view.ROIselect.pos()
            size = self.view.ROIselect.size()
            self.ROI_select_signal.emit(QtCore.QRectF(pos[0], pos[1], size[0], size[1]))

    @Slot(float, float)
    def double_clicked(self, posx, posy):
        self.view.crosshair.set_crosshair_position(posx, posy)
        self.model.crosshair_changed(posx, posy)
        self.sig_double_clicked.emit(posx, posy)

    @property
    def x_axis(self):
        return self.view.get_axis('top')

    @x_axis.setter
    def x_axis(self, axis):
        scaling, offset, label, units = extract_axis_info(axis)
        self.view.set_axis_scaling('top', scaling=scaling, offset=offset, label=label, units=units)

    @property
    def y_axis(self):
        return self.view.get_axis('right')

    @y_axis.setter
    def y_axis(self, axis):
        scaling, offset, label, units = extract_axis_info(axis)
        self.view.set_axis_scaling('top', scaling=scaling, offset=offset, label=label, units=units)

    def scale_lineout_dicts(self, lineout_dicts):
        for lineout_data in lineout_dicts.values():
            lineout_data.hor_axis, lineout_data.ver_axis = \
                self.view.scale_axis(lineout_data.hor_axis, lineout_data.ver_axis)
        return lineout_dicts

    @Slot(dict)
    def process_crosshair_lineouts(self, crosshair_dict):
        self.view.display_crosshair_lineouts(self.scale_lineout_dicts(crosshair_dict))
        self.update_crosshair_data(crosshair_dict)

    @Slot(dict)
    def process_roi_lineouts(self, roi_dict):
        self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()

        roi_dict = self.scale_lineout_dicts(roi_dict)
        self.view.display_roi_lineouts(roi_dict)

        self.measure_data_dict = dict([])
        for roi_key, lineout_data in roi_dict.items():
            self.data_to_export['data1D'][f'{self.title}_Hlineout_{roi_key}'] = \
                utils.DataToExport(name=self.title, data=lineout_data.hor_data, source='roi',
                                   x_axis=utils.Axis(data=lineout_data.hor_axis,
                                                     units=self.x_axis.axis_units,
                                                     label=self.x_axis.axis_label))

            self.data_to_export['data1D'][f'{self.title}_Vlineout_{roi_key}'] = \
                utils.DataToExport(name=self.title, data=lineout_data.ver_data, source='roi',
                                   x_axis=utils.Axis(data=lineout_data.ver_axis,
                                                     units=self.y_axis.axis_units,
                                                     label=self.y_axis.axis_units))

            self.data_to_export['data0D'][f'{self.title}_Integrated_{roi_key}'] = \
                utils.DataToExport(name=self.title, data=lineout_data.int_data, source='roi', )

            self.measure_data_dict[f'Lineout {roi_key}:'] = lineout_data.int_data

        self.view.roi_manager.settings.child('measurements').setValue(self.measure_data_dict)
        self.data_to_export_signal.emit(self.data_to_export)

        QtWidgets.QApplication.processEvents()
        self.ROI_changed.emit()

class Model2D(QObject):

    data_to_show_signal = Signal(dict)
    roi_lineout_signal = Signal(dict)
    crosshair_lineout_signal = Signal(dict)

    def __init__(self, view, filter_from_ROIs: FilterFromRois, filter_from_crosshair: FilterFromCrosshair):
        super().__init__()

        self._datas = None
        self.isdata = dict([])
        self.view = view
        self.filter_from_ROIs = filter_from_ROIs
        self.filter_from_crosshair = filter_from_crosshair

    def set_data(self, datas: utils.DataFromPlugins):
        try:
            self._datas = datas
            self.data_to_show_signal.emit(self._datas)

            if self.view.is_action_checked('roi'):
                self.model.roi_changed(self.view.roi_selection.ROIs)

            if self.view.is_action_checked('crosshair'):
                self.crosshair_changed(*self.view.crosshair.get_positions())

        except Exception as e:
            print(e)

    @Slot(dict)
    def roi_changed(self, ROIs):
        if self._datas is None:
            return

        self.filter_from_ROIs.update_filter(ROIs)

        roi_lineout_dict = self.filter_from_ROIs.filter_data(self._datas)

        self.roi_lineout_signal.emit(roi_lineout_dict)

    def crosshair_changed(self, posx=None, posy=None):

        if posx is None or posy is None or self._datas is None:
            return

        self.filter_from_crosshair.update_filter([posx, posy])

        crosshair_lineout_dict = self.filter_from_crosshair.filter_data(self._datas)

        self.crosshair_lineout_signal.emit(crosshair_lineout_dict)

    def show_hide_histogram_with_data(self):
        for key in self.view.histograms:
            if self.isdata[key] and self.view.actions[key].isChecked():
                self.view.histograms[key].setVisible(self.view.actions['histo'].isChecked())
                self.view.histograms[key].setLevels(self.raw_data[key].min(), self.raw_data[key].max())
        QtWidgets.QApplication.processEvents()


def main_controller():

    app = QtWidgets.QApplication(sys.argv)
    form = QtWidgets.QWidget()

    Nx = 100
    Ny = 200
    data_random = np.random.normal(size=(Ny, Nx))
    x = np.linspace(0, Nx - 1, Nx)
    y = np.linspace(0, Ny - 1, Ny)
    from pymodaq.daq_utils.daq_utils import gauss2D

    data_red = 3 * gauss2D(x, 0.2 * Nx, Nx / 5, y, 0.3 * Ny, Ny / 5, 1, 90) * np.sin(x/5)**2
    # data_red = pg.gaussianFilter(data_red, (2, 2))
    data_green = 3 * gauss2D(x, 0.2 * Nx, Nx / 5, y, 0.3 * Ny, Ny / 5, 1, 0)
    # data_green = pg.gaussianFilter(data_green, (2, 2))
    data_blue = data_random + 3 * gauss2D(x, 0.7 * Nx, Nx / 5, y, 0.2 * Ny, Ny / 5, 1)
    data_blue = pg.gaussianFilter(data_blue, (2, 2))

    prog = Viewer2D(form)
    # prog.set_axis_scaling(scaling_options=utils.ScalingOptions(
    #     scaled_xaxis=utils.ScaledAxis(label="eV", units=None, offset=100, scaling=0.1),
    #     scaled_yaxis=utils.ScaledAxis(label="time", units='s', offset=-20, scaling=2)))
    form.show()
    #prog.auto_levels_action_sym.trigger()
    #prog.view.actions['autolevels'].trigger()

    # data = np.load('triangulation_data.npy')
    #prog.show_data(utils.DataFromPlugins(name='mydata', distribution='uniform',
    #                                     data=[data_red, data_blue]))
    prog.show_data(data_red=data_red, data_blue=data_blue)
    # prog.setImage(data_spread=data)
    #app.processEvents()

    sys.exit(app.exec_())



def main_view():
    app = QtWidgets.QApplication(sys.argv)
    form = QtWidgets.QWidget()
    prog = View2D(form)
    form.show()
    sys.exit(app.exec_())

if __name__ == '__main__':  # pragma: no cover

    #main_view()
    main_controller()

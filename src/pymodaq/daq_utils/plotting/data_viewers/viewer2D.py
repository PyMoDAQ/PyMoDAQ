from collections import OrderedDict
import copy
import datetime
import numpy as np
import sys

import pymodaq.daq_utils.messenger
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import QObject, Slot, Signal
import pyqtgraph as pg
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
from pyqtgraph import ROI as pgROI

from pymodaq.daq_utils.managers.roi_manager import ROIManager
from pymodaq.daq_utils.managers.action_manager import ActionManager
from pymodaq.daq_utils.plotting.data_viewers.viewer2D_basic import ImageWidget
from pyqtgraph import PlotCurveItem
from pymodaq.daq_utils.plotting.data_viewers.viewerbase import ViewerBase
from pymodaq.daq_utils.plotting.items.image import UniformImageItem, SpreadImageItem
from pymodaq.daq_utils.plotting.items.axis_scaled import AXIS_POSITIONS
from pymodaq.daq_utils.plotting.items.crosshair import Crosshair
from pymodaq.daq_utils.plotting.utils.plot_utils import Data0DWithHistory, AxisInfosExtractor
from pymodaq.daq_utils.plotting.utils.filter import FilterFromCrosshair, FilterFromRois
import pymodaq.daq_utils.daq_utils as utils
import pymodaq.daq_utils.gui_utils as gutils
from pymodaq.daq_utils.exceptions import ViewerError

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
        image = UniformImageItem()
        image.setOpts(axisOrder=axisOrder)
    elif item_type == 'spread':
        image = SpreadImageItem()
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
        raise KeyError(f'Possible gradient are {Gradients} not {gradient}')

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
            if data.size > 0:
                self._image_items[IMAGE_TYPES[ind_data]].setImage(data, self.autolevels)

    def update_display_items(self):
        while len(self._image_items) > 0:
            self._plotitem.removeItem(self._image_items.pop(next(iter(self._image_items))))

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
    gradient_changed = Signal()

    def __init__(self, histogram_container: QtWidgets.QWidget, histogram_refs=IMAGE_TYPES):
        super().__init__()
        self._histograms = dict([])
        self._histogram_refs = histogram_refs
        self._histogram_container = histogram_container
        self.setup_histograms()
        self._autolevels = False

    def setup_histograms(self):
        for histo_key in self._histogram_refs:
            self._histograms[histo_key] = histogram_factory(None, gradient=histo_key)
            self.add_histogram(self._histograms[histo_key])
            self._histograms[histo_key].setVisible(False)
            self._histograms[histo_key].item.sigLookupTableChanged.connect(lambda: self.gradient_changed.emit())

    def get_histograms(self):
        return self._histograms

    def get_histogram(self, name):
        if name not in self.get_histograms():
            raise KeyError(f'The histogram {name} is not defined in {self.__class__.__name__}')
        else:
            return self._histograms[name]

    @property
    def autolevels(self):
        return self._autolevels

    @Slot(bool)
    def set_autolevels(self, isautolevels=True):
        self._autolevels = isautolevels
        for histo in self._histograms.values():
            histo.region.setVisible(not isautolevels)

    @Slot(bool)
    def activated(self, histo_action_checked):
        if histo_action_checked:
            for histo in self._histograms.values():
                histo.regionChanged()

    def affect_histo_to_imageitems(self, image_items):
        # TODO: if self._histogram_refs doesn't contains the same refs as image_items, we have an issue...
        for img_key in self._histogram_refs:
            self._histograms[img_key].setImageItem(image_items[img_key])

    def add_histogram(self, histogram):
        if self._histogram_container.layout() is None:
            self._histogram_container.setLayout(QtWidgets.QHBoxLayout())
        self._histogram_container.layout().addWidget(histogram)

    def show_hide_histogram(self, checked, are_items_visible):
        for ind_histo, histo_name in enumerate(self._histogram_refs):
            self._histograms[histo_name].setVisible(are_items_visible[ind_histo] and checked)

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
                for key in self._histogram_refs:
                    self._histograms[key].item.gradient.loadPreset(gradient)
            else:
                self._histograms[histo].item.gradient.loadPreset(gradient)


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
    crosshair_lineout_plotted = Signal(dict)
    roi_lineout_plotted = Signal(dict)

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

        self._roi_manager.new_ROI_signal.connect(self.add_ROI)
        self._roi_manager.remove_ROI_signal.connect(self.remove_ROI)
        self._roi_manager.roi_value_changed.connect(self.update_roi)

    def plot_roi_lineouts(self, roi_dicts):
        self.integrated_data.add_datas({roi_key: roi_dicts[roi_key].int_data for roi_key in roi_dicts})
        for roi_key, lineout_data in roi_dicts.items():
            if roi_key in self._roi_curves:
                if lineout_data.hor_data.size > 0:
                    self._roi_curves[roi_key]['hor'].setData(lineout_data.hor_axis, lineout_data.hor_data)
                    self._roi_curves[roi_key]['ver'].setData(lineout_data.ver_data, lineout_data.ver_axis)
                self._roi_curves[roi_key]['int'].setData(self.integrated_data.xaxis,
                                                         self.integrated_data.datas[roi_key])
        logger.debug('roi lineouts plotted')
        self.roi_lineout_plotted.emit(roi_dicts)

    def plot_crosshair_lineouts(self, crosshair_dict):
        for data_key, lineout_data in crosshair_dict.items():
            if data_key in self._crosshair_curves:
                self._crosshair_curves[data_key]['hor'].setData(lineout_data.hor_axis, lineout_data.hor_data)
                self._crosshair_curves[data_key]['ver'].setData(lineout_data.ver_data, lineout_data.ver_axis)
        logger.debug('crosshair lineouts plotted')
        self.crosshair_lineout_plotted.emit(crosshair_dict)

    def get_lineout_widget(self, name):
        if name not in LINEOUT_WIDGETS:
            raise KeyError(f'The lineout_widget reference should be within {LINEOUT_WIDGETS} not {name}')
        return self._lineout_widgets[name]

    @Slot(str, tuple)
    def update_roi(self, roi_key, param_changed):
        param, param_value = param_changed

        if param.name() == 'Color':
            for curve in self._roi_curves[roi_key].values():
                curve.setPen(param_value)

        self.roi_changed.emit(self._roi_manager.ROIs)

    @Slot(str)
    def remove_ROI(self, roi_name):
        index = int(roi_name.split('_')[1])
        self.remove_roi_lineout_items(index)

        self.roi_changed.emit(self._roi_manager.ROIs)

    @Slot(int, str)
    def add_ROI(self, newindex, roi_type):
        item = self._roi_manager.get_roi_from_index(newindex)
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
            for item in self.get_roi_curves_triplet()[k].values():
                item.setVisible(isroichecked)

    Slot(bool)
    def crosshair_clicked(self, iscrosshairchecked=True):
        for image_key in IMAGE_TYPES:
            self.show_crosshair_curves(image_key, iscrosshairchecked)

    def get_roi_curves_triplet(self):
        """
        Get the dictionary (one key by ROI) containing dicts with ROI PlotCurveItem

        Example:
        --------
        >>> roi_dict_triplet = self.get_roi_cruves_triplet()
        >>> hor_curve = roi_dict_triplet['ROI_00']['hor']  # where 'hor' is an entry of LINEOUT_WIDGETS
        """
        return self._roi_curves

    def get_crosshair_curves_triplet(self):
        """
        Get the dictionary (one key by ImageItem, see IMAGE_TYPES) containing dicts with PlotCurveItem

        Example:
        --------
        >>> crosshair_dict_triplet = self.get_crosshair_curves_triplet()
        >>> hor_curve = crosshair_dict_triplet['blue']['hor']  # where 'hor' is an entry of LINEOUT_WIDGETS
        """
        return self._crosshair_curves

    def get_crosshair_curve_triplet(self, curve_name):
        return self._crosshair_curves[curve_name]

    def setup_crosshair(self):
        for image_key in IMAGE_TYPES:
            self._crosshair_curves[image_key] = \
                {curv_key: curve_item_factory(image_key) for curv_key in LINEOUT_WIDGETS}
            self.add_lineout_items(self._crosshair_curves[image_key]['hor'], self._crosshair_curves[image_key]['ver'])

    def show_crosshair_curves(self, curve_key, show=True):
        for curve in self._crosshair_curves[curve_key].values():
            curve.setVisible(show)


class View2D(ActionManager, QtCore.QObject):
    def __init__(self, parent_widget=None):
        QtCore.QObject.__init__(self)
        ActionManager.__init__(self, toolbar=QtWidgets.QToolBar())
        self.setup_actions()

        self.parent_widget = parent_widget
        if self.parent_widget is None:
            self.parent_widget = QtWidgets.QWidget()
            self.parent_widget.show()

        self.image_widget = ImageWidget()
        self.roi_manager = ROIManager(self.image_widget, '2D')
        self.ROIselect = pg.RectROI([0, 0], [10, 10], centered=True, sideScalers=True)
        self.roi_target = pgROI(pos=(0, 0), size=(20,20), movable=False, rotatable=False, resizable=False)
        self.roi_target.setVisible(False)

        self.setup_widgets()

        self.histogrammer = Histogrammer(self.widget_histo)
        self.data_displayer = ImageDisplayer(self.plotitem)
        self.isocurver = IsoCurver(self.data_displayer.get_image('red'), self.histogrammer.get_histogram('red'))

        self.crosshair = Crosshair(self.image_widget)
        self.lineout_plotter = LineoutPlotter(self.graphical_widgets, self.roi_manager, self.crosshair)



        self.connect_things()
        self.prepare_ui()

        self.set_axis_label('bottom', label='', units='Pxls')
        self.set_axis_label('left', label='', units='Pxls')

    def show_roi_target(self, show=True):
        self.roi_target.setVisible(show)

    def move_scale_roi_target(self, pos=None, size=None):
        """
        Move and scale the target ROI (used to displat a particular area, for instance the currently scanned points
        during a scan
        Parameters
        ----------
        pos: (iterable) precising the central position of the ROI in the view
        size: (iterable) precising the size of the ROI
        """
        if pos is not None:
            if self.roi_target.pos() != pos:
                self.roi_target.setPos(pos)
        if size is not None:
            if self.roi_target.size() != size:
                self.roi_target.setSize(size)

    def setup_widgets(self):
        vertical_layout = QtWidgets.QVBoxLayout()
        vertical_layout.setContentsMargins(5, 5, 5, 5)
        self.parent_widget.setLayout(vertical_layout)
        splitter_vertical = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        vertical_layout.addWidget(splitter_vertical)


        splitter_vertical.addWidget(self.toolbar)

        # ####### Graphs, ImageItem, Histograms ############
        self.graphs_widget = QtWidgets.QWidget()
        self.graphs_widget.setLayout(QtWidgets.QHBoxLayout())
        self.graphs_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.setupGraphs(self.graphs_widget.layout())
        splitter_vertical.addWidget(self.graphs_widget)


        self.plotitem.addItem(self.ROIselect)

        self.plotitem.addItem(self.roi_target)

        self.splitter_VLeft.splitterMoved[int, int].connect(self.move_right_splitter)
        self.splitter_VRight.splitterMoved[int, int].connect(self.move_left_splitter)

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
        self.image_widget.add_scaled_axis('left')
        self.image_widget.add_scaled_axis('bottom')
        self.splitter.addWidget(self.roi_manager.roiwidget)
        self.roi_manager.roiwidget.setVisible(False)

    def setup_actions(self):

        self.add_action('position', '(,)')
        self.add_action('red', 'Red Channel', 'r_icon', tip='Show/Hide Red Channel', checkable=True)
        self.add_action('green', 'Green Channel', 'g_icon', tip='Show/Hide Green Channel', checkable=True)
        self.add_action('blue', 'Blue Channel', 'b_icon', tip='Show/Hide Blue Channel', checkable=True)
        self.add_action('autolevels', 'AutoLevels', 'autoscale',
                        tip='Scale Histogram to Min/Max intensity', checkable=True)
        self.add_action('auto_levels_sym', 'AutoLevels Sym.', 'autoscale',
                        tip='Make the autoscale of the histograms symetric with respect to 0', checkable=True)

        self.add_action('histo', 'Histogram', 'Histogram', tip='Show/Hide Histogram', checkable=True)
        self.add_action('roi', 'ROI', 'Region', tip='Show/Hide ROI Manager', checkable=True)
        self.add_action('isocurve', 'IsoCurve', 'meshPlot', tip='Show/Hide Isocurve', checkable=True)
        self.add_action('aspect_ratio', 'Aspect Ratio', 'Zoom_1_1', tip='Fix Aspect Ratio', checkable=True)

        self.add_action('crosshair', 'CrossHair', 'reset', tip='Show/Hide data Crosshair', checkable=True)
        self.add_action('ROIselect', 'ROI Select', 'Select_24',
                        tip='Show/Hide ROI selection area', checkable=True)
        self.add_action('flip_ud', 'Flip UD', 'scale_vertically',
                        tip='Flip the image up/down', checkable=True)
        self.add_action('flip_lr', 'Flip LR', 'scale_horizontally',
                        tip='Flip the image left/right', checkable=True)
        self.add_action('rotate', 'Rotate', 'rotation2',
                        tip='Rotate the image', checkable=True)

    def connect_things(self):
        self.data_displayer.updated_item.connect(self.histogrammer.affect_histo_to_imageitems)
        self.connect_action('autolevels', self.data_displayer.set_autolevels)
        self.connect_action('histo', self.histogrammer.activated)
        self.connect_action('autolevels', self.histogrammer.set_autolevels)
        self.connect_action('isocurve', self.isocurver.show_hide_iso)
        self.connect_action('isocurve', self.get_action('histo').trigger)
        for key in IMAGE_TYPES:
            self.connect_action(key, self.notify_visibility_data_displayer)
        self.connect_action('aspect_ratio', self.lock_aspect_ratio)
        self.connect_action('histo', self.show_hide_histogram)
        self.connect_action('roi', self.lineout_plotter.roi_clicked)
        self.connect_action('roi', self.show_lineout_widgets)
        self.connect_action('ROIselect', self.show_ROI_select)
        self.connect_action('crosshair', self.show_hide_crosshair)
        self.connect_action('crosshair', self.show_lineout_widgets)
        self.connect_action('crosshair', self.lineout_plotter.crosshair_clicked)
        self.histogrammer.affect_histo_to_imageitems(self.data_displayer.get_images())

    def prepare_ui(self):
        self.ROIselect.setVisible(False)
        self.show_hide_crosshair(False)
        self.show_lineout_widgets()

    @Slot(utils.DataFromPlugins)
    def display_images(self, datas):
        self.data_displayer.update_data(datas)
        if self.is_action_checked('isocurve'):
            self.isocurver.set_isocurve_data(datas['data'][0])

    def display_roi_lineouts(self, roi_dict):
        self.lineout_plotter.plot_roi_lineouts(roi_dict)

    def display_crosshair_lineouts(self, crosshair_dict):
        self.lineout_plotter.plot_crosshair_lineouts(crosshair_dict)

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
        self.splitter_VRight.splitterMoved[int, int].emit(int(ratio * self.parent_widget.height()), 1)
        self.splitter.moveSplitter(int(ratio * self.parent_widget.width()), 1)
        self.splitter_VLeft.moveSplitter(int(ratio * self.parent_widget.height()), 1)
        self.splitter_VLeft.splitterMoved[int, int].emit(int(ratio * self.parent_widget.height()), 1)
        QtGui.QGuiApplication.processEvents()

    def get_view_range(self):
        return self.image_widget.view.viewRange()

    def get_data_at(self, name='red', xy=(0, 0)):
        return self.data_displayer.get_image(name).get_val_at(xy)

    def lock_aspect_ratio(self):
        lock = self.is_action_checked('aspect_ratio')
        self.plotitem.vb.setAspectLocked(lock=lock, ratio=1)

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

    def get_double_clicked(self):
        return self.image_widget.view.sig_double_clicked

    def get_axis(self, position='left'):
        if position not in AXIS_POSITIONS:
            raise KeyError(f'{position} is not a possible position for Axis: {AXIS_POSITIONS}')
        return self.image_widget.getAxis(position)

    @property
    def plotitem(self):
        return self.image_widget.plotitem

    def get_crosshair_signal(self):
        """Convenience function from the Crosshair"""
        return self.crosshair.crosshair_dragged

    def get_crosshair_position(self):
        """Convenience function from the Crosshair"""
        return self.crosshair.get_positions()

    def set_crosshair_position(self, *positions):
        """Convenience function from the Crosshair"""
        self.crosshair.set_crosshair_position(*positions)

    @Slot(bool)
    def show_hide_crosshair(self, show=True):
        self.crosshair.setVisible(show)
        self.set_action_visible('position', show)
        self.crosshair.setVisible(show)
        if show:
            range = self.get_view_range()
            self.set_crosshair_position(np.mean(np.array(range[0])), np.mean(np.array(range[0])))
        logger.debug(f'Crosshair visible?: {self.crosshair.isVisible()}')

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
        return axis.axis_label, axis.axis_units


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
        x_offset, x_scaling, y_offset, y_scaling = self._get_axis_scaling_offset()
        return xaxis * x_scaling + x_offset, yaxis * y_scaling + y_offset

    def unscale_axis(self, xaxis, yaxis):
        x_offset, x_scaling, y_offset, y_scaling = self._get_axis_scaling_offset()
        return (xaxis - x_offset) / x_scaling, (yaxis - y_offset) / y_scaling

    def _get_axis_scaling_offset(self):
        x_offset = self.get_axis('top').axis_offset
        x_scaling = self.get_axis('top').axis_scaling
        y_offset = self.get_axis('right').axis_offset
        y_scaling = self.get_axis('right').axis_scaling
        return x_offset, x_scaling, y_offset, y_scaling


class Viewer2D(ViewerBase):
    crosshair_clicked = Signal(bool)
    ROI_select_signal = Signal(QtCore.QRectF)
    convenience_attributes = ('is_action_checked', 'is_action_visible', 'set_action_checked', 'set_action_visible',
                              'get_action', 'ROIselect', 'addAction', 'toolbar', 'crosshair', 'histogrammer',
                              'image_widget', 'scale_axis', 'unscale_axis', 'roi_manager', 'show_roi_target',
                              'move_scale_roi_target', 'get_data_at')

    def __init__(self, parent=None, title=''):
        super().__init__(parent, title)

        self._datas = None
        self.isdata = dict([])
        self._is_gradient_manually_set = False

        self.view = View2D(parent)

        self.filter_from_rois = FilterFromRois(self.view.roi_manager, self.view.data_displayer.get_image('red'),
                                               IMAGE_TYPES)
        self.filter_from_rois.register_activation_signal(self.view.get_action('roi').triggered)
        self.filter_from_rois.register_target_slot(self.process_roi_lineouts)

        self.filter_from_crosshair = FilterFromCrosshair(self.view.crosshair, self.view.data_displayer.get_images(),
                                                         IMAGE_TYPES)
        self.filter_from_crosshair.register_activation_signal(self.view.get_action('crosshair').triggered)
        self.filter_from_crosshair.register_target_slot(self.process_crosshair_lineouts)

        self.prepare_connect_ui()

        self.add_attributes_from_view()

    @Slot(dict)
    def roi_changed(self):
        self.filter_from_rois.filter_data(self._datas)

    def crosshair_changed(self):
        self.filter_from_crosshair.filter_data(self._datas)

    def setImage(self, data_red=None, data_green=None, data_blue=None, data_spread=None):
        pymodaq.daq_utils.messenger.deprecation_msg(f'setImage for PyMoDAQ Viewer2D is deprecated, use *show_data* with'
                                                    f'one argument as utils.DataFromPlugins', stacklevel=3)
        datas = self.format_data_as_datafromplugins(data_red=data_red, data_green=data_green,
                                                    data_blue=data_blue, data_spread=data_spread)
        self.show_data(datas)

    def setImageTemp(self, data_red=None, data_green=None, data_blue=None, data_spread=None):
        pymodaq.daq_utils.messenger.deprecation_msg(f'setImageTemp for PyMoDAQ Viewer2D is deprecated, use *show_data_temp* with'
                         f'one argument as utils.DataFromPlugins')
        datas = self.format_data_as_datafromplugins(data_red=data_red, data_green=data_green,
                                                    data_blue=data_blue, data_spread=data_spread)
        self.show_data_temp(datas)

    @staticmethod
    def format_data_as_datafromplugins(data_red=None, data_green=None, data_blue=None, data_spread=None):
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
        return datas

    def set_gradient(self, image_key, gradient):
        """convenience function"""
        self.view.histogrammer.set_gradient(image_key, 'grey')

    def _show_data(self, datas: utils.DataFromPlugins):
        """
        numpy arrays to be plotted and eventually filtered using ROI...
        Parameters
        ----------
        datas: (utils.DataToExport)

        """

        if len(datas['data']) == 1 and not self._is_gradient_manually_set:
            self.set_gradient('red', 'grey')

        self.isdata['red'] = len(datas['data']) > 0
        self.isdata['green'] = len(datas['data']) > 1
        self.isdata['blue'] = len(datas['data']) > 2

        self.set_visible_items()
        self.update_data()
        if not self.view.is_action_checked('roi'):
            self.data_to_export_signal.emit(self.data_to_export)

    def update_data(self):
        if self._raw_datas is not None:
            self._datas = self.set_image_transform()
            self._data_to_show_signal.emit(self._datas)

            if self.view.is_action_checked('roi'):
                self.roi_changed()

            if self.view.is_action_checked('crosshair'):
                self.crosshair_changed()


    def set_image_transform(self):
        """
        Deactivate some tool buttons if data type is "spread" then apply transform_image
        """
        data = copy.deepcopy(self._raw_datas)
        self.view.set_action_visible('flip_ud', data['distribution'] != 'spread')
        self.view.set_action_visible('flip_lr', data['distribution'] != 'spread')
        self.view.set_action_visible('rotate', data['distribution'] != 'spread')
        if data['distribution'] != 'spread':
            for ind_data in range(len(data['data'])):
                data['data'][ind_data] = self.transform_image(data['data'][ind_data])
        return data

    def transform_image(self, data):
        if self.view.is_action_checked('flip_ud'):
            data = np.flipud(data)
        if self.view.is_action_checked('flip_lr'):
            data = np.fliplr(data)
        if self.view.is_action_checked('rotate'):
            data = np.flipud(np.transpose(data))
        return data

    def set_visible_items(self):
        for key in IMAGE_TYPES:
            if self.view.is_action_checked(key) and not self.isdata[key]:  # turn it off if it was on but there is no data
                self.view.set_action_checked(key, False)
                self.view.set_action_visible(key, False)

            elif self.isdata[key]:
                self.view.set_action_checked(key, True)
                self.view.set_action_visible(key, True)

            self.view.notify_visibility_data_displayer()

    def show_roi(self, show=True, show_roi_widget=True):
        """convenience function to control roi"""
        if show == (not self.is_action_checked('roi')):
            self.get_action('roi').trigger()

        self.view.roi_manager.roiwidget.setVisible(show_roi_widget)

    def update_crosshair_data(self, crosshair_dict):
        try:
            posx, posy = self.view.get_crosshair_position()
            (posx_scaled, posy_scaled) = self.view.scale_axis(posx, posy)

            dat = f'({posx_scaled:.1e}{posy_scaled:.1e})\n'
            for image_key in IMAGE_TYPES:
                if self.view.is_action_checked(image_key):
                    dat += f' {image_key[0]}:{crosshair_dict[image_key].int_data:.1e}\n'

            self.view.set_action_text('position', dat)

        except Exception as e:
            print(e)

    def prepare_connect_ui(self):
        self.view.ROIselect.sigRegionChangeFinished.connect(self.selected_region_changed)

        self.view.connect_action('flip_ud', slot=self.update_data)
        self.view.connect_action('flip_lr', slot=self.update_data)
        self.view.connect_action('rotate', slot=self.update_data)
        self.view.connect_action('autolevels', slot=self.update_data)
        self.view.connect_action('isocurve', slot=self.update_data)
        self.view.histogrammer.gradient_changed.connect(lambda: setattr(self, '_is_gradient_manually_set', True))

        self._data_to_show_signal.connect(self.view.display_images)
        self.view.lineout_plotter.roi_changed.connect(self.roi_changed)
        self.view.get_crosshair_signal().connect(self.crosshair_changed)

        self.view.get_double_clicked().connect(self.double_clicked)

    def selected_region_changed(self):
        if self.view.is_action_checked('ROIselect'):
            pos = self.view.ROIselect.pos()
            size = self.view.ROIselect.size()
            self.ROI_select_signal.emit(QtCore.QRectF(pos[0], pos[1], size[0], size[1]))

    @Slot(float, float)
    def double_clicked(self, posx, posy):
        if self.view.is_action_checked('crosshair'):
            self.view.crosshair.set_crosshair_position(posx, posy)
            self.crosshair_changed()
        self.sig_double_clicked.emit(posx, posy)

    def set_scaling_axes(self, scaling_options: utils.ScalingOptions):
        """
        metod used to update the scaling of the right and top axes in order to translate pixels to real coordinates
        scaling_options=dict(scaled_xaxis=dict(label="",units=None,offset=0,scaling=1),scaled_yaxis=dict(label="",units=None,offset=0,scaling=1))
        """
        self.view.set_axis_scaling(position='top', **scaling_options['scaled_xaxis'])
        self.view.set_axis_scaling(position='right', **scaling_options['scaled_yaxis'])

        self.x_axis.linkedViewChanged(self.view.image_widget.view)
        self.y_axis.linkedViewChanged(self.view.image_widget.view)

    @property
    def x_axis(self):
        return self.view.get_axis('top')

    @x_axis.setter
    def x_axis(self, axis):
        scaling, offset, label, units = AxisInfosExtractor.extract_axis_info(axis)
        self.view.set_axis_scaling('top', scaling=scaling, offset=offset, label=label, units=units)

    @property
    def y_axis(self):
        return self.view.get_axis('right')

    @y_axis.setter
    def y_axis(self, axis):
        scaling, offset, label, units = AxisInfosExtractor.extract_axis_info(axis)
        self.view.set_axis_scaling('right', scaling=scaling, offset=offset, label=label, units=units)

    def scale_lineout_dicts(self, lineout_dicts):
        for lineout_data in lineout_dicts.values():
            lineout_data.hor_axis, lineout_data.ver_axis = \
                self.view.scale_axis(lineout_data.hor_axis, lineout_data.ver_axis)
        return lineout_dicts

    @Slot(dict)
    def process_crosshair_lineouts(self, crosshair_dict):
        self.view.display_crosshair_lineouts(self.scale_lineout_dicts(crosshair_dict))
        self.update_crosshair_data(crosshair_dict)
        self.crosshair_dragged.emit(*self.view.scale_axis(*self.view.crosshair.get_positions()))

    @Slot(dict)
    def process_roi_lineouts(self, roi_dict):
        roi_dict = self.scale_lineout_dicts(roi_dict)
        self.view.display_roi_lineouts(roi_dict)

        self.measure_data_dict = dict([])
        for roi_key, lineout_data in roi_dict.items():
            if not self._display_temporary:
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

            self.measure_data_dict[f'{roi_key}:'] = lineout_data.int_data

            QtWidgets.QApplication.processEvents()

        self.view.roi_manager.settings.child('measurements').setValue(self.measure_data_dict)
        if not self._display_temporary:
            self.data_to_export_signal.emit(self.data_to_export)
        self.ROI_changed.emit()




def main_controller():
    app = QtWidgets.QApplication(sys.argv)
    form = QtWidgets.QWidget()
    Nx = 100
    Ny = 200
    data_random = np.random.normal(size=(Ny, Nx))
    x = np.linspace(0, Nx - 1, Nx)
    y = np.linspace(0, Ny - 1, Ny)
    from pymodaq.daq_utils.daq_utils import gauss2D

    data_red = 3 * gauss2D(x, 0.2 * Nx, Nx / 5, y, 0.3 * Ny, Ny / 5, 1, 90) * np.sin(x/5)**2 + 0.1 * data_random
    # data_red = pg.gaussianFilter(data_red, (2, 2))
    data_green = 24 * gauss2D(x, 0.2 * Nx, Nx / 5, y, 0.3 * Ny, Ny / 5, 1, 0)
    # data_green = pg.gaussianFilter(data_green, (2, 2))
    data_green[70:80, 7:12] = np.nan

    data_blue = 10 * gauss2D(x, 0.7 * Nx, Nx / 5, y, 0.2 * Ny, Ny / 5, 1)
    data_blue = pg.gaussianFilter(data_blue, (2, 2))

    prog = Viewer2D(form)
    # prog.set_axis_scaling(scaling_options=utils.ScalingOptions(
    #     scaled_xaxis=utils.ScaledAxis(label="eV", units=None, offset=100, scaling=0.1),
    #     scaled_yaxis=utils.ScaledAxis(label="time", units='s', offset=-20, scaling=2)))
    form.show()
    #prog.auto_levels_action_sym.trigger()
    #prog.view.actions['autolevels'].trigger()

    data_spread = np.load('../../../resources/triangulation_data.npy')
    # data_shuffled = data
    # np.random.shuffle(data_shuffled)
    # prog.show_data(utils.DataFromPlugins(name='mydata', distribution='spread',
    #                                      data=[data, data_shuffled]))
    prog.view.get_action('histo').trigger()
    prog.view.get_action('autolevels').trigger()

    prog.show_data(utils.DataFromPlugins(name='mydata', distribution='uniform', data=[data_red, data_green]))
    #prog.show_data(utils.DataFromPlugins(name='mydata', distribution='spread', data=[data_spread]))

    #prog.ROI_select_signal.connect(print_roi_select)
    #prog.view.get_action('ROIselect').trigger()
    #prog.view.ROIselect.setSize((20, 35))
    #prog.view.ROIselect.setPos((45, 123))
    prog.show_roi_target(True)
    prog.move_scale_roi_target((50, 40), (20, 20))

    QtWidgets.QApplication.processEvents()

    # prog.setImage(data_spread=data)
    #app.processEvents()

    sys.exit(app.exec_())


def print_roi_select(rect):
    print(rect)


def main_view():
    app = QtWidgets.QApplication(sys.argv)
    form = QtWidgets.QWidget()
    prog = View2D(form)
    form.show()
    sys.exit(app.exec_())


if __name__ == '__main__':  # pragma: no cover

    #main_view()
    main_controller()

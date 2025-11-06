# -*- coding: utf-8 -*-
"""
Created the 03/11/2022

@author: Sebastien Weber
"""
from collections import OrderedDict
from pyqtgraph import PlotCurveItem
from qtpy.QtCore import QObject, Signal, Slot


from pymodaq_gui.plotting.utils.plot_utils import Data0DWithHistory
from pymodaq_gui.managers.roi_manager import ROIManager
from pymodaq_gui.plotting.items.crosshair import Crosshair
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import utils


logger = set_logger(get_module_name(__file__))
IMAGE_TYPES = ['red', 'green', 'blue']
COLOR_LIST = list(utils.plot_colors)
COLORS_DICT = dict(red=(255, 0, 0), green=(0, 255, 0), blue=(0, 0, 255), spread=(128, 128, 128))


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


class LineoutPlotter(QObject):
    """Base class to manage and display data filtered out into lineouts (1D, 0D)

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

    roi_changed = Signal(dict)
    crosshair_lineout_plotted = Signal(dict)
    roi_lineout_plotted = Signal(dict)

    lineout_widgets = ['int']  # should be reimplemented see viewer2D

    def __init__(self, graph_widgets: OrderedDict, roi_manager: ROIManager, crosshair: Crosshair):
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

        # for roi_key, lineout_data in roi_dicts.items():
        #     if roi_key in self._roi_curves:
        #         self._roi_curves[roi_key]['int'].setData(self.integrated_data.xaxis,
        #                                                  self.integrated_data.datas[roi_key])
        # self.plot_other_lineouts(roi_dicts)
        #
        # logger.debug('roi lineouts plotted')
        # self.roi_lineout_plotted.emit(roi_dicts)

    def plot_other_lineouts(self, roi_dicts):
        raise NotImplementedError

    def plot_crosshair_lineouts(self, crosshair_dict):
        self.plot_other_crosshair_lineouts(crosshair_dict)

        logger.debug('crosshair lineouts plotted')
        self.crosshair_lineout_plotted.emit(crosshair_dict)

    def plot_other_crosshair_lineouts(self, crosshair_dict):
        raise NotImplementedError

    def get_lineout_widget(self, name):
        if name not in self.lineout_widgets:
            raise KeyError(f'The lineout_widget reference should be within {self.lineout_widgets} not {name}')
        return self._lineout_widgets[name]

    @Slot(str, tuple)
    def update_roi(self, roi_key, param_changed):
        param, param_value = param_changed

        if param.name() == 'Color':
            if roi_key in self._roi_curves:
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
        item.sigRegionChangeFinished.connect(lambda: self.roi_changed.emit(self._roi_manager.ROIs))
        item_param = self._roi_manager.settings.child('ROIs', 'ROI_{:02d}'.format(newindex))
        color = item_param.child('Color').value()

        #self.add_roi_lineout_items(newindex, color)
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
            {curv_key: curve_item_factory(pen) for curv_key in self.lineout_widgets}
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
            self.get_lineout_widget(self.lineout_widgets[ind]).addItem(curve_item)

    def remove_lineout_items(self, *curve_items):
        """
        Remove Curve items sequentially to lineouts widgets: (hor, ver and int)
        Parameters
        ----------
        curve_items: (PlotCurveItem) at most 3 of them
        """

        for ind, curve_item in enumerate(curve_items):
            self.get_lineout_widget(self.lineout_widgets[ind]).removeItem(curve_item)

    @Slot(bool)
    def roi_clicked(self, isroichecked=True):
        self._roi_manager.roiwidget.setVisible(isroichecked)

        for k, roi in self._roi_manager.ROIs.items():
            roi.setVisible(isroichecked)
            for item in self.get_roi_curves_triplet()[k].values():
                item.setVisible(isroichecked)

    @Slot(bool)
    def crosshair_clicked(self, iscrosshairchecked=True):
        for image_key in IMAGE_TYPES:
            self.show_crosshair_curves(image_key, iscrosshairchecked)

    def get_roi_curves_triplet(self):
        """
        Get the dictionary (one key by ROI) containing dicts with ROI PlotCurveItem

        Example:
        --------
        >>> roi_dict_triplet = self.get_roi_cruves_triplet()
        >>> hor_curve = roi_dict_triplet['ROI_00']['hor']  # where 'hor' is an entry of self.lineout_widgets
        """
        return self._roi_curves

    def get_crosshair_curves_triplet(self):
        """
        Get the dictionary (one key by ImageItem, see IMAGE_TYPES) containing dicts with PlotCurveItem

        Example:
        --------
        >>> crosshair_dict_triplet = self.get_crosshair_curves_triplet()
        >>> hor_curve = crosshair_dict_triplet['blue']['hor']  # where 'hor' is an entry of self.lineout_widgets
        """
        return self._crosshair_curves

    def get_crosshair_curve_triplet(self, curve_name):
        return self._crosshair_curves[curve_name]

    def setup_crosshair(self):
        """to reimplement if needed"""
        pass

    def show_crosshair_curves(self, curve_key, show=True):
        """to reimplement if needed"""
        pass

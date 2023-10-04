import numpy as np
from pyqtgraph.parametertree import Parameter
from qtpy import QtCore, QtWidgets, QtGui
from qtpy.QtCore import QPointF, Slot, Signal, QObject
from typing import List, Tuple

from pyqtgraph import LinearRegionItem

from pymodaq.utils import data as data_mod
from pymodaq.utils import daq_utils as utils
from pymodaq.utils import math_utils as mutils
from pymodaq.utils.managers.roi_manager import ROIManager, LinearROI, RectROI
from pymodaq.utils.plotting.items.crosshair import Crosshair
from pymodaq.utils.plotting.items.image import UniformImageItem
from pymodaq.utils.plotting.data_viewers.viewer1Dbasic import Viewer1DBasic
from pymodaq.utils.logger import set_logger, get_module_name


from pymodaq.post_treatment.process_to_scalar import DataProcessorFactory


logger = set_logger(get_module_name(__file__))


data_processors = DataProcessorFactory()


class Filter:

    def __init__(self):
        self._is_active = False
        self._slot_to_send_data = None

    def register_activation_signal(self, activation_signal):
        activation_signal.connect(lambda x: self.set_active(x))

    def register_target_slot(self, slot):
        self._slot_to_send_data = slot

    @Slot(bool)
    def set_active(self, activate=True):
        self._is_active = activate

    def filter_data(self, data: data_mod.DataFromPlugins):
        if self._is_active:
            filtered_data = self._filter_data(data)
            if filtered_data is not None and self._slot_to_send_data is not None:
                self._slot_to_send_data(filtered_data)

    def _filter_data(self, data: data_mod.DataFromPlugins):
        raise NotImplementedError


class Filter1DFromCrosshair(Filter):
    def __init__(self, crosshair: Crosshair):
        """
        Extract data along a crosshair using coordinates and data displayed in graph_items such as  imageItems
        Parameters
        ----------
        crosshair : Crosshair
        """
        super().__init__()
        self.crosshair = crosshair
        self._x, self._y = 0., 0.
        self._axis: data_mod.Axis = None

    def update_axis(self, axis: data_mod.Axis):
        self._axis = axis

    def _filter_data(self, data: data_mod.DataFromPlugins):
        data_dict = dict([])
        if data is not None:
            axis = data.get_axis_from_index(0, create=False)[0]
            if axis is not None:
                self.update_axis(axis)

                self._x, self._y = self.crosshair.get_positions()
                ind_x = self._axis.find_index(self._x)
                for label, dat in zip(data.labels, data.data):
                    data_dict[label] = dict(pos=self._axis.get_data()[ind_x], value=dat[ind_x])
        return data_dict


class Filter2DFromCrosshair(Filter):
    def __init__(self, crosshair: Crosshair, graph_items, image_keys):
        """
        Extract data along a crosshair using coordinates and data displayed in graph_items such as  imageItems
        Parameters
        ----------
        crosshair : (Crosshair)
        graph_items : (dict)
        image_keys : (list) list of string identifier to link datas to their graph_items. This means that in
            _filter_data, datas['data'][key] is plotted on graph_items[key] for key in image_keys
        """
        super().__init__()
        self._graph_items = graph_items
        self._image_keys = image_keys
        self.crosshair = crosshair
        self._x, self._y = 0., 0.

    def set_graph_items(self, graph_items):
        self._graph_items = graph_items

    @Slot(bool)
    def set_active(self, activate=True):
        self._is_active = activate
        if activate:
            self.crosshair.crosshair_dragged.emit(*self.crosshair.get_positions())

    def _filter_data(self, datas: data_mod.DataFromPlugins):
        data_dict = dict([])
        if datas is not None:
            self._x, self._y = self.crosshair.get_positions()
            data_type = datas.distribution
            for data_index in range(len(self._image_keys)):
                if data_index < len(datas.data):
                    data = datas.data[data_index]
                    image_type = self._image_keys[data_index]
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
        if 0 <= H_indexes[0] < len(ver_axis):
            hor_data = data[H_indexes]
        else:
            out_of_bounds = True
            hor_data = np.zeros(hor_axis.shape)
        if 0 <= V_indexes[1] < len(hor_axis):
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

        points, data = self._graph_items[data_key].get_points_at(axis='x', val=posx)
        y_sorted_indexes = np.argsort(points[:, 1])
        ver_axis = points[y_sorted_indexes, 1][data_V_index]

        ver_data = data[y_sorted_indexes][data_V_index]

        return LineoutData(hor_axis=hor_axis, ver_axis=ver_axis, hor_data=hor_data, ver_data=ver_data,
                           int_data=self._graph_items[data_key].get_val_at((posx, posy)))

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
        point = self._graph_items[item_key].mapFromView(QPointF(x, y))
        return point.x(), point.y()


class Filter1DFromRois(Filter):
    """

    Parameters
    ----------
    roi_manager:ROIManager
    graph_item: PlotItems
    """
    def __init__(self, roi_manager: ROIManager):

        super().__init__()
        self._roi_settings = roi_manager.settings
        self._ROIs = roi_manager.ROIs
        self._axis: data_mod.Axis = None

    def update_axis(self, axis: data_mod.Axis):
        self._axis = axis

    def _filter_data(self, data: data_mod.DataFromPlugins) -> dict:
        data_dict = dict([])
        try:
            axis = data.get_axis_from_index(0, create=False)[0]
            if axis is not None:
                self.update_axis(axis)
            if data is not None:
                for roi_key, roi in self._ROIs.items():
                    try:
                        data_index = data.labels.index(self._roi_settings['ROIs', roi_key, 'use_channel'])
                    except ValueError:
                        data_index = 0
                    data_dict[roi_key] = self.get_data_from_roi(roi, self._roi_settings.child('ROIs', roi_key),
                                                                data, data_index)
        except Exception as e:
            pass
        return data_dict

    def get_data_from_roi(self, roi: LinearROI,  roi_param: Parameter, data: data_mod.DataWithAxes, data_index=0):
        if data is not None:
            _slice = self.get_slice_from_roi(roi, data)
            sub_data = data.isig[_slice]
            if sub_data.size != 0:
                processed_data = data_processors.get(roi_param['math_function']).process(sub_data)
            else:
                processed_data = None
            if processed_data is None:
                return LineoutData()
            else:
                if len(sub_data.axes) == 0:
                    pass
                return LineoutData(hor_axis=sub_data.axes[0], hor_data=sub_data.data[data_index],
                                   int_data=processed_data.data[data_index])

    def get_slice_from_roi(self, roi: RectROI, data: data_mod.DataWithAxes) -> slice:
        ind_x_min, ind_x_max = data.get_axis_from_index(data.sig_indexes[0])[0].find_indexes(roi.getRegion())
        size = data.get_axis_from_index(0)[0].size
        ind_x_min = int(min(max(ind_x_min, 0), size))
        ind_x_max = int(max(0, min(ind_x_max, size)))
        return slice(ind_x_min, ind_x_max)


class Filter2DFromRois(Filter):
    """Filters 2D data using 2D ROIs

    Parameters
    ----------
    roi_manager: ROIManager
    graph_item: UniformImageItem or SpreadImageItem
        The graphical item where data and ROIs are plotted
    image_keys : (list) list of string identifier to link datas to their graph_items. This means that in
        _filter_data, datas.data[key] is plotted on graph_items[key] for key in image_keys
    """
    def __init__(self, roi_manager: ROIManager, graph_item: UniformImageItem, image_keys):

        super().__init__()
        self._roi_settings = roi_manager.settings
        self._image_keys = image_keys
        self._graph_item = graph_item
        self.axes = (0, 1)
        self._ROIs = roi_manager.ROIs

    def _filter_data(self, data: data_mod.DataFromPlugins) -> dict:
        data_dict = dict([])
        try:
            if data is not None:
                for roi_key, roi in self._ROIs.items():
                    image_key = self._roi_settings['ROIs', roi_key, 'use_channel']
                    image_index = self._image_keys.index(image_key)

                    sub_data = data.deepcopy()
                    sub_data.data = [data[image_index]]
                    data_dict[roi_key] = self.get_xydata_from_roi(roi, sub_data,
                                                                  self._roi_settings['ROIs', roi_key, 'math_function'])
        except Exception as e:
            pass
        return data_dict

    def get_slices_from_roi(self, roi: RectROI, data: data_mod.DataWithAxes) -> Tuple[slice]:
        x, y = roi.pos().x(), roi.pos().y()
        width, height = roi.size().x(), roi.size().y()
        size_x = data.get_axis_from_index(1)[0].size
        size_y = data.get_axis_from_index(0)[0].size
        ind_x_min = int(min(max(x, 0), size_x))
        ind_y_min = int(min(max(y, 0), size_y))
        ind_x_max = int(max(0, min(x+width, size_x)))
        ind_y_max = int(max(0, min(y+height, size_y)))

        return slice(ind_y_min,ind_y_max), slice(ind_x_min, ind_x_max)

    def get_xydata_from_roi(self, roi, data: data_mod.DataWithAxes, math_function: str):

        if data is not None:
            if data.distribution.name == 'spread':
                xvals, yvals, data = self.get_xydata_spread(data, roi)
                ind_xaxis = np.argsort(xvals)
                ind_yaxis = np.argsort(yvals)
                xvals = xvals[ind_xaxis]
                yvals = yvals[ind_yaxis]
                data_H = data[ind_xaxis]
                data_V = data[ind_yaxis]
                int_data = np.array([np.mean(data)])
                math_data = int_data
            else:
                xvals, yvals, data_array = self.get_xydata(data.data[0], roi)
                slices = self.get_slices_from_roi(roi, data)
                sub_data = data.isig[slices[0], slices[1]]
                data_H = np.mean(data_array, axis=0)
                data_V = np.mean(data_array, axis=1)
                int_data = np.array([np.mean(data_array)])
                math_data = data_processors.get(math_function).process(sub_data).data

            return LineoutData(hor_axis=xvals, ver_axis=yvals, hor_data=data_H, ver_data=data_V, int_data=int_data,
                               math_data=math_data)

    def get_xydata(self, data: np.ndarray, roi: RectROI):
        data, coords = self.data_from_roi(data, roi)

        if data is not None:
            xvals = np.linspace(np.min(np.min(coords[1, :, :])), np.max(np.max(coords[1, :, :])),
                                data.shape[1])
            yvals = np.linspace(np.min(np.min(coords[0, :, :])), np.max(np.max(coords[0, :, :])),
                                data.shape[0])
        else:
            xvals = yvals = data = np.array([])
        return xvals, yvals, data

    def data_from_roi(self, data, roi):
        data, coords = roi.getArrayRegion(data, self._graph_item, self.axes, returnMappedCoords=True)
        return data, coords

    def get_xydata_spread(self, data, roi):
        xvals = []
        yvals = []
        data_out = []
        for ind in range(data.shape[0]):
            # invoke the QPainterpath of the ROI (from the shape method)
            if roi.shape().contains(QPointF(data.get_axis_from_index(0)[0].get_data()[ind] - roi.pos().x(),
                                            data.get_axis_from_index(0)[1].get_data()[ind] - roi.pos().y())):
                xvals.append(data.get_axis_from_index(0)[0].get_data()[ind])
                yvals.append(data.get_axis_from_index(0)[1].get_data()[ind])
                data_out.append(data[0][ind])
        data_out = np.array(data_out)
        xvals = np.array(xvals)
        yvals = np.array(yvals)
        return xvals, yvals, data_out


class LineoutData:
    def __init__(self, hor_axis=np.array([]), ver_axis=np.array([]), hor_data=np.array([]), ver_data=np.array([]),
                 int_data: np.ndarray = None, math_data: List[np.ndarray] = None):
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
        if math_data is None:
            math_data = self.int_data
        self.math_data = math_data


class FourierFilterer(QObject):
    filter_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__()
        if parent is None:
            parent = QtWidgets.QWidget()

        self.parent = parent

        self.raw_data = None
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

        self.viewer1D.ROI = LinearRegionItem(values=[0, 100])
        self.viewer1D.plotwidget.plotItem.addItem(self.viewer1D.ROI)
        self.data_filtered_plot = self.viewer1D.plotwidget.plotItem.plot()
        self.data_filtered_plot.setPen('w')
        self.viewer1D.ROI.sigRegionChangeFinished.connect(self.set_data)

        self.viewer1D.ROIfft = LinearRegionItem()
        self.viewer1D.plotwidget.plotItem.addItem(self.viewer1D.ROIfft)
        self.viewer1D.ROIfft.sigRegionChangeFinished.connect(self.update_filter)

        self.parent.show()

    def calculate_fft(self):

        ftaxis, axis = mutils.ftAxis_time(len(self.xaxis), np.max(self.xaxis) - np.min(self.xaxis))
        self.xaxisft = ftaxis / (2 * np.pi)
        self.data_fft = mutils.ft(self.data)

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
        except Exception as e:
            logger.exception(str(e))

    def set_data(self):
        xlimits = self.viewer1D.ROI.getRegion()
        indexes = mutils.find_index(self.raw_data['xaxis'], xlimits)
        self.data = self.raw_data['data'][indexes[0][0]:indexes[1][0]]
        self.xaxis = self.raw_data['xaxis'][indexes[0][0]:indexes[1][0]]
        try:
            self.calculate_fft()
        except Exception as e:
            logger.exception(str(e))
        self.viewer1D.x_axis = self.xaxis
        self.update_plot()

    def update_filter(self):
        try:
            xmin, xmax = self.viewer1D.ROIfft.getRegion()
            self.filter = mutils.gauss1D(self.xaxisft, np.mean([xmin, xmax]), xmax - xmin)
            self.data = np.real(mutils.ift(self.filter * self.data_fft))
            index = np.argmax(self.filter * self.data_fft)
            self.frequency = self.xaxisft[index]
            self.phase = np.angle(self.data_fft[index])

            self.filter_changed.emit(dict(frequency=self.frequency, phase=self.phase))
            self.update_plot()
        except Exception as e:
            logger.exception(str(e))

    def update_plot(self):

        if self.fftbutton1D.isChecked():
            if self.data_fft is not None:
                if self.filter is not None:
                    self.viewer1D.show_data([np.abs(self.data_fft), np.max(np.abs(self.data_fft)) * self.filter])
                else:
                    self.viewer1D.show_data([np.abs(self.data_fft)])
                self.viewer1D.x_axis = dict(data=self.xaxisft, label='freq.')
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
    import sys

    app = QtWidgets.QApplication(sys.argv)
    prog = FourierFilterer()

    from pymodaq.utils.daq_utils import gauss1D

    xdata = np.linspace(0, 400, 401)
    x0 = 50
    dx = 20
    tau = 27
    tau2 = 100
    ydata_gauss = 10 * gauss1D(xdata, x0, dx) + np.random.rand(len(xdata))
    ydata_expodec = np.zeros((len(xdata)))
    ydata_expodec[:50] = 10 * gauss1D(xdata[:50], x0, dx, 2)
    ydata_expodec[50:] = 10 * np.exp(-(xdata[50:] - x0) / tau)  # +10*np.exp(-(xdata[50:]-x0)/tau2)
    ydata_expodec += 2 * np.random.rand(len(xdata))
    ydata_sin = 10 + 2 * np.sin(2 * np.pi * 0.1 * xdata - np.deg2rad(55)) + np.sin(
        2 * np.pi * 0.008 * xdata - np.deg2rad(-10)) + 2 * np.random.rand(len(xdata))

    prog.show_data(dict(data=ydata_sin, xaxis=xdata))
    sys.exit(app.exec_())
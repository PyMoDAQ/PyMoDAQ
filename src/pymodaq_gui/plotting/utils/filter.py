import numpy as np
from pyqtgraph.parametertree import Parameter
from qtpy import QtCore, QtWidgets, QtGui
from qtpy.QtCore import QPointF, Slot, Signal, QObject
from typing import List, Tuple

from pyqtgraph import LinearRegionItem

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import utils
from pymodaq_utils import math_utils as mutils

from pymodaq_data.data import DataFromRoi, DataToExport, Axis, DataWithAxes
from pymodaq_data import data as data_mod
from pymodaq_data.post_treatment.process_to_scalar import DataProcessorFactory

from pymodaq_gui.managers.roi_manager import ROIManager, LinearROI, RectROI
from pymodaq_gui.plotting.items.crosshair import Crosshair
from pymodaq_gui.plotting.items.image import UniformImageItem
from pymodaq_gui.plotting.data_viewers.viewer1Dbasic import Viewer1DBasic


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

    def filter_data(self, data: data_mod.DataRaw):
        if self._is_active:
            filtered_data = self._filter_data(data)
            if filtered_data is not None and self._slot_to_send_data is not None:
                self._slot_to_send_data(filtered_data)

    def _filter_data(self, data: data_mod.DataRaw) -> DataToExport:
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

    def _filter_data(self, data: data_mod.DataRaw) -> DataToExport:
        dte = DataToExport('Crosshair')
        if data is not None:
            axis = data.get_axis_from_index(0, create=False)[0]
            if axis is not None:
                self.update_axis(axis)

                self._x, self._y = self.crosshair.get_positions()
                dwa = data.isig[data.axes[0].find_indexes([self._x])[0]]
                dwa.axes = [Axis('x', data=np.array([self._x]))]
                dte.append(dwa)
                # for label, dat in zip(data.labels, data.data):
                # dte.append(DataFromRoi('crosshair', data=[np.array([dat[ind_x]]) for dat in data.data],
                #                        axes=[Axis(data=np.array([self._axis.get_data()[ind_x]]))],
                #                        labels=data.labels))
        return dte


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

    def _filter_data(self, dwa: data_mod.DataRaw) -> DataToExport:
        dte = DataToExport('Crosshair')
        if dwa is not None:
            self._x, self._y = self.crosshair.get_positions()
            data_type = dwa.distribution
            if data_type == 'uniform':
                dte = self.get_data_from_uniform(dwa)
            elif data_type == 'spread':
                dte = self.get_data_from_spread(dwa)
        return dte

    def get_data_from_uniform(self, dwa: DataWithAxes) -> DataToExport:
        indx, indy = self.mapfromview(self._x, self._y, 'red')

        data_H_index = slice(None, None, 1)
        data_V_index = slice(None, None, 1)
        H_indexes = (utils.rint(indy), data_H_index)
        V_indexes = (data_V_index, utils.rint(indx))
        dte = DataToExport('Crosshair')
        try:
            if not (0 <= utils.rint(indy) < dwa.shape[0]):
                raise IndexError
            dwa_hor = dwa.isig[H_indexes]
            dwa_hor.labels = [f'Crosshair/{label}' for label in dwa_hor.labels]
            dwa_hor.name = 'hor'
            dte.append(dwa_hor)
        except IndexError:
            pass
        try:
            if not (0 <= utils.rint(indx) < dwa.shape[1]):
                raise IndexError
            dwa_ver = dwa.isig[V_indexes]
            dwa_ver.labels = [f'Crosshair/{label}' for label in dwa_ver.labels]
            dwa_ver.name = 'ver'
            dte.append(dwa_ver)
        except IndexError:
            pass
        try:
            if not (0 <= utils.rint(indy) < dwa.shape[0]) \
                or \
                    not (0 <= utils.rint(indx) < dwa.shape[1]):
                raise IndexError
            dwa_int = dwa.isig[utils.rint(indy), utils.rint(indx)]
            dwa_int.labels = [f'Crosshair/{label}' for label in dwa_int.labels]
            dwa_int.name = 'int'
            dte.append(dwa_int)
        except IndexError:
            pass
        return dte

    def get_data_from_spread(self, dwa: DataWithAxes) -> DataToExport:

        data_H_index = slice(None, None, 1)
        data_V_index = slice(None, None, 1)
        posx, posy = self.mapfromview(self._x, self._y, 'red')

        hor_data = []
        ver_data = []
        int_data = []
        hor_axis = None
        ver_axis = None

        for ind, data_key in enumerate(self._graph_items):
            if ind < len(dwa):
                points, data = self._graph_items[data_key].get_points_at(axis='y', val=posy)
                x_sorted_indexes = np.argsort(points[:, 0])
                hor_axis = points[x_sorted_indexes, 0][data_H_index]

                hor_data.append(data[x_sorted_indexes][data_H_index])

                points, data = self._graph_items[data_key].get_points_at(axis='x', val=posx)
                y_sorted_indexes = np.argsort(points[:, 1])
                ver_axis = points[y_sorted_indexes, 1][data_V_index]

                ver_data.append(data[y_sorted_indexes][data_V_index])

                int_data.append(np.array([self._graph_items[data_key].get_val_at((posx, posy))]))

        dte = DataToExport('Crosshair')
        if len(hor_data) > 0 and len(hor_axis) > 0:
            dte.append(DataFromRoi('hor', data=hor_data,
                                   axes=[Axis(dwa.axes[1].label, dwa.axes[1].units, data=hor_axis)]),)
        if len(ver_data) > 0 and len(ver_axis) > 0:
            dte.append(DataFromRoi('ver', data=ver_data,
                                   axes=[Axis(dwa.axes[0].label, dwa.axes[0].units, data=ver_axis)]))
        if len(int_data) > 0:
            dte.append(DataFromRoi('int', data=int_data))

        return dte

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

    def _filter_data(self, data: data_mod.DataRaw) -> DataToExport:
        dte = DataToExport('roi1D')
        try:
            axis = data.get_axis_from_index(0, create=False)[0]
            if axis is not None:
                self.update_axis(axis)
            if data is not None:
                for roi_key, roi in self._ROIs.items():
                    if self._roi_settings['ROIs', roi_key, 'use_channel'] == 'All':
                        data_index = list(range(len(data.labels)))
                    else:
                        try:
                            data_index = [data.labels.index(self._roi_settings['ROIs', roi_key,
                                          'use_channel'])]
                        except ValueError:
                            data_index = [0]
                    dte_tmp = self.get_data_from_roi(roi, self._roi_settings.child('ROIs', roi_key),
                                                     data)
                    if self._roi_settings['ROIs', roi_key, 'use_channel'] == 'All':
                        dte.append(dte_tmp.data)
                    else:
                        for index in data_index:
                            for dwa in dte_tmp.data:
                                dte.append(dwa.pop(index))

        except Exception as e:
            pass
        finally:
            return dte

    def get_data_from_roi(self, roi: LinearROI,  roi_param: Parameter, data: data_mod.DataWithAxes) -> DataToExport:
        if data is not None:
            dte = DataToExport('ROI1D')
            _slice = self.get_slice_from_roi(roi, data)
            sub_data: DataFromRoi = data.isig[_slice]
            sub_data.name = 'HorData'
            sub_data.origin = roi_param.name()
            sub_data.labels = [f'{roi_param.name()}/{label}' for label in sub_data.labels]
            dte.append(sub_data)
            if sub_data.size != 0:
                processed_data = data_processors.get(roi_param['math_function']).process(sub_data)
            else:
                processed_data = None
            if processed_data is not None:
                processed_data.name = 'IntData'
                dte.append(processed_data)
            return dte

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

    def _filter_data(self, dwa: data_mod.DataRaw) -> DataToExport:
        dte = DataToExport('ROI')
        if dwa is not None:
            try:
                labels = []
                for roi_key, roi in self._ROIs.items():
                    label = self._roi_settings['ROIs', roi_key, 'use_channel']
                    if label is not None:
                        if label != 'All':
                            sub_data = dwa.deepcopy()
                            sub_data.data = [dwa[dwa.labels.index(label)]]
                            sub_data.labels = [label]
                        else:
                            sub_data = dwa
                        dte_temp = self.get_xydata_from_roi(roi, sub_data,
                                                            self._roi_settings['ROIs',
                                                            roi_key, 'math_function'])

                        dte.append(dte_temp)
            except Exception as e:
                logger.warning(f'Issue with the ROI: {str(e)}')
        return dte

    def get_slices_from_roi(self, roi: RectROI, data_shape: tuple) -> Tuple[slice, slice]:
        x, y = roi.pos().x(), roi.pos().y()
        width, height = roi.size().x(), roi.size().y()
        size_y, size_x = data_shape
        ind_x_min = int(min(max(x, 0), size_x))
        ind_y_min = int(min(max(y, 0), size_y))
        ind_x_max = int(max(0, min(x+width, size_x)))
        ind_y_max = int(max(0, min(y+height, size_y)))
        return slice(ind_y_min,ind_y_max), slice(ind_x_min, ind_x_max)

    def get_xydata_from_roi(self, roi: RectROI, dwa: DataWithAxes, math_function: str) -> DataToExport:
        dte = DataToExport(roi.name)
        if dwa is not None:
            labels = [f'{roi.name}/{label}' for label in dwa.labels]
            if dwa.distribution.name == 'spread':
                xvals, yvals, data = self.get_xydata_spread(dwa, roi)
                if len(data) == 0:
                    return dte
                ind_xaxis = np.argsort(xvals)
                ind_yaxis = np.argsort(yvals)
                xvals = xvals[ind_xaxis]
                yvals = yvals[ind_yaxis]
                data_H = data[ind_xaxis]
                data_V = data[ind_yaxis]
                int_data = np.array([np.mean(data)])

                _x_axis = dwa.get_axis_from_index_spread(0, 0)
                x_axis = Axis(_x_axis.label, _x_axis.units, data=xvals, index=0, spread_order=0)
                _y_axis = dwa.get_axis_from_index_spread(0, 1)
                y_axis = Axis(_y_axis.label, _y_axis.units, data=yvals, index=0, spread_order=0)
                sub_data_hor = DataFromRoi('hor', distribution='spread', data=[data_H], axes=[x_axis],)
                sub_data_ver = DataFromRoi('ver', distribution='spread', data=[data_V], axes=[y_axis])
                math_data = DataFromRoi('int', data=int_data)
            else:
                slices = self.get_slices_from_roi(roi, dwa.shape)
                sub_data: DataFromRoi = dwa.isig[slices[0], slices[1]]
                sub_data_hor = sub_data.mean(0)
                sub_data_ver = sub_data.mean(1)
                math_data = data_processors.get(math_function).process(sub_data)

            sub_data_hor.name = 'hor'
            sub_data_hor.origin = roi.name
            sub_data_hor.labels = labels
            sub_data_ver.name = 'ver'
            sub_data_ver.origin = roi.name
            sub_data_ver.labels = labels
            math_data.name = 'int'
            math_data.origin = roi.name
            math_data.labels = labels

            dte.append([sub_data_hor, sub_data_ver, math_data])
            return dte

    #TODO possibly not used anymore to be deleted
    #
    # def get_xydata(self, data: np.ndarray, roi: RectROI):
    #     data, coords = self.data_from_roi(data, roi)
    #
    #     if data is not None:
    #         xvals = np.linspace(np.min(np.min(coords[1, :, :])), np.max(np.max(coords[1, :, :])),
    #                             data.shape[1])
    #         yvals = np.linspace(np.min(np.min(coords[0, :, :])), np.max(np.max(coords[0, :, :])),
    #                             data.shape[0])
    #     else:
    #         xvals = yvals = data = np.array([])
    #     return xvals, yvals, data
    #
    # def data_from_roi(self, data, roi):
    #     data, coords = roi.getArrayRegion(data, self._graph_item, self.axes, returnMappedCoords=True)
    #     return data, coords

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
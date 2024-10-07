from abc import ABCMeta, abstractmethod, abstractproperty
import sys
from typing import List, Tuple, Union

import numpy as np

try:
    from scipy.spatial import QhullError  # works for newer version of scipy
    from scipy.spatial import Delaunay as Triangulation
except ImportError:
    from scipy.spatial.qhull import QhullError  # works for old version of scipy
    from scipy.spatial.qhull import Delaunay as Triangulation

from qtpy import QtWidgets
from qtpy.QtCore import QObject, Slot, Signal, QRectF, QPointF

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.utils.dock import DockArea, Dock
from pymodaq_gui.plotting.data_viewers.viewer1D import Viewer1D
from pymodaq_gui.plotting.utils.axes_viewer import AxesViewer
from pymodaq_gui.plotting.data_viewers.viewer2D import Viewer2D
from pymodaq_gui.plotting.data_viewers.viewer0D import Viewer0D
from pymodaq_utils import utils
from pymodaq_utils import math_utils as mutils
from pymodaq_data.data import DataRaw, Axis, DataDistribution, DataWithAxes, DataCalculated

from pymodaq_gui.plotting.data_viewers.viewer import ViewerBase
from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_data.post_treatment.process_to_scalar import DataProcessorFactory
from pymodaq_gui.managers.roi_manager import SimpleRectROI, LinearROI


logger = set_logger(get_module_name(__file__))
data_processors = DataProcessorFactory()

DEBUG_VIEWER = False


class BaseDataDisplayer(QObject):
    data_dim_signal = Signal(str)
    processor_changed = Signal(object)
    distribution: DataDistribution = abstractproperty()

    def __init__(self, viewer0D: Viewer0D, viewer1D: Viewer1D, viewer2D: Viewer2D, navigator1D: Viewer1D,
                 navigator2D: Viewer2D, axes_viewer: AxesViewer):
        super().__init__()
        self._viewer0D = viewer0D
        self._viewer1D = viewer1D
        self._viewer2D = viewer2D
        self._navigator1D = navigator1D
        self._navigator2D = navigator2D
        self._axes_viewer = axes_viewer

        self._data: DataWithAxes = None
        self._nav_limits: tuple = (0, 10, None, None)
        self._signal_at: tuple = (0, 0)

        self.triangulation = False

        self._filter_type: str = None
        self._processor = None

        self._show_nav_integration = False

    @property
    def data_shape(self):
        return self._data.shape if self._data is not None else None

    def update_filter(self, filter_type: str):
        if filter_type in self._processor.functions:
            self._filter_type = filter_type
            self.update_nav_data(*self._nav_limits)

    def update_processor(self, math_processor: DataProcessorFactory):
        self._processor = math_processor
        self.processor_changed.emit(math_processor)

    def update_data(self, data: DataRaw, force_update=False):
        if self._data is None or self._data.shape != data.shape or force_update:
            self._data = data
            self.init(data)
        else:
            self._data.data = data.data[0]

        self.data_dim_signal.emit(self._data.get_data_dimension())

        self.update_viewer_data(*self._signal_at)
        self.update_nav_data(*self._nav_limits)

    def show_nav_integration(self, show=True):
        self._show_nav_integration = show
        self.update_viewer_data(*self._signal_at)

    @abstractmethod
    def init_rois(self, data: DataRaw):
        """Init crosshairs and ROIs in viewers if needed"""
        ...

    @abstractmethod
    def init(self):
        """init viewers or postprocessing once new data are loaded"""
        ...

    @abstractmethod
    def update_viewer_data(self, **kwargs):
        """ Update the signal display depending on the position of the crosshair in the navigation panels

        """
        ...

    def updated_nav_integration(self):
        """ Means the ROI select of the 2D viewer has been moved """
        ...

    @abstractmethod
    def update_nav_data(self, x, y, width=None, height=None):
        """Display navigator data potentially postprocessed from filters in the signal viewers"""
        ...

    @abstractmethod
    def get_nav_data(self, data: DataWithAxes, x, y, width=None, height=None) -> DataWithAxes:
        """Get filtered data"""
        ...

    def update_nav_data_from_roi(self, roi: Union[SimpleRectROI, LinearROI]):
        if isinstance(roi, LinearROI):
            x, y = roi.getRegion()
            self._nav_limits = (x, y, None, None)
        elif isinstance(roi, SimpleRectROI):
            x, y = roi.pos().x(), roi.pos().y()
            width, height = roi.size().x(), roi.size().y()
            self._nav_limits = (int(x), int(y), int(width), int(height))
        self.update_nav_data(*self._nav_limits)

    @staticmethod
    def get_out_of_range_limits(x, y, width, height):
        if x < 0:
            width = width + x
            x = 0
        if y < 0:
            height = height + y
            y = 0
        return x, y, width, height

    def update_nav_indexes(self, nav_indexes: List[int]):
        self._data.nav_indexes = nav_indexes
        self.update_data(self._data, force_update=True)

    def update_nav_limits(self, x, y, width=None, height=None):
        self._nav_limits = x, y, width, height


class UniformDataDisplayer(BaseDataDisplayer):
    """Specialized object to filter and plot linearly spaced data in dedicated viewers

    Meant for any navigation axes and up to signal data dimensionality of 2 (images)
    """
    distribution = DataDistribution['uniform']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def init(self, data: DataRaw):
        if len(data.nav_indexes) > 2 or not data.check_axes_linear():
            self._axes_viewer.set_nav_viewers(self._data.get_nav_axes_with_data())
        processor: DataProcessorFactory = data_processors
        self.update_processor(processor)

    def init_rois(self, nav_axes_limits: List[Tuple[float, float]] = None,
                  sig_axis_limits: List[Tuple[float, float]] = None):

        if len(nav_axes_limits) == 1:
            self._navigator1D.crosshair.set_crosshair_position(np.mean(nav_axes_limits[0]))

        if len(nav_axes_limits) == 2:
            self._navigator2D.crosshair.set_crosshair_position(
                *self._navigator2D.view.unscale_axis(np.mean(nav_axes_limits[1]),
                                                     np.mean(nav_axes_limits[0]))
            )
        if len(sig_axis_limits) == 1:
            self._viewer1D.roi.setPos((float(np.mean(sig_axis_limits[0]) -
                                             np.abs(np.diff(sig_axis_limits[0]))[0] / 3),
                                       float(np.mean(sig_axis_limits[0]) +
                                             np.abs(np.diff(sig_axis_limits[0]))[0] / 3))
                                      )
        if len(sig_axis_limits) == 2:
            scaled_axes = np.array(self._viewer2D.view.unscale_axis(np.array(sig_axis_limits[1]),
                                                                    np.array(sig_axis_limits[0])))

            self._viewer2D.roi.setSize(
                float(np.diff(scaled_axes[0])[0]) / 3,
                float(np.diff(scaled_axes[1])[0]) / 3)

            self._viewer2D.roi.setPos(
                float(np.mean(scaled_axes[0])) - float(np.diff(scaled_axes[0])[0]) / 6,
                float(np.mean(scaled_axes[1])) - float(np.diff(scaled_axes[1])[0]) / 6)

    def updated_nav_integration(self):
        """ Means the ROI select of the 2D viewer has been moved """
        self.update_viewer_data(*self._signal_at)

    def update_viewer_data(self, posx=0, posy=0):
        """ Update the signal display depending on the position of the crosshair in the navigation panels

        Parameters
        ----------
        posx: float
            from the 1D or 2D Navigator crosshair or from one of the navigation axis viewer (in that case
            nav_axis tells from which navigation axis the position comes from)
        posy: float
            from the 2D Navigator crosshair
        """
        self._signal_at = posx, posy
        if self._data is not None:
            try:
                if len(self._data.nav_indexes) == 0:
                    data = self._data

                elif len(self._data.nav_indexes) == 1:
                    nav_axis = self._data.axes_manager.get_nav_axes()[0]
                    if posx < nav_axis.min() or posx > nav_axis.max():
                        return
                    ind_x = nav_axis.find_index(posx)
                    logger.debug(f'Getting the data at nav index {ind_x}')
                    data: DataCalculated = self._data.inav[ind_x]
                    if self._show_nav_integration:
                        if self._navigator1D.view.is_action_checked('ROIselect'):
                            x0, x1 = self._navigator1D.view.ROIselect.getRegion()
                            ind_x0 = max(0, int(nav_axis.find_index(x0)))
                            ind_x1 = min(int(nav_axis.max()), int(nav_axis.find_index(x1)))
                            data.append(self._data.inav[ind_x0:ind_x1].mean(axis=(nav_axis.index)))
                        else:
                            data.append(self._data.mean(axis=nav_axis.index))

                elif len(self._data.nav_indexes) == 2 and self._data.check_axes_linear():
                    nav_x = self._data.axes_manager.get_nav_axes()[1]
                    nav_y = self._data.axes_manager.get_nav_axes()[0]
                    if posx < nav_x.min() or posx > nav_x.max():
                        return
                    if posy < nav_y.min() or posy > nav_y.max():
                        return
                    ind_x = nav_x.find_index(posx)
                    ind_y = nav_y.find_index(posy)
                    logger.debug(f'Getting the data at nav indexes {ind_y} and {ind_x}')
                    data = self._data.inav[ind_y, ind_x]
                    if self._show_nav_integration:
                        if self._navigator2D.view.is_action_checked('ROIselect'):
                            ind_x0 = max(0, int(self._navigator2D.view.ROIselect.x()))
                            ind_y0 = max(0, int(self._navigator2D.view.ROIselect.y()))
                            ind_x1 = min(int(nav_x.max()), ind_x0 + int(self._navigator2D.view.ROIselect.size().x()))
                            ind_y1 = min(int(nav_y.max()), ind_y0 + int(self._navigator2D.view.ROIselect.size().y()))
                            data.append(self._data.inav[ind_y0:ind_y1, ind_x0:ind_x1].mean(axis=(nav_x.index, nav_y.index)))
                        else:
                            data.append(self._data.mean(axis=(nav_x.index, nav_y.index)))
                else:
                    data = self._data.inav.__getitem__(self._axes_viewer.get_indexes())

                if len(self._data.axes_manager.sig_shape) == 0:  # means 0D data, plot on 0D viewer
                    self._viewer0D.show_data(data)

                elif len(self._data.axes_manager.sig_shape) == 1:  # means 1D data, plot on 1D viewer
                    self._viewer1D.show_data(data)

                elif len(self._data.axes_manager.sig_shape) == 2:  # means 2D data, plot on 2D viewer
                    self._viewer2D.show_data(data)
                    if DEBUG_VIEWER:
                        x, y, width, height = self.get_out_of_range_limits(*self._nav_limits)
                        _data_sig = data.isig[y: y + height, x: x + width]
                        self._debug_viewer_2D.show_data(_data_sig)

            except Exception as e:
                logger.exception(str(e))

    def update_nav_data(self, x, y, width=None, height=None):
        if self._data is not None and self._filter_type is not None and len(self._data.nav_indexes) != 0:
            nav_data = self.get_nav_data(self._data, x, y, width, height)
            if nav_data is not None:
                nav_data.nav_indexes = ()  # transform nav axes in sig axes for plotting
                if len(nav_data.shape) < 2:
                    self._navigator1D.show_data(nav_data)
                elif len(nav_data.shape) == 2 and self._data.check_axes_linear():
                    self._navigator2D.show_data(nav_data)
                else:
                    self._axes_viewer.set_nav_viewers(self._data.get_nav_axes_with_data())

    def get_nav_data(self, data: DataRaw, x, y, width=None, height=None):
        try:
            navigator_data = None
            if len(data.axes_manager.sig_shape) == 0:  # signal data is 0D
                navigator_data = data.deepcopy()

            elif len(data.axes_manager.sig_shape) == 1:  # signal data is 1D
                indx, indy = data.get_axis_from_index(data.sig_indexes[0])[0].find_indexes((x, y))
                navigator_data = self._processor.get(self._filter_type).process(data.isig[indx:indy])

            elif len(data.axes_manager.sig_shape) == 2:  # signal data is 2D
                x, y, width, height = self.get_out_of_range_limits(x, y, width, height)
                if not (width is None or height is None or width < 2 or height < 2):
                    navigator_data = self._processor.get(self._filter_type).process(data.isig[y: y + height, x: x + width])
                else:
                    navigator_data = None
            else:
                navigator_data = None

            return navigator_data

        except Exception as e:
            logger.warning('Could not compute the mathematical function')
        finally:
            return navigator_data


class SpreadDataDisplayer(BaseDataDisplayer):
    """Specialized object to filter and plot non uniformly spaced data in dedicated viewers

    Meant for any navigation axes and up to signal data dimensionality of 2 (images)
    """
    distribution = DataDistribution['spread']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.triangulation = True

    def init(self, data: DataWithAxes):
        processor = data_processors  # if len(data.axes_manager.sig_shape) > 1 else math_processors1D
        self.update_processor(processor)

    def init_rois(self, nav_axes_limits: List[Tuple[float, float]] = None,
                  sig_axis_limits: List[Tuple[float, float]] = None):
        pass

    def update_viewer_data(self, posx=0, posy=0):
        """ Update the signal display depending on the position of the crosshair in the navigation panels

        Spread data can be customly represented using:
        if signal data is 0D:
            * A viewer 1D with non-linearly spaced data points (for 1 navigation axis)
            * A viewer 2D with its SpreadImage item (for 2 navigation axis)
            * A double panel: viewer for signal data and viewer 1D for all nav axes as a function of index in the data
        otherwise:
            * A double panel: viewer for signal data and viewer 1D for all nav axes as a function of index in the data
            series

        Parameters
        ----------
        posx: float
            from the 1D or 2D Navigator crosshair or from one of the navigation axis viewer (in that case
            nav_axis tells from which navigation axis the position comes from)
        posy: float
            from the 2D Navigator crosshair
        """
        self._signal_at = posx, posy

        if self._data is not None:
            try:
                nav_axes = sorted(self._data.get_nav_axes_with_data(), key=lambda axis: axis.spread_order)

                if len(nav_axes) == 1:
                    # signal data plotted as a function of nav_axes[0] so get the index corresponding to
                    # the position posx
                    ind_nav = nav_axes[0].find_index(posx)
                    data = self._data.inav[ind_nav]

                elif len(nav_axes) == 2 and self.triangulation:
                    # signal data plotted as a function of nav_axes[0] and nav_axes[1] so get the common
                    # index corresponding to the position posx and posy
                    ind_nav, x0, y0 = mutils.find_common_index(nav_axes[0].data, nav_axes[1].data, posx, posy)
                    data = self._data.inav[ind_nav]
                else:
                    # navigation plotted as a function of index all nav_axes so get the index corresponding to
                    # the position posx
                    data = self._data.inav[int(posx)]

                if len(self._data.axes_manager.sig_shape) == 0:  # means 0D data, plot on 0D viewer
                    self._viewer0D.show_data(data)

                elif len(self._data.axes_manager.sig_shape) == 1:  # means 1D data, plot on 1D viewer
                    self._viewer1D.show_data(data)

                elif len(self._data.axes_manager.sig_shape) == 2:  # means 2D data, plot on 2D viewer
                    self._viewer2D.show_data(data)
                    if DEBUG_VIEWER:
                        x, y, width, height = self.get_out_of_range_limits(*self._nav_limits)
                        _data_sig = data.isig[y: y + height, x: x + width]
                        self._debug_viewer_2D.show_data(_data_sig)

            except Exception as e:
                logger.exception(str(e))

    def update_nav_data(self, x, y, width=None, height=None):
        if self._data is not None and self._filter_type is not None and len(self._data.nav_indexes) != 0:
            nav_data = self.get_nav_data(self._data, x, y, width, height)
            if nav_data is not None:
                nav_axes = nav_data.get_nav_axes_with_data()
                if len(nav_axes) < 2:
                    #nav_data.nav_indexes = ()
                    self._navigator1D.show_data(nav_data)
                elif len(nav_axes) == 2:
                    try:
                        Triangulation(np.array([axis.get_data() for axis in nav_data.get_nav_axes()]))
                        self._navigator2D.show_data(nav_data)
                    except QhullError as e:
                        self.triangulation = False
                        self._navigator2D.setVisible(False)
                        self._navigator1D.setVisible(True)
                        data_arrays = [axis.get_data() for axis in nav_axes]
                        labels = [axis.label for axis in nav_axes]
                        nav_data = DataCalculated('nav', data=data_arrays, labels=labels)
                        self._navigator1D.show_data(nav_data)
                else:
                    data_arrays = [axis.get_data() for axis in nav_axes]
                    labels = [axis.label for axis in nav_axes]
                    nav_data = DataCalculated('nav', data=data_arrays, labels=labels)
                    self._navigator1D.show_data(nav_data)

    def get_nav_data(self, data: DataRaw, x, y, width=None, height=None):
        try:
            navigator_data = None
            if len(data.axes_manager.sig_shape) == 0:  # signal data is 0D
                navigator_data = data

            elif len(data.axes_manager.sig_shape) == 1:  # signal data is 1D
                ind_x = data.get_axis_from_index(data.sig_indexes[0])[0].find_index(x)
                ind_y = data.get_axis_from_index(data.sig_indexes[0])[0].find_index(y)
                navigator_data = self._processor.get(self._filter_type).process(data.isig[ind_x:ind_y])

            elif len(data.axes_manager.sig_shape) == 2:  # signal data is 2D
                x, y, width, height = self.get_out_of_range_limits(x, y, width, height)
                if not (width is None or height is None or width < 2 or height < 2):
                    navigator_data = self._processor.get(self._filter_type).process(data.isig[y: y + height, x: x + width])
                else:
                    navigator_data = None
            else:
                navigator_data = None

            return navigator_data

        except Exception as e:
            logger.warning('Could not compute the mathematical function')
        finally:
            return navigator_data

    def get_nav_position(self, posx=0, posy=None):
        """
        crosshair position from the "spread" data viewer. Should return scan index where the scan was closest to posx,
        posy coordinates
        Parameters
        ----------
        posx
        posy

        See Also
        --------
        update_viewer_data
        """
        # todo adapt to new layout

        nav_axes = self.get_selected_axes()
        if len(nav_axes) != 0:
            if 'datas' in nav_axes[0]:
                datas = nav_axes[0]['datas']
                xaxis = datas[0]
                if len(datas) > 1:
                    yaxis = datas[1]
                    ind_scan = utils.find_common_index(xaxis, yaxis, posx, posy)
                else:
                    ind_scan = mutils.find_index(xaxis, posx)[0]

                self.navigator1D.ui.crosshair.set_crosshair_position(ind_scan[0])


class ViewerND(ParameterManager, ActionManager, ViewerBase):
    params = [
        {'title': 'Set data spread 1D-0D', 'name': 'set_data_spread1D0D', 'type': 'action', 'visible': False},
        {'title': 'Set data spread 1D-1D', 'name': 'set_data_spread1D1D', 'type': 'action', 'visible': False},
        {'title': 'Set data spread 1D-2D', 'name': 'set_data_spread1D2D', 'type': 'action', 'visible': False},
        {'title': 'Set data spread 2D-0D', 'name': 'set_data_spread2D0D', 'type': 'action', 'visible': False},
        {'title': 'Set data spread 2D-1D', 'name': 'set_data_spread2D1D', 'type': 'action', 'visible': False},
        {'title': 'Set data spread 2D-2D', 'name': 'set_data_spread2D2D', 'type': 'action', 'visible': False},
        {'title': 'Set data spread 3D-0D', 'name': 'set_data_spread3D0D', 'type': 'action', 'visible': False},
        {'title': 'Set data 4D', 'name': 'set_data_4D', 'type': 'action', 'visible': False},
        {'title': 'Set data 3D', 'name': 'set_data_3D', 'type': 'action', 'visible': False},
        {'title': 'Set data 2D', 'name': 'set_data_2D', 'type': 'action', 'visible': False},
        {'title': 'Set data 1D', 'name': 'set_data_1D', 'type': 'action', 'visible': False},
        {'title': 'Signal shape', 'name': 'data_shape_settings', 'type': 'group', 'children': [
            {'title': 'Initial Data shape:', 'name': 'data_shape_init', 'type': 'str', 'value': "",
             'readonly': True},
            {'title': 'Axes shape:', 'name': 'nav_axes_shapes', 'type': 'group', 'children': [],
             'readonly': True},
            {'title': 'Data shape:', 'name': 'data_shape', 'type': 'str', 'value': "", 'readonly': True},
            {'title': 'Navigator axes:', 'name': 'navigator_axes', 'type': 'itemselect'},
            {'title': 'Set Nav axes:', 'name': 'set_nav_axes', 'type': 'action', 'visible': True},
        ]},
    ]

    def __init__(self, parent: QtWidgets.QWidget = None, title=''):
        ViewerBase.__init__(self, parent, title=title)
        ActionManager.__init__(self, toolbar=QtWidgets.QToolBar())
        ParameterManager.__init__(self)

        self._area = None
        self._data = None

        self.viewer0D: Viewer0D = None
        self.viewer1D: Viewer1D = None
        self.viewer2D: Viewer2D = None
        self.navigator1D: Viewer1D = None
        self.navigator2D: Viewer2D = None
        self.axes_viewer: AxesViewer = None

        self.setup_widgets()

        self.data_displayer: BaseDataDisplayer = None

        self.setup_actions()

        self.connect_things()

        self.prepare_ui()

    def update_data_displayer(self, distribution: DataDistribution):
        if distribution.name == 'uniform':
            self.data_displayer = UniformDataDisplayer(self.viewer0D, self.viewer1D, self.viewer2D,
                                                       self.navigator1D, self.navigator2D,
                                                       self.axes_viewer)
        else:
            self.data_displayer = SpreadDataDisplayer(self.viewer0D, self.viewer1D, self.viewer2D,
                                                       self.navigator1D, self.navigator2D,
                                                       self.axes_viewer)

        self.navigator1D.crosshair.crosshair_dragged.connect(self.data_displayer.update_viewer_data)

        self.navigator1D.ROI_select_signal.connect(self.data_displayer.updated_nav_integration)

        self.navigator2D.crosshair_dragged.connect(self.data_displayer.update_viewer_data)

        self.navigator2D.ROI_select_signal.connect(self.data_displayer.updated_nav_integration)
        self.axes_viewer.navigation_changed.connect(self.data_displayer.update_viewer_data)
        self.data_displayer.data_dim_signal.connect(self.update_data_dim)

        self.viewer1D.roi.sigRegionChanged.connect(self.data_displayer.update_nav_data_from_roi)

        self.viewer2D.roi.sigRegionChanged.connect(self.data_displayer.update_nav_data_from_roi)

        self.get_action('filters').currentTextChanged.connect(self.data_displayer.update_filter)
        self.connect_action('integrate_nav', self.data_displayer.show_nav_integration)
        self.data_displayer.processor_changed.connect(self.update_filters)

    def _show_data(self, data: DataRaw, **kwargs):
        force_update = False
        self.settings.child('data_shape_settings', 'data_shape_init').setValue(str(data.shape))
        self.settings.child('data_shape_settings', 'navigator_axes').setValue(
            dict(all_items=[str(ax.index) for ax in data.axes],
                 selected=[str(ax.index) for ax in data.get_nav_axes()]))

        if (self._data is None or self._data.dim != data.dim or
                self._data.nav_indexes != data.nav_indexes):
            force_update = True
        if 'force_update' in kwargs:
            force_update = kwargs['force_update']

        if self.data_displayer is None or data.distribution != self.data_displayer.distribution:
            self.update_data_displayer(data.distribution)

        self.data_displayer.update_data(data, force_update=force_update)
        self._data = data

        if force_update:
            self.update_widget_visibility(data)
            self.data_displayer.init_rois(data.axes_limits(data.nav_indexes),
                                          data.axes_limits(data.sig_indexes))
        self.data_to_export_signal.emit(self.data_to_export)

    def set_data_test(self, data_shape='3D'):
        if 'spread' in data_shape:
            data_tri = np.load('../../../resources/triangulation_data.npy')
            axes = [Axis(data=data_tri[:, 0], index=0, label='x_axis', units='xunits', spread_order=0)]

            if 'spread2D' in data_shape or 'spread3D' in data_shape:
                axes.append(Axis(data=data_tri[:, 1], index=0, label='y_axis', units='yunits', spread_order=1))
                if data_shape == 'spread2D0D':
                    data = data_tri[:, 2]
                elif data_shape == 'spread2D1D':
                    x = np.linspace(-50, 50, 100)
                    data = np.zeros((data_tri.shape[0], len(x)))
                    for ind in range(data_tri.shape[0]):
                        data[ind, :] = data_tri[ind, 2] * mutils.gauss1D(x, 0.01*ind - 10, 20)
                    axes.append(Axis(data=x, index=1, label='sig_axis'))
                elif data_shape == 'spread2D2D':
                    x = np.linspace(-50, 50, 100)
                    y = np.linspace(-200, 200, 75)
                    data = np.zeros((data_tri.shape[0], len(y), len(x)))
                    for ind in range(data_tri.shape[0]):
                        #data[ind, :] = data_tri[ind, 2] * mutils.gauss2D(0.01*x, 0.1*ind - 20, 20, y, 0.1*ind-20, 10)
                        data[ind, :] = mutils.gauss2D(x, 10*data_tri[ind, 0], 20, y, 20*data_tri[ind, 1], 30)
                    axes.append(Axis(data=x, index=1, label='sig_axis0'))
                    axes.append(Axis(data=y, index=2, label='sig_axis1'))
                elif data_shape == 'spread3D0D':
                    if 'spread2D' in data_shape or 'spread3D' in data_shape:
                        axes.append(Axis(data=data_tri[:, 1], index=0, label='z_axis', units='zunits', spread_order=2))
                        data = data_tri[:, 2]
            
            else:
                if data_shape == 'spread1D0D':
                    data = data_tri[:, 2]
                elif data_shape == 'spread1D1D':
                    x = np.linspace(-50, 50, 100)
                    data = np.zeros((data_tri.shape[0], len(x)))
                    for ind in range(data_tri.shape[0]):
                        data[ind, :] = data_tri[ind, 2] * mutils.gauss1D(x, 0.01 * ind - 10, 20)
                    axes.append(Axis(data=x, index=1, label='sig_axis'))
                elif data_shape == 'spread1D2D':
                    x = np.linspace(-50, 50, 100)
                    y = np.linspace(-200, 200, 75)
                    data = np.zeros((data_tri.shape[0], len(y), len(x)))
                    for ind in range(data_tri.shape[0]):
                        # data[ind, :] = data_tri[ind, 2] * mutils.gauss2D(0.01*x, 0.1*ind - 20, 20, y, 0.1*ind-20, 10)
                        data[ind, :] = mutils.gauss2D(x, 10 * data_tri[ind, 0], 20, y, 20 * data_tri[ind, 1], 30)
                    axes.append(Axis(data=x, index=1, label='sig_axis0'))
                    axes.append(Axis(data=y, index=2, label='sig_axis1'))
            
            dataraw = DataRaw('NDdata', distribution='spread', dim='DataND',
                              data=[data], nav_indexes=(0, ),
                              axes=axes)
        else:
            x = mutils.linspace_step(-10, 10, 0.2)
            y = mutils.linspace_step(-30, 30, 2)
            t = mutils.linspace_step(-200, 200, 2)
            z = mutils.linspace_step(-50, 50, 0.5)
            data = np.zeros((len(y), len(x), len(t), len(z)))
            amp = mutils.gauss2D(x, 0, 5, y, 0, 4) + 0.1 * np.random.rand(len(y), len(x))
            amp = np.ones((len(y), len(x), len(t), len(z)))
            for indx in range(len(x)):
                for indy in range(len(y)):
                    data[indy, indx, :, :] = amp[indy, indx] * (
                        mutils.gauss2D(z, -50 + indx * 1, 20,
                                       t, 0 + 2 * indy, 30)
                        + np.random.rand(len(t), len(z)) / 10)

            if data_shape == '4D':
                dataraw = DataRaw('NDdata', data=data, dim='DataND', nav_indexes=[0, 1],
                                  axes=[Axis(data=y, index=0, label='y_axis', units='yunits'),
                                        Axis(data=x, index=1, label='x_axis', units='xunits'),
                                        Axis(data=t, index=2, label='t_axis', units='tunits'),
                                        Axis(data=z, index=3, label='z_axis', units='zunits')])
            elif data_shape == '3D':
                data = [np.sum(data, axis=2)]
                dataraw = DataRaw('NDdata', data=data, dim='DataND', nav_indexes=[0, 1],
                                  axes=[Axis(data=y, index=0, label='y_axis', units='yunits'),
                                        Axis(data=x, index=1, label='x_axis', units='xunits'),
                                        Axis(data=t, index=2, label='t_axis', units='tunits')])
            elif data_shape == '2D':
                data = [np.sum(data, axis=(2, 3))]
                dataraw = DataRaw('NDdata', data=data, dim='DataND', nav_indexes=[0],
                                  axes=[Axis(data=y, index=0, label='y_axis', units='yunits'),
                                        Axis(data=x, index=1, label='x_axis', units='xunits')],
                                  )
            elif data_shape == '1D':
                data = [np.sum(data, axis=(0, 1, 2))]
                dataraw = DataRaw('NDdata', data=data, dim='DataND', nav_indexes=[],
                                  axes=[Axis(data=z, index=0, label='z_axis', units='zunits')])
        self._show_data(dataraw, force_update=True)

    def update_widget_visibility(self, data: DataRaw = None,
                                 nav_indexes:Tuple[int] = None):
        if data is None:
            data = self._data
        if nav_indexes is None:
            nav_indexes = data.nav_indexes
        self.viewer0D.setVisible(len(data.shape) - len(nav_indexes) == 0)
        self.viewer1D.setVisible(len(data.shape) - len(nav_indexes) == 1)
        self.viewer2D.setVisible(len(data.shape) - len(nav_indexes) == 2)
        self.viewer1D.roi.setVisible(len(nav_indexes) != 0)
        self.viewer2D.roi.setVisible(len(nav_indexes) != 0)
        self._dock_navigation.setVisible(len(nav_indexes) != 0)
        #nav_axes = data.get_nav_axes()

        if data.distribution.name == DataDistribution.uniform:
            self.navigator1D.setVisible(len(nav_indexes) == 1)
            self.navigator2D.setVisible(len(nav_indexes) == 2 and data.check_axes_linear())
            self.axes_viewer.setVisible(len(nav_indexes) > 2 or (
                    len(nav_indexes) == 2 and not data.check_axes_linear()))
        elif data.distribution.name == DataDistribution.spread:
            self.navigator2D.setVisible(len(nav_indexes) == 2 and self.data_displayer.triangulation)
            self.navigator1D.setVisible(len(nav_indexes) == 1 or len(nav_indexes) > 2 or
                                        len(nav_indexes) == 2 and
                                        not self.data_displayer.triangulation)
        else:
            raise ValueError(f'Unknown distribution: {data.distribution.name}')

    def update_filters(self, processor: DataProcessorFactory):
        self.get_action('filters').clear()
        self.get_action('filters').addItems(processor.functions_filtered('DataND'))

    def show_settings(self, show: bool = True):
        if show:
            self.settings_tree.show()
        else:
            self.settings_tree.hide()

    def prepare_ui(self):
        self.navigator1D.setVisible(False)
        self.viewer2D.setVisible(False)
        self.navigator1D.setVisible(False)
        self.viewer2D.setVisible(False)

    def setup_actions(self):
        self.add_action('setaxes', icon_name='cartesian', checkable=True, tip='Change navigation/signal axes')
        self.add_widget('filters', QtWidgets.QComboBox, tip='Filter type to apply to signal data')
        self.add_action('integrate_nav',icon_name='integrator', checkable=True,
                        tip='Integrate the navigation data')

    def reshape_data(self):
        _nav_indexes = [int(index) for index in
                        self.settings.child('data_shape_settings', 'navigator_axes').value()['selected']]
        self.update_widget_visibility(nav_indexes=_nav_indexes)
        self.data_displayer.update_nav_indexes(_nav_indexes)

    def connect_things(self):
        self.settings.child('set_data_1D').sigActivated.connect(lambda: self.set_data_test('1D'))
        self.settings.child('set_data_2D').sigActivated.connect(lambda: self.set_data_test('2D'))
        self.settings.child('set_data_3D').sigActivated.connect(lambda: self.set_data_test('3D'))
        self.settings.child('set_data_4D').sigActivated.connect(lambda: self.set_data_test('4D'))
        self.settings.child('set_data_spread2D0D').sigActivated.connect(lambda: self.set_data_test('spread2D0D'))
        self.settings.child('set_data_spread2D1D').sigActivated.connect(lambda: self.set_data_test('spread2D1D'))
        self.settings.child('set_data_spread2D2D').sigActivated.connect(lambda: self.set_data_test('spread2D2D'))
        self.settings.child('set_data_spread1D0D').sigActivated.connect(lambda: self.set_data_test('spread1D0D'))
        self.settings.child('set_data_spread1D1D').sigActivated.connect(lambda: self.set_data_test('spread1D1D'))
        self.settings.child('set_data_spread1D2D').sigActivated.connect(lambda: self.set_data_test('spread1D2D'))
        self.settings.child('set_data_spread3D0D').sigActivated.connect(lambda: self.set_data_test('spread3D0D'))
        self.settings.child('data_shape_settings', 'set_nav_axes').sigActivated.connect(self.reshape_data)

        self.navigator1D.get_action('crosshair').trigger()
        self.connect_action('setaxes', self.show_settings)

    def setup_widgets(self):
        self.parent.setLayout(QtWidgets.QVBoxLayout())
        self.parent.layout().addWidget(self.toolbar)

        self._area = DockArea()
        self.parent.layout().addWidget(self._area)

        viewer0D_widget = QtWidgets.QWidget()
        self.viewer0D = Viewer0D(viewer0D_widget)

        viewer1D_widget = QtWidgets.QWidget()
        self.viewer1D = Viewer1D(viewer1D_widget)
        self.viewer1D.roi = LinearROI()
        self.viewer1D.view.plotitem.addItem(self.viewer1D.roi)

        viewer2D_widget = QtWidgets.QWidget()
        self.viewer2D = Viewer2D(viewer2D_widget)
        self.viewer2D.roi = SimpleRectROI(centered=True)
        self.viewer2D.view.plotitem.addItem(self.viewer2D.roi)
        
        self.viewer2D.set_action_visible('flip_ud', False)
        self.viewer2D.set_action_visible('flip_lr', False)
        self.viewer2D.set_action_visible('rotate', False)
        self.viewer2D.get_action('autolevels').trigger()

        self._dock_signal = Dock('Signal')
        self._dock_signal.addWidget(viewer0D_widget)
        self._dock_signal.addWidget(viewer1D_widget)
        self._dock_signal.addWidget(viewer2D_widget)

        navigator1D_widget = QtWidgets.QWidget()
        self.navigator1D = Viewer1D(navigator1D_widget)
        navigator2D_widget = QtWidgets.QWidget()
        self.navigator2D = Viewer2D(navigator2D_widget)
        self.navigator2D.get_action('autolevels').trigger()
        self.navigator2D.get_action('crosshair').trigger()

        nav_axes_widget = QtWidgets.QWidget()
        nav_axes_widget.setVisible(False)
        self.axes_viewer = AxesViewer(nav_axes_widget)

        self._dock_navigation = Dock('Navigation')
        self._dock_navigation.addWidget(navigator1D_widget)
        self._dock_navigation.addWidget(navigator2D_widget)
        self._dock_navigation.addWidget(nav_axes_widget)

        self._area.addDock(self._dock_navigation)
        self._area.addDock(self._dock_signal, 'right', self._dock_navigation)

    def update_data_dim(self, dim: str):
        self.settings.child('data_shape_settings', 'data_shape').setValue(dim)


def main():
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()
    prog = ViewerND(widget)
    for child in prog.settings.children():
        if 'set_data_' in child.name():
            child.show(True)
    prog.show_settings()

    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()


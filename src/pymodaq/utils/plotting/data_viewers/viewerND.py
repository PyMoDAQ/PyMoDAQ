import sys
from collections import OrderedDict
import copy
import datetime
from typing import List, Tuple, Union

import numpy as np
from pyqtgraph import LinearRegionItem
from qtpy import QtWidgets
from qtpy.QtCore import QObject, Slot, Signal, QRectF, QPointF

from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.gui_utils.dock import DockArea, Dock
from pymodaq.utils.parameter import Parameter
from pymodaq.utils.managers.action_manager import addaction
from pymodaq.utils.plotting.data_viewers.viewer1D import Viewer1D
from pymodaq.utils.plotting.data_viewers.viewer1Dbasic import Viewer1DBasic
from pymodaq.utils.plotting.data_viewers.viewer2D import Viewer2D
from pymodaq.utils.plotting.data_viewers.viewer0D import Viewer0D
import pymodaq.utils.daq_utils as utils
import pymodaq.utils.math_utils as mutils
from pymodaq.utils.data import DataRaw, Axis
from pymodaq.utils.plotting.utils.signalND import Signal as SignalND
from pymodaq.utils.plotting.data_viewers.viewer import ViewerBase
from pymodaq.utils.managers.action_manager import ActionManager
from pymodaq.utils.managers.parameter_manager import ParameterManager
from pymodaq.post_treatment.process_Nd_to_scalar import DataNDProcessorFactory
from pymodaq.post_treatment.process_1d_to_scalar import Data1DProcessorFactory


from pymodaq.utils.managers.roi_manager import SimpleRectROI, LinearROI


logger = set_logger(get_module_name(__file__))
math_processorsND = DataNDProcessorFactory()
math_processors1D = Data1DProcessorFactory()


DEBUG_VIEWER = False

class DataDisplayer(QObject):

    data_dim_signal = Signal(str)
    processor_changed = Signal(object)

    def __init__(self, viewer0D: Viewer0D, viewer1D: Viewer1D, viewer2D: Viewer2D, navigator1D: Viewer1D,
                 navigator2D: Viewer2D):
        super().__init__()
        self._viewer0D = viewer0D
        self._viewer1D = viewer1D
        self._viewer2D = viewer2D
        self._navigator1D = navigator1D
        self._navigator2D = navigator2D
        if DEBUG_VIEWER:
            self._debug_widget = QtWidgets.QWidget()
            self._debug_viewer_2D = Viewer2D(self._debug_widget)
            self._debug_widget.show()

        self._data: DataRaw = None
        self._nav_limits: tuple = (0, 10, None, None)
        self._signal_at: tuple = (0, 0)


        self._filter_type: str = None
        self._processor = None

    @property
    def data_shape(self):
        return self._data.shape if self._data is not None else None

    def update_filter(self, filter_type: str):
        if filter_type in self._processor.functions:
            self._filter_type = filter_type
            self.update_nav_data(*self._nav_limits)

    def update_processor(self, math_processor):
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

    def init(self, data: DataRaw):
        processor = math_processorsND if len(data.axes_manager.sig_shape) > 1 else math_processors1D
        self.update_processor(processor)

    def update_viewer_data(self, posx=0, posy=0):
        """ Update the signal display depending on the position of the crosshair in the navigation panels

        Parameters
        ----------
        posx: float
            from the 1D or 2D Navigator crosshair or from one of the navigation axis viewer (in that case
            nav_axis tells from wich navigation axis the position comes from)
        posy: float
            from the 2D Navigator crosshair
        """
        self._signal_at = posx, posy
        if self._data is not None:
            try:
                if len(self._data.nav_indexes) == 0:
                    data = self._data

                elif len(self._data.nav_indexes) == 1:
                    nav_axis_data = self._data.axes_manager.get_nav_axes()[0].data
                    if posx < nav_axis_data[0] or posx > nav_axis_data[-1]:
                        return
                    ind_x = mutils.find_index(nav_axis_data, posx)[0][0]
                    logger.debug(f'Getting the data at nav index {ind_x}')
                    data = self._data.inav[ind_x]

                elif len(self._data.nav_indexes) == 2:
                    nav_xaxis_data = self._data.axes_manager.get_nav_axes()[1].data
                    nav_yaxis_data = self._data.axes_manager.get_nav_axes()[0].data
                    if posx < nav_xaxis_data[0] or posx > nav_xaxis_data[-1]:
                        return
                    if posy < nav_yaxis_data[0] or posy > nav_yaxis_data[-1]:
                        return
                    ind_x = mutils.find_index(nav_xaxis_data, posx)[0][0]
                    ind_y = mutils.find_index(nav_yaxis_data, posy)[0][0]
                    logger.debug(f'Getting the data at nav indexes {ind_y} and {ind_x}')
                    data = self._data.inav[ind_y, ind_x]
                else:
                    return
                    #todo check this and update code
                    pos = []
                    for ind_view, view in enumerate(self.nav_axes_viewers):
                        p = view.roi_line.getPos()[0]
                        if p < 0 or p > len(self._nav_axes[ind_view]['data']):
                            return
                        ind = int(np.rint(p))
                        pos.append(ind)
                    data = self._data.inav.__getitem__(pos).data

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

    def update_nav_data_from_roi(self, roi: Union[SimpleRectROI, LinearROI]):
        if isinstance(roi, LinearROI):
            x, y = roi.getRegion()
            self._nav_limits = (int(x), int(y), None, None)
        elif isinstance(roi, SimpleRectROI):
            x, y = roi.pos().x(), roi.pos().y()
            width, height = roi.size().x(), roi.size().y()
            self._nav_limits = (int(x), int(y), int(width), int(height))
        self.update_nav_data(*self._nav_limits)

    def update_nav_data(self, x, y, width=None, height=None):
        if self._data is not None and self._filter_type is not None and len(self._data.nav_indexes) != 0:
            nav_data = self.get_nav_data(self._data, x, y, width, height)
            if nav_data is not None:
                if len(nav_data.shape) < 2:
                    self._navigator1D.show_data(nav_data)
                else:
                    self._navigator2D.show_data(nav_data)

    def get_nav_data(self, data: DataRaw, x, y, width=None, height=None):
        try:
            navigator_data = None
            if len(data.axes_manager.sig_shape) == 0:  # signal data is 0D
                navigator_data = data

            elif len(data.axes_manager.sig_shape) == 1:  # signal data is 1D
                _, navigator_data = self._processor.get(self._filter_type).process((x, y), data)

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


class ViewerND(ParameterManager, ActionManager, QObject):
    params = [
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

    def __init__(self, parent_widget: QtWidgets.QWidget):
        QObject.__init__(self)
        ActionManager.__init__(self, toolbar=QtWidgets.QToolBar())
        ParameterManager.__init__(self)

        self._area = None
        self._data = None

        self.parent_widget: QtWidgets.QWidget = parent_widget

        self.viewer0D: Viewer0D = None
        self.viewer1D: Viewer1D = None
        self.viewer2D: Viewer2D = None
        self.navigator1D: Viewer1D = None
        self.navigator2D: Viewer2D = None
        self.setup_widgets()

        self.data_displayer = DataDisplayer(self.viewer0D, self.viewer1D, self.viewer2D,
                                            self.navigator1D, self.navigator2D)

        self.setup_actions()

        self.connect_things()

        self.prepare_ui()

    def _show_data(self, data: DataRaw):
        force_update = False
        self.settings.child('data_shape_settings', 'data_shape_init').setValue(str(data.shape))
        self.settings.child('data_shape_settings', 'navigator_axes').setValue(
            dict(all_items=[str(ax.index) for ax in data.axes],
                 selected=[str(ax.index) for ax in data.get_nav_axes()]))
        if self._data is None or self._data.shape != data.shape or self._data.nav_indexes != data.nav_indexes:
            self.update_widget_visibility(data)
            self.init_rois(data)
            force_update = True
        self.data_displayer.update_data(data, force_update=force_update)

        self._data = data

    def init_rois(self, data: DataRaw):
        means = []
        for axis in data.axes_manager.get_nav_axes():
            means.append(np.mean(axis.data))
        if len(data.nav_indexes) == 1:
            self.navigator1D.set_crosshair_position(*means)
        elif len(data.nav_indexes) == 2:
            self.navigator2D.set_crosshair_position(*means)

        mins = []
        maxs = []
        for axis in data.axes_manager.get_signal_axes():
            mins.append(np.min(axis.data))
            maxs.append(np.max(axis.data))
        if len(data.axes_manager.sig_indexes) == 1:
            self.viewer1D.roi.setPos((mins[0], maxs[0]))
        elif len(data.axes_manager.sig_indexes) > 1:
            self.viewer2D.roi.setPos((0, 0))
            self.viewer2D.roi.setSize((len(data.get_axis_from_index(data.axes_manager.sig_indexes[1])),
                                      len(data.get_axis_from_index(data.axes_manager.sig_indexes[0]))))

    def set_data_test(self, data_shape='3D'):

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
            dataraw = DataRaw('NDdata', data=data, dim='DataND', nav_indexes=[0, 1],
                              axes=[Axis(data=y, index=0, label='y_axis', units='yunits'),
                                    Axis(data=x, index=1, label='x_axis', units='xunits')])
        elif data_shape == '1D':
            data = [np.sum(data, axis=(0, 1, 2))]
            dataraw = DataRaw('NDdata', data=data, dim='DataND', nav_indexes=[],
                              axes=[Axis(data=z, index=0, label='z_axis', units='zunits')])
        self._show_data(dataraw)

    def update_widget_visibility(self, data: DataRaw = None):
        if data is None:
            data = self._data
        self.viewer0D.setVisible(len(data.shape) - len(data.nav_indexes) == 0)
        self.viewer1D.setVisible(len(data.shape) - len(data.nav_indexes) == 1)
        self.viewer2D.setVisible(len(data.shape) - len(data.nav_indexes) == 2)
        self.viewer1D.roi.setVisible(len(data.nav_indexes) != 0)
        self.viewer2D.roi.setVisible(len(data.nav_indexes) != 0)
        self._dock_navigation.setVisible(len(data.nav_indexes) != 0)

        self.navigator1D.setVisible(len(data.nav_indexes) == 1)
        self.navigator2D.setVisible(len(data.nav_indexes) == 2)

    def update_filters(self, processor):
        self.get_action('filters').clear()
        self.get_action('filters').addItems(processor.functions)

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

    def reshape_data(self):
        _nav_indexes = [int(index) for index in
                        self.settings.child('data_shape_settings', 'navigator_axes').value()['selected']]
        self.update_widget_visibility()
        self.data_displayer.update_nav_indexes(_nav_indexes)

    def connect_things(self):
        self.settings.child('set_data_1D').sigActivated.connect(lambda: self.set_data_test('1D'))
        self.settings.child('set_data_2D').sigActivated.connect(lambda: self.set_data_test('2D'))
        self.settings.child('set_data_3D').sigActivated.connect(lambda: self.set_data_test('3D'))
        self.settings.child('set_data_4D').sigActivated.connect(lambda: self.set_data_test('4D'))
        self.settings.child('data_shape_settings', 'set_nav_axes').sigActivated.connect(self.reshape_data)

        self.navigator1D.crosshair.crosshair_dragged.connect(self.data_displayer.update_viewer_data)
        self.navigator1D.get_action('crosshair').trigger()
        self.navigator2D.crosshair_dragged.connect(self.data_displayer.update_viewer_data)
        self.connect_action('setaxes', self.show_settings)
        self.data_displayer.data_dim_signal.connect(self.update_data_dim)

        self.viewer1D.roi.sigRegionChanged.connect(self.data_displayer.update_nav_data_from_roi)
        self.viewer2D.roi.sigRegionChanged.connect(self.data_displayer.update_nav_data_from_roi)

        self.get_action('filters').currentTextChanged.connect(self.data_displayer.update_filter)
        self.data_displayer.processor_changed.connect(self.update_filters)

    def setup_widgets(self):
        self.parent_widget.setLayout(QtWidgets.QVBoxLayout())
        self.parent_widget.layout().addWidget(self.toolbar)

        self._area = DockArea()
        self.parent_widget.layout().addWidget(self._area)

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

        self.navigation_widget = QtWidgets.QWidget()
        self.nav_axes_widget = QtWidgets.QWidget()
        self.nav_axes_widget.setLayout(QtWidgets.QVBoxLayout())
        self.nav_axes_widget.setVisible(False)

        self._dock_navigation = Dock('Navigation')
        self._dock_navigation.addWidget(navigator1D_widget)
        self._dock_navigation.addWidget(navigator2D_widget)

        self._area.addDock(self._dock_navigation)
        self._area.addDock(self._dock_signal, 'right', self._dock_navigation)

    def update_data_dim(self, dim: str):
        self.settings.child('data_shape_settings', 'data_shape').setValue(dim)

    def setup_spread_UI(self):
        #todo adapt to new layout
        self.ui.spread_widget = QtWidgets.QWidget()
        self.ui.spread_widget.setLayout(QtWidgets.QVBoxLayout())
        widget1D = QtWidgets.QWidget()
        widget2D = QtWidgets.QWidget()
        self.ui.spread_viewer_1D = Viewer1D(widget1D)
        self.ui.spread_viewer_2D = Viewer2D(widget2D)
        self.ui.spread_widget.layout().addWidget(widget1D)
        self.ui.spread_widget.layout().addWidget(widget2D)

        self.ui.spread_viewer_1D.ui.crosshair.crosshair_dragged.connect(self.get_nav_position)
        self.ui.spread_viewer_1D.ui.crosshair_pb.trigger()
        self.ui.spread_viewer_2D.get_action('autolevels').trigger()

        self.ui.spread_viewer_2D.crosshair_dragged.connect(self.get_nav_position)
        self.ui.spread_viewer_2D.get_action('crosshair').trigger()

        self.ui.spread_widget.show()
        self.ui.spread_widget.setVisible(False)

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


def main():
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()
    prog = ViewerND(widget)
    prog.settings.child('set_data_4D').show(True)
    prog.settings.child('set_data_3D').show(True)
    prog.settings.child('set_data_2D').show(True)
    prog.settings.child('set_data_1D').show(True)
    prog.show_settings()

    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()


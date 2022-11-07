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
import pymodaq.utils.daq_utils as utils
import pymodaq.utils.math_utils as mutils
from pymodaq.utils.data import DataRaw, Axis
from pymodaq.utils.plotting.utils.signalND import Signal as SignalND
from pymodaq.utils.plotting.utils.signalND import DataAxis
from pymodaq.utils.plotting.data_viewers.viewer import ViewerBase
from pymodaq.utils.managers.action_manager import ActionManager
from pymodaq.utils.managers.parameter_manager import ParameterManager

logger = set_logger(get_module_name(__file__))


class DataDisplayer(QObject):

    data_dim_signal = Signal(str)

    def __init__(self, viewer1D: Viewer1D, viewer2D: Viewer2D, navigator1D: Viewer1D, navigator2D: Viewer2D):
        super().__init__()

        self._viewer1D = viewer1D
        self._viewer2D = viewer2D
        self._navigator1D = navigator1D
        self._navigator2D = navigator2D

        self._data: DataRaw = None
        self._nav_axes: List[Axis] = None
        self._nav_limits: tuple = (None, None)
        self._signal_at: tuple = (0, 0)
        self._data_buffer = []

    def update_data(self, data: DataRaw):
        if self._data is None or self._data.shape != data.shape:
            self._nav_axes = data.get_nav_axes()
            self._data = data
        else:
            self._data.data = data.data[0]

        self.data_dim_signal.emit(self._data.get_data_dimension())
        self.update_viewer_data(*self._signal_at)
        self.update_nav_data(*self._nav_limits)

    def update_nav_data(self, x, y, width=None, height=None):
        nav_data = self.get_nav_data(self._data, x, y, width, height)

        if len(nav_data.shape) < 2:
            self._navigator1D.show_data(nav_data)
        else:
            self._navigator2D.show_data(nav_data)
        # todo plot

    def get_nav_data(self, data: DataRaw, x, y, width=None, height=None):

        if len(data.axes_manager.sig_shape) == 0:  # signal data is 0D
            navigator_data = [data.data]

        elif len(data.axes_manager.sig_shape) == 1:  # signal data is 1D
            navigator_data = self.get_data_from_1Dsignal_roi(data, (x, y))

        elif len(data.axes_manager.sig_shape) == 2:  # signal data is 2D
            if width is not None and height is not None:
                navigator_data = [data.isig[x: x + width, y: y + height].sum((-1, -2)).data]
            else:
                navigator_data = [data.sum((-1, -2)).data]
        else:
            navigator_data = None
        axes = []
        for ind, axis in enumerate(self._data_raw.get_nav_axes()):
            axis.index = ind

        nav_data = DataRaw('NavData', data=navigator_data, )
        nav_data = self._data.get_navigator_data()
        return nav_data

    def get_data_from_1Dsignal_roi(self, data, x, y):
        self._nav_limits[0, 2] = [x, y]

        # if [x, y] != []:
        #     if self.ui.combomath.currentText() == 'Sum':
        #         navigator_data = [datas_transposed.isig[pt.x():pt.y() + 1].sum((-1)).data for pt in
        #                           ROI_bounds_1D]
        #     elif self.ui.combomath.currentText() == 'Mean':
        #         navigator_data = [datas_transposed.isig[pt.x():pt.y() + 1].mean((-1)).data for pt in
        #                           ROI_bounds_1D]
        #     elif self.ui.combomath.currentText() == 'Half-life':
        #         navigator_data = [datas_transposed.isig[pt.x():pt.y() + 1].halflife((-1)).data for pt in
        #                           ROI_bounds_1D]
        # else:
        #     if self.ui.combomath.currentText() == 'Sum':
        #         navigator_data = [datas_transposed.isig[:].sum((-1)).data]
        #     elif self.ui.combomath.currentText() == 'Mean':
        #         navigator_data = [datas_transposed.isig[:].mean((-1)).data]
        #     elif self.ui.combomath.currentText() == 'Half-life':
        #         navigator_data = [datas_transposed.isig[:].halflife((-1)).data]
        # return navigator_data
        return  data


    def update_nav_axes(self, nav_axes: List[Axis]):
        self._nav_axes = nav_axes

    def update_nav_limits(self, x, y, width=None, height=None):
        self._nav_limits = x, y, width, height

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
                # if len(self._nav_axes) == 0:
                #     data = self._data.data
                # elif len(self._nav_axes) == 1:
                #     if posx < self._nav_axes[0]['data'][0] or posx > self._nav_axes[0]['data'][-1]:
                #         return
                #     ind_x = mutils.find_index(self._nav_axes[0]['data'], posx)[0][0]
                #     logger.debug(f'Getting the data at nav index {ind_x}')
                #     data = self._data.inav[ind_x].data
                # elif len(self._nav_axes) == 2:
                #     if posx < self._nav_axes[0]['data'][0] or posx > self._nav_axes[0]['data'][-1]:
                #         return
                #     if posy < self._nav_axes[1]['data'][0] or posy > self._nav_axes[1]['data'][-1]:
                #         return
                #     ind_x = mutils.find_index(self._nav_axes[0]['data'], posx)[0][0]
                #     ind_y = mutils.find_index(self._nav_axes[1]['data'], posy)[0][0]
                #     logger.debug(f'Getting the data at nav indexes {ind_y} and {ind_x}')
                #     data = self._data.inav[ind_y, ind_x].data
                #
                # else:
                #     pos = []
                #     for ind_view, view in enumerate(self.nav_axes_viewers):
                #         p = view.roi_line.getPos()[0]
                #         if p < 0 or p > len(self._nav_axes[ind_view]['data']):
                #             return
                #         ind = int(np.rint(p))
                #         pos.append(ind)
                #     data = self._data.inav.__getitem__(pos).data

                data = self._data.get_signal_data()

                signal_axes = self._data_raw.get_signal_axes()
                for ind, axis in enumerate(signal_axes):
                    axis.index = ind

                if len(self._data.axes_manager.sig_shape) == 0:  # means 0D data, plot on 1D viewer
                    self._data_buffer.extend(data)
                    self._viewer1D.show_data(data)

                elif len(self._data.axes_manager.signal_shape) == 1:  # means 1D data, plot on 1D viewer
                    self._viewer1D.show_data(data)

                elif len(self._data.axes_manager.signal_shape) == 2:  # means 2D data, plot on 2D viewer
                    self._viewer2D.show_data(data)

            except Exception as e:
                logger.exception(str(e))

class ViewND(ParameterManager, ActionManager, QObject):
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
        
        self.parent_widget: QtWidgets.QWidget = parent_widget

        self.viewer1D: Viewer1D = None
        self.viewer2D: Viewer2D = None
        self.navigator1D: Viewer1D = None
        self.navigator2D: Viewer2D = None
        self.setup_widgets()

        self.data_displayer = DataDisplayer(self.viewer1D, self.viewer2D, self.navigator1D, self.navigator2D)

        self.setup_actions()

        self.connect_things()

        self.prepare_ui()

    def set_data_test(self, data_shape='3D'):

        x = mutils.linspace_step(-10, 10, 0.2)
        y = mutils.linspace_step(-30, 30, 2)
        t = mutils.linspace_step(-200, 200, 2)
        z = mutils.linspace_step(-50, 50, 0.5)
        data = np.zeros((len(y), len(x), len(t), len(z)))
        amp = mutils.gauss2D(x, 0, 1, y, 0, 2)
        for indx in range(len(x)):
            for indy in range(len(y)):
                data[indy, indx, :, :] = amp[indy, indx] * (
                    mutils.gauss2D(z, 0 + indx * 2, 20, t, 0 + 3 * indy, 30) + np.random.rand(len(t), len(z)) / 10)

        if data_shape == '4D':
            dataraw = DataRaw('NDdata', data=data, dim='DataND', nav_indexes=[2, 3],
                              axes=[Axis(data=y, index=0, label='y_axis', units='yunits'),
                                    Axis(data=x, index=1, label='x_axis', units='xunits'),
                                    Axis(data=t, index=2, label='t_axis', units='tunits'),
                                    Axis(data=z, index=3, label='z_axis', units='zunits')])
        elif data_shape == '3D':
            data = [np.sum(data, axis=3)]
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
            data = [np.sum(data, axis=(1, 2, 3))]
            dataraw = DataRaw('NDdata', data=data, dim='DataND', nav_indexes=[],
                              axes=[Axis(data=y, index=0, label='y_axis', units='yunits')])
        self.display_data(dataraw)


    def display_data(self, data: DataRaw):
        self.settings.child('data_shape_settings', 'data_shape_init').setValue(str(data.shape))
        self.settings.child('data_shape_settings', 'navigator_axes').setValue(
            dict(all_items=[ax['label'] for ax in data.axes],
                 selected=[ax['label'] for ax in data.get_nav_axes()]))

        self.viewer1D.setVisible(len(data.shape)-len(data.nav_axes) in (0, 1))
        self.viewer2D.setVisible(len(data.shape)-len(data.nav_axes) == 2)

        self.navigator1D.setVisible(len(data.nav_axes) == 1)
        self.navigator2D.setVisible(len(data.nav_axes) == 2)

        self.data_displayer.update_data(data)

    def signal_axes_selection(self):
        self.settings_tree.show()

    def prepare_ui(self):
        self.navigator1D.setVisible(False)
        self.viewer2D.setVisible(False)
        self.navigator1D.setVisible(False)
        self.viewer2D.setVisible(False)

    def setup_actions(self):
        self.add_action('setaxes', icon_name='cartesian', checkable=True, tip='Change navigation/signal axes')

    def connect_things(self):
        self.settings.child('set_data_1D').sigActivated.connect(lambda: self.set_data_test('1D'))
        self.settings.child('set_data_2D').sigActivated.connect(lambda: self.set_data_test('2D'))
        self.settings.child('set_data_3D').sigActivated.connect(lambda: self.set_data_test('3D'))
        self.settings.child('set_data_4D').sigActivated.connect(lambda: self.set_data_test('4D'))
        self.settings.child('data_shape_settings', 'set_nav_axes').sigActivated.connect(self.data_displayer.update_data)

        self.navigator1D.crosshair.crosshair_dragged.connect(self.data_displayer.update_viewer_data)
        self.navigator1D.get_action('crosshair').trigger()
        self.navigator2D.crosshair_dragged.connect(self.data_displayer.update_viewer_data)
        self.connect_action('setaxes', self.signal_axes_selection)
        self.data_displayer.data_dim_signal.connect(self.update_data_dim)

    def setup_widgets(self):
        self.parent_widget.setLayout(QtWidgets.QVBoxLayout())
        self.parent_widget.layout().addWidget(self.toolbar)

        self._area = DockArea()
        self.parent_widget.layout().addWidget(self._area)

        viewer1D_widget = QtWidgets.QWidget()
        self.viewer1D = Viewer1D(viewer1D_widget)
        viewer2D_widget = QtWidgets.QWidget()
        self.viewer2D = Viewer2D(viewer2D_widget)
        
        self.viewer2D.set_action_visible('flip_ud', False)
        self.viewer2D.set_action_visible('flip_lr', False)
        self.viewer2D.set_action_visible('rotate', False)
        self.viewer2D.get_action('autolevels').trigger()

        dock_signal = Dock('Signal')
        dock_signal.addWidget(viewer1D_widget)
        dock_signal.addWidget(viewer2D_widget)

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

        dock_navigation = Dock('Navigation')
        dock_navigation.addWidget(navigator1D_widget)
        dock_navigation.addWidget(navigator2D_widget)

        self._area.addDock(dock_navigation)
        self._area.addDock(dock_signal, 'right', dock_navigation)

    def update_data_dim(self, dim: str):
        self.settings.child('data_shape_settings', 'data_shape').setValue(dim)


class ViewerND(ViewerBase):
    """
    """
    def __init__(self, parent=None, title=''):
        
        self.parent: QtWidgets.QWidget = None
        super().__init__(parent=parent, title=title)

        self.view = ViewND(self.parent)
    
        self.nav_axes_viewers = []
        self.nav_axes_dicts = []

        self.x_axis = dict(data=None, label='', units='')
        self.y_axis = dict(data=None, label='', units='')

        self.data_buffer = []  # convenience list to store 0D data to be displayed
        self.datas = None
        self.datas_settings = None
        # set default data shape case
        self.data_axes = None
        # self.set_nav_axes(3)
        self.ui = QObject()  # the user interface
        self.set_GUI()
        self.setup_spread_UI()


    @Slot(OrderedDict)
    def export_data(self, datas):
        self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()
        for key in datas.keys():
            if key in self.data_to_export.keys():
                if isinstance(datas[key], OrderedDict):
                    if list(datas[key].keys()) != []:
                        self.data_to_export[key].update(datas[key])
        self.data_to_export_signal.emit(self.data_to_export)



    def set_axis(self, Npts):
        """
            | Set axis values from node and a linspace regular distribution

            ================ ======================= ==========================================
            **Parameters**     **Type**                **Description**

             *node*           tables Group instance   the root node of the local treated tree
            ================ ======================= ==========================================

            Returns
            -------
            float array
                the computed values axis.

        """
        axis = np.linspace(0, Npts, Npts, endpoint=False)
        return axis

    def restore_nav_axes(self, navigation_axes, nav_axes=None):
        if nav_axes is None:
            N_nav_axes = len(self.datas.data.shape)
        else:
            N_nav_axes = len([ax for ax in navigation_axes if 'nav' in ax])
        nav_axes_dicts = []
        sorted_indexes = []
        for k in navigation_axes:
            if 'nav' in k:
                if navigation_axes[k]['nav_index'] < N_nav_axes:
                    sorted_indexes.append(navigation_axes[k]['nav_index'])
                    nav_axes_dicts.append(copy.deepcopy(navigation_axes[k]))

        for ind in range(N_nav_axes):  # in case there was no nav axes in kwargs
            if ind not in sorted_indexes:
                sorted_indexes.append(ind)
                nav_axes_dicts.append(Axis(nav_index=ind, label=f'Nav {ind:02d}'))
                N = self.datas.data.shape[ind]
                nav_axes_dicts[-1]['data'] = np.linspace(0, N - 1, N)

        # sort nav axes:
        sorted_index = np.argsort(sorted_indexes)
        self.nav_axes_dicts = []
        for ind in sorted_index:
            self.nav_axes_dicts.append(nav_axes_dicts[ind])

    def set_data(self, datas_transposed, temp_data=False, restore_nav_axes=True, **kwargs):
        """
        """
        try:

            if restore_nav_axes:
                nav_axes = dict([])
                for ind, ax in enumerate(self.nav_axes_dicts):
                    nav_axes[f'nav_{ind}'] = ax
                self.restore_nav_axes(nav_axes)

            ##########################################################################
            # display the correct signal viewer
            if len(datas_transposed.axes_manager.signal_shape) == 0:  # signal data are 0D
                self.viewer1D.parent.setVisible(True)
                self.viewer2D.parent.setVisible(False)
            elif len(datas_transposed.axes_manager.signal_shape) == 1:  # signal data are 1D
                self.viewer1D.parent.setVisible(True)
                self.viewer2D.parent.setVisible(False)
            elif len(datas_transposed.axes_manager.signal_shape) == 2:  # signal data are 2D
                self.viewer1D.parent.setVisible(False)
                self.viewer2D.parent.setVisible(True)
            self.x_axis = Axis()
            self.y_axis = Axis()
            if len(datas_transposed.axes_manager.signal_shape) == 1 or len(
                    datas_transposed.axes_manager.signal_shape) == 2:  # signal data are 1D

                if 'x_axis' in kwargs:
                    if not isinstance(kwargs['x_axis'], dict):
                        self.x_axis['data'] = kwargs['x_axis'][:]
                        self.x_axis = kwargs['x_axis']
                    else:
                        self.x_axis = copy.deepcopy(kwargs['x_axis'])
                else:
                    self.x_axis['data'] = self.set_axis(datas_transposed.axes_manager.signal_shape[0])
                if 'y_axis' in kwargs:
                    self.viewer1D.set_axis_label(axis_settings=dict(orientation='left',
                                                                       label=kwargs['y_axis']['label'],
                                                                       units=kwargs['y_axis']['units']))

            if len(datas_transposed.axes_manager.signal_shape) == 2:  # signal data is 2D
                if 'y_axis' in kwargs:
                    if not isinstance(kwargs['y_axis'], dict):
                        self.y_axis['data'] = kwargs['y_axis'][:]
                        self.y_axis = kwargs['y_axis']
                    else:
                        self.y_axis = copy.deepcopy(kwargs['y_axis'])
                else:
                    self.y_axis['data'] = self.set_axis(datas_transposed.axes_manager.signal_shape[1])

            axes_nav = self.get_selected_axes_indexes()
            if len(axes_nav) == 0 or len(axes_nav) == 1:
                self.update_viewer_data(*self.navigator1D.ui.crosshair.get_positions())
            elif len(axes_nav) == 2:
                self.update_viewer_data(*self.navigator2D.crosshair.get_positions())

            # #get ROI bounds from viewers if any
            ROI_bounds_1D = []
            try:
                self.roi1D.getRegion()
                indexes_values = mutils.find_index(self.viewer1D.x_axis, self.roi1D.getRegion())
                ROI_bounds_1D.append(QPointF(indexes_values[0][0], indexes_values[1][0]))
            except Exception as e:
                logger.warning(str(e))

            ROI_bounds_2D = []
            try:
                ROI_bounds_2D.append(QRectF(self.ROI2D.pos().x(), self.ROI2D.pos().y(),
                                            self.ROI2D.size().x(), self.ROI2D.size().y()))
            except Exception as e:
                logger.warning(str(e))

            #############################################################
            # display the correct navigator viewer and set some parameters
            if len(axes_nav) <= 2:
                for view in self.nav_axes_viewers:
                    self.nav_axes_widget.layout().removeWidget(view.parent)
                    view.parent.close()
                self.nav_axes_viewers = []

            nav_axes = self.get_selected_axes()

            if len(nav_axes) == 0:  # no Navigator
                self.navigator1D.parent.setVisible(False)
                self.navigator2D.parent.setVisible(False)
                # self.navigator_label.setVisible(False)
                self.nav_axes_widget.setVisible(False)
                self.roi1D.setVisible(False)
                self.ROI2D.setVisible(False)
                navigator_data = []

            elif len(nav_axes) == 1:  # 1D Navigator
                self.roi1D.setVisible(True)
                self.ROI2D.setVisible(True)
                self.navigator1D.parent.setVisible(True)
                self.navigator2D.parent.setVisible(False)
                self.nav_axes_widget.setVisible(False)
                # self.navigator_label.setVisible(True)
                self.navigator1D.remove_plots()
                self.navigator1D.x_axis = nav_axes[0]

                labels = []
                units = []
                if self.scan_type.lower() == 'tabular' or self.is_spread:
                    if 'datas' in self.nav_axes_dicts[0]:
                        navigator_data = self.nav_axes_dicts[0]['datas'][:]
                        if 'labels' in self.nav_axes_dicts[0]:
                            labels = self.nav_axes_dicts[0]['labels'][:]
                        if 'all_units' in self.nav_axes_dicts[0]:
                            units = self.nav_axes_dicts[0]['all_units'][:]
                    else:
                        navigator_data = [self.nav_axes_dicts[0]['data']]
                    if self.is_spread:
                        if self.scan_type.lower() == 'tabular':
                            data_spread = []
                            for ind_label, lab in enumerate(labels):
                                if 'curvilinear' in lab.lower():
                                    data_spread = [self.nav_axes_dicts[0]['datas'][ind]]
                        else:
                            data_spread = self.nav_axes_dicts[0]['datas'][:]

                        data_spread.append(self.get_nav_data(datas_transposed, ROI_bounds_1D, ROI_bounds_2D)[0])
                        data_spread = np.vstack(data_spread).T

                else:
                    navigator_data = self.get_nav_data(datas_transposed, ROI_bounds_1D, ROI_bounds_2D)

                if self.is_spread:
                    self.ui.spread_viewer_2D.parent.setVisible(data_spread.shape[1] == 3)
                    self.ui.spread_viewer_1D.parent.setVisible(data_spread.shape[1] == 2)
                    if data_spread.shape[1] == 3:
                        self.ui.spread_viewer_2D.setImage(data_spread=data_spread)
                        if len(labels) > 1 and len(units) > 1:
                            self.ui.spread_viewer_2D.set_axis_label(dict(orientation='bottom', label=labels[0],
                                                                         units=units[0]))
                            self.ui.spread_viewer_2D.set_axis_label(dict(orientation='left', label=labels[1],
                                                                         units=units[1]))
                    else:
                        ind_sorted = np.argsort(data_spread[:, 0])
                        self.ui.spread_viewer_1D.show_data([data_spread[:, 1][ind_sorted]], labels=['data'],
                                                           x_axis=data_spread[:, 0][ind_sorted])
                        self.ui.spread_viewer_1D.set_axis_label(dict(orientation='bottom',
                                                                     label='Curvilinear value', units=''))

                if temp_data:
                    self.navigator1D.show_data_temp(navigator_data)
                    self.navigator1D.update_labels(labels)
                else:
                    self.navigator1D.show_data(navigator_data)
                    self.navigator1D.update_labels(labels)

            elif len(nav_axes) == 2:  # 2D Navigator:
                self.roi1D.setVisible(True)
                self.ROI2D.setVisible(True)

                self.navigator1D.parent.setVisible(False)
                self.navigator2D.parent.setVisible(True)
                self.nav_axes_widget.setVisible(False)
                # self.navigator_label.setVisible(True)

                self.navigator2D.x_axis = nav_axes[0]
                self.navigator2D.y_axis = nav_axes[1]

                navigator_data = self.get_nav_data(datas_transposed, ROI_bounds_1D, ROI_bounds_2D)

                if temp_data:
                    self.navigator2D.setImageTemp(*navigator_data)
                else:
                    self.navigator2D.setImage(*navigator_data)

            else:  # more than 2 nv axes, display all nav axes in 1D plots

                self.navigator1D.parent.setVisible(False)
                self.navigator2D.parent.setVisible(False)
                self.nav_axes_widget.setVisible(True)
                if len(self.nav_axes_viewers) != len(axes_nav):
                    for view in self.nav_axes_viewers:
                        self.nav_axes_widget.layout().removeWidget(view.parent)
                        view.parent.close()
                    widgets = []
                    self.nav_axes_viewers = []
                    for ind in range(len(axes_nav)):
                        widgets.append(QtWidgets.QWidget())
                        self.nav_axes_widget.layout().addWidget(widgets[-1])
                        self.nav_axes_viewers.append(Viewer1DBasic(widgets[-1], show_line=True))

                for ind in range(len(axes_nav)):
                    self.nav_axes_viewers[ind].roi_line_signal.connect(self.update_viewer_data)
                    self.nav_axes_viewers[ind].show_data([nav_axes[ind]['data']])
                    self.nav_axes_viewers[ind].set_axis_label(dict(orientation='bottom',
                                                                   label=nav_axes[ind]['label'],
                                                                   units=nav_axes[ind]['units']))

            self.update_viewer_data()

        except Exception as e:
            logger.exception(str(e))
            self.update_status(utils.getLineInfo() + str(e), self.wait_time, 'log')

    def get_data_from_1Dsignal_roi(self, datas_transposed, ROI_bounds_1D):
        if ROI_bounds_1D != []:
            if self.ui.combomath.currentText() == 'Sum':
                navigator_data = [datas_transposed.isig[pt.x():pt.y() + 1].sum((-1)).data for pt in
                                  ROI_bounds_1D]
            elif self.ui.combomath.currentText() == 'Mean':
                navigator_data = [datas_transposed.isig[pt.x():pt.y() + 1].mean((-1)).data for pt in
                                  ROI_bounds_1D]
            elif self.ui.combomath.currentText() == 'Half-life':
                navigator_data = [datas_transposed.isig[pt.x():pt.y() + 1].halflife((-1)).data for pt in
                                  ROI_bounds_1D]
        else:
            if self.ui.combomath.currentText() == 'Sum':
                navigator_data = [datas_transposed.isig[:].sum((-1)).data]
            elif self.ui.combomath.currentText() == 'Mean':
                navigator_data = [datas_transposed.isig[:].mean((-1)).data]
            elif self.ui.combomath.currentText() == 'Half-life':
                navigator_data = [datas_transposed.isig[:].halflife((-1)).data]
        return navigator_data

    def get_nav_data(self, datas_transposed, ROI_bounds_1D, ROI_bounds_2D):

        if len(datas_transposed.axes_manager.signal_shape) == 0:  # signal data is 0D
            navigator_data = [datas_transposed.data]

        elif len(datas_transposed.axes_manager.signal_shape) == 1:  # signal data is 1D
            navigator_data = self.get_data_from_1Dsignal_roi(datas_transposed, ROI_bounds_1D)

        elif len(datas_transposed.axes_manager.signal_shape) == 2:  # signal data is 2D
            if ROI_bounds_2D != []:
                navigator_data = [datas_transposed.isig[rect.x():rect.x() + rect.width(),
                                  rect.y():rect.y() + rect.height()].sum((-1, -2)).data for rect in
                                  ROI_bounds_2D]
            else:
                navigator_data = [datas_transposed.sum((-1, -2)).data]
        else:
            navigator_data = None
        return navigator_data

    def init_ROI(self):
        nav_axes = self.get_selected_axes()
        if len(nav_axes) != 0:
            self.navigator1D.ui.crosshair.set_crosshair_position(np.mean(nav_axes[0]['data']))
            if len(nav_axes) > 1:
                x, y = self.navigator2D.unscale_axis(np.mean(nav_axes[0]['data']),
                                                        np.mean(nav_axes[1]['data']))
                self.navigator2D.crosshair.set_crosshair_position(x, y)

            if self.x_axis['data'] is not None:
                self.roi1D.setRegion((np.min(self.x_axis['data']), np.max(self.x_axis['data'])))
            if self.x_axis['data'] is not None and self.y_axis['data'] is not None:
                self.ROI2D.setPos((np.min(self.x_axis['data']), np.min(self.y_axis['data'])))
                self.ROI2D.setSize((np.max(self.x_axis['data']) - np.min(self.x_axis['data']),
                                    np.max(self.y_axis['data']) - np.min(self.y_axis['data'])))

            self._update_navigator()



    def set_nav_axes(self, Ndim, nav_axes=None):
        self.data_axes = [ind for ind in range(Ndim)]
        if nav_axes is None:
            if Ndim > 0:
                nav_axes = self.data_axes[0:2]
            else:
                nav_axes = self.data_axes[0]

        self.settings.child('data_shape_settings', 'navigator_axes').setValue(
            dict(all_items=[ax['label'] for ax in self.nav_axes_dicts],
                 selected=[self.nav_axes_dicts[ind]['label'] for ind in nav_axes]))

    def set_GUI(self):
        """

        """
        # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

        # main_layout = QtWidgets.QGridLayout()
        # self._area.setLayout(main_layout)

        # vsplitter = QtWidgets.QSplitter(Qt.Vertical)
        # Hsplitter=QtWidgets.QSplitter(Qt.Horizontal)

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

        self.settings = Parameter.create(name='Param', type='group', children=params)
        # #self.signal_axes_selection()

        # connecting from tree
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)  # any changes on the settings
        self.settings.child(('set_data_1D')).sigActivated.connect(lambda: self.set_data_test('1D'))
        self.settings.child(('set_data_2D')).sigActivated.connect(lambda: self.set_data_test('2D'))
        self.settings.child(('set_data_3D')).sigActivated.connect(lambda: self.set_data_test('3D'))
        self.settings.child(('set_data_4D')).sigActivated.connect(lambda: self.set_data_test('4D'))
        self.settings.child('data_shape_settings', 'set_nav_axes').sigActivated.connect(self.update_data)
        # #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        # #% 1D signalviewer
        viewer1D_widget = QtWidgets.QWidget()
        self.viewer1D = Viewer1D(viewer1D_widget)
        self.roi1D = LinearRegionItem()
        self.viewer1D.viewer.plotwidget.plotItem.addItem(self.roi1D)
        self.ui.combomath = QtWidgets.QComboBox()
        self.ui.combomath.addItems(['Sum', 'Mean', 'Half-life'])
        self.viewer1D.ui.button_widget.addWidget(self.ui.combomath)
        self.ui.combomath.currentIndexChanged.connect(self._update_navigator)

        self.roi1D.sigRegionChangeFinished.connect(self._update_navigator)

        # % 2D viewer Dock
        viewer2D_widget = QtWidgets.QWidget()
        self.viewer2D = Viewer2D(viewer2D_widget)
        self.viewer2D.set_action_visible('flip_ud', False)
        self.viewer2D.set_action_visible('flip_lr', False)
        self.viewer2D.set_action_visible('rotate', False)
        self.viewer2D.get_action('autolevels').trigger()
        self.viewer2D.get_action('ROIselect').trigger()
        self.ROI2D = self.viewer2D.ROIselect
        self.viewer2D.ROI_select_signal.connect(self._update_navigator)

        dock_signal = Dock('Signal')
        dock_signal.addWidget(viewer1D_widget)
        dock_signal.addWidget(viewer2D_widget)

        # #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        # #% Navigator viewer Dock
        navigator1D_widget = QtWidgets.QWidget()
        self.navigator1D = Viewer1D(navigator1D_widget)
        self.navigator1D.ui.crosshair.crosshair_dragged.connect(self.update_viewer_data)
        self.navigator1D.ui.crosshair_pb.trigger()
        self.navigator1D.data_to_export_signal.connect(self.export_data)
        navigator2D_widget = QtWidgets.QWidget()
        self.navigator2D = Viewer2D(navigator2D_widget)
        self.navigator2D.get_action('autolevels').trigger()
        self.navigator2D.crosshair_dragged.connect(
            self.update_viewer_data)  # export scaled position in conjonction with 2D scaled axes
        self.navigator2D.get_action('crosshair').trigger()
        self.navigator2D.data_to_export_signal.connect(self.export_data)

        self.navigation_widget = QtWidgets.QWidget()
        # vlayout_navigation = QtWidgets.QVBoxLayout()
        # self.navigator_label = QtWidgets.QLabel('Navigation View')
        # self.navigator_label.setMaximumHeight(15)
        # layout_navigation.addWidget(self.navigator_label)
        self.nav_axes_widget = QtWidgets.QWidget()
        self.nav_axes_widget.setLayout(QtWidgets.QVBoxLayout())
        # vlayout_navigation.addWidget(navigator2D_widget)
        # vlayout_navigation.addWidget(self.nav_axes_widget)
        self.nav_axes_widget.setVisible(False)
        # vlayout_navigation.addWidget(navigator1D_widget)
        # self.navigation_widget.setLayout(vlayout_navigation)
        # vsplitter.insertWidget(0, self.navigation_widget)

        dock_navigation = Dock('Navigation')
        dock_navigation.addWidget(navigator1D_widget)
        dock_navigation.addWidget(navigator2D_widget)

        self._area.addDock(dock_navigation)
        self._area.addDock(dock_signal, 'right', dock_navigation)

        # self.ui.signal_widget = QtWidgets.QWidget()
        # VLayout1 = QtWidgets.QVBoxLayout()
        # self.viewer_label = QtWidgets.QLabel('Data View')
        # self.viewer_label.setMaximumHeight(15)
        # VLayout1.addWidget(self.viewer_label)
        # VLayout1.addWidget(viewer1D_widget)
        # VLayout1.addWidget(viewer2D_widget)
        # self.ui.signal_widget.setLayout(VLayout1)
        # vsplitter.insertWidget(1, self.ui.signal_widget)

        self.ui.set_signals_pb_1D = addaction('', icon_name='cartesian', checkable=True,
                                                                                        tip='Change navigation/signal axes')

        self.ui.set_signals_pb_1D_bis = addaction('', icon_name='cartesian', checkable=True,
                                                                                            tip='Change navigation/signal axes')
        self.ui.set_signals_pb_2D = addaction('', icon_name='cartesian', checkable=True,
                                                                                        tip='Change navigation/signal axes')
        self.ui.set_signals_pb_2D_bis = addaction('', icon_name='cartesian', checkable=True,
                                                                                            tip='Change navigation/signal axes')

        self.navigator1D.ui.button_widget.addAction(self.ui.set_signals_pb_1D)
        self.navigator2D.toolbar.addAction(self.ui.set_signals_pb_2D)
        self.viewer1D.ui.button_widget.addAction(self.ui.set_signals_pb_1D_bis)
        self.viewer2D.toolbar.addAction(self.ui.set_signals_pb_2D_bis)

        # main_layout.addWidget(vsplitter)

        self.ui.set_signals_pb_1D.triggered.connect(self.signal_axes_selection)
        self.ui.set_signals_pb_2D.triggered.connect(self.signal_axes_selection)
        self.ui.set_signals_pb_1D_bis.triggered.connect(self.signal_axes_selection)
        self.ui.set_signals_pb_2D_bis.triggered.connect(self.signal_axes_selection)

        # to start: display as default a 2D navigator and a 1D viewer
        self.navigator1D.parent.setVisible(False)
        self.viewer2D.parent.setVisible(True)

    def setup_spread_UI(self):
        self.ui.spread_widget = QtWidgets.QWidget()
        self.ui.spread_widget.setLayout(QtWidgets.QVBoxLayout())
        widget1D = QtWidgets.QWidget()
        widget2D = QtWidgets.QWidget()
        self.ui.spread_viewer_1D = Viewer1D(widget1D)
        self.ui.spread_viewer_2D = Viewer2D(widget2D)
        self.ui.spread_widget.layout().addWidget(widget1D)
        self.ui.spread_widget.layout().addWidget(widget2D)
        # todo: better connection as discussed
        self.ui.spread_viewer_1D.ui.crosshair.crosshair_dragged.connect(self.get_nav_position)
        self.ui.spread_viewer_1D.ui.crosshair_pb.trigger()
        self.ui.spread_viewer_2D.get_action('autolevels').trigger()
        # todo: better connection as discussed
        self.ui.spread_viewer_2D.crosshair_dragged.connect(self.get_nav_position)
        self.ui.spread_viewer_2D.get_action('crosshair').trigger()

        self.ui.spread_widget.show()
        self.ui.spread_widget.setVisible(False)

    def show_data_temp(self, datas, nav_axes=None, distribution='uniform', **kwargs):
        """
        """
        self.show_data(datas, temp_data=True, nav_axes=nav_axes, distribution=distribution, **kwargs)

    def set_nav_shapes(self):
        for child in self.settings.child('data_shape_settings', 'nav_axes_shapes').children():
            child.remove()

        for ind_ax, ax in enumerate(self.nav_axes_dicts):
            self.settings.child('data_shape_settings', 'nav_axes_shapes').addChild(
                {'title': ax['label'], 'name': f'nav_{ind_ax:02d}_shape', 'type': 'str', 'value': str(ax['data'].shape),
                 'readonly': True},
            )

    def show_data(self, datas, temp_data=False, nav_axes=None, is_spread=False, scan_type='', **kwargs):
        """Display datas as a hyperspaced dataset
        only one numpy ndarray should be used
        """
        self.is_spread = is_spread
        self.ui.spread_widget.setVisible(is_spread)

        self.scan_type = scan_type
        self.data_buffer = []
        self.data_to_export = OrderedDict(name=self.title, data0D=OrderedDict(), data1D=OrderedDict(),
                                          data2D=OrderedDict(), dataND=OrderedDict(), )
        self.data_to_export['dataND']['CH000'] = OrderedDict(data=datas, source='raw', nav_axes=nav_axes)
        for key in kwargs:
            self.data_to_export['dataND']['CH000'][key] = kwargs[key]
        self._datas = datas
        self.datas = SignalND(datas)
        self.datas_settings = kwargs
        self.restore_nav_axes(kwargs, nav_axes=nav_axes)
        self.set_nav_shapes()

        try:
            if self.data_axes is not None:
                if datas.ndim != len(self.data_axes) or self.get_selected_axes_indexes() != nav_axes:
                    self.set_nav_axes(datas.ndim, nav_axes)  # init the list of axes and set the managers to nav_axes
            else:
                self.set_nav_axes(datas.ndim, nav_axes)  # init the list of axes and set the managers to nav_axes

            # self.datas=hs.signals.BaseSignal(datas)

            self.update_data_signal()
            self.settings.child('data_shape_settings', 'data_shape_init').setValue(str(datas.shape))
            self.settings.child('data_shape_settings', 'data_shape').setValue(self.get_data_dimension())
            self.set_data(self.datas, temp_data=temp_data, **kwargs)

        except Exception as e:
            logger.exception(str(e))
            self.update_status(utils.getLineInfo() + str(e), self.wait_time, 'log')



    def get_selected_axes_indexes(self):
        if self.settings.child('data_shape_settings', 'navigator_axes').value() is None:
            return []
        labels = self.settings.child('data_shape_settings', 'navigator_axes').value()['selected']
        axes_nav = []
        for lab in labels:
            for ax in self.nav_axes_dicts:
                if ax['label'] == lab:
                    axes_nav.append(ax['nav_index'])
        return axes_nav

    def get_selected_axes(self):
        axes_nav = []
        if self.settings.child('data_shape_settings', 'navigator_axes').value() is not None:
            labels = self.settings.child('data_shape_settings', 'navigator_axes').value()['selected']
            for lab in labels:
                for ax in self.nav_axes_dicts:
                    if ax['label'] == lab:
                        axes_nav.append(ax)
                        break
        return axes_nav

    def update_data(self):
        restore_nav_axes = self.get_selected_axes_indexes() != self.get_selected_axes_indexes()

        self.update_data_signal()
        self.settings.child('data_shape_settings', 'data_shape').setValue(self.get_data_dimension())

        nav_axes = dict([])
        for ind, ax in enumerate(self.nav_axes_dicts):
            nav_axes[f'nav_{ind}'] = ax

        self.set_data(self.datas, restore_nav_axes=restore_nav_axes, **nav_axes)

    def update_data_signal(self):
        try:
            axes_nav = [len(self.data_axes) - ind - 1 for ind in self.get_selected_axes_indexes()]
            axes_signal = [ax for ax in self.data_axes if ax not in axes_nav]
            self.datas = SignalND(self._datas)
            self.datas = self.datas.transpose(signal_axes=axes_signal, navigation_axes=axes_nav)

        except Exception as e:
            logger.exception(str(e))
            self.update_status(utils.getLineInfo() + str(e), self.wait_time, 'log')

    def _update_Navigator(self):
        # #self.update_data_signal()
        self.set_data(self.datas, **self.datas_settings)


    def get_axis_from_label(self):
        pass

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




def main_view():
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()
    prog = ViewND(widget)
    prog.settings.child('set_data_4D').show(True)
    prog.settings.child('set_data_3D').show(True)
    prog.settings.child('set_data_2D').show(True)
    prog.settings.child('set_data_1D').show(True)

    prog.settings.child('set_data_4D').activate()

    widget.show()
    sys.exit(app.exec_())


def main():
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()
    prog = ViewerND(widget)
    prog.settings.child('set_data_4D').show(True)
    prog.settings.child('set_data_3D').show(True)
    prog.settings.child('set_data_2D').show(True)
    prog.settings.child('set_data_1D').show(True)
    prog.signal_axes_selection()
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main_view()


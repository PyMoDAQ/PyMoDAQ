from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt, QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize, QByteArray, QRectF, \
    QPointF
import sys
from pymodaq.daq_utils.plotting.viewer1D.viewer1D_main import Viewer1D
from pymodaq.daq_utils.plotting.viewer1D.viewer1Dbasic import Viewer1DBasic
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D
from pymodaq.daq_utils.daq_utils import Axis
from collections import OrderedDict
import numpy as np
from pyqtgraph.parametertree import Parameter, ParameterTree
import pymodaq.daq_utils.daq_utils as utils
from pyqtgraph import LinearRegionItem
from pymodaq.daq_utils.gui_utils import DockArea
from pyqtgraph.dockarea import Dock
import copy
from pymodaq.daq_utils.plotting.viewerND.signal_manager import Signal
import datetime

logger = utils.set_logger(utils.get_module_name(__file__))


class ViewerND(QtWidgets.QWidget, QObject):
    """

        ======================== =========================================
        **Attributes**            **Type**

        *dockarea*                instance of pyqtgraph.DockArea
        *mainwindow*              instance of pyqtgraph.DockArea
        *title*                   string
        *waitime*                 int
        *x_axis*                  float array
        *y_axis*                  float array
        *data_buffer*             list of data
        *ui*                      QObject
        ======================== =========================================

        Raises
        ------
        parent Exception
            If parent argument is None in constructor abort

        See Also
        --------
        set_GUI


        References
        ----------
        PyQt5, pyqtgraph, QtWidgets, QObject

    """
    command_DAQ_signal = pyqtSignal(list)
    log_signal = pyqtSignal(str)
    data_to_export_signal = pyqtSignal(OrderedDict)  # edict(name=self.DAQ_type,data0D=None,data1D=None,data2D=None)

    def __init__(self, parent=None):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(ViewerND, self).__init__()
        # if parent is None:
        #     raise Exception('no valid parent container, expected dockarea')
        # parent=DockArea()
        # exit(0)

        if parent is None:
            area = DockArea()
            area.show()
            self.area = area
        elif isinstance(parent, DockArea):
            self.area = parent
        elif isinstance(parent, QtWidgets.QWidget):
            area = DockArea()
            self.area = area
            parent.setLayout(QtWidgets.QVBoxLayout())
            parent.layout().addWidget(area)

        self.wait_time = 2000
        self.viewer_type = 'DataND'  # ☺by default but coul dbe used for 3D visualization
        self.distribution = 'uniform'
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
        self.title = ""
        self.data_to_export = OrderedDict(name=self.title, data0D=OrderedDict(), data1D=OrderedDict(),
                                          data2D=OrderedDict(),
                                          dataND=OrderedDict())

    @pyqtSlot(OrderedDict)
    def export_data(self, datas):
        self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()
        for key in datas.keys():
            if key in self.data_to_export.keys():
                if isinstance(datas[key], OrderedDict):
                    if list(datas[key].keys()) != []:
                        self.data_to_export[key].update(datas[key])
        self.data_to_export_signal.emit(self.data_to_export)

    def get_data_dimension(self):
        try:
            dimension = "("
            for ind, ax in enumerate(self.datas.axes_manager.navigation_shape):
                if ind != len(self.datas.axes_manager.navigation_shape) - 1:
                    dimension += str(ax) + ','
                else:
                    dimension += str(ax) + '|'
            for ind, ax in enumerate(self.datas.axes_manager.signal_shape):
                if ind != len(self.datas.axes_manager.signal_shape) - 1:
                    dimension += str(ax) + ','
                else:
                    dimension += str(ax) + ')'
            return dimension
        except Exception as e:
            self.update_status(utils.getLineInfo() + str(e), self.wait_time, log='log')
            logger.exception(str(e))
            return ""

    def parameter_tree_changed(self, param, changes):
        """
            Foreach value changed, update :
                * Viewer in case of **DAQ_type** parameter name
                * visibility of button in case of **show_averaging** parameter name
                * visibility of naverage in case of **live_averaging** parameter name
                * scale of axis **else** (in 2D pymodaq type)

            Once done emit the update settings signal to link the commit.

            =============== =================================== ================================================================
            **Parameters**    **Type**                           **Description**
            *param*           instance of ppyqtgraph parameter   the parameter to be checked
            *changes*         tuple list                         Contain the (param,changes,info) list listing the changes made
            =============== =================================== ================================================================
        """
        try:
            for param, change, data in changes:
                path = self.settings.childPath(param)
                if path is not None:
                    childName = '.'.join(path)
                else:
                    childName = param.name()
                if change == 'childAdded':
                    pass

                elif change == 'value':
                    pass
                    # if param.name()=='navigator_axes':
                    #    self.update_data_signal()
                    #    self.settings.child('data_shape_settings', 'data_shape').setValue(str(datas_transposed))
                    #    self.set_data(self.datas)

        except Exception as e:
            logger.exception(str(e))
            self.update_status(utils.getLineInfo() + str(e), self.wait_time, 'log')

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
            N_nav_axes = len(nav_axes)
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
                self.ui.viewer1D.parent.setVisible(True)
                self.ui.viewer2D.parent.setVisible(False)
            elif len(datas_transposed.axes_manager.signal_shape) == 1:  # signal data are 1D
                self.ui.viewer1D.parent.setVisible(True)
                self.ui.viewer2D.parent.setVisible(False)
            elif len(datas_transposed.axes_manager.signal_shape) == 2:  # signal data are 2D
                self.ui.viewer1D.parent.setVisible(False)
                self.ui.viewer2D.parent.setVisible(True)
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
                    self.ui.viewer1D.set_axis_label(axis_settings=dict(orientation='left',
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
                self.update_viewer_data(*self.ui.navigator1D.ui.crosshair.get_positions())
            elif len(axes_nav) == 2:
                self.update_viewer_data(*self.ui.navigator2D.ui.crosshair.get_positions())

            # #get ROI bounds from viewers if any
            ROI_bounds_1D = []
            try:
                self.ROI1D.getRegion()
                indexes_values = utils.find_index(self.ui.viewer1D.x_axis, self.ROI1D.getRegion())
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
                    self.ui.nav_axes_widget.layout().removeWidget(view.parent)
                    view.parent.close()
                self.nav_axes_viewers = []

            nav_axes = self.get_selected_axes()

            if len(nav_axes) == 0:  # no Navigator
                self.ui.navigator1D.parent.setVisible(False)
                self.ui.navigator2D.parent.setVisible(False)
                # self.navigator_label.setVisible(False)
                self.ui.nav_axes_widget.setVisible(False)
                self.ROI1D.setVisible(False)
                self.ROI2D.setVisible(False)
                navigator_data = []

            elif len(nav_axes) == 1:  # 1D Navigator
                self.ROI1D.setVisible(True)
                self.ROI2D.setVisible(True)
                self.ui.navigator1D.parent.setVisible(True)
                self.ui.navigator2D.parent.setVisible(False)
                self.ui.nav_axes_widget.setVisible(False)
                # self.navigator_label.setVisible(True)
                self.ui.navigator1D.remove_plots()
                self.ui.navigator1D.x_axis = nav_axes[0]

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
                    self.ui.navigator1D.show_data_temp(navigator_data)
                    self.ui.navigator1D.update_labels(labels)
                else:
                    self.ui.navigator1D.show_data(navigator_data)
                    self.ui.navigator1D.update_labels(labels)

            elif len(nav_axes) == 2:  # 2D Navigator:
                self.ROI1D.setVisible(True)
                self.ROI2D.setVisible(True)

                self.ui.navigator1D.parent.setVisible(False)
                self.ui.navigator2D.parent.setVisible(True)
                self.ui.nav_axes_widget.setVisible(False)
                # self.navigator_label.setVisible(True)

                self.ui.navigator2D.x_axis = nav_axes[0]
                self.ui.navigator2D.y_axis = nav_axes[1]

                navigator_data = self.get_nav_data(datas_transposed, ROI_bounds_1D, ROI_bounds_2D)

                if temp_data:
                    self.ui.navigator2D.setImageTemp(*navigator_data)
                else:
                    self.ui.navigator2D.setImage(*navigator_data)

            else:  # more than 2 nv axes, display all nav axes in 1D plots

                self.ui.navigator1D.parent.setVisible(False)
                self.ui.navigator2D.parent.setVisible(False)
                self.ui.nav_axes_widget.setVisible(True)
                if len(self.nav_axes_viewers) != len(axes_nav):
                    for view in self.nav_axes_viewers:
                        self.ui.nav_axes_widget.layout().removeWidget(view.parent)
                        view.parent.close()
                    widgets = []
                    self.nav_axes_viewers = []
                    for ind in range(len(axes_nav)):
                        widgets.append(QtWidgets.QWidget())
                        self.ui.nav_axes_widget.layout().addWidget(widgets[-1])
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
            self.ui.navigator1D.ui.crosshair.set_crosshair_position(np.mean(nav_axes[0]['data']))
            if len(nav_axes) > 1:
                x, y = self.ui.navigator2D.unscale_axis(np.mean(nav_axes[0]['data']),
                                                        np.mean(nav_axes[1]['data']))
                self.ui.navigator2D.ui.crosshair.set_crosshair_position(x, y)

            if self.x_axis['data'] is not None:
                self.ROI1D.setRegion((np.min(self.x_axis['data']), np.max(self.x_axis['data'])))
            if self.x_axis['data'] is not None and self.y_axis['data'] is not None:
                self.ROI2D.setPos((np.min(self.x_axis['data']), np.min(self.y_axis['data'])))
                self.ROI2D.setSize((np.max(self.x_axis['data']) - np.min(self.x_axis['data']),
                                    np.max(self.y_axis['data']) - np.min(self.y_axis['data'])))

            self.update_Navigator()

    def set_data_test(self, data_shape='3D'):

        x = utils.linspace_step(0, 20, 1)
        y = utils.linspace_step(0, 30, 1)
        t = utils.linspace_step(0, 200, 1)
        z = utils.linspace_step(0, 200, 1)
        datas = np.zeros((len(y), len(x), len(t), len(z)))
        amp = utils.gauss2D(x, 7, 5, y, 12, 10)
        for indx in range(len(x)):
            for indy in range(len(y)):
                datas[indy, indx, :, :] = amp[indy, indx] * (
                    utils.gauss2D(z, 50 + indx * 2, 20, t, 50 + 3 * indy, 30) + np.random.rand(len(t), len(z)) / 10)

        nav_axis = dict(nav00=Axis(data=y, nav_index=0, label='y_axis', units='yunits'),
                        nav01=Axis(data=x, nav_index=1, label='x_axis', units='xunits'),
                        nav02=Axis(data=t, nav_index=2, label='t_axis', units='tunits'),
                        nav03=Axis(data=z, nav_index=3, label='z_axis', units='zunits'))

        if data_shape == '4D':
            nav_axes = [2, 3]
            self.show_data(datas, temp_data=False, nav_axes=nav_axes, **nav_axis)
        elif data_shape == '3D':
            self.show_data(np.sum(datas, axis=3), temp_data=False, nav_axes=[0, 1], **nav_axis)
        elif data_shape == '2D':
            self.show_data(np.sum(datas, axis=(2, 3)), **nav_axis)
        elif data_shape == '1D':
            self.show_data(np.sum(datas, axis=(1, 2, 3)), **nav_axis)

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
        # self.area.setLayout(main_layout)

        # vsplitter = QtWidgets.QSplitter(Qt.Vertical)
        # Hsplitter=QtWidgets.QSplitter(Qt.Horizontal)

        params = [
            {'title': 'set data:', 'name': 'set_data_4D', 'type': 'action', 'visible': False},
            {'title': 'set data:', 'name': 'set_data_3D', 'type': 'action', 'visible': False},
            {'title': 'set data:', 'name': 'set_data_2D', 'type': 'action', 'visible': False},
            {'title': 'set data:', 'name': 'set_data_1D', 'type': 'action', 'visible': False},
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
        self.ui.viewer1D = Viewer1D(viewer1D_widget)
        self.ROI1D = LinearRegionItem()
        self.ui.viewer1D.viewer.plotwidget.plotItem.addItem(self.ROI1D)
        self.ui.combomath = QtWidgets.QComboBox()
        self.ui.combomath.addItems(['Sum', 'Mean', 'Half-life'])
        self.ui.viewer1D.ui.button_widget.addWidget(self.ui.combomath)
        self.ui.combomath.currentIndexChanged.connect(self.update_Navigator)

        self.ROI1D.sigRegionChangeFinished.connect(self.update_Navigator)

        # % 2D viewer Dock
        viewer2D_widget = QtWidgets.QWidget()
        self.ui.viewer2D = Viewer2D(viewer2D_widget)
        self.ui.viewer2D.ui.Ini_plot_pb.setVisible(False)
        self.ui.viewer2D.ui.FlipUD_pb.setVisible(False)
        self.ui.viewer2D.ui.FlipLR_pb.setVisible(False)
        self.ui.viewer2D.ui.rotate_pb.setVisible(False)
        self.ui.viewer2D.ui.auto_levels_pb.click()
        self.ui.viewer2D.ui.ROIselect_pb.click()
        self.ROI2D = self.ui.viewer2D.ui.ROIselect
        self.ui.viewer2D.ROI_select_signal.connect(self.update_Navigator)

        dock_signal = Dock('Signal')
        dock_signal.addWidget(viewer1D_widget)
        dock_signal.addWidget(viewer2D_widget)

        # #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        # #% Navigator viewer Dock
        navigator1D_widget = QtWidgets.QWidget()
        self.ui.navigator1D = Viewer1D(navigator1D_widget)
        self.ui.navigator1D.ui.crosshair.crosshair_dragged.connect(self.update_viewer_data)
        self.ui.navigator1D.ui.crosshair_pb.click()
        self.ui.navigator1D.data_to_export_signal.connect(self.export_data)
        navigator2D_widget = QtWidgets.QWidget()
        self.ui.navigator2D = Viewer2D(navigator2D_widget)
        self.ui.navigator2D.ui.auto_levels_pb.click()
        self.ui.navigator2D.crosshair_dragged.connect(
            self.update_viewer_data)  # export scaled position in conjonction with 2D scaled axes
        self.ui.navigator2D.ui.crosshair_pb.click()
        self.ui.navigator2D.data_to_export_signal.connect(self.export_data)

        self.ui.navigation_widget = QtWidgets.QWidget()
        # vlayout_navigation = QtWidgets.QVBoxLayout()
        # self.navigator_label = QtWidgets.QLabel('Navigation View')
        # self.navigator_label.setMaximumHeight(15)
        # layout_navigation.addWidget(self.navigator_label)
        self.ui.nav_axes_widget = QtWidgets.QWidget()
        self.ui.nav_axes_widget.setLayout(QtWidgets.QVBoxLayout())
        # vlayout_navigation.addWidget(navigator2D_widget)
        # vlayout_navigation.addWidget(self.ui.nav_axes_widget)
        self.ui.nav_axes_widget.setVisible(False)
        # vlayout_navigation.addWidget(navigator1D_widget)
        # self.ui.navigation_widget.setLayout(vlayout_navigation)
        # vsplitter.insertWidget(0, self.ui.navigation_widget)

        dock_navigation = Dock('Navigation')
        dock_navigation.addWidget(navigator1D_widget)
        dock_navigation.addWidget(navigator2D_widget)

        self.area.addDock(dock_navigation)
        self.area.addDock(dock_signal, 'right', dock_navigation)

        # self.ui.signal_widget = QtWidgets.QWidget()
        # VLayout1 = QtWidgets.QVBoxLayout()
        # self.viewer_label = QtWidgets.QLabel('Data View')
        # self.viewer_label.setMaximumHeight(15)
        # VLayout1.addWidget(self.viewer_label)
        # VLayout1.addWidget(viewer1D_widget)
        # VLayout1.addWidget(viewer2D_widget)
        # self.ui.signal_widget.setLayout(VLayout1)
        # vsplitter.insertWidget(1, self.ui.signal_widget)

        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/cartesian.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.set_signals_pb_1D = QtWidgets.QPushButton('')
        self.ui.set_signals_pb_1D.setToolTip('Change navigation/signal axes')
        self.ui.set_signals_pb_1D_bis = QtWidgets.QPushButton('')
        self.ui.set_signals_pb_1D_bis.setToolTip('Change navigation/signal axes')
        self.ui.set_signals_pb_1D.setIcon(icon)
        self.ui.set_signals_pb_1D_bis.setIcon(icon)
        self.ui.set_signals_pb_2D = QtWidgets.QPushButton('')
        self.ui.set_signals_pb_2D.setToolTip('Change navigation/signal axes')
        self.ui.set_signals_pb_2D.setIcon(icon)
        self.ui.set_signals_pb_2D_bis = QtWidgets.QPushButton('')
        self.ui.set_signals_pb_2D_bis.setToolTip('Change navigation/signal axes')
        self.ui.set_signals_pb_2D_bis.setIcon(icon)

        self.ui.navigator1D.ui.button_widget.addWidget(self.ui.set_signals_pb_1D)
        self.ui.navigator2D.toolbar_button.addWidget(self.ui.set_signals_pb_2D)
        self.ui.viewer1D.ui.button_widget.addWidget(self.ui.set_signals_pb_1D_bis)
        self.ui.viewer2D.toolbar_button.addWidget(self.ui.set_signals_pb_2D_bis)

        # main_layout.addWidget(vsplitter)

        self.ui.set_signals_pb_1D.clicked.connect(self.signal_axes_selection)
        self.ui.set_signals_pb_2D.clicked.connect(self.signal_axes_selection)
        self.ui.set_signals_pb_1D_bis.clicked.connect(self.signal_axes_selection)
        self.ui.set_signals_pb_2D_bis.clicked.connect(self.signal_axes_selection)

        # to start: display as default a 2D navigator and a 1D viewer
        self.ui.navigator1D.parent.setVisible(False)
        self.ui.viewer2D.parent.setVisible(True)

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
        self.ui.spread_viewer_1D.ui.crosshair_pb.click()
        self.ui.spread_viewer_2D.ui.auto_levels_pb.click()
        # todo: better connection as discussed
        self.ui.spread_viewer_2D.crosshair_dragged.connect(self.get_nav_position)
        self.ui.spread_viewer_2D.ui.crosshair_pb.click()

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
        self.datas = Signal(datas)
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

    def signal_axes_selection(self):
        self.ui.settings_tree = ParameterTree()
        self.ui.settings_tree.setMinimumWidth(300)
        self.ui.settings_tree.setParameters(self.settings, showTop=False)
        self.signal_axes_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        self.signal_axes_widget.setLayout(layout)
        layout.addWidget(self.ui.settings_tree)
        self.signal_axes_widget.adjustSize()
        self.signal_axes_widget.show()

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
            self.datas = Signal(self._datas)
            self.datas = self.datas.transpose(signal_axes=axes_signal, navigation_axes=axes_nav)

        except Exception as e:
            logger.exception(str(e))
            self.update_status(utils.getLineInfo() + str(e), self.wait_time, 'log')

    def update_Navigator(self):
        # #self.update_data_signal()
        self.set_data(self.datas, **self.datas_settings)

    def update_status(self, txt, wait_time=1000, log=''):
        """
            | Update the statut bar showing a Message with a delay of wait_time ms (1s by default)

            ================ ======== ===========================
            **Parameters**   **Type**     **Description**

             *txt*            string   the text message to show

             *wait_time*      int      the delay time of showing
            ================ ======== ===========================

        """
        if log != '':
            self.log_signal.emit(txt)

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
                    ind_scan = utils.find_index(xaxis, posx)[0]

                self.ui.navigator1D.ui.crosshair.set_crosshair_position(ind_scan[0])

    def update_viewer_data(self, posx=0, posy=0):
        """
            |PyQt5 slot triggered by the crosshair signal from the 1D or 2D Navigator
            | Update the viewer informations from an x/y given position and store data.
        Parameters
        ----------
        posx: (float) from the 1D or 2D Navigator crosshair or from one of the navigation axis viewer (in that case
            nav_axis tells from wich navigation axis the position comes from)
        posy: (float) from the 2D Navigator crosshair
        nav_axis: (int) index of the navigation axis from where posx comes from

        """
        if self.datas is not None:
            try:
                nav_axes = self.get_selected_axes()
                # datas_transposed=self.update_data_signal(self.datas)
                if len(nav_axes) == 0:
                    data = self.datas.data

                elif len(nav_axes) == 1:
                    if posx < nav_axes[0]['data'][0] or posx > nav_axes[0]['data'][-1]:
                        return
                    ind_x = utils.find_index(nav_axes[0]['data'], posx)[0][0]
                    data = self.datas.inav[ind_x].data
                elif len(nav_axes) == 2:
                    if posx < nav_axes[0]['data'][0] or posx > nav_axes[0]['data'][-1]:
                        return
                    if posy < nav_axes[1]['data'][0] or posy > nav_axes[1]['data'][-1]:
                        return
                    ind_x = utils.find_index(nav_axes[0]['data'], posx)[0][0]
                    ind_y = utils.find_index(nav_axes[1]['data'], posy)[0][0]
                    data = self.datas.inav[ind_x, ind_y].data

                else:
                    pos = []
                    for ind_view, view in enumerate(self.nav_axes_viewers):
                        p = view.roi_line.getPos()[0]
                        if p < 0 or p > len(nav_axes[ind_view]['data']):
                            return
                        ind = int(np.rint(p))
                        pos.append(ind)
                    data = self.datas.inav.__getitem__(pos).data

                if len(self.datas.axes_manager.signal_shape) == 0:  # means 0D data, plot on 1D viewer
                    self.data_buffer.extend(data)
                    self.ui.viewer1D.show_data([self.data_buffer])

                elif len(self.datas.axes_manager.signal_shape) == 1:  # means 1D data, plot on 1D viewer
                    self.ui.viewer1D.remove_plots()
                    self.ui.viewer1D.x_axis = self.x_axis
                    self.ui.viewer1D.show_data([data])

                elif len(self.datas.axes_manager.signal_shape) == 2:  # means 2D data, plot on 2D viewer
                    self.ui.viewer2D.x_axis = self.x_axis
                    self.ui.viewer2D.y_axis = self.y_axis
                    self.ui.viewer2D.setImage(data)
            except Exception as e:
                logger.exception(str(e))
                self.update_status(utils.getLineInfo() + str(e), wait_time=self.wait_time, log='log')


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    area = DockArea()
    prog = ViewerND(area)
    prog.settings.child(('set_data_4D')).show(True)
    prog.settings.child(('set_data_3D')).show(True)
    prog.settings.child(('set_data_2D')).show(True)
    prog.settings.child(('set_data_1D')).show(True)
    prog.signal_axes_selection()
    area.show()
    sys.exit(app.exec_())

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize, QByteArray, QRectF, QPointF

import sys
from pymodaq.daq_utils.plotting.viewer1D.viewer1D_main import Viewer1D
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D


from collections import OrderedDict
import numpy as np

from pyqtgraph.parametertree import Parameter, ParameterTree
import pymodaq.daq_utils.daq_utils as utils

from pyqtgraph import LinearRegionItem
import copy

from pymodaq.daq_utils.plotting.viewerND.signal import Signal
import datetime


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
    command_DAQ_signal=pyqtSignal(list)
    log_signal=pyqtSignal(str)
    data_to_export_signal=pyqtSignal(OrderedDict) #edict(name=self.DAQ_type,data0D=None,data1D=None,data2D=None)


    def __init__(self,parent=None):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(ViewerND, self).__init__()
        # if parent is None:
        #     raise Exception('no valid parent container, expected dockarea')
            # parent=DockArea()
            # exit(0)

        if parent is None:
            parent = QtWidgets.QWidget()
            parent.show()
        self.parent = parent

        self.wait_time = 2000
        self.viewer_type = 'DataND'  # ☺by default but coul dbe used for 3D visualization

        self.x_axis = dict(data=None, label='', units='')
        self.y_axis = dict(data=None, label='', units='')

        self.data_buffer = []  # convenience list to store 0D data to be displayed
        self.datas = None
        self.datas_settings = None
        # set default data shape case
        self.axes_nav = None
        self.data_axes = None
        # self.set_nav_axes(3)
        self.ui = QObject()  # the user interface
        self.set_GUI()




    @pyqtSlot(OrderedDict)
    def export_data(self, datas):
        datas['acq_time_s'] = datetime.datetime.now().timestamp()
        self.data_to_export_signal.emit(datas)

    def get_data_dimension(self):
        try:
            dimension="("
            for ind,ax in enumerate(self.datas.axes_manager.navigation_shape):
                if ind!=len(self.datas.axes_manager.navigation_shape)-1:
                    dimension+=str(ax)+','
                else:
                    dimension+=str(ax)+'|'
            for ind, ax in enumerate(self.datas.axes_manager.signal_shape):
                if ind!=len(self.datas.axes_manager.signal_shape)-1:
                    dimension+=str(ax)+','
                else:
                    dimension+=str(ax)+')'
            return dimension
        except Exception as e:
            self.update_status(utils.getLineInfo()+str(e), self.wait_time)
            return ""


    def parameter_tree_changed(self,param,changes):
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

            See Also
            --------
            change_viewer, daq_utils.custom_parameter_tree.iter_children
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
                    #if param.name()=='navigator_axes':
                    #    self.update_data_signal()
                    #    self.settings.child('data_shape_settings', 'data_shape').setValue(str(datas_transposed))
                    #    self.set_data(self.datas)


        except Exception as e:
            self.update_status(utils.getLineInfo()+str(e),self.wait_time,'log')

    def set_axis(self,Npts):
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
        axis=np.linspace(0,Npts,Npts,endpoint=False)
        return axis

    def set_data(self,datas_transposed,temp_data=False, **kwargs):
        """
        """
        try:
            self.nav_x_axis = dict(data=None, label='', units='')
            self.nav_y_axis = dict(data=None, label='', units='')
            if len(self.axes_nav)==1 or len(self.axes_nav)==2:#1D Navigator
                self.nav_y_axis['data'] = [0]
                if 'nav_x_axis' in kwargs:
                    if not isinstance(kwargs['nav_x_axis'], dict):
                        self.nav_x_axis['data'] = kwargs['nav_x_axis'][:]
                    else:
                        self.nav_x_axis = copy.deepcopy(kwargs['nav_x_axis'])
                else:
                    self.nav_x_axis['data']=self.set_axis(datas_transposed.axes_manager.navigation_shape[0])


            if len(self.axes_nav)==2:#2D Navigator:
                if 'nav_y_axis' in kwargs:
                    if not isinstance(kwargs['nav_y_axis'], dict):
                        self.nav_y_axis['data'] = kwargs['nav_y_axis'][:]
                    else:
                        self.nav_y_axis = copy.deepcopy(kwargs['nav_y_axis'])
                else:
                    self.nav_y_axis['data']=self.set_axis(datas_transposed.axes_manager.navigation_shape[1])


            ##########################################################################
            #display the correct signal viewer
            if len(datas_transposed.axes_manager.signal_shape)==0: #signal data are 0D
                self.ui.viewer1D.parent.setVisible(True)
                self.ui.viewer2D.parent.setVisible(False)
            elif len(datas_transposed.axes_manager.signal_shape)==1: #signal data are 1D
                self.ui.viewer1D.parent.setVisible(True)
                self.ui.viewer2D.parent.setVisible(False)
            elif len(datas_transposed.axes_manager.signal_shape)==2: #signal data are 2D
                self.ui.viewer1D.parent.setVisible(False)
                self.ui.viewer2D.parent.setVisible(True)
            self.x_axis = dict(data=None, label='', units='')
            self.y_axis = dict(data=None, label='', units='')
            if len(datas_transposed.axes_manager.signal_shape)==1 or len(datas_transposed.axes_manager.signal_shape)==2:#signal data are 1D

                if 'x_axis' in kwargs:
                    if not isinstance(kwargs['x_axis'], dict):
                        self.x_axis['data'] = kwargs['x_axis'][:]
                        self.x_axis = kwargs['x_axis']
                    else:
                        self.x_axis = copy.deepcopy(kwargs['x_axis'])
                else:
                    self.x_axis['data']=self.set_axis(datas_transposed.axes_manager.signal_shape[0])
                if 'y_axis' in kwargs:
                    self.ui.viewer1D.set_axis_label(axis_settings=dict(orientation='left',
                                                                       label=kwargs['y_axis']['label'],
                                                                       units=kwargs['y_axis']['units']))


            if len(datas_transposed.axes_manager.signal_shape)==2:#signal data is 2D
                if 'y_axis' in kwargs:
                    if not isinstance(kwargs['y_axis'], dict):
                        self.y_axis['data'] = kwargs['y_axis'][:]
                        self.y_axis = kwargs['y_axis']
                    else:
                        self.y_axis = copy.deepcopy(kwargs['y_axis'])
                else:
                    self.y_axis['data']=self.set_axis(datas_transposed.axes_manager.signal_shape[1])

            if len(self.axes_nav)==0 or len(self.axes_nav)==1:
                self.update_viewer_data(*self.ui.navigator1D.ui.crosshair.get_positions())
            elif len(self.axes_nav)==2:
                self.update_viewer_data(*self.ui.navigator2D.ui.crosshair.get_positions())



            ##get ROI bounds from viewers if any
            ROI_bounds_1D=[]
            try:
                self.ROI1D.getRegion()
                indexes_values = utils.find_index(self.ui.viewer1D.x_axis, self.ROI1D.getRegion())
                ROI_bounds_1D.append(QPointF(indexes_values[0][0],indexes_values[1][0]))
            except:
                pass

            ROI_bounds_2D=[]
            try:
                ROI_bounds_2D.append(QRectF(self.ROI2D.pos().x(),self.ROI2D.pos().y(),
                                        self.ROI2D.size().x(),self.ROI2D.size().y()))
            except:
                pass



            #############################################################
            #display the correct navigator viewer and set some parameters
            if len(self.axes_nav)==0:#no Navigator
                self.ui.navigator1D.parent.setVisible(False)
                self.ui.navigator2D.parent.setVisible(False)
                self.navigator_label.setVisible(False)
                self.ROI1D.setVisible(False)
                self.ROI2D.setVisible(False)
                navigator_data=[]


            elif len(self.axes_nav)==1:#1D Navigator
                self.ROI1D.setVisible(True)
                self.ROI2D.setVisible(True)
                self.ui.navigator1D.parent.setVisible(True)
                self.ui.navigator2D.parent.setVisible(False)
                self.navigator_label.setVisible(True)
                self.ui.navigator1D.remove_plots()
                self.ui.navigator1D.x_axis=self.nav_x_axis

                if len(datas_transposed.axes_manager.signal_shape) == 0: #signal data are 0D
                    navigator_data=[datas_transposed.data]

                elif len(datas_transposed.axes_manager.signal_shape) == 1:#signal data are 1D
                    if ROI_bounds_1D!=[]:
                        if self.ui.combomath.currentText() == 'Sum':
                            navigator_data=[datas_transposed.isig[pt.x():pt.y()+1].sum((-1)).data for pt in ROI_bounds_1D]
                        elif self.ui.combomath.currentText() == 'Mean':
                            navigator_data = [datas_transposed.isig[pt.x():pt.y() + 1].mean((-1)).data for pt in
                                              ROI_bounds_1D]
                        elif self.ui.combomath.currentText() == 'Half-life':
                            navigator_data = [datas_transposed.isig[pt.x():pt.y() + 1].halflife((-1)).data for pt in
                                              ROI_bounds_1D]
                    else:
                        if self.ui.combomath.currentText() == 'Sum':
                            navigator_data=[datas_transposed.isig[:].sum((-1)).data]
                        elif self.ui.combomath.currentText() == 'Mean':
                            navigator_data = [datas_transposed.isig[:].mean((-1)).data]
                        elif self.ui.combomath.currentText() == 'Half-life':
                            navigator_data = [datas_transposed.isig[:].halflife((-1)).data]

                elif len(datas_transposed.axes_manager.signal_shape)==2:#signal data is 2D
                    if ROI_bounds_2D!=[]:
                        navigator_data=[datas_transposed.isig[rect.x():rect.x()+rect.width(),rect.y():rect.y()+rect.height()].sum((-1,-2)).data for rect in ROI_bounds_2D]
                    else:
                        navigator_data=[datas_transposed.sum((-1,-2)).data]

                else:
                    pass
                if temp_data:
                    self.ui.navigator1D.show_data_temp(navigator_data)
                else:
                    self.ui.navigator1D.show_data(navigator_data)

            elif len(self.axes_nav)==2:#2D Navigator:
                self.ROI1D.setVisible(True)
                self.ROI2D.setVisible(True)

                self.ui.navigator1D.parent.setVisible(False)
                self.ui.navigator2D.parent.setVisible(True)
                self.navigator_label.setVisible(True)
                self.ui.navigator2D.x_axis = self.nav_x_axis
                self.ui.navigator2D.y_axis = self.nav_y_axis

                if len(datas_transposed.axes_manager.signal_shape)==0: #signal data is 0D
                    navigator_data=[datas_transposed.data]

                elif len(datas_transposed.axes_manager.signal_shape)==1: #signal data is 1D
                    if ROI_bounds_1D!=[]:
                        if self.ui.combomath.currentText() == 'Sum':
                            navigator_data=[datas_transposed.isig[pt.x():pt.y()+1].sum((-1)).data for pt in ROI_bounds_1D]
                        elif self.ui.combomath.currentText() == 'Mean':
                            navigator_data = [datas_transposed.isig[pt.x():pt.y() + 1].mean((-1)).data for pt in
                                              ROI_bounds_1D]
                        elif self.ui.combomath.currentText() == 'Half-life':
                            navigator_data = [datas_transposed.isig[pt.x():pt.y() + 1].halflife((-1)).data for pt in
                                              ROI_bounds_1D]
                    else:
                        if self.ui.combomath.currentText() == 'Sum':
                            navigator_data=[datas_transposed.isig[:].sum((-1)).data]
                        elif self.ui.combomath.currentText() == 'Mean':
                            navigator_data = [datas_transposed.isig[:].mean((-1)).data]
                        elif self.ui.combomath.currentText() == 'Half-life':
                            navigator_data = [datas_transposed.isig[:].halflife((-1)).data]

                elif len(datas_transposed.axes_manager.signal_shape)==2: #signal data is 2D
                    if ROI_bounds_2D!=[]:
                        navigator_data=[datas_transposed.isig[rect.x():rect.x()+rect.width(),rect.y():rect.y()+rect.height()].sum((-1,-2)).data for rect in ROI_bounds_2D]
                    else:
                        navigator_data=[datas_transposed.sum((-1,-2)).data]


                else:
                    pass
                if temp_data:
                    self.ui.navigator2D.setImageTemp(*navigator_data)
                else:
                    self.ui.navigator2D.setImage(*navigator_data)


            else:
                raise Exception('No valid Navigator shape')



        except Exception as e:
            self.update_status(utils.getLineInfo()+str(e),self.wait_time,'log')

    def init_ROI(self):

        self.ui.navigator1D.ui.crosshair.set_crosshair_position(np.mean(self.nav_x_axis['data']))
        x, y = self.ui.navigator2D.unscale_axis(np.mean(self.nav_x_axis['data']), np.mean(self.nav_y_axis['data']))
        self.ui.navigator2D.ui.crosshair.set_crosshair_position(x, y)

        self.ROI1D.setRegion((np.min(self.x_axis['data']), np.max(self.x_axis['data'])))

        self.ROI2D.setPos((np.min(self.x_axis['data']), np.min(self.y_axis['data'])))
        self.ROI2D.setSize((np.max(self.x_axis['data']) - np.min(self.x_axis['data']),
                            np.max(self.y_axis['data']) - np.min(self.y_axis['data'])))

        self.update_Navigator()


    def set_data_test(self,data_shape='3D'):


        x=utils.linspace_step(0,20,1)
        y=utils.linspace_step(0,30,1)
        t=utils.linspace_step(0,200,1)
        z=utils.linspace_step(0,200,1)
        datas=np.zeros((len(y),len(x),len(t),len(z)))
        amp=utils.gauss2D(x,7,5,y,12,10)
        for indx in range(len(x)):
            for indy in range(len(y)):
                datas[indy,indx,:,:]=amp[indy,indx]*(utils.gauss2D(z,50+indx*2,20,t,50+3*indy,30)+np.random.rand(len(t),len(z))/10)

        if data_shape=='4D':
            self.show_data(datas,temp_data=False,nav_axes=[2,3])
        elif data_shape=='3D':
            self.show_data(np.sum(datas,axis=3),temp_data=False,nav_axes=[0,1])
        elif data_shape=='2D':
            self.show_data(np.sum(datas,axis=(2,3)))
        elif data_shape=='1D':
            self.show_data(np.sum(datas,axis=(1,2,3)))

    def set_nav_axes(self,Ndim,nav_axes=None):
        self.data_axes=[ind for ind in range(Ndim)]
        if nav_axes is None:
            if Ndim>0:
                self.axes_nav=self.data_axes[0:2]
            else:
                self.axes_nav=self.data_axes[0]
        else:
            self.axes_nav=[Ndim-ind_ax-1 for ind_ax in nav_axes] #because hyperspy array order is reversed compared to numpy....
        self.axes_signal=[ax for ax in self.data_axes if ax not in self.axes_nav]
        self.settings.child('data_shape_settings', 'navigator_axes').setValue(dict(all_items=[str(ax) for ax in self.data_axes],selected=[str(ax) for ax in self.axes_nav]))


    def set_GUI(self):
        """

        """
        #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

        main_layout=QtWidgets.QGridLayout()
        self.parent.setLayout(main_layout)

        Vsplitter=QtWidgets.QSplitter(Qt.Vertical)
        #Hsplitter=QtWidgets.QSplitter(Qt.Horizontal)


        #%%create status bar
        self.ui.statusbar=QtWidgets.QStatusBar()
        self.ui.statusbar.setMaximumHeight(25)
        Vsplitter.addWidget(self.ui.statusbar)




        params=[
            {'title': 'set data:', 'name': 'set_data_4D', 'type': 'action', 'visible': False},
            {'title': 'set data:', 'name': 'set_data_3D', 'type': 'action', 'visible': False},
            {'title': 'set data:', 'name': 'set_data_2D', 'type': 'action', 'visible': False},
            {'title': 'set data:', 'name': 'set_data_1D', 'type': 'action', 'visible': False},
            {'title': 'Signal shape', 'name': 'data_shape_settings', 'type': 'group', 'children': [
                    {'title': 'Data shape:', 'name': 'data_shape', 'type': 'str', 'value': "", 'readonly': True},
                    {'title': 'Navigator axes:','name': 'navigator_axes', 'type': 'itemselect'},
                    {'title': 'Set Nav axes:', 'name': 'set_nav_axes', 'type': 'action', 'visible': True},
                        ]},
                ]

        self.settings=Parameter.create(name='Param', type='group', children=params)
        ##self.signal_axes_selection()

        #connecting from tree
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)#any changes on the settings
        self.settings.child(('set_data_1D')).sigActivated.connect(lambda : self.set_data_test('1D'))
        self.settings.child(('set_data_2D')).sigActivated.connect(lambda : self.set_data_test('2D'))
        self.settings.child(('set_data_3D')).sigActivated.connect(lambda : self.set_data_test('3D'))
        self.settings.child(('set_data_4D')).sigActivated.connect(lambda : self.set_data_test('4D'))
        self.settings.child('data_shape_settings','set_nav_axes').sigActivated.connect(self.update_data)
        ##%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        ##% 1D signalviewer
        viewer1D_widget=QtWidgets.QWidget()
        self.ui.viewer1D=Viewer1D(viewer1D_widget)
        self.ROI1D = LinearRegionItem()
        self.ui.viewer1D.viewer.plotwidget.plotItem.addItem(self.ROI1D)
        self.ui.combomath = QtWidgets.QComboBox()
        self.ui.combomath.addItems(['Sum', 'Mean', 'Half-life'])
        self.ui.viewer1D.ui.horizontalLayout.insertWidget(4, self.ui.combomath)
        self.ui.combomath.currentIndexChanged.connect(self.update_Navigator)

        self.ROI1D.sigRegionChangeFinished.connect(self.update_Navigator)
        #% 2D viewer Dock
        viewer2D_widget=QtWidgets.QWidget()
        self.ui.viewer2D=Viewer2D(viewer2D_widget)
        self.ui.viewer2D.ui.Ini_plot_pb.setVisible(False)
        self.ui.viewer2D.ui.FlipUD_pb.setVisible(False)
        self.ui.viewer2D.ui.FlipLR_pb.setVisible(False)
        self.ui.viewer2D.ui.rotate_pb.setVisible(False)
        self.ui.viewer2D.ui.auto_levels_pb.click()
        self.ui.viewer2D.ui.ROIselect_pb.click()
        self.ROI2D = self.ui.viewer2D.ui.ROIselect
        self.ui.viewer2D.ROI_select_signal.connect(self.update_Navigator)

        ###dock_viewer=Dock('Signal')
        ###dock_viewer.addWidget(viewer1D_widget)
        ###dock_viewer.addWidget(viewer2D_widget)


        ##%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        ##% Navigator viewer Dock
        navigator1D_widget=QtWidgets.QWidget()
        self.ui.navigator1D=Viewer1D(navigator1D_widget)
        self.ui.navigator1D.ui.crosshair.crosshair_dragged.connect(self.update_viewer_data)
        self.ui.navigator1D.ui.crosshair_pb.click()
        self.ui.navigator1D.data_to_export_signal.connect(self.export_data)
        navigator2D_widget=QtWidgets.QWidget()
        self.ui.navigator2D=Viewer2D(navigator2D_widget)
        self.ui.navigator2D.ui.auto_levels_pb.click()
        self.ui.navigator2D.crosshair_dragged.connect(self.update_viewer_data) #export scaled position in conjonction with 2D scaled axes
        self.ui.navigator2D.ui.crosshair_pb.click()
        self.ui.navigator2D.data_to_export_signal.connect(self.export_data)


        widg0=QtWidgets.QWidget()
        VLayout0=QtWidgets.QVBoxLayout()
        self.navigator_label=QtWidgets.QLabel('Navigation View')
        self.navigator_label.setMaximumHeight(15)
        VLayout0.addWidget(self.navigator_label)
        VLayout0.addWidget(navigator1D_widget)
        VLayout0.addWidget(navigator2D_widget)
        widg0.setLayout(VLayout0)
        Vsplitter.insertWidget(0,widg0)

        widg1=QtWidgets.QWidget()
        VLayout1=QtWidgets.QVBoxLayout()
        self.viewer_label=QtWidgets.QLabel('Data View')
        self.viewer_label.setMaximumHeight(15)
        VLayout1.addWidget(self.viewer_label)
        VLayout1.addWidget(viewer1D_widget)
        VLayout1.addWidget(viewer2D_widget)
        widg1.setLayout(VLayout1)
        Vsplitter.insertWidget(1,widg1)


        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/cartesian.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.set_signals_pb_1D=QtWidgets.QPushButton('')
        self.ui.set_signals_pb_1D.setToolTip('Change navigation/signal axes')
        self.ui.set_signals_pb_1D_bis = QtWidgets.QPushButton('')
        self.ui.set_signals_pb_1D_bis.setToolTip('Change navigation/signal axes')
        self.ui.set_signals_pb_1D.setIcon(icon)
        self.ui.set_signals_pb_1D_bis.setIcon(icon)
        self.ui.set_signals_pb_2D=QtWidgets.QPushButton('')
        self.ui.set_signals_pb_2D.setToolTip('Change navigation/signal axes')
        self.ui.set_signals_pb_2D.setIcon(icon)
        self.ui.set_signals_pb_2D_bis = QtWidgets.QPushButton('')
        self.ui.set_signals_pb_2D_bis.setToolTip('Change navigation/signal axes')
        self.ui.set_signals_pb_2D_bis.setIcon(icon)

        self.ui.navigator1D.ui.horizontalLayout.insertWidget(0,self.ui.set_signals_pb_1D)
        self.ui.navigator2D.ui.horizontalLayout_2.insertWidget(0,self.ui.set_signals_pb_2D)
        self.ui.viewer1D.ui.horizontalLayout.insertWidget(0, self.ui.set_signals_pb_1D_bis)
        self.ui.viewer2D.ui.horizontalLayout_2.insertWidget(0, self.ui.set_signals_pb_2D_bis)

        main_layout.addWidget(Vsplitter)

        self.ui.set_signals_pb_1D.clicked.connect(self.signal_axes_selection)
        self.ui.set_signals_pb_2D.clicked.connect(self.signal_axes_selection)
        self.ui.set_signals_pb_1D_bis.clicked.connect(self.signal_axes_selection)
        self.ui.set_signals_pb_2D_bis.clicked.connect(self.signal_axes_selection)

        #to start: display as default a 2D navigator and a 1D viewer
        self.ui.navigator1D.parent.setVisible(False)
        self.ui.viewer2D.parent.setVisible(True)


    def show_data_temp(self,datas,nav_axes=None, **kwargs):
        """
        """
        self.show_data(datas,temp_data=True,nav_axes=nav_axes, **kwargs)


    def show_data(self,datas,temp_data=False,nav_axes=None, **kwargs):
        """Display datas as a hyperspaced dataset
        only one numpy ndarray should be used
        """
        self.data_buffer = []
        try:
            if self.data_axes is not None:
                if datas.ndim != len(self.data_axes) or self.axes_nav != nav_axes:
                    self.set_nav_axes(datas.ndim, nav_axes) #init the list of axes and set the preset to nav_axes
            else:
                self.set_nav_axes(datas.ndim, nav_axes) #init the list of axes and set the preset to nav_axes

            #self.datas=hs.signals.BaseSignal(datas)
            self.datas = Signal(datas)
            self.datas_settings = kwargs
            self.update_data_signal()

            self.settings.child('data_shape_settings', 'data_shape').setValue(self.get_data_dimension())
            self.set_data(self.datas, temp_data=temp_data, **kwargs)

        except Exception as e:
            self.update_status(utils.getLineInfo()+str(e),self.wait_time,'log')


    def signal_axes_selection(self):
        self.ui.settings_tree=ParameterTree()
        self.ui.settings_tree.setMinimumWidth(300)
        self.ui.settings_tree.setParameters(self.settings, showTop=False)
        self.signal_axes_widget = QtWidgets.QWidget()
        layout=QtWidgets.QVBoxLayout()
        self.signal_axes_widget .setLayout(layout)
        layout.addWidget(self.ui.settings_tree)
        self.signal_axes_widget.adjustSize()
        self.signal_axes_widget.show()

    def update_data(self):
        self.update_data_signal()
        self.settings.child('data_shape_settings', 'data_shape').setValue(self.get_data_dimension())
        self.set_data(self.datas)

    def update_data_signal(self):
        try:
            self.axes_nav=[int(ax) for ax in self.settings.child('data_shape_settings', 'navigator_axes').value()['selected']]
            self.axes_signal=[ax for ax in self.data_axes if ax not in self.axes_nav]


            self.datas=self.datas.transpose(signal_axes=self.axes_signal,navigation_axes=self.axes_nav)


        except Exception as e:
            self.update_status(utils.getLineInfo()+str(e),self.wait_time,'log')

    def update_Navigator(self):
        ##self.update_data_signal()
        self.set_data(self.datas, **self.datas_settings)


    def update_status(self,txt,wait_time=1000,log=''):
        """
            | Update the statut bar showing a Message with a delay of wait_time ms (1s by default)

            ================ ======== ===========================
            **Parameters**   **Type**     **Description**

             *txt*            string   the text message to show

             *wait_time*      int      the delay time of showing
            ================ ======== ===========================

        """
        self.ui.statusbar.showMessage(txt,wait_time)
        if log=='log':
            self.log_signal.emit(txt)


    def update_viewer_data(self,posx=0,posy=0):
        """
            |PyQt5 slot triggered by the crosshair signal from the 1D or 2D Navigator
            | Update the viewer informations from an x/y given position and store data.
            | Ruled by the viewer type (0D,1D,2D)

            ================ ========= ==============================
            **Parameters**   **Type**        **Description**

             *posx*           int       the x position of the viewer

             *posy*           int       the y position of the viewer
            ================ ========= ==============================

            See Also
            --------
            update_status
        """
        try:
            #datas_transposed=self.update_data_signal(self.datas)
            if len(self.axes_nav)==0:
                data=self.datas.data

            elif len(self.axes_nav)==1:
                ind_x=utils.find_index(self.nav_x_axis['data'],posx)[0][0]
                data=self.datas.inav[ind_x].data
            elif len(self.axes_nav)==2:
                ind_x=utils.find_index(self.nav_x_axis['data'],posx)[0][0]
                ind_y=utils.find_index(self.nav_y_axis['data'],posy)[0][0]
                data=self.datas.inav[ind_x,ind_y].data

            if len(self.datas.axes_manager.signal_shape)==0:#means 0D data, plot on 1D viewer
                self.data_buffer.extend(data)
                self.ui.viewer1D.show_data([self.data_buffer])

            elif len(self.datas.axes_manager.signal_shape)==1: #means 1D data, plot on 1D viewer
                self.ui.viewer1D.remove_plots()
                self.ui.viewer1D.x_axis=self.x_axis
                self.ui.viewer1D.show_data([data])

            elif len(self.datas.axes_manager.signal_shape)==2: #means 2D data, plot on 2D viewer
                self.ui.viewer2D.x_axis = self.x_axis
                self.ui.viewer2D.y_axis = self.y_axis
                self.ui.viewer2D.setImage(data)
        except Exception as e:
            self.update_status(utils.getLineInfo()+str(e),wait_time=self.wait_time)



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = QtWidgets.QWidget()

    prog = ViewerND()
    prog.settings.child(('set_data_4D')).show(True)
    prog.settings.child(('set_data_3D')).show(True)
    prog.settings.child(('set_data_2D')).show(True)
    prog.settings.child(('set_data_1D')).show(True)
    prog.signal_axes_selection()
    form.show()
    sys.exit(app.exec_())
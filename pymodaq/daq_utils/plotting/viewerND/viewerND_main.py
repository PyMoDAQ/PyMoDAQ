from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize, QByteArray, QRectF, QPointF

import sys
import pymodaq
from pymodaq.daq_utils.plotting.viewer0D.viewer0D_main import Viewer0D
from pymodaq.daq_utils.plotting.viewer1D.viewer1D_main import Viewer1D
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D


from collections import OrderedDict
import numpy as np

from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree
import pymodaq.daq_utils.daq_utils as utils
import os
from easydict import EasyDict as edict
from pyqtgraph.dockarea import DockArea, Dock
import tables
from pymodaq.daq_utils.plotting.viewerND.signal import Signal
#import hyperspy.api as hs


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
        if parent is None:
            raise Exception('no valid parent container, expected dockarea')
            # parent=DockArea()
            # exit(0)

        if parent is None:
            parent=QtWidgets.QWidget()
        self.parent=parent

        self.wait_time=2000
        self.viewer_type='DataND' #☺by default but coul dbe used for 3D visualization

        self.x_axis=None
        self.y_axis=None

        self.data_buffer=[] #convenience list to store 0D data to be displayed
        self.datas=None

        self.ui=QObject() #the user interface
        self.set_GUI()

        #set default data shape case
        self.axes_nav=None
        self.data_axes=None
        #self.set_nav_axes(3)


    @pyqtSlot(OrderedDict)
    def export_data(self,datas):
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
            self.update_status(str(e), self.wait_time)
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
            self.update_status(str(e),self.wait_time,'log')

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

    def set_data(self,datas_transposed,temp_data=False):
        """
        """
        try:
            ##########################################################################
            #display the correct signal viewer
            if len(datas_transposed.axes_manager.signal_shape)==0: #signal data are 0D
                self.ui.viewer1D.parent.setVisible(True)
                self.ui.viewer2D.parent.setVisible(False)
            elif len(datas_transposed.axes_manager.signal_shape)==1: #signal data are 2D
                self.ui.viewer1D.parent.setVisible(True)
                self.ui.viewer2D.parent.setVisible(False)
            elif len(datas_transposed.axes_manager.signal_shape)==2: #signal data are 2D
                self.ui.viewer1D.parent.setVisible(False)
                self.ui.viewer2D.parent.setVisible(True)


            ##get ROI bounds from viewers if any
            ROI_bounds_1D=[]
            for ind_region,region in enumerate(self.ui.viewer1D.linear_regions):
                indexes_values=utils.find_index(self.ui.viewer1D.x_axis,region.getRegion()) #get index for boundaries if xaxis not in pixels
                ROI_bounds_1D.append(QPointF(indexes_values[0][0],indexes_values[1][0]))

            ROI_bounds_2D=[]
            for roi in self.ui.viewer2D.ui.ROIs:

                ROI_bounds_2D.append(QRectF(self.ui.viewer2D.ui.ROIs[roi].pos().x(),self.ui.viewer2D.ui.ROIs[roi].pos().y(),
                                            self.ui.viewer2D.ui.ROIs[roi].size().x(),self.ui.viewer2D.ui.ROIs[roi].size().y()))


            #############################################################
            #display the correct navigator viewer and set some parameters
            if len(self.axes_nav)==0:#no Navigator
                self.ui.navigator1D.parent.setVisible(False)
                self.ui.navigator2D.parent.setVisible(False)
                navigator_data=[]
                if len(datas_transposed.axes_manager.signal_shape)==1:#signal data are 1D
                    self.x_axis=self.set_axis(datas_transposed.axes_manager.signal_shape[0])

                elif len(datas_transposed.axes_manager.signal_shape)==2:#signal data is 2D
                    self.x_axis=self.set_axis(datas_transposed.axes_manager.signal_shape[0])
                    self.y_axis=self.set_axis(datas_transposed.axes_manager.signal_shape[1])


            elif len(self.axes_nav)==1:#1D Navigator
                self.ui.navigator1D.parent.setVisible(True)
                self.ui.navigator2D.parent.setVisible(False)
                self.nav_x_axis=self.set_axis(datas_transposed.axes_manager.navigation_shape[0])
                self.nav_y_axis=[0]
                self.ui.navigator1D.remove_plots()
                self.ui.navigator1D.x_axis=self.nav_x_axis

                if len(datas_transposed.axes_manager.signal_shape)==0: #signal data are 0D
                    navigator_data=[datas_transposed.data]

                elif len(datas_transposed.axes_manager.signal_shape)==1:#signal data are 1D
                    self.x_axis=self.set_axis(datas_transposed.axes_manager.signal_shape[0])
                    if ROI_bounds_1D!=[]:
                        navigator_data=[datas_transposed.isig[pt.x():pt.y()+1].sum((-1)).data for pt in ROI_bounds_1D]
                    else:
                        navigator_data=[datas_transposed.isig[:].sum((-1)).data]

                elif len(datas_transposed.axes_manager.signal_shape)==2:#signal data is 2D
                    self.x_axis=self.set_axis(datas_transposed.axes_manager.signal_shape[0])
                    self.y_axis=self.set_axis(datas_transposed.axes_manager.signal_shape[1])

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
                self.ui.navigator1D.parent.setVisible(False)
                self.ui.navigator2D.parent.setVisible(True)
                self.nav_x_axis=self.set_axis(datas_transposed.axes_manager.navigation_shape[0])
                self.nav_y_axis=self.set_axis(datas_transposed.axes_manager.navigation_shape[1])

                self.ui.navigator2D.set_scaling_axes(
                    scaling_options=edict(scaled_xaxis=edict(label="x axis",units=None,offset=np.min(self.nav_x_axis),scaling=self.nav_x_axis[1]-self.nav_x_axis[0]),
                                        scaled_yaxis=edict(label="y axis",units=None,offset=np.min(self.nav_y_axis),scaling=self.nav_y_axis[1]-self.nav_y_axis[0])))
                if len(datas_transposed.axes_manager.signal_shape)==0: #signal data is 0D
                    navigator_data=[datas_transposed.data]

                elif len(datas_transposed.axes_manager.signal_shape)==1: #signal data is 1D
                    self.x_axis=self.set_axis(datas_transposed.axes_manager.signal_shape[0])
                    if ROI_bounds_1D!=[]:
                        navigator_data=[datas_transposed.isig[pt.x():pt.y()+1].sum(-1).data for pt in ROI_bounds_1D]
                    else:
                        navigator_data=[datas_transposed.sum(-1).data]

                elif len(datas_transposed.axes_manager.signal_shape)==2: #signal data is 2D
                    self.x_axis=self.set_axis(datas_transposed.axes_manager.signal_shape[0])
                    self.y_axis=self.set_axis(datas_transposed.axes_manager.signal_shape[1])
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


            if len(self.axes_nav)==1:
                self.update_viewer_data(self.ui.navigator1D.ui.crosshair.get_positions())
            elif len(self.axes_nav)==2:
                self.update_viewer_data(self.ui.navigator2D.ui.crosshair.get_positions())

        except Exception as e:
            self.update_status(str(e),self.wait_time,'log')

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
        self.ui.viewer1D.ROI_changed_finished.connect(self.update_Navigator)
        #% 2D viewer Dock
        viewer2D_widget=QtWidgets.QWidget()
        self.ui.viewer2D=Viewer2D(viewer2D_widget)
        self.ui.viewer2D.ui.auto_levels_pb.click()
        self.ui.viewer2D.ROI_changed_finished.connect(self.update_Navigator)

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
        label0=QtWidgets.QLabel('Navigation View')
        label0.setMaximumHeight(15)
        VLayout0.addWidget(label0)
        VLayout0.addWidget(navigator1D_widget)
        VLayout0.addWidget(navigator2D_widget)
        widg0.setLayout(VLayout0)
        Vsplitter.insertWidget(0,widg0)

        widg1=QtWidgets.QWidget()
        VLayout1=QtWidgets.QVBoxLayout()
        label1=QtWidgets.QLabel('Data View')
        label1.setMaximumHeight(15)
        VLayout1.addWidget(label1)
        VLayout1.addWidget(viewer1D_widget)
        VLayout1.addWidget(viewer2D_widget)
        widg1.setLayout(VLayout1)
        Vsplitter.insertWidget(1,widg1)


        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/Labview_icons/Icon_Library/cartesian.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.ui.set_signals_pb_1D=QtWidgets.QPushButton('')
        self.ui.set_signals_pb_1D.setIcon(icon)
        self.ui.set_signals_pb_2D=QtWidgets.QPushButton('')
        self.ui.set_signals_pb_2D.setIcon(icon)

        self.ui.navigator1D.ui.horizontalLayout.insertWidget(0,self.ui.set_signals_pb_1D)
        self.ui.navigator2D.ui.horizontalLayout_2.insertWidget(0,self.ui.set_signals_pb_2D)

        main_layout.addWidget(Vsplitter)

        self.ui.set_signals_pb_1D.clicked.connect(self.signal_axes_selection)
        self.ui.set_signals_pb_2D.clicked.connect(self.signal_axes_selection)

        #to start: display as default a 2D navigator and a 1D viewer
        self.ui.navigator1D.parent.setVisible(False)
        self.ui.viewer2D.parent.setVisible(True)


    def show_data_temp(self,datas,nav_axes=None):
        """
        """
        self.show_data(datas,temp_data=True,nav_axes=nav_axes)


    def show_data(self,datas,temp_data=False,nav_axes=None):
        """Display datas as a hyperspaced dataset
        only one numpy ndarray should be used
        """
        self.data_buffer=[]
        try:
            if self.data_axes is not None:
                if datas.ndim != len(self.data_axes) or self.axes_nav != nav_axes:
                    self.set_nav_axes(datas.ndim, nav_axes) #init the list of axes and set the preset to nav_axes
            else:
                self.set_nav_axes(datas.ndim,nav_axes) #init the list of axes and set the preset to nav_axes

            #self.datas=hs.signals.BaseSignal(datas)
            self.datas=Signal(datas)
            self.update_data_signal()

            self.settings.child('data_shape_settings', 'data_shape').setValue(self.get_data_dimension())
            self.set_data(self.datas,temp_data=temp_data)

        except Exception as e:
            self.update_status(str(e),self.wait_time,'log')


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
            self.update_status(str(e),self.wait_time,'log')

    def update_Navigator(self):
        ##self.update_data_signal()
        self.set_data(self.datas)


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
                ind_x=utils.find_index(self.nav_x_axis,posx)[0][0]
                data=self.datas.inav[ind_x].data
            elif len(self.axes_nav)==2:
                ind_x=utils.find_index(self.nav_x_axis,posx)[0][0]
                ind_y=utils.find_index(self.nav_y_axis,posy)[0][0]
                data=self.datas.inav[ind_x,ind_y].data

            if len(self.datas.axes_manager.signal_shape)==0:#means 0D data, plot on 1D viewer
                self.data_buffer.extend(data)
                self.ui.viewer1D.show_data([self.data_buffer])

            elif len(self.datas.axes_manager.signal_shape)==1: #means 1D data, plot on 1D viewer
                self.ui.viewer1D.remove_plots()
                self.ui.viewer1D.x_axis=self.x_axis
                self.ui.viewer1D.show_data([data])

            elif len(self.datas.axes_manager.signal_shape)==2: #means 2D data, plot on 2D viewer
                self.ui.viewer2D.set_scaling_axes(
                        scaling_options=edict(scaled_xaxis=edict(label="x axis",units=None,offset=np.min(self.x_axis),scaling=self.x_axis[1]-self.x_axis[0]),
                                            scaled_yaxis=edict(label="y axis",units=None,offset=np.min(self.y_axis),scaling=self.y_axis[1]-self.y_axis[0])))
                self.ui.viewer2D.setImage(data)
        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)




class BaseSignal(object):


    def __init__(self, data, **kwds):
        """Create a Signal from a numpy array.

        Parameters
        ----------
        data : numpy array
           The signal data. It can be an array of any dimensions.
        axes : dictionary (optional)
            Dictionary to define the axes (see the
            documentation of the AxesManager class for more details).
        """

        self.data = data
        self.nav_axes=[ind for ind in range(len(data.shape))]
        self.sig_axes=[]


    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        from dask.array import Array
        if isinstance(value, Array):
            if not value.ndim:
                value = value.reshape((1,))
            self._data = value
        else:
            self._data = np.atleast_1d(np.asanyarray(value))


    def __repr__(self):
        unfolded = ""
        string = '<'
        string += ", %sdimensions: %s" % (
            self.nav_axes,
            self.axes_manager._get_dimension_str())

        string += '>'

        return string

    def _get_dimension_str(self):
        string = "("
        for axis in self.data[self.nav_axes]:
            string += str(axis.size) + ", "
        string = string.rstrip(", ")
        string += "|"
        for axis in self.data[self.sig_axes]:
            string += str(axis.size) + ", "
        string = string.rstrip(", ")
        string += ")"
        return string

def iterable_not_string(thing):
    return isinstance(thing, collections.Iterable) and \
        not isinstance(thing, str)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = QtWidgets.QWidget();

    prog = ViewerND(form)
    prog.settings.child(('set_data_4D')).show(True)
    prog.settings.child(('set_data_3D')).show(True)
    prog.settings.child(('set_data_2D')).show(True)
    prog.settings.child(('set_data_1D')).show(True)
    prog.signal_axes_selection()
    form.show()
    sys.exit(app.exec_())
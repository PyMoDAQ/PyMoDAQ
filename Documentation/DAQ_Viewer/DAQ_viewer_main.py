# -*- coding: utf-8 -*-
"""
Created on Wed Jan 10 16:54:14 2018

@author: Weber Sébastien
"""

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize

import sys
import PyMoDAQ
from PyMoDAQ.DAQ_Viewer.DAQ_GUI_settings import Ui_Form

from PyMoDAQ.DAQ_Utils.plotting.viewer0D.viewer0D_main import Viewer0D
from PyMoDAQ.DAQ_Utils.plotting.viewer1D.viewer1D_main import Viewer1D
from PyMoDAQ.DAQ_Utils.plotting.image_view_multicolor.image_view_multicolor import Image_View_Multicolor

import PyMoDAQ.DAQ_Utils.DAQ_utils as DAQ_utils
from PyMoDAQ.DAQ_Utils.DAQ_utils import ThreadCommand
from PyMoDAQ.DAQ_Viewer import hardware2D
from PyMoDAQ.DAQ_Viewer import hardware1D
from PyMoDAQ.DAQ_Viewer import hardware0D
from PyMoDAQ.DAQ_Viewer.hardware2D import DAQ_2DViewer_Det_type
from PyMoDAQ.DAQ_Viewer.hardware1D import DAQ_1DViewer_Det_type
from PyMoDAQ.DAQ_Viewer.hardware0D import DAQ_0DViewer_Det_type


from collections import OrderedDict
import pyqtgraph as pg
import numpy as np

from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import PyMoDAQ.DAQ_Utils.custom_parameter_tree as custom_tree
import os
from easydict import EasyDict as edict


from pyqtgraph.dockarea import DockArea, Dock
from pathlib import Path
import pickle
import datetime
import tables
import socket, select

from enum import IntEnum

class QSpinBox_ro(QtWidgets.QSpinBox):
    def __init__(self, **kwargs):
        super(QtWidgets.QSpinBox,self).__init__()
        self.setMaximum(100000)
        self.setReadOnly(True)
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)

class DAQ_Viewer(QtWidgets.QWidget,QObject):
    """
        ========================= =======================================
        **Attributes**             **Type**

        *command_detector*         instance of pyqt Signal
        *grab_done_signal*         instance of pyqt Signal
        *quit_signal*              instance of pyqt Signal
        *update_settings_signal*   instance of pyqt Signal
        *overshoot_signal*         instance of pyqt Signal
        *log_signal*               instance of pyqt Signal
        *params*                   dictionnary list

        *widgetsettings*           instance of QWidget
        *title*                    string
        *DAQ_type*                 string
        *dockarea*                 instance of DockArea
        *bkg*                      ???
        *filters*                  instance of tables.Filters
        *settings*                 instance of pyqtgraph parameter tree
        *measurement_module*       ???
        *detector*                 instance of DAQ_Detector
        *wait_time*                int
        *save_file_pathname*       string
        *ind_continuous_grab*      int
        *Initialized_state*        boolean
        *snapshot_pathname*        string
        *x_axis*                   1D numpy array
        *y_axis*                   1D numpy array
        *current_datas*            dictionnary
        *data_to_save_export*      ordered dictionnary
        *do_save_data*             boolean
        *do_continuous_save*       boolean
        *file_continuous_save*     ???
        ========================= =======================================
    """
    command_detector=pyqtSignal(ThreadCommand)
    grab_done_signal=pyqtSignal(OrderedDict) #OrderedDict(name=self.title,x_axis=None,y_axis=None,z_axis=None,data0D=None,data1D=None,data2D=None)
    quit_signal=pyqtSignal()
    #used to trigger a saving of the data (from programatical function
    # snapshot) and to trigger the end of acquisition from main program using this module
    update_settings_signal=pyqtSignal(edict)
    overshoot_signal=pyqtSignal(bool)
    log_signal=pyqtSignal(str)
    params = [
        {'title': 'Main Settings:','name': 'main_settings','type': 'group','children':[
            {'title': 'PyMoDAQ type:','name': 'DAQ_type', 'type': 'list', 'values': ['DAQ0D','DAQ1D','DAQ2D']},
            {'title': 'Detector type:','name': 'detector_type', 'type': 'str', 'value': '', 'readonly': True},
            {'title': 'Naverage', 'name': 'Naverage', 'type': 'int', 'default': 1, 'value': 1, 'min': 1},
            {'title': 'Show averaging:', 'name': 'show_averaging', 'type': 'bool', 'default': False, 'value': False},
            {'title': 'Live averaging:', 'name': 'live_averaging', 'type': 'bool', 'default': False, 'value': False},
            {'title': 'Wait time (ms)', 'name': 'wait_time', 'type': 'int', 'default': 0, 'value': 0, 'min': 0},
            {'title': 'Overshoot options:','name':'overshoot','type':'group', 'visible': False,'children':[
                    {'title': 'Stop if overshoot:', 'name': 'stop_overshoot', 'type': 'bool', 'value': False},
                    {'title': 'Overshoot value:', 'name': 'overshoot_value', 'type': 'float', 'value': 0}]},
            {'title': 'Axis options:','name':'axes','type':'group', 'visible': False,'children':[
                    {'title': 'X axis:','name':'xaxis','type':'group','children':[
                        {'title': 'Label:', 'name': 'xlabel', 'type': 'str', 'value': "x axis"},
                        {'title': 'Units:', 'name': 'xunits', 'type': 'str', 'value': "pxls"},
                        {'title': 'Offset:', 'name': 'xoffset', 'type': 'float', 'default': 0., 'value': 0.},
                        {'title': 'Scaling', 'name': 'xscaling', 'type': 'float', 'default': 1., 'value': 1.},
                        ]},
                    {'title': 'Y axis:','name':'yaxis','type':'group','children':[
                        {'title': 'Label:', 'name': 'ylabel', 'type': 'str', 'value': "x axis"},
                        {'title': 'Units:', 'name': 'yunits', 'type': 'str', 'value': "pxls"},
                        {'title': 'Offset:', 'name': 'yoffset', 'type': 'float', 'default': 0., 'value': 0.},
                        {'title': 'Scaling', 'name': 'yscaling', 'type': 'float', 'default': 1., 'value': 1.},
                        ]},
            ]}]},
        {'title': 'Save Settings','name': 'save_settings','type': 'group','children':[
            {'title': 'Base Path:', 'name': 'base_path', 'type': 'browsepath', 'default': 'D:/Data', 'value': 'D:/Data'},
            {'title': 'Base Name:', 'name': 'base_name', 'type': 'str', 'default': 'Data_0D_Viewer', 'value': 'Data_0D_Viewer'},
            {'title': 'Current Path::', 'name': 'current_file_name', 'type': 'text', 'default': 'D:/Data', 'value': 'D:/Data', 'readonly': True},
            {'title': 'Do Save:', 'name': 'do_save', 'type': 'bool', 'default': False, 'value': False},
            ]},
        {'title': 'Detector Settings','name': 'detector_settings', 'type': 'group'}
        ]

    def __init__(self,parent,dock_settings=None,dock_viewer=None,title="Testing",DAQ_type="DAQ2D",preset=None,init=False):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(DAQ_Viewer,self).__init__()


        self.ui=Ui_Form()
        widgetsettings=QtWidgets.QWidget()
        self.ui.setupUi(widgetsettings)

        self.title=title
        self.ui.title_label.setText(self.title)
        self.DAQ_type=DAQ_type
        self.dockarea=parent
        self.bkg=None #buffer to store background
        self.filters = tables.Filters(complevel=5)        #options to save data to h5 file using compression zlib library and level 5 compression

        #create main parameter tree
        self.ui.settings_tree = ParameterTree()
        self.ui.settings_layout.addWidget(self.ui.settings_tree,10)
        self.ui.settings_tree.setMinimumWidth(300)
        self.settings=Parameter.create(name='Settings', type='group', children=self.params)
        self.settings.child('main_settings','DAQ_type').setValue(self.DAQ_type)
        self.ui.settings_tree.setParameters(self.settings, showTop=False)
        #connecting from tree
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)#any changes on the settings will update accordingly the detector

        if dock_settings is not None:
            self.ui.settings_dock =dock_settings
            self.ui.settings_dock.setTitle(title+"_Settings")
        else:
            self.ui.settings_dock = Dock(title+"_Settings", size=(10, 10))
            self.dockarea.addDock(self.ui.settings_dock)

        if dock_viewer is not None:
            self.ui.viewer_dock =dock_viewer
            self.ui.viewer_dock.setTitle(title+"_Viewer")
        else:
            self.ui.viewer_dock = Dock(title+"_Viewer", size=(500,300), closable=False)
            self.dockarea.addDock(self.ui.viewer_dock,'right',self.ui.settings_dock)


        viewer_widget=QtWidgets.QWidget()
        self.ui.temp_viewer_widget=QtWidgets.QWidget()
        self.change_viewer(DAQ_type)
        #if DAQ_type=="DAQ0D":
        #    self.ui.viewer=Viewer0D(viewer_widget)
        #    self.ui.temporary_viewer=Viewer0D(self.ui.temp_viewer_widget)
        #    self.detector_types=DAQ_0DViewer_Det_type.names()
        #elif DAQ_type=="DAQ1D":
        #    self.ui.viewer=Viewer1D(viewer_widget)
        #    self.ui.temporary_viewer=Viewer1D(self.ui.temp_viewer_widget)
        #    self.detector_types=DAQ_1DViewer_Det_type.names()
        #    self.settings.child(('save_settings')).hide()
        #elif DAQ_type=="DAQ2D":
        #    self.ui.viewer=Image_View_Multicolor(viewer_widget)
        #    self.ui.temporary_viewer=Image_View_Multicolor(self.ui.temp_viewer_widget)
        #    self.detector_types=DAQ_2DViewer_Det_type.names()
        #    self.ui.viewer.set_scaling_axes(self.get_scaling_options())
        #    self.settings.child('main_settings','axes').show()
        #    self.settings.child(('save_settings')).hide()

        #self.ui.temp_viewer_widget.setVisible(False)

        #self.ui.viewer_dock.addWidget(viewer_widget)
        self.ui.settings_dock.addWidget(widgetsettings)





        self.ui.viewer.data_to_export_signal.connect(self.get_data_from_viewer)

        ##Setting detector types
        self.ui.Detector_type_combo.clear()
        self.ui.Detector_type_combo.addItems(self.detector_types)



        self.measurement_module=None
        self.detector=None
        self.set_enabled_grab_buttons(enable=False)
        self.set_enabled_Ini_buttons(enable=True)

        self.wait_time=1000
        self.save_file_pathname=None # to store last active path, will be an Path object
        self.ind_continuous_grab=0

        self.ui.Ini_state_LED.clickable=False
        self.ui.Ini_state_LED.set_as_false()
        self.Initialized_state=False
        self.measurement_module=None
        self.snapshot_pathname=None


        self.x_axis=None
        self.y_axis=None
        self.current_datas=None
        #edict to be send to the DAQ_Measurement module from 1D traces if any

        self.data_to_save_export=edict(name=self.title,x_axis=None,y_axis=None,z_axis=None,data0D=None,data1D=None,data2D=None)
        self.do_save_data=False
        self.do_continuous_save=False
        self.file_continuous_save=None




        self.ui.statusbar=QtWidgets.QStatusBar(parent)
        self.ui.statusbar.setMaximumHeight(25)
        self.ui.settings_layout.addWidget(self.ui.statusbar)
        self.ui.status_message=QtWidgets.QLabel()
        self.ui.status_message.setMaximumHeight(25)
        self.ui.statusbar.addWidget(self.ui.status_message)
        self.ui.current_Naverage=QSpinBox_ro()
        self.ui.current_Naverage.setToolTip('Current average value')
        self.ui.statusbar.addPermanentWidget(self.ui.current_Naverage)
        self.ui.current_Naverage.setVisible(False)

        ##Connecting buttons:
        self.ui.update_com_pb.clicked.connect(self.update_com) #update communications with hardware
        self.ui.Quit_pb.clicked.connect(self.Quit_fun,type = Qt.QueuedConnection)
        self.ui.settings_pb.clicked.connect(self.show_settings)
        self.ui.IniDet_pb.clicked.connect(self.IniDet_fun)
        self.update_status("Ready",wait_time=self.wait_time)
        self.ui.grab_pb.clicked.connect(lambda: self.Grab(grab_state=True))
        self.ui.single_pb.clicked.connect(lambda: self.Grab(grab_state=False))
        self.ui.save_new_pb.clicked.connect(self.save_new)
        self.ui.save_current_pb.clicked.connect(self.save_current)
        self.ui.load_data_pb.clicked.connect(self.load_data)
        self.grab_done_signal[OrderedDict].connect(self.save_export_data)
        self.ui.Detector_type_combo.currentIndexChanged.connect(self.set_setting_tree)
        self.ui.save_settings_pb.clicked.connect(self.save_settings)
        self.ui.load_settings_pb.clicked.connect(self.load_settings)

        self.ui.take_bkg_cb.clicked.connect(self.take_bkg)

        self.settings.child('save_settings','do_save').sigValueChanged.connect(self.set_continuous_save)

        self.set_setting_tree() #to activate parameters of default Mock detector

        # set preset options
        if preset is not None:
            for preset_dict in preset:
                #fo instance preset_dict=edict(object='Stage_type_combo',method='setCurrentIndex',value=1)
                if hasattr(self.ui,preset_dict['object']):
                    obj=getattr(self.ui,preset_dict['object'])
                    if hasattr(obj,preset_dict['method']):
                        setattr(obj,preset_dict['method'],preset_dict['value'])
        #initialize the controller if init=True
        if init:
            self.ui.IniDet_pb.click()


    def change_viewer(self,DAQ_type='DAQ0D'):
        """
            Change the viewer type from DAQ_Type value between :
                * **DAQ0D** : a 0D instance of viewer
                * **DAQ1D** : a 1D instance of viewer
                * **DAQ2D** : a 2D instance of viewer

            ============== ========== ===========================================
            **Parameters**  **Type**   **Description**
            *DAQ_type*      string     Define the target dimension of the viewer
            ============== ========== ===========================================
        """
        if self.ui.IniDet_pb.isChecked():
            self.ui.IniDet_pb.click()
        QtWidgets.QApplication.processEvents()

        self.DAQ_type=DAQ_type
        for widget in self.ui.viewer_dock.widgets:
            widget.close()
        self.ui.temp_viewer_widget.close()

        viewer_widget=QtWidgets.QWidget()
        self.ui.temp_viewer_widget=QtWidgets.QWidget()

        if DAQ_type=="DAQ0D":
            self.ui.viewer=Viewer0D(viewer_widget)
            self.ui.temporary_viewer=Viewer0D(self.ui.temp_viewer_widget)
            self.detector_types=DAQ_0DViewer_Det_type.names()
        elif DAQ_type=="DAQ1D":
            self.ui.viewer=Viewer1D(viewer_widget)
            self.ui.temporary_viewer=Viewer1D(self.ui.temp_viewer_widget)
            self.detector_types=DAQ_1DViewer_Det_type.names()
            self.settings.child(('save_settings')).hide()
        elif DAQ_type=="DAQ2D":
            self.ui.viewer=Image_View_Multicolor(viewer_widget)
            self.ui.temporary_viewer=Image_View_Multicolor(self.ui.temp_viewer_widget)
            self.detector_types=DAQ_2DViewer_Det_type.names()
            self.ui.viewer.set_scaling_axes(self.get_scaling_options())
            self.ui.viewer.ui.auto_levels_pb.click()
            self.settings.child('main_settings','axes').show()
            self.settings.child(('save_settings')).hide()


        self.ui.temp_viewer_widget.setVisible(False)

        self.ui.viewer_dock.addWidget(viewer_widget)
        self.ui.viewer.data_to_export_signal.connect(self.get_data_from_viewer)

        ##Setting detector types
        self.ui.Detector_type_combo.clear()
        self.ui.Detector_type_combo.addItems(self.detector_types)

    def load_data(self):

        """
            Load a .h5 file content from th select_file obtained pathname.
            In case of :
            * **DAQ0D type** : do nothing.
            * **DAQ1D type** : get x_axis and update the data viewer.
            * **DAQ2D type** : get x_axis, y_axis and update the data viewer.

            Once done show data on screen.

            See Also
            --------
            DAQ_utils.select_file, show_data, update_status
        """
        try:
            self.load_file_pathname=DAQ_utils.select_file(start_path=self.save_file_pathname,save=False, ext=['h5','dat','txt']) #see DAQ_utils
            ext=self.load_file_pathname.suffix[1:]
            if ext=='h5':

                h5file=tables.open_file(str(self.load_file_pathname),mode='r')
                h5root=h5file.root

                children=[child._v_name for child in h5root._f_list_nodes()]
                if self.DAQ_type=='DAQ0D':
                    if 'Data0D' in children:
                        pass

                elif self.DAQ_type=='DAQ1D':
                    if 'Data1D' in children:
                        channels=h5root._f_get_child('Data1D')._f_list_nodes()
                        self.x_axis=channels[0]._f_get_child('x_axis').read()
                        self.ui.viewer.x_axis=self.x_axis
                        datas=[channel._f_get_child('Data').read() for channel in channels]


                elif self.DAQ_type=='DAQ2D':
                    if 'Data2D' in children:
                        channels=h5root._f_get_child('Data2D')._f_list_nodes()
                        self.x_axis=channels[0]._f_get_child('x_axis').read()
                        self.y_axis=channels[0]._f_get_child('y_axis').read()
                        self.ui.viewer.set_scaling_axes(scaling_options=edict(scaled_xaxis=edict(label="",units=None,offset=self.x_axis[0],scaling=self.x_axis[1]-self.x_axis[0]),
                                                                              scaled_yaxis=edict(label="",units=None,offset=self.y_axis[0],scaling=self.y_axis[1]-self.y_axis[0])))
                        datas=[channel._f_get_child('Data').read() for channel in channels]

            else:
                data_tot=np.loadtxt(str(self.load_file_pathname))
                if self.DAQ_type=='DAQ0D':
                    pass

                elif self.DAQ_type=='DAQ1D':
                    self.x_axis=data_tot[:,0]
                    self.ui.viewer.x_axis=self.x_axis
                    datas=[data_tot[:,ind+1] for ind in range(data_tot[:,1:].shape[1])]


                elif self.DAQ_type=='DAQ2D':
                    pass

            self.show_data(datas)
        except Exception as e:
            self.update_status(str(e),self.wait_time,'log')


    def take_bkg(self):
        """
            Save a new file if bkg check button is on.

            See Also
            --------
            save_new
        """
        if self.ui.take_bkg_cb.isChecked():
            self.save_new()


    def save_settings(self,path=None):
        """
            | Save the current viewer settings.
            | In case of Region Of Interest setting, save the current viewer state.
            | Then dump setting if the QDialog has been cancelled.

            ============== ========= ======================================
            **Parameters** **Type**  **Description**
            path           string    the pathname of the file to be saved.
            ============== ========= ======================================

            See Also
            --------
            DAQ_utils.select_file, update_status
        """
        try:
            if path is None or path is False:
                path=DAQ_utils.select_file(save=True,ext='par')

            settings_main=self.settings.saveState()
            if hasattr(self.ui.viewer,'roi_settings'):
                settings_viewer=self.ui.viewer.roi_settings.saveState()
            else:
                settings_viewer=None

            settings=OrderedDict(settings_main=settings_main,settings_viewer=settings_viewer)

            if path is not None: #could be if the Qdialog has been canceled
                with open(str(path), 'wb') as f:
                    pickle.dump(settings, f, pickle.HIGHEST_PROTOCOL)

        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)


    def load_settings(self,path=None):
        """
            | Load settings contained in the pathname file (or select_file destination if path not defined).
            | Open a DAQ_type viewer instance (0D, 1D or 2D), send a data_to_export signal and restore state from the loaeded settings.

            =============== ========== =======================================
            **Parameters**   **Type**   **Description**
            *path*           string     the pathname of the file to be loaded
            =============== ========== =======================================

            See Also
            --------
            IniDet_fun, update_status
        """
        try:
            if self.ui.Ini_state_LED.state: #means  initialzed
                self.ui.IniDet_pb.setChecked(False)
                QtWidgets.QApplication.processEvents()
                self.IniDet_fun()

            if path is None or path is False:
                path=DAQ_utils.select_file(save=False,ext='par')
            with open(str(path), 'rb') as f:
                settings = pickle.load(f)
                settings_main=settings['settings_main']
                DAQ_type=settings_main['children']['main_settings']['children']['DAQ_type']['value']
                if DAQ_type!=self.DAQ_type:
                    if hasattr(self.ui.viewer.ui,'viewer_dock'):self.ui.viewer.ui.viewer_dock.close()
                    if hasattr(self.ui.viewer.ui,'ROIs_dock'):self.ui.viewer.ui.ROIs_dock.close()
                    if hasattr(self.ui.viewer.ui,'zoom_dock'):self.ui.viewer.ui.zoom_dock.close()
                    if hasattr(self.ui.viewer.ui,'Measurement_dock'):self.ui.viewer.ui.Measurement_dock.close()


                    QtWidgets.QApplication.processEvents()
                    if DAQ_type=="DAQ0D":
                        self.ui.viewer=Viewer0D(self.dockarea)
                        self.detector_types=DAQ_0DViewer_Det_type.names()
                    elif DAQ_type=="DAQ1D":
                        self.ui.viewer=Viewer1D(self.dockarea)
                        self.detector_types=DAQ_1DViewer_Det_type.names()
                    elif DAQ_type=="DAQ2D":
                        self.ui.viewer=Image_View_Multicolor(self.dockarea)
                        self.detector_types=DAQ_2DViewer_Det_type.names()

                    self.DAQ_type=DAQ_type
                    self.ui.viewer.data_to_export_signal.connect(self.get_data_from_viewer)
                self.ui.Detector_type_combo.clear()
                self.ui.Detector_type_combo.addItems(self.detector_types)
                self.ui.Detector_type_combo.setCurrentText(settings_main['children']['main_settings']['children']['detector_type']['name'])
                self.settings.restoreState(settings_main)


                settings_viewer=settings['settings_viewer']
                if hasattr(self.ui.viewer,'restore_state'):
                    self.ui.viewer.restore_state(settings_viewer)


        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)


    def update_com(self):
        pass


    def parameter_tree_changed(self,param,changes):
        """
            Foreach value changed, update :
                * Viewer in case of **DAQ_type** parameter name
                * visibility of button in case of **show_averaging** parameter name
                * visibility of naverage in case of **live_averaging** parameter name
                * scale of axis **else** (in 2D PyMoDAQ type)

            Once done emit the update settings signal to link the commit.

            =============== =================================== ================================================================
            **Parameters**    **Type**                           **Description**
            *param*           instance of ppyqtgraph parameter   the parameter to be checked
            *changes*         tuple list                         Contain the (param,changes,info) list listing the changes made
            =============== =================================== ================================================================
            
            See Also
            --------
            change_viewer, DAQ_Utils.custom_parameter_tree.iter_children
        """

        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':
                pass

            elif change == 'value':
                if param.name()=='DAQ_type':
                    self.change_viewer(param.value())
                elif param.name()=='show_averaging':
                    self.ui.temp_viewer_widget.setVisible(param.value())
                elif param.name()=='live_averaging':
                    self.ui.current_Naverage.setVisible(param.value())
                    if param.value()==True:
                        self.ind_continuous_grab=0
                elif param.name() in custom_tree.iter_children(self.settings.child('main_settings','axes'),[]):
                    if self.DAQ_type=="DAQ2D":
                        self.ui.viewer.set_scaling_axes(self.get_scaling_options())


                self.update_settings_signal.emit(edict(path=path,param=param))


            elif change == 'parent':
                pass

    def get_scaling_options(self):
        """
            Return the initialized dictionnary containing the scaling options.


            Returns
            -------
            dictionnary
                scaling options dictionnary.

        """
        scaling_options=edict(scaled_xaxis=edict(label=self.settings.child('main_settings','axes','xaxis','xlabel').value(),
                                    units=self.settings.child('main_settings','axes','xaxis','xunits').value(),
                                    offset=self.settings.child('main_settings','axes','xaxis','xoffset').value(),
                                    scaling=self.settings.child('main_settings','axes','xaxis','xscaling').value()),
                    scaled_yaxis=edict(label=self.settings.child('main_settings','axes','yaxis','ylabel').value(),
                                    units=self.settings.child('main_settings','axes','yaxis','yunits').value(),
                                    offset=self.settings.child('main_settings','axes','yaxis','yoffset').value(),
                                    scaling=self.settings.child('main_settings','axes','yaxis','yscaling').value()))
        return scaling_options

    def set_setting_tree(self):
        """
            Set the local setting tree instance cleaning the current one and populate it with
            standard options corresponding to the PyMoDAQ type viewer (0D, 1D or 2D).

            See Also
            --------
            update_status
        """
        self.detector_name=self.ui.Detector_type_combo.currentText()
        self.settings.child('main_settings','detector_type').setValue(self.detector_name)
        try:
            for child in self.settings.child(('detector_settings')).children():
                child.remove()
            if self.DAQ_type=='DAQ0D':
                obj=getattr(hardware0D,'DAQ_0DViewer_'+self.detector_name)
            elif self.DAQ_type=="DAQ1D":
                obj=getattr(hardware1D,'DAQ_1DViewer_'+self.detector_name)
            elif self.DAQ_type=='DAQ2D':
                obj=getattr(hardware2D,'DAQ_2DViewer_'+self.detector_name)

            params=getattr(obj,'params')
            det_params=Parameter.create(name='Det Settings', type='group', children=params)
            self.settings.child(('detector_settings')).addChildren(det_params.children())
        except Exception as e:
            self.update_status(str(e), wait_time=self.wait_time)


    def set_continuous_save(self):
        """
            Set a continous save file using the base path located file with
            a header-name containing date as a string.

            See Also
            --------
            DAQ_utils.set_current_scan_path
        """
        if self.settings.child('save_settings','do_save').value():
            date=datetime.datetime.now()

            date.strftime('%Y%m%d')
            self.do_continuous_save=True
            # set the filename and path
            base_name=self.settings.child('save_settings','base_name').value()
            scan_path,current_filename,continuous_save_path=DAQ_utils.set_current_scan_path(self.settings.child('save_settings','base_path').value(),
                                                                       base_name=base_name)

            self.continuous_save_path=continuous_save_path

            self.continuous_save_filename=base_name+date.strftime('_%Y%m%d_%H_%M_%S.dat')
            self.settings.child('save_settings','current_file_name').setValue(str(self.continuous_save_path.joinpath(self.continuous_save_filename)))

        else:
            self.do_continuous_save=False
            try:
                self.file_continuous_save.close()
            except Exception as e:
                pass

    @pyqtSlot(edict)#edict(name=self.title,x_axis=None,y_axis=None,z_axis=None,data0D=None,data1D=None,data2D=None)
    def save_export_data(self,datas):
        """
            Store in data_to_save_export buffer the data to be saved and do save at self.snapshot_pathname.

            ============== ============= ======================
            **Parameters**   **Type**     **Description**
            *datas*         dictionnary  the data to be saved
            ============== ============= ======================

            See Also
            --------
            save_datas
        """
        #do save data at self.snapshot_pathname
        self.data_to_save_export=datas #buffer to store current data
        if self.do_save_data:
            self.save_datas(self.save_file_pathname,datas)
            self.do_save_data=False

    def save_datas(self,path=None,datas=None):
        """
            Save procedure of .h5 file data.
            Course the data array and with :
            * **0D data** : store corresponding datas in a h5 file group (a node of the h5 tree)
            * **1D data** : store corresponding datas in a h5 file group (a node of the h5 tree) with a special array for x_axis values
            * **2D data** : store corresponding datas in a h5 file group (a node of the h5 tree) with a special array for x_axis and y_axis values.

            =============== ============= ========================================
            **Parameters**   **Type**     **Description**
            *path*           string        the path name of the file to be saved.
            *datas*          dictionnary   the raw datas to save.
            =============== ============= ========================================

            See Also
            --------
            DAQ_utils.select_file, DAQ_Utils.custom_parameter_tree.parameter_to_xml_string, update_status
        """

        if path is None:
            path=DAQ_utils.select_file(start_path=path,save=True, ext='h5') #see DAQ_utils

        try:
            h5file=tables.open_file(str(path),mode='w')
            h5group=h5file.root
            h5group._v_attrs.type='detector'

            settings_str=custom_tree.parameter_to_xml_string(self.settings)
            if self.DAQ_type!='DAQ0D':
                settings_str=b'<All_settings>'+settings_str
                settings_str+=custom_tree.parameter_to_xml_string(self.ui.viewer.roi_settings)+b'</All_settings>'
            h5group._v_attrs.settings=settings_str

            if datas['data0D'] is not None: #save Data0D if present
                if len(datas['data0D'])!=0: #save Data0D only if not empty (could happen)
                    data0D_group=h5file.create_group(h5group,'Data0D')
                    data0D_group._v_attrs.type='data0D'
                    for ind_channel,key in enumerate(datas['data0D'].keys()):

                        try:
                            array=h5file.create_carray(data0D_group,"CH{:03d}".format(ind_channel),obj=np.array([datas['data0D'][key]]), title=key,filters=self.filters)
                            array.attrs['data_type']='0D'
                            array.attrs['data_name']=key
                            array.attrs['shape']=datas['data0D'][key].shape
                        except Exception as e:
                            self.update_status(str(e),self.wait_time,'log')

            if datas['data1D'] is not None: #save Data1D if present
                if len(datas['data1D'])!=0: #save Data0D only if not empty (could happen)
                    data1D_group=h5file.create_group(h5group,'Data1D')
                    data1D_group._v_attrs.type='data1D'
                    for ind_channel,(key,channel) in enumerate(datas['data1D'].items()):
                        try:
                            channel_group=h5file.create_group(data1D_group,"CH{:03d}".format(ind_channel))
                            channel_group._v_attrs.Channel_name=key
                            if 'x_axis' in channel.keys():
                                x_axis=channel['x_axis']
                                xarray=h5file.create_array(channel_group,"x_axis",obj=x_axis, title=key)
                                xarray.attrs['shape']=xarray.shape
                            array=h5file.create_carray(channel_group,'Data',obj=channel['data'], title='data',filters=self.filters)
                            array.attrs['data_type']='1D'
                            array.attrs['data_name']=key
                            array.attrs['shape']=channel['data'].shape

                        except Exception as e:
                            self.update_status(str(e),self.wait_time,'log')

            #initialize 2D datas

            if datas['data2D'] is not None: #save Data2D if present
                if len(datas['data2D'])!=0: #save Data0D only if not empty (could happen)
                    data2D_group=h5file.create_group(h5group,'Data2D')
                    data2D_group._v_attrs.type='data2D'
                    for ind_channel,(key,channel) in enumerate(datas['data2D'].items()):
                        try:
                            channel_group=h5file.create_group(data2D_group,"CH{:03d}".format(ind_channel))
                            channel_group._v_attrs.Channel_name=key
                            if 'x_axis' in channel.keys():
                                x_axis=channel['x_axis']
                                xarray=h5file.create_array(channel_group,"x_axis",obj=x_axis, title=key)
                                xarray.attrs['shape']=xarray.shape
                            if 'y_axis' in channel.keys():
                                y_axis=channel['y_axis']
                                yarray=h5file.create_array(channel_group,"y_axis",obj=y_axis, title=key)
                                yarray.attrs['shape']=yarray.shape
                            array=h5file.create_carray(channel_group,'Data',obj=channel['data'], title='data',filters=self.filters)
                            array.attrs['data_type']='2D'
                            array.attrs['data_name']=key
                            array.attrs['shape']=channel['data'].shape

                        except Exception as e:
                            self.update_status(str(e),self.wait_time,'log')
            try:
                (root,filename)=os.path.split(str(path))
                filename,ext=os.path.splitext(filename)
                image_path=os.path.join(root,filename+'.png')
                self.dockarea.parent().grab().save(image_path);
            except Exception as e:
                self.update_status(str(e),self.wait_time,'log')

            h5file.close()

        except Exception as e:
            self.update_status(str(e),self.wait_time,'log')

    def update_status(self,txt,wait_time=0,log_type=None):
        """
            | Show the given txt message in the status bar with a delay of wait_time ms.
            | Emit a log signal if log_type parameter is defined.

            =============== =========== =====================================
            **Parameters**    **Type**   **Description**
            *txt*             string     the message to show
            *wait_time*       int        the delay of showwing
            *log_type*        string     the type of  the log signal to emit
            =============== =========== =====================================
        """
        self.ui.statusbar.showMessage(txt,wait_time)
        if log_type is not None:
            self.log_signal.emit(self.title+': '+txt)

    def save_new(self):
        """
            Do a new save from the select_file obtained pathname into a h5 file structure.

            See Also
            --------
            DAQ_utils.select_file, SnapShot
        """
        self.do_save_data=True
        self.save_file_pathname=DAQ_utils.select_file(start_path=self.save_file_pathname,save=True, ext='h5') #see DAQ_utils
        self.SnapShot(pathname=self.save_file_pathname)

    def save_current(self):
        """
            Save the current opened file from the select_file obtained pathname into a h5 file structure.

            See Also
            --------
            DAQ_utils.select_file, save_export_data
        """
        self.do_save_data=True
        self.save_file_pathname=DAQ_utils.select_file(start_path=self.save_file_pathname,save=True, ext='h5') #see DAQ_utils
        self.save_export_data(self.data_to_save_export)

    def SnapShot(self,pathname=None):
        """
            Do one single grab and save the data in pathname.

            =============== =========== =================================================
            **Parameters**    **Type**    **Description**
            *pathname*        string      the pathname to the location os the saved file
            =============== =========== =================================================

            See Also
            --------
            Grab, update_status
        """
        try:
            self.do_save_data=True
            if pathname is None:
                raise (Exception("filepathanme has not been defined in snapshot"))
            self.save_file_pathname=pathname

            self.Grab(False)
        except Exception as e:
            self.update_status(str(e),self.wait_time,'log')


    def Grab(self,grab_state=False):
        """
            Do a grab session using 2 profile :
                * if grab pb checked do  a continous save and send an "update_channels" thread command and a "Grab" too.
                * if not send a "Stop_grab" thread command with settings "main settings-naverage" node value as an attribute.

            See Also
            --------
            DAQ_utils.ThreadCommand, set_enabled_Ini_buttons
        """

        if not(grab_state):

            self.command_detector.emit(ThreadCommand("Single",[self.settings.child('main_settings','Naverage').value()]))
        else:
            if not(self.ui.grab_pb.isChecked()):
                if self.do_continuous_save:
                    self.file_continuous_save.close()
                self.command_detector.emit(ThreadCommand("Stop_grab"))
                self.set_enabled_Ini_buttons(enable=True)
            else:

                self.ind_continuous_grab=0
                if self.do_continuous_save:
                    self.file_continuous_save=open(str(self.continuous_save_path.joinpath(self.continuous_save_filename)),'a')
                self.thread_status(ThreadCommand("update_channels"))
                self.set_enabled_Ini_buttons(enable=False)
                self.command_detector.emit(ThreadCommand("Grab",[self.settings.child('main_settings','Naverage').value()]))




    def IniDet_fun(self):
        """
            | If Init detector button checked, init the detector and connect the data detector, the data detector temp, the status and the update_settings signals to their corresponding function.
            | Once done start the detector linked thread.
            |
            | Else send the "close" thread command.

            See Also
            --------
            set_enabled_grab_buttons, DAQ_utils.ThreadCommand, DAQ_Detector
        """
        try:
            QtWidgets.QApplication.processEvents()
            if not self.ui.IniDet_pb.isChecked():
                self.set_enabled_grab_buttons(enable=False)
                self.ui.Ini_state_LED.set_as_false()
                self.Initialized_state=False

                if hasattr(self,'detector_thread'):
                    self.command_detector.emit(ThreadCommand("Close"))
                self.Initialized_state=False


            else:
                self.detector_name=self.ui.Detector_type_combo.currentText()

                detector=DAQ_Detector(self.settings,self.detector_name)
                self.detector_thread=QThread()
                detector.moveToThread(self.detector_thread)

                self.command_detector[ThreadCommand].connect(detector.queue_command)
                detector.data_detector_sig[list].connect(self.show_data)
                detector.data_detector_temp_sig[list].connect(self.show_temp_data)
                detector.status_sig[ThreadCommand].connect(self.thread_status)
                self.update_settings_signal[edict].connect(detector.update_settings)

                self.detector_thread.detector=detector
                self.detector_thread.start()

                self.command_detector.emit(ThreadCommand("Ini_Detector",attributes=[self.settings.child(('detector_settings')).saveState()]))


        except Exception as e:
            self.update_status(str(e))
            self.set_enabled_grab_buttons(enable=False)

    def Quit_fun(self):
        """
            | Close the current instance of DAQ_Viewer_main emmiting the quit signal.
            | Treat an exception if an error during the detector unitializing has occured.

        """
        # insert anything that needs to be closed before leaving
        try:
            if self.Initialized_state==True: #means  initialzed
                self.ui.IniDet_pb.click()
                QtWidgets.QApplication.processEvents()
            self.quit_signal.emit()



            if __name__ == '__main__':
                try:
                    self.dockarea.parent().close()
                except: pass
        except Exception as e:
            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap(":/Labview_icons/Icon_Library/close2.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            msgBox=QtWidgets.QMessageBox(parent=None)
            msgBox.addButton(QtWidgets.QMessageBox.Yes)
            msgBox.addButton(QtWidgets.QMessageBox.No)
            msgBox.setWindowTitle("Error")
            msgBox.setText(str(e)+" error happened when uninitializing the Detector.\nDo you still want to quit?")
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Yes)
            ret=msgBox.exec();
            if ret==QtWidgets.QMessageBox.Yes:
                self.dockarea.parent().close()

    def show_settings(self):
        """
            Set the settings tree visible if the corresponding button is checked.
        """

        if self.ui.settings_pb.isChecked():
            self.ui.settings_tree.setVisible(True)
        else:
            self.ui.settings_tree.setVisible(False)

    def set_enabled_Ini_buttons(self,enable=False):
        """
            Set enable :
                * **Detector** button
                * **Init Detector** button
                * **Quit** button
                
            with the given enable boolean value.

            =============== =========== ===================
            **Parameters**    **Type**    **Description**
            *enable*          boolean     the value to map
            =============== =========== ===================
        """
        self.ui.Detector_type_combo.setEnabled(enable)
        self.ui.IniDet_pb.setEnabled(enable)
        self.ui.Quit_pb.setEnabled(enable)

    def set_enable_recursive(self,children,enable=False):
        """
            | Set enable childs of chidren root argument with enable parameter value (False as default) calling recursively the method on children.
            |
            | Recursivity decreasing on children argument.

            =============== ===================== ==================================================
            **Parameters**    **Type**             **Description**
            *children*        settings tree node   The starting node of the (sub)tree to be treated
            *enable*          boolean              the default value to map
            =============== ===================== ==================================================

            See Also
            --------
            set_enable_recursive
        """
        for child in children:
            if children==[]:
                return
            elif type(child) is QtWidgets.QSpinBox or type(child) is QtWidgets.QComboBox or type(child) is QtWidgets.QPushButton or type(child) is QtWidgets.QListWidget:
                child.setEnabled(enable)
            else:
                self.set_enable_recursive(child.children(),enable)

    def set_enabled_grab_buttons(self,enable=False):
        """
            Set enable with parameter value :
                * **grab** button
                * **single** button
                * **save current** button
                * **save new** button

            =============== =========== ===========================
            **Parameters**    **Type**    **Description**
            enable            boolean     the default value to map
            =============== =========== ===========================
        """
        self.ui.grab_pb.setEnabled(enable)
        self.ui.single_pb.setEnabled(enable)
        self.ui.save_current_pb.setEnabled(enable)
        self.ui.save_new_pb.setEnabled(enable)
        #self.ui.settings_pb.setEnabled(enable)


    @pyqtSlot(list)
    def show_temp_data(self,datas):
        """
            | Show the given datas in a temporary viewer in case of 0D/D datas.
            | In case of 2D datas, send a list of images (at most 3) to the 2D viewer.

            =============== ===================== ========================
            **Parameters**    **Type**             **Description**
            datas             ordered dictionnary  the datas to be showed.
            =============== ===================== ========================

        """
        if self.DAQ_type=="DAQ0D" or self.DAQ_type=="DAQ1D":
            self.ui.temporary_viewer.show_data(datas)

        if self.DAQ_type=="DAQ2D":
            """send a list of images (at most 3) to the 2D viewer
            """
            self.ui.temporary_viewer.setImage(*datas)


    @pyqtSlot(list)
    def show_data(self,datas):
        """
            | Check the snapshot leaf in the tree, if not none and data over the overshoot threshold, send an overshot signal.
            |
            | Process background buffer if needed.
            | Process live averaging if needed.
            | Show datas in case of 0D or 1D DAQ_type.
            | Send a list of images (at most 3) to the 2D viewer else.

            =============== ===================== ===================
            **Parameters**    **Type**             **Description**
            *datas*           ordered dictionnary  the datas to show
            =============== ===================== ===================

            See Also
            --------
            update_status
        """
        if  self.ui.take_bkg_cb.isChecked():
            self.ui.take_bkg_cb.setChecked(False)
            self.bkg=datas


        if self.settings.child('main_settings','overshoot','stop_overshoot').value():
            for data in datas:
                if self.DAQ_type=="DAQ0D":
                    if data>=self.settings.child('main_settings','overshoot','overshoot_value').value():
                        self.overshoot_signal.emit(True)
                else:
                    if any(data>=self.settings.child('main_settings','overshoot','overshoot_value').value()):
                        self.overshoot_signal.emit(True)

        #process bkg if needed
        if self.ui.do_bkg_cb.isChecked() and self.bkg is not None:
            try:
                for ind_data,dat in enumerate(datas):
                    datas[ind_data]=datas[ind_data]-self.bkg[ind_data]
            except Exception as e:
                self.update_status(str(e),self.wait_time,'log')


        if self.settings.child('main_settings','live_averaging').value():
            self.ui.current_Naverage.setValue(self.ind_continuous_grab)
            self.ind_continuous_grab+=1
            if self.ind_continuous_grab>1:
                try:
                    datas=[((self.ind_continuous_grab-1)*self.current_datas[ind]+datas[ind])/self.ind_continuous_grab for ind in range(len(datas))]
                except Exception as e:
                    self.update_status(str(e),self.wait_time,log_type='log')

        if self.DAQ_type=="DAQ0D" or self.DAQ_type=="DAQ1D":
            self.ui.viewer.show_data(datas)

        if self.DAQ_type=="DAQ2D":
            """send a list of images (at most 3) to the 2D viewer
            """
            self.ui.viewer.setImage(*datas)

        self.current_datas=datas


        if self.DAQ_type=="DAQ0D" and self.do_continuous_save:
            date=datetime.datetime.now()
            string=date.strftime('%H_%M_%S_%f')
            for data in datas:
                string+='\t{:.6e}'.format(data)
            string+='\n'
            try:
                self.file_continuous_save.write(string)
            except ValueError as e:
                self.file_continuous_save=open(str(self.continuous_save_path.joinpath(self.continuous_save_filename)),'a')
                self.file_continuous_save.write(string)
                self.file_continuous_save.close()



    @pyqtSlot(edict)
    def get_data_from_viewer(self,datas):
        """
            Emit the grab done signal with datas as an attribute.

            =============== ===================== ===================
            **Parameters**    **Type**             **Description**
            *datas*           ordered dictionnary  the datas to show
            =============== ===================== ===================
        """
        # datas=OrderedDict(name=self.title,x_axis=None,y_axis=None,z_axis=None,data0D=None,data1D=None,data2D=None)
        datas['name']=self.title
        self.grab_done_signal.emit(datas)

    @pyqtSlot(ThreadCommand)
    def thread_status(self,status): # general function to get datas/infos from all threads back to the main
        """
            General function to get datas/infos from all threads back to the main.

            In case of :
                * **Update_Status**   *command* : update the status from the given status attributes
                * **Ini_Detector**    *command* : update the status with "detector initialized" value and init state if attributes not null.
                * **Close**           *command* : Close the current thread and delete corresponding attributes on cascade.
                * **Grab**            *command* : Do nothing
                * **x_axis**          *command* : update x_axis from status attributes and User Interface viewer consequently.
                * **y_axis**          *command* : update y_axis from status attributes and User Interface viewer consequently.
                * **Update_channel**  *command* : update the viewer channels in case of 0D DAQ_type
                * **Update_settings** *command* : Update the "detector setting" node in the settings tree.

            =============== ================ =======================================================
            **Parameters**   **Type**            **Description**

            *status*        ThreadCommand()     instance of ThreadCommand containing two attributes:
                                                    * command   : string
                                                    * attributes: list
            =============== ================ =======================================================

            See Also
            --------
            update_status, set_enabled_grab_buttons, raise_timeout 
        """
        if status.command=="Update_Status":
            if len(status.attributes)>2:
                self.update_status(status.attributes[0],wait_time=self.wait_time,log_type=status.attributes[1])
            else:
                self.update_status(status.attributes[0],wait_time=self.wait_time)

        elif status.command=="Ini_Detector":
            self.update_status("detector initialized: "+str(status.attributes[0]['initialized']),wait_time=self.wait_time)

            if status.attributes[0]['initialized']:
                self.set_enabled_grab_buttons(enable=True)
                self.ui.Ini_state_LED.set_as_true()
                self.Initialized_state=True
            else:
                self.Initialized_state=False

        elif status.command=="Close":
            try:
                self.update_status(status.attributes[0],wait_time=self.wait_time)
                self.detector_thread.exit()
                self.detector_thread.wait()
                finished=self.detector_thread.isFinished()
                if finished:
                    delattr(self,'detector_thread')
                else:
                    self.update_status('thread is locked?!',self.wait_time,'log')
            except Exception as e:
                self.update_status(str(e),self.wait_time,'log')

            self.Initialized_state=False

        elif status.command=="Grab":
            pass

        elif status.command=="x_axis":
            self.x_axis=status.attributes[0]
            self.ui.viewer.x_axis=self.x_axis


        elif status.command=="y_axis":
            self.y_axis=status.attributes[0]
            self.ui.viewer.y_axis=self.y_axis


        elif status.command=="update_channels":
            if self.DAQ_type=='DAQ0D':
                self.ui.viewer.update_channels()


        elif status.command=='update_settings':
            try:
                self.settings.sigTreeStateChanged.disconnect(self.parameter_tree_changed)#any changes on the settings will update accordingly the detector
            except: pass
            try:
                if status.attributes[2] == 'value':
                    self.settings.child('detector_settings',*status.attributes[0]).setValue(status.attributes[1])
                elif status.attributes[2] == 'limits':
                    self.settings.child('detector_settings',*status.attributes[0]).setLimits(status.attributes[1])
            except: pass
            self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)#any changes on the settings will update accordingly the detector

        elif status.command=='raise_timeout':
            self.raise_timeout()

    @pyqtSlot()
    def raise_timeout(self):
        """
            Print the "timeout occured" error message in the status bar via the update_status method.

            See Also
            --------
            update_status
        """
        self.update_status("Timeout occured",wait_time=self.wait_time,log_type="log")


class DAQ_Detector(QObject):
    """
        ========================= ==========================
        **Attributes**              **Type**
        *status_sig*                instance of pyqt Signal
        *data_detector_sig*         instance of pyqt Signal
        *data_detector_temp_sig*    instance of pyqt Signal

        *waiting_for_data*          boolean
        *controller*                ???
        *detector_name*             string
        *detector*                  ???
        *controller_adress*         ???
        *grab_state*                boolean
        *single_grab*               boolean
        *x_axis*                    1D numpy array
        *y_axis*                    1D numpy array
        *datas*                     dictionnary
        *ind_average*               int
        *Naverage*                  int
        *average_done*              boolean
        *hardware_averaging*        boolean
        *show_averaging*            boolean
        *wait_time*                 int
        *DAQ_type*                  string
        ========================= ==========================
    """
    status_sig = pyqtSignal(ThreadCommand)
    data_detector_sig=pyqtSignal(list)
    data_detector_temp_sig=pyqtSignal(list)

    def __init__(self,settings_parameter,detector_name):
        super(DAQ_Detector,self).__init__()
        self.waiting_for_data=False
        self.controller=None
        self.detector_name=detector_name
        self.detector=None
        self.controller_adress=None
        self.grab_state=False
        self.single_grab=False
        self.x_axis=None
        self.y_axis=None
        self.datas=None
        self.ind_average=0
        self.Naverage=None
        self.average_done=False
        self.hardware_averaging=False
        self.show_averaging=False
        self.wait_time=settings_parameter.child('main_settings','wait_time').value()
        self.DAQ_type=settings_parameter.child('main_settings','DAQ_type').value()

    @pyqtSlot(edict)
    def update_settings(self,settings_parameter_dict):
        """
            | Set attributes values in case of "main_settings" path with corresponding parameter values.
            | Recursively call the method on detector class attributes else.

            ======================== ============== ======================================
            **Parameters**             **Type**      **Description**
            settings_parameter_dict    dictionnary   the (pathname,parameter) dictionnary
            ======================== ============== ======================================

            See Also
            --------
            update_settings
        """
        # =edict(path=path,param=param)
        path=settings_parameter_dict['path']
        param=settings_parameter_dict['param']
        if path[0]=='main_settings':
            if hasattr(self,path[-1]):
                setattr(self,path[-1],param.value())

        elif path[0]=='detector_settings':
            self.detector.update_settings(settings_parameter_dict)


    @pyqtSlot(ThreadCommand)
    def queue_command(self,command=ThreadCommand()):
        """
            Treat the given command parameter from his name :
              * **Ini_Detector** : Send the corresponding Thread command via a status signal.
              * **Close**        : Send the corresponding Thread command via a status signal.
              * **Grab**         : Call the local Grab method with command(s) attributes.
              * **Single**       : Call the local Single method with command(s) attributes.
              * **Stop_Grab**    : Send the correpsonding Thread command via a status signal.

            =============== ================= ============================
            **Parameters**    *Type*           **Description**
            *command*         ThreadCommand()  The command to be treated
            =============== ================= ============================

            See Also
            --------
            Grab, Single, DAQ_utils.ThreadCommand
        """
        if command.command=="Ini_Detector":
            status=self.Ini_Detector(*command.attributes)
            self.status_sig.emit(ThreadCommand(command.command,[ status,'log']))

        elif command.command=="Close":
            status=self.Close()
            self.status_sig.emit(ThreadCommand(command.command,[ status,'log']))

        elif command.command=="Grab":
            self.single_grab=False
            self.grab_state=True
            self.Grab(*command.attributes)

        elif command.command=="Single":
            self.single_grab=True
            self.grab_state=True
            self.Single(*command.attributes)

        elif command.command=="Stop_grab":
            self.grab_state=False
            self.status_sig.emit(ThreadCommand("Update_Status",['Stoping grab']))


    def Ini_Detector(self,params_state=None):
        """
            Init the detector from params_state parameter and DAQ_type class attribute :
                * in **0D** profile : update the local status and send the "x_axis" Thread command via a status signal
                * in **1D** profile : update the local status and send the "x_axis" Thread command via a status signal
                * in **2D** profile : update the local status and send the "x_axis" and the "y_axis" Thread command via a status signal

            =============== =========== ==========================================
            **Parameters**    **Type**    **Description**
            *params_state*     ???         the parameter's state of initialization
            =============== =========== ==========================================

            See Also
            --------
            Ini_Detector, DAQ_utils.ThreadCommand
        """
        try:
            #status="Not initialized"
            status=edict(initialized=False,info="",x_axis=None,y_axis=None)
            if self.DAQ_type=='DAQ0D':
                class_=getattr(hardware0D,'DAQ_0DViewer_'+self.detector_name)
                self.detector=class_(self,params_state)

                status.update(self.detector.Ini_Detector())
                if status['x_axis'] is not None:
                    self.x_axis=status['x_axis']
                    self.status_sig.emit(ThreadCommand("x_axis",[self.x_axis]))
                #status="Initialized"

            elif self.DAQ_type=='DAQ1D':
                class_=getattr(hardware1D,'DAQ_1DViewer_'+self.detector_name)
                self.detector=class_(self,params_state)

                status.update(self.detector.Ini_Detector())
                if status['x_axis'] is not None:
                    self.x_axis=status['x_axis']
                    self.status_sig.emit(ThreadCommand("x_axis",[self.x_axis]))
                #status="Initialized"

            elif self.DAQ_type=='DAQ2D':
                class_=getattr(hardware2D,'DAQ_2DViewer_'+self.detector_name)
                self.detector=class_(self,params_state)

                status.update(self.detector.Ini_Detector())
                if status['x_axis'] is not None:
                    self.x_axis=status['x_axis']
                    self.status_sig.emit(ThreadCommand("x_axis",[self.x_axis]))
                if status['y_axis'] is not None:
                    self.y_axis=status['y_axis']
                    self.status_sig.emit(ThreadCommand("y_axis",[self.y_axis]))
                #status="Initialized"


            else:
                raise Exception(self.detector_name + " unknown")
            self.detector.data_grabed_signal.connect(self.data_ready)
            self.hardware_averaging=class_.hardware_averaging #to check if averaging can be done directly by the hardware or done here software wise

            return status
        except Exception as e:
            self.status_sig.emit(ThreadCommand("Update_Status",[str(e),'log']))
            return status



    @pyqtSlot(list)
    def data_ready(self,datas):
        """
            | Update the local datas attributes from the given datas parameter if the averaging has to be done software wise.
            |
            | Else emit the data detector signals with datas parameter as an attribute.

            =============== ===================== =========================
            **Parameters**    **Type**             **Description**
            *datas*           ordered dictionnary  the datas to be emitted.
            =============== ===================== =========================

            See Also
            --------
            DAQ_utils.ThreadCommand
        """
        if not(self.hardware_averaging): #to execute if the averaging has to be done software wise
            self.ind_average+=1
            if self.ind_average==1:
                self.datas=datas
            else:
                try:
                    self.datas=[((self.ind_average-1)*self.datas[ind]+datas[ind])/self.ind_average for ind in range(len(datas))]
                    if self.show_averaging:
                        self.data_detector_temp_sig.emit(self.datas)
                except Exception as e:
                    self.status_sig.emit(ThreadCommand("Update_Status",[str(e),'log']))

            if self.ind_average==self.Naverage:
                self.average_done=True
                self.data_detector_sig.emit(self.datas)
                self.ind_average=0



        else:
            self.data_detector_sig.emit(datas)
        self.waiting_for_data=False
        if self.grab_state==False:
            #self.status_sig.emit(["Update_Status","Grabing braked"])
            self.detector.Stop()

    def Single(self,Naverage=1):
        """
            Call the Grab method with Naverage parameter as an attribute.

            =============== =========== ==================
            **Parameters**    **Type**    **Description**
            *Naverage*        int
            =============== =========== ==================

            See Also
            --------
            DAQ_utils.ThreadCommand, Grab
        """
        try:
            self.Grab(Naverage)
            #self.ind_average=0
            #self.Naverage=Naverage
            #self.status_sig.emit(["Update_Status","Start grabing"])
            #self.detector.Grab(Naverage)


        except Exception as e:
            status=str(e)
            self.status_sig.emit(ThreadCommand("Update_Status",[str(e),'log']))

    def Grab(self,Naverage=1):
        """
            | Update status with 'Start Grabing' Update_status sub command of the Thread command.
            | Process events and grab naverage is needed.

            =============== =========== ==================
            **Parameters**    **Type**    **Description**
            *Naverage*        int
            =============== =========== ==================

            See Also
            --------
            DAQ_utils.ThreadCommand, Grab
        """
        try:
            self.ind_average=0
            self.Naverage=Naverage
            if Naverage>1:
                self.average_done=False
            self.status_sig.emit(ThreadCommand("Update_Status",['Start Grabing']))
            self.waiting_for_data=False
            while 1:
                try:
                    if not(self.waiting_for_data):
                        self.waiting_for_data=True
                        QThread.msleep(self.wait_time)
                        self.detector.Grab(Naverage)
                    QtWidgets.QApplication.processEvents()
                    if self.single_grab:
                        if self.hardware_averaging:
                            break
                        else:
                            if self.average_done:
                                break


                    if self.grab_state==False:

                        #self.detector.Stop()
                        break
                except Exception as e:
                    print(str(e))

        except Exception as e:
            self.status_sig.emit(ThreadCommand("Update_Status",[str(e),'log']))


    def Close(self):
        """
            Close the current instance of DAQ_Detector.
        """
        try:
            status=self.detector.Close()
        except Exception as e:
            status=str(e)
        return status






if __name__ == '__main__':
    from PyMoDAQ.DAQ_Utils.DAQ_enums import DAQ_type
    app = QtWidgets.QApplication(sys.argv);
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000,500)
    win.setWindowTitle('PyMoDAQ main')
    prog = DAQ_Viewer(area,title="Testing",DAQ_type=DAQ_type['DAQ1D'].name)
    win.show()
    sys.exit(app.exec_())


# -*- coding: utf-8 -*-
"""
Created on Wed Jan 10 16:54:14 2018

@author: Weber Sébastien
"""

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QRectF

import sys
from pymodaq.daq_viewer.daq_gui_settings import Ui_Form

from pymodaq.daq_utils.plotting.viewer0D.viewer0D_main import Viewer0D
from pymodaq.daq_utils.plotting.viewer1D.viewer1D_main import Viewer1D
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D
from pymodaq.daq_utils.plotting.viewerND.viewerND_main import ViewerND
import pymodaq.daq_utils.daq_utils as daq_utils
from pymodaq.daq_utils.daq_utils import ThreadCommand, make_enum

from pymodaq_plugins.daq_viewer_plugins import plugins_0D
from pymodaq_plugins.daq_viewer_plugins import plugins_1D
from pymodaq_plugins.daq_viewer_plugins import plugins_2D

DAQ_0DViewer_Det_type=make_enum('daq_0Dviewer')
DAQ_1DViewer_Det_type=make_enum('daq_1Dviewer')
DAQ_2DViewer_Det_type=make_enum('daq_2Dviewer')


from collections import OrderedDict
import numpy as np

from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree
import os
from easydict import EasyDict as edict


from pyqtgraph.dockarea import DockArea, Dock
import pickle
import datetime
import tables



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
            {'title': 'DAQ type:','name': 'DAQ_type', 'type': 'list', 'values': ['DAQ0D','DAQ1D','DAQ2D'], 'readonly': True},
            {'title': 'Detector type:','name': 'detector_type', 'type': 'str', 'value': '', 'readonly': True},
            {'title': 'Nviewers:','name': 'Nviewers', 'type': 'int', 'value': 1, 'min': 1, 'default': 1, 'readonly': True},
            {'title': 'Controller ID:', 'name': 'controller_ID', 'type': 'int', 'value': 0, 'default': 0},

            {'title': 'Naverage', 'name': 'Naverage', 'type': 'int', 'default': 1, 'value': 1, 'min': 1},
            {'title': 'Show averaging:', 'name': 'show_averaging', 'type': 'bool', 'default': False, 'value': False},
            {'title': 'Live averaging:', 'name': 'live_averaging', 'type': 'bool', 'default': False, 'value': False},
            {'title': 'N Live aver.:', 'name': 'N_live_averaging', 'type': 'int', 'default': 0, 'value': 0, 'visible': False},
            {'title': 'Wait time (ms):', 'name': 'wait_time', 'type': 'int', 'default': 100, 'value': 100, 'min': 0},
            {'title': 'Continuous saving:', 'name': 'continuous_saving_opt', 'type': 'bool', 'default': False, 'value': False},
            {'title': 'Overshoot options:','name':'overshoot','type':'group', 'visible': True, 'expanded': False,'children':[
                    {'title': 'Overshoot:', 'name': 'stop_overshoot', 'type': 'bool', 'value': False},
                    {'title': 'Overshoot value:', 'name': 'overshoot_value', 'type': 'float', 'value': 0}]},
            {'title': 'Axis options:','name':'axes','type':'group', 'visible': False, 'expanded': False, 'children':[
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
            ]},

        ]},
        {'title': 'Continuous Saving','name': 'continuous_saving','type': 'group', 'expanded': False, 'visible': False, 'children':[
            {'title': 'Base Path:', 'name': 'base_path', 'type': 'browsepath', 'default': 'D:/Data', 'value': 'D:/Data', 'filetype': False},
            {'title': 'Base Name:', 'name': 'base_name', 'type': 'str', 'default': 'Data', 'value': 'Data'},
            {'title': 'Current Path:', 'name': 'current_file_name', 'type': 'text', 'default': 'D:/Data', 'value': 'D:/Data', 'readonly': True},
            {'title': 'Do Save:', 'name': 'do_save', 'type': 'bool', 'default': False, 'value': False},
            {'title': 'Compression options:', 'name': 'compression_options', 'type': 'group', 'children': [
                {'title': 'Compression library:','name': 'h5comp_library', 'type': 'list', 'value': 'zlib', 'values': ['zlib', 'lzo', 'bzip2', 'blosc']},
                {'title': 'Compression level:','name': 'h5comp_level', 'type': 'int', 'value': 5, 'min': 0 , 'max': 9},
                ]},
            ]},
        {'title': 'Detector Settings','name': 'detector_settings', 'type': 'group', 'children':[
            {'title': 'ROI select:','name':'ROIselect','type':'group', 'visible': False,'children':[
                {'title': 'Use ROI:', 'name': 'use_ROI', 'type': 'bool', 'value': False},
                {'title': 'x0:', 'name': 'x0', 'type': 'int', 'value': 0, 'min': 0},
                {'title': 'y0:', 'name': 'y0', 'type': 'int', 'value': 0, 'min': 0},
                {'title': 'width:', 'name': 'width', 'type': 'int', 'value': 10, 'min': 1},
                {'title': 'height:', 'name': 'height', 'type': 'int', 'value': 10, 'min': 1},
                ]}
            ]}
        ]

    def __init__(self,parent,dock_settings=None,dock_viewer=None,title="Testing",DAQ_type="DAQ0D",preset=None,init=False,controller_ID=-1):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(DAQ_Viewer,self).__init__()

        splash=QtGui.QPixmap('..//Documentation//splash.png')
        self.splash_sc = QtWidgets.QSplashScreen(splash,Qt.WindowStaysOnTopHint)

        self.ui=Ui_Form()
        widgetsettings=QtWidgets.QWidget()
        self.ui.setupUi(widgetsettings)
        self.ini_date=datetime.datetime.now()
        self.wait_time=1000
        self.title=title
        self.ui.title_label.setText(self.title)
        self.DAQ_type=DAQ_type
        self.dockarea=parent
        self.bkg=None #buffer to store background
        self.filters = tables.Filters(complevel=5)        #options to save data to h5 file using compression zlib library and level 5 compression

        self.ui.statusbar=QtWidgets.QStatusBar(parent)
        self.ui.statusbar.setMaximumHeight(25)
        self.ui.settings_layout.addWidget(self.ui.statusbar)
        self.ui.status_message=QtWidgets.QLabel()
        self.ui.status_message.setMaximumHeight(25)
        self.ui.statusbar.addWidget(self.ui.status_message)


        ############IMPORTANT############################
        self.controller=None #the hardware controller/set after initialization and to be used by other modules if needed
        #################################################

        #create main parameter tree
        self.ui.settings_tree = ParameterTree()
        self.ui.settings_layout.addWidget(self.ui.settings_tree,10)
        self.ui.settings_tree.setMinimumWidth(300)
        self.settings=Parameter.create(name='Settings', type='group', children=self.params)
        self.settings.child('main_settings','DAQ_type').setValue(self.DAQ_type)
        self.ui.settings_tree.setParameters(self.settings, showTop=False)
        #connecting from tree
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)#any changes on the settings will update accordingly the detector
        self.settings.child('main_settings','controller_ID').setValue(controller_ID)

        if dock_settings is not None:
            self.ui.settings_dock =dock_settings
            self.ui.settings_dock.setTitle(title+"_Settings")
        else:
            self.ui.settings_dock = Dock(title+"_Settings", size=(10, 10))
            self.dockarea.addDock(self.ui.settings_dock)

        self.ui.viewer_docks=[]
        if dock_viewer is not None:
            self.ui.viewer_docks.append(dock_viewer)
            self.ui.viewer_docks[-1].setTitle(title+"_Viewer 1")
        else:
            self.ui.viewer_docks.append(Dock(title+"_Viewer", size=(500,300), closable=False))
            self.dockarea.addDock(self.ui.viewer_docks[-1],'right',self.ui.settings_dock)





        #install specific viewers
        self.viewer_widgets=[]
        self.change_viewer()

        self.ui.settings_dock.addWidget(widgetsettings)


        ##Setting detector types
        self.ui.Detector_type_combo.clear()
        self.ui.Detector_type_combo.addItems(self.detector_types)

        self.measurement_module=None
        self.detector=None
        self.set_enabled_grab_buttons(enable=False)
        self.set_enabled_Ini_buttons(enable=True)


        self.save_file_pathname=None # to store last active path, will be an Path object
        self.ind_continuous_grab=0

        self.ui.Ini_state_LED.clickable=False
        self.ui.Ini_state_LED.set_as_false()
        self.Initialized_state=False
        self.measurement_module=None
        self.snapshot_pathname=None



        self.current_datas=None
        #edict to be send to the daq_measurement module from 1D traces if any

        self.data_to_save_export=OrderedDict([])
        self.do_save_data=False
        self.do_continuous_save=False
        self.file_continuous_save=None





        ##Connecting buttons:
        self.ui.update_com_pb.clicked.connect(self.update_com) #update communications with hardware
        self.ui.Quit_pb.clicked.connect(self.quit_fun, type = Qt.QueuedConnection)
        self.ui.settings_pb.clicked.connect(self.show_settings)
        self.ui.IniDet_pb.clicked.connect(self.ini_det_fun)
        self.update_status("Ready",wait_time=self.wait_time)
        self.ui.grab_pb.clicked.connect(lambda: self.grab_data(grab_state=True))
        self.ui.single_pb.clicked.connect(lambda: self.grab_data(grab_state=False))
        self.ui.stop_pb.clicked.connect(self.stop_all)
        self.ui.save_new_pb.clicked.connect(self.save_new)
        self.ui.save_current_pb.clicked.connect(self.save_current)
        self.ui.load_data_pb.clicked.connect(self.load_data)
        self.grab_done_signal[OrderedDict].connect(self.save_export_data)
        self.ui.Detector_type_combo.currentIndexChanged.connect(self.set_setting_tree)
        self.ui.save_settings_pb.clicked.connect(self.save_settings)
        self.ui.load_settings_pb.clicked.connect(self.load_settings)
        self.ui.DAQ_type_combo.currentTextChanged[str].connect(self.set_DAQ_type)
        self.ui.take_bkg_cb.clicked.connect(self.take_bkg)
        self.ui.DAQ_type_combo.setCurrentText(DAQ_type)


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

    def change_viewer(self):
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
        DAQ_type=self.settings.child('main_settings','DAQ_type').value()
        Nviewers=self.settings.child('main_settings','Nviewers').value()

        if self.ui.IniDet_pb.isChecked():
            self.ui.IniDet_pb.click()
        QtWidgets.QApplication.processEvents()

        self.DAQ_type=DAQ_type
        if hasattr(self.ui,'viewers'): #this basically means we are at the initialization satge of the class
            if self.ui.viewers!=[]:
                for ind in range(Nviewers):
                    viewer=self.ui.viewers.pop()
                    widget=self.viewer_widgets.pop()
                    widget.close()
                    if len(self.ui.viewer_docks)>1:
                        dock=self.ui.viewer_docks.pop()
                        dock.close()



        self.ui.viewers=[]
        self.viewer_widgets=[]
        self.viewer_types=[]
        if DAQ_type=="DAQ0D":
            for ind in range(Nviewers):
                self.viewer_widgets.append(QtWidgets.QWidget())
                self.ui.viewers.append(Viewer0D(self.viewer_widgets[-1]))
            self.detector_types=DAQ_0DViewer_Det_type.names('daq_0Dviewer')

        elif DAQ_type=="DAQ1D":
            for ind in range(Nviewers):
                self.viewer_widgets.append(QtWidgets.QWidget())
                self.ui.viewers.append(Viewer1D(self.viewer_widgets[-1]))
            self.detector_types=DAQ_1DViewer_Det_type.names('daq_1Dviewer')

        elif DAQ_type=="DAQ2D":
            for ind in range(Nviewers):
                self.viewer_widgets.append(QtWidgets.QWidget())
                self.ui.viewers.append(Viewer2D(self.viewer_widgets[-1]))
                self.ui.viewers[-1].set_scaling_axes(self.get_scaling_options())
                self.ui.viewers[-1].ui.auto_levels_pb.click()


            self.detector_types=DAQ_2DViewer_Det_type.names('daq_2Dviewer')


            self.settings.child('main_settings','axes').show()

            self.ui.viewers[0].ROI_select_signal.connect(self.update_ROI)
            self.ui.viewers[0].ui.ROIselect_pb.clicked.connect(self.show_ROI)

        self.viewer_types=[viewer.viewer_type for viewer in self.ui.viewers]


        for ind,viewer in enumerate(self.viewer_widgets):


            if ind==0:
                self.dockarea.addDock(self.ui.viewer_docks[-1],'right',self.ui.settings_dock)
            else:
                self.ui.viewer_docks.append(Dock(self.title+"_Viewer {:d}".format(ind), size=(500,300), closable=False))
                self.dockarea.addDock(self.ui.viewer_docks[-1],'right',self.ui.viewer_docks[-2])
            self.ui.viewer_docks[-1].addWidget(viewer)
            self.ui.viewers[ind].data_to_export_signal.connect(self.get_data_from_viewer)

        ##Setting detector types
        try:
            self.ui.Detector_type_combo.currentIndexChanged.disconnect(self.set_setting_tree)
        except: pass
        self.ui.Detector_type_combo.clear()
        self.ui.Detector_type_combo.addItems(self.detector_types)
        self.ui.Detector_type_combo.currentIndexChanged.connect(self.set_setting_tree)
        self.set_setting_tree()

    def do_save_continuous(self,datas):
        """
        method used to perform conitnuous saving of data, for instance for logging. Will save datas as a function of
        time in a h5 file set when *continuous_saving* parameter as been set.

        Parameters
        ----------
        datas:  list of OrderedDict as exported by detector plugins

        """
        try:
            h5group=self.file_continuous_save.root
            #init data if needed
            nodes_names=[node._v_name for node in self.file_continuous_save.list_nodes(h5group)]
            ##if self.DAQ_type=="DAQ0D":
            ##    data_type='Data0D'
            ##elif self.DAQ_type=="DAQ1D":
            ##    data_type='Data1D'
            ##elif self.DAQ_type=="DAQ2D":
            ##    data_type='Data2D'

            #init the enlargeable arrays
            for data_type in [data['type'] for data in datas]:
                if data_type not in nodes_names:
                    filters = tables.Filters(complevel=self.settings.child('continuous_saving','compression_options', 'h5comp_level').value(),
                                    complib=self.settings.child('continuous_saving','compression_options','h5comp_library').value())
                    data_group=self.file_continuous_save.create_group(h5group,data_type)
                    data_group._v_attrs.type=data_type.lower()
                    self.ini_date=datetime.datetime.now()
                    shape=(0,1)
                    array=self.file_continuous_save.create_earray(data_group,"Time",tables.Atom.from_dtype(np.dtype(np.float)),shape=shape, title="Time",filters=filters)
                    array._v_attrs['unit']="second"
                    for channels in datas: #list of OrderedDict
                        data_pannel=self.file_continuous_save.create_group(data_group,channels['name'])
                        data_pannel._v_attrs.type=data_type.lower()
                        for ind_channel,channel in enumerate(channels['data']):
                            shape=[0]
                            shape.extend(channel.shape)
                            array=self.file_continuous_save.create_earray(data_pannel,"CH{:03d}".format(ind_channel),tables.Atom.from_dtype(channel.dtype),shape=shape, title="CH{:03d}".format(ind_channel),filters=filters)
                            array.attrs['data_type']=data_type[-2:]
                            array.attrs['data_name']=channels['name']
                            array.attrs['shape'] = shape


            time_array=self.file_continuous_save.get_node(h5group._v_name+'/'+data_type+"/Time")
            dt=datetime.datetime.now()-self.ini_date
            time_array.append(np.array([dt.total_seconds()]).reshape((1,1)))
            for channels in datas: #list of OrderedDict
                for ind_channel,channel in enumerate(channels['data']):
                    array=self.file_continuous_save.get_node(h5group._v_name+'/'+channels['type']+'/'+channels['name']+'/CH{:03d}'.format(ind_channel))
                    shape=[1]
                    shape.extend(channel.shape)
                    array.append(channel.reshape(shape))

        except Exception as e:
            self.update_status(str(e),self.wait_time,'log')

    @pyqtSlot(edict)
    def get_data_from_viewer(self,datas):
        """
            Emit the grab done signal with datas as an attribute.

            =============== ===================== ===================
            **Parameters**    **Type**             **Description**
            *datas*           ordered dictionnary  the datas to show
            =============== ===================== ===================
        """
        # datas=OrderedDict(name=self.title,data0D=None,data1D=None,data2D=None)
        self.data_to_save_export['Ndatas']+=1
        for key in datas:
            if key!='name':
                if datas[key] is not None:
                    if self.data_to_save_export[key] is None:
                       self.data_to_save_export[key]=OrderedDict([])
                    for k in datas[key]:
                        self.data_to_save_export[key][k]=datas[key][k]

        if self.data_to_save_export['Ndatas']==len(self.ui.viewers):
            self.grab_done_signal.emit(self.data_to_save_export)

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

    def grab_data(self, grab_state=False):
        """
            Do a grab session using 2 profile :
                * if grab pb checked do  a continous save and send an "update_channels" thread command and a "grab" too.
                * if not send a "stop_grab" thread command with settings "main settings-naverage" node value as an attribute.

            See Also
            --------
            daq_utils.ThreadCommand, set_enabled_Ini_buttons
        """

        if not(grab_state):

            self.command_detector.emit(ThreadCommand("single",[self.settings.child('main_settings','Naverage').value()]))
        else:
            if not(self.ui.grab_pb.isChecked()):

                #if self.do_continuous_save:
                #    try:
                #        self.file_continuous_save.close()
                #    except: pass
                self.command_detector.emit(ThreadCommand("stop_grab"))
                self.set_enabled_Ini_buttons(enable=True)
                self.ui.settings_tree.setEnabled(True)
            else:

                self.ui.settings_tree.setEnabled(False)
                self.thread_status(ThreadCommand("update_channels"))
                self.set_enabled_Ini_buttons(enable=False)
                self.command_detector.emit(ThreadCommand("grab",[self.settings.child('main_settings','Naverage').value()]))

    def ini_det_fun(self):
        """
            | If Init detector button checked, init the detector and connect the data detector, the data detector temp, the status and the update_settings signals to their corresponding function.
            | Once done start the detector linked thread.
            |
            | Else send the "close" thread command.

            See Also
            --------
            set_enabled_grab_buttons, daq_utils.ThreadCommand, DAQ_Detector
        """
        try:
            QtWidgets.QApplication.processEvents()
            if not self.ui.IniDet_pb.isChecked():
                self.set_enabled_grab_buttons(enable=False)
                self.ui.Ini_state_LED.set_as_false()
                self.Initialized_state=False

                if hasattr(self,'detector_thread'):
                    self.command_detector.emit(ThreadCommand("close"))
                    QtWidgets.QApplication.processEvents()
                    QThread.msleep(1000)
                    if hasattr(self,'detector_thread'):
                        self.detector_thread.quit()

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

                self.command_detector.emit(ThreadCommand("ini_detector",attributes=[self.settings.child(('detector_settings')).saveState(),self.controller]))


        except Exception as e:
            self.update_status(str(e))
            self.set_enabled_grab_buttons(enable=False)


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
            daq_utils.select_file, show_data, update_status
        """
        try:
            self.load_file_pathname=daq_utils.select_file(start_path=self.save_file_pathname,save=False, ext=['h5','dat','txt']) #see daq_utils
            ext=self.load_file_pathname.suffix[1:]
            if ext=='h5':

                h5file=tables.open_file(str(self.load_file_pathname),mode='r')
                h5root=h5file.root

                children=[child._v_name for child in h5root._f_list_nodes()]
                for data_type in children:
                    channels=h5root._f_get_child(data_type)._f_list_nodes()
                    x_axis=channels[0]._f_get_child('x_axis').read()
                    datas=[OrderedDict(data=[channel._f_get_child('Data').read() for channel in channels],name=channels[0]._v_attrs['Channel_name'],type=data_type,x_axis=x_axis)]

            else:
                data_tot=np.loadtxt(str(self.load_file_pathname))
                if self.DAQ_type=='DAQ0D':
                    pass

                elif self.DAQ_type=='DAQ1D':
                    x_axis=data_tot[:,0]
                    for viewer in self.ui.viewers:
                        viewer.x_axis=x_axis
                    datas=[data_tot[:,ind+1] for ind in range(data_tot[:,1:].shape[1])]


                elif self.DAQ_type=='DAQ2D':
                    pass

            self.show_data(datas)
        except Exception as e:
            self.update_status(str(e),self.wait_time,'log')


    def load_settings(self,path=None):
        """
            to be checked to see if still working
            | Load settings contained in the pathname file (or select_file destination if path not defined).
            | Open a DAQ_type viewer instance (0D, 1D or 2D), send a data_to_save_export signal and restore state from the loaeded settings.

            =============== ========== =======================================
            **Parameters**   **Type**   **Description**
            *path*           string     the pathname of the file to be loaded
            =============== ========== =======================================

            See Also
            --------
            ini_det_fun, update_status
        """
        try:
            if self.ui.Ini_state_LED.state: #means  initialzed
                self.ui.IniDet_pb.setChecked(False)
                QtWidgets.QApplication.processEvents()
                self.ini_det_fun()

            if path is None or path is False:
                path=daq_utils.select_file(save=False,ext='par')
            with open(str(path), 'rb') as f:
                settings = pickle.load(f)
                settings_main=settings['settings_main']
                DAQ_type=settings_main['children']['main_settings']['children']['DAQ_type']['value']
                if DAQ_type!=self.settings.child('main_settings','DAQ_type'):
                    self.settings.child('main_settings','DAQ_type').setValue(DAQ_type)
                    QtWidgets.QApplication.processEvents()

                self.settings.restoreState(settings_main)


                settings_viewer=settings['settings_viewer']
                if hasattr(self.ui.viewers[0],'restore_state'):
                    self.ui.viewers[0].restore_state(settings_viewer)


        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)


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
                    self.DAQ_type=param.value()
                    self.change_viewer()
                    self.settings.child('continuous_saving','do_save').setValue(False)
                    if param.value() == 'DAQ2D':
                        self.settings.child('main_settings', 'axes').show()
                    else:
                        self.settings.child('main_settings', 'axes').hide()
                #elif param.name()=='Nviewers': #this parameter is readonly it is updated from the number of items in the data list sent to show_data
                #    self.update_viewer_pannels(param.value())
                elif param.name()=='show_averaging':
                    self.settings.child('main_settings', 'live_averaging').setValue(False)
                elif param.name()=='live_averaging':

                    self.settings.child('main_settings','show_averaging').setValue(False)
                    if param.value()==True:
                        self.settings.child('main_settings', 'N_live_averaging').show()
                        self.ind_continuous_grab=0
                        self.settings.child('main_settings', 'N_live_averaging').setValue(0)
                    else:
                        self.settings.child('main_settings', 'N_live_averaging').hide()
                elif param.name() in custom_tree.iter_children(self.settings.child('main_settings','axes'),[]):
                    if self.DAQ_type=="DAQ2D":
                        for viewer in self.ui.viewers:
                            viewer.set_scaling_axes(self.get_scaling_options())
                elif param.name() in custom_tree.iter_children(self.settings.child('detector_settings','ROIselect'),[]):
                    if self.DAQ_type=="DAQ2D":
                        try:
                            self.ui.viewers[0].ROI_select_signal.disconnect(self.update_ROI)
                        except: pass
                        if self.settings.child('detector_settings','ROIselect','use_ROI').value():
                            if not self.ui.viewers[0].ui.ROIselect_pb.isChecked():
                                self.ui.viewers[0].ui.ROIselect_pb.clicked()
                                QtWidgets.QApplication.processEvents()
                        self.ui.viewers[0].ui.ROIselect.setPos(self.settings.child('detector_settings','ROIselect','x0').value(),self.settings.child('detector_settings','ROIselect','y0').value())
                        self.ui.viewers[0].ui.ROIselect.setSize([self.settings.child('detector_settings','ROIselect','width').value(),self.settings.child('detector_settings','ROIselect','height').value()])
                        self.ui.viewers[0].ROI_select_signal.connect(self.update_ROI)

                elif param.name()=='continuous_saving_opt':
                    self.settings.child(('continuous_saving')).show(param.value())

                elif param.name()=='do_save':
                    if param.value() is True:
                        self.set_continuous_save()
                    else:
                        try:
                            self.file_continuous_save.close()
                        except: pass

                self.update_settings_signal.emit(edict(path=path,param=param))


            elif change == 'parent':
                pass


    def process_overshoot(self,datas):
        if self.settings.child('main_settings','overshoot','stop_overshoot').value():
            for channels in datas:
                for channel in channels['data']:
                    if any(channel>=self.settings.child('main_settings','overshoot','overshoot_value').value()):
                        self.overshoot_signal.emit(True)


    def quit_fun(self):
        """
            | close the current instance of daq_viewer_main emmiting the quit signal.
            | Treat an exception if an error during the detector unitializing has occured.

        """
        # insert anything that needs to be closed before leaving
        try:
            if self.Initialized_state==True: #means  initialzed
                self.ui.IniDet_pb.click()
                QtWidgets.QApplication.processEvents()
            self.quit_signal.emit()
            try:
                self.ui.settings_dock.close() #close the settings widget
            except: pass
            try:
                for dock in self.ui.viewer_docks:
                    dock.close() #the dock viewers
            except: pass


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

    @pyqtSlot()
    def raise_timeout(self):
        """
            Print the "timeout occured" error message in the status bar via the update_status method.

            See Also
            --------
            update_status
        """
        self.update_status("Timeout occured",wait_time=self.wait_time,log_type="log")

    def save_current(self):
        """
            Save the current opened file from the select_file obtained pathname into a h5 file structure.

            See Also
            --------
            daq_utils.select_file, save_export_data
        """
        self.do_save_data=True
        self.save_file_pathname=daq_utils.select_file(start_path=self.save_file_pathname,save=True, ext='h5') #see daq_utils
        self.save_export_data(self.data_to_save_export)


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
            daq_utils.select_file, daq_utils.custom_parameter_tree.parameter_to_xml_string, update_status
        """

        if path is None:
            path=daq_utils.select_file(start_path=path,save=True, ext='h5') #see daq_utils

        try:
            h5file=tables.open_file(str(path),mode='w')
            h5group=h5file.root
            h5group._v_attrs.type='detector'

            settings_str=custom_tree.parameter_to_xml_string(self.settings)
            if self.DAQ_type!='DAQ0D':
                settings_str=b'<All_settings>'+settings_str
                settings_str+=custom_tree.parameter_to_xml_string(self.ui.viewers[0].roi_settings)+b'</All_settings>'
            h5group._v_attrs.settings=settings_str

            if datas['data0D'] is not None: #save Data0D if present
                if len(datas['data0D'])!=0: #save Data0D only if not empty (could happen)
                    data0D_group=h5file.create_group(h5group,'Data0D')
                    data0D_group._v_attrs.type='data0D'
                    for ind_channel,key in enumerate(datas['data0D'].keys()):

                        try:
                            array=h5file.create_carray(data0D_group,"CH{:03d}".format(ind_channel),obj=np.array([datas['data0D'][key]]), title=key,filters=self.filters)
                            array.attrs['type']='data'
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
                            array.attrs['type']='data'
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
                            array.attrs['type']='data'
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

    @pyqtSlot(OrderedDict)
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

        if self.do_save_data:
            self.save_datas(self.save_file_pathname,datas)
            self.do_save_data=False

    def save_new(self):
        """
            Do a new save from the select_file obtained pathname into a h5 file structure.

            See Also
            --------
            daq_utils.select_file, snapshot
        """
        self.do_save_data=True
        self.save_file_pathname=daq_utils.select_file(start_path=self.save_file_pathname,save=True, ext='h5') #see daq_utils
        self.snapshot(pathname=self.save_file_pathname)


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
            daq_utils.select_file, update_status
        """
        try:
            if path is None or path is False:
                path=daq_utils.select_file(save=True,ext='par')

            settings_main=self.settings.saveState()
            if hasattr(self.ui.viewers[0],'roi_settings'):
                settings_viewer=self.ui.viewers[0].roi_settings.saveState()
            else:
                settings_viewer=None

            settings=OrderedDict(settings_main=settings_main,settings_viewer=settings_viewer)

            if path is not None: #could be if the Qdialog has been canceled
                with open(str(path), 'wb') as f:
                    pickle.dump(settings, f, pickle.HIGHEST_PROTOCOL)

        except Exception as e:
            self.update_status(str(e),wait_time=self.wait_time)

    def set_continuous_save(self):
        """
            Set a continous save file using the base path located file with
            a header-name containing date as a string.

            See Also
            --------
            daq_utils.set_current_scan_path
        """
        if self.settings.child('continuous_saving','do_save').value():
            date=datetime.datetime.now()
            if not os.path.isdir(self.settings.child('continuous_saving','base_path').value()):
                os.mkdir(self.settings.child('continuous_saving','base_path').value())

            self.do_continuous_save=True
            # set the filename and path
            base_name=self.settings.child('continuous_saving','base_name').value()
            scan_path,current_filename,continuous_save_path=daq_utils.set_current_scan_path(self.settings.child('continuous_saving','base_path').value(),
                                                                       base_name=base_name)

            self.continuous_save_path=continuous_save_path.parent #will remove the dataset part used for DAQ_scan datas

            self.continuous_save_filename=base_name+date.strftime('_%Y%m%d_%H_%M_%S.h5')
            self.settings.child('continuous_saving','current_file_name').setValue(str(self.continuous_save_path.joinpath(self.continuous_save_filename)))

            self.file_continuous_save=tables.open_file(str(self.continuous_save_path.joinpath(self.continuous_save_filename)),'a')
            h5group=self.file_continuous_save.root
            h5group._v_attrs.type='detector'

            settings_str=custom_tree.parameter_to_xml_string(self.settings)
            if self.DAQ_type!='DAQ0D':
                settings_str=b'<All_settings>'+settings_str
                settings_str+=custom_tree.parameter_to_xml_string(self.ui.viewers[0].roi_settings)+b'</All_settings>'
            h5group._v_attrs.settings=settings_str

        else:
            self.do_continuous_save=False
            try:
                self.file_continuous_save.close()
            except Exception as e:
                pass

    @pyqtSlot(str)
    def set_DAQ_type(self,daq_type):
        self.DAQ_type=daq_type
        self.settings.child('main_settings','DAQ_type').setValue(daq_type)

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




    def set_setting_tree(self):
        """
            Set the local setting tree instance cleaning the current one and populate it with
            standard options corresponding to the pymodaq type viewer (0D, 1D or 2D).

            See Also
            --------
            update_status
        """
        det_name=self.ui.Detector_type_combo.currentText()
        if det_name=='':
            det_name='Mock'
        self.detector_name=det_name
        self.settings.child('main_settings','detector_type').setValue(self.detector_name)
        try:
            if len(self.settings.child(('detector_settings')).children())>0:
                for child in self.settings.child(('detector_settings')).children()[1:]:#leave just the ROIselect group
                    child.remove()
            if self.DAQ_type=='DAQ0D':
                obj=getattr(getattr(plugins_0D,'daq_0Dviewer_'+self.detector_name),'DAQ_0DViewer_'+self.detector_name)
            elif self.DAQ_type=="DAQ1D":
                obj=getattr(getattr(plugins_1D,'daq_1Dviewer_'+self.detector_name),'DAQ_1DViewer_'+self.detector_name)
            elif self.DAQ_type=='DAQ2D':
                obj=getattr(getattr(plugins_2D,'daq_2Dviewer_'+self.detector_name),'DAQ_2DViewer_'+self.detector_name)


            params=getattr(obj,'params')
            det_params=Parameter.create(name='Det Settings', type='group', children=params)
            self.settings.child(('detector_settings')).addChildren(det_params.children())
        except Exception as e:
            self.update_status(str(e), wait_time=self.wait_time)

    @pyqtSlot(list)
    def show_data(self,datas):
        """
            | l.
            |
            | Process background buffer if needed.
            | Process live averaging if needed.
            | Show datas in case of 0D or 1D DAQ_type.
            | Send a list of images (at most 3) to the 2D viewer else.

            =============== =============================== ===================
            **Parameters**    **Type**                       **Description**
            *datas*           list of OrderedDict            the datas to show
            =============== =============================== ===================

            See Also
            --------
            update_status
        """
        try:
            self.data_to_save_export=OrderedDict(Ndatas=0,name=self.title,data0D=None,data1D=None,data2D=None) #to be populated from the results in the viewers
            Npannels=len(datas)
            self.process_overshoot(datas)

            data_types=[data['type'] for data in datas]


            if data_types!=self.viewer_types:
                self.update_viewer_pannels(data_types)



            if  self.ui.take_bkg_cb.isChecked():
                self.ui.take_bkg_cb.setChecked(False)
                self.bkg=datas

            #process bkg if needed
            if self.ui.do_bkg_cb.isChecked() and self.bkg is not None:
                try:
                    for ind_channels,channels in enumerate(datas):
                        for ind_channel,channel in enumerate(channels['data']):
                            datas[ind_channels]['data'][ind_channel]=datas[ind_channels]['data'][ind_channel]-self.bkg[ind_channels]['data'][ind_channel]
                except Exception as e:
                    self.update_status(str(e),self.wait_time,'log')


            if self.settings.child('main_settings','live_averaging').value():
                self.settings.child('main_settings','N_live_averaging').setValue(self.ind_continuous_grab)
                ##self.ui.current_Naverage.setValue(self.ind_continuous_grab)
                self.ind_continuous_grab+=1
                if self.ind_continuous_grab>1:
                    try:
                        for ind,dic in enumerate(datas):
                            dic['data']=[((self.ind_continuous_grab-1)*self.current_datas[ind]['data'][ind_channel]+dic['data'][ind_channel])/self.ind_continuous_grab for ind_channel in range(len(dic['data']))]
                    except Exception as e:
                        self.update_status(str(e),self.wait_time,log_type='log')

            for ind,data in enumerate(datas):
                self.ui.viewers[ind].title=data['name']
                if data['name']!='':
                    self.ui.viewer_docks[ind].setTitle(self.title+' '+data['name'])
                if data['type']=='Data0D':
                    self.ui.viewers[ind].show_data(data['data'])
                elif data['type']=='Data1D':
                    if 'x_axis' in data.keys():
                        self.ui.viewers[ind].x_axis=data['x_axis']
                    self.ui.viewers[ind].show_data(data['data'])

                elif data['type']=='Data2D':
                    if 'x_axis' in data.keys():
                        self.ui.viewers[ind].x_axis = data['x_axis']
                    if 'y_axis' in data.keys():
                        self.ui.viewers[ind].y_axis = data['y_axis']
                    self.ui.viewers[ind].setImage(*data['data'])


                else:
                    if 'nav_axes' in data.keys():
                        self.ui.viewers[ind].show_data(data['data'][0],nav_axes=data['nav_axes'])
                    else:
                        self.ui.viewers[ind].show_data(data['data'][0])

            self.current_datas=datas


            if self.do_continuous_save:
                self.do_save_continuous(datas)



        except Exception as e:
            self.update_status(str(e),self.wait_time,'log')

    def show_settings(self):
        """
            Set the settings tree visible if the corresponding button is checked.
        """

        if self.ui.settings_pb.isChecked():
            self.ui.settings_tree.setVisible(True)
        else:
            self.ui.settings_tree.setVisible(False)

    @pyqtSlot(list)
    def show_temp_data(self,datas):
        """
            | Show the given datas in the different pannels but do not send processed datas signal.

            =============== ====================== ========================
            **Parameters**    **Type**               **Description**
            datas             list  of OrderedDict   the datas to be showed.
            =============== ====================== ========================

        """
        data_types=[data['type'] for data in datas]
        if data_types!=self.viewer_types:
            self.update_viewer_pannels(data_types)
            QtWidgets.QApplication.processEvents()

        for ind,data in enumerate(datas):
            self.ui.viewers[ind].title=data['name']
            if data['name']!='':
                self.ui.viewer_docks[ind].setTitle(self.title+' '+data['name'])
            if data['type']=='Data0D':
                self.ui.viewers[ind].show_data_temp(data['data'])
            elif  data['type']=='Data1D':
                self.ui.viewers[ind].show_data_temp(data['data'])
                if 'x_axis' in data.keys():
                    self.ui.viewers[ind].x_axis=data['x_axis']
            elif data['type']=='Data2D':
                self.ui.viewers[ind].setImageTemp(*data['data'])
                # if 'x_axis' in data.keys():
                #     x_offset=np.min(data['x_axis'])
                #     x_scaling=data['x_axis'][1]-data['x_axis'][0]
                # else:
                #     x_offset=0
                #     x_scaling=1
                # if 'y_axis' in data.keys():
                #     y_offset=np.min(data['y_axis'])
                #     y_scaling=data['y_axis'][1]-data['y_axis'][0]
                # else:
                #     y_offset=0
                #     y_scaling=1
                # self.ui.viewers[ind].set_scaling_axes(scaling_options=edict(scaled_xaxis=edict(label="",units=None,offset=x_offset,scaling=x_scaling),
                #                                                             scaled_yaxis=edict(label="",units=None,offset=y_offset,scaling=y_scaling)))
            else:
                if 'nav_axes' in data.keys():
                    self.ui.viewers[ind].show_data_temp(data['data'][0],nav_axes=data['nav_axes'])
                else:
                    self.ui.viewers[ind].show_data_temp(data['data'][0])

    def snapshot(self, pathname=None):
        """
            Do one single grab and save the data in pathname.

            =============== =========== =================================================
            **Parameters**    **Type**    **Description**
            *pathname*        string      the pathname to the location os the saved file
            =============== =========== =================================================

            See Also
            --------
            grab, update_status
        """
        try:
            self.do_save_data=True
            if pathname is None:
                raise (Exception("filepathanme has not been defined in snapshot"))
            self.save_file_pathname=pathname

            self.grab_data(False)
        except Exception as e:
            self.update_status(str(e),self.wait_time,'log')

    def show_ROI(self):
        if self.DAQ_type=="DAQ2D":
            self.settings.child('detector_settings','ROIselect').setOpts(visible=self.ui.viewers[0].ui.ROIselect_pb.isChecked())
            pos=self.ui.viewers[0].ui.ROIselect.pos()
            size=self.ui.viewers[0].ui.ROIselect.size()
            self.update_ROI(QRectF(pos[0],pos[1],size[0],size[1]))


    def stop_all(self):
        self.command_detector.emit(ThreadCommand("stop_all"))
        if self.ui.grab_pb.isChecked():
            self.ui.grab_pb.setChecked(False)
        self.set_enabled_Ini_buttons(enable=True)

        self.ui.settings_tree.setEnabled(True)

    def take_bkg(self):
        """
            Save a new file if bkg check button is on.

            See Also
            --------
            save_new
        """
        if self.ui.take_bkg_cb.isChecked():
            self.save_new()

    @pyqtSlot(ThreadCommand)
    def thread_status(self,status): # general function to get datas/infos from all threads back to the main
        """
            General function to get datas/infos from all threads back to the main.

            In case of :
                * **Update_Status**   *command* : update the status from the given status attributes
                * **ini_detector**    *command* : update the status with "detector initialized" value and init state if attributes not null.
                * **close**           *command* : close the current thread and delete corresponding attributes on cascade.
                * **grab**            *command* : Do nothing
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

        elif status.command=="ini_detector":
            self.update_status("detector initialized: "+str(status.attributes[0]['initialized']),wait_time=self.wait_time)

            if status.attributes[0]['initialized']:
                self.controller=status.attributes[0]['controller']
                self.set_enabled_grab_buttons(enable=True)
                self.ui.Ini_state_LED.set_as_true()
                self.Initialized_state=True
            else:
                self.Initialized_state=False

        elif status.command=="close":
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

        elif status.command=="grab":
            pass

        elif status.command=="x_axis":
            try:
                x_axis=status.attributes[0]
                if type(x_axis)==list:
                    if len(x_axis)==len(self.ui.viewers):
                        for ind,viewer in enumerate(self.ui.viewers):
                            viewer.x_axis=x_axis[ind]
                else:
                    for viewer in self.ui.viewers:
                        viewer.x_axis=x_axis
            except Exception as e:
                self.update_status(str(e), self.wait_time, 'log')


        elif status.command=="y_axis":
            try:
                y_axis=status.attributes[0]
                if type(y_axis)==list:
                    if len(y_axis)==len(self.ui.viewers):
                        for ind,viewer in enumerate(self.ui.viewers):
                            viewer.y_axis=y_axis[ind]
                else:
                    for viewer in self.ui.viewers:
                        viewer.y_axis=y_axis
            except Exception as e:
                self.update_status(str(e), self.wait_time, 'log')

        elif status.command=="update_channels":
            pass
            #if self.DAQ_type=='DAQ0D':
            #    for viewer in self.ui.viewers:
            #        viewer.update_channels()


        elif status.command=='update_settings':
            try:
                self.settings.sigTreeStateChanged.disconnect(self.parameter_tree_changed)#any changes on the detcetor settings will update accordingly the gui
            except: pass
            try:
                if status.attributes[2] == 'value':
                    self.settings.child('detector_settings',*status.attributes[0]).setValue(status.attributes[1])
                elif status.attributes[2] == 'limits':
                    self.settings.child('detector_settings',*status.attributes[0]).setLimits(status.attributes[1])
                elif status.attributes[2] == 'options':
                    self.settings.child('detector_settings',*status.attributes[0]).setOpts(**status.attributes[1])
                elif status.attributes[2] == 'childAdded':
                    self.settings.child('detector_settings',*status.attributes[0]).addChild(status.attributes[1][0])
            except Exception as e:
                self.update_status(str(e),self.wait_time,'log')
            self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

        elif status.command=='raise_timeout':
            self.raise_timeout()

        elif status.command == 'show_splash':
            self.ui.settings_tree.setEnabled(False)
            self.splash_sc.show()
            self.splash_sc.raise_()
            self.splash_sc.showMessage(status.attributes[0], color=Qt.white)

        elif status.command == 'close_splash':
            self.splash_sc.close()
            self.ui.settings_tree.setEnabled(True)

    def update_com(self):
        pass

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

    def update_viewer_pannels(self,data_types=['Data0D']):
        Nviewers=len(data_types)

        self.settings.child('main_settings','Nviewers').setValue(Nviewers)
        DAQ_type=self.settings.child('main_settings','DAQ_type').value()

        #check if viewers are compatible with new data type
        N=0
        for ind, data_type in enumerate(data_types):
            if len(self.viewer_types)>ind:
                if data_type==self.viewer_types[ind]:
                    N+=1
                else:
                    break
            else:
                break

        while len(self.ui.viewers)>N:# remove all viewers after index N
        ##while len(self.ui.viewers)>Nviewers:
            viewer=self.ui.viewers.pop()
            widget=self.viewer_widgets.pop()
            widget.close()
            dock=self.ui.viewer_docks.pop()
            dock.close()
            QtWidgets.QApplication.processEvents()
        ##for ind,data_type in enumerate(data_types):
        ind_loop=0
        Nviewers_init=len(self.ui.viewers)
        while len(self.ui.viewers)<len(data_types):
            data_type=data_types[Nviewers_init+ind_loop]
            ind_loop+=1
            if data_type=="Data0D":
                self.viewer_widgets.append(QtWidgets.QWidget())
                self.ui.viewers.append(Viewer0D(self.viewer_widgets[-1]))
            elif data_type=="Data1D":
                self.viewer_widgets.append(QtWidgets.QWidget())
                self.ui.viewers.append(Viewer1D(self.viewer_widgets[-1]))
            elif data_type=="Data2D":

                self.viewer_widgets.append(QtWidgets.QWidget())
                self.ui.viewers.append(Viewer2D(self.viewer_widgets[-1]))
                self.ui.viewers[-1].set_scaling_axes(self.get_scaling_options())
                self.ui.viewers[-1].ui.auto_levels_pb.click()

            else: #for multideimensional data 0 up to dimension 4
                self.viewer_widgets.append(QtWidgets.QWidget())
                self.ui.viewers.append(ViewerND(self.viewer_widgets[-1]))



            self.ui.viewer_docks.append(Dock(self.title+"_Viewer {:d}".format(len(self.ui.viewer_docks)+1), size=(500,300), closable=False))
            self.ui.viewer_docks[-1].addWidget(self.viewer_widgets[-1])
            if ind==0:
                self.dockarea.addDock(self.ui.viewer_docks[-1],'right',self.ui.settings_dock)
            else:
                self.dockarea.addDock(self.ui.viewer_docks[-1],'right',self.ui.viewer_docks[-2])
            self.ui.viewers[-1].data_to_export_signal.connect(self.get_data_from_viewer)
            QtWidgets.QApplication.processEvents()

        self.viewer_types=[viewer.viewer_type for viewer in self.ui.viewers]
        QtWidgets.QApplication.processEvents()

    @pyqtSlot(QRectF)
    def update_ROI(self,rect=QRectF(0,0,1,1)):
        if self.DAQ_type=="DAQ2D":
            self.settings.child('detector_settings','ROIselect','x0').setValue(int(rect.x()))
            self.settings.child('detector_settings','ROIselect','y0').setValue(int(rect.y()))
            self.settings.child('detector_settings','ROIselect','width').setValue(max([1,int(rect.width())]))
            self.settings.child('detector_settings','ROIselect','height').setValue(max([1,int(rect.height())]))


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
              * **ini_detector** : Send the corresponding Thread command via a status signal.
              * **close**        : Send the corresponding Thread command via a status signal.
              * **grab**         : Call the local grab method with command(s) attributes.
              * **single**       : Call the local single method with command(s) attributes.
              * **stop_grab**    : Send the correpsonding Thread command via a status signal.

            =============== ================= ============================
            **Parameters**    *Type*           **Description**
            *command*         ThreadCommand()  The command to be treated
            =============== ================= ============================

            See Also
            --------
            grab, single, daq_utils.ThreadCommand
        """
        if command.command=="ini_detector":
            status=self.ini_detector(*command.attributes)
            self.status_sig.emit(ThreadCommand(command.command,[ status,'log']))

        elif command.command=="close":
            status=self.Close()
            self.status_sig.emit(ThreadCommand(command.command,[ status,'log']))

        elif command.command=="grab":
            self.single_grab=False
            self.grab_state=True
            self.grab_data(*command.attributes)

        elif command.command=="single":
            self.single_grab=True
            self.grab_state=True
            self.single(*command.attributes)

        elif command.command=="stop_grab":
            self.grab_state=False
            self.status_sig.emit(ThreadCommand("Update_Status",['Stoping grab']))

        elif command.command=="stop_all":
            self.grab_state=False
            self.detector.stop()
            QtWidgets.QApplication.processEvents()


    def ini_detector(self, params_state=None, controller=None):
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
            ini_detector, daq_utils.ThreadCommand
        """
        try:
            #status="Not initialized"
            status=edict(initialized=False,info="",x_axis=None,y_axis=None)
            if self.DAQ_type=='DAQ0D':
                class_=getattr(getattr(plugins_0D,'daq_0Dviewer_'+self.detector_name),'DAQ_0DViewer_'+self.detector_name)
                self.detector=class_(self,params_state)
                self.detector.data_grabed_signal.connect(self.data_ready)
                self.detector.data_grabed_signal_temp.connect(self.emit_temp_data)
                status.update(self.detector.ini_detector(controller))
                if status['x_axis'] is not None:
                    x_axis=status['x_axis']
                    self.status_sig.emit(ThreadCommand("x_axis",[x_axis]))
                #status="Initialized"

            elif self.DAQ_type=='DAQ1D':
                class_=getattr(getattr(plugins_1D,'daq_1Dviewer_'+self.detector_name),'DAQ_1DViewer_'+self.detector_name)
                self.detector=class_(self,params_state)
                self.detector.data_grabed_signal.connect(self.data_ready)
                self.detector.data_grabed_signal_temp.connect(self.emit_temp_data)
                status.update(self.detector.ini_detector(controller))
                if status['x_axis'] is not None:
                    x_axis=status['x_axis']
                    self.status_sig.emit(ThreadCommand("x_axis",[x_axis]))
                #status="Initialized"

            elif self.DAQ_type=='DAQ2D':
                class_=getattr(getattr(plugins_2D,'daq_2Dviewer_'+self.detector_name),'DAQ_2DViewer_'+self.detector_name)
                self.detector=class_(self,params_state)
                self.detector.data_grabed_signal.connect(self.data_ready)
                self.detector.data_grabed_signal_temp.connect(self.emit_temp_data)
                status.update(self.detector.ini_detector(controller))
                if status['x_axis'] is not None:
                    x_axis=status['x_axis']
                    self.status_sig.emit(ThreadCommand("x_axis",[x_axis]))
                if status['y_axis'] is not None:
                    y_axis=status['y_axis']
                    self.status_sig.emit(ThreadCommand("y_axis",[y_axis]))
                #status="Initialized"


            else:
                raise Exception(self.detector_name + " unknown")

            self.hardware_averaging=class_.hardware_averaging #to check if averaging can be done directly by the hardware or done here software wise

            return status
        except Exception as e:
            self.status_sig.emit(ThreadCommand("Update_Status",[str(e),'log']))
            return status

    @pyqtSlot(list)
    def emit_temp_data(self,datas):
        self.data_detector_temp_sig.emit(datas)

    @pyqtSlot(list)
    def data_ready(self,datas):
        """
            | Update the local datas attributes from the given datas parameter if the averaging has to be done software wise.
            |
            | Else emit the data detector signals with datas parameter as an attribute.

            =============== ===================== =========================
            **Parameters**    **Type**             **Description**
            *datas*           list                the datas to be emitted.
            =============== ===================== =========================

            See Also
            --------
            daq_utils.ThreadCommand
        """
        if not(self.hardware_averaging): #to execute if the averaging has to be done software wise
            self.ind_average+=1
            if self.ind_average==1:
                self.datas=datas
            else:
                try:
                    for indpannel, dic in enumerate(datas):
                        self.datas[indpannel]['data']=[((self.ind_average-1)*self.datas[indpannel]['data'][ind]+datas[indpannel]['data'][ind])/self.ind_average for ind in range(len(datas[indpannel]['data']))]

                    #self.datas=[((self.ind_average-1)*self.datas[indbis][data][ind]+datas[indbis][data][ind])/self.ind_average for ind in range(len(datas))]
                    if self.show_averaging:
                        self.emit_temp_data(self.datas)
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
            self.detector.stop()

    def single(self, Naverage=1):
        """
            Call the grab method with Naverage parameter as an attribute.

            =============== =========== ==================
            **Parameters**    **Type**    **Description**
            *Naverage*        int
            =============== =========== ==================

            See Also
            --------
            daq_utils.ThreadCommand, grab
        """
        try:
            self.grab_data(Naverage, live=False)
            #self.ind_average=0
            #self.Naverage=Naverage
            #self.status_sig.emit(["Update_Status","Start grabing"])
            #self.detector.grab(Naverage)


        except Exception as e:

            self.status_sig.emit(ThreadCommand("Update_Status",[str(e),'log']))

    def grab_data(self, Naverage=1, live=True):
        """
            | Update status with 'Start Grabing' Update_status sub command of the Thread command.
            | Process events and grab naverage is needed.

            =============== =========== ==================
            **Parameters**    **Type**    **Description**
            *Naverage*        int
            =============== =========== ==================

            See Also
            --------
            daq_utils.ThreadCommand, grab
        """
        try:
            self.ind_average=0
            self.Naverage=Naverage
            if Naverage>1:
                self.average_done=False
            self.status_sig.emit(ThreadCommand("Update_Status",['Start Grabing']))
            self.waiting_for_data=False


            ####TODO: choose if the live mode is only made inside the plugins (suitable with STEM plugins) or if we keep it on top?
            ##self.detector.grab(Naverage,live=live)

            while 1:
                try:
                    if not(self.waiting_for_data):
                        self.waiting_for_data=True
                        QThread.msleep(self.wait_time)
                        self.detector.grab_data(Naverage, live=live)
                    QtWidgets.QApplication.processEvents()
                    if self.single_grab:
                        if self.hardware_averaging:
                            break
                        else:
                            if self.average_done:
                                break


                    if self.grab_state==False:

                        #self.detector.stop()
                        break
                except Exception as e:
                    print(str(e))

        except Exception as e:
            self.status_sig.emit(ThreadCommand("Update_Status",[str(e),'log']))


    def Close(self):
        """
            close the current instance of DAQ_Detector.
        """
        try:
            status=self.detector.close()
        except Exception as e:
            status=str(e)
        return status






if __name__ == '__main__':
    from pymodaq.daq_utils.daq_enums import DAQ_type
    app = QtWidgets.QApplication(sys.argv);
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000,500)
    win.setWindowTitle('pymodaq main')
    prog = DAQ_Viewer(area,title="Testing",DAQ_type=DAQ_type['DAQ1D'].name)
    win.show()
    sys.exit(app.exec_())


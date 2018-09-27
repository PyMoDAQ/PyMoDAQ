from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize, QTimer, QDateTime, QDate, QTime

import sys
from PyMoDAQ.DAQ_Utils import python_lib as mylib
import pyqtgraph as pg
from pyqtgraph.dockarea import Dock, DockArea
import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter, ParameterTree
import PyMoDAQ.DAQ_Utils.custom_parameter_tree as custom_tree# to be placed after importing Parameter
import numpy as np
import pandas as pd
from PyMoDAQ.DAQ_Utils.hardware.digilent import digilent_main as dg

from PyMoDAQ.DAQ_Viewer.DAQ_viewer_main import DAQ_Viewer
from PyMoDAQ.DAQ_Utils.plotting.viewer1D.viewer1D_main import Viewer1D
from collections import OrderedDict
from easydict import EasyDict as edict
from PyMoDAQ.DAQ_Utils import DAQ_utils

import tables
import datetime
import pickle
import os
import re

class DAQ_Metheor(QtWidgets.QWidget,QObject):
    """

        ========================== =============================== ============================================================
         **Attributes**             **Type**                          **Description**

         *log_signal*               instance of pyqtSignal          Message transmission signal containing string
         *update_settings_signal*   instance of pyqtSignal          Message transmission signal containing dictionnary
         *process_data_sig*         instance of pyqtSignal          Message transmission signal containing ordered dictionnary
         *params*                   dictionnary  list               Representing the parameter tree

         *det_name*                 string                          The detector name
         *dock_viewer_settings*     instance of Dock                Viewer settings element of the User Interface
         *dock_viewer*              instance of Dock                Viewer element of the User Interface
         *fft_widget*               instance of QWidget             fft base element of the User Interface
         *dock_fft*                 instance of Dock                fft element of the User Interface
         *temperature_widget*       instance of QWidget             Temperature base element of the User Interface
         *dock_temperature*         instance of Dock                Temperature element of the User Interface
         *dock_settings*            instance of Dock                Temperature viewer base element of the User Interface
         *temperature_viewer*       instance of Viewer1D            Temperature viewer element of the User Interface
         *date*                     string                          The current date
         *daq_type*                 string                          The dimension of the current PyMoDAQ (DAQ1D as default)
         *control_type*             string                          The name of the controller used
         *devices*                  string list                     The digilent hardware devices list
         *process_object*           instance of DAQ_Process_data    ???
         *menubar*                  instance of QMenuBar            The generic menubar object of menu
        ========================== =============================== ============================================================

        References
        ----------
        PyQt5, pyqtgraph, numpy, pandas, easydict, tables, QtWidgets, QObject
    """
    log_signal=pyqtSignal(str)
    update_settings_signal=pyqtSignal(edict)
    process_data_sig=pyqtSignal(OrderedDict)
    params = [ {'title': 'Main settings:','name': 'main_settings','type': 'group','children':[
                    {'title': 'File name:','name': 'filename', 'type': 'text', 'value': ""},
                    {'title': 'Date:','name': 'date', 'type': 'str', 'value': ""},
                    ]},
            {'title': 'Laser Settings:','name': 'laser_settings','type': 'group','children':[
                    {'title': 'Ready:','name': 'laser_ready', 'type': 'led', 'value': False},
                    {'title': 'Device:','name': 'laser_device', 'type': 'str', 'value': ''},
                    {'title': 'Attenuation (V):','name': 'attenuation', 'type': 'float', 'value': 3.95, 'min': 0.001, 'max': 5.0},
                    {'title': 'Laser Rep. Rate (kHz):','name': 'laser_rep_rate', 'type': 'float', 'value': 70},
                    {'title': 'Laser wavelength (nm):','name': 'laser_wavelength', 'type': 'float', 'value': 1500},
                    {'title': 'Stokes-AS shift (nm):','name': 'stokes_shift', 'type': 'float', 'value': 50},
                    ]},
            {'title': 'Analysis:','name': 'analysis','type': 'group','children':[
                    {'title': 'Do Analysis:', 'name': 'do_analysis', 'type': 'bool', 'value': False},
                    {'title': 'Show:','name': 'show_analysis', 'type': 'list', 'value': 'raw', 'values': ['raw','FFT','average']},
                    {'title': 'Do FFT filtering:', 'name': 'do_fft', 'type': 'bool', 'value': False},
                    {'title': 'FFT resolution (m)', 'name': 'fft_resolution', 'type': 'int', 'value': 25, 'min': 0},
                    {'title': 'Gaussian order:', 'name': 'gaussian_order', 'type': 'int', 'value': 1, 'min': 1},
                    {'title': 'FFT threshold:', 'name': 'fft_threshold', 'type': 'int', 'value': 1},
                    ]},
              {'title': 'Temperature:','name': 'temperature','type': 'group','children':[
                    {'title': 'Process temperature:','name': 'process_temperature', 'type': 'bool', 'value': False},
                    {'title': 'Get temperature from:','name': 'get_temp_from', 'type': 'list', 'value': 'constants', 'values': ['constants','calibration']},
                        {'title': 'Temperatures:','name': 'temperatures','type': 'group','children':[
                            {'title': 'T1 (C):', 'name': 'T1', 'type': 'float', 'value': 60},
                            {'title': 'T2 (C):', 'name': 'T2', 'type': 'float', 'value': 60},
                            {'title': 'T3 (C):', 'name': 'T3', 'type': 'float', 'value': 0},
                            ]},
                        {'title': 'Distances:','name': 'distances','type': 'group','children':[
                            {'title': 'Zone 1:','name': 'zone1','type': 'group','children':[
                                {'title': 'x1 (m):', 'name': 'x1', 'type': 'float', 'value': 190},
                                {'title': 'x2 (m):', 'name': 'x2', 'type': 'float', 'value': 200},
                                ]},
                            {'title': 'Zone 2:','name': 'zone2','type': 'group','children':[
                                {'title': 'x1 (m):', 'name': 'x1', 'type': 'float', 'value': 635},
                                {'title': 'x2 (m):', 'name': 'x2', 'type': 'float', 'value': 645},
                                ]},
                            {'title': 'Zone 3:','name': 'zone3','type': 'group','children':[
                                {'title': 'x1 (m):', 'name': 'x1', 'type': 'float', 'value': 855},
                                {'title': 'x2 (m):', 'name': 'x2', 'type': 'float', 'value': 866},
                                ]},
                            ]},
                        {'title': 'Constants:','name': 'constants','type': 'group','children':[
                            {'title': 'Gamma (K):', 'name': 'gamma', 'type': 'float', 'value': 419.206,'step': 1},
                            {'title': 'Offset:', 'name': 'offset', 'type': 'float', 'value': 1,'step':0.01},
                            {'title': 'Loss (dB/km):', 'name': 'loss', 'type': 'float', 'value': -0.007, 'step':0.0001},
                            {'title': 'Slope:', 'name': 'slope', 'type': 'float', 'value': 1, 'step': 0.0001},
                            {'title': 'AS amplification:', 'name': 'amplification', 'type': 'float', 'value': 0.3513, 'step':0.0001},
                            ]},
            ]}]



    def __init__(self,parent,fname=""):

        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(DAQ_Metheor,self).__init__()
        self.title='DAQ_Metheor'

        self.wait_time=1000
        self.dockarea=parent
        self.mainwindow=parent.parent()




        det_name='Picoscope'
        dock_viewer_settings=Dock(det_name+" settings", size=(150,250))
        dock_viewer=Dock(det_name+" viewer", size=(350,350))
        self.dockarea.addDock(dock_viewer_settings, 'top')
        self.dockarea.addDock(dock_viewer,'right',dock_viewer_settings)

        dock_fft=Dock('Analysed traces',size=(350,350))
        self.dockarea.addDock(dock_fft, 'bottom')
        fft_widget=QtWidgets.QWidget()
        self.fft_viewer=Viewer1D(fft_widget)
        dock_fft.addWidget(fft_widget)
        self.fft_viewer.ui.Do_math_pb.click()
        self.fft_viewer.roi_settings.child('math_settings','Nlineouts_sb').setValue(3)
        self.fft_viewer.ui.ROIs_widget.hide()
        self.fft_viewer.ui.Graph_Lineouts.hide()


        dock_temperature=Dock('Temperature',size=(350,350))
        self.dockarea.addDock(dock_temperature, 'right',dock_fft)
        temperature_widget=QtWidgets.QWidget()
        self.temperature_viewer=Viewer1D(temperature_widget)
        dock_temperature.addWidget(temperature_widget)

        dock_settings=Dock('Settings',size=(350,350))
        self.dockarea.addDock(dock_settings, 'right')
        self.temperature_viewer.set_axis_label(axis_settings=dict(orientation='bottom',label='Distance',units='m'))


        #%% create logger dock
        self.dock_logger=Dock("Logger")
        self.logger_list=QtWidgets.QListWidget()
        self.logger_list.setMinimumWidth(300)
        self.dock_logger.addWidget(self.logger_list)
        self.dockarea.addDock(self.dock_logger,'bottom',dock_settings)
        #dock_logger.setVisible(False)


        #create main parameter tree
        self.settings_tree = ParameterTree()
        dock_settings.addWidget(self.settings_tree,10)
        self.settings_tree.setMinimumWidth(300)
        self.settings=Parameter.create(name='Settings', type='group', children=self.params)
        self.settings_tree.setParameters(self.settings, showTop=False)
        #connecting from tree
        date=QDateTime.currentDateTime().toString()
        self.settings.child('main_settings','date').setValue(date)
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)#any changes on the settings will update accordingly the detector
        self.settings.child('temperature','temperatures').hide()
        self.settings.child('temperature','distances').hide()
        self.settings.child('temperature','constants').hide()


        for ind_region,region in enumerate(self.fft_viewer.linear_regions):
            x1=self.settings.child('temperature','distances','zone{:d}'.format(ind_region+1),'x1').value()
            x2=self.settings.child('temperature','distances','zone{:d}'.format(ind_region+1),'x2').value()
            region.setRegion([x1,x2])

            region.sigRegionChangeFinished.connect(self.update_calibration_regions)
            region.hide()

        daq_type='DAQ1D'
        control_type='Picoscope'
        self.detector_module=DAQ_Viewer(self.dockarea,dock_settings=dock_viewer_settings,
                                            dock_viewer=dock_viewer,title=det_name,DAQ_type=daq_type)

        self.detector_module.ui.Detector_type_combo.setCurrentText(control_type)
        self.detector_module.settings.child('detector_settings','main_settings','dynamic').setValue('14bits')
        self.detector_module.ui.IniDet_pb.click()
        QtWidgets.QApplication.processEvents()

        self.detector_module.ui.viewer.set_axis_label(axis_settings=dict(orientation='bottom',label='Time',units='ms'))
        self.detector_module.settings.child('main_settings','DAQ_type').hide()
        self.detector_module.settings.child('main_settings','detector_type').hide()
        self.detector_module.settings.child('main_settings','wait_time').hide()


        self.detector_module.settings.child('detector_settings','main_settings','dynamic').hide()
        self.detector_module.settings.child('detector_settings','main_settings','temporal','window').setValue(0.16)
        self.detector_module.settings.child('detector_settings','main_settings','temporal','Nsamples').setValue(10000)

        self.detector_module.settings.child('detector_settings','main_settings','trigger','trig_channel').setValue('Ext')
        self.detector_module.settings.child('detector_settings','main_settings','trigger','trig_level').setValue(2.5)
        self.detector_module.settings.child('detector_settings','main_settings','trigger','trig_type').setValue('Rising')
        self.detector_module.settings.child('detector_settings','main_settings','trigger','trig_pretrigger').setValue(0)
        self.detector_module.settings.child('detector_settings','main_settings','trigger','trig_delay').setValue(0.006)
        #self.detector_module.settings.child('detector_settings','main_settings','trigger').hide()

        self.detector_module.settings.child('detector_settings','channels','ChA','coupling').hide()
        self.detector_module.settings.child('detector_settings','channels','ChA','offset').setValue(0.00253)
        self.detector_module.settings.child('detector_settings','channels','ChA','range').setValue('50mV')
        self.detector_module.settings.child('detector_settings','channels','ChA','active').hide()
        self.detector_module.settings.child('detector_settings','channels','ChB','active').setValue(True)
        self.detector_module.settings.child('detector_settings','channels','ChB','active').hide()
        self.detector_module.settings.child('detector_settings','channels','ChB','coupling').hide()
        self.detector_module.settings.child('detector_settings','channels','ChB','range').setValue('20mV')
        self.detector_module.settings.child('detector_settings','channels','ChC').hide()
        self.detector_module.settings.child('detector_settings','channels','ChD').hide()


        self.detector_module.quit_signal.connect(self.quit_fun)
        self.detector_module.log_signal[str].connect(self.emit_log)

        self.group_index_fiber_R=1.4626# at 1550nm
        self.group_index_fiber_AS=1.4620# at 1450nm
        self.group_index_fiber_S=1.4633# at 1650nm
        self.c=3e8#m/s
        self.save_file_pathname=None
        self.data_to_save_export=OrderedDict([])


        self.log_signal[str].connect(self.add_log)

        #creating the menubar
        self.menubar=self.mainwindow.menuBar()
        self.create_menu(self.menubar)


        #init the digilent discovery
        self.dig=dg.Digilent_AnalogOut_IO()
        devices=self.dig.device_enumeration()
        if devices==[]:
            self.settings.child('laser_settings', 'laser_device').setValue(devices[0]['name']+" / "+devices[0]['serial'])
            self.dig.open_device(devices[0]['ind'])

            self.dig.set_channel_node_value(0,0,1) #enable the enable node
            self.dig.set_channel_node_value(0,1,5.0) #full attenuation to start with
            self.dig.set_master_state(True)
            self.dig.set_trigger_source(0,'trigsrcNone')
            self.set_laser_controller()
            self.dig.start_stop_analogout(0,True)
            self.settings.child('laser_settings', 'laser_ready').setValue(True)
        else:
            self.settings.child('laser_settings', 'laser_ready').setValue(False)


        ## create process data thread
        process_object=DAQ_Process_data(self.settings.saveState())
        self.process_thread=QThread()
        process_object.moveToThread(self.process_thread)

        self.process_data_sig[OrderedDict].connect(process_object.update_data)
        process_object.data_signal[dict].connect(self.update_plot_process)
        process_object.status_sig[list].connect(self.thread_status)
        self.update_settings_signal[edict].connect(process_object.update_settings)
        self.process_thread.process_object=process_object
        self.process_thread.start()

        self.settings.child('laser_settings','stokes_shift').setValue(100)

    def set_laser_controller(self):
        """
          | Set the voltage node value and the laser frequency.
          | Configure the analog output pin with computed values and emit the 1/0 analog out signal.

        """
        self.dig.set_channel_node_value(0,1,self.settings.child('laser_settings','attenuation').value()) #set the voltage node
        freq=self.settings.child('laser_settings','laser_rep_rate').value()*1000
        self.dig.configure_analog_output(channel=0,function=dg.Digilent_FUNC(2).name,enable=True,frequency=freq,amplitude=2.5,offset=2.5)
        self.dig.start_stop_analogout(0,True)

    @pyqtSlot(OrderedDict)
    def send_data(self,datas):
        """
            Send the given data via the process_data_sig signal

            =============== ============================== ============================
            **Parameters**   **Type**                       **Description**

             *datas*         double precision float array   The raw datas to be sended
            =============== ============================== ============================

        """
        self.process_data_sig.emit(datas)

    def create_menu(self,menubar):
        """
            Set the filemenu structure with 6 elements into 2 submenus :
                * **Load data** : call the load_data method in three case with filetype parameter corresponding:
                    * DAQType(.dat file)
                    * DAQType(.h5 file)
                    * Sensornet Type(.ddf file)
                * **Save data** : call the save_current method in two case with filetype parameter corresponding:
                    * *Export as ascii* (.txt file)
                    * *Save data* (.h5 file)
                * **Show/Hide log window** : set Visible the dock logger

            =============== ====================== ======================================
            **Parameters**   **Type**               **Description**

             *menubar*       instance of QMenuBar   The generic menubar object of menu
            =============== ====================== ======================================

            See Also
            --------
            load_data, save_current
        """
        menubar.clear()

        #%% create Settings menu
        file_menu=menubar.addMenu('File')
        load_menu=file_menu.addMenu('Load Data')
        action_load_dat=load_menu.addAction('PyMoDAQ Type (.dat)')
        action_load_h5=load_menu.addAction('PyMoDAQ Type (.h5)')
        action_load_ddf=load_menu.addAction('Sensornet type (.ddf)')

        save_menu=file_menu.addMenu('Save Data')
        action_save_txt=save_menu.addAction('Export as ascii (.dat)')
        action_save_h5=save_menu.addAction('Save Data (.h5)')

        action_load_dat.triggered.connect(lambda: self.load_data(file_type="dat"))
        action_load_h5.triggered.connect(lambda:self.load_data(file_type="h5"))
        action_load_ddf.triggered.connect(lambda:self.load_data(file_type="ddf"))

        action_save_txt.triggered.connect(lambda:self.save_current(file_type='dat'))
        action_save_h5.triggered.connect(lambda:self.save_current(file_type='h5'))

        action_show_log=file_menu.addAction('Show/hide log window')
        action_show_log.setCheckable(True)
        action_show_log.toggled.connect(self.dock_logger.setVisible)


    def save_current(self,file_type='h5'):
        """
            | Save the current data in an external file wich could be loaded later (or analysed with DAQ_Analysis in case of .h5 file).
            | The path is given by the select_file method (imported from DAQ_Utils).

            =============== ========== =================================================================================
            **Parameters**   **Type**   **Description**

            *filetype*        string     Specify the filetype to store between .dat file and .h5 file (.h5 by default)
            =============== ========== =================================================================================

            See Also
            --------
            DAQ_utils.select_file, save_datas
        """
        self.do_save_data=True
        self.save_file_pathname=str(DAQ_utils.select_file(self.save_file_pathname,save=True, ext=file_type)) #see DAQ_utils
        self.save_datas(self.save_file_pathname,self.data_to_save_export,file_type=file_type)



    def save_datas(self,filepathname,datas,file_type='h5'):
        """
            | Store the given datas into the file specified by his access (given by the file pathname argument) and his type (given by file_type argument).
            | Each file have a header including date.

            ================ =============================== ==============================================================================================
            **Parameters**     **Type**                       **Descritpion**

             *filepathname*     string                         Specify the path of the file to be saved

             *datas*            double precision float array   Raw values data to be stored

             *file_type*        string                         Specify the filetype to store between .dat file, .h5 file and .dtt file (.h5 by default)
            ================ =============================== ==============================================================================================

            See Also
            --------
            DAQ_Utils.custom_parameter_tree.parameter_to_xml_string, update_status
        """
        try:
            self.settings.child('main_settings','filename').setValue(filepathname)
            date=QDateTime.currentDateTime().toString()

            if file_type=='dat':
                data_array=np.array(datas['x_axis'])
                header="#"+date+"\n"
                data_to_save=[]
                for ind,key in enumerate(datas):
                    header=header+"\t"+key
                    data_to_save.append(np.array(datas[key]))

                data_array=np.stack(data_to_save,axis=1)
                np.savetxt(filepathname,data_array,fmt='%.6e',delimiter='\t',header=header,comments='')

            elif file_type=='h5':
                h5file=tables.open_file(filepathname,mode='w')
                h5file.root._v_attrs['date']=date
                h5file.root._v_attrs['settings']=custom_tree.parameter_to_xml_string(self.settings)
                h5file.root._v_attrs['detector_settings']=custom_tree.parameter_to_xml_string(self.detector_module.settings)
                for ind,key in enumerate(datas):
                    h5file.create_array('/',key,datas[key])
                h5file.close()


            (root,filename)=os.path.split(filepathname)
            filename,ext=os.path.splitext(filename)
            image_path=os.path.join(root,filename+'.png')
            self.mainwindow.grab().save(image_path);
        except Exception as e:
            self.update_status(str(e),self.wait_time,log_type='log')

    def load_data(self,file_type='dat'):
        """
            Load data from the select_file method (imported from DAQ_Utils).

            In case of :

            * **.dat file** : the datas are stored in the User Interface viewer x_axis with update of show-data.
            * **.ddf file** : the datas are treated as a tree, stored in settings, and synchronously in the User Interface viewer x_axis updating show_data.
            * **.h5 file** : the h5 tree is readed node by node and stored into the User Interface viewer x_axis updating show_data.

            =============== ========== ==========================================================================================
            **Parameters**   **Type**   **Description**

            *file_type*       string    Specify the filetype to load between .dat file, .h5 file and .ddf file (.dat by default)
            =============== ========== ==========================================================================================

            See Also
            --------
            DAQ_utils.select_file, DAQ_Utils.custom_parameter_tree.XML_string_to_parameter, update_status
        """
        try:
            self.data_to_save_export=OrderedDict([])
            filename=str(DAQ_utils.select_file(self.save_file_pathname,save=False, ext=file_type)) #see DAQ_utils
            self.settings.child('main_settings','filename').setValue(filename)
            if file_type=='dat':
                data=np.loadtxt(filename)
                datas=OrderedDict(time_axis=data[:,0],data_S=data[:,2],data_AS=data[:,3],temparature=data[:,2])
                self.data_to_save_export.update(datas)

                self.detector_module.ui.viewer.x_axis=data[:,0]
                self.detector_module.show_data([data[:,1],data[:,2]])

            elif file_type=='ddf':
                file=open(filename)
                p = re.compile('(\S+)')
                for ind_line,line in enumerate(file):
                    if ind_line==9:
                        self.settings.child('main_settings','date').setValue(p.findall(line)[-1])
                    elif ind_line==13:
                        self.settings.child('temperature','constants','gamma').setValue(float(p.findall(line)[-1].replace(',','.')))
                    elif ind_line==14:
                        self.settings.child('temperature','constants','amplification').setValue(float(p.findall(line)[-1].replace(',','.')))
                    elif ind_line==16:
                        self.settings.child('temperature','constants','offset').setValue(float(p.findall(line)[-1].replace(',','.')))
                    elif ind_line==17:
                        self.settings.child('temperature','constants','loss').setValue(float(p.findall(line)[-1].replace(',','.')))
                    elif ind_line==18:
                        self.settings.child('temperature','constants','slope').setValue(float(p.findall(line)[-1].replace(',','.')))
                    elif ind_line==19:
                        break
                file.close()
                s=pd.read_table(filename,decimal=',',header=26)
                data=s.values

                group_index_fiber_R=1.4626# at 1550nm
                length_axis=data[:,0]
                time_axis=2*length_axis/(self.c/group_index_fiber_R)

                datas=OrderedDict(time_axis=time_axis,length_axis=length_axis,data_S=data[:,2],data_AS=data[:,3],data_S_raw=data[:,2],data_AS_raw=data[:,3])
                self.data_to_save_export.update(datas)
                #try:
                #    self.settings.sigTreeStateChanged.disconnect(self.parameter_tree_changed)#any changes on the settings will update accordingly the detector
                #except: pass
                self.settings.child('analysis','do_fft').setValue(False)
                self.settings.child('temperature','process_temperature').setValue(True)
                self.settings.child('temperature','get_temp_from').setValue('constants')
                #self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)#any changes on the settings will update accordingly the detector

                #self.update_plot_process(datas)
                self.detector_module.ui.viewer.x_axis=time_axis
                self.detector_module.show_data([data[:,2],data[:,3]])

            elif file_type=='h5':
                h5file=tables.open_file(filename,mode='r')
                children=h5file.root._f_list_nodes()
                datas=OrderedDict([])
                for child in children:
                    datas[child.name]=child.read()
                self.data_to_save_export.update(datas)
                params_list=custom_tree.XML_string_to_parameter(h5file.root._v_attrs['settings'])
                params=Parameter.create(title='Preset', name='Preset', type='group', children=params_list )
                self.settings.restoreState(params.saveState(filter = 'user'))
                self.detector_module.ui.viewer.x_axis=datas['time_axis']
                self.detector_module.show_data([datas['data_S_raw'],datas['data_AS_raw']])



        except Exception as e:
            self.update_status(str(e),self.wait_time,log_type='log')

    def update_calibration_regions(self):
        """
            Foreach region of the fftviewer, child are created with calibration values (temperature, distance and zone)
        """
        for ind_region,region in enumerate(self.fft_viewer.linear_regions):
            zone=region.getRegion()
            self.settings.child('temperature','distances','zone{:d}'.format(ind_region+1),'x1').setValue(zone[0])
            self.settings.child('temperature','distances','zone{:d}'.format(ind_region+1),'x2').setValue(zone[1])



    @pyqtSlot(OrderedDict)
    def update_plot_process(self,data):
        """
            Update data_to_save_export and in case of :
                * **raw analysis**       : Update the x_axis with time data in s ans show in the fft viewer
                * **FFT analysis**       : Update the x_axis with FFT frequency data in Hz and show in fft viewer
                * **average analysis**   : Update x_axis with length data in m and show in fft viewer
                * **temperature values** : Process the temperature

            =============== ============================== ============================
            **Parameters**  **Type**                        **Description**

             *data*          double precision float array   Data to be saved/exported
            =============== ============================== ============================

            See Also
            --------
            process_temperature, update_status
        """
        try:

            self.data_to_save_export.update(data)
            #data=dict(time_axis=self.time_axis,length_axis=position_AS,fft_axis=self.omega_grid/(2*np.pi)*1000,data_AS=self.data_AS_out,data_S=self.data_S_out,data_AS_raw=self.data_AS,data_S_raw=self.data_S,data_AS_fft=np.abs(data_AS_fft),data_S_fft=np.abs(data_S_fft))


            if self.settings.child('analysis','show_analysis').value()=='raw':
                self.fft_viewer.set_axis_label(axis_settings=dict(orientation='bottom',label='Time',units='s'))
                self.fft_viewer.x_axis=self.data_to_save_export['time_axis']
                self.fft_viewer.show_data([self.data_to_save_export['data_S_raw'],self.data_to_save_export['data_AS_raw']])

            if self.settings.child('analysis','show_analysis').value()=='FFT': # send fft
                self.fft_viewer.set_axis_label(axis_settings=dict(orientation='bottom',label='Frequency',units='Hz'))
                self.fft_viewer.x_axis=self.data_to_save_export['fft_axis']
                self.fft_viewer.show_data([self.data_to_save_export['data_S_fft'],self.data_to_save_export['data_AS_fft']])

            elif self.settings.child('analysis','show_analysis').value()=='average':#means average data
                self.fft_viewer.set_axis_label(axis_settings=dict(orientation='bottom',label='Distance',units='m'))
                self.fft_viewer.x_axis=self.data_to_save_export['length_axis']
                self.fft_viewer.show_data([self.data_to_save_export['data_S'],self.data_to_save_export['data_AS']])


            if self.settings.child('temperature','process_temperature').value():
                self.process_temperature()

        except Exception as e:
            self.update_status(str(e),self.wait_time,log_type='log')

    def process_temperature(self):
        """
            Start constants temperature process if temperature is constants or calibrate them else

            See Also
            --------
            process_temperature_constants, process_temperature_calibration
        """
        if self.settings.child('temperature','get_temp_from').value()== 'constants':
           self.process_temperature_constants()
        else:
            self.process_temperature_calibration()

    def process_temperature_constants(self):
        """
            | Update gamma, offset, loss, slope and amplification from settings tree and data AS/S and x_axis from data_to_save_export.
            | Update data temperature value from newest values of gamma, offset, loss, slope and amplification.
            | Temperature calculation is given by :
            |
            |      **gamma/(log(offset/(ratio*amp*exp(slope*loss*x_axis))))-273.15**
            |
            | Update the x_axis of temperature viewer and show data obtained in temperature viewer


            See Also
            --------
            update_status
        """
        try:
            if self.settings.child('temperature','process_temperature').value():
                gamma=self.settings.child('temperature','constants','gamma').value()
                offset=self.settings.child('temperature','constants','offset').value()
                loss=self.settings.child('temperature','constants','loss').value()*1e-3
                slope=self.settings.child('temperature','constants','slope').value()
                amplification=self.settings.child('temperature','constants','amplification').value()

                data_AS=self.data_to_save_export['data_AS']
                data_S=self.data_to_save_export['data_S']
                x_axis=self.data_to_save_export['length_axis']
                data_AS[data_AS<0]=0
                data_S[data_S<0]=0

                ratio=data_AS/data_S

                self.data_temperature=gamma/(np.log(offset/(ratio*amplification*np.exp(slope*loss*x_axis))))-273.15
                self.temperature_viewer.x_axis=x_axis
                self.temperature_viewer.show_data([self.data_temperature])
                self.data_to_save_export['data_temperature']=self.data_temperature
        except Exception as e:
            self.update_status(str(e),self.wait_time,log_type='log')

    def process_temperature_calibration(self):
        """
            | Compute Xbar from Abar and Bbar.
            | Abar index is found from settings tree indexes, Bbar index is found from log of (the mean of data-S divided by data-AS)
            | The Xbar value is used to update data temperature, once done show data obtained in temperature viewer and update data_to_save_export attribute.

            See Also
            --------
            update_status
        """

        if self.settings.child('temperature','process_temperature').value():
            try:
                zone1=[self.settings.child('temperature','distances','zone1','x1').value(),self.settings.child('temperature','distances','zone1','x2').value()]
                zone2=[self.settings.child('temperature','distances','zone2','x1').value(),self.settings.child('temperature','distances','zone2','x2').value()]
                zone3=[self.settings.child('temperature','distances','zone3','x1').value(),self.settings.child('temperature','distances','zone3','x2').value()]

                x_axis=self.data_to_save_export['length_axis']
                indexes1=mylib.find_index(x_axis,zone1)
                indexes2=mylib.find_index(x_axis,zone2)
                indexes3=mylib.find_index(x_axis,zone3)
                data_AS=self.data_to_save_export['data_AS']
                data_S=self.data_to_save_export['data_S']

                data_AS[data_AS<0]=0
                data_S[data_S<0]=0
                ratio_cal_1=np.log(np.mean(data_S_out[indexes1[0][0]:indexes1[1][0]])/np.mean(data_AS[indexes1[0][0]:indexes1[1][0]]))
                ratio_cal_2=np.log(np.mean(data_S_out[indexes2[0][0]:indexes2[1][0]])/np.mean(data_AS[indexes2[0][0]:indexes2[1][0]]))
                ratio_cal_3=np.log(np.mean(data_S_out[indexes3[0][0]:indexes3[1][0]])/np.mean(data_AS[indexes3[0][0]:indexes3[1][0]]))


                z1=(indexes1[0][1]+indexes1[1][1])/2
                z2=(indexes2[0][1]+indexes2[1][1])/2
                z3=(indexes3[0][1]+indexes3[1][1])/2

                T1=self.settings.child('temperature','temperatures','T1').value()+273
                T2=self.settings.child('temperature','temperatures','T2').value()+273
                T3=self.settings.child('temperature','temperatures','T3').value()+273

                Abar=np.array([[1,-T1,T1*z1],[1,-T2,T2*z2],[1,-T3,T3*z3]])
                Bbar=np.array([T1*ratio_cal_1,T2*ratio_cal_2,T3*ratio_cal_3])
                Xbar = np.linalg.solve(Abar,Bbar)

                self.data_temperature=Xbar[0]/(np.log(data_S/data_AS)+Xbar[1]-Xbar[2]*x_axis*1)-273

                self.temperature_viewer.x_axis=x_axis
                self.temperature_viewer.show_data([self.data_temperature])
                self.data_to_save_export['data_temperature']=self.data_temperature


            except Exception as e:
                self.update_status(str(e),self.wait_time,log_type='log')



    @pyqtSlot(str)
    def add_log(self,txt):
        """
            Add a log to the logger list from the givven text log and the current time

            ================ ========= ======================
            **Parameters**   **Type**   **Description**

             *txt*             string    the log to be added
            ================ ========= ======================

        """
        now=datetime.datetime.now()
        new_item=QtWidgets.QListWidgetItem(str(now)+": "+txt)
        self.logger_list.addItem(new_item)
        ##to do
        ##self.save_parameters.logger_array.append(str(now)+": "+txt)

    @pyqtSlot(str)
    def emit_log(self,txt):
        """
            Emit a log-signal from the given log index

            =============== ======== =======================
            **Parameters**  **Type** **Description**

             *txt*           string   the log to be emitted
            =============== ======== =======================

        """
        self.log_signal.emit(txt)

    def update_status(self,txt,wait_time=0,log_type=None):
        """
            Update the status of the detector module from the given log index with a delay of wait_time ms if specified (no delay by default)

            ================ ======== ========================================
            **Parameters**

             *txt*            string    the log index to be updated

             *wait_time*      int       delay time of update procedure in ms

             *log_type*       string    type of the log
            ================ ======== ========================================

            See Also
            --------
            update_status
        """
        try:
            self.detector_module.update_status(txt,wait_time=wait_time,log_type=log_type)
        except Exception as e:
            pass

    def quit_fun(self):
        """
            Close the current instance of DAQ_Metheor with modules on cascades
        """

        self.dig.set_master_state(False)
        self.dig.close_device()


        for area in self.dockarea.tempAreas:
            area.win.close()

        if hasattr(self,'mainwindow'):
            self.mainwindow.close()
        self.dockarea.parent().close()


    def parameter_tree_changed(self,param,changes):
        """
            Check the changes in parameters, cahnges and data array and in case of value (change is active) :
                * **laser response rate** : do the laser controller setting if specified in the current childPath
                * **analysis**            : do analysis grabbing done the signal
                * **temperature**         : process temperature and show data
                * **laser wavelength**    : calculate gamma for laser wavelength

            ================ ======================================== =====================================================
            **Parameters**    **Type**                                 **Description**

             *param*           instance of pyqtgraph Parameter         the parameter to be checked

             *changes*        (parameters, changes, data) tuple list   (parameters, changes, data) array to be checked
            ================ ======================================== =====================================================

            See Also
            --------
            set_laser_controller,send_data, process_temperature, calculate_gamma
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

                if 'attenuation' in path or 'laser_rep_rate' in path:
                    self.set_laser_controller()

                elif 'do_analysis' in path:
                    if param.value():
                        self.detector_module.grab_done_signal[OrderedDict].connect(self.send_data)
                    else:
                        self.detector_module.grab_done_signal.disconnect(self.send_data)

                elif 'temperature' in path:
                    if self.settings.child('temperature','process_temperature').value():
                        if self.settings.child('temperature','get_temp_from').value()=='calibration':
                            self.settings.child('temperature','temperatures').show()
                            self.settings.child('temperature','distances').show()
                            self.settings.child('temperature','constants').hide()

                            for region in self.fft_viewer.linear_regions:
                                region.show()
                        else:
                            for region in self.fft_viewer.linear_regions:
                                region.hide()
                            self.settings.child('temperature','temperatures').hide()
                            self.settings.child('temperature','distances').hide()
                            self.settings.child('temperature','constants').show()
                        self.process_temperature()
                    else:
                        for region in self.fft_viewer.linear_regions:
                            region.hide()
                elif 'laser_wavelength' in path or 'stokes_shift' in path:
                    self.calculate_gamma()

                self.update_settings_signal.emit(edict(path=path,param=param))


            elif change == 'parent':
                pass

    def calculate_gamma(self):
        """
            | Compute calculation of gamma given by :
            |

            | **h*c*dlambda/(lambda0**(2kb))**
            |

            where :
                * **h**       = 6.6260693E-34
                * **kb**      = 1.3806505E-23
                * **dlambda** = (strokes shift of laser)E-9
                * **lambda0** = (laser wavelength)E-9
                * **c**       = 3E8 m/s

            Once done, update temperature gamma with value

        """
        h=6.6260693e-34
        kb=1.3806505e-23
        lambda0=self.settings.child('laser_settings','laser_wavelength').value()*1e-9
        dlambda=self.settings.child('laser_settings','stokes_shift').value()*1e-9
        gamma=h*self.c*dlambda/(lambda0**2*kb)
        self.settings.child('temperature','constants','gamma').setValue(gamma)



    @pyqtSlot(list)
    def thread_status(self,status):
        """
        | General function to get datas/infos from all threads back to the main.
        | In case of update state, update status from argument

        =============== ============ ====================================
        **Parameters**   **Type**     **Description**

         *status*        string list   the statut states array to treate
        =============== ============ ====================================

        See Also
        --------
        update_status
        """
        # general function to get datas/infos from all threads back to the main
        if status[0]=="Update_Status":
            self.update_status(status[1],wait_time=self.wait_time,log_type=status[2])

class DAQ_Process_data(QObject):
    """
        =======================   ================================
        **Attributes**               **Type**

         *data_signal*            instance of pyqtSignal
         *status_sig*             instance of pyqtSignal
         *params*                 list
         *settings*               instance of pyqtgraph.parameter
         *Npts*                   int
         *data_AS*                int array
         *time_axis*              int array
         *omega_grid*             float array
         *time_grid*              float array
         *c*                      float
         *group_index_fiber_R*    float
         *group_index_fiber_AS*   float
         *group_index_fiber_S*    float
        =======================   ================================

        See Also
        --------
        send_param_status

        References
        ----------
        QObject, pyqtSignal

    """
    data_signal=pyqtSignal(OrderedDict)
    status_sig = pyqtSignal(list)
    params= []

    def __init__(self,params_state=None):
        """
        """
        super(DAQ_Process_data,self).__init__()
        self.settings=Parameter.create(name='Settings', type='group', children=self.params)
        if params_state is not None:
            self.settings.restoreState(params_state)
        self.settings.sigTreeStateChanged.connect(self.send_param_status)

        ##self.dl_min=100
        self.Npts=1
        ##self.threshold=0
        ##self.gaussian_order=1
        self.data_AS=np.array([0])
        self.data_S=np.array([0])
        self.time_axis=np.array([0])
        self.omega_grid=None
        self.time_grid=None
        self.c=3e8
        ##self.data_type=0
        ###self.temperature_parameters=dict(do_temp=...,temp_region_1=...,temp_region_2=...,temp_region_3=...,temp1=...,temp2=...,temp3=...)
        ##self.temperature_parameters=dict(do_temp=False)
        self.group_index_fiber_R=1.4626# at 1550nm
        self.group_index_fiber_AS=1.4620# at 1450nm
        self.group_index_fiber_S=1.4633# at 1650nm



    def emit_status(self,status):
        """
            Emit the status signal from the given array

            =============== ====== ======================================
            **Parameters**

             *status*        list   the statuts state list to be emitted
            =============== ====== ======================================

        """
        self.status_sig.emit(status)


    @pyqtSlot(edict)
    def update_settings(self,settings_parameter_dict):
        """
            Disconect the Tree State Changed signal if possible and upgrade settings Tree with Dictionnary values.

            ======================= ============ ======================================
            **Parameters**            **Type**      **Description**

            settings_parameter_dict  dictionnary  Dictionnary of parameters from paths
            ======================= ============ ======================================

            See Also
            --------
            send_param_status, commit_settings
        """
        path=settings_parameter_dict.path
        param=settings_parameter_dict.param
        try:
            self.settings.sigTreeStateChanged.disconnect(self.send_param_status)
        except: pass
        self.settings.child(*path[0:]).setValue(param.value())

        self.settings.sigTreeStateChanged.connect(self.send_param_status)

        self.commit_settings(param)

    def commit_settings(self,param):
        """
            Update fiberR,AS and S indexes in case of laser wavelength.

            =============== ================================ ==============================
            **Parameters**   **Type**                         **Description**

            *param*          instance of pyqtgraph parameter  The parameter to be commited
            =============== ================================ ==============================

            See Also
            --------
            process_data

        """
        if param.name()=='laser_wavelength':
            self.group_index_fiber_R=1.4626# at 1550nm
            self.group_index_fiber_AS=1.4620# at 1450nm
            self.group_index_fiber_S=1.4633# at 1650nm

            pass #to do: recalculate the group indexes
        self.process_data()

    def send_param_status(self,param,changes):
        """
            Send the status signal contening changes array in case of value or limits change statut.

            =============== ===================================  ==================================================
            **Parameters**   **Type**                             **Description**

             *param*         instance of pyqtgraph parameter      The parameter to be checked

             *changes*       tuple list                           The [parameter, change, data] array to be sended
            =============== ===================================  ==================================================

        """

        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':
                pass

            elif change == 'value' or change == 'limits':
                self.emit_status(['update_settings',path,data,change]) #parent is the main detector object and status_sig will be send to the GUI thrad
            elif change == 'parent':
                pass




    @pyqtSlot(list)
    def process_cmd(self,status):
        """
            Update data or parameters in case of.

            =============== ============== ===========================================
            **Parameters**   **Type**       **Description**

             *status*        string array   Containing the command name to be executed
            =============== ============== ===========================================

            See Also
            --------
            update_data

        """
        if status[0]=='update_data':
            self.update_data(status[1])
        elif status[0]=='update_parameters':
            self.update_parameters(status[1])

    @pyqtSlot(OrderedDict)
    def update_data(self,data):
        """
            Update data AS/S and time axis from given data and create the corresponding FFT axis.

            =============== ============================== ================================
            **Parameters**   **Type**                       **Description**

             *data*          double precision float array   Raw values array to be treated
            =============== ============================== ================================

            See Also
            --------
            create_FFT_axis, process_data, emit_status
        """
        try:
            self.data_AS=data['data1D']['CH001']['data']
            self.data_S=data['data1D']['CH000']['data']
            self.Npts=len(self.data_AS)
            self.time_axis=data['data1D']['CH000']['x_axis']
            self.create_FFT_axis()


            self.process_data()
        except Exception as e:
            self.emit_status(['Update_Status',str(e),'log'])

    def create_FFT_axis(self):
        """
            Create the FFT axis from time_axis attribute
        """
        time_window=(max(self.time_axis)-min(self.time_axis))*1e-3 # in s
        (self.omega_grid,self.time_grid)=mylib.ftAxis_time(len(self.time_axis),time_window)

    def process_data(self):
        try:

            if self.settings.child('analysis','do_fft').value():
                gaussian_order=self.settings.child('analysis','gaussian_order').value() #
                frep=self.settings.child('laser_settings','laser_rep_rate').value()*1e3 # laser repetition rate frequency in Hz
                dl_min=self.settings.child('analysis','fft_resolution').value()

                dl_min_rising_edge=100# m of fiber length
                dt_min=2*dl_min_rising_edge/self.c #fastest feature
                domega_max=2*np.pi/dt_min

                data_AS_fft=mylib.ft(self.data_AS)
                gate_omega=(mylib.gauss1D(self.omega_grid,2*np.pi*frep,2*domega_max,gaussian_order))

                data_AS_filtered_rising_edge=np.real(mylib.ift(data_AS_fft*gate_omega))
                self.threshold=(np.max(data_AS_filtered_rising_edge)+np.min(data_AS_filtered_rising_edge))/2
                data_shifted=np.concatenate((data_AS_filtered_rising_edge[1:],np.array([np.NaN])))
                dat=np.bitwise_and(data_AS_filtered_rising_edge<self.threshold, data_shifted>self.threshold)
                ind_rising_edge=[ind for ind,flag in enumerate(dat) if flag]

                if len(ind_rising_edge)!=0:
                    dt_min=2*dl_min/self.c #fastest feature
                    domega_max=2*np.pi/dt_min
                    gate_omega=(mylib.gauss1D(self.omega_grid,2*np.pi*frep,2*domega_max,gaussian_order))
                    data_AS_fft=mylib.ft(self.data_AS)*gate_omega
                    data_S_fft=mylib.ft(self.data_S)*gate_omega
                    data_AS_filtered=np.real(mylib.ift(data_AS_fft))
                    data_S_filtered=np.real(mylib.ift(data_S_fft))




                    Nperiod=len(ind_rising_edge)#2 stands because light is going back and forth
                    Ndata_mean=np.int(self.Npts/Nperiod)


                    data_AS_mean_filtered=np.zeros((Ndata_mean,Nperiod))
                    data_S_mean_filtered=np.zeros((Ndata_mean,Nperiod))

                    for ind_N in range(len(ind_rising_edge)):
                        try:
                            data_AS_mean_filtered[:,ind_N]=data_AS_filtered[ind_rising_edge[ind_N]-min(ind_rising_edge):ind_rising_edge[ind_N]-min(ind_rising_edge)+Ndata_mean]
                            data_S_mean_filtered[:,ind_N]=data_S_filtered[ind_rising_edge[ind_N]-min(ind_rising_edge):ind_rising_edge[ind_N]-min(ind_rising_edge)+Ndata_mean]
                        except:
                            break

                    data_AS_out=np.mean(data_AS_mean_filtered,1)

                    data_S_out=np.mean(data_S_mean_filtered,1)

                    time_axis_out=self.time_axis[0:Ndata_mean]
                    position_AS=self.c/self.group_index_fiber_AS*time_axis_out*1e-3/2
                    position_S=self.c/self.group_index_fiber_S*time_axis_out*1e-3/2
                else:
                    raise Exception("Threshold value is not adapted")

                data_out=OrderedDict(time_axis=self.time_axis,length_axis=position_AS,fft_axis=self.omega_grid/(2*np.pi)*1000,data_AS=data_AS_out,data_S=data_S_out,data_AS_raw=self.data_AS,data_S_raw=self.data_S,data_AS_fft=np.abs(data_AS_fft),data_S_fft=np.abs(data_S_fft))

                self.data_signal.emit(data_out)
            else:
                length_axis=self.c/self.group_index_fiber_AS*self.time_axis*1e-3/2
                data_out=OrderedDict(time_axis=self.time_axis,length_axis=length_axis,data_AS=self.data_AS,data_S=self.data_S,data_AS_raw=self.data_AS,data_S_raw=self.data_S)

                self.data_signal.emit(data_out)



        except Exception as e:
            self.status_sig.emit(['update_status',str(e),'log'])



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow();fname="";
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000,500)
    win.setWindowTitle('PyMoDAQ Metheor')
    prog = DAQ_Metheor(area,fname)
    win.show()
    sys.exit(app.exec_())

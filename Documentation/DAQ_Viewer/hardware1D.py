from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize
from PyMoDAQ.DAQ_Viewer.utility_classes import DAQ_Viewer_base
import numpy as np
from easydict import EasyDict as edict
from enum import Enum, IntEnum, EnumMeta
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import PyMoDAQ.DAQ_Utils.custom_parameter_tree
from PyMoDAQ.DAQ_Utils.python_lib.mathematics.mat_functions import gauss1D
import PyMoDAQ.DAQ_Utils.hardware.picoscope.picoscope_5000A as picoscope
from bitstring import BitArray
from PyMoDAQ.DAQ_Utils.DAQ_utils import ThreadCommand

class DAQ_1DViewer_Det_type(IntEnum):
    """
        Enum class of Det Type.

        =============== ===============
        **Attributes**   **Type**
        *Mock*           int
        *Picoscope*      int
        *names*          string list
        =============== ===============
    """
    Mock=0
    Picoscope=1
    @classmethod
    def names(cls):
        names=cls.__members__.items()
        return [name for name, member in cls.__members__.items()]



class DAQ_1DViewer_Mock(DAQ_Viewer_base):
    """
        ==================== ==================
        **Atrributes**        **Type**
        *params*              dictionnary list
        *hardware_averaging*  boolean
        *x_axis*              1D numpy array      
        *ind_data*            int
        ==================== ==================

        See Also
        --------
        utility_classes.DAQ_Viewer_base
    """
    params= [{'name': 'Mock1', 'type': 'group', 'children':[
                {'name': 'Npts', 'type': 'int', 'value': 200 , 'default':200, 'min':10},
                {'name': 'Amp', 'type': 'int', 'value': 20 , 'default':20, 'min':1},
                {'name': 'x0', 'type': 'float', 'value': 50 , 'default':50, 'min':0},
                {'name': 'dx', 'type': 'float', 'value': 20 , 'default':20, 'min':1},
                {'name': 'n', 'type': 'float', 'value': 1 , 'default':1, 'min':1},
                {'name': 'amp_noise', 'type': 'float', 'value': 0.1 , 'default':0.1, 'min':0}
                ]},
             {'name': 'Mock2', 'type': 'group', 'children':[
                    {'name': 'Npts', 'type': 'int', 'value': 200 , 'default':200, 'min':10},
                    {'name': 'Amp', 'type': 'int', 'value': 10 , 'default':10, 'min':1},
                    {'name': 'x0', 'type': 'float', 'value': 100 , 'default':100, 'min':0},
                    {'name': 'dx', 'type': 'float', 'value': 30 , 'default':30, 'min':1},
                    {'name': 'n', 'type': 'float', 'value': 2 , 'default':2, 'min':1},
                    {'name': 'amp_noise', 'type': 'float', 'value': 0.1 , 'default':0.1, 'min':0}
                ]}]
    hardware_averaging=False

    def __init__(self,parent=None,params_state=None): #init_params is a list of tuple where each tuple contains info on a 1D channel (Ntps,amplitude, width, position and noise)
        super(DAQ_1DViewer_Mock,self).__init__(parent,params_state)


        self.x_axis=None
        self.ind_data=0


    def commit_settings(self,param):
        """
            Setting the mock data

            ============== ========= =================
            **Parameters**  **Type**  **Description**
            *param*         none      not used
            ============== ========= =================

            See Also
            --------
            set_Mock_data
        """
        self.set_Mock_data()    
               
                
    def set_Mock_data(self):
        """
            For each parameter of the settings tree :
                * compute linspace numpy distribution with local parameters values
                * shift right the current data of ind_data position
                * add computed results to the data_mock list 

            Returns
            -------
            list
                The computed data_mock list.
        """
        self.data_mock=[]
        for param in self.settings.children():
            self.x_axis=np.linspace(0,param.children()[0].value()-1,param.children()[0].value())
            data_tmp=param.children()[1].value()*gauss1D(self.x_axis,param.children()[2].value(),param.children()[3].value(),param.children()[4].value())+param.children()[5].value()*np.random.rand((param.children()[0].value()))
            data_tmp=np.roll(data_tmp,self.ind_data)
            self.data_mock.append(data_tmp)
        self.ind_data+=1
        return self.data_mock

    def Ini_Detector(self):
        """
            Initialisation procedure of the detector updating the status dictionnary.

            See Also
            --------
            set_Mock_data, DAQ_utils.ThreadCommand
        """
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None))
        try:
            self.set_Mock_data()
            self.status.initialized=True
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
            self.status.info=str(e)
            self.status.initialized=False
            return self.status

    def Close(self):
        """
            Not implemented.
        """
        pass




    def Grab(self,Naverage=1):
        """
            | Start new acquisition
            | 

            For each integer step of naverage range:
                * set mock data
                * wait 100 ms
                * update the data_tot array

            | 
            | Send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       Number of spectrum to average.
                                      Specify the threshold of the mean calculation
            =============== ======== ===============================================

            See Also
            --------
            set_Mock_data
        """
        Naverage=1
        data_tot=self.set_Mock_data()
        for ind in range(Naverage-1):
            data_tmp=self.set_Mock_data()
            QThread.msleep(100)

            for ind,data in enumerate(data_tmp):
                data_tot[ind]+=data

        data_tot=[data/Naverage for data in data_tot]

        self.data_grabed_signal.emit(data_tot)

    def Stop(self):
        """
            not implemented.
        """
        
        return ""


class DAQ_1DViewer_Picoscope(DAQ_Viewer_base):
    """
        ==================== ==============================
        **Attributes**        **Type**
        *hardware_averaging*  boolean
        *params*              dictionnary list
        *pico*                instance of Picoscope_5000A
        *x_axis*              1D numpy array
        *Nsample_available*   int
        *buffers*             generic list
        ==================== ==============================

        See Also
        --------
        utility_classes.DAQ_Viewer_base
    """
    hardware_averaging=False
    params= [{'title': 'Main Settings:','name': 'main_settings', 'type': 'group', 'children':[
                {'title': 'Dynamic:','name': 'dynamic', 'type': 'list', 'values': picoscope.DAQ_Picoscope_dynamic.names()},
                {'title': 'N segments:','name': 'Nsegments', 'type': 'int', 'value': 1 , 'default': 1},
                {'title': 'Temporal:','name': 'temporal', 'type': 'group', 'children':[
                    {'title': 'Window (ms):','name': 'window', 'type': 'float', 'value': 100 , 'default': 100},
                    {'title': 'N samples:','name': 'Nsamples', 'type': 'int', 'value': 1000 , 'default': 1000},
                    {'title': 'Resolution (ms):','name': 'resolution', 'type': 'float', 'value': 0 , 'readonly':True},
                    ]},
                
                {'title': 'Trigger:','name': 'trigger', 'type': 'group', 'children':[
                    {'title': 'Enable trigger:','name': 'trig_enabled', 'type': 'bool','value': True},
                    {'title': 'Channel:','name': 'trig_channel', 'type': 'list','values': picoscope.DAQ_Picoscope_trigger_channel.names()},
                    {'title': 'Type:','name': 'trig_type', 'type': 'list', 'value': 'Rising', 'values': picoscope.DAQ_Picoscope_trigger_type.names()},
                    {'title': 'Level (V):','name': 'trig_level', 'type': 'float', 'value': 0, 'suffix': 'V'},
                    {'title': 'Pretrigger (%):','name': 'trig_pretrigger', 'type': 'int', 'value': 50, 'suffix': '%'},
                    {'title': 'Trigger delay (ms):','name': 'trig_delay', 'type': 'float', 'value': 0},
                    {'title': 'Autotrigger delay (ms):','name': 'trig_autotrig', 'type': 'int', 'value': 5000,},
                    ]},
                ]},
            {'title': 'Channels:','name': 'channels', 'type': 'group', 'children':[
                {'title': 'ChA:','name': 'ChA', 'type': 'group', 'children':[
                        {'title': 'Active?:','name': 'active', 'type': 'bool','value': True},
                        {'title': 'Range:','name': 'range', 'type': 'list','value': '200mV', 'values': picoscope.DAQ_Picoscope_range.names()},
                        {'title': 'Coupling:','name': 'coupling', 'type': 'list','values': picoscope.DAQ_Picoscope_coupling.names()},
                        {'title': 'Analog offset (V):','name': 'offset', 'type': 'float','value': 0},
                        {'title': 'Overflow:','name': 'overflow', 'type': 'led','value': False},
                ]},
                {'title': 'ChB:','name': 'ChB', 'type': 'group', 'children':[
                        {'title': 'Active?:','name': 'active', 'type': 'bool','value': False},
                        {'title': 'Range:','name': 'range', 'type': 'list','value': '200mV', 'values': picoscope.DAQ_Picoscope_range.names()},
                        {'title': 'Coupling:','name': 'coupling', 'type': 'list','values': picoscope.DAQ_Picoscope_coupling.names()},
                        {'title': 'Analog offset (V):','name': 'offset', 'type': 'float','value': 0},
                        {'title': 'Overflow:','name': 'overflow', 'type': 'led','value': False},
                ]},
                {'title': 'ChC:','name': 'ChC', 'type': 'group', 'children':[
                        {'title': 'Active?:','name': 'active', 'type': 'bool','value': False},
                        {'title': 'Range:','name': 'range', 'type': 'list','value': '200mV', 'values': picoscope.DAQ_Picoscope_range.names()},
                        {'title': 'Coupling:','name': 'coupling', 'type': 'list','values': picoscope.DAQ_Picoscope_coupling.names()},
                        {'title': 'Analog offset (V):','name': 'offset', 'type': 'float','value': 0},
                        {'title': 'Overflow:','name': 'overflow', 'type': 'led','value': False},
                ]},
                {'title': 'ChD:','name': 'ChD', 'type': 'group', 'children':[
                        {'title': 'Active?:','name': 'active', 'type': 'bool','value': False},
                        {'title': 'Range:','name': 'range', 'type': 'list','value': '200mV', 'values': picoscope.DAQ_Picoscope_range.names()},
                        {'title': 'Coupling:','name': 'coupling', 'type': 'list','values': picoscope.DAQ_Picoscope_coupling.names()},
                        {'title': 'Analog offset (V):','name': 'offset', 'type': 'float','value': 0},
                        {'title': 'Overflow:','name': 'overflow', 'type': 'led','value': False},
                ]}


            ]},
            ]

    def __init__(self,parent=None,params_state=None): #init_params is a list of tuple where each tuple contains info on a 1D channel (Ntps,amplitude, width, position and noise)
        super(DAQ_1DViewer_Picoscope,self).__init__(parent,params_state)
        self.pico=picoscope.Picoscope_5000A()
        self.x_axis=None
        self.Nsample_available=0
        self.buffers=[]

    def get_active_channels(self):
        """
            Get the active communications channels of the Picoscope 5000A.
        """
        return [child.name() for child in self.settings.child(('channels')) if child.child(('active')).value()]

    def emit_x_axis(self):
        """
            Emit the thread command "x_axis" with x_axis as an attribute.

            See Also
            --------
            DAQ_utils.ThreadCommand
        """
        self.emit_status(ThreadCommand("x_axis",[self.x_axis]))

    def get_xaxis(self,Nsamples,time_window):
        """
            Get the current x_axis with Picoscope 5000A profile.

            =============== ============= =================================
            **Parameters**   **Type**      **Description**
            *Nsamples*       int           The number of time axis samples
            *time_window*    float/int ??  The time window full size
            =============== ============= =================================

            Returns
            -------
            (1D numpy array,int) tuple
                The x_axis and his length couple.


        """
        time_inter_s=time_window*1e-6/(Nsamples)
        status=self.pico.get_time_base(time_inter_s,Nsamples)
        if status[0]!="PICO_OK":
            raise Exception(status)
        x_axis=status[2] #time in ms starting at 0
        time_inter_ms=status[3]

        pico_status,x_offset=self.pico.getTriggerTimeOffset()
        if x_offset is None:
            x_offset=0

        x_axis=x_axis-x_offset## use ps5000aGetTriggerTimeOffset64
        N_pre_trigger=int(self.Nsample_available*self.settings.child('main_settings','trigger','trig_pretrigger').value()/100)
        x_axis=x_axis-time_inter_ms*N_pre_trigger
        return x_axis,len(x_axis)

    def commit_settings(self,param):
        """
            | Activate the parameters changes in the hardware.
            | Disconnect the data ready signal to preserve correct transmission.
            | 

            The given parameter offer 5 differents profiles :
                * **channels**  : Activate the channels update on the Picoscope 5000A
                * **Nsegments** : Set segments on the Picoscope 5000A
                * **trigger**   : Set the trig options on the Picoscope 5000A
                * **temporal**  : Set number of samples and resolution of time on the Picoscope 5000A
                * **dynamic**   : Set channels to dynamic range.

            | 
            | Send the data ready signal ance done.

            =============== ================================ ==========================
            **Parameters**   **Type**                        **Description**
            *param*         instance of pyqtgraph.parameter  The parameter to activate
            =============== ================================ ==========================     

            See Also
            --------
            Data_ready, get_active_channels, DAQ_utils.ThreadCommand, set_channels_to_dynamic_range, Ini_Detector, set_buffers
        """
        try:
            self.pico.data_ready_signal.disconnect(self.Data_ready)
        except:
            pass

        if param.parent().parent().name()=='channels':
            self.emit_status(ThreadCommand("Update_Status",['Updating Settings, please wait']))
            channel=picoscope.DAQ_Picoscope_trigger_channel[param.parent().name()].value
            enable_state=param.parent().child(('active')).value()
            coupling_type=picoscope.DAQ_Picoscope_coupling[param.parent().child(('coupling')).value()].value
            ch_range=picoscope.DAQ_Picoscope_range[param.parent().child(('range')).value()].value
            analog_offset=param.parent().child(('offset')).value()
            status=self.pico.setChannels(channel,enable_state,coupling_type,ch_range,analog_offset)   
            if status!="PICO_OK":
                self.emit_status(ThreadCommand('Update_Status',[status,'log']))
            self.set_buffers()

        elif param.name()=='Nsegments':
            #set number of segments
            status,NmaxSamples=self.pico.setSegments(param.value())
            if status=="PICO_OK":
                Nactive_channels=len(self.get_active_channels())
                if NmaxSamples/Nactive_channels<self.settings.child('main_settings','temporal','Nsamples').value(): #the available samples have to be distributed among the active channels
                    self.settings.child('main_settings','temporal','Nsamples').setValue(int(NmaxSamples/Nactive_channels))
            self.set_buffers()

        elif param.parent().name()=='trigger':
            #set picoscope trigger

            trigger_enabled=self.settings.child('main_settings','trigger','trig_enabled').value() 
            trigger_channel=picoscope.DAQ_Picoscope_trigger_channel[self.settings.child('main_settings','trigger','trig_channel').value()].value
            trigger_level=self.settings.child('main_settings','trigger','trig_level').value()
            trigger_type=picoscope.DAQ_Picoscope_trigger_type[self.settings.child('main_settings','trigger','trig_type').value()].name
            delay_sample=self.settings.child('main_settings','trigger','trig_delay').value()*1e-3#in s
            autoTrigger_ms=self.settings.child('main_settings','trigger','trig_autotrig').value()
            status=self.pico.set_simple_trigger(trigger_enabled,trigger_channel,trigger_level,trigger_type,delay_sample,autoTrigger_ms)
            if status!="PICO_OK":
                self.emit_status(ThreadCommand('Update_Status',[status,'log']))

        elif param.parent().name()=='temporal':
            window_ms=self.settings.child('main_settings','temporal','window').value() 
            self.x_axis,self.Nsample_available=self.get_xaxis(self.settings.child('main_settings','temporal','Nsamples').value(),window_ms*1000) #get time axis in ms
            self.settings.child('main_settings','temporal','window').setValue(np.max(self.x_axis)-np.min(self.x_axis))
            self.settings.child('main_settings','temporal','resolution').setValue(self.x_axis[1]-self.x_axis[0])
            self.emit_x_axis()
            self.settings.child('main_settings','temporal','Nsamples').setValue(self.Nsample_available)
            self.set_buffers()

        elif param.name()=='dynamic':
            self.set_channels_to_dynamic_range(param.value())
            self.Ini_Detector()

        self.pico.data_ready_signal.connect(self.Data_ready) 

    def update_pico_settings(self):
        """
            | Update the Picoscope 5000A from the settings tree values.
            | 

            The update is made on 4 times :
                * **Communication channels** update
                * **Number of segments** update
                * **Trigger** update
                * **Temporal** update

            | 
            | Send the data ready signal once done.

            See Also
            --------
            commit_settings, set_buffers, Data_ready
        """
        try:
            self.pico.data_ready_signal.disconnect(self.Data_ready)
        except:
            pass
        #set channels
        self.commit_settings(self.settings.child('channels','ChA','active'))
        self.commit_settings(self.settings.child('channels','ChB','active'))
        self.commit_settings(self.settings.child('channels','ChC','active'))
        self.commit_settings(self.settings.child('channels','ChD','active'))

        #set segments
        self.commit_settings(self.settings.child('main_settings','Nsegments'))

        #set trigger
        self.commit_settings(self.settings.child('main_settings','trigger','trig_channel'))

        #get x_axis
        self.commit_settings(self.settings.child('main_settings','temporal','window'))

        #set buffers
        self.set_buffers()
                
        self.pico.data_ready_signal.connect(self.Data_ready)    

    def set_channels_to_dynamic_range(self,dynamic_range):
        """
            | Update the settings tree from the given dynamic_range value.
            | 
            
            The dynamic range values are included in :
                * **8** bits
                * **12** bits
                * **14** bits
                * **15** bits
                * **16** bits

            =============== ========= =========================================
            **Parameters**   **Type**  **Description**
            *dynamic_range*  string    The dynamic range in number of bit form.
            =============== ========= =========================================
        """
        if dynamic_range=='8bits' or dynamic_range=='12bits' or dynamic_range=='14bits':
            self.settings.child('channels','ChA').setOpts(visible=True)
            self.settings.child('channels','ChB').setOpts(visible=True)
            self.settings.child('channels','ChC').setOpts(visible=True)
            self.settings.child('channels','ChD').setOpts(visible=True)

        elif dynamic_range=='15bits':
            self.settings.child('channels','ChC').setOpts(visible=False)
            self.settings.child('channels','ChC','active').setValue(False)
            self.settings.child('channels','ChD').setOpts(visible=False)
            self.settings.child('channels','ChD','active').setValue(False)

        elif dynamic_range=='16bits':
            self.settings.child('channels','ChB').setOpts(visible=False)
            self.settings.child('channels','ChB','active').setValue(False)
            self.settings.child('channels','ChC').setOpts(visible=False)
            self.settings.child('channels','ChC','active').setValue(False)
            self.settings.child('channels','ChD').setOpts(visible=False)
            self.settings.child('channels','ChD','active').setValue(False)

    def Ini_Detector(self):
        """
            Initialisation procedure of the detector with Picoscope 5000A profile.

            See Also
            --------
            DAQ_utils.ThreadCommand, update_pico_settings
        """
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None))
        try:
            status=self.pico.open_unit(None,dynamic_range= picoscope.DAQ_Picoscope_dynamic[self.settings.child('main_settings','dynamic').value()].value)
            if status[0]=="PICO_OK":
                self.update_pico_settings()

                self.pico.overflow_signal.connect(self.set_overflow)

                self.status.initialized=True
                return self.status
            else:
                #self.emit_status(ThreadCommand('Update_Status',[status[0],'log']))
                self.status.info=status[0]
                self.status.initialized=False
                return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
            self.status.info=str(e)
            self.status.initialized=False
            return self.status



    @pyqtSlot(int)
    def set_overflow(self,ind):
        """
            =============== ========== ==========================================================================================
            **Parameters**   **Type**   **Description**
            *ind*            int         the integer value of overflow threshold to be converted to the Picoscope trigger channel
            =============== ========== ==========================================================================================
        """
        try:
            bits=BitArray(int=ind,length=4).bin
            for ind,char in enumerate(bits):
                self.settings.child('main_settings','channels',picoscope.DAQ_Picoscope_trigger_channel(ind).name,'overflow').setValue(bool(char))
        except:
            pass


    def set_buffers(self):
        """
            Set and populate the buffer from the active communication channels of the Picoscope 5000A.

            See Also
            --------
            DAQ_utils.ThreadCommand, get_active_channels
        """
        #set buffers
        self.buffers=[]
        channels=self.get_active_channels()

        for ind_segment in range(self.settings.child('main_settings','Nsegments').value()):
            buffer_tmp=[]
            for channel in channels:
                ind_channel=picoscope.DAQ_Picoscope_trigger_channel[channel].value
                status=self.pico.set_buffer(self.Nsample_available,channel=ind_channel,ind_segment=ind_segment,downsampling_mode=0)
                if status[0]!="PICO_OK":
                    self.emit_status(ThreadCommand('Update_Status',[status[0],'log']))
                else:
                    buffer_tmp.append(status[1])

            self.buffers.append(buffer_tmp)

    def Close(self):
        """
            Close the current instance of Picoscope 5000A.
        """
        try:
            self.pico.stop()
            status=self.pico.close_unit()
        except:
            pass

    def Stop(self):
        """
            Stop actions on Picoscope 5000A.
        """
        self.pico.stop()
        return ""

    def Grab(self,Naverage=1):#for rapid block mode
        """
            | Start a new acquisition.
            | 
            | Grab the current values with Picoscope 5000A profile procedure.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       Number of spectrum to average
            =============== ======== ===============================================

            Returns
            -------
            string list
                the updated status.

            See Also
            --------
            DAQ_utils.ThreadCommand 
        """
        try:
            self.Naverage=Naverage
           
            N_pre_trigger=int(self.Nsample_available*self.settings.child('main_settings','trigger','trig_pretrigger').value()/100)
            N_post_trigger=self.Nsample_available-N_pre_trigger
            status=self.pico.setNoOfCapture(self.settings.child('main_settings','Nsegments').value())
            if status!="PICO_OK":
                self.emit_status(ThreadCommand("Update_Status",[status,'log']))

            status=self.pico.run_block(N_pre_trigger,N_post_trigger,ind_segment=0)
            if status[0]=="PICO_OK":
                if type(status[1])==int:
                    QThread.msleep(status[1])
            return status
        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))


    @pyqtSlot()
    def Data_ready(self):
        """ 
            | Cast the raw data (from Picoscope's communication channel) to export considering time axis in ms.
            | Send the data grabed signal once done.

            See Also
            --------
            get_active_channels, DAQ_utils.ThreadCommand
        """
        try:
            Nsegments=self.settings.child('main_settings','Nsegments').value()
            channels=self.get_active_channels()
            ind_channels=[picoscope.DAQ_Picoscope_trigger_channel[channel].value for channel in channels]
            data=np.zeros((len(channels),self.Nsample_available,Nsegments))
            status,Nsamples=self.pico.get_value_bulk(Nsamples_required=self.Nsample_available,start_segment=0,stop_segment=Nsegments-1)
            if status!="PICO_OK":
                self.emit_status(ThreadCommand("Update_Status",[status,'log']))
            window_ms=self.settings.child('main_settings','temporal','window').value() 
            self.x_axis,self.Nsample_available=self.get_xaxis(self.settings.child('main_settings','temporal','Nsamples').value(),window_ms*1000) #get time axis in ms
            self.emit_x_axis()

            for ind_segment in range(Nsegments):
                for ind,ind_channel in enumerate(ind_channels):
                    status,data_channel=self.pico.get_data(channel=ind_channel,buffer=self.buffers[ind_segment][ind])
                    data[ind,:,ind_segment]=data_channel['data']
            data_export=[np.sum(data[ind,:,:],axis=1)/Nsegments for ind in range(len(channels))]
            self.data_grabed_signal.emit(data_export)
                
        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))





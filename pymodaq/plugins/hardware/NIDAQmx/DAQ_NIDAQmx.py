from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal, QThread
from pymodaq.daq_utils.daq_utils import ThreadCommand
import numpy as np
from pymodaq.daq_viewer.utility_classes import DAQ_Viewer_base
from easydict import EasyDict as edict
from collections import OrderedDict
from enum import IntEnum
from pymodaq.daq_viewer.utility_classes import comon_parameters

class DAQ_NIDAQ_source(IntEnum):
    """
        Enum class of NIDAQ_source

        =============== ==========
        **Attributes**   **Type**
        *Analog_Input*   int
        *Counter*        int
        =============== ==========
    """
    Analog_Input=0
    Counter=1
    @classmethod
    def names(cls):
        return [name for name, member in cls.__members__.items()]

class DAQ_NIDAQmx(DAQ_Viewer_base):
    """
        ==================== ========================
        **Attributes**         **Type**
        *data_grabed_signal*   instance of pyqtSignal
        *params*               dictionnary list
        *task*
        ==================== ========================

        See Also
        --------
        refresh_hardware
    """

    data_grabed_signal=pyqtSignal(list)
    import PyDAQmx

    params= comon_parameters+[
             {'title':'Refresh hardware:', 'name': 'refresh_hardware', 'type': 'bool','value': False},
             {'title':'Signal type:', 'name': 'NIDAQ_type', 'type': 'list', 'values': DAQ_NIDAQ_source.names()},
             {'title':'Devices:', 'name': 'NIDAQ_devices', 'type': 'list'},
             {'title':'Channels:', 'name': 'channels', 'type': 'itemselect'},
             {'title':'AI Settings::', 'name': 'AI_settings', 'type': 'group', 'children':[
                 {'title':'Nsamples:', 'name': 'Nsamples', 'type': 'int', 'value': 1000, 'default': 1000, 'min': 1},
                 {'title':'Frequency:', 'name': 'frequency', 'type': 'float', 'value': 1000, 'default': 1000, 'min': 0, 'suffix': 'Hz'},
                 {'title':'Voltage Min:', 'name': 'volt_min', 'type': 'float', 'value': -10, 'default': -10, 'min': -10, 'max': 10, 'suffix': 'V'},
                 {'title':'Voltage Max:', 'name': 'volt_max', 'type': 'float', 'value': 10, 'default': 10, 'min': -10, 'max': 10, 'suffix': 'V'},
                 ]},
             {'title':'Counter Settings::', 'name': 'counter_settings', 'type': 'group', 'children':[
                 {'title':'Edge type::', 'name': 'edge', 'type': 'list', 'values':['Rising','Falling']},
                 {'title':'Counting time (ms):', 'name': 'counting_time', 'type': 'float', 'value': 100, 'default': 100, 'min': 0},
                 ]},
             ]


    def __init__(self, parent=None, params_state=None, control_type="0D"):
        super(DAQ_NIDAQmx, self).__init__(parent, params_state)

        self.control_type = control_type  # could be "0D", "1D"
        if self.control_type =="1D":
            self.settings.child(('NIDAQ_type')).setLimits(['Analog_Input'])
        else:
            self.settings.child(('NIDAQ_type')).setLimits(DAQ_NIDAQ_source.names())

        self.task=None
        self.refresh_hardware()
        self.timer= QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.counter_done)


    def commit_settings(self,param):
        """
            Activate the parameters changes in the hardware.

            =============== ================================ ===========================
            **Parameters**   **Type**                        **Description**
            *param*         instance of pyqtgraph.parameter   the parameter to activate
            =============== ================================ ===========================

            See Also
            --------
            update_NIDAQ_channels, update_task, DAQ_NIDAQ_source, refresh_hardware
        """
        if param.name()=='NIDAQ_devices':
            self.update_NIDAQ_channels()
            self.update_task()

        elif param.name()=='NIDAQ_type':
            self.update_NIDAQ_channels()
            if param.value()==DAQ_NIDAQ_source(0).name: #analog input
                self.settings.child(('AI_settings')).show()
                self.settings.child(('counter_settings')).hide()
            elif param.value()==DAQ_NIDAQ_source(1).name: #counter input
                self.settings.child(('AI_settings')).hide()
                self.settings.child(('counter_settings')).show()
                self.update_task()

        elif param.name()=='refresh_hardware':
            if param.value():
                self.refresh_hardware()
                QtWidgets.QApplication.processEvents()
                self.settings.child(('refresh_hardware')).setValue(False)

        else:
            self.update_task()


    @classmethod
    def update_NIDAQ_devices(cls):
        """
            Read and decode devices in the buffer.

            =============== ========= =================
            **Parameters**  **Type**   **Description**
            *cls*            ???
            =============== ========= =================

            Returns
            -------
            list
                list of devices
        """
        try:
            buff=cls.PyDAQmx.create_string_buffer(128)
            cls.PyDAQmx.DAQmxGetSysDevNames(buff,len(buff));
            devices=buff.value.decode().split(',')
            return devices
        except: return []


    def update_NIDAQ_channels(self,device=None,type_signal=None):
        """
            Update the communication channels of the NIDAQ hardware.

            =============== ========== =======================
            **Parameters**   **Type**  **Description**
            *device*         string    the name of the device
            *type_signal*    string    the type of the signal
            =============== ========== =======================

            See Also
            --------
            DAQ_NIDAQ_source, daq_utils.ThreadCommand
        """
        try:
            if device is None:
                device=self.settings.child(('NIDAQ_devices')).value()
            if type_signal is None:
                type_signal=self.settings.child(('NIDAQ_type')).value()

            if device!="":
                buff=self.PyDAQmx.create_string_buffer(256)

                if type_signal==DAQ_NIDAQ_source(0).name: #analog input
                    self.PyDAQmx.DAQmxGetDevAIPhysicalChans(device,buff,len(buff))
                    channels=buff.value.decode()[5:].split(', '+device+'/')

                elif type_signal==DAQ_NIDAQ_source(1).name: #counter
                    self.PyDAQmx.DAQmxGetDevCIPhysicalChans(device,buff,len(buff))
                    channels=buff.value.decode()[5:].split(', '+device+'/')
                if len(channels)>=1:
                    self.settings.child(('channels')).setValue(dict(all_items=channels,selected=[channels[0]]))
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),"log"]))


    def refresh_hardware(self):
        """
            Refresh the NIDAQ hardware from settings values.

            See Also
            --------
            update_NIDAQ_devices, update_NIDAQ_channels
        """
        devices=self.update_NIDAQ_devices()
        self.settings.child(('NIDAQ_devices')).setLimits(devices)
        self.update_NIDAQ_channels()

    def update_task(self):
        """
            Update the current module task from settings parameters.

            See Also
            --------
            DAQ_NIDAQ_source, daq_utils.ThreadCommand
        """
        try:
            if self.task is not None:
                if type(self.task)==self.PyDAQmx.Task:
                    self.task.ClearTask()
                else: self.task=None

            self.task=self.PyDAQmx.Task()
            channels=self.settings.child(('channels')).value()['selected']
            device=self.settings.child(('NIDAQ_devices')).value()

            if self.settings.child(('NIDAQ_type')).value()==DAQ_NIDAQ_source(0).name: #analog input

                for channel in channels:
                    err_code=self.task.CreateAIVoltageChan(device+"/"+channel,"",self.PyDAQmx.DAQmx_Val_Cfg_Default,self.settings.child('AI_settings','volt_min').value(),
                                 self.settings.child('AI_settings','volt_max').value(),self.PyDAQmx.DAQmx_Val_Volts,None)
                    if err_code is None:
                        err_code=self.task.CfgSampClkTiming(None,self.settings.child('AI_settings','frequency').value(),self.PyDAQmx.DAQmx_Val_Rising,
                                                            self.PyDAQmx.DAQmx_Val_FiniteSamps,self.settings.child('AI_settings','Nsamples').value())

                        if err_code is not None:
                            status=self.task.GetErrorString(err_code);raise Exception(status)
                    else:status=self.task.GetErrorString(err_code);raise Exception(status)

            elif self.settings.child(('NIDAQ_type')).value()==DAQ_NIDAQ_source(1).name: #counter
                if self.settings.child('counter_settings','edge').value()=="Rising":
                    edge=self.PyDAQmx.DAQmx_Val_Rising
                else:
                    edge=self.PyDAQmx.DAQmx_Val_Falling
                for channel in channels:
                    err_code=self.task.CreateCICountEdgesChan(device+"/"+channel,"",edge,0,self.PyDAQmx.DAQmx_Val_CountUp);
                    if err_code is not None:
                        status=self.task.GetErrorString(err_code);raise Exception(status)

            self.status.initialized=True
            self.status.controller=self.task
        except Exception as e:
            self.status.info=str(e)
            self.status.initialized=False
            self.emit_status(ThreadCommand('Update_Status',[str(e),"log"]))

    def Ini_Detector(self,controller=None):
        """
            Initialisation procedure of the detector.

            See Also
            --------
            daq_utils.ThreadCommand
        """
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None,controller=None))
        try:
            if self.settings.child(('controller_status')).value()=="Slave":
                if controller is None: 
                    raise Exception('no controller has been defined externally while this detector is a slave one')
                else:
                    self.task=controller
            else:
                self.update_task()
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
            self.status.info=str(e)
            self.status.initialized=False
            return self.status

    def Close(self):
        """
            Close the current module task.
        """
        self.task.StopTask()
        self.task.ClearTask()
        self.task=None


    def Grab(self,Naverage=1,**kwargs):
        """
            | Grab the current values with NIDAQ profile procedure.
            |
            | Send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       Number of values to average
            =============== ======== ===============================================

            See Also
            --------
            DAQ_NIDAQ_source
        """


        channels=self.settings.child(('channels')).value()['selected']

        if self.settings.child(('NIDAQ_type')).value()==DAQ_NIDAQ_source(0).name: #analog input
            data_tot = []
            read = self.PyDAQmx.int32()
            N=self.settings.child('AI_settings','Nsamples').value()
            data = np.zeros(N*len(channels), dtype=np.float64)
            self.task.StartTask()
            self.task.ReadAnalogF64(self.PyDAQmx.DAQmx_Val_Auto,10.0,self.PyDAQmx.DAQmx_Val_GroupByChannel,data,len(data),self.PyDAQmx.byref(read),None)
            self.task.StopTask()

            if self.control_type == "0D":
                for ind in range(len(channels)):
                    data_tot.append(np.array([np.mean(data[ind*N:(ind+1)*N-1])]))
                self.data_grabed_signal.emit([OrderedDict(name='NI AI', data=data_tot, type='Data0D')])
            else:
                for ind in range(len(channels)):
                    data_tot.append(data[ind*N:(ind+1)*N-1])
                self.data_grabed_signal.emit([OrderedDict(name='NI AI', data=data_tot, type='Data1D')])

        elif self.settings.child(('NIDAQ_type')).value()==DAQ_NIDAQ_source(1).name: #counter input
            self.task.StartTask()
            self.timer.start(self.settings.child('counter_settings','counting_time').value())





    def counter_done(self):

        channels = self.settings.child(('channels')).value()['selected']
        data_counter = np.zeros(len(channels), dtype='uint32')
        read = self.PyDAQmx.int32()

        self.task.ReadCounterU32Ex(self.PyDAQmx.DAQmx_Val_Auto, 10.0, self.PyDAQmx.DAQmx_Val_GroupByChannel, data_counter,
                                   len(data_counter), self.PyDAQmx.byref(read), None)

        self.task.StopTask()
        data_counter = data_counter.astype(float)
        data_counter = data_counter / (self.settings.child('counter_settings', 'counting_time').value() * 1e-3)

        self.data_grabed_signal.emit([OrderedDict(name='NI Counter', data=[data_counter], type='Data0D')])

    def Stop(self):
        """
            not implemented.
        """

        return ""

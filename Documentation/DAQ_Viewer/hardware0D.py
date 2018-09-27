from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize
from PyMoDAQ.DAQ_Viewer.utility_classes import DAQ_Viewer_base
import numpy as np
from easydict import EasyDict as edict
from enum import IntEnum
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import PyMoDAQ.DAQ_Utils.custom_parameter_tree
from PyMoDAQ.DAQ_Utils.python_lib.mathematics.mat_functions import gauss1D
from PyMoDAQ.DAQ_Utils.DAQ_utils import ThreadCommand

class DAQ_0DViewer_Det_type(IntEnum):
    """
        Enum class of Det_Type

        ================ ==========
        **Attributes**   **Type**
        *Mock*           int
        *Keithley_Pico*  int
        *NIDAQ*          int
        ================ ==========
    """
    Mock=0
    Keithley_Pico=1
    NIDAQ=2
    @classmethod
    def names(cls):
        names=cls.__members__.items()
        return [name for name, member in cls.__members__.items()]

class DAQ_0DViewer_Keithley_Pico_type(IntEnum):
    """
        Enum class of Keithley_Pico_type

        =============== =========
        **Attributes**  **Type**
        *Pico_648X*     int
        *Pico_6430*     int
        *Pico_6514*     int
        =============== =========
    """
    Pico_648X=0
    Pico_6430=1
    Pico_6514=2
    @classmethod
    def names(cls):
        names=cls.__members__.items()
        return [name for name, member in cls.__members__.items()]

class DAQ_0DViewer_NIDAQ_source(IntEnum):
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
        names=cls.__members__.items()
        return [name for name, member in cls.__members__.items()]



class DAQ_0DViewer_Mock(DAQ_Viewer_base):
    """
        =============== =================
        **Attributes**  **Type**
        *params*        dictionnary list
        *x_axis*        1D numpy array
        *ind_data*      int
        =============== =================
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

    def __init__(self,parent=None,params_state=None): #init_params is a list of tuple where each tuple contains info on a 1D channel (Ntps,amplitude, width, position and noise)
        super(DAQ_0DViewer_Mock,self).__init__(parent,params_state)
        self.x_axis=None
        self.ind_data=0


    def commit_settings(self,param):
        """
            Setting the mock data.

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
            For each parameter of the settings tree compute linspace numpy distribution with local parameters values
            and add computed results to the data_mock list.
        """
        self.data_mock=[]
        for param in self.settings.children():
            x=np.linspace(0,param.children()[0].value()-1,param.children()[0].value())
            self.data_mock.append(param.children()[1].value()*gauss1D(x,param.children()[2].value(),param.children()[3].value(),param.children()[4].value())
                                  +param.children()[5].value()*np.random.rand((param.children()[0].value())))

    def Ini_Detector(self):
        """
            Initialisation procedure of the detector.

            Returns
            -------
            ???
                the initialized status.

            See Also
            --------
            set_Mock_data
        """
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None))
        self.set_Mock_data()
        self.status.initialized=True
        return self.status

    def Close(self):
        """
            not implemented.
        """
        pass

    def Grab(self,Naverage=1):
        """
            | Start new acquisition.
            |

            For each data on data_mock :
                * shift right data of ind_data positions
                * if naverage parameter is defined append the mean of the current data to the data to be grabbed.
                
            |
            | Send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       specify the threshold of the mean calculation
            =============== ======== ===============================================

        """
        data_tot=[]
        for data in self.data_mock:
            data=np.roll(data,self.ind_data)
            if Naverage>1:
                data_tot.append(np.mean(data[0:Naverage-1]))
            else:
                data_tot.append(data[0])

        self.data_grabed_signal.emit(data_tot)
        self.ind_data+=1

    def Stop(self):
        """
            not implemented.
        """

        return ""

class DAQ_0DViewer_Keithley_Pico(DAQ_Viewer_base):
    """
        ==================== ========================
        **Attributes**        **Type**
        *data_grabed_signal*  instance of pyqtSignal
        *VISA_rm*             ResourceManager
        *com_ports*           
        *params*              dictionnary list
        *keithley*
        *settings*
        ==================== ========================
    """
    data_grabed_signal=pyqtSignal(list)

    ##checking VISA ressources
    try:
        from visa import ResourceManager
        VISA_rm=ResourceManager()
        com_ports=VISA_rm.list_resources()
    #    import serial.tools.list_ports;
    #    com_ports=[comport.device for comport in serial.tools.list_ports.comports()]

        params= [{'title': 'VISA:','name': 'VISA_ressources', 'type': 'list', 'values': com_ports },
                 {'title': 'Keithley Type:','name': 'keithley_type', 'type': 'list', 'values': DAQ_0DViewer_Keithley_Pico_type.names()},
                 {'title': 'Id:', 'name': 'id', 'type': 'text', 'value': "" },
                 {'title': 'Timeout (ms):', 'name': 'timeout', 'type': 'int', 'value': 10000, 'default': 10000, 'min': 2000 },
                 {'title': 'Configuration:', 'name': 'config', 'type': 'group', 'children':[
                     {'title': 'Meas. type:', 'name': 'meas_type', 'type': 'list', 'value': 'CURR', 'default': 'CURR', 'values': ['CURR','VOLT','RES','CHAR'] },


                     ] },
                ]
    except:
        pass
    def __init__(self,parent=None,params_state=None):
        super(DAQ_0DViewer_Keithley_Pico,self).__init__(parent,params_state)
        from visa import ResourceManager
        self.VISA_rm=ResourceManager()
        self.keithley=None

    def Ini_Detector(self):
        """
            Initialisation procedure of the detector.

            Returns
            -------

                The initialized status.

            See Also
            --------
            DAQ_utils.ThreadCommand
        """
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None))
        try:
            self.keithley=self.VISA_rm.open_resource(self.settings.child(('VISA_ressources')).value(), read_termination='\r')
            self.keithley.timeout=self.settings.child(('timeout')).value()

            self.keithley.write("*rst; status:preset; *cls;")
            txt=self.keithley.query('*IDN?')
            self.settings.child(('id')).setValue(txt)
            self.keithley.write('CONF:'+self.settings.child('config','meas_type').value())
            self.keithley.write(':FORM:ELEM READ;DATA ASC;')
            self.keithley.write('ARM:SOUR IMM;')
            self.keithley.write('ARM:COUNt 1;')
            self.keithley.write('TRIG:SOUR IMM;')
            #%%
            data=self.keithley.query_ascii_values('READ?')

            self.status.initialized=True
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
            self.status.info=str(e)
            self.status.initialized=False
            return self.status


    def commit_settings(self, param):
        """
            Activate the parameters changes in the hardware.

            =============== ================================= ============================
            **Parameters**   **Type**                         **Description**
            *param*         instance of pyqtgraph.parameter   The parameter to be checked.
            =============== ================================= ============================

            See Also
            --------
            DAQ_utils.ThreadCommand
        """
        try:
            if param.name()=='timeout':
                self.keithley.timeout=self.settings.child(('timeout')).value()
            elif param.name()=='meas_type':
                self.keithley.write('CONF:'+param.value())


        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))

    def Close(self):
        """
            Close the current instance of Keithley viewer.
        """
        self.keithley.close()

    def Grab(self,Naverage=1):
        """
            | Start new acquisition.
            | Grab the current values with keithley profile procedure.
            | Send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       Number of values to average
            =============== ======== ===============================================
        """
        data_tot=[]
        self.keithley.write('ARM:SOUR IMM;')
        self.keithley.write('ARM:COUNt 1;')
        self.keithley.write('TRIG:SOUR IMM;')
        self.keithley.write('TRIG:COUN {:};'.format(Naverage))
        data_tot=self.keithley.query_ascii_values('READ?')
        #for ind in range(Naverage):
        #    data_tot.append(self.keithley.query_ascii_values('READ?')[0])
        data_tot=[np.mean(np.array(data_tot))]
        self.data_grabed_signal.emit(data_tot)


    def Stop(self):
        """
            not implemented?
        """
        return ""

class DAQ_0DViewer_NIDAQ(DAQ_Viewer_base):
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
    try:
        data_grabed_signal=pyqtSignal(list)
        import PyDAQmx
    except:
        pass
    params= [{'title':'Refresh hardware:', 'name': 'refresh_hardware', 'type': 'bool','value': False},
             {'title':'Signal type:', 'name': 'NIDAQ_type', 'type': 'list', 'values': DAQ_0DViewer_NIDAQ_source.names()},
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
                 {'title':'Counting time:', 'name': 'counting_time', 'type': 'float', 'value': 0.1, 'default': 0.1, 'min': 0, 'suffix': 's'},
                 ]},
             ]


    def __init__(self,parent=None,params_state=None):
        super(DAQ_0DViewer_NIDAQ,self).__init__(parent,params_state)

        self.task=None
        self.refresh_hardware()


    def commit_settings(self,param):
        """
            Activate the parameters changes in the hardware.

            =============== ================================ ===========================
            **Parameters**   **Type**                        **Description**
            *param*         instance of pyqtgraph.parameter   the parameter to activate
            =============== ================================ ===========================

            See Also
            --------
            update_NIDAQ_channels, update_task, DAQ_0DViewer_NIDAQ_source, refresh_hardware
        """
        if param.name()=='NIDAQ_devices':
            self.update_NIDAQ_channels()
            self.update_task()

        elif param.name()=='NIDAQ_type':
            self.update_NIDAQ_channels()
            if param.value()==DAQ_0DViewer_NIDAQ_source(0).name: #analog input
                self.settings.child(('AI_settings')).show()
                self.settings.child(('counter_settings')).hide()
            elif param.value()==DAQ_0DViewer_NIDAQ_source(1).name: #counter input
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
            DAQ_0DViewer_NIDAQ_source, DAQ_utils.ThreadCommand
        """
        try:
            if device is None:
                device=self.settings.child(('NIDAQ_devices')).value()
            if type_signal is None:
                type_signal=self.settings.child(('NIDAQ_type')).value()

            if device!="":
                buff=self.PyDAQmx.create_string_buffer(128)

                if type_signal==DAQ_0DViewer_NIDAQ_source(0).name: #analog input
                    self.PyDAQmx.DAQmxGetDevAIPhysicalChans(device,buff,len(buff))
                    channels=buff.value.decode()[5:].split(', '+device+'/')

                elif type_signal==DAQ_0DViewer_NIDAQ_source(1).name: #counter
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
            DAQ_0DViewer_NIDAQ_source, DAQ_utils.ThreadCommand
        """
        try:
            if self.task is not None:
                if type(self.task)==self.PyDAQmx.Task:
                    self.task.ClearTask()
                else: self.task=None

            self.task=self.PyDAQmx.Task()
            channels=self.settings.child(('channels')).value()['selected']
            device=self.settings.child(('NIDAQ_devices')).value()

            if self.settings.child(('NIDAQ_type')).value()==DAQ_0DViewer_NIDAQ_source(0).name: #analog input

                for channel in channels:
                    err_code=self.task.CreateAIVoltageChan(device+"/"+channel,"",self.PyDAQmx.DAQmx_Val_Cfg_Default,self.settings.child('AI_settings','volt_min').value(),
                                 self.settings.child('AI_settings','volt_max').value(),self.PyDAQmx.DAQmx_Val_Volts,None)
                    if err_code is None:
                        err_code=self.task.CfgSampClkTiming(None,self.settings.child('AI_settings','frequency').value(),self.PyDAQmx.DAQmx_Val_Rising,
                                                            self.PyDAQmx.DAQmx_Val_FiniteSamps,self.settings.child('AI_settings','Nsamples').value())

                        if err_code is not None:
                            status=self.task.GetErrorString(err_code);raise Exception(status)
                    else:status=self.task.GetErrorString(err_code);raise Exception(status)

            elif self.settings.child(('NIDAQ_type')).value()==DAQ_0DViewer_NIDAQ_source(1).name: #counter
                if self.settings.child('counter_settings','edge').value()=="Rising":
                    edge=self.PyDAQmx.DAQmx_Val_Rising
                else:
                    edge=self.PyDAQmx.DAQmx_Val_Falling
                for channel in channels:
                    err_code=self.task.CreateCICountEdgesChan(device+"/"+channel,"",edge,0,PyDAQmx.DAQmx_Val_CountUp);
                    if err_code is not None:
                        status=self.task.GetErrorString(err_code);raise Exception(status)

            self.status.initialized=True
        except Exception as e:
            self.status.info=str(e)
            self.status.initialized=False
            self.emit_status(ThreadCommand('Update_Status',[str(e),"log"]))

    def Ini_Detector(self):
        """
            Initialisation procedure of the detector.

            See Also
            --------
            DAQ_utils.ThreadCommand
        """
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None))
        try:
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


    def Grab(self,Naverage=1):
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
            DAQ_0DViewer_NIDAQ_source
        """
        data_tot=[]
        read = self.PyDAQmx.int32()
        channels=self.settings.child(('channels')).value()['selected']

        if self.settings.child(('NIDAQ_type')).value()==DAQ_0DViewer_NIDAQ_source(0).name: #analog input
            N=self.settings.child('AI_settings','Nsamples').value()
            data = np.zeros(N*len(channels), dtype=np.float64)
            self.task.StartTask()
            self.task.ReadAnalogF64(self.PyDAQmx.DAQmx_Val_Auto,10.0,self.PyDAQmx.DAQmx_Val_GroupByChannel,data,len(data),self.PyDAQmx.byref(read),None)
            for ind in range(len(channels)):
                data_tot.append(np.mean(data[ind*N:(ind+1)*N-1]))

        elif self.settings.child(('NIDAQ_type')).value()==DAQ_0DViewer_NIDAQ_source(1).name: #counter input
            N=1
            data = np.zeros(len(channels), dtype=np.uint32)
            self.task.StartTask()
            QThread.msleep(self.settings.child('counter_settings','counting_time').value())
            self.task.ReadCounterU32Ex(self.PyDAQmx.DAQmx_Val_Auto,10.0, self.PyDAQmx.DAQmx_Val_GroupByChannel, data,len(data), self.PyDAQmx.byref(read), None);
            data=data.astype(int)

            if len(channels)>1:
                for ind in range(len(channels)):
                    data_tot.append(data[ind*N:(ind+1)*N-1])
            else:
                data_tot.append(data[0])

        self.data_grabed_signal.emit(data_tot)
        self.task.StopTask()

    def Stop(self):
        """
            not implemented.
        """

        return ""

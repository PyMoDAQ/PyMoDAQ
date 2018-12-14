# -*- coding: utf-8 -*-
"""
Created on Thu Jun 14 15:14:54 2018

@author: Weber Sébastien
@email: seba.weber@gmail.com
"""
from PyQt5.QtCore import pyqtSignal
from easydict import EasyDict as edict
from pymodaq.daq_utils.daq_utils import ThreadCommand
from pymodaq.daq_viewer.utility_classes import DAQ_Viewer_base
from collections import OrderedDict

import numpy as np
from enum import IntEnum
import re
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree
from pymodaq.daq_viewer.utility_classes import comon_parameters

class ReferenceModes(IntEnum):
    """

    """
    Single=0
    Dual_Harmonic=1
    Dual_Reference=2
    @classmethod
    def names(cls):
        return [name for name, member in cls.__members__.items()]


class Status(IntEnum):
    """

    """
    command_complete=0
    invalid_command=1
    command_parameter_error=2
    reference_unlock=3
    output_overload=4
    new_ADC_values_available=5
    input_overload=6
    data_available=7
    
    @classmethod
    def names(cls):
        return [name for name, member in cls.__members__.items()]  
    

class OutputOverload(IntEnum):
    """

    """
    X1=0
    Y1=1
    X2=2
    Y2=3
    CH1=4
    CH2=5
    CH3=6
    CH4=7
    
    @classmethod
    def names(cls):
        return [name for name, member in cls.__members__.items()]  




#%%

class DAQ_0DViewer_LockIn7270(DAQ_Viewer_base):
    """
        ==================== ========================
        **Attributes**        **Type**
        *data_grabed_signal*  instance of pyqtSignal
        *VISA_rm*             ResourceManager
        *com_ports*           
        *params*              dictionnary list
        *inst*
        *settings*
        ==================== ========================
    """
    data_grabed_signal=pyqtSignal(list)
    channels_single_mode=['X', 'Y', 'MAG', 'PHA']
    channels_dual_mode=['X1', 'Y1', 'MAG1', 'PHA1', 'X2', 'Y2', 'MAG2', 'PHA2']


    ##checking VISA ressources
    try:
        from visa import ResourceManager
        VISA_rm=ResourceManager()
        devices=list(VISA_rm.list_resources(query=u'?*::RAW'))
       
    except:
        devices=[]

    params= comon_parameters+[
                {'title': 'VISA:','name': 'VISA_ressources', 'type': 'list', 'values': devices },
                {'title': 'Manufacturer:', 'name': 'manufacturer', 'type': 'str', 'value': "" },
                {'title': 'Serial number:', 'name': 'serial_number', 'type': 'str', 'value': "" },
                {'title': 'Model:', 'name': 'model', 'type': 'str', 'value': "" },
                {'title': 'Timeout (ms):', 'name': 'timeout', 'type': 'int', 'value': 2000, 'default': 2000, 'min': 1000 },
                {'title': 'Configuration:', 'name': 'config', 'type': 'group', 'children':[
                {'title': 'Mode:', 'name': 'mode', 'type': 'list', 'values': ReferenceModes.names() },
                {'title': 'Channels in separate viewer:', 'name': 'separate_viewers', 'type': 'bool', 'value': True },
                {'title': 'Channels:', 'name': 'channels', 'type': 'itemselect', 'value': dict(all_items=channels_single_mode,selected=['MAG', 'PHA']) },
                ] },
            ]
    def __init__(self,parent=None,params_state=None):
        super(DAQ_0DViewer_LockIn7270,self).__init__(parent,params_state)
        self.inst=None


    def query_data(self,cmd):
        try:
            res=self.inst.query(cmd)
            searched=re.search('\n',res)
            status_byte=res[searched.start()+1]
            overload_byte=res[searched.start()+3]
            if searched.start!=0:
                data=np.array([float(x) for x in res[0:searched.start()].split(",")])
            else:
                data=None
            return (status_byte,overload_byte,data)
        except:
            return ('\x01','\x00',None)

    def query_string(self,cmd):
        try:
            res=self.inst.query(cmd)
            searched=re.search('\n',res)
            status_byte=res[searched.start()+1]
            overload_byte=res[searched.start()+3]
            if searched.start!=0:
                str=res[0:searched.start()]
            else:
                str=""
            return (status_byte,overload_byte,str)
        except:
            return ('\x01','\x00',"")

    def Ini_Detector(self,controller=None):
        """
            Initialisation procedure of the detector.

            Returns
            -------

                The initialized status.

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
                    self.inst=controller
            else:
                self.inst=self.VISA_rm.open_resource(self.settings.child(('VISA_ressources')).value())

            self.inst.timeout=self.settings.child(('timeout')).value()
            self.settings.child(('manufacturer')).setValue(self.inst.manufacturer_name)
            self.settings.child(('serial_number')).setValue(self.inst.serial_number)
            self.settings.child(('model')).setValue(self.query_string('ID')[2])

            self.settings.child('config','mode').setValue(ReferenceModes(int(self.query_string('REFMODE')[2])).name)
            self.status.controller=self.inst
            self.status.initialized=True
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
            self.status.info=str(e)
            self.status.initialized=False
            return self.status

    def Grab(self,Naverage=1,**kwargs):
        """
            | Start new acquisition.
            | Grab the current values.
            | Send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       Number of values to average
            =============== ======== ===============================================
        """
        data_tot=[]
        for channel in self.settings.child('config','channels').value()['selected']:
            if self.settings.child('config','separate_viewers').value():
                data_tot.append(OrderedDict(name=channel,data=[self.query_data(channel+'.')[2]], type='Data0D'))
            else:
                data_tot.append(self.query_data(channel+'.')[2])
        if self.settings.child('config','separate_viewers').value():
            self.data_grabed_signal.emit(data_tot)
        else:
            self.data_grabed_signal.emit([OrderedDict(name='Keithley',data=data_tot, type='Data0D')])


    def commit_settings(self, param):
        """
            Activate the parameters changes in the hardware.

            =============== ================================= ============================
            **Parameters**   **Type**                         **Description**
            *param*         instance of pyqtgraph.parameter   The parameter to be checked.
            =============== ================================= ============================

            See Also
            --------
            daq_utils.ThreadCommand
        """
        try:
            if param.name()=='timeout':
                self.inst.timeout=self.settings.child(('timeout')).value()
            elif param.name()=='mode':
                self.query_str('REFMODE {}'.format(ReferenceModes[param.value()].value))
            elif param.name()=='channels':
                data_init=[]
                for channel in param.value()['selected']:
                    if self.settings.child('config','separate_viewers').value():
                        data_init.append(OrderedDict(name=channel,data=[np.array([0])], type='Data0D'))
                    else:
                        data_init.append(np.array([0]))
                if self.settings.child('config','separate_viewers').value():
                    self.data_grabed_signal_temp.emit(data_init)
                else:
                    self.data_grabed_signal_temp.emit([OrderedDict(name='Keithley',data=data_init, type='Data0D')])

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))


    def Close(self):
        """
            Close the current instance of the visa session.
        """
        self.inst.close()



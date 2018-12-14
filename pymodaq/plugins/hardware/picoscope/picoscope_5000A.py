# -*- coding: utf-8 -*-
"""
Created on Tue Mar 28 09:24:55 2017

@author: Weber
"""

from PyQt5.QtCore import QObject, pyqtSignal, QThread
import ctypes
from ctypes.util import find_library
import numpy as np
from enum import Enum, IntEnum, EnumMeta

class EnumMeta_picoscope(EnumMeta):
    def __getitem__(self, name):
        try:
            return super().__getitem__(name)
        except:
            return super().__getitem__('_'+name)

class DAQ_Picoscope_dynamic(IntEnum,metaclass=EnumMeta_picoscope):
    _8bits=0
    _12bits=1
    _14bits=2
    _15bits=3 
    _16bits=4 

    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name[1:] for name, member in self.__members__.items()]


class DAQ_Picoscope_trigger_type(IntEnum):
    Above=0
    Below=1
    Rising=2
    Falling=3
    Rising_or_Falling=4
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class DAQ_Picoscope_trigger_channel(IntEnum):
    ChA=0
    ChB=1
    ChC=2
    ChD=3 
    Ext=4 
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class DAQ_Picoscope_coupling(IntEnum):
    AC=0
    DC=1
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class DAQ_Picoscope_range(IntEnum,metaclass=EnumMeta_picoscope):
    _10mV=0
    _20mV=1
    _50mV=2
    _100mV=3 
    _200mV=4 
    _500mV=5
    _1V=6
    _2V=7
    _5V=8
    _10V=9
    _20V=10
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name[1:] for name, member in self.__members__.items()]




class Picoscope_5000A(QObject):
    """
    Initialize an object to control the picoscope. It uses ctypes library and the .dll or .so dynamic libraries
    """
    overflow_signal=pyqtSignal(int) #triggered when there is an voltage overflow on one of the channels
    data_ready_signal=pyqtSignal()
    max_delay=8388607 #☻from pico5000aAPI.h
    def __init__(self):
        super(Picoscope_5000A,self).__init__()
        self._handle=-1
        self.Nsamples=1000
        self.NmaxSamples=1
        self.Nsegments=1
        self.NoOfCapture=1
        self.time_ms=None
        self.time_base=4
        self.time_inter_ns=1
        self.range=[0.200,0.2,0.2,0.2] # range in V for each channel
        self.range_list=[0.01,0.02,0.05,0.1,0.2,0.5,1,2,5,10,20]
        self.trigger_list=dict(Above=0,Below=1,Rising=2,Falling=3,Rising_or_Falling=4)
        self.dynamic_range=1
        self.dynamic_range_list=[8,12,14,15,16]
        self.channel_list=["channelA","channelB","channelC","channelD","ext"]
        ps5000aBlockReady=ctypes.WINFUNCTYPE(None,ctypes.c_short,ctypes.c_wchar_p,ctypes.c_voidp) # callback function
        self.__data_ready = ps5000aBlockReady(self._data_ready) #this is in order to keep it in memory
        libpath=find_library("C:\\Program Files\\Pico Technology\\SDK\lib\\PS5000a.dll")
        self._picolib=ctypes.windll.LoadLibrary(libpath) #object containing all pico_5000A functions
        self.waveform_parameters_default=dict(offset_voltage=int(1e6),pkTopk=1e6,wave_type=1,start_frequency=10000,stop_frequency=10000,
                                               increment_frequency=0,dwell_time=0,sweep_type=0,operation=0,
                                               shots=0,sweeps=0,trigger_type=0,trigger_source=0,extInThreshold=0)


    def list_devices(self):
        """
        Method returning a dictionnary containing the number and serial numbers of the pico devices.
        
        Returns
        -------
        pico_status : string indicating the status of the controllers 
        devices : dict(Ndevices=...,device=list(str))
        """
        devices=None
        pico_status=""
        try:
            count=ctypes.pointer(ctypes.c_short())
            serials=ctypes.pointer(ctypes.c_char())
            serialLth=ctypes.pointer(ctypes.c_short(50))

            err_code=self._picolib.ps5000aEnumerateUnits(count,serials,serialLth)
            pico_status=self._translate_error(err_code)
            
            if pico_status=="PICO_OK":
                devices=ctypes.string_at(serials).decode().split(',')
        except Exception as e:
            pico_status=str(e)        
        return pico_status,devices


    def _data_ready(self,_handle,status,pPar):
        """
        function called everytime the datas are available in the buffer
        """
        #print("data ready")
        self.data_ready_signal.emit()
       

        
    def _translate_error(self,err_code):
        """
        Fonction translating the error code from the dll functions into strings
        """
        pico_status=dict(ind0='PICO_OK',
            ind1='PICO_MAX_UNITS_OPENED',
            ind2='PICO_MEMORY_FAIL',
            ind3='PICO_NOT_FOUND',
            ind4='PICO_FW_FAIL',
            ind5='PICO_OPEN_OPERATION_IN_PROGRESS',
            ind6='PICO_OPERATION_FAILED',
            ind7='PICO_NOT_RESPONDING',
            ind8='PICO_CONFIG_FAIL',
            ind9='PICO_KERNEL_DRIVER_TOO_OLD',
            indA='PICO_EEPROM_CORRUPT',
            indB='PICO_OS_NOT_SUPPORTED',
            indC='PICO_INVALID_HANDLE',
            indD='PICO_INVALID_PARAMETER',
            indE='PICO_INVALID_TIMEBASE',
            indF='PICO_INVALID_VOLTAGE_RANGE',
            ind10='PICO_INVALID_CHANNEL',
            ind11='PICO_INVALID_TRIGGER_CHANNEL',
            ind12='PICO_INVALID_CONDITION_CHANNEL',
            ind13='PICO_NO_SIGNAL_GENERATOR',
            ind14='PICO_STREAMING_FAILED',
            ind15='PICO_BLOCK_MODE_FAILED',
            ind16='PICO_NULL_PARAMETER',
            ind18='PICO_DATA_NOT_AVAILABLE',
            ind19='PICO_STRING_BUFFER_TOO_SMALL',
            ind1A='PICO_ETS_NOT_SUPPORTED',
            ind1B='PICO_AUTO_TRIGGER_TIME_TOO_SHORT',
            ind1C='PICO_BUFFER_STALL',
            ind1D='PICO_TOO_MANY_SAMPLES',
            ind1E='PICO_TOO_MANY_SEGMENTS',
            ind1F='PICO_PULSE_WIDTH_QUALIFIER',
            ind20='PICO_DELAY',
            ind21='PICO_SOURCE_DETAILS',
            ind22='PICO_CONDITIONS',
            ind24='PICO_DEVICE_SAMPLING',
            ind25='PICO_NO_SAMPLES_AVAILABLE',
            ind26='PICO_SEGMENT_OUT_OF_RANGE',
            ind27='PICO_BUSY',
            ind28='PICO_STARTINDEX_INVALID',
            ind29='PICO_INVALID_INFO',
            ind2A='PICO_INFO_UNAVAILABLE',
            ind2B='PICO_INVALID_SAMPLE_INTERVAL',
            ind2C='PICO_TRIGGER_ERROR',
            ind2D='PICO_MEMORY',
            ind35='PICO_SIGGEN_OUTPUT_OVER_VOLTAGE',
            ind36='PICO_DELAY_NULL',
            ind37='PICO_INVALID_BUFFER',
            ind38='PICO_SIGGEN_OFFSET_VOLTAGE',
            ind39='PICO_SIGGEN_PK_TO_PK',
            ind3A='PICO_CANCELLED',
            ind3B='PICO_SEGMENT_NOT_USED',
            ind3C='PICO_INVALID_CALL',
            ind3F='PICO_NOT_USED',
            ind40='PICO_INVALID_SAMPLERATIO',
            ind41='PICO_INVALID_STATE',
            ind42='PICO_NOT_ENOUGH_SEGMENTS',
            ind43='PICO_DRIVER_FUNCTION',
            ind45='PICO_INVALID_COUPLING',
            ind46='PICO_BUFFERS_NOT_SET',
            ind47='PICO_RATIO_MODE_NOT_SUPPORTED',
            ind49='PICO_INVALID_TRIGGER_PROPERTY',
            ind4A='PICO_INTERFACE_NOT_CONNECTED',
            ind4D='PICO_SIGGEN_WAVEFORM_SETUP_FAILED',
            ind4E='PICO_FPGA_FAIL',
            ind4F='PICO_POWER_MANAGER',
            ind50='PICO_INVALID_ANALOGUE_OFFSET',
            ind51='PICO_PLL_LOCK_FAILED',
            ind52='PICO_ANALOG_BOARD',
            ind53='PICO_CONFIG_FAIL_AWG',
            ind54='PICO_INITIALISE_FPGA',
            ind56='PICO_EXTERNAL_FREQUENCY_INVALID',
            ind57='PICO_CLOCK_CHANGE_ERROR',
            ind58='PICO_TRIGGER_AND_EXTERNAL_CLOCK_CLASH',
            ind59='PICO_PWQ_AND_EXTERNAL_CLOCK_CLASH',
            ind5A='PICO_UNABLE_TO_OPEN_SCALING_FILE',
            ind5B='PICO_MEMORY_CLOCK_FREQUENCY',
            ind5C='PICO_I2C_NOT_RESPONDING',
            ind5D='PICO_NO_CAPTURES_AVAILABLE',
            ind5E='PICO_NOT_USED_IN_THIS_CAPTURE_MODE',
            ind103='PICO_GET_DATA_ACTIVE',
            ind104='PICO_IP_NETWORKED',
            ind105='PICO_INVALID_IP_ADDRESS',
            ind106='PICO_IPSOCKET_FAILED',
            ind107='PICO_IPSOCKET_TIMEDOUT',
            ind108='PICO_SETTINGS_FAILED',
            ind109='PICO_NETWORK_FAILED',
            ind10A='PICO_WS2_32_DLL_NOT_LOADED',
            ind10B='PICO_INVALID_IP_PORT',
            ind10C='PICO_COUPLING_NOT_SUPPORTED',
            ind10D='PICO_BANDWIDTH_NOT_SUPPORTED',
            ind10E='PICO_INVALID_BANDWIDTH',
            ind10F='PICO_AWG_NOT_SUPPORTED',
            ind110='PICO_ETS_NOT_RUNNING',
            ind111='PICO_SIG_GEN_WHITENOISE_NOT_SUPPORTED',
            ind112='PICO_SIG_GEN_WAVETYPE_NOT_SUPPORTED',
            ind116='PICO_SIG_GEN_PRBS_NOT_SUPPORTED',
            ind117='PICO_ETS_NOT_AVAILABLE_WITH_LOGIC_CHANNELS',
            ind118='PICO_WARNING_REPEAT_VALUE',
            ind119='PICO_POWER_SUPPLY_CONNECTED',
            ind11A='PICO_POWER_SUPPLY_NOT_CONNECTED',
            ind11B='PICO_POWER_SUPPLY_REQUEST_INVALID',
            ind11C='PICO_POWER_SUPPLY_UNDERVOLTAGE',
            ind11D='PICO_CAPTURING_DATA',
            ind11E='PICO_USB3_0_DEVICE_NON_USB3_0_PORT',
            ind11F='PICO_NOT_SUPPORTED_BY_THIS_DEVICE',
            ind120='PICO_INVALID_DEVICE_RESOLUTION',
            ind121='PICO_INVALID_NO_CHANNELS_FOR_RESOLUTION',
            ind122='PICO_CHANNEL_DISABLED_DUE_TO_USB_POWERED'
            )
        
        key="ind"+hex(err_code)[2:].upper()
        return pico_status[key]

    def open_unit(self,serial=None,dynamic_range=0):
        """
        Initialize the controller with the given serial number (as a string) and in the given dynamic range

        Parameters
        ----------
        serial: string terminating with a null character, result from list_devices should be used
        dynamic_range: enum (or int) gives which dynamic range to be intialized with
            0: 8  bits
            1: 12 bits
            2: 14 bits
            3: 15 bits
            4: 16 bits

        Returns
        -------
            pico_status : string indicating the status of the controller 
        """
        if type(serial)==str or serial is None:
            try:
                self._handle=ctypes.pointer(ctypes.c_short())
                if serial is not None:
                    serial=ctypes.c_char_p(serial.encode())
                err_code=self._picolib.ps5000aOpenUnit(self._handle,serial,dynamic_range)
                pico_status=self._translate_error(err_code)
                if pico_status=="PICO_OK":
                    pico_status=self.get_dynamic_range()
                    
                    self.dynamic_range=pico_status[2]
            except Exception as e:
                pico_status=str(e)    
        else:
            raise Exception('not a valid serial number')
        return pico_status

    def setChannels(self,channel=0,enable_state=True,coupling_type=0,range=4,analog_offset=0):
        """
        Set the channel settings, to be used for all available channels (this depends of the dynamic range) 

        Parameters
        ----------
        channel: int 0, 1, 2 or 3 for channels A, B, C, D 
        enable_state: bool state of the channel
        coupling type: int 0:"AC mode" , 1:"DC mode"
        range: enum (int) maximum/minimum voltage range 
            0: +-10mV
            1: +-20mV
            2: +-50mV
            3: +-100mV
            4: +-200mV (default)
            5: +-500mV
            6: +-1V
            7: +-2V
            8: +-5V
            9: +-10V
            10: +-20V
        analog_offset: voltage offset to be added (within the values from _get_analog_offset())
        Returns
        -------
            pico_status : string indicating the status of the controller 
        """
        
        if self._handle.contents.value>0:
            try:
                err_code=self._picolib.ps5000aSetChannel(self._handle.contents,channel,ctypes.c_short(enable_state),ctypes.c_int(coupling_type),ctypes.c_int(range),ctypes.c_float(analog_offset))
                pico_status=self._translate_error(err_code)
                self.range[channel]=self.range_list[range]
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status

    def get_time_base(self,time_inter_s=1,Nsamples=1000,ind_segment=0):
        """
        Get/Set the time_base 

        Parameters
        ----------
        time_inter_s: float, the time interval between two data points
        Nsamples: int the number of samples required.
        ind_segment: int the index of the memory segment to use. not implemented yet see rapid block mode
       
        Returns
        -------
        tuple containing:
        pico_status : string indicating the status of the controller 
        tbase: the integer setting the time resolution
        time__ms: the time vector in ms containing Nsamples points
        
        """
        self.time_ms=None
        if self._handle.contents.value>0:
            try:
                #calculating the int tbase corresponding to the time_inter_s
                if self.dynamic_range==0:#8bits
                    if time_inter_s<=4e-9:
                        tbase=int(np.rint((np.log(1e9*time_inter_s)/np.log(2))))
                    else:
                        tbase=int(np.rint(time_inter_s*125000000)+2)
                    if tbase<0:
                        tbase=0
                elif self.dynamic_range==1:#12bits
                    if time_inter_s<=8e-9:
                        tbase=int(np.rint(np.log(5e8*time_inter_s)/np.log(2)+1))
                    else:
                        tbase=int(np.rint((time_inter_s*62500000)+3))
                    if tbase<1:
                        tbase=1
                elif self.dynamic_range==2 or self.dynamic_range==3:#14bits or 15 bits
                    tbase=int(np.rint((time_inter_s*125000000)+2))
                    if tbase<3:
                        tbase=3
                elif self.dynamic_range==4:#16bits
                    tbase=int(np.rint((time_inter_s*62500000)+3))
                    if tbase<4:
                        tbase=4
                self.time_base=tbase
                time_inter_ns=ctypes.pointer(ctypes.c_float())
                Nsample_available=ctypes.pointer(ctypes.c_long())
                flag=True
                ind_flag=0
                while flag:
                    err_code=self._picolib.ps5000aGetTimebase2(self._handle.contents,ctypes.c_ulong(self.time_base),ctypes.c_long(int(Nsamples)),time_inter_ns,Nsample_available,ind_segment)
                    pico_status=self._translate_error(err_code)
                    
                    if pico_status=="PICO_OK":
                        Ntot=Nsample_available.contents.value
                        if Nsamples>Ntot:
                            Nsamples=Ntot
                        time_max=time_inter_ns.contents.value
                        if time_max<time_inter_s*1e9: #make sure the obtained total time is as large as the requested window
                            self.time_base+=1
                        else:
                            flag=False

                    elif ind_flag>100:
                        flag=False
                    else:
                        self.time_base+=1 
                    ind_flag+=1                       

                if pico_status!="PICO_OK":
                    raise Exception(pico_status)
                Ntot=Nsample_available.contents.value
                if Nsamples>Ntot:
                    Nsamples=Ntot
                self.time_inter_ns=time_inter_ns.contents.value
                self.time_ms=self.time_inter_ns/1e6*np.linspace(0,Nsamples-1,Nsamples,dtype=int)
                
                    
                
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status,tbase,self.time_ms , self.time_inter_ns/1e6

    
    def run_block(self,N_pre_trigger,N_post_trigger,ind_segment=0):
        """
        Start the acquisition. When the acquisition is done, the inner method _data_ready is triggered

        Parameters
        ----------
        N_pre_trigger: int the number of samples to return before the trigger event. If no trigger has been set then this argument is ignored and noOfPostTriggerSamples specifies the maximum number of samples to collect.
        N_post_trigger: int the number of samples to be taken after a trigger event. If no trigger event has been set then this specifies the maximum number of samples to be taken
        ind_segment: int the index of the memory segment to use. not implemented yet see rapid block mode
       
        Returns
        -------
        tuple containing:
            pico_status : string indicating the status of the controller
            timemeas: the time in ms it should take to do the acquisition
        """
        timemeas=None
        if self._handle.contents.value>0:
            try:
                N_pre_trigger=ctypes.c_long(N_pre_trigger)
                N_post_trigger=ctypes.c_long(N_post_trigger)
                timemeas=ctypes.pointer(ctypes.c_long())
                parameter=ctypes.pointer(ctypes.c_void_p()) #a void pointer that is passed to the ps5000aBlockReady callback function. The callback can use this pointer to return arbitrary data to the application.
                err_code=self._picolib.ps5000aRunBlock(self._handle.contents,N_pre_trigger,N_post_trigger,ctypes.c_int(self.time_base),timemeas,ind_segment,self.__data_ready,parameter)
                pico_status=self._translate_error(err_code)
                timemeas=timemeas.contents.value
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status,timemeas

    def stop(self):
        """
        stop whatever the controller was doing. To be called after each run_block
        Returns
        -------
        pico_status : string indicating the status of the controller
        """
        if self._handle.contents.value>0:
            try:
                err_code=self._picolib.ps5000aStop(self._handle.contents)
                pico_status=self._translate_error(err_code)
                
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status

    def set_buffer(self,Nsample_available=0,channel=0,ind_segment=0,downsampling_mode=0):
        """
        This function tells the driver where to store the data, either unprocessed or downsampled, that will be returned after the next call to one of the GetValues

        Parameters
        ----------
        channel: int 0, 1, 2 or 3 for channels A, B, C, D 
        ind_segment: int the index of the memory segment to use. not implemented yet see rapid block mode
        downsampling_mode: enum (int)
             0:"nothing" , 1:"Aggregate", 2: "average", 3: "decimate"
        
        Returns
        -------
        tuple containing:
            pico_status : string indicating the status of the controller 
            buffer: the buffer corresponding to channel
        """
        
        if self._handle.contents.value>0:
            try:
                buffer_type=ctypes.c_short * Nsample_available
                buffer=ctypes.pointer(buffer_type())
                buffer_array_size=ctypes.c_long(Nsample_available)
                err_code=self._picolib.ps5000aSetDataBuffer(self._handle.contents,ctypes.c_int(channel),buffer,buffer_array_size,ctypes.c_ulong(ind_segment),downsampling_mode)
                pico_status=self._translate_error(err_code)
                
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status,buffer
        
    def set_buffers_segments(self,Nsample_available=0,channels=[0],Nsegments=1,downsampling_mode=0):
        if self._handle.contents.value>0:
            try:
                data_type=ctypes.c_short * Nsample_available
                buffer_indiv=ctypes.pointer(data_type())
                buffer=[[buffer_indiv for ind_segment in range(Nsegments)]for ind_channel in range(len(channels)) ]
                buffer_array_size=ctypes.c_long(Nsample_available)
                for ind_segment in range(Nsegments):
                    for ind_channel in range(len(channels)):
                        channel=channels[ind_channel]
                        err_code=self._picolib.ps5000aSetDataBuffer(self._handle.contents,ctypes.c_int(channel),buffer[ind_channel][ind_segment],
                                                                    buffer_array_size,ctypes.c_ulong(ind_segment),downsampling_mode)
                        pico_status=self._translate_error(err_code)
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status,buffer


    def get_value_bulk(self,Nsamples_required=1000,start_segment=1,stop_segment=1,downsampling_ratio=1,downsampling_mode=0):
        if self._handle.contents.value>0:
            try:
                Nseg=stop_segment-start_segment+1
                c_start_segment=ctypes.c_ulong(start_segment)
                c_stop_segment=ctypes.c_ulong(stop_segment)
                Nsamples_out=ctypes.pointer(ctypes.c_ulong(Nsamples_required))
                overflow_type=ctypes.c_short * (Nseg)
                overflow=ctypes.pointer(overflow_type())
                c_downsampling_ratio=ctypes.c_ulong(downsampling_ratio)
                
                err_code=self._picolib.ps5000aGetValuesBulk(self._handle.contents,Nsamples_out,c_start_segment,c_stop_segment,
                                                            c_downsampling_ratio,downsampling_mode,overflow)
                pico_status=self._translate_error(err_code)
                Nsamples_out=Nsamples_out.contents.value
                #for ind_seg in range(Nseg):
                #    self.overflow_signal.emit(overflow.contents[ind_seg])
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status,Nsamples_out

    def populate_buffer(self,start_index=0,Nsamples_required=1000, downsampling_ratio=1,downsampling_mode=0,ind_segment=0):
        """
        This function transfer data from the picoscope memory to the buffer memory previously set for all enables channels

        Parameters
        ----------
        start_index: int data from the uffer starting at start_index
        Nsamples_required: int Number of samples one want to read
        downsampling_ratio: 
        downsampling_mode: enum (int)
             0:"nothing" , 1:"Aggregate", 2: "average", 3: "decimate"
        ind_segment: not implemented
        
        Returns
        -------
        tuple containing:
            pico_status : string indicating the status of the controller 
            data: dict(time=...,data=...)
        """
        
        if self._handle.contents.value>0:
            try:
                start_index=ctypes.c_ulong(0)
                Nsamples_out=ctypes.pointer(ctypes.c_ulong(Nsamples_required))
                overflow=ctypes.pointer(ctypes.c_short())
                c_downsampling_ratio=ctypes.c_ulong(downsampling_ratio)
                c_ind_segment=ctypes.c_ulong(ind_segment)
                err_code=self._picolib.ps5000aGetValues(self._handle.contents,start_index,Nsamples_out,c_downsampling_ratio,downsampling_mode,c_ind_segment,overflow)
                pico_status=self._translate_error(err_code)
                Nsamples_out=Nsamples_out.contents.value
                self.overflow_signal.emit(overflow.contents.value)
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status,Nsamples_out
                

    def get_data(self,channel=0,buffer=None):
        """
        This function retrieve the data for a given channel and writes it in the buffer defined with _set_buffer

        Parameters
        ----------
        channel:  either 0 to 3 for channel A to D
        buffer: a pointer where data from channel is stored
                
        Returns
        -------
        tuple containing:
            pico_status : string indicating the status of the controller 
            data: dict(time=...,data=...)
        """
        data=np.array([])
        
        if self._handle.contents.value>0:
            try:
                pico_status,maxval=self._get_maximum()
                data=(np.array(buffer.contents[:]))/maxval*self.range[channel] #signal given in volts
                time_ms=self.time_ms
                data=dict(time=time_ms,data=data)
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status,data

    def _get_minimum(self):
        """
        This function retrieve the minimum value of the ADC converter giving the dynamic range selected
                       
        Returns
        -------
        tuple containing:
            pico_status : string indicating the status of the controller 
            min_val: the int minimum value
        """
        if self._handle.contents.value>0:
            try:
                minval=ctypes.pointer(ctypes.c_short())
                err_code=self._picolib.ps5000aMinimumValue(self._handle.contents,minval)
                pico_status=self._translate_error(err_code)
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status,minval.contents.value


    def _get_maximum(self):
        """
        This function retrieve the maximum value of the ADC converter giving the dynamic range selected
                       
        Returns
        -------
        tuple containing:
            pico_status : string indicating the status of the controller 
            max_val: the int maximum value
        """
        if self._handle.contents.value>0:
            try:
                maxval=ctypes.c_short()
                err_code=self._picolib.ps5000aMaximumValue(self._handle.contents,ctypes.byref(maxval))
                pico_status=self._translate_error(err_code)
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status,maxval.value

    def close_unit(self):
        if self._handle.contents.value>0:
            try:
                err_code=self._picolib.ps5000aCloseUnit(self._handle.contents)
                pico_status=self._translate_error(err_code)
                self._handle=-1
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status
    

    def set_dynamic_range(self,dynamic_range=0):
        """
        set the given dynamic range, atribute a new _handle

        Parameters
        ----------
        dynamic_range: enum (or int) gives which dynamic range to be intialized with
            0: 8  bits
            1: 12 bits
            2: 14 bits
            3: 15 bits
            4: 16 bits

        Returns
        -------
            pico_status : string indicating the status of the controller 
        """
        try:
            #self._handle=ctypes.pointer(ctypes.c_short())
            err_code=self._picolib.ps5000aSetDeviceResolution(self._handle.contents,dynamic_range)
            pico_status=self._translate_error(err_code)
            if pico_status=="PICO_OK":
                self.dynamic_range=dynamic_range
        except Exception as e:
            pico_status=str(e)
        return pico_status,self._handle.contents,dynamic_range

    def get_dynamic_range(self):
        """
        get the given dynamic range, atribute a new _handle

        Parameters
        ----------
        

        Returns
        -------
        tuple containing:
            pico_status : string indicating the status of the controller 
            dynamic_range: enum (or int) gives which dynamic range to be intialized with
            0: 8  bits
            1: 12 bits
            2: 14 bits
            3: 15 bits
            4: 16 bits
        """
        try:
            
            device_resolution=ctypes.pointer(ctypes.c_int(0))
            err_code=self._picolib.ps5000aGetDeviceResolution(self._handle.contents,device_resolution)
            pico_status=self._translate_error(err_code)
            if pico_status=="PICO_OK":
                self.dynamic_range=device_resolution.contents.value
        except Exception as e:
            pico_status=str(e)
        return pico_status,self._handle.contents,self.dynamic_range

    def set_waveform(self,type=0,frequency=1000,waveform_parameters=None):
        """
        set the the waveform signal generator from basic shapes (see ps5000aSetSigGenArbitrary for arbitrary waveforms)
        PICO_STATUS ps5000aSetSigGenBuiltIn
        (
        short handle,
        long offsetVoltage,
        unsigned long pkToPk,
        PS5000A_WAVE_TYPE waveType,
        float startFrequency,
        float stopFrequency,
        float increment,
        float dwellTime,
        PS5000A_SWEEP_TYPE sweepType,
        PS5000A_EXTRA_OPERATIONS operation,
        unsigned long shots,
        unsigned long sweeps,
        PS5000A_SIGGEN_TRIG_TYPE triggerType,
        PS5000A_SIGGEN_TRIG_SOURCE triggerSource,
        short extInThreshold
        )

        Parameters
        ----------
        type: enum (or int) gives the shape of the waveform
            0: sine
            1: square
            2: triangle
            3: DC
            4: ramp_up
            5: ramp down
            6: sinc sinus cardinal
            7: gaussian
            8: half sine
        frequency: the main frequency
        waveform_parameters: dictionnary containing the needed parameters

        Returns
        -------
            pico_status : string indicating the status of the controller 
        """
        try:
            if waveform_parameters is None: # set the default (square like TTL)
                waveform_parameters=self.waveform_parameters_default

                offset_voltage=ctypes.c_long(waveform_parameters['offset_voltage']) # in microvolt
                pkTopk=ctypes.c_ulong(int(waveform_parameters['pkTopk']))# in microvolt
                wave_type=waveform_parameters['wave_type']
                start_frequency=ctypes.c_float(waveform_parameters['start_frequency'])
                stop_frequency=ctypes.c_float(waveform_parameters['stop_frequency'])
                increment_frequency=ctypes.c_float(waveform_parameters['increment_frequency'])
                dwell_time=ctypes.c_float(waveform_parameters['dwell_time'])
                sweep_type=waveform_parameters['sweep_type'] #either PS5000A_UP ,PS5000A_DOWN, PS5000A_UPDOWN,PS5000A_DOWNUP
                operation=waveform_parameters['operation']
                """either PS5000A_ES_OFF, normal signal generator operation specified by wavetype. PS5000A_WHITENOISE, the signal generator produces white noise
                and ignores all settings except pkToPk and offsetVoltage. PS5000A_PRBS, produces a random bitstream with a bit rate
                specified by the start and stop frequency."""
                shots=ctypes.c_long(waveform_parameters['shots'])
                """0: sweep the frequency as specified by sweeps 1...PS5000A_MAX_SWEEPS_SHOTS: the number of cycles of thewaveform to be produced
                after a trigger event. sweeps must be zero.PS5000A_SHOT_SWEEP_TRIGGER_CONTINUOUS_RUN: start and run continuously after trigger occurs"""
                sweeps=ctypes.c_long(waveform_parameters['sweeps'])
                """
                0: produce number of cycles specified by shots 1..PS5000A_MAX_SWEEPS_SHOTS: the number of times to sweepthe frequency after a
                trigger event, according to sweepType.shots must be zero.PS5000A_SHOT_SWEEP_TRIGGER_CONTINUOUS_RUN: start a
                sweep and continue after trigger occurs"""
                trigger_type=waveform_parameters['trigger_type']
                """PS5000A_SIGGEN_RISING trigger on rising edge PS5000A_SIGGEN_FALLING trigger on falling edge PS5000A_SIGGEN_GATE_HIGH run while trigger is high
                PS5000A_SIGGEN_GATE_LOW run while trigger is low"""
                trigger_source=waveform_parameters['trigger_source']
                """PS5000A_SIGGEN_NONE run without waiting for trigger PS5000A_SIGGEN_SCOPE_TRIG use scope trigger  PS5000A_SIGGEN_EXT_IN use EXT input
                PS5000A_SIGGEN_SOFT_TRIG wait for software trigger provided by ps5000aSigGenSoftwareControl PS5000A_SIGGEN_TRIGGER_RAW reserved"""
                extInThreshold=ctypes.c_short(waveform_parameters['extInThreshold']) #used to set trigger level for external trigger.

            err_code=self._picolib.ps5000aSetSigGenBuiltIn(self._handle.contents,offset_voltage,pkTopk,wave_type,start_frequency,stop_frequency,increment_frequency,
                                                           dwell_time,sweep_type,operation,shots,sweeps,trigger_type,trigger_source,extInThreshold)
            pico_status=self._translate_error(err_code)

        except Exception as e:
            pico_status=str(e)
        return pico_status

    def setSegments(self,Nsegments):
        """
        Set the number of segment
        Parameters
        ----------
        Nsegments: value between 1 to 250000 for the pico model 5444B
        
        Return
        ----------
        pico_status
        NmaxSamples for all channels

        """
        if self._handle.contents.value>0:
            try:
                self.Nsegments=Nsegments
                Nmaxsamples=ctypes.pointer(ctypes.c_long())
                err_code=self._picolib.ps5000aMemorySegments(self._handle.contents,ctypes.c_ulong(Nsegments),Nmaxsamples)
                pico_status=self._translate_error(err_code)
                
                if pico_status=="PICO_OK":
                    self.NmaxSamples=Nmaxsamples.contents.value
                else:
                    raise Exception(pico_status)
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status,self.NmaxSamples

    def setNoOfCapture(self,Ncapture):
        """
        Set the number of capture for the rapid block mode
        Parameters
        ----------
        Ncapture: value between 1 to Nsegments for the pico model 5444B
        """
        if self._handle.contents.value>0:
            try:
                self.NoOfCapture=Ncapture
                err_code=self._picolib.ps5000aSetNoOfCaptures(self._handle.contents,ctypes.c_ulong(Ncapture))
                pico_status=self._translate_error(err_code)
                
                if pico_status!="PICO_OK":
                    raise Exception(pico_status)
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status


    def getTriggerTimeOffset(self):
        if self._handle.contents.value>0:
            try:
                time_ms=None
                time=ctypes.c_int64()
                time_units=ctypes.c_int()
                err_code=self._picolib.ps5000aGetTriggerTimeOffset64(self._handle.contents,ctypes.byref(time),ctypes.byref(time_units),ind_segment=0)
                pico_status=self._translate_error(err_code)
                if pico_status=="PICO_OK":
                    time_range=[1e-15,1e-12,1e-9,1e-6,1e-3,1]
                    time_ms=time.value*time_range[int(time_units.value)]*1e3

            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status,time_ms


    def set_simple_trigger(self,enable_trigger=True,channel_source=0,threshold_V=0,trigger_type="Rising",delay_sample=0,autoTrigger_ms=0):
        """
        set the trigger with simpler options

        Parameters
        ----------
        enable_trigger: False to disable the trigger, True to enable
        source: the channel on which to trigger, either 0 to 3 for channel A to D or 4 for external source
        threshold: the Voltage at which the trigger will fire.
        trigger_type: the type in which the signal must move to cause a trigger. The following directions are supported: Above, Below,Rising, Falling and Rising_or_Falling.
        delay_sample: the time between the trigger occurring and the first sample, in s.
        autoTrigger_ms: the number of milliseconds the device will wait if no trigger occurs. If this is set to zero, the scope device will wait indefinitely for a trigger.
        """
        if self._handle.contents.value>0:
            try:
                c_enable_trigger=ctypes.c_int16(int(enable_trigger))
                if channel_source!=4:
                    c_threshold_ADC=ctypes.c_int32(int(threshold_V*self._get_maximum()[1]/self.range[channel_source])) #trigger level in ADC counts (depends of the dynaic range and the actual channel selected range)
                else:
                    c_threshold_ADC=ctypes.c_int32(int(threshold_V*self._get_maximum()[1]/5)) #in external mode the full range is +-5V hence the 5 in the formula
                c_direction=ctypes.c_int32(int(self.trigger_list[trigger_type]))
                delay=int(delay_sample/(self.time_inter_ns*1e-9))
                
                if delay>self.max_delay:
                    c_delay_sample=ctypes.c_ulong(self.max_delay)
                else:
                    c_delay_sample=ctypes.c_ulong(delay)
                
                err_code=self._picolib.ps5000aSetSimpleTrigger(self._handle.contents,c_enable_trigger,ctypes.c_int(channel_source),c_threshold_ADC,c_direction,c_delay_sample,ctypes.c_short(autoTrigger_ms))
                pico_status=self._translate_error(err_code)
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status

    def set_trigger_channel_directions(self,channelA_direction=2,channelB_direction=2,channelC_direction=2,channelD_direction=2,ext_direction=2):
        """
        This function set the trigger directions for the given channels

        Parameters
        ----------
        channel_A direction: the direction in which the signal must pass through the threshold to activate the trigger.
        
        a dict containing : dict(thresholUpper=...,thresholdUpperHysteresis=...,thresholdLower=...,thresholdLowerHysteresis=...,
            channel=...,thresholdMode=...)
            *thresholUpper :the upper threshold at which the trigger mustfire. This is scaled in 16-bit ADC counts at the currently selected range for that channel.
            *thresholdUpperHysteresis :=0
            *thresholdLower : the lower threshold at which the trigger must fire. This is scaled in 16-bit ADC counts at the currently selected range for that channel.
            *thresholdLowerHysteresis :=0
            *channel : either 0 to 3 for channel A to D or 4 for external source
            *thresholdMode: either a level or window trigger
        
        Returns
        -------
            pico_status : string indicating the status of the controller 
        """
        if self._handle.contents.value>0:
            try:
                err_code=self._picolib.ps5000aSetTriggerChannelDirections(self._handle.contents,channelA_direction,channelB_direction,channelC_direction,channelD_direction,ext_direction,2)
                pico_status=self._translate_error(err_code)
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status

    def set_trigger_settings(self,channel_properties=None,time_out_ms=0):
        """
        This function set the trigger type and properties

        Parameters
        ----------
        channel_properties: a dict containing : dict(thresholUpper=...,thresholdUpperHysteresis=...,thresholdLower=...,thresholdLowerHysteresis=...,
            channel=...,thresholdMode=...)
            *thresholUpper :the upper threshold at which the trigger mustfire. This is scaled in 16-bit ADC counts at the currently selected range for that channel.
            *thresholdUpperHysteresis :=0
            *thresholdLower : the lower threshold at which the trigger must fire. This is scaled in 16-bit ADC counts at the currently selected range for that channel.
            *thresholdLowerHysteresis :=0
            *channel : either 0 to 3 for channel A to D or 4 for external source
            *thresholdMode: either a level or window trigger
        
        Returns
        -------
            pico_status : string indicating the status of the controller 
        """
        if self._handle.contents.value>0:
            try:
                if channel_properties is not None:
                    c_channelProperties=ctypes.pointer(Trigger_channel_properties(**channel_properties)*1)
                else:
                    c_channelProperties=None
                nChannelProperties=ctypes.c_short(1)
                auxOutputEnable=ctypes.c_short()
                autoTriggerMilliseconds=ctypes.c_long(time_out_ms) #if zero no timeout
                err_code=self._picolib.ps5000aSetTriggerChannelProperties(self._handle.contents,c_channelProperties,nChannelProperties,auxOutputEnable,autoTriggerMilliseconds)
                pico_status=self._translate_error(err_code)
            except Exception as e:
                pico_status=str(e)
        else:
            pico_status="not valid handle, or unit not initialized"
        return pico_status


class Trigger_channel_properties(ctypes.Structure):
    _fields_ = [("thresholUpper", ctypes.c_short),
                ("thresholdUpperHysteresis", ctypes.c_ushort),
                ("thresholdLower",ctypes.c_short),
                ("thresholdLowerHysteresis",ctypes.c_ushort),
                ("channel",ctypes.c_int), # what channelto be used as trigger
                ("thresholdMode",ctypes.c_int)] #0 for level, 1 for window

if __name__ == '__main__':
    #%%

    import python_lib.hardware.picoscope.picoscope_5000A as pic_module
    pico=pic_module.Picoscope_5000A()
    serial='DY137/002'
    serial=None
    status=pico.open_unit(serial=serial)
    print(status)
    
    
    #%%
    status=pico.get_dynamic_range()
    print(status)
   
    #%%
    status=pico._get_maximum()
    print(status)
    
    #%%
    status=pico._get_minimum()
    print(status)
    #%%
    status=pico.set_dynamic_range(dynamic_range=2)
    print(status)
    
    #%%
    status=pico.setChannels(channel=0)
    print(status)

    #%%
    time_inter_s=1e-4 #0.1ms
    Nsamples=4000
    pico.Nsamples=Nsamples
    status=pico.get_time_base(time_inter_s=time_inter_s,Nsamples=Nsamples)
    print(status)
    tbase=status[1]

    #%%
    #status=pico.set_simple_trigger(enable_trigger=True,threshold_V=0.05,autoTrigger_ms=100)
    #print(status)

    #%%
    status=pico.run_block(0,Nsamples)
    print(status)

    #%%
    status=pico.set_buffer()
    print(status)
    #%%
    status=pico.get_data(channel=0,Nsamples_required=Nsamples)
    print(status)
    #%%
    status=pico.close_unit()
    print(status)
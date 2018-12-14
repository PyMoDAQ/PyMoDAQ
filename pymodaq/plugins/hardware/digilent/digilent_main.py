import ctypes
import sys
from enum import Enum
from collections import OrderedDict


class Digilent_enumfilter(Enum):
    enumfilterAll=0
    enumfilterEExplorer=1
    enumfilterDiscovery=2
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]


class Digilent_devid(Enum):
    devidEExplorer=1
    devidDiscovery=2

    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_devversion(Enum):
    devverEExplorerC   = 2
    devverEExplorerE   = 4
    devverEExplorerF   = 5
    devverDiscoveryA   = 1
    devverDiscoveryB   = 2
    devverDiscoveryC   = 3

    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_ins_states(Enum):
    trigsrcNone                 = 0
    trigsrcPC                   = 1
    trigsrcDetectorAnalogIn     = 2
    trigsrcDetectorDigitalIn    = 3
    trigsrcAnalogIn             = 4
    trigsrcDigitalIn            = 5
    trigsrcDigitalOut           = 6
    trigsrcAnalogOut1           = 7
    trigsrcAnalogOut2           = 8
    trigsrcAnalogOut3           = 9
    trigsrcAnalogOut4           = 10
    trigsrcExternal1            = 11
    trigsrcExternal2            = 12
    trigsrcExternal3            = 13
    trigsrcExternal4            = 14

    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_devversion(Enum):
    DwfStateReady        = 0
    DwfStateConfig       = 4
    DwfStatePrefill      = 5
    DwfStateArmed        = 1
    DwfStateWait         = 7
    DwfStateTriggered    = 3
    DwfStateRunning      = 3
    DwfStateDone         = 2

    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_STS(Enum):
    stsRdy		= 0
    stsArm		= 1
    stsDone		= 2
    stsTrig		= 3
    stsCfg		= 4
    stsPrefill	= 5
    stsNotDone	= 6
    stsTrigDly	= 7
    stsError	= 8
    stsBusy		= 9
    stsStop		= 10


    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_ACQMODE(Enum):
    acqmodeSingle       = 0
    acqmodeScanShift    = 1
    acqmodeScanScreen   = 2
    acqmodeRecord       = 3


    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_filter(Enum):
    filterDecimate = 0
    filterAverage  = 1
    filterMinMax   = 2
    
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_TRIGSOURC(Enum):
    trigsrcNone               = 0;
    trigsrcPC                 = 1;
    trigsrcDetectorAnalogIn   = 2;
    trigsrcDetectorDigitalIn  = 3;
    trigsrcAnalogIn           = 4;
    trigsrcDigitalIn          = 5;
    trigsrcDigitalOut         = 6;
    trigsrcAnalogOut1         = 7;
    trigsrcAnalogOut2         = 8;
    trigsrcAnalogOut3         = 9;
    trigsrcAnalogOut4         = 10;
    trigsrcExternal1          = 11;
    trigsrcExternal2          = 12;
    trigsrcExternal3          = 13;
    trigsrcExternal4          = 14;
    trigsrcHigh               = 15;
    trigsrcLow                = 16;

    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_TRIGSlope(Enum):
    DwfTriggerSlopeRise   = 0;
    DwfTriggerSlopeFall   = 1;
    DwfTriggerSlopeEither = 2;
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_TRIGTYPE(Enum):
    trigtypeEdge         = 0
    trigtypePulse        = 1
    trigtypeTransition   = 2
    
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_TRIGCOND(Enum):
    trigcondRisingPositive   = 0
    trigcondFallingNegative  = 1
    
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_TRIGLEN(Enum):
    triglenLess       = 0
    triglenTimeout    = 1
    triglenMore       = 2
    
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_DWFERC(Enum):
    dwfercNoErc                  = 0		#  No error occurred
    dwfercUnknownError           = 1		#  API waiting on pending API timed out
    dwfercApiLockTimeout         = 2		#  API waiting on pending API timed out
    dwfercAlreadyOpened          = 3		#  Device already opened
    dwfercNotSupported           = 4		#  Device not supported
    dwfercInvalidParameter0      = 16	#  Invalid parameter sent in API call
    dwfercInvalidParameter1      = 17	#  Invalid parameter sent in API call
    dwfercInvalidParameter2      = 18	#  Invalid parameter sent in API call
    dwfercInvalidParameter3      = 19	#  Invalid parameter sent in API call
    
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_FUNC(Enum):
    funcDC       = 0
    funcSine     = 1
    funcSquare   = 2
    funcTriangle = 3
    funcRampUp   = 4
    funcRampDown = 5
    funcNoise    = 6
    funcCustom   = 30
    funcPlay     = 31
    
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_ANALOGIO(Enum):
    analogioEnable      = 1
    analogioVoltage     = 2
    analogioCurrent     = 3
    analogioPower       = 4
    analogioTemperature	= 5
    
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_ANALOGOUT(Enum):
    AnalogOutNodeCarrier  = 0
    AnalogOutNodeFM       = 1
    AnalogOutNodeAM       = 2
    
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_DIGITALINCLOCK(Enum):
    DwfDigitalInClockSourceInternal = 0
    DwfDigitalInClockSourceExternal = 1
    
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_DigitalInSample(Enum):
    DwfDigitalInSampleModeSimple   = 0
    # alternate samples: noise|sample|noise|sample|...  
    # where noise is more than 1 transition between 2 samples
    DwfDigitalInSampleModeNoise    = 1
    
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_DigitalOutOutput(Enum):
    DwfDigitalOutTypePulse      = 0
    DwfDigitalOutTypeCustom     = 1
    DwfDigitalOutTypeRandom     = 2
    
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_DigitalOutType(Enum):
    DwfDigitalOutTypePulse      = 0
    DwfDigitalOutTypeCustom     = 1
    DwfDigitalOutTypeRandom     = 2
    
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]

class Digilent_DigitalOutIdle(Enum):
    DwfDigitalOutIdleInit     = 0
    DwfDigitalOutIdleLow      = 1
    DwfDigitalOutIdleHigh     = 2
    DwfDigitalOutIdleZet      = 3
    
    @classmethod
    def names(self):
        names=self.__members__.items()
        return [name for name, member in self.__members__.items()]




class Digilent(object):
    def __init__(self):
        super(Digilent,self).__init__()

        self._handle=ctypes.c_int(0)
        self.devices=[]

        if sys.platform.startswith("win"):
            self.dwf = ctypes.cdll.dwf #should be registered in the registery when installing the software
        elif sys.platform.startswith("darwin"):
            self.dwf =  ctypes.cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
        else:
            self.dwf =  ctypes.cdll.LoadLibrary("libdwf.so")


        self.check_errors()
        #print DWF version
        version = ctypes.create_string_buffer(16)
        self.dwf.FDwfGetVersion(version)
        return version.value.decode()
        print("DWF Version: "+version.value.decode())


    def check_errors(self):
        #check library loading errors
        szerr = ctypes.c_int()
        self.dwf.FDwfGetLastError(ctypes.byref(szerr))
        error=szerr.value
        #print(Digilent_DWFERC(error).name)
        
        if not not error:
            raise(Exception(Digilent_DWFERC(error).name))


    def device_enumeration(self):
        #enumerate and print device information
        cdevices = ctypes.c_int()
        self.dwf.FDwfEnum(ctypes.c_int(0), ctypes.byref(cdevices))
        self.check_errors()

        Ndevices=cdevices.value
        print("Number of Devices: "+str(Ndevices))
        #declare string variables
        devicename = ctypes.create_string_buffer(64)
        serialnum = ctypes.create_string_buffer(16)
        IsInUse = ctypes.c_bool()

        self.devices=[]
        for ind_device in range(0, Ndevices):
            self.dwf.FDwfEnumDeviceName (ctypes.c_int(ind_device), devicename)
            self.check_errors()
            self.dwf.FDwfEnumSN (ctypes.c_int(ind_device), serialnum)
            self.check_errors()
            self.dwf.FDwfEnumDeviceIsOpened(ctypes.c_int(ind_device), ctypes.byref(IsInUse))
            self.check_errors()
            self.devices.append(dict(ind=ind_device,name=devicename.value.decode(),serial=serialnum.value.decode(),in_use=IsInUse.value))
        return self.devices

    def open_device(self,ind_device=-1):
        """opens a digilent device
        ind_device int: index of the device as returned by device_enumeration() (default -1 open first device)
        """
        self.dwf.FDwfDeviceOpen(ctypes.c_int(ind_device),ctypes.byref(self._handle))
        self.check_errors()

        if self._handle.value == 0:
            raise("failed to open device")

    def close_device(self):
        self.dwf.FDwfDeviceClose(self._handle)
        self.check_errors()


class Digilent_AnalogOut(Digilent):

    def __init__(self):
        super(Digilent_AnalogOut,self).__init__()

    def get_N_Analogout_channels(self):
        Nchannel=ctypes.c_int()
        self.dwf.FDwfAnalogOutCount(self._handle,ctypes.byref(Nchannel))
        self.check_errors()
        return Nchannel.value

    def configure_analog_output(self,channel=0,function=Digilent_FUNC(0).name,enable=True,frequency=1000,amplitude=1.0,offset=1.0):
        """Configure analog out channel waveform

        """

        self.dwf.FDwfAnalogOutNodeEnableSet(self._handle, ctypes.c_int(channel), Digilent_ANALOGOUT['AnalogOutNodeCarrier'].value, ctypes.c_bool(enable))
        self.check_errors()
        if enable:
            self.dwf.FDwfAnalogOutNodeFunctionSet(self._handle, ctypes.c_int(channel), Digilent_ANALOGOUT['AnalogOutNodeCarrier'].value, ctypes.c_ubyte(Digilent_FUNC[function].value))
            self.check_errors()
            self.dwf.FDwfAnalogOutNodeFrequencySet(self._handle, ctypes.c_int(channel), Digilent_ANALOGOUT['AnalogOutNodeCarrier'].value, ctypes.c_double(frequency))
            self.check_errors()
            self.dwf.FDwfAnalogOutNodeAmplitudeSet(self._handle, ctypes.c_int(channel), Digilent_ANALOGOUT['AnalogOutNodeCarrier'].value, ctypes.c_double(amplitude))
            self.check_errors()
            self.dwf.FDwfAnalogOutNodeOffsetSet(self._handle, ctypes.c_int(channel), Digilent_ANALOGOUT['AnalogOutNodeCarrier'].value, ctypes.c_double(offset))
            self.check_errors()

    def get_enabled_state(self,channel):
        """
        FDwfAnalogOutNodeEnableGet(
        HDWF hdwf, int idxChannel, AnalogOutNode node, BOOL *pfEnable)
        Parameters:
        - hdwf – Open interface handle on a device.
        - idxChannel – Channel index.
        - node – Node index.
        - pfEnable – Pointer to variable to receive enabled state.
        The function above is used to verify if a specific channel and node is enabled or disabled.
        """
        c_enabled=ctypes.c_bool()
        node=ctypes.c_int(Digilent_ANALOGOUT['AnalogOutNodeCarrier'].value)
        self.dwf.FDwfAnalogOutNodeEnableGet(self._handle,channel,node,ctypes.byref(c_enabled))
        self.check_errors()
        return c_enabled.value

    def start_stop_analogout(self,channel=-1,start=True):
        """start and stop the instrument
        FDwfAnalogOutConfigure(HDWF hdwf, int idxChannel, BOOL fStart)
        Parameters:
        - hdwf – Interface handle.
        - idxChannel – Channel index.
        - fStart – Start the instrument. To stop, set to FALSE.
        The function above is used to

        channel int: index of the channel (default -1 all channels)
        """
        self.dwf.FDwfAnalogOutConfigure(self._handle,channel,ctypes.c_bool(start))
        self.check_errors()

    def get_status(self,channel=0):
        """
        FDwfAnalogOutStatus(HDWF hdwf, int idxChannel, DwfState *psts)
        Parameters:
        - hdwf – Open interface handle on a device.
        - idxChannel – Channel index.
        - psts – Pointer to variable to return the state.
        The function above is used to check the state of the instrument.
        """
        status_byte=ctypes.c_ubyte()
        self.dwf.FDwfAnalogOutStatus(self._handle,channel,ctypes.byref(status_byte))
        self.check_errors()
        status=Digilent_STS(status_byte.value)
        return status.name

    def get_function(self,channel=0):
        node=ctypes.c_int(Digilent_ANALOGOUT['AnalogOutNodeCarrier'].value)
        c_func=ctypes.c_ubyte()
        self.dwf.FDwfAnalogOutNodeFunctionGet(self._handle,channel,node,ctypes.byref(c_func))
        self.check_errors()
        return Digilent_FUNC(c_func.value).name

    def get_frequency_range(self,channel):
        node=ctypes.c_int(Digilent_ANALOGOUT['AnalogOutNodeCarrier'].value)
        c_f_max=ctypes.c_double()
        c_f_min=ctypes.c_double()
        self.dwf.FDwfAnalogOutNodeFrequencyInfo(self._handle,channel,node,ctypes.byref(c_f_min),ctypes.byref(c_f_max))
        self.check_errors()
        return c_f_min.value, c_f_max.value

    def get_frequency(self,channel):
        node=ctypes.c_int(Digilent_ANALOGOUT['AnalogOutNodeCarrier'].value)
        c_freq=ctypes.c_double()

        self.dwf.FDwfAnalogOutNodeFrequencyGet(self._handle,channel,node,ctypes.byref(c_freq))
        self.check_errors()
        return c_freq.value

    def get_amplitude_range(self,channel):
        node=ctypes.c_int(Digilent_ANALOGOUT['AnalogOutNodeCarrier'].value)
        c_amp_max=ctypes.c_double()
        c_amp_min=ctypes.c_double()
        self.dwf.FDwfAnalogOutNodeAmplitudeInfo(self._handle,channel,node,ctypes.byref(c_amp_min),ctypes.byref(c_amp_max))
        self.check_errors()
        return c_amp_min.value, c_amp_max.value

    def get_amplitude(self,channel):
        node=ctypes.c_int(Digilent_ANALOGOUT['AnalogOutNodeCarrier'].value)
        c_amp=ctypes.c_double()
        self.dwf.FDwfAnalogOutNodeAmplitudeGet(self._handle,channel,node,ctypes.byref(c_amp))
        self.check_errors()
        return c_amp.value

    def get_offset_range(self,channel):
        node=ctypes.c_int(Digilent_ANALOGOUT['AnalogOutNodeCarrier'].value)
        c_offset_max=ctypes.c_double()
        c_offset_min=ctypes.c_double()
        self.dwf.FDwfAnalogOutNodeOffsetInfo(self._handle,channel,node,ctypes.byref(c_offset_min),ctypes.byref(c_offset_max))
        self.check_errors()
        return c_offset_min.value, c_offset_max.value

    def get_offset(self,channel):
        node=ctypes.c_int(Digilent_ANALOGOUT['AnalogOutNodeCarrier'].value)
        c_offset=ctypes.c_double()
        self.dwf.FDwfAnalogOutNodeOffsetGet(self._handle,channel,node,ctypes.byref(c_offset))
        self.check_errors()
        return c_offset.value


    def set_trigger_source(self,channel,trig_source=Digilent_TRIGSOURC(0).name):
        c_trig_source=ctypes.c_ubyte(Digilent_TRIGSOURC[trig_source].value)
        self.dwf.FDwfAnalogOutTriggerSourceSet(self._handle,channel,c_trig_source)
        self.check_errors()

    def get_trigger_source(self,channel):
        c_trig_source=ctypes.c_ubyte()
        self.dwf.FDwfAnalogOutTriggerSourceGet(self._handle,channel,ctypes.byref(c_trig_source))
        self.check_errors()
        return Digilent_TRIGSOURC(c_trig_source.value).name

    def set_trigger_slope(self,channel,trig_slope=Digilent_TRIGSlope(0).name):
        c_trig_slope=ctypes.c_ubyte(Digilent_TRIGSlope[trig_source].value)
        self.dwf.FDwfAnalogOutTriggerSlopeSet(self._handle,channel,c_trig_slope)
        self.check_errors()

    def get_trigger_slope(self,channel):
        c_trig_slope=ctypes.c_ubyte()
        self.dwf.FDwfAnalogOutTriggerSlopeGet(self._handle,channel,ctypes.byref(c_trig_slope))
        self.check_errors()
        return Digilent_TRIGSlope(c_trig_slope.value).name

class Digilent_AnalogIO(Digilent):

    def __init__(self):
        super(Digilent_AnalogIO,self).__init__()

    def configure(self):
        self.dwf.FDwfAnalogIOConfigure(self._handle)
        self.check_errors()

    def get_Nchannels(self):
        Nchannel=ctypes.c_int()
        self.dwf.FDwfAnalogIOChannelCount(self._handle,ctypes.byref(Nchannel))
        self.check_errors()
        return Nchannel.value

    def set_master_state(self,running=False):
        self.dwf.FDwfAnalogIOEnableSet(self._handle,ctypes.c_bool(running))
        self.check_errors()

    def get_master_state(self):
        c_running=ctypes.c_bool()
        self.dwf.FDwfAnalogIOEnableGet(self._handle,ctypes.byref(c_running))
        self.check_errors()
        return c_running.value

    def get_channel_name(self,channel=0):
        cname=ctypes.create_string_buffer(32)
        clabel=ctypes.create_string_buffer(16)
        self.dwf.FDwfAnalogIOChannelName(self._handle,channel,cname,clabel)
        self.check_errors()
        return cname.value.decode(),clabel.value.decode()

    def get_channel_Nnodes(self,channel=0):
        cNnodes=ctypes.c_int()
        self.dwf.FDwfAnalogIOChannelInfo(self._handle,channel,ctypes.byref(cNnodes))
        self.check_errors()
        return cNnodes.value

    def get_channel_node_name(self,channel=0,node=0):
        cname=ctypes.create_string_buffer(32)
        cunits=ctypes.create_string_buffer(16)
        self.dwf.FDwfAnalogIOChannelNodeName(self._handle,channel,node,cname,cunits)
        self.check_errors()
        return cname.value.decode(),cunits.value.decode()

    def get_channel_nodes(self,channel=0,node_idx=0):
        canalog=ctypes.c_ubyte()
        self.dwf.FDwfAnalogIOChannelNodeName(self._handle,channel,node_idx,ctypes.byref(canalog))
        self.check_errors()
        #to do : check the form (bitwise) of canalog to retrieve value from Digilent_ANALOGIO

    def get_node_status(self,channel=0,node_idx=0):
        cmin=ctypes.c_double()
        cmax=ctypes.c_double()
        csteps=ctypes.c_int()

        self.dwf.FDwfAnalogIOChannelNodeStatusInfo(self._handle,channel,node_idx,ctypes.byref(cmin),ctypes.byref(cmax),ctypes.byref(csteps))
        self.check_errors()
        return (cmin.value,cmax.value,csteps.value)


    def set_channel_node_value(self,channel,nodeidx,value=0.0):
        self.dwf.FDwfAnalogIOChannelNodeSet(self._handle,channel,nodeidx,ctypes.c_double(value))
        self.check_errors()

    def get_channel_node_value(self,channel,nodeidx):
        cvalue=ctypes.c_double()
        self.dwf.FDwfAnalogIOChannelNodeGet(self._handle,channel,nodeidx,ctypes.byref(cvalue))
        self.check_errors()
        return cvalue.value

    def get_channel_node_value_read(self,channel,nodeidx):
        cvalue=ctypes.c_double()
        self.dwf.FDwfAnalogIOChannelNodeStatus(self._handle,channel,nodeidx,ctypes.byref(cvalue))
        self.check_errors()
        return cvalue.value

class Digilent_AnalogOut_IO(Digilent_AnalogOut,Digilent_AnalogIO):

    def __init__(self):
        super(Digilent_AnalogOut_IO,self).__init__()

if __name__=='__main__':
    import time

    dig=Digilent_AnalogOut_IO()

    try: 
        devices=dig.device_enumeration()
        dig.open_device(0)
        print(dig.set_master_state(True)) #◙should not be set to true while analog functions are running


        #dig.configure()

        print(dig.get_Nchannels())
        print(dig.get_node_status(0,0))

        print(dig.get_channel_name(0))
        print(dig.get_channel_Nnodes(0))
        print(dig.get_channel_node_name(0,0))
        print(dig.get_channel_node_value(0,0))
        print(dig.set_channel_node_value(0,0,1)) #enable the enable node
        print(dig.get_channel_node_value(0,0))
        print(dig.get_channel_node_value_read(0,0))

        print(dig.set_channel_node_value(0,1,5)) #set the voltage node to 3.95V
        print(dig.get_channel_node_value(0,1))
        
        print(dig.get_channel_node_value(0,0))
        print(dig.get_channel_node_value_read(0,0))

        print(dig.get_master_state())
        print(dig.set_master_state(False))


        dig.configure_analog_output(channel=0,function=Digilent_FUNC(2).name,enable=True,frequency=70000,amplitude=2.5,offset=2.5)
        print(dig.get_amplitude_range(0))
        print(dig.get_amplitude(0))
        print(dig.get_frequency_range(0))
        
        print(dig.get_enabled_state(0))
        print(dig.get_function(0))
        print(dig.get_offset(0))
        print(dig.get_offset_range(0))
        print(dig.get_status(0))

        dig.set_trigger_source(0,'trigsrcNone')

        dig.start_stop_analogout(0,True)

        time.sleep(5)

        dig.start_stop_analogout(0,False)



        dig.close_device()
    except Exception as e:
        print(str(e))
        dig.close_device()

        
    

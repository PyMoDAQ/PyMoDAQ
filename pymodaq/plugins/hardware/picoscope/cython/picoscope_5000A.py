import ctypes
from ctypes.util import find_library

#%%

class Picoscope_5000A(object):
    
    def __init(self):
        super(Picoscope_5000A,self).__init__()
        self._handle=-1

    def translate_error(self,err_code):
        #ind=int("0x"+str(err_code),0)
        ind=err_code
        res=["PICO_OK","PICO_MAX_UNITS_OPENED","PICO_MEMORY_FAIL","PICO_NOT_FOUND",
             "PICO_FW_FAIL","PICO_OPEN_OPERATION_IN_PROGRESS","PICO_OPERATION_FAILED",
             "PICO_NOT_RESPONDING","PICO_CONFIG_FAIL","PICO_KERNEL_DRIVER_TOO_OLD",
             "PICO_EEPROM_CORRUPT","PICO_OS_NOT_SUPPORTED","PICO_INVALID_HANDLE","PICO_INVALID_PARAMETER",
             "PICO_INVALID_TIMEBASE","PICO_INVALID_VOLTAGE_RANGE","PICO_INVALID_CHANNEL","PICO_INVALID_TRIGGER_CHANNEL",
             "PICO_INVALID_CONDITION_CHANNEL","PICO_NO_SIGNAL_GENERATOR","PICO_STREAMING_FAILED",
             "PICO_BLOCK_MODE_FAILED","PICO_NULL_PARAMETER","PICO_ETS_MODE_SET","PICO_DATA_NOT_AVAILABLE",
             "PICO_STRING_BUFFER_TOO_SMALL","PICO_ETS_NOT_SUPPORTED","PICO_AUTO_TRIGGER_TIME_TOO_SHORT",
             "PICO_BUFFER_STALL","PICO_TOO_MANY_SAMPLES","PICO_TOO_MANY_SEGMENTS","PICO_PULSE_WIDTH_QUALIFIER",
             "PICO_DELAY","PICO_SOURCE_DETAILS","PICO_CONDITIONS","PICO_USER_CALLBACK",
             "PICO_DEVICE_SAMPLING","PICO_NO_SAMPLES_AVAILABLE","PICO_SEGMENT_OUT_OF_RANGE",
             "PICO_BUSY","PICO_STARTINDEX_INVALID","PICO_INVALID_INFO","PICO_INFO_UNAVAILABLE",
             "PICO_INVALID_SAMPLE_INTERVA","PICO_TRIGGER_ERROR","PICO_MEMORY","PICO_SIG_GEN_PARAM",
             "PICO_SHOTS_SWEEPS_WARNING","PICO_SIGGEN_TRIGGER_SOURCE","PICO_AUX_OUTPUT_CONFLICT",
             "PICO_AUX_OUTPUT_ETS_CONFLICT","PICO_WARNING_EXT_THRESHOLD_CONFLICT",
             "PICO_WARNING_AUX_OUTPUT_CONFLICT","PICO_SIGGEN_OUTPUT_OVER_VOLTAGE","PICO_DELAY_NULL",
             "PICO_INVALID_BUFFER","PICO_SIGGEN_OFFSET_VOLTAG","PICO_SIGGEN_PK_TO_PK",
             "PICO_CANCELLED","PICO_SEGMENT_NOT_USED","PICO_INVALID_CALL","","","PICO_NOT_USED",
             "PICO_INVALID_SAMPLERATIO","PICO_INVALID_STATE",
             "","","","PICO_INVALID_COUPLING",
             "PICO_BUFFERS_NOT_SET","PICO_RATIO_MODE_NOT_SUPPORTED","PICO_RAPID_NOT_SUPPORT_AGGREGATION",
             "PICO_INVALID_TRIGGER_PROPERTY"]
        return res[ind]

#%% callback function
ps5000aBlockReady=ctypes.WINFUNCTYPE(None,ctypes.c_short,ctypes.c_wchar_p,ctypes.c_voidp)
def data_ready(handle,status,pPar):
    print(status)
    print("data ready")
    
_data_ready = ps5000aBlockReady(data_ready)

#%%
libpath=find_library("C:\\Program Files\\Pico Technology\\SDK\lib\\PS5000a.dll")
picolib=ctypes.CDLL(libpath)

#%%
count=ctypes.pointer(ctypes.c_short(0))
serials=ctypes.pointer(ctypes.c_char(0))
serialLth=ctypes.pointer(ctypes.c_short(10))

res=picolib.ps5000aEnumerateUnits(count,serials,serialLth)
print(translate_error(res))

print(count.contents.value)
print(serials.contents.value)
print(serialLth.contents.value)
#%%
handle=ctypes.pointer(ctypes.c_short())
#serial=ctypes.pointer(ctypes.c_char_p("DY137/001".encode(encoding='UTF-8')))


res=picolib.ps5000aOpenUnit(handle,b'DY137/002',0)
print(translate_error(res))
#%%
channel=0
range_data=4
res=picolib.ps5000aSetChannel(handle.contents,channel,1,0,range_data,ctypes.c_float(0))
print(translate_error(res))


#%% segmentation
Nsegment=ctypes.c_uint(2)
nMaxSample=ctypes.c_int()
res=picolib.ps5000aMemorySegments(handle.contents,Nsegment,nMaxSample)
print(translate_error(res))

#%%time base
Nsamples=4000
tbase_sec=1e-6#s
tbase=int((tbase_sec*125000000)+2)

time_base=ctypes.c_ulong(tbase)
time_inter=ctypes.pointer(ctypes.c_float())
Nsample_available=ctypes.pointer(ctypes.c_long())

res=picolib.ps5000aGetTimebase2(handle.contents,time_base,ctypes.c_long(Nsamples),time_inter,Nsample_available,ind_segment)
print(translate_error(res))
print(time_inter.contents.value)
#%% run block


for ind_segment in range(Nsegment.value):

    Npretrigger=ctypes.c_long(0)
    Nposttrigger=ctypes.c_long(Nsamples)
    timemeas=ctypes.pointer(ctypes.c_long())
    callback_pointer=_data_ready
    parameter=ctypes.pointer(ctypes.c_void_p())
    res=picolib.ps5000aRunBlock(handle.contents,Npretrigger,Nposttrigger,time_base,timemeas,ind_segment,callback_pointer,parameter)
    print(translate_error(res))


#ready=ctypes.pointer(ctypes.c_short())
#res=picolib.ps5000aIsReady(handle.contents,ready)
#print(translate_error(res))
#print(ready.contents.value)

#%%
res=picolib.ps5000aStop(handle.contents)
print(translate_error(res))
#%%
segment=ctypes.c_ulong(1)

buffer=(ctypes.c_short *Nsamples)()
buffer_array_size=ctypes.c_long(len(buffer))
down_mode=0
res=picolib.ps5000aSetDataBuffer(handle.contents,channel,ctypes.byref(buffer),buffer_array_size,segment,down_mode)
print(translate_error(res))
#%%
start_index=ctypes.c_ulong(0)
Nsamples_out=ctypes.pointer(ctypes.c_ulong(Nsamples))
downsampling_ratio=ctypes.c_ulong(1)
down_mode=0
overflow=ctypes.pointer(ctypes.c_short())
res=picolib.ps5000aGetValues(handle.contents,start_index,Nsamples_out,downsampling_ratio,down_mode,segment,overflow)
print(translate_error(res))

minval=ctypes.c_short()
res=picolib.ps5000aMinimumValue(handle.contents,ctypes.byref(minval))

print(translate_error(res))

maxval=ctypes.c_short()
res=picolib.ps5000aMaximumValue(handle.contents,ctypes.byref(maxval))
print(translate_error(res))

data=(np.array(buffer[:]))/maxval.value*200
time_ns=time_inter.contents.value*np.linspace(0,len(data)-1,len(data),dtype=int)
fig=mylib.figure_docked('picolib');
plt.plot(time_ns/1000,data)
#plt.ylim((-10,10))
#%%
res=picolib.ps5000aCloseUnit(handle.contents)
print(translate_error(res))
    


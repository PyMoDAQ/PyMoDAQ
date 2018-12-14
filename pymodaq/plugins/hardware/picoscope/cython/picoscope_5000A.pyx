
cimport cpicoscope_5000A
import ctypes

cdef class Picoscope_5000A(object):
    cdef cpicoscope_5000A.int16_t* _handle

    cpdef list_devices(self):
        cdef cpicoscope_5000A.uint32_t err_code
        cdef cpicoscope_5000A.int16_t* count=<cpicoscope_5000A.int16_t*>0
        cdef cpicoscope_5000A.int8_t * serials=''
        cdef cpicoscope_5000A.int16_t* serialLth=<cpicoscope_5000A.int16_t*>20
        
        err_code=cpicoscope_5000A.ps5000aEnumerateUnits(count,serials,serialLth)
#        cdef bytes py_string = serials
#        print(py_string)
        return self._translate_error(err_code)
    
    cpdef open_unit(self, int dynamic_range):
        cdef cpicoscope_5000A.uint32_t err_code
        
        cdef cpicoscope_5000A.int8_t * serial_ptr=b'DY137/002'
        
        
        #cdef cpicoscope_5000A.PS5000A_DEVICE_RESOLUTION c_dynamic_range=dynamic_range
        err_code=cpicoscope_5000A.ps5000aOpenUnit(self._handle,<cpicoscope_5000A.int8_t *> serial_ptr, <cpicoscope_5000A.PS5000A_DEVICE_RESOLUTION> dynamic_range)
        
        return self._translate_error(err_code)
    
    cpdef _translate_error(self,cpicoscope_5000A.uint32_t err_code):
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
        return res[err_code]

		


#if __name__ == '__main__':
#    pass
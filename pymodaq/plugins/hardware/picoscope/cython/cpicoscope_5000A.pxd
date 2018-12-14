

cdef extern from "ps5000aAPI.h":

    enum PS5000A_DEVICE_RESOLUTION:
        PS5000A_DR_8BIT
        PS5000A_DR_12BIT
        PS5000A_DR_14BIT
        PS5000A_DR_15BIT
        PS5000A_DR_16BIT

    ctypedef unsigned int  uint32_t
    ctypedef uint32_t PICO_STATUS
    ctypedef short int16_t
    ctypedef signed char int8_t  
    
    PICO_STATUS ps5000aOpenUnit(int16_t * handle, int8_t * serial,PS5000A_DEVICE_RESOLUTION dynamic_range)

    PICO_STATUS ps5000aCloseUnit(int16_t handle)

    PICO_STATUS ps5000aEnumerateUnits(int16_t * count,int8_t  * serials,int16_t * serialLth)
"""
    PythonForPicam is a Python ctypes interface to the Princeton Instruments PICAM Library
    Copyright (C) 2013  Joe Lowney.  The copyright holder can be reached at joelowney@gmail.com

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or any 
    later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import ctypes as ctypes

from .PiTypes import PicamModel, pi64s, piint, pichar, pibln, piflt, PicamComputerInterface, PicamEnumeratedType

##### Some of the types defined dependent on an enum: PicamStringSize.  From picam.h we have the following:
"""
typedef enum PicamStringSize
{
    PicamStringSize_SensorName     =  64,
    PicamStringSize_SerialNumber   =  64,
    PicamStringSize_FirmwareName   =  64,
    PicamStringSize_FirmwareDetail = 256
} PicamStringSize;
"""
### Which is why I define the following:
PicamStringSize_SensorName = PicamStringSize_SerialNumber = PicamStringSize_FirmwareName = 64
PicamStringSize_FirmwareDetail = 256

"""
typedef struct PicamCameraID
{
    PicamModel          model;
    PicamComputerInterface computer_interface;
    pichar                 sensor_name[PicamStringSize_SensorName];
    pichar                 serial_number[PicamStringSize_SerialNumber];
} PicamCameraID;
"""
class PicamCameraID(ctypes.Structure):
    _fields_ = [("model", PicamModel),
                ("computer_interface", PicamComputerInterface),
                ("sensor_name", pichar * PicamStringSize_SensorName),
                ("serial_number", pichar * PicamStringSize_SerialNumber)]

# PicamHandle
PicamHandle = ctypes.c_void_p


# PicamFirmwareDetail
"""
typedef struct PicamFirmwareDetail
{
    pichar name[PicamStringSize_FirmwareName];
    pichar detail[PicamStringSize_FirmwareDetail];
} PicamFirmwareDetail;
"""

class PicamFirmwareDetail(ctypes.Structure):
    _fields_ = [("name", pichar * PicamStringSize_FirmwareName),
                ("detail", pichar * PicamStringSize_FirmwareDetail)]

##### Types defined on pp57-70 (chapter 4: Camera Parameter Values, Inofrmation, Constraints, and Commitment)
    ### Saving this for later!

##### Types defined on p76 (chapter 5: Camera Data Acquisition)

# PicamAvailableData
"""
typedef struct PicamAvailableData
{
    void* initial_readout;
    pi64s readout_count;
} PicamAvailableData;
"""
class PicamAvailableData(ctypes.Structure):
    _fields_ = [("initial_readout", ctypes.c_void_p), ("readout_count", pi64s)]

class PicamAvailableData2(ctypes.Structure):
    _fields_ = [ ( "initial_readout", ctypes.POINTER(type(ctypes.c_void_p()))), ("readout_count", pi64s)]

# PicamAcquisitionErrorsMask
"""
typedef enum PicamAcquisitionErrorsMask
{
    PicamAcquisitionErrorsMask_None           = 0x0,
    PicamAcquisitionErrorsMask_DataLost       = 0x1,
    PicamAcquisitionErrorsMask_ConnectionLost = 0x2
} PicamAcquisitionErrorsMask; /* (0x4) */
"""
PicamAcquisitionErrorsMask = ctypes.c_int

# PicamAcquisitionStatus
class PicamAcquisitionStatus(ctypes.Structure):
    _fields_ = [("running",pibln),
                ("errors",PicamAcquisitionErrorsMask),
                ("readout_rate",piflt)]



class PicamRoi(ctypes.Structure):
    _fields_ = [('x',piint),
                ('width',piint),
                ('x_binning',piint),
                ('y',piint),
                ('height',piint),
                ('y_binning',piint)]

class PicamRois(ctypes.Structure):
    _fields_ = [('roi_array', ctypes.POINTER(PicamRoi*1)),
                ('roi_count',piint)]
    
    
class PicamPulse(ctypes.Structure):
    _fields_ = [('delay', piflt),
                ('width', piflt)]
    
    
class PicamModulation(ctypes.Structure):
    _fields_ = [('duration', piflt),
                ('frequency', piflt),
                ('phase', piflt),
                ('output_signal_frequency', piflt)]
    
class PicamModulations(ctypes.Structure):
    _fields_ = [('modulation_array', ctypes.POINTER(PicamModulation *1)),
                ('modulation_count', piint)]
    
PicamConstraintScope=piint
"""
    PicamConstraintScope_Independent = 1,
    PicamConstraintScope_Dependent   = 2
} PicamConstraintScope; /* (3) */
"""

PicamConstraintSeverity=piint
"""
{
    PicamConstraintSeverity_Error   = 1,
    PicamConstraintSeverity_Warning = 2
} PicamConstraintSeverity; /* (3) */
"""

class PicamRangeConstraint(ctypes.Structure):
    _fields_ = [('scope', PicamConstraintScope),
                ('severity', PicamConstraintSeverity),
                ('empty_set',pibln),
                ('minimum', piflt),
                ('maximum', piflt),
                ('increment', piflt),
                ('excluded_values_array', ctypes.POINTER(piflt*10)),
                ('excluded_values_count', piint),
                ('outlying_values_array', ctypes.POINTER(piflt*10)),
                ('outlying_values_count', piint)]

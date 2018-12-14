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



##### Following definitions are from page 11 
piint = ctypes.c_int # """Integer native to platform"""
piflt = ctypes.c_float # """Floating point native to platform"""
pibln = ctypes.c_bool # """Boolean native to platform"""
pichar = ctypes.c_char # """character native to platform"""
pibyte = ctypes.c_byte # """Byte native to platform"""
pibool = ctypes.c_bool # """C++ Boolean native to platform????"""

pi8s = ctypes.c_int8
pi8u = ctypes.c_uint8
pi16s = ctypes.c_int16
pi16u = ctypes.c_uint16
pi32s = ctypes.c_int32
pi32u = ctypes.c_uint32
pi64s = ctypes.c_int64
pi64u = ctypes.c_uint64
## Not sure if these next two are correct
pi32f = ctypes.c_double
pi64f = ctypes.c_longdouble

##### types defined on p15 (chapter 2: General Library Usage -- Version, Initialization, and Strings).  Python ctypes doesn't support enums but int might work instead? """
PicamError = ctypes.c_int
PicamEnumeratedType = ctypes.c_int

##### types defined on pp24-pp25 (chapter 3: Camera Identification, Access, Information, and Demo) """

PicamModel = ctypes.c_int
PicamComputerInterface = ctypes.c_int
PicamStringSize = ctypes.c_int

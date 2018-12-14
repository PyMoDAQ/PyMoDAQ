# python-andor A Python3 wrapper for Andor's scientific cameras
#   based on:
#   pyAndor - A Python wrapper for Andor's scientific cameras
#   Copyright (C) 2009  Hamid Ohadi
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

from ctypes import *
import sys, os
import platform

import numpy as np

import time

#~ from andor.errorcodes import ERROR_CODE


"""Shamrock class which is meant to provide the Python version of the same
   functions that are defined in the Andor's SDK."""

class Shamrock:
    def __init__(self, dllpath="C:\\Program Files\\Andor SOLIS\\Drivers\\Shamrock\\C\\GratingWavelength\\"):
        # Check operating system and load library
        if platform.system() == "Linux":
            dllname = "/usr/local/lib/libshamrockcif.so"
            self.dll = cdll.LoadLibrary(dllname)
        elif platform.system() == "Windows":
            path = dllpath
            dllname = "ShamrockCIF"
            os.environ['PATH'] = path + ';' + os.environ['PATH']
            self.dll = windll.LoadLibrary(dllname)
        else:
            print "Cannot detect operating system, will now stop"
            raise
        
        # Initialize the device
        
        error = self.dll.ShamrockInitialize(path)
        print "Initializing: %s" % ( ERROR_CODE[error])
        
        self.verbosity = True
        self.NrPixels = 0
        
        
        
        

    def __del__(self):
        error = self.dll.ShamrockClose()
        #~ self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)

    def verbose(self, error, function=''):
        if self.verbosity is True:
            print("[%s]: %s" % (function, error))

    def SetVerbose(self, state=True):
        self.verbosity = state

    def GetNumberDevicesSR(self):
        nodevices = c_int()
        error = self.dll.ShamrockGetNumberDevices(byref(nodevices))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error], nodevices.value

    def GetFunctionReturnDescriptionSR(self, error, MaxDescStrLen):
        error = c_int(error)
        MaxDescStrLen = c_int(MaxDescStrLen)
        description = c_char_p()
        err = self.dll.ShamrockGetFunctionReturnDescription(error, description, MaxDescStrLen)
        self.verbose(ERROR_CODE[err], sys._getframe().f_code.co_name)
        return ERROR_CODE[err], description.value

    #---- sdkeeprom functions

    def GetSerialNumberSR(self, device):
        device = c_int(device)
        serial = c_char_p
        error = self.dll.ShamrockGetSerialNumber(device, serial)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error], serial.value

    def EepromGetOpticalParamsSR(self, device):
        device = c_int(device)
        FocalLength = c_float()
        AngularDeviation = c_float()
        FocalTilt = c_float()
        error = self.dll.ShamrockEepromGetOpticalParams(device, byref(FocalLength),byref(AngularDeviation), byref(FocalTilt))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error], FocalLength.value, AngularDeviation.value, FocalTilt.value

    #---- sdkgrating functions
    def SetGratingSR(self, device, grating):
        device = c_int(device)
        grating = c_int(grating)
        error = self.dll.ShamrockSetGrating(device, grating)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def GetGratingSR(self, device):
        device = c_int(device)
        grating = c_int()
        error = self.dll.ShamrockGetGrating(device, byref(grating))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error], grating.value

    def WavelengthResetSR(self, device):
        device = c_int(device)
        error = self.dll.ShamrockWavelengthReset(device)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def GetNumberGratingsSR(self, device):
        device = c_int(device)
        noGratings = c_int()
        error = self.dll.ShamrockGetNumberGratings(device, byref(noGratings))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error], noGratings.value

    def GetGratingInfoSR(self, device, grating):
        device = c_int(device)
        grating = c_int(grating)
        Lines = c_float()
        Blaze = c_char_p()
        Home = c_int()
        Offset = c_int()
        error = self.dll.ShamrockGetGratingInfo(device, grating, 
                    byref(Lines), byref(Blaze), byref(Home), byref(Offset))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error], Lines.value, Blaze, Home.value, Offset.value
    
    #---- sdkwavelength functions
    def SetWavelengthSR(self, device, wavelength):
        device = c_int(device)
        wavelength = c_float(wavelength)
        error = self.dll.ShamrockSetWavelength(device, wavelength)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]
    
    def GetWavelengthSR(self, device):
        device = c_int(device)
        wavelength = c_float()
        error = self.dll.ShamrockGetWavelength(device, byref(wavelength))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error], wavelength.value
    
    def GetWavelengthLimitsSR(self, device, grating):
        device = c_int(device)
        grating = c_int(grating)
        minLambda = c_float()
        maxLambda = c_float()
        error = self.dll.ShamrockGetWavelengthLimits(device, grating, byref(minLambda), byref(maxLambda))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error], minLambda.value, maxLambda.value
    
    def GotoZeroOrderSR(self, device):
        device = c_int(device)
        error = self.dll.ShamrockGotoZeroOrder(device)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]
    
    def AtZeroOrderSR(self, device):
        device = c_int(device)
        atZeroOrder = c_int()
        error = self.dll.ShamrockAtZeroOrder(device, byref(atZeroOrder))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error], atZeroOrder.value
    
    #---- sdkcalibration functions
    def SetNumberPixelsSR(self, device, NumberPixels):
        device = c_int(device)
        NumberPixels = c_int(NumberPixels)
        error = self.dll.ShamrockSetNumberPixels(device, NumberPixels)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        self.NrPixels = NumberPixels.value
        return ERROR_CODE[error]
    
    def SetPixelWidthSR(self, device, Width):
        device = c_int(device)
        Width = c_float(Width)
        error = self.dll.ShamrockSetPixelWidth(device, Width)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]
    
    def GetNumberPixelsSR(self, device):
        device = c_int(device)
        NumberPixels = c_int()
        error = self.dll.ShamrockGetNumberPixels(device, byref(NumberPixels))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        self.NrPixels = NumberPixels.value
        return ERROR_CODE[error], NumberPixels.value
    
    def GetPixelWidthSR(self, device):
        device = c_int(device)
        Width = c_float()
        error = self.dll.ShamrockGetPixelWidth(device, byref(Width))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error], Width.value
    
    def GetCalibrationSR(self, device):
        device = c_int(device)
        CalibrationValues = (c_float*self.NrPixels)()
        #~ CalibrationValues = c_void_p()
        NumberPixels = c_int()
        error = self.dll.ShamrockGetCalibration(device, byref(CalibrationValues), byref(NumberPixels))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error], CalibrationValues, NumberPixels.value
    


#~ -OK- unsigned int WINAPI ShamrockSetPixelWidth(int device, float Width);
#~ -OK- unsigned int WINAPI ShamrockSetNumberPixels(int device, int NumberPixels);
#~ -OK- unsigned int WINAPI ShamrockGetPixelWidth(int device, float* Width);
#~ -OK- unsigned int WINAPI ShamrockGetNumberPixels(int device, int* NumberPixels);
#~ -OK- unsigned int WINAPI ShamrockGetCalibration(int device, float* CalibrationValues, int NumberPixels);
#~ unsigned int WINAPI ShamrockGetPixelCalibrationCoefficients(int device, float* A, float* B, float* C, float* D);


#~ -OK- unsigned int WINAPI ShamrockSetWavelength(int device, float wavelength);
#~ -OK- unsigned int WINAPI ShamrockGetWavelength(int device, float *wavelength);
#~ -OK- unsigned int WINAPI ShamrockGotoZeroOrder(int device);
#~ -OK- unsigned int WINAPI ShamrockAtZeroOrder(int device, int *atZeroOrder);
#~ -OK- unsigned int WINAPI ShamrockGetWavelengthLimits(int device, int Grating, float *Min, float *Max);


ERROR_CODE = {
    20001: "DRV_ERROR_CODES",
    20002: "DRV_SUCCESS",
    20003: "DRV_VXNOTINSTALLED",
    20006: "DRV_ERROR_FILELOAD",
    20007: "DRV_ERROR_VXD_INIT",
    20010: "DRV_ERROR_PAGELOCK",
    20011: "DRV_ERROR_PAGE_UNLOCK",
    20013: "DRV_ERROR_ACK",
    20024: "DRV_NO_NEW_DATA",
    20026: "DRV_SPOOLERROR",
    20034: "DRV_TEMP_OFF",
    20035: "DRV_TEMP_NOT_STABILIZED",
    20036: "DRV_TEMP_STABILIZED",
    20037: "DRV_TEMP_NOT_REACHED",
    20038: "DRV_TEMP_OUT_RANGE",
    20039: "DRV_TEMP_NOT_SUPPORTED",
    20040: "DRV_TEMP_DRIFT",
    20050: "DRV_COF_NOTLOADED",
    20053: "DRV_FLEXERROR",
    20066: "DRV_P1INVALID",
    20067: "DRV_P2INVALID",
    20068: "DRV_P3INVALID",
    20069: "DRV_P4INVALID",
    20070: "DRV_INIERROR",
    20071: "DRV_COERROR",
    20072: "DRV_ACQUIRING",
    20073: "DRV_IDLE",
    20074: "DRV_TEMPCYCLE",
    20075: "DRV_NOT_INITIALIZED",
    20076: "DRV_P5INVALID",
    20077: "DRV_P6INVALID",
    20083: "P7_INVALID",
    20089: "DRV_USBERROR",
    20091: "DRV_NOT_SUPPORTED",
    20099: "DRV_BINNING_ERROR",
    20990: "DRV_NOCAMERA",
    20991: "DRV_NOT_SUPPORTED",
    20992: "DRV_NOT_AVAILABLE",

    20201: "SHAMROCK_COMMUNICATION_ERROR",
    20202: "SHAMROCK_SUCCESS",
    20266: "SHAMROCK_P1INVALID",
    20267: "SHAMROCK_P2INVALID",
    20268: "SHAMROCK_P3INVALID",
    20269: "SHAMROCK_P4INVALID",
    20270: "SHAMROCK_P5INVALID",
    20275: "SHAMROCK_NOT_INITIALIZED",
    20292: "SHAMROCK_NOT_AVAILABLE"
}








print 'Initializing Shamrock DLL...',
test = Shamrock()
test.verbosity = False
print 'Done. '
print

NRDEV = test.GetNumberDevicesSR()[1]
print "Number of Devices: ", NRDEV
NRGRA = test.GetNumberGratingsSR(0)[1]
print "Number of Gratings: ", NRGRA



print
print "Set Calibration... "
test.SetNumberPixelsSR(0, 1024)
test.SetPixelWidthSR(0, 26)
print "Get Calibration..."
PixNumber = test.GetNumberPixelsSR(0)[1]
PixWidth = test.GetPixelWidthSR(0)[1]
print '{} Pixels, width: {}'.format(PixNumber, PixWidth)
calib = test.GetCalibrationSR(0)
a = np.frombuffer(calib[1], dtype=np.dtype('f4')) # no copy. Changes in `a` are reflected in `Data`

## -----------
import matplotlib.pyplot as plt
plt.plot(a)
plt.xlabel("Nr of Pixel")
plt.ylabel("Calibration (Wavelength in nm)")
plt.show()
## -----------


print 'Done.'


print
G1 = test.GetGratingInfoSR(0,1)
G2 = test.GetGratingInfoSR(0,2)
WLlim1 = test.GetWavelengthLimitsSR(0,1)
WLlim2 = test.GetWavelengthLimitsSR(0,2)
print "Gra1: Lines {1}, Blaze {2}, Home {3}, Offset {4}".format(*G1)
print "Gra1: Wavelength limits: min {} / max {} (nm)".format(WLlim1[1], WLlim1[2])
print "Gra2: Lines {1}, Blaze {2}, Home {3}, Offset {4}".format(*G2)
print "Gra1: Wavelength limits: min {} / max {} (nm)".format(WLlim2[1], WLlim2[2])
print
CURGRA = test.GetGratingSR(0)[1]
print "Current Grating: ", CURGRA


print 
print 
print "Goto Zero order...",
test.GotoZeroOrderSR(0)
print 'Done.'

WL = test.GetWavelengthSR(0)[1]
print "Current Wavelength: {} nm".format(WL)
print "At 0 order? ", bool(test.AtZeroOrderSR(0)[1])

print
print 'setting wavelength...',
test.SetWavelengthSR(0, 500)
print 'done.'


WL = test.GetWavelengthSR(0)[1]
print "Current Wavelength: {} nm".format(WL)
print "At 0 order? ", bool(test.AtZeroOrderSR(0)[1])





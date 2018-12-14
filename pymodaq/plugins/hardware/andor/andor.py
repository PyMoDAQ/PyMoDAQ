import sys
import os
sys.path.append(os.path.split(__file__)[0])
from _andorsdk import AndorSDK

import time
import numpy as np
import matplotlib.pyplot as plt




class Andor():
    def __init__(self, targetT, Npixels, Wpixels, devNr=0, dllpath=""):
        """
        Init highlevel Andor Class.
        All Measurements in Full Vertical Binning (FVB).
        
        inputs:
          - targetT:    Target CCD Temperature (degrees C)
          - Npixels:    Number of Pixels on CCD
          - Wpixels:    Pixel Width of each Px on CCD (in microns)
          - devNr:      (optional) device number, if several installed. default = 0.
          - dllpath:    (optional) path to andor/shamrock DLLs. default = "".
        
        """
        self.Npixels = Npixels
        self.Wpixels = Wpixels
        self.devNr   = devNr
        self.dllpath = dllpath
        self.targetT = targetT
        
        self.ready       = False
        self.status      = ""
        self.Tstable     = False
        self.tempMsg     = ""
        self.temperature = 0
        self.calib       = []
        self.minLambda   = 0
        self.maxLambda   = 0
        self.atZeroOrder = False
        self.wavelength  = 0
        self.grating     = 0
        self.exposure    = 0
        self.accumulate  = 0
        self.kinetic     = 0
        self.wait_time   = 0
        self.lastData    = []
    
    
    def loadAndor(self):
        self.sdk = AndorSDK(dllpath=self.dllpath)
        
        ## Call init functions (get grating, wavelength, calibration...)
        self.device =  self.devNr
        self.setCCDConfig(self.Npixels, self.Wpixels)
        self.getGrating()
        self.gratingLines = self.getGratingInfo()[0]
        self.getWavelength()
        self.setExposureTime(0.1)
        self.getExposureTime()
        self.getStatus()
        
        self.sdk.SetReadMode(0)              # Full vert. binning
        
        self.setCooler(True)
        self.setTemperature(self.targetT)
        self.ready = True
        time.sleep(.1)
    
    
    def unloadAndor(self):
        del self.sdk
        self.ready = False
        time.sleep(.1)
    
    
    ####################################################################
    def _waitForAquisition(self, verbose=False):
        while self.getStatus() in ["DRV_ACQUIRING", 
                   "DRV_KINETIC_TIME_NOT_MET","DRV_ERROR_ACK", 
                   "DRV_ACQ_BUFFER", "DRV_TIME_NOT_MET"]:
            if verbose: print("not finished, waiting...")
            time.sleep(0.001)
    
    ## ---
    def setCCDConfig(self, Npixels, Wpixels):
        self.sdk.SetNumberPixelsSR(self.devNr, 1024)
        self.sdk.SetPixelWidthSR(self.devNr, 26)
        self.getCalibration()
        
    def getCalibration(self):
        _calib = self.sdk.GetCalibrationSR(self.devNr)
        self.calib = np.frombuffer(_calib[1], dtype=np.dtype('f4'))
        self.minLambda = self.calib.min()
        self.maxLambda = self.calib.max()
        return self.calib
    
    
    ## ---
    def setWavelength(self, targetWL):
        self._waitForAquisition()
        self.sdk.SetWavelengthSR(self.devNr, targetWL)
        self.getCalibration()
        self.getWavelength()
    
    def getWavelength(self):
        self.wavelength = self.sdk.GetWavelengthSR(self.devNr)[1]
        self.atZeroOrder = self.sdk.AtZeroOrderSR(self.devNr)[1]
        return self.wavelength
    
    
    ## ---
    def setGrating(self, gratingNr):
        self._waitForAquisition()
        self.sdk.SetGratingSR(self.devNr, gratingNr)
        self.getCalibration()
        self.getGrating()
        self.gratingLines = self.getGratingInfo()[0]
    
    def getGrating(self):
        self.grating = self.sdk.GetGratingSR(self.devNr)[1]
        return self.grating
    
    def getGratingInfo(self, gratingNr=-1):
        if gratingNr == -1: gratingNr = self.grating
        Lines, Blaze, Home, Offset = self.sdk.GetGratingInfoSR(self.devNr, gratingNr)[1:]
        return Lines, Home, Offset
    
    
    ## ---
    def setCooler(self, state):
        self._waitForAquisition()
        if state:
            self.sdk.SetCoolerMode(1)
            self.sdk.CoolerON()
        else:
            self.sdk.CoolerOFF()
    
    def setTemperature(self, targetT):
        self.setCooler(False)
        self.sdk.SetTemperature(int(targetT))
        self.setCooler(True)
        self.getTemperature()
    
    def getTemperature(self):
        MSG, T = self.sdk.GetTemperature()
        if MSG == 'DRV_TEMP_STABILIZED':
            self.Tstable = True
        else:
            self.Tstable = False
        self.tempMsg = MSG
        self.temperature = T
        return self.temperature
    
    
    ## ---
    def setExposureTime(self, exposure):
        self._waitForAquisition()
        self.sdk.SetExposureTime(exposure)
        self.getExposureTime()
    
    def getExposureTime(self):
        self.sdk.GetAcquisitionTimings()
        
        self.exposure = self.sdk._exposure
        self.accumulate = self.sdk._accumulate
        self.kinetic = self.sdk._kinetic
        self.wait_time = self.exposure + 0.02# + self.accumulate + self.kinetic + 0.05
        return self.exposure
    
    
    ## ---
    def getStatus(self):
        self.status = self.sdk.GetStatus()
        return self.status
    
    
    ## ---
    def startAquisition(self):
        self.sdk.StartAcquisition()
    
    
    def getAquisition(self, verbose=False):
        self._waitForAquisition(verbose)
        self.lastData = self.sdk.GetAcquiredData([])
        return np.array(self.lastData)
    







########################################################################
if __name__ == "__main__":
    andorTest = Andor(targetT=-20, Npixels=1024, Wpixels=26, devNr=0, dllpath="")
    for i in range(2):
        print("     Ready: ",andorTest.ready)
        andorTest.loadAndor()
        print( "     Ready: ",andorTest.ready)
        
        print(andorTest.grating)
        print( andorTest.getGratingInfo())
        print( andorTest.wavelength)
        print( andorTest.getStatus())
        print( '-----')
        print( andorTest.getTemperature())
        print( andorTest.tempMsg)
        print( '-----')
        
        andorTest.setExposureTime(0.1)
        print( "Total expected time per measurement (s):", andorTest.wait_time)
        plt.ion()
        for i in range(20):
            andorTest.startAquisition()
            DATA = andorTest.getAquisition()
            print( " T:", andorTest.getTemperature(), ' ({})'.format(andorTest.tempMsg))
            
            plt.clf()
            plt.title("MEASUREMENT #{}".format(i+1))
            plt.plot(andorTest.calib, DATA)
            plt.draw()
            plt.pause(.01)
        plt.ioff()
        plt.show()
        
        print( "     Ready: ",andorTest.ready)
        print( 30*"-" + "\nUNLOAD ANDOR...\n\n\n\n" + 30*"-")
        andorTest.unloadAndor()
        print( "     Ready: ",andorTest.ready)
        











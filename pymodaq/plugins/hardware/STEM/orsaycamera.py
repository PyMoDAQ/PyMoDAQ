"""
Class controlling orsay scan hardware.
"""
import sys
from ctypes import cdll, create_string_buffer, POINTER, byref
from ctypes import c_uint, c_int, c_char, c_char_p, c_void_p, c_short, c_long, c_bool, c_double, c_uint64, c_uint32, Array, CFUNCTYPE, WINFUNCTYPE
from ctypes import c_ushort, c_ulong, c_float
import os

__author__  = "Marcel Tence"
__status__  = "alpha"
__version__ = "0.1"

def _isPython3():
    return sys.version_info[0] >= 3

def _buildFunction(call, args, result):
    call.argtypes = args
    call.restype = result
    return call

def _createCharBuffer23(size):
    if (_isPython3()):
        return create_string_buffer(b'\000' * size)
    return create_string_buffer('\000' * size)

def _convertToString23(binaryString):
    if (_isPython3()):
        return binaryString.decode("utf-8")
    return binaryString

def _toString23(string):
    if (_isPython3()):
        return string.encode("utf-8")
    return string

# library must be in the same folder as this file.
if (sys.maxsize > 2**32):
    libname = os.path.dirname(__file__)
    libname = os.path.join(libname, "Cameras.dll")
    _library = cdll.LoadLibrary(libname)
    #print(f"OrsayCamera library: {_library}")
else:
    raise Exception("It must a python 64 bit version")

LOGGERFUNC = WINFUNCTYPE(None, c_char_p, c_bool)
#	void CAMERAS_EXPORT *OrsayCamerasInit(int manufacturer, const char *model, void(*logger)(const char *buf, bool debug), bool simul);
_OrsayCameraInit = _buildFunction(_library.OrsayCamerasInit, [c_int, c_char_p, c_char_p, LOGGERFUNC, c_bool], c_void_p)
#void CAMERAS_EXPORT OrsayCamerasClose(void* o);
_OrsayCameraClose = _buildFunction(_library.OrsayCamerasClose, [c_void_p], None)
#_OrsayCamera = _buildFunction(_library., [c_void_p, ], )

#void CAMERAS_EXPORT RegisterLogger(void *o, void(*logger)(const char *, bool));
_OrsayCameraRegisterLogger = _buildFunction(_library.RegisterLogger, [c_void_p, LOGGERFUNC], None)
#void CAMERAS_EXPORT RegisterDataLocker(void * o, void *(*LockDataPointer)(int cam,  int *datatype, int *sx, int *sy, int *sz));
DATALOCKFUNC = WINFUNCTYPE(c_void_p, c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(c_int))
_OrsayCameraRegisterDataLocker = _buildFunction(_library.RegisterDataLocker, [c_void_p, DATALOCKFUNC], None)
#void CAMERAS_EXPORT RegisterDataUnlocker(void *o, void(*UnLockDataPointer)(int cam, bool newdata));
DATAUNLOCKFUNC = WINFUNCTYPE(None, c_int, c_bool)
_OrsayCameraRegisterDataUnlocker = _buildFunction(_library.RegisterDataUnlocker, [c_void_p, DATAUNLOCKFUNC], None)
#void CAMERAS_EXPORT RegisterSpimDataLocker(void *o, void(*LockSpimDataPointer)(int cam, int *datatype, int *sx, int *sy, int *sz));
SPIMLOCKFUNC = WINFUNCTYPE(c_void_p, c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(c_int))
_OrsayCameraRegisterSpimDataLocker = _buildFunction(_library.RegisterSpimDataLocker, [c_void_p, SPIMLOCKFUNC], None)
#void CAMERAS_EXPORT RegisterSpimDataUnlocker(void *o, void *(*UnLockSpimDataPointer)(int cam, bool newdata, bool running));
SPIMUNLOCKFUNC = WINFUNCTYPE(None, c_int, c_bool, c_bool)
_OrsayCameraRegisterSpimDataUnlocker = _buildFunction(_library.RegisterSpimDataUnlocker, [c_void_p, SPIMUNLOCKFUNC], None)
#//void ** (*LockOnlineSpimDataPointer)(void *o, short cam, short *datatype, short *sx, short *sy, short *sz);
#//void(*UnLockOnlineSpimDataPointer)(void *o, int cam, bool newdata, bool running);
#void CAMERAS_EXPORT RegisterSpectrumDataLocker(void *o, void *(*LockSpectrumDataPointer)(int cam, int *datatype, int *sx));
SPECTLOCKFUNC = WINFUNCTYPE(c_void_p, c_int, POINTER(c_int), POINTER(c_int))
_OrsayCameraRegisterSpectrumDataLocker = _buildFunction(_library.RegisterSpectrumDataLocker, [c_void_p, SPECTLOCKFUNC], None)
#void CAMERAS_EXPORT RegisterSpectrumDataUnlocker(void *o, void(*UnLockSpectrumDataPointer)(int cam, bool newdata));
SPECTUNLOCKFUNC = WINFUNCTYPE(None, c_int, c_bool)
_OrsayCameraRegisterSpectrumDataUnlocker = _buildFunction(_library.RegisterSpectrumDataUnlocker, [c_void_p, SPECTUNLOCKFUNC], None)
#void CAMERAS_EXPORT RegisterSpimUpdateInfo(void *o, void(*UpdateSpimInfo)(unsigned long currentspectrum, bool running));
SPIMUPDATEFUNC = WINFUNCTYPE(None, c_int, c_bool)
_OrsayCameraRegisterSpimUpdateLocker = _buildFunction(_library.RegisterSpimUpdateInfo, [c_void_p, SPIMUPDATEFUNC], None)

#bool CAMERAS_EXPORT init_data_structures(void *o);
_OrsayCameraInit_data_structures = _buildFunction(_library.init_data_structures, [c_void_p], c_bool)

#void CAMERAS_EXPORT GetCCDSize(void *o, long *sx, long *sy);
_OrsayCameraGetCCDSize = _buildFunction(_library.GetCCDSize, [c_void_p, POINTER(c_long), POINTER(c_long)], None)
#void CAMERAS_EXPORT GetImageSize(void *o, long *sx, long *sy);
_OrsayCameraGetImageSize = _buildFunction(_library.GetImageSize, [c_void_p, ], None)

#//myrgn_type GetArea(void *o, );
#//bool SetArea(void *o, myrgn_type rg);
#void CAMERAS_EXPORT SetCCDOverscan(void *o, int x, int y);
_OrsayCameraSetCCDOverscan = _buildFunction(_library.SetCCDOverscan, [c_void_p, c_int, c_int], None)
#void CAMERAS_EXPORT DisplayOverscan(void *o, bool on);
_OrsayCameraDisplayOverscan = _buildFunction(_library.DisplayOverscan, [c_void_p, c_bool], None)
#void CAMERAS_EXPORT GetBinning(void *o, unsigned short *bx, unsigned short *by);
_OrsayCameraGetBinning = _buildFunction(_library.GetBinning, [c_void_p, POINTER(c_ushort), POINTER(c_ushort)], None)
#bool CAMERAS_EXPORT SetBinning(void *o, unsigned short bx, unsigned short by, bool estimatedark = true);
_OrsayCameraSetBinning = _buildFunction(_library.SetBinning, [c_void_p, c_ushort, c_ushort, c_bool], c_bool)
#void CAMERAS_EXPORT SetMirror(void *o, bool On);
_OrsayCameraSetMirror = _buildFunction(_library.SetMirror, [c_void_p, c_bool], None)
#void CAMERAS_EXPORT SetNbCumul(void *o, long n);
_OrsayCameraSetNbCumul = _buildFunction(_library.SetNbCumul, [c_void_p, c_long], None)
#long CAMERAS_EXPORT GetNbCumul(void *o);
_OrsayCameraGetNbCumul = _buildFunction(_library.GetNbCumul, [c_void_p], c_long)
#void CAMERAS_EXPORT SetSpimMode(void *o, unsigned short mode);
_OrsayCameraSetSpimMode = _buildFunction(_library.SetSpimMode, [c_void_p, c_ushort], None)
#bool CAMERAS_EXPORT StartSpim(void *o, unsigned long nbSpectra, unsigned long nbsp, float pose, bool saveK);
_OrsayCameraStartSpim = _buildFunction(_library.StartSpim, [c_void_p, c_ulong, c_ulong, c_float, c_bool], c_bool)
#bool CAMERAS_EXPORT ResumeSpim(void *o, int mode);
_OrsayCameraResumeSpim = _buildFunction(_library.ResumeSpim, [c_void_p, c_int], c_bool)
#bool CAMERAS_EXPORT PauseSpim(void *o);
_OrsayCameraPauseSpim = _buildFunction(_library.PauseSpim, [c_void_p], c_bool)
#bool CAMERAS_EXPORT StopSpim(void *o, bool endofline = false);
_OrsayCameraStopSpim = _buildFunction(_library.StopSpim, [c_void_p, c_bool], c_bool)

#void CAMERAS_EXPORT DisplayCCDInfos(void *o, char *filter);
_OrsayCameraDisplayCCDInfos = _buildFunction(_library.DisplayCCDInfos, [c_void_p, c_char_p], None)
#bool CAMERAS_EXPORT isCameraThere(void *o);
_OrsayCameraIsCameraThere = _buildFunction(_library.isCameraThere, [c_void_p], c_bool)
#bool CAMERAS_EXPORT GetTemperature(void *o, float *temperature, bool *status);
_OrsayCameraGetTemperature = _buildFunction(_library.GetCameraTemperature, [c_void_p, POINTER(c_float), POINTER(c_bool)], c_bool)
#bool CAMERAS_EXPORT SetTemperature(void *o, float temperature);
_OrsayCameraSetTemperature = _buildFunction(_library.SetCameraTemperature, [c_void_p, c_float], c_bool)
#bool CAMERAS_EXPORT SetupBinning(void *o);
_OrsayCameraSetupBinning = _buildFunction(_library.SetupBinning, [c_void_p], c_bool)
#bool CAMERAS_EXPORT StartFocus(void *o, float pose, short display, short accumulate);
_OrsayCameraStartFocus = _buildFunction(_library.StartFocus, [c_void_p, c_float, c_short, c_short], c_bool)
#bool CAMERAS_EXPORT StopFocus(void *o);
_OrsayCameraStopFocus = _buildFunction(_library.StopFocus, [c_void_p],c_bool )
#bool CAMERAS_EXPORT SetExposureTime(void *o, double pose);
_OrsayCameraSetExposureTime = _buildFunction(_library.SetCameraExposureTime, [c_void_p, c_double], c_bool)
#bool CAMERAS_EXPORT StartDarkCalibration(void *o, long numofimages);
#_OrsayCameraStartDarkCalibration = _buildFunction(_library.StartDarkCalibration, [c_void_p, c_long], c_bool)
#long CAMERAS_EXPORT GetNumOfSpeed(void *o, short p);
_OrsayCameraGetNumOfSpeed = _buildFunction(_library.GetNumOfSpeed, [c_void_p, c_int], c_long)
#long CAMERAS_EXPORT GetCurrentSpeed(void *o, short p);
_OrsayCameraGetCurrentSpeed = _buildFunction(_library.GetCurrentSpeed, [c_void_p, c_short], c_long)
#long CAMERAS_EXPORT SetSpeed(void *o, short p, long n);
_OrsayCameraSetSpeed = _buildFunction(_library.SetSpeed, [c_void_p, c_short, c_long], c_long)
#int CAMERAS_EXPORT GetNumOfGains(void *o, int p);
_OrsayCameraGetNumOfGains = _buildFunction(_library.GetNumOfGains, [c_void_p, c_int], c_int)
#const char CAMERAS_EXPORT *GetGainName(void *o, int p, int g);
_OrsayCameraGetGainName = _buildFunction(_library.GetGainName, [c_void_p, c_int, c_int], c_char_p)
#bool CAMERAS_EXPORT SetGain(void *o, short newgain);
_OrsayCameraSetGain = _buildFunction(_library.SetGain, [c_void_p, c_short], c_bool)
#short CAMERAS_EXPORT GetGain(void *o);
_OrsayCameraGetGain = _buildFunction(_library.GetGain, [c_void_p], c_short)
#double CAMERAS_EXPORT GetReadOutTime(void *o);
_OrsayCameraGetReadOutTime = _buildFunction(_library.GetReadOutTime, [c_void_p], c_double)
#long CAMERAS_EXPORT GetNumOfPorts(void *o);
_OrsayCameraGetNumOfPorts = _buildFunction(_library.GetNumOfPorts, [c_void_p], c_long)
#const char CAMERAS_EXPORT *GetPortName(void *o, long nb);
_OrsayCameraGetPortName = _buildFunction(_library.GetPortName, [c_void_p, c_long], c_char_p)
#long CAMERAS_EXPORT GetCurrentPort(void *o);
_OrsayCameraGetCurrentPort = _buildFunction(_library.GetCurrentPort, [c_void_p], c_long)
#bool CAMERAS_EXPORT SetCameraPort(void *o, long n);
_OrsayCameraSetCameraPort = _buildFunction(_library.SetCameraPort, [c_void_p, c_long], c_bool)
#unsigned short CAMERAS_EXPORT GetMultiplication(void *o, unsigned short *pmin, unsigned short *pmax);
_OrsayCameraGetMultiplication = _buildFunction(_library.GetMultiplication, [c_void_p, POINTER(c_ushort), POINTER(c_ushort)], c_ushort)
#void CAMERAS_EXPORT SetMultiplication(void *o, unsigned short mult);
_OrsayCameraSetMultiplication = _buildFunction(_library.SetMultiplication, [c_void_p, c_ushort], None)
#void CAMERAS_EXPORT getCCDStatus(void *o, short *mode, double *p1, double *p2, double *p3, double *p4);
_OrsayCameragetCCDStatus = _buildFunction(_library.getCCDStatus, [c_void_p, POINTER(c_short), POINTER(c_double), POINTER(c_double), POINTER(c_double), POINTER(c_double)], None)
#double CAMERAS_EXPORT GetReadoutSpeed(void *o);
_OrsayCameraGetReadoutSpeed = _buildFunction(_library.GetReadoutSpeed, [c_void_p], c_double)
#long CAMERAS_EXPORT GetPixelTime(void *o, short p, short v);
_OrsayCameraGetPixelTime = _buildFunction(_library.GetPixelTime, [c_void_p, c_short, c_short], c_long)
#void CAMERAS_EXPORT AdjustOverscan(void *o, int sx, int sy);
_OrsayCameraAdjustOverscan = _buildFunction(_library.AdjustOverscan, [c_void_p, c_int, c_int], None)
#void CAMERAS_EXPORT SetTurboMode(void *o, int active, short horizontalsize, short verticalsize);
_OrsayCameraSetTurboMode = _buildFunction(_library.SetTurboMode, [c_void_p, c_short, c_short, c_short], None)
#int CAMERAS_EXPORT GetTurboMode(void *o, short *horizontalsize, short *verticalsize);
_OrsayCameraGetTurboMode = _buildFunction(_library.GetTurboMode, [c_void_p, POINTER(c_short), POINTER(c_short)], c_int)
#bool CAMERAS_EXPORT SetExposureMode(void *o, short mode, short edge);
_OrsayCameraSetExposureMode = _buildFunction(_library.SetExposureMode, [c_void_p, c_short, c_short], c_bool)
#short CAMERAS_EXPORT GetExposureMode(void *o, short *edge);
_OrsayCameraGetExposureMode = _buildFunction(_library.GetExposureMode, [c_void_p, POINTER(c_short)], c_short)
#bool CAMERAS_EXPORT SetPulseMode(void *o, short mode);
_OrsayCameraSetPulseMode = _buildFunction(_library.SetPulseMode, [c_void_p, c_int], c_bool)
#bool CAMERAS_EXPORT SetVerticalShift(void *o, double shift, int clear);
_OrsayCameraSetVerticalShift = _buildFunction(_library.SetVerticalShift, [c_void_p, c_double, c_int], c_bool)
#bool CAMERAS_EXPORT SetFan(void *o, bool OnOff);
_OrsayCameraSetFan = _buildFunction(_library.SetFan, [c_void_p, c_bool], c_bool)
#bool CAMERAS_EXPORT GetFan(void *o);
_OrsayCameraGetFan = _buildFunction(_library.GetFan, [c_void_p], c_bool)

class orsayCamera(object):
    """Class controlling orsay camera class
       Requires Cameras.dll library to run.
    """
    def close(self):
        _OrsayCameraClose(self.orsaycamera)
        self.orsaycamera = None
    def __logger(self, message, debug):
#        print(f"log: {_convertToString23(message)}")
        pass
    def __init__(self, manufacturer, model, sn, simul):
        self.manufacturer = manufacturer
        self.fnlog = LOGGERFUNC(self.__logger)

        modelb = _toString23(model)
        self.orsaycamera = _OrsayCameraInit(manufacturer, modelb,  _toString23(sn), self.fnlog, simul)
        if not self.orsaycamera:
            raise Exception ("Camera not created")
        if not _OrsayCameraInit_data_structures(self.orsaycamera):
            raise Exception ("Camera not initialised properly")
#        print(f"Camera: {_OrsayCameraIsCameraThere(self.orsaycamera)}")
        self.setFan(0)
        #print("*** Put Fan on as temporary situation (no water in camera at the moment ***")

    def registerLogger(self, fn):
        "Replaces the original logger function"
        _OrsayCameraRegisterLogger(fn)

    def getImageSize(self):
        "Read size of image given by the current setting"
        sx = c_long()
        sy = c_long()
        _OrsayCameraGetImageSize(self.orsaycamera, byref(sx), byref(sy))
        return sx.value, sy.value

    def getCCDSize(self):
        "Size of the camera ccd chip"
        sx = c_long()
        sy = c_long()
        _OrsayCameraGetCCDSize(self.orsaycamera, byref(sx), byref(sy))
        return sx.value, sy.value

    def registerDataLocker(self, fn):
        "Function called to get data storage for a frame by frame readout"
        _OrsayCameraRegisterDataLocker(self.orsaycamera, fn)

    def registerDataUnlocker(self, fn):
        "Function called when data process is done for a frame by frame readout"
        _OrsayCameraRegisterDataUnlocker(self.orsaycamera, fn)

    def registerSpimDataLocker(self, fn):
       "Function called to get data storage for a spectrum image readout"
       _OrsayCameraRegisterSpimDataLocker(self.orsaycamera, fn)

    def registerSpimDataUnlocker(self, fn):
        "Function called when data process is done for a spectrum image readout"
        _OrsayCameraRegisterSpimDataUnlocker(self.orsaycamera, fn)

    def registerSpectrumDataLocker(self, fn):
       "Function called to get data storage for the current spectrum in spim readout"
       _OrsayCameraRegisterSpectrumDataLocker(self.orsaycamera, fn)

    def registerSpectrumDataUnlocker(self, fn):
        "Function called when data process is done he current spectrum in spim readout"
        _OrsayCameraRegisterSpectrumDataUnlocker(self.orsaycamera, fn)

    def setCCDOverscan(self, sx, sy):
        "For roper camera changes the size of the chip artificially to do online baseline correction (should 0,0 or 128,0)"
        _OrsayCameraSetCCDOverscan(self.orsaycamera, sx, sy)

    def displayOverscan(self, displayed):
        "When displayed set, the overscan area is displayed, changing image/spectrum size"
        _OrsayCameraDisplayOverscan(self.orsaycamera, displayed)

    def getBinning(self):
        "Return horizontal, vertical binning"
        bx = c_ushort(1)
        by = c_ushort(1)
        _OrsayCameraGetBinning(self.orsaycamera, byref(bx), byref(by))
        return bx.value, by.value

    def setBinning(self, bx, by):
        "Set  horizontal, vertical binning"
        _OrsayCameraSetBinning(self.orsaycamera, bx, by, 0)

    def setMirror(self, mirror):
        "If mirror true, horizontal data are flipped"
        _OrsayCameraSetMirror(self.orsaycamera, mirror)

    def setAccumulationNumber(self, count):
        "Define the number of images/spectra to sum (change to a property?"
        _OrsayCameraSetNbCumul(self.orsaycamera, count)

    def getAccumulateNumber(self):
        "Return the number of images/spectra to sum (change to a property?"
        return _OrsayCameraGetNbCumul(self.orsaycamera)

    def setSpimMode(self, mode):
        "Set the spim operating mode: 0:SPIMSTOPPED, 1:SPIMRUNNING, 2:SPIMPAUSED, 3:SPIMSTOPEOL, 4:SPIMSTOPEOF, 5:SPIMONLINE"
        _OrsayCameraSetSpimMode(self.orsaycamera, mode)

    def startSpim(self, nbspectra, nbspectraperpixel, dwelltime, is2D):
        "Start spectrum imaging acquisition"
        _OrsayCameraStartSpim(self.orsaycamera, nbspectra, nbspectraperpixel, dwelltime, c_bool(is2D))

    def pauseSpim(self):
        "Pause spectrum imaging acquisition"
        _OrsayCameraPauseSpim(self.orsaycamera)

    def resumeSpim(self, mode):
        "Resume spectrum imaging acquisition with mode: 0:SPIMSTOPPED, 1:SPIMRUNNING, 2:SPIMPAUSED, 3:SPIMSTOPEOL, 4:SPIMSTOPEOF, 5:SPIMONLINE"
        _OrsayCameraResumeSpim(self.orsaycamera, mode)

    def stopSpim(self, immediate):
        return _OrsayCameraStopSpim(self.orsaycamera, immediate)

    def isCameraThere(self):
        "Check if the camera exists"
        return _OrsayCameraGetTemperature(self.orsaycamera)

    def getTemperature(self):
        "Read ccd temperature and locked status"
        temperature = c_float()
        status = c_bool()
        res = _OrsayCameraGetTemperature(self.orsaycamera, byref(temperature), byref(status))
        return temperature.value, status.value

    def setTemperature(self, temperature):
        "Set the ccd temperature target point"
        _OrsayCameraSetTemperature(self.orsaycamera, temperature)

    def setupBinning(self):
        "Adjust binning using all current parameters and load it to camera - probably obsolete now"
        _OrsayCameraSetupBinning(self.orsaycamera)

    def startFocus(self, exposure, displaymode, accumulate):
        "Start imaging displaymode: 1d, 2d  accumulate if images/spectra have to be summed"
        mode = 0
        if (displaymode == "1d"):
            mode = 1
        return _OrsayCameraStartFocus(self.orsaycamera, exposure, mode, accumulate)

    def stopFocus(self):
        "Stop imaging"
        return _OrsayCameraStopFocus(self.orsaycamera)

    def setExposureTime(self, exposure):
        "Defines exposure time, usefull to get then frame rate including readout time"
        _OrsayCameraSetExposureTime(self.orsaycamera, exposure)

    def getNumofSpeeds(self, cameraport):
        "Find the number of speeds available for a specific readout port, they can be port dependant on some cameras"
        return  _OrsayCameraGetNumOfSpeed(self.orsaycamera, cameraport)

    def getSpeeds(self, cameraport):
        "Return the list of speeds for the cameraport as strings"
        nbspeeds = self.getNumofSpeeds(cameraport)
        speeds = list()
        for s in range(nbspeeds):
            pixeltime = self.getPixelTime(cameraport, s)
            speed = 1000 / pixeltime
            if speed < 1:
                speeds.append(str(1000000 / pixeltime) + " KHz")
            else:
                speeds.append(str(speed) + " MHz")
        return speeds

    def getCurrentSpeed(self, cameraport):
        "Find the speed used"
        if isinstance(cameraport, int):
            return _OrsayCameraGetCurrentSpeed(self.orsaycamera, c_short(cameraport))
        else:
            return 0

    def getAllPortsParams(self):
        "Find the list of speeds por all ports return a tuple of (port name, (speeds,), (gains,)"
        cp = self.getCurrentPort()
        nbports = self.getNumofPorts()
        allportsparams = ()
        for p in range(nbports):
            #self.setCurrentPort(p)
            portparams = (self.getPortName(p),)
            nbspeeds = self.getNumofSpeeds(p)
            speeds = ()
            #roperscientific gives pixel time in nanoseconds.
            for s in range(nbspeeds):
                #self.setSpeed(p, s)
                pixeltime = self.getPixelTime(p, s)
                speed = 1000 / pixeltime
                if speed < 1:
                    speed = str(1000000 /pixeltime) + " KHz"
                else:
                    speed = str(speed) + " MHz"
                speeds = speeds + (speed,)
            portparams = portparams + (speeds,)
            nbgains = self.getNumofGains(p)
            gains = ()
            for g in range(nbgains):
                gains = gains + ((self.getGainName(p, g), self.getGain(p)),)
            portparams = portparams + (gains,)
            allportsparams = allportsparams + (portparams,)
        return allportsparams

    def setSpeed(self, cameraport, speed):
        "Select speed used on this port"
        return _OrsayCameraSetSpeed(self.orsaycamera, cameraport, speed)

    def getNumofGains(self, cameraport):
        "Find the number of gains available for a specific readout port, they can be port dependant on some cameras"
        return  _OrsayCameraGetNumOfGains(self.orsaycamera, cameraport)

    def getGains(self, cameraport):
        "Return the list of gains for the cameraport as strings"
        nbgains = self.getNumofGains(cameraport)
        gains = list()
        for g in range(nbgains):
            gains.append(self.getGainName(cameraport, g))
        return gains

    def getGain(self, cameraport):
        "Find the speed used"
        return _OrsayCameraGetGain(self.orsaycamera, cameraport)

    def getGainName(self, cameraport, gain):
        "Get the label of the gain (low/Medium/High for instance"
        return _convertToString23(_OrsayCameraGetGainName(self.orsaycamera, cameraport, gain))

    def setGain(self, gain):
        "Select speed used on this port"
        res = _OrsayCameraSetGain(self.orsaycamera, gain)
        return res

    def getGain(self, cameraport):
        "Find the speed used"
        return _OrsayCameraGetGain(self.orsaycamera, cameraport)

    def getReadoutTime(self):
        "Find the time added after exposure in order to read the device, if not blanked it is added to expsue time"
        return _OrsayCameraGetReadOutTime(self.orsaycamera)

    def getNumofPorts(self):
        "Find the number of cameras ports"
        return _OrsayCameraGetNumOfPorts(self.orsaycamera)

    def getPortName(self, portnb):
        "Find the label of the camera port"
        return _convertToString23(_OrsayCameraGetPortName(self.orsaycamera, portnb))

    def getPortNames(self):
        "Find the label of the camera port"
        nbports = self.getNumofPorts()
        ports = ()
        k = 0
        while k < nbports:
            ports = ports + (_convertToString23(_OrsayCameraGetPortName(self.orsaycamera, k)),)
            k = k + 1
        return ports

    def getCurrentPort(self):
        "Returns the current port number"
        return _OrsayCameraGetCurrentPort(self.orsaycamera)

    def setCurrentPort(self, cameraport):
        "Choose the current port"
        if isinstance(cameraport, int):
            return _OrsayCameraSetCameraPort(self.orsaycamera, c_long(cameraport))
        else:
            print("cameraport not an integer")
            return False

    def getMultiplication(self):
        "Returns the multiplication value minvalue and maxvalue of the EMCCD port"
        minval = c_ushort()
        maxval = c_ushort()
        val = _OrsayCameraGetMultiplication(self.orsaycamera, byref(minval), byref(maxval))
        return val, minval.value, maxval.value

    def setMultiplication(self, multiplication):
        "Set the multiplication value of the EMCCD port"
        _OrsayCameraSetMultiplication(self.orsaycamera, multiplication)

    def getCCDStatus(self):
        "Returns the status of the acquisition"
        mode = c_short()
        p1 = c_double()
        p2 = c_double()
        p3 = c_double()
        p4 = c_double()
        _OrsayCameragetCCDStatus(self.orsaycamera, byref(mode), byref(p1), byref(p2), byref(p3), byref(p4))
        mode = mode.value
        if (mode == 0):
            return "idle", "actual temp", p1.value, "target temp", p2.value
        if (mode == 1):
            return "focus", p1.value, "frames/seconds"
        if(mode == 6):
            return "Spectrum imaging", "current spectrum", p1.value, "total spectra", p2.value

    def getReadoutSpeed(self):
        "Return expected frame rate"
        return _OrsayCameraGetReadoutSpeed(self.orsaycamera)

    def getPixelTime(self, cameraport, speed):
        "Returns time to shift a pixel for a specific port and speed"
        return _OrsayCameraGetPixelTime(self.orsaycamera, cameraport, speed)

    def adjustOverscan(self, sizex, sizey):
        "Extend the size of the cdd chip - tested only on horizontal axis"
        _OrsayCameraAdjustOverscan(self.orsaycamera, sizex, sizey)

    def setTurboMode(self, active, sizex, sizey):
        "Roper specific - fast and ultra high speed readout"
        _OrsayCameraSetTurboMode(self.orsaycamera, active, sizex, sizey)

    def getTurboMode(self):
        "Roper specific - fast and ultra high speed readout"
        sx = c_short()
        sy = c_short()
        res = _OrsayCameraGetTurboMode(self.orsaycamera, byref(sx), byref(sy))
        return res, sx.value, sy.value

    def setExposureMode(self, mode, edge):
        "Defines exposure trigger (slave/master), and edge polarity if used"
        return _OrsayCameraSetExposureMode(self.orsaycamera, mode, edge).value

    def getExposureMode(self):
        "Get exposure trigger (slave/master), and edge polarity if used"
        trigger = c_short()
        res = _OrsayCameraGetExposureMode(self.orsaycamera, byref(trigger)).value
        return res, trigger.value

    def setPulseMode(self, mode):
        "Defines what pulses comes out from camera"
        return _OrsayCameraSetPulseMode(self.orsaycamera, mode).value

    def setVerticalShift(self, shift, clear):
        "Defines shift rate and number of cleans"
        return _OrsayCameraSetVerticalShift(self.orsaycamera, shift, clear).value

    def setFan(self, On_Off):
        "Turns the camera fan on and off"
        return _OrsayCameraSetFan(self.orsaycamera, On_Off)

    def getFan(self):
        "Turns the camera fan on and off"
        return _OrsayCameraGetFan(self.orsaycamera)

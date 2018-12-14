# standard libraries
import ctypes
import gettext
import numpy
import threading
import typing

# third party libraries
from . import orsaycamera

# local libraries
from nion.data import Calibration
from nion.swift.model import HardwareSource
from nion.utils import Registry

from nion.instrumentation import camera_base

_ = gettext.gettext

STEM_CONTROLLER_ID = "autostem_controller"

class Camera(camera_base.Camera):

    def __init__(self, manufacturer, model):
        self.__config_dialog_handler = None
        self.camera = orsaycamera.orsayCamera(manufacturer, model, "", False)
        self.__sensor_dimensions = self.camera.getCCDSize()
        self.__readout_area = 0, 0, *self.__sensor_dimensions
        self.__orsay_binning = self.camera.getBinning()
        self.sizex, self.sizey = self.camera.getImageSize()
        self.sizez = 0

        # register data locker for focus acquisition
        self.fnlock = orsaycamera.DATALOCKFUNC(self.__data_locker)
        self.camera.registerDataLocker(self.fnlock)
        self.fnunlock = orsaycamera.DATAUNLOCKFUNC(self.__data_unlocker)
        self.camera.registerDataUnlocker(self.fnunlock)
        self.imagedata = None
        self.imagedata_ptr = None
        self.has_data_event = threading.Event()

        # register data locker for SPIM acquisition
        self.fnspimlock = orsaycamera.SPIMLOCKFUNC(self.__spim_data_locker)
        self.camera.registerSpimDataLocker(self.fnspimlock)
        self.fnspimunlock = orsaycamera.SPIMUNLOCKFUNC(self.__spim_data_unlocker)
        self.camera.registerSpimDataUnlocker(self.fnspimunlock)
        self.spimimagedata = None
        self.spimimagedata_ptr = None
        self.has_spim_data_event = threading.Event()

        self.twoD = "2d"
        self.__exposure_s = 0.010
        self.__orsay_exposure_ms = 10
        self.camera.setExposureTime(self.__orsay_exposure_ms / 1000)
        self.__frame_number = 0

        self.__acqon = False

        self.acquisition_mode = "Focus"
        self.nbspectra = 1

        self.autostem = HardwareSource.HardwareSourceManager().get_instrument_by_id(STEM_CONTROLLER_ID)

    def close(self):
        self.camera.stopSpim(True)
        #self.camera.close()

    def __data_locker(self, gene, datatype, sx, sy, sz):
        sx[0] = self.sizex
        sy[0] = self.sizey
        sz[0] = 1
        datatype[0] = 11
        return self.imagedata_ptr.value

    def __data_unlocker(self, gene, newdata):
        self.__frame_number += 1
        self.has_data_event.set()

    def __spim_data_locker(self, gene, datatype, sx, sy, sz):
        sx[0] = self.sizex
        sy[0] = self.sizey
        sz[0] = self.sizez
        datatype[0] = 100 + 11
        #print(f"spim lock {sx[0]} {sy[0]} {sz[0]}")
        return self.spimimagedata_ptr.value

    def __spim_data_unlocker(self, gene, newdata, running):
        #print(f"spim unlock {newdata} {running}")
        self.__frame_number += 1
        if (self.acquisition_mode == "Chrono") or (self.acquisition_mode == "Chrono-Live"):
            self.has_data_event.set()
            if (running == False):
                self.stop_live()
        else:
            if (running == False):
                self.has_spim_data_event.set()
                print("spim done")

    @property
    def sensor_dimensions(self) -> (int, int):
        return self.__sensor_dimensions

    @property
    def readout_area(self) -> (int, int, int, int):
        return self.__readout_area

    @readout_area.setter
    def readout_area(self, readout_area_TLBR: (int, int, int, int)) -> None:
        self.__readout_area = readout_area_TLBR

    @property
    def flip(self):
        return False

    @flip.setter
    def flip(self, do_flip):
        pass

    def start_live(self) -> None:
        self.__frame_number = 0
        self.sizex, self.sizey = self.camera.getImageSize()
        #if self.twoD == "2d":
        #    self.imagedata = numpy.empty((self.sizey, self.sizex), dtype = numpy.uint16)
        if self.twoD == "1d":
            self.sizey = 1
            #self.imagedata = numpy.empty((self.sizex,), dtype = numpy.float32)
        print(f"Start live, Image size: {self.sizex} x {self.sizey}  twoD: {self.twoD}    mode: {self.acquisition_mode}    nb spectra {self.nbspectra}")
        self.camera.setAccumulationNumber(self.nbspectra)
        if (self.acquisition_mode == "Chrono") or (self.acquisition_mode == "Chrono-Live"):
            self.sizey = self.nbspectra
            self.sizez = 1
            self.spimimagedata = numpy.empty((self.sizey, self.sizex), dtype = numpy.float32)
            self.spimimagedata_ptr = self.spimimagedata.ctypes.data_as(ctypes.c_void_p)
            self.camera.startSpim(1, self.nbspectra, self.__orsay_exposure_ms / 1000, False)
            self.camera.resumeSpim(4)  # stop eof
            if self.acquisition_mode == "Chrono-Live":
                self.camera.setSpimMode(1)  # continuous
        else:
            self.imagedata = numpy.empty((self.sizey, self.sizex), dtype = numpy.float32)
            self.imagedata_ptr = self.imagedata.ctypes.data_as(ctypes.c_void_p)
            acqmode = 0
            if self.acquisition_mode == "Cumul":
                acqmode = 1
            self.__acqon = self.camera.startFocus(self.__orsay_exposure_ms / 1000, self.twoD, acqmode)

    def stop_live(self) -> None:
        if (self.acquisition_mode == "Chrono") or (self.acquisition_mode == "Chrono-Live"):
            self.camera.stopSpim(True)
            self.__acqon = False
        else:
            self.__acqon = self.camera.stopFocus()

    def acquire_image(self) -> dict:
        self.has_data_event.wait(20.0)
        self.has_data_event.clear()
        if (self.acquisition_mode == "Chrono") or (self.acquisition_mode == "Chrono-Live"):
            data = self.spimimagedata
        else:
            data = self.imagedata
        collection_dimensions = 0
        datum_dimensions = 2
        if data.shape[0] == 2:
            collection_dimensions = 1
            datum_dimensions = 1
        elif data.shape[0] == 1:
            collection_dimensions = 0
            datum_dimensions = 1
            data = numpy.squeeze(data)
        else:
            collection_dimensions = 0
            datum_dimensions = 2
        properties = dict()
        properties["frame_number"] = self.__frame_number
        return {"data": data, "collection_dimension_count": collection_dimensions, "datum_dimension_count": datum_dimensions, "properties": properties, "spatial_calibrations": self.calibration}

    @property
    def calibration(self) -> dict:
        return {
            "x_scale_control": "ProEM_EELS_eVperpixel",
            "x_units_value": "eV",
            "y_scale_control": "ProEM_EELS_radsperpixel",
            "y_units_value": "rad",
            "intensity_units_value": "counts",
            "counts_per_electron_control": "ProEM_EELS_CountsPerElectron"
        }

    @property
    def mode(self):
        return "run"

    @mode.setter
    def mode(self, mode) -> None:
        pass

    @property
    def mode_as_index(self) -> int:
        return 0

    def get_exposure_ms(self, mode_id) -> float:
        return self.__exposure_s * 1000

    def set_exposure_ms(self, exposure_ms: float, mode_id) -> None:
        self.__exposure_s = exposure_ms / 1000
        # TODO: this is currently disabled; there is an architectural problem with communicating
        # changes to the frame parameters from the camera device. Until that is fixed, the hack
        # is to use orsay_exposure_ms; however this precludes the control of exposure from scripts
        # and particularly spectrum imaging.

    def get_binning(self, mode_id) -> int:
        return 1

    def set_binning(self, binning: int, mode_id) -> None:
        pass

    @property
    def binning_values(self) -> typing.List[int]:
        return [1]

    @property
    def exposure_ms(self) -> float:
        return self.get_exposure_ms(self.mode)

    @exposure_ms.setter
    def exposure_ms(self, value: float) -> None:
        self.set_exposure_ms(value, self.mode)

    @property
    def binning(self) -> int:
        return self.get_binning(self.mode)

    @binning.setter
    def binning(self, value: int) -> None:
        self.set_binning(value, self.mode)

    # until there is support for asymmetric binning in the standard camera, this orsay_binning property needs to be here

    @property
    def orsay_binning(self):
        return self.__orsay_binning

    @orsay_binning.setter
    def orsay_binning(self, b):
        acqon = self.__acqon
        print(f"binning acqon: {acqon}   binning {b}")
        if (acqon):
            self.stop_live()
        self.__orsay_binning = b
        self.camera.setBinning(self.__orsay_binning[0], self.__orsay_binning[1])
        if (acqon):
            self.start_live()

    # until there is improved architecture for handling frame parameters, this orsay_exposure_ms property needs to be here
    @property
    def orsay_exposure_ms(self):
        return self.__orsay_exposure_ms

    @orsay_exposure_ms.setter
    def orsay_exposure_ms(self, exposure_ms):
        self.__orsay_exposure_ms = exposure_ms
        self.camera.setExposureTime(self.__orsay_exposure_ms / 1000)

    @property
    def processing(self) -> typing.Optional[str]:
        return None

    @processing.setter
    def processing(self, value: str) -> None:
        pass

    def get_expected_dimensions(self, binning: int) -> (int, int):
        return self.__sensor_dimensions

    def acquire_sequence_prepare(self, scansize) -> None:
        self.__frame_number = 0
        print(f"preparing spim acquisition")
        self.sizex, tmpy = self.camera.getImageSize()
        self.sizey = scansize
        self.sizez = 1
        print(f"{self.sizex} {self.sizey} {self.sizez}")
        self.spimimagedata = numpy.zeros((self.sizex, self.sizey * self.sizez), dtype = numpy.float32)
        self.spimimagedata = numpy.ascontiguousarray(self.spimimagedata, dtype = numpy.float32)
        self.spimimagedata_ptr = self.spimimagedata.ctypes.data_as(ctypes.c_void_p)
        print(f"allocated {self.spimimagedata_ptr}")
        self.camera.startSpim(self.sizey * self.sizez, 1, self.__orsay_exposure_ms / 1000, False)
        print(f"prepared")

    def acquire_sequence(self, n: int) -> dict:
        self.camera.resumeSpim(4)  # stop eof
        self.__acqon = True
        print(f"resumed")
        print(f"acquiring {n}")
        print(f"wait {self.has_spim_data_event.wait(1000.0)}")
        self.has_spim_data_event.clear()
        self.camera.stopSpim(True)
        self.__acqon = False
        data = self.spimimagedata
        print(f"data {numpy.amax(data)}")
        return {"data": data, "properties": {"frame_number": self.__frame_number}, "spatial_calibrations": self.calibration}

    def start_monitor(self) -> None:
        pass

    # custom methods (not part of the camera_base.Camera)

    @property
    def fan_enabled(self) -> bool:
        return self.camera.getFan()

    @fan_enabled.setter
    def fan_enabled(self, value: bool) -> None:
        self.camera.setFan(bool(value))

    def isCameraAcquiring(self):
        return self.__acqon

    def set_softbinning(self, value):
        acqon = self.__acqon
        print(f"softbinning checked : {value} while acqon : {acqon}  ")
        if (acqon):
            self.stop_live()
        if (value):
            self.twoD = "1d"
        else:
            self.twoD = "2d"
        if (acqon):
            self.start_live()

    def setTurboMode(self, value):
        acqon = self.__acqon
        #values = [0, 1, 2, 4, 8]
        print(f"turbo mode : {value} while acqon : {acqon}  ")
        if (acqon):
            self.stop_live()
        self.camera.setTurboMode(value, 1600, 200)
        ro = self.camera.getReadoutTime()
        print(f"Readout time: {ro}   spectra/s {1/(ro+self.__exposure_s/1000)}")
        if (acqon):
            self.start_live()

    def getTurboMode(self):
        value, hs, vs = self.camera.getTurboMode()
        print(f"turbo mode : {value}")
        return value

    @property
    def readoutTime(self) -> float:
        return self.camera.getReadoutTime()

def periodic_logger():
    messages = list()
    data_elements = list()
    return messages, data_elements


def run():
    #input("Time to attach debugger -- type return to continue")
    #camera_device2 = Camera(1, "PIXIS: 100B")
    #camera_device2.camera_type = "eire"
    #camera_device2.camera_id = "orsay_camera_eire"
    #camera_device2.camera_name = _("Orsay Eire")
    #camera_device2.camera_panel_type = "orsay_camera_panel"

    #Registry.register_component(camera_device2, {"camera_device"})

    camera_device = Camera(1, "ProEM+: 1600xx(2)B eXcelon")
    camera_device.camera_type = "eels"
    camera_device.camera_id = "orsay_camera_eels"
    camera_device.camera_name = _("Orsay EELS")
    camera_device.camera_panel_type = "orsay_camera_panel"

    Registry.register_component(camera_device, {"camera_device"})


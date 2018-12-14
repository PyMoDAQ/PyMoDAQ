# standard libraries
import copy
import ctypes
import gettext
import numpy
import threading
import typing

# third party libraries

# local libraries
from nion.swift.model import HardwareSource

from .orsayscan import orsayScan, LOCKERFUNC, UNLOCKERFUNC, UNLOCKERFUNCA

from nion.instrumentation import scan_base

_ = gettext.gettext

SIZEZ = 2

AUTOSTEM_CONTROLLER_ID = "autostem_controller"


class Device:

    def __init__(self):
        self.__is_scanning = False
        self.on_device_state_changed = None
        self.__profiles = list()
        self.__profiles.append(scan_base.ScanFrameParameters({"size": (512, 512), "pixel_time_us": 0.2}))
        self.__profiles.append(scan_base.ScanFrameParameters({"size": (1024, 1024), "pixel_time_us": 0.2}))
        self.__profiles.append(scan_base.ScanFrameParameters({"size": (2048, 2048), "pixel_time_us": 2.5}))
        self.__frame_parameters = copy.deepcopy(self.__profiles[0])

        self.__frame_number = 0
        self.__scan_size = [512, 512]
        self.orsayscan = orsayScan(1)
        self.imagedata = numpy.empty((SIZEZ * self.__scan_size[1], self.__scan_size[0]), dtype = numpy.int16)
        self.imagedata_ptr = self.imagedata.ctypes.data_as(ctypes.c_void_p)
        self.has_data_event = threading.Event()
        self.fnlock = LOCKERFUNC(self.__data_locker)
        self.orsayscan.registerLocker(self.fnlock)
        self.fnunlock = UNLOCKERFUNCA(self.__data_unlockerA)
        self.orsayscan.registerUnlockerA(self.fnunlock)
        self.orsayscan.setPixelTime(0.000002)
        self.orsayscan.setScanScale(0, 5.0, 5.0)  # set the scan scale to 5v to match SuperScan, which output bank, then one for each direction

        channels_enabled = self.channels_enabled
        for channel_index in range(self.channel_count):
            self.set_channel_enabled(channel_index, channels_enabled[channel_index])

        print("OrsayScan Version: ", self.orsayscan.major)
        self.__angle = 0

    def close(self):
        pass

    @property
    def blanker_enabled(self) -> bool:
        """Return whether blanker is enabled."""
        return False

    @blanker_enabled.setter
    def blanker_enabled(self, blanker_on: bool) -> None:
        """Set whether blanker is enabled."""
        pass

    def change_pmt(self, channel_index: int, increase: bool) -> None:
        """Change the PMT value for the give channel; increase or decrease only."""
        pass

    @property
    def current_frame_parameters(self) -> scan_base.ScanFrameParameters:
        return self.__frame_parameters

    @property
    def channel_count(self):
        return self.orsayscan.getInputsCount()

    @property
    def channels_enabled(self) -> typing.Tuple[bool, ...]:
        return tuple(value != 0 for value in self.orsayscan.GetInputs()[1])

    def set_channel_enabled(self, channel_index: int, enabled: bool) -> bool:
        """in 16-bit mode, the number of channels used in hardware needs to be even
        in case odd number is slected, last channels can be repeated twice.
        call back function should then ignore this last channel; and it will match user interface
        in 32-bit mode, one channel can be enabled"""
        assert 0 <= channel_index < self.channel_count
        self.orsayscan.SetInputs([2, 3])
        # self.orsayscan.SetInputs([6, 7])  # hardware simulator
        return True

    def get_channel_name(self, channel_index: int) -> str:
        return self.orsayscan.getInputProperties(channel_index)[2]

    def read_partial(self, frame_number, pixels_to_skip) -> (typing.Sequence[dict], bool, bool, tuple, int, int):
        """Read or continue reading a frame.

        The `frame_number` may be None, in which case a new frame should be read.

        The `frame_number` otherwise specifies which frame to continue reading.

        The `pixels_to_skip` specifies where to start reading the frame, if it is a continuation.

        Return values should be a list of dict's (one for each active channel) containing two keys: 'data' and
        'properties' (see below), followed by a boolean indicating whether the frame is complete, a boolean indicating
        whether the frame was bad, a tuple of the form (top, left), (height, width) indicating the valid sub-area
        of the data, the frame number, and the pixels to skip next time around if the frame is not complate.

        The 'data' keys in the list of dict's should contain a ndarray with the size of the full acquisition and each
        ndarray should be the same size. The 'properties' keys are dicts which must contain the frame parameters and
        a 'channel_id' indicating the index of the channel (may be an int or float).
        """

        #self.__frame_number += 1
        self.has_data_event.wait(5.0)
        self.has_data_event.clear()
        # should be a loop over selected channels.
        data_arrays = self.imagedata[0:self.__scan_size[1], 0:self.__scan_size[0]].astype(numpy.float32), self.imagedata[self.__scan_size[1]:2*self.__scan_size[1], 0:self.__scan_size[0]].astype(numpy.float32)

        frame_number = self.__frame_number

        _data_elements = []

        sub_area = None
        for channel_index, data_array in enumerate(data_arrays):
            data_element = dict()
            image_metadata = self.__frame_parameters.as_dict()
            image_metadata["pixel_time_us"] = float(self.orsayscan.getPixelTime() * 1E6)
            image_metadata["pixels_x"] = self.__scan_size[1]
            image_metadata["pixels_y"] = self.__scan_size[0]
            image_metadata["center_x_nm"] = 0
            image_metadata["center_y_nm"] = 0
            image_metadata["rotation_deg"] = 0
            image_metadata["channel_id"] = channel_index
            data_element["data"] = data_array
            data_element["properties"] = image_metadata
            sub_area = ((0, 0), data_array.shape)
            _data_elements.append(data_element)

        complete = True
        bad_frame = False
        pixels_to_skip = 0  # only important when sub_area is not full area
        return _data_elements, complete, bad_frame, sub_area, frame_number, pixels_to_skip

    def get_profile_frame_parameters(self, profile_index: int) -> scan_base.ScanFrameParameters:
        return copy.deepcopy(self.__profiles[profile_index])

    @property
    def is_scanning(self) -> bool:
        self.__is_scanning = (self.orsayscan.getImagingKind() != 0)
        return self.__is_scanning

    def show_configuration_dialog(self, api_broker) -> None:
        """Open settings dialog, if any."""
        pass

    def save_frame_parameters(self) -> None:
        """Called when shutting down. Save frame parameters to persistent storage."""
        pass

    def set_frame_parameters(self, frame_parameters: scan_base.ScanFrameParameters) -> None:
        """Called just before and during acquisition.

        Device should use these parameters for new acquisition; and update to these parameters during acquisition.
        """
        self.orsayscan.setPixelTime(frame_parameters.pixel_time_us / 1E6)
        if self.__frame_parameters.size != frame_parameters.size:
            self.cancel()
            print("Changing frame size to [" + str(frame_parameters.size[0]) + ", " + str(frame_parameters.size[1]) + "]");
            self.orsayscan.setImageSize(frame_parameters.size[1], frame_parameters.size[0])
            self.start_frame(True)
        self.__frame_parameters = copy.deepcopy(frame_parameters)


    def set_profile_frame_parameters(self, profile_index: int, frame_parameters: scan_base.ScanFrameParameters) -> None:
        """Set the acquisition parameters for the give profile_index (0, 1, 2)."""
        self.__profiles[profile_index] = copy.deepcopy(frame_parameters)

    def set_idle_position_by_percentage(self, x: float, y: float) -> None:
        """Set the idle position as a percentage of the last used frame parameters."""
        pass

    def start_frame(self, is_continuous: bool) -> int:
        """Start acquiring. Return the frame number."""
        self.__scan_size = self.orsayscan.getImageSize()
        self.imagedata = numpy.empty((SIZEZ * self.__scan_size[1], self.__scan_size[0]), dtype = numpy.int16)
        self.imagedata_ptr = self.imagedata.ctypes.data_as(ctypes.c_void_p)
        self.__angle = 0
        self.orsayscan.setScanRotation(self.__angle)
        self.__is_scanning = self.orsayscan.startImaging(0, 1)
        return self.__frame_number

    def cancel(self) -> None:
        """Cancel acquisition (immediate)."""
        self.orsayscan.stopImaging(True)
        self.__is_scanning = False

    def stop(self) -> None:
        """Stop acquiring."""
        self.orsayscan.stopImaging(False)
        #self.__is_scanning = False

    def __data_locker(self, gene, datatype, sx, sy, sz):
        sx[0] = self.__scan_size[0]
        sy[0] = self.__scan_size[1]
        sz[0] = SIZEZ
        datatype[0] = 2
        return self.imagedata_ptr.value

    def __data_unlocker(self, gene, newdata):
        self.has_data_event.set()

    def __data_unlockerA(self, gene, newdata, imagenb, rect):
        if newdata:
            # message = "Image: " + str(imagenb) + "   pos: [" + str(rect[0]) + ", " + str(rect[1]) + "]   size: [" + str(rect[2]) + ", " + str(rect[3]) + "]"
            # print (message)
            # rect[0] x corner of rectangle updated
            # rect[1] y corner of rectangle updated
            # rect[2] horizontal size of the rectangle.
            # rect[3] vertical size of the rectangle.
            # image has all its data if .
            # numpy may only take the rectangle.
            # if rect[1] + rect[3] == self.__scan_size[1]:
            #     self.__angle = self.__angle + 5
            #     self.orsayscan.setScanRotation(self.__angle)
            #     print("Frame number: " + str(imagenb) + "    New rotation: " + str(self.__angle))
            self.__frame_number = imagenb
            self.has_data_event.set()


def run():
    scan_adapter = scan_base.ScanAdapter(Device(), "orsay_scan_device", _("Orsay Scan"))
    scan_hardware_source = scan_base.ScanHardwareSource(scan_adapter, AUTOSTEM_CONTROLLER_ID)
    HardwareSource.HardwareSourceManager().register_hardware_source(scan_hardware_source)

# standard libraries
import ctypes
from orsayscan import orsayScan, LOCKERFUNC, UNLOCKERFUNC, UNLOCKERFUNCA
import numpy
import threading
import time

SIZEX = 512
SIZEY = 512
SIZEZ = 2


class OrsayHardwareProxy:

    def __init__(self):
        self.__frame_number = 0
        self.orsayscan = orsayScan(1)
        print ("Version: ", self.orsayscan.major)
        self.imagedata = numpy.empty((SIZEZ, SIZEY, SIZEX), dtype = numpy.int16)
        self.imagedata_ptr = self.imagedata.ctypes.data_as(ctypes.c_void_p)
        self.has_data_event = threading.Event()
        self.fnlock = LOCKERFUNC(self.__data_locker)
        self.orsayscan.registerLocker(self.fnlock)
        self.fnunlock = UNLOCKERFUNCA(self.__data_unlockerA)
        self.orsayscan.registerUnlockerA(self.fnunlock)
        self.angle = 0
        self.imagenb = 0
        self._pixel_time_us = 2
        inpprop = self.orsayscan.getInputProperties(0)
        print(inpprop)

    @property
    def channel_count(self):
        return self.orsayscan.getInputsCount()

    def get_channel_info(self, channel_index):
        """Return a tuple of channel identifier and channel display name."""
        return "abcdafghijklmnop"[channel_index:channel_index+1], "ABCDEFGHIJKLMNOP"[channel_index:channel_index+1]

    @property
    def frame_number(self):
        return self.__frame_number

    @property
    def pixel_time_us(self):
        return self.orsayscan.getPixelTime() * 1000000

    @pixel_time_us.setter
    def pixel_time_us(self, value):
        self.orsayscan.setPixelTime(value/1000000)

    @property
    def scan_size(self):
        """Return size as a height, width tuple."""
 #       sizes = self.orsayscan.getImageSize()
 #       return sizes[0].value,sizes[1].value
        return 512, 512

#    @scan_size.setter
#    def scan_size(self, sizes):
#        self.orsayscan.setImageSize(sizes[0], sizes[1])

    def start(self):
        self.orsayscan.setPixelTime(0.000001)
        self.orsayscan.startImaging(0, 1)
        print("started")

    def stop(self, immediate):
        self.orsayscan.stopImaging(immediate)

    def __data_locker(self, gene, datatype, sx, sy, sz):
        sx[0] = SIZEX
        sy[0] = SIZEY
        sz[0] = SIZEZ
        datatype[0] = 2
        return self.imagedata_ptr.value

    def __data_unlocker(self, gene, newdata):
        self.has_data_event.set()

    def __data_unlockerA(self, gene, newdata, imagenb, rect):
        if newdata:
            message = "Image: " + str(imagenb) + "   pos: [" + str(rect[0]) + ", " + str(rect[1]) + "]   size: [" + str(rect[2]) + ", " + str(rect[3]) +"]"
            print (message)
            # rect[0] x corner of rectangle updated
            # rect[1] y corner of rectangle updated
            # rect[2] horizontal size of the rectangle.
            # rect[3] vertical size of the rectangle.
            # image has all its data if rect[1] + rect[3] = size y.
            # numpy may only take the rectangle.
            self.__frame_number = imagenb
            self.has_data_event.set()

    def grab_data(self):
        """Wait for the next frame and return a list of numpy arrays.

        The numpy array should be a copy.
        """
        self.__frame_number += 1
        self.has_data_event.wait(5.0)
        self.orsayscan.setScanRotation(self.angle)
        self.angle = self.angle + 1
        self.has_data_event.clear()
        return self.imagedata[0:0:SIZEY, 0:0:SIZEX].astype(numpy.float), self.imagedata[1:0:SIZEY, 1:0:SIZEX].astype(numpy.float)

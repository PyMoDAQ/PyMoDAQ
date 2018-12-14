# -*- coding: utf-8 -*-
"""
Created on Wed Jan 10 16:54:14 2018

@author: Weber
"""
from enum import IntEnum
class PicamComputerInterfaceEnum(IntEnum):

    PicamComputerInterface_Usb2            = 1
    PicamComputerInterface_1394A           = 2
    PicamComputerInterface_GigabitEthernet = 3
    PicamComputerInterface_Usb3            = 4

    def names(self):
        return [name for name, member in self.__members__.items()]
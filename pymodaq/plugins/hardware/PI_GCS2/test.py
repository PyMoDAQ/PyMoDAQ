# -*- coding: utf-8 -*-
"""
Created on Wed Jul 12 14:49:54 2017

@author: Weber
"""

from PyQt5.QtCore import QObject, pyqtSignal
import ctypes
from ctypes.util import find_library
import numpy as np
import os

#%%
libpath=find_library("C:\\Users\\Weber\\Labo\\Programmes Python\\PyMoDAQ\\DAQ_Utils\\hardware\\PI_GCS2_wrapper\\PI_Programming_Files_PI_GCS2_DLL\\PI_GCS2_DLL_x64.dll")
cgslib=ctypes.windll.LoadLibrary(libpath) #object containing all CGS2 physik instrumente functions
#%%
def translate_error(err_code):
    status='buffer too small'
    err_id=cgslib.PI_GetError(err_code)
    buffer=ctypes.pointer((ctypes.c_char *256)())
    res=cgslib.PI_TranslateError (err_id, buffer, 256)
    if res:
        print(buffer.contents.value)
        status= buffer.contents.value
    return status



#%%
buffer=ctypes.pointer((ctypes.c_char *256)())
err_code=cgslib.PI_EnumerateUSB(buffer,256)

if err_code>=0:
    Ncontrollers=err_code
    desc=buffer.contents.value
    print(desc.decode())
else:
    translate_error(err_code)
#%%
bufSize= 256
s=ctypes.create_string_buffer(b'\000' * bufSize)
err_code=cgslib.PI_EnumerateUSB(s,bufSize)

if err_code>=0:
    Ncontrollers=err_code
    desc=s.value
    print(desc.decode())
else:
    translate_error(err_code)


#%%
err_code=cgslib.PI_InterfaceSetupDlg()
#%%

ID=None
err_code=cgslib.PI_ConnectUSB(desc)
if err_code<0:
    translate_error(err_code)
else:
    ID=err_code
#%%
err_code=cgslib.PI_GetControllerID(ID)
translate_error(err_code)
#%%
err_code=cgslib.PI_CloseConnection (ID)
translate_error(err_code)

#%%
err_code=cgslib.PI_TryConnectUSB(desc[:-1])
translate_error(err_code)

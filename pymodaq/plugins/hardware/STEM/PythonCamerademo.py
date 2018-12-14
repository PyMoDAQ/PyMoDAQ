"""
# -*- coding:utf-8 -*-
Demo program for class controlling orsay camera.
"""
# standard libraries
import sys
import ctypes
import numpy
import orsaycamera
import time
import python_lib as mylib
import matplotlib.pyplot as plt
from PyMoDAQ.DAQ_Utils.plotting.image_view_multicolor.image_view_multicolor import Image_View_Multicolor
from PyQt5 import QtWidgets
from pyqtgraph.dockarea import DockArea
CCDSIZEX = 1600
CCDSIZEY = 200
SIZEZ = 1
sizex = 1600
sizey = 200

SPIMX = 16
SPIMY = 16


def dataLocker(camera, datatype, sx, sy, sz):
    """
    Callback pour obtenir le tableau ou stocker les nouvelles données.
    Dans un programme complet il est conseillé de verrouiler ce tableau (par exemple ne pas changer sa dimension, son type, le détuire etc...)
    camera dans le cas de plusieurs camera, c'est un index qui dit quelle camera envoie des data.
    permet d'utiliser le même code pour les callback.
    Le type de données est
        1   byte
        2   short
        3   long
        5   unsigned byte
        6   unsgned short
        7   unsigned long
        11  float 32 bit
        12  double 64 bit
   """
    sx[0] = sizex
    sy[0] = sizey
    sz[0] = 1
    datatype[0] = 11
    return pointeur.value

def dataUnlocker(camera, newdata):
    """
    Le tableau peut être utilisé
    on imprime les premières valeurs
    """
    print ("img: ", imagedata[0:10])
    prog.setImage(imagedata.reshape((sizey,sizex)))

def spimdataLocker(camera, datatype, sx, sy, sz):
    """
    Même chose que pour le mode focus, mais le tableau est 3D, voire plus
    """
    sx[0] = SPIMX
    sy[0] = SPIMY
    sz[0] = sizex
    datatype[0] = 11
    return pointeurspim.value


def spimdataUnlocker(camera, newdata, running):
    if running:
        # imprime un point par spectre
        print(".", end = "")
    else:
        print("Done")
        test.stopFocus()

def spectrumdataLocker(camera, datatype, sx):
    """
    Callback pour obtenir le tableau ou stcoker les nouvelles données.
    Dans un programme complet il est conseillé de verrouiler ce tableau (par exemple ne pas changer sa dimension, son type, le détuire etc...)
    camera dans le cas de plusieurs camera, c'est un index qui dit quelle camera envoie des data.
    permet d'utiliser le même code pour les callback.
    Le type de données est
        1   byte
        2   short

        3   long
        5   unsigned byte
        6   unsgned short
        7   unsigned long
        11  float 32 bit
        12  double 64 bit
   """
    sx[0] = sizex
    datatype[0] = 11
    return pointeurspectrum.value

def spectrumdataUnlocker(camera, newdata):
    """
    Le tableau peut être utilisé
    on imprime les premières valeurs
    """
#    print ("s", end = "")

#%%
test = orsaycamera.orsayCamera(1,'PIXIS: 256E','1234',True)
CCDSIZEX, CCDSIZEY = test.getCCDSize()
print ("CCD size:", test.getCCDSize())
print(test.getBinning())
print ("Image size:", test.getImageSize())
test.setBinning(1,1)
print("Binning: ", test.getBinning())
print("Readout time:", test.getReadoutTime())
test.setupBinning()
print ("Image size:", test.getImageSize())

print (test.getCCDStatus())
#%%
"List all ports"
nbports = test.getNumofPorts()
ports = test.getPortNames()
print("Ports:", ports)

allparams = test.getAllPortsParams()
for port in allparams:
    print(port)

fnlock = orsaycamera.DATALOCKFUNC(dataLocker)
test.registerDataLocker(fnlock)

fnunlock = orsaycamera.DATAUNLOCKFUNC(dataUnlocker)
test.registerDataUnlocker(fnunlock)

port =  test.getCurrentPort()
print("Port: ", port,"    vitesse", test.getCurrentSpeed(port))
test.setCurrentPort(0)
test.setSpeed(0, 0)
port =  test.getCurrentPort()
print("Port: ", port,"    vitesse", test.getCurrentSpeed(port))

# full binning vertical
test.setBinning(1, 1)

print("Readout time:", test.getReadoutTime())
#%%

"Test of image acquisition"
"à faire: des essais avec différents binning"
"à faire: des essais avec différents types de données"
sizex, sizey = test.getImageSize()
print("Image Size: ", sizex, sizey)
imagedata = numpy.zeros((sizex*sizey,), dtype = numpy.float32)
pointeur = imagedata.ctypes.data_as(ctypes.c_void_p)
#%%
app = QtWidgets.QApplication(sys.argv)
Form=DockArea()
Form=QtWidgets.QWidget()

prog = Image_View_Multicolor(Form);
Form.show()
sys.exit(app.exec_())
#%%
test.startFocus(0.1, "2d", 1)

time.sleep(10)
##
test.stopFocus()
#
#%%
mylib.figure_docked('image')
plt.imshow(imagedata.reshape((sizey,sizex)))
#%%
#Test of spectrum image acquisition
print("preparing spim acquisition")
sizex, sizey = test.getImageSize()

spimsize = sizex * SPIMY * SPIMX
spimdata = numpy.ones((spimsize,), dtype = numpy.float32)
pointeurspim = spimdata.ctypes.data_as(ctypes.c_void_p)

spectrumdata = numpy.zeros((CCDSIZEX,), dtype = numpy.float32)
pointeurspectrum = spectrumdata.ctypes.data_as(ctypes.c_void_p)

fnspimlock = orsaycamera.SPIMLOCKFUNC(spimdataLocker)
test.registerSpimDataLocker(fnspimlock)
fnspimunlock = orsaycamera.SPIMUNLOCKFUNC(spimdataUnlocker)
test.registerSpimDataUnlocker(fnspimunlock)

fnspectrumlock = orsaycamera.SPECTLOCKFUNC(spectrumdataLocker)
test.registerSpectrumDataLocker(fnspectrumlock)
fnspectrumunlock = orsaycamera.SPECTUNLOCKFUNC(spectrumdataUnlocker)
test.registerSpectrumDataUnlocker(fnspectrumunlock)


#%%
test.startSpim(SPIMX * SPIMY, 1, 0.01, False)
print("started, in state pause")

#démarrage réel de la caméra.
test.resumeSpim(4)  # stop eof
print("resumed")

mode = "spim"
# attend la fin du spim, imprime la progression
while mode != "idle":
    time.sleep(0.2)
    status = test.getCCDStatus()
    print(status, end = "\r")
    mode = status[0]
print("")

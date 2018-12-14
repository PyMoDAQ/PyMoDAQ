"""
Demo program for class controlling orsay scan hardware.
"""

# standard libraries
import sys
from ctypes import c_void_p, POINTER
from _ctypes import byref, POINTER
import numpy as np
from orsayscan import orsayScan, LOCKERFUNC, UNLOCKERFUNC, UNLOCKERFUNCA
import matplotlib.pyplot as plt
#import python_lib as mylib

#%%
#callback:
# pour la demo, on garde la taille fixe, avec 2 entrées, pas de lineaveraging
SIZEX = 4
SIZEY = 4
SIZEZ = 2

imagedata = np.zeros((2*SIZEY*SIZEX,), dtype = np.int16)
print (imagedata.ctypes.data_as(c_void_p))
pointeur = imagedata.ctypes.data_as(c_void_p)
#%%

def dataLocker(gene, datatype, sx, sy, sz):
    """
    Callback pour obtenir le tableau ou stcoker les nouvelles données.
    Dans un programme complet il est conseillé de verrouiler ce tableau (par exemple ne pas changer sa dimension, son type, le détuire etc...)
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
    sx[0] = SIZEX
    sy[0] = SIZEY
    sz[0] = SIZEZ
    datatype[0] = 2
    return pointeur.value


def dataUnlocker(gene, newdata):
    """
    Le tableau peut être utilisé
    on imprime les 16 premières valeurs
    """
    print (imagedata[0:20])


def dataUnlockerA(gene, newdata,  imagenb, rect):
    """
    Le tableau peut être utilisé
    on imprime le numéro d'image et les coordonnées du rectangle modifié
    """
    print ("Py Image: ", imagenb, "   pos: [", rect[0], ", ", rect[1], "]   size: [", rect[2], ", ", rect[3], "]")
    print ("Scan count: ", scan.getScanCount())

#
#   Instanciation du balayage
#%%
scan = orsayScan(1, 0)
#scan.init1()
#
# classe nécessaire pour le spectre image.
spimscan = orsayScan(2, scan.orsayscan)
#orsayspimscan.init2(scan.orsayscan)
#%%

nbinputs = scan.getInputsCount()
k = 0
while (k < nbinputs):
    unipolar, offset, name = scan.getInputProperties(k)
    print ("Input:" , k, "   label: ", name, "   video offset: ", offset)
    k = k+1

#choose X and Y ramps.
scan.SetInputs([0, 1])
nbinputs, inputs = scan.GetInputs()
sizex = SIZEX
sizey = SIZEY
scan.setImageSize(sizex, sizey)
sizex, sizey = scan.getImageSize()
scan.setImageArea(sizex, sizey, 0, sizex, 0, sizey)
res, sx, sy, stx, ex, sty, ey = scan.getImageArea()
scan.pixelTime=100/1e6
scan.setScanRotation(50)
scan.setScanScale(0, 1, 1)
scan.OrsayScanSetFieldSize(-0.012798743137951306)
scan.OrsayScanGetFieldSize()



#scan.setImageArea(512,512,30,30+128,50,50+128)
#scan.setImageArea(512,512,0,512,0,512)
#%%
fnlock = LOCKERFUNC(dataLocker)
scan.registerLocker(fnlock)

fnunlock = UNLOCKERFUNCA(dataUnlockerA)
scan.registerUnlockerA(fnunlock)
#%%
scan.startImaging(2, 1)

scan.stopImaging(False)


#%%

data=imagedata.reshape((2,SIZEY,SIZEX))
data=data.astype(np.float64)

data_1=data[0,:,:]
data_2=data[1,:,:]



fig=mylib.figure_docked('stem')
plt.subplot(1,2,1)
plt.pcolormesh(data_1, cmap='gray')
#plt.axis('square')
plt.colorbar()

plt.subplot(1,2,2)
plt.pcolormesh(data_2, cmap='gray')
plt.colorbar()
#plt.axis('square')

#%%
#choose X and Y ramps.
spimscan.SetInputs([0, 1])
nbinputs, inputs = spimscan.GetInputs()
sizex = SIZEX
sizey = SIZEY
spimscan.setImageSize(sizex, sizey)
sizex, sizey = spimscan.getImageSize()
spimscan.setImageArea(sizex, sizey, 0, sizex, 0, sizey)
res, sx, sy, stx, ex, sty, ey = spimscan.getImageArea()
spimscan.pixelTime=100/1e6
spimscan.setScanRotation(50)
spimscan.setScanScale(0, 1, 1)
spimscan.OrsayScanSetFieldSize(-0.012798743137951306)
spimscan.OrsayScanGetFieldSize()
#%%
scan.close()
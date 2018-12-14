"""
Class controlling orsay scan hardware.
"""
import sys
from ctypes import cdll, create_string_buffer, POINTER, byref
from ctypes import c_uint, c_int, c_char, c_char_p, c_void_p, c_short, c_long, c_bool, c_double, c_uint64, c_uint32, Array, CFUNCTYPE, WINFUNCTYPE
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

#is64bit = sys.maxsize > 2**32
if (sys.maxsize > 2**32):
    libname = os.path.dirname(__file__)
    libname = os.path.join(libname, "Scan.dll")
    _library = cdll.LoadLibrary(libname)
    print("OrsayScan library: ", _library)
else:
    raise Exception("It must a python 64 bit version")

#void SCAN_EXPORT *OrsayScanInit();
_OrsayScanInit = _buildFunction(_library.OrsayScanInit, [], c_void_p)

#void SCAN_EXPORT OrsayScanClose(void* o)
_OrsayScanClose = _buildFunction(_library.OrsayScanClose, [c_void_p], None)

#void SCAN_EXPORT OrsayScangetVersion(void* o, short *product, short *revision, short *serialnumber, short *major, short *minor);
_OrsayScangetVersion = _buildFunction(_library.OrsayScangetVersion, [c_void_p, POINTER(c_short), POINTER(c_short), POINTER(c_short), POINTER(c_short), POINTER(c_short)], None)

#int SCAN_EXPORT OrsayScanGetInputsCount(void* o);
_OrsayScangetInputsCount = _buildFunction(_library.OrsayScanGetInputsCount, [c_void_p], c_int)

#int SCAN_EXPORT OrsayScangetInputProperties(void* o, int nb, bool &unipolar, double &offset, char *buffer);
_OrsayScanGetInputProperties =  _buildFunction(_library.OrsayScanGetInputProperties, [c_void_p, c_int, POINTER(c_bool), POINTER(c_double), POINTER(c_char)], c_int)

#	bool SCAN_EXPORT OrsayScanSetInputProperties(void* o, int nb, bool unipolar, double offset);
_OrsayScanSetInputProperties = _buildFunction(_library.OrsayScanSetInputProperties, [c_void_p, c_int, c_bool, c_double], c_bool)

#bool SCAN_EXPORT OrsayScansetImageSize(self.orsayscan, int gene, int x, int y);
_OrsayScansetImageSize = _buildFunction(_library.OrsayScansetImageSize, [c_void_p, c_int, c_int, c_int], c_bool)

#	bool SCAN_EXPORT OrsayScangetImageSize(self.orsayscan, int gene, int *x, int *y);
_OrsayScangetImageSize = _buildFunction(_library.OrsayScangetImageSize, [c_void_p, c_int, POINTER(c_int), POINTER(c_int)], c_bool)

#bool SCAN_EXPORT OrsayScansetImageArea(void* o, int gene, int sx, int sy, int xd, int xf, int yd, int yf);
_OrsayScansetImageArea = _buildFunction(_library.OrsayScansetImageArea, [c_void_p, c_int, c_int, c_int, c_int, c_int, c_int, c_int], c_bool)

#bool SCAN_EXPORT OrsayScangetImageArea(void* o, int gene, int *sx, int *sy, int *xd, int *xf, int *yd, int *yf);
_OrsayScangetImageArea = _buildFunction(_library.OrsayScangetImageArea, [c_void_p, c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(c_int)], bool)

#double SCAN_EXPORT OrsayScangetPose(void* o, int gene);
_OrsayScangetPose = _buildFunction(_library.OrsayScangetPose, [c_void_p, c_int], c_double)

#bool SCAN_EXPORT OrsayScansetPose(void* o, int gene, double time);
_OrsayScansetPose = _buildFunction(_library.OrsayScansetPose, [c_void_p, c_int, c_double], c_bool)

#double SCAN_EXPORT OrsayScanGetImageTime(void* o, int gene);
_OrsayScanGetImageTime = _buildFunction(_library.OrsayScanGetImageTime, [c_void_p, c_int], c_double)

#bool SCAN_EXPORT OrsayScanSetInputs(void* o, int gene, int nb, int *inputs);
_OrsayScanSetInputs =_buildFunction(_library.OrsayScanSetInputs, [c_void_p, c_int, c_int, POINTER(c_int)], c_bool)

#int SCAN_EXPORT OrsayScanGetInputs(void* o, int gene, int *inputs);
_OrsayScanGetInputs =_buildFunction(_library.OrsayScanGetInputs, [c_void_p, c_int, POINTER(c_int)], c_int)

#void SCAN_EXPORT OrsayScanSetRotation(void* o, double angle);
_OrsayScanSetRotation = _buildFunction(_library.OrsayScanSetRotation,  [c_void_p, c_double], None)

#double SCAN_EXPORT OrsayScanGetRotation(void* o);
_OrsayScanGetRotation = _buildFunction(_library.OrsayScanGetRotation, [c_void_p], c_double)

#bool SCAN_EXPORT OrsayScanStartImaging(void* o, short gene, short mode, short lineaverage);
_OrsayScanStartImaging = _buildFunction(_library.OrsayScanStartImaging, [c_void_p, c_short, c_short, c_short], c_bool)

#bool SCAN_EXPORT OrsayScanStartSpim(void* o, short gene, short mode, short lineaverage, int nbspectraperpixel, bool sumpectra);
_OrsayScanStartSpim = _buildFunction(_library.OrsayScanStartSpim, [c_void_p, c_short, c_short, c_short, c_int, c_bool], c_bool)

#bool SCAN_EXPORT OrsayScanStopImaging(void* o, int gene, bool cancel);
_OrsayScanStopImaging = _buildFunction(_library.OrsayScanStopImaging, [c_void_p, c_int, c_bool], c_bool)

#bool SCAN_EXPORT OrsayScanStopImagingA(void* o, int gene, bool immediate);
_OrsayScanStopImagingA = _buildFunction(_library.OrsayScanStopImagingA, [c_void_p, c_int, c_bool], c_bool)

#void SCAN_EXPORT OrsayScanSetImagingMode(void* o, int gene, int stripes);
_OrsayScanSetImagingMode = _buildFunction(_library.OrsayScanSetImagingMode, [c_void_p, c_int, c_int], None);

#bool SCAN_EXPORT OrsayScanSetScanClock(void* o, int gene, int mode);
_OrsayScanSetScanClock = _buildFunction(_library.OrsayScanSetScanClock, [c_void_p, c_int, c_int], c_bool)

#unsigned long SCAN_EXPORT OrsayScanGetScansCount(void* o);
_OrsayScanGetScansCount = _buildFunction(_library.OrsayScanGetScansCount, [c_void_p], c_uint32)

#void SCAN_EXPORT OrsayScanSetScale(void* o, int sortie, double vx, double vy);
_OrsayScanSetScale = _buildFunction(_library.OrsayScanSetScale, [c_void_p, c_int, c_double, c_double], None)

#void SCAN_EXPORT OrsayScanSetImagingKind(self.orsayscan, int gene, int kind);
_OrsayScanSetImagingKind = _buildFunction(_library.OrsayScanSetImagingKind, [c_void_p, c_int, c_int], None)

#int SCAN_EXPORT OrsayScanGetImagingKind(self.orsayscan, int gene);
_OrsayScanGetImagingKind = _buildFunction(_library.OrsayScanGetImagingKind, [c_void_p, c_int], c_int)

#double SCAN_EXPORT OrsayScanGetVideoOffset(self.orsayscan, int index);
_OrsayScanGetVideoOffset = _buildFunction(_library.OrsayScanGetVideoOffset, [c_void_p, c_int], c_double)

#void SCAN_EXPORT OrsayScanSetVideoOffset(self.orsayscan, int index, double value);
_OrsayScanSetVideoOffset = _buildFunction(_library.OrsayScanSetVideoOffset, [c_void_p, c_int, c_double], None)

#void *(*LockScanDataPointer)(int gene, int *datatype, int *sx, int *sy, int *sz);
LOCKERFUNC = WINFUNCTYPE(c_void_p, c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(c_int))
#void SCAN_EXPORT OrsayScanRegisterDataLocker(void * o, void *(*LockScanDataPointer)(int gene, int *datatype, int *sx, int *sy, int *sz));
_OrsayScanregisterLocker = _buildFunction(_library.OrsayScanRegisterDataLocker, [c_void_p, LOCKERFUNC], None)

#void(*UnLockScanDataPointer)(int gene, bool newdata);
UNLOCKERFUNC = WINFUNCTYPE(None, c_int, c_bool)
UNLOCKERFUNCA = WINFUNCTYPE(None, c_int, c_int, c_int, POINTER(c_int))

#void SCAN_EXPORT OrsayScanRegisterDataUnlocker(self.orsayscan, void(*UnLockScanDataPointer)(int gene, bool newdata));
_OrsayScanregisterUnlocker = _buildFunction(_library.OrsayScanRegisterDataUnlocker, [c_void_p, UNLOCKERFUNC], None)
_OrsayScanregisterUnlockerA = _buildFunction(_library.OrsayScanRegisterDataUnlockerA, [c_void_p, UNLOCKERFUNCA], None)

# ajout de fonctions VG.
#bool SCAN_EXPORT OrsayScanSetProbeAt(self.orsayscan, int gene, int px, int py);
_OrsayScanSetProbeAt = _buildFunction(_library.OrsayScanSetProbeAt, [c_void_p, c_int, c_int, c_int], c_bool);

#void SCAN_EXPORT OrsayScanSetEHT(self.orsayscan, double val);
_OrsayScanSetEHT = _buildFunction(_library.OrsayScanSetEHT, [c_void_p, c_double], None);

#double SCAN_EXPORT OrsayScanGetEHT(self.orsayscan);
_OrsayScanGetEHT = _buildFunction(_library.OrsayScanGetEHT, [c_void_p], c_double);

#double SCAN_EXPORT OrsayScanGetMaxFieldSize(self.orsayscan);
_OrsayScanGetMaxFieldSize = _buildFunction(_library.OrsayScanGetMaxFieldSize, [c_void_p], c_double);

#double SCAN_EXPORT OrsayScanGetFieldSize(self.orsayscan);
_OrsayScanGetFieldSize = _buildFunction(_library.OrsayScanGetFieldSize, [c_void_p], c_double);

#double SCAN_EXPORT OrsayScanGetScanAngle(self.orsayscan, short *mirror);
_OrsayScanGetScanAngle = _buildFunction(_library.OrsayScanGetScanAngle, [c_void_p, c_short], c_double);

#bool SCAN_EXPORT OrsayScanSetFieldSize(self.orsayscan, double field);
_OrsayScanSetFieldSize = _buildFunction(_library.OrsayScanSetFieldSize, [c_void_p, c_double], c_bool);


#bool SCAN_EXPORT OrsayScanSetBottomBlanking(self.orsayscan, short mode, short source, double beamontime, bool risingedge, unsigned int nbpulses, double delay);
_OrsayScanSetBottomBlanking = _buildFunction(_library.OrsayScanSetBottomBlanking, [c_void_p, c_short, c_double, c_bool, c_uint, c_double], c_bool);

#bool SCAN_EXPORT OrsayScanSetTopBlanking(self.orsayscan, short mode, short source, double beamontime, bool risingedge, unsigned int nbpulses, double delay);
_OrsayScanSetTopBlanking = _buildFunction(_library.OrsayScanSetTopBlanking, [c_void_p, c_short, c_double, c_bool, c_uint, c_double], c_bool);


#bool SCAN_EXPORT OrsayScanSetCameraSync(self.orsayscan, bool eels, int divider, double width, bool risingedge);
_OrsayScanSetCameraSync = _buildFunction(_library.OrsayScanSetCameraSync, [c_void_p, c_bool, c_int, c_double, c_bool], c_bool);

#void SCAN_EXPORT OrsayScanObjectiveStigmateur(self.orsayscan, double x, double y);
_OrsayScanObjectiveStigmateur = _buildFunction(_library.OrsayScanObjectiveStigmateur, [c_void_p, c_double, c_double], None);

#void SCAN_EXPORT OrsayScanObjectiveStigmateurCentre(self.orsayscan, double xcx, double xcy, double ycx, double ycy);
_OrsayScanObjectiveStigmateurCentre = _buildFunction(_library.OrsayScanObjectiveStigmateurCentre, [c_void_p, c_double, c_double, c_double, c_double], None);

#void SCAN_EXPORT OrsayScanCondensorStigmateur(self.orsayscan, double x, double y);
_OrsayScanCondensorStigmateur = _buildFunction(_library.OrsayScanCondensorStigmateur, [c_void_p, c_double, c_double], None);

#void SCAN_EXPORT OrsayScanGrigson(self.orsayscan, double x1, double x2, double y1, double y2);
_OrsayScanGrigson = _buildFunction(_library.OrsayScanGrigson, [c_void_p, c_double, c_double, c_double, c_double], None);

#void SCAN_EXPORT OrsayScanAlObjective(self.orsayscan, double x1, double x2, double y1, double y2);
_OrsayScanAlObjective = _buildFunction(_library.OrsayScanAlObjective, [c_void_p, c_double, c_double, c_double, c_double], None);

#void SCAN_EXPORT OrsayScanAlGun(self.orsayscan, double x1, double x2, double y1, double y2);
_OrsayScanAlGun = _buildFunction(_library.OrsayScanAlGun, [c_void_p, c_double, c_double, c_double, c_double], None);

#void SCAN_EXPORT OrsayScanAlStigObjective(self.orsayscan, double x1, double x2, double y1, double y2);
_OrsayScanAlStigObjective = _buildFunction(_library.OrsayScanAlStigObjective, [c_void_p, c_double, c_double, c_double, c_double], None);


#void SCAN_EXPORT OrsayScanSetLaser(self.orsayscan, double frequency, int nbpulses, bool bottomblanking, short sync);
_OrsayScanSetLaser = _buildFunction(_library.OrsayScanSetLaser, [c_void_p, c_double, c_int, c_bool, c_short], None);

#void SCAN_EXPORT OrsayScanStartLaser(self.orsayscan, int mode);
_OrsayScanStartLaser = _buildFunction(_library.OrsayScanStartLaser, [c_void_p, c_int], None);

#void SCAN_EXPORT OrsayScanCancelLaser(self.orsayscan);
_OrsayScanCancelLaser = _buildFunction(_library.OrsayScanCancelLaser, [c_void_p], None);

#int SCAN_EXPORT OrsayScanGetLaserCount(self.orsayscan);
_OrsayScanGetLaserCount = _buildFunction(_library.OrsayScanGetLaserCount, [c_void_p], c_int);


class orsayScan(object):
    """Class controlling orsay scan hardware
       Requires Scan.dll library to run.
    """

    def __init__(self, gene, scandllobject = 0):
        self.gene = gene
        cproduct = c_short()
        crevision = c_short()
        cserialnumber = c_short()
        cmajor = c_short()
        cminor = c_short()
        if (gene < 2):
            self.orsayscan = _OrsayScanInit()
        if (gene > 1):
            self.orsayscan = scandllobject
        _OrsayScangetVersion(self.orsayscan, byref(cproduct), byref(crevision), byref(cserialnumber), byref(cmajor), byref(cminor))
        self._product = cproduct.value
        self._revision = crevision.value
        self._serialnumber = cserialnumber.value
        self._major = cmajor.value
        self._minor = cminor.value
        if self._major < 5:
            raise AttributeError("No device connected")

    def close(self):
        _OrsayScanClose(self.orsayscan)
        self.orsaycamera = None

    def __verifyUnsigned32Bit(self, value):
        """
        Check if value is in range 0 <= value <= 0xffffffff
        """
        if(value < 0 or value > 0xffffffff):
            raise AttributeError("Argument out of range (must be 32bit unsigned).")

    def __verifySigned32Bit(self, value):
        """
        Check if value is in range 0 <= value <= 0xffffffff
        """
        if(value < 0x8000000 or value > 0x7fffffff):
            raise AttributeError("Argument out of range (must be 32bit signed).")

    def __verifyPositiveInt(self, value):
        """
        Check if value is in range 0 <= value <= 0xffffffff
        """
        if(value < 0 or value > 0x7fffffff):
            raise AttributeError("Argument out of range (must be positive 32bit signed).")

    def __verifyStrictlyPositiveInt(self, value):
        """
        Check if value is in range 0 < value <= 0xffffffff
        """
        if(value < 0 or value > 0x7fffffff):
            raise AttributeError("Argument out of range (must be positive 32bit signed).")

    def getInputsCount(self):
        """
        Donne le nombre d'entrées vidéo actives
        """
        return _OrsayScangetInputsCount(self.orsayscan)

    def getInputProperties(self, input):
        """
        Lit les propriétés de l'entrée vidéo
        Retourne 3 valeurs: bool vrai si unipolaire, double offset, string nom.
        """
        unipolar = c_bool()
        offset = c_double()
        buffer = _createCharBuffer23(100)
        res = _OrsayScanGetInputProperties(self.orsayscan, input, byref(unipolar), byref(offset), buffer)
        return unipolar.value, offset.value, _convertToString23(buffer.value)

    def setInputProperties(self, input, unipolar, offet):
        """
        change les propriétés de l'entrée vidéo
        Pour le moment, seul l'offset est utilisé.
        """
        res =_OrsayScanSetInputProperties(self.orsayscan, input, offset)
        if (not res):
            raise Exception("Failed to set orsayscan input properties")
        return res

    def GetImageTime(self):
        """
        Donne le temps effectif de la durée de balayage d'une image
        """
        return _OrsayScanGetImageTime(self.orsayscan, self.gene)

    def SetInputs(self, inputs):
        """
        Choisit les entrées à lire.
        A cause d'une restriction hardware, les valeurs possibles sont 1, 2, 4, 6, 8
        """
        inputarray = (c_int * len(inputs))()
        k = 0
        while (k < len(inputs)):
            inputarray[k] = inputs[k]
            k = k +1
        return _OrsayScanSetInputs(self.orsayscan, self.gene, len(inputarray), inputarray)

    def GetInputs(self):
        """
        Donne la liste des entrées utilisées
        pas correcte, doit être corrigée
        """
        inputarray = (c_int * 20)()
        nbinputs = _OrsayScanGetInputs(self.orsayscan, self.gene, inputarray)
        inputs = [inputarray[0], inputarray[1]]
        return nbinputs, inputs

    def setImageSize(self, sizex, sizey):
        """
        Définit la taille de l'image en pixels
        Les limites de dimension sont 1 et 8192
        """
        self.__verifyPositiveInt(sizex)
        self.__verifyPositiveInt(sizey)
        res = _OrsayScansetImageSize(self.orsayscan, self.gene, sizex, sizey)
        if (not res):
            raise Exception("Failed to set orsayscan image size")

    def getImageSize(self):
        """
        Donne la taille de l'image
        *** il est impératif que le tableau passé à la callback ait cette taille
            multiplié par le nombre d'entrées, multiplié par le paramètre lineaveragng ***
        """
        sx = c_int()
        sy = c_int()
        res = _OrsayScangetImageSize(self.orsayscan, self.gene, byref(sx), byref(sy))
        if (not res):
            raise Exception("Failed to get orsayscan image size")
        return int(sx.value), int(sy.value)

    def setImageArea(self, sizex, sizey, startx, endx, starty, endy):
        """
        Définit une aire pour le balayage.
        sizex, sizey taille de l'image complète
        startx, endx début et fin de la largeur du rectangle
        starty, endy début et fin de la hauteur.
        """
#        self.__verifyStrictlyPositiveInt(sizex)
#        self.__verifyStrictlyPositiveInt(sizey)
        return _OrsayScansetImageArea(self.orsayscan, self.gene, sizex, sizey, startx, endx, starty, endy)

    def getImageArea(self):
        """
        Donne l'aire réduite utilisée,
        retourne les paramètres donnés à la fonction setImageArea ou ceux les plus proches valides.
        """
        sx, sy, stx, ex, sty, ey = c_int(), c_int(), c_int(), c_int(), c_int(), c_int()
        res = _OrsayScangetImageArea(self.orsayscan, self.gene, byref(sx), byref(sy), byref(stx), byref(ex), byref(sty), byref(ey))
        return res, int(sx.value), int(sy.value), int(stx.value), int(ex.value), int(sty.value), int(ey.value)

    @property
    def pixelTime(self):
        """
        Donne le temps par pixel
        """
        return _OrsayScangetPose(self.orsayscan, self.gene)

    @pixelTime.setter
    def pixelTime(self, value):
        """
        Définit le temps par pixel
        """
        return _OrsayScansetPose(self.orsayscan, self.gene, value)

    #def getPixelTime(self):
        """
        Donne le temps par pixel
        """
    #    return _OrsayScangetPose(self.orsayscan, self.gene)

    #def setPixelTime(self, dwell):
        """
        Définit le temps par pixel
        """

    #    return _OrsayScansetPose(self.orsayscan, self.gene, dwell)

    #
    #   Callback qui sera appelée lors d'arrivée de nouvelles données
    #
    def registerLocker(self, fn):
        """
        Définit la fonction callback appelée lorsque de nouvelles données sont présentes
        Elle a pour but de passer un tableau image sa dimension et son type de données
        On ne doit détruire cet objet avant l'appel d'une fonction unlock
        Voir programme demo.
        """
        _OrsayScanregisterLocker(self.orsayscan, fn)

    def registerUnlocker(self, fn):
        """
        Definit la fonction appelée à la fin du transfert de données.
        recoit newdata vrai si de nouvelles données sont effectivement là.
        Utiliser de préférence la fonction registerUnlockerA plus riche en informations sur le flux de données
        voir programe demo
        """
        _OrsayScanregisterUnlocker(self.orsayscan, fn)

    def registerUnlockerA(self, fn):
        """
        Definit la fonction appelée à la fin du transfert de données.
        reçoit newdata, le numéro de séquence de l'image en cours, rect: les coordonnées du rect où les données ont été modifiées.
        voir programe demo
        """
        _OrsayScanregisterUnlockerA(self.orsayscan, fn)

    def startSpim(self, mode, linesaveraging,Nspectra=1,save2D=False):
        """
        Démarre l'acquitisition de l'image.
        mode: --- expliqué plus tard ---
        lineaveraging: nombre de lignes à faire avant de passer à la ligne suivante.
        retourne vrai si l'acquisition a eu lieu.
        """
        return _OrsayScanStartSpim(self.orsayscan, self.gene, mode, linesaveraging,Nspectra,save2D)

    def setScanClock(self,trigger_input=0):
        """
        set the input line for starting the next pixel in the STEM imaging (pin 9 and 5 on subD9)
        Parameters
        ----------
        trigger_input: 0 for pin 9, 1 for pin 5, 2 for CL ready, 3 for In3, 4 for EELS ready

        Returns
        -------

        """
        return _OrsayScanSetScanClock(self.orsayscan, self.gene, trigger_input)

    def startImaging(self, mode, linesaveraging):
        """
        Démarre l'acquitisition de l'image.
        mode: --- expliqué plus tard ---
        lineaveraging: nombre de lignes à faire avant de passer à la ligne suivante.
        retourne vrai si l'acquisition a eu lieu.
        """
        return _OrsayScanStartImaging(self.orsayscan, self.gene, mode, linesaveraging)

    def stopImaging(self, cancel):
        """
        Arrete l'acquisition d'images
        cancel vrai => immédiat,  faux => à la fin du scan de l'image en cours
        """
        return _OrsayScanStopImaging(self.orsayscan, self.gene, cancel)

    def getScanCount(self):
        """
        Donne le nombe de balayages déjà faits
        """
        return _OrsayScanGetScansCount(self.orsayscan)

    def setScanRotation(self, angle):
        """
        Définit l'angle de rotation du balayage de l'image
        """
        _OrsayScanSetRotation(self.orsayscan, angle)

    def getScanRotation(self):
        """
        Relit la valeur de l'angle de rotation du balayage de l'image
        """
        return _OrsayScanGetRotation(self.orsayscan)

    def setScanScale(self, plug, xamp, yamp):
        """
        Ajuste la taille des signaux analogiques de balayage valeur >0 et inf"rieure à 1.
        """
        _OrsayScanSetScale(self.orsayscan, plug, xamp, yamp)

    def getImgagingKind(self):
        return _OrsayScanGetImagingKind(self.orsayscan)

    def setVideoOffset(self, inp, offset):
        """
        Définit l'offset analogique à ajouter au signal d'entrée afin d'avoir une valeur 0 pour 0 volts
        En principe, c'est un réglage et pour une machine cela ne devrait pas bouger beaucoup
        """
        _OrsayScanSetVideoOffset(self.orsayscan, inp, offset)

    def getVideoOffset(self, inp):
        """
        Donne la valeur de l'offset vidéo
        """
        return _OrsayScanGetVideoOffset(self.orsayscan, inp)

    def OrsayScanSetProbeAt(self,gene,px,py):
   #bool SCAN_EXPORT OrsayScanSetProbeAt(self.orsayscan, int gene, int px, int py);
       return _OrsayScanSetProbeAt(self.orsayscan,gene,px,py)

   #void SCAN_EXPORT OrsayScanSetEHT(self.orsayscan, double val);
    def OrsayScanSetEHT(self,val):
        _OrsayScanSetEHT(self.orsayscan,val)

    def OrsayScanGetEHT(self,val):
        return _OrsayScanGetEHT(self.orsayscan,val)

   #double SCAN_EXPORT OrsayScanGetMaxFieldSize(self.orsayscan);
    def OrsayScanGetMaxFieldSize(self,val):
        return _OrsayScanGetMaxFieldSize(self.orsayscan)

   #double SCAN_EXPORT OrsayScanGetFieldSize(self.orsayscan);
    def OrsayScanGetFieldSize(self):
        return _OrsayScanGetFieldSize(self.orsayscan)

   #double SCAN_EXPORT OrsayScanGetScanAngle(self.orsayscan, short *mirror);
    def OrsayScanGetScanAngle(self,mirror):
        return _OrsayScanGetScanAngle(self.orsayscan, mirror)
   #bool SCAN_EXPORT OrsayScanSetFieldSize(self.orsayscan, double field);
    def OrsayScanSetFieldSize(self,field):
        return _OrsayScanSetFieldSize(self.orsayscan,  field)

   #bool SCAN_EXPORT OrsayScanSetBottomBlanking(self.orsayscan, short mode, short source, double beamontime, bool risingedge, unsigned int nbpulses, double delay);
    def OrsayScanSetBottomBlanking(self,mode,source,beamontime = 0, risingedge = True, nbpulses = 0, delay = 0):
        """ Définit le blanker avant l'échantillon sur un VG/Nion
            mode : 0 blanker off, 1 blanker On, 2 controlled by source, 3 controlled by source but with locally defined time (beamontime parametre)
            source : to be choosen based on configuration file (eels camera readout, cl camera readout, laser pulse, ...)
            beamontime : with of the Blanker on signal, for instance CCD vertical transfer time, laser pulse width, ...
            risingedge : choose the edge that triggers the beamontime.
            nbpulses : number of pulses required a signal is generated (used to sync slave cameras)
            delay : delay used to generate the beamon signal after the trigger. if nbpulses != 0, this delay is incremented nbpulses times.
            (very specific application not tested yet).
        """
        return _OrsayScanSetBottomBlanking(self.orsayscan,mode, source,beamontime,risingedge,nbpulses,delay)
   #bool SCAN_EXPORT OrsayScanSetTopBlanking(self.orsayscan, short mode, short source, double beamontime, bool risingedge, unsigned int nbpulses, double delay);
    def OrsayScanSetTopBlanking(self,mode, source,beamontime = 0, risingedge = True, nbpulses = 0, delay = 0):
        """ Définit le blanker après l'échantillon sur un VG/Nion
            mode : 0 blanker off, 1 blanker On, 2 controlled by source, 3 controlled by source but with locally defined time (beamontime parametre)
            source : to be choosen based on configuration file (eels camera readout, cl camera readout, laser pulse, ...)
            beamontime : with of the Blanker on signal, for instance CCD vertical transfer time, laser pulse width, ...
            risingedge : choose the edge that triggers the beamontime.
            nbpulses : number of pulses required a signal is generated (used to sync slave cameras)
            delay : delay used to generate the beamon signal after the trigger. if nbpulses != 0, this delay is incremented nbpulses times.
            (very specific application not tested yet).
        """
        return _OrsayScanSetTopBlanking(self.orsayscan,mode, source,beamontime,risingedge,nbpulses,delay)


   #bool SCAN_EXPORT OrsayScanSetCameraSync(self.orsayscan, bool eels, int divider, double width, bool risingedge);
    def OrsayScanSetCameraSync(self,eels,divider,width,risingedge):
        """ Définit le mode de travail de la camera, par défaut la camera eels est maître
            eels: True => master, False => Slave
            divider: si mode slave, nombre d'impulsions pour avoir un trigger
            width: Largeur de l'impulsion
            risingedge: front utiliser pour compter l'impulsion.
        """
        return _OrsayScanSetCameraSync(self.orsayscan,eels,divider,width,risingedge)

    #
    #   Fonctions spécifique au VG
    #

   #void SCAN_EXPORT OrsayScanObjectiveStigmateur(self.orsayscan, double x, double y);
    def OrsayScanObjectiveStigmateur(self,x,y):
        """ Définit le stigmateur objectif (électrostatique) """
        _OrsayScanObjectiveStigmateur(self.orsayscan,x,y)

   #void SCAN_EXPORT OrsayScanObjectiveStigmateurCentre(self.orsayscan, double xcx, double xcy, double ycx, double ycy);
    def OrsayScanObjectiveStigmateurCentre(self,xcx,xcy,ycx,ycy):
        """ Définit le centre du stigmateur objectif """
        _OrsayScanObjectiveStigmateurCentre(self.orsayscan,xcx,xcy,ycx,ycy)

   #void SCAN_EXPORT OrsayScanCondensorStigmateur(self.orsayscan, double x, double y);
    def OrsayScanCondensorStigmateur(self,x,y):
        """ Définit le stigmateur condensuer (magnétique) """
        _OrsayScanCondensorStigmateur(self.orsayscan,x,y)

   #void SCAN_EXPORT OrsayScanGrigson(self.orsayscan, double x1, double x2, double y1, double y2);
    def OrsayScanGrigson(self,x1,x2,y1,y2):
        """ Définit le courant Grigson """
        _OrsayScanGrigson(self.orsayscan,x1,x2,y1,y2)

   #void SCAN_EXPORT OrsayScanAlObjective(self.orsayscan, double x1, double x2, double y1, double y2);
    def OrsayScanAlObjective(self,x1,x2,y1,y2):
        """ Aligne l'objectif """
        _OrsayScanAlObjective(self.orsayscan,x1,x2,y1,y2)
   #void SCAN_EXPORT OrsayScanAlGun(self.orsayscan, double x1, double x2, double y1, double y2);
    def OrsayScanAlGun(self,x1,x2,y1,y2):
        """ Aligne le canon """
        _OrsayScanAlGun(self.orsayscan,x1,x2,y1,y2)

   #void SCAN_EXPORT OrsayScanAlStigObjective(self.orsayscan, double x1, double x2, double y1, double y2);
    def OrsayScanAlStigObjective(self,x1,x2,y1,y2):
        """ Aligne le stigmateur canon(?) """
        _OrsayScanAlStigObjective(self.orsayscan,x1,x2,y1,y2)

   #void SCAN_EXPORT OrsayScanSetLaser(self.orsayscan, double frequency, int nbpulses, bool bottomblanking, short sync);
    def OrsayScanSetLaser(self,frequency,nbpulses,bottomblanking,sync):
        """ définit le mode de travail du laser
            frquency: frequence des impulsions
            nbpulses: nombre total d'impulsions sur le prochain tir
            bottomblanking: True => utilisé
            sync: < 0 pas utilisé, >= 0 utilise l'entrée choisie pour déclencher l'impulsion
        """
        _OrsayScanSetLaser(self.orsayscan,frequency,nbpulses,bottomblanking,sync)

   #void SCAN_EXPORT OrsayScanStartLaser(self.orsayscan, int mode);
    def OrsayScanStartLaser(self,mode):
        """ Démarre le laser """
        _OrsayScanStartLaser(self.orsayscan,mode)

   #void SCAN_EXPORT OrsayScanCancelLaser(self.orsayscan);
    def OrsayScanCancelLaser(self):
        """ arrete le laser """
        _OrsayScanCancelLaser(self.orsayscan)

   #int SCAN_EXPORT OrsayScanGetLaserCount(self.orsayscan);
    def OrsayScanGetLaserCount(self):
        """ donne le nombre d'impulsions déjà faites """
        return _OrsayScanGetLaserCount(self.orsayscan)
   
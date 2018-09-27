from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QDateTime, QSize

import numpy as np
from easydict import EasyDict as edict
from enum import IntEnum
from PyMoDAQ.DAQ_Viewer.utility_classes import DAQ_Viewer_base
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import PyMoDAQ.DAQ_Utils.custom_parameter_tree
from PyMoDAQ.DAQ_Utils import python_lib as mylib
import ctypes
from PyMoDAQ.DAQ_Viewer.utility_classes import DAQ_TCP_server
from PyMoDAQ.DAQ_Utils.DAQ_utils import ThreadCommand

class DAQ_2DViewer_Det_type(IntEnum):
    """
        Enum class of Det Type.

        =============== ================
        **Attributes**    **Type**
        *Mock*            int
        *OrsayCamera*     int
        *TCP_GRABBER*     int
        *names*          string list???
        =============== ================
    """
    Mock=0
    OrsayCamera=1
    TCP_GRABBER=2
    @classmethod
    def names(cls):
        names=cls.__members__.items()
        return [name for name, member in cls.__members__.items()]



class DAQ_2DViewer_Mock(DAQ_Viewer_base):
    """
        =============== ==================
        **Attributes**   **Type**
        *params*         dictionnary list
        *x_axis*         1D numpy array
        *y_axis*         1D numpy array
        =============== ==================

        See Also
        --------
        utility_classes.DAQ_Viewer_base
    """

    params= [{'name': 'Nx', 'type': 'int', 'value': 20 , 'default':20, 'min':1},
            {'name': 'Ny', 'type': 'int', 'value': 30 , 'default':30, 'min':1},
            {'name': 'Amp', 'type': 'int', 'value': 20 , 'default':20, 'min':1},
            {'name': 'x0', 'type': 'float', 'value': 10 , 'default':50, 'min':0},
            {'name': 'y0', 'type': 'float', 'value': 10 , 'default':50, 'min':0},
            {'name': 'dx', 'type': 'float', 'value': 5 , 'default':20, 'min':1},
            {'name': 'dy', 'type': 'float', 'value': 10 , 'default':20, 'min':1},
            {'name': 'n', 'type': 'float', 'value': 1 , 'default':1, 'min':1},
            {'name': 'amp_noise', 'type': 'float', 'value': 4 , 'default':0.1, 'min':0}
                ]
    def __init__(self,parent=None,params_state=None): #init_params is a list of tuple where each tuple contains info on a 1D channel (Ntps,amplitude, width, position and noise)
        super(DAQ_2DViewer_Mock,self).__init__(parent,params_state)
        self.x_axis=None
        self.y_axis=None



    def commit_settings(self,param):
        """
            Activate parameters changes on the hardware.

            =============== ================================ ===========================
            **Parameters**   **Type**                          **Description**
            *param*          instance of pyqtgraph Parameter   the parameter to activate
            =============== ================================ ===========================

            See Also
            --------
            set_Mock_data
        """
        self.set_Mock_data()

    def set_Mock_data(self):
        """
            | Set the x_axis and y_axis with a linspace distribution from settings parameters.
            |

            Once done, set the data mock with parameters :
                * **Amp** : The amplitude
                * **x0** : the origin of x
                * **dx** : the derivative x pos
                * **y0** : the origin of y
                * **dy** : the derivative y pos
                * **n** : ???
                * **amp_noise** : the noise amplitude

            Returns
            -------
                The computed data mock.
        """

        self.x_axis=np.linspace(0,self.settings.child(('Nx')).value(),self.settings.child(('Nx')).value(),endpoint=False)
        self.y_axis=np.linspace(0,self.settings.child(('Ny')).value(),self.settings.child(('Ny')).value(),endpoint=False)
        self.data_mock=self.settings.child(('Amp')).value()*(mylib.gauss2D(self.x_axis,self.settings.child(('x0')).value(),self.settings.child(('dx')).value(),
                                     self.y_axis,self.settings.child(('y0')).value(),self.settings.child(('dy')).value(),self.settings.child(('n')).value()))+self.settings.child(('amp_noise')).value()*np.random.rand(len(self.y_axis),len(self.x_axis))
        return self.data_mock



    def Ini_Detector(self):
        """
            Initialisation procedure of the detector initializing the status dictionnary.

            See Also
            --------
            DAQ_utils.ThreadCommand, get_xaxis, get_yaxis
        """
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None))
        try:
            self.x_axis=self.get_xaxis()
            self.y_axis=self.get_yaxis()
            self.status.x_axis=self.x_axis
            self.status.y_axis=self.y_axis
            self.status.initialized=True
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
            self.status.info=str(e)
            self.status.initialized=False
            return self.status

    def Close(self):
        """
            not implemented.
        """
        pass

    def get_xaxis(self):
        """
            Get the current x_axis from the Mock data setting.

            Returns
            -------
            1D numpy array
                the current x_axis.

            See Also
            --------
            set_Mock_data
        """
        self.set_Mock_data()
        return self.x_axis

    def get_yaxis(self):
        """
            Get the current y_axis from the Mock data setting.

            Returns
            -------
            1D numpy array
                the current y_axis.

            See Also
            --------
            set_Mock_data
        """
        self.set_Mock_data()
        return self.y_axis

    def Grab(self,Naverage=1):
        """
            | For each integer step of naverage range set mock data.
            | Construct the data matrix and send the data_grabed_signal once done.

            =============== ======== ===============================================
            **Parameters**  **Type**  **Description**
            *Naverage*      int       The number of images to average.
                                      specify the threshold of the mean calculation
            =============== ======== ===============================================

            See Also
            --------
            set_Mock_data
        """
        data=[] #list of image (at most 3 for red, green and blue channels)
        self.set_Mock_data()
        data_tmp=np.zeros((len(self.y_axis),len(self.x_axis)))
        for ind in range(Naverage):
            data_tmp+=self.set_Mock_data()
        data_tmp=data_tmp/Naverage
        data.append(data_tmp)
        QThread.msleep(100)
        self.data_grabed_signal.emit(data)

    def Stop(self):
        """
            not implemented.
        """

        return ""


class DAQ_2DViewer_OrsayCamera(DAQ_Viewer_base):
    """
        =============== ==================
        **Attributes**   **Type**
        *params*         dictionnary list
        *x_axis*         1D numpy array
        *y_axis*         1D numpy array
        *camera*         ???
        *data*           float array ???
        *CCDSIZEX*       ???
        *CCDSIZEY*       ???
        *data_pointer*   ???
        =============== ==================

        See Also
        --------
        utility_classes.DAQ_Viewer_base
    """
    params= [{'title': 'Exposure:', 'name': 'exposure', 'type': 'float', 'value': 0.1 , 'default':0.1},
             {'title': 'Image size:', 'name': 'image_size', 'type': 'group', 'children':[
                {'title': 'Nx:', 'name': 'Nx', 'type': 'int', 'value': 0, 'default':0 , 'readonly': True},
                {'title': 'Ny:', 'name': 'Ny', 'type': 'int', 'value': 0 , 'default':0 , 'readonly': True},
                ]},
             {'title': 'Temperature Settings:', 'name': 'temperature_settings', 'type': 'group', 'children':[
                {'title': 'Set Point:', 'name': 'set_point', 'type': 'float', 'value': -70, 'default':-70},
                {'title': 'Current value:', 'name': 'current_value', 'type': 'float', 'value': 0 , 'default':0, 'readonly': True},
                {'title': 'Locked:', 'name': 'locked', 'type': 'led', 'value': False , 'default':False, 'readonly': True},
                ]},
             {'title': 'Binning Settings:', 'name': 'binning_settings', 'type': 'group', 'children':[
                {'name': 'bin_x', 'type': 'int', 'value': 1 , 'default':1, 'min':1},
                {'name': 'bin_y', 'type': 'int', 'value': 1 , 'default':1, 'min':1}
                ]}
             ]
    from PyMoDAQ.DAQ_Utils.hardware.STEM import orsaycamera

    def __init__(self,parent=None,params_state=None):

        super(DAQ_2DViewer_OrsayCamera,self).__init__(parent,params_state) #initialize base class with commom attributes and methods

        self.x_axis=None
        self.y_axis=None
        self.camera=None
        self.data=None
        self.CCDSIZEX, self.CCDSIZEY=(None,None)
        self.data_pointer=None


    def commit_settings(self,param):
        """
            | Activate parameters changes on the hardware from parameter's name.
            |

            =============== ================================    =========================
            **Parameters**   **Type**                           **Description**
            *param*          instance of pyqtgraph parameter    The parameter to activate
            =============== ================================    =========================

            Three profile of parameter :
                * **bin_x** : set binning camera from bin_x parameter's value
                * **bin_y** : set binning camera from bin_y parameter's value
                * **set_point** : Set the camera's temperature from parameter's value.

        """
        if param.name()=='bin_x':
            self.camera.setBinning(param.value(),self.settings.child('binning_settings','bin_y').value())
            Nx, Ny = self.camera.getImageSize()
            self.settings.child('image_size','Nx').setValue(Nx)
            self.settings.child('image_size','Ny').setValue(Ny)
        elif param.name()=='bin_y':
            self.camera.setBinning(self.settings.child('binning_settings','bin_x').value(),param.value())
            Nx, Ny = self.camera.getImageSize()
            self.settings.child('image_size','Nx').setValue(Nx)
            self.settings.child('image_size','Ny').setValue(Ny)
        #elif param.name()=='exposure':
        #    self.camera.setExposureTime(self.settings.child(('exposure')).value())
        elif param.name()=='set_point':
            self.camera.setTemperature(param.value())

    def dataLocker(self,camera, datatype, sx, sy, sz):
        """
            | CallBack to obtain the tab and store the newest data.
            | In a full program context, it is recommanded to lock the tab (to keep size values, type and integrity for example).
            | It permit to use the same code in case of callback.
            |
            
            The data type is :
                * **1**  : byte
                * **2**  : short
                * **3**  : long
                * **5**  : unsigned byte
                * **6**  : unsgned short
                * **7**  : unsigned long
                * **11** : float 32 bit
                * **12** : double 64 bit

            =============== =============== =============================================================================
            **Parameters**    **Type**        **Description**
            *camera*                          in case of differents cameras, index pointing the camera sending the datas
            *datatype*        int             defined above
            *sx*              int array       X image size
            *sy*              int array       Y image size
            *sz*              int array       Z image size
            =============== =============== =============================================================================

            Returns
            -------
            ???



       """
        #Callback pour obtenir le tableau ou stocker les nouvelles données.
        # Dans un programme complet il est conseillé de verrouiler ce tableau (par exemple ne pas changer sa dimension, son type, le détuire etc...)
        # camera dans le cas de plusieurs camera, c'est un index qui dit quelle camera envoie des data.
        # permet d'utiliser le même code pour les callback.
        # Le type de données est
        #     1   byte
        #     2   short
        #     3   long
        #     5   unsigned byte
        #     6   unsgned short
        #     7   unsigned long
        #     11  float 32 bit
        #     12  double 64 bit
        sx[0] = self.settings.child('image_size','Nx').value()
        sy[0] = self.settings.child('image_size','Ny').value()
        sz[0] = 1
        datatype[0] = 11
        return self.data_pointer.value

    def dataUnlocker(self,camera, newdata):
        """
            Transmission of new acquired data

            =============== =============== ===============================
            **Parameters**   **Type**        **Description**

            *camera*         c_void pointer  pointer to camera object

            *newdata*        bool            True if new data is available
            =============== =============== ===============================

            See Also
            --------
            emit_data

        """
        #print(self.data[0:10])
        if newdata:
            self.emit_data()



    def emit_data(self):
        """
            Fonction used to emit data obtained by dataUnlocker callback or average it.

            See Also
            --------
            DAQ_utils.ThreadCommand
        """
        try:
            self.ind_grabbed+=1
            #print(self.ind_grabbed)
            self.data_average+=self.data.reshape((self.settings.child('image_size','Ny').value(),self.settings.child('image_size','Nx').value()))
            if self.ind_grabbed==self.Naverage:
                self.data_grabed_signal.emit([self.data_average/self.Naverage])
                #self.camera.stopFocus() #stop acquisition from camera, otherwise keep going (even if setAccumulationNumber has been set to one)

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))

    def Ini_Detector(self):
        """
            Initialisation procedure of the detector in four steps :
                * Register callback to get data from camera
                * Get image size and current binning
                * Set and Get temperature from camera
                * Init axes from image

            Returns
            -------
            string list ???
                The initialized status.

            See Also
            --------
            DAQ_utils.ThreadCommand, hardware1D.DAQ_1DViewer_Picoscope.update_pico_settings
        """
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None))
        try:
            from PyMoDAQ.DAQ_Utils.hardware.STEM import orsaycamera
            self.camera=orsaycamera.orsayCamera(1) #index represents manufacturer

            #%%%%%%% Register callback to get data from camera
            self.fnlock = orsaycamera.DATALOCKFUNC(self.dataLocker)
            self.camera.registerDataLocker(self.fnlock)

            self.fnunlock = orsaycamera.DATAUNLOCKFUNC(self.dataUnlocker)
            self.camera.registerDataUnlocker(self.fnunlock)


            #%%%%%% Get image size and current binning
            self.CCDSIZEX, self.CCDSIZEY = self.camera.getCCDSize()
            bin_x,bin_y=self.camera.getBinning()
            Nx, Ny = self.camera.getImageSize()
            self.settings.child('image_size','Nx').setValue(Nx)
            self.settings.child('image_size','Ny').setValue(Ny)
            self.settings.child('binning_settings','bin_x').setValue(bin_x)
            self.settings.child('binning_settings','bin_y').setValue(bin_y)

            #%%%%%%% Set and Get temperature from camera
            self.camera.setTemperature(self.settings.child('temperature_settings','set_point').value())
            temp,locked_status=self.camera.getTemperature()
            self.settings.child('temperature_settings','current_value').setValue(temp)
            self.settings.child('temperature_settings','locked').setValue(locked_status)
            #set timer to update temperature info from controller
            self.timer=self.startTimer(2000) #Timer event fired every 1s

            #%%%%%%% init axes from image
            self.x_axis=self.get_xaxis()
            self.y_axis=self.get_yaxis()
            self.status.x_axis=self.x_axis
            self.status.y_axis=self.y_axis
            self.status.initialized=True
            return self.status

        except Exception as e:
            self.status.info=str(e)
            self.status.initialized=False
            return self.status

    def timerEvent(self, event):
        """
            | Called by set timers (only one for this self).
            | Used here to update temperature status0.

            =============== ==================== ==============================================
            **Parameters**    **Type**             **Description**

            *event*           QTimerEvent object   Containing id from timer issuing this event
            =============== ==================== ==============================================
        """
        temp,locked_status=self.camera.getTemperature()
        self.settings.child('temperature_settings','current_value').setValue(temp)
        self.settings.child('temperature_settings','locked').setValue(locked_status)

    def Close(self):
        """
            Should be used to uninitialize camera but none provided by Marcel.
        """
        pass

    def get_xaxis(self):
        """
            Obtain the horizontal axis of the image.

            Returns
            -------
            1D numpy array
                Contains a vector of integer corresponding to the horizontal camera pixels.
        """
        if self.camera is not None:
            Nx, Ny = self.camera.getImageSize()
            self.settings.child('image_size','Nx').setValue(Nx)
            self.settings.child('image_size','Ny').setValue(Ny)
            self.x_axis=np.linspace(0,self.settings.child('image_size','Nx').value()-1,self.settings.child('image_size','Nx').value(),dtype=np.int)
        else: raise(Exception('Camera not defined'))
        return self.x_axis

    def get_yaxis(self):
        """
            Obtain the vertical axis of the image.

            Returns
            -------
            1D numpy array
                Contains a vector of integer corresponding to the vertical camera pixels.
        """
        if self.camera is not None:
            Nx, Ny = self.camera.getImageSize()
            self.settings.child('image_size','Nx').setValue(Nx)
            self.settings.child('image_size','Ny').setValue(Ny)
            self.y_axis=np.linspace(0,self.settings.child('image_size','Ny').value()-1,self.settings.child('image_size','Ny').value(),dtype=np.int)
        else: raise(Exception('Camera not defined'))
        return self.y_axis

    def Grab(self,Naverage=1):
        """
            Start new acquisition in two steps :
                * Initialize data: self.data for the memory to store new data and self.data_average to store the average data
                * Start acquisition with the given exposure in ms, in "1d" or "2d" mode

            =============== =========== =============================
            **Parameters**   **Type**    **Description**
            Naverage         int         Number of images to average
            =============== =========== =============================

            See Also
            --------
            DAQ_utils.ThreadCommand
        """
        try:
            self.ind_grabbed=0 #to keep track of the current image in the average
            self.Naverage=Naverage

            #%%%%%% Initialize data: self.data for the memory to store new data and self.data_average to store the average data
            self.data= np.zeros((self.settings.child('image_size','Nx').value()*self.settings.child('image_size','Ny').value(),), dtype = np.float32)
            self.data_average=np.zeros((self.settings.child('image_size','Ny').value(),self.settings.child('image_size','Nx').value()))
            self.data_pointer = self.data.ctypes.data_as(ctypes.c_void_p)

            #%%%%% Start acquisition with the given exposure in ms, in "1d" or "2d" mode
            self.camera.setAccumulationNumber(Naverage) #stop the acquisition after Navergae image if third argument of startfocus is 1
            self.camera.startFocus(self.settings.child(('exposure')).value(), "2d", 1)
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),"log"]))

    def Stop(self):
        """
            Stop the camera's actions.
        """
        try:
            self.camera.stopFocus()
        except: pass
        return ""

class DAQ_2DViewer_TCP_GRABBER(DAQ_TCP_server):
    """
        ================= ==============================
        **Attributes**      **Type**
        *command_server*    instance of pyqtSignal
        *x_axis*            1D numpy array
        *y_axis*            1D numpy array
        *data*              double precision float array
        ================= ==============================

        See Also
        --------
        utility_classes.DAQ_TCP_server
    """
    command_server=pyqtSignal(list)
    #params=DAQ_TCP_server.params
    def __init__(self,parent=None,params_state=None):

        super(DAQ_2DViewer_TCP_GRABBER,self).__init__(parent,params_state) #initialize base class with commom attributes and methods
        #server=DAQ_TCP_server(parent,params_state)
        #server.data_grabed_signal.connect(self.data_ready)
        #self.server_thread=QThread()
        ##server.moveToThread(self.server_thread)
        #self.command_server[list].connect(server.queue_command)

        #self.server_thread.server=server
        #self.server_thread.start()

        self.x_axis=None
        self.y_axis=None
        self.data=None

    def data_ready(self,data):
        """
            Send the grabed data signal.
        """
        self.data_grabed_signal.emit(data)


    def commit_settings(self,param):
        pass


    def Ini_Detector(self):
        """
            | Initialisation procedure of the detector updating the status dictionnary.
            |
            | Init axes from image , here returns only None values (to tricky to di it with the server and not really necessary for images anyway)

            See Also
            --------
            utility_classes.DAQ_TCP_server.init_server, get_xaxis, get_yaxis
        """
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None))
        try:
            self.init_server()

        #%%%%%%% init axes from image , here returns only None values (to tricky to di it with the server and not really necessary for images anyway)
            self.x_axis=self.get_xaxis()
            self.y_axis=self.get_yaxis()
            self.status.x_axis=self.x_axis
            self.status.y_axis=self.y_axis
            self.status.initialized=True
            return self.status

        except Exception as e:
            self.status.info=str(e)
            self.status.initialized=False
            return self.status

    def Close(self):
        """
            Should be used to uninitialize hardware.

            See Also
            --------
            utility_classes.DAQ_TCP_server.close_server
        """
        self.listening=False
        self.close_server()

    def get_xaxis(self):
        """
            Obtain the horizontal axis of the image.

            Returns
            -------
            1D numpy array
                Contains a vector of integer corresponding to the horizontal camera pixels.
        """
        pass
        return self.x_axis

    def get_yaxis(self):
        """
            Obtain the vertical axis of the image.

            Returns
            -------
            1D numpy array
                Contains a vector of integer corresponding to the vertical camera pixels.
        """
        pass
        return self.y_axis

    def Grab(self,Naverage=1):
        """
            Start new acquisition.
            Grabbed indice is used to keep track of the current image in the average.

            ============== ========== ==============================
            **Parameters**   **Type**  **Description**

            *Naverage*        int       Number of images to average
            ============== ========== ==============================

            See Also
            --------
            utility_classes.DAQ_TCP_server.process_cmds
        """
        try:
            self.ind_grabbed=0 #to keep track of the current image in the average
            self.Naverage=Naverage
            self.process_cmds("Send Data 2D")
            #self.command_server.emit(["process_cmds","Send Data 2D"])


        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),"log"]))

    def Stop(self):
        """
            not implemented.
        """
        pass
        return ""


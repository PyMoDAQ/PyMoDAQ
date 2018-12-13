#template example

#mandatory imports
from PyMoDAQ.DAQ_Utils.DAQ_utils import ThreadCommand
from PyMoDAQ.DAQ_Viewer.utility_classes import comon_parameters
from PyMoDAQ.DAQ_Utils import custom_parameter_tree
from PyMoDAQ.DAQ_Viewer.utility_classes import DAQ_Viewer_base
import numpy as np
from collections import OrderedDict
from PyQt5 import QtWidgets, QtCore
from easydict import EasyDict as edict

#########################################################################################
# example if one has to check for the platform type (for instance to load a .dll or .so file
from enum import IntEnum
import platform
import ctypes
if platform.system() == "Linux":
    libpath=ctypes.util.find_library('libandor') #to be checked
elif platform.system() == "Windows":
    if platform.machine() == "AMD64":
        libpath=ctypes.util.find_library('atmcd64d')
    else:
        libpath=ctypes.util.find_library('atmcd32d')

#########################################################################"
#example if one has to define an enum (to be used in a list later on)
class Template_Enum(IntEnum):
    """
    Enum class of template modes (fake).
    """
    Option1=0
    Option2=1
    Option3=2

    @classmethod
    def names(cls):
        """
        return enum fields as a list of strings
        """
        return [name for name, member in cls.__members__.items()]


class DAQ_NDViewer_Template(DAQ_Viewer_base):
    """
     Template to be used in order to write your own Move modules
    """

    #custom signal used to trigger data emission when recording is done
    callback_signal = QtCore.pyqtSignal()



    hardware_averaging = True #will use the accumulate acquisition mode if averaging is neccessary
    params= comon_parameters+[
        {'title': 'Dll library:', 'name': 'andor_lib', 'type': 'browsepath', 'value': libpath},
        
        {'title': 'Camera Settings:', 'name': 'camera_settings', 'type': 'group', 'expanded': True, 'children': [
            {'title': 'Camera SN:', 'name': 'camera_serialnumber', 'type': 'int', 'value': 0, 'readonly': True},
            {'title': 'Camera Model:', 'name': 'camera_model', 'type': 'str', 'value': '', 'readonly': True},

            {'title': 'Readout Modes:', 'name': 'readout', 'type': 'list', 'values': Orsay_Camera_ReadOut.names(), 'value': 'FullVertBinning'},
            {'title': 'Readout Settings:', 'name': 'readout_settings', 'type': 'group', 'children':[

                {'title': 'Single Track Settings:', 'name': 'st_settings', 'type': 'group', 'visible': False, 'children':[
                    {'title': 'Center pixel:', 'name': 'st_center', 'type': 'int', 'value': 1 , 'default':1, 'min':1},
                    {'title': 'Height:', 'name': 'st_height', 'type': 'int', 'value': 1 , 'default':1, 'min':1},
                ]},    
                {'title': 'Multi Track Settings:', 'name': 'mt_settings', 'type': 'group', 'visible': False, 'children':[
                    {'title': 'Ntrack:', 'name': 'mt_N', 'type': 'int', 'value': 1 , 'default':1, 'min':1},
                    {'title': 'Height:', 'name': 'mt_height', 'type': 'int', 'value': 1 , 'default':1, 'min':1},
                    {'title': 'Offset:', 'name': 'mt_offset', 'type': 'int', 'value': 1 , 'default':1, 'min':0},
                    {'title': 'Bottom:', 'name': 'mt_bottom', 'type': 'int', 'value': 1 , 'default':1, 'min':0, 'readonly': True},
                    {'title': 'Gap:', 'name': 'mt_gap', 'type': 'int', 'value': 1 , 'default':1, 'min':0, 'readonly': True},
                ]},
                {'title': 'Image Settings:', 'name': 'image_settings', 'type': 'group', 'visible': False, 'children':[
                    {'title': 'Binning along x:', 'name': 'bin_x', 'type': 'int', 'value': 1, 'default': 1, 'min': 1},
                    {'title': 'Binning along y:', 'name': 'bin_y', 'type': 'int', 'value': 1, 'default': 1, 'min': 1},
                    {'title': 'Start x:', 'name': 'im_startx', 'type': 'int', 'value': 1 , 'default':1, 'min':0},
                    {'title': 'End x:', 'name': 'im_endx', 'type': 'int', 'value': 1024 , 'default':1024, 'min':0},
                    {'title': 'Start y:', 'name': 'im_starty', 'type': 'int', 'value': 1 , 'default':1, 'min':1},
                    {'title': 'End y:', 'name': 'im_endy', 'type': 'int', 'value': 127 , 'default':127, 'min':1,},
                    ]},   
            ]},            
            {'title': 'Exposure (ms):', 'name': 'exposure', 'type': 'float', 'value': 0.01 , 'default':0.01, 'min': 0},
            
            {'title': 'Image size:', 'name': 'image_size', 'type': 'group', 'children':[
                {'title': 'Nx:', 'name': 'Nx', 'type': 'int', 'value': 0, 'default':0 , 'readonly': True},
                {'title': 'Ny:', 'name': 'Ny', 'type': 'int', 'value': 0 , 'default':0 , 'readonly': True},
                ]},
            
            {'title': 'Temperature Settings:', 'name': 'temperature_settings', 'type': 'group', 'children':[
                {'title': 'Set Point:', 'name': 'set_point', 'type': 'float', 'value': -20, 'default':-20},
                {'title': 'Current value:', 'name': 'current_value', 'type': 'float', 'value': 0 , 'default':0, 'readonly': True},
                {'title': 'Locked:', 'name': 'locked', 'type': 'led', 'value': False , 'default':False, 'readonly': True},
                ]},
            
            
        ]},
        
        {'title': 'Spectro Settings:', 'name': 'spectro_settings', 'type': 'group', 'expanded': True, 'children': [
            {'title': 'Spectro SN:', 'name': 'spectro_serialnumber', 'type': 'str', 'value': '', 'readonly': True},
            {'title': 'Wavelength (nm):', 'name': 'spectro_wl', 'type': 'float', 'value': 600, 'min': 0},
            {'title': 'Grating Settings:', 'name': 'grating_settings', 'type': 'group', 'expanded': True, 'children': [
                {'title': 'Grating:', 'name': 'grating', 'type': 'list'},
                {'title': 'Lines (/mm):', 'name': 'lines', 'type': 'int', 'readonly': True},
                {'title': 'Blaze WL (nm):', 'name': 'blaze', 'type': 'str', 'readonly': True},
            ]},
            {'title': 'Go to zero order:', 'name': 'zero_order', 'type': 'bool'},
        ]},
        ]


    def __init__(self,parent=None,params_state=None, control_type="camera"):

        super(DAQ_AndorSDK2,self).__init__(parent,params_state) #initialize base class with commom attributes and methods

        if self.control_type == "camera":
            self.settings.child('spectro_settings').hide()
        elif self.control_type == "shamrock":
            self.settings.child('camera_settings').hide()
        self.control_type = control_type
        self.x_axis=None
        self.y_axis=None
        self.controller=None
        self.data=None
        self.CCDSIZEX, self.CCDSIZEY=(None,None)
        self.data_pointer=None
        self.camera_done=False
        self.acquirred_image=None
        self.callback_thread = None
        self.Naverage = None
        self.data_shape = None #'Data2D' if sizey != 1 else 'Data1D'

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
        try:
            if param.name()=='set_point':
                self.controller.SetTemperature(param.value())

            elif param.name() == 'readout' or param.name() in custom_parameter_tree.iter_children(self.settings.child('camera_settings', 'readout_settings')):
                self.update_read_mode()
                
            elif param.name()=='exposure':
                self.controller.SetExposureTime(self.settings.child('camera_settings','exposure').value()/1000) #temp should be in s
                (err, timings) = self.controller.GetAcquisitionTimings()
                self.settings.child('camera_settings','exposure').setValue(timings['exposure']*1000)
            elif param.name() == 'grating':
                index_grating = self.grating_list.index(param.value())
                self.get_set_grating(index_grating)
                self.emit_status(ThreadCommand('show_splash', ["Setting wavelength"]))
                err = self.controller.SetWavelengthSR(0, self.settings.child('spectro_settings','spectro_wl').value())
                self.emit_status(ThreadCommand('close_splash'))

            elif param.name() == 'spectro_wl':
                self.emit_status(ThreadCommand('show_splash', ["Setting wavelength"]))
                err = self.controller.SetWavelengthSR(0, param.value())
                self.emit_status(ThreadCommand('close_splash'))

                if err != 'SHAMROCK_SUCCESS':
                    raise Exception(err)
                self.x_axis = self.get_xaxis()
            elif param.name() == 'zero_order':
                if param.value():
                    param.setValue(False)
                    err = self.controller.GotoZeroOrderSR(0)
                    if err != 'SHAMROCK_SUCCESS':
                        raise Exception(err)

            pass


        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))


    def emit_data(self):
        """
            Fonction used to emit data obtained by dataUnlocker callback.

            See Also
            --------
            DAQ_utils.ThreadCommand
        """
        try:
            self.ind_grabbed+=1
            sizey = self.settings.child('camera_settings','image_size','Ny').value()
            sizex = self.settings.child('camera_settings','image_size','Nx').value()
            self.controller.GetAcquiredDataNumpy(self.data_pointer, sizex*sizey)
            self.data_grabed_signal.emit([OrderedDict(name='Camera',data=[np.squeeze(self.data.reshape((sizey, sizex)).astype(np.float))], type=self.data_shape)])
            
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))



    def Ini_Detector(self,controller=None):
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
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None,controller=None))
        try:
            self.emit_status(ThreadCommand('show_splash', ["Initialising Camera and/or Shamrock"]))
            if self.settings.child(('controller_status')).value()=="Slave":
                if controller is None: 
                    raise Exception('no controller has been defined externally while this detector is a slave one')
                else:
                    self.controller = controller
            else:
                self.controller = _andorsdk.AndorSDK(self.settings.child(('andor_lib')).value(), self.control_type)

            if self.control_type == "camera" or self.control_type == "both":
                self.emit_status(ThreadCommand('show_splash', ["Set/Get Camera's settings"]))
                self.Ini_Camera()

            if self.control_type == "shamrock" or self.control_type == "both":
                self.emit_status(ThreadCommand('show_splash', ["Set/Get Shamrock's settings"]))
                self.Ini_Spectro()




            #%%%%%%% init axes from image
            self.x_axis=self.get_xaxis()
            self.y_axis=self.get_yaxis()
            self.status.x_axis=self.x_axis
            self.status.y_axis=self.y_axis
            self.status.initialized=True
            self.status.controller=self.controller
            self.emit_status(ThreadCommand('close_splash'))
            return self.status

        except Exception as e:
            self.status.info=str(e)
            self.status.initialized=False
            self.emit_status(ThreadCommand('close_splash'))
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
        locked_status, temp=self.controller.GetTemperature()
        self.settings.child('camera_settings','temperature_settings','current_value').setValue(temp)
        self.settings.child('camera_settings','temperature_settings','locked').setValue(locked_status == 'DRV_TEMP_STABILIZED')


    def Close(self):
        """

        """
        
        err, temp = self.controller.GetTemperature()
        if temp < -20:
            msgBox=QtWidgets.QMessageBox()
            msgBox.setText("Camera temperature is still at {:d}°C. Closing now may damage it!");
            msgBox.setInformativeText("The cooling will be maintained while shutting down camera. Keep it power plugged!!!");
            msgBox.show()

            QtWidgets.QApplication.processEvents()
            msgBox.exec()
            self.controller.SetCoolerMode(1)


        self.controller.Close()

    def get_xaxis(self):
        """
            Obtain the horizontal axis of the image.

            Returns
            -------
            1D numpy array
                Contains a vector of integer corresponding to the horizontal camera pixels.
        """
        if self.controller is not None:
            # if self.control_type == "camera":
            Nx=self.settings.child('camera_settings', 'image_size', 'Nx').value()
            self.x_axis = dict(data=np.linspace(0, Nx-1, Nx, dtype=np.int), label='Pixels')

            if self.control_type == "shamrock" or self.control_type == "both" and self.CCDSIZEX is not None:
                (err, calib) = self.controller.GetCalibrationSR(0, self.CCDSIZEX)
                calib = np.array(calib)
                if self.settings.child('camera_settings','readout').value() == Orsay_Camera_ReadOut['Image'].name:
                    binx = self.settings.child('camera_settings', 'readout_settings', 'image_settings', 'bin_x').value()
                    startx = self.settings.child('camera_settings', 'readout_settings', 'image_settings','im_startx').value()
                    endx = self.settings.child('camera_settings', 'readout_settings', 'image_settings','im_endx').value()
                    calib = calib[startx:endx+1:binx]

                if (calib.astype('int') != 0).all(): # check if calib values are equal to zero
                    self.x_axis = dict(data=calib, label='Wavelength (nm)')

            self.emit_x_axis()
        else:
            raise(Exception('controller not defined'))
        return self.x_axis

    def get_yaxis(self):
        """
            Obtain the vertical axis of the image.

            Returns
            -------
            1D numpy array
                Contains a vector of integer corresponding to the vertical camera pixels.
        """
        if self.controller is not None:

            Ny=self.settings.child('camera_settings','image_size','Ny').value()
            self.y_axis = dict(data=np.linspace(0, Ny-1, Ny, dtype=np.int), label='Pixels')
            self.emit_y_axis()
        else: raise(Exception('Camera not defined'))
        return self.y_axis

    def prepare_data(self):
        sizex = self.settings.child('camera_settings','image_size','Nx').value()
        sizey = self.settings.child('camera_settings','image_size','Ny').value()

        #%%%%%% Initialize data: self.data for the memory to store new data and self.data_average to store the average data
        image_size = sizex*sizey
        self.data = np.zeros((image_size,), dtype=np.long)
        self.data_pointer = self.data.ctypes.data_as(ctypes.c_void_p)

        data_shape = 'Data2D' if sizey != 1 else 'Data1D'
        if data_shape != self.data_shape:
            self.data_shape = data_shape
            #init the viewers
            self.data_grabed_signal_temp.emit([OrderedDict(name='Camera ',
                data=[np.squeeze(self.data.reshape((sizey,sizex)).astype(np.float))], type=self.data_shape)])

    def Grab(self,Naverage=1,**kwargs):
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
            self.camera_done = False

            self.ind_grabbed=0 #to keep track of the current image in the average
            self.Naverage = Naverage #

            self.prepare_data()
            if Naverage == 1:
                self.controller.SetAcquisitionMode(1)
            else:
                self.controller.SetAcquisitionMode(2)
                self.controller.SetNumberAccumulations(Naverage)
                
            self.controller.SetExposureTime(self.settings.child('camera_settings','exposure').value()/1000) #temp should be in s
            (err, timings) = self.controller.GetAcquisitionTimings()
            self.settings.child('camera_settings','exposure').setValue(timings['exposure']*1000)
            #%%%%% Start acquisition with the given exposure in ms, in "1d" or "2d" mode
            self.controller.StartAcquisition()
            self.callback_signal.emit()  #will trigger the waitfor acquisition

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),"log"]))

    def Stop(self):
        """
            Stop the camera's actions.
        """
        try:
            self.controller.CancelWait() #first cancel the waitacquistion (if any)
            QtWidgets.QApplication.processEvents()
            self.controller.AbortAcquisition() #abor the camera actions


        except: pass
        return ""

class AndorCallback(QtCore.QObject):
    """

    """
    data_sig=QtCore.pyqtSignal()
    def __init__(self,wait_fn):
        super(AndorCallback, self).__init__()
        self.wait_fn = wait_fn

    def wait_for_acquisition(self):
        err = self.wait_fn()

        if err != 'DRV_NO_NEW_DATA': #will be returned if the main thread called CancelWait
            self.data_sig.emit()

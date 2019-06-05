#template example

#mandatory imports
from pymodaq.daq_utils.daq_utils import ThreadCommand
from pymodaq.daq_viewer.utility_classes import comon_parameters
from pymodaq.daq_utils import custom_parameter_tree
from pymodaq.daq_viewer.utility_classes import DAQ_Viewer_base
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
     Template to be used in order to write your own viewer modules
    """

    #custom signal used to trigger data emission when recording is done
    callback_signal = QtCore.pyqtSignal()
    hardware_averaging = False #will use the accumulate acquisition mode if averaging is True else averaging is done software
                               # wise by the viewer module
    params= comon_parameters+[
        # comon_parameters as defined in utility_class. it has to be present in all plugins

        #below: custom settings for this plugin
        {'title': 'Dll library:', 'name': 'andor_lib', 'type': 'browsepath', 'value': libpath},
        
        {'title': 'Camera Settings:', 'name': 'camera_settings', 'type': 'group', 'expanded': True, 'children': [
            {'title': 'Camera SN:', 'name': 'camera_serialnumber', 'type': 'int', 'value': 0, 'readonly': True},
            {'title': 'Camera Model:', 'name': 'camera_model', 'type': 'str', 'value': '', 'readonly': True},

            {'title': 'Readout Modes:', 'name': 'readout', 'type': 'list', 'values': Orsay_Camera_ReadOut.names(), 'value': 'FullVertBinning'},
            {'title': 'Readout Settings:', 'name': 'readout_settings', 'type': 'group', 'children':[

                {'title': 'single Track Settings:', 'name': 'st_settings', 'type': 'group', 'visible': False, 'children':[
                    {'title': 'Center pixel:', 'name': 'st_center', 'type': 'int', 'value': 1 , 'default':1, 'min':1},
                    {'title': 'Height:', 'name': 'st_height', 'type': 'int', 'value': 1 , 'default':1, 'min':1},
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
            ]},
        ]

    def __init__(self,parent=None,params_state=None):
        #the super will call parent class initialization where , for instance, self.settings is created
        super(DAQ_NDViewer_Template,self).__init__(parent,params_state) #initialize base class with commom attributes and methods

        self.x_axis=None
        self.y_axis=None
        self.controller=None

        ########################## to modify below #####################
        #################################################################
        self.data=None
        self.CCDSIZEX, self.CCDSIZEY=(None,None)
        self.data_pointer=None
        self.camera_done=False
        self.acquirred_image=None
        self.callback_thread = None
        self.Naverage = None
        self.data_shape = None #'Data2D' if sizey != 1 else 'Data1D'
        #####################################################################################

    def commit_settings(self,param):
        """
        Activate parameters changes on the hardware from parameter's name.
        see documentation :ref:`hardware_settings`
        """

        try:
        ###############################################################
        ##################to modify below ###############################

            if param.name()=='set_point':
                self.controller.SetTemperature(param.value())

            elif param.name() == 'readout' or param.name() in custom_parameter_tree.iter_children(self.settings.child('camera_settings', 'readout_settings')):
                self.update_read_mode()
                
            elif param.name()=='exposure':
                self.controller.SetExposureTime(self.settings.child('camera_settings','exposure').value()/1000) #temp should be in s
                (err, timings) = self.controller.GetAcquisitionTimings()
                self.settings.child('camera_settings','exposure').setValue(timings['exposure']*1000)

        ####################################################################
        #########################################################################

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))

    def emit_data(self):
        """
        Function used to emit data when data ready. optional see Plugins documentation


        """
        try:

            ########################## to modify below #####################
            #################################################################
            self.ind_grabbed+=1
            sizey = self.settings.child('camera_settings','image_size','Ny').value()
            sizex = self.settings.child('camera_settings','image_size','Nx').value()
            self.controller.GetAcquiredDataNumpy(self.data_pointer, sizex*sizey)
            self.data_grabed_signal.emit([OrderedDict(name='Camera',data=[np.squeeze(self.data.reshape((sizey, sizex)).astype(np.float))], type=self.data_shape)])
            #######################################################################
            ##################################################################

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))

    def ini_detector(self, controller=None):
        """
        init hardware

        """
        ########################## to adapt below #####################
        #################################################################
        self.emit_status(ThreadCommand('show_splash', ["Initialising Camera and/or Shamrock"]))
        #######################################################
        #############################################

        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None,controller=None))
        try:
            if self.settings.child(('controller_status')).value()=="Slave":
                if controller is None: 
                    raise Exception('no controller has been defined externally while this detector is a slave one')
                else:
                    self.controller = controller
            else:

                ########################## to adapt below #####################
                #################################################################
                self.controller = _andorsdk.AndorSDK(self.settings.child(('andor_lib')).value(), self.control_type)
                ######################################################

            ########################## to adapt below if one requirre a reproducible event#####################
            ###########################see the timerEvent method that will be triggered######################################
            self.timer = self.startTimer(2000)  # Timer event fired every 2s
            #################################################################


            #%%%%%%% init axes from hardware: do xaxis if 1D viewer do both if 2D viewer
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

    ########################## to adapt below if a timer has been set#####################
    #################################################################
    def timerEvent(self, event):
        """
            | Called by set timer
            | Used here to update temperature status.
        """
        locked_status, temp=self.controller.GetTemperature()
        self.settings.child('camera_settings','temperature_settings','current_value').setValue(temp)
        self.settings.child('camera_settings','temperature_settings','locked').setValue(locked_status == 'DRV_TEMP_STABILIZED')
    ######################################################################################
    ##############################################################################

    def close(self):
        """

        """
        ########################## to adapt below #####################
        ################### write whatever is needed before closing hardware###################

        err, temp = self.controller.GetTemperature()
        if temp < -20:
            msgBox=QtWidgets.QMessageBox()
            msgBox.setText("Camera temperature is still at {:d}°C. Closing now may damage it!");
            msgBox.setInformativeText("The cooling will be maintained while shutting down camera. Keep it power plugged!!!");
            msgBox.show()

            QtWidgets.QApplication.processEvents()
            msgBox.exec()
            self.controller.SetCoolerMode(1)
        ############################################################

        self.controller.close() #put here any specific close method of your hardware/controller if any

    def get_xaxis(self):
        """
            Obtain the horizontal axis of the detectorf.

            Returns
            -------
            1D numpy array
        """
        if self.controller is not None:

            ########################## to adapt below #####################
            #################################################################
            Nx=self.settings.child('camera_settings', 'image_size', 'Nx').value()
            self.x_axis = dict(data=calib, label='Wavelength (nm)')
            ###############################################
            #############################################

            self.emit_x_axis()
        else:
            raise(Exception('controller not defined'))
        return self.x_axis

    def get_yaxis(self):
        """
            Obtain the vertical axis of the detector if any.

            Returns
            -------
            1D numpy array
        """
        if self.controller is not None:
            ########################## to adapt below #####################
            #################################################################
            Ny=self.settings.child('camera_settings','image_size','Ny').value()
            self.y_axis = dict(data=np.linspace(0, Ny-1, Ny, dtype=np.int), label='Pixels')
            #######################################

            self.emit_y_axis()
        else: raise(Exception('Camera not defined'))
        return self.y_axis

    def grab(self, Naverage=1, **kwargs):
        """

        """
        try:
            ########################## to adapt below #####################
            #################################################################
            #the content here will depend on the way your are finally getting the data see Plugins documentation
            self.controller.StartAcquisition()
            self.callback_signal.emit()  #will trigger the waitfor acquisition in the separated class
            ###############################################
            #################################################################


        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),"log"]))

    def stop(self):
        """
            stop the camera's actions.
        """
        try:
            self.controller.CancelWait() #first cancel the waitacquistion (if any)
            QtWidgets.QApplication.processEvents()
            self.controller.AbortAcquisition() #abor the camera actions


        except: pass
        return ""

class DetectorCallback(QtCore.QObject):
    """

    """
    data_sig=QtCore.pyqtSignal()
    def __init__(self,wait_fn):
        super(DetectorCallback, self).__init__()
        self.wait_fn = wait_fn

    def wait_for_acquisition(self):
        err = self.wait_fn()

        if err != 'DRV_NO_NEW_DATA': #will be returned if the main thread called CancelWait
            self.data_sig.emit()

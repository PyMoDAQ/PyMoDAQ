import numpy as np
from enum import IntEnum
import ctypes
import platform
from collections import OrderedDict
from PyQt5 import QtWidgets, QtCore
from easydict import EasyDict as edict
from pymodaq.daq_viewer.utility_classes import DAQ_Viewer_base

from pymodaq.daq_utils.daq_utils import ThreadCommand
from pymodaq.daq_viewer.utility_classes import comon_parameters
from pymodaq.plugins.hardware.andor import _andorsdk
from pymodaq.daq_utils import custom_parameter_tree


if platform.system() == "Linux":
    libpath=ctypes.util.find_library('libandor') #to be checked
elif platform.system() == "Windows":
    if platform.machine() == "AMD64":
        libpath=ctypes.util.find_library('atmcd64d')
    else:
        libpath=ctypes.util.find_library('atmcd32d')

class Orsay_Camera_ReadOut(IntEnum):
    """
        Enum class of readout modes.

        =============== =======================
        **Attributes**    **Type**
        *names*          string list of members
        =============== =======================
    """
    
    FullVertBinning=0
    SingleTrack=3
    MultiTrack=1
    RandomTrack=2
    Image=4
    Cropped=5


    @classmethod
    def names(cls):
        return [name for name, member in cls.__members__.items()]

class Orsay_Camera_AcqMode(IntEnum):
    """
        Enum class of AcqModes modes.

        =============== =======================
        **Attributes**    **Type**
        *names*          string list of members
        =============== =======================
    """
    Single_Scan = 1
    Accumulate = 2
    Kinetics = 3
    Fast_Kinetics = 4
    Run_till_abort = 5


    @classmethod
    def names(cls):
        return [name for name, member in cls.__members__.items()]


class DAQ_AndorSDK2(DAQ_Viewer_base):
    """
        Base class for Andor CCD camera and Shamrock spectrometer


        =============== ==================
        **Attributes**   **Type**

        =============== ==================

        See Also
        --------
        utility_classes.DAQ_Viewer_base
    """
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
            daq_utils.ThreadCommand
        """
        try:
            self.ind_grabbed+=1
            sizey = self.settings.child('camera_settings','image_size','Ny').value()
            sizex = self.settings.child('camera_settings','image_size','Nx').value()
            self.controller.GetAcquiredDataNumpy(self.data_pointer, sizex*sizey)
            self.data_grabed_signal.emit([OrderedDict(name='Camera',data=[np.squeeze(self.data.reshape((sizey, sizex)).astype(np.float))], type=self.data_shape)])
            
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))


    def update_read_mode(self):
        read_mode=Orsay_Camera_ReadOut[self.settings.child('camera_settings','readout').value()].value
        err = self.controller.SetReadMode(read_mode)
        if err != 'DRV_SUCCESS':
            self.emit_status(ThreadCommand('Update_Status',[err,'log']))
        else:
            self.settings.child('camera_settings', 'readout_settings').show()
            if read_mode == 0:#FVB:
                self.settings.child('camera_settings', 'readout_settings').hide()
                self.settings.child('camera_settings','image_size','Nx').setValue(self.CCDSIZEX)
                self.settings.child('camera_settings','image_size','Ny').setValue(1)


            elif read_mode == 3: #single track
                self.settings.child('camera_settings', 'readout_settings','mt_settings').hide()
                self.settings.child('camera_settings', 'readout_settings','st_settings').show()
                self.settings.child('camera_settings', 'readout_settings','image_settings').hide()

                err = self.set_single_track_area()

            elif read_mode == 1: #multitrack
                self.settings.child('camera_settings', 'readout_settings','mt_settings').show()
                self.settings.child('camera_settings', 'readout_settings','st_settings').hide()
                self.settings.child('camera_settings', 'readout_settings','image_settings').hide()

                err = self.set_multi_track_area()



            elif read_mode == 2: #random
                err = 'Random mode not implemented yet'
                
            elif read_mode == 4: #image
                self.settings.child('camera_settings', 'readout_settings','mt_settings').hide()
                self.settings.child('camera_settings', 'readout_settings','st_settings').hide()
                self.settings.child('camera_settings', 'readout_settings','image_settings').show()

                self.set_image_area()

                
            elif read_mode == 5: #croped
                err = 'Croped mode not implemented yet'
            self.emit_status(ThreadCommand('Update_Status',[err,'log']))
            
            (err, timings) = self.controller.GetAcquisitionTimings()
            self.settings.child('camera_settings', 'exposure').setValue(timings['exposure']*1000)

            self.x_axis = self.get_xaxis()
            self.y_axis = self.get_yaxis()

    def set_multi_track_area(self):

        N = self.settings.child('camera_settings', 'readout_settings', 'mt_settings', 'mt_N').value()
        height = self.settings.child('camera_settings', 'readout_settings', 'mt_settings', 'mt_height').value()
        offset = self.settings.child('camera_settings', 'readout_settings', 'mt_settings', 'mt_offset').value()
        (err, bottom, gap) = self.controller.SetMultiTrack(N, height, offset)
        self.settings.child('camera_settings', 'readout_settings', 'mt_settings', 'mt_bottom').setValue(bottom)
        self.settings.child('camera_settings', 'readout_settings', 'mt_settings', 'mt_gap').setValue(gap)
        if err == 'DRV_SUCCESS':
            self.settings.child('camera_settings', 'image_size', 'Nx').setValue(self.CCDSIZEX)
            self.settings.child('camera_settings', 'image_size', 'Ny').setValue(N)
        return err

    def set_single_track_area(self):
        center = self.settings.child('camera_settings', 'readout_settings', 'st_settings', 'st_center').value()
        height = self.settings.child('camera_settings', 'readout_settings', 'st_settings', 'st_height').value()
        err = self.controller.SetSingleTrack(center, height)
        if err == 'DRV_SUCCESS':
            self.settings.child('camera_settings', 'image_size', 'Nx').setValue(self.CCDSIZEX)
            self.settings.child('camera_settings', 'image_size', 'Ny').setValue(1)

        return err


    def set_image_area(self):

        binx = self.settings.child('camera_settings', 'readout_settings', 'image_settings', 'bin_x').value()
        biny = self.settings.child('camera_settings', 'readout_settings','image_settings', 'bin_y').value()
        startx = self.settings.child('camera_settings', 'readout_settings', 'image_settings', 'im_startx').value()
        endx = self.settings.child('camera_settings', 'readout_settings', 'image_settings', 'im_endx').value()
        starty = self.settings.child('camera_settings', 'readout_settings', 'image_settings', 'im_starty').value()
        endy = self.settings.child('camera_settings', 'readout_settings', 'image_settings', 'im_endy').value()
        err = self.controller.SetImage(binx, biny, startx, endx, starty, endy)
        if err == 'DRV_SUCCESS':
            self.settings.child('camera_settings', 'image_size', 'Nx').setValue(int((endx-startx+1)/binx))
            self.settings.child('camera_settings', 'image_size', 'Ny').setValue(int((endy-starty+1)/biny))

        return err

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
            daq_utils.ThreadCommand, hardware1D.DAQ_1DViewer_Picoscope.update_pico_settings
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

    def Ini_Spectro(self):
        self.settings.child('spectro_settings', 'spectro_serialnumber').setValue(
            self.controller.GetSerialNumberSR(0)[1].decode())
        #get grating info
        (err, Ngratings) = self.controller.GetNumberGratingsSR(0)
        self.grating_list = []
        for ind_grating in range(1, Ngratings+1):
            (err, lines, blaze, home, offset) = self.controller.GetGratingInfoSR(0,ind_grating)
            self.grating_list.append(str(int(lines)))
        self.settings.child('spectro_settings', 'grating_settings', 'grating').setLimits(self.grating_list)
        err, ind_grating = self.controller.GetGratingSR(0)
        self.settings.child('spectro_settings', 'grating_settings', 'grating').setValue(self.grating_list[ind_grating-1])

        self.get_set_grating(ind_grating-1)

        #setNpixels
        if self.CCDSIZEX is not None:
            err = self.controller.SetNumberPixelsSR(0, self.CCDSIZEX)
            (err, (pxl_width, pxl_height)) = self.controller.GetPixelSize()
            err = self.controller.SetPixelWidthSR(0, pxl_width)

            err, wl = self.controller.GetWavelengthSR(0)
            self.settings.child('spectro_settings','spectro_wl').setValue(wl)
            self.x_axis = self.get_xaxis()

    def get_set_grating(self, ind_grating):
        """
        set the current grating to ind_grating+1. ind_grating corresponds to the index in the GUI graitng list while the SDK index starts at 1...

        """
        self.emit_status(ThreadCommand('show_splash',["Moving grating please wait"]))
        err = self.controller.SetGratingSR(0, ind_grating+1)
        err, ind_grating = self.controller.GetGratingSR(0)

        (err, lines, blaze, home, offset) = self.controller.GetGratingInfoSR(0, ind_grating)
        self.settings.child('spectro_settings', 'grating_settings', 'grating').setValue(self.grating_list[ind_grating-1])
        self.settings.child('spectro_settings', 'grating_settings', 'lines').setValue(lines)
        self.settings.child('spectro_settings', 'grating_settings', 'blaze').setValue(blaze)

        (err,wl_min,wl_max) = self.controller.GetWavelengthLimitsSR(0, ind_grating)

        if err == "SHAMROCK_SUCCESS":
            self.settings.child('spectro_settings','spectro_wl').setLimits((wl_min, wl_max))


        self.emit_status(ThreadCommand('close_splash'))



    def Ini_Camera(self):


        # %%%%%% Get image size and current binning
        # get info from camera
        self.settings.child('camera_settings', 'camera_serialnumber').setValue(self.controller.GetCameraSerialNumber())
        self.settings.child('camera_settings', 'camera_model').setValue(self.controller.GetHeadModel().decode())


        self.CCDSIZEX, self.CCDSIZEY = self.controller.GetDetector()
        self.settings.child('camera_settings', 'readout_settings',
                            'st_settings', 'st_center').setLimits((1, self.CCDSIZEY))
        self.settings.child('camera_settings', 'readout_settings',
                            'st_settings', 'st_height').setLimits((1, self.CCDSIZEY))

        # get max exposure range
        err, maxexpo = self.controller.GetMaximumExposure()
        if err == 'DRV_SUCCESS':
            self.settings.child('camera_settings', 'exposure').setLimits((0, maxexpo))

        # set default read mode (full vertical binning)
        self.update_read_mode()

        # %%%%%%% Set and Get temperature from camera
        # get temperature range
        (err, temp_range) = self.controller.GetTemperatureRange()
        if err == "DRV_SUCCESS":
            self.settings.child('camera_settings', 'temperature_settings', 'set_point').setLimits(
                (temp_range[0], temp_range[1]))

        if not self.controller.IsCoolerOn():  # gets 0 or 1
            self.controller.CoolerON()

        self.controller.SetTemperature(
            self.settings.child('camera_settings', 'temperature_settings', 'set_point').value())
        locked_status, temp = self.controller.GetTemperature()
        self.settings.child('camera_settings', 'temperature_settings', 'current_value').setValue(temp)
        self.settings.child('camera_settings', 'temperature_settings', 'locked').setValue(
            locked_status == 'DRV_TEMP_STABILIZED')
        # set timer to update temperature info from controller
        self.timer = self.startTimer(2000)  # Timer event fired every 2s

        callback = AndorCallback(self.controller.WaitForAcquisition)
        self.callback_thread = QtCore.QThread()
        callback.moveToThread(self.callback_thread)
        callback.data_sig.connect(
            self.emit_data)  # when the wait for acquisition returns (with data taken), emit_data will be fired

        self.callback_signal.connect(callback.wait_for_acquisition)
        self.callback_thread.callback = callback
        self.callback_thread.start()


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
            daq_utils.ThreadCommand
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

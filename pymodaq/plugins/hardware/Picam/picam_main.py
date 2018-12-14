# -*- coding: utf-8 -*-
"""
Created on Wed Jan 10 14:33:53 2018

@author: Weber
"""

import numpy as np
import ctypes
from ctypes import pointer, byref
from ctypes.util import find_library

from Picam_types.PiTypes import piint, pi64s, pi16u, pibln, piflt
from Picam_types.PiTypesMore import PicamModel, PicamCameraID, PicamHandle, PicamAvailableData, PicamAcquisitionErrorsMask, PicamRangeConstraint
from enums.picam_model_enum import PicamModelEnum
from enums.picam_computer_interface_enum import PicamComputerInterfaceEnum
import enums.picam_parameter_enum as param_enum
from enums.picam_parameter_enum import PicamParameterEnum, PicamValueType, PicamConstaintType
from enums.picam_error_enum import PicamErrorEnum

import numpy as np
from pyqtgraph.parametertree import Parameter


class Picam(object):
    """
    Initialize an object to control the pixis camera. It uses ctypes library and the .dll or .so dynamic libraries
    """

    def __init__(self):
        super(Picam,self).__init__()
        libpath = 'C:\\Program Files\\Princeton Instruments\\PICam\\Runtime\\Picam.dll'
        self._picamlib=ctypes.windll.LoadLibrary(libpath) #object containing all picam functions
        self._cam=PicamHandle()
        self._camId=PicamCameraID()
        self.parameters_list=[]
        
        
        
        self._open_library()
        
        #check library version
        major = piint()
        minor = piint()
        distribution = piint()
        release = piint()
        err=self._picamlib.Picam_GetVersion(pointer(major),pointer(minor),pointer(distribution),pointer(release))
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
        print('Picam Version '+str(major.value)+'.'+str(minor.value)+'.'+str(distribution.value)+' Released: '+str(release.value))
        
    def _open_library(self):
        #check if library is initialized
        initialized=pibln()
        err=self._picamlib.Picam_IsLibraryInitialized(byref(initialized))
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
        #if not initialized do it    
        if not initialized.value:
            err=self._picamlib.Picam_InitializeLibrary()
            if err!=0:
                raise(Exception(PicamErrorEnum(err).name))
        
    def _close_library(self):
        err=self._picamlib.Picam_UninitializeLibrary()
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
        
    def close(self):
        #first get all opened camera and closed them:
        cameras=self.get_open_cameras()
        for camera in cameras:
            self.close_camera(camera)
        self._close_library()
    
    def get_open_cameras(self) -> list:
        buffer_type=PicamHandle * 4
        handles =pointer(buffer_type())
        count=piint(0)
        err=self._picamlib.Picam_GetOpenCameras(byref(handles),byref(count))
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
        if count.value!=0:
            buffer_type=PicamHandle * count.value
            handles =pointer(buffer_type())
            count=piint(0)
            err=self._picamlib.Picam_GetOpenCameras(byref(handles),byref(count))
            if err!=0:
                raise(Exception(PicamErrorEnum(err).name))
            return handles.contents
        else:
             return []
        
    def get_available_camera_IDs(self) -> list:
        Ids_list=[]
        buffer_type=PicamCameraID * 4
        Ids =pointer(buffer_type())
        count=piint(0)
        err=self._picamlib.Picam_GetAvailableCameraIDs(byref(Ids),byref(count))
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
        if count.value==0:
            raise(Exception("No available Camera"))
        
        #release memory
        err=self._picamlib.Picam_DestroyCameraIDs(Ids)
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
            
        buffer_type=PicamCameraID *count.value
        Ids =pointer(buffer_type())
        count=piint(0)
        err=self._picamlib.Picam_GetAvailableCameraIDs(byref(Ids),byref(count))
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
        Ids_list=Ids.contents[:]
        
        #release memory
        err=self._picamlib.Picam_DestroyCameraIDs(Ids)
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
        return Ids_list
    
    def get_democamera_models(self) -> list:
        models_list=[]
        buffer_type=ctypes.c_long * 4
        models =pointer(buffer_type(0))
        count=piint(0)
        err=self._picamlib.Picam_GetAvailableDemoCameraModels(byref(models),byref(count))
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
        #release memory
        err=self._picamlib.Picam_DestroyModels(models)
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
            
        if count.value==0:
            raise(Exception("No available Camera"))
        buffer_type=ctypes.c_long *count.value
        models =pointer(buffer_type(0))
        count=pointer(piint(0))
        err=self._picamlib.Picam_GetAvailableDemoCameraModels(byref(models),byref(count))
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))        
        models_list=models.contents[:]
        #release memory
        err=self._picamlib.Picam_DestroyModels(models)
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
        

        return models_list
    
    def connect_demo_camera(self,model_cam: int) -> PicamCameraID:
        model = ctypes.c_long(model_cam)
        serial_number = pointer(ctypes.c_wchar_p(''))
        PicamID = PicamCameraID()  
        err=self._picamlib.Picam_ConnectDemoCamera(model, serial_number, byref(PicamID))
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
        
        print('Camera model is '+PicamModelEnum(PicamID.model).name)
        print('Camera computer interface is '+PicamComputerInterfaceEnum(PicamID.computer_interface).name)
        print('Camera sensor_name is '+str(PicamID.sensor_name))
        print('Camera serial number is'+ str(PicamID.serial_number))
        self._camId=PicamID
        return PicamID
    
    def check_connected_camera(self,id_cam: PicamCameraID) -> bool:
        connected=pibln()
        err=self._picamlib.Picam_IsCameraIDConnected(byref(ctypes.c_long(id_cam)),byref(connected))
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
        return connected.value
           
            
    def open_camera(self,id_cam: PicamCameraID=None) -> PicamHandle:
        if id_cam==None:
            id_cam=self._camId
            
        camera=PicamHandle()
        err=self._picamlib.Picam_OpenCamera(byref(id_cam),byref(camera))
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
        self._cam=camera
        return camera
    
    def close_camera(self,camera=None):
        if camera is None:
            camera=self._cam
        err=self._picamlib.Picam_CloseCamera(camera)
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
    
    
    def get_parameters(self,cam:PicamHandle=None) -> list:
        params=[]
        if cam==None:
            cam=self._cam
            
        buffer_type=piint * 4
        parameters =pointer(buffer_type())
        count=piint(0)
        err=self._picamlib.Picam_GetParameters(cam,byref(parameters),byref(count))
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
        if count.value==0:
            raise(Exception("No available Parameters"))
            
        buffer_type=piint * count.value
        parameters =pointer(buffer_type())
        count=piint(0)
        err=self._picamlib.Picam_GetParameters(cam,byref(parameters),byref(count))
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
        vals=parameters.contents[:]
        
        #release memory
        err=self._picamlib.Picam_DestroyParameters(parameters)
        if err!=0:
            raise(Exception(PicamErrorEnum(err).name))
            
        # all indexes in the global list of parameters
        vals_enum=[v.value for v in PicamParameterEnum]
        
        for p in vals: #all available parameters for the given hardware
            if p in vals_enum: #check if it is in the list
                #check if this parameter is relevent for the hardware
                relevant=pibln()
                err=self._picamlib.Picam_IsParameterRelevant(cam,p,byref(relevant))
                if err!=0:
                    raise(Exception(PicamErrorEnum(err).name))
                if relevant.value:
                    params.append(PicamParameterEnum(p).name)
        self.parameters_list=params
        
        #to do create parameters list in a parameters object with read/write permissions and constraints...
        
        return params
    
    def create_parameters_object(self,cam:PicamHandle=None,params:list=None):
        """
        
        PicamParameter_FrameSize
        PicamParameter_PixelBitDepth',
       
        PicamParameter_SensorTemperatureReading',
        PicamParameter_SensorTemperatureStatus'
        PicamParameter_SensorTemperatureSetPoint',
        
        PicamParameter_ExposureTime',
        PicamParameter_TimeStamps',
        """
        mandatory_params=['PicamParameter_SensorTemperatureSetPoint','PicamParameter_ExposureTime', 'PicamParameter_ActiveWidth',
                          'PicamParameter_ActiveHeight','PicamParameter_FrameSize','PicamParameter_PixelBitDepth',
                          'PicamParameter_SensorTemperatureReading','PicamParameter_SensorTemperatureStatus',
                          
                          'PicamParameter_TimeStamps']
        

        if cam is None:
            cam=self._cam
        if params is None:
            params=mandatory_params
            
        params_list=[]
        for p_str in params:
            #%% get constraint type:
            ctr_type=piint()
            err=self._picamlib.Picam_GetParameterConstraintType(cam,PicamParameterEnum[p_str].value,byref(ctr_type))
            if err!=0:
                raise(Exception(PicamErrorEnum(err).name))
            
            #%% get value type %%%%%%%%%%%%%%%%%%%%%%%%%%%%
            value_type=piint()
            err=self._picamlib.Picam_GetParameterValueType(cam,PicamParameterEnum[p_str].value,byref(value_type))
            if err!=0:
                raise(Exception(PicamErrorEnum(err).name))
            value_ctypes=param_enum.parameter_value_type(value_type.value)
            
            #%% get value access  %%%%%%%%%%%%%%%%%%%%%%%%%%
            access=piint()
            err=self._picamlib.Picam_GetParameterValueAccess(cam,PicamParameterEnum[p_str].value,byref(access))
            if err!=0:
                raise(Exception(PicamErrorEnum(err).name))
            if access.value==0:
                access_read_only=True
            else: 
                access_read_only=False
                
            #%% check the constraints  
            PicamConstraintCategory=piint(2)
            """
            PicamConstraintType_None        = 1,
            PicamConstraintType_Range       = 2,
            PicamConstraintType_Collection  = 3,
            PicamConstraintType_Rois        = 4,
            PicamConstraintType_Pulse       = 5,
            PicamConstraintType_Modulations = 6
            """
            
            if ctr_type.value==2:
                buffer_type=PicamRangeConstraint*10
                range_cstr=pointer(buffer_type())
                err=self._picamlib.Picam_GetParameterRangeConstraint(cam,PicamParameterEnum[p_str].value,PicamConstraintCategory,range_cstr)
                if err!=0:
                    raise(Exception(PicamErrorEnum(err).name))     
                
            #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%    
            if  value_type.value==1:
                ptype='int'
                #test if the parameter can be read from hardware
                readable=pibln()
                err=self._picamlib.Picam_CanReadParameter(cam,PicamParameterEnum[p_str].value,byref(readable))
                if err!=0:
                    raise(Exception(PicamErrorEnum(err).name))
                if readable.value: # if true read the param value from hardware
                    value=piint()
                    err=self._picamlib.Picam_ReadParameterIntegerValue(cam,PicamParameterEnum[p_str].value,byref(value))
                    if err!=0:
                        raise(Exception(PicamErrorEnum(err).name))
                else: #otherwise get it from stored value
                    value=piint()
                    err=self._picamlib.Picam_GetParameterIntegerValue(cam,PicamParameterEnum[p_str].value,byref(value))
                    if err!=0:
                        raise(Exception(PicamErrorEnum(err).name))
                #create integer parameter
                params_list.append({'name': p_str[15:], 'readonly': access_read_only, 'type':ptype, 'value': value.value  })    
            #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            elif value_type.value==2:
                ptype='float'
                #test if the parameter can be read from hardware
                readable=pibln()
                err=self._picamlib.Picam_CanReadParameter(cam,PicamParameterEnum[p_str].value,byref(readable))
                if err!=0:
                    raise(Exception(PicamErrorEnum(err).name))
                if readable.value: # if true read the param value from hardware
                    value=piflt()
                    err=self._picamlib.Picam_ReadParameterFloatingPointValue(cam,PicamParameterEnum[p_str].value,byref(value))
                    if err!=0:
                        raise(Exception(PicamErrorEnum(err).name))
                else: #otherwise get it from stored value
                    value=piflt()
                    err=self._picamlib.Picam_GetParameterFloatingPointValue(cam,PicamParameterEnum[p_str].value,byref(value))
                    if err!=0:
                        raise(Exception(PicamErrorEnum(err).name))

                    
                    
#Picam_GetParameterIntegerDefaultValue()
#— Picam_GetParameterFloatingPointDefaultValue()
                    
                    
                #create floatingpoint parameter
                params_list.append({'name': p_str[15:], 'readonly': access_read_only, 'type':ptype, 'value': value.value  })    
            #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
            elif value_type.value==3:
                ptype='bool'
                value=piint()
                err=self._picamlib.Picam_GetParameterIntegerValue(cam,PicamParameterEnum[p_str].value,byref(value))
                if err!=0:
                    raise(Exception(PicamErrorEnum(err).name))
                #create integer parameter
                if value==0:
                    boolean=False
                else: boolean=True
                params_list.append({'name': p_str[15:], 'readonly': access_read_only, 'type':ptype, 'value': boolean  }) 
            #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%    
            elif value_type.value==4:
                ptype='list'
            
            
            #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%    
            elif value_type.value==6:
                ptype='int'
                value=pi64s()
                err=self._picamlib.Picam_GetParameterLargeIntegerValue(cam,PicamParameterEnum[p_str].value,byref(value))
                if err!=0:
                    raise(Exception(PicamErrorEnum(err).name))
                #create integer parameter
                params_list.append({'name': p_str[15:], 'readonly': access_read_only, 'type':ptype, 'value': value.value  }) 
                

#            self.DAQscan_settings=Parameter.create(name='Settings', type='group', children=params) 
    

class PicamCameraID_Py(object):
    def __init__(self,PicamID:PicamCameraID):
        self.model=PicamID.model
        self.serial_number=PicamID.serial_number
        self.sensor_name=PicamID.sensor_name
        self.computer_interface=PicamID.computer_interface
        
    def __str__(self):
        return 'Camera model is '+str(self.model)+' / Camera computer interface is '+str(self.computer_interface)+' / Camera sensor_name is '+str(self.sensor_name)+' / Camera serial number is'+ str(self.serial_number)


   
#        
#        
if __name__=='__main__':
    pic=Picam()
    pic.connect_demo_camera(28)
    pic.open_camera()
    pic.get_parameters()
    pic.create_parameters_object()
        
        
        
        
        
        
        
        
        
        
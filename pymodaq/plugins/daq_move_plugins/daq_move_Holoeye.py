
import os
from PyQt5 import QtWidgets
import sys
sys.path.append(os.getenv("HEDS_PYTHON_MODULES",""))
from holoeye import slmdisplaysdk
from pymodaq.daq_utils.daq_utils import select_file
from pymodaq.daq_move.utility_classes import DAQ_Move_base
from pymodaq.daq_move.utility_classes import comon_parameters
from pymodaq.daq_utils.daq_utils import ThreadCommand

from pymodaq.daq_utils import daq_utils, h5browser
from easydict import EasyDict as edict
from enum import IntEnum
import tables
import numpy as np

class HoloeyeControls(IntEnum):

    FullScreen=0
    SplitScreen=1
    File=2
    
    @classmethod
    def names(cls):
        names=cls.__members__.items()
        return [name for name, member in cls.__members__.items()]




class DAQ_Move_Holoeye(DAQ_Move_base):
    """
        Wrapper object to access the Mock fonctionnalities, similar wrapper for all controllers.

        =============== ==============
        **Attributes**    **Type**
        *params*          dictionnary
        =============== ==============
    """
    is_multiaxes=False
    stage_names=[]


    params= [{'title': 'Show Preview?:', 'name': 'show_preview', 'type': 'bool', 'value': False},
             {'title': 'Shaping type:', 'name': 'shaping_type', 'type': 'list', 'value': HoloeyeControls.names()[2],  'values': HoloeyeControls.names()},
             {'title': 'Splitting options:', 'name': 'splitting', 'type': 'group','visible': True, 'children':[
                 {'title': 'Splitting control:', 'name': 'split_control', 'type': 'list', 'values': ['Screen spliting','GreyA','GreyB']},
                 {'title': 'Splitting value:', 'name': 'split_value', 'type': 'float', 'value': 0.5, 'min': 0, 'max': 1},
                 {'title': 'Grey A value:', 'name': 'greyA_value', 'type': 'int', 'value': 0, 'min': 0, 'max': 255},
                 {'title': 'Grey B value:', 'name': 'greyB_value', 'type': 'int', 'value': 255, 'min': 0, 'max': 255},
                 {'title': 'Splitting direction:', 'name': 'split_dir', 'type': 'list', 'values': ['Horizontal','Vertical']},
                 {'title': 'Flipped?:', 'name': 'split_flip', 'type': 'bool', 'value': False},
                 ]},
              {'title': 'Calibration:', 'name': 'calibration', 'type': 'group', 'children': [
                    {'title': 'File name:', 'name': 'calib_file', 'type': 'browsepath', 'value': 'C:\\Users\\Weber\\Labo\\Programmes Python\\user_interface\\holography\\calibration\\calibration_phase_20180723.txt', 'filetype': True},
                    {'title': 'Apply calib?:', 'name': 'calib_apply', 'type': 'bool', 'value': False},
                    ]},
              {'title': 'MultiAxes:', 'name': 'multiaxes', 'type': 'group','visible':is_multiaxes, 'children':[
                        {'title': 'is Multiaxes:', 'name': 'ismultiaxes', 'type': 'bool', 'value': is_multiaxes, 'default': False},
                        {'title': 'Status:', 'name': 'multi_status', 'type': 'list', 'value': 'Master', 'values': ['Master','Slave']},
                        {'title': 'Axis:', 'name': 'axis', 'type': 'list',  'values':stage_names},
                        
                        ]}]+comon_parameters

    def __init__(self,parent=None,params_state=None):
        """
            Initialize the the class

            ============== ================================================ ==========================================================================================
            **Parameters**  **Type**                                         **Description**

            *parent*        Caller object of this plugin                    see DAQ_Move_main.DAQ_Move_stage
            *params_state*  list of dicts                                   saved state of the plugins parameters list
            ============== ================================================ ==========================================================================================

        """

        super(DAQ_Move_Holoeye,self).__init__(parent,params_state)
        self.settings.child(('scaling')).hide()
        self.calibration=None 
        self.data_uchar=None

    def Ini_Stage(self,controller=None):
        """
            Initialize the controller and stages (axes) with given parameters.

            ============== ================================================ ==========================================================================================
            **Parameters**  **Type**                                         **Description**

            *controller*    instance of the specific controller object       If defined this hardware will use it and will not initialize its own controller instance
            ============== ================================================ ==========================================================================================

            Returns
            -------
            Easydict
                dictionnary containing keys:
                 * *info* : string displaying various info
                 * *controller*: instance of the controller object in order to control other axes without the need to init the same controller twice
                 * *stage*: instance of the stage (axis or whatever) object
                 * *initialized*: boolean indicating if initialization has been done corretly

            See Also
            --------
             daq_utils.ThreadCommand
        """
        try:
            # initialize the stage and its controller status
            # controller is an object that may be passed to other instances of DAQ_Move_Mock in case
            # of one controller controlling multiaxes

            self.status.update(edict(info="",controller=None,initialized=False))


            #check whether this stage is controlled by a multiaxe controller (to be defined for each plugin)

            # if mutliaxes then init the controller here if Master state otherwise use external controller
            if self.settings.child('multiaxes','ismultiaxes').value() and self.settings.child('multiaxes','multi_status').value()=="Slave":
                if controller is None: 
                    raise Exception('no controller has been defined externally while this axe is a slave one')
                else:
                    self.controller=controller
            else: #Master stage
                self.controller=slmdisplaysdk.SLMDisplay() #any object that will control the stages
                
            dataWidth = self.controller.width_px
            dataHeight = self.controller.height_px
            self.data_uchar = slmdisplaysdk.createFieldUChar(dataWidth, dataHeight)

            info="Holoeye"
            self.status.info=info
            self.status.controller=self.controller
            self.status.initialized=True
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
            self.status.info=str(e)
            self.status.initialized=False
            return self.status


    def commit_settings(self,param):
        """
            | Activate any parameter changes on the PI_GCS2 hardware.
            |
            | Called after a param_tree_changed signal from DAQ_Move_main.

        """

        if param.name()=='shaping_type':
            self.settings.child(('splitting')).show( param.value()=='SplitScreen') #splitting option
            #set bounds
            if param.value()=='FullScreen':
                self.settings.child('bounds','is_bounds').setValue(True)
                self.settings.child('bounds','max_bound').setValue(255)

                #self.settings.child('
            elif param.value()=='SplitScreen':
                self.settings.child('bounds','is_bounds').setValue(True)
                if self.settings.child('splitting', 'split_control').value()=='Screen spliting':
                    self.settings.child('bounds','max_bound').setValue(1)
                else: 
                    self.settings.child('bounds','max_bound').setValue(255)                
            elif param.value()=='File':
                self.settings.child('bounds','is_bounds').setValue(False)

        elif param.name()=='show_preview':
            self.controller.utilsSLMPreviewShow(param.value())
             
        elif param.parent().name()=='splitting':
            if self.settings.child('splitting','split_control').value()=='Screen spliting':
                self.settings.child('bounds','max_bound').setValue(1)
            elif self.settings.child('splitting','split_control').value()=='GreyA' or self.settings.child('splitting','split_control').value()=='GreyB':
                self.settings.child('bounds','max_bound').setValue(255)

        elif param.name()=='calib_file' or param.name()=='calib_apply':
            fname=self.settings.child('calibration', 'calib_file').value()
            self.load_calibration(fname)


    def load_calibration(self,fname):
        (root,ext)=os.path.splitext(fname)
        if 'h5' in ext:
            self.calibration=h5browser.browse_data(fname) #phase values corresponding to grey levels (256 elements in array)
        elif 'txt' in ext or 'dat' in ext:
            self.calibration=np.loadtxt(fname)[:,1] # to update in order to select what data in file
        else: 
            self.calibration=None
            self.emit_status(ThreadCommand('Update_Status',['No calibration has been loaded','log']))

    def Close(self):
      """
        
      """
      self.controller.close()
      self.controller.release()

    def Stop_Motion(self):
      """
        Call the specific Move_Done function (depending on the hardware).

        See Also
        --------
        Move_Done
      """
      self.Move_Done()


    def Check_position(self):
        """
            Get the current position from the hardware with scaling conversion.

            Returns
            -------
            float
                The position obtained after scaling conversion.

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        pos=self.current_position
        #print('Pos from controller is {}'.format(pos))
        #pos=self.get_position_with_scaling(pos)
        #self.current_position=pos
        self.emit_status(ThreadCommand('Check_position',[pos]))
        return pos

    def Move_Abs(self,position):
        """
            Make the absolute move from the given position after thread command signal was received in DAQ_Move_main.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            DAQ_Move_base.set_position_with_scaling, DAQ_Move_base.poll_moving

        """
        try:
            position=self.check_bound(position)
            #position=self.set_position_with_scaling(position)
            #print(position)
            self.target_position=position
            if self.settings.child(('shaping_type')).value()=='FullScreen':
                self.controller.showBlankscreen( grayValue = position)
            elif self.settings.child(('shaping_type')).value()=='SplitScreen':
                if self.settings.child('splitting','split_control').value()=='Screen spliting':#,'GreyA','GreyB']
                    screenDivider=position
                else:
                    screenDivider=self.settings.child('splitting','split_value').value()
                if self.settings.child('splitting','split_control').value()=='GreyA':
                    a_gray_value=int(position)
                else:
                    a_gray_value=self.settings.child('splitting','greyA_value').value()
                if self.settings.child('splitting','split_control').value()=='GreyB':
                    b_gray_value=int(position)
                else:
                    b_gray_value=self.settings.child('splitting','greyB_value').value()
                
                flipped=self.settings.child('splitting','split_flip').value()

                if self.settings.child('splitting','split_dir').value()=='Vertical':
                    self.controller.showDividedScreenVertical(a_gray_value, b_gray_value, screenDivider, flipped)
                else:
                    self.controller.showDividedScreenHorizontal(a_gray_value, b_gray_value, screenDivider, flipped)
            elif self.settings.child(('shaping_type')).value()=='File':
                fname=str(select_file(start_path=None,save=False,ext='h5'))
                data=h5browser.browse_data(fname)

                if self.settings.child('calibration', 'calib_apply').value() and self.calibration is not None:
                    data=np.reshape(np.interp(data.reshape(np.prod(data.shape)),self.calibration,np.linspace(0,255,256)).astype('uint8'),data.shape)

                dataWidth = self.controller.width_px
                dataHeight = self.controller.height_px
                # Calculate the data:
                for indy in range(dataHeight):
                    for indx in range(dataWidth):
                        self.data_uchar[indy,indx] = data[indy,indx]

                if data is None:
                    raise Exception('No data has been selected')
                else:
                    self.controller.showData(self.data_uchar)

            self.current_position=position#+np.random.rand()-0.5
            self.poll_moving()
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))




    def Move_Rel(self,position):
        """
            Make the relative move from the given position after thread command signal was received in DAQ_Move_main.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            hardware.set_position_with_scaling, DAQ_Move_base.poll_moving

        """
        position=self.check_bound(self.current_position+position)-self.current_position
        self.target_position=position+self.current_position



        self.Move_Abs(self.target_position)

    def Move_Home(self):
        """
          Send the update status thread command.
            See Also
            --------
            daq_utils.ThreadCommand
        """
        self.emit_status(ThreadCommand('Update_Status',['Move Home not implemented']))


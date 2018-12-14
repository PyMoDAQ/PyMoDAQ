from pymodaq.daq_move.utility_classes import DAQ_Move_base
from pymodaq.daq_move.utility_classes import comon_parameters
from pymodaq.daq_utils.daq_utils import ThreadCommand
from easydict import EasyDict as edict


from pymodaq.plugins.hardware.STEM import orsayscan
from pymodaq.plugins.hardware.STEM.orsayscan_position import OrsayScanPosition

class DAQ_Move_STEM(DAQ_Move_base):
    """
        Wrapper object to access the Mock fonctionnalities, similar wrapper for all controllers.

        =============== ==============
        **Attributes**    **Type**
        *params*          dictionnary
        =============== ==============
    """

    is_multiaxes=True
    stage_names=['X','Y']


    params= [   {'title': 'Pixels:', 'name': 'pixels_settings', 'type': 'group', 'children':[
                     {'title': 'Nx:', 'name': 'Nx', 'type': 'int', 'min': 1, 'value': 256}, 
                     {'title': 'Ny:', 'name': 'Ny', 'type': 'int', 'min': 1, 'value': 256}]},
              {'title': 'MultiAxes:', 'name': 'multiaxes', 'type': 'group','visible':is_multiaxes, 'children':[
                        {'title': 'is Multiaxes:', 'name': 'ismultiaxes', 'type': 'bool', 'value': is_multiaxes, 'default': False},
                        {'title': 'Controller Status:', 'name': 'multi_status', 'type': 'list', 'value': 'Master', 'values': ['Master','Slave']},
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
        super(DAQ_Move_STEM,self).__init__(parent,params_state)


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
                    sizex, sizey = self.controller.getImageSize()
                    self.settings.child('pixels_settings','Nx').setOpts(readonly=True)
                    self.settings.child('pixels_settings','Ny').setOpts(readonly=True)
                    self.settings.child('pixels_settings','Nx').setValue(sizex)
                    self.settings.child('pixels_settings','Ny').setValue(sizey)


            else: #Master stage
                self.controller=OrsayScanPosition(1, 0)
                self.settings.child('pixels_settings','Nx').setOpts(readonly=False)
                self.settings.child('pixels_settings','Ny').setOpts(readonly=False)
                self.controller.setImageSize(self.settings.child('pixels_settings','Nx').value(),self.settings.child('pixels_settings','Ny').value())
                sizex, sizey = self.controller.getImageSize()
                self.controller.setImageArea(sizex, sizey, 0, sizex, 0, sizey)


            self.settings.child('bounds','is_bounds').setValue(True)
            self.settings.child('bounds','min_bound').setValue(0)

            if self.settings.child('multiaxes','axis').value()==self.stage_names[0]:
                self.settings.child('bounds','max_bound').setValue(sizex-1)
            else:
                self.settings.child('bounds','max_bound').setValue(sizey-1)


            #set timer to update image size from controller
            self.timer=self.startTimer(1000) #Timer event fired every 1s

            info="STEM coil"
            self.status.info=info
            self.status.controller=self.controller
            self.status.initialized=True
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
            self.status.info=str(e)
            self.status.initialized=False
            return self.status

    def timerEvent(self, event):
        """
            | Called by set timers (only one for this self).
            | 
            =============== ==================== ==============================================
            **Parameters**    **Type**             **Description**

            *event*           QTimerEvent object   Containing id from timer issuing this event
            =============== ==================== ==============================================
        """
        try:
            #this is used to update image area if any call of the controller within multiple instance has been triggered and image size has been changed
            sizex, sizey = self.controller.getImageSize()
            if sizex != self.settings.child('pixels_settings','Nx').value() or sizey != self.settings.child('pixels_settings','Ny').value():
                #try:
                #    self.settings.sigTreeStateChanged.disconnect(self.send_param_status)
                #except: pass
                self.controller.setImageSize(sizex,sizey)
                self.controller.setImageArea(sizex, sizey, 0, sizex, 0, sizey)
                self.settings.child('pixels_settings','Nx').setValue(sizex)
                self.settings.child('pixels_settings','Ny').setValue(sizey)

                if self.settings.child('multiaxes','axis').value()==self.stage_names[0]:
                    self.settings.child('bounds','max_bound').setValue(sizex-1)
                else:
                    self.settings.child('bounds','max_bound').setValue(sizey-1)

                #self.settings.sigTreeStateChanged.connect(self.send_param_status)
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),"log"]))

    def commit_settings(self,param):
        """
            | Called after a param_tree_changed signal from DAQ_Move_main.

        """

        if param.name()=='Nx' or param.name()=='Ny':
            self.controller.setImageSize(self.settings.child('pixels_settings','Nx').value(),self.settings.child('pixels_settings','Ny').value())
            sizex, sizey = self.controller.getImageSize()
            self.controller.setImageArea(sizex, sizey, 0, sizex, 0, sizey)
            if param.name()=='Nx' and self.settings.child('multiaxes','axis').value()==self.stage_names[0]:
                self.settings.child('bounds','max_bound').setValue(param.value()-1)
            elif param.name()=='Ny' and self.settings.child('multiaxes','axis').value()==self.stage_names[1]:
                self.settings.child('bounds','max_bound').setValue(param.value()-1)


    def Close(self):
        """
        
        """
        try:
            self.killTimer(self.timer)

            self.controller.close()
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),"log"]))

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
        position=self.check_bound(position)
        self.target_position=position


        if self.settings.child('multiaxes','axis').value()==self.stage_names[0]:
            px=int(position)
            py=int(self.controller.y)
        else:
            px=int(self.controller.x)
            py=int(position)

        self.controller.OrsayScanSetProbeAt(1,px,py)


        self.current_position=position #no check of the current position is possible...
        self.poll_moving()

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

        if self.settings.child('multiaxes','axis').value()==self.stage_names[0]:
            px=int(self.target_position)
            py=int(self.controller.y)
        else:
            px=int(self.controller.x)
            py=int(self.target_position)


        
        self.controller.OrsayScanSetProbeAt(1,px,py)

        self.current_position=self.target_position #no check of the current position is possible...
        self.poll_moving()

    def Move_Home(self):
        """
          Send the update status thread command.
            See Also
            --------
            daq_utils.ThreadCommand
        """
        self.controller.OrsayScanSetProbeAt(1,0,0)



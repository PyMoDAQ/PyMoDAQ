from PyMoDAQ.DAQ_Move.utility_classes import DAQ_Move_base
from PyMoDAQ.DAQ_Move.utility_classes import comon_parameters
from PyMoDAQ.DAQ_Utils.DAQ_utils import ThreadCommand
from easydict import EasyDict as edict

class DAQ_Move_Mock(DAQ_Move_base):
    """
        Wrapper object to access the Mock fonctionnalities, similar wrapper for all controllers.

        =============== ==============
        **Attributes**    **Type**
        *params*          dictionnary
        =============== ==============
    """
    is_multiaxes=False
    stage_names=[]


    params= [#elements to be added in order to control your custom stage
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

        super(DAQ_Move_Mock,self).__init__(parent,params_state)


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
             DAQ_utils.ThreadCommand
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
                self.controller="master_controller" #any object that will control the stages
                

            info="Mock stage"
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

        pass


    def Close(self):
      """
        not implemented.
      """
      pass

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
            DAQ_Move_base.get_position_with_scaling, DAQ_utils.ThreadCommand
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
        #position=self.set_position_with_scaling(position)
        #print(position)
        self.target_position=position

        self.current_position=position#+np.random.rand()-0.5
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



        self.current_position=self.target_position#+np.random.rand()-0.5
        self.poll_moving()

    def Move_Home(self):
        """
          Send the update status thread command.
            See Also
            --------
            DAQ_utils.ThreadCommand
        """
        self.emit_status(ThreadCommand('Update_Status',['Move Home not implemented']))


from pymodaq.daq_move.utility_classes import DAQ_Move_base
from pymodaq.daq_move.utility_classes import comon_parameters
from pymodaq.daq_utils.daq_utils import ThreadCommand
from easydict import EasyDict as edict

class DAQ_Move_Spectro270M(DAQ_Move_base):
    """
        Wrapper object to access the Spectro270M fonctionnalities, similar wrapper for all controllers.

        =============== ==============
        **Attributes**    **Type**
        *params*          list of dictionnaries
        =============== ==============
    """
    ##checking VISA ressources
    try:
        from visa import ResourceManager
        VISA_rm=ResourceManager()
        devices=VISA_rm.list_resources()
       
    except:
        devices=[]

    is_multiaxes=False
    stage_names=[]


    params= [{'title': 'Instrument settings:', 'name': 'instrument_settings', 'type': 'group', 'children':[
                {'title': 'VISA:','name': 'VISA_ressources', 'type': 'list', 'values': devices },
                {'title': 'Grating type:', 'name': 'grating_type', 'type': 'list', 'value': '600lines', 'values':['600 lines','1200 lines']},
                {'title': 'Grating settings:', 'name': 'grating_settings', 'type': 'group', 'children':[
                    {'title': 'Groove density:', 'name': 'groove_density', 'type': 'int', 'value': 600, 'readonly': True},
                    {'title': 'Blaze Wavelength:', 'name': 'blaze_wl', 'type': 'float', 'value': 1000.0, 'readonly': True},
                    {'title': 'Steps calibration:', 'name': 'steps_units', 'type': 'int', 'value': 16, 'readonly': True},
                    {'title': 'Min wavelength:', 'name': 'wl_min', 'type': 'float', 'value': 0., 'readonly': True},
                    {'title': 'Max wavelength:', 'name': 'wl_max', 'type': 'float', 'value': 1100., 'readonly': True},
                    {'title': 'Backlash wavelength:', 'name': 'backlash', 'type': 'float', 'value': 10., 'readonly': True},

                    ]},
                {'title': 'Slit settings:', 'name': 'slit_settings', 'type': 'group', 'children':[
                    {'title': 'Steps calibration:', 'name': 'steps_units', 'type': 'int', 'value': 500, 'readonly': True},
                    {'title': 'Backlash:', 'name': 'backlash', 'type': 'float', 'value': 0.05, 'readonly': True},
                    {'title': 'Slit unit:', 'name': 'slit_unit', 'type': 'str', 'value': 'mm', 'readonly': True},
                    {'title': 'Min limit:', 'name': 'slit_min', 'type': 'float', 'value': 0., 'readonly': True},
                    {'title': 'Max limit:', 'name': 'slit_max', 'type': 'float', 'value': 2.24, 'readonly': True},
                    ]},
        
                ]},
              {'title': 'MultiAxes:', 'name': 'multiaxes', 'type': 'group','visible':is_multiaxes, 'children':[
                        {'title': 'is Multiaxes:', 'name': 'ismultiaxes', 'type': 'bool', 'value': is_multiaxes, 'default': False},
                        {'title': 'Status:', 'name': 'multi_status', 'type': 'list', 'value': 'Master', 'values': ['Master','Slave']},
                        {'title': 'Axis:', 'name': 'axis', 'type': 'list',  'values':stage_names},
                        
                        ]}]+comon_parameters


    def __init__(self,parent=None,params_state=None):
        super(DAQ_Move_Spectro270M,self).__init__(parent,params_state)
        self.settings.child(('epsilon')).setValue(0.01)

    def commit_settings(self,param):
        if param.name()=='grating_type':
            if param.value()=='600 lines':
                self.settings.child('instrument_settings','grating_settings','groove_density').setValue(600)
                self.settings.child('instrument_settings','grating_settings','blaze_wl').setValue(1000.)
                self.settings.child('instrument_settings','grating_settings','steps_units').setValue(16)
                self.settings.child('instrument_settings','grating_settings','wl_min').setValue(0.0)
                self.settings.child('instrument_settings','grating_settings','wl_max').setValue(1100.)
                self.settings.child('instrument_settings','grating_settings','backlash').setValue(10.)
            elif param.value()=='1200 lines':
                self.settings.child('instrument_settings','grating_settings','groove_density').setValue(1200)
                self.settings.child('instrument_settings','grating_settings','blaze_wl').setValue(500.)
                self.settings.child('instrument_settings','grating_settings','steps_units').setValue(32)
                self.settings.child('instrument_settings','grating_settings','wl_min').setValue(0.0)
                self.settings.child('instrument_settings','grating_settings','wl_max').setValue(1100.)
                self.settings.child('instrument_settings','grating_settings','backlash').setValue(10.)


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
            self.settings.child(('controller_id')).setValue(info)
            self.status.info=info
            self.status.controller=self.controller
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
        pos=self.get_position_with_scaling(pos)
        self.current_position=pos
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

        position=self.set_position_with_scaling(position)
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

        position=self.set_position_with_scaling(position)
        #print(position)
        
        self.current_position=self.target_position#+np.random.rand()-0.5
        self.poll_moving()

    def Move_Home(self):
        """
          Send the update status thread command.
            See Also
            --------
            daq_utils.ThreadCommand
        """
        self.emit_status(ThreadCommand('Update_Status',['Move Home not implemented']))


from pymodaq.daq_move.utility_classes import DAQ_Move_base
from pymodaq.daq_move.utility_classes import comon_parameters
from pymodaq.daq_utils.daq_utils import ThreadCommand
from easydict import EasyDict as edict

class DAQ_Move_PiezoConcept(DAQ_Move_base):
    """
        Wrapper object to access the conex fonctionnalities, similar wrapper for all controllers.

        =============== ==================
        **Attributes**    **Type**
        *ports*           string list
        *TTL_children*    dictionnary list
        *params*          dictionnary list
        =============== ==================
    """

    #find available COM ports
    import serial.tools.list_ports
    ports =[str(port)[0:4] for port in list(serial.tools.list_ports.comports())]
    #if ports==[]:
    #    ports.append('')

    TTL_children=[{'title': 'IO type:', 'name': 'IO_type','type':'list', 'values':['disabled','input','output']},
                  {'title': 'Ref axis:', 'name': 'ref_axis','type':'list', 'values':['X','Y','Z']},
                  {'title': 'Slope:', 'name': 'slope','type':'list', 'values':['rising','falling']},
                  {'title': 'Options:', 'name': 'ouput_options','type': 'group', 'children': [
                        {'title': 'Output type:', 'name': 'output_type','type':'list', 'values':['start','end','given_step','gate_step']},
                        {'title': 'Start index:', 'name': 'start_index','type':'int', 'value': 0},
                        {'title': 'Stop index::', 'name': 'stop_index','type':'int', 'value': 0},
                        ]}
                 ]

    is_multiaxes=True
    stage_names=['X','Y','Z']

    params= [{'title': 'Units:', 'name': 'units', 'type': 'str', 'value': 'um', 'readonly': True}, #2I chose to use only microns and not nm
             {'title': 'Time interval (ms):', 'name': 'time_interval', 'type': 'int', 'value': 200},
             {'title': 'Controller Info:', 'name': 'controller_id', 'type': 'text', 'value': '', 'readonly': True},
             {'title': 'COM Port:', 'name': 'com_port', 'type': 'list', 'values': ports},
             {'title': 'TTL settings:', 'name': 'ttl_settings','type': 'group', 'visible':False, 'children': [
                 {'title': 'TTL 1:', 'name': 'ttl_1','type': 'group', 'children': TTL_children},
                 {'title': 'TTL 2:', 'name': 'ttl_2','type': 'group', 'children': TTL_children},
                 {'title': 'TTL 3:', 'name': 'ttl_3','type': 'group', 'children': TTL_children},
                 {'title': 'TTL 4:', 'name': 'ttl_4','type': 'group', 'children': TTL_children},
                 ]},
              {'title': 'MultiAxes:', 'name': 'multiaxes', 'type': 'group','visible':is_multiaxes, 'children':[
                        {'title': 'is Multiaxes:', 'name': 'ismultiaxes', 'type': 'bool', 'value': is_multiaxes, 'default': False},
                        {'title': 'Status:', 'name': 'multi_status', 'type': 'list', 'value': 'Master', 'values': ['Master','Slave']},
                        {'title': 'Axis:', 'name': 'axis', 'type': 'list',  'values':stage_names},
                        
                        ]}]+comon_parameters

    def __init__(self,parent=None,params_state=None):
        super(DAQ_Move_PiezoConcept,self).__init__(parent,params_state)

        self.controller=None
        self.settings.child(('epsilon')).setValue(1)

    def Ini_Stage(self,controller=None):
        """
            Initialize the controller and stages (axes) with given parameters.

            =============== =========================================== ===========================================================================================
            **Parameters**   **Type**                                     **Description**

            *controller*     instance of the specific controller object   If defined this hardware will use it and will not initialize its own controller instance
            =============== =========================================== ===========================================================================================

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

        # initialize the stage and its controller status
        # controller is an object that may be passed to other instances of DAQ_Move_Mock in case
        # of one controller controlling multiaxes
        try:
            self.status.update(edict(info="",controller=None,initialized=False))


            #check whether this stage is controlled by a multiaxe controller (to be defined for each plugin)

            # if mutliaxes then init the controller here if Master state otherwise use external controller
            if self.settings.child('multiaxes','ismultiaxes').value() and self.settings.child('multiaxes','multi_status').value()=="Slave":
                if controller is None: 
                    raise Exception('no controller has been defined externally while this stage is a slave one')
                else:
                    self.controller=controller
            else: #Master stage
                try:
                    self.Close()
                except:
                    pass
                self.controller=pzcpt.PiezoConcept()
                self.controller.init_communication(self.settings.child(('com_port')).value())

            controller_id=self.controller.get_controller_infos()
            self.settings.child(('controller_id')).setValue(controller_id)
            self.status.info=controller_id
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
            Close the current instance of Piezo instrument.
        """
        self.controller.close_communication()
        self.controller=None


    def Check_position(self):
        """
            Check the current position from the hardware.

            Returns
            -------
            float
                The position of the hardware.

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        position=self.controller.get_position(self.settings.child('multiaxes','axis').value())
        pos=position.pos
        if position.unit=='n': #then convert it in microns
            pos=pos/1000
        pos=self.get_position_with_scaling(pos)
        self.current_position=pos
        self.emit_status(ThreadCommand('Check_position',[pos]))
        return pos



    def Move_Abs(self,position):
        """
            Make the hardware absolute move of the Piezo instrument from the given position after thread command signal was received in DAQ_Move_main.

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
        pos=self.controller.Position(self.settings.child('multiaxes','axis').value(),position)
        out=self.controller.move_axis('ABS',pos)
        self.poll_moving()


    def Move_Rel(self,position):
        """
            Make the hardware relative move of the Piezo instrument from the given position after thread command signal was received in DAQ_Move_main.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            DAQ_Move_base.set_position_with_scaling, DAQ_Move_base.poll_moving

        """
        position=self.check_bound(self.current_position+position)-self.current_position
        self.target_position=position+self.current_position

        position=self.set_position_with_scaling(position)
        pos=self.controller.Position(self.settings.child('multiaxes','axis').value(),position)
        out=self.controller.move_axis('REL',pos)
        self.poll_moving()

    def Move_Home(self):
        """
            Move to the absolute vlue 100 corresponding the default point of the Piezo instrument.

            See Also
            --------
            DAQ_Move_base.Move_Abs
        """
        self.Move_Abs(100) #put the axis on the middle position so 100µm

if __name__ == "__main__":
    test=DAQ_Move_PiezoConcept()
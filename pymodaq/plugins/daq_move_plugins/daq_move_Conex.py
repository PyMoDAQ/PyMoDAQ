from pymodaq.daq_move.utility_classes import DAQ_Move_base
from pymodaq.daq_move.utility_classes import comon_parameters

from pymodaq.daq_utils.daq_utils import ThreadCommand
from easydict import EasyDict as edict
import sys
import clr

class DAQ_Move_Conex(DAQ_Move_base):
    """
        Wrapper object to access the conex fonctionnalities, similar wrapper for all controllers.

        =============== ==================
        **Attributes**   **Type**
        *ports*          list
        *conex_path*     string
        *params*         dictionnary list
        =============== ==================

        See Also
        --------
        daq_utils.ThreadCommand
    """
    #find available COM ports
    import serial.tools.list_ports
    ports =[str(port)[0:4] for port in list(serial.tools.list_ports.comports())]
    #if ports==[]:
    #    ports.append('')
    conex_path='C:\\Program Files\\Newport\\Piezo Motion Control\\Newport CONEX-AGAP Applet\\Samples'
    is_multiaxes=True
    stage_names=['U','V']

    params= [{'title': 'controller library:', 'name': 'conex_lib', 'type': 'browsepath', 'value': conex_path},
             {'title': 'Controller Name:', 'name': 'controller_name', 'type': 'str', 'value': '', 'readonly': True},
             {'title': 'Motor ID:', 'name': 'motor_id', 'type': 'str', 'value': '', 'readonly': True},
             {'title': 'COM Port:', 'name': 'com_port', 'type': 'list', 'values': ports},
             {'title': 'Controller address:', 'name': 'controller_address', 'type': 'int', 'value': 1, 'default': 1, 'min': 1},
              {'title': 'MultiAxes:', 'name': 'multiaxes', 'type': 'group','visible':is_multiaxes, 'children':[
                        {'title': 'is Multiaxes:', 'name': 'ismultiaxes', 'type': 'bool', 'value': is_multiaxes, 'default': False},
                        {'title': 'Status:', 'name': 'multi_status', 'type': 'list', 'value': 'Master', 'values': ['Master','Slave']},
                        {'title': 'Axis:', 'name': 'axis', 'type': 'list',  'values':stage_names},
                        
                        ]}]+comon_parameters



    def __init__(self,parent=None,params_state=None):
        super(DAQ_Move_Conex,self).__init__(parent,params_state)
        self.settings.child(('epsilon')).setValue(0.0001)

        #to be adjusted on the different computers
        try:
            sys.path.append(self.settings.child(('conex_lib')).value())
            clr.AddReference("ConexAGAPCmdLib")
            import Newport.ConexAGAPCmdLib as Conexcmd
            self.controller=Conexcmd.ConexAGAPCmds()
            self.settings.child('bounds','is_bounds').setValue(True)
            self.settings.child('bounds','min_bound').setValue(-0.02)
            self.settings.child('bounds','max_bound').setValue(0.02)

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status",[str(e)]))
            raise Exception(str(e))


    def commit_settings(self,param):
        """
            | Activate any parameter changes on the PI_GCS2 hardware.
            |
            | Called after a param_tree_changed signal from daq_move_main.

        """

        pass

    def Ini_Stage(self,controller=None):
        """
            Initialize the controller and stages (axes) with given parameters.

            =============== ================================================ =========================================================================================
            **Parameters**   **Type**                                         **Description**
            *controller*     instance of the specific controller object       If defined this hardware will use it and will not initialize its own controller instance
            =============== ================================================ =========================================================================================

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
            # controller is an object that may be passed to other instances of daq_move_Mock in case
            # of one controller controlling multiaxes

            self.status.update(edict(info="",controller=None,initialized=False))
            out=-1

            #check whether this stage is controlled by a multiaxe controller (to be defined for each plugin)

            # if mutliaxes then init the controller here if Master state otherwise use external controller
            if self.settings.child('multiaxes','ismultiaxes').value() and self.settings.child('multiaxes','multi_status').value()=="Slave":
                if controller is None: 
                    raise Exception('no controller has been defined externally while this axe is a slave one')
                else:
                    self.controller=controller
                    out=0
            else: #Master stage
                out=self.controller.OpenInstrument(self.settings.child(('com_port')).value()[0:4])


            controller_name=self.controller.VE(self.settings.child(('controller_address')).value(),"","")[1]
            motor_id=self.controller.ID_Get(self.settings.child(('controller_address')).value(),"","")[1]
            self.settings.child(('controller_name')).setValue(controller_name)
            self.settings.child(('motor_id')).setValue(motor_id)
            self.status.info=controller_name + " / " + motor_id
            self.status.controller=self.controller
            if out==0:
                self.status.initialized=True

            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
            self.status.info=str(e)
            self.status.initialized=False
            return self.status

    def Close(self):
        """
            Close the current instance of instrument.
        """
        self.controller.CloseInstrument()

    def Stop_Motion(self):
        """
            See Also
            --------
            daq_move_base.Move_Done
        """
        self.controller.ST(self.settings.child(('controller_address')).value(),"")
        self.Move_Done()

    def Check_position(self):
        """
            Get the current hardware position with scaling conversion given by get_position_with_scaling.

            See Also
            --------
            daq_move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        pos=self.controller.TP(self.settings.child(('controller_address')).value(),
                         self.settings.child('multiaxes','axis').value(),0.0000,"")[1]
        pos=self.get_position_with_scaling(pos)
        self.current_position=pos
        self.emit_status(ThreadCommand('Check_position',[pos]))
        return pos


    def Move_Abs(self,position):
        """
            Make the hardware absolute move from the given position after thread command signal was received in daq_move_main.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            daq_move_base.set_position_with_scaling, daq_move_base.poll_moving

        """
        position=self.check_bound(position)
        self.target_position=position

        position=self.set_position_with_scaling(position)
        out=self.controller.PA_Set(self.settings.child(('controller_address')).value(),
                              self.settings.child('multiaxes','axis').value(),position,"")
        self.poll_moving()


    def Move_Rel(self,position):
        """
            | Make the hardware relative move from the given position after thread command signal was received in daq_move_main.
            |
            | The final target position is given by **current_position+position**.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            daq_move_base.set_position_with_scaling, daq_move_base.poll_moving

        """
        position=self.check_bound(self.current_position+position)-self.current_position
        self.target_position=position+self.current_position

        position=self.set_position_with_scaling(position)

        out=self.controller.PR_Set(self.settings.child(('controller_address')).value(),
                              self.settings.child('multiaxes','axis').value(),position,"")
        self.poll_moving()

    def Move_Home(self):
        """
            Make the absolute move to original position (0).

            See Also
            --------
            Move_Abs
        """
        self.Move_Abs(0)

if __name__ == "__main__":
    test=daq_move_Conex()
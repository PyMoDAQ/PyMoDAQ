from pymodaq.daq_move.utility_classes import DAQ_Move_base
from pymodaq.daq_move.utility_classes import comon_parameters
from pymodaq.daq_utils.daq_utils import ThreadCommand
from easydict import EasyDict as edict
import clr
import sys
class DAQ_Move_Kinesis_Flipper(DAQ_Move_base):
    """
        Wrapper object to access the conex fonctionnalities, similar wrapper for all controllers.

        ================ =================
        **Attributes**    **Type**
        *Kinesis_path*    string
        *serialnumbers*   int list
        *params*          dictionnary list
        ================ =================

        See Also
        --------
        daq_utils.ThreadCommand
    """

    #Kinesis_path=os.environ['Kinesis'] #environement variable pointing to 'C:\\Program Files\\Thorlabs\\Kinesis'
    #to be adjusted on the different computers
    Kinesis_path='C:\\Program Files\\Thorlabs\\Kinesis'
    try:
        from System import Decimal
        from System import Action
        from System import UInt32
        from System import UInt64

        sys.path.append(Kinesis_path)

        clr.AddReference("Thorlabs.MotionControl.IntegratedStepperMotorsCLI")
        clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
        clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
        clr.AddReference("Thorlabs.MotionControl.FilterFlipperCLI")

        import Thorlabs.MotionControl.FilterFlipperCLI as Flipper
        import Thorlabs.MotionControl.DeviceManagerCLI as Device
        import Thorlabs.MotionControl.GenericMotorCLI as Generic


        Device.DeviceManagerCLI.BuildDeviceList()
        serialnumbers=[str(ser) for ser in Device.DeviceManagerCLI.GetDeviceList(Flipper.FilterFlipper.DevicePrefix)]
    except Exception as e:
        serialnumbers=[]
    is_multiaxes=False
    stage_names=[]


    params= [{'title': 'Kinesis library:', 'name': 'kinesis_lib', 'type': 'browsepath', 'value': Kinesis_path},
             {'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
             {'title': 'Serial number:', 'name': 'serial_number', 'type': 'list', 'values':serialnumbers},
              {'title': 'MultiAxes:', 'name': 'multiaxes', 'type': 'group','visible':is_multiaxes, 'children':[
                        {'title': 'is Multiaxes:', 'name': 'ismultiaxes', 'type': 'bool', 'value': is_multiaxes, 'default': False},
                        {'title': 'Status:', 'name': 'multi_status', 'type': 'list', 'value': 'Master', 'values': ['Master','Slave']},
                        {'title': 'Axis:', 'name': 'axis', 'type': 'list',  'values':stage_names},
                        
                        ]}]+comon_parameters


    def __init__(self,parent=None,params_state=None):
        super(DAQ_Move_Kinesis_Flipper,self).__init__(parent,params_state)
        self.settings.child(('epsilon')).setValue(1)
        self.settings.child('bounds','is_bounds').setValue(True)
        self.settings.child('bounds','max_bound').setValue(1)
        self.settings.child('bounds','min_bound').setValue(0)

        try:
            #Kinesis_path=os.environ['Kinesis'] #environement variable pointing to 'C:\\Program Files\\Thorlabs\\Kinesis'
            #to be adjusted on the different computers
            self.move_done_action=self.Action[self.UInt64](self.Move_Done)

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))
            raise Exception(str(e))

    def commit_settings(self,param):
        """
            | Activate any parameter changes on the hardware.
            | Called after a param_tree_changed signal received from DAQ_Move_main.

            =============== ================================ ========================
            **Parameters**  **Type**                          **Description**
            *param*         instance of pyqtgraph Parameter  The parameter to update
            =============== ================================ ========================
        """
        if param.name()==kinesis_lib:
            self.Kinesis_path=param.value()
            try:
                sys.path.append(self.Kinesis_path)
                clr.AddReference("Thorlabs.MotionControl.IntegratedStepperMotorsCLI")
                clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
                clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
                clr.AddReference("Thorlabs.MotionControl.FilterFlipperCLI")

                import Thorlabs.MotionControl.FilterFlipperCLI as Flipper
                import Thorlabs.MotionControl.DeviceManagerCLI as Device
                import Thorlabs.MotionControl.GenericMotorCLI as Generic
                Device.DeviceManagerCLI.BuildDeviceList()
                serialnumbers=[str(ser) for ser in Device.DeviceManagerCLI.GetDeviceList(Flipper.FilterFlipper.DevicePrefix)]

            except:
                serialnumbers=[]
            self.settings.child(('serial_number')).setOpts(limits=serialnumbers)



    def Ini_Stage(self,controller=None):
        """Initialize the controller and stages (axes) with given parameters.

            ============== =========================================== ===========================================================================================
            **Parameters**  **Type**                                     **Description**

            *controller*    instance of the specific controller object  If defined this hardware will use it and will not initialize its own controller instance
            ============== =========================================== ===========================================================================================

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
               
                self.Device.DeviceManagerCLI.BuildDeviceList()
                serialnumbers=self.Device.DeviceManagerCLI.GetDeviceList(self.Flipper.FilterFlipper.DevicePrefix)
                ser_bool=serialnumbers.Contains(self.settings.child(('serial_number')).value())
                if ser_bool:
                    self.controller=self.Flipper.FilterFlipper.CreateFilterFlipper(self.settings.child(('serial_number')).value())
                    self.controller.Connect(self.settings.child(('serial_number')).value())
                    self.controller.WaitForSettingsInitialized(5000)
                    self.controller.StartPolling(250)
                else:
                    raise Exception("Not valid serial number")


            info=self.controller.GetDeviceInfo().Name
            self.settings.child(('controller_id')).setValue(info)
            if not(self.controller.IsSettingsInitialized()):
                raise(Exception("no Stage Connected"))

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
            Close the current instance of Kinesis Flipper instrument.
        """
        self.controller.StopPolling();
        self.controller.Disconnect();
        self.controller.Dispose()
        self.controller=None

    def Stop_Motion(self):
        """
            See Also
            --------
            DAQ_Move_base.Move_Done
        """
        self.controller.Stop(0)
        self.Move_Done()

    def Check_position(self):
        """
            Get the current hardware position with scaling conversion of the Kinsesis insrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        pos = self.controller.Position
        pos = self.get_position_with_scaling(pos)
        self.emit_status(ThreadCommand('Check_position', [pos]))
        return pos

    def Move_Abs(self,position):
        """
            Make the hardware absolute move from the given position after thread command signal was received in DAQ_Move_main.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       int       either 1 or 2 for the flipper
            =============== ========= =======================

            See Also
            --------
            DAQ_Move_base.set_position_with_scaling

        """
        pos = self.Check_position()
        if int(pos) == 1:
            position = 2
        else:
            position = 1


        self.target_position=position
        self.controller.SetPosition(self.UInt32(position),self.move_done_action)


    def Move_Rel(self,position):
        """
            | Make the hardware relative move from the given position of the Kinesis instrument after thread command signal was received in DAQ_Move_main.
            |
            | The final target position is given by (current_position+position).

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            hardware.set_position_with_scaling

        """
        pos = self.Check_position()
        if int(pos) == 1:
            position = 2
        else:
            position = 1


        self.target_position = position
        self.controller.SetPosition(self.UInt32(position), self.move_done_action)


    def Move_Home(self):
        """
            Make the absolute move to original position (0).
        """
        self.controller.Home(self.move_done_action)

if __name__ == "__main__":
    test=DAQ_Move_Kinesis_Flipper()
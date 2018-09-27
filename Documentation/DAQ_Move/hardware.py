from PyQt5 import QtCore, QtGui, QtWidgets, QAxContainer
from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QVariant, QSize
from enum import IntEnum
from easydict import EasyDict as edict
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import PyMoDAQ.DAQ_Utils.custom_parameter_tree
from PyMoDAQ.DAQ_Utils.DAQ_utils import ThreadCommand
import PyMoDAQ.DAQ_Utils.hardware.piezoconcept.piezoconcept as pzcpt
import os
import sys
import numpy as np
import clr


class DAQ_Move_Stage_type(IntEnum):
    """
        Enum class listing the differents hardware profile.

        =================== =========== ==============================
        **Attributes**       **Type**
        *Mock*               int        assigned name from int index
        *Conex*              int        assigned name from int index
        *Kinesis*            int        assigned name from int index
        *Kinesis_Flipper*    int        assigned name from int index
        *PI*                 int        assigned name from int index
        *PiezoConcept*       int        assigned name from int index
        =================== =========== ==============================
    """
    Mock=0
    Conex=1
    Kinesis=2
    Kinesis_Flipper=3
    PI=4
    PiezoConcept=5
    @classmethod
    def names(cls):
        names=cls.__members__.items()
        return [name for name, member in cls.__members__.items()]

comon_parameters=[{'title': 'Timeout (ms):', 'name': 'timeout', 'type': 'int', 'value': 10000, 'default': 10000},
             {'title': 'Scaling:', 'name': 'scaling', 'type': 'group', 'children':[
             {'title': 'Use scaling:', 'name': 'use_scaling', 'type': 'bool', 'value': False, 'default': False},
             {'title': 'Scaling factor:', 'name': 'scaling', 'type': 'float', 'value': 1., 'default': 1.},
             {'title': 'Offset factor:', 'name': 'offset', 'type': 'float', 'value': 0., 'default': 0.}]}]


class DAQ_Move_base(QObject):
    """
        ================== =================================================
        **Attributes**      **Type**

        *Move_Done_signal*  instance of pyqtSignal
        *params*            list

        *parent*            QObject
        *controller*        instance of the controller object
        *stage*             instance of the stage (axis or whatever) object
        *status*            dictionnary
        *current_position*  float
        *target_position*   float
        *settings*          instance of pyqtgraph Parametertree
        ================== =================================================

        See Also
        --------
        send_param_status
    """
    Move_Done_signal=pyqtSignal(float)

    params= []
    def __init__(self,parent=None,params_state=None):
        super(DAQ_Move_base,self).__init__()
        self.parent=parent
        self.controller=None
        self.stage=None
        self.status=edict(info="",controller=None,stage=None,initialized=False)
        self.current_position=0
        self.target_position=0
        self.settings=Parameter.create(name='Settings', type='group', children=self.params)
        if params_state is not None:
            self.settings.restoreState(params_state)

        self.settings.sigTreeStateChanged.connect(self.send_param_status)

    def get_position_with_scaling(self,pos):
        """
            Get the current position from the hardware with scaling conversion.

            =============== ========= =====================
            **Parameters**  **Type**  **Description**
             *pos*           float    the current position
            =============== ========= =====================

            Returns
            =======
            float
                the computed position.
        """
        if self.settings.child('scaling','use_scaling').value():
            pos=(pos-self.settings.child('scaling','offset').value())*self.settings.child('scaling','scaling').value()
        return pos

    def set_position_with_scaling(self,pos):
        """
            Set the current position from the parameter and hardware with scaling conversion.

            =============== ========= ==========================
            **Parameters**  **Type**  **Description**
             *pos*           float    the position to be setted
            =============== ========= ==========================

            Returns
            =======
            float
                the computed position.
        """
        if self.settings.child('scaling','use_scaling').value():
            pos=pos/self.settings.child('scaling','scaling').value()+self.settings.child('scaling','offset').value()
        return pos

    def emit_status(self,status):
        """
            | Emit the statut signal from the given status parameter.
            |
            | The signal is sended to the gui to update the user interface.

            =============== ===================== ========================================================================================================================================
            **Parameters**   **Type**              **Description**
             *status*        ordered dictionnary    dictionnary containing keys:
                                                        * *info* : string displaying various info
                                                        * *controller*: instance of the controller object in order to control other axes without the need to init the same controller twice
                                                        * *stage*: instance of the stage (axis or whatever) object
                                                        * *initialized*: boolean indicating if initialization has been done corretly
            =============== ===================== ========================================================================================================================================
        """
        if self.parent is not None:
            self.parent.status_sig.emit(status)
        else:
            print(*status)

    def poll_moving(self):
        """
            Poll the current moving. In case of timeout emit the raise timeout Thread command.
            
            See Also
            --------
            DAQ_utils.ThreadCommand, Move_Done
        """
        sleep_ms=50
        ind=0
        while np.abs(self.Check_position()-self.target_position)>self.settings.child(('epsilon')).value():
            QThread.msleep(sleep_ms)

            ind+=1

            if ind*sleep_ms>=self.settings.child(('timeout')).value():

                self.emit_status(ThreadCommand('raise_timeout'))
                break
            self.current_position=self.Check_position()
            QtWidgets.QApplication.processEvents()
        self.Move_Done()

    def Move_Done(self,position=None):#the position argument is just there to match some signature of child classes
        """
            | Emit a move done signal transmitting the float position to hardware.
            | The position argument is just there to match some signature of child classes.

            =============== ========== =============================================================================
             **Arguments**   **Type**  **Description**
             *position*      float     The position argument is just there to match some signature of child classes
            =============== ========== =============================================================================

        """
        position=self.Check_position()
        self.Move_Done_signal.emit(position)

    @pyqtSlot(edict)
    def update_settings(self,settings_parameter_dict):#settings_parameter_dict=edict(path=path,param=param)
        """
            Receive the settings_parameter signal from the param_tree_changed method and make hardware updates of mmodified values.

            ==========================  =========== ==========================================================================================================
            **Arguments**               **Type**     **Description**
            *settings_parameter_dict*   dictionnary Dictionnary with the path of the parameter in hardware structure as key and the parameter name as element
            ==========================  =========== ==========================================================================================================

            See Also
            --------
            send_param_status, commit_settings
        """
        path=settings_parameter_dict.path
        param=settings_parameter_dict.param
        try:
            self.settings.sigTreeStateChanged.disconnect(self.send_param_status)
        except: pass
        self.settings.child(*path[1:]).setValue(param.value())

        self.settings.sigTreeStateChanged.connect(self.send_param_status)

        self.commit_settings(param)

    def commit_settings(self,param):
      """
        not implemented.
      """
      pass

    def send_param_status(self,param,changes):
        """
            | Send changes value updates to the gui to update consequently the User Interface.
            | The message passing is made via the Thread Command "update_settings".

            =============== =================================== ==================================================
            **Parameters**  **Type**                             **Description**
            *param*         instance of pyqtgraph parameter      The parameter to be checked
            *changes*       (parameter,change,infos)tuple list   The (parameter,change,infos) list to be treated
            =============== =================================== ==================================================

            See Also
            ========
            DAQ_utils.ThreadCommand
        """

        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':
                pass

            elif change == 'value' or change == 'limits':
                self.emit_status(ThreadCommand('update_settings',[path,data,change])) #parent is the main detector object and status_sig will be send to the GUI thrad
            elif change == 'parent':
                pass

class DAQ_Move_Mock(DAQ_Move_base):
    """
        Wrapper object to access the Mock fonctionnalities, similar wrapper for all controllers.

        =============== ==============
        **Attributes**    **Type**
        *params*          dictionnary
        =============== ==============
    """
    params= [{'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
             {'name': 'epsilon', 'type': 'float', 'value': 0.01}]+comon_parameters

    def __init__(self,parent=None,params_state=None):

        super(DAQ_Move_Mock,self).__init__(parent,params_state)



    def Ini_Stage(self,controller=None,stage=None):
        """
            Initialize the controller and stages (axes) with given parameters.

            ============== ================================================ ==========================================================================================
            **Parameters**  **Type**                                         **Description**

            *controller*    instance of the specific controller object       If defined this hardware will use it and will not initialize its own controller instance
            *stage*         instance of the stage (axis or whatever) object  ???
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
            self.status.update(info="",controller=None,stage=None,initialized=False)
            if controller is None: #not really useful for mock but necessary for others
                 self.controller="mock controller"
            else:
                self.controller=controller
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
            DAQ_Move_base.get_position_with_scaling, DAQ_utils.ThreadCommand
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
        position=self.set_position_with_scaling(position)
        #print(position)
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
        DAQ_utils.ThreadCommand
    """
    #find available COM ports
    import serial.tools.list_ports
    ports =[str(port)[0:4] for port in list(serial.tools.list_ports.comports())]
    #if ports==[]:
    #    ports.append('')
    conex_path='C:\\Program Files\\Newport\\Piezo Motion Control\\Newport CONEX-AGAP Applet\\Samples'

    params= [{'title': 'Conex library:', 'name': 'conex_lib', 'type': 'browsepath', 'value': conex_path},
             {'name': 'epsilon', 'type': 'float', 'value': 0.0001},
             {'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
             {'title': 'Motor ID:', 'name': 'motor_id', 'type': 'str', 'value': '', 'readonly': True},
             {'title': 'COM Port:', 'name': 'com_port', 'type': 'list', 'values': ports},
             {'title': 'Controller address:', 'name': 'controller_address', 'type': 'int', 'value': 1, 'default': 1, 'min': 1},
             {'title': 'Stage address:', 'name': 'axis_address', 'type': 'list', 'value': 'U', 'values': ['U','V']}]+comon_parameters


    def __init__(self,parent=None,params_state=None):
        super(DAQ_Move_Conex,self).__init__(parent,params_state)
        #to be adjusted on the different computers
        try:
            sys.path.append(self.settings.child(('conex_lib')).value())
            clr.AddReference("ConexAGAPCmdLib")
            import Newport.ConexAGAPCmdLib as Conexcmd
            self.Conex=Conexcmd.ConexAGAPCmds()
        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status",[str(e)]))
            raise Exception(str(e))

    def Ini_Stage(self,controller=None,stage=None):
        """
            Initialize the controller and stages (axes) with given parameters.

            =============== ================================================ =========================================================================================
            **Parameters**   **Type**                                         **Description**
            *controller*     instance of the specific controller object       If defined this hardware will use it and will not initialize its own controller instance
            *stage*          instance of the stage (axis or whatever) object  ???
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
            DAQ_utils.ThreadCommand
        """
        try:
            self.status.update(info="",controller=None,stage=None,initialized=False)

            if controller is None:
                 out=self.Conex.OpenInstrument(self.settings.child(('com_port')).value()[0:4])
            else:
                out=0
                self.Conex=controller

            controller_id=self.Conex.VE(self.settings.child(('controller_address')).value(),"","")[1]
            motor_id=self.Conex.ID_Get(self.settings.child(('controller_address')).value(),"","")[1]
            self.settings.child(('controller_id')).setValue(controller_id)
            self.settings.child(('motor_id')).setValue(motor_id)
            self.status.info=controller_id + " / " + motor_id
            self.status.controller=self.Conex
            if out>=0:
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
        self.Conex.CloseInstrument()

    def Stop_Motion(self):
        """
            See Also
            --------
            DAQ_Move_base.Move_Done
        """
        self.Conex.ST(self.settings.child(('controller_address')).value(),"")
        self.Move_Done()

    def Check_position(self):
        """
            Get the current hardware position with scaling conversion given by get_position_with_scaling.

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, DAQ_utils.ThreadCommand
        """
        pos=self.Conex.TP(self.settings.child(('controller_address')).value(),
                          self.settings.child(('axis_address')).value(),0.0000,"")[1]
        pos=self.get_position_with_scaling(pos)
        self.current_position=pos
        self.emit_status(ThreadCommand('Check_position',[pos]))
        return pos


    def Move_Abs(self,position):
        """
            Make the hardware absolute move from the given position after thread command signal was received in DAQ_Move_main.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            DAQ_Move_base.set_position_with_scaling, DAQ_Move_base.poll_moving

        """
        self.target_position=position

        position=self.set_position_with_scaling(position)
        out=self.Conex.PA_Set(self.settings.child(('controller_address')).value(),
                              self.settings.child(('axis_address')).value(),position,"")
        self.poll_moving()


    def Move_Rel(self,position):
        """
            | Make the hardware relative move from the given position after thread command signal was received in DAQ_Move_main.
            |
            | The final target position is given by **current_position+position**.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            DAQ_Move_base.set_position_with_scaling, DAQ_Move_base.poll_moving

        """
        self.target_position=self.current_position+position

        position=self.set_position_with_scaling(position)

        out=self.Conex.PR_Set(self.settings.child(('controller_address')).value(),
                              self.settings.child(('axis_address')).value(),position,"")
        self.poll_moving()

    def Move_Home(self):
        """
            Make the absolute move to original position (0).

            See Also
            --------
            Move_Abs
        """
        self.Move_Abs(0)



class DAQ_Move_Kinesis(DAQ_Move_base):
    """
        Wrapper object to access the kinesis fonctionnalities, similar wrapper for all controllers.

        =============== ==================
        **Attributes**   **Type**
        *Kinesis_path*   string
        *serialnumbers*  int list
        *params*         dictionnary list
        =============== ==================

        See Also
        --------
        DAQ_utils.ThreadCommand

    """
    Kinesis_path='C:\\Program Files\\Thorlabs\\Kinesis'
    try:
        from System import Decimal
        from System import Action
        from System import UInt64
        sys.path.append(Kinesis_path)
        clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
        clr.AddReference("Thorlabs.MotionControl.IntegratedStepperMotorsCLI")
        clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
        import Thorlabs.MotionControl.IntegratedStepperMotorsCLI as Integrated
        import Thorlabs.MotionControl.DeviceManagerCLI as Device
        import Thorlabs.MotionControl.GenericMotorCLI as Generic
        Device.DeviceManagerCLI.BuildDeviceList()
        serialnumbers=[str(ser) for ser in Device.DeviceManagerCLI.GetDeviceList(Integrated.CageRotator.DevicePrefix)]

    except:
        serialnumbers=[]

    params= [{'title': 'Kinesis library:', 'name': 'kinesis_lib', 'type': 'browsepath', 'value': Kinesis_path},
             {'name': 'epsilon', 'type': 'float', 'value': 0.01},
             {'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
             {'title': 'Serial number:', 'name': 'serial_number', 'type': 'list', 'values': serialnumbers} ]+comon_parameters

    def __init__(self,parent=None,params_state=None):
        super(DAQ_Move_Kinesis,self).__init__(parent,params_state)
        self.stage=None


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
            *param*         instance of pyqtgraph parameter  The parameter to update
            =============== ================================ ========================
        """
        if param.name()=='kinesis_lib':
            self.Kinesis_path=param.value()
            try:
                sys.path.append(Kinesis_path)
                clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
                clr.AddReference("Thorlabs.MotionControl.IntegratedStepperMotorsCLI")
                clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
                import Thorlabs.MotionControl.IntegratedStepperMotorsCLI as Integrated
                import Thorlabs.MotionControl.DeviceManagerCLI as Device
                import Thorlabs.MotionControl.GenericMotorCLI as Generic
                Device.DeviceManagerCLI.BuildDeviceList()
                serialnumbers=[str(ser) for ser in Device.DeviceManagerCLI.GetDeviceList(Integrated.CageRotator.DevicePrefix)]

            except:
                serialnumbers=[]
            self.settings.child(('serial_number')).setOpts(limits=serialnumbers)


    def Ini_Stage(self,controller=None,stage=None):
        """
            Initialize the controller and stages (axes) with given parameters.

            =============== ================================================ =========================================================================================
            **Parameters**   **Type**                                         **Description**
            *controller*     instance of the specific controller object       If defined this hardware will use it and will not initialize its own controller instance
            *stage*          instance of the stage (axis or whatever) object  ???
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
            DAQ_utils.ThreadCommand
        """
        self.status.update(edict(info="",controller=None,stage=None,initialized=False))
        try:
            self.controller=controller #None
            self.Device.DeviceManagerCLI.BuildDeviceList()
            serialnumbers=self.Device.DeviceManagerCLI.GetDeviceList(self.Integrated.CageRotator.DevicePrefix)
            ser_bool=serialnumbers.Contains(self.settings.child(('serial_number')).value())
            if stage is None:
                self.stage=self.Integrated.CageRotator.CreateCageRotator(self.settings.child(('serial_number')).value())
                self.stage.Connect(self.settings.child(('serial_number')).value())
                self.stage.WaitForSettingsInitialized(5000)
                self.stage.StartPolling(250)
            else:
                self.stage=stage

            info=self.stage.GetDeviceInfo().Name
            self.settings.child(('controller_id')).setValue(info)
            if not(self.stage.IsSettingsInitialized()):
                raise(Exception("no Stage Connected"))
            self.motorSettings = self.stage.GetMotorConfiguration(self.settings.child(('serial_number')).value(),2);
            self.status.info=info
            self.status.stage=self.stage
            self.status.initialized=True
            return self.status

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
            self.status.info=str(e)
            self.status.initialized=False
            return self.status


    def Close(self):
        """
            Close the current instance of Kinesis instrument.
        """
        self.stage.StopPolling();
        self.stage.Disconnect();
        self.stage.Dispose()
        self.stage=None

    def Stop_Motion(self):
        """
            See Also
            --------
            DAQ_Move_base.Move_Done
        """
        self.stage.Stop(0)
        self.Move_Done()

    def Check_position(self):
        """
            Get the current hardware position with scaling conversion of the Kinsesis insrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, DAQ_utils.ThreadCommand
        """
        pos=self.Decimal.ToDouble(self.stage.Position)
        pos=self.get_position_with_scaling(pos)
        self.emit_status(ThreadCommand('Check_position',[pos]))
        return pos

    def Move_Abs(self,position):
        """
            Make the hardware absolute move from the given position of the Kinesis instrument after thread command signal was received in DAQ_Move_main.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            DAQ_Move_base.set_position_with_scaling

        """
        position=self.set_position_with_scaling(position)
        self.stage.MoveTo(self.Decimal(position),self.move_done_action)

    def Move_Rel(self,position):
        """
            | Make the hardware relative move from the given position of the Kinesis instrument after thread command signal was received in DAQ_Move_main.
            |
            | The final target position is given by **current_position+position**.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            DAQ_Move_base.set_position_with_scaling

        """
        position=self.set_position_with_scaling(position)
        self.stage.MoveRelative(self.Generic.MotorDirection.Forward,self.Decimal(position),self.move_done_action)

    def Move_Home(self):
        """
            Make the absolute move to original position (0).
        """
        self.stage.Home(self.move_done_action)


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
        DAQ_utils.ThreadCommand
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

    params= [{'title': 'Kinesis library:', 'name': 'kinesis_lib', 'type': 'browsepath', 'value': Kinesis_path},
             {'name': 'epsilon', 'type': 'float', 'value': 1},
             {'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
             {'title': 'Serial number:', 'name': 'serial_number', 'type': 'list', 'values':serialnumbers}]+comon_parameters

    def __init__(self,parent=None,params_state=None):
        super(DAQ_Move_Kinesis_Flipper,self).__init__(parent,params_state)


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



    def Ini_Stage(self,controller=None,stage=None):
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
            DAQ_utils.ThreadCommand
        """
        self.status.update(edict(info="",controller=None,stage=None))
        try:
            self.controller=controller #None
            self.Device.DeviceManagerCLI.BuildDeviceList()
            serialnumbers=self.Device.DeviceManagerCLI.GetDeviceList(self.Flipper.FilterFlipper.DevicePrefix)
            ser_bool=serialnumbers.Contains(self.settings.child(('serial_number')).value())
            if stage is None:
                self.stage=self.Flipper.FilterFlipper.CreateFilterFlipper(self.settings.child(('serial_number')).value())
                self.stage.Connect(self.settings.child(('serial_number')).value())
                self.stage.WaitForSettingsInitialized(1000)
                self.stage.StartPolling(250)
            else:
                self.stage=stage

            info=self.stage.GetDeviceInfo().Name
            self.settings.child(('controller_id')).setValue(info)
            if not(self.stage.IsSettingsInitialized()):
                raise(Exception("no Stage Connected"))

            self.status.info=info
            self.status.stage=self.stage
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
        self.stage.StopPolling();
        self.stage.Disconnect();
        self.stage.Dispose()
        self.stage=None

    def Stop_Motion(self):
        """
            See Also
            --------
            DAQ_Move_base.Move_Done
        """
        self.stage.Stop(0)
        self.Move_Done()

    def Check_position(self):
        """
            Get the current hardware position with scaling conversion of the Kinsesis insrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, DAQ_utils.ThreadCommand
        """
        pos=self.stage.Position
        pos=self.get_position_with_scaling(pos)
        self.emit_status(ThreadCommand('Check_position',[pos]))
        return pos

    def Move_Abs(self,position):
        """
            Make the hardware absolute move from the given position after thread command signal was received in DAQ_Move_main.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            DAQ_Move_base.set_position_with_scaling

        """
        position=self.set_position_with_scaling(position)
        self.stage.SetPosition(self.UInt32(position),self.move_done_action)


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
        position=self.set_position_with_scaling(position)
        self.stage.MoveRelative(self.Generic.MotorDirection.Forward,self.Decimal(position),self.move_done_action)


    def Move_Home(self):
        """
            Make the absolute move to original position (0).
        """
        self.stage.Home(self.move_done_action)


class DAQ_Move_PI(DAQ_Move_base):
    """
        Wrapper object to access the Physik Instrumente fonctionnalities, similar wrapper for all controllers.

        =============== =======================
        **Attributes**   **Type**
        *GCS_path*       string
        *gcs_device*     string
        *devices*        instance of GCSDevice
        *params*         dictionnary list
        =============== =======================

        See Also
        --------
        DAQ_utils.ThreadCommand
    """

    try:
        GCS_path=os.environ['PI_GCS2']
    except KeyError:
        GCS_path="C:\\Users\\Public\\PI\\PI_Programming_Files_PI_GCS2_DLL"
    try:
      from pipython import GCSDevice
      gcs_device=GCSDevice(gcsdll=os.path.join(GCS_path,"PI_GCS2_DLL_x64.dll"))
      devices=gcs_device.EnumerateUSB()

      import serial.tools.list_ports as list_ports

      params= [{'title': 'GCS2 library:', 'name': 'gcs_lib', 'type': 'browsepath', 'value': GCS_path},
               {'title': 'Connection_type:', 'name': 'connect_type', 'type': 'list', 'value':'USB', 'values': ['USB', 'TCP/IP' , 'RS232']},
               {'title': 'Devices:', 'name': 'devices', 'type': 'list', 'values': devices},
               {'title': 'Daisy Chain Options:', 'name': 'dc_options', 'type': 'group', 'children': [
                   {'title': 'Use Daisy Chain:', 'name': 'is_daisy', 'type': 'bool', 'value': False},
                   {'title': 'Is master?:', 'name': 'is_daisy_master', 'type': 'bool', 'value': False},
                   {'title': 'Daisy Master Id:', 'name': 'daisy_id', 'type': 'int'},
                   {'title': 'Daisy Devices:', 'name': 'daisy_devices', 'type': 'list'},
                   {'title': 'Index in chain:', 'name': 'index_in_chain', 'type': 'int', 'enabled': True}]},
               {'title': 'Use Joystick:', 'name': 'use_joystick', 'type': 'bool', 'value': False},
               {'name': 'epsilon', 'type': 'float', 'value': 0.002, 'default': 0.002},
               {'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
               {'title': 'Stage address:', 'name': 'axis_address', 'type': 'list'}]+comon_parameters
    except:
      print('no GCS2 library')

    def __init__(self,parent=None,params_state=None):
        super(DAQ_Move_PI,self).__init__(parent,params_state)




    def commit_settings(self,param):
        """
            | Activate any parameter changes on the PI_GCS2 hardware.
            |
            | Called after a param_tree_changed signal from DAQ_Move_main.

            =============== ================================ ========================
            **Parameters**  **Type**                          **Description**
            *param*         instance of pyqtgraph Parameter  The parameter to update
            =============== ================================ ========================

            See Also
            --------
            DAQ_utils.ThreadCommand, DAQ_Move_PI.enumerate_devices
        """
        if param.name()=='gcs_lib':
            try:
                self.gcs_device.CloseConnection()
            except Exception as e:
                self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))
            self.Ini_device()

        elif param.name()=='connect_type':
            self.enumerate_devices()

        elif param.name()=='use_joystick':
            pass


    def enumerate_devices(self):
        """
            Enumerate PI_GCS2 devices from the connection type.

            Returns
            -------
            string list
                The list of the devices port.

            See Also
            --------
            DAQ_utils.ThreadCommand
        """
        try:
            devices=[]
            if self.settings.child(('connect_type')).value()=='USB':
                devices=self.gcs_device.EnumerateUSB()
            elif self.settings.child(('connect_type')).value()=='TCP/IP':
                devices=self.gcs_device.EnumerateTCPIPDevices()
            elif self.settings.child(('connect_type')).value()=='RS232':
                devices=[str(port) for port in list(self.list_ports.comports())]

            self.settings.child(('devices')).setLimits(devices)


            return devices
        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))

    def Ini_device(self):
        """
            See Also
            --------
            DAQ_Move_base.Close
        """
        from pipython import GCSDevice
        try:
            self.Close()
        except: pass
        self.gcs_device=GCSDevice(gcsdll=os.path.join(self.settings.child(('gcs_lib')).value(),"PI_GCS2_DLL_x64.dll"))


    def Ini_Stage(self,controller=None,stage=None):
        """
            Initialize the controller and stages (axes) with given parameters.

            =============== =========================================== ==========================================================================================
            **Parameters**  **Type**                                     **Description**

            *controller*     instance of the specific controller object  If defined this hardware will use it and will not initialize its own controller instance
            =============== =========================================== ==========================================================================================

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
            DAQ_Move_PI.set_referencing, DAQ_utils.ThreadCommand
        """
        try:
            self.status.update(edict(info="",controller=None,stage=None))
            self.Ini_device()#create a fresh and new instance of GCS device (in case multiple instances of DAQ_MOVE_PI are opened)

            device=self.settings.child(('devices')).value()
            if not self.settings.child('dc_options','is_daisy').value(): #simple connection
                if self.settings.child(('connect_type')).value()=='USB':
                    self.gcs_device.ConnectUSB(device)
                elif self.settings.child(('connect_type')).value()=='TCP/IP':
                    self.gcs_device.ConnectTCPIPByDescription(device)
                elif self.settings.child(('connect_type')).value()=='RS232':
                    self.gcs_device.ConnectRS232(int(device[3:])) #in this case device is a COM port, and one should use 1 for COM1 for instance

            else: #one use a daisy chain connection with a master device and slaves
                if self.settings.child('dc_options','is_daisy_master').value(): #init the master

                    if self.settings.child(('connect_type')).value()=='USB':
                        dev_ids=self.gcs_device.OpenUSBDaisyChain(device)
                    elif self.settings.child(('connect_type')).value()=='TCP/IP':
                        dev_ids=self.gcs_device.OpenTCPIPDaisyChain(device)
                    elif self.settings.child(('connect_type')).value()=='RS232':
                        dev_ids=self.gcs_device.OpenRS232DaisyChain(int(device[3:])) #in this case device is a COM port, and one should use 1 for COM1 for instance

                    self.settings.child('dc_options','daisy_devices').setLimits(dev_ids)
                    self.settings.child('dc_options','daisy_id').setValue(self.gcs_device.dcid)

                self.gcs_device.ConnectDaisyChainDevice(self.settings.child('dc_options','index_in_chain').value()+1,self.settings.child('dc_options','daisy_id').value())

            self.settings.child(('controller_id')).setValue(self.gcs_device.qIDN())
            self.settings.child(('axis_address')).setLimits(self.gcs_device.axes)

            self.set_referencing(self.gcs_device.axes[0])

            self.status.controller=self.gcs_device.qIDN()

            self.status.info=self.status.controller
            self.status.stage=device
            self.status.initialized=True
            return self.status


        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e),'log']))
            self.status.info=str(e)
            self.status.initialized=False
            return self.status

    def is_referenced(self,axe):
        """
            Return the referencement statement from the hardware device.

            ============== ========== ============================================
            **Parameters**  **Type**   **Description**

             *axe*          string     Representing a connected axe on controller
            ============== ========== ============================================

            Returns
            -------
            ???

        """
        return self.gcs_device.qFRF(axe)

    def set_referencing(self,axes):
        """
            Set the referencement statement into the hardware device.

            ============== ============== ===========================================
            **Parameters**    **Type**      **Description**
             *axes*           string list  Representing connected axes on controller
            ============== ============== ===========================================
        """
        if type(axes) is not list:
            axes=[axes]
        for axe in axes:
            #set referencing mode
            if type(axe) is str:
                if not self.is_referenced(axe):
                    self.gcs_device.RON(axe,True)
                    self.gcs_device.FRF(axe)

    def Close(self):
        """
            Close the current instance of PI_GCS2 instrument.
        """
        if not self.settings.child('dc_options','is_daisy').value(): #simple connection
            self.gcs_device.CloseConnection()
        else:
            self.gcs_device.CloseDaisyChain()

    def Stop_Motion(self):
        """
            See Also
            --------
            DAQ_Move_base.Move_Done
        """
        self.gcs_device.StopAll()
        self.Move_Done()

    def Check_position(self):
        """
            Get the current hardware position with scaling conversion of the PI_GCS2 instrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, DAQ_utils.ThreadCommand
        """
        self.set_referencing(self.settings.child(('axis_address')).value())
        pos_dict=self.gcs_device.qPOS(self.settings.child(('axis_address')).value())
        pos=pos_dict[self.settings.child(('axis_address')).value()]
        pos=self.get_position_with_scaling(pos)
        self.current_position=pos
        self.emit_status(ThreadCommand('Check_position',[pos]))
        return pos

    def Move_Abs(self,position):
        """
            Make the hardware absolute move of the PI_GCS2 instrument from the given position after thread command signal was received in DAQ_Move_main.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            DAQ_Move_PI.set_referencing, DAQ_Move_base.set_position_with_scaling, DAQ_Move_base.poll_moving

        """
        self.set_referencing(self.settings.child(('axis_address')).value())
        position=self.set_position_with_scaling(position)
        self.target_position=position
        out=self.gcs_device.MOV(self.settings.child(('axis_address')).value(),position)

        self.poll_moving()


    def Move_Rel(self,position):
        """
            Make the hardware relative move of the PI_GCS2 instrument from the given position after thread command signal was received in DAQ_Move_main.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            DAQ_Move_base.set_position_with_scaling, DAQ_Move_PI.set_referencing, DAQ_Move_base.poll_moving

        """
        position=self.set_position_with_scaling(position)
        self.target_position=position+self.current_position
        self.set_referencing(self.settings.child(('axis_address')).value())
        if self.gcs_device.HasMVR():
            out=self.gcs_device.MVR(self.settings.child(('axis_address')).value(),position)
        else:
            self.Move_abs(self.target_position)
        self.poll_moving()

    def Move_Home(self):
        """

            See Also
            --------
            DAQ_Move_PI.set_referencing, DAQ_Move_base.poll_moving
        """
        self.set_referencing(self.settings.child(('axis_address')).value())
        if self.gcs_device.HasGOH():
            self.gcs_device.GOH(self.settings.child(('axis_address')).value())
        else:
            self.gcs_device.FRF(self.settings.child(('axis_address')).value())
        self.poll_moving()


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

    params= [{'title': 'Units:', 'name': 'units', 'type': 'str', 'value': 'um', 'readonly': True}, #2I chose to use only microns and not nm
             {'title': 'Time interval (ms):', 'name': 'time_interval', 'type': 'int', 'value': 200},
             {'name': 'epsilon', 'type': 'float', 'value': 1},
             {'title': 'Controller Info:', 'name': 'controller_id', 'type': 'text', 'value': '', 'readonly': True},
             {'title': 'COM Port:', 'name': 'com_port', 'type': 'list', 'values': ports},
             {'title': 'Stage address:', 'name': 'axis_address', 'type': 'list', 'value': 'X', 'values': ['X','Y','Z']},
             {'title': 'TTL settings:', 'name': 'ttl_settings','type': 'group', 'visible':False, 'children': [
                 {'title': 'TTL 1:', 'name': 'ttl_1','type': 'group', 'children': TTL_children},
                 {'title': 'TTL 2:', 'name': 'ttl_2','type': 'group', 'children': TTL_children},
                 {'title': 'TTL 3:', 'name': 'ttl_3','type': 'group', 'children': TTL_children},
                 {'title': 'TTL 4:', 'name': 'ttl_4','type': 'group', 'children': TTL_children},
                 ]}
             ]+comon_parameters


    def __init__(self,parent=None,params_state=None):
        super(DAQ_Move_PiezoConcept,self).__init__(parent,params_state)

        self.piezo=None


    def Ini_Stage(self,controller=None,stage=None):
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
            DAQ_utils.ThreadCommand
        """
        self.status.update(edict(info="",controller=None,stage=None))
        try:
            if self.piezo is not None:
                try:
                    self.Close()
                except:
                    pass

            if controller is None:
                self.piezo=pzcpt.PiezoConcept()
            else:
                self.piezo=controller
            self.piezo.init_communication(self.settings.child(('com_port')).value())

            controller_id=self.piezo.get_controller_infos()
            self.settings.child(('controller_id')).setValue(controller_id)
            self.status.info=controller_id
            self.status.controller=self.piezo
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
        self.piezo.close_communication()
        self.piezo=None


    def Check_position(self):
        """
            Check the current position from the hardware.

            Returns
            -------
            float
                The position of the hardware.

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, DAQ_utils.ThreadCommand
        """
        position=self.piezo.get_position(self.settings.child(('axis_address')).value())
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
        self.target_position=position
        position=self.set_position_with_scaling(position)
        pos=pzcpt.Position(self.settings.child(('axis_address')).value(),position)
        out=self.piezo.move_axis('ABS',pos)
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
        self.target_position=self.current_position+position

        position=self.set_position_with_scaling(position)
        pos=pzcpt.Position(self.settings.child(('axis_address')).value(),position)
        out=self.piezo.move_axis('REL',pos)
        self.poll_moving()

    def Move_Home(self):
        """
            Move to the absolute vlue 100 corresponding the default point of the Piezo instrument.

            See Also
            --------
            DAQ_Move_base.Move_Abs
        """
        self.Move_Abs(100) #put the axis on the middle position so 100µm


if __name__=='__main__':
    test=DAQ_Move_PI()


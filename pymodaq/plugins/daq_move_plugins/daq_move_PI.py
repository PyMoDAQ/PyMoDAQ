from pymodaq.daq_move.utility_classes import DAQ_Move_base
from pymodaq.daq_move.utility_classes import comon_parameters
import os
from pymodaq.daq_utils.daq_utils import ThreadCommand
from easydict import EasyDict as edict
import platform

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
        daq_utils.ThreadCommand
    """

    GCS_path = "C:\\ProgramData\\PI\\GCSTranslator"
    #GCS_path = "C:\\Program Files (x86)\\PI\\GCSTranslator"

    from pipython import GCSDevice
    from pipython.interfaces.gcsdll import DLLDEVICES
    #check for installed dlls
    flag=False
    if '64' in platform.machine():
        machine = "64"
    for dll_name_tmp in DLLDEVICES:
        for file in os.listdir(GCS_path):
            if dll_name_tmp in file and '.dll' in file and machine in file:
                dll_name = file
                flag = True
            if flag:
                break
        if flag:
            break

    gcs_device = GCSDevice(gcsdll=os.path.join(GCS_path,dll_name))
    devices = gcs_device.EnumerateUSB()

    import serial.tools.list_ports as list_ports
    is_multiaxes=False
    stage_names=[]

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
             {'title': 'Closed loop?:', 'name': 'closed_loop', 'type': 'bool', 'value': True},
           {'title': 'Controller ID:', 'name': 'controller_id', 'type': 'str', 'value': '', 'readonly': True},
           {'title': 'Stage address:', 'name': 'axis_address', 'type': 'list'},
          {'title': 'MultiAxes:', 'name': 'multiaxes', 'type': 'group','visible':is_multiaxes, 'children':[
                    {'title': 'is Multiaxes:', 'name': 'ismultiaxes', 'type': 'bool', 'value': is_multiaxes, 'default': False},
                    {'title': 'Status:', 'name': 'multi_status', 'type': 'list', 'value': 'Master', 'values': ['Master','Slave']},
                    {'title': 'Axis:', 'name': 'axis', 'type': 'list',  'values':stage_names},

                    ]}]+comon_parameters





    def __init__(self,parent=None,params_state=None):

        super(DAQ_Move_PI,self).__init__(parent,params_state)
        self.settings.child(('epsilon')).setValue(0.01)



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
            daq_utils.ThreadCommand, DAQ_Move_PI.enumerate_devices
        """
        try:
            if param.name()=='gcs_lib':
                try:
                    self.controller.CloseConnection()
                except Exception as e:
                    self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))
                self.Ini_device()

            elif param.name()=='connect_type':
                self.enumerate_devices()

            elif param.name()=='use_joystick':
                axes = self.controller.axes
                for ind, ax in enumerate(axes):
                    try:
                        if param.value():
                            res = self.controller.JAX(1, ind+1, ax)
                            res = self.controller.JON(ind+1, True)
                        else:
                            self.controller.JON(ind+1, False)
                    except Exception as e:
                        pass


                pass
            elif param.name() == 'axis_address':
                self.settings.child(('closed_loop')).setValue(self.controller.qSVO(param.value())[param.value()])
                self.set_referencing(self.settings.child(('axis_address')).value())

            elif param.name()=='closed_loop':
                axe=self.settings.child(('axis_address')).value()
                if self.controller.qSVO(axe)[axe] != self.settings.child(('closed_loop')).value():
                    self.controller.SVO(axe,param.value())

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [str(e), 'log']))


    def enumerate_devices(self):
        """
            Enumerate PI_GCS2 devices from the connection type.

            Returns
            -------
            string list
                The list of the devices port.

            See Also
            --------
            daq_utils.ThreadCommand
        """
        try:
            devices=[]
            if self.settings.child(('connect_type')).value()=='USB':
                devices=self.controller.EnumerateUSB()
            elif self.settings.child(('connect_type')).value()=='TCP/IP':
                devices=self.controller.EnumerateTCPIPDevices()
            elif self.settings.child(('connect_type')).value()=='RS232':
                devices=[str(port) for port in list(self.list_ports.comports())]

            self.settings.child(('devices')).setLimits(devices)


            return devices
        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status",[str(e),'log']))

    def Ini_device(self):
        """
            load the correct dll given the chosen device

            See Also
            --------
            DAQ_Move_base.Close
        """
        from pipython import GCSDevice
        from pipython.interfaces.gcsdll import DLLDEVICES
        try:
            self.Close()
        except: pass
        device = self.settings.child(('devices')).value().rsplit(' ')
        dll = None
        flag = False
        for dll_tmp in DLLDEVICES:
            for dev in DLLDEVICES[dll_tmp]:
                for d in device:
                    if d in dev or dev in d:
                        res=self.check_dll_exist(dll_tmp)
                        if res[0]:
                            dll = res[1]
                            flag = True
                            break
                if flag:
                    break
            if flag:
                break

        if dll is None:
            raise Exception('No valid dll found for the given device')

        self.controller=GCSDevice(gcsdll=os.path.join(self.settings.child(('gcs_lib')).value(),dll))

    def check_dll_exist(self, dll_name):
        files=os.listdir(self.settings.child(('gcs_lib')).value())
        machine=''
        if '64' in platform.machine():
            machine = '64'
        res= (False,'')
        for file in files:
            if 'dll' in file and machine in file and dll_name in file:
                res = (True, file)
        return res

    def Ini_Stage(self,controller=None):
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
            DAQ_Move_PI.set_referencing, daq_utils.ThreadCommand
        """

        try:
            device=""
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
                self.Ini_device()#create a fresh and new instance of GCS device (in case multiple instances of DAQ_MOVE_PI are opened)

                device=self.settings.child(('devices')).value()
                if not self.settings.child('dc_options','is_daisy').value(): #simple connection
                    if self.settings.child(('connect_type')).value()=='USB':
                        self.controller.ConnectUSB(device)
                    elif self.settings.child(('connect_type')).value()=='TCP/IP':
                        self.controller.ConnectTCPIPByDescription(device)
                    elif self.settings.child(('connect_type')).value()=='RS232':
                        self.controller.ConnectRS232(int(device[3:])) #in this case device is a COM port, and one should use 1 for COM1 for instance

                else: #one use a daisy chain connection with a master device and slaves
                    if self.settings.child('dc_options','is_daisy_master').value(): #init the master

                        if self.settings.child(('connect_type')).value()=='USB':
                            dev_ids=self.controller.OpenUSBDaisyChain(device)
                        elif self.settings.child(('connect_type')).value()=='TCP/IP':
                            dev_ids=self.controller.OpenTCPIPDaisyChain(device)
                        elif self.settings.child(('connect_type')).value()=='RS232':
                            dev_ids=self.controller.OpenRS232DaisyChain(int(device[3:])) #in this case device is a COM port, and one should use 1 for COM1 for instance

                        self.settings.child('dc_options','daisy_devices').setLimits(dev_ids)
                        self.settings.child('dc_options','daisy_id').setValue(self.controller.dcid)

                    self.controller.ConnectDaisyChainDevice(self.settings.child('dc_options','index_in_chain').value()+1,self.settings.child('dc_options','daisy_id').value())

            self.settings.child(('controller_id')).setValue(self.controller.qIDN())
            self.settings.child(('axis_address')).setLimits(self.controller.axes)

            self.set_referencing(self.controller.axes[0])

            #check servo status:
            self.settings.child(('closed_loop')).setValue(self.controller.qSVO(self.controller.axes[0])[self.controller.axes[0]])

            self.status.controller=self.controller

            self.status.info="connected on device:{} /".format(device)+self.controller.qIDN()
            self.status.controller=self.controller
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
        try:
            return self.controller.qFRF(axe)
        except:
            return True

    def set_referencing(self,axes):
        """
            Set the referencement statement into the hardware device.

            ============== ============== ===========================================
            **Parameters**    **Type**      **Description**
             *axes*           string list  Representing connected axes on controller
            ============== ============== ===========================================
        """
        try:
            if type(axes) is not list:
                axes=[axes]
            for axe in axes:
                #set referencing mode
                if type(axe) is str:
                    if not self.is_referenced(axe)[axe]:
                        self.controller.RON(axe,True)
                        self.controller.FRF(axe)
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status',[str(e)+" / Referencing not enabled with this dll",'log']))

    def Close(self):
        """
            Close the current instance of PI_GCS2 instrument.
        """
        if not self.settings.child('dc_options','is_daisy').value(): #simple connection
            self.controller.CloseConnection()
        else:
            self.controller.CloseDaisyChain()

    def Stop_Motion(self):
        """
            See Also
            --------
            DAQ_Move_base.Move_Done
        """
        self.controller.StopAll()
        self.Move_Done()

    def Check_position(self):
        """
            Get the current hardware position with scaling conversion of the PI_GCS2 instrument provided by get_position_with_scaling

            See Also
            --------
            DAQ_Move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        self.set_referencing(self.settings.child(('axis_address')).value())
        pos_dict=self.controller.qPOS(self.settings.child(('axis_address')).value())
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

        position=self.check_bound(position)
        self.target_position=position

        position=self.set_position_with_scaling(position)
        out=self.controller.MOV(self.settings.child(('axis_address')).value(),position)

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
        position=self.check_bound(self.current_position+position)-self.current_position
        self.target_position=position+self.current_position



        if self.controller.HasMVR():
            out=self.controller.MVR(self.settings.child(('axis_address')).value(),position)
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
        if self.controller.HasGOH():
            self.controller.GOH(self.settings.child(('axis_address')).value())
        else:
            self.controller.FRF(self.settings.child(('axis_address')).value())
        self.poll_moving()

if __name__ == "__main__":
    test=DAQ_Move_PI()
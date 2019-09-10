from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QVariant, QSize
# from enum import IntEnum
from easydict import EasyDict as edict
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree
from pymodaq.daq_utils.daq_utils import ThreadCommand, getLineInfo, check_received_length, check_sended,\
    message_to_bytes, send_scalar, send_string, get_scalar, get_int, get_string, send_list
import socket
import select
import os
import sys
import numpy as np
from collections import OrderedDict
from pymodaq.daq_utils.tcp_server_client import TCPServer, tcp_parameters


comon_parameters=[{'title': 'Units:', 'name': 'units', 'type': 'str', 'value': '', 'readonly' : True},
                  {'name': 'epsilon', 'type': 'float', 'value': 0.01},
                  {'title': 'Timeout (ms):', 'name': 'timeout', 'type': 'int', 'value': 10000, 'default': 10000},

                    {'title': 'Bounds:', 'name': 'bounds', 'type': 'group', 'children':[
                        {'title': 'Set Bounds:', 'name': 'is_bounds', 'type': 'bool', 'value': False},
                        {'title': 'Min:', 'name': 'min_bound', 'type': 'float', 'value': 0, 'default': 0},
                        {'title': 'Max:', 'name': 'max_bound', 'type': 'float', 'value': 1, 'default': 1},]},
                    
                    {'title': 'Scaling:', 'name': 'scaling', 'type': 'group', 'children':[
                         {'title': 'Use scaling:', 'name': 'use_scaling', 'type': 'bool', 'value': False, 'default': False},
                         {'title': 'Scaling factor:', 'name': 'scaling', 'type': 'float', 'value': 1., 'default': 1.},
                         {'title': 'Offset factor:', 'name': 'offset', 'type': 'float', 'value': 0., 'default': 0.}]}]



class DAQ_Move_base(QObject):
    """ The base class to be herited by all actuator modules

    This base class implements all necessary parameters and methods for the plugin to communicate with its parent (the
    DAQ_Move module)

    Parameters
    ----------
    parent : DAQ_Move_stage instance (see daq_viewer_main module)
    params_state : Parameter instance (pyqtgraph) from which the module will get the initial settings (as defined in the preset)


    :ivar Move_Done_signal: pyqtSignal signal represented by a float. Is emitted each time the hardware reached the target
                            position within the epsilon precision (see comon_parameters variable)

    :ivar controller: the object representing the hardware in the plugin. Used to access hardware functionality

    :ivar status: easydict instance to set information (str), controller object, stage object (if required) and initialized
                  state (bool) to return to parent after initialization

    :ivar settings: Parameter instance representing the hardware settings defined from the params attribute. Modifications
                    on the GUI settings will be transferred to this attribute. It stores at all times the current state of the hardware/plugin

    :ivar params: class level attribute. List of dict used to create a Parameter object. Its definition on the class level enable
                  the automatic update of the GUI settings when changing plugins (even in preset mode creation). To be populated
                  on the plugin level as the base class does't represents a real hardware

    :ivar is_multiaxes: class level attribute (bool). Defines if the plugin controller controls multiple axes. If True, one has to define
                        a Master instance of this plugin and slave instances of this plugin (all sharing the same controller_ID Parameter)

    :ivar current_position: (float) stores the current position after each call to the check_position in the child module

    :ivar target_position: (float) stores the target position the controller should reach within epsilon

    """


    Move_Done_signal=pyqtSignal(float)
    is_multiaxes=False
    params= []
    _controller_units = ''

    def __init__(self,parent=None,params_state=None):
        QObject.__init__(self) #to make sure this is the parent class
        self.move_is_done = False
        self.parent=parent
        self.controller=None
        self.stage=None
        self.status=edict(info="",controller=None,stage=None,initialized=False)
        self.current_position=0
        self.target_position=0
        self.parent_parameters_path = []  # this is to be added in the send_param_status to take into account when the current class instance parameter list is a child of some other class
        self.settings=Parameter.create(name='Settings', type='group', children=self.params)
        if params_state is not None:
            if isinstance(params_state, dict):
                self.settings.restoreState(params_state)
            elif isinstance(params_state, Parameter):
                self.settings.restoreState(params_state.saveState())

        self.settings.sigTreeStateChanged.connect(self.send_param_status)
        self.controller_units = self._controller_units

    @property
    def controller_units(self):
        return self._controller_units

    @controller_units.setter
    def controller_units(self, units: str = ''):
        self._controller_units = units
        try:
            self.settings.child(('units')).setValue(units)
        except:
            pass

    def check_bound(self,position):
        self.move_is_done = False
        if self.settings.child('bounds','is_bounds').value():
            if position>self.settings.child('bounds','max_bound').value():
                position=self.settings.child('bounds','max_bound').value()
                self.emit_status(ThreadCommand('outofbounds',[]))
            elif position<self.settings.child('bounds','min_bound').value():
                position=self.settings.child('bounds','min_bound').value()
                self.emit_status(ThreadCommand('outofbounds',[]))
        return position

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
            QtWidgets.QApplication.processEvents()
        else:
            print(status)

    def commit_settings(self,param):
      """
        to subclass to transfer parameters to hardware
      """
      pass

    def commit_common_settings(self,param):
        pass

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

    def move_done(self, position=None):#the position argument is just there to match some signature of child classes
        """
            | Emit a move done signal transmitting the float position to hardware.
            | The position argument is just there to match some signature of child classes.

            =============== ========== =============================================================================
             **Arguments**   **Type**  **Description**
             *position*      float     The position argument is just there to match some signature of child classes
            =============== ========== =============================================================================

        """
        position=self.check_position()
        self.Move_Done_signal.emit(position)
        self.move_is_done = True

    def poll_moving(self):
        """
            Poll the current moving. In case of timeout emit the raise timeout Thread command.

            See Also
            --------
            DAQ_utils.ThreadCommand, move_done
        """
        sleep_ms=50
        ind=0
        while np.abs(self.check_position()-self.target_position)>self.settings.child(('epsilon')).value():
            if self.move_is_done:
                self.emit_status(ThreadCommand('Move has been stopped'))
                break
            QThread.msleep(sleep_ms)

            ind+=1

            if ind*sleep_ms >= self.settings.child(('timeout')).value():

                self.emit_status(ThreadCommand('raise_timeout'))
                break

            self.current_position=self.check_position()
            QtWidgets.QApplication.processEvents()
        self.move_done()


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
            if change == 'childAdded':
                self.emit_status(ThreadCommand('update_settings',
                                               [self.parent_parameters_path + path, [data[0].saveState(), data[1]],
                                                change]))  # send parameters values/limits back to the GUI. Send kind of a copy back the GUI otherwise the child reference will be the same in both th eUI and the plugin so one of them will be removed
            elif change == 'value' or change == 'limits' or change=='options':
                self.emit_status(ThreadCommand('update_settings', [self.parent_parameters_path+path, data, change])) #send parameters values/limits back to the GUI
            elif change == 'parent':
                pass

    def set_position_with_scaling(self, pos):
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
        if self.settings.child('scaling', 'use_scaling').value():
            pos=pos/self.settings.child('scaling', 'scaling').value()+self.settings.child('scaling', 'offset').value()
        return pos

    def set_position_relative_with_scaling(self, pos):
        """
            Set the scaled positions in case of relative moves
        """
        if self.settings.child('scaling', 'use_scaling').value():
            pos = pos/self.settings.child('scaling', 'scaling').value()
        return pos

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
        path = settings_parameter_dict['path']
        param = settings_parameter_dict['param']
        change = settings_parameter_dict['change']
        try:
            self.settings.sigTreeStateChanged.disconnect(self.send_param_status)
        except:
            pass
        if change == 'value':
            self.settings.child(*path[1:]).setValue(param.value())  # blocks signal back to main UI
        elif change == 'childAdded':
            child = Parameter.create(name='tmp')
            child.restoreState(param)
            self.settings.child(*path[1:]).addChild(child)  # blocks signal back to main UI
            param = child

        elif change == 'parent':
            children = custom_tree.get_param_from_name(self.settings, param.name())

            if children is not None:
                path = custom_tree.get_param_path(children)
                self.settings.child(*path[1:-1]).removeChild(children)

        self.settings.sigTreeStateChanged.connect(self.send_param_status)
        self.commit_common_settings(param)
        self.commit_settings(param)

class DAQ_Move_TCP_server(DAQ_Move_base, TCPServer):
    """
        ================= ==============================
        **Attributes**      **Type**
        *command_server*    instance of pyqtSignal
        *x_axis*            1D numpy array
        *y_axis*            1D numpy array
        *data*              double precision float array
        ================= ==============================

        See Also
        --------
        utility_classes.DAQ_TCP_server
    """
    params_client =[] #parameters of a client grabber
    command_server=pyqtSignal(list)

    message_list=["Quit", "Status","Done","Server Closed","Info","Infos", "Info_xml", "move_abs",
                  'move_home', 'move_rel', 'check_position', 'stop_motion', 'position_is', 'move_done']
    socket_types=["ACTUATOR"]
    params=comon_parameters +  tcp_parameters


    def __init__(self,parent=None,params_state=None):
        """

        Parameters
        ----------
        parent
        params_state
        """
        self.client_type = "ACTUATOR"
        DAQ_Move_base.__init__(self, parent,params_state) #initialize base class with commom attributes and methods
        self.settings.child(('bounds')).hide()
        self.settings.child(('scaling')).hide()
        self.settings.child(('epsilon')).setValue(1)


        TCPServer.__init__(self, self.client_type)

    def command_to_from_client(self,command):
        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client 'ACTUATOR' is connected then send it the command

            if command == 'position_is':
                pos = get_scalar(sock)

                pos = self.get_position_with_scaling(pos)
                self.current_position = pos
                self.emit_status(ThreadCommand('check_position', [pos]))

            elif command == 'move_done':
                pos = get_scalar(sock)
                pos = self.get_position_with_scaling(pos)
                self.current_position = pos
                self.emit_status(ThreadCommand('move_done', [pos]))


    def commit_settings(self,param):

        if param.name() in custom_tree.iter_children(self.settings.child(('infos')), []):
            actuator_socket = [client['socket'] for client in self.connected_clients if client['type'] == 'ACTUATOR'][0]
            send_string(actuator_socket, 'set_info')
            path = custom_tree.get_param_path(param)[2:]#get the path of this param as a list starting at parent 'infos'

            send_list(actuator_socket, path)

            #send value
            data = custom_tree.parameter_to_xml_string(param)
            send_string(actuator_socket, data)

    def ini_stage(self, controller=None):
        """
            | Initialisation procedure of the detector updating the status dictionnary.
            |
            | Init axes from image , here returns only None values (to tricky to di it with the server and not really necessary for images anyway)

            See Also
            --------
            utility_classes.DAQ_TCP_server.init_server, get_xaxis, get_yaxis
        """
        self.status.update(edict(initialized=False,info="",x_axis=None,y_axis=None,controller=None))
        try:
            self.settings.child(('infos')).addChildren(self.params_client)

            self.init_server()

            self.status.info = 'TCP Server actuator'
            self.status.initialized=True
            self.status.controller=self.serversocket
            return self.status

        except Exception as e:
            self.status.info=getLineInfo()+ str(e)
            self.status.initialized=False
            return self.status

    def close(self):
        """
            Should be used to uninitialize hardware.

            See Also
            --------
            utility_classes.DAQ_TCP_server.close_server
        """
        self.listening=False
        self.close_server()

    def move_Abs(self,position):
        """

        """
        position=self.check_bound(position)
        self.target_position=position

        position=self.set_position_with_scaling(position)

        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client self.client_type is connected then send it the command
            send_string(sock, 'move_abs')
            send_scalar(sock, position)

            #self.poll_moving()

    def move_Rel(self, position):
        position=self.check_bound(self.current_position+position)-self.current_position
        self.target_position=position+self.current_position

        position=self.set_position_relative_with_scaling(position)
        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client self.client_type is connected then send it the command
            send_string(sock, 'move_rel')
            send_scalar(sock, position)

            #self.poll_moving()

    def move_Home(self):
        """
            Make the absolute move to original position (0).

            See Also
            --------
            move_Abs
        """
        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client self.client_type is connected then send it the command
            send_string(sock, 'move_home')

    def check_position(self):
        """
            Get the current hardware position with scaling conversion given by get_position_with_scaling.

            See Also
            --------
            daq_move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client self.client_type is connected then send it the command
            self.send_command(sock, 'check_position')

        return self.current_position

    def stop_motion(self):
        """
            See Also
            --------
            daq_move_base.move_done
        """
        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client self.client_type is connected then send it the command
            self.send_command(sock, 'stop_motion')


    def stop(self):
        """
            not implemented.
        """
        pass
        return ""




if __name__=='__main__':
    test=DAQ_Move_base()
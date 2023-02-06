from qtpy import QtWidgets
from qtpy.QtCore import QObject, Slot, QThread, Signal, QTimer

from easydict import EasyDict as edict
import pymodaq.daq_utils.daq_utils as utils
import pymodaq.daq_utils.parameter.utils as putils
from pymodaq.daq_utils.parameter import ioxml
from pyqtgraph.parametertree import Parameter
from pymodaq.daq_utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.daq_utils.config import Config
from pymodaq.daq_utils.tcp_server_client import TCPServer, tcp_parameters
from pymodaq.daq_utils.messenger import deprecation_msg
import numpy as np
from time import perf_counter

logger = utils.set_logger(utils.get_module_name(__file__))
config = Config()


def comon_parameters(epsilon=config('actuator', 'epsilon_default')):
    return [{'title': 'Units:', 'name': 'units', 'type': 'str', 'value': '', 'readonly': True},
            {'title': 'Epsilon:', 'name': 'epsilon', 'type': 'float',
             'value': epsilon,
             'tip': 'Differential Value at which the controller considers it reached the target position'},
            {'title': 'Timeout (s):', 'name': 'timeout', 'type': 'int',
             'value': config('actuator', 'polling_timeout_s')},
            {'title': 'Bounds:', 'name': 'bounds', 'type': 'group', 'children': [
                {'title': 'Set Bounds:', 'name': 'is_bounds', 'type': 'bool', 'value': False},
                {'title': 'Min:', 'name': 'min_bound', 'type': 'float', 'value': 0, 'default': 0},
                {'title': 'Max:', 'name': 'max_bound', 'type': 'float', 'value': 1, 'default': 1}, ]},
            {'title': 'Scaling:', 'name': 'scaling', 'type': 'group', 'children': [
                {'title': 'Use scaling:', 'name': 'use_scaling', 'type': 'bool', 'value': False,
                 'default': False},
                {'title': 'Scaling factor:', 'name': 'scaling', 'type': 'float', 'value': 1., 'default': 1.},
                {'title': 'Offset factor:', 'name': 'offset', 'type': 'float', 'value': 0., 'default': 0.}]}]


MOVE_COMMANDS = ['abs', 'rel', 'home']


class MoveCommand:
    def __init__(self, move_type, value=0):
        if move_type not in MOVE_COMMANDS:
            raise ValueError(f'The allowed move types fro an actuator are {MOVE_COMMANDS}')
        self.move_type = move_type
        self.value = value


def comon_parameters_fun(is_multiaxes=False, axes_names=[], master=True, epsilon=config('actuator', 'epsilon_default')):
    """Function returning the common and mandatory parameters that should be on the actuator plugin level

    Parameters
    ----------
    is_multiaxes: bool
        If True, display the particular settings to define which axis the controller is driving
    axes_names: list of str
        The string identifier of every axis the controller can drive
    master: bool
        If True consider this plugin has to init the controller, otherwise use an already initialized instance
    """
    params = [{'title': 'MultiAxes:', 'name': 'multiaxes', 'type': 'group', 'visible': is_multiaxes, 'children': [
        {'title': 'is Multiaxes:', 'name': 'ismultiaxes', 'type': 'bool', 'value': is_multiaxes,
         'default': False},
        {'title': 'Status:', 'name': 'multi_status', 'type': 'list', 'value': 'Master' if master else 'Slave',
         'limits': ['Master', 'Slave']},
        {'title': 'Axis:', 'name': 'axis', 'type': 'list', 'limits': axes_names},

    ]}] + comon_parameters(epsilon)
    return params


params = [
    {'title': 'Main Settings:', 'name': 'main_settings', 'type': 'group', 'children': [
        {'title': 'Actuator type:', 'name': 'move_type', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Controller ID:', 'name': 'controller_ID', 'type': 'int', 'value': 0, 'default': 0},
        {'title': 'TCP/IP options:', 'name': 'tcpip', 'type': 'group', 'visible': True, 'expanded': False,
         'children': [
             {'title': 'Connect to server:', 'name': 'connect_server', 'type': 'bool_push', 'label': 'Connect',
              'value': False},
             {'title': 'Connected?:', 'name': 'tcp_connected', 'type': 'led', 'value': False},
             {'title': 'IP address:', 'name': 'ip_address', 'type': 'str',
              'value': config('network', 'tcp-server', 'ip')},
             {'title': 'Port:', 'name': 'port', 'type': 'int', 'value': config('network', 'tcp-server', 'port')},
         ]},
    ]},
    {'title': 'Actuator Settings:', 'name': 'move_settings', 'type': 'group'}
]


def main(plugin_file, init=True, title='test'):
    """
    this method start a DAQ_Move object with this defined plugin as actuator
    Returns
    -------

    """
    import sys
    from qtpy import QtWidgets
    from pymodaq.daq_move.daq_move_main import DAQ_Move
    from pathlib import Path
    app = QtWidgets.QApplication(sys.argv)
    if config('style', 'darkstyle'):
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet())

    Form = QtWidgets.QWidget()
    prog = DAQ_Move(Form, title=title,)
    Form.show()
    prog.actuator = Path(plugin_file).stem[9:]
    if init:
        prog.init()

    sys.exit(app.exec_())


class DAQ_Move_base(QObject):
    """ The base class to be inherited by all actuator modules

    This base class implements all necessary parameters and methods for the plugin to communicate with its parent (the
    DAQ_Move module)

    Parameters
    ----------
    parent : DAQ_Move_stage instance (see daq_viewer_main module)
    params_state : Parameter instance (pyqtgraph) from which the module will get the initial settings (as defined in the managers)


    :ivar Move_Done_signal: Signal signal represented by a float. Is emitted each time the hardware reached the target
                            position within the epsilon precision (see comon_parameters variable)

    :ivar controller: the object representing the hardware in the plugin. Used to access hardware functionality

    :ivar status: easydict instance to set information (str), controller object, stage object (if required) and initialized
                  state (bool) to return to parent after initialization

    :ivar settings: Parameter instance representing the hardware settings defined from the params attribute. Modifications
                    on the GUI settings will be transferred to this attribute. It stores at all times the current state of the hardware/plugin

    :ivar params: class level attribute. List of dict used to create a Parameter object. Its definition on the class level enable
                  the automatic update of the GUI settings when changing plugins (even in managers mode creation). To be populated
                  on the plugin level as the base class does't represents a real hardware

    :ivar is_multiaxes: class level attribute (bool). Defines if the plugin controller controls multiple axes. If True, one has to define
                        a Master instance of this plugin and slave instances of this plugin (all sharing the same controller_ID Parameter)

    :ivar current_position: (float) stores the current position after each call to the get_actuator_value in the child module

    :ivar target_position: (float) stores the target position the controller should reach within epsilon

    """

    Move_Done_signal = Signal(float)
    is_multiaxes = False
    stage_names = [] #deprecated
    axes_names = []
    params = []
    _controller_units = ''
    _epsilon = 1

    def __init__(self, parent=None, params_state=None):
        QObject.__init__(self)  # to make sure this is the parent class
        self.move_is_done = False
        self.parent = parent
        self.shamrock_controller = None
        self.stage = None
        self.status = edict(info="", controller=None, stage=None, initialized=False)
        self.current_position = 0.
        self.target_position = 0.
        self._ispolling = True
        self.parent_parameters_path = []  # this is to be added in the send_param_status to take into account when the
        # current class instance parameter list is a child of some other class
        self.settings = Parameter.create(name='Settings', type='group', children=self.params)
        if params_state is not None:
            if isinstance(params_state, dict):
                self.settings.restoreState(params_state)
            elif isinstance(params_state, Parameter):
                self.settings.restoreState(params_state.saveState())

        self.settings.sigTreeStateChanged.connect(self.send_param_status)
        self.controller_units = self._controller_units
        self.controller = None
        #
        # if self.settings['epsilon'] == config('actuator', 'epsilon_default'):
        #     self.settings.child('epsilon').setValue(self._epsilon)

        self.poll_timer = QTimer()
        self.poll_timer.setInterval(config('actuator', 'polling_interval_ms'))
        self._poll_timeout = config('actuator', 'polling_timeout_s')
        self.poll_timer.timeout.connect(self.check_target_reached)

        self.ini_attributes()

    def ini_attributes(self):
        pass

    def ini_stage_init(self, old_controller=None, new_controller=None):
        """Manage the Master/Slave controller issue

        First initialize the status dictionnary
        Then check whether this stage is controlled by a multiaxe controller (to be defined for each plugin)
            if it is a multiaxes controller then:
            * if it is Master: init the controller here
            * if it is Slave: use an already initialized controller (defined in the preset of the dashboard)

        Parameters
        ----------
        old_controller: object
            The particular object that allow the communication with the hardware, in general a python wrapper around the
            hardware library. In case of Slave this one comes from a previously initialized plugin
        new_controller: object
            The particular object that allow the communication with the hardware, in general a python wrapper around the
            hardware library. In case of Master it is the new instance of your plugin controller
        """
        self.status.update(edict(info="", controller=None, initialized=False))
        if self.settings['multiaxes', 'ismultiaxes'] and self.settings['multiaxes', 'multi_status'] == "Slave":
            if old_controller is None:
                raise Exception('no controller has been defined externally while this axe is a slave one')
            else:
                controller = old_controller
        else:  # Master stage
            controller = new_controller
        self.controller = controller
        return controller

    @property
    def controller_units(self):
        return self._controller_units

    @controller_units.setter
    def controller_units(self, units: str = ''):
        self._controller_units = units
        try:
            self.settings.child('units').setValue(units)
        except Exception:
            pass

    @property
    def ispolling(self):
        return self._ispolling

    @ispolling.setter
    def ispolling(self, polling=True):
        self._ispolling = polling

    def check_bound(self, position):
        """

        Parameters
        ----------
        position

        Returns
        -------

        """
        if self.settings.child('bounds', 'is_bounds').value():
            if position > self.settings.child('bounds', 'max_bound').value():
                position = self.settings.child('bounds', 'max_bound').value()
                self.emit_status(ThreadCommand('outofbounds', []))
            elif position < self.settings.child('bounds', 'min_bound').value():
                position = self.settings.child('bounds', 'min_bound').value()
                self.emit_status(ThreadCommand('outofbounds', []))
        return position

    def get_actuator_value(self):
        if hasattr(self, 'check_position'):
            deprecation_msg('check_position method in plugins is deprecated, use get_actuator_value',3)
            return self.check_position()
        else:
            raise NotImplementedError

    def move_abs(self, value):
        if hasattr(self, 'move_Abs'):
            deprecation_msg('move_Abs method in plugins is deprecated, use move_abs',3)
            self.move_Abs(value)
        else:
            raise NotImplementedError

    def move_rel(self, value):
        if hasattr(self, 'move_Rel'):
            deprecation_msg('move_Rel method in plugins is deprecated, use move_rel',3)
            self.move_Rel(value)
        else:
            raise NotImplementedError

    def move_home(self):
        if hasattr(self, 'move_Home'):
            deprecation_msg('move_Home method in plugins is deprecated, use move_home', 3)
            self.move_Home()
        else:
            raise NotImplementedError

    def emit_status(self, status):
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

    def commit_settings(self, param):
        """
          to subclass to transfer parameters to hardware
        """
        pass

    def commit_common_settings(self, param):
        pass

    def get_position_with_scaling(self, pos):
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
        if self.settings.child('scaling', 'use_scaling').value():
            pos = (pos - self.settings.child('scaling', 'offset').value()) * self.settings.child('scaling',
                                                                                                 'scaling').value()
        return pos

    def move_done(self, position=None):  # the position argument is just there to match some signature of child classes
        """
            | Emit a move done signal transmitting the float position to hardware.
            | The position argument is just there to match some signature of child classes.

            =============== ========== =============================================================================
             **Arguments**   **Type**  **Description**
             *position*      float     The position argument is just there to match some signature of child classes
            =============== ========== =============================================================================

        """
        if position is None:
            position = self.get_actuator_value()
        self.Move_Done_signal.emit(position)
        self.move_is_done = True

    def poll_moving(self):
        """
            Poll the current moving. In case of timeout emit the raise timeout Thread command.

            See Also
            --------
            DAQ_utils.ThreadCommand, move_done
        """
        if 'TCPServer' not in self.__class__.__name__:
            self.start_time = perf_counter()
            if self.ispolling:
                self.poll_timer.start()
            else:
                self.current_position = self.get_actuator_value()
                logger.debug(f'Current position: {self.current_position}')
                self.move_done(self.current_position)

    def check_target_reached(self):
        if np.abs(self.current_position - self.target_position) > self.settings.child('epsilon').value():
            logger.debug(f'Check move_is_done: {self.move_is_done}')
            if self.move_is_done:
                self.emit_status(ThreadCommand('Move has been stopped'))
                logger.info(f'Move has been stopped')

            self.current_position = self.get_actuator_value()
            self.emit_status(ThreadCommand('check_position', [self.current_position]))
            logger.debug(f'Current position: {self.current_position}')

            if perf_counter() - self.start_time >= self.settings.child('timeout').value():
                self.poll_timer.stop()
                self.emit_status(ThreadCommand('raise_timeout'))
                logger.info(f'Timeout activated')
        else:
            self.poll_timer.stop()
            logger.debug(f'Current position: {self.current_position}')
            self.move_done(self.current_position)

    def send_param_status(self, param, changes):
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
            elif change == 'value' or change == 'limits' or change == 'options':
                self.emit_status(ThreadCommand('update_settings', [self.parent_parameters_path + path, data,
                                                                   change]))  # send parameters values/limits back to the GUI
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
            pos = pos / self.settings.child('scaling', 'scaling').value() + self.settings.child('scaling',
                                                                                                'offset').value()
        return pos

    def set_position_relative_with_scaling(self, pos):
        """
            Set the scaled positions in case of relative moves
        """
        if self.settings.child('scaling', 'use_scaling').value():
            pos = pos / self.settings.child('scaling', 'scaling').value()
        return pos

    @Slot(edict)
    def update_settings(self, settings_parameter_dict):  # settings_parameter_dict=edict(path=path,param=param)
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
        except Exception:
            pass
        if change == 'value':
            self.settings.child(*path[1:]).setValue(param.value())  # blocks signal back to main UI
        elif change == 'childAdded':
            child = Parameter.create(name='tmp')
            child.restoreState(param)
            self.settings.child(*path[1:]).addChild(child)  # blocks signal back to main UI
            param = child

        elif change == 'parent':
            children = putils.get_param_from_name(self.settings, param.name())

            if children is not None:
                path = putils.get_param_path(children)
                self.settings.child(*path[1:-1]).removeChild(children)

        self.settings.sigTreeStateChanged.connect(self.send_param_status)
        self.commit_common_settings(param)
        self.commit_settings(param)


class DAQ_Move_TCP_server(DAQ_Move_base, TCPServer):
    """
        ================= ==============================
        **Attributes**      **Type**
        *command_server*    instance of Signal
        *x_axis*            1D numpy array
        *y_axis*            1D numpy array
        *data*              double precision float array
        ================= ==============================

        See Also
        --------
        utility_classes.DAQ_TCP_server
    """
    params_client = []  # parameters of a client grabber
    command_server = Signal(list)

    message_list = ["Quit", "Status", "Done", "Server Closed", "Info", "Infos", "Info_xml", "move_abs",
                    'move_home', 'move_rel', 'get_actuator_value', 'stop_motion', 'position_is', 'move_done']
    socket_types = ["ACTUATOR"]
    params = comon_parameters() + tcp_parameters

    def __init__(self, parent=None, params_state=None):
        """

        Parameters
        ----------
        parent
        params_state
        """
        self.client_type = "ACTUATOR"
        DAQ_Move_base.__init__(self, parent, params_state)  # initialize base class with commom attributes and methods
        self.settings.child(('bounds')).hide()
        self.settings.child(('scaling')).hide()
        self.settings.child(('epsilon')).setValue(1)

        TCPServer.__init__(self, self.client_type)

    def command_to_from_client(self, command):
        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client 'ACTUATOR' is connected then send it the command

            if command == 'position_is':
                pos = sock.get_scalar()

                pos = self.get_position_with_scaling(pos)
                self.current_position = pos
                self.emit_status(ThreadCommand('get_actuator_value', [pos]))

            elif command == 'move_done':
                pos = sock.get_scalar()
                pos = self.get_position_with_scaling(pos)
                self.current_position = pos
                self.emit_status(ThreadCommand('move_done', [pos]))
            else:
                self.send_command(sock, command)

    def commit_settings(self, param):

        if param.name() in putils.iter_children(self.settings.child(('settings_client')), []):
            actuator_socket = [client['socket'] for client in self.connected_clients if client['type'] == 'ACTUATOR'][0]
            actuator_socket.send_string('set_info')
            path = putils.get_param_path(param)[2:]
            # get the path of this param as a list starting at parent 'infos'

            actuator_socket.send_list(path)

            # send value
            data = ioxml.parameter_to_xml_string(param)
            actuator_socket.send_string(data)

    def ini_stage(self, controller=None):
        """
            | Initialisation procedure of the detector updating the status dictionnary.
            |
            | Init axes from image , here returns only None values (to tricky to di it with the server and not really necessary for images anyway)

            See Also
            --------
            utility_classes.DAQ_TCP_server.init_server, get_xaxis, get_yaxis
        """
        self.status.update(edict(initialized=False, info="", x_axis=None, y_axis=None, controller=None))
        try:
            self.settings.child(('infos')).addChildren(self.params_client)

            self.init_server()

            self.settings.child('units').hide()
            self.settings.child('epsilon').hide()

            self.status.info = 'TCP Server actuator'
            self.status.initialized = True
            self.status.controller = self.serversocket
            return self.status

        except Exception as e:
            self.status.info = getLineInfo() + str(e)
            self.status.initialized = False
            return self.status

    def close(self):
        """
            Should be used to uninitialize hardware.

            See Also
            --------
            utility_classes.DAQ_TCP_server.close_server
        """
        self.listening = False
        self.close_server()

    def move_Abs(self, position):
        """

        """
        position = self.check_bound(position)
        self.target_position = position

        position = self.set_position_with_scaling(position)

        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client self.client_type is connected then send it the command
            sock.send_string('move_abs')
            sock.send_scalar(position)

    def move_Rel(self, position):
        position = self.check_bound(self.current_position + position) - self.current_position
        self.target_position = position + self.current_position

        position = self.set_position_relative_with_scaling(position)
        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client self.client_type is connected then send it the command
            sock.send_string('move_rel')
            sock.send_scalar(position)

    def move_Home(self):
        """
            Make the absolute move to original position (0).

            See Also
            --------
            move_Abs
        """
        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client self.client_type is connected then send it the command
            sock.send_string('move_home')

    def get_actuator_value(self):
        """
            Get the current hardware position with scaling conversion given by get_position_with_scaling.

            See Also
            --------
            daq_move_base.get_position_with_scaling, daq_utils.ThreadCommand
        """
        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client self.client_type is connected then send it the command
            self.send_command(sock, 'get_actuator_value')

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


if __name__ == '__main__':
    test = DAQ_Move_base()

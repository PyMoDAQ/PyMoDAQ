from time import perf_counter
from typing import Union, List, Dict, TYPE_CHECKING
from numbers import Number

from easydict import EasyDict as edict
import numpy as np
from qtpy import QtWidgets
from qtpy.QtCore import QObject, Slot, Signal, QTimer

import pymodaq.utils.daq_utils as utils
import pymodaq.utils.parameter.utils as putils
from pymodaq.utils.parameter import Parameter
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.parameter import ioxml

from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo, find_keys_from_val
from pymodaq.utils import config as configmod
from pymodaq.utils.tcp_ip.tcp_server_client import TCPServer, tcp_parameters
from pymodaq.utils.messenger import deprecation_msg
from pymodaq.utils.data import DataActuator
from pymodaq.utils.enums import BaseEnum, enum_checker
from pymodaq.utils.tcp_ip.mysocket import Socket
from pymodaq.utils.tcp_ip.serializer import DeSerializer, Serializer

if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move_Hardware

logger = set_logger(get_module_name(__file__))
config = configmod.Config()


class DataActuatorType(BaseEnum):
    """Enum for new or old style holding the value of the actuator"""
    float = 0
    DataActuator = 1


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
    """Utility class to contain a given move type and value

    Attributes
    ----------
    move_type: str
        either:

        * 'abs': performs an absolute action
        * 'rel': performs a relative action
        * 'home': find the actuator's home
    value: float
        the value the move should reach

    """
    def __init__(self, move_type, value=0):
        if move_type not in MOVE_COMMANDS:
            raise ValueError(f'The allowed move types fro an actuator are {MOVE_COMMANDS}')
        self.move_type = move_type
        self.value = value


def comon_parameters_fun(is_multiaxes=False, axes_names=[], axis_names=[], master=True, epsilon=config('actuator', 'epsilon_default')):
    """Function returning the common and mandatory parameters that should be on the actuator plugin level

    Parameters
    ----------
    is_multiaxes: bool
        If True, display the particular settings to define which axis the controller is driving
    axis_names: list of str
        The string identifier of every axis the controller can drive
    master: bool
        If True consider this plugin has to init the controller, otherwise use an already initialized instance
    """
    if axis_names == [] and len(axes_names) != 0:
        axis_names = axes_names

    params = [
                 {'title': 'MultiAxes:', 'name': 'multiaxes', 'type': 'group', 'visible': is_multiaxes, 'children': [
                     {'title': 'is Multiaxes:', 'name': 'ismultiaxes', 'type': 'bool', 'value': is_multiaxes,
                      'default': False},
                     {'title': 'Status:', 'name': 'multi_status', 'type': 'list',
                      'value': 'Master' if master else 'Slave', 'limits': ['Master', 'Slave']},
                     {'title': 'Axis:', 'name': 'axis', 'type': 'list', 'limits': axis_names},
                 ]},
             ] + comon_parameters(epsilon)
    return params


params = [
    {'title': 'Main Settings:', 'name': 'main_settings', 'type': 'group', 'children': [
        {'title': 'Actuator type:', 'name': 'move_type', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Actuator name:', 'name': 'module_name', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Plugin Config:', 'name': 'plugin_config', 'type': 'bool_push', 'label': 'Show Config', },
        {'title': 'Controller ID:', 'name': 'controller_ID', 'type': 'int', 'value': 0, 'default': 0},
        {'title': 'Refresh value (ms):', 'name': 'refresh_timeout', 'type': 'int',
            'value': config('actuator', 'refresh_timeout_ms')},
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
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pathlib import Path
    app = QtWidgets.QApplication(sys.argv)
    if config('style', 'darkstyle'):
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet())

    widget = QtWidgets.QWidget()
    prog = DAQ_Move(widget, title=title,)
    widget.show()
    prog.actuator = Path(plugin_file).stem[9:]
    if init:
        prog.init_hardware_ui()

    sys.exit(app.exec_())


class DAQ_Move_base(QObject):
    """ The base class to be inherited by all actuator modules

    This base class implements all necessary parameters and methods for the plugin to communicate with its parent (the
    DAQ_Move module)

    Parameters
    ----------
    parent : DAQ_Move_Hardware
    params_state : Parameter
            pyqtgraph Parameter instance from which the module will get the initial settings (as defined in the preset)
    Attributes
    ----------
    move_done_signal: Signal
        signal represented by a float. Is emitted each time the hardware reached the target position within the epsilon
        precision (see comon_parameters variable)
    controller: object
        the object representing the hardware in the plugin. Used to access hardware functionality
    settings: Parameter
        instance representing the hardware settings defined from the params attribute. Modifications on the GUI settings
         will be transferred to this attribute. It stores at all times the current state of the hardware/plugin settings
    params: List of dict used to create a Parameter object.
        Its definition on the class level enable the automatic update of the GUI settings when changing plugins
        (even in managers mode creation). To be populated on the plugin level as the base class does't represents a
        real hardware
    is_multiaxes: bool
        class level attribute. Defines if the plugin controller controls multiple axes. If True, one has to define
        a Master instance of this plugin and slave instances of this plugin (all sharing the same controller_ID
        parameter)
    current_value: DataActuator
        stores the current position after each call to the get_actuator_value in the plugin
    target_value: DataActuator
        stores the target position the controller should reach within epsilon
    """

    move_done_signal = Signal(DataActuator)
    is_multiaxes = False
    stage_names = []
    params = []
    _controller_units = ''
    _epsilon = 1
    data_actuator_type = DataActuatorType['float']
    data_shape = (1, )  # expected shape of the underlying actuator's value (in general a float so shape = (1, ))

    def __init__(self, parent: 'DAQ_Move_Hardware' = None, params_state: dict = None):
        QObject.__init__(self)  # to make sure this is the parent class
        self.move_is_done = False
        self.parent = parent
        self.stage = None
        self.status = edict(info="", controller=None, stage=None, initialized=False)

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
        # self.settings.child('multiaxes',
        #                     'axis').sigLimitsChanged.connect(lambda param,
        #                                                             limits: self.send_param_status(
        #    param, [(param, 'limits', None)]))
        if parent is not None:
            self._title = parent.title
        else:
            self._title = "myactuator"
        self._current_value = DataActuator(self._title, data=[np.zeros(self.data_shape, dtype=float)])
        self._target_value = DataActuator(self._title, data=[np.zeros(self.data_shape, dtype=float)])
        self.controller_units = self._controller_units

        self.poll_timer = QTimer()
        self.poll_timer.setInterval(config('actuator', 'polling_interval_ms'))
        self._poll_timeout = config('actuator', 'polling_timeout_s')
        self.poll_timer.timeout.connect(self.check_target_reached)

        self.ini_attributes()

    @property
    def axis_name(self) -> Union[str, object]:
        """Get/Set the current axis using its string identifier"""
        limits = self.settings.child('multiaxes', 'axis').opts['limits']
        if isinstance(limits, list):
            return self.settings['multiaxes', 'axis']
        elif isinstance(limits, dict):
            return find_keys_from_val(limits, val=self.settings['multiaxes', 'axis'])[0]

    @axis_name.setter
    def axis_name(self, name: str):
        limits = self.settings.child('multiaxes', 'axis').opts['limits']
        if name in limits:
            if isinstance(limits, list):
                self.settings.child('multiaxes', 'axis').setValue(name)
            elif isinstance(limits, dict):
                self.settings.child('multiaxes', 'axis').setValue(limits[name])
            QtWidgets.QApplication.processEvents()

    @property
    def axis_names(self) -> Union[List, Dict]:
        """ Get/Set the names of all axes controlled by this instrument plugin

        Returns
        -------
        List of string or dictionary mapping names to integers
        """
        return self.settings.child('multiaxes', 'axis').opts['limits']

    @axis_names.setter
    def axis_names(self, names: Union[List, Dict]):
        self.settings.child('multiaxes', 'axis').setLimits(names)
        QtWidgets.QApplication.processEvents()

    @property
    def axis_value(self) -> object:
        """Get the current value selected from the current axis"""
        return self.settings['multiaxes', 'axis']

    def ini_attributes(self):
        """ To be subclassed, in order to init specific attributes needed by the real implementation"""
        self.controller = None

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
    def current_value(self):
        if self.data_actuator_type.name == 'float':
            return self._current_value.value()
        else:
            return self._current_value

    @current_value.setter
    def current_value(self, value: Union[float, DataActuator]):
        if not isinstance(value, DataActuator):
            self._current_value = DataActuator(self._title, data=value)
        else:
            self._current_value = value

    @property
    def target_value(self):
        if self.data_actuator_type.name == 'float':
            return self._target_value.value()
        else:
            return self._target_value

    @target_value.setter
    def target_value(self, value: Union[float, DataActuator]):
        if not isinstance(value, DataActuator):
            self._target_value = DataActuator(self._title, data=value)
        else:
            self._target_value = value

    @property
    def current_position(self):
        deprecation_msg('current_position attribute should not be used, use current_value')
        return self.current_value

    @current_position.setter
    def current_position(self, value):
        self.current_value = value

    @property
    def target_position(self):
        deprecation_msg('target_position attribute should not be used, use target_value')
        return self.target_value

    @target_position.setter
    def target_position(self, value):
        self.target_value = value

    @property
    def controller_units(self):
        """ Get/Set the units of this plugin"""
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
        """ Get/Set the polling status"""
        return self._ispolling

    @ispolling.setter
    def ispolling(self, polling=True):
        self._ispolling = polling

    def check_bound(self, position: DataActuator) -> DataActuator:
        """ Check if the current position is within the software bounds

        Return the new position eventually coerced within the bounds
        """
        if self.settings.child('bounds', 'is_bounds').value():
            if position > self.settings.child('bounds', 'max_bound').value():
                position = DataActuator(self._title, data=self.settings.child('bounds', 'max_bound').value())
                self.emit_status(ThreadCommand('outofbounds', []))
            elif position < self.settings.child('bounds', 'min_bound').value():
                position = DataActuator(self._title, data=self.settings.child('bounds', 'min_bound').value())
                self.emit_status(ThreadCommand('outofbounds', []))
        return position

    def get_actuator_value(self):
        if hasattr(self, 'check_position'):
            deprecation_msg('check_position method in plugins is deprecated, use get_actuator_value',3)
            return self.check_position()
        else:
            raise NotImplementedError

    def move_abs(self, value: Union[float, DataActuator]):
        if hasattr(self, 'move_Abs'):
            deprecation_msg('move_Abs method in plugins is deprecated, use move_abs', 3)
            self.move_Abs(value)
        else:
            raise NotImplementedError

    def move_rel(self, value: Union[float, DataActuator]):
        if hasattr(self, 'move_Rel'):
            deprecation_msg('move_Rel method in plugins is deprecated, use move_rel', 3)
            self.move_Rel(value)
        else:
            raise NotImplementedError

    def move_home(self, value: Union[float, DataActuator]):
        if hasattr(self, 'move_Home'):
            deprecation_msg('move_Home method in plugins is deprecated, use move_home', 3)
            self.move_Home()
        else:
            raise NotImplementedError

    def emit_status(self, status: ThreadCommand):
        """ Emit the status_sig signal with the given status ThreadCommand back to the main GUI.
        """
        if self.parent is not None:
            self.parent.status_sig.emit(status)
            QtWidgets.QApplication.processEvents()
        else:
            print(status)

    def emit_value(self, pos: DataActuator):
        """Convenience method to emit the current actuator value back to the UI"""

        self.emit_status(ThreadCommand('get_actuator_value', [pos]))

    def commit_settings(self, param: Parameter):
        """
          to subclass to transfer parameters to hardware
        """

    def commit_common_settings(self, param):
        pass

    def move_done(self, position: DataActuator = None):  # the position argument is just there to match some signature of child classes
        """
            | Emit a move done signal transmitting the float position to hardware.
            | The position argument is just there to match some signature of child classes.

            =============== ========== =============================================================================
             **Arguments**   **Type**  **Description**
             *position*      float     The position argument is just there to match some signature of child classes
            =============== ========== =============================================================================

        """
        if position is None:
            if self.data_actuator_type.name == 'float':
                position = DataActuator(self._title, data=self.get_actuator_value())
            else:
                position = self.get_actuator_value()
        if position.name != self._title:  # make sure the emitted DataActuator has the name of the real implementation
            #of the plugin
            position = DataActuator(self._title, data=position.value())
        self.move_done_signal.emit(position)
        self.move_is_done = True

    def poll_moving(self):
        """ Poll the current moving. In case of timeout emit the raise timeout Thread command.

        See Also
        --------
        DAQ_utils.ThreadCommand, move_done
        """
        if 'TCPServer' not in self.__class__.__name__:
            self.start_time = perf_counter()
            if self.ispolling:
                self.poll_timer.start()
            else:
                if self.data_actuator_type.name == 'float':
                    self._current_value = DataActuator(data=self.get_actuator_value())
                else:
                    self._current_value = self.get_actuator_value()
                logger.debug(f'Current position: {self._current_value}')
                self.move_done(self._current_value)

    def check_target_reached(self):
        # if not isinstance(self._current_value, DataActuator):
        #     self._current_value = DataActuator(data=self._current_value)
        # if not isinstance(self._target_value, DataActuator):
        #     self._target_value = DataActuator(data=self._target_value)

        logger.debug(f"epsilon value is {self.settings['epsilon']}")
        logger.debug(f"current_value value is {self._current_value}")
        logger.debug(f"target_value value is {self._target_value}")

        if not (self._current_value - self._target_value).abs() < self.settings['epsilon']:

            logger.debug(f'Check move_is_done: {self.move_is_done}')
            if self.move_is_done:
                self.emit_status(ThreadCommand('Move has been stopped', ))
                logger.info(f'Move has been stopped')
            self.current_value = self.get_actuator_value()

            self.emit_value(self._current_value)
            logger.debug(f'Current value: {self._current_value}')

            if perf_counter() - self.start_time >= self.settings['timeout']:
                self.poll_timer.stop()
                self.emit_status(ThreadCommand('raise_timeout', ))
                logger.info(f'Timeout activated')
        else:
            self.poll_timer.stop()
            logger.debug(f'Current value: {self._current_value}')
            self.move_done(self._current_value)

    def send_param_status(self, param, changes):
        """ Send changes value updates to the gui to update consequently the User Interface

        The message passing is made via the ThreadCommand "update_settings".
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
            elif change == 'limits':
                self.emit_status(ThreadCommand('update_settings', [self.parent_parameters_path + path, data,
                                                                   change]))

    def get_position_with_scaling(self, pos: DataActuator) -> DataActuator:
        """ Get the current position from the hardware with scaling conversion.
        """
        if self.settings['scaling', 'use_scaling']:
            pos = (pos - self.settings['scaling', 'offset']) * self.settings['scaling', 'scaling']
        return pos

    def set_position_with_scaling(self, pos: DataActuator) -> DataActuator:
        """ Set the current position from the parameter and hardware with scaling conversion.
        """
        if self.settings['scaling', 'use_scaling']:
            pos = pos / self.settings['scaling', 'scaling'] + self.settings['scaling', 'offset']
        return pos

    def set_position_relative_with_scaling(self, pos: DataActuator) -> DataActuator:
        """ Set the scaled positions in case of relative moves
        """
        if self.settings['scaling', 'use_scaling']:
            pos = pos / self.settings['scaling', 'scaling']
        return pos

    @Slot(edict)
    def update_settings(self, settings_parameter_dict):  # settings_parameter_dict=edict(path=path,param=param)
        """ Receive the settings_parameter signal from the param_tree_changed method and make hardware updates of
        modified values.
        """
        path = settings_parameter_dict['path']
        param = settings_parameter_dict['param']
        change = settings_parameter_dict['change']
        apply_settings = True
        try:
            self.settings.sigTreeStateChanged.disconnect(self.send_param_status)
        except Exception:
            pass
        if change == 'value':
            self.settings.child(*path[1:]).setValue(param.value())  # blocks signal back to main UI
        elif change == 'childAdded':
            try:
                child = Parameter.create(name='tmp')
                child.restoreState(param)
                param = child
                self.settings.child(*path[1:]).addChild(child)  # blocks signal back to main UI
            except ValueError:
                apply_settings = False
        elif change == 'parent':
            children = putils.get_param_from_name(self.settings, param.name())

            if children is not None:
                path = putils.get_param_path(children)
                self.settings.child(*path[1:-1]).removeChild(children)

        self.settings.sigTreeStateChanged.connect(self.send_param_status)
        if apply_settings:
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
    data_actuator_type = DataActuatorType['DataActuator']

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
        DAQ_Move_base.__init__(self, parent, params_state)  # initialize base class with commom attribute and methods
        self.settings.child('bounds').hide()
        self.settings.child('scaling').hide()
        self.settings.child('epsilon').setValue(1)

        TCPServer.__init__(self, self.client_type)

    def command_to_from_client(self, command):
        sock: Socket = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client 'ACTUATOR' is connected then send it the command

            if command == 'position_is':
                pos = DeSerializer(sock).dwa_deserialization()

                pos = self.get_position_with_scaling(pos)
                self._current_value = pos
                self.emit_status(ThreadCommand('get_actuator_value', [pos]))

            elif command == 'move_done':
                pos = DeSerializer(sock).dwa_deserialization()
                pos = self.get_position_with_scaling(pos)
                self._current_value = pos
                self.emit_status(ThreadCommand('move_done', [pos]))
            else:
                self.send_command(sock, command)

    def commit_settings(self, param):

        if param.name() in putils.iter_children(self.settings.child('settings_client'), []):
            actuator_socket: Socket = [client['socket'] for client in self.connected_clients if client['type'] == 'ACTUATOR'][0]
            actuator_socket.check_sended_with_serializer('set_info')
            path = putils.get_param_path(param)[2:]
            # get the path of this param as a list starting at parent 'infos'

            actuator_socket.check_sended_with_serializer(path)

            # send value
            data = ioxml.parameter_to_xml_string(param)
            actuator_socket.check_sended_with_serializer(data)

    def ini_stage(self, controller=None):
        """
            | Initialisation procedure of the detector updating the status dictionnary.
            |
            | Init axes from image , here returns only None values (to tricky to di it with the server and not really necessary for images anyway)

            See Also
            --------
            utility_classes.DAQ_TCP_server.init_server, get_xaxis, get_yaxis
        """
        self.settings.child('infos').addChildren(self.params_client)

        self.init_server()
        self.controller = self.serversocket
        self.settings.child('units').hide()
        self.settings.child('epsilon').hide()

        info = 'TCP Server actuator'
        initialized = True
        return info, initialized

    def close(self):
        """
            Should be used to uninitialize hardware.

            See Also
            --------
            utility_classes.DAQ_TCP_server.close_server
        """
        self.listening = False
        self.close_server()

    def move_abs(self, position: DataActuator):
        """

        """
        position = self.check_bound(position)
        self.target_value = position

        position = self.set_position_with_scaling(position)

        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client self.client_type is connected then send it the command
            sock.check_sended_with_serializer('move_abs')
            sock.check_sended_with_serializer(position)

    def move_rel(self, position: DataActuator):
        position = self.check_bound(self.current_value + position) - self.current_value
        self.target_value = position + self.current_value

        position = self.set_position_relative_with_scaling(position)
        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client self.client_type is connected then send it the command
            sock.check_sended_with_serializer('move_rel')
            sock.check_sended_with_serializer(position)

    def move_home(self):
        """
            Make the absolute move to original position (0).

            See Also
            --------
            move_Abs
        """
        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client self.client_type is connected then send it the command
            sock.check_sended_with_serializer('move_home')

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

        return self._current_value

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

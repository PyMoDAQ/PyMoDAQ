# -*- coding: utf-8 -*-
"""
Created the 29/07/2022

@author: Sebastien Weber
"""
import sys

from qtpy.QtCore import QObject, Signal, QThread, Slot, Qt, QTimer
from qtpy import QtWidgets

from easydict import EasyDict as edict

from pymodaq.utils.logger import set_logger, get_module_name, get_module_name
from pymodaq.control_modules.utils import ControlModule
from pymodaq.utils.parameter import ioxml
from pymodaq.control_modules.daq_move_ui import DAQ_Move_UI, ThreadCommand
from pymodaq.utils.managers.parameter_manager import ParameterManager, Parameter
from pymodaq.control_modules.move_utility_classes import MoveCommand
from pymodaq.utils.tcp_server_client import TCPClient
from pymodaq.control_modules.move_utility_classes import params as daq_move_params
from pymodaq.utils import daq_utils as utils
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.gui_utils import get_splash_sc
from pymodaq.utils import config
from pymodaq.utils.exceptions import ActuatorError
from pymodaq.utils.messenger import deprecation_msg
from pymodaq.utils.h5modules import module_saving


local_path = config.get_set_local_dir()
sys.path.append(local_path)
logger = set_logger(get_module_name(__file__))
DAQ_Move_Actuators = utils.get_plugins('daq_move')
ACTUATOR_TYPES = [mov['name'] for mov in DAQ_Move_Actuators]

STATUS_WAIT_TIME = 1000


class DAQ_Move(ParameterManager, ControlModule):
    """ Main PyMoDAQ class to drive actuators

    Qt object and generic UI to drive actuators.

    Attributes
    ----------
    init_signal: Signal[bool]
        This signal is emitted when the chosen actuator is correctly initialized
    move_done_signal: Signal[str, float]
        This signal is emitted when the chosen actuator finished its action. It gives the actuator's name and current
        value
    bounds_signal: Signal[bool]
        This signal is emitted when the actuator reached defined limited boundaries.

    See Also
    --------
    :class:`ControlModule`, :class:`ParameterManager`
    """
    settings_name = 'daq_move_settings'

    move_done_signal = Signal(str, float)
    _current_value_signal = Signal(str, float)
    # to be used in external program to make sure the move has been done,
    # export the current position. str refer to the unique title given to the module
    _update_settings_signal = Signal(edict)
    bounds_signal = Signal(bool)

    
    params = daq_move_params

    def __init__(self, parent=None, title="DAQ Move"):
        """

        Parameters
        ----------
        parent: QWidget or None
        parent: QWidget or None
            if it is a valid QWidget, it will hold the user interface to drive it
        title: str
            The unique (should be unique) string identifier for the underlying actuator
        """

        self.logger = set_logger(f'{logger.name}.{title}')
        self.logger.info(f'Initializing DAQ_Move: {title}')

        QObject.__init__(self)
        ParameterManager.__init__(self)
        ControlModule.__init__(self)

        self.parent = parent
        if parent is not None:
            self.ui = DAQ_Move_UI(parent, title)
        else:
            self.ui = None

        if self.ui is not None:
            self.ui.actuators = ACTUATOR_TYPES
            self.ui.set_settings_tree(self.settings_tree)
            self.ui.command_sig.connect(self.process_ui_cmds)

        self.splash_sc = get_splash_sc()
        self._title = title
        if len(ACTUATOR_TYPES) > 0:  # will be 0 if no valid plugins are installed
            self.actuator = ACTUATOR_TYPES[0]

        self.module_and_data_saver = module_saving.ActuatorSaver(self)

        self._move_done_bool = True

        self._current_value = 0.
        self._target_value = 0.
        self._relative_value = 0.

        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self.get_actuator_value)

    def process_ui_cmds(self, cmd: utils.ThreadCommand):
        """Process commands sent by actions done in the ui

        Parameters
        ----------
        cmd: ThreadCommand
            Possible values are :
            * init
            * quit
            * get_value
            * loop_get_value
            * find_home
            * stop
            * move_abs
            * move_rel
            * show_log
            * actuator_changed
            * rel_value
        """
        if cmd.command == 'init':
            self.init_hardware(cmd.attribute[0])
        elif cmd.command == 'quit':
            self.quit_fun()
        elif cmd.command == 'get_value':
            self.get_actuator_value()
        elif cmd.command == 'loop_get_value':
            self.get_continuous_actuator_value(cmd.attribute)
        elif cmd.command == 'find_home':
            self.move_home()
        elif cmd.command == 'stop':
            self.stop_motion()
        elif cmd.command == 'move_abs':
            self.move_abs(cmd.attribute)
        elif cmd.command == 'move_rel':
            self.move_rel(cmd.attribute)
        elif cmd.command == 'show_log':
            self.show_log()
        elif cmd.command == 'actuator_changed':
            self.actuator = cmd.attribute
        elif cmd.command == 'rel_value':
            self._relative_value = cmd.attribute


    def stop_motion(self):
        """Stop any motion
        """
        try:
            self.command_hardware.emit(ThreadCommand(command="stop_motion"))
        except Exception as e:
            self.logger.exception(str(e))

    def move(self, move_command: MoveCommand):
        """Generic method to trigger the correct action on the actuator

        Parameters
        ----------
        move_command: MoveCommand
            MoveCommand with move_type attribute either:
            * 'abs': performs an absolute action
            * 'rel': performs a relative action
            * 'home': find the actuator's home

        See Also
        --------
        :meth:`move_abs`, :meth:`move_rel`, :meth:`move_home`, :class:`..utility_classes.MoveCommand`

        """
        if move_command.move_type == 'abs':
            self.move_abs(move_command.value)
        elif move_command.move_type == 'rel':
            self.move_rel(move_command.value)
        elif move_command.move_type == 'home':
            self.move_home(move_command.value)

    def move_Abs(self, value, send_to_tcpip=False):
        deprecation_msg(f'The method *move_Abs* should not be used anymore, use *move_abs*')
        self.move_abs(value, send_to_tcpip=send_to_tcpip)

    def move_abs(self, value, send_to_tcpip=False):
        """Move the connected hardware to the absolute value

        Returns nothing but the move_done_signal will be send once the action is done

        Parameters
        ----------
        value: float
            The value the actuator should reach
        send_to_tcpip: bool
            if True, this position is send through the TCP/IP communication canal
        """
        try:
            self._send_to_tcpip = send_to_tcpip
            if not value == self._current_value:
                if self.ui is not None:
                    self.ui.move_done = False
                self._move_done_bool = False
                self._target_value = value
                self.update_status("Moving")
                self.command_hardware.emit(ThreadCommand(command="reset_stop_motion"))
                self.command_hardware.emit(ThreadCommand(command="move_abs", attribute=[value]))

        except Exception as e:
            self.logger.exception(str(e))

    def move_Home(self, send_to_tcpip=False):
        self.move_home(send_to_tcpip)
        deprecation_msg(f'The method *move_Home* is deprecated, use *move_home*')

    def move_home(self, send_to_tcpip=False):
        """Move the connected actuator to its home value (if any)

        Parameters
        ----------
        send_to_tcpip: bool
            if True, this position is send through the TCP/IP communication canal
        """
        self._send_to_tcpip = send_to_tcpip
        try:
            if self.ui is not None:
                self.ui.move_done = False
            self._move_done_bool = False
            self.update_status("Moving")
            self.command_hardware.emit(ThreadCommand(command="reset_stop_motion"))
            self.command_hardware.emit(ThreadCommand(command="move_Home"))

        except Exception as e:
            self.logger.exception(str(e))

    def move_Rel(self, rel_value, send_to_tcpip=False):
        deprecation_msg(f'The method *move_Rel* should not be used anymore, use *move_rel*')
        self.move_rel(rel_value, send_to_tcpip=send_to_tcpip)

    def move_rel(self, rel_value, send_to_tcpip=False):
        """Move the connected hardware to the relative value

        Returns nothing but the move_done_signal will be send once the action is done

        Parameters
        ----------
        value: float
            The relative value the actuator should reach
        send_to_tcpip: bool
            if True, this position is send through the TCP/IP communication canal
        """

        try:
            self._send_to_tcpip = send_to_tcpip
            if self.ui is not None:
                self.ui.move_done = False
            self._move_done_bool = False
            self._target_value = self._current_value + rel_value
            self.update_status("Moving")
            self.command_hardware.emit(ThreadCommand(command="reset_stop_motion"))
            self.command_hardware.emit(ThreadCommand(command="move_rel", attribute=[rel_value]))

        except Exception as e:
            self.logger.exception(str(e))

    def move_Rel_p(self):
        deprecation_msg(f'The method *move_Rel_p* should not be used anymore, use *move_rel_p*')
        self.move_rel_p()

    def move_Rel_m(self):
        deprecation_msg(f'The method *move_Rel_m* should not be used anymore, use *move_rel_m*')
        self.move_rel_m()

    def move_rel_p(self):
        self.move_rel(self._relative_value)

    def move_rel_m(self):
        self.move_rel(-self._relative_value)

    def quit_fun(self):
        """Programmatic quitting of the current instance of DAQ_Move

        Des-init the actuator then close the UI parent widget
        """
        # insert anything that needs to be closed before leaving

        if self._initialized_state:
            self.init_hardware(False)
        if self.ui is not None:
            self.ui.get_action('quit').trigger()
        self.quit_signal.emit()

    def ini_stage_fun(self):
        deprecation_msg(f'The function *ini_stage_fun* is deprecated, use init_hardware')
        self.init_hardware(True)

    def init_hardware_ui(self, do_init=True):
        """Programmatic actuator's Initialization

        Programmatic way to simulate a click on the init button of the UI to initialize the communication with the
        hardware

        Parameters
        ----------
        do_init: bool
            if the init or des-init should be performed
        """
        self.ui.do_init(do_init)

    def init_hardware(self, do_init=True):

        if not do_init:
            try:
                self.command_hardware.emit(ThreadCommand(command="close"))
                if self.ui is not None:
                    self.ui.actuator_init = False
            except Exception as e:
                self.logger.exception(str(e))
        else:
            try:
                hardware = DAQ_Move_Hardware(self._actuator_type, self._current_value, self._title)
                self._hardware_thread = QThread()
                hardware.moveToThread(self._hardware_thread)

                self.command_hardware[ThreadCommand].connect(hardware.queue_command)
                hardware.status_sig[ThreadCommand].connect(self.thread_status)
                self._update_settings_signal[edict].connect(hardware.update_settings)

                self._hardware_thread.hardware = hardware
                self._hardware_thread.start()
                self.command_hardware.emit(
                    ThreadCommand(command="ini_stage", attribute=[self.settings.child(('move_settings')).saveState(),
                                                                  self.controller]))
            except Exception as e:
                self.logger.exception(str(e))

    @property
    def initialized_state(self):
        """bool: status of the actuator's initialization (init or not)"""
        return self._initialized_state

    @property
    def move_done_bool(self):
        """bool: status of the actuator's action (done or not)"""
        return self._move_done_bool

    def value_changed(self, param):
        if param.name() == 'connect_server':
            if param.value():
                self.connect_tcp_ip()
            else:
                self._command_tcpip.emit(ThreadCommand('quit', ))

        elif param.name() == 'ip_address' or param.name == 'port':
            self._command_tcpip.emit(
                ThreadCommand('update_connection', dict(ipaddress=self.settings.child('main_settings', 'tcpip',
                                                                                      'ip_address').value(),
                                                        port=self.settings.child('main_settings', 'tcpip',
                                                                                 'port').value())))
        elif param.name() == 'refresh_timeout':
            self._refresh_timer.setInterval(param.value())

        path = self.settings.childPath(param)
        if path is not None:
            if 'main_settings' not in path:
                self._update_settings_signal.emit(edict(path=path, param=param, change='value'))
                if self.settings.child('main_settings', 'tcpip', 'tcp_connected').value():
                    self._command_tcpip.emit(ThreadCommand('send_info', dict(path=path, param=param)))

    def param_deleted(self, param):
        if param.name() not in putils.iter_children(self.settings.child('main_settings'), []):
            self._update_settings_signal.emit(edict(path=['move_settings'], param=param, change='parent'))

    def child_added(self, param, data):
        path = self.settings.childPath(param)
        if 'main_settings' not in path:
            self._update_settings_signal.emit(edict(path=path, param=data[0].saveState(), change='childAdded'))

    @Slot()
    def raise_timeout(self):
        """Update status with "Timeout occurred" statement and change the timeout flag.
        """
        self.update_status("Timeout occurred")
        self.wait_position_flag = False

    @Slot(ThreadCommand)
    def thread_status(self, status):  # general function to get datas/infos from all threads back to the main
        """
            | General function to get datas/infos from all threads back to the main0
            |

            Interpret a command from the command given by the ThreadCommand status :
                * In case of **'Update_status'** command, call the update_status method with status attribute as parameters
                * In case of **'ini_stage'** command, initialise a Stage from status attribute
                * In case of **'close'** command, close the launched stage thread
                * In case of **'check_position'** command, set the current_value value from status attribute
                * In case of **'move_done'** command, set the current_value value, make profile of move_done and send the move done signal with status attribute
                * In case of **'Move_Not_Done'** command, set the current position value from the status attribute, make profile of Not_move_done and send the Thread Command "move_abs"
                * In case of **'update_settings'** command, create child "Move Settings" from  status attribute (if possible)

            ================ ================= ======================================================
            **Parameters**     **Type**         **Description**

            *status*          ThreadCommand()   instance of ThreadCommand containing two attribute :

                                                 * *command*    str
                                                 * *attribute* list

            ================ ================= ======================================================

            See Also
            --------
            update_status, set_enabled_move_buttons, get_actuator_value, DAQ_utils.ThreadCommand, parameter_tree_changed, raise_timeout
        """

        if status.command == "Update_Status":
            if len(status.attribute) > 2:
                self.update_status(status.attribute[0], log=status.attribute[1])
            else:
                self.update_status(status.attribute[0])

        elif status.command == "ini_stage":
            # status.attribute[0]=edict(initialized=bool,info="", controller=)
            self.update_status("Stage initialized: {:} info: {:}".format(status.attribute[0]['initialized'],
                                                                         status.attribute[0]['info']))
            if status.attribute[0]['initialized']:
                self.controller = status.attribute[0]['controller']
                if self.ui is not None:
                    self.ui.actuator_init = True
                self._initialized_state = True
            else:
                self._initialized_state = False
            if self._initialized_state:
                self.get_actuator_value()
            self.init_signal.emit(self._initialized_state)

        elif status.command == "close":
            try:
                self.update_status(status.attribute[0])
                self._hardware_thread.exit()
                self._hardware_thread.wait()
                finished = self._hardware_thread.isFinished()
                if finished:
                    pass
                    delattr(self, 'hardware_thread')
                else:
                    self.update_status('thread is locked?!', STATUS_WAIT_TIME, 'log')
            except Exception as e:
                self.logger.exception(str(e))
            self._initialized_state = False
            self.init_signal.emit(self._initialized_state)

        elif status.command == "get_actuator_value" or status.command == 'check_position':
            if self.ui is not None:
                self.ui.display_value(status.attribute[0])
            self._current_value = status.attribute[0]
            self._current_value_signal.emit(self.title, self._current_value)
            if self.settings.child('main_settings', 'tcpip', 'tcp_connected').value() and self._send_to_tcpip:
                self._command_tcpip.emit(ThreadCommand('position_is', status.attribute))

        elif status.command == "move_done":
            if self.ui is not None:
                self.ui.display_value(status.attribute[0])
                self.ui.move_done = True
            self._current_value = status.attribute[0]
            self._move_done_bool = True
            self.move_done_signal.emit(self._title, status.attribute[0])
            if self.settings.child('main_settings', 'tcpip', 'tcp_connected').value() and self._send_to_tcpip:
                self._command_tcpip.emit(ThreadCommand('move_done', status.attribute))

        elif status.command == "Move_Not_Done":
            if self.ui is not None:
                self.ui.display_value(status.attribute[0])
                self.ui.move_done = False

            self._current_value = status.attribute[0]
            self._move_done_bool = False
            self.command_hardware.emit(ThreadCommand(command="move_abs", attribute=[self._target_value]))

        elif status.command == 'update_main_settings':
            # this is a way for the plugins to update main settings of the ui (solely values, limits and options)
            try:
                if status.attribute[2] == 'value':
                    self.settings.child('main_settings', *status.attribute[0]).setValue(status.attribute[1])
                elif status.attribute[2] == 'limits':
                    self.settings.child('main_settings', *status.attribute[0]).setLimits(status.attribute[1])
                elif status.attribute[2] == 'options':
                    self.settings.child('main_settings', *status.attribute[0]).setOpts(**status.attribute[1])
            except Exception as e:
                self.logger.exception(str(e))

        elif status.command == 'update_settings':
            # ThreadCommand(command='update_settings',attribute=[path,data,change]))
            try:
                self.settings.sigTreeStateChanged.disconnect(
                    self.parameter_tree_changed)  # any changes on the settings will update accordingly the detector
            except Exception:
                pass
            try:
                if status.attribute[2] == 'value':
                    self.settings.child('move_settings', *status.attribute[0]).setValue(status.attribute[1])
                elif status.attribute[2] == 'limits':
                    self.settings.child('move_settings', *status.attribute[0]).setLimits(status.attribute[1])
                elif status.attribute[2] == 'options':
                    self.settings.child('move_settings', *status.attribute[0]).setOpts(**status.attribute[1])
                elif status.attribute[2] == 'childAdded':
                    child = Parameter.create(name='tmp')
                    child.restoreState(status.attribute[1][0])
                    self.settings.child('move_settings', *status.attribute[0]).addChild(status.attribute[1][0])

            except Exception as e:
                self.logger.exception(str(e))
            self.settings.sigTreeStateChanged.connect(
                self.parameter_tree_changed)  # any changes on the settings will update accordingly the detector

        elif status.command == 'raise_timeout':
            self.raise_timeout()

        elif status.command == 'outofbounds':
            self.bounds_signal.emit(True)

        elif status.command == 'show_splash':
            self.settings_tree.setEnabled(False)
            self.splash_sc.show()
            self.splash_sc.raise_()
            self.splash_sc.showMessage(status.attribute[0], color=Qt.white)

        elif status.command == 'close_splash':
            self.splash_sc.close()
            self.settings_tree.setEnabled(True)

        elif status.command == 'set_allowed_values':
            if self.ui is not None:
                self.ui.set_spinbox_properties(**status.attribute)

    def get_position(self):
        deprecation_msg(f'This method is deprecated , please use `get_actuator_value`')
        self.get_actuator_value()

    def get_actuator_value(self):
        """Get the current actuator value via the "get_actuator_value" command send to the hardware

        Returns nothing but the  `move_done_signal` will be send once the action is done
        """
        try:
            self.command_hardware.emit(ThreadCommand(command="get_actuator_value"))

        except Exception as e:
            self.logger.exception(str(e))

    def grab(self):
        if self.ui is not None:
            self.manage_ui_actions('refresh_value', 'setChecked', 'False')
        self.get_continuous_actuator_value(False)

    def stop_grab(self):
        """Stop value polling. Mandatory

        First uncheck the ui action if ui is not None, then stop the polling
        """
        if self.ui is not None:
            self.manage_ui_actions('refresh_value', 'setChecked', 'False')
        self.get_continuous_actuator_value(False)

    def get_continuous_actuator_value(self, get_value=True):
        """Start the continuous getting of the actuator's value

        Parameters
        ----------
        get_value: bool
            if True start the timer to periodically fetch the actuator's value, else stop it

        Notes
        -----
        The current timer period is set by the refresh value *'refresh_timeout'* in the actuator main settings.
        """
        if get_value:
            self._refresh_timer.setInterval(self.settings['main_settings', 'refresh_timeout'])
            self._refresh_timer.start()
        else:
            self._refresh_timer.stop()

    @property
    def actuator(self):
        """str: the selected actuator's type

        Returns
        -------

        """
        return self._actuator_type

    @actuator.setter
    def actuator(self, act_type):
        if act_type in ACTUATOR_TYPES:
            self._actuator_type = act_type
            if self.ui is not None:
                self.ui.actuator = act_type
                self.update_settings()
        else:
            raise ActuatorError(f'{act_type} is an invalid actuator, should be within {ACTUATOR_TYPES}')

    @property
    def units(self):
        return self.settings['move_settings', 'units']

    def update_settings(self):

        self.settings.child('main_settings', 'move_type').setValue(self._actuator_type)
        self.settings.child('main_settings', 'module_name').setValue(self._title)
        try:
            for child in self.settings.child('move_settings').children():
                child.remove()
            parent_module = utils.find_dict_in_list_from_key_val(DAQ_Move_Actuators, 'name', self._actuator_type)
            class_ = getattr(getattr(parent_module['module'], 'daq_move_' + self._actuator_type),
                             'DAQ_Move_' + self._actuator_type)
            params = getattr(class_, 'params')
            move_params = Parameter.create(name='move_settings', type='group', children=params)

            self.settings.child('move_settings').addChildren(move_params.children())

        except Exception as e:
            self.logger.exception(str(e))

    def connect_tcp_ip(self):
        if self.settings.child('main_settings', 'tcpip', 'connect_server').value():
            self._tcpclient_thread = QThread()

            tcpclient = TCPClient(self.settings.child('main_settings', 'tcpip', 'ip_address').value(),
                                  self.settings.child('main_settings', 'tcpip', 'port').value(),
                                  self.settings.child('move_settings'), client_type="ACTUATOR")
            tcpclient.moveToThread(self._tcpclient_thread)
            self._tcpclient_thread.tcpclient = tcpclient
            tcpclient.cmd_signal.connect(self.process_tcpip_cmds)

            self._command_tcpip[ThreadCommand].connect(tcpclient.queue_command)

            self._tcpclient_thread.start()
            tcpclient.init_connection()

    @Slot(ThreadCommand)
    def process_tcpip_cmds(self, status):
        if 'move_abs' in status.command:
            self.move_abs(status.attribute[0], send_to_tcpip=True)

        elif 'move_rel' in status.command:
            self.move_rel(status.attribute[0], send_to_tcpip=True)

        elif 'move_home' in status.command:
            self.move_home(send_to_tcpip=True)

        elif 'check_position' in status.command:
            deprecation_msg('check_position is deprecated, you should use get_actuator_value')
            self._send_to_tcpip = True
            self.command_hardware.emit(ThreadCommand('get_actuator_value', ))

        elif 'get_actuator_value' in status.command:
            self._send_to_tcpip = True
            self.command_hardware.emit(ThreadCommand('get_actuator_value', ))

        elif status.command == 'connected':
            self.settings.child('main_settings', 'tcpip', 'tcp_connected').setValue(True)

        elif status.command == 'disconnected':
            self.settings.child('main_settings', 'tcpip', 'tcp_connected').setValue(False)

        elif status.command == 'Update_Status':
            self.thread_status(status)

        elif status.command == 'set_info':
            param_dict = ioxml.XML_string_to_parameter(status.attribute[1])[0]
            param_tmp = Parameter.create(**param_dict)
            param = self.settings.child('move_settings', *status.attribute[0][1:])

            param.restoreState(param_tmp.saveState())


class DAQ_Move_Hardware(QObject):
    """
        ================== ========================
        **Attributes**      **Type**
        *status_sig*        instance of Signal
        *hardware*          ???
        *actuator_type*        string
        *current_position*  float
        *target_value*   float
        *hardware_adress*   string
        *axis_address*      string
        *motion_stoped*     boolean
        ================== ========================
    """
    status_sig = Signal(ThreadCommand)

    def __init__(self, actuator_type, position, title='actuator'):
        super().__init__()
        self.logger = set_logger(f'{logger.name}.{title}.actuator')
        self._title = title
        self.hardware = None
        self.actuator_type = actuator_type
        self.current_position = position
        self._target_value = 0
        self.hardware_adress = None
        self.axis_address = None
        self.motion_stoped = False

    def close(self):
        """
            Uninitialize the stage closing the hardware.

        """
        self.hardware.close()

        return "Stage uninitialized"

    def get_actuator_value(self):
        """Get the current position checking the hardware value.
        """
        pos = self.hardware.get_actuator_value()
        return pos

    def check_position(self):
        """Get the current position checking the hardware position (deprecated)
        """
        deprecation_msg('check_position is deprecated, use get_actuator_value')
        pos = self.hardware.get_actuator_value()
        return pos

    def ini_stage(self, params_state=None, controller=None):
        """
            Init a stage updating the hardware and sending an hardware move_done signal.

            =============== =================================== ==========================================================================================================================
            **Parameters**   **Type**                             **Description**

             *params_state*  ordered dictionnary list             The parameter state of the hardware class composed by a list representing the tree to keep a temporary save of the tree

             *controller*    one or many instance of DAQ_Move     The controller id of the hardware

             *stage*         instance of DAQ_Move                 Defining axes and motors
            =============== =================================== ==========================================================================================================================

            See Also
            --------
            DAQ_utils.ThreadCommand, DAQ_Move
        """

        status = edict(initialized=False, info="")
        try:
            parent_module = utils.find_dict_in_list_from_key_val(DAQ_Move_Actuators, 'name', self.actuator_type)
            class_ = getattr(getattr(parent_module['module'], 'daq_move_' + self.actuator_type),
                             'DAQ_Move_' + self.actuator_type)
            self.hardware = class_(self, params_state)
            try:
                infos = self.hardware.ini_stage(controller)  # return edict(info="", controller=, stage=)
            except Exception as e:
                logger.exception('Hardware couldn\'t be initialized' + str(e))
                infos = str(e), False

            if isinstance(infos, edict):  # following old plugin templating
                status.update(infos)
                deprecation_msg('Returns from init_stage should now be a string and a boolean,'
                                ' see pymodaq_plugins_template', stacklevel=3)
            else:
                status.info = infos[0]
                status.initialized = infos[1]
            status.controller = self.hardware.controller
            self.hardware.move_done_signal.connect(self.move_done)

            return status
        except Exception as e:
            self.logger.exception(str(e))
            return status

    def move_abs(self, position, polling=True):
        """
            Make the hardware absolute move from the given position.

            =============== ========= =======================
            **Parameters**  **Type**   **Description**

            *position*       float     The absolute position
            =============== ========= =======================

            See Also
            --------
            move_Abs
        """
        position = float(position)  # because it may be a numpy float and could cause issues
        # see https://github.com/pythonnet/pythonnet/issues/1833
        self._target_value = position
        self.hardware.move_is_done = False
        self.hardware.ispolling = polling
        pos = self.hardware.move_abs(position)
        self.hardware.poll_moving()

    def move_rel(self, rel_position, polling=True):
        """
            Make the hardware relative move from the given relative position added to the current one.

            ================ ========= ======================
            **Parameters**   **Type**  **Description**

             *position*       float    The relative position
            ================ ========= ======================

            See Also
            --------
            move_Rel
        """
        rel_position = float(rel_position)  # because it may be a numpy float and could cause issues
        # see https://github.com/pythonnet/pythonnet/issues/1833
        self.hardware.move_is_done = False
        self._target_value = self.current_position + rel_position
        self.hardware.ispolling = polling
        pos = self.hardware.move_rel(rel_position)
        self.hardware.poll_moving()

    @Slot(float)
    def Move_Stoped(self, pos):
        """
            Send a "move_done" Thread Command with the given position as an attribute.

            See Also
            --------
            DAQ_utils.ThreadCommand
        """
        self.status_sig.emit(ThreadCommand("move_done", [pos]))

    def move_home(self):
        """
            Make the hardware move to the init position.

        """
        self.hardware.move_is_done = False
        self._target_value = 0
        self.hardware.move_home()

    @Slot(float)
    def move_done(self, pos):
        """Send the move_done signal back to the main class
        """
        self._current_value = pos
        self.status_sig.emit(ThreadCommand(command="move_done", attribute=[pos]))

    @Slot(ThreadCommand)
    def queue_command(self, command: ThreadCommand):
        """Interpret command send by DAQ_Move class
                * In case of **'ini_stage'** command, init a stage from command attribute.
                * In case of **'close'** command, unitinalise the stage closing hardware and emitting the corresponding status signal
                * In case of **'move_abs'** command, call the move_Abs method with position from command attribute
                * In case of **'move_rel'** command, call the move_Rel method with the relative position from the command attribute.
                * In case of **'move_home'** command, call the move_Home method
                * In case of **'get_actuator_value'** command, get the current position from the check_position method
                * In case of **'Stop_motion'** command, stop any motion via the stop_Motion method
                * In case of **'reset_stop_motion'** command, set the motion_stopped attribute to false

        Parameters
        ----------
        command: ThreadCommand
            Possible commands are:
            * **'ini_stage'** command, init a stage from command attribute.
            * **'close'** command, unitinalise the stage closing hardware and emitting the corresponding status signal
            * **'move_abs'** command, call the move_abs method with position from command attribute
            * **'move_rel'** command, call the move_rel method with the relative position from the command attribute.
            * **'move_home'** command, call the move_home method
            * **'get_actuator_value'** command, get the current position from the check_position method
            * **'stop_motion'** command, stop any motion via the stop_Motion method
            * **'reset_stop_motion'** command, set the motion_stopped attribute to false
        """
        try:
            if command.command == "ini_stage":
                status = self.ini_stage(
                    *command.attribute)  # return edict(initialized=bool,info="", controller=, stage=)
                self.status_sig.emit(ThreadCommand(command=command.command, attribute=[status, 'log']))

            elif command.command == "close":
                status = self.close()
                self.status_sig.emit(ThreadCommand(command=command.command, attribute=[status]))

            elif command.command == "move_abs":
                self.move_abs(*command.attribute)

            elif command.command == "move_rel":
                self.move_rel(*command.attribute)

            elif command.command == "move_home":
                self.move_home()

            elif command.command == "get_actuator_value":
                pos = self.get_actuator_value()
                self.status_sig.emit(ThreadCommand('get_actuator_value', [pos]))

            elif command.command == "stop_motion":
                self.stop_motion()

            elif command.command == "reset_stop_motion":
                self.motion_stoped = False

            else:  # custom commands for particular plugins (see spectrometer module 'get_spectro_wl' for instance)
                if hasattr(self.hardware, command.command):
                    cmd = getattr(self.hardware, command.command)
                    cmd(*command.attribute)
        except Exception as e:
            self.logger.exception(str(e))


    def stop_motion(self):
        """
            stop hardware motion with motion_stopped attribute updtaed to True and a status signal sended with an "update_status" Thread Command

            See Also
            --------
            DAQ_utils.ThreadCommand, stop_motion
        """
        self.status_sig.emit(ThreadCommand(command="Update_Status", attribute=["Motion stoping", 'log']))
        self.motion_stoped = True
        self.hardware.stop_motion()
        self.hardware.poll_timer.stop()

    @Slot(edict)
    def update_settings(self, settings_parameter_dict):
        """
            Update settings of hardware with dictionnary parameters in case of "Move_Settings" path, else update attribute with dictionnary parameters.

            =========================  =========== ======================================================
            **Parameters**              **Type**    **Description**

            *settings_parameter_dict*  dictionnary  Dictionnary containing the path and linked parameter
            =========================  =========== ======================================================

            See Also
            --------
            update_settings
        """
        # settings_parameter_dict = edict(path=path,param=param)
        path = settings_parameter_dict['path']
        param = settings_parameter_dict['param']
        if path[0] == 'main_settings':
            if hasattr(self, path[-1]):
                setattr(self, path[-1], param.value())

        elif path[0] == 'move_settings':
            self.hardware.update_settings(settings_parameter_dict)


def main(init_qt=True):
    if init_qt:  # used for the test suite
        app = QtWidgets.QApplication(sys.argv)

    widget = QtWidgets.QWidget()
    prog = DAQ_Move(widget, title="test")
    widget.show()

    if init_qt:
        sys.exit(app.exec_())
    return prog, widget


if __name__ == '__main__':
    main()


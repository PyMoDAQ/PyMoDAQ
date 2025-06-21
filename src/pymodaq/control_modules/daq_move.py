# -*- coding: utf-8 -*-
"""
Created the 29/07/2022

@author: Sebastien Weber
"""

from __future__ import annotations

import numbers
from importlib import import_module
from numbers import Number

import sys
from typing import List, Tuple, Union, Optional, Type
import numpy as np

from qtpy.QtCore import QObject, Signal, QThread, Slot, Qt, QTimer
from qtpy import QtWidgets

from easydict import EasyDict as edict

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import ThreadCommand
from pymodaq_utils import utils
from pymodaq.utils.gui_utils import get_splash_sc
from pymodaq_utils import config as config_mod
from pymodaq.utils.exceptions import ActuatorError
from pymodaq_utils.warnings import deprecation_msg
from pymodaq.utils.data import DataToExport, DataActuator
from pymodaq_data.h5modules.backends import Node

from pymodaq_gui.parameter import ioxml, Parameter
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.utils.utils import mkQApp

from pymodaq.utils.h5modules import module_saving
from pymodaq.control_modules.utils import ParameterControlModule
from pymodaq.control_modules.daq_move_ui import DAQ_Move_UI, ThreadCommand
from pymodaq.control_modules.move_utility_classes import (MoveCommand, DAQ_Move_base,
                                                          DataActuatorType, check_units,
                                                          DataUnitError)


from pymodaq.control_modules.move_utility_classes import params as daq_move_params
from pymodaq.utils.leco.pymodaq_listener import MoveActorListener, LECOMoveCommands

from pymodaq.utils.daq_utils import get_plugins
from pymodaq import Q_, Unit



local_path = config_mod.get_set_local_dir()
sys.path.append(str(local_path))
logger = set_logger(get_module_name(__file__))
config = config_mod.Config()

DAQ_Move_Actuators = get_plugins('daq_move')
ACTUATOR_TYPES = [mov['name'] for mov in DAQ_Move_Actuators]
if len(ACTUATOR_TYPES) == 0:
    raise ActuatorError('No installed Actuator')


STATUS_WAIT_TIME = 1000


class DAQ_Move(ParameterControlModule):
    """ Main PyMoDAQ class to drive actuators

    Qt object and generic UI to drive actuators.

    Attributes
    ----------
    init_signal: Signal[bool]
        This signal is emitted when the chosen actuator is correctly initialized
    move_done_signal: Signal[str, DataActuator]
        This signal is emitted when the chosen actuator finished its action. It gives the actuator's name and current
        value
    bounds_signal: Signal[bool]
        This signal is emitted when the actuator reached defined limited boundaries.

    See Also
    --------
    :class:`ControlModule`, :class:`ParameterManager`
    """
    settings_name = 'daq_move_settings'

    move_done_signal = Signal(DataActuator)
    current_value_signal = Signal(DataActuator)
    bounds_signal = Signal(bool)

    params = daq_move_params

    listener_class = MoveActorListener

    def __init__(self, parent=None, title="DAQ Move", **kwargs):
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

        super().__init__(action_list=('save', 'update'), **kwargs)

        self.parent = parent
        if parent is not None:
            self.ui = DAQ_Move_UI(parent, title)
        else:
            self.ui: Optional[DAQ_Move_UI] = None

        if self.ui is not None:
            self.ui.actuators = ACTUATOR_TYPES
            self.ui.set_settings_tree(self.settings_tree)
            self.ui.command_sig.connect(self.process_ui_cmds)

        self.splash_sc = get_splash_sc()
        self._title = title
        if len(ACTUATOR_TYPES) > 0:  # will be 0 if no valid plugins are installed
            self.actuator = kwargs.get('actuator', ACTUATOR_TYPES[0])

        self.module_and_data_saver = module_saving.ActuatorSaver(self)

        self._move_done_bool = True

        self._current_value = DataActuator(title, units=self.units)
        self._target_value = DataActuator(title, units=self.units)
        self._relative_value = DataActuator(title, units=self.units)

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
            * show_config
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
            data_act: DataActuator = cmd.attribute
            if not Unit(data_act.units).is_compatible_with(self.units) and data_act.units != '':
                data_act.force_units(self.units)
            self.move_abs(data_act)
        elif cmd.command == 'move_rel':
            data_act: DataActuator = cmd.attribute
            if not Unit(data_act.units).is_compatible_with(self.units) and data_act.units != '':
                data_act.force_units(self.units)
            self.move_rel(data_act)
        elif cmd.command == 'show_log':
            self.show_log()
        elif cmd.command == 'show_config':
            self.config = self.show_config(self.config)
            self.ui.config = self.config
        elif cmd.command == 'actuator_changed':
            self.actuator = cmd.attribute
        elif cmd.command == 'rel_value':
            self._relative_value = cmd.attribute

    @property
    def master(self) -> bool:
        """ Get/Set programmatically the Master/Slave status of an actuator"""
        if self.initialized_state:
            return self.settings['move_settings', 'multiaxes', 'multi_status'] == 'Master'
        else:
            return True

    @master.setter
    def master(self, is_master: bool):
        if self.initialized_state:
            self.settings.child('move_settings', 'multiaxes', 'multi_status').setValue(
                'Master' if is_master else 'Slave')

    def append_data(self, dte: Optional[DataToExport] = None, where: Union[Node, str, None] = None):
        """Appends current DataToExport to an ActuatorEnlargeableSaver

        Parameters
        ----------
        data
        where: Node or str
        See Also
        --------
        ActuatorEnlargeableSaver
        """
        if dte is None:
            dte = DataToExport(name=self.title, data=[self._current_value])
        self._add_data_to_saver(dte, where=where)
        # todo: test this for logging

    def _add_data_to_saver(self, data: DataToExport, where=None, **kwargs):
        """Adds DataToExport data to the current node using the declared module_and_data_saver

        Filters the data to be saved by DataSource as specified in the current H5Saver (see self.module_and_data_saver)

        Parameters
        ----------
        data: DataToExport
            The data to be saved
        kwargs: dict
            Other named parameters to be passed as is to the module_and_data_saver

        See Also
        --------
        DetectorSaver, DetectorEnlargeableSaver, DetectorExtendedSaver

        """
        #todo: test this for logging

        node = self.module_and_data_saver.get_set_node(where)
        self.module_and_data_saver.add_data(node, data, **kwargs)

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

    def move_abs(self, value: Union[DataActuator, numbers.Number], send_to_tcpip=False):
        """Move the connected hardware to the absolute value

        Returns nothing but the move_done_signal will be send once the action is done

        Parameters
        ----------
        value: ndarray
            The value the actuator should reach
        send_to_tcpip: bool
            if True, this position is send through the TCP/IP communication canal
        """
        try:
            if isinstance(value, Number):
                value = DataActuator(self.title, data=[np.array([value])], units=self.units)
            self._send_to_tcpip = send_to_tcpip
            if value != self._current_value:
                if self.ui is not None:
                    self.ui.move_done = False
                self._move_done_bool = False
                self._target_value = value
                self.update_status("Moving")
                self.command_hardware.emit(ThreadCommand(command="reset_stop_motion"))
                self.command_hardware.emit(ThreadCommand(command="move_abs", attribute=[value]))

        except Exception as e:
            self.logger.exception(str(e))

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
            self.command_hardware.emit(ThreadCommand(command="move_home"))

        except Exception as e:
            self.logger.exception(str(e))

    def move_rel(self, rel_value: Union[DataActuator, numbers.Number], send_to_tcpip=False):
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
            if isinstance(rel_value, Number):
                rel_value = DataActuator(self.title, data=[np.array([rel_value])], units=self.units)
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
        self.quit_signal.emit()
        if self.ui is not None:
            self.ui.close()
        # self.parent.close()

    def init_hardware(self, do_init=True):
        """ Init or desinit the selected instrument plugin class """
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
                    ThreadCommand(command="ini_stage", attribute=[
                        self.settings.child('move_settings').saveState(),
                        self.controller]))
            except Exception as e:
                self.logger.exception(str(e))

    @property
    def initialized_state(self):
        """bool: status of the actuator's initialization (init or not)"""
        return self._initialized_state

    @property
    def move_done_bool(self):
        """bool: status of the actuator's status (done or not)"""
        return self._move_done_bool

    def value_changed(self, param: Parameter):
        """ Apply changes of value in the settings"""
        super().value_changed(param=param)

        if param.name() == 'refresh_timeout':
            self._refresh_timer.setInterval(param.value())

        self._update_settings(param=param)

    def param_deleted(self, param):
        """ Apply deletion of settings """
        if param.name() not in putils.iter_children(self.settings.child('main_settings'), []):
            self._update_settings_signal.emit(edict(path=['move_settings'], param=param, change='parent'))

    def child_added(self, param, data):
        """ Apply addition of settings """
        path = self.settings.childPath(param)
        if 'main_settings' not in path:
            self._update_settings_signal.emit(edict(path=path, param=data[0].saveState(), change='childAdded'))

    def raise_timeout(self):
        """ Update status with "Timeout occurred" statement and change the timeout flag.
        """
        self.update_status("Timeout occurred")
        self.wait_position_flag = False

    @Slot(ThreadCommand)
    def thread_status(self, status: ThreadCommand):  # general function to get datas/infos from all threads back to the main
        """Get back info (using the ThreadCommand object) from the hardware

        And re-emit this ThreadCommand using the custom_sig signal if it should be used in a higher level module

        Commands valid for all control modules are defined in the parent class, here are described only the specific
        ones

        Parameters
        ----------
        status: ThreadCommand
            Possible values are:

            * **ini_stage**: obtains info from the initialization
            * **get_actuator_value**: update the UI current value
            * **move_done**: update the UI current value and emits the move_done signal
            * **outofbounds**: emits the bounds_signal signal with a True argument
            * **set_allowed_values**: used to change the behaviour of the spinbox controlling absolute values (see
              :meth:`daq_move_ui.set_abs_spinbox_properties`
            * stop: stop the motion
        """

        super().thread_status(status, 'move')

        if status.command == "ini_stage":
            self.update_status(f"Stage initialized: {status.attribute['initialized']} "
                               f"info: {status.attribute['info']}")
            if status.attribute['initialized']:
                self.controller = status.attribute['controller']
                if self.ui is not None:
                    self.ui.actuator_init = True
                self._initialized_state = True
            else:
                self._initialized_state = False
            if self._initialized_state:
                self.get_actuator_value()
            self.init_signal.emit(self._initialized_state)

        elif status.command == "get_actuator_value" or status.command == 'check_position':
            data_act = self._check_data_type(status.attribute)
            if self.ui is not None:
                self.ui.display_value(data_act)
                if self.ui.is_action_checked('show_graph'):
                    self.ui.show_data(DataToExport(name=self.title,
                                                   data=[data_act]))
            self._current_value = data_act
            self.current_value_signal.emit(self._current_value)
            if self.settings['main_settings', 'tcpip', 'tcp_connected'] and self._send_to_tcpip:
                self._command_tcpip.emit(ThreadCommand('position_is', data_act))
            if self.settings['main_settings', 'leco', 'leco_connected'] and self._send_to_tcpip:
                self._command_tcpip.emit(ThreadCommand(LECOMoveCommands.POSITION, data_act))

        elif status.command == "move_done":
            data_act = self._check_data_type(status.attribute)
            if self.ui is not None:
                self.ui.display_value(data_act)
                self.ui.move_done = True
            self._current_value = data_act
            self._move_done_bool = True
            self.move_done_signal.emit(data_act)
            if self.settings.child('main_settings', 'tcpip', 'tcp_connected').value() and self._send_to_tcpip:
                self._command_tcpip.emit(ThreadCommand('move_done', data_act))
            if self.settings.child('main_settings', 'leco', 'leco_connected').value() and self._send_to_tcpip:
                self._command_tcpip.emit(ThreadCommand(LECOMoveCommands.MOVE_DONE, data_act))

        elif status.command == 'outofbounds':
            logger.warning(f'The Actuator {self.title} has reached its defined bounds')
            self.bounds_signal.emit(True)

        elif status.command == 'set_allowed_values':
            if self.ui is not None:
                self.ui.set_abs_spinbox_properties(**status.attribute)

        elif status.command == 'stop':
            self.stop_motion()

        elif status.command == 'units':
            self.units = status.attribute

    def _check_data_type(self, data_act: Union[list[np.ndarray], float, DataActuator]) -> DataActuator:
        """ Make sure the data is a DataActuator

        Mostly to make sure DAQ_Move is backcompatible with old style plugins
        """
        if isinstance(data_act, list):  # backcompatibility
            data_act = data_act[0]
        if isinstance(data_act, np.ndarray):  # backcompatibility
            data_act = DataActuator(data=[data_act], units=self.units)
        data_act.name = self.title  # for the DataActuator name to be the title of the DAQ_Move
        if (not Unit(self.units).is_compatible_with(Unit(data_act.units)) and
                data_act.units == ''):  #this happens if the units have not been specified in
            # the plugin
            data_act.force_units(self.units)
        return  data_act

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
            self.manage_ui_actions('refresh_value', 'setChecked', False)
        self.get_continuous_actuator_value(False)

    def stop_grab(self):
        """Stop value polling. Mandatory

        First uncheck the ui action if ui is not None, then stop the polling
        """
        if self.ui is not None:
            self.manage_ui_actions('refresh_value', 'setChecked', False)
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
            self.update_plugin_config()
            if self.ui is not None:
                self.ui.actuator = act_type
            self.update_settings()
        else:
            raise ActuatorError(f'{act_type} is an invalid actuator, should be within {ACTUATOR_TYPES}')

    @property
    def actuators(self) -> List[str]:
        """ Get the list of possible actuators"""
        return ACTUATOR_TYPES

    def update_plugin_config(self):
        parent_module = utils.find_dict_in_list_from_key_val(DAQ_Move_Actuators, 'name', self.actuator)
        mod = import_module(parent_module['module'].__package__.split('.')[0])
        if hasattr(mod, 'config'):
            self.plugin_config = mod.config

    @property
    def units(self):
        """Get/Set the units for the controller"""
        return self.settings['move_settings', 'units']

    @units.setter
    def units(self, unit: str):
        self.settings.child('move_settings', 'units').setValue(unit)
        if self.ui is not None and config('actuator', 'display_units'):
            self.ui.set_unit_as_suffix(self.get_unit_to_display(unit))

    @staticmethod
    def get_unit_to_display(unit: str) -> str:
        """ Get the unit to be displayed in the UI

        If the controller units are in mm the displayed unit will be m
        because m is the base unit, then the user could ask for mm, km, µm...
        only issue is when the usual displayed unit is not the base one, then add cases below

        Parameters
        ----------
        unit: str

        Returns
        -------
        str: the unit to be displayed on the ui
        """
        if ('°' in unit or 'degree' in unit) and not '°C' in unit:
            # special cas as pint base unit for angles are radians
            return '°'
        elif 'W' in unit or 'watt' in unit.lower():
            return 'W'
        elif '°C' in unit or 'Celsius' in unit:
            return '°C'
        elif 'V' in unit or 'volt' in unit.lower():
            return 'V'
        elif 'Hz' in unit:
            return 'Hz'
        elif 'rpm' in unit or 'revolutions_per_minute' in unit:
            return 'rpm'
        else:
            return str(Q_(1, unit).to_base_units().units)

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
        super().connect_tcp_ip(params_state=self.settings.child('move_settings'),
                               client_type="ACTUATOR")

    @Slot(ThreadCommand)
    def process_tcpip_cmds(self, status: ThreadCommand) -> None:
        if super().process_tcpip_cmds(status=status) is None:
            return
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

        elif status.command == 'set_info':
            path_in_settings = status.attribute[0]
            param_as_xml = status.attribute[1]
            param_dict = ioxml.XML_string_to_parameter(param_as_xml)[0]
            param_tmp = Parameter.create(**param_dict)
            param = self.settings.child('move_settings', *path_in_settings[1:])
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

    def __init__(self, actuator_type, position: DataActuator, title='actuator'):
        super().__init__()
        self.logger = set_logger(f'{logger.name}.{title}.actuator')
        self._title = title
        self.hardware: Optional[DAQ_Move_base] = None
        self.actuator_type = actuator_type
        self.hardware_adress = None
        self.axis_address = None
        self.motion_stoped = False

    @property
    def title(self):
        return self._title

    def close(self):
        """
            Uninitialize the stage closing the hardware.

        """
        if self.hardware is not None and self.hardware.controller is not None:
            self.hardware.close()

        return "Stage uninitialized"

    def get_actuator_value(self):
        """Get the current position checking the hardware value.
        """
        if self.hardware is not None:
            pos = self.hardware.get_actuator_value()
            if self.hardware.data_actuator_type == DataActuatorType.float:
                pos = DataActuator(self._title, data=pos, units=self.hardware.axis_unit)
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

             *params_state*  ordered dictionary list             The parameter state of the hardware class composed by a list representing the tree to keep a temporary save of the tree

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
                logger.exception("Hardware couldn't be initialized", exc_info=e)
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
            if status.initialized:
                self.status_sig.emit(ThreadCommand('get_actuator_value', [self.get_actuator_value()]))

            return status
        except Exception as e:
            self.logger.exception(str(e))
            return status

    def move_abs(self, position: DataActuator, polling=True):
        """

        """
        position = check_units(position, self.hardware.axis_unit)
        self.hardware.move_is_done = False
        self.hardware.ispolling = polling
        if self.hardware.data_actuator_type == self.hardware.data_actuator_type.float:
            self.hardware.move_abs(position.units_as(self.hardware.axis_unit).value()) # convert to plugin controller current axis units
        else:
            position.units = self.hardware.axis_unit  # convert to plugin controller current axis units
            self.hardware.move_abs(position)
        self.hardware.poll_moving()

    def move_rel(self, rel_position: DataActuator, polling=True):
        """

        """
        rel_position = check_units(rel_position, self.hardware.axis_unit)
        self.hardware.move_is_done = False
        self.hardware.ispolling = polling

        if self.hardware.data_actuator_type.name == 'float':
            self.hardware.move_rel(rel_position.value())
        else:
            rel_position.units = self.hardware.axis_unit  # convert to plugin current axis units
            self.hardware.move_rel(rel_position)

        self.hardware.poll_moving()

    @Slot(float)
    def Move_Stoped(self, pos):
        """
            Send a "move_done" Thread Command with the given position as an attribute.

            See Also
            --------
            DAQ_utils.ThreadCommand
        """
        self.status_sig.emit(ThreadCommand("move_done", pos))

    def move_home(self):
        """
            Make the hardware move to the init position.

        """
        self.hardware.move_is_done = False
        self.hardware.move_home()

    @Slot(DataActuator)
    def move_done(self, pos: DataActuator):
        """Send the move_done signal back to the main class
        """
        self._current_value = pos
        self.status_sig.emit(ThreadCommand(command="move_done", attribute=pos))

    @Slot(ThreadCommand)
    def queue_command(self, command: ThreadCommand):
        """Interpret command send by DAQ_Move class
                * **ini_stage** command, init a stage from command attribute.
                * **close** command, unitinalise the stage closing hardware and emitting the corresponding status signal
                * **move_abs** command, call the move_Abs method with position from command attribute
                * **move_rel** command, call the move_Rel method with the relative position from the command attribute.
                * **move_home** command, call the move_home method
                * **get_actuator_value** command, get the current position from the check_position method
                * **Stop_motion** command, stop any motion via the stop_Motion method
                * **reset_stop_motion** command, set the motion_stopped attribute to false

        Parameters
        ----------
        command: ThreadCommand
            Possible commands are:
            * **ini_stage** command, init a stage from command attribute.
            * **close** command, unitinalise the stage closing hardware and emitting the corresponding status signal
            * **move_abs** command, call the move_abs method with position from command attribute
            * **move_rel** command, call the move_rel method with the relative position from the command attribute.
            * **move_home** command, call the move_home method
            * **get_actuator_value** command, get the current position from the check_position method
            * **stop_motion** command, stop any motion via the stop_Motion method
            * **reset_stop_motion** command, set the motion_stopped attribute to false
        """
        try:
            logger.debug(f'Threadcommand {command.command} sent to {self.title}')
            if command.command == "ini_stage":
                status: edict = self.ini_stage(*command.attribute)
                self.status_sig.emit(ThreadCommand(command=command.command, attribute=status))

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
                    if isinstance(command.attribute, list):
                        cmd(*command.attribute)
                    elif isinstance(command.attribute, dict):
                        cmd(**command.attribute)
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
        if self.hardware is not None and self.hardware.controller is not None:
            self.hardware.stop_motion()
        self.hardware.poll_timer.stop()

    @Slot(edict)
    def update_settings(self, settings_parameter_dict):
        """
            Update settings of hardware with dictionary parameters in case of "Move_Settings" path, else update attribute with dictionnary parameters.

            =========================  =========== ======================================================
            **Parameters**              **Type**    **Description**

            *settings_parameter_dict*  dictionary  Dictionary containing the path and linked parameter
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
            if self.hardware is not None:
                self.hardware.update_settings(settings_parameter_dict)


def main(init_qt=True):
    if init_qt:  # used for the test suite
        app = mkQApp("PyMoDAQ Move")

    widget = QtWidgets.QWidget()
    prog = DAQ_Move(widget, title="test")
    widget.show()

    if init_qt:
        sys.exit(app.exec_())
    return prog, widget


if __name__ == '__main__':
    main()


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
from typing import List, Union, Optional, Dict, TypeVar, TYPE_CHECKING
import numpy as np

from qtpy.QtCore import QObject, Signal, QThread, Slot, Qt, QTimer
from qtpy import QtWidgets

from easydict import EasyDict as edict

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import find_keys_from_val
from pymodaq_utils import utils
from pymodaq.utils.gui_utils import get_splash_sc
from pymodaq_utils.config import get_set_local_dir, GlobalConfig as Config
from pymodaq.utils.exceptions import ActuatorError
from pymodaq_utils.warnings import deprecation_msg
from pymodaq.utils.data import DataToExport, DataActuator
from pymodaq_data.h5modules.backends import Node, SaveType

from pymodaq_gui.h5modules.saving import H5Saver
from pymodaq_gui.parameter import ioxml, Parameter
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.qt_utils import mkQApp

from pymodaq.utils.h5modules import module_saving
from pymodaq.control_modules.instruments import ACTUATOR_TYPES, ACTUATOR_NAMES
from pymodaq.control_modules.utils import ParameterControlModule, HardwareWorkerBase

from pymodaq.control_modules.thread_commands import (ThreadStatus, ThreadStatusMove, ControlToHardware,
                                                     ControlToHardwareMove, UiToMainMove,
                                                     )
from pymodaq.control_modules.move_utility_classes import (ThreadCommand, MoveCommand, DAQ_Move_base, DataActuatorType,
                                                           check_units)


from pymodaq.control_modules.move_utility_classes import params as daq_move_params
from pymodaq.utils.leco.pymodaq_listener import (MoveActorListener, LECOMoveCommands, LECOCommands,)
from pymodaq import Q_, Unit


from pymodaq.control_modules.daq_move_ui.factory import ActuatorUIFactory

if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move_ui.ui_base import DAQ_Move_UI_Base

sys.path.append(str(get_set_local_dir()))
logger = set_logger(get_module_name(__file__))

config = Config()

HardwareController = TypeVar("HardwareController")


STATUS_WAIT_TIME = 1000


class DAQ_Move(ParameterControlModule):
    """Main PyMoDAQ class to drive actuators

    Qt object and generic UI to drive actuators.

    Attributes
    ----------
    move_done_signal: Signal[str, DataActuator]
        This signal is emitted when the chosen actuator finished its action. It gives the actuator's name and current
        value
    bounds_signal: Signal[bool]
        This signal is emitted when the actuator reached defined limited boundaries.

    See Also
    --------
    :class:`ControlModule`, :class:`ParameterManager`
    """

    settings_name = "daq_move_settings"
    _hw_kind = 'actuator'
    _ini_hw_cmd = ControlToHardware.INI_HARDWARE

    move_done_signal = Signal(DataActuator)
    current_value_signal = Signal(DataActuator)
    bounds_signal = Signal(bool)

    params = daq_move_params + [
        {'title': 'Saver Settings:', 'name': 'saver_settings', 'type': 'group',
         'visible': True, 'children': H5Saver.get_params_for_save_type(SaveType.actuator), 'expanded': False}]

    listener_class = MoveActorListener
    ui: Optional[DAQ_Move_UI_Base]

    def __init__(self, parent=None, title="DAQ Move", ui_identifier: Optional[str] = None, **kwargs) -> None:
        """

        Parameters
        ----------
        parent: QWidget or None
        parent: QWidget or None
            if it is a valid QWidget, it will hold the user interface to drive it
        title: str
            The unique (should be unique) string identifier for the underlying actuator
        """

        self.logger = set_logger(f"{logger.name}.{title}")
        self.logger.info(f"Initializing DAQ_Move: {title}")

        super().__init__(listener_class=MoveActorListener, action_list=("save", "update"), **kwargs)

        if not (
            ui_identifier is not None and ui_identifier in ActuatorUIFactory.keys()
        ):
            ui_identifier = config("pymodaq", "actuator", "ui")[0]
        self.settings.child("main_settings", "ui_type").setValue(ui_identifier)
        self.settings.child("main_settings", "ui_type").setOpts(readonly=True)

        DAQ_Move_UI = ActuatorUIFactory.get(ui_identifier)

        self.parent = parent
        if parent is not None:
            self.ui = DAQ_Move_UI(parent, title)
        else:
            self.ui = None

        if self.ui is not None:
            self.ui.actuators = ACTUATOR_NAMES
            self.ui.set_settings_tree(self.settings_tree)
            self.ui.command_sig.connect(self.process_ui_cmds)

        self.splash_sc = get_splash_sc()
        self._title = title
        if len(ACTUATOR_NAMES) > 0:  # will be 0 if no valid plugins are installed
            self.actuator = kwargs.get("actuator", ACTUATOR_NAMES[0])

        self._module_and_data_saver: module_saving.ActuatorTimeSaver = None
        for hidden_param in ('custom_name',
                            'current_scan_name',
                            'current_scan_path',
                            'current_h5_file',
                            'new_file',
                            'base_name'):
            self.settings.child('saver_settings', hidden_param).setOpts(visible=False)

        self._move_done_bool = True

        self._current_value = DataActuator(title, units=self.units)
        self._target_value = DataActuator(title, units=self.units)
        self._relative_value = DataActuator(title, units=self.units)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.get_actuator_value)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def current_value(self) -> DataActuator:
        if self._current_value.origin is None:
            self.current_value.origin = self.title
        return self._current_value

    @property
    def epsilon(self) -> float:
        return self.settings[self._hw_settings_name, 'epsilon']

    @property
    def move_done_bool(self):
        """bool: status of the actuator's status (done or not)"""
        return self._move_done_bool

    @property
    def actuator(self):
        """str: the selected actuator's type"""
        return self._actuator_type

    @actuator.setter
    def actuator(self, act_type):
        if act_type in ACTUATOR_NAMES:
            self._actuator_type = act_type
            self.update_plugin_config()
            if self.ui is not None:
                self.ui.actuator = act_type
            self._reload_plugin_settings()
        else:
            raise ActuatorError(
                f"{act_type} is an invalid actuator, should be within {ACTUATOR_NAMES}"
            )

    @property
    def actuators(self) -> List[str]:
        """Get the list of possible actuators"""
        return ACTUATOR_NAMES

    @property
    def units(self):
        """Get/Set the units for the controller"""
        return self.settings[self._hw_settings_name, "units"]

    @units.setter
    def units(self, unit: str):
        self.settings.child(self._hw_settings_name, "units").setValue(unit)
        if self.ui is not None and config("pymodaq", "actuator", "display_units"):
            unit = self.get_unit_to_display(unit)
            self.ui.set_unit_as_suffix(unit)
            self.ui.set_unit_prefix(
                config("pymodaq", "actuator", "siprefix")
                and (unit != "" or config("pymodaq", "actuator", "siprefix_even_without_units"))
            )

    @property
    def axis_names(self) -> Union[List, Dict]:
        """ Get the names of all possible axis"""
        return self.settings.child(self._hw_settings_name, 'controller', 'axis').opts['limits']

    @property
    def axis_name(self) -> str:
        """ Get/Set the current axis"""
        limits = self.settings.child(self._hw_settings_name, 'controller', 'axis').opts['limits']
        val = self.settings[self._hw_settings_name, 'controller', 'axis']
        if isinstance(limits, list):
            return val
        elif isinstance(limits, dict):
            return find_keys_from_val(limits, val=val)[0]
        else:
            TypeError('Unknown limits type')

    @axis_name.setter
    def axis_name(self, name: str):
        """ Get/Set the current axis"""
        limits = self.settings.child(self._hw_settings_name, 'controller', 'axis').opts['limits']
        if name in limits:
            if isinstance(limits, list):
                value = name
            elif isinstance(limits, dict):
                value = limits[name]
            else:
                return
            self.settings.child(self._hw_settings_name, 'controller', 'axis').setValue(value)

    # -------------------------------------------------------------------------
    # UI command processing
    # -------------------------------------------------------------------------

    def process_ui_cmds(self, cmd: utils.ThreadCommand):
        """Process commands sent by actions done in the ui

        Parameters
        ----------
        cmd: ThreadCommand
            Possible values are :
            * init
            * get_value
            * loop_get_value
            * find_home
            * stop
            * move_abs
            * move_rel
            * actuator_changed
            * rel_value
        """
        if cmd.command == UiToMainMove.INIT:
            self.init_hardware(cmd.attribute[0])
        elif cmd.command == UiToMainMove.GET_VALUE:
            self.get_actuator_value()
        elif cmd.command == UiToMainMove.LOOP_GET_VALUE:
            self.get_continuous_actuator_value(cmd.attribute)
        elif cmd.command == UiToMainMove.FIND_HOME:
            self.move_home()
        elif cmd.command == UiToMainMove.STOP:
            self.stop_motion()
        elif cmd.command == UiToMainMove.MOVE_ABS:
            data_act: DataActuator = cmd.attribute
            if (
                not Unit(data_act.units).is_compatible_with(self.units)
                and data_act.units != ""
            ):
                data_act.force_units(self.units)
            self.move_abs(data_act)
        elif cmd.command == UiToMainMove.MOVE_REL:
            data_act: DataActuator = cmd.attribute
            if (
                not Unit(data_act.units).is_compatible_with(self.units)
                and data_act.units != ""
            ):
                data_act.force_units(self.units)
            self.move_rel(data_act)
            self.ui.config = self.config
        elif cmd.command == UiToMainMove.ACTUATOR_CHANGED:
            self.actuator = cmd.attribute
        elif cmd.command == UiToMainMove.REL_VALUE:
            self._relative_value = cmd.attribute

    # -------------------------------------------------------------------------
    # Hardware lifecycle hooks
    # -------------------------------------------------------------------------

    def _pre_close_hardware(self):
        """Stop the refresh timer before closing so no more commands reach the hardware thread."""
        self._refresh_timer.stop()

    def _create_hardware(self):
        return ActuatorWorker(self._actuator_type, self._current_value, self._title)

    # -------------------------------------------------------------------------
    # Acquisition API
    # -------------------------------------------------------------------------

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
        if move_command.move_type == "abs":
            self.move_abs(move_command.value)
        elif move_command.move_type == "rel":
            self.move_rel(move_command.value)
        elif move_command.move_type == "home":
            self.move_home(move_command.value)

    def move_abs(self, value: Union[DataActuator, numbers.Number], send_to_leco=False):
        """Move the connected hardware to the absolute value

        Returns nothing but the move_done_signal will be send once the action is done

        Parameters
        ----------
        value: ndarray or DataActuator
            The value the actuator should reach
        send_to_leco: bool
            if True, this position is send through the LECO communication canal
        """
        try:
            if isinstance(value, Number):
                value = DataActuator(
                    self.title, data=[np.array([value])], units=self.units,
                )
            self._send_to_leco = send_to_leco
            if value.equal_to(self._current_value, Q_(self.epsilon, self.units)):
                self.thread_status(ThreadCommand(ThreadStatusMove.MOVE_DONE, value))
            else:
                if self.ui is not None:
                    self.ui.move_done = False
                self._move_done_bool = False
                self._target_value = value
                self.update_status("Moving")
                self.command_hardware.emit(
                    ThreadCommand(ControlToHardwareMove.RESET_STOP_MOTION),
                )
                self.command_hardware.emit(
                    ThreadCommand(ControlToHardwareMove.MOVE_ABS, attribute=[value]),
                )

        except Exception as e:
            self.logger.exception(str(e))

    def move_home(self, send_to_leco=False):
        """Move the connected actuator to its home value (if any)

        Parameters
        ----------
        send_to_leco: bool
            if True, this position is send through the LECO communication canal
        """
        self._send_to_leco = send_to_leco
        try:
            if self.ui is not None:
                self.ui.move_done = False
            self._move_done_bool = False
            self.update_status("Moving")
            self.command_hardware.emit(
                ThreadCommand(ControlToHardwareMove.RESET_STOP_MOTION),
            )
            self.command_hardware.emit(ThreadCommand(ControlToHardwareMove.MOVE_HOME))

        except Exception as e:
            self.logger.exception(str(e))

    def move_rel(
        self, rel_value: Union[DataActuator, numbers.Number], send_to_leco=False,
    ):
        """Move the connected hardware to the relative value

        Returns nothing but the move_done_signal will be send once the action is done

        Parameters
        ----------
        value: float
            The relative value the actuator should reach
        send_to_leco: bool
            if True, this position is send through the LECO communication canal
        """

        try:
            if isinstance(rel_value, Number):
                rel_value = DataActuator(
                    self.title, data=[np.array([rel_value])], units=self.units,
                )
            self._send_to_leco = send_to_leco
            if self.ui is not None:
                self.ui.move_done = False
            self._move_done_bool = False
            self._target_value = self._current_value + rel_value
            self.update_status("Moving")
            self.command_hardware.emit(
                ThreadCommand(ControlToHardwareMove.RESET_STOP_MOTION),
            )
            self.command_hardware.emit(
                ThreadCommand(ControlToHardwareMove.MOVE_REL, attribute=[rel_value]),
            )

        except Exception as e:
            self.logger.exception(str(e))

    def move_rel_p(self):
        self.move_rel(self._relative_value)

    def move_rel_m(self):
        self.move_rel(-self._relative_value)

    def get_actuator_value(self, send_to_leco=False):
        """Get the current actuator value via the "get_actuator_value" command send to the hardware

        Returns nothing but the  `move_done_signal` will be send once the action is done
        Parameters
        ----------
        send_to_leco: bool
            if True, this position is send through the LECO communication canal
        """
        self._send_to_leco = send_to_leco

        try:
            self.command_hardware.emit(
                ThreadCommand(ControlToHardwareMove.GET_ACTUATOR_VALUE)
            )

        except Exception as e:
            self.logger.exception(str(e))

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
            self._refresh_timer.setInterval(
                self.settings["main_settings", "refresh_timeout"]
            )
            self._refresh_timer.start()
        else:
            self._refresh_timer.stop()

    def grab(self):
        if self.ui is not None:
            self.manage_ui_actions("refresh_value", "setChecked", False)
        self.get_continuous_actuator_value(False)

    def stop_motion(self):
        """Stop any motion"""
        try:
            self.command_hardware.emit(ThreadCommand(ControlToHardwareMove.STOP_MOTION))
        except Exception as e:
            self.logger.exception(str(e))

    def stop_module(self):
        """ Programmatic entry to stop the Control module either moving, polling or grabbing"""
        self.stop_motion()
        self.stop_grab()

    def stop_grab(self):
        """Stop value polling. Mandatory

        First uncheck the ui action if ui is not None, then stop the polling
        """
        if self.ui is not None:
            self.manage_ui_actions("refresh_value", "setChecked", False)
        self.get_continuous_actuator_value(False)

    # -------------------------------------------------------------------------
    # Saving
    # -------------------------------------------------------------------------

    def setup_continuous_saving(self, init: bool = True):
        """Configure the objects dealing with the continuous saving mode"""
        if init:
            self.module_and_data_saver = module_saving.ActuatorTimeSaver(self)
            self.module_and_data_saver.h5saver = self.h5saver
            self.h5saver.settings.child('do_save').sigValueChanged.connect(self._init_continuous_save)
        else:
            self.h5saver.close_file()

    def _init_continuous_save(self):
        """ Initialize the continuous saving H5Saver object

        Update the module_and_data_saver attribute as :class:`DetectorTimeSaver` object
        """
        if self.settings.child('saver_settings', 'do_save').value():

            self.settings.child('saver_settings', 'base_name').setValue('Data')
            self.settings.child('saver_settings', 'N_saved').show()
            self.settings.child('saver_settings', 'N_saved').setValue(0)
            self.h5saver.init_file(update_h5=True)
        else:
            self.settings.child('saver_settings', 'N_saved').hide()

    def append_data(
        self, dte: Optional[DataToExport] = None, where: Union[Node, str, None] = None
    ):
        """Appends current DataToExport to an ActuatorEnlargeableSaver

        Parameters
        ----------
        dte: DataToExport, optional
        where: Node or str
        See Also
        --------
        ActuatorEnlargeableSaver
        """
        if dte is None:
            dte = DataToExport(name=self.title, data=[self._current_value])
        self._add_data_to_saver(dte, where=where)
        self.settings.child('saver_settings', 'N_saved').setValue(self.settings['saver_settings', 'N_saved'] + 1)

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
        # todo: test this for logging

        node = self.module_and_data_saver.get_set_node(where)
        self.module_and_data_saver.add_data(node, data, **kwargs)

    # -------------------------------------------------------------------------
    # Settings / Plugin management
    # -------------------------------------------------------------------------

    def update_plugin_config(self):
        parent_module = utils.find_dict_in_list_from_key_val(
            ACTUATOR_TYPES, "name", self.actuator
        )
        mod = import_module(parent_module["module"].__package__.split(".")[0])

    @staticmethod
    def get_unit_to_display(unit: str) -> str:
        """Get the unit to be displayed in the UI

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
        if ("°" in unit or "degree" in unit) and not "°C" in unit:
            # special case as pint base unit for angles are radians
            return "°"
        elif "°C" in unit:
            return "°C"
        else:
            for key in config("pymodaq", "actuator", "allowed_units"):
                if key in unit:
                    return config("pymodaq", "actuator", "allowed_units", key)
            return str(Q_(1, unit).to_base_units().units)

    def _load_plugin_params(self):
        parent_module = utils.find_dict_in_list_from_key_val(
            ACTUATOR_TYPES, "name", self._actuator_type
        )
        class_ = getattr(
            getattr(parent_module["module"], "daq_move_" + self._actuator_type),
            "DAQ_Move_" + self._actuator_type,
        )
        params = getattr(class_, "params")
        return Parameter.create(name=self._hw_settings_name, type="group", children=params)

    def _reload_plugin_settings(self):
        """Reload plugin settings, also updating the move_type in main_settings."""
        self.settings.child("main_settings", "move_type").setValue(self._actuator_type)
        super()._reload_plugin_settings()

    def _module_value_changed(self, param: Parameter):
        """Handle actuator-specific parameter changes."""
        if param.name() == "refresh_timeout":
            self._refresh_timer.setInterval(param.value())
        elif param.name() in putils.iter_children(self.settings.child('saver_settings'), []):
            path = self.settings.childPath(param)
            if param.name() == 'do_save':
                self.setup_continuous_saving(param.value())
            self.h5saver.settings.child(*path[1:]).setValue(param.value())

    # -------------------------------------------------------------------------
    # Thread status handler
    # -------------------------------------------------------------------------

    def _check_data_type(
        self, data_act: Union[list, np.ndarray, Number, DataActuator]
    ) -> DataActuator:
        """Make sure the data is a DataActuator

        Mostly to make sure DAQ_Move is backcompatible with old style plugins
        """
        if isinstance(data_act, list):  # backcompatibility
            if isinstance(data_act[0], Number):
                data_act = DataActuator(
                    data=[np.atleast_1d(val) for val in data_act], units=self.units
                )
            elif isinstance(data_act[0], np.ndarray):
                data_act = DataActuator(data=data_act, units=self.units)
            elif isinstance(data_act[0], DataActuator):
                data_act = data_act[0]
            else:
                raise TypeError("Unknown data type")
        elif isinstance(data_act, np.ndarray):  # backcompatibility
            data_act = DataActuator(data=[data_act], units=self.units)
        data_act.name = (
            self.title
        )  # for the DataActuator name to be the title of the DAQ_Move
        if (
            not Unit(self.units).is_compatible_with(Unit(data_act.units))
            and data_act.units == ""
        ):  # this happens if the units have not been specified in
            # the plugin
            data_act.force_units(self.units)
        return data_act

    @Slot(ThreadCommand)
    def thread_status(
        self, status: ThreadCommand,
    ):  # general function to get datas/infos from all threads back to the main
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

        super().thread_status(status)

        if status.command == ThreadStatus.INI_HARDWARE or status.command == ThreadStatusMove.INI_STAGE:
            self.update_status(
                f"Stage initialized: {status.attribute['initialized']} "
                f"info: {status.attribute['info']}",
            )
            if status.attribute["initialized"]:
                self.controller = status.attribute["controller"]
                if self.ui is not None:
                    self.ui.actuator_init = True
                self._initialized_state = True
            else:
                self._initialized_state = False
            if self._initialized_state:
                self.get_actuator_value()
            self.init_signal.emit(self._initialized_state)

        elif (
            status.command == ThreadStatusMove.GET_ACTUATOR_VALUE
            or status.command == "check_position"
        ):
            data_act = self._check_data_type(status.attribute)
            if self.ui is not None:
                self.ui.display_value(data_act)
                if self.ui.has_action("show_graph") and not self.ui.is_action_checked(
                    "show_graph",
                ):
                    self.ui.show_data(DataToExport(name=self.title, data=[data_act]))

            self._current_value = data_act
            if self.settings['saver_settings', 'do_save']:
                self.append_data()

            self.current_value_signal.emit(self._current_value)

            if self.settings["main_settings", "leco", "leco_connected"] and self._send_to_leco:
                self._leco_commands_signal.emit(ThreadCommand(LECOMoveCommands.POSITION, data_act))

        elif status.command == ThreadStatusMove.MOVE_DONE:
            data_act = self._check_data_type(status.attribute)
            if self.ui is not None:
                self.ui.display_value(data_act)
                self.ui.move_done = True
            self._current_value = data_act
            self._move_done_bool = True
            data_act.origin = data_act.origin if data_act.origin is not (None or '') else self.title
            self.move_done_signal.emit(data_act)

            if self.settings.child("main_settings", "leco", "leco_connected").value() and self._send_to_leco:
                self._leco_commands_signal.emit(ThreadCommand(LECOMoveCommands.MOVE_DONE, data_act))

        elif status.command == ThreadStatusMove.OUT_OF_BOUNDS:
            logger.warning(f"The Actuator {self.title} has reached its defined bounds")
            self.bounds_signal.emit(True)

        elif status.command == ThreadStatusMove.SET_ALLOWED_VALUES:
            if self.ui is not None:
                self.ui.set_abs_spinbox_properties(**status.attribute)

        elif status.command in (ThreadStatus.STOP, ThreadStatusMove.STOP):
            self.stop_motion()

        elif status.command == ThreadStatusMove.UNITS:
            self.units = status.attribute

    # -------------------------------------------------------------------------
    # LECO
    # -------------------------------------------------------------------------

    def process_leco_commands(self, status: ThreadCommand) -> None:
        """Receive commands from the LECO network and process them.

        Parameters
        ----------
        status: ThreadCommand
            Possible commands are:

            * :attr:`LECOMoveCommands.MOVE_ABS`: move to the absolute position given in ``status.attribute``.
            * :attr:`LECOMoveCommands.MOVE_REL`: move by the relative amount given in ``status.attribute``.
            * :attr:`LECOMoveCommands.MOVE_HOME`: move to the home position.
            * :attr:`LECOMoveCommands.STOP`: stop any ongoing motion.
            * :attr:`LECOMoveCommands.GET_ACTUATOR_VALUE`: read and return the current actuator position to LECO.
        """

        if status.command == LECOMoveCommands.MOVE_ABS:
            self.move_abs(status.attribute, send_to_leco=True)
        elif status.command == LECOMoveCommands.MOVE_REL:
            self.move_rel(status.attribute, send_to_leco=True)
        elif status.command == LECOMoveCommands.MOVE_HOME:
            self.move_home(send_to_leco=True)
        elif status.command == LECOMoveCommands.GET_ACTUATOR_VALUE:
            self.get_actuator_value(send_to_leco=True)
        elif status.command == LECOMoveCommands.STOP:
            self.stop_motion()
        else:
            super().process_leco_commands(status=status)


class ActuatorWorker(HardwareWorkerBase):
    """Worker class mediating between DAQ_Move and the actuator plugin instance.

    ================== ========================
    **Attributes**      **Type**
    *status_sig*        instance of Signal (inherited)
    *plugin*            actuator plugin instance
    *plugin_name*       string (inherited property)
    *controller_address* int or None
    *axis_address*      string
    *motion_stopped*    boolean
    ================== ========================
    """

    _kind = 'actuator'

    def __init__(self, actuator_type, position: DataActuator, title="actuator"):
        super().__init__(title, actuator_type)
        self.logger = set_logger(f"{logger.name}.{title}.actuator")
        self.plugin: Optional[DAQ_Move_base] = None
        self.axis_address = None
        self.motion_stopped = False
        self._move_completed = False   # debounce guard for MOVE_DONE

    # --- deprecated aliases ---------------------------------------------------

    @property
    def hardware(self):
        deprecation_msg("hardware is deprecated, use plugin")
        return self.plugin

    @property
    def hardware_adress(self):
        deprecation_msg("hardware_adress is deprecated, use controller_address")
        return self.controller_address

    @property
    def actuator_type(self):
        deprecation_msg("actuator_type is deprecated, use plugin_name")
        return self.plugin_name

    @property
    def motion_stoped(self):
        deprecation_msg("motion_stoped is deprecated, use motion_stopped")
        return self.motion_stopped

    def close(self):
        """Uninitialize the stage closing the hardware."""
        if self.plugin is not None and self.plugin.controller is not None:
            self.plugin.close()
        return "Stage uninitialized"

    def get_actuator_value(self) -> Optional[DataActuator]:
        """Get the current position from the plugin."""
        if self.plugin is not None:
            pos = self.plugin.get_actuator_value()
            if self.plugin.data_actuator_type == DataActuatorType.float:
                pos = DataActuator(self.title, data=pos, units=self.plugin.axis_unit)
            return pos

    def check_position(self):
        """Get the current position checking the hardware position (deprecated)"""
        deprecation_msg("check_position is deprecated, use get_actuator_value")
        pos = self.plugin.get_actuator_value()
        return pos

    def ini_hardware(self, params_state=None, controller: Optional[HardwareController] = None) -> edict:
        """Init the actuator plugin and wire its signals."""
        status = edict(initialized=False, info="")
        try:
            parent_module = utils.find_dict_in_list_from_key_val(
                ACTUATOR_TYPES, "name", self.plugin_name
            )
            class_ = getattr(
                getattr(parent_module["module"], "daq_move_" + self.plugin_name),
                "DAQ_Move_" + self.plugin_name,
            )
            self.plugin = class_(self, params_state)
            assert self.plugin is not None
            try:
                infos = self.plugin.ini_stage(
                    controller
                )  # return edict(info="", controller=, stage=)
            except Exception as e:
                self.logger.exception("Hardware couldn't be initialized", exc_info=e)
                infos = str(e), False

            if isinstance(infos, edict):  # following old plugin templating
                status.update(infos)
                deprecation_msg(
                    "Returns from init_stage should now be a string and a boolean,"
                    " see pymodaq_plugins_template",
                    stacklevel=3,
                )
            else:
                status.info = infos[0]
                status.initialized = infos[1]
            status.controller = self.plugin.controller
            self.controller_address = self.plugin.controller
            self.plugin.move_done_signal.connect(self.move_done)
            if status.initialized:
                self.status_sig.emit(
                    ThreadCommand(
                        ThreadStatusMove.GET_ACTUATOR_VALUE, self.get_actuator_value(),
                    ),
                )

            return status
        except Exception as e:
            self.logger.exception(str(e))
            return status

    def ini_stage(self, params_state=None, controller=None) -> edict:
        """Deprecated: use ini_hardware instead."""
        deprecation_msg("ini_stage is deprecated, use ini_hardware")
        return self.ini_hardware(params_state, controller)

    def move_abs(self, position: DataActuator, polling: bool = True) -> None:
        assert self.plugin is not None
        position = check_units(position, self.plugin.axis_unit)
        self.plugin.move_is_done = False
        self.plugin.ispolling = polling
        self._move_completed = False
        if self.plugin.data_actuator_type == self.plugin.data_actuator_type.float:
            self.plugin.move_abs(
                position.units_as(self.plugin.axis_unit).value()
            )
        else:
            position.units = self.plugin.axis_unit
            self.plugin.move_abs(position)
        self.plugin.poll_moving()

    def move_rel(self, rel_position: DataActuator, polling: bool = True) -> None:
        assert self.plugin is not None
        rel_position = check_units(rel_position, self.plugin.axis_unit)
        self.plugin.move_is_done = False
        self.plugin.ispolling = polling
        self._move_completed = False

        if self.plugin.data_actuator_type.name == 'float':
            self.plugin.move_rel(rel_position.units_as(self.plugin.axis_unit).value())
        else:
            rel_position.units = self.plugin.axis_unit
            self.plugin.move_rel(rel_position)

        self.plugin.poll_moving()

    @Slot(float)
    def Move_Stoped(self, pos):
        """Send a 'move_done' Thread Command with the given position as an attribute."""
        deprecation_msg("Move_Stoped is deprecated, use the move_done_signal instead")
        self.status_sig.emit(ThreadCommand(ThreadStatusMove.MOVE_DONE, pos))

    def move_home(self):
        """Make the hardware move to the init position."""
        assert self.plugin is not None
        self.plugin.move_is_done = False
        self._move_completed = False
        self.plugin.move_home()

    @Slot(DataActuator)
    def move_done(self, pos: DataActuator):
        """Send the move_done signal back to the main class"""
        if self._move_completed:
            return
        self._move_completed = True
        self._current_value = pos
        self.status_sig.emit(
            ThreadCommand(command=ThreadStatusMove.MOVE_DONE, attribute=pos),
        )

    @Slot(ThreadCommand)
    def queue_command(self, command: ThreadCommand):
        """Interpret command sent by DAQ_Move class.

        Common commands (ini_hardware, close) are handled by the base class.
        Move-specific commands are handled here.
        """
        if super().queue_command(command):
            return
        try:
            logger.debug(f"Threadcommand {command.command} sent to {self.title}")
            if command.command == ControlToHardwareMove.INI_STAGE:
                # Legacy alias → emit the canonical INI_HARDWARE status
                status: edict = self.ini_hardware(*command.attribute)
                self.status_sig.emit(
                    ThreadCommand(command=ThreadStatus.INI_HARDWARE, attribute=status)
                )

            elif command.command == ControlToHardwareMove.MOVE_ABS:
                self.move_abs(*command.attribute)

            elif command.command == ControlToHardwareMove.MOVE_REL:
                self.move_rel(*command.attribute)

            elif command.command == ControlToHardwareMove.MOVE_HOME:
                self.move_home()

            elif command.command == ControlToHardwareMove.GET_ACTUATOR_VALUE:
                pos = self.get_actuator_value()
                self.status_sig.emit(
                    ThreadCommand(ThreadStatusMove.GET_ACTUATOR_VALUE, pos),
                )

            elif command.command == ControlToHardwareMove.STOP_MOTION:
                self.stop_motion()

            elif command.command == ControlToHardwareMove.RESET_STOP_MOTION:
                self.motion_stopped = False

            else:  # custom commands for particular plugins
                self._dispatch_custom_command(command)
        except Exception as e:
            self.logger.exception(str(e))

    def stop_motion(self):
        """Stop hardware motion."""
        self.status_sig.emit(
            ThreadCommand(command=ThreadStatus.UPDATE_STATUS, attribute="Motion stopping")
        )
        self.motion_stopped = True
        assert self.plugin is not None
        if self.plugin is not None and self.plugin.controller is not None:
            self.plugin.stop_motion()
        self.plugin.poll_timer.stop()


def main(init_qt=True):
    from pymodaq.utils.gui_utils.loader_utils import create_load_daq_move
    app = mkQApp("PyMoDAQ Move")
    shared_ui, daq_move = create_load_daq_move('simple')
    shared_ui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

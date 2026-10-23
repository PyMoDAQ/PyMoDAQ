from contextlib import contextmanager
import warnings
import numpy as np
from typing import List, Union, TYPE_CHECKING, Optional, Sequence, Callable, Any, Iterator, cast

from pymodaq.control_modules.enums import MoveType
from pymodaq.control_modules.viewer_utility_classes import HW_SETTINGS_KEY as DETECTOR_SETTINGS_KEY

from qtpy.QtCore import QObject, Signal, Slot, QThread, QTimer
from qtpy import QtWidgets

import time

from pymodaq.utils.managers.modules.utils import ModuleType
from pymodaq_utils.enums import enum_checker
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import utils
from pymodaq_utils.config import GlobalConfig as Config

from pymodaq_data.data import DataToExport, DataSource, DataDim

from pymodaq_gui.parameter import Parameter
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.utils import Dock
from pymodaq_gui.messenger import messagebox

from pymodaq.utils.data import DataActuator, DataToActuators
from pymodaq.control_modules.thread_commands import ControlToHardwareMove, ControlToHardwareViewer

if TYPE_CHECKING:
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer
    from pymodaq.control_modules.daq_move import DAQ_Move

logger = set_logger(get_module_name(__file__))
config = Config()




class ModulesManager(QObject, ParameterManager):
    """Class to manage DAQ_Viewers and DAQ_Moves with UI to select some

    Easier to connect control modules signals to slots, test, ...

    Parameters
    ----------
    detectors: list of DAQ_Viewer
    actuators: list of DAQ_Move
    selected_detectors: list of DAQ_Viewer
        sublist of detectors
    selected_actuators: list of DAQ_Move
        sublist of actuators
    """
    settings_name = 'ModulesManagerSettings'
    modules_added_signal = Signal()
    detectors_changed = Signal(list)
    actuators_changed = Signal(list)
    det_done_signal = Signal(DataToExport)  # dte here contains DataWithAxes
    move_done_signal = Signal(DataToExport)  # dte here contains DataActuators
    timeout_signal = Signal(list)  # list of titles of the modules whose origin wasn't found among
                                    # the received responses (see grab_data/move_actuators)

    params = [
        {'title': "Probe detectors", 'name': 'probe_detectors', 'type': 'action_led', 'value': False},
        {'title': "Probe actuators", 'name': 'probe_actuators', 'type': 'action_led', 'value': False},

        {'title': 'Detectors', 'name': 'detectors', 'type': 'itemselect', 'checkbox': True},
        {'title': 'Actuators', 'name': 'actuators', 'type': 'itemselect', 'checkbox': True},

        # Probe results live in their own group, not nested under the probe buttons above,
        # so they render below the selection lists instead of pushing them out of view.
        {'title': 'Probed detector data', 'name': 'probe_detectors_results', 'type': 'group', 'children': []},
        {'title': 'Probed actuator positions', 'name': 'probe_actuators_results', 'type': 'group', 'children': []},
    ]

    def __init__(self,
                 detectors: Optional[Sequence['DAQ_Viewer']] = None,
                 actuators: Optional[Sequence['DAQ_Move']] = None,
                 selected_detectors: Optional[Sequence['DAQ_Viewer']] = None,
                 selected_actuators: Optional[Sequence['DAQ_Move']] = None,
                 parent_name: str = '',
                 **kwargs: Any) -> None:
        self.parent_name = parent_name
        # (callback, wrapper) pairs of the callbacks that detach themselves, see _auto_forgetting
        self._auto_forgetting_wrappers: list[tuple[Callable[..., Any], Callable[..., Any]]] = []
        QObject.__init__(self)
        ParameterManager.__init__(self)
        if detectors is None:
            detectors = []
        if actuators is None:
            actuators = []
        if selected_detectors is None:
            selected_detectors = []
        if selected_actuators is None:
            selected_actuators = []


        for mod in selected_actuators:
            assert mod in actuators
        for mod in selected_detectors:
            assert mod in detectors

        # None until the first grab / move, which sets them before they are used
        self.det_done_datas: DataToExport = None  # type: ignore[assignment]
        self.det_done_flag = False
        self.move_done_positions: DataToExport = None  # type: ignore[assignment]
        self.move_done_flag = False

        # sigActivated emits the param itself (ActionLedParameter.activate()), but neither
        # handler takes any argument, so Qt drops it -- same as any other zero-arg slot.
        self.settings.child('probe_detectors').sigActivated.connect(self.probe_detectors)
        self.settings.child('probe_actuators').sigActivated.connect(self.probe_actuators)

        self._detectors: list['DAQ_Viewer'] = []
        self._actuators: list['DAQ_Move'] = []

        self.actuators_connected = False
        self.detectors_connected = False

        self.set_actuators(list(actuators), list(selected_actuators))
        self.set_detectors(list(detectors), list(selected_detectors))

        self.detectors_timeout_timer = QTimer()
        self.detectors_timeout_timer.setSingleShot(True)
        self.detectors_timeout_timer.timeout.connect(self._on_detectors_timeout)

        self.actuators_timeout_timer = QTimer()
        self.actuators_timeout_timer.setSingleShot(True)
        self.actuators_timeout_timer.timeout.connect(self._on_actuators_timeout)

    def on_hardware_initialization(self, do_init: bool, module: Union['DAQ_Move', 'DAQ_Viewer']) -> None:
        """ Bypass method during initialization to assert whether a Master of some slave module already exists

        If a master module with the same id is already initialized, the slave module shares its controller and
        thread. The module is then initialized (or closed) according to *do_init*.

        Parameters
        ----------
        do_init: bool
            True to initialize the hardware of the module, False to close it
        module: DAQ_Move or DAQ_Viewer
            The control module whose hardware is about to be initialized
        """
        if not module.master:
            for other_module in self.modules_all:
                if other_module.initialized_state and other_module.id == module.id and other_module.master:
                    # the controller_and_thread of a control module is always set by its constructor
                    module.controller_and_thread.controller = other_module.controller_and_thread.controller  # type: ignore[union-attr]
                    module.controller_and_thread.thread = other_module.controller_and_thread.thread  # type: ignore[union-attr]
                    break
        module.init_hardware(do_init)

    def get_random_id(self) -> int:
        """ get a random *id* not already used by a module"""
        ids = [mod.id for mod in self.modules_all]
        id = np.random.randint(1, 1000)
        while id in ids:
            id = np.random.randint(1, 1000)
        return id

    @property
    def actuator_timeout(self) -> float:
        """Timeout (in seconds) while waiting for the actuators to reach their target positions (from the config)"""
        return config('pymodaq', 'actuator', 'polling_timeout_s')

    @property
    def detector_timeout(self) -> float:
        """Timeout (in milliseconds) while waiting for the detectors to send their data (from the config)"""
        return config('pymodaq', 'viewer', 'timeout')

    def enable_modules(self, enable: bool = True) -> None:
        """Enable or disable the toolbar of all the control modules"""
        for module in self.modules_all:
            module.ui.toolbar.setEnabled(enable)  # type: ignore[union-attr]

    def __repr__(self) -> str:
        try:
            return f'ModulesManager of "{self.parent_name}" with control modules: {self.get_names(self.modules_all)}'
        except AttributeError:
            return f'ModulesManager of "{self.parent_name}"'

    def show_only_control_modules(self, show: bool) -> None:
        """Hide (True) or show (False) the probing actions and results of the settings"""
        self.settings.child('probe_detectors').show(not show)
        self.settings.child('probe_actuators').show(not show)
        self.settings.child('probe_detectors_results').show(not show)
        self.settings.child('probe_actuators_results').show(not show)

    @classmethod
    def get_names(cls, modules: Union[Sequence[Union['DAQ_Move', 'DAQ_Viewer']], 'DAQ_Move', 'DAQ_Viewer']
                  ) -> list[str]:
        """Get the titles of a list of Control Modules

        Parameters
        ----------
        modules: list of DAQ_Move and/or DAQ_Viewer
            A single module is also accepted

        Returns
        -------
        list of str
            The title of each module
        """
        if not hasattr(modules, '__iter__'):
            modules = [modules]  # type: ignore[list-item]
        return [mod.title for mod in modules]  # type: ignore[union-attr]

    def get_mods_from_names(self, names: Sequence[str], mod: Union[ModuleType, str] = ModuleType.Detector
                            ) -> List[Union['DAQ_Move', 'DAQ_Viewer']]:
        """Getter of a list of given modules from their name (title)

        The names that do not match any module are ignored.

        Parameters
        ----------
        names: list of str
        mod: ModuleType or str
            either ModuleType.Detector for DAQ_Viewer modules or ModuleType.Actuator for DAQ_Move modules
            (the 'det' and 'act' strings are also accepted, for backward compatibility)
        """
        mods = []
        for name in names:
            d = self.get_mod_from_name(name, mod)
            if d is not None:
                mods.append(d)
        return mods

    def get_mod_from_name(self, name: str, mod: Union[ModuleType, str] = ModuleType.Detector
                          ) -> Union['DAQ_Move', 'DAQ_Viewer', None]:
        """Getter of a given module from its name (title)

        Returns None is no control module with this name exists

        Parameters
        ----------
        name: str
        mod: ModuleType or str
            either ModuleType.Detector for DAQ_Viewer modules or ModuleType.Actuator for DAQ_Move modules
            (the 'det' and 'act' strings are also accepted, for backward compatibility)
        """
        if mod == ModuleType.Detector or mod == 'det':  #backcompat when comparing to 'det'
            modules = self._detectors
        elif mod == ModuleType.Actuator or mod == 'act':
            modules = self._actuators
        elif mod == ModuleType.Control:
            modules = self._actuators + self._detectors
        else:
            return None

        if name in self.get_names(modules):
            return modules[self.get_names(modules).index(name)]
        else:
            logger.warning(f'No detector with this name: {name}')
            return None

    def add_modules(self, modules: list[Union['DAQ_Move', 'DAQ_Viewer']]) -> None:
        """ Add new modules to the manager keeping the initial set of selected actuators or detectors"""
        actuators = [act for act in modules if act.__class__.__name__ == 'DAQ_Move']
        detectors = [det for det in modules if det.__class__.__name__ == 'DAQ_Viewer']

        self.set_actuators(self.actuators_all + actuators, self.actuators)
        self.set_detectors(self.detectors_all + detectors, self.detectors)
        logger.debug(f"New modules added to the ModulesManager: {modules}"
                     f"Total list is: {self.modules_name}")
        self.modules_added_signal.emit()


    def set_actuators(self, actuators: list['DAQ_Move'], selected_actuators: list['DAQ_Move']) -> None:
        """Populates actuators and the subset to be selected in the UI"""
        self._actuators = actuators
        self.settings.child('actuators').setValue(dict(all_items=self.get_names(actuators),
                                                       selected=self.get_names(selected_actuators)))
    def set_actuators_from_names(self, actuators: list[str], selected_actuators: list[str]) -> None:
        """Populates actuators and the subset to be selected in the UI from their names"""
        for act in actuators:
            assert act in self.actuators_name
        for act in selected_actuators:
            assert act in self.actuators_name
        self.settings.child('actuators').setValue(dict(all_items=actuators,
                                                       selected=selected_actuators))

    def set_detectors(self, detectors: list['DAQ_Viewer'], selected_detectors: list['DAQ_Viewer']) -> None:
        """Populates detectors and the subset to be selected in the UI"""
        self._detectors = detectors
        self.settings.child('detectors').setValue(dict(all_items=self.get_names(detectors),
                                                       selected=self.get_names(selected_detectors)))

    def set_detectors_from_names(self, detectors: list[str], selected_detectors: list[str]) -> None:
        """Populates detectors and the subset to be selected in the UI from their names"""
        for det in detectors:
            assert det in self.detectors_name
        for det in selected_detectors:
            assert det in self.detectors_name
        self.settings.child('detectors').setValue(dict(all_items=detectors,
                                                       selected=selected_detectors))

    @property
    def detectors(self) -> List['DAQ_Viewer']:
        """Get the list of selected detectors"""
        return self.get_mods_from_names(self.selected_detectors_name)

    @property
    def detectors_all(self)  -> List['DAQ_Viewer']:
        """Get/Set the list of all detectors"""
        return self._detectors

    @detectors_all.setter
    def detectors_all(self, detectors: List['DAQ_Viewer']) -> None:
        self.set_detectors(detectors, [])

    @property
    def actuators(self) -> List['DAQ_Move']:
        """Get the list of selected actuators"""
        return self.get_mods_from_names(self.selected_actuators_name, mod=ModuleType.Actuator)

    @property
    def actuators_all(self) -> list['DAQ_Move']:
        """Get the list of all actuators"""
        return self._actuators

    @actuators_all.setter
    def actuators_all(self, actuators: List['DAQ_Move']) -> None:
        self.set_actuators(actuators, [])

    @property
    def modules(self) -> List[Union['DAQ_Move', 'DAQ_Viewer']]:
        """Get the list of detectors and actuators"""
        return self.detectors + self.actuators

    @property
    def modules_all(self) -> List[Union['DAQ_Move', 'DAQ_Viewer']]:
        """Get the list of all detectors and actuators"""
        return self.detectors_all + self.actuators_all

    @property
    def modules_name(self) -> list[str]:
        return [mod.title for mod in self.modules_all]

    @property
    def Ndetectors(self) -> int:
        """Get the number of selected detectors"""
        return len(self.detectors)

    @property
    def Nactuators(self) -> int:
        """Get the number of selected actuators"""
        return len(self.actuators)

    @property
    def detectors_name(self) -> List[str]:
        """Get all the names of the detectors"""
        return self.settings.child('detectors').value()['all_items']

    @property
    def selected_detectors_name(self) -> List[str]:
        """Get/Set the names of the selected detectors"""
        return self.settings.child('detectors').value()['selected']

    @selected_detectors_name.setter
    def selected_detectors_name(self, detectors: Sequence[str]) -> None:
        if set(detectors).issubset(self.detectors_name):
            self.settings.child('detectors').setValue(dict(all_items=self.detectors_name,
                                                           selected=detectors))

    @property
    def actuators_name(self) -> List[str]:
        """Get all the names of the actuators"""
        return self.settings.child('actuators').value()['all_items']

    @property
    def selected_actuators_name(self) -> List[str]:
        """Get/Set the names of the selected actuators"""
        return self.settings.child('actuators').value()['selected']

    @selected_actuators_name.setter
    def selected_actuators_name(self, actuators: Sequence[str]) -> None:
        if set(actuators).issubset(self.actuators_name):
            self.settings.child('actuators').setValue(dict(all_items=self.actuators_name,
                                                           selected=actuators))

    def value_changed(self, param: Parameter) -> None:
        """Clear the probed results and emit detectors_changed / actuators_changed when a selection changes"""
        if param.name() == 'detectors':
            # Previously probed channels no longer reflect the current selection
            self.settings.child('probe_detectors_results').clearChildren()
            self.detectors_changed.emit(param.value()['selected'])

        elif param.name() == 'actuators':
            self.settings.child('probe_actuators_results').clearChildren()
            self.actuators_changed.emit(param.value()['selected'])

    @contextmanager
    def _probing(self, connect: Callable[..., Any], timeout_handler: Callable[[List[str]], Any]) -> Iterator[None]:
        """Shared connect/timeout-watch/disconnect scaffold around a probe action.

        Both get_det_data_list (grab_data) and probe_actuators (move_actuators) bracket
        their actual hardware call the same way: connect modules, watch timeout_signal for
        a reply, always disconnect both afterwards. Only what happens *inside* differs.

        Parameters
        ----------
        connect: Callable[[bool], Any]
            connect_detectors or connect_actuators
        timeout_handler: Callable[[List[str]], Any]
            _on_detector_probe_timeout or _on_actuator_probe_timeout
        """
        connect()
        self.timeout_signal.connect(timeout_handler)
        try:
            yield
        finally:
            self.timeout_signal.disconnect(timeout_handler)
            connect(False)

    def probe_detectors(self) -> DataToExport:
        """Do a snap of selected detectors, to populate the Detectors panel's result tree
        (probe_detectors_results) and return the data"""

        if len(self.detectors) == 0:
            return DataToExport(name=__class__.__name__, control_module='DAQ_Viewer')  # type: ignore[name-defined]

        with self._probing(self.connect_detectors, self._on_detector_probe_timeout):
            datas: DataToExport = self.grab_data(Naverage=1)
            logger.debug(f'Acquired: {datas.get_full_names()}')

            results = self.settings.child('probe_detectors_results')
            results.clearChildren()

            data_children = []
            for data_dim in DataDim.names():
                data_from_dim = datas.get_data_from_dim(data_dim)
                if len(data_from_dim) != 0:
                    data_children.append(
                        {'title': data_dim, 'name': data_dim, 'type': 'group', 'children':[
                            {'title': dwa.origin, 'name': dwa.get_full_name(), 'type': 'str',
                             'value': dwa.name, 'readonly': True} for dwa in data_from_dim
                        ]})
            results.addChildren(data_children)
        return datas

    def get_det_data_list(self) -> DataToExport:
        """Deprecated alias for probe_detectors(), kept for backward compatibility."""
        warnings.warn(
            "get_det_data_list() is deprecated, use probe_detectors() instead",
            DeprecationWarning, stacklevel=2,
        )
        return self.probe_detectors()

    def _report_probe_timeout(self, probe_param_name: str, kind: str, missing_modules: List[str]) -> None:
        """ Reset the probe button's LED and report which modules failed to answer, by name """
        self.settings.child(probe_param_name).setValue(False)
        messagebox(text=f"The following {kind}(s) did not respond in time:\n"
                        + "\n".join(missing_modules))

    def _on_detector_probe_timeout(self, missing_modules: List[str]) -> None:
        self._report_probe_timeout('probe_detectors', 'detector', missing_modules)

    def _on_actuator_probe_timeout(self, missing_modules: List[str]) -> None:
        self._report_probe_timeout('probe_actuators', 'actuator', missing_modules)

    def get_probed_data_full_names(self, dim: Optional[Union[DataDim, str]] = None) -> List[str]:
        """Return full names (origin/name) of probed data, optionally filtered by dim.

        Parameters
        ----------
        dim: str, optional
            One of 'Data0D', 'Data1D', 'Data2D', 'DataND'. If None, all dims are returned.

        Returns
        -------
        list of str
        """
        names = []
        dim_enum = enum_checker(DataDim, dim) if dim is not None else None
        for det_param in self.settings.child('probe_detectors_results').children():
            if dim_enum is None or det_param.name() == dim_enum.name:
                names.extend([child.name() for child in det_param.children()])
        return names

    def _grab_data(self, check_do_override: bool = True, Naverage: Optional[int] = None, **kwargs: Any) -> None:
        self.det_done_datas = DataToExport(name=__class__.__name__, control_module='DAQ_Viewer')  # type: ignore[name-defined]
        self._received_data = 0
        self.det_done_flag = False
        self.settings.child('probe_detectors').setValue(self.det_done_flag)

        if check_do_override and 'DataMixer' in self.selected_detectors_name:
            overridden_detectors = cast('DAQ_Viewer', self.get_mod_from_name(
                'DataMixer', ModuleType.Detector)).settings.child(
                DETECTOR_SETTINGS_KEY, 'overridden_detectors').opts['limits']
        else:
            overridden_detectors = []

        for mod in self.detectors:
            if mod.title not in overridden_detectors:
                kwargs.update(dict(Naverage=Naverage if Naverage is not None else mod.Naverage))
                mod.command_hardware.emit(utils.ThreadCommand(ControlToHardwareViewer.SINGLE, kwargs))

    def _arm_callback(self, timeout_timer: QTimer, interval_ms: float, done_signal: Signal,
                      callback: Callable, connect_modules: Callable[[bool], Any],
                      do_connect_modules: bool):
        """ Shared preamble: watch `done_signal` for `callback`, backed by `timeout_timer`,
        connecting the underlying modules first if asked. """
        timeout_timer.setInterval(int(interval_ms))
        timeout_timer.start()
        done_signal.connect(callback)
        if do_connect_modules:
            connect_modules(True)

    def _auto_forgetting(self, callback: Callable[[DataToExport], Any], module_type: ModuleType,
                         disconnect_modules: bool) -> Callable[[DataToExport], Any]:
        """ Wrap `callback` so forget_callback is called on its behalf, right before it runs.

        The wrapper is remembered so that forget_callback(callback) also disconnects it, for instance after a timeout.
        """
        def _wrapped(dte: DataToExport):
            self.forget_callback(_wrapped, module_type=module_type,
                                 disconnect_modules=disconnect_modules)
            callback(dte)
        self._auto_forgetting_wrappers.append((callback, _wrapped))
        return _wrapped

    def grab_data_with_callback(self,
                                check_do_override: bool = True,
                                Naverage: Optional[int] = None,
                                callback: Optional[Callable[[DataToExport], Any]] = None,
                                do_connect_modules: bool = True,
                                detach_after_callback: bool = True,
                                **kwargs: Any) -> None:
        """Do a single grab of the selected detectors and return immediately

        The callback is called with a DataToExport holding the data of all the selected detectors when the last one
        has answered. If a detector does not answer in time (config viewer/timeout), the callback is not called and
        the timeout_signal is emitted.

        Parameters
        ----------
        check_do_override: bool
            See grab_data
        Naverage: int, optional
            If provided, overrides each detector's own Naverage setting
        callback: callable, optional
            Connected to det_done_signal, it stays connected unless detach_after_callback is True: call
            forget_callback yourself when it has been called (or on a timeout)
        do_connect_modules: bool
            If True the selected detectors are connected to the manager (see connect_detectors), forget_callback
            disconnects them
        detach_after_callback: bool
            If True (default), forget_callback is called on your behalf right before callback runs

        See Also
        --------
        forget_callback, grab_data
        """
        if callback is not None:
            if detach_after_callback:
                callback = self._auto_forgetting(callback, ModuleType.Detector, do_connect_modules)
            self._arm_callback(self.detectors_timeout_timer, self.detector_timeout,
                               self.det_done_signal, callback, self.connect_detectors,
                               do_connect_modules)
        self._grab_data(check_do_override, Naverage, **kwargs)

    def _on_detectors_timeout(self) -> None:
        missing_detectors = self.get_missing_detectors()
        self.timeout_signal.emit(missing_detectors)
        logger.error('Timeout Fired during waiting for data to be acquired from: '
                     f'{", ".join(missing_detectors)}')

    def _on_actuators_timeout(self) -> None:
        missing_actuators = self.get_missing_actuators()
        self.timeout_signal.emit(missing_actuators)
        logger.error('Timeout Fired during waiting for data to be acquired from: '
                     f'{", ".join(missing_actuators)}')

    def grab_data(self, check_do_override: bool = True, Naverage: Optional[int] = None,
                  **kwargs: Any) -> DataToExport:
        """Do a single grab of connected and selected detectors

        Parameter
        ---------
        check_do_override: bool
            If this is True the signal emission to the DAQ_Viewers will be conditionned to the status of their internal
            override_grab_from_extension attribute
        Naverage: int, optional
            If provided, overrides each detector's own Naverage setting. Useful for probing data shape without averaging.
        """

        self._grab_data(check_do_override=check_do_override, Naverage=Naverage, **kwargs)

        tzero = time.perf_counter()
        while not self.det_done_flag:
            # wait for grab done signals to end
            QtWidgets.QApplication.processEvents()  # mandatory for the det_done_flag boolean to be modified in the corresponding method
            if time.perf_counter() - tzero > self.detector_timeout / 1000:
                missing_detectors = self.get_missing_detectors()
                self.timeout_signal.emit(self.get_missing_detectors())
                logger.error('Timeout Fired during waiting for data to be acquired from: '
                              f'{", ".join(missing_detectors)}')
                break
            QThread.msleep(10)

        return self.det_done_datas

    def get_missing_detectors(self) -> list[str]:
        """match on origin (stable per-module id) rather than name, since a single
        detector emits one DataWithAxes per channel, each possibly named differently
        """
        received_origins = {dwa.origin for dwa in self.det_done_datas}
        return [det_title for det_title in self.selected_detectors_name
                if det_title not in received_origins]

    def get_missing_actuators(self) -> list[str]:
        """ match on origin (stable per-module id) rather than name: dte_act's
         `.name` holds the requested actuator's title, which is what gets
         stamped as `.origin` on the DataActuator the actuator reports back
        """
        received_origins = {dwa.origin for dwa in self.move_done_positions}
        return [act_title for act_title in self.selected_actuators_name
                if act_title not in received_origins]

    def grab_datas(self, **kwargs: Any) -> DataToExport:
        """ For back compatibility but use self.grab_data"""
        return self.grab_data(**kwargs)

    def connect_actuators(self, connect: bool = True, slot: Optional[Callable[..., Any]] = None,
                          signal: str = 'move_done') -> None:
        """Connect the selected actuators signal to a given or default slot

        Parameters
        ----------
        connect: bool
            if True, connect the selected actuators, if False disconnect the selected actuators (the ones that are
            not selected anymore are not touched: disconnect before changing the selection)
        slot: builtin_function_or_method
            method or function the chosen signal will be connected to
            if None, then the default move_done slot is used
        signal: str
            What kind of signal is to be used:

            * 'move_done' will connect the `move_done_signal` to the slot
            * 'current_value' will connect the 'current_value_signal' to the slot

        See Also
        --------
        :meth:`move_done`
        """
        if slot is None:
            slot = self.move_done
        if connect:
            for sig in [mod.move_done_signal if signal == 'move_done' else mod.current_value_signal
                        for mod in self.actuators]:
                sig.connect(slot)

        else:

            for sig in [mod.move_done_signal if signal == 'move_done' else mod.current_value_signal
                        for mod in self.actuators]:
                try:
                    sig.disconnect(slot)
                except TypeError as e:
                    logger.error(str(e))

        self.actuators_connected = connect

    def connect_detectors(self, connect: bool = True, slot: Optional[Callable[..., Any]] = None) -> None:
        """
        Connect selected DAQ_Viewers's grab_done_signal to the given slot

        Parameters
        ----------
        connect: bool
            if True, connect the selected detectors to the given slot (or default slot)
            if False, disconnect the selected detectors from it. The detectors that are not selected
            anymore are not touched: if the selection changed since they were connected, they stay connected.
            Disconnect before changing the selection.
        slot: method
            A method that should be connected, if None self.det_done is connected by default
        """

        if slot is None:
            slot = self.det_done

        if connect:
            for sig in [mod.grab_done_signal for mod in self.detectors]:
                sig.connect(slot)
        else:

            for sig in [mod.grab_done_signal for mod in self.detectors]:
                try:
                    sig.disconnect(slot)
                except TypeError as e:
                    # means the slot was not previously connected
                    logger.info(f'Could not disconnect grab signal from the {slot} slot', stacklevel=2)

        self.detectors_connected = connect

    def probe_actuators(self) -> None:
        """Open a single dialog to set target positions for all selected actuators, move them,
        then populate the Actuators panel's result tree (probe_actuators_results)"""
        actuators = self.actuators
        if not actuators:
            return

        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle('Move actuators to target position')
        layout = QtWidgets.QVBoxLayout()
        form = QtWidgets.QFormLayout()

        spinboxes: dict[str, QtWidgets.QDoubleSpinBox] = {}
        for mod in actuators:
            spinbox = QtWidgets.QDoubleSpinBox()
            spinbox.setRange(-1e9, 1e9)
            spinbox.setDecimals(4)
            spinbox.setValue(mod._current_value.value())
            form.addRow(mod.title, spinbox)
            spinboxes[mod.title] = spinbox

        layout.addLayout(form)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setLayout(layout)

        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        dte_act = DataToExport('Actuators', control_module='DAQ_MOVE')
        for mod in actuators:
            dte_act.append(DataActuator(mod.title, data=spinboxes[mod.title].value()))

        with self._probing(self.connect_actuators, self._on_actuator_probe_timeout):
            self.move_actuators(dte_act)

        results = self.settings.child('probe_actuators_results')
        results.clearChildren()
        for dact in self.move_done_positions:
            results.addChild(
                {'title': dact.name, 'name': dact.name.replace(' ', '_'),
                 'type': 'float', 'value': dact.value(), 'readonly': True},
            )

    def test_move_actuators(self) -> None:
        """Deprecated alias for probe_actuators(), kept for backward compatibility."""
        warnings.warn(
            "test_move_actuators() is deprecated, use probe_actuators() instead",
            DeprecationWarning, stacklevel=2,
        )
        return self.probe_actuators()

    def connect_and_move_actuators(self, dte_act: DataToExport,
                                   mode: Union[MoveType, str] = MoveType.ABS,
                                   polling: bool = True,
                                   slot: Optional[Callable] = None,
                                   signal: str = 'move_done') -> DataToExport:
        """ Connect Actuators specified in the dte object and move them either absolute or relative to the
        given value

        Parameters
        ----------
        dte_act: DataToExport
            One DataActuator per actuator, named like the actuator. The actuators named in it become the selected ones
        mode: MoveType or str
            Absolute (default) or relative positioning
        polling: bool
            See move_actuators
        slot: callable, optional
            See connect_actuators
        signal: str
            See connect_actuators

        Returns
        -------
        DataToExport
            The positions reported by the actuators once the moves are done
        """
        self.selected_actuators_name = [dwa.name for dwa in dte_act]
        self.connect_actuators(True, slot=slot, signal=signal)

        dte = self.move_actuators(dte_act, mode=mode, polling=polling)
        self.connect_actuators(False)
        return dte

    def move_actuators_with_callback(self, dte_act: DataToExport | DataToActuators,
                                     mode: Union[MoveType, str] = MoveType.ABS,
                                     callback: Optional[Callable[[DataToExport], Any]] = None,
                                     do_connect_modules: bool = True,
                                     detach_after_callback: bool = True) -> None:
        """ Move actuators defined within a DataToExport to the value included in the DatActuators within

        The actuators named in dte_act become the selected ones. This method returns immediately and the callback is
        called with a DataToExport containing DataActuators when all the moves are done. If an actuator does not answer
        in time (config actuator/polling_timeout_s), the callback is not called and the timeout_signal is emitted.

        Parameters
        ----------
        dte_act: DataToExport or DataToActuators
            One DataActuator per actuator, named like the actuator. For a DataToActuators, its own mode is used.
        mode: MoveType or str
            Absolute (default) or relative positioning
        callback: callable, optional
            Connected to move_done_signal, it stays connected unless detach_after_callback is True: call
            forget_callback yourself when it has been called (or on a timeout)
        do_connect_modules: bool
            If True the selected actuators are connected to the manager (see connect_actuators), forget_callback
            disconnects them
        detach_after_callback: bool
            If True (default), forget_callback is called on your behalf right before callback runs

        See Also
        --------
        forget_callback, move_actuators
        """

        if isinstance(dte_act, DataToActuators):
            mode = dte_act.mode

        self.selected_actuators_name = [dwa.name for dwa in dte_act]
        if callback is not None:
            if detach_after_callback:
                callback = self._auto_forgetting(callback, ModuleType.Actuator, do_connect_modules)
            self._arm_callback(self.actuators_timeout_timer, self.actuator_timeout * 1000,
                               self.move_done_signal, callback, self.connect_actuators,
                               do_connect_modules)
        self._move_actuators(dte_act, mode=mode,)

    def forget_callback(self,
                        callback: Callable[..., Any],
                        module_type: ModuleType = ModuleType.Detector,
                        disconnect_modules: bool = True) -> None:
        """ to be called by the caller of self.move_actuators_with_callback or self.grab_data_with_callback
        in order to disconnect properly the callback


        Optionaly also disconnect each selected actuaor and/or detector to the inner method checking when each move/grab
        is done

        This also works for a callback given to a *_with_callback method with detach_after_callback=True, that has not
        been called (for instance because of a timeout).
        """
        callbacks = [callback]
        for original, wrapper in list(self._auto_forgetting_wrappers):
            if wrapper is callback:  # the wrapper is running or is forgotten directly, it is done with
                self._auto_forgetting_wrappers.remove((original, wrapper))
            elif original == callback:
                self._auto_forgetting_wrappers.remove((original, wrapper))
                callbacks.append(wrapper)

        if module_type == ModuleType.Detector or module_type==ModuleType.Control:
            if disconnect_modules:
                self.connect_detectors(False)
            for cb in callbacks:
                try:
                    self.det_done_signal.disconnect(cb)
                except TypeError:
                    pass

        if module_type == ModuleType.Actuator or module_type == ModuleType.Control:
            if disconnect_modules:
                self.connect_actuators(False)
            for cb in callbacks:
                try:
                    self.move_done_signal.disconnect(cb)
                except TypeError:
                    pass


    def _move_actuators(self, dte_act: DataToExport | DataToActuators,
                        mode: Union[MoveType, str] = MoveType.ABS) -> DataToExport:
        self.move_done_positions = DataToExport(name=__class__.__name__, control_module='DAQ_Move')  # type: ignore[name-defined]
        self.move_done_flag = False
        self.settings.child('probe_actuators').setValue(self.move_done_flag)

        if mode == MoveType.ABS:
            command = ControlToHardwareMove.MOVE_ABS
        elif mode == MoveType.REL:
            command = ControlToHardwareMove.MOVE_REL
        else:
            logger.error(f'Invalid positioning mode: {mode}')
            return self.move_done_positions

        if len(dte_act) == self.Nactuators:
            for dact in dte_act:
                act = self.get_mod_from_name(dact.name, ModuleType.Actuator)
                if act is not None:
                    act.command_hardware.emit(
                        utils.ThreadCommand(command=command, attribute=[dact, True]))
        else:
            logger.error('Invalid number of positions compared to selected actuators')
        return self.move_done_positions


    def move_actuators(self, dte_act: DataToExport,
                       mode: Union[MoveType, str] = MoveType.ABS,
                       polling: bool = True,
                       ) -> DataToExport:
        """Apply positions to each currently selected actuator. By default the mode is absolute.

        Deprecated, you should use move_actuators_with_callback to avoid using a polling mechanism which uses Qt event loop
        processevents in a while loop

        Parameters
        ----------
        dte_act: DataToExport
            the DataToExport of position to apply. Its length must be equal to the number of selected actuators
        mode: MoveType or str
            either MoveType.ABS ('abs') for absolute positioning or MoveType.REL ('rel') for relative
        polling: bool (should not be used, prefer the callback version)
            if True will wait for the selected actuators to reach their target positions (they have to be
            connected to a method checking for the position and letting the programm know the move is done (default
            connection is the ``move_done`` method of this object)

        Returns
        -------
        DataToExport with the selected actuators's name as key and current actuators's value as value
        """

        self._move_actuators(dte_act, mode)

        if polling:
            tzero = time.perf_counter()
            while not self.move_done_flag:  # polling move done

                QtWidgets.QApplication.processEvents()  # mandatory for the det_done_flag boolean to be modified in the corresponding method
                if time.perf_counter() - tzero > self.actuator_timeout:  # timeout in seconds
                    missing_actuators = self.get_missing_actuators()
                    self.timeout_signal.emit(missing_actuators)
                    logger.error('Timeout Fired during waiting for actuators to be moved: '
                                  f'{", ".join(missing_actuators)}')
                    break
                QThread.msleep(10)

        self.move_done_signal.emit(self.move_done_positions)
        return self.move_done_positions

    def raise_actuator_timeout(self, module_name: str) -> None:
        """Placeholder, does nothing (to be overridden if needed)"""

    def reset_signals(self) -> None:
        """Set the move and grab done flags so that the polling loops of move_actuators and grab_data end"""
        self.move_done_flag = True
        self.det_done_flag = True

    def order_positions(self, positions: DataToExport) -> DataToExport:
        """ Reorder the content of the DataToExport given the order of the selected actuators"""
        actuators = self.selected_actuators_name
        pos = DataToExport('actuators')
        for act in actuators:
            pos.append(positions.get_data_from_name(act))
        return pos

    @Slot(DataActuator)
    def move_done(self, data_act: DataActuator) -> None:
        """Default slot connected to the move_done_signal of the selected actuators

        Store the position of an actuator and emit move_done_signal once all the selected actuators have answered.
        """
        try:
            # match on origin, not name, for the same reason as in move_actuators above
            if data_act.origin not in {dact.origin for dact in self.move_done_positions}:
                self.move_done_positions.append(data_act)

            if len(self.move_done_positions) == len(self.actuators):
                self.actuators_timeout_timer.stop()
                self.move_done_flag = True
                self.settings.child('probe_actuators').setValue(self.move_done_flag)
                self.move_done_signal.emit(self.move_done_positions)

        except Exception as e:
            logger.exception(str(e))

    def det_done(self, data: DataToExport) -> None:
        """Default slot connected to the grab_done_signal of the selected detectors

        Store the data of a detector and emit det_done_signal once all the selected detectors have answered.
        """
        if self.det_done_datas is not None:  # means that somehow data are not initialized so no further processing
            self._received_data += 1
            if len(data) != 0:
                self.det_done_datas.append(data)

            if self._received_data == len(self.detectors):
                self.detectors_timeout_timer.stop()
                self.det_done_flag = True
                self.settings.child('probe_detectors').setValue(self.det_done_flag)
                self.det_done_signal.emit(self.det_done_datas)


if __name__ == '__main__':
    import sys

    from pymodaq_gui.qt_utils import mkQApp

    from pymodaq.dashboard import create_load_dashboard


    app = mkQApp('ModulesManager')

    win, dashboard = create_load_dashboard()
    win.show()

    dashboard.experiment_manager.execute_entry()

    dashboard.modules_manager.settings_tree.show()

    dashboard.modules_manager.get_det_data_list()

    print(dashboard.modules_manager.get_probed_data_full_names())

    sys.exit(app.exec())



from typing import List, Union, TYPE_CHECKING, Optional, Sequence

from qtpy.QtCore import QObject, Signal, Slot
from qtpy import QtWidgets
from qtpy.QtCore import QThread
import time

from pymodaq.utils.managers.modules.utils import ModuleType
from pymodaq_utils.enums import enum_checker
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import utils
from pymodaq_utils.config import GlobalConfig as Config

from pymodaq_data.data import DataToExport, DataSource, DataDim

from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.parameter import Parameter
from pymodaq_gui.utils import Dock

from pymodaq.utils.data import DataActuator

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
    detectors_changed = Signal(list)
    actuators_changed = Signal(list)
    det_done_signal = Signal(DataToExport)  # dte here contains DataWithAxes
    move_done_signal = Signal(DataToExport)  # dte here contains DataActuators
    timeout_signal = Signal(bool)

    params = [
        {'title': 'Detectors', 'name': 'detectors', 'type': 'itemselect', 'checkbox': True},
        {'title': 'Actuators', 'name': 'actuators', 'type': 'itemselect', 'checkbox': True},

        {'title': "Probe detectors", 'name': 'probe_data', 'type': 'action_led', 'value': False, 'children': []},
        {'title': "Probe actuators", 'name': 'test_actuator', 'type': 'action_led', 'value': False, 'children': []},
    ]

    def __init__(self,
                 detectors: Optional[Sequence['DAQ_Viewer']] = None,
                 actuators: Optional[Sequence['DAQ_Move']] = None,
                 selected_detectors: Optional[Sequence['DAQ_Viewer']] = None,
                 selected_actuators: Optional[Sequence['DAQ_Move']] = None,
                 parent_name='',
                 **kwargs):

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

        self.parent_name = parent_name

        for mod in selected_actuators:
            assert mod in actuators
        for mod in selected_detectors:
            assert mod in detectors

        self.det_done_datas: DataToExport = None
        self.det_done_flag = False
        self.move_done_positions: DataToExport = None
        self.move_done_flag = False

        self.settings.child('probe_data').sigActivated.connect(self.get_det_data_list)
        self.settings.child('test_actuator').sigActivated.connect(self.test_move_actuators)

        self._detectors = []
        self._actuators = []

        self.actuators_connected = False
        self.detectors_connected = False

        self.set_actuators(actuators, selected_actuators)
        self.set_detectors(detectors, selected_detectors)

    @property
    def actuator_timeout(self):
        return config('pymodaq', 'actuator', 'timeout')

    @property
    def detector_timeout(self):
        return config('pymodaq', 'viewer', 'timeout')

    def __repr__(self):
        return f'ModulesManager of "{self.parent_name}" with control modules: {self.get_names(self.modules_all)}'

    def show_only_control_modules(self, show: True):
        self.settings.child('probe_data').show(not show)
        self.settings.child('test_actuator').show(not show)

    @classmethod
    def get_names(cls, modules:  list[Union['DAQ_Move', 'DAQ_Viewer']]):
        """Get the titles of a list of Control Modules

        Parameters
        ----------
        modules: list of DAQ_Move and/or DAQ_Viewer
        """
        if not hasattr(modules, '__iter__'):
            modules = [modules]
        return [mod.title for mod in modules]

    def get_mods_from_names(self, names, mod=ModuleType.Detector) -> List[Union['DAQ_Move', 'DAQ_Viewer']]:
        """Getter of a list of given modules from their name (title)

        Parameters
        ----------
        names: list of str
        mod: str
            either ModuleType.Detector for DAQ_Viewer modules or ModuleType.Actuator for DAQ_Move modules
        """
        mods = []
        for name in names:
            d = self.get_mod_from_name(name, mod)
            if d is not None:
                mods.append(d)
        return mods

    def get_mod_from_name(self, name, mod=ModuleType.Detector) -> Union['DAQ_Move', 'DAQ_Viewer', None]:
        """Getter of a given module from its name (title)

        Returns None is no control module with this name exists

        Parameters
        ----------
        name: str
        mod: str
            either ModuleType.Detector for DAQ_Viewer modules or ModuleType.Actuator for DAQ_Move modules
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

    def set_actuators(self, actuators: list['DAQ_Move'], selected_actuators: list['DAQ_Move']):
        """Populates actuators and the subset to be selected in the UI"""
        self._actuators = actuators
        self.settings.child('actuators').setValue(dict(all_items=self.get_names(actuators),
                                                       selected=self.get_names(selected_actuators)))

    def set_detectors(self, detectors: list['DAQ_Viewer'], selected_detectors: list['DAQ_Viewer']):
        """Populates detectors and the subset to be selected in the UI"""
        self._detectors = detectors
        self.settings.child('detectors').setValue(dict(all_items=self.get_names(detectors),
                                                       selected=self.get_names(selected_detectors)))

    @property
    def detectors(self) -> List['DAQ_Viewer']:
        """Get the list of selected detectors"""
        return self.get_mods_from_names(self.selected_detectors_name)

    @property
    def detectors_all(self)  -> List['DAQ_Viewer']:
        """Get/Set the list of all detectors"""
        return self._detectors

    @detectors_all.setter
    def detectors_all(self, detectors: List['DAQ_Viewer']):
        self.set_detectors(detectors, [])

    @property
    def actuators(self) -> List['DAQ_Move']:
        """Get the list of selected actuators"""
        return self.get_mods_from_names(self.selected_actuators_name, mod=ModuleType.Actuator)

    @property
    def actuators_all(self):
        """Get the list of all actuators"""
        return self._actuators

    @actuators_all.setter
    def actuators_all(self, actuators: List['DAQ_Move']):
        self.set_actuators(actuators, [])

    @property
    def modules(self):
        """Get the list of detectors and actuators"""
        return self.detectors + self.actuators

    @property
    def modules_all(self):
        """Get the list of all detectors and actuators"""
        return self.detectors_all + self.actuators_all

    @property
    def Ndetectors(self):
        """Get the number of selected detectors"""
        return len(self.detectors)

    @property
    def Nactuators(self):
        """Get the number of selected actuators"""
        return len(self.actuators)

    @property
    def detectors_name(self):
        """Get all the names of the detectors"""
        return self.settings.child('detectors').value()['all_items']

    @property
    def selected_detectors_name(self):
        """Get/Set the names of the selected detectors"""
        return self.settings.child('detectors').value()['selected']

    @selected_detectors_name.setter
    def selected_detectors_name(self, detectors):
        if set(detectors).issubset(self.detectors_name):
            self.settings.child('detectors').setValue(dict(all_items=self.detectors_name,
                                                           selected=detectors))

    @property
    def actuators_name(self):
        """Get all the names of the actuators"""
        return self.settings.child('actuators').value()['all_items']

    @property
    def selected_actuators_name(self) -> List[str]:
        """Get/Set the names of the selected actuators"""
        return self.settings.child('actuators').value()['selected']

    @selected_actuators_name.setter
    def selected_actuators_name(self, actuators):
        if set(actuators).issubset(self.actuators_name):
            self.settings.child('actuators').setValue(dict(all_items=self.actuators_name,
                                                           selected=actuators))

    def value_changed(self, param):
        if param.name() == 'detectors':
            self.detectors_changed.emit(param.value()['selected'])

        elif param.name() == 'actuators':
            self.actuators_changed.emit(param.value()['selected'])

    def get_det_data_list(self, add_to_this_param: Parameter = None) -> DataToExport:
        """Do a snap of selected detectors, to populate the data channels tree and return the data"""

        if len(self.detectors) == 0:
            return DataToExport(name=__class__.__name__, control_module='DAQ_Viewer')

        if add_to_this_param is None:
            add_to_this_param = self.settings.child('probe_data')

        self.connect_detectors()
        try:
            datas: DataToExport = self.grab_data(Naverage=1)
            logger.debug(f'Acquired: {datas.get_full_names()}')

            add_to_this_param.clearChildren()

            data_children = []

            for data_dim in DataDim.names():
                data_from_dim = datas.get_data_from_dim(data_dim)
                if len(data_from_dim) != 0:
                    data_children.append(
                        {'title': data_dim, 'name': data_dim, 'type': 'group', 'children':[
                            {'title': dwa.origin, 'name': dwa.get_full_name(), 'type': 'str',
                             'value': dwa.name, 'readonly': True} for dwa in data_from_dim
                        ]})
            add_to_this_param.addChildren(data_children)
        finally:
            self.connect_detectors(False)
        return datas

    def get_probed_data_full_names(self, dim: DataDim | str = None) -> List[str]:
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
        if dim is not None:
            dim = enum_checker(DataDim, dim)
        for det_param in self.settings.child('probe_data').children():
            if dim is None or det_param.name() == dim.name:
                names.extend([child.name() for child in det_param.children()])
        return names

    def grab_data(self, check_do_override=True, Naverage: Optional[int] = None, **kwargs):
        """Do a single grab of connected and selected detectors

        Parameter
        ---------
        check_do_override: bool
            If this is True the signal emission to the DAQ_Viewers will be conditionned to the status of their internal
            override_grab_from_extension attribute
        Naverage: int, optional
            If provided, overrides each detector's own Naverage setting. Useful for probing data shape without averaging.
        """
        self.det_done_datas = DataToExport(name=__class__.__name__, control_module='DAQ_Viewer')
        self._received_data = 0
        self.det_done_flag = False
        self.settings.child('probe_data').setValue(self.det_done_flag)
        tzero = time.perf_counter()
        
        if check_do_override and 'DataMixer' in self.selected_detectors_name:
            overridden_detectors = self.get_mod_from_name(
                'DataMixer', ModuleType.Detector).settings.child(
                'detector_settings', 'overridden_detectors').opts['limits']
        else:
            overridden_detectors = []

        for mod in self.detectors:
            if mod.title not in overridden_detectors:
                kwargs.update(dict(Naverage=Naverage if Naverage is not None else mod.Naverage))
                mod.command_hardware.emit(utils.ThreadCommand("single", kwargs))

        while not self.det_done_flag:
            # wait for grab done signals to end
            QtWidgets.QApplication.processEvents()  # mandatory for the det_done_flag boolean to be modified in the corresponding method
            if time.perf_counter() - tzero > self.detector_timeout / 1000:
                self.timeout_signal.emit(True)
                logger.error('Timeout Fired during waiting for data to be acquired')
                break
            QThread.msleep(10)

        self.det_done_signal.emit(self.det_done_datas)
        return self.det_done_datas

    def grab_datas(self, **kwargs):
        """ For back compatibility but use self.grab_data"""
        return self.grab_data(**kwargs)

    def connect_actuators(self, connect=True, slot=None, signal='move_done'):
        """Connect the selected actuators signal to a given or default slot

        Parameters
        ----------
        connect: bool
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
            try:
                for sig in [mod.move_done_signal if signal == 'move_done' else mod.current_value_signal
                            for mod in self.actuators]:
                    sig.disconnect(slot)
            except Exception as e:
                logger.error(str(e))

        self.actuators_connected = connect

    def connect_detectors(self, connect=True, slot=None):
        """
        Connect selected DAQ_Viewers's grab_done_signal to the given slot

        Parameters
        ----------
        connect: bool
            if True, connect to the given slot (or default slot)
            if False, disconnect all detectors (not only the currently selected ones.
            This is made because when selected detectors changed if you only disconnect those one,
            the previously connected ones will stay connected)
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

    def test_move_actuators(self):
        """Open a single dialog to set target positions for all selected actuators, then move them"""
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
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
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

        self.connect_actuators()
        self.move_actuators(dte_act)
        self.connect_actuators(False)

        test_actuator = self.settings.child('test_actuator')
        test_actuator.clearChildren()
        for dact in self.move_done_positions:
            test_actuator.addChild(
                {'title': dact.name, 'name': dact.name.replace(' ', '_'),
                 'type': 'float', 'value': dact.value(), 'readonly': True}
            )


    def connect_and_move_actuators(self, dte_act: DataToExport, mode='abs', polling=True,
                                   slot=None, signal='move_done') -> DataToExport:
        """ Connect Actuators specified in the dte object and move them either absolute or relative to the
        given value
        """
        self.selected_actuators_name = [dwa.name for dwa in dte_act]
        self.connect_actuators(True, slot=slot, signal=signal)

        dte = self.move_actuators(dte_act, mode=mode, polling=polling)
        self.connect_actuators(False)
        return dte

    def move_actuators(self, dte_act: DataToExport, mode='abs', polling=True) -> DataToExport:
        """will apply positions to each currently selected actuators. By Default the mode is absolute but can be

        Parameters
        ----------
        dte_act: DataToExport
            the DataToExport of position to apply. Its length must be equal to the number of selected actuators
        mode: str
            either 'abs' for absolute positionning or 'rel' for relative
        polling: bool
            if True will wait for the selected actuators to reach their target positions (they have to be
            connected to a method checking for the position and letting the programm know the move is done (default
            connection is this object `move_done` method)

        Returns
        -------
        DataToExport with the selected actuators's name as key and current actuators's value as value
        """
        self.move_done_positions = DataToExport(name=__class__.__name__, control_module='DAQ_Move')
        self.move_done_flag = False
        self.settings.child('test_actuator').setValue(self.move_done_flag)

        if mode == 'abs':
            command = 'move_abs'
        elif mode == 'rel':
            command = 'move_rel'
        else:
            logger.error(f'Invalid positioning mode: {mode}')
            return self.move_done_positions

        if len(dte_act) == self.Nactuators:
            for dact in dte_act:
                act = self.get_mod_from_name(dact.name, ModuleType.Actuator)
                if act is not None:
                    act.command_hardware.emit(
                        utils.ThreadCommand(command=command, attribute=[dact, polling]))
        else:
            logger.error('Invalid number of positions compared to selected actuators')
            return self.move_done_positions

        tzero = time.perf_counter()
        if polling:
            while not self.move_done_flag:  # polling move done

                QtWidgets.QApplication.processEvents()  # mandatory for the det_done_flag boolean to be modified in the corresponding method
                if time.perf_counter() - tzero > self.actuator_timeout / 1000:  # timeout in seconds
                    self.timeout_signal.emit(True)
                    logger.error('Timeout Fired during waiting for actuators to be moved')
                    break
                QThread.msleep(10)

        self.move_done_signal.emit(self.move_done_positions)
        return self.move_done_positions

    def reset_signals(self):
        self.move_done_flag = True
        self.det_done_flag = True

    def poll_init(self, module):
        tstart = time.perf_counter()
        while not module.initialized_state:
            QThread.msleep(1000)
            QtWidgets.QApplication.processEvents()
            if time.perf_counter() - tstart > config('pymodaq', 'control_module_ini_polling'):  # timeout of 60sec
                break
        return module.initialized_state

    def order_positions(self, positions: DataToExport):
        """ Reorder the content of the DataToExport given the order of the selected actuators"""
        actuators = self.selected_actuators_name
        pos = DataToExport('actuators')
        for act in actuators:
            pos.append(positions.get_data_from_name(act))
        return pos

    @Slot(DataActuator)
    def move_done(self, data_act: DataActuator):
        try:
            if data_act.name not in self.move_done_positions.get_names():
                self.move_done_positions.append(data_act)

            if len(self.move_done_positions) == len(self.actuators):
                self.move_done_flag = True
                self.settings.child('test_actuator').setValue(self.move_done_flag)
        except Exception as e:
            logger.exception(str(e))

    def det_done(self, data: DataToExport):
        if self.det_done_datas is not None:  # means that somehow data are not initialized so no further processing
            self._received_data += 1
            if len(data) != 0:
                self.det_done_datas.append(data)

            if self._received_data == len(self.detectors):
                self.det_done_flag = True
                self.settings.child('probe_data').setValue(self.det_done_flag)


if __name__ == '__main__':
    import sys

    from pymodaq_gui.qt_utils import mkQApp

    from pymodaq.dashboard import create_load_dashboard


    app = mkQApp('ModulesManager')

    win, dashboard = create_load_dashboard()
    win.show()

    dashboard.preset_manager.execute_entry()

    dashboard.modules_manager.settings_tree.show()

    dashboard.modules_manager.get_det_data_list()

    print(dashboard.modules_manager.get_probed_data_full_names())

    sys.exit(app.exec())

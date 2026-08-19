from typing import Any, TYPE_CHECKING

import qtpy
from qtpy import QtCore

from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.utils.exceptions import MasterSlaveError
from pymodaq.utils.managers.modules import ModuleType

from pymodaq_utils.logger import set_logger, get_module_name

if TYPE_CHECKING:
    from pymodaq.utils.managers.experiment.experiment_manager import ExperimentManager, PluginInfo

if qtpy.PYQT6:
    from PyQt6.QtStateMachine import QStateMachine, QState, QFinalState, QSignalTransition
elif qtpy.PYSIDE6:
    from qtpy.QtStateMachine import QStateMachine, QState, QFinalState, QSignalTransition
elif qtpy.PYQT5:
    from PyQt5.QtCore.QtStateMachine import QStateMachine, QState, QFinalState, QSignalTransition


logger = set_logger(get_module_name(__file__))


class MyState(QState):
    def __init__(self, parent=None, name: str = None):
        super().__init__(parent)

        if name is not None:
            self.setObjectName(name)

        self.incoming_transition: ValueTransition | None = None  # This will hold the transition object
        self.source_state: MyState | None = None

    def onEntry(self, event, /):
        logger.debug(f'Entering {self.objectName()}')
        super().onEntry(event, )

    def onExit(self, event, /):
        logger.debug(f'Exiting {self.objectName()}')
        super().onExit(event, )


class MyFinalState(QFinalState):
    def __init__(self, parent=None, name: str = None):
        super().__init__(parent)
        if name is not None:
            self.setObjectName(name)
        self.incoming_transition: ValueTransition | None = None  # This will hold the transition object
        self.source_state: MyState | None = None

    def onEntry(self, event, /):
        logger.debug(f'Entering  {self.objectName()}')

    def onExit(self, event, /):
        logger.debug(f'Exiting {self.objectName()}')


class ValueTransition(QSignalTransition):
    def __init__(self, signal: QtCore.Signal,
                 value: Any,
                 source_state: MyState,
                 target_state: MyState = None, ):
        super().__init__(signal, source_state, target_state)
        self.value = value

    def eventTest(self, event: QStateMachine.SignalEvent) -> bool:
        if not super().eventTest(event):
            return False

        arguments = event.arguments()
        if arguments:
            value = arguments[0]
            return value == self.value
        return False


class CreateAddModulesMachine(QtCore.QObject):

    instrument_created = QtCore.Signal()
    all_instruments_added = QtCore.Signal()
    module_added = QtCore.Signal()
    controller_obtained = QtCore.Signal()

    def __init__(self, manager: 'ExperimentManager', plugins: list[list['PluginInfo']], parent=None):
        super().__init__(parent)
        self.manager = manager

        self._current_module: DAQ_Move | DAQ_Viewer = None
        self._current_plugin: PluginInfo = None
        self._current_controller: Any = None

        self.machine = QStateMachine()
        self.create_module_state = MyState(name='Create Module State')
        self.set_module_type_state = MyState(name='Set Module State')
        self.add_module_state = MyState(name='Add Module State')
        self.init_module_state = MyState(name='Init Module State')
        self.get_controller_state = MyState(name='Get Controller State')
        self.done_module_state = MyFinalState(name='Done State')

        self.setup_machine()
        self.plugins = plugins
        self.ind_master_plugin = 0
        self.ind_id_plugin = 0
        self._ind_module = -1

    def start(self):
        self.machine.start()

    def setup_machine(self):

        self.machine.addState(self.create_module_state)
        self.machine.addState(self.set_module_type_state)
        self.machine.addState(self.add_module_state)
        self.machine.addState(self.init_module_state)
        self.machine.addState(self.get_controller_state)
        self.machine.addState(self.done_module_state)
        self.machine.setInitialState(self.create_module_state)

        self.create_module_state.entered.connect(self.create_module)
        self.set_module_type_state.entered.connect(self.set_module_type)
        self.add_module_state.entered.connect(self.add_module)
        self.init_module_state.entered.connect(self.init_module)
        self.get_controller_state.entered.connect(self.get_controller)


        self.create_module_state.addTransition(self.instrument_created,
                                               self.set_module_type_state)
        self.add_module_state.addTransition(self.module_added, self.init_module_state)
        self.get_controller_state.addTransition(self.controller_obtained, self.create_module_state)
        self.done_module_state.entered.connect(self.all_instruments_added.emit)

    def create_module(self):
        if self.ind_master_plugin == len(self.plugins):
            self.manager.close_subentries_display()
            self.create_module_state.addTransition(self.done_module_state)  # immediately transitioning
            return

        self._current_plugin: PluginInfo = self.plugins[self.ind_master_plugin][self.ind_id_plugin]
        plugin_info = self._current_plugin

        if self._current_plugin.is_master and not self._current_plugin.do_init:
            self.machine.stop()
            raise MasterSlaveError(
                                f"The instrument {plugin_info.name} defined as Master has to be "
                                f"initialized (init checked in the experiment) in order to init "
                                f"its associated slave instrument",
                            )
        elif self._current_plugin.is_master and self.ind_id_plugin > 0:
            self.machine.stop()
            raise MasterSlaveError(
                f"The instrument {plugin_info.name} should be defined as Slave",
            )
        elif not self._current_plugin.is_master and self.ind_id_plugin == 0:
            self.machine.stop()
            raise MasterSlaveError(
                f"The instrument {plugin_info.name} should be defined as Master",
            )

        # loop through all the plugin info (first by common id, then...)
        if self.ind_id_plugin == len(self.plugins[self.ind_master_plugin]) - 1:
            self.ind_master_plugin += 1
            self.ind_id_plugin = 0
        else:
            self.ind_id_plugin += 1
        self._ind_module += 1

        # clear previous transitions dependent on created module if any before changing the reference of self._current_module
        for transition in self.set_module_type_state.transitions():
            self.set_module_type_state.removeTransition(transition)
        for transition in self.init_module_state.transitions():
            self.init_module_state.removeTransition(transition)

        # create module
        if plugin_info.type == ModuleType.Actuator:
            self._current_module = self.manager.dashboard.create_actuator(
                plugin_info.name, plugin_info.class_name,
                ui_identifier=plugin_info.ui)
            self.manager.actuators_modules.append(self._current_module)

        elif plugin_info.type == ModuleType.Detector:
            self._current_module = self.manager.dashboard.create_detector(plugin_info.name,
                                                                          plugin_info.daq_type)
            self.manager.detector_modules.append(self._current_module)

        # create next transitions if module dependent
        self.set_module_type_state.addTransition(self._current_module.instrument_changed, self.add_module_state)
        self.init_module_state.addTransition(self._current_module.init_signal, self.get_controller_state)

        # fire signal to move on to the set_type state
        self.instrument_created.emit()

    def set_module_type(self):
        if self._current_plugin.type == ModuleType.Actuator:
            self.manager.dashboard.set_actuator_type(self._current_module, self._current_plugin.class_name)
        else:
            self.manager.dashboard.set_detector_type(self._current_module,
                                                     self._current_plugin.daq_type,
                                                     self._current_plugin.class_name)

        # signal to transition to next state is done within each module through its instrument_changed signal

    def add_module(self):
        if self._current_plugin.type == ModuleType.Actuator:
            self.manager.dashboard.add_actuator(self._current_module)
        else:
            self.manager.dashboard.add_detector(self._current_module)

        #manually fire the signal to transition
        self.module_added.emit()

    def init_module(self):
        self._current_module.apply_controller_parameters(self._current_plugin.settings.child("controller"))

        if not self._current_plugin.is_master:
            self._current_module.controller = self._current_controller
        self._current_module.init_hardware_ui()

    def get_controller(self):
        if self._current_plugin.is_master and self._current_module.initialized_state:
            self._current_controller = self._current_module.controller
        self.manager.subentries_model.set_status(self._ind_module,
                                                 self._current_module.initialized_state)
        self.controller_obtained.emit()

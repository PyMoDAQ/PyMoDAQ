from dataclasses import dataclass

from pymodaq.control_modules.enums import MoveType
from pymodaq.control_modules.move_utility_classes import HW_SETTINGS_KEY as ACTUATOR_SETTINGS_KEY
import time
from typing import Callable, TYPE_CHECKING, Union, Tuple

from qtpy import QtWidgets, QtCore
from serializall import SerializableFactory

from pymodaq_utils.enums import StrEnum
from pymodaq_utils.abstract import abstract_attribute

from pymodaq_data import DataToExport

from pymodaq_gui.utils.widgets import SpinBox
from pymodaq_gui.parameter.utils import Parameter, ParameterWithPath

from pymodaq.utils.data import DataActuator, DataToActuators

from pymodaq.utils.managers.modules.modules_manager import ModuleType
from pymodaq_utils.enums import StrEnum
from pymodaq.utils.managers.modules_manager import ModuleType
from pymodaq.extensions import ExtensionEnum
from pymodaq_gui.managers.settings.subentries import (
    SubEntryError,  # noqa
    SubEntry, SubEntryHandlerFactory,
    SubEntryHandler)

ser_factory = SerializableFactory()


if TYPE_CHECKING:
    from pymodaq.utils.managers.state.utils import StateModel
    from pymodaq.control_modules.daq_move import DAQ_Move
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer
    from pymodaq.dashboard import DashBoard



class StateSubEntryHandlerTypes(StrEnum):
    SETTINGS = 'StateSettings'
    ACTUATOR_VALUE = 'Actuator Value'
    INIT = 'Init. Module'
    WAIT = 'Waiting Time'
    STOP = 'Stop Module'
    STOP_ALL = 'Stop All Control Modules'
    STOP_EXTENSION = 'Stop Extension'


class StateSubEntryHandler(SubEntryHandler):

    def __init__(self,
                 model: 'StateModel',
                 settings: Parameter,
                 actuators: list[str] = None,
                 detectors: list[str] = None,
                 extensions: list[str] = None,
                 dashboard: 'DashBoard' = None
                 ):

        super().__init__(model, settings)
        self.actuators: list[str] = actuators if actuators is not None else []
        self.detectors: list[str] = detectors if detectors is not None else []
        self.extensions: list[str] = extensions if extensions is not None else []
        self.dashboard = dashboard

    @staticmethod
    def get_module(entry: SubEntry, dashboard: 'DashBoard') -> Union['DAQ_Move', 'DAQ_Viewer']:
        """ Get the Module on which the settings will be applied

        To be reimplemented
        """
        return dashboard.modules_manager.get_mod_from_name(entry.module_name, ModuleType.Control)



@SubEntryHandlerFactory.register_handler()
class StateSettingsEntryHandler(StateSubEntryHandler):

    handler_name = StateSubEntryHandlerTypes.SETTINGS
    use_dialog = False

    def execute_subentry(self, entry: SubEntry, dashboard: 'DashBoard'):
        """ Execute the given subentry

        In general, should get first the module on which the settings will be applied
        Then apply the Settings subentry to this module

        Examples
        --------
        module = self.get_module(entry, *args, **kwargs)
        module.settings.child(*entry.setting.path).setValue(entry.setting.value())
        """
        module = self.get_module(entry, dashboard)
        module.settings.child(*entry.setting.path[3:]).setValue(entry.setting.value())
        self.executed_signal.emit()


@SubEntryHandlerFactory.register_handler()
class ActuatorValueSubEntryHandler(StateSubEntryHandler):

    handler_name = StateSubEntryHandlerTypes.ACTUATOR_VALUE

    def setup_widgets(self):
        self.actuator_cb = QtWidgets.QComboBox()
        self.actuator_cb.addItems(self.actuators)
        self.value_sb = SpinBox(suffix=self.get_units_from_module_name(self.actuators[0]), siPrefix=True)
        self.actuator_cb.currentTextChanged.connect(self.update_suffix_in_dialog)

        self.widget.layout().addWidget(self.actuator_cb)
        self.widget.layout().addWidget(self.value_sb)

    def get_units_from_module_name(self, actuator_name: str):

        module = self.dashboard.modules_manager.get_mod_from_name(actuator_name, ModuleType.Actuator)
        if module is not None:
            units = module.get_unit_to_display(module.units)
        else:
            mods_settings = [group.child('name').value() for
                             group in self.settings.child(ModuleType.Actuator).children()]
            actuator_settings = self.settings.child(ModuleType.Actuator).children()[
                mods_settings.index(actuator_name)]
            units = actuator_settings.child(ACTUATOR_SETTINGS_KEY, 'units').value()
        return units

    def update_suffix_in_dialog(self, actuator_name: str):
        self.value_sb.setOpts(suffix=self.get_units_from_module_name(actuator_name))

    def get_subentry_from_dialog(self) -> SubEntry:
        return SubEntry(
            self.handler_name,
            self.actuator_cb.currentText(),
            setting=ParameterWithPath(
                parameter=Parameter.create(
                    title='Actuator Value',
                    name=''.join(self.handler_name.split(' ')),
                    type='float',
                    value=self.value_sb.value(),
                    suffix=self.value_sb.opts['suffix']),
            path=()))

    def execute_subentry(self, entry: SubEntry, dashboard: 'DashBoard'):
        """ Execute the given subentry """
        self._dashboard = dashboard
        module = self.get_module(entry, dashboard)
        if not module.initialized_state:
            raise SubEntryError('Could not move an actuator that is not initialized')
        try:
            units = entry.setting.parameter.opts.get('suffix', None)
            if units is None or units == '':
                units = module.units
            dte_actuators = DataToExport('actuators', data=[
                DataActuator(entry.module_name, data=entry.setting.parameter.value(),
                             units=units)])

            dashboard.modules_manager.timeout_signal.connect(self._on_timeout)
            dashboard.modules_manager.move_actuators_with_callback(dte_actuators,
                                                                   mode=MoveType.ABS,
                                                                   callback=self._on_move_done,
                                                                   do_connect_modules=True)

            dashboard.modules_manager.move(dte_actuators)

        except Exception as e:
            self.execution_failed.emit(e)
            dashboard.modules_manager.timeout_signal.disconnect(self._on_timeout)

    def _on_move_done(self):
        self._dashboard.modules_manager.timeout_signal.disconnect(self._on_timeout)
        self._dashboard.modules_manager.forget_callback(self._on_move_done, disconnect_modules=True)
        self.executed_signal.emit()

    def _on_timeout(self):
        self._dashboard.modules_manager.timeout_signal.disconnect(self._on_timeout)
        self.execution_failed.emit(SubEntryError('Timeout while waiting for actuators to be moved'))


@SubEntryHandlerFactory.register_handler()
class InitSubEntryHandler(StateSubEntryHandler):
    handler_name = StateSubEntryHandlerTypes.INIT

    def setup_widgets(self):
        self.control_module_cb = QtWidgets.QComboBox()
        self.control_module_cb.addItems(self.actuators + self.detectors)
        self.init_cb = QtWidgets.QCheckBox()

        self.widget.layout().addWidget(self.control_module_cb)
        self.widget.layout().addWidget(self.init_cb)

    def get_subentry_from_dialog(self) -> SubEntry:

        module_name = self.control_module_cb.currentText()
        module_type = ModuleType.Actuator if module_name in self.actuators else ModuleType.Detector
        return SubEntry(
            self.handler_name,
            module_name,
            setting=ParameterWithPath(
                parameter=Parameter.create(title='Control Module Init Value',
                                           name=''.join(self.handler_name.split(' ')),
                                           type='bool',
                                           value=True if self.init_cb.checkState() ==
                                                         QtCore.Qt.CheckState.Checked else False,
                                                   )))

    def execute_subentry(self, entry: SubEntry, dashboard: 'DashBoard'):
        """ Execute the given subentry """
        self._entry = entry
        self._dashboard = dashboard
        module = self.get_module(entry, dashboard)
        if module.initialized_state == entry.setting.value():
            raise SubEntryError(
                f'The {entry.module_name} module is already '
                f'{"initialized" if module.initialized_state else "uninitialized"}')
        try:
            module.init_signal.connect(self._on_module_initialization)
            module.init_hardware_ui(entry.setting.value())
        except Exception as e:
            self.execution_failed.emit(e)

    def _on_module_initialization(self, initialized: bool):
        module = self.get_module(self._entry, self._dashboard)
        module.init_signal.disconnect(self._on_module_initialization)
        if initialized != self._entry.setting.value():
            self.execution_failed.emit(ValueError('Could not initialize the module'))
        else:
            self.executed_signal.emit()


@SubEntryHandlerFactory.register_handler()
class WaitSubEntryHandler(StateSubEntryHandler):
    handler_name = StateSubEntryHandlerTypes.WAIT

    def setup_widgets(self):
        label = QtWidgets.QLabel('Waiting Time:')
        self.wait_time_sb = SpinBox(suffix='s', siPrefix=True)
        self.wait_time_sb.setValue(0.1)

        self.widget.layout().addWidget(label)
        self.widget.layout().addWidget(self.wait_time_sb)

    def get_subentry_from_dialog(self) -> SubEntry:

        return SubEntry(
            self.handler_name,
            str(ModuleType.NONE),
            setting=ParameterWithPath(
                parameter=Parameter.create(title='Waiting Time',
                                           name=''.join(self.handler_name.split(' ')),
                                           type='float',
                                           value=self.wait_time_sb.value(),
                                           suffix='s',
                                           siPrefix=True,
                                           )))

    def execute_subentry(self, entry: SubEntry, dashboard: 'DashBoard'):
        """ Execute the given subentry """
        QtCore.QTimer.singleShot(int(entry.setting.value()),
                                 self._on_wait_time_done)

    def _on_wait_time_done(self):
        self.executed_signal.emit()


@SubEntryHandlerFactory.register_handler()
class StopSubEntryHandler(StateSubEntryHandler):
    handler_name = StateSubEntryHandlerTypes.STOP

    def setup_widgets(self):
        label = QtWidgets.QLabel('Stop Module:')
        self.module_cb = QtWidgets.QComboBox()
        self.module_cb.addItems(self.actuators + self.detectors)
        self.stop_bool = QtWidgets.QCheckBox()
        self.stop_bool.setChecked(True)
        self.widget.layout().addWidget(label)
        self.widget.layout().addWidget(self.module_cb)
        self.widget.layout().addWidget(self.stop_bool)

    def get_subentry_from_dialog(self) -> SubEntry:
        return SubEntry(
            self.handler_name,
            self.module_cb.currentText(),
            setting=ParameterWithPath(
                parameter=Parameter.create(
                    title='Stop Module',
                    name=''.join(self.handler_name.split(' ')),
                    type='bool',
                    value=self.stop_bool.checkState() == QtCore.Qt.CheckState.Checked),
            path=()))

    def execute_subentry(self, entry: SubEntry,
                         dashboard: 'DashBoard'):
        """ Execute the given subentry """
        module = self.get_module(entry, dashboard)
        if not module.initialized_state:
            self.execution_failed.emit(
                SubEntryError('Could not stop an actuator that is not initialized'))
        try:
            dashboard.modules_manager.stop_module(entry.module_name)
            self.executed_signal.emit()
        except Exception as e:
            self.execution_failed.emit(e)


@SubEntryHandlerFactory.register_handler()
class StopAllSubEntryHandler(StateSubEntryHandler):
    handler_name = StateSubEntryHandlerTypes.STOP_ALL

    def setup_widgets(self):
        label = QtWidgets.QLabel('Stop All Modules:')
        self.stop_bool = QtWidgets.QCheckBox()
        self.stop_bool.setChecked(True)
        self.widget.layout().addWidget(label)
        self.widget.layout().addWidget(self.stop_bool)

    def get_subentry_from_dialog(self) -> SubEntry:
        return SubEntry(
            self.handler_name,
            ModuleType.NONE.value,
            setting=ParameterWithPath(
                parameter=Parameter.create(
                    title='Stop All Control Modules',
                    name=''.join(self.handler_name.split(' ')),
                    type='bool',
                    value=self.stop_bool.checkState() == QtCore.Qt.CheckState.Checked),
            path=()))

    def execute_subentry(self, entry: SubEntry,
                         dashboard: 'DashBoard'):
        """ Execute the given subentry """
        try:
            for mod_name in dashboard.modules_manager.actuators_name + dashboard.modules_manager.detectors_name:
               module = dashboard.modules_manager.get_mod_from_name(mod_name, ModuleType.Control)
               if module.initialized_state:
                   module.stop_module()
            self.executed_signal.emit()
        except Exception as e:
            self.execution_failed.emit(e)


@SubEntryHandlerFactory.register_handler()
class StopExtensionSubEntryHandler(StateSubEntryHandler):
    handler_name = StateSubEntryHandlerTypes.STOP_EXTENSION

    def setup_widgets(self):
        label = QtWidgets.QLabel('Stop Extension:')
        self.extension_cb = QtWidgets.QComboBox()
        self.extension_cb.addItems(self.extensions)
        self.stop_bool = QtWidgets.QCheckBox()
        self.stop_bool.setChecked(True)
        self.widget.layout().addWidget(label)
        self.widget.layout().addWidget(self.extension_cb)
        self.widget.layout().addWidget(self.stop_bool)

    def get_subentry_from_dialog(self) -> SubEntry:
        return SubEntry(
            self.handler_name,
            self.extension_cb.currentText(),
            setting=ParameterWithPath(
                parameter=Parameter.create(
                    title='Stop Extension',
                    name=''.join(self.handler_name.split(' ')),
                    type='bool',
                    value=self.stop_bool.checkState() == QtCore.Qt.CheckState.Checked),
            path=()))

    def execute_subentry(self, entry: SubEntry,
                         dashboard: 'DashBoard'):
        """ Execute the given subentry """
        try:
            if ExtensionEnum(entry.module_name) in dashboard.extensions:
                dashboard.extensions[ExtensionEnum(entry.module_name)].stop()
            self.executed_signal.emit()
        except Exception as e:
            self.execution_failed.emit(e)


if __name__ == '__main__':
    import sys
    from pymodaq_gui.qt_utils import mkQApp

    class MockModel:
        def add_data(self, index, data: SubEntry):
            print(data)

        def rowCount(self):
            return 1

    factory = SubEntryHandlerFactory()

    app = mkQApp('SpecialEntry')

    special_entry = factory.get_subentry_handler('wait_time')(MockModel(), None)
    special_entry.show_dialog()

    # Run application
    sys.exit(app.exec())



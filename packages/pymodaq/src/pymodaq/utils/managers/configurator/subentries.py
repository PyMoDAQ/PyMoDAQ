from dataclasses import dataclass
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


ser_factory = SerializableFactory()


if TYPE_CHECKING:
    from pymodaq.utils.managers.configurator.utils import ConfiguratorModel
    from pymodaq.control_modules.daq_move import DAQ_Move
    from  pymodaq.control_modules.daq_viewer import DAQ_Viewer
    from pymodaq.dashboard import DashBoard


class SubEntryError(Exception):
    pass


class SubEntryHandlerTypes(StrEnum):
    SETTINGS = 'Settings'
    ACTUATOR_VALUE = 'Actuator Value'
    INIT = 'Init. Module'
    WAIT = 'Waiting Time'
    STOP = 'Stop Module'
    STOP_ALL = 'Stop All Control Modules'
    STOP_EXTENSION = 'Stop Extension'


@SerializableFactory.register_decorator()
@dataclass
class ConfiguratorSubEntry:
    entry_type: SubEntryHandlerTypes
    module_name: str
    module_type: ModuleType
    setting: ParameterWithPath

    def __eq__(self, other: 'ConfiguratorSubEntry'):
        return (self.entry_type == other.entry_type and
                self.module_name == other.module_name and
                self.module_type == other.module_type and
                self.setting == other.setting)

    def __repr__(self):
        return f"ConfiguratorSubEntry({self.entry_type} for {self.module_type} module {self.module_name}:"\
               f" {self.setting.value()}"

    @staticmethod
    def serialize(entry: 'ConfiguratorSubEntry') -> bytes:
        """

        """
        bytes_string = b''
        bytes_string += ser_factory.get_apply_serializer(entry.entry_type.value)
        bytes_string += ser_factory.get_apply_serializer(entry.setting)
        bytes_string += ser_factory.get_apply_serializer(entry.module_name)
        bytes_string += ser_factory.get_apply_serializer(entry.module_type.value)
        return bytes_string

    @classmethod
    def deserialize(cls,
                    bytes_str: bytes) -> Union['ConfiguratorSubEntry',
    Tuple['ConfiguratorSubEntry', bytes]]:
        """Convert bytes into a ParameterWithPath object

        Returns
        -------
        ParameterWithPath: the decoded object
        bytes: the remaining bytes string if any
        """
        entry_type , remaining_bytes = ser_factory.get_apply_deserializer(bytes_str, False)
        entry_type = SubEntryHandlerTypes(entry_type)
        parameter_with_path, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)
        module_name, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)
        module_type, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)
        return ConfiguratorSubEntry(entry_type,
                                    module_name,
                                    ModuleType(module_type),
                                    parameter_with_path), remaining_bytes


class SubEntryHandler(QtCore.QObject):
    new_entry = QtCore.Signal(ConfiguratorSubEntry)

    handler_name: SubEntryHandlerTypes = abstract_attribute()  # to reimplement in real dialogs
    use_dialog = True

    def __init__(self,
                 model: 'ConfiguratorModel',
                 settings: Parameter,
                 actuators: list[str] = None,
                 detectors: list[str] = None,
                 extensions: list[str] = None,
                 ):

        super().__init__()
        self.settings: Parameter = settings
        self.actuators: list[str] = actuators if actuators is not None else []
        self.detectors: list[str] = detectors if detectors is not None else []
        self.extensions: list[str] = extensions if extensions is not None else []
        self.model: ConfiguratorModel = model

    @staticmethod
    def get_module(entry: ConfiguratorSubEntry, dashboard: 'DashBoard'):
        return dashboard.modules_manager.get_mod_from_name(entry.module_name, entry.module_type)

    def show_dialog(self):
        self.setup_ui()

    def setup_ui(self):
        self.dialog = QtWidgets.QDialog()
        vlayout = QtWidgets.QVBoxLayout()
        self.widget = QtWidgets.QWidget()
        self.widget.setLayout(QtWidgets.QHBoxLayout())

        self.setup_widgets()

        vlayout.addWidget(self.widget)
        self.dialog.setLayout(vlayout)
        buttonBox = QtWidgets.QDialogButtonBox(parent=self.dialog)

        buttonBox.addButton("Ok", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        buttonBox.accepted.connect(self.subentry_set)
        buttonBox.addButton("Cancel", QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)
        buttonBox.rejected.connect(self.dialog.reject)

        vlayout.addWidget(buttonBox)
        self.dialog.setWindowTitle(f"Fill in information about this {self.handler_name}")

        self.dialog.open()

    def subentry_set(self):
        self.dialog.accept()
        self.model.add_data(self.model.rowCount(),
                            self.get_subentry_from_dialog())

    def setup_widgets(self):
        """ To reimplement

        You can use self.widget as the container for your custom widgets!
        """
        pass

    def get_subentry_from_dialog(self) -> ConfiguratorSubEntry:
        """ Get a ConfiguratorEntry from the dialog

        To be reimplemented """
        raise NotImplementedError

    def execute_subentry(self, entry: ConfiguratorSubEntry,
                         dashboard: 'DashBoard'):
        """ Execute the given subentry """
        raise NotImplementedError


class SubEntryHandlerFactory:
    """The factory class to get SubEntry handlers"""

    handlers_registry = {}

    @classmethod
    def register_handler(cls) -> Callable:
        """Class decorator method to register SubEntryHandlers class to the internal
        registry.
        Must be used as a decorator above the definition of an SubEntryHandler inherited class.

        The entry class must implement specific class attributes and methods
        """

        def inner_wrapper(wrapped_class: SubEntryHandler) -> Callable:
            subentry_name = wrapped_class.handler_name

            if subentry_name not in cls.handlers_registry:
                cls.handlers_registry[subentry_name] = wrapped_class
            # Return wrapped_class
            return wrapped_class

        # Return decorated function
        return inner_wrapper

    @classmethod
    def get_subentry_handler(cls, subentry_name: str) -> type[SubEntryHandler]:
        """Factory command to get registered subentry handler.

        This method gets the appropriate executor class from the registry
        """

        if subentry_name not in cls.handlers_registry:
            raise KeyError(f".{subentry_name} is not a supported entry.")

        return cls.handlers_registry[subentry_name]

    @property
    def entries(self) -> list[str]:
        return [entry for entry in self.handlers_registry.keys()]


@SubEntryHandlerFactory.register_handler()
class SettingsEntryHandler(SubEntryHandler):

    handler_name = SubEntryHandlerTypes.SETTINGS
    use_dialog = False

    def execute_subentry(self, entry: ConfiguratorSubEntry,
                         dashboard: 'DashBoard'):
        """ Execute the given subentry """
        module = self.get_module(entry, dashboard)
        module.settings.child(*entry.setting.path[3:]).setValue(entry.setting.value())


@SubEntryHandlerFactory.register_handler()
class ActuatorValueSubEntryHandler(SubEntryHandler):

    handler_name = SubEntryHandlerTypes.ACTUATOR_VALUE

    def setup_widgets(self):
        self.actuator_cb = QtWidgets.QComboBox()
        self.actuator_cb.addItems(self.actuators)

        self.value_sb = SpinBox(suffix=self.get_units_from_module_name(self.actuators[0]), siPrefix= False)
        self.actuator_cb.currentTextChanged.connect(self.update_suffix_in_dialog)

        self.widget.layout().addWidget(self.actuator_cb)
        self.widget.layout().addWidget(self.value_sb)

    def get_units_from_module_name(self, actuator_name: str):
        mods_settings = [group.child('name').value() for
                        group in self.settings.child(ModuleType.Actuator).children()]
        actuator_settings = self.settings.child(ModuleType.Actuator).children()[
            mods_settings.index(actuator_name)]

        return actuator_settings.child('move_settings', 'units').value()

    def update_suffix_in_dialog(self, actuator_name: str):
        self.value_sb.setOpts(suffix=self.get_units_from_module_name(actuator_name))

    def get_subentry_from_dialog(self) -> ConfiguratorSubEntry:
        return ConfiguratorSubEntry(
            self.handler_name,
            self.actuator_cb.currentText(),
            module_type=ModuleType.Actuator,
            setting=ParameterWithPath(
                parameter=Parameter.create(
                    title= 'Actuator Value',
                    name=''.join(self.handler_name.split(' ')),
                    type='float',
                    value=self.value_sb.value(),
                    suffix=self.value_sb.opts['suffix']),
            path=()),)

    def execute_subentry(self, entry: ConfiguratorSubEntry,
                         dashboard: 'DashBoard'):
        """ Execute the given subentry """
        module = self.get_module(entry, dashboard)
        if not module.initialized_state:
            raise SubEntryError('Could not move an actuator that is not initialized')
        try:
            dte_actuators = DataToExport('actuators', data=[
                DataActuator(entry.module_name, data=entry.setting.parameter.value(),
                             units=entry.setting.parameter.opts.get('suffix', module.units))])

            dashboard.modules_manager.connect_and_move_actuators(dte_actuators)
        except Exception as e:
            raise SubEntryError from e

@SubEntryHandlerFactory.register_handler()
class InitSubEntryHandler(SubEntryHandler):
    handler_name = SubEntryHandlerTypes.INIT

    def setup_widgets(self):
        self.control_module_cb = QtWidgets.QComboBox()
        self.control_module_cb.addItems(self.actuators + self.detectors)
        self.init_cb = QtWidgets.QCheckBox()

        self.widget.layout().addWidget(self.control_module_cb)
        self.widget.layout().addWidget(self.init_cb)

    def get_subentry_from_dialog(self) -> ConfiguratorSubEntry:

        module_name = self.control_module_cb.currentText()
        module_type = ModuleType.Actuator if module_name in self.actuators else ModuleType.Detector
        return ConfiguratorSubEntry(
            self.handler_name,
            module_name,
            module_type=module_type,
            setting=ParameterWithPath(
                parameter=Parameter.create(title= 'Control Module Init Value',
                                           name=''.join(self.handler_name.split(' ')),
                                           type='bool',
                                           value=True if self.init_cb.checkState() ==
                                                         QtCore.Qt.CheckState.Checked else False,
                                                   )))

    def execute_subentry(self, entry: ConfiguratorSubEntry,
                         dashboard: 'DashBoard'):
        """ Execute the given subentry """
        module = self.get_module(entry, dashboard)
        if module.initialized_state == entry.setting.value():
            raise SubEntryError(
                f'The {entry.module_name} module is already '
                f'{"initialized" if module.initialized_state else "uninitialized"}')
        try:
            module.init_hardware_ui(entry.setting.value())
            if entry.setting.value():
                init_state = dashboard.modules_manager.poll_init(module)
                if init_state != entry.setting.value():
                    raise SubEntryError('Could not initialize the module')
        except Exception as e:

            raise SubEntryError from e

@SubEntryHandlerFactory.register_handler()
class WaitSubEntryHandler(SubEntryHandler):
    handler_name = SubEntryHandlerTypes.WAIT

    def setup_widgets(self):
        label = QtWidgets.QLabel('Waiting Time:')
        self.wait_time_sb = SpinBox(suffix='s', siPrefix=True)
        self.wait_time_sb.setValue(0.1)

        self.widget.layout().addWidget(label)
        self.widget.layout().addWidget(self.wait_time_sb)

    def get_subentry_from_dialog(self) -> ConfiguratorSubEntry:

        return ConfiguratorSubEntry(
            self.handler_name,
            str(ModuleType.NONE),
            module_type=ModuleType.NONE,
            setting=ParameterWithPath(
                parameter=Parameter.create(title='Waiting Time',
                                           name=''.join(self.handler_name.split(' ')),
                                           type='float',
                                           value=self.wait_time_sb.value(),
                                           suffix='s',
                                           siPrefix=True,
                                           )))

    def execute_subentry(self, entry: ConfiguratorSubEntry,
                         dashboard: 'DashBoard'):
        """ Execute the given subentry """
        start = time.perf_counter()

        while abs(time.perf_counter() - start) < entry.setting.value():
            QtWidgets.QApplication.processEvents()


@SubEntryHandlerFactory.register_handler()
class StopSubEntryHandler(SubEntryHandler):
    handler_name = SubEntryHandlerTypes.STOP

    def setup_widgets(self):
        label = QtWidgets.QLabel('Stop Module:')
        self.module_cb = QtWidgets.QComboBox()
        self.module_cb.addItems(self.actuators + self.detectors)
        self.stop_bool = QtWidgets.QCheckBox()
        self.stop_bool.setChecked(True)
        self.widget.layout().addWidget(label)
        self.widget.layout().addWidget(self.module_cb)
        self.widget.layout().addWidget(self.stop_bool)

    def get_subentry_from_dialog(self) -> ConfiguratorSubEntry:
        return ConfiguratorSubEntry(
            self.handler_name,
            self.module_cb.currentText(),
            module_type=ModuleType.Actuator if self.module_cb.currentText() in self.actuators else ModuleType.Detector,
            setting=ParameterWithPath(
                parameter=Parameter.create(
                    title= 'Stop Module',
                    name=''.join(self.handler_name.split(' ')),
                    type='bool',
                    value=self.stop_bool.checkState() == QtCore.Qt.CheckState.Checked,),
            path=()),)

    def execute_subentry(self, entry: ConfiguratorSubEntry,
                         dashboard: 'DashBoard'):
        """ Execute the given subentry """
        module = self.get_module(entry, dashboard)
        if not module.initialized_state:
            raise SubEntryError('Could not stop an actuator that is not initialized')
        try:
            dashboard.modules_manager.stop_module(entry.module_name)
        except Exception as e:
            raise SubEntryError from e


@SubEntryHandlerFactory.register_handler()
class StopAllSubEntryHandler(SubEntryHandler):
    handler_name = SubEntryHandlerTypes.STOP_ALL

    def setup_widgets(self):
        label = QtWidgets.QLabel('Stop All Modules:')
        self.stop_bool = QtWidgets.QCheckBox()
        self.stop_bool.setChecked(True)
        self.widget.layout().addWidget(label)
        self.widget.layout().addWidget(self.stop_bool)

    def get_subentry_from_dialog(self) -> ConfiguratorSubEntry:
        return ConfiguratorSubEntry(
            self.handler_name,
            ModuleType.NONE.value,
            module_type=ModuleType.Control,
            setting=ParameterWithPath(
                parameter=Parameter.create(
                    title= 'Stop All Control Modules',
                    name=''.join(self.handler_name.split(' ')),
                    type='bool',
                    value=self.stop_bool.checkState() == QtCore.Qt.CheckState.Checked,),
            path=()),)

    def execute_subentry(self, entry: ConfiguratorSubEntry,
                         dashboard: 'DashBoard'):
        """ Execute the given subentry """
        try:
            for mod_name in dashboard.modules_manager.actuators_name + dashboard.modules_manager.detectors_name:
               module = dashboard.modules_manager.get_mod_from_name(mod_name, ModuleType.Control)
               if module.initialized_state:
                   module.stop_module()
        except Exception as e:
            raise SubEntryError from e


@SubEntryHandlerFactory.register_handler()
class StopExtensionSubEntryHandler(SubEntryHandler):
    handler_name = SubEntryHandlerTypes.STOP_EXTENSION

    def setup_widgets(self):
        label = QtWidgets.QLabel('Stop Extension:')
        self.extension_cb = QtWidgets.QComboBox()
        self.extension_cb.addItems(self.extensions)
        self.stop_bool = QtWidgets.QCheckBox()
        self.stop_bool.setChecked(True)
        self.widget.layout().addWidget(label)
        self.widget.layout().addWidget(self.extension_cb)
        self.widget.layout().addWidget(self.stop_bool)

    def get_subentry_from_dialog(self) -> ConfiguratorSubEntry:
        return ConfiguratorSubEntry(
            self.handler_name,
            self.extension_cb.currentText(),
            module_type=ModuleType.Extension,
            setting=ParameterWithPath(
                parameter=Parameter.create(
                    title= 'Stop Extension',
                    name=''.join(self.handler_name.split(' ')),
                    type='bool',
                    value=self.stop_bool.checkState() == QtCore.Qt.CheckState.Checked,),
            path=()),)

    def execute_subentry(self, entry: ConfiguratorSubEntry,
                         dashboard: 'DashBoard'):
        """ Execute the given subentry """
        try:
            if ExtensionEnum(entry.module_name) in dashboard.extensions:
                dashboard.extensions[ExtensionEnum(entry.module_name)].stop()
        except Exception as e:
            raise SubEntryError from e


if __name__ == '__main__':
    import sys
    from pymodaq_gui.qt_utils import mkQApp

    class MockModel:
        def add_data(self, index, data: ConfiguratorSubEntry):
            print(data)

        def rowCount(self):
            return 1

    factory = SubEntryHandlerFactory()

    app = mkQApp('SpecialEntry')

    special_entry = factory.get_subentry_handler('wait_time')(MockModel(), None)
    special_entry.show_dialog()

    # Run application
    sys.exit(app.exec())



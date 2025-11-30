import time
from typing import Callable, TYPE_CHECKING, Union

from qtpy import QtWidgets, QtCore

from pymodaq_data import DataToExport
from pymodaq_gui.utils.widgets import SpinBox
from pymodaq_gui.parameter.utils import Parameter, ParameterWithPath
from pymodaq.utils.managers.configurator.entries import ConfiguratorSubEntry
from pymodaq_utils.abstract import abstract_attribute
from pymodaq.utils.data import DataActuator, DataToActuators

from pymodaq.utils.managers.modules_manager import ModuleType
from pymodaq_utils.enums import StrEnum

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


class SubEntryHandler(QtCore.QObject):
    new_entry = QtCore.Signal(ConfiguratorSubEntry)

    handler_name: SubEntryHandlerTypes = abstract_attribute()  # to reimplement in real dialogs
    use_dialog = True

    def __init__(self,
                 model: 'ConfiguratorModel',
                 settings: Parameter,
                 actuators: list[str] = None,
                 detectors: list[str] = None):

        super().__init__()
        self.settings: Parameter = settings
        self.actuators: list[str] = actuators
        self.detectors: list[str] = detectors
        self.model: ConfiguratorModel = model

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
                         module:Union['DAQ_Move', 'DAQ_Viewer'],
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

    handler_name = SubEntryHandlerTypes.SETTINGS.value
    use_dialog = False

    def execute_subentry(self, entry: ConfiguratorSubEntry,
                         module: 'DAQ_Move',
                         dashboard: 'DashBoard'):
        """ Execute the given subentry """
        module.settings.child(*entry.setting.path[3:]).setValue(entry.setting.value())


@SubEntryHandlerFactory.register_handler()
class ActuatorValueSubEntryHandler(SubEntryHandler):

    handler_name = SubEntryHandlerTypes.ACTUATOR_VALUE.value

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
                         module: 'DAQ_Move',
                         dashboard: 'DashBoard'):
        """ Execute the given subentry """
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
    handler_name = SubEntryHandlerTypes.INIT.value

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
                         module: Union['DAQ_Move', 'DAQ_Viewer'],
                         dashboard: 'DashBoard'):
        """ Execute the given subentry """
        if module.initialized_state == entry.setting.value():
            raise SubEntryError(
                f'The {entry.module_name} module is already '
                f'{"initialized" if module.initialized_state else "uninitialized"}')
        try:
            module.init_hardware_ui(entry.setting.value())
            if entry.setting.value():
                init_state = dashboard.poll_init(module)
                if init_state != entry.setting.value():
                    raise SubEntryError('Could not initialize the module')
        except Exception as e:

            raise SubEntryError from e

@SubEntryHandlerFactory.register_handler()
class WaitSubEntryHandler(SubEntryHandler):
    handler_name = SubEntryHandlerTypes.WAIT.value

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
                         module: Union['DAQ_Move', 'DAQ_Viewer'],
                         dashboard: 'DashBoard'):
        """ Execute the given subentry """
        start = time.perf_counter()

        while abs(time.perf_counter() - start) < entry.setting.value():
            QtWidgets.QApplication.processEvents()



if __name__ == '__main__':
    class MockModel:
        def add_data(self, index, data: ConfiguratorSubEntry):
            print(data)

        def rowCount(self):
            return 1

    factory = SubEntryHandlerFactory()

    from pymodaq_gui.utils.utils import mkQApp


    app = mkQApp('SpecialEntry')

    special_entry = factory.get_subentry_handler('wait_time')(MockModel(), None)
    special_entry.show_dialog()

    # Run application
    app.exec()

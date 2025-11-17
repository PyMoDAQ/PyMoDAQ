from typing import Callable, TYPE_CHECKING, Union

from qtpy import QtWidgets, QtCore

from pymodaq_data import DataToExport
from pymodaq_gui.utils.widgets import SpinBox
from pymodaq_gui.parameter.utils import Parameter, ParameterWithPath
from pymodaq.utils.managers.configurator.entries import ConfiguratorEntry
from pymodaq_utils.abstract import abstract_attribute
from pymodaq.utils.data import DataActuator, DataToActuators

from pymodaq.utils.managers.modules_manager import ModuleType

if TYPE_CHECKING:
    from pymodaq.utils.managers.configurator.utils import ConfiguratorModel
    from pymodaq.control_modules.daq_move import DAQ_Move
    from  pymodaq.control_modules.daq_viewer import DAQ_Viewer
    from pymodaq.dashboard import DashBoard



class SpecialEntry(QtCore.QObject):
    new_entry = QtCore.Signal(ConfiguratorEntry)

    special_entry_name: str = abstract_attribute()  # to reimplement in real dialogs
    nice_descriptor: str = abstract_attribute()  # to reimplement in real dialogs

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
        buttonBox.accepted.connect(self.entry_set)
        buttonBox.addButton("Cancel", QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)
        buttonBox.rejected.connect(self.dialog.reject)

        vlayout.addWidget(buttonBox)
        self.dialog.setWindowTitle(f"Fill in information about this {self.special_entry_name}")

        self.dialog.open()

    def entry_set(self):
        self.dialog.accept()
        self.model.add_data(self.model.rowCount(),
                            self.get_entry_from_dialog())

    def setup_widgets(self):
        """ To reimplement

        You can use self.widget as the container for your custom widgets!
        """
        pass

    def get_entry_from_dialog(self) -> ConfiguratorEntry:
        """ Get a ConfiguratorEntry from the dialog

        To be reimplemented """
        raise NotImplementedError

    def is_valid(self, entry: ConfiguratorEntry) -> bool:
        """ Check that the given entry is valid for the SpecialEntry

        To be reimplemented
        """
        raise NotImplementedError

    def apply_entry(self, entry: ConfiguratorEntry,
                    module:Union['DAQ_Move', 'DAQ_Viewer'],
                    dashboard: 'DashBoard'):
        """ Apply the given special entry """
        raise NotImplementedError


class SpecialEntryFactory:
    """The factory class for creating Special Configurator Entries"""

    entries_registry = {}

    prefix = 'special_entry'

    @classmethod
    def register_entry(cls) -> Callable:
        """Class decorator method to register SpecialEntries class to the internal registry.
        Must be used as a decorator above the definition of an EntryDialog inherited class.

        The entry class must implement specific class attributes and methods
        """

        def inner_wrapper(wrapped_class: SpecialEntry) -> Callable:
            special_entry_name = cls.get_full_name(wrapped_class.special_entry_name)

            if special_entry_name not in cls.entries_registry:
                cls.entries_registry[special_entry_name] = wrapped_class
            # Return wrapped_class
            return wrapped_class

        # Return decorated function
        return inner_wrapper

    @classmethod
    def get_full_name(cls, special_entry: str) -> str:
        return f'{cls.prefix}_{special_entry}'

    @classmethod
    def get_short_name(cls, special_entry_long: str) -> str:
        return special_entry_long.split(cls.prefix + '_')[1]

    @classmethod
    def get_entry(cls, special_entry_name: str) -> type[SpecialEntry]:
        """Factory command to get registered SpecialEntries Dialog and related Configurator entries.

        This method gets the appropriate executor class from the registry
        """
        return cls.get_entry_from_long_name(cls.get_full_name(special_entry_name))

    @classmethod
    def get_entry_from_long_name(cls, special_entry_name_long: str) -> type[SpecialEntry]:
        """Factory command to get registered SpecialEntries Dialog and related Configurator entries.

        This method gets the appropriate executor class from the registry
        """

        if special_entry_name_long not in cls.entries_registry:
            raise ValueError(f".{special_entry_name_long} is not a supported entry.")

        return cls.entries_registry[special_entry_name_long]

    @property
    def entries(self):
        return [entry for entry in self.entries_registry.keys()]

    @property
    def short_entries(self):
        return [entry.split(self.prefix + '_')[1] for entry in self.entries]


@SpecialEntryFactory.register_entry()
class ActuatorValueSpecialEntry(SpecialEntry):

    special_entry_name = 'actuator_value'
    nice_descriptor = 'Actuator Value'

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

    def get_entry_from_dialog(self) -> ConfiguratorEntry:
        return ConfiguratorEntry(
            self.actuator_cb.currentText(),
            module_type=ModuleType.Actuator,
            setting=ParameterWithPath(
                parameter=Parameter.create(
                    title= 'Actuator Value',
                    name=SpecialEntryFactory.get_full_name(self.special_entry_name),
                    type='float',
                    value=self.value_sb.value(),
                    suffix=self.value_sb.opts['suffix'])))

    def is_valid(self, entry: ConfiguratorEntry) -> bool:
        """ Check that the given entry is valid for the SpecialEntry
        """
        return entry.module_name in self.actuators

    def apply_entry(self, entry: ConfiguratorEntry,
                    module: 'DAQ_Move',
                    dashboard: 'DashBoard'):
        """ Apply the given special entry """
        dte_actuators = DataToExport('actuators', data=[
            DataActuator(entry.module_name, data=entry.setting.parameter.value(),
                         units=entry.setting.parameter.opts.get('suffix', module.units))])

        dashboard.modules_manager.connect_and_move_actuators(dte_actuators)


@SpecialEntryFactory.register_entry()
class InitSpecialEntry(SpecialEntry):
    special_entry_name = 'control_module_init'
    nice_descriptor = 'Init Control Module'

    def setup_widgets(self):
        self.control_module_cb = QtWidgets.QComboBox()
        self.control_module_cb.addItems(self.actuators + self.detectors)
        self.init_cb = QtWidgets.QCheckBox()

        self.widget.layout().addWidget(self.control_module_cb)
        self.widget.layout().addWidget(self.init_cb)

    def get_entry_from_dialog(self) -> ConfiguratorEntry:

        module_name = self.control_module_cb.currentText()
        module_type = ModuleType.Actuator if module_name in self.actuators else ModuleType.Detector
        return ConfiguratorEntry(
            module_name,
            module_type=module_type,
            setting=ParameterWithPath(
                parameter=Parameter.create(title= 'Control Module Init Value',
                                           name=SpecialEntryFactory.get_full_name(self.special_entry_name),
                                           type='bool',
                                           value=True if self.init_cb.checkState() ==
                                                         QtCore.Qt.CheckState.Checked else False,
                                                   )))

    def is_valid(self, entry: ConfiguratorEntry) -> bool:
        """ Check that the given entry is valid for the SpecialEntry
        """
        return entry.module_name in [group.child('name').value() for
                                     group in self.settings.child(entry.module_type).children()]

    def apply_entry(self, entry: ConfiguratorEntry,
                    module: Union['DAQ_Move', 'DAQ_Viewer'],
                    dashboard: 'DashBoard'):
        """ Apply the given special entry """
        if entry.setting.parameter.value():
            module.init_hardware_ui(True)
            dashboard.poll_init(module)


@SpecialEntryFactory.register_entry()
class WaitSpecialEntry(SpecialEntry):
    special_entry_name = 'wait_time'
    nice_descriptor = 'Waiting Time'

    def setup_widgets(self):
        label = QtWidgets.QLabel('Waiting Time:')
        self.wait_time_sb = SpinBox(suffix='s', siPrefix=True)
        self.wait_time_sb.setValue(0.1)

        self.widget.layout().addWidget(label)
        self.widget.layout().addWidget(self.wait_time_sb)

    def get_entry_from_dialog(self) -> ConfiguratorEntry:

        return ConfiguratorEntry(
            'None',
            module_type=ModuleType.NONE,
            setting=ParameterWithPath(
                parameter=Parameter.create(title='Waiting Time',
                                           name=SpecialEntryFactory.get_full_name(self.special_entry_name),
                                           type='float',
                                           value=self.wait_time_sb.value(),
                                           suffix='s',
                                           siPrefix=True,
                                           )))

    def is_valid(self, entry: ConfiguratorEntry) -> bool:
        """ Check that the given entry is valid for the SpecialEntry
        """
        return True

    def apply_entry(self, entry: ConfiguratorEntry,
                    module: Union['DAQ_Move', 'DAQ_Viewer'],
                    dashboard: 'DashBoard'):
        """ Apply the given special entry """
        QtCore.QThread.msleep(entry.setting.value() * 1000)


if __name__ == '__main__':
    class MockModel:
        def add_data(self, index, data: ConfiguratorEntry):
            print(data)

        def rowCount(self):
            return 1

    factory = SpecialEntryFactory()

    from pymodaq_gui.utils.utils import mkQApp


    app = mkQApp('SpecialEntry')

    special_entry = factory.get_entry('wait_time')(MockModel(), None)
    special_entry.show_dialog()

    # Run application
    app.exec()

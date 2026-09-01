from dataclasses import dataclass
from pymodaq.control_modules.move_utility_classes import HW_SETTINGS_KEY as ACTUATOR_SETTINGS_KEY
import time
from typing import Callable, TYPE_CHECKING, Union, Tuple

from qtpy import QtWidgets, QtCore
from serializall import SerializableFactory

from pymodaq.utils.managers.modules import ModuleType
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_utils.enums import StrEnum
from pymodaq_utils.abstract import abstract_attribute
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_gui.parameter.utils import Parameter, ParameterWithPath

from pymodaq_utils.enums import StrEnum


logger = set_logger(get_module_name(__file__))
ser_factory = SerializableFactory()


if TYPE_CHECKING:
    from pymodaq_gui.managers.settings.utils import SettingsManagerModel
    from pymodaq_gui.managers.settings.settings_manager import SettingsManager
    from pymodaq.dashboard import DashBoard


class SubEntryError(Exception):
    pass


class SubEntryHandlerTypes(StrEnum):
    SETTINGS = 'Settings'


@SerializableFactory.register_decorator()
@dataclass
class SubEntry:
    """ Depending on the module or modules this manager handles,
    the attributes below should be completed as well as the serialization/deserialization
    """
    entry_type: SubEntryHandlerTypes | str
    module_name: str
    setting: ParameterWithPath

    def __eq__(self, other: 'SubEntry'):
        return (self.entry_type == other.entry_type and
                self.module_name == other.module_name and
                self.setting == other.setting)

    def __repr__(self):
        return f"SubEntry({self.entry_type}:"\
               f" {self.setting.value()})"

    @staticmethod
    def serialize(entry: 'SubEntry') -> bytes:
        """

        """
        bytes_string = b''
        bytes_string += ser_factory.get_apply_serializer(str(entry.entry_type))
        bytes_string += ser_factory.get_apply_serializer(entry.setting)
        bytes_string += ser_factory.get_apply_serializer(entry.module_name)
        return bytes_string

    @classmethod
    def deserialize(cls,
                    bytes_str: bytes) -> Union['SubEntry',
    Tuple['SubEntry', bytes]]:
        """Convert bytes into a ParameterWithPath object

        Returns
        -------
        ParameterWithPath: the decoded object
        bytes: the remaining bytes string if any
        """
        entry_type , remaining_bytes = ser_factory.get_apply_deserializer(bytes_str, False)
        entry_type = entry_type
        parameter_with_path, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)
        module_name, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)

        return SubEntry(entry_type, module_name,
                        parameter_with_path), remaining_bytes


class SubEntryHandler(QtCore.QObject):
    new_entry = QtCore.Signal(SubEntry)
    executed_signal = QtCore.Signal(int) # to be emited when execution is done
    execution_failed = QtCore.Signal(Exception)

    handler_name: SubEntryHandlerTypes = abstract_attribute()  # to reimplement in real dialogs
    use_dialog = True
    sub_entry_done = QtCore.Signal(bool)

    def __init__(self,
                 model: 'SettingsManagerModel',
                 settings: Parameter,
                 *args,
                 ind_subentry: int = None,
                 **kwargs
                 ):

        super().__init__()
        self.settings: Parameter = settings
        self.model: SettingsManagerModel = model
        self._ind_subentry = ind_subentry  # the current index with subentries, see _execute_entry
        print(f'subhandler with index {ind_subentry}')

    @staticmethod
    def get_module(entry: SubEntry, *args, **kwargs) -> ParameterManager:
        """ Get the ParameterManager module on which the settings will be applied

        To be reimplemented
        """
        raise NotImplementedError

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

    def get_subentry_from_dialog(self) -> SubEntry:
        """ Get a StateSubEntry from the dialog

        To be reimplemented """
        raise NotImplementedError

    def execute_subentry(self, entry: SubEntry, **kwargs):
        """ Execute the given subentry and emit the signal sub_entry_done when done
        """
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
            else:
                logger.info(f"Subentry {subentry_name} already registered")
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

    def execute_subentry(self, entry: SubEntry,
                         *args, **kwargs):
        """ Execute the given subentry

        In general, should get first the module on which the settings will be applied
        Then apply the Settings subentry to this module

        Examples
        --------
        module = self.get_module(entry, *args, **kwargs)
        module.settings.child(*entry.setting.path).setValue(entry.setting.value())
        """
        raise NotImplementedError



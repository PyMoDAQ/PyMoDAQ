from dataclasses import dataclass
from pymodaq.control_modules.move_utility_classes import HW_SETTINGS_KEY as ACTUATOR_SETTINGS_KEY
import time
from typing import Callable, TYPE_CHECKING, Union, Tuple

from qtpy import QtWidgets, QtCore
from serializall import SerializableFactory

from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_utils.enums import StrEnum
from pymodaq_utils.abstract import abstract_attribute


from pymodaq_gui.parameter.utils import Parameter, ParameterWithPath
from pymodaq_gui.managers.settings.subentries import (SubEntryError,  # noqa
    SubEntryHandlerTypes, SettingsManagerSubEntry, SubEntryHandlerFactory)
from pymodaq_utils.enums import StrEnum
from pymodaq.utils.managers.modules_manager import ModuleType

ser_factory = SerializableFactory()


if TYPE_CHECKING:
    from pymodaq_gui.managers.settings.utils import SettingsManagerModel
    from pymodaq.dashboard import DashBoard



@SerializableFactory.register_decorator()
@dataclass
class SettingsManagerSubEntry(SettingsManagerSubEntry):
    """ Depending on the module or modules this manager handles,
    the attributes below should be completed as well as the serialization/deserialization
    """
    pass


class SubEntryHandler(QtCore.QObject):
    new_entry = QtCore.Signal(SettingsManagerSubEntry)


class SubEntryHandlerFactory(SubEntryHandlerFactory):
    """The factory class to get SubEntry handlers"""
    pass


@SubEntryHandlerFactory.register_handler()
class SettingsEntryHandler(SubEntryHandler):

    handler_name = SubEntryHandlerTypes.SETTINGS
    use_dialog = False

    def execute_subentry(self, entry: SettingsManagerSubEntry,
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



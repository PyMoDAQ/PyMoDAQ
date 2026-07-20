from dataclasses import dataclass

from numba.core.cgutils import if_zero

from pymodaq.control_modules.move_utility_classes import HW_SETTINGS_KEY as ACTUATOR_SETTINGS_KEY
import time
from typing import Callable, TYPE_CHECKING, Union, Tuple

from qtpy import QtWidgets, QtCore
from serializall import SerializableFactory

from pymodaq.utils.managers.modules import ModulesManager
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_utils.enums import StrEnum
from pymodaq_utils.abstract import abstract_attribute
from pymodaq.utils.scanner.scanner import Scanner

from pymodaq_gui.parameter.utils import Parameter, ParameterWithPath
from pymodaq_gui.managers.settings.subentries import (SubEntryError,  # noqa
                                                      SubEntryHandlerTypes, SubEntry, SubEntryHandlerFactory,
                                                      SubEntryHandler)

from pymodaq.utils.managers.modules_manager import ModuleType

ser_factory = SerializableFactory()


if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard
    from pymodaq_gui.h5modules.saving import H5Saver
    from pymodaq.extensions.scan.daq_scan import DAQScan
    from pymodaq.extensions.scan.manager.scan_manager import ScanManager


@SerializableFactory.register_decorator()
@dataclass
class ScanSubEntry(SubEntry):
    """ Depending on the module or modules this manager handles,
    the attributes below should be completed as well as the serialization/deserialization
    """
    pass


class SubEntryHandler(SubEntryHandler):
    new_entry = QtCore.Signal(ScanSubEntry)

    @staticmethod
    def get_module(entry: ScanSubEntry, *args, **kwargs) -> ParameterManager:
        """ Get the ParameterManager module on which the settings will be applied

        To be reimplemented
        """
        raise NotImplementedError


@SubEntryHandlerFactory.register_handler()
class ScanSettingsEntryHandler(SubEntryHandler):

    handler_name = 'ScanSettings'
    use_dialog = False

    def execute_subentry(self, entry: ScanSubEntry,
                         manager: 'ScanManager', *args, **kwargs):
        """ Execute the given subentry

        In general, should get first the module on which the settings will be applied
        Then apply the Settings subentry to this module

        Examples
        --------
        module = self.get_module(entry, *args, **kwargs)
        module.settings.child(*entry.setting.path).setValue(entry.setting.value())
        """

        module: Union['DAQScan', 'H5Saver'] = getattr(manager, entry.module_name)
        module.settings.child(*entry.setting.path[2:]).setValue(entry.setting.value())


@SubEntryHandlerFactory.register_handler()
class ControlModulesEntryHandler(SubEntryHandler):

    handler_name = 'ControlModulesSettings'
    use_dialog = False

    def __init__(self, *args, **kwargs) -> None:
        self.manager: ScanManager = None
        super().__init__(*args, **kwargs)

    def execute_subentry(self, entry: ScanSubEntry,
                         manager: 'ScanManager', *args, **kwargs):
        """ Execute the given subentry

        In general, should get first the module on which the settings will be applied
        Then apply the Settings subentry to this module

        Examples
        --------
        module = self.get_module(entry, *args, **kwargs)
        module.settings.child(*entry.setting.path).setValue(entry.setting.value())
        """

        module_from_daq_scan = self.manager.daq_scan.modules_manager
        module_from_manager = self.manager.modules_manager
        for child in entry.setting.parameter.children():
            value = module_from_daq_scan.settings[child.name()]
            value['selected'] = [mod for mod in child.value()['selected'] if
                                 mod in value['all_items']]
            module_from_daq_scan.settings[child.name()] = value
            module_from_manager.settings[child.name()] = value


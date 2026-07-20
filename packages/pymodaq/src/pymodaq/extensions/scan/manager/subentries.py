from copy import deepcopy
from dataclasses import dataclass

from typing import Callable, TYPE_CHECKING, Union, Tuple

from qtpy import QtWidgets, QtCore
from serializall import SerializableFactory

from pymodaq_gui.managers.parameter_manager import ParameterManager


from pymodaq_gui.parameter.utils import Parameter, ParameterWithPath
from pymodaq_gui.managers.settings.subentries import (SubEntryError,  # noqa
                                                      SubEntryHandlerTypes, SubEntry, SubEntryHandlerFactory,
                                                      SubEntryHandler)


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

    @classmethod
    def create_subentry(cls, manager: 'ScanManager') -> ScanSubEntry:
        pass

    @classmethod
    def update(cls, manager: 'ScanManager', entry: ScanSubEntry) -> None:
        """ update the manager according to the loading of the SubEntry"""
        pass


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

    @classmethod
    def create_subentry(cls, manager: 'ScanManager') -> ScanSubEntry:
        modules_settings = Parameter.create(name='modules', type='group', children=[
            manager.modules_manager.settings.child('detectors').saveState(),
            manager.modules_manager.settings.child('actuators').saveState(),
        ])
        return ScanSubEntry(cls.handler_name,
                            'ModuleManager',
                            ParameterWithPath(modules_settings))

    @classmethod
    def update(cls, manager: 'ScanManager', entry: ScanSubEntry):
        """ update the manager according to the loading of the SubEntry"""
        module_from_daq_scan = manager.daq_scan.modules_manager
        module_from_manager = manager.modules_manager
        for child in entry.setting.parameter.children():
            value = deepcopy(module_from_daq_scan.settings[child.name()])
            value['selected'] = [mod for mod in child.value()['selected'] if
                                 mod in value['all_items']]
            module_from_manager.settings[child.name()] = value

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
            value = deepcopy(module_from_daq_scan.settings[child.name()])
            value['selected'] = [mod for mod in child.value()['selected'] if
                                 mod in value['all_items']]
            if 'actuators' in child.name():
                module_from_daq_scan.selected_actuators_name = value['selected']
            else:
                module_from_daq_scan.selected_detectors_name = value['selected']
            module_from_manager.settings[child.name()] = value

@SubEntryHandlerFactory.register_handler()
class ScannnerEntryHandler(SubEntryHandler):

    handler_name = 'ScannerSubType'
    use_dialog = False

    def __init__(self, *args, **kwargs) -> None:
        self.manager: ScanManager = None
        super().__init__(*args, **kwargs)

    @classmethod
    def create_subentry(cls, manager: 'ScanManager') -> ScanSubEntry:
        scanner = manager.scanner
        scan_settings = Parameter.create(name='type_subtype', type='group', children=[
            scanner.settings.child('scan_type').saveState(),
            scanner.settings.child('scan_sub_type').saveState(),
            scanner.scanner.settings.saveState(),
        ])
        return ScanSubEntry(cls.handler_name,
                            'Scanner',
                            ParameterWithPath(scan_settings))

    @classmethod
    def update(cls, manager: 'ScanManager', entry: ScanSubEntry):
        """ update the manager according to the loading of the SubEntry"""
        pass

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
        scanner_from_daq_scan = self.manager.daq_scan.scanner
        scanner_from_manager = self.manager.scanner

        scan_type = entry.setting.parameter['scan_type']
        scan_sub_type = entry.setting.parameter['scan_sub_type']

        scanner_from_manager.settings['scan_type'] = scan_type
        scanner_from_daq_scan.settings['scan_type'] = scan_type
        QtWidgets.QApplication.processEvents()
        scanner_from_manager.settings['scan_sub_type'] = scan_sub_type
        scanner_from_daq_scan.settings['scan_sub_type'] = scan_sub_type
        QtWidgets.QApplication.processEvents()

        scanner_from_manager.scanner.settings.restoreState(
            entry.setting.parameter.child('scanner_settings').saveState())
        scanner_from_daq_scan.scanner.settings.restoreState(
            entry.setting.parameter.child('scanner_settings').saveState())


@SubEntryHandlerFactory.register_handler()
class StartScanEntryHandler(SubEntryHandler):

    handler_name = 'StartScanSubType'
    use_dialog = False

    def __init__(self, *args, **kwargs) -> None:
        self.manager: ScanManager = None
        super().__init__(*args, **kwargs)

    @classmethod
    def create_subentry(cls, manager: 'ScanManager') -> ScanSubEntry:
        start_settings = Parameter.create(name='start', type='bool',
                                         value=manager.is_action_checked('start_scan'))
        return ScanSubEntry(cls.handler_name,
                            'StartScan',
                            ParameterWithPath(start_settings))

    def update_subentry(self, manager: 'ScanManager', entry: ScanSubEntry):
        """ update the manager according to the loading of the SubEntry"""
        manager.set_action_checked('start_scan', entry.setting.value())

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
        if entry.setting.value():
            manager.daq_scan.override_popups(False)
            manager.daq_scan.start_scan()
            manager.daq_scan.cancel_override_popups()


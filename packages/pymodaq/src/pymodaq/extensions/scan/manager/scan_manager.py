
from typing import Union, TYPE_CHECKING
from pathlib import Path
import sys

import toml
from qtpy import QtWidgets, QtCore, QtGui

from pymodaq_utils.enums import StrEnum
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import GlobalConfig as Config, get_set_config_dir


from pymodaq_gui.h5modules.saving import H5Saver
from pymodaq_gui.parameter.ioxml import VALID_FOR_CONFIGURATION
from pymodaq_gui.managers.settings.utils import (
    SettingsManagerParameterTree, SettingsManagerModel, SettingsManagerTableView,
    settings_manager_subentries_from_path, ParameterDelegate,
    EntryActions, ModuleType)

from pymodaq.extensions.scan.manager.subentries import (
    SubEntryHandlerFactory, SubEntryHandler, SubEntryError,
    SubEntryHandlerTypes, ScanSubEntry, ParameterWithPath, ScanSettingsEntryHandler)

from pymodaq_gui.managers.settings.settings_manager import SettingsManager

from pymodaq.utils.scanner.scanner import Scanner


if TYPE_CHECKING:
    from pymodaq.extensions import DAQScan


logger = set_logger(get_module_name(__file__))
handler_factory = SubEntryHandlerFactory()

config = Config()



class ScanManager(SettingsManager):
    """
    Main class managing settings values to be restored in the DAQScan as well as info about
    a scan to be done.

    Could be extended with special subentries dealing with other features, see StateManager

    """

    entry_type = 'settings'
    entry_extension ='.scan'
    icon_name = 'qr_code_scanner'

    def __init__(self, daq_scan: 'DAQScan'):

        self.subentry_handler: SubEntryHandler = None
        self.config_model = SettingsManagerModel(save_path=self.get_entry_folder())

        dashboard = daq_scan.dashboard

        self.scanner: Scanner = Scanner(actuators=dashboard.actuators_modules)

        self.daq_scan = daq_scan
        self.h5saver = daq_scan.h5saver
        self.h5saver.settings.child('do_save').hide()
        self.h5saver.settings.child('custom_name').hide()

        self.params = [
            {'title': 'Options', 'name': 'daq_scan', 'type': 'group', 'children': daq_scan.params},
            {'title': 'Saver', 'name': 'h5saver', 'type': 'group', 'children': self.h5saver.params},
        ]

        super().__init__(dashboard=dashboard,
                         subentry_type=ScanSubEntry,
                         handler_id=ScanSettingsEntryHandler.handler_name)

        self.update_settings(self.settings)

    def connect_things(self):
        super().connect_things()
        self.modules_manager.actuators_changed.connect(self.update_scanner_actuators)

    def update_scanner_actuators(self):
        self.scanner.actuators = self.modules_manager.actuators

    def get_entry_folder(self, subfolder='', user=True) -> Path:
        """Get the folder path where the managed entries are stored."""
        if subfolder != '':
            target_path = get_set_config_dir('settings', user=user).joinpath(subfolder)
        else:
            target_path = get_set_config_dir('settings', user=user)
        target_path.mkdir(parents=True, exist_ok=True)
        return target_path

    @staticmethod
    def get_module_from_param(param: ParameterWithPath) -> Union[str]:
        """ should return the module name from data bundled in the ParameterWithPath

        To be reimplemented

        Parameters
        ----------
        param: ParameterWithPath

        """

        return param.path[1]

    def add_setting(self):
        if self.tree.currentItem() is not None:
            current_setting = self.tree.currentItem().param
            try:
                module = self.get_module_from_param(ParameterWithPath(current_setting))
            except KeyError:
                module = ModuleType.NONE.value
            entry = SubEntry(
                SubEntryHandlerTypes.SETTINGS, module,
                ParameterWithPath(current_setting))
            entries = self.config_model.split_entry(entry)
            for entry in entries:
                self.config_model.add_data(self.config_model.rowCount(), entry)


    def _execute_entry(self, entry_path: Path = None, **kwargs) -> bool:
        """Applies the entry from the given file in the manager.

        Parameters:
        -----------
        file : Path
            The path to the settings file to be applied.
        """
        if entry_path is None:
            entry_path = self.entry_filepath
        config_subentries = settings_manager_subentries_from_path(entry_path)

        if len(config_subentries) > 0:
            self.show_subentries(config_subentries, f'Loading {self.entry_type.capitalize()}: {self.entry}')

        for ind, entry in enumerate(config_subentries):
            subentry_handler = handler_factory.get_subentry_handler(entry.entry_type)(
                self.config_model, self.settings, self)
            try:
                subentry_handler.execute_subentry(entry, manager=self)
                self.subentries_model.set_status(ind, True)
                QtWidgets.QApplication.processEvents()
                QtCore.QThread.msleep(0)
            except (SubEntryError, NotImplementedError) as e:
                logger.exception(str(e))
                self.subentries_model.set_status(ind, False)

        self.close_subentries_display(1000)

        return True

    def setup_docks_and_widgets(self):
        super().setup_docks_and_widgets()
        self.main_widget.layout().insertWidget(0, self.modules_manager.settings_tree)
        self.main_widget.layout().insertWidget(1, self.scanner.parent_widget)


if __name__ == "__main__":
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import create_load_dashboard
    from pymodaq.utils.gui_utils.loader_utils import create_extension
    from pymodaq.extensions import DAQScan

    app = mkQApp('ScannerManager')

    win, dashboard = create_load_dashboard()
    win.mainwindow.setVisible(False)
    scan: DAQScan
    win_ext, scan = create_extension(dashboard, DAQScan)
    win_ext.show()

    scan.scan_manager.show()

    sys.exit(app.exec())

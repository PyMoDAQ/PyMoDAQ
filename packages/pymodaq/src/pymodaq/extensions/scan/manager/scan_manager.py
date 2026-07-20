from copy import deepcopy
from typing import Union, TYPE_CHECKING
from pathlib import Path
import sys

import toml
from qtpy import QtWidgets, QtCore, QtGui

from pymodaq_data import DataDim
from pymodaq_gui.utils.widgets.widget_with_label_title import WidgetWithLabelTitle
from pymodaq_utils.enums import StrEnum
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import GlobalConfig as Config, get_set_config_dir

from pymodaq_gui.parameter import ParameterTree
from pymodaq_gui.managers.settings.utils import (
    SettingsManagerParameterTree, SettingsManagerModel, SettingsManagerTableView,
    settings_manager_subentries_from_path, ParameterDelegate,
    EntryActions, ModuleType)

from pymodaq.extensions.scan.manager.subentries import (
    SubEntryHandlerFactory, SubEntryHandler, SubEntryError,
    SubEntryHandlerTypes, ScanSubEntry, ParameterWithPath, ScanSettingsEntryHandler,
    ControlModulesEntryHandler, ScannnerEntryHandler, StartScanEntryHandler)

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

    entry_type = 'scans'
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

    def _update_entry(self, entry: Union[str, Path] = None, **kwargs):
        # read binary file content and return a list of SubEntry
        data: list[ScanSubEntry] = settings_manager_subentries_from_path(Path(entry))

        # update control modules
        ControlModulesEntryHandler.update(self, data.pop(0))

        # update scanner
        ScannnerEntryHandler.update(self, data.pop(0))



        #populate the Settings Table
        self.config_model.load(data[:-1])

        # set the start scan action
        self.set_action_checked('start_scan', data[-1].setting.value())


    def save_entries(self, entry_path: Path = None):
        # first save an entry corresponding to the selected detectors and actuators
        modules_entry = ControlModulesEntryHandler.create_subentry(self)
        with open(entry_path, mode='wb') as file:
            file.write(modules_entry.serialize(modules_entry))

        # then save an entry corresponding to the scanner
        scanner_entry = ScannnerEntryHandler.create_subentry(self)
        with open(entry_path, mode='ab') as file:
            file.write(scanner_entry.serialize(scanner_entry))

        # then save the various settings about the scan flow or h5saver
        self.config_model.save(entry_path, mode='ab')

        # then save an entry corresponding to the start scan status
        start_entry = StartScanEntryHandler.create_subentry(self)
        with open(entry_path, mode='ab') as file:
            file.write(start_entry.serialize(start_entry))

    def connect_things(self):
        super().connect_things()
        self.modules_manager.actuators_changed.connect(self.update_scanner_actuators)
        self.get_data_pb.clicked.connect(self.probe_data)

    def probe_data(self):
        self.modules_manager.connect_detectors()
        dte = self.modules_manager.grab_data()
        self.modules_manager.connect_detectors(False)

        data_0D = dte.get_full_names(DataDim.Data0D)
        data_1D = dte.get_full_names(DataDim.Data1D)

        self.settings['daq_scan', 'plot_options', 'plot_0d'] = dict(all_items=data_0D,
                                                        selected=[])
        self.settings['daq_scan', 'plot_options', 'plot_1d'] = dict(all_items=data_1D,
                                                        selected=[])

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
            entry = ScanSubEntry(
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
        widget = QtWidgets.QWidget()
        configure_scan_widget = WidgetWithLabelTitle('(1) Configure a Scan:', widget)
        self.get_data_pb = QtWidgets.QPushButton('ProbeData')
        get_data_widget = WidgetWithLabelTitle('(2) Get Data To Plot:', self.get_data_pb)
        widget.setLayout(QtWidgets.QVBoxLayout())
        widget.layout().addWidget(self.modules_manager.settings_tree)
        widget.layout().addWidget(self.scanner.parent_widget)
        self.main_widget.layout().insertWidget(0, configure_scan_widget)
        configure_scan_widget.insert_widget(get_data_widget, 2)
        for child_name in ('probe_data', 'test_actuator'):
            self.modules_manager.settings.child(child_name).show(False)
        self.main_widget.layout().setStretch(0, 1)
        self.main_widget.layout().setStretch(1, 3)

        self.settings_to_pick.set_title('(3) Select Settings to Apply:')
        self.add_toolbar('after_settings','After Settings Applied')
        self.add_action('start_scan', 'Start Scan', 'motion_play',
                        tip="Start the scan after all settings have been applied.",
                        auto_menu=False, toolbar='after_settings', checkable=True,
                        icon_color=self.get_theme().red,
                        icon_checked_color=self.get_theme().green)
        self.settings_to_apply.set_title('(i) Settings to Apply:')
        self.settings_to_apply.insert_widget(
            WidgetWithLabelTitle('(ii) StartScan...or not',
                                 self.get_toolbar('after_settings')), 2)


if __name__ == "__main__":
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import create_load_dashboard
    from pymodaq.utils.gui_utils.loader_utils import create_extension
    from pymodaq.extensions import DAQScan

    app = mkQApp('ScannerManager')

    win, dashboard = create_load_dashboard()
    win.mainwindow.setVisible(False)
    dashboard.experiment_manager.execute_entry()
    QtWidgets.QApplication.processEvents()

    scan: DAQScan
    win_ext, scan = create_extension(dashboard, DAQScan)
    win_ext.show()

    sys.exit(app.exec())

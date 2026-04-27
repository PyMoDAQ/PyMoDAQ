from pathlib import Path
from typing import TYPE_CHECKING

from pyqtgraph.parametertree import Parameter
from qtpy import QtWidgets

from pymodaq_gui.h5modules.saving import H5Saver
from pymodaq_utils.config import get_set_path, get_set_local_dir
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_data.data import DataDim

from pymodaq_gui.managers.manager_base import ManagerBase
from pymodaq_gui.parameter import ioxml

from pymodaq.utils.scanner.scanner import Scanner


if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard
    from pymodaq.extensions.scan.daq_scan import DAQScan


EXTENSION_PATH = get_set_path(get_set_local_dir(user=True), 'DAQ_SCAN')
logger = set_logger(get_module_name(__file__))

class ScanManager(ManagerBase):

    entry_type = 'Scanner'
    entry_extension ='.xml'
    icon_name = 'qr_code_scanner'


    def __init__(self,
                 dashboard: 'DashBoard' = None,
                 daq_scan: 'DAQScan' = None,):

        if dashboard is not None:
            self._scanner = Scanner(actuators=dashboard.actuators_modules)
        else:
            self._scanner = None

        if daq_scan is not None:
            self._daq_scan = daq_scan
            self.params = daq_scan.params

        else:
            self._daq_scan = None
            self.params = []

        self._h5saver = H5Saver()
        self._h5saver.settings.child('do_save').hide()
        self._h5saver.settings.child('custom_name').hide()

        super().__init__(dashboard=dashboard)

    def do_things_after_ui_setup(self):
        self.main_widget.layout().insertWidget(1, self.scanner.parent_widget)

    @property
    def daq_scan(self) -> 'DAQScan':
        return self._daq_scan

    @property
    def scanner(self) -> Scanner:
        return self._scanner

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        """Get the folder path where the managed entries are stored."""
        return get_set_path(EXTENSION_PATH, 'scanners')

    def setup_docks_and_widgets(self):
        self.main_widget.setLayout(QtWidgets.QHBoxLayout())
        self.main_widget.layout().addWidget(self.modules_manager.settings_tree)
        self.main_widget.layout().addWidget(self.settings_tree)
        self.main_widget.layout().addWidget(self._h5saver.settings_tree)

    def value_changed(self, param: Parameter):
        if param.name() == 'plot_probe':
            self.plot_from()

    def plot_from(self):
        self.modules_manager.get_det_data_list()
        data0D_names = self.modules_manager.get_probed_data_full_names(DataDim.Data0D)
        data1D_names = self.modules_manager.get_probed_data_full_names(DataDim.Data1D)
        self.settings.child('plot_options', 'plot_0d').setValue(
            dict(all_items=data0D_names, selected=data0D_names))
        self.settings.child('plot_options', 'plot_1d').setValue(
            dict(all_items=data1D_names, selected=data1D_names))

    def save_entries(self, entry_path: Path = None):
        """ Particular implementation to save entries for this inherited Manager """
        if entry_path is None:
            entry_path = self.entry_filepath

        settings_to_save = Parameter.create(name='settings_to_save', type='group',
                                            children= [param.saveState() for param in self.settings_to_save_load()]
                                            )

        ioxml.parameter_to_xml_file(
            settings_to_save,
            entry_path,
            overwrite=True,
        )

    def settings_to_save_load(self) -> list[Parameter]:
        return [self.modules_manager.settings,
                self.scanner.settings,
                self.scanner.scanner.settings,
                self.settings,
                self._h5saver.settings,
                ]

    def _update_entry(self, entry_path: Path):
        """ Particular implementation to update entries for this inherited Manager """
        settings_to_load = self.settings_to_save_load()

        setting_from_file = Parameter.create(**ioxml.xml_file_to_parameter_dict(entry_path))

        for ind, setting in enumerate(setting_from_file.children()):
            settings_to_load[ind].restoreState(setting.saveState())

    def do_things_for_new_creation(self):
        """ To be reimplemented if needed """
        self.modules_manager.set_detectors(self.modules_manager.detectors_all, self.modules_manager.detectors_all)
        self.modules_manager.set_actuators(self.modules_manager.actuators_all, self.modules_manager.actuators_all)

    def _execute_entry(self, entry: Path = None, **kwargs) -> bool:
        """ Execute the selected entry file and update the DAQ_Scan settings with them

        Returns True if the entry has been applied otherwise False

        Should not be called directly, use :attr:`execute_entry` instead.
        """
        try:
            self.daq_scan.modules_manager.selected_actuators_name = self.modules_manager.selected_actuators_name
            self.daq_scan.modules_manager.selected_detectors_name = self.modules_manager.selected_detectors_name

            self.daq_scan.settings = self.settings.saveState()

            self.daq_scan.scanner.set_scan_from_settings(self.scanner.settings, self.scanner.scanner.settings)

            self.daq_scan.h5saver.settings = self._h5saver.settings.saveState()

            return True
        except Exception as e:
            logger.exception(str(e))
        finally:
            return False


if __name__ == '__main__':
    import sys
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import DashBoard, create_load_dashboard

    app = mkQApp('ExperimentManager')

    shared_ui, dashboard = create_load_dashboard()
    dashboard.experiment_manager.entry = 'mock_holo'
    dashboard.experiment_manager.execute_entry()
    shared_ui.show()

    prog = ScanManager(dashboard=dashboard)
    external_ui = QtWidgets.QMainWindow()

    toolbar, menu = prog.get_external_toolbar_menu()
    external_ui.addToolBar(toolbar)
    external_ui.menuBar().addMenu(menu)

    prog.mainwindow.show()
    prog.enable_actions(True)
    external_ui.show()
    sys.exit(app.exec())

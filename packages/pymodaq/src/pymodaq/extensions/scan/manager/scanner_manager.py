from copy import deepcopy
from typing import Union, TYPE_CHECKING
from pathlib import Path
import sys

import toml
from qtpy import QtWidgets, QtCore, QtGui
from serializall import SerializableFactory, SerializableBase

from pymodaq_data import DataDim
from pymodaq_gui.managers.manager_base import ManagerBase
from pymodaq_gui.utils.widgets.widget_with_label_title import WidgetWithLabelTitle
from pymodaq_utils.enums import StrEnum
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import GlobalConfig as Config, get_set_config_dir

from pymodaq_gui.parameter import ParameterTree


from pymodaq.utils.scanner.scanner import Scanner


if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard


logger = set_logger(get_module_name(__file__))

ser_factory = SerializableFactory()
config = Config()



class ScannerManager(ManagerBase):
    """
    Main class managing settings values to be restored in the Scanner part of a DAQScan (or elsewhere)
    """

    entry_type = 'scanners'
    entry_extension ='.scanner'
    icon_name = 'qr_code_scanner'

    params = [
        {'title': 'Actuators:', 'name': 'actuators', 'type': 'itemselect', }
    ]

    def __init__(self, dashboard: 'DashBoard'):
        self.scanner: Scanner = Scanner(actuators=dashboard.actuators_modules)
        super().__init__(dashboard)


    def _update_entry(self, entry: Union[str, Path] = None, **kwargs):
        with open(entry, mode='rb') as file:
            all_bytes = file.readlines()
        data = ser_factory.get_apply_deserializer(all_bytes)

    def save_entries(self, entry_path: Path = None):
        with open(entry_path, mode='wb') as file:
            file.write(ser_factory.get_apply_serializer(self.settings['actuators']))

    def connect_things(self):
        super().connect_things()
        self.modules_manager.actuators_changed.connect(self.update_scanner_actuators)

    def update_scanner_actuators(self):
        self.scanner.actuators = self.modules_manager.actuators

    def get_entry_folder(self, subfolder='', user=True) -> Path:
        """Get the folder path where the managed entries are stored."""
        if subfolder != '':
            target_path = get_set_config_dir('scanners', user=user).joinpath(subfolder)
        else:
            target_path = get_set_config_dir('scanners', user=user)
        target_path.mkdir(parents=True, exist_ok=True)
        return target_path


    def _execute_entry(self, entry_path: Path = None, **kwargs) -> bool:
        """Applies the entry from the given file in the manager.

        Parameters:
        -----------
        file : Path
            The path to the settings file to be applied.
        """

    def setup_docks_and_widgets(self):
        super().setup_docks_and_widgets()
        self.main_widget.layout().addWidget(self.scanner.parent_widget)


if __name__ == "__main__":
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import create_load_dashboard

    app = mkQApp('ScannerManager')

    win, dashboard = create_load_dashboard()


    scan_manager = ScannerManager(dashboard)
    scan_manager.show()




    sys.exit(app.exec())

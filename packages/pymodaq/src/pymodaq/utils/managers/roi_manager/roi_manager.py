import dataclasses
from typing import Union, TYPE_CHECKING, Callable
from pathlib import Path
import sys

from qtpy import QtWidgets, QtCore

from pymodaq.utils.managers.roi_manager.utils import get_set_roi_path
from pymodaq_data import DataWithAxes, DataToExport
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq.utils.config import get_set_experiment_path

from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq_gui.managers.manager_base import ManagerBase

if TYPE_CHECKING:
    pass

logger = set_logger(get_module_name(__file__))


class ROIManager(ManagerBase):
    """
    Base class for Manager directly depending on the status of the experiment manager
    To be reimplemented

    """

    entry_type = 'roi'
    entry_extension ='.xml'
    in_user_folder = True
    icon_name = 'select'

    def __init__(self, dashboard: 'DashBoard' = None, **kwargs):

        super().__init__(dashboard=dashboard, **kwargs)

    def setup_docks_and_widgets(self):
        self.main_widget.setLayout(QtWidgets.QHBoxLayout())
        self.main_widget.layout().addWidget(self.settings_tree)

    def save_entries(self, entry_path: Path = None):
        ioxml.parameter_to_xml_file(self.settings, entry_path)

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        return get_set_roi_path()

    def _update_entry(self, entry_path: Path):
        """ Particular implementation to update entries for this inherited Manager """
        pass



if __name__ == "__main__":
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import DashBoard, create_load_dashboard

    app = mkQApp('ROI Manager')
    shared_ui, dashboard = create_load_dashboard()
    shared_ui.hide()

    prog = ROIManager(dashboard)
    prog.enable_actions(True)
    prog.mainwindow.show()

    sys.exit(app.exec())

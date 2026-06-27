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

    params = [{'title': 'Viewers:', 'name': 'viewers', 'type': 'itemselect',
               'value': {'all_items': [], 'selected': []}}]

    def __init__(self, dashboard: 'DashBoard' = None, **kwargs):
        super().__init__(dashboard=dashboard, **kwargs)
        self.update_viewer_list()

    def do_things_after_experiment_set(self, experiment_name: str):
        super().do_things_after_experiment_set(experiment_name)
        self.update_viewer_list()

        experiment_name = self.dashboard.experiment_name
        if experiment_name not in self.entries:
            self.create_entry(experiment_name, bypass_dialog=True)
        self.update_entry(experiment_name)

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        self.create_dashboard_toolbar()
        self.mainwindow.insertToolBar(self.toolbar, self.get_toolbar('dashboard'), )
        self.mainwindow.addToolBarBreak(QtCore.Qt.TopToolBarArea)
        self.add_toolbar('management', 'Management',
                         parent=self.mainwindow,
                         add_break=True, before=self.toolbar)

    def setup_docks_and_widgets(self):
        self.main_widget.setLayout(QtWidgets.QHBoxLayout())
        self.main_widget.layout().addWidget(self.settings_tree)

    def setup_actions(self):
        self.add_action('update_viewers', 'Update viewers', 'refresh',
                        tip='Refresh the viewers list',
                        toolbar='management',
                        auto_menu=True)

    def connect_things(self):
        self.connect_action('update_viewers', self.update_viewer_list)

    def save_entries(self, entry_path: Path = None):
        ioxml.parameter_to_xml_file(self.settings, entry_path)

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        return get_set_roi_path()

    def _update_entry(self, entry_path: Path):
        """ Particular implementation to update entries for this inherited Manager """
        pass

    def update_viewer_list(self):

        viewers_name = []
        for detector in self.modules_manager.detectors_all:
            for viewer in detector.viewers:
                viewers_name.append(f'{detector.title}/{viewer.title}')
        self.settings.child('viewers').setValue({'all_items': viewers_name,
                                                 'selected': viewers_name})



if __name__ == "__main__":
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import DashBoard, create_load_dashboard

    app = mkQApp('ROI Manager')
    shared_ui, dashboard = create_load_dashboard()
    shared_ui.hide()

    prog = dashboard.roi_manager
    prog.enable_actions(True)
    prog.mainwindow.show()

    sys.exit(app.exec())

import dataclasses

from typing import Union, TYPE_CHECKING, Callable
from pathlib import Path
import sys

from qtpy import QtWidgets, QtCore

from pymodaq.utils.managers.roi_manager.utils import get_set_roi_path
from pymodaq_data import DataWithAxes, DataToExport
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.plotting.data_viewers import Viewer1D, Viewer2D
from pymodaq_gui.plotting.items.roi_sync import RoiParameter
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq.utils.config import get_set_experiment_path

from pymodaq_gui.parameter import Parameter, ParameterTree
from pymodaq_gui.managers.manager_base import ManagerBase
from pymodaq_gui.parameter.utils import ParameterWithPath
from pymodaq_utils.utils import find_objects_in_list_from_attr_name_val

from serializall.factory import SerializableFactory


if TYPE_CHECKING:
    pass

logger = set_logger(get_module_name(__file__))
ser_factory = SerializableFactory()


class ROIList(ParameterManager):
    params = [{'title': 'ROIs', 'name': 'rois', 'type': 'itemselect', 'checkbox': True}]


class ROIManager(ManagerBase):
    """
    Base class for Manager directly depending on the status of the experiment manager
    To be reimplemented

    """

    entry_type = 'roi'
    entry_extension ='.rois'
    in_user_folder = True
    icon_name = 'select'

    params = [{'title': 'Viewers:', 'name': 'viewers', 'type': 'itemselect', 'readonly': True,
               'value': {'all_items': [], 'selected': []}}]

    def __init__(self, dashboard: 'DashBoard' = None, **kwargs):

        self.saved_rois = ROIList()

        super().__init__(dashboard=dashboard, **kwargs)
        self.update_viewer_list_from_dashboard()


    def do_things_after_experiment_set(self, experiment_name: str):
        super().do_things_after_experiment_set(experiment_name, show_dashboard=True)
        self.update_viewer_list_from_dashboard()

        experiment_name = self.dashboard.experiment_name
        if experiment_name not in self.entries:
            self.create_entry(experiment_name, bypass_dialog=True)
        self.update_entry(experiment_name)

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        self.add_toolbar('management', 'Management',
                         parent=self.mainwindow,
                         add_break=True, before=self.toolbar)

    def setup_docks_and_widgets(self):
        self.main_widget.setLayout(QtWidgets.QHBoxLayout())
        self.main_widget.layout().addWidget(self.settings_tree)

        self.main_widget.layout().addWidget(self.saved_rois.settings_tree)

    def value_changed(self, param: Parameter):
        if param.name() == 'viewers':
            self.update_roi_list()


    def setup_actions(self):
        self.add_action('update_viewers', 'Update viewers', 'refresh',
                        tip='Refresh the viewers list',
                        toolbar='management',
                        auto_menu=True)

    def connect_things(self):
        self.connect_action('update_viewers', self.update_viewer_list_from_dashboard)

    def save_entries(self, entry_path: Path = None):
        objects = []
        for subentry in self.saved_rois.settings['rois']['selected']:
            module_name, viewer_name, roi_name, descriptor = subentry.split('/')
            detector = self.modules_manager.get_mod_from_name(module_name)
            if detector is not None:
                viewer: Viewer1D | Viewer2D = find_objects_in_list_from_attr_name_val(detector.viewers, 'title', viewer_name)[0]
                if viewer.roi_manager is not None:
                    param = ParameterWithPath(viewer.roi_manager.rois_setting.child(roi_name),
                                              [module_name, viewer_name, roi_name])
                    objects.append(param)

        with open(entry_path, 'wb') as file:
            file.write(ser_factory.get_apply_serializer(objects))

        self.update_roi_list_from_entry(entry_path)

    def update_roi_list_from_entry(self, entry_path: Path):

        roi_list = []
        with open(entry_path, 'rb') as file:
            bytes = file.read()
        objects: list[ParameterWithPath] = ser_factory.get_apply_deserializer(bytes)
        for pwp in objects:
            module_name, viewer_name, roi_name = pwp.path

            roi_list.append(self.format_roi(pwp.parameter,
                                            module_name,
                                            viewer_name))

        self.saved_rois.settings.child('rois').setValue({'all_items': roi_list,
                                                         'selected': roi_list})

    def _execute_entry(self, entry_path: Path = None, **kwargs) -> bool:
        with open(entry_path, 'rb') as file:
            bytes = file.read()
        objects: list[ParameterWithPath] = ser_factory.get_apply_deserializer(bytes)
        objects_as_dicts = self.sort_rois_in_dict(objects)
        for module_name in objects_as_dicts:
            detector = self.modules_manager.get_mod_from_name(module_name)
            for viewer_name in objects_as_dicts[module_name]:
                viewer: Viewer1D | Viewer2D = \
                find_objects_in_list_from_attr_name_val(detector.viewers, 'title', viewer_name)[0]
                viewer.do_math()
                viewer.roi_manager.clear_settings_slot()
                with viewer.roi_manager.rois_setting.treeChangeBlocker() as blocker:
                    viewer.roi_manager.rois_setting.addChildren(
                        objects_as_dicts[module_name][viewer_name])
        return True

    def sort_rois_in_dict(self, pwps: list[ParameterWithPath]) -> \
            dict[str, dict[str, list[Parameter]]]:
        """ sort the list of ROIs by detector first then by viewer"""

        pwps_in_dict = {}
        for pwp in pwps:
            if pwp.path[0] not in pwps_in_dict:
                pwps_in_dict[pwp.path[0]] = {}

            if pwp.path[1] not in pwps_in_dict[pwp.path[0]]:
                pwps_in_dict[pwp.path[0]][pwp.path[1]] = []
            pwps_in_dict[pwp.path[0]][pwp.path[1]].append(pwp.parameter)
        return pwps_in_dict

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        return get_set_roi_path()

    def _update_entry(self, entry_path: Path):
        """ Particular implementation to update entries for this inherited Manager """
        self.update_roi_list_from_entry(entry_path)

    def update_roi_list(self):
        roi_list = []
        for subentry in self.settings['viewers']['selected']:
            module_name, viewer_name = subentry.split('/')
            detector = self.modules_manager.get_mod_from_name(module_name)
            viewer: Viewer1D | Viewer2D = find_objects_in_list_from_attr_name_val(detector.viewers, 'title', viewer_name)[0]
            if viewer.roi_manager is not None:
                for roi_meta in viewer.roi_manager.ROIs:
                    roi_list.append(self.format_roi(roi_meta.param,
                                                    module_name,
                                                    viewer_name))
        self.saved_rois.settings.child('rois').setValue({'all_items': roi_list,
                                                         'selected': roi_list})

    @staticmethod
    def format_roi(roi_param: RoiParameter, module_name: str, viewer_name: str):
        return f'{module_name}/{viewer_name}/'\
               f'{roi_param.name()}/{roi_param.descriptor}'

    def update_viewer_list_from_dashboard(self):
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

    prog = dashboard.roi_manager
    prog.enable_actions(True)
    prog.mainwindow.show()

    # def add_rois():
    #     for detector in dashboard.modules_manager.detectors_all:
    #         for viewer in detector.viewers:
    #             if isinstance(viewer, Viewer1D):
    #                 viewer.get_action('do_math').trigger()
    #                 for _ in range(2):
    #                     viewer.roi_manager.add_roi_programmatically()
    #             elif isinstance(viewer, Viewer2D):
    #                 viewer.get_action('roi').trigger()
    #                 viewer.roi_manager.add_roi_programmatically()
    #
    # dashboard.experiment_manager.applied_entry.connect(add_rois)
    dashboard.experiment_manager.execute_entry('default')



    sys.exit(app.exec())

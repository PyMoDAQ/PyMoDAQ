from typing import Union, TYPE_CHECKING

from pymodaq.control_modules.enums import DAQTypesEnum

from pathlib import Path
import sys

from qtpy import QtWidgets

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.messenger import dialog

from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter import ioxml

from pymodaq.utils.config import get_set_experiment_path, get_set_overshoot_path, get_set_state_path, get_set_remote_path
from pymodaq_gui.config import get_set_layout_path, get_set_roi_path
from pymodaq_gui.managers.manager_base import ManagerBase
from pymodaq.utils.managers.modules.utils import ModuleType
from pymodaq.utils.managers.modules.loader import PluginInfo, ModuleLoader

from pymodaq.control_modules.utils import ControllerStatus
from pymodaq.utils.daq_utils import copy_experiment
from pymodaq.utils.managers.experiment import utils  # noqa , to register groupemove and groupdet Parameters
from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.control_modules.daq_viewer import DAQ_Viewer
if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard


logger = set_logger(get_module_name(__file__))

# check if experiment directory exists on the drive
experiment_path = get_set_experiment_path()
overshoot_path = get_set_overshoot_path()
layout_path = get_set_layout_path()


class ExperimentManager(ManagerBase):

    params_act = [{'title': 'Actuators:', 'name': ModuleType.Actuator.value, 'type': 'groupmove'}]
    params_det = [{'title': 'Detectors:', 'name': ModuleType.Detector.value, 'type': 'groupdet'}]

    params = params_act + params_det

    entry_type = 'experiment'
    entry_extension ='.xml'
    icon_name = 'experiment'

    def __init__(self,
                 dashboard: 'DashBoard' = None):

        super().__init__(dashboard=dashboard)
        self.actuators_modules: list[DAQ_Move] = []
        self.detector_modules: list[DAQ_Viewer] = []
        self.loader: ModuleLoader = None

    ### Reimplemented Methods ####################################################
    def list_managed_entries_path(self, **kwargs_to_entry_folder) -> list[Path]:
        """Should return a list of Path objects representing managed entries.

        Example:
        --------
        [path for path in get_set_experiment_path().iterdir() if path.suffix == self.entry_extension]
        """
        entry_path = self.get_entry_folder(**kwargs_to_entry_folder)
        if not entry_path.exists():
            entry_path.mkdir(parents=True)
        if not entry_path.joinpath(f'default{self.entry_extension}').exists():
            copy_experiment()
            self.update_entry()
        return [path for path in entry_path.iterdir() if path.suffix == self.entry_extension]

    def do_things_for_new_creation(self):
        for child in self.settings.child(ModuleType.Actuator.value).children():
            child.remove()
        for child in self.settings.child(ModuleType.Detector.value).children():
            child.remove()

    def save_entries(self, entry_path: Path = None):
        """ Particular implementation to save entries for this inherited Manager """

        if entry_path is None:
            entry_path = self.entry_filepath

        ioxml.parameter_to_xml_file(
            self.settings,
            entry_path,
            overwrite=True,
        )

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        """Get the folder path where the managed entries are stored."""
        return get_set_experiment_path()

    def _execute_entry(self, entry: Path = None, **kwargs) -> bool:
        """ Execute the selected entry file to the dashboard and adds Control Modules specified in it

        Returns True if the entry has been applied otherwise False

        Should not be called directly, use :attr:`execute_entry` instead.
        """
        try:
            if len(self.dashboard.actuators_modules) != 0 or len(self.dashboard.detector_modules) != 0:
                ret = dialog(title=f'Warning!',
                             message=f'Are you sure you want '
                                     f'to load a new {self.entry_type.capitalize()}: {entry.stem}? \n')
                if ret:
                    self.dashboard.remove_actuators(self.dashboard.actuators_modules)
                    self.dashboard.remove_detectors(self.dashboard.detector_modules)
                    for area in self.dashboard.dockarea.tempAreas:
                        area.window().close()
                else:
                    return False

            plugins_sorted, plugin_list_message = self.list_control_modules_from_preset()

            self.show_subentries(plugin_list_message, title=f'Loading Experiment: {self.entry}')

            self.dashboard.mainwindow.setVisible(False)
            for area in self.dashboard.dockarea.tempAreas:
                area.window().setVisible(False)

            QtWidgets.QApplication.processEvents()
            logger.info(f"Loading {self.entry_type.capitalize()} file: {entry}")

            self.load_control_modules(plugins_sorted)

        except Exception as e:
            self._on_load_failed(e)
            return False

    def finalize_execute(self, modules: list[DAQ_Viewer | DAQ_Move] = None):
        self.close_subentries_display()
        self.dashboard.title = self.entry
        self.dashboard.mainwindow.setWindowTitle(f"PyMoDAQ Dashboard: {self.dashboard.title}")


        self.dashboard.update_status(
            f"{self.entry_type.capitalize()} ({self.entry_filepath.name}) has been loaded",
            log_type="log",
        )
        self.dashboard.actuators_modules = [mod for mod in modules if isinstance(mod, DAQ_Move)]
        self.dashboard.detector_modules = [mod for mod in modules if isinstance(mod, DAQ_Viewer)]

        self.dashboard.mainwindow.setVisible(True)
        for area in self.dashboard.dockarea.tempAreas:
            area.window().setVisible(True)

        self.dashboard.update_init_tree()

        logger.info(f"{self.entry_type.capitalize()} file: {self.entry_filepath} has been loaded")
        self.set_entry_applied(True)

    def _on_load_failed(self, message: str):
        self.close_subentries_display()
        self.dashboard.mainwindow.setVisible(True)
        for area in self.dashboard.dockarea.tempAreas:
            area.window().setVisible(True)
        logger.info(message)

    def _update_entry(self, entry: Union[str, Path] = None, **kwargs):
        """ Update the Manager UI after a given entry as been selected/updated """
        if entry.exists():
            self.settings = entry
        else:

            self.settings = Parameter.create(title='Preset', name='Preset', type='group',
                                             children=self.params)

    def setup_actions(self):
        #  nothing more than the base actions from the base class
        pass

    def connect_things(self):
        self.new_entry.connect(self.remove_preset_related_files)
        self.deleted_entry.connect(self.remove_preset_related_files)

    @staticmethod
    def remove_preset_related_files(preset_name: str):
        for file in get_set_state_path(preset_name).iterdir():
            file.unlink(missing_ok=True)
        get_set_state_path(preset_name).rmdir()
        get_set_roi_path().joinpath(preset_name).unlink(missing_ok=True)
        get_set_layout_path().joinpath(preset_name).unlink(missing_ok=True)
        get_set_overshoot_path().joinpath(preset_name).unlink(missing_ok=True)
        get_set_remote_path().joinpath(preset_name).unlink(missing_ok=True)


    @staticmethod
    def _group_plugins_by_id(plugins: list[PluginInfo]) -> list[list[PluginInfo]]:
        """Group a flat list of plugin dicts by their 'ID' key, sorted by 'status' within each group."""
        IDs = list(set(plug.id for plug in plugins))

        plugins_sorted = []
        for id in IDs:
            plug_ids: list[PluginInfo] = [plug for plug in plugins if plug.id == id]  # group plugins having the same id
            plug_ids.sort(key=lambda p: p.is_master, reverse=True)  # sort them with the fist being Master (
            plugins_sorted.append(plug_ids)
        return plugins_sorted

    def list_control_modules_from_preset(self) -> tuple[list[list[PluginInfo]], list[str]]:
        # ################################################################

        # ##### sort plugins by IDs and within the same IDs by Master and Slave status
        plugins: list[PluginInfo] = []

        for child in (self.settings.child(ModuleType.Actuator.value).children() +
            self.settings.child(ModuleType.Detector.value).children()):
            plugins.append(
                PluginInfo(
                    id = child['controller', 'controller_ID'],
                    name = child['name'],
                    class_name=child['info', 'type'],
                    type = ModuleType.Actuator if ModuleType.Actuator.value.lower() == child.parent().name().lower() else ModuleType.Detector,
                    settings=child,
                    is_master=child["controller", "controller_status"] == ControllerStatus.MASTER.value,
                    do_init=child['info', 'init'],
                    ui = child['info', 'ui'] if 'ui' in [ch.name() for ch in child.child('info').children()] else None,
                    daq_type=DAQTypesEnum[child['info', 'dim']] if 'dim' in [ch.name() for ch in child.child('info').children()] else None,
                )
            )

        plugins_sorted = self._group_plugins_by_id(plugins)

        plugin_list_message = []
        for plug_id in plugins_sorted:
            for plugin in plug_id:
                plugin_list_message.append(
                    f"Initializing {plugin.class_name} {plugin.type.value.capitalize()}:"
                    f" {plugin.name}")

        return plugins_sorted, plugin_list_message

    def load_control_modules(self, plugins_sorted: list[list[PluginInfo]]):
        """
        Load an experiment file and create the corresponding Control Modules in the Dashboard.

        Modules are created/configured/initialized one at a time by :class:`ModuleLoader`,
        which waits on each module's own signals (rather than polling) since hardware
        initialization runs asynchronously on the module's own thread.
        """
        self.actuators_modules: list[DAQ_Move] = []
        self.detector_modules: list[DAQ_Viewer] = []

        self.loader = ModuleLoader(self.dashboard, plugins_sorted)
        self.loader.all_instruments_added.connect(self.finalize_execute)
        self.loader.load_failed.connect(self._on_load_failed)
        self.loader.module_index_init.connect(self.subentries_model.set_status)
        self.loader.start()


if __name__ == '__main__':
    from pymodaq_gui.qt_utils import mkQApp

    app = mkQApp('ExperimentManager')

    prog = ExperimentManager()
    external_ui = QtWidgets.QMainWindow()

    toolbar, menu = prog.get_external_toolbar_menu()
    external_ui.addToolBar(toolbar)
    external_ui.menuBar().addMenu(menu)

    prog.update_entry()
    prog.enable_actions(True)
    prog.mainwindow.show()
    external_ui.show()
    sys.exit(app.exec())

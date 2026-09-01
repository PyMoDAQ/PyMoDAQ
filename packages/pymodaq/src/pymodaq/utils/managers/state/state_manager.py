
from typing import Union, TYPE_CHECKING
from pathlib import Path
import sys

import toml
from qtpy import QtWidgets, QtCore, QtGui
from serializall import SerializableFactory, SerializableBase

from pymodaq.utils.managers.modules import ModuleType
from pymodaq.utils.managers.modules.module_settings_manager import ModulesSettingsManager
from pymodaq.utils.managers.experiment.experiment_manager import ExperimentManager
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import GlobalConfig as Config, get_set_local_dir

from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq_gui.parameter.utils import ParameterWithPath


from pymodaq.utils.managers.state.subentries import (
    SubEntryHandlerFactory,
    StateSubEntryHandler,
    SubEntryError,
    StateSubEntryHandlerTypes,
    StateSettingsEntryHandler,
    SubEntry)
from pymodaq.utils.managers.state.utils import (
    get_module_from_param
    )

from pymodaq_gui.managers.settings.settings_manager import SettingsManager


from pymodaq.utils.config import get_set_state_path
from pymodaq_gui.managers.manager_base import ManagerBase, ManagerActions
from pymodaq.extensions import ExtensionEnum
from pymodaq.launcher import HISTORY_FILE_NAME, HISTORY_FILE_PATH

from datetime import datetime

from pymodaq_gui.managers.settings.utils import (
    SettingsManagerParameterTree, SettingsManagerModel, SettingsManagerTableView,
    settings_manager_subentries_from_path, ParameterDelegate,
    EntryActions, )


if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard

logger = set_logger(get_module_name(__file__))
handler_factory = SubEntryHandlerFactory()
ser_factory = SerializableFactory()
config = Config()


class StateManager(SettingsManager):
    """
    Main class managing the configuration of control modules from a Dashboard in terms
    of their settings and actuator's value.

    This class provides a GUI to create, modify and save configurations for different experiments (DashBoard state)
    controlling various modules (actuators, detectors...).

    """

    entry_type = 'state'
    entry_extension ='.state'
    icon_name = 'discover_tune'
    settings_handler = StateSubEntryHandlerTypes.SETTINGS

    def __init__(self,
                 dashboard: 'DashBoard' = None):

        self.subentry_handler: StateSubEntryHandler = None
        self.subentry_handlers: list[StateSubEntryHandler] = []
        self.config_model = SettingsManagerModel()

        if dashboard is None:
            self._experiment_manager_local = ExperimentManager()
        else:
            self._experiment_manager_local = dashboard.experiment_manager
        super().__init__(dashboard=dashboard,
                         handler_id=StateSettingsEntryHandler.handler_name)

        self._processed_subentries = 0

        self.history_file_path: str = HISTORY_FILE_PATH
        self.config_model.save_path = self.get_entry_folder()

        self.update_settings(self.settings)

    @property
    def experiment_manager(self) -> ExperimentManager:
        return self._experiment_manager_local

    def show(self):
        """ Open the StateManager User Interface

        If the Dashboard is not None and has a current experiment set, the state experiment name
        entry will be set as readonly and the settings are taken from the modules
        """
        if self.dashboard is not None:
            settings = ModulesSettingsManager().create_settings_all(
                self.dashboard.modules_manager.actuators_all,
                self.dashboard.modules_manager.detectors_all,
            )
            self.update_settings(settings)
        else:
            self.update_settings(self._experiment_manager_local.entry)

        super().show()

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        """Get the folder path where the managed entries are stored."""
        return get_set_state_path(self.experiment_filename)

    @staticmethod
    def get_module_from_param(param: ParameterWithPath) -> Union[str]:
        """ should return the module name from data bundled in the ParameterWithPath

        To be reimplemented

        Parameters
        ----------
        param: ParameterWithPath

        """
        module_name, module_type = get_module_from_param(param)
        return module_name

    def set_experiment_filename(self, name: str):
        """ convenience method to be used as slot in Qt connection"""
        self.experiment_filename = name

    @property
    def experiment_filename(self) -> str:
        try:
            return self.experiment_manager.entries_sync.value['current']
        except KeyError:  # not yet instantiated but need to be there
            return 'default'

    @experiment_filename.setter
    def experiment_filename(self, experiment_filename: str):
        if experiment_filename in self.experiment_manager.entries:
            self.experiment_manager.entries_sync.update_key('current', experiment_filename)
            self.entries_sync.set_value({**self.entries_sync.value, 'items': self.entries, 'current': self.entry})

    def add_subentry(self, special_entry_name: str):
        self.subentry_handler = handler_factory.get_subentry_handler(special_entry_name)(
            self.config_model,
            self.settings,
            actuators=self.actuators,
            detectors=self.detectors,
            extensions=self.extensions,
            dashboard=self.dashboard)
        self.subentry_handler.show_dialog()

    @staticmethod
    def format_subentries(entries: list[SubEntry]):
        return [(f'{entry.entry_type.capitalize()} for '
                 f'{entry.module_name} - '
                 f'{entry.setting.parameter.title()} '
                 f'{entry.setting.value()}') for entry in entries]

    def _execute_entry(self, entry_path: Path = None, **kwargs) -> None | bool:
        """Applies the entry from the given file in the manager.

        Parameters:
        -----------
        file : Path
            The path to the state file to be applied.
        """
        if entry_path is None:
            entry_path = self.entry_filepath

        self.config_subentries = settings_manager_subentries_from_path(entry_path)[1:]
        # first element is the parallel/sequential boolean

        self.subentry_handlers: list[StateSubEntryHandler] = []

        if self.experiment_manager.applied_entry_name != self.experiment_filename:
            logger.warning(f'The current state is referring to the experiment: {self.experiment_filename} '
                           f'while the current applied experiment is: {self.experiment_manager.applied_entry_name}')
            return False

        if len(self.config_subentries) > 0:
            self.show_subentries(self.config_subentries, f'Loading State: {self.entry}')

        self._ind_subentry = -1
        self._processed_subentries = 0

        self._advance()
        return None

    def _advance(self):
        self._ind_subentry += 1
        if self._ind_subentry == len(self.config_subentries):
            if not self.is_action_checked('parallel_execution'):
                self.finalize()
            return

        entry = self.config_subentries[self._ind_subentry]
        self.subentry_handlers.append(handler_factory.get_subentry_handler(entry.entry_type)(
            self.config_model,
            self.settings,
            actuators=self.actuators,
            detectors=self.detectors,
            ind_subentry=self._ind_subentry))
        try:
            self.subentry_handlers[-1].executed_signal.connect(self._on_executed)
            self.subentry_handlers[-1].execution_failed.connect(self._on_execution_failed)
            self.subentry_handlers[-1].execute_subentry(entry, dashboard=self.dashboard)

            if self.is_action_checked('parallel_execution'):
                self._advance()

        except SubEntryError as e:
            self._processed_subentries += 1
            logger.exception(str(e))
            self.subentries_model.set_status(self._ind_subentry, False)
            self._advance()

    def _on_execution_failed(self, exception: SubEntryError):
        msg = exception.args[0]
        ind_error = exception.args[1]

        logger.warning(msg)
        self.subentries_model.set_status(ind_error, False)
        self._processed_subentries += 1

        if not self.is_action_checked('parallel_execution'):
            logger.debug(f'Index in loop {self._ind_subentry}\n'
                         f'index from Signal: {ind_error}')
            self._advance()
        elif self._processed_subentries == len(self.config_subentries):
            self.finalize()

    def _on_executed(self, ind_subentry):
        self._processed_subentries += 1
        self.subentries_model.set_status(ind_subentry, True)
        if not self.is_action_checked('parallel_execution'):
            logger.debug(f'Index in loop {self._ind_subentry}\n'
                         f'index from Signal: {ind_subentry}\n'
                         f'Total calls {self._processed_subentries}')
            self._advance()
        elif self._processed_subentries == len(self.config_subentries):
            self.finalize()

    def finalize(self):
        self.close_subentries_display(100)
        self.save_new_history_entry()
        self.set_entry_applied(True)

    def populate_from_settings(self, settings: Parameter):
        """
        Initialize the state from a Parameter settings.

        Parameters
        ----------
        settings : Parameter
            Settings containing all modules configuration
        """
        self.settings = settings
        self.set_readonly_setting(self.settings)
        self.display_settings(display_all=False,
                              param=self.settings)
        self.set_drag_mode_recursive(self.settings, movable=True, drop_enabled=True)

    @property
    def actuators(self) -> list[str]:
        if self.dashboard is not None:
            return self.dashboard.modules_manager.actuators_name
        else:
            return [param.opts['title'] for param in self.settings.child(ModuleType.Actuator).children()]

    @property
    def detectors(self) -> list[str]:
        if self.dashboard is not None:
            return self.dashboard.modules_manager.detectors_name
        else:
            return [param.opts['title'] for param in self.settings.child(ModuleType.Detector).children()]

    @property
    def extensions(self) -> list[str]:
        return ExtensionEnum.values()

    def populate_from_file(self, file_path: Path):
        """ for quick testing purpose, not meant to be used at the end"""
        children = ioxml.XML_file_to_parameter(file_path)
        settings = Parameter.create(
            title="Control Modules:", name="control_modules", type="group", children=children,
        )
        self.populate_from_settings(settings)

    def setup_actions(self):
        super().setup_actions()
        self.add_action('parallel_execution', 'Sequential/parallel Execution',
                        'format_list_numbered',
                        tip='if green (unchecked) perform a sequential execution else parallel',
                        checkable=True, icon_color=self.get_theme().green,
                        icon_checked_color=self.get_theme().red,
                        before=self.get_action(ManagerActions.EXECUTE),)
        self.create_dashboard_toolbar(add_dashboard=__name__ == '__main__',
                                      add_experiment=True, add_state=False, add_break=False)
        self.experiment_manager.enable_actions(True)
        self.toolbar.addSeparator()

    def connect_things(self):
        super().connect_things()

        if self.dashboard is None:
            self.experiment_manager.enable_actions(True)
            self.experiment_manager.get_action(ManagerActions.EXECUTE).setVisible(False)

        else:
            self.experiment_manager.get_action(ManagerActions.LIST_EXTERNAL).widget.setEnabled(False)
            self.experiment_manager.applied_entry.connect(self.set_experiment_filename)  #action slot from experiment menu need this to update the list onf state entries

        self.experiment_manager.entries_sync.value_changed.connect(lambda value: self.set_experiment_filename(value['current']))

    def update_settings(self, settings: Union[Parameter, Path, str] = None):
        if settings is None:
            settings = self._get_settings_from_file()
            if settings == '':
                return
        if isinstance(settings, str):
            self._experiment_manager_local.entry = settings
            experiment_settings: Parameter = self._experiment_manager_local.settings
            settings = ModulesSettingsManager().create_settings_all(
                experiment_settings.child(ModuleType.Actuator.value).children(),
                experiment_settings.child(ModuleType.Detector.value).children(),
            )
        if isinstance(settings, Parameter):
            self.populate_from_settings(settings)
        elif isinstance(settings, Path):
            self.populate_from_file(settings)
            self.experiment_filename = settings.stem
        else:
            raise TypeError(f'Cannot load settings from {settings}, should be a Parameter or a Path')

    def save_new_history_entry(self):
        """Implements this method from ManagerBase. Save a new history entry with experiment and state for one time"""

        date = datetime.now().strftime("%Y-%d-%m:%H:%M:%S")

        entry = {date: {'experiment': self.experiment_manager.entry, 'state': self.entry}}

        try:
            existing = toml.load(self.history_file_path)
        except (FileNotFoundError, PermissionError, OSError):
            existing = {}

        new_dict = {key: value for i, (key, value) in enumerate(existing.items())
                    if i >= len(existing) - config('pymodaq', 'launcher', 'max_history_size') + 1
                    and (config('pymodaq', 'launcher', 'keep_duplicates')
                         or (value['experiment'] != entry[str(date)]['experiment']
                             or value['state'] != entry[str(date)]['state']))
                    }
        new_dict.update(entry)

        with open(self.history_file_path, "w") as f:
            toml.dump(new_dict, f)

    def _update_entry(self, entry: Union[str, Path] = None, **kwargs):
        # read binary file content and return a list of Serializables
        data: list[SerializableBase] = settings_manager_subentries_from_path(Path(entry))

        try:
            checked = data.pop(0)
        except IndexError:
            checked = False

        self.set_action_checked('parallel_execution', checked)

        #populate the Settings Table
        self.config_model.load(data)


    def save_entries(self, entry_path: Path = None):
        # first save the sequential or parallel execution

        try:
            parallel_execution = self.is_action_checked('parallel_execution')
        except KeyError:
            parallel_execution = False

        with open(entry_path, mode='wb') as file:
            file.write(ser_factory.get_apply_serializer(parallel_execution))

        # then save the various settings about the states
        self.config_model.save(entry_path, mode='ab')



if __name__ == "__main__":
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import DashBoard, create_load_dashboard

    app = mkQApp('StateManager')

    shared_ui, dashboard = create_load_dashboard()
    shared_ui.hide()

    prog = StateManager(dashboard)
    prog.update_settings('default')
    prog.mainwindow.show()
    prog.enable_actions(True)
    prog.experiment_manager.enable_actions(True)

    sys.exit(app.exec())

from typing import Union, TYPE_CHECKING
from pathlib import Path
import sys

import toml
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt
from qtpy.QtGui import QKeySequence
from qtpy.QtCore import QModelIndex

from pymodaq.utils.managers.modules.module_settings_manager import SettingsManager
from pymodaq.utils.managers.experiment.experiment_manager import ExperimentManager
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import GlobalConfig as Config, get_set_local_dir

from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq_gui.parameter.utils import ParameterWithPath

from pymodaq_gui.parameter.ioxml import VALID_FOR_CONFIGURATION

from pymodaq.utils.managers.state.subentries import (
    SubEntryHandlerFactory, SubEntryHandler, SubEntryError, SubEntryHandlerTypes, StateSubEntry)
from pymodaq.utils.managers.state.utils import (
    StateParameterTree, StateModel, StateTableView,
    get_module_from_param, state_subentries_from_path, ParameterDelegate,
    EntryActions, ModuleType)



from pymodaq.utils.config import get_set_state_path
from pymodaq_gui.managers.manager_base import ManagerBase, ManagerActions
from pymodaq.extensions import ExtensionEnum
from pymodaq.launcher import HISTORY_FILE_NAME, HISTORY_FILE_PATH

from datetime import datetime

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard


logger = set_logger(get_module_name(__file__))
handler_factory = SubEntryHandlerFactory()

config = Config()


class StateManager(ManagerBase):
    """
    Main class managing the configuration of control modules from a Dashboard in terms
    of their settings and actuator's value.

    This class provides a GUI to create, modify and save configurations for different experiments (DashBoard state)
    controlling various modules (actuators, detectors...).

    """

    entry_type = 'state'
    entry_extension ='.state'
    icon_name = 'discover_tune'

    def __init__(self,
                 dashboard: 'DashBoard' = None):

        self.subentry_handler: SubEntryHandler = None
        self.config_model = StateModel()
        if dashboard is None:
            self._experiment_manager_local = ExperimentManager()
        else:
            self._experiment_manager_local = dashboard.experiment_manager

        super().__init__(dashboard=dashboard, tree=StateParameterTree())

        self.history_file_path: str = HISTORY_FILE_PATH


    @property
    def experiment_manager(self) -> ExperimentManager:
        return self._experiment_manager_local

    def show(self):
        """ Open the StateManager User Interface

        If the Dashboard is not None and has a current experiment set, the state experiment name
        entry will be set as readonly and the settings are taken from the modules
        """
        if self.dashboard is not None:
            settings = SettingsManager().create_settings_all(
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

    def save_entries(self, entry_path: Path = None):
        self.config_model.save(entry_path)

    @staticmethod
    def format_subentries(entries: list[StateSubEntry]):
        return [(f'{entry.entry_type.capitalize()} for '
                 f'{entry.module_name} - '
                 f'{entry.setting.parameter.title()} '
                 f'{entry.setting.value()}') for entry in entries]

    def _execute_entry(self, entry_path: Path = None, **kwargs) -> bool:
        """Applies the entry from the given file in the manager.

        Parameters:
        -----------
        file : Path
            The path to the state file to be applied.
        """
        if entry_path is None:
            entry_path = self.entry_filepath
        config_subentries = state_subentries_from_path(entry_path)

        if self.experiment_manager.applied_entry_name != self.experiment_filename:
            logger.warning(f'The current state is referring to the experiment: {self.experiment_filename} '
                           f'while the current applied experiment is: {self.experiment_manager.applied_entry_name}')
            return False

        if len(config_subentries) > 0:
            self.show_subentries(config_subentries, f'Loading State: {self.entry}')

        for ind, entry in enumerate(config_subentries):
            subentry_handler = handler_factory.get_subentry_handler(entry.entry_type)(
                self.config_model, self.settings, self.actuators, self.detectors)
            try:
                subentry_handler.execute_subentry(entry, dashboard=self.dashboard)
                self.subentries_model.set_status(ind, True)
                QtWidgets.QApplication.processEvents()
                QtCore.QThread.msleep(0)
            except SubEntryError as e:
                logger.exception(str(e))
                self.subentries_model.set_status(ind, False)

        self.close_subentries_display(1000)

        self.save_new_history_entry()

        return True

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

    def add_subentry(self, special_entry_name: str):
        self.subentry_handler = handler_factory.get_subentry_handler(special_entry_name)(
            self.config_model, self.settings, self.actuators, self.detectors, self.extensions)
        self.subentry_handler.show_dialog()

    def setup_docks_and_widgets(self):
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(False)
        self.tree.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragOnly)
        self.tree.doubleClicked.connect(self.add_setting)

        self.table_out = StateTableView(True)
        self.table_out.horizontalHeader().ResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table_out.horizontalHeader().setStretchLastSection(True)
        self.table_out.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        #self.table_out.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.table_out.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragDrop)
        self.table_out.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)


        self.table_out.setModel(self.config_model)
        self.table_out.add_data_signal[str].connect(self.add_subentry)
        self.table_out.remove_row_signal[int].connect(self.config_model.remove_data)
        self.table_out.load_data_signal.connect(self.config_model.load)
        self.table_out.save_data_signal.connect(self.config_model.save)
        self.delegate = ParameterDelegate()
        self.table_out.setItemDelegate(self.delegate)

        vlayout = QtWidgets.QVBoxLayout()
        hwidget = QtWidgets.QWidget()
        hlayout = QtWidgets.QHBoxLayout()
        hwidget.setLayout(hlayout)
        self.vlayout_right = QtWidgets.QVBoxLayout()
        valyout_left = QtWidgets.QVBoxLayout()

        self.widget_buttons = QtWidgets.QWidget()
        self.widget_buttons.setLayout(QtWidgets.QVBoxLayout())
        self.widget_buttons.layout().addStretch()

        self.widget_buttons.layout().addStretch()

        vlayout.addWidget(hwidget)
        hlayout.addLayout(valyout_left)
        hlayout.addWidget(self.widget_buttons)
        hlayout.addLayout(self.vlayout_right)

        valyout_left.addWidget(self.settings_tree)
        self.vlayout_right.addWidget(self.table_out)

        self.main_widget.setLayout(vlayout)

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        move_toolbar = self.add_toolbar('move', 'Move')
        move_toolbar.setOrientation(QtCore.Qt.Orientation.Vertical)
        self.widget_buttons.layout().insertWidget(1, move_toolbar)

        self.add_toolbar('actions', 'Actions', parent=self.mainwindow)
        self.vlayout_right.insertWidget(0, self.toolbar)

    def setup_actions(self):
        self.add_action('show_all_settings', 'Show All Settings', 'EditFind',
                        checkable=True,
                        tip='If Checked: display all settings (in green, settings that can be configured)'
                            ' otherwise only configurables ones',
                        toolbar='actions')

        self.create_dashboard_toolbar(add_dashboard=__name__ == '__main__',
                                      add_experiment=True, add_state=False, add_break=False)
        self.experiment_manager.enable_actions(True)

        self.add_action(EntryActions.ADD, 'Add', 'arrow_circle_right', toolbar='move',
                        tip='Add the current Parameter item', icon_color=self.get_theme().green,
                        )
        self.add_action(EntryActions.REMOVE, 'Remove', 'arrow_circle_left', toolbar='move',
                        tip='Delete the current Configuration item ("Del")',
                        icon_color=self.get_theme().red,
                        shortcut=Qt.Key.Key_Delete)
        self.add_action(EntryActions.UP, 'Move Up', 'arrow_circle_up', toolbar='move',
                        tip='Move UP the current Configuration item ("Ctrl+Up")',
                        icon_color=self.get_theme().blue,
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Up))
        self.add_action(EntryActions.DOWN, 'Move Down', 'arrow_circle_down', toolbar='move',
                        icon_color=self.get_theme().orange,
                        tip='Move Down the current Configuration item ("Ctrl+Down")',
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Down))
        self.toolbar.addSeparator()

    def connect_things(self):
        self.connect_action(EntryActions.ADD, self.add_setting)
        self.connect_action(EntryActions.REMOVE, self.remove_setting)
        self.connect_action(EntryActions.UP, self.move_up_setting)
        self.connect_action(EntryActions.DOWN, self.move_down_setting)

        self.connect_action('show_all_settings', self.display_settings)

        if self.dashboard is None:
            self.experiment_manager.enable_actions(True)
            self.experiment_manager.get_action(ManagerActions.EXECUTE).setVisible(False)

        else:
            self.experiment_manager.get_action(ManagerActions.LIST_EXTERNAL).widget.setEnabled(False)
            self.experiment_manager.applied_entry.connect(self.set_experiment_filename)  #action slot from experiment menu need this to update the list onf state entries

        self.experiment_manager.entries_sync.value_changed.connect(lambda value: self.set_experiment_filename(value['current']))
    def _update_entry(self, entry: Path):
        self.config_model.load(self.entry_filepath)

    def update_settings(self, settings: Union[Parameter, Path, str] = None):
        if settings is None:
            settings = self._get_settings_from_file()
            if settings == '':
                return
        if isinstance(settings, str):
            self._experiment_manager_local.entry = settings
            experiment_settings: Parameter = self._experiment_manager_local.settings
            settings = SettingsManager().create_settings_all(
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

    def set_readonly_setting(self, param: Parameter = None):
        """ Set all settings as readonly but configure the VALID_FOR_CONFIGURATION option:

        if initially readonly: VALID_FOR_CONFIGURATION is set to its value (if existing otherwise True if not specified)
        else: VALID_FOR_CONFIGURATION is set to False

        See Also
        --------
        pymodaq_gui.parameter.ioxml.VALID_FOR_CONFIGURATION
        pymodaq.control_modules.move_utility_classes.params
        pymodaq.control_modules.viewer_utility_classes.params

        """


        if not param.readonly():
            param.setOpts(**{'readonly': True,
                             VALID_FOR_CONFIGURATION: param.opts.get(VALID_FOR_CONFIGURATION, True)})
        else:
            if not param.opts.get(VALID_FOR_CONFIGURATION, False):
                param.setOpts(**{VALID_FOR_CONFIGURATION: False})

        for child in param.children():
            self.set_readonly_setting(child)

    def display_settings(self, display_all: bool = True, param: Parameter = None):
        if param is None:
            param = self.settings

        if display_all:
            param.setOpts(visible=True)
            if param.opts[VALID_FOR_CONFIGURATION]:
                brush = QtGui.QBrush(QtCore.Qt.GlobalColor.green)
                for item in param.items:
                    for ind_col in range(item.columnCount()):
                        item.setForeground(ind_col, brush)
        else:
            param.setOpts(visible=param.opts[VALID_FOR_CONFIGURATION])
            if param.opts[VALID_FOR_CONFIGURATION]:
                brush = QtGui.QBrush(QtCore.Qt.GlobalColor.white)
                for item in param.items:
                    for ind_col in range(item.columnCount()):
                        item.setForeground(ind_col, brush)

        for child in param.children():
            self.display_settings(display_all, child)

    def set_drag_mode_recursive(self, param: Parameter, movable=True, drop_enabled=True):
        if param.opts.get(VALID_FOR_CONFIGURATION, True):
            param.setOpts(movable=movable, dropEnabled=drop_enabled)
        for child in param.children():
            self.set_drag_mode_recursive(child, movable, drop_enabled)

    def add_setting(self):
        if self.tree.currentItem() is not None:
            current_setting = self.tree.currentItem().param
            try:
                module, module_type = get_module_from_param(ParameterWithPath(current_setting))
            except KeyError:
                module = ModuleType.NONE.value
                module_type = ModuleType.NONE
            entry = StateSubEntry(SubEntryHandlerTypes.SETTINGS, module,
                                  module_type, ParameterWithPath(current_setting))
            entries = self.config_model.split_entry(entry)
            for entry in entries:
                self.config_model.add_data(self.config_model.rowCount(), entry)

    def do_things_for_new_creation(self):
        self.table_out.setCurrentIndex(self.table_out.model().index(0, 0))
        self.table_out.clear()

    def remove_setting(self):
        index_0 = self.table_out.selectedIndexes()[0]
        indexes = list(set([index.row() for index in self.table_out.selectedIndexes()]))
        indexes.sort()
        for index in indexes[::-1]:  #start with the highest row
            if index != -1:
                self.config_model.remove_data(index)
        self.table_out.setCurrentIndex(index_0)

    def move_up_setting(self):
        indexes = list(set([index.row() for index in self.table_out.selectedIndexes()]))
        indexes.sort()
        if indexes[0] == 0:
            return
        else:
            for index in indexes:  #start with the lowest row
                if index != -1:  # means no selected row
                    self.config_model.moveRow(QModelIndex(), index,
                                              QModelIndex(), index-1)

    def move_down_setting(self):
        indexes = list(set([index.row() for index in self.table_out.selectedIndexes()]))
        indexes.sort()
        if indexes[-1] + 1 == self.config_model.rowCount():
            return
        else:
            for index in indexes[::-1]:  #start with the highest row
                if index != -1:  # means no selected row
                    self.config_model.moveRow(QModelIndex(), index,
                                              QModelIndex(), index+2)

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

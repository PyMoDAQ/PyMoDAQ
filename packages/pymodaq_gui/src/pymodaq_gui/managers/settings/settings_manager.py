
from typing import Union, TYPE_CHECKING
from pathlib import Path
import sys

import toml
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt
from qtpy.QtGui import QKeySequence
from qtpy.QtCore import QModelIndex

from pymodaq_gui.utils.widgets.widget_with_label_title import WidgetWithLabelTitle
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import GlobalConfig as Config, get_set_local_dir, get_set_config_dir

from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq_gui.parameter.utils import ParameterWithPath

from pymodaq_gui.parameter.ioxml import VALID_FOR_CONFIGURATION

from pymodaq_gui.managers.settings.subentries import (
    SubEntryHandlerFactory, SubEntryHandler, SubEntryError, SubEntryHandlerTypes, SubEntry)
from pymodaq_gui.managers.settings.utils import (
    SettingsManagerParameterTree, SettingsManagerModel, SettingsManagerTableView,
    settings_manager_subentries_from_path, ParameterDelegate,
    EntryActions, ModuleType)


from pymodaq_gui.managers.manager_base import ManagerBase, ManagerActions


if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard


logger = set_logger(get_module_name(__file__))
handler_factory = SubEntryHandlerFactory()

config = Config()


def get_set_settings_path(subfolder: str = '', user=False):
    """ creates and return the config folder path for this manager files
    """
    if subfolder != '':
        target_path = get_set_config_dir('settings', user=user).joinpath(subfolder)
    else:
        target_path = get_set_config_dir('settings', user=user)
    target_path.mkdir(parents=True, exist_ok=True)
    return target_path


class SettingsManager(ManagerBase):
    """
    Main class managing settings values to be restored.

    Could be extended with special subentries dealing with other features, see StateManager

    """

    entry_type = 'settings'
    entry_extension ='.settings'
    icon_name = 'settings'

    def __init__(self,
                 dashboard: 'DashBoard' = None,
                 subentry_type: type[SubEntry]=None,
                 handler_id='settings'):

        self.subentry_handler: SubEntryHandler = None
        if subentry_type is None:
            subentry_type = SubEntry
        self.config_model = SettingsManagerModel(save_path=self.get_entry_folder())

        super().__init__(dashboard=dashboard,
                         tree=SettingsManagerParameterTree(
                             manager=self,
                             subentry_type=subentry_type,
                             handler_id=handler_id))

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        """Get the folder path where the managed entries are stored."""
        return get_set_settings_path()

    def save_entries(self, entry_path: Path = None):
        self.config_model.save(entry_path)

    @staticmethod
    def format_subentries(entries: list[SubEntry]):
        return [(f'{entry.entry_type.capitalize()} for '
                 f'{entry.module_name} - '
                 f'{entry.setting.parameter.title()} '
                 f'{entry.setting.value()}') for entry in entries]

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
                self.config_model, self.settings)
            try:
                subentry_handler.execute_subentry(entry)
                self.subentries_model.set_status(ind, True)
                QtWidgets.QApplication.processEvents()
                QtCore.QThread.msleep(0)
            except (SubEntryError, NotImplementedError) as e:
                logger.exception(str(e))
                self.subentries_model.set_status(ind, False)

        self.close_subentries_display(1000)

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

    def populate_from_file(self, file_path: Path):
        """ for quick testing purpose, not meant to be used at the end"""
        children = ioxml.XML_file_to_parameter(file_path)
        settings = Parameter.create(
            title="Control Modules:", name="control_modules", type="group", children=children,
        )
        self.populate_from_settings(settings)

    def add_subentry(self, special_entry_name: str):
        """ Create an entry in the table from one of the special SubEntryHandlers"""
        self.subentry_handler = handler_factory.get_subentry_handler(special_entry_name)(
            self.config_model, self.settings, self)
        self.subentry_handler.show_dialog()

    def setup_docks_and_widgets(self):
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(False)
        self.tree.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragOnly)
        self.tree.doubleClicked.connect(self.add_setting)

        self.table_out = SettingsManagerTableView(True)
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

        layout = QtWidgets.QHBoxLayout()
        hwidget = QtWidgets.QWidget()
        hlayout = QtWidgets.QHBoxLayout()
        hwidget.setLayout(hlayout)
        self.vlayout_right = QtWidgets.QVBoxLayout()
        valyout_left = QtWidgets.QVBoxLayout()

        self.widget_buttons = QtWidgets.QWidget()
        self.widget_buttons.setLayout(QtWidgets.QVBoxLayout())
        self.widget_buttons.layout().addStretch()

        self.widget_buttons.layout().addStretch()

        layout.addWidget(hwidget)
        hlayout.addLayout(valyout_left)
        hlayout.addWidget(self.widget_buttons)
        hlayout.addLayout(self.vlayout_right)

        valyout_left.addWidget(WidgetWithLabelTitle('Select Settings:',
                                                    self.settings_tree))
        self.vlayout_right.addWidget(WidgetWithLabelTitle('Entries to apply:',
                                                          self.table_out))

        self.main_widget.setLayout(layout)

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

    def _update_entry(self, entry: Path):
        self.config_model.load(self.entry_filepath)

    def update_settings(self, settings: Union[Parameter, Path, str] = None):
        if settings is None:
            settings = self._get_settings_from_file()
            if settings == '':
                return

        if isinstance(settings, Parameter):
            self.populate_from_settings(settings)
        elif isinstance(settings, Path):
            self.populate_from_file(settings)
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

    @staticmethod
    def get_module_from_param(param: ParameterWithPath) -> Union[str]:
        """ should return the module name from data bundled in the ParameterWithPath

        To be reimplemented

        Parameters
        ----------
        param: ParameterWithPath

        """
        return ''

    def add_setting(self):
        if self.tree.currentItem() is not None:
            current_setting = self.tree.currentItem().param
            try:
                module = self.get_module_from_param(ParameterWithPath(current_setting))
            except KeyError:
                module = ModuleType.NONE.value
            entry = SubEntry(SubEntryHandlerTypes.SETTINGS, module,
                             ParameterWithPath(current_setting))
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



if __name__ == "__main__":
    from pymodaq_gui.qt_utils import mkQApp

    app = mkQApp('SettingsManager')

    prog = SettingsManager(dashboard=None)
    prog.update_settings(Path('../../resources/scan_settings.xml'))
    prog.mainwindow.show()
    prog.enable_actions(True)

    sys.exit(app.exec())

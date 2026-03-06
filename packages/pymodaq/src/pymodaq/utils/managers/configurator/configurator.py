
from typing import Union, TYPE_CHECKING
from pathlib import Path
import sys

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt
from qtpy.QtGui import QKeySequence
from qtpy.QtCore import QModelIndex

from pymodaq.utils.managers.modules.module_settings_manager import SettingsManager
from pymodaq.utils.managers.preset.preset_manager import PresetManager
from pymodaq_utils.logger import set_logger, get_module_name


from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq_gui.parameter.utils import ParameterWithPath

from pymodaq_gui.parameter.ioxml import VALID_FOR_CONFIGURATION

from pymodaq.utils.managers.configurator.subentries import (
    SubEntryHandlerFactory, SubEntryHandler, SubEntryError, SubEntryHandlerTypes, ConfiguratorSubEntry)
from pymodaq.utils.managers.configurator.utils import (
    ConfiguratorParameterTree, ConfiguratorModel, ConfiguratorTableView,
    get_module_from_param, config_subentries_from_path, ParameterDelegate,
    EntryActions, ModuleType)



from pymodaq.utils.config import get_set_configurator_path
from pymodaq_gui.managers.manager_base import ManagerBase, ManagerActions

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard


logger = set_logger(get_module_name(__file__))
handler_factory = SubEntryHandlerFactory()


class Configurator(ManagerBase):
    """
    Main class managing the configuration of control modules from a Dashboard in terms
    of their settings and actuator's value.

    This class provides a GUI to create, modify and save configurations for different presets (DashBoard state)
    controlling various modules (actuators, detectors...).

    Parameters
    ----------
    preset_filename : str, optional
        Name of the preset file to load at startup
    """

    entry_type = 'configurator'
    entry_extension ='.config'

    def __init__(self,
                 dashboard: 'DashBoard' = None,
                 preset_filename: str = 'default'):

        self.subentry_handler: SubEntryHandler = None
        self.config_model = ConfiguratorModel()
        if dashboard is None:
            self._preset_manager_local = PresetManager()
        else:
            self._preset_manager_local = dashboard.preset_manager

        super().__init__(dashboard=dashboard, tree=ConfiguratorParameterTree())

        self.preset_filename = preset_filename


    @property
    def preset_manager(self) -> 'PresetManager':
        return self._preset_manager_local

    def show(self):
        """ Open the Configurator User Interface

        If the Dashboard is not None and has a current preset set, the configurator preset name
        entry will be set as readonly and the settings are taken from the modules
        """
        if self.dashboard is not None:
            settings = SettingsManager().create_settings_all(
                self.dashboard.modules_manager.actuators_all,
                self.dashboard.modules_manager.detectors_all,
            )
            self.update_settings(settings)
        else:
            self.update_settings(self._preset_manager_local.entry)

        super().show()

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        """Get the folder path where the managed entries are stored."""
        return get_set_configurator_path(self.preset_filename)

    def set_preset_filename(self, name: str):
        """ convenience method to be used as slot in Qt connection"""
        self.preset_filename = name

    @property
    def preset_filename(self) -> str:
        try:
            return self.preset_manager.get_action(ManagerActions.LIST_EXTERNAL).widget.currentText()
        except KeyError:  # not yet instantiated but need to be there
            return 'default'

    @preset_filename.setter
    def preset_filename(self, preset_filename: str):
        if preset_filename in self.preset_manager.entries:
            self.preset_manager.get_action(ManagerActions.LIST_EXTERNAL).setCurrentText(preset_filename)
            self.entries_sync.update_key('items', self.entries)
            self.update_entry()

    def save_entries(self, entry_path: Path = None):
        self.config_model.save(entry_path)

    @staticmethod
    def format_subentries(entries: list[ConfiguratorSubEntry]):
        return [(f'{entry.entry_type.capitalize()} for '
                 f'{entry.module_name} - '
                 f'{entry.setting.parameter.title()} '
                 f'{entry.setting.value()}') for entry in entries]

    def execute_entry(self, entry_path: Path = None, **kwargs) -> bool:
        """Applies the entry from the given file in the manager.

        Parameters:
        -----------
        file : Path
            The path to the configuration file to be applied.
        """
        config_subentries = config_subentries_from_path(entry_path)

        if len(config_subentries) > 0:
            self.show_subentries(config_subentries, f'Loading Configuration: {self.entry}')

        for ind, entry in enumerate(config_subentries):
            subentry_handler = handler_factory.get_subentry_handler(entry.entry_type)(
                self.config_model, self.settings, self.actuators, self.detectors)
            try:
                if entry.module_name == ModuleType.NONE:
                    mod = None
                else:
                    mod = self.dashboard.modules_manager.get_mod_from_name(
                        entry.module_name, entry.module_type)
                subentry_handler.execute_subentry(entry, module=mod, dashboard=self.dashboard)
                self.subentries_model.set_status(ind, True)
                QtWidgets.QApplication.processEvents()
                QtCore.QThread.msleep(200)
            except SubEntryError as e:
                logger.exception(str(e))
                self.subentries_model.set_status(ind, False)

        self.close_subentries_display(1000)
        return True

    def populate_from_settings(self, settings: Parameter):
        """
        Initialize the configurator from a Parameter settings.

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
    def actuators(self):
        if self.dashboard is not None:
            return self.dashboard.modules_manager.actuators_name
        else:
            return [param.opts['title'] for param in self.settings.child(ModuleType.Actuator).children()]

    @property
    def detectors(self):
        if self.dashboard is not None:
            return self.dashboard.modules_manager.detectors_name
        else:
            return [param.opts['title'] for param in self.settings.child(ModuleType.Detector).children()]


    def populate_from_file(self, file_path: Path):
        """ for quick testing purpose, not meant to be used at the end"""
        children = ioxml.XML_file_to_parameter(file_path)
        settings = Parameter.create(
            title="Control Modules:", name="control_modules", type="group", children=children
        )
        self.populate_from_settings(settings)

    def add_subentry(self, special_entry_name: str):
        self.subentry_handler = handler_factory.get_subentry_handler(special_entry_name)(
            self.config_model, self.settings, self.actuators, self.detectors)
        self.subentry_handler.show_dialog()

    def setup_docks(self):
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(False)
        self.tree.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragOnly)
        self.tree.doubleClicked.connect(self.add_setting)

        self.table_out = ConfiguratorTableView(True)
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

        self.set_toolbar(self.add_toolbar('configurations'))

        vlayout = QtWidgets.QVBoxLayout()
        hwidget = QtWidgets.QWidget()
        hlayout = QtWidgets.QHBoxLayout()
        hwidget.setLayout(hlayout)
        vlayout_right = QtWidgets.QVBoxLayout()
        valyout_left = QtWidgets.QVBoxLayout()

        widget_buttons = QtWidgets.QWidget()
        widget_buttons.setLayout(QtWidgets.QVBoxLayout())
        widget_buttons.layout().addStretch()
        move_toolbar = self.add_toolbar('move')
        move_toolbar.setOrientation(QtCore.Qt.Orientation.Vertical)
        widget_buttons.layout().addWidget(move_toolbar)
        widget_buttons.layout().addStretch()

        vlayout.addWidget(hwidget)
        hlayout.addLayout(valyout_left)
        hlayout.addWidget(widget_buttons)
        hlayout.addLayout(vlayout_right)

        valyout_left.addWidget(self.settings_tree)
        vlayout_right.addWidget(self.get_toolbar('configurations'))
        vlayout_right.addWidget(self.table_out)

        self.main_widget.setLayout(vlayout)

    def setup_actions(self):
        self.add_action('show_all_settings', 'Show All Settings', 'EditFind',
                        checkable=True, toolbar=self.get_toolbar('main'),
                        tip='If Checked: display all settings (in green, settings that can be configured)'
                            ' otherwise only configurables ones')

        self.add_toolbar('preset', 'Preset Toolbar', parent=self.mainwindow, add_break=False)
        self.preset_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('preset'),)


        self.add_action(EntryActions.ADD, 'Add', 'SP_ArrowRight', toolbar='move',
                        tip='Add the current Parameter item',
                        )
        self.add_action(EntryActions.REMOVE, 'Remove', 'SP_ArrowLeft', toolbar='move',
                        tip='Delete the current Configuration item ("Del")',
                        shortcut=Qt.Key.Key_Delete)
        self.add_action(EntryActions.UP, 'Move Up', 'SP_ArrowUp', toolbar='move',
                        tip='Move UP the current Configuration item ("Ctrl+Up")',
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Up))
        self.add_action(EntryActions.DOWN, 'Move Down', 'SP_ArrowDown', toolbar='move',
                        tip='Move Down the current Configuration item ("Ctrl+Down")',
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Down))


    def connect_things(self):
        self.connect_action(EntryActions.ADD, self.add_setting)
        self.connect_action(EntryActions.REMOVE, self.remove_setting)
        self.connect_action(EntryActions.UP, self.move_up_setting)
        self.connect_action(EntryActions.DOWN, self.move_down_setting)

        self.connect_action('show_all_settings', self.display_settings)

        if self.dashboard is None:
            self.preset_manager.enable_actions(True)
            self.preset_manager.get_action(ManagerActions.EXECUTE).setVisible(False)
            self.preset_manager.get_action(ManagerActions.LIST_EXTERNAL
                                           ).widget.currentTextChanged.connect(self.set_preset_filename)
        else:
            self.preset_manager.get_action(ManagerActions.LIST_EXTERNAL).widget.setEnabled(False)

    def update_entry(self, entry: Union[str, Path] = None, **kwargs):
        self.config_model.load(self.entry_filename)

    def update_settings(self, settings: Union[Parameter, Path, str] = None):
        if settings is None:
            settings = self._get_settings_from_file()
            if settings == '':
                return
        if isinstance(settings, str):
            self._preset_manager_local.entry = settings
            preset_settings: Parameter = self._preset_manager_local.settings
            settings = SettingsManager().create_settings_all(
                preset_settings.child(ModuleType.Actuator.value).children(),
                preset_settings.child(ModuleType.Detector.value).children(),
            )

        if isinstance(settings, Parameter):
            self.populate_from_settings(settings)
        elif isinstance(settings, Path):
            self.populate_from_file(settings)
            self.preset_filename = settings.stem
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
            entry = ConfiguratorSubEntry(SubEntryHandlerTypes.SETTINGS, module,
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


if __name__ == "__main__":
    from pymodaq_gui.qt_utils import mkQApp

    app = mkQApp('PresetManager')
    external_ui = QtWidgets.QMainWindow()

    prog = Configurator()
    prog.update_settings('default')
    prog.mainwindow.show()

    toolbar, menu = prog.get_external_toolbar_menu()
    external_ui.addToolBar(toolbar)
    external_ui.menuBar().addMenu(menu)

    prog.enable_actions(True)

    external_ui.show()
    sys.exit(app.exec())

from typing import Union, TYPE_CHECKING
from pathlib import Path
import sys

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import QModelIndex


from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq.utils.config import get_set_preset_path

from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq_gui.parameter.utils import ParameterWithPath

from pymodaq_gui.parameter.ioxml import VALID_FOR_CONFIGURATION


from pymodaq.utils.managers.configurator.entries import ConfiguratorEntry
from pymodaq.utils.managers.configurator.special_entries import SpecialEntryFactory, SpecialEntry
from pymodaq.utils.managers.configurator.utils import (ConfiguratorParameterTree, ConfiguratorModel,
                                                       ConfiguratorTableView, get_module_from_param, config_entries_from_path,
                                                       ParameterDelegate, EntryActions,
                                                       ModuleType)



from pymodaq.utils.config import get_set_configurator_path
from pymodaq.utils.managers.utils import ManagerBase

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard


logger = set_logger(get_module_name(__file__))

special_entry_factory = SpecialEntryFactory()


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
                 menu: QtWidgets.QMenu = None,
                 toolbar: QtWidgets.QToolBar = None,
                 preset_filename: str = 'default'):

        self._preset_ini = preset_filename
        self.special_entry: SpecialEntry = None

        super().__init__(dashboard=dashboard, menu=menu, toolbar=toolbar,
                         tree=ConfiguratorParameterTree())

        self.preset_filename = preset_filename


    def show(self):
        self.update_settings(self.dashboard.modules_manager.get_settings_all())
        super().show()

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        """Get the folder path where the managed entries are stored."""
        try:
            return get_set_configurator_path(self.preset_filename)
        except KeyError as e: #fallback to preset ini
            return get_set_configurator_path(self._preset_ini)

    @property
    def preset_filename(self) -> str:
        if 'preset_filename' not in self.actions_names:
            return self._preset_ini  # fallback at startup
        else:
            return self.get_action('preset_filename').text()

    @preset_filename.setter
    def preset_filename(self, preset_filename: str):
        if preset_filename in [path.stem for path in get_set_preset_path().iterdir()]:
            self._preset_ini = preset_filename
            try:
                self.get_action('preset_filename').setText(preset_filename)
                self.get_action('entries').clear()
                self.get_action('entries').addItems(self.entries)
            except KeyError as e:
                pass

    def save_entries(self, entry_path: Path = None):
        self.config_model.save(entry_path)

    @staticmethod
    def format_entry_sublist(entries: list[ConfiguratorEntry]):
        return [(f'{entry.entry_type.capitalize()} for'
                 f'{entry.module_name} - '
                 f'{entry.setting.parameter.title()} '
                 f'{entry.setting.value()}') for entry in entries]

    def apply_entry(self, entry_path: Path = None, **kwargs):
        """Applies the entry from the given file in the manager.

        Parameters:
        -----------
        file : Path
            The path to the configuration file to be applied.
        """
        config_entries = config_entries_from_path(entry_path)

        if len(config_entries) > 0:
            self.show_entry_sublist(config_entries)

        for ind, entry in enumerate(config_entries):
            special_entry = special_entry_factory.get_entry(entry.entry_type)(
                self.config_model, self.settings, self.actuators, self.detectors)
            try:
                mod = self.dashboard.modules_manager.get_mod_from_name(entry.module_name,
                                                                       entry.module_type)
                special_entry.apply_entry(entry, module=mod, dashboard=self.dashboard)
                self.entry_sublist_model.set_status(ind, True)
                QtWidgets.QApplication.processEvents()
                QtCore.QThread.msleep(200)
            except Exception as e:
                logger.exception(str(e))
                self.entry_sublist_model.set_status(ind, False)

        self.close_entry_sublist(1000)

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

    def add_special_entry(self, special_entry_name: str):
        self.special_entry = special_entry_factory.get_entry(special_entry_name)(
            self.config_model, self.settings, self.actuators, self.detectors)
        self.special_entry.show_dialog()

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

        self.config_model = ConfiguratorModel()
        self.table_out.setModel(self.config_model)
        self.table_out.add_data_signal[str].connect(self.add_special_entry)
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
        self.add_widget('preset_label', QtWidgets.QLabel('Configuration from Preset: '),
                        toolbar=self.get_toolbar('main'))
        self.add_widget('preset_filename', QtWidgets.QLabel(''), tip='Name of the current preset',
                        toolbar=self.get_toolbar('main'))

        self.add_action(EntryActions.ADD, 'Add', 'SP_ArrowRight', toolbar='move')
        self.add_action(EntryActions.REMOVE, 'Remove', 'SP_ArrowLeft', toolbar='move',
                        shortcut=QtCore.Qt.Key.Key_Delete)
        self.add_action(EntryActions.UP, 'Move Up', 'SP_ArrowUp', toolbar='move')
        self.add_action(EntryActions.DOWN, 'Move Down', 'SP_ArrowDown', toolbar='move')
        self.add_action('show_all_settings', 'Show All Settings', 'FormatJustifyLeft',
                        checkable=True, toolbar=self.get_toolbar('main'),
                        tip='If Checked: display all settings (in green, settings that can be configured)'
                            ' otherwise only configurables ones')

    def connect_things(self):
        self.connect_action(EntryActions.ADD, self.add_setting)
        self.connect_action(EntryActions.REMOVE, self.remove_setting)
        self.connect_action(EntryActions.UP, self.move_up_setting)
        self.connect_action(EntryActions.DOWN, self.move_down_setting)

        self.connect_action('show_all_settings', self.display_settings)


    def update_entry(self, entry: Union[str, Path] = None, **kwargs):
        self.config_model.load(self.entry_filename)

    def update_settings(self, settings: Union[Parameter, Path, str] = None):
        if settings is None:
            settings = self._get_settings_from_file()
            if settings == '':
                return
        if isinstance(settings, str):
            settings = get_set_preset_path().joinpath(f'{settings}.xml')
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
            module, module_type = get_module_from_param(ParameterWithPath(current_setting))
            entry = ConfiguratorEntry(module, module_type, ParameterWithPath(current_setting))
            entries = self.config_model.split_entry(entry)
            for entry in entries:
                self.config_model.add_data(self.config_model.rowCount(), entry)

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
    from pymodaq_gui.utils.utils import mkQApp
    app = mkQApp('PresetManager')
    settings_path = Path(__file__).parent.parent.parent.parent.parent.parent.joinpath('tests/utils/managers/settings.xml')
    external_ui = QtWidgets.QMainWindow()
    toolbar = QtWidgets.QToolBar()
    menu = QtWidgets.QMenu('Configurator')
    external_ui.addToolBar(toolbar)
    external_ui.menuBar().addMenu(menu)

    prog = Configurator(menu=menu, toolbar=toolbar)
    prog.update_settings(settings_path)
    prog.mainwindow.show()

    external_ui.show()
    sys.exit(app.exec_())

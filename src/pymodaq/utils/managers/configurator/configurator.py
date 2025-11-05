from typing import Union, Optional
from pathlib import Path
import sys

from qtpy import QtWidgets, QtCore
from qtpy.QtWidgets import QDialogButtonBox, QDialog

from pymodaq.utils.data import DataActuator
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq.utils.config import get_set_preset_path

from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq_gui.parameter.utils import ParameterWithPath
from pymodaq_gui.messenger import dialog, messagebox

from pymodaq_gui.utils.widgets.spinbox import SpinBox
from pymodaq.utils.managers.configurator.utils import (ConfiguratorParameterTree, ConfiguratorModel,
                                                       ConfiguratorEntry, ConfiguratorTableView,
                                                       get_module_from_param, config_entries_from_path,
                                                       ParameterDelegate, EntryActions,
                                                       SpecialConfiguratorEntry, ModuleType)
from pymodaq_gui.parameter.utils import compareParameters

from pymodaq.utils.config import get_set_configurator_path


from pymodaq.utils.managers.utils import ManagerBase

logger = set_logger(get_module_name(__file__))


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

        super().__init__(dashboard=dashboard, menu=menu, toolbar=toolbar,
                         tree=ConfiguratorParameterTree())

        self.preset_filename = preset_filename

    def show(self):
        self.update_settings(self.dashboard.modules_manager.get_settings_all())
        self.mainwindow.show()

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
                self.get_action('entries').addItems(self.entries + ['...'])
            except KeyError as e:
                pass

    def save_entries(self, entry_path: Path = None):
        self.config_model.save(entry_path)

    def apply_entry(self, entry_path: Path = None, **kwargs):
        """Applies the entry from the given file in the manager.

        Parameters:
        -----------
        file : Path
            The path to the configuration file to be applied.
        """
        pwp_list = config_entries_from_path(entry_path)
        incompatible_index = self.check_parameters(pwp_list, self.dashboard.modules_manager.get_settings_all())
        for index, entry in enumerate(pwp_list):
            if index not in incompatible_index:
                mod = self.dashboard.modules_manager.get_mod_from_name(entry.module_name, entry.module_type)
                if SpecialConfiguratorEntry.ACTUATOR_VALUE in entry.setting.path:
                    mod.move_abs(DataActuator(entry.module_name, data=entry.setting.parameter.value(),
                                              units=entry.setting.parameter.opts.get('suffix', mod.units)))
                elif SpecialConfiguratorEntry.MODULE_INIT in entry.setting.path:
                    if entry.setting.parameter.value():
                        mod.init_hardware_ui(True)
                        self.dashboard.poll_init(mod)
                else:
                    mod.settings.child(*entry.setting.path[3:]).setValue(entry.setting.parameter.value())

    @staticmethod
    def check_parameters(entries: list[ConfiguratorEntry], settings: Parameter):
        """
        Check compatibility between configuration entries and current settings.

        Parameters
        ----------
        entries : list[ConfiguratorEntry]
            List of configuration entries to check
        settings : Parameter
            Current settings to compare against

        Returns
        -------
        list
            Indices of incompatible entries
        """
        incompatible_index = []
        for index, entry in enumerate(entries):
            if SpecialConfiguratorEntry.ACTUATOR_VALUE in entry.setting.path:
                if entry.module_name not in [group.child('name').value() for
                                             group in settings.child(ModuleType.Actuator).children()]:
                    incompatible_index.append(index)
            elif SpecialConfiguratorEntry.MODULE_INIT in entry.setting.path:
                if entry.module_name not in [group.child('name').value() for
                                             group in settings.child(entry.module_type).children()]:
                    incompatible_index.append(index)
            else:
                if not compareParameters(settings.child(*entry.setting.path[1:]), entry.setting.parameter):
                    incompatible_index.append(index)
        if len(incompatible_index) > 0:
            messagebox('Warning', f'The configuration entries with index: {incompatible_index} are no more compatible'
                                  f'with the current state of your Dashboard, Ignoring them in the applied '
                                  f'configuration')
        return incompatible_index

    def populate_from_settings(self, settings: Parameter):
        """
        Initialize the configurator from a Parameter settings.

        Parameters
        ----------
        settings : Parameter
            Settings containing all modules configuration
        """
        self.settings = settings
        self.set_drag_mode_recursive(self.settings, movable=True, drop_enabled=True)
        self._actuators = [
            param.opts['title'] for param in self.settings.child(ModuleType.Actuator).children()]
        self._detectors = [
            param.opts['title'] for param in self.settings.child(ModuleType.Detector).children()]

    def populate_from_file(self, file_path: Path):
        """ for quick testing purpose, not meant to be used at the end"""
        children = ioxml.XML_file_to_parameter(file_path)
        settings = Parameter.create(
            title="Control Modules:", name="control_modules", type="group", children=children
        )
        self.populate_from_settings(settings)

    def get_units_from_module_name(self, actuator_name: str):
        mods_settings = [group.child('name').value() for
                        group in self.settings.child(ModuleType.Actuator).children()]
        actuator_settings = self.settings.child(ModuleType.Actuator).children()[
            mods_settings.index(actuator_name)]

        return actuator_settings.child('move_settings', 'units').value()

    def update_suffix_in_dialog(self, actuator_name: str):
        self.value_sb.setOpts(suffix=self.get_units_from_module_name(actuator_name))

    def add_special_entry(self, add_type: SpecialConfiguratorEntry):
        if add_type == SpecialConfiguratorEntry.ACTUATOR_VALUE:
            self.get_actuator_value_from_widget()
        elif add_type == SpecialConfiguratorEntry.MODULE_INIT:
            self.get_control_module_init_from_widget()

    def get_actuator_value_from_widget(self):
        self.actuator_dialog = QDialog()
        vlayout = QtWidgets.QVBoxLayout()
        widget = QtWidgets.QWidget()
        widget.setLayout(QtWidgets.QHBoxLayout())
        self.actuator_cb = QtWidgets.QComboBox()
        self.actuator_cb.addItems(self._actuators)

        self.value_sb = SpinBox(suffix=self.get_units_from_module_name(self._actuators[0]), siPrefix= False)
        self.actuator_cb.currentTextChanged.connect(self.update_suffix_in_dialog)

        widget.layout().addWidget(self.actuator_cb)
        widget.layout().addWidget(self.value_sb)

        vlayout.addWidget(widget)
        self.actuator_dialog.setLayout(vlayout)
        buttonBox = QDialogButtonBox(parent=self.actuator_dialog)

        buttonBox.addButton("Ok", QDialogButtonBox.ButtonRole.AcceptRole)
        buttonBox.accepted.connect(self.actuator_value_set)
        buttonBox.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        buttonBox.rejected.connect(self.actuator_dialog.reject)

        vlayout.addWidget(buttonBox)
        self.actuator_dialog.setWindowTitle("Fill in information about this actuator target value")

        self.actuator_dialog.open()

    def actuator_value_set(self):
        self.actuator_dialog.accept()
        self.config_model.add_data(
            self.config_model.rowCount(),
            ConfiguratorEntry(self.actuator_cb.currentText(),
                              module_type=ModuleType.Actuator,
                              setting=
                              ParameterWithPath(
                                  parameter=
                                  Parameter.create(title= 'Actuator Value',
                                                   name=SpecialConfiguratorEntry.ACTUATOR_VALUE.value,
                                                   type='float',
                                                   value=self.value_sb.value(),
                                                   suffix=self.value_sb.opts['suffix']))))

    def get_control_module_init_from_widget(self):
        self.init_module_dialog = QDialog()
        vlayout = QtWidgets.QVBoxLayout()
        widget = QtWidgets.QWidget()
        widget.setLayout(QtWidgets.QHBoxLayout())
        self.control_module_cb = QtWidgets.QComboBox()


        self.control_module_cb.addItems(self._actuators + self._detectors)

        self.init_cb = QtWidgets.QCheckBox()

        widget.layout().addWidget(self.control_module_cb)
        widget.layout().addWidget(self.init_cb)

        vlayout.addWidget(widget)
        self.init_module_dialog.setLayout(vlayout)
        buttonBox = QDialogButtonBox(parent=self.init_module_dialog)

        buttonBox.addButton("Ok", QDialogButtonBox.ButtonRole.AcceptRole)
        buttonBox.accepted.connect(self.control_module_init_set)
        buttonBox.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        buttonBox.rejected.connect(self.init_module_dialog.reject)

        vlayout.addWidget(buttonBox)
        self.init_module_dialog.setWindowTitle("Fill in information about this Control Module initialized value")
        self.init_module_dialog.open()

    def control_module_init_set(self):
        self.init_module_dialog.accept()
        module_name = self.control_module_cb.currentText()
        module_type = ModuleType.Actuator if module_name in self._actuators else ModuleType.Detector
        self.config_model.add_data(
            self.config_model.rowCount(),
            ConfiguratorEntry(module_name,
                              module_type=module_type,
                              setting=
                              ParameterWithPath(
                                  parameter=
                                  Parameter.create(title= 'Control Module Init Value',
                                                   name=SpecialConfiguratorEntry.MODULE_INIT.value,
                                                   type='bool',
                                                   value=True if self.init_cb.checkState() ==
                                                                 QtCore.Qt.CheckState.Checked else False,
                                                                          ))))

    def setup_docks(self):
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(False)
        self.tree.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragOnly)

        self.table_out = ConfiguratorTableView(True)
        self.table_out.horizontalHeader().ResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table_out.horizontalHeader().setStretchLastSection(True)
        self.table_out.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.table_out.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.table_out.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragDrop)
        self.table_out.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)

        self.config_model = ConfiguratorModel()
        self.table_out.setModel(self.config_model)
        self.table_out.add_data_signal[SpecialConfiguratorEntry].connect(self.add_special_entry)
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

        widget_buttons = QtWidgets.QWidget()
        widget_buttons.setLayout(QtWidgets.QVBoxLayout())
        widget_buttons.layout().addStretch()
        move_toolbar = self.add_toolbar('move')
        move_toolbar.setOrientation(QtCore.Qt.Orientation.Vertical)
        widget_buttons.layout().addWidget(move_toolbar)
        widget_buttons.layout().addStretch()

        vlayout.addWidget(hwidget)
        hlayout.addWidget(self.settings_tree)
        hlayout.addWidget(widget_buttons)
        hlayout.addLayout(vlayout_right)

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


    def connect_things(self):
        self.connect_action(EntryActions.ADD, self.add_setting)
        self.connect_action(EntryActions.REMOVE, self.remove_setting)
        self.connect_action(EntryActions.UP, self.move_up_setting)
        self.connect_action(EntryActions.DOWN, self.move_down_setting)


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

    def set_drag_mode_recursive(self, param: Parameter, movable=True, drop_enabled=True):
        if not param.readonly():
            param.setOpts(movable=movable, dropEnabled=drop_enabled)
        for child in param.children():
            self.set_drag_mode_recursive(child, movable, drop_enabled)

    def add_setting(self):
        if self.tree.currentItem() is not None:
            current_setting = self.tree.currentItem().param
            module, module_type = get_module_from_param(ParameterWithPath(current_setting))
            entry = ConfiguratorEntry(module, module_type, ParameterWithPath(current_setting))
            self.config_model.add_data(self.config_model.rowCount(), entry)

    def remove_setting(self):
        current_index = self.table_out.currentIndex()
        if current_index.row() != -1:
            self.config_model.remove_data(current_index.row())

    def move_up_setting(self):
        current_index = self.table_out.currentIndex()
        if current_index.row() != -1:  # means no selected row
            self.config_model.moveRow(current_index.parent(), current_index.row(),
                                      current_index.parent(), current_index.row()-1)

    def move_down_setting(self):
        current_index = self.table_out.currentIndex()
        if current_index.row() != -1:  # means no selected row
            self.config_model.moveRow(current_index.parent(), current_index.row(),
                                      current_index.parent(), current_index.row()+2)

if __name__ == "__main__":
    from pymodaq_gui.utils.utils import mkQApp
    app = mkQApp('PresetManager')

    external_ui = QtWidgets.QMainWindow()
    toolbar = QtWidgets.QToolBar()
    menu = QtWidgets.QMenu('Configurator')
    external_ui.addToolBar(toolbar)
    external_ui.menuBar().addMenu(menu)

    prog = Configurator(menu=menu, toolbar=toolbar)
    prog.update_settings()
    prog.mainwindow.show()

    external_ui.show()
    sys.exit(app.exec_())

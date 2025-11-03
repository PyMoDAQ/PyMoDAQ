from typing import Union, Optional
from pathlib import Path
import sys

from qtpy import QtWidgets, QtCore
from qtpy.QtWidgets import QStyle
from qtpy.QtWidgets import QMessageBox, QDialogButtonBox, QDialog

from pymodaq.utils.data import DataActuator
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq.utils.config import get_set_preset_path

from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq_gui.parameter.utils import ParameterWithPath
from pymodaq_gui.messenger import dialog, messagebox

from pymodaq_gui.utils.widgets.spinbox import SpinBox
from pymodaq.utils.managers.configurator.utils import (ConfiguratorParameterTree, ConfiguratorModel,
                                                       ConfiguratorEntry, ConfiguratorTableView,
                                                       get_module_from_param, config_entry_from_path,
                                                       ModuleType, ParameterDelegate, EntryActions,
                                                       ConfigurationAction, SpecialConfiguratorEntry)
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.parameter.utils import compareParameters

from pymodaq.utils.config import get_set_configurator_path
from pymodaq.utils.managers.modules_manager import ModulesManager, ModuleType
from pymodaq_gui.utils.custom_app import CustomApp


logger = set_logger(get_module_name(__file__))


class Configurator(CustomApp):
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

    new_file = QtCore.Signal()

    def __init__(self, preset_filename: str = ''):
        super().__init__(parent=QtWidgets.QMainWindow(),
                         tree=ConfiguratorParameterTree())

        self.preset_filename = preset_filename
        self._actuators: list[str] = None
        self._detectors: list[str] = None

        self.main_widget = QtWidgets.QWidget()
        self.mainwindow.setCentralWidget(self.main_widget)

        self.setup_ui()

    @property
    def preset_filename(self) -> str:
        return self.get_action('preset_filename').currentText()

    @preset_filename.setter
    def preset_filename(self, preset_filename: str):
        if preset_filename in [path.stem for path in get_set_preset_path().iterdir()]:
            self.get_action('configurations').clear()
            self.get_action('preset_filename').setText(preset_filename)
            self.get_action('configurations').addItems(
                self.get_configurations(get_set_configurator_path(preset_filename)) + ['...'])

    @staticmethod
    def config_entry_from_path(filename: Union[str, Path]) -> list[ConfiguratorEntry]:
        return config_entry_from_path(filename)

    def apply_configuration(self, modules_manager: ModulesManager, configuration_path: Path):
        """
        Apply a saved configuration to the modules.

        Parameters
        ----------
        modules_manager : ModulesManager
            Manager containing all active modules
        configuration_path : Path
            Path to the configuration file to apply

        """
        pwp_list = self.config_entry_from_path(configuration_path)
        incompatible_index = self.check_parameters(pwp_list, modules_manager.get_settings_all())
        for index, entry in enumerate(pwp_list):
            if index not in incompatible_index:
                mod = modules_manager.get_mod_from_name(entry.module_name, entry.module_type)
                if SpecialConfiguratorEntry.ACTUATOR_VALUE in entry.setting.path:
                    mod.move_abs(DataActuator(entry.module_name, data=entry.setting.parameter.value(),
                                              units=entry.setting.parameter.opts.get('suffix', mod.units)))
                elif SpecialConfiguratorEntry.MODULE_INIT in entry.setting.path:
                    if entry.setting.parameter.value():
                        mod.init_hardware_ui(True)
                        #todo call the line below in new Manager implementation that has dashboard as an argument
                        #self.dashboard.poll_init()
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

        self.config_model = ConfiguratorModel(actuators=self._actuators)
        self.table_out.setModel(self.config_model)
        self.table_out.add_data_signal[SpecialConfiguratorEntry].connect(self.add_special_entry)
        self.table_out.remove_row_signal[int].connect(self.config_model.remove_data)
        self.table_out.load_data_signal.connect(self.config_model.load)
        self.table_out.save_data_signal.connect(self.config_model.save)
        self.delegate = ParameterDelegate()
        self.table_out.setItemDelegate(self.delegate)

        self.add_toolbar('configurations')

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

        self.add_widget('preset_label', QtWidgets.QLabel('Configuration from Preset:'))
        self.add_widget('preset_filename', QtWidgets.QLabel(''), tip='Name of the current preset')


        self.add_action(EntryActions.ADD, 'Add', 'SP_ArrowRight', toolbar='move')
        self.add_action(EntryActions.REMOVE, 'Remove', 'SP_ArrowLeft', toolbar='move',
                        shortcut=QtCore.Qt.Key.Key_Delete)
        self.add_action(EntryActions.UP, 'Move Up', 'SP_ArrowUp', toolbar='move')
        self.add_action(EntryActions.DOWN, 'Move Down', 'SP_ArrowDown', toolbar='move')

        self.add_widget('configurations', QtWidgets.QComboBox(),
                        tip='List of available configurations',
                        toolbar='configurations')
        self.add_action(ConfigurationAction.COPY, 'Copy Configuration', 'EditCopy', toolbar='configurations')
        self.add_action(ConfigurationAction.NEW, 'New Configuration', 'ListAdd',
                        toolbar='configurations',
                        tip='Create a new configuration file')
        self.add_action(ConfigurationAction.DELETE, 'Delete Configuration', 'ListRemove',
                        toolbar='configurations',
                        tip='Delete the current configuration file')
        self.add_action(ConfigurationAction.SAVE, 'Save Configuration', 'DocumentSave',
                        toolbar='configurations',
                        tip='Save/Update the current configuration')
        self.add_action(ConfigurationAction.RELOAD, 'Reload Configuration', 'ViewRefresh',
                        toolbar='configurations',
                        tip='Reload the current configuration file')


    def connect_things(self):
        self.connect_action(EntryActions.ADD, self.add_setting)
        self.connect_action(EntryActions.REMOVE, self.remove_setting)
        self.connect_action(EntryActions.UP, self.move_up_setting)
        self.connect_action(EntryActions.DOWN, self.move_down_setting)

        self.connect_action(ConfigurationAction.COPY, self.copy_configuration)
        self.connect_action(ConfigurationAction.NEW, self.create_configuration)
        self.connect_action(ConfigurationAction.DELETE, self.delete_configuration)
        self.connect_action(ConfigurationAction.SAVE, lambda: self.save_check())
        self.connect_action(ConfigurationAction.RELOAD, self.load_configuration)

        self.connect_action('configurations', self.get_action(ConfigurationAction.RELOAD).trigger,
                            signal_name='currentTextChanged')

    def load_configuration(self):
        preset_name = self.get_action('preset_filename').text()
        config_name = self.get_action('configurations').currentText()
        if config_name == '...':
            self.create_configuration()
            return
        self.config_model.load(get_set_configurator_path(preset_name).joinpath(f'{config_name}.config'))


    @staticmethod
    def get_configurations(preset_name: str) -> list[str]:
        """ Get all existing configuration files within a preset name """
        configs = []
        configuration_path = get_set_configurator_path(preset_name)
        if not configuration_path.exists():
            configuration_path.mkdir(parents=True)
        if not configuration_path.joinpath(f'default.config').exists():
            configuration_path.joinpath(f'default.config').touch()

        for file in get_set_configurator_path(preset_name).iterdir():
            if '.config' in file.suffix:
                configs.append(file.stem)
        configs.sort()
        if 'default' in configs:  #  make sure the default is the first one shown
            default = configs.pop(configs.index('default'))
            configs.insert(0, default)
        return configs

    def create_configuration(self):
        text, ok = QtWidgets.QInputDialog.getText(None, "Enter a NEW configuration name",
                                                  "Config name:", QtWidgets.QLineEdit.EchoMode.Normal)
        if ok and text != '':
            configurations = [self.get_action('configurations').itemText(ind).lower() for
                       ind in range(self.get_action('configurations').count())]
            if text.lower() not in configurations:
                configurations.append(text.lower())
                configurations.sort()
                index = configurations.index(text.lower())
                self.get_action('configurations').insertItem(index-1, text)
            self.get_action('configurations').setCurrentText(text)

    def copy_configuration(self):
        text, ok = QtWidgets.QInputDialog.getText(None, "Enter a NEW configuration name",
                                                  "Config name:", QtWidgets.QLineEdit.EchoMode.Normal)
        if ok and text != '':
            self.save_check(text)
            configurations = [self.get_action('configurations').itemText(ind).lower() for
                              ind in range(self.get_action('configurations').count())]
            if text.lower() not in configurations:
                configurations.append(text.lower())
                configurations.sort()
                index = configurations.index(text.lower())
                self.get_action('configurations').insertItem(index-1, text)
            self.get_action('configurations').setCurrentText(text)


    def delete_configuration(self, preset_name: Optional[str] = None, config_name: Optional[str] = None):
        if preset_name is None:
            preset_name = self.get_action('preset_filename').text()
        if config_name is None:
            config_name = self.get_action('configurations').currentText()
        user_agreed = dialog('Removing a Configuration',
                             message=f"You're going to delete the {config_name} file\nAre you sure?")
        if user_agreed:
            get_set_configurator_path(preset_name).joinpath(f'{config_name}.config').unlink(missing_ok=True)
            self.get_action('configurations').removeItem(self.get_action('configurations').currentIndex())

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

    def create_modify_configurator(self, preset_name: str, settings: Union[Parameter, Path] = None):
        """
        Create or modify a configuration for a given preset.

        Parameters
        ----------
        preset_name : str
            Name of the preset to configure
        settings : Union[Parameter, Path], optional
            Settings to load, by default None
        single_preset : bool, optional
            If True, locks the preset selection, by default False
        """
        if settings is None:
            settings = preset_name
        self.preset_filename = preset_name
        self.update_settings(settings)
        self.mainwindow.show()

    def save_check(self, configuration_name: str = None):
        """
        Check if current configuration can be saved and save it.

        Verifies that:
        - Configuration has entries
        - A filename is specified
        - Handles file overwrite confirmation
        """
        if self.get_action('configurations').currentText() == '' and configuration_name is None:
            messagebox(
                title="Saving issue",
                text="You didn't specify a file name for this configuration",
            )
            return

        else:
            if configuration_name is None:
                configuration_name = self.get_action('configurations').currentText()
            file_path = get_set_configurator_path(self.get_action('preset_filename').text()).joinpath(
                f"{configuration_name}.config")
            if file_path.exists():
                user_agreed = dialog(
                    title="Overwrite confirmation",
                    message="File exist do you want to overwrite it ?",
                )
                if not user_agreed:
                    return
            if not file_path.parent.exists():
                file_path.parent.mkdir(parents=True)
            self.config_model.save(file_path)
            self.new_file.emit()

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
    app = mkQApp('Configurator')

    prog = Configurator()
    prog.update_settings()
    prog.mainwindow.show()

    sys.exit(app.exec_())

from typing import Union, Optional
from pathlib import Path
import sys

from qtpy import QtWidgets, QtCore
from qtpy.QtWidgets import QStyle
from qtpy.QtWidgets import QMessageBox, QDialogButtonBox, QDialog

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq_gui.parameter.utils import ParameterWithPath, get_param_from_name
from pymodaq_gui.messenger import dialog, messagebox
from pymodaq_gui.managers.action_manager import addaction
from pymodaq_gui.utils.file_io import select_file
from pymodaq_gui.parameter.pymodaq_ptypes.list import Combo_pb
from pymodaq.utils.managers.configurator.utils import (ConfiguratorParameterTree, ConfiguratorModel,
                                                       ConfiguratorEntry, ConfiguratorTableView,
                                                       get_module_from_param, config_entry_from_path,
                                                       ModuleType, ParameterDelegate)
from pymodaq_gui.managers.parameter_manager import ParameterManager

from pymodaq.utils.config import get_set_configurator_path

logger = set_logger(get_module_name(__file__))


class Combo_pb(QtWidgets.QWidget):

    delete_config = QtCore.Signal(str)

    def __init__(self, items: list[str] = None):
        super(Combo_pb, self).__init__()
        if items is None:
            items = []
        self.make_widget(items)
        self.add_action.triggered.connect(self.add_an_item)
        self.delete_action.triggered.connect(self.remove_an_item)

    @property
    def count(self):
        return self.combo.count()

    def make_widget(self, items: list[str]):
        """
            Init the User Interface.
        """
        self.hor_layout = QtWidgets.QHBoxLayout()

        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(items)
        self.toolbar = QtWidgets.QToolBar()

        self.add_action = addaction('Add Config', 'Add2', tip='Create a new configuration',
                                    toolbar=self.toolbar)
        self.delete_action = addaction('Remove Config', 'remove', tip='Delete an existing configuration',
                                       toolbar=self.toolbar)
        self.hor_layout.addWidget(self.combo)
        self.hor_layout.addWidget(self.toolbar)

        self.hor_layout.setSpacing(0)
        self.hor_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.hor_layout)

        self.currentText = self.combo.currentText
        self.currentTextChanged = self.combo.currentTextChanged
        self.setCurrentIndex = self.combo.setCurrentIndex
        self.clear = self.combo.clear
        self.addItem = self.combo.addItem
        self.addItems = self.combo.addItems
        self.findText = self.combo.findText

    def add_an_item(self):
        text, ok = QtWidgets.QInputDialog.getText(None, "Enter a NEW configuration name",
                                                  "Config name:", QtWidgets.QLineEdit.Normal)
        if ok and text != '':
            self.addItem(text)
            self.combo.setCurrentText(text)

    def remove_an_item(self):
        config = self.combo.currentText()
        user_agreed = dialog('Removing a Configuration',
                             message=f"You're going to delete the {config} file\nAre you sure?")
        if user_agreed:
            self.combo.removeItem(self.combo.currentIndex())
            self.delete_config.emit(config)



class Configurator(QtCore.QObject):

    new_file = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self._actuators: list[str] = None
        self.control_modules_settings: Parameter = None

    @staticmethod
    def config_entry_from_path(filename: str) -> list[ConfiguratorEntry]:
        return config_entry_from_path(filename)

    @staticmethod
    def check_parameters(entries: list[ConfiguratorEntry], settings: Parameter):
        """Check if the extracted Config entries are compatible with the given settings
        in terms of path"""
        incompatible_index = []
        for entry in entries:
            settings.child(entry.module_type.value).children()

    def populate_from_settings(self, settings: Parameter):
        self.control_modules_settings = settings
        self.set_drag_mode_recursive(self.control_modules_settings, movable=True, drop_enabled=True)
        self._actuators = [
            param.opts['title'] for param in self.control_modules_settings.child(ModuleType.Actuator).children()]

    def populate_from_preset_file(self, file_path: Path):
        """ for quick testing purpose, not meant to be used at the end"""
        children = ioxml.XML_file_to_parameter(file_path)
        self.control_modules_settings = Parameter.create(
            title="Control Modules:", name="control_modules", type="group", children=children
        )
        self.set_drag_mode_recursive(self.control_modules_settings, movable=True, drop_enabled=True)
        self._actuators = [
            param.child('name').value() for param in self.control_modules_settings.child('Moves').children()]

    def make_widget(self, config_file_path: Optional[Union[str, Path]] = None) -> QtWidgets.QWidget:
        config_file_path = Path(config_file_path)
        main_widget = QtWidgets.QWidget()

        self.parameter_manager = ParameterManager(tree=ConfiguratorParameterTree())
        self.tree_in = self.parameter_manager.tree
        self.parameter_manager.settings = self.control_modules_settings
        self.tree_in.setDragEnabled(True)
        self.tree_in.setAcceptDrops(False)
        self.tree_in.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragOnly)

        self.preset_filename = QtWidgets.QLineEdit()
        self.preset_filename.setToolTip('Name of the current preset')
        self.preset_filename.setReadOnly(True)

        self.table_out = ConfiguratorTableView(True)
        self.table_out.horizontalHeader().ResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table_out.horizontalHeader().setStretchLastSection(True)
        self.table_out.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.table_out.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.table_out.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragDrop)
        self.table_out.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)

        self.config_model = ConfiguratorModel(actuators=self._actuators)
        self.table_out.setModel(self.config_model)
        self.table_out.add_data_signal[int].connect(self.config_model.add_data)
        self.table_out.remove_row_signal[int].connect(self.config_model.remove_data)
        self.table_out.load_data_signal.connect(self.config_model.load)
        self.table_out.save_data_signal.connect(self.config_model.save)
        self.delegate = ParameterDelegate()
        self.table_out.setItemDelegate(self.delegate)

        self.configurations_cb = Combo_pb()

        vlayout = QtWidgets.QVBoxLayout()
        hwidget = QtWidgets.QWidget()
        hlayout = QtWidgets.QHBoxLayout()
        hwidget.setLayout(hlayout)
        vlayout_right = QtWidgets.QVBoxLayout()

        widget_buttons = QtWidgets.QWidget()
        widget_buttons.setLayout(QtWidgets.QVBoxLayout())

        add_button = QtWidgets.QPushButton('Add')
        pixmapi = getattr(QStyle.StandardPixmap, 'SP_ArrowRight')
        icon = widget_buttons.style().standardIcon(pixmapi)
        add_button.setIcon(icon)
        add_button.clicked.connect(self.add_setting)

        remove_button = QtWidgets.QPushButton('Remove')
        pixmapi = getattr(QStyle.StandardPixmap, 'SP_ArrowLeft')
        icon = widget_buttons.style().standardIcon(pixmapi)
        remove_button.setIcon(icon)
        remove_button.clicked.connect(self.remove_setting)

        widget_buttons.layout().addStretch()
        widget_buttons.layout().addWidget(add_button)
        widget_buttons.layout().addWidget(remove_button)
        widget_buttons.layout().addStretch()

        layout_header = QtWidgets.QHBoxLayout()

        layout_header.addWidget(QtWidgets.QLabel('Configuration from Preset: '))
        layout_header.addWidget(self.preset_filename)
        vlayout.addLayout(layout_header)
        vlayout.addWidget(hwidget)
        hlayout.addWidget(self.parameter_manager.settings_tree)
        hlayout.addWidget(widget_buttons)
        hlayout.addLayout(vlayout_right)

        vlayout_right.addWidget(self.configurations_cb)
        vlayout_right.addWidget(self.table_out)

        main_widget.setLayout(vlayout)

        return main_widget

    @staticmethod
    def get_configurations(preset_name: str) -> list[str]:
        """ Get all existing configuration files within a preset name """
        configs = []
        for file in get_set_configurator_path(preset_name).iterdir():
            if '.config' in file.suffix:
                configs.append(file.stem)
        return configs

    @staticmethod
    def delete_configuration(preset_name: str, config_name: str):
        get_set_configurator_path(preset_name).joinpath(f'{config_name}.config').unlink(missing_ok=True)

    def create_modify_configurator(self,
                                   preset_name: str = 'apreset',
                                   ):

        self.dialog = QDialog()
        vlayout = QtWidgets.QVBoxLayout()

        configurator_widget = self.make_widget(config_file_path=get_set_configurator_path(preset_name))
        self.configurations_cb.currentTextChanged.connect(
        lambda config_name: self.config_model.load(
            get_set_configurator_path(preset_name).joinpath(f'{config_name}.config')))
        self.configurations_cb.addItems(self.get_configurations(get_set_configurator_path(preset_name)))
        self.configurations_cb.delete_config.connect(
            lambda config_name: self.delete_configuration(preset_name, config_name))

        self.preset_filename.setText(preset_name)

        buttonBox = QDialogButtonBox(parent=self.dialog)
        buttonBox.addButton("Save", QDialogButtonBox.ButtonRole.AcceptRole)
        buttonBox.accepted.connect(self.dialog_check)
        buttonBox.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        buttonBox.rejected.connect(self.dialog.reject)

        vlayout.addWidget(configurator_widget)
        vlayout.addWidget(buttonBox)
        self.dialog.setLayout(vlayout)
        self.dialog.setWindowTitle("Configurator Manager")

        res = self.dialog.open()

    def dialog_check(self):
        if self.config_model.rowCount() == 0:
            messagebox(
                title="Saving issue",
                text="You didn't specify any configuration entry to be saved",
            )
            return
        if self.configurations_cb.currentText == '':
            messagebox(
                title="Saving issue",
                text="You didn't specify a file name for this configuration",
            )
            return

        else:
            file_path = get_set_configurator_path(self.preset_filename.text()).joinpath(
                f'{self.configurations_cb.currentText()}.config')
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
            self.dialog.accept()
            self.new_file.emit()

    def set_drag_mode_recursive(self, param: Parameter, movable=True, drop_enabled=True):
        param.setOpts(movable=movable, dropEnabled=drop_enabled)
        for child in param.children():
            self.set_drag_mode_recursive(child, movable, drop_enabled)

    def add_setting(self):
        current_setting = self.tree_in.currentItem().param
        module, module_type = get_module_from_param(ParameterWithPath(current_setting))
        entry = ConfiguratorEntry(module, module_type, ParameterWithPath(current_setting))
        self.config_model.add_data(self.config_model.rowCount(), entry)

    def remove_setting(self):
        current_index = self.table_out.currentIndex()
        self.config_model.remove_data(current_index.row())


if __name__ == "__main__":
    from pymodaq_gui.utils.utils import mkQApp
    app = mkQApp('Configurator')

    from pymodaq.utils.config import get_set_preset_path

    preset_path = get_set_preset_path().joinpath('preset_default.xml')

    prog = Configurator()
    prog.populate_from_preset_file(preset_path)
    prog.create_modify_configurator('beam_steering')

    sys.exit(app.exec_())

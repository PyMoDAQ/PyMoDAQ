from typing import Union, Optional
from pathlib import Path
import sys

from qtpy import QtWidgets, QtCore
from qtpy.QtWidgets import QStyle
from qtpy.QtWidgets import QMessageBox, QDialogButtonBox, QDialog

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.parameter import Parameter, ioxml
from pymodaq_gui.parameter.utils import ParameterWithPath
from pymodaq_gui.messenger import dialog, messagebox
from pymodaq_gui.utils.file_io import select_file
from pymodaq.utils.managers.configurator.utils import (ConfiguratorParameterTree, ConfiguratorModel,
                                                       ConfiguratorEntry, ConfiguratorTableView,
                                                       get_module_from_param, parameter_with_path_from_file)
from pymodaq_gui.managers.parameter_manager import ParameterManager

from pymodaq.utils.config import get_set_configurator_path

logger = set_logger(get_module_name(__file__))



class Configurator:

    def __init__(self):
        self._actuators: list[str] = None
        self.control_modules_settings: Parameter = None

    @staticmethod
    def parameter_with_path_from_file(filename: str) -> list[ParameterWithPath]:
        return parameter_with_path_from_file(filename)

    @staticmethod
    def check_parameters(parameters: list[ParameterWithPath], settings: Parameter):
        """Check if the extracted parameters are compatible with the given settings
        in terms of path"""
        incompatible_index = []
        for pwp in parameters:
            pass


    def populate_from_settings(self, settings: Parameter):
        self.control_modules_settings = settings
        self.set_drag_mode_recursive(self.control_modules_settings, movable=True, drop_enabled=True)
        self._actuators = [
            param.opts['title'] for param in self.control_modules_settings.child('actuators').children()]

    def populate_from_preset_file(self, file_path: Path):
        ### for quick testing purpose, not meant to be used at the end"""
        children = ioxml.XML_file_to_parameter(file_path)
        self.control_modules_settings = Parameter.create(
            title="Control Modules:", name="control_modules", type="group", children=children
        )
        self.set_drag_mode_recursive(self.control_modules_settings, movable=True, drop_enabled=True)
        self._actuators = [
            param.child('name').value() for param in self.control_modules_settings.child('Moves').children()]
        self.create_modify_configurator()

    def make_widget(self, config_file_path: Optional[Union[str, Path]] = None) -> QtWidgets.QWidget:
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

        self.filename_edit = QtWidgets.QLineEdit()
        self.filename_edit.setToolTip('Name of the current configuration')

        self.table_out = ConfiguratorTableView(True)
        self.table_out.horizontalHeader().ResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table_out.horizontalHeader().setStretchLastSection(True)
        self.table_out.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.table_out.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.table_out.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragDrop)

        self.config_model = ConfiguratorModel(actuators=self._actuators)
        self.table_out.setModel(self.config_model)
        self.table_out.add_data_signal[int].connect(self.config_model.add_data)
        self.table_out.remove_row_signal[int].connect(self.config_model.remove_data)
        self.table_out.load_data_signal.connect(self.config_model.load)
        self.table_out.save_data_signal.connect(self.config_model.save)

        if config_file_path is not None:
            self.config_model.load(config_file_path)
            self.filename_edit.setText(config_file_path.stem)

        vlayout = QtWidgets.QVBoxLayout()
        hwidget = QtWidgets.QWidget()
        hlayout = QtWidgets.QHBoxLayout()
        hwidget.setLayout(hlayout)

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

        vlayout.addWidget(QtWidgets.QLabel('Configuration from Preset:'))
        vlayout.addWidget(self.preset_filename)
        vlayout.addWidget(QtWidgets.QLabel('Enter a name for this configuration:'))
        vlayout.addWidget(self.filename_edit)
        vlayout.addWidget(hwidget)
        hlayout.addWidget(self.parameter_manager.settings_tree)
        hlayout.addWidget(widget_buttons)
        hlayout.addWidget(self.table_out)

        main_widget.setLayout(vlayout)

        return main_widget

    def create_modify_configurator(self,
                                   preset_name: str = 'apreset',
                                   modify=False):
        path = None
        if modify:
            path = select_file(start_path=get_set_configurator_path(preset_name), save=False, ext="config")
            if path == "":
                return

        self.dialog = QDialog()
        vlayout = QtWidgets.QVBoxLayout()

        configurator_widget = self.make_widget(config_file_path=path)

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
        if self.filename_edit.text() == '':
            messagebox(
                title="Saving issue",
                text="You didn't specify a file name for this configuration",
            )
            return

        else:
            file_path = get_set_configurator_path(self.preset_filename.text()).joinpath(
                f'{self.filename_edit.text()}.config')
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
    prog.create_modify_configurator()

    sys.exit(app.exec_())

import os
from pathlib import Path
import sys
from dataclasses import dataclass
from typing import Union, Tuple

from docutils.nodes import title
from qtpy import QtWidgets, QtCore

from qtpy.QtCore import QMimeData, Qt, QVariant
from qtpy.QtWidgets import QMessageBox, QDialogButtonBox, QDialog, QStyle
from qtpy.QtGui import QIcon, QPixmap

import pymodaq_utils.config as config_mod
from pymodaq_utils.array_manipulation import limit
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.parameter.utils import ParameterWithPath, get_param_path
from pymodaq_gui.utils.file_io import select_file
from pymodaq_gui.parameter import ParameterTree, Parameter
from pymodaq_gui.utils.widgets.table import TableView, TableModel
from pymodaq_gui.parameter import ioxml
from pymodaq_gui.messenger import dialog as dialogbox
from pymodaq.utils import config as config_mod_pymodaq
from pymodaq.extensions import get_models
from pymodaq_utils.serialize.factory import SerializableFactory, SerializableBase


import pymodaq.utils.managers.preset_manager_utils  # to register move and det types

logger = set_logger(get_module_name(__file__))

# check if preset_mode directory exists on the drive
preset_path = config_mod_pymodaq.get_set_preset_path()
overshoot_path = config_mod_pymodaq.get_set_overshoot_path()
layout_path = config_mod_pymodaq.get_set_layout_path()

ser_factory = SerializableFactory()


@SerializableFactory.register_decorator()
@dataclass
class ConfiguratorEntry:
    module_name: str
    setting: ParameterWithPath

    @staticmethod
    def serialize(entry: 'ConfiguratorEntry') -> bytes:
        """

        """
        bytes_string = b''
        bytes_string += ser_factory.get_apply_serializer(entry.setting)
        bytes_string += ser_factory.get_apply_serializer(entry.module_name)
        return bytes_string

    @classmethod
    def deserialize(cls,
                    bytes_str: bytes) -> Union['ConfiguratorEntry',
    Tuple['ConfiguratorEntry', bytes]]:
        """Convert bytes into a ParameterWithPath object

        Returns
        -------
        ParameterWithPath: the decoded object
        bytes: the remaining bytes string if any
        """
        parameter_with_path, remaining_bytes = ser_factory.get_apply_deserializer(bytes_str, False)
        module_name, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)
        return ConfiguratorEntry(module_name, parameter_with_path), remaining_bytes


mock_list = ['elt1', 'elt2', 'elt3']
mock_entry = ConfiguratorEntry('Photodiode',
                               ParameterWithPath(
                                   parameter=Parameter.create(title='mytitle', name='myname',
                                                    type='list', value=mock_list[0],
                                                    limits=mock_list)))



class ConfiguratorModel(TableModel):
    def __init__(self, data: list[ConfiguratorEntry]=None, header=['Module Name', 'Setting Title', 'Value'], cast=str):
        self._data: list[ConfiguratorEntry] = None
        if data is None:
            data = [mock_entry]
        super().__init__(data, header, editable=[False, False, True], cast=cast)
        pass

    def columnCount(self, parent):
        return 3

    def mimeTypes(self):
        types = super().mimeTypes()
        types.append('pymodaq/parameter_with_path')
        types.append('pymodaq/configurator_entry')
        return types

    def mimeData(self, items):
        data = QMimeData()
        entry = self._data[items[0].row()]
        data.setData('pymodaq/configurator_entry', ConfiguratorEntry.serialize(entry))
        return data

    def data(self, index, role):
        if index.isValid():
            if role == Qt.DisplayRole or role == Qt.EditRole:
                entry: ConfiguratorEntry = self._data[index.row()]
                if index.column() == 0:
                    dat = entry.module_name
                elif index.column() == 1:
                    dat = entry.setting.parameter.name()
                elif index.column() == 2:
                    dat = entry.setting.parameter.value()
                else:
                    dat = ''
                return dat
            elif role == Qt.CheckStateRole and index.column() == 0 and self._show_checkbox:
                if self._checked[index.row()]:
                    return Qt.CheckState.Checked
                else:
                    return Qt.CheckState.Unchecked
        return QVariant()

    def dropMimeData(self, data: QMimeData, action, row, column, parent):
        if row == -1:
            row = self.rowCount(parent)
        if data.hasFormat('pymodaq/configurator_entry'):
            entry = ConfiguratorEntry.deserialize(data.data('pymodaq/configurator_entry').data())[0]
        else:
            entry = mock_entry
        self.data_tmp = entry
        self.insertRows(row, 1, parent)
        return True


class ParameterTree(ParameterTree):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mimeTypes(self):
        types = super().mimeTypes()
        types.append('pymodaq/parameter_with_path')
        types.append('pymodaq/configurator_entry')
        return types

    def mimeData(self, items):
        data = QMimeData()
        param_with_path = ParameterWithPath(items[0].param)
        module = self.get_module_from_param(param_with_path)
        if module is not None:
            entry = ConfiguratorEntry(module, param_with_path)
            data.setData('pymodaq/configurator_entry', ConfiguratorEntry.serialize(entry))
        return data

    def get_module_from_param(self, param: ParameterWithPath) -> Union[str, None]:
        if 'Actuators' in param.path or 'Moves' in param.path:
            try:
                index = param.path[::-1].index('Actuators')
            except ValueError:
                index = param.path[::-1].index('Moves')  #backcompat with old style preset
        elif 'Detectors' in param.path:
            index = param.path[::-1].index('Detectors')
        else:
            return None

        param_module = param.parameter
        for _ in range(index-1):
            param_module = param_module.parent()
        module = param_module.child('name').value()
        return module



class Configurator:
    def __init__(self, file_path: Path):
        self.control_modules_settings: Parameter = None
        self.set_dashboard_content_from_file(file_path)

    def set_dashboard_content_from_file(self, file_path: Path):

        children = ioxml.XML_file_to_parameter(file_path)
        self.control_modules_settings = Parameter.create(
            title="Control Modules:", name="control_modules", type="group", children=children
        )
        self.set_drag_mode_recursive(self.control_modules_settings, movable=True, drop_enabled=True)
        self.show_configurator()

    def show_configurator(self):

        self.tree_in = ParameterTree()
        self.tree_in.setParameters(self.control_modules_settings, showTop=False)
        self.tree_in.setDragEnabled(True)
        self.tree_in.setAcceptDrops(False)
        self.tree_in.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragOnly)

        self.table_out = TableView()
        self.config_model = ConfiguratorModel()
        self.table_out.setModel(self.config_model)
        self.table_out.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragDrop)

        self.main_widget = QtWidgets.QWidget()

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

        widget_buttons.layout().addWidget(add_button)


        vlayout.addWidget(hwidget)
        hlayout.addWidget(self.tree_in)
        hlayout.addWidget(widget_buttons)
        hlayout.addWidget(self.table_out)

        self.main_widget.setLayout(vlayout)

        self.main_widget.setWindowTitle("Fill in information about this manager")
        self.main_widget.show()

    def set_drag_mode_recursive(self, param: Parameter, movable=True, drop_enabled=True):
        param.setOpts(movable=movable, dropEnabled=drop_enabled)
        for child in param.children():
            self.set_drag_mode_recursive(child, movable, drop_enabled)


    def add_setting(self):
        current_setting = self.tree_in.currentItem()


if __name__ == "__main__":

    from pymodaq.utils.config import get_set_preset_path

    preset_path = get_set_preset_path().joinpath('preset_default.xml')

    app = QtWidgets.QApplication(sys.argv)


    prog = Configurator(preset_path)

    sys.exit(app.exec_())

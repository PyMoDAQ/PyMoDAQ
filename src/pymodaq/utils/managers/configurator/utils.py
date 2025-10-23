
import os
from pathlib import Path
import sys
from dataclasses import dataclass
from typing import Union, Tuple

from qtpy import QtWidgets, QtCore

from qtpy.QtCore import QMimeData, Qt, QVariant
from qtpy.QtWidgets import QMessageBox, QDialogButtonBox, QDialog, QStyle

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.enums import StrEnum
from pymodaq_gui.parameter.utils import ParameterWithPath, get_param_path

from pymodaq_gui.parameter import ParameterTree, Parameter
from pymodaq_gui.managers.parameter_manager import ParameterManager, ParameterTreeWidget
from pymodaq_gui.utils.widgets.table import TableView, TableModel
from pymodaq_gui.utils.widgets.spinbox import SpinBox

from pymodaq_gui import utils as gutils

from pymodaq_utils.serialize.factory import SerializableFactory, SerializableBase

from pymodaq.utils.config import get_set_configurator_path
from pymodaq.utils.managers.modules_manager import ModuleType


logger = set_logger(get_module_name(__file__))
ser_factory = SerializableFactory()


class ConfiguratorActions(StrEnum): # used in the DashBoard
    New = "new_configuration"
    Modify = "modify_configuration"
    Label = "configuration_label"
    List = "configuration_list"
    Load = "load_configuration"


def get_module_index_from_param(param: ParameterWithPath) -> Union[int, None]:
    if ModuleType.Actuator in param.path or 'Moves' in param.path:
        try:
            index = param.path[::-1].index(ModuleType.Actuator)
        except ValueError:
            index = param.path[::-1].index('Moves')  #backcompat with old style preset
    elif 'Detectors' in param.path or ModuleType.Detector in param.path:
        try:
            index = param.path[::-1].index(ModuleType.Detector)
        except ValueError:
            index = param.path[::-1].index('Detectors')  #backcompat with old style preset
    else:
        return None
    return len(param.path) - index


def get_module_from_param(param: ParameterWithPath) -> Union[tuple[str, ModuleType], None]:
    index = get_module_index_from_param(param)
    if index is None:
        return None
    if ModuleType.Actuator in param.path or 'Moves' in param.path:
        module_type = ModuleType.Actuator
    elif 'Detectors' in param.path or ModuleType.Detector in param.path:
        module_type = ModuleType.Detector
    else:
        return None
    index = len(param.path) - index
    param_module = param.parameter
    for _ in range(index-1):
        param_module = param_module.parent()
    module = param_module.child('name').value()
    return module, module_type


@SerializableFactory.register_decorator()
@dataclass
class ConfiguratorEntry:
    module_name: str
    module_type: ModuleType
    setting: ParameterWithPath

    @staticmethod
    def serialize(entry: 'ConfiguratorEntry') -> bytes:
        """

        """
        bytes_string = b''
        bytes_string += ser_factory.get_apply_serializer(entry.setting)
        bytes_string += ser_factory.get_apply_serializer(entry.module_name)
        bytes_string += ser_factory.get_apply_serializer(entry.module_type.value)
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
        module_type, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)
        module_type = ModuleType(module_type)
        return ConfiguratorEntry(module_name, module_type, parameter_with_path), remaining_bytes


def parameter_with_path_from_file(fname: str) -> list[ParameterWithPath]:
    with open(fname, 'rb') as file:
        lines = file.readlines()
    all_lines = b''
    for line in lines:
        all_lines += line
    data = []
    while len(all_lines) > 0:
        entry, all_lines = ConfiguratorEntry.deserialize(all_lines)
        data.append(entry)
    return data


mock_list = ['elt1', 'elt2', 'elt3']
mock_entry = ConfiguratorEntry('Photodiode',
                               ModuleType.Detector,
                               ParameterWithPath(
                                   parameter=Parameter.create(title='mytitle', name='myname',
                                                              type='list', value=mock_list[0],
                                                              limits=mock_list)))



class ConfiguratorModel(TableModel):
    def __init__(self, data: list[ConfiguratorEntry]=None,
                 header=('Module Name', 'Setting Title', 'Value'),
                 actuators: list[str] = None
                 ):
        self._data: list[ConfiguratorEntry] = None
        self.actuators = actuators
        if data is None:
            data = []
        super().__init__(data, header, editable=[False, False, False])
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

    def clear(self):
        self._data = []

    def edit_data(self, index):
        entry = self._data[index.row()]
        dialog = QDialog()

        vlayout = QtWidgets.QVBoxLayout()
        dialog.setLayout(vlayout)

        module_index = get_module_index_from_param(entry.setting)
        vlayout.addWidget(QtWidgets.QLabel(
            f'Setting from module {entry.module_name} with path:\n {entry.setting.path[module_index+2:]}'))
        setting = Parameter.create(name='settings', type='group', children=[entry.setting.parameter.saveState()])
        tree = ConfiguratorParameterTree(parent=dialog)
        tree.setParameters(setting, showTop=False)
        buttonBox = QDialogButtonBox(parent=dialog)
        buttonBox.addButton("Done", QDialogButtonBox.ButtonRole.AcceptRole)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        buttonBox.rejected.connect(dialog.reject)

        vlayout.addWidget(tree)
        vlayout.addWidget(buttonBox)
        dialog.setWindowTitle("Edit the setting")
        res = dialog.exec()

        if res:
            entry.setting.parameter.setValue(setting.children()[0].value())


    def add_data(self, row, data: ConfiguratorEntry = None):
        if data is None:
            data = self.get_data_from_value_widget()

        if data is not None:
            self.insert_data(row, data)

    def get_data_from_value_widget(self) -> ConfiguratorEntry:
        suffix = ''

        dialog = QDialog()
        vlayout = QtWidgets.QVBoxLayout()
        widget = QtWidgets.QWidget()
        widget.setLayout(QtWidgets.QHBoxLayout())
        actuator_cb = QtWidgets.QComboBox()
        actuator_cb.addItems(self.actuators)

        value_sb = SpinBox(suffix=suffix, siPrefix= True)
        widget.layout().addWidget(actuator_cb)
        widget.layout().addWidget(value_sb)

        vlayout.addWidget(widget)
        dialog.setLayout(vlayout)
        buttonBox = QDialogButtonBox(parent=dialog)

        buttonBox.addButton("Ok", QDialogButtonBox.ButtonRole.AcceptRole)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        buttonBox.rejected.connect(dialog.reject)

        vlayout.addWidget(buttonBox)
        dialog.setWindowTitle("Fill in information about this actuator target value")
        res = dialog.exec()

        if res:
            return ConfiguratorEntry(actuator_cb.currentText(),
                                     module_type=ModuleType.Actuator,
                                     setting=
                                     ParameterWithPath(
                                         parameter=
                                         Parameter.create(title= 'Actuator Value',
                                                          name='actuator_value',
                                                          type='float',
                                                          value=value_sb.value(),
                                                          suffix=suffix)))

    def remove_data(self, row):
        self.remove_row(row)

    def load(self, fname: str = None):
        if fname is None:
            fname = gutils.select_file(start_path=get_set_configurator_path(), save=False, ext='*')
        if fname is not None and fname != '':
            while self.rowCount(self.index(-1, -1)) > 0:
                self.remove_row(0)
            data = parameter_with_path_from_file(fname)

            for row in data:
                self.insert_data(self.rowCount(self.index(-1, -1)), row)

    def save(self, fname: str = None):
        if fname is None:
            fname = gutils.select_file(start_path=get_set_configurator_path(), save=True, ext='config',
                                       force_save_extension=True)
        with open(fname, 'wb') as file:
            file.writelines([ConfiguratorEntry.serialize(entry) for entry in self._data])



class ConfiguratorTableView(QtWidgets.QTableView):
    """
    """

    valueChanged = QtCore.Signal(list)
    add_data_signal = QtCore.Signal(int)
    remove_row_signal = QtCore.Signal(int)
    load_data_signal = QtCore.Signal()
    save_data_signal = QtCore.Signal()

    def __init__(self, menu=False):
        super().__init__()
        self.setmenu(menu)
        self.doubleClicked.connect(self.edit_row)

    def edit_row(self):
        index = self.currentIndex()
        index.model().edit_data(index)

    def setmenu(self, status):
        if status:
            self.menu = QtWidgets.QMenu()
            self.menu.addAction('Add Actuator Value', self.add)
            self.menu.addAction('Remove selected row', self.remove)
            self.menu.addAction('Clear all', self.clear)
            self.menu.addSeparator()
            self.menu.addAction('Load Configurator file', lambda: self.load_data_signal.emit())
            self.menu.addAction('Save Configurator file', lambda: self.save_data_signal.emit())
        else:
            self.menu = None

    def contextMenuEvent(self, event):
        if self.menu is not None:
            self.menu.exec(event.globalPos())

    def clear(self):
        self.model().clear()

    def add(self):
        self.add_data_signal.emit(self.currentIndex().row())

    def remove(self):
        self.remove_row_signal.emit(self.currentIndex().row())

    def data_has_changed(self, topleft, bottomright, roles):
        self.valueChanged.emit([topleft, bottomright, roles])

    def get_table_value(self):
        """

        """
        return self.model()

    def set_table_value(self, data_model):
        """

        """
        try:
            self.setModel(data_model)
            self.model().dataChanged.connect(self.data_has_changed)
        except Exception as e:
            pass



class ConfiguratorParameterTree(ParameterTree):
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
        module, module_type = get_module_from_param(param_with_path)
        if module is not None:
            entry = ConfiguratorEntry(module, module_type, param_with_path)
            data.setData('pymodaq/configurator_entry', ConfiguratorEntry.serialize(entry))
        return data



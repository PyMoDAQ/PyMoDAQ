from pathlib import Path
from typing import Union, Any

from qtpy import QtWidgets, QtCore

from qtpy.QtCore import QMimeData, Qt, QModelIndex
from qtpy.QtWidgets import QDialogButtonBox, QDialog
from pymodaq.utils.managers.configurator.subentries import SubEntryHandlerFactory, SubEntryHandlerTypes, \
    ConfiguratorSubEntry
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.enums import StrEnum
from pymodaq_utils.array_manipulation import are_elements_contiguous
from pymodaq_gui.parameter.utils import ParameterWithPath
from pymodaq_gui.parameter.ioxml import VALID_FOR_CONFIGURATION
from pymodaq_gui.qvariant import QVariant
from pymodaq_gui.parameter import ParameterTree, Parameter

from pymodaq_gui.utils.widgets.table import TableModel


from pymodaq_gui import utils as gutils

from serializall import SerializableFactory

from pymodaq.utils.config import get_set_configurator_path
from pymodaq.utils.managers.modules import ModuleType
import copy

logger = set_logger(get_module_name(__file__))
ser_factory = SerializableFactory()
special_entry_factory = SubEntryHandlerFactory()


class EntryActions(StrEnum):
    ADD = 'add_entry'
    REMOVE = 'remove_entry'
    UP = 'move_entry_up'
    DOWN = 'move_entry_down'


class ParameterDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self,  *args, **kwargs):
        super().__init__(*args, **kwargs)

    def createEditor(self, parent, option, index: QModelIndex):
        parameter: Parameter = index.model().get_data(index.row()).setting.parameter
        widget: QtWidgets.QWidget =  parameter.itemClass(parameter, depth=0).makeWidget()
        widget.setParent(parent)
        widget.setAutoFillBackground(True)

        # Set size policy to fill the cell
        widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding
        )

        # Force widget to fill cell height
        available_height = option.rect.height()
        widget.setMinimumHeight(available_height)
        widget.setMaximumHeight(available_height)

        # Remove layout margins if present
        if widget.layout() is not None:
            widget.layout().setContentsMargins(0, 0, 0, 0)
            widget.layout().setSpacing(0)

        # Connect signals for auto-commit on value change or focus loss
        self._connect_editor_signals(widget)

        return widget

    def _connect_editor_signals(self, widget):
        """Connect widget signals to auto-commit data changes"""
        # Try common value changed signals
        # if hasattr(widget, 'toggled'):
        #     widget.toggled.connect(lambda: self.commitData.emit(widget))
        # elif hasattr(widget, 'currentIndexChanged'):  # For comboboxes
        #     widget.currentIndexChanged.connect(lambda: self.commitData.emit(widget))
        # elif hasattr(widget, 'editingFinished'):
        #     widget.editingFinished.connect(lambda: self.commitData.emit(widget))
        # elif hasattr(widget, 'stateChanged'):  # For checkboxes
        #     widget.stateChanged.connect(lambda: self.commitData.emit(widget))
        # elif hasattr(widget, 'checkStateChanged'):  # For checkboxes
        #     widget.checkStateChanged.connect(lambda: self.commitData.emit(widget))
        #
        # # Install event filter to catch focus loss
        #widget.installEventFilter(self)
        pass

    def setEditorData(self, editor, index: QModelIndex):
        try:
            editor.setValue(index.data())
        except:
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index: QModelIndex):
        model.setData(index, copy.copy(editor.value()), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        """Ensure editor fills the cell completely"""
        rect = QtCore.QRect(option.rect)
        available_height = rect.height()
        editor.setMinimumHeight(available_height)
        editor.setMaximumHeight(available_height)
        editor.setGeometry(rect)

    def sizeHint(self, option, index):
        """Provide size hint for cells with widgets"""
        if index.column() == 2:
            hint = super().sizeHint(option, index)
            hint.setHeight(max(hint.height(), 40))
            return hint
        return super().sizeHint(option, index)

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


def config_subentries_from_path(fname: Path) -> list[ConfiguratorSubEntry]:
    if not fname.exists():
        return []
    with open(fname, 'rb') as file:
        lines = file.readlines()
    all_lines = b''
    for line in lines:
        all_lines += line
    data = []
    while len(all_lines) > 0:
        entry, all_lines = ConfiguratorSubEntry.deserialize(all_lines)
        data.append(entry)
    return data


mock_list = ['elt1', 'elt2', 'elt3']
mock_entry = ConfiguratorSubEntry('settings',
                               'Photodiode',
                                  ModuleType.Detector,
                                  ParameterWithPath(
                                   parameter=Parameter.create(title='mytitle', name='myname',
                                                              type='list', value=mock_list[0],
                                                              limits=mock_list)))



class ConfiguratorModel(TableModel):

    update_delegate = QtCore.Signal()

    def __init__(self, data: list[ConfiguratorSubEntry]=None,
                 header=('Type', 'Module', 'Title', 'Value'),
                 ):
        self._data: list[ConfiguratorSubEntry] = None
        if data is None:
            data = []
        super().__init__(data, header, editable=[False, False, False, True])
        pass

    def columnCount(self, parent):
        return 4

    def mimeTypes(self):
        types = super().mimeTypes()
        types.append('pymodaq/parameter_with_path')
        types.append('pymodaq/configurator_entry')
        return types

    def mimeData(self, items):
        data = QMimeData()
        rows = list(set([item.row() for item in items]))
        if are_elements_contiguous(rows):
            entries = [self._data[raw] for raw in rows]
            data.setData('pymodaq/configurator_entry', ser_factory.get_apply_serializer(entries))
        return data

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):
        if index.isValid():
            if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
                entry: ConfiguratorSubEntry = self._data[index.row()]
                if index.column() == 0:
                    dat = entry.entry_type.capitalize()
                elif index.column() == 1:
                    dat = entry.module_name
                elif index.column() == 2:
                    dat = entry.setting.parameter.title()
                elif index.column() == 3:
                    dat = f"{entry.setting.parameter.value()} {entry.setting.parameter.opts.get('suffix', '')}"
                else:
                    dat = ''
                return dat
            elif role == Qt.ItemDataRole.CheckStateRole and index.column() == 0 and self._show_checkbox:
                if self._checked[index.row()]:
                    return Qt.CheckState.Checked
                else:
                    return Qt.CheckState.Unchecked
            elif role == Qt.ItemDataRole.ToolTipRole:
                entry: ConfiguratorSubEntry = self._data[index.row()]
                return repr(entry)
        return QVariant()


    def dropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex):
        if row == -1:
            row = self.rowCount(parent)
        if data.hasFormat('pymodaq/configurator_entry'):
            entries: list[ConfiguratorSubEntry] = (
                ser_factory.get_apply_deserializer(
                    data.data('pymodaq/configurator_entry').data()))
        else:
            entries = [mock_entry]

        if action == QtCore.Qt.DropAction.MoveAction:
            pass
            # this is strange if I move things around using drag/drop
            # sometimes the MoveRows is called immediately without calling drop???
            # the code below is therefore not needed (but is still called in case of a drop!!)
            # for ind, entry in enumerate(entries):
            #     self.data_tmp = entry
            #     start_row = self._data.index(entry)
            #     #self.moveRows(start_row, len(entries))
            #     self.moveRow(parent, start_row, parent, row)
        elif action == QtCore.Qt.DropAction.CopyAction:  #but only one item in the list in Copy mode
            self.data_tmp = self.split_entry(entries[0])  # in case the entry has children parameters
            for entry in self.data_tmp:  #make sure there is no duplicate
                if entry in self._data:
                    self.data_tmp.remove(entry)
            self.insertRows(row, len(self.data_tmp), parent)
        self.update_delegate.emit()
        return True

    def setData(self, index, value, role):
        if index.isValid():
            if role == Qt.ItemDataRole.EditRole:
                if self.validate_data(index.row(), index.column(), value):
                    self._data[index.row()].setting.parameter.setValue(value)
                    self.dataChanged.emit(index, index, [role])
                    return True

                else:
                    return False
            elif role == Qt.ItemDataRole.CheckStateRole:
                self._checked[index.row()] = True if value == Qt.CheckState.Checked else False
                self.dataChanged.emit(index, index, [role])
                return True
        return False

    def split_entry(self, entry: ConfiguratorSubEntry,
                    entries: list[ConfiguratorSubEntry] = None) -> list[ConfiguratorSubEntry]:
        """ Split A ConfiguratorEntry into multiple entries if its underlying parameter has children"""
        if entries is None:
            entries = []
        if not entry.setting.parameter.hasChildren():
            if entry.setting.parameter.opts.get(VALID_FOR_CONFIGURATION, True):  # only add the ones specifying they are configurable
                entries.append(entry)
        else:
            for child in entry.setting.parameter.children():
                if child.opts.get(VALID_FOR_CONFIGURATION, True) :  # only add the ones specifying they are configurable
                    pwp = ParameterWithPath(parameter=child, path=entry.setting.path + [child.name()])
                    config_entry = ConfiguratorSubEntry(entry.entry_type, entry.module_name, entry.module_type, pwp)
                    self.split_entry(config_entry, entries)
        return entries

    def moveRow(self, sourceParent: QModelIndex, sourceRow: int,
                destinationParent: QModelIndex, destinationChild: int) -> bool:
        if (destinationChild > self.rowCount() or
                destinationChild < 0):
            return False
        self.beginMoveRows(sourceParent, sourceRow, sourceRow,
                           destinationParent, destinationChild)
        entry_to_be_moved = self._data.pop(sourceRow)
        self._data.insert(destinationChild if destinationChild < sourceRow else destinationChild -1,
                          entry_to_be_moved)
        self.endMoveRows()
        return True

    def moveRows(self, sourceParent: QModelIndex, sourceRow: int, count: int,
                 destinationParent: QModelIndex, destinationChild: int) -> bool:
        if count == 1:
            self.moveRow(sourceParent, sourceRow, destinationParent, destinationChild)
        else:
            super().moveRows(sourceParent, sourceRow, count,
                             destinationParent, destinationChild)

    def insertRows(self, row, count, parent):
        self.beginInsertRows(QtCore.QModelIndex(), row, row + count - 1)
        for ind in range(count):
            self._data.insert(row + ind, self.data_tmp[ind] if
            (hasattr(self.data_tmp, '__len__') and len(self.data_tmp) == count) else self.data_tmp)
            self._checked.insert(row + ind, False)
        self.endInsertRows()
        return True

    def clear(self):
        while self.rowCount() > 0:
            self.remove_row(0)

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

    def add_data(self, row, data: ConfiguratorSubEntry):
        if data is not None:
            if data in self._data:
                return
            self.insert_data(row, data)
            self.update_delegate.emit()

    def remove_data(self, row):
        self.remove_row(row)
        self.update_delegate.emit()

    def load(self, fname: Union[str, Path] = None):
        if fname is None:
            fname = gutils.select_file(start_path=get_set_configurator_path(), save=False, ext='*')
        if fname is not None and fname != '':
            while self.rowCount(self.index(-1, -1)) > 0:
                self.remove_row(0)
            data = config_subentries_from_path(Path(fname))

            for row in data:
                self.insert_data(self.rowCount(self.index(-1, -1)), row)
        self.update_delegate.emit()

    def save(self, fname: str = None):
        if fname is None:
            fname = gutils.select_file(start_path=get_set_configurator_path(), save=True, ext='config',
                                       force_save_extension=True)
        with open(fname, 'wb') as file:
            file.writelines([ConfiguratorSubEntry.serialize(entry) for entry in self._data])


class ConfiguratorTableView(QtWidgets.QTableView):
    """
    """

    valueChanged = QtCore.Signal(list)
    add_data_signal = QtCore.Signal(str)
    remove_row_signal = QtCore.Signal(int)
    load_data_signal = QtCore.Signal()
    save_data_signal = QtCore.Signal()

    def __init__(self, menu=False):
        super().__init__()
        self.setmenu(menu)
        #self.doubleClicked.connect(self.edit_row)

    def edit_row(self):
        index = self.currentIndex()
        index.model().edit_data(index)

    def setmenu(self, status):
        if status:
            self.menu = QtWidgets.QMenu()
            special_menu = self.menu.addMenu('Add Special Configuration')

            for entry in special_entry_factory.entries:
                special_entry = special_entry_factory.get_subentry_handler(entry)
                if special_entry.use_dialog:
                    special_menu.addAction(entry.capitalize(),
                                           self.create_menu_slot_special_entry(entry))

            self.menu.addSeparator()
            self.menu.addAction('Remove selected row', self.remove)
            self.menu.addAction('Clear all', self.clear)
            self.menu.addSeparator()
            self.menu.addAction('Load Configurator file', lambda: self.load_data_signal.emit())
            self.menu.addAction('Save Configurator file', lambda: self.save_data_signal.emit())
        else:
            self.menu = None

    def create_menu_slot_special_entry(self, entry: str):
        return lambda: self.add(entry)

    def contextMenuEvent(self, event):
        if self.menu is not None:
            self.menu.exec(event.globalPos())

    def clear(self):
        self.model().clear()

    def add(self, special_entry: str):
        self.add_data_signal.emit(special_entry)

    def remove(self):
        """ Remove selected rows, starting from the last one (to not mess with indexing)"""
        rows = list(set([index.row() for index in self.selectedIndexes()]))
        rows.sort(key=lambda row: -row)
        for row in rows:
            self.remove_row_signal.emit(row)

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
        try:
            module, module_type = get_module_from_param(param_with_path)
        except KeyError:
            module = ModuleType.NONE.value
            module_type = ModuleType.NONE
        if module is not None:
            entry = ConfiguratorSubEntry(SubEntryHandlerTypes.SETTINGS,
                                         module, module_type, param_with_path)
            data.setData('pymodaq/configurator_entry',
                         ser_factory.get_apply_serializer([entry]))
        return data

import sys
from pathlib import Path
from typing import Any, Union, TYPE_CHECKING, Optional

from qtpy.QtCore import Qt, QModelIndex
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtGui import QKeySequence

from pymodaq_gui.utils.styling import create_icon

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq.extensions.custom_ext import CustomExt
from pymodaq_gui.managers.action_manager import addwidget
from pymodaq_utils.enums import StrEnum

from pymodaq_gui.messenger import dialog
from pymodaq_gui.qt_utils import center_widget_on_screen_and_show, mkQApp
from pymodaq_gui.utils.splash import get_pymodaq_pixmap
from pymodaq_gui.utils.widgets.combo import ComboBox

from pymodaq_gui.utils.widget_sync import WidgetSync, SyncMode


logger = set_logger(get_module_name(__file__))


if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard


class ManagerActions(StrEnum):
    OPEN = 'open_manager'
    COPY = 'copy_entry'
    NEW = 'create_new_entry'
    DELETE = 'delete_entry'
    SAVE = 'save_entry'
    RELOAD = 'reload_entry'
    EXECUTE = 'execute_entry'
    LIST = 'list_entries'
    LABEL_EXTERNAL = 'label_external'
    LIST_EXTERNAL = 'list_entries_external'


class Toolbar(StrEnum):
    MAIN = 'main'
    EXTERNAL = 'external'


class Menu(StrEnum):
    MAIN = 'main'
    EXTERNAL = 'external'


class ManagerSubEntriesModel(QtCore.QAbstractListModel):

    def __init__(self, entries: list[str]):
        super().__init__()
        self._data = entries
        self.colors: list[QtCore.Qt.GlobalColor] = [QtCore.Qt.GlobalColor.darkGray for _ in range(len(self._data))]
        self.status: list[Union[bool, None]] = [None for _ in range(len(self._data))]

    def set_status(self, index: int, status: bool):
        self.status[index] = status
        if status:
            self.colors[index] = QtCore.Qt.GlobalColor.darkGreen
        else:
            self.colors[index] = QtCore.Qt.GlobalColor.darkRed
        model_index = self.index(index, 0)
        self.dataChanged.emit(model_index, model_index,
                              [Qt.ItemDataRole.DecorationRole,
                              Qt.ItemDataRole.BackgroundColorRole])

    def rowCount(self, *args, **kwargs) -> int:
        return len(self._data)

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):
        if index.isValid():
            if role == Qt.ItemDataRole.DisplayRole:
                return str(self._data[index.row()])
            elif role == Qt.ItemDataRole.DecorationRole:
                if self.status[index.row()] is None:
                    return create_icon('yellow_light')
                elif self.status[index.row()]:
                    return create_icon('greenLight2')
                else:
                    return create_icon('red_light')
            elif role == Qt.ItemDataRole.FontRole:
                return QtGui.QFont('Arial', 10)
            elif role == Qt.ItemDataRole.ForegroundRole:
                if self.status[index.row()] is None:
                    return QtGui.QBrush(QtCore.Qt.GlobalColor.darkGray)
                elif self.status[index.row()]:
                    return QtGui.QBrush(QtCore.Qt.GlobalColor.darkGreen)
                else:
                    return QtGui.QBrush(QtCore.Qt.GlobalColor.darkRed)
            elif role == Qt.ItemDataRole.BackgroundColorRole:
                return Qt.BrushStyle.NoBrush



class ManagerBase(CustomExt):

    new_entry = QtCore.Signal(str)
    applied_entry = QtCore.Signal(str)
    deleted_entry = QtCore.Signal(str)
    updated_entry = QtCore.Signal(str)

    entry_type: str
    entry_extension: str

    execute_action_checkable = False

    def __init__(self,
                 dashboard: 'DashBoard' = None,
                 **kwargs):

        super().__init__(parent=QtWidgets.QMainWindow(), dashboard=dashboard, **kwargs)

        self._entry_applied = False
        self._applied_entry_name: str = None

        self.main_widget = QtWidgets.QWidget()
        self.mainwindow.setCentralWidget(self.main_widget)
        self._entry_slots = {}

        self.splash_subentries: Optional[SubEntriesSplash] = None
        self.subentries_model: Optional[ManagerSubEntriesModel] = None

        #first create the object
        self.entries_sync = WidgetSync(
            initial_value={
                'items': [],
                'current': None,
                'enabled': False
        })

        self.setup_ui()
        self.enable_actions(False)
        # then update it using a call to self.entries (itself needing entries_sync)
        self.entries_sync.update_key('items', self.entries)
        self.entries_sync.update_key('current', 'default')

        self.update_action_list()
        self.update_execute_action_tooltip(self.entry)

    def enable_actions(self, enable=True):
        self.entries_sync.update_key('enabled', enable)
        for action in self.actions_names:
            self.set_action_enabled(action, enable)

    @staticmethod
    def format_subentries(entries: list[Any]):
        """ Should be reimplemented for better display than the repr one """
        return [str(entry) for entry in entries]

    def show_subentries(self, subentries: list[Any], title=''):
        self.splash_subentries = SubEntriesSplash(title=title)
        self.subentries_model = ManagerSubEntriesModel(self.format_subentries(subentries))
        self.splash_subentries.setModel(self.subentries_model)
        self.splash_subentries.show_splash()

    def close_subentries_display(self, after_ms=1000):
        if self.splash_subentries is not None:
            QtCore.QTimer.singleShot(after_ms, self.splash_subentries.close)

    @property
    def manager_name(self) -> str:
        return self.__class__.__name__

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        """Get the folder path where the managed entries are stored."""
        raise NotImplementedError

    def setup_ui(self):
        self.setup_docks()
        self.setup_actions_base()
        self.setup_actions()

        try:
            self.setup_menu(self._menubar)
        except TypeError:
            self.setup_menu()  # for backcompatibility

        self.connect_things_base()
        self.connect_things()

        self.do_things_after_ui_setup()

    @property
    def entry(self) -> str:
        """ Get/Set the name of the current entry """
        return self.get_action_list().currentText()

    @entry.setter
    def entry(self, entry_name: str):
        self.get_action_list().setCurrentText(entry_name)

    @property
    def entry_filepath(self) -> Path:
        """ Get the full path of the current entry file """
        kwargs_to_entry_folder = {}  # reimplement if needed
        return self.get_entry_folder(**kwargs_to_entry_folder).joinpath(
            self.entry + self.entry_extension)

    def entry_path_from_name(self, entry_name: str) -> Path:
        kwargs_to_entry_folder = {}  # reimplement if needed
        return self.get_entry_folder(**kwargs_to_entry_folder).joinpath(
            entry_name + self.entry_extension)

    @property
    def entries(self) -> list[str]:
        """ Get the name of all existing entries """
        return self.list_managed_entries()

    @property
    def entries_filepath(self) -> list[Path]:
        """ Get the full path of all entries file """
        return self.list_managed_entries_path()

    def list_managed_entries(self, **kwargs_to_entry_folder) -> list[str]:
        """Returns a list of names of managed entries with 'default' as first """
        entries = [path.stem for path in self.list_managed_entries_path(**kwargs_to_entry_folder)]
        entries.remove('default')
        entries = ['default'] + entries  # always shows default as first
        return entries

    def list_managed_entries_path(self, **kwargs_to_entry_folder) -> list[Path]:
        """Should return a list of Path objects representing managed entries.

        Example:
        --------
        [path for path in get_set_preset_path().iterdir() if path.suffix == self.entry_extension]
        """
        entry_path = self.get_entry_folder(**kwargs_to_entry_folder)
        if not entry_path.exists():
            entry_path.mkdir(parents=True)
        if not entry_path.joinpath(f'default{self.entry_extension}').exists():
            self.create_entry('default', bypass_dialog=True)
        return [path for path in entry_path.iterdir() if path.suffix == self.entry_extension]

    def setup_docks(self):
        """Sets up the widgets for the manager.

        Eventually, this can be reimplemented in subclasses to add more/different widgets/docks...
        """
        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addWidget(self.settings_tree)
        self.main_widget.setLayout(vlayout)

    def get_action_list(self) -> ComboBox:
        """ Convenience method to get right return type """
        return self.get_action(ManagerActions.LIST).widget

    def get_action_from_file(self, file: Path) -> str:
        """ Get an action name given a file and the manager name"""
        return f"{file.stem}_{self.manager_name}"

    def setup_actions_base(self):

        # ACTIONS in Manager
        self.add_widget('entry_label', QtWidgets.QLabel(
            f'{self.entry_type.capitalize()}:'))
        self.add_widget(ManagerActions.LIST, ComboBox(),
                        tip=f'Name of the current {self.entry_type}',
                        kwargs={'setReadOnly': True})
        self.get_action_list().addItems(self.entries)

        self.add_action(ManagerActions.COPY, f'Copy {self.entry_type.capitalize()}',
                        'file_copy')
        self.add_action(ManagerActions.NEW,
                        f'New {self.entry_type.capitalize()}', 'add_circle',
                        tip=f'Create a new {self.entry_type} file ("Ctrl+N")',
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_N),
                        icon_color=self.get_theme().green,)
        self.add_action(ManagerActions.DELETE,
                        f'Delete {self.entry_type.capitalize()}', 'do_not_disturb_on',
                        icon_color=self.get_theme().red,
                        tip=f'Delete the current {self.entry_type.capitalize()} ("Ctrl+Delete")',
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Delete))
        self.add_action(ManagerActions.SAVE,
                        f'Save {self.entry_type.capitalize()}', 'save_as',
                        icon_color=self.get_theme().blue,
                        tip=f'Save/Update the current {self.entry_type.capitalize()} ("Ctrl+S")',
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_S))
        self.add_action(ManagerActions.RELOAD,
                        f'Reload {self.entry_type.capitalize()}', 'refresh',
                        tip=f'Reload the current {self.entry_type} file ("Ctrl+Shift+R")',
                        icon_color=self.get_theme().orange,
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_R))
        self.add_action(ManagerActions.EXECUTE,
                        f'Execute {self.entry_type.capitalize()}', 'start',
                        icon_color=self.get_theme().magenta,
                        checkable=self.execute_action_checkable,
                        icon_checked_color=QtGui.QColor(255, 0, 201),
                        tip=f'Execute the current {self.entry_type} file ("Ctrl+Shift+E")',
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_E))
        self.add_action(ManagerActions.OPEN, f"{self.entry_type.capitalize()} Manager",
                        "build_circle",
                        icon_color=self.get_theme().blue,
                        tip=f'Open the {self.entry_type.capitalize()} Manager',
                        checkable=True,
                        icon_checked_color=self.get_theme().cyan,
                        auto_toolbar=False, auto_menu=False)

    def get_external_toolbar_menu(
            self, toolbar: QtWidgets.QToolBar = None,
            menu: QtWidgets.QMenu = None) -> tuple[QtWidgets.QToolBar, QtWidgets.QMenu]:
        """ Create or update a toolbar and a menu containing actions to open/set/execute the manager """
        if toolbar is None:
            toolbar = QtWidgets.QToolBar(f'{self.entry_type.capitalize()}')
        if menu is None:
            menu = QtWidgets.QMenu(f'{self.entry_type.capitalize()}')

        self.add_widget(ManagerActions.LABEL_EXTERNAL, QtWidgets.QLabel(f'{self.entry_type.capitalize()}:'),
                        toolbar=toolbar,)
        self.affect_to(ManagerActions.OPEN, toolbar)
        self.affect_to(ManagerActions.OPEN, menu)

        self.add_widget(ManagerActions.LIST_EXTERNAL, ComboBox(), toolbar=toolbar)
        self.sync_entries_with(self.get_action(ManagerActions.LIST_EXTERNAL).widget)
        self.affect_to(ManagerActions.EXECUTE, toolbar)
        return toolbar, menu

    def connect_things_base(self):
        self.connect_action(ManagerActions.COPY, lambda: self.copy_entry())
        self.connect_action(ManagerActions.NEW, lambda: self.create_entry())
        self.connect_action(ManagerActions.DELETE, lambda: self.delete_entry())
        self.connect_action(ManagerActions.SAVE, lambda: self.save_check())
        self.connect_action(ManagerActions.RELOAD, lambda: self.update_entry())
        self.connect_action(ManagerActions.EXECUTE, lambda: self.execute_entry())

        self.connect_action(ManagerActions.OPEN, lambda: self.show())

        self.entries_sync.value_changed.connect(lambda value: self.update_entry(value['current']))
        self.sync_entries_with(self.get_action_list())

    def sync_entries_with(self, combo: ComboBox):
        self.entries_sync.bind_properties(
            combo,
            property_map={
                'items': {
                    'signal': combo.items_changed,  
                    'getter': combo.get_items,
                    'setter': combo.set_items,
                    'mode': SyncMode.BIDIRECTIONAL
                },
                'current': {
                    'signal': combo.currentTextChanged,
                    'getter': combo.currentText,
                    'setter': combo.setCurrentText,
                    'mode': SyncMode.BIDIRECTIONAL
                },
                'enabled': {
                    'signal': combo.enabled_changed,
                    'getter': combo.isEnabled,
                    'setter': combo.setEnabled,
                    'mode': SyncMode.BIDIRECTIONAL
                }
            }
        )

    def create_entry(self, entry: str = None, bypass_dialog=False):
        if entry is not None:
            ok = True
        else:
            entry, ok = QtWidgets.QInputDialog.getText(
                None,
                f'Enter a NEW {self.entry_type.capitalize()} name',
                f'{self.entry_type.capitalize()} name:', QtWidgets.QLineEdit.Normal)
        self.do_things_for_new_creation()
        if ok and entry != '':
            if self.save_check(entry, bypass_dialog=bypass_dialog):
                self.entries_sync.append_to_list('items', entry)
                self.entries_sync.update_key('current', entry)
                self.update_action_list()
                self.new_entry.emit(entry)

    def do_things_for_new_creation(self):
        """ To be reimplemented if needed """
        pass

    def save_check(self, entry: str = None, bypass_dialog=False) -> bool:
        if entry is not None:
            entry_path = self.get_entry_folder().joinpath(entry+self.entry_extension)
        else:
            entry_path = self.entry_filepath
        if entry_path.exists():
            if not bypass_dialog:
                user_agreed = dialog(
                    title='Overwrite confirmation',
                    message='File exist do you want to overwrite it ?',
                )
                if not user_agreed:
                    return False
        self.save_entries(entry_path)
        return True

    def save_entries(self, entry_path: Path = None):
        """ Particular implementation to save entries for this inherited Manager """
        raise NotImplementedError

    def copy_entry(self, entry: str = None, bypass_dialog=False):
        if entry is None:
            entry, ok = QtWidgets.QInputDialog.getText(
                None, f'Enter a NEW {self.entry_type.capitalize()} name',
                f'{self.entry_type.capitalize()} name:', QtWidgets.QLineEdit.Normal)
            if not ok or entry == '':
                return

        if self.save_check(entry, bypass_dialog=bypass_dialog):
            self.entries_sync.append_to_list('items', entry)
            self.entries_sync.update_key('current', entry)
            self.update_action_list()
            self.new_entry.emit(entry)

    def delete_entry(self, entry: str = None, bypass_dialog=False):
        if entry is None:
            entry = self.entry
        else:
            self.entry = entry
        if bypass_dialog:
            user_agreed = True
        else:
            user_agreed = dialog(
                title='Delete confirmation',
                message=f'Are you sure you want to delete the {self.entry_type.capitalize()}'
                        f' {entry} ?',
            )
        if user_agreed:
            entries = self.entries[:]  # to get before unlinking

            self.entry_filepath.unlink(missing_ok=True)
            logger.info(f'{self.entry_type.capitalize()} file {self.entry} deleted')

            index = entries.index(entry)
            entries.pop(index)
            if len(entries) != 0:
                current = entries[max(0, index - 1)]
            else: # should trigger the default entry creation!
                entries = self.entries  # this recreate default
                current = entries[0]
            self.entries_sync.set_value({'items': entries,
                                        'current': current})  # deleting will update current and fire update_entry_base
            self.deleted_entry.emit(entry)  # notify that an entry has been deleted


    @property
    def entry_applied(self) -> bool:
        """ Get the status of the execution of the last applied entry

        If True, the :attr:`applied_entry_name` property will reflect the last successfully applied/executed entry
        """
        return self._entry_applied

    @entry_applied.setter
    def entry_applied(self, applied: bool):
        self._entry_applied = applied
        if applied:
            self._applied_entry_name = self.entry
            self.applied_entry.emit(self._applied_entry_name)

    @property
    def applied_entry_name(self) -> str | None:
        """ Get the name of the last entry that has been successfully applied/executed """
        return self._applied_entry_name

    def execute_entry(self, entry_path: Path = None, **kwargs):
        """ To be called to execute the selected entry """
        if entry_path is None:
            self.save_check(self.entry, bypass_dialog=True)
            entry_path = self.entry_filepath

        self.update_entry(entry_path.stem)

        if self.dashboard is None:
            logger.info(f"Cannot Load {self.entry_type.capitalize()} file: {entry_path.stem} as no Dashboard is initialized")
            return

        self.entry_applied = self._execute_entry(entry_path, **kwargs)

    def _execute_entry(self, entry_path: Path = None, **kwargs) -> bool:
        """Particular implementation of the entry execution for this manager

        Applies the entry from the given file in the manager.

        Should not be called directly, use :attr:`execute_entry` instead.

        To be reimplemented

        Parameters:
        -----------
        file : Path
            The path to the configuration file to be applied.
        """

        checked = self.is_action_checked(ManagerActions.EXECUTE)
        # you may want to use the checked state of this action in your implementation
        # Checkable EXECUTE action is optional and dependant if the class attribute
        # execute_action_checkable is set to True
        return False

    def update_entry(self, entry: Union[str, Path] = None, **kwargs):
        """ Update the table given the entry argument"""
        if entry is None:
            entry = self.entry_filepath

        if isinstance(entry, str):
            self.entry = entry  # make sure the current entry field reflects this method argument
            entry = self.get_entry_folder(**kwargs).joinpath(f'{entry}{self.entry_extension}')

        self.entry = entry.stem  # make sure the combo is updated (if triggered not from the combo, in particular the action slots)

        self._update_entry(entry)
        self.update_execute_action_tooltip(entry.stem)
        self.updated_entry.emit(entry.stem)

    def _update_entry(self, entry_path: Path):
        """ Particular implementation to update entries for this inherited Manager """
        raise NotImplementedError

    def show(self):
        if self.is_action_checked(ManagerActions.OPEN):
            self.mainwindow.show()
            self.mainwindow.raise_()
        else:
            self.mainwindow.hide()

    def update_action_list(self):
        with QtCore.QSignalBlocker(self.get_action_list()) as blocker:
            try:
                for ind_file, file in enumerate(self.list_managed_entries_path()):
                    if not self.has_action(self.get_action_from_file(file)):
                        self.add_action(
                            self.get_action_from_file(file),
                            file.stem,
                            "",
                            f"Load the {file.stem} entry",
                            auto_toolbar=False,
                        )
                self.update_actions_connection()
                self.update_menu()
            except KeyError as e:
                pass

    def update_actions_connection(self):
        for ind_file, file in enumerate(self.list_managed_entries_path()):
            self.connect_action(self.get_action_from_file(file), connect=False)
            self._entry_slots[file.stem] = self.create_slot_from_file(
                    self.get_entry_folder().joinpath(file.stem + self.entry_extension))
            self.connect_action(self.get_action_from_file(file),
                                self._entry_slots[file.stem])

    def update_execute_action_tooltip(self, entry: str):
        self.get_action(ManagerActions.EXECUTE).setToolTip(
            f'Execute the selected {self.entry_type} entry: {entry} ("Ctrl+A")')

    def create_slot_from_file(self, filename: Path):
        return lambda: self.execute_entry(filename)

    def update_menu(self, menu: QtWidgets.QMenu = None):
        try:
            if menu is None:
                menu = self.get_menu(Menu.EXTERNAL)
            self.update_action_list()
            menu.clear()
            menu.addAction(self.get_action(ManagerActions.OPEN))
            menu.addSeparator()
            load_menu = menu.addMenu(f"Load {self.entry_type.capitalize()}s")

            entries_path = self.list_managed_entries_path()
            entries_path.sort(key=lambda x: x.stem)
            default_index = [entry.stem for entry in entries_path].index('default')
            default_path = entries_path.pop(default_index)
            entries_path = [default_path] + entries_path

            for ind_file, file in enumerate(entries_path):
                if self.has_action(self.get_action_from_file(file)):
                    load_menu.addAction(self.get_action(
                        self.get_action_from_file(file)
                    )
                    )
        except AttributeError:  # means self.menu is not yet defined
            pass


class ListView(QtWidgets.QListView):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)


class SubEntriesSplash(QtWidgets.QLabel):

    def __init__(self, parent=None, title=''):
        super().__init__(parent)
        self.list_view = ListView()
        self.title_label = QtWidgets.QLabel(title)

    def mousePressEvent(self, event):
        self.close()

    def setModel(self, model):
        self.list_view.setModel(model)

    def show_splash(self):

        self.setPixmap(get_pymodaq_pixmap())

        self.list_view.viewport().setAutoFillBackground(False)
        self.list_view.setStyleSheet("QListView { outline: none; }")
        self.list_view.clearFocus()

        self.title_label.setFont(QtGui.QFont("Arial", 12))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)

        vlayout = QtWidgets.QVBoxLayout()
        hlayout = QtWidgets.QHBoxLayout()
        self.setLayout(hlayout)
        hlayout.addStretch(10)
        hlayout.addLayout(vlayout)
        vlayout.addWidget(self.title_label)
        vlayout.addWidget(self.list_view)
        vlayout.addStretch(10)

        center_widget_on_screen_and_show(self)
        self.raise_()


if __name__ == '__main__':
    import numpy as np


    # Create application and main window
    app = mkQApp('Dashboard')

    entries = [f'Module {ind:03.0f} si about to do something incredible' for ind in range(10)]

    widget = SubEntriesSplash()

    entry_sublist_model = ManagerSubEntriesModel(entries)
    widget.setModel(entry_sublist_model)


    def execute_entries(sublist: list[str]):
        for ind in range(len(sublist)):
            entry_sublist_model.set_status(ind, bool(np.random.randint(2)))
            QtWidgets.QApplication.processEvents()
            QtCore.QThread.msleep(200)
        QtCore.QThread.msleep(2000)
        #widget.close()

    widget.show_splash()
    execute_entries(entries)
    sys.exit(app.exec())
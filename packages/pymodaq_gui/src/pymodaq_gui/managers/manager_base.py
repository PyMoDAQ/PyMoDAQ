import sys
from pathlib import Path
from typing import Any, Union, TYPE_CHECKING, Optional

from qtpy.QtCore import Qt, QModelIndex
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtGui import QKeySequence

from pymodaq_gui.managers.action_manager import create_icon

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq.extensions.utils import CustomExt
from pymodaq_utils.enums import StrEnum

from pymodaq_gui.messenger import dialog
from pymodaq_gui.qt_utils import center_widget_on_screen_and_show
from pymodaq_gui.utils.splash import get_pymodaq_pixmap

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

    def __init__(self,
                 dashboard: 'DashBoard' = None,
                 menu: QtWidgets.QMenu = None,
                 toolbar: QtWidgets.QToolBar = None,
                 **kwargs):

        super().__init__(parent=QtWidgets.QMainWindow(), dashboard=dashboard, **kwargs)

        self.main_widget = QtWidgets.QWidget()
        self.mainwindow.setCentralWidget(self.main_widget)

        self.splash_subentries: Optional[SubEntriesSplash] = None
        self.subentries_model: Optional[ManagerSubEntriesModel] = None

        self.reference_toolbar(Toolbar.EXTERNAL, toolbar)
        self.reference_menu(Menu.EXTERNAL, menu)

        self.entries_sync = WidgetSync(
            initial_value={
            'items': self.entries,
            'current': self.entries[0]
        })

        self.setup_ui()

        self.update_action_list()
        self.update_execute_action_tooltip(self.entry)

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

    def update_entry(self, entry_path: Path):
        """ Particular implementation to update entries for this inherited Manager """
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
    def entry(self, preset_name: str):
        self.update_entry_base(preset_name)

    @property
    def entry_filename(self) -> Path:
        """ Get the full path of the current entry file """
        kwargs_to_entry_folder = {}  # reimplement if needed
        return self.get_entry_folder(**kwargs_to_entry_folder).joinpath(
            self.entry + self.entry_extension)

    @property
    def entries(self) -> list[str]:
        """ Get the name of all existing entries """
        return self.list_managed_entries()

    @property
    def entries_filename(self) -> list[Path]:
        """ Get the full path of all entries file """
        return self.list_managed_entries_path()

    def list_managed_entries(self, **kwargs_to_entry_folder) -> list[str]:
        """Returns a list of names of managed entries with 'default' as first """
        entries = [path.stem for path in self.list_managed_entries_path(**kwargs_to_entry_folder)]
        if 'default' in entries:  #  make sure the default is the first one shown
            default = entries.pop(entries.index('default'))
            entries.insert(0, default)
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

    def get_action_list(self) -> QtWidgets.QComboBox:
        """ Convenience method to get right return type """
        return self.get_action(ManagerActions.LIST)

    def get_action_list_external(self) -> QtWidgets.QComboBox:
        """ Convenience method to get right return type """
        return self.get_action(ManagerActions.LIST_EXTERNAL)

    def get_action_from_file(self, file: Path) -> str:
        """ Get an action name given a file and the manager name"""
        return f"{file.stem}_{self.manager_name}"

    def setup_actions_base(self):

        # ACTIONS in Manager
        self.add_widget('entry_label', QtWidgets.QLabel(
            f'Configuration from {self.entry_type.capitalize()}:'))
        self.add_widget(ManagerActions.LIST, QtWidgets.QComboBox(),
                        tip=f'Name of the current {self.entry_type}',
                        kwargs={'setReadOnly': True})
        self.get_action_list().addItems(self.entries)

        self.add_action(ManagerActions.COPY, f'Copy {self.entry_type.capitalize()}', 'EditCopy')
        self.add_action(ManagerActions.NEW,
                        f'New {self.entry_type.capitalize()}', 'ListAdd',
                        tip=f'Create a new {self.entry_type} file ("Ctrl+N")',
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_N))
        self.add_action(ManagerActions.DELETE,
                        f'Delete {self.entry_type.capitalize()}', 'ListRemove',
                        tip=f'Delete the current {self.entry_type.capitalize()} ("Ctrl+Delete")',
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Delete))
        self.add_action(ManagerActions.SAVE,
                        f'Save {self.entry_type.capitalize()}', 'DocumentSave',
                        tip=f'Save/Update the current {self.entry_type.capitalize()} ("Ctrl+S")',
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_S))
        self.add_action(ManagerActions.RELOAD,
                        f'Reload {self.entry_type.capitalize()}', 'ViewRefresh',
                        tip=f'Reload the current {self.entry_type} file ("Ctrl+R")',
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_R))
        self.add_action(ManagerActions.EXECUTE,
                        f'Execute {self.entry_type.capitalize()}', 'MailSend',
                        tip=f'Execute the current {self.entry_type} file ("Ctrl+E")',
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_E))


        # ACTIONS external: Dashboard, ...

        self.add_action(ManagerActions.OPEN, f"{self.entry_type.capitalize()} Manager", "DocumentProperties",
                        f'Open the {self.entry_type.capitalize()} Manager',
                        toolbar=Toolbar.EXTERNAL, menu=Menu.EXTERNAL)

        self.add_widget('external_label', QtWidgets.QLabel(f'{self.entry_type.capitalize()}:'),
                        toolbar=Toolbar.EXTERNAL)
        self.add_widget(ManagerActions.LIST_EXTERNAL, QtWidgets.QComboBox,
                        toolbar=Toolbar.EXTERNAL)
        self.affect_to(ManagerActions.EXECUTE, self.get_toolbar(Toolbar.EXTERNAL))

    def connect_things_base(self):
        self.connect_action(ManagerActions.LIST, self.update_entry_base,
                            signal_name='currentTextChanged')
        self.connect_action(ManagerActions.COPY, lambda: self.copy_entry())
        self.connect_action(ManagerActions.NEW, lambda: self.create_entry())
        self.connect_action(ManagerActions.DELETE, lambda: self.delete_entry())
        self.connect_action(ManagerActions.SAVE, lambda: self.save_check())
        self.connect_action(ManagerActions.RELOAD, lambda: self.update_entry_base())
        self.connect_action(ManagerActions.EXECUTE, lambda: self.execute_entry_base())

        self.connect_action(ManagerActions.OPEN, lambda: self.show())

        for combo in (self.get_action(ManagerActions.LIST), self.get_action(ManagerActions.LIST_EXTERNAL)):
            self.entries_sync.bind_properties(
                combo,
                property_map={
                    'items': {
                        'signal': None,  # FROM_SYNC only
                        'getter': lambda c=combo: [c.itemText(i) for i in range(c.count())],
                        'setter': lambda items, c=combo: (c.clear(), c.addItems(items)),
                        'mode': SyncMode.FROM_SYNC
                    },
                    'current': {
                        'signal': combo.currentTextChanged,
                        'getter': lambda c=combo: c.currentText(),
                        'setter': lambda text, c=combo: c.setCurrentText(text),
                        'mode': SyncMode.BIDIRECTIONAL
                    }
                }
            )

        # self.get_action_list_external().currentTextChanged.connect(self.get_action_list().setCurrentText)
        #
        # self.get_action_list().setCurrentText('default')

    def create_entry(self, entry: str = None, bypass_dialog=False):
        if entry is not None:
            ok = True
        else:
            entry, ok = QtWidgets.QInputDialog.getText(
                None,
                f'Enter a NEW {self.entry_type.capitalize()} name',
                f'{self.entry_type.capitalize()} name:', QtWidgets.QLineEdit.Normal)
        if ok and entry != '':
            entries = [self.get_action_list().itemText(ind).lower() for
                       ind in range(self.get_action_list().count())]
            if entry.lower() not in entries:
                entries.append(entry.lower())
                entries.sort()
                index = entries.index(entry.lower())
                self.get_action_list().insertItem(index-1, entry)

            self.get_action_list().setCurrentText(entry)
            self.save_check(bypass_dialog=bypass_dialog)
            self.update_action_list()
            self.new_entry.emit(entry)

    def save_check(self, entry: str = None, bypass_dialog=False):
        if entry is not None:
            entry_path = self.get_entry_folder().joinpath(entry+self.entry_extension)
        else:
            entry_path = self.entry_filename
        if entry_path.exists():
            if not bypass_dialog:
                user_agreed = dialog(
                    title='Overwrite confirmation',
                    message='File exist do you want to overwrite it ?',
                )
                if not user_agreed:
                    return
        self.save_entries(entry_path)

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

        self.save_check(entry, bypass_dialog=bypass_dialog)
        entries = [self.get_action_list().itemText(ind).lower() for
                   ind in range(self.get_action_list().count())]
        if entry.lower() not in entries:
            entries.append(entry.lower())
            entries.sort()
            index = entries.index(entry.lower())
            self.get_action_list().insertItem(index-1, entry)

        self.get_action_list().setCurrentText(entry)

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
            self.connect_action(ManagerActions.LIST, signal_name='currentTextChanged', connect=False)
            self.entry_filename.unlink(missing_ok=True)

            logger.info(f'{self.entry_type.capitalize()} file {self.entry} deleted')
            self.get_action_list().removeItem(
                self.get_action_list().currentIndex()
            )
            self.connect_action(ManagerActions.LIST, self.update_entry_base, signal_name='currentTextChanged')
            # self.update_action_list()
            self.deleted_entry.emit(entry)  # notify that an entry has been deleted
            self.update_entry_base(self.get_action_list().currentText())

    def execute_entry_base(self, entry_path: Path = None, **kwargs):
        if entry_path is None:
            self.save_check(self.entry, bypass_dialog=True)
            entry_path = self.entry_filename

        if self.dashboard is None:
            logger.info(f"Cannot Load {self.entry_type.capitalize()} file: {entry_path.stem} as no Dashboard is initialized")
            return

        self.execute_entry(entry_path, **kwargs)
        self.applied_entry.emit(entry_path.stem)

    def execute_entry(self, entry_path: Path = None, **kwargs):
        """Applies the entry from the given file in the manager.

        Parameters:
        -----------
        file : Path
            The path to the configuration file to be applied.
        """
        raise NotImplementedError

    def update_entry_base(self, entry: Union[str, Path] = None, **kwargs):
        if entry is None:
            entry = self.entry_filename

        if isinstance(entry, str):
            entry = self.get_entry_folder(**kwargs).joinpath(f'{entry}{self.entry_extension}')

        self.update_entry(entry)

        self.get_action_list().setCurrentText(entry.stem)
        self.update_execute_action_tooltip(entry.stem)
        self.get_action_list_external().setCurrentText(entry.stem)
        self.updated_entry.emit(entry.stem)

    def show(self):
        self.mainwindow.show()
        self.mainwindow.raise_()

    def update_action_list(self):
        with QtCore.QSignalBlocker(self.get_action_list()) as blocker:
            with QtCore.QSignalBlocker(self.get_action(ManagerActions.LIST)):
                try:
                    entries = []
                    self.get_action_list_external().clear()
                    for ind_file, file in enumerate(self.list_managed_entries_path()):
                        if not self.has_action(self.get_action_from_file(file)):
                            self.add_action(
                                self.get_action_from_file(file),
                                file.stem,
                                "",
                                f"Load the {file.stem} entry",
                                auto_toolbar=False,
                            )
                        entries.append(file.stem)
                    self.get_action_list_external().addItems(entries)
                    self.update_actions_connection()
                    self.update_menu()
                except KeyError as e:
                    pass
    def update_actions_connection(self):

        for ind_file, file in enumerate(self.list_managed_entries_path()):
            self.connect_action(self.get_action_from_file(file), connect=False)

            self.connect_action(
                self.get_action_from_file(file),
                self.create_slot_from_file(
                    self.get_entry_folder().joinpath(file.stem + self.entry_extension)),
            )

    def update_execute_action_tooltip(self, entry: str):
        self.get_action(ManagerActions.EXECUTE).setToolTip(
            f'Execute the selected {self.entry_type} entry: {entry} ("Ctrl+A")')

    def create_slot_from_file(self, filename: Path):
        return lambda: self.execute_entry_base(filename)

    def update_menu(self):
        try:
            menu = self.get_menu(Menu.EXTERNAL)
            menu.clear()
            menu.addAction(self.get_action(ManagerActions.OPEN))
            menu.addSeparator()
            load_menu = menu.addMenu(f"Load {self.entry_type.capitalize()}s")

            for ind_file, file in enumerate(self.list_managed_entries_path()):
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
    from pymodaq_gui.utils.utils import mkQApp
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
    app.exec()
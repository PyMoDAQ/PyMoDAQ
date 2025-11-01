from pathlib import Path
from typing import Any, Union
from qtpy import QtWidgets, QtCore

from pymodaq.extensions.utils import CustomExt
from pymodaq_utils.enums import StrEnum

from pymodaq_gui.managers.action_manager import ActionManager


class ExternalActions(StrEnum):
    Open = "open"
    Label = "label"
    List = "list"
    Load = "load"


class InternalActions(StrEnum):
    COPY = 'copy_entry'
    NEW = 'create_new_entry'
    DELETE = 'delete_entry'
    SAVE = 'save_entry'
    RELOAD = 'reload_entry'


class ManagerBase(CustomExt):

    new_file = QtCore.Signal()
    applied_entry = QtCore.Signal(Path)
    entry_type: str
    entry_extension: str

    def __init__(self,
                 dashboard: 'DashBoard' = None,
                 menu: QtWidgets.QMenu = None,
                 toolbar: QtWidgets.QToolBar = None):

        super().__init__(parent=QtWidgets.QMainWindow(), dashboard=dashboard)
        self.action_manager = ManagerActions(self, menu=menu, toolbar=toolbar)

        self.main_widget = QtWidgets.QWidget()
        self.mainwindow.setCentralWidget(self.main_widget)

        self.setup_ui()

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

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        """Get the folder path where the managed entries are stored."""
        raise NotImplementedError

    @property
    def entry(self) -> str:
        """ Get/Set the name of the current entry """
        return self.get_action('entries').currentText()

    @entry.setter
    def entry(self, preset_name: str):
        self.update_entry(preset_name)

    @property
    def entry_filename(self) -> Path:
        """ Get the full path of the current entry file """
        kwargs_to_entry_folder = {}  # reimplement if needed
        return self.get_entry_folder(**kwargs_to_entry_folder).joinpath(self.entry + self.entry_extension)

    @property
    def entries(self) -> list[str]:
        """ Get/Set the name of all existing entries """
        return [path.stem for path in self.get_entry_folder().iterdir() if path.suffix == self.entry_extension]

    @property
    def entries_filename(self) -> list[Path]:
        """ Get the full path of all entries file """
        return self.list_managed_entries_path()

    def list_managed_entries(self, **kwargs_to_entry_folder) -> list[str]:
        """Returns a list of names of managed entries."""
        return [path.stem for path in self.list_managed_entries_path(**kwargs_to_entry_folder)]

    def list_managed_entries_path(self, **kwargs_to_entry_folder) -> list[Path]:
        """Should return a list of Path objects representing managed entries.

        Example:
        --------
        [path for path in get_set_preset_path().iterdir() if path.suffix == self.entry_extension]
        """
        return [path for path in self.get_entry_folder(**kwargs_to_entry_folder).iterdir()
                if path.suffix == self.entry_extension]

    def setup_docks(self):
        """Sets up the widgets for the manager.

        Eventually, this can be overridden in subclasses to add more/different widgets/docks...
        """
        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addWidget(self.settings_tree)
        self.main_widget.setLayout(vlayout)

    def setup_actions_base(self):
        self.add_widget('entry_label', QtWidgets.QLabel(
            f'Configuration from {self.entry_type.capitalize()}:'))
        self.add_widget('entries', QtWidgets.QComboBox(),
                        tip=f'Name of the current {self.entry_type}',
                        kwargs={'setReadOnly': True})
        self.get_action('entries').addItems(self.entries + ['...'])

        self.add_action(InternalActions.COPY, f'Copy {self.entry_type.capitalize()}', 'EditCopy')
        self.add_action(InternalActions.NEW,
                        f'New {self.entry_type.capitalize()}', 'ListAdd',
                        tip=f'Create a new {self.entry_type} file')
        self.add_action(InternalActions.DELETE,
                        f'Delete {self.entry_type.capitalize()}', 'ListRemove',
                        tip=f'Delete the current {self.entry_type} file')
        self.add_action(InternalActions.SAVE,
                        f'Save {self.entry_type.capitalize()}', 'DocumentSave',
                        tip=f'Save/Update the current {self.entry_type.capitalize()}')
        self.add_action(InternalActions.RELOAD,
                        f'Reload {self.entry_type.capitalize()}', 'ViewRefresh',
                        tip=f'Reload the current {self.entry_type} file')

    def connect_things_base(self):
        self.connect_action('entries', self.update_entry,
                            signal_name='currentTextChanged')
        self.connect_action(InternalActions.COPY, self.copy_entry)
        self.connect_action(InternalActions.NEW, self.create_preset)
        self.connect_action(InternalActions.DELETE, self.delete_entry)
        self.connect_action(InternalActions.SAVE, lambda: self.save_check())
        self.connect_action(InternalActions.RELOAD, lambda: self.update_entry())

        self.get_action('entries').setCurrentText('default')

    def create_entry(self):
        text, ok = QtWidgets.QInputDialog.getText(
            None,
            f'Enter a NEW {self.entry_type.capitalize()} name',
            f'{self.entry_type.capitalize()} name:', QtWidgets.QLineEdit.Normal)
        if ok and text != '':
            entries = [self.get_action('entries').itemText(ind).lower() for
                       ind in range(self.get_action('entries').count())]
            if text.lower() not in entries:
                entries.append(text.lower())
                entries.sort()
                index = entries.index(text.lower())
                self.get_action('entries').insertItem(index-1, text)

            self.get_action('entries').setCurrentText(text)
            self.save_check()

    def copy_entry(self):
        text, ok = QtWidgets.QInputDialog.getText(
            None, f'Enter a NEW {self.entry_type.capitalize()} name',
            f'{self.entry_type.capitalize()} name:', QtWidgets.QLineEdit.Normal)
        if ok and text != '':
            self.save_check(text)
            entries = [self.get_action('entries').itemText(ind).lower() for
                       ind in range(self.get_action('entries').count())]
            if text.lower() not in entries:
                entries.append(text.lower())
                entries.sort()
                index = entries.index(text.lower())
                self.get_action('entries').insertItem(index-1, text)

            self.get_action('entries').setCurrentText(text)

    def delete_entry(self):
        current_preset = self.entry
        if current_preset == '...':
            return
        user_agreed = dialogbox(
            title='Delete confirmation',
            message=f'Are you sure you want to delete the {self.entry_type.capitalize()}'
                    f' {current_preset} ?',
        )
        if user_agreed:
            self.connect_action('entries', signal_name='currentTextChanged', connect=False)
            preset_file = self.get_entry_folder().joinpath(f'{current_preset}.xml')

            preset_file.unlink(missing_ok=True)
            self.remove_preset_related_files(current_preset)

            logger.info(f'{self.entry_type.capitalize()} file {preset_file} deleted')
            self.get_action('entries').removeItem(
                self.get_action('entries').currentIndex()
            )
            self.connect_action('entries', self.update_entry, signal_name='currentTextChanged')
            self.new_file.emit()  # notify that an antry has been deleted


    def apply_entry(self, entry: Union[str, Path] = None, **kwargs):
        """Applies the entry from the given file in the manager.

        Parameters:
        -----------
        file : Path
            The path to the configuration file to be applied.
        """
        raise NotImplementedError

    def delete_entry(self):
        """Deletes the current entry in the manager."""
        raise NotImplementedError

    def update_entry(self, entry: Union[str, Path] = None, **kwargs):
        """Updates the current entry with the one from the given file in the manager.

        Parameters:
        -----------
        file : Path
            The path to the configuration file to be updated.
        """
        raise NotImplementedError

    def show(self):
        self.mainwindow.show()


class ManagerActions(ActionManager):
    """Class to manage actions for a specific manager in PyMoDAQ.

    Inherits from ActionManager and initializes with a specific manager name.
    """

    def __init__(self, manager: ManagerMixin, menu: QtWidgets.QMenu = None, toolbar: QtWidgets.QToolBar = None):
        super().__init__()
        self.manager = manager
        self.manager_name = manager.__class__
        if toolbar is not None:
            self.set_toolbar(toolbar)
            self.hide_widget = False
        else:
            if hasattr(self.manager, 'toolbar'):
                self.set_toolbar(self.manager.toolbar)
                self.hide_widget = True

        if menu is not None:
            self.set_menu(menu)
        self.load_menu: QtWidgets.QMenu = None

        self.setup_actions()
        self.connect_things()

    def setup_actions(self):
        self.add_action(ExternalActions.Open, f"{self.manager.entry_type.capitalize()} Manager", "",
                        'Open the Preset Manager to create/modify experimental setup configuration files: "presets"',
                        auto_toolbar=False, auto_menu=True)
        self.add_widget(ExternalActions.Label, QtWidgets.QLabel(f'{self.manager.entry_type.capitalize()}:'), auto_toolbar=True)
        self.add_widget(ExternalActions.List, QtWidgets.QComboBox, signal_str="currentTextChanged",
                        slot=self.update_load_action_tooltip,
                        auto_toolbar=True)
        self.add_action(ExternalActions.Load, "LOAD", "Open",
                        tip=f"Load the selected {self.manager.entry_type}: ",
                        auto_toolbar=True, auto_menu=False)

        if self.hide_widget:
            self.get_action(ExternalActions.Label).setVisible(False)
            self.get_action(ExternalActions.List).setVisible(False)
            self.get_action(ExternalActions.Load).setVisible(False)

    def connect_things(self):
        self.connect_action(ExternalActions.Open, lambda: self.manager.show())

    def update_load_action_tooltip(self, entry: str):
        self.get_action(ExternalActions.Load).setToolTip(f"Load the selected {self.manager.entry_type}: {entry}")

    def get_action_from_file(self, file: Path):
        return f"{file.stem}_{self.manager_name}"

    def get_action_list(self) -> QtWidgets.QComboBox:
        return self.get_action(ExternalActions.List)

    def update_action_list(self, **kwargs_to_entry_folder):
        entries = []
        self.get_action_list().clear()
        for ind_file, file in enumerate(self.manager.list_managed_entries_path(**kwargs_to_entry_folder)):
            if not self.has_action(self.get_action_from_file(file)):
                self.add_action(
                    self.get_action_from_file(file),
                    file.stem,
                    "",
                    f"Load the {file.stem} entry",
                    auto_toolbar=False,
                )
            entries.append(file.stem)
        self.get_action_list().addItems(entries)
        self.update_actions_connection(**kwargs_to_entry_folder)
        self.update_menu(**kwargs_to_entry_folder)

    def update_actions_connection(self, **kwargs_to_entry_folder):

        for ind_file, file in enumerate(self.manager.list_managed_entries_path()):
            self.connect_action(self.get_action_from_file(file), connect=False)

            self.connect_action(
                self.get_action_from_file(file),
                self.create_slot_from_file(
                    self.manager.get_entry_folder(**kwargs_to_entry_folder).joinpath(file.stem)),
            )
            self.connect_action(ExternalActions.Load, connect=False)
            self.connect_action(ExternalActions.Load,
                                lambda: self.manager.apply_entry(
                                    self.manager.get_entry_folder(**kwargs_to_entry_folder).joinpath(
                                        f"{self.get_action_list().currentText()}.{self.manager.entry_extension}"
                                    )),
                                )

    def create_slot_from_file(self, filename: Path):
        return lambda: self.manager.apply_entry(filename)

    def update_menu(self, **kwargs_to_entry_folder):
        try:
            self.menu.clear()
            self.menu.addAction(self.get_action(ExternalActions.Open))
            self.menu.addSeparator()
            self.load_menu = self.menu.addMenu(f"Load {self.manager.entry_type.capitalize()}s")

            for ind_file, file in enumerate(self.manager.list_managed_entries_path(**kwargs_to_entry_folder)):
                if self.has_action(self.get_action_from_file(file)):
                    self.load_menu.addAction(self.get_action(
                        self.get_action_from_file(file)
                        )
                    )
        except AttributeError:  # means self.menu is not yet defined
            pass

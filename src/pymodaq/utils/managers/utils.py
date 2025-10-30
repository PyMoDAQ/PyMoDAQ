from pathlib import Path
from typing import Any
from qtpy import QtWidgets

from pymodaq_utils.enums import StrEnum

from pymodaq_gui.managers.action_manager import ActionManager


class ManagerMixin:

    def __init__(self, entry_type: str, entry_extension: str):
        self.entry_type = entry_type
        self.entry_extension = entry_extension

        self.mainwindow: QtWidgets.QMainWindow = None  # to be defined outside the Mixin

    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        """Get the folder path where the managed entries are stored."""
        raise NotImplementedError

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

    def apply_entry(self, file: Path):
        """Applies the entry from the given file in the manager.

        Parameters:
        -----------
        file : Path
            The path to the configuration file to be applied.
        """
        raise NotImplementedError

    def show(self):
        self.mainwindow.show()


class Actions(StrEnum):
    Open = "open"
    Label = "label"
    List = "list"
    Load = "load"


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
        self.add_action(Actions.Open, f"{self.manager.entry_type.capitalize()} Manager", "",
                        'Open the Preset Manager to create/modify experimental setup configuration files: "presets"',
                        auto_toolbar=False, auto_menu=True)
        self.add_widget(Actions.Label, QtWidgets.QLabel(f'{self.manager.entry_type.capitalize()}:'), auto_toolbar=True)
        self.add_widget(Actions.List, QtWidgets.QComboBox, signal_str="currentTextChanged",
                        slot=self.update_load_action_tooltip,
                        auto_toolbar=True)
        self.add_action(Actions.Load, "LOAD", "Open",
                        tip=f"Load the selected {self.manager.entry_type}: ",
                        auto_toolbar=True, auto_menu=False)

        if self.hide_widget:
            self.get_action(Actions.Label).setVisible(False)
            self.get_action(Actions.List).setVisible(False)
            self.get_action(Actions.Load).setVisible(False)

    def connect_things(self):
        self.connect_action(Actions.Open, lambda: self.manager.show())

    def update_load_action_tooltip(self, entry: str):
        self.get_action(Actions.Load).setToolTip(f"Load the selected {self.manager.entry_type}: {entry}")

    def get_action_from_file(self, file: Path):
        return f"{file.stem}_{self.manager_name}"

    def get_action_list(self) -> QtWidgets.QComboBox:
        return self.get_action(Actions.List)

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
            self.connect_action(Actions.Load, connect=False)
            self.connect_action(Actions.Load,
                                lambda: self.manager.apply_entry(
                                    self.manager.get_entry_folder(**kwargs_to_entry_folder).joinpath(
                                        f"{self.get_action_list().currentText()}.{self.manager.entry_extension}"
                                    )
                                ),
                                )

    def create_slot_from_file(self, filename: Path):
        return lambda: self.manager.apply_entry(filename)

    def update_menu(self, **kwargs_to_entry_folder):
        try:
            self.menu.clear()
            self.menu.addAction(self.get_action(Actions.Open))
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

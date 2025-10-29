from pathlib import Path

from qtpy import QtWidgets

from pymodaq_utils.enums import StrEnum

from pymodaq_gui.managers.action_manager import ActionManager


class ManagerMixin:

    def __init__(self, entry_type: str):
        self.entry_type = entry_type

    def list_managed_entries(self) -> list[str]:
        """Returns a list of names of managed entries."""
        return [path.stem for path in self.list_managed_entries_path()]

    def list_managed_entries_path(self) -> list[Path]:
        """Should return a list of Path objects representing managed entries."""
        raise NotImplementedError


class Actions(StrEnum):
    Open = "open"
    Label = "label"
    List = "list"
    Load = "load"


class ManagerActions(ActionManager):
    """Class to manage actions for a specific manager in PyMoDAQ.

    Inherits from ActionManager and initializes with a specific manager name.
    """

    def __init__(self, manager: ManagerMixin):
        super().__init__()
        self.manager = manager
        self.manager_name = manager.__class__

    def setup_actions(self):
        self.add_action(Actions.Open, "Preset Manager", "",
                        'Open the Preset Manager to create/modify experimental setup configuration files: "presets"',
                        auto_toolbar=False,)
        self.add_widget(Actions.Label, QtWidgets.QLabel('Preset:'), toolbar=self.toolbar)
        self.add_widget(Actions.List, QtWidgets.QComboBox, toolbar=self.toolbar,
                        signal_str="currentTextChanged", slot=self.update_load_action_tooltip,)
        self.add_action(Actions.Load, "LOAD", "Open", tip=f"Load the selected {self.manager.entry_type}: ")

    def update_load_action_tooltip(self, entry: str):
        self.get_action(Actions.Load).setToolTip(f"Load the selected {self.manager.entry_type}: {entry}")

    def get_action_from_file(self, file: Path):
        return f"{file.stem}_{self.manager_name}"

    def get_action_list(self) -> QtWidgets.QComboBox:
        return self.get_action(Actions.List)

    def update_action_list(self):
        entries = []
        self.get_action_list().clear()
        for ind_file, file in enumerate(self.manager.list_managed_entries_path()):
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
        self.update_preset_actions_connection()
        self.update_preset_menu()

    def update_preset_actions_connection(self):
        pass

    def update_preset_menu(self):
        pass
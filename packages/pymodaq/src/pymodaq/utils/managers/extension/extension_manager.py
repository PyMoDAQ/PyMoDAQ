import sys
from pathlib import Path
from typing import TYPE_CHECKING

from qtpy import QtWidgets

from pymodaq.extensions import get_extensions, ExtensionEnum
from pymodaq.extensions.custom_ext import CustomExt
from pymodaq.utils.gui_utils.loader_utils import create_extension
from pymodaq_gui.managers.manager_base import ManagerBase, ManagerActions
from pymodaq_utils import set_logger
from pymodaq_utils.logger import get_module_name

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard

logger = set_logger(get_module_name(__file__))


class ExtensionManager(ManagerBase):
    entry_type = 'extension'
    entry_extension = '.xml'
    icon_name = 'extension'

    def __init__(self, dashboard: 'DashBoard' = None):
        self.extension_catalog = get_extensions()
        self.loaded_extensions: dict[ExtensionEnum, CustomExt] = {}
        self._internal_dashboard_ui = None

        super().__init__(dashboard=dashboard)

        if self.entries:
            self.entries_sync.update_key('current', self.entries[0])

    # ManagerBase Implementation
    def get_entry_folder(self, **kwargs) -> Path:
        """Extensions are virtual; not file-backed."""
        return Path.home()

    def list_managed_entries(self, **kwargs) -> list[str]:
        """Extensions are defined in ExtensionEnum."""
        return ExtensionEnum.values()

    def list_managed_entries_path(self, **kwargs) -> list[Path]:
        """Extensions have no file paths."""
        return []

    def save_entries(self, entry_path: Path = None) -> None:
        """Extensions don't persist to files."""
        return NotImplemented

    def _update_entry(self, entry_path: Path) -> None:
        """Extensions don't need file updates."""
        return NotImplemented

    def _execute_entry(self, entry_path: Path = None, **kwargs) -> bool:
        """Load and display the selected extension."""
        entry_name = entry_path.stem

        if entry_name not in ExtensionEnum.values():
            logger.warning(f"Extension not found: {entry_name}")
            return False

        try:
            ext_enum = ExtensionEnum(entry_name)
            ext_module = self.load_extension(ext_enum, **kwargs)
            return ext_module is not None
        except Exception as e:
            logger.exception(f"Failed to load extension {entry_name}: {e}")
            return False

    def execute_entry(self, entry_path: str | Path = None, **kwargs):
        """Execute extension, creating dashboard if needed."""
        if self.dashboard is None:
            logger.info("Creating internal dashboard for extension")
            from pymodaq.dashboard import create_load_dashboard
            self._internal_dashboard_ui, dashboard = create_load_dashboard()
            self._internal_dashboard_ui.mainwindow.setVisible(False)
            self.dashboard = dashboard
            logger.info("Internal dashboard created")

        super().execute_entry(entry_path, **kwargs)

    def load_extension(self, ext_enum: ExtensionEnum,
                      win: QtWidgets.QMainWindow = None) -> CustomExt | None:
        """Load and display an extension."""
        try:
            shared_ui, ext_module = create_extension(
                self.dashboard,
                self.extension_catalog[ext_enum].klass,
                window=win,
            )

            self.loaded_extensions[ext_enum] = ext_module
            ext_module.shared_ui = shared_ui
            ext_module.status_signal.connect(self.update_status)
            shared_ui.show()

            if hasattr(ext_module, 'set_action_checked'):
                try:
                    ext_module.set_action_checked('show_dashboard', True)
                except (AttributeError, RuntimeError):
                    pass

            logger.info(f"Extension {ext_enum.value} loaded successfully")
            return ext_module
        except Exception as e:
            logger.error(f"Failed to load extension {ext_enum.value}: {e}")
            raise

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        self.extensions_menu = self.add_menu('extensions', "Extensions",
                                             parent_menu=self.menubar)

    def setup_actions(self):
        """Add extension actions to the manager."""
        for ext_name in ExtensionEnum.names():
            self.add_action(ExtensionEnum[ext_name],
                            ExtensionEnum[ext_name].value,
                            auto_toolbar=False,
                            menu=self.extensions_menu
                        )

        self.get_action(ManagerActions.COPY).setVisible(False)
        self.get_action(ManagerActions.NEW).setVisible(False)
        self.get_action(ManagerActions.DELETE).setVisible(False)
        self.get_action(ManagerActions.SAVE).setVisible(False)
        self.get_action(ManagerActions.RELOAD).setVisible(False)
        self.get_action(ManagerActions.OPEN).setVisible(False)

    def connect_things(self):
        """Connect extension actions to load methods."""
        for ext_name in ExtensionEnum.names():
            self.connect_action(ExtensionEnum[ext_name],
                               lambda e=ExtensionEnum[ext_name]: self.load_extension(e))

    def quit_fun(self):
        """Clean up extensions and internal dashboard."""
        try:
            for ext in self.loaded_extensions.values():
                if hasattr(ext, 'quit_fun'):
                    ext.quit_fun()
        except Exception as e:
            logger.exception(str(e))

        super().quit_fun()


def main():
    from pymodaq_gui.qt_utils import mkQApp

    app = mkQApp('ExtensionManager')
    prog = ExtensionManager()
    external_ui = QtWidgets.QMainWindow()

    toolbar, menu = prog.get_external_toolbar_menu()
    external_ui.addToolBar(toolbar)
    external_ui.menuBar().addMenu(menu)

    prog.update_entry()
    prog.enable_actions(True)
    prog.mainwindow.show()
    external_ui.show()
    sys.exit(app.exec())




if __name__ == '__main__':
    main()


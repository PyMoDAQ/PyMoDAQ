import sys
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Union, cast

from qtpy import QtWidgets

from pymodaq.extensions import get_extensions, ExtensionEnum
from pymodaq.extensions.custom_ext import CustomExt
from pymodaq.utils.gui_utils.loader_utils import create_extension
from pymodaq.utils.managers.modules.modules_manager import ModulesManager
from pymodaq_gui.managers.manager_base import ManagerBase, ManagerActions
from pymodaq_utils import set_logger
from pymodaq_utils.logger import get_module_name

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard
    from pymodaq.utils.shared_ui import SharedUI

logger = set_logger(get_module_name(__file__))


def _build_standalone_context(manager: 'ExtensionManager', configurator) -> SimpleNamespace:
    """Create a minimal dashboard context for standalone extension execution."""
    experiment_manager = configurator.experiment_manager
    return SimpleNamespace(
        mainwindow=manager.mainwindow,
        experiment_manager=experiment_manager,
        configurator=configurator,
        detector_modules=[],
        actuators_modules=[],
        modules_manager=ModulesManager([], [], parent_name='StandaloneExtensionManager'),
        splash_sc=manager.splash_sc,
        overshoot=False,
        experiment_file=Path('default.xml'),
        settings=experiment_manager.settings,
        roi_saver=SimpleNamespace(roi_experiments=None),
        add_status=lambda txt: None,
        update_status=lambda txt, wait_time=0, log_type=None: None,
    )



class ExtensionManager(ManagerBase):
    entry_type = 'extension'
    entry_extension = '.xml'

    def __init__(self, dashboard: 'DashBoard' = None, shared_UI: 'SharedUI' = None):
        self.extension_catalog = get_extensions()
        self.loaded_extensions: dict[ExtensionEnum, CustomExt] = {}
        self._standalone_configurator = None
        self._standalone_context: SimpleNamespace | None = None

        self.shared_ui = shared_UI

        super().__init__(dashboard=dashboard)

        if self.entries:
            self.entries_sync.update_key('current', self.entries[0])

    # ManagerBase API -----------------------------------------------------------
    def get_entry_folder(self, **kwargs_to_entry_folder) -> Path:
        # Extensions are not file-backed entries; return a harmless placeholder.
        return Path.home()

    def list_managed_entries(self, **kwargs_to_entry_folder) -> list[str]:
        return ExtensionEnum.values()

    def list_managed_entries_path(self, **kwargs_to_entry_folder) -> list[Path]:
        # Disable file-based action registration from ManagerBase.
        return []

    def save_entries(self, entry_path: Path = None):
        # No file persistence for extensions.
        return

    def _update_entry(self, entry_path: Path):
        return


    def execute_entry(self, entry_path: Union[str, Path] = None, **kwargs):
        """Execute selected entry even on standalone dashboard"""
        if entry_path is None:
            entry_name = self.entry
        elif isinstance(entry_path, Path):
            entry_name = entry_path.stem
        else:
            entry_name = str(entry_path)

        if entry_name not in self.entries:
            logger.warning(f"Unknown extension entry: {entry_name}")
            return

        resolved_entry_path = self.entry_path_from_name(entry_name)
        self.update_entry(resolved_entry_path)
        self.entry_applied = self._execute_entry(resolved_entry_path, **kwargs)



    def _execute_entry(self, entry_path: Path = None, **kwargs):
        extension_name = self.entry if entry_path is None else entry_path.stem
        if extension_name not in ExtensionEnum.values():
            logger.warning(f"Extension entry not found in enum values: {extension_name}")
            return False

        ext_enum = ExtensionEnum(extension_name)
        self.entry = extension_name
        self.load_extension(ext_enum, win=QtWidgets.QMainWindow())
        self.show()
        return True

    def setup_actions(self):
        # Keep only relevant manager actions for extension launching.
        for action_name in (ManagerActions.COPY, ManagerActions.NEW, ManagerActions.DELETE,
                            ManagerActions.SAVE, ManagerActions.RELOAD, ManagerActions.OPEN):
            self.get_action(action_name).setVisible(False)

        for ext_name in ExtensionEnum.names():
            self.add_action(ExtensionEnum[ext_name], ExtensionEnum[ext_name].value,
                            auto_toolbar=False)


    def connect_things(self):
        for ext_name in ExtensionEnum.names():
            self.connect_action(ExtensionEnum[ext_name],
                                self.create_extension_slot(ExtensionEnum[ext_name]))



    def create_extension_slot(self, extenum: ExtensionEnum):
        return lambda: self.load_extension(extenum)



    def load_extension(self, ext_enum: ExtensionEnum,
                       win: QtWidgets.QMainWindow = None
                       ) -> 'CustomExt':
        dashboard_context = self._get_extension_context()
        shared_ui, ext_module = create_extension(
            cast('DashBoard', dashboard_context), self.extension_catalog[ext_enum].klass,
            window=win,
        )
        self.loaded_extensions[ext_enum] = ext_module
        ext_module.shared_ui = shared_ui
        ext_module.status_signal.connect(self.update_status)
        shared_ui.show()
        ext_module.set_action_checked('show_dashboard', True)

        return ext_module

    def _get_extension_context(self) -> Union['DashBoard', SimpleNamespace]:
        if self.dashboard is not None:
            return self.dashboard

        self._ensure_standalone_context()
        if self._standalone_context is None:
            raise RuntimeError('Standalone extension context could not be initialized')
        return self._standalone_context

    def _ensure_standalone_context(self):
        if self._standalone_context is not None:
            return

        from pymodaq.utils.managers.configurator.configurator import Configurator

        self._standalone_configurator = Configurator()
        self._standalone_configurator.enable_actions(True)
        self._standalone_configurator.experiment_manager.enable_actions(True)
        self._standalone_context = _build_standalone_context(self, self._standalone_configurator)


    def quit_fun(self):
        try:
            for ext in self.loaded_extensions.values():
                if hasattr(ext, 'quit_fun'):
                    ext.quit_fun()

            if self._standalone_configurator is not None:
                self._standalone_configurator.quit_fun()

        except Exception as e:
            logger.exception(str(e))

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        self.extensions_menu = self.add_menu('extensions', "Extensions")
        for ext_name in ExtensionEnum.names():
            self.extensions_menu.addAction(self.get_action(ExtensionEnum[ext_name]))




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
from pathlib import Path
from typing import TYPE_CHECKING, Union

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

logger = set_logger(get_module_name(__file__))


class ExtensionManager(ManagerBase):
    entry_type = 'extension'
    entry_extension = '.xml'

    def __init__(self, dashboard: 'DashBoard' = None):
        self.extensions_names = ExtensionEnum.values()
        self.extensions: dict[ExtensionEnum, CustomExt] = {}
        self.extension_windows = []
        self._standalone_dashboard_proxy = None
        self._standalone_configurator = None

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
        # No settings tree update from file for extensions.
        return

    def save_new_history_entry(self):
        # Extensions are launched ad hoc; nothing to persist in launcher history.
        return

    def update_entry(self, entry: Union[str, Path] = None, **kwargs):
        if entry is None:
            entry_name = self.entry
        elif isinstance(entry, Path):
            entry_name = entry.stem
        else:
            entry_name = str(entry)

        if entry_name not in self.entries:
            return

        self.entry = entry_name
        self.update_execute_action_tooltip(entry_name)
        self.updated_entry.emit(entry_name)

    def execute_entry(self, entry_path: Path = None, **kwargs):
        if entry_path is None:
            entry_name = self.entry
        else:
            entry_name = entry_path.stem

        if entry_name not in self.entries:
            logger.warning(f'Unknown extension: {entry_name}')
            self.entry_applied = False
            return

        self.update_entry(entry_name)

        try:
            ext_enum = ExtensionEnum(entry_name)
            self.load_extension(ext_enum)
            self.entry_applied = True
        except Exception as e:
            logger.exception(str(e))
            self.entry_applied = False

    def setup_actions(self):
        # Keep only relevant manager actions for extension launching.
        for action_name in (ManagerActions.COPY, ManagerActions.NEW, ManagerActions.DELETE,
                            ManagerActions.SAVE, ManagerActions.RELOAD):
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
        extensions = get_extensions()
        if ext_enum not in extensions:
            raise KeyError(f'Unknown extension enum: {ext_enum}')

        dashboard_context = self._get_dashboard_context()

        shared_ui, ext_module = create_extension(
            dashboard_context, extensions[ext_enum].klass,
            window=win,
        )
        self.extensions[ext_enum] = ext_module
        ext_module.shared_ui = shared_ui
        if dashboard_context is not None and hasattr(dashboard_context, 'add_status'):
            ext_module.status_signal.connect(dashboard_context.add_status)
        else:
            ext_module.status_signal.connect(self.update_status)
        shared_ui.show()
        if ext_module.has_action('show_dashboard'):
            ext_module.set_action_checked('show_dashboard', True)

        return ext_module

    def quit_fun(self):
        try:
            for ext in self.extensions.values():
                if hasattr(ext, 'quit_fun'):
                    ext.quit_fun()

        except Exception as e:
            logger.exception(str(e))

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        self.extensions_menu = self.add_menu('extensions', "Extensions")
        for ext_name in ExtensionEnum.names():
            self.extensions_menu.addAction(self.get_action(ExtensionEnum[ext_name]))

    def _get_dashboard_context(self):
        if self.dashboard is not None:
            return self.dashboard

        if self._standalone_dashboard_proxy is None:
            from pymodaq.utils.managers.configurator.configurator import Configurator

            self._standalone_configurator = Configurator()
            self._standalone_configurator.enable_actions(True)
            preset_manager = self._standalone_configurator.preset_manager
            preset_manager.enable_actions(True)

            class _StandaloneDashboardProxy:
                pass

            proxy = _StandaloneDashboardProxy()
            proxy.mainwindow = self.mainwindow
            proxy.preset_manager = preset_manager
            proxy.configurator = self._standalone_configurator
            proxy.detector_modules = []
            proxy.actuators_modules = []
            proxy.modules_manager = ModulesManager([], [], parent_name='StandaloneExtensionManager')
            proxy.splash_sc = self.splash_sc
            proxy.overshoot = False
            proxy.preset_file = Path('default.xml')
            proxy.settings = preset_manager.settings

            class _DummyRoiSaver:
                roi_presets = None

            proxy.roi_saver = _DummyRoiSaver()
            proxy.add_status = lambda txt: self.update_status(txt)
            proxy.update_status = lambda txt, wait_time=0, log_type=None: self.update_status(txt)

            self._standalone_dashboard_proxy = proxy

        return self._standalone_dashboard_proxy




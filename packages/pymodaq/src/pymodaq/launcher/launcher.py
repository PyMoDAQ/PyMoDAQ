from datetime import datetime
import subprocess
import sys

from qtpy import QtCore, QtWidgets
from qtpy.QtCore import Signal, Qt, QFileSystemWatcher
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QComboBox,
)
import toml

from pymodaq_utils import set_logger
from pymodaq_utils.logger import get_module_name
from pymodaq_utils.utils import ThreadCommand
from pymodaq_utils.enums import StrEnum
from pymodaq_utils.config import get_set_local_dir

from pymodaq_gui.parameter import Parameter
from pymodaq_gui.utils import CustomApp

from pymodaq.extensions import ExtensionEnum
from pymodaq.launcher import HISTORY_FILE_PATH, HISTORY_FILE_NAME
from pymodaq.utils.managers.state.state_manager import StateManager
from pymodaq.utils.managers.extension.extension_manager import ExtensionManager
from pymodaq.utils.managers.modules.utils import ModuleType
from pymodaq.utils.shared_ui import SharedUI

from pymodaq_gui.managers.manager_base import ManagerActions  # should be imported after to avoid circular imports

logger = set_logger(get_module_name(__file__))


class EnumToolTip(StrEnum):
    DASHBOARD = 'Launch an empty Dashboard without configuration'
    DAQ_VIEWER = 'Launch an empty Viewer'
    DAQ_MOVE = 'Launch an empty DAQ_Move'
    H5BROWSER = 'Launch H5Browser'
    BACK_HISTORY = 'Navigate to the back item of experiments history'
    NEXT_HISTORY = 'Navigate to the next item of experiments history'
    RESTORE = 'Restore this experiment with the selected state_manager'


class ExperimentTreeBuilder:
    """Build experiment summary tree from full experiment settings."""

    def __init__(self, experiment_settings):
        self.experiment_settings = experiment_settings

    @staticmethod
    def _module_display_title(module_param) -> str:
        name_param = module_param.child('name')
        if name_param is not None and name_param.value() not in (None, ''):
            return str(name_param.value())
        module_title = module_param.title()
        if module_title:
            return str(module_title)
        return str(module_param.name())

    def _build_summary_group(self, module_type: ModuleType, group_title: str) -> dict:
        if not self.experiment_settings.children():
            module_name = "Actuators" if module_type == ModuleType.Actuator else "Detectors"
            children = [{
                'title': f"No {module_name.lower()} set for this experiment",
                'name': f'{module_type.value}_empty',
                'type': 'str',
                'readonly': True,
            }]
        else:
            group_param = self.experiment_settings.child(module_type.value)
            children = []

            if group_param is not None:
                for ind_module, module_param in enumerate(group_param.children()):
                    plugin_name = ""
                    info_param = module_param.child('info')
                    if info_param is not None:
                        type_param = info_param.child('type')
                        if type_param is not None:
                            plugin_name = str(type_param.value())

                    children.append({
                        'title': f"{self._module_display_title(module_param)} ({plugin_name})",
                        'name': f'{module_type.value}_title_{ind_module:02d}',
                        'type': 'group',
                    })

            if not children:
                module_name = "Actuators" if module_type == ModuleType.Actuator else "Detectors"
                children.append({
                    'title': f"No {module_name.lower()} set for this experiment",
                    'name': f'{module_type.value}_empty',
                    'type': 'str',
                    'readonly': True,
                })

        return {
            'title': group_title,
            'name': f'{module_type.value}_summary',
            'type': 'group',
            'expanded': True,
            'children': children,
        }

    def get_titles_only(self) -> list:
        """Return summary tree with only module titles."""
        return [
            self._build_summary_group(ModuleType.Actuator, 'Actuators'),
            self._build_summary_group(ModuleType.Detector, 'Detectors'),
        ]


class Launcher(CustomApp):
    command_sig = Signal(ThreadCommand)
    history_modified_sig = Signal()
    # list of dicts enabling a settings tree on the user interface
    params = []

    def __init__(self, parent: QtWidgets.QMainWindow, history_file_name: str = None):
        super().__init__(parent, add_toolbar_break=False)

        self.state_manager = StateManager()
        self.experiment_manager = self.state_manager.experiment_manager
        self._launcher_experiment_external_combo = None

        self.extension_manager = ExtensionManager()
        self.extension_manager_restore = ExtensionManager()

        # Loader
        self.history_keys = []
        self.history = {}
        self.history_index = 0
        self.history_file_name = history_file_name if history_file_name is not None else HISTORY_FILE_NAME
        self.history_file_path = get_set_local_dir(user=True).joinpath(self.history_file_name) if \
            (history_file_name is not None) else HISTORY_FILE_PATH

        # History file handler
        self._history_file_watcher = QFileSystemWatcher()
        self._history_file_watcher.addPath(str(self.history_file_path))
        self._history_file_watcher.fileChanged.connect(self.ui_refresh)
        self._history_file_watcher.fileChanged.connect(self._on_history_file_modified)

        self.splash_timer = QtCore.QTimer()
        self.splash_timer.timeout.connect(self.splash_sc.close)

        self.setup_ui()

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        # Remove the default toolbar created by CustomApp
        self.mainwindow.removeToolBar(self._toolbar)

    def setup_docks_and_widgets(self):
        """
        Layouts and widgets configuration.
        """

        # Layout
        self.main_hbox = QHBoxLayout()
        self.launcher_vbox = QVBoxLayout()
        self.loader_vbox = QVBoxLayout()
        self.hbox = QHBoxLayout()

        # Launcher
        self.dashboard_button = QPushButton("Dashboard")
        self.viewer_button = QPushButton("DAQ Viewer")
        self.move_button = QPushButton("DAQ Move")
        self.h5browser_button = QPushButton("H5Browser")
        self.shortcut_label = QLabel("Shortcuts :")
        self.launcher_vbox.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        # Header
        self.date_combo_box = QComboBox()
        self.date_combo_box.setMinimumSize(QtCore.QSize(146, 25))
        # set minimum size to ensure consistent UI layout when history file is empty vs non-empty
        self.date_label = QLabel("Date :")

        # Set tooltip buttons
        self.set_tooltip_button()

        # Set separator between launcher and loader
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("color: white;")

        self.main_hbox.addLayout(self.launcher_vbox)
        self.main_hbox.addWidget(separator)
        self.main_hbox.addLayout(self.loader_vbox, 1)
        self.loader_vbox.addLayout(self.hbox)
        self.loader_vbox.addWidget(self.add_toolbar('controls'))
        self.loader_vbox.layout().addWidget(self.settings_tree)

        self.experiment_manager.entry = 'New '

        self.set_launcher_vbox()

        self.set_header()
        self.set_controls()

        widget = QWidget()
        widget.setLayout(self.main_hbox)
        self.mainwindow.setCentralWidget(widget)

        logger.debug('docks are set')

    def setup_actions(self):
        '''
        subclass method from ActionManager
        '''
        self.add_action('launch_dashboard', 'Launch empty dashboard', '',
                        EnumToolTip.DASHBOARD, auto_toolbar=False
                        )
        self.add_action('launch_viewer', 'Launch empy viewer', '', EnumToolTip.DAQ_VIEWER, auto_toolbar=False)
        self.add_action('launch_move', 'Launch empty DAQ move', '', EnumToolTip.DAQ_MOVE, auto_toolbar=False)
        self.add_action('launch_h5browser', 'Launch H5Browser', '', EnumToolTip.H5BROWSER, auto_toolbar=False)

        self.add_action('back_config', 'Back', 'keyboard_arrow_left', EnumToolTip.BACK_HISTORY, auto_toolbar=True,
                        toolbar='header')
        self.header_toolbar.addWidget(self.date_label)
        self.header_toolbar.addWidget(self.date_combo_box)
        self.add_action('restore_dashboard', 'Launch',
                        'open_in_new', EnumToolTip.RESTORE, auto_toolbar=True, toolbar='header')
        self.add_action('next_config', 'Next', 'keyboard_arrow_right', EnumToolTip.NEXT_HISTORY, auto_toolbar=True,
                        toolbar='header')

        # setup_actions is called after setup_docks, style the action button here once it exists.
        button: QtWidgets.QToolButton = self.header_toolbar.widgetForAction(self.get_action('restore_dashboard'))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

    def connect_things(self):
        '''
        subclass method from CustomApp
        '''
        logger.debug('connecting things')
        logger.debug('connecting done')

        self.connect_action('launch_dashboard', self.launch_empty_dashboard)
        self.connect_action('launch_viewer',self.launch_empty_viewer)
        self.connect_action('launch_move',self.launch_empty_move)
        self.connect_action('launch_h5browser',self.launch_h5browser)

        # Connect action to button
        self.dashboard_button.clicked.connect(self.get_action('launch_dashboard').trigger)
        self.viewer_button.clicked.connect(self.get_action('launch_viewer').trigger)
        self.move_button.clicked.connect(self.get_action('launch_move').trigger)
        self.h5browser_button.clicked.connect(self.get_action('launch_h5browser').trigger)

        # Header of loader section
        self.connect_action('back_config', lambda: self.do_navigate(self.history_index + 1))
        self.connect_action('restore_dashboard', self.load_dashboard_with_experiment_and_state)
        self.connect_action('next_config', lambda: self.do_navigate(self.history_index-1))
        self.experiment_manager.get_action(ManagerActions.EXECUTE).setVisible(False)
        self.state_manager.get_action(ManagerActions.EXECUTE).setVisible(False)

        # Remove open action
        self.extension_manager.get_action(ManagerActions.OPEN).setVisible(False)

        # Inject new implementation extension launch method in the execute action
        execute_action = self.extension_manager.get_action(ManagerActions.EXECUTE)
        execute_action.triggered.disconnect() # disconnect normal action
        execute_action.triggered.connect(
            lambda checked=False: self.load_extension_subprocess(str(self.extension_manager.entry).strip())
        )

        self.date_combo_box.currentIndexChanged.connect(self._on_date_combo_box_changed)

    def do_things_after_ui_setup(self):
        """Non mandatory method to be subclassed in order to do things after the UI setup
        """
        self.history, self.history_keys = self.load_history_in_dict()
        self.experiment_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('experiment'))
        self.state_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('state_manager'))
        self.extension_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('launcher'))
        self.extension_manager_restore.get_external_toolbar_menu(toolbar=self.get_toolbar('extensions'))

        self.experiment_manager.enable_actions(True)
        self.experiment_manager.set_action_enabled('list_entries', True)
        self.state_manager.enable_actions(True)
        self.extension_manager.enable_actions(True)

        self.extension_manager_restore.enable_actions(True)
        self.extension_manager_restore.get_action(ManagerActions.OPEN).setVisible(False)
        self.extension_manager_restore.get_action(ManagerActions.EXECUTE).setVisible(False)
        restore_entries = self.extension_manager_restore.entries
        if 'empty' not in restore_entries:
            restore_entries = ['empty'] + restore_entries
        self.extension_manager_restore.entries_sync.update_key('items', restore_entries)
        self.extension_manager_restore.entries_sync.update_key('current', 'empty')

        self.ui_refresh()

    def set_launcher_vbox(self):
        """ Set widgets in QVBox launcher section"""
        self.launcher_vbox.addWidget(self.shortcut_label)
        for button in [self.dashboard_button, self.viewer_button, self.move_button, self.h5browser_button,]:
            button.setMinimumWidth(140)
            button.setMinimumHeight(28)
            button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            self.launcher_vbox.addWidget(button)

        self.launcher_vbox.setSpacing(10)

        # add horizontal separator to delimit shortcuts area and extensions area
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("color: white;")
        self.launcher_vbox.addWidget(separator)

        # add a toolbar for future extension feature
        self.launcher_vbox.addWidget(self.add_toolbar('launcher'))
        self.get_toolbar('launcher').setOrientation(QtCore.Qt.Orientation.Horizontal)

    def set_tooltip_button(self):
        self.dashboard_button.setToolTip(EnumToolTip.DASHBOARD)
        self.viewer_button.setToolTip(EnumToolTip.DAQ_VIEWER)
        self.move_button.setToolTip(EnumToolTip.DAQ_MOVE)
        self.h5browser_button.setToolTip(EnumToolTip.H5BROWSER)

    def set_header(self):
        self.hbox.addWidget(self.add_toolbar('header', 'Header', add_break=False))
        self.header_toolbar = self.get_toolbar('header')

        self.header_toolbar.layout().setSpacing(20)

    def set_controls(self):
        self.get_toolbar('controls').addWidget(self.add_toolbar('experiment', 'experiment', add_break=False))
        self.get_toolbar('controls').addWidget(self.add_toolbar('state_manager', 'State'))
        self.get_toolbar('controls').addWidget(self.add_toolbar('extensions', 'Extensions'))

    def popen_with_splash(self, args: list[str], msg: str, wait_time_ms: int = 1000):
        self.splash_sc.setVisible(True)
        self.splash_sc.showMessage(msg)
        subprocess.Popen(args)

        self.splash_timer.setInterval(wait_time_ms)
        self.splash_timer.start()

    def launch_empty_dashboard(self):
        self.popen_with_splash([sys.executable, '-m',  'pymodaq.dashboard'],
                               'Loading a DashBoard... Please wait...',
                               5000)

    def launch_empty_viewer(self):
        self.popen_with_splash([sys.executable, '-m',  'pymodaq.control_modules.daq_viewer'],
                               'Loading a DAQ_Viewer... Please wait...',
                               3000)

    def launch_empty_move(self):
        self.popen_with_splash([sys.executable, '-m',  'pymodaq.control_modules.daq_move'],
                               'Loading a DAQ_Move... Please wait...',
                               3000)

    def launch_h5browser(self):
        self.popen_with_splash([sys.executable, '-m',  'pymodaq.extensions.h5browser'],
                               'Loading a H5Browser... Please wait...',
                               3000)

    def show_experiment_titles_only(self, experiment_source=None):
        """Load an experiment source and display only module titles in settings_tree."""
        try:
            if experiment_source is None:
                experiment_settings = Parameter.create(name='empty', type='group', children=[])
            else:
                experiment_settings = self.create_parameter(experiment_source)
        except Exception as error:
            logger.warning(f'Unable to load experiment source {experiment_source}: {error}')
            if experiment_source is None:
                # Keep empty tree if no source provided
                experiment_settings = Parameter.create(name='empty', type='group', children=[])
            else:
                experiment_settings = self.create_parameter(self.experiment_manager.settings)

        self._full_experiment_settings = experiment_settings

        tree_builder = ExperimentTreeBuilder(experiment_settings)
        self.settings = tree_builder.get_titles_only()

        self.tree.header().hide()
        self.tree.expandAll()
        self.tree.setItemsExpandable(True)

    def load_dashboard_with_experiment_and_state(self):
        """
        Load and show dashboard with selected experiment and configuration.
        """
        args_lst = [sys.executable, '-m', 'pymodaq.dashboard',
                    '-x', self.experiment_manager.entry,
                    '-c', self.state_manager.entry]
        if self.extension_manager_restore.entry not in (None, '', 'empty'):
            args_lst += ['-e', self.extension_manager_restore.entry]
        self.popen_with_splash(args_lst,
                               f'Loading a DashBoard with {self.experiment_manager.entry} experiment and '
                               f'{self.state_manager.entry} state...\nPlease wait...',
                               5000)

    def do_navigate(self, index: int):
        """
        Navigate in history items by index.

        Parameters
        ----------
        index : int
            Value of index to go in history
        Notes
        -----
        Design by contract: caller must ensure the resulting index stays
        within valid history bounds.
        Precondition: 0 <= self.history_index + index < len(self.history)
        """
        assert 0 <= index < len(self.history)
        self.history_index = index
        self.ui_refresh()

    def check_disable_navigation_buttons(self):
        """
        Check and disable navigation buttons :
        * back button : last item of list
        * next button : first item of list
        Returns
        -------

        """
        self.set_action_enabled('next_config', self.history_index >= 1)
        self.set_action_enabled('back_config', self.history_index < len(self.history_keys) - 1)

    def ui_refresh(self):
        """Refresh interface and update experiment and configuration, entries,
        combo box values, actuators/detectors tree, history key and navigation actions."""
        # experiment and state
        if len(self.history_keys) > 0:
            actual_key = self.history_keys[self.history_index]

            self.experiment_manager.entry = self.history[actual_key]['experiment']
            self.state_manager.experiment_filename = self.experiment_manager.entry
            self.state_manager.entry = self.history[actual_key]['state']

            # date
            date = datetime.strptime(actual_key, "%Y-%d-%m:%H:%M:%S")
            self.date_combo_box.blockSignals(True)
            self.date_combo_box.clear()
            self.date_combo_box.addItems(
                [datetime.strptime(i, "%Y-%d-%m:%H:%M:%S").strftime("%Y/%m/%d at %Hh%M") for i in self.history_keys])
            self.date_combo_box.setCurrentText(date.strftime("%Y/%m/%d at %Hh%M"))
            self.date_combo_box.blockSignals(False)

            # tree
            self.show_experiment_titles_only(self.experiment_manager.entry_filepath)

        else:
            self.experiment_manager.entry = "default"
            self.state_manager.entry = "default"
            self.show_experiment_titles_only(None)


        # Enable and disable navigation buttons
        self.check_disable_navigation_buttons()

    def _on_date_combo_box_changed(self, index) :
        self.do_navigate(index)

    def load_history_in_dict(self) -> tuple[dict[str, str], list[str]]:
        """
        Read history file and return a dictionary with experiments and state entries sorted by date.

        Returns
        -------
        history : dict
            Dictionary where keys are datetime strings and values are dictionaries
            with 'experiment' and 'state' entries
            Example::

                {
                    '2026-18-03:17:07:38': {'experiment': 'Manip', 'state': 'default'},
                    '2026-18-03:17:06:31': {'experiment': 'default', 'state': 'default'}
                }

        history_keys : list[str]
            List of history dictionary keys sorted by descending date
        """
        try:
            history = toml.load(self.history_file_path)
        except (FileNotFoundError, PermissionError, OSError):
            history = {}

        history_keys = sorted(
            history.keys(),
            key=lambda k: datetime.strptime(k, "%Y-%d-%m:%H:%M:%S"),
            reverse=True
        )

        return history, history_keys

    def _on_history_file_modified(self):
        self.history, self.history_keys = self.load_history_in_dict()
        self.history_index = 0
        self.history_modified_sig.emit()

    def load_extension_subprocess(self, extension_name: str):
        """Launch an extension in a separate process"""
        # Validate and log the extension name
        if not extension_name or not isinstance(extension_name, str):
            error_msg = f"Invalid extension name: {extension_name} (type: {type(extension_name)})"
            logger.error(error_msg)
            print(error_msg)
            return None

        logger.info(f"Attempting to launch extension with name: '{extension_name}'")

        try:
            ext_enum = ExtensionEnum(extension_name)
            ext_class = self.extension_manager.extension_catalog[ext_enum].klass
            process = subprocess.Popen([sys.executable, '-m', ext_class.__module__])

            self.popen_with_splash([sys.executable, '-m', ext_class.__module__],
                                   f'Loading the {extension_name} extension... Please wait...',
                                   5000)

            logger.info(f"Extension '{extension_name}' successfully launched with process PID: {process.pid}")
            return process

        except ValueError as e:
            error_msg = f"Extension '{extension_name}' not found in ExtensionEnum: {e}"
            logger.error(error_msg)
            return None
        except Exception as e:
            error_msg = f"Failed to launch extension '{extension_name}': {type(e).__name__}: {e}"
            logger.error(error_msg)
            return None



def main():
    from pymodaq_gui.qt_utils import mkQApp

    app = mkQApp('Launcher')

    win = QtWidgets.QMainWindow()
    win.setWindowTitle('Launcher')

    shared_ui = SharedUI(win)
    prog = Launcher(win)
    shared_ui.affect_application(prog)

    win.resize(850, 450)

    win.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()

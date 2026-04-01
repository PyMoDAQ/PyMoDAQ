import subprocess
import sys
from datetime import datetime
from enum import StrEnum
from typing import Any, cast

from qtpy import QtCore, QtWidgets
from qtpy.QtCore import Signal, Qt
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
# Handler
from watchdog.observers import Observer

from pymodaq.dashboard import load_dashboard_with_preset
from pymodaq.extensions.daq_logger import main as logger_main
from pymodaq.utils.config import get_set_configurator_path
from pymodaq.utils.managers.configurator.configurator import Configurator
from pymodaq.utils.managers.modules.utils import ModuleType
from pymodaq.utils.shared_ui import SharedUI
from pymodaq_gui.managers.manager_base import ManagerActions
from pymodaq_gui.utils import CustomApp
from pymodaq_utils import set_logger
from pymodaq_utils.logger import get_module_name
from pymodaq_utils.utils import ThreadCommand

from pymodaq_utils.config import GlobalConfig

logger = set_logger(get_module_name(__file__))


class EnumToolTip(StrEnum):
    DASHBOARD = 'Launch an empty Dashboard without configuration'
    DAQ_VIEWER = 'Launch an empty Viewer'
    DAQ_MOVE = 'Launch an empty DAQ_Move'
    H5BROWSER = 'Launch H5Browser'
    BACK_HISTORY = 'Navigate to the back item of presets history'
    NEXT_HISTORY = 'Navigate to the next item of presets history'
    RESTORE = 'Restore this preset with the selected configurator'

class HistoryFileHandler(FileSystemEventHandler) :
    def __init__(self, callback, watched_path):
        self.callback = callback
        self.watched_path = str(watched_path)

    def on_modified(self, event: FileModifiedEvent) -> None:
        if not event.is_directory and event.src_path == self.watched_path:
            self.callback()



class Launcher(CustomApp):
    command_sig = Signal(ThreadCommand)
    history_modified_sig = Signal()
    # list of dicts enabling a settings tree on the user interface
    params = []

    def __init__(self, mainWindow, dashboard=None, history_file_name = 'history.toml'):
        super().__init__(mainWindow)

        self.dashboard = dashboard
        # init the App specific attributes
        self.raw_data = []

        # Remove the default toolbar created by CustomApp
        self.mainwindow.removeToolBar(self._toolbar)

        self.configurator = Configurator()
        self.preset_manager = self.configurator.preset_manager

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

        # Loader
        self.history_keys = []
        self.history = {}
        self.history_index = 0

        # Header
        self.box_label = QLabel("2026/03/02 at 16h45")  # debug only
        self.date_label = QLabel("Date :")

        self.history_file_name = history_file_name
        self.history_file_path = get_set_configurator_path(user=True) / self.history_file_name

        # History file handler (watchdog)
        self._handler = HistoryFileHandler(
                                            callback=self._on_history_file_modified,
                                            watched_path=self.history_file_path
                                        )
        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            path=str(self.history_file_path.parent),
            recursive=False
        )
        self._observer.start()
        self.history_modified_sig.connect(self._refresh_history_ui)

        self.setup_ui()

    def setup_actions(self):
        '''
        subclass method from ActionManager
        '''
        self.add_action('launch_dashboard', 'Launch empty dashboard', '',
                        EnumToolTip.DASHBOARD, auto_toolbar=True
                        )
        self.add_action('launch_viewer', 'Launch empy viewer', '', EnumToolTip.DAQ_VIEWER, auto_toolbar=False)
        self.add_action('launch_move', 'Launch empty DAQ move', '', EnumToolTip.DAQ_MOVE, auto_toolbar=False)
        self.add_action('launch_h5browser', 'Launch H5Browser', '', EnumToolTip.H5BROWSER, auto_toolbar=False)

        self.add_action('back_config', 'Back', 'keyboard_arrow_left', EnumToolTip.BACK_HISTORY, auto_toolbar=True,
                        toolbar='header')
        self.header_toolbar.addWidget(self.date_label)
        self.header_toolbar.addWidget(self.box_label)
        self.add_action('load_default_dashboard', 'Restore',
                        'open_in_new', EnumToolTip.RESTORE, auto_toolbar=True, toolbar='header')
        self.add_action('next_config', 'Next', 'keyboard_arrow_right', EnumToolTip.NEXT_HISTORY, auto_toolbar=True,
                        toolbar='header')

        # setup_actions is called after setup_docks; style the action button here once it exists.
        button = self.header_toolbar.widgetForAction(self.get_action('load_default_dashboard'))
        if isinstance(button, QtWidgets.QToolButton):
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

    def setup_docks(self):
        '''
        Configuration des layouts et widgets
        '''
        self.launcher_vbox.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.set_box_label_apparence()

        # Set tooltip buttons
        self.set_tooltip_button()

        # Set separator between launcher and loader
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("color: black;")

        self.main_hbox.addLayout(self.launcher_vbox)
        self.main_hbox.addWidget(separator)
        self.main_hbox.addLayout(self.loader_vbox, 1)
        self.loader_vbox.addLayout(self.hbox)
        self.loader_vbox.addWidget(self.add_toolbar('controls'))
        self.loader_vbox.layout().addWidget(self.settings_tree)

        self.preset_manager.entry = 'New '
        self.show_preset_titles_only(self.preset_manager.entry_filepath)

        self.set_launcher_vbox()

        self.set_header()
        self.set_controls()

        widget = QWidget()
        widget.setLayout(self.main_hbox)
        self.mainwindow.setCentralWidget(widget)



        logger.debug('docks are set')

    def _emit_command(self, command: str):
        cast(Any, self.command_sig).emit(ThreadCommand(command))

    def connect_things(self):
        '''
        subclass method from CustomApp
        '''
        logger.debug('connecting things')
        logger.debug('connecting done')

        self.connect_action('launch_dashboard', lambda: self.launch_empty_dashboard())
        self.connect_action('launch_viewer', lambda: self.launch_empty_viewer())
        self.connect_action('launch_move', lambda: self.launch_empty_move())
        self.connect_action('launch_h5browser', lambda: self.launch_h5browser())

        # Connect action to button
        self.dashboard_button.clicked.connect(self.get_action('launch_dashboard').trigger)
        self.viewer_button.clicked.connect(self.get_action('launch_viewer').trigger)
        self.move_button.clicked.connect(self.get_action('launch_move').trigger)
        self.h5browser_button.clicked.connect(self.get_action('launch_h5browser').trigger)

        # Header of loader section
        self.connect_action('back_config', lambda: self.do_navigate(1))
        self.connect_action('load_default_dashboard', self.load_dashboard_with_preset_configurator)
        self.connect_action('next_config', lambda: self.do_navigate(-1))
        self.preset_manager.get_action(ManagerActions.EXECUTE).setVisible(False)
        self.configurator.get_action(ManagerActions.EXECUTE).setVisible(False)

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        '''
        subclass method from CustomApp
        '''
        self.add_menu('file', 'File')

    def do_things_after_ui_setup(self):
        """Non mandatory method to be subclassed in order to do things after the UI setup
        """
        self.history, self.history_keys = self.load_history_in_dict()
        self.preset_manager.get_external_toolbar_menu(toolbar=self.get_toolbar('preset'))
        self.configurator.get_external_toolbar_menu(toolbar=self.get_toolbar('configurator'))
        self.preset_manager.enable_actions(True)
        self.preset_manager.set_action_enabled('list_entries', False)
        self.configurator.enable_actions(True)

        self.ui_refresh()

    def value_changed(self, param):
        logger.debug(f'calling value_changed with param {param.name()}')
        if param.name() == 'do_something':
            if param.value():
                self.settings.child('main_settings', 'something_done').setValue(True)
            else:
                self.settings.child('main_settings', 'something_done').setValue(False)

        logger.debug(f'Value change applied')

    def set_launcher_vbox(self):
        """ Set widgets in QVBox launcher section"""
        
        for button in [self.dashboard_button, self.viewer_button, self.move_button, self.h5browser_button]:
            button.setMinimumWidth(140)
            button.setMinimumHeight(28)
            button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            self.launcher_vbox.addWidget(button)
        
        self.launcher_vbox.addStretch(1)

        # Add a toolbar to compare button vs action approaches
        self.launcher_vbox.addWidget(self.add_toolbar('launcher'))
        self.get_toolbar('launcher').setOrientation(QtCore.Qt.Orientation.Vertical)

        self.launcher_vbox.setSpacing(10)

    def set_tooltip_button(self):
        self.dashboard_button.setToolTip(EnumToolTip.DASHBOARD)
        self.viewer_button.setToolTip(EnumToolTip.DAQ_VIEWER)
        self.move_button.setToolTip(EnumToolTip.DAQ_MOVE)
        self.h5browser_button.setToolTip(EnumToolTip.H5BROWSER)

    def set_box_label_apparence(self):
        self.box_label.setStyleSheet(
            'QLabel { border: 1px solid white; border-radius: 10px; padding: 4px 10px; }')
        self.box_label.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)

    def launch_empty_dashboard(self):
        subprocess.Popen(['dashboard'])

    def launch_empty_viewer(self):
        subprocess.Popen(['daq_viewer'])

    def launch_empty_move(self):
        subprocess.Popen(['daq_move'])

    def launch_h5browser(self):
        subprocess.Popen(['h5browser'])

    def launch_empty_logger(self):
        logger_main()

    def set_header(self):
        self.hbox.addWidget(self.add_toolbar('header', 'Header', add_break=False))
        self.header_toolbar = self.get_toolbar('header')
        # setup_docks runs before setup_actions, so the action may not exist yet.
        if self.has_action('load_default_dashboard'):
            button = self.header_toolbar.widgetForAction(self.get_action('load_default_dashboard'))
            if isinstance(button, QtWidgets.QToolButton):
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.header_toolbar.layout().setSpacing(20)

    def set_controls(self):
        self.get_toolbar('controls').addWidget(self.add_toolbar('preset', 'Preset', add_break=False))
        self.get_toolbar('controls').addWidget(self.add_toolbar('configurator', 'Configurator'))

    @staticmethod
    def _module_display_title(module_param) -> str:
        name_param = module_param.child('name')
        if name_param is not None and name_param.value() not in (None, ''):
            return str(name_param.value())

        module_title = module_param.title()
        if module_title:
            return str(module_title)

        return str(module_param.name())

    def _build_summary_group(self, preset_settings, module_type: ModuleType, group_title: str) -> dict:
        group_param = preset_settings.child(module_type.value)
        children = []

        if group_param is not None:
            for ind_module, module_param in enumerate(group_param.children()):
                children.append({
                    'title': self._module_display_title(module_param),
                    'name': f'{module_type.value}_title_{ind_module:02d}',
                    'type': 'group',
                })

        return {
            'title': group_title,
            'name': f'{module_type.value}_summary',
            'type': 'group',
            'expanded': True,
            'children': children,
        }

    def show_preset_titles_only(self, preset_source=None):
        """Load a preset source and display only module titles in settings_tree."""
        try:
            if preset_source is None:
                preset_settings = self.create_parameter(self.preset_manager.settings)
            else:
                preset_settings = self.create_parameter(preset_source)
        except Exception as error:
            logger.warning(f'Unable to load preset source {preset_source}: {error}')
            preset_settings = self.create_parameter(self.preset_manager.settings)

        self._full_preset_settings = preset_settings

        self.settings = [
            self._build_summary_group(preset_settings, ModuleType.Actuator, 'Actuators'),
            self._build_summary_group(preset_settings, ModuleType.Detector, 'Detectors'),
        ]

        self.tree.header().hide()
        self.tree.expandAll()
        self.tree.setItemsExpandable(True)


    def load_dashboard_with_preset_configurator(self):
        """
        Debug : load and show dashboard with default preset and default configurator
        Returns
        -------

        """
        self.dashboard, self._dashboard_extension, self._dashboard_shared_ui = load_dashboard_with_preset(
            preset_name=self.preset_manager.entry,
            configuration_name=self.configurator.entry,
        )
        self._dashboard_shared_ui.show()


    def do_navigate(self, offset: int):
        """
        Navigate in history items by offset.

        Parameters
        ----------
        offset : int
            Value to increment history index
        Notes
        -----
        Design by contract: caller must ensure the resulting index stays
        within valid history bounds.
        Precondition: 0 <= self.history_index + offset < len(self.history)
        """
        self.history_index += offset
        self.ui_refresh()

    def check_disable_navigation_buttons(self):
        """
        Check and disable navigation buttons :
        * back button : last item of list
        * next button : first item of list
        Returns
        -------

        """
        if self.history_index < 1 :
            self.set_action_enabled('next_config', False)
        else :
            self.set_action_enabled('next_config', True)

        if self.history_index >= len(self.history_keys) -1 :
            self.set_action_enabled('back_config', False)
        else :
            self.set_action_enabled('back_config', True)

    def ui_refresh(self):
        # preset and configurator
        if len(self.history_keys) > 0:
            actual_key = self.history_keys[self.history_index]

            self.preset_manager.entry = self.history[actual_key]['preset']
            self.configurator.preset_filename = self.preset_manager.entry
            QtWidgets.QApplication.processEvents()
            self.configurator.entry = self.history[actual_key]['configurator']

            # date label
            date = datetime.strptime(actual_key, "%Y-%d-%m:%H:%M:%S")
            self.box_label.setText(date.strftime("%Y/%m/%d at %Hh%M"))

        else:
            self.preset_manager.entry = "default"
            self.configurator.preset_filename = "default"
            self.configurator.update_entry("default")
            self.box_label.setText("-")

        # tree
        self.show_preset_titles_only(self.preset_manager.entry_filepath)

        # Enable and disable navigation buttons
        self.check_disable_navigation_buttons()

        # tree
        self.show_preset_titles_only(self.preset_manager.entry_filepath)



    def load_history_in_dict(self) -> tuple[
        dict[str, str], list[str]]:
        """
        Read history file and return a dictionary with presets and configurators sorted by date.

        Returns
        -------
        history : dict
            Dictionary where keys are datetime strings and values are dictionaries
            with 'preset' and 'configurator' entries
            Example::

                {
                    '2026-18-03:17:07:38': {'preset': 'Manip', 'configurator': 'default'},
                    '2026-18-03:17:06:31': {'preset': 'default', 'configurator': 'default'}
                }

        history_keys : list[str]
            List of history dictionary keys sorted by descending date
        """
        import tomllib
        from datetime import datetime

        if self.history_file_path.is_file():
            with open(self.history_file_path, "rb") as f:
                history = tomllib.load(f)
        else:
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

    def _refresh_history_ui(self):
        self.ui_refresh()




def main():
    from pymodaq_gui.qt_utils import mkQApp

    app = mkQApp('Launcher')

    win = QtWidgets.QMainWindow()
    win.setWindowTitle('Launcher')

    shared_ui = SharedUI(win)
    prog = Launcher(win)
    # print(prog.dashboard_button.size())
    shared_ui.affect_application(prog)

    # Calculate width and height as a screen ratio
    # screen = QApplication.screenAt(QCursor.pos())
    # size = screen.size()

    win.resize(850, 450)

    win.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()

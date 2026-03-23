from datetime import datetime
import subprocess
import sys
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

from pymodaq.dashboard import load_dashboard_with_preset
from pymodaq.extensions.daq_logger import main as logger_main
from pymodaq.utils.config import get_set_configurator_path
from pymodaq.utils.managers.modules.utils import ModuleType
from pymodaq.utils.managers.preset.preset_manager import PresetManager
from pymodaq.utils.shared_ui import SharedUI
from pymodaq_gui.utils import CustomApp
from pymodaq_utils import set_logger
from pymodaq_utils.logger import get_module_name
from pymodaq_utils.utils import ThreadCommand

logger = set_logger(get_module_name(__file__))


class EnumToolTip(StrEnum):
    DASHBOARD = 'Launch an empty Dashboard without configuration'
    VIEWER = 'Launch an empty Viewer'
    MOVE = 'Launch an empty DAQ_Move'
    H5BROWSER = 'Launch H5Browser'
    BACK_HISTORY = 'Navigate to the back item of presets history'
    NEXT_HISTORY = 'Navigate to the next item of presets history'
    RESTORE = 'Restore this preset with the selected configurator'


class Launcher(CustomApp):
    command_sig = Signal(ThreadCommand)
    # list of dicts enabling a settings tree on the user interface
    params = []

    def __init__(self, mainWindow, dashboard=None):
        super().__init__(mainWindow)
        self.dashboard = dashboard
        # init the App specific attributes
        self.raw_data = []

        # Remove the default toolbar created by CustomApp
        self.mainwindow.removeToolBar(self._toolbar)

        self.preset_manager = PresetManager()

        # Layout
        self.main_hbox = QHBoxLayout()
        self.launcher_vbox = QVBoxLayout()
        self.loader_vbox = QVBoxLayout()
        self.hbox = QHBoxLayout()

        # Launcher
        self.dashboard_button = QPushButton("Dashboard")
        self.viewer_button = QPushButton("Viewer")
        self.move_button = QPushButton("Move")
        self.h5browser_button = QPushButton("H5Browser")

        # Loader
        self.history_keys = []
        self.history = {}
        self.history_index = 0

        self.preset_name = ""
        self.configurator_name = ""

        self.preset_configurator_layout = QHBoxLayout()
        self.preset_label = QLabel("Preset :")
        self.preset_label_value = QLabel(self.preset_name)
        self.configurator_label = QLabel("Configurator :")
        self.configurator_label_value = QLabel(self.configurator_name) # combo box for the future


        # Header
        self.box_label = QLabel("2026/03/02 at 16h45")  # debug only
        self.date_label = QLabel("Date :")

        self.setup_ui()

    def setup_actions(self):
        '''
        subclass method from ActionManager
        '''
        self.add_action('launch_dashboard', 'Launch empty dashboard', '',
                        EnumToolTip.DASHBOARD, auto_toolbar=True,
                        toolbar='launcher')
        self.add_action('launch_viewer', 'Launch empy viewer', '', EnumToolTip.VIEWER, auto_toolbar=False)
        self.add_action('launch_move', 'Launch empty DAQ move', '', EnumToolTip.MOVE, auto_toolbar=False)
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
        self.loader_vbox.addLayout(self.preset_configurator_layout)
        self.loader_vbox.layout().addWidget(self.settings_tree)

        self.preset_manager.entry = 'New '
        self.show_preset_titles_only(self.preset_manager.entry_filepath)

        self.set_launcher_vbox()
        self.preset_configurator_layout.addWidget(self.preset_label)
        self.preset_configurator_layout.addWidget(self.preset_label_value)
        self.preset_configurator_layout.addWidget(self.configurator_label)
        self.preset_configurator_layout.addWidget(self.configurator_label_value)

        self.set_header()


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
        self.connect_action('back_config', lambda: self.do_back())
        self.connect_action('load_default_dashboard', lambda: self.load_dashboard_with_preset_configurator())
        self.connect_action('next_config', lambda: self.do_next())

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        '''
        subclass method from CustomApp
        '''
        self.add_menu('file', 'File')

    def do_things_after_ui_setup(self):
        """Non mandatory method to be subclassed in order to do things after the UI setup
        """
        self.history, self.history_keys = self.load_history_in_dict()
        self.ui_refresh()
        self.check_disable_navigation_buttons()

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
        self.launcher_vbox.addWidget(self.dashboard_button)
        self.launcher_vbox.addWidget(self.viewer_button)
        self.launcher_vbox.addWidget(self.move_button)
        self.launcher_vbox.addWidget(self.h5browser_button)
        self.launcher_vbox.addStretch(1)

        # Add a toolbar to compare button vs action approaches
        self.launcher_vbox.addWidget(self.add_toolbar('launcher'))
        self.get_toolbar('launcher').setOrientation(QtCore.Qt.Orientation.Vertical)

    def set_tooltip_button(self):
        self.dashboard_button.setToolTip(EnumToolTip.DASHBOARD)
        self.viewer_button.setToolTip(EnumToolTip.VIEWER)
        self.move_button.setToolTip(EnumToolTip.MOVE)
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

    def load_dashboard_with_preset_configurator(self, preset: str = 'default', configurator: str = 'default'):
        """
        Debug : load and show dashboard with default preset and default configurator
        Returns
        -------

        """
        self.dashboard, self._dashboard_extension, self._dashboard_shared_ui = load_dashboard_with_preset(
            preset_name=self.preset_name,
            configuration_name=self.configurator_name,
        )
        # Ensure close triggers object deletion so we can react on destroyed.
        self._dashboard_shared_ui.mainwindow.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._dashboard_shared_ui.mainwindow.destroyed.connect(self._refresh_after_dashboard_close)
        self._dashboard_shared_ui.show()

    def _refresh_after_dashboard_close(self):
        """Reload history and refresh launcher widgets once the dashboard window is closed."""
        self.history, self.history_keys = self.load_history_in_dict()
        if not self.history_keys:
            self.preset_name = ''
            self.configurator_name = ''
            self.box_label.setText('')
            self.preset_label_value.setText(self.preset_name)
            self.configurator_label_value.setText(self.configurator_name)
            self.check_disable_navigation_buttons()
            return

        self.history_index = 0
        self.ui_refresh()
        self.check_disable_navigation_buttons()
        

    def do_back(self):
        """
        Navigate in the next configuration
        Returns
        -------

        """
        print("do_next() method called")
        self.history_index +=1
        self.ui_refresh()
        self.check_disable_navigation_buttons()

    def do_next(self):
        """
        Navigate in the back configuration
        Returns
        -------

        """
        print("do_back() method called")
        self.history_index -= 1
        self.ui_refresh()
        self.check_disable_navigation_buttons()

    def check_disable_navigation_buttons(self):
        """
        Check and disable navigation buttons :
        * back button : last item of list
        * next button : first item of list
        Returns
        -------

        """
        if self.history_index < 1 :
            self.get_action('next_config').setDisabled(True)
        else :
            self.get_action('next_config').setDisabled(False)

        if self.history_index >= len(self.history_keys) -1 :
            self.get_action('back_config').setDisabled(True)
        else :
            self.get_action('back_config').setDisabled(False)

    def ui_refresh(self):
        # preset and configurator
        if len(self.history_keys) > 0 :
            actual_key = self.history_keys[self.history_index]
            self.preset_name = self.history[actual_key]['preset']
            self.configurator_name = self.history[actual_key]['configurator']

            # date label
            date = datetime.strptime(actual_key, "%Y-%d-%m:%H:%M:%S")
            self.box_label.setText(date.strftime("%Y/%m/%d at %Hh%M"))

        else :
            self.preset_name = "default"
            self.configurator_name = "default"
            self.box_label.setText("-")

        # preset and configurator labels
        self.preset_label_value.setText(self.preset_name)
        self.configurator_label_value.setText(self.configurator_name)

        # tree



    def load_history_in_dict(self, name_history_file: str = 'history.toml') -> tuple[
        dict[str, str], list[str]]:
        """
        Read history file and return a dictionary with presets and configurators sorted by date.

        Parameters
        ----------
        name_history_file : str, optional
            Name of the history file.

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

        history_path = get_set_configurator_path(user=True) / name_history_file

        if history_path.is_file():
            with open(history_path, "rb") as f:
                history = tomllib.load(f)
        else:
            history = {}

        history_keys = sorted(
            history.keys(),
            key=lambda k: datetime.strptime(k, "%Y-%d-%m:%H:%M:%S"),
            reverse=True
        )

        return history, history_keys


def main():
    from pymodaq_gui.qt_utils import mkQApp

    app = mkQApp('Launcher')

    fen = QtWidgets.QMainWindow()
    fen.setWindowTitle('Launcher')

    shared_ui = SharedUI(fen)
    prog = Launcher(fen)
    shared_ui.affect_application(prog)
    history, history_keys = prog.load_history_in_dict()
    print(f"History : \n{history}")
    print(f"Keys : \n{history_keys}")

    # Calculate width and height as a screen ratio
    # screen = QApplication.screenAt(QCursor.pos())
    # size = screen.size()

    fen.resize(800, 400)

    fen.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()

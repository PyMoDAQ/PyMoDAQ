import subprocess
import sys
import time

from enum import Enum

from qtpy.QtWidgets import QMessageBox
from pymodaq_plugin_manager.manager import PluginManager
from qtpy import QtCore, QtWidgets
from qtpy.QtCore import QDate, Signal
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListView,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pymodaq.dashboard import DashBoard
from pymodaq_gui.utils import CustomApp
from pymodaq_gui import config, logger
from pymodaq.utils.shared_ui import SharedUI
from pymodaq_utils.utils import ThreadCommand
from typing import Any, cast

from pymodaq.control_modules.daq_viewer import main as viewer_main
from pymodaq.control_modules.daq_move import main as move_main
from pymodaq.extensions.daq_logger import main as logger_main
#from tests.extensions.extension_loading_test import dashboard


class EnumToolTip(Enum) :
    DASHBOARD = 'Launch an empty Dashboard without configuration'
    VIEWER = 'Launch an empty Viewer'
    MOVE = 'Launch an empty DAQ_Move'
    H5BROWSER = 'Launch H5Browser'
    PLUGIN_MANAGER = 'Open plugin manager'

class Launcher(CustomApp):
    command_sig = Signal(ThreadCommand)
    # list of dicts enabling a settings tree on the user interface
    params = [
        {'title': 'Main settings:', 'name': 'main_settings', 'type': 'group', 'children': [
            {'title': 'Save base path:', 'name': 'base_path', 'type': 'browsepath',
             'value': config('data', 'data_saving', 'h5file', 'save_path')},
            {'title': 'File name:', 'name': 'target_filename', 'type': 'str', 'value': "", 'readonly': True},
            {'title': 'Date:', 'name': 'date', 'type': 'date', 'value': QDate.currentDate()},
            {'title': 'Do something, such as showing data:', 'name': 'do_something', 'type': 'bool', 'value': False},
            {'title': 'Something done:', 'name': 'something_done', 'type': 'bool', 'value': False, 'readonly': True},
        ]},
    ]

    def __init__(self, mainWindow, dashboard=None):
        super().__init__(mainWindow)
        self.dashboard = dashboard
        # init the App specific attributes
        self.raw_data = []

        # Layout
        self.main_HBox = QHBoxLayout()
        self.launcher_VBox = QVBoxLayout()
        self.loader_VBox = QVBoxLayout()
        self.header_HBox = QHBoxLayout()

        # Launcher
        self.dashboard_button = QPushButton("Dashboard")
        self.viewer_button = QPushButton("Viewer")
        self.move_button = QPushButton("Move")
        self.plugin_manager_button = QPushButton("Plugin manager")
        self.h5browser_button = QPushButton("H5Browser")

        # Loader
        self.listView = QListView()

        # Header
        self.box_label = QLabel("2026/03/02 at 16h45")
        self.back_button = QPushButton("←")
        self.next_button = QPushButton("→")
        self.date_label = QLabel("Date :")
        self.launch_button = QPushButton("Launch")

        self.setup_ui()

    def setup_actions(self):
        '''
        subclass method from ActionManager
        '''
        self.add_action('quit', 'Quit', 'close2', "Quit program", toolbar=self.toolbar)
        self.add_action('grab', 'Grab', 'camera', "Grab from camera", checkable=True, toolbar=self.toolbar)
        self.add_action('launch_dashboard', 'Launch empty dashboard', '', EnumToolTip.DASHBOARD.value)
        self.add_action('launch_viewer', 'Launch empy viewer', '', EnumToolTip.VIEWER.value)
        self.add_action('launch_move', 'Launch empty DAQ move', '', EnumToolTip.MOVE.value)
        self.add_action('launch_h5browser', 'Launch H5Browser', '', EnumToolTip.H5BROWSER.value)
        self.add_action('launch_plugin_manager', 'Open the plugin manager', '',EnumToolTip.PLUGIN_MANAGER.value)



    def setup_docks(self):
        '''
        Configuration des layouts et widgets
        '''
        self.launcher_VBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.box_label.setStyleSheet(
            'QLabel { border: 1px solid white; border-radius: 10px; padding: 4px 10px; }')
        self.box_label.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)

        # Set tooltips button
        self.dashboard_button.setToolTip(EnumToolTip.DASHBOARD.value)
        self.viewer_button.setToolTip(EnumToolTip.VIEWER.value)
        self.move_button.setToolTip(EnumToolTip.MOVE.value)
        self.h5browser_button.setToolTip(EnumToolTip.H5BROWSER.value)
        self.plugin_manager_button.setToolTip(EnumToolTip.PLUGIN_MANAGER.value)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("color: black;")

        self.main_HBox.addLayout(self.launcher_VBox)
        self.main_HBox.addWidget(separator)
        self.main_HBox.addLayout(self.loader_VBox, 1)
        self.loader_VBox.addLayout(self.header_HBox)

        self.launcher_VBox.addWidget(self.dashboard_button)
        self.launcher_VBox.addWidget(self.viewer_button)
        self.launcher_VBox.addWidget(self.move_button)
        self.launcher_VBox.addWidget(self.h5browser_button)
        self.launcher_VBox.addWidget(self.plugin_manager_button)
        self.launcher_VBox.addStretch(1)

        self.header_HBox.addWidget(self.back_button)
        self.header_HBox.addWidget(self.date_label)
        self.header_HBox.addWidget(self.box_label)
        self.header_HBox.addStretch(1)
        self.header_HBox.addWidget(self.launch_button)
        self.header_HBox.addWidget(self.next_button)

        self.loader_VBox.addWidget(self.listView)

        widget = QWidget()
        widget.setLayout(self.main_HBox)
        self.mainwindow.setCentralWidget(widget)

        logger.debug('docks are set')

    def _emit_command(self, command: str):
        cast(Any, self.command_sig).emit(ThreadCommand(command))

    def connect_things(self):
        '''
        subclass method from CustomApp
        '''
        logger.debug('connecting things')
        # self.actions['quit'].connect(self.quit_fun)
        logger.debug('connecting done')

        self.connect_action('launch_dashboard', lambda: self.launch_empty_dashboard())
        self.connect_action('launch_viewer', lambda: self.launch_empty_viewer())
        self.connect_action('launch_move', lambda: self.launch_empty_move())
        self.connect_action('launch_h5browser', lambda: self.launch_h5browser())
        self.connect_action('launch_plugin_manager', lambda: self.start_plugin_manager())

        # Connect action to button
        self.dashboard_button.clicked.connect(self.get_action('launch_dashboard').trigger)
        self.viewer_button.clicked.connect(self.get_action('launch_viewer').trigger)
        self.move_button.clicked.connect(self.get_action('launch_move').trigger)
        self.h5browser_button.clicked.connect(self.get_action('launch_h5browser').trigger)
        self.plugin_manager_button.clicked.connect(self.get_action('launch_plugin_manager').trigger)


    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        '''
        subclass method from CustomApp
        '''
        logger.debug('settings menu')
        if menubar is None:
            menubar = self.mainwindow.menuBar()
        file_menu = menubar.addMenu('File')
        self.affect_to('quit', file_menu)
        file_menu.addSeparator()
        logger.debug('menu set')

    def value_changed(self, param):
        logger.debug(f'calling value_changed with param {param.name()}')
        if param.name() == 'do_something':
            if param.value():
                self.settings.child('main_settings', 'something_done').setValue(True)
            else:
                self.settings.child('main_settings', 'something_done').setValue(False)

        # if isinstance(self.dashboard, DashBoard) :
        #     self.dashboard_button.setStyleSheet("background-color: blue")

        logger.debug(f'Value change applied')



    def start_plugin_manager(self):
        self.win_plug_manager = QtWidgets.QMainWindow()
        self.win_plug_manager.setWindowTitle("PyMoDAQ Plugin Manager")
        widget = QtWidgets.QWidget()
        self.win_plug_manager.setCentralWidget(widget)
        self.plugin_manager = PluginManager(widget)
        self.plugin_manager.quit_signal.connect(self.quit_fun)
        self.plugin_manager.restart_signal.connect(self.restart_fun)
        self.win_plug_manager.show()

    def restart_fun(self, ask=False):
        ret = False
        if ask:
            mssg = QMessageBox()
            mssg.setText(
                "You have to restart the application to take the"
                " modifications into account!"
            )
            mssg.setInformativeText("Do you want to restart?")
            mssg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            ret = mssg.exec()

        if ret == QMessageBox.StandardButton.Ok or not ask:
            self.quit_fun()
            subprocess.call([sys.executable, str(self._app_class_file)])

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




def main() :
    from pymodaq_gui.qt_utils import mkQApp

    app = mkQApp('Launcher')

    fen = QtWidgets.QMainWindow()
    fen.setWindowTitle('Launcher')

    shared_ui = SharedUI(fen)
    prog = Launcher(fen)
    shared_ui.affect_application(prog)

    fen.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()

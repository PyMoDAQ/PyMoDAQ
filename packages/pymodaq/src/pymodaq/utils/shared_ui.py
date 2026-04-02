#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
import logging
from packaging import version as version_mod
import subprocess
import sys
from typing import Optional, Union, Any

from qtpy import QtGui, QtWidgets, QtCore
from qtpy.QtCore import Qt, QThread, Signal, QSize
from qtpy.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QMessageBox,
)
from time import perf_counter
import numpy as np

from pymodaq_plugin_manager.manager import PluginManager
from pymodaq_plugin_manager.validate import get_pypi_pymodaq

from pymodaq_gui.managers.action_manager import QAction
from pymodaq_gui.utils import DockArea
from pymodaq_utils.enums import StrEnum
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import get_version
from pymodaq_utils.config import GlobalConfig as Config
from pymodaq.utils.leco.utils import start_coordinator
from pymodaq_utils.utils import get_module_path
from pymodaq_gui.utils.custom_app import CustomApp

from pymodaq_gui.shared_ui import SharedUI, MenuNames

logger = set_logger(get_module_name(__file__))

config =  Config()


class SharedUI(SharedUI):
    """ This class is a UI wrapper that incorporates all base functionalities one want in a
    main PyMoDAQ app including default menu and toolbar with settings, log, help... shortcuts

    Parameters:
    -----------
    app: CustomApp
        The wrapped application
    widget: QWidget, DockArea
        parent of the wrapped app eg stand alone DAQ_Move, Viewer, Browser DashBoard...
        if None, uses app.parent

    The second argument is the module file path from where the app has been launched: allows simple restart
    """


    def setup_actions(self):

        super().setup_actions()

        self.add_action("leco", "Run Leco Coordinator", "", "Run a Coordinator on this localhost",
                        auto_toolbar=False)
        self.add_action("plugin_manager", "Plugin Manager", 'extension', tip='Opens the Plugin Manager',
                        auto_toolbar=False)

    def connect_things(self):
        super().connect_things()

        self.connect_action("leco", start_coordinator)
        self.connect_action("plugin_manager", self.start_plugin_manager)

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        """
        Create the menubar object looking like :
        """
        super().setup_menu(menubar=menubar)
        self.get_menu(MenuNames.SETTINGS).addAction(self.get_action("leco"))
        self.get_menu(MenuNames.HELP).addAction(self.get_action("plugin_manager"))

    def start_plugin_manager(self):
        self.win_plug_manager = QtWidgets.QMainWindow()
        self.win_plug_manager.setWindowTitle("PyMoDAQ Plugin Manager")
        widget = QtWidgets.QWidget()
        self.win_plug_manager.setCentralWidget(widget)
        self.plugin_manager = PluginManager(widget)
        self.plugin_manager.quit_signal.connect(self.quit_fun)
        self.plugin_manager.restart_signal.connect(self.restart_fun)
        self.win_plug_manager.show()

    def setup_docks(self):
       super().setup_docks()

    def check_update(self, show=True):
        try:
            packages = ["pymodaq_utils", "pymodaq_data", "pymodaq_gui", "pymodaq"]
            current_versions = [version_mod.parse(get_version(p)) for p in packages]
            available_versions = [
                version_mod.parse(get_pypi_pymodaq(p)["version"]) for p in packages
            ]
            new_versions = np.greater(available_versions, current_versions)
            # Combine package and version information and select only the ones with a newer version available

            packages_data = np.array(
                list(zip(packages, current_versions, available_versions))
            )[new_versions]

            if len(packages_data) > 0:
                # Create a QDialog window and different graphical components
                dialog = QtWidgets.QDialog()
                dialog.setWindowTitle("Update check")

                vlayout = QtWidgets.QVBoxLayout()

                message_label = QLabel(
                    "New versions of PyMoDAQ packages available!\nUse your package manager to update."
                )
                message_label.setAlignment(Qt.AlignCenter)

                table = PymodaqUpdateTableWidget()
                table.setRowCount(len(packages_data))
                table.setColumnCount(3)
                table.setHorizontalHeaderLabels(
                    ["Package", "Current version", "New version"]
                )

                for p in packages_data:
                    table.append_row(p[0], p[1], p[2])

                # The vlayout contains the message, the table and the buttons
                # and is connected to the dialog window
                vlayout.addWidget(message_label)
                vlayout.addWidget(table)
                dialog.setLayout(vlayout)

                ret = dialog.exec()

            else:
                if show:
                    msgBox = QMessageBox()
                    msgBox.setWindowTitle("Update check")
                    msgBox.setText("Everything is up to date!")
                    ret = msgBox.exec()
        except Exception as e:
            logger.exception("Error while checking the available PyMoDAQ version")

        return False



def main():
    from pymodaq_gui.qt_utils import mkQApp
    app = mkQApp('CommonWindow')

    win = QtWidgets.QMainWindow()
    win.resize(1000, 500)
    win.setWindowTitle("PyMoDAQ Dashboard")
    window = SharedUI(win)

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

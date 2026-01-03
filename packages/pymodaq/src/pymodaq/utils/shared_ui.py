#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
import logging
from packaging import version as version_mod
import subprocess
import sys
from typing import Optional, Union

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

from pymodaq_gui.utils import DockArea
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import get_version
from pymodaq_utils import config as configmod
from pymodaq.utils.leco.utils import start_coordinator
from pymodaq.utils.config import Config as ControlModulesConfig

from pymodaq_gui.utils.custom_app import CustomApp
from pymodaq_gui.utils.splash import get_splash_sc


logger = set_logger(get_module_name(__file__))

config_utils = configmod.Config()
config = ControlModulesConfig()


class PymodaqUpdateTableWidget(QTableWidget):
    """
    A class to represent PyMoDAQ and its subpackages'
    available updates as a table.
    """

    def __init__(self):
        super().__init__()
        self._row = 0

    def setHorizontalHeaderLabels(self, labels):
        super().setHorizontalHeaderLabels(labels)
        self.setColumnCount(len(labels))

    def append_row(self, package, current_version, available_version):
        # Add labels
        self.setItem(self._row, 0, QTableWidgetItem(str(package)))
        self.setItem(self._row, 1, QTableWidgetItem(str(current_version)))
        self.setItem(self._row, 2, QTableWidgetItem(str(available_version)))

        self._row += 1

    def sizeHint(self):
        self.resizeColumnsToContents()
        self.resizeRowsToContents()

        # Compute the size to adapt the window (header + borders + sum of all the elements)
        width = (
            self.verticalHeader().width()
            + self.frameWidth() * 2
            + sum([self.columnWidth(i) for i in range(self.columnCount())])
        )

        height = (
            self.horizontalHeader().height()
            + self.frameWidth() * 2
            + sum([self.rowHeight(i) for i in range(self.rowCount())])
        )

        return QSize(width, height)


class SharedUI(CustomApp):
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

    def __init__(self, app: CustomApp, widget: Union[QtWidgets.QWidget, DockArea] = None,
                 app_class_file: Union[Path, str] = None):
        self.app = app
        if widget is None:
            widget = app.parent
        if isinstance(widget, QtWidgets.QMainWindow):
            parent = widget
            self.central_widget = widget.centralWidget()
        else:
            parent = QtWidgets.QMainWindow()
            parent.setCentralWidget(widget)
            self.central_widget = widget
        super().__init__(parent)
        self.app_class_file = app_class_file

        self._splash_sc: Optional[QtWidgets.QSplashScreen] = None

        self.setup_ui()
        self.mainwindow.setVisible(True)

    def show(self):
        self.mainwindow.show()

    @property
    def splash_sc(self) -> QtWidgets.QSplashScreen:
        if not hasattr(self, "_splash_sc") or self._splash_sc is None:
            self._splash_sc = get_splash_sc()
        return self._splash_sc

    def setup_actions(self):
        self.add_action(
            "log", "Log File", "", "Show Log File in default editor", auto_toolbar=False
        )
        self.add_action("quit", "Quit", "close2", "Quit program")

        self.toolbar.addSeparator()

        self.add_action("config_utils", "Utils Config.", "tree", tip="Show utility configuration file",)
        self.add_action("config", "Controls/Extensions Config.", "tree",
                        tip="Show Control Modules and Extensions configuration file",)
        self.add_action( "restart", "Restart", "", "Restart the Dashboard", auto_toolbar=False)
        self.add_action("leco", "Run Leco Coordinator", "", "Run a Coordinator on this localhost",
                        auto_toolbar=False,)
        self.add_action("about", "About", "information2")
        self.add_action("help", "Help", "help1")
        self.get_action("help").setShortcut(QtGui.QKeySequence("F1"))
        self.add_action("check_update", "Check Updates", "", auto_toolbar=False)
        self.toolbar.addSeparator()
        self.add_action("plugin_manager", "Plugin Manager", "")

    def connect_things(self):
        self.connect_action("log", self.show_log)
        self.connect_action("config_utils", lambda: self.show_config(config_utils))
        self.connect_action("config", lambda: self.show_config(config))
        self.connect_action("quit", self.quit_fun)
        self.connect_action("restart", self.restart_fun)
        self.connect_action("leco", start_coordinator)

        self.connect_action("about", self.show_about)
        self.connect_action("help", self.show_help)
        self.connect_action("check_update", lambda: self.check_update(True))
        self.connect_action("plugin_manager", self.start_plugin_manager)

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        """
        Create the menubar object looking like :
        """
       # menubar.clear()

        # %% create Settings menu
        self.file_menu = QtWidgets.QMenu("File")
        self.file_menu.addAction(self.get_action("log"))
        self.file_menu.addAction(self.get_action("config_utils"))
        self.file_menu.addAction(self.get_action("config"))
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.get_action("quit"))
        self.file_menu.addAction(self.get_action("restart"))

        self.settings_menu = QtWidgets.QMenu("Settings")
        self.settings_menu.addAction(self.get_action("leco"))

        menus = self.menubar.actions()
        for menu in (self.file_menu, self.settings_menu):
            if len(menus) > 0:
                self.menubar.insertMenu(menus[0], menu)
            else:
                self.menubar.addMenu(self.menu)

        # help menu
        help_menu = menubar.addMenu("?")
        help_menu.addAction(self.get_action("about"))
        help_menu.addAction(self.get_action("help"))
        help_menu.addSeparator()
        help_menu.addAction(self.get_action("check_update"))
        help_menu.addAction(self.get_action("plugin_manager"))

        self.file_menu.setEnabled(True)
        self.settings_menu.setEnabled(True)

    def start_plugin_manager(self):
        self.win_plug_manager = QtWidgets.QMainWindow()
        self.win_plug_manager.setWindowTitle("PyMoDAQ Plugin Manager")
        widget = QtWidgets.QWidget()
        self.win_plug_manager.setCentralWidget(widget)
        self.plugin_manager = PluginManager(widget)
        self.plugin_manager.quit_signal.connect(self.quit_fun)
        self.plugin_manager.restart_signal.connect(self.restart_fun)
        self.win_plug_manager.show()

    def quit_fun(self):
        """
        Quit the current instance of DashBoard and close on cascade move and detector modules.

        See Also
        --------
        quit_fun
        """
        try:
            self.app.quit_fun()
            QtWidgets.QApplication.processEvents()

            if hasattr(self, "mainwindow"):
                self.mainwindow.close()

        except Exception as e:
            logger.exception(str(e))

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
            subprocess.call([sys.executable, self.app_class_file])

    def show_log(self):
        import webbrowser

        webbrowser.open(logging.getLogger("pymodaq").handlers[0].baseFilename)

    def show_config(self, config):
        from pymodaq_gui.utils.widgets.tree_toml import TreeFromToml

        config_tree = TreeFromToml(config)
        config_tree.show_dialog()

    def setup_docks(self):
       pass

    def add_toolbar(self, short_name: str, title: str = '',
                    toolbar: QtWidgets.QToolBar = None,
                    area = QtCore.Qt.ToolBarArea.TopToolBarArea, add_break=True) -> QtWidgets.QToolBar:
        return super().add_toolbar(short_name, title, self.mainwindow,
                                   toolbar, area, add_break)

    @property
    def menubar(self):
        return self._menubar

    def show_about(self):
        self.splash_sc.setVisible(True)
        self.splash_sc.showMessage(
            f"PyMoDAQ version {get_version('pymodaq')}\n"
            f"Modular Acquisition with Python\n"
            f"Written by Sébastien Weber"
        )

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

    def show_help(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("http://pymodaq.cnrs.fr"))


def main():
    from pymodaq_gui.utils.utils import mkQApp
    app = mkQApp('CommonWindow')

    win = QtWidgets.QMainWindow()
    win.resize(1000, 500)
    win.setWindowTitle("PyMoDAQ Dashboard")
    window = SharedUI(win)

    # Run application
    app.exec()


if __name__ == "__main__":
    main()

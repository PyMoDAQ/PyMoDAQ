#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
import logging
from packaging import version as version_mod
import subprocess
import sys
from typing import Union, Any

from qtpy import QtGui, QtWidgets, QtCore
from qtpy.QtCore import Qt, QSize
from qtpy.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QMessageBox,
)
import numpy as np

from pymodaq_utils.packages import get_pypi_pymodaq

from pymodaq_gui.utils.widgets.window import make_window
from pymodaq_gui.utils import DockArea
from pymodaq_utils.enums import StrEnum
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.utils import get_version
from pymodaq_utils.config import GlobalConfig as Config
from pymodaq_utils.utils import get_module_path
from pymodaq_gui.utils.custom_app import CustomApp
from pymodaq_gui.utils.menu_utils import StickyMenu


logger = set_logger(get_module_name(__file__))

config = Config()


class MenuToolbarNames(StrEnum):
    FILE = 'file'
    SETTINGS = 'settings'
    VIEW = 'view'
    TOOLS = 'tools'
    TOOLBARS = 'toolbars'
    HELP = 'help'
    RUNTIME = 'runtime'


class PymodaqUpdateTableWidget(QTableWidget):
    """
    A class to represent PyMoDAQ and its subpackages available updates as a table.
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
    widget: QMainWindow, QWidget, DockArea
        parent of the wrapped app eg stand alone DAQ_Move, Viewer, Browser DashBoard...
        if None, uses app.parent

    The second argument is the module file path from where the app has been launched: allows simple restart
    """

    def __init__(self, widget: Union[QtWidgets.QWidget, DockArea],
                 show=True, title: str = None):

        if isinstance(widget, QtWidgets.QMainWindow):
            parent = widget
            self.central_widget = widget.centralWidget()
        else:
            parent = QtWidgets.QMainWindow()
            parent.setCentralWidget(widget)
            self.central_widget = widget

        super().__init__(parent, title=title,
                         create_app_toolbar=False)


        self._app_class_file: Union[str, Path] = None
        self._main_application: Union[CustomApp, Any] = None

        self.setup_ui()
        self.mainwindow.setVisible(show)

    def affect_application(self, app: CustomApp):
        """ Affect the given application to this SharedUI and add the App QMenus to the
        QMainWindow menubar reordering/merging them if necessary
        """
        self._app_class_file = get_module_path(app.__module__)
        self._main_application = app
        self.title = app.title

        #handle menus and merge them if necessary
        menus_dict = dict(zip([menu.title() for menu in self.menus], self.menus))
        if isinstance(app, CustomApp):
            for menu in app.menus:
                if menu.title() in menus_dict:  # two  menus with identical names (titles)
                    self._merge_menus(menu, menus_dict[menu.title()])
                elif menu.parent() == app.menubar:
                    self.menubar.insertMenu(self.get_menu(MenuToolbarNames.HELP).menuAction(),
                                            menu)
                else:
                    pass

        for toolbar in app.toolbars:
            self.get_menu(MenuToolbarNames.TOOLBARS).addAction(toolbar.toggleViewAction())

    def _merge_menus(self, menu_to_merge: QtWidgets.QMenu, menu: QtWidgets.QMenu):
        menu.insertActions(menu.actions()[0], menu_to_merge.actions())
        menu_to_merge.parent().removeAction(menu_to_merge.menuAction())

    @staticmethod
    def _get_menus_from_widget(widget: QtWidgets.QWidget) -> list[QtWidgets.QMenu]:
        menus = []
        for child in widget.children():
            if isinstance(child, QtWidgets.QMenu):
                menus.append(child)
        return menus

    def show(self, show=True):
        if show:
            self.mainwindow.show()
        else:
            self.hide()

    def hide(self):
        self.mainwindow.setVisible(False)

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        """
        Create the menubar object and toolbars:
        """

        if menubar is None:
            menubar = self.menubar

        runtime_toolbar = self.add_toolbar(MenuToolbarNames.RUNTIME, 'Runtime', parent=self.mainwindow, add_break=False)
        runtime_toolbar.setMovable(False)

        help_toolbar = self.add_toolbar(MenuToolbarNames.HELP, 'Help', parent=self.mainwindow, add_break=False)
        help_toolbar.setVisible(False)

        # File menu
        self.add_menu(MenuToolbarNames.FILE, MenuToolbarNames.FILE.capitalize(), parent_menu=menubar)
        self.get_menu(MenuToolbarNames.FILE).addSeparator()

        # View menu
        self.add_menu(MenuToolbarNames.VIEW, MenuToolbarNames.VIEW.capitalize(), parent_menu=menubar)
        self.get_menu(MenuToolbarNames.VIEW).addSeparator()

        self.add_menu(MenuToolbarNames.TOOLBARS, MenuToolbarNames.TOOLBARS.capitalize(), parent_menu=MenuToolbarNames.VIEW,
                      menu=StickyMenu())

        # Tools menu
        self.add_menu(MenuToolbarNames.TOOLS, MenuToolbarNames.TOOLS.capitalize(), parent_menu=menubar)
        self.get_menu(MenuToolbarNames.TOOLS).addSeparator()

        # Help menu
        self.add_menu(MenuToolbarNames.HELP, MenuToolbarNames.HELP.capitalize(), parent_menu=menubar)


    def setup_actions(self):

        # File menu
        self.add_action(short_name="restart", name="Restart", icon_name="restart_alt",
                        tip="Restart PyMoDAQ", auto_toolbar=False, menu=MenuToolbarNames.FILE)

        self.add_action(short_name="quit", name="Quit", icon_name="cancel",
                        tip="Quit PyMoDAQ", icon_color=self.get_theme().red, toolbar=MenuToolbarNames.RUNTIME,
                        menu=MenuToolbarNames.FILE)

        # Tools menu
        self.add_action(short_name="logs", name="Logs", icon_name="description",
                        tip="Open logs file", auto_toolbar=False, menu=MenuToolbarNames.TOOLS)

        self.add_action(short_name="preferences", name="Preferences", icon_name="handyman",
                        tip="PyMoDAQ preferences", toolbar=MenuToolbarNames.HELP, menu=MenuToolbarNames.TOOLS)

        # Help menu
        self.add_action(short_name="documentation", name="Documentation", icon_name="language",
                        tip="Online documentation", toolbar=MenuToolbarNames.HELP, menu=MenuToolbarNames.HELP)

        self.get_action("documentation").setShortcut(QtGui.QKeySequence("F1"))

        self.get_menu(MenuToolbarNames.HELP).addSeparator()

        self.add_action(short_name="check_updates", name="Check updates", icon_name="update",
                        auto_toolbar=False, menu=MenuToolbarNames.HELP)

        self.add_action(short_name="about", name="About PyMoDAQ", icon_name="info",
                        icon_color=self.get_theme().blue, toolbar=MenuToolbarNames.HELP, menu=MenuToolbarNames.HELP)

        for toolbar in self.toolbars:
            self.get_menu(MenuToolbarNames.TOOLBARS).addAction(toolbar.toggleViewAction())

    def connect_things(self):
        self.connect_action("logs", self.show_log)
        self.connect_action("preferences", lambda: self.show_config(config))
        self.connect_action("quit", self.quit_fun)
        self.connect_action("restart", self.restart_fun)

        self.connect_action("about", self.show_about)
        self.connect_action("documentation", self.show_help)
        self.connect_action("check_updates", lambda: self.check_update(True))

    def quit_fun(self):
        """
        Quit the current instance of DashBoard and close on cascade move and detector modules.

        See Also
        --------
        quit_fun
        """
        try:
            if hasattr(self._main_application, 'quit_fun'):
                self._main_application.quit_fun()
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
                " modifications into account!",
            )
            mssg.setInformativeText("Do you want to restart?")
            mssg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            ret = mssg.exec()

        if ret == QMessageBox.StandardButton.Ok or not ask:
            self.quit_fun()
            subprocess.call([sys.executable, str(self._app_class_file)])

    def show_log(self):
        import webbrowser
        webbrowser.open(logging.getLogger("pymodaq").handlers[0].baseFilename)

    def show_config(self, config):
        from pymodaq_gui.utils.widgets.tree_toml import TreeFromToml

        config_tree = TreeFromToml(config)
        res = config_tree.show_dialog()
        if res and hasattr(self._main_application, 'config_changed'):
                self._main_application.config_changed.emit()

    def setup_docks_and_widgets(self):
       pass

    def show_about(self):
        self.splash_sc.setVisible(True)
        self.splash_sc.showMessage(
            f"PyMoDAQ version {get_version('pymodaq')}\n"
            f"Modular Acquisition with Python\n"
            f"Written by Sébastien Weber",
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
                list(zip(packages, current_versions, available_versions)),
            )[new_versions]

            if len(packages_data) > 0:
                # Create a QDialog window and different graphical components
                dialog = QtWidgets.QDialog()
                dialog.setWindowTitle("Update check")

                vlayout = QtWidgets.QVBoxLayout()

                message_label = QLabel(
                    "New versions of PyMoDAQ packages available!\nUse your package manager to update.",
                )
                message_label.setAlignment(Qt.Alignment.AlignCenter)

                table = PymodaqUpdateTableWidget()
                table.setRowCount(len(packages_data))
                table.setColumnCount(3)
                table.setHorizontalHeaderLabels(
                    ["Package", "Current version", "New version"],
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
    from pymodaq_gui.qt_utils import mkQApp
    app = mkQApp('CommonWindow')

    win, area = make_window(area=False, title='SharedUI')
    window = SharedUI(win)

    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

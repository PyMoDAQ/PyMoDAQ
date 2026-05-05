#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

from qtpy import QtWidgets

from pymodaq_plugin_manager.manager import PluginManager

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import GlobalConfig as Config
from pymodaq.utils.leco.utils import start_coordinator

from pymodaq_gui.utils.shared_ui import SharedUI, MenuToolbarNames

logger = set_logger(get_module_name(__file__))

config = Config()


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

        self.add_action("leco", "Run Leco Coordinator", "router", "Run a Coordinator on this localhost",
                        auto_toolbar=False, menu=MenuToolbarNames.TOOLS)
        self.add_action("plugin_manager", "Plugin Manager", 'extension', tip='Opens the Plugin Manager',
                        auto_toolbar=False, menu=MenuToolbarNames.TOOLS)

    def connect_things(self):
        super().connect_things()

        self.connect_action("leco", start_coordinator)
        self.connect_action("plugin_manager", self.start_plugin_manager)

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

# -*- coding: utf-8 -*-
"""
Created the 25/10/2022

@author: Sebastien Weber
"""
from typing import TYPE_CHECKING

import numpy as np
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager

from pymodaq_utils.config import GlobalConfig
from pymodaq.extensions.custom_ext import CustomExt

from pymodaq_utils.utils import get_version
from pymodaq_gui.utils.dock import DockArea

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard


config = GlobalConfig()

BANNER = f'PyMoDAQ v{get_version("pymodaq")}\n' \
         'Main objects available for interaction:\n'\
         '* dashboard: Main Dashboard Object\n'\
         '* mods: ModuleManager of the dashboard\'s Control Modules\n'\
         '* np: numpy module\n\n'\
         'For inline plotting use: %matplotlib\n\n'


class QtConsole(RichJupyterWidget):
    """Live IPython console widget.
    .. image:: img/IPythonWidget.png
    :param custom_banner: Custom welcome message to be printed at the top of
       the console.
    """

    def __init__(self, parent=None, custom_banner=None, *args, **kwargs):
        if parent is not None:
            kwargs["parent"] = parent
        super().__init__(*args, **kwargs)
        if custom_banner is not None:
            self.banner = custom_banner
        self.kernel_manager = kernel_manager = QtInProcessKernelManager()
        kernel_manager.start_kernel()

        self.kernel_client = kernel_client = self._kernel_manager.client()
        kernel_client.start_channels()

        def stop():
            kernel_client.stop_channels()
            kernel_manager.shutdown_kernel()
        self.exit_requested.connect(stop)

    def push_variables(self, variable_dict):
        """ Given a dictionary containing name / value pairs, push those
        variables to the IPython console widget.
        :param variable_dict: Dictionary of variables to be pushed to the
            console's interactive namespace (```{variable_name: object, …}```)
        """
        self.kernel_manager.kernel.shell.push(variable_dict)


class Console(CustomExt):

    def __init__(self, dockarea: DockArea = None, dashboard: 'DashBoard' = None):
        """

        Parameters
        ----------
        dockarea: DockArea
            instance of the modified pyqtgraph Dockarea
        dashboard: DashBoard
            instance of the pymodaq dashboard

        """
        self.console = QtConsole(style_sheet=config('gui', 'style', 'syntax_highlighting'),
                                 syntax_style=config('gui', 'style', 'syntax_highlighting'),
                                 custom_banner=BANNER)
        super().__init__(dockarea, dashboard)

        self.setup_ui()

    def do_things_after_experiment_set(self, experiment: str):
        super().do_things_after_experiment_set(experiment)

        self.console.push_variables(
            {'dashboard': self.dashboard,
             'mods': self.modules_manager,
             'np': np})

    def setup_docks_and_widgets(self):
        self.create_dashboard_toolbar(add_break=False)
        self.mainwindow.setCentralWidget(self.console)

    def setup_actions(self):
        pass

    def connect_things(self):
        pass


def main():
    import sys
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import load_dashboard_with_arguments
    from pymodaq.utils.gui_utils.loader_utils import create_extension

    app = mkQApp('Console')

    win, dashboard, _ = load_dashboard_with_arguments(show_dashboard=False,
                                                      load_extension=False,
                                                      )
    win.mainwindow.setVisible(False)

    win_ext, console = create_extension(dashboard, Console,
                                        show_extension=True)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()

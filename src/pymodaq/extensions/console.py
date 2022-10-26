# -*- coding: utf-8 -*-
"""
Created the 25/10/2022

@author: Sebastien Weber
"""
from qtpy import QtWidgets
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager
from pymodaq.utils import config as configmod
from pymodaq.utils.daq_utils import get_version


config = configmod.Config()
BANNER = f'PyMoDAQ v{get_version()}\n' \
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


def main(init_qt=True):
    import sys

    if init_qt:  # used for the test suite
        app = QtWidgets.QApplication(sys.argv)
        if config('style', 'darkstyle'):
            import qdarkstyle
            app.setStyleSheet(qdarkstyle.load_stylesheet(qdarkstyle.DarkPalette))

    prog = QtConsole(style_sheet=config('style', 'syntax_highlighting'),
                     syntax_style=config('style', 'syntax_highlighting'),
                     custom_banner=BANNER,
                     )
    prog.show()
    if init_qt:
        sys.exit(app.exec_())
    return prog


if __name__ == '__main__':
    main()

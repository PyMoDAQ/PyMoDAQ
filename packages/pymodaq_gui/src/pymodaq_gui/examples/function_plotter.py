# -*- coding: utf-8 -*-
"""
Created the 27/06/2022

@author: Sebastien Weber
"""

import numpy as np
from qtpy import QtWidgets
from qtpy.QtCore import QDate, QTimer

from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq_utils.config import GlobalConfig as Config

from pymodaq_data.data import DataRaw, Axis

from pymodaq_gui.utils.widgets.window import make_window
from pymodaq_gui.utils.custom_app import CustomApp
from pymodaq_gui.utils.dock import Dock
from pymodaq_gui.utils.utils import mkQApp
from pymodaq_gui.plotting.data_viewers.viewer1D import Viewer1D


config = Config()
logger = set_logger(get_module_name(__file__))


class FunctionPlotter(CustomApp):

    # list of dicts enabling the settings tree on the user interface
    params = [
            {'title': 'Save base path:', 'name': 'base_path', 'type': 'browsepath',
             'value': config('data', 'data_saving', 'h5file', 'save_path')},
            {'title': 'File name:', 'name': 'target_filename', 'type': 'str', 'value': "", 'readonly': True},
            {'title': 'Date:', 'name': 'date', 'type': 'date', 'value': QDate.currentDate()},

            {'title': 'Functions:', 'name': 'functions', 'type': 'list',
             'limits': ['exp(-(x/5)**2)', 'sin(x)', 'arctan(x)']},
            {'title': 'Function:', 'name': 'function', 'type': 'str', 'value': 'sinc(x)'},
            {'title': 'Add function:', 'label': 'Add!', 'name': 'add_function', 'type': 'bool_push', 'value': False},
            {'title': 'Plot refresh (ms):', 'name': 'plot_refresh', 'type': 'int', 'value': 2000},
            {'title': 'Xaxis:', 'name': 'xaxis', 'type': 'group', 'children': [
                {'title': 'Npts:', 'name': 'npoints', 'type': 'int', 'value': 200},
                {'title': 'Xstart:', 'name': 'xstart', 'type': 'float', 'value': -10},
                {'title': 'Xstop:', 'name': 'xstop', 'type': 'int', 'value': 10},
            ]},
    ]

    def __init__(self, dockarea):
        """ Example of a CustomApplication to plot mathematical functions

        One need to reimplement several methods:

        * setup_docks_and_widgets()  # (mandatory) create the UI skeleton
        * setup_menus_and_toolbars(self.menubar)  # (optional) create menus and toolbars and add them to main_window
        * setup_actions()  # (mandatory) create and add actions to various menus and toolbars
        * connect_things()  # (mandatory) connect actions and other signals
        * do_things_after_ui_setup()  # (optional) post setup ui stuff if needed

        """


        super().__init__(dockarea)

        # init the object parameters
        self.raw_data = []
        self.setup_ui()

        self.timer = QTimer(self)
        self.timer.setInterval(self.settings['plot_refresh'])
        self.timer.timeout.connect(self.plot_timer)

        self.ind_plot = 0

    def setup_docks_and_widgets(self):
        """
        subclass method from CustomApp
        """
        logger.debug('setting docks')
        self.dock_settings = Dock('Settings', size=(350, 350))
        self.dockarea.addDock(self.dock_settings, 'left')
        self.dock_settings.addWidget(self.settings_tree, 10)
        # settings_tree is an inherited property of the ParameterManager base class

        # create a dock containing a viewer object
        self.dock_viewer = Dock('Viewer dock', size=(350, 350))
        self.dockarea.addDock(self.dock_viewer, 'right', self.dock_settings)  # add this dock to the right of the settings one
        viewer_widget = QtWidgets.QWidget()
        self.viewer = Viewer1D(viewer_widget)
        self.dock_viewer.addWidget(viewer_widget)

        logger.debug('docks are set')

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        pass

    def setup_actions(self):
        """
        subclass method from ActionManager
        """
        logger.debug('setting actions')

        self.add_action('show', 'Show/hide', 'visibility', "Show Hide Viewer",
                        checkable=True, checked=True)
        self.add_action('plot', 'Plot', 'looks_one', "Plot", checkable=False)
        self.add_action('plot_seq', 'Plot Sequence', 'repeat_one_on', "Plot functions", checkable=True)
        self.add_action('save', 'Save', 'save', "Save current function", checkable=False)
        logger.debug('actions set')

    def connect_things(self):
        self.connect_action('plot', self.plot)
        self.connect_action('show', lambda show: self.dock_viewer.setVisible(show))

        self.connect_action('plot_seq', self.plot_all)

    def value_changed(self, param):
        if param.name() == 'add_function':
            function_list = [self.settings['function']]
            old_functions = self.functions
            function_list.extend(old_functions)
            function_list = list(np.unique(function_list))
            self.settings.child('functions').setLimits(function_list)
            param.setValue(False)

    def plot(self):
        function_str = self.settings['functions']
        x = np.linspace(self.settings['xaxis', 'xstart'], self.settings['xaxis', 'xstop'],
                        self.settings['xaxis', 'npoints'])

        function_vals = eval(f'np.{function_str}')

        self.viewer.show_data(DataRaw(name=function_str,
                                      data=[function_vals],
                                      labels=[function_str],
                                      axes=[Axis(
                                          data=x, label='An axis', units='arb. units')],
                                      ),
                              )

    @property
    def functions(self):
        return self.settings.child('functions').opts['limits']

    def plot_timer(self):
        self.settings.child('functions').setValue(self.functions[self.ind_plot % len(self.functions)])
        self.plot()
        self.ind_plot += 1

    def plot_all(self):
        if self.is_action_checked('plot_seq'):
            self.timer.start()
        else:
            self.timer.stop()


def main():
    import sys
    from pymodaq_gui.utils.shared_ui import SharedUI

    app = mkQApp(FunctionPlotter.__name__)
    win, area = make_window(title=FunctionPlotter.__name__)

    prog = FunctionPlotter(area)
    shared_ui = SharedUI(win)
    shared_ui.affect_application(prog)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()

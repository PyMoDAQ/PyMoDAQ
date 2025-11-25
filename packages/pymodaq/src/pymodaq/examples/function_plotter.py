# -*- coding: utf-8 -*-
"""
Created the 27/06/2022

@author: Sebastien Weber
"""

import numpy as np
from qtpy import QtWidgets
from qtpy.QtCore import Slot, QDate, QThread, QTimer

from pymodaq.utils import data as data_mod
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq_gui.utils.custom_app import CustomApp
from pymodaq_gui.utils.dock import DockArea, Dock
from pymodaq_data.data import DataRaw, Axis
from pymodaq_utils.config import Config

from pymodaq_gui.plotting.data_viewers.viewer1D import Viewer1D


config = Config()
logger = set_logger(get_module_name(__file__))


class FunctionPlotter(CustomApp):

    # list of dicts enabling the settings tree on the user interface
    params = [
            {'title': 'Save base path:', 'name': 'base_path', 'type': 'browsepath',
             'value': config('data_saving', 'h5file', 'save_path')},
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
            ]}
    ]

    def __init__(self, dockarea):
        super().__init__(dockarea)

        # init the object parameters
        self.raw_data = []
        self.setup_ui()  # will trigger:
        #                  self.setup_docks()
        #                  self.setup_actions()  # see ActionManager MixIn class
        #                  self.setup_menu()
        #                  self.connect_things()
        self.timer = QTimer()
        self.timer.setInterval(self.settings['plot_refresh'])
        self.timer.timeout.connect(self.plot_timer)

        self.ind_plot = 0

    def setup_docks(self):
        """
        subclass method from CustomApp
        """
        logger.debug('setting docks')
        self.dock_settings = Dock('Settings', size=(350, 350))
        self.dockarea.addDock(self.dock_settings, 'left')
        self.dock_settings.addWidget(self.settings_tree, 10)
        # settings_tree is an inherited property of the ParameterManager base class

        # create a dock containing a viewer object
        dock_viewer = Dock('Viewer dock', size=(350, 350))
        self.dockarea.addDock(dock_viewer, 'right', self.dock_settings)  # add this dock to the right of the settings one
        viewer_widget = QtWidgets.QWidget()
        self.viewer = Viewer1D(viewer_widget)
        dock_viewer.addWidget(viewer_widget)

        logger.debug('docks are set')

    def setup_actions(self):
        """
        subclass method from ActionManager
        """
        logger.debug('setting actions')
        self.add_action('quit', 'Quit', 'close2', "Quit program", toolbar=self.toolbar)
        # toolbar is an inherited property of the ActionManager base class

        self.add_action('show', 'Show/hide', 'read2', "Show Hide Viewer", checkable=True, toolbar=self.toolbar)
        self.add_action('plot', 'Plot', 'snap', "Plot", checkable=False, toolbar=self.toolbar)
        self.add_action('plot_seq', 'Plot Sequence', 'camera', "Plot functions", checkable=True, toolbar=self.toolbar)
        self.add_action('save', 'Save', 'SaveAs', "Save current function", checkable=False, toolbar=self.toolbar)
        logger.debug('actions set')

    def connect_things(self):
        self.connect_action('quit', self.quit)
        self.connect_action('plot', self.plot)

        self.connect_action('plot_seq', self.plot_all)

    def quit(self):
        self.mainwindow.close()

    def plot(self):
        function_str = self.settings['functions']
        x = np.linspace(self.settings['xaxis', 'xstart'], self.settings['xaxis', 'xstop'],
                        self.settings['xaxis', 'npoints'])

        function_vals = eval(f'np.{function_str}')

        self.viewer.show_data(DataRaw(name=function_str,
                                      data=[function_vals],
                                      labels=[function_str],
                                      axes=[
                                          data_mod.Axis(
                                              data=x, label='An axis', units='arb. units')],
                                      )
                              )

    def value_changed(self, param):
        if param.name() == 'add_function':
            function_list = [self.settings['function']]
            old_functions = self.functions
            function_list.extend(old_functions)
            function_list = list(np.unique(function_list))
            self.settings.child('functions').setLimits(function_list)
            param.setValue(False)

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
    app = QtWidgets.QApplication(sys.argv)
    mainwindow = QtWidgets.QMainWindow()
    dockarea = DockArea()
    mainwindow.setCentralWidget(dockarea)

    prog = FunctionPlotter(dockarea)

    mainwindow.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

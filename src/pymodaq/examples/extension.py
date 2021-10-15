from pymodaq.daq_utils import gui_utils as gutils
from pymodaq.daq_utils import daq_utils as utils
from pyqtgraph.parametertree import Parameter, ParameterTree
from pymodaq.daq_utils.parameter import pymodaq_ptypes
from PyQt5 import QtWidgets, QtCore

from pymodaq.daq_utils.plotting.viewer1D.viewer1D_main import Viewer1D
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D


config = utils.load_config()
logger = utils.set_logger(utils.get_module_name(__file__))


class MyExtension(gutils.CustomApp):
    # list of dicts enabling the settings tree on the user interface
    params = [
        {'title': 'Main settings:', 'name': 'main_settings', 'type': 'group', 'children': [
            {'title': 'Save base path:', 'name': 'base_path', 'type': 'browsepath',
             'value': config['data_saving']['h5file']['save_path']},
            {'title': 'File name:', 'name': 'target_filename', 'type': 'str', 'value': "", 'readonly': True},
            {'title': 'Date:', 'name': 'date', 'type': 'date', 'value': QtCore.QDate.currentDate()},
            {'title': 'Do something, such as showing data:', 'name': 'do_something', 'type': 'bool', 'value': False},
            {'title': 'Something done:', 'name': 'something_done', 'type': 'led', 'value': False, 'readonly': True},
            {'title': 'Infos:', 'name': 'info', 'type': 'text', 'value': ""},
            {'title': 'push:', 'name': 'push', 'type': 'bool_push', 'value': False}
        ]},
        {'title': 'Other settings:', 'name': 'other_settings', 'type': 'group', 'children': [
            {'title': 'List of stuffs:', 'name': 'list_stuff', 'type': 'list', 'value': 'first',
             'values': ['first', 'second', 'third'], 'tip': 'choose a stuff from the list'},
            {'title': 'List of integers:', 'name': 'list_int', 'type': 'list', 'value': 0,
             'values': [0, 256, 512], 'tip': 'choose a stuff from this int list'},
            {'title': 'one integer:', 'name': 'an_integer', 'type': 'int', 'value': 500, },
            {'title': 'one float:', 'name': 'a_float', 'type': 'float', 'value': 2.7, },
        ]},
    ]

    def __init__(self, dockarea, dashboard):
        super().__init__(dockarea, dashboard)

    def connect_things(self):
        pass

    def setup_docks(self):
        """
        to be subclassed to setup the docks layout
        for instance:

        self.docks['ADock'] = gutils.Dock('ADock name)
        self.dockarea.addDock(self.docks['ADock"])
        self.docks['AnotherDock'] = gutils.Dock('AnotherDock name)
        self.dockarea.addDock(self.docks['AnotherDock"], 'bottom', self.docks['ADock"])

        See Also
        ########
        pyqtgraph.dockarea.Dock
        """
        self.docks['settings'] = gutils.Dock('Settings')
        self.dockarea.addDock(self.docks['settings'])
        self.docks['settings'].addWidget(self.settings_tree)

        self.docks['modmanager'] = gutils.Dock('Module Manager')
        self.dockarea.addDock(self.docks['modmanager'], 'right', self.docks['settings'])
        self.docks['modmanager'].addWidget(self.modules_manager.settings_tree)

        self.docks['viewer1D'] = gutils.Dock('Viewers')
        self.dockarea.addDock(self.docks['viewer1D'], 'right', self.docks['modmanager'])

        self.docks['viewer2D'] = gutils.Dock('Viewers')
        self.dockarea.addDock(self.docks['viewer2D'], 'bottom', self.docks['viewer1D'])

        widg = QtWidgets.QWidget()
        self.viewer1D = Viewer1D(widg)
        self.docks['viewer1D'].addWidget(widg)

        widg1 = QtWidgets.QWidget()
        self.viewer2D = Viewer2D(widg1)
        self.docks['viewer2D'].addWidget(widg1)

    def setup_menu(self):
        '''
        to be subclassed
        create menu for actions contained into the self.actions_manager, for instance:

        For instance:

        file_menu = self.menubar.addMenu('File')
        self.actions_manager.affect_to('load', file_menu)
        self.actions_manager.affect_to('save', file_menu)

        file_menu.addSeparator()
        self.actions_manager.affect_to('quit', file_menu)
        '''
        pass

    def value_changed(self, param):
        ''' to be subclassed for actions to perform when one of the param's value in self.settings is changed

        For instance:
        if param.name() == 'do_something':
            if param.value():
                print('Do something')
                self.settings.child('main_settings', 'something_done').setValue(False)

        Parameters
        ----------
        param: (Parameter) the parameter whose value just changed
        '''
        if param.name() == 'do_something':
            if param.value():
                self.modules_manager.det_done_signal.connect(self.show_data)
            else:
                self.modules_manager.det_done_signal.disconnect()

    def param_deleted(self, param):
        ''' to be subclassed for actions to perform when one of the param in self.settings has been deleted

        Parameters
        ----------
        param: (Parameter) the parameter that has been deleted
        '''
        raise NotImplementedError

    def child_added(self, param):
        ''' to be subclassed for actions to perform when a param  has been added in self.settings

        Parameters
        ----------
        param: (Parameter) the parameter that has been deleted
        '''
        raise NotImplementedError

    def setup_actions(self):
        pass

    def show_data(self, data_all):
        data1D = []
        data2D = []
        labels1D = []
        labels2D = []
        dims = ['data1D', 'data2D']
        for det in data_all:
            for dim in dims:
                if len(data_all[det][dim]) != 0:
                    for channel in data_all[det][dim]:
                        if dim == 'data1D':
                            labels1D.append(channel)
                            data1D.append(data_all[det][dim][channel]['data'])
                        else:
                            labels2D.append(channel)
                            data2D.append(data_all[det][dim][channel]['data'])
        self.viewer1D.show_data(data1D)
        self.viewer2D.setImage(*data2D[:min(3, len(data2D))])



def main():
    import sys
    from pymodaq.dashboard import DashBoard
    from pathlib import Path
    app = QtWidgets.QApplication(sys.argv)
    mainwindow = QtWidgets.QMainWindow()
    dockarea = gutils.DockArea()
    mainwindow.setCentralWidget(dockarea)

    #  init the dashboard
    mainwindow_dash = QtWidgets.QMainWindow()
    area_dash = gutils.DockArea()
    mainwindow_dash.setCentralWidget(area_dash)
    dashboard = DashBoard(area_dash)
    file = Path(utils.get_set_preset_path()).joinpath(f"{config['presets']['default_preset_for_scan']}.xml")
    if file.exists():
        dashboard.set_preset_mode(file)
    else:
        msgBox = QtWidgets.QMessageBox()
        msgBox.setText(f"The default file specified in the configuration file does not exists!\n"
                       f"{file}\n"
                       f"Impossible to load the DAQ_Scan Module")
        msgBox.setStandardButtons(msgBox.Ok)
        ret = msgBox.exec()

    prog = MyExtension(dockarea, dashboard)

    mainwindow.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()



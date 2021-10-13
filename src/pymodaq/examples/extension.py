from pymodaq.daq_utils import gui_utils as gutils
from pymodaq.daq_utils import daq_utils as utils
from pyqtgraph.parametertree import Parameter, ParameterTree
from pymodaq.daq_utils.parameter import pymodaq_ptypes
from PyQt5 import QtWidgets, QtCore

config = utils.load_config()
logger = utils.set_logger(utils.get_module_name(__file__))


class ActionManager(gutils.ActionManager):
    def __init__(self, toolbar=None, menu=None):
        super().__init__(toolbar, menu)

    def setup_actions(self):
        self.actions['quit'] = self.addaction('Quit', 'close2', "Quit program")
        self.actions['grab'] = self.addaction('Grab', 'camera', "Grab from camera", checkable=True)
        self.actions['load'] = self.addaction('Load', 'Open',
                                                "Load target file (.h5, .png, .jpg) or data from camera",
                                                checkable=False)
        self.actions['save'] = gutils.addaction('Save', 'SaveAs', "Save current data", checkable=False)



        # %% create file menu
        file_menu = self.menubar.addMenu('File')
        self.actions.affect_to('load', file_menu)
        self.actions.affect_to('save', file_menu)

        file_menu.addSeparator()
        self.actions.affect_to('quit', file_menu)


class MyApp(gutils.CustomApp):
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


    def setup_docks(self):
        '''

        '''
        pass

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

    def setup_settings_tree(self):
        '''  to be subclassed
        create a setting tree for actions contained into the self.actions_manager, for instance:

        for instance:
        self.docks()['Dock Settings'].addWidget(self.settings_tree, 10)
        '''
        pass

    def setup_UI(self):
        # ##### Manage Docks########
        names = ['Dock Settings', 'Dock Other']
        self.docks = DockedPanels(self.dockarea, names)

        # #### Manage actions, toolbar and Menu
        toolbar = QtWidgets.QToolBar()
        self.mainwindow.addToolBar(toolbar)

        self.actions = ActionManager(toolbar=toolbar)
        self.menu = Menu(self.mainwindow.menuBar(), self.actions)

        # #### Manage settings
        self.settings_tree = ParameterTree()
        self.docks()['Dock Settings'].addWidget(self.settings_tree, 10)

        self.settings = Parameter.create(name='Settings', type='group', children=self.params)  # create a Parameter
        # object containing the settings

        self.settings_tree.setParameters(self.settings, showTop=False)  # load the tree with this parameter object
        # any change to the tree on the user interface will call the parameter_tree_changed method where all actions
        # will be applied
        self.settings.sigTreeStateChanged.connect(self.parameter_tree_changed)

    def parameter_tree_changed(self, param, changes):
        for param, change, data in changes:
            if change == 'childAdded':
                pass

            elif change == 'value':
                if param.name() == 'do_something':
                    if param.value():
                        self.log_signal.emit('Do something')
                        print('Do something')
                        self.settings.child('main_settings', 'something_done').setValue(False)
                    else:
                        self.log_signal.emit('Stop Doing something')
                        print('Stop Doing something')
                        self.settings.child('main_settings', 'something_done').setValue(True)

            elif change == 'parent':
                pass


def main():
    import sys
    from pymodaq.dashboard import DashBoard
    from pathlib import Path
    app = QtWidgets.QApplication(sys.argv)
    mainwindow = QtWidgets.QMainWindow()
    dockarea = gutils.DockArea()
    mainwindow.setCentralWidget(dockarea)

    ## init the dashboard
    area_dash = gutils.DockArea()
    dashboard = DashBoard(area_dash)
    file = Path(utils.get_set_preset_path()).joinpath(f"{config['presets']['default_preset_for_scan']}.xml")
    if file.exists():
        dashboard.set_preset_mode(file)
        dashboard.load_scan_module()
    else:
        msgBox = QtWidgets.QMessageBox()
        msgBox.setText(f"The default file specified in the configuration file does not exists!\n"
                       f"{file}\n"
                       f"Impossible to load the DAQ_Scan Module")
        msgBox.setStandardButtons(msgBox.Ok)
        ret = msgBox.exec()

    prog = MyApp(dockarea, dashboard)

    mainwindow.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()



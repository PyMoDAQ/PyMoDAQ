from qtpy import QtWidgets

from pymodaq_gui.utils.custom_app import CustomApp



class MyApp(CustomApp):
    params = [
        {'title': 'Time Flow:', 'name': 'time_flow', 'type': 'group', 'expanded': False,
         'children': [
             {'title': 'Wait time step (ms)', 'name': 'wait_time', 'type': 'int', 'value': 0,
              'tip': 'Wait time in ms after each step of acquisition (move and grab)'},
             {'title': 'Wait time between (ms)', 'name': 'wait_time_between', 'type': 'int',
              'value': 0,
              'tip': 'Wait time in ms between move and grab processes'},
         ]}]
    def __init__(self, parent):
        super().__init__(parent=parent)

        self.setup_ui()

    def setup_docks_and_widgets(self):
        self.mainwindow.setCentralWidget(self.settings_tree)

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        if menubar is None:
            menubar = self.menubar

        self.toolbar.setVisible(False)

        self.add_menu('file', 'File', menubar)
        self.add_menu('tools', 'Tools', menubar)
        self.add_menu('subtools', 'SubTools', 'tools')
        self.add_toolbar('file', 'file', self.mainwindow, add_break=False)
        self.add_toolbar('app_toolbar', 'MyApp', self.mainwindow, add_break=False)

    def setup_actions(self):
        self.add_action('new', 'New File', 'draft', 'Create a new file',
                        toolbar='file', menu='file')
        self.add_action('save', 'Save File', 'file_save', 'Save file as',
                        toolbar='file', menu='file')
        self.add_action('load', 'Load File', 'file_open', 'Load file ',
                        toolbar='file', menu='file')

        self.add_action('tool1', 'Erase', 'ink_eraser', 'ink_eraser',
                        toolbar='app_toolbar', menu='tools')
        self.add_action('tool2', 'Erase off', 'ink_eraser_off', 'ink_eraser_off',
                        toolbar='app_toolbar', menu='subtools')
        self.add_action('tool3', 'input', 'input', 'input',
                        toolbar='app_toolbar', menu='subtools')

    def connect_things(self):
        pass


def test_shared_ui_custom(qtbot):
    import qt_themes
    from pymodaq_gui.utils.widgets.window import make_window
    from pymodaq_gui.utils.shared_ui import SharedUI

    qt_themes.set_theme('dracula')

    window, dockarea = make_window(area=False, title='SharedUiTest')
    qtbot.addWidget(window)
    app = MyApp(window)

    shared_ui = SharedUI(window)
    shared_ui.affect_application(app)

    shared_ui.quit_fun()






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
         ]},]
    def __init__(self, parent):
        super().__init__(parent=parent)

        self.setup_ui()

    def setup_docks(self):
        self.mainwindow.setCentralWidget(self.settings_tree)

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        pass

    def setup_actions(self):
        pass

    def connect_things(self):
        pass


if __name__ == "__main__":
    from pymodaq_gui.utils.utils import mkQApp
    from pymodaq.utils.gui_utils.widgets.window import make_window
    from pymodaq_gui.shared_ui import SharedUI

    qapp = mkQApp('SharedUidev')
    window, dockarea = make_window(area=False, title='SharedUiDev')
    app = MyApp(window)

    shared_ui = SharedUI(window)
    shared_ui.affect_application(app)

    qapp.exec()




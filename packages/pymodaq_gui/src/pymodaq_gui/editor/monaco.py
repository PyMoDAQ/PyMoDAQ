import pymodaq_gui


from qtmonaco import Monaco
from qtpy import QtWidgets

from pymodaq.utils.gui_utils.widgets.window import make_window
from pymodaq_gui.shared_ui import SharedUI
from pymodaq_gui.utils import CustomApp
from pymodaq_gui.utils.utils import mkQApp


class MonacoApp(CustomApp):
    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.monaco_widget: Monaco = None
        self.setup_ui()

    def setup_ui(self):
        self.setup_docks()
        self.setup_menu(self._menubar)
        self.setup_actions()  # see ActionManager MixIn class
        self.connect_things()
        self.do_things_after_ui_setup()

    def setup_docks(self):
        self.monaco_widget = Monaco()
        self.mainwindow.setCentralWidget(self.monaco_widget)

        self.monaco_widget.set_language("python")
        self.monaco_widget.set_theme('vs-dark' if self.get_theme().is_dark_theme() else 'vs')
        self.monaco_widget.set_minimap_enabled(True)

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        self.add_menu('file', 'File', menubar)
        self.add_toolbar('file', 'File', parent=self.mainwindow)

        self.get_toolbar('_default').setVisible(False)

    def setup_actions(self):
        self.add_action('new', 'New File', 'draft', 'Create a new file',
                        toolbar='file', menu='file', auto_menu=True)
        self.add_action('save', 'Save File', 'file_save', 'Save file as',
                        toolbar='file', menu='file', auto_menu=True)
        self.add_action('load', 'Load File', 'file_open', 'Load file ',
                        toolbar='file', menu='file', auto_menu=True)

    def connect_things(self):
        pass


def main():
    qapp = mkQApp('Monaco')

    win, area = make_window(area=False, title="Monaco")

    monaco_app = MonacoApp(win)

    shared_ui = SharedUI(win)
    shared_ui.affect_application(monaco_app)


    monaco_app.monaco_widget.set_text(
        """
    import numpy as np
    from typing import TYPE_CHECKING
    
    if TYPE_CHECKING:
        from bec_lib.devicemanager import DeviceContainer
        from bec_lib.scans import Scans
        dev: DeviceContainer
        scans: Scans
    
    #######################################
    ########## User Script #####################
    #######################################
    
    # This is a comment
    def hello_world():
        print("Hello, world!")
                """
    )

    qapp.exec_()

if __name__ == "__main__":
    main()
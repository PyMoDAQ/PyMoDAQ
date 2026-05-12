
from pymodaq_gui.utils.widgets.window import make_window
from pymodaq_gui.utils.shared_ui import SharedUI

from .monaco import MonacoApp


def editor_main_loader():
    win, area = make_window(area=False, title="Monaco")

    monaco_app = MonacoApp(win)

    shared_ui = SharedUI(win)
    shared_ui.affect_application(monaco_app)

    return shared_ui, monaco_app
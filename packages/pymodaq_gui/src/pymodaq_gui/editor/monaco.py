import pickle
import tempfile
from pathlib import Path


from qtmonaco import Monaco
from qtpy import QtWidgets, QtCore

from qt_themes import get_theme

from pymodaq_utils.config import get_set_local_dir

from pymodaq_gui.utils.styling import create_icon
from pymodaq_gui.utils.widgets.window import make_window

from pymodaq_gui.utils import CustomApp
from pymodaq_gui.utils.shared_ui import SharedUI, MenuNames
from pymodaq_gui.utils.file_io import select_file

from pymodaq_utils.config import GlobalConfig

config = GlobalConfig()


class FileWidget(QtWidgets.QFrame):

    close_signal = QtCore.Signal(Path)

    def __init__(self, filepath: Path, parent=None):
        super().__init__(parent)

        self.path = filepath
        self.close_button: QtWidgets.QPushButton = None
        self.file_name_button: QtWidgets.QPushButton = None

        self.setup_ui()

    def setup_ui(self):
        self.setLayout(QtWidgets.QHBoxLayout())
        self.file_name_button = QtWidgets.QPushButton(self.path.stem)
        self.file_name_button.setAutoExclusive(True)
        self.file_name_button.setCheckable(True)
        self.layout().addWidget(self.file_name_button)
        self.close_button = QtWidgets.QPushButton()
        self.close_button.setIcon(
            create_icon('cancel', get_theme(config('gui', 'style', 'theme')[0]).red))
        self.close_button.setVisible(False)
        self.close_button.clicked.connect(lambda: self.close_signal.emit(self.path))
        self.file_name_button.toggled.connect(self.show_close)
        self.layout().addWidget(self.close_button)

    def show_close(self, show=True):
        self.close_button.setVisible(show)


class FileWidgetAction(QtWidgets.QWidgetAction):

    def __init__(self, path: Path, parent=None):
        super().__init__(parent)
        self.path = path

    def createWidget(self, parent: QtWidgets.QWidget=None):
        widget = FileWidget(self.path, parent=parent)
        widget.file_name_button.toggled.connect(self.triggered.emit)
        return widget


class MonacoApp(CustomApp):
    def __init__(self, parent: QtWidgets.QWidget = None,):
        super().__init__(parent, create_app_toolbar=False)

        self.monaco_widget: Monaco = None
        self._current_path = config('data', 'data_saving', 'h5file', 'save_path')
        self._files: list[Path] = []

        self.setup_ui()

    def do_things_after_ui_setup(self):
        try:
            with open(self.local_files_path, 'rb') as f:
                _files = pickle.load(f)
                for ind, file in enumerate(_files):
                    self.add_file(file, display=True if ind == len(_files)-1 else False)
        except FileNotFoundError as e:
            pass

    def setup_docks_and_widgets(self):
        self.monaco_widget = Monaco()
        self.mainwindow.setCentralWidget(self.monaco_widget)

        self.monaco_widget.set_language("python")
        self.monaco_widget.set_theme('vs-dark' if self.get_theme().is_dark_theme() else 'vs')
        self.monaco_widget.set_minimap_enabled(True)

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        self.add_menu(MenuNames.FILE, 'File', parent_menu=menubar)
        self.add_menu('files', 'Recent Files', parent_menu=MenuNames.FILE)

        self.add_toolbar('file', 'File', parent=self.mainwindow, add_break=False)
        self.add_toolbar('files', 'Files', parent=self.mainwindow, add_break=True)
        self.get_toolbar('files').setMovable(False)

    def setup_actions(self):
        self.add_action('new', 'New File', 'draft', 'Create a new file',
                        toolbar='file', menu='file', auto_menu=True)
        self.add_action('save', 'Save File', 'file_save', 'Save file as',
                        toolbar='file', menu='file', auto_menu=True)
        self.add_action('load', 'Load File', 'file_open', 'Load file ',
                        toolbar='file', menu='file', auto_menu=True)

    def connect_things(self):
        self.connect_action('load', self.load_file)
        self.connect_action('new', self.create_file)

    def create_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            self.add_file(Path(f.name))

    def load_file(self):
        file_path = select_file(start_path=self._current_path, save=False, ext='py')
        if file_path:
            self.add_file(file_path)

    def add_file(self, file_path: Path, display=True):
        self._files.append(file_path)
        self._current_path = file_path.parent
        self.add_action(file_path.stem, toolbar='files',
                        action=FileWidgetAction(file_path))
        self.connect_action(file_path.stem, self._create_lambda_file_slot(file_path))
        if display:
            self.display_file_text(file_path)

    def _create_lambda_file_slot(self, file_path: Path):
        return lambda: self.display_file_text(file_path)


    def display_file_text(self, file_path: Path):
        with open(file_path, 'r') as f:
            self.monaco_widget.set_text(''.join(f.readlines()))

    @property
    def local_files_path(self) -> Path:
        return get_set_local_dir(user=True).joinpath('monaco_files')

    def quit_fun(self):
        super().quit_fun()
        with open(self.local_files_path, 'wb') as f:
            pickle.dump(self._files, f)


def main():
    from pymodaq_gui.utils.utils import mkQApp

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
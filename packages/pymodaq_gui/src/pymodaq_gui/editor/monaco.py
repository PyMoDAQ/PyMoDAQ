import pickle
import tempfile
from collections import OrderedDict
from pathlib import Path


from qtmonaco import Monaco
from qtpy import QtWidgets
from qtpy.QtGui import QKeySequence
from qtpy.QtCore import Qt, QFileSystemWatcher

from pymodaq_gui.messenger import dialog
from pymodaq_utils.config import get_set_local_dir

from pymodaq_gui.utils.widgets.window import make_window

from pymodaq_gui.utils import CustomApp
from pymodaq_gui.utils.shared_ui import SharedUI, MenuNames
from pymodaq_gui.utils.file_io import select_file

from pymodaq_utils.config import GlobalConfig

config = GlobalConfig()


class MonacoWithFile(Monaco):
    def __init__(self, file_path: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.file_path = file_path


class MonacoApp(CustomApp):
    def __init__(self, parent: QtWidgets.QWidget = None,):
        super().__init__(parent, create_app_toolbar=False)

        self.monaco_widget: Monaco = None
        self._save_path = config('data', 'data_saving', 'h5file', 'save_path')

        self.file_watcher = QFileSystemWatcher()

        self.setup_ui()

    def do_things_after_ui_setup(self):
        try:
            with open(self.local_files_path, 'rb') as f:
                _files = pickle.load(f)
                for file in _files:
                    self.add_file(file, display=True)
        except FileNotFoundError as e:
            pass

    def setup_docks_and_widgets(self):
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setElideMode(Qt.TextElideMode.ElideRight)
        self.tab_widget.setMovable(True)

        self.mainwindow.setCentralWidget(self.tab_widget)

    def create_monaco_widget(self, file_path: Path) -> MonacoWithFile:
        monaco_widget = MonacoWithFile(file_path)
        monaco_widget.set_language("python")
        monaco_widget.set_theme('vs-dark' if self.get_theme().is_dark_theme() else 'vs')
        monaco_widget.set_minimap_enabled(True)
        return monaco_widget

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        self.add_menu(MenuNames.FILE, 'File', parent_menu=menubar)
        self.add_menu('files', 'Recent Files', parent_menu=MenuNames.FILE)

        self.add_toolbar('file', 'File', parent=self.mainwindow, add_break=False)

    def setup_actions(self):
        self.add_action('new', 'New File', 'draft', 'Create a new file',
                        toolbar='file', menu='file', auto_menu=True,
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_N))
        self.add_action('load', 'Open File', 'file_open', 'Load file ',
                        toolbar='file', menu='file', auto_menu=True,
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_O))

        self.add_action('save', 'Save File', 'file_save', 'Save file',
                        toolbar='file', menu='file', auto_menu=True,
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_S))

        self.add_action('save_copy_as', 'Save a Copy As', 'save_as', 'Save a copy of the file as',
                        toolbar='file', menu='file', auto_menu=True,
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_S))

    def connect_things(self):
        self.connect_action('load', self.load_file)
        self.connect_action('new', self.create_file)
        self.connect_action('save', self.save_file)
        self.connect_action('save_copy_as', self.save_copy_file_as)

        self.tab_widget.tabCloseRequested.connect(self.close_editor)

        self.file_watcher.fileChanged.connect(self.do_things_on_file_changed)

    def do_things_on_file_changed(self, file_path_as_str: str):
        file_path = Path(file_path_as_str)

    @property
    def current_editor(self) -> MonacoWithFile:
        """ Get the editor in the currently opened tab"""
        return self.tab_widget.currentWidget()

    def get_editor_from_tab_index(self, tab_index: int) -> MonacoWithFile:
        """ get the Monaco editor instance from it's tab index"""
        return self.tab_widget.widget(tab_index)

    @property
    def current_file(self) -> Path:
        return self.current_editor.file_path

    def close_editor(self, tab_index: int):
        """ close the file and the editor of the given tab index"""

        #todo modify below to handle unsaved files!
        do_remove = dialog(title="Closing",
                           message=f'Are you sure you want to close the file'
                                   f' {self.get_editor_from_tab_index(tab_index).file_path.name}')
        if do_remove:
            file_path = self.files_path[tab_index]
            self.file_watcher.removePath(str(file_path))
            self.tab_widget.removeTab(tab_index)

    def remove_file(self, file_path: Path):
        """ remove the editor corresponding to the specified file Path """
        tab_index = self.files_path.index(file_path)
        self.close_editor(tab_index)

    def create_file(self):
        """ Create a new file and display it in a new tab """
        current_directory = self.current_editor.file_path.parent

        with current_directory.joinpath('untitled.py') as f:
            self.add_file(Path(f.name))

    def load_file(self, file_path: Path = None):
        """ Load a new file and display it in a new tab"""
        if file_path is None:
            file_path = select_file(start_path=self._save_path, save=False, ext='py')
        if file_path:
            self.add_file(file_path)

    def save_file(self):
        """ Save the current editor content in the corresponding file Path """
        self._save_file(self.current_file)

    def save_copy_file_as(self, file_path: Path = None):
        """ Make a copy of the curent editor content in a new file Path """
        if file_path is None:
            file_path = select_file(start_path=self._save_path, save=True, ext='py',
                                    force_save_extension=True)
        if file_path:
            self._save_file(file_path)
            self.add_file(file_path)

    def _save_file(self, file_path: Path = None):
        """ Save the current editor content in the specified file Path """
        if file_path is None:
            file_path = self.current_file

        with open(file_path, 'w', encoding="utf-8", newline='') as f:
            f.write(self.current_editor.get_text())

    def add_file(self, file_path: Path, display=True):
        """ Open and display a file content in a new editor"""
        self._save_path = file_path.parent
        self.file_watcher.addPath(str(file_path))

        monaco_widget = self.create_monaco_widget(file_path)
        tab_index = self.tab_widget.addTab(monaco_widget, file_path.name)
        self.tab_widget.setTabToolTip(tab_index, str(file_path))
        self.tab_widget.setCurrentIndex(tab_index)

        if display:
            self.display_file_text(file_path, monaco_widget)

    def display_file_text(self, text: Path | str, monaco_widget: MonacoWithFile=None):
        """ display in the given editor the text

        Parameters
        ----------
        text : str or Path
            if Path to a valid file, open the file and print in the editor the text it contains
        monaco_widget : MonacoWithFile

        """
        if monaco_widget is None:
            monaco_widget = self.current_editor

        if isinstance(text, Path):
            with open(text, 'r', encoding="utf-8", newline='') as f:
                text = ''.join(f.readlines())

        monaco_widget.set_text(text)

    @property
    def local_files_path(self) -> Path:
        """ Get a local file path to cache some data"""
        return get_set_local_dir(user=True).joinpath('monaco_files')

    @property
    def files_path(self) -> list[Path]:
        """ Get the list of all opened files in the order of the displayed tabs"""
        return [self.tab_widget.widget(index_tab).file_path for index_tab in range(self.tab_widget.count())]

    def quit_fun(self):
        super().quit_fun()
        with open(self.local_files_path, 'wb') as f:
            pickle.dump(self.files_path, f)


def main():
    from pymodaq_gui.utils.utils import mkQApp

    qapp = mkQApp('Monaco')

    win, area = make_window(area=False, title="Monaco")

    monaco_app = MonacoApp(win)

    shared_ui = SharedUI(win)
    shared_ui.affect_application(monaco_app)

    qapp.exec_()

if __name__ == "__main__":
    main()
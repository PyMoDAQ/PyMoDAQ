import pickle
import tempfile
from collections import OrderedDict
from pathlib import Path
import dataclasses

import subprocess
import sys

from qtmonaco import Monaco
from qtpy import QtWidgets
from qtpy.QtGui import QKeySequence, QColor, QTextCursor
from qtpy.QtCore import Qt, QFileSystemWatcher, Signal, QSignalBlocker, QThread, QObject

from pymodaq_gui.messenger import dialog
from pymodaq_utils.config import get_set_local_dir, GlobalConfig




from pymodaq_gui.utils import CustomApp
from pymodaq_gui.utils.shared_ui import SharedUI, MenuNames
from pymodaq_gui.utils.file_io import select_file


config = GlobalConfig()


class Redirect:
    def __init__(self, widget: QtWidgets.QTextEdit, autoscroll=True):
        self.widget = widget
        self.autoscroll = autoscroll

    def fileno(self):
        return 0

    def write(self, text: str):
        self.widget.append(text)
        if self.autoscroll:
            self.widget.moveCursor(QTextCursor.MoveOperation.End)

    def flush(self):
        pass


@dataclasses.dataclass
class FileStatus:
    path: Path
    unsaved: bool = False


class MonacoWithFile(Monaco):

    file_status = Signal(FileStatus)

    def __init__(self, file_path: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.file_path = file_path
        self._unsaved = False

        self.text_changed.connect(self.set_unsaved)

    def set_unsaved(self):
        if not self._unsaved:
            self._unsaved = True
            self.file_status.emit(FileStatus(self.file_path, True))

    def set_saved(self):
        if self._unsaved:
            self._unsaved = False
            self.file_status.emit(FileStatus(self.file_path, False))

    @property
    def saved(self):
        return not self._unsaved

    @property
    def unsaved(self):
        return self._unsaved


class Runner(QObject):
    def __init__(self, display: QtWidgets.QTextEdit):

        super().__init__()

        self.redirect = Redirect(display)
        self.redirect.write('Initializing subprocess runner')

    def do_subprocess(self, file_path: Path):
        self.redirect.write('Starting subprocess')
        subprocess.Popen([sys.executable, str(file_path)], stdout=self.redirect, stderr=self.redirect, text=True)


class MonacoApp(CustomApp):

    run_signal = Signal(Path)

    def __init__(self, parent: QtWidgets.QWidget = None,):
        super().__init__(parent, create_app_toolbar=False)

        self.monaco_widget: Monaco = None
        self._thread: QThread = None

        self._save_path = config('data', 'data_saving', 'h5file', 'save_path')

        self.file_watcher = QFileSystemWatcher()  # to check if file are modified from elsewhere

        self.setup_ui()

    def do_things_after_ui_setup(self):
        try:
            with open(self.local_files_path, 'rb') as f:
                _files = pickle.load(f)
                for file in _files:
                    self.add_file(file, display=True)

            self.highlight_tab(self.tab_widget.currentIndex())

        except FileNotFoundError as e:
            pass

    def setup_docks_and_widgets(self):
        self.main_widget = QtWidgets.QSplitter(Qt.Orientation.Vertical)

        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setElideMode(Qt.TextElideMode.ElideRight)
        self.tab_widget.setMovable(True)

        self.display_widget = QtWidgets.QTextEdit()
        self.display_widget.setReadOnly(True)

        self.main_widget.addWidget(self.tab_widget)
        self.main_widget.addWidget(self.display_widget)
        self.main_widget.setSizes([300, 100])

        self.mainwindow.setCentralWidget(self.main_widget)

    def add_text_to_display(self, text: str):
        self.display_widget.append(text)

    def run_file(self, file_path: Path = None):
        if file_path is None:
            file_path = self.current_file
        self._save_file(file_path)

        self.display_widget.clear()
        self.display_widget.append(f'Checking {file_path.name} file syntax...')
        try:
            self.check_python_syntax_valid(file_path)
        except SyntaxError as e:
            self.display_widget.append(f"Syntax error: {e}")
            return
        except Exception as e:
            self.display_widget.append(f"Error: {e}")
            return
        self.display_widget.append(f'Syntax is Ok!')

        self.display_widget.append(f'Running {file_path.name} file')


        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()

        self._runner = Runner(display=self.display_widget)
        # self._thread = QThread()
        # self._runner.moveToThread(self._thread)
        # self._thread.finished.connect(self._runner.deleteLater)
        self.run_signal.connect(self._runner.do_subprocess)

        # self._thread.start()

        self.run_signal.emit(file_path)

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

        self.add_action('run_file', 'Run current File', 'start', 'Run the currently selected file',
                        toolbar='file', menu='file', auto_menu=True,)

    def connect_things(self):
        self.connect_action('load', lambda: self.load_file())
        self.connect_action('new', self.create_file)
        self.connect_action('save', self.save_file)
        self.connect_action('save_copy_as', self.save_copy_file_as)

        self.connect_action('run_file', lambda: self.run_file())

        self.tab_widget.tabCloseRequested.connect(self.close_editor)
        self.tab_widget.tabBarClicked.connect(self.highlight_tab)

        self.file_watcher.fileChanged.connect(self.do_things_on_file_changed)

    def do_things_on_file_changed(self, file_path_as_str: str):
        file_path = Path(file_path_as_str)
        do_reload = dialog('File Changed',
                        message=f'{file_path.name} has been changed elsewhere, do you want to reload it?')
        if do_reload:
            self.current_file = file_path
            QtWidgets.QApplication.processEvents()

            self.display_file_text(file_path, self.current_editor)

    def highlight_tab(self, tab_index: int):
        for ind in range(self.tab_widget.count()):
            self.tab_widget.tabBar().setTabTextColor(ind,
                                                     self.get_theme().blue if ind==tab_index else self.get_theme().text)

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

    @current_file.setter
    def current_file(self, file_path: Path):
        tab_index = self.files_path.index(file_path)
        self.tab_widget.setCurrentIndex(tab_index)
        self.highlight_tab(tab_index)

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

        self.file_watcher.removePath(str(file_path))
        with open(file_path, 'w', encoding="utf-8", newline='') as f:
            f.write(self.current_editor.get_text())
        self.current_editor.set_saved()
        self.file_watcher.addPath(str(file_path))

    def add_file(self, file_path: Path, display=True):
        """ Open and display a file content in a new editor"""
        self._save_path = file_path.parent
        self.file_watcher.addPath(str(file_path))

        monaco_widget = self.create_monaco_widget(file_path)
        tab_index = self.tab_widget.addTab(monaco_widget, file_path.name)
        self.tab_widget.setTabToolTip(tab_index, str(file_path))
        self.tab_widget.setCurrentIndex(tab_index)

        monaco_widget.file_status.connect(self.unsaved_tabname)

        if display:
            self.display_file_text(file_path, monaco_widget)

        monaco_widget.set_saved()

    def unsaved_tabname(self, file_status: FileStatus):
        for ind in range(self.tab_widget.count()):
            editor: MonacoWithFile = self.tab_widget.widget(ind)
            self.tab_widget.setTabText(ind, f'{editor.file_path.name}' if editor.saved else f'{editor.file_path.name}*')

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

    @staticmethod
    def check_python_syntax_valid(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            compile(f.read(), file_path, "exec")


def main():
    from pymodaq_gui.utils.utils import mkQApp
    from pymodaq_gui.editor import editor_main_loader

    qapp = mkQApp('Monaco')

    shared_ui, monaco_app = editor_main_loader()
    shared_ui.show()

    qapp.exec()

if __name__ == "__main__":
    main()
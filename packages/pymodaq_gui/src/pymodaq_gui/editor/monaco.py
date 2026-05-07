import copy
import pickle
from pathlib import Path
import dataclasses

import subprocess
import sys


from qtpy import QtWidgets
from qtpy.QtGui import QKeySequence, QTextCursor
from qtpy.QtCore import Qt, QFileSystemWatcher, Signal, QThread, QObject

from pymodaq_utils.config import get_set_local_dir, GlobalConfig, get_set_path
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_gui.messenger import dialog
from pymodaq_gui.utils import CustomApp
from pymodaq_gui.utils.shared_ui import MenuToolbarNames
from pymodaq_gui.utils.file_io import select_file


logger = set_logger(get_module_name(__file__))

try:
    import qtpy.QtWebEngineCore

    if not hasattr(qtpy.QtWebEngineCore, 'QWebEnginePage'):
        from qtpy.QtWebEngineWidgets import QWebEnginePage

        qtpy.QtWebEngineCore.QWebEnginePage = QWebEnginePage

    from qtmonaco import Monaco
except ImportError as e:
    msg = f"Could not import the QtMonaco Editor, make sure you installed it with pip install qtmonaco "\
          f"or with pip install pymodaq_gui[editor].\n"\
          f"If using pyqt5 try also adding this package: pip install PyQtWebEngine\n"\
          f"If using pyqt6 try also adding this package: pip install PyQt6-WebEngine"
    logger.warning(msg)
    e.msg = f'{msg}\n{e.msg}'
    raise e

LOCAL_PATH = get_set_path(get_set_local_dir(user=True), 'monaco_editor')
LOCAL_FILES_PATH = LOCAL_PATH.joinpath('monaco_files')

config = GlobalConfig()

subprocess_file = get_set_local_dir(user=True).joinpath('temp_exec')


class Redirect:
    def __init__(self, widget: QtWidgets.QTextEdit, autoscroll=True):
        self.widget = widget
        self.autoscroll = autoscroll

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

        proc = subprocess.Popen([sys.executable, str(file_path)], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        out, err = proc.communicate()
        if err:
            self.redirect.write('Error in subprocess:')
            self.redirect.write(err)
        if out:
            self.redirect.write('Output of subprocess:')
            self.redirect.write(out)


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
        _files = self.get_files_cache()
        if len(_files) != 0:
            for file in _files:
                self.add_file(file, display=True)

        self.highlight_tab(self.tab_widget.currentIndex())

    def get_files_cache(self) -> list[Path]:
        with open(self.local_files_path, 'rb') as f:
            _files = pickle.load(f)
        return _files

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
        self._thread = QThread()
        self._runner.moveToThread(self._thread)
        self._thread.finished.connect(self._runner.deleteLater)
        self.run_signal.connect(self._runner.do_subprocess)

        self._thread.start()

        self.run_signal.emit(file_path)

    def create_monaco_widget(self, file_path: Path) -> MonacoWithFile:
        monaco_widget = MonacoWithFile(file_path)
        monaco_widget.set_language("python")
        monaco_widget.set_theme('vs-dark' if self.get_theme().is_dark_theme() else 'vs')
        monaco_widget.set_minimap_enabled(True)
        return monaco_widget

    def setup_menus_and_toolbars(self, menubar: QtWidgets.QMenuBar = None):
        self.add_menu(MenuToolbarNames.FILE, 'File', parent_menu=menubar)
        self.add_menu('files', 'Recent Files', parent_menu=MenuToolbarNames.FILE)

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
        self.add_action('save_as', 'Save File As', 'save_as', 'Save file As',
                        toolbar='file', menu='file', auto_menu=True,
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_S))
        self.add_action('save_copy_as', 'Save a Copy As', 'save_as', 'Save a copy of the file as',
                        toolbar='file', menu='file', auto_menu=True)
        self.add_action('run_file', 'Run current File', 'start', 'Run the currently selected file',
                        toolbar='file', menu='file', auto_menu=True,)

    def connect_things(self):
        self.connect_action('load', lambda: self.load_file())
        self.connect_action('new', lambda: self.create_file())
        self.connect_action('save', self.save_file)
        self.connect_action('save_as', lambda: self.save_file_as())
        self.connect_action('save_copy_as', lambda: self.save_copy_file_as())

        self.connect_action('run_file', lambda: self.run_file())

        self.tab_widget.tabCloseRequested.connect(self.close_editor)
        self.tab_widget.tabBarClicked.connect(self.highlight_tab)
        self.tab_widget.currentChanged.connect(self.highlight_tab)

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

    def is_file_and_editor_content_same(self, tab_index: int) -> bool:
        file_content = self._get_file_content(self.get_editor_from_tab_index(tab_index).file_path)
        editor_content = self.get_editor_from_tab_index(tab_index).get_text()
        return file_content == editor_content

    def close_editor(self, tab_index: int):
        """ close the file and the editor of the given tab index"""

        if not self.is_file_and_editor_content_same(tab_index):
            do_remove = dialog(title="Closing",
                               message=f'Your file {self.get_editor_from_tab_index(tab_index).file_path.name }'
                                       f'has not been saved since last modification, '
                                       f'are you sure you want to close it?'
                                       )
        else:
            do_remove = True

        if do_remove:
            file_path = self.files_path[tab_index]
            self.file_watcher.removePath(str(file_path))
            self.tab_widget.removeTab(tab_index)

    def remove_file(self, file_path: Path):
        """ remove the editor corresponding to the specified file Path """
        tab_index = self.files_path.index(file_path)
        self.close_editor(tab_index)

    def create_file(self, file_path: Path = None, add_to_watcher=True):
        """ Create a new file and display it in a new tab """
        if file_path is None:
            try:
                current_directory = self.current_editor.file_path.parent
            except AttributeError:
                current_directory = self.local_path
            file_path = current_directory.joinpath('untitled.py')

        with open(file_path, 'w') as f:
            self.add_file(Path(f.name), add_to_watcher=add_to_watcher)

    def load_file(self, file_path: Path = None):
        """ Load a new file and display it in a new tab"""
        if file_path is None:
            file_path = select_file(start_path=self._save_path, save=False, ext='py')
        if file_path:
            self.add_file(file_path)

    def save_file(self):
        """ Save the current editor content in the corresponding file Path """
        self._save_file(self.current_file)

    def save_file_as(self, file_path: Path = None, add_to_watcher=True):
        """ Rename the current editor file content in a new file Path """
        if file_path is None:
            file_path = select_file(start_path=self._save_path, save=True, ext='py',
                                    force_save_extension=True)
        current_path = copy.copy(self.current_file)

        if file_path:
            self._save_file(file_path)
            self.add_file(file_path, add_to_watcher=add_to_watcher)
            self.remove_file(current_path)
            current_path.unlink()

    def save_copy_file_as(self, file_path: Path = None, add_to_watcher=True):
        """ Make a copy of the current editor content in a new file Path """
        if file_path is None:
            file_path = select_file(start_path=self._save_path, save=True, ext='py',
                                    force_save_extension=True)
        if file_path:
            self._save_file(file_path)
            self.add_file(file_path, add_to_watcher=add_to_watcher)

    def _save_file(self, file_path: Path = None):
        """ Save the current editor content in the specified file Path """
        if file_path is None:
            file_path = self.current_file

        self.file_watcher.removePath(str(file_path))
        with open(file_path, 'w', encoding="utf-8", newline='') as f:
            f.write(self.current_editor.get_text())
        self.current_editor.set_saved()
        self.file_watcher.addPath(str(file_path))

    def add_file(self, file_path: Path, display=True, add_to_watcher=True):
        """ Open and display a file content in a new editor"""
        self._save_path = file_path.parent
        if add_to_watcher:
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
            text = self._get_file_content(text)

        monaco_widget.set_text(text)

    @staticmethod
    def _get_file_content(file_path: Path) -> str:
        with open(file_path, 'r', encoding="utf-8", newline='') as f:
            text = ''.join(f.readlines())
        return text

    @property
    def local_files_path(self) -> Path:
        """ Get a file path to store currently opened files"""
        path =  LOCAL_FILES_PATH
        if not path.is_file():
            self._create_files_file([], path)
        return path

    def _create_files_file(self, files: list[Path], file_path: Path = None):
        if file_path is None:
            file_path = self.local_files_path
        with open(file_path, 'wb') as f:
            pickle.dump(files, f)

    @property
    def local_path(self) -> Path:
        """ Get a local file path to cache some data related to this application"""
        return LOCAL_PATH

    @property
    def files_path(self) -> list[Path]:
        """ Get the list of all opened files in the order of the displayed tabs"""
        return [self.tab_widget.widget(index_tab).file_path for index_tab in range(self.tab_widget.count())]

    def quit_fun(self):
        super().quit_fun()
        self._create_files_file(self.files_path)

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
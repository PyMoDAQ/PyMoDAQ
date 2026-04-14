import pickle
import tempfile
from collections import OrderedDict
from pathlib import Path


from qtmonaco import Monaco
from qtpy import QtWidgets
from qtpy.QtGui import QKeySequence
from qtpy.QtCore import Qt

from pymodaq_gui.editor.file_widget import FileWidget, FileWidgetAction
from pymodaq_utils.config import get_set_local_dir

from pymodaq_gui.utils.widgets.window import make_window

from pymodaq_gui.utils import CustomApp
from pymodaq_gui.utils.shared_ui import SharedUI, MenuNames
from pymodaq_gui.utils.file_io import select_file

from pymodaq_utils.config import GlobalConfig

config = GlobalConfig()


class MonacoApp(CustomApp):
    def __init__(self, parent: QtWidgets.QWidget = None,):
        super().__init__(parent, create_app_toolbar=False)

        self.monaco_widget: Monaco = None
        self._save_path = config('data', 'data_saving', 'h5file', 'save_path')

        self._files: list[Path] = []
        self._file_widgets: dict[Path, FileWidget] = OrderedDict([])

        self._current_file: Path = None

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
        self.filenames_group = QtWidgets.QButtonGroup()

        self.monaco_widget = Monaco()
        self.mainwindow.setCentralWidget(self.monaco_widget )
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
                        toolbar='file', menu='file', auto_menu=True,
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_N))
        self.add_action('save', 'Save File', 'file_save', 'Save file',
                        toolbar='file', menu='file', auto_menu=True,
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_S))
        self.add_action('load', 'Open File', 'file_open', 'Load file ',
                        toolbar='file', menu='file', auto_menu=True,
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_O))

        self.add_action('save_as', 'Save File As', 'save_as', 'Save file as',
                        toolbar='file', menu='file', auto_menu=True,
                        shortcut=QKeySequence(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_S))


    def connect_things(self):
        self.connect_action('load', self.load_file)
        self.connect_action('new', self.create_file)
        self.connect_action('save', self.save_file)
        self.connect_action('save_as', self.save_file_as)

    def create_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            self.add_file(Path(f.name))

    def load_file(self):
        file_path = select_file(start_path=self._save_path, save=False, ext='py')
        if file_path:
            self.add_file(file_path)

    def save_file(self):
        self._save_file(self._current_file)

    def save_file_as(self):

        file_path = select_file(start_path=self._save_path, save=True, ext='py',
                                force_save_extension=True)
        if file_path:
            self._save_file(file_path)
            self.remove_file(self._current_file)
            self.add_file(file_path)

    def _save_file(self, file_path: Path):
        with open(file_path, 'w', encoding="utf-8", newline='') as f:
            f.write(self.monaco_widget.get_text())

    def add_file(self, file_path: Path, display=True):
        self._files.append(file_path)
        self._save_path = file_path.parent

        # widget = FileWidget(file_path)
        # self._actions[str(file_path)] = self.get_toolbar('files').addWidget(widget)
        # self.get_menu('files').addAction(self._actions[str(file_path)])

        action_widget = FileWidgetAction(file_path)
        self.add_action(str(file_path), str(file_path), toolbar='files', menu='files',
                        action=action_widget)
        widget = action_widget.defaultWidget()

        self.filenames_group.addButton(widget.file_name_button)
        widget.file_name_button.setChecked(True)
        widget.file_name_button.toggled.connect(self._create_lambda_file_slot(file_path))
        widget.close_button.clicked.connect(lambda: self.remove_file(file_path))
        self._file_widgets[file_path] = widget

        if display:
            self.display_file_text(file_path)

    def _create_lambda_file_slot(self, file_path: Path):
        return lambda: self.display_file_text(file_path)

    def remove_file(self, file_path: Path):
        self.get_toolbar('files').removeAction(self.get_action(str(file_path)))

        index = list(self._file_widgets.keys()).index(file_path)
        if index > 0:
            self._current_file = list(self._file_widgets.keys())[index-1]
        elif len(self._file_widgets) > 1:
            self._current_file = list(self._file_widgets.keys())[1]
        else:
            self._current_file = None
            self.monaco_widget.set_text('')

        self._file_widgets.pop(file_path)
        self._files.remove(file_path)
        if self._current_file is not None:
            self._file_widgets[self._current_file].file_name_button.setChecked(True)

    def display_file_text(self, file_path: Path):

        #autosave previous file
        if self._current_file is not None:
            self._save_file(self._current_file)

        self._current_file = file_path
        with open(file_path, 'r', encoding="utf-8", newline='') as f:
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

    qapp.exec_()

if __name__ == "__main__":
    main()
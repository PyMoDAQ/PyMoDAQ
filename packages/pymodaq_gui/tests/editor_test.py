import pytest
from pathlib import Path
import qt_themes
from pymodaq_gui.editor import editor_main_loader
from pymodaq_gui.editor.monaco import MonacoApp, LOCAL_FILES_PATH

@pytest.fixture
def editor(qtbot):
    if LOCAL_FILES_PATH.is_file():
        LOCAL_FILES_PATH.unlink()
    qt_themes.set_theme('dracula')
    shared_ui, monaco_app = editor_main_loader()
    shared_ui.show()
    qtbot.addWidget(shared_ui.mainwindow)
    yield monaco_app
    shared_ui.quit_fun()


class TestEditor:

    def test_init(self, editor):
        assert isinstance(editor, MonacoApp)

    def test_create_file(self, editor, tmp_path ):
        tmp_file =  tmp_path.joinpath('afile.py')
        editor.create_file(tmp_file, add_to_watcher=False)

        assert editor.current_file == tmp_file
        assert editor.current_editor.get_text() == ''
        assert tmp_file in editor.files_path

    def test_add_remove_file(self, editor):
        file_here = Path(__file__)
        editor.add_file(file_here, add_to_watcher=False)

        assert editor.current_file == file_here
        assert editor.current_editor.get_text() == editor._get_file_content(file_here)
        assert file_here in editor.files_path

        editor.remove_file(file_here)
        assert file_here not in editor.files_path


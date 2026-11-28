from types import SimpleNamespace

import pytest
import qt_themes
from qtpy import QtWidgets

from pymodaq_gui.utils.custom_app import CustomApp, WorkFlowActions


class MyApp(CustomApp):
    """App recording the hooks that setup_ui calls"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []
        self.setup_ui()

    def setup_docks_and_widgets(self):
        self.calls.append('setup_docks_and_widgets')
        self.n_iter_widget = QtWidgets.QSpinBox()
        self.statusbar.addPermanentWidget(self.n_iter_widget)

    def setup_menus_and_toolbars(self, menubar=None):
        self.calls.append('setup_menus_and_toolbars')

    def setup_workflow_actions(self):
        self.calls.append('setup_workflow_actions')
        super().setup_workflow_actions()

    def setup_actions(self):
        self.calls.append('setup_actions')

    def connect_things(self):
        self.calls.append('connect_things')

    def do_things_after_ui_setup(self):
        self.calls.append('do_things_after_ui_setup')


class MyWorkflowApp(MyApp):
    show_workflow_actions = True


class MyDeprecatedApp(CustomApp):
    """App using the names of the hooks before they were renamed"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []
        self.setup_ui()

    def setup_docks(self):
        self.calls.append('setup_docks')

    def setup_menu(self, menubar=None):
        self.calls.append('setup_menu')


def make_app(qtbot, app_class):
    main_window = QtWidgets.QMainWindow()
    my_app = app_class(parent=main_window, title="My App")
    main_window.show()
    qtbot.addWidget(main_window)
    return main_window, my_app


@pytest.fixture()
def app(qtbot):
    main_window, my_app = make_app(qtbot, MyApp)
    yield my_app

    main_window.close()
    main_window.deleteLater()


def test_status_bar(app):
    my_app = app

    my_app.update_status('a message for 2s', wait_time=2000)
    my_app.n_iter_widget.setValue(24)


def test_setup_ui_calls_the_hooks_in_order(app):
    assert app.calls == ['setup_docks_and_widgets', 'setup_menus_and_toolbars', 'setup_actions', 'connect_things',
                         'do_things_after_ui_setup']
    assert not app.has_action(WorkFlowActions.START)


def test_workflow_actions_are_set_up_between_menus_and_actions(qtbot):
    qt_themes.set_theme('dracula')  # the icons of the workflow actions are colored from the theme
    main_window, my_app = make_app(qtbot, MyWorkflowApp)
    assert my_app.calls == ['setup_docks_and_widgets', 'setup_menus_and_toolbars', 'setup_workflow_actions',
                            'setup_actions', 'connect_things', 'do_things_after_ui_setup']
    assert my_app.has_action(WorkFlowActions.START)
    main_window.close()


def test_deprecated_hooks_are_still_called_with_a_warning(qtbot):
    with pytest.warns(DeprecationWarning):
        main_window, my_app = make_app(qtbot, MyDeprecatedApp)
    assert my_app.calls == ['setup_docks', 'setup_menu']
    main_window.close()


def test_quit_fun_closes_the_window(app):
    assert app.mainwindow.isVisible()
    assert app.quit_fun() is True
    assert not app.mainwindow.isVisible()


class TestSnapshot:
    def test_default_widget_is_the_main_window(self, app):
        assert app.snapshot_widget() is app.mainwindow

    def test_snapshot_is_saved_as_png(self, app, tmp_path):
        path = app.save_snapshot(tmp_path / 'picture.png')

        assert path == tmp_path / 'picture.png'
        assert path.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'

    def test_another_widget_can_be_chosen(self, app, tmp_path):
        widget = QtWidgets.QLabel('result')
        app.snapshot_widget = lambda: widget

        assert app.save_snapshot(tmp_path / 'picture.png') is not None

    def test_no_widget_gives_no_picture(self, app, tmp_path):
        app.snapshot_widget = lambda: None

        assert app.save_snapshot(tmp_path / 'picture.png') is None
        assert not (tmp_path / 'picture.png').exists()

    def test_unwritable_path_gives_no_picture(self, app, tmp_path):
        assert app.save_snapshot(tmp_path / 'missing_folder' / 'picture.png') is None

    def test_payload_is_empty_by_default(self, app):
        assert app.saving_payload() == {}

    def test_failing_snapshot_widget_gives_no_picture(self, app, tmp_path):
        def failing():
            raise RuntimeError('bug in the extension')
        app.snapshot_widget = failing

        assert app.save_snapshot(tmp_path / 'picture.png') is None

    def test_app_without_saver_has_no_saving_to_end(self, app):
        assert app.take_saving_snapshot() is None
        app.end_saving()  # nothing to end, no error


class FakeReporter:
    """A saver that tells the saving events, as the ExtensionSaver does"""

    def __init__(self, path):
        self.saving = SimpleNamespace(saving_id='abc')
        self.path = path
        self.ended = []

    def snapshot_file_path(self, saving_id=None):
        return self.path

    def end_saving(self, snapshot_path=None, saving_id=None):
        self.ended.append((snapshot_path, saving_id))


class TestSavingReporter:
    @pytest.fixture
    def reporter(self, app, tmp_path):
        reporter = FakeReporter(tmp_path / 'picture.png')
        app.__class__.module_and_data_saver = property(lambda self: reporter)
        yield reporter
        del app.__class__.module_and_data_saver

    def test_a_saver_that_does_not_tell_the_savings_is_no_reporter(self, app):
        assert app.saving_reporter is None
        assert app.current_saving_id() is None

    def test_reporter_is_the_saver_that_tells_the_savings(self, app, reporter):
        assert app.saving_reporter is reporter
        assert app.current_saving_id() == 'abc'

    def test_end_takes_the_picture_then_tells_the_saver(self, app, reporter, tmp_path):
        app.end_saving('abc')

        assert reporter.ended == [(tmp_path / 'picture.png', 'abc')]

    def test_end_without_saving_id_gives_none_to_the_saver(self, app, reporter):
        app.notify_saving_end()

        assert reporter.ended == [(None, None)]

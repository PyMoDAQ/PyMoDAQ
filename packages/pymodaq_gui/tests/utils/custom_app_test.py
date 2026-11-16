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

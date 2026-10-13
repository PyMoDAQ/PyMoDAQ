import warnings

import pytest
from qtpy import QtWidgets

from pymodaq_gui.utils.custom_app import CustomApp


class CurrentApp(CustomApp):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_ui()

    def setup_docks_and_widgets(self):
        super().setup_docks_and_widgets()  # an app calling the base method must not get a warning


class OldDocksApp(CurrentApp):
    def setup_docks(self):
        pass


class OldMenuApp(CurrentApp):
    def setup_menu(self, menubar=None):
        pass


class OldAppCallingTheBase(CurrentApp):
    """Old apps often call the method of the base class: it must stay available"""
    def __init__(self, *args, **kwargs):
        self.base_called = False
        super().__init__(*args, **kwargs)

    def setup_docks(self):
        super().setup_docks()
        self.base_called = True

    def setup_menu(self, menubar=None):
        super().setup_menu(menubar)


class ChildOfOldApp(OldDocksApp):
    """The old hook is also found when it is defined by a parent of the app"""


def make_app(qtbot, app_class):
    main_window = QtWidgets.QMainWindow()
    qtbot.addWidget(main_window)
    return app_class(parent=main_window, title="My App")


def test_no_deprecation_warning_for_an_app_using_the_current_hooks(qtbot):
    with warnings.catch_warnings():
        warnings.simplefilter('error', DeprecationWarning)
        make_app(qtbot, CurrentApp)


@pytest.mark.parametrize('app_class, name', [(OldDocksApp, 'setup_docks'), (OldMenuApp, 'setup_menu'),
                                             (ChildOfOldApp, 'setup_docks')])
def test_old_hook_still_called_with_a_warning(qtbot, app_class, name):
    with pytest.warns(DeprecationWarning, match=name):
        make_app(qtbot, app_class)


def test_base_methods_can_still_be_called_by_an_old_app(qtbot):
    with pytest.warns(DeprecationWarning):
        app = make_app(qtbot, OldAppCallingTheBase)
    assert app.base_called

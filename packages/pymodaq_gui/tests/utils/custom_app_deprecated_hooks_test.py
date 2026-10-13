import warnings

import pytest
from qtpy import QtWidgets

from pymodaq_gui.utils.custom_app import CustomApp


class CurrentApp(CustomApp):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_ui()


class OldDocksApp(CurrentApp):
    def setup_docks(self):
        pass


class OldMenuApp(CurrentApp):
    def setup_menu(self, menubar=None):
        pass


def make_app(qtbot, app_class):
    main_window = QtWidgets.QMainWindow()
    qtbot.addWidget(main_window)
    return app_class(parent=main_window, title="My App")


def test_base_class_does_not_define_the_old_hooks():
    assert not hasattr(CustomApp, 'setup_docks')
    assert not hasattr(CustomApp, 'setup_menu')


def test_no_deprecation_warning_for_an_app_using_the_current_hooks(qtbot):
    with warnings.catch_warnings():
        warnings.simplefilter('error', DeprecationWarning)
        make_app(qtbot, CurrentApp)


@pytest.mark.parametrize('app_class, name', [(OldDocksApp, 'setup_docks'), (OldMenuApp, 'setup_menu')])
def test_old_hook_still_called_with_a_warning(qtbot, app_class, name):
    with pytest.warns(DeprecationWarning, match=name):
        make_app(qtbot, app_class)

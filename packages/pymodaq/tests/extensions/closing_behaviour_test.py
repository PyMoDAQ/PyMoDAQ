"""Closing windows: what happens to the Dashboard and the other extensions when an extension or the Dashboard is closed

* closing an extension shows the Dashboard again (the extension is the only thing closed)
* unless ``extensions/extension_close_all`` is True: the extension then asks the Dashboard to quit, closing everything
* closing the Dashboard closes all its extensions, but any of them can refuse (``_quit_fun`` guard)
"""
from unittest.mock import MagicMock

import pytest

from pymodaq_gui.utils import DockArea
from pymodaq_utils.config import GlobalConfig

from pymodaq.extensions import ExtensionEnum
from pymodaq.utils import custom_ext
from pymodaq.utils.custom_ext import CustomExt
from pymodaq.utils.plugin_testing import loaded_extension

CONFIG_KEYS = ('pymodaq', 'extensions', 'extension_close_all')


class Ext(CustomExt):
    can_quit = True

    def __init__(self, parent, dashboard):
        super().__init__(parent, dashboard)
        self.setup_ui()

    def setup_menus_and_toolbars(self, menubar=None):
        super().setup_menus_and_toolbars(menubar)
        if self.dashboard is not None:
            self.create_dashboard_toolbar()  # holds the action showing the Dashboard, as in the extension template

    def _quit_fun(self):
        return self.can_quit


@pytest.fixture
def close_all(monkeypatch):
    """Set the value of the ``extension_close_all`` option without touching the configuration file"""
    config = custom_ext.config

    def set_value(value: bool):
        def fake_config(*keys):
            return value if keys == CONFIG_KEYS else config(*keys)
        monkeypatch.setattr(custom_ext, 'config', fake_config)

    return set_value


@pytest.fixture
def loaded():
    """An extension in a Dashboard, known by the extension manager of the Dashboard (as when it is loaded from it)"""
    with loaded_extension(Ext) as (dashboard, extension):
        dashboard.extension_manager.loaded_extensions[ExtensionEnum.CONSOLE] = extension
        yield dashboard, extension
        dashboard.extension_manager.loaded_extensions.clear()


def spy_on_quit(dashboard):
    """Count the calls of Dashboard.quit_fun, without changing what it does"""
    spy = MagicMock(wraps=dashboard.quit_fun)
    dashboard.quit_fun = spy
    return spy


def test_extension_close_all_is_false_by_default():
    assert GlobalConfig()(*CONFIG_KEYS) is False


def test_dashboard_extensions_are_the_ones_of_the_extension_manager(loaded):
    dashboard, extension = loaded
    assert dashboard.extensions is dashboard.extension_manager.loaded_extensions
    assert dashboard.extensions[ExtensionEnum.CONSOLE] is extension


def test_closing_an_extension_closes_only_the_extension(loaded):
    dashboard, extension = loaded
    spy = spy_on_quit(dashboard)
    extension.mainwindow.show()
    assert not dashboard.mainwindow.isVisible()

    assert extension.quit_fun() is True

    assert not extension.mainwindow.isVisible()
    assert dashboard.mainwindow.isVisible()  # the Dashboard is shown again, it is not closed
    spy.assert_not_called()


def test_closing_an_extension_asks_the_dashboard_to_quit_when_close_all_is_set(loaded, close_all):
    close_all(True)
    dashboard, extension = loaded
    dashboard.quit_fun = MagicMock(return_value=True)

    assert extension.quit_fun() is True

    dashboard.quit_fun.assert_called_once_with()


def test_close_all_closes_the_dashboard_and_the_extension_once(loaded, close_all):
    close_all(True)
    dashboard, extension = loaded
    spy = spy_on_quit(dashboard)
    extension.mainwindow.show()
    dashboard.mainwindow.show()

    assert extension.quit_fun() is True

    spy.assert_called_once_with()  # the Dashboard does not call back the extension in a loop
    assert not extension.mainwindow.isVisible()
    assert not dashboard.mainwindow.isVisible()


def test_the_dashboard_quits_its_extensions_as_an_external_call(loaded, close_all):
    """With close_all the extension would otherwise ask the Dashboard to quit, that quits the extension, that..."""
    close_all(True)
    dashboard, extension = loaded
    extension.quit_fun = MagicMock(return_value=True)

    dashboard.quit_fun()

    extension.quit_fun.assert_called_once_with(external_call=True)


def test_closing_the_dashboard_closes_the_extensions(loaded):
    dashboard, extension = loaded
    extension.mainwindow.show()

    assert dashboard.quit_fun() is True

    assert not extension.mainwindow.isVisible()


@pytest.mark.parametrize('close_all_value', [False, True])
def test_an_extension_refusing_to_quit_keeps_everything_open(loaded, close_all, close_all_value):
    close_all(close_all_value)
    dashboard, extension = loaded
    extension.can_quit = False
    extension.mainwindow.show()
    dashboard.mainwindow.show()
    remove_modules = MagicMock()
    dashboard.remove_modules = remove_modules  # called when the Dashboard really quits

    assert not extension.quit_fun()
    assert dashboard.quit_fun() is False

    assert extension.mainwindow.isVisible()
    assert dashboard.mainwindow.isVisible()
    remove_modules.assert_not_called()


def test_the_dashboard_quits_if_all_the_extensions_agree(loaded):
    dashboard, extension = loaded
    other = MagicMock()
    other.quit_fun.return_value = True
    dashboard.extension_manager.loaded_extensions[ExtensionEnum.SCANNER] = other

    assert dashboard.quit_fun() is True

    other.quit_fun.assert_called_once_with(external_call=True)
    assert not extension.mainwindow.isVisible()


def test_close_all_without_dashboard_only_closes_the_extension(close_all):
    close_all(True)
    extension = Ext(DockArea(), None)

    assert extension.quit_fun() is True

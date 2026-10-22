"""Tools to test the dashboard extensions of a plugin package (or of PyMoDAQ), without hardware.

* :func:`loaded_extension`: context manager building an empty Dashboard, loading an extension class in it as the
  Dashboard menu does, and closing everything cleanly afterwards.
* :class:`PluginExtensionChecks`: pytest mixin, one test per extension of the package, checking that it loads and closes.

Example, in a test module of a plugin repository::

    from pymodaq.utils.plugin_testing import loaded_extension, PluginExtensionChecks
    from pymodaq_plugins_myplugin.extensions.my_extension import MyExtension

    class TestExtensions(PluginExtensionChecks):  # one loading test per extension of the package
        pass

    def test_my_extension_flow():
        with loaded_extension(MyExtension) as (dashboard, extension):
            extension.settings.child('main_settings', 'do_something').setValue(True)
            assert extension.modules_manager is not None

.. versionadded:: 5.3.7
"""
import contextlib
import importlib
import pkgutil
from pathlib import Path
from typing import Iterator, Optional

import pytest
from qtpy import QtCore, QtWidgets

from pyqtgraph import mkQApp
from pymodaq_utils.plugin_tools.checks import guess_package_name


def _flush_deleted_widgets():
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    QtWidgets.QApplication.processEvents()


@contextlib.contextmanager
def loaded_extension(extension_class: type, *ext_args, show: bool = False, theme: bool = False,
                     **ext_kwargs) -> Iterator[tuple['DashBoard', 'CustomExt']]:  # noqa: F821
    """Load an extension in an empty Dashboard and close both on exit.

    Parameters
    ----------
    extension_class: type
        A ``CustomExt`` subclass.
    ext_args, ext_kwargs:
        Given to the extension after the ``DockArea`` and the ``DashBoard`` (as ``create_extension`` does).
    show: bool
        Show the Dashboard and extension windows (False by default, no visible GUI is needed).
    theme: bool
        Apply the PyMoDAQ theme again, even if one is already set. Useful only to test the styling: it makes every
        widget alive process style events. By default the theme is applied only if the application has none.

    Yields
    ------
    tuple
        The ``DashBoard`` and the extension instance. The windows are closed and deleted on exit, even when the body of
        the ``with`` fails: left alive, they slow down the event loop of every test run afterwards.
    """
    from pymodaq.dashboard import create_load_dashboard
    from pymodaq.utils.gui_utils.loader_utils import create_extension

    import qt_themes
    from pymodaq_gui.qt_utils import apply_styling_rules

    app = mkQApp('extension_test')  # a bare QApplication: the Dashboard needs a theme, applied only once (or on demand)
    if theme or qt_themes.get_theme() is None:  # restyling an application with many live widgets can even crash Qt
        apply_styling_rules(app)

    shared_ui, dashboard = create_load_dashboard(show_dashboard=show)
    win_ext, extension = create_extension(dashboard, extension_class, *ext_args, show_extension=show, **ext_kwargs)
    try:
        yield dashboard, extension
    finally:
        try:
            extension.quit_fun()
            QtWidgets.QApplication.processEvents()
        finally:
            dashboard.quit_fun()
            # the quit functions do not delete the windows
            for widget in (win_ext.mainwindow, shared_ui.parent, dashboard.tree):
                widget.close()
                widget.deleteLater()
            _flush_deleted_widgets()


def find_extension_classes(package: str) -> list[tuple[str, type]]:
    """The extensions defined in the ``extensions`` folder of a plugin package, as ``(EXTENSION_NAME, class)`` pairs

    The modules are imported, following what the Dashboard does: a module is an extension if it has an
    ``EXTENSION_NAME``, and its class is the one named by ``CLASS_NAME``. An import error is raised, not hidden.
    """
    try:
        folder = importlib.import_module(f'{package}.extensions')
    except ModuleNotFoundError as e:
        if e.name == f'{package}.extensions':
            return []
        raise
    found = []
    for info in pkgutil.iter_modules(list(folder.__path__)):
        if info.name.startswith('_'):
            continue
        module = importlib.import_module(f'{package}.extensions.{info.name}')
        if hasattr(module, 'EXTENSION_NAME'):
            found.append((module.EXTENSION_NAME, getattr(module, module.CLASS_NAME)))
    return found


class PluginExtensionChecks:
    """Mixin to subclass in a test module of a plugin repository: one test per extension of the package.

    Each extension is loaded in an empty Dashboard and closed (:func:`loaded_extension`). This is the same check as
    the one done for the extensions of PyMoDAQ. The behaviour of an extension is specific to it: write its tests with
    :func:`loaded_extension`.

    The tests are not part of :class:`PluginPackageChecks`: they create windows, and a package that has no extension
    should not need Qt in its tests.
    """
    package_name: Optional[str] = None
    strict_imports = False  # if True, an extension that cannot be imported because of a missing third party module
    # fails instead of being skipped (recommended in the CI of a plugin as its dependencies are installed there)

    def pytest_generate_tests(self, metafunc):
        if 'extension_info' not in metafunc.fixturenames:
            return
        package = self.package_name or guess_package_name(Path(str(metafunc.definition.fspath)).parent)
        try:
            extensions = find_extension_classes(package)
        except ImportError as e:
            if self.strict_imports:
                raise
            extensions = [pytest.param(None, marks=pytest.mark.skip(f'extension not importable: {e}'), id='import')]
        metafunc.parametrize('extension_info', extensions, ids=[
            e.id if hasattr(e, 'id') else e[1].__name__ for e in extensions])

    def test_extension_loads_and_closes(self, extension_info):
        name, extension_class = extension_info
        with loaded_extension(extension_class) as (dashboard, extension):
            assert isinstance(extension, extension_class)
            assert extension.dashboard is dashboard
            assert extension.modules_manager is not None

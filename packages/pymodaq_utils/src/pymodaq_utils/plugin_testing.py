"""Pytest mixin applying the acceptance checks of :mod:`pymodaq_utils.plugin_checks` to a plugin package.

It is in ``pymodaq_utils`` (and not in ``pymodaq``) so that importing it does not start the whole PyMoDAQ
initialization. Use it in a test module of a plugin repository::

    from pymodaq_utils.plugin_testing import PluginPackageChecks

    class TestMyPlugin(PluginPackageChecks):
        package_name = 'pymodaq_plugins_myinstrument'  # optional, found from the package folder if omitted
        fail_on = 'error'  # or 'warning', 'todo'
        strict_imports = True

.. versionadded:: 5.4.0
"""
from pathlib import Path
from typing import Optional

import pytest

from pymodaq_utils.plugin_checks import (VIEWER_DIMS, PluginModule, check_package_layout, check_package_sources,
                                         check_plugin_module, find_plugin_modules, guess_package_name)


class PluginPackageChecks:
    """Mixin to subclass in a test module of a plugin repository, see the module documentation.

    Test classes are parametrized per plugin module so that every failure is reported individually.
    """
    package_name: Optional[str] = None
    fail_on = 'error'  # 'error', 'warning' or 'todo' (the unfinished parts: TODO comments, placeholders...): the
    # findings of the static rules of this level and above fail the tests
    strict_imports = False  # if True, a module that cannot be imported because of a missing third party module or
    # SDK fails instead of being skipped (recommended in the CI of a plugin as its dependencies are installed there)

    @pytest.fixture
    def package(self, request) -> str:
        return self.package_name or guess_package_name(Path(request.fspath).parent)

    def pytest_generate_tests(self, metafunc):
        if 'plugin_module' not in metafunc.fixturenames:
            return
        package = self.package_name or guess_package_name(Path(str(metafunc.definition.fspath)).parent)
        kinds = {'move': ('move',), 'viewer': VIEWER_DIMS}
        wanted = metafunc.function.__name__
        modules = [m for m in find_plugin_modules(package)
                   if m.kind in (kinds['move'] if '_move_' in wanted else kinds['viewer'])]
        metafunc.parametrize('plugin_module', modules, ids=str)

    def test_package_layout(self, package):
        problems = check_package_layout(package)
        assert not problems, '\n'.join(problems)

    def test_move_plugin(self, plugin_module):
        self._assert_module_ok(plugin_module)

    def test_viewer_plugin(self, plugin_module):
        self._assert_module_ok(plugin_module)

    def test_package_sources(self, package):
        result = check_package_sources(package)
        messages = result.failing(self.fail_on)
        assert not messages, '\n'.join(messages)

    def _assert_module_ok(self, plugin_module: PluginModule):
        result = check_plugin_module(plugin_module)
        messages = result.failing(self.fail_on, self.strict_imports)
        assert not messages, '\n'.join(messages)
        if result.warnings:
            pytest.skip('; '.join(result.warnings))

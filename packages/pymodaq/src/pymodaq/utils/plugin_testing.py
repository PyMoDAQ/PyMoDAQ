"""Reusable acceptance checks for PyMoDAQ instrument plugins (``pymodaq_plugins_*``).

No hardware is needed: the checks are static / import-level. Use them in a plugin repository with::

    from pymodaq.utils.plugin_testing import PluginPackageChecks

    class TestMyPlugin(PluginPackageChecks):
        package_name = 'pymodaq_plugins_myinstrument'  # optional, read from the nearest pyproject.toml if omitted

Every check is also exposed as a plain function returning a list of problems (empty if all is fine), see
``check_move_class``, ``check_viewer_class`` and ``check_package_layout``.

To get a report without pytest, for any installed plugin package::

    from pymodaq.utils.plugin_testing import check_plugin_package
    print(check_plugin_package('pymodaq_plugins_mock'))

.. versionadded:: 5.3.0
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pytest
import toml
from pyqtgraph.parametertree import Parameter

from pymodaq_data import Unit
from pymodaq_utils.utils import get_entrypoints

from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base

VIEWER_DIMS = ('0D', '1D', '2D', 'ND')
ENTRYPOINT_GROUPS = ('pymodaq.plugins', 'pymodaq.instruments')
OPTIONAL_ENTRYPOINT_GROUPS = ('pymodaq.extensions', 'pymodaq.models', 'pymodaq.pid_models',
                              'pymodaq.scanners', 'pymodaq.h5exporters')

# methods that have to be overridden by the plugin (they are abstract in the base classes, but these are not
# enforced as the bases are QObjects)
MANDATORY_MOVE_METHODS = ('ini_stage', 'get_actuator_value', 'stop_motion', 'close')
MANDATORY_VIEWER_METHODS = ('ini_detector', 'grab_data', 'stop', 'close')

PACKAGE_NAME_RE = re.compile(r'^pymodaq_plugins_\w+$')


@dataclass(frozen=True)
class PluginModule:
    """A plugin module found in a plugin package."""
    package: str
    module_name: str  # e.g. daq_move_Mock
    kind: str  # 'move' or '0D', '1D', '2D', 'ND' for viewers

    @property
    def import_path(self) -> str:
        if self.kind == 'move':
            return f'{self.package}.daq_move_plugins.{self.module_name}'
        return f'{self.package}.daq_viewer_plugins.plugins_{self.kind}.{self.module_name}'

    @property
    def prefix(self) -> str:
        return 'daq_move_' if self.kind == 'move' else f'daq_{self.kind}viewer_'

    @property
    def name(self) -> str:
        return self.module_name[len(self.prefix):]

    @property
    def class_name(self) -> str:
        return f'DAQ_Move_{self.name}' if self.kind == 'move' else f'DAQ_{self.kind}Viewer_{self.name}'

    @property
    def base_class(self) -> type:
        return DAQ_Move_base if self.kind == 'move' else DAQ_Viewer_base

    def __str__(self):
        return self.module_name


def _submodule_names(package_path: str) -> list[str]:
    """Names of modules (not packages) found in a package, without importing them."""
    return sorted(m.name for m in pkgutil.iter_modules([package_path]) if not m.ispkg)


def find_plugin_modules(package: str) -> list[PluginModule]:
    """Find all plugin modules of a plugin package from the file system (no plugin module is imported).

    Modules that don't follow the naming convention (``daq_move_*``, ``daq_{N}viewer_*``) are reported by
    :func:`check_package_layout`.
    """
    found = []
    try:
        move_pkg = importlib.import_module(f'{package}.daq_move_plugins')
        found.extend(PluginModule(package, name, 'move') for name in _submodule_names(list(move_pkg.__path__)[0])
                     if name.startswith('daq_move_'))
    except ModuleNotFoundError:
        pass
    for dim in VIEWER_DIMS:
        try:
            viewer_pkg = importlib.import_module(f'{package}.daq_viewer_plugins.plugins_{dim}')
        except ModuleNotFoundError:
            continue
        found.extend(PluginModule(package, name, dim) for name in _submodule_names(list(viewer_pkg.__path__)[0])
                     if name.startswith(f'daq_{dim}viewer_'))
    return found


def guess_package_name(start: Path) -> str:
    """Get the plugin package name from the nearest pyproject.toml above ``start``"""
    for folder in [start, *start.parents]:
        pyproject = folder / 'pyproject.toml'
        if pyproject.is_file():
            return toml.load(pyproject)['project']['name'].replace('-', '_')
    raise FileNotFoundError(f'No pyproject.toml found above {start}, define package_name explicitly')


def _is_overridden(klass: type, base: type, method: str) -> bool:
    return getattr(klass, method, None) is not None and getattr(klass, method) is not getattr(base, method, None)


def check_package_layout(package: str) -> list[str]:
    """Package name, entry points, mandatory sub-modules and naming of the plugin modules"""
    problems = []
    if not PACKAGE_NAME_RE.match(package):
        problems.append(f"Package name '{package}' should be of the form pymodaq_plugins_<name>")
    try:
        pkg = importlib.import_module(package)
    except Exception as e:
        return problems + [f'Package {package} cannot be imported: {e!r}']
    for attr in ('config', '__version__'):
        if not hasattr(pkg, attr):
            problems.append(f"{package}/__init__.py should define '{attr}'")
    try:
        importlib.import_module(f'{package}.utils')
    except Exception as e:
        problems.append(f'{package}.utils cannot be imported: {e!r}')

    entry_names = {ep.value.split(':')[0] for group in ENTRYPOINT_GROUPS for ep in get_entrypoints(group)}
    if package not in entry_names:
        problems.append(f'No entry point of groups {ENTRYPOINT_GROUPS} points to {package}: is the plugin installed, '
                        f'and does its pyproject.toml declare the entry points?')
    for group in OPTIONAL_ENTRYPOINT_GROUPS:
        for ep in get_entrypoints(group):
            if ep.value.split(':')[0].split('.')[0] == package:
                try:
                    ep.load()
                except Exception as e:
                    problems.append(f'Entry point {group}:{ep.name} cannot be loaded: {e!r}')

    # module naming: everything in daq_move_plugins / plugins_{N}D should follow the convention
    plugin_pkgs = [(f'{package}.daq_move_plugins', 'daq_move_')] + \
                  [(f'{package}.daq_viewer_plugins.plugins_{dim}', f'daq_{dim}viewer_') for dim in VIEWER_DIMS]
    for pkg_path, prefix in plugin_pkgs:
        try:
            sub = importlib.import_module(pkg_path)
        except ModuleNotFoundError:
            continue
        for name in _submodule_names(list(sub.__path__)[0]):
            if not name.startswith(prefix):
                problems.append(f"Module {pkg_path}.{name} should be named '{prefix}<Name>'")
    return problems


def _check_params(klass: type) -> list[str]:
    problems = []
    params = klass.params
    if not isinstance(params, list) or not all(isinstance(p, dict) for p in params):
        return [f'{klass.__name__}.params should be a list of dict']
    try:
        tree = Parameter.create(name='settings', type='group', children=params)
    except Exception as e:
        return [f'{klass.__name__}.params cannot build a Parameter tree: {e!r}']
    names = [child.name() for child in tree.children()]
    duplicates = {n for n in names if names.count(n) > 1}
    if duplicates:
        problems.append(f'{klass.__name__}.params has duplicated top level names: {sorted(duplicates)}')
    return problems


def _check_methods(klass: type, base: type, mandatory) -> list[str]:
    problems = [f'{klass.__name__} should override {m}()' for m in mandatory if not _is_overridden(klass, base, m)]
    if inspect.isabstract(klass):  # in case a base ever becomes a real ABC
        problems.append(f'{klass.__name__} is abstract: {sorted(klass.__abstractmethods__)}')
    return problems


def check_move_class(klass: type) -> list[str]:
    """Checks on an actuator plugin class"""
    if not (inspect.isclass(klass) and issubclass(klass, DAQ_Move_base)):
        return [f'{klass} should derive from DAQ_Move_base']
    problems = _check_methods(klass, DAQ_Move_base, MANDATORY_MOVE_METHODS)
    problems += _check_params(klass)

    axis_names = klass.get_class_axis_names()
    units = klass._controller_units
    if isinstance(units, str):
        unit_list = [units]
    elif isinstance(units, (list, dict)):
        unit_list = list(units.values()) if isinstance(units, dict) else units
        if not isinstance(units, type(axis_names)):
            problems.append(f'_controller_units ({type(units).__name__}) should be of the same type as '
                            f'_axis_names ({type(axis_names).__name__}), or a single str')
        elif len(units) != len(axis_names):
            problems.append('_controller_units should define one unit per axis')
    else:
        return problems + [f'_controller_units has an invalid type: {type(units).__name__}']
    for unit in unit_list:
        try:
            Unit(unit)
        except Exception:
            problems.append(f"Unit '{unit}' in _controller_units is unknown from pint")

    epsilons = klass._epsilons
    if epsilons is not None and not isinstance(epsilons, (int, float)):
        if not isinstance(epsilons, type(axis_names)) or len(epsilons) != len(axis_names):
            problems.append('_epsilons should be a number or have the same type and length as _axis_names')
    if isinstance(axis_names, list) and len(set(axis_names)) != len(axis_names):
        problems.append('_axis_names contains duplicates')
    if klass.is_multiaxes is False and len(axis_names) > 1:
        problems.append('_axis_names defines several axes but is_multiaxes is False')
    return problems


def check_viewer_class(klass: type) -> list[str]:
    """Checks on a detector plugin class"""
    if not (inspect.isclass(klass) and issubclass(klass, DAQ_Viewer_base)):
        return [f'{klass} should derive from DAQ_Viewer_base']
    problems = _check_methods(klass, DAQ_Viewer_base, MANDATORY_VIEWER_METHODS)
    problems += _check_params(klass)
    return problems


class PluginLoadError(Exception):
    """A plugin module cannot be imported or does not define the expected class"""


def load_plugin_class(plugin_module: PluginModule) -> type:
    """Import a plugin module and return its plugin class

    Raises
    ------
    PluginLoadError
        with an explicit message if the module cannot be imported or lacks the expected class
    """
    try:
        module = importlib.import_module(plugin_module.import_path)
    except Exception as e:
        raise PluginLoadError(f'{plugin_module.import_path} cannot be imported '
                              f'(are vendor SDK imports guarded?): {e!r}') from e
    klass = getattr(module, plugin_module.class_name, None)
    if klass is None:
        raise PluginLoadError(f'{plugin_module.import_path} should define a class named {plugin_module.class_name}')
    return klass


def check_plugin_module(plugin_module: PluginModule) -> list[str]:
    """Load a plugin module and run the checks relevant for its kind, returns the list of problems"""
    try:
        klass = load_plugin_class(plugin_module)
    except PluginLoadError as e:
        return [str(e)]
    return check_move_class(klass) if plugin_module.kind == 'move' else check_viewer_class(klass)


@dataclass
class CheckResult:
    """Problems found on one item (the package itself or one of its plugin modules)"""
    item: str
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


@dataclass
class PluginReport:
    """Result of all the checks on a plugin package, see :func:`check_plugin_package`"""
    package: str
    results: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(res.ok for res in self.results)

    @property
    def failures(self) -> list[CheckResult]:
        return [res for res in self.results if not res.ok]

    def to_dict(self) -> dict:
        return {'package': self.package, 'ok': self.ok,
                'results': {res.item: res.problems for res in self.results}}

    def __str__(self) -> str:
        lines = [f'{self.package}: {"OK" if self.ok else f"{len(self.failures)} item(s) with problems"} '
                 f'({len(self.results)} checked)']
        for res in self.results:
            lines.append(f'  [{"ok" if res.ok else "FAIL"}] {res.item}')
            lines.extend(f'         - {problem}' for problem in res.problems)
        return '\n'.join(lines)


def check_plugin_package(package: str) -> PluginReport:
    """Run all the checks on an installed plugin package and return a report, without using pytest

    Examples
    --------
    >>> report = check_plugin_package('pymodaq_plugins_mock')
    >>> print(report)
    >>> report.ok
    """
    report = PluginReport(package, [CheckResult('package layout', check_package_layout(package))])
    try:
        modules = find_plugin_modules(package)
    except Exception as e:
        report.results.append(CheckResult('plugin discovery', [f'Cannot list the plugin modules: {e!r}']))
        return report
    report.results.extend(CheckResult(str(mod), check_plugin_module(mod)) for mod in modules)
    return report


class PluginPackageChecks:
    """Mixin to subclass in a test module of a plugin repository, see the module documentation.

    Test classes are parametrized per plugin module so that every failure is reported individually.
    """
    package_name: Optional[str] = None

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
        problems = check_plugin_module(plugin_module)
        assert not problems, '\n'.join(problems)

    def test_viewer_plugin(self, plugin_module):
        problems = check_plugin_module(plugin_module)
        assert not problems, '\n'.join(problems)

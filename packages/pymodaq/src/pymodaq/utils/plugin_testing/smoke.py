"""PROTOTYPE of an automatic smoke test of an instrument plugin class (not exported, not documented, may change).

The vendor libraries a plugin imports (``pylablib``, ``serial``, ``clr``...) are replaced by stand-ins that accept any
call, and the plugin is then driven the way the Dashboard does it: initialization, reading the position or
grabbing data, moving, closing. What is checked is only the PyMoDAQ contract: return types, units, signals emitted,
no exception. Nothing says that the instrument would answer what the stand-in does: see ``Finding.stand_in`` for the
steps whose failure may come from the stand-in itself.
"""
import importlib
import importlib.abc
import importlib.machinery
import math
import sys
import traceback
import types
from dataclasses import dataclass, field
from typing import Optional
from unittest import mock

import numpy as np

from pymodaq_data.data import DataToExport, DataWithAxes

from pymodaq.utils.data import DataActuator
from pymodaq.utils.plugin_testing.harness import (_instantiate, grab_and_wait, move_abs_and_wait,
                                                  SignalTimeout)

NEVER_STUBBED = ('pymodaq', 'pymodaq_utils', 'pymodaq_data', 'pymodaq_gui', 'pymodaq_scripting', 'qtpy', 'numpy',
                 'scipy', 'pyqtgraph', 'PyQt5', 'PyQt6', 'PySide6', 'PySide2', 'pint', 'h5py', 'tables')


class _StubModule(types.ModuleType):
    """A module in which any attribute is a ``MagicMock`` and any submodule is a stub as well"""
    __path__ = []

    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(name)
        value = mock.MagicMock(name=f'{self.__name__}.{name}')
        setattr(self, name, value)
        return value


class _StubFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Last resort of the import system: provides a stub for what is not installed (and is not part of PyMoDAQ)"""

    def __init__(self):
        self.stubbed = []

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in NEVER_STUBBED:
            return None
        parent = sys.modules.get(fullname.rpartition('.')[0])
        if parent is not None and not isinstance(parent, _StubModule):
            return None  # a missing module of a package that exists is a bug of that package, not a missing library
        self.stubbed.append(fullname)
        return importlib.machinery.ModuleSpec(fullname, self, is_package=True)

    def create_module(self, spec):
        return _StubModule(spec.name)

    def exec_module(self, module):
        pass


@dataclass
class Finding:
    step: str
    ok: bool
    message: str = ''
    # the step failed in the code of the plugin on a value coming from the stand-in: a possible false alarm
    stand_in: bool = False


@dataclass
class Report:
    plugin: str
    findings: list = field(default_factory=list)
    stubbed_modules: list = field(default_factory=list)

    @property
    def ok(self):
        return all(f.ok for f in self.findings)


def _where(exc: BaseException) -> str:
    """Last frame of the traceback that is in a file of the plugin (not of PyMoDAQ)"""
    frames = [f for f in traceback.extract_tb(exc.__traceback__)
              if 'pymodaq/' not in f.filename.replace('\\', '/') or 'pymodaq_plugins' in f.filename]
    frame = frames[-1] if frames else traceback.extract_tb(exc.__traceback__)[-1]
    return f'{type(exc).__name__}: {exc} [{frame.filename.split("/")[-1]}:{frame.lineno}]'


def _is_mock_value(value) -> bool:
    return isinstance(value, mock.NonCallableMock) or (isinstance(value, np.ndarray) and value.dtype == object)


def _step(report: Report, name: str, func, stand_in_hint: bool = True):
    try:
        message = func()
        report.findings.append(Finding(name, True, message or ''))
        return True
    except BaseException as e:  # noqa: a crash of the plugin must never stop the report
        if isinstance(e, KeyboardInterrupt):
            raise
        text = _where(e)
        mocky = stand_in_hint and ('Mock' in text or 'stand' in text or 'MagicMock' in repr(e))
        report.findings.append(Finding(name, False, text, stand_in=mocky))
        return False


def smoke_actuator(plugin_class) -> Report:
    report = Report(plugin_class.__name__)
    holder = {}

    def instantiate():
        holder['plugin'] = _instantiate(plugin_class, None, {})
    if not _step(report, 'instantiate', instantiate, False):
        return report
    plugin = holder['plugin']

    def ini():
        result = plugin.ini_stage(None)
        assert isinstance(result, tuple) and len(result) == 2, f'ini_stage returned {type(result).__name__}, not (info, bool)'
        assert isinstance(result[1], (bool, np.bool_)), f'ini_stage second item is {type(result[1]).__name__}, not bool'
        assert isinstance(result[0], str), f'ini_stage first item is {type(result[0]).__name__}, not str'
        plugin.init_info, plugin.initialized = result
        assert result[1], f'ini_stage reported a failure: {result[0]}'
    if not _step(report, 'ini_stage', ini):
        return report

    def read():
        value = plugin.get_actuator_value()
        assert isinstance(value, (DataActuator, float, int, np.floating)), \
            f'get_actuator_value returned {type(value).__name__}'
        if isinstance(value, DataActuator):
            number = float(np.asarray(value.value()))
            assert math.isfinite(number), 'position is not a finite number'
            assert value.units is not None, 'position has no units'
        else:
            assert math.isfinite(float(value)), 'position is not a finite number'
        holder['value'] = value
    _step(report, 'get_actuator_value', read)

    def move():
        value = holder.get('value')
        target = float(np.asarray(value.value())) if isinstance(value, DataActuator) else 1.
        position = move_abs_and_wait(plugin, target + 1., timeout_ms=3000)
        assert isinstance(position, DataActuator), f'move_done_signal carried a {type(position).__name__}'
    _step(report, 'move_abs', move)

    _step(report, 'stop_motion', plugin.stop_motion)
    _step(report, 'close', plugin.close)
    return report


def smoke_detector(plugin_class) -> Report:
    report = Report(plugin_class.__name__)
    holder = {}

    def instantiate():
        holder['plugin'] = _instantiate(plugin_class, None, {})
    if not _step(report, 'instantiate', instantiate, False):
        return report
    plugin = holder['plugin']

    def ini():
        result = plugin.ini_detector(None)
        assert isinstance(result, tuple) and len(result) == 2, f'ini_detector returned {type(result).__name__}, not (info, bool)'
        assert isinstance(result[1], (bool, np.bool_)), f'ini_detector second item is {type(result[1]).__name__}, not bool'
        assert isinstance(result[0], str), f'ini_detector first item is {type(result[0]).__name__}, not str'
        plugin.init_info, plugin.initialized = result
        assert result[1], f'ini_detector reported a failure: {result[0]}'
    if not _step(report, 'ini_detector', ini):
        return report

    def grab():
        dte = grab_and_wait(plugin, 1, timeout_ms=3000)
        assert isinstance(dte, DataToExport), f'dte_signal carried a {type(dte).__name__}'
        assert len(dte) > 0, 'empty DataToExport'
        for dwa in dte:
            assert isinstance(dwa, DataWithAxes), f'{type(dwa).__name__} in the DataToExport'
            assert not any(_is_mock_value(d) for d in dwa.data), f'{dwa.name}: data is not numeric'
            assert all(np.all(np.isfinite(d)) for d in dwa.data), f'{dwa.name}: non finite data'
            assert dwa.units is not None and dwa.units != '', f'{dwa.name}: no units'
            ndim = dwa.data[0].ndim if dwa.data[0].ndim <= 2 else 3
            assert str(dwa.dim.name).endswith(str({0: '0', 1: '1', 2: '2'}.get(ndim, 'N'))) or ndim == 3, \
                f'{dwa.name}: dim {dwa.dim.name} for a {dwa.data[0].ndim}D array'
    _step(report, 'grab_data', grab)

    _step(report, 'close', plugin.close)
    return report


def run_module(module_name: str, install_stubs: bool = True) -> list:
    """Import a plugin module (with stubs for missing vendor libraries) and smoke test the plugin classes it defines"""
    finder = _StubFinder()
    if install_stubs:
        sys.meta_path.append(finder)
    reports = []
    try:
        try:
            module = importlib.import_module(module_name)
        except BaseException as e:
            r = Report(module_name)
            r.findings.append(Finding('import', False, _where(e)))
            r.stubbed_modules = finder.stubbed
            return [r]
        short = module_name.split('.')[-1]
        for name, obj in list(vars(module).items()):
            if not isinstance(obj, type) or obj.__module__ != module_name:
                continue
            if not name.lower().startswith('daq_'):
                continue
            if short.startswith('daq_move'):
                report = smoke_actuator(obj)
            elif 'viewer' in short:
                report = smoke_detector(obj)
            else:
                continue
            report.stubbed_modules = sorted(set(finder.stubbed))
            reports.append(report)
        return reports
    finally:
        if finder in sys.meta_path:
            sys.meta_path.remove(finder)

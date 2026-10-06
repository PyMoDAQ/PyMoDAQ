import sys
import textwrap

import pytest

from pymodaq_utils import plugin_checks as pt
from pymodaq_utils import plugin_rules as pt_rules
from pymodaq_utils.plugin_rules import Severity
from pymodaq_utils.plugin_testing import PluginPackageChecks


class TestMockPlugin(PluginPackageChecks):
    """The mock plugin, a hard dependency of PyMoDAQ, must pass all the checks"""
    package_name = 'pymodaq_plugins_mock'


GOOD_MOVE = '''
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, DataActuatorType, comon_parameters_fun, main

class DAQ_Move_Good(DAQ_Move_base):
    """A good actuator"""
    data_actuator_type = DataActuatorType.DataActuator
    _axis_names = ['x', 'y']
    _controller_units = ['mm', 'um']
    _epsilons = [0.1, 0.1]
    is_multiaxes = True
    params = comon_parameters_fun(axis_names=_axis_names)
    def ini_stage(self, controller=None): return '', True
    def get_actuator_value(self): pass
    def stop_motion(self): pass
    def close(self): pass

if __name__ == '__main__':
    main(__file__)
'''

BAD_MOVE = '''
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base

class DAQ_Move_Bad(DAQ_Move_base):
    _axis_names = ['x', 'y']
    _controller_units = {'x': 'notaunit'}
    params = [{'name': 'a', 'type': 'int', 'value': 1}, {'name': 'a', 'type': 'int', 'value': 2}]
    def close(self): pass
'''


@pytest.fixture
def fake_package(tmp_path, monkeypatch):
    root = tmp_path / 'pymodaq_plugins_fake'
    move = root / 'daq_move_plugins'
    move.mkdir(parents=True)
    (root / '__init__.py').write_text('')
    (move / '__init__.py').write_text('')
    (move / 'daq_move_Good.py').write_text(textwrap.dedent(GOOD_MOVE))
    (move / 'daq_move_Bad.py').write_text(textwrap.dedent(BAD_MOVE))
    (move / 'move_Misnamed.py').write_text('')
    (move / 'lextab.py').write_text('')
    (move / 'yacctab.py').write_text('')
    monkeypatch.syspath_prepend(str(tmp_path))
    yield 'pymodaq_plugins_fake'
    for name in [n for n in sys.modules if n.startswith('pymodaq_plugins_fake')]:
        del sys.modules[name]


def test_find_plugin_modules(fake_package):
    modules = pt.find_plugin_modules(fake_package)
    assert sorted(m.class_name for m in modules) == ['DAQ_Move_Bad', 'DAQ_Move_Good']
    assert all(m.kind == 'move' for m in modules)


def test_good_move_passes(fake_package):
    klass = pt.load_plugin_class(pt.PluginModule(fake_package, 'daq_move_Good', 'move'))
    assert pt.check_move_class(klass) == []


def test_bad_move_reports_everything(fake_package):
    klass = pt.load_plugin_class(pt.PluginModule(fake_package, 'daq_move_Bad', 'move'))
    problems = '\n'.join(pt.check_move_class(klass))
    for method in ('ini_stage', 'get_actuator_value', 'stop_motion'):
        assert f'override {method}()' in problems
    assert 'close()' not in problems
    assert 'same type as' in problems
    assert 'Parameter tree' in problems or 'duplicated' in problems
    assert 'is_multiaxes is False' in problems


def test_layout_reports_entrypoint_and_naming(fake_package):
    problems = '\n'.join(pt.check_package_layout(fake_package))
    assert 'move_Misnamed' in problems
    assert 'lextab' not in problems and 'yacctab' not in problems
    assert 'No entry point' in problems
    assert "should define 'config'" in problems


def test_wrong_class_name_fails(fake_package, tmp_path):
    (tmp_path / 'pymodaq_plugins_fake' / 'daq_move_plugins' / 'daq_move_Other.py').write_text(
        textwrap.dedent(GOOD_MOVE))  # defines DAQ_Move_Good, not DAQ_Move_Other
    with pytest.raises(pt.PluginLoadError, match='DAQ_Move_Other'):
        pt.load_plugin_class(pt.PluginModule(fake_package, 'daq_move_Other', 'move'))


def test_package_name_checked():
    assert any('pymodaq_plugins_<name>' in p for p in pt.check_package_layout('json'))


def test_report_mock():
    report = pt.check_plugin_package('pymodaq_plugins_mock')
    assert report.ok, str(report)
    assert 'daq_move_Mock' in report.to_dict()['results']
    assert str(report).startswith('pymodaq_plugins_mock: OK')


def test_report_fake(fake_package):
    report = pt.check_plugin_package(fake_package)
    assert not report.ok
    failed = {res.item for res in report.failures}
    assert failed == {'package layout', 'daq_move_Bad'}
    assert 'daq_move_Good' not in failed
    assert '[FAIL] daq_move_Bad' in str(report) and '[ok] daq_move_Good' in str(report)


@pytest.mark.parametrize('body, environmental', [
    ('import not_a_module_xyz', True),
    ('raise OSError("cannot load library")', True),
    ('from pymodaq.not_a_module import x', False),
    ('x = = 1', False),
])
def test_import_failure_classification(fake_package, tmp_path, body, environmental):
    (tmp_path / 'pymodaq_plugins_fake' / 'daq_move_plugins' / 'daq_move_Broken.py').write_text(body)
    result = pt.check_plugin_module(pt.PluginModule(fake_package, 'daq_move_Broken', 'move'))
    assert bool(result.warnings) is environmental
    assert bool(result.failing()) is not environmental  # a problem, or the finding of a syntax error


def test_deprecated_axis_names_declaration(fake_package, tmp_path):
    code = (textwrap.dedent(GOOD_MOVE)
            .replace('    _axis_names = ', '    axis_names = ')
            .replace('=_axis_names', '=axis_names')
            .replace('Good', 'Old'))
    (tmp_path / 'pymodaq_plugins_fake' / 'daq_move_plugins' / 'daq_move_Old.py').write_text(code)
    result = pt.check_plugin_module(pt.PluginModule(fake_package, 'daq_move_Old', 'move'))
    assert any("'axis_names'" in str(f) for f in result.findings if f.severity == Severity.ERROR)
    assert not result.ok


def test_fail_levels(fake_package):
    report = pt.check_plugin_package('pymodaq_plugins_mock')
    assert report.ok and not pt.check_plugin_package('pymodaq_plugins_mock', fail_on='warning').ok  # _epsilon
    assert not pt.check_plugin_package('pymodaq_plugins_mock', fail_on='todo').ok
    with pytest.raises(ValueError):
        pt.check_plugin_package('pymodaq_plugins_mock', fail_on='nope')


def test_strict_imports(fake_package, tmp_path):
    (tmp_path / 'pymodaq_plugins_fake' / 'daq_move_plugins' / 'daq_move_Env.py').write_text('import not_a_module_xyz')
    result = pt.check_plugin_module(pt.PluginModule(fake_package, 'daq_move_Env', 'move'))
    assert result.failing() == [] and result.failing(strict_imports=True)


def test_cli(capsys, monkeypatch):
    assert pt.main(['pymodaq_plugins_mock']) == 0
    assert pt.main(['pymodaq_plugins_mock', '--fail-on', 'todo', '-v']) == 1
    out = capsys.readouterr().out
    assert 'pymodaq_plugins_mock' in out and 'PMQ201' in out


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A plugin repository not installed, whose pyproject.toml still has the template name"""
    pkg = tmp_path / 'src' / 'pymodaq_plugins_notinstalled'
    (pkg / 'daq_move_plugins').mkdir(parents=True)
    (pkg / '__init__.py').write_text('config = None\n__version__ = "0"')
    (pkg / 'utils.py').write_text('')
    (pkg / 'daq_move_plugins' / '__init__.py').write_text('')
    (pkg / 'daq_move_plugins' / 'daq_move_Good.py').write_text(textwrap.dedent(GOOD_MOVE))
    (tmp_path / 'pyproject.toml').write_text('[project]\nname = "pymodaq_plugins_template"\n'
                                             'dynamic = ["entry-points"]\n')
    monkeypatch.setattr(sys, 'path', list(sys.path))  # resolve_target changes it
    yield tmp_path
    for name in [n for n in sys.modules if n.startswith('pymodaq_plugins_notinstalled')]:
        del sys.modules[name]


def test_resolve_target(repo):
    assert pt.resolve_target(str(repo)) == ('pymodaq_plugins_notinstalled', repo)  # the repository
    assert pt.resolve_target(str(repo / 'src' / 'pymodaq_plugins_notinstalled'))[0] == 'pymodaq_plugins_notinstalled'
    assert pt.resolve_target('pymodaq_plugins_mock') == ('pymodaq_plugins_mock', None)  # a package name
    (repo / 'empty').mkdir()
    with pytest.raises(ValueError):
        pt.resolve_target(str(repo / 'empty'))  # no package in it


def test_check_a_plugin_not_installed(repo, capsys):
    assert pt.main([str(repo)]) == 1  # PMQ103: the pyproject name is not the package one
    out = capsys.readouterr().out
    assert 'PMQ102' in out and 'PMQ103' in out  # the pyproject.toml is checked although its name is wrong
    assert 'the plugin is not installed' in out and 'No entry point' not in out
    assert '[ok] daq_move_Good' in out


def test_unreplaced_template_import_is_a_todo_not_a_failure(fake_package, tmp_path):
    (tmp_path / 'pymodaq_plugins_fake' / 'hardware').mkdir()
    (tmp_path / 'pymodaq_plugins_fake' / 'hardware' / '__init__.py').write_text('')
    code = 'from pymodaq_plugins_fake.hardware.python_wrapper_file_of_your_instrument import X'
    (tmp_path / 'pymodaq_plugins_fake' / 'daq_move_plugins' / 'daq_move_Tpl.py').write_text(code)
    result = pt.check_plugin_module(pt.PluginModule(fake_package, 'daq_move_Tpl', 'move'))
    assert result.problems == [] and result.warnings == []  # not a failure, not even with strict_imports
    assert [f.severity for f in result.findings if f.code == 'PMQ203'] == [Severity.TODO]
    assert result.failing() == [] and result.failing('todo', strict_imports=True)


def test_package_name_from_folder_not_from_unmodified_pyproject(repo):
    assert pt.guess_package_name(repo / 'src') == 'pymodaq_plugins_notinstalled'


def test_mock_has_no_error():
    findings = pt_rules.check_package_sources('pymodaq_plugins_mock')
    assert not [f for f in findings if f.severity == Severity.ERROR]


def test_conflicted_copy_is_not_taken_for_a_plugin_module(fake_package, tmp_path):
    name = 'daq_move_Mono_840G11-WEBER_oct.-05-085858-2026_CaseConflict.py'
    (tmp_path / 'pymodaq_plugins_fake' / 'daq_move_plugins' / name).write_text('x = = 1')
    assert sorted(m.module_name for m in pt.find_plugin_modules(fake_package)) == ['daq_move_Bad', 'daq_move_Good']
    assert 'PMQ112' in {f.code for f in pt.check_package_sources(fake_package).findings}


def test_report_color(capsys):
    report = pt.check_plugin_package('pymodaq_plugins_mock')
    assert '\033' not in str(report) and '\033' not in report.format()
    colored = report.format(color=True)
    assert '\033[32m[ok]\033[0m' in colored and '\033[33m[warn]\033[0m' in colored
    assert pt.main(['pymodaq_plugins_mock', '--color', 'always']) == 0
    assert '\033[' in capsys.readouterr().out
    assert pt.main(['pymodaq_plugins_mock', '--color', 'never']) == 0
    assert '\033[' not in capsys.readouterr().out


def test_check_a_single_file(repo, capsys):
    folder = repo / 'src' / 'pymodaq_plugins_notinstalled' / 'daq_move_plugins'
    assert pt.main([str(folder / 'daq_move_Good.py')]) == 0
    out = capsys.readouterr().out
    assert '[ok] daq_move_Good' in out and 'package layout' not in out  # only this module is checked

    (folder / 'daq_move_Todo.py').write_text(textwrap.dedent(GOOD_MOVE).replace('Good', 'Todo')
                                             + '\n# TODO complete me\n')
    assert pt.main([str(folder / 'daq_move_Todo.py'), '--fail-on', 'todo']) == 1
    out = capsys.readouterr().out
    assert 'PMQ201' in out and 'daq_move_Good' not in out

    with pytest.raises(SystemExit):  # not an instrument module
        pt.main([str(repo / 'src' / 'pymodaq_plugins_notinstalled' / 'utils.py')])


def test_syntax_error_is_located_and_reported_once(fake_package, tmp_path):
    code = 'class DAQ_Move_Syn:\n    _axis_names = [\'a\'\n    def close(self): pass\n'
    (tmp_path / 'pymodaq_plugins_fake' / 'daq_move_plugins' / 'daq_move_Syn.py').write_text(code)
    (tmp_path / 'pymodaq_plugins_fake' / 'broken_helper.py').write_text('x = = 1')  # not a plugin module
    report = pt.check_plugin_package(fake_package)
    errors = [(res.item, f) for res in report.results for f in res.findings if f.code in ('PMQ200', 'PMQ300')]
    assert sorted((item, f.code) for item, f in errors) == [('daq_move_Syn', 'PMQ300'), ('package sources', 'PMQ200')]
    finding = next(f for item, f in errors if f.code == 'PMQ300')
    assert finding.line == 2 and finding.column and "_axis_names = ['a'" in finding.hint
    assert f'daq_move_Syn.py:2:{finding.column}' in str(report)
    syn = next(res for res in report.results if res.item == 'daq_move_Syn')
    assert len(syn.problems) == 0  # the import error is not repeated, the finding says it all
    assert not report.ok

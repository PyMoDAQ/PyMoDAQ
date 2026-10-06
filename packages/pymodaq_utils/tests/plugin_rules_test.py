import shutil
import textwrap

import pytest

from pymodaq_utils import plugin_rules as pr
from pymodaq_utils.plugin_rules import Severity

PYPROJECT = '''
[features]
instruments = {instruments}
extensions = {extensions}

[urls]
package-url = 'https://github.com/PyMoDAQ/pymodaq_plugins_template' #todo modify url

[project]
name = "{name}" #todo modify template by your plugin short name
description = 'some word about your plugin'
dependencies = ["numpy"]
authors = [{{name = "Name Surname", email = "myname@test.fr"}}]
dynamic = ["version", "urls"]
'''


def codes(findings, severity=None):
    return {f.code for f in findings if severity is None or f.severity == severity}


@pytest.fixture
def project(tmp_path):
    def make(name='pymodaq_plugins_template', instruments='true', extensions='false', ext_code=False):
        (tmp_path / 'pyproject.toml').write_text(PYPROJECT.format(name=name, instruments=instruments,
                                                                  extensions=extensions))
        pkg = tmp_path / 'src' / 'pymodaq_plugins_foo'
        (pkg / 'daq_move_plugins').mkdir(parents=True, exist_ok=True)
        (pkg / 'daq_move_plugins' / 'daq_move_Foo.py').write_text('x = 1')
        if ext_code:
            (pkg / 'extensions').mkdir(exist_ok=True)
            (pkg / 'extensions' / 'my_ext.py').write_text('x = 1')
        return tmp_path
    return make


def test_pyproject_template_placeholders(project):
    findings = pr.check_pyproject('pymodaq_plugins_foo', project())
    assert {'PMQ102', 'PMQ103', 'PMQ104', 'PMQ105', 'PMQ106'} <= codes(findings)
    assert 'PMQ107' in codes(findings, Severity.WARNING)  # no pymodaq dependency
    assert 'PMQ108' in codes(findings, Severity.ERROR)  # no entry points
    assert all(f.line for f in findings if f.code in ('PMQ102', 'PMQ104', 'PMQ105'))


def test_pyproject_features_only_warn(project):
    root = project(name='pymodaq_plugins_foo', ext_code=True)
    findings = pr.check_pyproject('pymodaq_plugins_foo', root)
    assert 'PMQ109' in codes(findings, Severity.WARNING)  # code in extensions/ but feature is false
    assert 'PMQ109' not in codes(findings, Severity.ERROR)
    shutil.rmtree(root / 'src' / 'pymodaq_plugins_foo' / 'extensions')
    findings = pr.check_pyproject('pymodaq_plugins_foo', project(name='pymodaq_plugins_foo', extensions='true'))
    assert 'PMQ110' in codes(findings, Severity.WARNING)  # feature true but no code


def test_pyproject_wrong_name(project):
    findings = pr.check_pyproject('pymodaq_plugins_foo', project(name='my_plugin'))
    assert {'PMQ101', 'PMQ103'} <= codes(findings, Severity.ERROR)


def test_leftovers(tmp_path):
    pkg = tmp_path / 'pymodaq_plugins_foo'
    (pkg / 'resources').mkdir(parents=True)
    (pkg / 'resources' / 'config_template.toml').write_text("title = 'configuration of the plugin XXX'")
    (pkg / 'daq_move_Template.py').write_text(textwrap.dedent('''
        from x.python_wrapper_file_of_your_instrument import PythonWrapperObjectOfYourInstrument
        # TODO: complete me
        class A:
            def f(self):
                raise NotImplementedError  # remove this
        '''))
    (pkg / 'lextab.py').write_text('# todo generated')
    findings = pr.check_leftovers('pymodaq_plugins_foo', pkg)
    assert codes(findings) == {'PMQ201', 'PMQ202', 'PMQ203', 'PMQ204', 'PMQ205'}
    assert all(f.severity == Severity.TODO for f in findings)
    assert not [f for f in findings if f.path and f.path.stem == 'lextab']


def test_source_rules_without_import(tmp_path):
    path = tmp_path / 'daq_move_Foo.py'
    path.write_text(textwrap.dedent('''
        from pymodaq.daq_utils.daq_utils import ThreadCommand
        from not_installed_sdk import Thing

        class DAQ_Move_Foo(DAQ_Move_base):
            _epsilon = 0.1
            _axis_names = ['a', 'b']
            _controller_units = {'a': 'furlongs-per-fortnight-squared'}
            def close(self): pass
            def ini_stage(self, controller=None):
                return True
        '''))
    findings = pr.check_plugin_source(path, 'move', 'DAQ_Move_Foo', static_fallback=True)
    assert {'PMQ302', 'PMQ303', 'PMQ304', 'PMQ306', 'PMQ307', 'PMQ308', 'PMQ309', 'PMQ310'} <= codes(findings)
    # without fallback only the rules that are not already covered by the checks on the imported class
    findings = pr.check_plugin_source(path, 'move', 'DAQ_Move_Foo')
    assert not codes(findings) & {'PMQ304', 'PMQ305', 'PMQ306'}


def test_source_syntax_error(tmp_path):
    path = tmp_path / 'daq_move_Foo.py'
    path.write_text('x = = 1')
    assert codes(pr.check_plugin_source(path, 'move', 'DAQ_Move_Foo')) == {'PMQ300'}


def test_conflicted_copy_files_are_reported_and_otherwise_ignored(tmp_path):
    pkg = tmp_path / 'pymodaq_plugins_foo'
    pkg.mkdir()
    bad = pkg / 'daq_move_Mono_840G11-WEBER_oct.-05-085858-2026_CaseConflict.py'
    bad.write_text('# TODO this copy should not be scanned\nraise NotImplementedError')
    (pkg / 'daq_move_Mono.py').write_text('x = 1')
    assert [f.code for f in pr.check_file_names(pkg)] == ['PMQ112']
    assert pr.check_file_names(pkg)[0].severity == Severity.WARNING
    assert pr.check_leftovers('pymodaq_plugins_foo', pkg) == []  # no TODO / NotImplementedError from the copy

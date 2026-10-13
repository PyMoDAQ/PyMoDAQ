import shutil
import textwrap

import pytest

from pymodaq_utils.plugin_tools import rules as pr
from pymodaq_utils.plugin_tools.rules import Severity

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


class FakeStream:
    def __init__(self, tty):
        self.tty = tty

    def isatty(self):
        return self.tty


def test_colorize_and_use_color(monkeypatch):
    assert pr.colorize('x', 'red', False) == 'x'
    assert pr.colorize('x', 'red') == '\033[31mx\033[0m'
    monkeypatch.delenv('NO_COLOR', raising=False)
    monkeypatch.delenv('FORCE_COLOR', raising=False)
    assert pr.use_color('auto', FakeStream(True)) and not pr.use_color('auto', FakeStream(False))
    assert pr.use_color('always', FakeStream(False)) and not pr.use_color('never', FakeStream(True))
    monkeypatch.setenv('NO_COLOR', '1')
    assert not pr.use_color('auto', FakeStream(True)) and pr.use_color('always', FakeStream(False))
    monkeypatch.delenv('NO_COLOR')
    monkeypatch.setenv('FORCE_COLOR', '1')
    assert pr.use_color('auto', FakeStream(False))


def test_finding_format_color():
    finding = pr.Finding('PMQ999', Severity.ERROR, 'message', 'a hint')
    assert str(finding) == finding.format() == 'PMQ999 [error]: message  -> a hint'
    assert '\033[31m[error]\033[0m' in finding.format(color=True)
    assert '\033' not in finding.format()


def test_deprecated_api_of_actuators(tmp_path):
    path = tmp_path / 'daq_move_Foo.py'
    path.write_text(textwrap.dedent('''
        from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters, comon_parameters_fun

        class DAQ_Move_Foo(DAQ_Move_base):
            """doc"""
            params = [{'name': 'a', 'type': 'int'}] + comon_parameters
            def check_position(self):
                return self.current_position
            def move_Abs(self, value):
                self.target_position = value
            def move_Rel(self, value):
                self.target_position = value
            def close(self): pass
            def ini_stage(self, controller=None):
                return '', True
        '''))
    findings = pr.check_plugin_source(path, 'move', 'DAQ_Move_Foo', static_fallback=True)
    assert {'PMQ312', 'PMQ313', 'PMQ314'} <= codes(findings)
    assert codes(findings, Severity.ERROR) >= {'PMQ314'}
    assert len([f for f in findings if f.code == 'PMQ312']) == 3  # check_position, move_Abs and move_Rel
    # the old names are still accepted in place of the mandatory methods
    assert 'PMQ306' not in codes(findings)


def test_move_abs_and_move_rel_are_mandatory(tmp_path):
    path = tmp_path / 'daq_move_Foo.py'
    path.write_text(textwrap.dedent('''
        from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters

        class DAQ_Move_Foo(DAQ_Move_base):
            """doc"""
            params = comon_parameters
            def ini_stage(self, controller=None): return '', True
            def get_actuator_value(self): pass
            def close(self): pass
        '''))
    findings = pr.check_plugin_source(path, 'move', 'DAQ_Move_Foo', static_fallback=True)
    messages = [f.message for f in findings if f.code == 'PMQ306']
    assert any('move_abs' in m for m in messages) and any('move_rel' in m for m in messages)


def test_comon_parameters_called_or_of_a_viewer_is_fine(tmp_path):
    path = tmp_path / 'daq_move_Foo.py'
    path.write_text(textwrap.dedent('''
        from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters

        class DAQ_Move_Foo(DAQ_Move_base):
            """doc"""
            params = comon_parameters(epsilon=0.1)
        '''))
    assert 'PMQ314' not in codes(pr.check_plugin_source(path, 'move', 'DAQ_Move_Foo'))
    path = tmp_path / 'daq_0Dviewer_Foo.py'
    path.write_text(textwrap.dedent('''
        from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters

        class DAQ_0DViewer_Foo(DAQ_Viewer_base):
            """doc"""
            params = [{'name': 'a', 'type': 'int'}] + comon_parameters
        '''))
    assert 'PMQ314' not in codes(pr.check_plugin_source(path, '0D', 'DAQ_0DViewer_Foo'))


def test_legacy_settings_names(tmp_path):
    path = tmp_path / 'daq_move_Foo.py'
    path.write_text(textwrap.dedent('''
        class DAQ_Move_Foo(DAQ_Move_base):
            """doc"""
            def ini_stage(self, controller=None):
                if self.settings.child('multiaxes', 'multi_status').value() == 'Master':
                    pass
                return '', True
        '''))
    findings = [f for f in pr.check_plugin_source(path, 'move', 'DAQ_Move_Foo') if f.code == 'PMQ316']
    assert len(findings) == 1 and findings[0].line == 5
    assert '2 times' in findings[0].message


def test_legacy_names_in_subscripts_are_still_flagged_as_deprecated(tmp_path):
    path = tmp_path / 'daq_move_Foo.py'
    path.write_text(textwrap.dedent('''
        class DAQ_Move_Foo(DAQ_Move_base):
            """doc"""
            def ini_stage(self, controller=None):
                a = self.settings['multiaxes', 'axis']
                return '', True
        '''))
    assert 'PMQ316' in codes(pr.check_plugin_source(path, 'move', 'DAQ_Move_Foo'))


def test_data_actuator_type_inherited_from_a_plugin_class(tmp_path):
    path = tmp_path / 'daq_move_Foo.py'
    path.write_text(textwrap.dedent('''
        from other import DAQ_Move_Bar

        class DAQ_Move_Foo(DAQ_Move_Bar):
            """doc"""
        '''))
    assert 'PMQ303' not in codes(pr.check_plugin_source(path, 'move', 'DAQ_Move_Foo'))


def test_noqa_comment_silences_the_given_codes_on_that_line(tmp_path):
    source = '''
        class DAQ_Move_Foo(DAQ_Move_base):
            """doc"""
            def ini_stage(self, controller=None):
                if self.settings.child('multiaxes', 'a').value():  # noqa: {code}
                    pass
                return '', True
        '''
    path = tmp_path / 'daq_move_Foo.py'
    path.write_text(textwrap.dedent(source.format(code='PMQ303, PMQ316')))
    assert 'PMQ316' not in codes(pr.check_plugin_source(path, 'move', 'DAQ_Move_Foo'))
    path.write_text(textwrap.dedent(source.format(code='PMQ303')))
    assert 'PMQ316' in codes(pr.check_plugin_source(path, 'move', 'DAQ_Move_Foo'))


def test_deprecated_controller_init(tmp_path):
    path = tmp_path / 'daq_move_Foo.py'
    path.write_text(textwrap.dedent('''
        class DAQ_Move_Foo(DAQ_Move_base):
            """doc"""
            def ini_stage(self, controller=None):
                self.ini_stage_init(controller, Camera())  # noqa: PMQ999
                return '', True
        '''))
    findings = [f for f in pr.check_plugin_source(path, 'move', 'DAQ_Move_Foo') if f.code == 'PMQ318']
    assert len(findings) == 1 and findings[0].line == 5
    path.write_text(path.read_text().replace('PMQ999', 'PMQ318'))
    assert 'PMQ318' not in codes(pr.check_plugin_source(path, 'move', 'DAQ_Move_Foo'))


def test_python_code_rules(tmp_path):
    root = tmp_path / 'pymodaq_plugins_foo'
    (root / 'hardware').mkdir(parents=True)
    (root / 'hardware' / 'sdk.py').write_text(textwrap.dedent(r'''
        from ctypes import windll
        PATH = "C:\Program Files\Vendor"
        '''))
    (root / 'hardware' / 'guarded.py').write_text(textwrap.dedent('''
        import sys
        try:
            from ctypes import windll
        except ImportError:
            windll = None
        if sys.platform == 'win32':
            import winreg
            DLL = 'C:/Windows/System32/x.dll'
        '''))
    findings = pr.check_python_code(root)
    by_file = {(f.path.name, f.code) for f in findings}
    assert ('sdk.py', 'PMQ315') in by_file and ('sdk.py', 'PMQ317') in by_file
    assert not [f for f in findings if f.path.name == 'guarded.py']
    windows = next(f for f in findings if f.code == 'PMQ317')
    assert 'windll' in windows.message and '1 more' in windows.message


def test_syntax_warning_names_the_file(tmp_path):
    """An invalid escape sequence is warned about by python while the source is parsed: with the file name"""
    import warnings
    path = tmp_path / 'daq_move_Foo.py'
    path.write_text('PATTERN = "\\."\n\n\nclass DAQ_Move_Foo:\n    """doc"""\n')
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        pr.check_plugin_source(path, 'move', 'DAQ_Move_Foo')
    escapes = [w for w in caught if 'invalid escape sequence' in str(w.message)]
    assert escapes and all(w.filename == str(path) and w.lineno == 1 for w in escapes)


def test_noqa_on_leftovers_and_without_colon(tmp_path):
    root = tmp_path / 'pymodaq_plugins_foo'
    root.mkdir()
    (root / 'daq_move_Foo.py').write_text(textwrap.dedent('''
        class DAQ_Move_Foo:
            def get_actuator_value(self):
                raise NotImplementedError  # noqa PMQ202
            def other(self):
                raise NotImplementedError
        '''))
    findings = [f for f in pr.check_leftovers('pymodaq_plugins_foo', root) if f.code == 'PMQ202']
    assert [f.line for f in findings] == [6]


def test_finding_location_is_relative_to_the_package(tmp_path):
    inside = tmp_path / 'pymodaq_plugins_xxx' / 'hardware' / 'driver.py'
    finding = pr.Finding('PMQ317', Severity.WARNING, 'message', path=inside, line=5)
    assert finding.location == 'hardware/driver.py:5'
    assert pr.Finding('PMQ317', Severity.WARNING, 'message', path=tmp_path / 'other.py').location == 'other.py'


def test_windows_only_code_is_not_reported_for_a_windows_only_package(tmp_path):
    package = tmp_path / 'pymodaq_plugins_foo'
    (package / 'hardware').mkdir(parents=True)
    (package / 'daq_move_plugins').mkdir()
    (package / 'hardware' / 'sdk.py').write_text('PATH = "C:\\\\Program Files\\\\Vendor"\n')
    plugin = package / 'daq_move_plugins' / 'daq_move_Foo.py'
    plugin.write_text("class DAQ_Move_Foo:\n    supported_platforms = ('win32',)\n")
    assert not [f for f in pr.check_python_code(package) if f.code == 'PMQ317']
    plugin.write_text("class DAQ_Move_Foo:\n    supported_platforms = ('win32', 'linux')\n")
    assert [f for f in pr.check_python_code(package) if f.code == 'PMQ317']
    plugin.write_text("class DAQ_Move_Foo:\n    pass\n")
    assert [f for f in pr.check_python_code(package) if f.code == 'PMQ317']


def test_windows_only_code_is_fine_in_the_modules_used_by_windows_only_instruments_only(tmp_path):
    package = tmp_path / 'pymodaq_plugins_foo'
    (package / 'hardware').mkdir(parents=True)
    (package / 'daq_move_plugins').mkdir()
    for name in ('kinesis', 'shared', 'other'):
        (package / 'hardware' / f'{name}.py').write_text('PATH = "C:\\\\\\\\Program Files\\\\\\\\Vendor"\n')
    (package / 'daq_move_plugins' / 'daq_move_Win.py').write_text(
        "from pymodaq_plugins_foo.hardware.kinesis import PATH\nfrom ..hardware import shared\n"
        "class DAQ_Move_Win:\n    supported_platforms = ('win32',)\n")
    (package / 'daq_move_plugins' / 'daq_move_Any.py').write_text(
        "from pymodaq_plugins_foo.hardware.other import PATH\nfrom pymodaq_plugins_foo.hardware import shared\n"
        "class DAQ_Move_Any:\n    pass\n")
    reported = {f.path.name for f in pr.check_python_code(package) if f.code == 'PMQ317'}
    assert reported == {'shared.py', 'other.py'}

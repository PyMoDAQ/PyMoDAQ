import textwrap

import pytest

from pymodaq_utils.plugin_tools import platforms, rules, checks


def test_unsupported_reason():
    assert platforms.unsupported_reason(None, None) == ''
    assert platforms.unsupported_reason(('win32',), system='win32', machine='AMD64') == ''
    assert platforms.unsupported_reason(('linux',), system='linux2', machine='x86_64') == ''  # prefix
    reason = platforms.unsupported_reason(('win32',), system='linux', machine='x86_64')
    assert 'only works on Windows' in reason and 'linux' in reason
    assert platforms.unsupported_reason(('linux',), ('aarch64', 'armv7l'), 'linux', 'arm64') == ''  # alias
    reason = platforms.unsupported_reason(('linux',), ('aarch64', 'armv7l'), 'linux', 'x86_64')
    assert 'Linux (aarch64, armv7l)' in reason


def test_classifiers_for():
    assert platforms.classifiers_for(None) == [platforms.OS_INDEPENDENT]
    assert platforms.classifiers_for(('win32',)) == ['Operating System :: Microsoft :: Windows']
    assert platforms.classifiers_for({'linux', 'win32'}) == ['Operating System :: Microsoft :: Windows',
                                                             'Operating System :: POSIX :: Linux']


def test_invalid_values():
    assert platforms.invalid_values(('win32',), ('aarch64', 'arm64', 'AMD64')) == []
    assert len(platforms.invalid_values(('windows',), None)) == 1
    assert len(platforms.invalid_values(None, ('riscv',))) == 1
    assert len(platforms.invalid_values((), None)) == 1


PLUGIN = '''
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters

class DAQ_Move_Foo(DAQ_Move_base):
    """doc"""
    supported_platforms = {platforms}
    supported_architectures = {archs}
    params = comon_parameters
    def ini_stage(self, controller=None): return '', True
    def get_actuator_value(self): pass
    def move_abs(self, value): pass
    def move_rel(self, value): pass
    def close(self): pass
'''


def make_package(tmp_path, platforms_value, archs_value='None', classifiers=('Operating System :: OS Independent',)):
    package = tmp_path / 'src' / 'pymodaq_plugins_foo'
    (package / 'daq_move_plugins').mkdir(parents=True, exist_ok=True)
    (package / '__init__.py').touch()
    (package / 'daq_move_plugins' / '__init__.py').touch()
    (package / 'daq_move_plugins' / 'daq_move_Foo.py').write_text(
        PLUGIN.format(platforms=platforms_value, archs=archs_value))
    lines = ''.join(f'    "{c}",\n' for c in classifiers)
    (tmp_path / 'pyproject.toml').write_text(
        '[project]\nname = "pymodaq_plugins_foo"\nclassifiers = [\n    "Development Status :: 5",\n'
        f'{lines}    "Programming Language :: Python :: 3",\n]\n')
    return package


def test_package_platforms(tmp_path):
    package = make_package(tmp_path, "('win32',)")
    assert platforms.package_platforms(package) == {'win32'}
    package = make_package(tmp_path, 'None')
    assert platforms.package_platforms(package) is None


def test_invalid_declaration_is_reported(tmp_path):
    package = make_package(tmp_path, "('windows',)")
    findings = rules.check_plugin_source(package / 'daq_move_plugins' / 'daq_move_Foo.py', 'move', 'DAQ_Move_Foo',
                                         static_fallback=True)
    assert 'PMQ319' in {f.code for f in findings}


def test_classifiers_mismatch_and_fix(tmp_path):
    package = make_package(tmp_path, "('win32',)")
    findings = rules.check_os_classifiers(package, tmp_path)
    assert [f.code for f in findings] == ['PMQ320']
    assert platforms.update_pyproject_classifiers(tmp_path / 'pyproject.toml', platforms.package_platforms(package))
    text = (tmp_path / 'pyproject.toml').read_text()
    assert 'OS Independent' not in text and 'Operating System :: Microsoft :: Windows' in text
    assert '"Development Status :: 5",' in text and '"Programming Language :: Python :: 3",' in text
    assert rules.check_os_classifiers(package, tmp_path) == []
    assert not platforms.update_pyproject_classifiers(tmp_path / 'pyproject.toml', {'win32'})  # nothing to change


def test_classifier_added_when_missing(tmp_path):
    package = make_package(tmp_path, "('linux',)", classifiers=())
    platforms.update_pyproject_classifiers(tmp_path / 'pyproject.toml', platforms.package_platforms(package))
    assert 'Operating System :: POSIX :: Linux' in (tmp_path / 'pyproject.toml').read_text()
    import toml
    assert 'Operating System :: POSIX :: Linux' in toml.load(tmp_path / 'pyproject.toml')['project']['classifiers']


def test_cli_fix_classifiers(tmp_path, capsys):
    make_package(tmp_path, "('win32',)")
    checks.main([str(tmp_path), '--fix-classifiers', '--color', 'never'])
    out = capsys.readouterr().out
    assert 'classifiers updated' in out and 'Works on: Windows' in out


def test_docs_table_is_up_to_date():
    from pathlib import Path
    table = Path(platforms.__file__).parents[5] / 'docs' / 'src' / 'developer_folder' / 'plugin_platforms_table.inc'
    if not table.is_file():
        pytest.skip('docs not available (installed package)')
    assert table.read_text() == platforms.platforms_as_rst() + '\n', \
        'regenerate with: python -c "from pymodaq_utils.plugin_tools.platforms import platforms_as_rst; ' \
        f'open(\'{table}\', \'w\').write(platforms_as_rst() + chr(10))"'


DYNAMIC_PYPROJECT = '''[project]
name = "pymodaq_plugins_foo"
dynamic = ["version", "urls", "entry-points", "classifiers"]

[urls]
package-url = "https://example.org/foo"

[tool.pymodaq]
classifiers = [
    "Development Status :: 5",
    "Operating System :: OS Independent",
]
'''


def test_dynamic_classifiers_are_computed_when_building(tmp_path):
    from pymodaq_utils.resources.hatch_build_plugins import update_metadata_from_toml
    make_package(tmp_path, "('linux',)", "('aarch64',)")
    (tmp_path / 'pyproject.toml').write_text(DYNAMIC_PYPROJECT)
    metadata = {'name': 'pymodaq_plugins_foo'}
    update_metadata_from_toml(metadata, tmp_path)
    assert metadata['classifiers'] == ['Development Status :: 5', 'Operating System :: POSIX :: Linux']
    make_package(tmp_path, 'None')
    (tmp_path / 'pyproject.toml').write_text(DYNAMIC_PYPROJECT)
    update_metadata_from_toml(metadata, tmp_path)
    assert metadata['classifiers'] == ['Development Status :: 5', platforms.OS_INDEPENDENT]


def test_static_classifiers_are_left_alone_by_the_hook(tmp_path):
    from pymodaq_utils.resources.hatch_build_plugins import update_metadata_from_toml
    make_package(tmp_path, "('linux',)")
    (tmp_path / 'pyproject.toml').write_text(DYNAMIC_PYPROJECT.replace(', "classifiers"', ''))
    metadata = {'name': 'pymodaq_plugins_foo'}
    update_metadata_from_toml(metadata, tmp_path)
    assert 'classifiers' not in metadata


def test_cli_fix_classifiers_with_dynamic_classifiers(tmp_path, capsys):
    make_package(tmp_path, "('win32',)")
    (tmp_path / 'pyproject.toml').write_text(DYNAMIC_PYPROJECT)
    checks.main([str(tmp_path), '--fix-classifiers', '--color', 'never'])
    assert 'computed when the package is built' in capsys.readouterr().out
    assert (tmp_path / 'pyproject.toml').read_text() == DYNAMIC_PYPROJECT

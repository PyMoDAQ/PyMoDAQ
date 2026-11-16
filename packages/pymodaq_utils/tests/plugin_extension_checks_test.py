import pytest

from pymodaq_utils.plugin_tools import extension_checks as ec

GOOD = '''
from pymodaq.utils.custom_ext import CustomExt

EXTENSION_NAME = 'My extension'
CLASS_NAME = 'MyExtension'


class MyExtension(CustomExt):
    def __init__(self, parent, dashboard):
        super().__init__(parent, dashboard)
        self.setup_ui()

    def _quit_fun(self):
        return True
'''
NO_NAMES = GOOD.replace("EXTENSION_NAME = 'My extension'\n", '').replace("CLASS_NAME = 'MyExtension'\n", '')


def write(folder, name, code):
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code)
    return path


def test_is_core_extension(tmp_path):
    assert ec.is_core_extension(tmp_path / 'src' / 'pymodaq' / 'extensions' / 'scan' / 'scan.py')
    assert not ec.is_core_extension(tmp_path / 'pymodaq_plugins_foo' / 'extensions' / 'ext.py')


def test_one_file(tmp_path):
    report = ec.check_extension_files([write(tmp_path, 'ext.py', GOOD)])
    assert report.ok and len(report.results) == 1 and not report.results[0].findings


def test_missing_names_fail_for_a_plugin_but_not_for_the_core(tmp_path):
    plugin = write(tmp_path / 'pymodaq_plugins_foo', 'extensions/ext.py', NO_NAMES)
    core = write(tmp_path / 'pymodaq', 'extensions/ext.py', NO_NAMES)
    assert not ec.check_extension_files([plugin]).ok
    assert ec.check_extension_files([core]).ok
    assert ec.check_extension_files([plugin], core=True).ok
    assert not ec.check_extension_files([core], core=False).ok


def test_folder_takes_the_extensions_folder_and_leaves_private_modules(tmp_path):
    write(tmp_path, 'src/pymodaq_plugins_foo/extensions/good.py', GOOD)
    write(tmp_path, 'src/pymodaq_plugins_foo/extensions/_private.py', NO_NAMES)
    write(tmp_path, 'src/pymodaq_plugins_foo/extensions/__init__.py', '')
    write(tmp_path, 'src/pymodaq_plugins_foo/daq_move_plugins/daq_move_Foo.py', 'x = 1')
    files = ec.find_extension_files(tmp_path)
    assert [f.name for f in files] == ['good.py']
    assert [f.name for f in ec.find_extension_files(tmp_path / 'src' / 'pymodaq_plugins_foo')] == ['good.py']


def test_fail_on(tmp_path):
    code = GOOD.replace('self.setup_ui()', 'pass')
    path = write(tmp_path, 'ext.py', code)
    assert ec.check_extension_files([path]).ok
    assert not ec.check_extension_files([path], fail_on='warning').ok
    with pytest.raises(ValueError):
        ec.check_extension_files([path], fail_on='nothing')


def test_main(tmp_path, capsys):
    good = write(tmp_path, 'good.py', GOOD)
    bad = write(tmp_path, 'bad.py', NO_NAMES)
    assert ec.main([str(good), '--color', 'never']) == 0
    assert ec.main([str(bad), '--color', 'never']) == 1
    assert 'PMQ330' in capsys.readouterr().out
    with pytest.raises(SystemExit):
        ec.main([str(tmp_path / 'missing.py')])

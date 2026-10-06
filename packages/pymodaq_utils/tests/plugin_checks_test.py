import sys

import pytest

from pymodaq_utils import plugin_checks as pc


@pytest.fixture
def package(tmp_path, monkeypatch):
    root = tmp_path / 'src' / 'pymodaq_plugins_files'
    for folder in (root / 'daq_move_plugins', root / 'daq_viewer_plugins' / 'plugins_1D',
                   root / 'daq_viewer_plugins' / 'plugins_ND'):
        folder.mkdir(parents=True)
    for init in (root, root / 'daq_move_plugins', root / 'daq_viewer_plugins',
                 root / 'daq_viewer_plugins' / 'plugins_1D', root / 'daq_viewer_plugins' / 'plugins_ND'):
        (init / '__init__.py').write_text('')
    monkeypatch.setattr(sys, 'path', list(sys.path))  # resolve_file changes it
    return root


@pytest.mark.parametrize('relative, kind, name', [
    ('daq_move_plugins/daq_move_Foo.py', 'move', 'daq_move_Foo'),
    ('daq_viewer_plugins/plugins_1D/daq_1Dviewer_Foo_2.py', '1D', 'daq_1Dviewer_Foo_2'),
    ('daq_viewer_plugins/plugins_ND/daq_NDviewer_Foo.py', 'ND', 'daq_NDviewer_Foo')])
def test_resolve_file(package, relative, kind, name):
    file = package / relative
    file.write_text('')
    module = pc.resolve_file(file)
    assert (module.package, module.kind, module.module_name) == ('pymodaq_plugins_files', kind, name)
    assert str(package.parent) in sys.path


@pytest.mark.parametrize('relative', [
    'daq_move_plugins/foo.py',  # not named daq_move_*
    'daq_move_plugins/daq_move_Foo-conflict.py',  # not a valid module name
    'daq_viewer_plugins/plugins_1D/daq_2Dviewer_Foo.py',  # the dimension does not match the folder
    'utils.py',  # not an instrument module
    'daq_move_plugins/daq_move_Foo.txt'])
def test_resolve_file_invalid(package, relative):
    file = package / relative
    file.write_text('')
    with pytest.raises(ValueError):
        pc.resolve_file(file)


def test_resolve_file_outside_a_plugin(tmp_path):
    (tmp_path / 'daq_move_Foo.py').write_text('')
    with pytest.raises(ValueError, match='pymodaq_plugins_'):
        pc.resolve_file(tmp_path / 'daq_move_Foo.py')

import sys

import pytest

from pymodaq_utils import plugin_scaffold as sc


@pytest.fixture
def package(tmp_path, monkeypatch):
    root = tmp_path / 'src' / 'pymodaq_plugins_scaf'
    root.mkdir(parents=True)
    (root / '__init__.py').write_text('')
    monkeypatch.syspath_prepend(str(tmp_path / 'src'))
    yield root
    for name in [n for n in sys.modules if n.startswith('pymodaq_plugins_scaf')]:
        del sys.modules[name]


def test_package_is_found_from_a_subfolder(package, monkeypatch):
    monkeypatch.chdir(package.parent.parent)  # project root, the package is in src/
    assert sc.find_package_folder() == package


def test_invalid_arguments(package):
    with pytest.raises(ValueError):
        sc.create_instrument('move', 'foo', package)  # no capital letter
    with pytest.raises(ValueError):
        sc.create_instrument('3D', 'Foo', package)
    with pytest.raises(ValueError):
        sc.create_instrument('move', 'Foo', package.parent)  # not a pymodaq_plugins_ folder
    sc.create_instrument('move', 'Foo', package)
    with pytest.raises(FileExistsError):
        sc.create_instrument('move', 'Foo', package)


def test_cli(package, capsys):
    sc.main(['1D', 'Bar', '--folder', str(package)])
    assert (package / 'daq_viewer_plugins' / 'plugins_1D' / 'daq_1Dviewer_Bar.py').is_file()
    assert 'Created' in capsys.readouterr().out

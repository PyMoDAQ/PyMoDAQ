import sys

import pytest

from pymodaq.utils import plugin_scaffold as sc
from pymodaq.utils import plugin_testing as pt
from pymodaq.utils.plugin_rules import Severity


@pytest.fixture
def package(tmp_path, monkeypatch):
    root = tmp_path / 'src' / 'pymodaq_plugins_scaf'
    root.mkdir(parents=True)
    (root / '__init__.py').write_text('')
    monkeypatch.syspath_prepend(str(tmp_path / 'src'))
    yield root
    for name in [n for n in sys.modules if n.startswith('pymodaq_plugins_scaf')]:
        del sys.modules[name]


@pytest.mark.parametrize('kind, module', [('move', 'daq_move_Foo_1'), ('0D', 'daq_0Dviewer_Foo_1'),
                                          ('1D', 'daq_1Dviewer_Foo_1'), ('2D', 'daq_2Dviewer_Foo_1'),
                                          ('ND', 'daq_NDviewer_Foo_1')])
def test_created_instrument_is_valid_but_unfinished(package, kind, module):
    target = sc.create_instrument(kind, 'Foo_1', package)
    assert target.stem == module
    plugin_module = pt.find_plugin_modules('pymodaq_plugins_scaf')[0]
    assert plugin_module.module_name == module

    result = pt.check_plugin_module(plugin_module)
    assert result.problems == [] and result.warnings == [] and result.findings == []

    sources = pt.check_package_sources('pymodaq_plugins_scaf')  # TODO, NotImplementedError: unfinished, not wrong
    assert {f.severity for f in sources.findings} == {Severity.TODO}
    assert {f.code for f in sources.findings} >= {'PMQ201', 'PMQ202'}
    assert sources.failing() == [] and sources.failing(strict=True)


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

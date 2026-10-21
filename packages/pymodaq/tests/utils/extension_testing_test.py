import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

from pymodaq.utils.plugin_testing import loaded_extension, find_extension_classes, PluginExtensionChecks

EXTENSION = '''
from qtpy import QtWidgets
from pymodaq.utils.custom_ext import CustomExt

EXTENSION_NAME = 'FAKE_EXT'
CLASS_NAME = 'FakeExt'


class FakeExt(CustomExt):
    params = [{'title': 'A flag', 'name': 'flag', 'type': 'bool', 'value': False}]

    def __init__(self, parent, dashboard):
        super().__init__(parent, dashboard)
        self.closed = False
        self.setup_ui()

    def setup_docks_and_widgets(self):
        pass

    def _quit_fun(self):
        self.closed = True
        return True
'''


def _make_fake_package() -> str:
    # created at import: the mixin parametrizes its tests at collection, before any fixture runs
    base = Path(tempfile.mkdtemp(prefix='fakeext_'))
    root = base / 'pymodaq_plugins_fakeext'
    ext = root / 'extensions'
    ext.mkdir(parents=True)
    (root / '__init__.py').write_text('')
    (ext / '__init__.py').write_text('')
    (ext / 'fake_ext.py').write_text(textwrap.dedent(EXTENSION))
    (ext / 'helpers.py').write_text('X = 1\n')  # a module without EXTENSION_NAME is not an extension
    (ext / '_private.py').write_text('raise RuntimeError("never imported")\n')
    sys.path.insert(0, str(base))
    return root.name


FAKE_PACKAGE = _make_fake_package()


@pytest.fixture
def fake_package():
    return FAKE_PACKAGE


def test_find_extension_classes(fake_package):
    found = find_extension_classes(fake_package)
    assert [(name, klass.__name__) for name, klass in found] == [('FAKE_EXT', 'FakeExt')]


def test_find_extension_classes_without_extensions_folder():
    assert find_extension_classes('pymodaq_plugins_mock') == []


def test_loaded_extension(fake_package):
    _, klass = find_extension_classes(fake_package)[0]
    with loaded_extension(klass) as (dashboard, extension):
        assert extension.dashboard is dashboard
        assert extension.modules_manager is not None
        assert extension.settings['flag'] is False
    assert extension.closed


def test_loaded_extension_closes_when_the_body_fails(fake_package):
    _, klass = find_extension_classes(fake_package)[0]
    with pytest.raises(ZeroDivisionError):
        with loaded_extension(klass) as (dashboard, extension):
            1 / 0
    assert extension.closed


def test_core_extension_loads():
    from pymodaq.extensions.data_mixer.data_mixer import DataMixer
    with loaded_extension(DataMixer) as (dashboard, extension):
        assert isinstance(extension, DataMixer)


class TestFakeExtension(PluginExtensionChecks):
    package_name = FAKE_PACKAGE

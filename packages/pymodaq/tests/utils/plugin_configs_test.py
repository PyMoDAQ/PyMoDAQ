"""Registration in GlobalConfig of the Config of every installed plugin package (not only instrument ones)"""
import sys
import textwrap
from importlib.metadata import EntryPoint

import pytest

from pymodaq_utils.config import GlobalConfig
from pymodaq.utils import daq_utils


def write_package(root, name: str, utils_code: str):
    package = root.joinpath(name)
    package.mkdir()
    package.joinpath('__init__.py').write_text('')
    package.joinpath('utils.py').write_text(textwrap.dedent(utils_code))
    package.joinpath('config_template.toml').write_text("a_value = 12\n")


CONFIG_CODE = """
    from pathlib import Path
    from pymodaq_utils.config import BaseConfig

    class Config(BaseConfig):
        config_template_path = Path(__file__).parent.joinpath('config_template.toml')
        config_name = f"config_{__package__.split('pymodaq_plugins_')[1]}"
"""


@pytest.fixture
def fake_plugins(tmp_path, monkeypatch):
    """Three fake plugin packages: extension only, without Config, with a broken utils module"""
    write_package(tmp_path, 'pymodaq_plugins_fakeext', CONFIG_CODE)
    write_package(tmp_path, 'pymodaq_plugins_fakenoconfig', "a = 1\n")
    write_package(tmp_path, 'pymodaq_plugins_fakebroken', "import a_module_that_does_not_exist\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    entrypoints = {
        'pymodaq.extensions': [EntryPoint('fakeext', 'pymodaq_plugins_fakeext', 'pymodaq.extensions')],
        'pymodaq.plugins': [EntryPoint(name, f'pymodaq_plugins_{name}', 'pymodaq.plugins')
                            for name in ('fakeext', 'fakenoconfig', 'fakebroken')],
    }
    monkeypatch.setattr(daq_utils, 'get_entrypoints', lambda group: entrypoints.get(group, []))
    daq_utils.register_plugin_configs.cache_clear()
    yield
    daq_utils.register_plugin_configs.cache_clear()
    GlobalConfig()._configs.pop('fakeext', None)
    for name in ('fakeext', 'fakenoconfig', 'fakebroken'):
        for module in (f'pymodaq_plugins_{name}', f'pymodaq_plugins_{name}.utils'):
            sys.modules.pop(module, None)


def test_plugin_packages_are_deduplicated(fake_plugins):
    assert daq_utils.get_plugin_packages() == ['pymodaq_plugins_fakeext', 'pymodaq_plugins_fakenoconfig',
                                               'pymodaq_plugins_fakebroken']


def test_extension_only_plugin_config_is_registered(fake_plugins):
    assert 'fakeext' not in GlobalConfig()
    registered = daq_utils.register_plugin_configs()
    assert registered == ['fakeext']
    assert GlobalConfig()('fakeext', 'a_value') == 12


def test_registering_twice_is_harmless(fake_plugins):
    daq_utils.register_plugin_configs()
    daq_utils.register_plugin_configs.cache_clear()
    assert daq_utils.register_plugin_configs() == []  # already registered, no error
    assert 'fakeext' in GlobalConfig()


def test_installed_plugins_are_registered_at_import():
    import pymodaq  # noqa: the registration is done at import
    assert 'mock' in GlobalConfig()  # pymodaq_plugins_mock, a dependency of pymodaq

import pytest
from pathlib import Path
import datetime

import toml

from pymodaq_utils import config as config_mod
from pyqtgraph.parametertree import Parameter
from pymodaq_gui.config import ConfigSaverLoader, get_set_roi_path


class CustomConfig(config_mod.BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = None
    config_name = f"custom_settings"


class TestGetSet:
    def test_get_set_roi_path(self):
        local_path = config_mod.get_set_local_dir()
        roi_path = get_set_roi_path()
        assert Path(roi_path) == Path(local_path).joinpath('roi_configs')
        assert Path(roi_path).is_dir()


class TestConfigSaverLoader:
    params = [
        {'name': 'aparent', 'type': 'group', 'children': [
            {'name': 'aparam', 'type': 'group', 'children': [
                {'name': 'min', 'type': 'float', 'value': 2.},
                {'name': 'max', 'type': 'float', 'value': 6.}
            ]},
        {'name': 'anotherparam', 'type': 'group', 'children': [
            {'name': 'min', 'type': 'bool', 'value': True},
            {'name': 'max', 'type': 'str', 'value': 'klj'}
        ]},
    ]}]

    def test_init(self, qtbot):
        settings = Parameter.create(name='settings', type='group', children=self.params)
        base_path = ['aparent', 'anotherparent']
        config = CustomConfig()
        saver_loader = ConfigSaverLoader(settings, config, base_path)

        saver_loader.save_config()
        saver_loader.load_config(settings)

    def test_modified(self, qtbot):
        settings = Parameter.create(name='settings', type='group', children=self.params)
        base_path = ['aparent', 'anotherparent']
        config = CustomConfig()
        saver_loader = ConfigSaverLoader(settings, config, base_path)

        saver_loader.save_config()
        value_before = settings['aparent', 'anotherparam', 'max']
        settings.child('aparent', 'anotherparam', 'max').setValue('hjkfrd')
        saver_loader.load_config(settings)

        assert settings['aparent', 'anotherparam', 'max'] == value_before


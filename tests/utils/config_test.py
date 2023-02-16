import pytest
from pathlib import Path
from pymodaq.utils import config as config_mod



class TestGeneral:
    def test_load_config(self):
        config = config_mod.load_config()
        config = config_mod.Config()
        config('style', 'darkstyle')
        assert config('style', 'darkstyle') == config['style']['darkstyle']


def test_get_set_local_dir():
    local_path = config_mod.get_set_local_dir()
    assert Path(local_path).is_dir()


def test_check_config():
    dict1 = {'name': 'test', 'status': True}
    dict2 = {'name': 'test_2', 'status': False}
    dict3 = {'status': None}
    assert not config_mod.check_config(dict1, dict2)
    assert config_mod.check_config(dict1, dict3)
    assert dict1 == {'name': 'test', 'status': True}
    assert dict2 == {'name': 'test_2', 'status': False}
    assert dict3 == {'status': None, 'name': 'test'}


class TestGetSet:
    def test_get_set_config_path(self):
        local_path = config_mod.get_set_local_dir()
        config_path = config_mod.get_set_config_path()
        assert Path(config_path) == Path(local_path).joinpath('config')
        assert Path(config_path).is_dir()

    def test_get_set_preset_path(self):
        local_path = config_mod.get_set_local_dir()
        preset_path = config_mod.get_set_preset_path()
        assert Path(preset_path) == Path(local_path).joinpath('preset_configs')
        assert Path(preset_path).is_dir()

    def test_get_set_pid_path(self):
        local_path = config_mod.get_set_local_dir()
        pid_path = config_mod.get_set_pid_path()
        assert Path(pid_path) == Path(local_path).joinpath('pid_configs')
        assert Path(pid_path).is_dir()

    def test_get_set_log_path(self):
        local_path = config_mod.get_set_local_dir()
        log_path = config_mod.get_set_log_path()
        assert Path(log_path) == Path(local_path).joinpath('log')
        assert Path(log_path).is_dir()

    def test_get_set_layout_path(self):
        local_path = config_mod.get_set_local_dir()
        layout_path = config_mod.get_set_layout_path()
        assert Path(layout_path) == Path(local_path).joinpath('layout_configs')
        assert Path(layout_path).is_dir()

    def test_get_set_remote_path(self):
        local_path = config_mod.get_set_local_dir()
        remote_path = config_mod.get_set_remote_path()
        assert Path(remote_path) == Path(local_path).joinpath('remote_configs')
        assert Path(remote_path).is_dir()

    def test_get_set_overshoot_path(self):
        local_path = config_mod.get_set_local_dir()
        overshoot_path = config_mod.get_set_overshoot_path()
        assert Path(overshoot_path) == Path(local_path).joinpath('overshoot_configs')
        assert Path(overshoot_path).is_dir()

    def test_get_set_roi_path(self):
        local_path = config_mod.get_set_local_dir()
        roi_path = config_mod.get_set_roi_path()
        assert Path(roi_path) == Path(local_path).joinpath('roi_configs')
        assert Path(roi_path).is_dir()




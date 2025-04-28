from pathlib import Path

from pymodaq.utils import config as config_mod_pymodaq
from pymodaq_utils import config as config_mod


def test_import():
    from pymodaq.utils.config import (BaseConfig, Config, ConfigError, get_set_config_dir, USER,
                                      CONFIG_BASE_PATH, get_set_local_dir)


class TestGetSet:
    def test_get_set_preset_path(self):
        local_path = config_mod.get_set_local_dir()
        preset_path = config_mod_pymodaq.get_set_preset_path()
        assert Path(preset_path) == Path(local_path).joinpath('preset_configs')
        assert Path(preset_path).is_dir()

    def test_get_set_pid_path(self):
        local_path = config_mod.get_set_local_dir()
        pid_path = config_mod_pymodaq.get_set_pid_path()
        assert Path(pid_path) == Path(local_path).joinpath('pid_configs')
        assert Path(pid_path).is_dir()

    def test_get_set_log_path(self):
        local_path = config_mod.get_set_local_dir()
        log_path = config_mod.get_set_log_path()
        assert Path(log_path) == Path(local_path).joinpath('log')
        assert Path(log_path).is_dir()

    def test_get_set_layout_path(self):
        local_path = config_mod.get_set_local_dir()
        layout_path = config_mod_pymodaq.get_set_layout_path()
        assert Path(layout_path) == Path(local_path).joinpath('layout_configs')
        assert Path(layout_path).is_dir()

    def test_get_set_remote_path(self):
        local_path = config_mod.get_set_local_dir()
        remote_path = config_mod_pymodaq.get_set_remote_path()
        assert Path(remote_path) == Path(local_path).joinpath('remote_configs')
        assert Path(remote_path).is_dir()

    def test_get_set_overshoot_path(self):
        local_path = config_mod.get_set_local_dir()
        overshoot_path = config_mod_pymodaq.get_set_overshoot_path()
        assert Path(overshoot_path) == Path(local_path).joinpath('overshoot_configs')
        assert Path(overshoot_path).is_dir()


def test_required_config_entries():
    config = config_mod_pymodaq.Config()
    assert 'presets' in config
    assert 'default_preset_for_scan' in config('presets')
    assert 'default_preset_for_logger' in config('presets')
    assert 'default_preset_for_pid' in config('presets')

    assert 'actuator' in config
    assert 'ui' in config('actuator')
    assert 'epsilon_default' in config('actuator')
    assert 'polling_interval_ms' in config('actuator')
    assert 'polling_timeout_s' in config('actuator')
    assert 'refresh_timeout_ms' in config('actuator')
    assert 'timeout' in config('actuator')
    assert 'siprefix' in config('actuator')
    assert 'siprefix_even_without_units' in config('actuator')
    assert 'display_units' in config('actuator')

    assert 'binary' in config('actuator')
    assert 'value_1' in config('actuator', 'binary')
    assert 'value_2' in config('actuator', 'binary')

    assert 'viewer' in config
    assert 'daq_type' in config('viewer')
    assert 'viewer_in_thread' in config('viewer')
    assert 'timeout' in config('viewer')
    assert 'allow_settings_edition' in config('viewer')

    assert 'scan' in config
    assert 'scan_in_thread' in config('scan')
    assert 'show_popups' in config('scan')
    assert 'default' in config('scan')
    assert 'Naverage' in config('scan')
    assert 'average_on_top' in config('scan')
    assert 'steps_limit' in config('scan')
    assert 'sort1D' in config('scan')

    assert 'timeflow' in config('scan')
    assert 'wait_time' in config('scan', 'timeflow')
    assert 'wait_time_between' in config('scan', 'timeflow')
    assert 'timeout' in config('scan', 'timeflow')
from pathlib import Path

import pymodaq_gui.config
from pymodaq import ActuatorUIFactory
from pymodaq.utils import config as config_mod_pymodaq
from pymodaq_utils import config as config_mod



class TestGetSet:
    def test_get_set_experiment_path(self):
        local_path = config_mod.get_set_local_dir()
        experiment_path = config_mod_pymodaq.get_set_experiment_path()
        assert Path(experiment_path) == Path(local_path).joinpath('experiments')
        assert Path(experiment_path).is_dir()

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

    assert 'actuator' in config
    assert 'ui' in config('actuator')
    assert 'epsilon_default' in config('actuator')
    assert 'polling_interval_ms' in config('actuator')
    assert 'polling_timeout_s' in config('actuator')
    assert 'refresh_timeout_ms' in config('actuator')
    assert 'siprefix' in config('actuator')
    assert 'siprefix_even_without_units' in config('actuator')
    assert 'display_units' in config('actuator')

    for ui in ActuatorUIFactory.keys():
        assert ui in config('actuator', 'ui')

    assert 'default_value_red' in config('actuator')
    assert 'default_value_green' in config('actuator')
    assert 'default_value_relative' in config('actuator')

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
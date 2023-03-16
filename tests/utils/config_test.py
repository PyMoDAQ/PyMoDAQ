import pytest
from pathlib import Path
import datetime

import toml

from pymodaq.utils import config as config_mod

TOML_DICT = dict(scan=dict(scan1d=dict(start=0.,
                                       stop=5,
                                       step=0.1),
                           scan2d=dict(rmax=5,
                                       rstep=0.2),
                           ),
                 general=dict(name='myname',
                              date=datetime.date.today()))


def create_toml(path: Path):
    path.write_text(toml.dumps(TOML_DICT))


def test_replace_extension():
    test_name = 'config_test'

    assert config_mod.replace_file_extension(test_name+'.tiff', '.toml') == f'{test_name}.toml'
    assert config_mod.replace_file_extension(test_name+'.tiff', 'toml') == f'{test_name}.toml'
    assert config_mod.replace_file_extension(test_name, 'toml') == f'{test_name}.toml'


@pytest.mark.parametrize('user', [False, True])
def test_get_set_local_dir(user):
    local_path = config_mod.get_set_local_dir(user=user)
    assert isinstance(local_path, Path)
    assert local_path.is_dir()


class TestGetSet:
    def test_get_set_config_path(self):
        local_path = config_mod.get_set_local_dir()
        config_path = config_mod.get_set_config_dir()
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


class TestCopy:
    def test_copy_default(self):

        test_name = 'config'
        dest_file = config_mod.copy_template_config()
        dest_path = config_mod.get_set_local_dir()
        assert dest_path.joinpath(f'{test_name}.toml') == dest_file

    def test_copy_source(self, tmp_path):
        suffix = '.ini'
        test_name = 'config_test'
        template_path = tmp_path.joinpath('template.toml')
        create_toml(template_path)

        dest_file = config_mod.copy_template_config(test_name + suffix, source_path=template_path)
        dest_path = config_mod.get_set_local_dir()
        assert dest_path.joinpath(f'{test_name}.toml') == dest_file
        assert toml.load(dest_file) == TOML_DICT

    def test_copy_dest(self, tmp_path):
        test_name = 'config_test'
        template_path = tmp_path.joinpath('template.toml')
        create_toml(template_path)
        dest_name = 'dest'
        dest_path = tmp_path.joinpath(dest_name)
        dest_path.mkdir()
        dest_file = config_mod.copy_template_config(test_name, source_path=template_path, dest_path=dest_path)

        assert dest_path.joinpath(f'{test_name}.toml') == dest_file
        assert toml.load(dest_file) == TOML_DICT


def test_load_system_config(tmp_path):
    test_name = 'config_test'
    template_path = tmp_path.joinpath('template.toml')
    TOML_DICT['other'] = '123'
    create_toml(template_path)

    system_file = config_mod.get_set_local_dir().joinpath(test_name + '.toml')
    user_file = config_mod.get_set_local_dir(True).joinpath(test_name + '.toml')
    system_file.unlink(missing_ok=True)
    user_file.unlink(missing_ok=True)

    dest_file = config_mod.copy_template_config(test_name, source_path=template_path)
    config_dict = config_mod.load_system_config_and_update_from_user(test_name)
    assert config_dict == TOML_DICT
    assert config_dict['other'] == '123'

    user_path = config_mod.get_set_local_dir(user=True).joinpath(config_mod.replace_file_extension(test_name, 'toml'))
    user_dict = dict(other='456')
    config_mod.create_toml_from_dict(user_dict, user_path)
    assert toml.load(user_path) == user_dict

    config_dict = config_mod.load_system_config_and_update_from_user(test_name)
    assert config_dict['other'] == '456'


def test_check_config():
    dict1 = {'name': 'test', 'status': True}
    dict2 = {'name': 'test_2', 'status': False}
    dict3 = {'status': None}
    assert not config_mod.check_config(dict1, dict2)
    assert config_mod.check_config(dict1, dict3)
    assert dict1 == {'name': 'test', 'status': True}
    assert dict2 == {'name': 'test_2', 'status': False}
    assert dict3 == {'status': None, 'name': 'test'}


class TestConfig:

    def test_init(self):
        assert config_mod.Config.config_name == 'config_pymodaq'
        assert config_mod.Config.config_template_path.name == 'config_template.toml'

    def test_call(self):
        config = config_mod.Config()
        assert config('style', 'darkstyle') == config['style']['darkstyle']

    def test_get_item(self):
        config = config_mod.Config()
        assert config['style', 'darkstyle'] == config['style']['darkstyle']

    def test_set_item(self):
        config = config_mod.Config()

        config['style', 'darkstyle'] = 'bright'
        assert config('style', 'darkstyle') == 'bright'


class Config(config_mod.BaseConfig):
    config_name = 'custom_config_tested'
    config_template_path = Path(__file__).parent.joinpath('data/config_template.toml')


def test_custom_config():

    config_mod.get_config_file(Config.config_name, True).unlink(missing_ok=True)
    config_mod.get_config_file(Config.config_name, False).unlink(missing_ok=True)

    config = Config()
    config_dict = toml.load(config.config_template_path)

    assert config_mod.get_config_file(config.config_name, user=False).is_file()

    assert config.to_dict() == config_dict








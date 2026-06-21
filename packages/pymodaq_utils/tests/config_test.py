import atexit

import pytest
from pathlib import Path
import datetime

import toml

from pymodaq_utils.config import Config, GlobalConfig, BaseConfig, replace_file_extension, get_set_config_dir, get_set_local_dir, \
    copy_template_config, load_system_config_and_update_from_user, create_toml_from_dict, check_config, get_config_file, \
    recursive_iterable_flattening
from pymodaq_utils.config import _delete_config_files


class CustomConfig0(BaseConfig):
    config_name = 'test_utils_custom0'
    config_template_path = Path(__file__).parent.joinpath('data/config_template.toml')

    def __init__(self):
        super().__init__()
        atexit.unregister(self.save)
        atexit.register(lambda : _delete_config_files(self))


class CustomConfig1(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_name = "test_utils_custom1"
    config_template_path = None

    def __init__(self):
        super().__init__()
        atexit.unregister(self.save)
        atexit.register(lambda : _delete_config_files(self))


TOML_DICT = dict(
    scan=dict(scan1d=dict(start=0.,
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
    test_name = 'test'

    assert replace_file_extension(test_name+'.tiff', '.toml') == f'{test_name}.toml'
    assert replace_file_extension(test_name+'.tiff', 'toml') == f'{test_name}.toml'
    assert replace_file_extension(test_name, 'toml') == f'{test_name}.toml'


def test_import():
    from pymodaq_utils.config import (BaseConfig, Config, ConfigError, get_set_config_dir, USER,
                                      CONFIG_BASE_PATH, get_set_local_dir)

@pytest.mark.parametrize('user', [False, True])
def test_get_set_config_dir(user):
    local_path = get_set_config_dir(user=user)
    assert isinstance(local_path, Path)
    assert local_path.is_dir()


class TestGetSet:
    def test_get_set_config_path(self):
        local_path = get_set_local_dir()
        config_path = get_set_config_dir()
        assert Path(config_path) == Path(local_path).joinpath('config')
        assert Path(config_path).is_dir()



class TestCopy:
    def test_copy_default(self):

        test_name = 'config'
        dest_file = copy_template_config()
        dest_path = get_set_config_dir()

        assert dest_path.joinpath(f'{test_name}.toml') == dest_file


    def test_copy_source(self, tmp_path):
        suffix = '.ini'
        test_name = 'test'
        template_path = tmp_path.joinpath('template.toml')
        create_toml(template_path)

        dest_file = copy_template_config(test_name + suffix, source_path=template_path)
        dest_path = get_set_config_dir()
        assert dest_path.joinpath(f'{test_name}.toml') == dest_file
        assert toml.load(dest_file) == TOML_DICT

    def test_copy_dest(self, tmp_path):
        test_name = 'test'
        template_path = tmp_path.joinpath('template.toml')
        create_toml(template_path)
        dest_name = 'dest'
        dest_path = tmp_path.joinpath(dest_name)
        dest_path.mkdir()
        dest_file = copy_template_config(test_name, source_path=template_path, dest_path=dest_path)

        assert dest_path.joinpath(f'{test_name}.toml') == dest_file
        assert toml.load(dest_file) == TOML_DICT


def test_load_system_config(tmp_path):
    test_name = 'test'
    template_path = tmp_path.joinpath('template.toml')
    TOML_DICT['other'] = '123'
    create_toml(template_path)

    system_file = get_set_config_dir().joinpath(test_name + '.toml')
    user_file = get_set_config_dir(user=True).joinpath(test_name + '.toml')
    system_file.unlink(missing_ok=True)
    user_file.unlink(missing_ok=True)

    dest_file = copy_template_config(test_name, source_path=template_path)
    config_dict = load_system_config_and_update_from_user(test_name)
    assert config_dict == TOML_DICT
    assert config_dict['other'] == '123'

    user_path = get_set_config_dir(user=True).joinpath(
        replace_file_extension(test_name, 'toml'))
    user_dict = {'other' : '456'}
    create_toml_from_dict(user_dict, user_path)
    assert toml.load(user_path) == user_dict

    config_dict = load_system_config_and_update_from_user(test_name)
    assert config_dict['other'] == '456'

    # modifying nested dicts



def test_check_config():
    dict1 = {'name': 'test', 'status': True}
    dict2 = {'name': 'test_2', 'status': False}
    dict3 = {'status': None}
    assert not check_config(dict1, dict2)
    assert check_config(dict1, dict3)
    assert dict1 == {'name': 'test', 'status': True}
    assert dict2 == {'name': 'test_2', 'status': False}
    assert dict3 == {'status': None, 'name': 'test'}


class TestConfig:

    def test_init(self):
        assert CustomConfig0.config_name == 'test_utils_custom0'
        assert CustomConfig0.config_template_path.name == 'config_template.toml'

    def test_call(self):
        config = CustomConfig0()
        assert config('style', 'darkstyle') == config['style']['darkstyle']

    def test_get_item(self):
        config = CustomConfig0()
        assert config['style', 'darkstyle'] == config['style']['darkstyle']

    def test_set_item(self):
        config = CustomConfig1()

        config['style', 'theme'] = 'bright'
        assert config('style', 'theme') == 'bright'

    def test_get_children(self):
        config = GlobalConfig()
        config = config['utils']
        children = config.get_children('network', 'logging')
        for child in ['user', 'sql']:
            assert child in children

    def test_get(self):
        config = CustomConfig1()

        assert config.get(('an', 'unknown', 'key', 'in', 'the', 'config'), 'default_value') == 'default_value'
        config['style', 'theme'] = True
        assert config.get(('style', 'theme')) == True


class TestConfigSingleton:
    def test_is_same_object(self):
        config1 = CustomConfig0()
        config2 = CustomConfig0()

        assert config1 is config2


    def test_change_is_shared_same_class(self):
        config1 = CustomConfig0()
        config2 = CustomConfig0()

        assert config1['style', 'darkstyle'] == config2['style', 'darkstyle']

        config1['style', 'darkstyle'] = not config1['style', 'darkstyle']
        assert config1['style', 'darkstyle'] == config2['style', 'darkstyle']

    def test_different_class_different_objects(self):
        config1 = CustomConfig0()
        config2 = CustomConfig1()

        assert config1 is not config2

    def test_change_is_not_shared_different_class(self):
        config1 = CustomConfig0()
        config2 = CustomConfig1()

        # This entry doesn't exist in CustomConfig, let's create it
        config1['style', 'darkstyle'] = True
        config2['style', 'darkstyle'] = True
        assert config1['style', 'darkstyle'] == config2['style', 'darkstyle']

        config1['style', 'darkstyle'] = False
        assert config1['style', 'darkstyle'] != config2['style', 'darkstyle']

        #Let's put it back to its original state
        config1['style', 'darkstyle'] = True



def test_custom_config():
    config = CustomConfig0()
    config_dict = toml.load(config.config_template_path)

    assert get_config_file(config.config_name, user=False).is_file()

    assert config.to_dict() == config_dict

def test_nested_update_from_user(tmp_path):
    """ make sure the user defined entry within a nested config is loaded but that the other entries are also loaded
     from the system wide config file"""

    test_name = 'test'
    template_path = tmp_path.joinpath('template.toml')
    create_toml(template_path)  # creates a system wide config using TOML_DICT

    system_file = get_set_config_dir().joinpath(test_name + '.toml')
    user_file = get_set_config_dir(user=True).joinpath(test_name + '.toml')
    dest_file = copy_template_config(test_name, source_path=template_path)

    user_dict = dict(
        scan=dict(scan1d=dict(start=23.,
                       ),
                  ),
    )

    with open(user_file, 'w') as f:
        toml.dump(user_dict, f)  # creates a user config file with one entry of the nested config updated

    config_dict = load_system_config_and_update_from_user(test_name)
    assert 'start' in config_dict['scan']['scan1d']
    assert 'stop' in config_dict['scan']['scan1d']  # making sure the entry that is not in the user is still present

    Path(user_file).unlink(missing_ok=True)


def test_recursive_iterable_flattening():

    flattened = recursive_iterable_flattening([1, 3, ['klm', 4], 'poi', [1, [[1, 2], 'uio']]])
    assert flattened == [1, 3, 'klm', 4, 'poi', 1, 1, 2, 'uio']


def test_required_config_entries():
    config = Config()

    assert 'general' in config
    assert 'debug_level' in config('general')
    assert isinstance(config('general', 'debug_level'), list)
    assert 'check_version' in config('general')

    assert 'user' in config
    assert 'name' in config('user')

    assert 'backup' in config
    assert 'keep_backup' in config('backup')
    assert 'folder' in config('backup')
    assert 'limit' in config('backup')

    assert 'network' in config
    assert 'logging' in config('network')
    assert 'user' in config('network', 'logging')
    assert 'username' in config('network', 'logging', 'user')
    assert 'pwd' in config('network', 'logging', 'user')

    assert 'sql' in config('network', 'logging')
    assert 'ip' in config('network', 'logging', 'sql')
    assert 'port' in config('network', 'logging', 'sql')

    assert 'leco-server' in config('network')
    assert 'run_coordinator_at_startup' in config('network', 'leco-server')
    assert 'host' in config('network', 'leco-server')
    assert 'port' in config('network', 'leco-server')


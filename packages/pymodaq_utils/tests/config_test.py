import pytest
from pathlib import Path
import datetime

import toml

from pymodaq_utils import config as config_mod


TOML_DICT = dict(
    scan=dict(scan1d=
              dict(start=0.,
                   stop=5,
                   step=0.1),
              scan2d=
              dict(rmax=5,
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

    user_path = config_mod.get_set_local_dir(user=True).joinpath(
        config_mod.replace_file_extension(test_name, 'toml'))
    user_dict = dict(other='456')
    config_mod.create_toml_from_dict(user_dict, user_path)
    assert toml.load(user_path) == user_dict

    config_dict = config_mod.load_system_config_and_update_from_user(test_name)
    print(config_dict)
    assert config_dict['other'] == '456'

    # modifying nested dicts



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
        assert config_mod.Config.config_name == 'config_pymodaq_utils'
        assert config_mod.Config.config_template_path.name == 'config_template.toml'

    def test_call(self):
        config = config_mod.Config()
        assert config('style', 'theme') == config['style']['theme']

    def test_get_item(self):
        config = config_mod.Config()
        assert config['style', 'theme'] == config['style']['theme']

    def test_set_item(self):
        config = config_mod.Config()

        config['style', 'theme'] = 'bright'
        assert config('style', 'theme') == 'bright'

    def test_get_children(self):
        config = config_mod.Config()

        children = config.get_children('data_saving')
        for child in ['h5file', 'hsds', 'data_type']:
            assert child in children

    def test_get(self):
        config = config_mod.Config()

        assert config.get(('an', 'unknown', 'key', 'in', 'the', 'config'), 'default_value') == 'default_value'
        config['style', 'theme'] = True
        assert config.get(('style', 'theme')) == True


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


def test_nested_update_from_user(tmp_path):
    """ make sure the user defined entry within a nested config is loaded but that the other entries are also loaded
     from the system wide config file"""

    test_name = 'config_test'
    template_path = tmp_path.joinpath('template.toml')
    create_toml(template_path)  # creates a system wide config using TOML_DICT

    system_file = config_mod.get_set_local_dir().joinpath(test_name + '.toml')
    user_file = config_mod.get_set_local_dir(True).joinpath(test_name + '.toml')
    dest_file = config_mod.copy_template_config(test_name, source_path=template_path)

    user_dict = dict(
        scan=dict(scan1d=
                  dict(start=23.,
                       ),
                  ),
    )

    with open(user_file, 'w') as f:
        toml.dump(user_dict, f)  # creates a user config file with one entry of the nested config updated

    config_dict = config_mod.load_system_config_and_update_from_user(test_name)
    assert 'start' in config_dict['scan']['scan1d']
    assert 'stop' in config_dict['scan']['scan1d']  # making sure the entry that is not in the user is still present


class CustomConfig(config_mod.BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = None
    config_name = f"custom_settings"


def test_recursive_iterable_flattening():

    flattened = config_mod.recursive_iterable_flattening([1, 3, ['klm', 4], 'poi', [1, [[1, 2], 'uio']]])
    assert flattened == [1, 3, 'klm', 4, 'poi', 1, 1, 2, 'uio']


def test_required_config_entries():
    config = config_mod.Config()
    assert 'style' in config
    assert 'theme' in config['style']
    assert 'syntax_highlighting' in config['style']
    assert 'language' in config['style']
    assert 'country' in config['style']

    assert 'qtbackend' in config
    assert 'backends' in config['qtbackend']
    assert 'backend' in config['qtbackend']

    assert 'general' in config
    assert 'debug_level' in config('general')
    assert 'debug_levels' in config('general')
    assert 'check_version' in config('general')
    assert 'message_status_persistence' in config('general')
    assert 'hdf5_backend' in config('general')

    assert 'data_saving' in config
    assert 'h5file' in config['data_saving']
    assert 'save_path' in config('data_saving', 'h5file')
    assert 'compression_level' in config('data_saving', 'h5file')

    assert 'data_type' in config['data_saving']
    assert 'dynamic' in config('data_saving', 'data_type')
    assert 'dynamics' in config('data_saving', 'data_type')

    assert 'user' in config
    assert 'name' in config('user')

    assert 'plotting' in config
    assert 'backend' in config('plotting')
    assert 'plot_colors' in config('plotting')

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

    assert 'tcp-server' in config('network')
    assert 'ip' in config('network', 'tcp-server')
    assert 'port' in config('network', 'tcp-server')

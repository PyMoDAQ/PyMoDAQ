from abc import abstractproperty

from os import environ
import sys
import datetime
from pathlib import Path
from typing import Union, Dict, TypeVar, Any

import toml


try:
    USER = environ['USERNAME'] if sys.platform == 'win32' else environ['USER']
except:
    USER = 'unknown_user'

CONFIG_BASE_PATH = Path(environ['PROGRAMDATA']) if sys.platform == 'win32' else \
    Path('Library/Application Support') if sys.platform == 'darwin' else Path('/etc')


KeyType = TypeVar('KeyType')


def deep_update(mapping: Dict[KeyType, Any], *updating_mappings: Dict[KeyType, Any]) -> Dict[KeyType, Any]:
    """ Make sure a dictionary is updated using another dict in any nested level
    Taken from Pydantic v1
    """
    updated_mapping = mapping.copy()
    for updating_mapping in updating_mappings:
        for k, v in updating_mapping.items():
            if k in updated_mapping and isinstance(updated_mapping[k], dict) and isinstance(v, dict):
                updated_mapping[k] = deep_update(updated_mapping[k], v)
            else:
                updated_mapping[k] = v
    return updated_mapping


def replace_file_extension(filename: str, ext: str):
    """Replace the extension of a file by the specified one, without the dot"""
    file_name = Path(filename).stem  # remove eventual extensions
    if ext[0] == '.':
        ext = ext[1:]
    file_name += '.' + ext
    return file_name


def getitem_recursive(dic, *args, ndepth=0, create_if_missing=False):
    """Will scan recursively a dictionary in order to get the item defined by the iterable args

    Parameters
    ----------
    dic: dict
        the dictionary to scan
    args: an iterable of str
        keys of the dict
    ndepth: int
        by default (0) get the last element defined by args. 1 would mean it get the parent dict, 2 the parent of the
        parent...
    create_if_missing: bool
        if the entry is not present, create it assigning the 'none' default value (as a lower case string)
    Returns
    -------
    object or dict
    """
    args = list(args)
    while len(args) > ndepth:
        try:
            arg = args.pop(0)
            dic = dic[arg]
        except KeyError as e:
            if create_if_missing:
                if len(args) > 0:
                    dic[arg] = {}
                    dic = dic[arg]
                else:
                    dic[arg] = 'none'
                    dic = 'none'
            else:
                raise e
    return dic


def get_set_path(a_base_path: Path, dir_name: str) -> Path:
    path_to_get = a_base_path.joinpath(dir_name)
    if not path_to_get.is_dir():
        try:
            path_to_get.mkdir()
        except PermissionError as e:
            print(f"Cannot create local config folder at this location: {path_to_get}"
                  f", try using admin rights. "
                  f"Changing the not permitted path to a user one: {Path.home().joinpath(dir_name)}.")
            path_to_get = Path.home().joinpath(dir_name)
            if not path_to_get.is_dir():
                path_to_get.mkdir()
    return path_to_get


def get_set_local_dir(user=False) -> Path:
    """Defines, creates and returns a local folder where configuration files will be saved

    Depending on the os the configurations files will be stored in CONFIG_BASE_PATH, then
    each user will have another one created that could override the default and system-wide base folder

    Parameters
    ----------
    user: bool
        if False get the system-wide folder, otherwise the user folder

    Returns
    -------
    Path: the local path
    """
    if user:
        local_path = get_set_path(Path.home(), '.pymodaq')
    else:
        local_path = get_set_path(CONFIG_BASE_PATH, '.pymodaq')
    return local_path


def get_config_file(config_file_name: str, user=False):
    return get_set_local_dir(user).joinpath(replace_file_extension(config_file_name, 'toml'))


def get_set_config_dir(config_name='config', user=False):
    """Creates a folder in the local config directory to store specific configuration files

    Parameters
    ----------
    config_name: (str) name of the configuration folder
    user: bool
        if False get the system-wide folder, otherwise the user folder

    Returns
    -------
    Path

    See Also
    --------
    get_set_local_dir
    """
    return get_set_path(get_set_local_dir(user=user), config_name)


def get_set_log_path():
    """ creates and return the config folder path for log files
    """
    return get_set_config_dir('log')


def get_set_preset_path():
    """ creates and return the config folder path for managers files
    """
    return get_set_config_dir('preset_configs')


def get_set_batch_path():
    """ creates and return the config folder path for managers files
    """
    return get_set_config_dir('batch_configs')


def get_set_pid_path():
    """ creates and return the config folder path for PID files
    """
    return get_set_config_dir('pid_configs')


def get_set_layout_path():
    """ creates and return the config folder path for layout files
    """
    return get_set_config_dir('layout_configs')


def get_set_remote_path():
    """ creates and return the config folder path for remote (shortcuts or joystick) files
    """
    return get_set_config_dir('remote_configs')


def get_set_overshoot_path():
    """ creates and return the config folder path for overshoot files
    """
    return get_set_config_dir('overshoot_configs')


def get_set_roi_path():
    """ creates and return the config folder path for managers files
    """
    return get_set_config_dir('roi_configs')


def create_toml_from_dict(mydict: dict, dest_path: Path):
    """Create a Toml file at a given path from a dictionnary"""
    dest_path.write_text(toml.dumps(mydict))


def check_config(config_base: dict, config_local: dict):
        """Compare two configuration dictionaries. Adding missing keys

        Parameters
        ----------
        config_base: dict
            The base dictionaries with possible new keys
        config_local: dict
            a dict from a local config file potentially missing keys

        Returns
        -------
        bool: True if keys where missing else False
        """
        status = False
        for key in config_base:
            if key in config_local:
                if isinstance(config_base[key], dict):
                    status = status or check_config(config_base[key], config_local[key])
            else:
                config_local[key] = config_base[key]
                status = True
        return status


def copy_template_config(config_file_name: str = 'config', source_path: Union[Path, str] = None,
                         dest_path: Union[Path, str] = None):
    """Get a toml file path and copy it

    the destination is made of a given folder path (or the system-wide local path by default) and the config_file_name
    appended by the suffix '.toml'

    The source file (or pymodaq config template path by default) is read and dumped in this destination file

    Parameters
    ----------
    config_file_name: str
        the name of the destination config file
    source_path: Path or str
        the path of the toml source to be copied
    dest_path: Path or str
        the destination path of the copied config

    Returns
    -------
    Path: the path of the copied file
    """
    if dest_path is None:
        dest_path = get_set_local_dir()

    file_name = Path(config_file_name).stem  # remove eventual extensions
    file_name += '.toml'
    dest_path_with_filename = dest_path.joinpath(file_name)

    if source_path is None:
        config_template_dict = toml.load(Path(__file__).parent.parent.joinpath('resources/config_template.toml'))
    else:
        config_template_dict = toml.load(Path(source_path))

    create_toml_from_dict(config_template_dict, dest_path_with_filename)
    return dest_path_with_filename


def load_system_config_and_update_from_user(config_file_name: str):
    """load from a system-wide config file, update it from the user config file

    Parameters
    ----------
    config_file_name: str
        The config file to be loaded
    Returns
    -------
    dict: contains the toml system-wide file update with the user file
    """
    config_dict = dict([])
    toml_base_path = get_config_file(config_file_name, user=False)
    if toml_base_path.is_file():
        config_dict = toml.load(toml_base_path)
    toml_user_path = get_config_file(config_file_name, user=True)
    if toml_user_path.is_file():
        config_dict = deep_update(config_dict, toml.load(toml_user_path))
    return config_dict


class ConfigError(Exception):
    pass


class BaseConfig:
    """Base class to manage configuration files

    Should be subclassed with proper class attributes for each configuration file you need with pymodaq

    Attributes
    ----------
    config_name: str
        The name with which the configuration will be saved
    config_template_path: Path
        The Path of the template from which the config is constructed

    """
    config_template_path: Path = abstractproperty()
    config_name: str = abstractproperty()

    def __init__(self):
        self._config = self.load_config(self.config_name, self.config_template_path)

    def __repr__(self):
        return f'{self.config_name} configuration file'

    def __call__(self, *args):
        try:
            ret = getitem_recursive(self._config, *args)
        except KeyError as e:
            raise ConfigError(f'the path {args} does not exist in your configuration toml file, check '
                              f'your pymodaq_local folder')
        return ret

    def to_dict(self):
        return self._config

    def __getitem__(self, item):
        """for backcompatibility when it was a dictionnary"""
        if isinstance(item, tuple):
            return getitem_recursive(self._config, *item)
        else:
            return self._config[item]

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            dic = getitem_recursive(self._config, *key, ndepth=1, create_if_missing=False)
            dic[key[-1]] = value
        else:
            self._config[key] = value

    def load_config(self, config_file_name, template_path: Path):
        """Load a configuration file from both system-wide and user file

        check also if missing entries in the configuration file compared to the template"""
        toml_base_path = get_config_file(config_file_name, user=False)
        toml_user_path = get_config_file(config_file_name, user=True)
        if toml_base_path.is_file():
            config = toml.load(toml_base_path)
            config_template = toml.load(template_path)
            if check_config(config_template, config):  # check if all fields from template are there
                # (could have been  modified by some commits)
                create_toml_from_dict(config, toml_base_path)

        else:
            copy_template_config(config_file_name, template_path, toml_base_path.parent)

        if not toml_user_path.is_file():
            # create the author from environment variable
            config_dict = self.dict_to_add_to_user()
            if config_dict is not None:
                create_toml_from_dict(config_dict, toml_user_path)

        config_dict = load_system_config_and_update_from_user(config_file_name)
        return config_dict

    def dict_to_add_to_user(self):
        """To subclass"""
        return dict([])

    @property
    def config_path(self):
        """Get the user config path"""
        return get_config_file(self.config_name, user=True)

    @property
    def system_config_path(self):
        """Get the system_wide config path"""
        return get_config_file(self.config_name, user=False)

    def save(self):
        """Save the current Config object into the user toml file"""
        self.config_path.write_text(toml.dumps(self.to_dict()))


class Config(BaseConfig):
    """Main class to deal with configuration values for PyMoDAQ"""
    config_template_path = Path(__file__).parent.parent.joinpath('resources/config_template.toml')
    config_name = 'config_pymodaq'

    def dict_to_add_to_user(self):
        """To subclass"""
        return dict(user=dict(name=USER))



    
if __name__ == '__main__':

    config = Config()
    config('style', 'darkstyle')
    assert config('style', 'darkstyle') == config['style']['darkstyle']


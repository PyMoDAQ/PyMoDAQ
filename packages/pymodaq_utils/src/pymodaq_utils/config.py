import atexit
import threading
from abc import abstractproperty
from collections.abc import Iterable

import copy
import functools
from functools import cached_property
from os import environ
import sys
import datetime
from pathlib import Path
from typing import Union, Dict, TypeVar, Any, List, TYPE_CHECKING, Callable, Type
from typing import Iterable as IterableType

from pymodaq_utils import warnings
from pymodaq_utils.singleton import Singleton
from fasteners import ReaderWriterLock

import toml
import logging
if TYPE_CHECKING:
    from pymodaq_gui.parameter import Parameter


USER = environ.get('USERNAME' if sys.platform == 'win32' else 'USER', 'unknown_user')

CONFIG_BASE_PATH = (
    Path(environ['PROGRAMDATA']) if sys.platform == 'win32' else
    Path('/Library/Application Support') if sys.platform == 'darwin' else
    Path('/etc')
)


KeyType = TypeVar('KeyType')


def replace_item_in_list(items: list[Any],
                         old: Any,
                         new: Any):
    if not isinstance(items, list):
        items = list(items)
    index = items.index(old)
    items[index] = new
    return items


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
    return str(Path(filename).with_suffix('.' + ext.lstrip('.')))


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


def recursive_iterable_flattening(aniterable: IterableType):
    flatten_iter = []
    for elt in aniterable:
        if not isinstance(elt, str) and isinstance(elt, Iterable):
            flatten_iter.extend(recursive_iterable_flattening(elt))
        else:
            flatten_iter.append(elt)
    return flatten_iter


def get_set_path(a_base_path: Path, dir_name: str) -> Path:
    path_to_get = a_base_path.joinpath(dir_name)
    if not path_to_get.is_dir():
        try:
            path_to_get.mkdir()
        except PermissionError as e:
            logging.warning(f"Cannot create local config folder at this location: {path_to_get}"
                            f", try using admin rights. "
                            f"Changing the not permitted path to a user "
                            f"one: {Path.home().joinpath(dir_name)}.")
            path_to_get = Path.home().joinpath(dir_name)
            if not path_to_get.is_dir():
                path_to_get.mkdir()
    return path_to_get


@functools.cache
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


def get_config_file(config_file_name: str, user=False) -> Path:
    return get_set_config_dir('config',user=user).joinpath(replace_file_extension(config_file_name, 'toml'))


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
        dest_path = get_set_config_dir('config')

    file_name = Path(config_file_name).stem  # remove eventual extensions
    file_name += '.toml'
    dest_path_with_filename = dest_path.joinpath(file_name)

    if source_path is None:
        config_template_dict = {}
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


class ConfigSingleton(Singleton):
    _allow_direct_call: bool = False
    def __call__(cls, *args, **kwargs):
        if not cls._allow_direct_call:
            warnings.deprecation_msg(
                "Calling a constructor on Config classes is deprecated.\n"
                "You should use @GlobalConfig.register() decorator instead.\n"
                f"Your config entries will then be stored inside GlobalConfig "
                f"object, prefixed with `config_name` "
                f"(i.e. config['an_entry'] -> config['{getattr(cls, 'config_name', '`self.config_name`')}', 'an_entry'])"
            )
        return Singleton.__call__(cls, *args, **kwargs)



class BaseConfig(metaclass=ConfigSingleton):
    """Base class to manage configuration files

    Should be subclassed with proper class attributes for each configuration file you need with pymodaq

    Attributes
    ----------
    config_name: str
        The name with which the configuration will be saved
    config_template_path: Path
        The Path of the template from which the config is constructed

    """
    config_template_path: Path = NotImplemented
    config_name: str = NotImplemented


    def __init__(self):
        self._lock = ReaderWriterLock()
        self._config = {}
        self._modified_config = {}
        self.load()
        atexit.register(self.save)

    def __del__(self):
        self.save()

    def __repr__(self):
        return f'{self.config_name} configuration file'

    def __call__(self, *args):
        with self._lock.read_lock():
            try:
                ret = getitem_recursive(self._config, *args)
            except KeyError as e:
                raise ConfigError(f'the path {args} does not exist in your configuration toml'
                                  f' file, check your config folder')
            return ret

    def __contains__(self, item):
        with self._lock.read_lock():
            ret = self._config.__contains__(item)
        return ret

    def to_dict(self):
        # We need a copy as a returned object will be unlocked
        # So it could be modified
        with self._lock.read_lock():
            ret = copy.deepcopy(self._config)
        return ret

    def to_xml_string(self) -> bytes:
        """ Convert this object to a xml string representing it as a Parameter Tree

        pymodaq_gui is necessary for this purpose
        """
        try:
            from pymodaq_gui.utils.widgets.tree_toml import TreeFromToml
            from pymodaq_gui.parameter.ioxml import parameter_to_xml_string
            config_tree = TreeFromToml(self, capitalize=False)
            return parameter_to_xml_string(config_tree.settings)
        except ImportError:
            return b''

    def get(self, key: Union[str, Iterable[str]], default=None):
        with self._lock.read_lock():
            try:
                ret = self[key]
            except KeyError:
                ret = default
        return ret

    def __getitem__(self, item):
        """for backcompatibility when it was a dictionnary"""
        with self._lock.read_lock():
            if isinstance(item, tuple):
                ret = getitem_recursive(self._config, *item)
            else:
                ret = self._config[item]
        return ret

    def __setitem__(self, key, value):
        with self._lock.write_lock():
            if isinstance(key, tuple):
                # In visible config and modified config
                for config in (self._config, self._modified_config):
                    parent = getitem_recursive(config, *key, ndepth=1, create_if_missing=True)
                    parent[key[-1]] = {} if value is None else value

            else:
                self._config[key] = value
                self._modified_config[key] = value

    def dict_to_add_to_user(self):
        """To subclass"""
        return dict([])

    @cached_property
    def config_path(self):
        """Get the user config path"""
        return get_config_file(self.config_name, user=True)

    @cached_property
    def system_config_path(self):
        """Get the system_wide config path"""
        return get_config_file(self.config_name, user=False)

    def load(self):
        """Load a configuration file from both system-wide and user file
        check also if missing entries in the configuration file compared to the template"""

        # write lock because it MODIFIES config
        with self._lock.write_lock():
            toml_system_path = get_config_file(self.config_name, user=False)
            toml_user_path = get_config_file(self.config_name, user=True)
            if toml_system_path.is_file():
                config = toml.load(toml_system_path)
                if self.config_template_path is not None:
                    config_template = toml.load(self.config_template_path)
                else:
                    config_template = {}
                if check_config(config_template, config):  # check if all fields from template are there
                    # (could have been  modified by some commits)
                    create_toml_from_dict(config, toml_system_path)

            else:
                copy_template_config(self.config_name, self.config_template_path, toml_system_path.parent)

            if not toml_user_path.is_file():
                # create the author from environment variable
                config_dict = self.dict_to_add_to_user()
                if config_dict is not None:
                    create_toml_from_dict(config_dict, toml_user_path)
            self._config = load_system_config_and_update_from_user(self.config_name)
            self._modified_config = toml.load(get_config_file(self.config_name, user=True))

    def save(self):
        """Save the current Config object into the user toml file and reload it """
        with self._lock.write_lock():
            self.config_path.write_text(toml.dumps(self._modified_config))
            #  self._config = self.load_config(self.config_name, self.config_template_path)

    def get_children(self, *path: IterableType[str]):
        """ Get the list of config entries at a given path within the configuration toml file

        new in 4.3.0
        """
        with self._lock.read_lock():
            ret = list(getitem_recursive(self._config, *path).keys())
        return ret

class CacheConfig(BaseConfig):
    _allow_direct_call: bool = True

class GlobalConfig(metaclass=Singleton):
    config_name: str = 'global'
    _register_lock: threading.Lock = threading.Lock()

    def __init__(self):
        self._configs = {}

    @classmethod
    def register(cls) -> Callable:
        """ To be used as a decorator

        Register in the config registry a new config class using its name
        """
        def inner_wrapper(wrapped_class: Type[BaseConfig]) -> Callable:
            #TODO: Check for config file compatibility here.
            if wrapped_class.config_template_path is NotImplemented or \
                    wrapped_class.config_name is NotImplemented:
                raise NotImplementedError(f'{wrapped_class} does not properly provide a valid value for '
                                          f'`config_template_path` ({wrapped_class.config_template_path}) or for '
                                          f'`config_name` ({wrapped_class.config_name})')
            config = cls()
            name = wrapped_class.config_name

            with cls._register_lock:
                if name in config._configs:
                    raise ValueError(f'Failed to register {wrapped_class.__name__}. Config {name} already registered for {config._configs[name].__class__.__name__}')

                wrapped_class._allow_direct_call = True
                config.add_config(name, wrapped_class())
                wrapped_class._allow_direct_call = False
            return wrapped_class

        return inner_wrapper

    def add_config(self, name : str, config : BaseConfig):
        self._configs[name] = config

    @cached_property
    def config_path(self):
        """Get the user config path"""
        return get_set_config_dir(user=True)

    @cached_property
    def system_config_path(self):
        """Get the system_wide config path"""
        return get_set_config_dir(user=False)

    def __str__(self):
        return ('Managing configurations for:\n'
            + '\n'.join(map(
                lambda kv: f'\t{kv[0]}: {kv[1]}',
                self._configs.items()
            ))
        )
    def __contains__(self, item):
        return item in self._configs

    def get(self, key: Union[str, Iterable[str]], default=None):
        try:
            ret = self[key]
        except KeyError:
            ret = default
        return ret

    def __call__(self, *args):
        return self[args]

    def __getitem__(self, key):
        config = self._configs
        if key == ():
            return self.to_dict()

        if isinstance(key, tuple):
            config = config[key[0]]
            key =  key[1:]
        return config[key]

    def __setitem__(self, key, value):
        config = self._configs
        if isinstance(key, tuple):
            config = config[key[0]]
            key = key[1:]
        config[key] = value

    def to_dict(self):
        return {name : config.to_dict() for name, config in self._configs.items()}

    def save(self):
        for config in self._configs.values():
            config.save()

@GlobalConfig.register()
class Config(BaseConfig):
    """Main class to deal with configuration values for PyMoDAQ"""
    config_template_path = Path(__file__).parent.joinpath('resources/config_template.toml')
    config_name = 'utils'


    def dict_to_add_to_user(self):
        """To subclass"""
        return dict(user=dict(name=USER))

    def __call__(self, *args):
        if 'backends' in args:
            try:
                return super().__call__(*args)
            except KeyError:
               args = replace_item_in_list(args, 'backends', 'backend')
        elif 'backend' in args:
            entry = super().__call__(*args)
            if not isinstance(entry, list):
                try:
                    args = replace_item_in_list(args, 'backend', 'backends')
                    return super().__call__(*args)
                except (ConfigError, KeyError):
                    return [entry]
            else:
                return entry
        elif 'debug_levels' in args:
            try:
                return super().__call__(*args)
            except KeyError:
                args = replace_item_in_list(args, 'debug_levels', 'debug_level')
        elif 'debug_level' in args:
            entry = super().__call__(*args)
            if not isinstance(entry, list):
                args = replace_item_in_list(args, 'debug_level', 'debug_levels')
                try:
                    return super().__call__(*args)
                except (KeyError, ConfigError):
                    return [entry]
            else:
                return entry
        elif 'dynamics' in args:
            try:
                return super().__call__(*args)
            except KeyError:
                args = replace_item_in_list(args, 'dynamics', 'dynamic')
        elif 'dynamic' in args:
            entry = super().__call__(*args)
            if not isinstance(entry, list):
                args = replace_item_in_list(args, 'dynamic', 'dynamics')
                try:
                    return super().__call__(*args)
                except (KeyError, ConfigError):
                    return [entry]
            else:
                return entry
        elif 'hdf5_backend' in args:
            entry = super().__call__(*args)
            if not isinstance(entry, list):
                try:
                    return super().__call__(*args)
                except (KeyError, ConfigError):
                    return [entry]                                

        return super().__call__(*args)


def _delete_config_files(config : BaseConfig):
    """
    **DO NOT USE IN PRODUCTION**

    Delete config files stored on the disk, leaving the config object
    in an **undetermined state**.

    Parameters
    ----------
    config : BaseConfig
        The config object whose files are to be deleted

    Returns
    -------

    """
    get_config_file(config.config_name, user=False).unlink(missing_ok=True)
    get_config_file(config.config_name, user=True).unlink(missing_ok=True)

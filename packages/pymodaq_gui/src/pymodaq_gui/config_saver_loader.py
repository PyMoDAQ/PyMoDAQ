from abc import abstractproperty
from collections.abc import Iterable


from typing import List, TYPE_CHECKING, Optional
from typing import Iterable as IterableType


from pymodaq_utils.config import (BaseConfig, recursive_iterable_flattening, ConfigError,
                                  get_set_config_dir)
from pymodaq_gui.parameter import Parameter

if TYPE_CHECKING:
    from pymodaq_gui.parameter import Parameter


def get_set_roi_path():
    """ creates and return the config folder path for managers files
    """
    return get_set_config_dir('roi_configs')


class ConfigSaverLoader:
    """ Allows to set Parameters values from previously saved one in a configuration file

    This plays the role of a cache for these Parameters

    Parameters
    ----------
    base_param: Parameter
        The parent Parameter whose children should be cached in the config file
    config: BaseConfig
        The Config object that will cache the Parameter values
    base_path: Iterable[str]
        an iterable of string defining a "category"
    """

    def __init__(self, base_param: 'Parameter', config: BaseConfig,
                 base_path: IterableType[str] = None):
        self.config = config
        if base_path is None:
            base_path = []
        self._base_path: List[str] = list(recursive_iterable_flattening(base_path))
        self._base_param = base_param

    @property
    def base_path(self):
        """ Get/Set the iterable of string defining a particular configuration to be loaded/saved"""
        return self._base_path

    @base_path.setter
    def base_path(self, path: IterableType[str]):
        self._base_path = list(recursive_iterable_flattening(path))

    @property
    def base_param(self):
        """ Get/Set the parent Parameter whose children should be saved in the config file"""
        return self._base_param

    @base_param.setter
    def base_param(self, param: 'Parameter'):
        self._base_param = param

    def load_config(self, param: 'Parameter' = None):
        from pymodaq_gui.parameter import utils as putils

        if param is None:
            param = self.base_param
        base_path = self.base_path[:]
        for child in putils.iter_children_params(param, []):
            if len(child.children()) == 0:  # means it is not a group parameter

                path = base_path + putils.get_param_path(child)[1:]

                try:
                    child.setValue(self.config(
                        *path))  # first try to load the config including the actuators name
                except (ConfigError, TypeError) as e:
                    pass
            else:
                self.load_config(child)

    def save_config(self, param_to_save: Optional[Parameter] = None):
        from pymodaq_gui.parameter import utils as putils

        for param in putils.iter_children_params(self.base_param, []):
            if param_to_save is None or param == param_to_save:
                path_param = self.base_path[:]
                path_param.extend(putils.get_param_path(param)[1:])
                try:
                    if 'group' not in param.opts['type']:
                        self.config[tuple(path_param)] = param.value()
                except Exception as e:
                    pass
        self.config.save()


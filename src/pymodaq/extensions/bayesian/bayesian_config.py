# -*- coding: utf-8 -*-
"""
Created the 19/11/2023

@author: Sebastien Weber
"""
from typing import List
from abc import abstractproperty
from pathlib import Path
from pymodaq.utils.config import BaseConfig, getitem_recursive, ConfigError
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.parameter import Parameter
from pymodaq.utils.daq_utils import recursive_iterable_flattening


class BayesianConfig(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = Path(__file__).parent.parent.parent.joinpath('resources/config_bayesian_template.toml')
    config_name = f"bayesian_settings"

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            dic = getitem_recursive(self._config, *key, ndepth=1, create_if_missing=True)
            if value is None:  # means the setting is a group
                value = {}
            dic[key[-1]] = value
        else:
            self._config[key] = value


class ConfigSaverLoader:
    config: abstractproperty

    def __init__(self, *args, base_param: Parameter):
        self.base_path = recursive_iterable_flattening(args)
        self.base_param = base_param

    def load_config(self):
        base_path = self.base_path[:]
        for child in putils.iter_children_params(self.base_param, []):
            if len(child.children()) == 0:  # means it is not a group parameter

                path = base_path + putils.get_param_path(child)[1:]

                try:
                    child.setValue(self.config(
                        *path))  # first try to load the config including the actuators name
                except ConfigError as e:
                    pass
            else:
                self.set_settings_values(child)

    def get_bounds_config_base_path(self) -> List[str]:
        path = [self.dashboard.preset_file, self.model_class.__class__.__name__]
        path_actuators = self.modules_manager.selected_actuators_name
        path.extend(path_actuators)
        return path

    def save_bounds_config(self):
        path = self.get_bounds_config_base_path()

        for param in putils.iter_children_params(self.base_param, []):
            path_param = path[:]
            path_param.extend(putils.get_param_path(param)[1:])
            try:
                self.config[tuple(path)] = param.value()
            except Exception as e:
                pass
        self.config.save()
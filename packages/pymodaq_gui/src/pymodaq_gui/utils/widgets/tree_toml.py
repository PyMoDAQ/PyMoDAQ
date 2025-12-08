# -*- coding: utf-8 -*-
"""
Created the 19/10/2023

@author: Sebastien Weber
"""
from typing import Union
import datetime

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import QObject

from pymodaq_gui.parameter.utils import get_param_path
from pymodaq_gui.parameter import ParameterTree, Parameter
from pymodaq_utils.config import Config, create_toml_from_dict


class TreeFromToml(QObject):
    """ Create a ParameterTree from a configuration file"""

    def __init__(self, config: Config = None, capitalize=True, start_path: Union[str, tuple[str, ...]] = ()):
        super().__init__()

        if config is None:
            config = Config()
        self._config = config
        params = [{'title': 'Config path', 'name': 'config_path', 'type': 'str',
                   'value': str(self._config.config_path),
                   'readonly': True}]

        self.start_path = (start_path,) if isinstance(start_path, str) else start_path

        #calling a config returns a dict!
        params.extend(self.dict_to_param(config(*start_path), capitalize=capitalize))

        self.settings = Parameter.create(title='settings', name='settings', type='group',
                                         children=params)
        self.settings.sigTreeStateChanged.connect(self.cache_config_change)
        self.settings_tree = ParameterTree()

        self.settings_tree.setParameters(self.settings, showTop=False)

        self._cached_config_changes = {}
        self.dialog = None

    def cache_config_change(self, _base_param, changes):
        for param, change_type, value in changes:
            if change_type == "value":
                path = tuple(get_param_path(param)[1:])
                self._cached_config_changes[path] =  value

    def commit_config_changes_cache(self):
        for path, value in self._cached_config_changes.items():
            self._config[self.start_path + path] = value
        self._config.save()

    def show_dialog(self) -> bool:

        self.dialog = QtWidgets.QDialog()
        self.dialog.setWindowTitle('Please enter new configuration values!')
        self.dialog.setLayout(QtWidgets.QVBoxLayout())
        button_box = QtWidgets.QDialogButtonBox(parent=self.dialog)

        save_button = button_box.addButton('Save', QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        save_button.setObjectName('save')
        button_box.accepted.connect(self.dialog.accept)

        cancel_button = button_box.addButton("Cancel", QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)
        cancel_button.setObjectName('cancel')
        button_box.rejected.connect(self.dialog.reject)

        self.dialog.layout().addWidget(self.settings_tree)
        self.dialog.layout().addWidget(button_box)
        self.dialog.setWindowTitle('Configuration entries')
        res = self.dialog.exec()

        if res == QtWidgets.QDialog.DialogCode.Accepted:
            self.commit_config_changes_cache()
        self._cached_config_changes = {}
        return bool(res)

    @classmethod
    def param_to_dict(cls, param: Parameter) -> dict:
        config = dict()
        for child in param.children():
            if 'group' in child.opts['type']:
                config[child.name()] = cls.param_to_dict(child)
            else:
                if child.opts['type'] == 'datetime':
                    config[child.name()] = datetime.datetime.fromtimestamp(
                        child.value().toSecsSinceEpoch())  # convert QDateTime to python datetime
                elif child.opts['type'] == 'date':
                    qdt = QtCore.QDateTime()
                    qdt.setDate(child.value())
                    pdt = datetime.datetime.fromtimestamp(qdt.toSecsSinceEpoch())
                    config[child.name()] = pdt.date()
                elif child.opts['type'] == 'list':
                    if child.opts['value'] in child.opts['limits']:
                        child.opts["limits"].remove(child.opts['value'])
                        child.opts["limits"].insert(0,child.opts["value"])
                    config[child.name()] = child.opts["limits"]
                else:
                    config[child.name()] = child.value()
        return config

    @classmethod
    def dict_to_param(cls, config: dict, capitalize=True) -> Parameter:
        params = []
        for key in config:
            if isinstance(config[key], dict):
                params.append({'title': f'{key.capitalize() if capitalize else key}:',
                               'name': key, 'type': 'group',
                               'children': cls.dict_to_param(config[key], capitalize=capitalize),
                               'expanded': 'user' in key.lower() or 'general' in key.lower()})
            else:
                param = {'title': f'{key.capitalize() if capitalize else key}:',
                         'name': key, 'value': config[key]}
                if isinstance(config[key], float):
                    param['type'] = 'float'
                elif isinstance(config[key], bool):  # placed before int because a bool is an instance of int
                    param['type'] = 'bool'
                elif isinstance(config[key], int):
                    param['type'] = 'int'
                elif isinstance(config[key], datetime.datetime):
                    param['type'] = 'datetime'
                elif isinstance(config[key], datetime.date):
                    param['type'] = 'date'
                elif isinstance(config[key], str):
                    param['type'] = 'str'
                elif isinstance(config[key], list):
                    param['type'] = 'list'
                    param['limits'] = config[key]
                    param['value'] = config[key][0]
                    # param['show_pb'] = True # If True, this allows the user to change the limits in the list from the GUI. No need for now.
                params.append(param)
        return params

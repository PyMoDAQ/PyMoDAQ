# -*- coding: utf-8 -*-
"""
Created the 19/10/2023

@author: Sebastien Weber
"""
import datetime

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import QObject

from pymodaq_gui.parameter import ParameterTree, Parameter
from pymodaq_utils.config import Config, create_toml_from_dict


class TreeFromToml(QObject):
    """ Create a ParameterTree from a configuration file"""

    def __init__(self, config: Config = None, capitalize=True):
        super().__init__()

        if config is None:
            config = Config()
        self._config = config
        params = [{'title': 'Config path', 'name': 'config_path', 'type': 'str',
                   'value': str(self._config.config_path),
                   'readonly': True}]
        params.extend(self.dict_to_param(config.to_dict(), capitalize=capitalize))

        self.settings = Parameter.create(title='settings', name='settings', type='group',
                                         children=params)
        self.settings_tree = ParameterTree()
        self.settings_tree.setParameters(self.settings, showTop=False)

    def show_dialog(self) -> bool:

        self.dialog = QtWidgets.QDialog()
        self.dialog.setWindowTitle('Please enter new configuration values!')
        self.dialog.setLayout(QtWidgets.QVBoxLayout())
        buttonBox = QtWidgets.QDialogButtonBox(parent=self.dialog)

        buttonBox.addButton('Save', buttonBox.AcceptRole)
        buttonBox.accepted.connect(self.dialog.accept)
        buttonBox.addButton('Cancel', buttonBox.RejectRole)
        buttonBox.rejected.connect(self.dialog.reject)

        self.dialog.layout().addWidget(self.settings_tree)
        self.dialog.layout().addWidget(buttonBox)
        self.dialog.setWindowTitle('Configuration entries')
        res = self.dialog.exec()

        if res == self.dialog.Accepted:
            with open(self._config.config_path, 'w') as f:
                config_dict = self.param_to_dict(self.settings)
                config_dict.pop('config_path')
                create_toml_from_dict(config_dict, self._config.config_path)
        return res

    @classmethod
    def param_to_dict(cls, param: Parameter) -> dict:
        config = dict()
        for child in param.children():
            if 'group' in child.opts['type']:
                config[child.name()] = cls.param_to_dict(child)
            else:
                if child.opts['type'] == 'datetime':
                    config[child.name()] = datetime.fromtimestamp(
                        child.value().toSecsSinceEpoch())  # convert QDateTime to python datetime
                elif child.opts['type'] == 'date':
                    qdt = QtCore.QDateTime()
                    qdt.setDate(child.value())
                    pdt = datetime.fromtimestamp(qdt.toSecsSinceEpoch())
                    config[child.name()] = pdt.date()
                elif child.opts['type'] == 'list':
                    config[child.name()] = child.opts['limits']
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
                    param['show_pb'] = True
                params.append(param)
        return params

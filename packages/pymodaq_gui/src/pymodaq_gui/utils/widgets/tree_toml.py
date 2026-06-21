# -*- coding: utf-8 -*-
"""
Created the 19/10/2023

@author: Sebastien Weber
"""
import contextlib
import sys
from typing import Union, Any
import datetime

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import QObject, QSignalBlocker

from pymodaq_gui.parameter.utils import get_param_path
from pymodaq_gui.parameter import ParameterTree, Parameter
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.qt_utils import mkQApp
from pymodaq_utils.config import GlobalConfig as Config, create_toml_from_dict
from pymodaq_utils.utils import format_dir_path


class TreeFromToml(ParameterManager, QObject):
    """ Create a ParameterTree from a configuration file"""
    settings_name = 'configuration'
    params = [{'title': 'Config path', 'name': 'config_path', 'type': 'str',
               'value': '', 'readonly': True}]

    def __init__(self, config: Config = None, capitalize=True, start_path: Union[str, tuple[str, ...]] = ()):
        QObject.__init__(self)
        ParameterManager.__init__(self)

        if config is None:
            config = Config()
        self._config = config

        self.start_path = (start_path,) if isinstance(start_path, str) else start_path

        with QSignalBlocker(self.settings):
            self.settings.child('config_path').setValue(format_dir_path(self._config.config_path))
        self.settings.addChildren(self.dict_to_param(config(*start_path), capitalize=capitalize))

        self._cached_config_changes = {}
        self.dialog = None
        self._post_process_params()

    def _post_process_params(self):
        """For every list param named 'backend': expand limits from the template (so the full
        list of known backends is always shown) and grey out items not installed."""
        import pkgutil
        import toml
        from pathlib import Path
        from pymodaq_utils.config import GlobalConfig, BaseConfig

        installed_lower = {mod.name.lower() for mod in pkgutil.iter_modules()}

        # Some backend names are not pip package names; map them to their actual package.
        _backend_pkg_alias = {'qt': 'qtpy'}

        def _backend_available(name: str) -> bool:
            pkg = _backend_pkg_alias.get(name.lower(), name.lower())
            return pkg in installed_lower

        def annotate(param_group, template_dict):
            for child in param_group.children():
                key = child.name()
                tval = template_dict.get(key) if isinstance(template_dict, dict) else None
                if child.opts.get('type') == 'list' and key == 'backend':
                    current = list(child.opts.get('limits', []))
                    full = list(tval) if isinstance(tval, list) else list(current)
                    for item in current:  # keep any user-added entries not in template
                        if item not in full:
                            full.append(item)
                    unavailable = [x for x in full if isinstance(x, str)
                                   and not _backend_available(x)]
                    update = {'unavailable': unavailable}
                    if full != current:
                        update['limits'] = full
                    child.setOpts(**update)
                elif child.hasChildren():
                    annotate(child, tval if isinstance(tval, dict) else {})

        # Resolve (param_root, template) pairs so both start at the same nesting level
        if isinstance(self._config, GlobalConfig):
            for cfg_name, cfg in self._config._configs.items():
                tpath = getattr(cfg, 'config_template_path', None)
                if not (tpath and Path(tpath).is_file()):
                    continue
                template = toml.load(tpath)
                if self.start_path and self.start_path[0] == cfg_name:
                    for k in self.start_path[1:]:
                        template = template.get(k, {})
                    annotate(self.settings, template)
                elif not self.start_path:
                    with contextlib.suppress(Exception):
                        annotate(self.settings.child(cfg_name), template)
        elif isinstance(self._config, BaseConfig):
            tpath = getattr(self._config, 'config_template_path', None)
            if tpath and Path(tpath).is_file():
                template = toml.load(tpath)
                for k in self.start_path:
                    template = template.get(k, {})
                annotate(self.settings, template)

    def value_changed(self, param):
        path = tuple(get_param_path(param)[1:])
        self._cached_config_changes[path] = self.param_to_object(param)

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
        self.dialog.setWindowTitle('Preferences entries')
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
                config[child.name()] = cls.param_to_object(child)
        return config

    @classmethod
    def param_to_object(cls, param: Parameter) -> Any:
        """ Format the value of the Parameter depending on internal need """
        if param.opts['type'] == 'datetime':
            return datetime.datetime.fromtimestamp(
                param.value().toSecsSinceEpoch())  # convert QDateTime to python datetime
        elif param.opts['type'] == 'date':
            qdt = QtCore.QDateTime()
            qdt.setDate(param.value())
            pdt = datetime.datetime.fromtimestamp(qdt.toSecsSinceEpoch())
            return pdt.date()
        elif param.opts['type'] == 'list':
            if param.opts['value'] in param.opts['limits']:
                param.opts["limits"].remove(param.opts['value'])
                param.opts["limits"].insert(0, param.opts["value"])
            return param.opts["limits"]
        else:
            return param.value()

    @classmethod
    def dict_to_param(cls, config: dict, capitalize=True) -> list[Parameter]:
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


if __name__ == '__main__':
    app = mkQApp("TreeToml")
    tree_toml = TreeFromToml()
    tree_toml.show_dialog()
    sys.exit(app.exec())
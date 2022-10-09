import datetime
from pathlib import Path
import toml
from qtpy.QtCore import QObject
from pymodaq.daq_utils.messenger import messagebox
from pyqtgraph.parametertree import Parameter, ParameterTree
from qtpy import QtWidgets, QtCore


def getitem_recursive(dic, *args):
    args = list(args)
    while len(args) > 0:
        dic = dic[args.pop(0)]
    return dic


def get_set_local_dir(basename='pymodaq_local'):
    """Defines, creates abd returns a local folder where configurations files will be saved

    Parameters
    ----------
    basename: (str) how the configuration folder will be named

    Returns
    -------
    Path: the local path
    """
    local_path = Path.home().joinpath(basename)

    if not local_path.is_dir():                            # pragma: no cover
        try:
            local_path.mkdir()
        except Exception as e:
            local_path = Path(__file__).parent.parent.joinpath(basename)
            info = f"Cannot create local folder from your **Home** defined location: {Path.home()}," \
                   f" using PyMoDAQ's folder as local directory: {local_path}"
            print(info)
            if not local_path.is_dir():
                local_path.mkdir()
    return local_path


def get_set_config_path(config_name='config'):
    """Creates a folder in the local config directory to store specific configuration files

    Parameters
    ----------
    config_name: (str) name of the configuration folder

    Returns
    -------

    See Also
    --------
    get_set_local_dir
    """
    local_path = get_set_local_dir()
    path = local_path.joinpath(config_name)
    if not path.is_dir():
        path.mkdir()  # pragma: no cover
    return path


def get_set_log_path():
    """ creates and return the config folder path for log files
    """
    return get_set_config_path('log')


def get_set_preset_path():
    """ creates and return the config folder path for managers files
    """
    return get_set_config_path('preset_configs')


def get_set_batch_path():
    """ creates and return the config folder path for managers files
    """
    return get_set_config_path('batch_configs')


def get_set_pid_path():
    """ creates and return the config folder path for PID files
    """
    return get_set_config_path('pid_configs')


def get_set_layout_path():
    """ creates and return the config folder path for layout files
    """
    return get_set_config_path('layout_configs')


def get_set_remote_path():
    """ creates and return the config folder path for remote (shortcuts or joystick) files
    """
    return get_set_config_path('remote_configs')


def get_set_overshoot_path():
    """ creates and return the config folder path for overshoot files
    """
    return get_set_config_path('overshoot_configs')


def get_set_roi_path():
    """ creates and return the config folder path for managers files
    """
    return get_set_config_path('roi_configs')


def load_config(config_path=None, config_base_path=None):
    if not config_path:
        config_path = get_set_local_dir().joinpath('config.toml')
    if not config_base_path:
        config_base = toml.load(Path(__file__).parent.parent.joinpath('resources/config_template.toml'))
    else:
        config_base = toml.load(config_base_path)
    if not config_path.exists():  # copy the template from pymodaq folder and create one in pymodad's local folder
        config_path.write_text(toml.dumps(config_base))

    # check if all fields are there
    config = toml.load(config_path)
    if check_config(config_base, config):
        config_path.write_text(toml.dumps(config))
        config = config_base
    return config


class ConfigError(Exception):
    pass


class Config:
    def __init__(self, config_path=None, config_base_path=None):
        self._config = load_config(config_path, config_base_path)
        self.config_path = config_path
        self.config_base_path = config_base_path

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
        return self._config[item]


def set_config(config_as_dict, config_path=None):
    if not config_path:
        config_path = get_set_local_dir().joinpath('config.toml')

    config_path.write_text(toml.dumps(config_as_dict))


def check_config(config_base, config_local):
    status = False
    for key in config_base:
        if key in config_local:
            if isinstance(config_base[key], dict):
                status = status or check_config(config_base[key], config_local[key])
        else:
            config_local[key] = config_base[key]
            status = True
    return status


class TreeFromToml(QObject):
    def __init__(self, config=None, conf_path=None, config_base_path=None):
        super().__init__()
        if config is None:
            if conf_path is None:
                config_path = get_set_local_dir().joinpath('config.toml')
            else:
                config_path = conf_path
            config = Config(config_path, config_base_path)
        self.config_path = config_path
        params = [{'title': 'Config path', 'name': 'config_path', 'type': 'str', 'value': str(config.config_path),
                   'readonly': True}]
        params.extend(self.dict_to_param(config.to_dict()))

        self.settings = Parameter.create(title='settings', name='settings', type='group', children=params)
        self.settings_tree = ParameterTree()
        self.settings_tree.setParameters(self.settings, showTop=False)

    def show_dialog(self):

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
            with open(self.config_path, 'w') as f:
                config = self.param_to_dict(self.settings)
                config.pop('config_path')
                toml.dump(config, f)

    @classmethod
    def param_to_dict(cls, param):
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
    def dict_to_param(cls, config):
        params = []
        for key in config:
            if isinstance(config[key], dict):
                params.append({'title': f'{key.capitalize()}:', 'name': key, 'type': 'group',
                               'children': cls.dict_to_param(config[key]),
                               'expanded': 'user' in key.lower() or 'general' in key.lower()})
            else:
                param = {'title': f'{key.capitalize()}:', 'name': key, 'value': config[key]}
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
                    param['values'] = config[key]
                    param['value'] = config[key][0]
                    param['show_pb'] = True
                params.append(param)
        return params

    
if __name__ == '__main__':
    config = load_config()
    config = Config()
    config('style', 'darkstyle')
    assert config('style', 'darkstyle') == config['style']['darkstyle']


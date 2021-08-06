from PyQt5 import QtCore
from PyQt5.QtCore import QVariant
import sys
from packaging import version as version_mod

python_version = f'{str(sys.version_info.major)}.{str(sys.version_info.minor)}'
if version_mod.parse(python_version) >= version_mod.parse('3.8'):  # from version 3.8 this feature is included in the
    # standard lib
    from importlib import metadata
else:
    import importlib_metadata as metadata  # pragma: no cover
import pkgutil

import traceback
from collections import OrderedDict

import numpy as np
import datetime
from pathlib import Path
from ctypes import CFUNCTYPE

if 'win32' in sys.platform:
    from ctypes import WINFUNCTYPE

import enum
import os

import importlib
import toml
import logging
from logging.handlers import TimedRotatingFileHandler
import inspect
import json

plot_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (14, 207, 189), (207, 14, 166), (207, 204, 14)]

Cb = 1.602176e-19  # coulomb
h = 6.626068e-34  # J.s
c = 2.997924586e8  # m.s-1


def get_version():
    with open(str(Path(__file__).parent.parent.joinpath('resources/VERSION')), 'r') as fvers:
        version = fvers.read().strip()
    return version


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


def copy_preset():                          # pragma: no cover
    path = get_set_preset_path().joinpath('preset_default.xml')
    if not path.exists():  # copy the preset_default from pymodaq folder and create one in pymodad's local folder
        with open(str(Path(__file__).parent.parent.joinpath('resources/preset_default.xml')), 'r') as file:
            path.write_text(file.read())


def load_config(config_path=None):          # pragma: no cover
    if not config_path:
        config_path = get_set_local_dir().joinpath('config.toml')
    config_base = toml.load(Path(__file__).parent.parent.joinpath('resources/config_template.toml'))
    if not config_path.exists():  # copy the template from pymodaq folder and create one in pymodad's local folder
        config_path.write_text(toml.dumps(config_base))

    # check if all fields are there
    config = toml.load(config_path)
    if check_config(config_base, config):
        config_path.write_text(toml.dumps(config))
    return config


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


config = load_config()


class JsonConverter:
    def __init__(self):
        super().__init__()

    @classmethod
    def trusted_types(cls):
        return ['float', 'int', 'str', 'datetime', 'date', 'time', 'tuple', 'list', 'bool', 'bytes']

    @classmethod
    def istrusted(cls, type_name):
        return type_name in cls.trusted_types()

    @classmethod
    def object2json(cls, obj):
        dic = dict(module=type(obj).__module__, type=type(obj).__name__, data=repr(obj))
        return json.dumps(dic)

    @classmethod
    def json2object(cls, jsonstring):
        try:
            dic = json.loads(jsonstring)
            if isinstance(dic, dict):
                if dic['type'] in cls.trusted_types():
                    return eval(dic['data'])
                else:
                    return dic
            else:                                               # pragma: no cover
                return dic
        except Exception:
            return jsonstring


def decode_data(encoded_data):
    """
    Decode QbyteArrayData generated when drop items in table/tree/list view
    Parameters
    ----------
    encoded_data: QByteArray
                    Encoded data of the mime data to be dropped
    Returns
    -------
    data: list
            list of dict whose key is the QtRole in the Model, and the value a QVariant

    """
    data = []

    ds = QtCore.QDataStream(encoded_data, QtCore.QIODevice.ReadOnly)
    while not ds.atEnd():
        row = ds.readInt32()
        col = ds.readInt32()

        map_items = ds.readInt32()
        item = {}
        for ind in range(map_items):
            key = ds.readInt32()
            value = QVariant()
            ds >> value
            item[QtCore.Qt.ItemDataRole(key)] = value.value()
        data.append(item)
    return data


# ###################################
# # Units conversion
def Enm2cmrel(E_nm, ref_wavelength=515):
    """Converts energy in nm to cm-1 relative to a ref wavelength

    Parameters
    ----------
    E_nm: float
          photon energy in wavelength (nm)
    ref_wavelength: float
                    reference wavelength in nm from which calculate the photon relative energy

    Returns
    -------
    float
         photon energy in cm-1 relative to the ref wavelength

    Examples
    --------
    >>> Enm2cmrel(530, 515)
    549.551199853453
    """
    return 1 / (ref_wavelength * 1e-7) - 1 / (E_nm * 1e-7)


def Ecmrel2Enm(Ecmrel, ref_wavelength=515):
    """Converts energy from cm-1 relative to a ref wavelength to an energy in wavelength (nm)

    Parameters
    ----------
    Ecmrel: float
            photon energy in cm-1
    ref_wavelength: float
                    reference wavelength in nm from which calculate the photon relative energy

    Returns
    -------
    float
         photon energy in nm

    Examples
    --------
    >>> Ecmrel2Enm(500, 515)
    528.6117526302285
    """
    Ecm = 1 / (ref_wavelength * 1e-7) - Ecmrel
    return 1 / (Ecm * 1e-7)


def eV2nm(E_eV):
    """Converts photon energy from electronvolt to wavelength in nm

    Parameters
    ----------
    E_eV: float
          Photon energy in eV

    Returns
    -------
    float
         photon energy in nm

    Examples
    --------
    >>> eV2nm(1.55)
    799.898112990037
    """
    E_J = E_eV * Cb
    E_freq = E_J / h
    E_nm = c / E_freq * 1e9
    return E_nm


def nm2eV(E_nm):
    """Converts photon energy from wavelength in nm to electronvolt

    Parameters
    ----------
    E_nm: float
          Photon energy in nm

    Returns
    -------
    float
         photon energy in eV

    Examples
    --------
    >>> nm2eV(800)
    1.549802593918197
    """
    E_freq = c / E_nm * 1e9
    E_J = E_freq * h
    E_eV = E_J / Cb
    return E_eV


def E_J2eV(E_J):
    E_eV = E_J / Cb
    return E_eV


def eV2cm(E_eV):
    """Converts photon energy from electronvolt to absolute cm-1

    Parameters
    ----------
    E_eV: float
          Photon energy in eV

    Returns
    -------
    float
         photon energy in cm-1

    Examples
    --------
    >>> eV2cm(0.07)
    564.5880342655984
    """
    E_nm = eV2nm(E_eV)
    E_cm = 1 / (E_nm * 1e-7)
    return E_cm


def nm2cm(E_nm):
    """Converts photon energy from wavelength to absolute cm-1

        Parameters
        ----------
        E_nm: float
              Photon energy in nm

        Returns
        -------
        float
             photon energy in cm-1

        Examples
        --------
        >>> nm2cm(0.04)
        0.000025
        """
    return 1 / (E_nm * 1e7)


def cm2nm(E_cm):
    """Converts photon energy from absolute cm-1 to wavelength

            Parameters
            ----------
            E_cm: float
                  photon energy in cm-1

            Returns
            -------
            float
                 Photon energy in nm

            Examples
            --------
            >>> cm2nm(1e5)
            100
            """
    return 1 / (E_cm * 1e-7)


def eV2E_J(E_eV):
    E_J = E_eV * Cb
    return E_J


def eV2radfs(E_eV):
    E_J = E_eV * Cb
    E_freq = E_J / h
    E_radfs = E_freq * 2 * np.pi / 1e15
    return E_radfs


def l2w(x, speedlight=300):
    """Converts photon energy in rad/fs to nm (and vice-versa)

    Parameters
    ----------
    x: float
       photon energy in wavelength or rad/fs
    speedlight: float, optional
                the speed of light, by default 300 nm/fs

    Returns
    -------
    float

    Examples
    --------
    >>> l2w(800)
    2.356194490192345
    >>> l2w(800,3e8)
    2356194.490192345
    """
    y = 2 * np.pi * speedlight / x
    return y


#############################

def capitalize(string, Nfirst=1):
    """
    Returns same string but with first Nfirst letters upper
    Parameters
    ----------
    string: (str)
    Nfirst: (int)
    Returns
    -------
    str
    """
    return string[:Nfirst].upper() + string[Nfirst:]


def uncapitalize(string, Nfirst=1):
    return string[:Nfirst].lower() + string[Nfirst:]


def get_data_dimension(arr, scan_type='scan1D', remove_scan_dimension=False):
    dimension = len(arr.shape)
    if dimension == 1:
        if arr.size == 1:
            dimension = 0

    if remove_scan_dimension:
        if scan_type.lower() == 'scan1d':
            dimension -= 1
        elif scan_type.lower() == 'scan2d':
            dimension -= 2
    else:
        if dimension > 2:
            dimension = 'N'
    return arr.shape, f'{dimension}D', arr.size


def scroll_log(scroll_val, min_val, max_val):
    """
    Convert a scroll value [0-100] to a log scale between min_val and max_val
    Parameters
    ----------
    scroll
    min_val
    max_val
    Returns
    -------

    """
    assert scroll_val >= 0
    assert scroll_val <= 100
    value = scroll_val * (np.log10(max_val) - np.log10(min_val)) / 100 + np.log10(min_val)
    return 10 ** value


def scroll_linear(scroll_val, min_val, max_val):
    """
    Convert a scroll value [0-100] to a linear scale between min_val and max_val
    Parameters
    ----------
    scroll
    min_val
    max_val
    Returns
    -------

    """
    assert scroll_val >= 0
    assert scroll_val <= 100
    value = scroll_val * (max_val - min_val) / 100 + min_val
    return value


def getLineInfo():
    """get information about where the Exception has been triggered"""
    tb = sys.exc_info()[2]
    res = ''
    for t in traceback.format_tb(tb):
        res += t
    return res


class ThreadCommand(object):
    """ | Micro class managing the thread commands.
        |
        | A thread command is composed of a string name defining the command to execute and an attribute list splitable making arguments of the called function.

        =============== =============
        **Attributes**  **Type**
        *command*       string
        *attributes*    generic list
        =============== =============

    """

    def __init__(self, command="", attributes=[]):
        self.command = command
        self.attributes = attributes


class Axis(dict):
    """
    Utility class defining an axis for pymodaq's viewers, attributes can be accessed as dictionary keys
    """

    def __init__(self, data=None, label='', units='', **kwargs):
        """

        Parameters
        ----------
        data
        label
        units
        """
        if units is None:
            units = ''
        if label is None:
            label = ''

        if data is None or isinstance(data, np.ndarray):
            self['data'] = data
        else:
            raise TypeError('data for the Axis class should be a ndarray')
        if not isinstance(label, str):
            raise TypeError('label for the Axis class should be a string')
        self['label'] = label
        if not isinstance(units, str):
            raise TypeError('units for the Axis class should be a string')
        self['units'] = units
        self.update(kwargs)


class NavAxis(Axis):
    def __init__(self, data=None, label='', units='', nav_index=-1, **kwargs):
        super().__init__(data=data, label=label, units=units, **kwargs)

        if nav_index < 0:
            raise ValueError('nav_index should be a positive integer representing the index of this axis among all'
                             'navigation axes')
        self['nav_index'] = nav_index


class Data(OrderedDict):
    def __init__(self, name='', source='raw', distribution='uniform', x_axis=Axis(), y_axis=Axis(), **kwargs):
        """
        Generic class subclassing from OrderedDict defining data being exported from pymodaq's plugin or viewers,
        attributes can be accessed as dictionary keys. Should be subclassed from for real datas
        Parameters
        ----------
        source: (str) either 'raw' or 'roi...' if straight from a plugin or data processed within a viewer
        distribution: (str) either 'uniform' or 'spread'
        x_axis: (Axis) Axis class defining the corresponding axis (with data either linearly spaced or containing the
         x positions of the spread points)
        y_axis: (Axis) Axis class defining the corresponding axis (with data either linearly spaced or containing the
         x positions of the spread points)
        """

        if not isinstance(name, str):
            raise TypeError('name for the DataToExport class should be a string')
        self['name'] = name
        if not isinstance(source, str):
            raise TypeError('source for the DataToExport class should be a string')
        elif not ('raw' in source or 'roi' in source):
            raise ValueError('Invalid "source" for the DataToExport class')
        self['source'] = source

        if not isinstance(distribution, str):
            raise TypeError('distribution for the DataToExport class should be a string')
        elif distribution not in ('uniform', 'spread'):
            raise ValueError('Invalid "distribution" for the DataToExport class')
        self['distribution'] = distribution

        if not isinstance(x_axis, Axis):
            if isinstance(x_axis, np.ndarray):
                x_axis = Axis(data=x_axis)
            else:
                raise TypeError('x_axis for the DataToExport class should be a Axis class')
            self['x_axis'] = x_axis
        elif x_axis['data'] is not None:
            self['x_axis'] = x_axis

        if not isinstance(y_axis, Axis):
            if isinstance(y_axis, np.ndarray):
                y_axis = Axis(data=y_axis)
            else:
                raise TypeError('y_axis for the DataToExport class should be a Axis class')
            self['y_axis'] = y_axis
        elif y_axis['data'] is not None:
            self['y_axis'] = y_axis

        for k in kwargs:
            self[k] = kwargs[k]


class DataFromPlugins(Data):

    def __init__(self, data=None, dim='', labels=[], nav_axes=[], nav_x_axis=Axis(), nav_y_axis=Axis(), **kwargs):
        """
        Parameters
        ----------
        dim: (str) data dimensionality (either Data0D, Data1D, Data2D or DataND)


        """
        super().__init__(**kwargs)
        self['labels'] = labels
        if len(nav_axes) != 0:
            self['nav_axes'] = nav_axes
        if nav_x_axis['data'] is not None:
            self['nav_x_axis'] = nav_x_axis
        if nav_y_axis['data'] is not None:
            self['nav_y_axis'] = nav_y_axis

        iscorrect = True
        if data is not None:
            if isinstance(data, list):
                for dat in data:
                    if not isinstance(dat, np.ndarray):
                        iscorrect = False
            else:
                iscorrect = False

        if iscorrect:
            self['data'] = data
        else:
            raise TypeError('data for the DataFromPlugins class should be None or a list of numpy arrays')

        if dim not in ('Data0D', 'Data1D', 'Data2D', 'DataND') and data is not None:
            ndim = len(data[0].shape)
            if ndim == 1:
                if data[0].size == 1:
                    dim = 'Data0D'
                else:
                    dim = 'Data1D'
            elif ndim == 2:
                dim = 'Data2D'
            else:
                dim = 'DataND'
        self['dim'] = dim


class DataToExport(Data):
    def __init__(self, data=None, dim='', **kwargs):
        """
        Utility class defining a data being exported from pymodaq's viewers, attributes can be accessed as dictionary keys
        Parameters
        ----------
        data: (ndarray or a scalar)
        dim: (str) data dimensionality (either Data0D, Data1D, Data2D or DataND)
        """
        super().__init__(**kwargs)
        if data is None or isinstance(data, np.ndarray) or isinstance(data, float) or isinstance(data, int):
            self['data'] = data
        else:
            raise TypeError('data for the DataToExport class should be a scalar or a ndarray')

        if dim not in ('Data0D', 'Data1D', 'Data2D', 'DataND') or data is not None:
            if isinstance(data, np.ndarray):
                ndim = len(data.shape)
                if ndim == 1:
                    if data.size == 1:
                        dim = 'Data0D'
                    else:
                        dim = 'Data1D'
                elif ndim == 2:
                    dim = 'Data2D'
                else:
                    dim = 'DataND'
            else:
                dim = 'Data0D'
        self['dim'] = dim


class ScaledAxis(Axis):
    def __init__(self, label='', units='', offset=0, scaling=1):
        super().__init__(label=label, units=units)
        if not (isinstance(offset, float) or isinstance(offset, int)):
            raise TypeError('offset for the ScalingAxis class should be a float (or int)')
        self['offset'] = offset
        if not (isinstance(scaling, float) or isinstance(scaling, int)):
            raise TypeError('scaling for the ScalingAxis class should be a non null float (or int)')
        if scaling == 0 or scaling == 0.:
            raise ValueError('scaling for the ScalingAxis class should be a non null float (or int)')
        self['scaling'] = scaling


class ScalingOptions(dict):
    def __init__(self, scaled_xaxis=ScaledAxis(), scaled_yaxis=ScaledAxis()):
        assert isinstance(scaled_xaxis, ScaledAxis)
        assert isinstance(scaled_yaxis, ScaledAxis)
        self['scaled_xaxis'] = scaled_xaxis
        self['scaled_yaxis'] = scaled_yaxis


def recursive_find_files_extension(ini_path, ext, paths=[]):
    with os.scandir(ini_path) as it:
        for entry in it:
            if os.path.splitext(entry.name)[1][1:] == ext and entry.is_file():
                paths.append(entry.path)
            elif entry.is_dir():
                recursive_find_files_extension(entry.path, ext, paths)
    return paths


def recursive_find_expr_in_files(ini_path, exp='make_enum', paths=[],
                                 filters=['.git', '.idea', '__pycache__', 'build', 'egg', 'documentation', '.tox']):
    for child in Path(ini_path).iterdir():
        if not any(filt in str(child) for filt in filters):
            if child.is_dir():
                recursive_find_expr_in_files(child, exp, paths, filters)
            else:
                try:
                    with child.open('r') as f:
                        for ind, line in enumerate(f.readlines()):
                            if exp in line:
                                paths.append([child, ind])
                except Exception:
                    pass
    return paths


def remove_spaces(string):
    """
    return a string without any white spaces in it
    Parameters
    ----------
    string

    Returns
    -------

    """
    return ''.join(string.split())


def rint(x):
    """
    almost same as numpy rint function but return an integer
    Parameters
    ----------
    x: (float or integer)

    Returns
    -------
    nearest integer
    """
    return int(np.rint(x))


def elt_as_first_element(elt_list, match_word='Mock'):
    if not hasattr(elt_list, '__iter__'):
        raise TypeError('elt_list must be an iterable')
    if elt_list:
        ind_elt = 0
        for ind, elt in enumerate(elt_list):
            if not isinstance(elt, str):
                raise TypeError('elt_list must be a list of str')
            if match_word in elt:
                ind_elt = ind
                break
        plugin_match = elt_list[ind_elt]
        elt_list.remove(plugin_match)
        plugins = [plugin_match]
        plugins.extend(elt_list)
    else:
        plugins = []
    return plugins


def elt_as_first_element_dicts(elt_list, match_word='Mock', key='name'):
    if not hasattr(elt_list, '__iter__'):
        raise TypeError('elt_list must be an iterable')
    if elt_list:
        ind_elt = 0
        for ind, elt in enumerate(elt_list):
            if not isinstance(elt, dict):
                raise TypeError('elt_list must be a list of dicts')
            if match_word in elt[key]:
                ind_elt = ind
                break
        plugin_match = elt_list[ind_elt]
        elt_list.remove(plugin_match)
        plugins = [plugin_match]
        plugins.extend(elt_list)
    else:
        plugins = []
    return plugins


def get_plugins(plugin_type='daq_0Dviewer'):  # pragma: no cover
    """
    Get plugins names as a list
    Parameters
    ----------
    plugin_type: (str) plugin type either 'daq_0Dviewer', 'daq_1Dviewer', 'daq_2Dviewer', 'daq_NDviewer' or 'daq_move'
    module: (module) parent module of the plugins

    Returns
    -------

    """
    plugins_import = []
    discovered_plugins = metadata.entry_points()['pymodaq.plugins']

    for module in discovered_plugins:
        try:
            if plugin_type == 'daq_move':
                submodule = importlib.import_module(f'{module.value}.daq_move_plugins', module.value)
            else:
                submodule = importlib.import_module(f'{module.value}.daq_viewer_plugins.plugins_{plugin_type[4:6]}',
                                                    module.value)
            plugin_list = [{'name': mod[len(plugin_type) + 1:],
                            'module': submodule} for mod in [mod[1] for
                                                             mod in pkgutil.iter_modules([submodule.path.parent])]
                           if plugin_type in mod]
            # check if modules are importable

            for mod in plugin_list:
                try:
                    if plugin_type == 'daq_move':
                        importlib.import_module(f'{submodule.__package__}.daq_move_{mod["name"]}')
                    else:
                        importlib.import_module(f'{submodule.__package__}.daq_{plugin_type[4:6]}viewer_{mod["name"]}')
                    plugins_import.append(mod)
                except Exception:  # pragma: no cover
                    pass
        except Exception:  # pragma: no cover
            pass
    plugins_import = elt_as_first_element_dicts(plugins_import, match_word='Mock', key='name')
    return plugins_import


def check_vals_in_iterable(iterable1, iterable2):
    assert len(iterable1) == len(iterable2)
    iterable1 = list(iterable1)  # so the assertion below is valid for any kind of iterable, list, tuple, ndarray...
    iterable2 = list(iterable2)
    for val1, val2 in zip(iterable1, iterable2):
        assert val1 == val2


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


def get_set_log_path():
    """ creates and return the config folder path for log files
    """
    return get_set_config_path('log')


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


def get_module_name(module__file__path):
    """from the full path of a module extract its name"""
    path = Path(module__file__path)
    return path.stem


def set_logger(logger_name, add_handler=False, base_logger=False, add_to_console=False, log_level=None):
    """defines a logger of a given name and eventually add an handler to it

    Parameters
    ----------
    logger_name: (str) the name of the logger (usually it is the module name as returned by get_module_name
    add_handler (bool) if True adds a TimedRotatingFileHandler to the logger instance (should be True if logger set from
                main app
    base_logger: (bool) specify if this is the parent logger (usually where one defines the handler)

    Returns
    -------
    logger: (logging.logger) logger instance
    See Also
    --------
    get_module_name, logging.handlers.TimedRotatingFileHandler
    """
    if not base_logger:
        logger_name = f'pymodaq.{logger_name}'

    logger = logging.getLogger(logger_name)
    log_path = get_set_config_path('log')
    if add_handler:
        if log_level is None:
            config = load_config()
            log_level = config['general']['debug_level']
        logger.setLevel(log_level)
        handler = TimedRotatingFileHandler(log_path.joinpath('pymodaq.log'), when='midnight')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    if add_to_console:
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger


def caller_name(skip=2):
    """Get a name of a caller in the format module.class.method

       `skip` specifies how many levels of stack to skip while getting caller
       name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.

       An empty string is returned if skipped levels exceed stack height
    """
    stack = inspect.stack()
    start = 0 + skip
    if len(stack) < start + 1:
        return ''
    parentframe = stack[start][0]

    name = []
    module = inspect.getmodule(parentframe)
    # `modname` can be None when frame is executed directly in console
    # TODO(techtonik): consider using __main__
    if module:
        name.append(module.__name__)
    # detect classname
    if 'self' in parentframe.f_locals:
        # I don't know any way to detect call from the object method
        # XXX: there seems to be no way to detect static method call - it will
        #      be just a function call
        name.append(parentframe.f_locals['self'].__class__.__name__)
    codename = parentframe.f_code.co_name
    if codename != '<module>':  # top level usually
        name.append(codename)  # function or a method
    del parentframe
    return ".".join(name)


def zeros_aligned(n, align, dtype=np.uint32):
    """
    Get aligned memory array wih alignment align.
    Parameters
    ----------
    n: (int) length in dtype bytes of memory
    align: (int) memory alignment
    dtype: (numpy.dtype) type of the stored memory elements

    Returns
    -------

    """
    dtype = np.dtype(dtype)
    nbytes = n * dtype.itemsize
    buff = np.zeros(nbytes + align, dtype=np.uint8)
    start_index = -buff.ctypes.data % align
    return buff[start_index:start_index + nbytes].view(dtype)


def cfunc(name, dll, result, *args):
    """build and apply a ctypes prototype complete with parameter flags

    Parameters
    ----------
    name: (str) function name in the dll
    dll: (ctypes.windll) dll object
    result : result is the type of the result (c_int,..., python function handle,...)
    args: list of tuples with 3 or 4 elements each like (argname, argtype, in/out, default) where argname is the
    name of the argument, argtype is the type, in/out is 1 for input and 2 for output, and default is an optional
    default value.

    Returns
    -------
    python function
    """
    atypes = []
    aflags = []
    for arg in args:
        atypes.append(arg[1])
        aflags.append((arg[2], arg[0]) + arg[3:])
    return CFUNCTYPE(result, *atypes)((name, dll), tuple(aflags))


def winfunc(name, dll, result, *args):
    """build and apply a ctypes prototype complete with parameter flags
    Parameters
    ----------
    name:(str) function name in the dll
    dll: (ctypes.windll) dll object
    result: result is the type of the result (c_int,..., python function handle,...)
    args: list of tuples with 3 or 4 elements each like (argname, argtype, in/out, default) where argname is the
    name of the argument, argtype is the type, in/out is 1 for input and 2 for output, and default is an optional
    default value.

    Returns
    -------
    python function
    """
    atypes = []
    aflags = []
    for arg in args:
        atypes.append(arg[1])
        aflags.append((arg[2], arg[0]) + arg[3:])
    return WINFUNCTYPE(result, *atypes)((name, dll), tuple(aflags))


def set_param_from_param(param_old, param_new):
    """
        Walk through parameters children and set values using new parameter values.
    """
    for child_old in param_old.children():
        # try:
        path = param_old.childPath(child_old)
        child_new = param_new.child(*path)
        param_type = child_old.type()

        if 'group' not in param_type:  # covers 'group', custom 'groupmove'...
            # try:
            if 'list' in param_type:  # check if the value is in the limits of the old params (limits are usually set at initialization)
                if child_new.value() not in child_old.opts['limits']:
                    child_old.opts['limits'].append(child_new.value())

                child_old.setValue(child_new.value())
            elif 'str' in param_type or 'browsepath' in param_type or 'text' in param_type:
                if child_new.value() != "":  # to make sure one doesnt overwrite something
                    child_old.setValue(child_new.value())
            else:
                child_old.setValue(child_new.value())
            # except Exception as e:
            #    print(str(e))
        else:
            set_param_from_param(child_old, child_new)
        # except Exception as e:
        #    print(str(e))


# ########################
# #File management

def get_new_file_name(base_path=Path(config['data_saving']['h5file']['save_path']), base_name='tttr_data'):
    if isinstance(base_path, str):
        base_path = Path(base_path)

    today = datetime.datetime.now()

    date = today.strftime('%Y%m%d')
    year = today.strftime('%Y')
    year_dir = base_path.joinpath(year)
    if not year_dir.is_dir():
        year_dir.mkdir()
    curr_dir = base_path.joinpath(year, date)
    if not curr_dir.is_dir():
        curr_dir.mkdir()

    files = []
    for entry in curr_dir.iterdir():
        if entry.name.startswith(base_name) and entry.is_file():
            files.append(entry.stem)
    files.sort()
    if not files:
        index = 0
    else:
        index = int(files[-1][-3:]) + 1

    file = f'{base_name}_{index:03d}'
    return file, curr_dir


# ##############
# Math utilities
def my_moment(x, y):
    """Returns the moments of a distribution y over an axe x

    Parameters
    ----------
    x: list or ndarray
       vector of floats
    y: list or ndarray
       vector of floats corresponding to the x axis

    Returns
    -------
    m: list
       Contains moment of order 0 (mean) and of order 1 (std) of the distribution y
    """
    dx = np.mean(np.diff(x))
    norm = np.sum(y) * dx
    m = [np.sum(x * y) * dx / norm]
    m.extend([np.sqrt(np.sum((x - m[0]) ** 2 * y) * dx / norm)])
    return m


def normalize(x):
    x = x - np.min(x)
    x = x / np.max(x)
    return x


def odd_even(x):
    """
    odd_even tells if a number is odd (return True) or even (return False)

    Parameters
    ----------
    x: the integer number to test

    Returns
    -------
    bool : boolean
    """
    if not isinstance(x, int):
        raise TypeError(f'{x} should be an integer')
    if int(x) % 2 == 0:
        bool = False
    else:
        bool = True
    return bool


def greater2n(x):
    """
    return the first power of 2 greater than x
    Parameters
    ----------
    x: (int or float) a number

    Returns
    -------
    int: the power of 2 greater than x
    """
    if isinstance(x, bool):
        raise TypeError(f'{x} should be an integer or a float')
    if hasattr(x, '__iter__'):
        res = []
        for el in x:
            if isinstance(el, bool):
                raise TypeError(f'{el} should be an integer or a float')
            if not (isinstance(el, int) or isinstance(el, float)):
                raise TypeError(f'{x} elements should be integer or float')
            res.append(1 << (int(el) - 1).bit_length())
        if isinstance(x, np.ndarray):
            return np.array(res)
        else:
            return res
    else:
        if not (isinstance(x, int) or isinstance(x, float)):
            raise TypeError(f'{x} should be an integer or a float')
        return 1 << (int(x) - 1).bit_length()


def linspace_step(start, stop, step):
    """
    Compute a regular linspace_step distribution from start to stop values.

    =============== =========== ======================================
    **Parameters**    **Type**    **Description**
    *start*            scalar      the starting value of distribution
    *stop*             scalar      the stopping value of distribution
    *step*             scalar      the length of a distribution step
    =============== =========== ======================================

    Returns
    -------

    scalar array
        The computed distribution axis as an array.
    """
    if np.abs(step) < 1e-12 or np.sign(stop - start) != np.sign(step) or start == stop:
        raise ValueError('Invalid value for one parameter')
    Nsteps = int(np.ceil((stop - start) / step))
    new_stop = start + (Nsteps - 1) * step
    if np.abs(new_stop + step - stop) < 1e-12:
        Nsteps += 1
    new_stop = start + (Nsteps - 1) * step
    return np.linspace(start, new_stop, Nsteps)


def find_dict_if_matched_key_val(dict_tmp, key, value):
    """
    check if a key/value pair match in a given dictionnary
    Parameters
    ----------
    dict_tmp: (dict) the dictionnary to be tested
    key: (str) a key string to look for in dict_tmp
    value: (object) any python object

    Returns
    -------
    bool: True if the key/value pair has been found in dict_tmp

    """
    if key in dict_tmp:
        if dict_tmp[key] == value:
            return True
    return False


def find_dict_in_list_from_key_val(dicts, key, value, return_index=False):
    """ lookup within a list of dicts. Look for the dict within the list which has the correct key, value pair

    Parameters
    ----------
    dicts: (list) list of dictionnaries
    key: (str) specific key to look for in each dict
    value: value to match

    Returns
    -------
    dict: if found otherwise returns None
    """
    for ind, dict_tmp in enumerate(dicts):
        if find_dict_if_matched_key_val(dict_tmp, key, value):
            if return_index:
                return dict_tmp, ind
            else:
                return dict_tmp
    if return_index:
        return None, -1
    else:
        return None


def find_index(x, threshold):
    """
    find_index finds the index ix such that x(ix) is the closest from threshold
    Parameters
    ----------
    x : vector
    threshold : list of scalar

    Returns
    -------
    out : list of 2-tuple containing ix,x[ix]
            out=[(ix0,xval0),(ix1,xval1),...]
    """

    if not hasattr(threshold, '__iter__'):
        threshold = [threshold]
    out = []
    for value in threshold:
        ix = int(np.argmin(np.abs(x - value)))
        out.append((ix, x[ix]))
    return out


def find_common_index(x, y, x0, y0):
    vals = x + 1j * y
    val = x0 + 1j * y0
    ind = int(np.argmin(np.abs(vals - val)))
    return ind, x[ind], y[ind]


def gauss1D(x, x0, dx, n=1):
    """
    compute the gaussian function along a vector x, centered in x0 and with a
    FWHM i intensity of dx. n=1 is for the standart gaussian while n>1 defines
    a hypergaussian

    Parameters
    ----------
    x: (ndarray) first axis of the 2D gaussian
    x0: (float) the central position of the gaussian
    dx: (float) :the FWHM of the gaussian
    n=1 : an integer to define hypergaussian, n=1 by default for regular gaussian
    Returns
    -------
    out : vector
      the value taken by the gaussian along x axis

    """
    if dx <= 0:
        raise ValueError('dx should be strictly positive')
    if not isinstance(n, int):
        raise TypeError('n should be a positive integer')
    elif n < 0:
        raise ValueError('n should be a positive integer')
    out = np.exp(-2 * np.log(2) ** (1 / n) * (((x - x0) / dx)) ** (2 * n))
    return out


# def rotate_2D_array(arr, angle):
#     theta = np.radians(angle)
#     c, s = np.cos(theta), np.sin(theta)
#     R = np.array(((c, -s), (s, c)))
#     (x0r, y0r) = tuple(R.dot(np.array([x0, y0])))
#
#     data = np.zeros((len(y), len(x)))
#
#     for indx, xtmp in enumerate(x):
#         for indy, ytmp in enumerate(y):
#             rotatedvect = R.dot(np.array([xtmp, ytmp]))
#             data[indy, indx] = np.exp(
#                 -2 * np.log(2) ** (1 / n) * ((rotatedvect[0] - x0r) / dx) ** (2 * n)) * np.exp(
#                 -2 * np.log(2) ** (1 / n) * ((rotatedvect[1] - y0r) / dy) ** (2 * n))
#
#     return data


def gauss2D(x, x0, dx, y, y0, dy, n=1, angle=0):
    """
    compute the 2D gaussian function along a vector x, centered in x0 and with a
    FWHM in intensity of dx and smae along y axis. n=1 is for the standard gaussian while n>1 defines
    a hypergaussian. optionally rotate it by an angle in degree

    Parameters
    ----------
    x: (ndarray) first axis of the 2D gaussian
    x0: (float) the central position of the gaussian
    dx: (float) :the FWHM of the gaussian
    y: (ndarray) second axis of the 2D gaussian
    y0: (float) the central position of the gaussian
    dy: (float) :the FWHM of the gaussian
    n=1 : an integer to define hypergaussian, n=1 by default for regular gaussian
    angle: (float) a float to rotate main axes, in degree

    Returns
    -------
    out : ndarray 2 dimensions

    """
    if angle == 0:
        data = np.transpose(np.outer(gauss1D(x, x0, dx, n), gauss1D(y, y0, dy, n)))

    else:

        theta = np.radians(angle)
        c, s = np.cos(theta), np.sin(theta)
        R = np.array(((c, -s), (s, c)))
        (x0r, y0r) = tuple(R.dot(np.array([x0, y0])))

        data = np.zeros((len(y), len(x)))

        for indx, xtmp in enumerate(x):
            for indy, ytmp in enumerate(y):
                rotatedvect = R.dot(np.array([xtmp, ytmp]))
                data[indy, indx] = np.exp(
                    -2 * np.log(2) ** (1 / n) * ((rotatedvect[0] - x0r) / dx) ** (2 * n)) * np.exp(
                    -2 * np.log(2) ** (1 / n) * ((rotatedvect[1] - y0r) / dy) ** (2 * n))

    return data


def ftAxis(Npts, omega_max):
    """
    Given two numbers Npts,omega_max, return two vectors spanning the temporal
    and spectral range. They are related by Fourier Transform

    Parameters
    ----------
    Npts: (int)
      A number of points defining the length of both grids
    omega_max: (float)
      The maximum circular frequency in the spectral domain. its unit defines
      the temporal units. ex: omega_max in rad/fs implies time_grid in fs

    Returns
    -------
    omega_grid: (ndarray)
      The spectral axis of the FFT
    time_grid: (ndarray))
      The temporal axis of the FFT
    See Also
    --------
    ftAxis, ftAxis_time, ift, ft2, ift2
    """
    if not isinstance(Npts, int):
        raise TypeError('n should be a positive integer, if possible power of 2')
    elif Npts < 1:
        raise ValueError('n should be a strictly positive integer')
    dT = 2 * np.pi / (2 * omega_max)
    omega_grid = np.linspace(-omega_max, omega_max, Npts)
    time_grid = dT * np.linspace(-(Npts - 1) / 2, (Npts - 1) / 2, Npts)
    return omega_grid, time_grid


def ftAxis_time(Npts, time_max):
    """
    Given two numbers Npts,omega_max, return two vectors spanning the temporal
    and spectral range. They are related by Fourier Transform

    Parameters
    ----------
    Npts : number
      A number of points defining the length of both grids
    time_max : number
      The maximum tmporal window

    Returns
    -------
    omega_grid : vector
      The spectral axis of the FFT
    time_grid : vector
      The temporal axis of the FFT
    See Also
    --------
    ftAxis, ftAxis_time, ift, ft2, ift2
    """
    if not isinstance(Npts, int):
        raise TypeError('n should be a positive integer, if possible power of 2')
    elif Npts < 1:
        raise ValueError('n should be a strictly positive integer')
    dT = time_max / Npts
    omega_max = (Npts - 1) / 2 * 2 * np.pi / time_max
    omega_grid = np.linspace(-omega_max, omega_max, Npts)
    time_grid = dT * np.linspace(-(Npts - 1) / 2, (Npts - 1) / 2, Npts)
    return omega_grid, time_grid


def ft(x, dim=-1):
    """
    Process the 1D fast fourier transform and swaps the axis to get coorect results using ftAxis
    Parameters
    ----------
    x: (ndarray) the array on which the FFT should be done
    dim: the axis over which is done the FFT (default is the last of the array)

    Returns
    -------
    See Also
    --------
    ftAxis, ftAxis_time, ift, ft2, ift2
    """
    if not isinstance(dim, int):
        raise TypeError('dim should be an integer specifying the array dimension over which to do the calculation')
    assert isinstance(x, np.ndarray)
    assert dim >= -1
    assert dim <= len(x.shape) - 1

    out = np.fft.fftshift(np.fft.fft(np.fft.fftshift(x, axes=dim), axis=dim), axes=dim)
    return out


def ift(x, dim=0):
    """
    Process the inverse 1D fast fourier transform and swaps the axis to get correct results using ftAxis
    Parameters
    ----------
    x: (ndarray) the array on which the FFT should be done
    dim: the axis over which is done the FFT (default is the last of the array)

    Returns
    -------
    See Also
    --------
    ftAxis, ftAxis_time, ift, ft2, ift2
    """
    if not isinstance(dim, int):
        raise TypeError('dim should be an integer specifying the array dimension over which to do the calculation')
    assert isinstance(x, np.ndarray)
    assert dim >= -1
    assert dim <= len(x.shape) - 1
    out = np.fft.fftshift(np.fft.ifft(np.fft.fftshift(x, axes=dim), axis=dim), axes=dim)
    return out


def ft2(x, dim=(-2, -1)):
    """
    Process the 2D fast fourier transform and swaps the axis to get correct results using ftAxis
    Parameters
    ----------
    x: (ndarray) the array on which the FFT should be done
    dim: the axis over which is done the FFT (default is the last of the array)

    Returns
    -------
    See Also
    --------
    ftAxis, ftAxis_time, ift, ft2, ift2
    """
    assert isinstance(x, np.ndarray)
    if hasattr(dim, '__iter__'):
        for d in dim:
            if not isinstance(d, int):
                raise TypeError(
                    'elements in dim should be an integer specifying the array dimension over which to do the calculation')
            assert d <= len(x.shape)
    else:
        if not isinstance(dim, int):
            raise TypeError(
                'elements in dim should be an integer specifying the array dimension over which to do the calculation')
        assert dim <= len(x.shape)
    out = np.fft.fftshift(np.fft.fft2(np.fft.fftshift(x, axes=dim)), axes=dim)
    return out


def ift2(x, dim=(-2, -1)):
    """
    Process the inverse 2D fast fourier transform and swaps the axis to get correct results using ftAxis
    Parameters
    ----------
    x: (ndarray) the array on which the FFT should be done
    dim: the axis (or a tuple of axes) over which is done the FFT (default is the last of the array)

    Returns
    -------
    See Also
    --------
    ftAxis, ftAxis_time, ift, ft2, ift2
    """
    assert isinstance(x, np.ndarray)
    if hasattr(dim, '__iter__'):
        for d in dim:
            if not isinstance(d, int):
                raise TypeError(
                    'elements in dim should be an integer specifying the array dimension over which to do the calculation')
            assert d <= len(x.shape)
    else:
        if not isinstance(dim, int):
            raise TypeError(
                'elements in dim should be an integer specifying the array dimension over which to do the calculation')
        assert dim <= len(x.shape)
    out = np.fft.fftshift(np.fft.ifft2(np.fft.fftshift(x, axes=dim)), axes=dim)
    return out


if __name__ == '__main__':
    # paths = recursive_find_expr_in_files('C:\\Users\\weber\\Labo\\Programmes Python\\PyMoDAQ_Git', '__version__')
    # for p in paths:
    #     print(str(p))
    # v = get_version()
    # pass
    plugins = get_plugins()  # pragma: no cover
    pass

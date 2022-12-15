import os
import sys
from collections import OrderedDict
from ctypes import CFUNCTYPE

from pymodaq.daq_utils.config import get_set_config_path, get_set_preset_path, Config
from pymodaq.daq_utils.messenger import deprecation_msg
if 'win32' in sys.platform:
    from ctypes import WINFUNCTYPE
import datetime
import importlib
import inspect
import json
import logging
import functools
import time
from logging.handlers import TimedRotatingFileHandler
from packaging import version as version_mod
from pathlib import Path
import pkgutil
import traceback
import warnings
import numbers

import numpy as np
from qtpy import QtCore
from qtpy.QtCore import QLocale
from pymodaq.daq_utils.qvariant import QVariant

python_version = f'{str(sys.version_info.major)}.{str(sys.version_info.minor)}'
if version_mod.parse(python_version) >= version_mod.parse('3.8'):  # from version 3.8 this feature is included in the
    # standard lib
    from importlib import metadata
else:
    import importlib_metadata as metadata  # pragma: no cover

from pymodaq.daq_utils.exceptions import DataSourceError


plot_colors = [(255, 255, 255), (255, 0, 0), (0, 255, 0), (0, 0, 255), (14, 207, 189), (207, 14, 166), (207, 204, 14)]
config = Config()

Cb = 1.602176e-19  # coulomb
h = 6.626068e-34  # J.s
c = 2.997924586e8  # m.s-1


DATASOURCES = ('raw', 'roi')
DATADIMS = ('Data0D', 'Data1D', 'Data2D', 'DataND')


def load_config():
    deprecation_msg(f'Configuration file must now be  imported from the pymodaq.daq_utils.messenger module')
    return Config()


def is_64bits():
    return sys.maxsize > 2**32


def timer(func):
    """Print the runtime of the decorated function"""
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.perf_counter()    # 1
        value = func(*args, **kwargs)
        end_time = time.perf_counter()      # 2
        run_time = end_time - start_time    # 3
        print(f"Finished {func.__name__!r} in {run_time:.4f} secs")
        return value
    return wrapper_timer


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
            log_level = config('general', 'debug_level')
        logger.setLevel(log_level)
        handler = TimedRotatingFileHandler(log_path.joinpath('pymodaq.log'), when='midnight')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logging.captureWarnings(True)
        if log_level == 'DEBUG':
            warnings.filterwarnings('default', category=DeprecationWarning)
        else:
            warnings.filterwarnings('ignore', category=DeprecationWarning)

        warnings_logger = logging.getLogger("py.warnings")
        warnings_logger.addHandler(handler)

    if add_to_console:
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger


logger = set_logger('daq_utils')


def get_version():
    with open(str(Path(__file__).parent.parent.joinpath('resources/VERSION')), 'r') as fvers:
        version = fvers.read().strip()
    return version


def copy_preset():                          # pragma: no cover
    path = get_set_preset_path().joinpath('preset_default.xml')
    if not path.exists():  # copy the preset_default from pymodaq folder and create one in pymodad's local folder
        with open(str(Path(__file__).parent.parent.joinpath('resources/preset_default.xml')), 'r') as file:
            path.write_text(file.read())


def set_qt_backend():
    backend_present = True
    if config('qtbackend', 'backend').lower() not in [mod.lower() for mod in sys.modules]:
        backend_present = False
        logger.warning(f"The chosen Qt backend ({config('qtbackend', 'backend')}) has not been installed...\n"
                       f"Trying another...")
        backends = config('qtbackend', 'backends')
        backends.pop(backends.index(config('qtbackend', 'backend')))
        for backend in backends:
            if backend.lower() in [mod.lower() for mod in sys.modules]:
                backend_present = True
                break

    if backend_present:
        os.environ['QT_API'] = config('qtbackend', 'backend')
        logger.info('************************')
        logger.info(f"{config('qtbackend', 'backend')} Qt backend loaded")
        logger.info('************************')
    else:
        msg = f"No Qt backend could be found in your system, please install either pyqt5/6 or pyside2/6." \
              f"pyqt5 is still preferred, while pyqt6 should mostly work."
        logger.critical(msg)
        print(msg.upper())


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
            #TODO check this is fine
            value = QVariant()
            #value = None
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


class AxisBase(dict):
    """
    Utility class defining an axis for pymodaq's viewers, attributes can be accessed as dictionary keys or class
    type attributes
    """

    def __init__(self, label='', units='', **kwargs):
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
        if not isinstance(label, str):
            raise TypeError('label for the Axis class should be a string')
        self['label'] = label
        if not isinstance(units, str):
            raise TypeError('units for the Axis class should be a string')
        self['units'] = units
        self.update(kwargs)

    def __getattr__(self, item):
        if item in self:
            return self[item]
        else:
            raise AttributeError(f'{item} is not a valid attribute')


class Axis(AxisBase):
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
        super().__init__(label=label, units=units, **kwargs)
        if data is None or isinstance(data, np.ndarray):
            self['data'] = data
        else:
            raise TypeError('data for the Axis class should be a ndarray')
        self.update(kwargs)

    def __mul__(self, other):
        if isinstance(other, numbers.Number):
            return Axis(data=self['data'] * other, label=self['label'], units=self['units'])


class NavAxis(Axis):
    def __init__(self, data=None, label='', units='', nav_index=-1, **kwargs):
        super().__init__(data=data, label=label, units=units, **kwargs)

        if nav_index < 0:
            raise ValueError('nav_index should be a positive integer representing the index of this axis among all'
                             'navigation axes')
        self['nav_index'] = nav_index


class ScaledAxis(AxisBase):
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
    def __init__(self, scaled_xaxis: ScaledAxis, scaled_yaxis: ScaledAxis):
        assert isinstance(scaled_xaxis, ScaledAxis)
        assert isinstance(scaled_yaxis, ScaledAxis)
        self['scaled_xaxis'] = scaled_xaxis
        self['scaled_yaxis'] = scaled_yaxis


class Data(OrderedDict):
    def __init__(self, name='', source='raw', distribution='uniform', x_axis=Axis(), y_axis=Axis(), **kwargs):
        """
        Generic class subclassing from OrderedDict defining data being exported from pymodaq's plugin or viewers,
        attributes can be accessed as dictionary keys. Should be subclassed from for real datas
        Parameters
        ----------
        source: (str) either 'raw' or 'roi...' if straight from a plugin or data processed within a viewer
        distribution: (str) either 'uniform' or 'spread'
        x_axis: (Axis) Axis class defining the corresponding axis (if any) (with data either linearly spaced or containing the
         x positions of the spread points)
        y_axis: (Axis) Axis class defining the corresponding axis (if any) (with data either linearly spaced or containing the
         x positions of the spread points)
        """

        if not isinstance(name, str):
            raise TypeError(f'name for the {self.__class__.__name__} class should be a string')
        self['name'] = name
        if not isinstance(source, str):
            raise TypeError(f'source for the {self.__class__.__name__} class should be a string')
        elif not ('raw' in source or 'roi' in source):
            raise ValueError(f'Invalid "source" for the {self.__class__.__name__} class')
        self['source'] = source

        if not isinstance(distribution, str):
            raise TypeError(f'distribution for the {self.__class__.__name__} class should be a string')
        elif distribution not in ('uniform', 'spread'):
            raise ValueError(f'Invalid "distribution" for the {self.__class__.__name__} class')
        self['distribution'] = distribution

        if not isinstance(x_axis, Axis):
            if isinstance(x_axis, np.ndarray):
                x_axis = Axis(data=x_axis)
            else:
                raise TypeError(f'x_axis for the {self.__class__.__name__} class should be a Axis class')
            self['x_axis'] = x_axis
        elif x_axis['data'] is not None:
            self['x_axis'] = x_axis

        if not isinstance(y_axis, Axis):
            if isinstance(y_axis, np.ndarray):
                y_axis = Axis(data=y_axis)
            else:
                raise TypeError(f'y_axis for the {self.__class__.__name__} class should be a Axis class')
            self['y_axis'] = y_axis
        elif y_axis['data'] is not None:
            self['y_axis'] = y_axis

        for k in kwargs:
            self[k] = kwargs[k]

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError(f'{name} if not a key of {self}')

    def __repr__(self):
        return f'{self.__class__.__name__}: <name: {self.name}> - <distribution: {self.distribution}> - <source: {self.source}>'


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

        if dim not in DATADIMS and data is not None:
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

    def __repr__(self):
        return f'{self.__class__.__name__}: <name: {self.name}> - <distribution: {self.distribution}>' \
               f' - <source: {self.source}> - <dim: {self.dim}>'


class DataToExport(Data):
    def __init__(self, data=None, dim='', source='raw', **kwargs):
        """
        Utility class defining a data being exported from pymodaq's viewers, attributes can be accessed as dictionary keys
        Parameters
        ----------
        data: (ndarray or a scalar)
        dim: (str) data dimensionality (either Data0D, Data1D, Data2D or DataND)
        source: (str) either 'raw' for raw data or 'roi' for data extracted from a roi
        """
        super().__init__(source=source, **kwargs)
        if data is None or isinstance(data, np.ndarray) or isinstance(data, numbers.Number):
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
        if source not in DATASOURCES:
            raise DataSourceError(f'Data source should be in {DATASOURCES}')

    def __repr__(self):
        return f'{self.__class__.__name__}: <name: {self.name}> - <distribution: {self.distribution}>' \
               f' - <source: {self.source}> - <dim: {self.dim}>'


def ensure_ndarray(data):
    """
    Make sure data is returned as a numpy array
    Parameters
    ----------
    data

    Returns
    -------
    ndarray
    """
    if not isinstance(data, np.ndarray):
        if isinstance(data, list):
            data = np.array(data)
        else:
            data = np.array([data])
    return data


def setLocale():
    """
    defines the Locale to use to convert numbers to strings representation using language/country conventions
    Default is English and US
    """
    language = getattr(QLocale, config('style', 'language'))
    country = getattr(QLocale, config('style', 'country'))
    QLocale.setDefault(QLocale(language, country))


def recursive_find_files_extension(ini_path, ext, paths=[]):
    with os.scandir(ini_path) as it:
        for entry in it:
            if os.path.splitext(entry.name)[1][1:] == ext and entry.is_file():
                paths.append(entry.path)
            elif entry.is_dir():
                recursive_find_files_extension(entry.path, ext, paths)
    return paths


def recursive_find_files(ini_path, exp='make_enum', paths=[],
                         filters=['build']):
    for child in Path(ini_path).iterdir():
        if child.is_dir():
            recursive_find_files(child, exp, paths, filters)
        else:
            if exp in child.stem:
                if not any([filt in str(child) for filt in filters]):
                    paths.append(child)
    return paths


def recursive_find_expr_in_files(ini_path, exp='make_enum', paths=[],
                                 filters=['.git', '.idea', '__pycache__', 'build', 'egg', 'documentation', '.tox'],
                                 replace=False, replace_str=''):

    for child in Path(ini_path).iterdir():
        if not any(filt in str(child) for filt in filters):
            if child.is_dir():
                recursive_find_expr_in_files(child, exp, paths, filters, replace=replace, replace_str=replace_str)
            else:
                try:
                    found = False
                    with child.open('r') as f:
                        replacement = ''
                        for ind, line in enumerate(f):
                            if exp in line:
                                found = True
                                paths.append([child, ind, line])
                                if replace:
                                    replacement += line.replace(exp, replace_str)
                            else:
                                if replace:
                                    replacement += line
                    if replace and found:
                        with child.open('w') as f:
                            f.write(replacement)
                except Exception:
                    pass
    return paths


def count_lines(ini_path, count=0, filters=['lextab', 'yacctab','pycache', 'pyc']):
    # if Path(ini_path).is_file():
    #     with Path(ini_path).open('r') as f:
    #         count += len(f.readlines())
    #     return count
    for child in Path(ini_path).iterdir():
        if child.is_dir():
            count = count_lines(child, count)
        else:
            try:
                if not any([filt in child.name for filt in filters]):
                    if '.py' in child.name:
                        with child.open('r') as f:
                            count += len(f.readlines())
                else:
                    print(child.stem)
            except Exception:
                pass
    return count

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


def get_extensions():
    """
    Get pymodaq extensions as a list

    Returns
    -------
    list: list of disct containting the name and module of the found extension
    """
    extension_import = []
    entry_points = metadata.entry_points()
    if 'pymodaq.extensions' in entry_points:
        discovered_extension = entry_points['pymodaq.extensions']

        for pkg in discovered_extension:
            try:
                module = importlib.import_module(pkg.value)
                if hasattr(module, 'NICE_NAME'):
                    name = module.NICE_NAME
                else:
                    name = pkg.value
                extension = {'name': name, 'module': module}
                extension_import.append(extension)

            except Exception as e:  # pragma: no cover
                logger.warning(f'Impossible to import the {pkg.value} extension: {str(e)}')

    return extension_import

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


def get_models(model_name=None):
    """
    Get PID Models as a list to instantiate Control Actuators per degree of liberty in the model

    Returns
    -------
    list: list of disct containting the name and python module of the found models
    """
    from pymodaq.pid.utils import PIDModelGeneric
    models_import = []
    entry_points = metadata.entry_points()
    if 'pymodaq.pid_models' in entry_points:
        discovered_models = entry_points['pymodaq.pid_models']
        for pkg in discovered_models:
            try:
                module = importlib.import_module(pkg.value)
                module_name = pkg.value

                for mod in pkgutil.iter_modules([str(Path(module.__file__).parent.joinpath('models'))]):
                    try:
                        model_module = importlib.import_module(f'{module_name}.models.{mod.name}', module)
                        classes = inspect.getmembers(model_module, inspect.isclass)
                        for name, klass in classes:
                            if klass.__base__ is PIDModelGeneric:
                                models_import.append({'name': mod.name, 'module': model_module, 'class': klass})
                                break

                    except Exception as e:  # pragma: no cover
                        logger.warning(str(e))

            except Exception as e:  # pragma: no cover
                logger.warning(f'Impossible to import the {pkg.value} extension: {str(e)}')

    if model_name is None:
        return models_import
    else:
        return find_dict_in_list_from_key_val(models_import, 'name', model_name)

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
                except Exception as e:  # pragma: no cover
                    pass
        except Exception as e:  # pragma: no cover
            pass

    #add utility plugin for PID
    if plugin_type == 'daq_move':
        try:
            submodule = importlib.import_module('pymodaq.pid')

            plugins_import.append({'name': 'PID', 'module': submodule})

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


def get_module_name(module__file__path):
    """from the full path of a module extract its name"""
    path = Path(module__file__path)
    return path.stem


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

def get_new_file_name(base_path=Path(config('data_saving', 'h5file', 'save_path')), base_name='tttr_data'):
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

# math utility functions, should now be imported from the math_utils module
import pymodaq.daq_utils.math_utils as mutils

def my_moment(x, y):
    deprecation_msg(f'my_moment function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.my_moment(x, y)

def normalize(x):
    deprecation_msg(f'normalize function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.normalize(x)


def odd_even(x):
    deprecation_msg(f'odd_even function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.odd_even(x)


def greater2n(x):
    deprecation_msg(f'greater2n function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.greater2n(x)


def linspace_step(start, stop, step):
    deprecation_msg(f'linspace_step function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.linspace_step(start, stop, step)


def linspace_step_N(start, step, Npts):
    deprecation_msg(f'linspace_step_N function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.linspace_step_N(start, step, Npts)


def find_index(x, threshold):
    deprecation_msg(f'find_index function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.find_index(x, threshold)


def find_common_index(x, y, x0, y0):
    deprecation_msg(f'find_common_index function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.find_common_index(x, y, x0, y0)


def gauss1D(x, x0, dx, n=1):
    deprecation_msg(f'gauss1D function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.gauss1D(x, x0, dx, n=n)


def gauss2D(x, x0, dx, y, y0, dy, n=1, angle=0):
    deprecation_msg(f'gauss2D function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.gauss2D(x, x0, dx, y, y0, dy, n, angle)

def ftAxis(Npts, omega_max):
    deprecation_msg(f'ftAxis function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.ftAxis(Npts, omega_max)


def ftAxis_time(Npts, time_max):
    deprecation_msg(f'ftAxis_time function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.ftAxis_time(Npts, time_max)


def ft(x, dim=-1):
    deprecation_msg(f'ft function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.ft(x, dim)


def ift(x, dim=0):
    deprecation_msg(f'ift function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.ift(x, dim)


def ft2(x, dim=(-2, -1)):
    deprecation_msg(f'ft2 function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.ft2(x, dim)


def ift2(x, dim=(-2, -1)):
    deprecation_msg(f'ift2 function should now be imported from the {mutils.__name__} module', stacklevel=3)
    return mutils.ift2(x, dim)


if __name__ == '__main__':
    #paths = recursive_find_expr_in_files('C:\\Users\\weber\\Labo\\Programmes Python\\PyMoDAQ_Git', 'visa')
    # for p in paths:
    #     print(str(p))
    # v = get_version()
    # pass
    #plugins = get_plugins()  # pragma: no cover
    #extensions = get_extension()
    #models = get_models()
    #count = count_lines('C:\\Users\\weber\\Labo\\Programmes Python\\PyMoDAQ_Git\\pymodaq\src')


    # import license
    # mit = license.find('MIT')
    #
    # paths = recursive_find_expr_in_files('C:\\Users\\weber\\Labo\\Programmes Python\\PyMoDAQ_Git',
    #                                      exp='https://github.com/CEMES-CNRS',
    #                                      paths=[],
    #                                      filters=['.git', '.idea', '__pycache__', 'build', 'egg',
    #                                               '.tox', 'daq_utils.py'],
    #                                      replace=False, replace_str="https://github.com/PyMoDAQ")
    pass
    # paths = recursive_find_files('C:\\Users\\weber\\Labo\\Programmes Python\\PyMoDAQ_Git',
    #                      exp='VERSION', paths=[])
    # import version
    # for file in paths:
    #     with open(str(file), 'r') as f:
    #         v = version.Version(f.read())
    #         v.minor += 1
    #         v.patch = 0
    #     with open(str(file), 'w') as f:
    #         f.write(str(v))

    # for file in paths:
    #     with open(str(file), 'w') as f:
    #         f.write(mit.render(name='Sebastien Weber', email='sebastien.weber@cemes.fr'))


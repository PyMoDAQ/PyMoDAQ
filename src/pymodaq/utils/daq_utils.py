import os
import sys
import datetime
import importlib
import inspect
import json
import functools
import platform
import re
import time
import warnings
from packaging import version as version_mod
from pathlib import Path
import pkgutil
import traceback
import platform
from typing import Union, List

import numpy as np
from qtpy import QtCore
from qtpy.QtCore import QLocale

from pymodaq.utils import logger as logger_module
from pymodaq.utils.config import get_set_preset_path, Config
from pymodaq.utils.messenger import deprecation_msg
from pymodaq.utils.qvariant import QVariant

if version_mod.parse(platform.python_version()) >= version_mod.parse('3.8'):  # from version 3.8 this feature is included in the
    # standard lib
    from importlib import metadata
else:
    import importlib_metadata as metadata

if version_mod.parse(platform.python_version()) >= version_mod.parse('3.9'):
    # from version 3.9 the cache decorator is available
    from functools import cache
else:
    from functools import lru_cache as cache


if version_mod.parse(platform.python_version()) >= version_mod.parse('3.9'):
    # from version 3.9 the cache decorator is available
    from functools import cache
else:
    from functools import lru_cache as cache

logger = logger_module.set_logger(logger_module.get_module_name(__file__))

plot_colors = [(255, 255, 255), (255, 0, 0), (0, 255, 0), (0, 0, 255), (14, 207, 189), (207, 14, 166), (207, 204, 14)]
config = Config()


def __getattr__(name):
    if name in ['Axis', 'NavAxis', 'ScaledAxis', 'ScalingOptions', 'Data', 'DataTimeStamped', 'DataFromPlugins',
                'DataToEmit', 'DataToExport']:
        data_mod = importlib.import_module('.data', 'pymodaq.utils')
        deprecation_msg('Loading Axis or Data and their derived classes from daq_utils is deprecated, import them from'
                        ' pymodaq.utils.data module', 3)
        return getattr(data_mod, name)
    else:
        raise AttributeError


def load_config():
    deprecation_msg(f'config methods must now be  imported from the pymodaq.utils.messenger.cnfig module')
    return Config()


def set_logger(*args, **kwargs):
    deprecation_msg(f'Logger methods must now be  imported from the pymodaq.utils.logger module', 3)
    return logger_module.set_logger(*args, **kwargs)


def get_module_name(*args, **kwargs):
    deprecation_msg(f'Logger methods must now be  imported from the pymodaq.utils.logger module', 3)
    return logger_module.get_module_name(*args, **kwargs)


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


def get_version():
    """Obtain pymodaq version from the VERSION file

    Follows the layout from the packaging tool hatch, hatchling
    """
    DEFAULT_PATTERN = r'(?i)^(__version__|VERSION) *= *([\'"])v?(?P<version>.+?)\2'

    with open(str(Path(__file__).parent.parent.joinpath('resources/VERSION')), 'r') as fvers:
        contents = fvers.read().strip()
        match = re.search(DEFAULT_PATTERN, contents, flags=re.MULTILINE)
        groups = match.groupdict()
        if 'version' not in groups:
            raise ValueError('no group named `version` was defined in the pattern')
    return groups['version']


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
        backends.pop(config('qtbackend', 'backend'))
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
        warnings.warn(msg, FutureWarning, 3)
        print(msg.upper())


class JsonConverter:
    def __init__(self):
        super().__init__()

    @classmethod
    def trusted_types(cls):
        return ['float', 'int', 'str', 'datetime', 'date', 'time', 'tuple', 'list', 'bool', 'bytes',
                'float64']

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


def getLineInfo():
    """get information about where the Exception has been triggered"""
    tb = sys.exc_info()[2]
    res = ''
    for t in traceback.format_tb(tb):
        res += t
    return res


class ThreadCommand:
    """Generic object to pass info (command) and data (attribute) between thread or objects using signals

    Parameters
    ----------
    command: str
        The command to be analysed for further action
    attribute: any type
        the attribute related to the command. The actual type and value depend on the command and the situation
    attributes: deprecated, attribute should be used instead

    Attributes
    ----------
    command : str
        The command to be analysed for further action
    attribute : any type
        the attribute related to the command. The actual type and value depend on the command and the situation
    """

    def __init__(self, command: str, attribute=None, attributes=None):
        if not isinstance(command, str):
            raise TypeError(f'The command in a Threadcommand object should be a string, not a {type(command)}')
        self.command = command
        if attribute is None and attributes is not None:
            deprecation_msg('ThreadCommand signature changed, use attribute in place of attribute')
            self.attribute = attributes
            self.attributes = attributes
        self.attribute = attribute

    def __repr__(self):
        return f'Threadcommand: {self.command} with attribute {self.attribute}'


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


def find_keys_from_val(dict_tmp: dict, val: object):
    """Returns the keys from a dict if its value is matching val"""
    return [k for k, v in dict_tmp.items() if v == val]


def find_object_if_matched_attr_name_val(obj, attr_name, attr_value):
    """check if an attribute  key/value pair match in a given object

    Parameters
    ----------
    obj: object
    attr_name: str
        attribute name to look for in the object
    attr_value: object
        value to match

    Returns
    -------
    bool: True if the key/value pair has been found in dict_tmp

    """
    if hasattr(obj, attr_name):
        if getattr(obj, attr_name) == attr_value:
            return True
    return False


def find_objects_in_list_from_attr_name_val(objects: List[object], attr_name: str,
                                            attr_value: object, return_first=True):
    """ lookup within a list of objects. Look for the objects within the list which has the correct attribute name,
    value pair

    Parameters
    ----------
    objects: list
        list of objects
    attr_name: str
        attribute name to look for in the object
    attr_value: object
        value to match
    return_first: bool
        if True return the first objects found in the list else all the objects matching

    Returns
    -------
    list of tuple(object, int): object and index or list of object and indexes
    """
    selection = []
    obj = None
    for ind, obj_tmp in enumerate(objects):
        if find_object_if_matched_attr_name_val(obj_tmp, attr_name, attr_value):
            obj = obj_tmp
            if return_first:
                break
            else:
                selection.append((obj_tmp, ind))

    if obj is None:
        if return_first:
            return None, -1
        else:
            return []
    else:
        if return_first:
            return obj, ind
        else:
            return selection


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


def get_entrypoints(group='pymodaq.plugins'):
    """ Get the list of modules defined from a group entry point

    Because of evolution in the package, one or another of the forms below may be deprecated.
    We start from the newer way down to the older

    Parameters
    ----------
    group: str
        the name of the group
    """
    try:
        discovered_entrypoints = metadata.entry_points(group=group)
    except TypeError:
        try:
            discovered_entrypoints = metadata.entry_points().select(group=group)
        except AttributeError:
            discovered_entrypoints = metadata.entry_points().get(group, [])
    if isinstance(discovered_entrypoints, tuple):  # API for python > 3.8
        discovered_entrypoints = list(discovered_entrypoints)
    return discovered_entrypoints


@cache
def get_instrument_plugins():  # pragma: no cover
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
    discovered_plugins = []
    discovered_plugins_all = get_entrypoints(group='pymodaq.plugins')  # old naming of the instrument plugins
    discovered_plugins_all.extend(get_entrypoints(group='pymodaq.instruments'))  # new naming convention
    for entry in discovered_plugins_all:
        if entry.name not in [ent.name for ent in discovered_plugins]:
            discovered_plugins.append(entry)
    logger.debug(f'Found {len(discovered_plugins)} installed plugins, trying to import them')
    viewer_types = ['0D', '1D', '2D', 'ND']
    for entrypoint in discovered_plugins:
        #print(f'Looking for valid instrument plugins in package: {module.value}')
        plugin_list = []
        try:
            try:
                movemodule = importlib.import_module(f'{entrypoint.value}.daq_move_plugins', entrypoint.value)
                plugin_list.extend([{'name': mod[len('daq_move') + 1:],
                                     'module': movemodule,
                                     'parent_module': importlib.import_module(entrypoint.value),
                                     'type': 'daq_move'}
                                    for mod in [mod[1] for mod in pkgutil.iter_modules([str(movemodule.path.parent)])]
                                    if 'daq_move' in mod])
            except ModuleNotFoundError:
                pass
            viewer_modules = {}
            for vtype in viewer_types:
                try:
                    viewer_modules[vtype] = importlib.import_module(f'{entrypoint.value}.daq_viewer_plugins.plugins_{vtype}',
                                                    entrypoint.value)
                    plugin_list.extend([{'name': mod[len(f'daq_{vtype}viewer') + 1:],
                                     'module': viewer_modules[vtype],
                                     'parent_module': importlib.import_module(entrypoint.value),
                                     'type': f'daq_{vtype}viewer'}
                                    for mod in [mod[1] for mod in pkgutil.iter_modules([str(viewer_modules[vtype].path.parent)])]
                                    if f'daq_{vtype}viewer' in mod])
                except ModuleNotFoundError:
                    pass

            # check if modules are importable
            for mod in plugin_list:
                try:
                    plugin_type = mod['type']
                    if plugin_type == 'daq_move':
                        submodule = mod['module']
                        importlib.import_module(f'{submodule.__package__}.daq_move_{mod["name"]}')
                    else:
                        submodule = mod['module']
                        importlib.import_module(f'{submodule.__package__}.daq_{plugin_type[4:6]}viewer_{mod["name"]}')
                    plugins_import.append(mod)
                except Exception as e:  # pragma: no cover
                    """If an error is generated at the import, then exclude this plugin"""
                    logger.debug(f'Impossible to import Instrument plugin {mod["name"]}'
                                 f' from module: {mod["parent_module"].__package__}')
        except Exception as e:  # pragma: no cover
            logger.debug(str(e))
            
    # add utility plugin for PID
    try:
        pidmodule = importlib.import_module('pymodaq.extensions.pid')
        mod = [{'name': 'PID',
               'module': pidmodule,
               'parent_module': pidmodule,
               'type': 'daq_move'}]
        importlib.import_module(f'{pidmodule.__package__}.daq_move_PID')
        plugins_import.extend(mod)

    except Exception as e:
        logger.debug(f'Impossible to import PID utility plugin: {str(e)}')

    return plugins_import

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
    return [plug for plug in get_instrument_plugins() if plug['type'] == plugin_type]


def check_vals_in_iterable(iterable1, iterable2):
    assert len(iterable1) == len(iterable2)
    iterable1 = list(iterable1)  # so the assertion below is valid for any kind of iterable, list, tuple, ndarray...
    iterable2 = list(iterable2)
    for val1, val2 in zip(iterable1, iterable2):
        assert val1 == val2


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
import pymodaq.utils.math_utils as mutils

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

    # paths = recursive_find_expr_in_files(r'C:\Users\weber\Labo\Programmes Python\PyMoDAQ_Git',
    #                                      exp="cfunc",
    #                                      paths=[],
    #                                      filters=['.git', '.idea', '__pycache__', 'build', 'egg', 'documentation',
    #                                               '.tox',],
    #                                      replace=False,
    #                                      replace_str="pymodaq.utils")

    #get_version()
    get_instrument_plugins()
    #get_plugins('daq_move')
    #get_plugins('daq_0Dviewer')
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


import copy
import os
import sys
import datetime
import inspect
import json
import functools
import platform
import time
from packaging import version as version_mod
from pathlib import Path
import traceback
from typing import Any, cast, List, Optional, Tuple
from typing import Iterable as IterableType
from collections.abc import Iterable

import numpy as np

from pymodaq_utils import logger as logger_module
from pymodaq_utils.config import Config
from pymodaq_utils.warnings import deprecation_msg
from pymodaq_utils.serialize.factory import SerializableFactory, SerializableBase

from importlib import metadata
PackageNotFoundError = metadata.PackageNotFoundError  # for use elsewhere


# for use elsewhere
if version_mod.parse(platform.python_version()) >= version_mod.parse('3.9'):
    # from version 3.9 the cache decorator is available
    from functools import cache
else:
    from functools import lru_cache as cache


logger = logger_module.set_logger(logger_module.get_module_name(__file__))

config = Config()


class PlotColors:

    def __init__(self, colors=config('plotting', 'plot_colors')[:]):

        self._internal_counter = -1

        self.check_colors(colors)
        self._plot_colors = [tuple(color) for color in colors]

    def copy(self):
        return copy.copy(self)

    def remove(self, item):
        self._plot_colors.remove(item)

    def __getitem__(self, item: int):
        if not isinstance(item, int):
            raise TypeError('getter should be an integer')
        return tuple(self._plot_colors[item % len(self._plot_colors)])

    def __len__(self):
        return len(self._plot_colors)

    def __iter__(self):
        self._internal_counter = -1
        return self

    def __next__(self):
        if self._internal_counter >= len(self) - 1:
            raise StopIteration
        self._internal_counter += 1
        return self[self._internal_counter]

    def check_colors(self, colors: IterableType):
        if not isinstance(colors, Iterable):
            raise TypeError('Colors should be a list of 3-tuple 8 bits integer (0-255)')
        for color in colors:
            self.check_color(color)

    @staticmethod
    def check_color(color: IterableType):
        if not isinstance(color, Iterable) and len(color) != 3:
            raise TypeError('Colors should be a list of 3-tuple 8 bits integer (0-255)')
        for col_val in color:
            if not (isinstance(col_val, int) and 0 <= col_val <= 255):
                raise TypeError('Colors should be a list of 3-tuple 8 bits integer (0-255)')


plot_colors = PlotColors()


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


def get_version(package_name='pymodaq'):
    """Obtain the package version using the importlib metadata module
    """
    return metadata.version(package_name)


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

@SerializableFactory.register_decorator()
class ThreadCommand(SerializableBase):
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
    args: some variables in a list
    kwargs: some variables in a dict
    """
    command: str
    attribute: Any
    args: list
    kwargs: dict

    def __init__(self, command: str, attribute=None, attributes=None, args=(), kwargs: Optional[dict] = None):
        if not isinstance(command, str):
            raise TypeError(f'The command in a Threadcommand object should be a string, not a {type(command)}')
        self.command = command
        if attribute is None and attributes is not None:
            deprecation_msg('ThreadCommand signature changed, use attribute in place of attributes')
            self.attribute = attributes
            self.attributes = attributes
        self.attribute = attribute
        self.args = args
        self.kwargs = {} if kwargs is None else kwargs

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ThreadCommand):
            return NotImplemented
        return (
            self.command == other.command
            and self.attribute == other.attribute
            and self.args == other.args
            and self.kwargs == other.kwargs
        )

    @staticmethod
    def serialize(obj: "ThreadCommand") -> bytes:  # type: ignore[override]
        serialize_factory = SerializableFactory()
        byte_string = b""
        byte_string += serialize_factory.get_apply_serializer(obj.command)
        byte_string += serialize_factory.get_apply_serializer(obj.attribute)
        byte_string += serialize_factory.get_apply_serializer(obj.args)
        byte_string += serialize_factory.get_apply_serializer(obj.kwargs)
        return byte_string

    @staticmethod
    def deserialize(bytes_str: bytes) -> Tuple["ThreadCommand", bytes]:
        serialize_factory = SerializableFactory()
        command, remaining = cast(
            Tuple[str, bytes],
            serialize_factory.get_apply_deserializer(bytes_str=bytes_str, only_object=False),
        )
        attribute, remaining = cast(
            Tuple[Any, bytes], serialize_factory.get_apply_deserializer(remaining, False)
        )
        args, remaining = cast(
            Tuple[list, bytes],
            serialize_factory.get_apply_deserializer(remaining, False)
        )
        kwargs, remaining = cast(
            Tuple[dict, bytes],
            serialize_factory.get_apply_deserializer(remaining, False)
        )
        return ThreadCommand(command, attribute, args=tuple(args), kwargs=kwargs), remaining

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
    check if a key/value pair match in a given dictionary
    Parameters
    ----------
    dict_tmp: (dict) the dictionary to be tested
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


def find_dicts_in_list_from_key_val(dicts, key, value):
    """ lookup within a list of dicts. Look for the dicts within the list which have the correct key, value pair

    Parameters
    ----------
    dicts: (list) list of dictionnaries
    key: (str) specific key to look for in each dict
    value: value to match

    Returns
    -------
    dict: if found otherwise returns None
    """
    selection = []
    for ind, dict_tmp in enumerate(dicts):
        if find_dict_if_matched_key_val(dict_tmp, key, value):
            selection.append(dict_tmp)
    return selection


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


def get_entrypoints(group='pymodaq.plugins') -> List[metadata.EntryPoint]:
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
    if not isinstance(discovered_entrypoints, list):
        discovered_entrypoints = list(discovered_entrypoints)
    return discovered_entrypoints


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


if __name__ == '__main__':

    #plugins = get_plugins()  # pragma: no cover
    #extensions = get_extension()
    #models = get_models()
    #count = count_lines('C:\\Users\\weber\\Labo\\Programmes Python\\PyMoDAQ_Git\\pymodaq\src')


    # import license
    # mit = license.find('MIT')
    #

    paths = recursive_find_expr_in_files(r'C:\Users\weber\Labo\ProgrammesPython\PyMoDAQ_Git',
                                         exp="'multiaxes'",
                                         paths=[],
                                         filters=['.git', '.idea', '__pycache__', 'build', 'egg', 'documentation',
                                                  '.tox',],
                                         replace=False,
                                         replace_str="pymodaq.utils")

    #get_version()
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


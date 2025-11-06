# -*- coding: utf-8 -*-
"""
Created the 15/11/2022

@author: Sebastien Weber
"""
from typing import Union
from enum import Enum
import numpy as np
import importlib
from importlib import metadata
import pickle
from typing import Dict

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import Config
from pymodaq_utils.utils import capitalize, JsonConverter
from pymodaq_utils import utils
from pymodaq_utils.enums import BaseEnum, enum_checker


config = Config()
logger = set_logger(get_module_name(__file__))

backends_available = []

# default backend
is_tables = True
try:
    import tables
    backends_available.append('tables')
except Exception as e:                              # pragma: no cover
    logger.warning(str(e))
    is_tables = False

is_h5py = True
# other possibility
try:
    import h5py
    backends_available.append('h5py')
except Exception as e:                              # pragma: no cover
    logger.warning(str(e))
    is_h5py = False

is_h5pyd = True
# this one is to be used for remote reading/writing towards a HSDS server (or h5serv), see HDFGroup
try:
    import h5pyd
    backends_available.append('h5pyd')
except Exception as e:                              # pragma: no cover
    logger.warning(str(e))
    is_h5pyd = False

if not (is_tables or is_h5py or is_h5pyd):
    logger.exception('No valid hdf5 backend has been installed, please install either pytables or h5py')


class NodeError(Exception):
    pass


class SaveType(BaseEnum):
    scan = 0
    detector = 1
    logger = 2
    custom = 3
    actuator = 4
    optimizer = 5


class GroupType(BaseEnum):
    detector = 0
    actuator = 1
    data = 2
    ch = 3
    scan = 4
    external_h5 = 5
    data_dim = 6
    data_logger = 7


class InvalidExport(Exception):
    pass


def check_mandatory_attrs(attr_name, attr):
    """for cross compatibility between different backends. If these attributes have binary value, then decode them

    Parameters
    ----------
    attr_name
    attr

    Returns
    -------

    """
    if attr_name == 'TITLE' or attr_name == 'CLASS' or attr_name == 'EXTDIM':
        if isinstance(attr, bytes):
            return attr.decode()
        else:
            return attr
    else:
        return attr


def get_attr(node, attr_name, backend='tables'):
    if backend == 'tables':
        if attr_name is not None:
            attr = node._v_attrs[attr_name]
            attr = check_mandatory_attrs(attr_name, attr)
            return JsonConverter.json2object(attr)
        else:
            attrs = dict([])
            for attr_name in node._v_attrs._v_attrnames:
                attrval = node._v_attrs[attr_name]
                attrval = check_mandatory_attrs(attr_name, attrval)
                attrs[attr_name] = JsonConverter.json2object(attrval)
            return attrs
    else:
        if attr_name is not None:
            attr = node.attrs[attr_name]
            attr = check_mandatory_attrs(attr_name, attr)
            return JsonConverter.json2object(attr)
        else:
            attrs = dict([])
            for attr_name in node.attrs.keys():
                attrval = node.attrs[attr_name]
                attrval = check_mandatory_attrs(attr_name, attrval)
                attrs[attr_name] = JsonConverter.json2object(attrval)
            return attrs


def set_attr(node, attr_name, attr_value, backend='tables'):
    if backend == 'tables':
        node._v_attrs[attr_name] = JsonConverter.object2json(attr_value)
    else:
        node.attrs[attr_name] = JsonConverter.object2json(attr_value)


class InvalidGroupType(Exception):
    pass


class InvalidSave(Exception):
    pass


class InvalidGroupDataType(Exception):
    pass


class InvalidDataType(Exception):
    pass


class InvalidDataDimension(Exception):
    pass


class InvalidScanType(Exception):
    pass


class Node(object):
    def __init__(self, node, backend):
        if isinstance(node, Node):  # to ovoid recursion if one call Node(Node()) or even more
            self._node = node.node
        else:
            self._node = node
        self.backend = backend
        self._attrs = Attributes(self, backend)

    def __str__(self):
        # Get this class name
        classname = self.__class__.__name__
        # The title
        title = self.attrs['TITLE']
        return "%s (%s) %r" % \
               (self.path, classname, title)

    @property
    def node(self):
        return self._node

    def __eq__(self, other):
        return self.node == other.node

    @property
    def parent_node(self) -> 'GROUP':
        if self.path == '/':
            return None
        mod = importlib.import_module('.backends', 'pymodaq_data.h5modules')

        if self.backend == 'tables':
            p = self.node._v_parent
        else:
            p = self.node.parent
        klass = get_attr(p, 'CLASS', self.backend)
        _cls = getattr(mod, klass)
        return _cls(p, self.backend)

    @property
    def h5file(self):
        if self.backend == 'tables':
            return self.node._v_file
        else:
            return self.node.file

    def to_h5_backend(self) -> 'H5Backend':
        h5_backend = H5Backend(self.backend)
        h5_backend.h5file = self.h5file
        return h5_backend

    def set_attr(self, key, value):
        self.attrs[key] = value

    def get_attr(self, item):
        return self.attrs[item]

    @property
    def attrs(self):
        return self._attrs

    @property
    def name(self):
        """return node name
        """
        if self.backend == 'tables':
            return self._node._v_name
        else:
            path = self._node.name
            if path == '/':
                return path
            else:
                return path.split('/')[-1]

    @property
    def title(self):
        return self.attrs['TITLE']

    @property
    def path(self):
        """return node path
        Parameters
        ----------
        node (str or node instance), see h5py and pytables documentation on nodes

        Returns
        -------
        str : full path of the node
        """
        if self.backend == 'tables':
            return self._node._v_pathname
        else:
            return self._node.name


class GROUP(Node):
    def __init__(self, node, backend):
        super().__init__(node, backend)

    def __str__(self):
        """Return a short string representation of the group.
        """

        pathname = self.path
        classname = self.__class__.__name__
        title = self.attrs['TITLE']
        return "%s (%s) %r" % (pathname, classname, title)

    def __repr__(self):
        """Return a detailed string representation of the group.
        """

        rep = [
            '%r (%s)' % (childname, child.__class__.__name__)
            for (childname, child) in self.children().items()
        ]
        childlist = '[%s]' % (', '.join(rep))

        return "%s\n  children := %s" % (str(self), childlist)

    def children(self) -> Dict[str, Node]:
        """Get a dict containing all children node hanging from self whith their name as keys

        Returns
        -------
        dict: keys are children node names, values are the children nodes

        See Also
        --------
        children_name
        """
        mod = importlib.import_module('.backends', 'pymodaq_data.h5modules')
        children = dict([])
        if self.backend == 'tables':
            for child_name, child in self.node._v_children.items():
                klass = get_attr(child, 'CLASS', self.backend)
                if 'ARRAY' in klass:
                    _cls = getattr(mod, klass)
                else:
                    _cls = GROUP
                children[child_name] = _cls(child, self.backend)
        else:
            for child_name, child in self.node.items():

                klass = get_attr(child, 'CLASS', self.backend)
                if 'ARRAY' in klass:
                    _cls = getattr(mod, klass)
                else:
                    _cls = GROUP
                children[child_name] = _cls(child, self.backend)
        return children

    def get_child(self, name: str) -> Node:
        return self.children()[name]

    def children_name(self):
        """Gets the sorted list of children name hanging from self

        Returns
        -------
        list: list of name of the children
        """
        if self.backend == 'tables':
            return sorted(list(self.node._v_children.keys()))
        else:
            return sorted(list(self.node.keys()))
        pass

    def remove_children(self):
        children_dict = self.children()
        for child_name in children_dict:
            if self.backend == 'tables':
                children_dict[child_name].node._f_remove(recursive=True)
            else:
                self.node.__delitem__(child_name)


class CARRAY(Node):
    def __init__(self, node, backend):
        super().__init__(node, backend)
        self._array = node

    @property
    def array(self):
        return self._array

    def __repr__(self):
        """This provides more metainfo in addition to standard __str__"""

        return """%s
                shape := %s
                dtype := %s""" % (self, str(self.attrs['shape']), self.attrs['dtype'])

    def __getitem__(self, item):
        return self._array.__getitem__(item)

    def __setitem__(self, key, value):
        self._array.__setitem__(key, value)

    def read(self):
        if self.backend == 'tables':
            return self._array.read()
        else:
            return self._array[:]

    def __len__(self):
        if self.backend == 'tables':
            return self.array.nrows
        else:
            return len(self.array)


class EARRAY(CARRAY):
    def __init__(self, array, backend):
        super().__init__(array, backend)

    def append(self, data: np.ndarray, expand=True):
        """ appends a ndarray after the current data in the enlargeable array

        Considering the shape length of the enlargeable array is n+1

        The data to append could be:

        * a single element (without the enlargeable shape index that is always the first
        index, that is of shape length n). In that case the first index of the enlargeable array
        is increased by one.
        * an ensemble of elements (a ndarray) of shape length of (n+1).

        Parameters
        ----------
        data: np.ndarray
            the data array to append to the enlargeable node
        expand: bool
            If True the data array will have its shape expanded by one dim

        """
        if not isinstance(data, np.ndarray):
            raise TypeError('The appended object should be a ndarray')
        if len(self.attrs['shape']) > 1 and data.shape == self.attrs['shape'][1:]:
            shape = [1]
            shape.extend(data.shape)
            data = data.reshape(shape)
            extended_first_index = 1
        else:
            extended_first_index = data.shape[0]
        if expand and (len(data.shape) == 1 and not data.shape == (1, )):
            data = np.expand_dims(data, 1)
        self.append_backend(data)

        sh = list(self.attrs['shape'])
        sh[0] += extended_first_index
        self.attrs['shape'] = tuple(sh)

    def append_backend(self, data):
        if self.backend == 'tables':
            self.array.append(data)
        else:
            self.array.resize(self.array.len() + 1, axis=0)
            self.array[-1] = data


class VLARRAY(EARRAY):
    def __init__(self, array, backend):
        super().__init__(array, backend)

    def append(self, data):
        self.append_backend(data)

        sh = list(self.attrs['shape'])
        sh[0] += 1
        self.attrs['shape'] = tuple(sh)


class StringARRAY(VLARRAY):
    def __init__(self, array, backend):
        super().__init__(array, backend)

    def __getitem__(self, item):
        return self.array_to_string(super().__getitem__(item))

    def read(self):
        data_list = super().read()
        return [self.array_to_string(data) for data in data_list]

    def append(self, string):
        data = self.string_to_array(string)
        super().append(data)

    def array_to_string(self, array):
        return pickle.loads(array)

    def string_to_array(self, string):
        return np.frombuffer(pickle.dumps(string), np.uint8)


class Attributes(object):
    def __init__(self, node, backend='tables'):
        self._node = node
        self.backend = backend

    def __getitem__(self, item):
        if item == 'title':
            item = item.upper()
        attr = get_attr(self._node.node, item, backend=self.backend)
        # if isinstance(attr, bytes):
        #    attr = attr.decode()
        return attr

    def __setitem__(self, key, value):
        if key == 'title':
            key = key.upper()
        set_attr(self._node.node, key, value, backend=self.backend)

    def __iter__(self):
        self._iter_index = 0
        return self

    def __next__(self):
        if self._iter_index < len(self):
            self._iter_index += 1
            return self.attrs_name[self._iter_index-1]
        else:
            raise StopIteration

    def __len__(self):
        return len(self.attrs_name)

    def to_dict(self) -> dict:
        """Returns attributes name/value as a dict"""
        attrs_dict = dict()
        for name in self.attrs_name:
            attrs_dict[name] = self[name]
        return attrs_dict

    @property
    def node(self):
        return self._node

    @property
    def attrs_name(self):
        if self.backend == 'tables':
            return [k for k in self.node.node._v_attrs._v_attrnames]
        else:
            return [k for k in self.node.node.attrs.keys()]

    def __str__(self):
        """The string representation for this object."""

        # The pathname
        if self.backend == 'tables':
            pathname = self._node.node._v_pathname
        else:
            pathname = self._node.node.name
        # Get this class name
        classname = self.__class__.__name__
        # The attribute names
        attrnumber = len([n for n in self.attrs_name])
        return "%s.attrs (%s), %s attributes" % \
               (pathname, classname, attrnumber)

    def __repr__(self):
        attrnames = self.attrs_name
        if len(attrnames):
            rep = ['%s := %s' % (attr, str(self[attr]))
                   for attr in attrnames]
            attrlist = '[%s]' % (',\n    '.join(rep))

            return "%s:\n   %s" % (str(self), attrlist)
        else:
            return str(self)


class H5Backend:
    def __init__(self, backend='tables'):

        self._h5file = None
        self.backend = backend
        self.file_path = None
        self.compression = None
        if backend == 'tables':
            if is_tables:
                self.h5_library = tables
            else:
                raise ImportError('the pytables module is not present')
        elif backend == 'h5py':
            if is_h5py:
                self.h5_library = h5py
            else:
                raise ImportError('the h5py module is not present')
        elif backend == 'h5pyd':
            if is_h5pyd:
                self.h5_library = h5pyd
            else:
                raise ImportError('the h5pyd module is not present')

    @property
    def h5file(self):
        return self._h5file

    @h5file.setter
    def h5file(self, file):
        self.file_path = file.filename
        self._h5file = file

    @property
    def filename(self):
        return self._h5file.filename

    def isopen(self):
        if self._h5file is None:
            return False
        if self.backend == 'tables':
            return bool(self._h5file.isopen)
        elif self.backend == 'h5py':
            return bool(self._h5file.id.valid)
        else:
            return self._h5file.id.http_conn is not None

    def close_file(self):
        """Flush data and close the h5file
        """
        try:
            if self._h5file is not None:
                self.flush()
                if self.isopen():
                    self._h5file.close()
        except Exception as e:
            print(e)  # no big deal

    def open_file(self, fullpathname, mode='r', title='PyMoDAQ file', **kwargs):
        self.file_path = fullpathname
        if self.backend == 'tables':
            self._h5file = self.h5_library.open_file(str(fullpathname), mode=mode, title=title, **kwargs)
            if mode == 'w':
                try:
                    self.root().attrs['pymodaq_version'] = utils.get_version('pymodaq')
                except importlib.metadata.PackageNotFoundError:
                    self.root().attrs['pymodaq_version'] = '0.0.0'
                self.root().attrs['pymodaq_data_version'] = utils.get_version('pymodaq_data')
            return self._h5file
        else:
            self._h5file = self.h5_library.File(str(fullpathname), mode=mode, **kwargs)

            if mode == 'w':
                self.root().attrs['TITLE'] = title
                try:
                    self.root().attrs['pymodaq_version'] = utils.get_version('pymodaq')
                except importlib.metadata.PackageNotFoundError:
                    self.root().attrs['pymodaq_version'] = '0.0.0'
                self.root().attrs['pymodaq_data_version'] = utils.get_version('pymodaq_data')
            return self._h5file

    def save_file_as(self, filenamepath='h5copy.txt'):
        if self.backend == 'tables':
            self.h5file.copy_file(str(filenamepath))
        else:
            raise Warning(f'Not possible to copy the file with the "{self.backend}" backend')

    def root(self):
        if self.backend == 'tables':
            return GROUP(self._h5file.get_node('/'), self.backend)
        else:
            return GROUP(self._h5file, self.backend)

    def get_attr(self, node, attr_name=None):
        if isinstance(node, Node):
            node = node.node
        return get_attr(node, attr_name, self.backend)

    def set_attr(self, node, attr_name, attr_value):
        if isinstance(node, Node):
            node = node.node
        return set_attr(node, attr_name, attr_value, self.backend)

    def has_attr(self, node, attr_name):
        return attr_name in self.get_node(node).attrs.attrs_name

    def flush(self):
        if self._h5file is not None:
            self._h5file.flush()

    def define_compression(self, compression, compression_opts):
        """Define cmpression library and level of compression
        Parameters
        ----------
        compression: (str) either gzip and zlib are supported here as they are compatible
                        but zlib is used by pytables while gzip is used by h5py
        compression_opts (int) : 0 to 9  0: None, 9: maximum compression
        """
        #
        if self.backend == 'tables':
            if compression == 'gzip':
                compression = 'zlib'
            self.compression = self.h5_library.Filters(complevel=compression_opts, complib=compression)
        else:
            if compression == 'zlib':
                compression = 'gzip'
            self.compression = dict(compression=compression, compression_opts=compression_opts)

    def get_set_group(self, where, name, title='', **kwargs):
        """Retrieve or create (if absent) a node group
        Get attributed to the class attribute ``current_group``

        Parameters
        ----------
        where: str or node
               path or parent node instance
        name: str
              group node name
        title: str
               node title

        Keyword Arguments:
            any other metadata related to this node (for example: origin)
        Returns
        -------
        group: group node
        """

        if isinstance(where, Node):
            where = where.node

        if name not in list(self.get_children(where)):
            if self.backend == 'tables':
                group = self._h5file.create_group(where, name, title)
                for key, value in kwargs.items():
                    if not hasattr(group._v_attrs, key):
                        group._v_attrs[key] = value
            else:
                group = self.get_node(where).node.create_group(name)
                group.attrs['TITLE'] = title
                group.attrs['CLASS'] = 'GROUP'
                for key, value in kwargs.items():
                    if not hasattr(group.attrs, key):
                        group.attrs[key] = value

        else:
            group = self.get_node(where, name)
        return GROUP(group, self.backend)

    def get_group_by_title(self, where, title):
        if isinstance(where, Node):
            where = where.node

        node = self.get_node(where).node
        for child_name in self.get_children(node):
            child = node[child_name]
            if 'TITLE' in self.get_attr(child):
                if self.get_attr(child, 'TITLE') == title and self.get_attr(child, 'CLASS') == 'GROUP':
                    return GROUP(child, self.backend)
        return None

    def is_node_in_group(self, where, name):
        """
        Check if a given node with name is in the group defined by where (comparison on lower case strings)
        Parameters
        ----------
        where: (str or node)
                path or parent node instance
        name: (str)
              group node name

        Returns
        -------
        bool
            True if node exists, False otherwise
        """
        if isinstance(where, Node):
            where = where.node

        return name.lower() in [name.lower() for name in self.get_children(where)]

    def get_node(self, where, name=None) -> Node:
        if isinstance(where, Node):
            where = where.node
        try:
            if self.backend == 'tables':
                node = self._h5file.get_node(where, name)
            else:
                if name is not None:
                    if isinstance(where, str):
                        where += f'/{name}'
                        node = self._h5file.get(where)
                    else:
                        where = where.get(name)
                        node = where
                else:
                    if isinstance(where, str):
                        node = self._h5file.get(where)
                    else:
                        node = where
        except Exception as e:
            raise NodeError(str(e))

        if 'CLASS' not in self.get_attr(node):
            self.set_attr(node, 'CLASS', 'GROUP')
            return GROUP(node, self.backend)
        else:
            attr = self.get_attr(node, 'CLASS')
            if 'ARRAY' not in attr:
                return GROUP(node, self.backend)
            elif attr == 'CARRAY':
                return CARRAY(node, self.backend)
            elif attr == 'EARRAY':
                return EARRAY(node, self.backend)
            elif attr == 'VLARRAY':
                if self.get_attr(node, 'subdtype') == 'string':
                    return StringARRAY(node, self.backend)
                else:
                    return VLARRAY(node, self.backend)

    def get_node_name(self, node):
        """return node name
        Parameters
        ----------
        node (str or node instance), see h5py and pytables documentation on nodes

        Returns
        -------
        str: name of the node
        """
        if isinstance(node, Node):
            node = node.node
        return self.get_node(node).name

    def get_node_path(self, node):
        """return node path
        Parameters
        ----------
        node (str or node instance), see h5py and pytables documentation on nodes

        Returns
        -------
        str : full path of the node
        """
        if isinstance(node, Node):
            node = node.node
        return self.get_node(node).path

    def get_parent_node(self, node):
        if node == self.root():
            return None
        if isinstance(node, Node):
            node = node.node

        if self.backend == 'tables':
            return self.get_node(node._v_parent)
        else:
            return self.get_node(node.parent)

    def get_children(self, where):
        """Get a dict containing all children node hanging from where with their name as keys and types among Node,
        CARRAY, EARRAY, VLARRAY or StringARRAY

        Parameters
        ----------
        where (str or node instance)
            see h5py and pytables documentation on nodes, and Node objects of this module

        Returns
        -------
        dict: keys are children node names, values are the children nodes

        See Also
        --------
        :meth:`.GROUP.children_name`

        """
        where = self.get_node(where)  # return a node object in case where is a string
        if isinstance(where, Node):
            where = where.node

        mod = importlib.import_module('.backends', 'pymodaq_data.h5modules')
        children = dict([])
        if self.backend == 'tables':
            for child_name, child in where._v_children.items():
                klass = get_attr(child, 'CLASS', self.backend)
                if 'ARRAY' in klass:
                    _cls = getattr(mod, klass)
                else:
                    _cls = GROUP
                children[child_name] = _cls(child, self.backend)
        else:
            for child_name, child in where.items():
                klass = get_attr(child, 'CLASS', self.backend)
                if 'ARRAY' in klass:
                    _cls = getattr(mod, klass)
                else:
                    _cls = GROUP
                children[child_name] = _cls(child, self.backend)
        return children

    def walk_nodes(self, where):
        where = self.get_node(where)  # return a node object in case where is a string
        yield where
        for gr in self.walk_groups(where):
            for child in self.get_children(gr).values():
                yield child

    def walk_groups(self, where):
        where = self.get_node(where)  # return a node object in case where is a string
        if where.attrs['CLASS'] != 'GROUP':
            return None
        if self.backend == 'tables':
            for ch in self.h5file.walk_groups(where.node):
                yield self.get_node(ch)
        else:
            stack = [where]
            yield where
            while stack:
                obj = stack.pop()
                children = [child for child in self.get_children(obj).values() if child.attrs['CLASS'] == 'GROUP']
                for child in children:
                    stack.append(child)
                    yield child

    def read(self, array, *args, **kwargs):
        if isinstance(array, CARRAY):
            array = array.array
        if self.backend == 'tables':
            return array.read()
        else:
            return array[:]

    def create_carray(self, where, name, obj=None, title=''):
        if isinstance(where, Node):
            where = where.node
        if obj is None:
            raise ValueError('Data to be saved as carray cannot be None')
        dtype = obj.dtype
        if self.backend == 'tables':
            array = CARRAY(self._h5file.create_carray(where, name, obj=obj,
                                                      title=title,
                                                      filters=self.compression), self.backend)
        else:
            if self.compression is not None:
                array = CARRAY(self.get_node(where).node.create_dataset(name, data=obj, **self.compression),
                               self.backend)
            else:
                array = CARRAY(self.get_node(where).node.create_dataset(name, data=obj), self.backend)
            array.array.attrs['TITLE'] = title
            array.array.attrs[
                'CLASS'] = 'CARRAY'  # direct writing using h5py to be compatible with pytable automatic class writing as binary
        array.attrs['shape'] = obj.shape
        array.attrs['dtype'] = dtype.name
        array.attrs['subdtype'] = ''
        array.attrs['backend'] = self.backend
        return array

    def create_earray(self, where, name, dtype, data_shape=None, title=''):
        """create enlargeable arrays from data with a given shape and of a given type. The array is enlargeable along
        the first dimension
        """
        if isinstance(where, Node):
            where = where.node
        dtype = np.dtype(dtype)
        shape = [0]
        if data_shape is not None:
            shape.extend(list(data_shape))
        shape = tuple(shape)

        if self.backend == 'tables':
            atom = self.h5_library.Atom.from_dtype(dtype)
            array = EARRAY(self._h5file.create_earray(where, name, atom, shape=shape, title=title,
                                                      filters=self.compression), self.backend)
        else:
            maxshape = [None]
            if data_shape is not None:
                maxshape.extend(list(data_shape))
            maxshape = tuple(maxshape)
            if self.compression is not None:
                array = EARRAY(
                    self.get_node(where).node.create_dataset(name, shape=shape, dtype=dtype, maxshape=maxshape,
                                                             **self.compression), self.backend)
            else:
                array = EARRAY(
                    self.get_node(where).node.create_dataset(name, shape=shape, dtype=dtype, maxshape=maxshape),
                    self.backend)
            array.array.attrs['TITLE'] = title
            array.array.attrs[
                'CLASS'] = 'EARRAY'  # direct writing using h5py to be compatible with pytable automatic class writing as binary
            array.array.attrs['EXTDIM'] = 0
        array.attrs['shape'] = shape
        array.attrs['dtype'] = dtype.name
        array.attrs['subdtype'] = ''
        array.attrs['backend'] = self.backend
        return array

    def create_vlarray(self, where, name, dtype, title=''):
        """create variable data length and type and enlargeable 1D arrays

        Parameters
        ----------
        where: (str) group location in the file where to create the array node
        name: (str) name of the array
        dtype: (dtype) numpy dtype style, for particular case of strings, use dtype='string'
        title: (str) node title attribute (written in capitals)

        Returns
        -------
        array

        """
        if isinstance(where, Node):
            where = where.node
        if dtype == 'string':
            dtype = np.dtype(np.uint8)
            subdtype = 'string'
        else:
            dtype = np.dtype(dtype)
            subdtype = ''
        if self.backend == 'tables':
            atom = self.h5_library.Atom.from_dtype(dtype)
            if subdtype == 'string':
                array = StringARRAY(self._h5file.create_vlarray(where, name, atom, title=title,
                                                                filters=self.compression), self.backend)
            else:
                array = VLARRAY(self._h5file.create_vlarray(where, name, atom, title=title,
                                                            filters=self.compression), self.backend)
        else:
            maxshape = (None,)
            if self.backend == 'h5py':
                dt = self.h5_library.vlen_dtype(dtype)
            else:
                dt = h5pyd.special_dtype(dtype)
            if self.compression is not None:
                if subdtype == 'string':
                    array = StringARRAY(self.get_node(where).node.create_dataset(name, (0,), dtype=dt,
                                                                                 **self.compression, maxshape=maxshape),
                                        self.backend)
                else:
                    array = VLARRAY(self.get_node(where).node.create_dataset(name, (0,), dtype=dt, **self.compression,
                                                                             maxshape=maxshape), self.backend)
            else:
                if subdtype == 'string':
                    array = StringARRAY(self.get_node(where).node.create_dataset(name, (0,), dtype=dt,
                                                                                 maxshape=maxshape), self.backend)
                else:
                    array = VLARRAY(self.get_node(where).node.create_dataset(name, (0,), dtype=dt,
                                                                             maxshape=maxshape), self.backend)
            array.array.attrs['TITLE'] = title
            array.array.attrs[
                'CLASS'] = 'VLARRAY'  # direct writing using h5py to be compatible with pytable automatic class writing as binary
            array.array.attrs['EXTDIM'] = 0
        array.attrs['shape'] = (0,)
        array.attrs['dtype'] = dtype.name
        array.attrs['subdtype'] = subdtype
        array.attrs['backend'] = self.backend
        return array

    def add_group(self, group_name, group_type: Union[GroupType, str], where, title='', metadata=dict([])) -> GROUP:
        """
        Add a node in the h5 file tree of the group type
        Parameters
        ----------
        group_name: (str) a custom name for this group
        group_type: str or GroupType enum
            one of the possible values of GroupType, should be enforced by higher level modules not here
        where: (str or node) parent node where to create the new group
        metadata: (dict) extra metadata to be saved with this new group node

        Returns
        -------
        (node): newly created group node
        """
        if isinstance(where, Node):
            where = where.node

        if isinstance(group_type, Enum):
            group_type = group_type.name

        if group_name in self.get_children(self.get_node(where)):
            node = self.get_node(where, group_name)

        else:
            node = self.get_set_group(where, utils.capitalize(group_name), title)
            node.attrs['type'] = group_type.lower()
            for metadat in metadata:
                node.attrs[metadat] = metadata[metadat]
        node.attrs['backend'] = self.backend
        return node

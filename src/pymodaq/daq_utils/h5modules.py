import os
import sys
from collections import OrderedDict
import warnings
import logging
from copy import deepcopy
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QLocale, QByteArray

import pymodaq.daq_utils.parameter.ioxml
from pyqtgraph.parametertree import Parameter, ParameterTree
from pymodaq.daq_utils.parameter import utils as putils
from pymodaq.daq_utils.tree_layout.tree_layout_main import Tree_layout
from pymodaq.daq_utils.daq_utils import capitalize, Axis, JsonConverter, NavAxis
from pymodaq.daq_utils.gui_utils import h5tree_to_QTree, pngbinary2Qlabel, select_file, DockArea
from pymodaq.daq_utils.plotting.viewerND.viewerND_main import ViewerND
import pickle
from PyQt5 import QtWidgets
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils.scanner import scan_types as stypes
from pymodaq.daq_utils.gui_utils import dashboard_submodules_params

import datetime
from dateutil import parser
import numpy as np
from pathlib import Path
import copy
import importlib
from packaging import version as version_mod

config = utils.load_config()

logger = utils.set_logger(utils.get_module_name(__file__))
backends_available = []

# default backend
is_tables = True
try:
    import tables
    backends_available.append('tables')
except Exception as e:                              # pragma: no cover
    logger.exception(str(e))
    is_tables = False

is_h5py = True
# other possibility
try:
    import h5py
    backends_available.append('h5py')
except Exception as e:                              # pragma: no cover
    logger.exception(str(e))
    is_h5y = False

is_h5pyd = True
# this one is to be used for remote reading/writing towards a HSDS server (or h5serv), see HDFGroup
try:
    import h5pyd
    backends_available.append('h5pyd')
except Exception as e:                              # pragma: no cover
    logger.warning(str(e))
    is_h5yd = False

version = '0.0.1'
save_types = ['scan', 'detector', 'logger', 'custom']
group_types = ['raw_datas', 'scan', 'detector', 'move', 'data', 'ch', '', 'external_h5']
group_data_types = ['data0D', 'data1D', 'data2D', 'dataND']
data_types = ['data', 'axis', 'live_scan', 'navigation_axis', 'external_h5', 'strings', 'bkg']
data_dimensions = ['0D', '1D', '2D', 'ND']
scan_types = ['']
scan_types.extend(stypes)


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
    def parent_node(self):
        if self.path == '/':
            return None
        mod = importlib.import_module('.h5modules', 'pymodaq.daq_utils')

        if self.backend == 'tables':
            p = self.node._v_parent
        else:
            p = self.node.parent
        klass = get_attr(p, 'CLASS', self.backend)
        _cls = getattr(mod, klass)
        return _cls(p, self.backend)

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

    def children(self):
        """Get a dict containing all children node hanging from self whith their name as keys

        Returns
        -------
        dict: keys are children node names, values are the children nodes

        See Also
        --------
        children_name
        """
        mod = importlib.import_module('.h5modules', 'pymodaq.daq_utils')
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

    def children_name(self):
        """Gets the list of children name hanging from self

        Returns
        -------
        list: list of name of the children
        """
        if self.backend == 'tables':
            return list(self.node._v_children.keys())
        else:
            return list(self.node.keys())
        pass


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

    def append(self, data):
        if isinstance(data, np.ndarray):
            if data.shape != (1,):
                shape = [1]
                shape.extend(data.shape)
                data = data.reshape(shape)

        self.append_backend(data)

        sh = list(self.attrs['shape'])
        sh[0] += 1
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
        attr = get_attr(self._node.node, item, backend=self.backend)
        # if isinstance(attr, bytes):
        #    attr = attr.decode()
        return attr

    def __setitem__(self, key, value):
        set_attr(self._node.node, key, value, backend=self.backend)

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
                self.h5module = tables
            else:
                raise ImportError('the pytables module is not present')
        elif backend == 'h5py':
            if is_h5py:
                self.h5module = h5py
            else:
                raise ImportError('the h5py module is not present')
        elif backend == 'h5pyd':
            if is_h5pyd:
                self.h5module = h5pyd
            else:
                raise ImportError('the h5pyd module is not present')

    @property
    def h5file(self):
        return self._h5file

    @h5file.setter
    def h5file(self, file):
        self.file_path = file.filename
        self._h5file = file

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
            self._h5file = self.h5module.open_file(str(fullpathname), mode=mode, title=title, **kwargs)
            if mode == 'w':
                self.root().attrs['pymodaq_version'] = utils.get_version()
            return self._h5file
        else:
            self._h5file = self.h5module.File(str(fullpathname), mode=mode, **kwargs)

            if mode == 'w':
                self.root().attrs['TITLE'] = title
                self.root().attrs['pymodaq_version'] = utils.get_version()
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
            self.compression = self.h5module.Filters(complevel=compression_opts, complib=compression)
        else:
            if compression == 'zlib':
                compression = 'gzip'
            self.compression = dict(compression=compression, compression_opts=compression_opts)

    def get_set_group(self, where, name, title=''):
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

        Returns
        -------
        group: group node
        """
        if isinstance(where, Node):
            where = where.node

        if name not in list(self.get_children(where)):
            if self.backend == 'tables':
                group = self._h5file.create_group(where, name, title)
            else:
                group = self.get_node(where).node.create_group(name)
                group.attrs['TITLE'] = title
                group.attrs['CLASS'] = 'GROUP'

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

    def get_node(self, where, name=None):
        if isinstance(where, Node):
            where = where.node

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
        """Get a dict containing all children node hanging from where whith their name as keys and types among Node,
        CARRAY, EARRAY, VLARRAY or StringARRAY
        Parameters
        ----------
        where (str or node instance), see h5py and pytables documentation on nodes, and Node objects of this module

        Returns
        -------
        dict: keys are children node names, values are the children nodes

        See Also
        --------
        children_name, Node, CARRAY, EARRAY, VLARRAY or StringARRAY
        """
        where = self.get_node(where)  # return a node object in case where is a string
        if isinstance(where, Node):
            where = where.node

        mod = importlib.import_module('.h5modules', 'pymodaq.daq_utils')
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
            atom = self.h5module.Atom.from_dtype(dtype)
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
            atom = self.h5module.Atom.from_dtype(dtype)
            if subdtype == 'string':
                array = StringARRAY(self._h5file.create_vlarray(where, name, atom, title=title,
                                                                filters=self.compression), self.backend)
            else:
                array = VLARRAY(self._h5file.create_vlarray(where, name, atom, title=title,
                                                            filters=self.compression), self.backend)
        else:
            maxshape = (None,)
            if self.backend == 'h5py':
                dt = self.h5module.vlen_dtype(dtype)
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

    def add_group(self, group_name, group_type, where, title='', metadata=dict([])):
        """
        Add a node in the h5 file tree of the group type
        Parameters
        ----------
        group_name: (str) a custom name for this group
        group_type: (str) one of the possible values of **group_types**
        where: (str or node) parent node where to create the new group
        metadata: (dict) extra metadata to be saved with this new group node

        Returns
        -------
        (node): newly created group node
        """
        if isinstance(where, Node):
            where = where.node
        if group_type not in group_types:
            raise InvalidGroupType('Invalid group type')

        if group_name in self.get_children(self.get_node(where)):
            node = self.get_node(where, group_name)

        else:
            node = self.get_set_group(where, utils.capitalize(group_name), title)
            node.attrs['type'] = group_type.lower()
            for metadat in metadata:
                node.attrs[metadat] = metadata[metadat]
        node.attrs['backend'] = self.backend
        return node


class H5LogHandler(logging.StreamHandler):
    def __init__(self, h5saver):
        super().__init__()
        self.h5saver = h5saver
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.setFormatter(formatter)

    def emit(self, record):
        msg = self.format(record)
        self.h5saver.add_log(msg)


class H5SaverBase(H5Backend):
    """Object containing all methods in order to save datas in a *hdf5 file* with a hierachy compatible with
    the H5Browser. The saving parameters are contained within a **Parameter** object: self.settings that can be displayed
    on a UI using the widget self.settings_tree. At the creation of a new file, a node
    group named **Raw_datas** and represented by the attribute ``raw_group`` is created and set with a metadata attribute:

    * 'type' given by the **save_type** class parameter

    The root group of the file is then set with a few metadata:

    * 'pymodaq_version' the current pymodaq version, e.g. 1.6.2
    * 'file' the file name
    * 'date' the current date
    * 'time' the current time

    All datas will then be saved under this node in various groups

    See Also
    --------
    H5Browser

    Parameters
    ----------
    h5_file: pytables hdf5 file
             object used to save all datas and metadas
    h5_file_path: str or Path
                  pyqtSignal signal represented by a float. Is emitted each time the hardware reached the target
                  position within the epsilon precision (see comon_parameters variable)
    save_type: str
               an element of the list module attribute save_types = ['scan', 'detector', 'custom']
               * 'scan' is used for DAQ_Scan module and should be used for similar application
               * 'detector' is used for DAQ_Viewer module and should be used for similar application
               * 'custom' should be used for customized applications

    Attributes
    ----------

    settings: Parameter
               Parameter instance (pyqtgraph) containing all settings (could be represented using the settings_tree widget)

    settings_tree: ParameterTree
                   Widget representing as a Tree structure, all the settings defined in the class preamble variable ``params``

    """

    params = [
        {'title': 'Save type:', 'name': 'save_type', 'type': 'list', 'values': save_types, 'readonly': True},
    ] + dashboard_submodules_params + \
        [{'title': 'Backend:', 'name': 'backend', 'type': 'group', 'children': [
            {'title': 'Backend type:', 'name': 'backend_type', 'type': 'list', 'values': backends_available,
                'readonly': True},
            {'title': 'HSDS Server:', 'name': 'hsds_options', 'type': 'group', 'visible': False, 'children': [
                {'title': 'Endpoint:', 'name': 'endpoint', 'type': 'str',
                    'value': config['data_saving']['hsds']['root_url'], 'readonly': False},
                {'title': 'User:', 'name': 'user', 'type': 'str',
                    'value': config['data_saving']['hsds']['username'], 'readonly': False},
                {'title': 'password:', 'name': 'password', 'type': 'str',
                    'value': config['data_saving']['hsds']['pwd'], 'readonly': False},
            ]},
        ]},

        {'title': 'custom_name?:', 'name': 'custom_name', 'type': 'bool', 'default': False, 'value': False},
        {'title': 'show file content?', 'name': 'show_file', 'type': 'bool_push', 'default': False,
            'value': False},
        {'title': 'Base path:', 'name': 'base_path', 'type': 'browsepath',
            'value': config['data_saving']['h5file']['save_path'], 'filetype': False, 'readonly': True, },
        {'title': 'Base name:', 'name': 'base_name', 'type': 'str', 'value': 'Scan', 'readonly': True},
        {'title': 'Current scan:', 'name': 'current_scan_name', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Current path:', 'name': 'current_scan_path', 'type': 'text',
            'value': config['data_saving']['h5file']['save_path'], 'readonly': True, 'visible': False},
        {'title': 'h5file:', 'name': 'current_h5_file', 'type': 'text', 'value': '', 'readonly': True},
        {'title': 'New file', 'name': 'new_file', 'type': 'action'},
        {'title': 'Saving dynamic', 'name': 'dynamic', 'type': 'list', 'values': ['uint8', 'int8',
                                                                                  'uint16', 'int16',
                                                                                  'uint32', 'int32',
                                                                                  'uint64', 'int64',
                                                                                  'float64'],
         'value': 'float64'},
        {'title': 'Compression options:', 'name': 'compression_options', 'type': 'group', 'children': [
            {'title': 'Compression library:', 'name': 'h5comp_library', 'type': 'list', 'value': 'zlib',
                'values': ['zlib', 'gzip']},
            {'title': 'Compression level:', 'name': 'h5comp_level', 'type': 'int',
                'value': config['data_saving']['h5file']['compression_level'], 'min': 0, 'max': 9},
        ]},
    ]

    def __init__(self, save_type='scan', backend='tables'):
        """

        Parameters
        ----------
        save_type (str): one of ['scan', 'detector', 'logger', 'custom']
        backend (str): either 'tables' for pytables backend, 'h5py' for h5py backends or 'h5pyd' for HSDS backend

        See Also
        --------
        https://github.com/HDFGroup/hsds
        """
        H5Backend.__init__(self, backend)
        if save_type not in save_types:
            raise InvalidSave('Invalid saving type')

        self.h5_file_path = None
        self.h5_file_name = None
        self.logger_array = None
        self.file_loaded = False

        self.current_group = None
        self.current_scan_group = None
        self.current_scan_name = None
        self.raw_group = None

        self.settings = Parameter.create(title='Saving settings', name='save_settings', type='group',
                                         children=self.params)
        self.settings.child(('save_type')).setValue(save_type)

        # self.settings.child('saving_options', 'save_independent').show(save_type == 'scan')
        # self.settings.child('saving_options', 'do_save').show(not save_type == 'scan')
        # self.settings.child('saving_options', 'current_scan_name').show(save_type == 'scan')

        self.settings.sigTreeStateChanged.connect(
            self.parameter_tree_changed)  # any changes on the settings will update accordingly the detector

    @property
    def h5_file(self):
        return self._h5file


    def init_file(self, update_h5=False, custom_naming=False, addhoc_file_path=None, metadata=dict([]),
                  raw_group_name='Raw_datas'):
        """Initializes a new h5 file.
        Could set the h5_file attributes as:

        * a file with a name following a template if ``custom_naming`` is ``False`` and ``addhoc_file_path`` is ``None``
        * a file within a name set using a file dialog popup if ``custom_naming`` is ``True``
        * a file with a custom name if ``addhoc_file_path`` is a ``Path`` object or a path string

        Parameters
        ----------
        update_h5: bool
                   create a new h5 file with name specified by other parameters
                   if false try to open an existing file and will append new data to it
        custom_naming: bool
                       if True, a selection file dialog opens to set a new file name
        addhoc_file_path: Path or str
                          supplied name by the user for the new file
        metadata: dict
                    dictionnary with pair of key, value that should be saved as attributes of the root group
        Returns
        -------
        update_h5: bool
                   True if new file has been created, False otherwise
        """
        datetime_now = datetime.datetime.now()

        if addhoc_file_path is None:
            if not os.path.isdir(self.settings.child(('base_path')).value()):
                os.mkdir(self.settings.child(('base_path')).value())

            # set the filename and path
            base_name = self.settings.child(('base_name')).value()

            if not custom_naming:
                custom_naming = self.settings.child(('custom_name')).value()

            if not custom_naming:
                scan_type = self.settings.child(('save_type')).value() == 'scan'
                scan_path, current_scan_name, save_path = self.update_file_paths(update_h5)
                self.current_scan_name = current_scan_name
                self.settings.child(('current_scan_name')).setValue(current_scan_name)
                self.settings.child(('current_scan_path')).setValue(str(scan_path))

                if not scan_type:
                    self.h5_file_path = save_path.parent  # will remove the dataset part used for DAQ_scan datas
                    self.h5_file_name = base_name + datetime_now.strftime('_%Y%m%d_%H_%M_%S.h5')
                else:
                    self.h5_file_name = save_path.name + ".h5"
                    self.h5_file_path = save_path.parent

            else:
                self.h5_file_name = select_file(start_path=base_name, save=True, ext='h5')
                self.h5_file_path = self.h5_file_name.parent

        else:
            if isinstance(addhoc_file_path, str):
                addhoc_file_path = Path(addhoc_file_path)
            self.h5_file_path = addhoc_file_path.parent
            self.h5_file_name = addhoc_file_path.name

        fullpathname = str(self.h5_file_path.joinpath(self.h5_file_name))
        self.settings.child(('current_h5_file')).setValue(fullpathname)

        if update_h5:
            self.current_scan_group = None

        scan_group = None
        if self.current_scan_group is not None:
            scan_group = self.get_node_name(self.current_scan_group)

        if update_h5:
            self.close_file()
            self.open_file(fullpathname, 'w', title='PyMoDAQ file')

        else:
            self.close_file()
            self.open_file(fullpathname, 'a', title='PyMoDAQ file')

        self.raw_group = self.get_set_group(self.root(), raw_group_name, title='Data from PyMoDAQ modules')
        self.get_set_logger(self.raw_group)

        if scan_group is not None:
            self.current_scan_group = self.get_set_group(self.raw_group, scan_group)
        else:
            self.current_scan_group = self.get_last_scan()

        self.raw_group.attrs['type'] = self.settings.child(
            ('save_type')).value()  # first possibility to set a node attribute
        self.root().set_attr('file', self.h5_file_name)  # second possibility
        if update_h5:
            self.set_attr(self.root(), 'date', datetime_now.date().isoformat())
            self.set_attr(self.root(), 'time', datetime_now.time().isoformat())
            for metadat in metadata:
                self.raw_group.attrs[metadat] = metadata[metadat]
        return update_h5

    def add_scan_group(self, title='', settings_as_xml='', metadata=dict([])):
        """
        Add a new group of type scan
        See Also
        -------
        add_incremental_group
        """
        if self.current_scan_group is not None:
            if len(self.get_children(self.current_scan_group)) == 0:
                new_scan = False
            else:
                new_scan = True
        else:
            new_scan = True
        if new_scan:
            self.current_scan_group = self.add_incremental_group('scan', self.raw_group, title, settings_as_xml,
                                                                 metadata)
            self.set_attr(self.current_scan_group, 'description', '')
            self.settings.child(('current_scan_name')).setValue(self.get_node_name(self.current_scan_group))

        return self.current_scan_group

    def update_file_paths(self, update_h5=False):
        """

        Parameters
        ----------
        update_h5: bool
                   if True, will increment the file name and eventually the current scan index
                   if False, get the current scan index in the h5 file

        Returns
        -------
        scan_path: Path
        current_filename: str
        dataset_path: Path

        """

        try:
            # set the filename and path
            base_path = self.settings.child(('base_path')).value()
            base_name = self.settings.child(('base_name')).value()
            current_scan = self.settings.child(('current_scan_name')).value()
            scan_type = self.settings.child(('save_type')).value() == 'scan'
            ind_dataset = None
            if current_scan == '' or update_h5:
                next_scan_index = 0
                update_h5 = True  # just started the main program so one should create a new h5
                self.file_loaded = False
            else:
                next_scan_index = self.get_scan_index()
            if self.file_loaded:
                ind_dataset = int(os.path.splitext(self.h5_file_name)[0][-3:])
                try:
                    curr_date = datetime.date.fromisoformat(self.get_attr(self.root(), 'date'))
                except ValueError:
                    curr_date = parser.parse(self.get_attr(self.root(), 'date')).date()
            else:
                curr_date = datetime.date.today()

            scan_path, current_filename, dataset_path = self.set_current_scan_path(base_path, base_name, update_h5,
                                                                                   next_scan_index,
                                                                                   create_dataset_folder=False,
                                                                                   curr_date=curr_date,
                                                                                   ind_dataset=ind_dataset)
            self.settings.child(('current_scan_path')).setValue(str(dataset_path))

            return scan_path, current_filename, dataset_path

        except Exception as e:
            logger.exception(str(e))

    @classmethod
    def find_part_in_path_and_subpath(cls, base_dir, part='', create=False, increment=True):
        """
        Find path from part time.

        =============== ============ =============================================
        **Parameters**  **Type**      **Description**
        *base_dir*      Path object   The directory to browse
        *part*          string        The date of the directory to find/create
        *create*        boolean       Indicate the creation flag of the directory
        =============== ============ =============================================

        Returns
        -------
        Path object
            found path from part
        """
        found_path = None
        if part in base_dir.parts:  # check if current year is in the given base path
            if base_dir.name == part:
                found_path = base_dir
            else:
                for ind in range(len(base_dir.parts)):
                    tmp_path = base_dir.parents[ind]
                    if tmp_path.name == part:
                        found_path = base_dir.parents[ind]
                        break
        else:  # if not check if year is in the subfolders
            subfolders_year_name = [x.name for x in base_dir.iterdir() if x.is_dir()]
            subfolders_found_path = [x for x in base_dir.iterdir() if x.is_dir()]
            if part not in subfolders_year_name:
                if increment:
                    found_path = base_dir.joinpath(part)
                else:
                    found_path = base_dir
                if create:
                    found_path.mkdir()
            else:
                ind_path = subfolders_year_name.index(part)
                found_path = subfolders_found_path[ind_path]
        return found_path

    @classmethod
    def set_current_scan_path(cls, base_dir, base_name='Scan', update_h5=False, next_scan_index=0,
                              create_scan_folder=False,
                              create_dataset_folder=True, curr_date=None, ind_dataset=None):
        """

        Parameters
        ----------
        base_dir
        base_name
        update_h5
        next_scan_index
        create_scan_folder
        create_dataset_folder

        Returns
        -------

        """
        base_dir = Path(base_dir)
        if curr_date is None:
            curr_date = datetime.date.today()

        year_path = cls.find_part_in_path_and_subpath(base_dir, part=str(curr_date.year),
                                                      create=True)  # create directory of the year if it doen't exist and return it
        day_path = cls.find_part_in_path_and_subpath(year_path, part=curr_date.strftime('%Y%m%d'),
                                                     create=True)  # create directory of the day if it doen't exist and return it
        dataset_base_name = curr_date.strftime('Dataset_%Y%m%d')
        dataset_paths = sorted([path for path in day_path.glob(dataset_base_name + "*"+".h5") if path.is_file()])

        if ind_dataset is None:
            if dataset_paths == []:

                ind_dataset = 0
            else:
                if update_h5:
                    ind_dataset = int(dataset_paths[-1].stem.partition(dataset_base_name + "_")[2]) + 1
                else:
                    ind_dataset = int(dataset_paths[-1].stem.partition(dataset_base_name + "_")[2])

        dataset_path = cls.find_part_in_path_and_subpath(day_path,
                                                         part=dataset_base_name + "_{:03d}".format(ind_dataset),
                                                         create=False, increment=True)
        scan_paths = sorted([path for path in dataset_path.glob(base_name + '*') if path.is_dir()])
        # if scan_paths==[]:
        #     ind_scan=0
        # else:
        #     if list(scan_paths[-1].iterdir())==[]:
        #         ind_scan=int(scan_paths[-1].name.partition(base_name)[2])
        #     else:
        #         ind_scan=int(scan_paths[-1].name.partition(base_name)[2])+1
        ind_scan = next_scan_index
        #
        # scan_path = cls.find_part_in_path_and_subpath(dataset_path, part=base_name + '{:03d}'.format(ind_scan),
        #                                               create=create_scan_folder)
        scan_path = ''
        return dataset_path, base_name + '{:03d}'.format(ind_scan), dataset_path

    def get_last_scan(self):
        """Gets the last scan node within the h5_file and under the the **raw_group**

        Returns
        -------
        scan_group: pytables group or None


        """
        groups = [group for group in list(self.get_children(self.raw_group)) if 'Scan' in group]
        groups.sort()
        if len(groups) != 0:
            scan_group = self.get_node(self.raw_group, groups[-1])
        else:
            scan_group = None
        return scan_group

    def get_scan_index(self):
        """ return the scan group index in the "scan templating": Scan000, Scan001 as an integer
        """
        try:
            if self.current_scan_group is None:
                return 0
            else:

                groups = [group for group in self.get_children(self.raw_group) if 'Scan' in group]
                groups.sort()
                flag = False
                if len(groups) != 0:
                    if 'scan_done' in self.get_attr(self.get_node(self.raw_group, groups[-1])):
                        if self.get_attr(self.get_node(self.raw_group, groups[-1]), 'scan_done'):
                            return len(groups)
                        return len(groups) - 1
                    return len(groups) - 1
                return 0

        except Exception as e:
            logger.exception(str(e))

    def load_file(self, base_path=None, file_path=None):
        """Opens a file dialog to select a h5file saved on disk to be used

        Parameters
        ----------
        base_path
        file_path

        See Also
        --------
        :py:meth:`init_file`

        """
        if base_path is None:
            base_path = self.settings.child('base_path').value()
            if not os.path.isdir(base_path):
                base_path = None

        if file_path is None:
            file_path = select_file(base_path, save=False, ext='h5')

        if not (file_path is None or file_path == ''):
            if not isinstance(file_path, Path):
                file_path = Path(file_path)

            if 'h5' not in file_path.suffix:
                raise IOError('Invalid file type, should be a h5 file')

            self.init_file(addhoc_file_path=file_path)
            self.file_loaded = True

    def save_file(self, filename=None):
        if filename is None:
            filename = select_file(None, save=True, ext='h5')
        if filename != '':
            super().save_file_as(filename)

    def get_set_logger(self, where):
        """ Retrieve or create (if absent) a logger enlargeable array to store logs
        Get attributed to the class attribute ``logger_array``
        Parameters
        ----------
        where: node
               location within the tree where to save or retrieve the array

        Returns
        -------
        logger_array: vlarray
                      enlargeable array accepting strings as elements
        """
        if isinstance(where, Node):
            where = where.node
        logger = 'Logger'
        if logger not in list(self.get_children(where)):
            # check if logger node exist
            self.logger_array = self.add_string_array(where, logger)
            self.logger_array.attrs['type'] = 'log'
        else:
            self.logger_array = self.get_node(where, name=logger)
        return self.logger_array

    def add_log(self, msg):
        self.logger_array.append(msg)

    def add_data_group(self, where, group_data_type, title='', settings_as_xml='', metadata=dict([])):
        """Creates a group node at given location in the tree

        Parameters
        ----------
        where: group node
               where to create data group
        group_data_type: list of str
                         either ['data0D', 'data1D', 'data2D', 'dataND']
        title: str, optional
               a title for this node, will be saved as metadata
        settings_as_xml: str, optional
                         XML string created from a Parameter object to be saved as metadata
        metadata: dict, optional
                  will be saved as a new metadata attribute with name: key and value: dict value

        Returns
        -------
        group: group node

        See Also
        --------
        :py:meth:`àdd_group`
        """
        if group_data_type not in group_data_types:
            raise InvalidGroupDataType('Invalid data group type')
        metadata.update(settings=settings_as_xml)
        group = self.add_group(group_data_type, '', where, title, metadata)
        return group

    def add_navigation_axis(self, data, parent_group, axis='x_axis', enlargeable=False, title='', metadata=dict([])):
        """
        Create carray or earray for navigation axis within a scan
        Parameters
        ----------
        data: (ndarray) of dimension 1
        parent_group: (str or node) parent node where to save new data
        axis: (str) either x_axis, y_axis, z_axis or time_axis. 'x_axis', 'y_axis', 'z_axis', 'time_axis' are axes containing scalar values (floats or ints). 'time_axis' can be interpreted as the posix timestamp corresponding to a datetime object, see datetime.timestamp()
        enlargeable: (bool) if True the created array is a earray type if False the created array is a carray type
        """

        if axis not in ['x_axis', 'y_axis', 'z_axis', 'time_axis']:
            if 'axis' not in axis:  # this take care of the case of sequential scans where axes are labelled with indexes
                raise NameError('Invalid navigation axis name')

        array = self.add_array(parent_group, f"{self.settings.child(('save_type')).value()}_{axis}", 'navigation_axis',
                               data_shape=data.shape,
                               data_dimension='1D', array_to_save=data, enlargeable=enlargeable, title=title,
                               metadata=metadata)
        return array

    def add_data_live_scan(self, channel_group, data_dict, scan_type='scan1D', title='', scan_subtype=''):
        isadaptive = scan_subtype == 'Adaptive'
        if not isadaptive:
            shape, dimension, size = utils.get_data_dimension(data_dict['data'], scan_type=scan_type,
                                                              remove_scan_dimension=True)
        else:
            shape, dimension, size = data_dict['data'].shape, '0D', 1
        data_array = self.add_array(channel_group, 'Data', 'data', array_type=np.float,
                                    title=title,
                                    data_shape=shape,
                                    data_dimension=dimension, scan_type=scan_type,
                                    scan_subtype=scan_subtype,
                                    array_to_save=data_dict['data'])
        if 'x_axis' in data_dict:
            if not isinstance(data_dict['x_axis'], dict):
                array_to_save = data_dict['x_axis']
                tmp_dict = dict(label='', units='')
            else:
                tmp_dict = copy.deepcopy(data_dict['x_axis'])
                array_to_save = tmp_dict.pop('data')
            self.add_array(channel_group, 'x_axis', 'axis',
                           array_type=np.float, array_to_save=array_to_save,
                           enlargeable=False, data_dimension='1D', metadata=tmp_dict)
        if 'y_axis' in data_dict:
            if not isinstance(data_dict['y_axis'], dict):
                array_to_save = data_dict['y_axis']
                tmp_dict = dict(label='', units='')
            else:
                tmp_dict = copy.deepcopy(data_dict['y_axis'])
                array_to_save = tmp_dict.pop('data')
            self.add_array(channel_group, 'y_axis', 'axis',
                           array_type=np.float, array_to_save=array_to_save,
                           enlargeable=False, data_dimension='1D', metadata=tmp_dict)
        return data_array

    def add_data(self, channel_group, data_dict, scan_type='scan1D', scan_subtype='',
                 scan_shape=[], title='', enlargeable=False,
                 init=False, add_scan_dim=False, metadata=dict([])):
        """save data within the hdf5 file together with axes data (if any) and metadata, node name will be 'Data'

        Parameters
        ----------
        channel_group: (hdf5 node) node where to save the array, in general within a channel type group
        data_dict: (dict) dictionnary containing the data to save and all the axis and metadata mandatory key: 'data':
         (ndarray) data to save other keys: 'xxx_axis' (for instance x_axis, y_axis, 'nav_x_axis'....) or background
        scan_type: (str) either '', 'scan1D' or 'scan2D' or Tabular or sequential
        scan_subtype: (str) see scanner module
        scan_shape: (iterable) the shape of the scan dimensions
        title: (str) the title attribute of the array node
        enlargeable: (bool) if False, data are save as a CARRAY, otherwise as a EARRAY (for ragged data, see add_sting_array)
        init: (bool) if True, the array saved in the h5 file is initialized with the correct type but all element equal
                     to zero. Else, the 'data' key of data_dict is saved as is
        add_scan_dim: (bool) if True, the scan axes dimension (scan_shape iterable) is prepended to the array shape on the hdf5
                      In that case, the array is usually initialized as zero and further populated
        metadata: (dict) dictionnary whose keys will be saved as the array attributes


        Returns
        -------
        array (CARRAY or EARRAY)

        See Also
        --------
        add_array, add_string_array
        """

        shape, dimension, size = utils.get_data_dimension(data_dict['data'])
        tmp_data_dict = copy.deepcopy(data_dict)
        array_type = getattr(np, self.settings.child('dynamic').value())
        # save axis
        # this loop covers all type of axis : x_axis, y_axis... nav_x_axis, ...
        axis_keys = [k for k in tmp_data_dict.keys() if 'axis' in k]
        for key in axis_keys:
            if not isinstance(tmp_data_dict[key], dict):
                array_to_save = tmp_data_dict[key]
                tmp_dict = dict(label='', units='')
            else:
                tmp_dict = copy.deepcopy(tmp_data_dict[key])
                array_to_save = tmp_dict.pop('data')
                tmp_data_dict.pop(key)

            self.add_array(channel_group, key, 'axis', array_type=None, array_to_save=array_to_save,
                           enlargeable=False, data_dimension='1D', metadata=tmp_dict)

        array_to_save = tmp_data_dict.pop('data')
        if 'type' in tmp_data_dict:
            tmp_data_dict.pop('type')  # otherwise this metadata would overide mandatory attribute 'type' for a h5 node

        if 'bkg' in tmp_data_dict:
            bkg = tmp_data_dict.pop('bkg')
            self.add_array(channel_group, 'Bkg', 'bkg', array_type=array_type, array_to_save=bkg,
                           data_dimension=dimension)
        tmp_data_dict.update(metadata)
        array_to_save = array_to_save.astype(array_type)
        data_array = self.add_array(channel_group, 'Data', 'data', array_type=array_type,
                                    title=title, data_shape=shape, enlargeable=enlargeable, data_dimension=dimension,
                                    scan_type=scan_type, scan_subtype=scan_subtype, scan_shape=scan_shape,
                                    array_to_save=array_to_save,
                                    init=init, add_scan_dim=add_scan_dim, metadata=tmp_data_dict)


        self.flush()
        return data_array

    def add_array(self, where, name, data_type, data_shape=None, data_dimension=None, scan_type='', scan_subtype='',
                  scan_shape=[],
                  title='', array_to_save=None, array_type=None, enlargeable=False, metadata=dict([]),
                  init=False, add_scan_dim=False):
        """save data arrays on the hdf5 file together with metadata
        Parameters
        ----------
        where: (hdf5 node) node where to save the array
        name: (str) name of the array in the hdf5 file
        data_type: (str) one of ['data', 'axis', 'live_scan', 'navigation_axis', 'external_h5', 'strings', 'bkg'], mandatory
            so that the h5Browsr interpret correctly the array (see add_data)
        data_shape: (iterable) the shape of the array to save, mandatory if array_to_save is None
        data_dimension: (str) one of ['0D', '1D', '2D', 'ND']
        scan_type: (str) either '', 'scan1D' or 'scan2D'
        scan_shape: (iterable): the shape of the scan dimensions
        title: (str) the title attribute of the array node
        array_to_save: (ndarray or None) data to be saved in the array. If None, array_type and data_shape
                        should be specified
        array_type: (np.dtype or numpy types), eg np.float, np.int32 ...
        enlargeable: (bool) if False, data are save as a CARRAY, otherwise as a EARRAY (for ragged data, see add_sting_array)
        metadata: (dict) dictionnary whose keys will be saved as the array attributes
        init: (bool) if True, the array saved in the h5 file is initialized with the correct type but all element equal
                     to zero. Else, the 'data' key of data_dict is saved as is
        add_scan_dim: if True, the scan axes dimension (scan_shape iterable) is prepended to the array shape on the hdf5
                      In that case, the array is usually initialized as zero and further populated

        Returns
        -------
        array (CARRAY or EARRAY)

        See Also
        --------
        add_data, add_string_array
        """
        if array_type is None:
            if array_to_save is None:
                array_type = getattr(np, self.settings.child('dynamic').value())
            else:
                array_type = array_to_save.dtype

        if data_dimension not in data_dimensions:
            raise InvalidDataDimension('Invalid data dimension')
        if data_type not in data_types:
            raise InvalidDataType('Invalid data type')
        if scan_type != '':
            scan_type = utils.uncapitalize(scan_type)
        if scan_type.lower() not in [s.lower() for s in scan_types]:
            raise InvalidScanType('Invalid scan type')
        if enlargeable:
            if data_shape == (1,):
                data_shape = None
            array = self.create_earray(where, utils.capitalize(name), dtype=np.dtype(array_type),
                                       data_shape=data_shape, title=title)
        else:
            if add_scan_dim:  # means it is an array initialization to zero
                shape = list(scan_shape[:])
                shape.extend(data_shape)
                if init or array_to_save is None:
                    array_to_save = np.zeros(shape, dtype=np.dtype(array_type))

            array = self.create_carray(where, utils.capitalize(name), obj=array_to_save, title=title)
        self.set_attr(array, 'type', data_type)
        self.set_attr(array, 'data_dimension', data_dimension)
        self.set_attr(array, 'scan_type', scan_type)
        self.set_attr(array, 'scan_subtype', scan_subtype)

        for metadat in metadata:
            self.set_attr(array, metadat, metadata[metadat])
        return array

    def add_string_array(self, where, name, title='', metadata=dict([])):
        array = self.create_vlarray(where, name, dtype='string', title=title)
        array.attrs['shape'] = (0,)
        array.attrs['data_dimension'] = '0D'
        array.attrs['scan_type'] = 'scan1D'

        for metadat in metadata:
            array.attrs[metadat] = metadata[metadat]
        return array

    def get_set_group(self, where, name, title=''):
        self.current_group = super().get_set_group(where, name, title)
        return self.current_group

    def add_incremental_group(self, group_type, where, title='', settings_as_xml='', metadata=dict([])):
        """
        Add a node in the h5 file tree of the group type with an increment in the given name
        Parameters
        ----------
        group_type: (str) one of the possible values of **group_types**
        where: (str or node) parent node where to create the new group
        title: (str) node title
        settings_as_xml: (str) XML string containing Parameters representation (see custom_Tree)
        metadata: (dict) extra metadata to be saved with this new group node

        Returns
        -------
        (node): newly created group node
        """
        if group_type not in group_types:
            raise InvalidGroupType('Invalid group type')
        nodes = [name for name in self.get_children(self.get_node(where))]
        nodes_tmp = []
        for node in nodes:
            if utils.capitalize(group_type) in node:
                nodes_tmp.append(node)
        nodes_tmp.sort()
        if len(nodes_tmp) == 0:
            ind_group = -1
        else:
            ind_group = int(nodes_tmp[-1][-3:])
        group = self.get_set_group(where, utils.capitalize(group_type) + '{:03d}'.format(ind_group + 1), title)
        self.set_attr(group, 'settings', settings_as_xml)
        if group_type.lower() != 'ch':
            self.set_attr(group, 'type', group_type.lower())
        else:
            self.set_attr(group, 'type', '')
        for metadat in metadata:
            self.set_attr(group, metadat, metadata[metadat])
        return group

    def add_det_group(self, where, title='', settings_as_xml='', metadata=dict([])):
        """
        Add a new group of type detector
        See Also
        -------
        add_incremental_group
        """
        group = self.add_incremental_group('detector', where, title, settings_as_xml, metadata)
        return group

    def add_CH_group(self, where, title='', settings_as_xml='', metadata=dict([])):
        """
        Add a new group of type channel
        See Also
        -------
        add_incremental_group
        """
        group = self.add_incremental_group('ch', where, title, settings_as_xml, metadata)
        return group

    def add_live_scan_group(self, where, dimensionality, title='', settings_as_xml='', metadata=dict([])):
        """
        Add a new group of type live scan
        See Also
        -------
        add_incremental_group
        """
        metadata.update(settings=settings_as_xml)
        group = self.add_group(utils.capitalize('Live_scan_{:s}'.format(dimensionality)), '', where, title=title,
                               metadata=metadata)
        return group

    def add_move_group(self, where, title='', settings_as_xml='', metadata=dict([])):
        """
        Add a new group of type move
        See Also
        -------
        add_incremental_group
        """
        group = self.add_incremental_group('move', where, title, settings_as_xml, metadata)
        return group

    def parameter_tree_changed(self, param, changes):
        for param, change, data in changes:
            path = self.settings.childPath(param)

            if change == 'childAdded':
                pass

            elif change == 'value':
                if param.name() == 'show_file':
                    param.setValue(False)
                    self.show_file_content()

                elif param.name() == 'base_path':
                    try:
                        if not os.path.isdir(param.value()):
                            os.mkdir(param.value())
                    except Exception as e:
                        logger.warning(f"The base path couldn't be set, please check your options: {str(e)}")
                        self.update_status("The base path couldn't be set, please check your options")

                elif param.name() in putils.iter_children(self.settings.child('compression_options'), []):
                    compression = self.settings.child('compression_options', 'h5comp_library').value()
                    compression_opts = self.settings.child('compression_options', 'h5comp_level').value()
                    self.define_compression(compression, compression_opts)

            elif change == 'parent':
                pass

    def update_status(self, status):
        #self.status_sig.emit(utils.ThreadCommand("Update_Status", [status, 'log']))
        #logger.info(status)
        pass

    def show_file_content(self):
        form = QtWidgets.QWidget()
        if not self.isopen():
            if self.h5_file_path is not None:
                if self.h5_file_path.exists():
                    self.analysis_prog = H5Browser(form, h5file_path=self.h5_file_path)
                else:
                    logger.warning('The h5 file path has not been defined yet')
            else:
                logger.warning('The h5 file path has not been defined yet')
        else:
            self.flush()
            self.analysis_prog = H5Browser(form, h5file=self.h5file)
        form.show()


class H5Saver(H5SaverBase, QObject):
    """
    status_sig: pyqtSignal
                emits a signal of type Threadcommand in order to senf log information to a main UI
    new_file_sig: pyqtSignal
                  emits a boolean signal to let the program know when the user pressed the new file button on the UI
    """

    status_sig = pyqtSignal(utils.ThreadCommand)
    new_file_sig = pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        QObject.__init__(self)
        H5SaverBase.__init__(self, *args, **kwargs)

        self.settings_tree = ParameterTree()
        self.settings_tree.setMinimumHeight(310)
        self.settings_tree.setParameters(self.settings, showTop=False)
        self.settings.child(('new_file')).sigActivated.connect(lambda: self.emit_new_file(True))

    def emit_new_file(self, status):
        """Emits the new_file_sig

        Parameters
        ----------
        status: bool
                emits True if a new file has been asked by the user pressing the new file button on the UI
        """
        self.new_file_sig.emit(status)


def find_scan_node(scan_node):
    """
    utility function to find the parent node of "scan" type, meaning some of its children (DAQ_scan case)
    or co-nodes (daq_logger case) are navigation axes
    Parameters
    ----------
    scan_node: (pytables node)
        data node from where this function look for its navigation axes if any
    Returns
    -------
    node: the parent node of 'scan' type
    list: the data nodes of type 'navigation_axis' corresponding to the initial data node


    """
    try:
        while True:
            if scan_node.attrs['type'] == 'scan':
                break
            else:
                scan_node = scan_node.parent_node
        children = list(scan_node.children().values())  # for data saved using daq_scan
        children.extend([scan_node.parent_node.children()[child] for child in
                         scan_node.parent_node.children_name()])  # for data saved using the daq_logger
        nav_children = []
        for child in children:
            if 'type' in child.attrs.attrs_name:
                if child.attrs['type'] == 'navigation_axis':
                    nav_children.append(child)
        return scan_node, nav_children
    except Exception:
        return None, []


class H5BrowserUtil(H5Backend):
    def __init__(self, backend='tables'):
        super().__init__(backend=backend)

    def export_data(self, node_path='/', filesavename='datafile.txt'):
        if filesavename != '':
            node = self.get_node(node_path)
            if 'ARRAY' in node.attrs['CLASS']:
                data = node.read()
                if not isinstance(data, np.ndarray):
                    # in case one has a list of same objects (array of strings for instance, logger or other)
                    data = np.array(data)
                    np.savetxt(filesavename, data, '%s', '\t')
                else:
                    np.savetxt(filesavename, data, '%.6e', '\t')

            elif 'GROUP' in node.attrs['CLASS']:
                data_tot = []
                header = []
                dtypes = []
                fmts = []
                for subnode_name, subnode in node.children().items():
                    if 'ARRAY' in subnode.attrs['CLASS']:
                        if len(subnode.attrs['shape']) == 1:
                            data = subnode.read()
                            if not isinstance(data, np.ndarray):
                                # in case one has a list of same objects (array of strings for instance, logger or other)
                                data = np.array(data)
                            data_tot.append(data)
                            dtypes.append((subnode_name, data.dtype))
                            header.append(subnode_name)
                            if data.dtype.char == 'U':
                                fmt = '%s'  # for strings
                            elif data.dtype.char == 'l':
                                fmt = '%d'  # for integers
                            else:
                                fmt = '%.6f'  # for decimal numbers
                            fmts.append(fmt)

                data_trans = np.array(list(zip(*data_tot)), dtype=dtypes)
                np.savetxt(filesavename, data_trans, fmts, '\t', header='#' + '\t'.join(header))

    def get_h5file_scans(self, where='/'):
        # TODO add a test for this method
        scan_list = []
        where = self.get_node(where)
        for node in self.walk_nodes(where):
            if 'pixmap2D' in node.attrs.attrs_name:
                scan_list.append(
                    dict(scan_name='{:s}_{:s}'.format(node.parent_node.name, node.name), path=node.path,
                         data=node.attrs['pixmap2D']))

        return scan_list

    def get_h5_attributes(self, node_path):
        """

        """

        node = self.get_node(node_path)
        attrs_names = node.attrs.attrs_name
        attr_dict = OrderedDict([])
        for attr in attrs_names:
            # if attr!='settings':
            attr_dict[attr] = node.attrs[attr]

        settings = None
        scan_settings = None
        if 'settings' in attrs_names:
            if node.attrs['settings'] != '':
                settings = node.attrs['settings']

        if 'scan_settings' in attrs_names:
            if node.attrs['scan_settings'] != '':
                scan_settings = node.attrs['scan_settings']
        pixmaps = []
        for attr in attrs_names:
            if 'pixmap' in attr:
                pixmaps.append(node.attrs[attr])

        return attr_dict, settings, scan_settings, pixmaps

    def get_h5_data(self, node_path):
        """
        """
        node = self.get_node(node_path)
        is_spread = False
        if 'ARRAY' in node.attrs['CLASS']:
            data = node.read()
            nav_axes = []
            axes = dict([])
            if isinstance(data, np.ndarray):
                data = np.squeeze(data)
                if 'Bkg' in node.parent_node.children_name() and node.name != 'Bkg':
                    bkg = np.squeeze(self.get_node(node.parent_node.path, 'Bkg').read())
                    try:
                        data = data - bkg
                    except:
                        logger.warning(f'Could not substract bkg from data node {node_path} as their shape are '
                                       f'incoherent {bkg.shape} and {data.shape}')
                if 'type' in node.attrs.attrs_name:
                    if 'data' in node.attrs['type'] or 'channel' in node.attrs['type'].lower():
                        parent_path = node.parent_node.path
                        children = node.parent_node.children_name()

                        if 'data_dimension' not in node.attrs.attrs_name:  # for backcompatibility
                            data_dim = node.attrs['data_type']
                        else:
                            data_dim = node.attrs['data_dimension']
                        if 'scan_subtype' in node.attrs.attrs_name:
                            if node.attrs['scan_subtype'].lower() == 'adaptive':
                                is_spread = True
                        tmp_axes = ['x_axis', 'y_axis']
                        for ax in tmp_axes:
                            if capitalize(ax) in children:
                                axis_node = self.get_node(parent_path + '/{:s}'.format(capitalize(ax)))
                                axes[ax] = Axis(data=axis_node.read())
                                if 'units' in axis_node.attrs.attrs_name:
                                    axes[ax]['units'] = axis_node.attrs['units']
                                if 'label' in axis_node.attrs.attrs_name:
                                    axes[ax]['label'] = axis_node.attrs['label']
                            else:
                                axes[ax] = Axis()

                        if data_dim == 'ND':  # check for navigation axis
                            tmp_nav_axes = ['y_axis', 'x_axis', ]
                            nav_axes = []
                            for ind_ax, ax in enumerate(tmp_nav_axes):
                                if 'Nav_{:s}'.format(ax) in children:
                                    nav_axes.append(ind_ax)
                                    axis_node = self.get_node(parent_path + '/Nav_{:s}'.format(ax))
                                    if is_spread:
                                        axes['nav_{:s}'.format(ax)] = Axis(data=axis_node.read())
                                    else:
                                        axes['nav_{:s}'.format(ax)] = Axis(data=np.unique(axis_node.read()))
                                        if axes['nav_{:s}'.format(ax)]['data'].shape[0] != data.shape[ind_ax]:
                                            # could happen in case of linear back to start type of scan
                                            tmp_ax = []
                                            for ix in axes['nav_{:s}'.format(ax)]['data']:
                                                tmp_ax.extend([ix, ix])
                                                axes['nav_{:s}'.format(ax)] = Axis(data=np.array(tmp_ax))

                                    if 'units' in axis_node.attrs.attrs_name:
                                        axes['nav_{:s}'.format(ax)]['units'] = axis_node.attrs['units']
                                    if 'label' in axis_node.attrs.attrs_name:
                                        axes['nav_{:s}'.format(ax)]['label'] = axis_node.attrs['label']

                        if 'scan_type' in node.attrs.attrs_name:
                            scan_type = node.attrs['scan_type'].lower()
                            # if scan_type == 'scan1d' or scan_type == 'scan2d':
                            scan_node, nav_children = find_scan_node(node)
                            nav_axes = []
                            if scan_type == 'tabular' or is_spread:
                                datas = []
                                labels = []
                                all_units = []
                                for axis_node in nav_children:
                                    npts = axis_node.attrs['shape'][0]
                                    datas.append(axis_node.read())
                                    labels.append(axis_node.attrs['label'])
                                    all_units.append(axis_node.attrs['units'])

                                nav_axes.append(0)
                                axes['nav_x_axis'] = NavAxis(
                                    data=np.linspace(0, npts - 1, npts),
                                    nav_index=nav_axes[-1], units='', label='Scan index', labels=labels,
                                    datas=datas, all_units=all_units)
                            else:
                                for axis_node in nav_children:
                                    nav_axes.append(axis_node.attrs['nav_index'])
                                    if is_spread:
                                        axes[f'nav_{nav_axes[-1]:02d}'] = NavAxis(data=axis_node.read(),
                                                                                  nav_index=nav_axes[-1])
                                    else:
                                        axes[f'nav_{nav_axes[-1]:02d}'] = NavAxis(data=np.unique(axis_node.read()),
                                                                                  nav_index=nav_axes[-1])
                                        if nav_axes[-1] < len(data.shape):
                                            if axes[f'nav_{nav_axes[-1]:02d}'][
                                                    'data'].shape[0] != data.shape[nav_axes[-1]]:
                                                # could happen in case of linear back to start type of scan
                                                tmp_ax = []
                                                for ix in axes[f'nav_{nav_axes[-1]:02d}']['data']:
                                                    tmp_ax.extend([ix, ix])
                                                    axes[f'nav_{nav_axes[-1]:02d}'] = NavAxis(data=np.array(tmp_ax),
                                                                                              nav_index=nav_axes[-1])

                                    if 'units' in axis_node.attrs.attrs_name:
                                        axes[f'nav_{nav_axes[-1]:02d}']['units'] = axis_node.attrs[
                                            'units']
                                    if 'label' in axis_node.attrs.attrs_name:
                                        axes[f'nav_{nav_axes[-1]:02d}']['label'] = axis_node.attrs[
                                            'label']
                    elif 'axis' in node.attrs['type']:
                        axis_node = node
                        axes['y_axis'] = Axis(data=axis_node.read())
                        if 'units' in axis_node.attrs.attrs_name:
                            axes['y_axis']['units'] = axis_node.attrs['units']
                        if 'label' in axis_node.attrs.attrs_name:
                            axes['y_axis']['label'] = axis_node.attrs['label']
                        axes['x_axis'] = Axis(
                            data=np.linspace(0, axis_node.attrs['shape'][0] - 1, axis_node.attrs['shape'][0]),
                            units='pxls',
                            label='')
                return data, axes, nav_axes, is_spread

            elif isinstance(data, list):
                return data, [], [], is_spread


class H5Browser(QObject):
    """UI used to explore h5 files, plot and export subdatas"""
    data_node_signal = pyqtSignal(
        str)  # the path of a node where data should be monitored, displayed...whatever use from the caller
    status_signal = pyqtSignal(str)

    def __init__(self, parent, h5file=None, h5file_path=None, backend='tables'):
        """

        Parameters
        ----------
        parent: QtWidgets container, either a QWidget or a QMainWindow
        h5file: h5file instance (exact type depends on the backend)
        h5file_path: (str or Path) if specified load the corresponding file, otherwise open a select file dialog
        backend: (str) eitre 'tables, 'h5py' or 'h5pyd'

        See Also
        --------
        H5Backend, H5Backend
        """

        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(H5Browser, self).__init__()
        if not (isinstance(parent, QtWidgets.QWidget) or isinstance(parent, QtWidgets.QMainWindow)):
            raise Exception('no valid parent container, expected a QWidget or a QMainWindow')

        if isinstance(parent, QtWidgets.QMainWindow):
            self.main_window = parent
            self.parent = QtWidgets.QWidget()
            self.main_window.setCentralWidget(self.parent)
        else:
            self.main_window = None
            self.parent = parent

        self.backend = backend
        self.current_node_path = None

        # construct the UI interface
        self.ui = QObject()  # the user interface
        self.set_GUI()

        # construct the h5 interface and load the file (or open a select file message)
        self.h5utils = H5BrowserUtil(backend=self.backend)
        if h5file is None:
            if h5file_path is None:
                h5file_path = select_file(save=False, ext=['h5', 'hdf5'])
            if h5file_path != '':
                self.h5utils.open_file(h5file_path, 'a')
            else:
                return
        else:
            self.h5utils.h5file = h5file

        self.check_version()
        self.populate_tree()
        self.ui.h5file_tree.ui.Open_Tree.click()

    def check_version(self):
        if 'pymodaq_version' in self.h5utils.root().attrs.attrs_name:
            if version_mod.parse(self.h5utils.root().attrs['pymodaq_version']) < version_mod.parse('2.0'):
                msgBox = QtWidgets.QMessageBox(parent=None)
                msgBox.setWindowTitle("Invalid version")
                msgBox.setText(f"Your file has been saved using PyMoDAQ "
                               f"version {self.h5utils.root().attrs['pymodaq_version']} "
                               f"while you're using version: {utils.get_version()}\n"
                               f"Please create and use an adapted environment to use this version (up to 1.6.4):\n"
                               f"pip install pymodaq==1.6.4")
                ret = msgBox.exec()
                self.quit_fun()
                if self.main_window is not None:
                    self.main_window.close()
                else:
                    self.parent.close()

    def add_comments(self, status, comment=''):
        try:
            self.current_node_path = self.get_tree_node_path()
            node = self.h5utils.get_node(self.current_node_path)
            if 'comments' in node.attrs.attrs_name:
                tmp = node.attrs['comments']
            else:
                tmp = ''
            if comment == '':
                text, res = QtWidgets.QInputDialog.getMultiLineText(None, 'Enter comments', 'Enter comments here:', tmp)
                if res and text != '':
                    comment = text
                node.attrs['comments'] = comment
            else:
                node.attrs['comments'] = tmp + comment

            self.h5utils.flush()

        except Exception as e:
            logger.exception(str(e))

    def get_tree_node_path(self):
        return self.ui.h5file_tree.ui.Tree.currentItem().text(2)

    def export_data(self):
        try:
            file = select_file(save=True, ext='txt')
            self.current_node_path = self.get_tree_node_path()
            if file != '':
                self.h5utils.export_data(self.current_node_path, str(file))

        except Exception as e:
            logger.exception(str(e))

    def save_file(self, filename=None):
        if filename is None:
            filename = select_file(save=True, ext='txt')
        if filename != '':
            self.h5utils.save_file(filename)

    def quit_fun(self):
        """
        """
        try:
            self.h5utils.close_file()
            if self.main_window is None:
                self.parent.close()
            else:
                self.main_window.close()
        except Exception as e:
            logger.exception(str(e))

    def create_menu(self):
        """

        """
        self.menubar = self.main_window.menuBar()

        # %% create Settings menu
        self.file_menu = self.menubar.addMenu('File')
        load_action = self.file_menu.addAction('Load file')
        load_action.triggered.connect(lambda: self.load_file(None))
        save_action = self.file_menu.addAction('Save file')
        save_action.triggered.connect(self.save_file)
        self.file_menu.addSeparator()
        quit_action = self.file_menu.addAction('Quit')
        quit_action.triggered.connect(self.quit_fun)

        # help menu
        help_menu = self.menubar.addMenu('?')
        action_about = help_menu.addAction('About')
        action_about.triggered.connect(self.show_about)
        action_help = help_menu.addAction('Help')
        action_help.triggered.connect(self.show_help)
        action_help.setShortcut(QtCore.Qt.Key_F1)
        log_action = help_menu.addAction('Show log')
        log_action.triggered.connect(self.show_log)

    def show_about(self):
        splash_path = os.path.join(os.path.split(os.path.split(__file__)[0])[0], 'splash.png')
        splash = QtGui.QPixmap(splash_path)
        self.splash_sc = QtWidgets.QSplashScreen(splash, QtCore.Qt.WindowStaysOnTopHint)
        self.splash_sc.setVisible(True)
        self.splash_sc.showMessage(f"PyMoDAQ version {utils.get_version()}\n"
                                   f"Modular Acquisition with Python\nWritten by Sébastien Weber",
                                   QtCore.Qt.AlignRight, QtCore.Qt.white)

    def show_log(self):
        import webbrowser
        webbrowser.open(logger.handlers[0].baseFilename)

    def show_help(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("http://pymodaq.cnrs.fr"))

    def set_GUI(self):

        if self.main_window is not None:
            self.create_menu()

        layout = QtWidgets.QGridLayout()

        V_splitter = QtWidgets.QSplitter(Qt.Vertical)
        V_splitter2 = QtWidgets.QSplitter(Qt.Vertical)
        H_splitter = QtWidgets.QSplitter(Qt.Horizontal)

        Form = QtWidgets.QWidget()
        # self.ui.h5file_tree = Tree_layout(Form,col_counts=2,labels=["Node",'Pixmap'])
        self.ui.h5file_tree = Tree_layout(Form, col_counts=1, labels=["Node"])
        self.ui.h5file_tree.ui.Tree.setMinimumWidth(300)
        self.ui.h5file_tree.ui.Tree.itemClicked.connect(self.show_h5_attributes)
        self.ui.h5file_tree.ui.Tree.itemDoubleClicked.connect(self.show_h5_data)

        self.export_action = QtWidgets.QAction("Export data as *.txt file", None)
        self.export_action.triggered.connect(self.export_data)
        self.add_comments_action = QtWidgets.QAction("Add comments to this node", None)
        self.add_comments_action.triggered.connect(self.add_comments)
        self.ui.h5file_tree.ui.Tree.addAction(self.export_action)
        self.ui.h5file_tree.ui.Tree.addAction(self.add_comments_action)

        V_splitter.addWidget(Form)
        self.ui.attributes_tree = ParameterTree()
        self.ui.attributes_tree.setMinimumWidth(300)
        V_splitter.addWidget(self.ui.attributes_tree)

        self.settings_raw = Parameter.create(name='Param_raw', type='group')
        self.ui.attributes_tree.setParameters(self.settings_raw, showTop=False)

        H_splitter.addWidget(V_splitter)
        self.pixmap_widget = QtWidgets.QWidget()
        self.pixmap_widget.setMaximumHeight(100)
        V_splitter2.addWidget(self.pixmap_widget)
        self.ui.settings_tree = ParameterTree()
        self.ui.settings_tree.setMinimumWidth(300)
        V_splitter2.addWidget(self.ui.settings_tree)
        self.ui.text_list = QtWidgets.QListWidget()

        V_splitter2.addWidget(self.ui.text_list)

        H_splitter.addWidget(V_splitter2)

        form_viewer = QtWidgets.QWidget()
        self.viewer_area = DockArea()
        self.hyperviewer = ViewerND(self.viewer_area)
        H_splitter.addWidget(self.viewer_area)

        layout.addWidget(H_splitter)
        self.parent.setLayout(layout)

        self.settings = Parameter.create(name='Param', type='group')
        self.ui.settings_tree.setParameters(self.settings, showTop=False)

        self.status_signal.connect(self.add_log)

    def add_log(self, txt):
        logger.info(txt)

    def show_h5_attributes(self, item):
        """

        """
        try:
            self.current_node_path = self.get_tree_node_path()

            attr_dict, settings, scan_settings, pixmaps = self.h5utils.get_h5_attributes(self.current_node_path)

            for child in self.settings_raw.children():
                child.remove()
            params = []
            for attr in attr_dict:
                params.append({'title': attr, 'name': attr, 'type': 'str', 'value': attr_dict[attr], 'readonly': True})
            self.settings_raw.addChildren(params)

            if settings is not None:
                for child in self.settings.children():
                    child.remove()
                QtWidgets.QApplication.processEvents()  # so that the tree associated with settings updates
                params = pymodaq.daq_utils.parameter.ioxml.XML_string_to_parameter(settings)
                self.settings.addChildren(params)

            if scan_settings is not None:
                params = pymodaq.daq_utils.parameter.ioxml.XML_string_to_parameter(scan_settings)
                self.settings.addChildren(params)

            if pixmaps == []:
                self.pixmap_widget.setVisible(False)
            else:
                self.pixmap_widget.setVisible(True)
                self.show_pixmaps(pixmaps)

        except Exception as e:
            logger.exception(str(e))

    def show_pixmaps(self, pixmaps=[]):
        if self.pixmap_widget.layout() is None:
            layout = QtWidgets.QHBoxLayout()
            self.pixmap_widget.setLayout(layout)
        while 1:
            child = self.pixmap_widget.layout().takeAt(0)
            if not child:
                break
            child.widget().deleteLater()
            QtWidgets.QApplication.processEvents()
        labs = []
        for pix in pixmaps:
            labs.append(pngbinary2Qlabel(pix))
            self.pixmap_widget.layout().addWidget(labs[-1])

    def show_h5_data(self, item):
        """
        """
        try:
            self.current_node_path = item.text(2)
            self.show_h5_attributes(item)
            node = self.h5utils.get_node(self.current_node_path)
            self.data_node_signal.emit(self.current_node_path)
            if 'ARRAY' in node.attrs['CLASS']:
                data, axes, nav_axes, is_spread = self.h5utils.get_h5_data(self.current_node_path)
                if isinstance(data, np.ndarray):
                    if 'scan_type' in node.attrs.attrs_name:
                        scan_type = node.attrs['scan_type']
                    else:
                        scan_type = ''
                    self.hyperviewer.show_data(deepcopy(data), nav_axes=nav_axes, is_spread=is_spread,
                                               scan_type=scan_type, **deepcopy(axes))
                    self.hyperviewer.init_ROI()
                elif isinstance(data, list):
                    if not (not data):
                        if isinstance(data[0], str):
                            self.ui.text_list.clear()
                            for txt in data:
                                self.ui.text_list.addItem(txt)
        except Exception as e:
            logger.exception(str(e))

    def populate_tree(self):
        """
            | Init the ui-tree and store data into calling the h5_tree_to_Qtree convertor method

            See Also
            --------
            h5tree_to_QTree, update_status
        """
        try:
            if self.h5utils.h5file is not None:
                self.ui.h5file_tree.ui.Tree.clear()
                base_node = self.h5utils.root()
                base_tree_item, pixmap_items = h5tree_to_QTree(base_node)
                self.ui.h5file_tree.ui.Tree.addTopLevelItem(base_tree_item)
                self.add_widget_totree(pixmap_items)

        except Exception as e:
            logger.exception(str(e))

    def add_widget_totree(self, pixmap_items):

        for item in pixmap_items:
            widget = QtWidgets.QWidget()

            vLayout = QtWidgets.QVBoxLayout()
            label1D = QtWidgets.QLabel()
            bytes = QByteArray(item['node'].attrs['pixmap1D'])
            im1 = QtGui.QImage.fromData(bytes)
            a = QtGui.QPixmap.fromImage(im1)
            label1D.setPixmap(a)

            label2D = QtWidgets.QLabel()
            bytes = QByteArray(item['node'].attrs['pixmap2D'])
            im2 = QtGui.QImage.fromData(bytes)
            b = QtGui.QPixmap.fromImage(im2)
            label2D.setPixmap(b)

            vLayout.addWidget(label1D)
            vLayout.addwidget(label2D)
            widget.setLayout(vLayout)
            self.ui.h5file_tree.ui.Tree.setItemWidget(item['item'], 1, widget)


def browse_data(fname=None, ret_all=False, message=None):
    """
        | Browse data present in any h5 file, when user has selected the one,
    """
    if fname is None:
        fname = str(select_file(start_path=config['data_saving']['h5file']['save_path'], save=False, ext='h5'))

    if type(fname) != str:
        try:
            fname = str(fname)
        except Exception:
            raise Exception('filename in browse data is not valid')
    if fname != '':
        (root, ext) = os.path.splitext(fname)
        if not ('h5' in ext or 'hdf5' in ext):
            warnings.warn('This is not a PyMODAQ h5 file, there could be issues', Warning)

        form = QtWidgets.QWidget()
        browser = H5Browser(form, h5file_path=fname)

        dialog = QtWidgets.QDialog()
        vlayout = QtWidgets.QVBoxLayout()

        vlayout.addWidget(form)
        dialog.setLayout(vlayout)
        buttonBox = QtWidgets.QDialogButtonBox(parent=dialog)

        buttonBox.addButton('OK', buttonBox.AcceptRole)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.addButton('Cancel', buttonBox.RejectRole)
        buttonBox.rejected.connect(dialog.reject)
        vlayout.addWidget(buttonBox)

        dialog.setWindowTitle('Select a data node in the tree')
        if message is None or not isinstance(message, str):
            dialog.setWindowTitle('Select a data node in the tree')
        else:
            dialog.setWindowTitle(message)
        res = dialog.exec()

        if res == dialog.Accepted:
            node_path = browser.current_node_path
            data = browser.h5utils.get_node(node_path).read()
        else:
            data = None
            node_path = None

        browser.h5utils.close_file()

        if ret_all:
            return data, fname, node_path
        else:
            return data
    return None, '', ''


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ H5Browser')
    prog = H5Browser(win)
    win.show()
    QtWidgets.QApplication.processEvents()
    sys.exit(app.exec_())

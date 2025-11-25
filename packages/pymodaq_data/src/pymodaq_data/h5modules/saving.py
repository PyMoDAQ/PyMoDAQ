# -*- coding: utf-8 -*-
"""
Created the 15/11/2022

@author: Sebastien Weber
"""
import copy
import datetime
import enum

from dateutil import parser
from numbers import Number
import os
from pathlib import Path
from typing import Union, Iterable


import numpy as np

from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_utils import utils
from pymodaq_utils.config import Config
from pymodaq_data.data import DataDim, DataToExport, Axis, DataWithAxes
from pymodaq_utils.enums import BaseEnum, enum_checker
from pymodaq_utils.warnings import deprecation_msg


from .backends import (H5Backend, backends_available, SaveType, InvalidSave, InvalidExport,
                       Node, GroupType, InvalidDataDimension, InvalidScanType,
                       GROUP, VLARRAY)
from . import browsing


config = Config()
logger = set_logger(get_module_name(__file__))


class FileType(BaseEnum):
    detector = 0
    actuator = 1
    axis = 2
    scan = 3
    

class DataType(BaseEnum):
    data = 'Data'
    axis = 'Axis'
    live_scan = 'Live'
    external_h5 = 'ExtData'
    strings = 'Strings'
    bkg = 'Bkg'
    data_enlargeable = 'EnlData'
    error = 'ErrorBar'


class H5SaverLowLevel(H5Backend):
    """Object containing basic methods in order to structure and interact with a h5file compatible
    with the h5browser

    See Also
    --------
    H5Browser

    Attributes
    ----------
    h5_file: pytables hdf5 file
        object used to save all datas and metadas
    h5_file_path: str or Path
        The file path
    """

    def __init__(self, save_type: SaveType = 'scan', backend='tables'):
        H5Backend.__init__(self, backend)

        self.save_type = enum_checker(SaveType, save_type)

        self.h5_file_path = None
        self.h5_file_name = None
        self.file_loaded = False

        self._current_group = None
        self._raw_group: Union[GROUP, str] = '/RawData'
        self._logger_array = None

    @property
    def raw_group(self):
        return self._raw_group

    @property
    def h5_file(self):
        return self._h5file

    def init_file(self, file_name: Path, raw_group_name='RawData', new_file=False,
                  metadata: dict = None):
        """Initializes a new h5 file.

        Parameters
        ----------
        file_name: Path
            a complete Path pointing to a h5 file
        raw_group_name: str
            Base node name
        new_file: bool
            If True create a new file, otherwise append to a potential existing one
        metadata: dict
            A dictionary to be saved as attributes

        Returns
        -------
        bool
            True if new file has been created, False otherwise
        """
        datetime_now = datetime.datetime.now()

        if file_name is not None and isinstance(file_name, Path):
            self.h5_file_name = file_name.stem + ".h5"
            self.h5_file_path = file_name.parent
            if not self.h5_file_path.joinpath(self.h5_file_name).is_file():
                new_file = True

        else:
            return

        self.close_file()
        self.open_file(self.h5_file_path.joinpath(self.h5_file_name), 'w' if new_file else 'a', title='PyMoDAQ file')

        self._raw_group = self.get_set_group(self.root(), raw_group_name, title='Data from PyMoDAQ modules')
        self.get_set_logger(self._raw_group)

        if new_file:
            self._raw_group.attrs['type'] = self.save_type.name  # first possibility to set a node attribute
            self.root().set_attr('file', self.h5_file_name)  # second possibility

            self.set_attr(self.root(), 'date', datetime_now.date().isoformat())
            self.set_attr(self.root(), 'time', datetime_now.time().isoformat())

            if metadata is not None:
                for metadata_key in metadata:
                    self._raw_group.attrs[metadata_key] = metadata[metadata_key]

    def save_file(self, filename=None):
        if isinstance(filename, str) or isinstance(filename, Path) and filename != '':
            file_path = Path(filename)
            if str(file_path) != '':
                super().save_file_as(filename)

    def get_set_logger(self, where: Node = None) -> VLARRAY:
        """ Retrieve or create (if absent) a logger enlargeable array to store logs
        Get attributed to the class attribute ``logger_array``
        Parameters
        ----------
        where: node
               location within the tree where to save or retrieve the array

        Returns
        -------
        vlarray
            enlargeable array accepting strings as elements
        """
        if where is None:
            where = self.raw_group
        if isinstance(where, Node):
            where = where.node
        logger = 'Logger'
        if logger not in list(self.get_children(where)):
            # check if logger node exist
            self._logger_array = self.add_string_array(where, logger)
            self._logger_array.attrs['type'] = 'log'
        else:
            self._logger_array = self.get_node(where, name=logger)
        return self._logger_array

    def add_log(self, msg):
        self._logger_array.append(msg)

    def add_string_array(self, where, name, title='', metadata=dict([])):
        array = self.create_vlarray(where, name, dtype='string', title=title)
        array.attrs['shape'] = (0,)
        array.attrs['data_type'] = 'strings'

        for metadat in metadata:
            array.attrs[metadat] = metadata[metadat]
        return array
    
    def add_array(self, where: Union[GROUP, str], name: str, data_type: DataType, array_to_save: np.ndarray = None,
                  data_shape: tuple = None, array_type: np.dtype = None, data_dimension: DataDim = None,
                  scan_shape: tuple = tuple([]), add_scan_dim=False, enlargeable: bool = False,
                  title: str = '', metadata=dict([]), ):

        """save data arrays on the hdf5 file together with metadata
        Parameters
        ----------
        where: GROUP
            node where to save the array
        name: str
            name of the array in the hdf5 file
        data_type: DataType
            mandatory so that the h5Browser can interpret correctly the array
        data_shape: Iterable
            the shape of the array to save, mandatory if array_to_save is None
        data_dimension: DataDim
         The data's dimension
        scan_shape: Iterable
            the shape of the scan dimensions
        title: str
            the title attribute of the array node
        array_to_save: ndarray or None
            data to be saved in the array. If None, array_type and data_shape should be specified in order to init
            correctly the memory
        array_type: np.dtype or numpy types
            eg np.float, np.int32 ...
        enlargeable: bool
            if False, data are saved as a CARRAY, otherwise as a EARRAY (for ragged data, see add_string_array)
        metadata: dict
            dictionnary whose keys will be saved as the array attributes
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
                array_type = config('data_saving', 'data_type', 'dynamics')[0]
            else:
                array_type = array_to_save.dtype

        data_type = enum_checker(DataType, data_type)
        data_dimension = enum_checker(DataDim, data_dimension)

        if enlargeable:
            # if data_shape == (1,):
            #     data_shape = None
            array = self.create_earray(where, utils.capitalize(name), dtype=np.dtype(array_type),
                                       data_shape=data_shape, title=title)
        else:
            if add_scan_dim:  # means it is an array initialization to zero
                shape = list(scan_shape[:])
                if not(len(data_shape) == 1 and data_shape[0] == 1):  # means data are not ndarrays of scalars
                    shape.extend(data_shape)
                if array_to_save is None:
                    array_to_save = np.zeros(shape, dtype=np.dtype(array_type))

            array = self.create_carray(where, utils.capitalize(name), obj=array_to_save, title=title)
        self.set_attr(array, 'data_type', data_type.name)
        self.set_attr(array, 'data_dimension', data_dimension.name)

        for metadat in metadata:
            self.set_attr(array, metadat, metadata[metadat])
        return array

    def get_set_group(self, where, name, title='', **kwargs):
        """Get the group located at where if it exists otherwise creates it

        This also set the _current_group property
        """

        self._current_group = super().get_set_group(where, name, title, **kwargs)
        return self._current_group

    def get_groups(self, where: Union[str, GROUP], group_type: Union[str, GroupType, BaseEnum]):
        """Get all groups hanging from a Group and of a certain type"""
        groups = []
        if isinstance(group_type, enum.Enum):
            group_type = group_type.name
        for node_name in list(self.get_children(where)):
            group = self.get_node(where, node_name)
            if 'type' in group.attrs and group.attrs['type'].lower() == group_type.lower():
                groups.append(group)
        return groups

    def get_last_group(self, where: GROUP, group_type: Union[str, GroupType, enum.Enum]):
        groups = self.get_groups(where, group_type)
        if len(groups) != 0:
            return groups[-1]
        else:
            return None

    def get_node_from_attribute_match(self, where, attr_name, attr_value):
        """Get a Node starting from a given node (Group) matching a pair of node attribute name and value"""
        for node in self.walk_nodes(where):
            if attr_name in node.attrs and node.attrs[attr_name] == attr_value:
                return node

    def get_node_from_title(self, where, title: str):
        """Get a Node starting from a given node (Group) matching the given title"""
        return self.get_node_from_attribute_match(where, 'TITLE', title)

    def add_data_group(self, where, data_dim: DataDim, title='', settings_as_xml='', metadata=None):
        """Creates a group node at given location in the tree

        Parameters
        ----------
        where: group node
               where to create data group
        group_data_type: DataDim
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
        :py:meth:`add_group`
        """
        if metadata is None:
            metadata = {}
        data_dim = enum_checker(DataDim, data_dim)
        metadata.update(settings=settings_as_xml)
        group = self.add_group(data_dim.name, 'data_dim', where, title, metadata)
        return group

    def add_incremental_group(self, group_type: Union[str, GroupType, enum.Enum], where, title='', settings_as_xml='', metadata=None):
        """
        Add a node in the h5 file tree of the group type with an increment in the given name
        Parameters
        ----------
        group_type: str or GroupType enum
            one of the possible values of **group_types**
        where: str or node
            parent node where to create the new group
        title: str
            node title
        settings_as_xml: str
            XML string containing Parameter representation
        metadata: dict
            extra metadata to be saved with this new group node

        Returns
        -------
        node: newly created group node
        """
        if metadata is None:
            metadata = {}
        if isinstance(group_type, enum.Enum):
            group_type = group_type.name

        nodes = [name for name in self.get_children(self.get_node(where))]
        nodes_tmp = []
        for node in nodes:
            if utils.capitalize(group_type.lower()) in node:
                nodes_tmp.append(node)
        nodes_tmp.sort()
        if len(nodes_tmp) == 0:
            ind_group = -1
        else:
            ind_group = int(nodes_tmp[-1][-3:])
        group = self.get_set_group(where, f'{utils.capitalize(group_type.lower())}{ind_group + 1:03d}', title)
        self.set_attr(group, 'settings', settings_as_xml)
        if group_type.lower() != 'ch':
            self.set_attr(group, 'type', group_type.lower())
        else:
            self.set_attr(group, 'type', '')
        for metadat in metadata:
            self.set_attr(group, metadat, metadata[metadat])
        return group

    def add_act_group(self, where, title='', settings_as_xml='', metadata=None):
        """
        Add a new group of type detector
        See Also
        -------
        add_incremental_group
        """
        if metadata is None:
            metadata = {}
        group = self.add_incremental_group('actuator', where, title, settings_as_xml, metadata)
        return group

    def add_det_group(self, where, title='', settings_as_xml='', metadata=None):
        """
        Add a new group of type detector
        See Also
        -------
        add_incremental_group
        """
        if metadata is None:
            metadata = {}
        group = self.add_incremental_group('detector', where, title, settings_as_xml, metadata)
        return group

    def add_generic_group(self, where='/RawData', title='', settings_as_xml='', metadata=None,
                          group_type=GroupType.scan):
        """Add a new group of type given by the input argument group_type

        At creation adds the attributes description and scan_done to be used elsewhere

        See Also
        -------
        add_incremental_group
        """
        if metadata is None:
            metadata = {}
        metadata.update(dict(description='', scan_done=False))
        group = self.add_incremental_group(group_type, where, title, settings_as_xml, metadata)
        return group

    def add_scan_group(self, where='/RawData', title='', settings_as_xml='', metadata=None,):
        """Add a new group of type scan

        deprecated, use add_generic_group with a group type as GroupType.scan
        """
        if metadata is None:
            metadata = {}
        metadata.update(dict(description='', scan_done=False))
        group = self.add_generic_group(where, title, settings_as_xml, metadata, group_type=GroupType.scan)
        return group

    def add_ch_group(self, where, title='', settings_as_xml='', metadata=None):
        """
        Add a new group of type channel
        See Also
        -------
        add_incremental_group
        """
        if metadata is None:
            metadata = {}
        group = self.add_incremental_group('ch', where, title, settings_as_xml, metadata)
        return group


    def add_move_group(self, where, title='', settings_as_xml='', metadata=None):
        """
        Add a new group of type actuator
        See Also
        -------
        add_incremental_group
        """
        if metadata is None:
            metadata = {}
        group = self.add_incremental_group('actuator', where, title, settings_as_xml, metadata)
        return group



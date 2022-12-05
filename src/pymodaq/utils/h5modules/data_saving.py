# -*- coding: utf-8 -*-
"""
Created the 21/11/2022

@author: Sebastien Weber
"""
from time import time
from typing import Union, List

import numpy as np

from pymodaq.utils.abstract import ABCMeta, abstract_attribute
from pymodaq.utils.enums import enum_checker
from pymodaq.utils.data import Axis, DataDim, DataWithAxes, DataToExport
from .saving import DataType, H5SaverLowLevel
from .backends import GROUP, CARRAY, Node, EARRAY
from pymodaq.utils.daq_utils import capitalize
from pymodaq.utils.scanner import ScanType


SPECIAL_GROUP_NAMES = dict(nav_axes='NavAxes')


class AxisError(Exception):
    pass


class DataManagement(metaclass=ABCMeta):
    """Base abstract class to be used for all specialized object saving and loading data to/from a h5file

    Attributes
    ----------
    data_type: DataType
        The enum for this type of data, here abstract and should be redefined
    """
    data_type: DataType = abstract_attribute()
    _h5saver: H5SaverLowLevel = abstract_attribute()

    @classmethod
    def _format_node_name(cls, ind: int) -> str:
        """ Format the saved node following the data_type attribute and an integer index

        Parameters
        ----------
        ind: int

        Returns
        -------
        str: the future name of the node
        """
        return f'{capitalize(cls.data_type.value)}{ind:02d}'

    def _get_next_node_name(self, where) -> str:
        """Get the formatted next node name given the ones already saved

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself

        Returns
        -------
        str: the future name of the node
        """
        return self._format_node_name(self._get_next_data_type_index_in_group(where))

    def get_last_node_name(self, where) -> Union[str, None]:
        """Get the last node name among the ones already saved

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself

        Returns
        -------
        str: the name of the last saved node or None if none saved
        """
        index = self._get_next_data_type_index_in_group(where) -1
        if index == -1:
            return None
        else:
            return self._format_node_name(index)

    def get_node_from_index(self, where, index):
        return self._h5saver.get_node(where, self._format_node_name(index))

    def _get_next_data_type_index_in_group(self, where: Union[Node, str]) -> int:
        """Check how much node with a given data_type are already present within the GROUP where
        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself

        Returns
        -------
        int: the next available integer to index the node name
        """
        ind = 0
        for node in self._h5saver.walk_nodes(where):
            if 'data_type' in node.attrs:
                if node.attrs['data_type'] == self.data_type.name:
                    ind += 1
        return ind

    def _is_node_of_data_type(self, where):
        """Check if a given node is of the data_type of the real class implementation
        
        eg 'axis' for the AxisSaverLoader
        
        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself

        Returns
        -------
        bool
        """
        node = self._h5saver.get_node(where)
        return 'data_type' in node.attrs and node.attrs['data_type'] == self.data_type

    def _get_nodes_from_data_type(self, where):
        """Get the node list having the same data type of the real implementation
        
        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself

        Returns
        -------
        list of Nodes
        """
        node = self._h5saver.get_node(where)
        if isinstance(node, GROUP):
            parent_node = node
        else:
            parent_node = node.parent_node

        nodes = []
        for child_node in self._h5saver.walk_nodes(parent_node):
            if self._is_node_of_data_type(child_node):
                nodes.append(child_node)
        return nodes


class AxisSaverLoader(DataManagement):
    """Specialized Object to save and load Axis object to and from a h5file

    Parameters
    ----------
    h5saver: H5SaverLowLevel

    Attributes
    ----------
    data_type: DataType
        The enum for this type of data, here 'axis'
    """
    data_type = DataType['axis']

    def __init__(self, h5saver: H5SaverLowLevel):
        self._h5saver = h5saver
        self.data_type = enum_checker(DataType, self.data_type)

    def add_axis(self, where: Union[Node, str], axis: Axis, enlargeable=False):
        """Write Axis info at a given position within a h5 file

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        axis: Axis
            the Axis object to add as a node in the h5file
        """
        if axis.data is None:
            axis.create_linear_data(axis.size)

        array = self._h5saver.add_array(where, self._get_next_node_name(where), self.data_type, title=axis.label,
                                        array_to_save=axis.data, data_dimension=DataDim['Data1D'],
                                        enlargeable=enlargeable,
                                        metadata=dict(size=axis.size, label=axis.label, units=axis.units,
                                                      index=axis.index, offset=axis.offset, scaling=axis.scaling,
                                                      distribution='uniform' if axis.is_axis_linear() else 'spread'))
        return array

    def load_axis(self, where: Union[Node, str]) -> Axis:
        """create an Axis object from the data and metadata at a given node if of data_type: 'axis

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself

        Returns
        -------
        Axis
        """
        axis_node = self._h5saver.get_node(where)
        if not self._is_node_of_data_type(axis_node):
            raise AxisError(f'Could not create an Axis object from this node: {axis_node}')
        return Axis(label=axis_node.attrs['label'], units=axis_node.attrs['units'],
                    data=axis_node.read(), index=axis_node.attrs['index'])

    def get_axes(self, where: Union[Node, str]) -> List[Axis]:
        """Return a list of Axis objects from the Axis Nodes hanging from (or among) a given Node

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself

        Returns
        -------
        List[Axis]: the list of all Axis object
        """
        return [self.load_axis(node) for node in self._get_nodes_from_data_type(where)]


class DataSaverLoader(DataManagement):
    """Specialized Object to save and load DataWithAxes object to and from a h5file

    Parameters
    ----------
    h5saver: H5SaverLowLevel

    Attributes
    ----------
    data_type: DataType
        The enum for this type of data, here 'data'
    """
    data_type = DataType['data']

    def __init__(self, h5saver: H5SaverLowLevel):
        self.data_type = enum_checker(DataType, self.data_type)
        self._h5saver = h5saver
        self._axis_saver = AxisSaverLoader(h5saver)

    def add_data(self, where: Union[Node, str], data: DataWithAxes, save_axes=True):
        """

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        data
        save_axes: bool

        Returns
        -------

        """
        for ind_data in range(len(data)):
            self._h5saver.add_array(where, self._get_next_node_name(where), self.data_type, title=data.name,
                                    array_to_save=data[ind_data], data_dimension=data.dim.name,
                                    metadata=dict(timestamp=data.timestamp, label=data.labels[ind_data],
                                                  source=data.source.name, distribution=data.distribution.name,
                                                  nav_indexes=data.nav_indexes))
        if save_axes:
            for axis in data.axes:
                self._axis_saver.add_axis(where, axis)

    def get_axes(self, where: Union[Node, str]) -> List[Axis]:
        """

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself

        Returns
        -------

        """
        return self._axis_saver.get_axes(where)

    def get_bkg_nodes(self, where: Union[Node, str]):
        bkg_nodes = []
        for node in self._h5saver.walk_nodes(where):
            if 'data_type' in node.attrs and node.attrs['data_type'] =='bkg':
                bkg_nodes.append(node)
        return bkg_nodes

    def get_data_arrays(self, where: Union[Node, str], with_bkg=True) -> List[np.ndarray]:
        """

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        with_bkg: bool
            If True try to load background node and return the array with background subtraction

        Returns
        -------
        list of ndarray
        """
        if with_bkg:
            bkg_nodes = []
            if with_bkg:
                bkg_nodes = self.get_bkg_nodes(where)
            if len(bkg_nodes) == 0:
                with_bkg = False

        if with_bkg:
            return [array.read()-bkg.read() for array, bkg in zip(self._get_nodes_from_data_type(where), bkg_nodes)]
        else:
            return [array.read() for array in self._get_nodes_from_data_type(where)]

    def load_data(self, where, with_bkg=True) -> DataWithAxes:
        """Return a DataWithAxes object from the Data and Axis Nodes hanging from (or among) a given Node

        Does not include navigation axes stored elsewhere in the h5file

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        with_bkg: bool
            If True try to load background node and return the data with background subtraction

        See Also
        --------
        load_data
        """

        node = self._h5saver.get_node(where)
        if isinstance(node, GROUP):
            parent_node = node
        elif isinstance(node, CARRAY):
            parent_node = node.parent_node
        data_node = self._get_nodes_from_data_type(parent_node)[0]

        if not self._is_node_of_data_type(data_node):
            raise TypeError(f'Could not create an DataWithAxes object from this node: {data_node}')

        if 'axis' in self.data_type.name:
            ndarrays = [data_node.read()]
            axes = []
        else:
            ndarrays = self.get_data_arrays(parent_node, with_bkg=with_bkg)
            axes = self.get_axes(parent_node)

        data = DataWithAxes(data_node.attrs['TITLE'],
                            source=data_node.attrs['source'] if 'source' in data_node.attrs else 'raw',
                            dim=data_node.attrs['data_dimension'],
                            distribution=data_node.attrs['distribution'],
                            data=ndarrays,
                            labels=[data_node.attrs['label']],
                            nav_indexes=data_node.attrs['nav_indexes'] if 'nav_indexes' in data_node.attrs else (),
                            axes=axes)
        return data


class BkgSaver(DataSaverLoader):
    """Specialized Object to save and load DataWithAxes background object to and from a h5file

    Parameters
    ----------
    hsaver: H5SaverLowLevel

    Attributes
    ----------
    data_type: DataType
        The enum for this type of data, here 'data'
    """
    data_type = DataType['bkg']

    def __init__(self, h5saver: H5SaverLowLevel):
        super().__init__(h5saver)


class DataEnlargeableSaver(DataSaverLoader):
    """Specialized Object to save and load enlargeable DataWithAxes saved object to and from a h5file

    Parameters
    ----------
    h5saver: H5SaverLowLevel

    Attributes
    ----------
    data_type: DataType
        The enum for this type of data, here 'data_enlargeable'
    """
    data_type = DataType['data_enlargeable']

    def __init__(self, h5saver: H5SaverLowLevel):
        super().__init__(h5saver)

    def _create_data_arrays(self, where: Union[Node, str], data: DataWithAxes, save_axes=True):
        """ Create enlargeable array to store data

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        data: DataWithAxes
        save_axes: bool

        Notes
        -----
        Because data will be saved at a given index in the enlargeable array, related axes will have their index
        increased by one unity
        """

        if self.get_last_node_name(where) is None:
            for ind_data in range(len(data)):
                nav_indexes = list(data.nav_indexes)
                nav_indexes = [0] + list(np.array(nav_indexes, dtype=np.int) + 1)

                self._h5saver.add_array(where, self._get_next_node_name(where), self.data_type, title=data.name,
                                        array_to_save=data[ind_data],
                                        data_shape=data[ind_data].shape,
                                        array_type=data[ind_data].dtype,
                                        scan_type=ScanType['Scan1D'],
                                        enlargeable=True,
                                        data_dimension=data.dim.name,
                                        metadata=dict(timestamp=data.timestamp, label=data.labels[ind_data],
                                                      source=data.source.name, distribution=data.distribution.name,
                                                      nav_indexes=nav_indexes))
            if save_axes:
                for axis in data.axes:
                    axis.index += 1  # because of enlargeable data will have an extra shape
                    self._axis_saver.add_axis(where, axis)

    def add_data(self, where: Union[Node, str], data: DataWithAxes):
        if self.get_last_node_name(where) is None:
            self._create_data_arrays(where, data, save_axes=True)

        for ind_data in range(len(data)):
            array: EARRAY = self.get_node_from_index(where, ind_data)
            array.append(data[ind_data])


class DataToExportSaver:
    def __init__(self, h5saver: H5SaverLowLevel):
        self._h5saver = h5saver
        self._data_saver = DataSaverLoader(h5saver)
        self._bkg_saver = BkgSaver(h5saver)

    @staticmethod
    def channel_formatter(ind: int):
        return f'CH{ind:02d}'

    def add_data(self, where: Union[Node, str], data: DataToExport, settings_as_xml='', metadata={}):
        """

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        data
        settings_as_xml
        metadata

        Returns
        -------

        """
        dims = data.get_dim_presents()
        for dim in dims:
            dim_group = self._h5saver.get_set_group(where, dim)
            for ind, dwa in enumerate(data.get_data_from_dim(dim)):  # dwa: DataWithAxes filtered by dim
                dwa_group = self._h5saver.get_set_group(dim_group, self.channel_formatter(ind), dwa.name)
                # dwa_group = self._h5saver.add_ch_group(dim_group, dwa.name)
                self._data_saver.add_data(dwa_group, dwa)

    def add_bkg(self, where: Union[Node, str], data: DataToExport):
        dims = data.get_dim_presents()
        for dim in dims:
            dim_group = self._h5saver.get_set_group(where, dim)
            for ind, dwa in enumerate(data.get_data_from_dim(dim)):  # dwa: DataWithAxes filtered by dim
                dwa_group = self._h5saver.get_set_group(dim_group, self.channel_formatter(ind), dwa.name)
                # dwa_group = self._h5saver.get_node_from_title(dim_group, dwa.name)
                if dwa_group is not None:
                    self._bkg_saver.add_data(dwa_group, dwa, save_axes=False)


class DataToExportEnlargeableSaver(DataToExportSaver):

    def __init__(self, h5saver: H5SaverLowLevel):
        super().__init__(h5saver)
        self._data_saver = DataEnlargeableSaver(h5saver)
        self._nav_axis_saver = AxisSaverLoader(h5saver)

    def add_data(self, where: Union[Node, str], data: DataToExport, settings_as_xml='', metadata={}):
        super().add_data(where, data, settings_as_xml, metadata)
        nav_group = self._h5saver.get_set_group(where, SPECIAL_GROUP_NAMES['nav_axes'])
        if self._nav_axis_saver.get_last_node_name(nav_group) is None:
            axis = Axis(label='time_axis', units='s', data=np.array([0., 1.]), index=0)
            time_array = self._nav_axis_saver.add_axis(nav_group, axis, enlargeable=True)
            time_array.attrs['size'] = 0

        time_array = self._nav_axis_saver.get_node_from_index(nav_group, 0)
        time_array.append(np.array([time()]))
        time_array.attrs['size'] += 1


class DataLoader:
    """Specialized Object to load DataWithAxes object from a h5file

    Parameters
    ----------
    h5saver: H5SaverLowLevel
    """

    def __init__(self, h5saver: H5SaverLowLevel):
        self._h5saver = h5saver
        self._axis_loader = AxisSaverLoader(h5saver)
        self._data_loader = DataSaverLoader(h5saver)

    def get_nav_group(self, where: Union[Node, str]) -> Union[Node, None]:
        """

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself

        Returns
        -------
        GROUP: returns the group named SPECIAL_GROUP_NAMES['nav_axes'] holding all NavAxis for those data

        See Also
        --------
        SPECIAL_GROUP_NAMES
        """
        node = self._h5saver.get_node(where)
        while node is not None:  # means where reached the root level
            if isinstance(node, GROUP):
                if self._h5saver.is_node_in_group(node, SPECIAL_GROUP_NAMES['nav_axes']):
                    return self._h5saver.get_node(node, SPECIAL_GROUP_NAMES['nav_axes'])
            node = node.parent_node

    def load_data(self, where: Union[Node, str], with_bkg=True) -> DataWithAxes:
        """Load data from a node (or channel node)

        Loaded data contains also nav_axes if any and with optional background subtraction

        Parameters
        ----------
        where
        with_bkg

        Returns
        -------

        """
        node_data_type = DataType[self._h5saver.get_node(where).attrs['data_type']]
        self._data_loader.data_type = node_data_type
        data = self._data_loader.load_data(where, with_bkg=with_bkg)
        nav_group = self.get_nav_group(where)
        if nav_group is not None:
            nav_axes = self._axis_loader.get_axes(nav_group)
            data.axes.extend(nav_axes)
        return data
# -*- coding: utf-8 -*-
"""
Created the 21/11/2022

@author: Sebastien Weber
"""

from typing import Union, List

import numpy as np

from pymodaq.utils.abstract import ABCMeta, abstract_attribute
from pymodaq.utils.enums import enum_checker
from pymodaq.utils.data import Axis, DataDim, DataWithAxes, DataToExport
from .saving import DataType, H5SaverLowLevel
from .backends import GROUP, CARRAY, Node
from pymodaq.utils.daq_utils import capitalize


class AxisError(Exception):
    pass


class DataSaver(metaclass=ABCMeta):
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
        return f'{capitalize(cls.data_type.name)}{ind:02d}'

    def _get_node_name(self, where) -> str:
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


class AxisSaverLoader(DataSaver):
    """Specialized Object to save and load Axis object to and from a h5file

    Parameters
    ----------
    hsaver: H5SaverLowLevel

    Attributes
    ----------
    data_type: DataType
        The enum for this type of data, here 'axis'
    """
    data_type = DataType['axis']

    def __init__(self, hsaver: H5SaverLowLevel):

        self.data_type = enum_checker(DataType, self.data_type)
        self._h5saver = hsaver

    def add_axis(self, where: Union[Node, str], axis: Axis):
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

        array = self._h5saver.add_array(where, self._get_node_name(where), self.data_type, title=axis.label,
                                        array_to_save=axis.data, data_dimension=DataDim['Data1D'],
                                        metadata=dict(size=axis.size, label=axis.label, units=axis.units,
                                                      index=axis.index, offset=axis.offset, scaling=axis.scaling))
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


class DataSaverLoader(DataSaver):
    """Specialized Object to save and load DataWithAxes object to and from a h5file

    Parameters
    ----------
    hsaver: H5SaverLowLevel

    Attributes
    ----------
    data_type: DataType
        The enum for this type of data, here 'data'
    """
    data_type = DataType['data']

    def __init__(self, hsaver: H5SaverLowLevel):
        self.data_type = enum_checker(DataType, self.data_type)

        self._h5saver = hsaver
        self._axis_saver = AxisSaverLoader(hsaver)

    def add_data(self, where: Union[Node, str], data: DataWithAxes):
        """

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        data

        Returns
        -------

        """
        for ind_data in range(len(data)):
            self._h5saver.add_array(where, self._get_node_name(where), self.data_type, title=data.name,
                                    array_to_save=data[ind_data], data_dimension=data.dim.name,
                                    metadata=dict(timestamp=data.timestamp, label=data.labels[ind_data],
                                                  source=data.source.name, distribution=data.distribution.name,
                                                  nav_indexes=data.nav_indexes))
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

    def get_data_arrays(self, where: Union[Node, str]) -> List[np.ndarray]:
        """

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself

        Returns
        -------

        """
        return [array.read() for array in self._get_nodes_from_data_type(where)]

    def load_data(self, where) -> DataWithAxes:
        """Return a DataWithAxes object from the Data and Axis Nodes hanging from (or among) a given Node

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        """

        node = self._h5saver.get_node(where)
        if isinstance(node, GROUP):
            parent_node = node
        elif isinstance(node, CARRAY):
            parent_node = node.parent_node
        data_node = self._get_nodes_from_data_type(parent_node)[0]

        if not self._is_node_of_data_type(data_node):
            raise AxisError(f'Could not create an DataWithAxes object from this node: {data_node}')

        data = DataWithAxes(data_node.attrs['TITLE'], source=data_node.attrs['source'],
                            dim=data_node.attrs['data_dimension'], distribution=data_node.attrs['distribution'],
                            data=self.get_data_arrays(parent_node), labels=[data_node.attrs['label']],
                            nav_indexes=data_node.attrs['nav_indexes'],
                            axes=self.get_axes(parent_node))
        return data


class DataToExportSaver:

    def __init__(self, hsaver: H5SaverLowLevel):
        self._h5saver = hsaver
        self._data_saver = DataSaverLoader(hsaver)

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
            for dwa in data.get_data_from_dim(dim):  # dwa: DataWithAxes filtered by dim
                dwa_group = self._h5saver.add_ch_group(dim_group, dwa.name, settings_as_xml, metadata)
                self._data_saver.add_data(dwa_group, dwa)


# -*- coding: utf-8 -*-
"""
Created the 21/11/2022

@author: Sebastien Weber
"""
from time import time
from typing import Union, List, Tuple, Iterable

import numpy as np

from pymodaq.utils.abstract import ABCMeta, abstract_attribute
from pymodaq.utils.enums import enum_checker
from pymodaq.utils.data import Axis, DataDim, DataWithAxes, DataToExport, DataDistribution, DataDimError
from .saving import DataType, H5Saver
from .backends import GROUP, CARRAY, Node, EARRAY, NodeError
from pymodaq.utils.daq_utils import capitalize
from pymodaq.utils.scanner.utils import ScanType

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
    _h5saver: H5Saver = abstract_attribute()

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
        index = self._get_next_data_type_index_in_group(where) - 1
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
        node = self._get_node(where)
        return 'data_type' in node.attrs and node.attrs['data_type'] == self.data_type

    def _get_node(self, where: Union[str, Node]) -> Node:
        """Utility method to get a node from a node or a string"""
        return self._h5saver.get_node(where)

    def _get_nodes(self, where: Union[str, Node]) -> List[Node]:
        """Get Nodes hanging from where including where

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself

        Returns
        -------
        List[Node]
        """
        node = self._get_node(where)
        if isinstance(node, GROUP):
            return [child_node for child_node in self._h5saver.walk_nodes(node)]
        else:
            return [node]

    def _get_nodes_from_data_type(self, where):
        """Get the node list hanging from a parent and having the same data type as self
        
        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node

        Returns
        -------
        list of Nodes
        """
        node = self._get_node(where)
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
    h5saver: H5Saver

    Attributes
    ----------
    data_type: DataType
        The enum for this type of data, here 'axis'
    """
    data_type = DataType['axis']

    def __init__(self, h5saver: H5Saver):
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
        enlargeable: bool
            Specify if the underlying array will be enlargebale
        """
        array = self._h5saver.add_array(where, self._get_next_node_name(where), self.data_type, title=axis.label,
                                        array_to_save=axis.get_data(), data_dimension=DataDim['Data1D'],
                                        enlargeable=enlargeable,
                                        metadata=dict(size=axis.size, label=axis.label, units=axis.units,
                                                      index=axis.index, offset=axis.offset, scaling=axis.scaling,
                                                      distribution='uniform' if axis.is_axis_linear() else 'spread',
                                                      spread_order=axis.spread_order))
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
        axis_node = self._get_node(where)
        if not self._is_node_of_data_type(axis_node):
            raise AxisError(f'Could not create an Axis object from this node: {axis_node}')
        return Axis(label=axis_node.attrs['label'], units=axis_node.attrs['units'],
                    data=np.atleast_1d(np.squeeze(axis_node.read())), index=axis_node.attrs['index'],
                    spread_order=axis_node.attrs['spread_order'])

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
    h5saver: H5Saver

    Attributes
    ----------
    data_type: DataType
        The enum for this type of data, here 'data'
    """
    data_type = DataType['data']

    def __init__(self, h5saver: H5Saver):
        self.data_type = enum_checker(DataType, self.data_type)
        self._h5saver = h5saver
        self._axis_saver = AxisSaverLoader(h5saver)

    def isopen(self) -> bool:
        """ Get the opened status of the underlying hdf5 file"""
        return self._h5saver.isopen()

    def add_data(self, where: Union[Node, str], data: DataWithAxes, save_axes=True, **kwargs):
        """Adds Array nodes to a given location adding eventually axes as others nodes and metadata

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        data: DataWithAxes
        save_axes: bool
        """

        for ind_data in range(len(data)):
            metadata = dict(timestamp=data.timestamp, label=data.labels[ind_data],
                            source=data.source.name, distribution=data.distribution.name,
                            origin=data.origin,
                            nav_indexes=tuple(data.nav_indexes)
                            if data.nav_indexes is not None else None)
            for name in data.extra_attributes:
                metadata[name] = getattr(data, name)
            self._h5saver.add_array(where, self._get_next_node_name(where), self.data_type, title=data.name,
                                    array_to_save=data[ind_data], data_dimension=data.dim.name, metadata=metadata)
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
            if 'data_type' in node.attrs and node.attrs['data_type'] == 'bkg':
                bkg_nodes.append(node)
        return bkg_nodes

    def get_data_arrays(self, where: Union[Node, str], with_bkg=False,
                        load_all=False) -> List[np.ndarray]:
        """

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        with_bkg: bool
            If True try to load background node and return the array with background subtraction
        load_all: bool
            If True load all similar nodes hanging from a parent

        Returns
        -------
        list of ndarray
        """
        where = self._get_node(where)
        if with_bkg:
            bkg_nodes = []
            if with_bkg:
                bkg_nodes = self.get_bkg_nodes(where.parent_node)
            if len(bkg_nodes) == 0:
                with_bkg = False

        if load_all:
            getter = self._get_nodes_from_data_type
        else:
            getter = self._get_nodes

        if with_bkg:
            return [np.atleast_1d(np.squeeze(array.read()-bkg.read()))
                    for array, bkg in zip(getter(where), bkg_nodes)]
        else:
            return [np.atleast_1d(np.squeeze(array.read())) for array in getter(where)]

    def load_data(self, where, with_bkg=False, load_all=False) -> DataWithAxes:
        """Return a DataWithAxes object from the Data and Axis Nodes hanging from (or among) a
        given Node

        Does not include navigation axes stored elsewhere in the h5file. The node path is stored in
        the DatWithAxis using the attribute path

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        with_bkg: bool
            If True try to load background node and return the data with background subtraction
        load_all: bool
            If True, will load all data hanging from the same parent node

        See Also
        --------
        load_data
        """

        data_node = self._get_node(where)

        if load_all:
            parent_node = data_node.parent_node
            data_nodes = self._get_nodes_from_data_type(parent_node)
            data_node = data_nodes[0]
        else:
            parent_node = data_node.parent_node
            if not isinstance(data_node, CARRAY):
                return
            data_nodes = [data_node]

        if 'axis' in self.data_type.name:
            ndarrays = [np.atleast_1d(np.squeeze(data_node.read())) for data_node in data_nodes]
            axes = [Axis(label=data_node.attrs['label'], units=data_node.attrs['units'],
                         data=np.linspace(0, ndarrays[0].size-1, ndarrays[0].size-1))]
        else:
            ndarrays = self.get_data_arrays(data_node, with_bkg=with_bkg, load_all=load_all)
            axes = self.get_axes(parent_node)

        extra_attributes = data_node.attrs.to_dict()
        for name in ['TITLE', 'CLASS', 'VERSION', 'backend', 'source', 'data_dimension',
                     'distribution', 'label', 'origin', 'nav_indexes', 'dtype', 'data_type',
                     'subdtype', 'shape', 'size', 'EXTDIM', 'path']:
            extra_attributes.pop(name, None)

        data = DataWithAxes(data_node.attrs['TITLE'],
                            source=data_node.attrs['source'] if 'source' in data_node.attrs
                            else 'raw',
                            dim=data_node.attrs['data_dimension'],
                            distribution=data_node.attrs['distribution'],
                            data=ndarrays,
                            labels=[node.attrs['label'] for node in data_nodes],
                            origin=data_node.attrs['origin'] if 'origin' in data_node.attrs else '',
                            nav_indexes=data_node.attrs['nav_indexes'] if 'nav_indexes' in
                                                                          data_node.attrs else (),
                            axes=axes,
                            path=data_node.path,
                            **extra_attributes)
        return data


class BkgSaver(DataSaverLoader):
    """Specialized Object to save and load DataWithAxes background object to and from a h5file

    Parameters
    ----------
    hsaver: H5Saver

    Attributes
    ----------
    data_type: DataType
        The enum for this type of data, here 'data'
    """
    data_type = DataType['bkg']

    def __init__(self, h5saver: H5Saver):
        super().__init__(h5saver)


class DataEnlargeableSaver(DataSaverLoader):
    """Specialized Object to save and load enlargeable DataWithAxes saved object to and from a h5file

    Particular case of DataND will a single *nav_indexes* parameter will be appended as chunks of signal data

    Parameters
    ----------
    h5saver: H5Saver

    Attributes
    ----------
    data_type: DataType
        The enum for this type of data, here 'data_enlargeable'

    Notes
    -----
    To be used to save data from a timed logger (DAQViewer continuous saving or DAQLogger extension) or from an
    adaptive scan where the final shape is unknown or other module that need this feature
    """
    data_type = DataType['data_enlargeable']

    def __init__(self, h5saver: H5Saver):
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
                nav_indexes = [0] + list(np.array(nav_indexes, dtype=int) + 1)

                self._h5saver.add_array(where, self._get_next_node_name(where), self.data_type, title=data.name,
                                        array_to_save=data[ind_data],
                                        data_shape=data[ind_data].shape,
                                        array_type=data[ind_data].dtype,
                                        enlargeable=True,
                                        data_dimension=data.dim.name,
                                        metadata=dict(timestamp=data.timestamp, label=data.labels[ind_data],
                                                      source=data.source.name, distribution=data.distribution.name,
                                                      origin=data.origin,
                                                      nav_indexes=tuple(nav_indexes)))
            if save_axes:
                for axis in data.axes:
                    axis.index += 1  # because of enlargeable data will have an extra shape
                    self._axis_saver.add_axis(where, axis)

    def add_data(self, where: Union[Node, str], data: DataWithAxes):
        """ Append data to an enlargeable array node

        Data of dim (0, 1 or 2) will be just appended to the enlargeable array. DataND with one navigation axis of
        length (Lnav) will be considered as a collection of Lnav signal data of dim (0, 1 or 2) and will therefore be
        appended as Lnav signal data

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        data: DataWithAxes
        """
        if self.get_last_node_name(where) is None:
            if len(data.nav_indexes) == 0:
                data_init = data
            elif len(data.nav_indexes) == 1:
                data_init = data.inav[0]
                data_init.source = data.source  # because slicing returns a calculated one
            else:
                raise DataDimError('It is not possible to append DataND with more than 1 navigation axis')
            self._create_data_arrays(where, data_init, save_axes=True)

        for ind_data in range(len(data)):
            array: EARRAY = self.get_node_from_index(where, ind_data)
            array.append(data[ind_data])


class DataExtendedSaver(DataSaverLoader):
    """Specialized Object to save and load DataWithAxes saved object to and from a h5file in extended arrays

    Parameters
    ----------
    h5saver: H5Saver
    extended_shape: Tuple[int]
        the extra shape compared to the data the h5array will have

    Attributes
    ----------
    data_type: DataType
        The enum for this type of data, here 'data'
    """
    data_type = DataType['data']

    def __init__(self, h5saver: H5Saver, extended_shape: Tuple[int]):
        super().__init__(h5saver)
        self.extended_shape = extended_shape

    def _create_data_arrays(self, where: Union[Node, str], data: DataWithAxes, save_axes=True,
                            distribution=DataDistribution['uniform']):
        """ Create array with extra dimensions (from scan) to store data

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        data: DataWithAxes
        save_axes: bool

        Notes
        -----
        Because data will be saved at a given index in the "scan" array, related axes will have their index
        increased by the length of the scan dim (1 for scan1D, 2 for scan2D, ...)
        """
        if self.get_last_node_name(where) is None:
            for ind_data in range(len(data)):
                nav_indexes = list(data.nav_indexes)
                nav_indexes = [ind for ind in range(len(self.extended_shape))] +\
                              list(np.array(nav_indexes, dtype=int) + len(self.extended_shape))

                self._h5saver.add_array(where, self._get_next_node_name(where), self.data_type, title=data.name,
                                        data_shape=data[ind_data].shape,
                                        array_type=data[ind_data].dtype,
                                        scan_shape=self.extended_shape,
                                        add_scan_dim=True,
                                        data_dimension=data.dim.name,
                                        metadata=dict(timestamp=data.timestamp, label=data.labels[ind_data],
                                                      source=data.source.name, distribution=distribution.name,
                                                      origin=data.origin,
                                                      nav_indexes=tuple(nav_indexes)))

            if save_axes:
                for axis in data.axes:
                    axis.index += len(self.extended_shape)
                    # because there will be len(self.extended_shape) extra navigation axes
                    self._axis_saver.add_axis(where, axis)

    def add_data(self, where: Union[Node, str], data: DataWithAxes, indexes: List[int],
                 distribution=DataDistribution['uniform']):
        """Adds given DataWithAxes at a location within the initialized h5 array

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        data: DataWithAxes
        indexes: Iterable[int]
            indexes where to save data in the init h5array (should have the same length as extended_shape and with values
            coherent with this shape
        """
        if len(indexes) != len(self.extended_shape):
            raise IndexError(f'Cannot put data into the h5array with extended indexes {indexes}')
        for ind in range(len(indexes)):
            if indexes[ind] > self.extended_shape[ind]:
                raise IndexError(f'Indexes cannot be higher than the array shape')

        if self.get_last_node_name(where) is None:
            self._create_data_arrays(where, data, save_axes=True, distribution=distribution)

        for ind_data in range(len(data)):
            #todo check that getting with index is safe...
            array: CARRAY = self.get_node_from_index(where, ind_data)
            array[tuple(indexes)] = data[ind_data]
            # maybe use array.__setitem__(indexes, data[ind_data]) if it's not working


class DataToExportSaver:
    """Object used to save DataToExport object into a h5file following the PyMoDAQ convention

    Parameters
    ----------
    h5saver: H5Saver

    """
    def __init__(self, h5saver: H5Saver):
        self._h5saver = h5saver
        self._data_saver = DataSaverLoader(h5saver)
        self._bkg_saver = BkgSaver(h5saver)

    def _get_node(self, where: Union[Node, str]) -> Node:
        return self._h5saver.get_node(where)

    def close(self):
        self._h5saver.close()

    def isopen(self) -> bool:
        """ Get the opened status of the underlying hdf5 file"""
        return self._h5saver.isopen()

    @staticmethod
    def channel_formatter(ind: int):
        """All DataWithAxes included in the DataToExport will be saved into a channel group indexed
        and formatted as below"""
        return f'CH{ind:02d}'

    def add_data(self, where: Union[Node, str], data: DataToExport, settings_as_xml='',
                 metadata=None):
        """

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        data: DataToExport
        settings_as_xml: str
            The settings parameter as an XML string
        metadata: dict
            all extra metadata to be saved in the group node where data will be saved

        """
        if metadata is None:
            metadata = {}
        dims = data.get_dim_presents()
        for dim in dims:
            dim_group = self._h5saver.get_set_group(where, dim)
            for ind, dwa in enumerate(data.get_data_from_dim(dim)):
                # dwa: DataWithAxes filtered by dim
                dwa_group = self._h5saver.get_set_group(dim_group, self.channel_formatter(ind),
                                                        dwa.name)
                # dwa_group = self._h5saver.add_ch_group(dim_group, dwa.name)
                self._data_saver.add_data(dwa_group, dwa)

    def add_bkg(self, where: Union[Node, str], data: DataToExport):
        dims = data.get_dim_presents()
        for dim in dims:
            dim_group = self._h5saver.get_set_group(where, dim)
            for ind, dwa in enumerate(data.get_data_from_dim(dim)):
                # dwa: DataWithAxes filtered by dim
                dwa_group = self._h5saver.get_set_group(dim_group,
                                                        self.channel_formatter(ind), dwa.name)
                # dwa_group = self._get_node_from_title(dim_group, dwa.name)
                if dwa_group is not None:
                    self._bkg_saver.add_data(dwa_group, dwa, save_axes=False)


class DataToExportEnlargeableSaver(DataToExportSaver):
    """Generic object to save DataToExport objects in an enlargeable h5 array

    The next enlarged value should be specified in the add_data method

    Parameters
    ----------
    h5saver: H5Saver
    axis_name: str
        the name of the enlarged axis array
    axis_units: str
        the units of the enlarged axis array
    """
    def __init__(self, h5saver: H5Saver, axis_name: str = 'nav axis', axis_units: str = ''):

        super().__init__(h5saver)
        self._data_saver = DataEnlargeableSaver(h5saver)
        self._nav_axis_saver = AxisSaverLoader(h5saver)
        self._axis_name = axis_name
        self._axis_units = axis_units

    def add_data(self, where: Union[Node, str], data: DataToExport,
                 axis_value: Union[float, np.ndarray], settings_as_xml='', metadata=None):
        """

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        data: DataToExport
            The data to be saved into an enlargeable array
        axis_value: float or np.ndarray
            The next value (or values) of the enlarged axis
        settings_as_xml: str
            The settings parameter as an XML string
        metadata: dict
            all extra metadata to be saved in the group node where data will be saved
        """
        super().add_data(where, data, settings_as_xml, metadata)
        where = self._get_node(where)
        nav_group = self._h5saver.get_set_group(where, SPECIAL_GROUP_NAMES['nav_axes'])
        if self._nav_axis_saver.get_last_node_name(nav_group) is None:
            axis = Axis(label=self._axis_name, units=self._axis_units, data=np.array([0., 1.]), index=0)
            axis_array = self._nav_axis_saver.add_axis(nav_group, axis, enlargeable=True)
            axis_array.attrs['size'] = 0

        axis_array = self._nav_axis_saver.get_node_from_index(nav_group, 0)
        axis_array.append(np.atleast_1d(np.squeeze(np.array([axis_value]))), expand=False)
        axis_array.attrs['size'] += 1


class DataToExportTimedSaver(DataToExportEnlargeableSaver):
    """Specialized DataToExportEnlargeableSaver to save data as a function of a time axis

    Only one element ca be added at a time, the time axis value are enlarged using the data to be
    added timestamp

    Notes
    -----
    This object is made for continuous saving mode of DAQViewer and logging to h5file for DAQLogger
    """
    def __init__(self, h5saver: H5Saver):
        super().__init__(h5saver, 'time', 's')

    def add_data(self, where: Union[Node, str], data: DataToExport, settings_as_xml='',
                 metadata=None):
        super().add_data(where, data, axis_value=data.timestamp, settings_as_xml=settings_as_xml,
                         metadata=metadata)


class DataToExportExtendedSaver(DataToExportSaver):
    """Object to save DataToExport at given indexes within arrays including extended shape

    Mostly used for data generated from the DAQScan

    Parameters
    ----------
    h5saver: H5Saver
    extended_shape: Tuple[int]
        the extra shape compared to the data the h5array will have
    """

    def __init__(self, h5saver: H5Saver, extended_shape: Tuple[int]):
        super().__init__(h5saver)
        self._data_saver = DataExtendedSaver(h5saver, extended_shape)
        self._nav_axis_saver = AxisSaverLoader(h5saver)

    def add_nav_axes(self, where: Union[Node, str], axes: List[Axis]):
        """Used to add navigation axes related to the extended array

        Notes
        -----
        For instance the scan axes in the DAQScan
        """
        where = self._get_node(where)
        nav_group = self._h5saver.get_set_group(where, SPECIAL_GROUP_NAMES['nav_axes'])
        if self._nav_axis_saver.get_last_node_name(nav_group) is None:
            for axis in axes:
                self._nav_axis_saver.add_axis(nav_group, axis)

    def add_data(self, where: Union[Node, str], data: DataToExport, indexes: Iterable[int],
                 distribution=DataDistribution['uniform'],
                 settings_as_xml='', metadata={}):
        """

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        data: DataToExport
        indexes: List[int]
            indexes where to save data in the init h5array (should have the same length as
            extended_shape and with values coherent with this shape
        settings_as_xml: str
            The settings parameter as an XML string
        metadata: dict
            all extra metadata to be saved in the group node where data will be saved

        """
        dims = data.get_dim_presents()
        for dim in dims:
            dim_group = self._h5saver.get_set_group(where, dim)
            for ind, dwa in enumerate(data.get_data_from_dim(dim)):
                # dwa: DataWithAxes filtered by dim
                dwa_group = self._h5saver.get_set_group(dim_group,
                                                        self.channel_formatter(ind), dwa.name)
                self._data_saver.add_data(dwa_group, dwa, indexes=indexes,
                                          distribution=distribution)


class DataLoader:
    """Specialized Object to load DataWithAxes object from a h5file

    On the contrary to DataSaverLoader, does include navigation axes stored elsewhere in the h5file
    (for instance if saved from the DAQ_Scan)

    Parameters
    ----------
    h5saver: H5Saver
    """

    def __init__(self, h5saver: H5Saver):
        self._axis_loader: AxisSaverLoader = None
        self._data_loader: DataSaverLoader = None

        self.h5saver = h5saver

    @property
    def h5saver(self):
        return self._h5saver

    @h5saver.setter
    def h5saver(self, h5saver: H5Saver):
        self._h5saver = h5saver
        self._axis_loader = AxisSaverLoader(h5saver)
        self._data_loader = DataSaverLoader(h5saver)

    def get_node(self, where: Union[Node, str], name: str = None) -> Node:
        """ Convenience method to get node"""
        return self.h5saver.get_node(where, name)

    def get_nav_group(self, where: Union[Node, str]) -> Union[Node, None]:
        """

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself

        Returns
        -------
        GROUP: returns the group named SPECIAL_GROUP_NAMES['nav_axes'] holding all NavAxis for
        those data

        See Also
        --------
        SPECIAL_GROUP_NAMES
        """
        node = self._h5saver.get_node(where)
        while node is not None:  # means we reached the root level
            if isinstance(node, GROUP):
                if self._h5saver.is_node_in_group(node, SPECIAL_GROUP_NAMES['nav_axes']):
                    return self._h5saver.get_node(node, SPECIAL_GROUP_NAMES['nav_axes'])
            node = node.parent_node

    def load_data(self, where: Union[Node, str], with_bkg=False, load_all=False) -> DataWithAxes:
        """Load data from a node (or channel node)

        Loaded data contains also nav_axes if any and with optional background subtraction

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        with_bkg: bool
            If True will attempt to substract a background data node before loading
        load_all: bool
            If True, will load all data hanging from the same parent node

        Returns
        -------

        """
        node_data_type = DataType[self._h5saver.get_node(where).attrs['data_type']]
        self._data_loader.data_type = node_data_type
        data = self._data_loader.load_data(where, with_bkg=with_bkg, load_all=load_all)
        if 'axis' not in node_data_type.name:
            nav_group = self.get_nav_group(where)
            if nav_group is not None:
                nav_axes = self._axis_loader.get_axes(nav_group)
                data.axes.extend(nav_axes)
                data.get_dim_from_data_axes()
        data.create_missing_axes()
        return data

    def load_all(self, where: GROUP, data: DataToExport, with_bkg=False) -> DataToExport:

        where = self._h5saver.get_node(where)
        children_dict = where.children()
        data_list = []
        for child in children_dict:
            if isinstance(children_dict[child], GROUP):
                self.load_all(children_dict[child], data, with_bkg=with_bkg)
            elif ('data_type' in children_dict[child].attrs and 'data' in
                  children_dict[child].attrs['data_type']):

                data_list.append(self.load_data(children_dict[child].path,
                                                with_bkg=with_bkg, load_all=True))
                break
        data_tmp = DataToExport(name=where.name, data=data_list)
        data.append(data_tmp)

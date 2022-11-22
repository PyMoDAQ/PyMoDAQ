# -*- coding: utf-8 -*-
"""
Created the 21/11/2022

@author: Sebastien Weber
"""

from typing import Union, List
import xml.etree.ElementTree as ET

import numpy as np

from pymodaq.utils.abstract import ABCMeta, abstract_attribute
from pymodaq.utils.enums import enum_checker
from pymodaq.utils.data import Axis, DataDim, DataWithAxes, DataToExport
from .saving import DataType, H5SaverLowLevel
from .backends import GROUP, CARRAY, Node
from pymodaq.utils.daq_utils import capitalize
from pymodaq.utils.parameter import ioxml


class AxisError(Exception):
    pass


class Saver(metaclass=ABCMeta):
    """Base abstract class to be used for all specialized object saving and loading stuff to/from a h5file

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


class AxisSaverLoader(Saver):
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


class DataSaverLoader(Saver):
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
        for ind_data in range(len(data)):
            self._h5saver.add_array(where, self._get_node_name(where), self.data_type, title=data.name,
                                    array_to_save=data[ind_data], data_dimension=data.dim.name,
                                    metadata=dict(timestamp=data.timestamp, label=data.labels[ind_data],
                                                  source=data.source.name, distribution=data.distribution.name,
                                                  nav_indexes=data.nav_indexes))
        for axis in data.axes:
            self._axis_saver.add_axis(where, axis)

    def get_axes(self, where: Union[Node, str]) -> List[Axis]:
        return self._axis_saver.get_axes(where)

    def get_data_arrays(self, where: Union[Node, str]) -> List[np.ndarray]:
        return [array.read() for array in self._get_nodes_from_data_type(where)]

    def load_data(self, where) -> DataWithAxes:
        """Return a DataWithAxes object from the Data and Axis Nodes hanging from (or among) a given Node"""

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
        dims = data.get_dim_presents()
        for dim in dims:
            dim_group = self._h5saver.get_set_group(where, dim)
            for dwa in data.get_data_from_dim(dim):  # dwa: DataWithAxes filtered by dim
                dwa_group = self._h5saver.add_ch_group(dim_group, dwa.name, settings_as_xml, metadata)
                self._data_saver.add_data(dwa_group, dwa)



# class DetectorDataSaver:
#     data_type = 'data'
#
#     def __init__(self, hsaver: H5SaverLowLevel):
#         self.data_type = enum_checker(DataType, self.data_type)
#         self._h5saver = hsaver
#
#         self._det_group: GROUP = None
#
#     def add_detector(self, detector):
#         settings_xml = ET.Element('All_settings')
#         settings_xml.append(ioxml.walk_parameters_to_xml(param=detector.settings))
#         settings_xml.append(ioxml.walk_parameters_to_xml(param=self.h5saver.settings))
#
#         if self.ui is not None:
#             for ind, viewer in enumerate(detector.viewers):
#                 if hasattr(viewer, 'roi_manager'):
#                     roi_xml = ET.SubElement(settings_xml, f'ROI_Viewer_{ind:02d}')
#                     roi_xml.append(ioxml.walk_parameters_to_xml(viewer.roi_manager.settings))
#
#         self._det_group = self.h5saver.add_det_group(self.h5saver.raw_group, "Data", ET.tostring(settings_xml))
#
#     def add_external_h5(self, external_h5_file):
#
#         external_group = self.h5saver.add_group('external_data', 'external_h5', self._det_group)
#         if not external_h5_file.isopen:
#             h5saver = H5Saver()
#             h5saver.init_file(addhoc_file_path=external_h5_file.filename)
#             h5_file = h5saver.h5_file
#         else:
#             h5_file = external_h5_file
#         h5_file.copy_children(h5_file.get_node('/'), external_group, recursive=True)
#         h5_file.flush()
#         h5_file.close()
#
#     def add_data(self, data: DataToExport, bkg: DataToExport = None):
#         data_dims = ['data1D']  # we don't record 0D data in this mode (only in continuous)
#         if self.h5saver.settings['save_2D']:
#             data_dims.extend(['data2D', 'dataND'])
#
#         # self._channel_arrays = OrderedDict([])
#
#         for data_dim in data_dims:
#             data_from_dim = data.get_data_from_dim(DataDim[data_dim])
#             if bkg is not None:
#                 bkg_from_dim = bkg.get_data_from_dim(DataDim[data_dim])
#
#             if len(data_from_dim) != 0:
#                 data_group = self.h5saver.add_data_group(self._det_group, data_dim)
#                 for ind_channel, data_with_axes in enumerate(data_from_dim):
#                     channel_group = self.h5saver.add_CH_group(data_group, title=data_with_axes.name)
#                     if bkg is not None:
#                         if channel in bkg_container[data_dim]:
#                             data[data_dim][channel]['bkg'] = bkg_container[data_dim][channel]['data']
#                     self._channel_arrays[data_dim][channel] = h5saver.add_data(channel_group,
#                                                                                data[data_dim][channel],
#                                                                                scan_type='',
#                                                                                enlargeable=False)
#
#                     if data_dim == 'data2D' and 'Data2D' in self._viewer_types.names():
#                         ind_viewer = self._viewer_types.names().index('Data2D')
#                         string = pymodaq.utils.gui_utils.utils.widget_to_png_to_bytes(
#                             self.viewers[ind_viewer].parent)
#                         self._channel_arrays[data_dim][channel].attrs['pixmap2D'] = string
#
#         try:
#             if self.ui is not None:
#                 (root, filename) = os.path.split(str(path))
#                 filename, ext = os.path.splitext(filename)
#                 image_path = os.path.join(root, filename + '.png')
#                 self.dockarea.parent().grab().save(image_path)
#         except Exception as e:
#             self.logger.exception(str(e))
#
#         h5saver.close_file()
#         self.data_saved.emit()

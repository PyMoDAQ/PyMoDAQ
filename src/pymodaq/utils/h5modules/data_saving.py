# -*- coding: utf-8 -*-
"""
Created the 21/11/2022

@author: Sebastien Weber
"""

from typing import Union
import xml.etree.ElementTree as ET


from pymodaq.utils.abstract import ABCMeta, abstract_attribute
from pymodaq.utils.enums import enum_checker
from pymodaq.utils.data import Axis, DataDim
from .saving import DataType, H5SaverLowLevel
from .backends import Group
from pymodaq.utils.daq_utils import capitalize
from pymodaq.utils.parameter import ioxml


class Saver(metaclass=ABCMeta):
    data_type: DataType = abstract_attribute()
    _h5saver: H5SaverLowLevel = abstract_attribute()

    @classmethod
    def _format_node_name(cls, ind: int) -> str:
        return f'{capitalize(cls.data_type.name)}{ind:02d}'

    def _get_node_name(self, where) -> str:
        return self._format_node_name(self._get_next_data_type_index_in_group(where))

    def _get_next_data_type_index_in_group(self, where: Union[Group, str]) -> int:
        """Check how much node with a given data_type are already present within the Group where
        Parameters
        ----------
        where: Union[Group, str]

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


class AxisSaverLoader(Saver):
    data_type = DataType['axis']

    def __init__(self, hsaver: H5SaverLowLevel):
        self.data_type = enum_checker(DataType, self.data_type)
        self._h5saver = hsaver

    def add_axis(self, where: Union[Group, str], axis: Axis):
        """Write Axis info at a given position within a h5 file"""
        if axis.data is None:
            axis.create_linear_data(axis.size)

        array = self._h5saver.add_array(where, self._get_node_name(where), self.data_type, title=axis.label,
                                        array_to_save=axis.data, data_dimension=DataDim['Data1D'],
                                        metadata=dict(size=axis.size, label=axis.label, units=axis.units,
                                                      index=axis.index, offset=axis.offset, scaling=axis.scaling))
        return array

    def load_axis(self, where):
        axis_node = self._h5saver.get_node(where)
        return Axis(label=axis_node.attrs['label'], units=axis_node.attrs['units'],
                    data=axis_node.read(), index=axis_node.attrs['index'])


#
# class DetectorDataSaver:
#     data_type = 'data'
#
#     def __init__(self, hsaver: H5SaverLowLevel):
#         self.data_type = enum_checker(DataType, self.data_type)
#         self._h5saver = hsaver
#
#         self._det_group: Group = None
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

# -*- coding: utf-8 -*-
"""
Created the 23/11/2022

@author: Sebastien Weber
"""
from typing import Union, List
import xml.etree.ElementTree as ET


from pymodaq.utils.abstract import ABCMeta, abstract_attribute, abstractmethod

from pymodaq.utils.data import Axis, DataDim, DataWithAxes, DataToExport
from .saving import H5SaverLowLevel
from .backends import GROUP, CARRAY, Node, GroupType
from .data_saving import DataToExportSaver, AxisSaverLoader, DataSaverLoader
from pymodaq.utils.parameter import ioxml

from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.extensions.daq_scan import DAQ_Scan


class ModuleSaver(metaclass=ABCMeta):
    """Abstract base class to save info and data from main modules (DAQScan, DAQViewer, DAQMove, ...)"""
    group_type: GroupType = abstract_attribute()
    _module = abstract_attribute()
    _h5saver: H5SaverLowLevel = abstract_attribute()

    def get_set_node(self, where: Union[Node, str] = None) -> Node:
        """Get the node corresponding to this particular Module instance

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself

        Returns
        -------
        Node: the Node associated with this module
        """
        if where is None:
            where = self._h5saver.raw_group
        for node in self._h5saver.walk_nodes(where):
            if 'type' in node.attrs and node.attrs['type'] == self.group_type.name and node.title == self._module.title:
                return node
        return self._add_module(where)

    @abstractmethod
    def _add_module(self, where: Union[Node, str] = None, metadata={}):
        ...

    @property
    def module(self):
        return self._module

    @property
    def h5saver(self):
        return self._h5saver

    @h5saver.setter
    def h5saver(self, _h5saver: H5SaverLowLevel):
        self._h5saver = _h5saver


class DetectorSaver(ModuleSaver):
    """Implementation of the ModuleSaver class dedicated to DAQ_Viewer modules

    Parameters
    ----------
    h5saver
    module
    """
    group_type = GroupType['detector']

    def __init__(self, module: DAQ_Viewer):
        self._datatoexport_saver = None

        self._module: DAQ_Viewer = module
        self.h5saver = module.h5saver

    @property
    def h5saver(self):
        return self._h5saver

    @h5saver.setter
    def h5saver(self, _h5saver: H5SaverLowLevel):
        self._h5saver = _h5saver
        self._datatoexport_saver = DataToExportSaver(_h5saver)

    def _add_module(self, where: Union[Node, str] = None, metadata={}) -> Node:
        """

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        metadata: dict

        Returns
        -------

        """
        if where is None:
            where = self._h5saver.raw_group

        settings_xml = ET.Element('All_settings')
        settings_xml.append(ioxml.walk_parameters_to_xml(param=self._module.settings))
        settings_xml.append(ioxml.walk_parameters_to_xml(param=self._module.h5saver.settings))

        if self._module.ui is not None:
            for ind, viewer in enumerate(self._module.viewers):
                if hasattr(viewer, 'roi_manager'):
                    roi_xml = ET.SubElement(settings_xml, f'ROI_Viewer_{ind:02d}')
                    roi_xml.append(ioxml.walk_parameters_to_xml(viewer.roi_manager.settings))

        return self._h5saver.add_det_group(where, title=self._module.title, settings_as_xml=ET.tostring(settings_xml),
                                           metadata=metadata)

    def add_data(self, where: Union[Node, str], data: DataToExport):
        self._datatoexport_saver.add_data(where, data)


class ActuatorSaver(ModuleSaver):
    """Implementation of the ModuleSaver class dedicated to DAQ_Move modules

    Parameters
    ----------
    h5saver
    module
    """
    group_type = GroupType['actuator']

    def __init__(self, module: DAQ_Move):
        self._axis_saver = None

        self._module: DAQ_Move = module
        self.h5saver = module.h5saver

    @property
    def h5saver(self):
        return self._h5saver

    @h5saver.setter
    def h5saver(self, _h5saver: H5SaverLowLevel):
        self._h5saver = _h5saver
        self._axis_saver = AxisSaverLoader(_h5saver)

    def _add_module(self, where: Union[Node, str] = None, metadata={}):
        if where is None:
            where = self._h5saver.raw_group

        settings_xml = ET.Element('All_settings')
        settings_xml.append(ioxml.walk_parameters_to_xml(param=self._module.settings))

        return self._h5saver.add_act_group(where, title=self._module.title, settings_as_xml=ET.tostring(settings_xml),
                                           metadata=metadata)


class ScanSaver(ModuleSaver):
    """Implementation of the ModuleSaver class dedicated to DAQ_Scan module

    Parameters
    ----------
    h5saver
    module
    """
    group_type = GroupType['scan']

    def __init__(self, module: DAQ_Scan):

        self._module: DAQ_Scan = module
        self.h5saver = module.h5saver

    @property
    def h5saver(self):
        return self._h5saver

    @h5saver.setter
    def h5saver(self, _h5saver: H5SaverLowLevel):
        self._h5saver = _h5saver
        for module in self._module.modules_manager.modules:
            if hasattr(module, 'module_and_data_saver'):
                module.module_and_data_saver.h5saver = _h5saver

    def _add_module(self, where: Union[Node, str] = None, metadata={}) -> Node:
        """

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        metadata: dict

        Returns
        -------

        """
        if where is None:
            where = self._h5saver.raw_group

        settings_xml = ET.Element('All_settings')
        settings_xml.append(ioxml.walk_parameters_to_xml(param=self._module.settings))
        settings_xml.append(ioxml.walk_parameters_to_xml(param=self._module.h5saver.settings))

        return self._h5saver.add_scan_group(where, title=self._module.title, settings_as_xml=ET.tostring(settings_xml),
                                           metadata=metadata)




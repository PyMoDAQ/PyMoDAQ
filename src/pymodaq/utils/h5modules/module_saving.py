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
from .data_saving import DataToExportSaver, AxisSaverLoader, DataToExportEnlargeableSaver
from pymodaq.utils.parameter import ioxml

from pymodaq.control_modules.daq_viewer import DAQ_Viewer
from pymodaq.control_modules.daq_move import DAQ_Move
from pymodaq.extensions.daq_scan import DAQ_Scan


class ModuleSaver(metaclass=ABCMeta):
    """Abstract base class to save info and data from main modules (DAQScan, DAQViewer, DAQMove, ...)"""
    group_type: GroupType = abstract_attribute()
    _module = abstract_attribute()
    _h5saver: H5SaverLowLevel = abstract_attribute()
    _module_group: GROUP = abstract_attribute()

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
                self._module_group = node
                return node
        self._module_group = self._add_module(where)
        return self._module_group

    @abstractmethod
    def _add_module(self, where: Union[Node, str] = None, metadata={}):
        ...

    @property
    def module(self):
        return self._module

    @property
    def module_group(self):
        return self._module_group

    @property
    def h5saver(self):
        return self._h5saver

    @h5saver.setter
    def h5saver(self, _h5saver: H5SaverLowLevel):
        self._h5saver = _h5saver
        self.update_after_h5changed()

    @abstractmethod
    def update_after_h5changed(self):
        ...


class DetectorSaver(ModuleSaver):
    """Implementation of the ModuleSaver class dedicated to DAQ_Viewer modules

    Parameters
    ----------
    module
    """
    group_type = GroupType['detector']

    def __init__(self, module: DAQ_Viewer):
        self._datatoexport_saver: DataToExportSaver = None

        self._module: DAQ_Viewer = module
        self._module_group: GROUP = None
        self._h5saver = None

    def update_after_h5changed(self, ):
        self._datatoexport_saver = DataToExportSaver(self.h5saver)

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

        settings_xml = ET.Element('All_settings', type='group')
        settings_xml.append(ioxml.walk_parameters_to_xml(param=self._module.settings))
        saver_xml = ET.SubElement(settings_xml,'H5Saver', type='group')
        saver_xml.append(ioxml.walk_parameters_to_xml(param=self._h5saver.settings))

        if self._module.ui is not None:
            for ind, viewer in enumerate(self._module.viewers):
                if hasattr(viewer, 'roi_manager'):
                    roi_xml = ET.SubElement(settings_xml, f'ROI_Viewer_{ind:02d}', type='group')
                    roi_xml.append(ioxml.walk_parameters_to_xml(param=viewer.roi_manager.settings))

        return self._h5saver.add_det_group(where, title=self._module.title, settings_as_xml=ET.tostring(settings_xml),
                                           metadata=metadata)

    def add_data(self, where: Union[Node, str], data: DataToExport):
        self._datatoexport_saver.add_data(where, data)

    def add_bkg(self, where: Union[Node, str], data_bkg: DataToExport):
        self._datatoexport_saver.add_bkg(where, data_bkg)

    def add_external_h5(self, other_h5data: H5SaverLowLevel):
        if other_h5data is not None:
            external_group = self._h5saver.add_group('external_data', 'external_h5', self.module_group)
            try:
                if not other_h5data.isopen:
                    h5saver = H5SaverLowLevel()
                    h5saver.init_file(addhoc_file_path=other_h5data.filename)
                    h5_file = h5saver.h5_file
                else:
                    h5_file = other_h5data
                h5_file.copy_children(h5_file.get_node('/'), external_group, recursive=True)
                h5_file.flush()
                h5_file.close()

            except Exception as e:
                self.logger.exception(str(e))


class DetectorEnlargeableSaver(DetectorSaver):
    """Implementation of the ModuleSaver class dedicated to DAQ_Viewer modules in order to save enlargeable data

    Parameters
    ----------
    module
    """
    group_type = GroupType['detector']

    def __init__(self, module: DAQ_Viewer):
        super().__init__(module)
        self._datatoexport_saver: DataToExportEnlargeableSaver = None

    def update_after_h5changed(self, ):
        self._datatoexport_saver = DataToExportEnlargeableSaver(self.h5saver)


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
        self._module_group: GROUP = None
        self._module: DAQ_Move = module

    def update_after_h5changed(self):
        self._axis_saver = AxisSaverLoader(self.h5saver)

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
        self._module_group: GROUP = None
        self._module: DAQ_Scan = module

    def update_after_h5changed(self):
        for module in self._module.modules_manager.modules:
            if hasattr(module, 'module_and_data_saver'):
                module.module_and_data_saver.h5saver = self.h5saver

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



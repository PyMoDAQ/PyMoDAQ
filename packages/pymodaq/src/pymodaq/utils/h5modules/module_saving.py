# -*- coding: utf-8 -*-
"""
Created the 23/11/2022

@author: Sebastien Weber
"""
from __future__ import annotations

from typing import Union, List, Tuple, TYPE_CHECKING, Iterable
import time
import xml.etree.ElementTree as ET

import numpy as np

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.enums import BaseEnum
from pymodaq_utils.abstract import ABCMeta, abstract_attribute, abstractmethod
from pymodaq_utils.utils import capitalize

from pymodaq_data import DataDim, DataWithAxes
from pymodaq_data.data import Axis, DataToExport, DataDistribution, DataRaw, DataSource
from pymodaq_data.h5modules.data_saving import (
    DataToExportSaver, DataToExportEnlargeableSaver,
    DataToExportTimedSaver, DataToExportExtendedSaver)
from pymodaq_data.h5modules.backends import GROUP, Node

from pymodaq_gui.h5modules.saving import H5SaverBase
from pymodaq_gui.parameter import ioxml
from pymodaq.utils.managers.modules.utils import ModuleType

if TYPE_CHECKING:
    from pymodaq.extensions.scan.daq_scan import DAQScan
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer
    from pymodaq.control_modules.daq_move import DAQ_Move

logger = set_logger(get_module_name(__file__))


class GroupModuleType(BaseEnum):
    DETECTOR = 0
    ACTUATOR = 1
    SCAN = 2
    DATALOGGER = 3
    OPTIMIZER = 4
    TIME = 5


class ModuleSaver(metaclass=ABCMeta):
    """Abstract base class to save info and data from main modules (DAQScan, DAQViewer, DAQMove, ...)"""
    group_type: GroupModuleType = abstract_attribute()
    _module = abstract_attribute()
    _h5saver: H5SaverBase = abstract_attribute()
    _module_group: GROUP = abstract_attribute()
    main_module = True

    def flush(self):
        """Flush the underlying file"""
        self._h5saver.flush()

    def get_set_node(self, where: Union[Node, str] = None, name: str = None) -> GROUP:
        """Get or create the node corresponding to this particular Module instance

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        new: bool
            if True force the creation of a new indexed node of this class type
            if False return the last node (or create one if None)

        Returns
        -------
        GROUP: the Node associated with this module which should be a GROUP node
        """
        if where is None:
            where = self._h5saver.raw_group
        if name is None:
            name = self._module.title
        group = self._h5saver.get_node_from_title(where, name)
        if group is not None:
            self._module_group = group
            return group  # if I got one I return it else I create one

        self._module_group = self._add_module(where)
        return self._module_group

    def get_last_node(self, where: Union[Node, str] = None):
        """Get the last node corresponding to this particular Module instance

        Parameters
        ----------
        where: Union[Node, str]
           the path of a given node or the node itself
        new: bool
           if True force the creation of a new indexed node of this class type
           if False return the last node (or create one if None)

        Returns
        -------
        GROUP: the Node associated with this module which should be a GROUP node
        """
        if where is None:
            where = self._h5saver.raw_group

        group = self._h5saver.get_last_group(where, self.group_type)
        self._module_group = group
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
    def h5saver(self, _h5saver: H5SaverBase):
        self._h5saver = _h5saver
        self.update_after_h5changed()

    @abstractmethod
    def update_after_h5changed(self):
        ...

    def get_last_node_index(self, where: Union[Node, str] = None):
        node = self.get_last_node(where)
        return int(node.name.split(capitalize(self.group_type.name.lower()))[1])

    def get_next_node_name(self, where: Union[Node, str] = None):
        index = self.get_last_node_index(where)
        return f'{capitalize(self.group_type.name.lower())}{index+1:03d}'


class DetectorSaver(ModuleSaver):
    """Implementation of the ModuleSaver class dedicated to DAQ_Viewer modules

    Parameters
    ----------
    module
    """
    group_type = GroupModuleType.DETECTOR

    def __init__(self, module: DAQ_Viewer):
        self._datatoexport_saver: DataToExportSaver = None

        self._module: 'DAQ_Viewer' = module
        self._module_group: GROUP = None
        self._h5saver = None

    def update_after_h5changed(self):
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
        if self.main_module:
            saver_xml = ET.SubElement(settings_xml, 'H5Saver', type='group')
            saver_xml.append(ioxml.walk_parameters_to_xml(param=self._h5saver.settings))

        if self._module.ui is not None:
            for ind, viewer in enumerate(self._module.viewers):
                if hasattr(viewer, 'roi_manager'):
                    roi_xml = ET.SubElement(settings_xml, f'ROI_Viewer_{ind:02d}', type='group')
                    roi_xml.append(ioxml.walk_parameters_to_xml(param=viewer.roi_manager.settings))

        return self._h5saver.add_det_group(where, title=self._module.title, settings_as_xml=ET.tostring(settings_xml),
                                           metadata=metadata)

    def add_data(self, where: Union[Node, str], data: DataToExport, **kwargs):
        self._datatoexport_saver.add_data(where, data, **kwargs)

    def filter_data(self, dte: DataToExport) -> DataToExport:
        """ Filter Data to be saved depending on first the presence of the extra_attribute: *do_save* and then on
        the H5Saver settings
        """
        dte_filtered = DataToExport('Filtered')
        for dwa in dte:
            if 'do_save' in dwa.extra_attributes:  # this is the main filter
                if dwa.do_save:
                    dte_filtered.append(dwa)
            elif self.filter_data_wrt_settings(dwa):
                dte_filtered.append(dwa)
        return dte_filtered

    def filter_data_wrt_settings(self, dwa: DataWithAxes) -> bool:
        """ Check if this DataWithAxes should be saved depending on the H5Saver settings

        Return True if it should be saved
        """
        flag = True
        if not self.h5saver.settings['save_2D']:  # exclude 2D data and above
            flag = flag and not (dwa.dim == DataDim.Data2D or dwa.dim == DataDim.DataND)
        if self.h5saver.settings['save_raw_only']:  # exclude Calculated data
            flag = flag and dwa.source == DataSource.raw
        return flag

    def add_bkg(self, where: Union[Node, str], data_bkg: DataToExport):
        """ Adds a DataToExport as a background node in the h5file

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        data_bkg: DataToExport
            The data to be saved as background

        Returns
        -------

        """
        self._datatoexport_saver.add_bkg(where, data_bkg)

    def add_external_h5(self, other_h5data: H5SaverBase):
        if other_h5data is not None:
            external_group = self._h5saver.add_group('external_data', 'external_h5', self.module_group)
            try:
                if not other_h5data.isopen:
                    h5saver = H5SaverBase()
                    h5saver.init_file(addhoc_file_path=other_h5data.filename)
                    h5_file = h5saver.h5_file
                else:
                    h5_file = other_h5data
                h5_file.copy_children(h5_file.get_node('/'), external_group, recursive=True)
                h5_file.flush()
                h5_file.close()

            except Exception as e:
                self.logger.exception(str(e))


class DetectorTimeSaver(DetectorSaver):
    """Implementation of the ModuleSaver class dedicated to DAQ_Viewer modules in order to save enlargeable data

    Parameters
    ----------
    module
    """
    group_type = GroupModuleType.DETECTOR

    def __init__(self, module: DAQ_Viewer):
        super().__init__(module)
        self._datatoexport_saver: DataToExportTimedSaver = None

    def update_after_h5changed(self):
        self._datatoexport_saver = DataToExportTimedSaver(self.h5saver)


class DetectorEnlargeableSaver(DetectorSaver):
    """Implementation of the ModuleSaver class dedicated to DAQ_Viewer modules in order to save enlargeable data

    Parameters
    ----------
    module
    """
    group_type = GroupModuleType.DETECTOR

    def __init__(self, module: DAQ_Viewer,
                 enl_axis_names: Iterable[str] = None,
                 enl_axis_units: Iterable[str] = None):
        super().__init__(module)
        self.enl_axis_names = enl_axis_names
        self.enl_axis_units = enl_axis_units
        self._datatoexport_saver: DataToExportEnlargeableSaver = None

    def update_after_h5changed(self):
        self._datatoexport_saver = DataToExportEnlargeableSaver(
            self.h5saver, self.enl_axis_names, self.enl_axis_units)


class DetectorExtendedSaver(DetectorSaver):
    """Implementation of the ModuleSaver class dedicated to DAQ_Viewer modules in order to save enlargeable data

    Parameters
    ----------
    module
    """
    group_type = GroupModuleType.DETECTOR

    def __init__(self, module: DAQ_Viewer, extended_shape: Tuple[int]):
        super().__init__(module)
        self._extended_shape = extended_shape
        self._datatoexport_saver: DataToExportExtendedSaver = None

    def update_after_h5changed(self):
        self._datatoexport_saver = DataToExportExtendedSaver(self.h5saver, self._extended_shape)

    def add_data(self, where: Union[Node, str], data: DataToExport, indexes: Tuple[int],
                 distribution=DataDistribution['uniform']):
        self._datatoexport_saver.add_data(where, data, indexes=indexes, distribution=distribution)

    def add_nav_axes(self, where: Union[Node, str], axes: List[Axis]):
        self._datatoexport_saver.add_nav_axes(where, axes)


class ActuatorSaver(ModuleSaver):
    """Implementation of the ModuleSaver class dedicated to DAQ_Move modules

    Parameters
    ----------
    h5saver
    module
    """
    group_type = GroupModuleType.ACTUATOR

    def __init__(self, module: DAQ_Move):
        self._datatoexport_saver: DataToExportSaver = None
        self._module_group: GROUP = None
        self._module: DAQ_Move = module
        self._h5saver = None

    def update_after_h5changed(self):
        self._datatoexport_saver = DataToExportSaver(self.h5saver)

    def _add_module(self, where: Union[Node, str] = None, metadata=None):
        if metadata is None:
            metadata={}
        if where is None:
            where = self._h5saver.raw_group

        settings_xml = ET.Element('All_settings')
        settings_xml.append(ioxml.walk_parameters_to_xml(param=self._module.settings))

        return self._h5saver.add_act_group(where, title=self._module.title, settings_as_xml=ET.tostring(settings_xml),
                                           metadata=metadata)

    def add_data(self, where: Union[Node, str], data: DataToExport):
        self._datatoexport_saver.add_data(where, data)


class ActuatorTimeSaver(ActuatorSaver):
    def __init__(self, module: DAQ_Move):
        super().__init__(module)
        self._datatoexport_saver: DataToExportTimedSaver = None

    def update_after_h5changed(self):
        self._datatoexport_saver = DataToExportTimedSaver(self.h5saver)

    def add_data(self, where: Union[Node, str], data: DataToExport):
        self._datatoexport_saver.add_data(where, data)


class ActuatorEnlargeableSaver(ActuatorTimeSaver):
    """Implementation of the ModuleSaver class dedicated to DAQ_Move modules

    Parameters
    ----------
    h5saver
    module
    """

    def __init__(self, module: DAQ_Move,
                 enl_axis_names: Iterable[str] = None,
                 enl_axis_units: Iterable[str] = None):
        super().__init__(module)
        self.enl_axis_names = enl_axis_names
        self.enl_axis_units = enl_axis_units
        self._datatoexport_saver: DataToExportEnlargeableSaver = None

    def update_after_h5changed(self):
        self._datatoexport_saver = DataToExportEnlargeableSaver(
            self.h5saver, self.enl_axis_names, self.enl_axis_units)


    def add_data(self, where: Union[Node, str], data: DataToExport,
                 axis_values: List[Union[float, np.ndarray]] = None,
                 **kwargs):
        self._datatoexport_saver.add_data(where, data, axis_values, **kwargs)


class ScanSaver(ModuleSaver):
    """Implementation of the ModuleSaver class dedicated to DAQScan module

    Parameters
    ----------
    h5saver
    module
    """
    group_type = GroupModuleType.SCAN

    def __init__(self, module):
        self._module_group: GROUP = None
        self._module: DAQScan = module
        self._h5saver = None
        self._time_saver = TimeModuleSaver()

        for detector in self._module.modules_manager.detectors_all:
            detector._module_and_data_saver = DetectorSaver(detector)
        for actuator in self._module.modules_manager.actuators_all:
            actuator._module_and_data_saver = ActuatorSaver(actuator)

    def update_after_h5changed(self):
        for module in self._module.modules_manager.modules_all:
            if hasattr(module, '_module_and_data_saver'):
                module._module_and_data_saver.h5saver = self.h5saver
        self._time_saver.h5saver = self.h5saver

    def forget_h5(self):
        for module in self._module.modules_manager.modules_all:
            if hasattr(module, 'module_and_data_saver'):
                module.module_and_data_saver.h5saver = None
        self.h5saver.flush()

    def get_set_node(self, where: Union[Node, str] = None, new=False) -> GROUP:
        """Get the last group scan node

        Get the last Scan Group or create one
        get the last Scan Group if:
        * there is one already created
        * new is False

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        new: bool

        Returns
        -------
        GROUP: the GROUP associated with this module
        """
        self._module_group = self.get_last_node(where)
        new = new or (self._module_group is None)
        if new:
            self._module_group = self._add_module(where)
        for module in self._module.modules_manager.modules:
            module.module_and_data_saver.main_module = False
            module.module_and_data_saver.get_set_node(self._module_group)
        self._time_saver.get_set_node(self._module_group)
        return self._module_group

    def _add_module(self, where: Union[Node, str] = None, metadata=None) -> Node:
        """

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        metadata: dict

        Returns
        -------

        """
        if metadata is None:
            metadata = {}
        if where is None:
            where = self._h5saver.raw_group

        settings_xml = ET.Element('All_settings', type='group')
        settings_xml.append(ioxml.walk_parameters_to_xml(param=self._module.settings))
        if self.main_module:
            saver_xml = ET.SubElement(settings_xml, 'H5Saver', type='group')
            saver_xml.append(ioxml.walk_parameters_to_xml(param=self._h5saver.settings))

        return self._h5saver.add_generic_group(where, title=self._module.title,
                                            settings_as_xml=ET.tostring(settings_xml),
                                            metadata=metadata,
                                            group_type=self.group_type.name)

    def add_nav_axes(self, axes: List[Axis]):
        for detector in self._module.modules_manager.detectors:
            detector.module_and_data_saver.add_nav_axes(self._module_group, axes)

    def add_data(self, dte: DataToExport = None, indexes: Tuple[int] = None,
                 distribution=DataDistribution.uniform, **kwargs):
        for ind, detector in enumerate(self._module.modules_manager.detectors):
            try:
                detector.insert_data(indexes, where=self._module_group, distribution=distribution,
                                     extra_data=dte if ind == 0 else None,)
            except Exception as e:
                logger.exception(f'Cannot insert data: {str(e)}')

    def initialize_time_array(self, extended_shape: Tuple[int]):
        self._time_saver.initialize(extended_shape)

    def add_time(self, indexes: Tuple[int]):
        self._time_saver.add_time(indexes)


class TimeModule:
    """Minimal module-like object used by TimeModuleSaver."""
    title = 'Timestamps'


class TimeModuleSaver(ModuleSaver):
    """Saves per-scan-point elapsed time in a proper HDF5 group.

    Creates a 'Timestamps/' group inside the scan node, with a Data00 CARRAY
    of shape = scan_shape written via DataToExportExtendedSaver, so naming
    conventions and attributes are handled identically to detector data.

    Nav axes are NOT repeated here — they already live in each detector's
    NavAxes group and share the same index convention.
    """
    group_type = GroupModuleType.TIME

    def __init__(self):
        self._module = TimeModule()
        self._module_group = None
        self._h5saver = None
        self._extended_shape: Tuple[int] = None
        self._datatoexport_saver: DataToExportExtendedSaver = None
        self._start_time: float = None

    def update_after_h5changed(self):
        if self._extended_shape is not None:
            self._datatoexport_saver = DataToExportExtendedSaver(
                self._h5saver, self._extended_shape, fill_value=np.nan)

    def _add_module(self, where=None, metadata=None) -> Node:
        if metadata is None:
            metadata = {}
        if where is None:
            where = self._h5saver.raw_group
        # Fixed group name 'Timestamps' — no incremental index
        group = self._h5saver.get_set_group(where, 'Timestamps', title='Timestamps')
        self._h5saver.set_attr(group, 'type', 'time')
        settings_xml = ET.Element('All_settings', type='group')
        self._h5saver.set_attr(group, 'settings', ET.tostring(settings_xml))
        return group

    def initialize(self, extended_shape: Tuple[int]):
        """Set up the extended saver and start the internal clock."""
        self._extended_shape = extended_shape
        self._start_time = time.perf_counter()
        self._datatoexport_saver = DataToExportExtendedSaver(
            self._h5saver, extended_shape, fill_value=np.nan)

    def add_time(self, indexes: Tuple[int]):
        """Record elapsed seconds since initialize() was called at the given scan indexes."""
        if self._datatoexport_saver is not None:
            elapsed_time = float(np.float32(time.perf_counter() - self._start_time))
            dte = DataToExport('Timestamps', data=[
                DataRaw('ElapsedTime',
                        data=[np.array([elapsed_time], dtype=np.float32)],
                        units='s'),
            ])
            self._datatoexport_saver.add_data(
                self._module_group, dte, indexes=indexes,
                distribution=DataDistribution['uniform'])


class LoggerSaver(ScanSaver):
    """Implementation of the ModuleSaver class dedicated to H5Logger module

    H5Logger is the special logger to h5file of the DAQ_Logger extension

    Parameters
    ----------
    h5saver
    module
    """
    group_type = GroupModuleType.DATALOGGER
    def __init__(self, module):
        super().__init__(module)

    def update_after_h5changed(self):
        for module in self._module.modules_manager.detectors_all:
            module.module_and_data_saver = DetectorTimeSaver(module)
            module.module_and_data_saver.h5saver = self.h5saver
        for module in self._module.modules_manager.actuators_all:
            module.module_and_data_saver = ActuatorTimeSaver(module)
            module.module_and_data_saver.h5saver = self.h5saver

    def get_set_node(self, where: Union[Node, str] = None, new=False) -> GROUP:
        """Get the last group scan node

        Get the last Logger Group or create one
        get the last Scan Group if:
        * there is one already created
        * new is False

        Parameters
        ----------
        where: Union[Node, str]
            the path of a given node or the node itself
        new: bool

        Returns
        -------
        GROUP: the GROUP associated with this module
        """
        self._module_group = self.get_last_node(where)
        new = new or (self._module_group is None)
        if new:
            self._module_group = self._add_module(where)
        for module in self._module.modules_manager.modules:
            module.module_and_data_saver.main_module = False
            module.module_and_data_saver.get_set_node(self._module_group)
        return self._module_group

    def add_data(self, dte: DataToExport):
        """Add data to it's corresponding control module

        The name of the control module is the DataToExport name attribute
        """
        control_module = self._module.modules_manager.get_mod_from_name(dte.name, ModuleType.Control)

        if control_module is not None:
            control_module.append_data(dte=dte, where=self._module_group)


class OptimizerSaver(ScanSaver):
    """Implementation of the ModuleSaver class dedicated to Optimizer based modules

    Parameters
    ----------
    h5saver
    module
    """
    group_type = GroupModuleType.OPTIMIZER

    def __init__(self, module,
                 enl_axis_names: Iterable[str] = None,
                 enl_axis_units: Iterable[str] = None):
        super().__init__(module)
        self.enl_axis_names = enl_axis_names
        self.enl_axis_units = enl_axis_units

    def update_after_h5changed(self):
        for module in self._module.modules_manager.detectors:
            module.module_and_data_saver = DetectorEnlargeableSaver(
                module, self.enl_axis_names, self.enl_axis_units)
            module.module_and_data_saver.h5saver = self.h5saver
        self._time_saver.h5saver = self.h5saver


    def add_data(self, *args, axis_values: List[Union[float, np.ndarray]] = None,
                 **kwargs):
        for module in self._module.modules_manager.detectors:
            try:
                module.append_data(where=self._module_group,
                                   axis_values=axis_values,
                                   **kwargs)
            except Exception as e:
                logger.exception(f'Cannot append data: {str(e)}')

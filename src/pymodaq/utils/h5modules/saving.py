# -*- coding: utf-8 -*-
"""
Created the 15/11/2022

@author: Sebastien Weber
"""
import copy
import datetime
from dateutil import parser
from numbers import Number
import os
from pathlib import Path
from typing import Union, Iterable


import numpy as np
from qtpy.QtCore import QObject, Signal
from qtpy import QtWidgets

from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.parameter import Parameter, ParameterTree
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.managers.parameter_manager import ParameterManager
from pymodaq.utils.gui_utils.file_io import select_file

from pymodaq.utils.gui_utils.utils import dashboard_submodules_params
from pymodaq.utils import daq_utils as utils
from pymodaq.utils.config import Config
from pymodaq.utils.data import DataDim, DataToExport, Axis, DataWithAxes
from pymodaq.utils.enums import BaseEnum, enum_checker
from pymodaq.utils.scanner.utils import ScanType
from pymodaq.utils.messenger import deprecation_msg


from .backends import (H5Backend, backends_available, SaveType, InvalidSave, InvalidExport, InvalidDataType,
                       InvalidGroupType, InvalidGroupDataType, Node, GroupType, InvalidDataDimension, InvalidScanType,
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


class H5SaverLowLevel(H5Backend):
    """Object containing basic methods in order to structure and interact with a h5file compatible with the h5browser

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

    def init_file(self, file_name: Path, raw_group_name='RawData', new_file=False, metadata: dict = None):
        """Initializes a new h5 file.

        Parameters
        ----------
        file_name: Path
            a complete Path pointing to a h5 file
        raw_group_name: str
            Base node name
        new_file: bool
            If True create a new file, otherwise append to a potential existing one

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
            self.h5_file_name = select_file(save=True, ext='h5')
            self.h5_file_path = self.h5_file_name.parent
            new_file = True

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
        if filename is None:
            filename = select_file(None, save=True, ext='h5')
        if filename != '':
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
                array_type = config('data_saving', 'data_type', 'dynamic')
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

    def get_set_group(self, where, name, title=''):
        """Get the group located at where if it exists otherwise creates it

        This also set the _current_group property
        """
        self._current_group = super().get_set_group(where, name, title)
        return self._current_group

    def get_groups(self, where: Union[str, GROUP], group_type: GroupType):
        """Get all groups hanging from a Group and of a certain type"""
        groups = []
        for node_name in list(self.get_children(where)):
            group = self.get_node(where, node_name)
            if 'type' in group.attrs and group.attrs['type'] == group_type.name:
                groups.append(group)
        return groups

    def get_last_group(self, where: GROUP, group_type: GroupType):
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

    def add_data_group(self, where, data_dim: DataDim, title='', settings_as_xml='', metadata=dict([])):
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
        data_dim = enum_checker(DataDim, data_dim)
        metadata.update(settings=settings_as_xml)
        group = self.add_group(data_dim.name, 'data_dim', where, title, metadata)
        return group

    def add_incremental_group(self, group_type, where, title='', settings_as_xml='', metadata=dict([])):
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
        group_type = enum_checker(GroupType, group_type)

        nodes = [name for name in self.get_children(self.get_node(where))]
        nodes_tmp = []
        for node in nodes:
            if utils.capitalize(group_type.name) in node:
                nodes_tmp.append(node)
        nodes_tmp.sort()
        if len(nodes_tmp) == 0:
            ind_group = -1
        else:
            ind_group = int(nodes_tmp[-1][-3:])
        group = self.get_set_group(where, f'{utils.capitalize(group_type.name)}{ind_group + 1:03d}', title)
        self.set_attr(group, 'settings', settings_as_xml)
        if group_type.name.lower() != 'ch':
            self.set_attr(group, 'type', group_type.name.lower())
        else:
            self.set_attr(group, 'type', '')
        for metadat in metadata:
            self.set_attr(group, metadat, metadata[metadat])
        return group

    def add_act_group(self, where, title='', settings_as_xml='', metadata=dict([])):
        """
        Add a new group of type detector
        See Also
        -------
        add_incremental_group
        """
        group = self.add_incremental_group('actuator', where, title, settings_as_xml, metadata)
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

    def add_scan_group(self, where='/RawData', title='', settings_as_xml='', metadata=dict([])):
        """Add a new group of type scan

        At creation adds the attributes description and scan_done to be used elsewhere

        See Also
        -------
        add_incremental_group
        """
        metadata.update(dict(description='', scan_done=False))
        group = self.add_incremental_group(GroupType['scan'], where, title, settings_as_xml, metadata)
        return group

    def add_ch_group(self, where, title='', settings_as_xml='', metadata=dict([])):
        """
        Add a new group of type channel
        See Also
        -------
        add_incremental_group
        """
        group = self.add_incremental_group('ch', where, title, settings_as_xml, metadata)
        return group


    def add_move_group(self, where, title='', settings_as_xml='', metadata=dict([])):
        """
        Add a new group of type actuator
        See Also
        -------
        add_incremental_group
        """
        group = self.add_incremental_group('actuator', where, title, settings_as_xml, metadata)
        return group

    def show_file_content(self):
        win = QtWidgets.QMainWindow()
        if not self.isopen():
            if self.h5_file_path is not None:
                if self.h5_file_path.exists():
                    self.analysis_prog = browsing.H5Browser(win, h5file_path=self.h5_file_path)
                else:
                    logger.warning('The h5 file path has not been defined yet')
            else:
                logger.warning('The h5 file path has not been defined yet')
        else:
            self.flush()
            self.analysis_prog = browsing.H5Browser(win, h5file=self.h5file)
        win.show()


class H5SaverBase(H5SaverLowLevel, ParameterManager):
    """Object containing all methods in order to save datas in a *hdf5 file* with a hierarchy compatible with
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
                  Signal signal represented by a float. Is emitted each time the hardware reached the target
                  position within the epsilon precision (see comon_parameters variable)
    save_type: str
       an element of the enum module attribute SaveType
       * 'scan' is used for DAQScan module and should be used for similar application
       * 'detector' is used for DAQ_Viewer module and should be used for similar application
       * 'custom' should be used for customized applications

    Attributes
    ----------

    settings: Parameter
               Parameter instance (pyqtgraph) containing all settings (could be represented using the settings_tree widget)

    settings_tree: ParameterTree
                   Widget representing as a Tree structure, all the settings defined in the class preamble variable ``params``

    """
    settings_name = 'h5saver_settings'
    params = [
        {'title': 'Save type:', 'name': 'save_type', 'type': 'list', 'limits': SaveType.names(), 'readonly': True},
    ] + dashboard_submodules_params + \
        [{'title': 'Backend:', 'name': 'backend', 'type': 'group', 'children': [
            {'title': 'Backend type:', 'name': 'backend_type', 'type': 'list', 'limits': backends_available,
                'readonly': True},
            {'title': 'HSDS Server:', 'name': 'hsds_options', 'type': 'group', 'visible': False, 'children': [
                {'title': 'Endpoint:', 'name': 'endpoint', 'type': 'str',
                    'value': config('data_saving', 'hsds', 'root_url'), 'readonly': False},
                {'title': 'User:', 'name': 'user', 'type': 'str',
                    'value': config('data_saving', 'hsds', 'username'), 'readonly': False},
                {'title': 'password:', 'name': 'password', 'type': 'str',
                    'value': config('data_saving', 'hsds', 'pwd'), 'readonly': False},
            ]},
        ]},

        {'title': 'custom_name?:', 'name': 'custom_name', 'type': 'bool', 'default': False, 'value': False},
        {'title': 'show file content?', 'name': 'show_file', 'type': 'bool_push', 'default': False,
            'value': False},
        {'title': 'Base path:', 'name': 'base_path', 'type': 'browsepath',
            'value': config('data_saving', 'h5file', 'save_path'), 'filetype': False, 'readonly': True, },
        {'title': 'Base name:', 'name': 'base_name', 'type': 'str', 'value': 'Scan', 'readonly': True},
        {'title': 'Current scan:', 'name': 'current_scan_name', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Current path:', 'name': 'current_scan_path', 'type': 'text',
            'value': config('data_saving', 'h5file', 'save_path'), 'readonly': True, 'visible': False},
        {'title': 'h5file:', 'name': 'current_h5_file', 'type': 'text', 'value': '', 'readonly': True},
        {'title': 'New file', 'name': 'new_file', 'type': 'action'},
        {'title': 'Saving dynamic', 'name': 'dynamic', 'type': 'list',
         'limits': config('data_saving', 'data_type', 'dynamics'),
         'value': config('data_saving', 'data_type', 'dynamic')},
        {'title': 'Compression options:', 'name': 'compression_options', 'type': 'group', 'children': [
            {'title': 'Compression library:', 'name': 'h5comp_library', 'type': 'list', 'value': 'zlib',
                'limits': ['zlib', 'gzip']},
            {'title': 'Compression level:', 'name': 'h5comp_level', 'type': 'int',
                'value': config('data_saving', 'h5file', 'compression_level'), 'min': 0, 'max': 9},
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
        H5SaverLowLevel.__init__(self, save_type, backend)
        ParameterManager.__init__(self)

        self.current_scan_group = None
        self.current_scan_name = None

        self.settings.child('save_type').setValue(self.save_type.name)

    def show_settings(self, show=True):
        self.settings_tree.setVisible(show)

    def init_file(self, update_h5=False, custom_naming=False, addhoc_file_path=None, metadata=dict([])):
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
            if not os.path.isdir(self.settings['base_path']):
                os.mkdir(self.settings['base_path'])

            # set the filename and path
            base_name = self.settings['base_name']

            if not custom_naming:
                custom_naming = self.settings['custom_name']

            if not custom_naming:
                scan_type = self.settings['save_type'] == 'scan'
                scan_path, current_scan_name, save_path = self.update_file_paths(update_h5)
                self.current_scan_name = current_scan_name
                self.settings.child('current_scan_name').setValue(current_scan_name)
                self.settings.child('current_scan_path').setValue(str(scan_path))

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

        fullpathname = self.h5_file_path.joinpath(self.h5_file_name)
        self.settings.child('current_h5_file').setValue(str(fullpathname))

        super().init_file(fullpathname, new_file=update_h5, metadata=metadata)

        self.get_set_logger(self.raw_group)

        return update_h5

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
            base_path = self.settings['base_path']
            base_name = self.settings['base_name']
            current_scan = self.settings['current_scan_name']
            scan_type = self.settings['save_type'] == 'scan'
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
            self.settings.child('current_scan_path').setValue(str(dataset_path))

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
        ind_scan = next_scan_index
        return dataset_path, base_name + '{:03d}'.format(ind_scan), dataset_path

    def get_last_scan(self):
        """Gets the last scan node within the h5_file and under the **raw_group**

        Returns
        -------
        scan_group: pytables group or None


        """
        return self.get_last_group(self.raw_group, GroupType['scan'])

    def get_scan_groups(self):
        return self.get_groups(self.raw_group, GroupType['scan'])

    def get_scan_index(self):
        """ return the scan group index in the "scan templating": Scan000, Scan001 as an integer
        """

        last_scan = self.get_last_scan()
        return int(last_scan.name[4:]) if last_scan is not None else 0

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

    def value_changed(self, param):
        if param.name() == 'show_file':
            if param.value():
                param.setValue(False)
                self.show_file_content()

        elif param.name() == 'base_path':
            try:
                if not os.path.isdir(param.value()):
                    os.mkdir(param.value())
            except Exception as e:
                self.update_status(f"The base path couldn't be set, please check your options: {str(e)}")

        elif param.name() in putils.iter_children(self.settings.child('compression_options'), []):
            compression = self.settings.child('compression_options', 'h5comp_library').value()
            compression_opts = self.settings.child('compression_options', 'h5comp_level').value()
            self.define_compression(compression, compression_opts)

    def update_status(self, status):
        logger.warning(status)


class H5Saver(H5SaverBase, QObject):
    """
    status_sig: Signal
                emits a signal of type Threadcommand in order to senf log information to a main UI
    new_file_sig: Signal
                  emits a boolean signal to let the program know when the user pressed the new file button on the UI
    """

    status_sig = Signal(utils.ThreadCommand)
    new_file_sig = Signal(bool)

    def __init__(self, *args, **kwargs):
        """

        Parameters
        ----------
        args
        kwargs
        """
        QObject.__init__(self)
        H5SaverBase.__init__(self, *args, **kwargs)

        self.settings.child('new_file').sigActivated.connect(lambda: self.emit_new_file(True))

    def close(self):
        self.close_file()

    def emit_new_file(self, status):
        """Emits the new_file_sig

        Parameters
        ----------
        status: bool
                emits True if a new file has been asked by the user pressing the new file button on the UI
        """
        self.new_file_sig.emit(status)


# -*- coding: utf-8 -*-
"""
Created the 15/11/2022

@author: Sebastien Weber
"""
import os
from numbers import Number
import xml.etree.ElementTree as ET
from pymodaq.utils.logger import set_logger, get_module_name
from qtpy.QtCore import QObject, Signal

from pymodaq.utils.parameter import Parameter, ParameterTree
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.managers.parameter_manager import ParameterManager
from pymodaq.utils.gui_utils.file_io import select_file
from pymodaq.utils.parameter import ioxml
from pymodaq.utils.gui_utils.utils import dashboard_submodules_params

from qtpy import QtWidgets
from pymodaq.utils import daq_utils as utils
from pymodaq.utils.config import Config
from pymodaq.utils.data import DataDim, DataToExport
from pymodaq.control_modules.daq_viewer import DAQ_Viewer

import datetime
from dateutil import parser
import numpy as np
from pathlib import Path
import copy


from .backends import (H5Backend, backends_available, SaveTypeEnum, InvalidSave, InvalidExport, InvalidDataType,
                       InvalidGroupType, InvalidGroupDataType, Node, group_types, InvalidDataDimension, InvalidScanType,
                       data_types, scan_types, data_dimensions, Group)

from .browsing import H5Browser


config = Config()

logger = set_logger(get_module_name(__file__))


group_data_types = ['data0D', 'data1D', 'data2D', 'dataND']


class H5SaverBase(H5Backend, ParameterManager):
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
       an element of the enum module attribute SaveTypeEnum
       * 'scan' is used for DAQ_Scan module and should be used for similar application
       * 'detector' is used for DAQ_Viewer module and should be used for similar application
       * 'custom' should be used for customized applications

    Attributes
    ----------

    settings: Parameter
               Parameter instance (pyqtgraph) containing all settings (could be represented using the settings_tree widget)

    settings_tree: ParameterTree
                   Widget representing as a Tree structure, all the settings defined in the class preamble variable ``params``

    """

    params = [
        {'title': 'Save type:', 'name': 'save_type', 'type': 'list', 'limits': SaveTypeEnum.names(), 'readonly': True},
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
        H5Backend.__init__(self, backend)
        ParameterManager.__init__(self)

        if save_type not in SaveTypeEnum.names():
            raise InvalidSave('Invalid saving type')

        self.h5_file_path = None
        self.h5_file_name = None
        self.logger_array = None
        self.file_loaded = False

        self.current_group = None
        self.current_scan_group = None
        self.current_scan_name = None
        self.raw_group = None

        self.settings.child('save_type').setValue(save_type)

    @property
    def h5_file(self):
        return self._h5file

    def init_file(self, update_h5=False, custom_naming=False, addhoc_file_path=None, metadata=dict([]),
                  raw_group_name='raw_data'):
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

        fullpathname = str(self.h5_file_path.joinpath(self.h5_file_name))
        self.settings.child('current_h5_file').setValue(fullpathname)

        if update_h5:
            self.current_scan_group = None

        scan_group = None
        if self.current_scan_group is not None:
            scan_group = self.get_node_name(self.current_scan_group)

        if update_h5:
            self.close_file()
            self.open_file(fullpathname, 'w', title='PyMoDAQ file')

        else:
            self.close_file()
            self.open_file(fullpathname, 'a', title='PyMoDAQ file')

        self.raw_group = self.get_set_group(self.root(), raw_group_name, title='Data from PyMoDAQ modules')
        self.get_set_logger(self.raw_group)

        if scan_group is not None:
            self.current_scan_group = self.get_set_group(self.raw_group, scan_group)
        else:
            self.current_scan_group = self.get_last_scan()

        self.raw_group.attrs['type'] = self.settings['save_type']  # first possibility to set a node attribute
        self.root().set_attr('file', self.h5_file_name)  # second possibility
        if update_h5:
            self.set_attr(self.root(), 'date', datetime_now.date().isoformat())
            self.set_attr(self.root(), 'time', datetime_now.time().isoformat())
            for metadat in metadata:
                self.raw_group.attrs[metadat] = metadata[metadat]
        return update_h5

    def add_scan_group(self, title='', settings_as_xml='', metadata=dict([])):
        """
        Add a new group of type scan
        See Also
        -------
        add_incremental_group
        """
        if self.current_scan_group is not None:
            if len(self.get_children(self.current_scan_group)) == 0:
                new_scan = False
            else:
                new_scan = True
        else:
            new_scan = True
        if new_scan:
            self.current_scan_group = self.add_incremental_group('scan', self.raw_group, title, settings_as_xml,
                                                                 metadata)
            self.set_attr(self.current_scan_group, 'description', '')
            self.settings.child('current_scan_name').setValue(self.get_node_name(self.current_scan_group))

        return self.current_scan_group

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
        """Gets the last scan node within the h5_file and under the the **raw_group**

        Returns
        -------
        scan_group: pytables group or None


        """
        groups = [group for group in list(self.get_children(self.raw_group)) if 'Scan' in group]
        groups.sort()
        if len(groups) != 0:
            scan_group = self.get_node(self.raw_group, groups[-1])
        else:
            scan_group = None
        return scan_group

    def get_scan_index(self):
        """ return the scan group index in the "scan templating": Scan000, Scan001 as an integer
        """
        try:
            if self.current_scan_group is None:
                return 0
            else:

                groups = [group for group in self.get_children(self.raw_group) if 'Scan' in group]
                groups.sort()
                flag = False
                if len(groups) != 0:
                    if 'scan_done' in self.get_attr(self.get_node(self.raw_group, groups[-1])):
                        if self.get_attr(self.get_node(self.raw_group, groups[-1]), 'scan_done'):
                            return len(groups)
                        return len(groups) - 1
                    return len(groups) - 1
                return 0

        except Exception as e:
            logger.exception(str(e))

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

    def get_set_logger(self, where):
        """ Retrieve or create (if absent) a logger enlargeable array to store logs
        Get attributed to the class attribute ``logger_array``
        Parameters
        ----------
        where: node
               location within the tree where to save or retrieve the array

        Returns
        -------
        logger_array: vlarray
                      enlargeable array accepting strings as elements
        """
        if isinstance(where, Node):
            where = where.node
        logger = 'Logger'
        if logger not in list(self.get_children(where)):
            # check if logger node exist
            self.logger_array = self.add_string_array(where, logger)
            self.logger_array.attrs['type'] = 'log'
        else:
            self.logger_array = self.get_node(where, name=logger)
        return self.logger_array

    def add_log(self, msg):
        self.logger_array.append(msg)

    def add_data_group(self, where, group_data_type, title='', settings_as_xml='', metadata=dict([])):
        """Creates a group node at given location in the tree

        Parameters
        ----------
        where: group node
               where to create data group
        group_data_type: list of str
                         either ['data0D', 'data1D', 'data2D', 'dataND']
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
        if group_data_type not in DataDim.names():
            raise InvalidGroupDataType('Invalid data group type')
        metadata.update(settings=settings_as_xml)
        group = self.add_group(group_data_type, '', where, title, metadata)
        return group

    def add_navigation_axis(self, data, parent_group, axis='x_axis', enlargeable=False, title='', metadata=dict([])):
        """
        Create carray or earray for navigation axis within a scan
        Parameters
        ----------
        data: (ndarray) of dimension 1
        parent_group: (str or node) parent node where to save new data
        axis: (str) either x_axis, y_axis, z_axis or time_axis. 'x_axis', 'y_axis', 'z_axis', 'time_axis' are axes containing scalar values (floats or ints). 'time_axis' can be interpreted as the posix timestamp corresponding to a datetime object, see datetime.timestamp()
        enlargeable: (bool) if True the created array is a earray type if False the created array is a carray type
        """

        if axis not in ['x_axis', 'y_axis', 'z_axis', 'time_axis']:
            if 'axis' not in axis:  # this take care of the case of sequential scans where axes are labelled with indexes
                raise NameError('Invalid navigation axis name')

        array = self.add_array(parent_group, f"{self.settings['save_type']}_{axis}", 'navigation_axis',
                               data_shape=data.shape,
                               data_dimension='1D', array_to_save=data, enlargeable=enlargeable, title=title,
                               metadata=metadata)
        return array

    def add_data_live_scan(self, channel_group, data_dict, scan_type='scan1D', title='', scan_subtype=''):
        isadaptive = scan_subtype == 'Adaptive'
        if not isadaptive:
            shape, dimension, size = utils.get_data_dimension(data_dict['data'], scan_type=scan_type,
                                                              remove_scan_dimension=True)
        else:
            shape, dimension, size = data_dict['data'].shape, '0D', 1
        data_array = self.add_array(channel_group, 'Data', 'data', array_type=np.float,
                                    title=title,
                                    data_shape=shape,
                                    data_dimension=dimension, scan_type=scan_type,
                                    scan_subtype=scan_subtype,
                                    array_to_save=data_dict['data'])
        if 'x_axis' in data_dict:
            if not isinstance(data_dict['x_axis'], dict):
                array_to_save = data_dict['x_axis']
                tmp_dict = dict(label='', units='')
            else:
                tmp_dict = copy.deepcopy(data_dict['x_axis'])
                array_to_save = tmp_dict.pop('data')
            self.add_array(channel_group, 'x_axis', 'axis',
                           array_type=np.float, array_to_save=array_to_save,
                           enlargeable=False, data_dimension='1D', metadata=tmp_dict)
        if 'y_axis' in data_dict:
            if not isinstance(data_dict['y_axis'], dict):
                array_to_save = data_dict['y_axis']
                tmp_dict = dict(label='', units='')
            else:
                tmp_dict = copy.deepcopy(data_dict['y_axis'])
                array_to_save = tmp_dict.pop('data')
            self.add_array(channel_group, 'y_axis', 'axis',
                           array_type=np.float, array_to_save=array_to_save,
                           enlargeable=False, data_dimension='1D', metadata=tmp_dict)
        return data_array

    def add_data(self, channel_group, data_dict, scan_type='scan1D', scan_subtype='',
                 scan_shape=[], title='', enlargeable=False,
                 init=False, add_scan_dim=False, metadata=dict([])):
        """save data within the hdf5 file together with axes data (if any) and metadata, node name will be 'Data'

        Parameters
        ----------
        channel_group: (hdf5 node) node where to save the array, in general within a channel type group
        data_dict: (dict) dictionnary containing the data to save and all the axis and metadata mandatory key: 'data':
         (ndarray) data to save other keys: 'xxx_axis' (for instance x_axis, y_axis, 'nav_x_axis'....) or background
        scan_type: (str) either '', 'scan1D' or 'scan2D' or Tabular or sequential
        scan_subtype: (str) see scanner module
        scan_shape: (iterable) the shape of the scan dimensions
        title: (str) the title attribute of the array node
        enlargeable: (bool) if False, data are save as a CARRAY, otherwise as a EARRAY (for ragged data, see add_sting_array)
        init: (bool) if True, the array saved in the h5 file is initialized with the correct type but all element equal
                     to zero. Else, the 'data' key of data_dict is saved as is
        add_scan_dim: (bool) if True, the scan axes dimension (scan_shape iterable) is prepended to the array shape on the hdf5
                      In that case, the array is usually initialized as zero and further populated
        metadata: (dict) dictionnary whose keys will be saved as the array attributes


        Returns
        -------
        array (CARRAY or EARRAY)

        See Also
        --------
        add_array, add_string_array
        """

        shape, dimension, size = utils.get_data_dimension(data_dict['data'])
        tmp_data_dict = copy.deepcopy(data_dict)
        array_type = getattr(np, self.settings['dynamic'])
        # save axis
        # this loop covers all type of axis : x_axis, y_axis... nav_x_axis, ...
        axis_keys = [k for k in tmp_data_dict.keys() if 'axis' in k]
        for key in axis_keys:
            if not isinstance(tmp_data_dict[key], dict):
                array_to_save = tmp_data_dict[key]
                tmp_dict = dict(label='', units='')
            else:
                tmp_dict = copy.deepcopy(tmp_data_dict[key])
                array_to_save = tmp_dict.pop('data')
                tmp_data_dict.pop(key)

            self.add_array(channel_group, key, 'axis', array_type=None, array_to_save=array_to_save,
                           enlargeable=False, data_dimension='1D', metadata=tmp_dict)

        array_to_save = tmp_data_dict.pop('data')
        if isinstance(array_to_save, Number) or isinstance(array_to_save, str):
            array_to_save = np.array([array_to_save])
        if 'type' in tmp_data_dict:
            tmp_data_dict.pop('type')  # otherwise this metadata would overide mandatory attribute 'type' for a h5 node

        if 'bkg' in tmp_data_dict:
            bkg = tmp_data_dict.pop('bkg')
            self.add_array(channel_group, 'Bkg', 'bkg', array_type=array_type, array_to_save=bkg,
                           data_dimension=dimension)
        tmp_data_dict.update(metadata)
        array_to_save = array_to_save.astype(array_type)
        data_array = self.add_array(channel_group, 'Data', 'data', array_type=array_type,
                                    title=title, data_shape=shape, enlargeable=enlargeable, data_dimension=dimension,
                                    scan_type=scan_type, scan_subtype=scan_subtype, scan_shape=scan_shape,
                                    array_to_save=array_to_save,
                                    init=init, add_scan_dim=add_scan_dim, metadata=tmp_data_dict)


        self.flush()
        return data_array

    def add_array(self, where, name, data_type, data_shape=None, data_dimension=None, scan_type='', scan_subtype='',
                  scan_shape=[],
                  title='', array_to_save=None, array_type=None, enlargeable=False, metadata=dict([]),
                  init=False, add_scan_dim=False):
        """save data arrays on the hdf5 file together with metadata
        Parameters
        ----------
        where: (hdf5 node) node where to save the array
        name: (str) name of the array in the hdf5 file
        data_type: (str) one of ['data', 'axis', 'live_scan', 'navigation_axis', 'external_h5', 'strings', 'bkg'], mandatory
            so that the h5Browsr interpret correctly the array (see add_data)
        data_shape: (iterable) the shape of the array to save, mandatory if array_to_save is None
        data_dimension: (str) one of ['0D', '1D', '2D', 'ND']
        scan_type: (str) either '', 'scan1D' or 'scan2D'
        scan_shape: (iterable): the shape of the scan dimensions
        title: (str) the title attribute of the array node
        array_to_save: (ndarray or None) data to be saved in the array. If None, array_type and data_shape
                        should be specified
        array_type: (np.dtype or numpy types), eg np.float, np.int32 ...
        enlargeable: (bool) if False, data are save as a CARRAY, otherwise as a EARRAY (for ragged data, see add_sting_array)
        metadata: (dict) dictionnary whose keys will be saved as the array attributes
        init: (bool) if True, the array saved in the h5 file is initialized with the correct type but all element equal
                     to zero. Else, the 'data' key of data_dict is saved as is
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
                array_type = getattr(np, self.settings.child('dynamic').value())
            else:
                array_type = array_to_save.dtype

        if data_dimension not in data_dimensions:
            raise InvalidDataDimension('Invalid data dimension')
        if data_type not in data_types:
            raise InvalidDataType('Invalid data type')
        if scan_type != '':
            scan_type = utils.uncapitalize(scan_type)
        if scan_type.lower() not in [s.lower() for s in scan_types]:
            raise InvalidScanType('Invalid scan type')
        if enlargeable:
            if data_shape == (1,):
                data_shape = None
            array = self.create_earray(where, utils.capitalize(name), dtype=np.dtype(array_type),
                                       data_shape=data_shape, title=title)
        else:
            if add_scan_dim:  # means it is an array initialization to zero
                shape = list(scan_shape[:])
                shape.extend(data_shape)
                if init or array_to_save is None:
                    array_to_save = np.zeros(shape, dtype=np.dtype(array_type))

            array = self.create_carray(where, utils.capitalize(name), obj=array_to_save, title=title)
        self.set_attr(array, 'type', data_type)
        self.set_attr(array, 'data_dimension', data_dimension)
        self.set_attr(array, 'scan_type', scan_type)
        self.set_attr(array, 'scan_subtype', scan_subtype)

        for metadat in metadata:
            self.set_attr(array, metadat, metadata[metadat])
        return array

    def add_string_array(self, where, name, title='', metadata=dict([])):
        array = self.create_vlarray(where, name, dtype='string', title=title)
        array.attrs['shape'] = (0,)
        array.attrs['data_dimension'] = '0D'
        array.attrs['scan_type'] = 'scan1D'

        for metadat in metadata:
            array.attrs[metadat] = metadata[metadat]
        return array

    def get_set_group(self, where, name, title=''):
        self.current_group = super().get_set_group(where, name, title)
        return self.current_group

    def add_incremental_group(self, group_type, where, title='', settings_as_xml='', metadata=dict([])):
        """
        Add a node in the h5 file tree of the group type with an increment in the given name
        Parameters
        ----------
        group_type: (str) one of the possible values of **group_types**
        where: (str or node) parent node where to create the new group
        title: (str) node title
        settings_as_xml: (str) XML string containing Parameters representation (see custom_Tree)
        metadata: (dict) extra metadata to be saved with this new group node

        Returns
        -------
        (node): newly created group node
        """
        if group_type not in group_types:
            raise InvalidGroupType('Invalid group type')
        nodes = [name for name in self.get_children(self.get_node(where))]
        nodes_tmp = []
        for node in nodes:
            if utils.capitalize(group_type) in node:
                nodes_tmp.append(node)
        nodes_tmp.sort()
        if len(nodes_tmp) == 0:
            ind_group = -1
        else:
            ind_group = int(nodes_tmp[-1][-3:])
        group = self.get_set_group(where, utils.capitalize(group_type) + '{:03d}'.format(ind_group + 1), title)
        self.set_attr(group, 'settings', settings_as_xml)
        if group_type.lower() != 'ch':
            self.set_attr(group, 'type', group_type.lower())
        else:
            self.set_attr(group, 'type', '')
        for metadat in metadata:
            self.set_attr(group, metadat, metadata[metadat])
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

    def add_CH_group(self, where, title='', settings_as_xml='', metadata=dict([])):
        """
        Add a new group of type channel
        See Also
        -------
        add_incremental_group
        """
        group = self.add_incremental_group('ch', where, title, settings_as_xml, metadata)
        return group

    def add_live_scan_group(self, where, dimensionality, title='', settings_as_xml='', metadata=dict([])):
        """
        Add a new group of type live scan
        See Also
        -------
        add_incremental_group
        """
        metadata.update(settings=settings_as_xml)
        group = self.add_group(utils.capitalize('Live_scan_{:s}'.format(dimensionality)), '', where, title=title,
                               metadata=metadata)
        return group

    def add_move_group(self, where, title='', settings_as_xml='', metadata=dict([])):
        """
        Add a new group of type move
        See Also
        -------
        add_incremental_group
        """
        group = self.add_incremental_group('move', where, title, settings_as_xml, metadata)
        return group

    def value_changed(self, param):
        if param.name() == 'show_file':
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

    def show_file_content(self):
        form = QtWidgets.QWidget()
        if not self.isopen():
            if self.h5_file_path is not None:
                if self.h5_file_path.exists():
                    self.analysis_prog = H5Browser(form, h5file_path=self.h5_file_path)
                else:
                    logger.warning('The h5 file path has not been defined yet')
            else:
                logger.warning('The h5 file path has not been defined yet')
        else:
            self.flush()
            self.analysis_prog = H5Browser(form, h5file=self.h5file)
        form.show()


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


class DetectorDataSaver:
    def __init__(self, path: Path = None):

        if path is not None:
            path = Path(path)
            
        self._det_group: Group = None

        self.h5saver = H5Saver(save_type='detector')
        self.h5saver.init_file(update_h5=True, custom_naming=False, addhoc_file_path=path)

    def add_detector(self, detector: DAQ_Viewer):
        settings_xml = ET.Element('All_settings')
        settings_xml.append(ioxml.walk_parameters_to_xml(param=detector.settings))
        settings_xml.append(ioxml.walk_parameters_to_xml(param=self.h5saver.settings))

        if self.ui is not None:
            for ind, viewer in enumerate(detector.viewers):
                if hasattr(viewer, 'roi_manager'):
                    roi_xml = ET.SubElement(settings_xml, f'ROI_Viewer_{ind:02d}')
                    roi_xml.append(ioxml.walk_parameters_to_xml(viewer.roi_manager.settings))

        self._det_group = self.h5saver.add_det_group(self.h5saver.raw_group, "Data", ET.tostring(settings_xml))

    def add_external_h5(self, external_h5_file):

        external_group = self.h5saver.add_group('external_data', 'external_h5', self._det_group)
        if not external_h5_file.isopen:
            h5saver = H5Saver()
            h5saver.init_file(addhoc_file_path=external_h5_file.filename)
            h5_file = h5saver.h5_file
        else:
            h5_file = external_h5_file
        h5_file.copy_children(h5_file.get_node('/'), external_group, recursive=True)
        h5_file.flush()
        h5_file.close()

    def add_data(self, data: DataToExport):

    try:
        self._channel_arrays = OrderedDict([])
        data_dims = ['data1D']  # we don't recrod 0D data in this mode (only in continuous)
        if h5saver.settings.child(('save_2D')).value():
            data_dims.extend(['data2D', 'dataND'])

        if self._bkg is not None and self._do_bkg:
            bkg_container = OrderedDict([])
            self._process_data(self._bkg, bkg_container)

        for data_dim in data_dims:
            if data[data_dim] is not None:
                if data_dim in data.keys() and len(data[data_dim]) != 0:
                    if not h5saver.is_node_in_group(det_group, data_dim):
                        self._channel_arrays[data_dim] = OrderedDict([])

                        data_group = h5saver.add_data_group(det_group, data_dim)
                        for ind_channel, channel in enumerate(data[data_dim]):  # list of OrderedDict

                            channel_group = h5saver.add_CH_group(data_group, title=channel)

                            self._channel_arrays[data_dim]['parent'] = channel_group
                            if self._bkg is not None and self._do_bkg:
                                if channel in bkg_container[data_dim]:
                                    data[data_dim][channel]['bkg'] = bkg_container[data_dim][channel]['data']
                            self._channel_arrays[data_dim][channel] = h5saver.add_data(channel_group,
                                                                                       data[data_dim][channel],
                                                                                       scan_type='',
                                                                                       enlargeable=False)

                            if data_dim == 'data2D' and 'Data2D' in self._viewer_types.names():
                                ind_viewer = self._viewer_types.names().index('Data2D')
                                string = pymodaq.utils.gui_utils.utils.widget_to_png_to_bytes(
                                    self.viewers[ind_viewer].parent)
                                self._channel_arrays[data_dim][channel].attrs['pixmap2D'] = string
    except Exception as e:
        self.logger.exception(str(e))

    try:
        if self.ui is not None:
            (root, filename) = os.path.split(str(path))
            filename, ext = os.path.splitext(filename)
            image_path = os.path.join(root, filename + '.png')
            self.dockarea.parent().grab().save(image_path)
    except Exception as e:
        self.logger.exception(str(e))

    h5saver.close_file()
    self.data_saved.emit()

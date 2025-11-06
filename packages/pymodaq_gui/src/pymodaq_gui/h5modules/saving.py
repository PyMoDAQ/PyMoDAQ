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

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import utils
from pymodaq_utils.config import Config

from pymodaq_data.h5modules.backends import (
    H5Backend, backends_available, SaveType,
    GroupType, InvalidDataDimension, InvalidScanType,
    GROUP, VLARRAY)
from pymodaq_data.h5modules.saving import H5SaverLowLevel

from pymodaq_gui.parameter import Parameter, ParameterTree
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.utils.file_io import select_file
from pymodaq_gui.h5modules import browsing

config = Config()
logger = set_logger(get_module_name(__file__))


dashboard_submodules_params = [
    {'title': 'Save 2D datas and above:', 'name': 'save_2D', 'type': 'bool', 'value': True},
    {'title': 'Save raw datas only:', 'name': 'save_raw_only', 'type': 'bool', 'value': True, 'tooltip':
        'if True, will not save extracted ROIs used to do live plotting, only raw datas will be saved'},
    {'title': 'Do Save:', 'name': 'do_save', 'type': 'bool', 'default': False, 'value': False},
    {'title': 'N saved:', 'name': 'N_saved', 'type': 'int', 'default': 0, 'value': 0, 'visible': False},
]


class H5SaverBase(H5SaverLowLevel, ParameterManager):
    """Object containing all methods in order to save datas in a *hdf5 file* with a hierarchy
    compatible with the H5Browser. The saving parameters are contained within a **Parameter**
    object: self.settings that can be displayed on a UI using the widget self.settings_tree.
    At the creation of a new file, a node group named **Raw_data** and represented by the attribute
    ``raw_group`` is created and set with a metadata attribute:

    * 'type' given by the **save_type** class parameter

    The root group of the file is then set with a few metadata:

    * 'pymodaq_version' the current pymodaq version, e.g. 1.6.2
    * 'pymodaq_data_version' the current pymodaq_data version, e.g. 0.0.1
    * 'file' the file name
    * 'date' the current date
    * 'time' the current time

    All data will then be saved under this node in various groups

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
        {'title': 'Save type:', 'name': 'save_type', 'type': 'list', 'limits': SaveType.names(),
         'readonly': True},
    ] + dashboard_submodules_params + \
        [
            {'title': 'Backend:', 'name': 'backend', 'type': 'group', 'children': [
            {'title': 'Backend type:', 'name': 'backend_type', 'type': 'list',
             'limits': backends_available, 'readonly': True},
            {'title': 'HSDS Server:', 'name': 'hsds_options', 'type': 'group', 'visible': False,
             'children': [
                {'title': 'Endpoint:', 'name': 'endpoint', 'type': 'str',
                    'value': config('data_saving', 'hsds', 'root_url'), 'readonly': False},
                {'title': 'User:', 'name': 'user', 'type': 'str',
                    'value': config('data_saving', 'hsds', 'username'), 'readonly': False},
                {'title': 'password:', 'name': 'password', 'type': 'str',
                    'value': config('data_saving', 'hsds', 'pwd'), 'readonly': False},
            ]},
        ]},
        {'title': 'custom_name?:', 'name': 'custom_name', 'type': 'bool', 'default': False,
         'value': False},
        {'title': 'show file content?', 'name': 'show_file', 'type': 'bool_push', 'default': False,
            'value': False},
        {'title': 'Base path:', 'name': 'base_path', 'type': 'browsepath',
            'value': config('data_saving', 'h5file', 'save_path'), 'filetype': False,
         'readonly': True, },
        {'title': 'Base name:', 'name': 'base_name', 'type': 'str', 'value': 'Scan',
         'readonly': True},
        {'title': 'Current scan:', 'name': 'current_scan_name', 'type': 'str', 'value': '',
         'readonly': True},
        {'title': 'Current path:', 'name': 'current_scan_path', 'type': 'text',
            'value': config('data_saving', 'h5file', 'save_path'), 'readonly': True,
         'visible': False},
        {'title': 'h5file:', 'name': 'current_h5_file', 'type': 'text', 'value': '',
         'readonly': True},
        {'title': 'New file', 'name': 'new_file', 'type': 'action'},
        {'title': 'Saving dynamic', 'name': 'dynamic', 'type': 'list',
         'limits': config('data_saving', 'data_type', 'dynamics'),
         'value': config('data_saving', 'data_type', 'dynamic')},
        {'title': 'Compression options:', 'name': 'compression_options', 'type': 'group',
         'children': [
            {'title': 'Compression library:', 'name': 'h5comp_library', 'type': 'list',
             'value': 'zlib', 'limits': ['zlib', 'gzip']},
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

    def init_file(self, update_h5=False, custom_naming=False, addhoc_file_path=None,
                  metadata=dict([])):
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
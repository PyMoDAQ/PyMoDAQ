# -*- coding: utf-8 -*-
"""
Created the 15/11/2022

@author: Sebastien Weber
"""
from typing import Tuple
import os
from collections import OrderedDict
from typing import List
import warnings
import logging
import webbrowser
import numpy as np
from pathlib import Path
from packaging import version as version_mod

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import Config
from .backends import H5Backend
from .exporter import ExporterFactory

config = Config()
logger = set_logger(get_module_name(__file__))


class H5BrowserUtil(H5Backend):
    """Utility object to interact and get info and data from a hdf5 file

    Inherits H5Backend and all its functionalities

    Parameters
    ----------
    backend: str
        The used hdf5 backend: either tables, h5py or h5pyd
    """
    def __init__(self, backend='tables'):
        super().__init__(backend=backend)

    def export_data(self, node_path='/', filesavename: str = 'datafile.h5', filter=None):
        """Initialize the correct exporter and export the node"""

        # Format the node and file type
        filepath = Path(filesavename)
        node = self.get_node(node_path)
        # Separate dot from extension
        extension = filepath.suffix[1:]
        # Obtain the suitable exporter object
        exporter = ExporterFactory.create_exporter(
            extension,
            ExporterFactory.get_format_from_filter(filter))
        # Export the data
        exporter.export_data(node, filepath)

    def get_h5file_scans(self, where='/'):
        """Get the list of the scan nodes in the file

        Parameters
        ----------
        where: str
            the path in the file

        Returns
        -------
        list of dict
            dict with keys: scan_name, path (within the file) and data (the live scan png image)
        """
        # TODO add a test for this method
        scan_list = []
        where = self.get_node(where)
        for node in self.walk_nodes(where):
            if 'pixmap2D' in node.attrs:
                scan_list.append(
                    dict(scan_name='{:s}_{:s}'.format(node.parent_node.name, node.name), path=node.path,
                         data=node.attrs['pixmap2D']))

        return scan_list

    def get_h5_attributes(self, node_path):
        """
        """
        node = self.get_node(node_path)
        attrs_names = node.attrs.attrs_name
        attr_dict = OrderedDict(node.attrs.to_dict())

        settings = None
        scan_settings = None
        if 'settings' in attrs_names:
            if node.attrs['settings'] != '':
                settings = node.attrs['settings']

        if 'scan_settings' in attrs_names:
            if node.attrs['scan_settings'] != '':
                scan_settings = node.attrs['scan_settings']
        pixmaps = []
        for attr in attrs_names:
            if 'pixmap' in attr:
                pixmaps.append(node.attrs[attr])

        return attr_dict, settings, scan_settings, pixmaps


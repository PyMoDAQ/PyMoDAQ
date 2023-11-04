# -*- coding: utf-8 -*-
"""
Created the 02/03/2023

@author: Nicolas Tappy
"""
# Standard imports
from abc import ABCMeta, abstractmethod
from typing import Callable

# 3rd party imports
import numpy as np

# project imports
from pymodaq.utils.h5modules.backends import H5Backend, Node
from pymodaq.utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))


class H5Exporter(metaclass=ABCMeta):
    """Base class for an exporter. """

    # This is to define an abstract class attribute
    @classmethod
    @property
    @abstractmethod
    def FORMAT_DESCRIPTION(cls):
        """str: file format description as a short text. eg: text file"""
        raise NotImplementedError

    @classmethod
    @property
    @abstractmethod
    def FORMAT_EXTENSION(cls):
        """str: File format extension. eg: txt"""
        raise NotImplementedError

    def __init__(self):
        """Abstract Exporter Constructor"""
        pass

    @abstractmethod
    def export_data(self, node: Node, filename: str) -> None:
        """Abstract method to save a .h5 node to a file"""
        pass


class ExporterFactory:
    """The factory class for creating executors"""

    exporters_registry = {}
    file_filters = {}

    @classmethod
    def register_exporter(cls) -> Callable:
        """Class decorator method to register exporter class to the internal registry. Must be used as
        decorator above the definition of an H5Exporter class. H5Exporter must implement specific class
        attributes and methods, see definition: h5node_exporter.H5Exporter
        See h5node_exporter.H5txtExporter and h5node_exporter.H5txtExporter for usage examples.
        returns:
            the exporter class
        """

        def inner_wrapper(wrapped_class) -> Callable:
            extension = wrapped_class.FORMAT_EXTENSION
            format_desc = wrapped_class.FORMAT_DESCRIPTION

            if extension not in cls.exporters_registry:
                cls.exporters_registry[extension] = {}
            if filter not in cls.exporters_registry[extension]:
                cls.exporters_registry[extension][format_desc] = wrapped_class

            # Return wrapped_class
            return wrapped_class

        # Return decorated function
        return inner_wrapper

    @classmethod
    def create_exporter(cls, extension: str, filter: str) -> H5Exporter:
        """Factory command to create the exporter object.
        This method gets the appropriate executor class from the registry
        and instantiates it.
        Parameters
        ----------
        extension: str
            the extension of the file that will be exported
        filter: str
            the filter string
        Returns
        -------
        an instance of the executor created
        """
        if extension not in cls.exporters_registry:
            raise ValueError(f".{extension} is not a supported file format.")
        elif filter not in cls.exporters_registry[extension]:
            raise ValueError(f".{filter} is not a supported file description.")

        return cls.exporters_registry[extension][filter]()

    @classmethod
    def get_file_filters(cls):
        """Create the file filters string"""
        tmp_list = []
        for extension in cls.exporters_registry:
            for format_desc in cls.exporters_registry[extension]:
                tmp_list.append(f"{format_desc} (*.{extension})")
        return ";;".join(tmp_list)

    @staticmethod
    def get_format_from_filter(filter: str):
        """Returns the string format description removing the extension part"""
        return filter.split(' (*')[0]






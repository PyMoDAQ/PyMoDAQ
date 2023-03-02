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
            # Warn if overriding existing exporter
            if extension in cls.exporters_registry:
                logger.warning(f"Exporter for the .{extension} format already exists and will be replaced")

            # Register extension
            cls.exporters_registry[extension] = wrapped_class
            cls.file_filters[extension] = wrapped_class.FORMAT_DESCRIPTION
            # Return wrapped_class
            return wrapped_class

        # Return decorated function
        return inner_wrapper

    @classmethod
    def create_exporter(cls, extension: str):
        """Factory command to create the exporter object.
            This method gets the appropriate executor class from the registry
            and instantiates it.
            Args:
                extension (str): the extension of the file that will be exported
            returns:
                an instance of the executor created
        """
        if extension not in cls.exporters_registry:
            raise ValueError(f".{extension} is not a supported file format.")

        exporter_class = cls.exporters_registry[extension]

        exporter = exporter_class()

        return exporter

    @classmethod
    def get_file_filters(cls):
        """Create the file filters string"""
        tmplist = [f"{v} (*.{k})" for k, v in cls.file_filters.items()]
        return ";;".join(tmplist)


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





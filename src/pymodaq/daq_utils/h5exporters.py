# Standard imports
from abc import ABCMeta, abstractmethod
from typing import Callable

# 3rd party imports
import numpy as np

# project imports
from pymodaq.daq_utils.h5backend import H5Backend, Node
from pymodaq.daq_utils.daq_utils import set_logger, get_module_name

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
    def _export_data(self, node: Node, filename: str) -> None:
        """Abstract method to save a .h5 node to a file"""
        pass


@ExporterFactory.register_exporter()
class H5h5Exporter(H5Exporter):
    """ Exporter object for saving nodes as single h5 files"""

    FORMAT_DESCRIPTION = "Single node h5 file"
    FORMAT_EXTENSION = "h5"

    def _export_data(self, node: Node, filename: str) -> None:
        """Export an h5 node"""
        # This should allow to get the base file object
        if node.backend == 'tables':
            basefile = node.node._v_file
            basefile.copy_file(dstfilename=str(filename), overwrite=False)
        else:
            import h5py
            with h5py.File(filename, 'w') as f_dest:
                node.node.h5file.copy(self.h5file, f_dest)

        # basefile = node.get_file()
        # basefile.copy_file(dstfilename=str(filename), overwrite=False)

        new_file = H5Backend(backend="tables")
        new_file.open_file(str(filename), 'a')

        new_file.h5file.move_node(self.get_node_path(node), newparent=new_file.h5file.get_node('/'))
        new_file.h5file.remove_node('/Raw_datas', recursive=True)
        new_file.close_file()


@ExporterFactory.register_exporter()
class H5txtExporter(H5Exporter):
    """ Exporter object for saving nodes as txt files"""

    FORMAT_DESCRIPTION = "Text files"
    FORMAT_EXTENSION = "txt"

    def _export_data(self, node: Node, filename: str) -> None:
        """Export the node as a .txt file format"""
        if 'ARRAY' in node.attrs['CLASS']:
            data = node.read()
            if not isinstance(data, np.ndarray):
                # in case one has a list of same objects (array of strings for instance, logger or other)
                data = np.array(data)
                np.savetxt(filename, data, '%s', '\t')
            else:
                np.savetxt(filename, data, '%.6e', '\t')
        elif 'GROUP' in node.attrs['CLASS']:
            data_tot = []
            header = []
            dtypes = []
            fmts = []
            for subnode_name, subnode in node.children().items():
                if 'ARRAY' in subnode.attrs['CLASS']:
                    if len(subnode.attrs['shape']) == 1:
                        data = subnode.read()
                        if not isinstance(data, np.ndarray):
                            # in case one has a list of same objects (array of strings for instance, logger or other)
                            data = np.array(data)
                        data_tot.append(data)
                        dtypes.append((subnode_name, data.dtype))
                        header.append(subnode_name)
                        if data.dtype.char == 'U':
                            fmt = '%s'  # for strings
                        elif data.dtype.char == 'l':
                            fmt = '%d'  # for integers
                        else:
                            fmt = '%.6f'  # for decimal numbers
                        fmts.append(fmt)

            data_trans = np.array(list(zip(*data_tot)), dtype=dtypes)
            np.savetxt(filename, data_trans, fmts, '\t', header='#' + '\t'.join(header))


@ExporterFactory.register_exporter()
class H5asciiExporter(H5Exporter):
    """ Exporter object for saving nodes as txt files"""

    FORMAT_DESCRIPTION = "Ascii file"
    FORMAT_EXTENSION = "ascii"

    def _export_data(self, node: Node, filename: str) -> None:
        if 'ARRAY' in node.attrs['CLASS']:
            data = node.read()
            if not isinstance(data, np.ndarray):
                # in case one has a list of same objects (array of strings for instance, logger or other)
                data = np.array(data)
                np.savetxt(filename,
                           data.T if len(data.shape) > 1 else [data],
                           '%s', '\t')
            else:
                np.savetxt(filename,
                           data.T if len(data.shape) > 1 else [data],
                           '%.6e', '\t')

        elif 'GROUP' in node.attrs['CLASS']:
            data_tot = []
            header = []
            dtypes = []
            fmts = []
            for subnode_name, subnode in node.children().items():
                if 'ARRAY' in subnode.attrs['CLASS']:
                    if len(subnode.attrs['shape']) == 1:
                        data = subnode.read()
                        if not isinstance(data, np.ndarray):
                            # in case one has a list of same objects (array of strings for instance, logger or other)
                            data = np.array(data)
                        data_tot.append(data)
                        dtypes.append((subnode_name, data.dtype))
                        header.append(subnode_name)
                        if data.dtype.char == 'U':
                            fmt = '%s'  # for strings
                        elif data.dtype.char == 'l':
                            fmt = '%d'  # for integers
                        else:
                            fmt = '%.6f'  # for decimal numbers
                        fmts.append(fmt)

            data_trans = np.array(list(zip(*data_tot)), dtype=dtypes)

            np.savetxt(filename, data_trans, fmts, '\t', header='#' + '\t'.join(header))


@ExporterFactory.register_exporter()
class H5npyExporter(H5Exporter):
    """ Exporter object for saving nodes as npy files"""

    FORMAT_DESCRIPTION = "Binary NumPy format"
    FORMAT_EXTENSION = "npy"

    def _export_data(self, node: Node, filename: str) -> None:
        """Export the node as a numpy binary file format"""
        # String __contain__ method will evaluate to True for CARRAY,EARRAY,VLARRAY,stringARRAY
        if 'ARRAY' in node.attrs['CLASS']:
            data = node.read()
            if not isinstance(data, np.ndarray):
                data = np.array(data)

            np.save(filename, data)
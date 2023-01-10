# Standard imports
from abc import ABCMeta, abstractmethod

# 3rd party imports
import numpy as np

# project imports
from pymodaq.daq_utils.h5modules import H5BrowserUtil,H5Backend


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
    def _export_data(self, node, filename) -> None:
        """Abstract method to save a .h5 node to a file"""
        pass

@H5BrowserUtil.register_exporter()
class H5h5Exporter(H5Exporter):
    """ Exporter object for saving nodes as single h5 files"""

    FORMAT_DESCRIPTION = "Single node h5 file"
    FORMAT_EXTENSION = "h5"

    def _export_data(self, node, filename) -> None:
        """Export an h5 node"""
        #This should allow to get the base file object
        basefile = node._v_file
        basefile.copy_file(dstfilename=str(filename), overwrite=False)

        new_file = H5Backend(backend="tables")
        new_file.open_file(str(filename), 'a')

        new_file.h5file.move_node(self.get_node_path(node), newparent=new_file.h5file.get_node('/'))
        new_file.h5file.remove_node('/Raw_datas', recursive=True)
        new_file.close_file()

@H5BrowserUtil.register_exporter()
class H5txtExporter(H5Exporter):
    """ Exporter object for saving nodes as txt files"""

    FORMAT_DESCRIPTION = "Text files"
    FORMAT_EXTENSION = "txt"

    def _export_data(self, node, filename) -> None:
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

@H5BrowserUtil.register_exporter()
class H5asciiExporter(H5Exporter):
    """ Exporter object for saving nodes as txt files"""

    FORMAT_DESCRIPTION = "Ascii file"
    FORMAT_EXTENSION = "ascii"

    def _export_data(self, node, filename) -> None:
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
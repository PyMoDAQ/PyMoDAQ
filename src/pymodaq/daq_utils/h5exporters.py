# Standard imports
from abc import ABCMeta, abstractmethod
from typing import Callable, Union
import importlib

# 3rd party imports
import numpy as np

# project imports
from pymodaq.daq_utils.h5backend import H5Backend, Node
from pymodaq.daq_utils.h5utils import get_h5_data_from_node
from pymodaq.daq_utils.daq_utils import set_logger, get_module_name, Axis

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


# This Exporter depends on the availability of the hyperspy package.
# In the future, adding an optional dependency
found = importlib.util.find_spec("hyperspy")
if not found:
    logger.warning('Hyperspy module not found. To save data in the .hspy format, install hyperspy 1.7 or more recent.')
else:
    from hyperspy.axes import UniformDataAxis, DataAxis
    import hyperspy.api_nogui as hs


    @ExporterFactory.register_exporter()
    class H5hspyExporter(H5Exporter):
        """ Exporter object for saving nodes as hspy files"""

        FORMAT_DESCRIPTION = "Hyperspy file format"
        FORMAT_EXTENSION = "hspy"

        def _export_data(self, node: Node, filename) -> None:
            """Exporting a .h5 node as a hyperspy object"""

            #first verify if the node type is compatible with export. Only data nodes are.
            nodetype = node.attrs['type']
            if nodetype == 'data':
                #If yes we can use this function (the same for plotting in h5browser) to extract information
                data, axes, nav_axes, is_spread = get_h5_data_from_node(node)
                data = data.reshape(data.shape, order='F')
                logger.debug(f"extracted data of shape {data.shape}")
                logger.debug(f"extracted axes: {axes}")

                #get_h5_data_from_node will return sometimes empty axes that we must yeet.
                axes_keys_to_remove = []
                for key,ax in axes.items():
                    if ax['data'] is None:
                        logger.warning(f'Dropping axis {key} due to empty data')
                        axes_keys_to_remove.append(key)
                for key in axes_keys_to_remove:
                    del axes[key]

            else:
                #Else just raise an error.
                raise NotImplementedError(f"hspy export not supported for nodes of type {nodetype}'. "
                                          f"Export from the data node instead.")

            #Verify that this is not an adaptive scan. If it is we throw and say it is not supported.
            if is_spread:
                raise NotImplementedError(f"hspy export not supported for adaptive scan data.")

            #Then we build the hyperspy axes objects.
            hyperspy_axes = []
            for key, ax in axes.items():
                logger.info(f"Extracting axis {ax['label']}.")
                unique_ax = self.extract_axis(ax)
                try:
                    indexv = data.shape.index(len(unique_ax))
                    logger.info(f"{ax['label']}, size {len(unique_ax)}, data index: {indexv}")
                except ValueError:
                    raise ValueError(f"Signal axis of length {len(unique_ax)} does not match any "
                                     f"dimension in data of shape {data.shape} ")
                is_nav = key.startswith('nav')
                hyperspy_axes.append(self.build_hyperspy_axis(unique_ax, data_idx=indexv, label=ax['label'],
                                                              unit=ax['units'], navigate=is_nav))

            ordered_axes = sorted(hyperspy_axes, key=lambda d: d['index_in_array'])
            for ax in ordered_axes:
                del ax['index_in_array']
            #Then we build the hyperspy object. First we must know its dimensionality
            #from the number of signal axes.
            dim = len(axes)-len(nav_axes)
            if dim == 1:
                # Then signal1D
                sig = hs.signals.Signal1D(data=data, original_metadata={}, axes=ordered_axes)
            elif dim == 2:
                # Then signal2D
                sig = hs.signals.Signal2D(data=data, original_metadata={}, axes=ordered_axes)
            else:
                # Then basesignal
                sig = hs.signals.BaseSignal(data=data, original_metadata={}, axes=ordered_axes)

            #Finally save
            sig.save(filename)


        def extract_axis(self, ax: Axis) -> np.ndarray:
            """Extract the unique values in a PyMoDAQ axis object in an order-preserving way"""
            axis_data = ax.data
            _, idx = np.unique(axis_data, return_index=True)

            unique_ax = axis_data[np.sort(idx)]

            return unique_ax

        def verify_axis_data_uniformity(self, axis_data: np.ndarray, tol: float = 1e-6) -> (float, float):
            """Try fitting the axis data with an affine function. Return offset,slope if the
             result is within tolerances, otherwise return None, None"""
            slope = None
            offset = None

            index = np.arange(len(axis_data))
            res, residuals, rank, singular_values, rcond = np.polyfit(x=index, y=axis_data, deg=1, full=True)  # noqa
            if residuals[0] < tol:
                slope = res[0]
                offset = res[1]

            return offset, slope

        def build_hyperspy_axis(self, ax_data: np.ndarray, data_idx: int,
                                label: str, unit: str, navigate: bool) -> Union[UniformDataAxis, DataAxis]:
            """Build an axis based on the input data. Choose between a UniformDataAxis or
            DataAxis object based on a quick linearity check of the input data."""
            offset, scale = self.verify_axis_data_uniformity(ax_data)
            if offset is not None:
                axis_dict = {'_type': 'UniformDataAxis',
                             'index_in_array': data_idx,
                             'name': label,
                             'units': unit,
                             'navigate': navigate,
                             'size': len(ax_data),
                             'scale': scale,
                             'offset': offset}
            else:
                axis_dict = {'_type': 'DataAxis',
                             'index_in_array': data_idx,
                             'name': label,
                             'units': unit,
                             'navigate': navigate,
                             'size': len(ax_data),
                             'axis': ax_data}

            return axis_dict

        def build_hyperspy_original_metadata(self, node: Node):
            """Build original metadata dictionary"""
            pass
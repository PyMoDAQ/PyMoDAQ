# -*- coding: utf-8 -*-
"""
Created the 02/03/2023

@author: Sebastien Weber
"""

import numpy as np


# project imports
from pymodaq_data.h5modules.backends import Node
from pymodaq_data.h5modules.exporter import ExporterFactory, H5Exporter
from pymodaq_data.h5modules.backends import H5Backend


@ExporterFactory.register_exporter()
class H5h5Exporter(H5Exporter):
    """ Exporter object for saving nodes as single h5 files"""

    FORMAT_DESCRIPTION = "Single node h5 file"
    FORMAT_EXTENSION = "h5"

    def export_data(self, node: Node, filename: str) -> None:
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

        new_file.h5file.move_node(new_file.get_node_path(node), newparent='/')
        new_file.h5file.remove_node('/RawData', recursive=True)
        new_file.flush()

        new_file.get_set_group('/', 'RawData')
        new_file.h5file.move_node(f'/{node.name}',
                                  newparent='/RawData')

        new_file.close_file()


@ExporterFactory.register_exporter()
class H5txtExporter(H5Exporter):
    """ Exporter object for saving nodes as txt files"""

    FORMAT_DESCRIPTION = "Text files"
    FORMAT_EXTENSION = "txt"

    def export_data(self, node: Node, filename: str) -> None:
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
class H5npyExporter(H5Exporter):
    """ Exporter object for saving nodes as npy files"""

    FORMAT_DESCRIPTION = "Binary NumPy format"
    FORMAT_EXTENSION = "npy"

    def export_data(self, node: Node, filename: str) -> None:
        """Export the node as a numpy binary file format"""
        # String __contain__ method will evaluate to True for CARRAY,EARRAY,VLARRAY,stringARRAY
        if 'ARRAY' in node.attrs['CLASS']:
            data = node.read()
            if not isinstance(data, np.ndarray):
                data = np.array(data)

            np.save(filename, data)
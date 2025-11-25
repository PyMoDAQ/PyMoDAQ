# -*- coding: utf-8 -*-
"""
Created the 02/03/2023

@author: Sebastien Weber
"""
import numpy as np


# project imports
from pymodaq_data.h5modules.backends import Node
from pymodaq_data.h5modules.exporter import ExporterFactory, H5Exporter


@ExporterFactory.register_exporter()
class H5asciiExporter(H5Exporter):
    """ Exporter object for saving nodes as txt files"""

    FORMAT_DESCRIPTION = "Ascii flimj file"
    FORMAT_EXTENSION = "ascii"

    def export_data(self, node: Node, filename: str) -> None:
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



# -*- coding: utf-8 -*-
"""
Created the 02/03/2023

@author: Nicolas Tappy
"""
# Standard imports

# 3rd party imports
try:
    import numpy as np
    import hyperspy.api_nogui as hs

    # project imports
    from pymodaq_data.h5modules.backends import Node
    from pymodaq_data.h5modules.utils import get_h5_data_from_node, extract_axis, verify_axis_data_uniformity
    from pymodaq_data.h5modules.exporter import ExporterFactory, H5Exporter
    from pymodaq_utils.logger import set_logger, get_module_name
    from pymodaq_data.h5modules.data_saving import DataLoader

    # This is needed to log
    logger = set_logger(get_module_name(__file__))


    @ExporterFactory.register_exporter()
    class H5hspyExporter(H5Exporter):
        """ Exporter object for saving nodes as hspy files"""

        FORMAT_DESCRIPTION = "Hyperspy file format"
        FORMAT_EXTENSION = "hspy"

        def export_data(self, node: Node, filename) -> None:
            """Exporting a .h5 node as a hyperspy object"""

            # first verify if the node type is compatible with export. Only data nodes are.
            ############## compatible with v4 done by Seb
            nodetype = node.attrs['data_type']
            if 'data' in nodetype.lower():
                # If yes we can use this function (the same for plotting in h5browser) to extract information

                data_loader = DataLoader(node.to_h5_backend())

                #use the method in data_saving below to load properly data from nodes. The data object is a DataWithAxes
                #of dimensionality DataND
                #you can get all axes (nav and signals) from data.axes
                #each axis as an index corresponding to the data shape
                # data.nav_index is a tuple containing the index of the nav axes

                data = data_loader.load_data(node, with_bkg=False)
                axes = data.axes #all axes
                nav_axes = data.get_nav_axes_with_data() #only navigation one

                #deprecated
                # data, axes, nav_axes, is_spread = get_h5_data_from_node(node)
                is_spread = node.attrs['distribution'] != 'uniform'
                
                data_array = data.data.reshape(data.shape, order='F')
                logger.debug(f"extracted data of shape {data.shape}")
                logger.debug(f"extracted axes: {axes}")
                #################################### TODO below to be done by Nicolas :-) and should be tested!!

                # get_h5_data_from_node will return sometimes empty axes that we must yeet.
                axes_keys_to_remove = []
                for key, ax in axes.items():
                    if ax['data'] is None:
                        logger.warning(f'Dropping axis {key} due to empty data')
                        axes_keys_to_remove.append(key)
                for key in axes_keys_to_remove:
                    del axes[key]

            else:
                # Else just raise an error.
                raise NotImplementedError(f"hspy export not supported for nodes of type {nodetype}'. "
                                          f"Export from the data node instead.")

            # Verify that this is not an adaptive scan. If it is we throw and say it is not supported.
            if is_spread:
                raise NotImplementedError(f"hspy export not supported for adaptive scan data.")

            # Then we build the hyperspy axes objects.
            hyperspy_axes = []
            for key, ax in axes.items():
                logger.info(f"Extracting axis {ax['label']}.")
                unique_ax = extract_axis(ax)
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
            # Then we build the hyperspy object. First we must know its dimensionality
            # from the number of signal axes.
            dim = len(axes) - len(nav_axes)
            if dim == 1:
                # Then signal1D
                sig = hs.signals.Signal1D(data=data, original_metadata={}, axes=ordered_axes)
            elif dim == 2:
                # Then signal2D
                sig = hs.signals.Signal2D(data=data, original_metadata={}, axes=ordered_axes)
            else:
                # Then basesignal
                sig = hs.signals.BaseSignal(data=data, original_metadata={}, axes=ordered_axes)

            # Finally save
            sig.save(filename)

        def build_hyperspy_axis(self, ax_data: np.ndarray, data_idx: int,
                                label: str, unit: str, navigate: bool) -> dict:
            """Build an axis based on the input data. Choose between a UniformDataAxis or
            DataAxis object based on a quick linearity check of the input data."""
            offset, scale = verify_axis_data_uniformity(ax_data)
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
except:
    pass

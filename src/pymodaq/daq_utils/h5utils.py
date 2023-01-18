# Standard imports
from collections import OrderedDict
from typing import List, Dict

# 3rd party imports
import numpy as np

# project imports
from pymodaq.daq_utils.h5backend import Node
from pymodaq.daq_utils.daq_utils import set_logger, get_module_name
from pymodaq.daq_utils.daq_utils import capitalize, Axis, NavAxis

logger = set_logger(get_module_name(__file__))


# Normally, this function does not rely on a H5Backend object so this is good
def find_scan_node(scan_node: Node):
    """
    utility function to find the parent node of "scan" type, meaning some of its children (DAQ_scan case)
    or co-nodes (daq_logger case) are navigation axes
    Parameters
    ----------
    scan_node: (pytables node)
        data node from where this function look for its navigation axes if any
    Returns
    -------
    node: the parent node of 'scan' type
    list: the data nodes of type 'navigation_axis' corresponding to the initial data node

    """
    try:
        while True:
            if scan_node.attrs['type'] == 'scan':
                break
            else:
                scan_node = scan_node.parent_node
        children = list(scan_node.children().values())  # for data saved using daq_scan
        # How is it any different from list(scan_node.parent_node.children().values()) ???
        children.extend([scan_node.parent_node.children()[child] for child in
                         scan_node.parent_node.children_name()])  # for data saved using the daq_logger
        nav_children = []
        for child in children:
            if 'type' in child.attrs.attrs_name:
                if child.attrs['type'] == 'navigation_axis':
                    nav_children.append(child)
        return scan_node, nav_children
    except Exception:
        return None, []


def get_h5_attributes(self, node_path):
    """

        """
    node = self.get_node(node_path)
    attrs_names = node.attrs.attrs_name
    attr_dict = OrderedDict([])
    for attr in attrs_names:
        # if attr!='settings':
        attr_dict[attr] = node.attrs[attr]

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


# This is a get_h5_data rewritten to remove dependency on a H5Backend object
def get_h5_data_from_node(node: Node) -> (np.ndarray, Dict[str, Axis], List[Axis], bool):
    """Check if there exist a data in the node, and if yes get the relevant axes.
    """

    is_spread = False
    # checks If the node contains an array. Effectively, if the node is a 'CARRAY', 'EARRAY' etc.
    # if that's not the case we return some empty data
    if 'ARRAY' not in node.attrs['CLASS']:
        logger.warning(f'node {node} does not host a dataset.')
        return np.array([]), [], [], is_spread

    # Otherwise Axis node is an ARRAY subclass which implements read() and has a GROUP parent node
    data = node.read()
    nav_axes = []
    axes = dict([])
    if isinstance(data, np.ndarray):
        data = np.squeeze(data)
        if 'Bkg' in node.parent_node.children_name() and node.name != 'Bkg':
            parent_group = node.parent_node  # This should be a group object if I get how this works
            # Then the parent node should have a children method which alllows to get the background.
            bkg_node = parent_group.children()['Bkg']
            bkg = np.squeeze(bkg_node.read())
            # bkg = np.squeeze(self.get_node(node.parent_node.path, 'Bkg').read())
            try:
                data = data - bkg
            except ValueError:
                logger.warning(f'Could not substract bkg from data node {node} as their shape are '
                               f'incoherent {bkg.shape} and {data.shape}')
        if 'type' in node.attrs.attrs_name:
            if 'data' in node.attrs['type'] or 'channel' in node.attrs['type'].lower():
                # parent_path = node.parent_node.path
                children_names = node.parent_node.children_name()

                if 'data_dimension' not in node.attrs.attrs_name:  # for backcompatibility
                    data_dim = node.attrs['data_type']
                else:
                    data_dim = node.attrs['data_dimension']
                if 'scan_subtype' in node.attrs.attrs_name:
                    if node.attrs['scan_subtype'].lower() == 'adaptive':
                        is_spread = True
                tmp_axes = ['x_axis', 'y_axis']
                for ax in tmp_axes:
                    if capitalize(ax) in children_names:
                        # Following the same logic as before we should be able to apply this
                        axis_node = node.parent_node.children()[capitalize(ax)]
                        # axis_node = self.get_node(parent_path + '/{:s}'.format(capitalize(ax)))
                        axes[ax] = Axis(data=axis_node.read())
                        if 'units' in axis_node.attrs.attrs_name:
                            axes[ax]['units'] = axis_node.attrs['units']
                        if 'label' in axis_node.attrs.attrs_name:
                            axes[ax]['label'] = axis_node.attrs['label']
                    else:
                        axes[ax] = Axis()

                if data_dim == 'ND':  # check for navigation axis
                    tmp_nav_axes = ['y_axis', 'x_axis', ]
                    nav_axes = []
                    for ind_ax, ax in enumerate(tmp_nav_axes):
                        if 'Nav_{:s}'.format(ax) in children_names:
                            nav_axes.append(ind_ax)
                            axis_node = node.parent_node.children()[f"Nav_{ax}"]
                            # axis_node = self.get_node(parent_path + '/Nav_{:s}'.format(ax))
                            if is_spread:
                                axes['nav_{:s}'.format(ax)] = Axis(data=axis_node.read())
                            else:
                                axes['nav_{:s}'.format(ax)] = Axis(data=np.unique(axis_node.read()))
                                if axes['nav_{:s}'.format(ax)]['data'].shape[0] != data.shape[ind_ax]:
                                    # could happen in case of linear back to start type of scan
                                    tmp_ax = []
                                    for ix in axes['nav_{:s}'.format(ax)]['data']:
                                        tmp_ax.extend([ix, ix])
                                        axes['nav_{:s}'.format(ax)] = Axis(data=np.array(tmp_ax))

                            if 'units' in axis_node.attrs.attrs_name:
                                axes['nav_{:s}'.format(ax)]['units'] = axis_node.attrs['units']
                            if 'label' in axis_node.attrs.attrs_name:
                                axes['nav_{:s}'.format(ax)]['label'] = axis_node.attrs['label']

                if 'scan_type' in node.attrs.attrs_name:
                    scan_type = node.attrs['scan_type'].lower()
                    # if scan_type == 'scan1d' or scan_type == 'scan2d':
                    scan_node, nav_children = find_scan_node(node)
                    nav_axes = []
                    if scan_type == 'tabular' or is_spread:
                        datas = []
                        labels = []
                        all_units = []
                        npts = 2  # Just in case nav_children is empty
                        for axis_node in nav_children:
                            npts = axis_node.attrs['shape'][0]
                            datas.append(axis_node.read())
                            labels.append(axis_node.attrs['label'])
                            all_units.append(axis_node.attrs['units'])

                        nav_axes.append(0)
                        axes['nav_x_axis'] = NavAxis(
                            data=np.linspace(0, npts - 1, npts),
                            nav_index=nav_axes[-1], units='', label='Scan index', labels=labels,
                            datas=datas, all_units=all_units)
                    else:
                        for axis_node in nav_children:
                            nav_axes.append(axis_node.attrs['nav_index'])
                            if is_spread:
                                axes[f'nav_{nav_axes[-1]:02d}'] = NavAxis(data=axis_node.read(),
                                                                          nav_index=nav_axes[-1])
                            else:
                                axes[f'nav_{nav_axes[-1]:02d}'] = NavAxis(data=np.unique(axis_node.read()),
                                                                          nav_index=nav_axes[-1])
                                if nav_axes[-1] < len(data.shape):
                                    if axes[f'nav_{nav_axes[-1]:02d}']['data'].shape[0] != data.shape[nav_axes[-1]]:
                                        # could happen in case of linear back to start type of scan
                                        tmp_ax = []
                                        for ix in axes[f'nav_{nav_axes[-1]:02d}']['data']:
                                            tmp_ax.extend([ix, ix])
                                            axes[f'nav_{nav_axes[-1]:02d}'] = NavAxis(data=np.array(tmp_ax),
                                                                                      nav_index=nav_axes[-1])

                            if 'units' in axis_node.attrs.attrs_name:
                                axes[f'nav_{nav_axes[-1]:02d}']['units'] = axis_node.attrs[
                                    'units']
                            if 'label' in axis_node.attrs.attrs_name:
                                axes[f'nav_{nav_axes[-1]:02d}']['label'] = axis_node.attrs[
                                    'label']
            elif 'axis' in node.attrs['type']:
                axis_node = node
                axes['y_axis'] = Axis(data=axis_node.read())  # Axis node should be CARRAY which implements read()
                if 'units' in axis_node.attrs.attrs_name:
                    axes['y_axis']['units'] = axis_node.attrs['units']
                if 'label' in axis_node.attrs.attrs_name:
                    axes['y_axis']['label'] = axis_node.attrs['label']
                axes['x_axis'] = Axis(
                    data=np.linspace(0, axis_node.attrs['shape'][0] - 1, axis_node.attrs['shape'][0]),
                    units='pxls',
                    label='')
        return data, axes, nav_axes, is_spread

    elif isinstance(data, list):
        data = np.array(data)
        return data, dict([]), [], is_spread

def extract_axis(ax: Axis) -> np.ndarray:
    """Extract the unique values in a PyMoDAQ axis object in an order-preserving way"""
    axis_data = ax.data
    _, idx = np.unique(axis_data, return_index=True)

    unique_ax = axis_data[np.sort(idx)]

    return unique_ax

def verify_axis_data_uniformity(axis_data: np.ndarray, tol: float = 1e-6) -> (float, float):
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
# -*- coding: utf-8 -*-
"""
Created the 19/01/2023

@author: Sebastien Weber
"""


def find_scan_node(scan_node):
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

# -*- coding: utf-8 -*-
"""
Created the 15/11/2022

@author: Sebastien Weber
"""
import os
from collections import OrderedDict
import warnings
from copy import deepcopy
import logging
import webbrowser
import numpy as np
from pathlib import Path
from packaging import version as version_mod

from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.config import Config
from qtpy import QtGui, QtCore
from qtpy.QtCore import Qt, QObject, Signal, QByteArray

import pymodaq.utils.parameter.ioxml
from pymodaq.utils.parameter import Parameter, ParameterTree

from pymodaq.utils.tree_layout.tree_layout_main import Tree_layout
from pymodaq.utils.daq_utils import capitalize
from pymodaq.utils.data import Axis, DataRaw
from pymodaq.utils.gui_utils.utils import h5tree_to_QTree, pngbinary2Qlabel
from pymodaq.utils.gui_utils.file_io import select_file
from pymodaq.utils.plotting.data_viewers.viewerND import ViewerND
from qtpy import QtWidgets
from pymodaq.utils import daq_utils as utils

from .backends import H5Backend

config = Config()
logger = set_logger(get_module_name(__file__))


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


class H5BrowserUtil(H5Backend):
    """Utility object to interact and get info and data from a hdf5 file

    Inherits H5Backend and all its functionalities

    Parameters
    ----------
    backend: str
        The used hdf5 backend: either tables, h5py or h5pyd
    """
    def __init__(self, backend='tables'):
        super().__init__(backend=backend)

    def export_data(self, node_path='/', filesavename='datafile.h5'):
        """Export data in nodes in another file format

        Parameters
        ----------
        node_path: str
            the path in the file
        filesavename:
            the exported file name with a particular extension
            Accepted extensions are:
            * txt: to save node content in a tab delimited text file
            * ascii: to save node content in a tab delimited ascii file
            * h5
        """
        if filesavename != '':
            file = Path(filesavename)
            node = self.get_node(node_path)
            if file.suffix == '.txt' or file.suffix == '.ascii':
                if 'ARRAY' in node.attrs['CLASS']:
                    data = node.read()
                    if not isinstance(data, np.ndarray):
                        # in case one has a list of same objects (array of strings for instance, logger or other)
                        data = np.array(data)
                        np.savetxt(filesavename,
                                   data if file.suffix == '.txt' else data.T if len(data.shape) > 1 else [data],
                                   '%s', '\t')
                    else:
                        np.savetxt(filesavename,
                                   data if file.suffix == '.txt' else data.T if len(data.shape) > 1 else [data],
                                   '%.6e', '\t')

                elif 'Group' in node.attrs['CLASS']:
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
                    np.savetxt(filesavename, data_trans, fmts, '\t', header='#' + '\t'.join(header))
            elif file.suffix == '.h5':
                self.save_file_as(str(file))
                copied_file = H5Backend()
                copied_file.open_file(str(file), 'a')

                copied_file.h5file.move_node(self.get_node_path(node), newparent=copied_file.h5file.get_node('/'))
                copied_file.h5file.remove_node('/Raw_datas', recursive=True)
                copied_file.close_file()

    def get_h5file_scans(self, where='/'):
        """Get the list of the scan nodes in the file

        Parameters
        ----------
        where: str
            the path in the file

        Returns
        -------
        list of dict
            dict with keys: scan_name, path (within the file) and data (the live scan png image)
        """
        # TODO add a test for this method
        scan_list = []
        where = self.get_node(where)
        for node in self.walk_nodes(where):
            if 'pixmap2D' in node.attrs.attrs_name:
                scan_list.append(
                    dict(scan_name='{:s}_{:s}'.format(node.parent_node.name, node.name), path=node.path,
                         data=node.attrs['pixmap2D']))

        return scan_list

    def get_h5_attributes(self, node_path):
        """Get the list of attributes (metadata) of a given node

        Parameters
        ----------
        node_path: str
            the path in the file

        Returns
        -------
        attr_dict: OrderedDict
            attributes as a dict
        settings: str
            settings attribute
        scan_settings: str
            scan settings attribute
        pixmaps: list of pixmap
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

    def get_h5_data(self, node_path):
        """

        Parameters
        ----------
        node_path: str
            the path in the file

        Returns
        -------
        data: ndarray
        axes: dict of Axis
            all the axis referring to the data: signal axes and navigation axes
        nav_axes: list of int
            index of the navigation axes
        is_spread: bool
            if True data is not in a regular grid (linear, 2D or ND) but given as a table with coordinates and value

        """
        node = self.get_node(node_path)
        is_spread = False
        if 'ARRAY' in node.attrs['CLASS']:
            data = node.read()
            nav_axes = []
            axes = dict([])
            if isinstance(data, np.ndarray):
                data = np.squeeze(data)
                if 'Bkg' in node.parent_node.children_name() and node.name != 'Bkg':
                    bkg = np.squeeze(self.get_node(node.parent_node.path, 'Bkg').read())
                    try:
                        data = data - bkg
                    except:
                        logger.warning(f'Could not substract bkg from data node {node_path} as their shape are '
                                       f'incoherent {bkg.shape} and {data.shape}')
                if 'type' in node.attrs.attrs_name:
                    if 'data' in node.attrs['type'] or 'channel' in node.attrs['type'].lower():
                        parent_path = node.parent_node.path
                        children = node.parent_node.children_name()

                        if 'data_dimension' not in node.attrs.attrs_name:  # for backcompatibility
                            data_dim = node.attrs['data_type']
                        else:
                            data_dim = node.attrs['data_dimension']
                        if 'scan_subtype' in node.attrs.attrs_name:
                            if node.attrs['scan_subtype'].lower() == 'adaptive':
                                is_spread = True
                        tmp_axes = ['x_axis', 'y_axis']
                        for ind, ax in enumerate(tmp_axes):
                            if capitalize(ax) in children:
                                axis_node = self.get_node(parent_path + '/{:s}'.format(capitalize(ax)))
                                axes[ax] = Axis(data=axis_node.read(), index=len(data.shape)-ind-1)
                                if 'units' in axis_node.attrs.attrs_name:
                                    axes[ax].units = axis_node.attrs['units']
                                if 'label' in axis_node.attrs.attrs_name:
                                    axes[ax].label = axis_node.attrs['label']
                            # else:
                            #     axes[ax] = Axis()

                        if data_dim == 'ND':  # check for navigation axis
                            tmp_nav_axes = ['y_axis', 'x_axis', ]
                            nav_axes = []
                            for ind_ax, ax in enumerate(tmp_nav_axes):
                                if 'Nav_{:s}'.format(ax) in children:
                                    nav_axes.append(ind_ax)
                                    axis_node = self.get_node(parent_path + '/Nav_{:s}'.format(ax))
                                    if is_spread:
                                        axes['nav_{:s}'.format(ax)] = Axis(data=axis_node.read())
                                    else:
                                        axes['nav_{:s}'.format(ax)] = Axis(data=np.unique(axis_node.read()))
                                        if axes['nav_{:s}'.format(ax)].data.shape[0] != data.shape[ind_ax]:
                                            # could happen in case of linear back to start type of scan
                                            tmp_ax = []
                                            for ix in axes['nav_{:s}'.format(ax)].data:
                                                tmp_ax.extend([ix, ix])
                                                axes['nav_{:s}'.format(ax)] = Axis(data=np.array(tmp_ax))

                                    if 'units' in axis_node.attrs.attrs_name:
                                        axes['nav_{:s}'.format(ax)].units = axis_node.attrs['units']
                                    if 'label' in axis_node.attrs.attrs_name:
                                        axes['nav_{:s}'.format(ax)].label = axis_node.attrs['label']

                        if 'scan_type' in node.attrs.attrs_name:
                            scan_type = node.attrs['scan_type'].lower()
                            # if scan_type == 'scan1d' or scan_type == 'scan2d':
                            scan_node, nav_children = find_scan_node(node)
                            nav_axes = []
                            if scan_type == 'tabular' or is_spread:
                                datas = []
                                labels = []
                                all_units = []
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
                                        axes[f'nav_{nav_axes[-1]:02d}'] = Axis(data=axis_node.read(),
                                                                               index=nav_axes[-1])
                                    else:
                                        axes[f'nav_{nav_axes[-1]:02d}'] = Axis(data=np.unique(axis_node.read()),
                                                                               index=nav_axes[-1])
                                        if nav_axes[-1] < len(data.shape):
                                            if axes[f'nav_{nav_axes[-1]:02d}'].data.shape[0] != data.shape[nav_axes[-1]]:
                                                # could happen in case of linear back to start type of scan
                                                tmp_ax = []
                                                for ix in axes[f'nav_{nav_axes[-1]:02d}'].data:
                                                    tmp_ax.extend([ix, ix])
                                                    axes[f'nav_{nav_axes[-1]:02d}'] = Axis(data=np.array(tmp_ax),
                                                                                           index=nav_axes[-1])

                                    if 'units' in axis_node.attrs.attrs_name:
                                        axes[f'nav_{nav_axes[-1]:02d}'].units = axis_node.attrs[
                                            'units']
                                    if 'label' in axis_node.attrs.attrs_name:
                                        axes[f'nav_{nav_axes[-1]:02d}'].label = axis_node.attrs[
                                            'label']
                    elif 'axis' in node.attrs['type']:
                        axis_node = node
                        axes['y_axis'] = Axis(data=axis_node.read(), index=0)
                        if 'units' in axis_node.attrs.attrs_name:
                            axes['y_axis'].units = axis_node.attrs['units']
                        if 'label' in axis_node.attrs.attrs_name:
                            axes['y_axis'].label = axis_node.attrs['label']
                        # axes['x_axis'] = Axis(data=np.linspace(0, axis_node.attrs['shape'][0] - 1, axis_node.attrs['shape'][0]),
                        #                       units='pxls', label='', index=1)
                return data, axes, nav_axes, is_spread

            elif isinstance(data, list):
                return data, [], [], is_spread


class H5Browser(QObject):
    """UI used to explore h5 files, plot and export subdatas

    Parameters
    ----------
    parent: QtWidgets container
        either a QWidget or a QMainWindow
    h5file: h5file instance
        exact type depends on the backend
    h5file_path: str or Path
        if specified load the corresponding file, otherwise open a select file dialog
    backend: str
        either 'tables, 'h5py' or 'h5pyd'

    See Also
    --------
    H5Backend, H5Backend
    """
    data_node_signal = Signal(
        str)  # the path of a node where data should be monitored, displayed...whatever use from the caller
    status_signal = Signal(str)

    def __init__(self, parent, h5file=None, h5file_path=None, backend='tables'):
        super().__init__()
        if not (isinstance(parent, QtWidgets.QWidget) or isinstance(parent, QtWidgets.QMainWindow)):
            raise Exception('no valid parent container, expected a QWidget or a QMainWindow')

        if isinstance(parent, QtWidgets.QMainWindow):
            self.main_window = parent
            self.parent = QtWidgets.QWidget()
            self.main_window.setCentralWidget(self.parent)
        else:
            self.main_window = None
            self.parent = parent

        self.backend = backend
        self.current_node_path = None

        # construct the UI interface
        self.ui = QObject()  # the user interface
        self.set_GUI()

        # construct the h5 interface and load the file (or open a select file message)
        self.h5utils = H5BrowserUtil(backend=self.backend)
        if h5file is None:
            if h5file_path is None:
                h5file_path = select_file(save=False, ext=['h5', 'hdf5'])
            if h5file_path != '':
                self.h5utils.open_file(h5file_path, 'r')
            else:
                return
        else:
            self.h5utils.h5file = h5file

        self.check_version()
        self.populate_tree()
        self.ui.h5file_tree.ui.Open_Tree.click()

    def check_version(self):
        """Check version of PyMoDAQ to assert if file is compatible or not with the current version of the Browser"""
        if 'pymodaq_version' in self.h5utils.root().attrs.attrs_name:
            if version_mod.parse(self.h5utils.root().attrs['pymodaq_version']) < version_mod.parse('2.0'):
                msgBox = QtWidgets.QMessageBox(parent=None)
                msgBox.setWindowTitle("Invalid version")
                msgBox.setText(f"Your file has been saved using PyMoDAQ "
                               f"version {self.h5utils.root().attrs['pymodaq_version']} "
                               f"while you're using version: {utils.get_version()}\n"
                               f"Please create and use an adapted environment to use this version (up to 1.6.4):\n"
                               f"pip install pymodaq==1.6.4")
                ret = msgBox.exec()
                self.quit_fun()
                if self.main_window is not None:
                    self.main_window.close()
                else:
                    self.parent.close()

    def add_comments(self, status: bool, comment=''):
        """Add comments to a node

        Parameters
        ----------
        status: bool
        comment: str
            The comment to be added in a comment attribute to the current node path

        See Also
        --------
        current_node_path
        """
        try:
            self.current_node_path = self.get_tree_node_path()
            node = self.h5utils.get_node(self.current_node_path)
            if 'comments' in node.attrs.attrs_name:
                tmp = node.attrs['comments']
            else:
                tmp = ''
            if comment == '':
                text, res = QtWidgets.QInputDialog.getMultiLineText(None, 'Enter comments', 'Enter comments here:', tmp)
                if res and text != '':
                    comment = text
                node.attrs['comments'] = comment
            else:
                node.attrs['comments'] = tmp + comment

            self.h5utils.flush()

        except Exception as e:
            logger.exception(str(e))

    def get_tree_node_path(self):
        """Get the node path of the currently selected node in the UI"""
        return self.ui.h5file_tree.ui.Tree.currentItem().text(2)

    def export_data(self):
        """Opens a dialog to export data

        See Also
        --------
        H5BrowserUtil.export_data
        """
        try:
            file_filter = "Single node h5 file (*.h5);;Text files (*.txt);;Ascii file (*.ascii)"
            file = select_file(save=True, filter=file_filter)
            self.current_node_path = self.get_tree_node_path()
            if file != '':
                self.h5utils.export_data(self.current_node_path, str(file))

        except Exception as e:
            logger.exception(str(e))

    def save_file(self, filename=None):

        if filename is None:
            filename = select_file(save=True, ext='txt')
        if filename != '':
            self.h5utils.save_file(filename)

    def quit_fun(self):
        """
        """
        try:
            self.h5utils.close_file()
            if self.main_window is None:
                self.parent.close()
            else:
                self.main_window.close()
        except Exception as e:
            logger.exception(str(e))

    def create_menu(self):
        self.menubar = self.main_window.menuBar()

        # %% create Settings menu
        self.file_menu = self.menubar.addMenu('File')
        load_action = self.file_menu.addAction('Load file')
        load_action.triggered.connect(lambda: self.load_file(None))
        save_action = self.file_menu.addAction('Save file')
        save_action.triggered.connect(self.save_file)
        self.file_menu.addSeparator()
        quit_action = self.file_menu.addAction('Quit')
        quit_action.triggered.connect(self.quit_fun)

        # help menu
        help_menu = self.menubar.addMenu('?')
        action_about = help_menu.addAction('About')
        action_about.triggered.connect(self.show_about)
        action_help = help_menu.addAction('Help')
        action_help.triggered.connect(self.show_help)
        action_help.setShortcut(QtCore.Qt.Key_F1)
        log_action = help_menu.addAction('Show log')
        log_action.triggered.connect(self.show_log)

    def show_about(self):
        splash_path = os.path.join(os.path.split(os.path.split(__file__)[0])[0], 'splash.png')
        splash = QtGui.QPixmap(splash_path)
        self.splash_sc = QtWidgets.QSplashScreen(splash, QtCore.Qt.WindowStaysOnTopHint)
        self.splash_sc.setVisible(True)
        self.splash_sc.showMessage(f"PyMoDAQ version {utils.get_version()}\n"
                                   f"Modular Acquisition with Python\nWritten by Sébastien Weber",
                                   QtCore.Qt.AlignRight, QtCore.Qt.white)

    def show_log(self):
        webbrowser.open(logging.getLogger('pymodaq').handlers[0].baseFilename)

    def show_help(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl("http://pymodaq.cnrs.fr"))

    def set_GUI(self):

        if self.main_window is not None:
            self.create_menu()

        layout = QtWidgets.QGridLayout()

        V_splitter = QtWidgets.QSplitter(Qt.Vertical)
        V_splitter2 = QtWidgets.QSplitter(Qt.Vertical)
        H_splitter = QtWidgets.QSplitter(Qt.Horizontal)

        Form = QtWidgets.QWidget()
        # self.ui.h5file_tree = Tree_layout(Form,col_counts=2,labels=["Node",'Pixmap'])
        self.ui.h5file_tree = Tree_layout(Form, col_counts=1, labels=["Node"])
        self.ui.h5file_tree.ui.Tree.setMinimumWidth(300)
        self.ui.h5file_tree.ui.Tree.itemClicked.connect(self.show_h5_attributes)
        self.ui.h5file_tree.ui.Tree.itemDoubleClicked.connect(self.show_h5_data)

        self.export_action = QtWidgets.QAction("Export data", None)
        self.export_action.triggered.connect(self.export_data)

        self.add_comments_action = QtWidgets.QAction("Add comments to this node", None)
        self.add_comments_action.triggered.connect(self.add_comments)
        self.ui.h5file_tree.ui.Tree.addAction(self.export_action)
        self.ui.h5file_tree.ui.Tree.addAction(self.add_comments_action)

        V_splitter.addWidget(Form)
        self.ui.attributes_tree = ParameterTree()
        self.ui.attributes_tree.setMinimumWidth(300)
        V_splitter.addWidget(self.ui.attributes_tree)

        self.settings_raw = Parameter.create(name='Param_raw', type='group')
        self.ui.attributes_tree.setParameters(self.settings_raw, showTop=False)

        H_splitter.addWidget(V_splitter)
        self.pixmap_widget = QtWidgets.QWidget()
        self.pixmap_widget.setMaximumHeight(100)
        V_splitter2.addWidget(self.pixmap_widget)
        self.ui.settings_tree = ParameterTree()
        self.ui.settings_tree.setMinimumWidth(300)
        V_splitter2.addWidget(self.ui.settings_tree)
        self.ui.text_list = QtWidgets.QListWidget()

        V_splitter2.addWidget(self.ui.text_list)

        H_splitter.addWidget(V_splitter2)

        widget_viewer = QtWidgets.QWidget()
        self.hyperviewer = ViewerND(widget_viewer)
        H_splitter.addWidget(widget_viewer)

        layout.addWidget(H_splitter)
        self.parent.setLayout(layout)

        self.settings = Parameter.create(name='Param', type='group')
        self.ui.settings_tree.setParameters(self.settings, showTop=False)

        self.status_signal.connect(self.add_log)

    def add_log(self, txt):
        logger.info(txt)

    def show_h5_attributes(self, item):
        try:
            self.current_node_path = self.get_tree_node_path()

            attr_dict, settings, scan_settings, pixmaps = self.h5utils.get_h5_attributes(self.current_node_path)

            for child in self.settings_raw.children():
                child.remove()
            params = []
            for attr in attr_dict:
                params.append({'title': attr, 'name': attr, 'type': 'str', 'value': attr_dict[attr], 'readonly': True})
            self.settings_raw.addChildren(params)

            if settings is not None:
                for child in self.settings.children():
                    child.remove()
                QtWidgets.QApplication.processEvents()  # so that the tree associated with settings updates
                params = pymodaq.utils.parameter.ioxml.XML_string_to_parameter(settings)
                self.settings.addChildren(params)

            if scan_settings is not None:
                params = pymodaq.utils.parameter.ioxml.XML_string_to_parameter(scan_settings)
                self.settings.addChildren(params)

            if pixmaps == []:
                self.pixmap_widget.setVisible(False)
            else:
                self.pixmap_widget.setVisible(True)
                self.show_pixmaps(pixmaps)

        except Exception as e:
            logger.exception(str(e))

    def show_pixmaps(self, pixmaps=[]):
        if self.pixmap_widget.layout() is None:
            layout = QtWidgets.QHBoxLayout()
            self.pixmap_widget.setLayout(layout)
        while 1:
            child = self.pixmap_widget.layout().takeAt(0)
            if not child:
                break
            child.widget().deleteLater()
            QtWidgets.QApplication.processEvents()
        labs = []
        for pix in pixmaps:
            labs.append(pngbinary2Qlabel(pix))
            self.pixmap_widget.layout().addWidget(labs[-1])

    def show_h5_data(self, item):
        """
        """
        try:
            self.current_node_path = item.text(2)
            self.show_h5_attributes(item)
            node = self.h5utils.get_node(self.current_node_path)
            self.data_node_signal.emit(self.current_node_path)
            if 'ARRAY' in node.attrs['CLASS']:
                data, axes, nav_axes, is_spread = self.h5utils.get_h5_data(self.current_node_path)

                data_to_plot = DataRaw('mydata', data=data, axes=list(axes.values()), nav_indexes=nav_axes)

                if isinstance(data, np.ndarray):
                    if 'scan_type' in node.attrs.attrs_name:
                        scan_type = node.attrs['scan_type']
                    else:
                        scan_type = ''
                    # self.hyperviewer.show_data(deepcopy(data), nav_axes=nav_axes, is_spread=is_spread,
                    #                            scan_type=scan_type, **deepcopy(axes))
                    # self.hyperviewer.init_ROI()
                    self.hyperviewer.show_data(data_to_plot)
                elif isinstance(data, list):
                    if not (not data):
                        if isinstance(data[0], str):
                            self.ui.text_list.clear()
                            for txt in data:
                                self.ui.text_list.addItem(txt)
        except Exception as e:
            logger.exception(str(e))

    def populate_tree(self):
        """
            | Init the ui-tree and store data into calling the h5_tree_to_Qtree convertor method

            See Also
            --------
            h5tree_to_QTree, update_status
        """
        try:
            if self.h5utils.h5file is not None:
                self.ui.h5file_tree.ui.Tree.clear()
                base_node = self.h5utils.root()
                base_tree_item, pixmap_items = h5tree_to_QTree(base_node)
                self.ui.h5file_tree.ui.Tree.addTopLevelItem(base_tree_item)
                self.add_widget_totree(pixmap_items)

        except Exception as e:
            logger.exception(str(e))

    def add_widget_totree(self, pixmap_items):

        for item in pixmap_items:
            widget = QtWidgets.QWidget()

            vLayout = QtWidgets.QVBoxLayout()
            label1D = QtWidgets.QLabel()
            bytes = QByteArray(item['node'].attrs['pixmap1D'])
            im1 = QtGui.QImage.fromData(bytes)
            a = QtGui.QPixmap.fromImage(im1)
            label1D.setPixmap(a)

            label2D = QtWidgets.QLabel()
            bytes = QByteArray(item['node'].attrs['pixmap2D'])
            im2 = QtGui.QImage.fromData(bytes)
            b = QtGui.QPixmap.fromImage(im2)
            label2D.setPixmap(b)

            vLayout.addWidget(label1D)
            vLayout.addwidget(label2D)
            widget.setLayout(vLayout)
            self.ui.h5file_tree.ui.Tree.setItemWidget(item['item'], 1, widget)


def browse_data(fname=None, ret_all=False, message=None):
    """Browse data present in any h5 file using the H5Browser within a dialog window
    when the user has selected a given node, return its content

    Parameters
    ----------
    fname: str
    ret_all: bool
    message: str

    Returns
    -------
    data: the numpy array in the selected node
    if argument ret_all is True, returns also:
    fname: the file name
    node_path: hte path of the selected node within the H5 file tree

    """
    if fname is None:
        fname = str(select_file(start_path=config('data_saving', 'h5file', 'save_path'), save=False, ext='h5'))

    if type(fname) != str:
        try:
            fname = str(fname)
        except Exception:
            raise Exception('filename in browse data is not valid')
    if fname != '':
        (root, ext) = os.path.splitext(fname)
        if not ('h5' in ext or 'hdf5' in ext):
            warnings.warn('This is not a PyMODAQ h5 file, there could be issues', Warning)

        form = QtWidgets.QWidget()
        browser = H5Browser(form, h5file_path=fname)

        dialog = QtWidgets.QDialog()
        vlayout = QtWidgets.QVBoxLayout()

        vlayout.addWidget(form)
        dialog.setLayout(vlayout)
        buttonBox = QtWidgets.QDialogButtonBox(parent=dialog)

        buttonBox.addButton('OK', buttonBox.AcceptRole)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.addButton('Cancel', buttonBox.RejectRole)
        buttonBox.rejected.connect(dialog.reject)
        vlayout.addWidget(buttonBox)

        dialog.setWindowTitle('Select a data node in the tree')
        if message is None or not isinstance(message, str):
            dialog.setWindowTitle('Select a data node in the tree')
        else:
            dialog.setWindowTitle(message)
        res = dialog.exec()

        if res == dialog.Accepted:
            node_path = browser.current_node_path
            data = browser.h5utils.get_node(node_path).read()
        else:
            data = None
            node_path = None

        browser.h5utils.close_file()

        if ret_all:
            return data, fname, node_path
        else:
            return data
    return None, '', ''



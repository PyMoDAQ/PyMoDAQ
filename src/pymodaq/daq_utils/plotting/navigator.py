from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import Qt, QObject, pyqtSlot, pyqtSignal

import sys
import os
import numpy as np
import tables

from pyqtgraph.parametertree import Parameter, ParameterTree
from pymodaq.daq_utils.parameter import pymodaq_ptypes
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_basic import Viewer2DBasic
from pymodaq.daq_utils.plotting.graph_items import ImageItem, TriangulationItem
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils.h5modules import H5Saver, browse_data, H5BrowserUtil
from pymodaq.daq_utils import gui_utils as gutils

from pymodaq.daq_utils.daq_utils import get_set_local_dir

local_path = get_set_local_dir()
navigator_path = os.path.join(local_path, 'navigator_temp_files')
if not os.path.isdir(navigator_path):
    os.makedirs(navigator_path)

logger = utils.set_logger(utils.get_module_name(__file__))

Ntick = 128
colors_red = np.array([(int(r), 0, 0) for r in np.linspace(0, 255, Ntick)])
colors_green = np.array([(0, int(g), 0) for g in np.linspace(0, 255, Ntick)])
colors_blue = np.array([(0, 0, int(b)) for b in np.linspace(0, 255, Ntick)])
config = utils.load_config()


class Navigator(QObject):
    log_signal = pyqtSignal(str)
    sig_double_clicked = pyqtSignal(float, float)

    def __init__(self, parent=None, h5file_path=None):
        super().__init__(parent)

        if parent is None:
            parent = QtWidgets.QWidget()
        self.parent = parent
        self.title = 'Navigator'
        self.status_time = 1000
        self.x_range = []
        self.y_range = []
        self.filters = tables.Filters(complevel=5)
        self.next_scan_index = 0
        self.viewer = None
        self.overlays = []  # %list of imageItem items displaying 2D scans info
        self.h5module_path = h5file_path
        self.h5module = H5BrowserUtil()

        if h5file_path is not None:
            self.h5module.open_file(h5file_path, 'a')
            self.settings.child('settings', 'filepath').setValue(h5file_path)
            self.settings.child('settings', 'Load h5').hide()
            self.show_overlay()

        self.setupUI()

    def create_toolbar(self):
        iconload = QtGui.QIcon()
        iconload.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/NewLayer.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.loadaction = QtWidgets.QAction(iconload, "Load scan file (.h5)", None)
        self.toolbar.addAction(self.loadaction)
        self.loadaction.triggered.connect(self.load_data)

        iconloadim = QtGui.QIcon()
        iconloadim.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/Open_File_32.png"), QtGui.QIcon.Normal,
                             QtGui.QIcon.Off)
        self.loadactionim = QtWidgets.QAction(iconloadim, "Load image file (.h5)", None)
        self.toolbar.addAction(self.loadactionim)
        self.loadactionim.triggered.connect(self.load_image)

        icon_ratio = QtGui.QIcon()
        icon_ratio.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/Zoom_1_1.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.action_ratio = QtWidgets.QAction(icon_ratio, "Set viewbox aspect ratio to 1", None)
        self.action_ratio.setCheckable(True)
        self.toolbar.addAction(self.action_ratio)
        self.action_ratio.triggered.connect(self.set_aspect_ratio)

        icon_moveat = QtGui.QIcon()
        icon_moveat.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/move_contour.png"), QtGui.QIcon.Normal,
                              QtGui.QIcon.Off)
        self.moveat_action = QtWidgets.QAction(icon_moveat,
                                               "When selected, double clicking on viewbox will move DAQ_Move modules",
                                               None)
        self.moveat_action.setCheckable(True)
        self.toolbar.addAction(self.moveat_action)

        icon_sel_all = QtGui.QIcon()
        icon_sel_all.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/select_all2.png"), QtGui.QIcon.Normal,
                               QtGui.QIcon.Off)
        self.sel_all_action = QtWidgets.QAction(icon_sel_all, "Select (show) all 2D scans on the viewer", None)
        self.toolbar.addAction(self.sel_all_action)
        self.sel_all_action.triggered.connect(self.show_all)

        icon_sel_none = QtGui.QIcon()
        icon_sel_none.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/select_none.png"), QtGui.QIcon.Normal,
                                QtGui.QIcon.Off)
        self.sel_none_action = QtWidgets.QAction(icon_sel_none, "Unselect (hide) all 2D scans on the viewer", None)
        self.toolbar.addAction(self.sel_none_action)
        self.sel_none_action.triggered.connect(self.show_none)

        icon_histo = QtGui.QIcon()
        icon_histo.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/Histogram.png"), QtGui.QIcon.Normal,
                             QtGui.QIcon.Off)
        self.histo_action = QtWidgets.QAction(icon_histo, "Show (hide) histograms", None)
        self.toolbar.addAction(self.histo_action)
        self.histo_action.setCheckable(True)
        self.histo_action.triggered.connect(self.show_histo)

    @pyqtSlot(float, float)
    def move_at(self, posx, posy):
        if self.moveat_action.isChecked():
            self.sig_double_clicked.emit(posx, posy)

    def show_histo(self):
        show_state = self.histo_action.isChecked()
        self.viewer.histo_widget.setVisible(show_state)

    def show_all(self):
        self.show_scans()

    def show_none(self):
        self.show_scans(False)

    def show_scans(self, show=True):
        for child in self.settings.child('scans'):
            val = child.value()
            val['checked'] = show
            child.setValue(val)
            child.sigValueChanged.emit(child, val)

    def list_2Dscans(self):
        try:
            scans = self.h5module.get_h5file_scans()
            # settings=[dict(scan_name=node._v_name,path=node._v_pathname, pixmap=nparray2Qpixmap(node.read()))),...]
            params = []
            for child in self.settings.child(('scans')).children():
                if 'Scan' in child.name():
                    self.settings.child(('scans')).removeChild(child)
            for scan in scans:
                params.append({'name': scan['scan_name'], 'type': 'pixmap_check',
                               'value': dict(data=scan['data'], checked=False, path=scan['path'],
                                             info=scan['scan_name'])})
            self.settings.child(('scans')).addChildren(params)

            for child in self.settings.child(('scans')).children():
                val = child.value()
                val.update(dict(checked=True))
                child.setValue(val)
                child.sigValueChanged.emit(child, child.value())

        except Exception as e:
            logger.exception(str(e))

    def load_image(self):
        # image_filepath = str(utils.select_file(start_path=None, save=False, ext='h5'))
        data, fname, node_path = browse_data(ret_all=True)
        if data is not None and fname != '':
            self.h5module_image = H5BrowserUtil()
            self.h5module_image.open_file(fname, 'a')
            node = self.h5module_image.get_node(node_path)
            pixmaps = self.h5module_image.get_h5file_scans(node.parent_node)

            self.settings.child('settings', 'imagepath').setValue(fname)
            other_child = [child for child in self.settings.child(('scans')).children() if 'Scan' not in child.name()]
            if len(other_child) >= 1:
                for child in other_child:
                    self.settings.child(('scans')).removeChild(child)
            params = []
            for pixmap in pixmaps:
                params.append({'name': pixmap['scan_name'], 'type': 'pixmap_check',
                               'value': dict(data=pixmap['data'], checked=False, path=pixmap['path'])})
            self.settings.child(('scans')).addChildren(params)

            val = self.settings.child('scans', pixmaps[0]['scan_name']).value()
            val.update(dict(checked=True))
            self.settings.child('scans', pixmaps[0]['scan_name']).setValue(val)
            self.settings.child('scans', pixmaps[0]['scan_name']).sigValueChanged.emit(
                self.settings.child('scans', pixmaps[0]['scan_name']),
                self.settings.child('scans', pixmaps[0]['scan_name']).value())

    def load_data(self):
        self.h5module_path = str(gutils.select_file(start_path=config['data_saving']['h5file']['save_path'],
                                                    save=False, ext='h5'))
        if self.h5module_path != '':
            self.settings.child('settings', 'filepath').setValue(self.h5module_path)
            if self.h5module is not None:
                if self.h5module.isopen():
                    self.h5module.close_file()
            self.h5module.open_file(self.h5module_path, 'a')
            self.list_2Dscans()

    def set_aspect_ratio(self):
        if self.action_ratio.isChecked():
            self.viewer.image_widget.plotitem.vb.setAspectLocked(lock=True, ratio=1)
        else:
            self.viewer.image_widget.plotitem.vb.setAspectLocked(lock=False, ratio=1)

    def settings_changed(self, param, changes):
        """
            Check for changes in the given (parameter,change,information) tuple list.
            In case of value changed, update the DAQscan_settings tree consequently.

            =============== ============================================ ==============================
            **Parameters**    **Type**                                     **Description**
            *param*           instance of pyqtgraph parameter              the parameter to be checked
            *changes*         (parameter,change,information) tuple list    the current changes state
            =============== ============================================ ==============================
        """
        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':
                pass

            elif change == 'value':
                if param.parent().name() == 'scans':
                    if data['checked']:
                        try:
                            if 'Scan' in param.name():
                                h5module = self.h5module
                                nodes = [node for node in h5module.walk_nodes(data['path'])]
                            else:
                                h5module = self.h5module_image
                                nodes = [h5module.get_node(data['path'])]
                            ind = 0
                            for node in nodes:
                                flag = False
                                if 'type' in node.attrs.attrs_name and 'data_dimension' in node.attrs.attrs_name:
                                    if 'scan_type' in node.attrs.attrs_name:
                                        if node.attrs['scan_type'] == 'scan2D' and node.attrs['data_dimension'] == '0D':
                                            # 2d scan of 0D data
                                            flag = True
                                        elif node.attrs['scan_type'] == '' and node.attrs['data_dimension'] == '2D':
                                            # image data (2D) with no scan
                                            flag = True

                                if flag:
                                    isadaptive = 'adaptive' in node.attrs['scan_subtype'].lower()
                                    if isadaptive:
                                        im = TriangulationItem()
                                    else:
                                        im = ImageItem()
                                    im.setOpacity(1)
                                    # im.setOpts(axisOrder='row-major')
                                    self.viewer.image_widget.plotitem.addItem(im)
                                    im.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)

                                    if 'Scan' in param.name():
                                        if isadaptive:
                                            x_axis = h5module.get_node(h5module.get_node(data['path']).parent_node,
                                                                       utils.capitalize('scan_x_axis')).read()
                                            y_axis = h5module.get_node(h5module.get_node(data['path']).parent_node,
                                                                       utils.capitalize('scan_y_axis')).read()
                                        else:
                                            x_axis = np.unique(
                                                h5module.get_node(h5module.get_node(data['path']).parent_node,
                                                                  utils.capitalize('scan_x_axis')).read())
                                            y_axis = np.unique(
                                                h5module.get_node(h5module.get_node(data['path']).parent_node,
                                                                  utils.capitalize('scan_y_axis')).read())
                                    else:
                                        x_axis = np.unique(
                                            h5module.get_node(h5module.get_node(data['path']).parent_node,
                                                              utils.capitalize('x_axis')).read())
                                        y_axis = np.unique(
                                            h5module.get_node(h5module.get_node(data['path']).parent_node,
                                                              utils.capitalize('y_axis')).read())
                                    if not isadaptive:
                                        rect = QtCore.QRectF(np.min(x_axis), np.min(y_axis),
                                                             (np.max(x_axis) - np.min(x_axis)),
                                                             (np.max(y_axis) - np.min(y_axis)))
                                        im.setOpts(rescale=rect)
                                        im.setImage(node.read())
                                    else:
                                        im.setImage(np.vstack((x_axis, y_axis, node.read())).T)

                                    if ind == 0:
                                        # im.setLookupTable(colors_red)
                                        self.viewer.histogram_red.setImageItem(im)
                                        if not self.viewer.histogram_red.isVisible():
                                            self.viewer.histogram_red.setVisible(True)
                                    elif ind == 1:
                                        # im.setLookupTable(colors_green)
                                        self.viewer.histogram_green.setImageItem(im)
                                        if not self.viewer.histogram_green.isVisible():
                                            self.viewer.histogram_green.setVisible(True)
                                    else:
                                        # im.setLookupTable(colors_blue)
                                        self.viewer.histogram_blue.setImageItem(im)
                                        if not self.viewer.histogram_blue.isVisible():
                                            self.viewer.histogram_blue.setVisible(True)

                                    self.overlays.append(dict(name='{:s}_{:03d}'.format(param.name(), ind), image=im))

                                    ind += 1
                            # self.viewer.image_widget.view.autoRange()
                        except Exception as e:
                            logger.exception(str(e))

                    else:
                        for overlay in self.overlays[:]:
                            if param.name() in overlay['name']:
                                ind = self.overlays.index(overlay)
                                self.viewer.image_widget.plotitem.removeItem(overlay['image'])
                                self.overlays.pop(ind)

            elif change == 'parent':
                for overlay in self.overlays[:]:
                    if param.name() in overlay['name']:
                        ind = self.overlays.index(overlay)
                        self.viewer.image_widget.plotitem.removeItem(overlay['image'])
                        self.overlays.pop(ind)

    def setupUI(self):
        self.ui = QObject()
        layout = QtWidgets.QVBoxLayout()

        self.parent.setLayout(layout)
        sett_widget = QtWidgets.QWidget()
        self.sett_layout = QtWidgets.QHBoxLayout()
        sett_widget.setLayout(self.sett_layout)
        # creating a toolbar
        self.toolbar = QtWidgets.QToolBar()
        self.create_toolbar()
        layout.addWidget(self.toolbar)

        splitter = QtWidgets.QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # set viewer area
        widg = QtWidgets.QWidget()
        # self.viewer = Viewer2D(widg)
        self.viewer = Viewer2DBasic(widg)
        self.viewer.histogram_red.setVisible(False)
        self.viewer.histogram_green.setVisible(False)
        self.viewer.histogram_blue.setVisible(False)
        self.viewer.sig_double_clicked.connect(self.move_at)

        # displaying the scan list tree
        self.settings_tree = ParameterTree()
        # self.settings_tree.setMaximumWidth(300)
        self.settings_tree.setMinimumWidth(300)
        # self.settings_tree.setVisible(False)
        params_scan = [
            {'title': 'Settings', 'name': 'settings', 'type': 'group', 'children': [
                {'title': 'Load h5:', 'name': 'Load h5', 'type': 'action'},
                {'title': 'h5 path:', 'name': 'filepath', 'type': 'str', 'value': '', 'readonly': True},
                {'title': 'Load Image:', 'name': 'Load Image', 'type': 'action'},
                {'title': 'Image path:', 'name': 'imagepath', 'type': 'str', 'value': '', 'readonly': True},
            ]},
            {'title': 'Scans', 'name': 'scans', 'type': 'group', 'children': []},
        ]
        self.settings = Parameter.create(name='settings', type='group', children=params_scan)
        self.settings_tree.setParameters(self.settings, showTop=False)
        self.settings.sigTreeStateChanged.connect(self.settings_changed)

        self.settings.child('settings', 'Load h5').sigActivated.connect(self.load_data)
        self.settings.child('settings', 'Load Image').sigActivated.connect(self.load_image)

        self.ui.statusbar = QtWidgets.QStatusBar()
        self.ui.statusbar.setMaximumHeight(25)
        layout.addWidget(self.ui.statusbar)
        self.ui.log_message = QtWidgets.QLabel('Initializing')
        self.ui.statusbar.addPermanentWidget(self.ui.log_message)

        self.sett_layout.addWidget(self.settings_tree)
        splitter.addWidget(sett_widget)
        splitter.addWidget(self.viewer.parent)

    def show_image(self, data):
        """

        Parameters
        ----------
        data: (dict) with keys 'names', 'data', 'x_axis', 'y_axis', 'pixmap2D'
        """

        if self.h5module is None:
            scan_path, current_filename, dataset_path = H5Saver.set_current_scan_path(navigator_path, base_name='Scan',
                                                                                      update_h5=True,
                                                                                      next_scan_index=self.next_scan_index,
                                                                                      create_scan_folder=False)
            self.h5module = H5BrowserUtil()
            self.h5module.open_file(str(dataset_path.joinpath(dataset_path.name + ".h5")), 'w')

        else:
            scan_path, current_filename, dataset_path = H5Saver.set_current_scan_path(navigator_path, base_name='Scan',
                                                                                      update_h5=False,
                                                                                      next_scan_index=self.next_scan_index,
                                                                                      create_scan_folder=False)
            if not self.h5module.isopen():
                self.h5module.open_file(str(dataset_path.joinpath(dataset_path.name + ".h5")), 'a')

        h5group = self.h5module.root()
        data2D_group = self.h5module.get_set_group(h5group, 'Data2D')
        data2D_group.attrs.type = 'data2D'

        self.next_scan_index += 1
        curr_group = self.h5module.get_set_group('/Data2D', current_filename)
        live_group = self.h5module.get_set_group(curr_group, 'Live_scan_2D')
        live_group.attrs['pixmap2D'] = data['pixmap2D']

        xdata = data['x_axis']
        if isinstance(xdata, dict):
            xdata = xdata['data']
        xarray = self.h5module.create_carray(curr_group, "Scan_x_axis", obj=xdata,
                                             title=current_filename)
        xarray.attrs['type'] = 'navigation_axis'
        xarray.attrs['data_dimension'] = '1D'
        xarray.attrs['nav_index'] = 0

        ydata = data['y_axis']
        if isinstance(ydata, dict):
            ydata = ydata['data']
        yarray = self.h5module.create_carray(curr_group, "Scan_y_axis", obj=ydata,
                                             title=current_filename)
        yarray.attrs['type'] = 'navigation_axis'
        yarray.attrs['data_dimension'] = '1D'
        yarray.attrs['nav_index'] = 1

        for ind_channel, name in enumerate(data['names']):
            try:
                channel_group = self.h5module.get_set_group(live_group, name)
                channel_group.attrs.Channel_name = name
                array = self.h5module.create_carray(channel_group, current_filename + '_' + name,
                                                    obj=data['data'][ind_channel],
                                                    title='data', )
                array.attrs['type'] = 'data'
                array.attrs['data_dimension'] = '0D'
                array.attrs['data_name'] = name
                array.attrs['scan_type'] = 'scan2D'
                array.attrs['scan_subtype'] = ''
            except Exception as e:
                logger.exception(str(e))

        self.update_2Dscans()

    def update_2Dscans(self):
        try:
            if not self.h5module.isopen():
                self.h5module.open_file(self.h5module.file_path, 'a')
            scans = self.h5module.get_h5file_scans(self.h5module.root())
            # settings=[dict(scan_name=node._v_name,path=node._v_pathname, pixmap=nparray2Qpixmap(node.read()))),...]
            params = []
            children = [child.name() for child in self.settings.child(('scans')).children()]
            for scan in scans:
                if scan['scan_name'] not in children:
                    params.append({'name': scan['scan_name'], 'type': 'pixmap_check',
                                   'value': dict(data=scan['data'], checked=False, path=scan['path'],
                                                 info=scan['scan_name'])})
            self.settings.child(('scans')).addChildren(params)

            for child in self.settings.child(('scans')).children():
                if child.name() not in children:
                    val = child.value()
                    val.update(dict(checked=True))
                    child.setValue(val)
                    child.sigValueChanged.emit(child, child.value())

        except Exception as e:
            logger.exception(str(e))

    def update_h5file(self, h5file):
        if self.h5module is not None:
            self.h5module.h5file = h5file
        self.update_2Dscans()

    def update_status(self, txt, status_time=0, log_type=None):
        """
            Show the txt message in the status bar with a delay of status_time ms.

            =============== =========== =======================
            **Parameters**    **Type**    **Description**
            *txt*             string      The message to show
            *status_time*       int         the delay of showing
            *log_type*        string      the type of the log
            =============== =========== =======================
        """
        try:
            self.ui.statusbar.showMessage(txt, status_time)
            logger.info(txt)
        except Exception as e:
            logger.exception(str(e))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    widg = QtWidgets.QWidget()
    prog = Navigator(widg)
    widg.show()
    sys.exit(app.exec_())

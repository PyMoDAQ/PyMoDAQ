from pymodaq.utils.logger import set_logger, get_module_name, get_module_name
from pymodaq.utils.gui_utils.file_io import select_file
from qtpy import QtGui, QtWidgets, QtCore
from qtpy.QtCore import Qt, QObject, Slot, Signal

import sys
import os
import numpy as np
import tables

from pymodaq.utils.data import DataToExport, DataFromPlugins, DataDim, enum_checker
from pymodaq.utils.h5modules.data_saving import DataLoader
from pymodaq.utils.managers.parameter_manager import ParameterManager
from pymodaq.utils.managers.action_manager import ActionManager
from pymodaq.utils.plotting.data_viewers.viewer2D_basic import Viewer2DBasic
from pymodaq.utils.plotting.items.image import UniformImageItem, SpreadImageItem
from pymodaq.utils import daq_utils as utils
from pymodaq.utils.h5modules.browsing import browse_data, H5BrowserUtil
from pymodaq.utils.h5modules.saving import H5Saver
from pymodaq.utils import gui_utils as gutils

from pymodaq.utils.config import get_set_local_dir, Config

local_path = get_set_local_dir()
navigator_path = os.path.join(local_path, 'navigator_temp_files')
if not os.path.isdir(navigator_path):
    os.makedirs(navigator_path)

logger = set_logger(get_module_name(__file__))

Ntick = 128
colors_red = np.array([(int(r), 0, 0) for r in np.linspace(0, 255, Ntick)])
colors_green = np.array([(0, int(g), 0) for g in np.linspace(0, 255, Ntick)])
colors_blue = np.array([(0, 0, int(b)) for b in np.linspace(0, 255, Ntick)])
config = Config()


class Navigator(ParameterManager, ActionManager, QObject):

    settings_name = 'navigator_settings'
    log_signal = Signal(str)
    sig_double_clicked = Signal(float, float)
    params = [
        {'title': 'Settings', 'name': 'settings', 'type': 'group', 'children': [
            {'title': 'Load h5:', 'name': 'Load h5', 'type': 'action'},
            {'title': 'h5 path:', 'name': 'filepath', 'type': 'str', 'value': '', 'readonly': True},
            {'title': 'Load Image:', 'name': 'Load Image', 'type': 'action'},
            {'title': 'Image path:', 'name': 'imagepath', 'type': 'str', 'value': '', 'readonly': True},
        ]},
        {'title': 'Scans', 'name': 'scans', 'type': 'group', 'children': []},
    ]

    def __init__(self, parent=None, h5file_path=None):
        QObject.__init__(self)
        ParameterManager.__init__(self)
        ActionManager.__init__(self, toolbar=QtWidgets.QToolBar())
        if parent is None:
            parent = QtWidgets.QWidget()
        self.parent = parent
        self.title = 'Navigator'

        self.status_time = 1000

        self.h5saver = H5Saver()
        self.h5file_path = h5file_path
        self.viewer: Viewer2DBasic = None
        self.dataloader = DataLoader(self.h5saver)

        self.x_range = []
        self.y_range = []

        self.next_scan_index = 0

        self.overlays = []  # %list of imageItem items displaying 2D scans info

        self.h5module = H5BrowserUtil()

        if h5file_path is not None:
            self.h5saver.open_file(h5file_path, 'a')
            self.settings.child('settings', 'filepath').setValue(h5file_path)
            self.settings.child('settings', 'Load h5').hide()

            self.show_overlay()

        self.setup_actions()
        self.setup_ui()
        self.connect_things()

    def setup_actions(self):

        self.add_action('load_scan', 'Load Scan file', 'NewLayer', 'Load scan file (.h5)')
        self.add_action('load_image', 'Load Image File', 'Open_File_32', 'Load image file (.h5)')
        self.add_action('ratio', 'Viewbox Aspect Ratio', 'Zoom_1_1', 'Set viewbox aspect ratio to 1', checkable=True)
        self.add_action('move_at', 'Move at DoubleClicked', 'move_contour',
                        'When selected, double clicking on viewbox will move DAQ_Move modules',
                        checkable=True)
        self.add_action('select_all', 'Select All', 'select_all2', 'Select (show) all 2D scans on the viewer')
        self.add_action('select_none', 'Select None', 'select_none', 'Unselect (hide) all 2D scans on the viewer')
        self.add_action('histogram', 'Show Histograms', 'Histogram', 'Show (hide) histograms', checkable=True)

    def connect_things(self):

        self.connect_action('load_scan', self.load_data)
        self.connect_action('load_image', self.load_image)
        self.connect_action('ratio', self.set_aspect_ratio)
        self.connect_action('select_all', self.show_all)
        self.connect_action('select_none', self.show_none)
        self.connect_action('histogram', self.show_histo)

    @Slot(float, float)
    def move_at(self, posx, posy):
        if self.is_action_checked('move_at'):
            self.sig_double_clicked.emit(posx, posy)

    def show_histo(self):
        self.viewer.histo_widget.setVisible(self.is_action_checked('histogram'))

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

    def list_2D_scans(self):
        try:
            scans = self.h5saver.get_scan_groups()

            params = []
            for child in self.settings.child('scans').children():
                if 'Scan' in child.name():
                    self.settings.child('scans').removeChild(child)
            for scan in scans:
                _data = DataToExport('All')
                self.dataloader.load_all('/', _data)
                data_2D = _data.get_data_from_dim('Data2D')

                params.append({'name': scan.name, 'type': 'pixmap_check',
                               'value': dict(data=data_2D[0].data, checked=False, path=scan.path,
                                             info=scan.name)})
            self.settings.child('scans').addChildren(params)

            for child in self.settings.child('scans').children():
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
        self.h5file_path = str(select_file(start_path=config('data_saving', 'h5file', 'save_path'),
                                           save=False, ext='h5'))
        if self.h5file_path != '':
            self.settings.child('settings', 'filepath').setValue(self.h5file_path)
            if self.h5saver is not None:
                if self.h5saver.isopen():
                    self.h5saver.close_file()
            self.h5saver.open_file(self.h5file_path, 'a')
            self.list_2D_scans()

    def set_aspect_ratio(self):
        if self.is_action_checked('ratio'):
            self.viewer.image_widget.plotitem.vb.setAspectLocked(lock=True, ratio=1)
        else:
            self.viewer.image_widget.plotitem.vb.setAspectLocked(lock=False, ratio=1)

    def value_changed(self, param):

        if param.parent().name() == 'scans':
            if param.value()['checked']:
                try:
                    if 'Scan' in param.name():
                        h5module = self.h5module
                        nodes = [node for node in h5module.walk_nodes(param.value()['path'])]
                    else:
                        h5module = self.h5module_image
                        nodes = [h5module.get_node(param.value()['path'])]
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
                                im = SpreadImageItem()
                            else:
                                im = UniformImageItem()
                            im.setOpacity(1)
                            # im.setOpts(axisOrder='row-major')
                            self.viewer.image_widget.plotitem.addItem(im)
                            im.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)

                            if 'Scan' in param.name():
                                if isadaptive:
                                    x_axis = h5module.get_node(h5module.get_node(param.value()['path']).parent_node,
                                                               utils.capitalize('scan_x_axis')).read()
                                    y_axis = h5module.get_node(h5module.get_node(param.value()['path']).parent_node,
                                                               utils.capitalize('scan_y_axis')).read()
                                else:
                                    x_axis = np.unique(
                                        h5module.get_node(h5module.get_node(param.value()['path']).parent_node,
                                                          utils.capitalize('scan_x_axis')).read())
                                    y_axis = np.unique(
                                        h5module.get_node(h5module.get_node(param.value()['path']).parent_node,
                                                          utils.capitalize('scan_y_axis')).read())
                            else:
                                x_axis = np.unique(
                                    h5module.get_node(h5module.get_node(param.value()['path']).parent_node,
                                                      utils.capitalize('x_axis')).read())
                                y_axis = np.unique(
                                    h5module.get_node(h5module.get_node(param.value()['path']).parent_node,
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

    def param_deleted(self, param):
        for overlay in self.overlays[:]:
            if param.name() in overlay['name']:
                ind = self.overlays.index(overlay)
                self.viewer.image_widget.plotitem.removeItem(overlay['image'])
                self.overlays.pop(ind)

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout()

        self.parent.setLayout(layout)
        self.parent.layout().addWidget(self.toolbar)
        sett_widget = QtWidgets.QWidget()
        self.sett_layout = QtWidgets.QHBoxLayout()
        sett_widget.setLayout(self.sett_layout)

        layout.addWidget(self.toolbar)

        splitter = QtWidgets.QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # set viewer area
        widg = QtWidgets.QWidget()
        self.viewer = Viewer2DBasic(widg)
        self.viewer.histogram_red.setVisible(False)
        self.viewer.histogram_green.setVisible(False)
        self.viewer.histogram_blue.setVisible(False)
        self.viewer.sig_double_clicked.connect(self.move_at)

        self.settings.child('settings', 'Load h5').sigActivated.connect(self.load_data)
        self.settings.child('settings', 'Load Image').sigActivated.connect(self.load_image)

        self.statusbar = QtWidgets.QStatusBar()
        self.statusbar.setMaximumHeight(25)
        layout.addWidget(self.statusbar)
        self.log_message = QtWidgets.QLabel('Initializing')
        self.statusbar.addPermanentWidget(self.log_message)

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

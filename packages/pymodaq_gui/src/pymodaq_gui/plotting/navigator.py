import sys
import os

from pathlib import Path

import numpy as np
from qtpy import QtGui, QtWidgets, QtCore
from qtpy.QtCore import Qt, QObject, Slot, Signal

from pymodaq_utils.config import get_set_local_dir, Config
from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_data.data import DataToExport, DataWithAxes
from pymodaq_data.h5modules.data_saving import DataLoader

from pymodaq_gui.utils.file_io import select_file
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.managers.action_manager import ActionManager
from pymodaq_gui.plotting.data_viewers.viewer2D_basic import Viewer2DBasic
from pymodaq_gui.plotting.items.image import UniformImageItem, SpreadImageItem
from pymodaq_gui.h5modules.browsing import browse_data
from pymodaq_gui.h5modules.saving import H5Saver
from pymodaq_gui.parameter.pymodaq_ptypes.pixmap import PixmapCheckData


local_path = get_set_local_dir(user=True)
# navigator_path = local_path.joinpath('navigator_temp_files')
# if not navigator_path.is_dir():
#     navigator_path.mkdir()

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
        {'title': 'Image', 'name': 'image', 'type': 'pixmap_check'},
        {'title': 'Overlays', 'name': 'overlays', 'type': 'group', 'children': []},
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

        self._h5saver = H5Saver()
        self.dataloader = DataLoader(self._h5saver)

        self.h5file_path = h5file_path
        self.h5saver_image = H5Saver()

        self.viewer: Viewer2DBasic = None

        self.x_range = []
        self.y_range = []

        self.next_scan_index = 0

        self.overlays = []  # %list of imageItem items displaying 2D scans info

        # self.h5module = H5BrowserUtil()

        self.setup_actions()
        self.setup_ui()
        self.connect_things()
        self.set_aspect_ratio()

        if h5file_path is not None:
            self.h5saver.open_file(h5file_path, 'a')
            self.settings.child('settings', 'filepath').setValue(h5file_path)
            self.settings.child('settings', 'Load h5').hide()
            self.list_2D_scans()
            # self.show_overlay()

    @property
    def h5saver(self):
        return self._h5saver

    @h5saver.setter
    def h5saver(self, h5saver: H5Saver):
        self._h5saver = h5saver
        self.dataloader = DataLoader(h5saver)

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

        self.viewer.sig_double_clicked.connect(self.move_at)
        self.settings.child('settings', 'Load h5').sigActivated.connect(self.load_data)
        self.settings.child('settings', 'Load Image').sigActivated.connect(self.load_image)

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
        for child in self.settings.child('overlays'):
            val = child.value()
            val.checked = show
            child.setValue(val)
            child.sigValueChanged.emit(child, val)

    def get_data_from_scan_name(self, scan_name: str) -> DataToExport:
        _data = DataToExport('All')
        self.dataloader.load_all(f'/RawData/{scan_name}', _data)
        data_2D = _data.get_data_from_Naxes(2)
        for dat in data_2D:  # convert DataWithAxes DataND to Data2D
            dat.nav_indexes = ()
        return data_2D

    def set_axes(self, dwa: DataWithAxes):
        x_axis = dwa.get_axis_from_index(0)[0]
        y_axis = dwa.get_axis_from_index(1)[0]

        self.viewer.scaled_xaxis.axis_label = x_axis.label
        self.viewer.scaled_xaxis.axis_units = x_axis.units

        self.viewer.scaled_yaxis.axis_label = y_axis.label
        self.viewer.scaled_yaxis.axis_units = y_axis.units

    def list_2D_scans(self):
        try:
            scans = self.h5saver.get_scan_groups()

            params = []
            for child in self.settings.child('overlays').children():
                self.settings.child('overlays').removeChild(child)
            ind_overlay = 0
            axes_init = False
            for scan in scans:
                data_2D = self.get_data_from_scan_name(scan.name)
                for _dat in data_2D:
                    if not axes_init:
                        self.set_axes(_dat)
                        axes_init = True
                    params.append({'name': f'Overlay{ind_overlay:03.0f}', 'type': 'pixmap_check',
                                   'value': PixmapCheckData(data=_dat[0], checked=False, path=_dat.path,
                                                            info=f'{scan.name}/{_dat.get_full_name()}')})
                    ind_overlay += 1
            self.settings.child('overlays').addChildren(params)

            for child in self.settings.child('overlays').children():
                val = child.value()
                val.checked = True
                child.setValue(val)
                child.sigValueChanged.emit(child, child.value())

        except Exception as e:
            logger.exception(str(e))

    def load_image(self):
        data, fname, node_path = browse_data(ret_all=True)

        self.h5saver_image = H5Saver()
        self.h5saver_image.open_file(fname, 'r')

        self.settings.child('settings', 'imagepath').setValue(fname)
        self.settings.child('image').setValue(PixmapCheckData(data=data[0], checked=True, path=data.path))

        self.settings.child('image').sigValueChanged.emit(
            self.settings.child('image'),
            self.settings.child('image').value())

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
        self.viewer.set_aspect_ratio(self.is_action_checked('ratio'))

    def add_image_data(self, dwa: DataWithAxes):
        ims = []
        histograms = self.viewer.histograms
        for ind, data in enumerate(dwa):
            if ind > 2:
                break
            if dwa.distribution.name == 'spread':
                im = SpreadImageItem()
            else:
                im = UniformImageItem()
            ims.append(im)

            im.setOpacity(1)
            self.viewer.add_image_item(im, histogram=histograms[ind])
            im.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)

            if dwa.distribution.name == 'uniform':
                x_axis = dwa.get_axis_from_index(1)[0].get_data()
                y_axis = dwa.get_axis_from_index(0)[0].get_data()

                rect = QtCore.QRectF(np.min(y_axis), np.min(x_axis),
                                     (np.max(y_axis) - np.min(y_axis)),
                                     (np.max(x_axis) - np.min(x_axis)))

                im.setImage(data)
                im.setOpts(rect=rect)
            else:
                y_axis, x_axis = dwa.get_axis_from_index(0)
                im.setImage(np.vstack((x_axis, y_axis, dwa.data[0])).T)
            histograms[ind].setImageItem(im)
        return ims

    def remove_image_data(self, param):
        for overlay in self.overlays[:]:
            if param.name() in overlay['name']:
                ind = self.overlays.index(overlay)
                for image in overlay['images']:
                    self.viewer.plotitem.removeItem(image)
                self.overlays.pop(ind)

    def value_changed(self, param):

        if param.parent().name() == 'overlays':
            data: PixmapCheckData = param.value()
            if data.checked:
                dwa = self.dataloader.load_data(data.path, load_all=True)
                ims = self.add_image_data(dwa)
                self.overlays.append(dict(name=f'{param.name()}_{0}', images=ims))

            else:
                self.remove_image_data(param)
        elif param.name() == 'image':
            data: PixmapCheckData = param.value()
            if data.checked:
                dataloader = DataLoader(self.h5saver_image)
                dwa = dataloader.load_data(data.path)
                ims = self.add_image_data(dwa)
                self.overlays.append(dict(name='{:s}_{:03d}'.format(param.name(), 0), images=ims))
            else:
                self.remove_image_data(param)

    def param_deleted(self, param):
        self.remove_image_data(param)

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
        self.viewer.histogram_red.setVisible(True)
        self.viewer.histogram_green.setVisible(True)
        self.viewer.histogram_blue.setVisible(True)
        self.viewer.histogram_adaptive.setVisible(False)

        self.statusbar = QtWidgets.QStatusBar()
        self.statusbar.setMaximumHeight(25)
        layout.addWidget(self.statusbar)
        self.log_message = QtWidgets.QLabel('Initializing')
        self.statusbar.addPermanentWidget(self.log_message)

        self.sett_layout.addWidget(self.settings_tree)
        splitter.addWidget(sett_widget)
        splitter.addWidget(self.viewer.parent)

    def update_h5file(self, h5file):
        if self.h5saver is not None:
            self.h5saver.h5file = h5file
            self.dataloader = DataLoader(self.h5saver)
        self.list_2D_scans()

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



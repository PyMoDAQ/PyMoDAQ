from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QTimer, QDateTime, QDate, QTime

import sys
import os
from collections import OrderedDict
import numpy as np
import tables

from pyqtgraph.dockarea import Dock, DockArea
from pyqtgraph.parametertree import Parameter, ParameterTree
from pyqtgraph import HistogramLUTWidget
import pymodaq.daq_utils.custom_parameter_tree as custom_tree# to be placed after importing Parameter
from pymodaq.daq_utils.h5browser import browse_data
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D, ImageItem, ImageWidget
from pymodaq.daq_utils import daq_utils as utils

Ntick = 128
colors_red =np.array([(int(r),0,0) for r in np.linspace(0,255,Ntick)])
colors_green=np.array([(0,int(g),0) for g in np.linspace(0,255,Ntick)])
colors_blue=np.array([(0,0,int(b)) for b in np.linspace(0,255,Ntick)])

class Navigator(QObject):
    log_signal = pyqtSignal(str)
    sig_double_clicked = pyqtSignal(float, float)

    def __init__(self,parent=None, h5file=None):
        super(Navigator,self).__init__(parent)

        if parent is None:
            parent = QtWidgets.QWidget()
        self.parent = parent
        self.title = 'Navigator'
        self.status_time = 1000
        self.x_range = []
        self.y_range = []

        self.viewer = None
        self.overlays=[]#%list of imageItem items displaying 2D scans info
        self.h5file_path = None
        self.h5file = h5file
        if h5file is not None:
            self.settings.child('settings', 'filepath').setValue(h5file.filename)
            self.settings.child('settings', 'Load h5').hide()
            self.show_overlay()

        self.setupUI()

    def create_toolbar(self):
        iconload = QtGui.QIcon()
        iconload.addPixmap(QtGui.QPixmap(":/Labview_icons/Icon_Library/OpenLayers.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.loadaction = QtWidgets.QAction(iconload, "Load scan file (.h5)", None)
        self.toolbar.addAction(self.loadaction)
        self.loadaction.triggered.connect(self.load_data)

        iconloadim = QtGui.QIcon()
        iconloadim.addPixmap(QtGui.QPixmap(":/Labview_icons/Icon_Library/Open_File_32.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.loadactionim = QtWidgets.QAction(iconloadim, "Load image file (.h5)", None)
        self.toolbar.addAction(self.loadactionim)
        self.loadactionim.triggered.connect(self.load_image)

        icon_ratio = QtGui.QIcon()
        icon_ratio.addPixmap(QtGui.QPixmap(":/Labview_icons/Icon_Library/Zoom_1_1.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.action_ratio = QtWidgets.QAction(icon_ratio, "Set viewbox aspect ratio to 1", None)
        self.action_ratio.setCheckable(True)
        self.toolbar.addAction(self.action_ratio)
        self.action_ratio.triggered.connect(self.set_aspect_ratio)

        icon_moveat = QtGui.QIcon()
        icon_moveat.addPixmap(QtGui.QPixmap(":/Labview_icons/Icon_Library/move_contour.png"), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
        self.moveat_action = QtWidgets.QAction(icon_moveat, "When selected, double clicking on viewbox will move DAQ_Move modules", None)
        self.moveat_action.setCheckable(True)
        self.toolbar.addAction(self.moveat_action)

    @pyqtSlot(float,float)
    def double_clicked(self,posx,posy):
        if self.moveat_action.isChecked():
            self.sig_double_clicked.emit(posx,posy)


    def list_2Dscans(self):
        try:
            scans=utils.get_h5file_scans(self.h5file)
            #settings=[dict(scan_name=node._v_name,path=node._v_pathname, pixmap=nparray2Qpixmap(node.read()))),...]
            params=[]
            for child in self.settings.child(('scans')).children():
                if 'Scan' in child.name():
                    self.settings.child(('scans')).removeChild(child)
            for scan in scans:
                params.append({'name': scan['scan_name'], 'type': 'pixmap_check', 'value':dict(data=scan['data'],checked=False,path=scan['path'])})
            self.settings.child(('scans')).addChildren(params)

            for child in self.settings.child(('scans')).children():
                val = child.value()
                val.update(dict(checked = True))
                child.setValue(val)
                child.sigValueChanged.emit(child, child.value())

        except Exception as e:
            self.update_status(str(e),status_time=self.status_time,log_type='log')

    def load_image(self):
        image_filepath = str(utils.select_file(start_path=None, save=False, ext='h5'))
        if image_filepath != '.':
            self.h5file_image = tables.open_file(image_filepath)
            pixmaps = utils.get_h5file_scans(self.h5file_image)
            self.settings.child('settings', 'imagepath').setValue(image_filepath)
            other_child = [child for child in self.settings.child(('scans')).children() if 'Scan' not in child.name()]
            if len(other_child) >= 1:
                for child in other_child:
                    self.settings.child(('scans')).removeChild(child)
            params = []
            for pixmap in pixmaps:
                params.append({'name': pixmap['scan_name'], 'type': 'pixmap_check', 'value':dict(data=pixmap['data'],checked=False,path=pixmap['path'])})
            self.settings.child(('scans')).addChildren(params)

            val = self.settings.child('scans', pixmaps[0]['scan_name']).value()
            val.update(dict(checked = True))
            self.settings.child('scans', pixmaps[0]['scan_name']).setValue(val)
            self.settings.child('scans', pixmaps[0]['scan_name']).sigValueChanged.emit(self.settings.child('scans', pixmaps[0]['scan_name']),
                                                                                       self.settings.child('scans', pixmaps[0]['scan_name']).value())


    def load_data(self):
        self.h5file_path = str(utils.select_file(start_path=None,save=False, ext='h5'))
        if self.h5file_path != '.':
            self.settings.child('settings', 'filepath').setValue(self.h5file_path)
            if self.h5file is not None:
                self.h5file.close()
            self.h5file = tables.open_file(self.h5file_path)
            self.list_2Dscans()

    def set_aspect_ratio(self):
        if self.action_ratio.isChecked():
            self.viewer.image_widget.plotitem.vb.setAspectLocked(lock=True, ratio=1)
        else:
            self.viewer.image_widget.plotitem.vb.setAspectLocked(lock=False, ratio=1)

    def settings_changed(self,param,changes):
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
                                h5file = self.h5file
                            else:
                                h5file = self.h5file_image
                            ind = 0
                            for node in h5file.walk_nodes(data['path']):
                                if 'Scan' in param.name():
                                    if 'data_type' in node._v_attrs and 'scan_type' in node._v_attrs:
                                        flag = node._v_attrs['data_type'] == '0D' and node._v_attrs['scan_type'] == 'Scan2D'
                                    else:
                                        flag = False
                                else:
                                    flag = 'pixmap2D' in node._v_attrs
                                if flag:
                                    im=ImageItem()
                                    im.setOpacity(1)
                                    #im.setOpts(axisOrder='row-major')
                                    self.viewer.image_widget.plotitem.addItem(im)
                                    im.setCompositionMode(QtGui.QPainter.CompositionMode_Plus)
                                    im.setImage(node.read())
                                    if 'Scan' in param.name():
                                        x_axis = h5file.get_node(data['path']+'/scan_x_axis_unique').read()
                                        y_axis = h5file.get_node(data['path']+'/scan_y_axis_unique').read()
                                    else:
                                        x_axis = h5file.get_node(data['path'])._v_parent._f_get_child('x_axis')
                                        y_axis = h5file.get_node(data['path'])._v_parent._f_get_child('y_axis')


                                    dx = x_axis[1]-x_axis[0]
                                    dy = y_axis[1]-y_axis[0]
                                    im.setRect(QtCore.QRectF(np.min(x_axis),np.min(y_axis),np.max(x_axis)-np.min(x_axis)+dx,np.max(y_axis)-np.min(y_axis)+dy))
                                    if ind == 0:
                                        #im.setLookupTable(colors_red)
                                        self.viewer.ui.histogram_red.setImageItem(im)
                                        if not self.viewer.ui.histogram_red.isVisible():
                                            self.viewer.ui.histogram_red.setVisible(True)
                                    elif ind == 1:
                                        #im.setLookupTable(colors_green)
                                        self.viewer.ui.histogram_green.setImageItem(im)
                                        if not self.viewer.ui.histogram_green.isVisible():
                                            self.viewer.ui.histogram_green.setVisible(True)
                                    else:
                                        #im.setLookupTable(colors_blue)
                                        self.viewer.ui.histogram_blue.setImageItem(im)
                                        if not self.viewer.ui.histogram_blue.isVisible():
                                            self.viewer.ui.histogram_blue.setVisible(True)

                                    self.overlays.append(dict(name='{:s}_{:03d}'.format(param.name(),ind),image=im))

                                    ind += 1
                            self.viewer.image_widget.view.autoRange()
                        except  Exception as e:
                            self.update_status(str(e),status_time=self.status_time,log_type='log')

                    else:
                        for im in self.overlays[:]:
                            if param.name() in im['name']:
                                ind = self.overlays.index(im)
                                self.viewer.image_widget.plotitem.removeItem(im['image'])
                                self.overlays.pop(ind)

            elif change == 'parent':
                for overlay in self.overlays[:]:
                    if param.name() in overlay['name']:
                        ind = self.overlays.index(im)
                        self.viewer.image_widget.plotitem.removeItem(overlay['image'])
                        self.overlays.pop(ind)


    def setupUI(self):
        self.ui = QObject()
        layout =QtWidgets.QVBoxLayout()
        self.parent.setLayout(layout)

        # creating a toolbar
        self.toolbar = QtWidgets.QToolBar()
        self.create_toolbar()
        layout.addWidget(self.toolbar)

        splitter = QtWidgets.QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)



        #set viewer area
        widg = QtWidgets.QWidget()
        self.viewer = Viewer2D(widg)
        self.viewer.ui.widget.setVisible(False)
        self.viewer.image_widget.plotitem.vb.setAspectLocked(lock=False, ratio=1)
        self.viewer.ui.widget_histo.setVisible(True)
        #displaying the scan list tree
        self.settings_tree = ParameterTree()
        #self.settings_tree.setMaximumWidth(300)
        self.settings_tree.setMinimumWidth(300)
        #self.settings_tree.setVisible(False)
        params_scan = [
                        {'title': 'Settings', 'name': 'settings', 'type': 'group', 'children': [
                            {'title': 'Load h5:', 'name': 'Load h5', 'type': 'action'},
                            {'title': 'h5 path:', 'name': 'filepath', 'type': 'str', 'value': '', 'readonly': True},
                            {'title': 'Load Image:', 'name': 'Load Image', 'type': 'action'},
                            {'title': 'Image path:', 'name': 'imagepath', 'type': 'str', 'value': '', 'readonly': True},
                        ]},
                        {'title': 'Scans', 'name': 'scans', 'type': 'group', 'children': []},
                        ]
        self.settings=Parameter.create(name='settings', type='group', children=params_scan)
        self.settings_tree.setParameters(self.settings, showTop=False)
        self.settings.sigTreeStateChanged.connect(self.settings_changed)

        self.settings.child('settings', 'Load h5').sigActivated.connect(self.load_data)
        self.settings.child('settings', 'Load Image').sigActivated.connect(self.load_image)

        self.ui.statusbar = QtWidgets.QStatusBar()
        self.ui.statusbar.setMaximumHeight(25)
        layout.addWidget(self.ui.statusbar)
        self.ui.log_message = QtWidgets.QLabel('Initializing')
        self.ui.statusbar.addPermanentWidget(self.ui.log_message)



        splitter.addWidget(self.settings_tree)
        splitter.addWidget(widg)



    def update_2Dscans(self):
        try:
            scans=utils.get_h5file_scans(self.h5file)
            #settings=[dict(scan_name=node._v_name,path=node._v_pathname, pixmap=nparray2Qpixmap(node.read()))),...]
            params=[]
            children = [child.name() for child in self.settings.child(('scans')).children()]
            for scan in scans:
                if scan['scan_name'] not in children:
                    params.append({'name': scan['scan_name'], 'type': 'pixmap_check', 'value':dict(data=scan['data'],checked=False,path=scan['path'])})
            self.settings.child(('scans')).addChildren(params)

            for child in self.settings.child(('scans')).children():
                if child.name() not in children:
                    val = child.value()
                    val.update(dict(checked = True))
                    child.setValue(val)
                    child.sigValueChanged.emit(child, child.value())

        except Exception as e:
            self.update_status(str(e),status_time=self.status_time,log_type='log')

    def update_h5file(self, h5file):
        self.h5file = h5file
        self.list_2Dscans()

    def update_status(self,txt,status_time=0,log_type=None):
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
            self.ui.statusbar.showMessage(txt,status_time)
            if log_type is not None:
                self.log_signal.emit(self.title+': '+txt)
        except Exception as e:
            pass

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    widg = QtWidgets.QWidget()
    prog = Navigator(widg)
    widg.show()
    sys.exit(app.exec_())
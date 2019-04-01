from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal, QRectF, QRect, QPointF
import sys
import numpy as np
from collections import OrderedDict
from pyqtgraph import gaussianFilter, ROI, RectROI, PolyLineROI, Point


import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter, ParameterTree
import pymodaq.daq_utils.custom_parameter_tree
from pyqtgraph.dockarea import DockArea, Dock
from easydict import EasyDict as edict

class PolyLineROI_custom(PolyLineROI):
    def __init__(self,*args,**kwargs):
        super(PolyLineROI_custom,self).__init__(*args,**kwargs)

    def get_vertex(self):
        return [h['item'].pos() for h in self.handles]

    def getArrayIndexes(self, spacing=1, **kwds):
        imgPts = self.get_vertex()
        positions=[]
        for i in range(len(imgPts) - 1):
            d = Point(imgPts[i + 1] - imgPts[i])
            o = Point(imgPts[i])
            vect=Point(d.norm())
            Npts=0
            while Npts*spacing < d.length():

                positions.append(((o+Npts*spacing*vect).x(),(o+Npts*spacing*vect).y()))
                Npts+=1

        return positions


class ScanSelector(QObject):

    scan_select_signal = pyqtSignal(ROI)

    params = [
        {'title': 'Scan options', 'name': 'scan_options', 'type': 'group', 'children': [
            {'title': 'Sources:', 'name': 'sources', 'type': 'list',},
            {'title': 'Viewers:', 'name': 'viewers', 'type': 'list', },
            {'title': 'Scan type:', 'name': 'scan_type', 'type': 'list', 'values': ['Scan1D', 'Scan2D'], 'value': 'Scan2D'},
            ]},
        {'title': 'Scan Area', 'name': 'scan_area', 'type': 'group', 'children': [
            {'title': 'ROI select:', 'name': 'ROIselect', 'type': 'group', 'visible': True, 'children': [
                {'title': 'x0:', 'name': 'x0', 'type': 'int', 'value': 0, 'min': 0},
                {'title': 'y0:', 'name': 'y0', 'type': 'int', 'value': 0, 'min': 0},
                {'title': 'width:', 'name': 'width', 'type': 'int', 'value': 10, 'min': 1},
                {'title': 'height:', 'name': 'height', 'type': 'int', 'value': 10, 'min': 1},
            ]},
            {'title': 'Coordinates:', 'name': 'coordinates', 'type': 'itemselect', 'visible': True},
            ]},
        ]

    def __init__(self, viewer_items =[], scan_type='Scan2D', positions=[]):
        """

        Parameters
        ----------
        viewer_items: dict where the keys are the titles of the sources while the values are dict with keys
                        viewers: list of plotitems
                        names: list of viewer titles
        scan_type: (str) either 'Scan1D' correspondign to a polyline ROI or 'Scan2D' for a rect Roi
        positions: list
                        in case of 'Scan1D', should be a sequence of 2 floats sequence [(x1,y1),(x2,y2),(x3,y3),...]
                        in case of 'Scan2D', should be a sequence of 4 floats (x, y , w, h)
        """
        super(ScanSelector, self).__init__()
        self._viewers_items = viewer_items
        self.sources_names = list(viewer_items.keys())
        if len(viewer_items) != 0:
            self.scan_selector_source = viewer_items[self.sources_names[0]]['viewers'][0]
        else:
            self.scan_selector_source = None
        self.scan_selector = None
        self.setupUI()
        self.settings.child('scan_options', 'scan_type').setValue(scan_type)

        self.remove_scan_selector()
        if self.scan_selector_source is not None:
            if len(viewer_items[self.sources_names[0]]['viewers']) == 1:
                self.settings.child('scan_options', 'viewers').hide()
        else:
            self.settings.child('scan_options', 'viewers').hide()
        self.update_scan_area_type()

        if scan_type == "Scan1D" and positions != []:
            self.scan_selector.setPoints(positions)
        elif scan_type == 'Scan2D' and positions != []:
            self.scan_selector.setPos(positions[:2])
            self.scan_selector.setSize(positions[3:])

    @property
    def viewers_items(self):
        return self._viewers_items

    @viewers_items.setter
    def viewers_items(self, items):
        self._viewers_items = items
        self.sources_names = list(items.keys())
        self.scan_selector_source = items[self.sources_names[0]]['viewers'][0]
        self.settings.child('scan_options', 'sources').setOpts(limits=self.sources_names)
        viewer_names = self._viewers_items[self.sources_names[0]]['names']
        self.settings.child('scan_options', 'viewers').setOpts(limits=viewer_names)

    def show(self, visible=True):
        self.show_scan_selector(visible)
        if visible:
            self.widget.show()
        else:
            self.widget.hide()

    def hide(self):
        self.show(False)

    def setupUI(self):
        self.widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()

        self.settings_tree = ParameterTree()
        layout.addWidget(self.settings_tree,10)
        self.settings_tree.setMinimumWidth(300)
        self.settings=Parameter.create(name='Settings', type='group', children=self.params)
        self.settings_tree.setParameters(self.settings, showTop=False)

        self.settings.child('scan_options', 'sources').setOpts(limits=self.sources_names)
        if len(self.viewers_items):
            viewer_names = self._viewers_items[self.sources_names[0]]['names']
        else:
            viewer_names = []
        self.settings.child('scan_options', 'viewers').setOpts(limits=viewer_names)

        self.settings.sigTreeStateChanged.connect(self.source_changed)
        self.widget.setLayout(layout)

        #self.widget.show()
        self.widget.setWindowTitle('Scan Selector')

    def source_changed(self,param,changes):
        for param, change, data in changes:
            path = self.settings.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
            if change == 'childAdded':
                pass

            elif change == 'value':
                if param.name() == 'sources' and param.value() is not None:
                    viewer_names= self._viewers_items[param.value()]['names']
                    self.settings.child('scan_options', 'viewers').setOpts(limits=viewer_names)
                    if len(viewer_names) == 1:
                        self.settings.child('scan_options', 'viewers').hide()

                    self.remove_scan_selector()
                    self.scan_selector_source = self._viewers_items[param.value()]['viewers'][0]
                    self.update_scan_area_type()

                if param.name() == 'scan_type':


                    if param.value() == 'Scan1D':
                        self.settings.child('scan_area', 'ROIselect').hide()
                        self.settings.child('scan_area', 'coordinates').show()
                        self.remove_scan_selector()
                        self.update_scan_area_type()
                    else:
                        self.settings.child('scan_area', 'ROIselect').show()
                        self.settings.child('scan_area', 'coordinates').hide()
                        self.remove_scan_selector()
                        self.update_scan_area_type()
                    self.scan_selector.sigRegionChangeFinished.emit(self.scan_selector)


            elif change == 'parent':
                pass

    def remove_scan_selector(self):
        if self.scan_selector_source is not None:
            try:
                self.scan_selector_source.image_widget.plotitem.removeItem(self.scan_selector)
            except:
                pass

    pyqtSlot(str)
    def update_scan_area_type(self):

        if self.settings.child('scan_options', 'scan_type').value() == 'Scan1D':
            scan_area_type = 'PolyLines'
        else:
            scan_area_type = 'Rect'


        self.remove_scan_selector()
        if scan_area_type == 'Rect':
            self.scan_selector = RectROI([0,0],[10,10])

        elif scan_area_type == 'PolyLines':
            self.scan_selector = PolyLineROI_custom([(0, 0), [10, 10]])
        if self.scan_selector_source is not None:
            self.scan_selector.sigRegionChangeFinished.connect(self.update_scan)
            self.scan_selector_source.image_widget.plotitem.addItem(self.scan_selector)
            self.show_scan_selector()

            self.scan_selector.sigRegionChangeFinished.emit(self.scan_selector)


    def show_scan_selector(self,visible=True):
        self.scan_selector.setVisible(visible)

    def update_scan(self, roi):
        if self.scan_selector_source is not None:
            if isinstance(roi, RectROI):
                self.settings.child('scan_area', 'ROIselect', 'x0').setValue(roi.pos().x())
                self.settings.child('scan_area', 'ROIselect', 'y0').setValue(roi.pos().y())
                self.settings.child('scan_area', 'ROIselect', 'width').setValue(roi.size().x())
                self.settings.child('scan_area', 'ROIselect', 'height').setValue(roi.size().y())
            elif isinstance(roi, PolyLineROI_custom):
                self.settings.child('scan_area', 'coordinates').setValue(dict(all_items=['({:.03f} , {:.03f})'.format(pt.x(),
                            pt.y()) for pt in roi.get_vertex()],selected=[]))

            self.scan_select_signal.emit(roi)

if __name__ == '__main__':
    class UI():
        def __init__(self):
            pass


    from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D
    class FakeDaqScan():

        def __init__(self, area):
            self.area = area
            self.detector_modules = None
            self.ui = UI()
            self.dock = Dock('2D scan', size=(500, 300), closable=False)

            form = QtWidgets.QWidget()
            self.ui.scan2D_graph = Viewer2D(form)
            self.dock.addWidget(form)
            self.area.addDock(self.dock)

    from pymodaq.daq_utils.daq_enums import DAQ_type
    from pymodaq.daq_viewer.daq_viewer_main import DAQ_Viewer


    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = DockArea()

    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('pymodaq main')
    fake = FakeDaqScan(area)

    prog = DAQ_Viewer(area, title="Testing", DAQ_type=DAQ_type['DAQ2D'].name, parent_scan=fake)
    prog.ui.IniDet_pb.click()
    QThread.msleep(1000)
    QtWidgets.QApplication.processEvents()
    prog2 = DAQ_Viewer(area, title="Testing2", DAQ_type=DAQ_type['DAQ2D'].name, parent_scan=fake)
    prog2.ui.IniDet_pb.click()
    QThread.msleep(1000)
    QtWidgets.QApplication.processEvents()


    fake.detector_modules=[prog, prog2]
    items=OrderedDict()
    items[prog.title]=dict(viewers=[view for view in prog.ui.viewers],
                           names=[view.title for view in prog.ui.viewers],
                           )
    items[prog2.title] = dict(viewers=[view for view in prog2.ui.viewers],
                             names=[view.title for view in prog2.ui.viewers])
    items["DaqScan"] = dict(viewers=[fake.ui.scan2D_graph],
                             names=["DaqScan"])

    selector = ScanSelector(items,scan_type='Scan1D', positions=[(10,-10),(4,4),(80,50)])

    win.show()
    sys.exit(app.exec_())
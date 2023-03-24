from qtpy import QtWidgets
from qtpy.QtCore import QObject, Slot, QThread, Signal
import sys
from typing import List, Dict
from collections import OrderedDict
from pyqtgraph import ROI, RectROI, PolyLineROI, Point

from pymodaq.utils.parameter import Parameter, ParameterTree
from pymodaq.utils.managers.parameter_manager import ParameterManager
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.gui_utils import DockArea, Dock
from pymodaq.utils.plotting.utils.plot_utils import QVector
from pymodaq.utils import daq_utils as utils

logger = set_logger(get_module_name(__file__))


class PolyLineROI(PolyLineROI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_vertex(self):
        return [h['item'].pos() for h in self.handles]

    def get_vectors(self):
        imgPts = self.get_vertex()
        d = []
        for i in range(len(imgPts) - 1):
            d.append(QVector(imgPts[i], Point(imgPts[i + 1])))
        return d

    def getArrayIndexes(self, spacing=1, **kwds):
        imgPts = self.get_vertex()
        positions = []
        for i in range(len(imgPts) - 1):
            d = Point(imgPts[i + 1] - imgPts[i])
            o = Point(imgPts[i])
            vect = Point(d.norm())
            Npts = 0
            while Npts * spacing < d.length():
                positions.append(((o + Npts * spacing * vect).x(), (o + Npts * spacing * vect).y()))
                Npts += 1
        # add_last point not taken into account
        positions.append((imgPts[-1].x(), imgPts[-1].y()))
        return positions


class ScanSelector(ParameterManager, QObject):
    """Allows selection of a given 2D viewer to get scan info

    respectively scan2D or scan Tabular from respectively a rectangular ROI or a polyline

    Parameters
    ----------
    viewer_items: dict
        where the keys are the titles of the sources while the values are dict with keys
        * viewers: list of plotitems
        * names: list of viewer titles

    scan_type: str
        either 'Tabular' corresponding to a polyline ROI or 'Scan2D' for a rect Roi
    positions: list
        in case of 'Tabular', should be a sequence of 2 floats sequence [(x1,y1),(x2,y2),(x3,y3),...]
        in case of 'Scan2D', should be a sequence of 4 floats (x, y , w, h)
    """
    scan_select_signal = Signal(ROI)

    params = [
        {'title': 'Scan options', 'name': 'scan_options', 'type': 'group', 'children': [
            {'title': 'Sources:', 'name': 'sources', 'type': 'list', },
            {'title': 'Viewers:', 'name': 'viewers', 'type': 'list', },
            {'title': 'Scan type:', 'name': 'scan_type', 'type': 'list', 'limits': ['Tabular', 'Scan2D'],
             'value': 'Scan2D'},
        ]},
        {'title': 'Scan Area', 'name': 'scan_area', 'type': 'group', 'children': [
            {'title': 'ROI select:', 'name': 'ROIselect', 'type': 'group', 'visible': True, 'children': [
                {'title': 'x0:', 'name': 'x0', 'type': 'float', 'value': 0,},
                {'title': 'y0:', 'name': 'y0', 'type': 'float', 'value': 0,},
                {'title': 'width:', 'name': 'width', 'type': 'float', 'value': 10, 'min': 0.00001},
                {'title': 'height:', 'name': 'height', 'type': 'float', 'value': 10, 'min': 0.00001},
            ]},
            {'title': 'Coordinates:', 'name': 'coordinates', 'type': 'itemselect', 'visible': True},
        ]},
    ]

    def __init__(self, viewer_items=None, scan_type='Scan2D', positions=[]):
        QObject.__init__(self)
        ParameterManager.__init__(self, 'selector_settings')

        if viewer_items is None:
            viewer_items = dict([])

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
        self.settings.child('scan_options', 'sources').setOpts(limits=self.sources_names)
        if len(self.viewers_items):
            viewer_names = self._viewers_items[self.sources_names[0]]['names']
        else:
            viewer_names = []
        self.settings.child('scan_options', 'viewers').setOpts(limits=viewer_names)

    def value_changed(self, param):

        if param.name() == 'sources' and param.value() is not None:
            viewer_names = self._viewers_items[param.value()]['names']
            self.settings.child('scan_options', 'viewers').setOpts(limits=viewer_names)
            if len(viewer_names) == 1:
                self.settings.child('scan_options', 'viewers').hide()

            self.remove_scan_selector()
            self.scan_selector_source = self._viewers_items[param.value()]['viewers'][0]
            self.update_scan_area_type()

        if param.name() == 'scan_type':

            if param.value() == 'Tabular':
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


    def remove_scan_selector(self):
        if self.scan_selector_source is not None:
            try:
                self.scan_selector_source.image_widget.plotitem.removeItem(self.scan_selector)
            except Exception as e:
                logger.exception(str(e))
                pass

    Slot(str)

    def update_scan_area_type(self):

        if self.settings.child('scan_options', 'scan_type').value() == 'Tabular':
            scan_area_type = 'PolyLines'
        else:
            scan_area_type = 'Rect'

        self.remove_scan_selector()
        if scan_area_type == 'Rect':
            self.scan_selector = RectROI([0, 0], [10, 10])

        elif scan_area_type == 'PolyLines':
            self.scan_selector = PolyLineROI([(0, 0), [10, 10]])
        if self.scan_selector_source is not None:
            self.scan_selector.sigRegionChangeFinished.connect(self.update_scan)
            self.scan_selector_source.image_widget.plotitem.addItem(self.scan_selector)
            self.show_scan_selector()

            self.scan_selector.sigRegionChangeFinished.emit(self.scan_selector)

    def show_scan_selector(self, visible=True):
        self.scan_selector.setVisible(visible)

    def update_scan(self, roi):
        if self.scan_selector_source is not None:
            if isinstance(roi, RectROI):
                self.settings.child('scan_area', 'ROIselect', 'x0').setValue(roi.pos().x())
                self.settings.child('scan_area', 'ROIselect', 'y0').setValue(roi.pos().y())
                self.settings.child('scan_area', 'ROIselect', 'width').setValue(roi.size().x())
                self.settings.child('scan_area', 'ROIselect', 'height').setValue(roi.size().y())
            elif isinstance(roi, PolyLineROI):
                self.settings.child('scan_area', 'coordinates').setValue(
                    dict(all_items=['({:.03f} , {:.03f})'.format(pt.x(),
                                                                 pt.y()) for pt in roi.get_vertex()], selected=[]))

            self.scan_select_signal.emit(roi)



def main_fake_scan():
    from pymodaq.utils.plotting.data_viewers.viewer2D import Viewer2D
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer

    class UI:
        def __init__(self):
            pass

    class FakeDaqScan:

        def __init__(self, area):
            self.area = area
            self.detector_modules = None
            self.ui = UI()
            self.dock = Dock('2D scan', size=(500, 300), closable=False)

            form = QtWidgets.QWidget()
            self.ui.scan2D_graph = Viewer2D(form)
            self.dock.addWidget(form)
            self.area.addDock(self.dock)

    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    area = DockArea()

    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('pymodaq main')
    fake = FakeDaqScan(area)

    prog = DAQ_Viewer(area, title="Testing", daq_type='DAQ2D')#, parent_scan=fake)
    prog.init_hardware_ui(True)
    QThread.msleep(1000)
    QtWidgets.QApplication.processEvents()
    prog2 = DAQ_Viewer(area, title="Testing2", daq_type='DAQ2D')#, parent_scan=fake)
    prog2.init_hardware_ui(True)
    QThread.msleep(1000)
    QtWidgets.QApplication.processEvents()

    fake.detector_modules = [prog, prog2]
    items = OrderedDict()
    items[prog.title] = dict(viewers=[view for view in prog.ui.viewers],
                             names=[view.title for view in prog.ui.viewers],
                             )
    items[prog2.title] = dict(viewers=[view for view in prog2.ui.viewers],
                              names=[view.title for view in prog2.ui.viewers])
    items["DaqScan"] = dict(viewers=[fake.ui.scan2D_graph],
                            names=["DaqScan"])

    selector = ScanSelector(items, scan_type='Tabular', positions=[(10, -10), (4, 4), (80, 50)])

    win.show()


def main_navigator():
    from pymodaq.utils.plotting.navigator import Navigator
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer
    app = QtWidgets.QApplication(sys.argv)
    widg = QtWidgets.QWidget()
    navigator = Navigator(widg, h5file_path=r'C:\Data\2023\20230320\Dataset_20230320_001.h5')

    widg.show()
    navigator.list_2D_scans()

    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Viewer')
    win.show()

    viewer = DAQ_Viewer(area, title="Testing", daq_type='DAQ2D')
    viewer.init_hardware_ui(True)

    scan_selector = ScanSelector(viewer_items=dict(
        navigator=dict(viewers=[navigator.viewer], names=["Navigator"]),
        viewer=dict(viewers=viewer.viewers, names=[dock.name for dock in viewer.viewer_docks])))
    scan_selector.settings_tree.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    # main_fake_scan()
    main_navigator()

import importlib

import numpy as np
from qtpy import QtWidgets, QtCore
from qtpy.QtCore import QObject, Slot, QThread, Signal
import sys
from typing import List, Dict
from collections import OrderedDict
from pyqtgraph import ROI, RectROI, PolyLineROI, Point, LinearRegionItem
from abc import ABC, abstractmethod
from pymodaq.utils.parameter import Parameter, ParameterTree
from pymodaq.utils.managers.parameter_manager import ParameterManager
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.gui_utils import DockArea, Dock
from pymodaq.utils.plotting.utils.plot_utils import QVector
from pymodaq.utils import daq_utils as utils
from pymodaq.utils import gui_utils as gutils
from pymodaq.utils.enums import BaseEnum, enum_checker
from pymodaq.utils.parameter.pymodaq_ptypes import TableViewCustom
from pymodaq.utils.parameter import utils as putils


logger = set_logger(get_module_name(__file__))


class SelectorType(BaseEnum):
    ROI2D = 'RectangularRoi'
    ROI1D = 'LinearRegionItem'
    PolyLines = 'PolyLineROI'


class Selector:
    """Base class defining the interface for a Selector"""

    @abstractmethod
    def get_header(self):
        ...

    @abstractmethod
    def get_coordinates(self) -> np.ndarray:
        """Returns coordinates as a ndarray

        Particular implementation and returned array shape depends on the selector.
        """
        ...

    @abstractmethod
    def set_coordinates(self, coordinates: np.ndarray):
        """Set the coordinates of the selector using the input ndarray

        Particular implementation depends on the selector.
        """
        ...


class PolyLineROI(Selector, PolyLineROI):
    def __init__(self, *args, **kwargs):
        super().__init__(positions=[(0, 0), (10, 10)], *args, **kwargs)

    def get_header(self):
        return ['x', 'y']

    def get_coordinates(self) -> np.ndarray:
        return np.array([[vertex.x(), vertex.y()] for vertex in self.get_vertex()])

    def set_coordinates(self, coordinates: np.ndarray):
        self.setPoints(coordinates)

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


class RectangularRoi(Selector, RectROI):

    def __init__(self, *args, **kwargs):
        super().__init__([0, 0], [10, 10], *args, **kwargs)

    def get_header(self):
        return ['x', 'y']

    def get_coordinates(self) -> np.ndarray:
        """Returns bottom/left and top/right positions of the Rectangular ROI"""
        coordinates = [[self.pos().x(), self.pos().y()],
                       [self.pos().x() + self.size().x(), self.pos().y() + self.size().y()]]
        return np.array(coordinates)

    def set_coordinates(self, coordinates: np.ndarray):
        if len(coordinates) != 0:
            self.setPos(coordinates[0, :], finish=False)
            self.setSize(coordinates[1, :] - coordinates[0, :], finish=False)


class LinearRegionItem(Selector, LinearRegionItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_header(self):
        return ['x']

    def get_coordinates(self) -> np.ndarray:
        """Returns left and right positions of the Linear Region"""
        coordinates = [self.getRegion()]
        return np.array(coordinates).T

    def set_coordinates(self, coordinates: np.ndarray):
        self.setRegion(coordinates[:, 0])


class SelectorWrapper(Selector):
    """Wrapper around real implementation of Selector objects but having the same interface

    Used to be emitted with only one signature for all type of Selector
    """
    def __init__(self, selector: Selector):
        self._selector: Selector = selector

    def __call__(self, *args, **kwargs):
        return self._selector

    def get_header(self):
        return self._selector.get_header()

    def get_coordinates(self):
        self._selector.get_coordinates()

    def set_coordinates(self, coordinates: np.ndarray):
        self._selector.set_coordinates(coordinates)


class TableModel(gutils.TableModel):
    """Table Model for the Model/View Qt framework dedicated to the Tabular scan mode"""
    def __init__(self, data, header_names=None, **kwargs):
        if header_names is None:
            if 'header' in kwargs:  # when saved as XML the header will be saved and restored here
                header_names = [h for h in kwargs['header']]
                kwargs.pop('header')
            else:
                raise Exception('Invalid header')

        header = [name for name in header_names]
        editable = [True for _ in header_names]
        super().__init__(data, header, editable=editable, **kwargs)

    def data_as_ndarray(self):
        return np.array(self.raw_data)

    def __len__(self):
        return len(self._data)

    def add_data(self, row, data=None):
        if data is not None:
            self.insert_data(row, [float(d) for d in data])
        else:
            self.insert_data(row, [0. for name in self.header])

    def remove_data(self, row):
        self.remove_row(row)

    def __repr__(self):
        return f'{self.__class__.__name__} from module {self.__class__.__module__}'

    def validate_data(self, row, col, value):
        return True


class ScanSelector(ParameterManager, QObject):
    """Allows selection of a given 2D viewer to get scan info

    respectively scan2D or scan Tabular from respectively a rectangular ROI or a polyline

    Parameters
    ----------
    viewer_items: dict
        where the keys are the titles of the sources while the values are dict with keys
        * viewers: list of plotitems
        * names: list of viewer titles

    selector_type: str
        either 'PolyLines' corresponding to a polyline ROI or 'Rectangle' for a rect Roi
    positions: list
        a sequence of 2 floats sequence [(x1,y1),(x2,y2),(x3,y3),...]

    """
    scan_select_signal = Signal(SelectorWrapper)

    params = [
        {'title': 'Scan options', 'name': 'scan_options', 'type': 'group', 'children': [
            {'title': 'Sources:', 'name': 'sources', 'type': 'list', },
            {'title': 'Viewers:', 'name': 'viewers', 'type': 'list', },
            {'title': 'Selector type:', 'name': 'selector_type', 'type': 'list', 'limits': SelectorType.names()},
        ]},
        # {'title': 'Scan Area', 'name': 'scan_area', 'type': 'group', 'children': [
        #     {'title': 'ROI select:', 'name': 'ROIselect', 'type': 'group', 'visible': True, 'children': [
        #         {'title': 'x0:', 'name': 'x0', 'type': 'float', 'value': 0,},
        #         {'title': 'y0:', 'name': 'y0', 'type': 'float', 'value': 0,},
        #         {'title': 'width:', 'name': 'width', 'type': 'float', 'value': 10, 'min': 0.00001},
        #         {'title': 'height:', 'name': 'height', 'type': 'float', 'value': 10, 'min': 0.00001},
        #     ]},
        {'title': 'Coordinates:', 'name': 'coordinates', 'type': 'table_view', 'visible': True,
         'delegate': gutils.SpinBoxDelegate,},
        # ]},
    ]

    def __init__(self, viewer_items=None, selector_type='ROI2D', positions: List = None):
        QObject.__init__(self)
        ParameterManager.__init__(self, 'selector_settings')

        self.table_model: TableModel = None
        self.table_view: TableViewCustom = None

        if viewer_items is None:
            viewer_items = dict([])

        self._viewers_items = viewer_items
        self.sources_names = list(viewer_items.keys())
        if len(viewer_items) != 0:
            self.scan_selector_source = viewer_items[self.sources_names[0]]['viewers'][0]
        else:
            self.scan_selector_source = None
        self.selector: Selector = None

        self.setupUI()

        selector_type = enum_checker(SelectorType, selector_type)
        self.settings.child('scan_options', 'selector_type').setValue(selector_type.name)

        self.remove_scan_selector()
        if self.scan_selector_source is not None:
            if len(viewer_items[self.sources_names[0]]['viewers']) == 1:
                self.settings.child('scan_options', 'viewers').hide()
        else:
            self.settings.child('scan_options', 'viewers').hide()
        self.update_scan_area_type()

        if positions is not None:
            self.selector.set_coordinates(positions)


    def update_model(self, init_data=None):
        if init_data is None:
            init_data = [[0. for _ in self.selector.get_header()]]

        self.table_model = TableModel(init_data, self.selector.get_header())
        self.table_view = putils.get_widget_from_tree(self.settings_tree, TableViewCustom)[0]
        self.settings.child('coordinates').setValue(self.table_model)
        self.update_table_view()

    def update_model_data(self, data: np.ndarray):
        self.table_model.set_data_all(data)

    def update_table_view(self):
        self.table_view.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.table_view.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        styledItemDelegate = QtWidgets.QStyledItemDelegate()
        styledItemDelegate.setItemEditorFactory(gutils.SpinBoxDelegate())
        self.table_view.setItemDelegate(styledItemDelegate)

        self.table_view.setDragEnabled(False)
        self.table_view.setDropIndicatorShown(False)
        self.table_view.setAcceptDrops(False)
        self.table_view.viewport().setAcceptDrops(False)
        self.table_view.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.table_view.setDragDropMode(QtWidgets.QTableView.InternalMove)
        self.table_view.setDragDropOverwriteMode(False)

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
        self.show_selector(visible)
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

        if param.name() == 'selector_type':
            self.remove_scan_selector()
            self.update_scan_area_type()
            #self.selector.sigRegionChangeFinished.emit(self.selector)

        if param.name() == 'coordinates':
            self.selector.set_coordinates(param.value().data_as_ndarray())

    def remove_scan_selector(self):
        if self.scan_selector_source is not None:
            try:
                self.scan_selector_source.image_widget.plotitem.removeItem(self.selector)
            except Exception as e:
                logger.exception(str(e))
                pass

    def update_scan_area_type(self):
        self.remove_scan_selector()
        mod = importlib.import_module('.scan_selector', 'pymodaq.utils.plotting')
        self.selector = getattr(mod, SelectorType[self.settings['scan_options', 'selector_type']].value)()

        if self.scan_selector_source is not None and self.selector is not None:
            self.selector.sigRegionChangeFinished.connect(self.update_scan)
            self.scan_selector_source.image_widget.plotitem.addItem(self.selector)
            self.show_selector()
            self.update_model(self.selector.get_coordinates())
            # self.selector.sigRegionChangeFinished.emit(self.selector)

    def show_selector(self, visible=True):
        self.selector.setVisible(visible)

    def update_scan(self, roi):
        if self.scan_selector_source is not None:
            self.update_model_data(self.selector.get_coordinates())
            self.scan_select_signal.emit(SelectorWrapper(self.selector))


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

    selector = ScanSelector(items, scan_type='PolyLines', positions=[(10, -10), (4, 4), (80, 50)])

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

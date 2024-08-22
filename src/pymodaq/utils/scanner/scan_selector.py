from abc import ABC, abstractmethod
from collections import OrderedDict
import importlib
import time
import sys
from typing import List, Dict

import numpy as np
from qtpy import QtWidgets, QtCore
from qtpy.QtCore import QObject, Slot, QThread, Signal

from pyqtgraph import ROI, RectROI, PolyLineROI, Point, LinearRegionItem

from pymodaq_utils.factory import ObjectFactory
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import utils

from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui import utils as gutils
from pymodaq_gui.utils import DockArea, Dock
from pymodaq_gui.plotting.utils.plot_utils import QVector
from pymodaq_gui.parameter.pymodaq_ptypes import TableViewCustom
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.plotting.data_viewers.viewer import ViewerBase


logger = set_logger(get_module_name(__file__))


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


class SelectorFactory(ObjectFactory):
    """Factory class registering and storing Selectors"""


@SelectorFactory.register('PolyLines')
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


@SelectorFactory.register('RectangularROI')
class RectangularRoi(Selector, RectROI):

    def __init__(self, *args, **kwargs):
        super().__init__([0, 0], [10, 10], *args, invertible=True, **kwargs)

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
            self.setSize(coordinates[1, :] - coordinates[0, :])


@SelectorFactory.register('LinearROI')
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

    Mandatory because signal can only be emitted with one signature and not with child classes
    Hence this single wrapper of all real implementation of Selector
    """
    def __init__(self, selector: Selector):
        self._selector: Selector = selector

    def __call__(self, *args, **kwargs):
        return self._selector

    @property
    def name(self):
        return self._selector.__class__

    def get_header(self):
        return self._selector.get_header()

    def get_coordinates(self):
        return self._selector.get_coordinates()

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


class SelectorItem:
    """An object storing a viewer to display selectors and a name to reference it

    If the name is not given, constructs one from a unique index
    """
    _index: int = 0

    def __init__(self, viewer: ViewerBase, name: str = None):
        self.viewer = viewer
        if name is None:
            name = f'{self.viewer.title}_{self._index:03d}'
        self.name = name

        SelectorItem._index += 1


selector_factory = SelectorFactory()


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
            {'title': 'Selector type:', 'name': 'selector_type', 'type': 'list',
             'limits': selector_factory.keys},
        ]},
        {'title': 'Coordinates:', 'name': 'coordinates', 'type': 'table_view', 'visible': True,
         'delegate': gutils.SpinBoxDelegate,},
        # ]},
    ]

    def __init__(self, viewer_items: List[SelectorItem] = None, positions: List = None):
        QObject.__init__(self)
        ParameterManager.__init__(self, 'selector_settings')

        self.table_model: TableModel = None
        self.table_view: TableViewCustom = None

        self.selector: Selector = None
        self.selector_source: ViewerBase = None

        self.update_selector_type()

        if viewer_items is None:
            viewer_items = []

        self.viewers_items = viewer_items
        self.sources_names = [item.name for item in viewer_items]
        if len(viewer_items) != 0:
            self.selector_source = viewer_items[0].viewer
        else:
            self.selector_source = None

        # self.remove_selector()
        # self.update_selector_type()

        if positions is not None:
            self.selector.set_coordinates(positions)

    @property
    def selector_type(self) -> str:
        return self.settings['scan_options', 'selector_type']

    @selector_type.setter
    def selector_type(self, selector_type: str):
        if selector_type not in selector_factory.keys:
            raise TypeError(f'{selector_type} is an unknown Selector Type')
        self.settings.child('scan_options', 'selector_type').setValue(selector_type)

    @property
    def source_name(self) -> str:
        return self.settings['scan_options', 'sources']

    @source_name.setter
    def source_name(self, source: str):
        if source in self.settings.child('scan_options', 'sources').opts['limits']:
            self.settings.child('scan_options', 'sources').setValue(source)

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
    def viewers_items(self, items: List[SelectorItem]):
        self._viewers_items = items
        self.sources_names = [item.name for item in items]
        self.selector_source = items[0].viewer
        self.settings.child('scan_options', 'sources').setOpts(limits=self.sources_names)

    def show(self, visible=True):
        self.show_selector(visible)
        if visible:
            self.widget.show()
        else:
            self.widget.hide()

    def hide(self):
        self.show(False)

    def value_changed(self, param):

        if param.name() == 'sources' and param.value() is not None:
            self.remove_selector()
            self.selector_source = \
                utils.find_objects_in_list_from_attr_name_val(
                    self.viewers_items, 'name', param.value(), return_first=True)[0].viewer
            self.update_selector_type()

        if param.name() == 'selector_type':
            self.update_selector_type()
            self.selector.sigRegionChangeFinished.emit(self.selector)

        if param.name() == 'coordinates':
            self.selector.set_coordinates(param.value().data_as_ndarray())

    def remove_selector(self):
        if self.selector_source is not None:
            try:
                self.selector_source.image_widget.plotitem.removeItem(self.selector)
            except Exception as e:
                logger.exception(str(e))
                pass

    def update_selector_type(self):
        self.remove_selector()
        mod = importlib.import_module('.scan_selector', 'pymodaq.utils.scanner')
        self.selector = selector_factory.create(self.settings['scan_options', 'selector_type'])

        if self.selector_source is not None and self.selector is not None:
            self.selector.sigRegionChangeFinished.connect(self.update_scan)
            self.selector_source.plotitem.addItem(self.selector)
            self.show_selector()
            self.update_model(self.selector.get_coordinates())

    def show_selector(self, visible=True):
        self.selector.setVisible(visible)

    def update_scan(self):
        if self.selector_source is not None:
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
    time.sleep(1)
    QtWidgets.QApplication.processEvents()

    items = [SelectorItem(viewer=navigator.viewer, name="Navigator")]
    for _viewer_dock, _viewer in zip(viewer.viewers_docks, viewer.viewers):
        items.append(SelectorItem(viewer=_viewer, name=_viewer_dock.title()))

    scan_selector = ScanSelector(viewer_items=items)
    scan_selector.settings_tree.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    # main_fake_scan()
    main_navigator()

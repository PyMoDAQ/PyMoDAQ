from PyQt5.QtCore import QObject, pyqtSignal, QEvent, QBuffer, QIODevice, QLocale, Qt, QVariant, QModelIndex
from PyQt5.QtWidgets import QAction
from PyQt5 import QtGui, QtWidgets, QtCore
import numpy as np
from pathlib import Path
from pyqtgraph.dockarea.DockArea import DockArea, TempAreaWindow, Dock

from pyqtgraph.parametertree import Parameter, ParameterTree
import datetime
from pymodaq.daq_utils import daq_utils as utils
import toml

config = utils.load_config()

logger = utils.set_logger(utils.get_module_name(__file__))

dashboard_submodules_params = [
    {'title': 'Save 2D datas and above:', 'name': 'save_2D', 'type': 'bool', 'value': True},
    {'title': 'Save raw datas only:', 'name': 'save_raw_only', 'type': 'bool', 'value': True, 'tooltip':
        'if True, will not save extracted ROIs used to do live plotting, only raw datas will be saved'},
    {'title': 'Do Save:', 'name': 'do_save', 'type': 'bool', 'default': False, 'value': False},
    {'title': 'N saved:', 'name': 'N_saved', 'type': 'int', 'default': 0, 'value': 0, 'visible': False},
]


class QAction(QAction):
    """
    QAction subclass to miicmic signals as pushbuttons. Done to be sure of backcompatibility when I moved from
    pushbuttons to QAction
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.click = self.trigger
        self.clicked = self.triggered

class QSpinBox_ro(QtWidgets.QSpinBox):
    def __init__(self, **kwargs):
        super(QtWidgets.QSpinBox, self).__init__()
        self.setMaximum(100000)
        self.setReadOnly(True)
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)


def clickable(widget):
    class Filter(QObject):
        clicked = pyqtSignal()

        def eventFilter(self, obj, event):
            if obj == widget:
                if event.type() == QEvent.MouseButtonRelease:
                    if obj.rect().contains(event.pos()):
                        self.clicked.emit()
                        # The developer can opt for .emit(obj) to get the object within the slot.
                        return True
            return False

    filter = Filter(widget)
    widget.installEventFilter(filter)
    return filter.clicked


def h5tree_to_QTree(base_node, base_tree_elt=None, pixmap_items=[]):
    """
        | Convert a loaded h5 file to a QTreeWidgetItem element structure containing two columns.
        | The first is the name of the h5 current node, the second is the path of the node in the h5 structure.
        |
        | Recursive function discreasing on base_node.

        ==================   ======================================== ===============================
        **Parameters**        **Type**                                 **Description**

          *h5file*            instance class File from tables module   loaded h5 file

          *base_node*         pytables h5 node                         parent node

          *base_tree_elt*     QTreeWidgetItem                          parent QTreeWidgetItem element
        ==================   ======================================== ===============================

        Returns
        -------
        QTreeWidgetItem
            h5 structure copy converted into QtreeWidgetItem structure.

        See Also
        --------
        h5tree_to_QTree

    """

    if base_tree_elt is None:
        base_tree_elt = QtWidgets.QTreeWidgetItem([base_node.name, "", base_node.path])
    for node_name, node in base_node.children().items():
        child = QtWidgets.QTreeWidgetItem([node_name, "", node.path])
        if 'pixmap' in node.attrs.attrs_name:
            pixmap_items.append(dict(node=node, item=child))
        klass = node.attrs['CLASS']
        if klass == 'GROUP':
            h5tree_to_QTree(node, child, pixmap_items)

        base_tree_elt.addChild(child)
    return base_tree_elt, pixmap_items


class ListPicker(QObject):

    def __init__(self, list_str):
        super(ListPicker, self).__init__()
        self.list = list_str

    def pick_dialog(self):
        self.dialog = QtWidgets.QDialog()
        self.dialog.setMinimumWidth(500)
        vlayout = QtWidgets.QVBoxLayout()

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.addItems(self.list)

        vlayout.addWidget(self.list_widget, 10)
        self.dialog.setLayout(vlayout)

        buttonBox = QtWidgets.QDialogButtonBox()
        buttonBox.addButton('Apply', buttonBox.AcceptRole)
        buttonBox.accepted.connect(self.dialog.accept)
        buttonBox.addButton('Cancel', buttonBox.RejectRole)
        buttonBox.rejected.connect(self.dialog.reject)

        vlayout.addWidget(buttonBox)
        self.dialog.setWindowTitle('Select an entry in the list')

        res = self.dialog.show()

        pass
        if res == self.dialog.Accepted:
            # save managers parameters in a xml file
            return [self.list_widget.currentIndex(), self.list_widget.currentItem().text()]
        else:
            return [-1, ""]


def select_file(start_path=config['data_saving']['h5file']['save_path'], save=True, ext=None):
    """Save or open a file with Qt5 file dialog, to be used within an Qt5 loop.

    Usage::

        from pymodaq.daq_utils.daq_utils import select_file
        select_file(start_path="C:\\test.h5",save=True,ext='h5')

    =============== ======================================= ===========================================================================
    **Parameters**     **Type**                              **Description**

    *start_path*       Path object or str or None, optional  the path Qt5 will open in te dialog
    *save*             bool, optional                        * if True, a savefile dialog will open in order to set a savefilename
                                                             * if False, a openfile dialog will open in order to open an existing file
    *ext*              str, optional                         the extension of the file to be saved or opened
    =============== ======================================= ===========================================================================

    Returns
    -------
    Path object
        the Path object pointing to the file

    Examples
    --------



    """
    if ext is None:
        ext = '*'
    if not save:
        if not isinstance(ext, list):
            ext = [ext]

        filter = "Data files ("
        for ext_tmp in ext:
            filter += '*.' + ext_tmp + " "
        filter += ")"
    if start_path is not None:
        if not isinstance(start_path, str):
            start_path = str(start_path)
    if save:
        fname = QtWidgets.QFileDialog.getSaveFileName(None, 'Enter a .' + ext + ' file name', start_path,
                                                      ext + " file (*." + ext + ")")
    else:
        fname = QtWidgets.QFileDialog.getOpenFileName(None, 'Select a file name', start_path, filter)

    fname = fname[0]
    if fname != '':  # execute if the user didn't cancel the file selection
        fname = Path(fname)
        if save:
            parent = fname.parent
            filename = fname.stem
            fname = parent.joinpath(filename + "." + ext)  # forcing the right extension on the filename
    return fname  # fname is a Path object


class Dock(Dock):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setOrientation(self, o='auto', force=False):
        """
        Sets the orientation of the title bar for this Dock.
        Must be one of 'auto', 'horizontal', or 'vertical'.
        By default ('auto'), the orientation is determined
        based on the aspect ratio of the Dock.
        """
        if self.container() is not None:  # patch here for when Dock is closed and when the QApplication
            # event loop is processed
            if o == 'auto' and self.autoOrient:
                if self.container().type() == 'tab':
                    o = 'horizontal'
                elif self.width() > self.height() * 1.5:
                    o = 'vertical'
                else:
                    o = 'horizontal'
            if force or self.orientation != o:
                self.orientation = o
                self.label.setOrientation(o)
                self.updateStyle()

class DockArea(DockArea, QObject):
    """
    Custom Dockarea class subclassing from the standard DockArea class and QObject so it can emit a signal when docks
    are moved around (one subclassed method: moveDock)
    See Also
    --------
    pyqtgraph.dockarea
    """
    dock_signal = pyqtSignal()

    def __init__(self, parent=None, temporary=False, home=None):
        super(DockArea, self).__init__(parent, temporary, home)

    def moveDock(self, dock, position, neighbor):
        """
        Move an existing Dock to a new location.
        """
        # Moving to the edge of a tabbed dock causes a drop outside the tab box
        if position in ['left', 'right', 'top',
                        'bottom'] and neighbor is not None and neighbor.container() is not None and neighbor.container().type() == 'tab':
            neighbor = neighbor.container()
        self.addDock(dock, position, neighbor)
        self.dock_signal.emit()

    def addTempArea(self):
        if self.home is None:
            area = DockArea(temporary=True, home=self)
            self.tempAreas.append(area)
            win = TempAreaWindow(area)
            area.win = win
            win.show()
        else:
            area = self.home.addTempArea()
        # print "added temp area", area, area.window()
        return area


def set_enable_recursive(children, enable=False):
    """Apply the enable state on all children widgets, do it recursively

    Parameters
    ----------
    children: (list) elements children ofa pyqt5 element
    enable: (bool) set enabled state (True) of all children widgets
    """
    for child in children:
        if not children:
            return
        elif isinstance(child, QtWidgets.QSpinBox) or isinstance(child, QtWidgets.QComboBox) or \
                isinstance(child, QtWidgets.QPushButton) or isinstance(child, QtWidgets.QListWidget):
            child.setEnabled(enable)
        else:
            set_enable_recursive(child.children(), enable)


def widget_to_png_to_bytes(widget, keep_aspect=True, width=200, height=100):
    """
    Renders the widget content in a png format as a bytes string
    Parameters
    ----------
    widget: (QWidget) the widget to render
    keep_aspect: (bool) if True use width and the widget aspect ratio to calculate the height
                        if False use set values of width and height to produce the png
    width: (int) the rendered width of the png
    height: (int) the rendered width of the png

    Returns
    -------
    binary string

    """
    png = widget.grab().toImage()
    wwidth = widget.width()
    wheight = widget.height()
    if keep_aspect:
        height = width * wheight / wwidth

    png = png.scaled(width, height, QtCore.Qt.KeepAspectRatio)
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QIODevice.WriteOnly)
    png.save(buffer, "png")
    return buffer.data().data()


def pngbinary2Qlabel(databinary):
    buff = QBuffer()
    buff.open(QIODevice.WriteOnly)
    buff.write(databinary)
    dat = buff.data()
    pixmap = QtGui.QPixmap()
    pixmap.loadFromData(dat, 'PNG')
    label = QtWidgets.QLabel()
    label.setPixmap(pixmap)
    return label


class TableView(QtWidgets.QTableView):
    def __init__(self, *args, **kwargs):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super().__init__(*args, **kwargs)
        self.setupview()

    def setupview(self):
        self.setStyle(MyStyle())

        self.verticalHeader().hide()
        self.horizontalHeader().hide()
        self.horizontalHeader().setStretchLastSection(True)

        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.setSelectionMode(QtWidgets.QTableView.SingleSelection)

        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setDragDropMode(QtWidgets.QTableView.InternalMove)
        self.setDragDropOverwriteMode(False)


class MyStyle(QtWidgets.QProxyStyle):

    def drawPrimitive(self, element, option, painter, widget=None):
        """
        Draw a line across the entire row rather than just the column
        we're hovering over.  This may not always work depending on global
        style - for instance I think it won't work on OSX.
        """
        if element == self.PE_IndicatorItemViewItemDrop and not option.rect.isNull():
            option_new = QtWidgets.QStyleOption(option)
            option_new.rect.setLeft(0)
            if widget:
                option_new.rect.setRight(widget.width())
            option = option_new
        super().drawPrimitive(element, option, painter, widget)


class TableModel(QtCore.QAbstractTableModel):

    def __init__(self, data, header, editable=True, parent=None):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super().__init__(parent)
        if isinstance(data, np.ndarray):
            data_tot = []
            for dat in data:
                data_tot.append([float(d) for d in dat])
            data = data_tot
        self._data = data  # stored data as a list of list
        self.data_tmp = None
        self.header = header
        if not isinstance(editable, list):
            self.editable = [editable for h in header]
        else:
            self.editable = editable

    def rowCount(self, parent):
        return len(self._data)

    def columnCount(self, parent):
        if self._data != []:
            return len(self._data[0])
        else:
            return 0

    def get_data(self, row, col):
        return self._data[row][col]

    def get_data_all(self):
        return self._data

    def clear(self):
        while self.rowCount(self.index(-1, -1)) > 0:
            self.remove_row(0)

    def set_data_all(self, data):
        self.clear()
        for row in data:
            self.insert_data(self.rowCount(self.index(-1, -1)), [float(d) for d in row])

    def data(self, index, role):
        if index.isValid():
            if role == Qt.DisplayRole or role == Qt.EditRole:
                dat = self._data[index.row()][index.column()]
                return dat
        return QVariant()

    # def setHeaderData(self, section, orientation, value):
    #     if section == 2 and orientation == Qt.Horizontal:
    #         names = self._data.columns
    #         self._data = self._data.rename(columns={names[section]: value})
    #         self.headerDataChanged.emit(orientation, 0, section)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if section > len(self.header):
                    return QVariant()
                else:
                    return self.header[section]
            else:
                return section
        else:
            return QVariant()

    def flags(self, index):

        f = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled

        if self.editable[index.column()]:
            f |= Qt.ItemIsEditable

        if not index.isValid():
            f |= Qt.ItemIsDropEnabled
        return f

    def supportedDropActions(self):
        return Qt.MoveAction | Qt.CopyAction

    def validate_data(self, row, col, value):
        """
        to be subclassed in order to validate ranges of values for the cell defined by index
        Parameters
        ----------
        index: (QModelIndex)
        value: (str or float or int or ...)


        Returns
        -------
        bool: True if value is valid for the given row and col
        """
        return True

    def setData(self, index, value, role):
        if index.isValid():
            if role == Qt.EditRole:
                if self.validate_data(index.row(), index.column(), value):
                    self._data[index.row()][index.column()] = value
                    self.dataChanged.emit(index, index, [role])
                    return True

                else:
                    return False
        return False

    def dropMimeData(self, data, action, row, column, parent):
        if row == -1:
            row = self.rowCount(parent)

        self.data_tmp = [dat[2] for dat in utils.decode_data(data.data("application/x-qabstractitemmodeldatalist"))]
        self.insertRows(row, 1, parent)
        return True

    def insert_data(self, row, data):
        self.data_tmp = data
        self.insertRows(row, 1, self.index(-1, -1))

    def insertRows(self, row, count, parent):
        self.beginInsertRows(QtCore.QModelIndex(), row, row + count - 1)
        for ind in range(count):
            self._data.insert(row + ind, self.data_tmp)
        self.endInsertRows()
        return True

    def remove_row(self, row):
        self.removeRows(row, 1, self.index(-1, -1))

    def removeRows(self, row, count, parent):
        self.beginRemoveRows(QModelIndex(), row, row + count - 1)
        for ind in range(count):
            self._data.pop(row + ind)
        self.endRemoveRows()
        return True


class SpinBoxDelegate(QtWidgets.QItemEditorFactory):
    # http://doc.qt.io/qt-5/qstyleditemdelegate.html#subclassing-qstyleditemdelegate
    # It is possible for a custom delegate to provide editors without the use of an editor item factory.
    # In this case, the following virtual functions must be reimplemented:
    """
    TO implement custom widget editor for cells in a tableview
    """

    def __init__(self):
        super().__init__()

    def createEditor(self, userType, parent):
        if userType == QVariant.Double:
            doubleSpinBox = QtWidgets.QDoubleSpinBox(parent)
            doubleSpinBox.setDecimals(4)
            doubleSpinBox.setMaximum(-10000000)
            doubleSpinBox.setMaximum(10000000)  # The default maximum value is 99.99.所以要设置一下
            return doubleSpinBox
        else:
            return super().createEditor(userType, parent)


class TreeFromToml(QObject):
    def __init__(self, conf_path=None):
        super().__init__()

        self.config_path = utils.get_set_local_dir().joinpath('config.toml')
        config = utils.load_config(self.config_path)

        params = [{'title': 'Config path', 'name': 'config_path', 'type': 'str', 'value': str(self.config_path),
                   'readonly': True}]
        params.extend(self.dict_to_param(config))

        self.settings = Parameter.create(title='settings', name='settings', type='group', children=params)
        self.settings_tree = ParameterTree()
        self.settings_tree.setParameters(self.settings, showTop=False)

    def show_dialog(self):

        self.dialog = QtWidgets.QDialog()
        self.dialog.setWindowTitle('Please enter new configuration values!')
        self.dialog.setLayout(QtWidgets.QVBoxLayout())
        buttonBox = QtWidgets.QDialogButtonBox(parent=self.dialog)

        buttonBox.addButton('Save', buttonBox.AcceptRole)
        buttonBox.accepted.connect(self.dialog.accept)
        buttonBox.addButton('Cancel', buttonBox.RejectRole)
        buttonBox.rejected.connect(self.dialog.reject)

        self.dialog.layout().addWidget(self.settings_tree)
        self.dialog.layout().addWidget(buttonBox)
        self.dialog.setWindowTitle('Configuration entries')
        res = self.dialog.exec()

        if res == self.dialog.Accepted:
            with open(self.config_path, 'w') as f:
                config = self.param_to_dict(self.settings)
                config.pop('config_path')
                toml.dump(config, f)

    @classmethod
    def param_to_dict(cls, param):
        config = dict()
        for child in param.children():
            if 'group' in child.opts['type']:
                config[child.name()] = cls.param_to_dict(child)
            else:
                if child.opts['type'] == 'datetime':
                    config[child.name()] = datetime.fromtimestamp(
                        child.value().toSecsSinceEpoch())  # convert QDateTime to python datetime
                elif child.opts['type'] == 'date':
                    qdt = QtCore.QDateTime()
                    qdt.setDate(child.value())
                    pdt = datetime.fromtimestamp(qdt.toSecsSinceEpoch())
                    config[child.name()] = pdt.date()
                elif child.opts['type'] == 'list':
                    config[child.name()] = child.opts['limits']
                else:
                    config[child.name()] = child.value()
        return config

    @classmethod
    def dict_to_param(cls, config):
        params = []
        for key in config:
            if isinstance(config[key], dict):
                params.append({'title': f'{key.capitalize()}:', 'name': key, 'type': 'group',
                               'children': cls.dict_to_param(config[key]),
                               'expanded': 'user' in key.lower() or 'general' in key.lower()})
            else:
                param = {'title': f'{key.capitalize()}:', 'name': key, 'value': config[key]}
                if isinstance(config[key], float):
                    param['type'] = 'float'
                elif isinstance(config[key], bool):  # placed before int because a bool is an instance of int
                    param['type'] = 'bool'
                elif isinstance(config[key], int):
                    param['type'] = 'int'
                elif isinstance(config[key], datetime.datetime):
                    param['type'] = 'datetime'
                elif isinstance(config[key], datetime.date):
                    param['type'] = 'date'
                elif isinstance(config[key], str):
                    param['type'] = 'str'
                elif isinstance(config[key], list):
                    param['type'] = 'list'
                    param['values'] = config[key]
                    param['value'] = config[key][0]
                    param['show_pb'] = True
                params.append(param)
        return params


def show_message(message="blabla", title="Error"):
    msgBox = QtWidgets.QMessageBox(parent=None)
    msgBox.setWindowTitle(title)
    msgBox.setText(message)
    ret = msgBox.exec()
    return ret


if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication([])
    # QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    # w = QtWidgets.QMainWindow()
    # table = TableView(w)
    # styledItemDelegate = QtWidgets.QStyledItemDelegate()
    # styledItemDelegate.setItemEditorFactory(SpinBoxDelegate())
    # table.setItemDelegate(styledItemDelegate)
    #
    # table.setModel(TableModel([[name, 0., 1., 0.1] for name in ['X_axis', 'Y_axis', 'theta_axis']],
    #                           header=['Actuator', 'Start', 'Stop', 'Step'],
    #                           editable=[False, True, True, True]))
    # w.setCentralWidget(table)
    # w.show()
    #

    c = TreeFromToml()
    c.show_dialog()
    sys.exit(app.exec_())

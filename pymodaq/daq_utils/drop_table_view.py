from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QVariant, Qt, QModelIndex, QLocale
import pandas as pd
from pymodaq.daq_utils.daq_utils import decode_data

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
    
    def __init__(self, data, header, editable=True, parent = None):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super().__init__(parent)
        self._data = data #stored data as a list of list
        self.header = header
        if not isinstance(editable, list):
            self.editable = [editable for h in header]
        else:
            self.editable = editable

    def rowCount(self, parent):
        return len(self._data)

    def columnCount(self, parent):
        return len(self._data[0])

    def get_data(self, row, col):
        return self._data[row][col]

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
                return self.header[section]
            else:
                return section
        else:
            return QtCore.QVariant()

    def flags(self, index):

        f = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled

        if self.editable[index.column()]:
            f|= Qt.ItemIsEditable

        if not index.isValid():
            f |= Qt.ItemIsDropEnabled
        return f

    def supportedDropActions(self):
        return Qt.MoveAction | Qt.CopyAction

    def validate_data(self, row, col, value):
        """
        to be subclassed in order to validate ranges of values
        Parameters
        ----------
        row
        col
        value

        Returns
        -------
        bool: True if value is valid for the given row and col
        """
        return True

    def setData(self, index, value, role):
        if index.isValid():
            if role == Qt.EditRole:
                if self.validate_data(index.row, index.column(), value):
                    if index.column() != 0:
                        self._data[index.row()][index.column()] = value
                        self.dataChanged.emit(index, index, [role])
                        return True
                    else:
                        return False
                else:
                    return False
        return False

    def dropMimeData(self, data, action, row, column, parent):
        if row == -1:
            row = self.rowCount(parent)

        self.data_tmp = [dat[2] for dat in decode_data(data.data("application/x-qabstractitemmodeldatalist"))]
        self.insertRows(row, 1, parent)
        return True


    def insertRows(self, row, count, parent):
        self.beginInsertRows(QtCore.QModelIndex(), row, row + count - 1)
        for ind in range(count):
            self._data.insert(row+ind,self.data_tmp)
        self.endInsertRows()
        return True


    def removeRows(self, row, count, parent):
        self.beginRemoveRows(QModelIndex(), row, row + count - 1)
        for ind in range(count):
            self._data.pop(row+ind)
        self.endRemoveRows()
        return True

class ItemEditorFactory(QtWidgets.QItemEditorFactory):  # http://doc.qt.io/qt-5/qstyleditemdelegate.html#subclassing-qstyleditemdelegate    It is possible for a custom delegate to provide editors without the use of an editor item factory. In this case, the following virtual functions must be reimplemented:
    """
    TO implement custom widget editor for cells in a tableview
    """
    def __init__(self):
        super().__init__()

    def createEditor(self, userType, parent):
        if userType == QVariant.Double:
            doubleSpinBox = QtWidgets.QDoubleSpinBox(parent)
            doubleSpinBox.setDecimals(4)
            doubleSpinBox.setMaximum(10000000)  # The default maximum value is 99.99.所以要设置一下
            return doubleSpinBox
        else:
            return super().createEditor(userType, parent)

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication([])
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    w = QtWidgets.QMainWindow()
    table = TableView(w)
    styledItemDelegate = QtWidgets.QStyledItemDelegate()
    styledItemDelegate.setItemEditorFactory(ItemEditorFactory())
    table.setItemDelegate(styledItemDelegate)

    table.setModel(TableModel([[name, 0., 1., 0.1] for name in ['X_axis', 'Y_axis', 'theta_axis']],
                              header=['Actuator', 'Start', 'Stop', 'Step'],
                              editable=[False, True, True, True]))
    w.setCentralWidget(table)
    w.show()
    sys.exit(app.exec_())





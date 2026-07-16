import sys
from qt_themes import get_theme

from qtpy import QtWidgets, QtCore, QtGui

from pymodaq_gui.qt_utils import mkQApp
from pymodaq_gui.qvariant import QVariant
from pymodaq_gui.utils.widgets.combo import ComboBox


class ComboModel(QtCore.QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self.highlighted_index: int = None

    def set_data(self, data: list[str]):
        self._data = data

    def set_highlighted_index(self, index: int):
        self.highlighted_index = index

    def rowCount(self, parent) -> int:
        return len(self._data)

    def data(self, index: QtCore.QModelIndex, role):
        if role == QtCore.Qt.DisplayRole:
            return self._data[index.row()]
        elif role == QtCore.Qt.BackgroundRole and index.row() == self.highlighted_index:
            return QtGui.QBrush(get_theme().green)
        elif role == QtCore.Qt.ForegroundRole and index.row() == self.highlighted_index:
            return QtGui.QBrush(QtGui.QColor(0, 0, 0))
        else:
            return QVariant()


class HighlightedComboBox(ComboBox):
    """ This Combo Box will highlight one of its item depending on the value of
     the highlighted_index set with the set_highlighted_index method

     The highlighted color can be set using the activated_color property (QColor)

     This highlighting is using both the Model/View and SetStyleSheet paradigm to allow this
     behaviour.
     """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModel(ComboModel(parent=self))
        self.currentIndexChanged.connect(self.set_style)

        self._activated_color = get_theme().green

    @property
    def activated_color(self):
        return self._activated_color

    @activated_color.setter
    def activated_color(self, value: QtGui.QColor):
        self._activated_color = value

    def style_color_from_qcolor(self, color: QtGui.QColor) -> str:
        return f'rgb({color.red()}, {color.green()}, {color.blue()})'

    def combo_model(self) -> ComboModel:
        return self.model()

    def addItems(self, items: list[str]):
        self.combo_model().set_data(items)
        self.setCurrentIndex(0)

    def set_highlighted_index(self, index: int):
        self.combo_model().set_highlighted_index(index)
        self.currentIndexChanged.emit(self.currentIndex())

    @property
    def highlighted_index(self) -> int:
        return self.combo_model().highlighted_index

    def set_style(self, index: int = None):
        if index is None:
            index = self.currentIndex()
        if self.highlighted_index == index:
            self.setStyleSheet(
                "QComboBox {"
                f"background-color: {self.style_color_from_qcolor(self._activated_color)};"
                f"color: black;"
                "}"
                "QComboBox QAbstractItemView {}")
        else:
            self.setStyleSheet("QComboBox {}"
                               "QComboBox QAbstractItemView {}")




if __name__ == "__main__":

    app = mkQApp('Combo')

    widget = QtWidgets.QWidget()
    widget.setLayout(QtWidgets.QHBoxLayout())

    spinbox = QtWidgets.QSpinBox()
    combobox = HighlightedComboBox()
    combobox.addItems(['A', 'B', 'C', 'D'])

    spinbox.setMinimum(0)
    spinbox.valueChanged.connect(combobox.set_highlighted_index)

    widget.layout().addWidget(spinbox)
    widget.layout().addWidget(combobox)
    widget.show()

    app.exec()
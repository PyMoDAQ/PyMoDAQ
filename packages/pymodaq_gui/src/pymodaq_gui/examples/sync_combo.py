import sys

from qtpy import QtWidgets, QtCore

from pymodaq_gui.utils.widget_sync import WidgetSync


class ComboBox(QtWidgets.QComboBox):
    items_changed = QtCore.Signal(list)
    def __init__(self, parent=None):
        super().__init__(parent)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_items(self):
        return [self.itemText(ind) for ind in range(self.count())]

    def set_items(self, item_list: list[str]):
        self.clear()
        self.addItems(item_list)
        self.items_changed.emit(item_list)

    items = QtCore.Property(list, get_items, set_items, notify=items_changed)



class MyWidget(QtWidgets.QWidget):
    N= 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QtWidgets.QHBoxLayout())

        self.combos: list[ComboBox] = []

        for ind in range(self.N):
            self.combos.append(ComboBox())
            self.layout().addWidget(self.combos[ind])

        self.clear = QtWidgets.QPushButton('Clear')
        self.add = QtWidgets.QPushButton('Add')

        self.index_sb = QtWidgets.QSpinBox()
        self.clear.clicked.connect(self.clear_index)
        self.add.clicked.connect(self.set_items)

        vlayout = QtWidgets.QVBoxLayout()
        self.layout().addLayout(vlayout)
        vlayout.addWidget(self.index_sb)
        vlayout.addWidget(self.clear)
        vlayout.addWidget(self.add)

        self.sync_text = WidgetSync.for_combobox(self.combos[0], initial=None, use_text=True)
        self.sync_items = WidgetSync.for_property(self.combos[0], 'items', initial=None)

        for ind in range(1, self.N):
            self.sync_text.add(self.combos[ind])
            self.sync_items.add(self.combos[ind])

    def clear_index(self, index: int = None):
        if index is None:
            index = self.index_sb.value()
        self.combos[index].items = []

    def set_items(self, list_elt: list[str] = None, index: int = None):
        if index is None:
            index = self.index_sb.value()
        if list_elt is None or list_elt is False:
            list_elt = [f'elt {elt:03.0f}' for elt in range(index+1)]
        self.combos[index].items = list_elt


if __name__ == '__main__':
    from pymodaq_gui.utils.utils import mkQApp

    app = mkQApp('Combos')

    list_elt = ['elt1','elt2','elt3']

    widget = MyWidget()
    widget.show()
    widget.set_items(list_elt)

    sys.exit(app.exec_())
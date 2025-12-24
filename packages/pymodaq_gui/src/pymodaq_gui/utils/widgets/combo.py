from qtpy import QtWidgets, QtCore

class ComboBox(QtWidgets.QComboBox):

    items_changed = QtCore.Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

    def get_items(self) -> list[str]:
        return [self.itemText(index) for index in range(self.count())]

    def set_items(self, items: list[str]):
        self.clear()
        self.addItems(items[:])
        self.items_changed.emit(items[:])

    all_items = QtCore.Property(list, get_items, set_items, notify=items_changed)
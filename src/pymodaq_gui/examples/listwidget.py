from qtpy import QtWidgets, QtCore
from pymodaq_gui.parameter.pymodaq_ptypes.itemselect import ItemSelect


class MyListWidget(QtWidgets.QListWidget):

    def sizeHint(self):
        return QtCore.QSize(super().sizeHint().width(), 25 * self.count())


def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)

    lw = MyListWidget()
    lw.setResizeMode(QtWidgets.QListView.Adjust)
    for ind in range(10):
        item = QtWidgets.QListWidgetItem(f'item{ind}')
        lw.addItem(item)
        #lw.updateGeometry()

    lw.show()

    itemsel = ItemSelect()
    itemsel.set_value(dict(all_items=[f'item{ind}' for ind in range(23)],
                           selected=[f'item{ind}' for ind in range(23)]))
    itemsel.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

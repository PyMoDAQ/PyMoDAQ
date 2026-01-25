from pytest import fixture
from pytestqt import qtbot
from qtpy import QtWidgets, QtCore

from pymodaq_gui.utils.widgets.tree_layout import TreeLayout

DATA = [dict(name='papa', contents=[
    dict(name='fiston', contents=[dict(name='subfiston', contents='baby', filename='Cest pas sorcier')]),
    dict(name='fiston1', contents=[dict(name='subfiston', contents='baby', filename='Cest pas malin')]),
    dict(name='fiston2', contents=[dict(name='subfiston', contents='baby', filename='Cest pas normal')])]),
        dict(name='maman', contents=[dict(name='fistone', contents=[dict(name='subfistone', contents='baby')])])]

@fixture
def tree(qtbot):
    widget = QtWidgets.QWidget()
    tree = TreeLayout(widget, col_counts=2, labels=["Material", "File"])
    qtbot.addWidget(widget)
    widget.show()

    yield tree
    widget.close()



def test_populate_tree(tree):
    tree.populate_tree(DATA)


def test_add_action(tree):
    detector_action = QtWidgets.QAction("Grab from camera", None)
    tree.tree.addAction(detector_action)

def test_clicked(tree):
    tree.populate_tree(DATA)

    def print_item(item: QtWidgets.QTreeWidgetItem):
        print(item.text(0))

    tree.item_clicked_sig.connect(print_item)
    tree.item_double_clicked_sig.connect(print_item)

    ROW = 1
    COL = 1

    tree.tree.itemClicked.emit(tree.tree.itemFromIndex(tree.tree.model().index(ROW,COL)), COL)
    tree.tree.itemDoubleClicked.emit(tree.tree.itemFromIndex(tree.tree.model().index(ROW, COL)), COL)






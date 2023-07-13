from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import QObject, Signal, QLocale
import sys


class TreeLayout(QObject):
    """
    qtpy class object based on QtreeWidget
    The function populate_tree has to be used in order to populate the tree with structure as nested lists of dicts

    """
    status_sig = Signal(str)
    item_clicked_sig = Signal(object)
    item_double_clicked_sig = Signal(object)
    
    def __init__(self, parent=None, col_counts=1, labels=None):
        
        super().__init__()

        if parent is None:
            parent = QtWidgets.QWidget()
        self.parent = parent

        self.setupUi()

        self.tree.setColumnCount(col_counts)
        if labels is not None:
            self.tree.setHeaderLabels(labels)

        self.open_tree_pb.clicked.connect(self.expand_all)
        self.close_tree_pb.clicked.connect(self.collapse_all)
        self.open_tree_selected_pb.clicked.connect(self.open_tree_selection)
        
        self.tree.itemClicked.connect(self.item_clicked_sig.emit)
        self.tree.itemDoubleClicked.connect(self.item_double_clicked_sig.emit)

    def _current_text(self, col_index: int = 2):
        return self.tree.currentItem().text(col_index)

    def current_node_path(self):
        return self._current_text(2)

    def expand_all(self):
        self.tree.expandAll()

    def collapse_all(self):
        self.tree.collapseAll()

    @property
    def treewidget(self):
        return self.tree

    def setupUi(self):
        vlayout = QtWidgets.QVBoxLayout()
        hlayout = QtWidgets.QHBoxLayout()

        self.tree = CustomTree()
        vlayout.addWidget(self.tree)

        iconopen = QtGui.QIcon()
        iconopen.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/tree.png"), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
        self.open_tree_pb = QtWidgets.QPushButton('Open Tree')
        self.open_tree_pb.setIcon(iconopen)

        iconopensel = QtGui.QIcon()
        iconopensel.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/tree.png"), QtGui.QIcon.Normal,
                              QtGui.QIcon.Off)
        self.open_tree_selected_pb = QtWidgets.QPushButton('Open Selected')
        self.open_tree_selected_pb.setIcon(iconopensel)

        iconclose = QtGui.QIcon()
        iconclose.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/CollapseAll.png"), QtGui.QIcon.Normal,
                            QtGui.QIcon.Off)
        self.close_tree_pb = QtWidgets.QPushButton('Close Tree')
        self.close_tree_pb.setIcon(iconclose)

        hlayout.addWidget(self.open_tree_pb)
        hlayout.addWidget(self.open_tree_selected_pb)
        hlayout.addWidget(self.close_tree_pb)

        vlayout.addLayout(hlayout)

        self.parent.setLayout(vlayout)

    def open_tree_selection(self):
        self.tree_open_children(self.tree.selectedIndexes()[0])

    def tree_open_children(self, item_index):
        try:
            if not (item_index.isValid()):
                return

            self.tree.expand(item_index)
        except Exception as e:
            self.status_sig.emit(str(e))

    def tree_open_parents(self, item_index):
        try:
            if not (item_index.isValid()):
                return
            flag = True
            empty = QtCore.QModelIndex()
            parent = item_index
            while flag:
                parent = parent.parent()
                if parent != empty:
                    self.tree.expand(parent)
                else:
                    flag = False
                    break
        except Exception as e:
            self.status_sig.emit(str(e))

    def populate_tree(self, data_dict):
        try:
            parents = []
            for data in data_dict:
                str_list = [str(data['name'])]
                if 'filename' in data.keys():
                    str_list.append(data['filename'])
                if 'info' in data.keys():
                    str_list.append(data['info'])
                parent = QtWidgets.QTreeWidgetItem(str_list)
                Items = self.populate_sub_tree(data['contents'])
                parent.addChildren(Items)
                parents.append(parent)

            self.tree.addTopLevelItems(parents)
        except Exception as e:
            self.status_sig.emit(str(e))

    def populate_sub_tree(self, datas):
        try:
            parents = []
            for data in datas:
                str_list = [str(data['name'])]
                if 'filename' in data.keys():
                    str_list.append(data['filename'])
                if 'info' in data.keys():
                    str_list.append(data['info'])
                parent = QtWidgets.QTreeWidgetItem(str_list)
                if 'contents' in data.keys():
                    if type(data['contents']) == list:
                        Items = self.populate_sub_tree(data['contents'])
                        parent.addChildren(Items)
                parents.append(parent)
            return parents
        except Exception as e:
            self.status_sig.emit(str(e))
            return parents


class CustomTree(QtWidgets.QTreeWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)


if __name__ == '__main__':


    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    prog = TreeLayout(Form, col_counts=2, labels=["Material", "File"])

    # example of actions to add to the tree widget in order to show a context menu
    detector_action = QtWidgets.QAction("Grab from camera", None)
    prog.tree.addAction(detector_action)
    ########################

    Form.show()
    data = [dict(name='papa', contents=[
        dict(name='fiston', contents=[dict(name='subfiston', contents='baby', filename='Cest pas sorcier')]),
        dict(name='fiston1', contents=[dict(name='subfiston', contents='baby', filename='Cest pas malin')]),
        dict(name='fiston2', contents=[dict(name='subfiston', contents='baby', filename='Cest pas normal')])]),
        dict(name='maman', contents=[dict(name='fistone', contents=[dict(name='subfistone', contents='baby')])])]
    prog.populate_tree(data)
    # filename='C:\\Data\\2019\\20190220\\Dataset_20190220_004\\Dataset_20190220_004.h5'
    # import tables
    # h5_file = tables.open_file(filename, mode = "a")
    # for node in h5_file.walk_nodes():
    #     print(node)
    # base_node = h5_file.root
    # base_tree_item, pixmap_items = h5tree_to_QTree(h5_file, base_node)
    # prog.ui.Tree.addTopLevelItem(base_tree_item)
    sys.exit(app.exec_())

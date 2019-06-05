from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, pyqtSignal, QLocale
import sys





class Tree_layout(QObject):
    """
    PyQt5 class object based on QtreeWidget
    The function populate_Tree has to be used in order to populate the tree with structure as nested lists of dicts

    """
    status_sig=pyqtSignal(str)

    def __init__(self,parent = None,col_counts=1,labels=None):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(Tree_layout,self).__init__()

        if parent is None:
            parent = QtWidgets.QWidget()
        self.parent = parent

        self.setupUi()

        self.ui.Tree.setColumnCount(col_counts)
        if labels is not None:
            self.ui.Tree.setHeaderLabels(labels)

        self.ui.Open_Tree.clicked.connect(self.ui.Tree.expandAll)
        self.ui.Close_Tree.clicked.connect(self.ui.Tree.collapseAll)
        self.ui.Open_Tree_Selected.clicked.connect(self.open_Tree_selection)

    def setupUi(self):
        self.ui = QObject()

        vlayout = QtWidgets.QVBoxLayout()
        hlayout = QtWidgets.QHBoxLayout()

        self.ui.Tree = CustomTree()
        vlayout.addWidget(self.ui.Tree)

        iconopen = QtGui.QIcon()
        iconopen.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/tree.png"), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
        self.ui.Open_Tree = QtWidgets.QPushButton('Open Tree')
        self.ui.Open_Tree.setIcon(iconopen)

        iconopensel = QtGui.QIcon()
        iconopensel.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/tree.png"), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
        self.ui.Open_Tree_Selected = QtWidgets.QPushButton('Open Selected')
        self.ui.Open_Tree_Selected.setIcon(iconopensel)

        iconclose = QtGui.QIcon()
        iconclose.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/CollapseAll.png"), QtGui.QIcon.Normal,
                           QtGui.QIcon.Off)
        self.ui.Close_Tree = QtWidgets.QPushButton('Close Tree')
        self.ui.Close_Tree.setIcon(iconclose)

        hlayout.addWidget(self.ui.Open_Tree)
        hlayout.addWidget(self.ui.Open_Tree_Selected)
        hlayout.addWidget(self.ui.Close_Tree)

        vlayout.addLayout(hlayout)

        self.parent.setLayout(vlayout)

    def open_Tree_selection(self):
        self.Tree_open_children(self.ui.Tree.selectedIndexes()[0])


    
    def Tree_open_children(self,item_index):
        try:
            if not(item_index.isValid()):
                return

            self.ui.Tree.expand(item_index)
        except Exception as e:
            self.status_sig.emit(str(e))

    def Tree_open_parents(self,item_index):
        try:
            if not(item_index.isValid()):
                return
            flag=True
            empty=QtCore.QModelIndex()
            parent=item_index
            while flag:
                parent=parent.parent()
                if parent!=empty:
                    self.ui.Tree.expand(parent)
                else:
                    flag=False
                    break
        except Exception as e:
            self.status_sig.emit(str(e))


    def populate_Tree(self,data_dict):
        try:
            parents=[]
            for data in data_dict:
                str_list=[str(data['name'])]
                if 'filename' in data.keys():
                    str_list.append(data['filename'])
                if 'info' in data.keys():
                    str_list.append(data['info'])
                parent=QtWidgets.QTreeWidgetItem(str_list)
                Items=self.populate_sub_tree(data['contents'])
                parent.addChildren(Items)
                parents.append(parent)

            self.ui.Tree.addTopLevelItems(parents)
        except Exception as e:
            self.status_sig.emit(str(e))

    def populate_sub_tree(self,datas):
        try:
            parents=[]
            for data in datas:
                str_list=[str(data['name'])]
                if 'filename' in data.keys():
                    str_list.append(data['filename'])
                if 'info' in data.keys():
                    str_list.append(data['info'])
                parent = QtWidgets.QTreeWidgetItem(str_list)
                if 'contents' in data.keys():
                    if type(data['contents'])==list:
                        Items=self.populate_sub_tree(data['contents'])
                        parent.addChildren(Items)
                parents.append(parent)
            return parents
        except Exception as e:
            self.status_sig.emit(str(e))
            return parents

class CustomTree(QtWidgets.QTreeWidget):

    def __init__(self, parent = None):
        super(CustomTree, self).__init__(parent)
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)



if __name__ == '__main__':
    from pymodaq.daq_utils.daq_utils import h5tree_to_QTree
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    prog = Tree_layout(Form,col_counts=2,labels=["Material","File"])


    #example of actions to add to the tree widget in order to show a context menu
    detector_action = QtWidgets.QAction("Grab from camera", None)
    prog.ui.Tree.addAction(detector_action)
    ########################

    Form.show()
    data=[dict(name='papa',contents=[dict(name='fiston',contents=[dict(name='subfiston',contents='baby',filename='Cest pas sorcier')]),
                                     dict(name='fiston1',contents=[dict(name='subfiston',contents='baby',filename='Cest pas malin')]),
                                     dict(name='fiston2',contents=[dict(name='subfiston',contents='baby',filename='Cest pas normal')])]),
          dict(name='maman',contents=[dict(name='fistone',contents=[dict(name='subfistone',contents='baby')])])];
    prog.populate_Tree(data)
    filename='C:\\Data\\2019\\20190220\\Dataset_20190220_004\\Dataset_20190220_004.h5'
    import tables
    h5_file = tables.open_file(filename, mode = "a")
    for node in h5_file.walk_nodes():
        print(node)
    base_node = h5_file.root
    base_tree_item, pixmap_items = h5tree_to_QTree(h5_file, base_node)
    prog.ui.Tree.addTopLevelItem(base_tree_item)
    sys.exit(app.exec_())
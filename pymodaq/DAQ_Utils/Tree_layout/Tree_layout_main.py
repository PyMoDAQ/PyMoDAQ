from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QObject, pyqtSignal, QLocale
import sys
from pymodaq.daq_utils.tree_layout.tree_form import Ui_Form




class Tree_layout(Ui_Form,QObject):
    """
    PyQt5 class object based on QtreeWidget
    The function populate_Tree has to be used in order to populate the tree with structure as nested lists of dicts

    """
    status_sig=pyqtSignal(str)

    def __init__(self,parent,col_counts=1,labels=None):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(Ui_Form,self).__init__()
        
        self.ui=Ui_Form()
        self.ui.setupUi(parent)
        self.parent=parent

        self.ui.Tree.setColumnCount(col_counts)
        if labels is not None:
            self.ui.Tree.setHeaderLabels(labels)

        self.ui.Open_Tree.clicked.connect(self.ui.Tree.expandAll)
        self.ui.Close_Tree.clicked.connect(self.ui.Tree.collapseAll)
        self.ui.Open_Tree_Selected.clicked.connect(self.open_Tree_selection)

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


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    prog = Tree_layout(Form,col_counts=2,labels=["Material","File"])
    Form.show()
    data=[dict(name='papa',contents=[dict(name='fiston',contents=[dict(name='subfiston',contents='baby',filename='Cest pas sorcier')]),
                                     dict(name='fiston1',contents=[dict(name='subfiston',contents='baby',filename='Cest pas malin')]),
                                     dict(name='fiston2',contents=[dict(name='subfiston',contents='baby',filename='Cest pas normal')])]),
          dict(name='maman',contents=[dict(name='fistone',contents=[dict(name='subfistone',contents='baby')])])];
    prog.populate_Tree(data)
    filename='D:\\Data\\2018\\20180108\\Dataset_20180108_001\\Dataset_20180108_001.h5'
    import tables
    h5_file = tables.open_file(filename, mode = "a")
    for node in h5_file.walk_nodes():
        print(node)
    
    sys.exit(app.exec_())
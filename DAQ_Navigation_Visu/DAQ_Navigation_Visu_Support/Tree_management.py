from PyQt5 import QtCore, QtGui, QtWidgets
from nptdms import TdmsFile


def generate_Tree_from_tdms(Tree,tdms_file):

    groups=tdms_file.groups()
    groups_unique=mylib.remove_replica_list(groups)  
    Tree.setSelectionBehavior(Tree.SelectRows)
    model =QtGui.QStandardItemModel()
    model.setHorizontalHeaderLabels(['Data'])
    Tree.setModel(model)
    Tree.setUniformRowHeights(True)

    for i,parent_txt in enumerate(groups):
        parent = QtGui.QStandardItem(parent_txt)
        channels=tdms_file.group_channels(parent_txt)
        for j,child in enumerate(channels):
            child = QtGui.QStandardItem(child.channel)
            parent.appendRow(child)
        model.appendRow(parent)
        # span container columns
        Tree.setFirstColumnSpanned(i, Tree.rootIndex(), True)




if __name__=='__main__':
    path=('D:\\Data\\2016\\20161128\\scan001\\scan001.tdms')
    tdms_file = TdmsFile(path)
    x="blabla"

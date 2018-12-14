# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Tree_form.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(393, 414)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.splitter_2 = QtWidgets.QSplitter(Form)
        self.splitter_2.setOrientation(QtCore.Qt.Vertical)
        self.splitter_2.setObjectName("splitter_2")
        self.splitter = QtWidgets.QSplitter(self.splitter_2)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.verticalLayoutWidget = QtWidgets.QWidget(self.splitter)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout_7 = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.Tree = QtWidgets.QTreeWidget(self.verticalLayoutWidget)
        self.Tree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.Tree.setObjectName("Tree")
        self.Tree.headerItem().setText(0, "1")
        self.verticalLayout_7.addWidget(self.Tree)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.Open_Tree = QtWidgets.QPushButton(self.verticalLayoutWidget)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/Labview_icons/Icon_Library/tree.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.Open_Tree.setIcon(icon)
        self.Open_Tree.setObjectName("Open_Tree")
        self.horizontalLayout.addWidget(self.Open_Tree)
        self.Open_Tree_Selected = QtWidgets.QPushButton(self.verticalLayoutWidget)
        self.Open_Tree_Selected.setIcon(icon)
        self.Open_Tree_Selected.setObjectName("Open_Tree_Selected")
        self.horizontalLayout.addWidget(self.Open_Tree_Selected)
        self.Close_Tree = QtWidgets.QPushButton(self.verticalLayoutWidget)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/Labview_icons/Icon_Library/CollapseAll.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.Close_Tree.setIcon(icon1)
        self.Close_Tree.setObjectName("Close_Tree")
        self.horizontalLayout.addWidget(self.Close_Tree)
        self.verticalLayout_7.addLayout(self.horizontalLayout)
        self.gridLayout.addWidget(self.splitter_2, 0, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.Open_Tree.setText(_translate("Form", "Open Tree"))
        self.Open_Tree_Selected.setText(_translate("Form", "Open Selected"))
        self.Close_Tree.setText(_translate("Form", "Close Tree"))

import pymodaq.QtDesigner_Ressources.QtDesigner_ressources_rc

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())


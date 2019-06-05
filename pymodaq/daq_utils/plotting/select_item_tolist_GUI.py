# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'select_item_tolist_GUI.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(204, 289)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.add_item_pb = QtWidgets.QPushButton(Form)
        self.add_item_pb.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/Add2.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.add_item_pb.setIcon(icon)
        self.add_item_pb.setObjectName("add_item_pb")
        self.verticalLayout.addWidget(self.add_item_pb)
        self.remove_item_pb = QtWidgets.QPushButton(Form)
        self.remove_item_pb.setText("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/icons/Icon_Library/remove.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.remove_item_pb.setIcon(icon1)
        self.remove_item_pb.setObjectName("remove_item_pb")
        self.verticalLayout.addWidget(self.remove_item_pb)
        self.items_cb = QtWidgets.QComboBox(Form)
        self.items_cb.setObjectName("items_cb")
        self.verticalLayout.addWidget(self.items_cb)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.all_items_list = QtWidgets.QListWidget(Form)
        self.all_items_list.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.all_items_list.setDragEnabled(True)
        self.all_items_list.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.all_items_list.setAlternatingRowColors(True)
        self.all_items_list.setObjectName("all_items_list")
        self.horizontalLayout.addWidget(self.all_items_list)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.add_item_pb.setToolTip(_translate("Form", "Add item"))
        self.remove_item_pb.setToolTip(_translate("Form", "Remove item"))
        self.items_cb.setToolTip(_translate("Form", "Items"))
        self.all_items_list.setToolTip(_translate("Form", "List of possible items"))

import QtDesigner_ressources_rc

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())

